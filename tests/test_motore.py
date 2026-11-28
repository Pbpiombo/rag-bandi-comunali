"""Motore in memoria dell'ordine c-LR (src/motore.py), fermata 1 del 19e.

Test della sezione 7 di docs/piano-fermata-1.md che non chiedono il
collegamento alla catena (punti 1-5, 7 e la parte del punto 6 sul motore),
più il punto 9 e il confronto esatto dei Frammenti (sotto-fermata 1.3).
Nessun modello vero: embeddings finti (vettori fissati per testo) e
riordinatore finto (voti da un dizionario).
"""

import json
import sys
import types
from types import SimpleNamespace

import numpy as np
import pytest
from rank_bm25 import BM25Okapi

from src import motore as mo
from src.config import MODELLO_RIORDINO, REVISIONE_EMBEDDING, REVISIONE_RIORDINO
from src.retrieval import RecuperoIbrido, tokenizza


def unitario(*valori: float) -> list[float]:
    v = np.asarray(valori, dtype=np.float64)
    return list(v / np.linalg.norm(v))


class EmbeddingsFinti:
    """embed_query da un dizionario; le domande non elencate hanno `predefinito`."""

    def __init__(
        self, vettori: dict[str, list[float]], predefinito: list[float]
    ) -> None:
        self.vettori = vettori
        self.predefinito = predefinito

    def embed_query(self, testo: str) -> list[float]:
        return self.vettori.get(testo, self.predefinito)


def meta(fonte: str, n: int, **altro) -> dict:
    return {"fonte": fonte, "chunk_num": n, "titolo": f"Titolo {fonte}", **altro}


# --- 1. archivio: ordine per id ---


def test_frammenti_dal_get_di_chroma_escono_ordinati_per_id():
    dati = {
        "ids": ["c", "a", "b"],
        "documents": ["testo c", "testo a", "testo b"],
        "metadatas": [meta("f", 3), meta("f", 1), meta("f", 2)],
        "embeddings": np.asarray(
            [unitario(0, 0, 1), unitario(1, 0, 0), unitario(0, 1, 0)], dtype=np.float32
        ),
    }
    frammenti = mo.frammenti_da_get(dati)
    assert frammenti.ids == ("a", "b", "c")
    assert frammenti.testi == ("testo a", "testo b", "testo c")
    assert [m["chunk_num"] for m in frammenti.metadati] == [1, 2, 3]
    assert frammenti.matrice.dtype == np.float32
    assert np.array_equal(frammenti.matrice, dati["embeddings"][[1, 2, 0]])


def test_archivio_chroma_ordina_quello_che_legge(monkeypatch):
    disordinati = {
        "ids": ["z", "m"],
        "documents": ["tz", "tm"],
        "metadatas": [meta("f", 2), meta("f", 1)],
        "embeddings": [unitario(1, 0), unitario(0, 1)],
    }
    archivio = mo.ArchivioChroma("non-si-apre", contesti={("f", 1): "contesto"})
    monkeypatch.setattr(archivio, "_leggi", lambda: disordinati)
    frammenti = archivio.frammenti()
    assert frammenti.ids == ("m", "z")
    assert frammenti.contesti == {("f", 1): "contesto"}


def test_frammenti_non_ordinati_rifiutati():
    with pytest.raises(ValueError, match="ordinati"):
        mo.Frammenti(
            ids=("b", "a"),
            testi=("x", "y"),
            metadati=({}, {}),
            matrice=np.zeros((2, 2), dtype=np.float32),
        )


def test_vettori_di_postgres_con_to_numpy():
    class Vettore:  # come pgvector.Vector
        def __init__(self, valori):
            self.valori = valori

        def to_numpy(self):
            return np.asarray(self.valori, dtype=np.float32)

    matrice = mo.matrice_di([Vettore([0.6, 0.8]), Vettore([1.0, 0.0])])
    assert matrice.dtype == np.float32
    assert matrice.tolist() == [[pytest.approx(0.6), pytest.approx(0.8)], [1.0, 0.0]]


# --- 2. ricerca esatta: pari merito per id ---


