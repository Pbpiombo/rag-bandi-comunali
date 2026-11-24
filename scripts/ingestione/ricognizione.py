"""Ricognizione del Portale della Regione, senza modello: primo tempo della scansione.

Uso:
    python -m scripts.ingestione.ricognizione
    python -m scripts.ingestione.ricognizione --pagine-salvate CARTELLA
        [--oggi AAAA-MM-GG] [--testi]

Legge, attraverso Lettore (robots.txt, intestazione del progetto, pausa
per host, stop su 401 e 403, registro richieste.csv):
- i due elenchi attivi della Regione (tabella elenchi);
- la pagina di ogni voce nuova degli elenchi (non in archivio e mai
  esaminata), per la sua scadenza;
- la pagina delle voci gia' esaminate (in scansioni, non in archivio)
  solo se l'esito di allora non e' definitivo o se erano scadute da non
  piu' di GIORNI_FINESTRA giorni;
- la pagina di ogni bando della Regione in archivio aperto, senza
  scadenza o scaduto da non piu' di GIORNI_FINESTRA giorni.

Della pagina si legge la scadenza dal campo della fonte, con la
preselezione che c'e' gia' (src/estrazione/scadenza.py), e la si
confronta con quella in archivio. Scrive un solo rapporto CSV,
ricognizione.csv, nella cartella del giorno dati-grezzi/scansioni/<data>/,
accanto a richieste.csv, con una riga per bando e gruppo (un bando puo'
stare in piu' gruppi):
- nuovi: voci degli elenchi che non sono in archivio (bandi) ne' in
  scansioni, con la scadenza letta dalla pagina, o "non leggibile"
  (NON_LEGGIBILE); vuota, con il motivo nella nota, se la pagina non si
  e' letta;
- gia' viste: voci degli elenchi in scansioni e non in archivio, con
  l'esito e il motivo di allora nella nota. La pagina si rilegge solo se
  quell'esito non e' definitivo (definitivi: "salvato", e gli scarti con
  i motivi di registro.DEFINITIVI, scaduto o non e' un bando) o se la
  scadenza di allora cade negli ultimi GIORNI_FINESTRA giorni; allora la
  riga ha anche la scadenza della pagina, come per i nuovi;
- cambiati: scadenza della pagina diversa da quella in archivio e da
  ogni finestra del bando in scadenze_bando;
- scaduti dal 13/11: scadenza tra ULTIMA_SCANSIONE e ieri, quella della
  pagina se si legge, se no quella dell'archivio;
- spariti: bandi aperti secondo quella scadenza che nessuno dei due
  elenchi riporta piu' (solo se entrambi gli elenchi si sono letti);
- vietati: indirizzi vietati dal robots.txt, mai richiesti;
- da verificare: scadenza non leggibile, o pagina non letta;
- invariati: bandi in archivio riletti senza differenze, elencati solo
  se hanno una nota: possibile proroga o sospensione, "a sportello" per
  un bando a sportello in archivio senza scadenza leggibile nel campo
  della pagina, o "il campo indica la finestra n. X di Y" se la data del
  campo e' diversa da quella in archivio ma coincide con una delle
  finestre del bando in scadenze_bando (solo le righe di genere
  "domanda", in ordine di numero). In questo caso la scadenza che vale,
  per gli scaduti e gli spariti, resta quella dell'archivio.

I titoli delle voci vengono dallo slug: le lettere scritte come %c3%a0
o come "c3-a0" si decodificano (_titolo_da_slug di
src/estrazione/elenco.py).

Per ogni pagina letta, dei bandi in archivio e dei nuovi, se il testo o i
nomi dei file collegati contengono una parola di proroga
(src/estrazione/proroga.py), la nota del bando dice "possibile proroga:"
con la frase intera (che non si spezza a "n." o "art.") o il titolo,
tagliati a 200 battute. Allo stesso modo, con le parole di
src/estrazione/sospensione.py, "possibile sospensione:", tranne le frasi
escluse come formule di rito. Il
gruppo non cambia e nessuna data si scrive: la data prorogata, o la
sospensione, si legge nel secondo tempo, dall'atto, con la sua frase di
prova. Vale anche per le pagine gia' salvate nella cartella del giorno,
senza nuove richieste.

Non scrive nel database ne' in data/processed, non chiama il modello, non
tocca Chroma ne' Postgres. Lo stesso giorno, elenchi e pagine gia' letti
non si richiedono (Lettore, "gia' presente"); per rileggerli si toglie la
cartella del giorno. Un secondo rapporto dello stesso giorno prende il
suffisso -2, -3 e cosi' via.

--pagine-salvate CARTELLA: nessuna richiesta; valgono solo i file gia'
salvati in CARTELLA (robots/, elenchi/, pagine/), e il rapporto si scrive
li'. Una pagina che manca e' "da verificare". Serve ai test e a rifare il
rapporto su una cartella gia' letta.

--oggi AAAA-MM-GG: la data della ricognizione, al posto di quella di
oggi (Europe/Rome). Serve a rifare il rapporto di una cartella salvata
alla sua data: scaduti, finestra di GIORNI_FINESTRA giorni e spariti
dipendono dalla data.

--testi: accanto al rapporto, nella cartella <nome del rapporto>-testi/,
un file <id_bando>.txt per ogni bando cambiato, per ogni bando con la
nota "possibile sospensione" e per ogni bando con frasi di sospensione
escluse come formule di rito (src/estrazione/sospensione.py, REGOLE),
anche se per questo non ha la nota: le righe di scadenze_bando (data,
genere, origine, frase di prova), la scadenza dell'archivio e quella del
campo, le frasi intere della pagina con una data e una parola come
scadenza, termine, entro, finestra, sportello, proroga, le frasi intere
con una parola di sospensione e, a parte, quelle escluse con la regola
che le ha escluse. Nessuna frase si taglia.

Il secondo tempo, l'estrazione delle pagine scelte a mano, resta a
estrai_nuovi e riclassifica_bandi.
"""

