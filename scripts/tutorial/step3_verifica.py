"""STEP 3+4 - risposta con routing, dati numerici e verifica automatica."""

import sys

from src.chains.rag import costruisci_catena
from src.config import ENTE_PREDEFINITO
from src.verification.controllo import riassumi, verifica

SIMBOLI = {
    "verificato": "OK ",
    "non_trovato": "!! ",
    "non_citato": "?  ",
}

DOMANDE = [
    "Qual è il costo massimo giornaliero per un incarico professionale?",
    "Quanti abitanti ha il Comune di Abetone Cutigliano?",
    "Il calo demografico giustifica la richiesta di fondi per le aree interne?",
    "Qual è il bilancio comunale del 2025?",
]


def mostra(esito_catena: dict) -> None:
    print(f"\n{'=' * 74}")
    print(f">>> {esito_catena['domanda']}")
    print("=" * 74)

    decisione = esito_catena["decisione"]
    nomi = [i.get("nome") for i in decisione.get("interrogazioni", [])]

    print(
        f"\nROUTER  documenti: {decisione['documenti']}  "
        f"interrogazioni: {nomi or 'nessuna'}"
    )
    print(f"        frammenti recuperati: {len(esito_catena['documenti'])}")

    if "errore" in decisione:
        print(f"        ANOMALIA: {decisione['errore']}")

    print("\nRISPOSTA")
    print(esito_catena["risposta"])

    esiti = verifica(
        esito_catena["risposta"],
        esito_catena["documenti"],
        esito_catena.get("esiti_dati"),
    )

    print("\nVERIFICA DEI DATI CITATI")

    if not esiti:
        print("  Nessun dato numerico o normativo da verificare.")
        return

    for e in esiti:
        if e.tipo == "anno" and e.stato == "verificato":
            continue

        riga = f"  {SIMBOLI[e.stato]}{e.tipo:12} {e.valore:28}"
        if e.frammenti:
            riga += f" frammenti {e.frammenti}"
        print(riga)
        if e.dettaglio:
            print(f"       -> {e.dettaglio}")

    conteggio = riassumi(esiti)
    print(
        f"\n  Verificati: {conteggio['verificato']}  "
        f"Non trovati: {conteggio['non_trovato']}  "
        f"Non citati: {conteggio['non_citato']}"
    )


def main() -> None:
    catena = costruisci_catena(ENTE_PREDEFINITO)
    domande = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else DOMANDE

    for domanda in domande:
        mostra(catena.invoke(domanda))

    print(f"\n{'=' * 74}")


if __name__ == "__main__":
    main()
