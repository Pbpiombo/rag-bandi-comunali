"""Valori confrontabili: numeri, date, orari e riferimenti in una sola forma.

Uno stesso valore si scrive in molti modi: "322,00", "€ 322" e "322";
"31/07/2027", "31 luglio 2027" e "2027-07-31"; "19,5 milioni" e
"19.500.000". Qui ogni scrittura diventa un valore, e due valori si
confrontano per intero: 8 non e' "contenuto" in 80, e il 3 novembre non e'
contenuto nel 13 novembre.

Funzioni pure, senza database ne' modello. Le usa il verificatore delle
risposte; in seguito le usera' anche l'estrattore, per controllare che il
valore estratto compaia nella sua prova.
"""

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

MESI = (
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
)
_MESI = "|".join(MESI)

# Gli stessi moltiplicatori dell'estrattore (src/estrazione/bandi.py)
MOLTIPLICATORI = {
    "mila": Decimal(10) ** 3,
    "milione": Decimal(10) ** 6,
    "milioni": Decimal(10) ** 6,
    "mln": Decimal(10) ** 6,
    "miliardo": Decimal(10) ** 9,
    "miliardi": Decimal(10) ** 9,
}
_MOLTIPLICATORE = r"mila|milion[ei]|mln|miliard[oi]"

# Un numero all'italiana. La regola del punto e' quella dell'estrattore:
# seguito da tre cifre separa le migliaia (12.500 = 12500), seguito da una
# o due cifre finali e' decimale (9.2, 343423.56). La virgola e' sempre
# decimale. L'ordine delle alternative conta: le migliaia prima.
_CIFRE = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+\.\d{1,2}(?![\d.])|\d+(?:,\d+)?"
_DECIMALE_COL_PUNTO = re.compile(r"\d+\.\d{1,2}")

# Dentro un testo un numero non comincia ne' finisce a meta' di un altro:
# niente cifre, o cifra e separatore, prima; niente cifre, o separatore e
# cifra, dopo. Cosi' in "80%" non si legge un 8, e "1.2345" non e' un numero.
_PRIMA = r"(?<!\d)(?<!\d[.,])"
_DOPO = r"(?!\d|[.,]\d)"

_NUMERO_INTERO = re.compile(
    rf"(?P<cifre>{_CIFRE})(?:\s*(?P<molt>{_MOLTIPLICATORE}))?", re.IGNORECASE
)
_NUMERO = re.compile(
    rf"{_PRIMA}(?P<cifre>{_CIFRE}){_DOPO}(?:\s*(?P<molt>{_MOLTIPLICATORE})\b)?",
    re.IGNORECASE,
)
_PERCENTUALE = re.compile(
    rf"{_PRIMA}(?P<cifre>{_CIFRE}){_DOPO}\s*"
    r"(?:%|per\s*cento\b|punti\s+percentuali\b)",
    re.IGNORECASE,
)

_DATA_ISO = re.compile(r"(?<!\d)(?P<a>\d{4})-(?P<m>\d{2})-(?P<g>\d{2})(?!\d)")
_DATA_NUMERICA = re.compile(
    r"(?<![\d/.-])(?P<g>\d{1,2})(?P<sep>[/.-])(?P<m>\d{1,2})(?P=sep)(?P<a>\d{4})(?!\d)"
)
_DATA_LETTERE = re.compile(
    rf"(?<!\d)(?P<g>\d{{1,2}})\s*[°º]?\s+(?P<mese>{_MESI})\s+(?P<a>\d{{4}})(?!\d)",
    re.IGNORECASE,
)
_GIORNO_MESE_LETTERE = re.compile(
    rf"(?<!\d)(?P<g>\d{{1,2}})\s*[°º]?\s+(?P<mese>{_MESI})\b", re.IGNORECASE
)
_GIORNO_MESE_NUMERICO = re.compile(r"(?<![\d/.])(?P<g>\d{1,2})/(?P<m>\d{1,2})(?![/\d])")

