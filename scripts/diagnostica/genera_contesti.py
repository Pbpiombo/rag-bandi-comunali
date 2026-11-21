"""Contesto per frammento degli avvisi (passo 19d, terza mossa del perimetro).

Uso (dal terminale di chi mantiene il progetto; serve ANTHROPIC_API_KEY, o
un profilo di `ant auth login`):
    python -u -m scripts.diagnostica.genera_contesti --prova --tetto-dollari 0.05
    python -u -m scripts.diagnostica.genera_contesti --tetto-dollari 1.00
    python -u -m scripts.diagnostica.genera_contesti --controlla [--prova]

Per ogni frammento degli avvisi (871, quelli della misura esatta, letti da
dati-grezzi/prova/19d/v0/frammenti.json; Chroma non si apre) il modello
MODELLO riceve il documento intero, messo in cache, e il frammento, e
scrive tre righe (BANDO, ARGOMENTO, SERVE A) che collocano il frammento nel
documento. Il testo serve solo alla ricerca: il testo del frammento, quello
che si cita e che il verificatore controlla, resta pulito e separato.

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
controllo_contesti.txt (o controllo_contesti_prova.txt). Nessuna chiamata.

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
MAX_TOKENS = 300
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
)
ALTRO = "altro"

ISTRUZIONI = f"""Prepari testi per la ricerca in un archivio di bandi pubblici italiani \
(avvisi, decreti, allegati), consultato da uffici comunali, enti del terzo \
settore e imprese. Ricevi il titolo del bando, l'atto, un documento intero e \
un suo frammento. Scrivi un breve contesto che colloca il frammento nel \
documento, per aiutare la ricerca a trovarlo. Il contesto non viene mostrato \
a chi legge e non sostituisce il frammento.

Rispondi con tre righe, in italiano, in testo semplice, senza altro prima o dopo:
BANDO: il bando com'è intitolato, e la parte del documento in cui sta il \
frammento (articolo, paragrafo, allegato o azione), se il documento la indica. \
Se il titolo elenca più azioni o misure e il documento ne tratta una sola, \
indica solo quella.
ARGOMENTO: una o due voci di questo elenco, scritte esattamente così e \
separate da punto e virgola: {"; ".join(VOCI)}. Se nessuna va bene, scrivi \
"{ALTRO}:" seguito da poche parole.
SERVE A: una frase su che cosa permette di sapere il frammento, con le parole \
che userebbe un ufficio comunale o un'impresa che cerca un finanziamento, non \
quelle dell'atto.

In tutto tra 50 e 100 parole.

Regole:
- Non scrivere numeri, importi, percentuali, date o scadenze che nel \
frammento non ci sono. Sono ammessi solo il numero dell'atto, l'allegato, \
l'articolo o il paragrafo e il codice dell'azione, come compaiono nel documento.
- Non nominare altri bandi, altri allegati o altre azioni, anche se il \
documento li cita, a meno che il frammento parli proprio di loro.
- Non scrivere nomi di persone, indirizzi email o numeri di telefono.
- Non riassumere il frammento e non ripeterne le frasi: di' dove sta e a che \
cosa serve.
- Non scrivere domande.
- Se il frammento è un indice, un'intestazione o un testo senza contenuto, \
scrivi solo la riga BANDO."""

RICHIESTA_FINALE = "Scrivi il contesto di questo frammento."

ETICHETTE = {"BANDO": "bando", "ARGOMENTO": "argomento", "SERVE A": "serve_a"}


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


def blocco_documento(documento: Documento) -> str:
    parti = [f"<titolo_del_bando>{documento.titolo}</titolo_del_bando>"]
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
    """Le tre righe per etichetta (bando, argomento, serve_a); None se fuori formato.

    Una riga senza etichetta continua la precedente. Un'etichetta ripetuta,
    o testo prima della prima etichetta, è fuori formato.
    """
    righe: dict[str, str] = {}
    ultima = None
    for riga in testo.strip().splitlines():
        if not riga.strip():
            continue
        m = re.match(r"^\s*\**\s*(BANDO|ARGOMENTO|SERVE A)\s*\**\s*:\s*(.*)$", riga)
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


