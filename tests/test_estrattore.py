"""L'estrattore sulle tre pagine salvate, senza chiamare il modello.

Le risposte del modello sono scritte a mano (tests/pagine/*.risposta.json):
qui si verifica che il codice ne ricavi il risultato atteso
(tests/pagine/attesi.json), e come reagisce a risposte sbagliate.
"""

import copy
import json
import re
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from src.estrazione import bandi
from src.estrazione.bandi import (
    ISTRUZIONI,
    MODELLO_PROMPT,
    decidi_automatico,
    interpreta,
    valida,
)
from src.estrazione.beneficiari import (
    GENERICI,
    TERMINI,
    TIPI_BENEFICIARIO,
    TIPI_PRIVATI,
    frase_nel_testo,
)
from src.estrazione.salva import salva

PAGINE = Path(__file__).parent / "pagine"
ATTESI = json.loads((PAGINE / "attesi.json").read_text(encoding="utf-8"))


def pagina_salvata(nome: str) -> str:
    return (PAGINE / f"{nome}.txt").read_text(encoding="utf-8")


def risposta(nome: str) -> dict:
    return json.loads((PAGINE / f"{nome}.risposta.json").read_text(encoding="utf-8"))


def esegui(nome: str, dati: dict | None = None, aggiunta: str = ""):
    """interpreta + valida + decidi su una pagina salvata.

    aggiunta e' testo accodato alla pagina, per i casi che la pagina reale
    non contiene (es. un bando a sportello).
    """
    estrazione = interpreta(dati if dati is not None else risposta(nome))
    riga, problemi, avvisi = valida(estrazione, pagina_salvata(nome) + aggiunta)
    decisione = decidi_automatico(estrazione, riga) if not problemi else None
    return estrazione, riga, problemi, avvisi, decisione


class DataFissa(date):
    """Il giorno prima della scadenza del bando TPL."""

    @classmethod
    def today(cls):
        return cls(2021, 10, 1)


# --- le tre pagine con la risposta corretta ---


@pytest.mark.parametrize("nome", list(ATTESI))
def test_risposta_corretta_da_il_risultato_atteso(nome):
    atteso = ATTESI[nome]
    estrazione, riga, problemi, avvisi, decisione = esegui(nome)

    assert problemi == []
    assert avvisi == []
    assert estrazione.natura == atteso["natura"]
    salvare, motivo = decisione
    assert salvare == atteso["salvare"]
    assert motivo.startswith(atteso["motivo"])

    for campo, valore in atteso["campi"].items():
        assert riga[campo] == valore, campo

    tipi = sorted(b["tipo"] for b in riga.get("beneficiari_ammessi", []))
    assert tipi == atteso["tipi"]

    for tipo, parole in atteso["condizioni_contengono"].items():
        (b,) = [b for b in riga["beneficiari_ammessi"] if b["tipo"] == tipo]
        for parola in parole:
            assert parola in b["condizioni"].lower(), (tipo, parola)

    assert len(riga.get("interventi", [])) >= atteso["interventi_almeno"]
    assert riga.get("cumulabilita") == atteso["cumulabilita"]


def test_tpl_interventi_e_spese():
    _, riga, *_ = esegui("tpl")
    assert [i["genere"] for i in riga["interventi"]] == ["intervento"] + ["spesa"] * 4
    assert [i["numero"] for i in riga["interventi"]] == [1, 2, 3, 4, 5]


def test_musei_non_diventano_un_bando_per_comune():
    """La pagina non nomina i Comuni: il tipo e' il requisito, non 'comune'."""
    _, riga, *_ = esegui("musei")
    assert {b["tipo"] for b in riga["beneficiari_ammessi"]} == {"qualsiasi_soggetto"}


def test_qualifica_si_scarta_come_non_bando_in_modo_definitivo():
    from src.estrazione.registro import DEFINITIVI

    *_, (salvare, motivo) = esegui("qualifica")
    assert not salvare
    assert motivo.startswith(DEFINITIVI)


