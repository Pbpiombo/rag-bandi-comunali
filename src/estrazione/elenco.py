"""Scoperta dei bandi dagli elenchi web delle fonti.

Fonti, elenchi e regole di lettura stanno nel database (tabelle fonti ed
elenchi, caricate da data/processed): qui c'e' solo la meccanica. Una
fonte di tipo 'pagine' ha uno o piu' elenchi; di ogni elenco si leggono i
collegamenti al dominio della fonte che corrispondono al suo schema_link,
tolti quelli esclusi. Una voce vista in piu' elenchi della stessa fonte
compare una volta. Le fonti di tipo 'file' non hanno elenchi da leggere.
"""

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from http.client import HTTPException
from urllib.parse import unquote, urljoin, urlsplit

from src.database.schema import connetti
from src.estrazione.indirizzi import url_canonico
from src.estrazione.pagina import scarica

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
    ripetizioni; errore: il motivo se l'elenco non si e' scaricato.
    """

    elenco: Elenco
    fonte: Fonte
    collegamenti: list[tuple[str, str]]
    errore: str | None = None


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


def elenchi_attivi() -> list[tuple[Fonte, list[Elenco]]]:
    """Le fonti di tipo 'pagine', ciascuna con i suoi elenchi attivi.

    L'ordine e' quello del database (fonte, poi indirizzo dell'elenco):
    lo stesso a ogni lancio.
    """
    conn = connetti()
    try:
        fonti = conn.execute(
            "SELECT * FROM fonti WHERE tipo = 'pagine' ORDER BY codice"
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


def collegamenti(html: str, url_pagina: str, fonte: Fonte) -> list[tuple[str, str]]:
    """Le voci di un elenco: (slug, url canonico), nell'ordine della pagina.

    Valgono solo i collegamenti al dominio della fonte il cui percorso
    corrisponde a schema_link. Lo slug e' il gruppo 'slug', senza punti e
    barre finali; l'URL e' url_base seguito dal gruppo 'percorso', con lo
    slug cosi' ripulito. Uno slug che corrisponde a esclusi, o gia' visto,
    si salta.
    """
    schema = re.compile(fonte.schema_link)
    esclusi = re.compile(fonte.esclusi, re.IGNORECASE) if fonte.esclusi else None

    lettore = _Collegamenti()
    lettore.feed(html)

    voci, visti = [], set()
    for href in lettore.href:
        indirizzo = urljoin(url_pagina, href)
        if _dominio(indirizzo) != fonte.dominio:
            continue
        m = schema.match(urlsplit(indirizzo).path)
        if not m:
            continue

        slug = m["slug"].rstrip("./")
        if not slug or slug in visti or (esclusi and esclusi.match(slug)):
            continue
        visti.add(slug)

        prima = m["percorso"][: m.start("slug") - m.start("percorso")]
        voci.append((slug, url_canonico(f"{fonte.url_base}/{prima}{slug}")))

    return voci


def leggi_elenco(elenco: Elenco, fonte: Fonte) -> list[tuple[str, str]]:
    """Scarica un elenco e ne restituisce le voci (slug, url canonico).

    L'ordine e' informativo: i portali presentano per primi i bandi
    pubblicati piu' di recente.
    """
    return collegamenti(scarica(elenco.url, timeout=ATTESA_ELENCO), elenco.url, fonte)


def leggi_elenchi() -> list[Letto]:
    """Legge tutti gli elenchi attivi. Un elenco che non si scarica non
    ferma gli altri: il suo errore resta nel risultato."""
    letti = []
    for fonte, elenchi in elenchi_attivi():
        for elenco in elenchi:
            try:
                letti.append(Letto(elenco, fonte, leggi_elenco(elenco, fonte)))
            except (OSError, HTTPException) as errore:
                letti.append(Letto(elenco, fonte, [], str(errore)))
    return letti


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
