"""Tre correzioni alla pagina dell'app (25/11/2026).

1. Un errore del servizio del modello o del database dei documenti mostra
   una riga breve, senza traceback; ogni altro errore continua a emergere.
2. Sotto "Bandi citati" lo stato "sospeso" preso dal database, alla data di
   oggi, anche se la risposta non nomina la sospensione.
3. Pannello della verifica: le date di un intervallo rosso solo nella sua
   riga; messaggio arancione al singolare e al plurale; tipi in parole.

Senza modello, rete, Postgres o database vero: catena finta, database in
memoria di conftest o su file temporaneo (db_su_file).
"""

import logging
import sqlite3
from datetime import date

import anthropic
import httpx
import psycopg
import pytest
from streamlit.testing.v1 import AppTest

from src.database import interrogazioni_bandi as ib
from tests.test_citazioni import CatenaFinta, ConnessioneFinta
from tests.test_interrogazioni_bandi import BASE, bando
from tests.test_sospensioni import sospendi

OGGI = "2026-11-25"

# --- 1. Errore tecnico mostrato all'utente ---

_RICHIESTA = httpx.Request("POST", "https://api.anthropic.com/v1/messages")


def _stato(codice: int) -> httpx.Response:
    return httpx.Response(codice, request=_RICHIESTA)


ERRORI = {
    "autenticazione": anthropic.AuthenticationError(
        "dettaglio interno 1", response=_stato(401), body=None
    ),
    "limite di richieste": anthropic.RateLimitError(
        "dettaglio interno 2", response=_stato(429), body=None
    ),
    "connessione": anthropic.APIConnectionError(request=_RICHIESTA),
    "tempo scaduto": anthropic.APITimeoutError(request=_RICHIESTA),
    "errore interno": anthropic.InternalServerError(
        "dettaglio interno 3", response=_stato(500), body=None
    ),
    "sovraccarico": anthropic.OverloadedError(
        "dettaglio interno 4", response=_stato(529), body=None
    ),
    "non disponibile": anthropic.ServiceUnavailableError(
        "dettaglio interno 5", response=_stato(503), body=None
    ),
    "database dei documenti": psycopg.OperationalError("dettaglio interno 6"),
}


class CatenaCheFallisce:
    def __init__(self, errore: Exception) -> None:
        self.errore = errore

    def invoke(self, _domanda: str) -> dict:
        raise self.errore


def app_con_catena(monkeypatch, catena) -> AppTest:
    """L'app intera, con la domanda inviata; come in test_citazioni."""
    import streamlit as st

    import src.chains.rag
    import src.database.enti
    import src.database.repertorio
    import src.database.schema
    from src.config import ENTE_PREDEFINITO

    # carica_catena e' in cache_resource: ogni test la sua catena finta
    st.cache_resource.clear()
    monkeypatch.setenv("USA_POSTGRES", "0")
    monkeypatch.setattr(src.chains.rag, "costruisci_catena", lambda *_a, **_o: catena)
    monkeypatch.setattr(src.database.schema, "connetti", ConnessioneFinta)
    monkeypatch.setattr(
        src.database.enti, "elenco_enti", lambda _c: [(ENTE_PREDEFINITO, "Ente")]
    )
    monkeypatch.setattr(src.database.repertorio, "stato_archivio", lambda _c: "")

    pagina = AppTest.from_file("../app/app.py", default_timeout=30)
    pagina.run()
    pagina.text_area[0].input("domanda riservata dell'utente")
    [chiedi] = [b for b in pagina.button if b.label == "Chiedi"]
    chiedi.click().run()
    return pagina


@pytest.mark.parametrize("errore", ERRORI.values(), ids=ERRORI.keys())
def test_un_errore_del_servizio_mostra_una_riga_breve(monkeypatch, caplog, errore):
    from app.app import MESSAGGIO_SERVIZIO

    with caplog.at_level(logging.ERROR, logger="app"):
        pagina = app_con_catena(monkeypatch, CatenaCheFallisce(errore))

    assert not pagina.exception, pagina.exception
    assert [e.value for e in pagina.error] == [MESSAGGIO_SERVIZIO]
    # Nessun dettaglio tecnico nella pagina
    testi = " ".join(
        str(e.value) for e in [*pagina.markdown, *pagina.caption, *pagina.error]
    )
    assert "Traceback" not in testi
    assert type(errore).__name__ not in testi
    # Nel log il tipo, non la domanda ne' il testo dell'errore
    registro = " ".join(r.getMessage() for r in caplog.records if r.name == "app")
    assert type(errore).__name__ in registro
    assert "domanda riservata" not in registro
    assert str(errore) not in registro


