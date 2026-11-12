"""Scadenza letta dalla pagina senza modello, e filtro sull'anno nello slug."""

from datetime import date
from pathlib import Path

import pytest

from src.estrazione.elenco import anno_slug, recente
from src.estrazione.registro import DEFINITIVI
from src.estrazione.scadenza import (
    AL_MODELLO,
    ANNO_PASSATO,
    SCADUTO,
    SENZA_SCADENZA,
    motivo_scaduto,
    preselezione,
    scadenza_dichiarata,
)

PAGINE = Path(__file__).parent / "pagine"
OGGI = date(2026, 11, 11)
# L'etichetta del campo della scadenza per il portale della Regione: in
# produzione viene da fonti.etichetta_scadenza
CAMPO = "Data di scadenza presentazione domande"


def pagina(nome: str) -> str:
    return (PAGINE / f"{nome}.txt").read_text(encoding="utf-8")


# --- il campo sulle pagine salvate ---


def test_campo_con_la_data_in_lettere():
    assert scadenza_dichiarata(pagina("tpl"), CAMPO) == date(2021, 10, 21)


def test_campo_con_la_data_numerica_dopo_i_due_punti():
    assert scadenza_dichiarata(pagina("estero"), CAMPO) == date(2027, 12, 31)


def test_campo_che_non_e_una_data():
    assert scadenza_dichiarata(pagina("scuole-paritarie"), CAMPO) is None


def test_pagina_senza_campo():
    """I musei dicono la scadenza nel testo, non nel campo: decide il modello."""
    assert scadenza_dichiarata(pagina("musei"), CAMPO) is None


# --- i formati ---


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [
        (f"{CAMPO}\n31.12.2026", date(2026, 12, 31)),
        (f"{CAMPO}\n30.11.2026 13:00", date(2026, 11, 30)),
        (f"{CAMPO}:\n15.04.2027 23:59", date(2027, 4, 15)),
        (f"{CAMPO}: 22 ottobre 2021", date(2021, 10, 22)),
        (f"{CAMPO}\n5 Marzo 2024", date(2024, 3, 5)),
        # due volte la stessa data: vale
        (f"{CAMPO}\n31.12.2026\naltro\n{CAMPO}\n31.12.2026", date(2026, 12, 31)),
    ],
)
def test_formati_leggibili(testo, atteso):
    assert scadenza_dichiarata(testo, CAMPO) == atteso


@pytest.mark.parametrize(
    "testo",
    [
        f"{CAMPO}\nStato:",
        f"{CAMPO}\n31.12.2026 o fino a esaurimento delle risorse",
        f"{CAMPO}\n31.02.2026",
        f"{CAMPO}",
        # due date diverse: ambiguo
        f"{CAMPO}\n31.12.2026\n{CAMPO}\n31.01.2027",
        # un campo leggibile e uno no
        f"{CAMPO}\n31.12.2026\n{CAMPO}\nvedi avviso",
        "Scadenza presentazione domande: 21 ottobre 2021",
    ],
)
def test_valori_non_leggibili(testo):
    assert scadenza_dichiarata(testo, CAMPO) is None


# --- l'etichetta e' una regola della fonte ---

TERMINE = "Termine presentazione domande"


def test_etichetta_di_un_altra_fonte():
    testo = f"Importo a Bando\n710.624,00 €\n{TERMINE}\n31.12.2026\n"
    assert scadenza_dichiarata(testo, TERMINE) == date(2026, 12, 31)
    # con l'etichetta della Regione lo stesso testo non ha il campo
    assert scadenza_dichiarata(testo, CAMPO) is None


def test_fonte_senza_etichetta_non_ha_il_campo():
    """Un'etichetta vuota corrisponderebbe a ogni riga: nessuna data."""
    testo = f"{CAMPO}\n31.12.2026"
    assert scadenza_dichiarata(testo, None) is None
    assert scadenza_dichiarata(testo, "") is None
    assert preselezione(testo, True, OGGI, etichetta=None) == (AL_MODELLO, None)


@pytest.mark.parametrize(
    ("valore", "atteso"),
    [
        # come le scrive il sito del GAL MontagnAppennino
        ("ore 13.00 del 8 maggio 2026", date(2026, 5, 8)),
        ("PROROGATO alle ore 13.00 del 12 ottobre 2026", date(2026, 10, 12)),
        ("ore 12:00 del 27.06.2026", date(2026, 6, 27)),
    ],
)
def test_ora_prima_della_data(valore, atteso):
    assert scadenza_dichiarata(f"{TERMINE}\n{valore}", TERMINE) == atteso


