"""Ricognizione del Portale della Regione, senza modello: primo tempo della scansione.

Uso:
    python -m scripts.ingestione.ricognizione
    python -m scripts.ingestione.ricognizione --pagine-salvate CARTELLA

Legge, attraverso Lettore (robots.txt, intestazione del progetto, pausa
per host, stop su 401 e 403, registro richieste.csv):
- i due elenchi attivi della Regione (tabella elenchi);
- la pagina di ogni voce nuova degli elenchi (non in archivio), per la
  sua scadenza;
- la pagina di ogni bando della Regione in archivio aperto, senza
  scadenza o scaduto da non piu' di GIORNI_FINESTRA giorni.

Della pagina si legge la scadenza dal campo della fonte, con la
preselezione che c'e' gia' (src/estrazione/scadenza.py), e la si
confronta con quella in archivio. Scrive un solo rapporto CSV,
ricognizione.csv, nella cartella del giorno dati-grezzi/scansioni/<data>/,
accanto a richieste.csv, con una riga per bando e gruppo (un bando puo'
stare in piu' gruppi):
- nuovi: voci degli elenchi che non sono in archivio, con la scadenza
  letta dalla pagina, o "non leggibile" (NON_LEGGIBILE); vuota, con il
  motivo nella nota, se la pagina non si e' letta;
- cambiati: scadenza della pagina diversa da quella in archivio;
- scaduti dal 13/11: scadenza tra ULTIMA_SCANSIONE e ieri, quella della
  pagina se si legge, se no quella dell'archivio;
- spariti: bandi aperti secondo quella scadenza che nessuno dei due
  elenchi riporta piu' (solo se entrambi gli elenchi si sono letti);
- vietati: indirizzi vietati dal robots.txt, mai richiesti;
- da verificare: scadenza non leggibile, o pagina non letta;
- invariati: bandi in archivio riletti senza differenze, elencati solo
  se hanno una nota (oggi: possibile proroga).

Per ogni pagina letta, dei bandi in archivio e dei nuovi, se il testo o i
nomi dei file collegati contengono una parola di proroga
(src/estrazione/proroga.py), la nota del bando dice "possibile proroga:"
con la frase o il titolo, tagliati a 200 battute. Il gruppo non cambia e
nessuna data si scrive: la data prorogata si legge nel secondo tempo,
dall'atto, con la sua frase di prova. Vale anche per le pagine gia'
salvate nella cartella del giorno, senza nuove richieste.

Non scrive nel database ne' in data/processed, non chiama il modello, non
tocca Chroma ne' Postgres. Lo stesso giorno, elenchi e pagine gia' letti
non si richiedono (Lettore, "gia' presente"); per rileggerli si toglie la
cartella del giorno. Un secondo rapporto dello stesso giorno prende il
suffisso -2, -3 e cosi' via.

--pagine-salvate CARTELLA: nessuna richiesta; valgono solo i file gia'
salvati in CARTELLA (robots/, elenchi/, pagine/), e il rapporto si scrive
li'. Una pagina che manca e' "da verificare". Serve ai test e a rifare il
rapporto su una cartella gia' letta.

Il secondo tempo, l'estrazione delle pagine scelte a mano, resta a
estrai_nuovi e riclassifica_bandi.
"""

import csv
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from src.database.schema import connetti
from src.estrazione.elenco import (
    FUSO,
    apri_scansione,
    da_fermare,
    descrivi,
    elenchi_attivi,
    id_da_slug,
    leggi_elenchi,
    leggi_pagina,
    lettore_della_scansione,
    scopri,
)
from src.estrazione.indirizzi import url_canonico
from src.estrazione.lettore_siti import VIETATO
from src.estrazione.pagina import a_testo
from src.estrazione.proroga import nota_di_proroga
from src.estrazione.scadenza import preselezione

FONTE = "regione-toscana"

# La scansione precedente, fatta una sola volta (roadmap, "Ordine dei passi")
ULTIMA_SCANSIONE = date(2026, 11, 13)

