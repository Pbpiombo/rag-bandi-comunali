"""Verifica meccanica che i dati citati esistano nel frammento indicato."""

import re
from dataclasses import dataclass

from langchain_core.documents import Document

from src.database.modelli import senza_segnaposto

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

# Un riferimento sciolto a un frammento: [3], [D1], [D1.2]
SCHEMA_RIFERIMENTO = r"\[D?\d+(?:\.\d+)?\]"

# L'etichetta di un frammento in una citazione: 3, D1, o D1.2 per il
# secondo bando del blocco D1
ETICHETTA = r"D?\d+(?:\.\d+)?"
ETICHETTA_BANDO = re.compile(r"^D\d+\.\d+$")

MESI = (
    "gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|"
    "agosto|settembre|ottobre|novembre|dicembre"
)

# Il numero di un decreto o di una delibera in una citazione: "decreto
# dirigenziale n. 18191 del 7/8/2026" -> 18191, "DGR 1081/2026" -> 1081.
# Non e' un numero d'atto quello di una data: "decreto del 29 ottobre",
# "decreto 12/10/2026".
SCHEMA_NUMERO_ATTO = re.compile(
    r"(?:\b(?:decreto|delibera|deliberazione|dgr|dd)\b|d\.g\.r\.|d\.d\.)"
    r"(?P<mezzo>[^\d()\[\]]{0,40}?)"
    rf"(?P<numero>\d{{2,6}})(?:/\d{{4}})?(?![\d/])(?!\s+(?:{MESI}))",
    re.IGNORECASE,
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
    # verificato | non_trovato | non_citato | citazione_generica (un dato
    # di un solo bando citato con il blocco [Dn] invece che con [Dn.k])
    stato: str
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
    numerico proveniente dall'archivio statistico, 'D1.2' per il secondo
    bando del blocco D1.
    """
    return [
        (m.start(), m.group(1).upper())
        for m in re.finditer(rf"fonte:\s*\[({ETICHETTA})\]", risposta, re.IGNORECASE)
    ]


def numeri_atto(citazione: str) -> list[str]:
    """I numeri di decreto o delibera scritti in una citazione."""
    numeri = []
    for m in SCHEMA_NUMERO_ATTO.finditer(citazione):
        # "decreto del 12 ..." o "decreto dell'11 ...": e' una data
        if re.search(r"\bdel(?:l')?\s*$", m.group("mezzo"), re.IGNORECASE):
            continue
        numeri.append(m.group("numero"))
    return list(dict.fromkeys(numeri))


def contiene_numero(testo_normalizzato: str, numero: str) -> bool:
    """Il numero compare nel testo come numero intero, non dentro un altro."""
    return re.search(rf"(?<!\d){numero}(?!\d)", testo_normalizzato) is not None


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
    numerici dell'archivio statistico 'D1', 'D2', ...; il bando k del
    blocco Dn, se il risultato elenca bandi, 'Dn.k'.

    Il testo di confronto di Dn e' il blocco intero con le sue fonti;
    quello di Dn.k e' la riga del bando con la fonte di quel bando.
    Per una citazione a Dn.k si controllano anche i numeri di decreto o
    delibera scritti nella citazione: devono comparire nella riga del bando.
    """
    testi = {
        str(numero): normalizza(doc.page_content)
        for numero, doc in enumerate(documenti, start=1)
    }
    # Per ogni blocco Dn, le etichette dei suoi bandi
    voci_di: dict[str, list[str]] = {}

    for numero, (_, risultato) in enumerate(esiti_dati or [], start=1):
        blocco = f"D{numero}"
        fonti = " ".join(getattr(risultato, "fonti", None) or [])
        testi[blocco] = normalizza(f"{senza_segnaposto(risultato.testo)} {fonti}")
        voci_di[blocco] = []
        for k, voce in enumerate(getattr(risultato, "voci", None) or [], start=1):
            testi[f"{blocco}.{k}"] = normalizza(f"{voce.testo} {voce.fonte}")
            voci_di[blocco].append(f"{blocco}.{k}")

    def voci_con(varianti: set[str]) -> list[str]:
        """Le etichette dei bandi la cui riga contiene il dato."""
        return [
            e
            for e, t in testi.items()
            if ETICHETTA_BANDO.match(e) and any(v in t for v in varianti)
        ]

    citazioni = trova_citazioni(risposta)
    mascherata = maschera_citazioni(risposta)
    esiti: list[tuple[int, Esito]] = []

    for tipo, valore, posizione in trova_dati(mascherata):
        etichette = frammenti_citati(posizione, citazioni)
        contesto = contesto_di(risposta, posizione)

        if not etichette:
            esiti.append(
                (posizione, Esito(tipo, valore, [], "non_citato", contesto=contesto))
            )
            continue

        ago = normalizza(valore)
        varianti = {ago, re.sub(r"\.00$", "", ago)}
        dentro = [
            e for e in etichette if e in testi and any(v in testi[e] for v in varianti)
        ]

        if dentro:
            esiti.append(
                (
                    posizione,
                    _esito_trovato(
                        tipo, valore, dentro, voci_di, voci_con(varianti), contesto
                    ),
                )
            )
        else:
            # Se il dato e' nella riga di un bando, si indica il bando e non
            # anche il blocco che lo contiene
            bandi = voci_con(varianti)
            altrove = bandi or [
                e for e, t in testi.items() if any(v in t for v in varianti)
            ]
            dettaglio = (
                f"presente invece in {altrove}"
                if altrove
                else "non presente in nessuna fonte recuperata"
            )
            esiti.append(
                (
                    posizione,
                    Esito(tipo, valore, etichette, "non_trovato", dettaglio, contesto),
                )
            )

    esiti.extend(_verifica_atti(risposta, testi))
    return [e for _, e in sorted(esiti, key=lambda coppia: coppia[0])]


def _esito_trovato(
    tipo: str,
    valore: str,
    dentro: list[str],
    voci_di: dict[str, list[str]],
    bandi: list[str],
    contesto: str,
) -> Esito:
    """L'esito di un dato trovato nei frammenti citati.

    Se e' citato solo con blocchi di bandi [Dn] e compare nella riga di un
    solo bando, la citazione e' generica: il dato andava citato con
    l'etichetta di quel bando. Gli anni non contano: compaiono nei titoli.
    """
    blocchi = [e for e in dentro if voci_di.get(e)]
    if tipo != "anno" and blocchi and len(blocchi) == len(dentro):
        nei_blocchi = [b for b in bandi if b.rsplit(".", 1)[0] in blocchi]
        if len(nei_blocchi) == 1:
            return Esito(
                tipo,
                valore,
                dentro,
                "citazione_generica",
                f"presente solo nel bando [{nei_blocchi[0]}]: va citato con "
                "la sua etichetta",
                contesto,
            )
    return Esito(tipo, valore, dentro, "verificato", contesto=contesto)


def _verifica_atti(risposta: str, testi: dict[str, str]) -> list[tuple[int, Esito]]:
    """Controlla i numeri di decreto o delibera nelle citazioni dei bandi.

    In una citazione a [Dn.k] ogni numero d'atto deve comparire nella riga
    di quel bando; se compare nella riga di un altro bando, lo si indica.
    """
    esiti = []
    for m in re.finditer(SCHEMA_CITAZIONE, risposta, re.DOTALL | re.IGNORECASE):
        citazione = m.group(0)
        etichette = [
            e.upper()
            for e in re.findall(rf"\[({ETICHETTA})\]", citazione, re.IGNORECASE)
        ]
        bandi = [e for e in etichette if ETICHETTA_BANDO.match(e)]
        if not bandi:
            continue

        senza_etichette = re.sub(SCHEMA_RIFERIMENTO, " ", citazione)
        contesto = " ".join(citazione.split())
        for numero in numeri_atto(senza_etichette):
            dentro = [
                e for e in bandi if e in testi and contiene_numero(testi[e], numero)
            ]
            if dentro:
                esiti.append(
                    (
                        m.start(),
                        Esito("atto", numero, dentro, "verificato", "", contesto),
                    )
                )
                continue

            altrove = [
                e
                for e, t in testi.items()
                if ETICHETTA_BANDO.match(e) and contiene_numero(t, numero)
            ]
            dettaglio = (
                f"presente invece in {altrove}"
                if altrove
                else "non presente nella riga del bando citato"
            )
            esiti.append(
                (
                    m.start(),
                    Esito("atto", numero, bandi, "non_trovato", dettaglio, contesto),
                )
            )
    return esiti


def riassumi(esiti: list[Esito]) -> dict:
    """Conta gli esiti per stato.

    I tre stati di base ci sono sempre; citazione_generica solo quando
    compare, cosi' le risposte senza elenchi di bandi si riassumono come
    prima.
    """
    conteggio = {"verificato": 0, "non_trovato": 0, "non_citato": 0}
    for e in esiti:
        conteggio[e.stato] = conteggio.get(e.stato, 0) + 1
    return conteggio
