"""Risposta grezza del modello conservata per ogni estrazione.

Nessun test scrive nella cartella vera dei dati grezzi: tutti usano
tmp_path, e il modello e' un estrattore finto che restituisce una stringa.
"""

import json
from datetime import datetime

import pytest

from src.config import MODEL_NAME
from src.estrazione import grezzi
from src.estrazione.bandi import estrai, valida
from tests.test_estrattore import PAGINE, pagina_salvata

QUANDO = datetime(2026, 11, 13, 15, 30, tzinfo=grezzi.FUSO)
URL = "https://www.regione.toscana.it/-/tpl"


class EstrattoreFinto:
    """Restituisce sempre la stessa risposta, come farebbe il modello."""

    def __init__(self, risposta: str):
        self.risposta = risposta
        self.chiamate = 0

    def invoke(self, _ingresso):
        self.chiamate += 1
        return self.risposta


def risposta_tpl() -> str:
    """La risposta salvata di una pagina vera, come stringa."""
    return (PAGINE / "tpl.risposta.json").read_text(encoding="utf-8")


def test_il_file_ha_data_e_id_e_contiene_testo_e_risposta(tmp_path):
    percorso = grezzi.conserva(tmp_path, "tpl-2026", URL, "testo", "{}", QUANDO)

    assert percorso.name == "2026-11-13_tpl-2026.json"
    dati = json.loads(percorso.read_text(encoding="utf-8"))
    assert dati == {
        "id_bando": "tpl-2026",
        "url": URL,
        "estratto_il": "2026-11-13T15:30:00+01:00",
        "modello": MODEL_NAME,
        "testo": "testo",
        "risposta": "{}",
    }


def test_la_seconda_estrazione_dello_stesso_giorno_non_sovrascrive(tmp_path):
    primo = grezzi.conserva(tmp_path, "tpl", URL, "t", "prima", QUANDO)
    secondo = grezzi.conserva(tmp_path, "tpl", URL, "t", "seconda", QUANDO)
    terzo = grezzi.conserva(tmp_path, "tpl", URL, "t", "terza", QUANDO)

    assert [p.name for p in (primo, secondo, terzo)] == [
        "2026-11-13_tpl.json",
        "2026-11-13_tpl-2.json",
        "2026-11-13_tpl-3.json",
    ]
    assert grezzi.leggi(primo)["risposta"] == "prima"


def test_un_id_con_caratteri_strani_da_un_nome_pulito(tmp_path):
    percorso = grezzi.conserva(tmp_path, "Bando/2026 è?", URL, "t", "r", QUANDO)

    assert percorso.name == "2026-11-13_bando-2026.json"
    assert grezzi.leggi(percorso)["id_bando"] == "Bando/2026 è?"


def test_la_cartella_mancante_si_crea(tmp_path):
    cartella = tmp_path / "dati-grezzi" / "estrazioni"

    percorso = grezzi.conserva(cartella, "tpl", URL, "t", "r", QUANDO)

    assert percorso.parent == cartella


def test_estrai_conserva_la_risposta_tale_e_quale(tmp_path):
    testo = pagina_salvata("tpl")
    grezzo = risposta_tpl()

    estrai(
        EstrattoreFinto(grezzo),
        testo,
        conserva=grezzi.conservatore("tpl", URL, testo, tmp_path),
    )

    (percorso,) = tmp_path.glob("*_tpl.json")
    dati = grezzi.leggi(percorso)
    assert dati["risposta"] == grezzo
    assert dati["testo"] == testo


def test_una_risposta_non_json_si_conserva_prima_dell_errore(tmp_path):
    with pytest.raises(ValueError, match="non interpretabile"):
        estrai(
            EstrattoreFinto("Mi dispiace, non posso."),
            "testo",
            conserva=grezzi.conservatore("rotto", URL, "testo", tmp_path),
        )

    (percorso,) = tmp_path.glob("*_rotto.json")
    assert grezzi.leggi(percorso)["risposta"] == "Mi dispiace, non posso."


def test_con_conserva_none_non_si_scrive_niente(tmp_path, monkeypatch):
    monkeypatch.setattr(grezzi, "ESTRAZIONI_DIR", tmp_path)

    estrai(EstrattoreFinto(risposta_tpl()), pagina_salvata("tpl"), conserva=None)

    assert list(tmp_path.iterdir()) == []


def test_conserva_e_obbligatorio():
    with pytest.raises(TypeError):
        estrai(EstrattoreFinto(risposta_tpl()), "testo")


def test_rileggere_la_risposta_conservata_da_la_stessa_validazione(tmp_path):
    testo = pagina_salvata("tpl")
    estrattore = EstrattoreFinto(risposta_tpl())

    estrazione = estrai(
        estrattore, testo, conserva=grezzi.conservatore("tpl", URL, testo, tmp_path)
    )
    (percorso,) = tmp_path.glob("*_tpl.json")
    riletta, testo_riletto = grezzi.rileggi(percorso)

    assert riletta == estrazione
    assert valida(riletta, testo_riletto) == valida(estrazione, testo)
    assert estrattore.chiamate == 1


def test_il_conservatore_senza_cartella_usa_quella_dei_dati_grezzi(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(grezzi, "ESTRAZIONI_DIR", tmp_path)

    percorso = grezzi.conservatore("tpl", URL, "t")("r")

    assert percorso.parent == tmp_path


def test_la_cartella_dei_dati_grezzi_e_fuori_dal_repository():
    from src.config import ESTRAZIONI_DIR, ROOT_DIR

    assert not ESTRAZIONI_DIR.is_relative_to(ROOT_DIR)
