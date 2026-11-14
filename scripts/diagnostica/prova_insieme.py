"""Insieme di prova dell'app su domande realistiche.

Il file delle domande sta fuori dal repository,
dati-grezzi/prova/domande_complete.txt, una domanda per riga:

    gruppo | codice | domanda | atteso

gruppo: comuni, privati, aperte, viste (già usate: solo nel lotto 1, mai
nella misura a freddo). atteso è facoltativo, più voci separate da ";":
un titolo o parte di titolo di un bando che deve comparire tra i bandi
citati; "non: titolo" per un bando che non deve comparire; "a mano: testo"
per una cosa da giudicare a mano. Le righe che cominciano con "#" sono
commenti.

Modi:

    --dividi                    divide le domande in 4 lotti, stratificati
                                per gruppo, con un seme fisso; scrive
                                dati-grezzi/prova/lotti.json, una volta sola
    --stima --lotto N           codice, gruppo e lunghezza delle domande del
                                lotto e costo stimato, senza modello
    --registra --lotto N        ogni domanda con la catena dell'app, ente
                                Comune di Abetone Cutigliano; il router si
                                chiama 3 volte e la catena prosegue con la
                                prima risposta
    --registra --lotto N --riprendi CARTELLA
                                completa una registrazione interrotta,
                                nella stessa cartella
    --riverifica CARTELLA       solo il verificatore sulle risposte salvate
    --riepilogo                 le misure a freddo dei lotti registrati

Ogni registrazione va in dati-grezzi/prova/lotto_N/<data-ora>/: meta.json
(data, commit, impronta dei CSV di data/processed, stato), un file JSON per
domanda in domande/ con tutto ciò che serve a riverificare, rapporto.md. La
prima registrazione di un lotto è "a freddo" e non si sovrascrive: ogni
registrazione nuova ha la sua cartella. Le riverifiche vanno in
CARTELLA/riverifiche/<data-ora>/, con esiti.json e rapporto.md.

Giudizi a mano in dati-grezzi/prova/lotto_N/giudizi.csv: lo script vi
aggiunge le righe da giudicare (non trovate, senza fonte, citate con il
blocco, il campione dei verificati, le attese "a mano") e non tocca mai un
giudizio scritto. Il rapporto conta i giudizi; quello di una riverifica
mostra solo le righe senza giudizio.

Lo script lavora solo sul lotto indicato.

Uso: python -m scripts.diagnostica.prova_insieme --dividi
"""

import argparse
import csv
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import traceback
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from langchain_core.callbacks import get_usage_metadata_callback
from langchain_core.documents import Document

from scripts.ingestione.estrai_nuovi import (
    PREZZO_INGRESSO,
    PREZZO_USCITA,
    costo_reale,
    errore_bloccante,
)
from src.chains.router import pulisci_json
from src.config import (
    CHUNK_SIZE,
    DATI_GREZZI_DIR,
    ENTE_PREDEFINITO,
    MODEL_NAME,
    PROCESSED_DIR,
    ROOT_DIR,
)
from src.database.modelli import Approfondimento, Risultato, VoceBando, bandi_citati
from src.verification.controllo import giudizio, verifica

CARTELLA_PROVA = DATI_GREZZI_DIR / "prova"
FILE_DOMANDE = CARTELLA_PROVA / "domande_complete.txt"
FILE_LOTTI = CARTELLA_PROVA / "lotti.json"

GRUPPI_MISURATI = ("comuni", "privati", "aperte")
GRUPPO_VISTE = "viste"
GRUPPI = (*GRUPPI_MISURATI, GRUPPO_VISTE)

NUMERO_LOTTI = 4
# Semi fissi, salvati in lotti.json e in meta.json: la divisione e il
# campione dei verificati si rifanno uguali
SEME_DIVISIONE = 20261114
SEME_CAMPIONE = 20261115
CAMPIONE_VERIFICATI = 10

CHIAMATE_ROUTER = 3

GIUDIZI = (
    "falso_allarme_data",
    "falso_allarme_numero",
    "falso_allarme_etichetta",
    "falso_allarme_titolo",
    "errore_vero",
    "verificato_a_torto",
    "corretto",
)
COLONNE_GIUDIZI = ("codice", "valore", "contesto", "giudizio", "nota")

# Il valore delle righe dei giudizi che vengono dalle attese "a mano:"
VALORE_A_MANO = "a mano"

STATI = ("verificato", "non_trovato", "non_citato", "citazione_generica")

# Stima del costo prima di ogni misura. Il prompt del router si misura in
# caratteri; quello della risposta si stima: istruzioni, profilo, domanda,
# K frammenti di CHUNK_SIZE caratteri con l'intestazione, e un margine per
# il blocco dei dati. I caratteri diventano token con un rapporto
# prudente per l'italiano. Dopo la prima registrazione si usano le medie
# misurate.
CARATTERI_PER_TOKEN = 3.2
MARGINE_INTESTAZIONE = 1.15
MARGINE_DATI = 8000
USCITA_ROUTER = 80
USCITA_RISPOSTA = (800, 1500)

FUSO = ZoneInfo("Europe/Rome")


class ErroreProva(Exception):
    """Un errore dell'insieme di prova da mostrare senza traccia."""


class Bloccante(Exception):
    """Credito esaurito o autenticazione rifiutata: la corsa si ferma."""


# --- Lettura del file delle domande ---


@dataclass
class Domanda:
    """Una riga del file delle domande."""

    gruppo: str
    codice: str
    testo: str
    attese: list[str] = field(default_factory=list)
    vietate: list[str] = field(default_factory=list)
    a_mano: list[str] = field(default_factory=list)


def leggi_domande(testo: str) -> list[Domanda]:
    """Le domande del file, con le attese divise per tipo.

    Gli errori indicano il numero di riga e il codice, mai il testo
    della domanda.
    """
    domande = []
    codici = set()
    for numero, riga in enumerate(testo.splitlines(), start=1):
        riga = riga.strip()
        if not riga or riga.startswith("#"):
            continue
        parti = [p.strip() for p in riga.split("|")]
        if len(parti) not in (3, 4):
            raise ErroreProva(
                f"riga {numero}: {len(parti)} campi invece di 3 o 4 separati da |"
            )
        gruppo, codice, domanda = parti[:3]
        if gruppo not in GRUPPI:
            raise ErroreProva(f"riga {numero}: gruppo sconosciuto {gruppo!r}")
        if not codice or not domanda:
            raise ErroreProva(f"riga {numero}: codice o domanda vuoti")
        if codice in codici:
            raise ErroreProva(f"riga {numero}: codice ripetuto {codice!r}")
        codici.add(codice)

        voce = Domanda(gruppo, codice, domanda)
        for atteso in (parti[3] if len(parti) == 4 else "").split(";"):
            atteso = atteso.strip()
            minuscolo = atteso.lower()
            if not atteso:
                continue
            if minuscolo.startswith("non:"):
                voce.vietate.append(atteso[4:].strip())
            elif minuscolo.startswith("a mano:"):
                voce.a_mano.append(atteso[7:].strip())
            else:
                voce.attese.append(atteso)
        domande.append(voce)
    return domande


