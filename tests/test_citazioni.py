"""Test delle citazioni ripetute accorciate nel testo mostrato (25/11/2026).

Le citazioni vengono dalle risposte vere salvate: domande sulla
sospensione degli incentivi (dati-grezzi/prova/sospensione/2026-11-24/),
lotti 1-3 dell'insieme di prova e passo 19e. Si riporta solo il testo
delle citazioni, mai quello delle domande. Le citazioni malformate sono
scritte a mano: nelle 226 risposte salvate non ce n'e' nessuna.
"""

import pytest

from src.citazioni import accorcia_citazioni

# Il riferimento_atto degli incentivi ai datori di lavoro [D1.13], come lo
# scrive la risposta sul disoccupato di 57 anni (sospensione, 24/11/2026)
ATTO_INCENTIVI = (
    "Decreto dirigenziale Arti 848 del 2 novembre 2023, modificato con decreto "
    "995 del 27 dicembre 2023, rettificato con decreto Arti 689 del 29 luglio "
    "2025, rifinanziato con decreto Arti 1043 del 18 novembre 2025, modificato "
    "con decreto Arti 1189 del 29 dicembre 2025, rifinanziato con decreto Arti "
    "1019 del 3 settembre 2026, modificato con decreto Arti 1318 del 6 novembre "
    "2026; sospeso per l'articolo 5 lettere a-e con decreto n. 742/2026 di Arti, "
    "pubblicato sul Burt l'8 luglio 2026"
)
INCENTIVI = f"(fonte: [D1.13], {ATTO_INCENTIVI})"

# Passo 19e: un frammento citato con pagine diverse; due frammenti dello
# stesso decreto
BANDO_18191 = "Regione Toscana, Decreto n. 18191 del 07/08/2026, Allegato A"
BANDO_13512 = "Regione Toscana, Decreto n. 13512 del 19/06/2026, Allegato 1"


def test_prima_citazione_intera_e_successive_ridotte():
    testo = (
        f"In archivio risulta un bando {INCENTIVI}.\n\n"
        f"Tuttavia questo bando è sospeso in parte {INCENTIVI}.\n\n"
        f"Per queste categorie si istruiscono solo le domande {INCENTIVI}."
    )
    assert accorcia_citazioni(testo) == (
        f"In archivio risulta un bando {INCENTIVI}.\n\n"
        "Tuttavia questo bando è sospeso in parte (fonte: [D1.13]).\n\n"
        "Per queste categorie si istruiscono solo le domande (fonte: [D1.13])."
    )


def test_stessa_fonte_con_pagina_diversa_tiene_la_pagina():
    testo = (
        f"Uno (fonte: [1], {BANDO_18191}, pag. 1). "
        f"Due (fonte: [1], {BANDO_18191}, pag. 3). "
        f"Tre (fonte: [1], {BANDO_18191}, pag. 1)."
    )
    assert accorcia_citazioni(testo) == (
        f"Uno (fonte: [1], {BANDO_18191}, pag. 1). "
        "Due (fonte: [1], pag. 3). "
        "Tre (fonte: [1])."
    )


def test_due_fonti_con_la_stessa_descrizione_restano_intere_la_prima_volta():
    testo = (
        f"A (fonte: [2], {BANDO_13512}, pag. 6). "
        f"B (fonte: [3], {BANDO_13512}, pag. 31). "
        f"C (fonte: [2], {BANDO_13512}, pag. 6)."
    )
    assert accorcia_citazioni(testo) == (
        f"A (fonte: [2], {BANDO_13512}, pag. 6). "
        f"B (fonte: [3], {BANDO_13512}, pag. 31). "
        "C (fonte: [2])."
    )


def test_stessa_etichetta_con_descrizioni_diverse_non_si_accorcia():
    # Lotto 1, L02: [D1.7] citato con e senza la modifica del decreto
    testo = (
        "Uno (fonte: [D1.7], decreto dirigenziale 9505 del 30 aprile 2026, come "
        "modificato dal decreto dirigenziale 13512 del 19 giugno 2026). "
        "Due (fonte: [D1.7], decreto dirigenziale 9505 del 30 aprile 2026)."
    )
    assert accorcia_citazioni(testo) == testo


def test_piu_etichette_nella_stessa_parentesi_non_si_accorcia():
    # Lotto 1, P10: la stessa citazione doppia compare due volte
    doppia = (
        "(fonte: [D1.1], Decreto n.22460 del 10.10.2026 - Decreto di approvazione "
        "del Bando; fonte: [D1.2], Decreto n.22552 del 13.10.2026 - Decreto di "
        "approvazione del Bando)"
    )
    testo = f"Uno {doppia}. Due {doppia}."
    assert accorcia_citazioni(testo) == testo


