"""Interrogazioni sui dati statistici del territorio, sempre riferite a un ente."""

import sqlite3

from src.database.modelli import Risultato, fonti_distinte


def popolazione_anno(
    conn: sqlite3.Connection, codice_ente: str, anno: int
) -> Risultato:
    """Residenti in un anno specifico."""
    riga = conn.execute(
        "SELECT * FROM popolazione WHERE codice_ente = ? AND anno = ?",
        (codice_ente, anno),
    ).fetchone()

    if riga is None:
        disponibili = conn.execute(
            "SELECT MIN(anno), MAX(anno) FROM popolazione WHERE codice_ente = ?",
            (codice_ente,),
        ).fetchone()
        if disponibili[0] is None:
            return Risultato(
                "Nessun dato di popolazione in archivio per questo ente.",
                trovato=False,
            )
        return Risultato(
            f"Nessun dato di popolazione per l'anno {anno}. "
            f"Anni disponibili: da {disponibili[0]} a {disponibili[1]}.",
            trovato=False,
        )

    return Risultato(
        f"Popolazione residente al 1 gennaio {riga['anno']}: "
        f"{riga['residenti']} abitanti.",
        fonti=[riga["fonte"]],
    )


def popolazione_ultima(conn: sqlite3.Connection, codice_ente: str) -> Risultato:
    """Il dato di popolazione più recente disponibile."""
    riga = conn.execute(
        "SELECT * FROM popolazione WHERE codice_ente = ? ORDER BY anno DESC LIMIT 1",
        (codice_ente,),
    ).fetchone()

    if riga is None:
        return Risultato(
            "Nessun dato di popolazione in archivio per questo ente.", trovato=False
        )

    return Risultato(
        f"Dato più recente: {riga['residenti']} abitanti al 1 gennaio {riga['anno']}.",
        fonti=[riga["fonte"]],
    )


def popolazione_serie(conn: sqlite3.Connection, codice_ente: str) -> Risultato:
    """L'intera serie storica, anno per anno."""
    righe = conn.execute(
        "SELECT * FROM popolazione WHERE codice_ente = ? ORDER BY anno",
        (codice_ente,),
    ).fetchall()

    if not righe:
        return Risultato(
            "Nessun dato di popolazione in archivio per questo ente.", trovato=False
        )

    elenco = "; ".join(f"{r['anno']}: {r['residenti']}" for r in righe)

    return Risultato(
        f"Serie storica della popolazione residente al 1 gennaio: {elenco}.",
        fonti=fonti_distinte(righe),
    )


def popolazione_variazione(
    conn: sqlite3.Connection,
    codice_ente: str,
    da: int | None = None,
    a: int | None = None,
) -> Risultato:
    """Variazione della popolazione tra due anni."""
    righe = conn.execute(
        "SELECT * FROM popolazione WHERE codice_ente = ? ORDER BY anno",
        (codice_ente,),
    ).fetchall()

    if len(righe) < 2:
        return Risultato(
            "Servono almeno due anni di dati per calcolare una variazione.",
            trovato=False,
        )

    primo = next((r for r in righe if r["anno"] == da), righe[0])
    ultimo = next((r for r in righe if r["anno"] == a), righe[-1])

    if primo["anno"] == ultimo["anno"]:
        return Risultato("Gli anni indicati coincidono.", trovato=False)

    differenza = ultimo["residenti"] - primo["residenti"]
    percentuale = differenza / primo["residenti"] * 100

    verso = "diminuita" if differenza < 0 else "aumentata"

    return Risultato(
        f"Tra il {primo['anno']} e il {ultimo['anno']} la popolazione è "
        f"{verso} di {abs(differenza)} unità "
        f"({percentuale:+.1f}%), passando da {primo['residenti']} "
        f"a {ultimo['residenti']} abitanti.",
        fonti=fonti_distinte([primo, ultimo]),
    )


def dato_territoriale(
    conn: sqlite3.Connection, codice_ente: str, chiave: str
) -> Risultato:
    """Un dato stabile sul territorio, per chiave."""
    riga = conn.execute(
        "SELECT * FROM territorio WHERE codice_ente = ? AND chiave = ?",
        (codice_ente, chiave.lower()),
    ).fetchone()

    if riga is None:
        chiavi = conn.execute(
            "SELECT chiave FROM territorio WHERE codice_ente = ?",
            (codice_ente,),
        ).fetchall()
        elenco = ", ".join(r["chiave"] for r in chiavi) or "nessuna"
        return Risultato(
            f"Nessun dato territoriale per '{chiave}'. Chiavi disponibili: {elenco}.",
            trovato=False,
        )

    valore = f"{riga['chiave'].capitalize()}: {riga['valore']} {riga['unita'] or ''}"

    return Risultato(valore.strip() + ".", fonti=[riga["fonte"]])


def densita_abitativa(conn: sqlite3.Connection, codice_ente: str) -> Risultato:
    """Abitanti per chilometro quadrato, calcolata sui dati più recenti."""
    pop = conn.execute(
        "SELECT * FROM popolazione WHERE codice_ente = ? ORDER BY anno DESC LIMIT 1",
        (codice_ente,),
    ).fetchone()
    sup = conn.execute(
        "SELECT * FROM territorio WHERE codice_ente = ? AND chiave = 'superficie'",
        (codice_ente,),
    ).fetchone()

    if pop is None or sup is None:
        return Risultato(
            "Servono sia la popolazione sia la superficie per calcolare "
            "la densità, e uno dei due dati manca.",
            trovato=False,
        )

    densita = pop["residenti"] / sup["valore"]

    return Risultato(
        f"Densità abitativa: {densita:.1f} abitanti per kmq "
        f"({pop['residenti']} abitanti al 1 gennaio {pop['anno']} "
        f"su {sup['valore']} kmq). Valore calcolato, non riportato "
        f"come tale nelle fonti.",
        fonti=[pop["fonte"], sup["fonte"]],
    )
