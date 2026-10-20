"""STEP 2 - interrogazione con citazione delle fonti."""

import sys

from src.chains.rag import costruisci_catena

DOMANDE = [
    "Qual è il costo massimo giornaliero per un incarico professionale?",
    "Qual è il costo totale del progetto Ludoteche di montagna?",
    "Entro quando va presentata la relazione annuale sullo stato di "
    "avanzamento della Strategia d'area?",
    "Il Comune di Abetone Cutigliano può presentare domanda sull'avviso "
    "per il rafforzamento amministrativo?",
    "Quanti abitanti ha il Comune di Abetone Cutigliano?",
]


def mostra(esito: dict) -> None:
    print(f"\n{'=' * 74}")
    print(f">>> {esito['domanda']}")
    print("=" * 74)

    print("\nFRAMMENTI RECUPERATI")
    for numero, (documento, origine) in enumerate(
        zip(esito["documenti"], esito["origini"], strict=True), start=1
    ):
        meta = documento.metadata
        print(
            f"  [{numero}] {meta.get('ente')} "
            f"| {meta.get('tipo_documento')} | pag. {meta.get('page')} "
            f"| {', '.join(origine)}"
        )

    print("\nRISPOSTA")
    print(esito["risposta"])


def main() -> None:
    catena = costruisci_catena()

    domande = [" ".join(sys.argv[1:])] if len(sys.argv) > 1 else DOMANDE

    for domanda in domande:
        mostra(catena.invoke(domanda))

    print(f"\n{'=' * 74}")


if __name__ == "__main__":
    main()