# --- salvataggio e ripresa ---


def leggi_salvati(percorso: Path, impronta: str | None = None) -> dict[str, dict]:
    """Le righe salvate per id. Un'ultima riga troncata si ignora.

    Con `impronta`, una riga con un'impronta diversa ferma: le versioni
    delle istruzioni non si mescolano nello stesso file.
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
        salvati[dato["id"]] = dato
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
    righe = righe_del_contesto(testo) or {}
    voci, libero, ignote = voci_dell_argomento(righe.get("argomento", ""))
    return {
        "id": frammento.id,
        "fonte": documento.fonte,
        "chunk_num": frammento.chunk_num,
        "sha256_frammento": frammento.sha256,
        "impronta": impronta_istruzioni(),
        "modello": MODELLO,
        "testo": testo,
        "righe": righe,
        "argomento_voci": voci,
        "argomento_altro": libero,
        "argomento_non_ricondotto": ignote,
        "stop_reason": risposta.stop_reason,
        **uso,
        "costo_dollari": round(costo(uso), 8),
        "request_id": getattr(risposta, "_request_id", None),
        "ora": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


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
    """Per un file: segni dei gemelli (codici, nomi d'azione o di bando, numeri d'atto)."""

    codici: set[str] = field(default_factory=set)
    frasi: set[str] = field(default_factory=set)
    numeri: set[str] = field(default_factory=set)


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


# Il nome che distingue un bando dal suo gemello, deciso a mano dai titoli
# (docs/coda.md, "Passo 19d", punto 5): le altre parole dei titoli dei due
# bandi PMI ("costi", "euro", "fino") sono troppo comuni negli avvisi
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


def segni_del_gemello(
    documento: Documento, gemelli: list[Documento]
) -> SegniDelGemello:
    """Segni che un contesto parla di un gemello.

    Codici d'azione e d'allegato e nomi d'azione dei gemelli (dalla parte
    del registro e dal nome del file); il nome del bando gemello
    (NOMI_DEL_BANDO) e i numeri del suo atto che nell'atto proprio non ci
    sono. Il controllo li ammette quando stanno nel frammento.
    """
    from scripts.diagnostica.controlla_fatti import codice_della_parte

    segni = SegniDelGemello()
    numeri_propri = numeri_di(f"{documento.titolo} {documento.atto}")
    for g in gemelli:
        codice = codice_della_parte(g.parte)
        if codice and codice != codice_della_parte(documento.parte):
            segni.codici.add(codice)
            if ":" in g.parte:
                segni.frasi.add(_normale(g.parte.split(":", 1)[1]))
        allegato = _allegato(g.fonte)
        if allegato and allegato != _allegato(documento.fonte):
            segni.codici.add(allegato)
        if g.id_bando != documento.id_bando:
            segni.frasi |= set(NOMI_DEL_BANDO.get(g.id_bando, ()))
        segni.numeri |= {
            n
            for n in (_norma_numero(x) for x in NUMERO.findall(g.atto))
            if len(n) >= 3 and n not in numeri_propri
        }
    return segni


def testo_di_ricerca(
    righe: dict[str, str], quali=("bando", "argomento", "serve_a")
) -> str:
    """Il testo del contesto che entra nella ricerca: le righe scelte, senza etichette."""
    return " ".join(righe[q] for q in quali if righe.get(q)).strip()


def controlla_contesto(
    dato: dict, frammento: str, documento: Documento, segni: SegniDelGemello
) -> list[tuple[str, str]]:
    """Le violazioni di un contesto: (tipo, dettaglio); tipo numero, gemello o forma."""
    violazioni: list[tuple[str, str]] = []
    testo = dato.get("testo") or ""
    righe = dato.get("righe") or {}
    contenuto = testo_di_ricerca(righe)
    if dato.get("stop_reason") != "end_turn":
        violazioni.append(("forma", f"stop_reason {dato.get('stop_reason')}"))
    if not testo.strip():
        violazioni.append(("forma", "vuoto"))
        return violazioni
    if not righe or "bando" not in righe:
        violazioni.append(("forma", "fuori formato"))
    elif ("argomento" in righe) != ("serve_a" in righe):
        violazioni.append(("forma", "manca ARGOMENTO o SERVE A"))
    if "argomento" in righe:
        voci = dato.get("argomento_voci") or []
        if dato.get("argomento_non_ricondotto") or not voci:
            violazioni.append(
                ("forma", f"argomento non ricondotto: {righe['argomento']!r}")
            )
        if len(voci) > 2:
            violazioni.append(("forma", f"più di due voci: {voci}"))
    parole = len(_parole(contenuto))
    if parole > PAROLE_MASSIME:
        violazioni.append(("forma", f"troppo lungo: {parole} parole"))
    if "?" in testo:
        violazioni.append(("forma", "domanda"))
    if PREMESSA.match(testo):
        violazioni.append(("forma", "premessa"))
    quota = quota_copiata(contenuto, frammento)
    if quota > QUOTA_COPIA:
        violazioni.append(("forma", f"copiato dal frammento: {quota:.0%}"))
    if contatti_rimasti(testo, documento.titolo) or "@" in testo:
        violazioni.append(("forma", "contatti"))

    # numeri e date
    ammessi = numeri_di(f"{documento.titolo} {documento.atto} {documento.parte}")
    del_frammento = numeri_di(frammento)
    del_documento = numeri_di(documento.testo)
    codici_ammessi = set(
        CODICE.findall(
            f"{documento.titolo} {documento.atto} {documento.parte} {documento.testo}"
        )
    )
    resto = contenuto
    for m in RIFERIMENTO.finditer(contenuto):
        numero = _norma_numero(re.sub(r"^[A-Z]", "", m[1]))
        if m[1] not in codici_ammessi and numero not in del_documento:
            violazioni.append(("numero", f"riferimento non nel documento: {m[0]!r}"))
    resto = RIFERIMENTO.sub(" ", resto)
    for codice in CODICE.findall(resto):
        if codice not in codici_ammessi:
            violazioni.append(("numero", f"codice non nel documento: {codice}"))
    resto = CODICE.sub(" ", resto)
    for n in NUMERO.findall(resto):
        norma = _norma_numero(n)
        if norma not in del_frammento and norma not in ammessi:
            violazioni.append(("numero", f"numero non nel frammento: {n}"))
    dove_ammesse = (
        f"{frammento} {documento.titolo} {documento.atto} {documento.parte}"
    ).lower()
    for regola in (PAROLE_NUMERO, MESI):
        for m in regola.finditer(contenuto):
            if m[0].lower() not in dove_ammesse:
                violazioni.append(("numero", f"parola non nel frammento: {m[0]}"))

    # gemello: ammesso se il segno sta nel frammento
    for codice in sorted(segni.codici):
        if re.search(rf"\b{codice}\b", contenuto, re.IGNORECASE) and not re.search(
            rf"\b{codice}\b", frammento, re.IGNORECASE
        ):
            violazioni.append(("gemello", f"codice {codice}"))
    for frase in sorted(segni.frasi):
        cerca = rf"\b{re.escape(frase)}\b"
        if re.search(cerca, _normale(contenuto)) and not re.search(
            cerca, _normale(frammento)
        ):
            violazioni.append(("gemello", f"nome {frase!r}"))
    numeri_contenuto = {_norma_numero(n) for n in NUMERO.findall(contenuto)}
    for numero in sorted(segni.numeri & numeri_contenuto):
        if numero not in del_frammento:
            violazioni.append(("gemello", f"atto {numero}"))
    return violazioni


def controlla_tutti(
    documenti: list[Documento], salvati: dict[str, dict]
) -> tuple[dict[str, list[tuple[str, str]]], list[str]]:
    """(violazioni per id del frammento, linee del rapporto)."""
    from collections import Counter

    gemelli = gemelli_dei_file(documenti)
    violazioni: dict[str, list[tuple[str, str]]] = {}
    per_file = []
    tipi: Counter = Counter()
    solo_bando = 0
    corti = 0
    voci: Counter = Counter()
    for d in documenti:
        segni = segni_del_gemello(d, gemelli[d.fonte])
        fatti = [f for f in d.frammenti if f.id in salvati]
        con = 0
        for f in fatti:
            dato = salvati[f.id]
            trovate = controlla_contesto(dato, f.testo, d, segni)
            righe = dato.get("righe") or {}
            if righe and set(righe) == {"bando"}:
                solo_bando += 1
            if len(_parole(testo_di_ricerca(righe))) < PAROLE_MINIME:
                corti += 1
            voci.update(dato.get("argomento_voci") or ["(nessuna)"])
            if trovate:
                violazioni[f.id] = trovate
                con += 1
                tipi.update({t for t, _ in trovate})
        per_file.append((d.fonte, len(fatti), len(d.frammenti), con))
    totale = sum(n for _, n, _, _ in per_file)
    linee = [
        (
            f"Controlli sui contesti generati ({totale} su "
            f"{sum(len(d.frammenti) for d in documenti)} frammenti)"
        ),
        f"Frammenti con almeno una violazione: {len(violazioni)} "
        f"({len(violazioni) / totale:.1%})"
        if totale
        else "Nessun contesto salvato",
        "Per tipo (frammenti): "
        + ", ".join(f"{t} {n}" for t, n in sorted(tipi.items())),
        f"Solo riga BANDO (indice o testo senza contenuto, ammesso): {solo_bando}",
        f"Contesti sotto {PAROLE_MINIME} parole (non è una violazione): {corti}",
        "Voci di ARGOMENTO: " + ", ".join(f"{v} {n}" for v, n in voci.most_common()),
        "",
        "Per file: frammenti con contesto / frammenti, con violazioni",
    ]
    linee += [f"  {f}: {n} / {tot}, {c}" for f, n, tot, c in per_file]
    linee += ["", "Violazioni, per frammento:"]
    for d in documenti:
        for f in d.frammenti:
            if f.id in violazioni:
                linee.append(
                    f"  {d.fonte} #{f.chunk_num}: "
                    + "; ".join(f"{t}: {x}" for t, x in violazioni[f.id])
                )
    return violazioni, linee


def esegui_controlli(prova: bool) -> int:
    documenti = leggi_documenti()
    percorso = FILE_PROVA if prova else FILE_CONTESTI
    if prova:
        documenti = [d for d in documenti if d.fonte == FILE_DELLA_PROVA]
    salvati = leggi_salvati(percorso, impronta_istruzioni())
    if not salvati:
        print(f"Nessun contesto in {percorso}")
        return 1
    _, linee = controlla_tutti(documenti, salvati)
    nome = "controllo_contesti_prova.txt" if prova else "controllo_contesti.txt"
    testo = "\n".join(linee)
    (CARTELLA / nome).write_text(testo + "\n", encoding="utf-8")
    print(testo)
    print(f"\nScritto {CARTELLA / nome}")
    return 0


# --- uso ---


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--prova", action="store_true", help=f"solo {FILE_DELLA_PROVA} (5 frammenti)"
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
        if argomenti.controlla:
            return esegui_controlli(argomenti.prova)
        if argomenti.tetto_dollari is None or argomenti.tetto_dollari <= 0:
            print("Serve --tetto-dollari, maggiore di zero.", file=sys.stderr)
            return 2
        documenti = leggi_documenti()
        controlla_documenti(documenti)
        percorso = FILE_CONTESTI
        if argomenti.prova:
            documenti = [d for d in documenti if d.fonte == FILE_DELLA_PROVA]
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
            _, linee = controlla_tutti(documenti, salvati)
            print("\n" + "\n".join(linee))
        return 0
    except ArrestoGenerazione as motivo:
        print(f"Arresto: {motivo}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