_PERIODO = re.compile(
    r"(?<!\d)(?P<da>(?:19|20)\d{2})\s*(?P<sep>[-–/])\s*(?P<a>(?:19|20)\d{2})(?!\d)"
)
_ORARIO_ORE = re.compile(
    r"\bore\s+(?P<h>\d{1,2})(?:[.:](?P<min>\d{2}))?(?!\d)", re.IGNORECASE
)
_ORARIO = re.compile(r"(?<![\d.:])(?P<h>\d{1,2}):(?P<min>\d{2})(?![\d:])")

_RIFERIMENTO = re.compile(r"(?<![\d/])(?P<n>\d{1,6})/(?P<a>\d{4})(?![\d/])")
_RIFERIMENTO_INTERO = re.compile(r"(?:n\.?\s*)?(?P<n>\d{1,6})/(?P<a>\d{4})", re.I)

# Un atto con numero e data: "decreto n. 1234 del 12/03/2026", "DGR 1081
# del 7 settembre 2026", "prot. 26286 del 3 novembre 2026". Le pagine
# scrivono lo stesso atto anche come "1234/2026": il numero con l'anno
# della data vale come riferimento.
_DATA_QUALSIASI = (
    r"\d{4}-\d{2}-\d{2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{4}"
    rf"|\d{{1,2}}\s*[°º]?\s+(?:{_MESI})\s+\d{{4}}"
)
_ATTO_CON_DATA = re.compile(
    r"(?:\bn\s*[.°º]?|\bnumero|"
    r"(?:\b(?:decreto|delibera|deliberazione|dgrt?|dd|protocollo)\b"
    r"|d\.g\.r\.(?:t\.)?|d\.d\.|\bprot\.)"
    r"[^\d()\[\]]{0,40}?)"
    rf"\s*(?P<n>\d{{1,6}})\s+del(?:l['’])?\s*(?P<data>{_DATA_QUALSIASI})(?!\d)",
    re.IGNORECASE,
)

# Articoli, paragrafi, punti e lettere: "art. 54", "articolo 54, comma 2",
# "par. 3", "punto 3", "lett. 3". Un numero d'articolo non e' un importo:
# "art. 54" si conferma solo con un articolo 54, mai con "54 euro".
_ARTICOLO = re.compile(
    r"\b(?P<genere>art(?:icolo)?|par(?:agrafo)?|punto|lett(?:era)?)\.?\s*"
    r"(?P<n>\d+)(?:\s*,?\s*comma\s*(?P<comma>\d+))?(?!\d)",
    re.IGNORECASE,
)
_GENERI_ARTICOLO = {
    "art": "art",
    "articolo": "art",
    "par": "par",
    "paragrafo": "par",
    "punto": "punto",
    "lett": "lett",
    "lettera": "lett",
}
# Codici di classificazione con i punti, come quelli ATECO: a tre livelli
# ("49.34.00"), o con la lettera maiuscola della sezione ("I 55.1"). Sono
# un valore solo: le loro cifre non sono numeri. Due livelli senza lettera
# ("55.1") restano un numero, perche' non si distinguono da un decimale.
_CODICE_TRE_LIVELLI = r"\d{2}\.\d{2}\.\d{1,2}"
_CODICE_SEZIONE = r"[A-U]\s?\d{2}(?:\.\d{1,2}){1,2}"
_CODICI_PUNTATI = (
    re.compile(rf"(?<![\w.])(?:{_CODICE_SEZIONE}|{_CODICE_TRE_LIVELLI})(?!\d|\.\d)"),
)
_CODICI = (
    re.compile(r"\b[A-Z]\d{2}[A-Z]\d{10,12}\b", re.IGNORECASE),  # CUP
    re.compile(r"\b\d{8}-\d\b"),
    *_CODICI_PUNTATI,
)

