"""STEP 4 - crea il database dei dati numerici e lo popola dai CSV."""

from src.database.schema import (
    connetti,
    crea_schema,
    popola_da_csv,
    riepilogo,
)


def main() -> None:
    conn = connetti()

    crea_schema(conn)

    print("\n  Caricamento dai CSV in data/processed:")
    popola_da_csv(conn)

    riepilogo(conn)
    conn.close()


if __name__ == "__main__":
    main()
