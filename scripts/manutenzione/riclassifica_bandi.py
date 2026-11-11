"""Riclassifica con l'estrattore nuovo i bandi gia' in archivio.

Uso:
    python -u -m scripts.manutenzione.riclassifica_bandi --prova   elenca e stima il costo
    python -u -m scripts.manutenzione.riclassifica_bandi           riclassifica

Si esaminano i bandi non ancora classificati (classificato_il vuoto):
rilanciare lo script riprende quelli rimasti. Per ciascuno si riscarica
la pagina e si estrae con l'estrattore nuovo, che porta beneficiari per
tipo, interventi e cumulabilita'.

Nessun dato attuale si perde:
- se la pagina non si scarica, l'estrazione fallisce o la validazione
  trova problemi, la riga resta com'e';
- se il modello dice che la pagina non e' un bando, la riga resta com'e'
  e il caso si segnala: la decisione spetta a chi rivede;
- un campo pieno che torna vuoto conserva il valore vecchio, e il caso
  si elenca a parte con il motivo, perche' un valore che l'estrattore
  nuovo non riesce a provare e' sospetto e va controllato a mano.

Un bando scaduto si riclassifica comunque: i bandi scaduti restano in
archivio. Le pagine dei bandi in archivio non passano dal registro delle
scansioni, che riguarda la scoperta di pagine nuove.
"""

import sys
import time
from http.client import HTTPException

from anthropic import APIError
from langchain_core.callbacks import get_usage_metadata_callback

from scripts.ingestione.estrai_nuovi import (
    COSTO_BANDO,
    errore_bloccante,
    mostra_costo,
)
from src.database.schema import aggiorna_csv, connetti
from src.estrazione.bandi import (
    costruisci_estrattore,
    decidi_automatico,
    estrai,
    valida,
)
from src.estrazione.pagina import prendi
from src.estrazione.salva import COLONNE, salva

PAUSA = 1.0

# Le colonne che l'estrazione non decide: le scrive salva()
NON_ESTRATTE = {"id", "url", "fonte", "codice_fonte", "verificato_il"}
COLONNE_FUSE = [c for c in COLONNE if c not in NON_ESTRATTE]

# Il motivo di un valore vuoto quando nessun avviso lo spiega
SENZA_AVVISO = "il modello non ha restituito un valore"

TABELLE_BANDO = ("bandi", "beneficiari_bando", "interventi_bando")


def _vuoto(valore) -> bool:
    return valore is None or valore == ""


def _motivo(colonna: str, avvisi: list[str]) -> str:
    """L'avviso che spiega perche' la colonna e' vuota, se c'e'.

    La frase di cumulabilita' si spiega con l'avviso di cumulabilita'.
    """
    nome = colonna.removesuffix("_frase")
    return next((a for a in avvisi if a.startswith(f"{nome}:")), SENZA_AVVISO)


def fondi(precedente: dict, riga: dict, avvisi: list[str]) -> list[dict]:
    """Rimette nella riga nuova i valori vecchi che tornano vuoti.

    Modifica riga e restituisce i valori mantenuti, con colonna, valore
    vecchio e motivo per cui il nuovo e' vuoto.
    """
    mantenuti = []
    for colonna in COLONNE_FUSE:
        vecchio = precedente.get(colonna)
        if _vuoto(vecchio) or not _vuoto(riga.get(colonna)):
            continue
        riga[colonna] = vecchio
        mantenuti.append(
            {
                "colonna": colonna,
                "vecchio": vecchio,
                "motivo": _motivo(colonna, avvisi),
            }
        )
    return mantenuti


def differenze(precedente: dict, riga: dict) -> list[tuple[str, object, object]]:
    """Le colonne piene in entrambe le righe con valori diversi."""
    return [
        (c, precedente.get(c), riga.get(c))
        for c in COLONNE_FUSE
        if not _vuoto(precedente.get(c))
        and not _vuoto(riga.get(c))
        and str(precedente.get(c)) != str(riga.get(c))
    ]


def da_riclassificare() -> list[dict]:
    """I bandi in archivio non ancora classificati, in ordine di id."""
    conn = connetti()
    try:
        righe = conn.execute(
            "SELECT * FROM bandi WHERE classificato_il IS NULL ORDER BY id"
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in righe]


