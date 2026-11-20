"""Caricamento degli avvisi in Chroma (compito 19c-3), senza Chroma e senza rete.

Il database è quello in memoria di tests/conftest.py; al posto di Chroma
un archivio finto con get, delete e add_documents; al posto del
tokenizzatore del modello uno che conta le parole.
"""

import csv
import subprocess
import sys
from datetime import date

import pytest
from langchain_core.documents import Document

import scripts.ingestione.carica_avvisi as script
from scripts.ingestione.elenco_pdf_bandi import cartella_file
from scripts.ingestione.registra_avvisi import COLONNE
from src.estrazione import pdf_bando as pb
from src.ingestion.avvisi import NOME_OMESSO

ID = "bando-prova"
TITOLO = "Bando di prova per i Comuni"


@pytest.fixture
def db(conn):
    conn.execute(
        "INSERT INTO fonti (codice, nome, url_base, schema_link, fonte, verificato_il) "
        "VALUES ('fonte-prova', 'Fonte di prova', 'https://www.prova.it', '^/x$', "
        "'prova', '2026-11-20')"
    )
    for id_bando, scadenza, url in (
        (ID, "2026-12-05", "https://www.prova.it/a"),
        ("bando-vecchio", "2025-10-01", "https://www.prova.it/b"),
        ("bando-recente", "2026-11-10", "https://www.prova.it/c"),
        ("bando-senza-scadenza", None, "https://www.prova.it/d"),
        ("bando-con-date", "2025-01-01", "https://www.prova.it/e"),
    ):
        conn.execute(
            "INSERT INTO bandi (id, titolo, ente, scadenza, url, fonte, codice_fonte, "
            "verificato_il) VALUES (?, ?, 'Regione di prova', ?, ?, 'Fonte di prova', "
            "'fonte-prova', '2026-11-20')",
            (id_bando, TITOLO if id_bando == ID else id_bando, scadenza, url),
        )
    conn.execute(
        "INSERT INTO scadenze_bando (id_bando, numero, genere, descrizione, scadenza, "
        "frase) VALUES ('bando-con-date', 2, 'domanda', 'seconda finestra', "
        "'2026-10-01', 'entro il 1 ottobre 2026')"
    )
    return conn


class Tokenizer:
    """Una parola, un token; [CLS] e [SEP] come nel modello vero."""

    def __call__(self, testo, return_offsets_mapping=False):
        import re

        parole = [(m.start(), m.end()) for m in re.finditer(r"\S+", testo)]
        offset = [(0, 0), *parole, (0, 0)]
        return {"input_ids": list(range(len(offset))), "offset_mapping": offset}


class Archivio:
    """Al posto di Chroma: get con un where di uguaglianza, delete, add_documents."""

    def __init__(self):
        self.dati: dict[str, Document] = {}

    def get(self, where=None, include=None):
        ids = [
            i
            for i, d in self.dati.items()
            if not where or all(d.metadata.get(k) == v for k, v in where.items())
        ]
        return {"ids": ids, "metadatas": [self.dati[i].metadata for i in ids]}

    def delete(self, ids):
        for i in ids:
            del self.dati[i]

    def add_documents(self, documents, ids):
        self.dati.update(zip(ids, documents, strict=True))


def riga_registro(**valori):
    riga = dict.fromkeys(COLONNE, "")
    riga.update(
        sha256="a" * 64,
        id_bandi=ID,
        classe=pb.AVVISO,
        uso="frammenti",
        atto="Decreto n. 100 del 01/02/2026, Allegato A",
        nome_file="avviso-prova.pdf",
        scaricato_il="2026-11-19",
    )
    riga.update(valori)
    return riga


PARAGRAFO = (
    "Possono presentare domanda i Comuni con popolazione fino a 5.000 abitanti "
    "per interventi sulle strade comunali. Il contributo massimo è di 40.000,00 euro. "
)
PAGINE = [
    PARAGRAFO * 4,
    PARAGRAFO * 2
    + "\nResponsabile del procedimento (RUP) è Tizio Caio in qualità di RUP.\n",
]


# --- controllo dei numeri ---


