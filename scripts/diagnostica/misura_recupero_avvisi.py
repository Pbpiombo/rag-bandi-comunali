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
import re
import sys
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
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
CARTELLA_19D = DATI_GREZZI_DIR / "prova" / "19d"


@dataclass(frozen=True)
class Variante:
    """Una configurazione del recupero da misurare.

    limite: token del modello di embedding (None: quello del modello, 128);
    intestazione: titolo · parte · atto davanti al testo su cui si calcola
    il vettore dei frammenti degli avvisi (il testo del frammento resta
    pulito, e la ricerca per parole non la vede);
    frammenti: (dimensione, sovrapposizione) in caratteri per la divisione
    degli avvisi (None: quella del caricamento, src/config.py).
    I documenti di sempre restano con i loro frammenti e senza intestazione;
    i loro vettori si ricalcolano con il limite della variante.
    """

    limite: int | None = None
    intestazione: bool = False
    frammenti: tuple[int, int] | None = None

    def descrizione(self) -> str:
        parti = [f"limite {self.limite or LIMITE_MODELLO} token"]
        parti.append(
            "intestazione nel vettore" if self.intestazione else "senza intestazione"
        )
        parti.append(
            f"frammenti degli avvisi da {self.frammenti[0]} caratteri con "
            f"{self.frammenti[1]} di sovrapposizione"
            if self.frammenti
            else "frammenti del caricamento"
        )
        return "; ".join(parti)


LIMITE_MODELLO = 128
CORTI = (600, 200)
VARIANTI: dict[str, Variante] = {
    "v0": Variante(),
    "v1": Variante(limite=512),
    "v2": Variante(intestazione=True),
    "v3": Variante(frammenti=CORTI),
    "v1+v2": Variante(limite=512, intestazione=True),
    "v1+v2+v3": Variante(limite=512, intestazione=True, frammenti=CORTI),
}

NOTA_REGOLA = (
    "Regola corretta il 20/11/2026, prima di aprire il controllo: tutte le "
    "varianti e le combinazioni si scelgono sulla taratura; il controllo si "
    "apre una volta sola, sulla scelta finale. Il ramo 'tra 75 e 85% si "
    "prova una combinazione e si rimisura' è annullato."
)

# Condizioni della misura.
# A: il percorso dell'app.
# Bi: filtro sul bando, domanda intera (la definizione di B della prima
#     misura di taratura, 20/11/2026).
# B: filtro sul bando, domanda ripulita con ripulisci_domanda e le parole
#    del titolo del bando del fatto (definizione cambiata dopo la prima
#    misura di taratura, decisione del 20/11/2026: l'app, quando riconosce
#    il documento, cerca con la domanda ripulita). Dove non c'è un tratto
#    che nomina il bando la domanda resta intera; la punteggiatura rimasta
#    orfana resta, come nell'app.
CONDIZIONI_MISURA = ("A", "Bi", "B")

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

# Classi delle restrizioni di avvolgi
RISTRETTA_GIUSTO = "giusto"
RISTRETTA_GEMELLO = "giusto + gemello"
RISTRETTA_ALTRO = "giusto + altro"
RISTRETTA_SBAGLIATO = "sbagliato"

_PER_CONDIZIONE = [
    "trovato",
    "primo_giusto",
    "posizioni_pezzi",
    "posizioni_profonde",
    "cause",
    "gemello_senza_giusto",
    "pezzo_dal_gemello",
]
COLONNE_MISURA = [
    "riga",
    "id_bando",
    "registro",
    "in_tabella",
    "pezzi",
    "visti",
    "gemello",
    "documenti_giusti",
    "domanda_B",
    "ristretta_A",
    "classe_ristretta_A",
    "di_sempre_A",
    "pezzi_spezzati",
    "pezzi_assenti",
    *(f"{c}_{n}" for c in CONDIZIONI_MISURA for n in _PER_CONDIZIONE),
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
        "posizioni_profonde": [prima_posizione(p, profondi, giusti) for p in unita],
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


def apri_recupero(
    copia: Path,
    limite: int | None = None,
    prefissi: dict[str, str] | None = None,
    store=None,
):
    """RecuperoMisura sulla copia di Chroma: RecuperoIbrido più la ricerca per bando.

    Con `limite`, il modello di embedding delle domande usa quel limite di
    token (lo stesso con cui sono stati calcolati i vettori della copia).
    Con `prefissi` (testo per nome del file), la ricerca per parole indicizza
    il prefisso davanti al testo dei frammenti di quei file; il testo dei
    frammenti restituiti resta quello della copia.
    Con `store` (per esempio StoreEsatto) si usa quello e `copia` non conta.
    """
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
            self.bm25 = BM25Okapi(
                [
                    tokenizza(testo_lessicale(d.page_content, d.metadata, prefissi))
                    for d in self.documenti
                ]
            )

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

    if store is None:
        embeddings = crea_embeddings()
        if limite:
            embeddings._client.max_seq_length = limite
        store = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(copia),
            collection_metadata={"hnsw:space": "cosine"},
        )
    return RecuperoMisura(store)


def testo_lessicale(testo: str, meta: dict, prefissi: dict[str, str] | None) -> str:
    """Il testo con il prefisso del suo file davanti, se c'è.

    Serve alla ricerca per parole (apri_recupero) e al vettore
    (prepara_copia_parte); il testo del frammento resta quello della copia.
    """
    prefisso = (prefissi or {}).get(meta.get("fonte") or "")
    return f"{prefisso}\n{testo}" if prefisso else testo


class ConAmpiezza:
    """Il recupero con un'ampiezza data, da avvolgere come quello dell'app."""

    def __init__(self, base, ampiezza: int) -> None:
        self.base = base
        self.ampiezza = ampiezza

    def titoli(self) -> dict[str, str]:
        return self.base.titoli()

    def cerca(self, domanda: str, k: int = 8, fonte: str | None = None) -> list:
        return self.base.cerca(domanda, k=k, ampiezza=self.ampiezza, fonte=fonte)


class Profondo(ConAmpiezza):
    """Il recupero con ampiezza PROFONDITA."""

    def __init__(self, base) -> None:
        super().__init__(base, PROFONDITA)


# --- restrizioni, domanda ripulita, parte vista ---


def classe_restrizione(nominati: set[str], giusti: set[str], gemelli: set[str]) -> str:
    """Giusto, giusto + gemello, giusto + altro o sbagliato; vuota se nessuna."""
    if not nominati:
        return ""
    if not nominati & giusti:
        return RISTRETTA_SBAGLIATO
    altri = nominati - giusti
    if not altri:
        return RISTRETTA_GIUSTO
    return RISTRETTA_GEMELLO if altri <= gemelli else RISTRETTA_ALTRO


def domanda_ripulita(domanda: str, titolo: str) -> str:
    """La domanda senza il tratto che nomina il bando, con la funzione di avvolgi."""
    from src.recupero_documenti import parole_titolo, ripulisci_domanda

    return ripulisci_domanda(domanda, parole_titolo(titolo))


def car_visti(tokenizer, testo: str, limite: int) -> int:
    """I caratteri del frammento che il modello vede con `limite` token ([CLS] e [SEP] compresi)."""
    codifica = tokenizer(testo, return_offsets_mapping=True)
    if len(codifica["input_ids"]) <= limite:
        return len(testo)
    return codifica["offset_mapping"][limite - 2][1]


# --- copie di Chroma ---


def intestazione_di(meta: dict) -> str:
    """Titolo · parte · atto di un frammento degli avvisi, senza le voci vuote."""
    voci = (meta.get("titolo"), meta.get("parte"), meta.get("riferimento_atto"))
    return " · ".join(str(v).strip() for v in voci if v and str(v).strip())


def testo_per_vettore(testo: str, meta: dict, intestazione: bool) -> str:
    """Il testo su cui si calcola il vettore: con l'intestazione solo per gli avvisi."""
    if intestazione and meta.get("sha256"):
        return f"{intestazione_di(meta)}\n{testo}"
    return testo


def _senza_vuoti(meta: dict) -> dict:
    return {k: v for k, v in meta.items() if v is not None}


def impronta_frammenti(ids: list[str], testi: list[str], metadati: list[dict]) -> str:
    """sha256 di ids, testi e metadati, indipendente dall'ordine."""
    import json

    voci = sorted(
        [i, testo, sorted(_senza_vuoti(meta).items())]
        for i, testo, meta in zip(ids, testi, metadati, strict=True)
    )
    return impronta(json.dumps(voci, ensure_ascii=False).encode("utf-8"))


@contextmanager
def dimensione_dei_frammenti(modulo, frammenti: tuple[int, int] | None):
    """Durante il blocco, `modulo.spezza` divide con la dimensione data."""
    if frammenti is None:
        yield
        return
    import functools

    originale = modulo.spezza
    modulo.spezza = functools.partial(
        originale, dimensione=frammenti[0], sovrapposizione=frammenti[1]
    )
    try:
        yield
    finally:
        modulo.spezza = originale


def frammenti_avvisi(frammenti: tuple[int, int] | None) -> list:
    """I frammenti degli avvisi come li fa il caricamento, con la divisione data.

    Si usa scripts.ingestione.carica_avvisi.frammenti_del_file su tutte le
    righe del registro con uso "frammenti"; nulla si scrive.
    """
    from scripts.ingestione import carica_avvisi as ca
    from scripts.ingestione.registra_avvisi import NOME_FILE
    from src.config import PROCESSED_DIR
    from src.database.schema import connetti

    conn = connetti()
    try:
        tokenizer = ca.apri_tokenizer()
        uscita = []
        with dimensione_dei_frammenti(ca, frammenti):
            for riga in ca.leggi_registro(PROCESSED_DIR / NOME_FILE):
                pagine = ca.pagine_del_pdf(ca.percorso_del_file(riga))
                uscita += ca.frammenti_del_file(riga, pagine, conn, tokenizer).frammenti
    finally:
        conn.close()
    return uscita