import csv
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from src.database.schema import connetti
from src.estrazione.elenco import (
    FUSO,
    _titolo_da_slug,
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
from src.estrazione.proroga import frasi_con, nota_di_proroga
from src.estrazione.registro import DEFINITIVI
from src.estrazione.scadenza import MESI, preselezione
from src.estrazione.sospensione import esamina as esamina_sospensione
from src.estrazione.sospensione import nota_di_sospensione

FONTE = "regione-toscana"

# La scansione precedente, fatta una sola volta (roadmap, "Ordine dei passi")
ULTIMA_SCANSIONE = date(2026, 11, 13)

# I bandi scaduti da non piu' di tanti giorni si ricontrollano, per le
# proroghe (coda.md, requisiti della scansione, voce 7)
GIORNI_FINESTRA = 60

NUOVI = "nuovi"
GIA_VISTE = "già viste"
CAMBIATI = "cambiati"
SCADUTI = "scaduti dal 13/11"
SPARITI = "spariti"
VIETATI = "vietati dal robots.txt"
DA_VERIFICARE = "da verificare"
INVARIATI = "invariati"
GRUPPI = (
    NUOVI,
    GIA_VISTE,
    CAMBIATI,
    SCADUTI,
    SPARITI,
    VIETATI,
    DA_VERIFICARE,
    INVARIATI,
)

# La scadenza di un bando nuovo quando la pagina si legge ma il campo no
NON_LEGGIBILE = "non leggibile"

# La nota di un bando a sportello in archivio senza scadenza nel campo
A_SPORTELLO = "a sportello"

# La data di uno scarto per scadenza registrato in scansioni
SCADUTO_IL = re.compile(r"scaduto il (\d{4}-\d{2}-\d{2})")

# La nota di un bando il cui campo indica una delle sue finestre
FINESTRA = "il campo indica la finestra n. {numero} di {quante}"

# Per --testi: una frase con una data e una parola di scadenza, cercate sul
# testo normalizzato (minuscolo, senza accenti)
DATA_NEL_TESTO = re.compile(
    r"(?<!\d)\d{1,2}(?:[./]\d{1,2}[./]\d{4}|\s+(?:" + "|".join(MESI) + r")\s+\d{4})"
)
PAROLA_DI_SCADENZA = re.compile(
    r"(?<!\w)(?:scadenz\w*|termin\w*|entro|finestr\w*|sportell\w*|prorog\w*)(?!\w)"
)
FRASE_DI_SCADENZA = re.compile(
    rf"(?=.*{DATA_NEL_TESTO.pattern})(?=.*{PAROLA_DI_SCADENZA.pattern})", re.DOTALL
)

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
class Testo:
    """Il materiale di un bando per il file di --testi."""

    base: Riga
    # le righe di scadenze_bando del bando, di ogni genere
    finestre: list[dict]
    html: str


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
    # per --testi: i bandi cambiati e quelli con frasi di sospensione,
    # valide o escluse
    testi: list[Testo] = field(default_factory=list)

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


def gia_esaminati() -> dict[str, dict]:
    """Per URL canonico, l'esito registrato in scansioni."""
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT url, esito, motivo, esaminato_il FROM scansioni"
        ).fetchall()
    finally:
        conn.close()
    return {r["url"]: dict(r) for r in righe}


