"""Caricamento in Chroma dei PDF degli avvisi (passo 19, compito 19c-3).

Uso:
    python -u -m scripts.ingestione.carica_avvisi --prova
    python -u -m scripts.ingestione.carica_avvisi
    python -u -m scripts.ingestione.carica_avvisi --togli-scaduti [--giorni 365]

Legge data/processed/documenti_bandi.csv (scripts/ingestione/registra_avvisi.py)
e carica nell'archivio locale dei documenti (Chroma) solo i file con uso
"frammenti". Solo Chroma: nessun import di pgstore o psycopg, l'app online
(Postgres) non vede nulla fino al compito 19e.

Per ogni file:
1. il file si cerca in dati-grezzi/avvisi/<scaricato_il>/ e la sua
   impronta deve essere quella del registro;
2. pulizia del compito 19c-1 (src/ingestion/avvisi.py): righe ripetute,
   contatti di persone, parole spezzate a fine riga;
3. divisione di sempre (src/ingestion/testo.spezza: 1500 caratteri, 250
   di sovrapposizione), con la ricucitura "prudente" dei numeri;
4. controllo dei numeri: ogni numero di un frammento deve comparire nel
   testo grezzo della stessa pagina (il testo del lettore con i soli
   spazi normalizzati). Eccezioni: gli anni e i numeri con /anno ricuciti
   dalla regola prudente, e i numeri che compaiono togliendo gli spazi
   attorno a "/" tra due cifre ("2021/ 2115"), che il rapporto elenca a
   parte come "ricuciti alla barra". I numeri che non passano si elencano;
5. metadati da bandi (id_bando, titolo, ente) e dal registro (classe come
   tipo_documento, atto come riferimento_atto, parte, sha256), più page,
   fonte (nome del file), chunk_num, token, car_visti, tabella_probabile.
   Nessuna scadenza e nessuno stato: si calcolano dall'archivio a ogni
   domanda (src/database/stato_documenti.py). L'intestazione del
   frammento non entra nel testo: la costruisce rag.etichetta dai
   metadati, e il verificatore controlla i dati sul solo testo;
6. id dei frammenti sha256[:16]::i; prima di scrivere un file si tolgono
   tutti i frammenti con lo stesso sha256, così il rilancio non crea
   doppioni e un file che produce meno frammenti non ne lascia di vecchi.

Un file con uso "frammenti" per più di un bando ferma lo script
(decisione del 20/11/2026).

--prova: fa tutto tranne aprire Chroma e scrivere; stampa il rapporto.
--togli-scaduti: toglie da Chroma i frammenti degli avvisi dei bandi la
cui ultima scadenza è passata da più di --giorni giorni (predefinito 365:
lo storico dell'app copre dodici mesi). Senza l'opzione non si toglie
nulla. Con --prova Chroma non si apre, e l'opzione lo dice senza fare
niente. Tocca solo i frammenti con il metadato sha256, cioè quelli
caricati da questo script.

Rete: le librerie di Hugging Face leggono il modello di embedding solo
dalla copia su disco (HF_HUB_OFFLINE=1, TRANSFORMERS_OFFLINE=1) e la
telemetria di Chroma è spenta (ANONYMIZED_TELEMETRY=False). Le variabili
si impostano in main, prima di importare quelle librerie.
"""

import argparse
import csv
import io
import os
import re
import statistics
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

from langchain_core.documents import Document

from scripts.ingestione.elenco_pdf_bandi import cartella_di, cartella_file
from scripts.ingestione.registra_avvisi import FRAMMENTI, NOME_FILE, SEPARATORE
from src.config import CHUNK_OVERLAP, CHUNK_SIZE, EMBEDDING_MODEL, PROCESSED_DIR
from src.estrazione import pdf_bando as pb
from src.ingestion.avvisi import Sostituzione, pulisci_avviso
from src.ingestion.testo import applica_metadati, e_indice, pulisci, spezza

SENZA_RETE = {
    "HF_HUB_OFFLINE": "1",
    "TRANSFORMERS_OFFLINE": "1",
    "ANONYMIZED_TELEMETRY": "False",
}

# Il modello di embedding vede i primi 128 token, [CLS] e [SEP] compresi
MASSIMO_TOKEN = 128

