"""Tipi di beneficiari dei bandi: la lista chiusa.

Ogni soggetto ammesso da un bando si riconduce a uno o piu' di questi
tipi. La lista e' l'unica definizione: lo schema del database ne ricava
il vincolo sui valori ammessi, l'estrattore la riceve nel prompt.
"""

import re

# Codice del tipo -> descrizione, raggruppati per macrogruppo
TIPI_BENEFICIARIO = {
    # enti pubblici
    "comune": "Comuni, amministrazioni comunali",
    "unione_comuni": "Unioni di comuni, gestioni associate tra comuni",
    "altro_ente_pubblico": (
        "altri enti pubblici: province, citta' metropolitane, Regione, "
        "aziende sanitarie, enti parco, consorzi pubblici"
    ),
    # imprese
    "impresa_agricola": "imprese agricole e forestali, imprenditori agricoli",
    "impresa_turistica": "imprese turistiche e ricettive, agriturismi",
    "impresa_artigiana_commerciale": "imprese artigiane e commerciali",
    "altra_impresa": "altre imprese",
    # professionisti e lavoratori autonomi
    "professionista_autonomo": (
        "liberi professionisti, lavoratori autonomi, titolari di impresa individuale"
    ),
    # terzo settore e associazioni
    "terzo_settore": (
        "enti del terzo settore, associazioni, fondazioni, cooperative "
        "sociali, associazioni sportive dilettantistiche"
    ),
    # cittadini e famiglie
    "cittadini_famiglie": (
        "persone fisiche, famiglie, studenti, lavoratori dipendenti"
    ),
    # ricerca e formazione
    "ricerca_formazione": (
        "universita', enti di ricerca, scuole, agenzie formative accreditate"
    ),
    # chiunque soddisfi un requisito, senza un tipo indicato dal bando
    "qualsiasi_soggetto": (
        "chiunque soddisfi un requisito, senza un tipo di soggetto indicato "
        "(es. i titolari di un museo accreditato); le condizioni sono obbligatorie"
    ),
}

# Il tipo che richiede sempre le condizioni
PER_REQUISITO = "qualsiasi_soggetto"

# Da dove viene una riga di beneficiari_bando
ORIGINI = ("estrazione", "ammette_comuni")

# I tipi privati e tutti i tipi con un soggetto indicato, per le regole.
# I tipi privati non comprendono cittadini_famiglie: "privati", "datori di
# lavoro", "soggetti ospitanti privati" sono imprese, professionisti ed
# enti; le persone fisiche entrano solo se il bando le nomina (regola
# "persone fisiche"). "Pubblici e/o privati" invece comprende tutti i tipi
# (verifica a mano del 12 novembre 2026).
TIPI_IMPRESA = (
    "impresa_agricola",
    "impresa_turistica",
    "impresa_artigiana_commerciale",
    "altra_impresa",
)
TIPI_PRIVATI = (*TIPI_IMPRESA, "professionista_autonomo", "terzo_settore")
TIPI_PUBBLICI = ("comune", "unione_comuni", "altro_ente_pubblico")
TUTTI_CON_SOGGETTO = tuple(t for t in TIPI_BENEFICIARIO if t != PER_REQUISITO)