def impronta(percorso: Path) -> str:
    """L'impronta sha256 del contenuto di un file."""
    return hashlib.sha256(percorso.read_bytes()).hexdigest()


def carica_domande(percorso: Path = FILE_DOMANDE) -> list[Domanda]:
    """Le domande del file, che resta fuori dal repository."""
    if not percorso.exists():
        raise ErroreProva(f"file delle domande non trovato: {percorso}")
    return leggi_domande(percorso.read_text(encoding="utf-8"))


# --- Divisione in lotti ---


def dividi(domande: list[Domanda], seme: int, lotti: int = NUMERO_LOTTI) -> dict:
    """I codici per lotto, stratificati per gruppo.

    Per ogni gruppo misurato i codici, in ordine alfabetico e poi
    mescolati con il seme, vanno a turno nei lotti: le proporzioni tra i
    gruppi sono le stesse in ogni lotto, a meno di una domanda. Il turno
    continua da un gruppo all'altro e comincia dal lotto 2, perché il
    lotto 1 riceve in più tutte le domande "viste".
    """
    casuale = random.Random(seme)
    divisione = {n: [] for n in range(1, lotti + 1)}
    turno = 1
    for gruppo in GRUPPI_MISURATI:
        codici = sorted(d.codice for d in domande if d.gruppo == gruppo)
        casuale.shuffle(codici)
        for codice in codici:
            divisione[turno % lotti + 1].append(codice)
            turno += 1
    divisione[1] += sorted(d.codice for d in domande if d.gruppo == GRUPPO_VISTE)
    return divisione


def conteggi_lotti(domande: list[Domanda], divisione: dict) -> str:
    """La tabella dei conteggi per gruppo e lotto, senza le domande."""
    gruppo_di = {d.codice: d.gruppo for d in domande}
    lotti = sorted(divisione)
    righe = ["gruppo    " + "".join(f"lotto {n:<4}" for n in lotti) + "totale"]
    for gruppo in GRUPPI:
        conti = [sum(gruppo_di[c] == gruppo for c in divisione[n]) for n in lotti]
        righe.append(
            f"{gruppo:<10}" + "".join(f"{c:<10}" for c in conti) + str(sum(conti))
        )
    totali = [len(divisione[n]) for n in lotti]
    righe.append("totale    " + "".join(f"{c:<10}" for c in totali) + str(sum(totali)))
    return "\n".join(righe)


def scrivi_lotti(
    domande: list[Domanda],
    percorso: Path,
    impronta_domande: str,
    seme: int = SEME_DIVISIONE,
) -> dict:
    """Divide e scrive lotti.json. Non rifà una divisione esistente."""
    if percorso.exists():
        raise ErroreProva(f"{percorso} esiste già: la divisione non si rifà")
    divisione = dividi(domande, seme)
    gruppo_di = {d.codice: d.gruppo for d in domande}
    contenuto = {
        "creato": adesso().isoformat(timespec="seconds"),
        "seme": seme,
        "impronta_domande": impronta_domande,
        "lotti": {
            str(n): [{"codice": c, "gruppo": gruppo_di[c]} for c in codici]
            for n, codici in divisione.items()
        },
    }
    percorso.parent.mkdir(parents=True, exist_ok=True)
    scrivi_json(percorso, contenuto)
    return divisione


def domande_del_lotto(
    lotto: int,
    percorso_lotti: Path = FILE_LOTTI,
    percorso_domande: Path = FILE_DOMANDE,
) -> list[Domanda]:
    """Le domande di un lotto, nell'ordine della divisione.

    Avvisa se il file delle domande è cambiato dopo la divisione; si
    ferma se un codice del lotto non c'è più.
    """
    if not percorso_lotti.exists():
        raise ErroreProva("lotti.json non trovato: lancia prima --dividi")
    lotti = leggi_json(percorso_lotti)
    if str(lotto) not in lotti["lotti"]:
        raise ErroreProva(f"lotto {lotto} inesistente")
    if impronta(percorso_domande) != lotti["impronta_domande"]:
        print("ATTENZIONE: il file delle domande è cambiato dopo la divisione.")
    per_codice = {d.codice: d for d in carica_domande(percorso_domande)}
    codici = [v["codice"] for v in lotti["lotti"][str(lotto)]]
    mancanti = [c for c in codici if c not in per_codice]
    if mancanti:
        raise ErroreProva(f"codici del lotto non più nel file: {', '.join(mancanti)}")
    return [per_codice[c] for c in codici]


# --- Controllo delle attese ---


def normalizza(testo: str) -> str:
    """Il testo per il confronto: apostrofi, maiuscole e spazi uniformi."""
    testo = unicodedata.normalize("NFKC", testo)
    testo = testo.replace("\u2019", "'").replace("\u2018", "'")
    return " ".join(testo.casefold().split())


def controlla_attese(domanda: Domanda, titoli: list[str]) -> dict:
    """Le attese trovate e mancanti, e le vietate comparse, tra i titoli citati."""
    titoli_n = [normalizza(t) for t in titoli]

    def compare(atteso: str) -> bool:
        cercato = normalizza(atteso)
        return any(cercato in t for t in titoli_n)

    return {
        "trovate": [a for a in domanda.attese if compare(a)],
        "mancanti": [a for a in domanda.attese if not compare(a)],
        "vietate_comparse": [v for v in domanda.vietate if compare(v)],
    }


# --- Router chiamato tre volte ---


def interpretabile(grezzo: str) -> bool:
    """La risposta del router si legge come la legge decidi: un oggetto JSON."""
    try:
        return isinstance(json.loads(pulisci_json(grezzo)), dict)
    except json.JSONDecodeError:
        return False