def riclassifica(estrattore, precedente: dict) -> dict:
    """Estrae di nuovo un bando e, se l'estrazione regge, lo aggiorna.

    Restituisce l'esito: salvato, non_bando o fallito, con il motivo, gli
    avvisi, i valori vecchi mantenuti e le differenze.
    """
    esito = {"id": precedente["id"], "mantenuti": [], "cambiati": [], "avvisi": []}

    try:
        testo = prendi(precedente["url"])
    except (OSError, HTTPException) as errore:
        return {
            **esito,
            "esito": "fallito",
            "motivo": f"pagina non scaricata ({errore})",
        }

    estrazione = estrai(estrattore, testo)
    riga, problemi, avvisi = valida(estrazione, testo)
    esito["avvisi"] = avvisi

    if estrazione.natura == "non_bando":
        return {**esito, "esito": "non_bando", "motivo": estrazione.natura_motivo}
    if problemi:
        return {**esito, "esito": "fallito", "motivo": "; ".join(problemi)}

    riga["id"] = precedente["id"]
    esito["mantenuti"] = fondi(precedente, riga, avvisi)
    esito["cambiati"] = differenze(precedente, riga)
    _, stato = decidi_automatico(estrazione, riga)

    salva(riga, precedente["url"], precedente["fonte"], precedente["codice_fonte"])
    return {**esito, "esito": "salvato", "motivo": stato}


def mostra_rapporto(esiti: list[dict]) -> None:
    """Esiti, differenze e, a parte, i valori vecchi mantenuti."""
    print("\n" + "=" * 74)
    conteggio = {}
    for e in esiti:
        conteggio[e["esito"]] = conteggio.get(e["esito"], 0) + 1
    print("RIEPILOGO: " + ", ".join(f"{n} {k}" for k, n in conteggio.items()))
    print("=" * 74)

    for genere in ("salvato", "non_bando", "fallito"):
        scelti = [e for e in esiti if e["esito"] == genere]
        if not scelti:
            continue
        print(f"\n{genere.upper()}")
        for e in scelti:
            print(f"  {e['id'][:50]:50} {e['motivo']}")

    cambiati = [e for e in esiti if e["cambiati"]]
    if cambiati:
        print("\nVALORI CAMBIATI (prima -> dopo)")
        for e in cambiati:
            print(f"  {e['id']}")
            for colonna, prima, dopo in e["cambiati"]:
                print(f"    {colonna}: {prima}  ->  {dopo}")

    mantenuti = [e for e in esiti if e["mantenuti"]]
    print("\nVALORI VECCHI MANTENUTI PERCHE' IL NUOVO E' VUOTO (da controllare)")
    if not mantenuti:
        print("  nessuno")
    for e in mantenuti:
        print(f"  {e['id']}")
        for m in e["mantenuti"]:
            print(f"    {m['colonna']}: {m['vecchio']}")
            print(f"      motivo: {m['motivo']}")


def main() -> None:
    bandi = da_riclassificare()
    print(f"Bandi da riclassificare: {len(bandi)}")
    print(f"Costo stimato: circa {len(bandi) * COSTO_BANDO:.2f} $")

    if "--prova" in sys.argv:
        for b in bandi:
            print(f"  {b['id'][:50]:50} {b['url']}")
        print("\nProva: nessuna estrazione eseguita, nulla modificato.")
        return

    if not bandi:
        return

    estrattore = costruisci_estrattore()
    esiti = []

    with get_usage_metadata_callback() as contatore:
        for numero, precedente in enumerate(bandi, start=1):
            print(f"\n[{numero}/{len(bandi)}] {precedente['id']}")
            try:
                esito = riclassifica(estrattore, precedente)
            except (APIError, ValueError, OSError, HTTPException) as errore:
                if errore_bloccante(errore):
                    # La riga resta com'e' e senza classificato_il: un
                    # nuovo lancio la riprende
                    print(
                        f"\nINTERROTTO: problema di credito o autenticazione ({errore})"
                    )
                    break
                esito = {
                    "id": precedente["id"],
                    "esito": "fallito",
                    "motivo": str(errore),
                    "mantenuti": [],
                    "cambiati": [],
                    "avvisi": [],
                }

            esiti.append(esito)
            print(f"    {esito['esito']} ({esito['motivo'][:70]})")
            time.sleep(PAUSA)

    mostra_rapporto(esiti)
    mostra_costo(contatore.usage_metadata, len(esiti))
    aggiorna_csv(*TABELLE_BANDO)


if __name__ == "__main__":
    main()
