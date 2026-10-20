"""Ingestione di tutti i PDF in data/raw, ciascuno con i propri metadati."""

from src.config import RAW_DIR
from src.ingestion.pdf_ingest import (
    carica_pdf,
    salva_in_chroma,
)
from src.ingestion.testo import applica_metadati, spezza
from src.pgstore import salva_chunk_in_db

INTESTAZIONE_AVVISO = (
    r"AVVISO PUBBLICO\s*"
    r"per la presentazione delle Domande di finanziamento dei\s*"
    r"[\"“”]?Progetti di rafforzamento amministrativo[\"“”]?\s*"
    r"degli enti Capofila delle Aree interne,\s*"
    r"a supporto dell['’]attuazione delle Strategie d['’]area"
)

DOCUMENTI = [
    {
        "chiave": "Decreto n.9550",
        "intestazione": INTESTAZIONE_AVVISO,
        "salta_pagine": [2, 3],
        "metadati": {
            "titolo": (
                "Avviso pubblico - Progetti di rafforzamento amministrativo "
                "degli enti Capofila delle Aree interne"
            ),
            "tipo_documento": "avviso_pubblico",
            "livello": "regionale",
            "ente": "Regione Toscana",
            "riferimento_atto": "Decreto dirigenziale n. 9550 del 28/04/2026",
            "programma": "PR FESR Toscana 2021-2027 - Sub-Azione 5.2.1.5",
            "data_pubblicazione": "2026-04-28",
            "data_scadenza": "",
            "scadenza_note": (
                "Ore 12:00 del trentesimo giorno successivo alla pubblicazione "
                "sul BURT: data assoluta non indicata nel documento"
            ),
            "id_bando": "",
        },
    },
    {
        "chiave": "evoluzione-del-requisito-associativo",
        "intestazione": None,
        "salta_pagine": [],
        "metadati": {
            "titolo": (
                "Evoluzione del requisito associativo nella Strategia Nazionale "
                "per le Aree Interne - Linee Guida 2021-2027"
            ),
            "tipo_documento": "linee_guida",
            "livello": "nazionale",
            "ente": "Dipartimento per le politiche di coesione e per il Sud",
            "riferimento_atto": "Allegato 4 al PSNAI 2021-2027",
            "programma": "SNAI 2021-2027",
            "data_pubblicazione": "2025-03",
            "data_scadenza": "",
            "scadenza_note": "",
            "id_bando": "",
        },
    },
    {
        "chiave": "contributo-censis",
        "intestazione": None,
        "salta_pagine": [],
        "metadati": {
            "titolo": (
                "Supporto operativo alla Strategia delle Aree Interne - "
                "Individuazione e analisi di gruppi omogenei di territori e di "
                "politiche per il territorio per una meta lettura della SNAI"
            ),
            "tipo_documento": "studio",
            "livello": "nazionale",
            "ente": "CENSIS",
            "riferimento_atto": "",
            "programma": "SNAI",
            "data_pubblicazione": "2024-10",
            "data_scadenza": "",
            "scadenza_note": "",
            "id_bando": "",
        },
    },
    {
        "chiave": "PROGETTO_DEF_SNAI_C3",
        "intestazione": None,
        "salta_pagine": [],
        "metadati": {
            "titolo": (
                "Progetto C3.1 Ludoteche di montagna - Scheda C3.1.d "
                "Appennino Pistoiese"
            ),
            "tipo_documento": "progetto",
            "livello": "comunale",
            "ente": "Comune di Abetone Cutigliano",
            "riferimento_atto": "Deliberazione di Giunta n. 170 del 01/09/2026",
            "programma": (
                "APQ Area interna Garfagnana, Lunigiana, Media Valle del "
                "Serchio, Appennino Pistoiese - CUP D59I25001630001"
            ),
            "data_pubblicazione": "2026-09-02",
            "data_scadenza": "",
            "scadenza_note": "",
            "id_bando": "",
        },
    },
    {
        "chiave": "13287",
        "intestazione": None,
        "salta_pagine": [],
        "metadati": {
            "titolo": (
                "Avviso pubblico per manifestazione di interesse alla "
                "presentazione di progetti di investimento per la concessione "
                "di contributi a comuni su cui insistono mercati rionali"
            ),
            "tipo_documento": "avviso_pubblico",
            "livello": "regionale",
            "ente": "Regione Toscana",
            "riferimento_atto": "Decreto dirigenziale n. 13287 del 10/06/2026",
            "programma": "Contributi ai Comuni per i mercati rionali",
            "data_pubblicazione": "2026-06-25",
            "data_scadenza": "2026-09-15",
            "scadenza_note": (
                "Il testo riporta le ore 12:00 del 15/09/2026; la scadenza è "
                "stata poi prorogata alle ore 12:00 del 15/10/2026 con decreto "
                "20141 del 11/09/2026, non contenuto in questo documento"
            ),
            "id_bando": "mercati-rionali-2026",
        },
    },
]


def trova_file(chiave: str):
    """Cerca in data/raw il PDF il cui nome contiene la chiave."""
    candidati = [p for p in sorted(RAW_DIR.glob("*.pdf")) if chiave in p.name]

    if not candidati:
        return None
    if len(candidati) > 1:
        raise RuntimeError(f"Più di un PDF corrisponde a '{chiave}': {candidati}")

    return candidati[0]


def ingerisci(scheda: dict) -> bool:
    percorso = trova_file(scheda["chiave"])

    if percorso is None:
        print(f"\n[SALTATO] nessun PDF contiene '{scheda['chiave']}'")
        return False

    print(f"\n--- {percorso.name} ---")

    pagine = carica_pdf(percorso)
    chunk = spezza(
        pagine,
        intestazione=scheda["intestazione"],
        salta_pagine=scheda["salta_pagine"],
    )

    metadati = dict(scheda["metadati"])
    metadati["fonte"] = percorso.name

    chunk = applica_metadati(chunk, metadati)
    salva_in_chroma(chunk, fonte=percorso.name)
    salva_chunk_in_db(chunk)
    return True


def main() -> None:

    print(f"Documenti da ingerire: {len(DOCUMENTI)}")

    riusciti = sum(ingerisci(scheda) for scheda in DOCUMENTI)

    print(f"\nIngestione completata: {riusciti}/{len(DOCUMENTI)} documenti.")


if __name__ == "__main__":
    main()
