"""Confronta le risposte della catena con Chroma e con Postgres."""

from src.chains.rag import costruisci_catena
from src.config import ENTE_PREDEFINITO
from src.pgstore import RecuperoPostgres
from src.verification.controllo import riassumi, verifica

DOMANDE = [
    "Qual è il costo massimo giornaliero per un incarico professionale?",
    "Quali enti sono beneficiari del sostegno?",
]


def main():
    # Esegue il confronto tra le due catene

    catene = {
        "chroma": costruisci_catena(ENTE_PREDEFINITO),
        "postgres": costruisci_catena(ENTE_PREDEFINITO, recupero=RecuperoPostgres()),
    }

    for domanda in DOMANDE:
        print(f"\n{'=' * 70}\n>>> {domanda}\n{'=' * 70}")

        for nome, catena in catene.items():
            esito = catena.invoke(domanda)
            esiti = verifica(esito["risposta"], esito["documenti"], esito["esiti_dati"])
            print(f"\n--- {nome} ---")
            print(esito["risposta"])
            print(riassumi(esiti))


if __name__ == "__main__":
    main()
