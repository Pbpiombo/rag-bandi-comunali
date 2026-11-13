"""Importa i bandi dal file open data di Incentivi Italia (piano fonti, tappa 5).

Uso:
    python -u -m scripts.ingestione.importa_incentivi --file PERCORSO --misura
    python -u -m scripts.ingestione.importa_incentivi --file PERCORSO --prova
    python -u -m scripts.ingestione.importa_incentivi --file PERCORSO

--file: OpenData_Incentivi.csv, scaricato a mano dalla pagina open data
del portale (sezione Incentivi, mai Aiuti), fuori dal repository.
--del AAAA-MM-GG: la data del file, citata nella fonte di ogni bando; se
manca, il nome della cartella del file, se e' una data.

--misura: senza rete e senza scrivere, quante righe passano la regola,
per classe di concedente e per stato, e i concedenti nuovi.
--prova: controlla le pagine degli enti, senza modello, e dice quante
righe si salverebbero e quante sono da verificare; non scrive nulla.
Senza opzioni: come --prova, poi salva le righe in bandi e
beneficiari_bando, registra salvate e da verificare in scansioni, ed
esporta i CSV, anche se si interrompe.

Nessuna chiamata al modello. Le righe aperte per enti pubblici si
elencano: la loro pagina si legge con il modello in un passo a parte.
"""

import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.database.schema import aggiorna_csv, connetti
from src.estrazione import incentivi as inc
from src.estrazione.indirizzi import url_canonico
from src.estrazione.pagina import scarica
from src.estrazione.registro import registra
from src.estrazione.salva import salva

# Pausa tra i download delle pagine degli enti
PAUSA_PAGINE = 0.5

# Il prefisso del motivo delle righe da verificare in scansioni: non
# comincia con "scaduto", cosi' tornano a ogni aggiornamento del file
PREFISSO_DA_VERIFICARE = "da verificare: "

ORDINE_STATI = (inc.APERTO, inc.SPORTELLO, inc.IN_ARRIVO, inc.STORICO)


def opzione_testo(nome: str) -> str | None:
    """Il valore di un'opzione testuale da riga di comando, se c'e'."""
    if nome not in sys.argv:
        return None
    posizione = sys.argv.index(nome)
    return sys.argv[posizione + 1] if posizione + 1 < len(sys.argv) else None


def data_del_file(percorso: Path) -> str:
    """La data del file: --del, oppure il nome della cartella."""
    valore = opzione_testo("--del") or percorso.parent.name
    try:
        return date.fromisoformat(valore).isoformat()
    except ValueError:
        sys.exit(
            f"Data del file non riconosciuta ('{valore}'): indicala con --del AAAA-MM-GG"
        )


def altre_fonti() -> set[str]:
    """Gli URL in bandi o in scansioni con una fonte diversa da questa."""
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT url FROM bandi WHERE codice_fonte <> ? "
            "UNION SELECT url FROM scansioni WHERE codice_fonte <> ?",
            (inc.CODICE_FONTE, inc.CODICE_FONTE),
        ).fetchall()
    finally:
        conn.close()
    return {url_canonico(r["url"]) for r in righe}


def fonte_presente() -> bool:
    """La fonte e' nella tabella fonti: senza, bandi e scansioni la rifiutano."""
    conn = connetti()
    try:
        riga = conn.execute(
            "SELECT 1 FROM fonti WHERE codice = ? AND tipo = 'file'",
            (inc.CODICE_FONTE,),
        ).fetchone()
    finally:
        conn.close()
    return riga is not None


def _breve(esame: inc.Esame) -> str:
    i = esame.incentivo
    return f"{i.id:>6} {esame.stato:10} {i.titolo[:70]}"


def mostra_ignorate(esami: list[inc.Esame]) -> None:
    conteggio = Counter(e.motivo for e in esami if e.esito == inc.IGNORATA)
    print(f"\nIgnorate: {sum(conteggio.values())}")
    for motivo, quante in conteggio.most_common():
        print(f"  {quante:5}  {motivo}")


def mostra_per_classe(esami: list[inc.Esame], esito: str, titolo: str) -> None:
    """Le righe con quell'esito, per stato e classe di concedente."""
    scelti = [e for e in esami if e.esito == esito]
    print(f"\n{titolo}: {len(scelti)}")
    tabella = Counter((e.stato, e.classe) for e in scelti)
    classi = inc.CLASSI_AMMESSE
    print(f"  {'stato':12}" + "".join(f"{c:>12}" for c in classi) + f"{'totale':>9}")
    for st in ORDINE_STATI:
        valori = [tabella[(st, c)] for c in classi]
        print(f"  {st:12}" + "".join(f"{v:>12}" for v in valori) + f"{sum(valori):>9}")


def mostra_elenco(esami: list[inc.Esame], esito: str, titolo: str) -> None:
    scelti = [e for e in esami if e.esito == esito]
    print(f"\n{titolo}: {len(scelti)}")
    for e in scelti:
        print(f"  {_breve(e)}")


def _gruppo(motivo: str) -> str:
    """Il motivo senza i dettagli della riga, per contarli insieme."""
    for separatore in (" (", ": ", ", la pagina"):
        motivo = motivo.split(separatore)[0]
    return motivo


