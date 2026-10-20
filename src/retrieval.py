"""Recupero ibrido: ricerca densa (embedding) e lessicale (BM25), unite con RRF."""

import re

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from src.vectorstore import apri_store

COSTANTE_RRF = 60


def tokenizza(testo: str) -> list[str]:
    """Spezza in parole minuscole, preservando i codici composti.

    Un riferimento come '41/2022' produce tre token: '41/2022', '41', '2022'.
    Il primo e' raro e discrimina molto; gli altri due mantengono
    la corrispondenza parziale.
    """
    testo = testo.lower()

    composti = re.findall(r"\b[\w.]*\d[\w./-]*\b", testo)
    parole = re.findall(r"[a-zàèéìòù]{2,}", testo)

    token = list(parole)
    for pezzo in composti:
        token.append(pezzo)
        token.extend(re.findall(r"\w+", pezzo))

    return token


def chiave_di(documento: Document) -> tuple:
    """Identificatore stabile di un chunk, per riconoscerlo nelle due liste."""
    meta = documento.metadata
    return (meta.get("fonte"), meta.get("chunk_num"))


class RecuperoIbrido:
    """Tiene in memoria l'indice lessicale e interroga entrambi i motori."""

    def __init__(self) -> None:
        self.store = apri_store()

        dati = self.store.get()
        self.documenti = [
            Document(page_content=testo, metadata=meta)
            for testo, meta in zip(dati["documents"], dati["metadatas"], strict=True)
        ]

        self.bm25 = BM25Okapi([tokenizza(d.page_content) for d in self.documenti])

        print(f"  Indice lessicale costruito su {len(self.documenti)} chunk")

    def _lessicale(self, domanda: str, quanti: int) -> list[Document]:
        punteggi = self.bm25.get_scores(tokenizza(domanda))
        migliori = sorted(
            range(len(punteggi)), key=lambda i: punteggi[i], reverse=True
        )[:quanti]
        return [self.documenti[i] for i in migliori if punteggi[i] > 0]

    def cerca(
        self,
        domanda: str,
        k: int = 8,
        ampiezza: int = 20,
    ) -> list[tuple[Document, float, list[str]]]:
        """Restituisce i k chunk migliori con punteggio RRF e provenienza."""
        densa = self.store.similarity_search(domanda, k=ampiezza)
        lessicale = self._lessicale(domanda, ampiezza)

        punti: dict = {}

        for nome, elenco in (("densa", densa), ("lessicale", lessicale)):
            for posizione, documento in enumerate(elenco, start=1):
                chiave = chiave_di(documento)

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
