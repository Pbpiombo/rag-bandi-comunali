"""I PDF della pagina di un bando, per l'elenco da approvare a mano (passo 19).

Compito 19a della roadmap: dall'HTML gia' salvato di una pagina si
ricavano i link ai PDF, ciascuno con un'etichetta e una classe proposta;
dai file gia' scaricati, gli indicatori di leggibilita' del testo. Ne
escono le righe dell'elenco, con la colonna "decisione" vuota: la scelta
del file da caricare e' sempre a mano. Qui non c'e' rete e non c'e'
modello: la lettura delle pagine, dei robots.txt e dei file e' del
compito 19b.

La classe e' una proposta, mai una decisione: le regole sono parole nel
testo del link e nel nome del file, in ordine, e vince la prima che
corrisponde (CLASSI). Il motivo dice quale parola ha deciso.

Gli indicatori si calcolano sul testo come lo legge carica_pdf, lo stesso
lettore dell'ingestione: misurano il testo che verrebbe caricato. Le
soglie del giudizio sono provvisorie, da tarare nel 19b sui file veri.

Limite noto: un link a un documento senza estensione nel percorso (per
esempio /documents/d/... senza .pdf) non si riconosce; si vedra' sulle
pagine vere del 19b.
"""

import csv
import hashlib
import io
import re
import statistics
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

from src.config import SOGLIA_PAGINA_MINIMA

# L'intestazione delle richieste del codice nuovo che legge i siti (dal
# compito 19b): dichiara il progetto, come scripts/manutenzione/
# carica_istat.py. INTESTAZIONI di src/estrazione/pagina.py non cambia
# (voce in docs/coda.md, dettaglio del passo 19).
INTESTAZIONI_PROGETTO = {"User-Agent": "Mozilla/5.0 (compatible; rag-bandi-comunali)"}

# Un documento: .pdf o .p7m alla fine del percorso o prima di un'altra
# parte del percorso (/x.pdf/uuid), in maiuscolo o minuscolo
DOCUMENTO = re.compile(r"\.(pdf|p7m)(/|$)", re.IGNORECASE)
P7M = re.compile(r"\.p7m(/|$)", re.IGNORECASE)

# Testi di link che non dicono nulla del file: l'etichetta viene dal nome
GENERICI = {
    "apri",
    "clicca qui",
    "download",
    "leggi",
    "link",
    "pdf",
    "qui",
    "scarica",
    "scarica il file",
    "visualizza",
}

# Le classi, nell'ordine delle regole: vince la prima che corrisponde.
# Il testo confrontato e' etichetta e nome del file, in minuscolo, con
# trattini, trattini bassi e punti trasformati in spazi.
CONSOLIDATO = "consolidato"
DA_DECIDERE = "da_decidere"
MODULISTICA = "modulistica"
AVVISO = "avviso"
ALLEGATO = "allegato"
ATTO = "atto"
ALTRO = "altro"

REGOLE = (
    (
        CONSOLIDATO,
        re.compile(
            r"testo coordinato|consolidat|aggiornat[oa] (?:alle|con le) modific"
            r"|testo integrat"
        ),
    ),
    (
        DA_DECIDERE,
        re.compile(
            r"rettific|errata corrige|prorog|graduatori|\belenco\b|ammessi"
            r"|\besit[oi]\b|\bfaq\b|estratto|\bburt\b|parte iii|assegnati"
            r"|revocat|rinunciatar"
        ),
    ),
    (
        MODULISTICA,
        re.compile(
            r"\bmodul[oi]\b|modulistica|\bdomanda\b|fac ?simile|dichiarazion"
            r"|\bschema\b|\bformat\b"
        ),
    ),
    (AVVISO, re.compile(r"avvis[oi]|\bband[oi]\b|disciplinar")),
    (ALLEGATO, re.compile(r"allegat|\ball [a-z0-9]\b")),
    (ATTO, re.compile(r"decret|delibera|determin")),
)

CLASSI = (*[classe for classe, _ in REGOLE], ALTRO)

# Un'etichetta che e' solo "Allegato A" o "All. A": in Regione Toscana
# l'avviso e' spesso l'allegato A del decreto
SOLO_ALLEGATO_A = re.compile(r"all(?:egato)? a")
PROBABILE_AVVISO = (
    "probabile avviso: in Regione Toscana l'avviso è spesso l'allegato A del decreto"
)

