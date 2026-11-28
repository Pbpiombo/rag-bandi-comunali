"""Interfaccia Streamlit per il sistema RAG territoriale."""

import logging
import os
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

# Streamlit esegue questo file direttamente, quindi la radice del progetto
# non e' nel percorso di ricerca dei moduli: ce la mettiamo a mano.
RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

import anthropic
import psycopg
import streamlit as st

from src.chains.rag import costruisci_catena, impronta_istruzioni
from src.citazioni import accorcia_citazioni
from src.config import ACCORCIA_CITAZIONI, ENTE_PREDEFINITO, MODEL_NAME, ORDINE_C_LR
from src.database.enti import elenco_enti
from src.database.interrogazioni_bandi import (
    data_di_oggi,
    sospensioni_attive,
    sospensioni_di,
)
from src.database.modelli import bandi_citati, collegamenti_bandi, con_etichette
from src.database.repertorio import stato_archivio
from src.database.schema import connetti
from src.normalizzazione import MESI, data, uniforma_trattini
from src.pgstore import RecuperoPostgres
from src.verification.controllo import contesto_di, dati_presenti, giudizio, verifica

LOG = logging.getLogger("app")

# Gli errori del servizio del modello e del database dei documenti: l'utente
# vede una riga sola, senza dettagli (demo del 24/11/2026, traceback di un
# errore di autenticazione). Elenco chiuso: ogni altro errore, compresi
# quelli di programmazione, continua a emergere.
ERRORI_SERVIZIO = (
    anthropic.AuthenticationError,
    anthropic.RateLimitError,
    anthropic.APIConnectionError,  # comprende APITimeoutError
    anthropic.InternalServerError,
    anthropic.OverloadedError,
    anthropic.ServiceUnavailableError,
    psycopg.OperationalError,  # connessione o tempo scaduto di Postgres
)
MESSAGGIO_SERVIZIO = (
    "Il servizio non è disponibile in questo momento. Riprova tra qualche minuto."
)

# I tipi dei dati come li legge l'utente; i nomi interni non cambiano
ETICHETTE_TIPI = {
    "quantita": "numero",
    "importo": "importo",
    "data": "data",
    "atto": "atto",
    "codice": "codice",
    "riferimento": "riferimento",
    "intervallo": "intervallo di date",
    "periodo": "periodo",
    "anno": "anno",
    "orario": "orario",
    "percentuale": "percentuale",
}

st.set_page_config(
    page_title="Assistente territoriale",
    page_icon="⛰",
    layout="wide",
)

SIMBOLI = {
    "verificato": "✓",
    "non_trovato": "✗",
    "non_citato": "?",
    "citazione_generica": "≈",
    "dalla_domanda": "ℹ",
}

# Il dato scritto dall'utente nella domanda: nota neutra, senza colore
NOTA_DOMANDA = (
    "Numeri scritti nella domanda: non si cercano nelle fonti e non contano "
    "nella verifica."
)
# Cosa promette il pannello, sempre sotto la verifica (25/11/2026)
PROMESSA_VERIFICA = (
    "Il controllo riguarda numeri, date, importi e atti: dice se compaiono "
    "nella fonte citata, non se la risposta è completa."
)

ESEMPI = [
    "Quali bandi sono aperti per il Comune?",
    "Quali bandi per il Comune scadono nei prossimi 30 giorni?",
    (
        "Chi può partecipare a Sport Missione Comune e qual è il mutuo massimo "
        "per un piccolo comune?"
    ),
    "Quali bandi aperti ci sono per le imprese turistiche?",
    "Ci sono contributi aperti per le aziende agricole e forestali?",
    "Qual è il costo massimo giornaliero per un incarico professionale?",
    "Quanti abitanti ha il Comune e come è cambiata la popolazione dal 2019?",
]

# Una risposta fermata da max_tokens (correzione D1)
AVVISO_INTERROTTA = (
    "La risposta si è interrotta perché troppo lunga: è incompleta e può "
    "mancare l'ultima parte. Rifaccia la domanda in modo più circoscritto "
    "(per esempio un solo tipo di bando)."
)
RIGA_INTERROTTA = "[risposta interrotta]"