def test_ricerca_esatta_a_pari_merito_vince_l_id_minore():
    # Arrivo in disordine (b prima di a), vettori identici: l'ordine non deve
    # dipendere dall'arrivo. La ricerca non si fida dell'ordine dei Frammenti.
    uguale = unitario(1, 1, 0)
    arrivo = SimpleNamespace(
        ids=("b", "a", "c"),
        testi=("tb", "ta", "tc"),
        metadati=(meta("f", 2), meta("f", 1), meta("f", 3)),
        matrice=np.asarray([uguale, uguale, unitario(0, 0, 1)], dtype=np.float32),
    )
    ricerca = mo.RicercaEsatta(arrivo, EmbeddingsFinti({}, unitario(1, 1, 0)))
    trovati = ricerca.similarity_search("domanda", k=3)
    assert [d.page_content for d in trovati] == ["ta", "tb", "tc"]


def test_ricerca_esatta_rifiuta_vettori_non_normalizzati():
    frammenti = mo.Frammenti.da_righe(["a"], ["t"], [meta("f", 1)], [[2.0, 0.0]])
    with pytest.raises(ValueError, match="normalizzati"):
        mo.RicercaEsatta(frammenti, EmbeddingsFinti({}, unitario(1, 0)))


# --- archivio finto per i test sul motore ---


def motore_finto(contesti=None, altri=10) -> mo.Motore:
    """Un bando B1 con quattro frammenti di avviso, più `altri` frammenti di sempre."""
    ids, testi, metadati, vettori = [], [], [], []

    def aggiungi(id_, testo, m, v):
        ids.append(id_)
        testi.append(testo)
        metadati.append(m)
        vettori.append(v)

    avviso = "avviso.pdf"
    aggiungi(
        "a1", "alfa alfa", meta(avviso, 1, id_bando="B1", sha256="x"), unitario(1, 0, 0)
    )
    aggiungi(
        "a2",
        "beta beta",
        meta(avviso, 2, id_bando="B1", sha256="x"),
        unitario(0.9, 0.1, 0),
    )
    aggiungi(
        "a3",
        "alfa gamma",
        meta(avviso, 3, id_bando="B1", sha256="x"),
        unitario(0, 1, 0),
    )
    aggiungi(
        "a4",
        "alfa delta",
        meta(avviso, 4, id_bando="B1", sha256="x"),
        unitario(0, 0.5, 1),
    )
    for n in range(altri):
        aggiungi(
            f"s{n:02d}", f"beta comune {n}", meta("sempre.pdf", n), unitario(0, 0, 1)
        )
    frammenti = mo.Frammenti.da_righe(ids, testi, metadati, vettori, contesti)
    return mo.Motore(frammenti, EmbeddingsFinti({}, unitario(0, 0, 1)))


# --- 3. BM25 con il contesto, documenti col testo pulito ---


def test_parola_solo_nel_contesto_trova_il_frammento_col_testo_pulito():
    motore = motore_finto(contesti={("avviso.pdf", 3): "Zafferano di montagna"})
    trovati = motore._lessicale("zafferano", 5)
    assert [d.metadata["chunk_num"] for d in trovati] == [3]
    assert trovati[0].page_content == "alfa gamma"
    risultati = motore.cerca("zafferano", k=5)
    documento, _, origini = next(
        r for r in risultati if r[0].metadata["chunk_num"] == 3
    )
    assert "lessicale #1" in origini
    assert documento.page_content == "alfa gamma"


# --- 4. ricerca ristretta a un bando ---


def test_cerca_nel_bando_pesa_le_parole_su_tutto_l_indice():
    # Nel bando "alfa" è comune e "beta" rara; su tutto l'indice il contrario
    # (i frammenti di sempre hanno tutti "beta"). Con il BM25 di tutto
    # l'indice vince a1 (alfa alfa), con quello del solo bando vincerebbe a2.
    motore = motore_finto()
    risultati = motore.cerca_nel_bando("alfa beta", "B1", k=10)
    assert {d.metadata["id_bando"] for d, _, _ in risultati} == {"B1"}
    per_posto = {
        o: d.metadata["chunk_num"]
        for d, _, origini in risultati
        for o in origini
        if o.startswith("lessicale")
    }
    assert per_posto["lessicale #1"] == 1
    # stesso ordine della ricerca per parole generale, ristretta al bando
    generale = [
        d.metadata["chunk_num"]
        for d in motore._lessicale("alfa beta", 50)
        if d.metadata.get("id_bando") == "B1"
    ]
    assert [
        per_posto[f"lessicale #{n}"] for n in range(1, len(per_posto) + 1)
    ] == generale


