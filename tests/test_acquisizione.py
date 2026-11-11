"""Registro delle scansioni, salvataggio dei bandi e lettura dell'elenco,
con gli URL in forma canonica."""

import importlib
import re
import sqlite3
import sys

import pytest

import scripts.ingestione.scopri_bandi as scopri_bandi
from src.estrazione import elenco
from src.estrazione.registro import da_non_riesaminare, registra
from src.estrazione.salva import ConflittoBando, conflitto, salva

TOSCANA = "regione-toscana"
BASE = "https://www.regione.toscana.it"
FONTE = "Portale bandi Regione Toscana"

# Estratto dell'elenco del portale, con i link nella forma reale: slug
# con "/", con ".", con caratteri codificati (%C3%A0, %C2%A0), un link
# ripetuto, una voce di servizio da escludere.
ELENCO_SALVATO = """
<a href="https://www.regione.toscana.it/-/bando-parcheggi-2026">Parcheggi</a>
<a href="https://www.regione.toscana.it/-/avviso-pubblico-per-il-sostegno-allo-sport-per-l-annualit%C3%A0-2022">Sport</a>
<a href="https://www.regione.toscana.it/-/selezione-per%C2%A0dirigente-medico-disciplina-ortopedia">Selezione</a>
<a href="https://www.regione.toscana.it/-/manifestazione-di-interesse-per-il-reperimento-di-patrimonio-immobiliare-da-destinare-ad-emergenza-abitativa-e/o-residenza-sociale-1">Emergenza</a>
<a href="https://www.regione.toscana.it/-/presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo">Museo</a>
<a href="https://www.regione.toscana.it/-/presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo-2024">Museo 2024</a>
<a href="https://www.regione.toscana.it/-/bando-legalita-scuole-a.s.-2025-26">Legalita</a>
<a href="https://www.regione.toscana.it/-/bando-parcheggi-2026">Parcheggi, di nuovo</a>
<a href="https://www.regione.toscana.it/-/accessibilita-e-uso-del-sito">Accessibilita</a>
"""


def _leggi(percorso, sql: str, parametri=()) -> list[sqlite3.Row]:
    c = sqlite3.connect(percorso)
    c.row_factory = sqlite3.Row
    try:
        return c.execute(sql, parametri).fetchall()
    finally:
        c.close()


def _riga(titolo: str = "Bando di prova") -> dict:
    return {
        "titolo": titolo,
        "ente": "Regione Toscana",
        "ammette_comuni": 1,
        "a_sportello": 0,
        "beneficiari": "Comuni",
    }


def _salva(id_bando: str, url: str, titolo: str = "Bando di prova") -> None:
    salva({**_riga(titolo), "id": id_bando}, url, FONTE, TOSCANA)


# --- salva: i tre casi di id e URL ---


