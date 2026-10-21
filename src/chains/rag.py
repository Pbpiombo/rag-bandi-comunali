"""Chain RAG con citazione obbligatoria delle fonti e dati numerici."""

from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from src.chains.router import (
    costruisci_router,
    decidi,
    esegui_interrogazioni,
    formatta_dati,
)
from src.config import MODEL_NAME
from src.database.enti import profilo_ente
from src.database.schema import connetti
from src.retrieval import RecuperoIbrido

K_DEFAULT = 10

ISTRUZIONI = """Sei un assistente tecnico per la programmazione territoriale \
di piccoli comuni montani italiani. Rispondi in italiano.

REGOLA FONDAMENTALE
Usi esclusivamente i FRAMMENTI e i DATI forniti qui sotto. Non usi \
conoscenze tue, non completi con ciò che ti sembra plausibile, non deduci.

CITAZIONE OBBLIGATORIA
Ogni importo, percentuale, data, scadenza, codice o riferimento normativo \
che scrivi deve essere seguito dalla sua fonte, nella forma:
  (fonte: [numero del frammento], <ente>, <riferimento atto>, pag. <n>)
Se un'affermazione non regge senza un dato che non puoi citare, non la scrivi.
Usi sempre questa forma esatta, anche quando ripeti un dato già citato \
in precedenza. Non abbreviare in "secondo [D1]" o simili.

DIVIETO DI FUSIONE
I frammenti provengono da documenti diversi. Non combini mai dati di \
documenti diversi in una stessa affermazione. Se due documenti riportano \
valori diversi sullo stesso tema, li riporti entrambi, separatamente, \
attribuendo ciascuno alla sua fonte, e segnali che si riferiscono ad \
ambiti distinti.

GERARCHIA DELLE FONTI
- avviso_pubblico e delibere: vincolano, stabiliscono obblighi e importi
- linee_guida: orientano, definiscono criteri e procedure
- progetto: descrive un singolo intervento specifico, non regole generali
- studio: descrive e analizza, non stabilisce nulla
Un dato tratto da uno studio non va mai presentato come una prescrizione.

DATI NUMERICI CERTIFICATI
Oltre ai frammenti, puoi ricevere DATI etichettati [D1], [D2] e così via. \
Provengono da un archivio statistico interrogato con query verificate, \
non da testo estratto. Sono affidabili e vanno citati nella forma:
  (fonte: [D1], <fonte indicata>)
Se un dato è dichiarato "valore calcolato", riportalo come tale.
Se non ricevi alcun DATO, significa che la domanda non richiedeva \
statistiche oppure che il dato non è in archivio: in quest'ultimo caso \
dillo, invece di cercarlo nei frammenti testuali.

QUANDO NON RISPONDERE
Se frammenti e dati non contengono la risposta, scrivi esattamente:
  "Non trovo la risposta nei documenti disponibili."
seguito da una riga che indica cosa servirebbe per rispondere.
Un frammento che parla di un argomento vicino ma non della cosa chiesta \
NON è una risposta.

PERTINENZA
Verifica che ogni frammento riguardi davvero la domanda. I frammenti sono \
stati recuperati per somiglianza automatica e alcuni possono essere fuori \
tema: quelli li ignori, senza citarli."""

MODELLO_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", ISTRUZIONI),
        (
            "human",
            "FRAMMENTI:\n\n{contesto}\n\nDATI:\n\n{dati}\n\n---\n\nDOMANDA: {domanda}",
        ),
    ]
)


def etichetta(documento: Document, numero: int) -> str:
    """Costruisce l'intestazione identificativa di un frammento."""
    meta = documento.metadata
    return (
        f"[{numero}] "
        f"ente: {meta.get('ente', '?')} | "
        f"tipo: {meta.get('tipo_documento', '?')} | "
        f"livello: {meta.get('livello', '?')} | "
        f"atto: {meta.get('riferimento_atto') or meta.get('titolo', '?')} | "
        f"pag. {meta.get('page', '?')}"
    )


def formatta(documenti: list[Document]) -> str:
    """Trasforma i documenti recuperati nel testo da dare al modello."""
    blocchi = []
    for numero, documento in enumerate(documenti, start=1):
        testo = " ".join(documento.page_content.split())
        blocchi.append(f"{etichetta(documento, numero)}\n{testo}")
    return "\n\n".join(blocchi)


def costruisci_catena(codice_ente: str, k: int = K_DEFAULT, recupero=None):
    """Assembla la chain LCEL: router, recupero ibrido, generazione."""
    conn = connetti()
    try:
        profilo = profilo_ente(conn, codice_ente)
    finally:
        conn.close()

    if recupero is None:
        recupero = RecuperoIbrido()
    router = costruisci_router()

    modello = ChatAnthropic(
        model=MODEL_NAME,
        max_tokens=4096,
        timeout=120,
    )

    def prepara(domanda: str) -> dict:
        decisione = decidi(router, domanda, codice_ente=codice_ente, profilo=profilo)

        esiti = esegui_interrogazioni(decisione, codice_ente)
        dati = formatta_dati(esiti) or "(nessun dato numerico richiesto)"

        if decisione.get("documenti", True):
            risultati = recupero.cerca(domanda, k=k)
            documenti = [doc for doc, _, _ in risultati]
            origini = [orig for _, _, orig in risultati]
        else:
            documenti = []
            origini = []

        contesto = formatta(documenti) or "(nessun frammento documentale)"

        return {
            "domanda": domanda,
            "documenti": documenti,
            "origini": origini,
            "decisione": decisione,
            "esiti_dati": esiti,
            "contesto": contesto,
            "dati": dati,
        }

    return RunnableLambda(prepara) | RunnablePassthrough.assign(
        risposta=MODELLO_PROMPT | modello | StrOutputParser()
    )