@pytest.mark.parametrize(
    "frammento, pagina",
    [
        pytest.param("B B1 40.000,00", "B B1 40.000,00", id="uguale"),
        pytest.param("entro il 2026", "entro il 202 6", id="anno ricucito"),
        pytest.param("legge 41/2022", "legge 41/202 2", id="numero con anno ricucito"),
        pytest.param("Reg. 1060/2021", "Reg. 1 060/2021", id="numero con /anno"),
        pytest.param("artt. 5 3, 14", "artt. 5 3, 14", id="non ricucito"),
        pytest.param("punti 4", "punti\u00a0\t 4", id="spazi normalizzati"),
    ],
)
def test_numeri_che_passano(frammento, pagina):
    assert script.numeri_non_trovati(frammento, pagina) == []


@pytest.mark.parametrize(
    "frammento, pagina, mancanti",
    [
        pytest.param(
            "B B140.000,00", "B B1 40.000,00", ["140.000,00"], id="celle fuse"
        ),
        pytest.param("punti 5090", "punti 50 90", ["5090"], id="punteggi fusi"),
        pytest.param("artt. 53,14", "artt. 5 3, 14", ["53,14"], id="articoli fusi"),
        pytest.param("nel 14", "nel 2014", ["14"], id="dentro un numero più lungo"),
        pytest.param(
            "Reg. 2021/21154",
            "Reg. 2021/ 2115 4",
            ["2021/21154"],
            id="barra e cella fusa",
        ),
    ],
)
def test_numeri_che_non_passano(frammento, pagina, mancanti):
    assert script.numeri_non_trovati(frammento, pagina) == mancanti


@pytest.mark.parametrize(
    "frammento, pagina, alla_barra",
    [
        pytest.param(
            "Reg. 2021/2115",
            "Reg. 2021/ 2115",
            [("2021/2115", "2021/ 2115")],
            id="dopo",
        ),
        pytest.param(
            "DM 30/3/2015 n. 52",
            "DM 30/3 /2015 n. 52",
            [("30/3/2015", "30/3 /2015")],
            id="prima",
        ),
        pytest.param(
            "Reg. 2021/2116",
            "Reg. 2021\t/ 2116",
            [("2021/2116", "2021 / 2116")],
            id="spazi di ogni tipo",
        ),
    ],
)
def test_ricuciti_alla_barra(frammento, pagina, alla_barra):
    """Passano il controllo, ma il rapporto li elenca a parte."""
    assert script.controlla_numeri(frammento, pagina) == ([], alla_barra)


def test_numero_fuso_vero_resta_non_trovato():
    """L'eccezione della barra non copre le celle fuse."""
    assert script.controlla_numeri("B B140.000,00", "B B1 40.000,00") == (
        ["140.000,00"],
        [],
    )


def test_spazi_solo_tra_due_cifre():
    # "n. 41/ 2022" ha la barra tra cifre; "art. 3 / bis" no
    assert script.controlla_numeri("art. 3/2022", "art. 3 / bis 2022") == (
        ["3/2022"],
        [],
    )


# --- misure ---


def test_tabella_probabile():
    tabella = "Tab. 1\nLINEA A1\nMicro e piccola\nimpresa\n20%\nMedia impresa 10%"
    assert script.tabella_probabile(tabella)
    assert not script.tabella_probabile(PARAGRAFO * 3)
    assert not script.tabella_probabile("a)\nb)\nc)\nd)\ne)")


def test_misura_token():
    corto = "una frase breve"
    assert script.misura_token(Tokenizer(), corto) == (5, len(corto))
    lungo = " ".join(f"p{i}" for i in range(200))
    token, visti = script.misura_token(Tokenizer(), lungo)
    assert token == 202
    assert lungo[:visti].split()[-1] == "p125"  # 126 parole viste


# --- registro e file ---


def scrivi_registro(percorso, righe):
    with percorso.open("w", encoding="utf-8-sig", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=COLONNE)
        scrittore.writeheader()
        scrittore.writerows(righe)
    return percorso


