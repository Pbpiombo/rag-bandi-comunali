"""Ordine c-LR nella catena e nell'app (sotto-fermata 1.4 della fermata 1 del 19e).

Test della sezione 7 di docs/piano-fermata-1.md rimasti alla 1.4:
- punto 6 nella catena: il contesto di un frammento non arriva al modello,
  né al verificatore, né ai documenti dell'esito (regola R3);
- punto 8: recupera_riordinati chiede CANDIDATI_RIORDINO candidati ad
  avvolgi e riordina fuori; a interruttore spento prepara chiama recupera
  come prima; i vicini vengono dopo il riordino;
- a interruttore spento niente del motore si carica (né modelli né file dei
  contesti), e importare src.motore non carica modelli;
- l'archivio dell'app si costruisce sempre dal file dei contesti.

Nessun modello vero, database su file temporaneo (db_su_file di conftest).
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from langchain_core.documents import Document
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from src import motore as mo
from src.chains import rag
from src.config import CANDIDATI_RIORDINO
from src.verification.controllo import verifica
from tests.test_motore import motore_finto
from tests.test_vicini import db_con_ente  # noqa: F401 - fixture

RADICE = Path(__file__).resolve().parents[1]
ROUTER_FISSO = '{"documenti": true, "interrogazioni": []}'
SEGRETO = "987.654"


class RiordinatoreSegreto:
    """Voto alto alle coppie che contengono il segreto, poi in ordine di arrivo."""

    def __init__(self) -> None:
        self.coppie: list = []

    def predict(self, coppie, show_progress_bar=False):
        self.coppie.append(list(coppie))
        return np.asarray(
            [
                [0.0, 1.0 if SEGRETO in t else -0.01 * i]
                for i, (_, t) in enumerate(coppie)
            ]
        )


def con_router_e_modello(monkeypatch, risposta="ok") -> list:
    """Router fisso e modello finto che registra il testo ricevuto."""
    ricevuti: list = []

    def modello(valore):
        ricevuti.append(valore.to_string())
        return AIMessage(content=risposta)

    monkeypatch.setattr(
        rag, "costruisci_router", lambda: RunnableLambda(lambda _e: ROUTER_FISSO)
    )
    monkeypatch.setattr(rag, "ChatAnthropic", lambda **_: RunnableLambda(modello))
    return ricevuti


# --- punto 6, nella catena: il contesto non esce mai (R3) ---


# Il frammento con il contesto può arrivare alla catena da due strade: dalla
# ricerca per significato (documento di RicercaEsatta) o, se lì non è tra i
# primi 20, solo dalla ricerca per parole (documento di Motore.documenti). Con
# 10 frammenti di sempre è tra i primi 20 per significato; con 30, i 30 di
# sempre (più vicini alla domanda) lo spingono fuori, e resta la sola strada
# per parole. Il test controlla tutte e due, e quale strada ha preso.
STRADE = {10: "densa", 30: "lessicale"}


@pytest.mark.parametrize("altri", sorted(STRADE))
def test_il_contesto_non_arriva_a_modello_verificatore_e_documenti(
    db_con_ente,  # noqa: F811
    monkeypatch,
    altri,
):
    risposta = (
        f"Il contributo massimo è di {SEGRETO} euro (fonte: [1], ente, atto, pag. 1)."
    )
    ricevuti = con_router_e_modello(monkeypatch, risposta)
    monkeypatch.setattr(rag, "ORDINE_C_LR", True)
    motore = motore_finto(
        contesti={("avviso.pdf", 2): f"Contributo massimo {SEGRETO} euro"},
        altri=altri,
    )
    riordinatore = RiordinatoreSegreto()
    catena = rag.costruisci_catena(
        "11111111111", recupero=motore, riordino=mo.Riordino(riordinatore)
    )
    esito = catena.invoke("Qual è il contributo massimo?")

    # il contesto c'era ed è arrivato al riordino: il frammento è il primo
    assert any(SEGRETO in t for _, t in riordinatore.coppie[0])
    assert esito["documenti"][0].metadata["chunk_num"] == 2
    assert esito["origini"][0][-1] == "riordino #1"
    strade = {o.split(" #")[0] for o in esito["origini"][0][:-1]}
    assert STRADE[altri] in strade
    if altri == 30:
        assert strade == {"lessicale"}
    # ma non al modello, né nel contesto della catena
    assert len(ricevuti) == 1
    assert SEGRETO not in ricevuti[0]
    assert SEGRETO not in esito["contesto"]
    # né nei documenti dell'esito (le fonti mostrate)
    for d in esito["documenti"]:
        assert SEGRETO not in d.page_content
        assert SEGRETO not in repr(d.metadata)
    # né nel testo su cui lavora il verificatore: il dato non si trova
    esiti = verifica(esito["risposta"], esito["documenti"], esito["esiti_dati"])
    [dato] = [e for e in esiti if e.valore.startswith("987")]
    assert dato.stato == "non_trovato"


# --- punto 8: porta d'ingresso ---


class RecuperoRegistrato:
    """Un recupero finto: registra le richieste, dà `n` candidati numerati."""

    def __init__(self, n: int = 40) -> None:
        self.richieste: list = []
        self.contesti = {("f.pdf", 3): "contesto del tre"}
        self.documenti = [
            Document(
                page_content=f"testo {i}",
                metadata={"fonte": "f.pdf", "chunk_num": i, "page": 1},
            )
            for i in range(n)
        ]

    def titoli(self):
        return {}

    def cerca(self, domanda, k=10, fonte=None):
        self.richieste.append((domanda, k))
        return [
            (d, 1.0 / (i + 1), [f"densa #{i + 1}"])
            for i, d in enumerate(self.documenti[:k])
        ]

    def frammento(self, fonte, numero):
        return None


class RiordinoRegistrato:
    """Rovescia l'ordine dei candidati; registra domanda, candidati e contesti."""

    def __init__(self) -> None:
        self.chiamate: list = []

    def riordina_candidati(self, domanda, candidati, contesti, k):
        self.chiamate.append((domanda, list(candidati), contesti, k))
        rovesciati = list(reversed(candidati))[:k]
        return [
            (d, 0.5, [*o, f"riordino #{n}"])
            for n, (d, _, o) in enumerate(rovesciati, start=1)
        ]


