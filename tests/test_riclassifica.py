"""Riclassificazione dei bandi in archivio: fusione con i valori vecchi."""

from scripts.ingestione.estrai_nuovi import errore_bloccante
from scripts.manutenzione.riclassifica_bandi import (
    SENZA_AVVISO,
    da_riclassificare,
    differenze,
    fondi,
)
from src.estrazione.salva import salva

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
