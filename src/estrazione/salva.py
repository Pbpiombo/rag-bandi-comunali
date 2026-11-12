"""Scrittura di un bando estratto nel database."""

import sqlite3
from datetime import date, datetime
from zoneinfo import ZoneInfo

from src.database.schema import connetti
from src.estrazione.indirizzi import url_canonico

COLONNE = [
    "id",
    "titolo",
    "ente",
    "tema",
    "programma",
    "apertura",
    "scadenza",
    "scadenza_nota",
    "a_sportello",
    "beneficiari",
    "territorio",
    "premialita",
    "costo_min",
    "costo_max",
    "contributo_perc",
    "contributo_min",
    "contributo_max",
    "dotazione",
    "url",
    "riferimento_atto",
    "fonte",
    "codice_fonte",
    "verificato_il",
    "cumulabilita",
    "cumulabilita_frase",
    "pubblicato_il",
    "pubblicato_origine",
    "natura",
    "natura_motivo",
]

COLONNE_BENEFICIARI = [
    "tipo",
    "soggetto",
    "condizioni",
    "frase",
    "confidenza",
    "origine",
]
COLONNE_INTERVENTI = ["numero", "genere", "descrizione", "frase"]
COLONNE_SCADENZE = ["numero", "genere", "descrizione", "apertura", "scadenza", "frase"]


class ConflittoBando(Exception):
    """L'id o l'URL del bando appartengono gia' a un altro bando."""


def esiste(id_bando: str) -> dict | None:
    """Restituisce la riga esistente per quell'identificativo, se c'e'."""
    conn = connetti()
    try:
        riga = conn.execute("SELECT * FROM bandi WHERE id = ?", (id_bando,)).fetchone()
        return dict(riga) if riga else None
    finally:
        conn.close()


def _conflitto(conn: sqlite3.Connection, id_bando: str, url: str) -> str | None:
    """Descrive il conflitto con un bando gia' salvato, se c'e'.

    Lo stesso id con lo stesso URL e' un aggiornamento, non un conflitto.
    """
    righe = conn.execute(
        "SELECT id, url FROM bandi WHERE id = ? OR url = ?", (id_bando, url)
    ).fetchall()

    for r in righe:
        if r["id"] == id_bando and r["url"] != url:
            return (
                f"l'id '{id_bando}' appartiene gia' al bando con URL {r['url']}, "
                f"non a {url}"
            )
        if r["url"] == url and r["id"] != id_bando:
            return f"l'URL {url} e' gia' salvato con id '{r['id']}', non '{id_bando}'"

    return None


def conflitto(id_bando: str, url: str) -> str | None:
    """Come _conflitto, per chi vuole saperlo prima di chiedere conferma."""
    conn = connetti()
    try:
        return _conflitto(conn, id_bando, url_canonico(url))
    finally:
        conn.close()


def _sostituisci(
    conn: sqlite3.Connection,
    tabella: str,
    colonne: list[str],
    id_bando: str,
    righe: list[dict],
) -> None:
    """Sostituisce le righe di una tabella collegata a un bando."""
    conn.execute(f"DELETE FROM {tabella} WHERE id_bando = ?", (id_bando,))
    elenco = ", ".join(["id_bando", *colonne])
    segnaposto = ", ".join("?" for _ in range(len(colonne) + 1))
    conn.executemany(
        f"INSERT INTO {tabella} ({elenco}) VALUES ({segnaposto})",
        [[id_bando, *(r.get(c) for c in colonne)] for r in righe],
    )


def segna_non_bando(id_bando: str, motivo: str) -> bool:
    """Segna un bando in archivio come pagina che non e' un bando.

    La riga resta, con i suoi dati, ma le interrogazioni non la mostrano
    tra le opportunita'. classificato_il diventa oggi: la riga e' stata
    esaminata con l'estrattore nuovo e non va riesaminata. Restituisce
    False se l'id non e' in archivio.
    """
    conn = connetti()
    try:
        cursore = conn.execute(
            "UPDATE bandi SET natura = 'non_bando', natura_motivo = ?, "
            "classificato_il = ? WHERE id = ?",
            (
                motivo,
                datetime.now(ZoneInfo("Europe/Rome")).date().isoformat(),
                id_bando,
            ),
        )
        conn.commit()
        return cursore.rowcount == 1
    finally:
        conn.close()


def _date_manuali(conn: sqlite3.Connection, id_bando: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM scadenze_bando WHERE id_bando = ? AND origine = 'manuale' "
        "ORDER BY numero",
        (id_bando,),
    ).fetchall()
    return [dict(r) for r in rows]


def date_manuali(id_bando: str) -> list[dict]:
    """Le righe di scadenze_bando inserite a mano per un bando."""
    conn = connetti()
    try:
        return _date_manuali(conn, id_bando)
    finally:
        conn.close()


def _data(s: dict) -> str:
    periodo = (
        f"dal {s['apertura']} al {s['scadenza']}"
        if s.get("apertura")
        else f"entro il {s['scadenza']}"
    )
    return f"{s['genere']} «{s['descrizione']}» {periodo}"


