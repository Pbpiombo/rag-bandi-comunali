"""Test dell'insieme di prova, senza modello e con domande inventate qui."""

import csv
import json
import sqlite3

import pytest
from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import (
    FakeListChatModel,
    GenericFakeChatModel,
)
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from scripts.diagnostica import prova_insieme as p
from src.database.modelli import Approfondimento, Risultato, VoceBando

FILE_FINTO = """# Insieme di prova finto
# gruppo | codice | domanda | atteso
comuni | C1 | Bandi per le strade comunali? | strade; non: mercati rionali
comuni | C2 | Contributi per l'illuminazione? |
comuni | C3 | Fondi per le scuole? | a mano: cita la scadenza
comuni | C4 | Bandi per lo sport? | Sport Missione Comune; a mano: dice il mutuo
privati | P1 | Contributi per un rifugio? | turismo
privati | P2 | Aiuti per un'azienda agricola? |
privati | P3 | Bandi per un negozio? | NON: risorse genetiche
privati | P4 | Fondi per un artigiano? |
aperte | A1 | Cosa posso chiedere? |
aperte | A2 | Ci sono opportunità? |
aperte | A3 | Domanda aperta tre? |
aperte | A4 | Domanda aperta quattro? |
viste | V1 | Domanda già vista? |
viste | V2 | Altra domanda vista? |
"""


def domande():
    return p.leggi_domande(FILE_FINTO)


# --- Lettura del file ---


def test_lettura_salta_commenti_e_divide_le_attese():
    lette = domande()
    assert len(lette) == 14
    c1 = lette[0]
    assert (c1.gruppo, c1.codice, c1.testo) == (
        "comuni",
        "C1",
        "Bandi per le strade comunali?",
    )
    assert c1.attese == ["strade"]
    assert c1.vietate == ["mercati rionali"]
    assert c1.a_mano == []


def test_lettura_attese_multiple_e_a_mano():
    c4 = next(d for d in domande() if d.codice == "C4")
    assert c4.attese == ["Sport Missione Comune"]
    assert c4.a_mano == ["dice il mutuo"]
    c2 = next(d for d in domande() if d.codice == "C2")
    assert (c2.attese, c2.vietate, c2.a_mano) == ([], [], [])


def test_lettura_non_maiuscolo():
    p3 = next(d for d in domande() if d.codice == "P3")
    assert p3.vietate == ["risorse genetiche"]
    assert p3.attese == []


@pytest.mark.parametrize(
    "riga",
    [
        "comuni | C1",
        "ignoto | X1 | domanda? |",
        "comuni |  | domanda? |",
        "comuni | C1 | a | b | c",
    ],
)
def test_lettura_righe_malformate(riga):
    with pytest.raises(p.ErroreProva):
        p.leggi_domande(riga)


def test_lettura_codice_ripetuto_senza_mostrare_la_domanda():
    testo = "comuni | C1 | prima segreta? |\ncomuni | C1 | seconda segreta? |"
    with pytest.raises(p.ErroreProva) as errore:
        p.leggi_domande(testo)
    assert "riga 2" in str(errore.value)
    assert "segreta" not in str(errore.value)


# --- Divisione ---


def test_divisione_stratificata():
    lette = domande()
    divisione = p.dividi(lette, seme=7)
    gruppo_di = {d.codice: d.gruppo for d in lette}
    for gruppo in p.GRUPPI_MISURATI:
        conti = [sum(gruppo_di[c] == gruppo for c in divisione[n]) for n in divisione]
        assert max(conti) - min(conti) <= 1
    tutti = [c for codici in divisione.values() for c in codici]
    assert sorted(tutti) == sorted(gruppo_di)


def test_divisione_viste_tutte_nel_lotto_1():
    divisione = p.dividi(domande(), seme=7)
    assert {"V1", "V2"} <= set(divisione[1])
    for n in (2, 3, 4):
        assert not any(c.startswith("V") for c in divisione[n])


