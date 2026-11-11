"""Interrogazioni sui bandi: filtri per apertura, beneficiari e tema."""

import sqlite3
from datetime import date

from src.database.modelli import Risultato

# Un Comune puo' presentare domanda: c'e' una riga di beneficiari_bando di
# tipo 'comune'. Si calcola dai beneficiari, non si memorizza nel bando.
AMMETTE_COMUNI = (
    "EXISTS (SELECT 1 FROM beneficiari_bando AS b "
    "WHERE b.id_bando = bandi.id AND b.tipo = 'comune')"
)


def euro(valore) -> str:
    """Formatta un importo con il separatore di migliaia italiano.

    Python usa la convenzione americana con la virgola; qui serve il punto.
    """
    if not valore:
        return "?"
    return f"{valore:,.0f}".replace(",", ".")


def formatta_bando(riga, oggi: str) -> str:
    """Una riga di bando in forma leggibile."""
    pezzi = [f"«{riga['titolo']}» ({riga['ente']})"]

    if riga["a_sportello"]:
        pezzi.append(f"a sportello fino al {riga['scadenza']}")
    elif riga["scadenza"]:
        giorni = (date.fromisoformat(riga["scadenza"]) - date.fromisoformat(oggi)).days
        stato = f"scade il {riga['scadenza']}"
        if giorni >= 0:
            stato += f" (fra {giorni} giorni)"
        else:
            stato += f" (SCADUTO da {abs(giorni)} giorni)"
        pezzi.append(stato)

    if riga["scadenza_nota"]:
        pezzi.append(f"nota: {riga['scadenza_nota']}")

    pezzi.append(f"beneficiari: {riga['beneficiari']}")

    if riga["contributo_perc"]:
        pezzi.append(f"contributo fino al {riga['contributo_perc']:.0f}%")

    if riga["costo_min"] and riga["costo_max"]:
        pezzi.append(
            f"progetto ammissibile da {euro(riga['costo_min'])} "
            f"a {euro(riga['costo_max'])} euro"
        )
    elif riga["costo_max"]:
        pezzi.append(f"progetto fino a {euro(riga['costo_max'])} euro")
    elif riga["costo_min"]:
        pezzi.append(f"progetto da almeno {euro(riga['costo_min'])} euro")

    if riga["premialita"]:
        pezzi.append(f"premialità: {riga['premialita']}")

    pezzi.append(f"url: {riga['url']}")

    return " | ".join(pezzi)


def fonte_bando(riga) -> str:
    """La fonte di un bando, con la data in cui è stata verificata."""
    return (
        f"{riga['fonte']}, {riga['riferimento_atto']} "
        f"(dati verificati il {riga['verificato_il']})"
    )


def bandi_aperti_per_comuni(conn: sqlite3.Connection) -> Risultato:
    """I bandi ancora aperti a cui un Comune può presentare domanda."""
    oggi = date.today().isoformat()

    righe = conn.execute(
        f"""
        SELECT bandi.*, {AMMETTE_COMUNI} AS ammette_comuni FROM bandi
        WHERE {AMMETTE_COMUNI}
          AND (scadenza IS NULL OR scadenza >= ?)
        ORDER BY a_sportello, scadenza
        """,
        (oggi,),
    ).fetchall()

    if not righe:
        totale = conn.execute(
            f"SELECT COUNT(*) FROM bandi WHERE {AMMETTE_COMUNI}"
        ).fetchone()[0]
        return Risultato(
            f"Nessun bando aperto per i Comuni alla data del {oggi}. "
            f"In archivio ce ne sono {totale} rivolti ai Comuni, tutti scaduti.",
            trovato=False,
        )

    elenco = "\n".join(f"- {formatta_bando(r, oggi)}" for r in righe)

    return Risultato(
        f"Bandi aperti a cui un Comune può presentare domanda "
        f"(alla data del {oggi}), {len(righe)} in archivio:\n{elenco}",
        fonti=[fonte_bando(r) for r in righe],
    )


def bandi_in_scadenza(conn: sqlite3.Connection, giorni: int = 60) -> Risultato:
    """I bandi per Comuni che scadono entro un certo numero di giorni."""
    oggi = date.today()
    limite = date.fromordinal(oggi.toordinal() + giorni).isoformat()

    righe = conn.execute(
        f"""
        SELECT bandi.*, {AMMETTE_COMUNI} AS ammette_comuni FROM bandi
        WHERE {AMMETTE_COMUNI}
          AND a_sportello = 0
          AND scadenza BETWEEN ? AND ?
        ORDER BY scadenza
        """,
        (oggi.isoformat(), limite),
    ).fetchall()

    if not righe:
        return Risultato(
            f"Nessun bando per Comuni in scadenza nei prossimi {giorni} giorni.",
            trovato=False,
        )

    elenco = "\n".join(f"- {formatta_bando(r, oggi.isoformat())}" for r in righe)

    return Risultato(
        f"Bandi per Comuni in scadenza entro {giorni} giorni:\n{elenco}",
        fonti=[fonte_bando(r) for r in righe],
    )


def bandi_per_tema(conn: sqlite3.Connection, tema: str) -> Risultato:
    """I bandi di un certo tema, con l'indicazione se aperti e per chi."""
    oggi = date.today().isoformat()

    righe = conn.execute(
        f"SELECT bandi.*, {AMMETTE_COMUNI} AS ammette_comuni FROM bandi "
        "WHERE tema LIKE ? ORDER BY scadenza DESC",
        (f"%{tema.lower()}%",),
    ).fetchall()

    if not righe:
        temi = conn.execute(
            "SELECT DISTINCT tema FROM bandi WHERE tema IS NOT NULL"
        ).fetchall()
        elenco = ", ".join(r["tema"] for r in temi) or "nessuno"
        return Risultato(
            f"Nessun bando sul tema '{tema}'. Temi in archivio: {elenco}.",
            trovato=False,
        )

    elenco = "\n".join(
        f"- {'[COMUNI AMMESSI] ' if r['ammette_comuni'] else '[NON per i Comuni] '}"
        f"{formatta_bando(r, oggi)}"
        for r in righe
    )

    return Risultato(
        f"Bandi sul tema '{tema}' in archivio:\n{elenco}",
        fonti=[fonte_bando(r) for r in righe],
    )


def dettaglio_bando(conn: sqlite3.Connection, id_bando: str) -> Risultato:
    """Tutti i dati strutturati di un singolo bando."""
    riga = conn.execute(
        f"SELECT bandi.*, {AMMETTE_COMUNI} AS ammette_comuni FROM bandi "
        "WHERE id = ? OR titolo LIKE ?",
        (id_bando, f"%{id_bando}%"),
    ).fetchone()

    if riga is None:
        ids = conn.execute("SELECT id FROM bandi").fetchall()
        return Risultato(
            f"Nessun bando corrisponde a '{id_bando}'. "
            f"Identificativi in archivio: {', '.join(r['id'] for r in ids)}.",
            trovato=False,
        )

    oggi = date.today().isoformat()
    ammessi = "SÌ" if riga["ammette_comuni"] else "NO"

    dotazione = (
        f"{euro(riga['dotazione'])} euro" if riga["dotazione"] else "non indicata"
    )

    return Risultato(
        f"{formatta_bando(riga, oggi)} | "
        f"Comuni ammessi: {ammessi} | "
        f"dotazione complessiva: {dotazione} | "
        f"atto: {riga['riferimento_atto']}",
        fonti=[fonte_bando(riga)],
    )