# La sezione dei bandi tenuti fuori dagli elenchi: non valutati, non
# "pertinenti" (correzione C3)
TITOLO_DA_APPROFONDIRE = "Bandi che non ho potuto valutare"
DIDASCALIA_DA_APPROFONDIRE = (
    "Sulla pagina manca un dato essenziale, indicato per ciascuno."
)

# Bottoni degli esempi per riga: con 7 domande una riga sola e' troppo stretta
ESEMPI_PER_RIGA = 4


USA_POSTGRES = os.getenv("USA_POSTGRES", "1") == "1"


def recupero_e_riordino() -> tuple:
    """(recupero, riordino) per la catena, secondo Postgres e l'ordine c-LR.

    - Postgres acceso: RecuperoPostgres, senza riordino. Fino alla fermata 5
      del 19e l'interruttore ORDINE_C_LR qui non ha effetto (l'archivio
      Postgres del motore non c'è ancora): sulla demo, che usa Postgres,
      l'app resta quella di prima anche a interruttore acceso.
    - Postgres spento, interruttore acceso: motore in memoria su Chroma, con
      il file dei contesti, e riordino (carica_motore).
    - Postgres spento, interruttore spento: (None, None), e la catena si
      costruisce il suo RecuperoIbrido come prima; niente del motore si
      carica.
    """
    if USA_POSTGRES:
        return RecuperoPostgres(), None
    if ORDINE_C_LR:
        from src.motore import carica_motore

        return carica_motore()
    return None, None


@st.cache_resource(show_spinner="Caricamento del recupero documentale...")
def carica_recupero():
    """Un solo recupero, condiviso da tutti gli enti: i documenti sono gli stessi.

    In cache: con l'ordine c-LR i due modelli si caricano una volta sola.
    """
    return recupero_e_riordino()


def avviso_ordine() -> str:
    """La riga che l'app registra all'avvio sull'ordine dei frammenti."""
    if not ORDINE_C_LR:
        return "ordine c-LR spento: recupero di prima"
    if USA_POSTGRES:
        return (
            "ordine c-LR acceso ma senza effetto: con Postgres resta il recupero "
            "di prima fino alla fermata 5 del 19e"
        )
    return "ordine c-LR acceso: motore in memoria su Chroma e riordino"


@st.cache_resource(show_spinner=False)
def registra_avvio() -> None:
    """Una volta per processo: l'avviso sull'ordine dei frammenti nel registro."""
    if ORDINE_C_LR and USA_POSTGRES:
        LOG.warning(avviso_ordine())
    else:
        LOG.info(avviso_ordine())


@st.cache_resource(show_spinner="Costruzione della catena per l'ente...")
def carica_catena(codice_ente: str):
    """Una catena per ente, costruita una volta sola."""
    recupero, riordino = carica_recupero()
    return costruisci_catena(codice_ente, recupero=recupero, riordino=riordino)


# Un'etichetta di bando in un testo del pannello: "D1.2", anche dentro
# "presente invece in ['D1.2']" o "nel bando [D1.1]"
ETICHETTA_BANDO = re.compile(r"(?<![\w.])D\d+\.\d+(?!\d)")


def con_collegamenti(testo: str, collegamenti: dict) -> str:
    """Il testo con le etichette dei bandi come collegamenti alla loro pagina.

    L'url viene dal database (collegamenti_bandi); un'etichetta senza bando,
    come D2 o un frammento, resta testo. Streamlit apre i collegamenti
    verso altri siti in una nuova scheda.
    """

    def collega(m: re.Match) -> str:
        voce = collegamenti.get(m.group(0))
        return f"[{m.group(0)}](<{voce.url}>)" if voce else m.group(0)

    return ETICHETTA_BANDO.sub(collega, testo)


AVVISO_ROUTER = (
    "Non sono riuscito a scegliere le interrogazioni sui dati: "
    "la risposta si basa solo sui documenti."
)


def avviso_router(decisione: dict) -> str | None:
    """La riga per l'utente quando il router non ha dato una decisione.

    Sempre la stessa riga neutra: il testo grezzo del router, l'errore e lo
    stop_reason restano nella decisione per la diagnosi, non si mostrano.
    """
    return AVVISO_ROUTER if "errore" in decisione else None