def test_registro_solo_frammenti(tmp_path):
    percorso = scrivi_registro(
        tmp_path / "r.csv",
        [riga_registro(), riga_registro(sha256="b" * 64, uso="solo_registro")],
    )
    assert [r["sha256"] for r in script.leggi_registro(percorso)] == ["a" * 64]


def test_registro_file_per_piu_bandi(tmp_path):
    percorso = scrivi_registro(tmp_path / "r.csv", [riga_registro(id_bandi="x|y")])
    with pytest.raises(script.ErroreCaricamento, match="più bandi"):
        script.leggi_registro(percorso)


def test_file_con_impronta_diversa(tmp_path):
    riga = riga_registro()
    cartella = cartella_file(tmp_path / riga["scaricato_il"], ID)
    cartella.mkdir(parents=True)
    (cartella / riga["nome_file"]).write_bytes(b"%PDF-1.4 altro")
    with pytest.raises(script.ErroreCaricamento, match="impronta"):
        script.percorso_del_file(riga, tmp_path)
    (cartella / riga["nome_file"]).unlink()
    with pytest.raises(script.ErroreCaricamento, match="non trovato"):
        script.percorso_del_file(riga, tmp_path)


# --- frammenti di un file ---


METADATI = {
    "page",
    "chunk_num",
    "id_bando",
    "titolo",
    "ente",
    "tipo_documento",
    "riferimento_atto",
    "fonte",
    "sha256",
    "parte",
    "token",
    "car_visti",
    "tabella_probabile",
}


def test_frammenti_e_metadati(db):
    esito = script.frammenti_del_file(riga_registro(), PAGINE, db, Tokenizer())
    assert esito.frammenti
    for d in esito.frammenti:
        assert set(d.metadata) == METADATI
        assert d.metadata["titolo"] == TITOLO
        assert d.metadata["ente"] == "Regione di prova"
        assert d.metadata["tipo_documento"] == pb.AVVISO
        assert (
            d.metadata["riferimento_atto"]
            == "Decreto n. 100 del 01/02/2026, Allegato A"
        )
        # l'intestazione non entra nel testo
        assert not d.page_content.startswith(TITOLO)
    assert [d.metadata["chunk_num"] for d in esito.frammenti] == list(
        range(len(esito.frammenti))
    )
    assert esito.numeri_mancanti == []
    assert esito.pagine_lette == 2


def test_contatti_tolti_dai_frammenti(db):
    esito = script.frammenti_del_file(riga_registro(), PAGINE, db, Tokenizer())
    testo = " ".join(d.page_content for d in esito.frammenti)
    assert "Tizio" not in testo and NOME_OMESSO in testo
    assert [(p, s.tipo) for p, s in esito.contatti] == [(2, "nome")]


def test_numeri_fusi_si_vedono(db, monkeypatch):
    """Con la ricucitura completa il controllo trova il numero fuso."""
    vera = script.spezza
    monkeypatch.setattr(
        script, "spezza", lambda pagine, ricucitura: vera(pagine, ricucitura="completa")
    )
    pagine = [PARAGRAFO * 3 + "\nAzione B1 40.000,00 euro\n"]
    esito = script.frammenti_del_file(riga_registro(), pagine, db, Tokenizer())
    assert [m[2] for m in esito.numeri_mancanti] == ["140.000,00"]


def test_ricuciti_alla_barra_nel_rapporto(db):
    pagine = [PARAGRAFO * 3 + "\nai sensi del Reg. (UE) 2021/ 2115 e successive\n"]
    esito = script.frammenti_del_file(riga_registro(), pagine, db, Tokenizer())
    assert esito.numeri_mancanti == []
    assert [(p, n, t) for _, p, n, t in esito.ricuciti_barra] == [
        (1, "2021/2115", "2021/ 2115")
    ]
    righe = script.rapporto_totale([esito])
    assert "Controllo dei numeri: 0 non trovati nel testo grezzo della pagina" in righe
    assert "Ricuciti alla barra: 1" in righe
    assert any("2021/2115" in r and "«2021/ 2115»" in r for r in righe)


