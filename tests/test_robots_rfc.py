"""Test del confronto delle regole del robots.txt secondo RFC 9309.

I robots.txt veri in tests/dati/robots sono copiati tali e quali da
dati-grezzi/avvisi/2026-11-19/robots, letti il 19/11/2026 dalla fase
--robots dello script elenco_pdf_bandi. Su questi urllib.robotparser
sbagliava: legge le regole alla lettera ("*" e "$" non sono jolly) e
applica la prima che corrisponde invece della piu' lunga.
"""

import json
from pathlib import Path

import pytest

from src.estrazione import lettore_siti as ls

ROBOTS = Path(__file__).parent / "dati" / "robots"


def regole_di(host: str) -> ls.RegoleRobots:
    return ls.regole_per((ROBOTS / f"{host}.txt").read_text(encoding="utf-8"))


# --- le sei righe della tabella del 19/11/2026, sui robots.txt veri ---


@pytest.mark.parametrize(
    ("host", "url", "atteso"),
    [
        (
            "www.creditosportivo.it",
            "https://www.creditosportivo.it/wp-content/uploads/avviso.pdf",
            False,
        ),
        ("www.creditosportivo.it", "https://www.creditosportivo.it/avviso.PDF", False),
        (
            "www.regione.toscana.it",
            "https://www.regione.toscana.it/qualcosa/search",
            False,
        ),
        (
            "www.regione.toscana.it",
            "https://www.regione.toscana.it/x/asset_publisher/abc",
            False,
        ),
        ("www.mit.gov.it", "https://www.mit.gov.it/it/media/oembed", False),
        ("www.mit.gov.it", "https://www.mit.gov.it/core/x.css", True),
    ],
)
def test_righe_della_tabella_sui_robots_veri(host, url, atteso):
    assert ls.permesso(regole_di(host), url) is atteso


def test_pagine_dei_bandi_consentite_sui_robots_veri():
    pagine = {
        "www.regione.toscana.it": "https://www.regione.toscana.it/-/bando-parcheggi-2026",
        "www.creditosportivo.it": "https://www.creditosportivo.it/fondi-speciali-bandi-cultura-2026",
        "www.mit.gov.it": (
            "https://www.mit.gov.it/comunicazione/news/"
            "fondo-piccoli-comuni-online-lavviso-pubblico-2026"
        ),
        "www.mimit.gov.it": (
            "https://www.mimit.gov.it/it/incentivi/"
            "sostegno-alla-domanda-di-servizi-di-cloud-computing-e-cyber-security"
        ),
    }
    for host, url in pagine.items():
        assert ls.permesso(regole_di(host), url) is True, host


def test_crawl_delay_letto_a_mano_sui_robots_veri():
    assert regole_di("www.creditosportivo.it").crawl_delay == 2.0
    assert regole_di("www.regione.toscana.it").crawl_delay is None


# --- un caso per ogni regola ---


def test_gruppo_per_nome_con_jolly():
    testo = (
        "User-agent: *\nDisallow: /tutti/\n\n"
        "User-agent: rag-bandi-comunali\nDisallow: /*.pdf\n"
    )
    regole = ls.regole_per(testo)
    # vale il gruppo con il nome, con il suo jolly; quello per * no
    assert ls.permesso(regole, "https://x.it/doc/avviso.pdf") is False
    assert ls.permesso(regole, "https://x.it/tutti/pagina") is True


def test_gruppi_per_tutti_uniti():
    testo = (
        "User-agent: *\nDisallow: /a\n\nUser-agent: *\nDisallow: /b\nCrawl-delay: 4\n"
    )
    regole = ls.regole_per(testo)
    assert ls.permesso(regole, "https://x.it/a") is False
    assert ls.permesso(regole, "https://x.it/b") is False
    assert regole.crawl_delay == 4.0


