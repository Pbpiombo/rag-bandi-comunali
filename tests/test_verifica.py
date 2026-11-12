"""Collaudo del verificatore con risposte deliberatamente falsificate.

Non chiama il modello: costruisce risposte finte e controlla che
il verificatore reagisca come previsto. Gratuito e istantaneo.
"""

from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from src.database.modelli import Risultato, VoceBando
from src.verification.controllo import (
    Esito,
    giudizio,
    riassumi,
    trova_dati,
    verifica,
)

FRAMMENTI = [
    Document(
        page_content=(
            "I compensi di cui alle precedenti lettere b e c sono ammissibili "
            "a finanziamento secondo un parametro di costo giornata/uomo pari "
            "al massimo a € 322,00, oltre oneri previdenziali e fiscali."
        ),
        metadata={"ente": "Regione Toscana", "pagina": 11},
    ),
    Document(
        page_content=(
            "6. Quadro economico a.s. 2026/2027 a.s. 2027/2028 totale "
            "Costo per personale € 9.000,00 € 9.000,00 € 18.000,00 "
            "Costo per attrezzature € 785,00 € 785,00 € 1.570,00 "
            "Totale € 9.785,00 € 9.785,00 € 19.570,00"
        ),
        metadata={"ente": "Comune di Abetone Cutigliano", "pagina": 14},
    ),
    Document(
        page_content=(
            "Sono ammissibili eventuali costi indiretti, calcolati "
            "forfettariamente in un valore massimo pari al 7% delle altre "
            "spese sopradette, ai sensi dell'art. 54 del Reg. UE 2021/1060."
        ),
        metadata={"ente": "Regione Toscana", "pagina": 11},
    ),
    # Per i casi falsificati della revisione del 12 novembre 2026: valori
    # che contengono, come testo, quelli inventati nelle risposte
    Document(
        page_content=(
            "Il contributo è pari all'80% della spesa ammissibile, fino a "
            "€ 150.000,00. La dotazione complessiva è di 19.5 milioni di euro. "
            "Le domande si presentano entro il 13 novembre 2026. Il diritto di "
            "segreteria è di 54 euro. Il bando è approvato con decreto "
            "dirigenziale n. 1234 del 12/03/2026."
        ),
        metadata={"ente": "Regione Toscana", "pagina": 3},
    ),
    # Un frammento il cui atto sta solo nei metadati, come nell'intestazione
    # [n] ... atto: ... che il modello riceve
    Document(
        page_content="Il compenso giornaliero è ammesso fino a € 322,00.",
        metadata={
            "ente": "Regione Toscana",
            "pagina": 2,
            "riferimento_atto": "Decreto dirigenziale n. 9550 del 28/04/2026",
        },
    ),
]

# Un elenco con un solo bando, la cui riga scrive le date in ISO
RIGA_BANDO = (
    "«Bando di prova» (Regione Toscana) | scade il 2027-07-31 (fra 261 giorni) "
    "| atto: decreto dirigenziale n. 18191"
)
BANDO = Risultato(
    f"Bandi aperti:\n- [#1] {RIGA_BANDO}",
    fonti=["Portale, decreto dirigenziale n. 18191"],
    voci=[VoceBando(RIGA_BANDO, "Portale, decreto dirigenziale n. 18191")],
)

POPOLAZIONE = SimpleNamespace(
    testo="Dato più recente: 1834 abitanti al 1 gennaio 2026.",
    fonti=["ISTAT"],
)

BANDI = SimpleNamespace(
    testo="progetto ammissibile da 25.000 a 35.000 euro",
    fonti=["Portale"],
)