def _nota_di_allora(esame: dict) -> str:
    return f"in scansioni: {esame['esito']} il {esame['esaminato_il']}" + (
        f" ({esame['motivo']})" if esame["motivo"] else ""
    )


def da_rileggere(esame: dict, oggi: date) -> bool:
    """Una voce gia' esaminata si rilegge se l'esito di allora non e'
    definitivo, o se era scaduta da non piu' di GIORNI_FINESTRA giorni
    (per le proroghe)."""
    motivo = esame["motivo"] or ""
    if trovata := SCADUTO_IL.match(motivo):
        scaduto = date.fromisoformat(trovata.group(1))
        return scaduto >= oggi - timedelta(days=GIORNI_FINESTRA)
    definitivo = esame["esito"] == "salvato" or (
        esame["esito"] == "scartato" and motivo.startswith(DEFINITIVI)
    )
    return not definitivo


def finestre_dei_bandi() -> dict[str, list[dict]]:
    """Per id del bando, le righe di scadenze_bando dei bandi della
    Regione, di ogni genere, in ordine di numero."""
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT s.id_bando, s.numero, s.genere, s.scadenza, s.origine, s.frase "
            "FROM scadenze_bando s JOIN bandi b ON b.id = s.id_bando "
            "WHERE b.codice_fonte = ? ORDER BY s.id_bando, s.numero",
            (FONTE,),
        ).fetchall()
    finally:
        conn.close()
    finestre: dict[str, list[dict]] = {}
    for r in righe:
        finestre.setdefault(r["id_bando"], []).append(dict(r))
    return finestre


def finestra_del_campo(pagina: date | None, finestre: list[dict]) -> str | None:
    """La nota FINESTRA se la data del campo coincide con una finestra del
    bando: solo le righe di genere "domanda", contate in ordine di numero."""
    if pagina is None:
        return None
    domande = [f for f in finestre if f["genere"] == "domanda"]
    for numero, finestra in enumerate(domande, start=1):
        if finestra["scadenza"] == pagina.isoformat():
            return FINESTRA.format(numero=numero, quante=len(domande))
    return None


def _etichetta_scadenza() -> str | None:
    [(fonte, _)] = elenchi_attivi(FONTE)
    return fonte.etichetta_scadenza