def mostra_verifica(esito: dict) -> None:
    """Il pannello di verifica dei dati citati."""
    esiti = verifica(
        esito["risposta"],
        esito["documenti"],
        esito.get("esiti_dati"),
        domanda=esito.get("domanda"),
    )
    collegamenti = collegamenti_bandi(esito.get("esiti_dati"))
    # Le due date di un intervallo rosso restano solo nella sua riga rossa:
    # tra i dati presenti sembrerebbero confermate (25/11/2026). Si tolgono
    # prima di raggruppare, cosi' la stessa data scritta altrove resta, e il
    # livello non cambia: con un intervallo rosso e' rosso comunque
    nascoste = date_degli_intervalli_rossi(esito["risposta"], esiti)
    esiti = [e for e in esiti if id(e) not in nascoste]
    # Una riga e un conteggio per ogni dato con le sue fonti, anche se la
    # risposta lo cita piu' volte: solo la visualizzazione, il verificatore
    # e i file della prova restano come sono
    gruppi = raggruppa_esiti(esiti)
    volte = {id(e): n for e, n in gruppi}
    esiti = [e for e, _ in gruppi]

    livello, messaggio = giudizio(esiti)
    messaggio = singolare_o_plurale(messaggio)
    della_domanda = [e for e in esiti if e.stato == "dalla_domanda"]
    if livello == "nessuno":
        st.caption(messaggio)
        mostra_dati_della_domanda(della_domanda, collegamenti, volte)
        st.caption(PROMESSA_VERIFICA)
        return

    # Il verde solo se tutto cio' che si poteva verificare e' verificato
    {"rosso": st.error, "arancione": st.warning, "verde": st.success}[livello](
        messaggio
    )

    da_mostrare = [
        e for e in esiti if not (e.tipo == "anno" and e.stato == "verificato")
    ]

    problematici = [
        e for e in da_mostrare if e.stato not in ("verificato", "dalla_domanda")
    ]
    verificati = [e for e in da_mostrare if e.stato == "verificato"]

    for e in problematici:
        st.markdown(riga_esito(e, collegamenti, volte[id(e)]))
        # Per una citazione generica il dettaglio indica il bando giusto
        if e.dettaglio:
            spiegazione = spiega_dettaglio(e, esito.get("documenti") or [])
            st.caption(f"    {con_collegamenti(spiegazione, collegamenti)}")

    mostra_dati_della_domanda(della_domanda, collegamenti, volte)

    if verificati:
        with st.expander(dati_presenti(len(verificati)), expanded=False):
            for e in verificati:
                st.markdown(riga_esito(e, collegamenti, volte[id(e)]))

    st.caption(PROMESSA_VERIFICA)


def singolare_o_plurale(messaggio: str) -> str:
    """Il messaggio del verificatore senza le forme "dato/i" e "citato/i".

    "1 dato/i senza fonte" -> "1 dato senza fonte", "3 dato/i" -> "3 dati".
    Il verificatore e i suoi test restano come sono: cambia solo il testo
    mostrato.
    """

    def accorda(m: re.Match) -> str:
        n, parola = m.group(1), m.group(2)
        return f"{n} {parola}o" if n == "1" else f"{n} {parola}i"

    return re.sub(r"\b(\d+) (dat|citat)o/i\b", accorda, messaggio)


def date_degli_intervalli_rossi(risposta: str, esiti: list) -> set[int]:
    """Gli id delle date presenti che stanno dentro un intervallo rosso.

    Gli esiti non portano la posizione: la si ritrova nella risposta, come
    la legge il verificatore (trattini uniformati), dove valore e contesto
    coincidono con quelli dell'esito. Una stessa data scritta altrove nella
    risposta resta tra i dati presenti.
    """
    testo = uniforma_trattini(risposta)
    tratti = []
    for e in esiti:
        if e.tipo == "intervallo" and e.stato == "non_trovato":
            schema = r"\s+".join(re.escape(p) for p in e.valore.split())
            tratti += [(m.start(), m.end()) for m in re.finditer(schema, testo)]
    if not tratti:
        return set()
    nascoste = set()
    for e in esiti:
        if e.tipo != "data" or e.stato != "verificato" or not data(e.valore):
            continue
        for m in re.finditer(re.escape(e.valore), testo):
            p = m.start()
            if contesto_di(testo, p) == e.contesto and any(
                i <= p < f for i, f in tratti
            ):
                nascoste.add(id(e))
    return nascoste


