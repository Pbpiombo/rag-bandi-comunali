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

Oltre ai link con .pdf o .p7m nel percorso, due forme del portale della
Regione Toscana viste il 19/11/2026 nelle pagine dei bandi (compito 19b):

- gli atti della banca dati, bancadati/atti/Contenuto.xml?id=...&nomeFile=...
  su www301: il nome del file e' nomeFile, decodificato; il formato si
  controlla allo scarico (%PDF);
- i documenti del portale /documents/d/...-pdf, e -p7m per i firmati.

Le stesse forme con -docx, -ods, -xlsx, .doc, .xls restano fuori: sono
moduli, non PDF.
"""

import csv
import hashlib
import io
import re
import statistics
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urldefrag, urljoin, urlsplit

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
# Gli atti della banca dati della Regione: il nome sta in nomeFile
ATTO_BANCADATI = re.compile(r"/bancadati/atti/Contenuto\.xml$", re.IGNORECASE)
# I documenti del portale della Regione: l'estensione e' un suffisso "-pdf"
DOCUMENTO_PORTALE = re.compile(r"/documents/d/.+-(pdf|p7m)$", re.IGNORECASE)

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
PROROGA = "proroga"
DA_DECIDERE = "da_decidere"
MODULISTICA = "modulistica"
AVVISO = "avviso"
ALLEGATO = "allegato"
ATTO = "atto"
ALTRO = "altro"

REGOLE = (
    # piu' versioni dello stesso testo (decisione del 19/11/2026): tra
    # piu' consolidati o avvisi vince il decreto piu' recente (versioni)
    (
        CONSOLIDATO,
        re.compile(
            r"testo coordinato|consolidat|aggiornat[oa] (?:alle|con le) modific"
            r"|testo integrat"
        ),
    ),
    # la proroga porta la scadenza vera: si scarica subito dopo l'avviso
    (PROROGA, re.compile(r"prorog|rettific|differiment|riapertur|errata corrige")),
    (
        DA_DECIDERE,
        re.compile(
            r"graduatori|\belenco\b|ammessi"
            r"|\besit[oi]\b|\bfaq\b|estratto|\bburt\b|parte iii|assegnati"
            r"|revocat|rinunciatar"
        ),
    ),
    (
        MODULISTICA,
        re.compile(
            r"\bmodul[oi]\b|modulistica|\bdomanda\b|fac ?simile|dichiarazion"
            r"|\bschema\b|\bformat\b|\bistanz[ae]\b|formulari"
        ),
    ),
    # "elementi essenziali" (la delibera con i criteri) e' un atto, anche
    # se dice "del bando"
    (ATTO, re.compile(r"elementi essenziali")),
    (
        AVVISO,
        re.compile(
            r"avvis[oi]|\bband[oi]\b|disciplinar|chiamata di progetti"
            r"|invito a presentare|manifestazion[ei] di interesse"
        ),
    ),
    (ALLEGATO, re.compile(r"allegat|\ball [a-z0-9]\b")),
    # "Testo Atto": il link al decreto quando nomeFile non dice nulla
    (ATTO, re.compile(r"decret|delibera|determin|\btesto (?:dell')?atto\b")),
)

CLASSI = (*dict.fromkeys(classe for classe, _ in REGOLE), ALTRO)

# Parole di una versione del testo, che fanno consolidato solo con
# "testo", "bando" o "avviso" nell'etichetta o nel nome del file:
# "Progetti ammissibili ... Allegato 1A aggiornato" resta un allegato
VERSIONE = re.compile(r"aggiornat|corrett|definitiv|coordinat")
DI_UN_TESTO = re.compile(r"\btesto\b|\bband[oi]\b|avvis[oi]")

# "istanza" fa modulistica, salvo "avviso" o "bando" nell'etichetta:
# "Avviso per la presentazione di istanze" resta un avviso
ISTANZA = re.compile(r"\bistanz[ae]\b")
AVVISO_IN_ETICHETTA = next(s for c, s in REGOLE if c == AVVISO)

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
    "stato_scarico",
    "anteprima",
    "sezioni",
    "decisione",
]

# Le sezioni di un avviso, cercate pagina per pagina (compito 19b)
SEZIONI = {
    "beneficiari": re.compile(
        r"soggetti beneficiari|beneficiari|soggetti ammess|"
        r"possono presentare (?:la )?domand|destinatari",
        re.IGNORECASE,
    ),
    "spese ammissibili": re.compile(
        r"spese ammissibili|spese ammesse|costi ammissibili|interventi ammissibili",
        re.IGNORECASE,
    ),
    "criteri o punteggio": re.compile(
        r"criteri di (?:valutazione|selezione)|punteggi|griglia di valutazione|premialit",
        re.IGNORECASE,
    ),
    "cumulo": re.compile(r"cumul", re.IGNORECASE),
    "modalità di presentazione": re.compile(
        r"modalit[àa] (?:di|e termini di) presentazione|"
        r"presentazione dell[ae] domand|termini di presentazione",
        re.IGNORECASE,
    ),
}
# I segnali contrari: un decreto, un modulo
DECRETA = "DECRETA"
SOTTOSCRITTO = "il sottoscritto dichiara"
CONTRARI = {
    DECRETA: re.compile(r"\bDECRETA\b"),
    SOTTOSCRITTO: re.compile(
        r"\b(?:il|la)\s+sottoscritt[oa]\b.{0,300}?\bdichiar", re.IGNORECASE | re.DOTALL
    ),
}
# Provvisoria: un file con almeno tante sezioni ha le sezioni di un avviso
SEZIONI_MINIME_AVVISO = 3
# Soglie provvisorie, tarate il 19/11/2026 sui 12 bandi della prima prova
# del passo 19: 3 sezioni per un link di classe avviso o consolidato; 4 per
# ogni altra classe, e mai con un testo "da rivedere" (una presentazione in
# slide passava con 3)
SEZIONI_MINIME_ALTRE = 4
CLASSI_DI_AVVISO = ("avviso", "consolidato")
# Un file con "il sottoscritto dichiara" su piu' di questa quota di pagine
# e' un modulo
QUOTA_PAGINE_MODULO = 0.5
# Pagine elencate per sezione nella colonna sezioni
PAGINE_PER_SEZIONE = 3
CARATTERI_ANTEPRIMA = 200

# L'ordine di scarico per classe; modulistica e .p7m non si scaricano
PRIORITA = {
    CONSOLIDATO: 0,
    AVVISO: 1,
    PROROGA: 2,
    # 3: allegato con "probabile avviso"
    ALLEGATO: 4,
    ATTO: 5,
    ALTRO: 6,
    DA_DECIDERE: 7,
}
PRIORITA_PROBABILE_AVVISO = 3

# Un allegato nominato vicino a beneficiari o codici ATECO
_ALLEGATO = r"(?i:allegat[oi])\s+(?:n\.\s*)?([A-Z]|\d{1,2})\b"
_MOTIVO_RICHIAMO = r"(?i:beneficiar|soggetti ammissibil|ateco)"
RICHIAMO = re.compile(
    rf"{_MOTIVO_RICHIAMO}.{{0,200}}?{_ALLEGATO}|{_ALLEGATO}.{{0,200}}?{_MOTIVO_RICHIAMO}",
    re.DOTALL,
)

# Un link che porta alla pagina di un avviso, per le pagine che sono
# notizie (il fondo strade del MIT)
VERSO_AVVISO = re.compile(r"avvis", re.IGNORECASE)


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
        if parti.scheme not in ("http", "https"):
            continue
        nome_file = nome_del_documento(parti)
        if nome_file is None:
            continue
        testo = _spazi(testo)
        if generico(testo) and _spazi(titolo):
            testo = _spazi(titolo)
        # lo stesso documento in http e in https e' uno solo
        chiave = urlsplit(url)._replace(scheme="https").geturl()
        if chiave in trovati:
            if generico(trovati[chiave]["testo"]) and not generico(testo):
                trovati[chiave]["testo"] = testo
            if parti.scheme == "https":
                trovati[chiave]["url"] = url
            continue
        trovati[chiave] = {
            "url": url,
            "testo": testo,
            "nome_file": nome_file,
            "host": parti.hostname or "",
            "p7m": nome_file.lower().endswith(".p7m"),
        }
    return [Collegamento(**v) for v in trovati.values()]


def nome_del_documento(parti) -> str | None:
    """Il nome del file di un link a un documento, o None se non lo e'.

    .pdf o .p7m nel percorso; un atto della banca dati con nomeFile; un
    documento del portale che finisce con -pdf o -p7m.
    """
    if DOCUMENTO.search(parti.path):
        nome = unquote(DOCUMENTO.split(parti.path)[0].rsplit("/", 1)[-1])
        return f"{nome}.{DOCUMENTO.search(parti.path).group(1).lower()}"
    if ATTO_BANCADATI.search(parti.path):
        nome = _spazi(parse_qs(parti.query).get("nomeFile", [""])[0])
        return f"{nome}.pdf" if nome else None
    trovato = DOCUMENTO_PORTALE.search(parti.path)
    if trovato:
        nome = unquote(parti.path.rsplit("/", 1)[-1])[: -len(trovato.group(1)) - 1]
        return f"{nome}.{trovato.group(1).lower()}"
    return None


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
    versione = VERSIONE.search(testo)
    if versione and DI_UN_TESTO.search(testo):
        return CONSOLIDATO, f"'{versione.group(0)}' in un testo"
    for classe, schema in REGOLE:
        trovato = schema.search(testo)
        if not trovato:
            continue
        if (
            classe == MODULISTICA
            and all(ISTANZA.fullmatch(m.group(0)) for m in schema.finditer(testo))
            and AVVISO_IN_ETICHETTA.search(_per_regole(etichetta))
        ):
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
            completa_riga(riga, *letti[collegamento.url])
        righe.append(riga)
    return righe


def completa_riga(riga: dict, ind: Indicatori, sha256: str) -> dict:
    """Aggiunge a una riga dell'elenco gli indicatori e lo sha256 del file."""
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
    return riga