def _nuovi(
    letti,
    lettore,
    righe: list[Riga],
    oggi: date,
    etichetta: str | None,
    testi: list[Testo],
) -> set[str]:
    """Le voci degli elenchi fuori archivio: nuove o gia' viste.

    Una voce mai esaminata va tra i nuovi e la sua pagina si legge; una
    voce in scansioni va tra le gia' viste, con l'esito di allora, e la
    pagina si legge solo se da_rileggere. La pagina si legge attraverso
    Lettore: una voce vietata dal robots.txt non si richiede e va tra i
    vietati; una pagina letta da' la scadenza del campo, o NON_LEGGIBILE;
    una pagina non letta resta nel suo gruppo con il motivo nella nota.
    Un host fermato interrompe le letture: le voci rimaste restano nel
    loro gruppo, senza scadenza. Una pagina letta con la nota di
    possibile sospensione, o con frasi di sospensione escluse, entra in
    testi. Restituisce gli URL di tutte le
    voci degli elenchi.
    """
    esaminati = gia_esaminati()
    voci = scopri(letti)
    for v in voci:
        if not v.nuovo:
            continue
        esame = esaminati.get(url_canonico(v.url))
        riga = Riga(
            GIA_VISTE if esame else NUOVI,
            id_da_slug(v.slug, v.url),
            v.url,
            _titolo_da_slug(v.slug),
        )
        note = [_nota_di_allora(esame) if esame else ""]
        if esame and not da_rileggere(esame, oggi):
            pass  # esito definitivo: la pagina non si rilegge
        elif da_fermare(lettore):
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
                sospensione = nota_di_sospensione(html)
                note.append(sospensione)
                if sospensione or esamina_sospensione(html).escluse:
                    testi.append(Testo(riga, [], html))
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
    testi: list[Testo] = []
    nell_elenco = (
        set() if interrotta else _nuovi(letti, lettore, righe, oggi, etichetta, testi)
    )
    # un host fermato durante le pagine dei nuovi ferma anche il resto
    interrotta = da_fermare(lettore)
    lette = 0
    aperti = []
    # per i bandi in archivio: la riga di base e la nota di possibile
    # proroga o sospensione
    indizi: list[tuple[Riga, str]] = []
    tutte_le_finestre = finestre_dei_bandi()
    for bando in bandi_da_ricontrollare(oggi):
        url = url_canonico(bando["url"])
        archivio = bando["scadenza"] or ""
        base = Riga("", bando["id"], url, bando["titolo"], archivio)
        finestre = tutte_le_finestre.get(bando["id"], [])

        pagina = None
        # la data del campo e' una delle finestre: vale l'archivio
        finestra = None
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
                if base.scadenza_archivio != (pagina.isoformat() if pagina else ""):
                    finestra = finestra_del_campo(pagina, finestre)
                confronto = _confronto(base, pagina, bando["a_sportello"], finestra)
                righe.extend(confronto)
                if nota := nota_di_proroga(html):
                    indizi.append((base, nota))
                sospensione = nota_di_sospensione(html)
                if sospensione:
                    indizi.append((base, sospensione))
                if (
                    sospensione
                    or esamina_sospensione(html).escluse
                    or any(r.gruppo == CAMBIATI for r in confronto)
                ):
                    testi.append(Testo(base, finestre, html))

        # la scadenza che vale: quella della pagina se si legge, se non e'
        # una delle finestre del bando
        dalla_pagina = pagina is not None and finestra is None
        attuale = (
            pagina
            if dalla_pagina
            else (date.fromisoformat(archivio) if archivio else None)
        )
        da_dove = "pagina" if dalla_pagina else "archivio"
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

    _aggiungi_note(righe, indizi)
    ordine = {g: i for i, g in enumerate(GRUPPI)}
    righe.sort(key=lambda r: (ordine[r.gruppo], r.id_bando))
    return Rapporto(righe, interrotta, dict(lettore.fermati), mancati, lette, testi)


def _aggiungi_note(righe: list[Riga], indizi: list[tuple[Riga, str]]) -> None:
    """La nota di possibile proroga o sospensione su ogni riga del bando,
    senza cambiarne il gruppo. Un bando riletto senza differenze non ha
    righe: per non perdere la nota, entra tra gli INVARIATI con la sola
    nota; una seconda nota dello stesso bando si aggiunge a quella riga."""
    for base, nota in indizi:
        sue = [r for r in righe if r.url == base.url]
        for r in sue:
            r.nota = f"{r.nota}; {nota}" if r.nota else nota
        if not sue:
            righe.append(_come(base, INVARIATI, nota))


