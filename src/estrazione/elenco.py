"""Scoperta dei bandi dagli elenchi web delle fonti.

Fonti, elenchi e regole di lettura stanno nel database (tabelle fonti ed
elenchi, caricate da data/processed): qui c'e' solo la meccanica. Una
fonte di tipo 'pagine' ha uno o piu' elenchi; di ogni elenco si leggono i
collegamenti al dominio della fonte che corrispondono al suo schema_link,
tolti quelli esclusi. Una voce vista in piu' elenchi della stessa fonte
compare una volta. Le fonti di tipo 'file' non hanno elenchi da leggere.

Di ogni elenco si tengono anche i collegamenti scartati (da schema_link o
da esclusi) e il totale che la pagina dichiara; se lo script indica una
cartella, l'elenco letto si conserva li', HTML e voci, per sapere dopo
che cosa conteneva.

Gli script leggono elenchi e pagine attraverso Lettore
(lettore_della_scansione, leggi_pagina): robots.txt, intestazione del
progetto, pausa per host, stop su 401 e 403, registro delle richieste in
dati-grezzi/scansioni/<data>/ (dal 23/11/2026; la scansione del 13/11
usava scarica, con l'intestazione di un browser e senza robots.txt).
"""

import csv
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from html.parser import HTMLParser
from http.client import HTTPException
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlsplit
from zoneinfo import ZoneInfo

from src.config import SCANSIONI_DIR
from src.database.schema import connetti
from src.estrazione import lettore_siti
from src.estrazione.indirizzi import url_canonico
from src.estrazione.lettore_siti import Esito, Lettore, RobotsIlleggibile
from src.estrazione.pagina import a_testo, scarica

FUSO = ZoneInfo("Europe/Rome")

# Lunghezza massima dell'identificativo di un bando, e del codice che lo
# chiude quando lo slug e' piu' lungo
LUNGHEZZA_ID = 60
LUNGHEZZA_CODICE = 6

# Parole nello slug che suggeriscono un bando rivolto a enti pubblici
INDIZI_COMUNE = re.compile(
    r"comun|enti-local|enti-pubblic|territori|amministrazion|"
    r"union[ei]|province|servizi-pubblic|patrimonio-pubblic|"
    r"scuol|nidi|bibliotec|muse|impiant|parcheggi|edifici|"
    r"montan|aree-intern|borgh|paesagg",
    re.IGNORECASE,
)

# Un anno a quattro cifre dentro lo slug, tra trattini o agli estremi. I
# trattini si controllano senza consumarli: in "annualita-2023-2025" il
# trattino tra i due anni serve a entrambi, e il 2025 non va perso.
ANNO_NELLO_SLUG = re.compile(r"(?<![^-])(20[0-2]\d)(?![^-])")

# Tempo massimo per scaricare un elenco: le pagine della Regione con 200
# voci arrivano a un minuto
ATTESA_ELENCO = 90

# Parametri dell'indirizzo che fissano quante voci mostra una pagina
# dell'elenco: delta per la Regione, _per_page per Sviluppo Toscana
PARAMETRI_DELTA = ("delta", "_per_page")

# Quota di delta oltre la quale l'elenco e' vicino al limite della pagina:
# le voci in piu' finirebbero in una seconda pagina, che non si legge
AVVISO_DELTA = 0.9

# Il totale dichiarato dalla pagina, nella forma "Risultati: 3 Bandi"
# (piano-fonti.md, tappa 2), con l'eventuale punto delle migliaia; e la
# forma dell'elenco vuoto
RISULTATI = re.compile(r"Risultati:\s*(\d{1,3}(?:\.\d{3})+|\d+)", re.IGNORECASE)
NESSUN_RISULTATO = re.compile(r"Nessun risultato trovato", re.IGNORECASE)

# Motivi di scarto di un collegamento al dominio della fonte
SCHEMA = "schema"
ESCLUSI = "esclusi"
VOCE = "voce"