# --- risposte sbagliate del modello ---


def test_tpl_come_a_settembre_le_regole_aggiungono_i_tipi():
    """Settembre: solo 'comune', a bassa confidenza. Le regole correggono."""
    dati = risposta("tpl")
    dati["beneficiari_ammessi"] = [
        {
            "soggetto": "Enti locali competenti",
            "tipi": ["comune"],
            "condizioni": None,
            "frase": "Enti locali competenti.",
            "confidenza": "bassa",
        }
    ]
    _, riga, problemi, avvisi, _ = esegui("tpl", dati)

    assert problemi == []
    assert sorted(b["tipo"] for b in riga["beneficiari_ammessi"]) == [
        "altro_ente_pubblico",
        "comune",
        "unione_comuni",
    ]
    assert all(b["confidenza"] == "bassa" for b in riga["beneficiari_ammessi"])
    atteso = (
        "beneficiario 'Enti locali competenti': aggiunti altro_ente_pubblico, "
        "unione_comuni per le regole di corrispondenza"
    )
    assert avvisi == [atteso]


def test_beneficiari_a_bassa_confidenza_non_fanno_scartare(monkeypatch):
    """Con il bando ancora aperto, la bassa confidenza sui tipi non scarta."""
    monkeypatch.setattr(bandi, "date", DataFissa)
    dati = risposta("tpl")
    for b in dati["beneficiari_ammessi"]:
        b["confidenza"] = "bassa"

    *_, decisione = esegui("tpl", dati)

    assert decisione == (True, "aperto fino al 2021-10-21")


def test_frase_assente_dalla_pagina_scarta_la_voce():
    dati = risposta("tpl")
    dati["beneficiari_ammessi"].append(
        {
            "soggetto": "Province",
            "tipi": ["altro_ente_pubblico"],
            "condizioni": None,
            "frase": "Possono partecipare anche le Province toscane.",
            "confidenza": "media",
        }
    )
    dati["interventi"].append(
        {"genere": "spesa", "descrizione": "progettazione", "frase": "spese tecniche"}
    )
    dati["cumulabilita"] = {"clausola": "cumulabile", "frase": "e' cumulabile"}

    _, riga, problemi, avvisi, _ = esegui("tpl", dati)

    assert problemi == []
    assert len(riga["beneficiari_ammessi"]) == 3
    assert len(riga["interventi"]) == 5
    assert riga["cumulabilita"] is None
    assert len(avvisi) == 3
    assert all("frase non trovata nella pagina" in a for a in avvisi)


def test_tipo_fuori_lista_e_un_problema():
    dati = risposta("tpl")
    dati["beneficiari_ammessi"][0]["tipi"] = ["comune", "comuni_montani"]
    _, _, problemi, *_ = esegui("tpl", dati)
    assert any("comuni_montani" in p for p in problemi)


def test_nessun_beneficiario_verificato_e_un_problema():
    dati = risposta("tpl")
    dati["beneficiari_ammessi"][0]["frase"] = "Frase inventata dal modello."
    _, _, problemi, *_ = esegui("tpl", dati)
    assert "beneficiari_ammessi: nessun beneficiario con frase verificata" in problemi


def test_qualsiasi_soggetto_senza_condizioni_si_scarta():
    dati = risposta("musei")
    dati["beneficiari_ammessi"][0]["condizioni"] = None
    _, _, problemi, avvisi, _ = esegui("musei", dati)
    assert any("qualsiasi_soggetto senza condizioni" in a for a in avvisi)
    assert "beneficiari_ammessi: nessun beneficiario con frase verificata" in problemi


def _musei_con_soggetto(soggetto: str, tipi: list[str] | None = None):
    """La risposta dei musei con un soggetto diverso, accodato alla pagina."""
    dati = risposta("musei")
    voce = dati["beneficiari_ammessi"][0]
    voce["soggetto"] = soggetto
    if tipi:
        voce["tipi"] = tipi
    voce["frase"] = f"Possono partecipare {soggetto}."
    return esegui("musei", dati, aggiunta=f"\n{voce['frase']}\n")


