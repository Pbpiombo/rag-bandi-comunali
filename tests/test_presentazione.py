"""Test della correzione C: presentazione delle risposte.

Piano in docs/piano-correzioni-lotto1.md, "Correzione C". Le regole del
prompt (C1, C2, C5) hanno solo controlli deboli sulla presenza del testo:
il comportamento si misura registrando il lotto 1. "Da approfondire" (C3)
e "Fonti" (C4) si provano sull'app, con streamlit.testing.
"""

from markdown_it import MarkdownIt
from streamlit.testing.v1 import AppTest

from src.chains.rag import ISTRUZIONI
from src.database.interrogazioni_bandi import GRUPPO_SENZA_SCADENZA, GRUPPO_SPORTELLO
from src.database.modelli import Approfondimento

# --- Regole del prompt (controlli deboli) ---


def test_c1_niente_azioni_che_l_app_non_sa_fare():
    assert "COSA PUÒ FARE L'APP" in ISTRUZIONI
    assert "non cerca su internet" in ISTRUZIONI
    assert "non ricorda le domande precedenti" in ISTRUZIONI
    assert "Non nominare interrogazioni, parametri" in ISTRUZIONI
    assert "rifaccia la domanda indicando" in ISTRUZIONI


def test_c2_bandi_generici_nominati_come_possibili_e_in_sintesi():
    assert "nominali come possibili" in ISTRUZIONI
    assert "non esistono o non sono presenti" in ISTRUZIONI
    assert "raggruppati per tipo di" in ISTRUZIONI
    assert "mai l'elenco completo" in ISTRUZIONI


def test_c2_un_bando_generico_non_e_un_argomento_vicino():
    # La riga di "QUANDO NON RISPONDERE" viene dopo quella sull'argomento
    # vicino, che altrimenti la contraddice
    vicino = ISTRUZIONI.index("NON è una risposta.")
    eccezione = ISTRUZIONI.index("non è un argomento vicino")
    assert vicino < eccezione < ISTRUZIONI.index("COSA PUÒ FARE L'APP")


def test_c5_niente_dati_attribuiti_a_chi_chiede():
    # Regola di D2, che sostituisce quella di C5 (docs/piano-correzioni-lotto1.md)
    assert "Non scrivere mai il codice ATECO" in ISTRUZIONI
    assert "Sbagliato:" in ISTRUZIONI
    assert "Giusto:" in ISTRUZIONI
    # L'esempio non usa la domanda con cui si misura (L02) né un codice vero
    # attribuito a un'attività: tarerebbe il prompt sulla misura
    assert "56.10" not in ISTRUZIONI
    assert "ristorante" not in ISTRUZIONI.lower()


# --- C3: "Da approfondire" nell'app ---


def pagina_da_approfondire(voci):
    from app.app import mostra_da_approfondire
    from src.database.modelli import Risultato

    risultato = Risultato("Bandi aperti per altre imprese", da_approfondire=voci)
    mostra_da_approfondire({"esiti_dati": [("bandi_per_beneficiario", risultato)]})


def esegui_pagina(funzione, **argomenti) -> AppTest:
    pagina = AppTest.from_function(funzione, kwargs=argomenti, default_timeout=30)
    pagina.run()
    assert not pagina.exception, pagina.exception
    return pagina


def contenuti(pagina: AppTest) -> list[str]:
    return [e.value for e in [*pagina.markdown, *pagina.caption]]


def test_c3_titolo_e_didascalia_senza_pertinenti():
    voce = Approfondimento(
        "Progetti di cooperazione internazionale",
        "https://esempio.it/cooperazione",
        "beneficiari non indicati sulla pagina",
    )
    pagina = esegui_pagina(pagina_da_approfondire, voci=[voce])

    assert "#### Bandi che non ho potuto valutare" in [e.value for e in pagina.markdown]
    assert [e.value for e in pagina.caption] == [
        "Sulla pagina manca un dato essenziale, indicato per ciascuno."
    ]
    assert not any("pertinent" in t.lower() for t in contenuti(pagina))
    # Ogni voce porta il suo problema
    assert any("beneficiari non indicati sulla pagina" in t for t in contenuti(pagina))


def test_c3_senza_voci_la_sezione_non_compare():
    pagina = esegui_pagina(pagina_da_approfondire, voci=[])
    assert contenuti(pagina) == []


# --- C4: intestazioni dei gruppi in "Fonti" ---

RIGA = "- [#{k}] «Bando {k}» (Regione Toscana) | scade il 2026-12-31 | url: https://esempio.it/{k}"

