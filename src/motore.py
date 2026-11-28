"""Motore in memoria dell'ordine c-LR (fermata 1 del 19e, sotto-fermata 1.1).

Un solo motore, due archivi (docs/piano-fermata-1.md, sezione 3): l'archivio
dà i `Frammenti` (id, testi, metadati, vettori, contesti), sempre ordinati
per id; il motore li tiene in memoria e cerca come la misura del 19d:

- ricerca per significato esatta (prodotto scalare con tutti i vettori,
  pari merito per id);
- ricerca per parole (BM25) sul testo con il contesto davanti;
- fusione RRF di `RecuperoIbrido.cerca` (ereditata, non riscritta);
- ricerca ristretta a un bando (`cerca_nel_bando`);
- riordino dei candidati con il riordinatore (contesto davanti al testo).

Il codice è copiato da scripts/diagnostica/misura_recupero_avvisi.py
(impronta 216d67cc8abc), che resta congelato e fa da riferimento (decisione
1 del 28/11/2026): `testo_con_contesto`, `StoreEsatto` (qui
`RicercaEsatta`), `controlla_normalizzati`, la costruzione del BM25 e
`cerca_nel_bando` di `RecuperoMisura`, `riordina`, `testo_per_riordino`,
l'ordine per id di `esporta_frammenti`. Il doppione è annotato in
docs/coda.md.

I documenti restituiti hanno il testo pulito e i metadati del frammento,
mai il contesto: il contesto vive in un dizionario a parte del motore e
serve solo a cercare e a riordinare (decisione 2 del 25/11/2026).

Non è collegato all'app: nessuno lo importa (sotto-fermata 1.4).
"""

import platform
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path

import numpy as np
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from src.config import (
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    MODELLO_RIORDINO,
    REVISIONE_EMBEDDING,
    REVISIONE_RIORDINO,
)
from src.retrieval import COSTANTE_RRF, RecuperoIbrido, chiave_di, tokenizza

# Scarto massimo della norma dei vettori da 1 (TOLLERANZA_NORMA della misura)
TOLLERANZA_NORMA = 1e-3
# Ampiezza di ogni ricerca prima della fusione (AMPIEZZA_APP della misura,
# la stessa di RecuperoIbrido.cerca)
AMPIEZZA = 20
# Peso della ricerca per significato nella fusione di cerca_nel_bando
# (PESO_DENSA della misura): con 0,5 i pesi sono 2 * 0,5 = 1 per tutte e due
# le ricerche, come in RecuperoIbrido.cerca
PESO_DENSA = 0.5

Contesti = dict[tuple[str, int], str]


# --- archivio ---


def matrice_di(vettori) -> np.ndarray:
    """I vettori come matrice float32, una riga per frammento.

    Accetta righe numpy, liste o oggetti con `to_numpy()` (i vettori di
    pgvector letti da Postgres, fermata 5): la conversione è dell'archivio,
    il motore riceve sempre una matrice.
    """
    righe = [v.to_numpy() if hasattr(v, "to_numpy") else v for v in vettori]
    if not righe:
        return np.zeros((0, 0), dtype=np.float32)
    return np.asarray(np.stack([np.asarray(r) for r in righe]), dtype=np.float32)


