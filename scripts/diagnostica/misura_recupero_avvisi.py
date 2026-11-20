"""Misura del recupero sui frammenti degli avvisi (passo 19d).

Uso:
    python -u -m scripts.diagnostica.misura_recupero_avvisi --dividi
        [--foglio dati-grezzi/fatti_pdf_modello_2026-11-20.xlsx]
        [--csv-controllo dati-grezzi/prova/fatti_controllo_2026-11-20.csv]
        [--uscita dati-grezzi/prova/fatti_divisione_2026-11-20.csv]
    python -u -m scripts.diagnostica.misura_recupero_avvisi --misura
        [--divisione ...] [--cartella dati-grezzi/prova/19d/v0] [--controllo]

Tempo 2, --misura (descritto in fondo, sotto "Misura").

Tempo 1, --dividi: i fatti del foglio (le righe con una frase) si
dividono a caso in due metà, "taratura" e "controllo", con il seme fisso
SEME. La taratura serve a scegliere la variante; il controllo si guarda
una volta sola, alla fine (docs/coda.md, "Passo 19d").

Regole della divisione (decisioni del 20/11/2026):
1. l'unità è il fatto: un fatto in più pezzi resta intero;
2. per ogni bando, le due metà differiscono al più di un fatto, e così i
   totali;
3. le frasi identiche (al livello "senza spazi" di controlla_fatti)
   stanno nella stessa metà, e con loro i gruppi di GRUPPI_FISSI;
4. le frasi di controllo sui gemelli (solo_calcolato "no" nel CSV di
   controlla_fatti) si ripartiscono: per ogni bando e in totale le due
   metà differiscono al più di una;
5. differenze massime tra le due metà (CONDIZIONI, decisione del
   20/11/2026, presa prima di ogni misura): righe di tabella 1; fatti con
   risposta in più pezzi 1; domande "semplice" 3 e domande "caso" 3;
   fatti con tutti i pezzi nella parte vista dal modello di embedding 2.
   "Nella parte vista" viene da pezzi_visti del CSV di controlla_fatti,
   uguale al numero dei pezzi: un pezzo è visto se sta per intero nei
   primi car_visti caratteri di almeno un frammento. La colonna posizioni
   dello stesso CSV riporta solo il primo frammento che contiene il pezzo
   e non basta (riga 15: visto solo in un frammento successivo).

Come si sceglie: con il generatore inizializzato da SEME, per ogni bando
si mescolano i fatti e la prima metà va in taratura (il bando con un
numero dispari di fatti dà quello in più a una metà scelta a caso); se la
proposta viola le regole 2-5 se ne fa un'altra, con lo stesso generatore.
Lo stesso seme e gli stessi ingressi danno sempre la stessa divisione.
Se in TENTATIVI_MASSIMI proposte nessuna rispetta tutto, lo script si
ferma e dice, condizione per condizione, quante proposte la violano e
quante violano solo quella: le condizioni non si allentano da sole.

Il file della divisione non si sovrascrive: se esiste già, lo script
rifà la divisione e dice solo se coincide. Accanto si scrive l'impronta
(.sha256). Nessuna rete, nessun modello, Chroma non si apre.

Misura (tempo 2). La divisione si legge solo se la sua impronta è quella
del file .sha256. Si leggono solo i fatti di una metà: la taratura, o il
controllo con l'opzione esplicita --controllo (da usare solo su
istruzione). Il Chroma vero non si apre: se ne fa una copia nella
cartella di uscita, e le impronte dei suoi file si confrontano prima e
dopo. Per ogni fatto, con k=K:
A. il percorso dell'app: src.chains.rag.recupera su avvolgi(recupero),
   dove recupero ha la cerca di RecuperoIbrido;
B. la stessa ricerca ibrida ristretta ai frammenti del bando
   (RecuperoMisura.cerca_nel_bando).
Criterio di "trovato" e cause dei mancati: sotto, "tempo 2: misura". La
posizione di un frammento giusto oltre i primi K si prende da una
seconda ricerca con ampiezza PROFONDITA, perché con l'ampiezza dell'app
(20 per lista) i candidati sono al più 40. Uscite nella cartella:
misura_<metà>.csv (una riga per fatto) e rapporto_<metà>.txt. Durante la
misura ogni connessione di rete ferma lo script; il modello di embedding
si legge solo dalla copia su disco (HF_HUB_OFFLINE). Nessun modello di
linguaggio.
"""

import argparse
import csv
import hashlib
import io
import random
import sys
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path

from scripts.diagnostica.controlla_fatti import (
    NOTA_APISTICI,
    SEPARATORE_PEZZI,
    Frammento,
    _unione,
    leggi_foglio,
    livello_c,
    posizione,
    unita_della_frase,
)
from src.config import DATI_GREZZI_DIR

SEME = 19_2026_1120

TARATURA = "taratura"
CONTROLLO = "controllo"

# Gruppi decisi a mano (decisione 6d del 20/11/2026): la riga 21
# (Cultura, frase di controllo identica nell'avviso Sport), la 24 (Sport,
# identica nell'avviso Cultura) e la 23 (Cultura, quasi gemella: un pezzo
# identico nell'avviso Sport) stanno nella stessa metà. Numeri di riga del
# foglio fatti_pdf_modello_2026-11-20.xlsx.
GRUPPI_FISSI: tuple[tuple[int, ...], ...] = ((21, 23, 24),)

TENTATIVI_MASSIMI = 5_000