def test_piu_etichette_non_conta_come_prima_citazione():
    # La citazione doppia resta com'e' e non registra [3]: la prima
    # citazione semplice di [3] resta intera
    testo = (
        f"A (fonte: [3], {BANDO_13512}, pag. 31; fonte: [7], {BANDO_13512}, "
        f"pag. 31). B (fonte: [3], {BANDO_13512}, pag. 31). "
        f"C (fonte: [3], {BANDO_13512}, pag. 31)."
    )
    assert accorcia_citazioni(testo) == (
        f"A (fonte: [3], {BANDO_13512}, pag. 31; fonte: [7], {BANDO_13512}, "
        f"pag. 31). B (fonte: [3], {BANDO_13512}, pag. 31). C (fonte: [3])."
    )


@pytest.mark.parametrize(
    "malformata",
    [
        # Senza i due punti
        f"(fonte [D1.13], {ATTO_INCENTIVI})",
        # Parentesi annidate su due livelli: lo schema del verificatore non
        # la riconosce
        "(fonte: [D1.13], decreto 848 (modificato (due volte)))",
        # Parentesi non chiusa
        "(fonte: [D1.13], decreto 848 del 2 novembre 2023",
    ],
)
def test_citazione_malformata_resta_com_e(malformata):
    testo = f"Uno {INCENTIVI}. Due {malformata}. Tre {malformata}."
    assert accorcia_citazioni(testo) == testo


def test_etichette_fuori_dalle_citazioni_restano_com_e():
    # Lotto 1, L03: etichette in testa ai punti di un elenco e nel testo
    testo = (
        "**Bandi a sportello per il sostegno finanziario alle PMI:**\n\n"
        "- [D1.6] «Bando 2026 Pmi: sovvenzioni per abbattere interessi» "
        "(fonte: [D1.6], decreto dirigenziale 9505 del 30 aprile 2026).\n"
        "- [D1.6] di nuovo, a sportello "
        "(fonte: [D1.6], decreto dirigenziale 9505 del 30 aprile 2026).\n\n"
        "La delibera è richiamata nei bandi [D1.7] e [D1.19]."
    )
    assert accorcia_citazioni(testo) == (
        "**Bandi a sportello per il sostegno finanziario alle PMI:**\n\n"
        "- [D1.6] «Bando 2026 Pmi: sovvenzioni per abbattere interessi» "
        "(fonte: [D1.6], decreto dirigenziale 9505 del 30 aprile 2026).\n"
        "- [D1.6] di nuovo, a sportello (fonte: [D1.6]).\n\n"
        "La delibera è richiamata nei bandi [D1.7] e [D1.19]."
    )


def test_profilo_dell_ente_resta_com_e():
    testo = (
        "Il Comune è in area interna (fonte: profilo dell'ente). "
        "È capofila (fonte: profilo dell'ente)."
    )
    assert accorcia_citazioni(testo) == testo


def test_citazione_senza_descrizione_resta_com_e():
    testo = "Uno (fonte: [D1]). Due (fonte: [D1])."
    assert accorcia_citazioni(testo) == testo


def test_testo_prima_di_fonte_nella_parentesi_resta():
    testo = (
        f"A {INCENTIVI}. B (inclusa la lettera c, fonte: [D1.13], {ATTO_INCENTIVI})."
    )
    assert accorcia_citazioni(testo) == (
        f"A {INCENTIVI}. B (inclusa la lettera c, fonte: [D1.13])."
    )


def test_funzione_spenta_il_testo_mostrato_e_quello_del_modello(monkeypatch):
    from streamlit.testing.v1 import AppTest

    import app.app

    # mostra_risposta legge l'interruttore importato da src.config
    monkeypatch.setattr(app.app, "ACCORCIA_CITAZIONI", False)
    testo = f"Uno {INCENTIVI}. Due {INCENTIVI}."
    pagina = AppTest.from_function(
        pagina_risposta, kwargs={"risposta": testo}, default_timeout=30
    )
    pagina.run()
    assert not pagina.exception, pagina.exception
    assert [e.value for e in pagina.markdown] == [testo]


