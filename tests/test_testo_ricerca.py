"""Test del testo di ricerca per bando (passo 17 della roadmap).

CSV e catalogo finti in una cartella temporanea: mai i dati veri.
"""

import csv
import random
import sqlite3
from pathlib import Path

import pytest

import scripts.manutenzione.crea_testo_ricerca as script
from src.database.schema import CSV_FUORI_DATABASE, DDL, TABELLE_DA_CSV
from src.ordinamento import testo_ricerca as tr

RADICE = Path(__file__).resolve().parent.parent

DATA = "2026-11-12"
FONTE_INC = f"Incentivi Italia, OpenData_Incentivi.csv del {DATA}, CC BY 4.0"
FONTE_RT = "Portale bandi Regione Toscana"

BANDI = [
    {
        "id": "rifugi",
        "titolo": "Contributi ai rifugi alpini",
        "fonte": FONTE_RT,
        "codice_fonte": "regione-toscana",
    },
    {
        "id": "solo-titolo",
        "titolo": "Premi per la cultura.",
        "fonte": FONTE_RT,
        "codice_fonte": "regione-toscana",
    },
    {
        "id": "incentivi-900001",
        "titolo": "Bando nazionale per il turismo",
        "fonte": FONTE_INC,
        "codice_fonte": "incentivi-italia",
    },
]

INTERVENTI = [
    {
        "id_bando": "rifugi",
        "numero": "10",
        "genere": "spesa",
        "descrizione": "Impianti fotovoltaici",
        "frase": "installazione di impianti\nfotovoltaici sul tetto",
    },
    {
        "id_bando": "rifugi",
        "numero": "2",
        "genere": "spesa",
        "descrizione": "Ristrutturazione dei locali",
        "frase": "ristrutturazione dei locali",
    },
]

COLONNE_CATALOGO = [
    "ID_Incentivo",
    "Titolo",
    "Descrizione",
    "Forma_agevolazione",
    "Obiettivo_Finalita",
    "Settore_Attivita",
]

CATALOGO = [
    {
        "ID_Incentivo": "900001",
        "Titolo": "Bando nazionale per il turismo",
        "Descrizione": "Cos'è Un sostegno alle strutture\nricettive.",
        "Forma_agevolazione": "Contributo a fondo perduto",
        "Obiettivo_Finalita": "Sostegno investimenti\\,Transizione ecologica",
        "Settore_Attivita": "Alberghiero\\,Turismo",
    },
    {
        "ID_Incentivo": "900002",
        "Titolo": "Un altro incentivo",
        "Descrizione": "Non riguarda i nostri bandi.",
        "Forma_agevolazione": "Garanzia",
        "Obiettivo_Finalita": "Innovazione e ricerca",
        "Settore_Attivita": "ICT",
    },
]


def scrivi_csv(percorso: Path, righe: list[dict], colonne: list[str]) -> Path:
    with percorso.open("w", encoding="utf-8-sig", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=colonne)
        scrittore.writeheader()
        scrittore.writerows(righe)
    return percorso


def archivio(cartella: Path, bandi=BANDI, interventi=INTERVENTI) -> Path:
    cartella.mkdir(parents=True, exist_ok=True)
    scrivi_csv(cartella / "bandi.csv", bandi, ["id", "titolo", "fonte", "codice_fonte"])
    scrivi_csv(
        cartella / "interventi_bando.csv",
        interventi,
        ["id_bando", "numero", "genere", "descrizione", "frase"],
    )
    return cartella


def catalogo(cartella: Path, righe=CATALOGO, colonne=COLONNE_CATALOGO) -> Path:
    (cartella / DATA).mkdir(parents=True, exist_ok=True)
    return scrivi_csv(cartella / DATA / "OpenData_Incentivi.csv", righe, colonne)


@pytest.fixture
def dati(tmp_path) -> tuple[Path, Path]:
    return archivio(tmp_path / "processed"), catalogo(tmp_path / "grezzi")


def per_id(righe: list[dict]) -> dict[str, dict]:
    return {r["id_bando"]: r for r in righe}


# --- composizione del testo ---


def test_titolo_e_interventi_in_ordine_di_numero(dati):
    cartella, file_catalogo = dati
    riga = per_id(tr.costruisci(cartella, file_catalogo, DATA))["rifugi"]
    assert riga["testo"] == (
        "Contributi ai rifugi alpini. Ristrutturazione dei locali. "
        "Impianti fotovoltaici. installazione di impianti fotovoltaici sul tetto"
    )
    assert riga["parti"] == "titolo;interventi"