# Un frammento ha probabilmente una tabella se ha almeno RIGHE_TABELLA
# righe brevi di seguito (meno di pb.RIGA_BREVE caratteri), e almeno
# CIFRE_TABELLA di queste hanno una cifra
RIGHE_TABELLA = 4
CIFRE_TABELLA = 2

NUMERO = re.compile(r"\d+(?:[.,/]\d+)*")
ANNO_O_NUMERO_CON_ANNO = re.compile(r"(?:\d+/)?(?:19|20)\d\d")


class ErroreCaricamento(Exception):
    """Un ingresso che non torna: si riporta, non si indovina."""


def senza_rete() -> None:
    """Impedisce alle librerie del modello di embedding e a Chroma di usare la rete."""
    for nome, valore in SENZA_RETE.items():
        os.environ[nome] = valore


# --- registro e bandi ---


def leggi_registro(percorso: Path) -> list[dict]:
    """Le righe del registro con uso "frammenti"; errore se una è per più bandi."""
    if not percorso.is_file():
        raise ErroreCaricamento(f"registro non trovato: {percorso}")
    with percorso.open(encoding="utf-8-sig", newline="") as f:
        righe = [r for r in csv.DictReader(f) if r["uso"] == FRAMMENTI]
    for riga in righe:
        if SEPARATORE in riga["id_bandi"]:
            raise ErroreCaricamento(
                f"{riga['sha256'][:12]}: uso frammenti per più bandi "
                f"({riga['id_bandi']}): per ora non si carica"
            )
    return righe


def percorso_del_file(riga: dict, radice: Path | None = None) -> Path:
    """Il file su disco, verificato con l'impronta del registro."""
    cartella = (
        radice / riga["scaricato_il"] if radice else cartella_di(riga["scaricato_il"])
    )
    percorso = cartella_file(cartella, riga["id_bandi"]) / riga["nome_file"]
    if not percorso.is_file():
        raise ErroreCaricamento(f"file non trovato: {percorso}")
    impronta = pb.impronta_file(percorso)
    if impronta != riga["sha256"]:
        raise ErroreCaricamento(
            f"{percorso.name}: impronta {impronta[:12]}, nel registro {riga['sha256'][:12]}"
        )
    return percorso


def bando(conn, id_bando: str):
    riga = conn.execute(
        "SELECT id, titolo, ente, scadenza FROM bandi WHERE id = ?", (id_bando,)
    ).fetchone()
    if riga is None:
        raise ErroreCaricamento(f"bando non in archivio: {id_bando}")
    return riga


# --- controllo dei numeri ---


def grezzo(testo: str) -> str:
    """Il testo del lettore con i soli spazi normalizzati."""
    return re.sub(r"[ \t]+", " ", testo.replace("\u00a0", " "))


def _presente(numero: str, testo: str) -> bool:
    """Il numero compare intero: non dentro un numero più lungo."""
    schema = rf"(?<![\d])(?<![\d][.,/]){re.escape(numero)}(?![\d])(?![.,/]\d)"
    return re.search(schema, testo) is not None


# Spazi attorno a una barra tra due cifre: "2021/ 2115", "30/3 /2015"
BARRA_CON_SPAZI = re.compile(r"(?<=\d)[ \t]*/[ \t]*(?=\d)")


def _alla_barra(numero: str, testo: str) -> str | None:
    """Il tratto del testo con il numero scritto con spazi attorno alle barre."""
    schema = r"[ \t]*/[ \t]*".join(re.escape(p) for p in numero.split("/"))
    m = re.search(rf"(?<![\d])(?<![\d][.,/]){schema}(?![\d])(?![.,/]\d)", testo)
    return m.group(0) if m else None


def controlla_numeri(
    frammento: str, pagina_grezza: str
) -> tuple[list[str], list[tuple[str, str]]]:
    """I numeri del frammento non trovati nel testo grezzo della pagina, e
    quelli trovati solo togliendo gli spazi attorno a una barra tra cifre.

    Passano anche gli anni e i numeri con /anno che la ricucitura prudente
    ha formato da cifre separate ("202 6", "41/202 2", "1 060/2021").
    Passa un numero che compare nel testo grezzo dopo aver tolto gli spazi
    attorno a "/" tra due cifre ("2021/ 2115"): la ricucitura prudente li
    toglie. Questi si restituiscono a parte, con il testo del PDF, perché
    il rapporto li elenchi. Una cella fusa ("B140.000,00" da "B1 40.000,00")
    non passa mai.
    """
    testo = grezzo(pagina_grezza)
    ricucito = pulisci(pagina_grezza, ricucitura="prudente")
    senza_spazi = BARRA_CON_SPAZI.sub("/", testo)
    mancanti: list[str] = []
    alla_barra: list[tuple[str, str]] = []
    for numero in NUMERO.findall(frammento):
        if _presente(numero, testo):
            continue
        if ANNO_O_NUMERO_CON_ANNO.fullmatch(numero) and _presente(numero, ricucito):
            continue
        if "/" in numero and _presente(numero, senza_spazi):
            alla_barra.append((numero, _alla_barra(numero, testo) or ""))
            continue
        mancanti.append(numero)
    return mancanti, alla_barra