# Regola 5: nome della condizione -> differenza massima tra le due metà
CONDIZIONI = {
    "righe di tabella": 1,
    "risposte in più pezzi": 1,
    "registro semplice": 3,
    "registro caso": 3,
    "tutti i pezzi nella parte vista": 2,
}

FOGLIO = DATI_GREZZI_DIR / "fatti_pdf_modello_2026-11-20.xlsx"
CONTROLLO_CSV = DATI_GREZZI_DIR / "prova" / "fatti_controllo_2026-11-20.csv"
DIVISIONE = DATI_GREZZI_DIR / "prova" / "fatti_divisione_2026-11-20.csv"

COLONNE = [
    "riga",
    "id_bando",
    "meta",
    "gruppo",
    "registro",
    "in_tabella",
    "pezzi",
    "gemello",
    "visti",
]


class ErroreDivisione(Exception):
    """Ingressi che non tornano, o regole che non si possono rispettare."""


# --- ingressi ---


def leggi_controllo(percorso: Path) -> dict[int, dict]:
    """Dal CSV di controlla_fatti, per riga del foglio: id_bando, gemello, visti.

    gemello: solo_calcolato "no"; visti: pezzi_visti uguale a pezzi.
    """
    with percorso.open(encoding="utf-8-sig", newline="") as f:
        return {
            int(r["riga"]): {
                "id_bando": r["id_bando"],
                "gemello": r["solo_calcolato"].strip() == "no",
                "visti": int(r["pezzi_visti"] or 0) == int(r["pezzi"]),
            }
            for r in csv.DictReader(f)
        }


def controlla_ingressi(
    fatti: list[dict], controllo: dict[int, dict], fissi: tuple[tuple[int, ...], ...]
) -> None:
    """Foglio e controllo con le stesse righe e gli stessi bandi; gruppi fissi esistenti."""
    bando_di = {f["riga"]: f["id_bando"] for f in fatti}
    if set(controllo) != set(bando_di):
        raise ErroreDivisione(
            f"righe solo nel foglio {sorted(set(bando_di) - set(controllo))}, "
            f"solo nel controllo {sorted(set(controllo) - set(bando_di))}"
        )
    for riga, dati in controllo.items():
        if bando_di[riga] != dati["id_bando"]:
            raise ErroreDivisione(
                f"riga {riga}: {dati['id_bando']} nel controllo, "
                f"{bando_di[riga]!r} nel foglio"
            )
    for gruppo in fissi:
        mancanti = [r for r in gruppo if r not in bando_di]
        if mancanti:
            raise ErroreDivisione(
                f"gruppo fisso {gruppo}: righe senza frase {mancanti}"
            )


# --- gruppi ---


def gruppi(
    fatti: list[dict], fissi: tuple[tuple[int, ...], ...] = GRUPPI_FISSI
) -> dict[int, int]:
    """Riga -> gruppo (la riga più bassa del gruppo).

    Stanno insieme i fatti con la frase identica al livello senza spazi e
    quelli di un gruppo fisso; un fatto da solo è un gruppo di sé.
    """
    capo = {f["riga"]: f["riga"] for f in fatti}

    def radice(r: int) -> int:
        while capo[r] != r:
            r = capo[r]
        return r

    def unisci(a: int, b: int) -> None:
        ra, rb = radice(a), radice(b)
        if ra != rb:
            capo[max(ra, rb)] = min(ra, rb)

    per_frase: dict[str, int] = {}
    for f in fatti:
        chiave = livello_c(str(f["frase"]))
        if chiave in per_frase:
            unisci(per_frase[chiave], f["riga"])
        else:
            per_frase[chiave] = f["riga"]
    for gruppo in fissi:
        for r in gruppo[1:]:
            unisci(gruppo[0], r)
    return {r: radice(r) for r in capo}


# --- divisione ---


def numero_pezzi(fatto: dict) -> int:
    return len(str(fatto["frase"]).split(SEPARATORE_PEZZI))


def insiemi_delle_condizioni(fatti: list[dict]) -> dict[str, set[int]]:
    """Per ogni condizione di CONDIZIONI, le righe che contano."""
    registro = {f["riga"]: str(f.get("registro") or "").strip() for f in fatti}
    return {
        "righe di tabella": {
            f["riga"] for f in fatti if str(f.get("in_tabella") or "").strip() == "sì"
        },
        "risposte in più pezzi": {f["riga"] for f in fatti if numero_pezzi(f) > 1},
        "registro semplice": {r for r, v in registro.items() if v == "semplice"},
        "registro caso": {r for r, v in registro.items() if v == "caso"},
        "tutti i pezzi nella parte vista": {f["riga"] for f in fatti if f.get("visti")},
    }


def _squilibrio(meta: dict[int, str], righe) -> int:
    lati = Counter(meta[r] for r in righe)
    return abs(lati[TARATURA] - lati[CONTROLLO])


