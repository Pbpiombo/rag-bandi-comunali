"""Fonte Incentivi Italia (piano fonti, tappa 5), su righe e pagine inventate.

tests/dati/incentivi_prova.csv ha le colonne della sezione Incentivi del
file open data e righe inventate: nessuna riga del file vero entra nel
repository. Le pagine tests/pagine/incentivi-*.html sono pagine d'ente
inventate (vedi LEGGIMI.md). Nessun test usa la rete.
"""

import csv
import sqlite3
import urllib.error
from datetime import date
from pathlib import Path

import pytest

import scripts.ingestione.importa_incentivi as importa
from src.database.interrogazioni_bandi import descrivi_beneficiari, stato_sportello
from src.database.schema import DDL, connetti
from src.estrazione import incentivi as inc
from src.estrazione.beneficiari import TIPI_IMPRESA, TIPI_PUBBLICI

DATI = Path(__file__).parent / "dati" / "incentivi_prova.csv"
PAGINE = Path(__file__).parent / "pagine"
OGGI = date(2026, 11, 13)


def pagina(nome: str) -> str:
    return (PAGINE / f"incentivi-{nome}.html").read_text(encoding="utf-8")


@pytest.fixture
def righe() -> dict[str, inc.Incentivo]:
    return {i.id: i for i in inc.leggi_file(DATI)}


def esami(righe, altre_fonti=frozenset()) -> dict[str, inc.Esame]:
    condivisi = inc.link_condivisi(list(righe.values()))
    return {
        i.id: inc.esamina(i, OGGI, condivisi, set(altre_fonti)) for i in righe.values()
    }


class RobotsLiberi(inc.Robots):
    """Un robots.txt che permette tutto, senza rete."""

    def __init__(self) -> None:
        super().__init__(scarica=lambda url: "User-agent: *\nDisallow:\n")


def scarica_da(pagine: dict[str, str]):
    """Una rete finta: l'HTML per URL canonico; un URL non previsto fallisce."""
    scaricati = []

    def finto(url, timeout=30):
        scaricati.append(url)
        if url not in pagine:
            raise AssertionError(f"pagina scaricata senza motivo: {url}")
        return pagine[url]

    finto.scaricati = scaricati
    return finto


# --- lettura del file ---


def test_file_della_sezione_aiuti_e_rifiutato(tmp_path):
    aiuti = tmp_path / "aiuti.csv"
    aiuti.write_text(
        "Codice_Beneficiario,Denominazione_Beneficiario,Importo_Aiuto\n1,Prova,100\n",
        encoding="utf-8",
    )
    with pytest.raises(inc.FileNonValido, match="sezione Incentivi"):
        inc.leggi_file(aiuti)


def test_separatore_punto_e_virgola(tmp_path):
    with DATI.open(encoding="utf-8", newline="") as f:
        righe = list(csv.reader(f))
    altro = tmp_path / "punto_e_virgola.csv"
    with altro.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter=";").writerows(righe)

    assert [i.id for i in inc.leggi_file(altro)] == [i.id for i in inc.leggi_file(DATI)]


def test_colonne_lette_per_nome(tmp_path):
    with DATI.open(encoding="utf-8", newline="") as f:
        righe = list(csv.reader(f))
    # le stesse colonne in ordine inverso
    rovesciato = tmp_path / "rovesciato.csv"
    with rovesciato.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows([r[::-1] for r in righe])

    prima = inc.leggi_file(DATI)[0]
    dopo = inc.leggi_file(rovesciato)[0]
    assert (dopo.id, dopo.titolo, dopo.chiusura) == (
        prima.id,
        prima.titolo,
        prima.chiusura,
    )


def test_multivalore_divisi(righe):
    nazionale = righe["900001"]
    assert len(nazionale.regioni) == 20
    assert "Valle d'Aosta/Vallée d'Aoste" in nazionale.regioni
    assert nazionale.settori == ["Turismo", "Commercio"]
    assert righe["900003"].comuni == ["Abetone Cutigliano", "Pistoia"]
    # la virgola dentro un valore non divide
    assert righe["900008"].settori == ["Agricoltura, silvicoltura e pesca"]
    assert righe["900008"].tipologie == [
        "Impresa",
        "Cooperative/Associazioni Non Profit",
    ]


def test_importi_e_date(righe):
    nazionale = righe["900001"]
    assert nazionale.contributo_min is None  # 0.0 non e' un valore
    assert (nazionale.contributo_max, nazionale.costo_min) == (50000.0, 1000.0)
    assert nazionale.chiusura == date(2026, 12, 31)
    assert righe["900006"].chiusura is None


