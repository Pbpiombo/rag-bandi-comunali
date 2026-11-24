"""Frammenti vicini passati al modello (passo 19e, rimedio 1).

con_vicini è pura: i test usano frammenti inventati e un `prendi` su un
dizionario. La catena si prova con recupero, router e modello finti, sul
database temporaneo di tests/conftest.py.
"""

import sqlite3

import pytest
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.runnables import RunnableLambda

from src.chains.rag import etichetta
from src.recupero_documenti import (
    RecuperoPerDocumento,
    con_vicini,
    unisci_testi,
)
from src.retrieval import RecuperoIbrido
from src.verification.controllo import verifica

AVVISO = "avviso-a.pdf"
ALTRO = "avviso-b.pdf"


def frammento(fonte, numero, testo=None, pagina=1, bando="bando-a"):
    meta = {"fonte": fonte, "chunk_num": numero, "page": pagina}
    if bando:
        meta["id_bando"] = bando
    return Document(page_content=testo or f"testo {fonte} {numero}.", metadata=meta)


def archivio(*documenti):
    """Un `prendi` su un dizionario, che registra le chiamate."""
    per_chiave = {(d.metadata["fonte"], d.metadata["chunk_num"]): d for d in documenti}
    chiamate = []

    def prendi(fonte, numero):
        chiamate.append((fonte, numero))
        return per_chiave.get((fonte, numero))

    prendi.chiamate = chiamate
    return prendi


def risultati(*documenti):
    return [(d, 1.0 / (i + 1), [f"densa #{i + 1}"]) for i, d in enumerate(documenti)]


def chiavi(uscita):
    return [d.metadata.get("vicini") for d, _, _ in uscita]


# --- regole della scelta ---


def test_mai_vicini_di_un_altro_file_ne_oltre_la_fine_del_file():
    # #5 è l'ultimo frammento di avviso-a; avviso-b ha un #6 che non va preso
    a4, a5 = frammento(AVVISO, 4), frammento(AVVISO, 5)
    b6 = frammento(ALTRO, 6)
    uscita = con_vicini(risultati(a5), archivio(a4, a5, b6), (-1, 1))
    assert chiavi(uscita) == [[4, 5]]
    assert "avviso-b" not in uscita[0][0].page_content


def test_inizio_del_file_senza_frammento_prima():
    a0, a1 = frammento(AVVISO, 0), frammento(AVVISO, 1)
    uscita = con_vicini(risultati(a0), archivio(a0, a1), (-1, 1))
    assert chiavi(uscita) == [[0, 1]]


def test_vicino_gia_tra_i_risultati_non_si_ripete():
    docs = [frammento(AVVISO, n) for n in range(3, 9)]
    prendi = archivio(*docs)
    uscita = con_vicini(risultati(docs[2], docs[3]), prendi, (-1, 1))  # #5 e #6
    assert chiavi(uscita) == [[4, 5, 6, 7]]
    testo = uscita[0][0].page_content
    for n in (4, 5, 6, 7):
        assert testo.count(f"testo {AVVISO} {n}.") == 1
    assert (AVVISO, 5) not in prendi.chiamate and (AVVISO, 6) not in prendi.chiamate


def test_contigui_uniti_in_ordine_di_documento_e_blocchi_nell_ordine_della_ricerca():
    docs = [frammento(AVVISO, n) for n in range(1, 10)]
    # la ricerca mette prima #7, poi #3
    uscita = con_vicini(risultati(docs[6], docs[2]), archivio(*docs), (-1, 1))
    assert chiavi(uscita) == [[6, 7, 8], [2, 3, 4]]
    testo = uscita[0][0].page_content
    assert testo.index("6.") < testo.index("7.") < testo.index("8.")


def test_solo_il_frammento_dopo():
    docs = [frammento(AVVISO, n) for n in range(1, 5)]
    uscita = con_vicini(risultati(docs[1]), archivio(*docs), (1,))
    assert chiavi(uscita) == [[2, 3]]


def test_senza_spostamenti_i_risultati_sono_gli_stessi():
    docs = [frammento(AVVISO, n) for n in range(1, 5)]
    entrata = risultati(docs[1], docs[3])
    prendi = archivio(*docs)
    assert con_vicini(entrata, prendi, ()) is entrata
    assert prendi.chiamate == []