# Trattini tipografici che valgono "-": U+2010 trattino, U+2011 trattino
# non separabile, U+2012 trattino delle cifre, U+2013 trattino medio, U+2212
# meno. "2026‑11‑13" con U+2011 e' la data 2026-11-13. La lineetta U+2014
# resta: e' punteggiatura, non un separatore di cifre.
_TRATTINI = str.maketrans(dict.fromkeys("‐‑‒–−", "-"))

_ANNO = re.compile(r"(?:19|20)\d{2}")


def uniforma_trattini(testo: str) -> str:
    """I trattini tipografici diventano "-"; la lunghezza del testo non cambia."""
    return testo.translate(_TRATTINI)


def codice(testo: str) -> str:
    """Un codice in una sola forma: senza spazi, in maiuscolo ("i 55.1" -> "I55.1")."""
    return re.sub(r"\s", "", testo).upper()


def _decimale(cifre: str) -> Decimal:
    """Le cifre di un numero all'italiana, gia' riconosciute, come Decimal."""
    if _DECIMALE_COL_PUNTO.fullmatch(cifre):
        return Decimal(cifre)
    return Decimal(cifre.replace(".", "").replace(",", "."))


def _con_moltiplicatore(cifre: str, moltiplicatore: str | None) -> Decimal:
    valore = _decimale(cifre)
    if moltiplicatore:
        valore *= MOLTIPLICATORI[moltiplicatore.lower()]
    return valore


def numero(testo: str) -> Decimal | None:
    """Un numero scritto all'italiana, o None se il testo non e' un numero.

    Il simbolo e la parola "euro" non contano, e nemmeno "di" prima di
    "euro": "€ 322,00", "322 euro" e "19,5 milioni di euro" sono numeri. Gli
    zeri decimali non contano: numero("322,00") == numero("322").
    """
    pulito = re.sub(r"€|\beuro\b", " ", testo.lower().replace(" ", " "))
    pulito = re.sub(r"\s+di$", "", pulito.strip()).strip()
    trovato = _NUMERO_INTERO.fullmatch(pulito)
    if not trovato:
        return None
    return _con_moltiplicatore(trovato["cifre"], trovato["molt"])


def _iso(anno: int, mese: int, giorno: int) -> str | None:
    try:
        return date(anno, mese, giorno).isoformat()
    except ValueError:
        return None


def _mese(nome: str) -> int:
    return MESI.index(nome.lower()) + 1


def _data_da(trovato: re.Match) -> str | None:
    """La data in ISO da una corrispondenza di uno dei tre schemi."""
    mese = _mese(trovato["mese"]) if "mese" in trovato.re.groupindex else None
    return _iso(
        int(trovato["a"]),
        mese or int(trovato["m"]),
        int(trovato["g"]),
    )


def data(testo: str) -> str | None:
    """Una data in ISO (AAAA-MM-GG), o None se il testo non e' una data.

    Forme: 2027-07-31; 31/07/2027, 31-07-2027, 31.07.2027, anche con giorno
    e mese di una cifra; 31 luglio 2027, anche 1° o 1º. Il giorno deve
    esistere: 31/02/2026 non e' una data.
    """
    pulito = testo.strip()
    for schema in (_DATA_ISO, _DATA_NUMERICA, _DATA_LETTERE):
        trovato = schema.fullmatch(pulito)
        if trovato:
            return _data_da(trovato)
    return None


def _mm_gg(mese: int, giorno: int) -> str | None:
    # Il 2000 e' bisestile: il 29 febbraio esiste
    iso = _iso(2000, mese, giorno)
    return iso[5:] if iso else None


def giorno_mese(testo: str) -> str | None:
    """Una data senza anno nella forma MM-GG: "15 ottobre", "30/06"."""
    pulito = testo.strip()
    trovato = _GIORNO_MESE_LETTERE.fullmatch(pulito)
    if trovato:
        return _mm_gg(_mese(trovato["mese"]), int(trovato["g"]))
    trovato = _GIORNO_MESE_NUMERICO.fullmatch(pulito)
    if trovato:
        return _mm_gg(int(trovato["m"]), int(trovato["g"]))
    return None