def test_comuni_dell_unione_come_nella_tabella_enti():
    enti = Path(__file__).parents[1] / "data" / "processed" / "enti.csv"
    with enti.open(encoding="utf-8-sig", newline="") as f:
        comuni = {
            r["nome"].removeprefix("Comune di ")
            for r in csv.DictReader(f)
            if r["tipo"] == "comune"
        }
    assert set(inc.COMUNI_TERRITORIO) == comuni


# --- regola territoriale e concedenti ---


def test_comuni_con_nomi_simili_non_passano(righe):
    e = esami(righe)
    assert (e["900002"].esito, e["900002"].motivo) == (
        inc.IGNORATA,
        "elenco di comuni senza i nostri",
    )
    assert e["900003"].esito == inc.PAGINA


def test_comune_di_altra_regione_con_tutte_le_regioni_e_scartato(righe):
    e = esami(righe)["900004"]
    assert (e.esito, e.classe) == (inc.IGNORATA, inc.ALTRO_TERRITORIO)


def test_senza_toscana_e_senza_i_nostri_comuni_e_ignorata(righe):
    assert esami(righe)["900013"].motivo == "fuori dalla Toscana"


def test_concedente_sconosciuto_da_verificare(righe):
    e = esami(righe)["900005"]
    assert e.esito == inc.DA_VERIFICARE
    assert e.motivo == "concedente non in tabella: Ente Inventato di Prova"


def test_concedente_con_maiuscole_diverse_stessa_classe():
    assert inc.classe_concedente("ministero  della CULTURA") == inc.NAZIONALE
    assert inc.classe_concedente("Ministero della Cultura - altro") is None


def test_nessun_concedente_in_due_classi():
    nomi = [inc.normalizza_nome(n) for nomi in inc.CONCEDENTI.values() for n in nomi]
    assert len(nomi) == len(set(nomi))


def test_scaduto_da_due_anni_ignorato_senza_scaricare(righe, monkeypatch):
    e = esami(righe)
    assert e["900007"].esito == inc.IGNORATA

    finto = scarica_da({})
    monkeypatch.setattr(importa, "scarica", finto)
    monkeypatch.setattr(inc, "_scarica_robots", lambda url: "")
    monkeypatch.setattr(importa, "PAUSA_PAGINE", 0)
    importa.controlla_pagine([e["900007"]])
    assert finto.scaricati == []


def test_storico_di_tre_mesi_passa(righe):
    e = esami(righe)["900008"]
    assert (e.stato, e.esito, e.classe) == (inc.STORICO, inc.PAGINA, inc.TERRITORIO)


def test_senza_date_da_verificare(righe):
    assert esami(righe)["900015"].motivo == "nessuna data nel catalogo"


def test_link_condiviso_da_verificare(righe):
    e = esami(righe)
    for id_ in ("900009", "900010"):
        assert e[id_].esito == inc.DA_VERIFICARE
        assert e[id_].motivo.startswith("Link_istituzionale usato da piu' righe")


def test_link_gia_in_archivio_da_altra_fonte_saltato(righe):
    url = righe["900003"].url
    assert esami(righe, {url})["900003"].esito == inc.GIA_IN_ARCHIVIO


def test_doppione_saltato_con_il_bando_tenuto(righe):
    riga = righe["900003"]
    condivisi = inc.link_condivisi(list(righe.values()))

    e = inc.esamina(riga, OGGI, condivisi, set(), {riga.url: "bando-della-regione"})

    assert e.esito == inc.GIA_IN_ARCHIVIO
    assert e.motivo == "doppione di bando-della-regione"


def test_doppione_registrato_in_scansioni_e_non_salvato(db_su_file, righe):
    riga = righe["900003"]
    condivisi = inc.link_condivisi(list(righe.values()))
    e = inc.esamina(riga, OGGI, condivisi, set(), {riga.url: "bando-della-regione"})

    importa.scrivi([e], inc.NOME_FONTE.format(data="2026-11-12"))

    conn = connetti()
    try:
        scansione = conn.execute(
            "SELECT esito, motivo FROM scansioni WHERE url = ?", (riga.url,)
        ).fetchone()
        salvati = conn.execute("SELECT count(*) FROM bandi").fetchone()[0]
    finally:
        conn.close()
    assert tuple(scansione) == ("scartato", "doppione di bando-della-regione")
    assert salvati == 0