def test_recupera_riordinati_chiede_i_candidati_e_riordina_fuori():
    recupero = RecuperoRegistrato()
    riordino = RiordinoRegistrato()
    uscita = rag.recupera_riordinati(
        recupero, riordino, recupero.contesti, "Quanto  dura", k=10
    )
    assert recupero.richieste == [("Quanto dura?", CANDIDATI_RIORDINO)]
    [(domanda, candidati, contesti, k)] = riordino.chiamate
    assert domanda == "Quanto dura?"
    assert len(candidati) == CANDIDATI_RIORDINO == 30
    assert contesti is recupero.contesti
    assert k == 10
    assert [d.metadata["chunk_num"] for d, _, _ in uscita] == list(range(29, 19, -1))


def test_interruttore_acceso_la_catena_riordina_e_i_vicini_vengono_dopo(
    db_con_ente,  # noqa: F811
    monkeypatch,
):
    con_router_e_modello(monkeypatch)
    monkeypatch.setattr(rag, "ORDINE_C_LR", True)
    dati_ai_vicini: list = []
    vicini_veri = rag.con_vicini

    def vicini_registrati(risultati, frammento, spostamenti):
        dati_ai_vicini.append([d.metadata["chunk_num"] for d, _, _ in risultati])
        return vicini_veri(risultati, frammento, spostamenti)

    monkeypatch.setattr(rag, "con_vicini", vicini_registrati)
    recupero = RecuperoRegistrato()
    riordino = RiordinoRegistrato()
    esito = rag.costruisci_catena(
        "11111111111", recupero=recupero, riordino=riordino
    ).invoke("Quanto  dura")
    # avvolgi ha chiesto 30 candidati al recupero; il riordino li ha avuti tutti
    assert ("Quanto dura?", CANDIDATI_RIORDINO) in recupero.richieste
    [(domanda, candidati, contesti, k)] = riordino.chiamate
    assert (domanda, len(candidati), k) == ("Quanto dura?", 30, 10)
    assert contesti is recupero.contesti
    # i vicini ricevono l'ordine del riordino, e i documenti lo seguono
    atteso = list(range(29, 19, -1))
    assert dati_ai_vicini == [atteso]
    assert [d.metadata["chunk_num"] for d in esito["documenti"]] == atteso
    assert all(o[-1].startswith("riordino #") for o in esito["origini"])