def test_divisione_ripetibile_e_indipendente_dall_ordine():
    lette = domande()
    assert p.dividi(lette, seme=7) == p.dividi(lette, seme=7)
    assert p.dividi(list(reversed(lette)), seme=7) == p.dividi(lette, seme=7)


def test_divisione_cambia_con_il_seme():
    lette = domande()
    semi = {json.dumps(p.dividi(lette, seme=s)) for s in range(10)}
    assert len(semi) > 1


def test_scrivi_lotti_una_volta_sola(tmp_path):
    percorso = tmp_path / "lotti.json"
    p.scrivi_lotti(domande(), percorso, "impronta", seme=3)
    contenuto = json.loads(percorso.read_text(encoding="utf-8"))
    assert contenuto["seme"] == 3
    assert set(contenuto["lotti"]) == {"1", "2", "3", "4"}
    # Solo codici e gruppi, non il testo delle domande
    assert "strade" not in percorso.read_text(encoding="utf-8")
    with pytest.raises(p.ErroreProva):
        p.scrivi_lotti(domande(), percorso, "impronta", seme=3)


def test_domande_del_lotto_nell_ordine_della_divisione(tmp_path):
    file_domande = tmp_path / "domande.txt"
    file_domande.write_text(FILE_FINTO, encoding="utf-8")
    file_lotti = tmp_path / "lotti.json"
    divisione = p.scrivi_lotti(domande(), file_lotti, p.impronta(file_domande))
    lotto = p.domande_del_lotto(2, file_lotti, file_domande)
    assert [d.codice for d in lotto] == divisione[2]


def test_conteggi_senza_domande():
    lette = domande()
    tabella = p.conteggi_lotti(lette, p.dividi(lette, seme=7))
    assert "comuni" in tabella and "viste" in tabella
    assert "strade" not in tabella


# --- Attese ---


def test_attese_trovate_mancanti_e_vietate():
    c1 = next(d for d in domande() if d.codice == "C1")
    titoli = ["Fondo per le STRADE dei piccoli comuni", "Mercati  rionali 2026"]
    esito = p.controlla_attese(c1, titoli)
    assert esito == {
        "trovate": ["strade"],
        "mancanti": [],
        "vietate_comparse": ["mercati rionali"],
    }


def test_attese_apostrofo_tipografico():
    d = p.Domanda("comuni", "X", "?", attese=["dell'Appennino"])
    assert p.controlla_attese(d, ["Bando dell’Appennino"])["trovate"]
    assert p.controlla_attese(d, ["Altro"])["mancanti"] == ["dell'Appennino"]


# --- Router ---


def test_esito_router_conta_le_anomalie():
    buono = '{"documenti": true, "interrogazioni": []}'
    recintato = "```json\n" + buono + "\n```"
    assert p.esito_router([buono, recintato, "non so"]) == {
        "riuscito": True,
        "anomalie": 1,
        "chiamate": 3,
    }
    assert p.esito_router(["testo", buono, "[1, 2]"])["riuscito"] is False
    assert p.esito_router(["testo", buono, "[1, 2]"])["anomalie"] == 2


def messaggio(testo: str) -> AIMessage:
    return AIMessage(
        content=testo,
        usage_metadata={"input_tokens": 100, "output_tokens": 10, "total_tokens": 110},
        response_metadata={"model_name": "finto"},
    )


def test_router_triplo_chiama_tre_volte_e_restituisce_la_prima():
    modello = GenericFakeChatModel(
        messages=iter([messaggio("primo"), messaggio("secondo"), messaggio("terzo")])
    )
    router = p.RouterTriplo(modello | (lambda m: m.content))
    assert router.invoke("entrata") == "primo"
    assert router.grezzi == ["primo", "secondo", "terzo"]
    assert router.uso["finto"]["input_tokens"] == 300