def test_aperto_per_enti_pubblici_al_modello(righe):
    assert esami(righe)["900011"].esito == inc.AL_MODELLO


# --- controllo sulla pagina ---


@pytest.mark.parametrize(
    "testo",
    [
        "termine: 2026-12-31",
        "entro il 31/12/2026",
        "entro il 31.12.2026 ore 12",
        "entro il 31-12-2026",
        "entro il 31 dicembre 2026",
        "entro il 31 DICEMBRE 2026",
    ],
)
def test_data_trovata_in_ogni_forma(testo):
    assert inc.cerca_data(testo, date(2026, 12, 31)) == testo


def test_data_con_cifre_singole_e_primo_del_mese():
    assert inc.cerca_data("dal 1/3/2026", date(2026, 3, 1))
    assert inc.cerca_data("dal 01.03.2026", date(2026, 3, 1))
    assert inc.cerca_data("dal 1° marzo 2026", date(2026, 3, 1))


@pytest.mark.parametrize(
    "testo",
    ["entro il 13 dicembre 2026", "entro il 31/12/20265", "codice 131/12/2026"],
)
def test_data_con_i_confini_numerici(testo):
    giorno = date(2026, 12, 3) if "13 dicembre" in testo else date(2026, 12, 31)
    assert inc.cerca_data(testo, giorno) is None


def test_data_trovata_sulla_pagina_e_salvabile_con_la_prova(righe):
    e = esami(righe)["900001"]
    inc.controlla_pagina(e, lambda url: pagina("con-data"), RobotsLiberi())
    assert e.esito == inc.SALVABILE
    assert "entro le ore 12:00 del 31/12/2026" in e.prova


def test_data_assente_da_verificare(righe):
    e = esami(righe)["900001"]
    inc.controlla_pagina(e, lambda url: pagina("proroga"), RobotsLiberi())
    assert e.esito == inc.DA_VERIFICARE
    assert e.motivo == (
        "data di chiusura del catalogo (2026-12-31) non trovata sulla pagina"
    )


def test_sportello_aperto_da_piu_di_due_anni_da_verificare(righe):
    e = esami(righe)["900006"]
    assert (e.stato, e.esito) == (inc.SPORTELLO, inc.DA_VERIFICARE)
    assert e.motivo == (
        "sportello senza chiusura aperto da piu' di 2 anni (dal 2023-05-02)"
    )


def test_sportello_aperto_e_chiuso(righe):
    aperto = esami(righe)["900016"]
    assert aperto.esito == inc.PAGINA
    inc.controlla_pagina(aperto, lambda url: pagina("sportello"), RobotsLiberi())
    assert aperto.esito == inc.SALVABILE

    chiuso = esami(righe)["900016"]
    inc.controlla_pagina(chiuso, lambda url: pagina("sportello-chiuso"), RobotsLiberi())
    assert chiuso.esito == inc.DA_VERIFICARE
    assert "chiuso per esaurimento" in chiuso.motivo


def test_robots_che_vieta_non_scarica_la_pagina(righe):
    e = esami(righe)["900001"]
    robots = inc.Robots(scarica=lambda url: "User-agent: *\nDisallow: /bandi/\n")
    finto = scarica_da({})
    inc.controlla_pagina(e, finto, robots)
    assert (e.esito, e.motivo) == (inc.DA_VERIFICARE, "robots.txt vieta la pagina")
    assert finto.scaricati == []


def test_robots_assente_permette_non_leggibile_da_verificare():
    def errore(codice):
        def scarica(url):
            raise urllib.error.HTTPError(url, codice, "errore", {}, None)

        return scarica

    url = "https://www.esempio.it/bando"
    assert inc.Robots(scarica=errore(404)).permesso(url) is True
    assert inc.Robots(scarica=errore(403)).permesso(url) is False
    assert inc.Robots(scarica=errore(500)).permesso(url) is None


def test_robots_dice_quanto_aspettare_tra_due_download():
    url = "https://www.esempio.it/bando"
    con_attesa = inc.Robots(scarica=lambda _url: "User-agent: *\nCrawl-delay: 2\n")
    senza = inc.Robots(scarica=lambda _url: "User-agent: *\nDisallow:\n")

    assert con_attesa.attesa(url) == 2.0
    assert senza.attesa(url) == 0.0


