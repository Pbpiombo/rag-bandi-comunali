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
    codice_della_parte,
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

# Secondo foglio (114 fatti su 11 bandi): stesse regole, seme suo. Le righe
# con una frase identica o quasi (controlla_fatti.coincidenze) a una del
# primo foglio vanno nella metà di quella; le coppie quasi uguali dentro il
# secondo foglio stanno nella stessa metà, come i gruppi fissi del primo
# (decisione 6d). I fatti non trovati da controlla_fatti restano fuori.
SEME_2 = 2_2026_1120
FOGLIO_2 = DATI_GREZZI_DIR / "fatti_pdf_modello_2_2026-11-20.xlsx"
CONTROLLO_CSV_2 = DATI_GREZZI_DIR / "prova" / "fatti_controllo_2_2026-11-20.csv"
DIVISIONE_2 = DATI_GREZZI_DIR / "prova" / "fatti_divisione_2_2026-11-20.csv"

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
COLONNE_2 = [*COLONNE, "come_nel_primo_foglio"]


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
    vincoli: dict[int, str] | None = None,
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
    if vincoli and any(meta[r] != m for r, m in vincoli.items()):
        violate.append("vincoli")
    return violate


def proposta(
    rng: random.Random,
    per_bando: dict[str, list[int]],
    vincoli: dict[int, str] | None = None,
) -> dict[int, str]:
    """Per ogni bando, in ordine di nome: righe mescolate, la prima metà in taratura.

    Le righe con un vincolo hanno la loro metà; le altre del bando si
    mescolano e completano la taratura fino al numero estratto. Senza
    vincoli in un bando, le chiamate al generatore sono quelle di sempre
    (la divisione del primo foglio non cambia).
    """
    vincoli = vincoli or {}
    meta = {}
    for id_bando in sorted(per_bando):
        righe = sorted(per_bando[id_bando])
        fisse = [r for r in righe if r in vincoli]
        if not fisse:
            rng.shuffle(righe)
            quante = len(righe) // 2 + (rng.random() < 0.5 if len(righe) % 2 else 0)
            for indice, r in enumerate(righe):
                meta[r] = TARATURA if indice < quante else CONTROLLO
            continue
        libere = [r for r in righe if r not in vincoli]
        rng.shuffle(libere)
        quante = len(righe) // 2 + (rng.random() < 0.5 if len(righe) % 2 else 0)
        quante -= sum(vincoli[r] == TARATURA for r in fisse)
        for r in fisse:
            meta[r] = vincoli[r]
        for indice, r in enumerate(libere):
            meta[r] = TARATURA if indice < quante else CONTROLLO
    return meta


def dividi(
    fatti: list[dict],
    gemelli: set[int],
    seme: int = SEME,
    fissi: tuple[tuple[int, ...], ...] = GRUPPI_FISSI,
    condizioni: dict[str, int] | None = None,
    vincoli: dict[int, str] | None = None,
) -> tuple[dict[int, str], dict[int, int], int]:
    """(riga -> metà, riga -> gruppo, tentativi usati).

    `vincoli`: riga -> metà obbligata (secondo foglio: la metà della frase
    identica o quasi del primo).
    """
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
        meta = proposta(rng, per_bando, vincoli)
        violate = violazioni(
            meta, bando_di, gruppo_di, gemelli, insiemi, condizioni, vincoli
        )
        if not violate:
            return meta, gruppo_di, tentativo
        violata.update(violate)
        if len(violate) == 1:
            sola.update(violate)
    nomi = ["gruppi", "bandi", "gemelli", *condizioni] + (
        ["vincoli"] if vincoli else []
    )
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


def testo_csv(righe: list[dict], colonne: list[str] = COLONNE) -> bytes:
    uscita = io.StringIO(newline="")
    scrittore = csv.DictWriter(uscita, fieldnames=colonne, lineterminator="\n")
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


# --- secondo foglio ---


def coppie_quasi(fatti: list[dict]) -> tuple[tuple[int, ...], ...]:
    """Le coppie di righe dello stesso foglio con frase identica o quasi."""
    from scripts.diagnostica.controlla_fatti import coincidenze

    coppie = []
    for f in fatti:
        dopo = [g for g in fatti if g["riga"] > f["riga"]]
        coppie += [(f["riga"], r) for r, _ in coincidenze(f, dopo)]
    return tuple(coppie)


def vincoli_dal_primo(
    fatti: list[dict], primo: list[dict], meta_primo: dict[int, str]
) -> tuple[dict[int, str], dict[int, str]]:
    """(riga -> metà, riga -> descrizione) per le righe con una frase identica o
    quasi a una del primo foglio; ferma se le righe del primo stanno in metà
    diverse."""
    from scripts.diagnostica.controlla_fatti import coincidenze, formato_coincidenze

    vincoli, descrizioni = {}, {}
    for f in fatti:
        trovate = coincidenze(f, primo)
        if not trovate:
            continue
        lati = {meta_primo[r] for r, _ in trovate}
        if len(lati) > 1:
            raise ErroreDivisione(
                f"riga {f['riga']}: coincide con righe del primo foglio in metà "
                f"diverse ({formato_coincidenze(trovate)})"
            )
        vincoli[f["riga"]] = lati.pop()
        descrizioni[f["riga"]] = formato_coincidenze(trovate)
    return vincoli, descrizioni


def metà_del_primo(divisione: Path, righe: set[int]) -> dict[int, str]:
    """Dalla divisione del primo foglio (impronta verificata), solo la metà
    delle righe date: nient'altro della divisione si legge."""
    attesa = Path(f"{divisione}.sha256").read_text(encoding="utf-8").split()[0]
    if impronta(divisione.read_bytes()) != attesa:
        raise ErroreDivisione(
            f"{divisione.name}: impronta diversa da quella del .sha256"
        )
    with divisione.open(encoding="utf-8", newline="") as f:
        return {
            int(r["riga"]): r["meta"]
            for r in csv.DictReader(f)
            if int(r["riga"]) in righe
        }


def totali_del_primo(divisione: Path) -> Counter:
    """Quanti fatti per metà nella divisione del primo foglio."""
    with divisione.open(encoding="utf-8", newline="") as f:
        return Counter(r["meta"] for r in csv.DictReader(f))


def esegui_divisione_2() -> int:
    """La divisione del secondo foglio, con i vincoli dal primo."""
    from scripts.diagnostica.controlla_fatti import TROVATA

    fatti = leggi_foglio(FOGLIO_2)
    with CONTROLLO_CSV_2.open(encoding="utf-8-sig", newline="") as f:
        esiti = {int(r["riga"]): r["esito"] for r in csv.DictReader(f)}
    fuori = sorted(r for r, e in esiti.items() if e != TROVATA)
    fatti = [f for f in fatti if f["riga"] not in fuori]
    dati_controllo = {
        r: d for r, d in leggi_controllo(CONTROLLO_CSV_2).items() if r not in fuori
    }
    quasi = coppie_quasi(fatti)
    controlla_ingressi(fatti, dati_controllo, quasi)
    for f in fatti:
        f["visti"] = dati_controllo[f["riga"]]["visti"]
    gemelli = {r for r, d in dati_controllo.items() if d["gemello"]}

    primo = leggi_foglio(FOGLIO)
    from scripts.diagnostica.controlla_fatti import coincidenze

    righe_primo = {r for f in fatti for r, _ in coincidenze(f, primo)}
    vincoli, descrizioni = vincoli_dal_primo(
        fatti, primo, metà_del_primo(DIVISIONE, righe_primo)
    )
    meta, gruppo_di, tentativi = dividi(
        fatti, gemelli, seme=SEME_2, fissi=quasi, condizioni=CONDIZIONI, vincoli=vincoli
    )
    righe = righe_divisione(fatti, meta, gruppo_di, gemelli)
    for r in righe:
        r["come_nel_primo_foglio"] = descrizioni.get(r["riga"], "")
    dati = testo_csv(righe, COLONNE_2)

    print(f"Foglio: {FOGLIO_2.name} (sha256 {impronta(FOGLIO_2.read_bytes())})")
    print(
        f"Fuori dalla divisione (non trovati da controlla_fatti): {fuori or 'nessuno'}"
    )
    print(f"Coppie quasi uguali nel secondo foglio, nella stessa metà: {quasi}")
    print("Vincoli dal primo foglio:")
    for r, m in sorted(vincoli.items()):
        print(f"  riga {r} -> {m} ({descrizioni[r]})")
    print("\n".join(rapporto(righe, SEME_2, tentativi)))
    primo_tot = totali_del_primo(DIVISIONE)
    secondo_tot = Counter(r["meta"] for r in righe)
    print(
        f"\nTotali con il primo foglio: taratura {primo_tot[TARATURA]} + "
        f"{secondo_tot[TARATURA]} = {primo_tot[TARATURA] + secondo_tot[TARATURA]}; "
        f"controllo {primo_tot[CONTROLLO]} + {secondo_tot[CONTROLLO]} = "
        f"{primo_tot[CONTROLLO] + secondo_tot[CONTROLLO]}"
    )
    print()
    if DIVISIONE_2.exists():
        uguale = DIVISIONE_2.read_bytes() == dati
        print(
            f"{DIVISIONE_2.name} esiste già e non si sovrascrive: "
            + (
                "la divisione rifatta coincide."
                if uguale
                else "la divisione rifatta È DIVERSA."
            )
        )
        return 0 if uguale else 1
    DIVISIONE_2.write_bytes(dati)
    firma = impronta(dati)
    Path(f"{DIVISIONE_2}.sha256").write_text(
        f"{firma}  {DIVISIONE_2.name}\n", encoding="utf-8"
    )
    print(f"Scritto {DIVISIONE_2} (sha256 {firma})")
    return 0


# --- tempo 2: misura ---
#
# Un fatto è "trovato" se ogni suo pezzo sta, al livello senza spazi, in un
# frammento tra i primi K di un documento giusto: un file del bando (per
# gli apistici, il file dell'allegato della nota). Per una riga di tabella
# il pezzo è l'insieme delle sue celle, tutte nello stesso frammento.

K = 10
AMPIEZZA_APP = 20  # quella di RecuperoIbrido.cerca, usata dall'app
PESO_DENSA = 0.5  # peso della ricerca per significato nella fusione di oggi
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
            r["nome_file"]
            for r in del_bando
            if codice_della_parte(r["parte"]) == nota[1]
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
    contesti: dict[tuple[str, int], str] | None = None,
):
    """RecuperoMisura sulla copia di Chroma: RecuperoIbrido più la ricerca per bando.

    Con `contesti` (testo per (fonte, chunk_num)) la ricerca per parole
    indicizza anche il contesto del frammento (testo_con_contesto).

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
                    tokenizza(
                        testo_con_contesto(
                            testo_lessicale(d.page_content, d.metadata, prefissi),
                            d.metadata,
                            contesti,
                        )
                    )
                    for d in self.documenti
                ]
            )

        def cerca_nel_bando(
            self,
            domanda: str,
            id_bando: str,
            k: int,
            ampiezza: int = AMPIEZZA_APP,
            peso: float = PESO_DENSA,
        ) -> list:
            """Come cerca, solo tra i frammenti del bando; BM25 pesato su tutto l'indice.

            `peso` è il peso della ricerca per significato nella fusione RRF
            (quella per parole ha 1 - peso); con 0,5 i punteggi sono quelli
            di RecuperoIbrido.
            """
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
            pesi = {"densa": 2 * peso, "lessicale": 2 * (1 - peso)}
            for nome, elenco in (("densa", densa), ("lessicale", lessicale)):
                for pos, documento in enumerate(elenco, start=1):
                    voce = punti.setdefault(
                        chiave_di(documento),
                        {"doc": documento, "punteggio": 0.0, "origini": []},
                    )
                    voce["punteggio"] += pesi[nome] / (COSTANTE_RRF + pos)
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


def testo_con_contesto(
    testo: str, meta: dict, contesti: dict[tuple[str, int], str] | None
) -> str:
    """Il testo con il contesto del suo frammento davanti, se c'è (passo 19d).

    `contesti` è per (fonte, chunk_num); il testo del frammento restituito
    dalla ricerca resta quello della copia.
    """
    chiave = (meta.get("fonte") or "", meta.get("chunk_num"))
    contesto = (contesti or {}).get(chiave)
    return f"{contesto}\n{testo}" if contesto else testo


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
        codice = codice_della_parte(r["parte"])
        if codice is None:
            continue
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
    prefissi che il modello vuole davanti a domanda e frammenti;
    intestazione: titolo · parte · atto davanti al testo del vettore degli
    avvisi, come la variante v2 (testo_per_vettore); cartella: dove stanno
    vettori e misure, sotto CARTELLA_19D (vuota: il nome del modello).
    """

    nome: str
    limite: int | None = None
    domanda: str = ""
    passaggio: str = ""
    intestazione: bool = False
    cartella: str = ""
    # parte: la parte del registro ("Azione B1: <nome>") davanti al testo del
    # vettore e della ricerca per parole, solo per i file che ne hanno una
    # con il nome (parti_del_registro); il testo del frammento resta pulito
    parte: bool = False
    # contesto: le righe del contesto per frammento (RIGHE_CONTESTO) davanti
    # al testo del vettore dei frammenti degli avvisi che ne hanno uno
    contesto: str = ""


