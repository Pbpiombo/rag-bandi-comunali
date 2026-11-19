"""Corregge a mano campi dei bandi e dei beneficiari, con le frasi di un testo salvato.

Uso:
    python -m scripts.manutenzione.correggi_da_testo --prova   verifica soltanto
    python -m scripts.manutenzione.correggi_da_testo           corregge

Come correggi_atti, ma senza rete: le frasi che provano il valore corretto
si cercano (con frase_nel_testo) nel testo della pagina gia' salvato in
dati-grezzi, non in una pagina riscaricata. Per ogni correzione: la
tabella, la riga, i valori che devono esserci in archivio, i valori
corretti, le frasi e il file del testo. Si corregge solo se i valori in
archivio sono ancora tutti quelli attesi e tutte le frasi si trovano;
altrimenti si salta e lo si dice. I campi di una correzione cambiano
insieme (per esempio pubblicato_il e pubblicato_origine).

Tabelle e campi correggibili stanno in CAMPI. Una riga di
beneficiari_bando si indica con id_bando e tipo, e deve essere una sola;
la sua correzione mette origine 'manuale'.

Alla fine riversa nei CSV le tabelle toccate. Rilanciarlo non cambia
nulla: una correzione gia' applicata si riconosce e si salta.

Queste correzioni non sono protette da una riestrazione futura: vanno
ricontrollate se il bando si riestrae.
"""

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from src.config import DATI_GREZZI_DIR
from src.database.schema import aggiorna_csv, connetti
from src.estrazione.beneficiari import frase_nel_testo

# Tabella -> (campi che identificano la riga, campi correggibili)
CAMPI = {
    "bandi": (("id",), ("pubblicato_il", "pubblicato_origine")),
    "beneficiari_bando": (("id_bando", "tipo"), ("soggetto", "origine")),
}


@dataclass(frozen=True)
class Correzione:
    """Una correzione: dove, da che cosa, a che cosa, con quali prove."""

    tabella: str
    riga: dict
    attesi: dict
    corretti: dict
    frasi: tuple
    testo: Path


TESTO_RIEVOCAZIONE = (
    DATI_GREZZI_DIR / "manuali" / "2026-11-19" / "fondo-rievocazione-storica-2027.txt"
)

# Riga 355 del testo salvato, la prima frase
FRASE_BENEFICIARI_RIEVOCAZIONE = (
    "Possono presentare istanza di contributo gli Enti locali, soggetti "
    "pubblici, enti di rievocazione storica, vale a dire le associazioni di "
    "promozione sociale, le organizzazioni non lucrative di utilità sociale e "
    "le fondazioni che hanno per fine statutario la tutela e la trasmissione "
    "della memoria storica"
)

CORREZIONI = [
    # Il modello ha preso la data del decreto (20/03/2025) al posto della
    # data di pubblicazione della pagina, righe 21 e 360 del testo salvato
    Correzione(
        tabella="bandi",
        riga={"id": "fondo-rievocazione-storica-2027"},
        attesi={"pubblicato_il": "2025-03-20", "pubblicato_origine": "atto"},
        corretti={"pubblicato_il": "2026-11-03", "pubblicato_origine": "pubblicazione"},
        frasi=("3 Novembre 2026",),
        testo=TESTO_RIEVOCAZIONE,
    ),
    # Il soggetto della riga altro_ente_pubblico era "Enti locali": il tipo
    # viene da "soggetti pubblici", riga 355 del testo salvato
    Correzione(
        tabella="beneficiari_bando",
        riga={
            "id_bando": "fondo-rievocazione-storica-2027",
            "tipo": "altro_ente_pubblico",
        },
        attesi={"soggetto": "Enti locali", "origine": "estrazione"},
        corretti={"soggetto": "soggetti pubblici", "origine": "manuale"},
        frasi=(FRASE_BENEFICIARI_RIEVOCAZIONE,),
        testo=TESTO_RIEVOCAZIONE,
    ),
]


def _controlla(correzione: Correzione) -> None:
    """La correzione tocca solo righe e campi ammessi."""
    chiave, correggibili = CAMPI[correzione.tabella]
    assert tuple(correzione.riga) == chiave, correzione.riga
    assert set(correzione.attesi) == set(correzione.corretti), correzione
    assert set(correzione.corretti) <= set(correggibili), correzione.corretti


def correggi(
    conn: sqlite3.Connection, correzione: Correzione, testo: str | None, prova: bool
) -> str:
    """Verifica e applica una correzione; dice cosa e' successo.

    testo: il testo salvato in cui cercare le frasi; None se il file manca.
    """
    _controlla(correzione)
    campi = list(correzione.corretti)
    dove = " AND ".join(f"{c} = ?" for c in correzione.riga)
    righe = conn.execute(
        f"SELECT {', '.join(campi)} FROM {correzione.tabella} WHERE {dove}",
        tuple(correzione.riga.values()),
    ).fetchall()
    if not righe:
        return "NON TROVATO"
    if len(righe) > 1:
        return f"SALTATO: {len(righe)} righe corrispondono, ne serve una"

    attuale = dict(zip(campi, righe[0], strict=True))
    if attuale == correzione.corretti:
        return "gia' corretto"
    diversi = {c: v for c, v in attuale.items() if v != correzione.attesi[c]}
    if diversi:
        return f"SALTATO: in archivio {diversi}, attesi {correzione.attesi}"

    if testo is None:
        return f"SALTATO: testo non trovato ({correzione.testo})"
    mancanti = [f for f in correzione.frasi if not frase_nel_testo(f, testo)]
    if mancanti:
        return f"SALTATO: frasi non trovate nel testo: {mancanti}"

    cambi = ", ".join(
        f"{c}: «{attuale[c]}» -> «{correzione.corretti[c]}»" for c in campi
    )
    if prova:
        return f"da correggere: {cambi}"
    imposta = ", ".join(f"{c} = ?" for c in campi)
    conn.execute(
        f"UPDATE {correzione.tabella} SET {imposta} WHERE {dove}",
        (*correzione.corretti.values(), *correzione.riga.values()),
    )
    return f"corretto: {cambi}"


def leggi_testo(percorso: Path) -> str | None:
    """Il testo salvato, o None se il file manca."""
    return percorso.read_text(encoding="utf-8") if percorso.exists() else None


def applica(
    conn: sqlite3.Connection, correzioni: list[Correzione], prova: bool
) -> tuple[list[str], set[str]]:
    """Le correzioni, in ordine: i messaggi e le tabelle modificate."""
    messaggi, toccate = [], set()
    for correzione in correzioni:
        esito = correggi(conn, correzione, leggi_testo(correzione.testo), prova)
        riga = ", ".join(f"{c}={v}" for c, v in correzione.riga.items())
        messaggi.append(f"{correzione.tabella} [{riga}]: {esito}")
        if esito.startswith("corretto"):
            toccate.add(correzione.tabella)
    return messaggi, toccate


def main(correzioni: list[Correzione] | None = None) -> None:
    prova = "--prova" in sys.argv
    conn = connetti()
    try:
        messaggi, toccate = applica(conn, correzioni or CORREZIONI, prova)
        conn.commit()
    finally:
        conn.close()

    for messaggio in messaggi:
        print(f"  {messaggio}")
    if prova:
        print("\nProva: nulla modificato.")
        return
    if toccate:
        aggiorna_csv(*sorted(toccate))


if __name__ == "__main__":
    main()
