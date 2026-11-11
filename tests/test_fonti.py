"""Tabella fonti, chiavi di bandi e scansioni, forma canonica degli URL,
migrazione dei CSV."""

import csv
import sqlite3

import pytest

from scripts.manutenzione.migra_fonti import (
    MigrazioneFermata,
    migra_bandi,
    migra_scansioni,
)
from src.config import PROCESSED_DIR
from src.database.schema import TABELLE_DA_CSV, carica_csv
from src.estrazione.indirizzi import url_canonico

TOSCANA = "regione-toscana"
ALTRA = "altra-fonte"
BASE = "https://www.regione.toscana.it"


@pytest.fixture
def con_fonti(conn):
    """Il database di prova con due fonti."""
    conn.executemany(
        "INSERT INTO fonti (codice, nome, url_elenco, url_base, fonte, verificato_il) "
        "VALUES (?, ?, ?, ?, 'prova', '2026-11-11')",
        [
            (TOSCANA, "Toscana", f"{BASE}/bandi-aperti", BASE),
            (ALTRA, "Altra", "https://altra.it/bandi", "https://altra.it"),
        ],
    )
    return conn


def _bando(conn, id_bando: str, url: str, codice_fonte: str = TOSCANA) -> None:
    conn.execute(
        "INSERT INTO bandi (id, titolo, ente, beneficiari, "
        "url, fonte, codice_fonte, verificato_il) "
        "VALUES (?, 'titolo', 'ente', 'Comuni', ?, 'prova', ?, '2026-11-11')",
        (id_bando, url, codice_fonte),
    )


def _scansione(conn, url: str, slug: str, codice_fonte: str) -> None:
    conn.execute(
        "INSERT INTO scansioni (url, codice_fonte, slug, esito, motivo, esaminato_il) "
        "VALUES (?, ?, ?, 'scartato', 'scaduto', '2026-11-11')",
        (url, codice_fonte, slug),
    )


# --- forma canonica degli URL ---


@pytest.mark.parametrize(
    ("grezzo", "atteso"),
    [
        ("http://www.regione.toscana.it/-/bando", f"{BASE}/-/bando"),
        (f"{BASE}/-/bando/", f"{BASE}/-/bando"),
        ("https://WWW.Regione.Toscana.it/-/Bando", f"{BASE}/-/Bando"),
        (f"{BASE}/-/bando#paragrafo", f"{BASE}/-/bando"),
        (f"{BASE}/-/bando?utm_source=x&utm_medium=y", f"{BASE}/-/bando"),
        (f"{BASE}/-/bando?fbclid=abc", f"{BASE}/-/bando"),
        ("https://altra.it/p?id=12&utm_source=x&b=2", "https://altra.it/p?id=12&b=2"),
        (f"  {BASE}/-/bando  ", f"{BASE}/-/bando"),
        (f"{BASE}/-/e/o-residenza", f"{BASE}/-/e/o-residenza"),
    ],
)
def test_url_canonico(grezzo, atteso):
    assert url_canonico(grezzo) == atteso


def test_url_canonico_e_stabile():
    url = "http://Altra.it/p/?id=1&utm_campaign=z#a"
    assert url_canonico(url_canonico(url)) == url_canonico(url)


# --- schema ---


def test_stesso_slug_da_due_fonti_non_si_sovrascrive(con_fonti):
    _scansione(con_fonti, f"{BASE}/-/bando-2026", "bando-2026", TOSCANA)
    _scansione(con_fonti, "https://altra.it/-/bando-2026", "bando-2026", ALTRA)

    quante = con_fonti.execute("SELECT COUNT(*) FROM scansioni").fetchone()[0]
    assert quante == 2


def test_scansione_con_lo_stesso_url_e_rifiutata(con_fonti):
    _scansione(con_fonti, f"{BASE}/-/bando", "bando", TOSCANA)
    with pytest.raises(sqlite3.IntegrityError):
        _scansione(con_fonti, f"{BASE}/-/bando", "bando", TOSCANA)


def test_due_bandi_con_lo_stesso_url_sono_rifiutati(con_fonti):
    _bando(con_fonti, "primo", f"{BASE}/-/bando")
    with pytest.raises(sqlite3.IntegrityError):
        _bando(con_fonti, "secondo", f"{BASE}/-/bando")


def test_bando_con_fonte_sconosciuta_e_rifiutato(con_fonti):
    with pytest.raises(sqlite3.IntegrityError):
        _bando(con_fonti, "primo", f"{BASE}/-/bando", "inesistente")


def test_scansione_con_fonte_sconosciuta_e_rifiutata(con_fonti):
    with pytest.raises(sqlite3.IntegrityError):
        _scansione(con_fonti, f"{BASE}/-/bando", "bando", "inesistente")


def test_fonti_caricata_prima_di_chi_la_usa():
    ordine = list(TABELLE_DA_CSV)
    assert ordine.index("fonti") < ordine.index("bandi")
    assert ordine.index("fonti") < ordine.index("scansioni")


