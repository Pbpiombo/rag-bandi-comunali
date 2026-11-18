"""Schede di etichettatura per le domande dell'insieme di prova, senza modello.

Per ogni domanda il programma prepara i bandi candidati, con i campi già
estratti (titolo, ente, tipi di beneficiario, interventi, stato), e lascia
vuota la colonna del giudizio: pertinente, generico o no. Le etichette
servono a scrivere attese con polarità e a misurare il futuro passo di
classificazione (roadmap, "Indicazioni del revisore tecnico", punto 9).

Candidati per domanda, unione di tre vie, con l'origine di ciascuno:

- router: tutte le interrogazioni proposte nelle risposte grezze del router
  (grezzi_router) di tutte le registrazioni salvate in dati-grezzi/prova
  per quel codice, eseguite nel codice con esegui_su come le esegue la
  catena. Risposte non interpretabili e interrogazioni non valide si
  saltano e si contano;
- ente: bandi_aperti_per_ente, per le domande del gruppo comuni;
- parole: bandi non scaduti con almeno una parola significativa della
  domanda nel titolo, negli interventi o nei beneficiari.

Si tolgono i doppioni per id e le righe con natura non_bando; si ordina
per numero di vie, poi per chiamate del router che hanno portato il bando
(ogni risposta grezza di ogni registrazione, colonna chiamate_router), poi
per parole della domanda trovate nel bando, poi per titolo. Si scrivono
tutti i candidati; con --massimo N al più N per domanda, elencando i
tagliati nel riepilogo. I bandi "da
approfondire" dei risultati non sono candidati (il modello non li vede):
si elencano nel riepilogo.

Data di riferimento: le interrogazioni leggono la data da
interrogazioni_bandi.data_di_oggi. Il contesto alla_data la fissa per la
durata dell'esecuzione con interrogazioni_bandi.data_fissata, che vale per
tutti i moduli che la importano, e la ripristina all'uscita. Lo stato dei bandi si
calcola con le funzioni di diagnosi_attese (scaduto, stato_bando).

Legge solo il file delle domande, i JSON salvati e SQLite in sola lettura:
nessuna chiamata al modello, nessun accesso a Postgres.

Uso:

    python -m scripts.diagnostica.schede_etichette [--codici C02,C03]
        [--data 2026-11-16] [--massimo N]

Uscita in dati-grezzi/etichette/<AAAA-MM-GG_HHMMSS>/, sempre in una
cartella nuova: schede.xlsx (fogli "candidati" e "forme", con i menu a
tendina, prima riga bloccata e filtri sulle colonne) e riepilogo.md, con la
sezione dei bandi ricorrenti.
"""

import argparse
import json
import sqlite3
import sys
from collections import Counter
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.datavalidation import DataValidation

from scripts.diagnostica import prova_insieme
from scripts.diagnostica.diagnosi_attese import apri_in_lettura, stato_alla_data
from scripts.diagnostica.prova_insieme import (
    Domanda,
    adesso,
    carica_domande,
    celle,
    impronta_csv,
    leggi_json,
    nome_cartella,
    nome_file,
    registrazioni,
)
from src.chains.router import estrai_decisione
from src.config import DATI_GREZZI_DIR, ENTE_PREDEFINITO
from src.database.interrogazioni_bandi import NOMI_TIPI, _parole, _simili, data_fissata
from src.database.repertorio import PER_NOME, esegui_su
from src.estrazione.beneficiari import PER_REQUISITO

CARTELLA_ETICHETTE = DATI_GREZZI_DIR / "etichette"
# La baseline: la regressione finale del 16/11/2026 (commit 715b411)
DATA_BASELINE = "2026-11-16"
REGISTRAZIONE_BASELINE = Path("lotto_1") / "2026-11-16_111330"

MAX_INTERVENTI = 200
GRUPPO_COMUNI = "comuni"
# I gruppi delle domande di privati: P (privati) e L (viste)
GRUPPI_PRIVATI = ("privati", "viste")

ROUTER = "router"
ENTE = "ente"
PAROLE = "parole"
VIE = (ROUTER, ENTE, PAROLE)

GIUDIZI = ("pertinente", "generico", "no")
FORME = ("non_trovo", "solo_generici", "elenco")

