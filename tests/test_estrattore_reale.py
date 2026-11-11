"""L'estrattore con il modello vero sulle tre pagine salvate.

Marcato 'modello': non parte con python -m pytest. Ogni pagina costa una
chiamata all'API. Si lancia solo per scelta esplicita:

    python -m pytest -m modello tests/test_estrattore_reale.py

Confronta il risultato con tests/pagine/attesi.json, la stessa tabella del
test senza modello, sui punti che contano: natura, esito, campi principali,
tipi di beneficiari e parole chiave delle condizioni.
"""

import json
from pathlib import Path

import pytest

from src.estrazione.bandi import (
    costruisci_estrattore,
    decidi_automatico,
    estrai,
    valida,
)

pytestmark = pytest.mark.modello

PAGINE = Path(__file__).parent / "pagine"
ATTESI = json.loads((PAGINE / "attesi.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def estrattore():
    return costruisci_estrattore()


@pytest.mark.parametrize("nome", list(ATTESI))
def test_modello_vero_sulle_pagine_salvate(estrattore, nome):
    atteso = ATTESI[nome]
    testo = (PAGINE / f"{nome}.txt").read_text(encoding="utf-8")

    estrazione = estrai(estrattore, testo)
    riga, problemi, avvisi = valida(estrazione, testo)
    print(f"\n{nome}: problemi={problemi}\navvisi={avvisi}")

    assert problemi == []
    assert estrazione.natura == atteso["natura"]

    salvare, motivo = decidi_automatico(estrazione, riga)
    assert salvare == atteso["salvare"]
    assert motivo.startswith(atteso["motivo"])

    for campo, valore in atteso["campi"].items():
        assert riga[campo] == valore, campo

    tipi = sorted({b["tipo"] for b in riga.get("beneficiari_ammessi", [])})
    assert tipi == atteso["tipi"]

    for tipo, parola in atteso["condizioni_contengono"].items():
        condizioni = " ".join(
            b["condizioni"] or ""
            for b in riga["beneficiari_ammessi"]
            if b["tipo"] == tipo
        )
        assert parola in condizioni.lower(), tipo

    assert len(riga.get("interventi", [])) >= atteso["interventi_almeno"]
