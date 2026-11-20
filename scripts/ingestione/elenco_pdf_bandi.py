"""Elenco dei PDF dei bandi della prima prova del passo 19 (compito 19b).

Uso, una fase per volta, con una fermata dopo ciascuna:
    python -u -m scripts.ingestione.elenco_pdf_bandi --robots
    python -u -m scripts.ingestione.elenco_pdf_bandi --pagine --data AAAA-MM-GG
    python -u -m scripts.ingestione.elenco_pdf_bandi --file --data AAAA-MM-GG

--robots: legge il robots.txt degli host delle pagine, lo stampa per
intero e dice per ogni pagina se e' consentita. Esce con errore se un
host vieta una pagina, rifiuta la richiesta o ha un robots.txt che non
si legge.
--pagine: legge e salva le pagine dei bandi, ne estrae i link ai PDF e
stampa per bando il piano di scarico. Per le pagine che sono notizie
(PAGINE_NOTIZIA) segue un solo passaggio verso la pagina dell'avviso, se
il candidato e' uno solo.
--file: scarica i file in ordine di probabilita', con i tetti, si ferma
per bando al primo file con le sezioni di un avviso (piu' gli allegati
richiamati per beneficiari o codici ATECO), scrive elenco.csv e stampa
la tabella. La colonna decisione resta vuota.

--data: la cartella dati-grezzi/avvisi/<data>/ da usare; senza, quella
di oggi. Quello che e' gia' nella cartella non si richiede di nuovo.
--senza-robots HOST: permette di procedere per un host il cui robots.txt
non si legge; la scelta va nel registro delle richieste. Ripetibile.
--bando ID: solo questo bando di PRIMA_PROVA o di BANDI_AGGIUNTI.
Ripetibile. I BANDI_AGGIUNTI si leggono solo se nominati con --bando.
--senza-rete: solo per --file; nessuna richiesta: si usano i file gia'
nella cartella e gli altri restano "non tentato (senza rete)". Serve a
ricomporre elenco.csv dopo una modifica delle regole.
--solo-primo: per ogni bando si tenta solo il primo file dell'ordine di
scarico; gli altri restano "non tentato". Serve alla prima prova su un
bando: se il primo file non e' un PDF o non ha le sezioni di un avviso,
ci si ferma li'.

Eccezione per i PDF degli avvisi (decisione del 19/11/2026, CLAUDE.md
"Lettura dei siti"): un file vietato dal robots.txt si scarica lo stesso
se il link sta in una pagina di bando consentita e la classe e' in
CLASSI_ECCEZIONE; restano pause, Crawl-delay, tetti e intestazione, e un
rifiuto tecnico resta un limite. Si spegne con ECCEZIONE_ROBOTS_AVVISI.
Modulistica e .p7m non si scaricano mai.

Regole di rete in src/estrazione/lettore_siti.py. Nessuna chiamata al
modello. I bandi sono quelli di PRIMA_PROVA; l'indirizzo di ogni pagina
si legge da data/processed/bandi.csv.
"""

import argparse
import csv
import hashlib
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import DATI_GREZZI_DIR, PROCESSED_DIR
from src.estrazione import pdf_bando as pb
from src.estrazione.grezzi import nome_sicuro
from src.estrazione.lettore_siti import (
    GIA_PRESENTE,
    NOME_PROGRAMMA,
    OK,
    Lettore,
    RobotsIlleggibile,
    host_di,
)
from src.estrazione.pagina import a_testo

# I 12 bandi della prima prova (immobili-emergenza-abitativa-2026 esclusa
# il 19/11/2026: e' un non_bando)
PRIMA_PROVA = (
    "fondo-strade-piccoli-comuni-2026",
    "parcheggi-2026",
    "cultura-missione-comune-2026",
    "sport-missione-comune-2026",
    "contributi-a-enti-locali-e-ets-per-punti-digitale-fac-8db4be",
    "contributi-agli-enti-locali-per-lo-sviluppo-di-proget-01bfe9",
    "contributi-per-uso-e-gestione-sostenibile-delle-risor-9d883c",
    "bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-7057d9",
    "bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-8cd3ac",
    "sostegno-agli-investimenti-strutturali-aziende-apisti-401650",
    "incentivi-8659",
    "sostegno-a-progetti-di-promozione-ed-educazione-music-e81761",
)