def test_cerca_nel_bando_somma_densa_e_lessicale_con_peso_uno():
    motore = motore_finto()
    risultati = motore.cerca_nel_bando("alfa beta", "B1", k=10)
    for _, punteggio, origini in risultati:
        atteso = sum(1 / (60 + int(o.split("#")[1])) for o in origini)
        assert punteggio == pytest.approx(atteso, rel=0, abs=1e-15)


# --- 5. fusione: la stessa di RecuperoIbrido.cerca ---


def test_cerca_del_motore_uguale_a_recupero_ibrido():
    contesti = {("avviso.pdf", 4): "beta delta contesto"}
    motore = motore_finto(contesti=contesti)
    ibrido = RecuperoIbrido.__new__(RecuperoIbrido)
    ibrido.store = motore.store
    ibrido.documenti = motore.documenti
    ibrido.bm25 = BM25Okapi(
        [
            tokenizza(mo.testo_con_contesto(d.page_content, d.metadata, contesti))
            for d in motore.documenti
        ]
    )
    for domanda in ("alfa beta", "delta", "comune 3", "nessuna parola"):
        for fonte in (None, "avviso.pdf"):
            attesi = RecuperoIbrido.cerca(ibrido, domanda, k=8, fonte=fonte)
            ottenuti = motore.cerca(domanda, k=8, fonte=fonte)
            assert [(d.page_content, d.metadata, p, o) for d, p, o in ottenuti] == [
                (d.page_content, d.metadata, p, o) for d, p, o in attesi
            ]


# --- 6. (parte del motore) il contesto non esce mai ---


def test_il_contesto_non_entra_in_nessun_documento():
    segreto = "987654"
    motore = motore_finto(contesti={("avviso.pdf", 2): f"Contesto con {segreto}"})
    usciti = list(motore.documenti)
    usciti += [d for d, _, _ in motore.cerca(segreto, k=20)]
    usciti += [d for d, _, _ in motore.cerca_nel_bando(segreto, "B1", k=20)]
    usciti += [motore.frammento("avviso.pdf", 2)]
    assert any(d.metadata["chunk_num"] == 2 for d in usciti[len(motore.documenti) :])
    for d in usciti:
        assert segreto not in d.page_content
        assert segreto not in repr(d.metadata)


# --- 7. riordino ---


class RiordinatoreFinto:
    """predict con voti a due colonne da un dizionario per testo; registra le coppie."""

    def __init__(self, voti: dict[str, float]) -> None:
        self.voti = voti
        self.coppie: list = []

    def predict(self, coppie, show_progress_bar=False):
        self.coppie.append(list(coppie))
        return np.asarray(
            [[-self.voti[t], self.voti[t]] for _, t in coppie], dtype=np.float32
        )


def candidato(testo: str, n: int) -> tuple:
    from langchain_core.documents import Document

    return Document(page_content=testo, metadata=meta("f.pdf", n)), 0.1, [f"densa #{n}"]


def test_riordino_coppie_pari_merito_e_ultima_colonna():
    candidati = [candidato("uno", 1), candidato("due", 2), candidato("tre", 3)]
    contesti = {("f.pdf", 2): "Il contesto"}
    finto = RiordinatoreFinto({"uno": 0.5, "Il contesto\ndue": 0.9, "tre": 0.5})
    uscita = mo.Riordino(finto).riordina_candidati("Domanda?", candidati, contesti, k=2)
    assert finto.coppie == [
        [("Domanda?", "uno"), ("Domanda?", "Il contesto\ndue"), ("Domanda?", "tre")]
    ]
    # due (0,9), poi uno e tre a pari merito nell'ordine di prima; k=2
    assert [d.page_content for d, _, _ in uscita] == ["due", "uno"]
    assert uscita[0][1] == pytest.approx(0.9)
    assert uscita[0][2] == ["densa #2", "riordino #1"]
    assert uscita[1][2] == ["densa #1", "riordino #2"]