class RouterTriplo:
    """Il router dell'app chiamato più volte sulla stessa entrata.

    Conserva tutte le risposte grezze e il consumo di token delle
    chiamate; restituisce la prima, con cui la catena prosegue.
    """

    def __init__(self, router, volte: int = CHIAMATE_ROUTER) -> None:
        self.router = router
        self.volte = volte
        self.grezzi: list[str] = []
        self.uso: dict = {}

    def azzera(self) -> None:
        """Dimentica le chiamate della domanda precedente."""
        self.grezzi = []
        self.uso = {}

    def invoke(self, entrata):
        self.azzera()
        with get_usage_metadata_callback() as contatore:
            for _ in range(self.volte):
                self.grezzi.append(self.router.invoke(entrata))
        self.uso = dict(contatore.usage_metadata)
        return self.grezzi[0]


def esito_router(grezzi: list[str]) -> dict:
    """Riuscito se la prima risposta è interpretabile; anomalie su tutte."""
    letti = [interpretabile(g) for g in grezzi]
    return {
        "riuscito": bool(letti) and letti[0],
        "anomalie": letti.count(False),
        "chiamate": len(letti),
    }


# --- Conversione da e verso JSON, per la riverifica ---


def esiti_dati_in_json(esiti_dati: list) -> list[dict]:
    """Gli esiti delle interrogazioni come dizionari."""
    return [{"nome": nome, "risultato": asdict(r)} for nome, r in esiti_dati or []]


def esiti_dati_da_json(voci: list[dict]) -> list:
    """Gli esiti delle interrogazioni ricostruiti dai dizionari."""
    esiti = []
    for voce in voci:
        r = dict(voce["risultato"])
        r["voci"] = [VoceBando(**v) for v in r.get("voci", [])]
        r["da_approfondire"] = [
            Approfondimento(**a) for a in r.get("da_approfondire", [])
        ]
        esiti.append((voce["nome"], Risultato(**r)))
    return esiti


def documenti_in_json(documenti: list[Document]) -> list[dict]:
    """I frammenti come dizionari, con i metadati."""
    return [{"page_content": d.page_content, "metadata": d.metadata} for d in documenti]


def documenti_da_json(voci: list[dict]) -> list[Document]:
    """I frammenti ricostruiti dai dizionari."""
    return [
        Document(page_content=v["page_content"], metadata=v["metadata"]) for v in voci
    ]


# --- Verifica di una risposta ---


def verifica_risposta(domanda: Domanda, risposta: str, documenti, esiti_dati) -> dict:
    """Il verificatore e il controllo delle attese su una risposta."""
    esiti = verifica(risposta, documenti, esiti_dati)
    citati = bandi_citati(risposta, esiti_dati)
    livello, messaggio = giudizio(esiti)
    return {
        "esiti_verifica": [asdict(e) for e in esiti],
        "giudizio": {"livello": livello, "messaggio": messaggio},
        "bandi_citati": [asdict(v) for v in citati],
        "attese_esito": controlla_attese(domanda, [v.titolo or v.url for v in citati]),
    }


def verifica_protetta(domanda: Domanda, risposta: str, documenti, esiti_dati) -> dict:
    """Come verifica_risposta, ma un errore del verificatore non si propaga.

    L'errore va in errore_verifica, con la traccia, e la risposta resta
    da riverificare con --riverifica dopo la correzione. Senza errore,
    errore_verifica è None: in una riverifica cancella quello precedente.
    """
    try:
        esito = verifica_risposta(domanda, risposta, documenti, esiti_dati)
    except Exception as errore:  # noqa: BLE001 - un errore non ferma le altre domande
        return {
            "esiti_verifica": [],
            "giudizio": None,
            "bandi_citati": [],
            "attese_esito": {},
            "errore_verifica": f"{type(errore).__name__}: {errore}",
            "traccia_verifica": traceback.format_exc(),
        }
    return {**esito, "errore_verifica": None, "traccia_verifica": None}


def domanda_di(voce: dict) -> Domanda:
    """La domanda salvata in un file di risultato."""
    return Domanda(
        voce["gruppo"],
        voce["codice"],
        voce["domanda"],
        voce.get("attese", []),
        voce.get("vietate", []),
        voce.get("a_mano", []),
    )


def riverifica_voce(voce: dict) -> dict:
    """La verifica rifatta sui dati salvati, senza modello."""
    if voce.get("errore") or "risposta" not in voce:
        return {"errore": voce.get("errore", "risposta mancante")}
    return verifica_protetta(
        domanda_di(voce),
        voce["risposta"],
        documenti_da_json(voce.get("documenti", [])),
        esiti_dati_da_json(voce.get("esiti_dati", [])),
    )


# --- Registrazione ---


def adesso() -> datetime:
    return datetime.now(FUSO)


def nome_cartella(momento: datetime) -> str:
    return momento.strftime("%Y-%m-%d_%H%M%S")


def nome_file(codice: str) -> str:
    """Il nome del file di una domanda: il codice, con i soli caratteri sicuri."""
    return re.sub(r"[^\w.-]", "_", codice) + ".json"