# Bandi aggiunti dopo la prima prova, uno per volta: si scelgono solo con
# --bando, e senza --bando la prova resta quella dei 12. Il fondo
# rievocazioni (compito 19c-4, 20/11/2026) ha la pagina già letta il
# 19/11/2026 (dati-grezzi/manuali/2026-11-19/), da copiare nella cartella
# del giorno prima di --pagine.
BANDI_AGGIUNTI = ("fondo-rievocazione-storica-2027",)

FUSO = ZoneInfo("Europe/Rome")

# Le pagine in archivio che sono notizie, non la pagina del bando
PAGINE_NOTIZIA = {"fondo-strade-piccoli-comuni-2026"}

FILE_PER_BANDO = 4
FILE_IN_TUTTO = 40
MASSIMO_FILE = 20 * 1024 * 1024  # byte
MASSIMO_PAGINA = 5 * 1024 * 1024  # byte

# Gli stati di scarico, oltre agli esiti del lettore
SCARICATO = "scaricato"
A_MANO = "a mano"
OLTRE_IL_TETTO = "oltre il tetto"
NON_NECESSARIO = "non necessario"
SCARICATO_ECCEZIONE = "scaricato (eccezione robots)"
ALTRO_ALTRO_HOST = "classe altro su un host diverso dalla pagina"
VERSIONE_SUPERATA = "versione superata"
SOSTITUITO = "sostituito dal consolidato"
AVVISO_IN_PIU_PARTI = "avviso in più parti"
NON_TENTATO = "non tentato (--solo-primo)"

# L'eccezione al robots.txt per i PDF degli avvisi, in un punto solo:
# False la spegne. Le classi a cui vale.
ECCEZIONE_ROBOTS_AVVISI = True
CLASSI_ECCEZIONE = (pb.CONSOLIDATO, pb.AVVISO, pb.PROROGA, pb.ALLEGATO)


class ErroreElenco(Exception):
    """Un dato mancante per procedere: si riporta, non si indovina."""


def cartella_di(data: str) -> Path:
    return DATI_GREZZI_DIR / "avvisi" / data


def bandi_della_prova(
    percorso: Path | None = None, ids: tuple[str, ...] = PRIMA_PROVA
) -> list[tuple[str, str]]:
    """(id, url della pagina) per i bandi della prova, da bandi.csv."""
    percorso = percorso or PROCESSED_DIR / "bandi.csv"
    with percorso.open(encoding="utf-8-sig", newline="") as f:
        url = {r["id"]: r["url"] for r in csv.DictReader(f)}
    mancanti = [i for i in ids if not url.get(i)]
    if mancanti:
        raise ErroreElenco("bandi senza indirizzo in bandi.csv: " + ", ".join(mancanti))
    return [(i, url[i]) for i in ids]


def file_pagina(cartella: Path, id_bando: str, seguita: bool = False) -> Path:
    suffisso = "--seguita" if seguita else ""
    return cartella / "pagine" / f"{nome_sicuro(id_bando)}{suffisso}.html"


def nome_del_file(collegamento_url: str, nome_file: str) -> str:
    """Il nome del file su disco: dal nome nel link e dall'indirizzo."""
    base = nome_sicuro(Path(nome_file).stem)[:60]
    codice = hashlib.sha1(collegamento_url.encode()).hexdigest()[:8]
    return f"{base}-{codice}.pdf"


def cartella_file(cartella: Path, id_bando: str) -> Path:
    return cartella / "file" / nome_sicuro(id_bando)


def testo_html(percorso: Path) -> str:
    return percorso.read_bytes().decode("utf-8", errors="ignore")


# --- fase 1: robots.txt ---


def fase_robots(lettore: Lettore, bandi: list[tuple[str, str]], stampa=print) -> bool:
    """Stampa i robots.txt e il permesso per pagina; False se ci si ferma."""
    per_host: dict[str, list[tuple[str, str]]] = {}
    for id_bando, url in bandi:
        per_host.setdefault(host_di(url), []).append((id_bando, url))

    tutto_bene = True
    for host, sue in per_host.items():
        try:
            regole = lettore.regole(sue[0][1])
        except RobotsIlleggibile as errore:
            stampa(f"\n=== {host}: {errore}")
            stampa(f"    per procedere comunque: --senza-robots {host}")
            tutto_bene = False
            continue
        stampa(f"\n=== {host}: robots.txt {regole.esito} ({regole.url})")
        stampa(f"    Crawl-delay per {NOME_PROGRAMMA}: {regole.crawl_delay}")
        stampa(f"    pausa tra le richieste: {lettore.pausa(host):g} s")
        if regole.testo:
            stampa("--- testo completo ---")
            stampa(regole.testo.rstrip())
            stampa("--- fine ---")
        for id_bando, url in sue:
            permesso = lettore.consentito(url)
            stampa(f"    {'consentita' if permesso else 'VIETATA'}: {id_bando} {url}")
            if not permesso:
                tutto_bene = False
        if host in lettore.fermati:
            stampa(f"    HOST FERMATO: {lettore.fermati[host]}")
            tutto_bene = False
    return tutto_bene


