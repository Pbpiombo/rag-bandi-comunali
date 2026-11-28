"""File dei contesti per frammento (scripts/ingestione/esporta_contesti.py).

Sotto-fermata 1.3 della fermata 1 del 19e: le righe hanno i campi che il
motore legge, l'impronta del testo del frammento, e il file non si
sovrascrive con un contenuto diverso. Nessun PDF, nessun Chroma: documenti
e contesti salvati finti.
"""

import json

import pytest

from scripts.diagnostica.genera_contesti import Documento, FrammentoDaContestualizzare
from scripts.ingestione import esporta_contesti as ec
from src import motore as mo


def documenti_finti() -> list[Documento]:
    frammenti = [
        FrammentoDaContestualizzare("id-2", 2, "secondo frammento"),
        FrammentoDaContestualizzare("id-1", 1, "primo frammento"),
    ]
    return [
        Documento(
            fonte="avviso.pdf",
            id_bando="B1",
            titolo="Titolo",
            atto="",
            parte="",
            testo="primo frammento secondo frammento",
            frammenti=frammenti,
        )
    ]


def salvati_finti() -> dict:
    return {
        f.id: {"sha256_frammento": f.sha256, "impronta": "a758adc6d26c" + "0" * 52}
        for d in documenti_finti()
        for f in d.frammenti
    }


CONTESTI = {("avviso.pdf", 2): "Contesto due", ("avviso.pdf", 1): "Contesto uno"}


def test_righe_con_i_campi_del_motore_e_l_impronta_del_testo():
    righe = ec.righe_del_file(CONTESTI, documenti_finti(), salvati_finti())
    assert [(r["fonte"], r["chunk_num"]) for r in righe] == [
        ("avviso.pdf", 1),
        ("avviso.pdf", 2),
    ]
    assert all(tuple(r) == mo.CAMPI_CONTESTO for r in righe)
    assert righe[0]["sha256_testo"] == mo.impronta_testo("primo frammento")
    assert righe[0]["contesto"] == "Contesto uno"
    assert {r["origine"] for r in righe} == {"modello"}
    # il motore le legge tutte come valide
    contesti, scarti = mo.contesti_validi(
        righe,
        ["primo frammento", "secondo frammento"],
        [
            {"fonte": "avviso.pdf", "chunk_num": 1, "sha256": "x"},
            {"fonte": "avviso.pdf", "chunk_num": 2, "sha256": "x"},
        ],
    )
    assert contesti == CONTESTI
    assert scarti.totale() == 0


def test_righe_ferme_se_il_contesto_e_stato_scritto_su_un_altro_testo():
    salvati = salvati_finti()
    salvati["id-1"]["sha256_frammento"] = mo.impronta_testo("un altro testo")
    with pytest.raises(ec.ErroreEsportazione, match="impronta del testo"):
        ec.righe_del_file(CONTESTI, documenti_finti(), salvati)


def test_il_file_non_si_sovrascrive_con_un_contenuto_diverso(tmp_path):
    percorso = tmp_path / "contesti_avvisi.jsonl"
    righe = ec.righe_del_file(CONTESTI, documenti_finti(), salvati_finti())
    testo = ec.testo_del_file(righe)
    assert ec.confronta(percorso, testo)[0] is False
    assert ec.scrivi(percorso, testo).startswith("scritto")
    assert percorso.read_text(encoding="utf-8") == testo
    assert ec.scrivi(percorso, testo).startswith("niente da scrivere")
    diverso = ec.testo_del_file([{**righe[0], "contesto": "Altro"}, righe[1]])
    uguale, descrizione = ec.confronta(percorso, diverso)
    assert uguale is False
    assert "cambiate 1" in descrizione
    with pytest.raises(ec.ErroreEsportazione, match="non si sovrascrive"):
        ec.scrivi(percorso, diverso)
    assert percorso.read_text(encoding="utf-8") == testo
    assert [json.loads(r)["contesto"] for r in testo.splitlines()] == [
        "Contesto uno",
        "Contesto due",
    ]