COLONNE_CANDIDATI = (
    "codice",
    "gruppo",
    "domanda",
    "id_bando",
    "titolo",
    "ente",
    "tipi_beneficiario",
    "interventi",
    "stato",
    "origine",
    "chiamate_router",
    "giudizio",
    "nota",
)
COLONNE_FORME = ("codice", "domanda", "attese_attuali", "forma_attesa", "nota")

# Parole delle domande che non distinguono un bando da un altro, oltre a
# interrogazioni_bandi.PAROLE_VUOTE (che ha già bando, bandi, contributo,
# contributi). Senza accenti, come le confronta _parole.
PAROLE_DOMANDA = frozenset(
    """
    quali quale quanti come dove quando chi sono ci ho hai ha abbiamo hanno
    posso possiamo puo potrei vorrei vogliamo devo dobbiamo fare fa esiste
    esistono essere sia nostro nostra nostri nostre mio mia questo questa
    anche solo piu ogni tutti tutte altro altri qualche comune comuni ente
    unione abetone cutigliano finanziamento finanziamenti agevolazione
    agevolazioni aiuto aiuti opportunita incentivo incentivi aperto aperti
    aperta aperte partecipare richiedere chiedere ottenere attivita progetto
    progetti impresa imprese azienda aziende bando bandi contributo
    contributi san marcello piteglio sambuca pistoiese pistoia avere fondi
    fondo
    """.split()
) | frozenset(
    # Preposizioni articolate e semplici: quelle già in PAROLE_VUOTE (del,
    # della, dei, degli, delle, nel, nella, nei, per, con...) restano lì; le
    # parole di meno di 3 lettere (al, ai) _parole le toglie comunque
    """
    del dello della dei degli delle al allo alla ai agli alle dal dallo dalla
    dai dagli dalle nel nello nella nei negli nelle sul sullo sulla sui sugli
    sulle per con tra fra
    """.split()
)

# Il messaggio di esegui_su per un TypeError della funzione interrogata
PARAMETRI_NON_VALIDI = "Parametri non validi"


class ErroreSchede(Exception):
    """Un errore da mostrare senza traccia."""


# --- Data di riferimento ---


def alla_data(giorno: date) -> AbstractContextManager[None]:
    """Le interrogazioni vedono giorno come data di oggi, fino all'uscita.

    È interrogazioni_bandi.data_fissata: la data si fissa dentro
    data_di_oggi, e la vedono tutti i moduli che la importano per nome
    (repertorio, src.chains.rag).
    """
    return data_fissata(giorno)


# --- Parole ---


def parole_significative(testo: str) -> list[str]:
    """Le parole della domanda che distinguono un bando, senza ripetizioni."""
    viste: list[str] = []
    for p in _parole(testo):
        if p not in PAROLE_DOMANDA and p not in viste:
            viste.append(p)
    return viste


def parole_trovate(cercate: list[str], parole_bando: set[str]) -> int:
    """Quante parole cercate hanno una parola simile nel testo del bando."""
    return sum(any(_simili(p, t) for t in parole_bando) for p in cercate)


# --- Archivio ---


@dataclass
class Bando:
    """Una riga di bandi con i campi della scheda, alla data di riferimento."""

    id: str
    titolo: str
    ente: str
    url: str
    natura: str
    scaduto: bool
    stato: str
    tipi: str
    interventi: str
    parole: set[str]
    codici_tipi: set[str] = field(default_factory=set)


def tronca(testo: str, massimo: int) -> str:
    return testo if len(testo) <= massimo else testo[: massimo - 1] + "…"


def carica_archivio(conn: sqlite3.Connection, oggi: str) -> dict[str, Bando]:
    """Tutti i bandi, con stato, tipi leggibili, interventi e parole."""
    archivio = {}
    for riga in conn.execute("SELECT * FROM bandi ORDER BY id").fetchall():
        id_bando = riga["id"]
        interventi = [
            r["descrizione"]
            for r in conn.execute(
                "SELECT descrizione FROM interventi_bando WHERE id_bando = ? "
                "ORDER BY numero",
                (id_bando,),
            ).fetchall()
        ]
        beneficiari = conn.execute(
            "SELECT tipo, soggetto, condizioni, frase FROM beneficiari_bando "
            "WHERE id_bando = ? ORDER BY tipo",
            (id_bando,),
        ).fetchall()
        tipi = list(
            dict.fromkeys(NOMI_TIPI.get(b["tipo"], b["tipo"]) for b in beneficiari)
        )
        testi = [riga["titolo"], *interventi] + [
            b[campo] or ""
            for b in beneficiari
            for campo in ("soggetto", "condizioni", "frase")
        ]
        stato, frase = stato_alla_data(conn, riga, oggi)
        archivio[id_bando] = Bando(
            id=id_bando,
            titolo=riga["titolo"],
            ente=riga["ente"],
            url=riga["url"],
            natura=riga["natura"],
            scaduto=stato == "scaduto",
            stato=f"{stato}: {frase}",
            tipi=", ".join(tipi),
            interventi=tronca("; ".join(interventi), MAX_INTERVENTI),
            parole={p for t in testi for p in _parole(t)},
            codici_tipi={b["tipo"] for b in beneficiari},
        )
    return archivio


