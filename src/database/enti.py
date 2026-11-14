"""Estrazione informazioni enti dalle tabelle."""

import sqlite3

COLONNE_PROFILO = [
    "nome",
    "tipo",
    "regione",
    "provincia",
    "area_interna",
    "capofila_area",
    "toscana_diffusa",
]
COLONNE_SI_NO = [
    "capofila_area",
    "toscana_diffusa",
]


def profilo_ente(conn: sqlite3.Connection, codice: str) -> dict:
    """Il profilo dell’ente per il router, con i sì e no come booleani.

    Per un Comune il profilo riporta anche il nome dell'Unione di cui fa
    parte: None se l'appartenenza non e' in archivio, cioe' non verificata.
    Il profilo di un'Unione non ha questo campo.
    """
    elenco = ", ".join(f"e.{c}" for c in COLONNE_PROFILO)
    riga = conn.execute(
        f"SELECT {elenco}, u.nome AS unione FROM enti e "
        "LEFT JOIN enti u ON u.codice_fiscale = e.unione "
        "WHERE e.codice_fiscale = ?",
        (codice,),
    ).fetchone()
    if riga is None:
        raise ValueError(f"Ente non trovato: {codice}")
    profilo = dict(riga)
    for colonna in COLONNE_SI_NO:
        if profilo[colonna] is not None:
            profilo[colonna] = bool(profilo[colonna])
    if profilo["tipo"] != "comune":
        del profilo["unione"]
    return profilo


def elenco_enti(
    conn: sqlite3.Connection,
) -> list[tuple[str, str]]:
    """legge la riga della tabella enti e ne estrae codice e nome di tutti gli enti."""
    righe = conn.execute(
        "SELECT codice_fiscale,nome FROM enti ORDER BY nome"
    ).fetchall()
    if not righe:
        raise ValueError(
            "Nessun ente in archivio: caricare enti.csv con step4_crea_db."
        )
    return [(r["codice_fiscale"], r["nome"]) for r in righe]
