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
from langchain_core.callbacks import UsageMetadataCallbackHandler

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

    contatore = UsageMetadataCallbackHandler()
    estrazione = estrai(estrattore.with_config(callbacks=[contatore]), testo)
    riga, problemi, avvisi = valida(estrazione, testo)

    # Il risultato e i token, stampati prima dei controlli: con -s si vedono
    # anche quando un controllo fallisce
    uso = list(contatore.usage_metadata.values())
    print(f"\n=== {nome}")
    print(
        f"token: ingresso {sum(u['input_tokens'] for u in uso)}, "
        f"uscita {sum(u['output_tokens'] for u in uso)}"
    )
    print(f"natura: {estrazione.natura} ({estrazione.natura_motivo})")
    if estrazione.natura == "bando":
        print(f"esito: {decidi_automatico(estrazione, riga) if not problemi else None}")
        for campo in atteso["campi"]:
            print(f"  {campo}: {riga.get(campo)!r}")
        for b in riga.get("beneficiari_ammessi", []):
            print(f"  beneficiario {b['tipo']}: {b['condizioni']!r}")
        print(f"  interventi: {[i['genere'] for i in riga.get('interventi', [])]}")
        print(f"  cumulabilita: {riga.get('cumulabilita')!r}")
    print(f"problemi: {problemi}")
    print(f"avvisi: {avvisi}")

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
