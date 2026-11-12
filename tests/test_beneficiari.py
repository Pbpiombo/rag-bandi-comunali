"""Tabelle beneficiari_bando e interventi_bando, migrazione da
ammette_comuni, salvataggio di un bando con le sue righe."""

import sqlite3

import pytest

from scripts.manutenzione.migra_beneficiari import MigrazioneFermata, migra
from src.database.interrogazioni_bandi import filtro_ente
from src.estrazione.beneficiari import (
    GENERICI,
    PER_REQUISITO,
    TIPI_BENEFICIARIO,
    TIPI_PRIVATI,
    TIPI_PUBBLICI,
    tipi_da_termini,
)
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


def test_chi_e_ammesso_si_calcola_dai_beneficiari(con_bando):
    def ammette(tipo):
        filtro, parametri = filtro_ente(tipo)
        return con_bando.execute(
            f"SELECT {filtro} FROM bandi WHERE id = 'tpl'", parametri
        ).fetchone()[0]

    assert ammette("comune") == 0
    _beneficiario(con_bando, "unione_comuni")
    assert (ammette("comune"), ammette("unione_comuni")) == (0, 1)
    _beneficiario(con_bando, "comune")
    assert ammette("comune") == 1


# --- regole di corrispondenza ---


@pytest.mark.parametrize(
    "testo",
    [
        "Liberi professionisti iscritti agli ordini",
        "libere/i professioniste/i",
        "una libera professionista",
        "lavoratori autonomi",
        "lavoratrici/lavoratori autonome/i",
        "lavoratrici e lavoratori autonomi",
        "titolari di impresa individuale",
        "titolari d’impresa individuale",
        "il titolare di impresa individuale",
    ],
)
def test_professionisti_e_autonomi_in_tutte_le_forme(testo):
    assert tipi_da_termini(testo) == {"professionista_autonomo"}


@pytest.mark.parametrize(
    "testo",
    ["lavoratori dipendenti", "professionisti della salute", "impresa individuale"],
)
def test_professionisti_e_autonomi_non_per_parole_sciolte(testo):
    assert "professionista_autonomo" not in tipi_da_termini(testo)


def test_le_regole_usano_i_confini_di_parola():
    # "privati" dentro un'altra parola non e' il soggetto generico
    assert tipi_da_termini("privatizzati", GENERICI) == set()
    assert tipi_da_termini("soggetti ospitanti privati", GENERICI) == set(TIPI_PRIVATI)


def test_soggetti_generici_solo_tra_i_generici():
    # le regole specifiche non comprendono i soggetti generici
    assert tipi_da_termini("soggetti ospitanti privati") == set()
    assert tipi_da_termini("datori di lavoro", GENERICI) == set(TIPI_PRIVATI)
    assert tipi_da_termini("soggetti pubblici", GENERICI) == set(TIPI_PUBBLICI)
    tutti = set(TIPI_BENEFICIARIO) - {PER_REQUISITO}
    for testo in (
        "Altri soggetti pubblici e/o privati",
        "soggetti pubblici o privati",
        "enti pubblici e privati",
        "un soggetto pubblico o privato",
    ):
        assert tipi_da_termini(testo, GENERICI) == tutti, testo


def test_organismi_formativi_e_enti_di_formazione():
    assert tipi_da_termini("organismi formativi accreditati") == {"ricerca_formazione"}
    assert tipi_da_termini("enti di formazione") == {"ricerca_formazione"}


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


def _riga(**altro) -> dict:
    return {
        "id": "tpl",
        "titolo": "TPL",
        "ente": "Regione",
        "a_sportello": 0,
        "beneficiari": "Enti locali competenti.",
        **altro,
    }


def _leggi(percorso, sql):
    c = sqlite3.connect(percorso)
    try:
        return c.execute(sql).fetchall()
    finally:
        c.close()


def test_salva_con_beneficiari_li_scrive_e_segna_la_classificazione(db_su_file):
    beneficiari = [
        {
            "tipo": "comune",
            "soggetto": "Enti locali competenti",
            "condizioni": "competenti",
            "frase": "Enti locali competenti.",
            "confidenza": "alta",
            "origine": "estrazione",
        }
    ]
    salva(
        _riga(beneficiari_ammessi=beneficiari, interventi=[]),
        f"{BASE}/-/tpl",
        "prova",
        "regione-toscana",
    )

    assert _leggi(
        db_su_file, "SELECT id_bando, tipo, condizioni, origine FROM beneficiari_bando"
    ) == [("tpl", "comune", "competenti", "estrazione")]
    assert _leggi(db_su_file, "SELECT classificato_il IS NOT NULL FROM bandi") == [(1,)]


def test_salva_senza_beneficiari_non_tocca_le_tabelle_collegate(db_su_file):
    salva(_riga(), f"{BASE}/-/tpl", "prova", "regione-toscana")
    c = sqlite3.connect(db_su_file)
    c.execute(
        "INSERT INTO beneficiari_bando (id_bando, tipo, frase, origine) "
        "VALUES ('tpl', 'unione_comuni', 'Enti locali competenti.', 'estrazione')"
    )
    c.execute("INSERT INTO interventi_bando VALUES ('tpl', 1, 'spesa', 'autobus', 'x')")
    c.execute("UPDATE bandi SET classificato_il = '2026-11-11'")
    c.commit()
    c.close()

    salva(_riga(titolo="TPL aggiornato"), f"{BASE}/-/tpl", "prova", "regione-toscana")

    assert _leggi(db_su_file, "SELECT tipo, origine FROM beneficiari_bando") == [
        ("unione_comuni", "estrazione")
    ]
    assert len(_leggi(db_su_file, "SELECT * FROM interventi_bando")) == 1
    assert _leggi(db_su_file, "SELECT classificato_il FROM bandi") == [("2026-11-11",)]