# I bandi scaduti da non piu' di tanti giorni si ricontrollano, per le
# proroghe (coda.md, requisiti della scansione, voce 7)
GIORNI_FINESTRA = 60

NUOVI = "nuovi"
CAMBIATI = "cambiati"
SCADUTI = "scaduti dal 13/11"
SPARITI = "spariti"
VIETATI = "vietati dal robots.txt"
DA_VERIFICARE = "da verificare"
INVARIATI = "invariati"
GRUPPI = (NUOVI, CAMBIATI, SCADUTI, SPARITI, VIETATI, DA_VERIFICARE, INVARIATI)

# La scadenza di un bando nuovo quando la pagina si legge ma il campo no
NON_LEGGIBILE = "non leggibile"

COLONNE = [
    "gruppo",
    "id_bando",
    "url",
    "titolo",
    "scadenza_archivio",
    "scadenza_pagina",
    "nota",
]


@dataclass
class Riga:
    gruppo: str
    id_bando: str
    url: str
    titolo: str
    scadenza_archivio: str = ""
    scadenza_pagina: str = ""
    nota: str = ""


@dataclass
class Rapporto:
    righe: list[Riga]
    # la corsa si e' fermata: un host fermato (401, 403, 429, robots.txt
    # illeggibile); quello che resta non si e' letto
    interrotta: bool
    fermati: dict[str, str]
    # gli elenchi non letti per intero: gli spariti non si calcolano
    elenchi_mancati: list[str]
    pagine_lette: int

    def conteggi(self) -> dict[str, int]:
        return {g: sum(r.gruppo == g for r in self.righe) for g in GRUPPI}


class ContaRichieste:
    """La funzione che apre gli indirizzi, con il conto delle richieste vere."""

    def __init__(self, apri) -> None:
        self._apri = apri
        self.quante = 0

    def __call__(self, url: str, intestazioni: dict):
        self.quante += 1
        return self._apri(url, intestazioni)


def bandi_da_ricontrollare(oggi: date) -> list[dict]:
    """I bandi della Regione aperti, senza scadenza o scaduti da non piu'
    di GIORNI_FINESTRA giorni. Le righe segnate come non bando no."""
    dal = (oggi - timedelta(days=GIORNI_FINESTRA)).isoformat()
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT id, titolo, url, scadenza, a_sportello FROM bandi "
            "WHERE codice_fonte = ? AND COALESCE(natura, 'bando') = 'bando' "
            "AND (scadenza IS NULL OR scadenza >= ?) ORDER BY id",
            (FONTE, dal),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in righe]


def gia_esaminati() -> dict[str, str]:
    """Per URL canonico, l'esito registrato in scansioni: per i nuovi."""
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT url, esito, motivo, esaminato_il FROM scansioni"
        ).fetchall()
    finally:
        conn.close()
    return {
        r["url"]: f"in scansioni: {r['esito']} il {r['esaminato_il']}"
        + (f" ({r['motivo']})" if r["motivo"] else "")
        for r in righe
    }


def _etichetta_scadenza() -> str | None:
    [(fonte, _)] = elenchi_attivi(FONTE)
    return fonte.etichetta_scadenza


def _nuovi(
    letti, lettore, righe: list[Riga], oggi: date, etichetta: str | None
) -> set[str]:
    """Le voci nuove degli elenchi, con la scadenza letta dalla loro pagina.

    La pagina si legge attraverso Lettore: una voce vietata dal robots.txt
    non si richiede e va tra i vietati; una pagina letta da' la scadenza
    del campo, o NON_LEGGIBILE; una pagina non letta resta tra i nuovi con
    il motivo nella nota. Un host fermato interrompe le letture: le voci
    rimaste restano tra i nuovi, senza scadenza. Restituisce gli URL di
    tutte le voci degli elenchi.
    """
    esaminati = gia_esaminati()
    voci = scopri(letti)
    for v in voci:
        if not v.nuovo:
            continue
        riga = Riga(NUOVI, id_da_slug(v.slug, v.url), v.url, v.titolo)
        note = [esaminati.get(url_canonico(v.url), "")]
        if da_fermare(lettore):
            note.append("pagina non letta: corsa interrotta")
        else:
            esito, html = leggi_pagina(lettore, v.url)
            if html is None and esito.stato == VIETATO:
                riga.gruppo = VIETATI
                note.append("voce nuova dell'elenco, non richiesta")
            elif html is None:
                note.append(f"pagina non letta: {descrivi(esito)}")
            else:
                scadenza = _scadenza_pagina(html, oggi, etichetta)
                riga.scadenza_pagina = (
                    scadenza.isoformat() if scadenza else NON_LEGGIBILE
                )
                note.append(nota_di_proroga(html))
        riga.nota = "; ".join(n for n in note if n)
        righe.append(riga)
    return {v.url for v in voci}


