"""Instrada la domanda verso i documenti, il database, o entrambi."""

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from src.config import ENTE_PREDEFINITO, MODEL_NAME, PROFILO_ENTE
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
come "possiamo partecipare a qualche bando?" richiede bandi_aperti_per_comuni.

ESEMPI
"Quanti abitanti ha il comune?"
{{"documenti": false, "interrogazioni": [{{"nome": "popolazione_ultima", "parametri": {{}}}}]}}

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


def descrivi_profilo() -> str:
    """Il profilo dell'ente in forma testuale, per il prompt."""
    righe = []
    for chiave, valore in PROFILO_ENTE.items():
        if valore is None:
            righe.append(f"- {chiave}: non verificato")
        elif isinstance(valore, bool):
            righe.append(f"- {chiave}: {'sì' if valore else 'no'}")
        else:
            righe.append(f"- {chiave}: {valore}")
    return "\n".join(righe)


def decidi(router, domanda: str) -> dict:
    """Restituisce la decisione, con un ripiego sicuro in caso di errore."""
    grezzo = router.invoke(
        {
            "domanda": domanda,
            "repertorio": descrivi_repertorio(),
            "stato": stato_archivio(ENTE_PREDEFINITO),
            "profilo": descrivi_profilo(),
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


def esegui_interrogazioni(decisione: dict) -> list:
    """Esegue le interrogazioni indicate dal router."""
    esiti = []
    for richiesta in decisione.get("interrogazioni", []):
        nome = richiesta.get("nome", "")
        parametri = richiesta.get("parametri") or {}
        esiti.append((nome, esegui(nome, parametri, ENTE_PREDEFINITO)))
    return esiti


def formatta_dati(esiti: list) -> str:
    """Trasforma gli esiti in un blocco di testo per il prompt principale."""
    if not esiti:
        return ""

    blocchi = []
    for numero, (nome, risultato) in enumerate(esiti, start=1):
        fonti = "; ".join(risultato.fonti) if risultato.fonti else "nessuna"
        blocchi.append(
            f"[D{numero}] interrogazione: {nome} | fonte: {fonti}\n{risultato.testo}"
        )

    return "\n\n".join(blocchi)