def test_riordina_ultima_colonna_e_pari_merito():
    voti = np.asarray([[9.0, 0.1], [0.0, 0.7], [5.0, 0.1], [0.0, 0.1]])
    assert mo.riordina(voti, 4) == [1, 0, 2, 3]
    assert mo.riordina([0.2, 0.2, 0.3], 3) == [2, 0, 1]
    with pytest.raises(ValueError):
        mo.riordina([0.1], 2)


def test_riordino_senza_candidati():
    finto = RiordinatoreFinto({})
    assert mo.Riordino(finto).riordina_candidati("D?", [], {}, k=10) == []
    assert finto.coppie == []


# --- revisioni fissate (decisione 5) ---


def test_modelli_caricati_alle_revisioni_fissate(monkeypatch):
    chiamate = {}

    class CrossEncoderFinto:
        def __init__(self, nome, **opzioni):
            chiamate["riordino"] = (nome, opzioni)

    class EmbeddingsHF:
        def __init__(self, **opzioni):
            chiamate["embedding"] = opzioni

    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        types.SimpleNamespace(CrossEncoder=CrossEncoderFinto),
    )
    monkeypatch.setitem(
        sys.modules,
        "langchain_huggingface",
        types.SimpleNamespace(HuggingFaceEmbeddings=EmbeddingsHF),
    )
    mo.carica_riordinatore(solo_locale=True)
    mo.carica_embeddings()
    nome, opzioni = chiamate["riordino"]
    assert nome == MODELLO_RIORDINO
    assert opzioni["revision"] == REVISIONE_RIORDINO
    assert opzioni["trust_remote_code"] is False
    assert opzioni["local_files_only"] is True
    assert chiamate["embedding"]["model_kwargs"]["revision"] == REVISIONE_EMBEDDING
    assert chiamate["embedding"]["encode_kwargs"] == {"normalize_embeddings": True}


# --- 9. file dei contesti (sotto-fermata 1.3) ---


def get_con_avviso() -> dict:
    """Come get() di Chroma: due frammenti di un avviso (con sha256) e uno di sempre."""
    return {
        "ids": ["c", "a", "b"],
        "documents": ["testo di sempre", "primo dell'avviso", "secondo dell'avviso"],
        "metadatas": [
            meta("sempre.pdf", 0),
            meta("avviso.pdf", 1, id_bando="B1", sha256="x"),
            meta("avviso.pdf", 2, id_bando="B1", sha256="x"),
        ],
        "embeddings": [unitario(0, 0, 1), unitario(1, 0, 0), unitario(0, 1, 0)],
    }


def riga_contesto(fonte, n, testo, contesto) -> dict:
    return {
        "fonte": fonte,
        "chunk_num": n,
        "sha256_testo": mo.impronta_testo(testo),
        "contesto": contesto,
        "origine": "modello",
        "impronta_istruzioni": "a758adc6d26c",
    }


def archivio_con_file(monkeypatch, tmp_path, righe) -> mo.ArchivioChroma:
    percorso = tmp_path / "contesti_avvisi.jsonl"
    percorso.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in righe),
        encoding="utf-8",
    )
    archivio = mo.ArchivioChroma("non-si-apre", file_contesti=percorso)
    monkeypatch.setattr(archivio, "_leggi", get_con_avviso)
    return archivio


def test_file_contesti_riga_con_impronta_diversa_scartata_e_contata(
    monkeypatch, tmp_path
):
    archivio = archivio_con_file(
        monkeypatch,
        tmp_path,
        [
            riga_contesto("avviso.pdf", 1, "primo dell'avviso", "Contesto uno"),
            # scritto su un testo che il frammento non ha più
            riga_contesto("avviso.pdf", 2, "secondo, versione vecchia", "Contesto due"),
        ],
    )
    frammenti = archivio.frammenti()
    assert frammenti.contesti == {("avviso.pdf", 1): "Contesto uno"}
    assert archivio.scarti.impronta_diversa == [("avviso.pdf", 2)]
    assert archivio.scarti.totale() == 1
    assert "impronta del testo diversa 1" in archivio.scarti.rapporto()