TESTO_A_GRUPPI = "\n".join(
    [
        "Bandi aperti per altre imprese (alla data del 2026-11-14), 4 in archivio:",
        RIGA.format(k=1),
        RIGA.format(k=2),
        GRUPPO_SPORTELLO,
        RIGA.format(k=3),
        GRUPPO_SENZA_SCADENZA,
        RIGA.format(k=4),
        (
            "2 bandi aperti in archivio hanno beneficiari non ancora classificati: "
            "potrebbero ammettere anche questo tipo."
        ),
    ]
)


def pagina_fonti(testo):
    from app.app import mostra_fonti
    from src.database.modelli import Risultato

    risultato = Risultato(testo, fonti=["Portale bandi Regione Toscana"])
    mostra_fonti(
        {
            "esiti_dati": [("bandi_per_beneficiario", risultato)],
            "documenti": [],
            "origini": [],
        }
    )


def voci_rese(markdown: str) -> list[str]:
    """Il testo di ogni voce d'elenco, reso come lo rende un parser markdown."""
    gettoni = MarkdownIt("commonmark").parse(markdown)
    voci, dentro, testo = [], 0, []
    for g in gettoni:
        if g.type == "list_item_open":
            dentro += 1
            testo = []
        elif g.type == "list_item_close":
            dentro -= 1
            voci.append(" ".join(testo).strip())
        elif dentro and g.type == "inline":
            testo.append(g.content)
    return voci


def test_c4_intestazioni_dei_gruppi_fuori_dalle_voci():
    pagina = esegui_pagina(pagina_fonti, testo=TESTO_A_GRUPPI)

    [blocco] = [e.value for e in pagina.markdown if "[D1.1]" in e.value]
    voci = voci_rese(blocco)

    # Tante voci quante righe di bando, nessuna vuota
    assert [v.split("»")[0] for v in voci] == [
        f"[D1.{k}] «Bando {k}" for k in range(1, 5)
    ]
    assert all(v for v in voci)
    # Nessuna intestazione o avvertenza dentro una voce: stanno come paragrafi
    for riga in (GRUPPO_SPORTELLO, GRUPPO_SENZA_SCADENZA, "non ancora classificati"):
        assert not any(riga in v for v in voci)
        assert riga in MarkdownIt("commonmark").render(blocco)


def test_c4_prima_l_intestazione_finiva_nella_voce_precedente():
    # Il difetto che la correzione toglie: lo stesso testo senza le righe
    # vuote mette "A sportello" in coda al bando 2
    voci = voci_rese(TESTO_A_GRUPPI)
    assert GRUPPO_SPORTELLO in voci[1]


def test_c4_il_testo_per_il_modello_non_cambia():
    from app.app import gruppi_separati

    separato = gruppi_separati(TESTO_A_GRUPPI)
    assert [r for r in separato.split("\n") if r] == TESTO_A_GRUPPI.split("\n")


# --- D3: "QUANDO NON RISPONDERE" senza le parole del sistema ---


def test_d3_cosa_servirebbe_detto_come_bando_o_documento():
    assert "quale bando o documento servirebbe" in ISTRUZIONI
    assert (
        "Non parlare di frammenti, dati forniti, interrogazioni, parametri o temi "
        "dell'archivio" in ISTRUZIONI
    )
    assert "cosa servirebbe per rispondere" not in ISTRUZIONI


def test_d3_rifaccia_la_domanda_solo_per_dettagli_mancanti():
    assert "solo se mancano dettagli che chi chiede non ha dato" in ISTRUZIONI
    assert "mai per ripetere quello che la domanda dice già" in ISTRUZIONI


# --- D1: risposta interrotta da max_tokens, nell'app ---


def pagina_risposta(stop_reason):
    from app.app import mostra_risposta

    mostra_risposta(
        {"risposta": "Il bando scade il (fon", "stop_reason_risposta": stop_reason}
    )


def test_d1_risposta_interrotta_con_avviso_e_riga_finale():
    from app.app import AVVISO_INTERROTTA, RIGA_INTERROTTA

    pagina = esegui_pagina(pagina_risposta, stop_reason="max_tokens")

    assert [e.value for e in pagina.warning] == [AVVISO_INTERROTTA]
    [testo] = [e.value for e in pagina.markdown]
    assert testo.startswith("Il bando scade il (fon")
    assert testo.endswith(RIGA_INTERROTTA)


def test_d1_risposta_completa_senza_avviso():
    pagina = esegui_pagina(pagina_risposta, stop_reason="end_turn")

    assert not pagina.warning
    assert [e.value for e in pagina.markdown] == ["Il bando scade il (fon"]


# --- E1: risposta parziale quando i frammenti parlano della cosa chiesta ---


