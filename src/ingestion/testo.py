"""Trasformazione del testo estratto dai PDF in chunk.

Pulizia, riconoscimento degli indici, divisione in chunk e metadati.
Non legge file e non scrive su database: lavora solo su testo e Document.
"""

import re

from langchain_core.documents import Document

from src.config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    SOGLIA_CHUNK,
    SOGLIA_PAGINA_MINIMA,
)


def pulisci(testo: str, intestazione: str | None = None) -> str:
    """Normalizza gli spazi, poi rimuove l'intestazione ricorrente."""
    testo = testo.replace("\u00a0", " ")
    testo = re.sub(r"[ \t]+", " ", testo)

    # Ricuce i numeri spezzati dall'estrazione: "41/202 2" -> "41/2022"
    testo = re.sub(r"(?<=\d)[ \t]+(?=\d)", "", testo)
    testo = re.sub(r"(?<=\d)[ \t]*([/.,])[ \t]*(?=\d)", r"\1", testo)

    testo = re.sub(r"[ \t]*(?:\.[ \t]*){5,}", " ", testo)

    if intestazione:
        testo = re.sub(intestazione, " ", testo, flags=re.IGNORECASE)

    testo = re.sub(r"\n{3,}", "\n\n", testo)
    return testo.strip()


def e_indice(testo: str, soglia: int = 5) -> bool:
    """Riconosce le pagine di indice dai puntini di guida seguiti dalla pagina.

    I PDF usano punti ripetuti o il carattere di ellissi, a volte separati
    da spazi. Il numero di pagina finale distingue un sommario da un modulo
    da compilare, che contiene puntini analoghi ma senza numero.
    """
    schema = r"(?:(?:\.\s?){4,}|(?:\u2026\s?){2,})\s*(?:pag\.?\s*)?\d{1,3}\b"
    return len(re.findall(schema, testo, re.IGNORECASE)) >= soglia


def spezza(
    pagine: list[Document],
    intestazione: str | None = None,
    salta_pagine: list[int] | None = None,
) -> list[Document]:
    """Divide le pagine in chunk, saltando quelle indicate."""
    # import all'interno della funzione, così il pacchetto si carica solo quando spezza viene chiamata.
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    salta_pagine = salta_pagine or []

    tenute = []

    for pagina in pagine:
        numero = pagina.metadata["page"]

        if numero in salta_pagine:
            continue

        if e_indice(pagina.page_content):
            print(f"  Saltata pagina {numero}: indice")
            continue

        testo = pulisci(pagina.page_content, intestazione)

        if len(testo) < SOGLIA_PAGINA_MINIMA:
            print(f"  Saltata pagina {numero}: troppo corta ({len(testo)} caratteri)")
            continue

        tenute.append(Document(page_content=testo, metadata=pagina.metadata))

    print(f"  Pagine tenute: {len(tenute)}")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            r"\n\d{1,2}\.\d{1,2}\s",
            r"\n\d{1,2}\.\s",
            r"\n\n",
            r"\n(?![\d−•-])",
            r"\.\s",
            r";\s",
            r"\s",
            r"",
        ],
        keep_separator=True,
        is_separator_regex=True,
    )

    chunk = splitter.split_documents(tenute)

    tenuti = [c for c in chunk if len(c.page_content.strip()) >= SOGLIA_CHUNK]
    scartati = [c for c in chunk if len(c.page_content.strip()) < SOGLIA_CHUNK]

    if scartati:
        print(f"  Chunk scartati perche' troppo corti: {len(scartati)}")
        for c in scartati[:10]:
            print(f"  [{c.metadata['page']}] {c.page_content.strip()[:80]}")

    chunk = tenuti

    print(f"  Chunk prodotti: {len(chunk)}")
    return chunk


def applica_metadati(chunk: list[Document], metadati: dict) -> list[Document]:
    """Unisce i metadati forniti a quelli già presenti su ogni chunk."""
    return [
        Document(
            page_content=pezzo.page_content,
            metadata={**pezzo.metadata, **metadati, "chunk_num": indice},
        )
        for indice, pezzo in enumerate(chunk)
    ]
