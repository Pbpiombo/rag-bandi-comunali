"""test degli funzioni enti.py che estraggono informazioni dalle tabelle"""

import sqlite3

import pytest

from src.chains.rag import ISTRUZIONI
from src.chains.router import descrivi_profilo
from src.database.enti import elenco_enti, profilo_ente
from src.database.schema import DDL, TABELLE_DA_CSV, carica_csv
from tests.conftest import CON_DATI, SENZA_DATI


def test_profilo_converte_booleani(conn):
    profilo = profilo_ente(conn, CON_DATI)
    assert profilo["capofila_area"] is False


def test_profilo_vuoto_non_verificato(conn):
    profilo = profilo_ente(conn, CON_DATI)
    assert profilo["toscana_diffusa"] is None


def test_ente_inesistente_alza_errore(conn):
    with pytest.raises(ValueError):
        profilo_ente(conn, "00000000000")


def test_elenco_in_ordine_alfabetico(conn):
    assert elenco_enti(conn) == [
        (CON_DATI, "Comune con dati"),
        (SENZA_DATI, "Comune senza dati"),
    ]


# --- Unione di appartenenza ---

UNIONE = "33333333333"


def _con_unione(conn) -> None:
    """Aggiunge un'Unione e vi iscrive il Comune con dati."""
    conn.execute(
        "INSERT INTO enti (codice_fiscale, nome, tipo, regione, provincia, fonte, "
        "verificato_il) VALUES (?, 'Unione di prova', 'unione', 'Toscana', "
        "'Pistoia', 'prova', '2026-01-01')",
        (UNIONE,),
    )
    conn.execute(
        "UPDATE enti SET unione = ?, fonte_unione = 'scheda di prova' "
        "WHERE codice_fiscale = ?",
        (UNIONE, CON_DATI),
    )
    conn.commit()


def test_profilo_del_comune_riporta_il_nome_dell_unione(conn):
    _con_unione(conn)
    assert profilo_ente(conn, CON_DATI)["unione"] == "Unione di prova"


def test_unione_non_in_archivio_e_non_verificata(conn):
    _con_unione(conn)
    profilo = profilo_ente(conn, SENZA_DATI)
    assert profilo["unione"] is None
    assert "- unione: non verificato" in descrivi_profilo(profilo)


def test_profilo_dell_unione_senza_il_campo(conn):
    _con_unione(conn)
    assert "unione" not in profilo_ente(conn, UNIONE)


def test_unione_senza_fonte_rifiutata(conn):
    _con_unione(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "UPDATE enti SET fonte_unione = NULL WHERE codice_fiscale = ?",
            (CON_DATI,),
        )


def test_unione_inesistente_rifiutata_alla_chiusura(conn):
    conn.execute(
        "UPDATE enti SET unione = '00000000000', fonte_unione = 'prova' "
        "WHERE codice_fiscale = ?",
        (CON_DATI,),
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.commit()


def test_lo_schema_carica_l_unione_dal_csv():
    """Il CSV vero, letto in un database in memoria: nel file i Comuni
    possono venire prima della loro Unione."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.executescript(DDL)
    assert carica_csv(c, "enti", TABELLE_DA_CSV["enti"]) == 4

    righe = c.execute(
        "SELECT e.tipo, u.nome AS nome_unione, e.fonte_unione FROM enti e "
        "LEFT JOIN enti u ON u.codice_fiscale = e.unione"
    ).fetchall()
    comuni = [r for r in righe if r["tipo"] == "comune"]
    assert len(comuni) == 3
    for r in comuni:
        assert r["nome_unione"] == "Unione di Comuni Montani Appennino Pistoiese"
        assert "regione.toscana.it" in r["fonte_unione"]
    unione = [r for r in righe if r["tipo"] == "unione"]
    assert [(r["nome_unione"], r["fonte_unione"]) for r in unione] == [(None, None)]
    c.close()


def test_istruzioni_distinguono_l_unione_dal_capofila_dell_area():
    # controllo debole: il comportamento si misura registrando
    assert "L'Unione dell'ente è quella del profilo" in ISTRUZIONI
    assert "capofila di un'area interna non è per questo" in ISTRUZIONI
