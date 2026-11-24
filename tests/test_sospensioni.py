"""Sospensioni dei bandi (sospensioni_bando): stato, elenchi, conteggi,
etichetta dei frammenti, correzioni a mano, copia congelata, ricognizione.

Dati finti, nel database in memoria di conftest o in quello temporaneo su
file (db_su_file): mai il database vero.
"""

import sqlite3

import pytest
from langchain_core.documents import Document

import scripts.ingestione.ricognizione as ricognizione
import scripts.manutenzione.correggi_da_testo as cdt
from src.chains.rag import etichetta
from src.database import interrogazioni_bandi as ib
from src.database.repertorio import _stato_bandi
from src.database.schema import crea_da_csv
from src.database.stato_documenti import con_stato_bando, stato_bando
from tests.conftest import CON_DATI as COMUNE
from tests.test_interrogazioni_bandi import BASE, DataFissa, bando
from tests.test_misure_congelate import scrivi_archivio
from tests.test_ricognizione import OGGI as OGGI_RICOGNIZIONE
from tests.test_ricognizione import _in_archivio

# La data di DataFissa (test_interrogazioni_bandi)
OGGI = "2026-11-11"
IMPRESE = (("altra_impresa", None, "imprese"),)
COMUNI = (("comune", None, "Comuni"),)


@pytest.fixture
def db(conn, monkeypatch):
    """Il database di prova con una fonte, nessun bando, la data fissata."""
    monkeypatch.setattr(ib, "date", DataFissa)
    conn.execute(
        "INSERT INTO fonti (codice, nome, url_base, schema_link, fonte, "
        "verificato_il) VALUES ('regione-toscana', 'Toscana', ?, '^/-/', 'prova', "
        "'2026-11-11')",
        (BASE,),
    )
    return conn


def sospendi(conn, id_bando, ambito="tutto", dal="2026-07-08", numero=1, **campi):
    """Inserisce un periodo di sospensione."""
    riga = {
        "id_bando": id_bando,
        "numero": numero,
        "ambito": ambito,
        "sospeso_dal": dal,
        "sospesi": "under 30 disoccupati" if ambito == "in_parte" else None,
        "resta_aperto": "solo per persone con disabilità"
        if ambito == "in_parte"
        else None,
        "atto": "decreto 742/2026",
        "frase": "La sospensione decorre dal 8 luglio 2026",
        "verificato_il": "2026-11-23",
        **campi,
    }
    conn.execute(
        f"INSERT INTO sospensioni_bando ({', '.join(riga)}) "
        f"VALUES ({', '.join('?' for _ in riga)})",
        list(riga.values()),
    )


def righe_con(testo: str, id_bando: str) -> list[str]:
    return [r for r in testo.splitlines() if f"«Bando {id_bando}»" in r]


def riga_bando(conn, id_bando):
    return conn.execute("SELECT * FROM bandi WHERE id = ?", (id_bando,)).fetchone()


# --- sospeso del tutto ----------------------------------------------------------


def test_sospeso_del_tutto_fuori_dagli_aperti_e_in_coda(db):
    bando(db, "aperto", COMUNI)
    bando(db, "fermo", COMUNI)
    sospendi(db, "fermo")

    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    assert "1 in archivio" in testo.splitlines()[0]
    gruppi = testo.split(f"\n{ib.GRUPPO_SOSPESI}\n")
    assert len(gruppi) == 2
    assert righe_con(gruppi[0], "fermo") == []
    assert (
        righe_con(gruppi[1], "fermo")[0]
        .split(" | ")[1]
        .startswith("SOSPESO dal 2026-07-08 (decreto 742/2026): per tutti")
    )


def test_sospeso_del_tutto_non_si_conta_nel_riepilogo(db):
    bando(db, "aperto", COMUNI)
    bando(db, "fermo", COMUNI)
    sospendi(db, "fermo")

    testo = _stato_bandi(db, COMUNE)

    assert "di cui 1 aperti" in testo
    assert testo.endswith(", più 1 sospesi del tutto")


def test_sospeso_del_tutto_fuori_da_in_scadenza(db):
    bando(db, "fermo", COMUNI, scadenza="2026-11-30")
    sospendi(db, "fermo")

    risultato = ib.bandi_in_scadenza(db, COMUNE)

    assert not risultato.trovato
    assert "fermo" not in risultato.testo


def test_sospeso_del_tutto_per_beneficiario_e_per_tema(db):
    bando(db, "aperto", IMPRESE, tema="lavoro")
    bando(db, "fermo", IMPRESE, tema="lavoro")
    sospendi(db, "fermo")

    per_tipo = ib.bandi_per_beneficiario(db, "altra_impresa").testo
    assert "1 in archivio" in per_tipo.splitlines()[0]
    assert righe_con(per_tipo.split(ib.GRUPPO_SOSPESI)[1], "fermo")

    per_tema = ib.bandi_per_tema(db, "lavoro")
    aperti, sospesi = per_tema.testo.split(ib.GRUPPO_SOSPESI)
    assert righe_con(aperti, "fermo") == []
    assert righe_con(sospesi, "fermo")
    assert len(per_tema.voci) == len(per_tema.fonti) == 2


