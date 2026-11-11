"""Estrazione assistita dei campi di un bando dal testo della pagina."""

import json
import re
from dataclasses import dataclass
from datetime import date

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.config import MODEL_NAME

# I campi che il modello deve produrre, con il tipo atteso.
# I campi critici richiedono sempre conferma umana.
CAMPI = {
    "titolo": ("str", False),
    "ente": ("str", False),
    "tema": ("str", False),
    "programma": ("str", False),
    "apertura": ("data", False),
    "scadenza": ("data", True),
    "scadenza_nota": ("str", False),
    "a_sportello": ("bool", True),
    "ammette_comuni": ("bool", True),
    "beneficiari": ("str", True),
    "territorio": ("str", False),
    "premialita": ("str", False),
    "costo_min": ("num", False),
    "costo_max": ("num", False),
    "contributo_perc": ("num", False),
    "contributo_min": ("num", False),
    "contributo_max": ("num", False),
    "dotazione": ("num", False),
    "riferimento_atto": ("str", False),
}

CRITICI = [nome for nome, (_, critico) in CAMPI.items() if critico]

# I campi senza i quali il bando non si salva, se mancano o non si
# convertono. Diversi dai critici, che indicano cosa far confermare.
# - titolo, ente: identificano il bando e compaiono nella citazione
# - beneficiari: e' la prova da cui si decide chi puo' partecipare
# - ammette_comuni: obbligatorio nello schema
# - scadenza, a_sportello: da loro si calcola se il bando e' aperto
# Gli altri campi, se non si convertono, restano vuoti con un avviso.
BLOCCANTI = {
    "titolo",
    "ente",
    "beneficiari",
    "ammette_comuni",
    "scadenza",
    "a_sportello",
}

# I campi numerici per cui "fino a 50.000 euro" e' il valore cercato:
# un tetto. Per un minimo, un tetto non ha senso.
TETTO_AMMESSO = {"costo_max", "contributo_max", "contributo_perc", "dotazione"}

# Un numero in formato italiano: punto ogni tre cifre e virgola
# decimale (1.200.000,00), oppure senza separatori (300000, 1,2)
NUMERO = r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?"

IMPORTO = re.compile(
    r"^(?:(?P<tetto>fino a|massimo|max\.?|non superiore a)\s+)?"
    rf"(?P<numero>{NUMERO})"
    r"(?:\s*(?P<moltiplicatore>mila|milion[ei]|mln|miliard[oi]))?$"
)

MOLTIPLICATORI = {
    "mila": 1e3,
    "milione": 1e6,
    "milioni": 1e6,
    "mln": 1e6,
    "miliardo": 1e9,
    "miliardi": 1e9,
}

# Qualunque sequenza di cifre e separatori: serve a contare gli importi
CIFRE = re.compile(r"\d[\d.,]*\d|\d")

NON_ESATTO = re.compile(r"\b(oltre|almeno|circa|più di|piu' di|a partire da)\b")

ISTRUZIONI = """Estrai i dati strutturati di un bando pubblico dal testo \
della sua pagina web.

Restituisci SOLO un oggetto JSON, senza testo prima o dopo, senza \
delimitatori di codice.

STRUTTURA
Per ogni campo produci un oggetto con tre chiavi:
  "valore": il dato estratto, oppure null se assente
  "confidenza": "alta", "media" o "bassa"
  "prova": la frase del testo da cui ricavi il valore, al massimo 25 parole

CAMPI DA ESTRARRE
- titolo: il titolo completo del bando
- ente: chi emana il bando
- tema: una sola parola tra commercio, casa, ambiente, formazione, \
istruzione, cultura, territorio, mobilita, agricoltura, turismo, pesca, sociale
- programma: il programma di finanziamento, es. PR FESR 2021-2027
- apertura: data di apertura delle domande, formato AAAA-MM-GG
- scadenza: data ULTIMA per presentare DOMANDA, formato AAAA-MM-GG
- scadenza_nota: proroghe, orari, condizioni sulla scadenza
- a_sportello: true se non c'e' una scadenza competitiva ma si presenta \
fino a esaurimento risorse
- ammette_comuni: true SOLO se un Comune puo' presentare domanda \
direttamente come beneficiario
- beneficiari: la frase del bando che definisce chi puo' presentare domanda
- territorio: ambito territoriale ammissibile
- premialita: criteri che assegnano punteggio aggiuntivo
- costo_min, costo_max: importo minimo e massimo del PROGETTO ammissibile
- contributo_perc: percentuale massima di contributo, solo il numero
- contributo_min, contributo_max: importo minimo e massimo del CONTRIBUTO
- dotazione: dotazione finanziaria complessiva del bando
- riferimento_atto: decreto o delibera che approva il bando

REGOLE CRITICHE

1. SCADENZA. Cerca la data entro cui si presenta la DOMANDA, non quella di \
rendicontazione o di conclusione lavori. Se il testo segnala una proroga, \
usa la data prorogata e spiega in scadenza_nota. Se il campo strutturato \
della pagina contraddice il testo, fidati del TESTO e segnala la \
discrepanza in scadenza_nota, con confidenza "bassa".

2. AMMETTE_COMUNI. Decidi leggendo il paragrafo sui beneficiari, MAI il tag \
della pagina, che e' spesso sbagliato. Metti true solo se il Comune e' \
esplicitamente tra i soggetti che presentano domanda. Se il Comune \
partecipa solo come partner, o se raccoglie domande altrui senza essere \
beneficiario, valuta con attenzione e usa confidenza "bassa".

3. IMPORTI. Sono quattro grandezze diverse e non vanno confuse: \
la dotazione complessiva del bando, il costo del singolo progetto, \
il contributo concedibile, la percentuale. Se non distingui con certezza, \
usa null e confidenza "bassa".

4. Se un dato non e' nel testo, usa null. NON dedurre, NON completare con \
conoscenze tue."""