def _scadenza_pagina(html: str, oggi: date, etichetta: str | None) -> date | None:
    """La scadenza del campo della pagina, con la preselezione.

    Il filtro sull'anno e l'obbligo della scadenza non servono qui: si
    vuole solo la data del campo, se c'e' ed e' leggibile.
    """
    _, scadenza = preselezione(a_testo(html), True, oggi, False, etichetta=etichetta)
    return scadenza


def ricognisci(lettore, oggi: date) -> Rapporto:
    """Legge elenchi e pagine e costruisce il rapporto. Non scrive nel
    database; Lettore scrive solo nella sua cartella."""
    righe: list[Riga] = []
    letti = leggi_elenchi(FONTE, lettore=lettore)
    mancati = [f"{x.elenco.url}: {x.errore}" for x in letti if x.errore]
    if not letti:
        mancati.append(f"nessun elenco attivo per la fonte {FONTE}")
    interrotta = da_fermare(lettore)

    etichetta = _etichetta_scadenza()
    nell_elenco = (
        set() if interrotta else _nuovi(letti, lettore, righe, oggi, etichetta)
    )
    # un host fermato durante le pagine dei nuovi ferma anche il resto
    interrotta = da_fermare(lettore)
    lette = 0
    aperti = []
    # per i bandi in archivio: la riga di base e la nota di possibile proroga
    proroghe: list[tuple[Riga, str]] = []
    for bando in bandi_da_ricontrollare(oggi):
        url = url_canonico(bando["url"])
        archivio = bando["scadenza"] or ""
        base = Riga("", bando["id"], url, bando["titolo"], archivio)

        pagina = None
        if interrotta:
            righe.append(_come(base, DA_VERIFICARE, "non letta: corsa interrotta"))
        else:
            esito, html = leggi_pagina(lettore, url)
            interrotta = da_fermare(lettore)
            if html is None and esito.stato == VIETATO:
                righe.append(_come(base, VIETATI, "bando in archivio, non richiesto"))
            elif html is None:
                righe.append(
                    _come(base, DA_VERIFICARE, f"pagina non letta: {descrivi(esito)}")
                )
            else:
                lette += 1
                pagina = _scadenza_pagina(html, oggi, etichetta)
                righe.extend(_confronto(base, pagina, bando["a_sportello"]))
                if nota := nota_di_proroga(html):
                    proroghe.append((base, nota))

        # la scadenza che vale: quella della pagina se si legge
        attuale = pagina or (date.fromisoformat(archivio) if archivio else None)
        da_dove = "pagina" if pagina else "archivio"
        if attuale and ULTIMA_SCANSIONE <= attuale < oggi:
            righe.append(_come(base, SCADUTI, f"scadenza dalla {da_dove}"))
        if attuale is None or attuale >= oggi:
            aperti.append((base, da_dove))

    if not interrotta and not mancati:
        for base, da_dove in aperti:
            if base.url not in nell_elenco:
                righe.append(
                    _come(
                        base,
                        SPARITI,
                        f"aperto secondo la {da_dove}, in nessuno dei due elenchi",
                    )
                )

    _aggiungi_proroghe(righe, proroghe)
    ordine = {g: i for i, g in enumerate(GRUPPI)}
    righe.sort(key=lambda r: (ordine[r.gruppo], r.id_bando))
    return Rapporto(righe, interrotta, dict(lettore.fermati), mancati, lette)


