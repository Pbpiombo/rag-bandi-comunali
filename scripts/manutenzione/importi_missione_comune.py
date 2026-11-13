"""Importi massimi e contributo di Sport e Cultura Missione Comune 2026.

Uso:
    python -m scripts.manutenzione.importi_missione_comune

Script una tantum (docs/piano-fonti.md, tappa 5, decisioni del
13/11/2026, quinta serie). Le pagine danno il mutuo massimo agevolabile
per fascia di ente (2, 4, 6 milioni): nessun campo lo contiene, e la
frase della pagina si aggiunge, testuale, al testo dei beneficiari.
Cultura Missione Comune aveva contributo_perc = 100, che e'
l'abbattimento degli interessi del mutuo, non un contributo sul costo:
si svuota, e la frase della pagina va nella nota.

Le frasi si leggono dalla pagina al momento, senza modello, e si
aggiungono solo se ci sono: una pagina cambiata ferma lo script. Alla
fine riversa bandi nel CSV. Rilanciarlo non cambia nulla.
"""

import sys
import time

from src.database.schema import aggiorna_csv, connetti
from src.estrazione.beneficiari import frase_nel_testo
from src.estrazione.pagina import a_testo, scarica

PAGINE = {
    "sport-missione-comune-2026": (
        "https://www.creditosportivo.it/fondi-speciali-bandi-sport-2026/"
    ),
    "cultura-missione-comune-2026": (
        "https://www.creditosportivo.it/fondi-speciali-bandi-cultura-2026/"
    ),
}
CULTURA = "cultura-missione-comune-2026"

# Le righe della pagina sugli importi massimi, dalla prima all'ultima
INIZIO_IMPORTI = "L’importo massimo di mutuo agevolabile"
FINE_IMPORTI = "6 milioni di euro"
# La frase sul contributo di Cultura Missione Comune
INIZIO_CONTRIBUTO = "Le istanze complete della documentazione prevista"

# Crawl-delay del robots.txt dell'Istituto
PAUSA = 2


def frase_importi(righe: list[str]) -> str | None:
    """Le righe sugli importi massimi, unite in una frase, se ci sono."""
    inizio = next(
        (i for i, r in enumerate(righe) if r.startswith(INIZIO_IMPORTI)), None
    )
    if inizio is None:
        return None
    fine = next(
        (i for i in range(inizio, len(righe)) if righe[i].startswith(FINE_IMPORTI)),
        None,
    )
    return None if fine is None else " ".join(righe[inizio : fine + 1])


def frase_contributo(righe: list[str]) -> str | None:
    return next((r for r in righe if r.startswith(INIZIO_CONTRIBUTO)), None)


def main() -> None:
    conn = connetti()
    try:
        for numero, (id_bando, url) in enumerate(PAGINE.items()):
            if numero:
                time.sleep(PAUSA)
            testo = a_testo(scarica(url))
            righe = testo.splitlines()
            riga = conn.execute(
                "SELECT beneficiari, scadenza_nota, contributo_perc FROM bandi "
                "WHERE id = ?",
                (id_bando,),
            ).fetchone()
            if riga is None:
                sys.exit(f"{id_bando}: non in archivio")

            importi = frase_importi(righe)
            if importi is None or not frase_nel_testo(importi, testo):
                sys.exit(f"{id_bando}: frase degli importi non trovata nella pagina")
            if importi in riga["beneficiari"]:
                print(f"{id_bando}: importi gia' nel testo dei beneficiari")
            else:
                conn.execute(
                    "UPDATE bandi SET beneficiari = ? WHERE id = ?",
                    (f"{riga['beneficiari']}. {importi}", id_bando),
                )
                print(f"{id_bando}: importi aggiunti ai beneficiari")

            if id_bando != CULTURA:
                continue
            contributo = frase_contributo(righe)
            if contributo is None:
                sys.exit(f"{id_bando}: frase del contributo non trovata nella pagina")
            nota = riga["scadenza_nota"] or ""
            if contributo not in nota:
                nota = f"{nota} Contributo: «{contributo}»".strip()
            conn.execute(
                "UPDATE bandi SET contributo_perc = NULL, scadenza_nota = ? WHERE id = ?",
                (nota, id_bando),
            )
            print(
                f"{id_bando}: contributo_perc svuotato (era {riga['contributo_perc']}), "
                "frase nella nota"
            )
        conn.commit()
    finally:
        conn.close()
    aggiorna_csv("bandi")


if __name__ == "__main__":
    main()
