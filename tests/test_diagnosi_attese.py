"""Diagnosi delle attese: archivio, recupero, esclusione, su JSON sintetici."""

import csv
import json

import pytest

from scripts.diagnostica import diagnosi_attese as d

BASE = "https://www.regione.toscana.it/-/"
DATA_PROVA = "2026-11-16"


@pytest.fixture
def db(conn):
    """Il database in memoria del conftest con una fonte e quattro bandi."""
    conn.execute(
        "INSERT INTO fonti (codice, nome, url_base, schema_link, fonte, "
        "verificato_il) VALUES ('regione-toscana', 'Toscana', ?, '^/-/', 'prova', "
        "'2026-11-11')",
        (BASE,),
    )
    bando(
        conn, "strade", "Fondo investimenti stradali nei piccoli Comuni", "2026-12-31"
    )
    bando(conn, "mercati", "Mercati rionali 2026", "2026-10-15")
    bando(conn, "sportello", "Credito per l’Appennino", None, a_sportello=1)
    bando(
        conn,
        "pagina",
        "Pagina informativa sui contributi alla montagna",
        None,
        natura="non_bando",
    )
    return conn


def bando(conn, id_bando, titolo, scadenza, **campi):
    riga = {
        "id": id_bando,
        "titolo": titolo,
        "ente": "Regione Toscana",
        "scadenza": scadenza,
        "a_sportello": 0,
        "url": BASE + id_bando,
        "fonte": "prova",
        "codice_fonte": "regione-toscana",
        "verificato_il": "2026-11-11",
        **campi,
    }
    conn.execute(
        f"INSERT INTO bandi ({', '.join(riga)}) "
        f"VALUES ({', '.join('?' for _ in riga)})",
        list(riga.values()),
    )


def voce(attese=(), vietate=(), dati="", citati=(), **campi):
    """Una voce di domanda come la salva prova_insieme."""
    return {
        "gruppo": "comuni",
        "codice": "C99",
        "domanda": "Quali bandi?",
        "attese": list(attese),
        "vietate": list(vietate),
        "a_mano": [],
        "dati": dati,
        "risposta": "Risposta.",
        "bandi_citati": [
            {"testo": "", "fonte": "D1.1", "titolo": t, "url": ""} for t in citati
        ],
        **campi,
    }


def categorie(db, v, oggi=DATA_PROVA):
    diagnosi, _ = d.diagnosi_voce(db, v, oggi)
    return {x.testo: x.categoria for x in diagnosi}


# --- Categorie ---


def test_ok_se_citata(db):
    v = voce(
        attese=["Fondo investimenti stradali"],
        dati="[D1.1] Fondo investimenti stradali nei piccoli Comuni",
        citati=["Fondo investimenti stradali nei piccoli Comuni"],
    )
    assert categorie(db, v) == {"Fondo investimenti stradali": d.OK}


def test_esclusione_se_nei_dati_ma_non_citata(db):
    v = voce(
        attese=["Fondo investimenti stradali"],
        dati="[D1.1] Fondo investimenti stradali nei piccoli Comuni",
    )
    diagnosi, _ = d.diagnosi_voce(db, v, DATA_PROVA)
    assert diagnosi[0].categoria == d.ESCLUSIONE
    assert diagnosi[0].nei_dati and not diagnosi[0].citata


def test_recupero_se_in_archivio_aperto_e_non_nei_dati(db):
    v = voce(attese=["Fondo investimenti stradali"], dati="[D1.1] Altro bando")
    diagnosi, _ = d.diagnosi_voce(db, v, DATA_PROVA)
    assert diagnosi[0].categoria == d.RECUPERO
    assert [(t.id, t.stato) for t in diagnosi[0].titoli] == [("strade", d.APERTO)]


def test_archivio_scaduto_se_tutti_scaduti_alla_data_della_prova(db):
    v = voce(attese=["mercati rionali"])
    diagnosi, _ = d.diagnosi_voce(db, v, DATA_PROVA)
    assert diagnosi[0].categoria == d.ARCHIVIO_SCADUTO
    assert diagnosi[0].titoli[0].stato == d.SCADUTO