def test_link_con_lettere_accentate_codificato(righe):
    e = esami(righe)["900001"]
    e.incentivo.link = (
        "https://www.ministero-di-prova.it/bandi/disabilità-2026?a=1&b=%20"
    )
    finto = scarica_da(
        {"https://www.ministero-di-prova.it/bandi/disabilit%C3%A0-2026?a=1&b=%20": ""}
    )
    inc.controlla_pagina(e, finto, RobotsLiberi())
    assert finto.scaricati == [
        "https://www.ministero-di-prova.it/bandi/disabilit%C3%A0-2026?a=1&b=%20"
    ]


def test_pagina_non_scaricata_da_verificare(righe):
    def rotta(url):
        raise OSError("connessione rifiutata")

    e = esami(righe)["900001"]
    inc.controlla_pagina(e, rotta, RobotsLiberi())
    assert e.esito == inc.DA_VERIFICARE
    assert e.motivo.startswith("pagina non scaricata")


# --- riga di bandi e beneficiari ---


def test_tipi_privati_dai_settori(righe):
    avvisi = []
    tipi = [b["tipo"] for b in inc.beneficiari_privati(righe["900001"], avvisi)]
    assert tipi == ["impresa_turistica", "impresa_artigiana_commerciale"]
    assert avvisi == []


def test_impresa_senza_settori_e_ogni_tipo_d_impresa(righe):
    tipi = {b["tipo"] for b in inc.beneficiari_privati(righe["900006"], [])}
    assert tipi == set(TIPI_IMPRESA)


def test_ente_pubblico_mai_tra_i_tipi_del_catalogo(righe):
    for incentivo in righe.values():
        tipi = {b["tipo"] for b in inc.beneficiari_privati(incentivo, [])}
        assert not tipi & set(TIPI_PUBBLICI)


def test_tipologia_sconosciuta_nessun_tipo_e_un_avviso(righe):
    avvisi = []
    tipi = [b["tipo"] for b in inc.beneficiari_privati(righe["900014"], avvisi)]
    assert tipi == ["professionista_autonomo"]
    assert avvisi == [
        "Tipologia_Soggetto sconosciuta: 'Tipologia Inventata', nessun tipo"
    ]


def test_solo_enti_pubblici_non_si_salva(righe):
    e = esami(righe)["900012"]
    assert (e.stato, e.esito) == (inc.STORICO, inc.PAGINA)
    e.prova = "entro il 30/09/2026"
    assert inc.prepara_salvataggio(e) is None
    assert e.esito == inc.DA_VERIFICARE
    assert e.motivo.startswith("nessun tipo privato nel catalogo")


def test_riga_di_bandi(righe):
    e = esami(righe)["900001"]
    e.prova = "entro le ore 12:00 del 31/12/2026"
    riga = inc.riga_bando(e, [])
    assert riga["id"] == "incentivi-900001"
    assert (riga["apertura"], riga["scadenza"], riga["a_sportello"]) == (
        "2026-01-15",
        "2026-12-31",
        0,
    )
    assert riga["pubblicato_il"] is None
    assert inc.NOTA_CATALOGO in riga["beneficiari"]
    assert "Microimpresa" in riga["beneficiari"]
    assert riga["territorio"] == "nazionale (20 regioni nel catalogo)"
    assert "31/12/2026" in riga["scadenza_nota"]


# --- salvataggio e registro, sul database su file ---


def _importa(righe, pagine: dict[str, str], monkeypatch) -> dict[str, inc.Esame]:
    """Esame, controllo delle pagine e scrittura, con la rete finta."""
    monkeypatch.setattr(importa, "scarica", scarica_da(pagine))
    monkeypatch.setattr(
        inc, "_scarica_robots", lambda url: "User-agent: *\nDisallow:\n"
    )
    monkeypatch.setattr(importa, "PAUSA_PAGINE", 0)
    e = esami(righe)
    importa.controlla_pagine(list(e.values()))
    importa.scrivi(list(e.values()), inc.NOME_FONTE.format(data="2026-11-12"))
    return e


PAGINE_PROVA = {
    "https://www.ministero-di-prova.it/bandi/turismo-2026": "con-data",
    "https://www.regione-di-prova.it/-/sportello-recente": "sportello",
    "https://www.regione-di-prova.it/-/montagna": "proroga",
    "https://www.camera-di-prova.it/bando-export": "proroga",
    "https://www.regione-di-prova.it/-/solo-enti": "proroga",
    "https://www.ministero-di-prova.it/bandi/ricerca": "proroga",
}


