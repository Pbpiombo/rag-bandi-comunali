"""Creazione e popolamento del database dei dati numerici."""

import csv
import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from src.config import DATA_DIR, PROCESSED_DIR, SQLITE_PATH
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
    verificato_il   TEXT NOT NULL,
    -- l'Unione di cui il Comune fa parte, con la fonte dell'appartenenza.
    -- Il vincolo e' differito: nel CSV un Comune puo' venire prima della
    -- sua Unione, e il controllo si fa alla chiusura del caricamento
    unione          TEXT REFERENCES enti(codice_fiscale)
                    DEFERRABLE INITIALLY DEFERRED,
    fonte_unione    TEXT,
    CHECK (unione IS NULL OR fonte_unione IS NOT NULL)
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
-- sito e' quello ufficiale, e quando e' stato controllato il robots.txt.
--
-- tipo 'pagine': i bandi si scoprono dagli elenchi web della tabella
-- elenchi e si leggono pagina per pagina, con le regole qui sotto.
-- tipo 'file': un file scaricato a mano e letto dal codice; non ha
-- elenchi da scansionare.
--
-- Le regole di lettura di una fonte 'pagine' (src/estrazione/elenco.py):
--   url_base: dominio dei collegamenti accettati, e base degli URL;
--   schema_link: espressione sul percorso del collegamento, con i gruppi
--     'percorso' (la parte dopo url_base) e 'slug' (in fondo a percorso);
--   esclusi: espressione sugli slug da ignorare (voci di servizio);
--   etichetta_scadenza: il campo della pagina con la data di scadenza,
--     letto senza modello dalla preselezione (src/estrazione/scadenza.py);
--   filtro_anno_slug: una pagina senza scadenza leggibile e con un anno
--     passato nello slug si salta;
--   scadenza_obbligatoria: una pagina senza scadenza leggibile non e' un
--     bando di questa fonte, e si salta senza modello.
CREATE TABLE IF NOT EXISTS fonti (
    codice                  TEXT PRIMARY KEY,
    nome                    TEXT NOT NULL,
    tipo                    TEXT NOT NULL DEFAULT 'pagine'
                            CHECK (tipo IN ('pagine', 'file')),
    url_base                TEXT NOT NULL,
    schema_link             TEXT,
    esclusi                 TEXT,
    etichetta_scadenza      TEXT,
    filtro_anno_slug        INTEGER NOT NULL DEFAULT 0
                            CHECK (filtro_anno_slug IN (0, 1)),
    scadenza_obbligatoria   INTEGER NOT NULL DEFAULT 0
                            CHECK (scadenza_obbligatoria IN (0, 1)),
    fonte                   TEXT NOT NULL,
    verificato_il           TEXT NOT NULL,
    CHECK (tipo = 'file' OR schema_link IS NOT NULL)
);

-- Le pagine da cui si scoprono i bandi di una fonte: piu' elenchi per la
-- stessa fonte. Per una fonte 'file', la pagina da cui il file si
-- scarica, con attivo = 0. fonte e verificato_il come in fonti.
CREATE TABLE IF NOT EXISTS elenchi (
    url             TEXT PRIMARY KEY,
    codice_fonte    TEXT NOT NULL REFERENCES fonti(codice),
    nome            TEXT NOT NULL,
    attivo          INTEGER NOT NULL DEFAULT 1 CHECK (attivo IN (0, 1)),
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

    -- vuoto se la pagina non dice chi puo' presentare domanda: il bando si
    -- salva comunque e compare tra quelli da approfondire
    beneficiari         TEXT,
    -- la frase della pagina che rimanda all'avviso per i requisiti, se i
    -- beneficiari non sono sulla pagina
    beneficiari_rimando TEXT,
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
    -- e' la pubblicazione vera o la data dell'atto che approva il bando;
    -- 'apertura': la data di apertura del catalogo Incentivi Italia.
    pubblicato_il       TEXT,
    pubblicato_origine  TEXT
                        CHECK (pubblicato_origine IN ('pubblicazione', 'atto', 'apertura')),
    -- una pagina in archivio che il modello giudica non un bando (es. una
    -- graduatoria): resta in archivio, ma non compare tra le opportunita'
    natura              TEXT NOT NULL DEFAULT 'bando'
                        CHECK (natura IN ('bando', 'non_bando')),
    natura_motivo       TEXT,
    -- contatti d'ufficio letti dal codice sulla pagina (src/estrazione/
    -- contatti.py): mai nomi o email di persone. Vuoto: vedi la pagina
    contatti            TEXT,
    contatti_letti_il   TEXT
);

