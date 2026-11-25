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
from decimal import Decimal

from langchain_core.documents import Document

from src.database.modelli import SEGNAPOSTO, senza_segnaposto
from src.normalizzazione import (
    MESI,
    Valori,
    articolo,
    atti_con_data,
    codice,
    data,
    date_degli_atti,
    giorno_mese,
    intervalli,
    letterale,
    numeri_in_lettere,
    numero,
    orario,
    periodo,
    riferimento,
    uniforma_trattini,
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
ETICHETTA_BLOCCO = re.compile(r"^D\d+$")

_MESI = "|".join(MESI)
_MOLTIPLICATORE = r"mila|milion[ei]|mln|miliard[oi]"

# Il numero di un decreto, di una delibera o di un protocollo in una
# citazione: "decreto dirigenziale n. 18191 del 7/8/2026" -> 18191, "DGR
# 1081/2026" -> 1081, "Avviso pubblico 2026, prot. 26286" -> 26286.
# Non e' un numero d'atto quello di una data: "decreto del 29 ottobre",
# "decreto 12/10/2026".
SCHEMA_NUMERO_ATTO = re.compile(
    r"(?:\b(?:decreto|delibera|deliberazione|dgrt?|dd|protocollo)\b"
    r"|d\.g\.r\.(?:t\.)?|d\.d\.|\bprot\.)"
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
# Le qualificazioni sono un elenco chiuso e si possono ripetere ("di Giunta
# Regionale Toscana"); parole libere no, neanche con "n.": "il decreto
# stabilisce n. 10 posti" non e' l'atto 10.
_QUALIFICA = (
    r"dirigenziale|regionale|di\s+giunta(?:\s+regionale)?|"
    r"della\s+giunta(?:\s+regionale)?|"
    r"del\s+presidente(?:\s+della\s+giunta(?:\s+regionale)?)?|"
    r"del\s+consiglio(?:\s+regionale)?|"
    r"della\s+regione\s+toscana|regione\s+toscana|toscana|rt|gr|grt"
)
_DATA_ATTO = (
    r"\d{4}-\d{2}-\d{2}|\d{1,2}[/.-]\d{1,2}[/.-]\d{4}"
    rf"|\d{{1,2}}\s*[°º]?\s+(?:{_MESI})\s+\d{{4}}"
)
SCHEMA_ATTO_TESTO = (
    r"(?:\b(?:decreto|delibera|deliberazione|dgrt?|dd|protocollo)\b"
    r"|\bd\.g\.r\.(?:t\.)?|\bd\.d\.|\bprot\.)"
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
        # "€ 322,00" e "€. 34,00": il punto dopo il simbolo non e' l'importo
        r"€\.?\s*(\d[\d.]*(?:,\d{1,2})?)",
        r"\b([\d.]+,\d{2})\s*euro\b",
    ],
    "percentuale": [
        r"\b(\d+(?:[.,]\d+)?)\s*(?:%|per\s*cento|punti\s+percentuali)",
    ],
    "data": [
        r"\b(\d{4}-\d{2}-\d{2})\b",
        r"\b(\d{1,2}:\d{2})\b",
        rf"\b((?:\d{{1,2}}\s*[°º]?|primo)\s+(?:{_MESI})(?:\s+\d{{4}})?)\b",
        r"\b(\d{1,2}/\d{1,2}/\d{4})\b",
        r"\b(\d{1,2}-\d{1,2}-\d{4})\b",
        r"\b(\d{1,2}\.\d{1,2}\.\d{4})\b",
        r"\b(\d{1,2}/\d{1,2})(?!/)\b",
    ],
    "codice": [
        r"\b([A-Z]\d{2}[A-Z]\d{10,12})\b",
        r"\b(\d{8}-\d)\b",
        # Codici con i punti (ATECO): "49.34.00", "I 55.1". La lettera
        # della sezione e' maiuscola anche se gli schemi ignorano le
        # maiuscole: "a 12.5" non e' un codice
        r"(?<![\w.])((?-i:[A-U])\s?\d{2}(?:\.\d{1,2}){1,2})(?!\d|\.\d)",
        r"(?<![\w.])(\d{2}\.\d{2}\.\d{1,2})(?!\d|\.\d)",
        # A due livelli solo dopo la parola: "codice ATECO 56.10"
        r"\bateco(?:\s+primario)?\s+(\d{2}\.\d{1,2})(?!\d|\.\d)",
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
        # Anche con la virgola, "ore 10,00": non un orario 10 e una quantita' 00
        r"\bore\s+(\d{1,2}(?:[:.,]\d{2})?)",
        r"\b(?:alle|dalle)\s+(\d{1,2}[.,]\d{2})(?!\d|\s*(?:€|euro\b))",
    ],
    "quantita": [
        # Migliaia e decimali sono un valore solo: "Euro 50.000,00" e' 50000,
        # non 50 e 000,00 (falsi allarmi del lotto 1, L02 e L03)
        r"\b(\d{1,3}(?:\.\d{3})+,\d+)\b",
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
    # di un solo bando citato con il blocco [Dn] invece che con [Dn.k]) |
    # dalla_domanda (una quantita' scritta dall'utente nella domanda e non
    # nella fonte, o un importo, una percentuale o una data scritti nella
    # risposta come dati dell'utente: ne' verificati ne' allarme)
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


def inizio_citazione(blocco: str) -> int:
    """Dove comincia la citazione vera in un blocco tra parentesi: al primo
    "fonte:".

    In "(inclusa l'aliquota del 7%, fonte: [7], Regione, pag. 14)" il testo
    prima di "fonte:" è contenuto della risposta e si verifica come il
    resto; da "fonte:" in poi è la citazione.

    Senza "fonte:" tutto il blocco è citazione e l'inizio è 0: è il caso
    delle etichette sciolte ("[D1.2]", "secondo [D2]", "(fonti: [D1.1])")
    che maschera_citazioni riconosce con SCHEMA_RIFERIMENTO.
    """
    trovato = re.search(r"fonte:", blocco, re.IGNORECASE)
    return trovato.start() if trovato else 0


def maschera_citazioni(risposta: str) -> str:
    """Sostituisce con spazi le citazioni e i rimandi ai frammenti.

    Di un blocco tra parentesi con "fonte:" si mascherano la parentesi
    aperta e la parte da "fonte:" in poi: il testo prima resta, e i suoi
    dati si verificano sulla fonte citata subito dopo.
    Gli atti scritti fuori dalle citazioni non si mascherano: sono dati,
    e si controllano come gli altri (SCHEMA_ATTO_TESTO).
    """

    def a_spazi(m):
        blocco = m.group(0)
        inizio = inizio_citazione(blocco)
        if inizio == 0:
            # Tutto il blocco è citazione: spazi quanti sono i caratteri,
            # così le posizioni restano quelle della risposta
            return " " * len(blocco)
        return " " + blocco[1:inizio] + " " * (len(blocco) - inizio)

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
    """I numeri di decreto, delibera o protocollo scritti in una citazione."""
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
                if tipo == "data" and not _data_esistente(dato.valore):
                    dato.tipo = "letterale"
                if m.groupdict().get("data_atto"):
                    dato.data_atto = m.group("data_atto")
                    dato.posizione_data = m.start("data_atto")
                trovati.append(dato)

    return sorted(trovati, key=lambda d: d.posizione)


def _data_esistente(valore: str) -> bool:
    """Il valore con la forma di una data o di un orario esiste come tale.

    "21/27" di "PR FESR 21/27" ha la forma di un giorno e un mese, ma il
    mese 27 non esiste: non e' una data, e il verificatore lo cerca tale e
    quale nella fonte (tipo "letterale"). Non lo ignora: un periodo
    sbagliato ("14/20" al posto di "21/27") e' un errore vero. E non lo
    lascia agli schemi delle quantita', dove "21" e "27" si potrebbero
    confermare per coincidenza con altri numeri della fonte.
    """
    return bool(data(valore) or orario(valore) or giorno_mese(valore))


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
        if n is None:
            return False
        # Una quantita' con la forma di un anno ("dal 2021," con la virgola,
        # che lo schema degli anni non prende) vale anche tra gli anni della
        # fonte, dove sta se la fonte lo scrive in una data ("dal primo
        # gennaio 2021")
        anno = tipo == "quantita" and re.fullmatch(r"(?:19|20)\d{2}", valore)
        return (
            n in fonte.numeri
            or n in fonte.percentuali
            or bool(anno and int(valore) in fonte.anni)
        )

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
        return codice(valore) in fonte.codici

    if tipo == "letterale":
        return letterale(valore) in fonte.letterali

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


# L'inizio di un punto d'elenco: "- ", "* ", "• ", "1. ", "2) "
PUNTO_ELENCO = re.compile(r"[ \t]*(?:[-*•]|\d+[.)])\s")


def citazioni_del_dato(
    risposta: str, posizione: int, citazioni: list[tuple[int, str]]
) -> list[str]:
    """I frammenti a cui si riferisce un dato: quelli citati dopo, salvo in un elenco.

    In un punto d'elenco che ha gia' la sua citazione, un dato scritto dopo
    di essa appartiene a quel punto: se la citazione successiva sta oltre
    l'a capo, e' quella del punto dopo, e vale la citazione del proprio
    punto. "- «EU-Blending» (fonte: [D1.8]): settori ai sensi della delibera
    704/2025.⏎- «Obbligazioni» (fonte: [D1.9])": il 704 va con D1.8 (9
    falsi allarmi nelle risposte salvate, 25/11/2026). Vale anche quando la
    citazione dopo contiene il dato: un dato del punto di Sport non si
    conferma con la riga di Cultura del punto seguente (caso 4).
    """
    etichette = frammenti_citati(posizione, citazioni)
    if not etichette:
        return etichette
    successiva = min(p for p, _ in citazioni if p > posizione)
    if "\n" not in risposta[posizione:successiva]:
        return etichette
    inizio = risposta.rfind("\n", 0, posizione) + 1
    if not PUNTO_ELENCO.match(risposta, inizio):
        return etichette
    precedenti = [e for p, e in citazioni if inizio <= p < posizione]
    return [precedenti[-1]] if precedenti else etichette


# Importi, percentuali e date della domanda (25/11/2026): non trovati nella
# fonte, sono dati dell'utente solo se la risposta li scrive come tali,
# possessivo piu' nome piu' "di" o "da" subito prima del valore ("il suo
# prestito di 30 mila"). Senza la guardia, il valore della domanda
# attribuito alla fonte ("il bando vale fino a 50 mila (fonte: [D1])",
# quando la fonte dice 40.000) perdeva l'allarme.
TIPI_DELL_UTENTE = ("importo", "percentuale", "data")
DATO_DELL_UTENTE = re.compile(
    r"\b(?:suo|sua|suoi|sue|vostro|vostra|vostri|vostre)\s+[^\W\d_]+\s+"
    r"(?:di|da)\s+$",
    re.IGNORECASE,
)


def dell_utente(risposta: str, posizione: int) -> bool:
    """Il valore a posizione e' scritto come dato dell'utente."""
    return bool(DATO_DELL_UTENTE.search(risposta, 0, posizione))


def valori_della_domanda(domanda: str | None) -> Valori | None:
    """I valori della domanda, con i numeri in lettere ("centoventi alveari").

    I numeri in lettere valgono per le quantita' (verifica), quindi solo da
    10 in su: "una", "sei" o "otto" in una domanda sono quasi sempre altre
    parole, e le quantita' a una cifra non si estraggono. Importi,
    percentuali e date contano solo con la guardia di dell_utente.
    """
    if not domanda:
        return None
    trovati = valori(domanda)
    trovati.numeri |= {
        Decimal(n)
        for n, _ in numeri_in_lettere(domanda, solo_con_unita=False)
        if n >= 10
    }
    return trovati


def contesto_di(testo: str, posizione: int, ampiezza: int = 40) -> str:
    """Il testo intorno a un dato, per rendere leggibile la riga di verifica."""
    inizio = max(0, posizione - ampiezza)
    fine = posizione + ampiezza
    return " ".join(testo[inizio:fine].split())


# La finestra di bandi_in_scadenza nell'intestazione: "in scadenza entro
# 30 giorni"
SCHEMA_FINESTRA = re.compile(r"\bentro\s+\d{1,3}\s+giorni\b", re.IGNORECASE)
# La finestra dello storico di bandi_scaduti_per_ente: "passata negli ultimi
# 12 mesi". Vale per ogni riga come quella delle scadenze (correzione G4,
# docs/piano-correzioni-lotto1.md); il conteggio "N in archivio" resta escluso
SCHEMA_FINESTRA_STORICO = re.compile(
    r"\bnegli\s+ultimi\s+\d{1,2}\s+mesi\b", re.IGNORECASE
)


def date_dell_intestazione(testo: str) -> str:
    """Le date e la finestra dell'intestazione di un elenco di bandi.

    L'intestazione e' il testo prima della prima riga: "Bandi aperti a cui
    un Comune può presentare domanda (alla data del 2026-11-12), 12 in
    archivio:". La data dell'archivio vale per ogni riga del blocco, e si
    cita con l'etichetta di un bando; cosi' la finestra di un elenco in
    scadenza ("entro 30 giorni") e quella dello storico ("negli ultimi 12
    mesi"), che ogni riga rispetta. Gli altri numeri no: "12 in archivio"
    non deve verificare un 12 qualsiasi attribuito a un bando. Le date in
    ISO; le finestre come sono scritte.
    """
    trovato = SEGNAPOSTO.search(testo)
    intestazione = testo[: trovato.start()] if trovato else ""
    finestre = [
        m.group(0)
        for schema in (SCHEMA_FINESTRA, SCHEMA_FINESTRA_STORICO)
        for m in schema.finditer(intestazione)
    ]
    return " ".join([*sorted(valori(intestazione).date), *finestre])


def fonti_di(
    documenti: list[Document], esiti_dati: list | None
) -> tuple[dict[str, str], dict[str, str], dict[str, list[str]]]:
    """I testi di confronto di ogni etichetta, e i bandi di ogni blocco.

    I frammenti documentali sono '1', '2', ...; i blocchi dei dati 'D1',
    'D2', ... con le loro fonti; il bando k del blocco Dn, se il risultato
    elenca bandi, 'Dn.k', con le date dell'intestazione del blocco, la
    riga e la fonte di quel bando.

    Restituisce (testi, testi_atti, voci_di). testi_atti e' il testo in
    cui si cercano i numeri d'atto: per un frammento, il suo testo con
    riferimento_atto e titolo dei metadati, che il modello vede
    nell'intestazione del frammento; per i dati, lo stesso di testi. Gli
    altri dati si cercano solo in testi: una data presente soltanto
    nell'intestazione non e' nel frammento, salvo quelle dello stato del
    bando (metadato stato_bando), che fanno parte del testo di confronto.
    """
    # Lo stato del bando, calcolato alla data della domanda, sta
    # nell'intestazione del frammento: "scaduto il 2026-10-15 (fonte: [3])"
    # si verifica su quella riga, come il testo
    testi = {
        str(numero_frammento): " ".join(
            [doc.page_content, str(doc.metadata.get("stato_bando") or "")]
        ).strip()
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
        date = date_dell_intestazione(risultato.testo)
        for k, voce in enumerate(getattr(risultato, "voci", None) or [], start=1):
            testi[f"{blocco}.{k}"] = f"{date} {voce.testo} {voce.fonte}"
            voci_di[blocco].append(f"{blocco}.{k}")

    for etichetta, testo in testi.items():
        testi_atti.setdefault(etichetta, testo)
    return testi, testi_atti, voci_di


def verifica(
    risposta: str,
    documenti: list[Document],
    esiti_dati: list | None = None,
    domanda: str | None = None,
) -> list[Esito]:
    """Controlla che ogni dato della risposta esista nella fonte citata.

    I frammenti documentali sono etichettati '1', '2', ...; i dati
    numerici dell'archivio statistico 'D1', 'D2', ...; il bando k del
    blocco Dn, se il risultato elenca bandi, 'Dn.k'.

    Il testo di confronto di Dn e' il blocco intero con le sue fonti;
    quello di Dn.k sono le date dell'intestazione del blocco (la data
    dell'archivio, non i numeri), la riga del bando e la fonte di quel
    bando.
    Un atto scritto nel testo ("decreto n. 9550 del 28/04/2026") e' un
    dato: il suo numero si cerca nelle fonti citate dopo di esso, per un
    frammento anche nei metadati dell'atto. Nelle citazioni a Dn.k e a un
    frammento si controllano anche i numeri di decreto o delibera scritti
    nella citazione.

    Un dato in un punto d'elenco, dopo la citazione del suo punto, va con
    quella (citazioni_del_dato). Con la domanda, una quantita' non trovata
    nella fonte ma scritta dall'utente ("un disoccupato di 57 anni") ha
    l'esito dalla_domanda, ne' verificato ne' allarme; date, importi e
    percentuali della domanda solo se la risposta li scrive come dati
    dell'utente ("il suo prestito di 30 mila"), altrimenti restano al
    controllo normale. Gli intervalli
    di date "dal X al Y" sono un dato anche come coppia: la fine prima
    dell'inizio e' non trovata anche senza fonte, e gli estremi presenti
    nella fonte citata ma non nella stessa finestra pure (_verifica_intervalli).
    """
    # "2026‑11‑13" con il trattino U+2011 e' una data come "2026-11-13"; la
    # lunghezza non cambia, quindi le posizioni restano quelle della risposta
    risposta = uniforma_trattini(risposta)
    testi, testi_atti, voci_di = fonti_di(documenti, esiti_dati)
    valori_di = {etichetta: valori(testo) for etichetta, testo in testi.items()}
    della_domanda = valori_della_domanda(domanda)

    def dalla_domanda(dato: Dato) -> bool:
        """Un valore che l'utente ha scritto nella domanda.

        Una quantita' sempre; un importo, una percentuale o una data solo se
        la risposta lo scrive come dato dell'utente (dell_utente).
        """
        if della_domanda is None or not presente(dato, della_domanda):
            return False
        if dato.tipo == "quantita":
            return True
        return dato.tipo in TIPI_DELL_UTENTE and dell_utente(risposta, dato.posizione)

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
        etichette = citazioni_del_dato(risposta, posizione, citazioni)
        contesto = contesto_di(risposta, posizione)

        if not etichette:
            stato = "dalla_domanda" if dalla_domanda(dato) else "non_citato"
            esiti.append((posizione, Esito(tipo, valore, [], stato, contesto=contesto)))
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
        elif dalla_domanda(dato):
            esiti.append(
                (
                    posizione,
                    Esito(
                        tipo,
                        valore,
                        etichette,
                        "dalla_domanda",
                        "il numero è nella domanda",
                        contesto,
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
                    _esito_data_atto(
                        dato.valore,
                        dato.data_atto,
                        dentro,
                        testi_atti,
                        contesto_di(risposta, dato.posizione_data),
                    ),
                )
            )

    esiti.extend(_verifica_atti(risposta, testi_atti))
    esiti.extend(
        _verifica_intervalli(risposta, mascherata, citazioni, testi, valori_di)
    )
    return [e for _, e in sorted(esiti, key=lambda coppia: coppia[0])]


def _verifica_intervalli(
    risposta: str,
    mascherata: str,
    citazioni: list[tuple[int, str]],
    testi: dict[str, str],
    valori_di: dict[str, Valori],
) -> list[tuple[int, Esito]]:
    """Gli intervalli di date della risposta controllati come coppia.

    Le due date si verificano gia' una per una; qui il ruolo. "dal
    2027-01-11 al 2027-01-10" e' sbagliato senza bisogno della fonte: la
    fine viene prima dell'inizio. Con X e Y entrambi nelle fonti citate, la
    coppia deve essere un intervallo di una di esse: 2027-01-10 fine di una
    finestra non conferma "dal 2027-01-11 al 2027-01-10" (caso 3 del
    24/11/2026). Un intervallo giusto non aggiunge esiti.
    """
    esiti = []
    coppie_di: dict[str, set] = {}
    for posizione, scritto, inizio, fine in intervalli(mascherata):
        etichette = citazioni_del_dato(risposta, posizione, citazioni)
        contesto = contesto_di(risposta, posizione)
        valore = " ".join(scritto.split())
        if fine < inizio:
            esiti.append(
                (
                    posizione,
                    Esito(
                        "intervallo",
                        valore,
                        etichette,
                        "non_trovato",
                        "la fine viene prima dell'inizio",
                        contesto,
                    ),
                )
            )
            continue
        citate = [e for e in etichette if e in testi]
        estremi = any(inizio in valori_di[e].date for e in citate) and any(
            fine in valori_di[e].date for e in citate
        )
        if not estremi:
            continue
        for e in citate:
            if e not in coppie_di:
                coppie_di[e] = {(x, y) for _, _, x, y in intervalli(testi[e])}
        if not any((inizio, fine) in coppie_di[e] for e in citate):
            esiti.append(
                (
                    posizione,
                    Esito(
                        "intervallo",
                        valore,
                        citate,
                        "non_trovato",
                        "estremi presenti, ma non della stessa finestra",
                        contesto,
                    ),
                )
            )
    return esiti


def _esito_data_atto(
    numero_atto: str,
    data_scritta: str,
    dentro: list[str],
    testi_atti: dict[str, str],
    contesto: str,
) -> Esito:
    """L'esito della data di un atto, nel testo o in una citazione.

    Si cerca dove si e' trovato il numero dell'atto (dentro), quindi per un
    frammento anche nei metadati, e deve comparire insieme a quel numero:
    "n. 9550 del 28/04/2026" non si conferma con un 9550 da una parte e un
    28/04/2026 dall'altra. Se il numero non e' stato trovato, la data non si
    giudica: l'esito dell'atto copre gia' tutto il riferimento. Per questo
    chi chiama passa solo un dentro non vuoto.
    """
    coppia = (str(int(numero_atto)), data(data_scritta))
    con_data = [e for e in dentro if coppia in atti_con_data(testi_atti[e])]
    if con_data:
        return Esito("data", data_scritta, con_data, "verificato", "", contesto)

    date_dell_atto = sorted(
        {d for e in dentro for n, d in atti_con_data(testi_atti[e]) if n == coppia[0]}
    )
    dettaglio = (
        f"l'atto {coppia[0]} nella fonte citata ha la data {', '.join(date_dell_atto)}"
        if date_dell_atto
        else f"l'atto {coppia[0]} compare nella fonte citata senza questa data"
    )
    return Esito("data", data_scritta, dentro, "non_trovato", dettaglio, contesto)


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
    """Controlla i numeri di decreto o delibera nelle citazioni, e le date.

    In una citazione a [Dn.k] ogni numero d'atto deve comparire nella riga
    di quel bando; in una citazione a un frammento [n], nel suo testo o
    nei metadati del suo atto. Se compare in un'altra fonte, lo si indica.
    La data scritta con il numero ("decreto 18191 del 7/8/2026") si
    controlla come per gli atti nel testo (_esito_data_atto). In una
    citazione a un blocco [Dn] il numero si cerca in tutto il blocco, con
    le sue fonti: non dice di quale bando sia l'atto, ma un numero assente
    dal blocco risulta non trovato invece di passare senza esito (correzione
    D4, docs/piano-correzioni-lotto1.md: prima non si controllava).
    """
    esiti = []
    for m in re.finditer(SCHEMA_CITAZIONE, risposta, re.DOTALL | re.IGNORECASE):
        # Il testo prima di "fonte:" è risposta, già controllato da verifica:
        # qui solo la citazione, così un atto lì non si conta due volte
        citazione = m.group(0)[inizio_citazione(m.group(0)) :]
        etichette = [
            e.upper()
            for e in re.findall(rf"\[({ETICHETTA})\]", citazione, re.IGNORECASE)
        ]
        controllate = [
            e
            for e in etichette
            if ETICHETTA_BANDO.match(e) or ETICHETTA_BLOCCO.match(e) or e.isdigit()
        ]
        if not controllate:
            continue
        solo_bandi = all(ETICHETTA_BANDO.match(e) for e in controllate)

        senza_etichette = re.sub(SCHEMA_RIFERIMENTO, " ", citazione)
        contesto = " ".join(citazione.split())
        date_scritte = date_degli_atti(senza_etichette)
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
                esiti.extend(
                    (
                        m.start(),
                        _esito_data_atto(
                            numero_atto, scritta, dentro, testi_atti, contesto
                        ),
                    )
                    for n, scritta, _ in date_scritte
                    if n == str(int(numero_atto))
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
    di riferimento, e confermarli non dice nulla sulla risposta. I dati
    della domanda (dalla_domanda) non contano: ne' verificati ne' allarmi.
    """
    esiti = [e for e in esiti if e.stato != "dalla_domanda"]
    if not esiti:
        return "nessuno", "Nessun dato numerico da verificare in questa risposta."

    conteggio = riassumi(esiti)
    non_trovati = conteggio["non_trovato"]
    non_citati = conteggio["non_citato"]
    generici = conteggio.get("citazione_generica", 0)
    verificati = sum(e.stato == "verificato" and e.tipo != "anno" for e in esiti)

    # Il verificatore dice se un dato compare nella fonte citata, non se la
    # risposta e' giusta o completa: i testi per l'utente dicono "presenti",
    # non "verificati" (25/11/2026)
    if non_trovati:
        frase = (
            "1 dato citato non è stato trovato nella fonte indicata."
            if non_trovati == 1
            else f"{non_trovati} dati citati non sono stati trovati nella fonte "
            "indicata."
        )
        return "rosso", f"{frase} {CONTROLLARE_A_MANO}"

    if verificati and not non_citati and not generici:
        return "verde", f"{dati_presenti(verificati)}."

    problemi = (
        [] if verificati else ["nessun dato presente nella fonte oltre agli anni"]
    )
    if non_citati:
        problemi.append(f"{non_citati} dato/i senza fonte")
    if generici:
        problemi.append(f"{generici} citato/i con il blocco invece che con il bando")
    primo = f"dati presenti nella fonte citata: {verificati}; " if verificati else ""
    testo = primo + ", ".join(problemi)
    return "arancione", f"{testo[0].upper()}{testo[1:]}. {CONTROLLARE_A_MANO}"


CONTROLLARE_A_MANO = "Controllare a mano prima di riutilizzare la risposta."


def dati_presenti(n: int) -> str:
    """ "1 dato presente nella fonte citata", "N dati presenti nella fonte citata"."""
    if n == 1:
        return "1 dato presente nella fonte citata"
    return f"{n} dati presenti nella fonte citata"


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
