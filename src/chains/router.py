"""Instrada la domanda verso i documenti, il database, o entrambi."""

import json
import re

from langchain_anthropic import ChatAnthropic
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
usa bandi_per_beneficiario con il codice del tipo. Per chi vuole avviare \
o gestire un'impresa senza un settore preciso usa altra_impresa; non \
esistono codici per genere, età o fase dell'impresa.

Quando la domanda nomina un bando preciso, per titolo, per nome proprio \
o per il suo oggetto ("il bando per i mercati rionali"), usa \
dettaglio_bando con le parole distintive del titolo come id_bando, e metti \
"documenti": true. Non usare bandi_per_tema per un bando nominato: il tema \
in archivio è una categoria generale (commercio, ambiente...) e non \
contiene le parole del titolo. bandi_per_tema serve solo per le domande \
generiche su un argomento ("ci sono bandi per il commercio?").
Se la domanda nomina l'ente che emette il bando (MIT, Ministero, Regione, \
GAL, ICS, Invitalia...), quel nome non va in id_bando: i titoli dei bandi \
non lo contengono. "Il fondo strade MIT per i piccoli comuni" diventa \
id_bando "fondo strade piccoli comuni".

ESEMPI
"Quanti abitanti ha il comune?"
{{"documenti": false, "interrogazioni": [{{"nome": "popolazione_ultima", "parametri": {{}}}}]}}

"Ci sono bandi aperti per le aziende agricole del territorio?"
{{"documenti": false, "interrogazioni": [{{"nome": "bandi_per_beneficiario", "parametri": {{"tipo": "impresa_agricola"}}}}]}}

"Vorrei avviare una nuova attività: ci sono contributi?"
{{"documenti": false, "interrogazioni": [{{"nome": "bandi_per_beneficiario", "parametri": {{"tipo": "altra_impresa"}}}}]}}

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


# Con claude-sonnet-5 il ragionamento adattivo è attivo quando il parametro
# thinking manca, e i suoi token contano nel tetto. Con 512, il 14 novembre
# 2026 una domanda del lotto 1 ha esaurito il tetto tre volte su tre senza
# scrivere il JSON (docs/piano-correzioni-lotto1.md, correzione 1). Il
# ragionamento non si spegne con thinking disabled: claude-sonnet-5-5 lo
# rifiuta, e il modello si cambia dal .env.
MAX_TOKENS_ROUTER = 2048


def costruisci_router():
    """Catena che decide dove cercare.

    Restituisce il messaggio intero del modello, non solo il testo: decidi
    ne legge anche lo stop_reason.
    """
    modello = ChatAnthropic(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS_ROUTER,
        timeout=60,
    )
    return MODELLO_ROUTER | modello


def testo_e_fine(risposta) -> tuple[str, str | None]:
    """Il testo della risposta del router e il suo stop_reason.

    Di un messaggio del modello si prendono solo i blocchi di testo, senza
    quelli di ragionamento, e lo stop_reason dai metadati. Una stringa (i
    router finti dei test) è il testo, con stop_reason sconosciuto.
    """
    if isinstance(risposta, str):
        return risposta, None
    metadati = getattr(risposta, "response_metadata", None) or {}
    return risposta.text, metadati.get("stop_reason")


def estrai_decisione(testo: str) -> dict | None:
    """La decisione del router nel suo testo, anche con testo intorno.

    Si prova a leggere un oggetto JSON da ogni "{" e si tengono quelli con
    "documenti" o "interrogazioni": le recinzioni ``` e il testo prima o
    dopo non contano. Una decisione sola, o più copie identiche, è la
    risposta. Nessuna, o più decisioni diverse, dà None: la risposta non si
    interpreta, invece di sceglierne una a caso.
    """
    lettore = json.JSONDecoder()
    trovate: list[dict] = []
    for m in re.finditer(r"\{", testo):
        try:
            oggetto, _ = lettore.raw_decode(testo, m.start())
        except json.JSONDecodeError:
            continue
        if not isinstance(oggetto, dict):
            continue
        if "documenti" not in oggetto and "interrogazioni" not in oggetto:
            continue
        if oggetto not in trovate:
            trovate.append(oggetto)
    return trovate[0] if len(trovate) == 1 else None


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
    """Restituisce la decisione, con un ripiego sicuro in caso di errore.

    Il ripiego cerca nei documenti, senza interrogazioni. La decisione in
    errore conserva il motivo, lo stop_reason e il testo grezzo: servono
    alla diagnosi, non all'utente, a cui l'app mostra una riga neutra. Con
    una decisione valida lo stop_reason si aggiunge quando è noto.
    """
    risposta = router.invoke(
        {
            "domanda": domanda,
            "repertorio": descrivi_repertorio(),
            "stato": stato_archivio(codice_ente),
            "profilo": descrivi_profilo(profilo),
        }
    )

    grezzo, stop_reason = testo_e_fine(risposta)
    decisione = estrai_decisione(grezzo)
    if decisione is None:
        return {
            "documenti": True,
            "interrogazioni": [],
            "errore": "risposta del router non interpretabile",
            "stop_reason": stop_reason,
            "grezzo": grezzo,
        }

    decisione.setdefault("documenti", True)
    decisione.setdefault("interrogazioni", [])
    if stop_reason is not None:
        decisione["stop_reason"] = stop_reason
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