# --- fase 2: pagine ---


def indirizzo_seguita(cartella: Path, id_bando: str) -> str | None:
    """L'indirizzo della pagina seguita da una notizia, se c'e'."""
    seguita = file_pagina(cartella, id_bando, seguita=True)
    if not seguita.exists():
        return None
    return seguita.with_suffix(".url").read_text(encoding="utf-8").strip()


def pagine_consentite(
    lettore: Lettore, cartella: Path, id_bando: str, url: str
) -> bool:
    """La pagina del bando, e quella seguita, sono consentite dal robots.txt."""
    seguita = indirizzo_seguita(cartella, id_bando)
    return lettore.consentito(url) and (seguita is None or lettore.consentito(seguita))


def con_eccezione(riga: dict, pagine_ok: bool) -> bool:
    """Il file si chiede anche se il robots.txt lo vieta: eccezione per gli avvisi."""
    return (
        ECCEZIONE_ROBOTS_AVVISI
        and pagine_ok
        and riga["classe"] in CLASSI_ECCEZIONE
        and not pb.da_non_scaricare(riga)
    )


def host_delle_pagine(cartella: Path, id_bando: str, url: str) -> set[str]:
    """Gli host della pagina del bando e di quella seguita da una notizia."""
    seguita = indirizzo_seguita(cartella, id_bando)
    return {host_di(url)} | ({host_di(seguita)} if seguita else set())


def esclusione(riga: dict, host_pagine: set[str]) -> str | None:
    """Perche' un file non si scarica mai, o None.

    Modulistica e .p7m; un file di classe altro su un host diverso da
    quello della pagina del bando (per esempio un regolamento europeo).
    """
    motivo = pb.da_non_scaricare(riga)
    if motivo:
        return motivo
    if riga["classe"] == pb.ALTRO and riga["host_file"] not in host_pagine:
        return ALTRO_ALTRO_HOST
    return None


def da_scaricare(
    righe: list[dict], host_pagine: set[str], superate: list[dict] | None = None
) -> list[dict]:
    """Le righe in ordine di scarico, senza le escluse e le versioni superate."""
    superate = superate or []
    return [
        r
        for r in pb.ordine_di_scarico(righe)
        if not esclusione(r, host_pagine) and not any(r is s for s in superate)
    ]


def collegamenti_del_bando(
    cartella: Path, id_bando: str, url: str
) -> list[pb.Collegamento]:
    """I link ai documenti della pagina salvata, e di quella seguita."""
    principale = file_pagina(cartella, id_bando)
    if not principale.exists():
        raise ErroreElenco(f"pagina di {id_bando} non salvata: lancia prima --pagine")
    collegamenti = pb.link_ai_documenti(testo_html(principale), url)
    seguita = file_pagina(cartella, id_bando, seguita=True)
    if seguita.exists():
        url_seguita = indirizzo_seguita(cartella, id_bando)
        visti = {c.url for c in collegamenti}
        collegamenti += [
            c
            for c in pb.link_ai_documenti(testo_html(seguita), url_seguita)
            if c.url not in visti
        ]
    return collegamenti


def fase_pagine(
    lettore: Lettore, bandi: list[tuple[str, str]], cartella: Path, stampa=print
) -> None:
    """Legge le pagine, segue le notizie di un passaggio, stampa il piano."""
    for id_bando, url in bandi:
        esito = lettore.prendi(
            url, file_pagina(cartella, id_bando), "pagina", MASSIMO_PAGINA
        )
        stampa(f"\n=== {id_bando}: pagina {esito.stato} ({url})")
        if not esito.presente:
            continue

        righe = pb.righe_elenco(
            id_bando, url, pb.link_ai_documenti(testo_html(esito.percorso), url)
        )
        con_avviso = any(r["classe"] in (pb.AVVISO, pb.CONSOLIDATO) for r in righe)
        if id_bando in PAGINE_NOTIZIA and not con_avviso:
            segui_notizia(lettore, cartella, id_bando, url, esito.percorso, stampa)

        stampa_piano(lettore, cartella, id_bando, url, stampa)