@dataclass(frozen=True, eq=False)
class Frammenti:
    """I frammenti di un archivio, ordinati per id.

    ids, testi, metadati e righe della matrice sono allineati; `contesti` è
    per (fonte, chunk_num). L'ordine per id non è un dettaglio: da lui
    dipendono i pari merito della ricerca esatta e l'ordine dell'indice BM25
    (get() di Chroma non restituisce i frammenti in ordine di id, prova zero
    del 28/11/2026). Si costruisce con `da_righe`, che ordina.
    """

    ids: tuple[str, ...]
    testi: tuple[str, ...]
    metadati: tuple[dict, ...]
    matrice: np.ndarray
    contesti: Contesti = field(default_factory=dict)

    def __post_init__(self) -> None:
        n = len(self.ids)
        if not (len(self.testi) == len(self.metadati) == len(self.matrice) == n):
            raise ValueError("ids, testi, metadati e vettori in numero diverso")
        if any(a >= b for a, b in zip(self.ids, self.ids[1:], strict=False)):
            raise ValueError("frammenti non ordinati per id, o id ripetuti")

    @classmethod
    def da_righe(cls, ids, testi, metadati, vettori, contesti=None) -> "Frammenti":
        """I frammenti in ordine di id, comunque arrivino (come esporta_frammenti)."""
        ids, testi, metadati, vettori = (
            list(ids),
            list(testi),
            list(metadati),
            list(vettori),
        )
        ordine = sorted(range(len(ids)), key=lambda i: ids[i])
        return cls(
            ids=tuple(ids[i] for i in ordine),
            testi=tuple(testi[i] for i in ordine),
            metadati=tuple(dict(metadati[i]) for i in ordine),
            matrice=matrice_di([vettori[i] for i in ordine]),
            contesti=dict(contesti or {}),
        )


def frammenti_da_get(dati: dict, contesti: Contesti | None = None) -> Frammenti:
    """I Frammenti dal risultato di get() di Chroma (documents, metadatas, embeddings)."""
    return Frammenti.da_righe(
        dati["ids"], dati["documents"], dati["metadatas"], dati["embeddings"], contesti
    )


class ArchivioChroma:
    """L'archivio locale: la collezione di Chroma letta una volta, in ordine di id.

    I contesti si passano da fuori; dalla sotto-fermata 1.3 li legge dal
    file data/db/contesti_avvisi.jsonl (decisione 2 del 28/11/2026).
    L'archivio non scrive mai nel Chroma.
    """

    def __init__(
        self,
        cartella: Path,
        collezione: str = COLLECTION_NAME,
        contesti: Contesti | None = None,
    ) -> None:
        self.cartella = Path(cartella)
        self.collezione = collezione
        self.contesti = dict(contesti or {})

    def _leggi(self) -> dict:
        import chromadb
        from chromadb.config import Settings

        cliente = chromadb.PersistentClient(
            path=str(self.cartella), settings=Settings(anonymized_telemetry=False)
        )
        dati = cliente.get_collection(self.collezione).get(
            include=["documents", "metadatas", "embeddings"]
        )
        del cliente
        return dati

    def frammenti(self) -> Frammenti:
        return frammenti_da_get(self._leggi(), self.contesti)


# --- ricerca ---


def testo_con_contesto(testo: str, meta: dict, contesti: Contesti | None) -> str:
    """Il testo con il contesto del suo frammento davanti, se c'è (passo 19d).

    `contesti` è per (fonte, chunk_num). Serve solo all'indice per parole e
    alle coppie del riordinatore: il testo dei documenti restituiti resta
    quello pulito.
    """
    chiave = (meta.get("fonte") or "", meta.get("chunk_num"))
    contesto = (contesti or {}).get(chiave)
    return f"{contesto}\n{testo}" if contesto else testo


def controlla_normalizzati(matrice) -> float:
    """Lo scarto massimo della norma da 1; errore se supera la tolleranza."""
    scarto = float(np.max(np.abs(np.linalg.norm(matrice, axis=1) - 1.0)))
    if scarto > TOLLERANZA_NORMA:
        raise ValueError(f"vettori non normalizzati: scarto della norma {scarto:.4f}")
    return scarto


