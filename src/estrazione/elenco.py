"""Scoperta dei bandi pubblicati sul portale della Regione Toscana."""

import re
from dataclasses import dataclass
from datetime import date

from src.database.schema import connetti
from src.estrazione.indirizzi import url_canonico
from src.estrazione.pagina import scarica

CODICE_FONTE = "regione-toscana"
ELENCO = "https://www.regione.toscana.it/bandi-aperti?delta=200"
BASE = "https://www.regione.toscana.it"

# Lo slug di una pagina del portale, dopo "/-/". Puo' contenere "." e "/"
# (es. "museo/ecomuseo", "a.s.-2025-26"): una regex che li escludesse
# taglierebbe lo slug e confonderebbe pagine diverse.
SLUG_NEL_LINK = re.compile(r"/-/([a-z0-9][a-z0-9./-]{10,})")

# Voci del portale che non sono bandi
ESCLUSI = {
    "accessibilita-e-uso-del-sito",
    "atti-di-notifica",
    "bandi-di-concorso-e-avvisi",
    "note-legali",
    "privacy",
    "mappa-del-sito",
    "contatti",
}

PAROLE_ESCLUSE = re.compile(
    r"^(accessibilit|note-legali|privacy|mappa|contatti|"
    r"amministrazione-trasparente|urp|newsletter)",
    re.IGNORECASE,
)

# Parole nello slug che suggeriscono un bando rivolto a enti pubblici
INDIZI_COMUNE = re.compile(
    r"comun|enti-local|enti-pubblic|territori|amministrazion|"
    r"union[ei]|province|servizi-pubblic|patrimonio-pubblic|"
    r"scuol|nidi|bibliotec|muse|impiant|parcheggi|edifici|"
    r"montan|aree-intern|borgh|paesagg",
    re.IGNORECASE,
)

# Un anno a quattro cifre dentro lo slug
ANNO_NELLO_SLUG = re.compile(r"(?:^|-)(20[0-2]\d)(?:-|$)")


@dataclass
class Voce:
    """Un bando trovato nell'elenco del portale."""

    slug: str
    url: str
    codice_fonte: str
    titolo: str
    nuovo: bool
    promettente: bool
    anno: int | None
    recente: bool
    posizione: int


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


def leggi_elenco() -> list[str]:
    """Gli slug dei bandi nell'elenco, nell'ordine in cui compaiono.

    L'ordine e' informativo: il portale presenta per primi i bandi
    pubblicati piu' di recente.
    """
    html = scarica(ELENCO, timeout=60)

    trovati = [s.rstrip("./") for s in SLUG_NEL_LINK.findall(html)]

    ordinati = []
    for s in trovati:
        if s in ordinati or s in ESCLUSI or PAROLE_ESCLUSE.match(s):
            continue
        ordinati.append(s)

    return ordinati


def url_da_slug(slug: str) -> str:
    """L'URL, in forma canonica, della pagina del portale con quello slug."""
    return url_canonico(f"{BASE}/-/{slug}")


def gia_in_archivio() -> set[str]:
    """Gli URL, in forma canonica, dei bandi gia' presenti nel database."""
    conn = connetti()
    try:
        righe = conn.execute("SELECT url FROM bandi").fetchall()
    finally:
        conn.close()

    return {url_canonico(r["url"]) for r in righe}


def scopri() -> list[Voce]:
    """Confronta l'elenco del portale con l'archivio e segnala i nuovi."""
    noti = gia_in_archivio()
    anno_corrente = date.today().year

    return [
        Voce(
            slug=s,
            url=url_da_slug(s),
            codice_fonte=CODICE_FONTE,
            titolo=_titolo_da_slug(s),
            nuovo=url_da_slug(s) not in noti,
            promettente=promettente(s),
            anno=anno_slug(s),
            recente=recente(s, anno_corrente),
            posizione=i,
        )
        for i, s in enumerate(leggi_elenco(), start=1)
    ]