def test_frase_uguale_alla_descrizione_omessa():
    testo, _ = tr.testo_bando(
        "Titolo",
        [{"numero": "1", "descrizione": "Acquisto  mezzi", "frase": "acquisto mezzi"}],
        None,
    )
    assert testo == "Titolo. Acquisto mezzi"


def test_catalogo_senza_forma_agevolazione(dati):
    cartella, file_catalogo = dati
    riga = per_id(tr.costruisci(cartella, file_catalogo, DATA))["incentivi-900001"]
    assert riga["testo"] == (
        "Bando nazionale per il turismo. Cos'è Un sostegno alle strutture "
        "ricettive. Sostegno investimenti, Transizione ecologica. "
        "Alberghiero, Turismo"
    )
    assert "fondo perduto" not in riga["testo"]
    assert "\\," not in riga["testo"]
    assert riga["parti"] == "titolo;catalogo"


def test_nessun_a_capo_nel_testo(dati):
    cartella, file_catalogo = dati
    for riga in tr.costruisci(cartella, file_catalogo, DATA):
        assert "\n" not in riga["testo"] and "\r" not in riga["testo"]


def test_fonti_e_licenza_per_i_tre_casi(dati):
    cartella, file_catalogo = dati
    righe = per_id(tr.costruisci(cartella, file_catalogo, DATA))

    con_interventi = righe["rifugi"]
    assert con_interventi["fonte_titolo"] == FONTE_RT
    assert con_interventi["fonte_interventi"] == FONTE_RT
    assert con_interventi["fonte_catalogo"] == ""
    assert con_interventi["licenza_catalogo"] == ""
    assert con_interventi["data_catalogo"] == ""

    solo_titolo = righe["solo-titolo"]
    assert solo_titolo["testo"] == "Premi per la cultura"
    assert solo_titolo["parti"] == "titolo"
    assert solo_titolo["fonte_titolo"] == FONTE_RT
    assert solo_titolo["fonte_interventi"] == ""

    del_catalogo = righe["incentivi-900001"]
    assert del_catalogo["fonte_titolo"] == FONTE_INC
    assert del_catalogo["fonte_interventi"] == ""
    assert del_catalogo["fonte_catalogo"] == (
        f"Incentivi Italia, OpenData_Incentivi.csv del {DATA}"
    )
    assert del_catalogo["licenza_catalogo"] == "CC BY 4.0"
    assert del_catalogo["data_catalogo"] == DATA


def test_senza_bandi_del_catalogo_il_file_non_serve(tmp_path):
    cartella = archivio(tmp_path / "processed", bandi=BANDI[:2])
    assert [r["id_bando"] for r in tr.costruisci(cartella)] == ["rifugi", "solo-titolo"]


# --- errori: niente testo parziale ---


def test_errore_se_il_catalogo_manca(dati, tmp_path):
    cartella, _ = dati
    with pytest.raises(tr.ErroreTestoRicerca, match="file del catalogo non trovato"):
        tr.costruisci(cartella, tmp_path / "non-esiste.csv", DATA)
    with pytest.raises(tr.ErroreTestoRicerca, match="file del catalogo non trovato"):
        tr.costruisci(cartella, None, None)


def test_errore_se_la_data_del_file_e_diversa(dati):
    cartella, file_catalogo = dati
    with pytest.raises(tr.ErroreTestoRicerca, match="del 2026-11-20"):
        tr.costruisci(cartella, file_catalogo, "2026-11-20")


def test_errore_se_i_bandi_citano_date_diverse(tmp_path):
    altro = dict(
        BANDI[2], id="incentivi-900002", fonte=FONTE_INC.replace(DATA, "2026-10-01")
    )
    cartella = archivio(tmp_path / "processed", bandi=[*BANDI, altro])
    file_catalogo = catalogo(tmp_path / "grezzi")
    with pytest.raises(tr.ErroreTestoRicerca, match="date diverse"):
        tr.costruisci(cartella, file_catalogo, DATA)


def test_errore_se_la_fonte_non_ha_la_data(tmp_path):
    senza = dict(BANDI[2], fonte="Incentivi Italia")
    cartella = archivio(tmp_path / "processed", bandi=[senza], interventi=[])
    with pytest.raises(tr.ErroreTestoRicerca, match="senza la data"):
        tr.costruisci(cartella, catalogo(tmp_path / "grezzi"), DATA)


