"""Indizio di una proroga in una pagina di bando, senza modello.

Si cercano parole chiave (PAROLE) nel testo della pagina e nei nomi dei
file collegati, senza distinguere maiuscole e accenti, come parole
intere: "improrogabile" o "prorogabile" non contano, perche' dicono il
contrario o niente. Il risultato e' solo un indizio con la frase in cui
compare: nessuna data. La data prorogata si legge nel secondo tempo
della scansione, dall'atto, con la sua frase di prova.

Casi visti sulle pagine salvate il 19/11/2026: la frase "Proroga fino
alle ore 13 del 30 novembre 2026" (risorse genetiche forestali), il
titolo dell'allegato "...-Proroga-del-termine-ultimo-di-presentazione-
delle-istanze.pdf" (Cultura e Sport Missione Comune).
"""

import re
import unicodedata
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

from src.estrazione.pagina import a_testo

# Le parole e le espressioni, gia' senza accenti e in minuscolo
PAROLE = (
    "proroga",
    "prorogato",
    "prorogata",
    "prorogati",
    "differimento",
    "differito",
    "riapertura dei termini",
    "riaperti i termini",
)

# Parole intere: niente lettere o cifre subito prima o subito dopo
SCHEMA = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(p) for p in PAROLE) + r")(?!\w)")

# Le frasi di una riga: si divide dopo il punto, il punto e virgola, il
# punto esclamativo o interrogativo seguiti da uno spazio
FINE_FRASE = re.compile(r"(?<=[.;!?])\s+")

LUNGHEZZA_MASSIMA = 200

PREFISSO = "possibile proroga: "


def normalizza(testo: str) -> str:
    """Minuscolo, senza accenti; trattini bassi e trattini come spazi,
    cosi' i nomi dei file si leggono come frasi."""
    senza_accenti = "".join(
        c
        for c in unicodedata.normalize("NFKD", testo.lower())
        if not unicodedata.combining(c)
    )
    return re.sub(r"[_\-]+", " ", senza_accenti)


class _Indirizzi(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.href: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        if tag == "a":
            self.href.extend(v for k, v in attrs if k == "href" and v)


def _nomi_file(html: str) -> list[str]:
    """L'ultima parte del percorso di ogni collegamento, decodificata."""
    lettore = _Indirizzi()
    lettore.feed(html)
    nomi = []
    for href in lettore.href:
        nome = unquote(urlsplit(href).path.rstrip("/").rsplit("/", 1)[-1])
        if nome and nome not in nomi:
            nomi.append(nome)
    return nomi


def frase_di_proroga(html: str) -> str | None:
    """La prima frase, titolo o nome di file con una parola di PAROLE.

    Prima il testo della pagina (che comprende i titoli dei collegamenti),
    poi i nomi dei file collegati. Restituisce il testo com'e' scritto,
    tagliato a LUNGHEZZA_MASSIMA battute; None se nessuna parola compare.
    """
    for riga in a_testo(html).splitlines():
        for frase in FINE_FRASE.split(riga):
            if SCHEMA.search(normalizza(frase)):
                return frase.strip()[:LUNGHEZZA_MASSIMA]
    for nome in _nomi_file(html):
        if SCHEMA.search(normalizza(nome)):
            return nome[:LUNGHEZZA_MASSIMA]
    return None


def nota_di_proroga(html: str) -> str | None:
    """La nota del rapporto, "possibile proroga: <frase>", o None."""
    frase = frase_di_proroga(html)
    return PREFISSO + frase if frase else None