def test_qualsiasi_soggetto_con_soggetti_privati_diventa_i_tipi_privati():
    _, riga, problemi, avvisi, _ = _musei_con_soggetto("soggetti ospitanti privati")

    assert problemi == []
    ammessi = riga["beneficiari_ammessi"]
    assert sorted(b["tipo"] for b in ammessi) == sorted(TIPI_PRIVATI)
    # le condizioni passano alle righe nuove
    assert all("museo" in b["condizioni"] for b in ammessi)
    # e il soggetto originale, con la sua qualificazione
    assert {b["soggetto"] for b in ammessi} == {"soggetti ospitanti privati"}
    atteso = (
        "beneficiario 'soggetti ospitanti privati': qualsiasi_soggetto sostituito "
        f"da {', '.join(sorted(TIPI_PRIVATI))} per le regole di corrispondenza"
    )
    assert avvisi == [atteso]


def test_qualsiasi_soggetto_pubblici_o_privati_compare_ai_comuni():
    _, riga, problemi, _, _ = _musei_con_soggetto("soggetti pubblici o privati")

    assert problemi == []
    tipi = {b["tipo"] for b in riga["beneficiari_ammessi"]}
    assert {"comune", "unione_comuni"} <= tipi
    assert "qualsiasi_soggetto" not in tipi


def test_soggetto_generico_non_aggiunge_tipi_a_un_soggetto_classificato():
    """ "privati senza scopo di lucro" classificato terzo_settore resta tale."""
    _, riga, problemi, avvisi, _ = _musei_con_soggetto(
        "soggetti privati senza scopo di lucro", ["terzo_settore"]
    )

    assert problemi == []
    assert [b["tipo"] for b in riga["beneficiari_ammessi"]] == ["terzo_settore"]
    assert avvisi == []


def test_natura_sconosciuta_e_un_problema():
    dati = risposta("tpl")
    dati["natura"] = {"valore": "forse", "motivo": "", "prova": ""}
    _, _, problemi, *_ = esegui("tpl", dati)
    assert problemi == ["natura: valore 'forse' non riconosciuto (bando o non_bando)"]


def test_origine_della_pubblicazione_sconosciuta_resta_vuota():
    dati = risposta("tpl")
    dati["pubblicato_il"]["origine"] = "sito"
    _, riga, problemi, avvisi, _ = esegui("tpl", dati)
    assert problemi == []
    assert riga["pubblicato_il"] == "2021-09-22"
    assert riga["pubblicato_origine"] is None
    assert any(a.startswith("pubblicato_il: origine 'sito'") for a in avvisi)


def test_campi_semplici_come_valore_nudo_restano_ad_alta_confidenza():
    estrazione = interpreta(risposta("tpl"))
    titolo = next(c for c in estrazione.campi if c.nome == "titolo")
    assert (titolo.confidenza, titolo.prova) == ("alta", "")


# --- bandi a sportello ---


# La frase che rende a sportello la pagina del TPL, nei test che ne hanno bisogno
SPORTELLO = "\nLe domande si presentano a sportello fino a esaurimento delle risorse."


def _a_sportello(scadenza):
    dati = copy.deepcopy(risposta("tpl"))
    dati["a_sportello"] = {
        "valore": True,
        "confidenza": "alta",
        "prova": "Le domande si presentano a sportello fino a esaurimento delle risorse",
    }
    dati["scadenza"]["valore"] = scadenza
    return dati


def test_a_sportello_senza_chiusura_si_salva():
    *_, decisione = esegui("tpl", _a_sportello(None), SPORTELLO)
    assert decisione == (True, "a sportello")


def test_a_sportello_con_chiusura_passata_e_scaduto():
    *_, decisione = esegui("tpl", _a_sportello("2021-10-21"), SPORTELLO)
    assert decisione == (False, "scaduto il 2021-10-21")