def test_errore_se_un_bando_manca_dal_catalogo(dati, tmp_path):
    cartella, _ = dati
    file_catalogo = catalogo(tmp_path / "ridotto", righe=CATALOGO[1:])
    with pytest.raises(tr.ErroreTestoRicerca, match="assenti.*900001"):
        tr.costruisci(cartella, file_catalogo, DATA)


def test_errore_se_manca_una_colonna_del_catalogo(dati, tmp_path):
    cartella, _ = dati
    colonne = [c for c in COLONNE_CATALOGO if c != "Settore_Attivita"]
    righe = [{c: r[c] for c in colonne} for r in CATALOGO]
    file_catalogo = catalogo(tmp_path / "senza-colonna", righe=righe, colonne=colonne)
    with pytest.raises(tr.ErroreTestoRicerca, match="Settore_Attivita"):
        tr.costruisci(cartella, file_catalogo, DATA)


# --- ripetibilita' ---


def test_stessi_dati_stessi_byte(dati, tmp_path):
    cartella, file_catalogo = dati
    primo = tr.in_byte(tr.costruisci(cartella, file_catalogo, DATA))

    # le righe dei CSV in ingresso in un altro ordine
    rimescolati = archivio(
        tmp_path / "rimescolati",
        bandi=random.Random(1).sample(BANDI, len(BANDI)),
        interventi=INTERVENTI[::-1],
    )
    secondo = tr.in_byte(tr.costruisci(rimescolati, file_catalogo, DATA))

    assert primo == secondo
    assert primo.startswith(b"\xef\xbb\xbfid_bando,testo,parti,")


# --- lo script ---


def test_script_scrive_e_controlla(dati):
    cartella, file_catalogo = dati
    argomenti = ["--file", str(file_catalogo)]

    assert script.main([*argomenti, "--controlla"], cartella=cartella) == 1
    assert script.main(argomenti, cartella=cartella) == 0
    scritto = (cartella / tr.NOME_FILE).read_bytes()
    assert scritto == tr.in_byte(tr.costruisci(cartella, file_catalogo, DATA))
    assert script.main([*argomenti, "--controlla"], cartella=cartella) == 0

    # stesse righe con fine riga diverse: non e' una differenza
    (cartella / tr.NOME_FILE).write_bytes(scritto.replace(b"\r\n", b"\n"))
    assert script.main([*argomenti, "--controlla"], cartella=cartella) == 0

    # un titolo cambiato rende il file vecchio
    bandi = [dict(BANDI[0], titolo="Titolo nuovo"), *BANDI[1:]]
    archivio(cartella, bandi=bandi)
    assert script.main([*argomenti, "--controlla"], cartella=cartella) == 1


def test_script_esce_con_errore_senza_catalogo(dati, capsys):
    cartella, _ = dati
    assert script.main([], cartella=cartella) == 1
    assert "file del catalogo non trovato" in capsys.readouterr().err
    assert not (cartella / tr.NOME_FILE).exists()


# --- il testo non va al modello ---


def test_testo_ricerca_fuori_dal_database():
    """Il testo non si carica in SQLite: nessuna interrogazione lo legge."""
    assert "testo_ricerca" in CSV_FUORI_DATABASE
    assert tr.NOME_FILE == "testo_ricerca.csv"
    assert "testo_ricerca" not in TABELLE_DA_CSV
    conn = sqlite3.connect(":memory:")
    conn.executescript(DDL)
    tabelle = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    conn.close()
    assert not any("ricerca" in t for t in tabelle)


def test_solo_l_ordinamento_legge_il_testo_di_ricerca():
    """In src/ e app/ solo src/ordinamento nomina il testo di ricerca.

    schema.py lo nomina in CSV_FUORI_DATABASE, per la copia congelata.
    Quando il passo 4 lo leggera', il nuovo lettore si aggiunge qui.
    """
    ammessi = {
        RADICE / "src" / "database" / "schema.py",
    }
    lettori = sorted(
        str(p.relative_to(RADICE))
        for cartella in ("src", "app")
        for p in (RADICE / cartella).rglob("*.py")
        if "testo_ricerca" in p.read_text(encoding="utf-8")
        and p not in ammessi
        and (RADICE / "src" / "ordinamento") not in p.parents
    )
    assert lettori == []
