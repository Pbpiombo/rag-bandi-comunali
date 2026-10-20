"""STEP 1 - ingestione del primo PDF di test."""

from src.config import RAW_DIR
from src.ingestion.pdf_ingest import (
    carica_pdf,
    salva_in_chroma,
)
from src.ingestion.testo import applica_metadati, spezza

INTESTAZIONE = (
    r"AVVISO PUBBLICO\s*"
    r"per la presentazione delle Domande di finanziamento dei\s*"
    r"[\"“”]?Progetti di rafforzamento amministrativo[\"“”]?\s*"
    r"degli enti Capofila delle Aree interne,\s*"
    r"a supporto dell['’]attuazione delle Strategie d['’]area"
)

SALTA_PAGINE = [2, 3]

METADATI = {
    "titolo": (
        "Avviso pubblico - Progetti di rafforzamento amministrativo "
        "degli enti Capofila delle Aree interne"
    ),
    "tipo_documento": "avviso_pubblico",
    "ente": "Regione Toscana",
    "riferimento_atto": "Decreto dirigenziale n. 9550 del 28/04/2026",
    "programma": "PR FESR Toscana 2021-2027 - Sub-Azione 5.2.1.5",
    "data_pubblicazione": "2026-04-28",
    "data_scadenza": "",
    "scadenza_note": (
        "Ore 12:00 del trentesimo giorno successivo alla pubblicazione sul BURT: "
        "data assoluta non indicata nel documento"
    ),
}


def main() -> None:

    pdf_presenti = sorted(RAW_DIR.glob("*.pdf"))

    if not pdf_presenti:
        raise FileNotFoundError(f"Nessun PDF trovato in {RAW_DIR}")

    if len(pdf_presenti) > 1:
        print("  PDF presenti nella cartella:")
        for p in pdf_presenti:
            print(f"    - {p.name}")
        raise RuntimeError("Più di un PDF in data/raw: tienine uno solo per ora.")

    percorso = pdf_presenti[0]

    print(f"\n[1/4] Caricamento: {percorso.name}")
    pagine = carica_pdf(percorso)

    print("[2/4] Suddivisione in chunk")
    chunk = spezza(pagine, intestazione=INTESTAZIONE, salta_pagine=SALTA_PAGINE)

    print("[3/4] Applicazione metadati")
    METADATI["fonte"] = percorso.name
    chunk = applica_metadati(chunk, METADATI)

    print("[4/4] Calcolo embedding e scrittura")
    salva_in_chroma(chunk, fonte=percorso.name)

    print("\nIngestione completata.")


if __name__ == "__main__":
    main()