@pytest.mark.parametrize(
    "errore",
    [
        ValueError("errore di programmazione"),
        KeyError("risposta"),
        anthropic.BadRequestError(
            "richiesta mal formata", response=_stato(400), body=None
        ),
    ],
    ids=["ValueError", "KeyError", "BadRequestError"],
)
def test_un_errore_di_altro_tipo_non_viene_catturato(monkeypatch, errore):
    from app.app import MESSAGGIO_SERVIZIO

    pagina = app_con_catena(monkeypatch, CatenaCheFallisce(errore))

    assert pagina.exception
    assert MESSAGGIO_SERVIZIO not in [e.value for e in pagina.error]


def test_una_risposta_normale_non_mostra_il_messaggio(monkeypatch):
    from app.app import MESSAGGIO_SERVIZIO

    esito = {
        "domanda": "domanda",
        "risposta": "Non trovo la risposta nei documenti disponibili.",
        "documenti": [],
        "origini": [],
        "decisione": {"documenti": False, "interrogazioni": []},
        "esiti_dati": [],
        "stop_reason_risposta": "end_turn",
    }
    pagina = app_con_catena(monkeypatch, CatenaFinta(esito))

    assert not pagina.exception, pagina.exception
    assert MESSAGGIO_SERVIZIO not in [e.value for e in pagina.error]


# --- 2. "Sospeso" accanto ai bandi citati ---


@pytest.fixture
def db(conn):
    conn.execute(
        "INSERT INTO fonti (codice, nome, url_base, schema_link, fonte, "
        "verificato_il) VALUES ('regione-toscana', 'Toscana', ?, '^/-/', 'prova', "
        "'2026-11-11')",
        (BASE,),
    )
    return conn


def test_bando_sospeso_in_parte(db):
    from app.app import stato_sospensione

    bando(db, "incentivi")
    sospendi(db, "incentivi", ambito="in_parte", dal="2026-07-08")

    assert stato_sospensione(db, BASE + "incentivi", OGGI) == (
        "sospeso in parte dall'8 luglio 2026"
    )


def test_bando_sospeso_del_tutto(db):
    from app.app import stato_sospensione

    bando(db, "fermo")
    sospendi(db, "fermo", ambito="tutto", dal="2026-07-01")

    assert stato_sospensione(db, BASE + "fermo", OGGI) == "sospeso dal 1° luglio 2026"


def test_una_sospensione_totale_vale_piu_di_una_parziale(db):
    from app.app import stato_sospensione

    bando(db, "due")
    sospendi(db, "due", ambito="in_parte", dal="2026-07-08", numero=1)
    sospendi(db, "due", ambito="tutto", dal="2026-09-15", numero=2)

    assert stato_sospensione(db, BASE + "due", OGGI) == "sospeso dal 15 settembre 2026"


def test_bando_non_sospeso(db):
    from app.app import stato_sospensione

    bando(db, "aperto")

    assert stato_sospensione(db, BASE + "aperto", OGGI) is None
    assert stato_sospensione(db, BASE + "non-in-archivio", OGGI) is None


def test_sospensione_con_data_futura(db):
    from app.app import stato_sospensione

    bando(db, "futuro")
    sospendi(db, "futuro", dal="2026-12-01")

    assert stato_sospensione(db, BASE + "futuro", OGGI) is None


def test_sospensione_gia_riaperta(db):
    from app.app import stato_sospensione

    bando(db, "riaperto")
    sospendi(
        db,
        "riaperto",
        dal="2026-07-08",
        riaperto_il="2026-10-01",
        riapertura_frase="Il bando riapre il 1 ottobre 2026",
    )

    assert stato_sospensione(db, BASE + "riaperto", OGGI) is None
    # Il giorno prima della riapertura era ancora sospeso
    assert stato_sospensione(db, BASE + "riaperto", "2026-09-30") == (
        "sospeso dall'8 luglio 2026"
    )