def prepara_copia(cartella: Path, variante: Variante | None, sorgente: Path) -> dict:
    """Copia di Chroma nella cartella, trasformata secondo la variante.

    v0 (o None): copia e basta. Altrimenti si ricalcolano i vettori di tutti
    i frammenti con il limite della variante (e l'intestazione per gli
    avvisi); con `frammenti`, gli avvisi si ridividono: prima si controlla
    che la divisione del caricamento ridia esattamente i frammenti della
    copia (numero e impronta), poi si tolgono e si mettono i nuovi.
    Controllo dei vettori: i frammenti con lo stesso testo, senza
    intestazione ed entro il limite di prima devono avere lo stesso vettore.
    """
    import shutil

    variante = variante or Variante()
    copia = cartella / "chroma"
    if copia.exists():
        shutil.rmtree(copia)
    cartella.mkdir(parents=True, exist_ok=True)
    shutil.copytree(sorgente, copia)
    if variante == Variante():
        return {}

    import chromadb
    import numpy as np
    from chromadb.config import Settings

    from scripts.ingestione.carica_avvisi import identificatori
    from src.config import COLLECTION_NAME
    from src.vectorstore import crea_embeddings

    embeddings = crea_embeddings()
    limite = variante.limite or LIMITE_MODELLO
    embeddings._client.max_seq_length = limite
    tokenizer = embeddings._client.tokenizer
    cliente = chromadb.PersistentClient(
        path=str(copia), settings=Settings(anonymized_telemetry=False)
    )
    collezione = cliente.get_collection(COLLECTION_NAME)
    dati = collezione.get(include=["documents", "metadatas", "embeddings"])
    vecchi = {
        i: (testo, vettore)
        for i, testo, vettore in zip(
            dati["ids"], dati["documents"], dati["embeddings"], strict=True
        )
    }
    info: dict = {}
    ids, testi, metadati = dati["ids"], dati["documents"], dati["metadatas"]
    if variante.frammenti:
        avvisi = [k for k, m in enumerate(metadati) if m.get("sha256")]
        predefiniti = frammenti_avvisi(None)
        attesa = impronta_frammenti(
            [ids[k] for k in avvisi],
            [testi[k] for k in avvisi],
            [metadati[k] for k in avvisi],
        )
        rifatta = impronta_frammenti(
            identificatori(predefiniti),
            [d.page_content for d in predefiniti],
            [d.metadata for d in predefiniti],
        )
        info["ricostruzione"] = (len(predefiniti), len(avvisi), rifatta == attesa)
        if len(predefiniti) != len(avvisi) or rifatta != attesa:
            raise ErroreMisura(
                f"la divisione del caricamento non ridà i frammenti della copia: "
                f"{len(predefiniti)} contro {len(avvisi)}, impronte "
                f"{rifatta[:12]} e {attesa[:12]}"
            )
        info["impronta_avvisi"] = attesa
        nuovi = frammenti_avvisi(variante.frammenti)
        tolti = {ids[k] for k in avvisi}
        collezione.delete(ids=sorted(tolti))
        # i nuovi frammenti possono avere gli stessi id di quelli tolti
        # (sha256[:16]::n): non sono più nella collezione e vanno aggiunti
        vecchi = {i: v for i, v in vecchi.items() if i not in tolti}
        tenuti = [k for k in range(len(ids)) if k not in set(avvisi)]
        ids = [ids[k] for k in tenuti] + identificatori(nuovi)
        testi = [testi[k] for k in tenuti] + [d.page_content for d in nuovi]
        metadati = [metadati[k] for k in tenuti] + [
            _senza_vuoti(d.metadata) for d in nuovi
        ]
        info["avvisi"] = len(nuovi)
    vettori = embeddings.embed_documents(
        [
            testo_per_vettore(testo, meta, variante.intestazione)
            for testo, meta in zip(testi, metadati, strict=True)
        ]
    )
    for a in range(0, len(ids), 500):
        b = a + 500
        presenti = [k for k in range(a, min(b, len(ids))) if ids[k] in vecchi]
        assenti = [k for k in range(a, min(b, len(ids))) if ids[k] not in vecchi]
        if presenti:
            collezione.update(
                ids=[ids[k] for k in presenti],
                embeddings=[vettori[k] for k in presenti],
            )
        if assenti:
            collezione.add(
                ids=[ids[k] for k in assenti],
                embeddings=[vettori[k] for k in assenti],
                documents=[testi[k] for k in assenti],
                metadatas=[metadati[k] for k in assenti],
            )
    confrontabili = [
        k
        for k, i in enumerate(ids)
        if i in vecchi
        and vecchi[i][0] == testi[k]
        and testo_per_vettore(testi[k], metadati[k], variante.intestazione) == testi[k]
        and len(tokenizer(testi[k])["input_ids"]) <= LIMITE_MODELLO
    ]
    coseni = [
        float(np.dot(np.asarray(vecchi[ids[k]][1]), np.asarray(vettori[k])))
        for k in confrontabili
    ]
    nella_copia = collezione.get(include=[])["ids"]
    if sorted(nella_copia) != sorted(ids):
        raise ErroreMisura(
            f"la copia ha {len(nella_copia)} frammenti, attesi {len(ids)}"
        )
    del cliente
    info.update(
        frammenti=len(ids),
        confrontabili=len(confrontabili),
        coseno_minimo=min(coseni) if coseni else None,
    )
    return info


def stato_dei_pezzi(
    fatto: dict, giusti: set[str], frammenti_per_fonte: dict[str, list[Frammento]]
) -> tuple[int, int, int]:
    """(interi, spezzati, assenti): i pezzi del fatto nei frammenti dei documenti giusti."""
    interi = spezzati_ = assenti = 0
    for pezzo in unita_del_fatto(fatto):
        frammenti = [
            fr for f in sorted(giusti) for fr in frammenti_per_fonte.get(f, [])
        ]
        if any(contiene(pezzo, fr) for fr in frammenti):
            interi += 1
        elif any(
            spezzato(pezzo, frammenti_per_fonte.get(f, [])) for f in sorted(giusti)
        ):
            spezzati_ += 1
        else:
            assenti += 1
    return interi, spezzati_, assenti


# --- numeri ---


def _quota(parte: int, tutto: int) -> str:
    return f"{parte}/{tutto}" + (f" ({100 * parte / tutto:.1f}%)" if tutto else "")


GRUPPI_DEI_FATTI = [
    ("registro semplice", lambda r: r["registro"] == "semplice"),
    ("registro caso", lambda r: r["registro"] == "caso"),
    ("tabella sì", lambda r: r["in_tabella"] == "sì"),
    ("tabella no", lambda r: r["in_tabella"] != "sì"),
    ("tutti i pezzi visti (128 token)", lambda r: r["visti"] == "sì"),
    ("non tutti visti (128 token)", lambda r: r["visti"] != "sì"),
    ("risposta in un pezzo", lambda r: int(r["pezzi"]) == 1),
    ("risposta in più pezzi", lambda r: int(r["pezzi"]) > 1),
]


def numeri(righe: list[dict], c: str) -> list[tuple[str, str]]:
    """Le misure di una condizione, come (etichetta, valore)."""
    trovato = [r for r in righe if r[f"{c}_trovato"] == "sì"]
    valori = [("trovati", _quota(len(trovato), len(righe)))]
    for nome, scelta in GRUPPI_DEI_FATTI:
        sue = [r for r in righe if scelta(r)]
        valori.append(
            (nome, _quota(sum(r[f"{c}_trovato"] == "sì" for r in sue), len(sue)))
        )
    primi = [int(r[f"{c}_primo_giusto"]) for r in righe if r[f"{c}_primo_giusto"]]
    valori += [
        ("primo giusto al 1° posto", str(sum(p == 1 for p in primi))),
        ("primo giusto tra i primi 3", str(sum(p <= 3 for p in primi))),
        ("primo giusto tra i primi 5", str(sum(p <= 5 for p in primi))),
        ("primo giusto tra i primi 10", str(len(primi))),
        ("nessun giusto tra i primi 10", str(len(righe) - len(primi))),
        (
            "gemello tra i primi 10, giusto assente",
            str(sum(r[f"{c}_gemello_senza_giusto"] == "sì" for r in righe)),
        ),
        (
            "pezzo preso dal gemello",
            str(sum(r[f"{c}_pezzo_dal_gemello"] == "sì" for r in righe)),
        ),
    ]
    return valori


def tabella_affiancata(colonne: list[tuple[str, list[dict], str]]) -> list[str]:
    """Le misure di più (titolo, righe, condizione) una accanto all'altra."""
    tabelle = [numeri(righe, c) for _, righe, c in colonne]
    larghezza = max(len(e) for e, _ in tabelle[0]) + 2
    linee = [" " * larghezza + "".join(f"{t:>20}" for t, _, _ in colonne)]
    for i, (etichetta, _) in enumerate(tabelle[0]):
        linee.append(
            f"{etichetta:<{larghezza}}" + "".join(f"{t[i][1]:>20}" for t in tabelle)
        )
    return linee


def righe_restrizioni(righe: list[dict]) -> list[str]:
    ristrette = [r for r in righe if r["ristretta_A"]]
    classi = Counter(r["classe_ristretta_A"] for r in ristrette)
    linee = [
        f"avvolgi ha ristretto la ricerca {len(ristrette)} volte: "
        + ", ".join(f"{k} {v}" for k, v in sorted(classi.items()))
    ]
    linee += [
        f"  riga {r['riga']}: {r['classe_ristretta_A']} ({r['ristretta_A']})"
        for r in ristrette
    ]
    sempre = [int(r["di_sempre_A"]) for r in righe]
    linee.append(
        f"frammenti dai documenti di sempre tra i primi 10 (A): {sum(sempre)} su "
        f"{K * len(righe)}; fatti con almeno uno: {sum(s > 0 for s in sempre)}"
    )
    return linee


def righe_gemelle(righe: list[dict], c: str) -> list[str]:
    gemelle = [r for r in righe if r["gemello"] == "sì" or int(r["riga"]) == 23]
    return [
        f"  riga {r['riga']} ({r['id_bando']}): trovato {r[f'{c}_trovato']}, "
        f"posizioni {r[f'{c}_posizioni_pezzi']}, preso dal gemello "
        f"{r[f'{c}_pezzo_dal_gemello']}"
        for r in gemelle
    ]


def rapporto_misura(righe: list[dict], intestazione: list[str]) -> list[str]:
    linee = [*intestazione, ""]
    linee += tabella_affiancata([(c, righe, c) for c in CONDIZIONI_MISURA])
    linee += ["", *righe_restrizioni(righe), ""]
    for c in ("Bi", "B"):
        linee += [f"Frasi gemelle e riga 23, condizione {c}:", *righe_gemelle(righe, c)]
    linee += ["", "Domande cambiate dalla pulizia di B:"]
    linee += [f"  riga {r['riga']}: {r['domanda_B']}" for r in righe if r["domanda_B"]]
    for c in CONDIZIONI_MISURA:
        mancati = [r for r in righe if r[f"{c}_trovato"] != "sì"]
        linee += ["", f"Non trovati in {c}: {len(mancati)}"]
        linee += [
            f"  riga {r['riga']} ({r['id_bando']}): {r[f'{c}_cause']}" for r in mancati
        ]
    return linee


def _posizioni(pos) -> str:
    return " || ".join("-" if p is None else str(p) for p in pos)


def riga_misura(
    fatto: dict,
    giusti: set[str],
    gemelli: set[str],
    esiti: dict[str, dict],
    nominati: set[str],
    di_sempre: int,
    domanda_b: str,
) -> dict:
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
        "domanda_B": domanda_b,
        "ristretta_A": " | ".join(sorted(nominati)),
        "classe_ristretta_A": classe_restrizione(nominati, giusti, gemelli),
        "di_sempre_A": di_sempre,
    }
    for c, esito in esiti.items():
        riga.update(
            {
                f"{c}_trovato": sì_no(esito["trovato"]),
                f"{c}_primo_giusto": esito["primo_giusto"] or "",
                f"{c}_posizioni_pezzi": _posizioni(esito["posizioni_pezzi"]),
                f"{c}_posizioni_profonde": _posizioni(esito["posizioni_profonde"]),
                f"{c}_cause": " / ".join(esito["cause"]),
                f"{c}_gemello_senza_giusto": sì_no(esito["gemello_senza_giusto"]),
                f"{c}_pezzo_dal_gemello": sì_no(esito["pezzo_dal_gemello"]),
            }
        )
    return riga


