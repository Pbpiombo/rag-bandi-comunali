"""Inserisce a mano le date dei bandi a finestre gia' in archivio.

Uso:
    python -m scripts.manutenzione.inserisci_finestre

Script una tantum (docs/piano-post-scansione.md, tappa 5c). Le date sono
lette dalle pagine dei bandi il 12 novembre 2026, senza modello; ogni riga
porta la frase della pagina da cui viene. La scadenza del bando in archivio
deve gia' essere l'ultima scadenza 'domanda': se non lo e', il bando si
salta e lo si dice.

Crea la tabella scadenze_bando se il database e' precedente; alla fine
riversa la tabella nel CSV. Rilanciarlo non cambia nulla: le righe di un
bando si sostituiscono.
"""

from src.database.schema import aggiorna_csv, connetti, crea_schema

# id del bando -> (genere, descrizione, apertura, scadenza, frase della pagina)
FINESTRE = {
    # https://www.regione.toscana.it/-/dopo-la-laurea-finanziamenti-per-progetti-
    # di-informazione-orientamento-e-imprenditorialit%C3%A0-accademica
    "dopo-la-laurea-finanziamenti-per-progetti-di-informaz-851fa7": [
        (
            "domanda",
            "prima finestra",
            "2025-08-21",
            "2025-10-31",
            (
                "Prima scadenza: presentazione dal 21 agosto, (giorno successivo "
                "alla data di pubblicazione del bando sul Burt) fino alle ore "
                "23.59 del 31 ottobre 2025"
            ),
        ),
        (
            "domanda",
            "seconda finestra, solo se resta budget",
            "2026-06-15",
            "2026-07-15",
            (
                "Seconda scadenza: dalla data del 15 giugno 2026 fino alle ore 23.59 "
                "del 15 luglio 2026"
            ),
        ),
        (
            "domanda",
            "terza finestra, solo se resta budget",
            "2026-11-11",
            "2026-12-11",
            (
                "Terza scadenza : dalla data del 11 novembre 2026 fino alle ore 23.59 "
                "del 11 dicembre 2026"
            ),
        ),
        (
            "domanda",
            "quarta finestra, solo se resta budget",
            "2027-06-15",
            "2027-07-15",
            (
                "Quarta scadenza: dalla data del 15 giugno 2027 fino alle ore 23.59 "
                "del 15 luglio 2027"
            ),
        ),
    ],
}


def inserisci(conn, id_bando: str, righe: list[tuple]) -> str:
    """Sostituisce le date di un bando e dice cosa e' successo."""
    bando = conn.execute(
        "SELECT scadenza FROM bandi WHERE id = ?", (id_bando,)
    ).fetchone()
    if bando is None:
        return "NON TROVATO"

    ultima = max(r[3] for r in righe if r[0] == "domanda")
    if bando["scadenza"] != ultima:
        return (
            f"SALTATO: la scadenza in archivio e' {bando['scadenza']}, "
            f"l'ultima finestra chiude il {ultima}"
        )

    ordinate = sorted(righe, key=lambda r: (r[3], r[2] or ""))
    conn.execute("DELETE FROM scadenze_bando WHERE id_bando = ?", (id_bando,))
    conn.executemany(
        "INSERT INTO scadenze_bando (id_bando, numero, genere, descrizione, "
        "apertura, scadenza, frase) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(id_bando, numero, *r) for numero, r in enumerate(ordinate, start=1)],
    )
    return f"{len(ordinate)} righe"


def main() -> None:
    conn = connetti()
    try:
        crea_schema(conn)
        for id_bando, righe in FINESTRE.items():
            print(f"  {id_bando}: {inserisci(conn, id_bando, righe)}")
        conn.commit()
    finally:
        conn.close()

    aggiorna_csv("scadenze_bando")


if __name__ == "__main__":
    main()
