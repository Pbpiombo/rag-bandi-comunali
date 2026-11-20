"""Trattino a fine riga dentro un indirizzo web (compito 19c-3, secondo tempo).

Nei 16 avvisi del 19/11/2026 ci sono 22 indirizzi spezzati su un trattino
vero, per esempio "https://www.regione.toscana.it/agricoltura-e-" a fine
riga e "alimentazione/agrobiodiversita" sotto: le righe si uniscono e il
trattino resta.
"""

import pytest

from src.ingestion.avvisi import ricuci_parole


@pytest.mark.parametrize(
    "ingresso, atteso",
    [
        pytest.param(
            "vedi https://www.regione.toscana.it/agricoltura-e-\nalimentazione/agro",
            "vedi https://www.regione.toscana.it/agricoltura-e-alimentazione/agro",
            id="https",
        ),
        pytest.param(
            "sul sito www.esteri.it/legalizzazione-\ndocumenti consolari",
            "sul sito www.esteri.it/legalizzazione-documenti consolari",
            id="www",
        ),
        pytest.param(
            "(https://rica.crea.gov.it/APP/anb/anagrafe-\nnazionale-35.php)",
            "(https://rica.crea.gov.it/APP/anb/anagrafe-nazionale-35.php)",
            id="tra parentesi",
        ),
        pytest.param(
            "(www.regione.toscana.it/banche-\nregionali)",
            "(www.regione.toscana.it/banche-regionali)",
            id="www tra parentesi",
        ),
    ],
)
def test_indirizzo_tiene_il_trattino(ingresso, atteso):
    assert ricuci_parole(ingresso) == (atteso, 1)


def test_parola_e_indirizzo_nello_stesso_testo():
    testo = "da ri-\nchiedere su https://www.prova.it/bandi-\naperti"
    assert ricuci_parole(testo) == (
        "da richiedere su https://www.prova.it/bandi-aperti",
        2,
    )


def test_parola_dopo_un_indirizzo_sulla_stessa_riga():
    # il pezzo con il trattino è una parola, non l'indirizzo che la precede
    testo = "https://www.prova.it e poi ri-\nchiedere"
    assert ricuci_parole(testo) == ("https://www.prova.it e poi richiedere", 1)
