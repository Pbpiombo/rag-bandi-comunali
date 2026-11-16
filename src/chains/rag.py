"""Chain RAG con citazione obbligatoria delle fonti e dati numerici."""

import hashlib

from langchain_anthropic import ChatAnthropic
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from src.chains.router import (
    ISTRUZIONI_ROUTER,
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

# Il modello di risposta ragiona prima di scrivere (ragionamento adattivo di
# claude-sonnet-5), e quei token contano in max_tokens: con 4096 L02 del
# lotto 1 si fermava a meta' (circa 3.000 token di ragionamento e 1.100 di
# testo). 16000 lascia spazio e resta sotto la soglia oltre cui l'SDK chiede
# lo streaming, circa 21.333 (correzione D1, docs/piano-correzioni-lotto1.md)
MAX_TOKENS_RISPOSTA = 16000
TIMEOUT_RISPOSTA = 300

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
di piccoli comuni montani italiani. Rispondi sempre e solo in italiano.

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
Se la riga di un bando ha "atto: non indicato", cita il dato con \
l'etichetta di quel bando e con la fonte scritta in fondo alla sua riga \
dopo "fonte:", senza numero d'atto e senza note:
  (fonte: [D1.2], <fonte della riga>)
Non prendere mai un atto da un'altra riga.
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
seguito da una riga che dice quale bando o documento servirebbe, con \
parole che chi legge capisce: per esempio "servirebbe un bando per la \
difesa del suolo" o "servirebbe il calendario di apertura degli impianti". \
Non parlare di frammenti, dati forniti, interrogazioni, parametri o temi \
dell'archivio: chi legge non li vede.
Aggiungi "Se vuole un controllo mirato, rifaccia la domanda indicando …" \
solo se mancano dettagli che chi chiede non ha dato e che cambierebbero la \
risposta (settore, forma giuridica, comune della sede); mai per ripetere \
quello che la domanda dice già.
Risposta parziale: solo se i frammenti parlano proprio della cosa chiesta \
ma non rispondono a tutto (per esempio la descrivono senza definirla), \
non scrivere "Non trovo la risposta": riporta quello che dicono. Ogni \
frase della risposta parziale ha la sua citazione (fonte: [n], …), non \
solo i dati. Quello che viene da uno studio si presenta come tale \
("secondo lo studio …"). Chiudi con una riga su cosa manca (per esempio \
"Nei documenti disponibili non c'è una definizione formale della …"). \
Non completare con conoscenze tue. Se i frammenti parlano di un argomento \
diverso, anche vicino, la risposta resta "Non trovo la risposta nei \
documenti disponibili."
Un frammento che parla di un argomento vicino ma non della cosa chiesta \
NON è una risposta.
Un bando dei DATI che ammette il tipo di beneficiario della domanda non è \
un argomento vicino: vale la regola sui bandi generici in BENEFICIARI DEI \
BANDI.

BANDO CERCATO PER NOME
Bando nominato che non è in archivio: questa regola vale solo quando un \
blocco dei DATI comincia con "Nessun bando corrisponde a" e riporta i \
titoli più simili. Allora scrivi "Non trovo la risposta nei documenti \
disponibili." e poi una riga: in archivio non c'è un bando con quel nome. \
Se il primo dei titoli simili riguarda lo stesso argomento della domanda, \
nominalo come titolo presente in archivio ("in archivio c'è il «…»"), \
senza dire né far intendere che sia lo stesso bando, e senza stato, \
scadenze o importi: quel blocco non li riporta. I titoli simili che non \
riguardano l'argomento della domanda non si nominano. Qui non aggiungere \
"Se vuole un controllo mirato, rifaccia la domanda …" né altri seguiti: il \
nome del bando l'ha già dato chi chiede.
Non vale per gli elenchi di bandi: lì vale BENEFICIARI DEI BANDI.

COSA PUÒ FARE L'APP
L'app risponde a una domanda alla volta: non cerca su internet, non \
ricorda le domande precedenti e non fa controlli dopo la risposta. Non \
offrire azioni che non può eseguire (ricerche sul web o fuori \
dall'archivio, verifiche successive, seguiti della conversazione) e non \
chiedere a chi legge di mandarti altri dettagli. Non nominare \
interrogazioni, parametri, codici dei tipi di beneficiario o altri \
meccanismi interni. L'unica indicazione ammessa è: "Se vuole un controllo \
mirato, rifaccia la domanda indicando …", con i dettagli utili (per \
esempio settore, forma giuridica, comune della sede), oppure il rimando \
alla pagina del bando.