def test_file_contesti_riga_su_frammento_senza_sha256_rifiutata(monkeypatch, tmp_path):
    # l'impronta del testo torna, ma il frammento non è di un avviso
    archivio = archivio_con_file(
        monkeypatch,
        tmp_path,
        [riga_contesto("sempre.pdf", 0, "testo di sempre", "Contesto di sempre")],
    )
    frammenti = archivio.frammenti()
    assert frammenti.contesti == {}
    assert archivio.scarti.non_di_avviso == [("sempre.pdf", 0)]
    assert archivio.scarti.totale() == 1


def test_file_contesti_frammento_assente_e_righe_ripetute_non_usate(
    monkeypatch, tmp_path
):
    archivio = archivio_con_file(
        monkeypatch,
        tmp_path,
        [
            riga_contesto("avviso.pdf", 9, "non c'è", "Contesto nove"),
            riga_contesto("avviso.pdf", 1, "primo dell'avviso", "Uno, prima copia"),
            riga_contesto("avviso.pdf", 1, "primo dell'avviso", "Uno, seconda copia"),
            riga_contesto("avviso.pdf", 2, "secondo dell'avviso", "Contesto due"),
        ],
    )
    frammenti = archivio.frammenti()
    assert frammenti.contesti == {("avviso.pdf", 2): "Contesto due"}
    assert archivio.scarti.senza_frammento == [("avviso.pdf", 9)]
    assert archivio.scarti.ripetute == [("avviso.pdf", 1)]
    assert archivio.scarti.totale() == 2


def test_file_contesti_mancante_ferma_l_archivio(monkeypatch, tmp_path):
    archivio = mo.ArchivioChroma("non-si-apre", file_contesti=tmp_path / "manca.jsonl")
    monkeypatch.setattr(archivio, "_leggi", get_con_avviso)
    with pytest.raises(mo.ErroreContesti, match="manca il file dei contesti"):
        archivio.frammenti()


def test_archivio_chroma_legge_il_file_dei_contesti_per_predefinito():
    assert mo.ArchivioChroma("x").file_contesti == mo.FILE_CONTESTI
    assert mo.FILE_CONTESTI.name == "contesti_avvisi.jsonl"
    assert mo.FILE_CONTESTI.parent == mo.CHROMA_DIR.parent


# --- confronto esatto di due Frammenti (sotto-fermata 1.3) ---


def frammenti_di_prova(**cambi) -> mo.Frammenti:
    campi = {
        "ids": ("a", "b"),
        "testi": ("ta", "tb"),
        "metadati": (meta("f", 1), meta("f", 2)),
        "matrice": np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
        "contesti": {("f", 1): "contesto a"},
    }
    campi.update(cambi)
    return mo.Frammenti(**campi)


def test_differenze_vuote_tra_frammenti_uguali():
    assert frammenti_di_prova().differenze(frammenti_di_prova()) == []


@pytest.mark.parametrize(
    ("campo", "cambio"),
    [
        ("ids", {"ids": ("a", "c")}),
        ("testi", {"testi": ("ta", "tb ")}),
        # stesso valore, tipo diverso: 2 contro 2.0
        ("metadati", {"metadati": (meta("f", 1), meta("f", 2.0))}),
        # 0.0 e -0.0 sono uguali per ==, non nei bit
        (
            "matrice",
            {"matrice": np.asarray([[1.0, -0.0], [0.0, 1.0]], dtype=np.float32)},
        ),
        ("contesti", {"contesti": {("f", 1): "contesto A"}}),
    ],
)
def test_differenze_trova_ogni_campo(campo, cambio):
    differenze = frammenti_di_prova().differenze(frammenti_di_prova(**cambio))
    assert len(differenze) == 1
    assert differenze[0].startswith(f"{campo}:")