def test_lo_stato_segue_la_data_della_prova(db, tmp_path):
    """Lo stesso bando: recupero prima della scadenza, archivio_scaduto dopo."""
    prima = registrazione(
        tmp_path / "lotto_1" / "prima", "2026-10-01", voce(attese=["mercati rionali"])
    )
    dopo = registrazione(
        tmp_path / "lotto_1" / "dopo", DATA_PROVA, voce(attese=["mercati rionali"])
    )
    assert d.diagnosi_cartella(db, prima).diagnosi[0].categoria == d.RECUPERO
    assert d.diagnosi_cartella(db, dopo).diagnosi[0].categoria == d.ARCHIVIO_SCADUTO


def test_sportello_aperto_e_recupero(db):
    v = voce(attese=["credito per l'appennino"])
    diagnosi, _ = d.diagnosi_voce(db, v, DATA_PROVA)
    assert diagnosi[0].categoria == d.RECUPERO
    assert diagnosi[0].titoli[0].stato == d.A_SPORTELLO


def test_archivio_se_non_e_un_titolo(db):
    v = voce(attese=["deve cercare anche nei bandi"], dati="[D1.1] Mercati rionali")
    diagnosi, _ = d.diagnosi_voce(db, v, DATA_PROVA)
    assert diagnosi[0].categoria == d.ARCHIVIO
    assert diagnosi[0].titoli == []


def test_archivio_non_bando_se_corrispondono_solo_righe_non_bando(db):
    v = voce(attese=["contributi alla montagna"])
    diagnosi, _ = d.diagnosi_voce(db, v, DATA_PROVA)
    assert diagnosi[0].categoria == d.ARCHIVIO_NON_BANDO
    assert diagnosi[0].titoli[0].natura == "non_bando"
    assert "natura non_bando" in diagnosi[0].titoli[0].descrizione()


def test_non_bando_contato_ma_non_decide(db):
    """Un bando scaduto e una riga non_bando aperta: archivio_scaduto."""
    bando(db, "mercati-pagina", "Mercati rionali, pagina", None, natura="non_bando")
    diagnosi, _ = d.diagnosi_voce(db, voce(attese=["mercati rionali"]), DATA_PROVA)
    assert len(diagnosi[0].titoli) == 2
    assert diagnosi[0].categoria == d.ARCHIVIO_SCADUTO


def test_piu_titoli_uno_aperto_e_uno_scaduto_danno_recupero(db):
    bando(db, "mercati-2027", "Mercati rionali 2027", "2027-03-31")
    diagnosi, _ = d.diagnosi_voce(db, voce(attese=["mercati rionali"]), DATA_PROVA)
    assert [(t.id, t.stato) for t in diagnosi[0].titoli] == [
        ("mercati", d.SCADUTO),
        ("mercati-2027", d.APERTO),
    ]
    assert diagnosi[0].categoria == d.RECUPERO


def test_corrispondenza_come_controlla_attese(db):
    """Apostrofo tipografico e maiuscole, nei dati, nei citati e in archivio."""
    v = voce(
        attese=["CREDITO PER L'APPENNINO"],
        dati="[D1.1] Credito per l’Appennino",
        citati=["Credito per l’Appennino"],
    )
    diagnosi, _ = d.diagnosi_voce(db, v, DATA_PROVA)
    assert diagnosi[0].categoria == d.OK
    assert len(diagnosi[0].titoli) == 1


def test_errore_se_la_voce_non_ha_risposta(db):
    v = voce(attese=["Fondo investimenti stradali"], errore="RuntimeError: x")
    del v["risposta"]
    assert categorie(db, v) == {"Fondo investimenti stradali": d.ERRORE}


# --- Vietate ---


def test_vietata_citata_e_non_citata(db):
    v = voce(
        vietate=["mercati rionali", "Fondo investimenti stradali"],
        dati="[D1.1] Mercati rionali 2026; Fondo investimenti stradali",
        citati=["Mercati rionali 2026"],
    )
    assert categorie(db, v) == {
        "mercati rionali": d.VIETATA_CITATA,
        "Fondo investimenti stradali": d.VIETATA_NON_CITATA,
    }


# --- Registrazioni e uscita ---