def riga_a_mano(id_bando: str, url_pagina: str, n: int, nome_file: str) -> dict:
    """La riga di un PDF messo a mano nella cartella, senza link nella pagina."""
    riga = dict.fromkeys(COLONNE_ELENCO, "")
    classe, motivo = classifica(_da_nome(nome_file), nome_file)
    riga.update(
        {
            "id_bando": id_bando,
            "url_pagina": url_pagina,
            "n": n,
            "etichetta": _da_nome(nome_file),
            "classe": classe,
            "motivo_classe": motivo,
            "p7m": "no",
        }
    )
    return riga


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
                "| ripetute | giudizio | host | p7m | scarico | sezioni | anteprima |"
            ),
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        corpo = [
            f"| {r['n']} | {_cella(r['etichetta'])} | {r['classe']} | {r['pagine']} "
            f"| {r['caratteri_per_pagina']} | {r['pagine_vuote']} "
            f"| {r['righe_brevi']} | {r['righe_ripetute']} | {r['giudizio']} "
            f"| {r['host_file']} | {r['p7m']} | {r['stato_scarico']} "
            f"| {_cella(r['sezioni'])} | {_cella(r['anteprima'])[:80]} |"
            for r in sue
        ]
        blocchi.append("\n".join(testa + corpo))
    return "\n\n".join(blocchi)