def test_i_frammenti_che_non_sono_avvisi_restano_come_sono():
    pdf = frammento("relazione.pdf", 3, bando=None)
    vicino_pdf = frammento("relazione.pdf", 4, bando=None)
    a2, a3 = frammento(AVVISO, 2), frammento(AVVISO, 3)
    prendi = archivio(pdf, vicino_pdf, a2, a3)
    uscita = con_vicini(risultati(pdf, a3), prendi, (-1, 1))
    assert uscita[0][0] is pdf
    assert uscita[0][2] == ["densa #1"]
    assert chiavi(uscita) == [None, [2, 3]]
    assert all(fonte != "relazione.pdf" for fonte, _ in prendi.chiamate)


def test_origini_e_punteggio_del_blocco():
    docs = [frammento(AVVISO, n) for n in range(1, 5)]
    uscita = con_vicini(risultati(docs[1]), archivio(*docs), (-1, 1))
    _, punteggio, origini = uscita[0]
    assert punteggio == 1.0
    assert origini == ["densa #1", "vicini: 1, 2, 3"]


def test_i_documenti_del_recupero_non_si_modificano():
    a1, a2 = frammento(AVVISO, 1), frammento(AVVISO, 2)
    prima = dict(a1.metadata)
    con_vicini(risultati(a1), archivio(a1, a2), (-1, 1))
    assert a1.metadata == prima


# --- unione dei testi e pagine ---


def test_unione_toglie_la_sovrapposizione():
    ripetuto = "il contributo è concesso per tre anni dalla data di erogazione"
    a = "Primo tratto. " + ripetuto
    b = ripetuto + " Secondo tratto."
    assert unisci_testi(a, b) == "Primo tratto. " + ripetuto + " Secondo tratto."


def test_unione_senza_sovrapposizione_va_a_capo():
    assert unisci_testi("Fine del punto 3.", "4. Inizio del punto 4.") == (
        "Fine del punto 3.\n4. Inizio del punto 4."
    )


def test_sovrapposizione_troppo_corta_non_si_toglie():
    # 6 caratteri in comune: sotto la soglia, possono essere un caso
    assert unisci_testi("fino a euro", "a euro 500") == "fino a euro\na euro 500"


def test_blocco_su_due_pagine_ha_la_pagina_n_m_nell_etichetta():
    a1 = frammento(AVVISO, 1, pagina=3)
    a2 = frammento(AVVISO, 2, pagina=4)
    uscita = con_vicini(risultati(a1), archivio(a1, a2), (1,))
    documento = uscita[0][0]
    assert documento.metadata["page"] == "3-4"
    assert "pag. 3-4" in etichetta(documento, 1)


def test_blocco_su_una_pagina_tiene_il_numero():
    a1, a2 = frammento(AVVISO, 1, pagina=3), frammento(AVVISO, 2, pagina=3)
    uscita = con_vicini(risultati(a1), archivio(a1, a2), (1,))
    assert uscita[0][0].metadata["page"] == 3


# --- verificatore ---


def test_dato_solo_nel_vicino_si_verifica_citando_il_blocco():
    a5 = frammento(AVVISO, 5, "Il contributo è concesso alle micro imprese.", pagina=3)
    a6 = frammento(AVVISO, 6, "L'importo massimo è di 45.000 euro.", pagina=4)
    risposta = (
        "Il contributo massimo è di 45.000 euro (fonte: [1], Regione Toscana, pag. 4)."
    )
    senza = verifica(risposta, [a5])
    assert [e.stato for e in senza if e.valore == "45.000"] == ["non_trovato"]
    con = con_vicini(risultati(a5), archivio(a5, a6), (-1, 1))
    esiti = verifica(risposta, [d for d, _, _ in con])
    assert [e.stato for e in esiti if e.valore == "45.000"] == ["verificato"]


# --- recuperi ---


class RecuperoSenzaFrammento:
    def titoli(self):
        return {}

    def cerca(self, domanda, k=10):
        return []


def test_un_recupero_senza_frammento_spegne_i_vicini():
    assert RecuperoPerDocumento(RecuperoSenzaFrammento()).frammento(AVVISO, 1) is None


