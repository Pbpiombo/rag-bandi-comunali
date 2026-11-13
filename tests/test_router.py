"""Test della descrizione del profilo dell'ente per il router."""

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