def _cella(testo) -> str:
    """Un valore dentro una cella markdown: niente barre verticali."""
    return str(testo or "").replace("|", "/")


# --- compito 19b: verifica sul contenuto e ordine di scarico ---


@dataclass(frozen=True)
class Sezioni:
    """Le sezioni di un avviso trovate in un file, con le pagine fisiche."""

    pagine: int
    trovate: dict
    contrari: dict


def sezioni_avviso(pagine: list[str]) -> Sezioni:
    """Per ogni sezione e segnale contrario, le pagine (da 1) in cui compare."""
    trovate: dict[str, list[int]] = {}
    contrari: dict[str, list[int]] = {}
    for numero, testo in enumerate(pagine, start=1):
        for nome, schema in SEZIONI.items():
            if schema.search(testo):
                trovate.setdefault(nome, []).append(numero)
        for nome, schema in CONTRARI.items():
            if schema.search(testo):
                contrari.setdefault(nome, []).append(numero)
    return Sezioni(len(pagine), trovate, contrari)


def e_avviso(
    sezioni: Sezioni, classe: str | None = None, giudizio_testo: str | None = None
) -> tuple[bool, str]:
    """Il file ha le sezioni di un avviso, con una nota.

    Almeno SEZIONI_MINIME_AVVISO sezioni per un link di classe avviso o
    consolidato (e senza classe); per le altre classi almeno
    SEZIONI_MINIME_ALTRE, e mai con il testo "da rivedere". Salvo un
    modulo ("il sottoscritto dichiara" su piu' di QUOTA_PAGINE_MODULO
    delle pagine). Un decreto con le sezioni solo dopo "DECRETA" conta
    come avviso, con la segnalazione.
    """
    quante = len(sezioni.trovate)
    di_avviso = classe is None or classe in CLASSI_DI_AVVISO
    if quante < SEZIONI_MINIME_AVVISO:
        return False, f"{quante} sezioni su {len(SEZIONI)}"
    if not di_avviso and quante < SEZIONI_MINIME_ALTRE:
        return False, (
            f"{quante} sezioni su {len(SEZIONI)}: ne servono "
            f"{SEZIONI_MINIME_ALTRE} per la classe {classe}"
        )
    if not di_avviso and giudizio_testo == DA_RIVEDERE:
        return False, f"testo da rivedere: non vale come avviso per la classe {classe}"
    modulo = sezioni.contrari.get(SOTTOSCRITTO, [])
    if sezioni.pagine and len(modulo) / sezioni.pagine > QUOTA_PAGINE_MODULO:
        return False, f"modulo: '{SOTTOSCRITTO}' su {len(modulo)} pagine"
    decreta = sezioni.contrari.get(DECRETA, [])
    if decreta:
        prima = min(min(p) for p in sezioni.trovate.values())
        if prima > max(decreta):
            return True, f"decreto con l'avviso allegato da pag. {prima}"
    return True, ""