def segui_notizia(lettore, cartella, id_bando, url, percorso, stampa) -> None:
    """Un solo passaggio dalla notizia alla pagina dell'avviso, se e' una."""
    candidati = pb.link_verso_avviso(testo_html(percorso), url)
    if len(candidati) != 1:
        stampa(f"    notizia: {len(candidati)} link verso un avviso, nessuno seguito")
        for candidato in candidati:
            stampa(f"      - {candidato}")
        return
    destinazione = file_pagina(cartella, id_bando, seguita=True)
    esito = lettore.prendi(candidati[0], destinazione, "pagina", MASSIMO_PAGINA)
    stampa(f"    notizia: seguito {candidati[0]} ({esito.stato})")
    if esito.presente:
        destinazione.with_suffix(".url").write_text(candidati[0], encoding="utf-8")


def stampa_piano(
    lettore: Lettore, cartella: Path, id_bando: str, url: str, stampa=print
) -> None:
    """Link e classi, ordine di scarico, file vietati dal robots.txt, host."""
    righe = pb.righe_elenco(
        id_bando, url, collegamenti_del_bando(cartella, id_bando, url)
    )
    stampa(f"    {len(righe)} link a documenti")
    for riga in righe:
        stampa(
            f"      {riga['n']:>2}. [{riga['classe']}] {riga['etichetta']} "
            f"({riga['host_file']}) {riga['motivo_classe']}"
        )
    host_pagine = host_delle_pagine(cartella, id_bando, url)
    superate, problema = pb.versioni(righe)
    if problema:
        stampa(f"    VERSIONI DA DECIDERE A MANO: {problema}")
    for riga in pb.ordine_di_scarico(righe):
        motivo = esclusione(riga, host_pagine) or (
            VERSIONE_SUPERATA if any(riga is s for s in superate) else None
        )
        if motivo:
            stampa(f"    escluso: {riga['n']} ({motivo})")
    ordine = da_scaricare(righe, host_pagine, superate)
    stampa(
        "    ordine di scarico: "
        + (", ".join(str(r["n"]) for r in ordine) or "nessun file")
        + f" (al massimo {FILE_PER_BANDO})"
    )
    pagine_ok = pagine_consentite(lettore, cartella, id_bando, url)
    for riga in ordine:
        noto = lettore.permesso_noto(riga["url_file"])
        if noto is False:
            seguito = (
                "si scarica per l'eccezione sugli avvisi"
                if con_eccezione(riga, pagine_ok)
                else "non si scarica"
            )
            stampa(f"    VIETATO dal robots.txt: {riga['n']} ({seguito})")
        elif noto is None:
            stampa(
                f"    robots.txt di {riga['host_file']} non ancora letto: {riga['n']}"
            )
    altri_host = sorted({r["host_file"] for r in ordine} - {host_di(url)})
    if altri_host:
        stampa(
            "    host dei file da controllare nel robots.txt: " + ", ".join(altri_host)
        )


# --- fase 3: file ed elenco ---


def esamina_pdf(percorso: Path) -> tuple[pb.Indicatori, str, list[str]]:
    from src.ingestion.pdf_ingest import carica_pdf

    pagine = [p.page_content for p in carica_pdf(percorso)]
    return pb.indicatori(pagine), pb.impronta_file(percorso), pagine


def completa_con_pdf(riga: dict, percorso: Path) -> tuple[bool, list[str]]:
    """Indicatori, sezioni e anteprima di un file; True se ha le sezioni di un avviso."""
    ind, sha256, pagine = esamina_pdf(percorso)
    pb.completa_riga(riga, ind, sha256)
    sezioni = pb.sezioni_avviso(pagine)
    riga["sezioni"] = pb.testo_sezioni(sezioni, riga["classe"], riga["giudizio"])
    riga["anteprima"] = pb.anteprima(pagine)
    return pb.e_avviso(sezioni, riga["classe"], riga["giudizio"])[0], pagine