CASI = [
    {
        "nome": "importo corretto",
        "risposta": "Il costo massimo è € 322,00 (fonte: [1], Regione Toscana, pag. 11).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "importo INVENTATO",
        "risposta": "Il costo massimo è € 450,00 (fonte: [1], Regione Toscana, pag. 11).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "importo giusto, frammento SBAGLIATO",
        "risposta": "Il costo massimo è € 322,00 (fonte: [2], Comune, pag. 14).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "importo SENZA citazione",
        "risposta": "Il costo massimo è € 322,00 e va applicato a tutti gli incarichi.",
        "atteso": {"verificato": 0, "non_trovato": 0, "non_citato": 1},
    },
    {
        "nome": "cifra alterata di poco",
        "risposta": "Il totale è € 19.520,00 (fonte: [2], Comune, pag. 14).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "percentuale corretta",
        "risposta": "I costi indiretti sono al 7% (fonte: [3], Regione Toscana, pag. 11).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "percentuale INVENTATA",
        "risposta": "I costi indiretti sono al 15% (fonte: [3], Regione Toscana, pag. 11).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "formattazione diversa dello stesso importo",
        "risposta": "Il costo massimo è di 322,00 euro (fonte: [1], Regione Toscana, pag. 11).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "rifiuto: nessun dato",
        "risposta": "Non trovo la risposta nei documenti disponibili.",
        "atteso": {"verificato": 0, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "dato numerico corretto",
        "risposta": "Il comune ha 1834 abitanti (fonte: [D1], ISTAT).",
        "dati": [("popolazione_ultima", POPOLAZIONE)],
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "dato numerico ALTERATO",
        "risposta": "Il comune ha 1900 abitanti (fonte: [D1], ISTAT).",
        "dati": [("popolazione_ultima", POPOLAZIONE)],
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        # Fino al 12 novembre 2026 l'atto nel testo era mascherato e
        # l'atteso era 1 verificato: il caso controllava solo che l'importo
        # non sparisse. Ora il decreto e' un dato, e il frammento 1 non lo
        # riporta ne' nel testo ne' nei metadati.
        "nome": "atto in prosa: importo verificato, decreto assente dalla fonte",
        "risposta": (
            "Secondo il Decreto dirigenziale n. 9550 del 28/04/2026, "
            "il costo è € 322,00 (fonte: [1], Regione, pag. 11)."
        ),
        "atteso": {"verificato": 1, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "N12 atto in prosa: decreto nei metadati del frammento citato",
        "risposta": (
            "Secondo il Decreto dirigenziale n. 9550 del 28/04/2026, "
            "il costo è € 322,00 (fonte: [5], Regione, pag. 2)."
        ),
        # l'atto, la sua data e l'importo
        "atteso": {"verificato": 3, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N21 atto con numero e data nei metadati: entrambi verificati",
        "risposta": (
            "Il compenso è fissato dal decreto dirigenziale n. 9550 del "
            "28/04/2026 (fonte: [5], Regione, pag. 2)."
        ),
        "atteso": {"verificato": 2, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N22 atto giusto con la data SBAGLIATA",
        "risposta": (
            "Il compenso è fissato dal decreto dirigenziale n. 9550 del "
            "28/05/2026 (fonte: [5], Regione, pag. 2)."
        ),
        "atteso": {"verificato": 1, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "citazione con testo prima di fonte",
        "risposta": "Il costo è € 322,00 (nota, fonte: [1], Regione, pag. 11).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "importo con decimali non spezzato",
        "risposta": "Il totale è 19.570,00 € (fonte: [2], Comune, pag. 14).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "importo tra nome atto e data NON deve sparire",
        "risposta": (
            "Il decreto prevede € 322,00 con scadenza il 28/04/2026 "
            "(fonte: [1], Regione, pag. 11)."
        ),
        "atteso": {"verificato": 1, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "separatore migliaia dentro una frase",
        "risposta": "Il progetto va da 25.000 a 35.000 euro (fonte: [D1], Regione).",
        "dati": [("bandi", BANDI)],
        "atteso": {"verificato": 2, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "data ISO e orario sono date",
        "risposta": "Scade il 2026-10-15 alle 12:00 (fonte: [1], Regione, pag. 11).",
        "atteso": {"verificato": 0, "non_trovato": 2, "non_citato": 0},
    },
    {
        "nome": "riferimento normativo CORRETTO ma assente dal frammento citato",
        "risposta": (
            "La dichiarazione è resa ai sensi del D.Lgs. 231/2007 "
            "(fonte: [1], Regione, pag. 11)."
        ),
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    # --- casi falsificati della revisione: un valore contenuto in un altro ---
    {
        "nome": "N1 percentuale contenuta in un'altra (8% contro 80%)",
        "risposta": "Il contributo copre l'8% (fonte: [4], Regione, pag. 3).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "N2 percentuale intera",
        "risposta": "Il contributo copre l'80% (fonte: [4], Regione, pag. 3).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N3 importo contenuto in un altro (50.000 contro 150.000,00)",
        "risposta": "Il contributo arriva a € 50.000 (fonte: [4], Regione, pag. 3).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "N4 importo intero",
        "risposta": "Il contributo arriva a € 150.000 (fonte: [4], Regione, pag. 3).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N5 giorno contenuto in un altro (3 contro 13 novembre)",
        "risposta": "Le domande scadono il 3 novembre 2026 (fonte: [4], Regione).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "N6 giorno intero",
        "risposta": "Le domande scadono il 13 novembre 2026 (fonte: [4], Regione).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    # --- atti nel testo della risposta ---
    {
        "nome": "N7 decreto INVENTATO nel testo",
        "risposta": (
            "Il bando è approvato con decreto n. 9999 del 12/03/2026 "
            "(fonte: [4], Regione)."
        ),
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "N8 decreto giusto nel testo",
        "risposta": (
            "Il bando è approvato con decreto dirigenziale n. 1234 del "
            "12/03/2026 (fonte: [4], Regione)."
        ),
        # il numero e la sua data
        "atteso": {"verificato": 2, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N19 decreto nella citazione di un frammento, nei suoi metadati",
        "risposta": (
            "Il costo è € 322,00 "
            "(fonte: [5], Decreto dirigenziale n. 9550 del 28/04/2026, pag. 2)."
        ),
        # l'importo, l'atto della citazione e la sua data
        "atteso": {"verificato": 3, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N23 decreto nella citazione con la data SBAGLIATA",
        "risposta": (
            "Il costo è € 322,00 "
            "(fonte: [5], Decreto dirigenziale n. 9550 del 28/05/2026, pag. 2)."
        ),
        "atteso": {"verificato": 2, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "N24 DGRT nel testo, con numero e data",
        "risposta": (
            "Il bando attua la DGRT n. 1234 del 12/03/2026 (fonte: [4], Regione)."
        ),
        "atteso": {"verificato": 2, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N20 decreto nella citazione di un frammento che non lo riporta",
        "risposta": (
            "Il costo è € 322,00 "
            "(fonte: [1], Decreto dirigenziale n. 9550 del 28/04/2026, pag. 11)."
        ),
        "atteso": {"verificato": 1, "non_trovato": 1, "non_citato": 0},
    },
    # --- riferimento n/aaaa e atto con numero e data ---
    {
        "nome": "N17 riferimento n/aaaa contro atto con numero e data",
        "risposta": "Il bando è il n. 1234/2026 (fonte: [4], Regione).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N18 riferimento n/aaaa con l'anno SBAGLIATO",
        "risposta": "Il bando è il n. 1234/2025 (fonte: [4], Regione).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    # --- date in forme diverse contro la riga ISO di un bando ---
    {
        "nome": "N9 data numerica contro riga ISO",
        "risposta": (
            "Il bando scade il 31/07/2027 "
            "(fonte: [D1.1], decreto dirigenziale n. 18191)."
        ),
        "dati": [("bandi_aperti_per_ente", BANDO)],
        "atteso": {"verificato": 2, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N10 data in lettere contro riga ISO",
        "risposta": (
            "Il bando scade il 31 luglio 2027 "
            "(fonte: [D1.1], decreto dirigenziale n. 18191)."
        ),
        "dati": [("bandi_aperti_per_ente", BANDO)],
        "atteso": {"verificato": 2, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N11 giorni contenuti in un altro numero (26 contro 261)",
        "risposta": (
            "Mancano 26 giorni alla scadenza "
            "(fonte: [D1.1], decreto dirigenziale n. 18191)."
        ),
        "dati": [("bandi_aperti_per_ente", BANDO)],
        "atteso": {"verificato": 1, "non_trovato": 1, "non_citato": 0},
    },
    # --- importi con moltiplicatore ---
    {
        "nome": "N13 importo in milioni, scritto in un'altra forma",
        "risposta": "La dotazione è di 19,5 milioni di euro (fonte: [4], Regione).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N14 importo in milioni INVENTATO",
        "risposta": "La dotazione è di 19,8 milioni di euro (fonte: [4], Regione).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    # --- articoli: si confermano solo con un articolo ---
    {
        "nome": "N15 articolo confermato solo da un importo uguale",
        "risposta": "La spesa è ammessa ai sensi dell'art. 54 (fonte: [4], Regione).",
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "N16 articolo presente nel frammento",
        "risposta": "La spesa è ammessa ai sensi dell'art. 54 (fonte: [3], Regione).",
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    # Prova del 12 novembre 2026: il testo nella parentesi prima di "fonte:"
    # è contenuto della risposta, e si verifica sulla fonte della parentesi
    {
        "nome": "N23 percentuale dentro la parentesi, prima di fonte",
        "risposta": (
            "I costi indiretti sono ammessi (inclusa l'aliquota forfettaria del "
            "7% per i costi indiretti, fonte: [3], Regione Toscana, pag. 11)."
        ),
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N24 percentuale FALSIFICATA dentro la parentesi, prima di fonte",
        "risposta": (
            "I costi indiretti sono ammessi (inclusa l'aliquota forfettaria del "
            "17% per i costi indiretti, fonte: [3], Regione Toscana, pag. 11)."
        ),
        "atteso": {"verificato": 0, "non_trovato": 1, "non_citato": 0},
    },
    {
        "nome": "N25 importo prima di fonte, atto con data dopo fonte",
        "risposta": (
            "Il compenso giornaliero è ammesso (fino a € 322,00, fonte: [5], "
            "Regione Toscana, Decreto dirigenziale n. 9550 del 28/04/2026, pag. 2)."
        ),
        "atteso": {"verificato": 3, "non_trovato": 0, "non_citato": 0},
    },
    {
        "nome": "N26 atto prima di fonte, contato una volta sola",
        "risposta": (
            "Il compenso è ammesso (approvato con decreto dirigenziale n. 9550 "
            "del 28/04/2026, fonte: [5], Regione, pag. 2)."
        ),
        "atteso": {"verificato": 2, "non_trovato": 0, "non_citato": 0},
    },
]


@pytest.mark.parametrize("caso", CASI, ids=[caso["nome"] for caso in CASI])
def test_verifica_conteggi(caso):
    esiti = verifica(caso["risposta"], FRAMMENTI, caso.get("dati"))
    assert riassumi(esiti) == caso["atteso"]


def test_data_dell_atto_sbagliata_indica_quella_della_fonte():
    risposta = (
        "Il compenso è fissato dal decreto dirigenziale n. 9550 del "
        "28/05/2026 (fonte: [5], Regione, pag. 2)."
    )
    atto, data_atto = verifica(risposta, FRAMMENTI)
    assert (atto.tipo, atto.valore, atto.stato) == ("atto", "9550", "verificato")
    assert (data_atto.tipo, data_atto.valore, data_atto.stato) == (
        "data",
        "28/05/2026",
        "non_trovato",
    )
    assert data_atto.dettaglio == "l'atto 9550 nella fonte citata ha la data 2026-04-28"


def test_atto_non_trovato_la_sua_data_non_si_giudica():
    """Il caso 12: l'esito dell'atto copre gia' tutto il riferimento."""
    risposta = (
        "Secondo il Decreto dirigenziale n. 9550 del 28/04/2026, "
        "il costo è € 322,00 (fonte: [1], Regione, pag. 11)."
    )
    assert [(e.tipo, e.stato) for e in verifica(risposta, FRAMMENTI)] == [
        ("atto", "non_trovato"),
        ("importo", "verificato"),
    ]


# --- atti nel testo: che cosa e' un atto ---


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [
        ("Delibera di Giunta Regionale Toscana n. 546", ("atto", "546")),
        ("delibera della giunta regionale toscana n. 546", ("atto", "546")),
        (
            "Decreto del Presidente della Giunta Regionale Toscana n. 12",
            ("atto", "12"),
        ),
        ("decreto della Regione Toscana n. 9550", ("atto", "9550")),
        ("DGRT n. 546", ("atto", "546")),
        ("D.G.R.T. n. 546", ("atto", "546")),
        ("DGR 1081/2026", ("atto", "1081")),
        # parole libere tra la parola e il numero: non e' un atto
        ("il decreto stabilisce n. 10 posti", ("quantita", "10")),
        ("il decreto prevede € 322,00", ("importo", "322,00")),
    ],
)
def test_che_cosa_e_un_atto(testo, atteso):
    (dato,) = trova_dati(testo)
    assert (dato.tipo, dato.valore) == atteso


# --- giudizio: il colore del pannello ---


def esito(tipo: str, stato: str) -> Esito:
    return Esito(tipo, "x", ["1"], stato)


@pytest.mark.parametrize(
    ("esiti", "livello"),
    [
        ([], "nessuno"),
        ([esito("anno", "verificato")], "arancione"),
        ([esito("importo", "verificato"), esito("importo", "non_citato")], "arancione"),
        (
            [esito("data", "verificato"), esito("data", "citazione_generica")],
            "arancione",
        ),
        ([esito("importo", "verificato"), esito("data", "non_trovato")], "rosso"),
        ([esito("importo", "non_citato"), esito("data", "non_trovato")], "rosso"),
        ([esito("importo", "verificato"), esito("anno", "verificato")], "verde"),
    ],
    ids=[
        "nessun esito",
        "solo anni verificati",
        "un verificato e un non citato",
        "un verificato e una citazione generica",
        "un non trovato",
        "un non trovato e un non citato",
        "tutti verificati",
    ],
)
def test_giudizio(esiti, livello):
    assert giudizio(esiti)[0] == livello


def test_giudizio_non_e_verde_con_zero_verificati():
    """Il difetto della revisione: verde con "0 dati verificati"."""
    livello, messaggio = giudizio([esito("importo", "non_citato")] * 3)
    assert livello == "arancione"
    assert messaggio.startswith("Nessun dato verificato oltre agli anni, 3 dato/i")


def test_giudizio_conta_i_verificati_senza_gli_anni():
    livello, messaggio = giudizio(
        [esito("importo", "verificato"), esito("anno", "verificato")]
    )
    assert (livello, messaggio) == ("verde", "Dati verificati nella fonte citata: 1.")


def test_giudizio_arancione_dice_cosa_manca():
    _, messaggio = giudizio(
        [esito("importo", "verificato"), esito("importo", "non_citato")]
    )
    assert messaggio == (
        "Dati verificati: 1; 1 dato/i senza fonte. "
        "Verificare manualmente prima di riutilizzare la risposta."
    )


def test_tipi_data_e_orario():
    risposta = "Scade il 2026-10-15 alle 12:00 (fonte: [1], Regione, pag. 11)."
    esiti = verifica(risposta, FRAMMENTI)
    assert [(e.tipo, e.valore) for e in esiti] == [
        ("data", "2026-10-15"),
        ("data", "12:00"),
    ]