def test_a_sportello_con_chiusura_futura_si_salva(monkeypatch):
    monkeypatch.setattr(bandi, "date", DataFissa)
    *_, decisione = esegui("tpl", _a_sportello("2021-10-21"), SPORTELLO)
    assert decisione == (True, "a sportello fino al 2021-10-21")


# --- prove dei campi cercate nella pagina ---


def test_scadenza_con_prova_assente_dalla_pagina_e_un_problema():
    dati = risposta("tpl")
    dati["scadenza"]["prova"] = "Le domande vanno presentate entro il 21 ottobre 2021"
    _, _, problemi, *_ = esegui("tpl", dati)
    assert len(problemi) == 1
    assert problemi[0].startswith(
        "scadenza: prova del valore '2021-10-21' non trovata nella pagina"
    )


def test_a_sportello_con_prova_assente_dalla_pagina_e_un_problema():
    _, _, problemi, *_ = esegui("tpl", _a_sportello(None))
    assert len(problemi) == 1
    assert problemi[0].startswith("a_sportello: prova del valore '1' non trovata")


def test_a_sportello_falso_non_richiede_una_prova():
    """La pagina dei musei non dice da nessuna parte che non e' a sportello."""
    dati = risposta("musei")
    assert dati["a_sportello"] == {"valore": False, "confidenza": "alta", "prova": ""}
    _, riga, problemi, *_ = esegui("musei", dati)
    assert (riga["a_sportello"], problemi) == (0, [])


@pytest.mark.parametrize("nudo", [False, "false", "no"])
def test_a_sportello_falso_nudo_si_accetta_senza_prova(nudo):
    """Il modello a volte scrive false invece dell'oggetto con la prova."""
    dati = risposta("musei")
    dati["a_sportello"] = nudo
    estrazione, riga, problemi, *_ = esegui("musei", dati)
    campo = next(c for c in estrazione.campi if c.nome == "a_sportello")
    assert (campo.valore, campo.confidenza, campo.prova) == (False, "alta", "")
    assert (riga["a_sportello"], problemi) == (0, [])


def test_a_sportello_vero_nudo_senza_frase_e_un_problema():
    """Il caso delle 13 pagine fallite nella scansione dell'11 novembre 2026.

    Anche se la pagina dice che e' a sportello, un true senza la frase
    non si accetta: la prova deve sempre essere verificata.
    """
    dati = risposta("tpl")
    dati["a_sportello"] = True
    _, _, problemi, *_ = esegui("tpl", dati, SPORTELLO)
    atteso = (
        "a_sportello: prova del valore '1' non trovata nella pagina "
        "('formato non conforme')"
    )
    assert problemi == [atteso]


def test_importo_con_prova_assente_dalla_pagina_resta_vuoto():
    dati = risposta("tpl")
    dati["dotazione"]["prova"] = "la dotazione complessiva e' di 2 milioni"
    _, riga, problemi, avvisi, _ = esegui("tpl", dati)
    assert problemi == []
    assert riga["dotazione"] is None
    atteso = (
        "dotazione: prova del valore '2000000.0' non trovata nella pagina "
        "('la dotazione complessiva e' di 2 milioni'), lasciato vuoto"
    )
    assert avvisi == [atteso]


def test_pubblicazione_con_prova_assente_dalla_pagina_resta_vuota():
    dati = risposta("musei")
    dati["pubblicato_il"]["prova"] = "pubblicato il 16 agosto 2023"
    _, riga, problemi, avvisi, _ = esegui("musei", dati)
    assert problemi == []
    assert (riga["pubblicato_il"], riga["pubblicato_origine"]) == (None, None)
    assert len(avvisi) == 1
    assert avvisi[0].startswith("pubblicato_il: prova del valore '2023-08-16'")


# --- frasi e prompt ---


def test_frase_nel_testo_ignora_spazi_maiuscole_apostrofi_e_punto_finale():
    pagina = pagina_salvata("musei")
    assert frase_nel_testo("ammontano a  EURO 1.200.000,00 complessivi.", pagina)
    assert frase_nel_testo(
        "Le risorse finanziarie previste per l'annualità 2023", pagina
    )
    assert not frase_nel_testo("", pagina)
    assert not frase_nel_testo("ammontano a euro 2.000.000,00", pagina)