def numeri_non_trovati(frammento: str, pagina_grezza: str) -> list[str]:
    """I numeri del frammento che non passano il controllo (controlla_numeri)."""
    return controlla_numeri(frammento, pagina_grezza)[0]


# --- misure per il 19d ---


def tabella_probabile(testo: str) -> bool:
    """Righe brevi di seguito, alcune con cifre: probabilmente una tabella."""
    di_seguito: list[str] = []
    for riga in (r.strip() for r in testo.split("\n")):
        if not riga:
            continue
        if len(riga) < pb.RIGA_BREVE:
            di_seguito.append(riga)
            if (
                len(di_seguito) >= RIGHE_TABELLA
                and sum(any(c.isdigit() for c in r) for r in di_seguito)
                >= CIFRE_TABELLA
            ):
                return True
        else:
            di_seguito = []
    return False


def misura_token(tokenizer, testo: str) -> tuple[int, int]:
    """I token del frammento ([CLS] e [SEP] compresi) e i caratteri che il modello vede."""
    codifica = tokenizer(testo, return_offsets_mapping=True)
    token = len(codifica["input_ids"])
    if token <= MASSIMO_TOKEN:
        return token, len(testo)
    # tenuti: [CLS], 126 token del testo, [SEP]; l'ultimo tenuto è il 126°
    return token, codifica["offset_mapping"][MASSIMO_TOKEN - 2][1]


# --- un file ---


@dataclass
class EsitoFile:
    """I frammenti di un file e quello che il rapporto ne dice."""

    riga: dict
    frammenti: list[Document]
    pagine_lette: int
    saltate: list[tuple[int, str]]
    contatti: list[tuple[int, Sostituzione]]
    righe_tolte: int
    parole_ricucite: int
    # (frammento, pagina, numero)
    numeri_mancanti: list[tuple[int, int, str]] = field(default_factory=list)
    # (frammento, pagina, numero, testo del PDF)
    ricuciti_barra: list[tuple[int, int, str, str]] = field(default_factory=list)


def pagine_del_pdf(percorso: Path) -> list[str]:
    """I testi delle pagine, letti con il lettore di sempre (pypdf)."""
    from src.ingestion.pdf_ingest import carica_pdf

    with redirect_stdout(io.StringIO()):
        return [p.page_content for p in carica_pdf(percorso)]


def pagine_saltate(pagine: list[str]) -> list[tuple[int, str]]:
    """Le pagine che spezza salta, e perché, con le sue stesse regole."""
    from src.config import SOGLIA_PAGINA_MINIMA

    saltate = []
    for numero, testo in enumerate(pagine, start=1):
        if e_indice(testo):
            saltate.append((numero, "indice"))
        elif len(pulisci(testo, ricucitura="prudente")) < SOGLIA_PAGINA_MINIMA:
            saltate.append((numero, "troppo corta"))
    return saltate


