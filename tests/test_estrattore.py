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
from src.estrazione.beneficiari import TERMINI, TIPI_BENEFICIARIO, frase_nel_testo
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

    for tipo, parola in atteso["condizioni_contengono"].items():
        (b,) = [b for b in riga["beneficiari_ammessi"] if b["tipo"] == tipo]
        assert parola in b["condizioni"].lower()

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
    for espressione in TERMINI:
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