def test_il_prompt_contiene_tutti_i_tipi_e_le_regole():
    for codice in TIPI_BENEFICIARIO:
        assert f"- {codice}:" in ISTRUZIONI
    for espressione in TERMINI | GENERICI:
        assert f'"{espressione}"' in ISTRUZIONI


def test_il_prompt_ha_come_unica_variabile_il_testo():
    """Le graffe degli esempi JSON non diventano variabili del prompt."""
    assert MODELLO_PROMPT.input_variables == ["testo"]
    messaggi = MODELLO_PROMPT.format_messages(testo="PAGINA")
    assert '{"soggetto"' in messaggi[0].content


# --- salvataggio dell'estrazione ---


def test_salva_scrive_beneficiari_e_interventi_e_sostituisce_i_migrati(db_su_file):
    url = "https://www.regione.toscana.it/-/tpl"
    _, riga, *_ = esegui("tpl")
    riga["id"] = "tpl"

    c = sqlite3.connect(db_su_file)
    c.execute(
        "INSERT INTO bandi (id, titolo, ente, beneficiari, url, fonte, codice_fonte, "
        "verificato_il) VALUES ('tpl', 'vecchio', 'Regione', 'Comuni', ?, 'prova', "
        "'regione-toscana', '2026-01-01')",
        (url,),
    )
    c.execute(
        "INSERT INTO beneficiari_bando (id_bando, tipo, frase, origine) "
        "VALUES ('tpl', 'comune', 'Comuni', 'ammette_comuni')"
    )
    c.commit()
    c.close()

    salva(riga, url, "Portale bandi Regione Toscana", "regione-toscana")

    c = sqlite3.connect(db_su_file)
    beneficiari = c.execute(
        "SELECT tipo, origine FROM beneficiari_bando ORDER BY tipo"
    ).fetchall()
    interventi = c.execute("SELECT COUNT(*) FROM interventi_bando").fetchone()[0]
    bando = c.execute(
        "SELECT titolo, pubblicato_il, pubblicato_origine, classificato_il FROM bandi"
    ).fetchone()
    c.close()

    assert beneficiari == [
        ("altro_ente_pubblico", "estrazione"),
        ("comune", "estrazione"),
        ("unione_comuni", "estrazione"),
    ]
    assert interventi == 5
    assert bando[:3] == (
        "Contributi per sostenere il trasporto pubblico locale nelle aree deboli",
        "2021-09-22",
        "pubblicazione",
    )
    # classificato_il e' la data del salvataggio
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", bando[3])


# --- bandi a finestre o con piu' scadenze ---

FINESTRE = (
    "\nPrima finestra: dal 1 settembre al 30 settembre 2021."
    "\nSeconda finestra: dal 1 ottobre al 21 ottobre 2021."
    "\nTerza finestra: dal 1 marzo al 31 marzo 2022."
    "\nLa proposta completa va inviata entro il 15 gennaio 2022.\n"
)


def _finestra(descrizione, apertura, scadenza, frase, genere="domanda"):
    return {
        "genere": genere,
        "descrizione": descrizione,
        "apertura": apertura,
        "scadenza": scadenza,
        "frase": frase,
    }


PRIMA = _finestra(
    "prima finestra",
    "2021-09-01",
    "2021-09-30",
    "Prima finestra: dal 1 settembre al 30 settembre 2021.",
)
SECONDA = _finestra(
    "seconda finestra",
    "2021-10-01",
    "2021-10-21",
    "Seconda finestra: dal 1 ottobre al 21 ottobre 2021.",
)
TERZA = _finestra(
    "terza finestra",
    "2022-03-01",
    "2022-03-31",
    "Terza finestra: dal 1 marzo al 31 marzo 2022.",
)
COMPLETA = _finestra(
    "proposta completa",
    None,
    "2022-01-15",
    "La proposta completa va inviata entro il 15 gennaio 2022.",
    genere="fase_successiva",
)


