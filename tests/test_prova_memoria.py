"""Pagina della prova di memoria (app/prova_memoria.py, docs/prova-memoria.md).

1. a_vettore: ogni forma in cui la colonna embedding può arrivare dal
   driver diventa lo stesso vettore numpy; una forma non riconosciuta dà un
   errore con tipo e lunghezza, mai il contenuto.
2. Un passo che non riesce: si annota il solo tipo dell'errore e il
   riepilogo parziale lo riporta.
3. Esclusione degli avvisi dal Chroma: per sha256, non per id_bando, che
   ha anche un documento di sempre (199 righe invece di 316).
4. Parti della memoria del contenitore da memory.stat.
5. Criterio per il quarto caso, scritto dopo la versione 1, stampato in un
   blocco separato dalla regola.

Valori finti, senza Postgres, rete o modelli. La pagina si carica dal suo
percorso: app/ non è un pacchetto, e importata così la pagina non parte
(Streamlit la esegue come __main__).
"""

import importlib.util
import struct
from pathlib import Path

import numpy as np
import pytest
from pgvector import Vector

PERCORSO = Path(__file__).resolve().parents[1] / "app" / "prova_memoria.py"
_spec = importlib.util.spec_from_file_location("prova_memoria", PERCORSO)
pm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pm)

NUMERI = [0.25, -1.5, 3.0, 1e-7]
ATTESO = np.array(NUMERI, dtype=np.float32)


def _binario(numeri: list[float]) -> bytes:
    """Formato binario di pgvector, scritto a mano: dimensione, zero, float32 big-endian."""
    return struct.pack(f">HH{len(numeri)}f", len(numeri), 0, *numeri)


# --- 1. Forme del vettore ---


@pytest.mark.parametrize(
    "valore",
    [
        Vector(NUMERI),
        _binario(NUMERI),
        bytearray(_binario(NUMERI)),
        memoryview(_binario(NUMERI)),
        Vector(NUMERI).to_binary(),
        "[0.25,-1.5,3,1e-07]",
        " [0.25, -1.5, 3.0, 1e-07] ",
        Vector(NUMERI).to_text(),
        NUMERI,
        tuple(NUMERI),
        np.array(NUMERI, dtype=np.float64),
    ],
    ids=[
        "pgvector.Vector",
        "bytes",
        "bytearray",
        "memoryview",
        "bytes da Vector.to_binary",
        "testo",
        "testo con spazi",
        "testo da Vector.to_text",
        "lista",
        "tupla",
        "array numpy",
    ],
)
def test_ogni_forma_da_lo_stesso_vettore(valore):
    vettore = pm.a_vettore(valore)
    assert vettore.dtype == np.float32
    assert vettore.ndim == 1
    np.testing.assert_array_equal(vettore, ATTESO)


def test_vstack_delle_righe_come_in_leggi_da_postgres():
    """Righe con forme diverse si impilano in una matrice float32."""
    righe = [Vector(NUMERI), _binario(NUMERI), "[0.25,-1.5,3,1e-07]"]
    matrice = np.vstack([pm.a_vettore(v) for v in righe])
    assert matrice.shape == (3, 4)
    assert matrice.dtype == np.float32


@pytest.mark.parametrize(
    ("valore", "tipo", "lunghezza"),
    [
        ({"segreto": 1}, "dict", "1"),
        (12345, "int", "non definita"),
        ("segreto-non-vettore", "str", "19"),
        ("[1, segreto]", "str", "12"),
        (b"\x00\x05\x00\x00segreto", "bytes", "11"),
        (b"\x00", "bytes", "1"),
        (b"\x00\x01\x00\x07\x00\x00\x00\x00", "bytes", "8"),
        ([[1.0, 2.0], [3.0, 4.0]], "list", "2"),
        (["segreto"], "list", "1"),
    ],
    ids=[
        "dizionario",
        "intero",
        "testo senza parentesi",
        "testo con parola",
        "bytes di lunghezza sbagliata",
        "bytes troppo corti",
        "bytes con secondo intero non zero",
        "lista a due dimensioni",
        "lista di testi",
    ],
)
def test_forma_non_riconosciuta_dice_tipo_e_lunghezza_non_contenuto(
    valore, tipo, lunghezza
):
    with pytest.raises(pm.ErrorePagina) as info:
        pm.a_vettore(valore)
    messaggio = str(info.value)
    assert f"tipo {tipo}" in messaggio
    assert f"lunghezza {lunghezza}" in messaggio
    assert "segreto" not in messaggio