# --- Via del router ---


@dataclass
class Richieste:
    """Le interrogazioni proposte dal router per una domanda, senza doppioni."""

    richieste: dict[str, tuple[str, dict]] = field(default_factory=dict)
    volte: Counter = field(default_factory=Counter)
    # Le chiavi delle richieste di ogni risposta interpretabile, una per
    # risposta grezza di ogni registrazione
    per_risposta: list[set[str]] = field(default_factory=list)
    registrazioni: int = 0
    risposte: int = 0
    non_interpretabili: int = 0
    non_leggibili: int = 0


def chiave_richiesta(nome: str, parametri: dict) -> str:
    return json.dumps([nome, parametri], ensure_ascii=False, sort_keys=True)


def richieste_del_router(cartella_prova: Path, codice: str) -> Richieste:
    """Le interrogazioni nelle risposte grezze del router di ogni registrazione."""
    esito = Richieste()
    for cartella_lotto in sorted(cartella_prova.glob("lotto_*")):
        for cartella in registrazioni(cartella_lotto):
            percorso = cartella / "domande" / nome_file(codice)
            if not percorso.exists():
                continue
            esito.registrazioni += 1
            for grezzo in leggi_json(percorso).get("grezzi_router") or []:
                esito.risposte += 1
                decisione = estrai_decisione(grezzo or "")
                if decisione is None:
                    esito.non_interpretabili += 1
                    continue
                chiavi: set[str] = set()
                esito.per_risposta.append(chiavi)
                for richiesta in decisione.get("interrogazioni") or []:
                    # Come esegui_interrogazioni: nome e parametri della richiesta
                    if not isinstance(richiesta, dict):
                        esito.non_leggibili += 1
                        continue
                    nome = richiesta.get("nome", "")
                    parametri = richiesta.get("parametri") or {}
                    if not isinstance(parametri, dict):
                        esito.non_leggibili += 1
                        continue
                    chiave = chiave_richiesta(nome, parametri)
                    esito.richieste.setdefault(chiave, (nome, parametri))
                    esito.volte[chiave] += 1
                    chiavi.add(chiave)
    return esito


@dataclass
class Esecuzione:
    """L'esito di un'interrogazione eseguita o saltata."""

    chiave: str
    volte: int
    id_bandi: list[str] = field(default_factory=list)
    da_approfondire: list[str] = field(default_factory=list)
    saltata: str = ""


def esegui_richiesta(
    conn: sqlite3.Connection,
    nome: str,
    parametri: dict,
    codice_ente: str,
    per_url: dict[str, str],
) -> Esecuzione:
    """Un'interrogazione eseguita come la esegue la catena, con gli id dei bandi."""
    esecuzione = Esecuzione(chiave_richiesta(nome, parametri), 1)
    if nome not in PER_NOME:
        esecuzione.saltata = f"'{nome}' non è nel repertorio"
        return esecuzione
    try:
        risultato = esegui_su(conn, nome, parametri, codice_ente)
    except (ValueError, sqlite3.Error) as errore:
        esecuzione.saltata = f"{type(errore).__name__}: {errore}"
        return esecuzione
    if risultato.testo.startswith(PARAMETRI_NON_VALIDI):
        esecuzione.saltata = risultato.testo
        return esecuzione
    esecuzione.id_bandi = [per_url[v.url] for v in risultato.voci if v.url in per_url]
    esecuzione.da_approfondire = [a.titolo for a in risultato.da_approfondire]
    return esecuzione


# --- Candidati ---


