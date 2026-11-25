"""Prova di memoria per Streamlit Cloud (docs/prova-memoria.md).

Pagina a sé, sul ramo prova-memoria: non importa la catena né src.config,
non usa la chiave del modello di linguaggio e non scrive nel database.
Misura, un passo alla volta, la memoria del processo con i due modelli
(embedding e riordinatore) e con l'intera tabella dei frammenti in memoria,
e il tempo del riordino di 30 coppie.

Non mostra il testo dei frammenti né il contenuto dei secrets: dei frammenti
riordinati mostra solo un'impronta corta del testo, per confrontare i
punteggi con quelli del PC (docs/prova-memoria.md, "Confronto dei
punteggi").

Lettura dalla copia del Chroma: solo se la variabile d'ambiente
PROVA_MEMORIA_CHROMA indica la cartella di una copia. Online la variabile
non c'è e la pagina legge solo dalla tabella `chunk` di Postgres.
"""

import hashlib
import json
import os
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from importlib import metadata as metadati_pacchetti
from pathlib import Path

import numpy as np
import streamlit as st

# Stessi modelli dell'app e della misura del 19d: EMBEDDING_MODEL in
# src/config.py, RIORDINATORI["osiria"] in
# scripts/diagnostica/misura_recupero_avvisi.py. Copiati qui perché
# src.config chiede la chiave del modello di linguaggio.
MODELLO_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
RIORDINATORE = "osiria/minilm-l12-h384-italian-cross-encoder"
# I file che si scaricano del riordinatore: FILE_RIORDINATORE in
# scripts/diagnostica/misura_recupero_avvisi.py (niente varianti onnx o
# openvino).
FILE_RIORDINATORE = (
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "sentencepiece.bpe.model",
    "vocab.txt",
    "modules.json",
    "sentence_bert_config.json",
    "config_sentence_transformers.json",
    "README.md",
)
COLLEZIONE_CHROMA = "abetone_documenti"  # COLLECTION_NAME in src/config.py

DOMANDA = "Entro quale data devono essere sostenute le spese?"
COPPIE = 30
RIPETIZIONI = 10
RIORDINI_DI_FILA = 20
RICERCHE = 10

CARTELLA_CHROMA_VERA = (
    Path(__file__).resolve().parents[1] / "data" / "db" / "chroma"
).resolve()

MB = 1024 * 1024


class ErrorePagina(Exception):
    """Errore da mostrare nella pagina con un messaggio senza segreti."""


# --- Memoria e macchina --------------------------------------------------


def _leggi_intero(percorso: str) -> int | None:
    """Un numero da un file di sistema, o None se manca o non è un numero."""
    try:
        testo = Path(percorso).read_text().strip()
    except OSError:
        return None
    return int(testo) if testo.isdigit() else None