def file_del_bando(
    lettore: Lettore,
    cartella: Path,
    id_bando: str,
    url: str,
    gia_scaricati: int,
    solo_primo: bool = False,
    stampa=print,
) -> tuple[list[dict], bool, int]:
    """Le righe dell'elenco di un bando, se l'avviso e' stato trovato, e i file presi.

    Prima i file messi a mano (nessuna richiesta), poi i link in ordine di
    scarico, fino al primo avviso; dopo l'avviso, solo gli allegati
    richiamati e le proroghe. Le versioni superate non si scaricano; un
    avviso dopo un consolidato con le sezioni e' "sostituito dal
    consolidato". Senza link di classe avviso o consolidato, gli allegati
    si scaricano tutti (nei tetti) e decide il contenuto: piu' file con
    le sezioni di un avviso sono un "avviso in piu' parti".
    gia_scaricati: i file gia' presi dagli altri bandi.
    """
    collegamenti = collegamenti_del_bando(cartella, id_bando, url)
    righe = pb.righe_elenco(id_bando, url, collegamenti)
    nomi = {
        r["url_file"]: nome_del_file(r["url_file"], c.nome_file)
        for r, c in zip(righe, collegamenti, strict=True)
    }
    dove = cartella_file(cartella, id_bando)
    testo_pagina = a_testo(testo_html(file_pagina(cartella, id_bando)))

    host_pagine = host_delle_pagine(cartella, id_bando, url)
    superate, problema = pb.versioni(righe)
    if problema:
        raise ErroreElenco(f"{id_bando}: {problema}")
    for riga in righe:
        stato = esclusione(riga, host_pagine) or (
            VERSIONE_SUPERATA if any(riga is s for s in superate) else None
        )
        if stato:
            riga["stato_scarico"] = stato

    trovato = False
    da_consolidato = False
    richiamati: list[dict] = []
    con_sezioni: list[dict] = []
    presi = 0
    pagine_ok = pagine_consentite(lettore, cartella, id_bando, url)
    ordine = da_scaricare([r for r in righe if r["url_file"]], host_pagine, superate)
    # "avviso in piu' parti" solo quando nessun link del bando ha classe
    # avviso o consolidato (decisione del 19/11/2026)
    in_parti = not any(
        r["classe"] in (pb.AVVISO, pb.CONSOLIDATO) for r in righe if r["url_file"]
    )

    def dopo_avviso(riga: dict, pagine: list[str]) -> None:
        nonlocal trovato, da_consolidato, richiamati
        con_sezioni.append(riga)
        if trovato:
            return
        trovato = True
        da_consolidato = riga["classe"] == pb.CONSOLIDATO
        richiamati = pb.allegati_richiamati([*pagine, testo_pagina], righe)

    def ancora_utile(riga: dict) -> bool:
        return (
            any(riga is r for r in richiamati)
            or riga["classe"] == pb.PROROGA
            or (in_parti and riga["classe"] == pb.ALLEGATO)
        )

    # file messi a mano: senza nessuna richiesta
    attesi = set(nomi.values())
    a_mano = (
        sorted(p for p in dove.glob("*.pdf") if p.name not in attesi)
        if dove.exists()
        else []
    )
    for numero, percorso in enumerate(a_mano, start=len(righe) + 1):
        riga = pb.riga_a_mano(id_bando, url, numero, percorso.name)
        riga["stato_scarico"] = A_MANO
        avviso, pagine = completa_con_pdf(riga, percorso)
        righe.append(riga)
        if avviso:
            dopo_avviso(riga, pagine)

    tentati = 0
    for riga in ordine:
        if solo_primo and tentati >= 1:
            riga["stato_scarico"] = NON_TENTATO
            continue
        if trovato and da_consolidato and riga["classe"] == pb.AVVISO:
            riga["stato_scarico"] = SOSTITUITO
            continue
        if trovato and not ancora_utile(riga):
            riga["stato_scarico"] = NON_NECESSARIO
            continue
        destinazione = dove / nomi[riga["url_file"]]
        if not destinazione.exists() and (
            presi >= FILE_PER_BANDO or gia_scaricati + presi >= FILE_IN_TUTTO
        ):
            riga["stato_scarico"] = OLTRE_IL_TETTO
            continue
        tentati += 1
        esito = lettore.prendi(
            riga["url_file"],
            destinazione,
            "file",
            MASSIMO_FILE,
            solo_pdf=True,
            eccezione_robots=con_eccezione(riga, pagine_ok),
        )
        stampa(
            f"  {id_bando} #{riga['n']}: {esito.stato}, HTTP {esito.codice}, "
            f"Content-Type {esito.tipo_contenuto or '?'}, {esito.byte} byte, "
            f"primi byte {esito.inizio!r}"
            + (" (eccezione robots)" if esito.eccezione else "")
        )
        riga["stato_scarico"] = {OK: SCARICATO, GIA_PRESENTE: GIA_PRESENTE}.get(
            esito.stato, esito.stato
        )
        if esito.eccezione:
            riga["stato_scarico"] = SCARICATO_ECCEZIONE
        if not esito.presente:
            continue
        presi += 1
        avviso, pagine = completa_con_pdf(riga, destinazione)
        if avviso:
            dopo_avviso(riga, pagine)
    if in_parti and len(con_sezioni) > 1:
        for riga in con_sezioni:
            riga["sezioni"] += f" | {AVVISO_IN_PIU_PARTI}"
    return righe, trovato, presi