# --- confronto tra varianti ---


def cambi_di_esito(
    base: list[dict], variante: list[dict], c: str
) -> tuple[list[str], list[str]]:
    """(guadagnati, persi) passando dalla base alla variante, come numeri di riga."""
    prima = {r["riga"]: r[f"{c}_trovato"] == "sì" for r in base}
    dopo = {r["riga"]: r[f"{c}_trovato"] == "sì" for r in variante}
    if set(prima) != set(dopo):
        raise ErroreMisura("le due misure non hanno gli stessi fatti")
    ordine = sorted(prima, key=int)
    return (
        [r for r in ordine if dopo[r] and not prima[r]],
        [r for r in ordine if prima[r] and not dopo[r]],
    )


def pezzi_affiancati(
    misure: list[tuple[str, list[dict]]], condizioni: tuple[str, ...] = ("A", "B")
) -> list[str]:
    """Per le risposte in più pezzi: posizione di ogni pezzo, nei primi 10 e profonda."""

    def cella(r: dict, c: str, i: int) -> str:
        primi = r[f"{c}_posizioni_pezzi"].split(" || ")[i]
        profonda = r[f"{c}_posizioni_profonde"].split(" || ")[i]
        return f"{primi} ({'>' + str(PROFONDITA) if profonda == '-' else profonda})"

    titoli = [f"{n} {c}" for n, _ in misure for c in condizioni]
    linee = [f"{'riga':<6}{'pezzo':<7}" + "".join(f"{t:>12}" for t in titoli)]
    per_riga = [{r["riga"]: r for r in righe} for _, righe in misure]
    for numero in sorted(per_riga[0], key=int):
        prima = per_riga[0][numero]
        for i in range(int(prima["pezzi"])):
            if int(prima["pezzi"]) < 2:
                break
            celle = [
                cella(righe[numero], c, i) for righe in per_riga for c in condizioni
            ]
            linee.append(f"{numero:<6}{i + 1:<7}" + "".join(f"{x:>12}" for x in celle))
    return linee


def leggi_misura(percorso: Path) -> list[dict]:
    with percorso.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def rapporto_confronto(misure: list[tuple[str, list[dict]]]) -> list[str]:
    """Confronto di più misure; la prima è la base (v0), l'ultima la variante."""
    base_nome, base = misure[0]
    nome, variante = misure[-1]
    colonne = [
        (f"{n} {etichetta}", righe, c)
        for n, righe in misure
        for etichetta, c in (("A", "A"), ("B", "B"))
    ]
    linee = [
        f"Confronto {', '.join(n for n, _ in misure)}, metà di taratura",
        NOTA_REGOLA,
        "",
    ]
    linee += tabella_affiancata(colonne)
    for c in ("A", "B"):
        guadagnati, persi = cambi_di_esito(base, variante, c)
        linee += [
            "",
            (
                f"Condizione {c}, da {base_nome} a {nome}, fatti che cambiano "
                f"esito: ora trovati {len(guadagnati)} "
                f"({', '.join(guadagnati) or '-'}); ora non trovati "
                f"{len(persi)} ({', '.join(persi) or '-'})"
            ),
        ]
    linee += [
        "",
        "Con 40 fatti e uno strumento che oscillava di un fatto, scarti di 1-3",
        "fatti sono entro il rumore (istruzione del 20/11/2026, quarto giro).",
    ]
    linee += [
        "",
        "Risposte in più pezzi: posizione del frammento giusto per pezzo, nei",
        f"primi 10 ('-' se assente) e tra parentesi con ampiezza {PROFONDITA}:",
        *pezzi_affiancati(misure),
    ]
    return linee


RIGHE_SEGUITE = (21, 23, 24, 72, 74)


def esegui_riepilogo(lato: str) -> int:
    """Una riga per configurazione misurata, più le frasi gemelle seguite."""
    misure = [
        (nome, leggi_misura(CARTELLA_19D / nome / f"misura_{lato}.csv"))
        for nome in VARIANTI
        if (CARTELLA_19D / nome / f"misura_{lato}.csv").exists()
    ]
    if not misure:
        raise ErroreMisura("nessuna misura da riassumere")

    def conta(righe, c, scelta=lambda r: True):
        sue = [r for r in righe if scelta(r)]
        return f"{sum(r[f'{c}_trovato'] == 'sì' for r in sue)}/{len(sue)}"

    def primi5(righe, c):
        return str(
            sum(
                bool(r[f"{c}_primo_giusto"]) and int(r[f"{c}_primo_giusto"]) <= 5
                for r in righe
            )
        )

    titoli = [
        "trovati A",
        "trovati B",
        "un pezzo A",
        "un pezzo B",
        "più pezzi A",
        "più pezzi B",
        "primo<=5 A",
        "primo<=5 B",
    ]
    linee = [f"Riepilogo del passo 19d, metà: {lato}", NOTA_REGOLA, ""]
    linee.append(f"{'':<10}" + "".join(f"{x:>13}" for x in titoli))
    for nome, righe in misure:

        def uno(r):
            return int(r["pezzi"]) == 1

        def piu(r):
            return int(r["pezzi"]) > 1

        valori = [
            conta(righe, "A"),
            conta(righe, "B"),
            conta(righe, "A", uno),
            conta(righe, "B", uno),
            conta(righe, "A", piu),
            conta(righe, "B", piu),
            primi5(righe, "A"),
            primi5(righe, "B"),
        ]
        linee.append(f"{nome:<10}" + "".join(f"{x:>13}" for x in valori))
    linee += [
        "",
        "Frasi gemelle seguite: posizione del frammento giusto per pezzo, nei",
        f"primi 10 e tra parentesi con ampiezza {PROFONDITA}",
    ]
    for nome, righe in misure:
        per_riga = {int(r["riga"]): r for r in righe}
        celle = []
        for numero in RIGHE_SEGUITE:
            if numero not in per_riga:
                continue
            r = per_riga[numero]
            for c in ("A", "B"):
                celle.append(
                    f"{numero}{c} {r[f'{c}_posizioni_pezzi']} "
                    f"({r[f'{c}_posizioni_profonde']})"
                )
        linee.append(f"  {nome:<9} " + "; ".join(celle))
    testo = "\n".join(linee)
    (CARTELLA_19D / f"riepilogo_{lato}.txt").write_text(testo + "\n", encoding="utf-8")
    print(testo)
    return 0


def esegui_misura(
    foglio: Path, divisione: Path, lato: str, variante: str, cartella: Path
) -> int:
    import time

    from scripts.ingestione.carica_avvisi import (
        SENZA_RETE,
        leggi_registro,
        senza_rete,
    )
    from scripts.ingestione.registra_avvisi import NOME_FILE
    from src.config import CHROMA_DIR, PROCESSED_DIR

    senza_rete()
    configurazione = VARIANTI[variante]
    limite = configurazione.limite
    firma = verifica_impronta(divisione)
    fatti = fatti_della_meta(leggi_foglio(foglio), righe_della_meta(divisione, lato))
    file_per_bando: dict[str, list[dict]] = defaultdict(list)
    for r in leggi_registro(PROCESSED_DIR / NOME_FILE):
        file_per_bando[r["id_bandi"]].append(r)

    tempi = {}
    prima = impronte_cartella(CHROMA_DIR)
    with senza_connessioni():
        inizio = time.perf_counter()
        ricalcolo = prepara_copia(cartella, configurazione, CHROMA_DIR)
        tempi["copia di Chroma" + (" e vettori ricalcolati" if ricalcolo else "")] = (
            time.perf_counter() - inizio
        )
        dopo = impronte_cartella(CHROMA_DIR)
        if dopo != prima:
            raise ErroreMisura("le impronte del Chroma vero sono cambiate")

        from src.chains.rag import recupera
        from src.recupero_documenti import avvolgi, documenti_nominati
        from src.retrieval import normalizza_domanda

        inizio = time.perf_counter()
        recupero = apri_recupero(cartella / "chroma", limite)
        app = avvolgi(recupero)
        profondo = avvolgi(Profondo(recupero))
        tempi["apertura del recupero (modello e BM25)"] = time.perf_counter() - inizio

        tokenizer = recupero.store.embeddings._client.tokenizer
        titolo_del_bando = {}
        frammenti_per_fonte: dict[str, list[Frammento]] = defaultdict(list)
        for d in recupero.documenti:
            fonte, fr = frammento_di(d)
            if limite:
                fr.car_visti = car_visti(tokenizer, fr.testo, limite)
            frammenti_per_fonte[fonte].append(fr)
            if d.metadata.get("id_bando"):
                titolo_del_bando[d.metadata["id_bando"]] = d.metadata["titolo"]
        for lista in frammenti_per_fonte.values():
            lista.sort(key=lambda fr: fr.chunk_num)

        inizio = time.perf_counter()
        righe = []
        for fatto in fatti:
            giusti, gemelli = documenti_del_fatto(fatto, file_per_bando)
            domanda = normalizza_domanda(str(fatto["domanda"]))
            ripulita = domanda_ripulita(domanda, titolo_del_bando[fatto["id_bando"]])
            risultati_a = recupera(app, fatto["domanda"], k=K)
            elenchi = {
                "A": (
                    risultati_a,
                    recupera(profondo, fatto["domanda"], k=PROFONDITA),
                ),
            }
            for c, testo in (("Bi", domanda), ("B", ripulita)):
                elenchi[c] = (
                    recupero.cerca_nel_bando(testo, fatto["id_bando"], K),
                    recupero.cerca_nel_bando(
                        testo, fatto["id_bando"], PROFONDITA, ampiezza=PROFONDITA
                    ),
                )
            esiti = {
                c: valuta(
                    fatto,
                    [frammento_di(d) for d, _, _ in primi],
                    [frammento_di(d) for d, _, _ in profondi],
                    giusti,
                    gemelli,
                    frammenti_per_fonte,
                )
                for c, (primi, profondi) in elenchi.items()
            }
            nominati = set(documenti_nominati(domanda, app.titoli))
            _, spezzati_, assenti = stato_dei_pezzi(fatto, giusti, frammenti_per_fonte)
            di_sempre = sum(not d.metadata.get("sha256") for d, _, _ in risultati_a)
            righe.append(
                riga_misura(
                    fatto,
                    giusti,
                    gemelli,
                    esiti,
                    nominati,
                    di_sempre,
                    ripulita if ripulita != domanda else "",
                )
            )
            righe[-1].update(pezzi_spezzati=spezzati_, pezzi_assenti=assenti)
        tempi[f"ricerche ({len(fatti)} fatti, 6 per fatto)"] = (
            time.perf_counter() - inizio
        )
        del recupero, app, profondo

    dopo = impronte_cartella(CHROMA_DIR)
    if dopo != prima:
        raise ErroreMisura("le impronte del Chroma vero sono cambiate")

    intestazione = [
        f"Passo 19d, misura {variante}, metà: {lato}",
        f"Divisione: {divisione.name} (sha256 {firma})",
        NOTA_REGOLA,
        f"Configurazione: {configurazione.descrizione()}",
        (
            (
                f"Vettori ricalcolati per {ricalcolo['frammenti']} frammenti"
                + (
                    f", di cui {ricalcolo['avvisi']} degli avvisi ridivisi"
                    if "avvisi" in ricalcolo
                    else ""
                )
                + (
                    "; controllo della divisione: il caricamento ridà "
                    f"{ricalcolo['ricostruzione'][0]} frammenti contro "
                    f"{ricalcolo['ricostruzione'][1]} della copia, impronta "
                    f"{ricalcolo['impronta_avvisi'][:16]} uguale"
                    if "ricostruzione" in ricalcolo
                    else ""
                )
                + (
                    f"; controllo dei vettori: {ricalcolo['confrontabili']} "
                    "frammenti con lo stesso testo, senza intestazione ed entro "
                    f"{LIMITE_MODELLO} token, coseno minimo con il vettore di "
                    f"prima {ricalcolo['coseno_minimo']:.6f}"
                    if ricalcolo.get("coseno_minimo") is not None
                    else ""
                )
            )
            if ricalcolo
            else "Copia senza modifiche"
        ),
        (
            f"k={K}; A: recupera(avvolgi(RecuperoIbrido)), ampiezza {AMPIEZZA_APP}; "
            f"Bi e B: RecuperoMisura.cerca_nel_bando, ampiezza {AMPIEZZA_APP}; "
            f"posizioni oltre i primi {K} con ampiezza {PROFONDITA}"
        ),
        (
            "B: la definizione è cambiata dopo la prima misura di taratura "
            "(20/11/2026). Bi è la definizione della prima misura (domanda "
            "intera); B usa la domanda ripulita con ripulisci_domanda e le "
            "parole del titolo del bando del fatto."
        ),
        (
            "Parte vista per le cause: "
            + (
                f"ricalcolata con {limite} token"
                if limite
                else f"car_visti dei metadati ({LIMITE_MODELLO} token)"
            )
            + f"; i gruppi 'visti' sono quelli della divisione ({LIMITE_MODELLO} token)"
        ),
        (
            f"Chroma vero: {len(prima)} file, impronte uguali prima e dopo; "
            f"copia in {cartella / 'chroma'}"
        ),
        (
            "Variabili senza rete: "
            + ", ".join(f"{n}={v}" for n, v in SENZA_RETE.items())
            + "; connessioni di rete vietate durante la misura"
        ),
        "Tempi: " + "; ".join(f"{n} {s:.1f} s" for n, s in tempi.items()),
    ]
    spezzati_tot = sum(int(r["pezzi_spezzati"]) for r in righe)
    assenti_tot = sum(int(r["pezzi_assenti"]) for r in righe)
    pezzi_tot = sum(int(r["pezzi"]) for r in righe)
    intestazione.append(
        f"Pezzi di {lato} nei frammenti dei documenti giusti: {pezzi_tot}, di cui "
        f"spezzati tra due frammenti {spezzati_tot}, in nessun frammento {assenti_tot}"
    )
    with (cartella / f"misura_{lato}.csv").open("w", encoding="utf-8", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=COLONNE_MISURA, lineterminator="\n")
        scrittore.writeheader()
        scrittore.writerows(righe)
    testo = "\n".join(
        rapporto_misura(leggi_misura(cartella / f"misura_{lato}.csv"), intestazione)
    )
    (cartella / f"rapporto_{lato}.txt").write_text(testo + "\n", encoding="utf-8")
    print(testo)

    base = CARTELLA_19D / "v0" / f"misura_{lato}.csv"
    if variante != "v0" and base.exists():
        misure = [("v0", leggi_misura(base))]
        v1 = CARTELLA_19D / "v1" / f"misura_{lato}.csv"
        if variante != "v1" and v1.exists():
            misure.append(("v1", leggi_misura(v1)))
        misure.append((variante, leggi_misura(cartella / f"misura_{lato}.csv")))
        confronto = "\n".join(rapporto_confronto(misure))
        (cartella / f"confronto_{lato}.txt").write_text(
            confronto + "\n", encoding="utf-8"
        )
        print("\n" + confronto)
    return 0