def test_la_vecchia_conversione_falliva_su_vector():
    """La riga di prima (np.asarray su un Vector di pgvector 0.5) è la causa
    del TypeError del passo 4 online."""
    with pytest.raises(TypeError):
        np.asarray(Vector(NUMERI), dtype=np.float32)


# --- 2. Errore di un passo ---


def _stato() -> dict:
    return {"inizio": "2026-11-25 10:00 UTC", "fonte": "postgres"}


def test_errore_imprevisto_annota_solo_il_tipo():
    def passo_rotto(stato):
        raise TypeError("postgresql://utente:segreto@host/db")

    stato, esiti = _stato(), []
    pm.esegui_passo(4, passo_rotto, stato, esiti)
    assert esiti == []
    assert stato["errore"] == {
        "passo": 4,
        "testo": "Passo 4 non riuscito: TypeError",
    }


def test_errore_della_pagina_tiene_il_suo_messaggio():
    def passo_rotto(stato):
        raise pm.ErrorePagina("lettura da Postgres non riuscita (OperationalError)")

    stato, esiti = _stato(), []
    pm.esegui_passo(4, passo_rotto, stato, esiti)
    assert stato["errore"]["testo"] == (
        "Passo 4 non riuscito: lettura da Postgres non riuscita (OperationalError)"
    )


def test_passo_riuscito_toglie_l_errore_precedente():
    stato, esiti = _stato(), []
    stato["errore"] = {"passo": 4, "testo": "Passo 4 non riuscito: TypeError"}
    pm.esegui_passo(
        4, lambda s: {"memoria": {"processo": 1.0, "massimo": 1.0}}, stato, esiti
    )
    assert "errore" not in stato
    assert len(esiti) == 1


def test_riepilogo_parziale_con_errore_e_ambiente():
    stato = _stato()
    esiti = [{"memoria": {"processo": 93.7, "massimo": 95.5}}]
    stato["errore"] = {"passo": 2, "testo": "Passo 2 non riuscito: TypeError"}
    testo = pm.riepilogo(stato, esiti)
    righe = testo.splitlines()
    assert any(r.startswith("python: ") for r in righe)
    assert any(r.startswith("torch: ") for r in righe)
    assert any(r.startswith("scheda grafica vista da torch: ") for r in righe)
    assert "Passo 1. Memoria all'avvio" in righe
    assert "  memoria: processo 93.700, massimo 95.500" in righe
    assert righe[-1] == "Passo 2 non riuscito: TypeError"
    assert "Regola scritta prima" not in testo


# --- 3. Esclusione degli avvisi ---


@pytest.mark.parametrize(
    ("meta", "avviso"),
    [
        (
            {"id_bando": "bando-x", "sha256": "ab" * 32, "tipo_documento": "avviso"},
            True,
        ),
        ({"id_bando": "mercati-rionali-2026", "tipo_documento": "bando"}, False),
        ({"id_bando": "", "tipo_documento": "regolamento"}, False),
        ({"tipo_documento": "piano"}, False),
        (None, False),
    ],
    ids=[
        "avviso caricato",
        "documento di sempre con id_bando",
        "documento con id_bando vuoto",
        "documento senza id_bando",
        "metadati assenti",
    ],
)
def test_avviso_riconosciuto_da_sha256(meta, avviso):
    assert pm.e_frammento_di_avviso(meta) is avviso


