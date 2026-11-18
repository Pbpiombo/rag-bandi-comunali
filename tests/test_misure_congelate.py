"""Data fissa e archivio congelato per le misure (passo 0 della roadmap).

Gli archivi sono cartelle di CSV scritte dal test in tmp_path; i database
si ricreano da lì con crea_da_csv, mai in data/db.
"""

import csv
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pytest
from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from scripts.diagnostica import prova_insieme as p
from scripts.diagnostica import schede_etichette
from src.chains import rag
from src.config import ROOT_DIR
from src.database import interrogazioni_bandi, repertorio, schema
from src.database.interrogazioni_bandi import data_di_oggi, data_fissata
from src.database.schema import (
    TABELLE_DA_CSV,
    ErroreArchivio,
    archivio_da,
    connetti,
    crea_da_csv,
)
from tests.test_prova_insieme import domande, esito_catena_finto, prepara_registra_finto

ENTE = "11111111111"
BASE = "https://www.regione.toscana.it/-/"


def scrivi_archivio(cartella: Path, bandi: dict[str, str], orfani: int = 0) -> Path:
    """Una cartella con tutti i CSV di TABELLE_DA_CSV: un Comune, una fonte,
    i bandi dati (id -> scadenza) aperti ai Comuni.

    orfani: righe di beneficiari_bando di bandi che non esistono, che il
    caricamento scarta.
    """
    righe = {t: [] for t in TABELLE_DA_CSV}
    righe["enti"].append(
        {
            "codice_fiscale": ENTE,
            "nome": "Comune di prova",
            "tipo": "comune",
            "regione": "Toscana",
            "provincia": "Pistoia",
            "fonte": "prova",
            "verificato_il": "2026-01-01",
        }
    )
    righe["fonti"].append(
        {
            "codice": "regione-toscana",
            "nome": "Toscana",
            "url_base": BASE,
            "schema_link": "^/-/",
            "fonte": "prova",
            "verificato_il": "2026-11-11",
        }
    )
    for id_bando, scadenza in bandi.items():
        righe["bandi"].append(
            {
                "id": id_bando,
                "titolo": f"Bando {id_bando}",
                "ente": "Regione Toscana",
                "beneficiari": "Comuni",
                "scadenza": scadenza,
                "a_sportello": "0",
                "url": BASE + id_bando,
                "fonte": "prova",
                "codice_fonte": "regione-toscana",
                "verificato_il": "2026-11-11",
                "classificato_il": "2026-11-11",
            }
        )
        righe["beneficiari_bando"].append(
            {
                "id_bando": id_bando,
                "tipo": "comune",
                "frase": "Possono partecipare i Comuni.",
                "origine": "estrazione",
            }
        )
    for numero in range(orfani):
        righe["beneficiari_bando"].append(
            {
                "id_bando": f"inesistente-{numero}",
                "tipo": "comune",
                "frase": "Possono partecipare i Comuni.",
                "origine": "estrazione",
            }
        )
    cartella.mkdir(parents=True, exist_ok=True)
    for tabella, colonne in TABELLE_DA_CSV.items():
        with (cartella / f"{tabella}.csv").open(
            "w", encoding="utf-8-sig", newline=""
        ) as f:
            scrittore = csv.DictWriter(f, fieldnames=colonne)
            scrittore.writeheader()
            scrittore.writerows(righe[tabella])
    return cartella


def titoli_aperti() -> list[str]:
    """I bandi aperti per l'ente, con la stessa strada del router: connetti()."""
    risultato = repertorio.esegui("bandi_aperti_per_ente", {}, ENTE)
    return sorted(v.titolo for v in risultato.voci)


# La data "vera" nei test: date.today() di interrogazioni_bandi, fissata
OGGI_VERO = date(2030, 1, 15)


class DataVera(date):
    @classmethod
    def today(cls):
        return cls(OGGI_VERO.year, OGGI_VERO.month, OGGI_VERO.day)


