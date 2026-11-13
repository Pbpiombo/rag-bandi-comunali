"""Toglie dall'archivio due bandi di Incentivi Italia letti con il modello.

Uso:
    python -m scripts.manutenzione.togli_bandi_incentivi

Script una tantum (docs/piano-fonti.md, tappa 5, decisioni del
13/11/2026, terza serie). Le due pagine lette con il modello non danno
un bando affidabile:
- fondo di garanzia per l'impiantistica sportiva: la pagina presenta
  piu' fondi, e il bando salvato mescola due misure (la frase sugli enti
  pubblici e' del comparto "patrimonio culturale");
- automotive, accordi per l'innovazione: le imprese sono andate perse
  (frase non trovata nella pagina), resta solo ricerca_formazione.

Le righe di bandi e delle tabelle collegate si cancellano; in scansioni
la pagina resta, con esito 'scartato' e un motivo "da verificare: ...",
che estrai_incentivi non rilegge. Nessuna chiamata al modello. Alla fine
riversa le tabelle nei CSV. Rilanciarlo non cambia nulla.
"""

from src.database.schema import aggiorna_csv, connetti

PREFISSO = "da verificare: "

DA_TOGLIERE = {
    "incentivi-1726": (
        "due misure mescolate nella stessa pagina (fondi speciali dell'Istituto "
        "per il Credito Sportivo: la frase sugli enti pubblici e' del comparto "
        "patrimonio culturale)"
    ),
    "incentivi-8890": (
        "imprese perse nell'estrazione (frase dei beneficiari non trovata nella "
        "pagina): resta solo ricerca e formazione"
    ),
}

COLLEGATE = ("beneficiari_bando", "interventi_bando", "scadenze_bando")


def togli(id_bando: str, motivo: str) -> str:
    """Cancella il bando e annota la pagina come da verificare."""
    conn = connetti()
    try:
        riga = conn.execute(
            "SELECT url FROM bandi WHERE id = ?", (id_bando,)
        ).fetchone()
        if riga is None:
            return "non in archivio"
        for tabella in COLLEGATE:
            conn.execute(f"DELETE FROM {tabella} WHERE id_bando = ?", (id_bando,))
        conn.execute("DELETE FROM bandi WHERE id = ?", (id_bando,))
        aggiornate = conn.execute(
            "UPDATE scansioni SET esito = 'scartato', motivo = ? WHERE url = ?",
            (PREFISSO + motivo, riga["url"]),
        ).rowcount
        conn.commit()
        return f"tolto; scansioni aggiornate: {aggiornate}"
    finally:
        conn.close()


def main() -> None:
    for id_bando, motivo in DA_TOGLIERE.items():
        print(f"{id_bando}: {togli(id_bando, motivo)}")
    aggiorna_csv("bandi", *COLLEGATE, "scansioni")


if __name__ == "__main__":
    main()