def frammenti_del_file(
    riga: dict, pagine_grezze: list[str], conn, tokenizer
) -> EsitoFile:
    """Pulizia, divisione, controllo dei numeri e metadati di un file."""
    if not pagine_grezze:
        raise ErroreCaricamento(f"{riga['nome_file']}: nessuna pagina")
    scheda = bando(conn, riga["id_bandi"])
    pulizia = pulisci_avviso(pagine_grezze, scheda["titolo"])
    pagine = [
        Document(page_content=testo, metadata={"page": numero})
        for numero, testo in enumerate(pulizia.pagine, start=1)
    ]
    with redirect_stdout(io.StringIO()):
        pezzi = spezza(pagine, ricucitura="prudente")

    metadati = {
        "id_bando": scheda["id"],
        "titolo": scheda["titolo"],
        "ente": scheda["ente"],
        "tipo_documento": riga["classe"],
        "riferimento_atto": riga["atto"],
        "fonte": riga["nome_file"],
        "sha256": riga["sha256"],
        "parte": riga["parte"],
    }
    frammenti = []
    mancanti: list[tuple[int, int, str]] = []
    barra: list[tuple[int, int, str, str]] = []
    for numero, pezzo in enumerate(applica_metadati(pezzi, metadati)):
        pagina = pezzo.metadata["page"]
        non_trovati, alla_barra = controlla_numeri(
            pezzo.page_content, pagine_grezze[pagina - 1]
        )
        mancanti += [(numero, pagina, n) for n in non_trovati]
        barra += [(numero, pagina, n, nel_pdf) for n, nel_pdf in alla_barra]
        token, visti = misura_token(tokenizer, pezzo.page_content)
        pezzo.metadata.update(
            token=token,
            car_visti=visti,
            tabella_probabile=tabella_probabile(pezzo.page_content),
        )
        frammenti.append(pezzo)

    return EsitoFile(
        riga=riga,
        frammenti=frammenti,
        pagine_lette=len(pagine_grezze),
        saltate=pagine_saltate(pulizia.pagine),
        contatti=pulizia.contatti,
        righe_tolte=len(pulizia.righe_tolte),
        parole_ricucite=pulizia.parole_ricucite,
        numeri_mancanti=mancanti,
        ricuciti_barra=barra,
    )


def identificatori(frammenti: list[Document]) -> list[str]:
    return [
        f"{d.metadata['sha256'][:16]}::{d.metadata['chunk_num']}" for d in frammenti
    ]


# --- Chroma ---


def scrivi(store, esito: EsitoFile) -> tuple[int, int]:
    """Toglie i frammenti con lo stesso sha256, poi scrive i nuovi: (tolti, scritti)."""
    vecchi = store.get(where={"sha256": esito.riga["sha256"]})["ids"]
    if vecchi:
        store.delete(ids=vecchi)
    store.add_documents(documents=esito.frammenti, ids=identificatori(esito.frammenti))
    return len(vecchi), len(esito.frammenti)


def ultima_scadenza(conn, id_bando: str) -> str | None:
    """La data più lontana tra bandi.scadenza e scadenze_bando, o None."""
    date_bando = [
        r[0]
        for r in conn.execute(
            "SELECT scadenza FROM bandi WHERE id = ? AND scadenza IS NOT NULL "
            "UNION SELECT scadenza FROM scadenze_bando WHERE id_bando = ? "
            "AND scadenza IS NOT NULL",
            (id_bando, id_bando),
        ).fetchall()
        if r[0]
    ]
    return max(date_bando) if date_bando else None


def scaduti_da_togliere(store, conn, oggi: date, giorni: int) -> dict[str, list[str]]:
    """Per bando scaduto da più di `giorni`, gli id dei suoi frammenti di avviso.

    Solo i frammenti con il metadato sha256; i bandi senza scadenza restano.
    """
    limite = (oggi - timedelta(days=giorni)).isoformat()
    dati = store.get(include=["metadatas"])
    per_bando: dict[str, list[str]] = {}
    for id_frammento, meta in zip(dati["ids"], dati["metadatas"], strict=True):
        if meta.get("sha256") and meta.get("id_bando"):
            per_bando.setdefault(meta["id_bando"], []).append(id_frammento)
    return {
        id_bando: ids
        for id_bando, ids in sorted(per_bando.items())
        if (fine := ultima_scadenza(conn, id_bando)) is not None and fine < limite
    }


# --- rapporto ---


