"""Interfaccia Streamlit per il sistema RAG territoriale."""

import os
import re
import sys
from pathlib import Path

# Streamlit esegue questo file direttamente, quindi la radice del progetto
# non e' nel percorso di ricerca dei moduli: ce la mettiamo a mano.
RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

import streamlit as st

from src.chains.rag import costruisci_catena, impronta_istruzioni
from src.config import ENTE_PREDEFINITO, MODEL_NAME
from src.database.enti import elenco_enti
from src.database.modelli import bandi_citati, collegamenti_bandi, con_etichette
from src.database.repertorio import stato_archivio
from src.database.schema import connetti
from src.pgstore import RecuperoPostgres
from src.verification.controllo import giudizio, verifica

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
}

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


@st.cache_resource(show_spinner="Caricamento del recupero documentale...")
def carica_recupero():
    """Un solo recupero, condiviso da tutti gli enti: i documenti sono gli stessi."""
    return RecuperoPostgres()


@st.cache_resource(show_spinner="Costruzione della catena per l'ente...")
def carica_catena(codice_ente: str):
    """Una catena per ente, costruita una volta sola."""
    if USA_POSTGRES:
        return costruisci_catena(codice_ente, recupero=carica_recupero())
    return costruisci_catena(codice_ente)


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
    )
    collegamenti = collegamenti_bandi(esito.get("esiti_dati"))
    # Una riga e un conteggio per ogni dato con le sue fonti, anche se la
    # risposta lo cita piu' volte: solo la visualizzazione, il verificatore
    # e i file della prova restano come sono
    gruppi = raggruppa_esiti(esiti)
    volte = {id(e): n for e, n in gruppi}
    esiti = [e for e, _ in gruppi]

    livello, messaggio = giudizio(esiti)
    if livello == "nessuno":
        st.caption(messaggio)
        return

    # Il verde solo se tutto cio' che si poteva verificare e' verificato
    {"rosso": st.error, "arancione": st.warning, "verde": st.success}[livello](
        messaggio
    )

    da_mostrare = [
        e for e in esiti if not (e.tipo == "anno" and e.stato == "verificato")
    ]

    problematici = [e for e in da_mostrare if e.stato != "verificato"]
    verificati = [e for e in da_mostrare if e.stato == "verificato"]

    for e in problematici:
        st.markdown(riga_esito(e, collegamenti, volte[id(e)]))
        # Per una citazione generica il dettaglio indica il bando giusto
        if e.dettaglio:
            st.caption(f"    {con_collegamenti(e.dettaglio, collegamenti)}")

    if verificati:
        with st.expander(f"{len(verificati)} dati verificati", expanded=False):
            for e in verificati:
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
    riga = f"{SIMBOLI[e.stato]}  **{e.valore}**  ({e.tipo})"
    if e.contesto:
        riga += f"  ·  _{testo_per_collegamento(e.contesto)}_"
    if e.frammenti:
        riga += f" → fonti {con_collegamenti(', '.join(e.frammenti), collegamenti)}"
    if volte > 1:
        riga += f"  ×{volte}"
    if e.stato == "verificato":
        return riga
    colore = "red" if e.stato == "non_trovato" else "orange"
    return f":{colore}[{riga}]"


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

    st.markdown("#### Bandi citati")
    for voce in citati:
        titolo = testo_per_collegamento(voce.titolo or voce.url)
        st.markdown(f"- [{titolo}](<{voce.url}>)")


def mostra_risposta(esito: dict) -> None:
    """La risposta del modello; se si e' fermata per max_tokens, lo dice.

    Una risposta troncata non deve sembrare completa: avviso sopra e riga
    in fondo, che resta anche se il testo si copia (correzione D1,
    docs/piano-correzioni-lotto1.md). Il testo salvato e verificato resta
    quello del modello: la riga la aggiunge solo l'app.
    """
    risposta = esito["risposta"]
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
        st.markdown(f"- [{voce.titolo}]({voce.url}) — {voce.problema} · {contatti}")


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

    catena = carica_catena(codice_ente)

    with st.spinner("Ricerca e generazione in corso..."):
        esito = catena.invoke(domanda.strip())

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
