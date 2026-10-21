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

# --- Parametri di ingestione ---
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
COLLECTION_NAME = "abetone_documenti"

SOGLIA_PAGINA_MINIMA = 50  # Pagine con meno caratteri vengono scartate

CHUNK_SIZE = 1500
CHUNK_OVERLAP = 250
SOGLIA_CHUNK = 150

# Profilo dell'ente per cui si cercano le opportunità di finanziamento
PROFILO_ENTE = {
    "nome": "Comune di Abetone Cutigliano",
    "tipo": "comune",
    "regione": "Toscana",
    "provincia": "Pistoia",
    "area_interna": "Garfagnana - Lunigiana - Media Valle del Serchio - Appennino Pistoiese",
    "capofila_area": False,
    "toscana_diffusa": None,  # da verificare sull'elenco della L.R. 11/2025
}
ENTE_PREDEFINITO = "90060100477"  # provvisorio: sostituito dalla scelta dell'utente al sottopasso 5
