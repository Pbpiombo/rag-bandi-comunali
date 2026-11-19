"""Una pagina HTML al posto del robots.txt vale come robots.txt assente.

Caso reale del 19/11/2026: www301.regione.toscana.it/robots.txt risponde
200 con la pagina "La pagina che hai richiesto non esiste..". Nessuna rete.
"""

import json

import pytest

from src.estrazione import lettore_siti as ls
from tests.test_lettore_siti import ROBOTS, SITO, lettore, registro

PAGINA_ERRORE = (
    "<html>\n<head>\n<TITLE>Regione Toscana | HOME</TITLE>\n</head>\n<body>\n"
    "<center>La pagina che hai richiesto non esiste..</center>\n</body>\n</html>\n"
)


@pytest.mark.parametrize(
    ("testo", "tipo", "atteso"),
    [
        (PAGINA_ERRORE, "", True),
        ("﻿  <!DOCTYPE html><html></html>", "", True),
        ("User-agent: *\nDisallow: /a\n", "text/html; charset=utf-8", True),
        ("User-agent: *\nDisallow: /a\n", "text/plain", False),
        ("# commento <html>\nUser-agent: *\n", "", False),
    ],
)
def test_riconosce_una_pagina_html(testo, tipo, atteso):
    assert ls.pagina_html(testo, tipo) is atteso


def test_pagina_html_si_registra_come_assente(tmp_path):
    let, _, _ = lettore(
        tmp_path, {ROBOTS: (PAGINA_ERRORE.encode(), {"Content-Type": "text/html"})}
    )
    regole = let.regole(SITO)
    assert regole.esito == ls.ASSENTE_HTML
    assert regole.crawl_delay is None
    # permesso come un robots.txt assente
    assert let.consentito(f"{SITO}/bancadati/atti/Contenuto.xml?id=1") is True
    salvato = json.loads(
        (tmp_path / "robots" / "www.sito-di-prova.it.json").read_text(encoding="utf-8")
    )
    assert salvato["esito"] == ls.ASSENTE_HTML
    # il testo arrivato resta, come prova
    assert (tmp_path / "robots" / "www.sito-di-prova.it.txt").read_text(
        encoding="utf-8"
    ) == PAGINA_ERRORE


def test_pagina_html_senza_content_type(tmp_path):
    let, _, _ = lettore(tmp_path, {ROBOTS: PAGINA_ERRORE.encode()})
    assert let.regole(SITO).esito == ls.ASSENTE_HTML


def test_esito_salvato_come_letto_si_corregge_senza_richiesta(tmp_path):
    cartella = tmp_path / "robots"
    cartella.mkdir()
    file_json = cartella / "www.sito-di-prova.it.json"
    file_json.write_text(
        json.dumps(
            {
                "host": "www.sito-di-prova.it",
                "url": ROBOTS,
                "esito": "letto",
                "codice": 200,
                "testo": PAGINA_ERRORE,
                "crawl_delay": None,
            }
        ),
        encoding="utf-8",
    )
    let, rete, _ = lettore(tmp_path, {})
    assert let.regole(SITO).esito == ls.ASSENTE_HTML
    assert rete.chiamate == []
    assert json.loads(file_json.read_text(encoding="utf-8"))["esito"] == ls.ASSENTE_HTML
    scelte = [r for r in registro(tmp_path) if r["tipo"] == "scelta"]
    assert [r["esito"] for r in scelte] == [ls.ASSENTE_HTML]


def test_robots_vero_resta_letto(tmp_path):
    let, _, _ = lettore(
        tmp_path,
        {ROBOTS: (b"User-agent: *\nDisallow: /a\n", {"Content-Type": "text/plain"})},
    )
    assert let.regole(SITO).esito == ls.LETTO
    assert let.consentito(f"{SITO}/a") is False
