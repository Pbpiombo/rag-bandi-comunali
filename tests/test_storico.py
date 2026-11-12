"""Bandi scaduti da meno di un anno salvati come storico (piano fonti, tappa 3).

La decisione di salvare, con la data fissata; la coerenza con la
preselezione senza modello; il registro delle scansioni.
"""

import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from src.estrazione.bandi import STORICO, Campo, Estrazione, decidi_automatico
from src.estrazione.registro import DEFINITIVI, da_non_riesaminare, registra
from src.estrazione.scadenza import GIORNI_STORICO, MARGINE_GIORNI, nello_storico

OGGI = date(2026, 11, 12)
ATTESI = json.loads(
    (Path(__file__).parent / "pagine" / "attesi.json").read_text(encoding="utf-8")
)


def _giorni_fa(giorni: int) -> str:
    return (OGGI - timedelta(days=giorni)).isoformat()


def _decidi(scadenza: str | None, a_sportello: int = 0, natura: str = "bando"):
    estrazione = Estrazione(
        campi=[Campo("scadenza", scadenza, "alta", "prova", True)],
        natura=natura,
        natura_motivo="graduatoria" if natura == "non_bando" else "",
    )
    riga = {"scadenza": scadenza, "a_sportello": a_sportello}
    return decidi_automatico(estrazione, riga, oggi=OGGI)


def test_scaduto_ieri_si_salva_come_storico():
    assert _decidi(_giorni_fa(1)) == (True, "storico: scaduto il 2026-11-11")


def test_la_soglia_e_di_un_anno():
    assert _decidi(_giorni_fa(365)) == (True, "storico: scaduto il 2025-11-12")
    assert _decidi(_giorni_fa(366)) == (False, "scaduto il 2025-11-11")


def test_sportello_con_chiusura_passata_e_storico():
    assert _decidi(_giorni_fa(30), a_sportello=1) == (
        True,
        f"storico: scaduto il {_giorni_fa(30)}",
    )


@pytest.mark.parametrize(
    ("scadenza", "a_sportello", "natura", "atteso"),
    [
        ("2026-12-31", 0, "bando", (True, "aperto fino al 2026-12-31")),
        (None, 1, "bando", (True, "a sportello")),
        (None, 0, "bando", (False, "scadenza non determinata")),
        (_giorni_fa(10), 0, "non_bando", (False, "non e' un bando: graduatoria")),
    ],
)
def test_gli_altri_esiti_non_cambiano(scadenza, a_sportello, natura, atteso):
    assert _decidi(scadenza, a_sportello, natura) == atteso


def test_il_motivo_dello_storico_non_e_uno_scarto_definitivo():
    _, motivo = _decidi(_giorni_fa(30))
    assert motivo.startswith(STORICO)
    assert not any(motivo.startswith(d) for d in DEFINITIVI)


@pytest.mark.parametrize(
    ("giorni", "atteso"),
    [(0, False), (1, True), (365, True), (366, False), (-5, False)],
)
def test_nello_storico(giorni, atteso):
    """Scaduto da 1 a 365 giorni: oggi non e' ancora scaduto, il futuro no."""
    assert nello_storico(_giorni_fa(giorni), OGGI) is atteso


def test_la_preselezione_non_scarta_pagine_da_storico():
    """Una pagina scaduta da meno della soglia deve arrivare al modello."""
    assert MARGINE_GIORNI >= GIORNI_STORICO


SCADUTI_SALVATI = {
    nome: a["motivo"]
    for nome, a in ATTESI.items()
    if (a.get("motivo") or "").startswith("scaduto il ")
}


def test_le_pagine_salvate_sono_due_scadute():
    assert sorted(SCADUTI_SALVATI) == ["musei", "tpl"]


@pytest.mark.parametrize("nome", sorted(SCADUTI_SALVATI))
def test_le_pagine_salvate_scadute_da_anni_restano_scartate(nome):
    """TPL (2021) e musei (2023) sono scaduti da piu' di un anno: l'esito
    atteso delle pagine salvate non cambia."""
    motivo = SCADUTI_SALVATI[nome]
    assert _decidi(motivo.removeprefix("scaduto il ")) == (False, motivo)


def test_lo_storico_registrato_non_e_da_non_riesaminare(db_su_file):
    url = "https://www.regione.toscana.it/-/bando-scaduto-2026"
    registra(url, "regione-toscana", "bando-scaduto-2026", "salvato", "storico: x")

    assert url not in da_non_riesaminare()
