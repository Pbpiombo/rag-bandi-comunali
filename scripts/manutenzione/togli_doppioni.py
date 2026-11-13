"""Toglie dall'archivio i doppioni elencati in data/processed/doppioni.csv.

Uso:
    python -m scripts.manutenzione.togli_doppioni            prova: nulla cambia
    python -m scripts.manutenzione.togli_doppioni --scrivi   toglie

Per ogni riga del file ancora in archivio (src/estrazione/doppioni.py):
1. confronta campo per campo la versione tolta con quella tenuta; se la
   tolta ha un valore che la tenuta non ha, e non e' tra le differenze
   accettate della riga, si ferma e lo mostra;
2. elenca le interrogazioni in cui compare la tolta: aperti per ciascun
   ente, per ciascun tipo di beneficiario, per tema;
3. con --scrivi: toglie la riga e quelle collegate, annota la pagina in
   scansioni come "doppione di <id>", rilancia le interrogazioni e
   annulla la rimozione se la tenuta manca da una in cui c'era la tolta.

Prima di scrivere, copia del database in dati-grezzi/backup. Alla fine
riversa nei CSV bandi, le tabelle collegate e scansioni. Nessuna chiamata
al modello e nessuna pagina scaricata. Rilanciarlo non cambia nulla.
"""

import sys

from src.database.schema import aggiorna_csv, connetti
from src.estrazione.doppioni import (
    COLLEGATE,
    FileNonValido,
    copia_di_sicurezza,
    leggi_doppioni,
    togli,
)


def mostra(esito) -> None:
    print(f"\n== {esito.id_tolto or esito.url} -> {esito.id_tenuto}: {esito.stato}")
    for campo in esito.lacune:
        print(f"   LACUNA della tenuta: {campo}")
    for diverso in esito.diversi:
        print(f"   diverso (tolta / tenuta): {diverso}")
    for nome, dove in esito.prima.items():
        dopo = esito.dopo.get(nome, "ASSENTE") if esito.dopo else ""
        print(f"   {nome}: tolta in {dove}" + (f"; tenuta in {dopo}" if dopo else ""))
    if esito.stato in ("da togliere", "tolto") and not esito.prima:
        print("   la tolta non compare in nessuna interrogazione")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    scrivi = "--scrivi" in sys.argv
    try:
        doppioni = leggi_doppioni()
    except FileNonValido as errore:
        sys.exit(f"data/processed/doppioni.csv rifiutato: {errore}")
    print(f"{len(doppioni)} doppioni nel file")

    conn = connetti()
    tolti = 0
    try:
        if scrivi:
            print(f"Backup: {copia_di_sicurezza(conn, 'togli-doppioni')}")
        for doppione in doppioni.values():
            esito = togli(conn, doppione, scrivi)
            mostra(esito)
            tolti += esito.stato == "tolto"
    finally:
        conn.close()

    if not scrivi:
        print("\nProva: nulla modificato. Per togliere: --scrivi")
        return
    print(f"\nTolti: {tolti}")
    if tolti:
        aggiorna_csv("bandi", *COLLEGATE, "scansioni")


if __name__ == "__main__":
    main()