@pytest.fixture
def oggi_vero(monkeypatch):
    """data_di_oggi senza data fissata restituisce OGGI_VERO."""
    monkeypatch.setattr(interrogazioni_bandi, "date", DataVera)
    return OGGI_VERO


@pytest.fixture
def archivio(tmp_path):
    """Un database ricreato da un archivio con un bando che scade il 20/11."""
    cartella = scrivi_archivio(tmp_path / "csv", {"parcheggi": "2026-11-20"})
    percorso = tmp_path / "congelato" / "archivio.sqlite"
    crea_da_csv(percorso, cartella)
    return percorso


# --- Data fissa ---


def test_data_fissata_vale_per_chi_importa_il_nome(oggi_vero):
    giorno = date(2026, 11, 16)
    with data_fissata(giorno):
        assert interrogazioni_bandi.data_di_oggi() == giorno
        assert repertorio.data_di_oggi() == giorno
        assert rag.data_di_oggi() == giorno
        with data_fissata(date(2026, 12, 1)):
            assert rag.data_di_oggi() == date(2026, 12, 1)
        assert rag.data_di_oggi() == giorno
    assert rag.data_di_oggi() == oggi_vero


def test_alla_data_vale_anche_per_rag():
    """alla_data sostituiva il nome solo in interrogazioni_bandi e repertorio."""
    with schede_etichette.alla_data(date(2026, 11, 16)):
        assert rag.data_di_oggi() == date(2026, 11, 16)


def test_stato_dei_frammenti_alla_data_fissata(archivio):
    """con_stato_del_giorno in rag.py calcola lo stato alla data fissata."""
    frammento = Document(
        page_content="Il contributo è pari all'80%.",
        metadata={"ente": "Regione Toscana", "page": 1, "id_bando": "parcheggi"},
    )
    with archivio_da(archivio):
        with data_fissata(date(2026, 11, 16)):
            prima = rag.con_stato_del_giorno([frammento])
        with data_fissata(date(2026, 12, 1)):
            dopo = rag.con_stato_del_giorno([frammento])

    assert prima[0].metadata["stato_bando"].startswith("aperto, scade il 2026-11-20")
    assert dopo[0].metadata["stato_bando"] == (
        "scaduto il 2026-11-20 (alla data del 2026-12-01)"
    )


# --- Archivio congelato ---


def test_le_interrogazioni_leggono_l_archivio_indicato(tmp_path):
    uno = tmp_path / "uno.sqlite"
    due = tmp_path / "due.sqlite"
    crea_da_csv(uno, scrivi_archivio(tmp_path / "a", {"strade": "2027-01-31"}))
    crea_da_csv(due, scrivi_archivio(tmp_path / "b", {"scuole": "2027-01-31"}))

    with data_fissata(date(2026, 11, 16)):
        with archivio_da(uno):
            primo = titoli_aperti()
            with archivio_da(due):
                secondo = titoli_aperti()
            di_nuovo = titoli_aperti()

    assert primo == ["Bando strade"]
    assert secondo == ["Bando scuole"]
    assert di_nuovo == ["Bando strade"]


def test_crea_da_csv_conta_caricate_e_scartate(tmp_path, capsys):
    cartella = scrivi_archivio(tmp_path / "csv", {"strade": "2027-01-31"}, orfani=2)
    conteggi = crea_da_csv(tmp_path / "db.sqlite", cartella)

    assert conteggi["bandi"] == {"caricate": 1, "scartate": 0}
    assert conteggi["beneficiari_bando"] == {"caricate": 1, "scartate": 2}
    assert set(conteggi) == set(TABELLE_DA_CSV)
    assert p.scartate(conteggi) == {"beneficiari_bando": 2}