# --- terzo giro: ampiezza e k, vicini, parole in comune, nome dell'azione ---

# Combinazioni (ampiezza, k) misurate sulle copie di v0 e v1, senza copie
# nuove; la prima è quella dell'app e del secondo giro.
COMBINAZIONI = [
    (AMPIEZZA_APP, K),
    (PROFONDITA, K),
    (AMPIEZZA_APP, 15),
    (PROFONDITA, 15),
]
BASI_GRIGLIA = ("v0", "v1")
CONDIZIONI_GRIGLIA = ("A", "B")
DISTANZA_VICINI = 2

# Parole che non contano nel confronto tra domanda e pezzo: articoli,
# preposizioni, congiunzioni, parole interrogative, ausiliari e modali,
# pronomi atoni, possessivi e dimostrativi, dopo _normale (minuscole e
# senza accenti). Le lettere sole si scartano a parte; le cifre restano.
PAROLE_FUNZIONALI = frozenset(
    "il lo la gli le un uno una del dello della dei degli delle dell "
    "al allo alla ai agli alle all dal dallo dalla dai dagli dalle dall "
    "nel nello nella nei negli nelle nell sul sullo sulla sui sugli sulle sull "
    "col coi di da in con su per tra fra ed che cui come se ma anche oppure non "
    "quale quali qual quanto quanta quanti quante cosa chi dove quando perche "
    "sono essere era ha hanno puo possono deve devono viene vengono sia siano "
    "abbiamo possiamo dobbiamo siamo ho posso devo "
    "si ci ne mi ti vi "
    "nostro nostra nostri nostre mio mia suo sua suoi loro "
    "questo questa questi queste quello quella quelli quelle piu".split()
)

# Riga del titolo degli allegati degli apistici: "Intervento B Azione B4: ..."
SCHEMA_AZIONE = re.compile(r"^Intervento B Azione (B\d+): *(.+?) *$", re.MULTILINE)
RIGHE_APISTICI = range(67, 75)


def nome_colonna(ampiezza: int, k: int, c: str) -> str:
    return f"a{ampiezza}_k{k}_{c}"


def frammenti_della_copia(recupero, limite: int | None):
    """(frammenti per fonte, ordinati per chunk_num; titolo per id_bando)."""
    tokenizer = recupero.store.embeddings._client.tokenizer
    titolo_del_bando = {}
    frammenti_per_fonte: dict[str, list[Frammento]] = defaultdict(list)
    for d in recupero.documenti:
        fonte, fr = frammento_di(d)
        if limite:
            fr.car_visti = car_visti(tokenizer, fr.testo, limite)
        frammenti_per_fonte[fonte].append(fr)
        if d.metadata.get("id_bando"):
            titolo_del_bando[d.metadata["id_bando"]] = d.metadata["titolo"]
    for lista in frammenti_per_fonte.values():
        lista.sort(key=lambda fr: fr.chunk_num)
    return frammenti_per_fonte, titolo_del_bando


def distanza_dai_primi(
    pezzo: list[str],
    primi: list[tuple[str, Frammento]],
    giusti: set[str],
    frammenti_per_fonte: dict[str, list[Frammento]],
    massima: int = DISTANZA_VICINI,
) -> int | None:
    """0 se il pezzo sta in un frammento giusto tra i primi; altrimenti la
    distanza più piccola (fino a `massima`, in chunk_num dello stesso file)
    tra un frammento giusto tra i primi e un frammento che contiene il pezzo.
    """
    if prima_posizione(pezzo, primi, giusti) is not None:
        return 0
    migliore = None
    for fonte, fr in primi:
        if fonte not in giusti:
            continue
        for altro in frammenti_per_fonte.get(fonte, []):
            d = abs(altro.chunk_num - fr.chunk_num)
            if 1 <= d <= massima and (migliore is None or d < migliore):
                if contiene(pezzo, altro):
                    migliore = d
    return migliore


def completo_con_vicini(distanze: list[int | None], distanza: int) -> bool:
    """Il fatto è intero se ogni pezzo sta tra i primi o in un vicino entro `distanza`."""
    return all(d is not None and d <= distanza for d in distanze)


def parole_significative(testo: str) -> list[str]:
    """Le parole del testo senza quelle funzionali, una volta sola, in ordine."""
    from src.database.interrogazioni_bandi import _normale

    return list(
        dict.fromkeys(
            p
            for p in re.findall(r"[a-z0-9]+", _normale(testo))
            if p not in PAROLE_FUNZIONALI and not (len(p) == 1 and p.isalpha())
        )
    )


def parole_in_comune(domanda: str, pezzo: str) -> tuple[list[str], list[str]]:
    """(parole significative della domanda, quelle che hanno una simile nel pezzo).

    "Simile" è _simili di src/database/interrogazioni_bandi.py: uguali, o
    con le stesse prime 5 lettere se la più corta ne ha almeno 5; è la
    riduzione alla radice che il progetto ha già.
    """
    from src.database.interrogazioni_bandi import _simili

    nella_domanda = parole_significative(domanda)
    nel_pezzo = parole_significative(pezzo)
    comuni = [p for p in nella_domanda if any(_simili(p, q) for q in nel_pezzo)]
    return nella_domanda, comuni


def testo_dei_pezzi(fatto: dict) -> str:
    return " ".join(" ".join(celle) for celle in unita_del_fatto(fatto))


def nome_dell_azione(pagine: list[str], codice: str) -> tuple[int, str, str] | None:
    """(pagina da 1, riga esatta, parte proposta) del titolo dell'azione `codice`."""
    for numero, testo in enumerate(pagine, start=1):
        for m in SCHEMA_AZIONE.finditer(testo):
            if m[1] == codice:
                return numero, m[0], f"Azione {m[1]}: {m[2]}"
    return None


def mediana(valori: list[float]) -> float | None:
    import statistics

    return statistics.median(valori) if valori else None


def _media(valori: list[float]) -> str:
    return f"{sum(valori) / len(valori):.1f}" if valori else "-"


def esiti_combinazione(
    fatto, primi, profondi, giusti, gemelli, frammenti_per_fonte
) -> dict:
    """Esito di un fatto per una combinazione, con bando e caratteri dei primi."""
    esito = valuta(
        fatto,
        [frammento_di(d) for d, _, _ in primi],
        [frammento_di(d) for d, _, _ in profondi],
        giusti,
        gemelli,
        frammenti_per_fonte,
    )
    return {
        "trovato": "sì" if esito["trovato"] else "no",
        "posizioni": _posizioni(esito["posizioni_pezzi"]),
        "primo_giusto": esito["primo_giusto"] or "",
        "del_bando": sum(
            d.metadata.get("id_bando") == fatto["id_bando"] for d, _, _ in primi
        ),
        "frammenti": len(primi),
        "caratteri": sum(len(d.page_content) for d, _, _ in primi),
    }