def _hh_mm(ore: str, minuti: str | None) -> str | None:
    h, m = int(ore), int(minuti or 0)
    if h > 24 or m > 59 or (h == 24 and m):
        return None
    return f"{h:02d}:{m:02d}"


def orario(testo: str) -> str | None:
    """Un orario nella forma HH:MM: "12:00", "ore 12", "ore 9.30"."""
    pulito = testo.strip()
    for schema in (_ORARIO_ORE, _ORARIO):
        trovato = schema.fullmatch(pulito)
        if trovato:
            return _hh_mm(trovato["h"], trovato["min"])
    return None


def _articolo_da(trovato: re.Match) -> tuple[str, str | None]:
    """L'articolo senza comma e, se c'e', con il comma: "art 54", "art 54 comma 2"."""
    base = f"{_GENERI_ARTICOLO[trovato['genere'].lower()]} {int(trovato['n'])}"
    con_comma = f"{base} comma {int(trovato['comma'])}" if trovato["comma"] else None
    return base, con_comma


def articolo(testo: str) -> str | None:
    """Un articolo, paragrafo, punto o lettera: "art. 54, comma 2" -> "art 54 comma 2"."""
    trovato = _ARTICOLO.fullmatch(testo.strip())
    if not trovato:
        return None
    base, con_comma = _articolo_da(trovato)
    return con_comma or base


def riferimento(testo: str) -> str | None:
    """Un riferimento nella forma n/aaaa: "n. 041/2022" -> "41/2022"."""
    trovato = _RIFERIMENTO_INTERO.fullmatch(testo.strip())
    return f"{int(trovato['n'])}/{trovato['a']}" if trovato else None


def periodo(testo: str) -> str | None:
    """Un periodo tra due anni: "2021 – 2027" o "2026/2027" -> "2021-2027"."""
    trovato = _PERIODO.fullmatch(testo.strip())
    return f"{trovato['da']}-{trovato['a']}" if trovato else None


def date_degli_atti(testo: str) -> list[tuple[str, str, str | None]]:
    """Gli atti scritti con numero e data, come terne (numero, data, ISO).

    "decreto n. 9550 del 28/04/2026" -> ("9550", "28/04/2026",
    "2026-04-28"). La data e' come appare nel testo; l'ISO e' None se la
    data non esiste (31/02/2026).
    """
    return [
        (str(int(m["n"])), m["data"], data(m["data"]))
        for m in _ATTO_CON_DATA.finditer(testo.replace(" ", " "))
    ]


def atti_con_data(testo: str) -> set[tuple[str, str]]:
    """Gli atti scritti con numero e data, come coppie (numero, data ISO).

    "decreto dirigenziale n. 9550 del 28/04/2026" -> ("9550", "2026-04-28").
    Numero e data sono una coppia: lo stesso numero con un'altra data e' un
    altro riferimento.
    """
    return {(n, iso) for n, _, iso in date_degli_atti(testo) if iso}


@dataclass
class Valori:
    """I valori di un testo, divisi per famiglia.

    anni: anche quelli delle date e dei periodi. giorni_mese: anche quelli
    delle date complete, per confrontare "15 ottobre" con "15/10/2026".
    numeri: anche gli anni scritti da soli ("nel 2026"), non le cifre di
    date, orari, periodi, riferimenti e articoli. percentuali a parte.
    articoli: "art 54", e per "art. 54, comma 2" anche "art 54 comma 2".
    riferimenti: le forme n/aaaa, e per ogni atto con numero e data
    ("decreto n. 1234 del 12/03/2026") anche "1234/2026".
    """

    date: set[str] = field(default_factory=set)
    giorni_mese: set[str] = field(default_factory=set)
    anni: set[int] = field(default_factory=set)
    periodi: set[str] = field(default_factory=set)
    orari: set[str] = field(default_factory=set)
    riferimenti: set[str] = field(default_factory=set)
    codici: set[str] = field(default_factory=set)
    articoli: set[str] = field(default_factory=set)
    percentuali: set[Decimal] = field(default_factory=set)
    numeri: set[Decimal] = field(default_factory=set)


