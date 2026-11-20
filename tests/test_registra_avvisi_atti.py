"""Atto dal titolo della prima pagina, per decisione a mano (ritocco del 19c-2).

Usa la cartella di prova di tests/test_registra_avvisi.py.
"""

import pytest

import scripts.ingestione.registra_avvisi as script
from src.estrazione import pdf_bando as pb
from tests.test_pdf_bando import pdf_minimo
from tests.test_registra_avvisi import DATA, URL_CREDITO, archivio  # noqa: F401

PRIMA_PAGINA = [
    "1",
    "ALLEGATO A",
    "Complemento Sviluppo Rurale (CSR) 2023/2027",
    'SRA99-ACA99.B "Recupero e tutela',
    'delle risorse genetiche"',
    "Bando - annualità 2026",
]


def _con_testo_coordinato(archivio, monkeypatch, pezzi):  # noqa: F811
    archivio.aggiungi(
        "bando-f",
        URL_CREDITO.format(nome="testo-coordinato-bando-sra-aca-99b"),
        pb.CONSOLIDATO,
        pdf_minimo([PRIMA_PAGINA, ["altro testo"]]),
    )
    decisione = script.Decisione(
        "testo coordinato",
        pb.CONSOLIDATO,
        script.FRAMMENTI,
        "atto dalla prima pagina",
        "2026-11-20",
        atto_prima_pagina=pezzi,
    )
    decisioni = {**script.DECISIONI_A_MANO, archivio.elenco[-1]["sha256"]: decisione}
    monkeypatch.setattr(script, "DECISIONI_A_MANO", decisioni)
    return archivio.scrivi()


def test_atto_dalla_prima_pagina(archivio, monkeypatch):  # noqa: F811
    pezzi = (
        "Allegato A",
        'SRA99-ACA99.B "Recupero e tutela delle risorse genetiche"',
        "Bando - annualità 2026",
    )
    cartella = _con_testo_coordinato(archivio, monkeypatch, pezzi)
    riga = next(
        r for r in script.costruisci(cartella, DATA) if r["id_bandi"] == "bando-f"
    )
    assert riga["atto"] == (
        'Allegato A, SRA99-ACA99.B "Recupero e tutela delle risorse genetiche", '
        "Bando - annualità 2026"
    )
    assert riga["atto_origine"] == script.DA_PRIMA_PAGINA
    assert riga["deciso_da"] == script.A_MANO
    assert (riga["classe"], riga["uso"]) == (pb.CONSOLIDATO, script.FRAMMENTI)


def test_pezzo_che_non_e_nella_prima_pagina(archivio, monkeypatch):  # noqa: F811
    cartella = _con_testo_coordinato(
        archivio, monkeypatch, ("Allegato A", "Bando 2027")
    )
    with pytest.raises(script.ErroreRegistro, match="non è nella prima pagina"):
        script.costruisci(cartella, DATA)


def test_decisione_del_testo_coordinato_vero():
    decisione = script.DECISIONI_A_MANO[
        "aa0d0bd1b0192161369309f812926f41f9d9d632dab6a829038d17b9bc746bb1"
    ]
    assert decisione.atto_prima_pagina
    assert (decisione.classe, decisione.uso) == (pb.CONSOLIDATO, script.FRAMMENTI)
