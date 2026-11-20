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


def apri_recupero(copia: Path, limite: int | None = None):
    """RecuperoMisura sulla copia di Chroma: RecuperoIbrido più la ricerca per bando.

    Con `limite`, il modello di embedding delle domande usa quel limite di
    token (lo stesso con cui sono stati calcolati i vettori della copia).
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


class Profondo:
    """Il recupero con ampiezza PROFONDITA, da avvolgere come quello dell'app."""

    def __init__(self, base) -> None:
        self.base = base

    def titoli(self) -> dict[str, str]:
        return self.base.titoli()

    def cerca(self, domanda: str, k: int = 8, fonte: str | None = None) -> list:
        return self.base.cerca(domanda, k=k, ampiezza=PROFONDITA, fonte=fonte)


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
                f"Condizione {c}, da {base_nome} a {nome}: guadagnati "
                f"{len(guadagnati)} ({', '.join(guadagnati) or '-'}); persi "
                f"{len(persi)} ({', '.join(persi) or '-'})"
            ),
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


# --- uso ---


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dividi", action="store_true", help="tempo 1: divisione")
    parser.add_argument("--misura", action="store_true", help="tempo 2: misura")
    parser.add_argument(
        "--riepilogo", action="store_true", help="una riga per configurazione misurata"
    )
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
    if argomenti.dividi + argomenti.misura + argomenti.riepilogo != 1:
        print(
            "Serve un comando solo: --dividi, --misura o --riepilogo.", file=sys.stderr
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
        cartella = argomenti.cartella or CARTELLA_19D / argomenti.variante
        return esegui_misura(
            argomenti.foglio, argomenti.divisione, lato, argomenti.variante, cartella
        )
    except (ErroreDivisione, ErroreMisura) as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
