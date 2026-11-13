"""I doppioni tra le fonti dei bandi: elenco, confronto e rimozione.

Lo stesso bando puo' arrivare da due fonti: dalla pagina dell'ente e dal
catalogo di Incentivi Italia, che rimanda a un altro indirizzo (il BURT,
Arti, Sviluppo Toscana). Si tiene la versione letta dalla pagina; l'altra
si elenca in data/processed/doppioni.csv, un file per tutte le fonti, che
le importazioni leggono per non salvarla di nuovo. E' il primo pezzo
della regola dei due domini (roadmap).

Colonne del file:
- url: l'indirizzo, in forma canonica, della versione tolta;
- codice_fonte: la fonte della versione tolta;
- id_tenuto: il bando che resta;
- motivo: perche' e' lo stesso bando, e perche' le differenze accettate
  non si riportano;
- verificato_il: la data del controllo;
- differenze_accettate: i campi della versione tolta che la tenuta non
  ha e che si e' deciso di non riportare, separati da virgole (per un
  tipo di beneficiario: tipo:<nome>). Vuoto se non ce ne sono.

Una rimozione si annulla togliendo la riga dal file (e rilanciando
l'importazione della fonte), oppure dalla copia del database.
"""

import csv
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.config import DATI_GREZZI_DIR, PROCESSED_DIR
from src.database import interrogazioni_bandi as ib
from src.estrazione.indirizzi import url_canonico

PERCORSO = PROCESSED_DIR / "doppioni.csv"
COLONNE = [
    "url",
    "codice_fonte",
    "id_tenuto",
    "motivo",
    "verificato_il",
    "differenze_accettate",
]

# Il motivo in scansioni della pagina tolta, seguito dall'id del tenuto
PREFISSO = "doppione di "

# Le tabelle con le righe di un bando, da togliere insieme a lui
COLLEGATE = ("beneficiari_bando", "interventi_bando", "scadenze_bando")

# I campi confrontati: un valore nella tolta e nessuno nella tenuta e' una
# lacuna, che ferma la rimozione se non e' tra le differenze accettate
CAMPI_CONFRONTO = (
    "apertura",
    "scadenza",
    "scadenza_nota",
    "costo_min",
    "costo_max",
    "contributo_perc",
    "contributo_min",
    "contributo_max",
    "dotazione",
    "territorio",
    "premialita",
    "riferimento_atto",
    "cumulabilita",
    "pubblicato_il",
)


class FileNonValido(ValueError):
    """Il file dei doppioni non ha la forma attesa."""


@dataclass(frozen=True)
class Doppione:
    """Una riga del file: la versione tolta e il bando che resta."""

    url: str
    codice_fonte: str
    id_tenuto: str
    motivo: str
    verificato_il: str
    differenze_accettate: frozenset[str]


def motivo_scansione(id_tenuto: str) -> str:
    """Il motivo con cui la pagina tolta resta in scansioni."""
    return f"{PREFISSO}{id_tenuto}"


def leggi_doppioni(percorso: Path = PERCORSO) -> dict[str, Doppione]:
    """I doppioni del file, per indirizzo canonico. Nessun file: nessuno."""
    if not percorso.exists():
        return {}
    with percorso.open(encoding="utf-8-sig", newline="") as f:
        lettore = csv.DictReader(f)
        if lettore.fieldnames != COLONNE:
            raise FileNonValido(
                f"colonne attese {COLONNE}, trovate {lettore.fieldnames}"
            )
        doppioni: dict[str, Doppione] = {}
        for numero, riga in enumerate(lettore, start=2):
            vuoti = [c for c in COLONNE[:-1] if not (riga[c] or "").strip()]
            if vuoti:
                raise FileNonValido(f"riga {numero}: campi vuoti {vuoti}")
            try:
                date.fromisoformat(riga["verificato_il"])
            except ValueError as errore:
                raise FileNonValido(f"riga {numero}: data non valida") from errore
            url = url_canonico(riga["url"].strip())
            if url in doppioni:
                raise FileNonValido(f"riga {numero}: indirizzo ripetuto {url}")
            accettate = frozenset(
                d.strip()
                for d in (riga["differenze_accettate"] or "").split(",")
                if d.strip()
            )
            doppioni[url] = Doppione(
                url,
                riga["codice_fonte"].strip(),
                riga["id_tenuto"].strip(),
                riga["motivo"].strip(),
                riga["verificato_il"],
                accettate,
            )
    return doppioni


def copia_di_sicurezza(
    conn: sqlite3.Connection, motivo: str, cartella: Path | None = None
) -> Path:
    """Copia il database in dati-grezzi/backup, fuori dal repository.

    Usa la copia di SQLite, che vale anche con la connessione aperta. Il
    nome dice la data, l'ora e il motivo: comune-AAAA-MM-GG-HHMM-prima-di-...
    """
    cartella = cartella or DATI_GREZZI_DIR / "backup"
    cartella.mkdir(parents=True, exist_ok=True)
    ora = datetime.now(ZoneInfo("Europe/Rome")).strftime("%Y-%m-%d-%H%M")
    destinazione = cartella / f"comune-{ora}-prima-di-{motivo}.sqlite"
    copia = sqlite3.connect(destinazione)
    try:
        conn.backup(copia)
    finally:
        copia.close()
    return destinazione


def _vuoto(valore) -> bool:
    return valore is None or (isinstance(valore, str) and not valore.strip())


def _tipi(conn: sqlite3.Connection, id_bando: str) -> set[str]:
    return {
        r[0]
        for r in conn.execute(
            "SELECT tipo FROM beneficiari_bando WHERE id_bando = ?", (id_bando,)
        )
    }


