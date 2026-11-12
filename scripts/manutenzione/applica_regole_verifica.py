"""Applica ai bandi in archivio due regole della seconda verifica a mano.

Uso:
    python -m scripts.manutenzione.applica_regole_verifica --prova   elenca soltanto
    python -m scripts.manutenzione.applica_regole_verifica           applica

Script una tantum (verifica a mano del 12 novembre 2026). Le regole sono
quelle che l'estrattore applica ormai da se'; qui si applicano ai bandi
gia' estratti, senza modello:

1. I soggetti privati generici ("privati", "soggetti privati", "datori di
   lavoro", "soggetti ospitanti privati") non comprendono le persone
   fisiche: si tolgono le loro righe cittadini_famiglie, salvo che il
   soggetto o la frase nominino le persone fisiche. "Pubblici e/o privati"
   comprende tutti i tipi, e resta com'e'.
2. Un bando la cui pagina dice "salvo esaurimento (anticipato) delle
   risorse" e' a sportello anche con una data di chiusura: a_sportello
   diventa 1. Le pagine dei bandi non a sportello si riscaricano; la frase
   trovata si stampa come prova.

Alla fine riversa bandi e beneficiari_bando nei CSV. Rilanciarlo non
cambia nulla.
"""

import sys
import time
from http.client import HTTPException

from src.database.schema import aggiorna_csv, connetti
from src.estrazione.bandi import prova_sportello
from src.estrazione.beneficiari import GENERICI, TERMINI, tipi_da_termini
from src.estrazione.pagina import prendi

PAUSA = 0.5


def persone_escluse(soggetto: str | None, frase: str) -> bool:
    """Il soggetto e' privato generico, e non nomina le persone fisiche.

    Le regole generiche lo riconducono a dei tipi, tra cui non ci sono
    cittadini_famiglie; e le regole specifiche non ce le aggiungono.
    """
    testo = soggetto or frase
    generici = tipi_da_termini(testo, GENERICI)
    return (
        bool(generici)
        and "cittadini_famiglie" not in generici
        and "cittadini_famiglie" not in tipi_da_termini(testo, TERMINI)
    )


def righe_persone_da_togliere(conn) -> list[dict]:
    """Le righe cittadini_famiglie dei soggetti privati generici."""
    righe = conn.execute(
        "SELECT id_bando, tipo, soggetto, frase FROM beneficiari_bando "
        "WHERE tipo = 'cittadini_famiglie' ORDER BY id_bando"
    ).fetchall()
    return [dict(r) for r in righe if persone_escluse(r["soggetto"], r["frase"])]


def bandi_da_rendere_a_sportello(conn) -> list[tuple[str, str]]:
    """I bandi non a sportello la cui pagina dice "salvo esaurimento".

    Restituisce (id, frase della pagina). Una pagina che non si scarica si
    segnala e si salta.
    """
    bandi = conn.execute(
        "SELECT id, url FROM bandi WHERE natura = 'bando' AND a_sportello = 0 "
        "ORDER BY id"
    ).fetchall()
    trovati = []
    for b in bandi:
        try:
            testo = prendi(b["url"])
        except (OSError, HTTPException) as errore:
            print(f"  pagina non scaricata, saltato: {b['id']} ({errore})")
            continue
        frase = prova_sportello(testo)
        if frase:
            trovati.append((b["id"], frase))
        time.sleep(PAUSA)
    return trovati


def main() -> None:
    prova = "--prova" in sys.argv
    conn = connetti()
    try:
        persone = righe_persone_da_togliere(conn)
        print(f"1. Righe cittadini_famiglie da togliere: {len(persone)}")
        for r in persone:
            print(f"  {r['id_bando']}: «{r['soggetto']}»")

        sportello = bandi_da_rendere_a_sportello(conn)
        print(f"\n2. Bandi da rendere a sportello: {len(sportello)}")
        for id_bando, frase in sportello:
            print(f"  {id_bando}\n    prova: «{frase}»")

        if prova:
            print("\nProva: nulla modificato.")
            return

        for r in persone:
            conn.execute(
                "DELETE FROM beneficiari_bando WHERE id_bando = ? AND tipo = ? "
                "AND frase = ?",
                (r["id_bando"], r["tipo"], r["frase"]),
            )
        for id_bando, _ in sportello:
            conn.execute("UPDATE bandi SET a_sportello = 1 WHERE id = ?", (id_bando,))
        conn.commit()
    finally:
        conn.close()

    aggiorna_csv("bandi", "beneficiari_bando")


if __name__ == "__main__":
    main()
