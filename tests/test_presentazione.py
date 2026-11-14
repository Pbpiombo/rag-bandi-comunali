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
    assert "Non attribuire a chi chiede dati che non ha dichiarato" in ISTRUZIONI
    assert "codice ATECO" in ISTRUZIONI
    assert "verifichi il codice della sua attività" in ISTRUZIONI


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