@dataclass
class Candidato:
    bando: Bando
    vie: set[str]
    punteggio: int
    chiamate_router: int = 0

    @property
    def origine(self) -> str:
        return ", ".join(v for v in VIE if v in self.vie)


@dataclass
class Scheda:
    """I candidati di una domanda e i conteggi per il riepilogo."""

    domanda: Domanda
    parole: list[str]
    candidati: list[Candidato]
    per_via: dict[str, int]
    unione: int
    tagliati: list[Candidato]
    richieste: Richieste
    esecuzioni: list[Esecuzione]
    da_approfondire: list[str]


def scheda_domanda(
    conn: sqlite3.Connection,
    domanda: Domanda,
    archivio: dict[str, Bando],
    cartella_prova: Path,
    codice_ente: str,
    massimo: int | None = None,
) -> Scheda:
    """I candidati delle tre vie per una domanda, uniti, ordinati e tagliati."""
    per_url = {b.url: b.id for b in archivio.values()}
    parole = parole_significative(domanda.testo)
    vie: dict[str, set[str]] = {}

    def aggiungi(id_bandi, via: str) -> None:
        for id_bando in id_bandi:
            vie.setdefault(id_bando, set()).add(via)

    richieste = richieste_del_router(cartella_prova, domanda.codice)
    esecuzioni = []
    for chiave, (nome, parametri) in richieste.richieste.items():
        esecuzione = esegui_richiesta(conn, nome, parametri, codice_ente, per_url)
        esecuzione.volte = richieste.volte[chiave]
        esecuzioni.append(esecuzione)
        aggiungi(esecuzione.id_bandi, ROUTER)
    # Per ogni bando, le risposte del router con almeno una richiesta che
    # lo restituisce
    bandi_per_chiave = {e.chiave: set(e.id_bandi) for e in esecuzioni}
    chiamate = Counter(
        id_bando
        for chiavi in richieste.per_risposta
        for id_bando in set().union(*(bandi_per_chiave[k] for k in chiavi))
    )

    if domanda.gruppo == GRUPPO_COMUNI:
        esecuzione = esegui_richiesta(
            conn, "bandi_aperti_per_ente", {}, codice_ente, per_url
        )
        esecuzione.chiave = f"{ENTE}: {esecuzione.chiave}"
        esecuzioni.append(esecuzione)
        aggiungi(esecuzione.id_bandi, ENTE)

    if parole:
        aggiungi(
            [
                b.id
                for b in archivio.values()
                if not b.scaduto and parole_trovate(parole, b.parole)
            ],
            PAROLE,
        )

    candidati = [
        Candidato(archivio[i], v, parole_trovate(parole, archivio[i].parole))
        for i, v in vie.items()
        if archivio[i].natura != "non_bando"
    ]
    for c in candidati:
        c.chiamate_router = chiamate.get(c.bando.id, 0)
    candidati.sort(
        key=lambda c: (
            -len(c.vie),
            -c.chiamate_router,
            -c.punteggio,
            c.bando.titolo,
            c.bando.id,
        )
    )
    per_via = {via: sum(via in c.vie for c in candidati) for via in VIE}
    da_approfondire = list(
        dict.fromkeys(t for e in esecuzioni for t in e.da_approfondire)
    )
    return Scheda(
        domanda=domanda,
        parole=parole,
        candidati=candidati[:massimo] if massimo else candidati,
        per_via=per_via,
        unione=len(candidati),
        tagliati=candidati[massimo:] if massimo else [],
        richieste=richieste,
        esecuzioni=esecuzioni,
        da_approfondire=da_approfondire,
    )


def prepara_schede(
    conn: sqlite3.Connection,
    domande: list[Domanda],
    giorno: date,
    cartella_prova: Path,
    codice_ente: str = ENTE_PREDEFINITO,
    massimo: int | None = None,
) -> tuple[list[Scheda], dict[str, Bando]]:
    """Le schede di tutte le domande, con le interrogazioni alla data giorno.

    Restituisce anche l'archivio alla stessa data, per i conteggi del
    riepilogo.
    """
    with alla_data(giorno):
        archivio = carica_archivio(conn, giorno.isoformat())
        schede = [
            scheda_domanda(conn, d, archivio, cartella_prova, codice_ente, massimo)
            for d in domande
        ]
    return schede, archivio


# --- Uscita ---


