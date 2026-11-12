"""Fonte GAL MontagnAppennino (piano fonti, tappa 4), sulle pagine salvate.

Le pagine in tests/pagine/gal-*.html sono il blocco <main> delle pagine
del sito, scaricate il 12 novembre 2026 (vedi LEGGIMI.md). Le regole di
lettura sono quelle vere, caricate da data/processed/fonti.csv.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

import scripts.ingestione.estrai_nuovi as estrai_nuovi
from src.estrazione import elenco
from src.estrazione.pagina import a_testo, ritaglia
from src.estrazione.scadenza import (
    AL_MODELLO,
    SENZA_SCADENZA,
    preselezione,
    scadenza_dichiarata,
)

PAGINE = Path(__file__).parent / "pagine"
GAL = "gal-montagnappennino"
BASE = "https://www.montagnappennino.it"
ELENCO_GAL = f"{BASE}/bandi-e-graduatorie"
TERMINE = "Termine presentazione domande"
OGGI = date(2026, 11, 12)

AS01 = "aso1-investimenti-non-produttivi-e-per-lo-sviluppo-socio-economico-delle-ree-rurali"
SRD14 = "srd-14-investimenti-produttivi-non-agricoli-in-aree-rurali"


def html(nome: str) -> str:
    return (PAGINE / f"{nome}.html").read_text(encoding="utf-8")


def pagina_come_testo(nome: str) -> str:
    return a_testo(html(nome))


@pytest.fixture
def fonte_gal(db_su_file) -> elenco.Fonte:
    return next(f for f in elenco.leggi_fonti() if f.codice == GAL)


@pytest.fixture
def solo_gal(db_su_file, monkeypatch):
    """Gli elenchi veri: quello del GAL dalla pagina salvata, gli altri vuoti."""
    scaricati = []

    def finto(url, timeout=30):
        scaricati.append(url)
        return html("gal-elenco") if url == ELENCO_GAL else ""

    monkeypatch.setattr(elenco, "scarica", finto)
    return scaricati


# --- la fonte nel database ---


def test_regole_della_fonte(fonte_gal):
    assert fonte_gal.tipo == "pagine"
    assert fonte_gal.dominio == "montagnappennino.it"
    assert fonte_gal.etichetta_scadenza == TERMINE
    assert not fonte_gal.filtro_anno_slug
    assert fonte_gal.scadenza_obbligatoria


# --- l'elenco ---


def test_l_elenco_da_le_quattro_pagine_di_bando(solo_gal):
    [letto] = [x for x in elenco.leggi_elenchi() if x.elenco.url == ELENCO_GAL]

    # nell'ordine della pagina, ogni collegamento una volta sola (il sito
    # li ripete: titolo, immagine, pulsante "Vai")
    assert letto.collegamenti == [
        (AS01, f"{BASE}/bando/{AS01}"),
        ("3451", f"{BASE}/bando/3451"),
        (SRD14, f"{BASE}/bando/{SRD14}"),
        ("3450", f"{BASE}/bando/3450"),
    ]


def test_voci_del_gal_con_la_loro_fonte(solo_gal):
    voci = [v for v in elenco.scopri() if v.codice_fonte == GAL]

    assert len(voci) == 4
    assert all(v.nuovo for v in voci)
    assert all(v.fonte.nome == "Sito GAL MontagnAppennino" for v in voci)
    # nessun allegato, nessuna pagina che non sia /bando/
    assert all(v.url.startswith(f"{BASE}/bando/") for v in voci)


def test_leggere_una_sola_fonte(solo_gal):
    letti = elenco.leggi_elenchi(GAL)

    assert [x.elenco.url for x in letti] == [ELENCO_GAL]
    assert solo_gal == [ELENCO_GAL]


# --- il testo delle pagine ---


def test_entita_convertite():
    t = pagina_come_testo("gal-as01")

    assert "&rsquo;" not in t and "&ldquo;" not in t
    assert "all’interno del territorio eligibile" in t
    assert "«" not in t  # nessuna conversione inventata
    assert "AS01 “Investimenti non produttivi" in t


@pytest.mark.parametrize(
    ("entita", "atteso"),
    [
        # quelle della tabella restano come prima: i testi della Regione non
        # cambiano
        ("a&nbsp;b", "a b"),
        ("a&ndash;b", "a-b"),
        ("a&mdash;b", "a-b"),
        ("10&euro;", "10€"),
        ("&#8364;", "€"),
        # le altre, nuove
        ("dell&rsquo;ente", "dell’ente"),
        ("&ldquo;x&rdquo;", "“x”"),
        ("&Eacute;", "É"),
        ("&copy; 2026", "© 2026"),
    ],
)
def test_a_testo_converte_le_entita(entita, atteso):
    assert a_testo(f"<p>{entita}</p>") == atteso


@pytest.mark.parametrize("nome", ["gal-as01", "gal-srd14"])
def test_il_ritaglio_conserva_i_dati_ordinati(nome):
    r = ritaglia(pagina_come_testo(nome))
    for etichetta in (
        TERMINE,
        "Importo a Bando",
        "A chi si rivolge",
        "Contributo minimo",
        "Contributo massimo",
        "Tasso di sostegno",
    ):
        assert etichetta in r


# --- la scadenza senza modello ---


def test_scadenza_di_as01_e_quella_della_proroga():
    """Il 18/09 della prima scadenza non c'e': vale il campo prorogato."""
    assert scadenza_dichiarata(pagina_come_testo("gal-as01"), TERMINE) == date(
        2026, 10, 12
    )


def test_scadenza_di_srd14():
    assert scadenza_dichiarata(pagina_come_testo("gal-srd14"), TERMINE) == date(
        2026, 5, 8
    )


def test_la_pagina_vuota_non_ha_scadenza():
    assert scadenza_dichiarata(pagina_come_testo("gal-vuota"), TERMINE) is None


def test_pagina_vuota_saltata_solo_se_la_fonte_richiede_la_scadenza():
    t = pagina_come_testo("gal-vuota")
    comune = {"recente": True, "oggi": OGGI, "filtro_anni": False, "etichetta": TERMINE}

    assert preselezione(t, **comune, scadenza_obbligatoria=True) == (
        SENZA_SCADENZA,
        None,
    )
    assert preselezione(t, **comune) == (AL_MODELLO, None)


def test_scaduti_da_meno_di_un_anno_vanno_al_modello():
    """AS01 e SRD14 sono scaduti da meno di un anno: storico, non scarto."""
    for nome, scadenza in (
        ("gal-as01", date(2026, 10, 12)),
        ("gal-srd14", date(2026, 5, 8)),
    ):
        assert preselezione(
            pagina_come_testo(nome),
            recente=True,
            oggi=OGGI,
            filtro_anni=False,
            etichetta=TERMINE,
            scadenza_obbligatoria=True,
        ) == (AL_MODELLO, scadenza)


# --- il percorso della preselezione di estrai_nuovi ---


def test_preselezione_del_gal(solo_gal, monkeypatch, capsys):
    pagine = {
        f"{BASE}/bando/3450": html("gal-vuota"),
        f"{BASE}/bando/3451": html("gal-vuota"),
        f"{BASE}/bando/{AS01}": html("gal-as01"),
        f"{BASE}/bando/{SRD14}": html("gal-srd14"),
    }
    monkeypatch.setattr(estrai_nuovi, "scarica", lambda url: pagine[url])
    monkeypatch.setattr(estrai_nuovi.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["estrai_nuovi", "--prova"])
    voci = [v for v in elenco.scopri() if v.codice_fonte == GAL]

    candidati, _ = estrai_nuovi.preseleziona(voci, prova=True)

    assert [v.slug for v, _ in candidati] == [AS01, SRD14]
    uscita = capsys.readouterr().out
    assert "saltati senza scadenza leggibile, in fonti che la richiedono: 2" in uscita
