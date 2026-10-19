"""Collaudo del verificatore con risposte deliberatamente falsificate.

Non chiama il modello: costruisce risposte finte e controlla che
il verificatore reagisca come previsto. Gratuito e istantaneo.
"""
from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

from src.verification.controllo import riassumi, verifica

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
]

POPOLAZIONE = SimpleNamespace(
    testo="Dato più recente: 1834 abitanti al 1 gennaio 2026.",
    fonti=["ISTAT"],
)

BANDI= SimpleNamespace(
    testo="progetto ammissibile da 25.000 a 35.000 euro",
    fonti= ["Portale"],
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
        "nome": "riferimento all'atto in prosa, non citazione",
        "risposta": (
            "Secondo il Decreto dirigenziale n. 9550 del 28/04/2026, "
            "il costo è € 322,00 (fonte: [1], Regione, pag. 11)."
        ),
        "atteso": {"verificato": 1, "non_trovato": 0, "non_citato": 0},
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
        "dati": [("bandi",BANDI)],
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
]


@pytest.mark.parametrize("caso", CASI, ids=[caso["nome"] for caso in CASI])
def test_verifica_conteggi(caso):
    esiti = verifica(caso["risposta"], FRAMMENTI, caso.get("dati"))
    assert riassumi(esiti) == caso["atteso"]


def test_tipi_data_e_orario():
    risposta = "Scade il 2026-10-15 alle 12:00 (fonte: [1], Regione, pag. 11)."
    esiti = verifica(risposta, FRAMMENTI)
    assert [(e.tipo, e.valore) for e in esiti] == [
        ("data", "2026-10-15"),
        ("data", "12:00"),
    ]