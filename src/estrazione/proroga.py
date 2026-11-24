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

prima_frase e frasi_con valgono per qualunque schema di parole: le usa
anche src/estrazione/sospensione.py.
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


def prima_frase(html: str, schema: re.Pattern) -> str | None:
    """La prima frase, titolo o nome di file in cui compare schema.

    schema si cerca sul testo normalizzato (normalizza). Prima le frasi
    intere del testo della pagina (che comprende i titoli dei
    collegamenti), poi i nomi dei file collegati (candidate). Restituisce
    il testo com'e' scritto, tagliato a LUNGHEZZA_MASSIMA battute; None se
    schema non compare.
    """
    for frase in candidate(html):
        if schema.search(normalizza(frase)):
            return frase[:LUNGHEZZA_MASSIMA]
    return None


def candidate(html: str) -> list[str]:
    """Le frasi intere del testo della pagina (frasi_intere), riga per
    riga, poi i nomi dei file collegati: dove si cercano le parole."""
    frasi = [f for riga in a_testo(html).splitlines() for f in frasi_intere(riga)]
    return frasi + _nomi_file(html)


# Le abbreviazioni dopo le quali un punto non chiude la frase ("decreto
# n. 742/2026", "art. 5"), gia' in minuscolo; e ogni lettera sola ("L.
# 68/1999", "D. Lgs.")
ABBREVIAZIONI = frozenset(
    "n nn art artt lett pag pagg ecc sig dott prof lgs dlgs reg cfr es "
    "all rif tel num cap".split()
)
PAROLA_PRIMA = re.compile(r"(\w+)$")


def frasi_intere(riga: str) -> list[str]:
    """Le frasi di una riga, intere: si divide come FINE_FRASE, ma non
    dopo il punto di un'abbreviazione (ABBREVIAZIONI) o di una lettera
    sola."""
    frasi, inizio = [], 0
    for fine in FINE_FRASE.finditer(riga):
        prima = riga[inizio : fine.start()]
        parola = PAROLA_PRIMA.search(prima[:-1]) if prima.endswith(".") else None
        if parola and (
            len(parola.group(1)) == 1 or parola.group(1).lower() in ABBREVIAZIONI
        ):
            continue
        frasi.append(prima.strip())
        inizio = fine.end()
    frasi.append(riga[inizio:].strip())
    return [f for f in frasi if f]


def frasi_con(html: str, schema: re.Pattern) -> list[str]:
    """Tutte le frasi intere, poi i nomi dei file collegati (candidate),
    in cui compare schema, senza tagli e senza ripetizioni."""
    trovate: list[str] = []
    for frase in candidate(html):
        if schema.search(normalizza(frase)) and frase not in trovate:
            trovate.append(frase)
    return trovate


def frase_di_proroga(html: str) -> str | None:
    """La prima frase, titolo o nome di file con una parola di PAROLE,
    tagliata a LUNGHEZZA_MASSIMA battute (prima_frase)."""
    return prima_frase(html, SCHEMA)


def nota_di_proroga(html: str) -> str | None:
    """La nota del rapporto, "possibile proroga: <frase>", o None."""
    frase = frase_di_proroga(html)
    return PREFISSO + frase if frase else None