def test_funzione_accesa_il_testo_mostrato_e_accorciato():
    from streamlit.testing.v1 import AppTest

    testo = f"Uno {INCENTIVI}. Due {INCENTIVI}."
    pagina = AppTest.from_function(
        pagina_risposta, kwargs={"risposta": testo}, default_timeout=30
    )
    pagina.run()
    assert not pagina.exception, pagina.exception
    assert [e.value for e in pagina.markdown] == [
        f"Uno {INCENTIVI}. Due (fonte: [D1.13])."
    ]


def pagina_risposta(risposta):
    # AppTest esegue solo il corpo di questa funzione
    from app.app import mostra_risposta

    mostra_risposta({"risposta": risposta})


# --- L'app intera: verificatore e bandi citati ricevono il testo intero ---


class CatenaFinta:
    """Restituisce un esito fisso, senza modello, rete o database."""

    def __init__(self, esito: dict) -> None:
        self.esito = esito

    def invoke(self, _domanda: str) -> dict:
        return dict(self.esito)


class ConnessioneFinta:
    def close(self) -> None:
        pass


def test_verificatore_e_bandi_citati_ricevono_il_testo_intero(monkeypatch):
    from streamlit.testing.v1 import AppTest

    import src.chains.rag
    import src.database.enti
    import src.database.modelli
    import src.database.repertorio
    import src.database.schema
    import src.verification.controllo
    from src.config import ENTE_PREDEFINITO
    from src.database.modelli import Risultato, VoceBando

    voce = VoceBando(
        "«Incentivi ai datori di lavoro privati» (Regione Toscana) | aperto",
        ATTO_INCENTIVI,
        titolo="Incentivi ai datori di lavoro privati",
        url="https://esempio.it/incentivi",
    )
    risultato = Risultato(
        "Bandi aperti (alla data del 2026-11-24), 1 in archivio:\n- [#1] " + voce.testo,
        fonti=[voce.fonte],
        voci=[voce],
    )
    risposta = (
        f"In archivio risulta un bando {INCENTIVI}. "
        f"È sospeso in parte dal 2026-07-08 {INCENTIVI}."
    )
    esito = {
        "domanda": "domanda di prova",
        "risposta": risposta,
        "documenti": [],
        "origini": [],
        "decisione": {"documenti": False, "interrogazioni": []},
        "esiti_dati": [("bandi_aperti_per_ente", risultato)],
        "stop_reason_risposta": "end_turn",
    }

    ricevuti = {"verifica": [], "bandi_citati": []}
    verifica_vera = src.verification.controllo.verifica
    bandi_citati_veri = src.database.modelli.bandi_citati

    def verifica_registrata(testo, *argomenti, **opzioni):
        ricevuti["verifica"].append(testo)
        return verifica_vera(testo, *argomenti, **opzioni)

    def bandi_citati_registrata(testo, *argomenti, **opzioni):
        ricevuti["bandi_citati"].append(testo)
        return bandi_citati_veri(testo, *argomenti, **opzioni)

    # app/app.py si esegue da capo e importa questi nomi dai moduli: si
    # sostituiscono nei moduli. Niente Postgres, niente database vero
    monkeypatch.setenv("USA_POSTGRES", "0")
    monkeypatch.setattr(src.verification.controllo, "verifica", verifica_registrata)
    monkeypatch.setattr(src.database.modelli, "bandi_citati", bandi_citati_registrata)
    monkeypatch.setattr(
        src.chains.rag, "costruisci_catena", lambda *_a, **_o: CatenaFinta(esito)
    )
    monkeypatch.setattr(src.database.schema, "connetti", ConnessioneFinta)
    monkeypatch.setattr(
        src.database.enti, "elenco_enti", lambda _c: [(ENTE_PREDEFINITO, "Ente")]
    )
    monkeypatch.setattr(src.database.repertorio, "stato_archivio", lambda _c: "")

    pagina = AppTest.from_file("../app/app.py", default_timeout=30)
    pagina.run()
    pagina.text_area[0].input("domanda di prova")
    [chiedi] = [b for b in pagina.button if b.label == "Chiedi"]
    chiedi.click().run()
    assert not pagina.exception, pagina.exception

    # Il testo mostrato e' accorciato: la prova riguarda davvero due testi diversi
    mostrati = [e.value for e in pagina.markdown]
    assert f"In archivio risulta un bando {INCENTIVI}. " in "".join(mostrati)
    assert any(t.endswith("dal 2026-07-08 (fonte: [D1.13]).") for t in mostrati)
    # Verificatore e bandi citati hanno ricevuto il testo del modello, intero
    assert ricevuti["verifica"] == [risposta]
    assert ricevuti["bandi_citati"] == [risposta]