def confronta(conn: sqlite3.Connection, tolta, tenuta) -> tuple[list[str], list[str]]:
    """Le lacune della tenuta e le differenze, campo per campo.

    Lacuna: la tolta ha un valore e la tenuta no (per i tipi di
    beneficiario: un tipo della tolta che la tenuta non ha; per lo
    sportello: la tolta e' a sportello e la tenuta no). Differenza: due
    valori diversi, entrambi presenti; si mostra, non ferma.
    """
    lacune, diversi = [], []
    for campo in CAMPI_CONFRONTO:
        a, b = tolta[campo], tenuta[campo]
        if _vuoto(a) or a == b:
            continue
        if _vuoto(b):
            lacune.append(campo)
        else:
            diversi.append(f"{campo}: {a!r} / {b!r}")
    if tolta["a_sportello"] and not tenuta["a_sportello"]:
        lacune.append("a_sportello")
    for tipo in sorted(_tipi(conn, tolta["id"]) - _tipi(conn, tenuta["id"])):
        lacune.append(f"tipo:{tipo}")
    return lacune, diversi


def interrogazioni(conn: sqlite3.Connection, *ids: str) -> dict[str, object]:
    """Le interrogazioni in cui i bandi possono comparire, per nome.

    Aperti per ciascun ente, per ciascun tipo di beneficiario dei bandi,
    per ciascun loro tema.
    """
    enti = [r[0] for r in conn.execute("SELECT codice_fiscale FROM enti ORDER BY 1")]
    segnaposti = ", ".join("?" for _ in ids)
    tipi = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT tipo FROM beneficiari_bando "
            f"WHERE id_bando IN ({segnaposti}) ORDER BY 1",
            ids,
        )
    ]
    temi = [
        r[0]
        for r in conn.execute(
            f"SELECT DISTINCT tema FROM bandi WHERE id IN ({segnaposti}) "
            "AND tema IS NOT NULL ORDER BY 1",
            ids,
        )
    ]
    domande: dict[str, object] = {}
    for ente in enti:
        domande[f"aperti per {ente}"] = lambda e=ente: ib.bandi_aperti_per_ente(conn, e)
    for tipo in tipi:
        domande[f"per beneficiario {tipo}"] = lambda t=tipo: ib.bandi_per_beneficiario(
            conn, t
        )
    for tema in temi:
        domande[f"per tema {tema}"] = lambda t=tema: ib.bandi_per_tema(conn, t)
    return domande


def dove_compare(domande: dict[str, object], url: str) -> dict[str, str]:
    """In quali interrogazioni compare il bando, e dove: elenco o da approfondire."""
    trovato = {}
    for nome, domanda in domande.items():
        risultato = domanda()
        if any(v.url == url for v in risultato.voci):
            trovato[nome] = "elenco"
        elif any(a.url == url for a in risultato.da_approfondire):
            trovato[nome] = "da approfondire"
    return trovato


@dataclass
class Esito:
    """Cosa e' successo a un doppione."""

    url: str
    id_tolto: str | None
    id_tenuto: str
    stato: str  # gia' tolto, tenuto assente, fermato, tolto, annullato
    lacune: list[str]
    diversi: list[str]
    prima: dict[str, str]
    dopo: dict[str, str]


def togli(conn: sqlite3.Connection, doppione: Doppione, scrivi: bool) -> Esito:
    """Confronta, toglie e controlla un doppione; annulla se serve.

    Con scrivi=False si ferma dopo il confronto e le interrogazioni di
    prima: nulla cambia. Con scrivi=True toglie la riga e le sue righe
    collegate, annota la pagina in scansioni, rilancia le interrogazioni e
    conferma solo se il bando tenuto compare in ognuna in cui compariva
    il tolto; altrimenti annulla (rollback).
    """
    tolta = conn.execute(
        "SELECT * FROM bandi WHERE url = ?", (doppione.url,)
    ).fetchone()
    tenuta = conn.execute(
        "SELECT * FROM bandi WHERE id = ?", (doppione.id_tenuto,)
    ).fetchone()
    esito = Esito(doppione.url, None, doppione.id_tenuto, "", [], [], {}, {})
    if tolta is None:
        esito.stato = "gia' tolto"
        return esito
    esito.id_tolto = tolta["id"]
    if tenuta is None:
        esito.stato = "tenuto assente"
        return esito

    lacune, esito.diversi = confronta(conn, tolta, tenuta)
    esito.lacune = [c for c in lacune if c not in doppione.differenze_accettate]
    if esito.lacune:
        esito.stato = "fermato"
        return esito

    domande = interrogazioni(conn, tolta["id"], tenuta["id"])
    esito.prima = dove_compare(domande, tolta["url"])
    if not scrivi:
        esito.stato = "da togliere"
        return esito

    conn.commit()
    for tabella in COLLEGATE:
        conn.execute(f"DELETE FROM {tabella} WHERE id_bando = ?", (tolta["id"],))
    conn.execute("DELETE FROM bandi WHERE id = ?", (tolta["id"],))
    conn.execute(
        "INSERT OR REPLACE INTO scansioni (url, codice_fonte, slug, esito, motivo, "
        "esaminato_il) VALUES (?, ?, ?, 'scartato', ?, ?)",
        (
            url_canonico(tolta["url"]),
            tolta["codice_fonte"],
            tolta["id"],
            motivo_scansione(tenuta["id"]),
            datetime.now(ZoneInfo("Europe/Rome")).date().isoformat(),
        ),
    )
    esito.dopo = dove_compare(domande, tenuta["url"])
    if set(esito.prima) - set(esito.dopo):
        conn.rollback()
        esito.stato = "annullato"
    else:
        conn.commit()
        esito.stato = "tolto"
    return esito