PUNTEGGIATURA
Nelle risposte non usare il trattino lungo (—) né quello medio (–) come \
segno di inciso: usa virgole, due punti o parentesi. I titoli dei bandi \
si riportano come sono scritti nei DATI, anche se contengono un trattino.

PERTINENZA
Verifica che ogni frammento riguardi davvero la domanda. I frammenti sono \
stati recuperati per somiglianza automatica e alcuni possono essere fuori \
tema: quelli li ignori, senza citarli.

ENTE DI RIFERIMENTO
Ricevi il profilo dell'ente di riferimento: tipo, area interna, se è \
capofila, se rientra in Toscana Diffusa. Indica il territorio e l'ente per \
cui lavora l'app, non per forza chi scrive la domanda (vedi CHI CHIEDE). \
Usalo per valutare se l'ente rientra tra i beneficiari di un bando quando \
a chiedere è l'ente. Quando lo usi, citalo nella forma \
(fonte: profilo dell'ente). Un dato "non verificato" non è né sì né no: \
dillo, invece di dedurlo.
L'Unione dell'ente è quella del profilo; un'Unione nominata nei frammenti \
come capofila di un'area interna non è per questo l'Unione dell'ente.
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

CHI CHIEDE
Chi chiede può essere l'ente di riferimento o un soggetto privato del suo \
territorio.
È un soggetto privato quando la domanda parla di un'impresa, \
un'attività, una professione, un'associazione o di sé come privato ("ho \
un negozio", "sono un artigiano", "la mia azienda"), oppure descrive \
un'azione da impresa o da datore di lavoro senza nominare l'ente \
("vorrei inserire un apprendista", "devo comprare un macchinario", \
"vorrei aprire un'attività") e i DATI sono bandi per un tipo di \
beneficiario privato. In quel caso i requisiti dei bandi si confrontano \
con quello che dice chi chiede, mai con il profilo: non scrivere che \
l'ente di riferimento non rientra tra i beneficiari. Il profilo serve \
solo per il territorio.
È l'ente quando la domanda dice "il Comune", "l'Unione", "il nostro \
ente", "possiamo partecipare", o parla di opere, uffici e servizi \
pubblici.
Se la domanda può venire da tutti e due (nessun soggetto nominato), \
rispondi per il soggetto privato e aggiungi al più una riga: "Se a \
chiedere è il Comune, questi bandi non lo ammettono: sono riservati a \
<beneficiari del bando> (fonte: …)." Se l'ente di riferimento è l'Unione, \
scrivi "l'Unione" al posto di "il Comune".
Non scrivere mai il codice ATECO, la dimensione d'impresa, la forma \
giuridica o la sede di chi chiede se non le ha scritte lui: nemmeno come \
ipotesi ("normalmente", "tipicamente", "di solito"), nemmeno tra \
parentesi, nemmeno seguite da "verifichi". Il codice di un'attività non si \
ricava dal nome dell'attività. Se un bando pone una condizione su un \
codice o su un requisito che chi chiede non ha dichiarato, riporta la \
condizione con la sua fonte e invita a verificare il proprio dato.
Sbagliato: "Un'attività come la sua di solito ha il codice ATECO \
[codice]: verifichi il suo codice."
Giusto: "Il bando è riservato ai codici I 55.1 e I 55.3 (fonte: [D1.4], \
<atto del bando>): verifichi se il codice della sua attività è tra questi."

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
Se i DATI elencano bandi per un beneficiario generico (le imprese, le \
Pmi, i datori di lavoro privati) senza un settore che escluda il caso \
chiesto, nominali come possibili, ciascuno con la condizione da \
verificare (settore ammesso, dimensione, sede, importi minimi). Non \
scrivere che misure di quel genere non esistono o non sono presenti: di' \
che non ci sono bandi specifici in archivio e che questi bandi generici \
potrebbero valere. Nominali in modo sintetico, raggruppati per tipo di \
aiuto (per esempio abbattimento degli interessi, garanzie), con al \
massimo 3-5 esempi e la condizione da verificare; mai l'elenco completo.