def mostra_da_verificare(esami: list[inc.Esame]) -> None:
    scelti = [e for e in esami if e.esito == inc.DA_VERIFICARE]
    print(f"\nDa verificare a mano: {len(scelti)}")
    gruppi = defaultdict(list)
    for e in scelti:
        gruppi[_gruppo(e.motivo)].append(e)
    for motivo, voci in sorted(gruppi.items(), key=lambda x: -len(x[1])):
        print(f"  {len(voci):4}  {motivo}")
        for e in voci:
            print(f"          {_breve(e)} | {e.motivo[:90]}")


def mostra_concedenti_nuovi(esami: list[inc.Esame]) -> None:
    nuovi = Counter(
        e.incentivo.concedente
        for e in esami
        if e.esito == inc.DA_VERIFICARE and e.motivo.startswith("concedente non in")
    )
    print(f"\nConcedenti non in tabella: {len(nuovi)}")
    for nome, quante in nuovi.most_common():
        print(f"  {quante:3}  {nome}")


def mostra_avvisi(esami: list[inc.Esame]) -> None:
    avvisi = Counter(a for e in esami for a in e.avvisi)
    if avvisi:
        print(f"\nAvvisi: {sum(avvisi.values())}")
        for avviso, quanti in avvisi.most_common():
            print(f"  {quanti:4}  {avviso}")


def controlla_pagine(esami: list[inc.Esame]) -> None:
    """Il controllo sulla pagina dell'ente delle righe da salvare."""
    da_controllare = [e for e in esami if e.esito == inc.PAGINA]
    robots = inc.Robots()
    print(f"\nControllo di {len(da_controllare)} pagine degli enti, senza modello...")
    for numero, esame in enumerate(da_controllare, start=1):
        inc.controlla_pagina(esame, scarica, robots)
        if esame.esito == inc.SALVABILE:
            esame.riga = inc.prepara_salvataggio(esame)
        print(f"  [{numero}/{len(da_controllare)}] {_breve(esame)} -> {esame.esito}")
        time.sleep(PAUSA_PAGINE)


def scrivi(esami: list[inc.Esame], fonte: str) -> None:
    """Salva le righe salvabili e registra salvate e da verificare."""
    for esame in esami:
        url = esame.incentivo.url
        slug = f"incentivi-{esame.incentivo.id}"
        if esame.esito == inc.SALVABILE:
            salva(esame.riga, esame.incentivo.link, fonte, inc.CODICE_FONTE)
            registra(
                url,
                inc.CODICE_FONTE,
                slug,
                "salvato",
                inc.motivo_salvato(esame),
                "; ".join(esame.avvisi),
            )
        elif esame.esito == inc.DA_VERIFICARE and url:
            registra(
                url,
                inc.CODICE_FONTE,
                slug,
                "scartato",
                PREFISSO_DA_VERIFICARE + esame.motivo,
                "; ".join(esame.avvisi),
            )


def main() -> None:
    percorso = opzione_testo("--file")
    if not percorso:
        sys.exit("Indica il file con --file PERCORSO")
    percorso = Path(percorso)
    misura = "--misura" in sys.argv
    prova = "--prova" in sys.argv
    data_file = data_del_file(percorso)
    oggi = datetime.now(ZoneInfo("Europe/Rome")).date()

    try:
        incentivi = inc.leggi_file(percorso)
    except inc.FileNonValido as errore:
        sys.exit(f"File rifiutato: {errore}")
    print(f"File del {data_file}: {len(incentivi)} righe; data di riferimento {oggi}")

    condivisi = inc.link_condivisi(incentivi)
    esistenti = altre_fonti()
    esami = [inc.esamina(i, oggi, condivisi, esistenti) for i in incentivi]

    mostra_ignorate(esami)
    mostra_concedenti_nuovi(esami)
    if misura:
        mostra_per_classe(esami, inc.PAGINA, "Da controllare sulla pagina")
        mostra_elenco(esami, inc.AL_MODELLO, "Per enti pubblici, al modello")
        mostra_elenco(esami, inc.GIA_IN_ARCHIVIO, "Gia' in archivio da un'altra fonte")
        mostra_da_verificare(esami)
        print("\nMisura: nessuna pagina scaricata, nulla scritto.")
        return

    if not prova and not fonte_presente():
        sys.exit(
            f"La fonte '{inc.CODICE_FONTE}' non e' nella tabella fonti: aggiungila "
            "a data/processed/fonti.csv e ricrea il database."
        )

    controlla_pagine(esami)
    mostra_per_classe(esami, inc.SALVABILE, "Si salverebbero")
    mostra_elenco(
        esami, inc.AL_MODELLO, "Per enti pubblici, al modello (passo a parte)"
    )
    mostra_elenco(esami, inc.GIA_IN_ARCHIVIO, "Gia' in archivio da un'altra fonte")
    mostra_da_verificare(esami)
    mostra_avvisi(esami)

    if prova:
        print("\nProva: nessuna riga salvata, nulla registrato.")
        return

    try:
        scrivi(esami, inc.NOME_FONTE.format(data=data_file))
    finally:
        aggiorna_csv("bandi", "beneficiari_bando", "scansioni")


if __name__ == "__main__":
    main()
