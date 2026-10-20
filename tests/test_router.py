"""Test della descrizione del profilo dell'ente per il router."""

import pytest

from src.chains.router import descrivi_profilo


def test_booleani_diventano_si_e_no(monkeypatch):
    monkeypatch.setattr(
        "src.chains.router.PROFILO_ENTE",
        {"capofila_area": False, "toscana_diffusa": True},
    )
    testo = descrivi_profilo()
    assert "- capofila_area: no" in testo
    assert "- toscana_diffusa: sì" in testo


def test_valore_mancante_diventa_non_verificato(monkeypatch):
    monkeypatch.setattr(
        "src.chains.router.PROFILO_ENTE",
        {"toscana_diffusa": None},
    )
    testo = descrivi_profilo()
    assert "- toscana_diffusa: non verificato" in testo


def test_testo_resta_invariato(monkeypatch):
    monkeypatch.setattr(
        "src.chains.router.PROFILO_ENTE",
        {"regione": "Toscana"}
    )
    testo=descrivi_profilo()
    assert "- regione: Toscana" in testo


@pytest.mark.xfail(strict=True)
def test_uno_e_zero_diventano_si_no(monkeypatch):
    monkeypatch.setattr(
        "src.chains.router.PROFILO_ENTE",
        {"capofila_area": 0, "toscana_diffusa": 1},
    )
    testo = descrivi_profilo()
    assert "- capofila_area: no" in testo
    assert "- toscana_diffusa: sì" in testo
