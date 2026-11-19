"""Correzioni a mano con le frasi di un testo salvato, senza rete.

I test usano il database in memoria di conftest.py, o quello temporaneo su
file (db_su_file) per main: mai il database vero, e mai i CSV veri.
"""

import sqlite3
import sys

import pytest

import scripts.manutenzione.correggi_da_testo as cdt

ID = "bando-di-prova-2027"
FRASE = (
    "Possono presentare istanza di contributo gli Enti locali, soggetti "
    "pubblici, enti di rievocazione storica"
)
TESTO = f"Titolo della pagina\n3 Novembre 2026\n{FRASE}, vale a dire le associazioni.\n"


def _popola(c: sqlite3.Connection) -> None:
    """Un bando con la data dell'atto e una riga di beneficiari da correggere."""
    c.execute(
        "INSERT OR IGNORE INTO fonti (codice, nome, tipo, url_base, schema_link, "
        "fonte, verificato_il) VALUES ('fonte-prova', 'Fonte di prova', 'pagine', "
        "'https://www.prova.it', '^/(?P<percorso>(?P<slug>[a-z-]+))$', 'prova', "
        "'2026-11-19')"
    )
    c.execute(
        "INSERT INTO bandi (id, titolo, ente, url, fonte, codice_fonte, "
        "verificato_il, pubblicato_il, pubblicato_origine) VALUES (?, 'Bando', "
        "'Ente', 'https://www.prova.it/bando', 'Fonte di prova', 'fonte-prova', "
        "'2026-11-19', '2025-03-20', 'atto')",
        (ID,),
    )
    c.execute(
        "INSERT INTO beneficiari_bando (id_bando, tipo, soggetto, frase, origine) "
        "VALUES (?, 'altro_ente_pubblico', 'Enti locali', ?, 'estrazione')",
        (ID, FRASE),
    )
    c.commit()


def _correzioni(testo) -> list[cdt.Correzione]:
    return [
        cdt.Correzione(
            tabella="bandi",
            riga={"id": ID},
            attesi={"pubblicato_il": "2025-03-20", "pubblicato_origine": "atto"},
            corretti={
                "pubblicato_il": "2026-11-03",
                "pubblicato_origine": "pubblicazione",
            },
            frasi=("3 Novembre 2026",),
            testo=testo,
        ),
        cdt.Correzione(
            tabella="beneficiari_bando",
            riga={"id_bando": ID, "tipo": "altro_ente_pubblico"},
            attesi={"soggetto": "Enti locali", "origine": "estrazione"},
            corretti={"soggetto": "soggetti pubblici", "origine": "manuale"},
            frasi=(FRASE,),
            testo=testo,
        ),
    ]


def _stato(c: sqlite3.Connection) -> tuple:
    bando = c.execute(
        "SELECT pubblicato_il, pubblicato_origine FROM bandi WHERE id = ?", (ID,)
    ).fetchone()
    beneficiario = c.execute(
        "SELECT soggetto, origine FROM beneficiari_bando WHERE id_bando = ?", (ID,)
    ).fetchone()
    return tuple(bando), tuple(beneficiario)


PRIMA = (("2025-03-20", "atto"), ("Enti locali", "estrazione"))
DOPO = (("2026-11-03", "pubblicazione"), ("soggetti pubblici", "manuale"))


@pytest.fixture
def testo(tmp_path):
    percorso = tmp_path / "pagina.txt"
    percorso.write_text(TESTO, encoding="utf-8")
    return percorso


def test_correzione_riuscita(conn, testo):
    _popola(conn)

    messaggi, toccate = cdt.applica(conn, _correzioni(testo), prova=False)

    assert _stato(conn) == DOPO
    assert all("corretto: " in m for m in messaggi)
    assert toccate == {"bandi", "beneficiari_bando"}


def test_rilanciata_non_cambia_nulla(conn, testo):
    _popola(conn)
    cdt.applica(conn, _correzioni(testo), prova=False)

    messaggi, toccate = cdt.applica(conn, _correzioni(testo), prova=False)

    assert _stato(conn) == DOPO
    assert all(m.endswith("gia' corretto") for m in messaggi)
    assert toccate == set()


def test_frase_non_trovata_nessuna_modifica(conn, tmp_path):
    _popola(conn)
    altro = tmp_path / "altro.txt"
    altro.write_text("Una pagina che non contiene le frasi.", encoding="utf-8")

    messaggi, toccate = cdt.applica(conn, _correzioni(altro), prova=False)

    assert _stato(conn) == PRIMA
    assert all("SALTATO: frasi non trovate" in m for m in messaggi)
    assert toccate == set()


def test_testo_mancante_nessuna_modifica(conn, tmp_path):
    _popola(conn)

    messaggi, _ = cdt.applica(conn, _correzioni(tmp_path / "manca.txt"), prova=False)

    assert _stato(conn) == PRIMA
    assert all("SALTATO: testo non trovato" in m for m in messaggi)


def test_valore_in_archivio_diverso_dall_atteso_nessuna_modifica(conn, testo):
    _popola(conn)
    conn.execute("UPDATE bandi SET pubblicato_il = '2026-01-01' WHERE id = ?", (ID,))
    conn.execute(
        "UPDATE beneficiari_bando SET soggetto = 'Comuni' WHERE id_bando = ?", (ID,)
    )

    messaggi, toccate = cdt.applica(conn, _correzioni(testo), prova=False)

    assert _stato(conn) == (
        ("2026-01-01", "atto"),
        ("Comuni", "estrazione"),
    )
    assert all("SALTATO: in archivio" in m for m in messaggi)
    assert toccate == set()


def test_campo_non_correggibile_rifiutato(conn, testo):
    _popola(conn)
    sbagliata = cdt.Correzione(
        tabella="bandi",
        riga={"id": ID},
        attesi={"titolo": "Bando"},
        corretti={"titolo": "Altro"},
        frasi=("3 Novembre 2026",),
        testo=testo,
    )

    with pytest.raises(AssertionError):
        cdt.applica(conn, [sbagliata], prova=False)


def test_prova_non_scrive(db_su_file, testo, monkeypatch, capsys):
    """--prova: database invariato e nessun CSV riscritto."""
    c = sqlite3.connect(db_su_file)
    try:
        _popola(c)
    finally:
        c.close()

    def vietata(*tabelle):
        raise AssertionError(f"aggiorna_csv chiamata in prova: {tabelle}")

    monkeypatch.setattr(cdt, "aggiorna_csv", vietata)
    monkeypatch.setattr(sys, "argv", ["correggi_da_testo", "--prova"])

    cdt.main(_correzioni(testo))

    c = sqlite3.connect(db_su_file)
    try:
        assert _stato(c) == PRIMA
    finally:
        c.close()
    uscita = capsys.readouterr().out
    assert uscita.count("da correggere: ") == 2
    assert "Prova: nulla modificato." in uscita


def test_senza_prova_riversa_le_tabelle_toccate(db_su_file, testo, monkeypatch):
    c = sqlite3.connect(db_su_file)
    try:
        _popola(c)
    finally:
        c.close()
    riversate = []
    monkeypatch.setattr(cdt, "aggiorna_csv", lambda *t: riversate.extend(t))
    monkeypatch.setattr(sys, "argv", ["correggi_da_testo"])

    cdt.main(_correzioni(testo))

    c = sqlite3.connect(db_su_file)
    try:
        assert _stato(c) == DOPO
    finally:
        c.close()
    assert riversate == ["bandi", "beneficiari_bando"]
