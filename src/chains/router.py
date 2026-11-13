"""Instrada la domanda verso i documenti, il database, o entrambi."""

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.config import MODEL_NAME
from src.database.modelli import con_etichette
from src.database.repertorio import descrivi_repertorio, esegui, stato_archivio

ISTRUZIONI_ROUTER = """Devi decidere dove cercare la risposta a una domanda \
su un piccolo comune montano italiano.

Esistono due archivi.

ARCHIVIO DOCUMENTALE
Contiene il testo di avvisi pubblici, linee guida, delibere e studi. \
Risponde a domande su regole, requisiti, scadenze, importi di bandi, \
procedure, obblighi.

ARCHIVIO NUMERICO
Contiene dati statistici certificati, interrogabili solo tramite le \
interrogazioni predefinite elencate qui sotto:

{repertorio}

CONTENUTO EFFETTIVO DELL'ARCHIVIO NUMERICO
{stato}

Se la domanda riguarda una tabella segnalata come VUOTA, non indicare \
interrogazioni e non attivare i documenti: il dato non è disponibile in \
nessun archivio.

IL TUO COMPITO
Restituisci SOLO un oggetto JSON, senza testo prima o dopo, senza \
delimitatori di codice, con questa struttura:

{{"documenti": true/false, "interrogazioni": [{{"nome": "...", "parametri": {{}}}}]}}

Metti "documenti": true se la domanda riguarda regole, procedure o \
contenuti di atti.
Elenca una o più interrogazioni se la domanda riguarda dati numerici.
Puoi indicare entrambe le cose: alcune domande richiedono sia il contesto \
statistico sia le regole.
Se nessuna interrogazione del repertorio è adatta, lascia la lista vuota: \
NON inventare nomi di interrogazioni.

PER CHI STAI CERCANDO
{profilo}

Quando la domanda riguarda opportunità di finanziamento, bandi aperti, \
scadenze o ammissibilità, usa le interrogazioni sui bandi. Una domanda \
come "possiamo partecipare a qualche bando?" richiede bandi_aperti_per_ente: \
l'ente lo conosce il programma, non va indicato nei parametri. Per i bandi \
rivolti ad altri soggetti del territorio (imprese, associazioni, cittadini) \
usa bandi_per_beneficiario con il codice del tipo.

Quando la domanda nomina un bando preciso, per titolo, per nome proprio \
o per il suo oggetto ("il bando per i mercati rionali"), usa \
dettaglio_bando con le parole distintive del titolo come id_bando, e metti \
"documenti": true. Non usare bandi_per_tema per un bando nominato: il tema \
in archivio è una categoria generale (commercio, ambiente...) e non \
contiene le parole del titolo. bandi_per_tema serve solo per le domande \
generiche su un argomento ("ci sono bandi per il commercio?").

ESEMPI
"Quanti abitanti ha il comune?"
{{"documenti": false, "interrogazioni": [{{"nome": "popolazione_ultima", "parametri": {{}}}}]}}

"Ci sono bandi aperti per le aziende agricole del territorio?"
{{"documenti": false, "interrogazioni": [{{"nome": "bandi_per_beneficiario", "parametri": {{"tipo": "impresa_agricola"}}}}]}}

"Quanto si può ottenere dal bando per le aziende apistiche?"
{{"documenti": true, "interrogazioni": [{{"nome": "dettaglio_bando", "parametri": {{"id_bando": "aziende apistiche"}}}}]}}

"Quali sono i requisiti per accedere al bando?"
{{"documenti": true, "interrogazioni": []}}

"Il calo demografico giustifica la richiesta di fondi per le aree interne?"
{{"documenti": true, "interrogazioni": [{{"nome": "popolazione_variazione", "parametri": {{}}}}]}}"""

MODELLO_ROUTER = ChatPromptTemplate.from_messages(
    [
        ("system", ISTRUZIONI_ROUTER),
        ("human", "{domanda}"),
    ]
)


def costruisci_router():
    """Catena che decide dove cercare."""
    modello = ChatAnthropic(
        model=MODEL_NAME,
        max_tokens=512,
        timeout=60,
    )
    return MODELLO_ROUTER | modello | StrOutputParser()


def pulisci_json(testo: str) -> str:
    """Toglie eventuali delimitatori di codice attorno al JSON."""
    testo = testo.strip()
    if testo.startswith("```"):
        righe = [r for r in testo.splitlines() if not r.strip().startswith("```")]
        testo = "\n".join(righe)
    return testo.strip()


def descrivi_profilo(profilo: dict) -> str:
    """Il profilo dell'ente in forma testuale, per il prompt."""
    righe = []
    for chiave, valore in profilo.items():
        if valore is None:
            righe.append(f"- {chiave}: non verificato")
        elif isinstance(valore, bool):
            righe.append(f"- {chiave}: {'sì' if valore else 'no'}")
        else:
            righe.append(f"- {chiave}: {valore}")
    return "\n".join(righe)


def decidi(router, domanda: str, codice_ente: str, profilo: dict) -> dict:
    """Restituisce la decisione, con un ripiego sicuro in caso di errore."""
    grezzo = router.invoke(
        {
            "domanda": domanda,
            "repertorio": descrivi_repertorio(),
            "stato": stato_archivio(codice_ente),
            "profilo": descrivi_profilo(profilo),
        }
    )

    try:
        decisione = json.loads(pulisci_json(grezzo))
    except json.JSONDecodeError:
        return {
            "documenti": True,
            "interrogazioni": [],
            "errore": f"risposta del router non interpretabile: {grezzo[:120]}",
        }

    decisione.setdefault("documenti", True)
    decisione.setdefault("interrogazioni", [])
    return decisione


def esegui_interrogazioni(decisione: dict, codice_ente: str) -> list:
    """Esegue le interrogazioni indicate dal router."""
    esiti = []
    for richiesta in decisione.get("interrogazioni", []):
        nome = richiesta.get("nome", "")
        parametri = richiesta.get("parametri") or {}
        esiti.append((nome, esegui(nome, parametri, codice_ente)))
    return esiti


def formatta_dati(esiti: list) -> str:
    """Trasforma gli esiti in un blocco di testo per il prompt principale."""
    if not esiti:
        return ""

    blocchi = []
    for numero, (nome, risultato) in enumerate(esiti, start=1):
        fonti = "; ".join(risultato.fonti) if risultato.fonti else "nessuna"
        # Le righe dei bandi prendono l'etichetta [Dn.k]: il modello cita
        # ogni dato con il bando a cui appartiene
        testo = con_etichette(risultato.testo, numero)
        blocchi.append(f"[D{numero}] interrogazione: {nome} | fonte: {fonti}\n{testo}")

    return "\n\n".join(blocchi)
