"""Riclassificazione dei bandi in archivio: fusione con i valori vecchi."""

import sqlite3

from scripts.ingestione.estrai_nuovi import errore_bloccante
from scripts.manutenzione import riclassifica_bandi as rb
from scripts.manutenzione.riclassifica_bandi import (
    SENZA_AVVISO,
    da_riclassificare,
    differenze,
    fondi,
    mantieni_scadenze,
)
from src.estrazione.bandi import interpreta
from src.estrazione.salva import salva, segna_non_bando
from tests.test_estrattore import pagina_salvata, risposta

PRECEDENTE = {
    "id": "bando-prova",
    "titolo": "Bando di prova",
    "dotazione": 500000.0,
    "contributo_perc": 80.0,
    "cumulabilita": "cumulabile",
    "scadenza": "2026-12-31",
    "premialita": None,
}


def test_un_valore_pieno_che_torna_vuoto_resta_e_si_elenca():
    riga = {"titolo": "Bando di prova", "dotazione": None, "contributo_perc": 80.0}
    avvisi = [
        (
            "dotazione: prova del valore '500000.0' non trovata nella pagina "
            "('...'), lasciato vuoto"
        )
    ]

    mantenuti = fondi(PRECEDENTE, riga, avvisi)

    assert riga["dotazione"] == 500000.0
    dotazione = next(m for m in mantenuti if m["colonna"] == "dotazione")
    assert dotazione["vecchio"] == 500000.0
    assert dotazione["motivo"].startswith("dotazione: prova del valore")


def test_senza_avviso_il_motivo_dice_che_il_modello_non_ha_dato_valore():
    riga = {"titolo": "Bando di prova", "contributo_perc": 80.0}

    mantenuti = fondi(PRECEDENTE, riga, [])

    cumulabilita = next(m for m in mantenuti if m["colonna"] == "cumulabilita")
    assert cumulabilita["motivo"] == SENZA_AVVISO
    assert riga["cumulabilita"] == "cumulabile"


def test_un_valore_nuovo_pieno_non_si_tocca_e_un_vecchio_vuoto_non_si_elenca():
    riga = {
        "titolo": "Bando di prova",
        "dotazione": 600000.0,
        "contributo_perc": 80.0,
        "cumulabilita": "non cumulabile",
        "scadenza": "2027-01-31",
    }

    mantenuti = fondi(PRECEDENTE, riga, [])

    assert mantenuti == []
    assert riga["dotazione"] == 600000.0
    assert riga.get("premialita") is None


def test_differenze_elenca_solo_i_valori_pieni_cambiati():
    riga = {
        "titolo": "Bando di prova",
        "dotazione": 600000.0,
        "contributo_perc": 80.0,
        "scadenza": None,
    }

    assert differenze(PRECEDENTE, riga) == [("dotazione", 500000.0, 600000.0)]


def test_da_riclassificare_prende_solo_i_bandi_non_classificati(db_su_file):
    base = {
        "titolo": "Bando",
        "ente": "Regione Toscana",
        "beneficiari": "Comuni",
        "a_sportello": 0,
    }
    salva(
        {**base, "id": "vecchio"},
        "https://www.regione.toscana.it/-/vecchio",
        "x",
        "regione-toscana",
    )
    salva(
        {**base, "id": "nuovo", "beneficiari_ammessi": []},
        "https://www.regione.toscana.it/-/nuovo",
        "x",
        "regione-toscana",
    )

    assert [b["id"] for b in da_riclassificare()] == ["vecchio"]


def test_credito_esaurito_e_autenticazione_fermano_la_corsa():
    credito = ValueError(
        "Error code: 400 - Your credit balance is too low to access the API"
    )
    assert errore_bloccante(credito)
    assert errore_bloccante(RuntimeError("authentication_error: invalid x-api-key"))


def test_un_errore_della_pagina_non_ferma_la_corsa():
    assert not errore_bloccante(ValueError("Risposta non interpretabile come JSON"))
    assert not errore_bloccante(OSError("HTTP Error 404: Not Found"))


def _leggi(percorso, sql):
    c = sqlite3.connect(percorso)
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def test_segna_non_bando_lo_toglie_dai_da_riclassificare(db_su_file):
    base = {
        "titolo": "Bando",
        "ente": "Regione Toscana",
        "beneficiari": "Comuni",
        "a_sportello": 0,
    }
    salva(
        {**base, "id": "graduatoria"},
        "https://www.regione.toscana.it/-/graduatoria",
        "x",
        "regione-toscana",
    )

    assert segna_non_bando("graduatoria", "graduatoria di un bando chiuso")
    assert not segna_non_bando("inesistente", "motivo")

    righe = _leggi(
        db_su_file,
        "SELECT natura, natura_motivo, classificato_il IS NOT NULL FROM bandi",
    )
    assert righe == [("non_bando", "graduatoria di un bando chiuso", 1)]
    assert da_riclassificare() == []