ACQUISIZIONE = ["fonti", "bandi", "beneficiari_bando", "interventi_bando", "scansioni"]


@pytest.mark.parametrize("tabella", ACQUISIZIONE)
def test_i_csv_veri_si_caricano_senza_scarti(conn, tabella):
    """I CSV di data/processed entrano tutti nello schema, in memoria."""
    for t in ACQUISIZIONE:
        if t == tabella:
            break
        carica_csv(conn, t, TABELLE_DA_CSV[t])

    with (PROCESSED_DIR / f"{tabella}.csv").open(encoding="utf-8-sig") as f:
        righe_csv = len(list(csv.DictReader(f)))

    assert carica_csv(conn, tabella, TABELLE_DA_CSV[tabella]) == righe_csv


# --- migrazione dei CSV ---


def _vecchio_bando(id_bando: str, url: str) -> dict:
    return {"id": id_bando, "url": url, "fonte": "Portale bandi Regione Toscana"}


def _vecchia_scansione(slug: str, esito: str = "scartato") -> dict:
    return {"slug": slug, "esito": esito, "motivo": "", "esaminato_il": "2026-11-01"}


def test_migra_bandi_aggiunge_la_fonte_a_ogni_riga():
    righe = [_vecchio_bando("a", f"{BASE}/-/a"), _vecchio_bando("b", f"{BASE}/-/b")]

    migrate = migra_bandi(righe, TOSCANA)

    assert len(migrate) == len(righe)
    assert all(r["codice_fonte"] == TOSCANA for r in migrate)
    assert [r["id"] for r in migrate] == ["a", "b"]


def test_migra_bandi_rilanciata_non_cambia_nulla():
    righe = [_vecchio_bando("a", f"{BASE}/-/a")]
    una_volta = migra_bandi(righe, TOSCANA)
    assert migra_bandi(una_volta, ALTRA) == una_volta


def test_migra_bandi_si_ferma_su_url_non_canonico():
    with pytest.raises(MigrazioneFermata) as errore:
        migra_bandi([_vecchio_bando("a", f"{BASE}/-/a/")], TOSCANA)
    assert errore.value.righe == [f"{BASE}/-/a/"]


def test_migra_bandi_si_ferma_su_url_duplicato():
    righe = [_vecchio_bando("a", f"{BASE}/-/x"), _vecchio_bando("b", f"{BASE}/-/x")]
    with pytest.raises(MigrazioneFermata):
        migra_bandi(righe, TOSCANA)


def test_migra_scansioni_ricostruisce_url_come_scopri():
    migrate = migra_scansioni([_vecchia_scansione("bando-2026")], BASE, TOSCANA, set())

    assert migrate == [
        {
            "url": f"{BASE}/-/bando-2026",
            "codice_fonte": TOSCANA,
            "slug": "bando-2026",
            "esito": "scartato",
            "motivo": "",
            "esaminato_il": "2026-11-01",
        }
    ]


def test_migra_scansioni_conserva_ogni_riga():
    righe = [_vecchia_scansione(f"bando-{i}") for i in range(50)]
    assert len(migra_scansioni(righe, BASE, TOSCANA, set())) == 50


def test_migra_scansioni_rilanciata_non_cambia_nulla():
    una_volta = migra_scansioni([_vecchia_scansione("a")], BASE, TOSCANA, set())
    assert migra_scansioni(una_volta, "https://altro.it", ALTRA, set()) == una_volta


def test_migra_scansioni_salvato_con_bando_corrispondente():
    righe = [_vecchia_scansione("bando-2026", "salvato")]
    migrate = migra_scansioni(righe, BASE, TOSCANA, {f"{BASE}/-/bando-2026"})
    assert migrate[0]["url"] == f"{BASE}/-/bando-2026"


def test_migra_scansioni_si_ferma_su_salvato_senza_bando():
    """Lo slug tagliato dalla vecchia regex non ritrova il suo bando."""
    righe = [
        _vecchia_scansione("tagliato-e", "salvato"),
        _vecchia_scansione("altro", "scartato"),
    ]
    with pytest.raises(MigrazioneFermata) as errore:
        migra_scansioni(righe, BASE, TOSCANA, {f"{BASE}/-/tagliato-e/o-residenza"})
    assert errore.value.righe == [f"tagliato-e  ->  {BASE}/-/tagliato-e"]


def test_migra_scansioni_si_ferma_su_url_duplicato():
    righe = [
        {**_vecchia_scansione("a"), "url": f"{BASE}/-/a", "codice_fonte": TOSCANA},
        {**_vecchia_scansione("b"), "url": f"{BASE}/-/a", "codice_fonte": TOSCANA},
    ]
    with pytest.raises(MigrazioneFermata):
        migra_scansioni(righe, BASE, TOSCANA, set())