def mostra_dati_della_domanda(esiti: list, collegamenti: dict, volte: dict) -> None:
    """I numeri scritti dall'utente nella domanda: una nota, senza colore."""
    if not esiti:
        return
    st.caption(NOTA_DOMANDA)
    for e in esiti:
        st.markdown(riga_esito(e, collegamenti, volte[id(e)]))


def raggruppa_esiti(esiti: list) -> list[tuple]:
    """Gli esiti uniti per (stato, valore normalizzato, fonti), con le occorrenze.

    Una risposta che cita lo stesso decreto quattro volte con la stessa
    fonte da' quattro esiti uguali: nel pannello diventano una riga "×4", e
    il conteggio del messaggio li conta una volta (voce "Pannello" della
    roadmap). Lo stesso valore con fonti diverse resta in righe diverse; lo
    stato fa parte della chiave, cosi' un verificato e un non trovato non si
    fondono. Si tiene il primo esito di ogni gruppo, nell'ordine della
    risposta.
    """
    gruppi: dict[tuple, list] = {}
    for e in esiti:
        chiave = (
            e.stato,
            " ".join(e.valore.split()).lower(),
            tuple(sorted(set(e.frammenti))),
        )
        gruppi.setdefault(chiave, [e, 0])[1] += 1
    return [(e, n) for e, n in gruppi.values()]


def riga_esito(e, collegamenti: dict, volte: int = 1) -> str:
    """La riga Markdown di un dato nel pannello di verifica.

    Valore, tipo, contesto e fonti, con le etichette dei bandi come
    collegamenti; in rosso un dato non trovato, in arancione gli altri
    problemi, senza colore un dato verificato. Il contesto e' un ritaglio
    della risposta e puo' tagliare una citazione a meta' ("], decreto)"):
    le sue parentesi quadre si proteggono, altrimenti chiuderebbero il
    colore in anticipo. Le etichette dei bandi nelle fonti no: sono i
    collegamenti.
    """
    riga = f"{SIMBOLI[e.stato]}  **{e.valore}**  ({ETICHETTE_TIPI.get(e.tipo, e.tipo)})"
    if e.contesto:
        riga += f"  ·  _{testo_per_collegamento(e.contesto)}_"
    if e.frammenti:
        riga += f" → fonti {con_collegamenti(', '.join(e.frammenti), collegamenti)}"
    if volte > 1:
        riga += f"  ×{volte}"
    if e.stato in ("verificato", "dalla_domanda"):
        return riga
    colore = "red" if e.stato == "non_trovato" else "orange"
    return f":{colore}[{riga}]"


def _documento_di(etichetta: str, documenti: list) -> str | None:
    """Il documento da cui viene un frammento: il file, o l'atto."""
    if not etichetta.isdigit() or not 0 < int(etichetta) <= len(documenti):
        return None
    meta = documenti[int(etichetta) - 1].metadata
    return meta.get("fonte") or meta.get("riferimento_atto") or None


def spiega_dettaglio(e, documenti: list) -> str:
    """La frase per l'utente sotto un dato non trovato o con un problema.

    Il dettaglio del verificatore resta com'e' (lo usano i file della
    prova); qui si dice dove sta il dato: in nessuna fonte, nella riga di
    un altro bando, in un altro documento, in un altro punto dello stesso
    documento, in un altro blocco di dati. Resta comunque rosso: la
    risposta lo attribuisce alla fonte sbagliata.
    """
    dettaglio = e.dettaglio
    if dettaglio == "non presente in nessuna fonte recuperata":
        return "Non trovato in nessuna fonte recuperata."
    altrove = re.fullmatch(r"presente invece in \[(.*)\]", dettaglio)
    if not altrove:
        return dettaglio[:1].upper() + dettaglio[1:].rstrip(".") + "."

    etichette = re.findall(r"'([^']+)'", altrove.group(1))
    bandi = [x for x in etichette if ETICHETTA_BANDO.fullmatch(x)]
    blocchi = [x for x in etichette if re.fullmatch(r"D\d+", x)]
    frammenti = [x for x in etichette if x.isdigit()]
    citati = {_documento_di(x, documenti) for x in e.frammenti} - {None}
    stesso = [x for x in frammenti if _documento_di(x, documenti) in citati]
    altri = [x for x in frammenti if x not in stesso]

    def elenco(xs: list[str], parentesi: bool = False) -> str:
        return ", ".join(f"[{x}]" if parentesi else x for x in xs)

    if stesso and not (bandi or blocchi or altri):
        return (
            "Non trovato nel punto citato: è in un altro punto dello stesso "
            f"documento, {elenco(stesso, True)}."
        )
    parti = []
    if bandi:
        parti.append(f"è invece nella riga di un altro bando, {elenco(bandi)}")
    if blocchi:
        parti.append(f"è invece in un altro blocco di dati, {elenco(blocchi)}")
    if altri:
        parti.append(f"è invece in un altro documento, {elenco(altri, True)}")
    if stesso:
        parti.append(
            f"è in un altro punto dello stesso documento, {elenco(stesso, True)}"
        )
    return "Non trovato nella fonte citata: " + "; ".join(parti) + "."


