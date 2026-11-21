"""Contesto per frammento degli avvisi (passo 19d, terza mossa del perimetro).

Uso (dal terminale di chi mantiene il progetto; serve ANTHROPIC_API_KEY, o
un profilo di `ant auth login`):
    python -u -m scripts.diagnostica.genera_contesti --prova [--file NOME.pdf]
        --tetto-dollari 0.10
    python -u -m scripts.diagnostica.genera_contesti --tetto-dollari 1.00
    python -u -m scripts.diagnostica.genera_contesti --controlla [--prova]

Per ogni frammento degli avvisi (871, quelli della misura esatta, letti da
dati-grezzi/prova/19d/v0/frammenti.json; Chroma non si apre) il modello
MODELLO riceve il documento intero, messo in cache, e il frammento, e
scrive quattro righe (DOVE, ARGOMENTO, SERVE A, PAROLE) che collocano il frammento nel
documento. La riga BANDO (titolo, atto, parte del registro) la compone il
programma (riga_bando), uguale per tutti i frammenti di un file. Il testo
serve solo alla ricerca: il testo del frammento, quello che si cita e che
il verificatore controlla, resta pulito e separato.

Revisione del 21/11/2026, la sola prevista, dopo la prima generazione
(archiviata in contesti_v1.jsonl, non misurata): prompt e controlli rivisti
guardando le violazioni dei controlli, non i risultati di ricerca, che non
sono stati calcolati. Un contesto troncato (max_tokens) si rifà una volta.

Il documento è il testo pulito del file (misura_recupero_avvisi.testo_pulito:
premesse tolte, pulisci_avviso con i contatti di persone già tolti, pulizia
prudente, pagine d'indice e corte saltate), lo stesso da cui nascono i
frammenti: prima di ogni chiamata si controlla che ogni frammento compaia
tale e quale nel testo del suo documento e che nel documento non restino
email nominative o telefoni (contatti_rimasti).

Ordine: un documento alla volta; la prima chiamata di un documento scrive
la cache e solo dopo la sua risposta partono le altre, in fila.

Risultati: una riga JSON per frammento in CARTELLA (contesti.jsonl, o
contesti_prova.jsonl con --prova), scritta subito dopo ogni chiamata: id
del frammento, testo generato, righe lette, token in ingresso, letti dalla
cache, scritti in cache, in uscita, costo stimato. Un lancio interrotto
riprende saltando i frammenti già salvati con la stessa impronta delle
istruzioni.

Arresti: il tetto di spesa (--tetto-dollari, cumulativo su tutti i lanci
dello stesso file), prima di ogni chiamata, con il costo massimo della
chiamata; i token letti dalla cache a zero dopo la seconda chiamata di un
documento lungo, in questo lancio; tre errori dell'API di fila; un errore
che non si ripete (credenziali, richiesta rifiutata).

--controlla: i controlli sul testo generato (controlla_tutti), scritti in
controllo_contesti_<data>_<ora>.txt (o controllo_contesti_prova_<data>_<ora>.txt:
un rapporto non sovrascrive il precedente), con i segni automatici tolti
dopo la lettura (segni_automatici_tolti.txt, se c'è). Nessuna chiamata.

L'unica connessione di rete dello script è verso l'API di Anthropic, e solo
senza --controlla.
"""

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from src.config import DATI_GREZZI_DIR

MODELLO = "claude-haiku-5-5"
# Prima generazione: 300, con 81 contesti troncati su 871 (uscita mediana
# 248 token). Le righe nuove sono più corte; 600 lascia margine
MAX_TOKENS = 600
SFORZO = "low"
CARTELLA = DATI_GREZZI_DIR / "prova" / "19d" / "contesto"
FILE_CONTESTI = CARTELLA / "contesti.jsonl"
FILE_PROVA = CARTELLA / "contesti_prova.jsonl"
# Prova: l'avviso del fondo strade, 983 token stimati e 5 frammenti; sopra
# il minimo della cache, che quindi si verifica anche nella prova
FILE_DELLA_PROVA = "avviso_pubblico_prot_26286_del_03_11_2026-74a82f09.pdf"
NUMERO_FILE = 17
NUMERO_FRAMMENTI = 871

# Dollari per milione di token: tabella dei modelli dello SDK al 3/11/2026
# (Claude Haiku 5.5: ingresso 0,10, uscita 0,50, fino a 100.000 token di
# prompt); cache: scrittura 1,25 volte l'ingresso (durata 5 minuti),
# lettura 0,1 volte. Da ricontrollare in Console dopo la prova.
PREZZI = {
    "ingresso": 0.10,
    "scrittura_cache": 0.125,
    "lettura_cache": 0.01,
    "uscita": 0.50,
}
# Caratteri per token nella stima prudente del costo massimo di una chiamata
# (il tokenizzatore locale dà circa 4,3 caratteri per token sugli avvisi)
CARATTERI_PER_TOKEN_PRUDENTE = 2.5
# Un documento è "lungo" (la cache deve funzionare) da tanti caratteri:
# restano fuori solo le due proroghe (1.791 e 2.114 caratteri)
LUNGO = 4_000
ERRORI_DI_FILA = 3
ATTESA_DOPO_ERRORE = 10  # secondi

VOCI = (
    "chi può partecipare",
    "importi e massimali",
    "percentuali di contributo",
    "spese ammesse o escluse",
    "punteggi e criteri di valutazione",
    "procedura e scadenze di presentazione",
    "documenti da allegare",
    "cumulo con altri aiuti",
    "obblighi, vincoli e revoche",
    "rendicontazione e pagamento",
    # voci aggiunte il 21/11/2026 dalle 570 descrizioni libere di "altro"
    # della prima generazione (conteggi nel rapporto della revisione)
    "riferimenti normativi",
    "definizioni",
    "controlli e sanzioni",
    "istruttoria e graduatoria",
    "trattamento dei dati personali",
    "varianti, proroghe e modifiche",
    "premesse e finalità",
    "contatti e informazioni",
    "dotazione e risorse",
    "aiuti di Stato e regime di aiuto",
    "indice o intestazione",
)
ALTRO = "altro"
INDICE = "indice o intestazione"

ISTRUZIONI = f"""Prepari testi per la ricerca in un archivio di bandi pubblici italiani \
(avvisi, decreti, allegati), consultato da uffici comunali, enti del terzo \
settore e imprese. Ricevi il titolo del bando, l'atto, la parte, un documento \
intero e un suo frammento. Scrivi un breve contesto che colloca il frammento \
nel documento, per aiutare la ricerca a trovarlo. Il contesto non viene \
mostrato a chi legge e non sostituisce il frammento. Titolo, atto e parte li \
aggiunge il programma: non riscriverli.

Rispondi con quattro righe, in italiano, in testo semplice, senza altro prima o dopo:
DOVE: l'articolo, il paragrafo o la sezione in cui sta il frammento, con il \
numero e il titolo come li indica il documento, e nient'altro. Se il documento \
non li indica, scrivi "non indicato".
ARGOMENTO: da una a tre voci di questo elenco, scritte esattamente così e \
separate da punto e virgola: {"; ".join(VOCI)}. Scrivi "{ALTRO}:" seguito da \
poche parole solo se nessuna voce si applica.
SERVE A: una frase su che cosa permette di sapere il frammento, con le parole \
che userebbe un ufficio comunale o un'impresa che cerca un finanziamento, non \
quelle dell'atto.
PAROLE: da 5 a 10 parole o brevi espressioni, separate da punto e virgola, \
con cui un ufficio comunale, un'associazione o un'impresa cercherebbe questo \
passaggio: parole comuni, non quelle dell'atto, senza numeri e senza il nome \
del bando.

ARGOMENTO e SERVE A insieme: tra 30 e 60 parole.

Regole:
- In ARGOMENTO, in SERVE A e in PAROLE non scrivere numeri, importi, \
percentuali, date o scadenze, nemmeno in lettere, che nel frammento non ci sono.
- Nella riga DOVE scrivi solo numeri di articolo, paragrafo, sezione o allegato.
- Non nominare altri bandi, altri allegati o altre azioni, anche se il \
documento li cita, a meno che il frammento parli proprio di loro.
- Non scrivere nomi di persone, indirizzi email o numeri di telefono.
- Non riassumere il frammento e non ripeterne le frasi: di' dove sta e a che \
cosa serve.
- Non scrivere domande.
- Se il frammento è un indice, un'intestazione o un testo senza contenuto, in \
ARGOMENTO scrivi "{INDICE}"."""

RICHIESTA_FINALE = "Scrivi il contesto di questo frammento."

