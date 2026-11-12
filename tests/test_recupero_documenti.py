"""Scelta dei documenti nominati nella domanda e divisione dei posti (P2).

Funzioni pure: niente database, niente embedding. I titoli sono quelli dei
5 documenti in archivio al 12 novembre 2026.
"""

from langchain_core.documents import Document

from src.recupero_documenti import (
    RecuperoPerDocumento,
    dividi_posti,
    documenti_nominati,
    ripulisci_domanda,
    unisci,
)

CAPOFILA = "Decreto n.9550 del 28-04-2026- Allegato A.pdf"
MERCATI = "Decreto_n.13287_del_10-06-2026-Allegato-A.pdf"
LINEE_GUIDA = (
    "4_evoluzione-del-requisito-associativo-nella-snai-linee-guida-2021-2027.pdf"
)
LUDOTECHE = "PROGETTO_DEF_SNAI_C3_PROGETTO-SERVIZIO_SCHEMA_20260214_SIGNED.pdf"
CENSIS = (
    "2_contributo-censis-individuazione-e-analisi-di-gruppi-omogenei-di-territori.pdf"
)

TITOLI = {
    CAPOFILA: "Avviso pubblico - Progetti di rafforzamento amministrativo degli "
    "enti Capofila delle Aree interne",
    MERCATI: "Avviso pubblico per manifestazione di interesse alla presentazione "
    "di progetti di investimento per la concessione di contributi a comuni su "
    "cui insistono mercati rionali",
    LINEE_GUIDA: "Evoluzione del requisito associativo nella Strategia Nazionale "
    "per le Aree Interne - Linee Guida 2021-2027",
    LUDOTECHE: "Progetto C3.1 Ludoteche di montagna - Scheda C3.1.d Appennino "
    "Pistoiese",
    CENSIS: "Supporto operativo alla Strategia delle Aree Interne - "
    "Individuazione e analisi di gruppi omogenei di territori e di politiche "
    "per il territorio per una meta lettura della SNAI",
}


def nominati(domanda: str, titoli: dict | None = None) -> set[str]:
    return set(documenti_nominati(domanda, titoli or TITOLI))


# --- documenti nominati ------------------------------------------------------


def test_un_avviso_nominato():
    domanda = (
        "Qual è il costo massimo giornaliero per un incarico professionale "
        "nell'avviso per il rafforzamento amministrativo dei capofila delle "
        "aree interne?"
    )
    # "aree interne" sta anche nei titoli delle linee guida e del Censis, ma
    # lì è contenuto strettamente nelle parole trovate per l'avviso.
    assert nominati(domanda) == {CAPOFILA}


def test_avviso_mercati_rionali():
    assert nominati(
        "Nell'avviso per i mercati rionali, qual è il costo minimo e massimo?"
    ) == {MERCATI}


def test_due_avvisi_nominati():
    domanda = (
        "Chi può presentare domanda nell'avviso per il rafforzamento "
        "amministrativo e chi nell'avviso per i mercati rionali?"
    )
    assert nominati(domanda) == {CAPOFILA, MERCATI}


def test_progetto_nominato():
    assert nominati("Qual è il costo totale del progetto Ludoteche di montagna?") == {
        LUDOTECHE
    }


def test_parole_del_titolo_senza_nominare_un_documento():
    # Nessuna parola che introduce un documento: la restrizione non scatta.
    assert (
        nominati(
            "Quanti comuni sono compresi nelle aree interne della strategia 2021-2027?"
        )
        == set()
    )
    assert (
        nominati(
            "Quando il requisito associativo è assolto per i comuni già associati "
            "in un'Unione di Comuni montani?"
        )
        == set()
    )


def test_parola_documento_senza_titolo():
    assert (
        nominati("Quale percentuale di costi indiretti è ammessa nello stesso avviso?")
        == set()
    )


def test_una_sola_parola_del_titolo_non_basta():
    assert nominati("Cosa prevede l'avviso per i mercati?") == set()


def test_troppi_documenti_nessuna_restrizione():
    # "aree interne" con "documento": tre titoli alla pari, nessuno scelto.
    assert nominati("Cosa dice il documento sulle aree interne?") == set()


# --- titoli quasi uguali, come saranno i PDF dei bandi ------------------------

MUSEI = {
    "musei-2025.pdf": "Bando sistemi museali 2025",
    "musei-2026.pdf": "Bando sistemi museali 2026",
}


def test_titoli_quasi_uguali_senza_anno_li_prende_entrambi():
    assert nominati("Nel bando sistemi museali, chi può partecipare?", MUSEI) == {
        "musei-2025.pdf",
        "musei-2026.pdf",
    }


