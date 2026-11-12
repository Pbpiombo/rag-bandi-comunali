"""Inserisce a mano le date dei bandi a finestre gia' in archivio.

Uso:
    python -m scripts.manutenzione.inserisci_finestre

Script una tantum (docs/piano-post-scansione.md, tappa 5c). Le date sono
lette dalle pagine dei bandi il 12 novembre 2026, senza modello; ogni riga
porta la frase della pagina da cui viene. La scadenza del bando in archivio
deve gia' essere l'ultima scadenza 'domanda': se non lo e', il bando si
salta e lo si dice.

Fa eccezione GOL (decisione del 12 novembre 2026): la pagina da' per la
Misura 1 sia il 31/07/2026 sia il 31/07/2027, e i decreti sulla stessa
pagina approvano domande pervenute dopo il 31/07/2026. Vale il 2027, e
bandi.scadenza passa da 2026-07-31 a 2027-07-31, solo se e' ancora il
valore vecchio. La contraddizione resta nella descrizione della riga, che
l'utente vede, oltre che in scadenza_nota.

Le righe hanno origine 'manuale': una nuova estrazione non le sostituisce,
e le date diverse proposte dal modello si elencano da rivedere.

Crea la tabella scadenze_bando, o la sua colonna origine, se il database e'
precedente; alla fine riversa nei CSV bandi e scadenze_bando. Rilanciarlo
non cambia nulla: le righe di un bando si sostituiscono.
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
    # https://www.regione.toscana.it/-/assegno-formazione-gol
    "assegno-formazione-gol": [
        (
            "domanda",
            (
                "Misura 1, assegno formazione: la pagina riporta anche il "
                "31/07/2026, verificare sul bando"
            ),
            None,
            "2027-07-31",
            (
                "La domanda di finanziamento per Assegno formazione Gol è presentata "
                "dagli enti erogatori per nome e per conto dei beneficiari GOL che "
                "hanno formalizzato con i centri per l'impiego l’adesione "
                "all’Assegno formazione GOL e potrà essere presentata fino al 31 "
                "luglio 2027"
            ),
        ),
        (
            "domanda",
            "Misura 2, iscrizione al catalogo",
            None,
            "2027-06-30",
            (
                "L’Avviso è a sportello, la domanda di inserimento/cancellazione "
                "nel/dal Catalogo può essere presentata fino al 30 giugno 2027"
            ),
        ),
    ],
    # https://www.regione.toscana.it/-/partenariato-europeo-per-la-medicina-
    # personalizzata-jtc-2027
    "partenariato-europeo-per-la-medicina-personalizzata-jtc-2027": [
        (
            "domanda",
            "pre-proposta (Pre-Proposal)",
            None,
            "2027-01-20",
            "Termine per la presentazione delle Pre-Proposal: 20 gennaio 2027 (14:00, CET)",
        ),
        (
            "fase_successiva",
            "proposta completa (Full Proposal)",
            None,
            "2027-05-25",
            "Termine per la presentazione della Full Proposal: 25 maggio 2027 (14:00, CEST)",
        ),
    ],
}

# id del bando -> (scadenza attesa in archivio, scadenza corretta)
CORREZIONI_SCADENZA = {
    "assegno-formazione-gol": ("2026-07-31", "2027-07-31"),
}


def correggi_scadenza(conn, id_bando: str, attesa: str, corretta: str) -> str:
    """Corregge bandi.scadenza solo se e' ancora il valore atteso."""
    bando = conn.execute(
        "SELECT scadenza FROM bandi WHERE id = ?", (id_bando,)
    ).fetchone()
    if bando is None:
        return "NON TROVATO"
    if bando["scadenza"] == corretta:
        return f"scadenza gia' {corretta}"
    if bando["scadenza"] != attesa:
        return f"NON CORRETTA: in archivio c'e' {bando['scadenza']}, atteso {attesa}"
    conn.execute("UPDATE bandi SET scadenza = ? WHERE id = ?", (corretta, id_bando))
    return f"scadenza {attesa} -> {corretta}"


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
        "apertura, scadenza, frase, origine) VALUES (?, ?, ?, ?, ?, ?, ?, 'manuale')",
        [(id_bando, numero, *r) for numero, r in enumerate(ordinate, start=1)],
    )
    return f"{len(ordinate)} righe"


def aggiungi_origine(conn) -> bool:
    """Aggiunge la colonna origine a una scadenze_bando creata prima."""
    presenti = {r["name"] for r in conn.execute("PRAGMA table_info(scadenze_bando)")}
    if "origine" in presenti:
        return False
    conn.execute(
        "ALTER TABLE scadenze_bando ADD COLUMN origine TEXT NOT NULL "
        "DEFAULT 'estrazione' CHECK (origine IN ('estrazione', 'manuale'))"
    )
    return True


def main() -> None:
    conn = connetti()
    try:
        crea_schema(conn)
        if aggiungi_origine(conn):
            print("  Colonna origine aggiunta a scadenze_bando")
        for id_bando, (attesa, corretta) in CORREZIONI_SCADENZA.items():
            esito = correggi_scadenza(conn, id_bando, attesa, corretta)
            print(f"  {id_bando}: {esito}")
        for id_bando, righe in FINESTRE.items():
            print(f"  {id_bando}: {inserisci(conn, id_bando, righe)}")
        conn.commit()
    finally:
        conn.close()

    aggiorna_csv("bandi", "scadenze_bando")


if __name__ == "__main__":
    main()