# BANDO: solo per riconoscerla se il modello la scrive lo stesso; si scarta
# (riga_salvata) e al suo posto va quella composta dal programma
ETICHETTE = {
    "BANDO": "bando",
    "DOVE": "dove",
    "ARGOMENTO": "argomento",
    "SERVE A": "serve_a",
    "PAROLE": "parole",
}
RIGHE_DEL_MODELLO = ("dove", "argomento", "serve_a", "parole")
# Righe in cui valgono solo i numeri del frammento (stessi controlli)
RIGHE_DAL_FRAMMENTO = ("argomento", "serve_a", "parole")
VOCI_DI_PAROLE = (5, 10)
PAROLE_CHIESTE = (30, 60)  # ARGOMENTO e SERVE A insieme
NOTA_REVISIONE = (
    "Controlli e prompt rivisti il 21/11/2026 dopo la prima generazione "
    "(contesti_v1.jsonl, non misurata), guardando le violazioni e non i "
    "risultati di ricerca, che non sono stati calcolati."
)


class ArrestoGenerazione(Exception):
    """Un motivo per fermarsi: tetto, cache, errori, ingressi che non tornano."""


@dataclass
class FrammentoDaContestualizzare:
    id: str
    chunk_num: int
    testo: str

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.testo.encode("utf-8")).hexdigest()


@dataclass
class Documento:
    fonte: str
    id_bando: str
    titolo: str
    atto: str
    parte: str
    testo: str
    frammenti: list[FrammentoDaContestualizzare] = field(default_factory=list)

    @property
    def lungo(self) -> bool:
        return len(self.testo) >= LUNGO


# --- ingressi ---


def contatti_rimasti(testo: str, titolo: str | None) -> list[str]:
    """Email da togliere e righe con un telefono rimaste nel testo, mascherate.

    Le regole sono quelle della pulizia (src/ingestion/avvisi.py): PEC e
    caselle d'ufficio restano.
    """
    from src.estrazione.contatti import EMAIL
    from src.ingestion import avvisi as av

    rimasti = [
        f"email {av.mascherato(m.group(0))}"
        for m in EMAIL.finditer(testo)
        if not av.email_da_tenere(m.group(0).rstrip("."), titolo)
    ]
    rimasti += [
        f"telefono {av.mascherato(riga.strip())}"
        for riga in testo.splitlines()
        if av.PAROLA_TELEFONO.search(riga) and av.TELEFONO.search(riga)
    ]
    return rimasti


def controlla_documenti(documenti: list[Documento]) -> None:
    """Numero di file e frammenti, frammenti nel testo, nessun contatto rimasto."""
    if len(documenti) != NUMERO_FILE:
        raise ArrestoGenerazione(f"{len(documenti)} file invece di {NUMERO_FILE}")
    n = sum(len(d.frammenti) for d in documenti)
    if n != NUMERO_FRAMMENTI:
        raise ArrestoGenerazione(f"{n} frammenti invece di {NUMERO_FRAMMENTI}")
    for d in documenti:
        fuori = [f.chunk_num for f in d.frammenti if f.testo.strip() not in d.testo]
        if fuori:
            raise ArrestoGenerazione(
                f"{d.fonte}: frammenti non nel testo del documento: {fuori}"
            )
        rimasti = contatti_rimasti(d.testo, d.titolo)
        if rimasti:
            raise ArrestoGenerazione(f"{d.fonte}: contatti rimasti: {rimasti}")


def leggi_documenti() -> list[Documento]:
    """I 17 file degli avvisi con il testo pulito e i loro frammenti, da v0."""
    from collections import defaultdict

    from scripts.diagnostica.misura_recupero_avvisi import (
        CARTELLA_19D,
        leggi_vettori,
        testo_pulito,
    )
    from scripts.ingestione import carica_avvisi as ca
    from scripts.ingestione.registra_avvisi import NOME_FILE
    from src.config import PROCESSED_DIR

    ids, testi, metadati, _ = leggi_vettori(CARTELLA_19D / "v0")
    per_fonte: dict[str, list[FrammentoDaContestualizzare]] = defaultdict(list)
    meta_di: dict[str, dict] = {}
    for id_, testo, meta in zip(ids, testi, metadati, strict=True):
        if meta.get("sha256"):
            per_fonte[meta["fonte"]].append(
                FrammentoDaContestualizzare(id_, int(meta["chunk_num"]), testo)
            )
            meta_di[meta["fonte"]] = meta
    documenti = []
    for riga in ca.leggi_registro(PROCESSED_DIR / NOME_FILE):
        fonte = riga["nome_file"]
        if fonte not in per_fonte:
            continue
        meta = meta_di[fonte]
        documenti.append(
            Documento(
                fonte=fonte,
                id_bando=meta["id_bando"],
                titolo=meta.get("titolo") or "",
                atto=meta.get("riferimento_atto") or "",
                parte=riga.get("parte") or "",
                testo=testo_pulito(
                    ca.pagine_del_pdf(ca.percorso_del_file(riga)), meta.get("titolo")
                ),
                frammenti=sorted(per_fonte[fonte], key=lambda f: f.chunk_num),
            )
        )
    mancanti = set(per_fonte) - {d.fonte for d in documenti}
    if mancanti:
        raise ArrestoGenerazione(f"file dei frammenti non nel registro: {mancanti}")
    return documenti


# --- richiesta e costi ---


def impronta_istruzioni() -> str:
    """Cambia se cambiano istruzioni, modello o parametri: le righe non si mescolano."""
    testo = json.dumps(
        [MODELLO, MAX_TOKENS, SFORZO, ISTRUZIONI, RICHIESTA_FINALE],
        ensure_ascii=False,
    )
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()


# La lista delle azioni nel titolo degli apistici ("azioni B1–B3–B4–B5"):
# nella riga composta e nel titolo dato al modello resta la sola azione
# del file, dalla parte del registro
AZIONI_NEL_TITOLO = re.compile(r"\s*:?\s*azioni\s+[A-Z]\d+(?:\W{1,3}[A-Z]\d+)+", re.I)


def titolo_del_file(documento: Documento) -> str:
    """Il titolo del bando; senza la lista delle azioni se il file ha la sua azione."""
    from scripts.diagnostica.controlla_fatti import codice_della_parte

    if codice_della_parte(documento.parte):
        return AZIONI_NEL_TITOLO.sub("", documento.titolo).strip()
    return documento.titolo


def riga_bando(documento: Documento) -> str:
    """La riga BANDO, composta dal programma: titolo, atto, parte. Uguale per il file."""
    voci = (titolo_del_file(documento), documento.atto, documento.parte)
    return "; ".join(v.strip() for v in voci if v and v.strip())


def blocco_documento(documento: Documento) -> str:
    parti = [f"<titolo_del_bando>{titolo_del_file(documento)}</titolo_del_bando>"]
    if documento.atto:
        parti.append(f"<atto>{documento.atto}</atto>")
    if documento.parte:
        parti.append(f"<parte>{documento.parte}</parte>")
    parti.append(f"<documento>\n{documento.testo}\n</documento>")
    return "\n".join(parti)


def richiesta(documento: Documento, frammento: FrammentoDaContestualizzare) -> dict:
    """Gli argomenti di messages.create: istruzioni e documento nel prefisso in cache."""
    return {
        "model": MODELLO,
        "max_tokens": MAX_TOKENS,
        "system": ISTRUZIONI,
        "thinking": {"type": "disabled"},
        "output_config": {"effort": SFORZO},
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": blocco_documento(documento),
                        "cache_control": {"type": "ephemeral"},
                    },
                    {
                        "type": "text",
                        "text": f"<frammento>\n{frammento.testo}\n</frammento>\n"
                        + RICHIESTA_FINALE,
                    },
                ],
            }
        ],
    }


def costo(uso: dict) -> float:
    """Dollari di una chiamata dai conteggi di token."""
    return (
        uso["input_tokens"] * PREZZI["ingresso"]
        + uso["cache_creation_input_tokens"] * PREZZI["scrittura_cache"]
        + uso["cache_read_input_tokens"] * PREZZI["lettura_cache"]
        + uso["output_tokens"] * PREZZI["uscita"]
    ) / 1_000_000


def costo_massimo(
    documento: Documento, frammento: FrammentoDaContestualizzare
) -> float:
    """Il caso peggiore: tutto l'ingresso scritto in cache, MAX_TOKENS in uscita."""
    caratteri = (
        len(ISTRUZIONI)
        + len(blocco_documento(documento))
        + len(frammento.testo)
        + len(RICHIESTA_FINALE)
    )
    token = caratteri / CARATTERI_PER_TOKEN_PRUDENTE
    return (
        token * PREZZI["scrittura_cache"] + MAX_TOKENS * PREZZI["uscita"]
    ) / 1_000_000


# --- lettura delle tre righe ---