def test_router_triplo_contato_anche_dal_contatore_esterno():
    modello = GenericFakeChatModel(messages=iter([messaggio(str(i)) for i in range(4)]))
    router = p.RouterTriplo(modello | (lambda m: m.content))
    with p.get_usage_metadata_callback() as contatore:
        router.invoke("x")
        modello.invoke("risposta")
    totale = dict(contatore.usage_metadata)
    assert totale["finto"]["input_tokens"] == 400
    risposta = p.differenza_uso(totale, router.uso)
    assert risposta["finto"] == {"input_tokens": 100, "output_tokens": 10}


# --- Conversione e riverifica ---


def esiti_finti():
    risultato = Risultato(
        testo="Bandi aperti (archivio al 2026-11-14):\n"
        "[#1] Fondo strade piccoli comuni, scadenza 2026-12-31, contributo 50.000 euro "
        "(atto: decreto 123 del 2026)",
        fonti=["catalogo regionale"],
        voci=[
            VoceBando(
                testo="Fondo strade piccoli comuni, scadenza 2026-12-31, "
                "contributo 50.000 euro (atto: decreto 123 del 2026)",
                fonte="decreto 123 del 2026",
                titolo="Fondo strade piccoli comuni",
                url="https://esempio.it/strade",
            )
        ],
        da_approfondire=[Approfondimento("Altro", "https://esempio.it/a", "scadenza")],
    )
    return [("bandi_aperti_per_ente", risultato)]


def documenti_finti():
    return [
        Document(
            page_content="Il contributo massimo è di 80.000 euro.",
            metadata={"ente": "Regione", "page": 3, "riferimento_atto": "Decreto 9"},
        )
    ]


RISPOSTA_FINTA = (
    "Il Fondo strade scade il 31 dicembre 2026 (fonte: [D1.1], decreto 123 del 2026) "
    "e dà fino a 50.000 euro (fonte: [D1.1], decreto 123 del 2026). "
    "Un altro avviso arriva a 90.000 euro (fonte: [1], Regione, Decreto 9, pag. 3). "
    "Si parla anche di 7.000 euro."
)


def test_andata_e_ritorno_degli_esiti_dati():
    originali = esiti_finti()
    json_ = json.loads(json.dumps(p.esiti_dati_in_json(originali)))
    assert p.esiti_dati_da_json(json_) == originali
    documenti = documenti_finti()
    assert p.documenti_da_json(p.documenti_in_json(documenti)) == documenti


def voce_finta(codice="C1", gruppo="comuni", risposta=RISPOSTA_FINTA):
    domanda = next(d for d in domande() if d.codice == codice)
    voce = {
        "codice": codice,
        "gruppo": gruppo,
        "domanda": domanda.testo,
        "attese": domanda.attese,
        "vietate": domanda.vietate,
        "a_mano": domanda.a_mano,
        "router": {"riuscito": True, "anomalie": 1, "chiamate": 3},
        "decisione": {
            "documenti": True,
            "interrogazioni": [{"nome": "bandi_aperti_per_ente"}],
        },
        "esiti_dati": p.esiti_dati_in_json(esiti_finti()),
        "documenti": p.documenti_in_json(documenti_finti()),
        "risposta": risposta,
        "costo": {"totale": {"dollari": 0.05}},
    }
    voce.update(
        p.verifica_risposta(domanda, risposta, documenti_finti(), esiti_finti())
    )
    return json.loads(json.dumps(voce))


def test_verifica_risposta_finta():
    voce = voce_finta()
    stati = {e["valore"]: e["stato"] for e in voce["esiti_verifica"]}
    assert stati["50.000"] == "verificato"
    assert stati["90.000"] == "non_trovato"
    assert stati["7.000"] == "non_citato"
    assert voce["attese_esito"]["trovate"] == ["strade"]
    assert [b["titolo"] for b in voce["bandi_citati"]] == [
        "Fondo strade piccoli comuni"
    ]