MODELLO_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", ISTRUZIONI),
        ("human", "TESTO DELLA PAGINA:\n\n{testo}"),
    ]
)


@dataclass
class Campo:
    """Un campo estratto, con la sua confidenza e la prova."""

    nome: str
    valore: object
    confidenza: str
    prova: str
    critico: bool


def costruisci_estrattore():
    """Catena che estrae i campi di un bando."""
    modello = ChatAnthropic(
        model=MODEL_NAME,
        max_tokens=4096,
        timeout=180,
    )
    return MODELLO_PROMPT | modello | StrOutputParser()


def pulisci_json(testo: str) -> str:
    """Toglie eventuali delimitatori di codice attorno al JSON."""
    testo = testo.strip()
    if testo.startswith("```"):
        righe = [r for r in testo.splitlines() if not r.strip().startswith("```")]
        testo = "\n".join(righe)
    return testo.strip()


def estrai(estrattore, testo: str, debug: bool = False) -> list[Campo]:
    """Estrae i campi dal testo della pagina, con confidenza e prova."""
    grezzo = estrattore.invoke({"testo": testo})

    try:
        dati = json.loads(pulisci_json(grezzo))
    except json.JSONDecodeError as errore:
        raise ValueError(
            f"Risposta non interpretabile come JSON: {errore}\n{grezzo[:300]}"
        ) from errore

    if debug:
        print("--- JSON GREZZO ---")
        print(json.dumps(dati, indent=2, ensure_ascii=False)[:2000])
        print("--- fine ---\n")

    campi = []
    for nome, (_, critico) in CAMPI.items():
        voce = dati.get(nome)

        if isinstance(voce, dict):
            valore = voce.get("valore")
            confidenza = voce.get("confidenza", "bassa")
            prova = voce.get("prova", "")
        elif voce is None:
            valore, confidenza, prova = None, "bassa", "campo assente"
        else:
            # Il modello ha restituito il valore nudo invece dell'oggetto:
            # lo accettiamo ma abbassiamo la confidenza.
            valore, confidenza, prova = voce, "bassa", "formato non conforme"

        if confidenza not in ("alta", "media", "bassa"):
            confidenza = "bassa"

        campi.append(
            Campo(
                nome=nome,
                valore=valore,
                confidenza=confidenza,
                prova=prova,
                critico=critico,
            )
        )

    return campi


def da_rivedere(campi: list[Campo]) -> list[Campo]:
    """I campi che richiedono conferma: critici o a bassa confidenza."""
    return [c for c in campi if c.critico or c.confidenza != "alta"]


