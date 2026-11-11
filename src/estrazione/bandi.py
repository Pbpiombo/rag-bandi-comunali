"""Estrazione assistita dei campi di un bando dal testo della pagina."""

import json
import re
from dataclasses import dataclass, field
from datetime import date

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.config import MODEL_NAME
from src.estrazione.beneficiari import (
    PER_REQUISITO,
    TERMINI,
    TIPI_BENEFICIARIO,
    frase_nel_testo,
    tipi_da_termini,
)

# I campi semplici del bando: nome -> (tipo, critico, con_prova).
# - critico: richiede sempre conferma umana nell'estrazione manuale
# - con_prova: il modello restituisce valore, confidenza e prova; gli altri
#   campi sono un valore nudo, per contenere i token in uscita
CAMPI = {
    "titolo": ("str", False, False),
    "ente": ("str", False, False),
    "tema": ("str", False, False),
    "programma": ("str", False, False),
    "apertura": ("data", False, False),
    "scadenza": ("data", True, True),
    "scadenza_nota": ("str", False, False),
    "a_sportello": ("bool", True, True),
    "pubblicato_il": ("data", False, True),
    "beneficiari": ("str", True, True),
    "territorio": ("str", False, False),
    "premialita": ("str", False, False),
    "costo_min": ("num", False, True),
    "costo_max": ("num", False, True),
    "contributo_perc": ("num", False, True),
    "contributo_min": ("num", False, True),
    "contributo_max": ("num", False, True),
    "dotazione": ("num", False, True),
    "riferimento_atto": ("str", False, False),
}

CRITICI = [nome for nome, (_, critico, _) in CAMPI.items() if critico]

# I campi senza i quali il bando non si salva, se mancano o non si
# convertono. Diversi dai critici, che indicano cosa far confermare.
# - titolo, ente: identificano il bando e compaiono nella citazione
# - beneficiari: la frase da cui si ricavano i tipi di beneficiari
# - scadenza, a_sportello: da loro si calcola se il bando e' aperto
# Oltre a questi, serve almeno un beneficiario con frase verificata.
# Gli altri campi, se non si convertono, restano vuoti con un avviso.
BLOCCANTI = {"titolo", "ente", "beneficiari", "scadenza", "a_sportello"}

NATURE = ("bando", "non_bando")

# Da dove viene la data di pubblicazione
ORIGINI_PUBBLICAZIONE = ("pubblicazione", "atto")

# Motivi di scarto: devono iniziare cosi' perche' il registro delle
# scansioni li riconosca come definitivi (src/estrazione/registro.py)
NON_BANDO = "non e' un bando"

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


def _elenco_tipi() -> str:
    return "\n".join(f"- {codice}: {d}" for codice, d in TIPI_BENEFICIARIO.items())


def _elenco_termini() -> str:
    return "\n".join(
        f'- "{espressione}" comprende: {", ".join(tipi)}'
        for espressione, tipi in TERMINI.items()
    )