class RicercaEsatta:
    """Ricerca per significato esatta: prodotto scalare con tutti i vettori.

    Ha similarity_search() come lo store di Chroma che RecuperoIbrido si
    aspetta. I pari merito si ordinano per id, così l'ordine non dipende da
    nient'altro che dai numeri. Calcolo in float64, come StoreEsatto.
    """

    def __init__(self, frammenti: Frammenti, embeddings) -> None:
        self.ids = list(frammenti.ids)
        self.testi = list(frammenti.testi)
        self.metadati = [dict(m) for m in frammenti.metadati]
        self.matrice = np.asarray(frammenti.matrice, dtype=np.float64)
        if len(self.ids) != len(self.matrice):
            raise ValueError("vettori e frammenti in numero diverso")
        controlla_normalizzati(self.matrice)
        self.embeddings = embeddings

    def punteggi(self, domanda: str):
        vettore = np.asarray(self.embeddings.embed_query(domanda), dtype=np.float64)
        return self.matrice @ vettore

    def similarity_search(self, query: str, k: int = 4, filter: dict | None = None):  # noqa: A002
        punteggi = self.punteggi(query)
        indici = [
            i
            for i, meta in enumerate(self.metadati)
            if not filter or all(meta.get(c) == v for c, v in filter.items())
        ]
        ordine = sorted(indici, key=lambda i: (-punteggi[i], self.ids[i]))[:k]
        return [
            Document(page_content=self.testi[i], metadata=dict(self.metadati[i]))
            for i in ordine
        ]


class Motore(RecuperoIbrido):
    """La ricerca dell'app (cerca è quella di RecuperoIbrido) sul motore esatto.

    Come RecuperoMisura della misura con StoreEsatto: documenti nell'ordine
    dei Frammenti (per id), BM25 sul testo con il contesto davanti. Offre
    anche titoli() e frammento(fonte, chunk_num), ereditati.
    """

    def __init__(self, frammenti: Frammenti, embeddings) -> None:
        self.frammenti = frammenti
        self.store = RicercaEsatta(frammenti, embeddings)
        self._contesti: Contesti = dict(frammenti.contesti)
        self.documenti = [
            Document(page_content=testo, metadata=dict(meta))
            for testo, meta in zip(frammenti.testi, frammenti.metadati, strict=True)
        ]
        self.bm25 = BM25Okapi(
            [
                tokenizza(
                    testo_con_contesto(d.page_content, d.metadata, self._contesti)
                )
                for d in self.documenti
            ]
        )
        self._per_chiave = {chiave_di(d): d for d in self.documenti}

    @property
    def contesti(self) -> Contesti:
        """Una copia dei contesti, per il riordino: mai dentro un Document."""
        return dict(self._contesti)

    def cerca_nel_bando(
        self, domanda: str, id_bando: str, k: int, ampiezza: int = AMPIEZZA
    ) -> list[tuple[Document, float, list[str]]]:
        """Come cerca, solo tra i frammenti del bando; BM25 pesato su tutto l'indice.

        I punteggi delle parole si calcolano su tutto l'indice, così il peso
        per rarità resta quello dell'archivio; poi si tengono solo i
        frammenti del bando.
        """
        densa = self.store.similarity_search(
            domanda, k=ampiezza, filter={"id_bando": id_bando}
        )
        punteggi = self.bm25.get_scores(tokenizza(domanda))
        indici = [
            i
            for i, d in enumerate(self.documenti)
            if d.metadata.get("id_bando") == id_bando
        ]
        migliori = sorted(indici, key=lambda i: punteggi[i], reverse=True)[:ampiezza]
        lessicale = [self.documenti[i] for i in migliori if punteggi[i] > 0]
        punti: dict = {}
        pesi = {"densa": 2 * PESO_DENSA, "lessicale": 2 * (1 - PESO_DENSA)}
        for nome, elenco in (("densa", densa), ("lessicale", lessicale)):
            for pos, documento in enumerate(elenco, start=1):
                voce = punti.setdefault(
                    chiave_di(documento),
                    {"doc": documento, "punteggio": 0.0, "origini": []},
                )
                voce["punteggio"] += pesi[nome] / (COSTANTE_RRF + pos)
                voce["origini"].append(f"{nome} #{pos}")
        ordinati = sorted(punti.values(), key=lambda v: v["punteggio"], reverse=True)
        return [(v["doc"], v["punteggio"], v["origini"]) for v in ordinati[:k]]


# --- riordino ---


