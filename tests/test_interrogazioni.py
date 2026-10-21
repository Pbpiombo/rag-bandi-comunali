"""Test delle interrogazioni sui dati: ogni ente vede solo i suoi."""

from src.database.interrogazioni_dati import popolazione_ultima
from src.database.repertorio import stato_archivio
from tests.conftest import CON_DATI, SENZA_DATI


def test_ente_con_dati_trova_la_popolazione(conn):
    esito = popolazione_ultima(conn, CON_DATI)
    assert esito.trovato
    assert "1834" in esito.testo


def test_ente_senza_dati_non_vede_altrui(conn):
    esito = popolazione_ultima(conn, SENZA_DATI)
    assert not esito.trovato
    assert "1834" not in esito.testo


def test_stato_archivio_per_ente_senza_dati(conn, monkeypatch):
    monkeypatch.setattr("src.database.repertorio.connetti", lambda: conn)
    stato = stato_archivio(SENZA_DATI)
    assert "popolazione: VUOTA" in stato