def scrivi_json(percorso: Path, contenuto) -> None:
    percorso.write_text(
        json.dumps(contenuto, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def leggi_json(percorso: Path):
    return json.loads(percorso.read_text(encoding="utf-8"))


def stato_git() -> dict:
    """Il commit corrente e se ci sono modifiche non salvate."""

    def git(*argomenti: str) -> str:
        risultato = subprocess.run(
            ["git", *argomenti],
            cwd=ROOT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        return risultato.stdout.strip()

    return {
        "commit": git("rev-parse", "HEAD"),
        "modifiche_non_salvate": bool(git("status", "--porcelain")),
    }


def impronta_csv(cartella: Path = PROCESSED_DIR) -> dict:
    """L'impronta di ogni CSV di data/processed e una complessiva."""
    per_file = {p.name: impronta(p) for p in sorted(cartella.glob("*.csv"))}
    complessiva = hashlib.sha256(
        "".join(f"{nome}:{h}\n" for nome, h in per_file.items()).encode()
    ).hexdigest()
    return {"file": per_file, "complessiva": complessiva}


def registrazioni(cartella_lotto: Path) -> list[Path]:
    """Le cartelle di registrazione di un lotto, dalla più vecchia."""
    if not cartella_lotto.exists():
        return []
    return sorted(p for p in cartella_lotto.iterdir() if (p / "meta.json").exists())


def registrazione_a_freddo(cartella_lotto: Path) -> Path | None:
    """La cartella della registrazione a freddo del lotto, se c'è."""
    for cartella in registrazioni(cartella_lotto):
        if leggi_json(cartella / "meta.json").get("a_freddo"):
            return cartella
    return None


def prepara_registrazione(cartella_lotto: Path, lotto: int, riprendi: Path | None):
    """La cartella della registrazione e il suo meta, nuova o da riprendere.

    Una registrazione nuova è a freddo se il lotto non ne ha altre. Si
    rifiuta se la corsa a freddo del lotto è incompleta: va ripresa.
    """
    if riprendi is not None:
        meta_path = riprendi / "meta.json"
        if not meta_path.exists():
            raise ErroreProva(f"{riprendi} non è una cartella di registrazione")
        meta = leggi_json(meta_path)
        if meta.get("lotto") != lotto:
            raise ErroreProva(
                f"{riprendi} è del lotto {meta.get('lotto')}, non {lotto}"
            )
        if meta.get("stato") == "completa":
            raise ErroreProva(f"{riprendi} è già completa: niente da riprendere")
        return riprendi, meta

    a_freddo = registrazione_a_freddo(cartella_lotto)
    if a_freddo is not None:
        meta_freddo = leggi_json(a_freddo / "meta.json")
        if meta_freddo.get("stato") != "completa":
            raise ErroreProva(
                f"la registrazione a freddo {a_freddo} è incompleta: "
                f"completala con --registra --lotto {lotto} --riprendi {a_freddo}"
            )

    momento = adesso()
    cartella = cartella_lotto / nome_cartella(momento)
    if cartella.exists():
        raise ErroreProva(f"{cartella} esiste già")
    meta = {
        "lotto": lotto,
        "inizio": momento.isoformat(timespec="seconds"),
        "fine": None,
        "stato": "incompleta",
        "a_freddo": not registrazioni(cartella_lotto),
        "modello": MODEL_NAME,
        "ente": ENTE_PREDEFINITO,
        "seme_campione": SEME_CAMPIONE,
        "riprese": [],
    }
    return cartella, meta


def costo_di(uso: dict) -> dict:
    """Token e dollari di un consumo di LangChain."""
    ingresso, uscita, dollari = costo_reale(uso or {})
    return {"ingresso": ingresso, "uscita": uscita, "dollari": round(dollari, 5)}


def differenza_uso(totale: dict, parte: dict) -> dict:
    """Il consumo del totale tolta una parte, per modello."""
    risultato = {}
    for modello, uso in (totale or {}).items():
        tolto = (parte or {}).get(modello, {})
        risultato[modello] = {
            chiave: uso.get(chiave, 0) - tolto.get(chiave, 0)
            for chiave in ("input_tokens", "output_tokens")
        }
    return risultato


def registra_domanda(
    catena, router: RouterTriplo, domanda: Domanda, percorso: Path
) -> dict:
    """Una domanda con la catena dell'app, con tutto ciò che serve a riverificarla.

    La voce si salva in percorso appena c'è la risposta, prima della
    verifica, e di nuovo con gli esiti: un errore del verificatore non
    perde la risposta, si registra nella voce e la corsa prosegue. Un
    errore della catena si registra nella voce; un errore bloccante ferma
    la corsa.
    """
    voce = {"momento": adesso().isoformat(timespec="seconds"), **asdict(domanda)}
    voce["domanda"] = voce.pop("testo")
    router.azzera()
    with get_usage_metadata_callback() as contatore:
        try:
            esito = catena.invoke(domanda.testo)
        except Exception as errore:  # noqa: BLE001 - un errore non ferma le altre domande
            if errore_bloccante(errore):
                raise Bloccante(str(errore)) from errore
            esito = None
            voce["errore"] = f"{type(errore).__name__}: {errore}"
    totale = dict(contatore.usage_metadata)

    voce["grezzi_router"] = list(router.grezzi)
    voce["router"] = esito_router(router.grezzi)
    voce["costo"] = {
        "router": costo_di(router.uso),
        "risposta": costo_di(differenza_uso(totale, router.uso)),
        "totale": costo_di(totale),
    }
    if esito is None:
        scrivi_json(percorso, voce)
        return voce

    voce.update(
        {
            "decisione": esito["decisione"],
            "esiti_dati": esiti_dati_in_json(esito.get("esiti_dati")),
            "dati": esito["dati"],
            "contesto": esito["contesto"],
            "profilo": esito["profilo"],
            "documenti": documenti_in_json(esito["documenti"]),
            "origini": esito.get("origini", []),
            "risposta": esito["risposta"],
        }
    )
    scrivi_json(percorso, voce)
    voce.update(
        verifica_protetta(
            domanda, esito["risposta"], esito["documenti"], esito.get("esiti_dati")
        )
    )
    scrivi_json(percorso, voce)
    return voce


def costruisci_catena_di_prova() -> tuple:
    """La catena dell'app per l'ente predefinito, con il router chiamato 3 volte.

    Il recupero come in carica_catena di app/app.py: Postgres con
    USA_POSTGRES=1 (predefinito), altrimenti quello locale.
    """
    from src.chains.rag import costruisci_catena
    from src.chains.router import costruisci_router

    router = RouterTriplo(costruisci_router())
    if os.getenv("USA_POSTGRES", "1") == "1":
        from src.pgstore import RecuperoPostgres

        catena = costruisci_catena(
            ENTE_PREDEFINITO, recupero=RecuperoPostgres(), router=router
        )
        return catena, router, "Postgres"
    return costruisci_catena(ENTE_PREDEFINITO, router=router), router, "Chroma"


def registra(lotto: int, riprendi: Path | None = None) -> Path:
    """Registra il lotto, o completa una registrazione interrotta."""
    from src.database.interrogazioni_bandi import data_di_oggi

    domande = domande_del_lotto(lotto)
    cartella_lotto = CARTELLA_PROVA / f"lotto_{lotto}"
    cartella, meta = prepara_registrazione(cartella_lotto, lotto, riprendi)
    cartella_domande = cartella / "domande"
    cartella_domande.mkdir(parents=True, exist_ok=True)

    git = stato_git()
    csv_ora = impronta_csv()
    impronta_domande = impronta(FILE_DOMANDE)
    if riprendi is None:
        meta.update(
            {
                "data_di_oggi": data_di_oggi().isoformat(),
                **git,
                "impronta_csv": csv_ora,
                "impronta_domande": impronta_domande,
                "codici": [d.codice for d in domande],
            }
        )
    else:
        if git["commit"] != meta.get("commit"):
            print("ATTENZIONE: il commit è cambiato dall'inizio della registrazione.")
        if csv_ora["complessiva"] != meta["impronta_csv"]["complessiva"]:
            print("ATTENZIONE: i CSV di data/processed sono cambiati.")
        if data_di_oggi().isoformat() != meta.get("data_di_oggi"):
            print("ATTENZIONE: la data di oggi è cambiata: stati dei bandi diversi.")
        meta["riprese"].append(
            {
                "momento": adesso().isoformat(timespec="seconds"),
                "data_di_oggi": data_di_oggi().isoformat(),
                **git,
                "impronta_csv": csv_ora["complessiva"],
            }
        )

    catena, router, recupero = costruisci_catena_di_prova()
    meta.setdefault("recupero", recupero)
    scrivi_json(cartella / "meta.json", meta)

    da_fare = [
        d for d in domande if not (cartella_domande / nome_file(d.codice)).exists()
    ]
    print(f"Lotto {lotto}, {cartella}")
    print(f"  a freddo: {'sì' if meta['a_freddo'] else 'no'}; da fare {len(da_fare)}")

    completa = False
    try:
        for numero, domanda in enumerate(da_fare, start=1):
            percorso = cartella_domande / nome_file(domanda.codice)
            voce = registra_domanda(catena, router, domanda, percorso)
            print(f"  {numero}/{len(da_fare)} {domanda.codice}: {riassunto_voce(voce)}")
        completa = True
    except Bloccante as errore:
        print(f"\nFERMATA: {errore}")
    except KeyboardInterrupt:
        print("\nFERMATA: interruzione da tastiera")
    finally:
        meta["stato"] = "completa" if completa else "incompleta"
        meta["fine"] = adesso().isoformat(timespec="seconds")
        scrivi_json(cartella / "meta.json", meta)

    voci = leggi_voci(cartella)
    precompila_giudizi(cartella_lotto / "giudizi.csv", voci, meta["seme_campione"])
    giudizi = leggi_giudizi(cartella_lotto / "giudizi.csv")
    (cartella / "rapporto.md").write_text(
        rapporto(voci, meta, giudizi, f"Lotto {lotto}, registrazione"),
        encoding="utf-8",
    )
    if not completa:
        print(
            f"Registrazione incompleta: --registra --lotto {lotto} --riprendi {cartella}"
        )
    print(f"Rapporto: {cartella / 'rapporto.md'}")
    return cartella


def riassunto_voce(voce: dict) -> str:
    """Una riga di avanzamento, senza il testo della domanda."""
    if voce.get("errore"):
        return f"errore {voce['errore'][:80]}"
    if voce.get("errore_verifica"):
        return (
            f"risposta salvata, errore del verificatore {voce['errore_verifica'][:80]}"
        )
    conti = conteggi_stati(voce)
    return (
        f"router {'ok' if voce['router']['riuscito'] else 'NO'} "
        f"({voce['router']['anomalie']} anomalie), "
        f"{conti['verificato']} verificati, {conti['non_trovato']} non trovati, "
        f"{conti['non_citato']} senza fonte, {voce['costo']['totale']['dollari']:.3f} $"
    )


def leggi_voci(cartella: Path) -> list[dict]:
    """Le voci delle domande di una registrazione, nell'ordine dei codici di meta."""
    meta = leggi_json(cartella / "meta.json")
    voci = []
    for codice in meta.get("codici", []):
        percorso = cartella / "domande" / nome_file(codice)
        if percorso.exists():
            voci.append(leggi_json(percorso))
    return voci


# --- Riverifica ---


def riverifica(cartella: Path) -> Path:
    """Rifà la verifica sulle risposte salvate e scrive esiti e rapporto."""
    if not (cartella / "meta.json").exists():
        raise ErroreProva(f"{cartella} non è una cartella di registrazione")
    meta = leggi_json(cartella / "meta.json")
    voci = leggi_voci(cartella)
    momento = adesso()

    nuove = []
    esiti = {}
    for voce in voci:
        rifatta = riverifica_voce(voce)
        esiti[voce["codice"]] = rifatta
        nuove.append({**voce, **rifatta})

    uscita = cartella / "riverifiche" / nome_cartella(momento)
    uscita.mkdir(parents=True)
    git = stato_git()
    scrivi_json(
        uscita / "esiti.json",
        {"momento": momento.isoformat(timespec="seconds"), **git, "esiti": esiti},
    )

    cartella_lotto = cartella.parent
    precompila_giudizi(cartella_lotto / "giudizi.csv", nuove, meta["seme_campione"])
    giudizi = leggi_giudizi(cartella_lotto / "giudizi.csv")
    meta_riverifica = {
        **meta,
        "riverifica": momento.isoformat(timespec="seconds"),
        "commit_riverifica": git["commit"],
    }
    (uscita / "rapporto.md").write_text(
        rapporto(
            nuove,
            meta_riverifica,
            giudizi,
            f"Lotto {meta['lotto']}, riverifica",
            solo_senza_giudizio=True,
        ),
        encoding="utf-8",
    )
    print(f"Rapporto: {uscita / 'rapporto.md'}")
    return uscita


# --- Giudizi a mano ---


def chiave(codice: str, valore: str, contesto: str) -> tuple[str, str, str]:
    return (codice, valore, contesto)


def righe_da_giudicare(voci: list[dict], seme: int) -> list[dict]:
    """Le righe da giudicare: problemi, campione dei verificati, attese a mano.

    Il campione: CAMPIONE_VERIFICATI dati verificati scelti con il seme,
    esclusi gli anni come nel pannello dell'app, una volta ogni coppia
    valore-contesto.
    """
    righe = []
    visti = set()
    candidati = []
    for voce in voci:
        codice = voce["codice"]
        for e in voce.get("esiti_verifica", []):
            k = chiave(codice, e["valore"], e["contesto"])
            if k in visti:
                continue
            visti.add(k)
            if e["stato"] == "verificato":
                if e["tipo"] != "anno":
                    candidati.append((codice, e))
            else:
                righe.append({"codice": codice, "esito": e, "motivo": e["stato"]})
    numero = min(CAMPIONE_VERIFICATI, len(candidati))
    for codice, e in random.Random(seme).sample(candidati, numero):
        righe.append({"codice": codice, "esito": e, "motivo": "campione"})
    for voce in voci:
        for testo in voce.get("a_mano", []):
            righe.append(
                {
                    "codice": voce["codice"],
                    "esito": {"valore": VALORE_A_MANO, "contesto": testo},
                    "motivo": "a_mano",
                }
            )
    return righe


def leggi_giudizi(percorso: Path) -> dict:
    """I giudizi scritti, per chiave (codice, valore, contesto)."""
    if not percorso.exists():
        return {}
    with percorso.open(encoding="utf-8-sig", newline="") as f:
        return {
            chiave(r["codice"], r["valore"], r["contesto"]): r
            for r in csv.DictReader(f)
        }


def precompila_giudizi(percorso: Path, voci: list[dict], seme: int) -> int:
    """Aggiunge al file dei giudizi le righe nuove da giudicare.

    Le righe già presenti, con o senza giudizio, restano come sono.
    Restituisce quante righe ha aggiunto.
    """
    esistenti = leggi_giudizi(percorso)
    nuove = []
    for riga in righe_da_giudicare(voci, seme):
        e = riga["esito"]
        k = chiave(riga["codice"], e["valore"], e["contesto"])
        if k in esistenti:
            continue
        esistenti[k] = {}
        nuove.append(
            {
                "codice": riga["codice"],
                "valore": e["valore"],
                "contesto": e["contesto"],
                "giudizio": "",
                "nota": "",
            }
        )
    if not nuove:
        return 0
    percorso.parent.mkdir(parents=True, exist_ok=True)
    nuovo_file = not percorso.exists()
    with percorso.open(
        "a", encoding="utf-8-sig" if nuovo_file else "utf-8", newline=""
    ) as f:
        scrittore = csv.DictWriter(f, fieldnames=COLONNE_GIUDIZI)
        if nuovo_file:
            scrittore.writeheader()
        scrittore.writerows(nuove)
    return len(nuove)


def giudizio_di(giudizi: dict, codice: str, e: dict) -> str:
    riga = giudizi.get(chiave(codice, e["valore"], e["contesto"]))
    return (riga or {}).get("giudizio", "").strip()


# --- Rapporto ---


def conteggi_stati(voce: dict) -> Counter:
    conti = Counter({s: 0 for s in STATI})
    conti.update(e["stato"] for e in voce.get("esiti_verifica", []))
    return conti


def celle(testo) -> str:
    """Un valore per una cella di tabella markdown."""
    return str(testo).replace("|", "\\|").replace("\n", " ")


def riga_esito(codice: str, e: dict, giudizi: dict) -> str:
    riga = f"- `{codice}` **{celle(e['valore'])}**"
    if e.get("tipo"):
        riga += f" ({e['tipo']}, {e['stato']})"
    if e.get("contesto"):
        riga += f" · _{celle(e['contesto'])}_"
    if e.get("frammenti"):
        riga += f" → fonti {', '.join(e['frammenti'])}"
    if e.get("dettaglio"):
        riga += f" · {celle(e['dettaglio'])}"
    giudicato = giudizio_di(giudizi, codice, e)
    if giudicato:
        riga += f" · **giudizio: {giudicato}**"
    return riga


def rapporto(
    voci: list[dict],
    meta: dict,
    giudizi: dict,
    titolo: str,
    solo_senza_giudizio: bool = False,
) -> str:
    """Il rapporto markdown di una registrazione o di una riverifica."""
    righe = [f"# {titolo}", ""]
    righe.append(f"- inizio: {meta.get('inizio')}; fine: {meta.get('fine')}")
    if meta.get("riverifica"):
        righe.append(
            f"- riverifica: {meta['riverifica']}, commit {meta.get('commit_riverifica')}"
        )
    righe.append(
        f"- stato: {meta.get('stato')}; a freddo: {'sì' if meta.get('a_freddo') else 'no'}"
    )
    righe.append(
        f"- commit {meta.get('commit')}"
        + (" (con modifiche non salvate)" if meta.get("modifiche_non_salvate") else "")
    )
    impronta_tot = (meta.get("impronta_csv") or {}).get("complessiva", "")
    righe.append(f"- CSV di data/processed: {impronta_tot[:16]}")
    righe.append(
        f"- data di oggi: {meta.get('data_di_oggi')}; modello {meta.get('modello')}; "
        f"recupero {meta.get('recupero')}; ente {meta.get('ente')}"
    )
    righe.append(f"- domande registrate: {len(voci)} su {len(meta.get('codici', []))}")
    righe.append("")

    righe += [
        (
            "| codice | gruppo | router | interrogazioni | bandi citati | attese "
            "| vietate | verificati | non trovati | senza fonte | col blocco | costo $ |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    totale = 0.0
    for voce in voci:
        r = voce.get("router", {})
        router = (
            f"{'sì' if r.get('riuscito') else 'no'}, "
            f"{r.get('anomalie', '?')}/{r.get('chiamate', CHIAMATE_ROUTER)}"
        )
        costo = voce.get("costo", {}).get("totale", {}).get("dollari", 0.0)
        totale += costo
        if voce.get("errore"):
            righe.append(
                f"| {voce['codice']} | {voce['gruppo']} | {router} "
                f"| errore: {celle(voce['errore'][:60])} | | | | | | | | {costo:.3f} |"
            )
            continue
        nomi = [
            i.get("nome", "?")
            for i in voce.get("decisione", {}).get("interrogazioni", [])
        ]
        if voce.get("errore_verifica"):
            righe.append(
                f"| {voce['codice']} | {voce['gruppo']} | {router} "
                f"| {celle(', '.join(nomi)) or '—'} "
                "| | | | errore del verificatore | | | "
                f"| {costo:.3f} |"
            )
            continue
        attese = voce.get("attese_esito") or {}
        conti = conteggi_stati(voce)
        righe.append(
            f"| {voce['codice']} | {voce['gruppo']} | {router} "
            f"| {celle(', '.join(nomi)) or '—'} | {len(voce.get('bandi_citati', []))} "
            f"| {len(attese.get('trovate', []))}/{len(voce.get('attese', []))} "
            f"| {len(attese.get('vietate_comparse', []))} "
            f"| {conti['verificato']} | {conti['non_trovato']} | {conti['non_citato']} "
            f"| {conti['citazione_generica']} | {costo:.3f} |"
        )
    righe += ["", f"Costo totale: {totale:.3f} $", ""]

    errori = [v for v in voci if v.get("errore") or v.get("errore_verifica")]
    if errori:
        righe += ["## Errori", ""]
        for v in errori:
            if v.get("errore"):
                righe.append(f"- `{v['codice']}` catena: {celle(v['errore'])}")
            else:
                righe.append(
                    f"- `{v['codice']}` verificatore (risposta salvata, da "
                    f"riverificare): {celle(v['errore_verifica'])}"
                )
        righe.append("")

    mancate = [
        v
        for v in voci
        if (v.get("attese_esito") or {}).get("mancanti")
        or (v.get("attese_esito") or {}).get("vietate_comparse")
    ]
    if mancate:
        righe += ["## Attese non soddisfatte", ""]
        for v in mancate:
            a = v["attese_esito"]
            if a["mancanti"]:
                righe.append(f"- `{v['codice']}` mancanti: {'; '.join(a['mancanti'])}")
            if a["vietate_comparse"]:
                righe.append(
                    f"- `{v['codice']}` vietate comparse: {'; '.join(a['vietate_comparse'])}"
                )
        righe.append("")

    def mostra(codice: str, e: dict) -> bool:
        return not (solo_senza_giudizio and giudizio_di(giudizi, codice, e))

    da_vedere = [
        (v["codice"], e)
        for v in voci
        for e in v.get("esiti_verifica", [])
        if e["stato"] != "verificato"
    ]
    righe += ["## Non trovati, senza fonte, citati con il blocco", ""]
    if solo_senza_giudizio:
        righe += ["Solo le righe senza giudizio.", ""]
    mostrate = [riga_esito(c, e, giudizi) for c, e in da_vedere if mostra(c, e)]
    righe += mostrate or ["Nessuna."]
    righe.append("")

    campione = [
        r
        for r in righe_da_giudicare(voci, meta.get("seme_campione", SEME_CAMPIONE))
        if r["motivo"] == "campione"
    ]
    righe += [
        f"## Campione di verificati da controllare a mano (seme {meta.get('seme_campione')})",
        "",
    ]
    mostrate = [
        riga_esito(r["codice"], r["esito"], giudizi)
        for r in campione
        if mostra(r["codice"], r["esito"])
    ]
    righe += mostrate or ["Nessuno."]
    righe.append("")

    a_mano = [(v, t) for v in voci for t in v.get("a_mano", [])]
    if a_mano:
        righe += ["## Attese da giudicare a mano", ""]
        for v, testo in a_mano:
            e = {"valore": VALORE_A_MANO, "contesto": testo}
            if not mostra(v["codice"], e):
                continue
            righe.append(riga_esito(v["codice"], e, giudizi))
            righe += [
                "",
                "<details><summary>risposta</summary>",
                "",
                v.get("risposta", v.get("errore", "")),
                "",
                "</details>",
                "",
            ]

    righe += ["## Giudizi", ""]
    righe += conta_giudizi(voci, giudizi, meta.get("seme_campione", SEME_CAMPIONE))
    return "\n".join(righe) + "\n"


def conta_giudizi(voci: list[dict], giudizi: dict, seme: int) -> list[str]:
    """I conteggi dei giudizi sulle righe di questa registrazione."""
    conti = Counter()
    sconosciuti = []
    for r in righe_da_giudicare(voci, seme):
        valore = giudizio_di(giudizi, r["codice"], r["esito"])
        if not valore:
            conti["senza giudizio"] += 1
        elif valore in GIUDIZI:
            conti[valore] += 1
        else:
            sconosciuti.append(f"`{r['codice']}` {r['esito']['valore']}: {valore}")
    righe = [f"- {nome}: {conti[nome]}" for nome in (*GIUDIZI, "senza giudizio")]
    if sconosciuti:
        righe.append(f"- giudizi non riconosciuti: {'; '.join(sconosciuti)}")
    return righe


# --- Riepilogo ---


def misure(voci: list[dict]) -> dict:
    """Le misure di un insieme di voci, escluse le domande viste."""
    voci = [v for v in voci if v["gruppo"] != GRUPPO_VISTE]
    conti = Counter()
    for v in voci:
        conti.update(conteggi_stati(v))
    return {
        "domande": len(voci),
        "errori": sum(bool(v.get("errore")) for v in voci),
        "errori_verifica": sum(bool(v.get("errore_verifica")) for v in voci),
        "router_riusciti": sum(
            v.get("router", {}).get("riuscito", False) for v in voci
        ),
        "anomalie": sum(v.get("router", {}).get("anomalie", 0) for v in voci),
        "chiamate_router": sum(v.get("router", {}).get("chiamate", 0) for v in voci),
        "attese_trovate": sum(
            len((v.get("attese_esito") or {}).get("trovate", [])) for v in voci
        ),
        "attese": sum(len(v.get("attese", [])) for v in voci),
        "vietate": sum(
            len((v.get("attese_esito") or {}).get("vietate_comparse", [])) for v in voci
        ),
        **{s: conti[s] for s in STATI},
        "costo": sum(
            v.get("costo", {}).get("totale", {}).get("dollari", 0.0) for v in voci
        ),
    }


def ultima_riverifica(cartella: Path) -> tuple[str, dict] | None:
    """La data e gli esiti della riverifica più recente di una registrazione."""
    cartelle = sorted((cartella / "riverifiche").glob("*/esiti.json"))
    if not cartelle:
        return None
    contenuto = leggi_json(cartelle[-1])
    return contenuto["momento"], contenuto["esiti"]


def riepilogo(cartella_prova: Path = CARTELLA_PROVA) -> str:
    """Le misure a freddo dei lotti registrati, e quelle dopo le correzioni.

    Le misure a freddo sono sempre quelle originali della registrazione;
    le riverifiche più recenti vanno nella seconda tabella, con la data.
    """
    prima = [
        "## Misure a freddo (escluse le domande viste)",
        "",
        (
            "| lotto | stato | domande | errori catena/verificatore | router riusciti "
            "| anomalie router "
            "| attese | vietate | verificati | non trovati | senza fonte | col blocco "
            "| costo medio $ |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    dopo = [
        "## Dopo le correzioni (riverifica più recente)",
        "",
        (
            "| lotto | data | attese | vietate | verificati | non trovati "
            "| senza fonte | col blocco | errori del verificatore |"
        ),
        "|---|---|---|---|---|---|---|---|---|",
    ]
    lotti = sorted(
        (p for p in cartella_prova.glob("lotto_*") if p.is_dir()),
        key=lambda p: int(p.name.split("_")[1]),
    )
    for cartella_lotto in lotti:
        freddo = registrazione_a_freddo(cartella_lotto)
        if freddo is None:
            continue
        lotto = cartella_lotto.name.split("_")[1]
        meta = leggi_json(freddo / "meta.json")
        voci = leggi_voci(freddo)
        m = misure(voci)
        medio = m["costo"] / m["domande"] if m["domande"] else 0.0
        prima.append(
            f"| {lotto} | {meta.get('stato')} | {m['domande']} "
            f"| {m['errori']}/{m['errori_verifica']} "
            f"| {m['router_riusciti']}/{m['domande']} "
            f"| {m['anomalie']}/{m['chiamate_router']} "
            f"| {m['attese_trovate']}/{m['attese']} | {m['vietate']} "
            f"| {m['verificato']} | {m['non_trovato']} | {m['non_citato']} "
            f"| {m['citazione_generica']} | {medio:.3f} |"
        )
        rifatta = ultima_riverifica(freddo)
        if rifatta is None:
            continue
        data, esiti = rifatta
        nuove = [{**v, **esiti.get(v["codice"], {})} for v in voci]
        d = misure(nuove)
        dopo.append(
            f"| {lotto} | {data} | {d['attese_trovate']}/{d['attese']} | {d['vietate']} "
            f"| {d['verificato']} | {d['non_trovato']} | {d['non_citato']} "
            f"| {d['citazione_generica']} | {d['errori_verifica']} |"
        )
    return "\n".join([*prima, "", *dopo]) + "\n"


# --- Stima ---


def misure_registrate(cartella_prova: Path = CARTELLA_PROVA) -> dict | None:
    """Le medie dei token misurati in tutte le registrazioni, se ce ne sono."""
    router, risposta = [], []
    for percorso in cartella_prova.glob("lotto_*/*/domande/*.json"):
        costo = leggi_json(percorso).get("costo", {})
        if costo.get("router", {}).get("ingresso"):
            router.append(costo["router"])
        if costo.get("risposta", {}).get("ingresso"):
            risposta.append(costo["risposta"])
    if not router or not risposta:
        return None

    def media(voci: list[dict], campo: str) -> float:
        return sum(v[campo] for v in voci) / len(voci)

    return {
        "domande": len(risposta),
        "router_ingresso": media(router, "ingresso"),
        "router_uscita": media(router, "uscita"),
        "risposta_ingresso": media(risposta, "ingresso"),
        "risposta_uscita": media(risposta, "uscita"),
    }


def dollari(ingresso: float, uscita: float) -> float:
    return (ingresso * PREZZO_INGRESSO + uscita * PREZZO_USCITA) / 1_000_000


def stima(lotto: int) -> None:
    """Domande del lotto (codice, gruppo, lunghezza) e costo stimato, senza modello."""
    from src.chains.rag import ISTRUZIONI, K_DEFAULT
    from src.chains.router import MODELLO_ROUTER, descrivi_profilo
    from src.database.enti import profilo_ente
    from src.database.repertorio import descrivi_repertorio, stato_archivio
    from src.database.schema import connetti

    domande = domande_del_lotto(lotto)
    conn = connetti()
    try:
        profilo = descrivi_profilo(profilo_ente(conn, ENTE_PREDEFINITO))
    finally:
        conn.close()
    repertorio, stato = descrivi_repertorio(), stato_archivio(ENTE_PREDEFINITO)

    print(f"Lotto {lotto}: {len(domande)} domande")
    print(f"{'codice':<12}{'gruppo':<10}caratteri")
    caratteri_router = 0
    caratteri_risposta = 0
    for d in domande:
        print(f"{d.codice:<12}{d.gruppo:<10}{len(d.testo)}")
        messaggi = MODELLO_ROUTER.format_messages(
            domanda=d.testo, repertorio=repertorio, stato=stato, profilo=profilo
        )
        caratteri_router += sum(len(m.content) for m in messaggi)
        caratteri_risposta += (
            len(ISTRUZIONI)
            + len(profilo)
            + len(d.testo)
            + K_DEFAULT * CHUNK_SIZE * MARGINE_INTESTAZIONE
            + MARGINE_DATI
        )
    n = len(domande)
    gruppi = Counter(d.gruppo for d in domande)
    print("per gruppo: " + ", ".join(f"{g} {gruppi[g]}" for g in GRUPPI if gruppi[g]))

    print(
        f"\nChiamate al modello: {n * (CHIAMATE_ROUTER + 1)} "
        f"({CHIAMATE_ROUTER} router + 1 risposta per domanda)"
    )
    router_in = caratteri_router / CARATTERI_PER_TOKEN * CHIAMATE_ROUTER
    router_out = n * CHIAMATE_ROUTER * USCITA_ROUTER
    risposta_in = caratteri_risposta / CARATTERI_PER_TOKEN
    basso = dollari(router_in + risposta_in, router_out + n * USCITA_RISPOSTA[0])
    alto = dollari(router_in + risposta_in, router_out + n * USCITA_RISPOSTA[1])
    print(
        f"Stima dai prompt ({CARATTERI_PER_TOKEN} caratteri per token): router "
        f"{router_in:,.0f} token in ingresso, risposte {risposta_in:,.0f}; "
        f"tra {basso:.2f} $ e {alto:.2f} $ ({basso / n:.3f}–{alto / n:.3f} $ a domanda)"
    )

    misurate = misure_registrate()
    if misurate is None:
        print("Nessuna misura registrata: la stima dai prompt è l'unica.")
        return
    a_domanda = dollari(
        misurate["router_ingresso"] + misurate["risposta_ingresso"],
        misurate["router_uscita"] + misurate["risposta_uscita"],
    )
    print(
        f"Stima dalle misure ({misurate['domande']} domande registrate): "
        f"{a_domanda:.3f} $ a domanda, {a_domanda * n:.2f} $ per il lotto"
    )


# --- Riga di comando ---


def dividi_e_mostra() -> None:
    domande = carica_domande()
    divisione = scrivi_lotti(domande, FILE_LOTTI, impronta(FILE_DOMANDE))
    print(f"Seme {SEME_DIVISIONE}; scritto {FILE_LOTTI}")
    print(conteggi_lotti(domande, divisione))


def main(argomenti: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Insieme di prova dell'app.")
    modo = parser.add_mutually_exclusive_group(required=True)
    modo.add_argument("--dividi", action="store_true")
    modo.add_argument("--stima", action="store_true")
    modo.add_argument("--registra", action="store_true")
    modo.add_argument("--riverifica", type=Path, metavar="CARTELLA")
    modo.add_argument("--riepilogo", action="store_true")
    parser.add_argument("--lotto", type=int)
    parser.add_argument("--riprendi", type=Path, metavar="CARTELLA")
    a = parser.parse_args(argomenti)

    if (a.stima or a.registra) and a.lotto is None:
        parser.error("--stima e --registra vogliono --lotto N")
    if a.riprendi is not None and not a.registra:
        parser.error("--riprendi si usa con --registra")

    try:
        if a.dividi:
            dividi_e_mostra()
        elif a.stima:
            stima(a.lotto)
        elif a.registra:
            registra(a.lotto, a.riprendi)
        elif a.riverifica is not None:
            riverifica(a.riverifica)
        else:
            print(riepilogo(), end="")
    except ErroreProva as errore:
        print(f"ERRORE: {errore}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
