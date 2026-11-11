"""Registro delle pagine gia' esaminate durante le scansioni."""

from datetime import date

from src.database.schema import connetti
from src.estrazione.indirizzi import url_canonico

# Motivi di scarto definitivi: non ha senso riesaminarli
DEFINITIVI = ("scaduto", "non ammette i Comuni")


def registra(
    url: str,
    codice_fonte: str,
    slug: str | None,
    esito: str,
    motivo: str = "",
    avvisi: str = "",
) -> None:
    """Annota l'esito dell'esame di una pagina.

    La chiave e' l'URL in forma canonica: riesaminare la stessa pagina
    aggiorna la riga invece di aggiungerne una. Motivo e avvisi si
    registrano per intero, senza tagli.
    """
    conn = connetti()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO scansioni "
            "(url, codice_fonte, slug, esito, motivo, avvisi, esaminato_il) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                url_canonico(url),
                codice_fonte,
                slug,
                esito,
                motivo,
                avvisi or None,
                date.today().isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def da_non_riesaminare() -> set[str]:
    """Gli URL, in forma canonica, gia' esaminati con esito definitivo.

    Uno scaduto o non pertinente non cambia: riesaminarlo costa una
    chiamata e produce lo stesso risultato. Gli scarti per incertezza
    (scadenza non determinata, bassa confidenza) restano invece
    candidati, perche' la pagina o il prompt possono essere migliorati.
    """
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT url, motivo FROM scansioni WHERE esito = 'scartato'"
        ).fetchall()
    finally:
        conn.close()

    return {
        r["url"]
        for r in righe
        if any((r["motivo"] or "").startswith(d) for d in DEFINITIVI)
    }


def riepilogo() -> str:
    """Quante pagine sono state esaminate e con quale esito."""
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT esito, COUNT(*) AS quante FROM scansioni GROUP BY esito"
        ).fetchall()
        ultima = conn.execute("SELECT MAX(esaminato_il) FROM scansioni").fetchone()[0]
    finally:
        conn.close()

    if not righe:
        return "Nessuna scansione registrata."

    parti = [f"{r['esito']}: {r['quante']}" for r in righe]
    return f"Ultima scansione {ultima} | " + ", ".join(parti)
