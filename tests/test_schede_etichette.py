"""Schede di etichettatura: tre vie, doppioni, taglio, data, uscita xlsx."""

import json
from datetime import date

import pytest
from openpyxl import load_workbook

from scripts.diagnostica import prova_insieme
from scripts.diagnostica import schede_etichette as s
from scripts.diagnostica.prova_insieme import Domanda
from src.database import interrogazioni_bandi, repertorio
from tests.conftest import CON_DATI

BASE = "https://www.regione.toscana.it/-/"
GIORNO = date(2026, 11, 16)
TEMA = "mobilita"


@pytest.fixture
def db(conn):
    """Il database in memoria del conftest con una fonte."""
    conn.execute(
        "INSERT INTO fonti (codice, nome, url_base, schema_link, fonte, "
        "verificato_il) VALUES ('regione-toscana', 'Toscana', ?, '^/-/', 'prova', "
        "'2026-11-11')",
        (BASE,),
    )
    return conn


def bando(
    conn,
    id_bando,
    titolo,
    scadenza="2026-12-31",
    tipi=("comune",),
    interventi=(),
    soggetto=None,
    **campi,
):
    """Un bando classificato, con i suoi beneficiari e interventi."""
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
        "classificato_il": "2026-11-11",
        **campi,
    }
    conn.execute(
        f"INSERT INTO bandi ({', '.join(riga)}) "
        f"VALUES ({', '.join('?' for _ in riga)})",
        list(riga.values()),
    )
    for tipo in tipi:
        conn.execute(
            "INSERT INTO beneficiari_bando (id_bando, tipo, soggetto, condizioni, "
            "frase, origine) VALUES (?, ?, ?, ?, ?, 'estrazione')",
            (
                id_bando,
                tipo,
                soggetto,
                # qualsiasi_soggetto vale solo con le condizioni (schema)
                "requisiti del bando" if tipo == "qualsiasi_soggetto" else None,
                f"frase {tipo}",
            ),
        )
    for numero, descrizione in enumerate(interventi, start=1):
        conn.execute(
            "INSERT INTO interventi_bando (id_bando, numero, genere, descrizione, "
            "frase) VALUES (?, ?, 'intervento', ?, ?)",
            (id_bando, numero, descrizione, descrizione),
        )


def grezzo(*richieste) -> str:
    """Una risposta grezza del router con le interrogazioni date."""
    return json.dumps(
        {
            "documenti": False,
            "interrogazioni": [{"nome": n, "parametri": p} for n, p in richieste],
        }
    )


def registrazione(cartella_prova, lotto, nome, codice, *grezzi):
    cartella = cartella_prova / f"lotto_{lotto}" / nome
    (cartella / "domande").mkdir(parents=True)
    (cartella / "meta.json").write_text("{}", encoding="utf-8")
    (cartella / "domande" / f"{codice}.json").write_text(
        json.dumps({"codice": codice, "grezzi_router": list(grezzi)}),
        encoding="utf-8",
    )


def domanda(testo, gruppo="privati", codice="X01"):
    return Domanda(gruppo, codice, testo)


def schede_e_archivio(db, cartella_prova, *domande, giorno=GIORNO, massimo=None):
    return s.prepara_schede(
        db, list(domande), giorno, cartella_prova, CON_DATI, massimo=massimo
    )


def schede(db, cartella_prova, *domande, giorno=GIORNO, massimo=None):
    return schede_e_archivio(
        db, cartella_prova, *domande, giorno=giorno, massimo=massimo
    )[0]


def origini(scheda) -> dict:
    return {c.bando.id: c.origine for c in scheda.candidati}


# --- Le tre vie ---


def test_via_router_una_esecuzione_per_interrogazione_ripetuta(db, tmp_path):
    bando(db, "strade", "Fondo per la viabilità", tema=TEMA)
    richiesta = grezzo(("bandi_per_tema", {"tema": TEMA}))
    registrazione(tmp_path, 1, "r1", "X01", richiesta, richiesta)
    registrazione(tmp_path, 2, "r2", "X01", richiesta)

    [scheda] = schede(db, tmp_path, domanda("Cosa offre l'archivio?"))
    assert origini(scheda) == {"strade": "router"}
    assert scheda.richieste.registrazioni == 2
    assert scheda.richieste.risposte == 3
    assert len(scheda.esecuzioni) == 1
    assert scheda.esecuzioni[0].volte == 3