def violazioni(
    meta: dict[int, str],
    bando_di: dict[int, str],
    gruppo_di: dict[int, int],
    gemelli: set[int],
    insiemi: dict[str, set[int]],
    condizioni: dict[str, int],
) -> list[str]:
    """Le regole 2-5 del modulo che una proposta riga -> metà non rispetta."""
    violate = []
    per_gruppo = defaultdict(set)
    for r, m in meta.items():
        per_gruppo[gruppo_di[r]].add(m)
    if any(len(lati) > 1 for lati in per_gruppo.values()):
        violate.append("gruppi")

    per_bando: dict[str, list[int]] = defaultdict(list)
    for r, b in bando_di.items():
        per_bando[b].append(r)
    if _squilibrio(meta, meta) > 1 or any(
        _squilibrio(meta, righe) > 1 for righe in per_bando.values()
    ):
        violate.append("bandi")
    if _squilibrio(meta, gemelli) > 1 or any(
        _squilibrio(meta, [r for r in righe if r in gemelli]) > 1
        for righe in per_bando.values()
    ):
        violate.append("gemelli")

    for nome, massimo in condizioni.items():
        if _squilibrio(meta, insiemi[nome]) > massimo:
            violate.append(nome)
    return violate


def proposta(rng: random.Random, per_bando: dict[str, list[int]]) -> dict[int, str]:
    """Per ogni bando, in ordine di nome: righe mescolate, la prima metà in taratura."""
    meta = {}
    for id_bando in sorted(per_bando):
        righe = sorted(per_bando[id_bando])
        rng.shuffle(righe)
        quante = len(righe) // 2 + (rng.random() < 0.5 if len(righe) % 2 else 0)
        for indice, r in enumerate(righe):
            meta[r] = TARATURA if indice < quante else CONTROLLO
    return meta


def dividi(
    fatti: list[dict],
    gemelli: set[int],
    seme: int = SEME,
    fissi: tuple[tuple[int, ...], ...] = GRUPPI_FISSI,
    condizioni: dict[str, int] | None = None,
) -> tuple[dict[int, str], dict[int, int], int]:
    """(riga -> metà, riga -> gruppo, tentativi usati)."""
    condizioni = CONDIZIONI if condizioni is None else condizioni
    bando_di = {f["riga"]: f["id_bando"] for f in fatti}
    gruppo_di = gruppi(fatti, fissi)
    insiemi = insiemi_delle_condizioni(fatti)
    per_bando: dict[str, list[int]] = defaultdict(list)
    for r, b in bando_di.items():
        per_bando[b].append(r)

    rng = random.Random(seme)
    violata: Counter = Counter()
    sola: Counter = Counter()
    for tentativo in range(1, TENTATIVI_MASSIMI + 1):
        meta = proposta(rng, per_bando)
        violate = violazioni(meta, bando_di, gruppo_di, gemelli, insiemi, condizioni)
        if not violate:
            return meta, gruppo_di, tentativo
        violata.update(violate)
        if len(violate) == 1:
            sola.update(violate)
    nomi = ["gruppi", "bandi", "gemelli", *condizioni]
    dettaglio = "; ".join(
        f"{n}: violata in {violata[n]}, unica violata in {sola[n]}" for n in nomi
    )
    raise ErroreDivisione(
        f"nessuna divisione valida in {TENTATIVI_MASSIMI} tentativi ({dettaglio})"
    )


# --- uscita ---


def righe_divisione(
    fatti: list[dict],
    meta: dict[int, str],
    gruppo_di: dict[int, int],
    gemelli: set[int],
) -> list[dict]:
    return [
        {
            "riga": f["riga"],
            "id_bando": f["id_bando"],
            "meta": meta[f["riga"]],
            "gruppo": gruppo_di[f["riga"]],
            "registro": str(f.get("registro") or "").strip(),
            "in_tabella": str(f.get("in_tabella") or "").strip(),
            "pezzi": numero_pezzi(f),
            "gemello": "sì" if f["riga"] in gemelli else "no",
            "visti": "sì" if f.get("visti") else "no",
        }
        for f in sorted(fatti, key=lambda f: f["riga"])
    ]


def testo_csv(righe: list[dict]) -> bytes:
    uscita = io.StringIO(newline="")
    scrittore = csv.DictWriter(uscita, fieldnames=COLONNE, lineterminator="\n")
    scrittore.writeheader()
    scrittore.writerows(righe)
    return uscita.getvalue().encode("utf-8")


def impronta(dati: bytes) -> str:
    return hashlib.sha256(dati).hexdigest()


def rapporto(righe: list[dict], seme: int, tentativi: int) -> list[str]:
    linee = [f"Seme: {seme} (proposta accettata al tentativo {tentativi})", ""]
    per_bando = Counter((r["id_bando"], r["meta"]) for r in righe)
    linee.append(f"{'bando':<62} taratura controllo")
    for id_bando in sorted({r["id_bando"] for r in righe}):
        linee.append(
            f"{id_bando:<62} {per_bando[(id_bando, TARATURA)]:>8} "
            f"{per_bando[(id_bando, CONTROLLO)]:>9}"
        )
    for lato in (TARATURA, CONTROLLO):
        sue = [r for r in righe if r["meta"] == lato]
        registri = Counter(r["registro"] for r in sue)
        visti = sum(r["visti"] == "sì" for r in sue)
        gemelle = [
            f"{r['riga']} ({r['id_bando']})" for r in sue if r["gemello"] == "sì"
        ]
        linee += [
            "",
            f"{lato}: {len(sue)} fatti",
            f"  registro: semplice {registri['semplice']}, caso {registri['caso']}",
            f"  righe di tabella: {sum(r['in_tabella'] == 'sì' for r in sue)}",
            f"  risposte in più pezzi: {sum(r['pezzi'] > 1 for r in sue)}",
            f"  fatti con tutti i pezzi nella parte vista: {visti}",
            f"  frasi gemelle: {len(gemelle)}: " + "; ".join(gemelle),
        ]
    return linee