@pytest.mark.parametrize(
    "valore",
    [
        "entro 60 giorni dal 1 gennaio 2026",
        "PROROGATO",
        "alle ore 13.00",
        "prorogato al 12 ottobre 2026 salvo esaurimento",
    ],
)
def test_ora_prima_della_data_resta_rigida(valore):
    assert scadenza_dichiarata(f"{TERMINE}\n{valore}", TERMINE) is None


# --- la preselezione ---


def test_scaduto_da_oltre_un_anno_non_va_al_modello():
    assert preselezione(pagina("tpl"), recente=True, oggi=OGGI, etichetta=CAMPO) == (
        SCADUTO,
        date(2021, 10, 21),
    )


def test_il_margine_e_di_un_anno():
    entro = f"{CAMPO}\n10.11.2025"  # 366 giorni prima
    sul_margine = f"{CAMPO}\n11.11.2025"  # 365 giorni prima
    assert preselezione(entro, True, OGGI, etichetta=CAMPO)[0] == SCADUTO
    assert preselezione(sul_margine, True, OGGI, etichetta=CAMPO)[0] == AL_MODELLO


def test_il_campo_vale_piu_dell_anno_nello_slug():
    slug = "lavorare-all-estero-borse-di-mobilit%C3%A0-il-bando-2023"
    assert not recente(slug, 2026)
    assert preselezione(
        pagina("estero"), recente=False, oggi=OGGI, etichetta=CAMPO
    ) == (
        AL_MODELLO,
        date(2027, 12, 31),
    )


def test_senza_campo_decide_l_anno_nello_slug():
    assert preselezione(pagina("musei"), recente=False, oggi=OGGI, etichetta=CAMPO) == (
        ANNO_PASSATO,
        None,
    )
    assert preselezione(pagina("musei"), recente=True, oggi=OGGI, etichetta=CAMPO) == (
        AL_MODELLO,
        None,
    )


def test_filtro_sull_anno_disattivabile():
    esito = preselezione(
        pagina("musei"), recente=False, oggi=OGGI, filtro_anni=False, etichetta=CAMPO
    )
    assert esito == (AL_MODELLO, None)


def test_il_motivo_e_uno_scarto_definitivo():
    motivo = motivo_scaduto(date(2021, 10, 21))
    assert motivo == "scaduto il 2021-10-21 (campo della pagina, senza modello)"
    assert any(motivo.startswith(d) for d in DEFINITIVI)


# --- l'anno nello slug ---


@pytest.mark.parametrize(
    ("slug", "anno"),
    [
        # il trattino tra due anni vale per entrambi
        ("incentivi-occupazione-annualit%C3%A0-2023-2025", 2025),
        ("bando-residenze-artistiche-2022-2024", 2024),
        ("bando-2026-2027-per-attivita", 2027),
        ("2021-bando", 2021),
        ("bando-2023", 2023),
        ("bando-12023-x", None),
        ("bando-20231", None),
        ("bando-senza-anno", None),
    ],
)
def test_anno_nello_slug(slug, anno):
    assert anno_slug(slug) == anno


def test_recente_tiene_l_anno_scorso():
    assert recente("bando-2025", 2026)
    assert not recente("bando-2024", 2026)
    assert recente("bando-senza-anno", 2026)


# --- fonti che richiedono la scadenza ---


def test_con_la_scadenza_obbligatoria_vince_lo_scaduto_dal_campo():
    """Il campo scaduto da oltre un anno resta uno scaduto, anche se la
    fonte richiede la scadenza."""
    assert preselezione(
        pagina("tpl"), True, OGGI, etichetta=CAMPO, scadenza_obbligatoria=True
    ) == (SCADUTO, date(2021, 10, 21))


def test_con_la_scadenza_obbligatoria_la_pagina_senza_campo_si_salta():
    """Prima del filtro sull'anno: lo slug non conta."""
    assert preselezione(
        pagina("musei"), False, OGGI, etichetta=CAMPO, scadenza_obbligatoria=True
    ) == (SENZA_SCADENZA, None)
