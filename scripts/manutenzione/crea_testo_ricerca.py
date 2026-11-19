"""Crea data/processed/testo_ricerca.csv, il testo di ricerca per bando (passo 17).

Uso:
    python -u -m scripts.manutenzione.crea_testo_ricerca --file PERCORSO
    python -u -m scripts.manutenzione.crea_testo_ricerca --file PERCORSO --controlla

--file: OpenData_Incentivi.csv, lo stesso file da cui vengono i bandi di
Incentivi Italia, fuori dal repository.
--del AAAA-MM-GG: la data del file; se manca, il nome della cartella del
file, se e' una data. Deve essere quella scritta nella fonte dei bandi.
--controlla: non scrive; ricostruisce il testo e lo confronta con il
file esistente, ed esce con errore se e' diverso o manca. Si lancia
prima di fare una copia congelata (docs/piano-insieme-prova.md).

Si leggono i CSV di data/processed, non SQLite. Nessuna chiamata al
modello. Il testo serve solo all'ordinamento: non va al modello che
scrive e non si cita (src/ordinamento/testo_ricerca.py).
"""

import argparse
import sys
from datetime import date
from pathlib import Path

from src.config import PROCESSED_DIR
from src.ordinamento.testo_ricerca import (
    NOME_FILE,
    ErroreTestoRicerca,
    costruisci,
    scrivi,
    uguale_al_file,
)


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--file", type=Path, help="OpenData_Incentivi.csv")
    parser.add_argument("--del", dest="data", help="la data del file, AAAA-MM-GG")
    parser.add_argument(
        "--controlla",
        action="store_true",
        help="confronta con il file esistente, senza scrivere",
    )
    return parser.parse_args(argv)


def data_del_file(percorso: Path | None, indicata: str | None) -> str | None:
    """La data del file: --del, oppure il nome della cartella se e' una data."""
    valore = indicata or (percorso.parent.name if percorso else None)
    if valore is None:
        return None
    try:
        return date.fromisoformat(valore).isoformat()
    except ValueError:
        raise ErroreTestoRicerca(
            f"data del file non riconosciuta ('{valore}'): indicala con --del AAAA-MM-GG"
        ) from None


def main(argv: list[str] | None = None, cartella: Path | None = None) -> int:
    argomenti = leggi_argomenti(argv)
    cartella = cartella or PROCESSED_DIR
    destinazione = cartella / NOME_FILE
    try:
        data_file = data_del_file(argomenti.file, argomenti.data)
        righe = costruisci(cartella, argomenti.file, data_file)
    except ErroreTestoRicerca as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        return 1

    if argomenti.controlla:
        if uguale_al_file(righe, destinazione):
            print(f"{destinazione.name}: aggiornato ({len(righe)} bandi)")
            return 0
        print(
            f"{destinazione.name}: diverso dai dati attuali o mancante; "
            "rigeneralo prima della copia congelata",
            file=sys.stderr,
        )
        return 1

    scrivi(righe, destinazione)
    print(f"{destinazione.name}: {len(righe)} bandi scritti")
    return 0


if __name__ == "__main__":
    sys.exit(main())