def test_nome_in_un_gruppo_con_piu_nomi():
    testo = "User-agent: altro\nUser-agent: RAG-Bandi-Comunali\nCrawl-delay: 1\nDisallow: /x\n"
    regole = ls.regole_per(testo)
    assert regole.crawl_delay == 1.0
    assert ls.permesso(regole, "https://x.it/x") is False


def test_vince_la_regola_piu_lunga():
    regole = ls.regole_per("User-agent: *\nDisallow: /a\nAllow: /a/b\n")
    assert ls.permesso(regole, "https://x.it/a/b/c") is True
    assert ls.permesso(regole, "https://x.it/a/c") is False


def test_a_parita_vince_allow():
    regole = ls.regole_per("User-agent: *\nDisallow: /pagina\nAllow: /pagina\n")
    assert ls.permesso(regole, "https://x.it/pagina") is True


def test_dollaro_a_fine_percorso():
    regole = ls.regole_per("User-agent: *\nDisallow: /*.pdf$\n")
    assert ls.permesso(regole, "https://x.it/avviso.pdf") is False
    assert ls.permesso(regole, "https://x.it/avviso.pdf?versione=2") is True
    assert ls.permesso(regole, "https://x.it/avviso.pdf/scarica") is True


def test_query_nel_confronto():
    regole = ls.regole_per("User-agent: *\nDisallow: /search?\n")
    assert ls.permesso(regole, "https://x.it/search?q=bandi") is False
    assert ls.permesso(regole, "https://x.it/search") is True


def test_disallow_vuoto_e_commenti():
    regole = ls.regole_per(
        "# commento\nUser-agent: * # tutti\nDisallow:\nSitemap: /s.xml\n"
    )
    assert regole.regole == []
    assert ls.permesso(regole, "https://x.it/qualunque") is True


def test_il_lettore_usa_il_confronto_rfc(tmp_path):
    """Il Lettore interroga con le stesse regole, anche da un robots.txt salvato."""
    cartella = tmp_path / "robots"
    cartella.mkdir()
    testo = (ROBOTS / "www.creditosportivo.it.txt").read_text(encoding="utf-8")
    (cartella / "www.creditosportivo.it.json").write_text(
        '{"host": "www.creditosportivo.it", "url": "https://www.creditosportivo.it/robots.txt",'
        ' "esito": "letto", "codice": 200, "testo": '
        + json.dumps(testo)
        + ', "crawl_delay": 99}',
        encoding="utf-8",
    )

    def nessuna_rete(*_):
        raise AssertionError("richiesta di rete")

    lettore = ls.Lettore(tmp_path, apri=nessuna_rete, dormi=lambda _s: None)
    assert lettore.consentito("https://www.creditosportivo.it/doc/avviso.pdf") is False
    assert lettore.consentito(
        "https://www.creditosportivo.it/fondi-speciali-bandi-sport-2026"
    )
    # il Crawl-delay si rilegge dal testo, non dal valore salvato
    assert lettore.pausa("www.creditosportivo.it") == 2.0
    assert lettore.permesso_noto("https://altro.it/a.pdf") is None


def test_il_lettore_non_applica_l_eccezione_alle_pagine(tmp_path):
    """eccezione_robots vale solo per i file: una pagina vietata non si chiede."""
    chiamate = []

    def rete(url, _intestazioni):
        chiamate.append(url)
        if url.endswith("/robots.txt"):
            return _Risposta(b"User-agent: *\nDisallow: /-/\n")
        raise AssertionError(f"richiesta non prevista: {url}")

    lettore = ls.Lettore(tmp_path, apri=rete, dormi=lambda _s: None)
    esito = lettore.prendi(
        "https://x.it/-/bando", tmp_path / "p.html", "pagina", eccezione_robots=True
    )
    assert esito.stato == ls.VIETATO
    assert chiamate == ["https://x.it/robots.txt"]


class _Risposta:
    def __init__(self, corpo: bytes) -> None:
        self._corpo = [corpo]
        self.headers = {}
        self.status = 200

    def read(self, _quanti=-1) -> bytes:
        return self._corpo.pop() if self._corpo else b""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False
