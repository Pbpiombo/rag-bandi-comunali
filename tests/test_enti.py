"""test degli funzioni enti.py che estraggono informazioni dalle tabelle"""

import pytest

from src.database.enti import elenco_enti, profilo_ente
from tests.conftest import CON_DATI, SENZA_DATI


def test_profilo_converte_booleani(conn):
    profilo = profilo_ente(conn, CON_DATI)
    assert profilo["capofila_area"] is False


def test_profilo_vuoto_non_verificato(conn):
    profilo = profilo_ente(conn, CON_DATI)
    assert profilo["toscana_diffusa"] is None


def test_ente_inesistente_alza_errore(conn):
    with pytest.raises(ValueError):
        profilo_ente(conn, "00000000000")


def test_elenco_in_ordine_alfabetico(conn):
    assert elenco_enti(conn) == [
        (CON_DATI, "Comune con dati"),
        (SENZA_DATI, "Comune senza dati"),
    ]