def _con_scadenze(voci):
    dati = risposta("tpl")
    dati["scadenze"] = voci
    return esegui("tpl", dati, aggiunta=FINESTRE)


def test_scadenze_verificate_e_scadenza_del_bando_dall_ultima():
    _, riga, problemi, avvisi, _ = _con_scadenze([TERZA, PRIMA, SECONDA])

    assert problemi == []
    assert [(s["numero"], s["descrizione"]) for s in riga["scadenze"]] == [
        (1, "prima finestra"),
        (2, "seconda finestra"),
        (3, "terza finestra"),
    ]
    assert riga["scadenza"] == "2022-03-31"
    atteso = (
        "scadenza: il modello indica '2021-10-21', l'ultima scadenza per "
        "presentare domanda e' 2022-03-31: uso 2022-03-31"
    )
    assert avvisi == [atteso]


def test_fase_successiva_non_cambia_la_scadenza_del_bando():
    _, riga, problemi, avvisi, _ = _con_scadenze([SECONDA, COMPLETA])

    assert problemi == []
    assert [s["genere"] for s in riga["scadenze"]] == ["domanda", "fase_successiva"]
    assert riga["scadenza"] == "2021-10-21"
    assert avvisi == []


def test_scadenza_con_frase_assente_si_scarta():
    inventata = {**TERZA, "frase": "Terza finestra: dal 1 aprile 2022."}
    _, riga, _, avvisi, _ = _con_scadenze([PRIMA, SECONDA, inventata])

    assert [s["descrizione"] for s in riga["scadenze"]] == [
        "prima finestra",
        "seconda finestra",
    ]
    assert any(
        a.startswith("scadenze: 'terza finestra' frase non trovata") for a in avvisi
    )


@pytest.mark.parametrize(
    "sbagliata",
    [
        {**TERZA, "genere": "rendicontazione"},
        {**TERZA, "scadenza": "31/03/2022"},
        {**TERZA, "apertura": "marzo"},
        {**TERZA, "apertura": "2022-04-01"},
    ],
)
def test_scadenza_non_valida_si_scarta(sbagliata):
    _, riga, _, avvisi, _ = _con_scadenze([PRIMA, SECONDA, sbagliata])

    assert len(riga["scadenze"]) == 2
    assert any(a.startswith("scadenze: 'terza finestra'") for a in avvisi)


def test_una_sola_data_nessuna_riga():
    _, riga, _, avvisi, _ = _con_scadenze([SECONDA])

    assert riga["scadenze"] == []
    assert riga["scadenza"] == "2021-10-21"
    assert avvisi == ["scadenze: una sola data verificata, nessuna riga salvata"]


def test_il_prompt_chiede_le_scadenze_e_le_date_in_contraddizione():
    assert '"scadenze"' in ISTRUZIONI
    assert "fase_successiva" in ISTRUZIONI
    assert "non sceglierne una" in ISTRUZIONI


def test_salva_scrive_e_sostituisce_le_scadenze(db_su_file):
    url = "https://www.regione.toscana.it/-/tpl"
    _, riga, *_ = _con_scadenze([PRIMA, SECONDA, TERZA])
    riga["id"] = "tpl"

    salva(riga, url, "Portale bandi Regione Toscana", "regione-toscana")

    c = sqlite3.connect(db_su_file)
    righe = c.execute(
        "SELECT numero, genere, apertura, scadenza FROM scadenze_bando ORDER BY numero"
    ).fetchall()
    scadenza = c.execute("SELECT scadenza FROM bandi").fetchone()[0]
    c.close()
    assert righe == [
        (1, "domanda", "2021-09-01", "2021-09-30"),
        (2, "domanda", "2021-10-01", "2021-10-21"),
        (3, "domanda", "2022-03-01", "2022-03-31"),
    ]
    assert scadenza == "2022-03-31"

    # una nuova estrazione con una sola data toglie le righe
    _, riga, *_ = esegui("tpl")
    riga["id"] = "tpl"
    salva(riga, url, "Portale bandi Regione Toscana", "regione-toscana")
    c = sqlite3.connect(db_su_file)
    assert c.execute("SELECT COUNT(*) FROM scadenze_bando").fetchone()[0] == 0
    c.close()