def test_riverifica_uguale_alla_verifica_originale():
    voce = voce_finta()
    rifatta = p.riverifica_voce(voce)
    assert rifatta["esiti_verifica"] == voce["esiti_verifica"]
    assert rifatta["attese_esito"] == voce["attese_esito"]


def test_riverifica_di_una_voce_con_errore():
    assert p.riverifica_voce({"errore": "Timeout"}) == {"errore": "Timeout"}


# --- Giudizi e rapporto ---


def test_precompila_giudizi_senza_duplicati_e_senza_toccare_i_giudizi(tmp_path):
    percorso = tmp_path / "giudizi.csv"
    voci = [voce_finta("C1"), voce_finta("C4")]
    aggiunte = p.precompila_giudizi(percorso, voci, seme=1)
    assert aggiunte > 0
    with percorso.open(encoding="utf-8-sig", newline="") as f:
        righe = list(csv.DictReader(f))
    assert list(righe[0]) == list(p.COLONNE_GIUDIZI)
    valori = {(r["codice"], r["valore"]) for r in righe}
    assert ("C1", "90.000") in valori
    assert ("C1", "7.000") in valori
    assert ("C4", p.VALORE_A_MANO) in valori

    # Scrivo un giudizio, come farebbe chi giudica, e precompilo di nuovo
    righe[0]["giudizio"] = "errore_vero"
    with percorso.open("w", encoding="utf-8-sig", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=p.COLONNE_GIUDIZI)
        scrittore.writeheader()
        scrittore.writerows(righe)
    assert p.precompila_giudizi(percorso, voci, seme=1) == 0
    giudizi = p.leggi_giudizi(percorso)
    primo = (righe[0]["codice"], righe[0]["valore"], righe[0]["contesto"])
    assert giudizi[primo]["giudizio"] == "errore_vero"
    assert len(giudizi) == len(righe)


def test_campione_ripetibile_e_senza_anni():
    voci = [voce_finta("C1"), voce_finta("C4")]
    primo = p.righe_da_giudicare(voci, seme=5)
    assert primo == p.righe_da_giudicare(voci, seme=5)
    campione = [r for r in primo if r["motivo"] == "campione"]
    assert campione
    assert len(campione) <= p.CAMPIONE_VERIFICATI
    assert all(r["esito"]["tipo"] != "anno" for r in campione)
    assert all(r["esito"]["stato"] == "verificato" for r in campione)


def meta_finto():
    return {
        "lotto": 1,
        "stato": "completa",
        "a_freddo": True,
        "commit": "abc",
        "seme_campione": 5,
        "codici": ["C1", "C4"],
    }


def test_rapporto_righe_conteggi_e_sezioni():
    voci = [voce_finta("C1"), voce_finta("C4")]
    testo = p.rapporto(voci, meta_finto(), {}, "Lotto 1")
    riga_c1 = next(r for r in testo.splitlines() if r.startswith("| C1 "))
    celle = [c.strip() for c in riga_c1.strip("|").split("|")]
    # codice, gruppo, router, interrogazioni, bandi citati, attese, vietate,
    # verificati, non trovati, senza fonte, col blocco, costo
    assert celle[2] == "sì, 1/3"
    assert celle[3] == "bandi_aperti_per_ente"
    assert celle[4] == "1"
    assert celle[5] == "1/1"
    assert celle[8] == "1"
    assert celle[9] == "1"
    assert "90.000" in testo and "7.000" in testo
    assert "## Campione" in testo
    assert "## Attese da giudicare a mano" in testo
    assert "- senza giudizio:" in testo


