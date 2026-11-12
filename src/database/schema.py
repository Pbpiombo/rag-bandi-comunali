"""Creazione e popolamento del database dei dati numerici."""

import csv
import sqlite3

from src.config import PROCESSED_DIR, SQLITE_PATH
from src.estrazione.beneficiari import ORIGINI, PER_REQUISITO, TIPI_BENEFICIARIO


def _elenco_sql(valori) -> str:
    """Un elenco di stringhe per una clausola IN: 'a', 'b', 'c'."""
    return ", ".join(f"'{v}'" for v in valori)


# I segnaposto {TIPI}, {ORIGINI} e {PER_REQUISITO} vengono riempiti
# subito sotto con le liste chiuse di src/estrazione/beneficiari.py
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
    codice_ente         TEXT NOT NULL REFERENCES enti(codice_fiscale),
    anno                INTEGER NOT NULL,
    residenti           INTEGER NOT NULL,
    fonte               TEXT NOT NULL,
    data_rilevazione    TEXT,
    PRIMARY KEY (codice_ente, anno)
);

CREATE TABLE IF NOT EXISTS bilancio (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codice_ente     TEXT NOT NULL REFERENCES enti(codice_fiscale),
    anno            INTEGER NOT NULL,
    tipo            TEXT NOT NULL CHECK (tipo IN ('entrata', 'spesa')),
    voce            TEXT NOT NULL,
    importo         REAL NOT NULL,
    fonte           TEXT NOT NULL,
    UNIQUE (codice_ente, anno, tipo, voce)
);

CREATE TABLE IF NOT EXISTS turismo (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codice_ente     TEXT NOT NULL REFERENCES enti(codice_fiscale),
    anno            INTEGER NOT NULL,
    mese            INTEGER CHECK (mese BETWEEN 1 AND 12),
    arrivi          INTEGER,
    presenze        INTEGER,
    fonte           TEXT NOT NULL,
    UNIQUE (codice_ente, anno, mese)
);

CREATE TABLE IF NOT EXISTS territorio (
    codice_ente     TEXT NOT NULL REFERENCES enti(codice_fiscale),
    chiave          TEXT NOT NULL,
    valore          REAL NOT NULL,
    unita           TEXT,
    fonte           TEXT NOT NULL,
    PRIMARY KEY     (codice_ente, chiave)
);

-- I siti da cui si acquisiscono i bandi. nome e' il testo citato come
-- fonte del bando; fonte e verificato_il dicono da dove sappiamo che il
-- sito e' quello ufficiale.
CREATE TABLE IF NOT EXISTS fonti (
    codice          TEXT PRIMARY KEY,
    nome            TEXT NOT NULL,
    url_elenco      TEXT NOT NULL,
    url_base        TEXT NOT NULL,
    fonte           TEXT NOT NULL,
    verificato_il   TEXT NOT NULL
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

    beneficiari         TEXT NOT NULL,
    territorio          TEXT,
    premialita          TEXT,

    costo_min           REAL,
    costo_max           REAL,
    contributo_perc     REAL,
    contributo_min      REAL,
    contributo_max      REAL,
    dotazione           REAL,

    url                 TEXT NOT NULL UNIQUE,
    riferimento_atto    TEXT,
    fonte               TEXT NOT NULL,
    codice_fonte        TEXT NOT NULL REFERENCES fonti(codice),
    verificato_il       TEXT NOT NULL,

    -- clausola sul cumulo con altri finanziamenti, e la frase che la dice
    cumulabilita        TEXT,
    cumulabilita_frase  TEXT,
    -- data in cui i beneficiari sono stati classificati per tipo;
    -- vuota per i bandi che conoscono solo se ammettono i Comuni
    classificato_il     TEXT,
    -- data di pubblicazione del bando: per i bandi a sportello senza
    -- chiusura e' l'unico indizio di quanto siano vecchi. L'origine dice se
    -- e' la pubblicazione vera o la data dell'atto che approva il bando.
    pubblicato_il       TEXT,
    pubblicato_origine  TEXT
                        CHECK (pubblicato_origine IN ('pubblicazione', 'atto')),
    -- una pagina in archivio che il modello giudica non un bando (es. una
    -- graduatoria): resta in archivio, ma non compare tra le opportunita'
    natura              TEXT NOT NULL DEFAULT 'bando'
                        CHECK (natura IN ('bando', 'non_bando')),
    natura_motivo       TEXT
);

-- Chi puo' presentare domanda, per tipo di beneficiario (lista chiusa in
-- src/estrazione/beneficiari.py), con le condizioni e la frase del bando.
-- origine 'ammette_comuni': riga ricavata dal vecchio campo si'/no, che
-- diceva solo se i Comuni erano ammessi.
CREATE TABLE IF NOT EXISTS beneficiari_bando (
    id_bando        TEXT NOT NULL REFERENCES bandi(id),
    tipo            TEXT NOT NULL CHECK (tipo IN ({TIPI})),
    soggetto        TEXT,
    condizioni      TEXT,
    frase           TEXT NOT NULL,
    confidenza      TEXT CHECK (confidenza IN ('alta', 'media', 'bassa')),
    origine         TEXT NOT NULL CHECK (origine IN ({ORIGINI})),
    PRIMARY KEY (id_bando, tipo, frase),
    CHECK (tipo <> '{PER_REQUISITO}' OR condizioni IS NOT NULL)
);

-- Interventi e spese ammissibili, ciascuno con la frase del bando
CREATE TABLE IF NOT EXISTS interventi_bando (
    id_bando        TEXT NOT NULL REFERENCES bandi(id),
    numero          INTEGER NOT NULL,
    genere          TEXT NOT NULL CHECK (genere IN ('intervento', 'spesa')),
    descrizione     TEXT NOT NULL,
    frase           TEXT NOT NULL,
    PRIMARY KEY (id_bando, numero)
);