@dataclass(frozen=True)
class Fonte:
    """Una riga della tabella fonti: chi e', e le regole per leggerla."""

    codice: str
    nome: str
    tipo: str
    url_base: str
    schema_link: str | None
    esclusi: str | None
    etichetta_scadenza: str | None
    filtro_anno_slug: bool
    scadenza_obbligatoria: bool

    @property
    def dominio(self) -> str:
        """Il dominio della fonte, senza "www.": i collegamenti accettati."""
        return _dominio(self.url_base)


@dataclass(frozen=True)
class Elenco:
    """Una pagina da cui si scoprono i bandi di una fonte."""

    url: str
    codice_fonte: str
    nome: str


@dataclass
class Letto:
    """Il risultato della lettura di un elenco.

    collegamenti: (slug, url canonico) nell'ordine della pagina, senza
    ripetizioni; errore: il motivo se l'elenco non si e' scaricato;
    scartati: (url, motivo) dei collegamenti al dominio della fonte
    scartati da schema_link (SCHEMA) o da esclusi (ESCLUSI); totale: le
    voci che la pagina dichiara, None se non lo dichiara o non si
    riconosce; copia: il file HTML conservato, None se non si conserva.
    """

    elenco: Elenco
    fonte: Fonte
    collegamenti: list[tuple[str, str]]
    errore: str | None = None
    scartati: list[tuple[str, str]] = field(default_factory=list)
    totale: int | None = None
    copia: Path | None = None


@dataclass
class Voce:
    """Un bando trovato in un elenco."""

    slug: str
    url: str
    codice_fonte: str
    titolo: str
    nuovo: bool
    promettente: bool
    anno: int | None
    recente: bool
    posizione: int
    fonte: Fonte
    elenco: str


def _dominio(url: str) -> str:
    return urlsplit(url).netloc.lower().removeprefix("www.")


def _fonte(riga) -> Fonte:
    return Fonte(
        codice=riga["codice"],
        nome=riga["nome"],
        tipo=riga["tipo"],
        url_base=riga["url_base"].rstrip("/"),
        schema_link=riga["schema_link"],
        esclusi=riga["esclusi"],
        etichetta_scadenza=riga["etichetta_scadenza"],
        filtro_anno_slug=bool(riga["filtro_anno_slug"]),
        scadenza_obbligatoria=bool(riga["scadenza_obbligatoria"]),
    )


def leggi_fonti() -> list[Fonte]:
    """Tutte le fonti del database, di ogni tipo."""
    conn = connetti()
    try:
        righe = conn.execute("SELECT * FROM fonti ORDER BY codice").fetchall()
    finally:
        conn.close()
    return [_fonte(r) for r in righe]


def elenchi_attivi(codice_fonte: str | None = None) -> list[tuple[Fonte, list[Elenco]]]:
    """Le fonti di tipo 'pagine', ciascuna con i suoi elenchi attivi.

    codice_fonte: solo quella fonte. L'ordine e' quello del database
    (fonte, poi indirizzo dell'elenco): lo stesso a ogni lancio.
    """
    conn = connetti()
    try:
        fonti = conn.execute(
            "SELECT * FROM fonti WHERE tipo = 'pagine' "
            "AND (? IS NULL OR codice = ?) ORDER BY codice",
            (codice_fonte, codice_fonte),
        ).fetchall()
        elenchi = conn.execute(
            "SELECT url, codice_fonte, nome FROM elenchi WHERE attivo = 1 "
            "ORDER BY codice_fonte, url"
        ).fetchall()
    finally:
        conn.close()

    return [
        (
            _fonte(f),
            [
                Elenco(e["url"], e["codice_fonte"], e["nome"])
                for e in elenchi
                if e["codice_fonte"] == f["codice"]
            ],
        )
        for f in fonti
    ]