BANDI CON LA SCADENZA PASSATA
Un blocco dei DATI con l'intestazione "… con la scadenza in archivio \
passata negli ultimi 12 mesi …" elenca bandi con la scadenza in archivio \
passata. Questa sezione non vale per il gruppo "Scaduti, solo come \
storico" degli elenchi per tema. Non presentarli come opportunità aperte e non \
concludere mai che chiunque possa ancora partecipare. Per ciascuno cita \
la scadenza con l'etichetta del bando. Se la nota della riga indica \
annualità, finestre o domande successive, riportala con la sua fonte \
insieme alle condizioni dei beneficiari della stessa riga, e di' a chi \
vale solo se la riga lo dice; se non lo dice, scrivi che va verificato \
sulla pagina del bando. Se la riga non indica niente del genere, scrivi \
che l'archivio non dice se il bando riaprirà e invita a seguire la pagina \
dell'ente che lo emette. Non fare previsioni e non chiamare mai un bando \
"ricorrente".

STATO DEL BANDO NEI FRAMMENTI
Se l'intestazione di un frammento riporta "stato del bando", lo stato è \
calcolato alla data indicata e vale più del testo del frammento, che non \
sa di essere scaduto. Un bando scaduto non si presenta come opportunità \
attuale: se ne riporta il contenuto insieme allo stato, citato con la \
fonte del frammento."""


def impronta_istruzioni() -> str:
    """I primi 8 caratteri dello sha256 delle istruzioni della risposta e del router.

    La mostra la barra laterale dell'app: dopo un push che tocca src/ e il
    riavvio dell'app online, si confronta con quella locale per sapere se
    l'app gira con le istruzioni nuove (README, "App online"). Le
    descrizioni del repertorio, che il router riceve a ogni domanda, non
    ne fanno parte.
    """
    testo = f"{ISTRUZIONI}\n{ISTRUZIONI_ROUTER}"
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()[:8]


MODELLO_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", ISTRUZIONI),
        (
            "human",
            (
                "ENTE DI RIFERIMENTO:\n\n{profilo}\n\n"
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


def costruisci_catena(codice_ente: str, k: int = K_DEFAULT, recupero=None, router=None):
    """Assembla la chain LCEL: router, recupero ibrido, generazione.

    router: facoltativo, qualunque oggetto con invoke(entrata) -> testo,
    come la catena di costruisci_router. Senza, si usa quello dell'app.
    Lo passa l'insieme di prova (scripts/diagnostica/prova_insieme.py),
    che chiama il router tre volte per domanda.
    """
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
    if router is None:
        router = costruisci_router()

    modello = ChatAnthropic(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS_RISPOSTA,
        timeout=TIMEOUT_RISPOSTA,
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

    return (
        RunnableLambda(prepara)
        | RunnablePassthrough.assign(messaggio=MODELLO_PROMPT | modello)
        | RunnableLambda(con_testo_della_risposta)
    )


def con_testo_della_risposta(esito: dict) -> dict:
    """L'esito con il testo della risposta e il motivo per cui si e' fermata.

    Il testo si estrae dal messaggio come prima (StrOutputParser: solo i
    blocchi di testo, non il ragionamento). stop_reason_risposta e'
    "max_tokens" se la risposta e' stata troncata: l'app lo dice e la prova
    lo conta (correzione D1). Il messaggio intero non resta nell'esito.
    """
    esito = dict(esito)
    messaggio = esito.pop("messaggio")
    metadati = getattr(messaggio, "response_metadata", None) or {}
    return {
        **esito,
        "risposta": StrOutputParser().invoke(messaggio),
        "stop_reason_risposta": metadati.get("stop_reason"),
    }