@pytest.mark.parametrize(
    ("iso", "testo"),
    [
        ("2026-07-08", "dall'8 luglio 2026"),
        ("2026-11-11", "dall'11 novembre 2026"),
        ("2026-07-01", "dal 1° luglio 2026"),
        ("2026-03-15", "dal 15 marzo 2026"),
    ],
)
def test_data_in_italiano(iso, testo):
    from app.app import dal_in_italiano

    assert dal_in_italiano(iso) == testo


def pagina_bandi_citati(risposta):
    # AppTest esegue solo il corpo di questa funzione
    from app.app import mostra_bandi_citati
    from src.database.modelli import Risultato, VoceBando

    base = "https://www.regione.toscana.it/-/"
    voci = [
        VoceBando(
            "riga",
            "fonte",
            titolo="Incentivi ai datori di lavoro",
            url=base + "incentivi",
        ),
        VoceBando(
            "riga", "fonte", titolo="Bando parcheggi 2026", url=base + "parcheggi"
        ),
    ]
    mostra_bandi_citati(
        {
            "risposta": risposta,
            "esiti_dati": [("bandi_aperti_per_ente", Risultato("elenco", voci=voci))],
        }
    )


def test_bandi_citati_con_un_bando_sospeso_e_uno_no(db_su_file, monkeypatch):
    c = sqlite3.connect(db_su_file)
    c.execute("PRAGMA foreign_keys = ON")
    bando(c, "incentivi", titolo="Incentivi ai datori di lavoro")
    bando(c, "parcheggi", titolo="Bando parcheggi 2026")
    sospendi(c, "incentivi", ambito="in_parte", dal="2026-07-08")
    c.commit()
    c.close()
    monkeypatch.setattr(ib, "_DATA_FISSA", date(2026, 11, 25))

    # La risposta non nomina la sospensione
    risposta = "Incentivi (fonte: [D1.1], decreto). Parcheggi (fonte: [D1.2], decreto)."
    pagina = AppTest.from_function(
        pagina_bandi_citati, kwargs={"risposta": risposta}, default_timeout=30
    )
    pagina.run()
    assert not pagina.exception, pagina.exception

    assert [e.value for e in pagina.markdown] == [
        "#### Bandi citati",
        (
            "- [Incentivi ai datori di lavoro](<https://www.regione.toscana.it/-/incentivi>)"
            " · sospeso in parte dall'8 luglio 2026"
        ),
        "- [Bando parcheggi 2026](<https://www.regione.toscana.it/-/parcheggi>)",
    ]


# --- 3. Pannello della verifica ---


def pagina_verifica(risposta):
    # AppTest esegue solo il corpo di questa funzione
    from app.app import mostra_verifica
    from src.database.modelli import Risultato, VoceBando

    voce = VoceBando(
        "«Incentivi» (Regione Toscana) | finestre: dal 2026-01-11 al 2027-01-10; "
        "dal 2027-01-11 al 2028-01-10 | contributo 5.000 euro",
        "Portale, decreto dirigenziale n. 18191 (dati estratti il 2026-11-11)",
        titolo="Incentivi",
        url="https://esempio.it/i",
    )
    risultato = Risultato(
        f"Bandi aperti (alla data del 2026-11-11), 1 in archivio:\n- [#1] {voce.testo}",
        fonti=[voce.fonte],
        voci=[voce],
    )
    mostra_verifica(
        {
            "risposta": risposta,
            "documenti": [],
            "esiti_dati": [("bandi_aperti_per_ente", risultato)],
        }
    )


def esegui(risposta) -> AppTest:
    pagina = AppTest.from_function(
        pagina_verifica, kwargs={"risposta": risposta}, default_timeout=30
    )
    pagina.run()
    assert not pagina.exception, pagina.exception
    return pagina


CITA = "(fonte: [D1.1], decreto dirigenziale n. 18191)"