def test_crea_da_csv_rifiuta_un_csv_mancante(tmp_path):
    cartella = scrivi_archivio(tmp_path / "csv", {})
    (cartella / "scadenze_bando.csv").unlink()
    destinazione = tmp_path / "db.sqlite"

    with pytest.raises(ErroreArchivio, match="scadenze_bando"):
        crea_da_csv(destinazione, cartella)
    assert not destinazione.exists()


def test_crea_da_csv_non_tocca_data_db(tmp_path):
    cartella = scrivi_archivio(tmp_path / "csv", {})
    vero = ROOT_DIR / "data" / "db" / "comune.sqlite"
    prima = vero.stat().st_mtime_ns if vero.exists() else None

    for destinazione in (vero, vero.parent / "prova_congelata.sqlite"):
        with pytest.raises(ErroreArchivio, match="data/db"):
            crea_da_csv(destinazione, cartella)
    assert not (vero.parent / "prova_congelata.sqlite").exists()
    assert (vero.stat().st_mtime_ns if vero.exists() else None) == prima


def test_crea_da_csv_non_sovrascrive(tmp_path):
    cartella = scrivi_archivio(tmp_path / "csv", {})
    destinazione = tmp_path / "db.sqlite"
    destinazione.write_bytes(b"gia' qui")

    with pytest.raises(ErroreArchivio, match="esiste"):
        crea_da_csv(destinazione, cartella)
    assert destinazione.read_bytes() == b"gia' qui"


def test_archivio_da_vuole_un_file_esistente(tmp_path):
    with pytest.raises(ErroreArchivio):
        with archivio_da(tmp_path / "manca.sqlite"):
            pass
    assert not (tmp_path / "manca.sqlite").exists()


# --- Senza opzioni: nessun cambiamento ---


def percorso_aperto(conn: sqlite3.Connection) -> Path:
    return Path(conn.execute("PRAGMA database_list").fetchone()[2])


def test_senza_contesti_data_vera_e_database_vero(
    tmp_path, monkeypatch, archivio, oggi_vero
):
    vero = tmp_path / "vero.sqlite"
    monkeypatch.setattr(schema, "SQLITE_PATH", vero)

    assert data_di_oggi() == oggi_vero
    conn = connetti()
    assert percorso_aperto(conn) == vero
    conn.close()

    with archivio_da(archivio), data_fissata(date(2026, 11, 16)):
        pass
    assert data_di_oggi() == oggi_vero
    conn = connetti()
    assert percorso_aperto(conn) == vero
    conn.close()


def test_l_app_e_la_catena_non_fissano_data_ne_archivio():
    """Data e archivio si fissano solo da codice: l'app non li nomina."""
    nomi = ("data_fissata", "archivio_da", "_DATA_FISSA", "_PERCORSO_ALTERNATIVO")
    definiti = {
        ROOT_DIR / "src" / "database" / "interrogazioni_bandi.py",
        ROOT_DIR / "src" / "database" / "schema.py",
    }
    file = [*(ROOT_DIR / "app").rglob("*.py"), *(ROOT_DIR / "src").rglob("*.py")]
    trovati = [
        f"{f.relative_to(ROOT_DIR)}: {n}"
        for f in file
        if f not in definiti
        for n in nomi
        if n in f.read_text(encoding="utf-8")
    ]
    assert trovati == []


# --- Cartella temporanea dell'archivio congelato ---


def test_archivio_congelato_cancella_la_cartella(tmp_path, capsys):
    cartella = scrivi_archivio(tmp_path / "csv", {"strade": "2027-01-31"})

    with p.archivio_congelato(cartella) as conteggi:
        conn = connetti()
        temporanea = percorso_aperto(conn).parent
        conn.close()

    assert conteggi["bandi"]["caricate"] == 1
    assert not temporanea.exists()
    assert "AVVISO" not in capsys.readouterr().out