# --- tempo 2: misura ---
#
# Un fatto è "trovato" se ogni suo pezzo sta, al livello senza spazi, in un
# frammento tra i primi K di un documento giusto: un file del bando (per
# gli apistici, il file dell'allegato della nota). Per una riga di tabella
# il pezzo è l'insieme delle sue celle, tutte nello stesso frammento.

K = 10
AMPIEZZA_APP = 20  # quella di RecuperoIbrido.cerca, usata dall'app
PROFONDITA = 50  # per la posizione del frammento giusto oltre i primi K
V0 = DATI_GREZZI_DIR / "prova" / "19d" / "v0"

# Documenti gemelli tra bandi (docs/coda.md, "Passo 19d", punto 5). Gli
# allegati degli apistici sono gemelli tra loro: si ricavano dalla nota.
GEMELLI_DEI_BANDI = {
    "cultura-missione-comune-2026": "sport-missione-comune-2026",
    "sport-missione-comune-2026": "cultura-missione-comune-2026",
    "bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-7057d9": (
        "bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-8cd3ac"
    ),
    "bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-8cd3ac": (
        "bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-7057d9"
    ),
}

GEMELLO = "gemello al posto del giusto"
FUORI_VISTA = "pezzo fuori dalla parte vista"
SPEZZATO = "pezzo spezzato tra frammenti"
ASSENTE_FRAMMENTI = "pezzo in nessun frammento del documento giusto"

COLONNE_MISURA = [
    "riga",
    "id_bando",
    "registro",
    "in_tabella",
    "pezzi",
    "visti",
    "gemello",
    "documenti_giusti",
    "trovato_A",
    "primo_giusto_A",
    "posizioni_pezzi_A",
    "cause_A",
    "gemello_senza_giusto_A",
    "pezzo_dal_gemello_A",
    "ristretta_A",
    "ristretta_giusta_A",
    "di_sempre_A",
    "trovato_B",
    "primo_giusto_B",
    "posizioni_pezzi_B",
    "cause_B",
    "gemello_senza_giusto_B",
    "pezzo_dal_gemello_B",
]


class ErroreMisura(Exception):
    """Divisione alterata, ingressi che non tornano, rete toccata."""


def verifica_impronta(divisione: Path) -> str:
    """L'impronta della divisione, se coincide con quella del file .sha256."""
    attesa = Path(f"{divisione}.sha256").read_text(encoding="utf-8").split()[0]
    vera = impronta(divisione.read_bytes())
    if vera != attesa:
        raise ErroreMisura(f"{divisione.name}: sha256 {vera}, atteso {attesa}")
    return vera


def righe_della_meta(divisione: Path, lato: str) -> dict[int, dict]:
    """Le righe della divisione di una sola metà; le altre non escono da qui."""
    with divisione.open(encoding="utf-8", newline="") as f:
        return {int(r["riga"]): r for r in csv.DictReader(f) if r["meta"] == lato}


def fatti_della_meta(foglio: list[dict], righe: dict[int, dict]) -> list[dict]:
    """I fatti del foglio nelle righe date, con i dati della divisione."""
    fatti = []
    for f in foglio:
        if f["riga"] not in righe:
            continue
        riga = righe[f["riga"]]
        if riga["id_bando"] != f["id_bando"]:
            raise ErroreMisura(
                f"riga {f['riga']}: {riga['id_bando']} nella divisione, "
                f"{f['id_bando']} nel foglio"
            )
        fatti.append({**f, "visti": riga["visti"], "gemello": riga["gemello"]})
    mancanti = set(righe) - {f["riga"] for f in fatti}
    if mancanti:
        raise ErroreMisura(f"righe della divisione senza frase: {sorted(mancanti)}")
    return fatti


def impronte_cartella(cartella: Path) -> dict[str, str]:
    """sha256 di ogni file della cartella, per percorso relativo."""
    return {
        p.relative_to(cartella).as_posix(): impronta(p.read_bytes())
        for p in sorted(cartella.rglob("*"))
        if p.is_file()
    }


@contextmanager
def senza_connessioni():
    """Ogni tentativo di aprire una connessione di rete ferma la misura."""
    import socket

    originali = (
        socket.socket.connect,
        socket.socket.connect_ex,
        socket.create_connection,
    )

    def vietato(*args, **kwargs):
        raise ErroreMisura(f"tentativo di connessione di rete: {args[1:]!r}")

    socket.socket.connect = vietato
    socket.socket.connect_ex = vietato
    socket.create_connection = vietato
    try:
        yield
    finally:
        socket.socket.connect, socket.socket.connect_ex, socket.create_connection = (
            originali
        )


# --- documenti giusti e gemelli ---


def documenti_del_fatto(
    fatto: dict, file_per_bando: dict[str, list[dict]]
) -> tuple[set[str], set[str]]:
    """(fonti giuste, fonti gemelle) del fatto, come nomi di file.

    Giusti: i file del bando, o il file dell'allegato della nota per gli
    apistici; gemelli: gli altri allegati dello stesso bando, o i file del
    bando gemello.
    """
    del_bando = file_per_bando.get(fatto["id_bando"], [])
    if not del_bando:
        raise ErroreMisura(f"riga {fatto['riga']}: bando senza file nel registro")
    nota = NOTA_APISTICI.match(str(fatto.get("note") or ""))
    if nota:
        giusti = {
            r["nome_file"] for r in del_bando if r["parte"] == f"Azione {nota[1]}"
        }
        if not giusti:
            raise ErroreMisura(f"riga {fatto['riga']}: allegato {nota[2]} non trovato")
        gemelli = {r["nome_file"] for r in del_bando} - giusti
        return giusti, gemelli
    gemello = GEMELLI_DEI_BANDI.get(fatto["id_bando"])
    gemelli = {r["nome_file"] for r in file_per_bando.get(gemello, [])}
    return {r["nome_file"] for r in del_bando}, gemelli