def attese_attuali(domanda: Domanda) -> str:
    voci = (
        list(domanda.attese)
        + [f"non: {v}" for v in domanda.vietate]
        + [f"a mano: {a}" for a in domanda.a_mano]
    )
    return " ; ".join(voci)


def foglio(libro: Workbook, titolo: str, colonne: tuple, righe: list[list]):
    ws = libro.create_sheet(titolo)
    ws.append(list(colonne))
    for cella in ws[1]:
        cella.font = Font(bold=True)
    for riga in righe:
        ws.append(riga)
    ws.freeze_panes = "A2"
    for cella in ws[1]:
        ws.column_dimensions[cella.column_letter].width = 18
    for riga in ws.iter_rows(min_row=2):
        for cella in riga:
            cella.alignment = Alignment(wrap_text=True, vertical="top")
    return ws


def tendina(ws, colonna: str, valori: tuple) -> None:
    """Il menu a tendina sulla colonna, per tutte le righe dei dati."""
    indice = ws[1][0].column + [c.value for c in ws[1]].index(colonna)
    lettera = ws.cell(row=1, column=indice).column_letter
    convalida = DataValidation(
        type="list", formula1=f'"{",".join(valori)}"', allow_blank=True
    )
    ws.add_data_validation(convalida)
    convalida.add(f"{lettera}2:{lettera}{max(ws.max_row, 2)}")


def scrivi_xlsx(percorso: Path, schede: list[Scheda]) -> None:
    libro = Workbook()
    libro.remove(libro.active)
    righe_candidati = [
        [
            s.domanda.codice,
            s.domanda.gruppo,
            s.domanda.testo,
            c.bando.id,
            c.bando.titolo,
            c.bando.ente,
            c.bando.tipi,
            c.bando.interventi,
            c.bando.stato,
            c.origine,
            c.chiamate_router,
            None,
            None,
        ]
        for s in schede
        for c in s.candidati
    ]
    ws = foglio(libro, "candidati", COLONNE_CANDIDATI, righe_candidati)
    ws.auto_filter.ref = ws.dimensions
    tendina(ws, "giudizio", GIUDIZI)
    righe_forme = [
        [s.domanda.codice, s.domanda.testo, attese_attuali(s.domanda), None, None]
        for s in schede
    ]
    ws = foglio(libro, "forme", COLONNE_FORME, righe_forme)
    tendina(ws, "forma_attesa", FORME)
    libro.save(percorso)


def stato_impronta(cartella_prova: Path) -> str:
    """L'impronta attuale dei CSV confrontata con quella della baseline."""
    attuale = impronta_csv()["complessiva"]
    meta = cartella_prova / REGISTRAZIONE_BASELINE / "meta.json"
    if not meta.exists():
        return f"attuale {attuale[:12]}; baseline non trovata ({meta})"
    baseline = (leggi_json(meta).get("impronta_csv") or {}).get("complessiva", "")
    esito = (
        "uguale: l'archivio è quello della baseline"
        if attuale == baseline
        else "DIVERSA: l'archivio non è quello della baseline"
    )
    return (
        f"attuale {attuale[:12]}, baseline {baseline[:12]} "
        f"({REGISTRAZIONE_BASELINE.as_posix()}): {esito}"
    )


# I tipi di beneficiario privati per i conteggi dei bandi aperti: tutti
# quelli che non sono enti pubblici e non sono qualsiasi_soggetto
TIPI_ENTI_PUBBLICI = ("comune", "unione_comuni", "altro_ente_pubblico")
TIPI_PRIVATI_CONTATI = tuple(
    t for t in NOMI_TIPI if t not in TIPI_ENTI_PUBBLICI and t != PER_REQUISITO
)


def aperto(bando: Bando) -> bool:
    """Un bando, non una pagina informativa, non scaduto alla data."""
    return bando.natura != "non_bando" and not bando.scaduto


def ammette(bando: Bando, tipo: str) -> bool:
    """Il bando ha una riga del tipo o di qualsiasi_soggetto, come filtro_ente."""
    return bool(bando.codici_tipi & {tipo, PER_REQUISITO})