def testo_per_collegamento(testo: str) -> str:
    """Il testo con le parentesi quadre protette, per un collegamento Markdown."""
    return testo.replace("[", r"\[").replace("]", r"\]")


def mostra_bandi_citati(esito: dict) -> None:
    """I bandi citati nella risposta con [Dn.k], scritti dall'app.

    Titolo e indirizzo vengono dal database, non dal modello. I
    collegamenti verso altri siti Streamlit li apre in una nuova scheda.
    """
    citati = bandi_citati(esito["risposta"], esito.get("esiti_dati"))
    if not citati:
        return

    # Lo stato "sospeso" dal database, alla data di oggi: compare anche se
    # la risposta non nomina la sospensione (25/11/2026)
    oggi = data_di_oggi().isoformat()
    conn = connetti()
    try:
        stati = {voce.url: stato_sospensione(conn, voce.url, oggi) for voce in citati}
    finally:
        conn.close()

    st.markdown("#### Bandi citati")
    for voce in citati:
        titolo = testo_per_collegamento(voce.titolo or voce.url)
        stato = f" · {stati[voce.url]}" if stati[voce.url] else ""
        st.markdown(f"- [{titolo}](<{voce.url}>){stato}")


def dal_in_italiano(iso: str) -> str:
    """'dall'8 luglio 2026', 'dal 1° luglio 2026', 'dal 15 luglio 2026'."""
    giorno = date.fromisoformat(iso)
    numero = "1°" if giorno.day == 1 else str(giorno.day)
    preposizione = "dall'" if giorno.day in (8, 11) else "dal "
    return f"{preposizione}{numero} {MESI[giorno.month - 1]} {giorno.year}"


def stato_sospensione(conn, url: str, oggi: str) -> str | None:
    """ "sospeso dal …" o "sospeso in parte dal …" per un bando sospeso oggi.

    Il bando si trova per url, l'indirizzo della sua pagina; le sospensioni
    in corso sono quelle di sospensioni_attive (dal giorno sospeso_dal al
    giorno prima della riapertura). Con una sospensione totale in corso il
    bando e' sospeso; altrimenti in parte. La data e' la prima sospensione
    in corso di quel genere. None per un bando non sospeso o non in archivio.
    """
    riga = conn.execute("SELECT id FROM bandi WHERE url = ?", (url,)).fetchone()
    if riga is None:
        return None
    attive = sospensioni_attive(sospensioni_di(conn, riga["id"]), oggi)
    if not attive:
        return None
    totali = [s["sospeso_dal"] for s in attive if s["ambito"] == "tutto"]
    if totali:
        return f"sospeso {dal_in_italiano(min(totali))}"
    return f"sospeso in parte {dal_in_italiano(min(s['sospeso_dal'] for s in attive))}"