# --- criterio di "trovato" e cause ---


def unita_del_fatto(fatto: dict) -> list[list[str]]:
    in_tabella = str(fatto.get("in_tabella") or "").strip().lower() == "sì"
    return unita_della_frase(fatto["frase"], in_tabella)


def contiene(pezzo: list[str], fr: Frammento) -> tuple[int, int] | None:
    """Inizio e fine del pezzo (tutte le sue celle) nel testo vero del frammento."""
    tratti = [posizione(livello_c(c), fr) for c in pezzo]
    if not tratti or any(t is None for t in tratti):
        return None
    return min(t[0] for t in tratti), max(t[1] for t in tratti)


def prima_posizione(
    pezzo: list[str], elenco: list[tuple[str, Frammento]], fonti: set[str]
) -> int | None:
    """Posizione (da 1) del primo frammento di una delle fonti che contiene il pezzo."""
    for numero, (fonte, fr) in enumerate(elenco, start=1):
        if fonte in fonti and contiene(pezzo, fr):
            return numero
    return None


def spezzato(pezzo: list[str], frammenti: list[Frammento]) -> bool:
    """Il pezzo sta in due frammenti consecutivi uniti, e in nessuno da solo."""
    testo_c = "".join(livello_c(c) for c in pezzo)
    return len(pezzo) == 1 and any(
        testo_c in _unione(a.compatto, b.compatto)
        for a, b in zip(frammenti, frammenti[1:], strict=False)
    )


def cause_del_pezzo(
    pezzo: list[str],
    primi: list[tuple[str, Frammento]],
    profondi: list[tuple[str, Frammento]],
    giusti: set[str],
    gemelli: set[str],
    frammenti_per_fonte: dict[str, list[Frammento]],
) -> list[str]:
    """Le cause per un pezzo che non sta in nessun frammento giusto tra i primi."""
    cause = []
    del_documento = [
        fr for f in sorted(giusti) for fr in frammenti_per_fonte.get(f, [])
    ]
    tratti = [t for fr in del_documento if (t := contiene(pezzo, fr))]
    visti = [
        fr
        for fr in del_documento
        if (t := contiene(pezzo, fr)) and t[1] <= fr.car_visti
    ]
    if not tratti:
        separati = any(
            spezzato(pezzo, frammenti_per_fonte.get(f, [])) for f in sorted(giusti)
        )
        cause.append(SPEZZATO if separati else ASSENTE_FRAMMENTI)
    elif not visti:
        cause.append(FUORI_VISTA)
    if tratti:
        profonda = prima_posizione(pezzo, profondi, giusti)
        cause.append(
            f"frammento giusto in posizione {profonda} (ampiezza {PROFONDITA})"
            if profonda
            else f"frammento giusto oltre i primi {PROFONDITA}"
        )
    if prima_posizione(pezzo, primi, gemelli):
        cause.append(GEMELLO)
    return cause


def valuta(
    fatto: dict,
    primi: list[tuple[str, Frammento]],
    profondi: list[tuple[str, Frammento]],
    giusti: set[str],
    gemelli: set[str],
    frammenti_per_fonte: dict[str, list[Frammento]],
) -> dict:
    """Esito di un fatto su un elenco di frammenti recuperati (i primi K)."""
    unita = unita_del_fatto(fatto)
    posizioni = [prima_posizione(p, primi, giusti) for p in unita]
    dal_gemello = [prima_posizione(p, primi, gemelli) for p in unita]
    cause = []
    for numero, (pezzo, pos) in enumerate(zip(unita, posizioni, strict=True), 1):
        if pos is None:
            elenco = cause_del_pezzo(
                pezzo, primi, profondi, giusti, gemelli, frammenti_per_fonte
            )
            prefisso = f"pezzo {numero}: " if len(unita) > 1 else ""
            cause.append(prefisso + "; ".join(elenco))
    trovate = [p for p in posizioni if p is not None]
    fonti_primi = {fonte for fonte, _ in primi}
    return {
        "trovato": all(p is not None for p in posizioni),
        "primo_giusto": min(trovate) if trovate else None,
        "posizioni_pezzi": posizioni,
        "cause": cause,
        "gemello_senza_giusto": bool(fonti_primi & gemelli)
        and not fonti_primi & giusti,
        "pezzo_dal_gemello": any(
            g is not None and (p is None or g < p)
            for g, p in zip(dal_gemello, posizioni, strict=True)
        ),
    }


# --- recupero sulla copia ---


def frammento_di(documento) -> tuple[str, Frammento]:
    meta = documento.metadata
    testo = documento.page_content
    return meta.get("fonte") or "", Frammento(
        meta.get("chunk_num", -1),
        meta.get("page", 0),
        testo,
        meta.get("car_visti", len(testo)),
    )