def bandi_ricorrenti(schede: list[Scheda]) -> list[tuple[Bando, int, int]]:
    """Per ogni bando candidato: domande del gruppo comuni e domande di privati.

    Si contano anche i candidati tagliati da --massimo. In ordine di domande
    di privati, poi di domande dei comuni, decrescenti, poi per titolo.
    """
    bandi: dict[str, Bando] = {}
    comuni: Counter = Counter()
    privati: Counter = Counter()
    for s in schede:
        for c in s.candidati + s.tagliati:
            bandi[c.bando.id] = c.bando
            if s.domanda.gruppo == GRUPPO_COMUNI:
                comuni[c.bando.id] += 1
            elif s.domanda.gruppo in GRUPPI_PRIVATI:
                privati[c.bando.id] += 1
    righe = [(b, comuni[i], privati[i]) for i, b in bandi.items()]
    righe.sort(key=lambda r: (-r[2], -r[1], r[0].titolo, r[0].id))
    return righe


def sezione_ricorrenti(schede: list[Scheda], archivio: dict[str, Bando]) -> list[str]:
    aperti = [b for b in archivio.values() if aperto(b)]
    domande_comuni = sum(s.domanda.gruppo == GRUPPO_COMUNI for s in schede)
    domande_privati = sum(s.domanda.gruppo in GRUPPI_PRIVATI for s in schede)
    righe = [
        "",
        "## Bandi ricorrenti",
        "",
        (
            f"Bandi aperti alla data di riferimento: {len(aperti)} (natura bando, "
            "non scaduti: comprende gli sportelli e i bandi senza scadenza)."
        ),
        "",
        (
            "Bandi aperti per tipo di beneficiario privato. Un bando ammette un "
            "tipo se ha una riga di quel tipo o di qualsiasi_soggetto in "
            "beneficiari_bando, come le interrogazioni per ente:"
        ),
        "",
        "| tipo | bandi aperti che lo ammettono | di cui con una riga del tipo |",
        "|---|---|---|",
    ]
    for tipo in TIPI_PRIVATI_CONTATI:
        con_riga = sum(tipo in b.codici_tipi for b in aperti)
        righe.append(
            f"| {tipo} | {sum(ammette(b, tipo) for b in aperti)} | {con_riga} |"
        )
    righe += [
        "",
        (
            f"Domande in cui ogni bando compare come candidato: {domande_comuni} "
            f"del gruppo comuni, {domande_privati} di privati (P e L). Tipi: "
            "i tipi distinti del bando in beneficiari_bando."
        ),
        "",
        "| bando | domande comuni | domande privati | tipi |",
        "|---|---|---|---|",
    ]
    righe += [
        f"| {celle(b.titolo)} [{b.id}] | {comuni} | {privati} | {len(b.codici_tipi)} |"
        for b, comuni, privati in bandi_ricorrenti(schede)
    ]
    return righe