ISTRUZIONI = f"""Estrai i dati strutturati di un bando pubblico dal testo \
della sua pagina web.

Restituisci SOLO un oggetto JSON, senza testo prima o dopo, senza \
delimitatori di codice.

PRIMA DI TUTTO: E' UN BANDO?
"natura": {{"valore": "bando" oppure "non_bando", "motivo": "...", \
"prova": "..."}}
E' un bando se offre un finanziamento, un contributo o un'agevolazione per \
cui si presenta domanda. NON e' un bando: una graduatoria o un esito, una \
procedura amministrativa (riconoscimenti, accreditamenti, iscrizioni a \
elenchi), un concorso o una selezione di personale, un avviso solo \
informativo. Per "non_bando" scrivi nel motivo quale di questi casi e' e \
lascia vuoti gli altri campi.

CAMPI CON PROVA
Per questi campi produci un oggetto con tre chiavi:
  "valore": il dato estratto, oppure null se assente
  "confidenza": "alta", "media" o "bassa"
  "prova": la frase del testo da cui ricavi il valore, copiata, al massimo \
25 parole
- scadenza: data ULTIMA per presentare DOMANDA, formato AAAA-MM-GG
- a_sportello: true se non c'e' una scadenza competitiva ma si presenta \
fino a esaurimento risorse
- pubblicato_il: data di pubblicazione del bando, formato AAAA-MM-GG. \
Aggiungi la chiave "origine": "pubblicazione" se il testo indica la \
pubblicazione (es. sul BURT), "atto" se usi la data dell'atto che approva \
il bando perche' la pubblicazione non e' indicata
- beneficiari: la frase del bando che definisce chi puo' presentare domanda
- costo_min, costo_max: importo minimo e massimo del PROGETTO ammissibile
- contributo_perc: percentuale massima di contributo, solo il numero
- contributo_min, contributo_max: importo minimo e massimo del CONTRIBUTO
- dotazione: dotazione finanziaria complessiva del bando

CAMPI SEMPLICI
Per questi campi produci solo il valore, oppure null:
- titolo: il titolo completo del bando
- ente: chi emana il bando
- tema: una sola parola tra commercio, casa, ambiente, formazione, \
istruzione, cultura, territorio, mobilita, agricoltura, turismo, pesca, sociale
- programma: il programma di finanziamento, es. PR FESR 2021-2027
- apertura: data di apertura delle domande, formato AAAA-MM-GG
- scadenza_nota: proroghe, orari, condizioni sulla scadenza
- territorio: ambito territoriale ammissibile
- premialita: criteri che assegnano punteggio aggiuntivo
- riferimento_atto: decreto o delibera che approva il bando

BENEFICIARI AMMESSI
"beneficiari_ammessi": un elenco, un elemento per ogni soggetto che il \
bando ammette a presentare domanda:
  {{"soggetto": "il soggetto come lo scrive il bando",
    "tipi": ["uno o piu' codici della lista sotto"],
    "condizioni": "le condizioni per essere ammesso, oppure null",
    "frase": "la frase del bando che lo dice, copiata esattamente",
    "confidenza": "alta", "media" o "bassa"}}
Tipi ammessi, SOLO questi codici:
{_elenco_tipi()}
Regole di corrispondenza:
{_elenco_termini()}
- "imprese" o "PMI" senza un settore comprende tutti e quattro i tipi di \
impresa; con un settore, solo quello
Quando due tipi si sovrappongono vale il piu' specifico: una scuola statale \
e' ricerca_formazione, una cooperativa sociale e' terzo_settore.
Se il bando definisce chi partecipa con un requisito e non con un tipo di \
soggetto (es. "i musei accreditati", "i titolari di"), usa \
{PER_REQUISITO} e scrivi il requisito nelle condizioni. Non dedurre un \
tipo che il bando non nomina.
Condizioni: tutto cio' che restringe l'ammissione di quel soggetto \
(es. "fino a 5.000 abitanti", "in forma associata", "titolare di museo \
accreditato", "competente per il servizio").

INTERVENTI E SPESE AMMISSIBILI
"interventi": un elenco, un elemento per ogni intervento o spesa ammessa:
  {{"genere": "intervento" oppure "spesa", "descrizione": "in breve", \
"frase": "la frase del bando, copiata esattamente"}}
Elenco vuoto se il testo non li descrive.

CUMULABILITA'
"cumulabilita": {{"clausola": "cosa dice il bando sul cumulo con altri \
finanziamenti, oppure null", "frase": "la frase del bando, copiata"}}

REGOLE CRITICHE

1. FRASI. Ogni "frase" e ogni "prova" va copiata dal testo, parola per \
parola: viene cercata nella pagina, e se non si trova il dato viene scartato.

2. SCADENZA. Cerca la data entro cui si presenta la DOMANDA, non quella di \
rendicontazione o di conclusione lavori. Se il testo segnala una proroga, \
usa la data prorogata e spiega in scadenza_nota. Se il campo strutturato \
della pagina contraddice il testo, fidati del TESTO e segnala la \
discrepanza in scadenza_nota, con confidenza "bassa".

3. BENEFICIARI. Decidi leggendo il paragrafo sui beneficiari, MAI il tag \
della pagina, che e' spesso sbagliato. Un soggetto che partecipa solo come \
partner, o che raccoglie domande altrui senza essere beneficiario, non e' \
un beneficiario ammesso.

4. IMPORTI. Sono quattro grandezze diverse e non vanno confuse: \
la dotazione complessiva del bando, il costo del singolo progetto, \
il contributo concedibile, la percentuale. Se non distingui con certezza, \
usa null e confidenza "bassa".

5. Se un dato non e' nel testo, usa null. NON dedurre, NON completare con \
conoscenze tue."""

