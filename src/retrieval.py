"""Recupero ibrido: ricerca densa (embedding) e lessicale (BM25), unite con RRF."""

import re

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from src.vectorstore import apri_store

COSTANTE_RRF = 60

# Apostrofi e virgolette tipografici, ricondotti a quelli dritti
_TIPOGRAFICI = str.maketrans(
    {"’": "'", "‘": "'", "`": "'", "“": '"', "”": '"', "«": '"', "»": '"'}
)


def normalizza_domanda(domanda: str) -> str:
    """La domanda in una forma sola, prima di ogni ricerca.

    Apostrofi e virgolette tipografici diventano dritti, il punto
    interrogativo finale si toglie, gli spazi si uniformano. Il 12
    novembre 2026 la stessa domanda copiata con l'apostrofo tipografico,
    o scritta senza "?", spostava di diverse posizioni il frammento giusto
    (scripts/diagnostica/prova_recupero.py): il modello di embedding è
    sensibile a questi caratteri.
    """
    testo = " ".join(domanda.translate(_TIPOGRAFICI).split())
    return testo.rstrip("?").rstrip()


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

    def titoli(self) -> dict[str, str]:
        """Titolo di ogni documento in archivio, per nome del file sorgente."""
        return {
            d.metadata["fonte"]: d.metadata.get("titolo") or ""
            for d in self.documenti
            if d.metadata.get("fonte")
        }

    def _lessicale(
        self, domanda: str, quanti: int, fonte: str | None = None
    ) -> list[Document]:
        """BM25 su tutto l'archivio; con `fonte`, solo i chunk di quel documento.

        I punteggi si calcolano sempre su tutto l'indice, così il peso per
        rarità delle parole resta quello dell'archivio.
        """
        punteggi = self.bm25.get_scores(tokenizza(domanda))
        indici = [
            i
            for i in range(len(punteggi))
            if fonte is None or self.documenti[i].metadata.get("fonte") == fonte
        ]
        migliori = sorted(indici, key=lambda i: punteggi[i], reverse=True)[:quanti]
        return [self.documenti[i] for i in migliori if punteggi[i] > 0]

    def cerca(
        self,
        domanda: str,
        k: int = 8,
        ampiezza: int = 20,
        fonte: str | None = None,
    ) -> list[tuple[Document, float, list[str]]]:
        """Restituisce i k chunk migliori con punteggio RRF e provenienza.

        Con `fonte`, la ricerca si limita ai chunk di quel documento.
        """
        filtro = {"fonte": fonte} if fonte else None
        densa = self.store.similarity_search(domanda, k=ampiezza, filter=filtro)
        lessicale = self._lessicale(domanda, ampiezza, fonte=fonte)

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