def fonte_di(url: str) -> Fonte | None:
    """La fonte a cui appartiene un indirizzo, dal dominio di url_base."""
    dominio = _dominio(url)
    return next((f for f in leggi_fonti() if f.dominio == dominio), None)


class _Collegamenti(HTMLParser):
    """Gli href dei tag <a>, nell'ordine della pagina."""

    def __init__(self) -> None:
        super().__init__()
        self.href: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag == "a":
            self.href.extend(v for k, v in attrs if k == "href" and v)


def _analizza(html: str, url_pagina: str, fonte: Fonte) -> list[tuple[str, str, str]]:
    """I collegamenti al dominio della fonte, nell'ordine della pagina.

    Restituisce (slug, url, esito): esito VOCE per le voci dell'elenco,
    SCHEMA o ESCLUSI per gli scartati. Per una voce lo slug e' il gruppo
    'slug', senza punti e barre finali, e l'URL e' url_base seguito dal
    gruppo 'percorso', con lo slug cosi' ripulito.

    Tra gli scartati per SCHEMA entrano solo i percorsi con "/-/", la
    forma delle pagine di contenuto della Regione: i menu e le pagine di
    sezione non sono scarti. Per le fonti che non usano "/-/" il
    conteggio e' quindi sempre zero. Le ripetizioni non si contano; i
    collegamenti ad altri domini non sono scarti.
    """
    schema = re.compile(fonte.schema_link)
    esclusi = re.compile(fonte.esclusi, re.IGNORECASE) if fonte.esclusi else None

    lettore = _Collegamenti()
    lettore.feed(html)

    righe, visti, scartati_visti = [], set(), set()
    for href in lettore.href:
        indirizzo = urljoin(url_pagina, href)
        if _dominio(indirizzo) != fonte.dominio:
            continue
        percorso = urlsplit(indirizzo).path
        m = schema.match(percorso)
        if not m:
            url = url_canonico(indirizzo)
            if "/-/" in percorso and url not in scartati_visti:
                scartati_visti.add(url)
                righe.append(("", url, SCHEMA))
            continue

        slug = m["slug"].rstrip("./")
        if not slug or slug in visti:
            continue
        visti.add(slug)

        prima = m["percorso"][: m.start("slug") - m.start("percorso")]
        url = url_canonico(f"{fonte.url_base}/{prima}{slug}")
        righe.append((slug, url, ESCLUSI if esclusi and esclusi.match(slug) else VOCE))

    return righe


def collegamenti(html: str, url_pagina: str, fonte: Fonte) -> list[tuple[str, str]]:
    """Le voci di un elenco: (slug, url canonico), nell'ordine della pagina.

    Valgono solo i collegamenti al dominio della fonte il cui percorso
    corrisponde a schema_link. Lo slug e' il gruppo 'slug', senza punti e
    barre finali; l'URL e' url_base seguito dal gruppo 'percorso', con lo
    slug cosi' ripulito. Uno slug che corrisponde a esclusi, o gia' visto,
    si salta.
    """
    return [
        (slug, url)
        for slug, url, esito in _analizza(html, url_pagina, fonte)
        if esito == VOCE
    ]


def totale_dichiarato(html: str) -> int | None:
    """Le voci che la pagina dell'elenco dichiara di avere.

    Riconosce "Risultati: N" e "Nessun risultato trovato" (zero) nel
    testo della pagina, non nel markup. None se la pagina non dichiara
    un totale o lo scrive in una forma che non si riconosce.
    """
    testo = a_testo(html)
    trovato = RISULTATI.search(testo)
    if trovato:
        return int(trovato[1].replace(".", ""))
    if NESSUN_RISULTATO.search(testo):
        return 0
    return None


