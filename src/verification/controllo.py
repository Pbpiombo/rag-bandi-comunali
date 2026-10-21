"""Verifica meccanica che i dati citati esistano nel frammento indicato."""

import re
from dataclasses import dataclass

from langchain_core.documents import Document

# Quanti caratteri dopo un dato cercare la sua citazione
FINESTRA_CITAZIONE = 600

# Il blocco di citazione, che puo' contenere parentesi annidate:
# (fonte: [2], Ente, Atto n. X del gg/mm/aaaa (nota), pag. N)
SCHEMA_CITAZIONE = r"\((?:[^()]|\([^()]*\))*fonte:(?:[^()]|\([^()]*\))*\)"
SCHEMA_ATTO = (
    r"(?:decreto|deliberazione|delibera|avviso)"
    r"(?:\s+\w+|\s+n\.?|\s+del|\s+\d+|\s*,)*"
    r"\s*\d{1,2}/\d{1,2}/\d{4}"
)

# Un riferimento sciolto a un frammento: [3], [D1]
SCHEMA_RIFERIMENTO = r"\[D?\d+\]"

MESI = (
    "gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|"
    "agosto|settembre|ottobre|novembre|dicembre"
)

SCHEMI = {
    "importo": [
        r"\b([\d.]+,\d{1,2})\s*€",
        r"€\s*([\d.]+(?:,\d{1,2})?)",
        r"\b([\d.]+,\d{2})\s*euro\b",
    ],
    "percentuale": [
        r"\b(\d+(?:[.,]\d+)?)\s*(?:%|per\s*cento)",
    ],
    "data": [
        r"\b(\d{4}-\d{2}-\d{2})\b",
        r"\b(\d{1,2}:\d{2})\b",
        rf"\b(\d{{1,2}}\s+(?:{MESI})(?:\s+\d{{4}})?)\b",
        r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
        r"\b(\d{1,2}-\d{1,2}-\d{4})\b",
        r"\b(\d{1,2}/\d{1,2})(?!/)\b",
    ],
    "codice": [
        r"\b([A-Z]\d{2}[A-Z]\d{10,12})\b",
        r"\b(\d{8}-\d)\b",
    ],
    "riferimento": [
        r"\bn\.?\s*(\d+/\d{4})\b",
        r"\bart\.?\s*(\d+(?:\s*,\s*comma\s*\d+)?)",
        r"\b(?:par\.?|paragrafo|punto|lett\.?)\s*(\d+)\b",
        r"\b(\d{1,4}/\d{4})\b",
    ],
    "periodo": [
        r"\b(19\d{2}|20\d{2})\s*[-\u2013/]\s*(?:19\d{2}|20\d{2})\b",
    ],
    "anno": [
        r"(?<![\d.,/-])(19\d{2}|20\d{2})(?![\d.,/-])",
    ],
    "orario": [
        r"\bore\s+(\d{1,2}(?:[:.]\d{2})?)",
    ],
    "quantita": [
        r"\b(\d+,\d{1,2})\b",
        r"\b(\d{1,3}(?:\.\d{3})+)\b",
        r"\b(\d{2,})\b",
    ],
}


@dataclass
class Esito:
    """Il risultato della verifica di un singolo dato."""

    tipo: str
    valore: str
    frammenti: list[str]
    stato: str  # verificato | non_trovato | non_citato
    dettaglio: str = ""
    contesto: str = ""


def normalizza(testo: str) -> str:
    """Riduce il testo a una forma confrontabile.

    Toglie gli spazi, elimina i separatori delle migliaia e uniforma il
    separatore decimale, cosi' che '€ 19.570,00', '19570.00' e
    '19570,00' risultino uguali, e '9.2%' corrisponda a '9,2%'.
    """
    testo = testo.lower().replace("\u00a0", " ")

    # I separatori delle migliaia vanno tolti PRIMA di eliminare gli spazi:
    # dopo, la sequenza '25.000 a' diventa '25.000a' e il confine di parola
    # dopo le tre cifre non esiste piu'.
    testo = re.sub(r"(?<=\d)\.(?=\d{3}(?!\d))", "", testo)
    testo = re.sub(r"(?<=\d)[.,](?=\d)", ".", testo)

    return re.sub(r"\s+", "", testo)


def maschera_citazioni(risposta: str) -> str:
    """Sostituisce citazioni, riferimenti ad atti e rimandi ai frammenti."""

    def a_spazi(m):
        return " " * len(m.group(0))

    risposta = re.sub(
        SCHEMA_CITAZIONE, a_spazi, risposta, flags=re.DOTALL | re.IGNORECASE
    )
    risposta = re.sub(SCHEMA_ATTO, a_spazi, risposta, flags=re.IGNORECASE)
    return re.sub(SCHEMA_RIFERIMENTO, a_spazi, risposta)


