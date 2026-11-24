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


# --- 24/11/2026: campi nuovi dei bandi e righe nuove di beneficiari_bando ---

# Una frase con gli spazi accanto alle virgolette, come sulla pagina dei
# contributi per i giornali (categoria C)
FRASE_C = (
    "C) Soggetti che esercitano attività di distribuzione con codice Ateco "
    "46.18.3 “ Attività di intermediari del commercio ”"
)
TESTO_NUOVO = (
    f"{TESTO}Domande entro il 24 novembre 2026, con decreto 25474.\n"
    "Le risorse sono pari a 450 mila euro.\n"
    f"{FRASE_C} il cui codice fosse 82.99.20.\n"
)

CAMPI_NUOVI_ATTESI = {
    "scadenza": None,
    "scadenza_nota": None,
    "riferimento_atto": None,
    "verificato_il": "2026-11-19",
    "beneficiari": None,
    "dotazione": None,
}
CAMPI_NUOVI_CORRETTI = {
    "scadenza": "2026-11-24",
    "scadenza_nota": "proroga al 24 novembre 2026",
    "riferimento_atto": "decreto 25474",
    "verificato_il": "2026-11-24",
    "beneficiari": "Enti locali, soggetti pubblici",
    "dotazione": 450000.0,
}

RIGA_C = {
    "id_bando": ID,
    "tipo": "altra_impresa",
    "soggetto": "distributori",
    "condizioni": "codice Ateco 46.18.3",
    "frase": FRASE_C,
    "confidenza": "alta",
    "origine": "manuale",
}


@pytest.fixture
def testo_nuovo(tmp_path):
    percorso = tmp_path / "pagina-nuova.txt"
    percorso.write_text(TESTO_NUOVO, encoding="utf-8")
    return percorso


def _campi_nuovi(testo) -> cdt.Correzione:
    return cdt.Correzione(
        tabella="bandi",
        riga={"id": ID},
        attesi=CAMPI_NUOVI_ATTESI,
        corretti=CAMPI_NUOVI_CORRETTI,
        frasi=("entro il 24 novembre 2026, con decreto 25474", "450 mila euro"),
        testo=testo,
    )


def _aggiunta(testo, **diversi) -> cdt.Aggiunta:
    return cdt.Aggiunta(
        tabella="beneficiari_bando",
        riga={**RIGA_C, **diversi},
        frasi=("3 Novembre 2026",),
        testo=testo,
    )


def _righe_c(c: sqlite3.Connection) -> list[tuple]:
    return [
        tuple(r)
        for r in c.execute(
            "SELECT tipo, soggetto, origine FROM beneficiari_bando "
            "WHERE id_bando = ? AND tipo = 'altra_impresa'",
            (ID,),
        )
    ]


def test_campi_nuovi_dei_bandi_si_correggono_insieme(conn, testo_nuovo):
    _popola(conn)

    messaggi, toccate = cdt.applica(conn, [_campi_nuovi(testo_nuovo)], prova=False)

    campi = ", ".join(CAMPI_NUOVI_CORRETTI)
    riga = conn.execute(f"SELECT {campi} FROM bandi WHERE id = ?", (ID,)).fetchone()
    assert dict(zip(CAMPI_NUOVI_CORRETTI, riga, strict=True)) == CAMPI_NUOVI_CORRETTI
    assert messaggi[0].startswith("bandi [id=bando-di-prova-2027]: corretto: ")
    assert toccate == {"bandi"}


def test_campi_nuovi_saltati_se_un_valore_in_archivio_e_cambiato(conn, testo_nuovo):
    _popola(conn)
    conn.execute("UPDATE bandi SET scadenza = '2026-11-19' WHERE id = ?", (ID,))

    messaggi, toccate = cdt.applica(conn, [_campi_nuovi(testo_nuovo)], prova=False)

    assert tuple(conn.execute("SELECT scadenza, dotazione FROM bandi").fetchone()) == (
        "2026-11-19",
        None,
    )
    assert "SALTATO: in archivio {'scadenza': '2026-11-19'}" in messaggi[0]
    assert toccate == set()