def applica_date_manuali(riga: dict, manuali: list[dict]) -> list[str]:
    """Le date inserite a mano prevalgono su quelle della nuova estrazione.

    Se il bando ha righe 'manuale' in scadenze_bando, la riga perde la
    chiave scadenze (cosi' salva non tocca la tabella) e la scadenza del
    bando torna l'ultima scadenza 'domanda' delle righe manuali. Modifica
    riga e restituisce le differenze da rivedere: le date proposte dal
    modello e non in archivio, quelle in archivio e non proposte, e una
    scadenza del bando diversa. Senza righe manuali non fa nulla.
    """
    if not manuali:
        return []

    da_rivedere = []
    proposte = riga.pop("scadenze", None)
    if proposte is not None:
        chiave = lambda s: (s["genere"], s.get("apertura"), s["scadenza"])  # noqa: E731
        tenute = {chiave(s) for s in manuali}
        if not proposte:
            da_rivedere.append(
                f"il modello non propone date multiple: restano le {len(manuali)} "
                "righe inserite a mano"
            )
        else:
            nuove = {chiave(s) for s in proposte}
            da_rivedere += [
                f"proposta dal modello, non in archivio: {_data(s)}"
                for s in proposte
                if chiave(s) not in tenute
            ]
            da_rivedere += [
                f"inserita a mano, non proposta dal modello: {_data(s)}"
                for s in manuali
                if chiave(s) not in nuove
            ]

    domande = [s["scadenza"] for s in manuali if s["genere"] == "domanda"]
    if domande:
        ultima = max(domande)
        if riga.get("scadenza") != ultima:
            da_rivedere.append(
                f"scadenza del bando: il modello indica {riga.get('scadenza')}, "
                f"le date inserite a mano danno {ultima}: resta {ultima}"
            )
            riga["scadenza"] = ultima
    return da_rivedere


def salva(riga: dict, url: str, fonte: str, codice_fonte: str) -> list[str]:
    """Scrive o aggiorna la riga del bando nel database.

    Un bando si aggiorna solo con lo stesso id e lo stesso URL. Se l'id
    appartiene a un altro URL, o l'URL a un altro id, solleva
    ConflittoBando e non scrive nulla.

    L'aggiornamento usa ON CONFLICT DO UPDATE, non INSERT OR REPLACE:
    REPLACE cancellerebbe la riga, in silenzio, insieme ai riferimenti
    delle tabelle beneficiari_bando, interventi_bando e scadenze_bando.

    Se la riga contiene beneficiari_ammessi (prodotti e verificati da
    valida), sostituiscono tutti i beneficiari del bando, comprese le
    righe migrate da ammette_comuni, e classificato_il diventa oggi.
    Lo stesso per interventi e scadenze. Senza quelle chiavi, le tabelle
    collegate restano come sono.

    Fanno eccezione le date inserite a mano (scadenze_bando con origine
    'manuale'): non si sostituiscono mai, e la scadenza del bando resta
    quella che danno (applica_date_manuali). Restituisce le differenze da
    rivedere tra le date proposte e quelle tenute; vuota se non ce ne sono.
    """
    oggi = date.today().isoformat()
    riga = dict(riga)
    riga["url"] = url_canonico(url)
    riga["fonte"] = fonte
    riga["codice_fonte"] = codice_fonte
    riga["verificato_il"] = oggi
    # Si salva solo cio' che e' un bando: una riga segnata prima come non
    # bando e poi estratta come bando torna tra le opportunita'
    riga["natura"] = "bando"
    riga["natura_motivo"] = None

    segnaposto = ", ".join("?" for _ in COLONNE)
    elenco = ", ".join(COLONNE)
    aggiorna = ", ".join(f"{c} = excluded.{c}" for c in COLONNE if c != "id")

    conn = connetti()
    try:
        problema = _conflitto(conn, riga["id"], riga["url"])
        if problema:
            raise ConflittoBando(f"Non salvo: {problema}")

        da_rivedere = applica_date_manuali(riga, _date_manuali(conn, riga["id"]))
        valori = [riga.get(c) for c in COLONNE]

        conn.execute(
            f"INSERT INTO bandi ({elenco}) VALUES ({segnaposto}) "
            f"ON CONFLICT(id) DO UPDATE SET {aggiorna}",
            valori,
        )
        if "beneficiari_ammessi" in riga:
            _sostituisci(
                conn,
                "beneficiari_bando",
                COLONNE_BENEFICIARI,
                riga["id"],
                riga["beneficiari_ammessi"],
            )
            conn.execute(
                "UPDATE bandi SET classificato_il = ? WHERE id = ?", (oggi, riga["id"])
            )

        if "interventi" in riga:
            _sostituisci(
                conn,
                "interventi_bando",
                COLONNE_INTERVENTI,
                riga["id"],
                riga["interventi"],
            )

        if "scadenze" in riga:
            _sostituisci(
                conn,
                "scadenze_bando",
                COLONNE_SCADENZE,
                riga["id"],
                riga["scadenze"],
            )

        conn.commit()
    finally:
        conn.close()
    return da_rivedere