def test_importazione_salva_e_registra(db_su_file, righe, monkeypatch):
    pagine = {u: pagina(n) for u, n in PAGINE_PROVA.items()}
    _importa(righe, pagine, monkeypatch)

    conn = connetti()
    try:
        bandi = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM bandi")}
        tipi = conn.execute(
            "SELECT tipo, origine FROM beneficiari_bando "
            "WHERE id_bando = 'incentivi-900001' ORDER BY tipo"
        ).fetchall()
        scansioni = {
            r["slug"]: dict(r) for r in conn.execute("SELECT * FROM scansioni")
        }
    finally:
        conn.close()

    assert set(bandi) == {"incentivi-900001", "incentivi-900016"}
    assert bandi["incentivi-900001"]["codice_fonte"] == inc.CODICE_FONTE
    assert bandi["incentivi-900001"]["classificato_il"] is not None
    assert [tuple(t) for t in tipi] == [
        ("impresa_artigiana_commerciale", "catalogo"),
        ("impresa_turistica", "catalogo"),
    ]
    assert scansioni["incentivi-900001"]["esito"] == "salvato"
    # le da verificare tornano a ogni aggiornamento: motivo non "scaduto"
    da_verificare = scansioni["incentivi-900003"]
    assert da_verificare["esito"] == "scartato"
    assert da_verificare["motivo"].startswith(importa.PREFISSO_DA_VERIFICARE)
    # ignorate e righe al modello non si registrano
    assert "incentivi-900007" not in scansioni
    assert "incentivi-900011" not in scansioni


def test_seconda_importazione_nessuna_riga_in_piu(db_su_file, righe, monkeypatch):
    pagine = {u: pagina(n) for u, n in PAGINE_PROVA.items()}
    _importa(righe, pagine, monkeypatch)
    conn = connetti()
    prima = [
        conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("bandi", "beneficiari_bando", "scansioni")
    ]
    conn.close()

    _importa(righe, pagine, monkeypatch)
    conn = connetti()
    dopo = [
        conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("bandi", "beneficiari_bando", "scansioni")
    ]
    conn.close()
    assert prima == dopo


def test_sportello_salvato_con_la_data_di_apertura(db_su_file, righe, monkeypatch):
    pagine = {u: pagina(n) for u, n in PAGINE_PROVA.items()}
    _importa(righe, pagine, monkeypatch)
    conn = connetti()
    riga = conn.execute("SELECT * FROM bandi WHERE id = 'incentivi-900016'").fetchone()
    conn.close()

    assert (riga["pubblicato_il"], riga["pubblicato_origine"]) == (
        "2025-06-02",
        inc.ORIGINE_APERTURA,
    )
    # la regola della tappa 5a legge la data di apertura: oggi no, fra due anni si'
    assert "probabilmente esaurito" not in stato_sportello(riga, OGGI.isoformat())
    assert "probabilmente esaurito" in stato_sportello(riga, "2027-06-03")


def test_beneficiari_del_catalogo_non_sono_frasi_del_bando():
    riga = {"classificato_il": "2026-11-13"}
    voce = {
        "tipo": "altra_impresa",
        "soggetto": "Impresa",
        "condizioni": None,
        "frase": "Impresa",
        "origine": "catalogo",
    }
    testo = descrivi_beneficiari(riga, [voce])
    assert "dal catalogo Incentivi Italia: «Impresa»" in testo
    assert "frase del bando" not in testo


def test_schema_ammette_le_origini_nuove():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys = ON")
    c.executescript(DDL)
    c.execute(
        "INSERT INTO fonti (codice, nome, tipo, url_base, fonte, verificato_il) "
        "VALUES ('f', 'f', 'file', 'https://f.it', 'prova', '2026-11-13')"
    )
    c.execute(
        "INSERT INTO bandi (id, titolo, ente, beneficiari, url, fonte, codice_fonte, "
        "verificato_il, pubblicato_il, pubblicato_origine) VALUES ('b', 't', 'e', "
        "'x', 'https://f.it/b', 'prova', 'f', '2026-11-13', '2023-01-01', 'apertura')"
    )
    c.execute(
        "INSERT INTO beneficiari_bando (id_bando, tipo, frase, origine) "
        "VALUES ('b', 'altra_impresa', 'Impresa', 'catalogo')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        c.execute("UPDATE bandi SET pubblicato_origine = 'inventata' WHERE id = 'b'")
    c.close()
