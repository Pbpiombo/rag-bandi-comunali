"""Scrittura di un bando estratto nel database."""

import sqlite3
from datetime import date

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
]


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


def salva(riga: dict, url: str, fonte: str, codice_fonte: str) -> None:
    """Scrive o aggiorna la riga del bando nel database.

    Un bando si aggiorna solo con lo stesso id e lo stesso URL. Se l'id
    appartiene a un altro URL, o l'URL a un altro id, solleva
    ConflittoBando e non scrive nulla.

    L'aggiornamento usa ON CONFLICT DO UPDATE, non INSERT OR REPLACE:
    REPLACE cancellerebbe la riga, in silenzio, insieme ai riferimenti
    delle tabelle beneficiari_bando e interventi_bando.

    Finche' l'estrattore produce ammette_comuni (si'/no), il valore 1
    diventa una riga di beneficiari_bando di tipo 'comune', con origine
    'ammette_comuni', come nella migrazione dei bandi esistenti.
    """
    riga = dict(riga)
    riga["url"] = url_canonico(url)
    riga["fonte"] = fonte
    riga["codice_fonte"] = codice_fonte
    riga["verificato_il"] = date.today().isoformat()

    valori = [riga.get(c) for c in COLONNE]
    segnaposto = ", ".join("?" for _ in COLONNE)
    elenco = ", ".join(COLONNE)
    aggiorna = ", ".join(f"{c} = excluded.{c}" for c in COLONNE if c != "id")

    conn = connetti()
    try:
        problema = _conflitto(conn, riga["id"], riga["url"])
        if problema:
            raise ConflittoBando(f"Non salvo: {problema}")

        conn.execute(
            f"INSERT INTO bandi ({elenco}) VALUES ({segnaposto}) "
            f"ON CONFLICT(id) DO UPDATE SET {aggiorna}",
            valori,
        )
        conn.execute(
            "DELETE FROM beneficiari_bando "
            "WHERE id_bando = ? AND origine = 'ammette_comuni'",
            (riga["id"],),
        )
        if riga.get("ammette_comuni") == 1:
            conn.execute(
                "INSERT INTO beneficiari_bando (id_bando, tipo, frase, origine) "
                "VALUES (?, 'comune', ?, 'ammette_comuni')",
                (riga["id"], riga["beneficiari"]),
            )
        conn.commit()
    finally:
        conn.close()
