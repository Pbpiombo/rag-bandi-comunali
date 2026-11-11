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
    # terzo settore e associazioni
    "terzo_settore": (
        "enti del terzo settore, associazioni, fondazioni, cooperative "
        "sociali, associazioni sportive dilettantistiche"
    ),
    # cittadini e famiglie
    "cittadini_famiglie": "persone fisiche, famiglie, studenti, lavoratori",
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

# Regole di corrispondenza: un'espressione del bando -> i tipi che comprende.
# Si applicano nel codice, dopo il modello: se il soggetto o la frase
# contengono l'espressione, i tipi mancanti vengono aggiunti con un avviso.
# Solo espressioni ombrello senza ambiguita': "imprese" o "comuni" da soli
# non ci sono, perche' compaiono anche dentro "imprese agricole" o
# "unioni di comuni".
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
    "persone fisiche": ("cittadini_famiglie",),
    "organismi di ricerca": ("ricerca_formazione",),
    "istituzioni scolastiche": ("ricerca_formazione",),
    "agenzie formative": ("ricerca_formazione",),
}


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


def tipi_da_termini(testo: str) -> set[str]:
    """I tipi che le regole di corrispondenza ricavano da un testo."""
    trovati = set()
    ridotto = normalizza(testo)
    for espressione, tipi in TERMINI.items():
        if espressione in ridotto:
            trovati.update(tipi)
    return trovati
