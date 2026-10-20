import json
import os
import re

import numpy as np
import psycopg
from dotenv import load_dotenv
from langchain_core.documents import Document
from pgvector.psycopg import register_vector

from src.vectorstore import crea_embeddings

load_dotenv()

COSTANTE_RRF = 60


def salva_chunk_in_db(documenti: list[Document]) -> None:
    """Salva i chunk dei documenti nel database."""

    with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
        register_vector(conn)
        cursor = conn.cursor()

        emb = crea_embeddings()

        testi = [doc.page_content for doc in documenti]
        vettori = emb.embed_documents(testi)

        for documento, vettore in zip(documenti, vettori, strict=True):
            cursor.execute(
                "INSERT INTO chunk (testo, metadata, embedding) VALUES (%s, %s, %s)",
                (
                    documento.page_content,
                    json.dumps(documento.metadata),
                    np.array(vettore),
                ),
            )
        conn.commit()

    print(f"  Salvati {len(documenti)} chunk su Postgres")


def a_or_query(domanda: str) -> str:
    """Trasforma la domanda in una query OR per to_tsquery.

    Estrae solo le sequenze alfanumeriche, così la punteggiatura non rompe
    to_tsquery, e unisce i termini con OR: l'AND di plainto_tsquery era
    troppo rigido e su domande in linguaggio naturale non trovava nulla.
    """
    parole = re.findall(r"\w+", domanda.lower())
    return " | ".join(parole)


class RecuperoPostgres:
    """Recupero ibrido su Postgres: densa con pgvector, lessicale con full-text."""

    def __init__(self) -> None:
        self.emb = crea_embeddings()

    def _densa(self, domanda: str, quanti: int) -> list[Document]:
        """Cerca per similarità semantica, confrontando gli embedding."""
        vettore_domanda = np.array(self.emb.embed_query(domanda))

        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            register_vector(conn)
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id,
                        testo, 
                        metadata, 
                        embedding <=> %s AS distanza
                FROM chunk
                ORDER BY distanza
                LIMIT %s""",
                (vettore_domanda, quanti),
            )

            return [
                Document(page_content=testo, metadata={**metadata, "id": id})
                for id, testo, metadata, distanza in cursor.fetchall()
            ]

    def _lessicale(self, domanda: str, quanti: int) -> list[Document]:
        """Cerca per parole, con il full-text italiano di Postgres."""

        query = a_or_query(domanda)

        with psycopg.connect(os.getenv("DATABASE_URL")) as conn:
            register_vector(conn)
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id,
                        testo, 
                        metadata, 
                        ts_rank_cd(to_tsvector('italian', testo), to_tsquery('italian', %s)) AS rank
                        FROM chunk
                        WHERE to_tsvector('italian', testo) @@ to_tsquery('italian', %s)
                        ORDER BY rank DESC
                        LIMIT %s""",
                (query, query, quanti),
            )

            return [
                Document(page_content=testo, metadata={**metadata, "id": id})
                for id, testo, metadata, rank in cursor.fetchall()
            ]

    def cerca(
        self, domanda: str, k: int = 8, ampiezza: int = 20
    ) -> list[tuple[Document, float, list[str]]]:
        """Restituisce i k chunk migliori con punteggio RRF e provenienza."""
        densa = self._densa(domanda, quanti=ampiezza)
        lessicale = self._lessicale(domanda, quanti=ampiezza)

        punti: dict = {}

        for nome, elenco in (("densa", densa), ("lessicale", lessicale)):
            for posizione, documento in enumerate(elenco, start=1):
                chiave = documento.metadata["id"]

                if chiave not in punti:
                    punti[chiave] = {
                        "doc": documento,
                        "punteggio": 0.0,
                        "origini": [],
                    }

                punti[chiave]["punteggio"] += 1 / (COSTANTE_RRF + posizione)
                punti[chiave]["origini"].append(f"{nome} #{posizione}")

        ordinati = sorted(punti.values(), key=lambda v: v["punteggio"], reverse=True)

        return [(v["doc"], v["punteggio"], v["origini"]) for v in ordinati[:k]]


if __name__ == "__main__":
    recupero = RecuperoPostgres()

    domande = [
        "Quante risorse sono destinate a ciascuna Area interna?",
        "Entro quale data devono essere sostenute le spese?",
        "Chi sono i soggetti che possono presentare domanda?",
        "Quali enti sono beneficiari del sostegno?",
        "Qual è il costo massimo giornaliero per un incarico professionale?",
        "cosa dice l'art. 7 comma 6?",
    ]

    for domanda in domande:
        print(f"\n>>> {domanda}")
        for doc, punteggio, origini in recupero.cerca(domanda, k=5, ampiezza=20):
            meta = doc.metadata
            print(
                f"  {punteggio:.4f} | {meta.get('ente')} | p. {meta.get('page')} | {', '.join(origini)}"
            )
            print(f"      {doc.page_content[:100].strip()}")