def mostra_risposta(esito: dict) -> None:
    """La risposta del modello; se si e' fermata per max_tokens, lo dice.

    Una risposta troncata non deve sembrare completa: avviso sopra e riga
    in fondo, che resta anche se il testo si copia (correzione D1,
    docs/piano-correzioni-lotto1.md). Il testo salvato e verificato resta
    quello del modello: la riga la aggiunge solo l'app. Le citazioni
    ripetute si accorciano solo qui (src/citazioni.py): verificatore e
    bandi citati ricevono esito["risposta"] intero.
    """
    risposta = esito["risposta"]
    risposta = accorcia_citazioni(risposta) if ACCORCIA_CITAZIONI else risposta
    if esito.get("stop_reason_risposta") == "max_tokens":
        st.warning(AVVISO_INTERROTTA)
        risposta = f"{risposta.rstrip()}\n\n{RIGA_INTERROTTA}"
    st.markdown(risposta)


def mostra_da_approfondire(esito: dict) -> None:
    """I bandi con un dato essenziale mancante o incerto, scritti dall'app.

    Vengono dalle interrogazioni del turno, non dal modello: non sono nella
    risposta e il verificatore non li controlla. Un bando compare una volta.
    Non sono stati valutati, quindi il titolo non li dice pertinenti
    (correzione C3, docs/piano-correzioni-lotto1.md).
    """
    voci = {}
    for _, risultato in esito.get("esiti_dati") or []:
        for voce in risultato.da_approfondire:
            voci.setdefault(voce.url, voce)
    if not voci:
        return

    st.markdown(f"#### {TITOLO_DA_APPROFONDIRE}")
    st.caption(DIDASCALIA_DA_APPROFONDIRE)
    for voce in voci.values():
        contatti = voce.contatti or "vedi la pagina"
        st.markdown(f"- [{voce.titolo}]({voce.url}): {voce.problema} · {contatti}")


def gruppi_separati(testo: str) -> str:
    """Il testo di un blocco di dati, con le righe fuori elenco come paragrafi.

    Le intestazioni dei gruppi ("A sportello, finché ci sono risorse:") e
    le avvertenze seguono una voce "- …" senza riga vuota: in markdown sono
    la continuazione di quella voce, e nell'app finivano in coda al bando
    precedente (correzione C4, docs/piano-correzioni-lotto1.md). Una riga
    vuota prima e dopo ne fa un paragrafo. Solo per l'app: il testo dato
    al modello e al verificatore non cambia.
    """
    righe = []
    for numero, riga in enumerate(testo.split("\n")):
        if numero and riga.strip() and not riga.startswith("- "):
            righe += ["", riga, ""]
        else:
            righe.append(riga)
    return "\n".join(righe)


# I caratteri che il markdown di Streamlit interpreta: "1. " a inizio testo
# apre un elenco numerato, due "$" una formula
CARATTERI_MARKDOWN = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>$~])")


def testo_letterale(testo: str) -> str:
    """Il testo con una barra rovesciata davanti ai caratteri del markdown.

    Per il testo dei frammenti, che viene dai documenti e va mostrato come
    e': un frammento che comincia con il numero di un paragrafo ("1.
    Premessa") diventava un elenco numerato (osservazioni dall'app online
    del 15 novembre 2026, docs/piano-correzioni-lotto1.md). Il markdown
    resta per quello che scrive il programma.
    """
    return CARATTERI_MARKDOWN.sub(r"\\\1", testo)


def mostra_fonti(esito: dict) -> None:
    """I frammenti documentali e i dati numerici usati."""
    dati = esito.get("esiti_dati") or []
    documenti = esito["documenti"]
    origini = esito.get("origini") or []

    if dati:
        st.markdown("##### Dati numerici certificati")
        for numero, (nome, risultato) in enumerate(dati, start=1):
            with st.expander(f"[D{numero}]  {nome}", expanded=False):
                # Le righe dei bandi con le etichette [Dn.k] citate nella risposta
                st.write(gruppi_separati(con_etichette(risultato.testo, numero)))
                for f in risultato.fonti:
                    st.caption(f"fonte: {f}")

    if documenti:
        st.markdown("##### Frammenti documentali")
        for numero, doc in enumerate(documenti, start=1):
            meta = doc.metadata
            intestazione = (
                f"[{numero}]  {meta.get('ente')} · "
                f"{meta.get('tipo_documento')} · pag. {meta.get('page')}"
            )

            with st.expander(intestazione, expanded=False):
                if numero <= len(origini):
                    st.caption(f"recuperato da: {', '.join(origini[numero - 1])}")
                st.caption(
                    f"atto: {meta.get('riferimento_atto') or meta.get('titolo')}"
                )
                st.write(testo_letterale(" ".join(doc.page_content.split())))


