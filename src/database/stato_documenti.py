"""Stato del bando a cui appartiene un frammento documentale (proposta P3).

Nella prova del 12 novembre 2026 l'avviso per i mercati rionali, scaduto
il 15 ottobre, è stato presentato dai frammenti come attuale: il testo di
un bando non sa di essere scaduto. Qui lo stato si calcola alla data della
domanda, con le stesse funzioni delle interrogazioni sui bandi, e va
nell'intestazione del frammento. Non si memorizza da nessuna parte: si
ricalcola a ogni domanda, su copie dei documenti recuperati.

Un frammento è collegato a un bando:
- dal metadato `id_bando`, se c'è;
- altrimenti dall'atto dei metadati (`riferimento_atto`), solo se il
  collegamento è certo: la coppia numero e data dell'atto compare
  nell'atto di un solo bando in archivio. Con zero o più bandi
  corrispondenti, nessuno stato: meglio niente che uno sbagliato.
"""

import sqlite3
from datetime import date

from langchain_core.documents import Document

from src.database.interrogazioni_bandi import (
    SENZA_SCADENZA,
    scadenze_di,
    stato_finestre,
    stato_sportello,
    tra_quanto,
)
from src.normalizzazione import atti_con_data


def stato_bando(riga, scadenze: list, oggi: str) -> str:
    """Lo stato di un bando alla data `oggi` (ISO), in una frase.

    Un bando con più date segue le sue finestre; uno con la scadenza
    passata è scaduto, anche se a sportello; uno sportello aperto invita a
    verificare le risorse.
    """
    finestre = stato_finestre(riga, scadenze, oggi)
    if finestre:
        return finestre

    scadenza = riga["scadenza"]
    if scadenza and scadenza < oggi:
        return f"scaduto il {scadenza}"
    if riga["a_sportello"]:
        return stato_sportello(riga, oggi)
    if scadenza:
        giorni = (date.fromisoformat(scadenza) - date.fromisoformat(oggi)).days
        return f"aperto, scade il {scadenza} ({tra_quanto(giorni)})"
    return SENZA_SCADENZA


def bando_del_documento(conn: sqlite3.Connection, metadati: dict):
    """La riga di `bandi` a cui appartiene il documento, o None."""
    id_bando = metadati.get("id_bando")
    if id_bando:
        riga = conn.execute("SELECT * FROM bandi WHERE id = ?", (id_bando,)).fetchone()
    else:
        atti = atti_con_data(str(metadati.get("riferimento_atto") or ""))
        if not atti:
            return None
        candidati = [
            r
            for r in conn.execute(
                "SELECT * FROM bandi WHERE riferimento_atto IS NOT NULL"
            ).fetchall()
            if atti & atti_con_data(r["riferimento_atto"])
        ]
        riga = candidati[0] if len(candidati) == 1 else None

    if riga is None or riga["natura"] == "non_bando":
        return None
    return riga


def con_stato_bando(
    documenti: list[Document], conn: sqlite3.Connection, oggi: str
) -> list[Document]:
    """Copie dei documenti con il metadato `stato_bando`, dove c'è un bando.

    Lo stato porta la data a cui è calcolato: "scaduto il 2026-10-15 (alla
    data del 2026-11-12)". I documenti originali non si toccano: possono
    essere quelli tenuti in memoria dal recupero.
    """
    risultato = []
    stati: dict[str, str | None] = {}
    for documento in documenti:
        riga = bando_del_documento(conn, documento.metadata)
        if riga is None:
            risultato.append(documento)
            continue
        if riga["id"] not in stati:
            scadenze = scadenze_di(conn, riga["id"])
            stati[riga["id"]] = (
                f"{stato_bando(riga, scadenze, oggi)} (alla data del {oggi})"
            )
        metadati = {**documento.metadata, "stato_bando": stati[riga["id"]]}
        risultato.append(
            Document(page_content=documento.page_content, metadata=metadati)
        )
    return risultato