def test_via_ente_solo_per_il_gruppo_comuni(db, tmp_path):
    bando(db, "parcheggi", "Bando parcheggi 2026")
    testo = "Quali possiamo chiedere?"
    [comuni, privati] = schede(
        db, tmp_path, domanda(testo, "comuni", "C01"), domanda(testo, "privati", "P01")
    )
    assert comuni.parole == []
    assert origini(comuni) == {"parcheggi": "ente"}
    assert origini(privati) == {}


def test_via_parole_titolo_interventi_beneficiari(db, tmp_path):
    bando(db, "titolo", "Contributi per i rifugi di montagna")
    bando(
        db,
        "interventi",
        "Bando turismo",
        interventi=["manutenzione della sentieristica"],
    )
    bando(db, "beneficiari", "Bando ospitalità", soggetto="agriturismi")
    bando(db, "scaduto", "Rifugi 2025", scadenza="2026-10-01")
    bando(db, "vuoto", "Bando contributi imprese")

    d = domanda("Vorrei sistemare il rifugio e la sentieristica, ho un agriturismo")
    [scheda] = schede(db, tmp_path, d)
    assert scheda.parole == ["sistemare", "rifugio", "sentieristica", "agriturismo"]
    assert origini(scheda) == {
        "titolo": "parole",
        "interventi": "parole",
        "beneficiari": "parole",
    }


def test_parole_vuote_aggiunte():
    assert s.parole_significative(
        "Ci sono contributi per le imprese di San Marcello Piteglio e Sambuca "
        "Pistoiese, in provincia di Pistoia?"
    ) == ["provincia"]
    assert s.parole_significative(
        "Si possono avere fondi a fondo perduto per un festival?"
    ) == ["possono", "perduto", "festival"]


def test_preposizioni_articolate_vuote():
    assert s.parole_significative(
        "Fondi dalla Regione sulla viabilità tra i borghi, negli spazi e "
        "sugli impianti, fra le frazioni, per le strade con le scuole"
    ) == [
        "regione",
        "viabilita",
        "borghi",
        "spazi",
        "impianti",
        "frazioni",
        "strade",
        "scuole",
    ]


# --- Chiamate del router ---


def test_chiamate_router_contate_per_risposta_e_usate_nell_ordine(db, tmp_path):
    """B da 3 risposte, A da 1: B prima di A a parità di vie e parole.

    Una risposta con due richieste che restituiscono lo stesso bando conta
    una volta sola.
    """
    bando(db, "a", "Bando A per la viabilità", tema=TEMA)
    bando(db, "b", "Bando B per la viabilità", tema=TEMA, tipi=("altra_impresa",))
    per_tema = ("bandi_per_tema", {"tema": TEMA})
    per_impresa = ("bandi_per_beneficiario", {"tipo": "altra_impresa"})
    registrazione(
        tmp_path,
        1,
        "r1",
        "X01",
        grezzo(per_tema, per_impresa),
        grezzo(per_impresa),
    )
    registrazione(tmp_path, 2, "r2", "X01", grezzo(per_impresa), "illeggibile")

    [scheda] = schede(db, tmp_path, domanda("Cosa offre l'archivio?"))
    assert [(c.bando.id, c.origine, c.chiamate_router) for c in scheda.candidati] == [
        ("b", "router", 3),
        ("a", "router", 1),
    ]


def test_chiamate_router_prima_del_punteggio_delle_parole(db, tmp_path):
    """Due bandi da router e parole: conta prima chi ha più chiamate.

    "molte" ha più parole della domanda nel titolo ma una sola chiamata;
    "poche" ne ha una sola ma tre chiamate.
    """
    bando(db, "molte", "Strade e ponti", tema=TEMA)
    bando(db, "poche", "Strade", tema=TEMA, tipi=("altra_impresa",))
    per_tema = ("bandi_per_tema", {"tema": TEMA})
    per_impresa = ("bandi_per_beneficiario", {"tipo": "altra_impresa"})
    registrazione(
        tmp_path,
        1,
        "r1",
        "X01",
        grezzo(per_tema),
        grezzo(per_impresa),
        grezzo(per_impresa),
    )
    [scheda] = schede(db, tmp_path, domanda("Strade e ponti"))
    assert [(c.bando.id, c.chiamate_router, c.punteggio) for c in scheda.candidati] == [
        ("poche", 3, 1),
        ("molte", 1, 2),
    ]