def testo_sezioni(
    sezioni: Sezioni, classe: str | None = None, giudizio_testo: str | None = None
) -> str:
    """La colonna sezioni: quante, quali con le pagine, i segnali contrari."""

    def pagine(numeri: list[int]) -> str:
        mostrate = ", ".join(str(n) for n in numeri[:PAGINE_PER_SEZIONE])
        return mostrate + (", …" if len(numeri) > PAGINE_PER_SEZIONE else "")

    parti = [f"{len(sezioni.trovate)} su {len(SEZIONI)}"]
    parti += [
        f"{nome} p. {pagine(sezioni.trovate[nome])}"
        for nome in SEZIONI
        if nome in sezioni.trovate
    ]
    testo = "; ".join(parti)
    if sezioni.contrari:
        contrari = "; ".join(
            f"{nome} p. {pagine(numeri)}" for nome, numeri in sezioni.contrari.items()
        )
        testo += f" | contrari: {contrari}"
    _, nota = e_avviso(sezioni, classe, giudizio_testo)
    if nota:
        testo += f" | {nota}"
    return testo


def anteprima(pagine: list[str], caratteri: int = CARATTERI_ANTEPRIMA) -> str:
    """Le prime righe della prima pagina con testo, su una riga sola."""
    for testo in pagine:
        righe = [_spazi(r) for r in testo.splitlines() if _spazi(r)]
        if righe:
            unite = " / ".join(righe)
            return unite if len(unite) <= caratteri else unite[: caratteri - 1] + "…"
    return ""


def da_non_scaricare(riga: dict) -> str | None:
    """Lo stato di una riga che non si scarica mai: modulistica o .p7m."""
    if riga["p7m"] == "sì":
        return "p7m"
    if riga["classe"] == MODULISTICA:
        return "modulistica"
    return None


def ordine_di_scarico(righe: list[dict]) -> list[dict]:
    """Le righe da scaricare, in ordine di probabilita' di essere l'avviso.

    Consolidato, avviso, allegato con "probabile avviso", poi gli altri;
    a parita', l'ordine della pagina. Modulistica e .p7m restano fuori.
    """

    def priorita(riga: dict) -> tuple[int, int]:
        classe = riga["classe"]
        valore = PRIORITA[classe]
        if classe == ALLEGATO and PROBABILE_AVVISO in riga["motivo_classe"]:
            valore = PRIORITA_PROBABILE_AVVISO
        return valore, int(riga["n"])

    return sorted((r for r in righe if not da_non_scaricare(r)), key=priorita)


