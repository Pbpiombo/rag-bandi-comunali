"""Doppioni tra le fonti: il file, il confronto, la rimozione e l'annullamento.

Database in memoria (conftest), con due fonti e bandi inventati. Nessuna
rete, nessun modello.
"""

import sqlite3
from datetime import date

import pytest

from src.database import interrogazioni_bandi as ib
from src.estrazione import doppioni as dp

OGGI = date(2026, 11, 13)
REGIONE = "https://www.regione.toscana.it/-/"
CATALOGO = "https://www.regione.toscana.it/bancadati/BURT/Contenuto.xml?id="
COLONNE = ",".join(dp.COLONNE)


class DataFissa(date):
    @classmethod
    def today(cls):
        return cls(OGGI.year, OGGI.month, OGGI.day)


@pytest.fixture
def db(conn, monkeypatch):
    """Il database di prova con le due fonti dei bandi."""
    monkeypatch.setattr(ib, "date", DataFissa)
    conn.executemany(
        "INSERT INTO fonti (codice, nome, url_base, schema_link, fonte, "
        "verificato_il) VALUES (?, ?, ?, '^/-/', 'prova', '2026-11-13')",
        [
            ("regione-toscana", "Toscana", REGIONE),
            ("incentivi-italia", "Incentivi Italia", "https://www.incentivi.gov.it"),
        ],
    )
    return conn


def bando(conn, id_bando, url, fonte, tipi=("impresa_turistica",), **campi):
    """Un bando aperto, con una riga di beneficiari per ogni tipo."""
    riga = {
        "id": id_bando,
        "titolo": f"Bando {id_bando}",
        "ente": "Regione Toscana",
        "beneficiari": "Imprese",
        "scadenza": "2026-12-31",
        "url": url,
        "fonte": "prova",
        "codice_fonte": fonte,
        "verificato_il": "2026-11-13",
        "classificato_il": "2026-11-13",
        **campi,
    }
    conn.execute(
        f"INSERT INTO bandi ({', '.join(riga)}) VALUES ({', '.join('?' for _ in riga)})",
        list(riga.values()),
    )
    for tipo in tipi:
        conn.execute(
            "INSERT INTO beneficiari_bando (id_bando, tipo, frase, origine) "
            "VALUES (?, ?, 'frase', 'estrazione')",
            (id_bando, tipo),
        )


def coppia(conn, tolta=None, tenuta=None):
    """La versione del catalogo e quella della Regione dello stesso bando."""
    bando(conn, "incentivi-1", CATALOGO + "1", "incentivi-italia", **(tolta or {}))
    bando(conn, "turismo", REGIONE + "turismo", "regione-toscana", **(tenuta or {}))


def doppione(accettate=()):
    return dp.Doppione(
        CATALOGO + "1",
        "incentivi-italia",
        "turismo",
        "stesso bando",
        "2026-11-13",
        frozenset(accettate),
    )


def esiste(conn, id_bando) -> bool:
    return (
        conn.execute("SELECT 1 FROM bandi WHERE id = ?", (id_bando,)).fetchone()
        is not None
    )


# --- il file ---


def scrivi_file(tmp_path, *righe) -> object:
    percorso = tmp_path / "doppioni.csv"
    percorso.write_text("\n".join([COLONNE, *righe]) + "\n", encoding="utf-8-sig")
    return percorso


def test_il_file_si_legge_per_indirizzo_canonico(tmp_path):
    percorso = scrivi_file(
        tmp_path,
        f'{CATALOGO}1,incentivi-italia,turismo,stesso bando,2026-11-13,"costo_max, '
        'tipo:impresa_turistica"',
        f"{CATALOGO}2,incentivi-italia,altro,stesso bando,2026-11-13,",
    )

    letti = dp.leggi_doppioni(percorso)

    assert set(letti) == {CATALOGO + "1", CATALOGO + "2"}
    assert letti[CATALOGO + "1"].id_tenuto == "turismo"
    assert letti[CATALOGO + "1"].differenze_accettate == {
        "costo_max",
        "tipo:impresa_turistica",
    }
    assert letti[CATALOGO + "2"].differenze_accettate == frozenset()


def test_senza_file_nessun_doppione(tmp_path):
    assert dp.leggi_doppioni(tmp_path / "manca.csv") == {}


@pytest.mark.parametrize(
    ("righe", "messaggio"),
    [
        (["url,id_tenuto"], "colonne attese"),
        ([f"{CATALOGO}1,incentivi-italia,,motivo,2026-11-13,"], "campi vuoti"),
        ([f"{CATALOGO}1,incentivi-italia,turismo,motivo,13/11/2026,"], "data"),
        (
            [
                f"{CATALOGO}1,incentivi-italia,turismo,motivo,2026-11-13,",
                f"{CATALOGO}1,incentivi-italia,altro,motivo,2026-11-13,",
            ],
            "ripetuto",
        ),
    ],
)
def test_un_file_sbagliato_si_rifiuta(tmp_path, righe, messaggio):
    percorso = tmp_path / "doppioni.csv"
    if righe[0].startswith("url,id_tenuto"):
        percorso.write_text("url,id_tenuto\n", encoding="utf-8")
    else:
        percorso = scrivi_file(tmp_path, *righe)

    with pytest.raises(dp.FileNonValido, match=messaggio):
        dp.leggi_doppioni(percorso)