# Soglie del giudizio, provvisorie: da tarare nel compito 19b
CARATTERI_MINIMI_PER_PAGINA = 200  # mediana sotto: da OCR
QUOTA_PAGINE_VUOTE = 0.5  # oltre: da OCR
RIGA_BREVE = 40  # caratteri
QUOTA_RIGHE_BREVI = 0.6  # oltre: da rivedere (tabelle o colonne)
QUOTA_PAROLE_SPEZZATE = 0.15  # righe che finiscono con una parola spezzata
PAGINE_PER_RIPETUTE = 3  # sotto, le righe ripetute non si contano
RIGA_RIPETUTA_MINIMA = 5  # caratteri: le righe piu' brevi non si contano

LEGGIBILE = "leggibile"
DA_OCR = "da OCR"
DA_RIVEDERE = "da rivedere"

COLONNE_ELENCO = [
    "id_bando",
    "url_pagina",
    "n",
    "etichetta",
    "classe",
    "motivo_classe",
    "url_file",
    "host_file",
    "p7m",
    "pagine",
    "caratteri_per_pagina",
    "pagine_vuote",
    "righe_brevi",
    "righe_ripetute",
    "giudizio",
    "motivo_giudizio",
    "sha256",
    "decisione",
]


@dataclass(frozen=True)
class Collegamento:
    """Un link a un documento nella pagina di un bando."""

    url: str
    testo: str
    nome_file: str
    host: str
    p7m: bool


@dataclass(frozen=True)
class Indicatori:
    """La leggibilita' del testo estratto da un PDF."""

    pagine: int
    caratteri_per_pagina: int
    pagine_vuote: int
    righe_brevi: float
    righe_ripetute: int
    parole_spezzate: float