def test_archivio_congelato_con_connessione_aperta_avvisa_e_basta(tmp_path, capsys):
    """Su Windows il file aperto non si cancella: avviso, nessun errore."""
    cartella = scrivi_archivio(tmp_path / "csv", {"strade": "2027-01-31"})

    with p.archivio_congelato(cartella):
        aperta = connetti()
        temporanea = percorso_aperto(aperta).parent

    uscita = capsys.readouterr().out
    if sys.platform == "win32":
        assert "AVVISO: cartella temporanea non cancellata" in uscita
        assert temporanea.exists()
    aperta.close()
    shutil.rmtree(temporanea, ignore_errors=True)


def test_archivio_congelato_con_csv_mancante_e_un_errore_della_prova(tmp_path):
    cartella = scrivi_archivio(tmp_path / "csv", {})
    (cartella / "enti.csv").unlink()

    with pytest.raises(p.ErroreProva, match="enti"):
        with p.archivio_congelato(cartella):
            pass


# --- prova_insieme: --data e --archivio ---


def registra_finto(tmp_path, monkeypatch):
    """registra senza modello; la catena finta annota data e archivio che vede."""
    prepara_registra_finto(tmp_path / "prova", monkeypatch, domande()[:2])
    # impronta_csv vera: con --archivio si calcola su quella cartella
    monkeypatch.setattr(p, "impronta_csv", IMPRONTA_CSV)
    visti = []

    def catena_di_prova():
        conn = connetti()
        try:
            bandi = [r[0] for r in conn.execute("SELECT id FROM bandi")]
        finally:
            conn.close()
        visti.append((data_di_oggi(), bandi))
        return RunnableLambda(esito_catena_finto), p.RouterTriplo(None), "finto"

    monkeypatch.setattr(p, "costruisci_catena_di_prova", catena_di_prova)
    return visti


IMPRONTA_CSV = p.impronta_csv


def test_registra_con_data_e_archivio(tmp_path, monkeypatch, capsys, oggi_vero):
    visti = registra_finto(tmp_path, monkeypatch)
    cartella_csv = scrivi_archivio(tmp_path / "csv", {"strade": "2027-01-31"})

    registrazione = p.registra(1, data=date(2026, 11, 16), archivio=cartella_csv)

    meta = p.leggi_json(registrazione / "meta.json")
    assert visti == [(date(2026, 11, 16), ["strade"])]
    assert meta["data_di_oggi"] == "2026-11-16"
    assert meta["data_fissata"] == "2026-11-16"
    assert meta["archivio"] == str(cartella_csv.resolve())
    assert meta["impronta_csv"] == IMPRONTA_CSV(cartella_csv)
    assert meta["archivio_scartate"] == {}
    assert "avvisi_misura" not in meta
    rapporto = (registrazione / "rapporto.md").read_text(encoding="utf-8")
    assert f"- CSV di {cartella_csv.resolve()}:" in rapporto
    assert "- data di oggi: 2026-11-16 (fissata);" in rapporto
    assert "ATTENZIONE" not in capsys.readouterr().out
    # All'uscita, data vera
    assert data_di_oggi() == oggi_vero


def test_la_ripresa_rilegge_data_e_archivio_dal_meta(tmp_path, monkeypatch):
    visti = registra_finto(tmp_path, monkeypatch)
    cartella_csv = scrivi_archivio(tmp_path / "csv", {"strade": "2027-01-31"})
    registrazione = p.registra(1, data=date(2026, 11, 16), archivio=cartella_csv)
    # Interrotta dopo la prima domanda
    meta = p.leggi_json(registrazione / "meta.json")
    meta["stato"] = "incompleta"
    p.scrivi_json(registrazione / "meta.json", meta)
    ultimo = sorted((registrazione / "domande").glob("*.json"))[-1]
    ultimo.unlink()

    p.registra(1, riprendi=registrazione)

    assert visti[-1] == (date(2026, 11, 16), ["strade"])
    assert ultimo.exists()
    meta = p.leggi_json(registrazione / "meta.json")
    assert meta["riprese"][-1]["data_di_oggi"] == "2026-11-16"
    assert (
        meta["riprese"][-1]["impronta_csv"]
        == (IMPRONTA_CSV(cartella_csv)["complessiva"])
    )


