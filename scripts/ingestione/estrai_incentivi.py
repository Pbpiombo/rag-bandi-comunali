"""Legge con il modello le pagine dei bandi aperti per enti pubblici di Incentivi Italia.

Uso:
    python -u -m scripts.ingestione.estrai_incentivi --file PERCORSO --prova
    python -u -m scripts.ingestione.estrai_incentivi --file PERCORSO

Il catalogo non basta a dire se un comune puo' partecipare (decisione del
13/11/2026, piano fonti tappa 5): le righe aperte, sportello o in arrivo
con "Ente Pubblico" tra le tipologie non si salvano dal file
(importa_incentivi), ma si estraggono dalla pagina del Link_istituzionale
come gli altri bandi: estrazione, validazione delle prove, decisione
automatica. I tipi di beneficiario, pubblici compresi, sono quelli letti
dalla pagina.

Le righe sono quelle che src/estrazione/incentivi.esamina assegna al
modello, con le stesse esclusioni (link gia' in archivio da un'altra
fonte, link condiviso); robots.txt si controlla prima di scaricare.

--prova: elenca le pagine e stima il costo, senza scaricare ne' chiamare
il modello. Senza: estrae, salva, registra in scansioni ed esporta i CSV,
anche se si interrompe. Un errore di credito o di autenticazione ferma
tutto senza registrare la pagina.
"""

import sys
import time
from datetime import datetime
from http.client import HTTPException
from pathlib import Path
from zoneinfo import ZoneInfo

from anthropic import APIError
from langchain_core.callbacks import get_usage_metadata_callback

from scripts.ingestione.estrai_nuovi import (
    COSTO_BANDO,
    PAUSA,
    errore_bloccante,
    mostra_costo,
)
from scripts.ingestione.importa_incentivi import (
    PREFISSO_DA_VERIFICARE,
    altre_fonti,
    data_del_file,
    fonte_presente,
    opzione_testo,
)
from src.database.schema import aggiorna_csv, connetti
from src.estrazione import incentivi as inc
from src.estrazione.bandi import (
    costruisci_estrattore,
    decidi_automatico,
    estrai,
    valida,
)
from src.estrazione.beneficiari import TIPI_PUBBLICI
from src.estrazione.grezzi import conservatore
from src.estrazione.pagina import a_testo, ritaglia, scarica
from src.estrazione.registro import registra
from src.estrazione.salva import salva


def gia_esaminate() -> set[str]:
    """Le pagine di questa fonte gia' esaminate con esito salvato o scartato.

    Non si rileggono: una chiamata costa, e una pagina tolta a mano
    dall'archivio (scripts/manutenzione/togli_bandi_incentivi) non deve
    tornare. Le pagine fallite (non scaricate, prove non trovate) si
    ritentano.
    """
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT url FROM scansioni WHERE codice_fonte = ? "
            "AND esito IN ('salvato', 'scartato')",
            (inc.CODICE_FONTE,),
        ).fetchall()
    finally:
        conn.close()
    return {r["url"] for r in righe}


def da_estrarre(percorso: Path, oggi) -> list[inc.Esame]:
    """Le righe del file che vanno lette con il modello, non ancora esaminate."""
    incentivi = inc.leggi_file(percorso)
    condivisi = inc.link_condivisi(incentivi)
    esistenti = altre_fonti()
    esaminate = gia_esaminate()
    esami = [inc.esamina(i, oggi, condivisi, esistenti) for i in incentivi]
    return [
        e
        for e in esami
        if e.esito == inc.AL_MODELLO and e.incentivo.url not in esaminate
    ]