def test_estrai_bando_mostra_le_scadenze(capsys):
    from scripts.ingestione.estrai_bando import mostra

    dati = risposta("tpl")
    dati["scadenze"] = [PRIMA, COMPLETA]
    mostra(interpreta(dati))

    uscita = capsys.readouterr().out
    assert "  - [domanda] prima finestra: dal 2021-09-01 al 2021-09-30" in uscita
    assert "  - [fase_successiva] proposta completa: entro il 2022-01-15" in uscita
    assert f"      frase: {PRIMA['frase']}" in uscita


def test_estrai_bando_senza_scadenze_multiple(capsys):
    from scripts.ingestione.estrai_bando import mostra

    mostra(interpreta(risposta("tpl")))
    assert "SCADENZE MULTIPLE\n  nessuna (una sola data)" in capsys.readouterr().out


# --- sportello con data di chiusura ---


@pytest.mark.parametrize(
    "frase",
    [
        "Domande fino al 31 ottobre 2027, salvo esaurimento anticipato delle risorse disponibili.",
        "Domande dal 28 marzo fino al 31 dicembre 2026, salvo esaurimento delle risorse.",
        "Fino al 31/12/2027, salvo l’esaurimento anticipato delle risorse.",
    ],
)
def test_prova_sportello_trova_la_frase(frase):
    assert bandi.prova_sportello(f"Titolo\n{frase}\nAltro") == frase


def test_graduatoria_fino_a_esaurimento_non_e_sportello():
    testo = "Le risorse sono assegnate in ordine di graduatoria fino a esaurimento delle risorse."
    assert bandi.prova_sportello(testo) is None


def test_salvo_esaurimento_rende_il_bando_a_sportello():
    frase = (
        "Domande fino al 21 ottobre 2021, salvo esaurimento anticipato delle risorse."
    )
    _, riga, problemi, avvisi, decisione = esegui("tpl", aggiunta=f"\n{frase}\n")

    assert problemi == []
    assert riga["a_sportello"] == 1
    assert avvisi == [f"a_sportello: la pagina dice «{frase}»: bando a sportello"]
    assert decisione[1].startswith("scaduto il 2021-10-21")


def test_prova_sportello_lunga_si_accorcia_e_resta_nel_testo():
    riga = "x" * 400 + " salvo esaurimento delle risorse " + "y" * 400
    prova = bandi.prova_sportello(riga)
    assert len(prova) <= 2 * bandi.PROVA_MAX
    assert frase_nel_testo(prova, riga)


def test_il_prompt_dice_che_sportello_e_data_non_si_contraddicono():
    assert "non sono una contraddizione" in ISTRUZIONI
    assert "modificano scadenze o requisiti" in ISTRUZIONI
    assert "cittadini_famiglie solo se il bando nomina" in ISTRUZIONI


# --- enti religiosi: terzo_settore con la condizione, mai qualsiasi_soggetto ---


def _ammessi(riga) -> list[tuple[str, str | None]]:
    return [(b["tipo"], b["condizioni"]) for b in riga["beneficiari_ammessi"]]


def test_ente_religioso_come_qualsiasi_soggetto_diventa_terzo_settore():
    _, riga, problemi, avvisi, _ = _musei_con_soggetto(
        "Enti religiosi", ["qualsiasi_soggetto"]
    )

    assert problemi == []
    [(tipo, condizioni)] = _ammessi(riga)
    assert tipo == "terzo_settore"
    # la condizione dei musei resta, preceduta da quella dell'ente religioso
    assert condizioni.startswith("ente religioso; ")
    # la sostituzione la fa gia' la regola di corrispondenza "enti religiosi"
    assert any(
        "qualsiasi_soggetto sostituito da terzo_settore per le regole" in a
        for a in avvisi
    )