def test_registra_con_righe_scartate_le_scrive_e_le_stampa(
    tmp_path, monkeypatch, capsys
):
    registra_finto(tmp_path, monkeypatch)
    cartella_csv = scrivi_archivio(tmp_path / "csv", {"strade": "2027-01-31"}, 1)

    registrazione = p.registra(1, data=date(2026, 11, 16), archivio=cartella_csv)

    meta = p.leggi_json(registrazione / "meta.json")
    assert meta["archivio_scartate"] == {"beneficiari_bando": 1}
    assert "righe scartate dai CSV: {'beneficiari_bando': 1}" in (
        capsys.readouterr().out
    )
    rapporto = (registrazione / "rapporto.md").read_text(encoding="utf-8")
    assert "righe scartate dai CSV" in rapporto


@pytest.mark.parametrize(
    ("opzioni", "parola"),
    [({"archivio": True}, "manca --data"), ({"data": True}, "manca --archivio")],
)
def test_una_sola_opzione_avvisa_prima_e_nel_rapporto(
    tmp_path, monkeypatch, capsys, opzioni, parola
):
    visti = registra_finto(tmp_path, monkeypatch)
    cartella_csv = scrivi_archivio(tmp_path / "csv", {"strade": "2027-01-31"})
    argomenti = {
        "data": date(2026, 11, 16) if opzioni.get("data") else None,
        "archivio": cartella_csv if opzioni.get("archivio") else None,
    }

    registrazione = p.registra(1, **argomenti)

    uscita = capsys.readouterr().out
    assert uscita.index(parola) < uscita.index("Lotto 1,")
    meta = p.leggi_json(registrazione / "meta.json")
    assert parola in meta["avvisi_misura"][0]
    rapporto = (registrazione / "rapporto.md").read_text(encoding="utf-8")
    assert f"**ATTENZIONE**: {meta['avvisi_misura'][0]}" in rapporto
    assert len(visti) == 1


def test_registra_senza_opzioni_come_prima(tmp_path, monkeypatch, capsys, oggi_vero):
    prepara_registra_finto(tmp_path, monkeypatch, domande()[:2])

    registrazione = p.registra(1)

    meta = p.leggi_json(registrazione / "meta.json")
    assert meta["data_di_oggi"] == oggi_vero.isoformat()
    assert meta["data_fissata"] is None
    assert meta["archivio"] is None
    assert "archivio_scartate" not in meta
    assert "avvisi_misura" not in meta
    assert "ATTENZIONE" not in capsys.readouterr().out
    rapporto = (registrazione / "rapporto.md").read_text(encoding="utf-8")
    assert "- CSV di data/processed:" in rapporto


def test_registra_con_archivio_senza_csv_non_crea_la_registrazione(
    tmp_path, monkeypatch
):
    registra_finto(tmp_path, monkeypatch)
    cartella_csv = scrivi_archivio(tmp_path / "csv", {})
    (cartella_csv / "bandi.csv").unlink()

    with pytest.raises(p.ErroreProva, match="bandi"):
        p.registra(1, data=date(2026, 11, 16), archivio=cartella_csv)
    assert not (tmp_path / "prova" / "lotto_1").exists()


@pytest.mark.parametrize(
    "argomenti",
    [
        ["--stima", "--lotto", "1", "--data", "2026-11-16"],
        ["--riepilogo", "--archivio", "x"],
        ["--registra", "--lotto", "1", "--riprendi", "x", "--data", "2026-11-16"],
        ["--registra", "--lotto", "1", "--riprendi", "x", "--archivio", "x"],
        ["--registra", "--lotto", "1", "--data", "16/11/2026"],
    ],
)
def test_data_e_archivio_solo_con_registra_e_senza_riprendi(argomenti):
    with pytest.raises(SystemExit):
        p.main(argomenti)
