"""Tipi di beneficiari dei bandi: la lista chiusa.

Ogni soggetto ammesso da un bando si riconduce a uno o piu' di questi
tipi. La lista e' l'unica definizione: lo schema del database ne ricava
il vincolo sui valori ammessi, l'estrattore la riceve nel prompt.
"""

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
