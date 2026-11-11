"""Tabelle beneficiari_bando e interventi_bando, migrazione da
ammette_comuni, salvataggio di un bando con le sue righe."""

import sqlite3

import pytest

from scripts.manutenzione.migra_beneficiari import MigrazioneFermata, migra
from src.database.interrogazioni_bandi import AMMETTE_COMUNI
from src.estrazione.beneficiari import TIPI_BENEFICIARIO
from src.estrazione.salva import salva

BASE = "https://www.regione.toscana.it"


@pytest.fixture
def con_bando(conn):
    """Il database di prova con una fonte e un bando."""
    conn.execute(
        "INSERT INTO fonti VALUES ('regione-toscana', 'Toscana', ?, ?, 'prova', "
        "'2026-11-11')",
        (f"{BASE}/bandi-aperti", BASE),
    )
    conn.execute(
        "INSERT INTO bandi (id, titolo, ente, beneficiari, url, fonte, "
        "codice_fonte, verificato_il) VALUES ('tpl', 'TPL', 'Regione', "
        "'Enti locali competenti.', ?, 'prova', 'regione-toscana', '2026-11-11')",
        (f"{BASE}/-/tpl",),
    )
    return conn


def _beneficiario(conn, tipo, condizioni=None, frase="Enti locali competenti."):
    conn.execute(
        "INSERT INTO beneficiari_bando (id_bando, tipo, condizioni, frase, origine) "
        "VALUES ('tpl', ?, ?, ?, 'estrazione')",
        (tipo, condizioni, frase),
    )


# --- schema ---


@pytest.mark.parametrize("tipo", list(TIPI_BENEFICIARIO))
def test_ogni_tipo_della_lista_e_accettato(con_bando, tipo):
    _beneficiario(con_bando, tipo, condizioni="condizione di prova")


def test_tipo_fuori_lista_e_rifiutato(con_bando):
    with pytest.raises(sqlite3.IntegrityError):
        _beneficiario(con_bando, "comuni_montani")


def test_qualsiasi_soggetto_senza_condizioni_e_rifiutato(con_bando):
    with pytest.raises(sqlite3.IntegrityError):
        _beneficiario(con_bando, "qualsiasi_soggetto", condizioni=None)


def test_beneficiario_di_un_bando_inesistente_e_rifiutato(con_bando):
    with pytest.raises(sqlite3.IntegrityError):
        con_bando.execute(
            "INSERT INTO beneficiari_bando (id_bando, tipo, frase, origine) "
            "VALUES ('inesistente', 'comune', 'frase', 'estrazione')"
        )


def test_origine_fuori_lista_e_rifiutata(con_bando):
    with pytest.raises(sqlite3.IntegrityError):
        con_bando.execute(
            "INSERT INTO beneficiari_bando (id_bando, tipo, frase, origine) "
            "VALUES ('tpl', 'comune', 'frase', 'inventata')"
        )


def test_un_bando_ha_piu_tipi_dalla_stessa_frase(con_bando):
    for tipo in ("comune", "unione_comuni", "altro_ente_pubblico"):
        _beneficiario(con_bando, tipo, condizioni="competenti")

    quanti = con_bando.execute("SELECT COUNT(*) FROM beneficiari_bando").fetchone()
    assert quanti[0] == 3


def test_intervento_con_genere_fuori_lista_e_rifiutato(con_bando):
    with pytest.raises(sqlite3.IntegrityError):
        con_bando.execute(
            "INSERT INTO interventi_bando VALUES ('tpl', 1, 'progetto', 'x', 'x')"
        )


def test_ammette_comuni_si_calcola_dai_beneficiari(con_bando):
    def ammette():
        return con_bando.execute(
            f"SELECT {AMMETTE_COMUNI} FROM bandi WHERE id = 'tpl'"
        ).fetchone()[0]

    assert ammette() == 0
    _beneficiario(con_bando, "unione_comuni")
    assert ammette() == 0
    _beneficiario(con_bando, "comune")
    assert ammette() == 1


