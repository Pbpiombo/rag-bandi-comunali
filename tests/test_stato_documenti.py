"""Stato del bando nei frammenti documentali (P3): calcolo, collegamento,
intestazione, prompt e verificatore.

Database in memoria di conftest; la data è passata come argomento.
"""

import pytest
from langchain_core.documents import Document

from src.chains.rag import ISTRUZIONI, etichetta
from src.database.stato_documenti import (
    bando_del_documento,
    con_stato_bando,
    stato_bando,
)
from src.verification.controllo import riassumi, verifica
from tests.test_interrogazioni_bandi import BASE, bando

OGGI = "2026-11-12"


@pytest.fixture
def db(conn):
    conn.execute(
        "INSERT INTO fonti (codice, nome, url_base, schema_link, fonte, "
        "verificato_il) VALUES ('regione-toscana', 'Toscana', ?, '^/-/', 'prova', "
        "'2026-11-11')",
        (BASE,),
    )
    return conn


def riga(db, id_bando):
    return db.execute("SELECT * FROM bandi WHERE id = ?", (id_bando,)).fetchone()


def frammento(**metadati) -> Document:
    return Document(
        page_content="Il contributo concedibile è pari a non più dell'80%.",
        metadata={"ente": "Regione Toscana", "page": 7, **metadati},
    )


# --- stato del bando ----------------------------------------------------------


def test_scaduto(db):
    bando(db, "mercati", scadenza="2026-10-15")
    assert stato_bando(riga(db, "mercati"), [], OGGI) == "scaduto il 2026-10-15"


def test_aperto_con_i_giorni_mancanti(db):
    bando(db, "parcheggi", scadenza="2026-11-30")
    assert (
        stato_bando(riga(db, "parcheggi"), [], OGGI)
        == "aperto, scade il 2026-11-30 (fra 18 giorni)"
    )


def test_scade_oggi_e_ancora_aperto(db):
    bando(db, "oggi", scadenza=OGGI)
    assert stato_bando(riga(db, "oggi"), [], OGGI) == f"aperto, scade il {OGGI} (oggi)"


def test_sportello_aperto_e_sportello_con_chiusura_passata(db):
    bando(db, "sportello", scadenza="2027-07-18", a_sportello=1)
    assert stato_bando(riga(db, "sportello"), [], OGGI).startswith(
        "a sportello fino al 2027-07-18"
    )
    bando(db, "chiuso", scadenza="2026-01-31", a_sportello=1)
    assert stato_bando(riga(db, "chiuso"), [], OGGI) == "scaduto il 2026-01-31"


def test_senza_scadenza(db):
    bando(db, "senza", scadenza=None)
    assert stato_bando(riga(db, "senza"), [], OGGI) == (
        "scadenza non indicata, da verificare sul bando"
    )


def test_bando_a_piu_date_segue_le_finestre(db):
    bando(db, "finestre", scadenza="2027-06-30")
    db.execute(
        "INSERT INTO scadenze_bando (id_bando, numero, genere, descrizione, "
        "apertura, scadenza, frase) VALUES ('finestre', 1, 'domanda', "
        "'prima finestra', '2026-11-01', '2026-11-30', 'frase')"
    )
    documenti = con_stato_bando([frammento(id_bando="finestre")], db, OGGI)
    assert (
        documenti[0]
        .metadata["stato_bando"]
        .startswith(
            "finestra aperta fino al 2026-11-30 (prima finestra, fra 18 giorni)"
        )
    )


# --- collegamento del documento al bando ---------------------------------------

ATTO_MERCATI = (
    "decreto dirigenziale 13287 del 10 giugno 2026, modificato con decreto "
    "dirigenziale 20141 del 11 settembre 2026"
)


def test_collegato_da_id_bando(db):
    bando(db, "mercati", scadenza="2026-10-15")
    assert bando_del_documento(db, {"id_bando": "mercati"})["id"] == "mercati"


def test_id_bando_assente_in_archivio(db):
    assert bando_del_documento(db, {"id_bando": "non-esiste"}) is None