def esamina_pagina(estrattore, esame: inc.Esame, robots: inc.Robots, fonte: str):
    """Estrae e decide una pagina. Restituisce (esito, motivo, avvisi, riga)."""
    url = inc.indirizzo_ascii(esame.incentivo.url)
    permesso = robots.permesso(url)
    if not permesso:
        motivo = (
            "robots.txt vieta la pagina"
            if permesso is False
            else "robots.txt del dominio non leggibile"
        )
        return "scartato", PREFISSO_DA_VERIFICARE + motivo, "", None

    try:
        testo = ritaglia(a_testo(scarica(url)))
    except (OSError, HTTPException, ValueError) as errore:
        return "fallito", f"pagina non scaricata ({errore})", "", None

    id_bando = f"incentivi-{esame.incentivo.id}"
    estrazione = estrai(estrattore, testo, conserva=conservatore(id_bando, url, testo))
    riga, problemi, avvisi = valida(estrazione, testo)
    avvisi = "; ".join(avvisi)
    if problemi:
        return "fallito", "; ".join(problemi), avvisi, None

    riga["id"] = id_bando
    salvare, motivo = decidi_automatico(estrazione, riga)
    if not salvare:
        return "scartato", motivo, avvisi, riga
    salva(riga, esame.incentivo.link, fonte, inc.CODICE_FONTE)
    return "salvato", motivo, avvisi, riga


def main() -> None:
    percorso = opzione_testo("--file")
    if not percorso:
        sys.exit("Indica il file con --file PERCORSO")
    percorso = Path(percorso)
    data_file = data_del_file(percorso)
    oggi = datetime.now(ZoneInfo("Europe/Rome")).date()

    try:
        esami = da_estrarre(percorso, oggi)
    except inc.FileNonValido as errore:
        sys.exit(f"File rifiutato: {errore}")

    print(f"Pagine per enti pubblici da leggere con il modello: {len(esami)}")
    for e in esami:
        print(f"  {e.incentivo.id:>6} {e.stato:10} {e.incentivo.titolo[:70]}")
    print(f"Costo al piu' {len(esami) * COSTO_BANDO:.2f} $")
    if "--prova" in sys.argv:
        print("\nProva: nessuna pagina scaricata, nessuna chiamata al modello.")
        return
    if not fonte_presente():
        sys.exit(f"La fonte '{inc.CODICE_FONTE}' non e' nella tabella fonti.")

    fonte = inc.NOME_FONTE_PAGINA.format(data=data_file)
    estrattore = costruisci_estrattore()
    robots = inc.Robots()
    esiti = []
    try:
        with get_usage_metadata_callback() as contatore:
            for numero, e in enumerate(esami, start=1):
                print(f"\n[{numero}/{len(esami)}] {e.incentivo.titolo[:70]}")
                try:
                    esito, motivo, avvisi, riga = esamina_pagina(
                        estrattore, e, robots, fonte
                    )
                except (APIError, ValueError, KeyError, TypeError) as errore:
                    if errore_bloccante(errore):
                        print(f"\nINTERROTTO: credito o autenticazione ({errore})")
                        break
                    esito, motivo, avvisi, riga = "fallito", str(errore), "", None

                registra(
                    e.incentivo.url,
                    inc.CODICE_FONTE,
                    f"incentivi-{e.incentivo.id}",
                    esito,
                    motivo,
                    avvisi,
                )
                tipi = sorted(
                    {b["tipo"] for b in (riga or {}).get("beneficiari_ammessi", [])}
                )
                esiti.append((e, esito, motivo, tipi))
                print(f"    {esito} ({motivo[:90]})")
                print(f"    tipi: {', '.join(tipi) or '-'}")
                if avvisi:
                    print(f"    avvisi: {avvisi[:150]}")
                time.sleep(PAUSA)

        print("\n" + "=" * 74)
        for e, esito, motivo, tipi in esiti:
            pubblici = [t for t in tipi if t in TIPI_PUBBLICI]
            print(
                f"{e.incentivo.id:>6} {esito:9} enti pubblici: "
                f"{', '.join(pubblici) or 'esclusi'} | {e.incentivo.titolo[:50]} "
                f"| {motivo[:40]}"
            )
        mostra_costo(contatore.usage_metadata, len(esiti))
    finally:
        aggiorna_csv(
            "bandi",
            "beneficiari_bando",
            "interventi_bando",
            "scadenze_bando",
            "scansioni",
        )


if __name__ == "__main__":
    main()