# --- il confronto ---


def test_un_valore_che_la_tenuta_non_ha_ferma(db):
    coppia(db, tolta={"costo_max": 70000.0})

    esito = dp.togli(db, doppione(), scrivi=True)

    assert esito.stato == "fermato"
    assert esito.lacune == ["costo_max"]
    assert esiste(db, "incentivi-1")


def test_un_tipo_che_la_tenuta_non_ha_ferma(db):
    coppia(db, tolta={"tipi": ("impresa_turistica", "professionista_autonomo")})

    esito = dp.togli(db, doppione(), scrivi=True)

    assert esito.lacune == ["tipo:professionista_autonomo"]
    assert esiste(db, "incentivi-1")


def test_valori_diversi_si_mostrano_ma_non_fermano(db):
    coppia(db, tolta={"contributo_max": 11000.0}, tenuta={"contributo_max": 10875.6})

    esito = dp.togli(db, doppione(), scrivi=False)

    assert esito.stato == "da togliere"
    assert esito.diversi == ["contributo_max: 11000.0 / 10875.6"]


def test_una_differenza_accettata_non_ferma(db):
    coppia(db, tolta={"costo_max": 70000.0})

    esito = dp.togli(db, doppione(accettate=["costo_max"]), scrivi=False)

    assert esito.stato == "da togliere"
    assert esito.lacune == []


# --- la rimozione ---


def test_la_prova_non_cambia_nulla(db):
    coppia(db)

    esito = dp.togli(db, doppione(), scrivi=False)

    assert esito.prima == {"per beneficiario impresa_turistica": "elenco"}
    assert esiste(db, "incentivi-1")
    assert db.execute("SELECT count(*) FROM scansioni").fetchone()[0] == 0


def test_toglie_e_annota_in_scansioni(db):
    coppia(db)
    db.execute(
        "INSERT INTO interventi_bando (id_bando, numero, genere, descrizione, frase) "
        "VALUES ('incentivi-1', 1, 'spesa', 'spesa', 'frase')"
    )

    esito = dp.togli(db, doppione(), scrivi=True)

    assert esito.stato == "tolto"
    assert esito.dopo == {"per beneficiario impresa_turistica": "elenco"}
    assert not esiste(db, "incentivi-1")
    for tabella in dp.COLLEGATE:
        assert (
            db.execute(
                f"SELECT count(*) FROM {tabella} WHERE id_bando = 'incentivi-1'"
            ).fetchone()[0]
            == 0
        )
    scansione = db.execute(
        "SELECT codice_fonte, slug, esito, motivo FROM scansioni WHERE url = ?",
        (CATALOGO + "1",),
    ).fetchone()
    assert tuple(scansione) == (
        "incentivi-italia",
        "incentivi-1",
        "scartato",
        "doppione di turismo",
    )


def test_si_annulla_se_la_tenuta_non_compare(db):
    # la tenuta non e' un bando: non compare negli elenchi
    coppia(db, tenuta={"natura": "non_bando", "natura_motivo": "graduatoria"})

    esito = dp.togli(db, doppione(), scrivi=True)

    assert esito.stato == "annullato"
    assert esito.prima == {"per beneficiario impresa_turistica": "elenco"}
    assert esito.dopo == {}
    assert esiste(db, "incentivi-1")
    assert db.execute("SELECT count(*) FROM beneficiari_bando").fetchone()[0] == 2
    assert db.execute("SELECT count(*) FROM scansioni").fetchone()[0] == 0


def test_rilanciarlo_non_cambia_nulla(db):
    coppia(db)
    dp.togli(db, doppione(), scrivi=True)

    assert dp.togli(db, doppione(), scrivi=True).stato == "gia' tolto"


def test_tenuto_assente_non_si_toglie(db):
    bando(db, "incentivi-1", CATALOGO + "1", "incentivi-italia")

    assert dp.togli(db, doppione(), scrivi=True).stato == "tenuto assente"
    assert esiste(db, "incentivi-1")


def test_la_copia_di_sicurezza_ha_i_dati(db, tmp_path):
    coppia(db)
    db.commit()

    copia = dp.copia_di_sicurezza(db, "prova", tmp_path)

    assert copia.parent == tmp_path
    assert copia.name.endswith("-prima-di-prova.sqlite")
    letta = sqlite3.connect(copia)
    try:
        assert letta.execute("SELECT count(*) FROM bandi").fetchone()[0] == 2
    finally:
        letta.close()