class _LettoreLink(HTMLParser):
    """Gli <a> della pagina: href, title e testo, nell'ordine."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.link: list[tuple[str, str, str]] = []
        self._aperto: list | None = None

    def handle_starttag(self, tag, attrs) -> None:
        if tag == "a":
            valori = dict(attrs)
            titolo = valori.get("title") or valori.get("aria-label") or ""
            self._aperto = [valori.get("href") or "", titolo, ""]

    def handle_data(self, data) -> None:
        if self._aperto is not None:
            self._aperto[2] += data

    def handle_endtag(self, tag) -> None:
        if tag == "a" and self._aperto is not None:
            href, titolo, testo = self._aperto
            self.link.append((href, titolo, testo))
            self._aperto = None


def _spazi(testo: str) -> str:
    return " ".join((testo or "").split())


def link_ai_documenti(html: str, url_pagina: str) -> list[Collegamento]:
    """I link a PDF e .p7m della pagina, nell'ordine e senza doppioni.

    L'url e' assoluto e senza ancora. Lo stesso file linkato piu' volte
    compare una volta, con il primo testo non generico. Un testo generico
    ("Leggi") cede il posto al title del link, se c'e'.
    """
    lettore = _LettoreLink()
    lettore.feed(html)

    trovati: dict[str, dict] = {}
    for href, titolo, testo in lettore.link:
        if not href:
            continue
        # mailto:, tel: e simili cadono sullo schema; un'ancora sulla pagina
        url = urldefrag(urljoin(url_pagina, href.strip()))[0]
        parti = urlsplit(url)
        if parti.scheme not in ("http", "https") or not DOCUMENTO.search(parti.path):
            continue
        testo = _spazi(testo)
        if generico(testo) and _spazi(titolo):
            testo = _spazi(titolo)
        if url in trovati:
            if generico(trovati[url]["testo"]) and not generico(testo):
                trovati[url]["testo"] = testo
            continue
        nome = unquote(DOCUMENTO.split(parti.path)[0].rsplit("/", 1)[-1])
        estensione = DOCUMENTO.search(parti.path).group(1).lower()
        trovati[url] = {
            "url": url,
            "testo": testo,
            "nome_file": f"{nome}.{estensione}",
            "host": parti.hostname or "",
            "p7m": bool(P7M.search(parti.path)),
        }
    return [Collegamento(**v) for v in trovati.values()]


def _da_nome(nome_file: str) -> str:
    """Il nome del file senza estensioni, con i separatori come spazi."""
    nome = re.sub(r"(\.(pdf|p7m))+$", "", nome_file, flags=re.IGNORECASE)
    return _spazi(re.sub(r"[_\-+]+", " ", nome))


def generico(testo: str) -> bool:
    """Il testo del link non dice nulla del file ("Leggi", "Clicca qui")."""
    pulito = re.sub(r"[^\w\s]", " ", (testo or "").lower())
    return _spazi(pulito) in GENERICI or not _spazi(pulito)


def etichetta(collegamento: Collegamento) -> str:
    """Il testo del link o, se vuoto o generico, il nome del file."""
    if generico(collegamento.testo):
        return _da_nome(collegamento.nome_file)
    return collegamento.testo


def _per_regole(testo: str) -> str:
    testo = unquote(testo or "").lower()
    return _spazi(re.sub(r"[_\-+.]+", " ", testo))


def classifica(etichetta: str, nome_file: str) -> tuple[str, str]:
    """La classe proposta e il motivo, dalla prima regola che corrisponde."""
    testo = _per_regole(f"{etichetta} {_da_nome(nome_file)}")
    for classe, schema in REGOLE:
        trovato = schema.search(testo)
        if not trovato:
            continue
        motivo = f"'{trovato.group(0)}'"
        if classe == ALLEGATO and SOLO_ALLEGATO_A.fullmatch(_per_regole(etichetta)):
            motivo += f"; {PROBABILE_AVVISO}"
        return classe, motivo
    return ALTRO, "nessuna parola decisiva"


def indicatori(pagine: list[str]) -> Indicatori:
    """Gli indicatori di leggibilita' dai testi delle pagine."""
    if not pagine:
        return Indicatori(0, 0, 0, 0.0, 0, 0.0)
    lunghezze = [len(p.strip()) for p in pagine]
    righe = [r.strip() for p in pagine for r in p.splitlines() if r.strip()]
    brevi = sum(1 for r in righe if len(r) < RIGA_BREVE)
    spezzate = sum(1 for r in righe if re.search(r"[^\W\d_]-$", r))

    ripetute = 0
    if len(pagine) >= PAGINE_PER_RIPETUTE:
        per_riga: dict[str, int] = {}
        for pagina in pagine:
            for riga in {r.strip() for r in pagina.splitlines()}:
                # le righe brevissime ("Pag.", numeri di pagina) non contano
                if len(riga) >= RIGA_RIPETUTA_MINIMA:
                    per_riga[riga] = per_riga.get(riga, 0) + 1
        ripetute = sum(1 for n in per_riga.values() if n > len(pagine) / 2)

    return Indicatori(
        pagine=len(pagine),
        caratteri_per_pagina=int(statistics.median(lunghezze)),
        pagine_vuote=sum(1 for n in lunghezze if n < SOGLIA_PAGINA_MINIMA),
        righe_brevi=round(brevi / len(righe), 2) if righe else 0.0,
        righe_ripetute=ripetute,
        parole_spezzate=round(spezzate / len(righe), 2) if righe else 0.0,
    )


def giudizio(ind: Indicatori) -> tuple[str, str]:
    """Leggibile, da OCR o da rivedere, con il motivo."""
    if ind.pagine == 0:
        return DA_OCR, "nessuna pagina"
    if ind.pagine_vuote / ind.pagine > QUOTA_PAGINE_VUOTE:
        return DA_OCR, f"{ind.pagine_vuote} pagine su {ind.pagine} senza testo"
    if ind.caratteri_per_pagina < CARATTERI_MINIMI_PER_PAGINA:
        return DA_OCR, f"{ind.caratteri_per_pagina} caratteri per pagina (mediana)"
    if ind.righe_brevi > QUOTA_RIGHE_BREVI:
        return DA_RIVEDERE, f"righe brevi {ind.righe_brevi:.0%}: tabelle o colonne"
    if ind.parole_spezzate > QUOTA_PAROLE_SPEZZATE:
        return DA_RIVEDERE, f"parole spezzate a fine riga {ind.parole_spezzate:.0%}"
    motivo = ""
    if ind.righe_ripetute:
        motivo = f"{ind.righe_ripetute} righe ripetute, da togliere al caricamento"
    return LEGGIBILE, motivo


