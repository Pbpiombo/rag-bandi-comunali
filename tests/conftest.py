import sqlite3

import pytest

from src.database.schema import DDL, TABELLE_DA_CSV, carica_csv

CON_DATI = "11111111111"
SENZA_DATI = "22222222222"


@pytest.fixture
def conn():
    """Un database in memoria con due enti, e la popolazione di uno solo."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.executescript(DDL)
    c.executemany(
        "INSERT INTO enti (codice_fiscale, nome, tipo, regione, provincia, fonte, verificato_il) "
        "VALUES (?, ?, 'comune', 'Toscana', 'Pistoia', 'prova', '2026-01-01')",
        [(CON_DATI, "Comune con dati"), (SENZA_DATI, "Comune senza dati")],
    )
    c.execute(
        "INSERT INTO popolazione (codice_ente, anno, residenti, fonte) VALUES (?, 2026, 1834, 'prova')",
        (CON_DATI,),
    )
    yield c
    c.close()


@pytest.fixture
def db_su_file(tmp_path, monkeypatch):
    """Un database su file temporaneo, al posto di quello vero.

    Serve al codice che apre la connessione da se' con connetti(), come
    registra() e salva(). Contiene lo schema e le fonti e gli elenchi
    veri, caricati da data/processed: i test leggono le pagine con le
    regole che usa la scansione.
    """
    percorso = tmp_path / "prova.sqlite"
    monkeypatch.setattr("src.database.schema.SQLITE_PATH", percorso)

    c = sqlite3.connect(percorso)
    c.execute("PRAGMA foreign_keys = ON")
    c.executescript(DDL)
    for tabella in ("fonti", "elenchi"):
        carica_csv(c, tabella, TABELLE_DA_CSV[tabella])
    c.close()
    return percorso