def test_titoli_quasi_uguali_con_anno_prende_quello_giusto():
    assert nominati("Nel bando sistemi museali 2026, chi può partecipare?", MUSEI) == {
        "musei-2026.pdf"
    }


# --- domanda ripulita --------------------------------------------------------


def ripulita(domanda: str) -> str:
    trovate = set().union(*documenti_nominati(domanda, TITOLI).values())
    return ripulisci_domanda(domanda, trovate)


def test_ripulisci_toglie_il_tratto_che_nomina_il_documento():
    assert (
        ripulita("Nell'avviso per i mercati rionali, qual è il costo minimo?")
        == "Nell', qual è il costo minimo?"
    )


def test_ripulisci_lascia_le_parole_del_titolo_fuori_dal_tratto():
    # "contributi" è nel titolo dell'avviso, ma qui è ciò che si chiede;
    # "decreto" non apre un tratto.
    assert (
        ripulita(
            "Con quale decreto è stato approvato l'avviso per i mercati "
            "rionali, e quali contributi prevede?"
        )
        == "Con quale decreto è stato approvato l', e quali contributi prevede?"
    )


def test_ripulisci_titolo_lungo_e_due_tratti():
    assert ripulita(
        "Qual è il costo massimo nell'avviso per il rafforzamento "
        "amministrativo dei capofila delle aree interne?"
    ) == ("Qual è il costo massimo nell'?")
    assert ripulita(
        "Chi può presentare domanda nell'avviso per il rafforzamento "
        "amministrativo e chi nell'avviso per i mercati rionali?"
    ) == ("Chi può presentare domanda nell' e chi nell'?")


def test_ripulisci_senza_parola_introduttiva_non_toglie_nulla():
    domanda = "Nel decreto sui mercati rionali, chi può partecipare?"
    assert ripulisci_domanda(domanda, {"mercati", "rionali"}) == domanda


# --- divisione dei posti -----------------------------------------------------


def test_dividi_posti():
    assert dividi_posti(10, 0) == [10]
    assert dividi_posti(10, 1) == [5, 5]
    assert dividi_posti(10, 2) == [4, 3, 3]
    assert sum(dividi_posti(7, 2)) == 7


def elemento(fonte: str, numero: int) -> tuple:
    documento = Document(
        page_content="", metadata={"fonte": fonte, "chunk_num": numero}
    )
    return (documento, 0.0, [f"densa #{numero + 1}"])


def chiavi(scelti: list) -> list[tuple]:
    return [(d.metadata["fonte"], d.metadata["chunk_num"]) for d, _, _ in scelti]


def test_unisci_alterna_e_rispetta_i_posti():
    generale = [elemento("g", i) for i in range(10)]
    documento = [elemento("d", i) for i in range(10)]
    scelti = unisci([generale, documento], [2, 3], 5)
    assert chiavi(scelti) == [("g", 0), ("d", 0), ("g", 1), ("d", 1), ("d", 2)]


def test_unisci_salta_i_doppioni_e_riempie_i_posti_vuoti():
    generale = [elemento("d", 0), elemento("g", 1), elemento("g", 2), elemento("g", 3)]
    documento = [elemento("d", 0)]  # già preso dalla ricerca generale
    scelti = unisci([generale, documento], [2, 2], 4)
    assert chiavi(scelti) == [("d", 0), ("g", 1), ("g", 2), ("g", 3)]


# --- recupero avvolto, con un motore finto ------------------------------------


class MotoreFinto:
    def __init__(self):
        self.chiamate = []

    def titoli(self):
        return TITOLI

    def cerca(self, domanda, k=8, fonte=None):
        self.chiamate.append((domanda, fonte))
        etichetta = fonte or "generale"
        return [elemento(etichetta, i) for i in range(k)]


def test_senza_documenti_nominati_una_sola_ricerca_identica():
    motore = MotoreFinto()
    risultati = RecuperoPerDocumento(motore).cerca("Quanti abitanti?", k=10)
    assert motore.chiamate == [("Quanti abitanti?", None)]
    assert len(risultati) == 10


def test_con_un_documento_ricerca_generale_e_ristretta():
    motore = MotoreFinto()
    domanda = "Nell'avviso per i mercati rionali, qual è il costo minimo?"
    risultati = RecuperoPerDocumento(motore).cerca(domanda, k=10)

    assert motore.chiamate[0] == (domanda, None)
    ripulita, fonte = motore.chiamate[1]
    assert fonte == MERCATI
    assert "mercati" not in ripulita.lower()

    fonti = [d.metadata["fonte"] for d, _, _ in risultati]
    assert fonti.count("generale") == 5
    assert fonti.count(MERCATI) == 5
    for documento, _, origini in risultati:
        ristretto = documento.metadata["fonte"] == MERCATI
        assert all(o.startswith("documento:") == ristretto for o in origini)