-- Le date di un bando a finestre o con piu' scadenze, solo per i bandi con
-- piu' date. genere 'domanda': un periodo in cui si presenta domanda (una
-- finestra, o una misura con la sua scadenza); 'fase_successiva': una
-- scadenza per chi ha gia' superato una fase, che non apre il bando a
-- nuove domande. bandi.scadenza resta l'ultima scadenza 'domanda'.
CREATE TABLE IF NOT EXISTS scadenze_bando (
    id_bando        TEXT NOT NULL REFERENCES bandi(id),
    numero          INTEGER NOT NULL,
    genere          TEXT NOT NULL CHECK (genere IN ('domanda', 'fase_successiva')),
    descrizione     TEXT NOT NULL,
    apertura        TEXT,
    scadenza        TEXT NOT NULL,
    frase           TEXT NOT NULL,
    PRIMARY KEY (id_bando, numero),
    CHECK (apertura IS NULL OR apertura <= scadenza)
);

-- Le pagine gia' esaminate. La chiave e' l'URL in forma canonica, unico
-- tra tutte le fonti; lo slug resta solo come informazione leggibile.
CREATE TABLE IF NOT EXISTS scansioni (
    url             TEXT PRIMARY KEY,
    codice_fonte    TEXT NOT NULL REFERENCES fonti(codice),
    slug            TEXT,
    esito          TEXT NOT NULL CHECK (esito IN ('salvato', 'scartato', 'fallito')),
    motivo          TEXT,
    -- campi non bloccanti rimasti vuoti, con il valore originale
    avvisi          TEXT,
    esaminato_il    TEXT NOT NULL
);
"""

DDL = (
    DDL.replace("{TIPI}", _elenco_sql(TIPI_BENEFICIARIO))
    .replace("{ORIGINI}", _elenco_sql(ORIGINI))
    .replace("{PER_REQUISITO}", PER_REQUISITO)
)

TABELLE_DA_CSV = {
    "enti": [
        "codice_fiscale",
        "nome",
        "tipo",
        "codice_istat",
        "regione",
        "provincia",
        "area_interna",
        "capofila_area",
        "toscana_diffusa",
        "fonte",
        "verificato_il",
    ],
    "popolazione": ["codice_ente", "anno", "residenti", "fonte", "data_rilevazione"],
    "bilancio": ["codice_ente", "anno", "tipo", "voce", "importo", "fonte"],
    "turismo": ["codice_ente", "anno", "mese", "arrivi", "presenze", "fonte"],
    "territorio": ["codice_ente", "chiave", "valore", "unita", "fonte"],
    # fonti va caricata prima di bandi e scansioni, che vi fanno riferimento
    "fonti": ["codice", "nome", "url_elenco", "url_base", "fonte", "verificato_il"],
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
        "codice_fonte",
        "verificato_il",
        "cumulabilita",
        "cumulabilita_frase",
        "classificato_il",
        "pubblicato_il",
        "pubblicato_origine",
        "natura",
        "natura_motivo",
    ],
    # beneficiari_bando, interventi_bando e scadenze_bando dopo bandi, a cui
    # fanno riferimento
    "beneficiari_bando": [
        "id_bando",
        "tipo",
        "soggetto",
        "condizioni",
        "frase",
        "confidenza",
        "origine",
    ],
    "interventi_bando": ["id_bando", "numero", "genere", "descrizione", "frase"],
    "scadenze_bando": [
        "id_bando",
        "numero",
        "genere",
        "descrizione",
        "apertura",
        "scadenza",
        "frase",
    ],
    "scansioni": [
        "url",
        "codice_fonte",
        "slug",
        "esito",
        "motivo",
        "avvisi",
        "esaminato_il",
    ],
}


def connetti() -> sqlite3.Connection:
    """Apre la connessione, creando la cartella se serve."""
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(SQLITE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
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

    inserite = 0
    scartate = 0

    with percorso.open(encoding="utf-8-sig", newline="") as f:
        lettore = csv.DictReader(f)
        # Una colonna aggiunta allo schema dopo il CSV non c'e' nel file:
        # si lascia fuori dall'inserimento, cosi' prende il valore
        # predefinito invece di un NULL esplicito
        colonne = [c for c in colonne if c in (lettore.fieldnames or [])]
        segnaposto = ", ".join("?" for _ in colonne)
        elenco = ", ".join(colonne)
        sql = f"INSERT OR REPLACE INTO {tabella} ({elenco}) VALUES ({segnaposto})"

        for numero, riga in enumerate(lettore, start=2):
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


def chiave_primaria(conn: sqlite3.Connection, tabella: str) -> list[str]:
    """Le colonne della chiave primaria di una tabella, nel loro ordine."""
    # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
    info = conn.execute(f"PRAGMA table_info({tabella})").fetchall()
    return [r[1] for r in sorted((r for r in info if r[5]), key=lambda r: r[5])]


def esporta_csv(conn: sqlite3.Connection, tabella: str, colonne: list[str]) -> int:
    """Riscrive il CSV di data/processed con il contenuto attuale della tabella.

    Le righe sono in ordine di chiave primaria: lo stesso contenuto da' lo
    stesso file, e i diff dei CSV mostrano solo i dati cambiati.
    """
    percorso = PROCESSED_DIR / f"{tabella}.csv"
    elenco = ", ".join(colonne)
    ordine = ", ".join(chiave_primaria(conn, tabella)) or colonne[0]
    righe = conn.execute(f"SELECT {elenco} FROM {tabella} ORDER BY {ordine}").fetchall()

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