def converti_importo(nome: str, valore) -> tuple[float | None, str | None]:
    """Converte un importo in numero. Restituisce (numero, motivo).

    Accetta un solo importo, in formato italiano, con "euro" o "€",
    eventualmente con un moltiplicatore (mila, milioni, miliardi) e, per
    i campi che indicano un tetto, preceduto da "fino a" o "massimo".
    Tutto il resto non diventa un numero: due importi, un intervallo, un
    importo approssimato ("oltre", "circa") o un punto che non separa le
    migliaia. In quei casi il numero e' None e il motivo dice perche'.
    """
    if isinstance(valore, bool):
        return None, "e' un vero/falso, non un importo"

    if isinstance(valore, (int, float)):
        return float(valore), None

    testo = str(valore).lower().replace("€", " ")
    testo = re.sub(r"\beur(o)?\b", " ", testo)
    testo = re.sub(r"\s+", " ", testo).strip()
    testo = re.sub(r"\s+di$", "", testo)

    trovato = IMPORTO.match(testo)
    if trovato:
        if trovato["tetto"] and nome not in TETTO_AMMESSO:
            return None, "indica un tetto, non un minimo"
        numero = float(trovato["numero"].replace(".", "").replace(",", "."))
        numero *= MOLTIPLICATORI.get(trovato["moltiplicatore"], 1)
        return round(numero, 2), None

    importi = CIFRE.findall(testo)
    if len(importi) > 1:
        return None, "contiene piu' di un importo"
    if NON_ESATTO.search(testo):
        return None, "importo non esatto"
    if importi and not re.fullmatch(NUMERO, importi[0]):
        return None, "separatori non riconosciuti"
    return None, "formato non riconosciuto"


def normalizza_valore(nome: str, valore) -> tuple[object, str | None]:
    """Converte il valore estratto nel tipo che il database si aspetta.

    Restituisce (valore, motivo): il motivo e' None se il valore e'
    assente o convertito, altrimenti spiega perche' non si converte.
    """
    tipo = CAMPI[nome][0]

    if valore is None or valore == "":
        return None, None

    if tipo == "bool":
        if isinstance(valore, bool):
            return (1 if valore else 0), None
        testo = str(valore).strip().lower()
        if testo in ("true", "si", "sì", "1"):
            return 1, None
        if testo in ("false", "no", "0"):
            return 0, None
        return None, "non e' vero o falso"

    if tipo == "num":
        return converti_importo(nome, valore)

    if tipo == "data":
        testo = str(valore).strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", testo):
            return testo, None
        return None, "non e' nel formato AAAA-MM-GG"

    return str(valore).strip(), None


def valida(campi: list[Campo]) -> tuple[dict, list[str], list[str]]:
    """Converte i campi in una riga per il database.

    Restituisce (riga, problemi, avvisi). I problemi impediscono il
    salvataggio: un campo bloccante mancante o non convertibile. Gli
    avvisi no: un campo non bloccante che non si converte resta vuoto,
    e l'avviso conserva il valore originale per chi lo rivede.
    """
    riga = {}
    problemi = []
    avvisi = []

    for c in campi:
        riga[c.nome], motivo = normalizza_valore(c.nome, c.valore)

        if motivo is None:
            continue

        messaggio = f"{c.nome}: valore '{c.valore}' non convertibile ({motivo})"
        if c.nome in BLOCCANTI:
            problemi.append(messaggio)
        else:
            avvisi.append(f"{messaggio}, lasciato vuoto")

    for obbligatorio in ("titolo", "ente", "beneficiari"):
        if not riga.get(obbligatorio):
            problemi.append(f"{obbligatorio}: campo obbligatorio mancante")

    if riga.get("ammette_comuni") is None:
        problemi.append("ammette_comuni: deve essere 0 o 1, non puo' restare vuoto")

    if riga.get("a_sportello") is None:
        riga["a_sportello"] = 0

    return riga, problemi, avvisi


def decidi_automatico(campi: list[Campo], riga: dict) -> tuple[bool, str]:
    """Decide se salvare senza conferma umana.

    La soglia e' prudente: si salva solo quando i campi critici sono
    espliciti e il bando risulta ancora aperto. In tutti gli altri casi
    si scarta con il motivo, per una revisione successiva.
    """
    per_nome = {c.nome: c for c in campi}

    if riga.get("ammette_comuni") != 1:
        return False, "non ammette i Comuni"

    ammette = per_nome.get("ammette_comuni")
    if ammette and ammette.confidenza == "bassa":
        return False, "ammette_comuni a bassa confidenza"

    if riga.get("a_sportello") == 1:
        return True, "a sportello"

    scadenza = riga.get("scadenza")
    if not scadenza:
        return False, "scadenza non determinata"

    if scadenza < date.today().isoformat():
        return False, f"scaduto il {scadenza}"

    campo_scadenza = per_nome.get("scadenza")
    if campo_scadenza and campo_scadenza.confidenza == "bassa":
        return False, f"scadenza {scadenza} a bassa confidenza"

    return True, f"aperto fino al {scadenza}"
