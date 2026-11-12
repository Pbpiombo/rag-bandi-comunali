"""Verifica meccanica che i dati citati esistano nel frammento indicato.

Il confronto e' sui valori, non sul testo: ogni dato della risposta e ogni
fonte si riducono a valori (src/normalizzazione.py), e un dato e' verificato
se il suo valore compare per intero tra quelli della fonte, nella famiglia
giusta. Cosi' "8%" non si conferma con "80%", "€ 50.000" con "€ 150.000",
il 3 novembre con il 13 novembre; e "31/07/2027" si conferma con
"2027-07-31".
"""

import re
from dataclasses import dataclass

from langchain_core.documents import Document

from src.database.modelli import SEGNAPOSTO, senza_segnaposto
from src.normalizzazione import (
    MESI,
    Valori,
    articolo,
    atti_con_data,
    data,
    giorno_mese,
    numero,
    orario,
    periodo,
    riferimento,
    valori,
)

# Quanti caratteri dopo un dato cercare la sua citazione
FINESTRA_CITAZIONE = 600

# Il blocco di citazione, che puo' contenere parentesi annidate:
# (fonte: [2], Ente, Atto n. X del gg/mm/aaaa (nota), pag. N)
SCHEMA_CITAZIONE = r"\((?:[^()]|\([^()]*\))*fonte:(?:[^()]|\([^()]*\))*\)"

# Un riferimento sciolto a un frammento: [3], [D1], [D1.2]
SCHEMA_RIFERIMENTO = r"\[D?\d+(?:\.\d+)?\]"

# L'etichetta di un frammento in una citazione: 3, D1, o D1.2 per il
# secondo bando del blocco D1
ETICHETTA = r"D?\d+(?:\.\d+)?"
ETICHETTA_BANDO = re.compile(r"^D\d+\.\d+$")

_MESI = "|".join(MESI)
_MOLTIPLICATORE = r"mila|milion[ei]|mln|miliard[oi]"

# Il numero di un decreto o di una delibera in una citazione: "decreto
# dirigenziale n. 18191 del 7/8/2026" -> 18191, "DGR 1081/2026" -> 1081.
# Non e' un numero d'atto quello di una data: "decreto del 29 ottobre",
# "decreto 12/10/2026".
SCHEMA_NUMERO_ATTO = re.compile(
    r"(?:\b(?:decreto|delibera|deliberazione|dgr|dd)\b|d\.g\.r\.|d\.d\.)"
    r"(?P<mezzo>[^\d()\[\]]{0,40}?)"
    rf"(?P<numero>\d{{2,6}})(?:/\d{{4}})?(?![\d/])(?!\s+(?:{_MESI}))",
    re.IGNORECASE,
)

# Un atto nel testo della risposta, fuori dalle citazioni: "decreto
# dirigenziale n. 9550 del 28/04/2026" -> 9550, "DGR 1081/2026" -> 1081.
# Piu' stretto di SCHEMA_NUMERO_ATTO: tra la parola e il numero solo
# qualificazioni e "n.", cosi' "il decreto prevede € 322,00" non e' l'atto
# 322. La data dell'atto si controlla insieme al numero: deve comparire con
# quel numero, nella fonte in cui il numero e' stato trovato.
_QUALIFICA = (
    r"dirigenziale|regionale|di\s+giunta(?:\s+regionale)?|"
    r"della\s+giunta(?:\s+regionale)?|"
    r"del\s+presidente(?:\s+della\s+giunta(?:\s+regionale)?)?|"
    r"del\s+consiglio(?:\s+regionale)?|gr|grt"
)
_DATA_ATTO = (
    r"\d{4}-\d{2}-\d{2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{4}"
    rf"|\d{{1,2}}\s*[°º]?\s+(?:{_MESI})\s+\d{{4}}"
)
SCHEMA_ATTO_TESTO = (
    r"(?:\b(?:decreto|delibera|deliberazione|dgr|dd)\b|\bd\.g\.r\.|\bd\.d\.)"
    rf"(?:\s+(?:{_QUALIFICA}))*"
    r"(?:\s*(?:n\.|n°|nº|n\b|numero))?"
    r"\s*(?P<numero>\d{2,6})(?:/\d{4})?(?![\d/]|[.,]\d)"
    rf"(?!\s+(?:{_MESI}))"
    rf"(?:\s+del(?:l['’])?\s*(?P<data_atto>{_DATA_ATTO}))?"
)