def apri_misura(foglio: Path, divisione: Path, lato: str):
    """(firma della divisione, fatti della metà, file per bando)."""
    from scripts.ingestione.carica_avvisi import leggi_registro
    from scripts.ingestione.registra_avvisi import NOME_FILE
    from src.config import PROCESSED_DIR

    firma = verifica_impronta(divisione)
    fatti = fatti_della_meta(leggi_foglio(foglio), righe_della_meta(divisione, lato))
    file_per_bando: dict[str, list[dict]] = defaultdict(list)
    for r in leggi_registro(PROCESSED_DIR / NOME_FILE):
        file_per_bando[r["id_bandi"]].append(r)
    return firma, fatti, file_per_bando


def esegui_griglia(foglio: Path, divisione: Path, lato: str, base: str) -> int:
    """Ampiezza e k sulla copia di una base, più vicini e parole in comune."""
    import time

    from scripts.ingestione.carica_avvisi import senza_rete
    from src.config import CHROMA_DIR

    if base not in BASI_GRIGLIA:
        raise ErroreMisura(f"base {base!r}: la griglia si misura su {BASI_GRIGLIA}")
    senza_rete()
    cartella = CARTELLA_19D / base
    copia = cartella / "chroma"
    if not copia.is_dir():
        raise ErroreMisura(f"manca la copia {copia}")
    misura_base = {r["riga"]: r for r in leggi_misura(cartella / f"misura_{lato}.csv")}
    limite = VARIANTI[base].limite
    firma, fatti, file_per_bando = apri_misura(foglio, divisione, lato)

    prima = impronte_cartella(CHROMA_DIR)
    prima_copia = impronte_cartella(copia)
    inizio = time.perf_counter()
    with senza_connessioni():
        from src.chains.rag import recupera
        from src.recupero_documenti import avvolgi
        from src.retrieval import normalizza_domanda

        recupero = apri_recupero(copia, limite)
        app = {a: avvolgi(ConAmpiezza(recupero, a)) for a in (AMPIEZZA_APP, PROFONDITA)}
        frammenti_per_fonte, titolo_del_bando = frammenti_della_copia(recupero, limite)

        righe = []
        for fatto in fatti:
            giusti, gemelli = documenti_del_fatto(fatto, file_per_bando)
            domanda = normalizza_domanda(str(fatto["domanda"]))
            ripulita = domanda_ripulita(domanda, titolo_del_bando[fatto["id_bando"]])
            id_bando = fatto["id_bando"]
            profondi = {
                "A": recupera(app[PROFONDITA], fatto["domanda"], k=PROFONDITA),
                "B": recupero.cerca_nel_bando(
                    ripulita, id_bando, PROFONDITA, ampiezza=PROFONDITA
                ),
            }
            unita = unita_del_fatto(fatto)
            riga = {
                "riga": str(fatto["riga"]),
                "id_bando": id_bando,
                "pezzi": len(unita),
            }
            for ampiezza, k in COMBINAZIONI:
                for c in CONDIZIONI_GRIGLIA:
                    primi = (
                        recupera(app[ampiezza], fatto["domanda"], k=k)
                        if c == "A"
                        else recupero.cerca_nel_bando(
                            ripulita, id_bando, k, ampiezza=ampiezza
                        )
                    )
                    esito = esiti_combinazione(
                        fatto, primi, profondi[c], giusti, gemelli, frammenti_per_fonte
                    )
                    n = nome_colonna(ampiezza, k, c)
                    riga.update({f"{n}_{chiave}": v for chiave, v in esito.items()})
                    if (ampiezza, k) == COMBINAZIONI[0]:
                        elenco = [frammento_di(d) for d, _, _ in primi]
                        distanze = [
                            distanza_dai_primi(p, elenco, giusti, frammenti_per_fonte)
                            for p in unita
                        ]
                        riga[f"{c}_vicini"] = _posizioni(distanze)
            nella_domanda, comuni = parole_in_comune(ripulita, testo_dei_pezzi(fatto))
            riga.update(
                parole_domanda=" ".join(nella_domanda),
                parole_comuni=" ".join(comuni),
                n_parole_domanda=len(nella_domanda),
                n_parole_comuni=len(comuni),
            )
            righe.append(riga)
        del recupero, app
    tempo = time.perf_counter() - inizio

    if impronte_cartella(CHROMA_DIR) != prima:
        raise ErroreMisura("le impronte del Chroma vero sono cambiate")
    dopo_copia = impronte_cartella(copia)
    cambiati = sorted(
        n
        for n in set(prima_copia) | set(dopo_copia)
        if prima_copia.get(n) != dopo_copia.get(n)
    )

    # La combinazione dell'app deve ridare la misura del secondo giro
    diverse = [
        (
            r["riga"],
            c,
            r[f"{nome_colonna(*COMBINAZIONI[0], c)}_posizioni"],
            misura_base[r["riga"]][f"{c}_posizioni_pezzi"],
        )
        for r in righe
        for c in CONDIZIONI_GRIGLIA
        if r[f"{nome_colonna(*COMBINAZIONI[0], c)}_trovato"]
        != misura_base[r["riga"]][f"{c}_trovato"]
        or r[f"{nome_colonna(*COMBINAZIONI[0], c)}_posizioni"]
        != misura_base[r["riga"]][f"{c}_posizioni_pezzi"]
    ]
    if diverse:
        raise ErroreMisura(
            f"la combinazione dell'app non ridà la misura di {base}: {diverse}"
        )

    colonne = list(righe[0])
    with (cartella / f"griglia_{lato}.csv").open(
        "w", encoding="utf-8", newline=""
    ) as f:
        scrittore = csv.DictWriter(f, fieldnames=colonne, lineterminator="\n")
        scrittore.writeheader()
        scrittore.writerows(righe)
    intestazione = [
        f"Passo 19d, terzo giro, base {base}, metà: {lato}",
        f"Divisione: {divisione.name} (sha256 {firma})",
        NOTA_REGOLA,
        (
            f"Copia riusata: {copia}; impronte "
            + (
                f"cambiate all'apertura in sola lettura: {', '.join(cambiati)}"
                if cambiati
                else "uguali prima e dopo"
            )
        ),
        f"Chroma vero: {len(prima)} file, impronte uguali prima e dopo",
        f"Controllo: con ampiezza {AMPIEZZA_APP} e k={K} trovati e posizioni uguali a misura_{lato}.csv",
        f"Tempo: {tempo:.1f} s",
    ]
    testo = "\n".join(rapporto_griglia(righe, intestazione))
    (cartella / f"griglia_{lato}.txt").write_text(testo + "\n", encoding="utf-8")
    print(testo)
    return 0


def rapporto_griglia(righe: list[dict], intestazione: list[str]) -> list[str]:
    linee = [*intestazione, ""]
    uno = [r for r in righe if int(r["pezzi"]) == 1]
    piu = [r for r in righe if int(r["pezzi"]) > 1]

    def conta(sue, n):
        return f"{sum(r[f'{n}_trovato'] == 'sì' for r in sue)}/{len(sue)}"

    titoli = [
        "trovati A",
        "trovati B",
        "un pezzo A",
        "un pezzo B",
        "più pezzi A",
        "più pezzi B",
    ]
    linee.append(f"{'ampiezza, k':<14}" + "".join(f"{t:>13}" for t in titoli))
    for ampiezza, k in COMBINAZIONI:
        a, b = nome_colonna(ampiezza, k, "A"), nome_colonna(ampiezza, k, "B")
        valori = [
            conta(righe, a),
            conta(righe, b),
            conta(uno, a),
            conta(uno, b),
            conta(piu, a),
            conta(piu, b),
        ]
        linee.append(f"{f'{ampiezza}, {k}':<14}" + "".join(f"{v:>13}" for v in valori))

    linee += ["", f"Guadagnati e persi rispetto ad ampiezza {AMPIEZZA_APP}, k={K}:"]
    for ampiezza, k in COMBINAZIONI[1:]:
        for c in CONDIZIONI_GRIGLIA:
            base = nome_colonna(*COMBINAZIONI[0], c)
            n = nome_colonna(ampiezza, k, c)
            guadagnati = [
                r["riga"]
                for r in righe
                if r[f"{n}_trovato"] == "sì" and r[f"{base}_trovato"] != "sì"
            ]
            persi = [
                r["riga"]
                for r in righe
                if r[f"{base}_trovato"] == "sì" and r[f"{n}_trovato"] != "sì"
            ]
            linee.append(
                f"  ampiezza {ampiezza}, k={k}, {c}: guadagnati {len(guadagnati)} "
                f"({', '.join(guadagnati) or '-'}); persi {len(persi)} ({', '.join(persi) or '-'})"
            )

    linee += [
        "",
        "Frammenti del bando giusto e caratteri passati al modello (media per fatto):",
    ]
    for ampiezza, k in COMBINAZIONI:
        for c in CONDIZIONI_GRIGLIA:
            n = nome_colonna(ampiezza, k, c)
            linee.append(
                f"  ampiezza {ampiezza}, k={k}, {c}: frammenti {_media([int(r[f'{n}_frammenti']) for r in righe])}, "
                f"del bando {_media([int(r[f'{n}_del_bando']) for r in righe])}, "
                f"caratteri {_media([int(r[f'{n}_caratteri']) for r in righe])}"
            )
    for ampiezza in (AMPIEZZA_APP, PROFONDITA):
        for c in CONDIZIONI_GRIGLIA:
            dieci = [int(r[f"{nome_colonna(ampiezza, K, c)}_caratteri"]) for r in righe]
            quindici = [
                int(r[f"{nome_colonna(ampiezza, 15, c)}_caratteri"]) for r in righe
            ]
            extra = [q - d for q, d in zip(quindici, dieci, strict=True)]
            linee.append(
                f"  caratteri in più da k={K} a k=15, ampiezza {ampiezza}, {c}: media "
                f"{_media(extra)}, minimo {min(extra)}, massimo {max(extra)}"
            )

    linee += [
        "",
        f"Vicini (ampiezza {AMPIEZZA_APP}, k={K}), risposte in più pezzi: per pezzo 0 se",
        "tra i primi, 1 o 2 se in un vicino a quella distanza di un frammento giusto",
        "tra i primi, '-' se oltre:",
    ]
    for c in CONDIZIONI_GRIGLIA:
        for d in (1, DISTANZA_VICINI):
            interi = [
                r["riga"]
                for r in piu
                if r[f"{nome_colonna(*COMBINAZIONI[0], c)}_trovato"] != "sì"
                and completo_con_vicini(_distanze(r[f"{c}_vicini"]), d)
            ]
            linee.append(
                f"  {c}, vicini a ±{d}: fatti in più pezzi resi interi {len(interi)} "
                f"({', '.join(interi) or '-'})"
            )
        for r in piu:
            linee.append(
                f"    riga {r['riga']}: trovato {r[f'{nome_colonna(*COMBINAZIONI[0], c)}_trovato']}, "
                f"pezzi {r[f'{c}_vicini']}"
            )
    for c in CONDIZIONI_GRIGLIA:
        for d in (1, DISTANZA_VICINI):
            interi = [
                r["riga"]
                for r in uno
                if r[f"{nome_colonna(*COMBINAZIONI[0], c)}_trovato"] != "sì"
                and completo_con_vicini(_distanze(r[f"{c}_vicini"]), d)
            ]
            linee.append(
                f"  stesso conteggio, risposte in un pezzo, {c}, ±{d}: {len(interi)} "
                f"({', '.join(interi) or '-'})"
            )

    b = nome_colonna(*COMBINAZIONI[0], "B")
    trovati = [r for r in righe if r[f"{b}_trovato"] == "sì"]
    mancati = [r for r in righe if r[f"{b}_trovato"] != "sì"]
    linee += [
        "",
        "Parole significative della domanda ripulita in comune con il pezzo (B):",
        (
            f"  trovati: {len(trovati)}, mediana "
            f"{mediana([int(r['n_parole_comuni']) for r in trovati])} in comune su "
            f"{mediana([int(r['n_parole_domanda']) for r in trovati])} della domanda"
        ),
        (
            f"  non trovati: {len(mancati)}, mediana "
            f"{mediana([int(r['n_parole_comuni']) for r in mancati])} in comune su "
            f"{mediana([int(r['n_parole_domanda']) for r in mancati])} della domanda"
        ),
    ]
    for r in mancati:
        linee.append(
            f"    riga {r['riga']}: {r['n_parole_comuni']} su {r['n_parole_domanda']} "
            f"(in comune: {r['parole_comuni'] or '-'}; della domanda: {r['parole_domanda']})"
        )
    return linee


