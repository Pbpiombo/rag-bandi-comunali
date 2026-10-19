"""Lettura pdf e scrittura su Chroma."""

from pathlib import Path

import pypdf
from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.config import CHROMA_DIR
from src.vectorstore import apri_store


def carica_pdf(percorso: Path) -> list[Document]:
    """Legge il PDF e restituisce un Document per ogni pagina."""
    if not percorso.exists():
        raise FileNotFoundError(f"PDF non trovato: {percorso}")

    lettore = pypdf.PdfReader(str(percorso))

    pagine = []
    for numero, pagina in enumerate(lettore.pages, start=1):
        pagine.append(
            Document(
                page_content=pagina.extract_text() or "",
                metadata={"page": numero},
            )
        )

    if not any(p.page_content.strip() for p in pagine):
        print(f"  ATTENZIONE: nessun testo estratto da {percorso.name}")

    return pagine


def salva_in_chroma(chunk: list[Document], fonte: str) -> Chroma:
    """Calcola gli embedding e scrive nel vector store."""
    store = apri_store()
    identificatori = [f"{fonte}::{i}" for i in range(len(chunk))]
    store.add_documents(documents=chunk, ids=identificatori)
    print(f"  Salvati {len(chunk)} chunk in {CHROMA_DIR}")
    return store


def rimuovi_documento(fonte: str) -> int:
    """Cancella dal vector store tutti i chunk di un documento."""
    store = apri_store()
    dati = store.get(where={"fonte": fonte})

    if dati["ids"]:
        store.delete(ids=dati["ids"])

    return len(dati["ids"])
