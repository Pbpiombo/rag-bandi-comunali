"""I doppioni tra le fonti dei bandi, e la copia del database prima di toccarli.

Lo stesso bando puo' arrivare da due fonti: dalla pagina dell'ente e dal
catalogo di Incentivi Italia, che rimanda a un altro indirizzo (il BURT,
Arti, Sviluppo Toscana). Si tiene la versione letta dalla pagina; l'altra
si elenca in data/processed/doppioni.csv, che le importazioni leggono per
non salvarla di nuovo.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import DATI_GREZZI_DIR


def copia_di_sicurezza(
    conn: sqlite3.Connection, motivo: str, cartella: Path | None = None
) -> Path:
    """Copia il database in dati-grezzi/backup, fuori dal repository.

    Usa la copia di SQLite, che vale anche con la connessione aperta. Il
    nome dice la data, l'ora e il motivo: comune-AAAA-MM-GG-HHMM-prima-di-...
    """
    cartella = cartella or DATI_GREZZI_DIR / "backup"
    cartella.mkdir(parents=True, exist_ok=True)
    ora = datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d-%H%M")
    destinazione = cartella / f"comune-{ora}-prima-di-{motivo}.sqlite"
    copia = sqlite3.connect(destinazione)
    try:
        conn.backup(copia)
    finally:
        copia.close()
    return destinazione
