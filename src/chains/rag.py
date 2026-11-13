"""Chain RAG con citazione obbligatoria delle fonti e dati numerici."""

from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from src.chains.router import (
    costruisci_router,
    decidi,
    descrivi_profilo,
    esegui_interrogazioni,
    formatta_dati,
)
from src.config import MODEL_NAME
from src.database.enti import profilo_ente
from src.database.interrogazioni_bandi import data_di_oggi
from src.database.repertorio import esegui
from src.database.schema import connetti
from src.database.stato_documenti import con_stato_bando
from src.recupero_documenti import avvolgi
from src.retrieval import RecuperoIbrido, normalizza_domanda

K_DEFAULT = 10

# Il nome del blocco dei dati con la popolazione aggiunta dal programma: lo
# stesso che il prompt indica al modello
BLOCCO_POPOLAZIONE = "popolazione dell'ente (aggiunta dal programma)"


def recupera(recupero, domanda: str, k: int = K_DEFAULT) -> list:
    """La ricerca dei frammenti come la fa la catena: domanda normalizzata.

    È l'unico punto da cui la catena cerca; la usa anche
    scripts/diagnostica/prova_recupero.py, per misurare lo stesso percorso.
    """
    return recupero.cerca(normalizza_domanda(domanda), k=k)


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
Negli elenchi di bandi ogni bando ha la sua etichetta: [D1.1], [D1.2] e \
così via, all'inizio della sua riga. Un dato di un bando (scadenza, \
importo, percentuale, decreto) si cita con l'etichetta di QUEL bando e con \
l'atto scritto nella sua riga dopo "atto:":
  (fonte: [D1.2], <atto del bando>)
Non citare con [D1] un dato che appartiene a un solo bando, e non \
attribuire a un bando l'atto di un altro.
Non scrivere indirizzi web: i collegamenti ai bandi citati li mostra l'app.
Se un dato è dichiarato "valore calcolato", riportalo come tale.
Se scrivi la data dell'archivio o di oggi, citala con l'etichetta del \
blocco dei dati che la riporta, come ogni altro dato; se non serve alla \
risposta, non scriverla.
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
tema: quelli li ignori, senza citarli.