def valori(testo: str) -> Valori:
    """Tutti i valori di un testo.

    Si leggono in quest'ordine: date, date senza anno, periodi, orari,
    riferimenti, codici, articoli, percentuali, numeri. Una porzione gia' letta non si
    rilegge: le cifre di "28/04/2026" sono una data, non i numeri 28, 4 e
    2026.
    """
    testo = uniforma_trattini(testo.replace(" ", " "))
    trovati = Valori()
    occupati: list[tuple[int, int]] = []

    def libere(schema: re.Pattern):
        """Le corrispondenze che non si sovrappongono a quelle gia' lette."""
        for m in schema.finditer(testo):
            if any(m.start() < f and i < m.end() for i, f in occupati):
                continue
            occupati.append((m.start(), m.end()))
            yield m

    for schema in (_DATA_ISO, _DATA_NUMERICA, _DATA_LETTERE):
        for m in libere(schema):
            iso = _data_da(m)
            if iso:
                trovati.date.add(iso)
                trovati.giorni_mese.add(iso[5:])
                trovati.anni.add(int(iso[:4]))

    for m in libere(_GIORNO_MESE_LETTERE):
        mm_gg = _mm_gg(_mese(m["mese"]), int(m["g"]))
        if mm_gg:
            trovati.giorni_mese.add(mm_gg)
    for m in libere(_GIORNO_MESE_NUMERICO):
        mm_gg = _mm_gg(int(m["m"]), int(m["g"]))
        if mm_gg:
            trovati.giorni_mese.add(mm_gg)

    for m in libere(_PERIODO):
        trovati.periodi.add(f"{m['da']}-{m['a']}")
        trovati.anni.update((int(m["da"]), int(m["a"])))
        # "2026/2027" e' anche un riferimento nella forma n/aaaa
        if m["sep"] == "/":
            trovati.riferimenti.add(f"{m['da']}/{m['a']}")

    for schema in (_ORARIO_ORE, _ORARIO):
        for m in libere(schema):
            hh_mm = _hh_mm(m["h"], m["min"])
            if hh_mm:
                trovati.orari.add(hh_mm)

    for m in libere(_RIFERIMENTO):
        trovati.riferimenti.add(f"{int(m['n'])}/{m['a']}")

    # Non occupa il testo: il numero e la data restano un numero e una data
    for numero_atto, iso in atti_con_data(testo):
        trovati.riferimenti.add(f"{numero_atto}/{iso[:4]}")

    for schema in _CODICI:
        for m in libere(schema):
            trovati.codici.add(codice(m.group(0)))
            # "I 55.10.00" vale anche senza la lettera della sezione
            if re.match(r"[A-Z]", m.group(0)) and re.search(
                _CODICE_TRE_LIVELLI, m.group(0)
            ):
                trovati.codici.add(re.search(_CODICE_TRE_LIVELLI, m.group(0)).group(0))

    for m in libere(_ARTICOLO):
        base, con_comma = _articolo_da(m)
        trovati.articoli.add(base)
        if con_comma:
            trovati.articoli.add(con_comma)

    for m in libere(_PERCENTUALE):
        trovati.percentuali.add(_decimale(m["cifre"]))

    for m in libere(_NUMERO):
        trovati.numeri.add(_con_moltiplicatore(m["cifre"], m["molt"]))
        if not m["molt"] and _ANNO.fullmatch(m["cifre"]):
            trovati.anni.add(int(m["cifre"]))

    return trovati
