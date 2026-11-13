"""Contatti d'ufficio per i bandi gia' in archivio, riscaricando le pagine.

Uso:
    python -u -m scripts.manutenzione.aggiungi_contatti --prova
    python -u -m scripts.manutenzione.aggiungi_contatti --prova --fonte CODICE
    python -u -m scripts.manutenzione.aggiungi_contatti --prova --limite 10
    python -u -m scripts.manutenzione.aggiungi_contatti --scrivi

Nessuna chiamata al modello: i contatti si leggono con il codice
(src/estrazione/contatti.py) dal testo della pagina, lo stesso che va
all'estrattore. Mai nomi o email di persone: nel dubbio un contatto si
scarta e resta il collegamento alla pagina.

Con --prova non scrive niente: stampa per ogni bando i contatti che
scriverebbe e quante email ha scartato, con le nominative mascherate.
Senza --prova serve --scrivi, esplicito: aggiorna contatti e
contatti_letti_il ed esporta bandi.csv.

Si rispettano robots.txt e il suo Crawl-delay; tra due download dello
stesso dominio si aspetta almeno ATTESA_MINIMA secondi.
"""

import sys
import time
from datetime import datetime
from http.client import HTTPException
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from src.database.schema import aggiorna_csv, connetti
from src.estrazione.contatti import EMAIL, contatti_da_testo, email_nominativa
from src.estrazione.incentivi import Robots, indirizzo_ascii
from src.estrazione.pagina import a_testo, ritaglia, scarica

ATTESA_MINIMA = 1.0


def opzione(nome: str) -> str | None:
    if nome not in sys.argv:
        return None
    posizione = sys.argv.index(nome)
    return sys.argv[posizione + 1] if posizione + 1 < len(sys.argv) else None


def mascherata(email: str) -> str:
    """Un'email nominativa senza la parte che identifica la persona."""
    return (
        f"[nominativa]@{email.split('@', 1)[1]}" if email_nominativa(email) else email
    )


def bandi_da_leggere(codice_fonte: str | None, limite: int | None) -> list:
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT id, titolo, url, codice_fonte FROM bandi "
            "WHERE natura = 'bando' AND (? IS NULL OR codice_fonte = ?) "
            "ORDER BY codice_fonte, id",
            (codice_fonte, codice_fonte),
        ).fetchall()
    finally:
        conn.close()
    return righe[:limite] if limite else righe


def main() -> None:
    prova = "--prova" in sys.argv
    if not prova and "--scrivi" not in sys.argv:
        print("Indica --prova (non scrive niente) oppure --scrivi.")
        return

    limite = opzione("--limite")
    bandi = bandi_da_leggere(opzione("--fonte"), int(limite) if limite else None)
    robots = Robots()
    ultimo: dict[str, float] = {}
    trovati, senza, non_letti = {}, 0, []

    print(
        f"{len(bandi)} bandi da leggere{' (prova: nessuna scrittura)' if prova else ''}"
    )
    for numero, bando in enumerate(bandi, start=1):
        url = indirizzo_ascii(bando["url"])
        dominio = urlsplit(url).netloc
        permesso = robots.permesso(url)
        if not permesso:
            motivo = (
                "robots.txt vieta" if permesso is False else "robots.txt illeggibile"
            )
            non_letti.append((bando["id"], motivo))
            continue

        attesa = max(robots.attesa(url), ATTESA_MINIMA)
        trascorso = time.monotonic() - ultimo.get(dominio, 0.0)
        if trascorso < attesa:
            time.sleep(attesa - trascorso)
        try:
            testo = ritaglia(a_testo(scarica(url, timeout=120)))
        except (OSError, HTTPException, ValueError) as errore:
            non_letti.append((bando["id"], f"pagina non scaricata ({errore})"))
            continue
        finally:
            ultimo[dominio] = time.monotonic()

        contatti = contatti_da_testo(testo, bando["titolo"])
        tutte = {e.rstrip(".").lower() for e in EMAIL.findall(testo)}
        scartate = sorted(mascherata(e) for e in tutte if e not in (contatti or ""))

        print(f"[{numero}/{len(bandi)}] {bando['codice_fonte']} {bando['id'][:50]}")
        print(f"    contatti: {contatti or '(nessuno: vedi la pagina)'}")
        if scartate:
            print(f"    email scartate: {', '.join(scartate)}")
        if contatti:
            trovati[bando["id"]] = contatti
        else:
            senza += 1

    print(
        f"\nRIEPILOGO: {len(trovati)} con contatti, {senza} senza, "
        f"{len(non_letti)} non letti"
    )
    for id_bando, motivo in non_letti:
        print(f"  non letto: {id_bando}: {motivo}")

    if prova:
        print("Prova: nessuna scrittura.")
        return

    oggi = datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
    conn = connetti()
    try:
        conn.executemany(
            "UPDATE bandi SET contatti = ?, contatti_letti_il = ? WHERE id = ?",
            [(c, oggi, i) for i, c in trovati.items()],
        )
        conn.commit()
    finally:
        conn.close()
    aggiorna_csv("bandi")
    print(f"Scritti i contatti di {len(trovati)} bandi.")


if __name__ == "__main__":
    main()