def delta_di(url: str) -> int | None:
    """Quante voci mostra una pagina dell'elenco, dal suo indirizzo.

    Legge il primo dei PARAMETRI_DELTA presente; None se non c'e' o non
    e' un numero.
    """
    parametri = parse_qs(urlsplit(url).query)
    for nome in PARAMETRI_DELTA:
        valori = parametri.get(nome)
        if valori and valori[0].isdigit():
            return int(valori[0])
    return None


def avviso_delta(url: str, totale: int | None, voci: int) -> str | None:
    """Un avviso se l'elenco supera o si avvicina al limite della pagina.

    Il confronto si fa con il totale dichiarato; se la pagina non lo
    dichiara, con le voci lette. Senza delta nell'indirizzo, nessun
    avviso.
    """
    delta = delta_di(url)
    if delta is None:
        return None
    if totale is not None and totale > delta:
        return (
            f"il totale dichiarato ({totale}) supera delta ({delta}): "
            "le voci oltre la prima pagina non si leggono"
        )
    quante, cosa = (totale, "dichiarate") if totale is not None else (voci, "lette")
    if quante >= AVVISO_DELTA * delta:
        return (
            f"{quante} voci {cosa} con delta {delta}: vicino al limite della "
            "pagina, le voci in piu' finirebbero in una seconda pagina non letta"
        )
    return None


def _nome_elenco(url: str) -> str:
    """Il nome dei file di un elenco: host, percorso e parametri ripuliti."""
    parti = urlsplit(url)
    nome = f"{parti.netloc}{parti.path}-{parti.query}".lower()
    return re.sub(r"[^a-z0-9]+", "-", nome).strip("-") or "elenco"


def _base_libera(cartella: Path, nome: str) -> Path:
    """Il primo nome non usato: nome, nome-2, nome-3, ... (senza estensione)."""
    base, numero = cartella / nome, 2
    while base.with_suffix(".html").exists() or base.with_suffix(".csv").exists():
        base = cartella / f"{nome}-{numero}"
        numero += 1
    return base


def conserva_elenco(
    cartella: Path,
    elenco: Elenco,
    html: str,
    righe: list[tuple[str, str, str]],
    quando: datetime | None = None,
) -> Path:
    """Conserva un elenco letto: l'HTML e le sue righe, in una cartella del giorno.

    Scrive <cartella>/<AAAA-MM-GG>/<nome>.html, l'HTML come lo restituisce
    scarica, e <nome>.csv con posizione, slug, url ed esito (voce, schema,
    esclusi) nell'ordine della pagina. Una seconda lettura dello stesso
    elenco nello stesso giorno prende il suffisso -2, -3 e cosi' via.
    Restituisce il percorso dell'HTML.
    """
    quando = quando or datetime.now(FUSO)
    giorno = cartella / quando.date().isoformat()
    giorno.mkdir(parents=True, exist_ok=True)

    base = _base_libera(giorno, _nome_elenco(elenco.url))
    pagina = base.with_suffix(".html")
    pagina.write_text(html, encoding="utf-8", newline="")

    with base.with_suffix(".csv").open("w", encoding="utf-8", newline="") as f:
        scrittore = csv.writer(f)
        scrittore.writerow(["posizione", "slug", "url", "esito"])
        for posizione, (slug, url, esito) in enumerate(righe, start=1):
            scrittore.writerow([posizione, slug, url, esito])

    return pagina


class LetturaMancata(Exception):
    """Lettore non ha dato la pagina: vietata, rifiutata, host fermato..."""