# Regole di corrispondenza: un'espressione del bando -> i tipi che comprende.
# Si applicano nel codice, dopo il modello: se il soggetto o la frase
# contengono l'espressione, i tipi mancanti vengono aggiunti con un avviso.
# Solo espressioni ombrello senza ambiguita': "imprese" o "comuni" da soli
# non ci sono, perche' compaiono anche dentro "imprese agricole" o
# "unioni di comuni".
# Le chiavi sono le espressioni leggibili, mostrate nel prompt; il confronto
# usa i confini di parola, e per le espressioni in FORME un'espressione
# regolare che copre anche le altre forme della pagina.
TERMINI = {
    # art. 2 del TUEL: comuni, province, citta' metropolitane, unioni...
    "enti locali": ("comune", "unione_comuni", "altro_ente_pubblico"),
    "enti pubblici": ("comune", "unione_comuni", "altro_ente_pubblico"),
    "pubbliche amministrazioni": ("comune", "unione_comuni", "altro_ente_pubblico"),
    "amministrazioni pubbliche": ("comune", "unione_comuni", "altro_ente_pubblico"),
    "comuni in forma associata": ("comune", "unione_comuni"),
    "gestioni associate": ("comune", "unione_comuni"),
    "unioni di comuni": ("unione_comuni",),
    "unioni dei comuni": ("unione_comuni",),
    "aziende sanitarie": ("altro_ente_pubblico",),
    "enti del ssr": ("altro_ente_pubblico",),
    "enti del terzo settore": ("terzo_settore",),
    # enti religiosi ed ecclesiastici: terzo settore, con la condizione
    # ENTE_RELIGIOSO quando il soggetto e' solo l'ente religioso (in
    # bandi._valida_beneficiari), mai qualsiasi_soggetto
    "enti religiosi": ("terzo_settore",),
    "enti ecclesiastici": ("terzo_settore",),
    "persone fisiche": ("cittadini_famiglie",),
    "organismi di ricerca": ("ricerca_formazione",),
    "istituzioni scolastiche": ("ricerca_formazione",),
    "agenzie formative": ("ricerca_formazione",),
    "organismi formativi": ("ricerca_formazione",),
    "enti di formazione": ("ricerca_formazione",),
    "enti formativi": ("ricerca_formazione",),
    "liberi professionisti": ("professionista_autonomo",),
    "lavoratori autonomi": ("professionista_autonomo",),
    "titolari di impresa individuale": ("professionista_autonomo",),
    # forme associative di imprese o professionisti: vanno ai tipi di chi le
    # compone. "Consorzi" o "forme associative" da soli no: ci sono anche i
    # consorzi di bonifica e le forme associative tra Comuni.
    "reti, consorzi, associazioni di imprese": TIPI_IMPRESA,
    "reti, associazioni di professionisti": ("professionista_autonomo",),
}

# Soggetti generici: non sono un requisito, nominano dei tipi. Si applicano
# solo per sostituire qualsiasi_soggetto, mai per aggiungere tipi a un
# soggetto gia' classificato: il bando li usa spesso con una qualificazione
# che restringe ("privati senza scopo di lucro", "datori di lavoro privati
# ad esclusione delle persone fisiche"), e le regole non la leggono.
GENERICI = {
    "privati": TIPI_PRIVATI,
    "soggetti privati": TIPI_PRIVATI,
    "datori di lavoro": TIPI_PRIVATI,
    "soggetti pubblici": TIPI_PUBBLICI,
    "pubblici o privati": TUTTI_CON_SOGGETTO,
    "pubblici e/o privati": TUTTI_CON_SOGGETTO,
    "pubblici e privati": TUTTI_CON_SOGGETTO,
    "pubblico o privato": TUTTI_CON_SOGGETTO,
}

# Le forme femminili, singolari e con la barra delle espressioni di TERMINI
# che le pagine usano: "libere/i professioniste/i",
# "lavoratrici/lavoratori autonome/i", "titolari d'impresa individuale"
_VOCALE = r"[aeio](?:/[aeio])?"
_LAVORATORE = r"lavorat(?:ori|rici|ore|rice)"
_AGGREGATI = (
    r"(?:reti|rete|consorzi|consorzio|associazioni|aggregazioni|raggruppamenti"
    r"|forme associative)(?: temporane[ei])?"
)
FORME = {
    "liberi professionisti": rf"liber{_VOCALE} professionist{_VOCALE}",
    "lavoratori autonomi": (
        rf"{_LAVORATORE}(?:\s*(?:/|e|o|e/o)\s*{_LAVORATORE})? autonom{_VOCALE}"
    ),
    "titolari di impresa individuale": (
        r"titolar[ei](?:/[ei])? (?:di |d'|dell')impres[ae] individual[ei]"
    ),
    # "reti di imprese", "consorzi tra imprese", "associazioni temporanee di
    # imprese", "forme associative di imprese e professionisti"... ma non
    # "di imprese agricole": con un settore vale solo quello, e lo decide
    # il modello
    "reti, consorzi, associazioni di imprese": (
        rf"{_AGGREGATI} (?:di|tra|fra) (?:professionisti (?:e|o) )?imprese"
        r"(?! (?:agricol|turistic|ricettiv|artigian|commercial|forestal|agro))"
    ),
    "reti, associazioni di professionisti": (
        rf"{_AGGREGATI} (?:di|tra|fra) (?:imprese ?(?:e|o|/) ?)?professionisti"
    ),
    # "ente religioso", "enti religiosi civilmente riconosciuti"
    "enti religiosi": r"ent[ei] religios[oi]",
    "enti ecclesiastici": r"ent[ei] ecclesiastic[oi]",
}