def test_solo_sospesi_del_tutto_nessun_aperto_ma_elencati(db):
    bando(db, "fermo", COMUNI)
    sospendi(db, "fermo")

    risultato = ib.bandi_aperti_per_ente(db, COMUNE)

    assert risultato.testo.startswith("Nessun bando aperto ora per i Comuni")
    assert righe_con(risultato.testo, "fermo")
    assert len(risultato.voci) == len(risultato.fonti) == 1


# --- sospeso in parte -----------------------------------------------------------


def test_sospeso_in_parte_resta_tra_gli_aperti_con_l_avviso(db):
    bando(db, "parte", COMUNI, scadenza="2026-12-31")
    sospendi(db, "parte", ambito="in_parte")

    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    assert "1 in archivio" in testo.splitlines()[0]
    assert ib.GRUPPO_SOSPESI not in testo
    pezzi = righe_con(testo, "parte")[0].split(" | ")
    assert pezzi[1] == (
        "SOSPESO IN PARTE dal 2026-07-08 (decreto 742/2026): sospeso per under 30 "
        "disoccupati; resta aperto solo per persone con disabilità"
    )
    assert pezzi[2] == "per la parte non sospesa: scade il 2026-12-31 (fra 50 giorni)"
    assert "di cui 1 aperti" in _stato_bandi(db, COMUNE)


def test_la_sospensione_viene_prima_di_ogni_aperto(db):
    bando(db, "parte", COMUNI, scadenza="2027-01-10", a_sportello=1)
    sospendi(db, "parte", ambito="in_parte")
    riga = ib.formatta_bando(
        riga_bando(db, "parte"), OGGI, sospensioni=ib.sospensioni_di(db, "parte")
    )
    assert riga.index("SOSPESO IN PARTE") < riga.index("a sportello fino al")


# --- date della sospensione -----------------------------------------------------


def test_sospensione_con_data_futura_non_vale_ancora(db):
    bando(db, "futura", COMUNI)
    sospendi(db, "futura", dal="2026-11-12")
    riga = riga_bando(db, "futura")

    assert ib.formatta_bando(
        riga, OGGI, sospensioni=ib.sospensioni_di(db, "futura")
    ) == ib.formatta_bando(riga, OGGI)
    assert "1 in archivio" in ib.bandi_aperti_per_ente(db, COMUNE).testo


def test_sospensione_dal_giorno_stesso_vale(db):
    bando(db, "oggi", COMUNI)
    sospendi(db, "oggi", dal=OGGI)
    assert ib.sospeso_del_tutto(ib.sospensioni_di(db, "oggi"), OGGI)


def test_il_giorno_della_riapertura_non_e_piu_sospeso(db):
    bando(db, "riaperto", COMUNI)
    sospendi(
        db,
        "riaperto",
        riaperto_il=OGGI,
        riapertura_frase="Riapertura del bando con decreto 841",
    )
    sospensioni = ib.sospensioni_di(db, "riaperto")
    riga = riga_bando(db, "riaperto")

    assert ib.sospensioni_attive(sospensioni, OGGI) == []
    assert ib.sospensioni_attive(sospensioni, "2026-11-10") != []
    assert ib.formatta_bando(riga, OGGI, sospensioni=sospensioni) == (
        ib.formatta_bando(riga, OGGI)
    )
    assert "1 in archivio" in ib.bandi_aperti_per_ente(db, COMUNE).testo


def test_lo_schema_rifiuta_una_sospensione_in_parte_senza_cosa_resta_aperto(db):
    bando(db, "parte", COMUNI)
    with pytest.raises(sqlite3.IntegrityError):
        sospendi(db, "parte", ambito="in_parte", resta_aperto=None)


# --- etichetta dei frammenti ----------------------------------------------------


def test_l_etichetta_dei_frammenti_porta_la_sospensione(db):
    bando(db, "parte", COMUNI, scadenza="2026-12-31")
    sospendi(db, "parte", ambito="in_parte")
    documento = Document(
        page_content="Testo dell'avviso.", metadata={"id_bando": "parte", "page": 1}
    )

    (con_stato,) = con_stato_bando([documento], db, OGGI)

    assert con_stato.metadata["stato_bando"].startswith(
        "SOSPESO IN PARTE dal 2026-07-08"
    )
    assert "stato del bando: SOSPESO IN PARTE" in etichetta(con_stato, 1)
    riga = riga_bando(db, "parte")
    assert stato_bando(riga, [], OGGI) == "aperto, scade il 2026-12-31 (fra 50 giorni)"


# --- correzioni a mano ----------------------------------------------------------

ID = "bando-sospeso"
FRASE = "La sospensione decorre dal 8 luglio 2026, data di pubblicazione del decreto."
RIAPERTURA = "Riapertura del bando con decreto 841 del 14 ottobre 2026."
TESTO = f"Titolo\n{FRASE}\nSospensione per gli under 30 disoccupati.\n{RIAPERTURA}\n"