def test_e1_risposta_parziale_solo_sulla_cosa_chiesta():
    assert "Risposta parziale: solo se i frammenti parlano proprio della cosa" in (
        ISTRUZIONI
    )
    assert "Ogni frase della risposta parziale ha la sua citazione" in ISTRUZIONI
    assert '"secondo lo studio …"' in ISTRUZIONI
    assert "Chiudi con una riga su cosa manca" in ISTRUZIONI
    assert "diverso, anche vicino, la risposta resta" in ISTRUZIONI


def test_e1_prima_della_riga_sull_argomento_vicino():
    parziale = ISTRUZIONI.index("Risposta parziale:")
    vicino = ISTRUZIONI.index("Un frammento che parla di un argomento vicino")
    assert ISTRUZIONI.index("QUANDO NON RISPONDERE") < parziale < vicino


# --- Testo dei frammenti mostrato come testo, non come markdown ---


def pagina_frammento(testo):
    from langchain_core.documents import Document

    from app.app import mostra_fonti

    documento = Document(
        page_content=testo,
        metadata={
            "ente": "Regione Toscana",
            "tipo_documento": "avviso_pubblico",
            "page": 4,
            "riferimento_atto": "Decreto dirigenziale n. 9550 del 28/04/2026",
        },
    )
    mostra_fonti({"esiti_dati": [], "documenti": [documento], "origini": [["denso"]]})


def valore_del_frammento(pagina: AppTest, inizio: str) -> str:
    """Il valore markdown del frammento, tra quelli resi nella pagina."""
    [valore] = [e.value for e in pagina.markdown if inizio in e.value]
    return valore


def test_un_frammento_con_il_numero_di_paragrafo_non_e_un_elenco():
    # Frammento [5] di A05 nel lotto 2: "1. Premessa" diventava un <ol>
    testo = "1. Premessa Il Programma Regionale Toscana FESR 2021 -2027"
    pagina = esegui_pagina(pagina_frammento, testo=testo)

    valore = valore_del_frammento(pagina, "Premessa")
    gettoni = MarkdownIt("commonmark").parse(valore)
    assert not any(g.type == "ordered_list_open" for g in gettoni)
    reso = MarkdownIt("commonmark").render(valore)
    assert reso.removeprefix("<p>").startswith("1. Premessa")


def test_due_dollari_nel_frammento_non_aprono_una_formula():
    # In Streamlit due "$" aprono una formula: ogni "$" va preceduto da "\"
    testo = "Il contributo va da $10 a $20 per domanda."
    pagina = esegui_pagina(pagina_frammento, testo=testo)

    valore = valore_del_frammento(pagina, "contributo")
    assert valore.count("$") == 2
    assert all(valore[i - 1] == "\\" for i, c in enumerate(valore) if c == "$")
    assert "$10 a $20" in MarkdownIt("commonmark").render(valore)


# --- Modello e impronta delle istruzioni nella barra laterale ---


def test_l_impronta_cambia_se_cambiano_le_istruzioni(monkeypatch):
    from src.chains import rag

    prima = rag.impronta_istruzioni()
    assert len(prima) == 8
    assert prima == rag.impronta_istruzioni()

    monkeypatch.setattr(rag, "ISTRUZIONI", rag.ISTRUZIONI + " ")
    assert rag.impronta_istruzioni() != prima


def test_l_impronta_comprende_le_istruzioni_del_router(monkeypatch):
    from src.chains import rag

    prima = rag.impronta_istruzioni()
    monkeypatch.setattr(rag, "ISTRUZIONI_ROUTER", rag.ISTRUZIONI_ROUTER + " ")
    assert rag.impronta_istruzioni() != prima


def pagina_barra_laterale():
    import streamlit as st

    from app.app import riga_versione

    with st.sidebar:
        st.caption(riga_versione())


def test_la_riga_di_versione_compare_nella_barra_laterale():
    import inspect

    import app.app as app
    from src.chains.rag import impronta_istruzioni
    from src.config import MODEL_NAME

    pagina = esegui_pagina(pagina_barra_laterale)

    attesa = f"Modello: {MODEL_NAME} · istruzioni {impronta_istruzioni()}"
    assert [e.value for e in pagina.sidebar.caption] == [attesa]
    # E l'app la scrive davvero nella barra laterale
    assert "st.caption(riga_versione())" in inspect.getsource(app.main)


# --- F1: il profilo è l'ente di riferimento, non per forza chi chiede ---


def messaggio_umano() -> str:
    from src.chains.rag import MODELLO_PROMPT

    return MODELLO_PROMPT.messages[1].prompt.template


def test_f1_intestazione_ente_di_riferimento():
    assert "ENTE DI RIFERIMENTO" in ISTRUZIONI
    assert messaggio_umano().startswith("ENTE DI RIFERIMENTO:")
    assert "ENTE PER CUI RISPONDI" not in ISTRUZIONI
    assert "ENTE PER CUI RISPONDI" not in messaggio_umano()
    assert "ente che pone la domanda" not in ISTRUZIONI
    assert "non per forza chi scrive la domanda" in ISTRUZIONI