def test_rapporto_conta_i_giudizi_e_alla_riverifica_nasconde_i_giudicati():
    voci = [voce_finta("C1")]
    e = next(e for e in voci[0]["esiti_verifica"] if e["valore"] == "90.000")
    giudizi = {
        ("C1", "90.000", e["contesto"]): {"giudizio": "falso_allarme_numero"},
        ("C1", "7.000", "x"): {"giudizio": "altro"},
    }
    testo = p.rapporto(voci, meta_finto(), giudizi, "Lotto 1")
    assert "- falso_allarme_numero: 1" in testo
    assert "**giudizio: falso_allarme_numero**" in testo

    rifatto = p.rapporto(voci, meta_finto(), giudizi, "R", solo_senza_giudizio=True)
    sezione = rifatto.split("## Non trovati")[1].split("## Campione")[0]
    assert "90.000" not in sezione
    assert "7.000" in sezione


def test_rapporto_con_errore():
    voce = {
        "codice": "C2",
        "gruppo": "comuni",
        "domanda": "?",
        "errore": "APIError: tempo scaduto",
        "router": {"riuscito": False, "anomalie": 3, "chiamate": 3},
        "costo": {"totale": {"dollari": 0.01}},
    }
    testo = p.rapporto([voce], meta_finto(), {}, "Lotto 1")
    assert "errore: APIError" in testo


# --- Registrazione: cartelle, ripresa e riepilogo ---


def scrivi_registrazione(cartella, meta, voci):
    (cartella / "domande").mkdir(parents=True)
    p.scrivi_json(cartella / "meta.json", meta)
    for voce in voci:
        p.scrivi_json(cartella / "domande" / p.nome_file(voce["codice"]), voce)


def test_prima_registrazione_a_freddo_e_poi_no(tmp_path):
    cartella, meta = p.prepara_registrazione(tmp_path / "lotto_1", 1, None)
    assert meta["a_freddo"] is True
    assert meta["stato"] == "incompleta"
    scrivi_registrazione(
        tmp_path / "lotto_1" / "2026-11-14_100000", {**meta, "stato": "completa"}, []
    )
    _, seconda = p.prepara_registrazione(tmp_path / "lotto_1", 1, None)
    assert seconda["a_freddo"] is False


def test_nuova_registrazione_rifiutata_se_la_fredda_e_incompleta(tmp_path):
    lotto = tmp_path / "lotto_1"
    scrivi_registrazione(
        lotto / "2026-11-14_100000",
        {"lotto": 1, "a_freddo": True, "stato": "incompleta"},
        [],
    )
    with pytest.raises(p.ErroreProva, match="--riprendi"):
        p.prepara_registrazione(lotto, 1, None)


def test_riprendi_conserva_la_cartella_e_lo_stato_a_freddo(tmp_path):
    cartella = tmp_path / "lotto_1" / "2026-11-14_100000"
    scrivi_registrazione(
        cartella, {"lotto": 1, "a_freddo": True, "stato": "incompleta"}, []
    )
    ripresa, meta = p.prepara_registrazione(tmp_path / "lotto_1", 1, cartella)
    assert ripresa == cartella
    assert meta["a_freddo"] is True
    with pytest.raises(p.ErroreProva):
        p.prepara_registrazione(tmp_path / "lotto_2", 2, cartella)


def test_riprendi_rifiuta_una_registrazione_completa(tmp_path):
    cartella = tmp_path / "lotto_1" / "2026-11-14_100000"
    scrivi_registrazione(
        cartella, {"lotto": 1, "a_freddo": True, "stato": "completa"}, []
    )
    with pytest.raises(p.ErroreProva, match="completa"):
        p.prepara_registrazione(tmp_path / "lotto_1", 1, cartella)


