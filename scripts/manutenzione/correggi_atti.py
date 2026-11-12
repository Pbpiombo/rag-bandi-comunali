"""Corregge a mano atti e una nota dei bandi, dalla seconda verifica.

Uso:
    python -m scripts.manutenzione.correggi_atti --prova   verifica soltanto
    python -m scripts.manutenzione.correggi_atti           corregge

Script una tantum (verifica a mano del 12 novembre 2026). Per ogni bando:
il campo, il valore che deve esserci in archivio, il valore corretto e le
frasi della pagina che lo provano. La pagina si riscarica e ogni frase si
cerca con frase_nel_testo. Si corregge solo se il valore in archivio e'
ancora quello atteso e tutte le frasi si trovano; altrimenti si salta e lo
si dice.

riferimento_atto: il decreto che approva il bando e quelli che ne
modificano scadenze o requisiti, proroghe comprese. Per le risorse
genetiche forestali si rimette il valore precedente alla riestrazione del
12 novembre 2026, che aveva perso le due proroghe.

Alla fine riversa bandi nel CSV. Rilanciarlo non cambia nulla.

Queste correzioni non sono protette da una riestrazione futura: vanno
ricontrollate alla prossima scansione (roadmap, "In coda").
"""

import sys
from http.client import HTTPException

from src.database.schema import aggiorna_csv, connetti
from src.estrazione.beneficiari import frase_nel_testo
from src.estrazione.pagina import prendi

CAMPI = ("riferimento_atto", "scadenza_nota")

# id del bando -> (campo, valore atteso, valore corretto, frasi della pagina)
CORREZIONI = {
    "risorse-genetiche-forestali-2026": (
        "riferimento_atto",
        "decreto dirigenziale 14800 del 29 giugno 2026",
        (
            "Decreto dirigenziale 14800 del 29 giugno 2026, modificato con "
            "decreto dirigenziale 21128 del 24 settembre 2026 e decreto "
            "dirigenziale 23817 del 29 ottobre 2026"
        ),
        [
            (
                "Proroga per presentare le domande di sostegno fino alle ore 13 "
                "del 30 ottobre 2026 (scadenza iniziale 30 settembre 2026), con "
                "decreto dirigenziale 21128 del 24 settembre 2026"
            ),
            (
                "ulteriore proroga fino alle ore 13.00 del 13 novembre 2026 , con "
                "decreto dirigenziale 23817 del 29 ottobre 2026"
            ),
        ],
    ),
    "sostegno-della-conciliazione-vita-lavoro-contributo-p-f32ff6": (
        "riferimento_atto",
        "decreto dirigenziale 25139 del 11 novembre 2024",
        (
            "decreto dirigenziale 25139 del 11 novembre 2024, modificato con "
            "decreto dirigenziale 13318 del 16 giugno 2026"
        ),
        [
            (
                "Pproroga per presentare domanda fino al 31 ottobre 2027, con "
                "decreto dirigenziale 13318 del 16 giugno 2026"
            ),
        ],
    ),
    "sicurezza-e-salute-nei-luoghi-di-lavoro-il-bando-2026-757f63": (
        "riferimento_atto",
        "decreto dirigenziale 13543 del 15 giugno 2026",
        (
            "decreto dirigenziale 13543 del 15 giugno 2026, modificato con "
            "decreto dirigenziale 23818 del 27 ottobre 2026"
        ),
        [
            (
                "La Regione Toscana con decreto dirigenziale 23818 del 27 ottobre "
                "2026, pubblicato sul Burt del 4 novembre 2026 supplemento 253 "
                "alla parte III, ha approvato, per le motivazioni espresse nella "
                "narrativa del decreto stesso, modifiche necessarie del testo del "
                "bando"
            ),
        ],
    ),
    "mercati-rionali-2026": (
        "riferimento_atto",
        "decreto dirigenziale 13287 del 10 giugno 2026",
        (
            "decreto dirigenziale 13287 del 10 giugno 2026, modificato con "
            "decreto dirigenziale 20141 del 11 settembre 2026"
        ),
        [
            (
                "scadenza del bando prorogata fino alle ore 12 del 15 ottobre "
                "2026, con decreto dirigenziale 20141 del 11 settembre 2026"
            ),
        ],
    ),
    "percorsi-formativi-ecosistemi-2026": (
        "riferimento_atto",
        "Decreto dirigenziale 17615 del 31 luglio 2026",
        (
            "Decreto dirigenziale 17615 del 31 luglio 2026, modificato con "
            "decreti dirigenziali 19940 del 7 settembre 2026 e 20251 del 14 "
            "settembre 2026"
        ),
        [
            (
                "Proroga per presentare la domanda fino alle ore 13 del 12 ottobre "
                '2026 e chiarimento sui "Soggetti ammessi alla presentazione dei '
                'progetti", con decreto dirigenziale 19940 del 7 settembre 2026'
            ),
            (
                "Specifica sulla natura degli interventi e dei destinatar i, con "
                "decreto dirigenziale 20251 del 14 settembre 2026"
            ),
        ],
    ),
    # sportello e data di chiusura non si contraddicono: la nota le riporta
    "conciliazione-vita-lavoro-contributi-per-lavoratrici-3d10eb": (
        "scadenza_nota",
        (
            "Il testo indica sia che le domande sono raccolte fino a esaurimento "
            "delle risorse disponibili, sia una data di scadenza fissa al "
            "31.10.2027: le due informazioni sono contraddittorie"
        ),
        (
            "Domande fino ad esaurimento delle risorse disponibili; Data di "
            "scadenza presentazione domande: 31.10.2027"
        ),
        [
            "Domande fino ad esaurimento delle risorse disponibili",
            "Data di scadenza presentazione domande: 31.10.2027",
        ],
    ),
}


def correggi(conn, id_bando: str, correzione: tuple, prova: bool) -> str:
    """Verifica e applica una correzione; dice cosa e' successo."""
    campo, atteso, corretto, frasi = correzione
    assert campo in CAMPI
    riga = conn.execute(
        f"SELECT url, {campo} FROM bandi WHERE id = ?", (id_bando,)
    ).fetchone()
    if riga is None:
        return "NON TROVATO"
    if riga[campo] == corretto:
        return f"{campo} gia' corretto"
    if riga[campo] != atteso:
        return f"SALTATO: {campo} in archivio e' «{riga[campo]}», atteso «{atteso}»"

    try:
        testo = prendi(riga["url"])
    except (OSError, HTTPException) as errore:
        return f"SALTATO: pagina non scaricata ({errore})"
    mancanti = [f for f in frasi if not frase_nel_testo(f, testo)]
    if mancanti:
        return f"SALTATO: frasi non trovate nella pagina: {mancanti}"

    if not prova:
        conn.execute(f"UPDATE bandi SET {campo} = ? WHERE id = ?", (corretto, id_bando))
    return f"{'da correggere' if prova else 'corretto'}: {campo}, frasi trovate"


def main() -> None:
    prova = "--prova" in sys.argv
    conn = connetti()
    try:
        for id_bando, correzione in CORREZIONI.items():
            print(f"  {id_bando}: {correggi(conn, id_bando, correzione, prova)}")
        conn.commit()
    finally:
        conn.close()

    if prova:
        print("\nProva: nulla modificato.")
        return
    aggiorna_csv("bandi")


if __name__ == "__main__":
    main()