# Come si riconoscono i dati nella risposta. L'ordine conta: una porzione
# gia' catturata non si riconsidera.
SCHEMI = {
    "atto": [SCHEMA_ATTO_TESTO],
    "importo": [
        rf"\b(\d[\d.]*(?:,\d+)?\s*(?:{_MOLTIPLICATORE}))\b",
        r"\b([\d.]+,\d{1,2})\s*€",
        r"€\s*([\d.]+(?:,\d{1,2})?)",
        r"\b([\d.]+,\d{2})\s*euro\b",
    ],
    "percentuale": [
        r"\b(\d+(?:[.,]\d+)?)\s*(?:%|per\s*cento|punti\s+percentuali)",
    ],
    "data": [
        r"\b(\d{4}-\d{2}-\d{2})\b",
        r"\b(\d{1,2}:\d{2})\b",
        rf"\b(\d{{1,2}}\s*[°º]?\s+(?:{_MESI})(?:\s+\d{{4}})?)\b",
        r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
        r"\b(\d{1,2}-\d{1,2}-\d{4})\b",
        r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b",
        r"\b(\d{1,2}/\d{1,2})(?!/)\b",
    ],
    "codice": [
        r"\b([A-Z]\d{2}[A-Z]\d{10,12})\b",
        r"\b(\d{8}-\d)\b",
    ],
    "riferimento": [
        r"\bn\.?\s*(\d+/\d{4})\b",
        r"\bart(?:icolo)?\.?\s*(\d+(?:\s*,?\s*comma\s*\d+)?)",
        r"\b(?:par\.?|paragrafo|punto|lett\.?)\s*(\d+)\b",
        r"\b(\d{1,4}/\d{4})\b",
    ],
    "periodo": [
        r"\b(19\d{2}|20\d{2})\s*[-–/]\s*(?:19\d{2}|20\d{2})\b",
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


@dataclass
class Dato:
    """Un dato riconosciuto nella risposta.

    valore: come appare nel pannello ("322,00", "54"); intero: tutto il
    testo riconosciuto ("art. 54", "2021-2027"), che per articoli e periodi
    dice di che cosa si tratta.
    """

    tipo: str
    valore: str
    posizione: int
    intero: str
    # Solo per un atto scritto con la data: la data come appare, e dove
    data_atto: str | None = None
    posizione_data: int = 0


def maschera_citazioni(risposta: str) -> str:
    """Sostituisce con spazi le citazioni e i rimandi ai frammenti.

    Gli atti scritti fuori dalle citazioni non si mascherano: sono dati,
    e si controllano come gli altri (SCHEMA_ATTO_TESTO).
    """

    def a_spazi(m):
        return " " * len(m.group(0))

    risposta = re.sub(
        SCHEMA_CITAZIONE, a_spazi, risposta, flags=re.DOTALL | re.IGNORECASE
    )
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


def contiene_numero(testo: str, numero_atto: str) -> bool:
    """Il numero compare nel testo come numero intero, non dentro un altro."""
    return (
        re.search(rf"(?<!\d)(?<!\d[.,]){numero_atto}(?!\d|[.,]\d)", testo) is not None
    )


def trova_dati(risposta: str) -> list[Dato]:
    """Ogni dato citabile della risposta, in ordine di posizione.

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
                dato = Dato(tipo, m.group(1).strip(), m.start(), m.group(0).strip())
                if m.groupdict().get("data_atto"):
                    dato.data_atto = m.group("data_atto")
                    dato.posizione_data = m.start("data_atto")
                trovati.append(dato)

    return sorted(trovati, key=lambda d: d.posizione)


def presente(dato: Dato, fonte: Valori) -> bool:
    """Il valore del dato compare per intero tra i valori della fonte.

    Ogni tipo si cerca nella sua famiglia: una percentuale tra le
    percentuali, un articolo tra gli articoli, una data tra le date. Un
    importo o una quantita' anche tra le percentuali, perche' nelle
    tabelle le cifre compaiono senza simbolo.
    """
    tipo, valore = dato.tipo, dato.valore

    if tipo in ("importo", "quantita"):
        n = numero(valore)
        return n is not None and (n in fonte.numeri or n in fonte.percentuali)

    if tipo == "percentuale":
        n = numero(valore)
        return n is not None and n in fonte.percentuali

    if tipo == "data":
        iso = data(valore)
        if iso:
            return iso in fonte.date
        ora = orario(valore)
        if ora:
            return ora in fonte.orari
        return giorno_mese(valore) in fonte.giorni_mese

    if tipo == "orario":
        return orario(f"ore {valore}") in fonte.orari

    if tipo == "anno":
        return int(valore) in fonte.anni

    if tipo == "periodo":
        return periodo(dato.intero) in fonte.periodi

    if tipo == "codice":
        return valore.upper() in fonte.codici

    if tipo == "riferimento":
        art = articolo(dato.intero)
        if art:
            return art in fonte.articoli
        # "2026/2027" e' anche un periodo, se la fonte lo scrive con il trattino
        return (
            riferimento(valore) in fonte.riferimenti or periodo(valore) in fonte.periodi
        )

    return False


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


def intestazione_di(testo: str) -> str:
    """L'intestazione di un elenco di bandi: il testo prima della prima riga.

    "Bandi aperti a cui un Comune può presentare domanda (alla data del
    2026-11-12), 5 in archivio:". Vale per ogni riga del blocco: la data
    dell'archivio, citata con l'etichetta di un bando, si trova qui.
    """
    trovato = SEGNAPOSTO.search(testo)
    return testo[: trovato.start()] if trovato else ""


def fonti_di(
    documenti: list[Document], esiti_dati: list | None
) -> tuple[dict[str, str], dict[str, str], dict[str, list[str]]]:
    """I testi di confronto di ogni etichetta, e i bandi di ogni blocco.

    I frammenti documentali sono '1', '2', ...; i blocchi dei dati 'D1',
    'D2', ... con le loro fonti; il bando k del blocco Dn, se il risultato
    elenca bandi, 'Dn.k', con l'intestazione del blocco, la riga e la
    fonte di quel bando.

    Restituisce (testi, testi_atti, voci_di). testi_atti e' il testo in
    cui si cercano i numeri d'atto: per un frammento, il suo testo con
    riferimento_atto e titolo dei metadati, che il modello vede
    nell'intestazione del frammento; per i dati, lo stesso di testi. Gli
    altri dati si cercano solo in testi: una data presente soltanto
    nell'intestazione non e' nel frammento.
    """
    testi = {
        str(numero_frammento): doc.page_content
        for numero_frammento, doc in enumerate(documenti, start=1)
    }
    testi_atti = {
        str(numero_frammento): " ".join(
            [
                doc.page_content,
                str(doc.metadata.get("riferimento_atto") or ""),
                str(doc.metadata.get("titolo") or ""),
            ]
        )
        for numero_frammento, doc in enumerate(documenti, start=1)
    }
    voci_di: dict[str, list[str]] = {}

    for numero_blocco, (_, risultato) in enumerate(esiti_dati or [], start=1):
        blocco = f"D{numero_blocco}"
        fonti = " ".join(getattr(risultato, "fonti", None) or [])
        testi[blocco] = f"{senza_segnaposto(risultato.testo)} {fonti}"
        voci_di[blocco] = []
        intestazione = intestazione_di(risultato.testo)
        for k, voce in enumerate(getattr(risultato, "voci", None) or [], start=1):
            testi[f"{blocco}.{k}"] = f"{intestazione} {voce.testo} {voce.fonte}"
            voci_di[blocco].append(f"{blocco}.{k}")

    for etichetta, testo in testi.items():
        testi_atti.setdefault(etichetta, testo)
    return testi, testi_atti, voci_di


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
    quello di Dn.k e' l'intestazione del blocco (con la data dell'archivio),
    la riga del bando e la fonte di quel bando.
    Un atto scritto nel testo ("decreto n. 9550 del 28/04/2026") e' un
    dato: il suo numero si cerca nelle fonti citate dopo di esso, per un
    frammento anche nei metadati dell'atto. Nelle citazioni a Dn.k e a un
    frammento si controllano anche i numeri di decreto o delibera scritti
    nella citazione.
    """
    testi, testi_atti, voci_di = fonti_di(documenti, esiti_dati)
    valori_di = {etichetta: valori(testo) for etichetta, testo in testi.items()}

    def ha(dato: Dato, etichetta: str) -> bool:
        """La fonte con quell'etichetta contiene il dato."""
        if dato.tipo == "atto":
            return contiene_numero(testi_atti[etichetta], dato.valore)
        return presente(dato, valori_di[etichetta])

    def bandi_con(dato: Dato) -> list[str]:
        """Le etichette dei bandi la cui riga contiene il dato."""
        return [e for e in testi if ETICHETTA_BANDO.match(e) and ha(dato, e)]

    citazioni = trova_citazioni(risposta)
    mascherata = maschera_citazioni(risposta)
    esiti: list[tuple[int, Esito]] = []

    for dato in trova_dati(mascherata):
        tipo, valore, posizione = dato.tipo, dato.valore, dato.posizione
        etichette = frammenti_citati(posizione, citazioni)
        contesto = contesto_di(risposta, posizione)

        if not etichette:
            esiti.append(
                (posizione, Esito(tipo, valore, [], "non_citato", contesto=contesto))
            )
            continue

        dentro = [e for e in etichette if e in testi and ha(dato, e)]

        if dentro:
            esiti.append(
                (
                    posizione,
                    _esito_trovato(
                        tipo, valore, dentro, voci_di, bandi_con(dato), contesto
                    ),
                )
            )
        else:
            # Se il dato e' nella riga di un bando, si indica il bando e non
            # anche il blocco che lo contiene
            altrove = bandi_con(dato) or [e for e in testi if ha(dato, e)]
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

        if dato.data_atto and dentro:
            esiti.append(
                (
                    dato.posizione_data,
                    _esito_data_atto(dato, dentro, testi_atti, risposta),
                )
            )

    esiti.extend(_verifica_atti(risposta, testi_atti))
    return [e for _, e in sorted(esiti, key=lambda coppia: coppia[0])]


def _esito_data_atto(
    dato: Dato, dentro: list[str], testi_atti: dict[str, str], risposta: str
) -> Esito:
    """L'esito della data di un atto scritto nel testo.

    Si cerca dove si e' trovato il numero dell'atto (dentro), quindi per un
    frammento anche nei metadati, e deve comparire insieme a quel numero:
    "n. 9550 del 28/04/2026" non si conferma con un 9550 da una parte e un
    28/04/2026 dall'altra. Se il numero non e' stato trovato, la data non si
    giudica: l'esito dell'atto copre gia' tutto il riferimento.
    """
    contesto = contesto_di(risposta, dato.posizione_data)
    iso = data(dato.data_atto)
    coppia = (str(int(dato.valore)), iso)
    con_data = [e for e in dentro if coppia in atti_con_data(testi_atti[e])]
    if con_data:
        return Esito("data", dato.data_atto, con_data, "verificato", "", contesto)

    date_dell_atto = sorted(
        {d for e in dentro for n, d in atti_con_data(testi_atti[e]) if n == coppia[0]}
    )
    dettaglio = (
        f"l'atto {coppia[0]} nella fonte citata ha la data {', '.join(date_dell_atto)}"
        if date_dell_atto
        else f"l'atto {coppia[0]} compare nella fonte citata senza questa data"
    )
    return Esito("data", dato.data_atto, dentro, "non_trovato", dettaglio, contesto)


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


def _verifica_atti(
    risposta: str, testi_atti: dict[str, str]
) -> list[tuple[int, Esito]]:
    """Controlla i numeri di decreto o delibera nelle citazioni.

    In una citazione a [Dn.k] ogni numero d'atto deve comparire nella riga
    di quel bando; in una citazione a un frammento [n], nel suo testo o
    nei metadati del suo atto. Se compare in un'altra fonte, lo si indica.
    Le citazioni a un blocco [Dn] non si controllano: non si sa di quale
    bando sia l'atto.
    """
    esiti = []
    for m in re.finditer(SCHEMA_CITAZIONE, risposta, re.DOTALL | re.IGNORECASE):
        citazione = m.group(0)
        etichette = [
            e.upper()
            for e in re.findall(rf"\[({ETICHETTA})\]", citazione, re.IGNORECASE)
        ]
        controllate = [e for e in etichette if ETICHETTA_BANDO.match(e) or e.isdigit()]
        if not controllate:
            continue
        solo_bandi = all(ETICHETTA_BANDO.match(e) for e in controllate)

        senza_etichette = re.sub(SCHEMA_RIFERIMENTO, " ", citazione)
        contesto = " ".join(citazione.split())
        for numero_atto in numeri_atto(senza_etichette):
            dentro = [
                e
                for e in controllate
                if e in testi_atti and contiene_numero(testi_atti[e], numero_atto)
            ]
            if dentro:
                esiti.append(
                    (
                        m.start(),
                        Esito("atto", numero_atto, dentro, "verificato", "", contesto),
                    )
                )
                continue

            con_numero = [
                e for e, t in testi_atti.items() if contiene_numero(t, numero_atto)
            ]
            # Come per gli altri dati: se l'atto e' nella riga di un bando, si
            # indica il bando e non anche il blocco che lo contiene
            altrove = [e for e in con_numero if ETICHETTA_BANDO.match(e)] or con_numero
            if altrove:
                dettaglio = f"presente invece in {altrove}"
            elif solo_bandi:
                dettaglio = "non presente nella riga del bando citato"
            else:
                dettaglio = "non presente nella fonte citata"
            esiti.append(
                (
                    m.start(),
                    Esito(
                        "atto",
                        numero_atto,
                        controllate,
                        "non_trovato",
                        dettaglio,
                        contesto,
                    ),
                )
            )
    return esiti


def giudizio(esiti: list[Esito]) -> tuple[str, str]:
    """Il livello del pannello di verifica e il suo messaggio.

    - "rosso": almeno un dato non trovato nella fonte citata;
    - "verde": almeno un dato verificato che non sia un anno, e nessun dato
      senza fonte o citato con il blocco invece che con il bando;
    - "arancione": nessun dato non trovato, ma dati senza fonte o citati con
      il blocco, oppure nessun dato verificato oltre agli anni;
    - "nessuno": nessun dato da verificare.

    Gli anni non bastano per il verde: compaiono nei titoli e nelle date
    di riferimento, e confermarli non dice nulla sulla risposta.
    """
    if not esiti:
        return "nessuno", "Nessun dato numerico da verificare in questa risposta."

    conteggio = riassumi(esiti)
    non_trovati = conteggio["non_trovato"]
    non_citati = conteggio["non_citato"]
    generici = conteggio.get("citazione_generica", 0)
    verificati = sum(e.stato == "verificato" and e.tipo != "anno" for e in esiti)

    if non_trovati:
        return "rosso", (
            f"{non_trovati} dato/i citato/i NON trovato/i nella fonte indicata. "
            "Verificare manualmente prima di riutilizzare la risposta."
        )

    if verificati and not non_citati and not generici:
        return "verde", f"Dati verificati nella fonte citata: {verificati}."

    problemi = [] if verificati else ["nessun dato verificato oltre agli anni"]
    if non_citati:
        problemi.append(f"{non_citati} dato/i senza fonte")
    if generici:
        problemi.append(f"{generici} citato/i con il blocco invece che con il bando")
    primo = f"dati verificati: {verificati}; " if verificati else ""
    testo = primo + ", ".join(problemi)
    return "arancione", (
        testo[0].upper()
        + testo[1:]
        + ". Verificare manualmente prima di riutilizzare la risposta."
    )


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
