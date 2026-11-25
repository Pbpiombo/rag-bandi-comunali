import os
from pathlib import Path

from dotenv import load_dotenv

# Percorso assoluto della cartella radice del progetto
ROOT_DIR = Path(__file__).resolve().parents[1]

# Legge il file .env e rende disponibili le variabili al programma
load_dotenv(ROOT_DIR / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    raise RuntimeError(
        "ANTHROPIC_API_KEY non trovata. Controlla che il file .env "
        "esista nella radice del progetto."
    )

MODEL_NAME = os.getenv("MODEL_NAME", "claude-sonnet-5")

# --- Percorsi dei dati ---
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
CHROMA_DIR = DATA_DIR / "db" / "chroma"
SQLITE_PATH = DATA_DIR / "db" / "comune.sqlite"

# Dati grezzi, fuori dal repository: la cartella accanto al progetto.
# ESTRAZIONI_DIR: la risposta del modello per ogni estrazione di un bando
# (src/estrazione/grezzi.py), per rifare la validazione senza ripagarlo.
# ELENCHI_DIR: la copia di ogni elenco letto dalla scansione, HTML e voci
# (src/estrazione/elenco.py), per sapere dopo che cosa l'elenco conteneva.
# SCANSIONI_DIR: una cartella per giorno con le letture della scansione
# fatte attraverso Lettore (robots.txt, elenchi, pagine, richieste.csv) e
# il rapporto della ricognizione (scripts/ingestione/ricognizione.py).
DATI_GREZZI_DIR = ROOT_DIR.parent / "dati-grezzi"
ESTRAZIONI_DIR = DATI_GREZZI_DIR / "estrazioni"
ELENCHI_DIR = DATI_GREZZI_DIR / "elenchi"
SCANSIONI_DIR = DATI_GREZZI_DIR / "scansioni"

# --- Parametri di ingestione ---
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "abetone_documenti"

SOGLIA_PAGINA_MINIMA = 50  # Pagine con meno caratteri vengono scartate

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 250
SOGLIA_CHUNK = 150

# Frammenti vicini passati al modello (docs/coda.md, "Passo 19e, rimedio
# 1"): per ogni frammento di un avviso (metadato id_bando) anche quello
# prima e quello dopo nello stesso file. Spenti: i vicini sono misurati solo
# sull'ordine c-LR in condizione B (24/11/2026, V1 passa); si accendono con
# (-1, 1) insieme all'ordine c-LR e al filtro per bando nel passo 19e.
# Lavorano solo se il recupero sa restituire un frammento da (fonte,
# chunk_num): oggi Chroma si', Postgres no (query rimandata al passo 19e).
SPOSTAMENTI_VICINI: tuple[int, ...] = ()

# Citazioni ripetute accorciate alla sola etichetta (src/citazioni.py).
# Agisce solo sul testo mostrato; verificatore e bandi citati ricevono
# sempre il testo intero. Misurato il 25/11/2026 su 226 risposte salvate
# (docs/coda.md, "Citazioni ripetute (25/11/2026)"). False: testo come prima.
ACCORCIA_CITAZIONI = True

# Ripiego anche quando dettaglio_bando trova solo bandi scaduti (tappa 6a,
# docs/piano-19e.md, 25/11/2026): si aggiungono i candidati del testo unito
# tra i non scaduti, mai scelti; gli scaduti restano mostrati come scaduti.
# Senza candidati il risultato non cambia. False: come prima.
RIPIEGO_ANCHE_CON_SCADUTI = True

# Ente selezionato all'apertura dell'app e usato dagli script da riga di comando.
ENTE_PREDEFINITO = "90060100477"
