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

RICUCITURE = ("completa", "prudente")

# Ricucitura prudente: due gruppi di cifre separati da spazi si uniscono
# solo se ne viene un anno ("202 6", "41/202 2") o un numero seguito da
# "/anno" ("1 060/2021"). Le cifre non devono continuare oltre i due
# gruppi, nemmeno dopo un punto o una virgola ("20 25.000" resta com'\u00e8).
_DUE_GRUPPI = re.compile(
    r"(?<!\d)(?<![.,]\d)(\d{1,3})[ \t]+(\d{1,3})(?!\d)(?![.,]\d)(?=(/(?:19|20)\d\d(?!\d))?)"
)
_ANNO = re.compile(r"(?:19|20)\d\d")


def _ricuci_prudente(testo: str) -> str:
    """Unisce i numeri spezzati solo nei due casi sicuri (vedi sopra).

    Nelle tabelle la ricucitura completa fonde celle vicine: "B1 40.000,00"
    diventava "B140.000,00", "2021/2115 4" (regolamento e punteggio)
    "2021/21154", "artt. 5 3, 14" "53,14" (avvisi del 19/11/2026).
    """

    def unisci(m: re.Match) -> str:
        unito = m.group(1) + m.group(2)
        if _ANNO.fullmatch(unito) or m.group(3):
            return unito
        return m.group(0)

    testo = _DUE_GRUPPI.sub(unisci, testo)
    # Solo la barra: virgola e punto tra cifre separate restano come sono
    return re.sub(r"(?<=\d)[ \t]*/[ \t]*(?=\d)", "/", testo)


def pulisci(
    testo: str, intestazione: str | None = None, ricucitura: str = "completa"
) -> str:
    """Normalizza gli spazi, poi rimuove l'intestazione ricorrente.

    `ricucitura` dice come si uniscono i numeri spezzati dall'estrazione:
    "completa" (la regola dei documenti caricati fino al 19/11/2026, che
    unisce ogni cifra separata da spazi) o "prudente" (solo anni e numeri
    con /anno, per gli avvisi dei bandi del passo 19).
    """
    if ricucitura not in RICUCITURE:
        raise ValueError(f"ricucitura sconosciuta: {ricucitura!r}")
    testo = testo.replace("\u00a0", " ")
    testo = re.sub(r"[ \t]+", " ", testo)

    if ricucitura == "prudente":
        testo = _ricuci_prudente(testo)
    else:
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
    ricucitura: str = "completa",
) -> list[Document]:
    """Divide le pagine in chunk, saltando quelle indicate.

    `ricucitura` passa a `pulisci`: "completa" per i documenti di sempre,
    "prudente" per gli avvisi dei bandi.
    """
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

        testo = pulisci(pagina.page_content, intestazione, ricucitura)

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
