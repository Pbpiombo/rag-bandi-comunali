"""Interfaccia Streamlit per il sistema RAG territoriale."""

import os
import sys
from pathlib import Path

# Streamlit esegue questo file direttamente, quindi la radice del progetto
# non e' nel percorso di ricerca dei moduli: ce la mettiamo a mano.
RADICE = Path(__file__).resolve().parents[1]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

import streamlit as st

from src.chains.rag import costruisci_catena
from src.database.repertorio import stato_archivio
from src.pgstore import RecuperoPostgres
from src.verification.controllo import riassumi, verifica

st.set_page_config(
    page_title="Assistente territoriale",
    page_icon="⛰",
    layout="wide",
)

SIMBOLI = {
    "verificato": "✓",
    "non_trovato": "✗",
    "non_citato": "?",
}

ESEMPI = [
    "Qual è il costo massimo giornaliero per un incarico professionale?",
    "Quanti abitanti ha il Comune?",
    "Il calo demografico giustifica la richiesta di fondi per le aree interne?",
    "Entro quando va presentata la relazione annuale?",
]


USA_POSTGRES = os.getenv("USA_POSTGRES", "1") == "1"

@st.cache_resource(show_spinner="Costruzione degli indici in corso...")
def carica_catena():
    """Costruita una volta sola e riusata a ogni interazione."""
    if USA_POSTGRES:
        return costruisci_catena(recupero=RecuperoPostgres())
    return costruisci_catena()


def mostra_verifica(esito: dict) -> None:
    """Il pannello di verifica dei dati citati."""
    esiti = verifica(
        esito["risposta"],
        esito["documenti"],
        esito.get("esiti_dati"),
    )

    if not esiti:
        st.caption("Nessun dato numerico da verificare in questa risposta.")
        return

    conteggio = riassumi(esiti)
    problemi = conteggio["non_trovato"]

    if problemi:
        st.error(
            f"{problemi} dato/i citato/i NON trovato/i nella fonte indicata. "
            "Verificare manualmente prima di riutilizzare la risposta."
        )
    else:
        st.success(f"{conteggio['verificato']} dati verificati nella fonte citata.")

    da_mostrare = [
        e for e in esiti if not (e.tipo == "anno" and e.stato == "verificato")
    ]

    problematici = [e for e in da_mostrare if e.stato != "verificato"]
    verificati = [e for e in da_mostrare if e.stato == "verificato"]

    for e in problematici:
        riga = f"{SIMBOLI[e.stato]}  **{e.valore}**  ({e.tipo})"
        if e.contesto:
            riga += f"  ·  _{e.contesto}_" 
        if e.frammenti:
            riga += f" → fonti {', '.join(e.frammenti)}"
        if e.stato == "non_trovato":
            st.markdown(f":red[{riga}]")
            if e.dettaglio:
                st.caption(f"    {e.dettaglio}")
        else:
            st.markdown(f":orange[{riga}]")

    if verificati:
        with st.expander(f"{len(verificati)} dati verificati", expanded=False):
            for e in verificati:
                riga = f"{SIMBOLI[e.stato]}  **{e.valore}**  ({e.tipo})"
                if e.contesto:
                    riga += f"  ·  _{e.contesto}_"
                if e.frammenti:
                    riga += f" → fonti {', '.join(e.frammenti)}"
                st.markdown(riga)


def mostra_fonti(esito: dict) -> None:  
    """I frammenti documentali e i dati numerici usati."""
    dati = esito.get("esiti_dati") or []
    documenti = esito["documenti"]
    origini = esito.get("origini") or []

    if dati:
        st.markdown("##### Dati numerici certificati")
        for numero, (nome, risultato) in enumerate(dati, start=1):
            with st.expander(f"[D{numero}]  {nome}", expanded=False):
                st.write(risultato.testo)
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
                st.write(" ".join(doc.page_content.split()))


def main() -> None:
    st.title("Assistente per la programmazione territoriale")
    st.caption(
        "Risponde solo sulla base dei documenti e dei dati in archivio, "
        "citando la fonte di ogni dato."
    )

    with st.sidebar:
        
        st.caption(f"Vector store: {'Postgres' if USA_POSTGRES else 'Chroma'}")
        st.header("Archivi")
        st.markdown("**Dati numerici**")
        st.code(stato_archivio(), language=None)
        st.divider()
        st.caption(
            "Il sistema rifiuta di rispondere quando i documenti non "
            "contengono l'informazione. Un rifiuto è un esito corretto."
        )

    if "domanda" not in st.session_state:
        st.session_state.domanda = ""

    st.markdown("###### Esempi")
    colonne = st.columns(len(ESEMPI))
    for colonna, esempio in zip(colonne, ESEMPI, strict=True):
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

    catena = carica_catena()

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

    if "errore" in decisione:
        st.warning(f"Anomalia del router: {decisione['errore']}")

    sinistra, destra = st.columns([3, 2])

    with sinistra:
        st.markdown("#### Risposta")
        st.markdown(esito["risposta"])
        st.divider()
        st.markdown("#### Verifica")
        mostra_verifica(esito)

    with destra:
        st.markdown("#### Fonti")
        mostra_fonti(esito)


if __name__ == "__main__":
    main()