def _distanze(testo: str) -> list[int | None]:
    return [None if x == "-" else int(x) for x in testo.split(" || ")]


def prepara_copia_parte(
    cartella: Path, sorgente: Path, parti: dict[str, str], limite: int | None
) -> dict:
    """Copia di una copia di Chroma con la parte davanti al testo del vettore.

    Solo per i frammenti dei file in `parti`; testo e metadati restano
    quelli della sorgente. I vettori si calcolano con il limite della base.
    """
    import shutil

    import chromadb
    from chromadb.config import Settings

    from src.config import COLLECTION_NAME
    from src.vectorstore import crea_embeddings

    copia = cartella / "chroma"
    if copia.exists():
        shutil.rmtree(copia)
    cartella.mkdir(parents=True, exist_ok=True)
    shutil.copytree(sorgente, copia)
    embeddings = crea_embeddings()
    embeddings._client.max_seq_length = limite or LIMITE_MODELLO
    cliente = chromadb.PersistentClient(
        path=str(copia), settings=Settings(anonymized_telemetry=False)
    )
    collezione = cliente.get_collection(COLLECTION_NAME)
    dati = collezione.get(
        where={"fonte": {"$in": sorted(parti)}}, include=["documents", "metadatas"]
    )
    per_fonte = Counter(m["fonte"] for m in dati["metadatas"])
    if set(per_fonte) != set(parti):
        raise ErroreMisura(
            f"file senza frammenti nella copia: {sorted(set(parti) - set(per_fonte))}"
        )
    vettori = embeddings.embed_documents(
        [
            testo_lessicale(t, m, parti)
            for t, m in zip(dati["documents"], dati["metadatas"], strict=True)
        ]
    )
    collezione.update(ids=dati["ids"], embeddings=vettori)
    dopo = collezione.get(ids=dati["ids"], include=["documents"])
    if dict(zip(dopo["ids"], dopo["documents"], strict=True)) != dict(
        zip(dati["ids"], dati["documents"], strict=True)
    ):
        raise ErroreMisura("il testo dei frammenti è cambiato nella copia")
    totale = collezione.count()
    del cliente
    return {
        "frammenti": len(dati["ids"]),
        "per_fonte": dict(per_fonte),
        "totale": totale,
    }


def esegui_apistici(foglio: Path, divisione: Path, lato: str) -> int:
    """Nome dell'azione dai quattro allegati, poi la misura delle righe 67-74."""
    import time

    from scripts.ingestione import carica_avvisi as ca
    from scripts.ingestione.registra_avvisi import NOME_FILE
    from src.config import CHROMA_DIR, PROCESSED_DIR

    ca.senza_rete()
    linee = [
        f"Passo 19d, terzo giro, nome dell'azione degli apistici, metà: {lato}",
        NOTA_REGOLA,
        "",
    ]
    parti: dict[str, str] = {}
    for r in ca.leggi_registro(PROCESSED_DIR / NOME_FILE):
        if not r["parte"].startswith("Azione "):
            continue
        codice = r["parte"].split()[1]
        trovato = nome_dell_azione(ca.pagine_del_pdf(ca.percorso_del_file(r)), codice)
        if trovato is None:
            raise ErroreMisura(
                f"{r['nome_file']}: nessuna riga 'Intervento B Azione {codice}: ...'"
            )
        pagina, riga_esatta, proposta = trovato
        parti[r["nome_file"]] = proposta
        linee += [
            f"{r['nome_file']} ({r['atto']}, parte nel registro {r['parte']!r}):",
            f"  pagina {pagina}, testo esatto: {riga_esatta!r}",
            f"  parte proposta: {proposta!r}, fonte: pagina {pagina} del file, titolo dell'allegato",
        ]
    if len(parti) != 4:
        raise ErroreMisura(
            f"allegati degli apistici nel registro: {len(parti)}, attesi 4"
        )

    firma, fatti, file_per_bando = apri_misura(foglio, divisione, lato)
    fatti = [f for f in fatti if f["riga"] in RIGHE_APISTICI]
    linee += [
        "",
        f"Righe {RIGHE_APISTICI.start}-{RIGHE_APISTICI.stop - 1} della metà {lato}: "
        + ", ".join(str(f["riga"]) for f in fatti),
        f"Divisione: {divisione.name} (sha256 {firma})",
    ]

    prima = impronte_cartella(CHROMA_DIR)
    with senza_connessioni():
        from src.chains.rag import recupera
        from src.recupero_documenti import avvolgi
        from src.retrieval import normalizza_domanda

        for base in BASI_GRIGLIA:
            inizio = time.perf_counter()
            sorgente = CARTELLA_19D / base / "chroma"
            prima_sorgente = impronte_cartella(sorgente)
            cartella = CARTELLA_19D / f"{base}+parte"
            limite = VARIANTI[base].limite
            info = prepara_copia_parte(cartella, sorgente, parti, limite)
            if impronte_cartella(sorgente) != prima_sorgente:
                raise ErroreMisura(f"le impronte di {sorgente} sono cambiate")
            recupero = apri_recupero(cartella / "chroma", limite, prefissi=parti)
            app = avvolgi(recupero)
            profondo = avvolgi(Profondo(recupero))
            frammenti_per_fonte, titolo_del_bando = frammenti_della_copia(
                recupero, limite
            )
            misura_base = {
                r["riga"]: r
                for r in leggi_misura(CARTELLA_19D / base / f"misura_{lato}.csv")
            }
            linee += [
                "",
                (
                    f"Base {base}, copia {cartella / 'chroma'}: vettori "
                    f"ricalcolati per {info['frammenti']} frammenti "
                    f"({', '.join(f'{k} {v}' for k, v in sorted(info['per_fonte'].items()))}) "
                    f"su {info['totale']}; parte nel vettore e nella ricerca per "
                    "parole, testo pulito"
                ),
                f"{'riga':<6}{'':<4}{base + ' primi 10 (50)':>26}{base + '+parte primi 10 (50)':>30}",
            ]
            for fatto in fatti:
                giusti, gemelli = documenti_del_fatto(fatto, file_per_bando)
                domanda = normalizza_domanda(str(fatto["domanda"]))
                ripulita = domanda_ripulita(
                    domanda, titolo_del_bando[fatto["id_bando"]]
                )
                elenchi = {
                    "A": (
                        recupera(app, fatto["domanda"], k=K),
                        recupera(profondo, fatto["domanda"], k=PROFONDITA),
                    ),
                    "B": (
                        recupero.cerca_nel_bando(ripulita, fatto["id_bando"], K),
                        recupero.cerca_nel_bando(
                            ripulita, fatto["id_bando"], PROFONDITA, ampiezza=PROFONDITA
                        ),
                    ),
                }
                for c, (primi, profondi) in elenchi.items():
                    esito = valuta(
                        fatto,
                        [frammento_di(d) for d, _, _ in primi],
                        [frammento_di(d) for d, _, _ in profondi],
                        giusti,
                        gemelli,
                        frammenti_per_fonte,
                    )
                    vecchia = misura_base[str(fatto["riga"])]
                    prima_c = f"{vecchia[f'{c}_trovato']} {vecchia[f'{c}_posizioni_pezzi']} ({vecchia[f'{c}_posizioni_profonde']})"
                    dopo_c = (
                        f"{'sì' if esito['trovato'] else 'no'} {_posizioni(esito['posizioni_pezzi'])} "
                        f"({_posizioni(esito['posizioni_profonde'])})"
                    )
                    linee.append(
                        f"{fatto['riga']:<6}{c:<4}{prima_c:>26}{dopo_c:>30}"
                        + ("  pezzo dal gemello" if esito["pezzo_dal_gemello"] else "")
                    )
            del recupero, app, profondo
            linee.append(f"Tempo: {time.perf_counter() - inizio:.1f} s")
    if impronte_cartella(CHROMA_DIR) != prima:
        raise ErroreMisura("le impronte del Chroma vero sono cambiate")
    linee.append(f"Chroma vero: {len(prima)} file, impronte uguali prima e dopo")
    testo = "\n".join(linee)
    (CARTELLA_19D / f"apistici_{lato}.txt").write_text(testo + "\n", encoding="utf-8")
    print(testo)
    return 0


# --- quarto giro: ricerca esatta e altri modelli di embedding ---

# La ricerca densa sull'indice HNSW di Chroma non è ripetibile da un
# processo all'altro (terzo giro: la coda di sqlite si riapplica a ogni
# apertura). Da qui la misura è esatta: vettori e metadati letti una volta
# dalla copia, ordinati con il prodotto scalare su tutti i frammenti, con
# lo stesso filtro e la stessa unione con la ricerca per parole.


@dataclass(frozen=True)
class Modello:
    """Un modello di embedding da misurare con la ricerca esatta.

    limite: token (None: quello del modello); domanda e passaggio: i
    prefissi che il modello vuole davanti a domanda e frammenti.
    """

    nome: str
    limite: int | None = None
    domanda: str = ""
    passaggio: str = ""