def _confronto(
    base: Riga, pagina: date | None, a_sportello, finestra: str | None = None
) -> list[Riga]:
    """Da verificare se la scadenza della pagina non si legge, ma tra gli
    invariati con la nota A_SPORTELLO se il bando e' a sportello in
    archivio; tra gli invariati con la nota finestra se la data del campo
    e' una delle finestre del bando (finestra_del_campo); cambiato se e'
    diversa da quella in archivio. Scrive la scadenza della pagina in
    base, che vale per le righe successive dello stesso bando."""
    base.scadenza_pagina = pagina.isoformat() if pagina else ""
    if pagina is None and a_sportello:
        return [_come(base, INVARIATI, A_SPORTELLO)]
    if pagina is None:
        nota = "scadenza non leggibile dal campo della pagina"
        return [_come(base, DA_VERIFICARE, nota)]
    if finestra:
        return [_come(base, INVARIATI, finestra)]
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


def testo_di(t: Testo) -> str:
    """Il contenuto del file di --testi per un bando: finestre, date e
    frasi intere della pagina, senza tagli."""
    b = t.base
    righe = [
        f"{b.titolo} [{b.id_bando}]",
        b.url,
        "",
        f"Scadenza in archivio: {b.scadenza_archivio or 'nessuna'}",
        f"Scadenza dal campo della pagina: {b.scadenza_pagina or 'non leggibile'}",
        "",
        f"Righe di scadenze_bando ({len(t.finestre)}):",
    ]
    righe += [
        f"  {f['numero']}. {f['scadenza']} ({f['genere']}, {f['origine']}): "
        f"{f['frase']}"
        for f in t.finestre
    ] or ["  nessuna"]
    sospensione = esamina_sospensione(t.html)
    escluse = [
        f"{e.frase} [esclusa: {'; '.join(e.regole)}]" for e in sospensione.escluse
    ]
    for titolo, frasi in (
        (
            "Frasi della pagina con una data e una parola di scadenza",
            frasi_con(t.html, FRASE_DI_SCADENZA),
        ),
        ("Frasi della pagina con una parola di sospensione", sospensione.valide),
        ("Frasi escluse come formule di rito", escluse),
    ):
        righe += ["", f"{titolo} ({len(frasi)}):"]
        righe += [f"  - {frase}" for frase in frasi] or ["  nessuna"]
    return "\n".join(righe) + "\n"


def scrivi_testi(rapporto: Rapporto, percorso: Path) -> Path:
    """Un file <id_bando>.txt per ogni bando in rapporto.testi, nella
    cartella <nome del rapporto>-testi/ accanto al rapporto."""
    cartella = percorso.with_name(f"{percorso.stem}-testi")
    cartella.mkdir(parents=True, exist_ok=True)
    for t in rapporto.testi:
        (cartella / f"{t.base.id_bando}.txt").write_text(testo_di(t), encoding="utf-8")
    return cartella


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
    if "--oggi" in sys.argv:
        valore = opzione_testo("--oggi") or ""
        try:
            oggi = date.fromisoformat(valore)
        except ValueError:
            sys.exit(f"--oggi vuole una data AAAA-MM-GG, non {valore!r}")
    salvate = opzione_testo("--pagine-salvate")
    contatore = ContaRichieste(apri_scansione)
    if salvate:
        lettore = lettore_della_scansione(Path(salvate), senza_rete=True)
    else:
        lettore = lettore_della_scansione(apri=contatore)
    print(f"Letture in {lettore.cartella}")
    print(f"Data della ricognizione: {oggi.isoformat()}")

    rapporto = ricognisci(lettore, oggi)
    percorso = scrivi_rapporto(rapporto, lettore.cartella)
    mostra(rapporto, percorso, contatore.quante)
    if "--testi" in sys.argv:
        cartella = scrivi_testi(rapporto, percorso)
        print(f"Testi di {len(rapporto.testi)} bandi: {cartella}")
    if rapporto.interrotta:
        sys.exit(1)


if __name__ == "__main__":
    main()