def _memoria_windows() -> tuple[int, int]:
    """Working set attuale e massimo del processo, in byte (solo Windows).

    Stesso metodo di memoria_del_processo in
    scripts/diagnostica/misura_recupero_avvisi.py, senza librerie nuove.
    """
    import ctypes
    from ctypes import wintypes

    class Contatori(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    contatori = Contatori()
    contatori.cb = ctypes.sizeof(Contatori)
    corrente = ctypes.windll.kernel32.GetCurrentProcess
    corrente.restype = wintypes.HANDLE
    informazioni = ctypes.windll.psapi.GetProcessMemoryInfo
    informazioni.argtypes = [wintypes.HANDLE, ctypes.POINTER(Contatori), wintypes.DWORD]
    informazioni.restype = wintypes.BOOL
    if not informazioni(corrente(), ctypes.byref(contatori), contatori.cb):
        return 0, 0
    return int(contatori.WorkingSetSize), int(contatori.PeakWorkingSetSize)


def memoria() -> dict:
    """Memoria del processo e, se leggibile, del contenitore, in MB.

    processo: VmRSS di /proc/self/status (working set su Windows).
    massimo: VmHWM di /proc/self/status (picco del working set su Windows).
    contenitore: memoria del cgroup (tutti i processi del contenitore),
    con il limite, se il sistema li espone.
    """
    if sys.platform == "win32":
        attuale, massimo = _memoria_windows()
        return {"processo": attuale / MB, "massimo": massimo / MB}
    valori = {}
    try:
        for riga in Path("/proc/self/status").read_text().splitlines():
            nome, _, resto = riga.partition(":")
            if nome in ("VmRSS", "VmHWM"):
                valori[nome] = int(resto.split()[0]) * 1024
    except OSError:
        pass
    if "VmHWM" not in valori:
        import resource

        valori["VmHWM"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    risultato = {
        "processo": valori.get("VmRSS", 0) / MB,
        "massimo": valori["VmHWM"] / MB,
    }
    # cgroup v2, poi v1
    for usata, limite in (
        ("/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory.max"),
        (
            "/sys/fs/cgroup/memory/memory.usage_in_bytes",
            "/sys/fs/cgroup/memory/memory.limit_in_bytes",
        ),
    ):
        valore = _leggi_intero(usata)
        if valore is not None:
            risultato["contenitore"] = valore / MB
            tetto = _leggi_intero(limite)
            if tetto is not None and tetto < 2**60:
                risultato["limite contenitore"] = tetto / MB
            break
    return risultato


def macchina() -> dict:
    """Quello che serve a leggere i tempi e a confrontare i punteggi."""
    dati = {
        "python": platform.python_version(),
        "sistema": platform.platform(),
        "processori visti": os.cpu_count(),
    }
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text()
    except OSError:
        dati["processore"] = platform.processor()
    else:
        for riga in cpuinfo.splitlines():
            if riga.startswith("model name"):
                dati["processore"] = riga.partition(":")[2].strip()
            if riga.startswith("flags"):
                bandiere = set(riga.partition(":")[2].split())
                dati["avx2"] = "avx2" in bandiere
                dati["avx512f"] = "avx512f" in bandiere
                break
    quota = Path("/sys/fs/cgroup/cpu.max")
    if quota.exists():
        try:
            dati["quota processore (cpu.max)"] = quota.read_text().strip()
        except OSError:
            pass
    nvidia = sorted(
        d.metadata["Name"]
        for d in metadati_pacchetti.distributions()
        if (d.metadata["Name"] or "").lower().startswith("nvidia-")
    )
    dati["pacchetti nvidia installati"] = len(nvidia)
    return dati


# --- Lettura dei frammenti ------------------------------------------------


def url_database() -> str | None:
    """DATABASE_URL dall'ambiente o dai secrets; il valore non si mostra."""
    valore = os.getenv("DATABASE_URL")
    if valore:
        return valore
    try:
        return st.secrets.get("DATABASE_URL")
    except FileNotFoundError:
        return None


def leggi_da_postgres(url: str) -> dict:
    """Tutta la tabella chunk in sola lettura, vettori in forma binaria.

    I byte letti sono la somma delle celle come arrivano dal server
    (risultato binario), senza l'involucro del protocollo.
    """
    import psycopg
    from pgvector.psycopg import register_vector

    inizio = time.perf_counter()
    try:
        with psycopg.connect(url) as conn:
            conn.read_only = True
            register_vector(conn)
            with conn.cursor(binary=True) as cursore:
                cursore.execute("SELECT id, testo, metadata, embedding FROM chunk")
                righe = cursore.fetchall()
                risultato = cursore.pgresult
                per_colonna = [0, 0, 0, 0]
                for i in range(risultato.ntuples):
                    for j in range(risultato.nfields):
                        valore = risultato.get_value(i, j)
                        per_colonna[j] += len(valore) if valore is not None else 0
            conn.rollback()
    except psycopg.Error as errore:
        # Solo il tipo: il messaggio di una connessione può contenere
        # l'indirizzo del database, che sta nei secrets.
        raise ErrorePagina(
            f"lettura da Postgres non riuscita ({type(errore).__name__})"
        ) from None
    tempo = time.perf_counter() - inizio
    return {
        "ids": [str(r[0]) for r in righe],
        "testi": [r[1] for r in righe],
        "metadati": [r[2] or {} for r in righe],
        "vettori": np.vstack([np.asarray(r[3], dtype=np.float32) for r in righe]),
        "byte": dict(
            zip(("id", "testo", "metadati", "vettori"), per_colonna, strict=True)
        ),
        "byte_misurati": True,
        "tempo": tempo,
        "esclusi": 0,
    }


def leggi_da_chroma(cartella: str) -> dict:
    """Frammenti dalla copia del Chroma, senza gli avvisi (metadato id_bando).

    Senza gli avvisi l'insieme somiglia a quello della tabella online. I byte
    sono una stima: testo in UTF-8, metadati in JSON, vettori a 4 byte per
    numero.
    """
    import chromadb

    inizio = time.perf_counter()
    cliente = chromadb.PersistentClient(path=cartella)
    collezione = cliente.get_collection(COLLEZIONE_CHROMA)
    dati = collezione.get(include=["documents", "metadatas", "embeddings"])
    tempo = time.perf_counter() - inizio
    tenuti = [
        i
        for i, meta in enumerate(dati["metadatas"])
        if not (meta or {}).get("id_bando")
    ]
    ids = [dati["ids"][i] for i in tenuti]
    testi = [dati["documents"][i] for i in tenuti]
    metadati = [dati["metadatas"][i] or {} for i in tenuti]
    vettori = np.asarray(dati["embeddings"], dtype=np.float32)[tenuti]
    return {
        "ids": ids,
        "testi": testi,
        "metadati": metadati,
        "vettori": vettori,
        "byte": {
            "id": sum(len(x.encode()) for x in ids),
            "testo": sum(len(t.encode()) for t in testi),
            "metadati": sum(len(json.dumps(m).encode()) for m in metadati),
            "vettori": int(vettori.nbytes),
        },
        "byte_misurati": False,
        "tempo": tempo,
        "esclusi": len(dati["ids"]) - len(tenuti),
    }


# --- Ricerca e riordino ---------------------------------------------------


def tokenizza(testo: str) -> list[str]:
    """Copia di tokenizza in src/retrieval.py (che importa src.config)."""
    import re

    testo = testo.lower()
    composti = re.findall(r"\b[\w.]*\d[\w./-]*\b", testo)
    parole = re.findall(r"[a-zàèéìòù]{2,}", testo)
    token = list(parole)
    for pezzo in composti:
        token.append(pezzo)
        token.extend(re.findall(r"\w+", pezzo))
    return token


def impronta(testo: str) -> str:
    """Impronta corta del testo: identifica il frammento senza mostrarlo."""
    return hashlib.sha1(testo.encode()).hexdigest()[:10]


def riordina(riordinatore, coppie: list[tuple[str, str]]) -> tuple[float, list]:
    """Un riordino: tempo in secondi e punteggi."""
    inizio = time.perf_counter()
    punteggi = riordinatore.predict(coppie, show_progress_bar=False)
    return time.perf_counter() - inizio, [float(p) for p in punteggi]


# --- I passi --------------------------------------------------------------


def passo_avvio(stato: dict) -> dict:
    return {"memoria": memoria(), "macchina": macchina()}


def passo_embedding(stato: dict) -> dict:
    inizio = time.perf_counter()
    import torch
    from sentence_transformers import SentenceTransformer

    importazione = time.perf_counter() - inizio
    inizio = time.perf_counter()
    stato["embedding"] = SentenceTransformer(MODELLO_EMBEDDING)
    caricamento = time.perf_counter() - inizio
    return {
        "memoria": memoria(),
        "tempi": {
            "import di torch e sentence-transformers": importazione,
            "scaricamento e caricamento": caricamento,
        },
        "torch": torch.__version__,
        "thread di torch": torch.get_num_threads(),
        "cuda disponibile": torch.cuda.is_available(),
    }


def passo_riordinatore(stato: dict) -> dict:
    from huggingface_hub import snapshot_download
    from sentence_transformers import CrossEncoder

    inizio = time.perf_counter()
    cartella = snapshot_download(RIORDINATORE, allow_patterns=list(FILE_RIORDINATORE))
    scaricamento = time.perf_counter() - inizio
    inizio = time.perf_counter()
    stato["riordinatore"] = CrossEncoder(cartella, trust_remote_code=False)
    caricamento = time.perf_counter() - inizio
    byte_su_disco = sum(
        f.stat().st_size for f in Path(cartella).rglob("*") if f.is_file()
    )
    return {
        "memoria": memoria(),
        "tempi": {"scaricamento": scaricamento, "caricamento": caricamento},
        "MB su disco": byte_su_disco / MB,
    }


def passo_tabella(stato: dict) -> dict:
    if stato["fonte"] == "chroma":
        dati = leggi_da_chroma(stato["cartella_chroma"])
    else:
        dati = leggi_da_postgres(stato["url"])
    stato["dati"] = dati
    righe = len(dati["testi"])
    totale = sum(dati["byte"].values())
    return {
        "memoria": memoria(),
        "tempi": {"lettura": dati["tempo"]},
        "righe": righe,
        "avvisi esclusi (solo Chroma)": dati["esclusi"],
        "byte": dati["byte"],
        "byte totali": totale,
        "byte misurati sul risultato": dati["byte_misurati"],
        "dimensione dei vettori": int(dati["vettori"].shape[1]) if righe else 0,
    }


def passo_indice(stato: dict) -> dict:
    from rank_bm25 import BM25Okapi

    inizio = time.perf_counter()
    stato["bm25"] = BM25Okapi([tokenizza(t) for t in stato["dati"]["testi"]])
    costruzione = time.perf_counter() - inizio
    return {"memoria": memoria(), "tempi": {"costruzione": costruzione}}


def passo_riordino(stato: dict) -> dict:
    dati = stato["dati"]
    embedding = stato["embedding"]
    bm25 = stato["bm25"]

    tempi_densa = []
    for _ in range(RICERCHE):
        inizio = time.perf_counter()
        vettore = embedding.encode(DOMANDA, normalize_embeddings=True)
        punti = dati["vettori"] @ vettore.astype(np.float32)
        ordine = np.argsort(-punti, kind="stable")[:COPPIE]
        tempi_densa.append(time.perf_counter() - inizio)
    tempi_lessicale = []
    for _ in range(RICERCHE):
        inizio = time.perf_counter()
        bm25.get_scores(tokenizza(DOMANDA))
        tempi_lessicale.append(time.perf_counter() - inizio)

    scelti = [int(i) for i in ordine]
    coppie = [(DOMANDA, dati["testi"][i]) for i in scelti]
    stato["coppie"] = coppie
    tempi = []
    serie = []
    for _ in range(RIPETIZIONI):
        tempo, punteggi = riordina(stato["riordinatore"], coppie)
        tempi.append(tempo)
        serie.append(punteggi)
    stabili = all(p == serie[0] for p in serie)
    punteggi = serie[0]
    riordinati = sorted(range(len(scelti)), key=lambda k: -punteggi[k])
    return {
        "memoria": memoria(),
        "coppie": len(coppie),
        "riordino mediana": statistics.median(tempi),
        "riordino massimo": max(tempi),
        "ricerca densa esatta mediana": statistics.median(tempi_densa),
        "BM25 mediana": statistics.median(tempi_lessicale),
        "punteggi identici tra le ripetizioni": stabili,
        "impronte": [
            (
                impronta(dati["testi"][scelti[k]]),
                round(float(punti[scelti[k]]), 6),
                round(punteggi[k], 6),
            )
            for k in riordinati
        ],
    }


def passo_di_fila(stato: dict) -> dict:
    tempi = [
        riordina(stato["riordinatore"], stato["coppie"])[0]
        for _ in range(RIORDINI_DI_FILA)
    ]
    return {
        "memoria": memoria(),
        "riordino mediana": statistics.median(tempi),
        "riordino massimo": max(tempi),
    }


PASSI = [
    ("Memoria all'avvio", passo_avvio),
    ("Modello di embedding", passo_embedding),
    ("Riordinatore", passo_riordinatore),
    ("Tabella dei frammenti", passo_tabella),
    ("Indice lessicale", passo_indice),
    (f"Riordino di {COPPIE} coppie, {RIPETIZIONI} volte", passo_riordino),
    (f"{RIORDINI_DI_FILA} riordini di fila", passo_di_fila),
]


# --- Riepilogo ------------------------------------------------------------


def _numero(valore) -> str:
    if isinstance(valore, float):
        return f"{valore:.3f}"
    return str(valore)


def riepilogo(stato: dict, esiti: list[dict]) -> str:
    """Testo semplice da copiare, con la regola scritta prima."""
    righe = [
        "Prova di memoria (docs/prova-memoria.md)",
        f"data: {stato['inizio']}",
        f"fonte dei frammenti: {stato['fonte']}",
        f"domanda fissa: {DOMANDA}",
    ]
    for n, ((titolo, _), esito) in enumerate(zip(PASSI, esiti, strict=False), 1):
        righe.append("")
        righe.append(f"Passo {n}. {titolo}")
        for chiave, valore in esito.items():
            if chiave == "impronte":
                righe.append(
                    "  impronte (testo, prodotto scalare, punteggio del riordinatore),"
                    " in ordine di riordino:"
                )
                righe.extend(f"    {i} {d:.6f} {r:.6f}" for i, d, r in valore)
            elif isinstance(valore, dict):
                interno = ", ".join(f"{k} {_numero(v)}" for k, v in valore.items())
                righe.append(f"  {chiave}: {interno}")
            else:
                righe.append(f"  {chiave}: {_numero(valore)}")
    if len(esiti) == len(PASSI):
        righe += ["", "Regola scritta prima (docs/prova-memoria.md, sezione 2):"]
        righe += esito_regola(esiti)
    return "\n".join(righe)


def esito_regola(esiti: list[dict]) -> list[str]:
    """Le tre condizioni, una per riga con valore e soglia, e l'esito.

    Un valore non leggibile (assente o non positivo) non passa.
    """
    memoria_finale = esiti[-1]["memoria"]
    condizioni = [
        ("memoria dopo il passo 7", memoria_finale.get("processo"), 540, "MB", 1),
        (
            "massimo dall'avvio, dopo il passo 7",
            memoria_finale.get("massimo"),
            690,
            "MB",
            1,
        ),
        (
            "mediana del riordino (passo 6)",
            esiti[5].get("riordino mediana"),
            10,
            "s",
            3,
        ),
    ]
    righe = []
    tutte = True
    for nome, valore, soglia, unita, cifre in condizioni:
        if valore is None or valore <= 0:
            tutte = False
            righe.append(f"  {nome}: non leggibile (soglia {soglia} {unita})")
            continue
        passa = valore < soglia
        tutte = tutte and passa
        righe.append(
            f"  {nome}: {valore:.{cifre}f} {unita}, soglia {soglia} {unita},"
            f" {'passa' if passa else 'non passa'}"
        )
    righe.append(f"  esito: {'passa' if tutte else 'non passa'}")
    return righe


# --- Pagina ---------------------------------------------------------------

st.set_page_config(page_title="Prova di memoria", page_icon=":material/memory:")
st.title("Prova di memoria")
st.caption(
    "Pagina di prova del ramo prova-memoria: niente modello di linguaggio, "
    "sola lettura sulla tabella dei frammenti. Una sola scheda aperta: "
    "un'altra scheda raddoppia i modelli in memoria."
)

if "stato" not in st.session_state:
    st.session_state.stato = {
        "inizio": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
    }
    st.session_state.esiti = []
stato = st.session_state.stato
esiti = st.session_state.esiti

cartella_chroma = os.getenv("PROVA_MEMORIA_CHROMA")
usa_chroma = False
if cartella_chroma:
    usa_chroma = st.toggle(
        "Leggi i frammenti dalla copia del Chroma (solo per la prova in locale)",
        value=True,
        disabled=bool(esiti),
    )
if usa_chroma:
    copia = Path(cartella_chroma).resolve()
    if copia == CARTELLA_CHROMA_VERA or CARTELLA_CHROMA_VERA in copia.parents:
        st.error("La cartella indicata è il Chroma vero: serve una copia.")
        st.stop()
    stato["fonte"] = "chroma"
    stato["cartella_chroma"] = str(copia)
else:
    stato["fonte"] = "postgres"
    url = url_database()
    if not url:
        st.error("Manca DATABASE_URL nei secrets.")
        st.stop()
    stato["url"] = url
st.write(f"Fonte dei frammenti: **{stato['fonte']}**")

for numero, (titolo, funzione) in enumerate(PASSI, 1):
    with st.container(border=True):
        fatto = numero <= len(esiti)
        if st.button(
            f"{numero}. {titolo}",
            key=f"passo_{numero}",
            disabled=numero != len(esiti) + 1,
        ):
            with st.spinner("In corso..."):
                try:
                    esiti.append(funzione(stato))
                except ErrorePagina as errore:
                    st.error(f"Passo {numero} non riuscito: {errore}")
                    st.stop()
            st.rerun()
        if fatto:
            esito = esiti[numero - 1]
            mem = esito["memoria"]
            st.write(
                f"Memoria del processo: **{mem['processo']:.1f} MB** "
                f"(massimo {mem['massimo']:.1f} MB)"
            )
            altro = {k: v for k, v in esito.items() if k not in ("memoria", "impronte")}
            if "contenitore" in mem:
                altro["contenitore"] = {
                    k: v for k, v in mem.items() if k not in ("processo", "massimo")
                }
            st.json(altro, expanded=False)

if esiti:
    st.subheader("Riepilogo da copiare")
    st.code(riepilogo(stato, esiti), language=None)