def test_collegato_dall_atto_con_numero_e_data(db):
    bando(db, "mercati", riferimento_atto=ATTO_MERCATI)
    metadati = {"riferimento_atto": "Decreto dirigenziale n. 13287 del 10/06/2026"}
    assert bando_del_documento(db, metadati)["id"] == "mercati"


def test_stesso_numero_con_altra_data_non_collega(db):
    bando(db, "mercati", riferimento_atto=ATTO_MERCATI)
    metadati = {"riferimento_atto": "Decreto dirigenziale n. 13287 del 10/06/2025"}
    assert bando_del_documento(db, metadati) is None


def test_atto_senza_data_non_collega(db):
    bando(db, "mercati", riferimento_atto=ATTO_MERCATI)
    assert bando_del_documento(db, {"riferimento_atto": "Decreto n. 13287"}) is None


def test_due_bandi_con_lo_stesso_atto_non_collegano(db):
    bando(db, "lotto-1", riferimento_atto="decreto n. 500 del 01/02/2026, lotto 1")
    bando(db, "lotto-2", riferimento_atto="decreto n. 500 del 01/02/2026, lotto 2")
    metadati = {"riferimento_atto": "Decreto n. 500 del 01/02/2026"}
    assert bando_del_documento(db, metadati) is None


def test_non_bando_non_ha_stato(db):
    bando(db, "pagina", natura="non_bando", natura_motivo="pagina informativa")
    assert bando_del_documento(db, {"id_bando": "pagina"}) is None


# --- copie dei documenti ------------------------------------------------------


def test_con_stato_bando_non_tocca_gli_originali(db):
    bando(db, "mercati", scadenza="2026-10-15")
    originale = frammento(id_bando="mercati")
    senza_bando = frammento(riferimento_atto="Decreto n. 9550 del 28/04/2026")

    documenti = con_stato_bando([originale, senza_bando], db, OGGI)

    assert documenti[0].metadata["stato_bando"] == (
        "scaduto il 2026-10-15 (alla data del 2026-11-12)"
    )
    assert "stato_bando" not in originale.metadata
    assert documenti[1] is senza_bando


# --- intestazione, prompt e verificatore --------------------------------------


def test_intestazione_con_lo_stato():
    documento = frammento(
        riferimento_atto="Decreto n. 13287 del 10/06/2026",
        stato_bando="scaduto il 2026-10-15 (alla data del 2026-11-12)",
    )
    assert etichetta(documento, 3).endswith(
        "| stato del bando: scaduto il 2026-10-15 (alla data del 2026-11-12)"
    )
    assert "stato del bando" not in etichetta(frammento(), 3)


def test_regola_nel_prompt():
    assert "STATO DEL BANDO NEI FRAMMENTI" in ISTRUZIONI
    assert "Un bando scaduto non si presenta come opportunità" in ISTRUZIONI


RISPOSTA_SCADUTO = (
    "Il bando è scaduto il 15/10/2026 (fonte: [1], Regione Toscana, pag. 7)."
)


def test_verificatore_trova_la_data_dello_stato():
    documento = frammento(
        stato_bando="scaduto il 2026-10-15 (alla data del 2026-11-12)"
    )
    assert riassumi(verifica(RISPOSTA_SCADUTO, [documento])) == {
        "verificato": 1,
        "non_trovato": 0,
        "non_citato": 0,
    }


def test_verificatore_senza_stato_la_data_non_ce():
    assert riassumi(verifica(RISPOSTA_SCADUTO, [frammento()])) == {
        "verificato": 0,
        "non_trovato": 1,
        "non_citato": 0,
    }


def test_verificatore_data_sbagliata_dello_stato():
    documento = frammento(
        stato_bando="scaduto il 2026-10-15 (alla data del 2026-11-12)"
    )
    risposta = RISPOSTA_SCADUTO.replace("15/10/2026", "15/09/2026")
    assert riassumi(verifica(risposta, [documento]))["non_trovato"] == 1