def test_interruttore_spento_prepara_chiama_recupera_come_prima(
    db_con_ente,  # noqa: F811
    monkeypatch,
):
    con_router_e_modello(monkeypatch)
    monkeypatch.setattr(rag, "ORDINE_C_LR", False)
    chiamate: list = []
    recupera_vera = rag.recupera

    def recupera_registrata(recupero, domanda, k=10):
        chiamate.append(k)
        return recupera_vera(recupero, domanda, k=k)

    def vietata(*_a, **_o):
        raise AssertionError("recupera_riordinati a interruttore spento")

    monkeypatch.setattr(rag, "recupera", recupera_registrata)
    monkeypatch.setattr(rag, "recupera_riordinati", vietata)
    recupero = RecuperoRegistrato()
    riordino = RiordinoRegistrato()
    esito = rag.costruisci_catena(
        "11111111111", recupero=recupero, riordino=riordino
    ).invoke("Quanto  dura")
    assert chiamate == [10]
    assert riordino.chiamate == []
    assert [d.metadata["chunk_num"] for d in esito["documenti"]] == list(range(10))
    assert all(not o[-1].startswith("riordino") for o in esito["origini"])


# --- interruttore spento: niente del motore si carica ---


def vietato(nome):
    def _(*_a, **_o):
        raise AssertionError(f"{nome} caricato a interruttore spento")

    return _


def test_interruttore_spento_la_catena_non_carica_niente_del_motore(
    db_con_ente,  # noqa: F811
    monkeypatch,
):
    con_router_e_modello(monkeypatch)
    monkeypatch.setattr(rag, "ORDINE_C_LR", False)
    for nome in (
        "carica_motore",
        "carica_embeddings",
        "carica_riordinatore",
        "leggi_righe_contesti",
    ):
        monkeypatch.setattr(mo, nome, vietato(nome))
    monkeypatch.setattr(mo.ArchivioChroma, "frammenti", vietato("ArchivioChroma"))
    # il recupero di prima, finto: costruirlo non deve aprire Chroma
    monkeypatch.setattr(rag, "RecuperoIbrido", RecuperoRegistrato)
    esito = rag.costruisci_catena("11111111111").invoke("Quanto  dura")
    assert len(esito["documenti"]) == 10


def test_interruttore_acceso_senza_recupero_la_catena_carica_il_motore(
    db_con_ente,  # noqa: F811
    monkeypatch,
):
    con_router_e_modello(monkeypatch)
    monkeypatch.setattr(rag, "ORDINE_C_LR", True)
    caricati: list = []

    def carica_motore():
        caricati.append(1)
        return RecuperoRegistrato(), RiordinoRegistrato()

    monkeypatch.setattr(mo, "carica_motore", carica_motore)
    monkeypatch.setattr(rag, "RecuperoIbrido", vietato("RecuperoIbrido"))
    esito = rag.costruisci_catena("11111111111").invoke("Quanto  dura")
    assert caricati == [1]
    assert esito["origini"][0][-1] == "riordino #1"