def leggi_elenco(
    elenco: Elenco,
    fonte: Fonte,
    cartella: Path | None = None,
    lettore: Lettore | None = None,
) -> Letto:
    """Scarica un elenco e ne restituisce voci, scartati e totale dichiarato.

    L'ordine delle voci e' informativo: i portali presentano per primi i
    bandi pubblicati piu' di recente. Con cartella, l'elenco letto si
    conserva (conserva_elenco); senza, non si scrive nulla.

    lettore: l'elenco si legge attraverso Lettore (robots.txt, intestazione
    del progetto, pausa per host, registro); un elenco che Lettore non da'
    solleva LetturaMancata. Senza lettore si usa scarica: resta per i test
    che la sostituiscono, gli script passano sempre un lettore.
    """
    if lettore is None:
        html = scarica(elenco.url, timeout=ATTESA_ELENCO)
    else:
        esito, html = leggi_pagina(lettore, elenco.url, "elenchi")
        if html is None:
            raise LetturaMancata(descrivi(esito))
    righe = _analizza(html, elenco.url, fonte)
    copia = conserva_elenco(cartella, elenco, html, righe) if cartella else None
    return Letto(
        elenco,
        fonte,
        [(slug, url) for slug, url, esito in righe if esito == VOCE],
        scartati=[(url, esito) for _, url, esito in righe if esito != VOCE],
        totale=totale_dichiarato(html),
        copia=copia,
    )


def leggi_elenchi(
    codice_fonte: str | None = None,
    cartella: Path | None = None,
    lettore: Lettore | None = None,
) -> list[Letto]:
    """Legge gli elenchi attivi, di tutte le fonti o di quella indicata.

    Un elenco che non si scarica non ferma gli altri: il suo errore resta
    nel risultato, e non se ne conserva copia. cartella: dove conservare
    gli elenchi letti; None, il valore predefinito, non scrive nulla.
    lettore: come in leggi_elenco. Dopo un host fermato (401, 403, 429) o
    un robots.txt illeggibile, Lettore non fa altre richieste a quell'host:
    gli elenchi rimasti hanno l'errore, senza richieste.
    """
    letti = []
    for fonte, elenchi in elenchi_attivi(codice_fonte):
        for elenco in elenchi:
            try:
                letti.append(leggi_elenco(elenco, fonte, cartella, lettore))
            except (OSError, HTTPException, LetturaMancata) as errore:
                letti.append(Letto(elenco, fonte, [], str(errore)))
    return letti


# --- letture attraverso Lettore ---

# Lunghezza massima del nome di un file salvato da Lettore, prima del
# codice che lo distingue: i percorsi di Windows restano sotto i 260
# caratteri anche con gli slug lunghi della Regione
LUNGHEZZA_NOME_FILE = 100

# Esito di una lettura il cui robots.txt non si legge: Lettore solleva
# RobotsIlleggibile e chi chiama si ferma, senza decidere da solo
ROBOTS_ILLEGGIBILE = "robots.txt non leggibile"


def lettore_della_scansione(
    cartella: Path | None = None, senza_rete: bool = False, apri=None
) -> Lettore:
    """Il Lettore delle scansioni: una cartella per giorno in SCANSIONI_DIR.

    Intestazione del progetto, robots.txt letto prima di ogni host, pausa
    per host (Crawl-delay o lettore_siti.PAUSA_PREDEFINITA), stop su 401 e
    403, registro richieste.csv nella cartella. Le richieste hanno il tempo
    di un elenco (ATTESA_ELENCO), non quello predefinito di Lettore.

    cartella: un'altra cartella al posto di quella del giorno; con
    senza_rete, nessuna richiesta: valgono solo i file gia' salvati li'.
    apri: la funzione che apre gli indirizzi, per i test.
    """
    if cartella is None:
        cartella = SCANSIONI_DIR / datetime.now(FUSO).date().isoformat()
    return Lettore(cartella, apri=apri or apri_scansione, senza_rete=senza_rete)


def apri_scansione(url: str, intestazioni: dict):
    """La richiesta vera di Lettore, con il tempo di un elenco (ATTESA_ELENCO)."""
    return lettore_siti._apri(url, intestazioni, timeout=ATTESA_ELENCO)


