"""test funzioni src.ingestion.testo"""

import pytest
from langchain_core.documents import Document

from src.config import CHUNK_SIZE, SOGLIA_CHUNK
from src.ingestion.testo import pulisci, spezza

CASI_PULIZIA = [
    pytest.param("41/202 2", "41/2022", id="numeri spezzati"),
    pytest.param(
        "Il costo\u00a0massimo è € 322,00 e va applicato a tutti\u00a0gli incarichi.",
        "Il costo massimo è € 322,00 e va applicato a tutti gli incarichi.",
        id="spazio non separabile",
    ),
    pytest.param(
        "Il comune ha 1834 \tabitanti (fonte: [D1], \tISTAT).",
        "Il comune ha 1834 abitanti (fonte: [D1], ISTAT).",
        id="spazi e tabulazioni ridotti a uno",
    ),
    pytest.param(
        "il costo è € 322,  00 (fonte: [1], Regione, pag. 11).",
        "il costo è € 322,00 (fonte: [1], Regione, pag. 11).",
        id="separatore staccato",
    ),
    pytest.param(
        "Introduzione ........ 3",
        "Introduzione 3",
        id="cinque punti in fila ridotti a uno spazio",
    ),
    pytest.param(
        "riferimento all'atto in prosa.\n\n\nNuova citazione",
        "riferimento all'atto in prosa.\n\nNuova citazione",
        id="tre o più a capo diventano due",
    ),
    pytest.param(
        "punti 3, 4 e 5",
        "punti 3, 4 e 5",
        id="virgola tra numeri distinti non li fonde",
        marks=pytest.mark.xfail(strict=True),
    ),
]

TESTO_LUNGO = "Una frase qualunque sul bando. " * 50
PAGINA_INDICE = "capitolo 1.............15\n" * 15
PAGINA_CORTA = "non li fonde"


@pytest.mark.parametrize("ingresso, atteso", CASI_PULIZIA)
def test_pulisci(ingresso, atteso):
    assert pulisci(ingresso) == atteso


@pytest.mark.xfail(strict=True)
def test_rimuovi_intestazione():
    testo = "il costo massimo è REGIONE TOSCANA di 322,00 euro"
    intestazione = "regione toscana"
    assert pulisci(testo, intestazione) == "il costo massimo è di 322,00 euro"


def test_salta_pagine_indicate():
    pagine = [
        Document(page_content=TESTO_LUNGO, metadata={"page": 1}),
        Document(page_content=TESTO_LUNGO, metadata={"page": 2}),
    ]
    chunk = spezza(pagine, salta_pagine=[2])
    pagine_nei_chunk = {c.metadata["page"] for c in chunk}
    assert pagine_nei_chunk == {1}


def test_salta_indice():
    pagine = [
        Document(page_content=PAGINA_INDICE, metadata={"page": 1}),
        Document(page_content=TESTO_LUNGO, metadata={"page": 2}),
    ]
    chunk = spezza(pagine)
    pagine_nei_chunk = {c.metadata["page"] for c in chunk}
    assert pagine_nei_chunk == {2}


def test_pagina_corta_non_produce_chunk():
    pagine = [
        Document(page_content=TESTO_LUNGO, metadata={"page": 1}),
        Document(page_content=PAGINA_CORTA, metadata={"page": 2}),
    ]
    chunk = spezza(pagine)
    pagine_nei_chunk = {c.metadata["page"] for c in chunk}
    assert pagine_nei_chunk == {1}


def test_chunk_entro_i_limiti_di_lunghezza():
    pagine = [Document(page_content=TESTO_LUNGO, metadata={"page": 1})]
    chunk = spezza(pagine)
    assert len(chunk) > 1
    assert all(SOGLIA_CHUNK <= len(c.page_content) <= CHUNK_SIZE for c in chunk)


def test_chunk_conservano_i_metadati():
    pagine = [
        Document(
            page_content=TESTO_LUNGO, metadata={"page": 1, "fonte": "avviso_mercati"}
        )
    ]
    chunk = spezza(pagine)
    assert all(c.metadata == {"page": 1, "fonte": "avviso_mercati"} for c in chunk)
