"""Test del router: profilo dell'ente, lettura della risposta, avviso nell'app."""

import inspect

import pytest
from langchain_core.messages import AIMessage

from src.chains import router as modulo_router
from src.chains.router import descrivi_profilo


def test_booleani_diventano_si_e_no():
    testo = descrivi_profilo({"capofila_area": False, "toscana_diffusa": True})
    assert "- capofila_area: no" in testo
    assert "- toscana_diffusa: sì" in testo


def test_valore_mancante_diventa_non_verificato():
    testo = descrivi_profilo({"toscana_diffusa": None})
    assert "- toscana_diffusa: non verificato" in testo


def test_testo_resta_invariato():
    testo = descrivi_profilo({"regione": "Toscana"})
    assert "- regione: Toscana" in testo


def test_esempi_del_prompt_usano_interrogazioni_esistenti():
    # Un'interrogazione rinominata non deve restare negli esempi del router
    import re

    from src.chains.router import ISTRUZIONI_ROUTER
    from src.database.repertorio import PER_NOME

    # "..." e' il segnaposto dello schema JSON, non un esempio
    nomi = re.findall(r'"nome": "([^".][^"]*)"', ISTRUZIONI_ROUTER)
    assert "dettaglio_bando" in nomi
    assert [n for n in nomi if n not in PER_NOME] == []


# --- Lettura della risposta del router (correzione 1, docs/piano-correzioni-lotto1.md) ---

DECISIONE = '{"documenti": false, "interrogazioni": []}'


@pytest.fixture
def senza_database(monkeypatch):
    """decidi senza il database vero: repertorio e stato dell'archivio finti."""
    monkeypatch.setattr(modulo_router, "descrivi_repertorio", lambda: "repertorio")
    monkeypatch.setattr(modulo_router, "stato_archivio", lambda codice: "stato")


class RouterFinto:
    """Un router che restituisce sempre la stessa risposta."""

    def __init__(self, risposta):
        self.risposta = risposta

    def invoke(self, entrata):
        return self.risposta


def decidi_su(risposta):
    return modulo_router.decidi(
        RouterFinto(risposta), "domanda?", codice_ente="1", profilo={}
    )


@pytest.mark.parametrize(
    "testo",
    [
        # Forma di A01 del lotto 1: un paragrafo, poi il JSON
        "Questa domanda non riguarda gli archivi a mia disposizione.\n\n" + DECISIONE,
        # JSON seguito da testo
        DECISIONE + "\n\nPer questo tipo di informazione contatti il Comune.",
        # Testo prima e dopo, con il paragrafo in mezzo
        "Premessa.\n\n" + DECISIONE + "\n\nConsiglio finale.",
        # JSON tra recinzioni con testo intorno
        "Ecco la decisione:\n```json\n" + DECISIONE + "\n```\nFine.",
    ],
)
def test_decisione_estratta_dal_testo(senza_database, testo):
    decisione = decidi_su(testo)
    assert "errore" not in decisione
    assert decisione == {"documenti": False, "interrogazioni": []}


def test_decisione_con_interrogazioni_annidate(senza_database):
    testo = (
        "Uso i bandi.\n"
        '{"documenti": true, "interrogazioni": [{"nome": "bandi_per_tema", '
        '"parametri": {"tema": "sport"}}]}'
    )
    decisione = decidi_su(testo)
    assert decisione["interrogazioni"] == [
        {"nome": "bandi_per_tema", "parametri": {"tema": "sport"}}
    ]


def test_due_decisioni_uguali_valgono_una(senza_database):
    assert "errore" not in decidi_su(DECISIONE + "\n" + DECISIONE)


def test_due_decisioni_diverse_sono_un_errore(senza_database):
    testo = DECISIONE + '\n{"documenti": true, "interrogazioni": []}'
    assert "errore" in decidi_su(testo)


@pytest.mark.parametrize("testo", ["", "Non so rispondere.", "[1, 2]", '{"altro": 1}'])
def test_testo_senza_decisione_e_un_errore(senza_database, testo):
    decisione = decidi_su(testo)
    assert decisione["documenti"] is True
    assert decisione["interrogazioni"] == []
    assert decisione["errore"]
    assert decisione["grezzo"] == testo


def test_json_troncato_registra_stop_reason_e_testo_grezzo(senza_database):
    # Forma di L05 del lotto 1: tetto di max_tokens raggiunto a metà JSON
    troncato = (
        '{"documenti": false, "interrogazioni": [{"nome": "bandi_per_tema", "parametri'
    )
    risposta = AIMessage(
        content=troncato, response_metadata={"stop_reason": "max_tokens"}
    )
    decisione = decidi_su(risposta)
    assert decisione["errore"]
    assert decisione["stop_reason"] == "max_tokens"
    assert decisione["grezzo"] == troncato


def test_messaggio_con_ragionamento_usa_solo_il_testo(senza_database):
    risposta = AIMessage(
        content=[
            {"type": "thinking", "thinking": ""},
            {"type": "text", "text": DECISIONE},
        ],
        response_metadata={"stop_reason": "end_turn"},
    )
    decisione = decidi_su(risposta)
    assert decisione == {
        "documenti": False,
        "interrogazioni": [],
        "stop_reason": "end_turn",
    }


def test_stringa_senza_stop_reason_come_prima(senza_database):
    # Un router che restituisce testo (i test, gli script) non aggiunge chiavi
    assert decidi_su(DECISIONE) == {"documenti": False, "interrogazioni": []}


def test_max_tokens_del_router_almeno_2048(monkeypatch):
    creati = []

    def modello_finto(**argomenti):
        creati.append(argomenti)
        from langchain_core.language_models.fake_chat_models import (
            FakeListChatModel,
        )

        return FakeListChatModel(responses=[DECISIONE])

    monkeypatch.setattr(modulo_router, "ChatAnthropic", modello_finto)
    catena = modulo_router.costruisci_router()
    assert creati[0]["max_tokens"] >= 2048
    # Il router restituisce il messaggio intero, non solo il testo
    risposta = catena.invoke(
        {"domanda": "?", "repertorio": "", "stato": "", "profilo": ""}
    )
    assert isinstance(risposta, AIMessage)


# --- B: il testo grezzo del router non arriva all'utente ---


def test_app_con_router_in_errore_mostra_la_riga_neutra():
    from app.app import AVVISO_ROUTER, avviso_router

    decisione = {
        "documenti": True,
        "interrogazioni": [],
        "errore": "risposta del router non interpretabile",
        "stop_reason": "max_tokens",
        "grezzo": "Questa domanda non riguarda gli archivi SEGRETO",
    }
    avviso = avviso_router(decisione)
    assert (
        avviso
        == AVVISO_ROUTER
        == (
            "Non sono riuscito a scegliere le interrogazioni sui dati: "
            "la risposta si basa solo sui documenti."
        )
    )
    assert "SEGRETO" not in avviso
    assert "non interpretabile" not in avviso
    assert avviso_router({"documenti": True, "interrogazioni": []}) is None


def test_app_non_scrive_il_dettaglio_del_router():
    import app.app as app

    sorgente = inspect.getsource(app.main)
    assert "decisione['errore']" not in sorgente
    assert 'decisione["errore"]' not in sorgente
    assert "grezzo" not in sorgente