def _normale(testo: str) -> str:
    return re.sub(r"\s+", " ", testo.strip().lower()).strip(" .")


def righe_del_contesto(testo: str) -> dict[str, str] | None:
    """Le righe per etichetta (dove, argomento, serve_a; bando se il modello la
    scrive lo stesso); None se fuori formato.

    Una riga senza etichetta continua la precedente. Un'etichetta ripetuta,
    o testo prima della prima etichetta, è fuori formato.
    """
    righe: dict[str, str] = {}
    ultima = None
    for riga in testo.strip().splitlines():
        if not riga.strip():
            continue
        m = re.match(
            r"^\s*\**\s*(BANDO|DOVE|ARGOMENTO|SERVE A|PAROLE)\s*\**\s*:\s*(.*)$", riga
        )
        if m:
            chiave = ETICHETTE[m[1]]
            if chiave in righe:
                return None
            righe[chiave] = m[2].strip()
            ultima = chiave
        elif ultima is None:
            return None
        else:
            righe[ultima] = f"{righe[ultima]} {riga.strip()}".strip()
    return righe or None


def voci_dell_argomento(argomento: str) -> tuple[list[str], str, list[str]]:
    """(voci dell'elenco chiuso, testo libero dopo "altro:", parti non ricondotte)."""
    voci: list[str] = []
    libero = ""
    ignote: list[str] = []
    normali = {_normale(v): v for v in VOCI}
    for parte in argomento.split(";"):
        p = _normale(parte)
        if not p:
            continue
        if p.startswith(ALTRO):
            if ALTRO not in voci:
                voci.append(ALTRO)
            libero = parte.split(":", 1)[1].strip() if ":" in parte else ""
            continue
        trovata = normali.get(p) or next(
            (v for n, v in normali.items() if n in p), None
        )
        if trovata is None:
            ignote.append(parte.strip())
        elif trovata not in voci:
            voci.append(trovata)
    return voci, libero, ignote


# Forme vicine, scritte a mano (decisione del 21/11/2026): solo forme che
# dicono la stessa cosa della voce. Niente somiglianze calcolate. Si
# provano prima di scartare una parte di ARGOMENTO (normalizza_argomento).
FORME_VICINE = {
    "chi può partecipare": (
        "beneficiari",
        "soggetti beneficiari",
        "soggetti ammessi",
        "requisiti di accesso",
        "requisiti di ammissibilità",
        "requisiti di partecipazione",
    ),
    "importi e massimali": (
        "importi",
        "massimali",
        "massimali di spesa",
        "importo del contributo",
        "contributo massimo",
    ),
    "percentuali di contributo": (
        "percentuale di contributo",
        "intensità del contributo",
        "intensità dell'aiuto",
    ),
    "spese ammesse o escluse": (
        "spese ammissibili",
        "spese ammesse",
        "spese escluse",
        "spese non ammissibili",
    ),
    "punteggi e criteri di valutazione": (
        "punteggi",
        "criteri di valutazione",
        "criteri di selezione",
        "criteri di priorità",
    ),
    "procedura e scadenze di presentazione": (
        "modalità di presentazione",
        "presentazione della domanda",
        "termini di presentazione",
        "scadenze",
    ),
    "documenti da allegare": ("documentazione da allegare", "allegati alla domanda"),
    "cumulo con altri aiuti": ("cumulo", "cumulabilità"),
    "obblighi, vincoli e revoche": (
        "obblighi",
        "vincoli",
        "revoca",
        "revoche",
        "obblighi del beneficiario",
        "impegni del beneficiario",
    ),
    "rendicontazione e pagamento": (
        "rendicontazione",
        "pagamento",
        "domanda di pagamento",
        "erogazione del contributo",
    ),
    "riferimenti normativi": ("normativa di riferimento", "quadro normativo"),
    "definizioni": ("glossario",),
    "controlli e sanzioni": ("controlli", "verifiche", "sanzioni"),
    "istruttoria e graduatoria": ("istruttoria", "graduatoria"),
    "trattamento dei dati personali": ("privacy", "protezione dei dati personali"),
    "varianti, proroghe e modifiche": (
        "varianti",
        "proroghe",
        "proroga",
        "modifiche",
        "varianti e proroghe",
    ),
    "premesse e finalità": (
        "premesse",
        "finalità",
        "obiettivi",
        "finalità e obiettivi",
    ),
    "contatti e informazioni": (
        "contatti",
        "informazioni",
        "responsabile del procedimento",
    ),
    "dotazione e risorse": (
        "dotazione finanziaria",
        "risorse disponibili",
        "risorse finanziarie",
    ),
    "aiuti di Stato e regime di aiuto": (
        "aiuti di stato",
        "regime di aiuto",
        "de minimis",
    ),
    "indice o intestazione": ("indice", "intestazione"),
}


def normalizza_argomento(argomento: str) -> str:
    """La riga ARGOMENTO ricondotta all'elenco chiuso (decisione del 21/11/2026).

    Per ogni parte separata da punto e virgola: la voce dell'elenco, o la
    voce di una sua forma vicina (FORME_VICINE); se la parte intera non è
    né l'una né l'altra, si provano i suoi pezzi separati da virgola
    ("varianti, modifiche non sostanziali"). Dal 21/11/2026, dopo la
    generazione completa, lo stesso vale per il testo dopo "altro:"
    ("altro: varianti, modifiche" diventa "varianti, proroghe e
    modifiche"); l'elenco delle forme non cambia. Le altre parti si
    scartano. Al massimo VOCI_MASSIME voci, senza doppioni. Se non resta
    nessuna voce: "altro:" con il testo del modello (i punto e virgola
    diventano virgole). Congelata fino a fine misura
    (impronta_normalizzazione).
    """
    normali = {_normale(v): v for v in VOCI}
    vicine = {_normale(f): v for v, forme in FORME_VICINE.items() for f in forme}
    voci: list[str] = []

    def prendi(testo: str) -> bool:
        voce = normali.get(_normale(testo)) or vicine.get(_normale(testo))
        if voce and voce not in voci:
            voci.append(voce)
        return voce is not None

    for parte in argomento.split(";"):
        p = _normale(parte)
        if p.startswith(ALTRO):
            parte = parte.split(":", 1)[1] if ":" in parte else ""
            p = _normale(parte)
        if not p:
            continue
        if not prendi(parte):
            for pezzo in parte.split(","):
                prendi(pezzo)
    if voci:
        return "; ".join(voci[:VOCI_MASSIME])
    libero = re.sub(rf"(?i)^\s*{ALTRO}\s*:\s*", "", argomento.strip())
    libero = libero.strip().rstrip(";").strip().replace(";", ",")
    return f"{ALTRO}: {libero}" if libero else ALTRO


def impronta_normalizzazione() -> str:
    """Cambia se cambiano voci, forme vicine o la regola: la normalizzazione è
    congelata fino a fine misura (decisione del 21/11/2026)."""
    import inspect

    testo = json.dumps(
        [VOCI, FORME_VICINE, VOCI_MASSIME, inspect.getsource(normalizza_argomento)],
        ensure_ascii=False,
    )
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()


def con_argomento_normalizzato(dato: dict) -> dict:
    """Il contesto con ARGOMENTO normalizzato; la riga del modello resta in
    `argomento_modello`. Un contesto già normalizzato si rinormalizza dalla
    riga del modello, così vale la regola di oggi anche per le righe salvate."""
    righe = dato.get("righe") or {}
    if "argomento" not in righe:
        return dato
    del_modello = dato.get("argomento_modello", righe["argomento"])
    nuovo = normalizza_argomento(del_modello)
    voci, libero, ignote = voci_dell_argomento(nuovo)
    return {
        **dato,
        "righe": {**righe, "argomento": nuovo},
        "argomento_modello": del_modello,
        "argomento_voci": voci,
        "argomento_altro": libero,
        "argomento_non_ricondotto": ignote,
    }


# --- salvataggio e ripresa ---


def leggi_salvati(percorso: Path, impronta: str | None = None) -> dict[str, dict]:
    """Le righe salvate per id. Un'ultima riga troncata si ignora.

    Con `impronta`, una riga con un'impronta diversa ferma: le versioni
    delle istruzioni non si mescolano nello stesso file. ARGOMENTO esce
    normalizzato anche per le righe scritte prima della normalizzazione
    (con_argomento_normalizzato).
    """
    if not percorso.exists():
        return {}
    righe = percorso.read_text(encoding="utf-8").splitlines()
    salvati = {}
    for numero, riga in enumerate(righe, 1):
        if not riga.strip():
            continue
        try:
            dato = json.loads(riga)
        except json.JSONDecodeError as errore:
            if numero == len(righe):
                print(f"Ultima riga di {percorso.name} troncata: si ignora.")
                continue
            raise ArrestoGenerazione(
                f"{percorso.name}, riga {numero}: non è JSON"
            ) from errore
        if impronta and dato.get("impronta") != impronta:
            raise ArrestoGenerazione(
                f"{percorso.name} ha righe scritte con altre istruzioni (impronta "
                f"{str(dato.get('impronta'))[:12]} invece di {impronta[:12]}): "
                "spostalo o rinominalo prima di generare di nuovo"
            )
        salvati[dato["id"]] = con_argomento_normalizzato(dato)
    return salvati