def apri_recupero(copia: Path):
    """RecuperoMisura sulla copia di Chroma: RecuperoIbrido più la ricerca per bando."""
    from langchain_chroma import Chroma

    from src.config import COLLECTION_NAME
    from src.retrieval import COSTANTE_RRF, RecuperoIbrido, chiave_di, tokenizza
    from src.vectorstore import crea_embeddings

    class RecuperoMisura(RecuperoIbrido):
        """La ricerca dell'app (cerca è quella di RecuperoIbrido), su un altro store."""

        def __init__(self, store) -> None:
            from langchain_core.documents import Document
            from rank_bm25 import BM25Okapi

            self.store = store
            dati = self.store.get()
            self.documenti = [
                Document(page_content=testo, metadata=meta)
                for testo, meta in zip(
                    dati["documents"], dati["metadatas"], strict=True
                )
            ]
            self.bm25 = BM25Okapi([tokenizza(d.page_content) for d in self.documenti])

        def cerca_nel_bando(
            self, domanda: str, id_bando: str, k: int, ampiezza: int = AMPIEZZA_APP
        ) -> list:
            """Come cerca, solo tra i frammenti del bando; BM25 pesato su tutto l'indice."""
            densa = self.store.similarity_search(
                domanda, k=ampiezza, filter={"id_bando": id_bando}
            )
            punteggi = self.bm25.get_scores(tokenizza(domanda))
            indici = [
                i
                for i, d in enumerate(self.documenti)
                if d.metadata.get("id_bando") == id_bando
            ]
            migliori = sorted(indici, key=lambda i: punteggi[i], reverse=True)[
                :ampiezza
            ]
            lessicale = [self.documenti[i] for i in migliori if punteggi[i] > 0]
            punti: dict = {}
            for nome, elenco in (("densa", densa), ("lessicale", lessicale)):
                for pos, documento in enumerate(elenco, start=1):
                    voce = punti.setdefault(
                        chiave_di(documento),
                        {"doc": documento, "punteggio": 0.0, "origini": []},
                    )
                    voce["punteggio"] += 1 / (COSTANTE_RRF + pos)
                    voce["origini"].append(f"{nome} #{pos}")
            ordinati = sorted(
                punti.values(), key=lambda v: v["punteggio"], reverse=True
            )
            return [(v["doc"], v["punteggio"], v["origini"]) for v in ordinati[:k]]

    store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=crea_embeddings(),
        persist_directory=str(copia),
        collection_metadata={"hnsw:space": "cosine"},
    )
    return RecuperoMisura(store)


class Profondo:
    """Il recupero con ampiezza PROFONDITA, da avvolgere come quello dell'app."""

    def __init__(self, base) -> None:
        self.base = base

    def titoli(self) -> dict[str, str]:
        return self.base.titoli()

    def cerca(self, domanda: str, k: int = 8, fonte: str | None = None) -> list:
        return self.base.cerca(domanda, k=k, ampiezza=PROFONDITA, fonte=fonte)


# --- numeri ---


def _quota(parte: int, tutto: int) -> str:
    return f"{parte}/{tutto}" + (f" ({100 * parte / tutto:.1f}%)" if tutto else "")


def riepilogo_condizione(righe: list[dict], c: str) -> list[str]:
    trovati = [r for r in righe if r[f"trovato_{c}"] == "sì"]
    linee = [f"Condizione {c}: trovati {_quota(len(trovati), len(righe))}"]
    gruppi_righe = [
        ("registro semplice", lambda r: r["registro"] == "semplice"),
        ("registro caso", lambda r: r["registro"] == "caso"),
        ("tabella sì", lambda r: r["in_tabella"] == "sì"),
        ("tabella no", lambda r: r["in_tabella"] != "sì"),
        ("tutti i pezzi nella parte vista", lambda r: r["visti"] == "sì"),
        ("non tutti nella parte vista", lambda r: r["visti"] != "sì"),
        ("risposta in un pezzo", lambda r: int(r["pezzi"]) == 1),
        ("risposta in più pezzi", lambda r: int(r["pezzi"]) > 1),
    ]
    for nome, scelta in gruppi_righe:
        sue = [r for r in righe if scelta(r)]
        linee.append(
            f"  {nome:<34} {_quota(sum(r[f'trovato_{c}'] == 'sì' for r in sue), len(sue))}"
        )
    primi = [int(r[f"primo_giusto_{c}"]) for r in righe if r[f"primo_giusto_{c}"]]
    linee.append(
        "  primo frammento giusto: al 1° posto "
        f"{sum(p == 1 for p in primi)}, tra i primi 3 {sum(p <= 3 for p in primi)}, "
        f"tra i primi 5 {sum(p <= 5 for p in primi)}, tra i primi 10 {len(primi)}, "
        f"nessuno tra i primi 10 {len(righe) - len(primi)}"
    )
    linee.append(
        "  gemello tra i primi 10 e nessun frammento giusto: "
        f"{sum(r[f'gemello_senza_giusto_{c}'] == 'sì' for r in righe)}; "
        "pezzo preso dal gemello prima che dal giusto: "
        f"{sum(r[f'pezzo_dal_gemello_{c}'] == 'sì' for r in righe)}"
    )
    return linee