-- Chi puo' presentare domanda, per tipo di beneficiario (lista chiusa in
-- src/estrazione/beneficiari.py), con le condizioni e la frase del bando.
-- origine 'ammette_comuni': riga ricavata dal vecchio campo si'/no, che
-- diceva solo se i Comuni erano ammessi; 'manuale': riga inserita a mano,
-- con la frase letta sulla pagina del bando.
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
-- origine 'manuale': righe lette a mano dalla pagina, che una nuova
-- estrazione non sostituisce mai; le date diverse proposte dal modello si
-- elencano da rivedere.
CREATE TABLE IF NOT EXISTS scadenze_bando (
    id_bando        TEXT NOT NULL REFERENCES bandi(id),
    numero          INTEGER NOT NULL,
    genere          TEXT NOT NULL CHECK (genere IN ('domanda', 'fase_successiva')),
    descrizione     TEXT NOT NULL,
    apertura        TEXT,
    scadenza        TEXT NOT NULL,
    frase           TEXT NOT NULL,
    origine         TEXT NOT NULL DEFAULT 'estrazione'
                    CHECK (origine IN ('estrazione', 'manuale')),
    PRIMARY KEY (id_bando, numero),
    CHECK (apertura IS NULL OR apertura <= scadenza)
);

-- Le sospensioni di un bando, una riga per periodo. Lo stato si calcola
-- dalla scadenza, che una sospensione non cambia: qui sta il dato che la
-- dice. ambito 'tutto': non si presentano domande; 'in_parte': sospeso per
-- alcune categorie (sospesi), aperto per altre (resta_aperto). Un periodo
-- vale dal giorno sospeso_dal fino al giorno prima di riaperto_il; senza
-- riaperto_il e' in corso. La riapertura riempie riaperto_il e
-- riapertura_frase sulla stessa riga. Si scrive solo a mano, con le frasi
-- di prova trovate nel testo salvato (scripts/manutenzione/
-- correggi_da_testo.py): l'estrazione non la scrive.
CREATE TABLE IF NOT EXISTS sospensioni_bando (
    id_bando          TEXT NOT NULL REFERENCES bandi(id),
    numero            INTEGER NOT NULL,
    ambito            TEXT NOT NULL CHECK (ambito IN ('tutto', 'in_parte')),
    sospeso_dal       TEXT NOT NULL,
    sospesi           TEXT,
    resta_aperto      TEXT,
    atto              TEXT NOT NULL,
    frase             TEXT NOT NULL CHECK (frase <> ''),
    riaperto_il       TEXT,
    riapertura_frase  TEXT CHECK (riapertura_frase <> ''),
    verificato_il     TEXT NOT NULL,
    origine           TEXT NOT NULL DEFAULT 'manuale'
                      CHECK (origine IN ('manuale')),
    PRIMARY KEY (id_bando, numero),
    CHECK (ambito = 'tutto' OR (sospesi IS NOT NULL AND resta_aperto IS NOT NULL)),
    CHECK (ambito = 'in_parte' OR resta_aperto IS NULL),
    CHECK ((riaperto_il IS NULL) = (riapertura_frase IS NULL)),
    CHECK (riaperto_il IS NULL OR riaperto_il > sospeso_dal)
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
        "unione",
        "fonte_unione",
    ],
    "popolazione": ["codice_ente", "anno", "residenti", "fonte", "data_rilevazione"],
    "bilancio": ["codice_ente", "anno", "tipo", "voce", "importo", "fonte"],
    "turismo": ["codice_ente", "anno", "mese", "arrivi", "presenze", "fonte"],
    "territorio": ["codice_ente", "chiave", "valore", "unita", "fonte"],
    # fonti va caricata prima di elenchi, bandi e scansioni, che vi fanno
    # riferimento
    "fonti": [
        "codice",
        "nome",
        "tipo",
        "url_base",
        "schema_link",
        "esclusi",
        "etichetta_scadenza",
        "filtro_anno_slug",
        "scadenza_obbligatoria",
        "fonte",
        "verificato_il",
    ],
    "elenchi": ["url", "codice_fonte", "nome", "attivo", "fonte", "verificato_il"],
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
        "beneficiari_rimando",
        "contatti",
        "contatti_letti_il",
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
        "origine",
    ],
    "sospensioni_bando": [
        "id_bando",
        "numero",
        "ambito",
        "sospeso_dal",
        "sospesi",
        "resta_aperto",
        "atto",
        "frase",
        "riaperto_il",
        "riapertura_frase",
        "verificato_il",
        "origine",
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


# I CSV di data/processed che entrano nella copia congelata (e quindi
# nell'impronta dell'archivio) ma non si caricano in SQLite: nessuna
# interrogazione del repertorio li legge. testo_ricerca: il testo per
# l'ordinamento dei bandi (passo 17 della roadmap), che non va al modello
# che scrive e non si cita (src/ordinamento/testo_ricerca.py).
# documenti_bandi: il registro dei PDF degli avvisi scaricati, una riga per
# impronta del file (passo 19, scripts/ingestione/registra_avvisi.py).
CSV_FUORI_DATABASE = ("testo_ricerca", "documenti_bandi")

# Le tabelle di TABELLE_DA_CSV nate dopo la prima copia congelata
# (dati-grezzi/archivi/2026-11-24_e26e2e30/), che non le contiene: una copia
# non si modifica mai. crea_da_csv le accetta assenti e le lascia vuote;
# per tutte le altre un CSV mancante resta un errore. sospensioni_bando:
# dal 24/11/2026.
TABELLE_DOPO_LA_COPIA = ("sospensioni_bando",)


class ErroreArchivio(Exception):
    """Un archivio di CSV da cui non si puo' creare il database."""


# Il database aperto da connetti al posto di SQLITE_PATH, dentro archivio_da.
# Si imposta solo da codice, dentro un blocco with: nessuna variabile
# d'ambiente o configurazione lo attiva, e l'app non lo usa.
_PERCORSO_ALTERNATIVO: Path | None = None


def connetti() -> sqlite3.Connection:
    """Apre la connessione, creando la cartella se serve.

    Il database e' SQLITE_PATH, o quello indicato da archivio_da.
    """
    percorso = _PERCORSO_ALTERNATIVO or SQLITE_PATH
    percorso.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(percorso)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def archivio_da(percorso: Path) -> Iterator[None]:
    """connetti apre percorso al posto di SQLITE_PATH fino all'uscita.

    Il file deve esistere: connetti non ne crea uno vuoto per sbaglio.
    """
    global _PERCORSO_ALTERNATIVO
    if not Path(percorso).is_file():
        raise ErroreArchivio(f"database non trovato: {percorso}")
    precedente = _PERCORSO_ALTERNATIVO
    _PERCORSO_ALTERNATIVO = Path(percorso)
    try:
        yield
    finally:
        _PERCORSO_ALTERNATIVO = precedente


def crea_schema(conn: sqlite3.Connection) -> None:
    """Crea le tabelle se non esistono."""
    conn.executescript(DDL)
    conn.commit()
    # PRAGMA database_list: (seq, name, file) del database principale
    print(f"  Schema creato in {conn.execute('PRAGMA database_list').fetchone()[2]}")


def _carica(
    conn: sqlite3.Connection, tabella: str, colonne: list[str], cartella: Path
) -> tuple[int, int]:
    """Carica un CSV della cartella, se presente: righe caricate e scartate."""
    percorso = cartella / f"{tabella}.csv"

    if not percorso.exists():
        print(f"  [saltato] {percorso.name} non presente")
        return 0, 0

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

    return inserite, scartate


def carica_csv(
    conn: sqlite3.Connection,
    tabella: str,
    colonne: list[str],
    cartella: Path | None = None,
) -> int:
    """Carica un CSV da data/processed, o da cartella, se presente."""
    # PROCESSED_DIR si legge qui, non nel valore predefinito: i test lo
    # sostituiscono nel modulo
    return _carica(conn, tabella, colonne, cartella or PROCESSED_DIR)[0]


def popola_da_csv(
    conn: sqlite3.Connection, cartella: Path | None = None
) -> dict[str, dict[str, int]]:
    """Carica tutte le tabelle di TABELLE_DA_CSV dai CSV della cartella.

    La strada unica per popolare il database: la usano step4_crea_db e
    crea_da_csv. Restituisce, per tabella, le righe caricate e scartate.
    """
    conteggi = {}
    for tabella, colonne in TABELLE_DA_CSV.items():
        caricate, scartate = _carica(conn, tabella, colonne, cartella or PROCESSED_DIR)
        conteggi[tabella] = {"caricate": caricate, "scartate": scartate}
    return conteggi


def crea_da_csv(destinazione: Path, cartella: Path) -> dict[str, dict[str, int]]:
    """Un database nuovo in destinazione, dai CSV di cartella.

    Per le misure su un archivio congelato (passo 0 della roadmap). Si
    rifiuta se manca un CSV di TABELLE_DA_CSV (salvo quelli di
    TABELLE_DOPO_LA_COPIA, che restano tabelle vuote), se destinazione esiste gia'
    o se sta in data/db: il database dell'app non si tocca mai. La
    connessione si chiude prima di uscire. Restituisce, per tabella, le
    righe caricate e scartate.
    """
    destinazione = Path(destinazione)
    cartella = Path(cartella)
    if not cartella.is_dir():
        raise ErroreArchivio(f"cartella dei CSV non trovata: {cartella}")
    mancanti = [
        t
        for t in TABELLE_DA_CSV
        if t not in TABELLE_DOPO_LA_COPIA and not (cartella / f"{t}.csv").is_file()
    ]
    if mancanti:
        raise ErroreArchivio(f"in {cartella} mancano i CSV di: {', '.join(mancanti)}")
    vietate = {SQLITE_PATH.resolve().parent, (DATA_DIR / "db").resolve()}
    if vietate & set(destinazione.resolve().parents):
        raise ErroreArchivio(
            f"{destinazione} sta in data/db: il database dell'app non si tocca"
        )
    if destinazione.exists():
        raise ErroreArchivio(f"{destinazione} esiste gia'")

    destinazione.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(destinazione)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        crea_schema(conn)
        return popola_da_csv(conn, cartella)
    finally:
        conn.close()


def _per_csv(valore):
    """Riporta a intero un decimale senza parte frazionaria: 1200.0 diventa 1200."""
    if isinstance(valore, float) and valore.is_integer():
        return int(valore)
    return valore


# Un a-capo in qualunque forma, dentro un valore da esportare
A_CAPO = re.compile(r"\r\n|\r|\n")


def chiave_primaria(conn: sqlite3.Connection, tabella: str) -> list[str]:
    """Le colonne della chiave primaria di una tabella, nel loro ordine."""
    # PRAGMA table_info: (cid, name, type, notnull, dflt_value, pk)
    info = conn.execute(f"PRAGMA table_info({tabella})").fetchall()
    return [r[1] for r in sorted((r for r in info if r[5]), key=lambda r: r[5])]


def esporta_csv(conn: sqlite3.Connection, tabella: str, colonne: list[str]) -> int:
    """Riscrive il CSV di data/processed con il contenuto attuale della tabella.

    Le righe sono in ordine di chiave primaria: lo stesso contenuto da' lo
    stesso file, e i diff dei CSV mostrano solo i dati cambiati.

    Un a-capo dentro un valore di testo diventa uno spazio, nel CSV e nel
    database, e si stampa dove: git converte le fine riga al checkout,
    anche dentro i campi, e il dato cambierebbe da una copia all'altra.
    Non e' un errore perche' l'esportazione arriva quando il database e'
    gia' scritto: fermarla lascerebbe i CSV indietro. La correzione nel
    database si conferma qui, salvo dentro una transazione gia' aperta da
    chi chiama, che resta sua.
    """
    percorso = PROCESSED_DIR / f"{tabella}.csv"
    elenco = ", ".join(colonne)
    chiave = chiave_primaria(conn, tabella)
    ordine = ", ".join(chiave) or colonne[0]
    righe = conn.execute(
        f"SELECT rowid AS _riga, {elenco} FROM {tabella} ORDER BY {ordine}"
    ).fetchall()
    gia_in_transazione = conn.in_transaction

    corretti = []
    with percorso.open("w", encoding="utf-8-sig", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=colonne)
        scrittore.writeheader()
        for riga in righe:
            valori = {c: _per_csv(riga[c]) for c in colonne}
            for c, valore in valori.items():
                if isinstance(valore, str) and A_CAPO.search(valore):
                    valori[c] = A_CAPO.sub(" ", valore)
                    conn.execute(
                        f"UPDATE {tabella} SET {c} = ? WHERE rowid = ?",
                        (valori[c], riga["_riga"]),
                    )
                    nome = "/".join(str(riga[k]) for k in chiave) or riga["_riga"]
                    corretti.append(f"{nome}.{c}")
            scrittore.writerow(valori)

    if corretti and not gia_in_transazione:
        conn.commit()
    print(f"  {tabella}: {len(righe)} righe esportate in {percorso.name}")
    if corretti:
        print(
            f"  {tabella}: a-capo sostituiti con uno spazio, nel CSV e nel "
            f"database, in {len(corretti)} campi: {', '.join(corretti)}"
        )
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