@pytest.fixture
def con_bando(db):
    bando(db, ID, COMUNI)
    return db


def aggiunta(testo, frase=FRASE, frasi=("under 30 disoccupati",)) -> cdt.Aggiunta:
    return cdt.Aggiunta(
        tabella="sospensioni_bando",
        riga={
            "id_bando": ID,
            "numero": 1,
            "ambito": "in_parte",
            "sospeso_dal": "2026-07-08",
            "sospesi": "under 30 disoccupati",
            "resta_aperto": "solo per persone con disabilità",
            "atto": "decreto 742/2026",
            "frase": frase,
            "verificato_il": "2026-11-23",
            "origine": "manuale",
        },
        frasi=frasi,
        testo=testo,
    )


def riapertura(testo, frase=RIAPERTURA) -> cdt.Correzione:
    return cdt.Correzione(
        tabella="sospensioni_bando",
        riga={"id_bando": ID, "numero": 1},
        attesi={"riaperto_il": None, "riapertura_frase": None},
        corretti={"riaperto_il": "2026-10-24", "riapertura_frase": frase},
        frasi=(),
        testo=testo,
    )


def quante(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM sospensioni_bando").fetchone()[0]


def test_correggi_aggiunge_una_sospensione_con_le_frasi_trovate(con_bando, tmp_path):
    esito = cdt.aggiungi(con_bando, aggiunta(tmp_path), TESTO, prova=False)
    assert esito.startswith("aggiunta")
    assert quante(con_bando) == 1


@pytest.mark.parametrize(
    ("frase", "frasi", "motivo"),
    [
        ("Frase che nella pagina non c'e'.", ("under 30 disoccupati",), "non trovate"),
        (FRASE, ("over 55 disoccupati",), "non trovate"),
        ("", ("under 30 disoccupati",), "vuota"),
        (None, ("under 30 disoccupati",), "vuota"),
        (FRASE, ("  ",), "vuota"),
    ],
)
def test_correggi_rifiuta_una_sospensione_senza_frase(
    con_bando, tmp_path, frase, frasi, motivo
):
    esito = cdt.aggiungi(
        con_bando, aggiunta(tmp_path, frase, frasi), TESTO, prova=False
    )
    assert esito.startswith("SALTATO") and motivo in esito
    assert quante(con_bando) == 0


def test_correggi_applica_una_riapertura_con_la_frase_trovata(con_bando, tmp_path):
    cdt.aggiungi(con_bando, aggiunta(tmp_path), TESTO, prova=False)
    esito = cdt.correggi(con_bando, riapertura(tmp_path), TESTO, prova=False)
    assert esito.startswith("corretto")
    assert ib.sospensioni_attive(ib.sospensioni_di(con_bando, ID), "2026-11-11") == []


@pytest.mark.parametrize(
    ("frase", "motivo"),
    [("Riapertura che nella pagina non c'e'.", "non trovate"), ("", "vuota")],
)
def test_correggi_rifiuta_una_riapertura_senza_frase(
    con_bando, tmp_path, frase, motivo
):
    cdt.aggiungi(con_bando, aggiunta(tmp_path), TESTO, prova=False)
    esito = cdt.correggi(con_bando, riapertura(tmp_path, frase), TESTO, prova=False)
    assert esito.startswith("SALTATO") and motivo in esito
    assert (
        con_bando.execute(
            "SELECT riaperto_il FROM sospensioni_bando WHERE id_bando = ?", (ID,)
        ).fetchone()[0]
        is None
    )


# --- copia congelata e ricognizione ---------------------------------------------


def test_crea_da_csv_accetta_una_copia_senza_le_sospensioni(tmp_path):
    cartella = scrivi_archivio(tmp_path / "csv", {"strade": "2027-01-31"})
    (cartella / "sospensioni_bando.csv").unlink()

    conteggi = crea_da_csv(tmp_path / "db.sqlite", cartella)

    assert conteggi["sospensioni_bando"] == {"caricate": 0, "scartate": 0}
    assert conteggi["bandi"] == {"caricate": 1, "scartate": 0}
    c = sqlite3.connect(tmp_path / "db.sqlite")
    assert c.execute("SELECT COUNT(*) FROM sospensioni_bando").fetchone()[0] == 0
    c.close()


def test_la_ricognizione_rilegge_anche_i_sospesi_del_tutto(db_su_file):
    _in_archivio("fermo", "fermo", "2027-01-10")
    _in_archivio("aperto", "aperto", "2027-01-10")
    c = sqlite3.connect(db_su_file)
    c.execute("PRAGMA foreign_keys = ON")
    sospendi(c, "fermo")
    c.commit()
    c.close()

    ids = [r["id"] for r in ricognizione.bandi_da_ricontrollare(OGGI_RICOGNIZIONE)]

    assert ids == ["aperto", "fermo"]