MODELLI: dict[str, Modello] = {
    "v0": Modello("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
    "e5-small": Modello("intfloat/multilingual-e5-small", 512, "query: ", "passage: "),
    "e5-base": Modello("intfloat/multilingual-e5-base", 512, "query: ", "passage: "),
}
K_ESATTI = (K, 15)
FILE_VETTORI = "vettori.npy"
FILE_FRAMMENTI = "frammenti.json"
TOLLERANZA_NORMA = 1e-3
# I fatti non trovati in v1, condizione B, nel terzo giro
RIGHE_PERSE = (18, 23, 24, 29, 42, 45, 51, 58, 72, 74, 89, 91)


def controlla_normalizzati(matrice) -> float:
    """Lo scarto massimo della norma da 1; ferma se supera la tolleranza."""
    import numpy as np

    scarto = float(np.max(np.abs(np.linalg.norm(matrice, axis=1) - 1.0)))
    if scarto > TOLLERANZA_NORMA:
        raise ErroreMisura(f"vettori non normalizzati: scarto della norma {scarto:.4f}")
    return scarto


class StoreEsatto:
    """Ricerca densa esatta: prodotto scalare con tutti i vettori.

    Ha get(), similarity_search() ed embeddings come lo store di Chroma
    che RecuperoMisura si aspetta. I pari merito si ordinano per id, così
    l'ordine non dipende da nient'altro che dai numeri.
    """

    def __init__(self, ids, testi, metadati, matrice, embeddings, prefisso="") -> None:
        import numpy as np

        self.ids = list(ids)
        self.testi = list(testi)
        self.metadati = [dict(m) for m in metadati]
        self.matrice = np.asarray(matrice, dtype=np.float64)
        if len(self.ids) != len(self.matrice):
            raise ErroreMisura("vettori e frammenti in numero diverso")
        controlla_normalizzati(self.matrice)
        self.embeddings = embeddings
        self.prefisso = prefisso

    def get(self) -> dict:
        return {"ids": self.ids, "documents": self.testi, "metadatas": self.metadati}

    def punteggi(self, domanda: str):
        import numpy as np

        vettore = np.asarray(
            self.embeddings.embed_query(self.prefisso + domanda), dtype=np.float64
        )
        return self.matrice @ vettore

    def similarity_search(self, query: str, k: int = 4, filter: dict | None = None):  # noqa: A002
        from langchain_core.documents import Document

        punteggi = self.punteggi(query)
        indici = [
            i
            for i, meta in enumerate(self.metadati)
            if not filter or all(meta.get(c) == v for c, v in filter.items())
        ]
        ordine = sorted(indici, key=lambda i: (-punteggi[i], self.ids[i]))[:k]
        return [
            Document(page_content=self.testi[i], metadata=dict(self.metadati[i]))
            for i in ordine
        ]


def esporta_frammenti(copia: Path) -> tuple[list, list, list, list]:
    """(ids, testi, metadati, vettori) di una copia di Chroma, ordinati per id."""
    import chromadb
    from chromadb.config import Settings

    from src.config import COLLECTION_NAME

    cliente = chromadb.PersistentClient(
        path=str(copia), settings=Settings(anonymized_telemetry=False)
    )
    dati = cliente.get_collection(COLLECTION_NAME).get(
        include=["documents", "metadatas", "embeddings"]
    )
    del cliente
    ordine = sorted(range(len(dati["ids"])), key=lambda i: dati["ids"][i])
    return (
        [dati["ids"][i] for i in ordine],
        [dati["documents"][i] for i in ordine],
        [dati["metadatas"][i] for i in ordine],
        [list(dati["embeddings"][i]) for i in ordine],
    )


def salva_vettori(cartella: Path, ids, testi, metadati, matrice) -> str:
    """Scrive vettori e frammenti; restituisce l'impronta dei frammenti."""
    import json

    import numpy as np

    cartella.mkdir(parents=True, exist_ok=True)
    np.save(cartella / FILE_VETTORI, np.asarray(matrice, dtype=np.float32))
    (cartella / FILE_FRAMMENTI).write_text(
        json.dumps(
            {"ids": ids, "testi": testi, "metadati": metadati}, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    return impronta_frammenti(ids, testi, metadati)


def leggi_vettori(cartella: Path) -> tuple[list, list, list, object]:
    import json

    import numpy as np

    if not (cartella / FILE_VETTORI).exists():
        raise ErroreMisura(f"mancano i vettori in {cartella}: serve --prepara-vettori")
    dati = json.loads((cartella / FILE_FRAMMENTI).read_text(encoding="utf-8"))
    return (
        dati["ids"],
        dati["testi"],
        dati["metadati"],
        np.load(cartella / FILE_VETTORI),
    )


def crea_embeddings_di(modello: Modello):
    """Il modello come lo usa il progetto (HuggingFaceEmbeddings, normalizzato)."""
    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(
        model_name=modello.nome, encode_kwargs={"normalize_embeddings": True}
    )
    if modello.limite:
        embeddings._client.max_seq_length = modello.limite
    return embeddings


def testi_con_prefisso(testi: list[str], prefisso: str) -> list[str]:
    return [prefisso + t for t in testi]


def esegui_prepara_vettori(nome: str) -> int:
    """v0: vettori letti dalla copia di v0; gli altri: ricalcolati con il modello."""
    import time

    import numpy as np

    from scripts.ingestione.carica_avvisi import senza_rete

    senza_rete()
    modello = MODELLI[nome]
    cartella = CARTELLA_19D / nome
    inizio = time.perf_counter()
    with senza_connessioni():
        if nome == "v0":
            copia = CARTELLA_19D / "v0" / "chroma"
            ids, testi, metadati, matrice = esporta_frammenti(copia)
        else:
            ids, testi, metadati, _ = leggi_vettori(CARTELLA_19D / "v0")
            embeddings = crea_embeddings_di(modello)
            matrice = embeddings.embed_documents(
                testi_con_prefisso(testi, modello.passaggio)
            )
        scarto = controlla_normalizzati(np.asarray(matrice))
        firma = salva_vettori(cartella, ids, testi, metadati, matrice)
    if nome != "v0":
        _, t0, m0, _ = leggi_vettori(CARTELLA_19D / "v0")
        if impronta_frammenti(ids, t0, m0) != firma:
            raise ErroreMisura("i frammenti non sono quelli di v0")
    print(
        f"{nome}: {len(ids)} frammenti, dimensione {len(matrice[0])}, scarto massimo "
        f"della norma {scarto:.2e}, impronta dei frammenti {firma[:16]}, "
        f"{time.perf_counter() - inizio:.1f} s"
    )
    return 0


def apri_recupero_esatto(nome: str):
    """RecuperoMisura sui vettori della cartella del modello, con ricerca esatta."""
    modello = MODELLI[nome]
    ids, testi, metadati, matrice = leggi_vettori(CARTELLA_19D / nome)
    embeddings = crea_embeddings_di(modello)
    store = StoreEsatto(ids, testi, metadati, matrice, embeddings, modello.domanda)
    return apri_recupero(Path(), store=store)


def esegui_esatta(foglio: Path, divisione: Path, lato: str, nome: str) -> int:
    """Misura esatta con k=10 e k=15, condizioni A e B (B ripulita)."""
    import json
    import time

    from scripts.ingestione.carica_avvisi import senza_rete
    from src.config import CHROMA_DIR

    senza_rete()
    modello = MODELLI[nome]
    cartella = CARTELLA_19D / nome
    firma, fatti, file_per_bando = apri_misura(foglio, divisione, lato)
    prima = impronte_cartella(CHROMA_DIR)
    tempi = {}
    with senza_connessioni():
        from src.chains.rag import recupera
        from src.recupero_documenti import avvolgi, documenti_nominati
        from src.retrieval import normalizza_domanda

        inizio = time.perf_counter()
        recupero = apri_recupero_esatto(nome)
        app = avvolgi(recupero)
        profondo = avvolgi(Profondo(recupero))
        frammenti_per_fonte, titolo_del_bando = frammenti_della_copia(
            recupero, modello.limite
        )
        tempi["apertura"] = time.perf_counter() - inizio

        inizio = time.perf_counter()
        righe = {k: [] for k in K_ESATTI}
        elenchi_scritti = {}
        for fatto in fatti:
            giusti, gemelli = documenti_del_fatto(fatto, file_per_bando)
            domanda = normalizza_domanda(str(fatto["domanda"]))
            ripulita = domanda_ripulita(domanda, titolo_del_bando[fatto["id_bando"]])
            profondi = {
                "A": recupera(profondo, fatto["domanda"], k=PROFONDITA),
                "B": recupero.cerca_nel_bando(
                    ripulita, fatto["id_bando"], PROFONDITA, ampiezza=PROFONDITA
                ),
            }
            nominati = set(documenti_nominati(domanda, app.titoli))
            for k in K_ESATTI:
                primi = {
                    "A": recupera(app, fatto["domanda"], k=k),
                    "B": recupero.cerca_nel_bando(ripulita, fatto["id_bando"], k),
                }
                esiti = {
                    c: valuta(
                        fatto,
                        [frammento_di(d) for d, _, _ in primi[c]],
                        [frammento_di(d) for d, _, _ in profondi[c]],
                        giusti,
                        gemelli,
                        frammenti_per_fonte,
                    )
                    for c in CONDIZIONI_GRIGLIA
                }
                di_sempre = sum(not d.metadata.get("sha256") for d, _, _ in primi["A"])
                riga = riga_misura(
                    fatto,
                    giusti,
                    gemelli,
                    esiti,
                    nominati,
                    di_sempre,
                    ripulita if ripulita != domanda else "",
                )
                _, spezzati_, assenti = stato_dei_pezzi(
                    fatto, giusti, frammenti_per_fonte
                )
                riga.update(pezzi_spezzati=spezzati_, pezzi_assenti=assenti)
                righe[k].append(riga)
                for c in CONDIZIONI_GRIGLIA:
                    elenchi_scritti[f"{fatto['riga']} {c} k={k}"] = [
                        [d.metadata.get("fonte"), d.metadata.get("chunk_num"), repr(p)]
                        for d, p, _ in primi[c]
                    ]
            for c in CONDIZIONI_GRIGLIA:
                elenchi_scritti[f"{fatto['riga']} {c} profondi"] = [
                    [d.metadata.get("fonte"), d.metadata.get("chunk_num"), repr(p)]
                    for d, p, _ in profondi[c]
                ]
        tempi["ricerche"] = time.perf_counter() - inizio
        del recupero, app, profondo
    if impronte_cartella(CHROMA_DIR) != prima:
        raise ErroreMisura("le impronte del Chroma vero sono cambiate")

    testo_elenchi = json.dumps(elenchi_scritti, ensure_ascii=False, indent=0).encode()
    (cartella / f"elenchi_esatti_{lato}.json").write_bytes(testo_elenchi)
    for k in K_ESATTI:
        with (cartella / f"esatta_k{k}_{lato}.csv").open(
            "w", encoding="utf-8", newline=""
        ) as f:
            scrittore = csv.DictWriter(
                f, fieldnames=COLONNE_MISURA, lineterminator="\n", restval=""
            )
            scrittore.writeheader()
            scrittore.writerows(righe[k])

    intestazione = [
        f"Passo 19d, quarto giro, misura esatta {nome}, metà: {lato}",
        f"Divisione: {divisione.name} (sha256 {firma})",
        NOTA_REGOLA,
        (
            f"Modello {modello.nome}, limite {modello.limite or LIMITE_MODELLO} token, "
            f"prefisso della domanda {modello.domanda!r}, dei frammenti "
            f"{modello.passaggio!r}; ricerca densa esatta (prodotto scalare su "
            "tutti i frammenti, pari merito per id)"
        ),
        f"Elenchi recuperati: elenchi_esatti_{lato}.json, sha256 {impronta(testo_elenchi)}",
        f"Chroma vero: {len(prima)} file, impronte uguali prima e dopo",
        "Tempi: " + "; ".join(f"{n} {s:.1f} s" for n, s in tempi.items()),
    ]
    # il rapporto legge i CSV appena scritti, come i confronti
    scritte = {k: leggi_esatta(nome, k, lato) for k in K_ESATTI}
    testo = "\n".join(rapporto_esatto(nome, scritte, lato, intestazione))
    (cartella / f"esatta_{lato}.txt").write_text(testo + "\n", encoding="utf-8")
    print(testo)
    return 0


def leggi_esatta(nome: str, k: int, lato: str) -> list[dict] | None:
    percorso = CARTELLA_19D / nome / f"esatta_k{k}_{lato}.csv"
    return leggi_misura(percorso) if percorso.exists() else None


def esiti_diversi(prima: dict[str, bool], dopo: dict[str, bool]) -> list[str]:
    """Le righe in cui l'esito cambia, in ordine di numero."""
    if set(prima) != set(dopo):
        raise ErroreMisura("le due misure non hanno gli stessi fatti")
    return [r for r in sorted(prima, key=int) if prima[r] != dopo[r]]


def rapporto_esatto(
    nome: str, righe: dict[int, list[dict]], lato: str, intestazione: list[str]
) -> list[str]:
    linee = [*intestazione, ""]
    linee += tabella_affiancata(
        [(f"k={k} {c}", righe[k], c) for k in K_ESATTI for c in CONDIZIONI_GRIGLIA]
    )
    if nome == "v0":
        # confronto con la misura sull'indice di Chroma
        chroma = {
            K: {
                c: {
                    r["riga"]: r[f"{c}_trovato"] == "sì"
                    for r in leggi_misura(CARTELLA_19D / "v0" / f"misura_{lato}.csv")
                }
                for c in CONDIZIONI_GRIGLIA
            },
            15: {
                c: {
                    r["riga"]: r[f"{nome_colonna(AMPIEZZA_APP, 15, c)}_trovato"] == "sì"
                    for r in leggi_misura(CARTELLA_19D / "v0" / f"griglia_{lato}.csv")
                }
                for c in CONDIZIONI_GRIGLIA
            },
        }
        linee += [
            "",
            "Esiti diversi dalla misura sull'indice di Chroma (secondo e terzo giro):",
        ]
        for k in K_ESATTI:
            for c in CONDIZIONI_GRIGLIA:
                esatti = {r["riga"]: r[f"{c}_trovato"] == "sì" for r in righe[k]}
                diversi = esiti_diversi(chroma[k][c], esatti)
                linee.append(
                    f"  k={k}, {c}: {len(diversi)} "
                    + (
                        "("
                        + ", ".join(
                            f"{r} {'trovato' if esatti[r] else 'non trovato'}"
                            for r in diversi
                        )
                        + ")"
                        if diversi
                        else ""
                    )
                )
        return linee
    for k in K_ESATTI:
        base = leggi_esatta("v0", k, lato)
        if base is None:
            continue
        linee += ["", f"=== k={k}: confronto con v0 (misura esatta) ==="]
        linee += rapporto_confronto([("v0", base), (nome, righe[k])])[2:]
        per_riga = {int(r["riga"]): r for r in righe[k]}
        base_per_riga = {int(r["riga"]): r for r in base}
        linee += ["", f"I 12 fatti non trovati in v1 B nel terzo giro, k={k}:"]
        for numero in RIGHE_PERSE:
            r, b = per_riga[numero], base_per_riga[numero]
            celle = [
                f"{c} v0 {b[f'{c}_trovato']} {b[f'{c}_posizioni_pezzi']} "
                f"({b[f'{c}_posizioni_profonde']}) -> {nome} {r[f'{c}_trovato']} "
                f"{r[f'{c}_posizioni_pezzi']} ({r[f'{c}_posizioni_profonde']})"
                for c in CONDIZIONI_GRIGLIA
            ]
            linee.append(f"  riga {numero}: " + "; ".join(celle))
    return linee


def memoria_del_processo() -> int:
    """Memoria del processo in byte (working set su Windows, RSS altrove)."""
    if sys.platform == "win32":
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
        # senza i tipi dichiarati la maniglia del processo si tronca a 32 bit
        corrente = ctypes.windll.kernel32.GetCurrentProcess
        corrente.restype = wintypes.HANDLE
        informazioni = ctypes.windll.psapi.GetProcessMemoryInfo
        informazioni.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Contatori),
            wintypes.DWORD,
        ]
        informazioni.restype = wintypes.BOOL
        if not informazioni(corrente(), ctypes.byref(contatori), contatori.cb):
            raise ErroreMisura("GetProcessMemoryInfo non ha risposto")
        return int(contatori.WorkingSetSize)
    import resource

    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def dimensione_su_disco(nome_modello: str) -> int:
    """Byte dei file del modello nella cache di Hugging Face."""
    from huggingface_hub.constants import HF_HUB_CACHE

    cartella = Path(HF_HUB_CACHE) / f"models--{nome_modello.replace('/', '--')}"
    if not cartella.exists():
        raise ErroreMisura(f"modello non scaricato: {nome_modello}")
    return sum(p.stat().st_size for p in (cartella / "blobs").rglob("*") if p.is_file())


def esegui_peso(nome: str) -> int:
    """Memoria, tempo di caricamento e di una domanda, disco; in un processo nuovo."""
    import statistics
    import time

    from scripts.ingestione.carica_avvisi import senza_rete

    senza_rete()
    modello = MODELLI[nome]
    mb = 1024 * 1024
    with senza_connessioni():
        partenza = memoria_del_processo()
        import langchain_huggingface  # noqa: F401
        import sentence_transformers  # noqa: F401

        dopo_import = memoria_del_processo()
        inizio = time.perf_counter()
        embeddings = crea_embeddings_di(modello)
        caricamento = time.perf_counter() - inizio
        dopo_modello = memoria_del_processo()
        domanda = modello.domanda + (
            "Il nostro comune montano può partecipare al bando per la scuola "
            "di musica se ha già avuto un contributo?"
        )
        embeddings.embed_query(domanda)
        durate = []
        for _ in range(20):
            inizio = time.perf_counter()
            embeddings.embed_query(domanda)
            durate.append((time.perf_counter() - inizio) * 1000)
        dopo_domande = memoria_del_processo()
        linee = [
            f"{nome} ({modello.nome}):",
            (
                f"  memoria all'avvio di Python {partenza / mb:.0f} MB; dopo gli "
                f"import {dopo_import / mb:.0f} MB; dopo il caricamento del modello "
                f"{dopo_modello / mb:.0f} MB (modello: "
                f"+{(dopo_modello - dopo_import) / mb:.0f} MB); "
                f"dopo 21 domande {dopo_domande / mb:.0f} MB"
            ),
            f"  caricamento del modello {caricamento:.1f} s",
            (
                f"  vettore di una domanda: mediana {statistics.median(durate):.1f} "
                f"ms, minimo {min(durate):.1f}, massimo {max(durate):.1f} "
                "(20 prove, CPU)"
            ),
            f"  su disco: {dimensione_su_disco(modello.nome) / mb:.0f} MB",
        ]
        if nome == "v0":
            # Il recupero locale dell'app senza Postgres e senza il modello di
            # linguaggio, su una copia: Chroma più l'indice BM25.
            from langchain_chroma import Chroma

            from src.config import COLLECTION_NAME

            store = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=embeddings,
                persist_directory=str(CARTELLA_19D / "v0" / "chroma"),
                collection_metadata={"hnsw:space": "cosine"},
            )
            recupero = apri_recupero(Path(), store=store)
            recupero.cerca("contributo per la musica?", k=10)
            linee.append(
                "  con il recupero locale su una copia (Chroma e BM25, 1187 "
                f"frammenti): {memoria_del_processo() / mb:.0f} MB"
            )
    print("\n".join(linee))
    return 0