def fase_file(
    lettore: Lettore,
    bandi: list[tuple[str, str]],
    cartella: Path,
    stampa=print,
    solo_primo: bool = False,
) -> list[dict]:
    """Scarica, verifica e scrive elenco.csv; stampa la tabella e i bandi senza avviso."""
    tutte: list[dict] = []
    senza_avviso = []
    presi = 0
    for id_bando, url in bandi:
        if not file_pagina(cartella, id_bando).exists():
            stampa(f"{id_bando}: pagina non salvata, nessun file")
            senza_avviso.append(id_bando)
            continue
        righe, trovato, quanti = file_del_bando(
            lettore, cartella, id_bando, url, presi, solo_primo, stampa
        )
        presi += quanti
        tutte += righe
        if not trovato:
            senza_avviso.append(id_bando)

    pb.scrivi_elenco(tutte, cartella / "elenco.csv")
    stampa(pb.tabella_elenco(tutte))
    stampa(f"\nFile presi: {presi} (tetto {FILE_IN_TUTTO})")
    stampa(
        "Nessun avviso riconosciuto: "
        + (", ".join(senza_avviso) if senza_avviso else "nessuno")
    )
    if lettore.fermati:
        for host, motivo in lettore.fermati.items():
            stampa(f"Host fermato: {host} ({motivo})")
    return tutte


# --- uso ---


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    fase = parser.add_mutually_exclusive_group(required=True)
    fase.add_argument("--robots", action="store_true")
    fase.add_argument("--pagine", action="store_true")
    fase.add_argument("--file", action="store_true")
    parser.add_argument("--data", type=date.fromisoformat, default=None)
    parser.add_argument("--senza-robots", action="append", default=[], metavar="HOST")
    parser.add_argument("--bando", action="append", default=[], metavar="ID")
    parser.add_argument("--solo-primo", action="store_true")
    parser.add_argument("--senza-rete", action="store_true")
    return parser.parse_args(argv)


def ids_della_prova(scelti: list[str]) -> tuple[str, ...]:
    """I 12 della prima prova, più i BANDI_AGGIUNTI nominati con --bando."""
    return PRIMA_PROVA + tuple(i for i in BANDI_AGGIUNTI if i in scelti)


def scegli_bandi(
    bandi: list[tuple[str, str]], scelti: list[str]
) -> list[tuple[str, str]]:
    """I bandi indicati con --bando, nell'ordine della prova; tutti se nessuno."""
    if not scelti:
        return bandi
    noti = {i for i, _ in bandi}
    estranei = [i for i in scelti if i not in noti]
    if estranei:
        raise ErroreElenco("bandi non della prova: " + ", ".join(estranei))
    return [(i, u) for i, u in bandi if i in scelti]


def main(
    argv: list[str] | None = None, lettore: Lettore | None = None, bandi=None
) -> int:
    argomenti = leggi_argomenti(argv)
    data = (argomenti.data or datetime.now(FUSO).date()).isoformat()
    cartella = lettore.cartella if lettore else cartella_di(data)
    lettore = lettore or Lettore(
        cartella, permetti_senza_robots=set(argomenti.senza_robots)
    )
    if argomenti.senza_rete:
        if not argomenti.file:
            print("Errore: --senza-rete vale solo con --file", file=sys.stderr)
            return 1
        lettore.senza_rete = True
    try:
        bandi = scegli_bandi(
            bandi or bandi_della_prova(ids=ids_della_prova(argomenti.bando)),
            argomenti.bando,
        )
        print(f"Cartella: {cartella}")
        if argomenti.robots:
            return 0 if fase_robots(lettore, bandi) else 1
        if argomenti.pagine:
            fase_pagine(lettore, bandi, cartella)
        else:
            fase_file(lettore, bandi, cartella, solo_primo=argomenti.solo_primo)
    except RobotsIlleggibile as errore:
        print(
            f"Fermato: {errore}. Per procedere: --senza-robots {errore.host}",
            file=sys.stderr,
        )
        return 1
    except ErroreElenco as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