def test_bando_non_in_archivio(db):
    with pytest.raises(script.ErroreCaricamento, match="non in archivio"):
        script.frammenti_del_file(
            riga_registro(id_bandi="altro"), PAGINE, db, Tokenizer()
        )


def test_identificatori(db):
    esito = script.frammenti_del_file(riga_registro(), PAGINE, db, Tokenizer())
    assert script.identificatori(esito.frammenti)[:2] == [
        f"{'a' * 16}::0",
        f"{'a' * 16}::1",
    ]


# --- scrittura e rilancio ---


def test_rilancio_senza_doppioni(db):
    archivio = Archivio()
    altro = Document(page_content="altro documento", metadata={"fonte": "vecchio.pdf"})
    archivio.add_documents([altro], ["vecchio.pdf::0"])
    esito = script.frammenti_del_file(riga_registro(), PAGINE, db, Tokenizer())
    assert script.scrivi(archivio, esito) == (0, len(esito.frammenti))
    assert script.scrivi(archivio, esito) == (
        len(esito.frammenti),
        len(esito.frammenti),
    )
    assert len(archivio.dati) == len(esito.frammenti) + 1
    # un file che ora produce meno frammenti non ne lascia di vecchi
    meno = script.frammenti_del_file(riga_registro(), PAGINE[:1], db, Tokenizer())
    assert len(meno.frammenti) < len(esito.frammenti)
    script.scrivi(archivio, meno)
    assert len(archivio.dati) == len(meno.frammenti) + 1
    assert "vecchio.pdf::0" in archivio.dati


# --- bandi scaduti ---


def frammento(id_bando, **altri):
    return Document(page_content="x", metadata={"id_bando": id_bando, **altri})


def test_scaduti_solo_oltre_i_giorni(db):
    archivio = Archivio()
    for i, id_bando in enumerate(
        ("bando-vecchio", "bando-recente", "bando-senza-scadenza", "bando-con-date", ID)
    ):
        archivio.add_documents([frammento(id_bando, sha256=str(i))], [f"{i}::0"])
    # un documento di sempre, senza sha256, non si tocca mai
    archivio.add_documents([frammento("bando-vecchio")], ["vecchio.pdf::0"])
    oggi = date(2026, 11, 20)
    assert script.scaduti_da_togliere(archivio, db, oggi, 365) == {
        "bando-vecchio": ["0::0"]
    }
    assert script.scaduti_da_togliere(archivio, db, oggi, 5) == {
        "bando-con-date": ["3::0"],
        "bando-recente": ["1::0"],
        "bando-vecchio": ["0::0"],
    }


def test_ultima_scadenza_con_piu_date(db):
    assert script.ultima_scadenza(db, "bando-con-date") == "2026-10-01"
    assert script.ultima_scadenza(db, "bando-senza-scadenza") is None


def test_senza_opzione_non_si_toglie_nulla():
    argomenti = script.leggi_argomenti([])
    assert not argomenti.togli_scaduti and not argomenti.prova
    assert argomenti.giorni == 365
    assert script.leggi_argomenti(["--togli-scaduti", "--giorni", "30"]).giorni == 30


# --- rete e Postgres ---


def test_senza_rete(monkeypatch):
    for nome in script.SENZA_RETE:
        monkeypatch.delenv(nome, raising=False)
    script.senza_rete()
    import os

    assert os.environ["HF_HUB_OFFLINE"] == "1"
    assert os.environ["TRANSFORMERS_OFFLINE"] == "1"
    assert os.environ["ANONYMIZED_TELEMETRY"] == "False"


def test_nessun_import_di_postgres():
    """Lo script e il lettore dei PDF non caricano pgstore né psycopg."""
    codice = (
        "import sys\n"
        "import scripts.ingestione.carica_avvisi\n"
        "import src.ingestion.pdf_ingest\n"
        "print(sorted(m for m in sys.modules if m == 'src.pgstore' "
        "or m.startswith('psycopg')))\n"
    )
    uscita = subprocess.run(
        [sys.executable, "-c", codice], capture_output=True, text=True, check=True
    )
    assert uscita.stdout.strip().splitlines()[-1] == "[]"