def registrazione(cartella, data_di_oggi, *voci):
    (cartella / "domande").mkdir(parents=True)
    codici = []
    for numero, v in enumerate(voci):
        v = {**v, "codice": f"C{numero:02d}"}
        codici.append(v["codice"])
        (cartella / "domande" / f"{v['codice']}.json").write_text(
            json.dumps(v, ensure_ascii=False), encoding="utf-8"
        )
    meta = {
        "lotto": 1,
        "data_di_oggi": data_di_oggi,
        "commit": "abc1234",
        "codici": codici,
    }
    (cartella / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return cartella


def test_cartella_senza_data_della_prova(db, tmp_path):
    cartella = tmp_path / "lotto_1" / "x"
    cartella.mkdir(parents=True)
    (cartella / "meta.json").write_text("{}", encoding="utf-8")
    with pytest.raises(d.ErroreDiagnosi):
        d.diagnosi_cartella(db, cartella)


def test_voci_senza_attese_saltate(db, tmp_path):
    cartella = registrazione(
        tmp_path / "lotto_1" / "r",
        DATA_PROVA,
        voce(),
        voce(attese=["mercati rionali"]),
    )
    r = d.diagnosi_cartella(db, cartella)
    assert r.voci == 2
    assert [x.codice for x in r.diagnosi] == ["C01"]
    assert r.nome == "lotto_1/r"


def test_scrive_rapporto_e_csv_con_i_totali(db, tmp_path):
    cartella = registrazione(
        tmp_path / "lotto_1" / "r",
        DATA_PROVA,
        voce(attese=["Fondo investimenti stradali", "deve cercare anche nei bandi"]),
        voce(
            attese=["mercati rionali"],
            vietate=["Credito"],
            citati=["Credito per l’Appennino"],
        ),
    )
    registrazioni = [d.diagnosi_cartella(db, cartella)]
    titoli = [d.diagnosi_titolo(db, "Fondo investimenti", DATA_PROVA)]
    uscita = d.scrivi_uscita(tmp_path / "uscita", registrazioni, titoli)

    with (uscita / "diagnosi.csv").open(encoding="utf-8") as f:
        righe = list(csv.DictReader(f))
    assert [r["categoria"] for r in righe] == [
        d.RECUPERO,
        d.ARCHIVIO,
        d.ARCHIVIO_SCADUTO,
        d.VIETATA_CITATA,
        d.IN_ARCHIVIO,
    ]
    assert righe[0]["n_titoli"] == "1"

    testo = (uscita / "rapporto.md").read_text(encoding="utf-8")
    assert "| recupero | 1 | 1 |" in testo
    assert "| archivio | 1 | 1 |" in testo
    assert "lotto_1/r C00: deve cercare anche nei bandi" in testo
    assert "lotto_1/r C01: Credito" in testo
    assert "Titoli cercati (--titolo)" in testo


# --- Opzione --titolo ---


def test_titolo_controlla_solo_l_archivio(db):
    aperto = d.diagnosi_titolo(db, "fondo investimenti stradali", DATA_PROVA)
    assert aperto.categoria == d.IN_ARCHIVIO
    assert aperto.nei_dati is None and aperto.citata is None
    assert d.diagnosi_titolo(db, "mercati rionali", DATA_PROVA).categoria == (
        d.ARCHIVIO_SCADUTO
    )
    assert d.diagnosi_titolo(db, "bando inesistente", DATA_PROVA).categoria == (
        d.ARCHIVIO
    )


def test_opzione_titolo_ripetibile(db, tmp_path, monkeypatch):
    monkeypatch.setattr(d, "apri_in_lettura", lambda: db)
    monkeypatch.setattr(d, "CARTELLA_DIAGNOSI", tmp_path)
    uscita = d.main(["--titolo", "contributi alla montagna", "--titolo", "nessuno"])
    with (uscita / "diagnosi.csv").open(encoding="utf-8") as f:
        righe = list(csv.DictReader(f))
    assert [(r["tipo"], r["categoria"]) for r in righe] == [
        ("titolo", d.ARCHIVIO_NON_BANDO),
        ("titolo", d.ARCHIVIO),
    ]


def test_senza_cartelle_ne_titoli_errore():
    with pytest.raises(SystemExit):
        d.leggi_argomenti([])