def test_importare_motore_e_catena_non_carica_modelli():
    codice = (
        "import sys\n"
        "import src.motore, src.chains.rag\n"
        "pesanti = [m for m in ('torch', 'sentence_transformers', 'transformers')"
        " if m in sys.modules]\n"
        "print(pesanti)\n"
    )
    uscita = subprocess.run(
        [sys.executable, "-c", codice],
        cwd=RADICE,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    assert uscita.stdout.strip().splitlines()[-1] == "[]"


# --- app: carica_recupero e avviso all'avvio ---


@pytest.fixture
def app_modulo(monkeypatch):
    """app/app.py importato come modulo, senza eseguire la pagina."""
    spec = importlib.util.spec_from_file_location(
        "app_per_i_test", RADICE / "app" / "app.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_app_interruttore_spento_su_chroma_non_carica_il_motore(
    app_modulo, monkeypatch
):
    monkeypatch.setattr(app_modulo, "USA_POSTGRES", False)
    monkeypatch.setattr(app_modulo, "ORDINE_C_LR", False)
    monkeypatch.setattr(mo, "carica_motore", vietato("carica_motore"))
    assert app_modulo.recupero_e_riordino() == (None, None)
    assert "spento" in app_modulo.avviso_ordine()


def test_app_con_postgres_l_interruttore_non_ha_effetto(app_modulo, monkeypatch):
    monkeypatch.setattr(app_modulo, "USA_POSTGRES", True)
    monkeypatch.setattr(app_modulo, "ORDINE_C_LR", True)
    monkeypatch.setattr(app_modulo, "RecuperoPostgres", lambda: "postgres")
    monkeypatch.setattr(mo, "carica_motore", vietato("carica_motore"))
    assert app_modulo.recupero_e_riordino() == ("postgres", None)
    assert "senza effetto" in app_modulo.avviso_ordine()
    assert "fermata 5" in app_modulo.avviso_ordine()


def test_app_interruttore_acceso_su_chroma_motore_e_riordino(app_modulo, monkeypatch):
    monkeypatch.setattr(app_modulo, "USA_POSTGRES", False)
    monkeypatch.setattr(app_modulo, "ORDINE_C_LR", True)
    monkeypatch.setattr(mo, "carica_motore", lambda: ("motore", "riordino"))
    assert app_modulo.recupero_e_riordino() == ("motore", "riordino")
    assert "acceso: motore" in app_modulo.avviso_ordine()


# --- l'archivio dell'app viene sempre dal file dei contesti ---


def test_carica_motore_legge_il_file_dei_contesti(monkeypatch, tmp_path):
    from tests.test_motore import get_con_avviso, riga_contesto

    file_contesti = tmp_path / "contesti_avvisi.jsonl"
    righe = [
        riga_contesto("avviso.pdf", 1, "primo dell'avviso", "Contesto uno"),
        riga_contesto("avviso.pdf", 2, "testo vecchio", "Contesto due"),
    ]
    file_contesti.write_text(
        "".join(json.dumps(r) + "\n" for r in righe), encoding="utf-8"
    )
    monkeypatch.setattr(mo.ArchivioChroma, "_leggi", lambda self: get_con_avviso())
    monkeypatch.setattr(mo, "carica_embeddings", lambda solo_locale=False: None)
    monkeypatch.setattr(mo, "carica_riordinatore", lambda solo_locale=False: "rr")
    motore, riordino = mo.carica_motore("non-si-apre", file_contesti=file_contesti)
    # la riga con l'impronta che non torna non si usa
    assert motore.contesti == {("avviso.pdf", 1): "Contesto uno"}
    assert riordino.modello == "rr"
    with pytest.raises(mo.ErroreContesti):
        mo.carica_motore("non-si-apre", file_contesti=tmp_path / "manca.jsonl")