def indicatori_pdf(percorso: str | Path) -> Indicatori:
    """Gli indicatori di un PDF, letto come lo legge l'ingestione."""
    # import qui: pdf_ingest carica Chroma, che non serve al resto del modulo
    from src.ingestion.pdf_ingest import carica_pdf

    return indicatori([p.page_content for p in carica_pdf(Path(percorso))])


def impronta_file(percorso: str | Path) -> str:
    """Lo sha256 del file."""
    return hashlib.sha256(Path(percorso).read_bytes()).hexdigest()


def righe_elenco(
    id_bando: str,
    url_pagina: str,
    collegamenti: list[Collegamento],
    letti: dict[str, tuple[Indicatori, str]] | None = None,
) -> list[dict]:
    """Le righe dell'elenco di un bando, nell'ordine della pagina.

    letti: per url del file, gli indicatori e lo sha256 dei file gia'
    scaricati; per gli altri le colonne restano vuote. decisione e'
    sempre vuota: si riempie a mano.
    """
    letti = letti or {}
    righe = []
    for numero, collegamento in enumerate(collegamenti, start=1):
        nome = etichetta(collegamento)
        classe, motivo = classifica(nome, collegamento.nome_file)
        riga = dict.fromkeys(COLONNE_ELENCO, "")
        riga.update(
            {
                "id_bando": id_bando,
                "url_pagina": url_pagina,
                "n": numero,
                "etichetta": nome,
                "classe": classe,
                "motivo_classe": motivo,
                "url_file": collegamento.url,
                "host_file": collegamento.host,
                "p7m": "sì" if collegamento.p7m else "no",
            }
        )
        if collegamento.url in letti:
            ind, sha256 = letti[collegamento.url]
            esito, perche = giudizio(ind)
            riga.update(
                {
                    "pagine": ind.pagine,
                    "caratteri_per_pagina": ind.caratteri_per_pagina,
                    "pagine_vuote": ind.pagine_vuote,
                    "righe_brevi": ind.righe_brevi,
                    "righe_ripetute": ind.righe_ripetute,
                    "giudizio": esito,
                    "motivo_giudizio": perche,
                    "sha256": sha256,
                }
            )
        righe.append(riga)
    return righe


def contenuto_elenco(righe: list[dict]) -> bytes:
    """Il CSV dell'elenco: UTF-8 con BOM, righe per bando e per numero."""
    ordinate = sorted(righe, key=lambda r: (r["id_bando"], int(r["n"])))
    buffer = io.StringIO(newline="")
    scrittore = csv.DictWriter(buffer, fieldnames=COLONNE_ELENCO, lineterminator="\r\n")
    scrittore.writeheader()
    scrittore.writerows(ordinate)
    return buffer.getvalue().encode("utf-8-sig")


def scrivi_elenco(righe: list[dict], percorso: str | Path) -> None:
    """Scrive l'elenco da approvare, sostituendo il file."""
    Path(percorso).write_bytes(contenuto_elenco(righe))


def tabella_elenco(righe: list[dict]) -> str:
    """L'elenco come tabelle markdown, una per bando, da mostrare in chat."""
    blocchi = []
    per_bando: dict[str, list[dict]] = {}
    for riga in sorted(righe, key=lambda r: (r["id_bando"], int(r["n"]))):
        per_bando.setdefault(riga["id_bando"], []).append(riga)
    for id_bando, sue in per_bando.items():
        testa = [
            f"{id_bando} — {sue[0]['url_pagina']}",
            "",
            (
                "| # | etichetta | classe | pag. | car./pag. | vuote | brevi "
                "| ripetute | giudizio | host | p7m |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        corpo = [
            f"| {r['n']} | {r['etichetta']} | {r['classe']} | {r['pagine']} "
            f"| {r['caratteri_per_pagina']} | {r['pagine_vuote']} "
            f"| {r['righe_brevi']} | {r['righe_ripetute']} | {r['giudizio']} "
            f"| {r['host_file']} | {r['p7m']} |"
            for r in sue
        ]
        blocchi.append("\n".join(testa + corpo))
    return "\n\n".join(blocchi)