# --- uso ---


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dividi", action="store_true", help="tempo 1: divisione")
    parser.add_argument("--misura", action="store_true", help="tempo 2: misura")
    parser.add_argument(
        "--riepilogo", action="store_true", help="una riga per configurazione misurata"
    )
    parser.add_argument(
        "--griglia",
        action="store_true",
        help="terzo giro: ampiezza e k sulla copia di --variante (v0 o v1)",
    )
    parser.add_argument(
        "--apistici",
        action="store_true",
        help="terzo giro: nome dell'azione dagli allegati e misura delle righe 67-74",
    )
    parser.add_argument(
        "--prepara-vettori",
        action="store_true",
        help="quarto giro: vettori dei frammenti di v0 per --modello",
    )
    parser.add_argument(
        "--esatta",
        action="store_true",
        help="quarto giro: misura con la ricerca densa esatta, k=10 e k=15",
    )
    parser.add_argument(
        "--peso", action="store_true", help="quarto giro: memoria e tempi del modello"
    )
    parser.add_argument("--modello", choices=sorted(MODELLI), default="v0")
    parser.add_argument(
        "--controllo",
        action="store_true",
        help="misura la metà di controllo invece della taratura (solo su istruzione)",
    )
    parser.add_argument("--foglio", type=Path, default=FOGLIO)
    parser.add_argument("--csv-controllo", type=Path, default=CONTROLLO_CSV)
    parser.add_argument("--uscita", type=Path, default=DIVISIONE)
    parser.add_argument("--divisione", type=Path, default=DIVISIONE)
    parser.add_argument("--variante", choices=sorted(VARIANTI), default="v0")
    parser.add_argument(
        "--cartella", type=Path, help="predefinita: dati-grezzi/prova/19d/<variante>"
    )
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
    comandi = (
        argomenti.dividi,
        argomenti.misura,
        argomenti.riepilogo,
        argomenti.griglia,
        argomenti.apistici,
        argomenti.prepara_vettori,
        argomenti.esatta,
        argomenti.peso,
    )
    if sum(comandi) != 1:
        print(
            "Serve un comando solo: --dividi, --misura, --riepilogo, --griglia, "
            "--apistici, --prepara-vettori, --esatta o --peso.",
            file=sys.stderr,
        )
        return 2
    try:
        if argomenti.dividi:
            return esegui_divisione(
                argomenti.foglio, argomenti.csv_controllo, argomenti.uscita
            )
        lato = CONTROLLO if argomenti.controllo else TARATURA
        if argomenti.riepilogo:
            return esegui_riepilogo(lato)
        if argomenti.griglia:
            return esegui_griglia(
                argomenti.foglio, argomenti.divisione, lato, argomenti.variante
            )
        if argomenti.apistici:
            return esegui_apistici(argomenti.foglio, argomenti.divisione, lato)
        if argomenti.prepara_vettori:
            return esegui_prepara_vettori(argomenti.modello)
        if argomenti.esatta:
            return esegui_esatta(
                argomenti.foglio, argomenti.divisione, lato, argomenti.modello
            )
        if argomenti.peso:
            return esegui_peso(argomenti.modello)
        cartella = argomenti.cartella or CARTELLA_19D / argomenti.variante
        return esegui_misura(
            argomenti.foglio, argomenti.divisione, lato, argomenti.variante, cartella
        )
    except (ErroreDivisione, ErroreMisura) as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