def riga_versione() -> str:
    """Il modello e l'impronta delle istruzioni con cui gira l'app.

    Dopo un push che tocca src/ l'app online va riavviata: i moduli di
    src/ restano quelli caricati all'avvio, e la catena e' in cache.
    L'impronta della barra laterale, confrontata con quella locale, dice
    se il riavvio e' avvenuto (README, "App online").
    """
    return f"Modello: {MODEL_NAME} · istruzioni {impronta_istruzioni()}"


def main() -> None:
    registra_avvio()
    st.title("Assistente per la programmazione territoriale")
    st.caption(
        "Risponde solo sulla base dei documenti e dei dati in archivio, "
        "citando la fonte di ogni dato."
    )

    with st.sidebar:
        conn = connetti()
        try:
            elenco = elenco_enti(conn)
        finally:
            conn.close()

        nomi_enti = dict(elenco)
        codici = list(nomi_enti)

        codice_ente = st.selectbox(
            "Ente",
            options=codici,
            format_func=lambda codice: nomi_enti[codice],
            index=codici.index(ENTE_PREDEFINITO),
        )

        st.caption(f"Vector store: {'Postgres' if USA_POSTGRES else 'Chroma'}")
        st.caption(riga_versione())
        st.header("Archivi")
        st.markdown("**Dati numerici**")
        st.code(stato_archivio(codice_ente), language=None)
        st.divider()
        st.caption(
            "Il sistema rifiuta di rispondere quando i documenti non "
            "contengono l'informazione. Un rifiuto è un esito corretto."
        )

    if "domanda" not in st.session_state:
        st.session_state.domanda = ""

    st.markdown("###### Esempi")
    for inizio in range(0, len(ESEMPI), ESEMPI_PER_RIGA):
        riga = ESEMPI[inizio : inizio + ESEMPI_PER_RIGA]
        # Sempre ESEMPI_PER_RIGA colonne: i bottoni dell'ultima riga restano
        # larghi quanto quelli sopra
        colonne = st.columns(ESEMPI_PER_RIGA)
        for colonna, esempio in zip(colonne, riga, strict=False):
            with colonna:
                if st.button(esempio, use_container_width=True):
                    st.session_state.domanda = esempio

    domanda = st.text_area(
        "Domanda",
        value=st.session_state.domanda,
        height=80,
        placeholder="Scrivi una domanda sui documenti o sui dati del Comune...",
    )

    if not st.button("Chiedi", type="primary"):
        return

    if not domanda.strip():
        st.warning("Scrivi una domanda.")
        return

    try:
        catena = carica_catena(codice_ente)
        with st.spinner("Ricerca e generazione in corso..."):
            esito = catena.invoke(domanda.strip())
    except ERRORI_SERVIZIO as errore:
        # Nel log il tipo e il momento, non il testo dell'errore ne' la domanda
        LOG.error(
            "Servizio non disponibile: %s alle %s",
            type(errore).__name__,
            datetime.now(UTC).isoformat(timespec="seconds"),
        )
        st.error(MESSAGGIO_SERVIZIO)
        return

    decisione = esito["decisione"]
    nomi = [i.get("nome") for i in decisione.get("interrogazioni", [])]

    riga_router = []
    if decisione.get("documenti"):
        riga_router.append(f"{len(esito['documenti'])} frammenti documentali")
    if nomi:
        riga_router.append(f"interrogazioni: {', '.join(nomi)}")
    if not riga_router:
        riga_router.append("nessun archivio pertinente")

    st.caption("· ".join(riga_router))

    avviso = avviso_router(decisione)
    if avviso:
        st.info(avviso)

    sinistra, destra = st.columns([3, 2])

    with sinistra:
        st.markdown("#### Risposta")
        mostra_risposta(esito)
        mostra_bandi_citati(esito)
        mostra_da_approfondire(esito)
        st.divider()
        st.markdown("#### Verifica")
        mostra_verifica(esito)

    with destra:
        st.markdown("#### Fonti")
        mostra_fonti(esito)


if __name__ == "__main__":
    main()
