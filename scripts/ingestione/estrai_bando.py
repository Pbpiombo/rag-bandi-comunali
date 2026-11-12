"""Estrae i campi di un bando e li salva nel database dopo conferma.

Uso:
    python -m scripts.ingestione.estrai_bando URL identificativo
    python -m scripts.ingestione.estrai_bando percorso/testo.txt URL identificativo

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
from src.estrazione.elenco import CODICE_FONTE
from src.estrazione.pagina import prendi
from src.estrazione.salva import ConflittoBando, conflitto, esiste, salva

SEGNI = {"alta": "  ", "media": "~ ", "bassa": "! "}
FONTE = "Portale bandi Regione Toscana"

# Le tabelle che un salvataggio modifica, da riversare nei CSV
TABELLE_BANDO = ("bandi", "beneficiari_bando", "interventi_bando", "scadenze_bando")


def mostra(estrazione) -> None:
    """Stampa cio' che il modello ha estratto, prima della verifica."""
    print("=" * 74)
    print(f"NATURA: {estrazione.natura}  {estrazione.natura_motivo}")
    print("=" * 74)
    print("CAMPI ESTRATTI")
    print("=" * 74)

    for c in estrazione.campi:
        marca = "CRITICO" if c.critico else "       "
        valore = c.valore if c.valore is not None else "(vuoto)"
        print(f"{SEGNI[c.confidenza]}{marca} {c.nome:20} {valore}")
        if c.prova and (c.critico or c.confidenza != "alta"):
            print(f"                            prova: {c.prova}")

    print("\nBENEFICIARI AMMESSI")
    for b in estrazione.beneficiari:
        if not isinstance(b, dict):
            print(f"  (formato non conforme) {b}")
            continue
        tipi = ", ".join(map(str, b.get("tipi") or []))
        print(f"  - {b.get('soggetto')}  ->  {tipi}  [{b.get('confidenza')}]")
        if b.get("condizioni"):
            print(f"      condizioni: {b['condizioni']}")
        print(f"      frase: {b.get('frase')}")

    print("\nINTERVENTI E SPESE")
    for i in estrazione.interventi:
        if isinstance(i, dict):
            print(f"  - [{i.get('genere')}] {i.get('descrizione')}")

    clausola = (estrazione.cumulabilita or {}).get("clausola")
    print(f"\nCUMULABILITA': {clausola or '(non indicata)'}")

    print("\nSCADENZE MULTIPLE")
    if not estrazione.scadenze:
        print("  nessuna (una sola data)")
    for s in estrazione.scadenze:
        if not isinstance(s, dict):
            print(f"  (formato non conforme) {s}")
            continue
        periodo = (
            f"dal {s.get('apertura')} al {s.get('scadenza')}"
            if s.get("apertura")
            else f"entro il {s.get('scadenza')}"
        )
        print(f"  - [{s.get('genere')}] {s.get('descrizione')}: {periodo}")
        print(f"      frase: {s.get('frase')}")


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
            "a_sportello",
            "pubblicato_il",
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
        print("Uso: python -m scripts.ingestione.estrai_bando URL identificativo")
        print(
            "     python -m scripts.ingestione.estrai_bando testo.txt URL identificativo"
        )
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
        print(
            "Uso: python -m scripts.ingestione.estrai_bando testo.txt URL identificativo"
        )
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
    estrazione = estrai(estrattore, testo, debug="--debug" in sys.argv)

    mostra(estrazione)

    riga, problemi, avvisi = valida(estrazione, testo)

    if avvisi:
        print("\nAVVISI: campi e voci lasciati vuoti, da completare a mano se serve")
        for a in avvisi:
            print(f"  - {a}")

    if riga["natura"] == "non_bando":
        print(f"\nNon e' un bando ({riga['natura_motivo']}). Non salvo.")
        return

    if problemi:
        print("\nPROBLEMI DI VALIDAZIONE")
        for p in problemi:
            print(f"  - {p}")
        print(
            "\nNon salvo. Correggi il testo della pagina oppure "
            "inserisci la riga a mano."
        )
        return

    rivedere = da_rivedere(estrazione.campi)
    print(f"\n{len(rivedere)} campi da confermare su {len(estrazione.campi)}.")

    riga["id"] = id_bando

    problema = conflitto(id_bando, url)
    if problema:
        print(f"\nNon salvo: {problema}")
        print("Scegli un altro identificativo, o correggi la riga in archivio.")
        return

    if "--auto" in sys.argv:
        salvare, motivo = decidi_automatico(estrazione, riga)

        if salvare:
            salva(riga, url, FONTE, CODICE_FONTE)
            aggiorna_csv(*TABELLE_BANDO)
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

    try:
        salva(riga, url, FONTE, CODICE_FONTE)
    except ConflittoBando as errore:
        print(errore)
        return

    aggiorna_csv(*TABELLE_BANDO)
    print(f"Salvato: {riga['id']}")


if __name__ == "__main__":
    main()