def riepilogo(
    schede: list[Scheda],
    archivio: dict[str, Bando],
    giorno: date,
    codice_ente: str,
    impronta: str,
    momento: str,
    massimo: int | None = None,
) -> str:
    righe = [
        "# Schede di etichettatura",
        "",
        f"- generato: {momento}",
        f"- data di riferimento: {giorno.isoformat()}",
        f"- ente: {codice_ente}",
        f"- impronta dei CSV di data/processed: {impronta}",
        f"- giudizio (foglio candidati): {', '.join(GIUDIZI)}",
        f"- forma_attesa (foglio forme): {', '.join(FORME)}",
        (
            f"- al più {massimo} candidati per domanda"
            if massimo
            else "- tutti i candidati di ogni domanda"
        ),
        "",
        "## Domande",
        "",
        (
            "| codice | router | ente | parole | unione | scritti | tagliati "
            "| interrogazioni eseguite | saltate | risposte non interpretabili |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for s in schede:
        eseguite = sum(1 for e in s.esecuzioni if not e.saltata)
        saltate = sum(1 for e in s.esecuzioni if e.saltata) + s.richieste.non_leggibili
        righe.append(
            f"| {s.domanda.codice} | {s.per_via[ROUTER]} | {s.per_via[ENTE]} "
            f"| {s.per_via[PAROLE]} | {s.unione} | {len(s.candidati)} "
            f"| {len(s.tagliati)} | {eseguite} | {saltate} "
            f"| {s.richieste.non_interpretabili} su {s.richieste.risposte} |"
        )

    for s in schede:
        r = s.richieste
        righe += [
            "",
            f"## {s.domanda.codice} ({s.domanda.gruppo})",
            "",
            f"- domanda: {s.domanda.testo}",
            f"- parole significative: {', '.join(s.parole) or 'nessuna'}",
            (
                f"- registrazioni lette: {r.registrazioni}; risposte del router: "
                f"{r.risposte}, non interpretabili {r.non_interpretabili}, "
                f"richieste non leggibili {r.non_leggibili}"
            ),
            (
                f"- candidati per via: router {s.per_via[ROUTER]}, ente "
                f"{s.per_via[ENTE]}, parole {s.per_via[PAROLE]}; unione {s.unione}, "
                f"scritti {len(s.candidati)}, tagliati {len(s.tagliati)}"
            ),
            "- interrogazioni:",
        ]
        if not s.esecuzioni:
            righe.append("  - nessuna")
        for e in s.esecuzioni:
            esito = f"saltata: {e.saltata}" if e.saltata else f"{len(e.id_bandi)} bandi"
            righe.append(f"  - `{e.chiave}` ×{e.volte}: {celle(esito)}")
        if s.da_approfondire:
            righe.append(f"- da approfondire: {'; '.join(s.da_approfondire)}")
        if s.tagliati:
            righe.append(f"- tagliati ({len(s.tagliati)}):")
            righe += [
                f"  - {c.bando.titolo} [{c.bando.id}]: {c.origine}" for c in s.tagliati
            ]
    righe += sezione_ricorrenti(schede, archivio)
    return "\n".join(righe) + "\n"


def scrivi_uscita(
    cartella: Path,
    schede: list[Scheda],
    archivio: dict[str, Bando],
    giorno: date,
    codice_ente: str,
    impronta: str,
    massimo: int | None = None,
) -> Path:
    """Crea la cartella, che non deve esistere, e ci scrive xlsx e riepilogo."""
    cartella.parent.mkdir(parents=True, exist_ok=True)
    try:
        cartella.mkdir()
    except FileExistsError as errore:
        raise ErroreSchede(f"la cartella esiste già: {cartella}") from errore
    scrivi_xlsx(cartella / "schede.xlsx", schede)
    (cartella / "riepilogo.md").write_text(
        riepilogo(
            schede,
            archivio,
            giorno,
            codice_ente,
            impronta,
            adesso().isoformat(timespec="seconds"),
            massimo,
        ),
        encoding="utf-8",
    )
    return cartella


# --- Programma ---


def scegli(domande: list[Domanda], codici: str | None) -> list[Domanda]:
    if not codici:
        return domande
    voluti = [c.strip() for c in codici.split(",") if c.strip()]
    per_codice = {d.codice: d for d in domande}
    mancanti = [c for c in voluti if c not in per_codice]
    if mancanti:
        raise ErroreSchede(f"codici non nel file delle domande: {', '.join(mancanti)}")
    return [per_codice[c] for c in voluti]


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--codici", help="solo questi codici, separati da virgole")
    parser.add_argument(
        "--data",
        default=DATA_BASELINE,
        type=date.fromisoformat,
        help=f"data di riferimento AAAA-MM-GG (predefinita {DATA_BASELINE})",
    )
    parser.add_argument(
        "--massimo",
        type=int,
        help="al più N candidati per domanda (senza: tutti)",
    )
    argomenti = parser.parse_args(argv)
    if argomenti.massimo is not None and argomenti.massimo < 1:
        parser.error("--massimo deve essere almeno 1")
    return argomenti


def main(argv: list[str] | None = None) -> Path:
    argomenti = leggi_argomenti(argv)
    cartella_prova = prova_insieme.CARTELLA_PROVA
    domande = scegli(carica_domande(prova_insieme.FILE_DOMANDE), argomenti.codici)
    impronta = stato_impronta(cartella_prova)
    conn = apri_in_lettura()
    try:
        schede, archivio = prepara_schede(
            conn,
            domande,
            argomenti.data,
            cartella_prova,
            massimo=argomenti.massimo,
        )
    finally:
        conn.close()
    cartella = scrivi_uscita(
        CARTELLA_ETICHETTE / nome_cartella(adesso()),
        schede,
        archivio,
        argomenti.data,
        ENTE_PREDEFINITO,
        impronta,
        argomenti.massimo,
    )
    print(f"Schede: {cartella / 'schede.xlsx'}")
    print(f"Riepilogo: {cartella / 'riepilogo.md'}")
    return cartella


if __name__ == "__main__":
    try:
        main()
    except ErroreSchede as errore:
        print(f"Errore: {errore}")
        sys.exit(1)