def test_le_date_di_un_intervallo_rosso_restano_solo_nella_sua_riga():
    from app.app import raggruppa_esiti
    from src.verification.controllo import verifica

    risposta = (
        f"La finestra successiva va dal 2027-01-11 al 2027-01-10 {CITA}. "
        f"Il contributo è di 5.000 euro {CITA}."
    )
    pagina = esegui(risposta)

    # Il verificatore resta com'e': le due date sono presenti una per una
    esiti = [e for e, _ in raggruppa_esiti(verifica(risposta, [], dati_incentivi()))]
    presenti_grezzi = {e.valore for e in esiti if e.stato == "verificato"}
    assert {"2027-01-11", "2027-01-10", "5.000", "18191"} <= presenti_grezzi

    [rosso] = [e.value for e in pagina.error]
    assert rosso.startswith("1 dato citato non è stato trovato")
    righe = [e.value for e in pagina.markdown]
    assert any("(intervallo di date)" in r and r.startswith(":red[") for r in righe)
    # Le due date non compaiono tra i presenti, ne' altrove come righe proprie
    assert not any("**2027-01-11**" in r or "**2027-01-10**" in r for r in righe)
    # Il conteggio dei presenti e' quello delle righe mostrate
    [presenti] = pagina.expander
    mostrati = [m.value for m in presenti.markdown]
    assert presenti.label == "2 dati presenti nella fonte citata"
    assert len(mostrati) == 2
    assert any("**5.000**" in r for r in mostrati)
    assert any("**18191**" in r for r in mostrati)


def test_la_stessa_data_scritta_altrove_resta_tra_i_presenti():
    risposta = (
        f"La finestra successiva va dal 2027-01-11 al 2027-01-10 {CITA}. "
        f"La prima finestra chiude il 2027-01-10 {CITA}."
    )
    pagina = esegui(risposta)

    [presenti] = pagina.expander
    mostrati = [m.value for m in presenti.markdown]
    assert presenti.label == "2 dati presenti nella fonte citata"
    assert any("**2027-01-10**" in r and "chiude il" in r for r in mostrati)
    assert not any("**2027-01-11**" in r for r in mostrati)


def dati_incentivi():
    # Gli stessi dati di pagina_verifica, per chiamare il verificatore fuori dalla pagina
    from src.database.modelli import Risultato, VoceBando

    voce = VoceBando(
        "«Incentivi» (Regione Toscana) | finestre: dal 2026-01-11 al 2027-01-10; "
        "dal 2027-01-11 al 2028-01-10 | contributo 5.000 euro",
        "Portale, decreto dirigenziale n. 18191 (dati estratti il 2026-11-11)",
        titolo="Incentivi",
        url="https://esempio.it/i",
    )
    risultato = Risultato(
        f"Bandi aperti (alla data del 2026-11-11), 1 in archivio:\n- [#1] {voce.testo}",
        fonti=[voce.fonte],
        voci=[voce],
    )
    return [("bandi_aperti_per_ente", risultato)]


def test_messaggio_arancione_al_singolare():
    pagina = esegui(f"La finestra apre il 2026-01-11 {CITA}. Servono 12 mesi.")

    [arancione] = [e.value for e in pagina.warning]
    assert "1 dato senza fonte" in arancione
    assert "/i" not in arancione


def test_messaggio_arancione_al_plurale():
    pagina = esegui(
        f"La finestra apre il 2026-01-11 {CITA}. Servono 12 mesi e 30 giorni."
    )

    [arancione] = [e.value for e in pagina.warning]
    assert "2 dati senza fonte" in arancione
    assert "/i" not in arancione


@pytest.mark.parametrize(
    ("grezzo", "mostrato"),
    [
        ("1 dato/i senza fonte", "1 dato senza fonte"),
        ("3 dato/i senza fonte", "3 dati senza fonte"),
        ("1 citato/i con il blocco", "1 citato con il blocco"),
        ("2 citato/i con il blocco", "2 citati con il blocco"),
        (
            "Nessun dato presente nella fonte oltre agli anni, 3 dato/i",
            "Nessun dato presente nella fonte oltre agli anni, 3 dati",
        ),
    ],
)
def test_singolare_o_plurale(grezzo, mostrato):
    from app.app import singolare_o_plurale

    assert singolare_o_plurale(grezzo) == mostrato


def test_i_tipi_in_parole_per_l_utente():
    from app.app import ETICHETTE_TIPI, riga_esito
    from src.verification.controllo import Esito

    assert ETICHETTE_TIPI["quantita"] == "numero"
    assert ETICHETTE_TIPI["intervallo"] == "intervallo di date"
    riga = riga_esito(Esito("quantita", "57", ["D1.1"], "verificato"), {})
    assert riga == "✓  **57**  (numero) → fonti D1.1"
    # Un tipo senza etichetta resta con il suo nome
    assert "(letterale)" in riga_esito(
        Esito("letterale", "21/27", [], "verificato"), {}
    )