def test_recupero_ibrido_restituisce_il_frammento_dalla_memoria():
    recupero = RecuperoIbrido.__new__(RecuperoIbrido)
    a1 = frammento(AVVISO, 1)
    recupero._per_chiave = {(AVVISO, 1): a1}
    assert recupero.frammento(AVVISO, 1) is a1
    assert recupero.frammento(AVVISO, 2) is None


# --- catena ---


@pytest.fixture
def db_con_ente(db_su_file):
    c = sqlite3.connect(db_su_file)
    c.execute(
        "INSERT INTO enti (codice_fiscale, nome, tipo, regione, provincia, fonte, "
        "verificato_il) VALUES ('11111111111', 'Comune finto', 'comune', 'Toscana', "
        "'Pistoia', 'prova', '2026-01-01')"
    )
    c.commit()
    c.close()
    return db_su_file


class RecuperoConFrammenti:
    """Un recupero finto che restituisce #5 e sa dare i frammenti del file."""

    def __init__(self, documenti, trovati, con_frammento=True):
        self.per_chiave = {
            (d.metadata["fonte"], d.metadata["chunk_num"]): d for d in documenti
        }
        self.trovati = trovati
        if con_frammento:
            self.frammento = lambda fonte, numero: self.per_chiave.get((fonte, numero))

    def titoli(self):
        return {}

    def cerca(self, domanda, k=10):
        return [(d, 0.5, ["densa #1"]) for d in self.trovati]


def catena(monkeypatch, recupero, spostamenti=None):
    """La catena con router e modello finti; con `spostamenti` l'interruttore
    dei vicini è impostato dal test, senza `spostamenti` resta il predefinito."""
    from src.chains import rag

    monkeypatch.setattr(
        rag,
        "costruisci_router",
        lambda: RunnableLambda(lambda e: '{"documenti": true, "interrogazioni": []}'),
    )
    monkeypatch.setattr(
        rag, "ChatAnthropic", lambda **_: FakeListChatModel(responses=["ok"])
    )
    if spostamenti is not None:
        monkeypatch.setattr(rag, "SPOSTAMENTI_VICINI", spostamenti)
    return rag.costruisci_catena("11111111111", recupero=recupero)


def tre_frammenti():
    return (
        frammento(AVVISO, 4, "Requisiti di accesso.", pagina=2),
        frammento(AVVISO, 5, "Le imprese devono mantenere la sede", pagina=2),
        frammento(AVVISO, 6, "per tre anni dalla data di erogazione.", pagina=3),
    )


def test_la_catena_passa_il_vicino_al_modello(db_con_ente, monkeypatch):
    a4, a5, a6 = tre_frammenti()
    recupero = RecuperoConFrammenti([a4, a5, a6], [a5])
    esito = catena(monkeypatch, recupero, (-1, 1)).invoke("Per quanto?")
    assert "per tre anni dalla data di erogazione" in esito["contesto"]
    assert "pag. 2-3" in esito["contesto"]
    assert len(esito["documenti"]) == len(esito["origini"]) == 1


def test_la_catena_senza_frammento_resta_come_oggi(db_con_ente, monkeypatch):
    _, a5, a6 = tre_frammenti()
    recupero = RecuperoConFrammenti([a5, a6], [a5], con_frammento=False)
    esito = catena(monkeypatch, recupero, (-1, 1)).invoke("Per quanto?")
    assert "per tre anni" not in esito["contesto"]
    assert "pag. 2-3" not in esito["contesto"]


def test_con_il_valore_predefinito_il_contesto_e_quello_senza_vicini(
    db_con_ente, monkeypatch
):
    # vicini spenti finché l'ordine c-LR e il filtro per bando non sono
    # nella catena (docs/coda.md, "Passo 19e, rimedio 1")
    documenti = tre_frammenti()
    predefinito = catena(
        monkeypatch, RecuperoConFrammenti(documenti, [documenti[1]])
    ).invoke("Per quanto?")
    senza = catena(
        monkeypatch,
        RecuperoConFrammenti(documenti, [documenti[1]], con_frammento=False),
        (),
    ).invoke("Per quanto?")
    assert predefinito["contesto"] == senza["contesto"]
    assert "per tre anni" not in predefinito["contesto"]