def rapporto_file(esito: EsitoFile) -> list[str]:
    token = [d.metadata["token"] for d in esito.frammenti]
    tipi: dict[str, int] = {}
    for _, s in esito.contatti:
        tipi[s.tipo] = tipi.get(s.tipo, 0) + 1
    saltate = ", ".join(f"{n} ({motivo})" for n, motivo in esito.saltate) or "nessuna"
    dettaglio = ", ".join(f"{k} {v}" for k, v in sorted(tipi.items()))
    frammenti = (
        f"   frammenti {len(esito.frammenti)}; token mediana "
        f"{statistics.median(token) if token else 0:.0f}, oltre {MASSIMO_TOKEN}: "
        f"{sum(t > MASSIMO_TOKEN for t in token)}; tabella probabile: "
        f"{sum(d.metadata['tabella_probabile'] for d in esito.frammenti)}"
    )
    pulizia = (
        f"   contatti tolti: {sum(tipi.values())}"
        + (f" ({dettaglio})" if tipi else "")
        + f"; righe ripetute tolte {esito.righe_tolte}; parole ricucite "
        f"{esito.parole_ricucite}; numeri non trovati {len(esito.numeri_mancanti)}; "
        f"ricuciti alla barra {len(esito.ricuciti_barra)}"
    )
    return [
        f"## {esito.riga['nome_file']}  ({esito.riga['id_bandi']})",
        f"   pagine lette {esito.pagine_lette}; saltate: {saltate}",
        frammenti,
        pulizia,
    ]


def rapporto_totale(esiti: list[EsitoFile]) -> list[str]:
    frammenti = [d for e in esiti for d in e.frammenti]
    token = [d.metadata["token"] for d in frammenti]
    mancanti = [(e, m) for e in esiti for m in e.numeri_mancanti]
    totale = (
        f"Totale: {len(esiti)} file, {sum(e.pagine_lette for e in esiti)} pagine, "
        f"{len(frammenti)} frammenti; token mediana "
        f"{statistics.median(token) if token else 0:.0f}, oltre {MASSIMO_TOKEN}: "
        f"{sum(t > MASSIMO_TOKEN for t in token)}; tabella probabile: "
        f"{sum(d.metadata['tabella_probabile'] for d in frammenti)}; contatti tolti: "
        f"{sum(len(e.contatti) for e in esiti)}"
    )
    barra = [(e, m) for e in esiti for m in e.ricuciti_barra]
    righe = [
        "",
        totale,
        f"Controllo dei numeri: {len(mancanti)} non trovati nel testo grezzo della pagina",
    ]
    righe += [
        f"   {e.riga['nome_file']} frammento {n} p. {p}: {numero}"
        for e, (n, p, numero) in mancanti
    ]
    righe.append(f"Ricuciti alla barra: {len(barra)}")
    righe += [
        f"   {e.riga['nome_file']} frammento {n} p. {p}: {numero} (nel PDF «{nel_pdf}»)"
        for e, (n, p, numero, nel_pdf) in barra
    ]
    return righe


# --- uso ---


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--prova", action="store_true", help="non apre Chroma e non scrive"
    )
    parser.add_argument(
        "--togli-scaduti",
        action="store_true",
        help="toglie gli avvisi dei bandi scaduti da più di --giorni giorni",
    )
    parser.add_argument("--giorni", type=int, default=365)
    return parser.parse_args(argv)


def apri_tokenizer():
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(EMBEDDING_MODEL)


def main(argv: list[str] | None = None) -> int:
    argomenti = leggi_argomenti(argv)
    senza_rete()
    from src.database.interrogazioni_bandi import data_di_oggi
    from src.database.schema import connetti

    print(f"Divisione: {CHUNK_SIZE} caratteri, {CHUNK_OVERLAP} di sovrapposizione")
    conn = connetti()
    try:
        righe = leggi_registro(PROCESSED_DIR / NOME_FILE)
        tokenizer = apri_tokenizer()
        esiti = []
        for riga in righe:
            esito = frammenti_del_file(
                riga, pagine_del_pdf(percorso_del_file(riga)), conn, tokenizer
            )
            esiti.append(esito)
            print("\n".join(rapporto_file(esito)))
        print("\n".join(rapporto_totale(esiti)))

        store = None
        if not argomenti.prova:
            from src.vectorstore import apri_store

            store = apri_store()
            for esito in esiti:
                tolti, scritti = scrivi(store, esito)
                print(f"{esito.riga['nome_file']}: tolti {tolti}, scritti {scritti}")

        if argomenti.togli_scaduti:
            if store is None:
                print("--togli-scaduti con --prova: Chroma non si apre, nulla da dire")
            else:
                da_togliere = scaduti_da_togliere(
                    store, conn, data_di_oggi(), argomenti.giorni
                )
                for id_bando, ids in da_togliere.items():
                    store.delete(ids=ids)
                    print(f"tolti {len(ids)} frammenti di {id_bando} (scaduto)")
    except ErroreCaricamento as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