# La condizione delle righe di un soggetto che e' solo un ente religioso o
# ecclesiastico: terzo_settore da solo comprenderebbe tutte le
# associazioni e cooperative
ENTE_RELIGIOSO = "ente religioso"
_RELIGIOSO = r"(?:religios[oi]|ecclesiastic[oi])"
_SOLO_RELIGIOSO = re.compile(
    rf"^(?:gli |agli |degli )?ent[ei] {_RELIGIOSO}"
    rf"(?:(?: ed| e| o|,) {_RELIGIOSO})*"
    r"(?: civilmente riconosciut[oi])?[ .;,:]*$"
)


def _schema(espressione: str) -> re.Pattern:
    """L'espressione regolare di una regola, con i confini di parola."""
    corpo = FORME.get(espressione, re.escape(espressione))
    return re.compile(rf"\b(?:{corpo})\b")


_SCHEMI = {espressione: _schema(espressione) for espressione in TERMINI | GENERICI}


def normalizza(testo: str) -> str:
    """Testo ridotto per i confronti: minuscolo, apostrofi e spazi uniformi."""
    testo = (testo or "").lower()
    for curvo, dritto in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"')):
        testo = testo.replace(curvo, dritto)
    testo = testo.replace(" ", " ")
    return re.sub(r"\s+", " ", testo).strip()


def frase_nel_testo(frase: str, testo: str) -> bool:
    """La frase compare nel testo della pagina, a meno di spazi e maiuscole.

    La punteggiatura finale della frase non conta: il modello la omette
    spesso anche quando copia la frase esattamente.
    """
    cercata = normalizza(frase).rstrip(".;:,")
    return bool(cercata) and cercata in normalizza(testo)


def tipi_da_termini(testo: str, regole: dict = TERMINI) -> set[str]:
    """I tipi che le regole di corrispondenza ricavano da un testo.

    regole: TERMINI (le regole specifiche) o GENERICI (i soggetti generici).
    """
    trovati = set()
    ridotto = normalizza(testo)
    for espressione, tipi in regole.items():
        if _SCHEMI[espressione].search(ridotto):
            trovati.update(tipi)
    return trovati


def solo_ente_religioso(soggetto: str | None) -> bool:
    """Il soggetto e' soltanto un ente religioso o ecclesiastico.

    "Enti religiosi", "Enti religiosi ed ecclesiastici civilmente
    riconosciuti" si'; "Fondazioni ed enti religiosi" no: li' l'ente
    religioso e' uno dei soggetti, e la condizione non vale per gli altri.
    """
    return bool(_SOLO_RELIGIOSO.match(normalizza(soggetto)))


def soggetto_generico(soggetto: str | None) -> bool:
    """Il soggetto corrisponde a una regola dei soggetti generici.

    Si calcola al momento, non si memorizza: serve a mostrare il soggetto
    come lo scrive il bando, perche' la sua qualificazione ("che operano
    nel campo della ricerca") non sta nel tipo.
    """
    return bool(soggetto) and bool(tipi_da_termini(soggetto, GENERICI))