# La data di un atto nel nome del file: 16-11-2026, 30_04_2026, 30.04.2026
DATA_NEL_NOME = re.compile(r"(\d{2})[-_.](\d{2})[-_.](\d{4})")


def nome_per_la_data(riga: dict) -> str:
    """Il nome del file di una riga: nomeFile per gli atti della banca dati."""
    parti = urlsplit(riga["url_file"])
    nome_file = parse_qs(parti.query).get("nomeFile")
    return nome_file[0] if nome_file else unquote(parti.path.rsplit("/", 1)[-1])


def data_del_documento(riga: dict) -> date | None:
    """La data dell'atto nel nome del file, o None se non si ricava."""
    trovata = DATA_NEL_NOME.search(nome_per_la_data(riga))
    if not trovata:
        return None
    giorno, mese, anno = (int(g) for g in trovata.groups())
    try:
        return date(anno, mese, giorno)
    except ValueError:
        return None


def versioni(righe: list[dict]) -> tuple[list[dict], str | None]:
    """Le versioni superate tra consolidati e avvisi dello stesso bando.

    Vince la versione con l'atto piu' recente, data dal nome del file
    (decisione del 19/11/2026). Con una sola versione nulla e' superato.
    Se una data non si ricava, o se piu' versioni hanno la data piu'
    recente, non si sceglie: restituisce il problema.
    """
    candidati = [
        r
        for r in righe
        if r["classe"] in (CONSOLIDATO, AVVISO)
        and r["url_file"]
        and not da_non_scaricare(r)
    ]
    if len(candidati) < 2:
        return [], None
    date_ = [(r, data_del_documento(r)) for r in candidati]
    senza = [r for r, d in date_ if d is None]
    if senza:
        return [], "data non ricavabile dal nome del file per " + ", ".join(
            f"{r['n']} ({r['etichetta']})" for r in senza
        )
    piu_recente = max(d for _, d in date_)
    vincitori = [r for r, d in date_ if d == piu_recente]
    if len(vincitori) > 1:
        return [], f"stessa data ({piu_recente.isoformat()}) per " + ", ".join(
            f"{r['n']} ({r['etichetta']})" for r in vincitori
        )
    return [r for r, _ in date_ if r is not vincitori[0]], None


def allegati_richiamati(testi: list[str], righe: list[dict]) -> list[dict]:
    """Le righe degli allegati nominati vicino a beneficiari o codici ATECO.

    testi: le pagine dell'avviso e il testo della pagina del bando. Un
    allegato si riconosce dalla lettera o dal numero ("Allegato B"),
    confrontato con etichetta e nome del file della riga.
    """
    sigle = set()
    for testo in testi:
        for trovato in RICHIAMO.finditer(testo):
            sigle.add((trovato.group(1) or trovato.group(2)).lower())
    scelte = []
    for riga in righe:
        if da_non_scaricare(riga):
            continue
        testo = _per_regole(
            f"{riga['etichetta']} {riga['url_file'].rsplit('/', 1)[-1]}"
        )
        if any(re.search(rf"\ball(?:egato)? {re.escape(s)}\b", testo) for s in sigle):
            scelte.append(riga)
    return scelte


def link_verso_avviso(html: str, url_pagina: str) -> list[str]:
    """I link di una pagina-notizia che portano alla pagina di un avviso.

    Link http o https, non a PDF, diversi dalla pagina stessa, con "avvis"
    nel testo o nell'indirizzo; senza doppioni, nell'ordine della pagina.
    """
    lettore = _LettoreLink()
    lettore.feed(html)
    pagina = urldefrag(url_pagina)[0]
    trovati: list[str] = []
    for href, titolo, testo in lettore.link:
        if not href:
            continue
        url = urldefrag(urljoin(url_pagina, href.strip()))[0]
        parti = urlsplit(url)
        if parti.scheme not in ("http", "https") or DOCUMENTO.search(parti.path):
            continue
        if url == pagina or url in trovati:
            continue
        if VERSO_AVVISO.search(f"{testo} {titolo} {unquote(parti.path)}"):
            trovati.append(url)
    return trovati