MODELLO_PROMPT = ChatPromptTemplate.from_messages(
    [
        # Le parentesi graffe del testo vanno raddoppiate: il modello del
        # prompt le leggerebbe come variabili
        ("system", ISTRUZIONI.replace("{", "{{").replace("}", "}}")),
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


@dataclass
class Estrazione:
    """Cio' che il modello ha estratto da una pagina, prima della verifica."""

    campi: list[Campo]
    natura: str | None = None
    natura_motivo: str = ""
    natura_prova: str = ""
    pubblicato_origine: str | None = None
    beneficiari: list = field(default_factory=list)
    interventi: list = field(default_factory=list)
    cumulabilita: dict | None = None


def costruisci_estrattore():
    """Catena che estrae i campi di un bando."""
    modello = ChatAnthropic(
        model=MODEL_NAME,
        max_tokens=8192,
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


def _confidenza(valore) -> str:
    return valore if valore in ("alta", "media", "bassa") else "bassa"


def interpreta(dati: dict) -> Estrazione:
    """Trasforma il JSON del modello in un'Estrazione, senza verificarla."""
    campi = []
    for nome, (_, critico, con_prova) in CAMPI.items():
        voce = dati.get(nome)

        if isinstance(voce, dict):
            valore = voce.get("valore")
            confidenza = _confidenza(voce.get("confidenza"))
            prova = voce.get("prova") or ""
        elif voce is None:
            valore, confidenza, prova = None, "bassa", "campo assente"
        elif con_prova:
            # Il modello ha restituito il valore nudo invece dell'oggetto:
            # lo accettiamo ma abbassiamo la confidenza.
            valore, confidenza, prova = voce, "bassa", "formato non conforme"
        else:
            # Campo semplice: il valore nudo e' il formato richiesto
            valore, confidenza, prova = voce, "alta", ""

        campi.append(Campo(nome, valore, confidenza, prova, critico))

    natura = dati.get("natura")
    if not isinstance(natura, dict):
        natura = {"valore": natura}

    pubblicato = dati.get("pubblicato_il")
    origine = pubblicato.get("origine") if isinstance(pubblicato, dict) else None

    cumulabilita = dati.get("cumulabilita")

    return Estrazione(
        campi=campi,
        natura=natura.get("valore"),
        natura_motivo=natura.get("motivo") or "",
        natura_prova=natura.get("prova") or "",
        pubblicato_origine=origine,
        beneficiari=dati.get("beneficiari_ammessi") or [],
        interventi=dati.get("interventi") or [],
        cumulabilita=cumulabilita if isinstance(cumulabilita, dict) else None,
    )


def estrai(estrattore, testo: str, debug: bool = False) -> Estrazione:
    """Estrae i dati dal testo della pagina, con confidenza e prove."""
    grezzo = estrattore.invoke({"testo": testo})

    try:
        dati = json.loads(pulisci_json(grezzo))
    except json.JSONDecodeError as errore:
        raise ValueError(
            f"Risposta non interpretabile come JSON: {errore}\n{grezzo[:300]}"
        ) from errore

    if debug:
        print("--- JSON GREZZO ---")
        print(json.dumps(dati, indent=2, ensure_ascii=False)[:4000])
        print("--- fine ---\n")

    return interpreta(dati)


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


def _valida_beneficiari(
    voci: list, testo: str, problemi: list[str], avvisi: list[str]
) -> list[dict]:
    """Le righe di beneficiari_bando ricavate dall'elenco del modello.

    Per ogni soggetto: i tipi devono essere della lista chiusa (altrimenti
    e' un problema); la frase deve comparire nella pagina (altrimenti il
    soggetto si scarta con un avviso); le regole di corrispondenza
    aggiungono i tipi mancanti, con un avviso. Si produce una riga per
    tipo; due soggetti con lo stesso tipo e la stessa frase si fondono.
    """
    righe: dict[tuple[str, str], dict] = {}

    for numero, voce in enumerate(voci, start=1):
        if not isinstance(voce, dict):
            avvisi.append(f"beneficiario {numero}: formato non conforme, scartato")
            continue

        soggetto = (voce.get("soggetto") or "").strip()
        frase = (voce.get("frase") or "").strip()
        condizioni = (voce.get("condizioni") or "").strip() or None
        tipi = voce.get("tipi") or []
        if isinstance(tipi, str):
            tipi = [tipi]
        nome = soggetto or f"beneficiario {numero}"

        fuori_lista = [t for t in tipi if t not in TIPI_BENEFICIARIO]
        if fuori_lista:
            problemi.append(
                f"beneficiari_ammessi: tipi fuori dalla lista per '{nome}': "
                f"{', '.join(map(str, fuori_lista))}"
            )
            continue

        if not frase_nel_testo(frase, testo):
            avvisi.append(
                f"beneficiario '{nome}': frase non trovata nella pagina, "
                f"scartato ('{frase[:80]}')"
            )
            continue

        aggiunti = sorted(tipi_da_termini(soggetto or frase) - set(tipi))
        if aggiunti:
            avvisi.append(
                f"beneficiario '{nome}': aggiunti {', '.join(aggiunti)} "
                "per le regole di corrispondenza"
            )
            tipi = [*tipi, *aggiunti]

        if not tipi:
            avvisi.append(f"beneficiario '{nome}': nessun tipo indicato, scartato")
            continue

        for tipo in dict.fromkeys(tipi):
            if tipo == PER_REQUISITO and not condizioni:
                avvisi.append(
                    f"beneficiario '{nome}': {PER_REQUISITO} senza condizioni, scartato"
                )
                continue

            chiave = (tipo, frase)
            if chiave in righe:
                esistente = righe[chiave]
                if condizioni and condizioni != esistente["condizioni"]:
                    esistente["condizioni"] = "; ".join(
                        c for c in (esistente["condizioni"], condizioni) if c
                    )
                continue

            righe[chiave] = {
                "tipo": tipo,
                "soggetto": soggetto or None,
                "condizioni": condizioni,
                "frase": frase,
                "confidenza": _confidenza(voce.get("confidenza")),
                "origine": "estrazione",
            }

    return list(righe.values())


def _valida_interventi(voci: list, testo: str, avvisi: list[str]) -> list[dict]:
    """Gli interventi con genere valido e frase presente nella pagina."""
    validi = []
    for numero, voce in enumerate(voci, start=1):
        if not isinstance(voce, dict):
            avvisi.append(f"intervento {numero}: formato non conforme, scartato")
            continue

        genere = voce.get("genere")
        descrizione = (voce.get("descrizione") or "").strip()
        frase = (voce.get("frase") or "").strip()

        if genere not in ("intervento", "spesa") or not descrizione:
            avvisi.append(
                f"intervento {numero}: genere o descrizione mancanti, scartato"
            )
            continue

        if not frase_nel_testo(frase, testo):
            avvisi.append(
                f"intervento '{descrizione[:50]}': frase non trovata nella pagina, scartato"
            )
            continue

        validi.append(
            {
                "numero": len(validi) + 1,
                "genere": genere,
                "descrizione": descrizione,
                "frase": frase,
            }
        )
    return validi


def _valida_cumulabilita(
    voce: dict | None, testo: str, avvisi: list[str]
) -> tuple[str | None, str | None]:
    """La clausola di cumulabilita' e la sua frase, se verificata."""
    if not voce or not (voce.get("clausola") or "").strip():
        return None, None

    clausola = voce["clausola"].strip()
    frase = (voce.get("frase") or "").strip()

    if not frase_nel_testo(frase, testo):
        avvisi.append("cumulabilita: frase non trovata nella pagina, lasciata vuota")
        return None, None

    return clausola, frase


def valida(estrazione: Estrazione, testo: str) -> tuple[dict, list[str], list[str]]:
    """Converte l'estrazione in una riga per il database e la verifica.

    Restituisce (riga, problemi, avvisi). I problemi impediscono il
    salvataggio: natura non riconosciuta, un campo bloccante mancante o
    non convertibile, un tipo fuori lista, nessun beneficiario verificato.
    Gli avvisi no: un campo non bloccante che non si converte, o una voce
    la cui frase non compare nella pagina, resta vuoto e l'avviso
    conserva il valore originale per chi lo rivede.

    Le frasi si controllano su testo, la pagina da cui si e' estratto.
    La riga contiene anche beneficiari_ammessi e interventi, gia'
    verificati, che salva() scrive nelle rispettive tabelle.
    """
    riga = {
        "natura": estrazione.natura,
        "natura_motivo": estrazione.natura_motivo,
    }
    problemi = []
    avvisi = []

    if estrazione.natura not in NATURE:
        problemi.append(
            f"natura: valore '{estrazione.natura}' non riconosciuto (bando o non_bando)"
        )
        return riga, problemi, avvisi

    # Una pagina che non e' un bando si scarta senza guardare il resto
    if estrazione.natura == "non_bando":
        return riga, problemi, avvisi

    for c in estrazione.campi:
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

    if riga.get("a_sportello") is None:
        riga["a_sportello"] = 0

    riga["pubblicato_origine"] = None
    if riga.get("pubblicato_il"):
        if estrazione.pubblicato_origine in ORIGINI_PUBBLICAZIONE:
            riga["pubblicato_origine"] = estrazione.pubblicato_origine
        else:
            avvisi.append(
                f"pubblicato_il: origine '{estrazione.pubblicato_origine}' "
                "non riconosciuta, lasciata vuota"
            )

    riga["beneficiari_ammessi"] = _valida_beneficiari(
        estrazione.beneficiari, testo, problemi, avvisi
    )
    if not riga["beneficiari_ammessi"]:
        problemi.append("beneficiari_ammessi: nessun beneficiario con frase verificata")

    riga["interventi"] = _valida_interventi(estrazione.interventi, testo, avvisi)

    riga["cumulabilita"], riga["cumulabilita_frase"] = _valida_cumulabilita(
        estrazione.cumulabilita, testo, avvisi
    )

    return riga, problemi, avvisi


def decidi_automatico(estrazione: Estrazione, riga: dict) -> tuple[bool, str]:
    """Decide se salvare senza conferma umana.

    Si scarta solo cio' che non e' un bando o e' scaduto (scarti
    definitivi), oppure la cui scadenza e' incerta (scarti da rivedere).
    Il tipo di beneficiario non e' mai motivo di scarto: si filtra al
    momento della domanda.

    Un bando a sportello si salva anche senza data di chiusura; se ha una
    data di chiusura gia' passata, e' scaduto.
    """
    if estrazione.natura == "non_bando":
        motivo = f": {estrazione.natura_motivo}" if estrazione.natura_motivo else ""
        return False, f"{NON_BANDO}{motivo}"

    scadenza = riga.get("scadenza")
    if scadenza and scadenza < date.today().isoformat():
        return False, f"scaduto il {scadenza}"

    if riga.get("a_sportello") == 1:
        return True, f"a sportello fino al {scadenza}" if scadenza else "a sportello"

    if not scadenza:
        return False, "scadenza non determinata"

    campo_scadenza = next((c for c in estrazione.campi if c.nome == "scadenza"), None)
    if campo_scadenza and campo_scadenza.confidenza == "bassa":
        return False, f"scadenza {scadenza} a bassa confidenza"

    return True, f"aperto fino al {scadenza}"