# --- Doppioni, non_bando, taglio ---


def test_doppioni_uniti_con_le_vie_e_messi_in_testa(db, tmp_path):
    bando(db, "strade", "Fondo per le strade", tema=TEMA)
    bando(db, "parcheggi", "Bando parcheggi 2026")
    richiesta = grezzo(("bandi_per_tema", {"tema": TEMA}))
    registrazione(tmp_path, 1, "r1", "C01", richiesta)
    registrazione(tmp_path, 2, "r2", "C01", richiesta)

    [scheda] = schede(
        db, tmp_path, domanda("Ci sono fondi per le strade?", "comuni", "C01")
    )
    assert [(c.bando.id, c.origine) for c in scheda.candidati] == [
        ("strade", "router, ente, parole"),
        ("parcheggi", "ente"),
    ]


def test_non_bando_escluso_da_tutte_le_vie(db, tmp_path):
    bando(db, "pagina", "Pagina sulle strade", tema=TEMA, natura="non_bando")
    registrazione(tmp_path, 1, "r1", "C01", grezzo(("bandi_per_tema", {"tema": TEMA})))
    [scheda] = schede(
        db, tmp_path, domanda("Ci sono fondi per le strade?", "comuni", "C01")
    )
    assert scheda.candidati == []
    assert scheda.unione == 0


def diciotto_bandi(db):
    for n in range(16):
        bando(db, f"strade-{n:02d}", f"Strade numero {n:02d}")
    bando(db, "ponti-a", "Strade zona A", interventi=["rifacimento dei ponti"])
    bando(db, "ponti-b", "Strade zona B", interventi=["ponti e guadi"])


def test_senza_massimo_tutti_i_candidati(db, tmp_path):
    diciotto_bandi(db)
    [scheda] = schede(db, tmp_path, domanda("Strade e ponti"))
    assert scheda.unione == 18
    assert len(scheda.candidati) == 18
    assert scheda.tagliati == []


def test_taglio_con_massimo(db, tmp_path):
    diciotto_bandi(db)
    lista, archivio = schede_e_archivio(
        db, tmp_path, domanda("Strade e ponti"), massimo=15
    )
    [scheda] = lista
    assert scheda.unione == 18
    assert len(scheda.candidati) == 15
    assert [c.bando.id for c in scheda.tagliati] == [
        "strade-13",
        "strade-14",
        "strade-15",
    ]
    assert [c.bando.id for c in scheda.candidati[:2]] == ["ponti-a", "ponti-b"]

    testo = s.riepilogo(
        lista, archivio, GIORNO, CON_DATI, "impronta", "adesso", massimo=15
    )
    assert "- al più 15 candidati per domanda" in testo
    assert "- tagliati (3):" in testo
    assert "  - Strade numero 15 [strade-15]: parole" in testo


def test_opzione_massimo(db, tmp_path, monkeypatch):
    diciotto_bandi(db)
    domande = tmp_path / "domande.txt"
    domande.write_text("privati | P01 | Strade e ponti\n", encoding="utf-8")
    monkeypatch.setattr(prova_insieme, "FILE_DOMANDE", domande)
    monkeypatch.setattr(prova_insieme, "CARTELLA_PROVA", tmp_path / "prova")
    monkeypatch.setattr(s, "CARTELLA_ETICHETTE", tmp_path / "etichette")
    monkeypatch.setattr(s, "apri_in_lettura", lambda: db)

    uscita = s.main(["--massimo", "15"])
    righe = list(load_workbook(uscita / "schede.xlsx")["candidati"].values)
    assert len(righe) == 1 + 15
    assert "- tagliati (3):" in (uscita / "riepilogo.md").read_text(encoding="utf-8")
    assert s.leggi_argomenti([]).massimo is None
    with pytest.raises(SystemExit):
        s.leggi_argomenti(["--massimo", "0"])


# --- Interrogazioni saltate ---


