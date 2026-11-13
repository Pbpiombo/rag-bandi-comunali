"""Risposte grezze del modello, conservate per ogni estrazione di un bando.

Ogni chiamata all'estrattore scrive un file JSON in dati-grezzi/estrazioni
(ESTRAZIONI_DIR), fuori dal repository, con il testo inviato al modello e
la sua risposta tale e quale. Serve a rifare la validazione dopo una
modifica alle regole senza ripagare il modello, e a costruire l'insieme di
prova dell'estrattore.

Il file si scrive subito dopo la chiamata, prima di interpretare la
risposta: si conservano anche le risposte che non sono JSON valido e
quelle delle estrazioni che falliscono la validazione.

Nome del file: AAAA-MM-GG_<id del bando>.json. Una seconda estrazione
dello stesso bando nello stesso giorno non sovrascrive la prima: prende
il suffisso -2, -3 e cosi' via.
"""

import json
import re
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import ESTRAZIONI_DIR, MODEL_NAME
from src.estrazione.bandi import Estrazione, interpreta_grezzo

FUSO = ZoneInfo("Europe/Rome")

# Caratteri ammessi nel nome del file, oltre al punto dell'estensione
NON_AMMESSI = re.compile(r"[^a-z0-9_-]+")


def nome_sicuro(id_bando: str) -> str:
    """L'id del bando ridotto a caratteri sicuri per un nome di file."""
    pulito = NON_AMMESSI.sub("-", id_bando.lower()).strip("-")
    return pulito or "senza-id"


def _percorso_libero(cartella: Path, base: str) -> Path:
    """Il primo nome non ancora usato: base.json, base-2.json, ..."""
    percorso = cartella / f"{base}.json"
    numero = 2
    while percorso.exists():
        percorso = cartella / f"{base}-{numero}.json"
        numero += 1
    return percorso


def conserva(
    cartella: Path,
    id_bando: str,
    url: str,
    testo: str,
    grezzo: str,
    quando: datetime | None = None,
) -> Path:
    """Scrive la risposta grezza del modello e restituisce il percorso.

    testo: il testo inviato al modello, cioe' quello su cui si valida;
    grezzo: la risposta del modello, senza alcuna elaborazione.
    """
    quando = quando or datetime.now(FUSO)
    cartella.mkdir(parents=True, exist_ok=True)
    percorso = _percorso_libero(
        cartella, f"{quando.date().isoformat()}_{nome_sicuro(id_bando)}"
    )
    contenuto = {
        "id_bando": id_bando,
        "url": url,
        "estratto_il": quando.isoformat(timespec="seconds"),
        "modello": MODEL_NAME,
        "testo": testo,
        "risposta": grezzo,
    }
    percorso.write_text(
        json.dumps(contenuto, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return percorso


def conservatore(
    id_bando: str, url: str, testo: str, cartella: Path | None = None
) -> Callable[[str], Path]:
    """La funzione da passare a estrai(conserva=...) per un bando.

    cartella: ESTRAZIONI_DIR se non indicata.
    """

    def _conserva(grezzo: str) -> Path:
        return conserva(cartella or ESTRAZIONI_DIR, id_bando, url, testo, grezzo)

    return _conserva


def leggi(percorso: Path) -> dict:
    """Il contenuto di un file di risposta grezza."""
    return json.loads(Path(percorso).read_text(encoding="utf-8"))


def rileggi(percorso: Path) -> tuple[Estrazione, str]:
    """L'Estrazione e il testo di una risposta conservata, senza modello.

    Con il risultato si rilancia valida(estrazione, testo). Una risposta
    che non e' JSON valido solleva ValueError, come estrai.
    """
    dati = leggi(percorso)
    return interpreta_grezzo(dati["risposta"]), dati["testo"]