def test_f1_chi_chiede_privato_ente_e_caso_ambiguo():
    chi_chiede = ISTRUZIONI.index("CHI CHIEDE")
    privato = ISTRUZIONI.index("È un soggetto privato quando")
    ente = ISTRUZIONI.index("È l'ente quando")
    ambiguo = ISTRUZIONI.index("Se la domanda può venire da tutti e due")
    ateco = ISTRUZIONI.index("Non scrivere mai il codice ATECO")
    # La regola viene prima del divieto di D2, dentro "CHI CHIEDE"
    assert chi_chiede < privato < ente < ambiguo < ateco
    assert "mai con il profilo" in ISTRUZIONI
    assert "rispondi per il soggetto privato" in ISTRUZIONI
    assert '"Se a chiedere è il Comune' in ISTRUZIONI


def test_f1_gli_esempi_non_sono_le_domande_della_misura():
    # Come per D2: P05 ("assumere una persona") e P24 ("un giovane in
    # tirocinio") misurano la regola, e non devono comparire come esempi
    assert "assumere" not in ISTRUZIONI
    assert "tirocin" not in ISTRUZIONI


# --- F3: niente trattini lunghi ---


def test_f3_regola_sui_trattini_nelle_istruzioni():
    assert "PUNTEGGIATURA" in ISTRUZIONI
    assert "trattino lungo (—)" in ISTRUZIONI
    assert "quello medio (–)" in ISTRUZIONI
    assert "usa virgole, due punti o parentesi" in ISTRUZIONI


def stringhe_del_codice(percorso) -> list[str]:
    """Le costanti di testo di un file Python, comprese le parti delle f-string."""
    import ast

    albero = ast.parse(percorso.read_text(encoding="utf-8"))
    return [
        nodo.value
        for nodo in ast.walk(albero)
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str)
    ]


def test_f3_nessun_trattino_lungo_nelle_stringhe_dell_app():
    # Le righe che l'app e le interrogazioni scrivono per chi legge; le
    # ISTRUZIONI (src/chains) nominano i trattini per vietarli, e restano fuori
    from pathlib import Path

    radice = Path(__file__).resolve().parent.parent
    file = [*radice.glob("app/*.py"), *radice.glob("src/database/*.py")]
    assert file
    trovate = [
        (f.name, s)
        for f in file
        for s in stringhe_del_codice(f)
        if "—" in s or "–" in s
    ]
    assert trovate == []


def test_f3_da_approfondire_senza_trattino_e_titolo_intatto():
    # Il separatore tra titolo e motivo non è più un trattino lungo; il
    # trattino nel titolo del bando è un dato della fonte e resta
    voce = Approfondimento(
        "Programma 2021–2027 — seconda edizione",
        "https://esempio.it/programma",
        "scadenza non indicata sulla pagina",
    )
    pagina = esegui_pagina(pagina_da_approfondire, voci=[voce])

    righe = [t for t in contenuti(pagina) if "esempio.it/programma" in t]
    attesa = (
        "- [Programma 2021–2027 — seconda edizione](https://esempio.it/programma): "
        "scadenza non indicata sulla pagina · vedi la pagina"
    )
    assert righe == [attesa]


# --- correzione G (dal lotto 4) ---


def test_g2a_bando_senza_atto_citato_con_la_fonte_della_riga():
    assert 'Se la riga di un bando ha "atto: non indicato"' in ISTRUZIONI
    assert "(fonte: [D1.2], <fonte della riga>)" in ISTRUZIONI
    assert "Non prendere mai un atto da un'altra riga." in ISTRUZIONI


def test_g3_bando_nominato_non_in_archivio():
    inizio = ISTRUZIONI.index("Bando nominato che non è in archivio")
    regola = ISTRUZIONI[inizio : ISTRUZIONI.index("COSA PUÒ FARE L'APP")]
    assert "in archivio c'è il «…»" in regola
    assert "senza dire né far intendere che sia lo stesso" in regola
    assert "senza stato, scadenze o importi" in regola
    assert "non si nominano" in regola
    assert "né altri seguiti" in regola
    # Dentro QUANDO NON RISPONDERE, dopo la formula del "Non trovo"
    assert ISTRUZIONI.index("QUANDO NON RISPONDERE") < inizio


def test_g_regole_non_tarate_sulle_domande_del_lotto_4():
    # Le domande con cui si misura G non stanno nelle istruzioni (come F1a)
    for parola in ("Sport e periferie", "Missione Comune", "falegnam", "Filiera"):
        assert parola not in ISTRUZIONI