def test_interrogazioni_non_valide_saltate_e_contate(db, tmp_path):
    bando(db, "strade", "Fondo per la viabilità", tema=TEMA)
    registrazione(
        tmp_path,
        1,
        "r1",
        "X01",
        "non è una decisione",
        grezzo(("inventata", {})),
        grezzo(("bandi_per_tema", {"argomento": TEMA})),
        json.dumps({"documenti": False, "interrogazioni": ["bandi_per_tema"]}),
        grezzo(("bandi_per_tema", {"tema": TEMA})),
    )
    lista, archivio = schede_e_archivio(db, tmp_path, domanda("Cosa offre l'archivio?"))
    [scheda] = lista
    assert scheda.richieste.non_interpretabili == 1
    assert scheda.richieste.non_leggibili == 1
    saltate = [e.saltata for e in scheda.esecuzioni if e.saltata]
    assert len(saltate) == 2
    assert "non è nel repertorio" in saltate[0]
    assert saltate[1].startswith("Parametri non validi")
    assert origini(scheda) == {"strade": "router"}

    testo = s.riepilogo(lista, archivio, GIORNO, CON_DATI, "impronta", "adesso")
    assert "| 1 | 3 | 1 su 5 |" in testo


# --- Data di riferimento ---


def test_data_di_riferimento_nelle_interrogazioni(db, tmp_path):
    bando(db, "parcheggi", "Bando parcheggi 2026", scadenza="2026-11-20")
    registrazione(tmp_path, 1, "r1", "C01", grezzo(("bandi_aperti_per_ente", {})))
    d = domanda("Quali possiamo chiedere?", "privati", "C01")

    [prima] = schede(db, tmp_path, d, giorno=date(2026, 11, 16))
    [dopo] = schede(db, tmp_path, d, giorno=date(2026, 11, 25))
    assert origini(prima) == {"parcheggi": "router"}
    assert prima.candidati[0].bando.stato.startswith("aperto")
    assert origini(dopo) == {}


def test_alla_data_attraverso_repertorio_e_interrogazioni(db):
    """bandi_in_scadenza passa da repertorio a interrogazioni_bandi."""
    bando(db, "parcheggi", "Bando parcheggi 2026", scadenza="2026-11-20")
    originale = interrogazioni_bandi.data_di_oggi

    with s.alla_data(date(2026, 11, 16)):
        assert repertorio.data_di_oggi() == date(2026, 11, 16)
        vicino = repertorio.esegui_su(db, "bandi_in_scadenza", {"giorni": 10}, CON_DATI)
    with s.alla_data(date(2026, 11, 1)):
        lontano = repertorio.esegui_su(
            db, "bandi_in_scadenza", {"giorni": 10}, CON_DATI
        )

    assert [v.titolo for v in vicino.voci] == ["Bando parcheggi 2026"]
    assert lontano.voci == []
    assert interrogazioni_bandi.data_di_oggi is originale
    assert repertorio.data_di_oggi is originale


# --- Uscita ---


def test_xlsx_fogli_colonne_e_tendine(db, tmp_path):
    bando(db, "strade", "Fondo per le strade", interventi=["strade comunali"])
    d = Domanda(
        "comuni", "C01", "Ci sono fondi per le strade?", ["strade"], ["neve"], ["forma"]
    )
    lista, archivio = schede_e_archivio(db, tmp_path, d)
    uscita = s.scrivi_uscita(
        tmp_path / "uscita", lista, archivio, GIORNO, CON_DATI, "impronta"
    )

    libro = load_workbook(uscita / "schede.xlsx")
    assert libro.sheetnames == ["candidati", "forme"]
    candidati, forme = libro["candidati"], libro["forme"]
    assert [c.value for c in candidati[1]] == list(s.COLONNE_CANDIDATI)
    assert [c.value for c in forme[1]] == list(s.COLONNE_FORME)
    assert candidati.freeze_panes == "A2"
    assert candidati.auto_filter.ref == "A1:M2"

    riga = [c.value for c in candidati[2]]
    assert riga[3] == "strade"
    assert riga[9] == "ente, parole"
    assert riga[10] == 0
    assert riga[11] is None
    [convalida] = candidati.data_validations.dataValidation
    assert convalida.type == "list"
    assert convalida.formula1 == '"pertinente,generico,no"'
    assert "L2" in str(convalida.sqref)

    assert forme["C2"].value == "strade ; non: neve ; a mano: forma"
    [convalida] = forme.data_validations.dataValidation
    assert convalida.formula1 == '"non_trovo,solo_generici,elenco"'
    assert "D2" in str(convalida.sqref)

    riepilogo = (uscita / "riepilogo.md").read_text(encoding="utf-8")
    assert "- parole significative: strade" in riepilogo