def trova_citazioni(risposta: str) -> list[tuple[int, str]]:
    """Restituisce coppie (posizione, etichetta del frammento).

    L'etichetta e' '3' per un frammento documentale, 'D1' per un dato
    numerico proveniente dall'archivio statistico.
    """
    return [
        (m.start(), m.group(1).upper())
        for m in re.finditer(r"fonte:\s*\[(D?\d+)\]", risposta, re.IGNORECASE)
    ]


def trova_dati(risposta: str) -> list[tuple[str, str, int]]:
    """Restituisce terne (tipo, valore, posizione) di ogni dato citabile.

    Gli schemi sono provati in ordine: una porzione di testo gia' catturata
    da uno schema precedente non viene riconsiderata. Cosi' '28/04/2026'
    resta una data e non produce anche un finto riferimento '04/2026'.
    """
    trovati = []
    occupati = []

    def si_sovrappone(inizio: int, fine: int) -> bool:
        return any(inizio < f and i < fine for i, f in occupati)

    for tipo, schemi in SCHEMI.items():
        for schema in schemi:
            for m in re.finditer(schema, risposta, re.IGNORECASE):
                if si_sovrappone(m.start(), m.end()):
                    continue

                occupati.append((m.start(), m.end()))
                trovati.append((tipo, m.group(1).strip(), m.start()))

    return sorted(trovati, key=lambda t: t[2])


def frammenti_citati(posizione: int, citazioni: list[tuple[int, str]]) -> list[str]:
    """I frammenti citati dopo un dato, entro il paragrafo.

    Restituisce il gruppo di citazioni piu' vicino, cosi' un dato seguito
    da altro testo prima della fonte viene comunque associato.
    """
    successive = [c for c in citazioni if c[0] > posizione]

    if not successive:
        return []

    prima = successive[0][0]

    if prima - posizione > FINESTRA_CITAZIONE:
        return []

    etichette = [etichetta for pos, etichetta in successive if pos <= prima + 200]
    return list(dict.fromkeys(etichette))


def contesto_di(testo: str, posizione: int, ampiezza: int = 40) -> str:
    """Il testo intorno a un dato, per rendere leggibile la riga di verifica."""
    inizio = max(0, posizione - ampiezza)
    fine = posizione + ampiezza
    return " ".join(testo[inizio:fine].split())


def verifica(
    risposta: str,
    documenti: list[Document],
    esiti_dati: list | None = None,
) -> list[Esito]:
    """Controlla che ogni dato della risposta esista nella fonte citata.

    I frammenti documentali sono etichettati '1', '2', ...; i dati
    numerici dell'archivio statistico 'D1', 'D2', ...
    """
    testi = {
        str(numero): normalizza(doc.page_content)
        for numero, doc in enumerate(documenti, start=1)
    }

    for numero, (_, risultato) in enumerate(esiti_dati or [], start=1):
        testi[f"D{numero}"] = normalizza(risultato.testo)

    citazioni = trova_citazioni(risposta)
    mascherata = maschera_citazioni(risposta)
    esiti = []

    for tipo, valore, posizione in trova_dati(mascherata):
        etichette = frammenti_citati(posizione, citazioni)
        contesto = contesto_di(risposta, posizione)

        if not etichette:
            esiti.append(Esito(tipo, valore, [], "non_citato", contesto=contesto))
            continue

        ago = normalizza(valore)
        varianti = {ago, re.sub(r"\.00$", "", ago)}
        dentro = [
            e for e in etichette if e in testi and any(v in testi[e] for v in varianti)
        ]

        if dentro:
            esiti.append(Esito(tipo, valore, dentro, "verificato", contesto=contesto))
        else:
            altrove = [e for e, t in testi.items() if any(v in t for v in varianti)]
            dettaglio = (
                f"presente invece in {altrove}"
                if altrove
                else "non presente in nessuna fonte recuperata"
            )
            esiti.append(
                Esito(tipo, valore, etichette, "non_trovato", dettaglio, contesto)
            )

    return esiti


def riassumi(esiti: list[Esito]) -> dict:
    """Conta gli esiti per stato."""
    conteggio = {"verificato": 0, "non_trovato": 0, "non_citato": 0}
    for e in esiti:
        conteggio[e.stato] += 1
    return conteggio