def aggiungi(percorso: Path, dato: dict) -> None:
    percorso.parent.mkdir(parents=True, exist_ok=True)
    with percorso.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(dato, ensure_ascii=False) + "\n")
        f.flush()


def riga_salvata(
    documento: Documento, frammento: FrammentoDaContestualizzare, risposta
) -> dict:
    """La riga del file da una risposta dell'API (o di un client finto nei test)."""
    u = risposta.usage
    uso = {
        "input_tokens": int(u.input_tokens or 0),
        "cache_read_input_tokens": int(getattr(u, "cache_read_input_tokens", 0) or 0),
        "cache_creation_input_tokens": int(
            getattr(u, "cache_creation_input_tokens", 0) or 0
        ),
        "output_tokens": int(u.output_tokens or 0),
    }
    testo = "".join(
        b.text for b in risposta.content if getattr(b, "type", "") == "text"
    ).strip()
    if risposta.stop_reason == "refusal":
        testo = ""
    lette = righe_del_contesto(testo) or {}
    # la riga BANDO del modello si scarta: vale quella composta dal programma
    scritta = lette.pop("bando", None)
    righe = {"bando": riga_bando(documento), **lette} if lette else {}
    voci, libero, ignote = voci_dell_argomento(righe.get("argomento", ""))
    return con_argomento_normalizzato(
        {
            "id": frammento.id,
            "fonte": documento.fonte,
            "chunk_num": frammento.chunk_num,
            "sha256_frammento": frammento.sha256,
            "impronta": impronta_istruzioni(),
            "modello": MODELLO,
            "testo": testo,
            "righe": righe,
            "bando_scritto_dal_modello": scritta,
            "argomento_voci": voci,
            "argomento_altro": libero,
            "argomento_non_ricondotto": ignote,
            "stop_reason": risposta.stop_reason,
            **uso,
            "costo_dollari": round(costo(uso), 8),
            "request_id": getattr(risposta, "_request_id", None),
            "ora": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
    )


# --- generazione ---


def chiama(client, argomenti: dict, attesa: float = ATTESA_DOPO_ERRORE):
    """Una chiamata; ripete fino a ERRORI_DI_FILA errori ripetibili, poi si ferma."""
    import anthropic

    errori = 0
    while True:
        try:
            return client.messages.create(**argomenti)
        except (
            anthropic.AuthenticationError,
            anthropic.PermissionDeniedError,
            anthropic.BadRequestError,
            anthropic.NotFoundError,
        ) as errore:
            raise ArrestoGenerazione(f"errore che non si ripete: {errore}") from errore
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as errore:
            errori += 1
            if errori >= ERRORI_DI_FILA:
                raise ArrestoGenerazione(
                    f"{ERRORI_DI_FILA} errori dell'API di fila; ultimo: {errore}"
                ) from errore
            print(f"  errore dell'API ({errore}); si riprova tra {attesa:.0f} s")
            time.sleep(attesa)


def descrivi(numero: int, totale: int, dato: dict) -> str:
    return (
        f"  [{numero}/{totale}] frammento {dato['chunk_num']}: ingresso "
        f"{dato['input_tokens']}, letti dalla cache {dato['cache_read_input_tokens']}, "
        f"scritti in cache {dato['cache_creation_input_tokens']}, uscita "
        f"{dato['output_tokens']}, {dato['costo_dollari']:.5f} $, "
        f"{dato['stop_reason']}"
    )


def genera(
    documenti: list[Documento],
    client,
    percorso: Path,
    tetto: float,
    mostra_testo: bool = False,
    attesa: float = ATTESA_DOPO_ERRORE,
) -> dict:
    """Genera i contesti mancanti; restituisce i conti del lancio.

    Si ferma (ArrestoGenerazione) sul tetto, sulla cache a zero e sugli
    errori; quello che è già stato salvato resta.
    """
    impronta = impronta_istruzioni()
    salvati = leggi_salvati(percorso, impronta)
    per_id = {f.id: (d, f) for d in documenti for f in d.frammenti}
    estranei = [i for i in salvati if i not in per_id]
    if estranei:
        raise ArrestoGenerazione(f"righe salvate di frammenti sconosciuti: {estranei}")
    cambiati = [
        i for i, s in salvati.items() if s["sha256_frammento"] != per_id[i][1].sha256
    ]
    if cambiati:
        raise ArrestoGenerazione(f"frammenti cambiati dopo il salvataggio: {cambiati}")
    speso = sum(s["costo_dollari"] for s in salvati.values())
    conti = {"già salvati": len(salvati), "chiamate": 0, "spesi_prima": speso}
    print(
        f"Già salvati {len(salvati)} frammenti su "
        f"{sum(len(d.frammenti) for d in documenti)}; spesi finora {speso:.4f} $ "
        f"su un tetto di {tetto:.2f} $"
    )
    for documento in documenti:
        da_fare = [f for f in documento.frammenti if f.id not in salvati]
        if not da_fare:
            continue
        print(
            f"{documento.fonte}: {len(da_fare)} frammenti da fare su "
            f"{len(documento.frammenti)} ({len(documento.testo)} caratteri"
            + (", documento lungo" if documento.lungo else "")
            + ")"
        )
        for numero, frammento in enumerate(da_fare, 1):
            massimo = costo_massimo(documento, frammento)
            if speso + massimo > tetto:
                raise ArrestoGenerazione(
                    f"tetto di spesa: spesi {speso:.4f} $, la prossima chiamata può "
                    f"costare fino a {massimo:.4f} $, tetto {tetto:.2f} $"
                )
            risposta = chiama(client, richiesta(documento, frammento), attesa)
            dato = riga_salvata(documento, frammento, risposta)
            if dato["stop_reason"] == "max_tokens":
                # troncato: si rifà una volta sola, e si tiene il secondo esito
                speso += dato["costo_dollari"]
                if speso + massimo > tetto:
                    raise ArrestoGenerazione(
                        f"tetto di spesa prima di rifare il frammento "
                        f"{frammento.chunk_num}: spesi {speso:.4f} $"
                    )
                primo = dato
                risposta = chiama(client, richiesta(documento, frammento), attesa)
                dato = riga_salvata(documento, frammento, risposta)
                dato["rifatto"] = True
                dato["costo_primo_tentativo"] = primo["costo_dollari"]
                dato["output_tokens_primo_tentativo"] = primo["output_tokens"]
                speso -= primo["costo_dollari"]
                dato["costo_dollari"] = round(
                    dato["costo_dollari"] + primo["costo_dollari"], 8
                )
                conti["chiamate"] += 1
            aggiungi(percorso, dato)
            speso += dato["costo_dollari"]
            conti["chiamate"] += 1
            print(descrivi(numero, len(da_fare), dato))
            if mostra_testo:
                print("    " + (dato["testo"] or "(vuoto)").replace("\n", "\n    "))
            if (
                numero == 1
                and documento.lungo
                and not (
                    dato["cache_creation_input_tokens"]
                    or dato["cache_read_input_tokens"]
                )
            ):
                print("  ATTENZIONE: la prima chiamata non ha scritto niente in cache")
            if numero == 2 and documento.lungo and dato["cache_read_input_tokens"] == 0:
                raise ArrestoGenerazione(
                    f"{documento.fonte}: dopo la seconda chiamata i token letti dalla "
                    "cache sono zero"
                )
    conti["spesi"] = speso
    return conti


# --- controlli sul testo generato ---

NUMERO = re.compile(r"\d+(?:[.,]\d+)*")
CODICE = re.compile(r"\b[A-Z]{1,5}\d+(?:\.\d+)*[A-Z]?\b")
RIFERIMENTO = re.compile(
    r"(?i)\b(?:art(?:icol[oi])?|par(?:agraf[oi])?|punt[oi]|cap(?:itol[oi])?|"
    r"allegat[oi]|azion[ei]|sezion[ei]|letter[ae]|comm[ai]|intervent[oi]|"
    r"misur[ae]|tab(?:ella)?)\.?\s+([A-Z]?\d+(?:\.\d+)*)"
)
PAROLE_NUMERO = re.compile(
    r"(?i)\b(mila|milion[ei]|miliard[oi]|per ?cento|percento|dieci|venti|trenta|"
    r"quaranta|cinquanta|sessanta|settanta|ottanta|novanta|cento|mille)\b"
)
MESI = re.compile(
    r"(?i)\b(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
    r"settembre|ottobre|novembre|dicembre)\b"
)
PREMESSA = re.compile(r"(?i)^\s*(ecco|certo|di seguito|il contesto)\b")
PAROLE_MASSIME = 150
PAROLE_MINIME = 15
NGRAMMA_COPIA = 6
QUOTA_COPIA = 0.5
QUOTA_VIOLAZIONI = 0.05
# Voci di ARGOMENTO ammesse per frammento. Erano 2; portate a 3 il
# 21/11/2026 dopo la prova su 5 contesti, guardando i controlli e non i
# risultati della misura (un frammento lungo può coprire tre argomenti).
# Il prompt, che chiede una o due voci, e la sua impronta non cambiano.
VOCI_MASSIME = 3
NOTA_VOCI = (
    f"Voci di ARGOMENTO: violazione oltre {VOCI_MASSIME} (regola allentata da 2 "
    "a 3 il 21/11/2026, dopo la prova su 5 contesti, guardando i controlli e "
    "non i risultati; prompt e impronta invariati)"
)

# Tre gruppi di violazioni (decisione del 21/11/2026, prima dei controlli
# sugli 871): contenuto (tipi "numero" e "gemello": numeri, date, segni del
# gemello verificati a mano, codici di altre azioni, numeri d'atto), segno
# automatico del gemello, forma. Un contesto con violazioni di contenuto o
# da segno automatico non tolto si scarta, e conta per la condizione di
# arresto; uno con sole violazioni di forma resta.
GEMELLO_AUTOMATICO = "gemello automatico"
CONTENUTO = "contenuto"
AUTOMATICO = "segno automatico"
FORMA = "forma"
GRUPPO_DEL_TIPO = {
    "numero": CONTENUTO,
    "gemello": CONTENUTO,
    GEMELLO_AUTOMATICO: AUTOMATICO,
    "forma": FORMA,
}
# Segni automatici tolti dopo la lettura, uno per riga: "<fonte> | <segno>".
# Un segno si toglie solo se tutti i suoi casi sono usi generici (regola del
# 21/11/2026); i casi di un segno non tolto contano come violazioni vere
NOME_SEGNI_TOLTI = "segni_automatici_tolti.txt"  # in CARTELLA


def gruppi_di(trovate: list[tuple[str, str]]) -> set[str]:
    """I gruppi (contenuto, segno automatico, forma) delle violazioni di un frammento."""
    return {GRUPPO_DEL_TIPO[t] for t, _ in trovate}


def da_scartare(trovate: list[tuple[str, str]]) -> bool:
    """Il contesto si scarta: violazioni di contenuto o da segno automatico non tolto."""
    return bool(gruppi_di(trovate) - {FORMA})


def leggi_segni_tolti(percorso: Path | None = None) -> set[tuple[str, str]]:
    """Le coppie (fonte, segno) del file dei segni automatici tolti; vuoto se manca.

    Righe vuote e righe che cominciano con "#" si ignorano.
    """
    percorso = percorso or CARTELLA / NOME_SEGNI_TOLTI
    if not percorso.exists():
        return set()
    tolti = set()
    for numero, riga in enumerate(percorso.read_text(encoding="utf-8").splitlines(), 1):
        if not riga.strip() or riga.lstrip().startswith("#"):
            continue
        fonte, sep, segno = riga.partition("|")
        if not sep or not fonte.strip() or not segno.strip():
            raise ArrestoGenerazione(
                f"{percorso.name}, riga {numero}: serve '<fonte> | <segno>'"
            )
        tolti.add((fonte.strip(), _normale(segno)))
    return tolti


def togli_segni(
    segni: "SegniDelGemello", fonte: str, tolti: set[tuple[str, str]]
) -> set[str]:
    """Toglie dai segni di `fonte` quelli automatici del file dei tolti; li restituisce.

    Ferma se il file nomina, per questa fonte, un segno che non è automatico.
    """
    suoi = {s for f, s in tolti if f == fonte}
    non_automatici = suoi - segni.automatici
    if non_automatici:
        raise ArrestoGenerazione(
            f"{fonte}: segni tolti che non sono automatici: {sorted(non_automatici)}"
        )
    segni.automatici -= suoi
    segni.frasi -= suoi
    return suoi


def _norma_numero(n: str) -> str:
    return n.rstrip(".,").replace(".", "").lstrip("0") or "0"


def numeri_di(testo: str) -> set[str]:
    """I numeri del testo, normalizzati; anche con gli spazi tra cifre tolti."""
    compatto = re.sub(r"(?<=\d)[ \t]+(?=[\d.,])|(?<=[\d.,])[ \t]+(?=\d)", "", testo)
    return {_norma_numero(n) for t in (testo, compatto) for n in NUMERO.findall(t)}


def _parole(testo: str) -> list[str]:
    return re.findall(r"\w+", testo.lower())


def quota_copiata(contesto: str, frammento: str, n: int = NGRAMMA_COPIA) -> float:
    """Quota delle parole del contesto dentro sequenze di n parole uguali nel frammento."""
    c, f = _parole(contesto), _parole(frammento)
    if len(c) < n:
        return 0.0
    del_frammento = {tuple(f[i : i + n]) for i in range(len(f) - n + 1)}
    coperte = set()
    for i in range(len(c) - n + 1):
        if tuple(c[i : i + n]) in del_frammento:
            coperte.update(range(i, i + n))
    return len(coperte) / len(c)


@dataclass
class SegniDelGemello:
    """Per un file: segni dei gemelli (codici, nomi d'azione o di bando, numeri d'atto).

    `scartati`: i segni candidati tolti perché compaiono nel testo del
    proprio documento (revisione del 21/11/2026).
    """

    codici: set[str] = field(default_factory=set)
    frasi: set[str] = field(default_factory=set)
    numeri: set[str] = field(default_factory=set)
    scartati: set[str] = field(default_factory=set)
    # quelli cercati in automatico (segni_automatici), già anche in `frasi`
    automatici: set[str] = field(default_factory=set)

    def vuoti(self) -> bool:
        return not (self.codici or self.frasi or self.numeri)


def gemelli_dei_file(documenti: list[Documento]) -> dict[str, list[Documento]]:
    """Per file: i file gemelli (bando gemello, o un altro allegato con un'altra azione)."""
    from scripts.diagnostica.controlla_fatti import codice_della_parte
    from scripts.diagnostica.misura_recupero_avvisi import GEMELLI_DEI_BANDI

    gemelli = {}
    for d in documenti:
        codice = codice_della_parte(d.parte)
        gemelli[d.fonte] = [
            g
            for g in documenti
            if g.id_bando == GEMELLI_DEI_BANDI.get(d.id_bando)
            or (
                g.id_bando == d.id_bando
                and g.fonte != d.fonte
                and codice
                and codice_della_parte(g.parte)
                and codice_della_parte(g.parte) != codice
            )
        ]
    return gemelli


def _allegato(fonte: str) -> str | None:
    m = re.search(r"allegato-([a-z]\d+)", fonte)
    return m[1].upper() if m else None


# Candidati scelti a mano dai titoli (docs/coda.md, "Passo 19d", punto 5);
# dal 21/11/2026 valgono solo se il programma verifica che non compaiono
# nel testo del proprio documento (segni_del_gemello)
NOMI_DEL_BANDO = {
    "cultura-missione-comune-2026": ("cultura",),
    "sport-missione-comune-2026": ("sport",),
    "bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-7057d9": (
        "commissioni di garanzia",
        "50 mila",
    ),
    "bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-8cd3ac": (
        "blending",
        "costi di garanzia",
        "finanziamenti bancari",
    ),
}


def _compare(segno: str, testo: str, maiuscole: bool = False) -> bool:
    """Il segno compare nel testo come parola intera (i codici: maiuscole uguali)."""
    if maiuscole:
        return re.search(rf"\b{re.escape(segno)}\b", testo) is not None
    cerca = rf"\b{re.escape(_normale(segno))}\b"
    return re.search(cerca, _normale(testo)) is not None


def altri_del_bando(documento: Documento, documenti: list[Documento]) -> str:
    """Il testo degli altri file dello stesso bando che non sono un allegato
    d'azione (per l'avviso Cultura: la sua proroga, e viceversa)."""
    from scripts.diagnostica.controlla_fatti import codice_della_parte

    if codice_della_parte(documento.parte):
        return ""
    return " ".join(
        d.testo
        for d in documenti
        if d.id_bando == documento.id_bando
        and d.fonte != documento.fonte
        and not codice_della_parte(d.parte)
    )


def segni_del_gemello(
    documento: Documento, gemelli: list[Documento], del_bando: str = ""
) -> SegniDelGemello:
    """Segni che un contesto parla di un gemello, verificati sul proprio documento.

    Candidati: codici d'azione e d'allegato e nomi d'azione dei gemelli
    (parte del registro e nome del file); per i bandi gemelli, NOMI_DEL_BANDO,
    le parole del titolo del gemello che il titolo proprio non ha, e i
    numeri del suo atto. Un candidato vale solo se non compare mai nel
    testo del proprio documento (né nel suo atto); gli altri vanno in
    `scartati`. Per i segni di un bando gemello il proprio documento è il
    bando intero (`del_bando`: gli altri suoi file, altri_del_bando), per
    quelli di un altro allegato è il file. A questi si aggiungono i segni
    cercati in automatico (segni_automatici). Il controllo li cerca solo
    nelle righe scritte dal modello.
    """
    from scripts.diagnostica.controlla_fatti import codice_della_parte
    from scripts.diagnostica.misura_recupero_avvisi import parole_significative

    segni = SegniDelGemello()
    a_mano: set[str] = set()
    # il testo del documento, non il titolo: quello degli apistici elenca
    # tutte le azioni
    proprio = f"{documento.atto} {documento.testo}"
    proprio_bando = f"{proprio} {del_bando}"
    numeri_propri = numeri_di(proprio_bando)
    parole_titolo = set(parole_significative(documento.titolo))
    for g in gemelli:
        codici, frasi = set(), set()
        codice = codice_della_parte(g.parte)
        if codice and codice != codice_della_parte(documento.parte):
            codici.add(codice)
            if ":" in g.parte:
                frasi.add(_normale(g.parte.split(":", 1)[1]))
        allegato = _allegato(g.fonte)
        if allegato and allegato != _allegato(documento.fonte):
            codici.add(allegato)
        if g.id_bando != documento.id_bando:
            frasi |= {_normale(x) for x in NOMI_DEL_BANDO.get(g.id_bando, ())}
            frasi |= {
                p
                for p in parole_significative(g.titolo)
                if len(p) >= 4 and p not in parole_titolo
            }
        for c in codici:
            (segni.scartati if _compare(c, proprio, True) else segni.codici).add(c)
        for f in frasi:
            (segni.scartati if _compare(f, proprio_bando) else a_mano).add(f)
        for x in NUMERO.findall(g.atto):
            n = _norma_numero(x)
            if len(n) >= 3:
                (segni.scartati if n in numeri_propri else segni.numeri).add(n)
        automatici = segni_automatici(
            documento, g, del_bando if g.id_bando != documento.id_bando else ""
        )
        segni.automatici |= set(automatici)
    # un segno scelto a mano e verificato vale come tale anche se è pure
    # automatico: le violazioni si contano nel gruppo del contenuto
    segni.automatici -= a_mano
    segni.frasi = a_mano | segni.automatici
    segni.scartati -= segni.codici | segni.frasi | segni.numeri
    return segni


# Segni cercati in automatico (decisione del 21/11/2026): fino a
# SEGNI_AUTOMATICI per coppia, parole o coppie di parole che compaiono
# almeno FREQUENZA_SEGNO volte nel testo del gemello e mai nel proprio
# documento (testo, titolo, atto, parte)
SEGNI_AUTOMATICI = 3
FREQUENZA_SEGNO = 3
LETTERE_SEGNO = 5
RADICE_SEGNO = 6


def _parole_del_testo(testo: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", testo.lower())


def segni_automatici(
    documento: Documento, gemello: Documento, del_bando: str = ""
) -> list[str]:
    """Fino a SEGNI_AUTOMATICI segni del gemello, dal più frequente nel suo testo.

    Parole di almeno LETTERE_SEGNO lettere, non funzionali, la cui radice
    (prime RADICE_SEGNO lettere) non compare nel proprio documento; oppure
    coppie di parole consecutive del gemello le cui radici nel proprio
    documento non stanno mai insieme (pur comparendo tutte e due). Il segno
    scelto si cerca poi nel contesto com'è, parola intera.
    Una coppia che contiene una parola già scelta non si aggiunge. A parità
    di frequenza, in ordine alfabetico.
    """
    from collections import Counter

    from scripts.diagnostica.misura_recupero_avvisi import PAROLE_FUNZIONALI

    proprio = (
        f"{documento.titolo} {documento.atto} {documento.parte} {documento.testo} "
        f"{del_bando}"
    )
    # l'assenza si verifica sulla radice, le prime RADICE_SEGNO lettere
    # (21/11/2026: "attrezzatura" del gemello contro "attrezzature" proprie)
    radici_proprie = [p[:RADICE_SEGNO] for p in _parole_del_testo(proprio)]
    insieme_radici = set(radici_proprie)
    sequenza_radici = " ".join(radici_proprie)
    del_gemello = _parole_del_testo(gemello.testo)

    def buona(p: str) -> bool:
        return len(p) >= LETTERE_SEGNO and p not in PAROLE_FUNZIONALI

    conti: Counter = Counter()
    for p in del_gemello:
        if buona(p) and p[:RADICE_SEGNO] not in insieme_radici:
            conti[p] += 1
    for a, b in zip(del_gemello, del_gemello[1:], strict=False):
        ra, rb = a[:RADICE_SEGNO], b[:RADICE_SEGNO]
        if buona(a) and buona(b) and ra in insieme_radici and rb in insieme_radici:
            if not re.search(rf"\b{ra} {rb}\b", sequenza_radici):
                conti[f"{a} {b}"] += 1
    scelti: list[str] = []
    for segno, n in sorted(conti.items(), key=lambda x: (-x[1], x[0])):
        if n < FREQUENZA_SEGNO or len(scelti) == SEGNI_AUTOMATICI:
            break
        if any(s in segno.split() for s in scelti):
            continue
        scelti.append(segno)
    return scelti


def testo_di_ricerca(
    righe: dict[str, str],
    quali=("bando", "dove", "argomento", "serve_a", "parole"),
) -> str:
    """Il testo del contesto che entra nella ricerca: le righe scelte, senza etichette."""
    return " ".join(righe[q] for q in quali if righe.get(q)).strip()


# Riferimenti di struttura senza parola davanti: 4.2.2, 16.4, 1.3.2.1 (gruppi
# di 1-2 cifre dopo il punto; "50.000" e "1.242.000" non lo sono)
# Dal 21/11/2026 vale anche seguito da punteggiatura ("1.1," "6.2,"), purché
# la punteggiatura non sia seguita da una cifra (18.000,00 resta fuori)
STRUTTURA = re.compile(r"(?<![\d.,])\d{1,3}(?:\.\d{1,2})+(?!\d|[.,]\d)")
DATA_DOVE = re.compile(r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b")
NUMERO_SOLO = re.compile(r"^\d{1,3}$")


def apre_una_riga(numero: str, testo: str) -> bool:
    """Nel testo il numero apre una riga come paragrafo o punto ("1.1 …", "2. …")."""
    cerca = rf"(?m)^[ \t]*{re.escape(numero)}(?:[.)]|\s)"
    return re.search(cerca, testo) is not None


def _togli_struttura(testo: str, documento: Documento, violazioni: list) -> str:
    """Toglie dal testo date, riferimenti di struttura e codici; segnala quelli
    che nel documento non ci sono. Restituisce il testo che resta.

    Un riferimento senza parola davanti (4.2.2, 16.4) vale solo se nel
    documento apre una riga come paragrafo o punto (apre_una_riga).
    """
    for m in DATA_DOVE.finditer(testo):
        violazioni.append(
            ("numero", f"numero non di struttura nella riga DOVE (data): {m[0]}")
        )
    testo = DATA_DOVE.sub(" ", testo)
    del_documento = numeri_di(documento.testo)
    codici_documento = set(
        CODICE.findall(
            f"{documento.titolo} {documento.atto} {documento.parte} {documento.testo}"
        )
    )
    for m in RIFERIMENTO.finditer(testo):
        numero = _norma_numero(re.sub(r"^[A-Z]", "", m[1]))
        if m[1] not in codici_documento and numero not in del_documento:
            violazioni.append(("numero", f"riferimento non nel documento: {m[0]!r}"))
    resto = RIFERIMENTO.sub(" ", testo)
    for m in STRUTTURA.finditer(resto):
        if not apre_una_riga(m[0], documento.testo):
            violazioni.append(("numero", f"riferimento non nel documento: {m[0]!r}"))
    resto = STRUTTURA.sub(" ", resto)
    for codice in CODICE.findall(resto):
        if codice not in codici_documento:
            violazioni.append(("numero", f"codice non nel documento: {codice}"))
    return CODICE.sub(" ", resto)


def controlla_contesto(
    dato: dict, frammento: str, documento: Documento, segni: SegniDelGemello
) -> list[tuple[str, str]]:
    """Le violazioni di un contesto: (tipo, dettaglio); tipo numero, gemello,
    gemello automatico (un segno di segni_automatici) o forma.

    Si controllano solo le righe scritte dal modello (DOVE, ARGOMENTO,
    SERVE A, PAROLE): la riga BANDO la compone il programma. Numeri: nella
    riga DOVE solo riferimenti di struttura che stanno nel documento; in
    ARGOMENTO, SERVE A e PAROLE solo numeri, date e parole di numero che
    stanno nel frammento. Un frammento con la sola voce "indice o
    intestazione" vale anche senza SERVE A.
    """
    violazioni: list[tuple[str, str]] = []
    testo = dato.get("testo") or ""
    righe = dato.get("righe") or {}
    del_modello = " ".join(righe[k] for k in RIGHE_DEL_MODELLO if righe.get(k))
    argomento_serve = " ".join(righe[k] for k in RIGHE_DAL_FRAMMENTO if righe.get(k))
    if dato.get("stop_reason") != "end_turn":
        violazioni.append(("forma", f"stop_reason {dato.get('stop_reason')}"))
    if not testo.strip():
        violazioni.append(("forma", "vuoto"))
        return violazioni
    if not righe:
        violazioni.append(("forma", "fuori formato"))
    elif not ("argomento" in righe and "serve_a" in righe) and (
        dato.get("argomento_voci") != [INDICE]
    ):
        # un frammento di solo indice o intestazione vale anche senza SERVE A
        violazioni.append(("forma", "manca ARGOMENTO o SERVE A"))
    if "argomento" in righe:
        voci = dato.get("argomento_voci") or []
        if dato.get("argomento_non_ricondotto") or not voci:
            violazioni.append(
                ("forma", f"argomento non ricondotto: {righe['argomento']!r}")
            )
        if len(voci) > VOCI_MASSIME:
            violazioni.append(("forma", f"più di {VOCI_MASSIME} voci: {voci}"))
    parole = len(_parole(del_modello))
    if parole > PAROLE_MASSIME:
        violazioni.append(("forma", f"troppo lungo: {parole} parole"))
    if "?" in testo:
        violazioni.append(("forma", "domanda"))
    if PREMESSA.match(testo):
        violazioni.append(("forma", "premessa"))
    quota = quota_copiata(del_modello, frammento)
    if quota > QUOTA_COPIA:
        violazioni.append(("forma", f"copiato dal frammento: {quota:.0%}"))
    if contatti_rimasti(testo, documento.titolo) or "@" in testo:
        violazioni.append(("forma", "contatti"))

    # numeri: riga DOVE
    dove = righe.get("dove") or ""
    resto = _togli_struttura(dove, documento, violazioni)
    for n in NUMERO.findall(resto):
        # un numero solo vale come riferimento se nel documento apre una riga
        if NUMERO_SOLO.match(n) and apre_una_riga(n, documento.testo):
            continue
        violazioni.append(("numero", f"numero non di struttura nella riga DOVE: {n}"))
    for regola in (PAROLE_NUMERO, MESI):
        for m in regola.finditer(dove):
            violazioni.append(("numero", f"parola di numero nella riga DOVE: {m[0]}"))
    # numeri: ARGOMENTO e SERVE A, solo quelli del frammento
    del_frammento = numeri_di(frammento)
    for n in NUMERO.findall(argomento_serve):
        if _norma_numero(n) not in del_frammento:
            violazioni.append(("numero", f"numero non nel frammento: {n}"))
    frammento_minuscolo = frammento.lower()
    for regola in (PAROLE_NUMERO, MESI):
        for m in regola.finditer(argomento_serve):
            if m[0].lower() not in frammento_minuscolo:
                violazioni.append(("numero", f"parola non nel frammento: {m[0]}"))

    # gemello, nelle sole righe del modello; ammesso se il segno sta nel frammento
    for codice in sorted(segni.codici):
        if re.search(rf"\b{codice}\b", del_modello, re.IGNORECASE) and not re.search(
            rf"\b{codice}\b", frammento, re.IGNORECASE
        ):
            violazioni.append(("gemello", f"codice {codice}"))
    for frase in sorted(segni.frasi):
        cerca = rf"\b{re.escape(frase)}\b"
        if re.search(cerca, _normale(del_modello)) and not re.search(
            cerca, _normale(frammento)
        ):
            tipo = GEMELLO_AUTOMATICO if frase in segni.automatici else "gemello"
            violazioni.append((tipo, f"nome {frase!r}"))
    numeri_modello = {_norma_numero(n) for n in NUMERO.findall(del_modello)}
    for numero in sorted(segni.numeri & numeri_modello):
        if numero not in del_frammento:
            violazioni.append(("gemello", f"atto {numero}"))
    return violazioni


def linee_dei_segni(
    documenti: list[Documento],
    tutti: list[Documento] | None = None,
    tolti: set[tuple[str, str]] | None = None,
) -> list[str]:
    """Per file: i segni del gemello rimasti dopo la verifica e quelli scartati.

    `tutti`: i file fra cui cercare gemelli e altri file del bando (con
    --prova, tutti i 17, anche se si controlla un file solo). `tolti`: i
    segni automatici tolti dopo la lettura (leggi_segni_tolti).
    """
    tutti = tutti or documenti
    gemelli = gemelli_dei_file(tutti)
    linee = []
    for d in documenti:
        if not gemelli[d.fonte]:
            continue
        s = segni_del_gemello(d, gemelli[d.fonte], altri_del_bando(d, tutti))
        via = togli_segni(s, d.fonte, tolti or set())
        a_mano = sorted(s.codici) + sorted(s.frasi - s.automatici) + sorted(s.numeri)
        linee.append(
            f"  {d.fonte}: rimasti "
            + (
                "NESSUNO"
                if s.vuoti()
                else f"verificati {', '.join(a_mano) or '-'}; automatici "
                f"{', '.join(sorted(s.automatici)) or '-'}"
            )
            + "; scartati (nel testo del documento) "
            + (", ".join(sorted(s.scartati)) or "-")
            + (
                f"; automatici tolti dopo la lettura {', '.join(sorted(via))}"
                if via
                else ""
            )
        )
    return linee


def controlla_tutti(
    documenti: list[Documento],
    salvati: dict[str, dict],
    tutti: list[Documento] | None = None,
    tolti: set[tuple[str, str]] | None = None,
) -> tuple[dict[str, list[tuple[str, str]]], list[str]]:
    """(violazioni per id del frammento, linee del rapporto).

    Si controllano i frammenti di `documenti`; gemelli e altri file del
    bando si cercano fra `tutti` (predefinito: `documenti`). Con --prova
    `documenti` è il file provato e `tutti` sono i 17: prima del
    21/11/2026 i gemelli si cercavano fra i soli file provati, e il
    controllo del gemello nella prova non trovava niente. `tolti`: i segni
    automatici tolti dopo la lettura (leggi_segni_tolti), che non si
    cercano. Il rapporto separa i tre gruppi (gruppi_di); la condizione di
    arresto conta i frammenti da scartare (da_scartare).
    """
    from collections import Counter

    tutti = tutti or documenti
    tolti = tolti or set()
    fonti = {d.fonte for d in tutti}
    ignote = sorted(f for f, _ in tolti if f not in fonti)
    if ignote:
        raise ArrestoGenerazione(f"segni tolti di file sconosciuti: {ignote}")
    gemelli = gemelli_dei_file(tutti)
    violazioni: dict[str, list[tuple[str, str]]] = {}
    per_file = []
    tipi: Counter = Counter()
    voci: Counter = Counter()
    fuori_misura: Counter = Counter()
    scritta_bando = rifatti = indice = 0
    for d in documenti:
        segni = segni_del_gemello(d, gemelli[d.fonte], altri_del_bando(d, tutti))
        togli_segni(segni, d.fonte, tolti)
        fatti = [f for f in d.frammenti if f.id in salvati]
        con = 0
        gruppi_file: Counter = Counter()
        for f in fatti:
            dato = salvati[f.id]
            trovate = controlla_contesto(dato, f.testo, d, segni)
            righe = dato.get("righe") or {}
            parole = len(_parole(testo_di_ricerca(righe, ("argomento", "serve_a"))))
            voci_parole = [
                v for v in (righe.get("parole") or "").split(";") if v.strip()
            ]
            if righe and not (
                VOCI_DI_PAROLE[0] <= len(voci_parole) <= VOCI_DI_PAROLE[1]
            ):
                fuori_misura["parole"] += 1
            if parole < PAROLE_CHIESTE[0]:
                fuori_misura["sotto"] += 1
            elif parole > PAROLE_CHIESTE[1]:
                fuori_misura["sopra"] += 1
            scritta_bando += bool(dato.get("bando_scritto_dal_modello"))
            rifatti += bool(dato.get("rifatto"))
            indice += INDICE in (dato.get("argomento_voci") or [])
            voci.update(dato.get("argomento_voci") or ["(nessuna)"])
            if trovate:
                violazioni[f.id] = trovate
                con += 1
                tipi.update({t for t, _ in trovate})
                gruppi_file.update(gruppi_di(trovate))
                gruppi_file["scartare"] += da_scartare(trovate)
        per_file.append((d.fonte, len(fatti), len(d.frammenti), con, gruppi_file))
    totale = sum(n for _, n, _, _, _ in per_file)
    gruppi = [set(gruppi_di(v)) for v in violazioni.values()]
    contenuto = sum(CONTENUTO in g for g in gruppi)
    automatico = sum(AUTOMATICO in g for g in gruppi)
    solo_automatico = sum(g == {AUTOMATICO} or g == {AUTOMATICO, FORMA} for g in gruppi)
    forma = sum(FORMA in g for g in gruppi)
    solo_forma = sum(g == {FORMA} for g in gruppi)
    vere = sum(da_scartare(v) for v in violazioni.values())

    def quota(n: int) -> str:
        return f"{n} ({n / totale:.1%})" if totale else str(n)

    linee = [
        (
            f"Controlli sui contesti generati ({totale} su "
            f"{sum(len(d.frammenti) for d in documenti)} frammenti)"
        ),
        NOTA_REVISIONE,
        f"Normalizzazione di ARGOMENTO: impronta {impronta_normalizzazione()[:12]}",
        (
            f"Frammenti con almeno una violazione: {quota(len(violazioni))}"
            if totale
            else "Nessun contesto salvato"
        ),
        (
            "  contenuto (numeri, date, segni del gemello verificati a mano, "
            f"codici di altre azioni, numeri d'atto): {quota(contenuto)}"
        ),
        (
            f"  segno automatico del gemello: {quota(automatico)}, di cui senza "
            f"violazioni di contenuto {solo_automatico}"
        ),
        f"  forma: {quota(forma)}, di cui di sola forma {solo_forma}",
        (
            f"Violazioni vere (contenuto, o segno automatico non tolto): "
            f"{quota(vere)}; soglia di arresto {QUOTA_VIOLAZIONI:.0%}; questi "
            "contesti si scartano, quelli di sola forma restano"
        ),
        (
            "Segni automatici tolti dopo la lettura: "
            + (", ".join(f"{f} | {s}" for f, s in sorted(tolti)) or "nessuno")
        ),
        "Per tipo (frammenti): "
        + ", ".join(f"{t} {n}" for t, n in sorted(tipi.items())),
        (
            f"ARGOMENTO e SERVE A fuori da {PAROLE_CHIESTE[0]}-{PAROLE_CHIESTE[1]} "
            f"parole (non è una violazione): sotto {fuori_misura['sotto']}, sopra "
            f"{fuori_misura['sopra']}"
        ),
        (
            f"PAROLE fuori da {VOCI_DI_PAROLE[0]}-{VOCI_DI_PAROLE[1]} voci (non è "
            f"una violazione): {fuori_misura['parole']}"
        ),
        f"Riga BANDO scritta lo stesso dal modello (scartata): {scritta_bando}",
        f"Contesti rifatti dopo un troncamento: {rifatti}",
        f"ARGOMENTO '{INDICE}': {indice}",
        NOTA_VOCI,
        "Voci di ARGOMENTO: " + ", ".join(f"{v} {n}" for v, n in voci.most_common()),
        "",
        "Segni del gemello dopo la verifica sul proprio documento:",
        *linee_dei_segni(documenti, tutti, tolti),
        "",
        (
            "Per file: frammenti con contesto / frammenti, con violazioni; per "
            "gruppo: contenuto, segno automatico, forma; da scartare"
        ),
    ]
    linee += [
        f"  {f}: {n} / {tot}, {c}; {g[CONTENUTO]}, {g[AUTOMATICO]}, {g[FORMA]}; "
        f"{g['scartare']}"
        for f, n, tot, c, g in per_file
    ]
    linee += ["", "Violazioni, per frammento:"]
    for d in documenti:
        for f in d.frammenti:
            if f.id in violazioni:
                linee.append(
                    f"  {d.fonte} #{f.chunk_num}: "
                    + "; ".join(f"{t}: {x}" for t, x in violazioni[f.id])
                )
    return violazioni, linee


def documenti_della_prova(documenti: list[Documento], nome: str) -> list[Documento]:
    scelti = [d for d in documenti if d.fonte == nome]
    if not scelti:
        raise ArrestoGenerazione(
            f"{nome} non è tra i {len(documenti)} file degli avvisi"
        )
    return scelti


def percorso_del_rapporto(prova: bool, ora: str | None = None) -> Path:
    """Il file del rapporto dei controlli, con data e ora: non si sovrascrive
    un rapporto precedente (decisione del 21/11/2026). Se il nome c'è già,
    un numero in coda."""
    base = "controllo_contesti_prova" if prova else "controllo_contesti"
    ora = ora or time.strftime("%Y-%m-%d_%H%M%S")
    percorso = CARTELLA / f"{base}_{ora}.txt"
    numero = 2
    while percorso.exists():
        percorso = CARTELLA / f"{base}_{ora}_{numero}.txt"
        numero += 1
    return percorso


def esegui_controlli(prova: bool) -> int:
    documenti = leggi_documenti()
    percorso = FILE_PROVA if prova else FILE_CONTESTI
    salvati = leggi_salvati(percorso, impronta_istruzioni())
    if not salvati:
        print(f"Nessun contesto in {percorso}")
        return 1
    tutti = documenti
    if prova:
        documenti = [d for d in documenti if any(f.id in salvati for f in d.frammenti)]
    _, linee = controlla_tutti(documenti, salvati, tutti, leggi_segni_tolti())
    rapporto = percorso_del_rapporto(prova)
    testo = "\n".join(linee)
    rapporto.write_text(testo + "\n", encoding="utf-8")
    print(testo)
    print(f"\nScritto {rapporto}")
    return 0


# --- uso ---


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--prova",
        action="store_true",
        help=f"un file solo (--file; predefinito {FILE_DELLA_PROVA}), in "
        f"{FILE_PROVA.name}",
    )
    parser.add_argument(
        "--file", help="con --prova: il nome del PDF del registro da provare"
    )
    parser.add_argument(
        "--tetto-dollari",
        type=float,
        help="spesa massima, cumulativa su tutti i lanci dello stesso file",
    )
    parser.add_argument(
        "--controlla", action="store_true", help="solo i controlli, nessuna chiamata"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, client=None) -> int:
    argomenti = leggi_argomenti(argv)
    try:
        if argomenti.file and not argomenti.prova:
            print("--file vale solo con --prova.", file=sys.stderr)
            return 2
        if argomenti.controlla:
            return esegui_controlli(argomenti.prova)
        if argomenti.tetto_dollari is None or argomenti.tetto_dollari <= 0:
            print("Serve --tetto-dollari, maggiore di zero.", file=sys.stderr)
            return 2
        documenti = leggi_documenti()
        controlla_documenti(documenti)
        tutti = documenti
        percorso = FILE_CONTESTI
        if argomenti.prova:
            documenti = documenti_della_prova(
                documenti, argomenti.file or FILE_DELLA_PROVA
            )
            percorso = FILE_PROVA
        print(
            f"Modello {MODELLO}, impronta delle istruzioni "
            f"{impronta_istruzioni()[:12]}, file {percorso}"
        )
        if client is None:
            import anthropic

            client = anthropic.Anthropic(max_retries=4)
        inizio = time.perf_counter()
        conti = genera(
            documenti, client, percorso, argomenti.tetto_dollari, argomenti.prova
        )
        salvati = leggi_salvati(percorso, impronta_istruzioni())
        print(
            f"\nFatto: {conti['chiamate']} chiamate in questo lancio, "
            f"{len(salvati)} frammenti salvati, spesi in tutto {conti['spesi']:.4f} $ "
            f"(stima con i prezzi di PREZZI), {time.perf_counter() - inizio:.0f} s"
        )
        if argomenti.prova:
            _, linee = controlla_tutti(documenti, salvati, tutti)
            print("\n" + "\n".join(linee))
        return 0
    except ArrestoGenerazione as motivo:
        print(f"Arresto: {motivo}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