def test_riga_nuova_aggiunta_con_la_sua_frase(conn, testo_nuovo):
    _popola(conn)

    messaggi, toccate = cdt.applica(conn, [_aggiunta(testo_nuovo)], prova=False)

    assert _righe_c(conn) == [("altra_impresa", "distributori", "manuale")]
    assert messaggi == [
        f"beneficiari_bando [id_bando={ID}, tipo=altra_impresa]: aggiunta: "
        + ", ".join(f"{c}: «{v}»" for c, v in RIGA_C.items())
    ]
    assert toccate == {"beneficiari_bando"}


def test_riga_nuova_rilanciata_non_si_ripete(conn, testo_nuovo):
    _popola(conn)
    cdt.applica(conn, [_aggiunta(testo_nuovo)], prova=False)

    messaggi, toccate = cdt.applica(conn, [_aggiunta(testo_nuovo)], prova=False)

    assert len(_righe_c(conn)) == 1
    assert messaggi[0].endswith("gia' aggiunta")
    assert toccate == set()


def test_riga_nuova_saltata_se_la_sua_frase_non_e_nel_testo(conn, testo):
    """TESTO non contiene la frase della categoria C: niente riga."""
    _popola(conn)

    messaggi, toccate = cdt.applica(conn, [_aggiunta(testo)], prova=False)

    assert _righe_c(conn) == []
    assert "SALTATO: frasi non trovate nel testo" in messaggi[0]
    assert toccate == set()


def test_riga_nuova_saltata_se_la_chiave_c_e_gia_con_altri_valori(conn, testo_nuovo):
    _popola(conn)
    cdt.applica(conn, [_aggiunta(testo_nuovo)], prova=False)

    messaggi, _ = cdt.applica(
        conn, [_aggiunta(testo_nuovo, soggetto="altri distributori")], prova=False
    )

    assert _righe_c(conn) == [("altra_impresa", "distributori", "manuale")]
    assert "SALTATO: c'e' gia' una riga con la stessa chiave" in messaggi[0]


def test_riga_nuova_per_un_bando_che_non_c_e(conn, testo_nuovo):
    _popola(conn)

    messaggi, toccate = cdt.applica(
        conn, [_aggiunta(testo_nuovo, id_bando="bando-assente")], prova=False
    )

    assert "NON TROVATO" in messaggi[0]
    assert toccate == set()


def test_riga_nuova_senza_origine_manuale_rifiutata(conn, testo_nuovo):
    _popola(conn)

    with pytest.raises(AssertionError):
        cdt.applica(conn, [_aggiunta(testo_nuovo, origine="estrazione")], prova=False)
    assert _righe_c(conn) == []


def test_prova_mostra_ogni_frase_trovata_o_no(
    db_su_file, testo_nuovo, monkeypatch, capsys
):
    """--prova: per ogni correzione le frasi una per una, con si' o NO;
    database invariato e nessun CSV riscritto."""
    c = sqlite3.connect(db_su_file)
    try:
        _popola(c)
    finally:
        c.close()
    monkeypatch.setattr(
        cdt, "aggiorna_csv", lambda *t: pytest.fail(f"aggiorna_csv in prova: {t}")
    )
    monkeypatch.setattr(sys, "argv", ["correggi_da_testo", "--prova"])
    assente = cdt.Correzione(
        tabella="bandi",
        riga={"id": ID},
        attesi={"dotazione": None},
        corretti={"dotazione": 1.0},
        frasi=("450 mila euro", "una frase che non c'e'"),
        testo=testo_nuovo,
    )

    cdt.main([_campi_nuovi(testo_nuovo), _aggiunta(testo_nuovo), assente])

    uscita = capsys.readouterr().out
    assert "    trovata: si: «entro il 24 novembre 2026, con decreto 25474»" in uscita
    assert f"    trovata: si: «{FRASE_C}»" in uscita
    assert "    trovata: NO: «una frase che non c'e'»" in uscita
    assert "da aggiungere: " in uscita
    c = sqlite3.connect(db_su_file)
    try:
        assert _righe_c(c) == []
        assert c.execute("SELECT scadenza FROM bandi").fetchone() == (None,)
    finally:
        c.close()
