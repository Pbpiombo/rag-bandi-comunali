"""Una lettura su Postgres, perche' Supabase non metta in pausa il progetto.

Uso:
    python -m scripts.manutenzione.tieni_sveglio

Sul piano gratuito Supabase mette in pausa i progetti senza attivita' per
circa una settimana. Il workflow .github/workflows/tieni_sveglio.yml lancia
questo script ogni 3 giorni; si puo' lanciare anche a mano.

Solo letture: la connessione e' in sola lettura e la query conta i
frammenti di `chunk`. Legge DATABASE_URL dall'ambiente o da .env.
Se il progetto e' gia' in pausa la connessione fallisce: va ripristinato
dal pannello di Supabase, lo script non puo' farlo.
"""

import os
import sys

import psycopg
from dotenv import load_dotenv

QUERY = "SELECT count(*) FROM chunk"


def main() -> int:
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL non impostata.", file=sys.stderr)
        return 1

    try:
        with psycopg.connect(url, connect_timeout=30) as conn:
            conn.read_only = True
            (frammenti,) = conn.execute(QUERY).fetchone()
    except psycopg.OperationalError as errore:
        # Un progetto in pausa risponde "tenant/user ... not found"
        print(
            "Connessione non riuscita. Se il messaggio dice "
            "'tenant/user ... not found' il progetto e' in pausa e va "
            f"ripristinato dal pannello di Supabase.\n{errore}",
            file=sys.stderr,
        )
        return 1

    print(f"Postgres risponde: {frammenti} frammenti in chunk.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
