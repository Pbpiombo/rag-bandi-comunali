"""Registro delle scansioni, salvataggio dei bandi e lettura dell'elenco,
con gli URL in forma canonica."""

import sqlite3

import pytest

from src.estrazione import elenco
from src.estrazione.registro import da_non_riesaminare, registra
from src.estrazione.salva import ConflittoBando, conflitto, salva

TOSCANA = "regione-toscana"
BASE = "https://www.regione.toscana.it"
FONTE = "Portale bandi Regione Toscana"

# Estratto dell'elenco del portale, con i link nella forma reale: slug
# con "/" e con ".", un link ripetuto, una voce di servizio da escludere.
ELENCO_SALVATO = """
<a href="https://www.regione.toscana.it/-/bando-parcheggi-2026">Parcheggi</a>
<a href="https://www.regione.toscana.it/-/manifestazione-di-interesse-per-il-reperimento-di-patrimonio-immobiliare-da-destinare-ad-emergenza-abitativa-e/o-residenza-sociale-1">Emergenza</a>
<a href="https://www.regione.toscana.it/-/presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo">Museo</a>
<a href="https://www.regione.toscana.it/-/presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo-2024">Museo 2024</a>
<a href="https://www.regione.toscana.it/-/bando-legalita-scuole-a.s.-2025-26">Legalita</a>
<a href="https://www.regione.toscana.it/-/bando-parcheggi-2026">Parcheggi, di nuovo</a>
<a href="https://www.regione.toscana.it/-/accessibilita-e-uso-del-sito">Accessibilita</a>
"""


def _leggi(percorso, sql: str, parametri=()) -> list[sqlite3.Row]:
    c = sqlite3.connect(percorso)
    c.row_factory = sqlite3.Row
    try:
        return c.execute(sql, parametri).fetchall()
    finally:
        c.close()


def _riga(titolo: str = "Bando di prova") -> dict:
    return {
        "titolo": titolo,
        "ente": "Regione Toscana",
        "ammette_comuni": 1,
        "a_sportello": 0,
        "beneficiari": "Comuni",
    }


def _salva(id_bando: str, url: str, titolo: str = "Bando di prova") -> None:
    salva({**_riga(titolo), "id": id_bando}, url, FONTE, TOSCANA)


# --- salva: i tre casi di id e URL ---


def test_stesso_id_e_stesso_url_aggiorna(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Prima versione")
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Seconda versione")

    righe = _leggi(db_su_file, "SELECT id, titolo, codice_fonte FROM bandi")
    assert [tuple(r) for r in righe] == [
        ("parcheggi-2026", "Seconda versione", TOSCANA)
    ]


def test_stesso_id_con_url_diverso_e_rifiutato(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Originale")

    with pytest.raises(ConflittoBando, match="parcheggi-2026"):
        _salva("parcheggi-2026", f"{BASE}/-/altro-bando", "Intruso")

    righe = _leggi(db_su_file, "SELECT id, url, titolo FROM bandi")
    assert [tuple(r) for r in righe] == [
        ("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Originale")
    ]


def test_stesso_url_con_id_diverso_e_rifiutato(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Originale")

    with pytest.raises(ConflittoBando, match="parcheggi-2026"):
        _salva("bando-parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Intruso")

    righe = _leggi(db_su_file, "SELECT id, titolo FROM bandi")
    assert [tuple(r) for r in righe] == [("parcheggi-2026", "Originale")]


def test_il_conflitto_si_vede_anche_con_url_scritto_diversamente(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026")

    with pytest.raises(ConflittoBando):
        _salva("altro-id", "http://www.regione.toscana.it/-/bando-parcheggi-2026/")


def test_salva_scrive_url_canonico(db_su_file):
    _salva(
        "parcheggi-2026",
        "http://www.regione.toscana.it/-/bando-parcheggi-2026/?utm_source=x",
    )

    righe = _leggi(db_su_file, "SELECT url FROM bandi")
    assert righe[0]["url"] == f"{BASE}/-/bando-parcheggi-2026"


def test_conflitto_prima_di_salvare(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026")

    assert conflitto("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026") is None
    assert conflitto("nuovo-id", f"{BASE}/-/bando-nuovo") is None
    assert conflitto("parcheggi-2026", f"{BASE}/-/altro") is not None
    assert conflitto("altro-id", f"{BASE}/-/bando-parcheggi-2026/") is not None


# --- registro delle scansioni ---


def test_registra_due_volte_la_stessa_pagina_lascia_una_riga(db_su_file):
    registra(f"{BASE}/-/bando-x", TOSCANA, "bando-x", "fallito", "errore di rete")
    registra(
        f"{BASE}/-/bando-x/", TOSCANA, "bando-x", "scartato", "scaduto il 2025-01-01"
    )

    righe = _leggi(db_su_file, "SELECT url, esito, motivo FROM scansioni")
    assert [tuple(r) for r in righe] == [
        (f"{BASE}/-/bando-x", "scartato", "scaduto il 2025-01-01")
    ]


def test_da_non_riesaminare_restituisce_url_con_esito_definitivo(db_su_file):
    registra(
        f"{BASE}/-/scaduto", TOSCANA, "scaduto", "scartato", "scaduto il 2025-01-01"
    )
    registra(
        f"{BASE}/-/privati", TOSCANA, "privati", "scartato", "non ammette i Comuni"
    )
    registra(
        f"{BASE}/-/incerto", TOSCANA, "incerto", "scartato", "scadenza non determinata"
    )
    registra(f"{BASE}/-/rotto", TOSCANA, "rotto", "fallito", "scaduto il 2025-01-01")

    assert da_non_riesaminare() == {f"{BASE}/-/scaduto", f"{BASE}/-/privati"}


# --- lettura dell'elenco ---


@pytest.fixture
def elenco_salvato(monkeypatch):
    """L'elenco del portale letto dall'estratto salvato, non dal sito."""
    monkeypatch.setattr(elenco, "scarica", lambda url, timeout=30: ELENCO_SALVATO)


EMERGENZA = (
    "manifestazione-di-interesse-per-il-reperimento-di-patrimonio-"
    "immobiliare-da-destinare-ad-emergenza-abitativa-e/o-residenza-sociale-1"
)


def test_leggi_elenco_conserva_slug_con_barra_e_punto(elenco_salvato):
    assert elenco.leggi_elenco() == [
        "bando-parcheggi-2026",
        EMERGENZA,
        "presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo",
        "presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo-2024",
        "bando-legalita-scuole-a.s.-2025-26",
    ]


def test_scopri_riconosce_i_bandi_in_archivio_per_url(db_su_file, elenco_salvato):
    """Il bando con "/" nello slug, salvato con un id nostro, non e' nuovo."""
    url_emergenza = f"{BASE}/-/{EMERGENZA}"
    _salva("immobili-emergenza-abitativa-2026", url_emergenza)

    voci = {v.url: v for v in elenco.scopri()}

    assert not voci[url_emergenza].nuovo
    assert voci[f"{BASE}/-/bando-parcheggi-2026"].nuovo
    assert all(v.codice_fonte == TOSCANA for v in voci.values())
    assert len(voci) == 5


def test_gia_in_archivio_restituisce_url_canonici(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026")
    assert elenco.gia_in_archivio() == {f"{BASE}/-/bando-parcheggi-2026"}