def rapporto_misura(righe: list[dict], intestazione: list[str]) -> list[str]:
    linee = [*intestazione, ""]
    linee += riepilogo_condizione(righe, "A")
    ristrette = [r for r in righe if r["ristretta_A"]]
    sempre = [int(r["di_sempre_A"]) for r in righe]
    linee += [
        (
            f"  avvolgi ha ristretto la ricerca: {len(ristrette)} volte, al documento "
            f"giusto {sum(r['ristretta_giusta_A'] == 'sì' for r in ristrette)}"
        ),
        *(
            f"    riga {r['riga']}: {r['ristretta_A']} "
            f"({'giusto' if r['ristretta_giusta_A'] == 'sì' else 'sbagliato'})"
            for r in ristrette
        ),
        (
            f"  frammenti dai documenti di sempre tra i primi 10: {sum(sempre)} su "
            f"{10 * len(righe)}; fatti con almeno uno: {sum(s > 0 for s in sempre)}"
        ),
        "",
    ]
    linee += riepilogo_condizione(righe, "B")
    gemelle = [r for r in righe if r["gemello"] == "sì" or r["riga"] in GRUPPI_FISSI[0]]
    linee.append("  frasi gemelle e gruppo della riga 23:")
    for r in gemelle:
        linee.append(
            f"    riga {r['riga']} ({r['id_bando']}): trovato {r['trovato_B']}, "
            f"posizioni {r['posizioni_pezzi_B']}, preso dal gemello "
            f"{r['pezzo_dal_gemello_B']}"
        )
    for c in ("A", "B"):
        mancati = [r for r in righe if r[f"trovato_{c}"] != "sì"]
        linee += ["", f"Non trovati in {c}: {len(mancati)}"]
        for r in mancati:
            linee.append(f"  riga {r['riga']} ({r['id_bando']}): {r[f'cause_{c}']}")
    return linee


def riga_misura(fatto: dict, giusti, a: dict, b: dict, nominati, di_sempre) -> dict:
    def testo_posizioni(pos):
        return " || ".join("-" if p is None else str(p) for p in pos)

    def sì_no(valore):
        return "sì" if valore else "no"

    riga = {
        "riga": fatto["riga"],
        "id_bando": fatto["id_bando"],
        "registro": str(fatto.get("registro") or "").strip(),
        "in_tabella": str(fatto.get("in_tabella") or "").strip(),
        "pezzi": len(unita_del_fatto(fatto)),
        "visti": fatto["visti"],
        "gemello": fatto["gemello"],
        "documenti_giusti": " | ".join(sorted(giusti)),
        "ristretta_A": " | ".join(sorted(nominati)),
        "ristretta_giusta_A": sì_no(nominati & giusti) if nominati else "",
        "di_sempre_A": di_sempre,
    }
    for c, esito in (("A", a), ("B", b)):
        riga.update(
            {
                f"trovato_{c}": sì_no(esito["trovato"]),
                f"primo_giusto_{c}": esito["primo_giusto"] or "",
                f"posizioni_pezzi_{c}": testo_posizioni(esito["posizioni_pezzi"]),
                f"cause_{c}": " / ".join(esito["cause"]),
                f"gemello_senza_giusto_{c}": sì_no(esito["gemello_senza_giusto"]),
                f"pezzo_dal_gemello_{c}": sì_no(esito["pezzo_dal_gemello"]),
            }
        )
    return riga


