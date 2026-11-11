"""Segna come non bandi le tre pagine in archivio giudicate tali l'11/11/2026.

Uso:
    python -m scripts.manutenzione.segna_non_bandi

Script una tantum (docs/piano-post-scansione.md, punto 1). Nella
riclassificazione dell'11 novembre 2026 il modello ha giudicato queste tre
righe dell'archivio pagine che non sono bandi; allora la riga restava
com'era. I motivi sono quelli registrati nel log di quella corsa. D'ora in
poi riclassifica_bandi le segna da se'.

Se il database e' precedente alla colonna natura, la aggiunge prima;
alla fine riversa bandi nel CSV. Rilanciarlo non cambia nulla.
"""

from src.database.schema import aggiorna_csv, connetti
from src.estrazione.salva import segna_non_bando

NON_BANDI = {
    "immobili-emergenza-abitativa-2026": (
        "procedura amministrativa: si tratta di una manifestazione di "
        "interesse/ricognizione di patrimonio immobiliare da destinare a "
        "finalità abitative, non di un bando che eroga un contributo o "
        "finanziamento su domanda"
    ),
    "sistemi-museali-2026": (
        "La pagina riporta l'esito/graduatoria del bando: in apertura si legge "
        "'Graduatoria di merito' e che con Decreto è stata approvata la "
        "graduatoria di merito del bando, quindi il bando è già concluso e la "
        "pagina documenta il risultato, non un'opportunità ancora aperta."
    ),
    "spettacolo-dal-vivo-2026": (
        "La pagina descrive l'approvazione di una graduatoria, l'assegnazione "
        "dei contributi e le modalità di rendicontazione e liquidazione di un "
        "bando già concluso, non un invito a presentare domanda"
    ),
}

# Le colonne aggiunte a bandi, per un database creato prima
COLONNE_NUOVE = {
    "natura": (
        "TEXT NOT NULL DEFAULT 'bando' CHECK (natura IN ('bando', 'non_bando'))"
    ),
    "natura_motivo": "TEXT",
}


def aggiungi_colonne() -> list[str]:
    """Aggiunge a bandi le colonne che mancano. Restituisce quelle aggiunte."""
    conn = connetti()
    try:
        presenti = {r["name"] for r in conn.execute("PRAGMA table_info(bandi)")}
        aggiunte = [c for c in COLONNE_NUOVE if c not in presenti]
        for colonna in aggiunte:
            conn.execute(
                f"ALTER TABLE bandi ADD COLUMN {colonna} {COLONNE_NUOVE[colonna]}"
            )
        conn.commit()
        return aggiunte
    finally:
        conn.close()


def main() -> None:
    aggiunte = aggiungi_colonne()
    if aggiunte:
        print(f"Colonne aggiunte a bandi: {', '.join(aggiunte)}")

    for id_bando, motivo in NON_BANDI.items():
        esito = "segnato" if segna_non_bando(id_bando, motivo) else "NON TROVATO"
        print(f"  {id_bando}: {esito}")

    aggiorna_csv("bandi")


if __name__ == "__main__":
    main()