# --- 4. Parti della memoria del contenitore ---

MIB = 1024 * 1024


def test_parti_del_contenitore_cgroup_v2():
    stat = "\n".join(
        [
            f"anon {1500 * MIB}",
            f"file {1400 * MIB}",
            f"kernel {60 * MIB}",
            f"active_file {300 * MIB}",
            f"inactive_file {1100 * MIB}",
        ]
    )
    parti = pm.parti_del_contenitore(stat, 2960 * MIB)
    assert parti == {
        "contenitore anon": 1500.0,
        "contenitore file (cache)": 1400.0,
        "contenitore senza cache inattiva": 1860.0,
    }


def test_parti_del_contenitore_cgroup_v1():
    stat = "\n".join(
        [
            f"rss {10 * MIB}",
            f"total_rss {900 * MIB}",
            f"total_cache {2000 * MIB}",
            f"total_inactive_file {1900 * MIB}",
        ]
    )
    parti = pm.parti_del_contenitore(stat, 2950 * MIB)
    assert parti == {
        "contenitore anon": 900.0,
        "contenitore file (cache)": 2000.0,
        "contenitore senza cache inattiva": 1050.0,
    }


def test_parti_del_contenitore_senza_voci():
    assert pm.parti_del_contenitore("", 100 * MIB) == {}


# --- 5. Criterio scritto dopo la versione 1 ---


def _esiti(massimo, mediana, limite=3072.0):
    """Sette passi finti con i numeri che servono a regola e criterio."""
    esiti = [{"memoria": {"processo": 100.0, "massimo": 100.0}} for _ in range(7)]
    esiti[5]["riordino mediana"] = mediana
    esiti[6]["memoria"] = {"processo": 1727.4, "massimo": massimo}
    if limite is not None:
        esiti[6]["memoria"]["limite contenitore"] = limite
    return esiti


def test_criterio_con_i_numeri_della_versione_1():
    assert pm.esito_criterio(_esiti(1887.02, 2.862)) == [
        "  limite letto dal contenitore: 3072.0 MB",
        "  massimo dall'avvio, dopo il passo 7: 1887.0 MB, soglia 2048 MB, passa",
        "  7 passi nella stessa sessione, senza riavvio durante la misura: sì",
        "  mediana del riordino (passo 6): 2.862 s, soglia 10 s, passa",
        "  esito: passa",
    ]


def test_criterio_non_passa_sopra_2048():
    righe = pm.esito_criterio(_esiti(2048.0, 2.862))
    assert righe[1].endswith("soglia 2048 MB, non passa")
    assert righe[-1] == "  esito: non passa"


def test_criterio_non_passa_con_riordino_lento():
    assert pm.esito_criterio(_esiti(1887.0, 10.5))[-1] == "  esito: non passa"


def test_criterio_con_limite_diverso_tiene_la_soglia():
    righe = pm.esito_criterio(_esiti(1887.0, 2.862, limite=4096.0))
    assert righe[0] == (
        "  limite letto dal contenitore: 4096.0 MB"
        " (diverso dai 3072 della versione 1: la soglia resta 2048 MB)"
    )
    assert righe[-1] == "  esito: passa"


def test_criterio_senza_limite_o_massimo():
    esiti = _esiti(0, 2.862, limite=None)
    righe = pm.esito_criterio(esiti)
    assert righe[0] == "  limite letto dal contenitore: non leggibile"
    assert "non leggibile" in righe[1]
    assert righe[-1] == "  esito: non passa"


def test_riepilogo_regola_poi_criterio_separati():
    testo = pm.riepilogo(_stato(), _esiti(1887.02, 2.862))
    regola = testo.index("Regola scritta prima")
    criterio = testo.index("Criterio per il quarto caso, scritto dopo la versione 1")
    assert regola < criterio
    blocco_regola = testo[regola:criterio]
    assert "  esito: non passa" in blocco_regola
    assert testo.rstrip().endswith("  esito: passa")