def test_salvare_come_bando_toglie_il_segno_di_non_bando(db_su_file):
    riga = {
        "id": "pagina",
        "titolo": "Bando",
        "ente": "Regione Toscana",
        "beneficiari": "Comuni",
        "a_sportello": 0,
    }
    url = "https://www.regione.toscana.it/-/pagina"
    salva(riga, url, "x", "regione-toscana")
    segna_non_bando("pagina", "graduatoria")

    salva(riga, url, "x", "regione-toscana")

    righe = _leggi(db_su_file, "SELECT natura, natura_motivo FROM bandi")
    assert righe == [("bando", None)]


# --- date di scadenze_bando ---

DATE_VECCHIE = [
    {
        "numero": 1,
        "genere": "domanda",
        "descrizione": "prima finestra",
        "apertura": None,
        "scadenza": "2021-10-21",
        "frase": "frase uno",
    },
    {
        "numero": 2,
        "genere": "domanda",
        "descrizione": "seconda finestra",
        "apertura": "2022-03-01",
        "scadenza": "2022-03-31",
        "frase": "frase due",
    },
]


def test_date_nuove_presenti_le_vecchie_non_si_toccano():
    nuove = [{**DATE_VECCHIE[0], "descrizione": "nuova"}]
    riga = {"scadenza": "2021-10-21", "scadenze": nuove}

    assert mantieni_scadenze(DATE_VECCHIE, riga, []) is None
    assert riga["scadenze"] == nuove


def test_riclassifica_tiene_le_date_vecchie_se_le_nuove_sono_vuote(
    db_su_file, monkeypatch
):
    url = "https://www.regione.toscana.it/-/tpl"
    salva(
        {
            "id": "tpl",
            "titolo": "TPL",
            "ente": "Regione Toscana",
            "beneficiari": "Enti locali competenti.",
            "a_sportello": 0,
            "scadenza": "2022-03-31",
            "scadenze": DATE_VECCHIE,
        },
        url,
        "x",
        "regione-toscana",
    )
    # la nuova estrazione e' quella della pagina salvata: una sola data
    monkeypatch.setattr(rb, "prendi", lambda _: pagina_salvata("tpl"))
    monkeypatch.setattr(rb, "estrai", lambda _e, _t: interpreta(risposta("tpl")))
    (precedente,) = rb.da_riclassificare()

    esito = rb.riclassifica(None, precedente)

    assert esito["esito"] == "salvato"
    assert _leggi(
        db_su_file, "SELECT numero, scadenza FROM scadenze_bando ORDER BY numero"
    ) == [(1, "2021-10-21"), (2, "2022-03-31")]
    # la scadenza del bando resta l'ultima delle date mantenute
    assert _leggi(db_su_file, "SELECT scadenza FROM bandi") == [("2022-03-31",)]
    (date,) = [m for m in esito["mantenuti"] if m["colonna"] == "scadenze_bando"]
    assert date["vecchio"] == "prima finestra 2021-10-21; seconda finestra 2022-03-31"
    assert date["motivo"] == SENZA_AVVISO


# --- riestrazione di bandi indicati ---


def test_ids_richiesti_con_id_ripetibile():
    argomenti = ["prog", "--id", "a", "--prova", "--id", "b", "--id"]
    assert rb.ids_richiesti(argomenti) == ["a", "b"]
    assert rb.ids_richiesti(["prog", "--id", "--prova"]) == []


def test_da_riestrarre_prende_anche_i_classificati(db_su_file):
    base = {
        "titolo": "Bando",
        "ente": "Regione Toscana",
        "beneficiari": "Comuni",
        "a_sportello": 0,
    }
    salva(
        {**base, "id": "classificato", "beneficiari_ammessi": []},
        "https://www.regione.toscana.it/-/classificato",
        "x",
        "regione-toscana",
    )
    salva(
        {**base, "id": "vecchio"},
        "https://www.regione.toscana.it/-/vecchio",
        "x",
        "regione-toscana",
    )

    trovati, mancanti = rb.da_riestrarre(
        ["classificato", "inesistente", "classificato"]
    )

    assert [b["id"] for b in trovati] == ["classificato"]
    assert mancanti == ["inesistente"]
