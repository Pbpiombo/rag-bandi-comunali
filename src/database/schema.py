"""Creazione e popolamento del database dei dati numerici."""

import csv
import sqlite3

from src.config import PROCESSED_DIR, SQLITE_PATH

DDL = """
CREATE TABLE IF NOT EXISTS enti (
    codice_fiscale  TEXT PRIMARY KEY,
    nome            TEXT NOT NULL,
    tipo            TEXT NOT NULL 
                    CHECK (tipo IN ('comune', 'unione')),
    codice_istat    TEXT,
    regione         TEXT NOT NULL,
    provincia       TEXT NOT NULL,
    area_interna    TEXT,
    capofila_area   INTEGER NOT NULL DEFAULT 0
                    CHECK(capofila_area IN (0,1)),
    toscana_diffusa INTEGER
                    CHECK(toscana_diffusa IN (0,1)),
    fonte           TEXT NOT NULL,
    verificato_il   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS popolazione (
    anno                INTEGER PRIMARY KEY,
    residenti           INTEGER NOT NULL,
    fonte               TEXT NOT NULL,
    data_rilevazione    TEXT
);

CREATE TABLE IF NOT EXISTS bilancio (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    anno        INTEGER NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('entrata', 'spesa')),
    voce        TEXT NOT NULL,
    importo     REAL NOT NULL,
    fonte       TEXT NOT NULL,
    UNIQUE (anno, tipo, voce)
);

CREATE TABLE IF NOT EXISTS turismo (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    anno        INTEGER NOT NULL,
    mese        INTEGER CHECK (mese BETWEEN 1 AND 12),
    arrivi      INTEGER,
    presenze    INTEGER,
    fonte       TEXT NOT NULL,
    UNIQUE (anno, mese)
);

CREATE TABLE IF NOT EXISTS territorio (
    chiave      TEXT PRIMARY KEY,
    valore      REAL NOT NULL,
    unita       TEXT,
    fonte       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bandi (
    id                  TEXT PRIMARY KEY,
    titolo              TEXT NOT NULL,
    ente                TEXT NOT NULL,
    tema                TEXT,
    programma           TEXT,

    apertura            TEXT,
    scadenza            TEXT,
    scadenza_nota       TEXT,
    a_sportello         INTEGER NOT NULL DEFAULT 0
                        CHECK (a_sportello IN (0, 1)),

    ammette_comuni      INTEGER NOT NULL
                        CHECK (ammette_comuni IN (0, 1)),
    beneficiari         TEXT NOT NULL,
    territorio          TEXT,
    premialita          TEXT,

    costo_min           REAL,
    costo_max           REAL,
    contributo_perc     REAL,
    contributo_min      REAL,
    contributo_max      REAL,
    dotazione           REAL,

    url                 TEXT NOT NULL,
    riferimento_atto    TEXT,
    fonte               TEXT NOT NULL,
    verificato_il       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS scansioni (
    slug            TEXT PRIMARY KEY,
    esito           TEXT NOT NULL CHECK (esito IN ('salvato', 'scartato', 'fallito')),
    motivo          TEXT,
    esaminato_il    TEXT NOT NULL
);
"""

TABELLE_DA_CSV = {
    "enti": ["codice_fiscale",
             "nome",
             "tipo",
             "codice_istat",
             "regione",
             "provincia",
             "area_interna",
             "capofila_area",
             "toscana_diffusa",
             "fonte",
             "verificato_il"],
    "popolazione": ["anno", "residenti", "fonte", "data_rilevazione"],
    "bilancio": ["anno", "tipo", "voce", "importo", "fonte"],
    "turismo": ["anno", "mese", "arrivi", "presenze", "fonte"],
    "territorio": ["chiave", "valore", "unita", "fonte"],
    "bandi": [
        "id",
        "titolo",
        "ente",
        "tema",
        "programma",
        "apertura",
        "scadenza",
        "scadenza_nota",
        "a_sportello",
        "ammette_comuni",
        "beneficiari",
        "territorio",
        "premialita",
        "costo_min",
        "costo_max",
        "contributo_perc",
        "contributo_min",
        "contributo_max",
        "dotazione",
        "url",
        "riferimento_atto",
        "fonte",
        "verificato_il",
    ],
    "scansioni": ["slug", "esito", "motivo", "esaminato_il"]
}


def connetti() -> sqlite3.Connection:
    """Apre la connessione, creando la cartella se serve."""
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def crea_schema(conn: sqlite3.Connection) -> None:
    """Crea le tabelle se non esistono."""
    conn.executescript(DDL)
    conn.commit()
    print(f"  Schema creato in {SQLITE_PATH}")


def carica_csv(conn: sqlite3.Connection, tabella: str, colonne: list[str]) -> int:
    """Carica un CSV da data/processed, se presente."""
    percorso = PROCESSED_DIR / f"{tabella}.csv"

    if not percorso.exists():
        print(f"  [saltato] {percorso.name} non presente")
        return 0

    segnaposto = ", ".join("?" for _ in colonne)
    elenco = ", ".join(colonne)
    sql = f"INSERT OR REPLACE INTO {tabella} ({elenco}) VALUES ({segnaposto})"

    inserite = 0
    scartate = 0

    with percorso.open(encoding="utf-8-sig", newline="") as f:
        for numero, riga in enumerate(csv.DictReader(f), start=2):
            valori = [riga.get(c) or None for c in colonne]

            try:
                conn.execute(sql, valori)
                inserite += 1
            except sqlite3.IntegrityError as errore:
                scartate += 1
                print(f"    riga {numero} scartata: {errore}")

    conn.commit()

    messaggio = f"  {tabella}: {inserite} righe caricate"
    if scartate:
        messaggio += f", {scartate} scartate"
    print(messaggio + f" da {percorso.name}")

    return inserite


def _per_csv(valore):
    """Riporta a intero un decimale senza parte frazionaria: 1200.0 diventa 1200."""
    if isinstance(valore, float) and valore.is_integer():
        return int(valore)
    return valore


def esporta_csv(conn: sqlite3.Connection, tabella: str, colonne: list[str]) -> int:
    """Riscrive il CSV di data/processed con il contenuto attuale della tabella."""
    percorso = PROCESSED_DIR / f"{tabella}.csv"
    elenco = ", ".join(colonne)
    righe = conn.execute(
        f"SELECT {elenco} FROM {tabella} ORDER BY {colonne[0]}"
    ).fetchall()

    with percorso.open("w", encoding="utf-8-sig", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=colonne)
        scrittore.writeheader()
        for riga in righe:
            scrittore.writerow({c: _per_csv(riga[c]) for c in colonne})

    print(f"  {tabella}: {len(righe)} righe esportate in {percorso.name}")
    return len(righe)


def aggiorna_csv(*tabelle: str) -> None:
    """Riversa nei CSV il contenuto attuale delle tabelle indicate."""
    conn = connetti()
    try:
        for tabella in tabelle:
            esporta_csv(conn, tabella, TABELLE_DA_CSV[tabella])
    finally:
        conn.close()
        

def riepilogo(conn: sqlite3.Connection) -> None:
    """Stampa quante righe contiene ogni tabella."""
    print("\n  Contenuto del database:")
    for tabella in TABELLE_DA_CSV:
        quante = conn.execute(f"SELECT COUNT(*) FROM {tabella}").fetchone()[0]
        print(f"    {tabella:14} {quante} righe")