def _aggiungi_proroghe(righe: list[Riga], proroghe: list[tuple[Riga, str]]) -> None:
    """La nota di possibile proroga su ogni riga del bando, senza cambiarne
    il gruppo. Un bando riletto senza differenze non ha righe: per non
    perdere la nota, entra tra gli INVARIATI con la sola nota."""
    for base, nota in proroghe:
        sue = [r for r in righe if r.url == base.url]
        for r in sue:
            r.nota = f"{r.nota}; {nota}" if r.nota else nota
        if not sue:
            righe.append(_come(base, INVARIATI, nota))


def _confronto(base: Riga, pagina: date | None, a_sportello) -> list[Riga]:
    """Da verificare se la scadenza della pagina non si legge, cambiato
    se e' diversa da quella in archivio. Scrive la scadenza della pagina
    in base, che vale per le righe successive dello stesso bando."""
    base.scadenza_pagina = pagina.isoformat() if pagina else ""
    if pagina is None:
        nota = "scadenza non leggibile dal campo della pagina"
        if a_sportello:
            nota += "; a sportello in archivio"
        return [_come(base, DA_VERIFICARE, nota)]
    if base.scadenza_pagina != base.scadenza_archivio:
        archivio = base.scadenza_archivio or "senza scadenza"
        return [
            _come(base, CAMBIATI, f"archivio {archivio}, pagina {base.scadenza_pagina}")
        ]
    return []


def _come(base: Riga, gruppo: str, nota: str) -> Riga:
    return Riga(
        gruppo,
        base.id_bando,
        base.url,
        base.titolo,
        base.scadenza_archivio,
        base.scadenza_pagina,
        nota,
    )


def scrivi_rapporto(rapporto: Rapporto, cartella: Path) -> Path:
    """ricognizione.csv nella cartella, senza sovrascrivere: -2, -3..."""
    cartella.mkdir(parents=True, exist_ok=True)
    percorso, numero = cartella / "ricognizione.csv", 2
    while percorso.exists():
        percorso = cartella / f"ricognizione-{numero}.csv"
        numero += 1
    with percorso.open("w", encoding="utf-8-sig", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=COLONNE, lineterminator="\r\n")
        scrittore.writeheader()
        for r in rapporto.righe:
            scrittore.writerow(r.__dict__)
    return percorso


def mostra(rapporto: Rapporto, percorso: Path, richieste: int) -> None:
    print("\nRICOGNIZIONE DEL PORTALE DELLA REGIONE (senza modello)")
    for gruppo, quanti in rapporto.conteggi().items():
        print(f"  {gruppo:24} {quanti}")
    print(f"\nPagine dei bandi lette: {rapporto.pagine_lette}")
    print(f"Richieste fatte ai siti: {richieste}")
    for mancato in rapporto.elenchi_mancati:
        print(f"Elenco non letto, spariti non calcolati: {mancato}")
    if rapporto.interrotta:
        print(f"INTERROTTA: host fermati {rapporto.fermati}")
    print(f"Rapporto: {percorso}")


def opzione_testo(nome: str) -> str | None:
    if nome not in sys.argv:
        return None
    posizione = sys.argv.index(nome)
    return sys.argv[posizione + 1] if posizione + 1 < len(sys.argv) else None


def data_di_oggi() -> date:
    """La data della ricognizione, in Europe/Rome (i test la fissano)."""
    return datetime.now(FUSO).date()


def main() -> None:
    oggi = data_di_oggi()
    salvate = opzione_testo("--pagine-salvate")
    contatore = ContaRichieste(apri_scansione)
    if salvate:
        lettore = lettore_della_scansione(Path(salvate), senza_rete=True)
    else:
        lettore = lettore_della_scansione(apri=contatore)
    print(f"Letture in {lettore.cartella}")

    rapporto = ricognisci(lettore, oggi)
    percorso = scrivi_rapporto(rapporto, lettore.cartella)
    mostra(rapporto, percorso, contatore.quante)
    if rapporto.interrotta:
        sys.exit(1)


if __name__ == "__main__":
    main()