def nome_file(url: str) -> str:
    """Il nome del file di una pagina salvata da Lettore, senza estensione.

    Host, percorso e parametri ripuliti come per gli elenchi conservati;
    oltre LUNGHEZZA_NOME_FILE caratteri, il nome si taglia e si chiude con
    un codice dall'URL, perche' due slug lunghi con lo stesso inizio non
    finiscano nello stesso file.
    """
    nome = _nome_elenco(url)
    if len(nome) <= LUNGHEZZA_NOME_FILE:
        return nome
    codice = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"{nome[:LUNGHEZZA_NOME_FILE].rstrip('-')}-{codice}"


def leggi_pagina(
    lettore: Lettore, url: str, sottocartella: str = "pagine"
) -> tuple[Esito, str | None]:
    """Una pagina letta attraverso Lettore: l'esito e l'HTML, o None.

    La pagina si salva in <cartella del lettore>/<sottocartella>/; se c'e'
    gia' non si richiede (Lettore, "gia' presente"). Un indirizzo vietato
    dal robots.txt non si richiede e va nel registro come vietato. Un
    robots.txt illeggibile ferma l'host in Lettore (nel registro come
    "host fermato") e da' l'esito ROBOTS_ILLEGGIBILE: nessun'altra
    richiesta all'host, e chi chiama si ferma (da_fermare).
    """
    destinazione = lettore.cartella / sottocartella / f"{nome_file(url)}.html"
    try:
        esito = lettore.prendi(url, destinazione, "pagina")
    except RobotsIlleggibile as errore:
        lettore.ferma(errore.host, str(errore))
        return Esito(url, ROBOTS_ILLEGGIBILE, nota=str(errore)), None
    if not esito.presente:
        return esito, None
    return esito, destinazione.read_bytes().decode("utf-8", errors="ignore")


def descrivi(esito: Esito) -> str:
    """L'esito di una lettura mancata, in una riga."""
    parti = [esito.stato]
    if esito.codice:
        parti.append(f"HTTP {esito.codice}")
    if esito.nota:
        parti.append(esito.nota)
    return ", ".join(parti)


def da_fermare(lettore: Lettore) -> bool:
    """La corsa si ferma: un host fermato da Lettore (401, 403, 429 o
    robots.txt illeggibile). Mai un secondo tentativo con un'altra
    intestazione: Lettore usa sempre quella del progetto."""
    return bool(lettore.fermati)


def riepilogo_elenchi(letti: list[Letto]) -> str:
    """Per ogni elenco: voci, totale dichiarato, delta, copia e scartati.

    Un totale che non si legge si scrive "!! totale non letto !!", perche'
    si noti: senza totale non si sa se l'elenco e' stato letto per intero.
    """
    righe = ["Elenchi letti:"]
    for letto in letti:
        intestazione = f"  [{letto.fonte.codice}] {letto.elenco.url}"
        if letto.errore:
            righe.append(f"{intestazione}: ERRORE ({letto.errore})")
            continue

        totale = (
            f"totale dichiarato {letto.totale}"
            if letto.totale is not None
            else "!! totale non letto !!"
        )
        delta = delta_di(letto.elenco.url)
        delta = f", delta {delta}" if delta is not None else ""
        righe.append(f"{intestazione}: {len(letto.collegamenti)} voci, {totale}{delta}")

        avviso = avviso_delta(letto.elenco.url, letto.totale, len(letto.collegamenti))
        if avviso:
            righe.append(f"      AVVISO: {avviso}")
        if letto.copia:
            righe.append(f"      copia: {letto.copia}")

        for motivo, nome in ((SCHEMA, "schema_link"), (ESCLUSI, "esclusi")):
            scartati = [url for url, m in letto.scartati if m == motivo]
            righe.append(f"      scartati per {nome} ({len(scartati)})")
            righe.extend(f"        {url}" for url in scartati)

    return "\n".join(righe)


def _titolo_da_slug(slug: str) -> str:
    """Ricostruisce un titolo leggibile dal segmento dell'URL."""
    return slug.replace("-", " ").capitalize()


