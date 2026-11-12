"""Riclassifica con l'estrattore nuovo i bandi gia' in archivio.

Uso:
    python -u -m scripts.manutenzione.riclassifica_bandi --prova   elenca e stima il costo
    python -u -m scripts.manutenzione.riclassifica_bandi           riclassifica
    python -u -m scripts.manutenzione.riclassifica_bandi --id A --id B [--prova]

Si esaminano i bandi non ancora classificati (classificato_il vuoto):
rilanciare lo script riprende quelli rimasti. Con --id (ripetibile) si
riestraggono i bandi indicati, anche se gia' classificati; un id che non
e' in archivio si segnala e si salta. Per ciascuno si riscarica
la pagina e si estrae con l'estrattore nuovo, che porta beneficiari per
tipo, interventi e cumulabilita'.

Nessun dato attuale si perde:
- se la pagina non si scarica, l'estrazione fallisce o la validazione
  trova problemi, la riga resta com'e';
- se il modello dice che la pagina non e' un bando, i dati della riga
  restano com'erano, ma la riga si segna come non bando (segna_non_bando):
  non compare piu' tra le opportunita' e non si riesamina;
- un campo pieno che torna vuoto conserva il valore vecchio, e il caso
  si elenca a parte con il motivo, perche' un valore che l'estrattore
  nuovo non riesce a provare e' sospetto e va controllato a mano. Lo
  stesso per le date di scadenze_bando: se la nuova estrazione non ne
  trova, restano le vecchie.

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
    scadenza_dalle_righe,
    valida,
)
from src.estrazione.pagina import prendi
from src.estrazione.salva import COLONNE, COLONNE_SCADENZE, salva, segna_non_bando

PAUSA = 1.0

# Le colonne che l'estrazione non decide: le scrive salva()
NON_ESTRATTE = {
    "id",
    "url",
    "fonte",
    "codice_fonte",
    "verificato_il",
    "natura",
    "natura_motivo",
}
COLONNE_FUSE = [c for c in COLONNE if c not in NON_ESTRATTE]

# Il motivo di un valore vuoto quando nessun avviso lo spiega
SENZA_AVVISO = "il modello non ha restituito un valore"

TABELLE_BANDO = ("bandi", "beneficiari_bando", "interventi_bando", "scadenze_bando")


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


def scadenze_precedenti(id_bando: str) -> list[dict]:
    """Le righe di scadenze_bando gia' in archivio per un bando."""
    conn = connetti()
    try:
        righe = conn.execute(
            f"SELECT {', '.join(COLONNE_SCADENZE)} FROM scadenze_bando "
            "WHERE id_bando = ? ORDER BY numero",
            (id_bando,),
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in righe]


def mantieni_scadenze(
    precedenti: list[dict], riga: dict, avvisi: list[str]
) -> dict | None:
    """Rimette nella riga nuova le date vecchie, se le nuove sono vuote.

    salva() sostituisce le righe di scadenze_bando: senza questo, una nuova
    estrazione che non ritrova le date le cancellerebbe, comprese quelle
    inserite a mano. Con le date vecchie, la scadenza del bando torna
    l'ultima scadenza 'domanda'. Restituisce il valore mantenuto, nella
    forma di fondi(), o None se non c'era niente da mantenere.
    """
    if riga.get("scadenze") or not precedenti:
        return None
    riga["scadenze"] = [dict(p) for p in precedenti]
    scadenza_dalle_righe(riga, avvisi)
    return {
        "colonna": "scadenze_bando",
        "vecchio": "; ".join(f"{p['descrizione']} {p['scadenza']}" for p in precedenti),
        "motivo": _motivo("scadenze", avvisi),
    }


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


def da_riestrarre(ids: list[str]) -> tuple[list[dict], list[str]]:
    """I bandi indicati, anche se gia' classificati, e gli id non trovati.

    L'ordine e' quello degli id; un id ripetuto conta una volta.
    """
    conn = connetti()
    try:
        trovati, mancanti = [], []
        for id_bando in dict.fromkeys(ids):
            riga = conn.execute(
                "SELECT * FROM bandi WHERE id = ?", (id_bando,)
            ).fetchone()
            if riga is None:
                mancanti.append(id_bando)
            else:
                trovati.append(dict(riga))
    finally:
        conn.close()
    return trovati, mancanti


def ids_richiesti(argomenti: list[str]) -> list[str]:
    """Gli id passati con --id, che si puo' ripetere."""
    return [
        argomenti[i + 1]
        for i, a in enumerate(argomenti[:-1])
        if a == "--id" and not argomenti[i + 1].startswith("--")
    ]


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
        segna_non_bando(precedente["id"], estrazione.natura_motivo)
        return {**esito, "esito": "non_bando", "motivo": estrazione.natura_motivo}
    if problemi:
        return {**esito, "esito": "fallito", "motivo": "; ".join(problemi)}

    riga["id"] = precedente["id"]
    esito["mantenuti"] = fondi(precedente, riga, avvisi)
    date = mantieni_scadenze(scadenze_precedenti(precedente["id"]), riga, avvisi)
    if date:
        esito["mantenuti"].append(date)
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
    if "--id" in sys.argv:
        ids = ids_richiesti(sys.argv)
        if not ids:
            print("--id senza identificativo: nulla da fare.")
            return
        bandi, mancanti = da_riestrarre(ids)
        for id_bando in mancanti:
            print(f"  NON IN ARCHIVIO, saltato: {id_bando}")
    else:
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