MINILM = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODELLI: dict[str, Modello] = {
    "v0": Modello(MINILM),
    # le varianti v1, v2 e v1+v2 (VARIANTI) con la ricerca esatta, sui
    # frammenti di v0; misure della notte del 20/11/2026
    "v1": Modello(MINILM, 512, cartella="notte/v1"),
    "v2": Modello(MINILM, intestazione=True, cartella="notte/v2"),
    "v1+v2": Modello(MINILM, 512, intestazione=True, cartella="notte/v1+v2"),
    "e5-small": Modello("intfloat/multilingual-e5-small", 512, "query: ", "passage: "),
    "e5-base": Modello("intfloat/multilingual-e5-base", 512, "query: ", "passage: "),
    # v0 con il nome dell'azione degli apistici (21/11/2026): vettori di v0,
    # ricalcolati solo i frammenti dei file con la parte
    "v0+parte": Modello(MINILM, parte=True, cartella="v0+parte97"),
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


def cartella_modello(nome: str) -> Path:
    return CARTELLA_19D / (MODELLI[nome].cartella or nome)


def testi_dei_vettori(modello: Modello, testi: list[str], metadati: list[dict]):
    """I testi su cui il modello calcola i vettori: intestazione, poi prefisso."""
    return testi_con_prefisso(
        [
            testo_per_vettore(t, m, modello.intestazione)
            for t, m in zip(testi, metadati, strict=True)
        ],
        modello.passaggio,
    )


def parti_del_registro(righe: list[dict] | None = None) -> dict[str, str]:
    """Nome del file -> parte, per i file del registro con il nome dell'azione.

    Solo le parti nella forma "Azione B1: <nome>" (registra_avvisi); una
    parte con il solo codice non entra. Senza `righe` si legge il registro
    di data/processed.
    """
    if righe is None:
        from scripts.ingestione import carica_avvisi as ca
        from scripts.ingestione.registra_avvisi import NOME_FILE
        from src.config import PROCESSED_DIR

        righe = ca.leggi_registro(PROCESSED_DIR / NOME_FILE)
    return {
        r["nome_file"]: r["parte"]
        for r in righe
        if codice_della_parte(r["parte"]) and ":" in r["parte"]
    }


def vettori_con_la_parte(
    ids, testi, metadati, matrice, parti: dict[str, str], embeddings
):
    """La matrice di v0 con i vettori ricalcolati, parte davanti, per i file in `parti`.

    Prima di ricalcolare controlla che lo stesso modello, sui testi senza
    parte, ridia i vettori di v0 (scarto massimo restituito); poi sostituisce
    solo le righe dei file in `parti`. Restituisce (matrice, indici
    ricalcolati, scarto).
    """
    import numpy as np

    indici = [i for i, m in enumerate(metadati) if (m.get("fonte") or "") in parti]
    if {metadati[i]["fonte"] for i in indici} != set(parti):
        raise ErroreMisura("file con la parte senza frammenti tra quelli di v0")
    nuova = np.array(matrice, dtype=np.float32, copy=True)
    senza = np.asarray(embeddings.embed_documents([testi[i] for i in indici]))
    scarto = float(np.max(np.abs(senza - nuova[indici])))
    if scarto > TOLLERANZA_NORMA:
        raise ErroreMisura(
            f"il modello non ridà i vettori di v0 (scarto {scarto:.2e}): "
            "non si ricalcola"
        )
    con = embeddings.embed_documents(
        [testo_lessicale(testi[i], metadati[i], parti) for i in indici]
    )
    nuova[indici] = np.asarray(con, dtype=np.float32)
    return nuova, indici, scarto


def esegui_prepara_vettori(nome: str) -> int:
    """v0: vettori letti dalla copia di v0; gli altri: ricalcolati con il modello.

    v0+parte: i vettori di v0, ricalcolati solo per i file con la parte.
    """
    import time

    import numpy as np

    from scripts.ingestione.carica_avvisi import senza_rete

    senza_rete()
    modello = MODELLI[nome]
    cartella = cartella_modello(nome)
    inizio = time.perf_counter()
    nota = ""
    with senza_connessioni():
        if modello.parte:
            ids, testi, metadati, matrice = leggi_vettori(CARTELLA_19D / "v0")
            parti = parti_del_registro()
            matrice, indici, scarto_v0 = vettori_con_la_parte(
                ids, testi, metadati, matrice, parti, crea_embeddings_di(modello)
            )
            nota = (
                f"; ricalcolati {len(indici)} frammenti di {len(parti)} file "
                f"(scarto dai vettori di v0 senza parte {scarto_v0:.2e})"
            )
        elif nome == "v0":
            copia = CARTELLA_19D / "v0" / "chroma"
            ids, testi, metadati, matrice = esporta_frammenti(copia)
        elif modello.contesto:
            ids, testi, metadati, _ = leggi_vettori(CARTELLA_19D / "v0")
            contesti = contesti_per_frammento(modello.contesto)
            embeddings = crea_embeddings_di(modello)
            matrice = embeddings.embed_documents(
                [
                    testo_con_contesto(t, m, contesti)
                    for t, m in zip(testi, metadati, strict=True)
                ]
            )
            nota = f"; {len(contesti)} frammenti con il contesto davanti"
        else:
            ids, testi, metadati, _ = leggi_vettori(CARTELLA_19D / "v0")
            embeddings = crea_embeddings_di(modello)
            matrice = embeddings.embed_documents(
                testi_dei_vettori(modello, testi, metadati)
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
        f"{time.perf_counter() - inizio:.1f} s{nota}"
    )
    return 0


def apri_recupero_esatto(nome: str):
    """RecuperoMisura sui vettori della cartella del modello, con ricerca esatta."""
    modello = MODELLI[nome]
    ids, testi, metadati, matrice = leggi_vettori(cartella_modello(nome))
    embeddings = crea_embeddings_di(modello)
    store = StoreEsatto(ids, testi, metadati, matrice, embeddings, modello.domanda)
    prefissi = parti_del_registro() if modello.parte else None
    return apri_recupero(Path(), store=store, prefissi=prefissi)


def visti_con_prefisso(
    frammenti_per_fonte: dict[str, list[Frammento]],
    prefissi: dict[str, str],
    tokenizer,
    limite: int,
) -> None:
    """car_visti dei frammenti con il prefisso: i caratteri del testo che il
    modello vede dopo il prefisso e l'a capo (testo_lessicale), entro `limite`."""
    for fonte, prefisso in prefissi.items():
        for fr in frammenti_per_fonte.get(fonte, []):
            visti = car_visti(tokenizer, f"{prefisso}\n{fr.testo}", limite)
            fr.car_visti = max(0, visti - len(prefisso) - 1)


def apri_tutto_esatto(nome: str):
    """(recupero, app, profondo, frammenti per fonte, titolo per bando) di un modello."""
    from src.recupero_documenti import avvolgi

    modello = MODELLI[nome]
    recupero = apri_recupero_esatto(nome)
    app = avvolgi(recupero)
    profondo = avvolgi(Profondo(recupero))
    frammenti_per_fonte, titolo_del_bando = frammenti_della_copia(
        recupero, modello.limite
    )
    if modello.parte:
        visti_con_prefisso(
            frammenti_per_fonte,
            parti_del_registro(),
            recupero.store.embeddings._client.tokenizer,
            modello.limite or LIMITE_MODELLO,
        )
    return recupero, app, profondo, frammenti_per_fonte, titolo_del_bando


def esegui_esatta(foglio: Path, divisione: Path, lato: str, nome: str) -> int:
    """Misura esatta con k=10 e k=15, condizioni A e B (B ripulita)."""
    import json
    import time

    from scripts.ingestione.carica_avvisi import senza_rete
    from src.config import CHROMA_DIR

    senza_rete()
    modello = MODELLI[nome]
    cartella = cartella_modello(nome)
    firma, fatti, file_per_bando = apri_misura(foglio, divisione, lato)
    prima = impronte_cartella(CHROMA_DIR)
    tempi = {}
    with senza_connessioni():
        inizio = time.perf_counter()
        recupero, app, profondo, frammenti_per_fonte, titolo_del_bando = (
            apri_tutto_esatto(nome)
        )
        tempi["apertura"] = time.perf_counter() - inizio

        inizio = time.perf_counter()
        righe, elenchi_scritti = ricerche_esatte(
            recupero,
            app,
            profondo,
            fatti,
            file_per_bando,
            frammenti_per_fonte,
            titolo_del_bando,
        )
        tempi["ricerche"] = time.perf_counter() - inizio
        del recupero, app, profondo
    if impronte_cartella(CHROMA_DIR) != prima:
        raise ErroreMisura("le impronte del Chroma vero sono cambiate")

    testo_elenchi = json.dumps(elenchi_scritti, ensure_ascii=False, indent=0).encode()
    (cartella / f"elenchi_esatti_{lato}.json").write_bytes(testo_elenchi)
    for k in K_ESATTI:
        scrivi_misura(cartella / f"esatta_k{k}_{lato}.csv", righe[k])

    intestazione = [
        f"Passo 19d, quarto giro, misura esatta {nome}, metà: {lato}",
        f"Divisione: {divisione.name} (sha256 {firma})",
        NOTA_REGOLA,
        descrizione_modello(modello),
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


def descrizione_modello(modello: Modello) -> str:
    return (
        f"Modello {modello.nome}, limite {modello.limite or LIMITE_MODELLO} token, "
        f"prefisso della domanda {modello.domanda!r}, dei frammenti "
        f"{modello.passaggio!r}"
        + ("; intestazione nel vettore" if modello.intestazione else "")
        + (
            "; parte del registro davanti al testo del vettore e della ricerca per "
            "parole, solo per i file con il nome dell'azione; testo del frammento "
            "pulito"
            if modello.parte
            else ""
        )
        + (
            f"; contesto per frammento ({modello.contesto}) davanti al testo del "
            "vettore degli avvisi; testo del frammento pulito"
            if modello.contesto
            else ""
        )
        + "; ricerca densa esatta (prodotto scalare su tutti i frammenti, pari "
        "merito per id)"
    )


def scrivi_misura(percorso: Path, righe: list[dict]) -> None:
    with percorso.open("w", encoding="utf-8", newline="") as f:
        scrittore = csv.DictWriter(
            f, fieldnames=COLONNE_MISURA, lineterminator="\n", restval=""
        )
        scrittore.writeheader()
        scrittore.writerows(righe)


def ricerche_esatte(
    recupero,
    app,
    profondo,
    fatti,
    file_per_bando,
    frammenti_per_fonte,
    titolo_del_bando,
) -> tuple[dict[int, list[dict]], dict[str, list]]:
    """Per ogni fatto e ogni k di K_ESATTI, le righe della misura (A e B) e gli elenchi."""
    from src.chains.rag import recupera
    from src.recupero_documenti import documenti_nominati
    from src.retrieval import normalizza_domanda

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
            _, spezzati_, assenti = stato_dei_pezzi(fatto, giusti, frammenti_per_fonte)
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
    return righe, elenchi_scritti


def leggi_esatta(nome: str, k: int, lato: str) -> list[dict] | None:
    percorso = cartella_modello(nome) / f"esatta_k{k}_{lato}.csv"
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


# --- quinto giro: taratura intera (primo e secondo foglio) ---

# I numeri di riga dei due fogli si sovrappongono: nella misura sui due
# fogli le righe del secondo si spostano di SCOSTAMENTO_2 (riga 18 del
# secondo foglio -> 1018). Le righe del primo restano quelle di sempre.
SCOSTAMENTO_2 = 1000
SUFFISSO_INTERA = "97"
MODELLI_INTERA = ("v0", "e5-small", "e5-base")

# Cause dei non trovati, per fatto: la prima che si applica, in quest'ordine
CAUSA_SPEZZATO = "pezzo spezzato tra frammenti"
CAUSA_ASSENTE = "pezzo in nessun frammento del documento giusto"
CAUSA_FUORI_VISTA = "pezzo fuori dalla parte vista"
CAUSA_GEMELLO = "gemello al posto del giusto"
# Posizione del pezzo messo peggio nella ricerca con ampiezza PROFONDITA,
# che non coincide con la posizione nei primi k (ampiezza dell'app)
CAUSA_OLTRE_15 = "giusto entro il 15° posto con ampiezza 50"
CAUSA_OLTRE_30 = "giusto dal 16° al 30° posto con ampiezza 50"
CAUSA_OLTRE_50 = "giusto dal 31° al 50° posto con ampiezza 50"
CAUSA_OLTRE = "giusto oltre i primi 50"
FASCE = (CAUSA_OLTRE_15, CAUSA_OLTRE_30, CAUSA_OLTRE_50, CAUSA_OLTRE)
SENZA_POSIZIONE = "senza posizione"
ORDINE_CAUSE = (
    CAUSA_SPEZZATO,
    CAUSA_ASSENTE,
    CAUSA_FUORI_VISTA,
    CAUSA_GEMELLO,
    CAUSA_OLTRE_15,
    CAUSA_OLTRE_30,
    CAUSA_OLTRE_50,
    CAUSA_OLTRE,
)


def unisci_fogli(fatti_per_foglio: list[tuple[list[dict], int]]) -> list[dict]:
    """I fatti di più fogli in un elenco solo, con la riga spostata e il foglio.

    Ogni voce è (fatti, scostamento); il foglio è la posizione nell'elenco,
    da 1. Due fatti con la stessa riga dopo lo spostamento fermano.
    """
    uniti = []
    for numero, (fatti, scostamento) in enumerate(fatti_per_foglio, 1):
        uniti += [
            {**f, "riga": f["riga"] + scostamento, "foglio": numero} for f in fatti
        ]
    doppie = [r for r, n in Counter(f["riga"] for f in uniti).items() if n > 1]
    if doppie:
        raise ErroreMisura(f"righe uguali tra i fogli: {sorted(doppie)}")
    return uniti


def foglio_della_riga(riga) -> int:
    return 2 if int(riga) >= SCOSTAMENTO_2 else 1


def nome_della_riga(riga) -> str:
    """'18' per il primo foglio, '2:18' per il secondo."""
    numero = int(riga)
    return f"2:{numero - SCOSTAMENTO_2}" if numero >= SCOSTAMENTO_2 else str(numero)


def file_intera(nome: str, k: int, lato: str) -> Path:
    return cartella_modello(nome) / f"esatta_k{k}_{lato}_{SUFFISSO_INTERA}.csv"


def esegui_esatta_intera(lato: str, nome: str) -> int:
    """Misura esatta sui due fogli insieme, k=10 e k=15, condizioni A e B."""
    import json
    import time

    from scripts.ingestione.carica_avvisi import senza_rete
    from src.config import CHROMA_DIR

    senza_rete()
    cartella = cartella_modello(nome)
    firma_1, fatti_1, file_per_bando = apri_misura(FOGLIO, DIVISIONE, lato)
    firma_2, fatti_2, _ = apri_misura(FOGLIO_2, DIVISIONE_2, lato)
    fatti = unisci_fogli([(fatti_1, 0), (fatti_2, SCOSTAMENTO_2)])
    prima = impronte_cartella(CHROMA_DIR)
    tempi = {}
    with senza_connessioni():
        inizio = time.perf_counter()
        recupero, app, profondo, frammenti_per_fonte, titolo_del_bando = (
            apri_tutto_esatto(nome)
        )
        tempi["apertura"] = time.perf_counter() - inizio
        inizio = time.perf_counter()
        righe, elenchi_scritti = ricerche_esatte(
            recupero,
            app,
            profondo,
            fatti,
            file_per_bando,
            frammenti_per_fonte,
            titolo_del_bando,
        )
        tempi["ricerche"] = time.perf_counter() - inizio
        del recupero, app, profondo
    if impronte_cartella(CHROMA_DIR) != prima:
        raise ErroreMisura("le impronte del Chroma vero sono cambiate")

    testo_elenchi = json.dumps(elenchi_scritti, ensure_ascii=False, indent=0).encode()
    nome_elenchi = f"elenchi_esatti_{lato}_{SUFFISSO_INTERA}.json"
    (cartella / nome_elenchi).write_bytes(testo_elenchi)
    for k in K_ESATTI:
        scrivi_misura(file_intera(nome, k, lato), righe[k])
    linee = [
        (
            f"Passo 19d, misura esatta {nome} sui due fogli, metà: {lato} "
            f"({len(fatti_1)} + {len(fatti_2)} fatti)"
        ),
        (
            f"Divisioni: {DIVISIONE.name} (sha256 {firma_1}), "
            f"{DIVISIONE_2.name} (sha256 {firma_2})"
        ),
        f"Righe del secondo foglio spostate di {SCOSTAMENTO_2} nei CSV",
        NOTA_REGOLA,
        descrizione_modello(MODELLI[nome]),
        f"Elenchi recuperati: {nome_elenchi}, sha256 {impronta(testo_elenchi)}",
        f"Chroma vero: {len(prima)} file, impronte uguali prima e dopo",
        "Tempi: " + "; ".join(f"{n} {s:.1f} s" for n, s in tempi.items()),
        "",
    ]
    scritte = {k: leggi_misura(file_intera(nome, k, lato)) for k in K_ESATTI}
    linee += tabella_affiancata(
        [(f"k={k} {c}", scritte[k], c) for k in K_ESATTI for c in CONDIZIONI_GRIGLIA]
    )
    testo = "\n".join(linee)
    (cartella / f"esatta_{lato}_{SUFFISSO_INTERA}.txt").write_text(
        testo + "\n", encoding="utf-8"
    )
    print(testo)
    return 0


def causa_del_fatto(cause: str) -> str:
    """La causa principale di un fatto non trovato, dalla colonna <c>_cause.

    Per le posizioni conta il pezzo messo peggio.
    """
    if SPEZZATO in cause:
        return CAUSA_SPEZZATO
    if ASSENTE_FRAMMENTI in cause:
        return CAUSA_ASSENTE
    if FUORI_VISTA in cause:
        return CAUSA_FUORI_VISTA
    if GEMELLO in cause:
        return CAUSA_GEMELLO
    return fascia_di_posizione(cause)


def fascia_di_posizione(cause: str) -> str:
    """La fascia della posizione profonda del pezzo messo peggio."""
    if f"oltre i primi {PROFONDITA}" in cause:
        return CAUSA_OLTRE
    posizioni = [int(p) for p in re.findall(r"in posizione (\d+)", cause)]
    if not posizioni:
        raise ErroreMisura(f"causa non riconosciuta: {cause!r}")
    peggiore = max(posizioni)
    if peggiore <= 15:
        return CAUSA_OLTRE_15
    if peggiore <= 30:
        return CAUSA_OLTRE_30
    return CAUSA_OLTRE_50


def differenza(prima: int, dopo: int) -> str:
    """'+n', '-n' o '0'. Se lo scarto è casuale lo dice il test dei segni
    (nota_dei_segni), non una soglia fissa: la soglia di 3 fatti è tolta il
    21/11/2026."""
    scarto = dopo - prima
    return f"{scarto:+d}" if scarto else "0"


def nota_dei_segni(guadagnati: int, persi: int) -> str:
    """'p = …', con "entro il rumore" se p > SOGLIA_CASO (test esatto dei segni)."""
    p = probabilita_segni(guadagnati, persi)
    return f"p = {_virgola(p)}" + ("; entro il rumore" if p > SOGLIA_CASO else "")


def _trovati(righe: list[dict], c: str, scelta=lambda r: True) -> tuple[int, int]:
    sue = [r for r in righe if scelta(r)]
    return sum(r[f"{c}_trovato"] == "sì" for r in sue), len(sue)


def _primi_entro(righe: list[dict], c: str, posto: int) -> int:
    return sum(
        bool(r[f"{c}_primo_giusto"]) and int(r[f"{c}_primo_giusto"]) <= posto
        for r in righe
    )


GRUPPI_INTERA = [
    ("tutti", lambda r: True),
    ("primo foglio", lambda r: foglio_della_riga(r["riga"]) == 1),
    ("secondo foglio", lambda r: foglio_della_riga(r["riga"]) == 2),
    ("un pezzo", lambda r: int(r["pezzi"]) == 1),
    ("più pezzi", lambda r: int(r["pezzi"]) > 1),
    ("tabella sì", lambda r: r["in_tabella"] == "sì"),
    ("tabella no", lambda r: r["in_tabella"] != "sì"),
    ("registro semplice", lambda r: r["registro"] == "semplice"),
    ("registro caso", lambda r: r["registro"] == "caso"),
    ("frasi gemelle", lambda r: r["gemello"] == "sì"),
]


def gemelli_presi(righe: list[dict], c: str) -> tuple[list[str], list[str]]:
    """(frasi gemelle prese dal gemello, altri fatti presi dal gemello), come righe."""
    presi = [r for r in righe if r[f"{c}_pezzo_dal_gemello"] == "sì"]
    return (
        [nome_della_riga(r["riga"]) for r in presi if r["gemello"] == "sì"],
        [nome_della_riga(r["riga"]) for r in presi if r["gemello"] != "sì"],
    )


def righe_diverse_dal_primo(vecchie: list[dict], nuove: list[dict]) -> list[str]:
    """Le righe del primo foglio la cui misura sui due fogli differisce da quella sui 40."""
    del_primo = {r["riga"]: r for r in nuove if foglio_della_riga(r["riga"]) == 1}
    if set(del_primo) != {r["riga"] for r in vecchie}:
        raise ErroreMisura("le righe del primo foglio non sono le stesse")
    return [r["riga"] for r in vecchie if del_primo[r["riga"]] != r]


def rapporto_intero(
    misure: dict[tuple[str, int], list[dict]], lato: str, confronti: bool = True
) -> list[str]:
    """Il riepilogo delle misure sui due fogli; misure per (modello, k).

    Con confronti=False la sezione 4 non c'è: i confronti li scrive chi
    chiama. Nella sezione 4 lo scarto si giudica con il test dei segni.
    """
    configurazioni = list(misure)
    etichette = [f"{n} k={k}" for n, k in configurazioni]
    larga = 24
    linee = [
        f"Passo 19d, riepilogo della misura esatta sui due fogli, metà: {lato}",
        NOTA_REGOLA,
        "Righe del secondo foglio scritte come 2:<riga>."
        + (f" {NOTA_SEGNI}" if confronti else ""),
        "",
        "1. Fatti trovati, A / B, su n fatti",
        f"{'':<{larga}}{'n':>4}" + "".join(f"{e:>18}" for e in etichette),
    ]
    prime = next(iter(misure.values()))
    for gruppo, scelta in GRUPPI_INTERA:
        celle = [
            f"{_trovati(righe, 'A', scelta)[0]} / {_trovati(righe, 'B', scelta)[0]}"
            for righe in misure.values()
        ]
        n = _trovati(prime, "A", scelta)[1]
        linee.append(f"{gruppo:<{larga}}{n:>4}" + "".join(f"{x:>18}" for x in celle))

    linee += ["", "2. Posizione del primo frammento giusto, A / B (fatti, cumulati)"]
    linee.append(f"{'':<{larga}}" + "".join(f"{e:>18}" for e in etichette))
    for posto in (1, 3, 5, 10, 15):
        celle = []
        for (_, k), righe in misure.items():
            if posto > k:
                celle.append("-")
            else:
                celle.append(
                    f"{_primi_entro(righe, 'A', posto)} / {_primi_entro(righe, 'B', posto)}"
                )
        nome = "al 1° posto" if posto == 1 else f"tra i primi {posto}"
        linee.append(f"{nome:<{larga}}" + "".join(f"{x:>18}" for x in celle))

    linee += ["", "3. Pezzi presi dal bando (o allegato) sbagliato prima del giusto"]
    for etichetta, righe in zip(etichette, misure.values(), strict=True):
        for c in CONDIZIONI_GRIGLIA:
            gemelle, altri = gemelli_presi(righe, c)
            senza = [
                nome_della_riga(r["riga"])
                for r in righe
                if r[f"{c}_gemello_senza_giusto"] == "sì"
            ]
            linee.append(
                f"  {etichetta:<14} {c}: frasi gemelle {len(gemelle)} "
                f"({', '.join(gemelle) or '-'}); altri fatti {len(altri)} "
                f"({', '.join(altri) or '-'}); gemello tra i primi k senza il "
                f"giusto {len(senza)} ({', '.join(senza) or '-'})"
            )

    if confronti:
        linee += ["", "4. Differenze dalla base v0 con lo stesso k (fatti trovati)"]
        for (n, k), righe in misure.items():
            if n == "v0" or ("v0", k) not in misure:
                continue
            base = misure[("v0", k)]
            for c in CONDIZIONI_GRIGLIA:
                guadagnati, persi = cambi_di_esito(base, righe, c)
                linee.append(
                    f"  {n} k={k} {c}: {_trovati(righe, c)[0]} contro "
                    f"{_trovati(base, c)[0]}, "
                    f"{differenza(_trovati(base, c)[0], _trovati(righe, c)[0])}; "
                    f"ora trovati {', '.join(map(nome_della_riga, guadagnati)) or '-'}; "
                    f"ora non trovati {', '.join(map(nome_della_riga, persi)) or '-'}; "
                    f"{nota_dei_segni(len(guadagnati), len(persi))}"
                )
        for n in dict.fromkeys(n for n, _ in configurazioni):
            if (n, K) in misure and (n, 15) in misure:
                for c in CONDIZIONI_GRIGLIA:
                    guadagnati, persi = cambi_di_esito(
                        misure[(n, K)], misure[(n, 15)], c
                    )
                    prima_ = _trovati(misure[(n, K)], c)[0]
                    dopo = _trovati(misure[(n, 15)], c)[0]
                    linee.append(
                        f"  {n} da k={K} a k=15 {c}: {differenza(prima_, dopo)}; "
                        f"ora trovati {len(guadagnati)}, ora non trovati {len(persi)} "
                        f"({', '.join(map(nome_della_riga, persi)) or '-'}); "
                        f"{nota_dei_segni(len(guadagnati), len(persi))}"
                    )
    else:
        linee += ["", "4. Confronti: più sotto, con il test esatto dei segni"]

    bandi = sorted({r["id_bando"] for righe in misure.values() for r in righe})
    largo = max(len(b) for b in bandi) + 1
    linee += ["", "5. Risultati per bando, trovati A / B su n fatti"]
    linee.append(f"{'':<{largo}}{'n':>4}" + "".join(f"{e:>18}" for e in etichette))
    for bando in bandi:
        celle = []
        for righe in misure.values():
            a, n = _trovati(righe, "A", lambda r, b=bando: r["id_bando"] == b)
            b_, _ = _trovati(righe, "B", lambda r, b=bando: r["id_bando"] == b)
            celle.append(f"{a} / {b_}")
        linee.append(f"{bando:<{largo}}{n:>4}" + "".join(f"{x:>18}" for x in celle))

    if ("v0", K) in misure:
        mancati = [r for r in misure[("v0", K)] if r["B_trovato"] != "sì"]
        per_causa = defaultdict(list)
        for r in mancati:
            per_causa[causa_del_fatto(r["B_cause"])].append(r)
        linee += [
            "",
            (
                f"6. Non trovati in v0, condizione B, k={K}: {len(mancati)}, divisi "
                "per causa (la prima che si applica: spezzato, assente, fuori dalla "
                "parte vista, gemello al posto del giusto, posizione del pezzo "
                "messo peggio)"
            ),
        ]
        for causa in ORDINE_CAUSE:
            sue = per_causa.get(causa, [])
            if not sue:
                continue
            fasce = Counter(
                fascia_di_posizione(r["B_cause"])
                if re.search(r"in posizione \d|oltre i primi", r["B_cause"])
                else SENZA_POSIZIONE
                for r in sue
            )
            dettaglio = (
                " ("
                + "; ".join(
                    f"{f} {fasce[f]}" for f in (*FASCE, SENZA_POSIZIONE) if fasce[f]
                )
                + ")"
                if causa not in FASCE
                else ""
            )
            linee.append(f"  {causa}: {len(sue)}{dettaglio}")
            linee += [
                f"    {nome_della_riga(r['riga'])} ({r['id_bando']}, {r['registro']}, "
                f"pezzi {r['pezzi']}, tabella {r['in_tabella'] or 'no'}): "
                f"{r['B_cause']}"
                for r in sue
            ]
    return linee


def esegui_riepilogo_intero(lato: str) -> int:
    """riepilogo_<lato>_97.txt dalle misure sui due fogli, più il confronto con i 40."""
    misure = {
        (n, k): leggi_misura(file_intera(n, k, lato))
        for n in MODELLI_INTERA
        for k in K_ESATTI
        if file_intera(n, k, lato).exists()
    }
    if not misure:
        raise ErroreMisura("nessuna misura sui due fogli da riassumere")
    linee = rapporto_intero(misure, lato)
    linee += ["", "7. Righe del primo foglio uguali alla misura esatta sui 40"]
    for (n, k), righe in misure.items():
        vecchie = leggi_esatta(n, k, lato)
        if vecchie is None:
            linee.append(f"  {n} k={k}: misura sui 40 assente")
            continue
        diverse = righe_diverse_dal_primo(vecchie, righe)
        linee.append(
            f"  {n} k={k}: {len(vecchie) - len(diverse)} su {len(vecchie)} identiche"
            + (f"; diverse: {', '.join(diverse)}" if diverse else "")
        )
    testo = "\n".join(linee)
    (CARTELLA_19D / f"riepilogo_{lato}_{SUFFISSO_INTERA}.txt").write_text(
        testo + "\n", encoding="utf-8"
    )
    print(testo)
    return 0


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


# --- notte del 20/11/2026: sola taratura intera, misura esatta ---
#
# Parte 1: v1, v2 e v1+v2 con la ricerca esatta (--prepara-vettori e
# --esatta-intera con --modello), confronti con il test dei segni.
# Parte 2: curve su k e sul peso della fusione, token dei documenti, costi
# del contesto per frammento, risultati per bando e per allegato.
# Parte 3: risposte in più pezzi, vicini e pagina intera.
# Parte 4: riordinatore su 30 candidati.
# Uscite in NOTTE.

NOTTE = CARTELLA_19D / "notte"
SOGLIA_CASO = 0.05
MODELLI_NOTTE = ("v0", "v1", "v2", "v1+v2", "e5-small", "e5-base")
MODELLI_CURVE = ("v0", "e5-small")
K_CURVA = (5, 8, 10, 12, 15, 20, 25, 30)
PESI_CURVA = (0.5, 0.6, 0.7, 0.8, 0.9)
VICINI_NOTTE = (1, 2, 3, 5)
ISTRUZIONE_CONTESTO = 60  # token di istruzione per frammento (parte 2d)
USCITA_CONTESTO = 100  # token in uscita per frammento (parte 2d)
CANDIDATI = 30
RIORDINATORI = {
    "osiria": "osiria/minilm-l12-h384-italian-cross-encoder",
    "mmarco": "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
}
# I file che si scaricano di un riordinatore: niente codice, niente varianti
# onnx o openvino
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
NOTA_SEGNI = (
    "p: test esatto dei segni a due code sulle coppie discordanti (fatti "
    "trovati da una sola delle due configurazioni); 'entro il rumore' se "
    "p > 0,05."
)


def probabilita_segni(guadagnati: int, persi: int) -> float:
    """Test esatto dei segni, a due code, sulle coppie discordanti."""
    import math

    n = guadagnati + persi
    if n == 0:
        return 1.0
    coda = sum(math.comb(n, i) for i in range(min(guadagnati, persi) + 1))
    return min(1.0, 2 * coda / 2**n)


def _virgola(x: float, cifre: int = 3) -> str:
    return f"{x:.{cifre}f}".replace(".", ",")


def _segni(guadagnati: list[str], persi: list[str]) -> str:
    return (
        f"guadagnati {len(guadagnati)} ({', '.join(guadagnati) or '-'}); persi "
        f"{len(persi)} ({', '.join(persi) or '-'}); "
        + nota_dei_segni(len(guadagnati), len(persi))
    )


def riga_segni(
    nome_base: str, base: list[dict], nome: str, variante: list[dict], c: str
) -> str:
    """Guadagnati, persi e probabilità che lo scarto sia casuale."""
    guadagnati, persi = cambi_di_esito(base, variante, c)
    return (
        f"  {nome} contro {nome_base}, {c}: {_trovati(variante, c)[0]} contro "
        f"{_trovati(base, c)[0]}; "
        + _segni(
            [nome_della_riga(r) for r in guadagnati],
            [nome_della_riga(r) for r in persi],
        )
    )


def coppie_della_parte_1() -> list[tuple[tuple[str, int], tuple[str, int]]]:
    coppie = []
    for k in K_ESATTI:
        coppie += [(("v0", k), (n, k)) for n in MODELLI_NOTTE[1:]]
        coppie += [
            (("v1", k), ("v1+v2", k)),
            (("v2", k), ("v1+v2", k)),
            (("e5-small", k), ("e5-base", k)),
        ]
    coppie += [((n, K), (n, 15)) for n in MODELLI_NOTTE]
    return coppie


def scrivi_notte(nome_file: str, linee: list[str]) -> None:
    NOTTE.mkdir(parents=True, exist_ok=True)
    testo = "\n".join(linee)
    (NOTTE / nome_file).write_text(testo + "\n", encoding="utf-8")
    print(testo)


def misure_intere(nomi, lato: str) -> dict[tuple[str, int], list[dict]]:
    return {
        (n, k): leggi_misura(file_intera(n, k, lato))
        for n in nomi
        for k in K_ESATTI
        if file_intera(n, k, lato).exists()
    }


def esegui_notte_1(lato: str) -> int:
    misure = misure_intere(MODELLI_NOTTE, lato)
    mancanti = [
        f"{n} k={k}" for n in MODELLI_NOTTE for k in K_ESATTI if (n, k) not in misure
    ]
    if mancanti:
        raise ErroreMisura(f"misure sui due fogli mancanti: {', '.join(mancanti)}")
    linee = [
        "Notte del 20/11/2026, parte 1: le configurazioni sui 97 fatti di taratura",
        *(f"{n}: {descrizione_modello(MODELLI[n])}" for n in MODELLI_NOTTE),
        (
            "v2 e v1+v2: intestazione (titolo · parte · atto) davanti al testo del "
            "vettore dei soli avvisi; la ricerca per parole non la vede (come le "
            "copie di Chroma della variante)."
        ),
        "",
        *rapporto_intero(misure, lato, confronti=False),
        "",
        "8. Confronti",
        NOTA_SEGNI,
    ]
    for a, b in coppie_della_parte_1():
        for c in CONDIZIONI_GRIGLIA:
            linee.append(
                riga_segni(
                    f"{a[0]} k={a[1]}", misure[a], f"{b[0]} k={b[1]}", misure[b], c
                )
            )
    scrivi_notte(f"parte1_configurazioni_{lato}.txt", linee)
    return 0


# --- parte 2 ---


def fatti_intera(lato: str):
    """(firme, fatti dei due fogli, file per bando)."""
    firma_1, fatti_1, file_per_bando = apri_misura(FOGLIO, DIVISIONE, lato)
    firma_2, fatti_2, _ = apri_misura(FOGLIO_2, DIVISIONE_2, lato)
    fatti = unisci_fogli([(fatti_1, 0), (fatti_2, SCOSTAMENTO_2)])
    return (firma_1, firma_2), fatti, file_per_bando


def _media_virgola(valori: list[float]) -> str:
    return _virgola(sum(valori) / len(valori), 1) if valori else "-"


def curve_di_un_modello(nome: str, fatti, file_per_bando) -> dict:
    """Esiti in B per ogni k di K_CURVA e ogni peso di PESI_CURVA (con k=K)."""
    from src.retrieval import normalizza_domanda

    recupero, _, _, frammenti_per_fonte, titoli = apri_tutto_esatto(nome)
    esiti = {("k", k): [] for k in K_CURVA} | {("peso", w): [] for w in PESI_CURVA}
    for fatto in fatti:
        giusti, gemelli = documenti_del_fatto(fatto, file_per_bando)
        domanda = normalizza_domanda(str(fatto["domanda"]))
        ripulita = domanda_ripulita(domanda, titoli[fatto["id_bando"]])
        profondi = [
            frammento_di(d)
            for d, _, _ in recupero.cerca_nel_bando(
                ripulita, fatto["id_bando"], PROFONDITA, ampiezza=PROFONDITA
            )
        ]
        # l'ordine non dipende da k: i primi k sono un taglio dei primi 30
        tutti = recupero.cerca_nel_bando(ripulita, fatto["id_bando"], max(K_CURVA))
        elenchi = {("k", k): tutti[:k] for k in K_CURVA}
        for w in PESI_CURVA:
            elenchi[("peso", w)] = recupero.cerca_nel_bando(
                ripulita, fatto["id_bando"], K, peso=w
            )
        for chiave, primi in elenchi.items():
            esito = valuta(
                fatto,
                [frammento_di(d) for d, _, _ in primi],
                profondi,
                giusti,
                gemelli,
                frammenti_per_fonte,
            )
            esiti[chiave].append(
                {
                    "riga": str(fatto["riga"]),
                    "trovato": esito["trovato"],
                    "dal_gemello": esito["pezzo_dal_gemello"],
                    "frammenti": len(primi),
                    "caratteri": sum(len(d.page_content) for d, _, _ in primi),
                }
            )
    return esiti


def controlla_curve(esiti: dict, misura: list[dict]) -> None:
    """Con k=K e con il peso di oggi gli esiti sono quelli della misura esatta."""
    attesi = {r["riga"]: r["B_trovato"] == "sì" for r in misura}
    for chiave in (("k", K), ("peso", PESO_DENSA)):
        trovati = {e["riga"]: e["trovato"] for e in esiti[chiave]}
        if trovati != attesi:
            raise ErroreMisura(f"{chiave}: esiti diversi dalla misura esatta")


def cambi_tra_esiti(base: list[dict], altri: list[dict]) -> tuple[list[str], list[str]]:
    """(guadagnati, persi) tra due elenchi di esiti delle curve, nello stesso ordine."""
    guadagnati = [
        nome_della_riga(e["riga"])
        for e, b in zip(altri, base, strict=True)
        if e["trovato"] and not b["trovato"]
    ]
    persi = [
        nome_della_riga(e["riga"])
        for e, b in zip(altri, base, strict=True)
        if b["trovato"] and not e["trovato"]
    ]
    return guadagnati, persi


def testo_pulito(pagine_grezze: list[str], titolo: str | None) -> str:
    """Il testo del file come lo vede spezza: premesse, pulizia, pagine tenute."""
    from scripts.ingestione.carica_avvisi import togli_premesse
    from src.config import SOGLIA_PAGINA_MINIMA
    from src.ingestion.avvisi import pulisci_avviso
    from src.ingestion.testo import e_indice, pulisci

    senza_premesse, _ = togli_premesse(pagine_grezze)
    tenute = []
    for testo in pulisci_avviso(senza_premesse, titolo).pagine:
        if e_indice(testo):
            continue
        pulito = pulisci(testo, None, "prudente")
        if len(pulito) >= SOGLIA_PAGINA_MINIMA:
            tenute.append(pulito)
    return "\n\n".join(tenute)


def costi_contesto(per_file: list[dict]) -> dict[str, int]:
    """Totali del contesto per frammento; per file: documento, frammenti, token_frammenti.

    Scrittura in cache: ogni documento una volta. Lettura: il documento per
    ogni frammento; senza la prima chiamata di ogni file, che scrive, un
    documento in meno per file. Ingresso non in cache: il frammento più
    ISTRUZIONE_CONTESTO. Uscita: USCITA_CONTESTO per frammento.
    """
    return {
        "scrittura in cache": sum(f["documento"] for f in per_file),
        "lettura dalla cache": sum(f["documento"] * f["frammenti"] for f in per_file),
        "lettura dalla cache, senza la prima chiamata di ogni file": sum(
            f["documento"] * (f["frammenti"] - 1) for f in per_file
        ),
        "ingresso non in cache": sum(
            f["token_frammenti"] + ISTRUZIONE_CONTESTO * f["frammenti"]
            for f in per_file
        ),
        "uscita": sum(USCITA_CONTESTO * f["frammenti"] for f in per_file),
    }


def conta_token(tokenizer, testo: str) -> int:
    return len(tokenizer(testo, add_special_tokens=False)["input_ids"])


def token_dei_file() -> list[dict]:
    """Per ogni file con frammenti: caratteri e token del testo pulito e dei frammenti."""
    from scripts.ingestione import carica_avvisi as ca
    from scripts.ingestione.registra_avvisi import NOME_FILE
    from src.config import PROCESSED_DIR

    _, testi, metadati, _ = leggi_vettori(CARTELLA_19D / "v0")
    frammenti: dict[str, list[str]] = defaultdict(list)
    titolo_di: dict[str, str] = {}
    for testo, meta in zip(testi, metadati, strict=True):
        if meta.get("sha256"):
            frammenti[meta["fonte"]].append(testo)
            titolo_di[meta["fonte"]] = meta.get("titolo")
    tokenizer = ca.apri_tokenizer()
    uscita = []
    for riga in ca.leggi_registro(PROCESSED_DIR / NOME_FILE):
        fonte = riga["nome_file"]
        documento = testo_pulito(
            ca.pagine_del_pdf(ca.percorso_del_file(riga)), titolo_di.get(fonte)
        )
        suoi = frammenti.get(fonte, [])
        uscita.append(
            {
                "fonte": fonte,
                "id_bando": riga["id_bandi"],
                "caratteri": len(documento),
                "documento": conta_token(tokenizer, documento),
                "frammenti": len(suoi),
                "token_frammenti": sum(conta_token(tokenizer, t) for t in suoi),
                "frammenti_nel_testo": sum(t.strip() in documento for t in suoi),
            }
        )
    return uscita


def per_allegato(righe: list[dict], c: str) -> dict[str, tuple[int, int]]:
    """Trovati per documento giusto, solo dove il documento giusto è uno."""
    gruppi: dict[str, list[dict]] = defaultdict(list)
    for r in righe:
        if " | " not in r["documenti_giusti"]:
            gruppi[r["documenti_giusti"]].append(r)
    return {d: _trovati(sue, c) for d, sue in sorted(gruppi.items())}


APISTICI = "sostegno-agli-investimenti-strutturali-aziende-apisti-401650"


def linee_parte_2(curve: dict, file: list[dict], sei: dict) -> list[str]:
    from src.config import EMBEDDING_MODEL

    linee = [
        "",
        (
            "a. Quanti frammenti, condizione B (fusione con ampiezza 20 per lista, "
            "quella dell'app: al più 40 candidati)"
        ),
        (
            "   trovati; frammenti restituiti e caratteri del testo dei frammenti "
            "passati al modello, media per fatto (massimo)"
        ),
    ]
    for n, sue in curve.items():
        linee.append(f"  {n}")
        for k in K_CURVA:
            es = sue[("k", k)]
            linee.append(
                f"    k={k:<3} trovati {sum(e['trovato'] for e in es):>3}/{len(es)}; "
                f"frammenti {_media_virgola([e['frammenti'] for e in es])}; "
                f"caratteri {_media_virgola([e['caratteri'] for e in es])} "
                f"({max(e['caratteri'] for e in es)}); "
                f"pezzi presi dal gemello {sum(e['dal_gemello'] for e in es)}"
            )
    linee += [
        "",
        (
            f"b. Peso della ricerca per significato nella fusione RRF, B, k={K} "
            "(quella per parole ha 1 - peso; 0,5 è oggi); confronto con 0,5"
        ),
    ]
    for n, sue in curve.items():
        base = sue[("peso", PESO_DENSA)]
        linee.append(f"  {n}")
        for w in PESI_CURVA:
            es = sue[("peso", w)]
            linee.append(
                f"    peso {_virgola(w, 1)}: trovati {sum(e['trovato'] for e in es)}"
                f"/{len(es)}; "
                + _segni(*cambi_tra_esiti(base, es))
                + f"; pezzi presi dal gemello {sum(e['dal_gemello'] for e in es)}"
            )

    linee += [
        "",
        (
            "c. Token del testo pulito di ogni file. Conteggio: il tokenizzatore di "
            f"{EMBEDDING_MODEL} (sentencepiece di XLM-RoBERTa), senza i token "
            "speciali. Non è il tokenizzatore del modello di linguaggio, che non si "
            "può usare senza chiamarlo: è il più vicino che c'è in locale, e il "
            "valore vero può differire. Accanto, i caratteri."
        ),
        (
            "   Testo pulito: premesse tolte, pulisci_avviso, pulisci prudente, "
            "pagine d'indice e troppo corte saltate, pagine unite con una riga "
            "vuota (come spezza prima della divisione). 'nel testo': frammenti che "
            "compaiono tali e quali nel testo pulito."
        ),
        f"  {'file':<66}{'caratteri':>10}{'token':>8}{'nel testo':>12}",
    ]
    for f in sorted(file, key=lambda f: f["fonte"]):
        linee.append(
            f"  {f['fonte']:<66}{f['caratteri']:>10}{f['documento']:>8}"
            f"{f['frammenti_nel_testo']:>7}/{f['frammenti']}"
        )
    linee.append(
        f"  {'totale (' + str(len(file)) + ' file)':<66}"
        f"{sum(f['caratteri'] for f in file):>10}{sum(f['documento'] for f in file):>8}"
    )
    per_bando: dict[str, list[dict]] = defaultdict(list)
    for f in file:
        per_bando[f["id_bando"]].append(f)
    linee += ["", "   Per bando, i suoi file insieme:"]
    linee.append(f"  {'bando':<66}{'file':>5}{'caratteri':>10}{'token':>8}")
    for bando, suoi in sorted(per_bando.items()):
        linee.append(
            f"  {bando:<66}{len(suoi):>5}{sum(f['caratteri'] for f in suoi):>10}"
            f"{sum(f['documento'] for f in suoi):>8}"
        )

    linee += [
        "",
        (
            "d. Contesto per frammento (stesso conteggio dei token). Per file: token "
            "del documento, frammenti, token dei frammenti."
        ),
        f"  {'file':<66}{'documento':>10}{'frammenti':>10}{'token fr.':>10}",
    ]
    for f in sorted(file, key=lambda f: f["fonte"]):
        linee.append(
            f"  {f['fonte']:<66}{f['documento']:>10}{f['frammenti']:>10}"
            f"{f['token_frammenti']:>10}"
        )
    linee.append(
        f"  {'totale':<66}{sum(f['documento'] for f in file):>10}"
        f"{sum(f['frammenti'] for f in file):>10}"
        f"{sum(f['token_frammenti'] for f in file):>10}"
    )
    linee.append(
        f"   Totali in token (istruzione {ISTRUZIONE_CONTESTO} e uscita "
        f"{USCITA_CONTESTO} per frammento):"
    )
    linee += [f"    {voce}: {valore}" for voce, valore in costi_contesto(file).items()]

    etichette = [f"{n} k={k}" for n, k in sei]
    bandi = sorted({r["id_bando"] for righe in sei.values() for r in righe})
    largo = max(len(b) for b in bandi) + 1
    linee += [
        "",
        "e. Fatti trovati in B per bando, nelle sei configurazioni già misurate",
        f"  {'':<{largo}}{'n':>4}" + "".join(f"{e:>15}" for e in etichette),
    ]
    for bando in bandi:
        celle = [
            _trovati(righe, "B", lambda r, b=bando: r["id_bando"] == b)
            for righe in sei.values()
        ]
        linee.append(
            f"  {bando:<{largo}}{celle[0][1]:>4}"
            + "".join(f"{x[0]:>15}" for x in celle)
        )
    linee += ["", "   Apistici, per allegato (il documento giusto del fatto):"]
    allegati = {
        chiave: per_allegato([r for r in righe if r["id_bando"] == APISTICI], "B")
        for chiave, righe in sei.items()
    }
    for nome_file in next(iter(allegati.values())):
        celle = [allegati[chiave][nome_file] for chiave in sei]
        linee.append(
            f"  {nome_file:<{largo}}{celle[0][1]:>4}"
            + "".join(f"{x[0]:>15}" for x in celle)
        )
    return linee


def esegui_notte_2(lato: str) -> int:
    import time

    from scripts.ingestione.carica_avvisi import senza_rete
    from src.config import CHROMA_DIR

    senza_rete()
    inizio = time.perf_counter()
    (firma_1, firma_2), fatti, file_per_bando = fatti_intera(lato)
    prima = impronte_cartella(CHROMA_DIR)
    with senza_connessioni():
        curve = {
            n: curve_di_un_modello(n, fatti, file_per_bando) for n in MODELLI_CURVE
        }
        file = token_dei_file()
    if impronte_cartella(CHROMA_DIR) != prima:
        raise ErroreMisura("le impronte del Chroma vero sono cambiate")
    for n in MODELLI_CURVE:
        controlla_curve(curve[n], leggi_misura(file_intera(n, K, lato)))
    linee = [
        (
            f"Notte del 20/11/2026, parte 2: curve e conteggi, metà: {lato} "
            f"({len(fatti)} fatti)"
        ),
        (
            f"Divisioni: sha256 {firma_1}, {firma_2}; Chroma vero: {len(prima)} file, "
            "impronte uguali prima e dopo"
        ),
        (
            "Controllo: con k=10 e con il peso 0,5 gli esiti coincidono con la misura "
            "esatta sui 97 (esatta_k10_taratura_97.csv)."
        ),
        NOTA_SEGNI,
        *linee_parte_2(curve, file, misure_intere(MODELLI_INTERA, lato)),
        "",
        f"Tempo: {time.perf_counter() - inizio:.0f} s",
    ]
    scrivi_notte(f"parte2_curve_{lato}.txt", linee)
    return 0


# --- parte 3 ---


def frammenti_dei_vettori() -> tuple[dict[str, list[Frammento]], dict]:
    """(frammenti per fonte ordinati per chunk_num, indice per (fonte, chunk_num))."""
    _, testi, metadati, _ = leggi_vettori(CARTELLA_19D / "v0")
    per_fonte: dict[str, list[Frammento]] = defaultdict(list)
    indice = {}
    for testo, meta in zip(testi, metadati, strict=True):
        fonte = meta.get("fonte") or ""
        fr = Frammento(
            meta.get("chunk_num", -1),
            meta.get("page", 0),
            testo,
            meta.get("car_visti", len(testo)),
        )
        if (fonte, fr.chunk_num) in indice:
            raise ErroreMisura(f"chunk_num ripetuto: {fonte} {fr.chunk_num}")
        indice[(fonte, fr.chunk_num)] = fr
        per_fonte[fonte].append(fr)
    for lista in per_fonte.values():
        lista.sort(key=lambda fr: fr.chunk_num)
    return per_fonte, indice


def allargati(
    primi: list[tuple[str, Frammento]],
    frammenti_per_fonte: dict[str, list[Frammento]],
    distanza: int | None = None,
    pagina: bool = False,
) -> list[tuple[str, Frammento]]:
    """I primi più i vicini entro `distanza` nello stesso file, o la loro pagina intera."""
    scelti = {(f, fr.chunk_num): (f, fr) for f, fr in primi}
    for fonte, fr in primi:
        for altro in frammenti_per_fonte.get(fonte, []):
            vicino = (
                distanza is not None and abs(altro.chunk_num - fr.chunk_num) <= distanza
            )
            if vicino or (pagina and altro.pagina == fr.pagina):
                scelti.setdefault((fonte, altro.chunk_num), (fonte, altro))
    return list(scelti.values())


def trovato_in(
    fatto: dict, elenco: list[tuple[str, Frammento]], giusti: set[str]
) -> bool:
    return all(
        prima_posizione(p, elenco, giusti) is not None for p in unita_del_fatto(fatto)
    )


def distanza_tra_pezzi(
    fatto: dict, giusti: set[str], frammenti_per_fonte: dict[str, list[Frammento]]
) -> tuple[int, int] | None:
    """(frammenti, pagine) tra i pezzi più lontani; None se stanno in file diversi.

    Per ogni coppia di pezzi conta la coppia di frammenti più vicina dello
    stesso file che li contiene; per il fatto, la coppia di pezzi più lontana.
    """
    luoghi = [
        [
            (f, fr.chunk_num, fr.pagina)
            for f in sorted(giusti)
            for fr in frammenti_per_fonte.get(f, [])
            if contiene(p, fr)
        ]
        for p in unita_del_fatto(fatto)
    ]
    in_frammenti = in_pagine = 0
    for i in range(len(luoghi)):
        for j in range(i + 1, len(luoghi)):
            coppie = [
                (abs(a[1] - b[1]), abs(a[2] - b[2]))
                for a in luoghi[i]
                for b in luoghi[j]
                if a[0] == b[0]
            ]
            if not coppie:
                return None
            in_frammenti = max(in_frammenti, min(c[0] for c in coppie))
            in_pagine = max(in_pagine, min(c[1] for c in coppie))
    return in_frammenti, in_pagine


def esegui_notte_3(lato: str) -> int:
    import json

    (firma_1, firma_2), fatti, file_per_bando = fatti_intera(lato)
    frammenti_per_fonte, indice = frammenti_dei_vettori()
    piu = {f["riga"] for f in fatti if len(unita_del_fatto(f)) > 1}
    linee = [
        (
            f"Notte del 20/11/2026, parte 3: risposte in più pezzi, condizione B, "
            f"k={K}, metà: {lato}"
        ),
        (
            f"Divisioni: sha256 {firma_1}, {firma_2}. Fatti in più pezzi: {len(piu)} "
            f"su {len(fatti)}. Nessuna ricerca nuova: elenchi dei primi {K} da "
            "elenchi_esatti_taratura_97.json, frammenti da v0/frammenti.json; per "
            "ogni fatto l'esito sugli elenchi coincide con quello del CSV."
        ),
        (
            "Distanza tra i pezzi: per la coppia di pezzi più lontana, la coppia più "
            "vicina di frammenti dello stesso file che li contiene (0: stesso "
            "frammento), in frammenti (chunk_num) e in pagine."
        ),
    ]
    for nome in MODELLI_CURVE:
        elenchi = json.loads(
            (
                cartella_modello(nome) / f"elenchi_esatti_{lato}_{SUFFISSO_INTERA}.json"
            ).read_text(encoding="utf-8")
        )
        per_riga = {r["riga"]: r for r in leggi_misura(file_intera(nome, K, lato))}
        modi = {f"vicini a distanza {d}": {"distanza": d} for d in VICINI_NOTTE}
        modi["pagina intera"] = {"pagina": True}
        conti = {
            m: {"più pezzi": [], "tutti": [], "frammenti": [], "caratteri": []}
            for m in modi
        }
        linee += [
            "",
            f"=== {nome} ===",
            (
                f"  {'riga':<7}{'pezzi':>6}  {'posizioni (ampiezza 50)':<26}"
                f"{'frammenti':>10}{'pagine':>8}  trovato"
            ),
        ]
        for fatto in fatti:
            giusti, _ = documenti_del_fatto(fatto, file_per_bando)
            primi = [
                (f, indice[(f, c)]) for f, c, _ in elenchi[f"{fatto['riga']} B k={K}"]
            ]
            riga = per_riga[str(fatto["riga"])]
            if trovato_in(fatto, primi, giusti) != (riga["B_trovato"] == "sì"):
                raise ErroreMisura(f"riga {fatto['riga']}: esito diverso dal CSV")
            for modo, argomenti in modi.items():
                elenco = allargati(primi, frammenti_per_fonte, **argomenti)
                if trovato_in(fatto, elenco, giusti) and riga["B_trovato"] != "sì":
                    conti[modo]["tutti"].append(nome_della_riga(fatto["riga"]))
                    if fatto["riga"] in piu:
                        conti[modo]["più pezzi"].append(nome_della_riga(fatto["riga"]))
                conti[modo]["frammenti"].append(len(elenco))
                conti[modo]["caratteri"].append(sum(len(fr.testo) for _, fr in elenco))
            if fatto["riga"] not in piu:
                continue
            distanza = distanza_tra_pezzi(fatto, giusti, frammenti_per_fonte)
            linee.append(
                f"  {nome_della_riga(fatto['riga']):<7}{riga['pezzi']:>6}  "
                f"{riga['B_posizioni_profonde']:<26}"
                + (
                    f"{distanza[0]:>10}{distanza[1]:>8}"
                    if distanza
                    else f"{'file diversi':>18}"
                )
                + f"  {riga['B_trovato']}"
            )
        trovati_piu = sum(per_riga[str(r)]["B_trovato"] == "sì" for r in piu)
        trovati = sum(r["B_trovato"] == "sì" for r in per_riga.values())
        primi_car = [
            sum(len(indice[(f, c)].testo) for f, c, _ in elenchi[f"{r} B k={K}"])
            for r in per_riga
        ]
        linee += [
            "",
            (
                f"  Senza vicini: trovati più pezzi {trovati_piu}/{len(piu)}, tutti "
                f"{trovati}/{len(fatti)}; caratteri dei primi {K} "
                f"{_media_virgola(primi_car)} in media per fatto."
            ),
            (
                "  Fatti in più che diventerebbero trovati restituendo, per ogni "
                f"frammento tra i primi {K}, anche (frammenti e caratteri restituiti: "
                "media per fatto, su tutti i fatti):"
            ),
        ]
        for modo, conto in conti.items():
            linee.append(
                f"    {modo}: più pezzi +{len(conto['più pezzi'])} "
                f"({', '.join(conto['più pezzi']) or '-'}), tutti "
                f"+{len(conto['tutti'])} ({', '.join(conto['tutti']) or '-'}); "
                f"frammenti {_media_virgola(conto['frammenti'])}, caratteri "
                f"{_media_virgola(conto['caratteri'])}"
            )
    scrivi_notte(f"parte3_piu_pezzi_{lato}.txt", linee)
    return 0


# --- parte 4 ---


def cartella_hf(nome: str) -> Path:
    from huggingface_hub.constants import HF_HUB_CACHE

    return Path(HF_HUB_CACHE) / ("models--" + nome.replace("/", "--"))


def codice_del_modello(file) -> list[str]:
    """I file .py che il modello caricherebbe: quelli nella radice, tranne gli
    script di addestramento, che nessuno esegue al caricamento."""
    return [
        f
        for f in file
        if f.endswith(".py") and "/" not in f and not f.startswith("train")
    ]


def esegui_scarica_riordinatore(chiave: str) -> int:
    """Scarica un riordinatore una volta: la sola eccezione alla rete autorizzata.

    Si ferma senza scaricare il modello se è riservato (gated), se contiene
    codice che il modello caricherebbe (codice_del_modello), se config.json
    chiede codice (auto_map) o se manca model.safetensors. Si scaricano solo
    i file di FILE_RIORDINATORE; si carica con trust_remote_code=False. Con l'errore dei certificati usa l'archivio di
    Windows (truststore); la verifica resta sempre attiva.
    """
    import json

    from huggingface_hub import HfApi, hf_hub_download

    nome = RIORDINATORI[chiave]
    stato = {"truststore": False}

    def con_certificati(funzione, *args, **kwargs):
        try:
            return funzione(*args, **kwargs)
        except Exception as errore:  # noqa: BLE001
            testo = f"{errore!r} {errore.__cause__!r} {errore.__context__!r}"
            if stato["truststore"] or (
                "CERTIFICATE_VERIFY_FAILED" not in testo and "local issuer" not in testo
            ):
                raise
            import truststore
            from huggingface_hub.utils import close_session

            truststore.inject_into_ssl()
            # la sessione già aperta ha il contesto di prima: se ne apre una nuova
            close_session()
            stato["truststore"] = True
            print("certificati: uso l'archivio di Windows (truststore)")
            return funzione(*args, **kwargs)

    info = con_certificati(HfApi().model_info, nome, files_metadata=True)
    file = {s.rfilename: s.size for s in info.siblings}
    licenza = info.card_data.get("license") if info.card_data else None
    print(f"{nome}: gated {info.gated!r}, licenza {licenza!r}, file {sorted(file)}")
    if info.gated:
        raise ErroreMisura(f"{nome}: accesso riservato, non si scarica")
    codice = codice_del_modello(file)
    if codice:
        raise ErroreMisura(f"{nome}: codice del modello ({', '.join(codice)})")
    if "model.safetensors" not in file:
        raise ErroreMisura(f"{nome}: manca model.safetensors, non si scarica")
    config = json.loads(
        Path(con_certificati(hf_hub_download, nome, "config.json")).read_text(
            encoding="utf-8"
        )
    )
    if "auto_map" in config:
        raise ErroreMisura(f"{nome}: config.json chiede codice del modello (auto_map)")
    scelti = [f for f in FILE_RIORDINATORE if f in file]
    for f in scelti:
        con_certificati(hf_hub_download, nome, f)
    # i file veri stanno in blobs; snapshots ha solo collegamenti
    cartella = cartella_hf(nome)
    occupato = sum(p.stat().st_size for p in (cartella / "blobs").iterdir())
    fuori = sorted(set(file) - set(scelti))
    print(
        f"scaricati: {', '.join(scelti)}; non scaricati: {', '.join(fuori)}; "
        f"{cartella / 'blobs'}: {occupato / 2**20:.1f} MB"
    )
    return 0


def riordina(voti, n: int) -> list[int]:
    """Gli indici dei candidati dal voto più alto; a parità, l'ordine di prima.

    Con due classi per coppia vale l'ultima (quella positiva).
    """
    import numpy as np

    voti = np.asarray(voti, dtype=np.float64)
    if voti.ndim == 2:
        voti = voti[:, -1]
    if len(voti) != n:
        raise ErroreMisura("voti e candidati in numero diverso")
    return sorted(range(n), key=lambda i: (-voti[i], i))


def cartella_riordino(nome: str) -> Path:
    """notte/riordino per i modelli della notte; per gli altri, la loro cartella."""
    if nome in MODELLI_CURVE:
        return NOTTE / "riordino"
    return cartella_modello(nome) / "riordino"


def file_riordino(chiave: str, nome: str, k: int, lato: str) -> Path:
    return cartella_riordino(nome) / f"{chiave}_{nome}_k{k}_{lato}.csv"


def esegui_riordino(lato: str, chiave: str, nome: str) -> int:
    import json
    import statistics
    import time

    from scripts.ingestione.carica_avvisi import senza_rete
    from src.config import CHROMA_DIR

    if nome not in MODELLI_CURVE and not MODELLI[nome].parte:
        raise ErroreMisura(f"riordino solo su {', '.join(MODELLI_CURVE)} e v0+parte")
    senza_rete()
    (firma_1, firma_2), fatti, file_per_bando = fatti_intera(lato)
    prima = impronte_cartella(CHROMA_DIR)
    with senza_connessioni():
        from sentence_transformers import CrossEncoder

        from src.chains.rag import recupera
        from src.recupero_documenti import documenti_nominati
        from src.retrieval import normalizza_domanda

        recupero, app, _, frammenti_per_fonte, titoli = apri_tutto_esatto(nome)
        memoria_prima = memoria_del_processo()
        inizio = time.perf_counter()
        riordinatore = CrossEncoder(
            RIORDINATORI[chiave], trust_remote_code=False, local_files_only=True
        )
        caricamento = time.perf_counter() - inizio
        memoria_dopo = memoria_del_processo()
        massimo = riordinatore.max_seq_length
        tokenizer = riordinatore.tokenizer
        righe = {k: [] for k in K_ESATTI}
        tra_i_candidati = dict.fromkeys(CONDIZIONI_GRIGLIA, 0)
        tempi = {c: [] for c in CONDIZIONI_GRIGLIA}
        lunghe = dict.fromkeys(CONDIZIONI_GRIGLIA, 0)
        coppie = dict.fromkeys(CONDIZIONI_GRIGLIA, 0)
        frammenti_lunghi = set()
        esempio = None
        for fatto in fatti:
            giusti, gemelli = documenti_del_fatto(fatto, file_per_bando)
            domanda = normalizza_domanda(str(fatto["domanda"]))
            ripulita = domanda_ripulita(domanda, titoli[fatto["id_bando"]])
            candidati = {
                "A": [d for d, _, _ in recupera(app, fatto["domanda"], k=CANDIDATI)],
                "B": [
                    d
                    for d, _, _ in recupero.cerca_nel_bando(
                        ripulita, fatto["id_bando"], CANDIDATI
                    )
                ],
            }
            domande = {"A": domanda, "B": ripulita}
            riordinati = {}
            for c in CONDIZIONI_GRIGLIA:
                docs = candidati[c]
                testi = [(domande[c], d.page_content) for d in docs]
                t = time.perf_counter()
                voti = riordinatore.predict(testi, show_progress_bar=False)
                tempi[c].append(time.perf_counter() - t)
                for (q, testo), d in zip(testi, docs, strict=True):
                    coppie[c] += 1
                    lunghezza = len(tokenizer(q, testo)["input_ids"])
                    if lunghezza <= massimo:
                        continue
                    lunghe[c] += 1
                    frammenti_lunghi.add(
                        (d.metadata.get("fonte"), d.metadata.get("chunk_num"))
                    )
                    if esempio is None:
                        tronca = tokenizer(
                            q, testo, truncation="longest_first", max_length=massimo
                        )["input_ids"]
                        domanda_ids = tokenizer(q)["input_ids"][:-1]
                        esempio = [
                            lunghezza,
                            len(tronca),
                            tronca[: len(domanda_ids)] == domanda_ids,
                        ]
                riordinati[c] = [docs[i] for i in riordina(voti, len(docs))]
                if trovato_in(fatto, [frammento_di(d) for d in riordinati[c]], giusti):
                    tra_i_candidati[c] += 1
            nominati = set(documenti_nominati(domanda, app.titoli))
            for k in K_ESATTI:
                esiti = {
                    c: valuta(
                        fatto,
                        [frammento_di(d) for d in riordinati[c][:k]],
                        [frammento_di(d) for d in riordinati[c]],
                        giusti,
                        gemelli,
                        frammenti_per_fonte,
                    )
                    for c in CONDIZIONI_GRIGLIA
                }
                di_sempre = sum(
                    not d.metadata.get("sha256") for d in riordinati["A"][:k]
                )
                righe[k].append(
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
        del recupero, app, riordinatore
    if impronte_cartella(CHROMA_DIR) != prima:
        raise ErroreMisura("le impronte del Chroma vero sono cambiate")
    cartella_riordino(nome).mkdir(parents=True, exist_ok=True)
    for k in K_ESATTI:
        scrivi_misura(file_riordino(chiave, nome, k, lato), righe[k])
    dati = {
        "modello": RIORDINATORI[chiave],
        "base": nome,
        "divisioni": [firma_1, firma_2],
        "chroma_vero": f"{len(prima)} file, impronte uguali prima e dopo",
        "memoria_in_più_MB": (memoria_dopo - memoria_prima) / 2**20,
        "caricamento_s": caricamento,
        "tempo_per_domanda_s": {
            c: {"media": statistics.mean(v), "mediana": statistics.median(v)}
            for c, v in tempi.items()
        },
        "lunghezza_massima": massimo,
        "coppie": coppie,
        "coppie_troncate": lunghe,
        "frammenti_troncati": len(frammenti_lunghi),
        "esempio_troncamento": esempio,
        "trovati_tra_i_candidati": tra_i_candidati,
    }
    (cartella_riordino(nome) / f"{chiave}_{nome}_{lato}.json").write_text(
        json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    if nome not in MODELLI_CURVE:
        return 0
    return esegui_rapporto_riordino(lato)


def linee_riordino(dati: dict, misure: dict[str, list[dict]]) -> list[str]:
    """Il rapporto di un riordinatore su una base; misure per etichetta."""
    linee = [f"  {'':<26}{'n':>4}" + "".join(f"{e:>20}" for e in misure)]
    prime = next(iter(misure.values()))
    for gruppo, scelta in GRUPPI_INTERA:
        celle = [
            f"{_trovati(r, 'A', scelta)[0]} / {_trovati(r, 'B', scelta)[0]}"
            for r in misure.values()
        ]
        linee.append(
            f"  {gruppo:<26}{_trovati(prime, 'A', scelta)[1]:>4}"
            + "".join(f"{x:>20}" for x in celle)
        )
    for posto in (1, 5):
        celle = [
            f"{_primi_entro(r, 'A', posto)} / {_primi_entro(r, 'B', posto)}"
            for r in misure.values()
        ]
        nome_posto = "primo giusto al 1° posto" if posto == 1 else "tra i primi 5"
        linee.append(f"  {nome_posto:<30}" + "".join(f"{x:>20}" for x in celle))
    for c in CONDIZIONI_GRIGLIA:
        celle = []
        for r in misure.values():
            gemelle, altri = gemelli_presi(r, c)
            celle.append(f"{len(gemelle)} + {len(altri)}")
        linee.append(
            f"  {'presi dal gemello, ' + c:<30}" + "".join(f"{x:>20}" for x in celle)
        )
    linee.append(
        "  (celle: fatti trovati in A / in B; presi dal gemello: frasi gemelle + "
        "altri fatti)"
    )
    for k in K_ESATTI:
        for c in CONDIZIONI_GRIGLIA:
            linee.append(
                riga_segni(
                    f"senza riordino k={k}",
                    misure[f"senza riordino k={k}"],
                    f"riordino k={k}",
                    misure[f"riordino k={k}"],
                    c,
                )
            )
    for k in K_ESATTI:
        for c in CONDIZIONI_GRIGLIA:
            gemelle, altri = gemelli_presi(misure[f"riordino k={k}"], c)
            linee.append(
                f"  presi dal bando sbagliato, riordino k={k} {c}: frasi gemelle "
                f"{', '.join(gemelle) or '-'}; altri fatti {', '.join(altri) or '-'}"
            )
    tempo = dati["tempo_per_domanda_s"]
    linee += [
        f"  trovati tra i {CANDIDATI} candidati (il massimo raggiungibile): "
        + ", ".join(f"{c} {v}" for c, v in dati["trovati_tra_i_candidati"].items()),
        (
            f"  memoria in più dopo il caricamento: {dati['memoria_in_più_MB']:.0f} MB; "
            f"caricamento {dati['caricamento_s']:.1f} s"
        ),
        f"  tempo per domanda con {CANDIDATI} candidati (media, mediana): "
        + "; ".join(
            f"{c} {v['media'] * 1000:.0f} ms, {v['mediana'] * 1000:.0f} ms"
            for c, v in tempo.items()
        ),
        f"  lunghezza massima letta: {dati['lunghezza_massima']} token (domanda e "
        "frammento insieme, token speciali compresi); coppie oltre: "
        + ", ".join(
            f"{c} {dati['coppie_troncate'][c]} su {dati['coppie'][c]}"
            for c in CONDIZIONI_GRIGLIA
        )
        + f"; frammenti diversi oltre: {dati['frammenti_troncati']}",
    ]
    if dati["esempio_troncamento"]:
        prima, dopo, intera = dati["esempio_troncamento"]
        linee.append(
            "  troncamento 'longest_first' (predefinito di sentence-transformers): "
            "si tolgono token dalla fine della sequenza più lunga, il frammento; "
            f"prova su una coppia: {prima} token -> {dopo}, domanda "
            f"{'intera' if intera else 'troncata'}"
        )
    return linee


def esegui_rapporto_riordino(lato: str) -> int:
    import json

    linee = [
        f"Notte del 20/11/2026, parte 4: riordinatore, metà: {lato}",
        (
            f"Per ogni domanda {CANDIDATI} candidati dal recupero di oggi (A: recupera "
            f"dell'app con k={CANDIDATI}; B: ricerca nel bando con la domanda "
            f"ripulita, k={CANDIDATI}); il riordinatore dà un voto a ogni coppia "
            "(A: domanda normalizzata; B: domanda ripulita) e frammento; si tengono "
            "i primi 10 o 15. A parità di voto, l'ordine di prima."
        ),
        NOTA_SEGNI,
    ]
    for chiave in RIORDINATORI:
        for nome in MODELLI_CURVE:
            percorso = NOTTE / "riordino" / f"{chiave}_{nome}_{lato}.json"
            if not percorso.exists():
                continue
            dati = json.loads(percorso.read_text(encoding="utf-8"))
            misure = {}
            for k in K_ESATTI:
                misure[f"senza riordino k={k}"] = leggi_misura(
                    file_intera(nome, k, lato)
                )
                misure[f"riordino k={k}"] = leggi_misura(
                    file_riordino(chiave, nome, k, lato)
                )
            linee += [
                "",
                f"=== {dati['modello']} su {nome} ===",
                f"  {dati['chroma_vero']}",
            ]
            linee += linee_riordino(dati, misure)
    scrivi_notte(f"parte4_riordinatore_{lato}.txt", linee)
    return 0


# --- nome dell'azione degli apistici sui 97 fatti (21/11/2026) ---

PARTE_97 = "v0+parte"
RIORDINATORE_PICCOLO = "osiria"


def pezzi_in_vista(
    fatti: list[dict],
    file_per_bando: dict[str, list[dict]],
    frammenti_per_fonte: dict[str, list[Frammento]],
) -> dict[tuple[int, int], bool]:
    """Per ogni pezzo intero in un frammento giusto: se sta nella parte vista
    di almeno uno. Chiave (riga, numero del pezzo da 1)."""
    stato = {}
    for fatto in fatti:
        giusti, _ = documenti_del_fatto(fatto, file_per_bando)
        frammenti = [
            fr for f in sorted(giusti) for fr in frammenti_per_fonte.get(f, [])
        ]
        for numero, pezzo in enumerate(unita_del_fatto(fatto), 1):
            tratti = [(fr, t) for fr in frammenti if (t := contiene(pezzo, fr))]
            if tratti:
                stato[(fatto["riga"], numero)] = any(
                    t[1] <= fr.car_visti for fr, t in tratti
                )
    return stato


def apistici_dei_primi(elenchi: dict, chiave: str, file_apistici: set[str]) -> int:
    return sum(fonte in file_apistici for fonte, _, _ in elenchi.get(chiave, []))


def esegui_parte_97(lato: str) -> int:
    """Rapporto: v0+parte contro v0, senza e con il riordinatore piccolo."""
    import json

    from transformers import AutoTokenizer

    from scripts.ingestione.carica_avvisi import senza_rete

    if lato != TARATURA:
        raise ErroreMisura("il rapporto della parte si fa solo sulla taratura")
    senza_rete()
    parti = parti_del_registro()
    _, fatti, file_per_bando = fatti_intera(lato)
    cartella = cartella_modello(PARTE_97)
    misure = {}
    for nome in ("v0", PARTE_97):
        for k in K_ESATTI:
            misure[(nome, k)] = leggi_misura(file_intera(nome, k, lato))
            misure[(f"{RIORDINATORE_PICCOLO} {nome}", k)] = leggi_misura(
                file_riordino(RIORDINATORE_PICCOLO, nome, k, lato)
            )
    basi = ["v0", PARTE_97, f"{RIORDINATORE_PICCOLO} v0"]
    basi.append(f"{RIORDINATORE_PICCOLO} {PARTE_97}")
    del_bando = {r["riga"] for r in misure[("v0", K)] if r["id_bando"] == APISTICI}

    linee = [
        f"Passo 19d, nome dell'azione degli apistici sui 97 fatti, metà: {lato}",
        descrizione_modello(MODELLI[PARTE_97]),
        "Parti dal registro (data/processed/documenti_bandi.csv):",
        *[f"  {f}: {p!r}" for f, p in sorted(parti.items())],
        (
            "Base: le misure della notte (v0/esatta_k*_taratura_97.csv e "
            f"notte/riordino/{RIORDINATORE_PICCOLO}_v0_k*_taratura.csv); "
            f"riordinatore {RIORDINATORI[RIORDINATORE_PICCOLO]}, {CANDIDATI} candidati"
        ),
        NOTA_SEGNI,
        "",
        "1. Fatti trovati su 97, A / B; 1° B e ≤5 B dalla misura con k=10",
        f"  {'configurazione':<28}{'k=10':>10}{'k=15':>10}{'1° B':>7}{'≤5 B':>7}",
    ]
    for b in basi:
        celle = [
            f"{_trovati(misure[(b, k)], 'A')[0]} / {_trovati(misure[(b, k)], 'B')[0]}"
            for k in K_ESATTI
        ]
        linee.append(
            f"  {b:<28}{celle[0]:>10}{celle[1]:>10}"
            f"{_primi_entro(misure[(b, K)], 'B', 1):>7}"
            f"{_primi_entro(misure[(b, K)], 'B', 5):>7}"
        )

    linee += ["", "2. Confronti con la stessa base senza la parte"]
    for prima, dopo in ((basi[0], basi[1]), (basi[2], basi[3])):
        for k in K_ESATTI:
            for c in CONDIZIONI_GRIGLIA:
                linee.append(
                    riga_segni(
                        f"{prima} k={k}",
                        misure[(prima, k)],
                        f"{dopo} k={k}",
                        misure[(dopo, k)],
                        c,
                    )
                )

    linee += ["", "3. Apistici (fatti di taratura del bando), per allegato giusto"]
    for c in CONDIZIONI_GRIGLIA:
        allegati = {
            (b, k): per_allegato(
                [r for r in misure[(b, k)] if r["id_bando"] == APISTICI], c
            )
            for b in basi
            for k in K_ESATTI
        }
        file_ = list(next(iter(allegati.values())))
        intestazioni = [
            m[1].upper() if (m := re.search(r"allegato-(a\d+)", f)) else f
            for f in file_
        ]
        linee.append(
            f"  {c}: {'configurazione':<30}"
            + "".join(
                f"{n + ' (' + str(allegati[(basi[0], K)][f][1]) + ')':>9}"
                for n, f in zip(intestazioni, file_, strict=True)
            )
            + f"{'tutti':>8}"
        )
        for (b, k), voci in allegati.items():
            celle = [voci[f][0] for f in file_]
            linee.append(
                f"     {b + ', k=' + str(k):<30}"
                + "".join(f"{x:>9}" for x in celle)
                + f"{sum(celle):>8}"
            )
    for c in CONDIZIONI_GRIGLIA:
        for k in K_ESATTI:
            prima, dopo = (
                [r for r in misure[(b, k)] if r["riga"] in del_bando] for b in basi[:2]
            )
            linee.append(
                riga_segni(f"v0 k={k}", prima, f"{PARTE_97} k={k}", dopo, c).replace(
                    "  ", "  apistici: ", 1
                )
            )

    linee += [
        "",
        "4. Presi dal bando o dall'allegato sbagliato prima del giusto",
        "   (frasi gemelle; altri fatti; tra parentesi quelli degli apistici)",
    ]
    for b in basi:
        for k in K_ESATTI:
            for c in CONDIZIONI_GRIGLIA:
                gemelle, altri = gemelli_presi(misure[(b, k)], c)
                api = [
                    nome_della_riga(r["riga"])
                    for r in misure[(b, k)]
                    if r["riga"] in del_bando and r[f"{c}_pezzo_dal_gemello"] == "sì"
                ]
                senza = [
                    nome_della_riga(r["riga"])
                    for r in misure[(b, k)]
                    if r["riga"] in del_bando and r[f"{c}_gemello_senza_giusto"] == "sì"
                ]
                linee.append(
                    f"  {b}, k={k}, {c}: frasi gemelle {', '.join(gemelle) or '-'}; "
                    f"altri {', '.join(altri) or '-'} (apistici: presi "
                    f"{', '.join(api) or '-'}; allegato sbagliato tra i primi senza "
                    f"il giusto {', '.join(senza) or '-'})"
                )

    # 5. parte vista: car_visti dei metadati (v0) contro car_visti con il prefisso
    ids, testi, metadati, _ = leggi_vettori(cartella)
    tokenizer = AutoTokenizer.from_pretrained(MINILM, local_files_only=True)
    senza_prefisso: dict[str, list[Frammento]] = defaultdict(list)
    for testo, meta in zip(testi, metadati, strict=True):
        if meta.get("fonte") in parti:
            senza_prefisso[meta["fonte"]].append(
                Frammento(
                    meta.get("chunk_num", -1),
                    meta.get("page", 0),
                    testo,
                    meta.get("car_visti", len(testo)),
                )
            )
    con_prefisso = {
        f: [Frammento(fr.chunk_num, fr.pagina, fr.testo, fr.car_visti) for fr in lista]
        for f, lista in senza_prefisso.items()
    }
    visti_con_prefisso(con_prefisso, parti, tokenizer, LIMITE_MODELLO)
    coppie_fr = [
        (a, b)
        for f in sorted(senza_prefisso)
        for a, b in zip(senza_prefisso[f], con_prefisso[f], strict=True)
    ]
    fatti_api = [f for f in fatti if f["id_bando"] == APISTICI]
    prima_vista = pezzi_in_vista(fatti_api, file_per_bando, senza_prefisso)
    dopo_vista = pezzi_in_vista(fatti_api, file_per_bando, con_prefisso)
    usciti = [k for k, v in prima_vista.items() if v and not dopo_vista[k]]
    entrati = [k for k, v in prima_vista.items() if not v and dopo_vista[k]]
    tagliati = [(a, b) for a, b in coppie_fr if b.car_visti < a.car_visti]
    linee += [
        "",
        f"5. Parte vista dal modello ({LIMITE_MODELLO} token), frammenti con la parte",
        (
            f"  frammenti {len(coppie_fr)}; con meno testo visto per il prefisso "
            f"{len(tagliati)}; caratteri del testo visti, media: senza prefisso "
            f"{_media([a.car_visti for a, _ in coppie_fr])}, con prefisso "
            f"{_media([b.car_visti for _, b in coppie_fr])}; testo intero, media "
            f"{_media([len(a.testo) for a, _ in coppie_fr])}"
        ),
        (
            f"  pezzi dei fatti degli apistici interi in un frammento giusto: "
            f"{len(prima_vista)}; nella parte vista senza prefisso "
            f"{sum(prima_vista.values())}, con prefisso {sum(dopo_vista.values())}"
        ),
        "  usciti dalla parte vista per il prefisso: "
        + (", ".join(f"{nome_della_riga(r)} pezzo {n}" for r, n in usciti) or "-"),
        "  entrati: "
        + (", ".join(f"{nome_della_riga(r)} pezzo {n}" for r, n in entrati) or "-"),
    ]

    # 6. effetto sugli altri bandi
    def altri(righe: list[dict]) -> list[dict]:
        return [r for r in righe if r["riga"] not in del_bando]

    linee += ["", f"6. Altri bandi ({len(altri(misure[('v0', K)]))} fatti)"]
    for prima, dopo in ((basi[0], basi[1]), (basi[2], basi[3])):
        for k in K_ESATTI:
            for c in CONDIZIONI_GRIGLIA:
                linee.append(
                    riga_segni(
                        f"{prima} k={k}",
                        altri(misure[(prima, k)]),
                        f"{dopo} k={k}",
                        altri(misure[(dopo, k)]),
                        c,
                    )
                )
    elenchi = {
        nome: json.loads(
            (
                cartella_modello(nome) / f"elenchi_esatti_{lato}_{SUFFISSO_INTERA}.json"
            ).read_text(encoding="utf-8")
        )
        for nome in ("v0", PARTE_97)
    }
    file_apistici = {r["nome_file"] for r in file_per_bando[APISTICI]}
    for k in K_ESATTI:
        conti = {
            nome: {
                r["riga"]: apistici_dei_primi(
                    elenchi[nome], f"{r['riga']} A k={k}", file_apistici
                )
                for r in altri(misure[("v0", k)])
            }
            for nome in elenchi
        }
        piu = [r for r in conti["v0"] if conti[PARTE_97][r] > conti["v0"][r]]
        meno = [r for r in conti["v0"] if conti[PARTE_97][r] < conti["v0"][r]]
        linee.append(
            f"  frammenti degli apistici tra i primi {k} in A, fatti degli altri "
            f"bandi: in tutto {sum(conti['v0'].values())} con v0, "
            f"{sum(conti[PARTE_97].values())} con {PARTE_97}; fatti con più "
            f"frammenti degli apistici {len(piu)} "
            f"({', '.join(nome_della_riga(r) for r in piu) or '-'}), con meno "
            f"{len(meno)} ({', '.join(nome_della_riga(r) for r in meno) or '-'})"
        )

    testo = "\n".join(linee)
    (cartella / f"parte_{lato}_{SUFFISSO_INTERA}.txt").write_text(
        testo + "\n", encoding="utf-8"
    )
    print(testo)
    return 0


# --- contesto per frammento (21/11/2026, terza mossa del perimetro) ---
#
# Il contesto lo scrive scripts/diagnostica/genera_contesti.py; qui si
# misura. Tutte le configurazioni hanno il riordinatore piccolo (osiria) sui
# 30 candidati e la ricerca esatta; cambia dove entra il contesto:
#   c-0   da nessuna parte (deve rifare "osiria su v0" della notte);
#   c-R   solo nel testo che legge il riordinatore;
#   c-L   solo nella ricerca per parole;
#   c-LR  nella ricerca per parole e nel riordinatore;
#   c-LVR anche nel vettore, con il limite a 512 token (vettori v1+contesto).
# Righe del contesto (--righe): tutte, senza ARGOMENTO, senza SERVE A.
# I contesti con violazioni di contenuto, o da segno automatico del gemello
# non tolto dopo la lettura (genera_contesti.da_scartare), non entrano: quel
# frammento resta senza contesto. Le violazioni di sola forma non scartano
# il contesto. Oltre il 5% di contesti da scartare la misura non parte
# (decisioni del 21/11/2026: una sola revisione delle istruzioni, nata dai
# controlli; tre gruppi di violazioni, prima dei controlli sugli 871).
#
# Regola di adozione (decisa il 21/11/2026, prima di ogni misura): una
# configurazione si adotta solo se guadagna in B sia con k=10 sia con k=15
# contro c-0; "guadagna" vuol dire più guadagnati che persi con p ≤ 0,05.
#
# Domande a mano (--domande-a-mano): 30 fatti di taratura (DOMANDE_A_MANO),
# misurati con la domanda scritta da chi mantiene il progetto al posto di
# quella del foglio, nelle stesse configurazioni. Regola, decisa prima: il
# guadagno netto (guadagnati meno persi contro c-0, in B) "resta" se con le
# domande a mano è positivo e almeno metà di quello con le domande del
# foglio sugli stessi 30 fatti; "si riduce" se è positivo ma sotto la metà;
# "non resta" se è zero o negativo.
# Regola in più (decisa il 21/11/2026, prima di ogni misura): se una
# configurazione guadagna con le domande dei fogli ma non con le domande
# scritte a mano, non si adotta. "Non guadagna con le domande a mano": in B
# il guadagno netto contro c-0 è zero o negativo, a k=10 o a k=15
# (adottabile_con_mano).
# Secondo file (deciso il 21/11/2026, dopo la misura sulle prime 29):
# DOMANDE_A_MANO_2, altri 30 fatti di taratura, nessuno già nel primo file,
# stessa esclusione e stesse colonne, seme SEME_MANO_2. Con --domande-a-mano
# la misura usa tutti i file che ci sono; le righe con la domanda vuota si
# saltano con un avviso.
# Terzo file e contesto delle frasi (piano del 21/11/2026 sera):
# DOMANDE_A_MANO_3, tutti i fatti di taratura che non stanno nei primi due,
# senza il fondo strade. --contesto-domande-a-mano riscrive il secondo e il
# terzo, solo se nessuna domanda è compilata, con le colonne di
# COLONNE_CONTESTO prese dal testo pulito del documento (non scritte da un
# modello), e ne scrive una copia .xlsx con il testo a capo; la misura legge
# la copia .xlsx se c'è, altrimenti il .csv.

CARTELLA_CONTESTO = CARTELLA_19D / "contesto"
DOMANDE_A_MANO = CARTELLA_CONTESTO / "domande_a_mano.csv"
COLONNE_MANO = ["riga", "foglio", "titolo", "frase", "domanda_a_mano"]
SEME_MANO = 19_2026_1121
DOMANDE_A_MANO_2 = CARTELLA_CONTESTO / "domande_a_mano_2.csv"
SEME_MANO_2 = 19_2026_1122
DOMANDE_A_MANO_3 = CARTELLA_CONTESTO / "domande_a_mano_3.csv"
COLONNE_CONTESTO = ["file", "pagina", "testo_prima", "testo_dopo", "spiegata"]
# ordine delle colonne nei file con il contesto: la frase tra il testo prima e
# quello dopo, la domanda subito dopo
COLONNE_MANO_CONTESTO = [
    "riga",
    "foglio",
    "titolo",
    "file",
    "pagina",
    "testo_prima",
    "frase",
    "testo_dopo",
    "domanda_a_mano",
    "spiegata",
]
CARATTERI_CONTESTO = 400
NON_TROVATA = "frase non trovata nel testo pulito"
NUMERO_MANO = 30
ESCLUSO_MANO = "fondo-strade-piccoli-comuni-2026"
NESSUNA = "nessuna"
# BANDO la compone il programma; DOVE, ARGOMENTO e SERVE A le scrive il
# modello (revisione del 21/11/2026)
RIGHE_CONTESTO = {
    "tutte": ("bando", "dove", "argomento", "serve_a", "parole"),
    "senza-argomento": ("bando", "dove", "serve_a", "parole"),
    "senza-serve-a": ("bando", "dove", "argomento", "parole"),
    "senza-parole": ("bando", "dove", "argomento", "serve_a"),
    # aggiunte il 21/11/2026, prima della misura, per togliere una riga alla
    # volta anche BANDO e DOVE
    "senza-bando": ("dove", "argomento", "serve_a", "parole"),
    "senza-dove": ("bando", "argomento", "serve_a", "parole"),
}
NOME_RIGA = {
    "bando": "BANDO",
    "dove": "DOVE",
    "argomento": "ARGOMENTO",
    "serve_a": "SERVE A",
    "parole": "PAROLE",
}


@dataclass(frozen=True)
class ConfigContesto:
    lessicale: bool
    vettore: bool
    riordinatore: bool

    def descrizione(self) -> str:
        dove = [
            n
            for n, sì in (
                ("ricerca per parole", self.lessicale),
                ("vettore (limite 512 token)", self.vettore),
                ("riordinatore", self.riordinatore),
            )
            if sì
        ]
        return "contesto in: " + (", ".join(dove) if dove else "nessuna parte")


CONFIG_CONTESTO = {
    "c-0": ConfigContesto(False, False, False),
    "c-R": ConfigContesto(False, False, True),
    "c-L": ConfigContesto(True, False, False),
    "c-LR": ConfigContesto(True, False, True),
    "c-LVR": ConfigContesto(True, True, True),
}

for _righe in RIGHE_CONTESTO:
    MODELLI[f"v1+contesto-{_righe}"] = Modello(
        MINILM, 512, cartella=f"contesto/vettori-{_righe}", contesto=_righe
    )

# Tipo del fatto (colonna tipo_fatto, senza "(più punti)") -> voce dell'elenco
# chiuso di ARGOMENTO (genera_contesti.VOCI)
VOCE_DEL_TIPO = {
    "chi può partecipare": "chi può partecipare",
    "importo o massimale": "importi e massimali",
    "percentuale coperta o quota a carico": "percentuali di contributo",
    "spesa ammessa o esclusa": "spese ammesse o escluse",
    "punteggio o criterio di valutazione": "punteggi e criteri di valutazione",
    "procedura": "procedura e scadenze di presentazione",
    "vincoli dopo il contributo e revoca": "obblighi, vincoli e revoche",
    "cumulo con altri contributi": "cumulo con altri aiuti",
    "definizione": "altro",
}


def tipo_del_fatto(fatto: dict) -> str:
    tipo = re.sub(r"\s*\(più punti\)\s*$", "", str(fatto.get("tipo_fatto") or ""))
    return tipo.strip().lower()


def contesti_da(
    documenti,
    salvati: dict[str, dict],
    righe: str,
    tolti: set[tuple[str, str]] | None = None,
) -> tuple[dict[tuple[str, int], str], dict[str, list]]:
    """(contesto per (fonte, chunk_num), violazioni dei contesti scartati, per id).

    Ferma se manca un contesto o se i contesti da scartare superano la
    quota. Si scartano, e quei frammenti restano senza contesto, i contesti
    con violazioni di contenuto o da segno automatico non tolto
    (genera_contesti.da_scartare); quelli di sola forma restano. `tolti`: i
    segni automatici tolti dopo la lettura (genera_contesti.leggi_segni_tolti).
    """
    from scripts.diagnostica import genera_contesti as gc

    frammenti = [(d, f) for d in documenti for f in d.frammenti]
    mancanti = [f.id for _, f in frammenti if f.id not in salvati]
    if mancanti:
        raise ErroreMisura(
            f"{len(mancanti)} frammenti senza contesto: la generazione non è finita"
        )
    tutte, _ = gc.controlla_tutti(documenti, salvati, tolti=tolti)
    violazioni = {i: v for i, v in tutte.items() if gc.da_scartare(v)}
    quota = len(violazioni) / len(frammenti)
    if quota > gc.QUOTA_VIOLAZIONI:
        raise ErroreMisura(
            f"contesti con violazioni vere {len(violazioni)} su {len(frammenti)} "
            f"({quota:.1%}), oltre il {gc.QUOTA_VIOLAZIONI:.0%}: si rivedono le "
            "istruzioni una volta, a partire dai controlli"
        )
    contesti = {}
    for d, f in frammenti:
        if f.id in violazioni:
            continue
        testo = gc.testo_di_ricerca(
            salvati[f.id].get("righe") or {}, RIGHE_CONTESTO[righe]
        )
        if testo:
            contesti[(d.fonte, f.chunk_num)] = testo
    return contesti, violazioni


def leggi_contesti_generati():
    """(documenti, contesti salvati) di genera_contesti, con l'impronta di oggi."""
    from scripts.diagnostica import genera_contesti as gc

    try:
        documenti = gc.leggi_documenti()
        return documenti, gc.leggi_salvati(gc.FILE_CONTESTI, gc.impronta_istruzioni())
    except gc.ArrestoGenerazione as errore:
        raise ErroreMisura(str(errore)) from errore


def contesti_della_misura(documenti, salvati, righe: str):
    """contesti_da con i segni automatici tolti dopo la lettura (il file in
    dati-grezzi/prova/19d/contesto, se c'è)."""
    from scripts.diagnostica import genera_contesti as gc

    try:
        return contesti_da(documenti, salvati, righe, gc.leggi_segni_tolti())
    except gc.ArrestoGenerazione as errore:
        raise ErroreMisura(str(errore)) from errore


def contesti_per_frammento(righe: str) -> dict[tuple[str, int], str]:
    documenti, salvati = leggi_contesti_generati()
    return contesti_della_misura(documenti, salvati, righe)[0]


def nome_dei_vettori(config: ConfigContesto, righe: str) -> str:
    return f"v1+contesto-{righe}" if config.vettore else "v0"


def file_contesto(nome: str, righe: str, k: int, lato: str, mano: bool) -> Path:
    coda = "_mano" if mano else ""
    return CARTELLA_CONTESTO / "misure" / f"{nome}_{righe}_k{k}_{lato}{coda}.csv"


def testo_per_riordino(documento, contesti: dict | None) -> str:
    return testo_con_contesto(documento.page_content, documento.metadata, contesti)


def misura_riordinata(
    recupero,
    app,
    riordinatore,
    fatti: list[dict],
    file_per_bando: dict[str, list[dict]],
    frammenti_per_fonte: dict[str, list[Frammento]],
    titoli: dict[str, str],
    contesti_riordino: dict | None,
) -> tuple[dict[int, list[dict]], dict]:
    """Come esegui_riordino: 30 candidati, voti del riordinatore, primi 10 e 15.

    Con `contesti_riordino` il riordinatore legge contesto e frammento; la
    valutazione è sempre sul testo pulito del frammento.
    """
    import statistics
    import time

    from src.chains.rag import recupera
    from src.recupero_documenti import documenti_nominati
    from src.retrieval import normalizza_domanda

    massimo = riordinatore.max_seq_length
    tokenizer = riordinatore.tokenizer
    righe = {k: [] for k in K_ESATTI}
    tra_i_candidati = dict.fromkeys(CONDIZIONI_GRIGLIA, 0)
    tempi = {c: [] for c in CONDIZIONI_GRIGLIA}
    lunghe = dict.fromkeys(CONDIZIONI_GRIGLIA, 0)
    coppie = dict.fromkeys(CONDIZIONI_GRIGLIA, 0)
    for fatto in fatti:
        giusti, gemelli = documenti_del_fatto(fatto, file_per_bando)
        domanda = normalizza_domanda(str(fatto["domanda"]))
        ripulita = domanda_ripulita(domanda, titoli[fatto["id_bando"]])
        candidati = {
            "A": [d for d, _, _ in recupera(app, fatto["domanda"], k=CANDIDATI)],
            "B": [
                d
                for d, _, _ in recupero.cerca_nel_bando(
                    ripulita, fatto["id_bando"], CANDIDATI
                )
            ],
        }
        domande = {"A": domanda, "B": ripulita}
        riordinati = {}
        for c in CONDIZIONI_GRIGLIA:
            docs = candidati[c]
            if trovato_in(fatto, [frammento_di(d) for d in docs], giusti):
                tra_i_candidati[c] += 1
            testi = [
                (domande[c], testo_per_riordino(d, contesti_riordino)) for d in docs
            ]
            inizio = time.perf_counter()
            voti = riordinatore.predict(testi, show_progress_bar=False) if docs else []
            tempi[c].append(time.perf_counter() - inizio)
            for q, testo in testi:
                coppie[c] += 1
                lunghe[c] += len(tokenizer(q, testo)["input_ids"]) > massimo
            riordinati[c] = [docs[i] for i in riordina(voti, len(docs))]
        nominati = set(documenti_nominati(domanda, app.titoli))
        for k in K_ESATTI:
            esiti = {
                c: valuta(
                    fatto,
                    [frammento_di(d) for d in riordinati[c][:k]],
                    [frammento_di(d) for d in riordinati[c]],
                    giusti,
                    gemelli,
                    frammenti_per_fonte,
                )
                for c in CONDIZIONI_GRIGLIA
            }
            di_sempre = sum(not d.metadata.get("sha256") for d in riordinati["A"][:k])
            righe[k].append(
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
    dati = {
        "trovati_tra_i_candidati": tra_i_candidati,
        "coppie": coppie,
        "coppie_troncate": lunghe,
        "lunghezza_massima": massimo,
        "tempo_per_domanda_s": {
            c: {"media": statistics.mean(v), "mediana": statistics.median(v)}
            for c, v in tempi.items()
            if v
        },
    }
    return righe, dati


def apri_contesto(nome_vettori: str, contesti_lessicali: dict | None):
    """(recupero, app, frammenti per fonte, titoli) sui vettori dati, ricerca esatta."""
    from src.recupero_documenti import avvolgi

    modello = MODELLI[nome_vettori]
    ids, testi, metadati, matrice = leggi_vettori(cartella_modello(nome_vettori))
    store = StoreEsatto(
        ids, testi, metadati, matrice, crea_embeddings_di(modello), modello.domanda
    )
    recupero = apri_recupero(Path(), store=store, contesti=contesti_lessicali)
    frammenti_per_fonte, titoli = frammenti_della_copia(recupero, modello.limite)
    return recupero, avvolgi(recupero), frammenti_per_fonte, titoli


# --- domande a mano ---


def riga_nel_foglio(riga) -> int:
    numero = int(riga)
    return numero - SCOSTAMENTO_2 if numero >= SCOSTAMENTO_2 else numero


def chiave_a_mano(f: dict) -> tuple[int, int]:
    """(foglio, riga nel foglio) di un fatto o di una riga dei file a mano."""
    return int(f["foglio"]), riga_nel_foglio(f["riga"])


def scelta_a_mano(
    fatti: list[dict],
    n: int = NUMERO_MANO,
    seme: int = SEME_MANO,
    esclusi: frozenset[tuple[int, int]] = frozenset(),
) -> list[dict]:
    """n fatti a caso, ripartiti tra i bandi in proporzione, senza il fondo strade
    e senza i fatti di esclusi (chiavi di chiave_a_mano).

    Quote per bando: parte intera di n * fatti del bando / fatti, poi un
    fatto in più ai bandi con il resto più grande (a parità, per id_bando).
    Dentro ogni bando, in ordine di id_bando, si estrae con random.Random(seme)
    dai fatti in ordine di riga.
    """
    per_bando: dict[str, list[dict]] = defaultdict(list)
    for f in fatti:
        if f["id_bando"] != ESCLUSO_MANO and chiave_a_mano(f) not in esclusi:
            per_bando[f["id_bando"]].append(f)
    totale = sum(len(v) for v in per_bando.values())
    if totale < n:
        raise ErroreMisura(f"{totale} fatti, ne servono {n}")
    esatte = {b: n * len(v) / totale for b, v in per_bando.items()}
    quote = {b: int(q) for b, q in esatte.items()}
    resti = sorted(per_bando, key=lambda b: (-(esatte[b] - quote[b]), b))
    for b in resti[: n - sum(quote.values())]:
        quote[b] += 1
    generatore = random.Random(seme)
    scelti = []
    for b in sorted(per_bando):
        ordine = sorted(per_bando[b], key=lambda f: int(f["riga"]))
        scelti += generatore.sample(ordine, quote[b])
    return sorted(scelti, key=lambda f: (int(f["foglio"]), riga_nel_foglio(f["riga"])))


def righe_a_mano(scelti: list[dict]) -> list[dict]:
    return [
        {
            "riga": riga_nel_foglio(f["riga"]),
            "foglio": int(f["foglio"]),
            "titolo": str(f.get("titolo") or "").strip(),
            "frase": str(f["frase"]).strip(),
            "domanda_a_mano": "",
        }
        for f in scelti
    ]


def _testo_cella(valore) -> str:
    """Una cella dell'.xlsx come testo: vuota "", 13.0 (Google Sheet) "13"."""
    if valore is None:
        return ""
    if isinstance(valore, float) and valore.is_integer():
        return str(int(valore))
    return str(valore)


def _righe_xlsx(percorso: Path) -> list[dict]:
    from openpyxl import load_workbook

    libro = load_workbook(percorso, read_only=True, data_only=True)
    try:
        valori = list(libro.worksheets[0].iter_rows(values_only=True))
    finally:
        libro.close()
    if not valori:
        return []
    testa = [_testo_cella(v).strip() for v in valori[0]]
    righe = []
    for riga in valori[1:]:
        celle = [_testo_cella(v) for v in riga] + [""] * (len(testa) - len(riga))
        if any(c.strip() for c in celle):
            righe.append(dict(zip(testa, celle, strict=False)))
    return righe


def leggi_domande_a_mano(percorso: Path) -> list[dict]:
    """Le righe del file; .xlsx, o .csv con separatore virgola o punto e virgola
    (Excel). Le colonne in più si ignorano."""
    if percorso.suffix.lower() == ".xlsx":
        righe = _righe_xlsx(percorso)
    else:
        testo = percorso.read_text(encoding="utf-8-sig")
        prima = testo.splitlines()[0] if testo else ""
        separatore = ";" if prima.count(";") > prima.count(",") else ","
        righe = list(csv.DictReader(io.StringIO(testo), delimiter=separatore))
    if not righe or set(COLONNE_MANO) - set(righe[0]):
        raise ErroreMisura(f"{percorso.name}: servono le colonne {COLONNE_MANO}")
    return righe


def rimanenti_a_mano(
    fatti: list[dict], esclusi: frozenset[tuple[int, int]]
) -> list[dict]:
    """Tutti i fatti senza il fondo strade e senza quelli di esclusi, in ordine
    di foglio e riga."""
    return sorted(
        (
            f
            for f in fatti
            if f["id_bando"] != ESCLUSO_MANO and chiave_a_mano(f) not in esclusi
        ),
        key=chiave_a_mano,
    )


def chiavi_dei_file(percorsi: tuple[Path, ...]) -> frozenset[tuple[int, int]]:
    """Le chiavi dei fatti dei file a mano dati; si ferma se ne manca uno."""
    chiavi = set()
    for percorso in percorsi:
        if not percorso.exists():
            raise ErroreMisura(f"manca {percorso.name}: il file nuovo lo esclude")
        chiavi |= {chiave_a_mano(r) for r in leggi_domande_a_mano(percorso)}
    return frozenset(chiavi)


def esegui_prepara_a_mano(secondo: bool = False, terzo: bool = False) -> int:
    """Scrive DOMANDE_A_MANO (o DOMANDE_A_MANO_2, senza i fatti del primo, o
    DOMANDE_A_MANO_3, tutti quelli che non stanno nei primi due), o se c'è già
    dice se le righe sono quelle della scelta."""
    _, fatti, _ = fatti_intera(TARATURA)
    percorso, seme, esclusi = DOMANDE_A_MANO, SEME_MANO, frozenset()
    if secondo:
        percorso, seme = DOMANDE_A_MANO_2, SEME_MANO_2
        esclusi = chiavi_dei_file((DOMANDE_A_MANO,))
    if terzo:
        percorso = DOMANDE_A_MANO_3
        esclusi = chiavi_dei_file((DOMANDE_A_MANO, DOMANDE_A_MANO_2))
        scelti = rimanenti_a_mano(fatti, esclusi)
    else:
        scelti = scelta_a_mano(fatti, seme=seme, esclusi=esclusi)
    nuove = righe_a_mano(scelti)
    chiavi = [(r["foglio"], r["riga"]) for r in nuove]
    per_bando = Counter(
        f["id_bando"]
        for f in fatti
        if (int(f["foglio"]), riga_nel_foglio(f["riga"])) in set(chiavi)
    )
    if percorso.exists():
        vecchie = leggi_domande_a_mano(percorso)
        uguali = [(int(r["foglio"]), int(r["riga"])) for r in vecchie] == chiavi
        print(
            f"{percorso} esiste già e non si sovrascrive: le righe "
            + (
                "coincidono con la scelta."
                if uguali
                else "NON coincidono con la scelta."
            )
        )
        return 0 if uguali else 1
    percorso.parent.mkdir(parents=True, exist_ok=True)
    with percorso.open("w", encoding="utf-8-sig", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=COLONNE_MANO, lineterminator="\n")
        scrittore.writeheader()
        scrittore.writerows(nuove)
    scelta = "tutti i rimanenti" if terzo else f"seme {seme}"
    fuori = sum(f["id_bando"] == ESCLUSO_MANO for f in fatti)
    print(
        f"Scritto {percorso}: {len(nuove)} fatti di taratura ({scelta}); "
        f"fuori per l'esclusione di {ESCLUSO_MANO}: {fuori}"
    )
    for b, n in sorted(per_bando.items()):
        print(f"  {b}: {n}")
    return 0


def testo_prima(testo: str, inizio_frase: int, n: int = CARATTERI_CONTESTO) -> str:
    """Circa n caratteri prima della frase, senza la parola tagliata in testa."""
    inizio = max(0, inizio_frase - n)
    tratto = testo[inizio:inizio_frase]
    if inizio > 0 and not testo[inizio - 1].isspace():
        tratto = re.sub(r"^\S*", "", tratto, count=1)
    return ("… " if inizio > 0 else "") + tratto.strip()


def testo_dopo(testo: str, fine_frase: int, n: int = CARATTERI_CONTESTO) -> str:
    """Circa n caratteri dopo la frase, senza la parola tagliata in coda."""
    fine = min(len(testo), fine_frase + n)
    tratto = testo[fine_frase:fine]
    if fine < len(testo) and not testo[fine].isspace():
        tratto = re.sub(r"\S*$", "", tratto, count=1)
    return tratto.strip() + (" …" if fine < len(testo) else "")


def tratto_del_pezzo(pezzo: list[str], fr: Frammento) -> tuple[int, int] | None:
    """Inizio e fine del pezzo nel testo: le celle in ordine, ognuna dopo la
    precedente; se così non si trova, come contiene (ogni cella per sé)."""
    da, inizio = 0, None
    for cella in pezzo:
        compatta = livello_c(cella)
        k = fr.compatto.find(compatta, da) if compatta else -1
        if k < 0:
            return contiene(pezzo, fr)
        inizio = k if inizio is None else inizio
        da = k + len(compatta)
    if inizio is None:
        return None
    return fr.mappa[inizio], fr.mappa[da - 1] + 1


def _per_pezzo(valori: list[str], uno_se_uguali: bool = False) -> str:
    """Il valore di un pezzo solo; per più pezzi "[pezzo N] …", uno per
    paragrafo, o il valore una volta se uno_se_uguali e sono tutti uguali."""
    if len(valori) == 1 or (uno_se_uguali and len(set(valori)) == 1):
        return valori[0]
    return "\n\n".join(f"[pezzo {i}] {v}" for i, v in enumerate(valori, 1))


def contesto_delle_frasi(
    fatti: list[dict], file_per_bando: dict[str, list[dict]], documenti
) -> dict[tuple[int, int], dict[str, str]]:
    """Per ogni fatto, le colonne di COLONNE_CONTESTO dal testo pulito dei suoi
    file giusti (genera_contesti.Documento.testo, come lo vede spezza).

    Ogni pezzo si cerca come nella misura (primo punto in cui compare, file
    giusti in ordine di nome), le celle di una tabella in ordine
    (tratto_del_pezzo). La pagina è pagina_fisica del
    foglio. Niente è scritto da un modello; "spiegata" resta vuota.
    """
    interi = {d.fonte: (d, Frammento(-1, 0, d.testo, len(d.testo))) for d in documenti}
    uscita = {}
    for fatto in fatti:
        giusti, _ = documenti_del_fatto(fatto, file_per_bando)
        file, prima, dopo = [], [], []
        for pezzo in unita_del_fatto(fatto):
            trovato = next(
                (
                    (interi[f][0], t)
                    for f in sorted(giusti)
                    if f in interi and (t := tratto_del_pezzo(pezzo, interi[f][1]))
                ),
                None,
            )
            if trovato is None:
                file.append(NON_TROVATA)
                prima.append("")
                dopo.append("")
                continue
            d, (a, b) = trovato
            file.append(d.fonte + (f" ({d.parte})" if d.parte else ""))
            prima.append(testo_prima(d.testo, a))
            dopo.append(testo_dopo(d.testo, b))
        uscita[chiave_a_mano(fatto)] = {
            "file": _per_pezzo(file, uno_se_uguali=True),
            "pagina": _testo_cella(fatto.get("pagina_fisica")).strip(),
            "testo_prima": _per_pezzo(prima),
            "testo_dopo": _per_pezzo(dopo),
            "spiegata": "",
        }
    return uscita


def compilate(righe: list[dict]) -> list[dict]:
    return [r for r in righe if str(r.get("domanda_a_mano") or "").strip()]


def righe_con_contesto(
    righe: list[dict], fatti: list[dict], contesti: dict[tuple[int, int], dict]
) -> list[dict]:
    """Le stesse righe, nello stesso ordine, con le colonne del contesto."""
    per_chiave = {chiave_a_mano(f): f for f in fatti}
    uscita = []
    for r in righe:
        chiave = chiave_a_mano(r)
        if chiave not in per_chiave or chiave not in contesti:
            raise ErroreMisura(f"riga {chiave} non tra i fatti di taratura")
        if str(per_chiave[chiave]["frase"]).strip() != str(r["frase"]).strip():
            raise ErroreMisura(f"riga {chiave}: la frase non è quella del foglio")
        valori = {c: str(r.get(c) or "") for c in COLONNE_MANO} | contesti[chiave]
        uscita.append({c: valori[c] for c in COLONNE_MANO_CONTESTO})
    return uscita


def scrivi_csv_a_mano(percorso: Path, righe: list[dict], colonne: list[str]) -> None:
    with percorso.open("w", encoding="utf-8-sig", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=colonne, lineterminator="\n")
        scrittore.writeheader()
        scrittore.writerows(righe)


LARGHEZZE_XLSX = {"testo_prima": 60, "frase": 60, "testo_dopo": 60}
LARGHEZZE_XLSX |= {"domanda_a_mano": 50, "titolo": 30, "file": 30}


def scrivi_xlsx_a_mano(percorso: Path, righe: list[dict], colonne: list[str]) -> None:
    """Copia .xlsx: testo a capo, celle in alto, intestazione ferma, tutto testo."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    libro = Workbook()
    foglio = libro.active
    foglio.title = "domande"
    foglio.append(colonne)
    for r in righe:
        foglio.append([str(r.get(c) or "") for c in colonne])
    a_capo = Alignment(wrap_text=True, vertical="top")
    for riga in foglio.iter_rows():
        for cella in riga:
            cella.data_type = "s"  # niente formule né numeri: "=…" resta testo
            cella.alignment = a_capo
    for cella in foglio[1]:
        cella.font = Font(bold=True)
        larghezza = LARGHEZZE_XLSX.get(cella.value, 10)
        foglio.column_dimensions[cella.column_letter].width = larghezza
    foglio.freeze_panes = "A2"
    libro.save(percorso)


def file_da_leggere(percorso: Path) -> Path | None:
    """La copia .xlsx se c'è, altrimenti il .csv, o None se non c'è nessuno dei due.

    Si ferma se ci sono tutti e due e il .csv ha domande compilate: si
    compila una copia sola.
    """
    copia = percorso.with_suffix(".xlsx")
    if not copia.exists():
        return percorso if percorso.exists() else None
    if percorso.exists() and compilate(leggi_domande_a_mano(percorso)):
        raise ErroreMisura(
            f"{percorso.name} ha domande compilate ma c'è anche {copia.name}: "
            "si compila una copia sola, l'altra si toglie"
        )
    return copia


def esegui_contesto_a_mano(
    percorsi: tuple[Path, ...] = (DOMANDE_A_MANO_2, DOMANDE_A_MANO_3),
) -> int:
    """Riscrive i file dati con le colonne del contesto, più la copia .xlsx.

    Prima controlla tutti i file: se uno ha una domanda compilata (nel .csv o
    nella copia .xlsx) non si scrive niente.
    """
    from scripts.diagnostica import genera_contesti as gc

    presenti = [p for p in percorsi if p.exists()]
    if not presenti:
        raise ErroreMisura(f"manca {percorsi[0].name}")
    da_scrivere = []
    for p in presenti:
        righe = leggi_domande_a_mano(p)
        copia = p.with_suffix(".xlsx")
        piene = compilate(righe) + (
            compilate(leggi_domande_a_mano(copia)) if copia.exists() else []
        )
        if piene:
            raise ErroreMisura(
                f"{p.name}: {len(piene)} domande già compilate: non si riscrive"
            )
        da_scrivere.append((p, righe))
    _, fatti, file_per_bando = fatti_intera(TARATURA)
    chiavi = {chiave_a_mano(r) for _, righe in da_scrivere for r in righe}
    try:
        documenti = gc.leggi_documenti()
    except gc.ArrestoGenerazione as errore:
        raise ErroreMisura(str(errore)) from errore
    contesti = contesto_delle_frasi(
        [f for f in fatti if chiave_a_mano(f) in chiavi], file_per_bando, documenti
    )
    for p, righe in da_scrivere:
        nuove = righe_con_contesto(righe, fatti, contesti)
        scrivi_csv_a_mano(p, nuove, COLONNE_MANO_CONTESTO)
        scrivi_xlsx_a_mano(p.with_suffix(".xlsx"), nuove, COLONNE_MANO_CONTESTO)
        mancate = sum(NON_TROVATA in r["file"] for r in nuove)
        pezzi = sum("[pezzo " in r["testo_prima"] for r in nuove)
        print(
            f"Riscritto {p} e {p.with_suffix('.xlsx').name}: {len(nuove)} righe, "
            f"{pezzi} a più pezzi, {mancate} con un pezzo non trovato"
        )
    return 0


def con_domande_a_mano(
    fatti: list[dict], percorso: Path = DOMANDE_A_MANO, salta_vuote: bool = False
) -> list[dict]:
    """I fatti del file, con la domanda scritta a mano al posto di quella del foglio.

    Una riga con la domanda vuota ferma tutto, o con salta_vuote si salta con
    un avviso.
    """
    righe = leggi_domande_a_mano(percorso)
    per_chiave = {(int(f["foglio"]), riga_nel_foglio(f["riga"])): f for f in fatti}
    vuote = [r for r in righe if not str(r["domanda_a_mano"] or "").strip()]
    if vuote and not salta_vuote:
        raise ErroreMisura(
            f"domande a mano vuote alle righe {', '.join(r['riga'] for r in vuote)}"
        )
    if vuote:
        print(
            f"Avviso: {percorso.name}, {len(vuote)} righe con la domanda vuota "
            "saltate: "
            + ", ".join(f"foglio {r['foglio']} riga {r['riga']}" for r in vuote)
        )
        righe = [r for r in righe if r not in vuote]
    uscita = []
    for r in righe:
        chiave = (int(r["foglio"]), int(r["riga"]))
        if chiave not in per_chiave:
            raise ErroreMisura(f"riga {chiave} non tra i fatti di taratura")
        fatto = per_chiave[chiave]
        if str(fatto["frase"]).strip() != r["frase"].strip():
            raise ErroreMisura(f"riga {chiave}: la frase non è quella del foglio")
        uscita.append({**fatto, "domanda": r["domanda_a_mano"].strip()})
    return uscita


def con_i_file_a_mano(
    fatti: list[dict],
    percorsi: tuple[Path, ...] = (DOMANDE_A_MANO, DOMANDE_A_MANO_2, DOMANDE_A_MANO_3),
) -> list[dict]:
    """I fatti di tutti i file a mano che ci sono (la copia .xlsx se c'è),
    insieme, senza le righe vuote; si ferma se un fatto compare due volte."""
    presenti = [p for p in map(file_da_leggere, percorsi) if p is not None]
    if not presenti:
        raise ErroreMisura(f"manca {percorsi[0].name}")
    uscita, viste = [], set()
    for percorso in presenti:
        dal_file = con_domande_a_mano(fatti, percorso, salta_vuote=True)
        chiavi = {chiave_a_mano(f) for f in dal_file}
        if len(chiavi) < len(dal_file):
            raise ErroreMisura(f"{percorso.name}: un fatto compare due volte")
        if viste & chiavi:
            raise ErroreMisura(
                f"{percorso.name}: fatti già in un altro file {sorted(viste & chiavi)}"
            )
        viste |= chiavi
        print(f"{percorso.name}: {len(dal_file)} domande a mano nella misura")
        uscita += dal_file
    if not uscita:
        raise ErroreMisura("nessuna domanda a mano compilata")
    return uscita


# --- misura e rapporti ---


def esegui_contesto(lato: str, nome: str, righe: str, mano: bool) -> int:
    import json
    import time

    from scripts.ingestione.carica_avvisi import senza_rete
    from src.config import CHROMA_DIR

    if mano and lato != TARATURA:
        raise ErroreMisura("le domande a mano sono fatti di taratura")
    config = CONFIG_CONTESTO[nome]
    if nome == "c-0":
        righe = NESSUNA
    senza_rete()
    _, fatti, file_per_bando = fatti_intera(lato)
    if mano:
        fatti = con_i_file_a_mano(fatti)
    contesti = contesti_per_frammento(righe) if righe != NESSUNA else {}
    nome_vettori = nome_dei_vettori(config, righe)
    prima = impronte_cartella(CHROMA_DIR)
    inizio = time.perf_counter()
    with senza_connessioni():
        from sentence_transformers import CrossEncoder

        recupero, app, frammenti_per_fonte, titoli = apri_contesto(
            nome_vettori, contesti if config.lessicale else None
        )
        riordinatore = CrossEncoder(
            RIORDINATORI[RIORDINATORE_PICCOLO],
            trust_remote_code=False,
            local_files_only=True,
        )
        per_k, dati = misura_riordinata(
            recupero,
            app,
            riordinatore,
            fatti,
            file_per_bando,
            frammenti_per_fonte,
            titoli,
            contesti if config.riordinatore else None,
        )
        del recupero, app, riordinatore
    if impronte_cartella(CHROMA_DIR) != prima:
        raise ErroreMisura("le impronte del Chroma vero sono cambiate")
    for k in K_ESATTI:
        percorso = file_contesto(nome, righe, k, lato, mano)
        percorso.parent.mkdir(parents=True, exist_ok=True)
        scrivi_misura(percorso, per_k[k])
    dati.update(
        configurazione=nome,
        descrizione=config.descrizione(),
        righe=righe,
        vettori=nome_vettori,
        frammenti_con_contesto=len(contesti),
        domande_a_mano=mano,
        fatti=len(fatti),
        chroma_vero=f"{len(prima)} file, impronte uguali prima e dopo",
        tempo_s=time.perf_counter() - inizio,
    )
    json_ = file_contesto(nome, righe, K, lato, mano).with_suffix(".json")
    json_.write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{nome} ({config.descrizione()}), righe {righe}, vettori {nome_vettori}")
    for k in K_ESATTI:
        r = per_k[k]
        print(f"  k={k}: A {_trovati(r, 'A')[0]}, B {_trovati(r, 'B')[0]} su {len(r)}")
    print(
        f"  tra i {CANDIDATI} candidati: {dati['trovati_tra_i_candidati']}; coppie "
        f"oltre {dati['lunghezza_massima']} token: {dati['coppie_troncate']}"
    )
    return 0


def _apistici(r: dict) -> bool:
    return r["id_bando"] == APISTICI


GRUPPI_CONTESTO = [
    ("tutti", lambda r: True),
    ("apistici", _apistici),
    ("altri bandi", lambda r: not _apistici(r)),
]


def misure_contesto(lato: str, mano: bool) -> dict[tuple[str, str], dict[int, list]]:
    """Le misure scritte, per (configurazione, righe), con tutti e due i k."""
    misure = {}
    for nome in CONFIG_CONTESTO:
        for righe in [NESSUNA] if nome == "c-0" else list(RIGHE_CONTESTO):
            file_ = {k: file_contesto(nome, righe, k, lato, mano) for k in K_ESATTI}
            if all(p.exists() for p in file_.values()):
                misure[(nome, righe)] = {k: leggi_misura(p) for k, p in file_.items()}
    return misure


def _scegli(righe: list[dict], scelta) -> list[dict]:
    return [r for r in righe if scelta(r)]


def adottabile(base: dict[int, list], variante: dict[int, list]) -> bool:
    """La regola di adozione: in B, più guadagnati che persi con p ≤ 0,05, a k=10 e 15."""
    for k in K_ESATTI:
        guadagnati, persi = cambi_di_esito(base[k], variante[k], "B")
        if len(guadagnati) <= len(persi):
            return False
        if probabilita_segni(len(guadagnati), len(persi)) > SOGLIA_CASO:
            return False
    return True


def adottabile_con_mano(
    base: dict[int, list],
    variante: dict[int, list],
    base_mano: dict[int, list],
    variante_mano: dict[int, list],
) -> bool:
    """La regola di adozione, più quella delle domande a mano: in B il netto
    contro c-0 con le domande a mano è positivo sia a k=10 sia a k=15."""
    return adottabile(base, variante) and all(
        _netto(base_mano[k], variante_mano[k], "B") > 0 for k in K_ESATTI
    )


def esito_a_mano(netto_foglio: int, netto_mano: int) -> str:
    """La regola delle domande a mano (decisa prima della misura)."""
    if netto_foglio <= 0:
        return "nessun guadagno con le domande del foglio: niente da verificare"
    if netto_mano <= 0:
        return "non resta"
    return "resta" if 2 * netto_mano >= netto_foglio else "si riduce"


def _netto(base: list[dict], variante: list[dict], c: str) -> int:
    guadagnati, persi = cambi_di_esito(base, variante, c)
    return len(guadagnati) - len(persi)


def parole_dal_contesto(
    fatto: dict,
    domanda: str,
    giusti: set[str],
    frammenti_per_fonte: dict[str, list[Frammento]],
    righe_del_frammento,
) -> tuple[list[str], dict[str, list[str]]] | None:
    """(parole della domanda simili nel frammento, parole simili solo nel contesto
    per riga) sul primo frammento giusto che contiene il primo pezzo."""
    from src.database.interrogazioni_bandi import _simili

    pezzo = unita_del_fatto(fatto)[0]
    for fonte in sorted(giusti):
        for fr in frammenti_per_fonte.get(fonte, []):
            if contiene(pezzo, fr):
                _, nel_frammento = parole_in_comune(domanda, fr.testo)
                solo = {}
                for riga, testo in (
                    righe_del_frammento(fonte, fr.chunk_num) or {}
                ).items():
                    parole = parole_significative(testo)
                    solo[riga] = [
                        p
                        for p in parole_significative(domanda)
                        if p not in nel_frammento and any(_simili(p, q) for q in parole)
                    ]
                return nel_frammento, solo
    return None


def esegui_rapporto_contesto(lato: str) -> int:
    import json

    from scripts.diagnostica import genera_contesti as gc
    from src.retrieval import normalizza_domanda

    if lato != TARATURA:
        raise ErroreMisura("il rapporto del contesto si fa solo sulla taratura")
    misure = misure_contesto(lato, False)
    if ("c-0", NESSUNA) not in misure:
        raise ErroreMisura("manca la misura di c-0: serve --contesto c-0")
    base = misure[("c-0", NESSUNA)]
    documenti, salvati = leggi_contesti_generati()
    _, violazioni = contesti_della_misura(documenti, salvati, "tutte")
    _, fatti, file_per_bando = fatti_intera(lato)
    fatto_di = {str(f["riga"]): f for f in fatti}
    frammenti_per_fonte, _ = frammenti_dei_vettori()
    id_di = {(d.fonte, f.chunk_num): f.id for d in documenti for f in d.frammenti}

    def righe_del_frammento(fonte, chunk):
        i = id_di.get((fonte, chunk))
        if i is None or i in violazioni:
            return {}
        return salvati[i].get("righe") or {}

    linee = [
        f"Passo 19d, contesto per frammento, metà: {lato}",
        (
            f"Contesti: {gc.FILE_CONTESTI.name}, modello {gc.MODELLO}, impronta "
            f"{gc.impronta_istruzioni()[:12]}; {len(salvati)} frammenti, con "
            f"violazioni vere (senza contesto nella misura) {len(violazioni)}"
        ),
        (
            f"Riordinatore {RIORDINATORI[RIORDINATORE_PICCOLO]}, {CANDIDATI} candidati, "
            "ricerca esatta; base c-0 = osiria su v0"
        ),
        NOTA_SEGNI,
        (
            "Regola di adozione: guadagno in B con k=10 e con k=15 contro c-0 (più "
            "guadagnati che persi, p ≤ 0,05)."
        ),
        "",
    ]

    # 0. c-0 contro la misura della notte
    linee.append("0. c-0 contro osiria su v0 della notte (notte/riordino)")
    for k in K_ESATTI:
        notte = file_riordino(RIORDINATORE_PICCOLO, "v0", k, lato)
        if not notte.exists():
            linee.append(f"  k={k}: manca {notte.name}")
            continue
        vecchie = {r["riga"]: r for r in leggi_misura(notte)}
        diverse = [r["riga"] for r in base[k] if vecchie.get(r["riga"]) != r]
        linee.append(
            f"  k={k}: "
            + (
                "righe identiche"
                if not diverse and len(vecchie) == len(base[k])
                else "righe diverse: " + ", ".join(nome_della_riga(x) for x in diverse)
            )
        )

    # 1. tabella
    for gruppo, scelta in GRUPPI_CONTESTO:
        n = len(_scegli(base[K], scelta))
        linee += [
            "",
            (
                f"1. Fatti trovati, A / B, {gruppo} ({n}); 1° B e ≤5 B con k=10; "
                f"tetto: giusto tra i {CANDIDATI} candidati, A / B (solo per tutti)"
            ),
            (
                f"  {'configurazione':<28}{'k=10':>10}{'k=15':>10}{'1° B':>7}"
                f"{'≤5 B':>7}{'tetto':>10}"
            ),
        ]
        for (nome, righe), m in misure.items():
            celle = [
                f"{_trovati(_scegli(m[k], scelta), 'A')[0]} / "
                f"{_trovati(_scegli(m[k], scelta), 'B')[0]}"
                for k in K_ESATTI
            ]
            tetto = ""
            if gruppo == "tutti":
                percorso = file_contesto(nome, righe, K, lato, False).with_suffix(
                    ".json"
                )
                t = json.loads(percorso.read_text(encoding="utf-8"))
                tetto = f"{t['trovati_tra_i_candidati']['A']} / " + str(
                    t["trovati_tra_i_candidati"]["B"]
                )
            linee.append(
                f"  {nome + ' ' + righe:<28}{celle[0]:>10}{celle[1]:>10}"
                f"{_primi_entro(_scegli(m[K], scelta), 'B', 1):>7}"
                f"{_primi_entro(_scegli(m[K], scelta), 'B', 5):>7}{tetto:>10}"
            )

    # 2. confronti con c-0
    linee += ["", "2. Confronti con c-0"]
    for (nome, righe), m in misure.items():
        if nome == "c-0":
            continue
        linee.append(
            f"  {nome} {righe}: regola di adozione con le domande dei fogli "
            + ("SODDISFATTA" if adottabile(base, m) else "non soddisfatta")
            + " (va confermata con le domande a mano, sezione 6)"
        )
        for gruppo, scelta in GRUPPI_CONTESTO:
            for k in K_ESATTI:
                for c in CONDIZIONI_GRIGLIA:
                    linee.append(
                        riga_segni(
                            f"c-0 k={k}",
                            _scegli(base[k], scelta),
                            f"{nome} {righe} k={k}",
                            _scegli(m[k], scelta),
                            c,
                        ).replace("  ", f"  [{gruppo}] ", 1)
                    )

    # 3. per foglio
    linee += ["", "3. Guadagnati e persi in B per foglio"]
    for (nome, righe), m in misure.items():
        if nome == "c-0":
            continue
        for foglio in (1, 2):
            for k in K_ESATTI:
                linee.append(
                    riga_segni(
                        f"c-0 k={k}",
                        [r for r in base[k] if foglio_della_riga(r["riga"]) == foglio],
                        f"{nome} {righe} k={k}",
                        [r for r in m[k] if foglio_della_riga(r["riga"]) == foglio],
                        "B",
                    ).replace("  ", f"  [foglio {foglio}] ", 1)
                )

    # 4. bando sbagliato
    linee += ["", "4. Presi dal bando o dall'allegato sbagliato prima del giusto"]
    for (nome, righe), m in misure.items():
        for k in K_ESATTI:
            for c in CONDIZIONI_GRIGLIA:
                gemelle, altri = gemelli_presi(m[k], c)
                linee.append(
                    f"  {nome} {righe} k={k} {c}: frasi gemelle "
                    f"{', '.join(gemelle) or '-'}; altri {', '.join(altri) or '-'}"
                )

    # 5. parole in comune per i fatti guadagnati
    linee += [
        "",
        (
            "5. Fatti guadagnati in B contro c-0: parole della domanda (B) simili "
            "solo nel contesto del primo frammento giusto, per riga (rischio: "
            "domande e contesti scritti da un modello)"
        ),
    ]
    for (nome, righe), m in misure.items():
        if nome == "c-0":
            continue
        for k in K_ESATTI:
            guadagnati, _ = cambi_di_esito(base[k], m[k], "B")
            per_riga: Counter = Counter()
            con_solo = 0
            dettagli = []
            for riga in guadagnati:
                fatto = fatto_di[riga]
                r = next(x for x in m[k] if x["riga"] == riga)
                domanda = r["domanda_B"] or normalizza_domanda(str(fatto["domanda"]))
                giusti, _ = documenti_del_fatto(fatto, file_per_bando)
                esito = parole_dal_contesto(
                    fatto, domanda, giusti, frammenti_per_fonte, righe_del_frammento
                )
                if esito is None:
                    continue
                _, solo = esito
                usate = {
                    q: p for q, p in solo.items() if p and q in RIGHE_CONTESTO[righe]
                }
                if usate:
                    con_solo += 1
                    per_riga.update(usate.keys())
                    dettagli.append(
                        f"{nome_della_riga(riga)} ("
                        + "; ".join(
                            f"{NOME_RIGA[q]}: {', '.join(p)}" for q, p in usate.items()
                        )
                        + ")"
                    )
            linee.append(
                f"  {nome} {righe} k={k}: guadagnati {len(guadagnati)}, con parole solo "
                f"nel contesto {con_solo}; per riga: "
                + (", ".join(f"{NOME_RIGA[q]} {n}" for q, n in per_riga.items()) or "-")
            )
            if dettagli:
                linee.append("    " + "; ".join(dettagli))

    # 6. domande a mano
    mano = misure_contesto(lato, True)
    linee += ["", "6. Domande a mano (30 fatti di taratura)"]
    if ("c-0", NESSUNA) not in mano:
        linee.append("  non misurate: serve --contesto c-0 --domande-a-mano")
    else:
        base_mano = mano[("c-0", NESSUNA)]
        dei_30 = {r["riga"] for r in base_mano[K]}
        linee.append(
            "  regola: il guadagno netto in B resta se con le domande a mano è "
            "positivo e almeno metà di quello con le domande del foglio sugli stessi "
            "fatti; si riduce se è positivo ma sotto la metà; non resta se è zero o "
            "negativo"
        )
        for (nome, righe), m in mano.items():
            if nome == "c-0" or (nome, righe) not in misure:
                continue
            linee.append(
                f"  {nome} {righe}: regola di adozione con le domande a mano "
                + (
                    "SODDISFATTA"
                    if adottabile_con_mano(base, misure[(nome, righe)], base_mano, m)
                    else "non soddisfatta"
                )
            )
            for k in K_ESATTI:
                foglio_base = [r for r in base[k] if r["riga"] in dei_30]
                foglio_var = [
                    r for r in misure[(nome, righe)][k] if r["riga"] in dei_30
                ]
                celle = []
                for c in CONDIZIONI_GRIGLIA:
                    nf = _netto(foglio_base, foglio_var, c)
                    nm = _netto(base_mano[k], m[k], c)
                    celle.append(f"{c}: foglio {nf:+d}, a mano {nm:+d}")
                verdetto = esito_a_mano(
                    _netto(foglio_base, foglio_var, "B"),
                    _netto(base_mano[k], m[k], "B"),
                )
                linee.append(
                    f"  {nome} {righe} k={k}: " + "; ".join(celle) + f" -> {verdetto}"
                )
                for c in CONDIZIONI_GRIGLIA:
                    linee.append(
                        "    a mano "
                        + riga_segni(
                            f"c-0 k={k}", base_mano[k], f"{nome} k={k}", m[k], c
                        ).strip()
                    )

    # 7. tempi e troncamenti
    linee += ["", "7. Riordinatore: tempi per domanda e coppie oltre il limite"]
    for nome, righe in misure:
        percorso = file_contesto(nome, righe, K, lato, False).with_suffix(".json")
        t = json.loads(percorso.read_text(encoding="utf-8"))
        tempi = "; ".join(
            f"{c} {v['media'] * 1000:.0f} ms"
            for c, v in t["tempo_per_domanda_s"].items()
        )
        linee.append(
            f"  {nome} {righe}: {tempi}; coppie oltre {t['lunghezza_massima']} token "
            + ", ".join(
                f"{c} {t['coppie_troncate'][c]} su {t['coppie'][c]}"
                for c in CONDIZIONI_GRIGLIA
            )
        )

    testo = "\n".join(linee)
    uscita = CARTELLA_CONTESTO / f"rapporto_contesto_{lato}.txt"
    uscita.write_text(testo + "\n", encoding="utf-8")
    print(testo)
    return 0


def esegui_argomenti_contesto(lato: str) -> int:
    """Quante volte la voce di ARGOMENTO del frammento della risposta è il tipo del fatto.

    Misura dell'affidabilità dell'etichetta, non una variante di ricerca:
    nessuna ricerca, solo i frammenti che contengono i pezzi del fatto.
    """
    if lato != TARATURA:
        raise ErroreMisura("gli argomenti si contano solo sulla taratura")
    documenti, salvati = leggi_contesti_generati()
    _, violazioni = contesti_della_misura(documenti, salvati, "tutte")
    _, fatti, file_per_bando = fatti_intera(lato)
    frammenti_per_fonte, _ = frammenti_dei_vettori()
    id_di = {(d.fonte, f.chunk_num): f.id for d in documenti for f in d.frammenti}
    ignoti = sorted({tipo_del_fatto(f) for f in fatti} - set(VOCE_DEL_TIPO))
    if ignoti:
        raise ErroreMisura(f"tipi di fatto senza voce: {ignoti}")
    esiti = conta_argomenti(
        fatti, file_per_bando, frammenti_per_fonte, id_di, salvati, violazioni
    )
    linee = [
        f"Passo 19d, ARGOMENTO del contesto contro il tipo del fatto, metà: {lato}",
        (
            "Frammento della risposta: il primo frammento giusto (per file e "
            "chunk_num) che contiene il primo pezzo; 'almeno uno': uno qualunque "
            "dei frammenti giusti che contengono un pezzo. Voce attesa da "
            "VOCE_DEL_TIPO."
        ),
        "",
    ]
    linee += righe_argomenti(esiti)
    testo = "\n".join(linee)
    uscita = CARTELLA_CONTESTO / f"argomenti_{lato}.txt"
    uscita.write_text(testo + "\n", encoding="utf-8")
    print(testo)
    return 0


def conta_argomenti(
    fatti, file_per_bando, frammenti_per_fonte, id_di, salvati, violazioni
) -> list[dict]:
    """Per fatto: tipo, voce attesa, voci del primo frammento, coincidenze."""
    esiti = []
    for fatto in fatti:
        giusti, _ = documenti_del_fatto(fatto, file_per_bando)
        voce = VOCE_DEL_TIPO[tipo_del_fatto(fatto)]
        contenenti = []
        for numero, pezzo in enumerate(unita_del_fatto(fatto)):
            for fonte in sorted(giusti):
                for fr in frammenti_per_fonte.get(fonte, []):
                    if contiene(pezzo, fr):
                        contenenti.append((numero, fonte, fr.chunk_num))
        esito = {"riga": fatto["riga"], "id_bando": fatto["id_bando"]}
        esito.update(tipo=tipo_del_fatto(fatto), voce=voce, primo=None, uno=False)
        if not contenenti:
            esito["stato"] = "senza frammento"
            esiti.append(esito)
            continue
        voci_di = {}
        for _, fonte, chunk in contenenti:
            i = id_di[(fonte, chunk)]
            voci_di[(fonte, chunk)] = (
                None if i in violazioni else salvati[i].get("argomento_voci") or []
            )
        _, fonte, chunk = contenenti[0]
        primo = voci_di[(fonte, chunk)]
        if primo is None:
            esito["stato"] = "contesto escluso"
        else:
            esito["stato"] = "valutato"
            esito["primo"] = primo
        esito["uno"] = any(v and voce in v for v in voci_di.values())
        esiti.append(esito)
    return esiti


def righe_argomenti(esiti: list[dict]) -> list[str]:
    valutati = [e for e in esiti if e["stato"] == "valutato"]
    linee = [
        (
            f"Fatti {len(esiti)}; valutati {len(valutati)}; senza frammento "
            f"{sum(e['stato'] == 'senza frammento' for e in esiti)}; contesto del "
            f"primo frammento escluso "
            f"{sum(e['stato'] == 'contesto escluso' for e in esiti)}"
        ),
    ]
    for gruppo, scelta in GRUPPI_CONTESTO:
        sue = [e for e in valutati if scelta(e)]
        linee.append(
            f"  {gruppo}: coincide nel primo frammento "
            f"{sum(e['voce'] in e['primo'] for e in sue)} su {len(sue)}; in almeno uno "
            f"{sum(e['uno'] for e in sue)}"
        )
    linee += [
        "",
        "Per tipo del fatto: coincide / valutati; voci date al primo frammento",
    ]
    for tipo in sorted({e["tipo"] for e in valutati}):
        sue = [e for e in valutati if e["tipo"] == tipo]
        voci = Counter(v for e in sue for v in (e["primo"] or ["(nessuna)"]))
        linee.append(
            f"  {tipo} ({VOCE_DEL_TIPO[tipo]}): "
            f"{sum(e['voce'] in e['primo'] for e in sue)} / {len(sue)}; "
            + ", ".join(f"{v} {n}" for v, n in voci.most_common())
        )
    mancati = [
        f"{nome_della_riga(e['riga'])} ({e['tipo']} -> {', '.join(e['primo']) or '-'})"
        for e in valutati
        if e["voce"] not in e["primo"]
    ]
    linee += ["", "Non coincidono: " + ("; ".join(mancati) or "-")]
    return linee


# --- uso ---


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dividi", action="store_true", help="tempo 1: divisione")
    parser.add_argument(
        "--dividi-secondo",
        action="store_true",
        help="divisione del secondo foglio dei fatti (FOGLIO_2), con i vincoli dal primo",
    )
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
    parser.add_argument(
        "--esatta-intera",
        action="store_true",
        help="misura esatta sui due fogli dei fatti insieme, per --modello",
    )
    parser.add_argument(
        "--riepilogo-intero",
        action="store_true",
        help="riepilogo delle misure esatte sui due fogli",
    )
    parser.add_argument(
        "--notte",
        type=int,
        choices=(1, 2, 3, 4),
        help="misure della notte del 20/11/2026 (4: riordino con --riordinatore)",
    )
    parser.add_argument(
        "--scarica-riordinatore",
        choices=sorted(RIORDINATORI),
        help="scarica un riordinatore da huggingface.co (unica rete autorizzata)",
    )
    parser.add_argument("--riordinatore", choices=sorted(RIORDINATORI))
    parser.add_argument(
        "--parte-97",
        action="store_true",
        help=(
            "rapporto del nome dell'azione degli apistici sui 97 fatti: v0+parte "
            "contro v0, senza e con il riordinatore piccolo"
        ),
    )
    parser.add_argument(
        "--contesto",
        choices=sorted(CONFIG_CONTESTO),
        help="contesto per frammento: misura una configurazione (con osiria)",
    )
    parser.add_argument(
        "--righe",
        choices=sorted(RIGHE_CONTESTO),
        default="tutte",
        help="righe del contesto che entrano nella ricerca (con --contesto)",
    )
    parser.add_argument(
        "--domande-a-mano",
        action="store_true",
        help=(
            "con --contesto: i fatti di domande_a_mano.csv e, se ci sono, di "
            "domande_a_mano_2 e _3 (.xlsx se c'è, altrimenti .csv), domanda "
            "scritta a mano; righe vuote saltate"
        ),
    )
    parser.add_argument(
        "--rapporto-contesto",
        action="store_true",
        help="rapporto delle misure del contesto contro c-0",
    )
    parser.add_argument(
        "--argomenti-contesto",
        action="store_true",
        help="ARGOMENTO del frammento della risposta contro il tipo del fatto",
    )
    parser.add_argument(
        "--prepara-domande-a-mano",
        action="store_true",
        help="scrive domande_a_mano.csv (30 fatti di taratura, seme fisso)",
    )
    parser.add_argument(
        "--prepara-domande-a-mano-2",
        action="store_true",
        help="scrive domande_a_mano_2.csv (altri 30 fatti, non nel primo file)",
    )
    parser.add_argument(
        "--prepara-domande-a-mano-3",
        action="store_true",
        help="scrive domande_a_mano_3.csv (tutti i fatti non nei primi due file)",
    )
    parser.add_argument(
        "--contesto-domande-a-mano",
        action="store_true",
        help=(
            "riscrive domande_a_mano_2 e _3 con il testo intorno alla frase, "
            "solo se nessuna domanda è compilata, più una copia .xlsx"
        ),
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
        argomenti.dividi_secondo,
        argomenti.misura,
        argomenti.riepilogo,
        argomenti.griglia,
        argomenti.apistici,
        argomenti.prepara_vettori,
        argomenti.esatta,
        argomenti.peso,
        argomenti.esatta_intera,
        argomenti.riepilogo_intero,
        argomenti.notte is not None,
        argomenti.scarica_riordinatore is not None,
        argomenti.parte_97,
        argomenti.contesto is not None,
        argomenti.rapporto_contesto,
        argomenti.argomenti_contesto,
        argomenti.prepara_domande_a_mano,
        argomenti.prepara_domande_a_mano_2,
        argomenti.prepara_domande_a_mano_3,
        argomenti.contesto_domande_a_mano,
    )
    if sum(comandi) != 1:
        print(
            "Serve un comando solo: --dividi, --dividi-secondo, --misura, "
            "--riepilogo, --griglia, "
            "--apistici, --prepara-vettori, --esatta, --peso, --esatta-intera "
            "--riepilogo-intero, --notte, --scarica-riordinatore, --parte-97, "
            "--contesto, --rapporto-contesto, --argomenti-contesto o "
            "--prepara-domande-a-mano, --prepara-domande-a-mano-2, "
            "--prepara-domande-a-mano-3 o --contesto-domande-a-mano.",
            file=sys.stderr,
        )
        return 2
    try:
        if argomenti.dividi_secondo:
            return esegui_divisione_2()
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
        if argomenti.esatta_intera:
            return esegui_esatta_intera(lato, argomenti.modello)
        if argomenti.riepilogo_intero:
            return esegui_riepilogo_intero(lato)
        if argomenti.scarica_riordinatore:
            return esegui_scarica_riordinatore(argomenti.scarica_riordinatore)
        if argomenti.parte_97:
            return esegui_parte_97(lato)
        if argomenti.contesto:
            return esegui_contesto(
                lato, argomenti.contesto, argomenti.righe, argomenti.domande_a_mano
            )
        if argomenti.rapporto_contesto:
            return esegui_rapporto_contesto(lato)
        if argomenti.argomenti_contesto:
            return esegui_argomenti_contesto(lato)
        if argomenti.prepara_domande_a_mano:
            return esegui_prepara_a_mano()
        if argomenti.prepara_domande_a_mano_2:
            return esegui_prepara_a_mano(secondo=True)
        if argomenti.prepara_domande_a_mano_3:
            return esegui_prepara_a_mano(terzo=True)
        if argomenti.contesto_domande_a_mano:
            return esegui_contesto_a_mano()
        if argomenti.notte == 4:
            if not argomenti.riordinatore:
                return esegui_rapporto_riordino(lato)
            return esegui_riordino(lato, argomenti.riordinatore, argomenti.modello)
        if argomenti.notte:
            parti = {1: esegui_notte_1, 2: esegui_notte_2, 3: esegui_notte_3}
            return parti[argomenti.notte](lato)
        cartella = argomenti.cartella or CARTELLA_19D / argomenti.variante
        return esegui_misura(
            argomenti.foglio, argomenti.divisione, lato, argomenti.variante, cartella
        )
    except (ErroreDivisione, ErroreMisura) as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