def promettente(slug: str) -> bool:
    """Lo slug suggerisce un bando rivolto a enti pubblici.

    E' un filtro grossolano per ridurre i candidati prima dell'estrazione,
    non una decisione: quella spetta alla lettura del testo.
    """
    return bool(INDIZI_COMUNE.search(slug))


def anno_slug(slug: str) -> int | None:
    """L'anno contenuto nello slug, se presente."""
    trovati = ANNO_NELLO_SLUG.findall(slug)
    return max(int(a) for a in trovati) if trovati else None


def recente(slug: str, anno_corrente: int | None = None) -> bool:
    """Lo slug non contiene un anno passato.

    Molte pagine restano nell'elenco per anni dopo la scadenza: l'anno
    nel nome e' il segnale piu' economico per riconoscerle. Uno slug
    senza anno resta candidato, perche' l'assenza non dice nulla.
    """
    anno_corrente = anno_corrente or date.today().year
    anno = anno_slug(slug)
    return anno is None or anno >= anno_corrente - 1


def id_da_slug(slug: str, url: str) -> str:
    """L'identificativo di un bando, ricavato dal suo slug.

    Decodifica le sequenze %XX, toglie gli accenti e sostituisce ogni
    carattere fuori da a-z, 0-9 e "-" con un trattino, cosi' l'id e'
    utilizzabile anche come nome di file. Se supera LUNGHEZZA_ID
    caratteri, lo taglia e lo chiude con un codice ricavato dall'URL
    canonico completo: due slug con lo stesso inizio danno id diversi.
    """
    testo = unicodedata.normalize("NFKD", unquote(slug))
    testo = testo.encode("ascii", "ignore").decode().lower()
    testo = re.sub(r"[^a-z0-9-]+", "-", testo)
    testo = re.sub(r"-{2,}", "-", testo).strip("-")

    if len(testo) <= LUNGHEZZA_ID:
        return testo

    codice = hashlib.sha1(url_canonico(url).encode("utf-8")).hexdigest()
    inizio = testo[: LUNGHEZZA_ID - LUNGHEZZA_CODICE - 1].rstrip("-")
    return f"{inizio}-{codice[:LUNGHEZZA_CODICE]}"


def gia_in_archivio(codice_fonte: str | None = None) -> set[str]:
    """Gli URL, in forma canonica, dei bandi gia' presenti nel database.

    Con codice_fonte, solo quelli di quella fonte.
    """
    conn = connetti()
    try:
        if codice_fonte is None:
            righe = conn.execute("SELECT url FROM bandi").fetchall()
        else:
            righe = conn.execute(
                "SELECT url FROM bandi WHERE codice_fonte = ?", (codice_fonte,)
            ).fetchall()
    finally:
        conn.close()

    return {url_canonico(r["url"]) for r in righe}


def scopri(letti: list[Letto] | None = None) -> list[Voce]:
    """Confronta gli elenchi delle fonti con l'archivio e segnala i nuovi.

    letti: gli elenchi gia' letti con leggi_elenchi; se manca, si leggono.
    Una voce vista in piu' elenchi della stessa fonte compare una volta,
    con l'elenco in cui e' comparsa per prima.
    """
    if letti is None:
        letti = leggi_elenchi()
    noti = gia_in_archivio()
    anno_corrente = date.today().year

    voci, visti = [], set()
    for letto in letti:
        for slug, url in letto.collegamenti:
            if url in visti:
                continue
            visti.add(url)
            voci.append(
                Voce(
                    slug=slug,
                    url=url,
                    codice_fonte=letto.fonte.codice,
                    titolo=_titolo_da_slug(slug),
                    nuovo=url not in noti,
                    promettente=promettente(slug),
                    anno=anno_slug(slug),
                    recente=recente(slug, anno_corrente),
                    posizione=len(voci) + 1,
                    fonte=letto.fonte,
                    elenco=letto.elenco.url,
                )
            )
    return voci
