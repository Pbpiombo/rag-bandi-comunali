"""Estrae i campi di un bando e li salva nel database dopo conferma.

Uso:
    python -m scripts.estrai_bando URL identificativo
    python -m scripts.estrai_bando percorso/testo.txt URL identificativo

Nella prima forma la pagina viene scaricata; nella seconda si parte da un
testo gia' salvato, utile per rileggere una pagina senza riscaricarla.

L'identificativo e' una convenzione nostra, non un dato del documento:
va sempre indicato, ed e' cio' che distingue un bando nuovo da un
aggiornamento di uno gia' in archivio.

Opzioni:
    --debug         stampa il JSON grezzo restituito dal modello
    --salva-testo   salva in data/processed il testo estratto dalla pagina
    --auto          salva senza chiedere conferma, applicando la soglia
"""

import sys
from pathlib import Path

from src.config import PROCESSED_DIR
from src.database.schema import aggiorna_csv
from src.estrazione.bandi import (
    costruisci_estrattore,
    da_rivedere,
    decidi_automatico,
    estrai,
    valida,
)
from src.estrazione.pagina import prendi
from src.estrazione.salva import esiste, salva

SEGNI = {"alta": "  ", "media": "~ ", "bassa": "! "}
FONTE = "Portale bandi Regione Toscana"


def mostra(campi) -> None:
    """Stampa i campi estratti, con la prova per quelli da verificare."""
    print("=" * 74)
    print("CAMPI ESTRATTI")
    print("=" * 74)

    for c in campi:
        marca = "CRITICO" if c.critico else "       "
        valore = c.valore if c.valore is not None else "(vuoto)"
        print(f"{SEGNI[c.confidenza]}{marca} {c.nome:20} {valore}")
        if c.prova and (c.critico or c.confidenza != "alta"):
            print(f"                            prova: {c.prova}")


def mostra_confronto(precedente: dict, riga: dict) -> None:
    """Evidenzia le differenze rispetto alla riga gia' in archivio."""
    print(
        f"\nATTENZIONE: '{riga['id']}' esiste gia' in archivio "
        f"(verificato il {precedente['verificato_il']})."
    )

    cambiati = [
        (c, precedente.get(c), riga.get(c))
        for c in (
            "scadenza",
            "ammette_comuni",
            "a_sportello",
            "contributo_perc",
            "dotazione",
        )
        if str(precedente.get(c)) != str(riga.get(c))
    ]

    if not cambiati:
        print("  Nessuna differenza sui campi principali.")
        return

    print("  Differenze:")
    for nome, prima, dopo in cambiati:
        print(f"    {nome}: {prima}  ->  {dopo}")

    perdite = [n for n, prima, dopo in cambiati if prima and not dopo]
    if perdite:
        print(f"  ATTENZIONE: salvando perderesti {', '.join(perdite)}")


def conferma(domanda: str) -> bool:
    """Chiede conferma esplicita. Tutto cio' che non e' si vale no."""
    risposta = input(f"\n{domanda} [s/N] ").strip().lower()
    return risposta in ("s", "si", "sì")


def leggi_argomenti() -> tuple[str, str, str] | None:
    """Restituisce (testo, url, identificativo), oppure None se mancano."""
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not argomenti:
        print("Uso: python -m scripts.estrai_bando URL identificativo")
        print("     python -m scripts.estrai_bando testo.txt URL identificativo")
        return None

    if argomenti[0].startswith("http"):
        if len(argomenti) < 2:
            print("Serve l'identificativo del bando.")
            return None

        url, id_bando = argomenti[0], argomenti[1]

        print(f"Scarico: {url}")
        testo = prendi(url)

        if "--salva-testo" in sys.argv:
            percorso = PROCESSED_DIR / f"pagina_{id_bando}.txt"
            percorso.write_text(testo, encoding="utf-8")
            print(f"Testo salvato in {percorso}")

        return testo, url, id_bando

    if len(argomenti) < 3:
        print("Uso: python -m scripts.estrai_bando testo.txt URL identificativo")
        return None

    percorso = Path(argomenti[0])

    if not percorso.exists():
        print(f"File non trovato: {percorso}")
        return None

    return percorso.read_text(encoding="utf-8"), argomenti[1], argomenti[2]


def main() -> None:
    letti = leggi_argomenti()
    if letti is None:
        return

    testo, url, id_bando = letti
    print(f"Testo utile: {len(testo)} caratteri\n")

    estrattore = costruisci_estrattore()
    campi = estrai(estrattore, testo, debug="--debug" in sys.argv)

    mostra(campi)

    riga, problemi = valida(campi)

    if problemi:
        print("\nPROBLEMI DI VALIDAZIONE")
        for p in problemi:
            print(f"  - {p}")
        print(
            "\nNon salvo. Correggi il testo della pagina oppure "
            "inserisci la riga a mano."
        )
        return

    rivedere = da_rivedere(campi)
    print(f"\n{len(rivedere)} campi da confermare su {len(campi)}.")

    riga["id"] = id_bando

    if "--auto" in sys.argv:
        salvare, motivo = decidi_automatico(campi, riga)

        if salvare:
            salva(riga, url, FONTE)
            aggiorna_csv("bandi")
            print(f"\nSALVATO: {id_bando} ({motivo})")
        else:
            print(f"\nSCARTATO: {id_bando} ({motivo})")
        return

    precedente = esiste(riga["id"])
    if precedente:
        mostra_confronto(precedente, riga)

    if not conferma("Salvare nel database?"):
        print("Non salvato.")
        return

    salva(riga, url, FONTE)
    aggiorna_csv("bandi")
    print(f"Salvato: {riga['id']}")


if __name__ == "__main__":
    main()