def esegui_misura(foglio: Path, divisione: Path, lato: str, cartella: Path) -> int:
    import shutil
    import time

    from scripts.ingestione.carica_avvisi import (
        SENZA_RETE,
        leggi_registro,
        senza_rete,
    )
    from scripts.ingestione.registra_avvisi import NOME_FILE
    from src.config import CHROMA_DIR, PROCESSED_DIR

    senza_rete()
    firma = verifica_impronta(divisione)
    fatti = fatti_della_meta(leggi_foglio(foglio), righe_della_meta(divisione, lato))
    file_per_bando: dict[str, list[dict]] = defaultdict(list)
    for r in leggi_registro(PROCESSED_DIR / NOME_FILE):
        file_per_bando[r["id_bandi"]].append(r)

    tempi = {}
    inizio = time.perf_counter()
    prima = impronte_cartella(CHROMA_DIR)
    copia = cartella / "chroma"
    if copia.exists():
        shutil.rmtree(copia)
    cartella.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CHROMA_DIR, copia)
    tempi["copia di Chroma"] = time.perf_counter() - inizio

    with senza_connessioni():
        from src.chains.rag import recupera
        from src.recupero_documenti import avvolgi, documenti_nominati
        from src.retrieval import normalizza_domanda

        inizio = time.perf_counter()
        recupero = apri_recupero(copia)
        app = avvolgi(recupero)
        profondo = avvolgi(Profondo(recupero))
        tempi["apertura del recupero (modello e BM25)"] = time.perf_counter() - inizio

        frammenti_per_fonte: dict[str, list[Frammento]] = defaultdict(list)
        for d in recupero.documenti:
            fonte, fr = frammento_di(d)
            frammenti_per_fonte[fonte].append(fr)
        for lista in frammenti_per_fonte.values():
            lista.sort(key=lambda fr: fr.chunk_num)

        inizio = time.perf_counter()
        righe = []
        for fatto in fatti:
            giusti, gemelli = documenti_del_fatto(fatto, file_per_bando)
            domanda = normalizza_domanda(str(fatto["domanda"]))
            risultati_a = recupera(app, fatto["domanda"], k=K)
            primi_a = [frammento_di(d) for d, _, _ in risultati_a]
            profondi_a = [
                frammento_di(d)
                for d, _, _ in recupera(profondo, fatto["domanda"], k=PROFONDITA)
            ]
            primi_b = [
                frammento_di(d)
                for d, _, _ in recupero.cerca_nel_bando(domanda, fatto["id_bando"], K)
            ]
            profondi_b = [
                frammento_di(d)
                for d, _, _ in recupero.cerca_nel_bando(
                    domanda, fatto["id_bando"], PROFONDITA, ampiezza=PROFONDITA
                )
            ]
            argomenti = (giusti, gemelli, frammenti_per_fonte)
            esito_a = valuta(fatto, primi_a, profondi_a, *argomenti)
            esito_b = valuta(fatto, primi_b, profondi_b, *argomenti)
            nominati = set(documenti_nominati(domanda, app.titoli))
            di_sempre = sum(not d.metadata.get("sha256") for d, _, _ in risultati_a)
            righe.append(
                riga_misura(fatto, giusti, esito_a, esito_b, nominati, di_sempre)
            )
        tempi[f"ricerche ({len(fatti)} fatti, 4 per fatto)"] = (
            time.perf_counter() - inizio
        )
        del recupero, app, profondo

    dopo = impronte_cartella(CHROMA_DIR)
    if dopo != prima:
        raise ErroreMisura(
            "le impronte del Chroma vero sono cambiate durante la misura"
        )

    intestazione = [
        f"Passo 19d, misura di partenza (v0), metà: {lato}",
        f"Divisione: {divisione.name} (sha256 {firma})",
        (
            f"k={K}; A: recupera(avvolgi(RecuperoIbrido)), ampiezza {AMPIEZZA_APP}; "
            f"B: RecuperoMisura.cerca_nel_bando, ampiezza {AMPIEZZA_APP}; "
            f"posizioni oltre i primi {K} con ampiezza {PROFONDITA}"
        ),
        f"Chroma vero: {len(prima)} file, impronte uguali prima e dopo; copia in {copia}",
        (
            "Variabili senza rete: "
            + ", ".join(f"{n}={v}" for n, v in SENZA_RETE.items())
            + "; connessioni di rete vietate durante la misura"
        ),
        "Tempi: " + "; ".join(f"{n} {s:.1f} s" for n, s in tempi.items()),
    ]
    testo = "\n".join(rapporto_misura(righe, intestazione)) + "\n"
    with (cartella / f"misura_{lato}.csv").open("w", encoding="utf-8", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=COLONNE_MISURA, lineterminator="\n")
        scrittore.writeheader()
        scrittore.writerows(righe)
    (cartella / f"rapporto_{lato}.txt").write_text(testo, encoding="utf-8")
    print(testo)
    return 0


# --- uso ---


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dividi", action="store_true", help="tempo 1: divisione")
    parser.add_argument("--misura", action="store_true", help="tempo 2: misura")
    parser.add_argument(
        "--controllo",
        action="store_true",
        help="misura la metà di controllo invece della taratura (solo su istruzione)",
    )
    parser.add_argument("--foglio", type=Path, default=FOGLIO)
    parser.add_argument("--csv-controllo", type=Path, default=CONTROLLO_CSV)
    parser.add_argument("--uscita", type=Path, default=DIVISIONE)
    parser.add_argument("--divisione", type=Path, default=DIVISIONE)
    parser.add_argument("--cartella", type=Path, default=V0)
    return parser.parse_args(argv)


def esegui_divisione(foglio: Path, controllo: Path, uscita: Path) -> int:
    fatti = leggi_foglio(foglio)
    dati_controllo = leggi_controllo(controllo)
    controlla_ingressi(fatti, dati_controllo, GRUPPI_FISSI)
    for f in fatti:
        f["visti"] = dati_controllo[f["riga"]]["visti"]
    gemelli = {r for r, d in dati_controllo.items() if d["gemello"]}
    meta, gruppo_di, tentativi = dividi(
        fatti, gemelli, fissi=GRUPPI_FISSI, condizioni=CONDIZIONI
    )
    righe = righe_divisione(fatti, meta, gruppo_di, gemelli)
    dati = testo_csv(righe)

    print(f"Foglio: {foglio.name} (sha256 {impronta(foglio.read_bytes())})")
    print("\n".join(rapporto(righe, SEME, tentativi)))
    print()

    if uscita.exists():
        uguale = uscita.read_bytes() == dati
        print(
            f"{uscita.name} esiste già e non si sovrascrive: "
            + (
                "la divisione rifatta coincide."
                if uguale
                else "la divisione rifatta È DIVERSA."
            )
        )
        return 0 if uguale else 1

    uscita.parent.mkdir(parents=True, exist_ok=True)
    uscita.write_bytes(dati)
    firma = impronta(dati)
    Path(f"{uscita}.sha256").write_text(f"{firma}  {uscita.name}\n", encoding="utf-8")
    print(f"Scritto {uscita} (sha256 {firma})")
    return 0


def main(argv: list[str] | None = None) -> int:
    argomenti = leggi_argomenti(argv)
    if argomenti.dividi == argomenti.misura:
        print("Serve un comando solo: --dividi o --misura.", file=sys.stderr)
        return 2
    try:
        if argomenti.dividi:
            return esegui_divisione(
                argomenti.foglio, argomenti.csv_controllo, argomenti.uscita
            )
        lato = CONTROLLO if argomenti.controllo else TARATURA
        return esegui_misura(
            argomenti.foglio, argomenti.divisione, lato, argomenti.cartella
        )
    except (ErroreDivisione, ErroreMisura) as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