# --- migrazione ---


def _vecchio(id_bando: str, ammette: str, beneficiari: str = "Comuni") -> dict:
    return {
        "id": id_bando,
        "titolo": "Bando",
        "ammette_comuni": ammette,
        "beneficiari": beneficiari,
    }


def test_migra_crea_una_riga_comune_per_ogni_bando_che_li_ammetteva():
    bandi, beneficiari = migra(
        [_vecchio("a", "1", "I Comuni toscani"), _vecchio("b", "0"), _vecchio("c", "1")]
    )

    assert [b["id"] for b in bandi] == ["a", "b", "c"]
    assert all("ammette_comuni" not in b for b in bandi)
    assert all(b["classificato_il"] == "" for b in bandi)
    assert beneficiari == [
        {
            "id_bando": "a",
            "tipo": "comune",
            "soggetto": "",
            "condizioni": "",
            "frase": "I Comuni toscani",
            "confidenza": "",
            "origine": "ammette_comuni",
        },
        {
            "id_bando": "c",
            "tipo": "comune",
            "soggetto": "",
            "condizioni": "",
            "frase": "Comuni",
            "confidenza": "",
            "origine": "ammette_comuni",
        },
    ]


def test_migra_rilanciata_non_cambia_nulla():
    bandi, _ = migra([_vecchio("a", "1"), _vecchio("b", "0")])
    di_nuovo, beneficiari = migra(bandi)
    assert (di_nuovo, beneficiari) == (bandi, [])


def test_migra_si_ferma_su_valore_diverso_da_0_e_1():
    with pytest.raises(MigrazioneFermata) as errore:
        migra([_vecchio("a", "1"), _vecchio("b", "forse")])
    assert errore.value.righe == ["b: ammette_comuni = 'forse'"]


def test_migra_si_ferma_su_bando_che_ammette_senza_beneficiari():
    with pytest.raises(MigrazioneFermata):
        migra([_vecchio("a", "1", beneficiari="  ")])


# --- salvataggio ---


def _riga(ammette: int) -> dict:
    return {
        "id": "tpl",
        "titolo": "TPL",
        "ente": "Regione",
        "a_sportello": 0,
        "ammette_comuni": ammette,
        "beneficiari": "Enti locali competenti.",
    }


def _leggi(percorso, sql):
    c = sqlite3.connect(percorso)
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def test_salva_ricava_la_riga_comune_da_ammette_comuni(db_su_file):
    salva(_riga(1), f"{BASE}/-/tpl", "prova", "regione-toscana")

    assert _leggi(
        db_su_file, "SELECT id_bando, tipo, frase, origine FROM beneficiari_bando"
    ) == [("tpl", "comune", "Enti locali competenti.", "ammette_comuni")]


def test_salva_aggiorna_senza_cancellare_le_righe_estratte(db_su_file):
    salva(_riga(1), f"{BASE}/-/tpl", "prova", "regione-toscana")
    c = sqlite3.connect(db_su_file)
    c.execute(
        "INSERT INTO beneficiari_bando (id_bando, tipo, frase, origine) "
        "VALUES ('tpl', 'unione_comuni', 'Enti locali competenti.', 'estrazione')"
    )
    c.execute("INSERT INTO interventi_bando VALUES ('tpl', 1, 'spesa', 'autobus', 'x')")
    c.execute("UPDATE bandi SET classificato_il = '2026-11-11'")
    c.commit()
    c.close()

    salva(_riga(0), f"{BASE}/-/tpl", "prova", "regione-toscana")

    assert _leggi(db_su_file, "SELECT tipo, origine FROM beneficiari_bando") == [
        ("unione_comuni", "estrazione")
    ]
    assert len(_leggi(db_su_file, "SELECT * FROM interventi_bando")) == 1
    assert _leggi(db_su_file, "SELECT classificato_il FROM bandi") == [("2026-11-11",)]