def riordina(voti, n: int) -> list[int]:
    """Gli indici dei candidati dal voto più alto; a parità, l'ordine di prima.

    Con due classi per coppia vale l'ultima (quella positiva).
    """
    voti = np.asarray(voti, dtype=np.float64)
    if voti.ndim == 2:
        voti = voti[:, -1]
    if len(voti) != n:
        raise ValueError("voti e candidati in numero diverso")
    return sorted(range(n), key=lambda i: (-voti[i], i))


def voti_di(voti) -> list[float]:
    """Un voto per candidato (l'ultima colonna se sono due), come in riordina."""
    voti = np.asarray(voti, dtype=np.float64)
    if voti.ndim == 2:
        voti = voti[:, -1]
    return [float(v) for v in voti]


class Riordino:
    """Il riordinatore sui candidati: coppie (domanda, contesto + a capo + testo).

    `modello` ha predict(coppie, show_progress_bar=False), come CrossEncoder.
    La domanda si passa già nella forma voluta (in A normalizzata, in B
    ripulita, come nella misura): il riordino non la cambia.
    """

    def __init__(self, modello) -> None:
        self.modello = modello

    def coppie(self, domanda: str, candidati: list, contesti: Contesti | None):
        return [
            (domanda, testo_con_contesto(d.page_content, d.metadata, contesti))
            for d, _, _ in candidati
        ]

    def riordina_candidati(
        self, domanda: str, candidati: list, contesti: Contesti | None, k: int
    ) -> list[tuple[Document, float, list[str]]]:
        """I primi k candidati dopo il riordino, con il voto e le origini.

        candidati: tuple (documento, punteggio, origini) in ordine di ricerca.
        Ogni risultato ha come punteggio il voto del riordinatore e, in fondo
        alle origini, "riordino #n" (n da 1). I documenti sono quelli dei
        candidati, non toccati.
        """
        coppie = self.coppie(domanda, candidati, contesti)
        voti = (
            self.modello.predict(coppie, show_progress_bar=False) if candidati else []
        )
        ordine = riordina(voti, len(candidati))
        valori = voti_di(voti) if candidati else []
        uscita = []
        for n, i in enumerate(ordine[:k], start=1):
            documento, _, origini = candidati[i]
            uscita.append((documento, valori[i], [*origini, f"riordino #{n}"]))
        return uscita


# --- modelli ---


def carica_embeddings(solo_locale: bool = False):
    """Il modello di embedding delle domande, alla revisione fissata.

    Stessa configurazione di crea_embeddings (src/vectorstore.py) e della
    misura (stesso modello, vettori normalizzati, nessun limite di token),
    più la revisione (decisione 5 del 28/11/2026).
    """
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"revision": REVISIONE_EMBEDDING, "local_files_only": solo_locale},
        encode_kwargs={"normalize_embeddings": True},
    )


def carica_riordinatore(solo_locale: bool = False):
    """Il riordinatore osiria L12, alla revisione fissata, senza codice remoto."""
    from sentence_transformers import CrossEncoder

    return CrossEncoder(
        MODELLO_RIORDINO,
        revision=REVISIONE_RIORDINO,
        trust_remote_code=False,
        local_files_only=solo_locale,
    )


def versioni() -> dict[str, str]:
    """Versioni di Python e delle librerie e revisioni dei modelli, per il registro.

    Alla fermata 5 servono a confrontare l'ambiente del PC e quello online
    prima degli ordini (docs/piano-fermata-1.md, sezione 5).
    """
    uscita = {"python": platform.python_version()}
    for nome in (
        "torch",
        "sentence-transformers",
        "transformers",
        "numpy",
        "rank-bm25",
    ):
        try:
            uscita[nome] = metadata.version(nome)
        except metadata.PackageNotFoundError:
            uscita[nome] = ""
    uscita["revisione_embedding"] = REVISIONE_EMBEDDING
    uscita["revisione_riordino"] = REVISIONE_RIORDINO
    return uscita