def test_stesso_id_e_stesso_url_aggiorna(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Prima versione")
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Seconda versione")

    righe = _leggi(db_su_file, "SELECT id, titolo, codice_fonte FROM bandi")
    assert [tuple(r) for r in righe] == [
        ("parcheggi-2026", "Seconda versione", TOSCANA)
    ]


def test_stesso_id_con_url_diverso_e_rifiutato(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Originale")

    with pytest.raises(ConflittoBando, match="parcheggi-2026"):
        _salva("parcheggi-2026", f"{BASE}/-/altro-bando", "Intruso")

    righe = _leggi(db_su_file, "SELECT id, url, titolo FROM bandi")
    assert [tuple(r) for r in righe] == [
        ("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Originale")
    ]


def test_stesso_url_con_id_diverso_e_rifiutato(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Originale")

    with pytest.raises(ConflittoBando, match="parcheggi-2026"):
        _salva("bando-parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Intruso")

    righe = _leggi(db_su_file, "SELECT id, titolo FROM bandi")
    assert [tuple(r) for r in righe] == [("parcheggi-2026", "Originale")]


def test_il_conflitto_si_vede_anche_con_url_scritto_diversamente(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026")

    with pytest.raises(ConflittoBando):
        _salva("altro-id", "http://www.regione.toscana.it/-/bando-parcheggi-2026/")


def test_salva_scrive_url_canonico(db_su_file):
    _salva(
        "parcheggi-2026",
        "http://www.regione.toscana.it/-/bando-parcheggi-2026/?utm_source=x",
    )

    righe = _leggi(db_su_file, "SELECT url FROM bandi")
    assert righe[0]["url"] == f"{BASE}/-/bando-parcheggi-2026"


def test_conflitto_prima_di_salvare(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026")

    assert conflitto("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026") is None
    assert conflitto("nuovo-id", f"{BASE}/-/bando-nuovo") is None
    assert conflitto("parcheggi-2026", f"{BASE}/-/altro") is not None
    assert conflitto("altro-id", f"{BASE}/-/bando-parcheggi-2026/") is not None


# --- registro delle scansioni ---


def test_registra_due_volte_la_stessa_pagina_lascia_una_riga(db_su_file):
    registra(f"{BASE}/-/bando-x", TOSCANA, "bando-x", "fallito", "errore di rete")
    registra(
        f"{BASE}/-/bando-x/", TOSCANA, "bando-x", "scartato", "scaduto il 2025-01-01"
    )

    righe = _leggi(db_su_file, "SELECT url, esito, motivo FROM scansioni")
    assert [tuple(r) for r in righe] == [
        (f"{BASE}/-/bando-x", "scartato", "scaduto il 2025-01-01")
    ]


def test_da_non_riesaminare_restituisce_url_con_esito_definitivo(db_su_file):
    registra(
        f"{BASE}/-/scaduto", TOSCANA, "scaduto", "scartato", "scaduto il 2025-01-01"
    )
    registra(
        f"{BASE}/-/graduatoria",
        TOSCANA,
        "graduatoria",
        "scartato",
        "non e' un bando: graduatoria",
    )
    registra(
        f"{BASE}/-/incerto", TOSCANA, "incerto", "scartato", "scadenza non determinata"
    )
    registra(f"{BASE}/-/rotto", TOSCANA, "rotto", "fallito", "scaduto il 2025-01-01")

    assert da_non_riesaminare() == {f"{BASE}/-/scaduto", f"{BASE}/-/graduatoria"}


def test_gli_scarti_per_tipo_di_beneficiario_tornano_candidati(db_su_file):
    """I bandi si acquisiscono per ogni tipo di beneficiario: questi scarti
    delle scansioni passate non sono piu' definitivi."""
    registra(
        f"{BASE}/-/privati", TOSCANA, "privati", "scartato", "non ammette i Comuni"
    )
    registra(
        f"{BASE}/-/incerto",
        TOSCANA,
        "incerto",
        "scartato",
        "ammette_comuni a bassa confidenza",
    )

    assert da_non_riesaminare() == set()


def test_registra_conserva_motivo_e_avvisi_per_intero(db_su_file):
    motivo = "; ".join(f"campo_{i}: campo obbligatorio mancante" for i in range(10))
    avvisi = (
        "dotazione: valore '238.440,00 euro (con possibile incremento "
        "fino a 3.485.957,00 euro)' non convertibile, lasciato vuoto"
    )
    registra(f"{BASE}/-/bando-x", TOSCANA, "bando-x", "fallito", motivo, avvisi)

    riga = _leggi(db_su_file, "SELECT motivo, avvisi FROM scansioni")[0]
    assert len(motivo) > 100
    assert (riga["motivo"], riga["avvisi"]) == (motivo, avvisi)


def test_registra_senza_avvisi_lascia_la_colonna_vuota(db_su_file):
    registra(f"{BASE}/-/bando-x", TOSCANA, "bando-x", "scartato", "scaduto")
    assert _leggi(db_su_file, "SELECT avvisi FROM scansioni")[0]["avvisi"] is None


# --- lettura dell'elenco ---


@pytest.fixture
def elenco_salvato(monkeypatch):
    """L'elenco del portale letto dall'estratto salvato, non dal sito."""
    monkeypatch.setattr(elenco, "scarica", lambda url, timeout=30: ELENCO_SALVATO)


EMERGENZA = (
    "manifestazione-di-interesse-per-il-reperimento-di-patrimonio-"
    "immobiliare-da-destinare-ad-emergenza-abitativa-e/o-residenza-sociale-1"
)


def test_leggi_elenco_conserva_slug_interi(elenco_salvato):
    """Slug con "/", "." e caratteri codificati non vengono tagliati."""
    assert elenco.leggi_elenco() == [
        "bando-parcheggi-2026",
        "avviso-pubblico-per-il-sostegno-allo-sport-per-l-annualit%C3%A0-2022",
        "selezione-per%C2%A0dirigente-medico-disciplina-ortopedia",
        EMERGENZA,
        "presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo",
        "presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo-2024",
        "bando-legalita-scuole-a.s.-2025-26",
    ]


def test_scopri_riconosce_i_bandi_in_archivio_per_url(db_su_file, elenco_salvato):
    """Il bando con "/" nello slug, salvato con un id nostro, non e' nuovo."""
    url_emergenza = f"{BASE}/-/{EMERGENZA}"
    _salva("immobili-emergenza-abitativa-2026", url_emergenza)

    voci = {v.url: v for v in elenco.scopri()}

    assert not voci[url_emergenza].nuovo
    assert voci[f"{BASE}/-/bando-parcheggi-2026"].nuovo
    assert all(v.codice_fonte == TOSCANA for v in voci.values())
    assert len(voci) == 7


def test_gia_in_archivio_restituisce_url_canonici(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026")
    assert elenco.gia_in_archivio() == {f"{BASE}/-/bando-parcheggi-2026"}


# --- identificativo ricavato dallo slug ---


def _id(slug: str) -> str:
    return elenco.id_da_slug(slug, elenco.url_da_slug(slug))


def test_id_da_slug_corto_resta_uguale():
    assert _id("bando-parcheggi-2026") == "bando-parcheggi-2026"


def test_id_da_slug_decodifica_e_toglie_accenti_barre_e_punti():
    assert _id("sport-annualit%C3%A0-2022") == "sport-annualita-2022"
    assert _id("selezione-per%C2%A0dirigente") == "selezione-per-dirigente"
    assert _id("museo/ecomuseo-2024") == "museo-ecomuseo-2024"
    assert _id("scuole-a.s.-2025-26") == "scuole-a-s-2025-26"


def test_id_da_slug_lungo_finisce_con_codice_dall_url():
    identificativo = _id(EMERGENZA)

    assert len(identificativo) <= elenco.LUNGHEZZA_ID
    assert re.fullmatch(r"[a-z0-9-]+-[0-9a-f]{6}", identificativo)
    assert identificativo.startswith("manifestazione-di-interesse-per-il-reper")
    assert _id(EMERGENZA) == identificativo


def test_slug_lunghi_con_lo_stesso_inizio_danno_id_diversi():
    """Le tre pagine museo/ecomuseo hanno i primi 60 caratteri uguali."""
    inizio = "presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo"
    slug = [f"{inizio}/ecomuseo", f"{inizio}/ecomuseo-2024", f"{inizio}/ecomuseo-x"]

    identificativi = {_id(s) for s in slug}

    assert len(identificativi) == 3
    assert all(len(i) <= elenco.LUNGHEZZA_ID for i in identificativi)


def test_id_da_slug_lunghi_non_vanno_in_conflitto_al_salvataggio(db_su_file):
    inizio = "presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo"
    for s in (f"{inizio}/ecomuseo", f"{inizio}/ecomuseo-2024"):
        url = elenco.url_da_slug(s)
        _salva(elenco.id_da_slug(s, url), url)

    assert len(_leggi(db_su_file, "SELECT id FROM bandi")) == 2


# --- scopri_bandi --comandi ---


def test_comandi_usano_il_percorso_giusto_del_modulo(
    db_su_file, elenco_salvato, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "argv", ["scopri_bandi", "--comandi"])

    scopri_bandi.main()

    comandi = [
        r for r in capsys.readouterr().out.splitlines() if r.startswith("python -m")
    ]
    assert len(comandi) == 7
    for comando in comandi:
        _, _, modulo, url, identificativo = comando.split(" ")
        assert modulo == "scripts.ingestione.estrai_bando"
        assert url.startswith(f"{BASE}/-/")
        assert re.fullmatch(r"[a-z0-9-]{1,60}", identificativo)
    importlib.import_module(modulo)