def test_nessuna_sovrascrittura(tmp_path):
    cartella = tmp_path / "esistente"
    cartella.mkdir()
    (cartella / "riepilogo.md").write_text("di prima", encoding="utf-8")
    with pytest.raises(s.ErroreSchede):
        s.scrivi_uscita(cartella, [], {}, GIORNO, CON_DATI, "impronta")
    assert (cartella / "riepilogo.md").read_text(encoding="utf-8") == "di prima"
    assert not (cartella / "schede.xlsx").exists()


def test_main_con_codici(db, tmp_path, monkeypatch):
    bando(db, "strade", "Fondo per le strade")
    domande = tmp_path / "domande.txt"
    domande.write_text(
        "comuni | C01 | Ci sono fondi per le strade? | strade\n"
        "privati | P01 | Ho un negozio\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(prova_insieme, "FILE_DOMANDE", domande)
    monkeypatch.setattr(prova_insieme, "CARTELLA_PROVA", tmp_path / "prova")
    monkeypatch.setattr(s, "CARTELLA_ETICHETTE", tmp_path / "etichette")
    monkeypatch.setattr(s, "apri_in_lettura", lambda: db)

    uscita = s.main(["--codici", "C01", "--data", "2026-11-16"])
    righe = list(load_workbook(uscita / "schede.xlsx")["candidati"].values)
    assert [r[0] for r in righe[1:]] == ["C01"]
    with pytest.raises(s.ErroreSchede):
        s.scegli(prova_insieme.carica_domande(domande), "Z99")


# --- Bandi ricorrenti ---


def test_bandi_ricorrenti_e_aperti_per_tipo(db, tmp_path):
    bando(db, "strade", "Fondo per le strade", tipi=("comune", "altra_impresa"))
    bando(
        db,
        "rifugi",
        "Rifugi e strade di montagna",
        tipi=("impresa_turistica", "qualsiasi_soggetto"),
    )
    bando(db, "agricoltura", "Strade rurali", tipi=("impresa_agricola",))
    bando(db, "scaduto", "Strade 2025", scadenza="2026-10-01", tipi=("altra_impresa",))
    bando(
        db,
        "pagina",
        "Pagina sulle imprese",
        natura="non_bando",
        tipi=("altra_impresa",),
    )
    lista, archivio = schede_e_archivio(
        db,
        tmp_path,
        domanda("Quali possiamo chiedere?", "comuni", "C01"),
        domanda("Strade di montagna", "privati", "P01"),
        domanda("Montagna", "privati", "P02"),
        domanda("Strade", "viste", "L01"),
    )
    # rifugi: in 3 domande private; strade e agricoltura in 2, e a parità
    # prima chi è nelle domande dei comuni. rifugi ha qualsiasi_soggetto,
    # quindi bandi_aperti_per_ente lo dà anche al Comune, come filtro_ente
    assert [
        (b.id, comuni, privati, len(b.codici_tipi))
        for b, comuni, privati in s.bandi_ricorrenti(lista)
    ] == [
        ("rifugi", 1, 3, 2),
        ("strade", 1, 2, 2),
        ("agricoltura", 0, 2, 1),
    ]

    testo = s.riepilogo(lista, archivio, GIORNO, CON_DATI, "impronta", "adesso")
    assert "## Bandi ricorrenti" in testo
    assert "Bandi aperti alla data di riferimento: 3 " in testo
    # rifugi ammette tutti per requisito; strade con una riga altra_impresa
    assert "| altra_impresa | 2 | 1 |" in testo
    assert "| impresa_agricola | 2 | 1 |" in testo
    assert "| cittadini_famiglie | 1 | 0 |" in testo
    assert "| comune |" not in testo
    assert "| Fondo per le strade [strade] | 1 | 2 | 2 |" in testo