def test_ente_religioso_classificato_altrimenti_diventa_terzo_settore():
    dati = risposta("musei")
    voce = dati["beneficiari_ammessi"][0]
    voce["soggetto"] = "Enti religiosi ed ecclesiastici civilmente riconosciuti"
    voce["tipi"] = ["altro_ente_pubblico"]
    voce["condizioni"] = None
    voce["frase"] = f"Possono partecipare {voce['soggetto']}."

    _, riga, problemi, _, _ = esegui("musei", dati, aggiunta=f"\n{voce['frase']}\n")

    assert problemi == []
    assert _ammessi(riga) == [("terzo_settore", "ente religioso")]


def test_la_condizione_resta_se_dice_gia_ente_religioso():
    dati = risposta("musei")
    voce = dati["beneficiari_ammessi"][0]
    voce["soggetto"] = "Enti religiosi"
    voce["tipi"] = ["terzo_settore"]
    voce["condizioni"] = "ente religioso civilmente riconosciuto"
    voce["frase"] = "Enti religiosi"

    _, riga, _, avvisi, _ = esegui("musei", dati, aggiunta="\nEnti religiosi\n")

    assert _ammessi(riga) == [
        ("terzo_settore", "ente religioso civilmente riconosciuto")
    ]
    assert avvisi == []


def test_ente_religioso_tra_altri_soggetti_non_restringe_gli_altri():
    _, riga, problemi, _, _ = _musei_con_soggetto(
        "Fondazioni ed enti religiosi", ["terzo_settore"]
    )

    assert problemi == []
    [(tipo, condizioni)] = _ammessi(riga)
    assert tipo == "terzo_settore"
    assert "ente religioso" not in (condizioni or "")


def test_il_prompt_dice_la_regola_degli_enti_religiosi():
    assert (
        "Enti religiosi ed ecclesiastici sono terzo_settore, con la condizione "
        '"ente religioso": mai qualsiasi_soggetto.'
    ) in ISTRUZIONI


def test_il_prompt_chiede_i_soggetti_riservati_negli_interventi():
    assert "viabilita' rurale, solo enti pubblici" in ISTRUZIONI
    assert "La frase comprende allora anche la parte che nomina quei soggetti." in (
        ISTRUZIONI
    )


@pytest.mark.parametrize("ordine", [1, -1])
def test_soggetto_senza_condizioni_prevale_nella_fusione(ordine):
    # "Comuni" e "Comuni in forma associata" con la stessa frase: i Comuni
    # sono ammessi anche da soli, in qualunque ordine li elenchi il modello
    frase = "Possono partecipare Comuni, Unioni di Comuni, Comuni in forma associata."
    voci = [
        {"soggetto": "Comuni", "tipi": ["comune"], "frase": frase},
        {
            "soggetto": "Comuni in forma associata",
            "tipi": ["comune", "unione_comuni"],
            "condizioni": "in forma associata",
            "frase": frase,
        },
        {"soggetto": "Unioni di Comuni", "tipi": ["unione_comuni"], "frase": frase},
    ][::ordine]
    righe = bandi._valida_beneficiari(voci, frase, [], [])
    assert {r["tipo"]: r["condizioni"] for r in righe} == {
        "comune": None,
        "unione_comuni": None,
    }


def test_due_condizioni_diverse_si_tengono_entrambe():
    frase = "Possono partecipare i Comuni montani e i Comuni sotto i 5.000 abitanti."
    voci = [
        {
            "soggetto": "Comuni",
            "tipi": ["comune"],
            "condizioni": "montani",
            "frase": frase,
        },
        {
            "soggetto": "Comuni",
            "tipi": ["comune"],
            "condizioni": "sotto i 5.000 abitanti",
            "frase": frase,
        },
    ]
    righe = bandi._valida_beneficiari(voci, frase, [], [])
    assert [r["condizioni"] for r in righe] == ["montani; sotto i 5.000 abitanti"]