ENTE PER CUI RISPONDI
Ricevi il profilo dell'ente che pone la domanda: tipo, area interna, se è \
capofila, se rientra in Toscana Diffusa. Usalo per valutare se l'ente \
rientra tra i beneficiari di un bando. Quando lo usi, citalo nella forma \
(fonte: profilo dell'ente). Un dato "non verificato" non è né sì né no: \
dillo, invece di dedurlo.
La popolazione dell'ente non è nel profilo: è nei DATI, nel blocco \
"popolazione dell'ente". Quando un bando ha una soglia o delle fasce di \
abitanti, confrontala con quel dato e citalo con la sua etichetta. Se il \
blocco non c'è, la popolazione dell'ente non è disponibile: dillo, senza \
stimarla e senza sommare quella dei comuni.
Nel confronto ci sono due dati di due fonti diverse: la soglia si cita \
con l'etichetta del bando e la popolazione con quella del suo blocco, \
ciascuna subito dopo il proprio numero. Mai una sola citazione per tutti \
e due. Esempio, con il bando in [D1.3] e la popolazione in [D2]:
  Il bando ammette i comuni fino a 5.000 abitanti (fonte: [D1.3], <atto \
del bando>); il Comune ne ha 1.834 (fonte: [D2], <fonte indicata>), \
quindi rientra nella soglia.

BENEFICIARI DEI BANDI
Se un bando indica "ammesso se ...", l'ente è ammesso a condizione: \
riporta la condizione, non rispondere con un semplice sì. Se indica \
"beneficiari non ancora classificati", non sai se l'ente è ammesso: dillo \
e invita a verificare sul bando. Un bando "a sportello" resta aperto \
finché ci sono risorse: riporta l'invito a verificarne la disponibilità.
Gli elenchi di bandi contengono solo i bandi con i dati essenziali: \
quelli con la scadenza o i beneficiari non indicati li mostra l'app a \
parte, sotto la risposta. Non dire che non esistono altri bandi: di' che \
sono quelli in archivio con dati completi.

STATO DEL BANDO NEI FRAMMENTI
Se l'intestazione di un frammento riporta "stato del bando", lo stato è \
calcolato alla data indicata e vale più del testo del frammento, che non \
sa di essere scaduto. Un bando scaduto non si presenta come opportunità \
attuale: se ne riporta il contenuto insieme allo stato, citato con la \
fonte del frammento."""

MODELLO_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", ISTRUZIONI),
        (
            "human",
            (
                "ENTE PER CUI RISPONDI:\n\n{profilo}\n\n"
                "FRAMMENTI:\n\n{contesto}\n\nDATI:\n\n{dati}\n\n---\n\nDOMANDA: {domanda}"
            ),
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
    ) + (
        f" | stato del bando: {meta['stato_bando']}" if meta.get("stato_bando") else ""
    )


def formatta(documenti: list[Document]) -> str:
    """Trasforma i documenti recuperati nel testo da dare al modello."""
    blocchi = []
    for numero, documento in enumerate(documenti, start=1):
        testo = " ".join(documento.page_content.split())
        blocchi.append(f"{etichetta(documento, numero)}\n{testo}")
    return "\n\n".join(blocchi)


def con_stato_del_giorno(documenti: list[Document]) -> list[Document]:
    """I documenti con lo stato del loro bando, calcolato alla data di oggi."""
    conn = connetti()
    try:
        return con_stato_bando(documenti, conn, data_di_oggi().isoformat())
    finally:
        conn.close()


def con_popolazione(esiti: list, codice_ente: str) -> list:
    """Gli esiti del router, con la popolazione dell'ente se manca.

    La aggiunge il programma, non il modello, a ogni domanda: serve a
    confrontare l'ente con le soglie di abitanti dei bandi. Arriva come un
    blocco di dati con fonte e anno, che il verificatore controlla come gli
    altri. Non si aggiunge se il router l'ha gia' chiesta, ne' per un ente
    senza dati di popolazione (l'Unione).
    """
    if any(nome.startswith("popolazione") for nome, _ in esiti):
        return esiti
    risultato = esegui("popolazione_ultima", {}, codice_ente)
    if not risultato.trovato:
        return esiti
    return [*esiti, (BLOCCO_POPOLAZIONE, risultato)]


def costruisci_catena(codice_ente: str, k: int = K_DEFAULT, recupero=None):
    """Assembla la chain LCEL: router, recupero ibrido, generazione."""
    conn = connetti()
    try:
        profilo = profilo_ente(conn, codice_ente)
    finally:
        conn.close()

    if recupero is None:
        recupero = RecuperoIbrido()
    # Se la domanda nomina un documento, si cerca anche dentro quel documento
    # (P2). Ricollegata il 12 novembre 2026 dopo la prova su 15 domande e
    # su 5 di controllo, in quattro forme, con la domanda normalizzata:
    # scripts/diagnostica/prova_recupero.py.
    recupero = avvolgi(recupero)
    router = costruisci_router()

    modello = ChatAnthropic(
        model=MODEL_NAME,
        max_tokens=4096,
        timeout=120,
    )

    def prepara(domanda: str) -> dict:
        decisione = decidi(router, domanda, codice_ente=codice_ente, profilo=profilo)

        esiti = con_popolazione(
            esegui_interrogazioni(decisione, codice_ente), codice_ente
        )
        dati = formatta_dati(esiti) or "(nessun dato numerico richiesto)"

        if decisione.get("documenti", True):
            risultati = recupera(recupero, domanda, k=k)
            documenti = con_stato_del_giorno([doc for doc, _, _ in risultati])
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
            "profilo": descrivi_profilo(profilo),
        }

    return RunnableLambda(prepara) | RunnablePassthrough.assign(
        risposta=MODELLO_PROMPT | modello | StrOutputParser()
    )