def test_riepilogo_usa_gli_originali_e_le_riverifiche_a_parte(tmp_path):
    voci = [voce_finta("C1")]
    vista = {**voce_finta("C4"), "codice": "V1", "gruppo": "viste"}
    cartella = tmp_path / "lotto_1" / "2026-11-14_100000"
    scrivi_registrazione(
        cartella,
        {**meta_finto(), "codici": ["C1", "V1"]},
        [*voci, vista],
    )
    # Una riverifica che trova tutto: non deve cambiare le misure a freddo
    tutto_verificato = [{**e, "stato": "verificato"} for e in voci[0]["esiti_verifica"]]
    riverifiche = cartella / "riverifiche" / "2026-11-20_090000"
    riverifiche.mkdir(parents=True)
    p.scrivi_json(
        riverifiche / "esiti.json",
        {
            "momento": "2026-11-20T09:00:00+01:00",
            "esiti": {"C1": {"esiti_verifica": tutto_verificato}},
        },
    )
    testo = p.riepilogo(tmp_path)
    freddo, dopo = testo.split("## Dopo le correzioni")
    riga = next(r for r in freddo.splitlines() if r.startswith("| 1 "))
    celle = [c.strip() for c in riga.strip("|").split("|")]
    # lotto, stato, domande (la vista esclusa), ..., non trovati, senza fonte
    assert celle[2] == "1"
    assert celle[9] == "1"
    assert celle[10] == "1"
    riga_dopo = next(r for r in dopo.splitlines() if r.startswith("| 1 "))
    celle_dopo = [c.strip() for c in riga_dopo.strip("|").split("|")]
    assert celle_dopo[1] == "2026-11-20T09:00:00+01:00"
    assert celle_dopo[5] == "0"
    assert celle_dopo[6] == "0"


# --- La catena dell'app senza il parametro router ---


@pytest.fixture
def db_con_ente(db_su_file):
    c = sqlite3.connect(db_su_file)
    c.execute(
        "INSERT INTO enti (codice_fiscale, nome, tipo, regione, provincia, fonte, "
        "verificato_il) VALUES ('11111111111', 'Comune finto', 'comune', 'Toscana', "
        "'Pistoia', 'prova', '2026-01-01')"
    )
    c.commit()
    c.close()
    return db_su_file


class RecuperoFinto:
    def titoli(self):
        return []

    def cerca(self, domanda, k=10):
        return []


DECISIONE = '{"documenti": false, "interrogazioni": []}'


def prepara_catena(monkeypatch, chiamate):
    """La catena con modello e router finti: nessuna chiamata all'API."""
    from src.chains import rag

    def router_app():
        chiamate.append("costruisci_router")
        return RunnableLambda(lambda entrata: (chiamate.append("router"), DECISIONE)[1])

    monkeypatch.setattr(rag, "costruisci_router", router_app)
    monkeypatch.setattr(
        rag,
        "ChatAnthropic",
        lambda **_: FakeListChatModel(responses=["risposta finta"]),
    )
    return rag


def test_catena_senza_router_usa_quello_dell_app(db_con_ente, monkeypatch):
    chiamate = []
    rag = prepara_catena(monkeypatch, chiamate)
    catena = rag.costruisci_catena("11111111111", recupero=RecuperoFinto())
    esito = catena.invoke("Quanti abitanti?")
    assert chiamate == ["costruisci_router", "router"]
    assert esito["decisione"] == {"documenti": False, "interrogazioni": []}
    assert esito["risposta"] == "risposta finta"
    assert esito["documenti"] == []
    assert esito["dati"] == "(nessun dato numerico richiesto)"


def test_catena_con_router_passato(db_con_ente, monkeypatch):
    chiamate = []
    rag = prepara_catena(monkeypatch, chiamate)
    triplo = p.RouterTriplo(
        RunnableLambda(lambda entrata: (chiamate.append("triplo"), DECISIONE)[1])
    )
    catena = rag.costruisci_catena(
        "11111111111", recupero=RecuperoFinto(), router=triplo
    )
    esito = catena.invoke("Quanti abitanti?")
    assert chiamate == ["triplo", "triplo", "triplo"]
    assert triplo.grezzi == [DECISIONE] * 3
    assert esito["risposta"] == "risposta finta"
