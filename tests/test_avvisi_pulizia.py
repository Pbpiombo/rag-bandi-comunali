"""Pulizia degli avvisi dei bandi (compito 19c-1).

Ricucitura prudente dei numeri (opzione di `pulisci`), righe ripetute,
contatti di persone, parole spezzate a fine riga. I casi dei numeri sono
quelli visti negli avvisi scaricati il 19/11/2026; i nomi e le email sono
inventati.
"""

import pytest
from langchain_core.documents import Document

from src.ingestion.avvisi import (
    EMAIL_OMESSA,
    NOME_OMESSO,
    TELEFONO_OMESSO,
    email_da_tenere,
    mascherato,
    pulisci_avviso,
    ricuci_parole,
    righe_ripetute,
    togli_contatti,
    togli_righe,
)
from src.ingestion.testo import pulisci, spezza

# --- ricucitura prudente ---

UNITI = [
    pytest.param("41/202 2", "41/2022", id="anno dopo la barra"),
    pytest.param("entro il 202 6", "entro il 2026", id="anno spezzato"),
    pytest.param("Reg. (UE) 1 060/2021", "Reg. (UE) 1060/2021", id="numero con /anno"),
    pytest.param("legge 394/1 991", "legge 394/1991", id="anno dopo la barra 2"),
    pytest.param("dal 2 004, poi", "dal 2004, poi", id="anno prima della virgola"),
    pytest.param("41 / 2022", "41/2022", id="spazi attorno alla barra"),
]

NON_UNITI = [
    pytest.param("B B1 40.000,00 Apicoltori", id="azione e importo"),
    pytest.param("Regolamento (UE) n. 2021/2115 4", id="regolamento e punteggio"),
    pytest.param("da 0 a 10 punti 50 90", id="due celle di punteggio"),
    pytest.param("artt. 5 3, 14, 17 e 41", id="virgola tra articoli"),
    pytest.param("punti 3, 4 e 5", id="virgola tra numeri distinti"),
    pytest.param("20 25.000,00", id="cifre che continuano dopo il punto"),
]


@pytest.mark.parametrize("ingresso, atteso", UNITI)
def test_prudente_unisce_anni_e_numeri_con_anno(ingresso, atteso):
    assert pulisci(ingresso, ricucitura="prudente") == atteso


@pytest.mark.parametrize("ingresso", NON_UNITI)
def test_prudente_non_fonde_celle_vicine(ingresso):
    assert pulisci(ingresso, ricucitura="prudente") == ingresso


def test_senza_opzione_pulisci_fonde_come_prima():
    # I 5 documenti caricati fino al 19/11/2026 restano con la regola di sempre
    assert pulisci("B B1 40.000,00") == "B B140.000,00"
    assert pulisci("artt. 5 3, 14") == "artt. 53,14"


def test_ricucitura_sconosciuta():
    with pytest.raises(ValueError):
        pulisci("testo", ricucitura="nessuna")


def test_spezza_passa_la_ricucitura():
    testo = "Risorse per azione. " * 20 + "B B1 40.000,00 Apicoltori. " * 10
    pagine = [Document(page_content=testo, metadata={"page": 1})]
    prudente = " ".join(c.page_content for c in spezza(pagine, ricucitura="prudente"))
    completa = " ".join(c.page_content for c in spezza(pagine))
    assert "B1 40.000,00" in prudente and "B140.000,00" not in prudente
    assert "B140.000,00" in completa


# --- righe ripetute ---


def test_righe_ripetute_in_piu_di_meta_delle_pagine():
    pagine = [f"Allegato 1 Bando\ntesto della pagina {n}\n{n}" for n in range(4)]
    ripetute = righe_ripetute(pagine)
    assert ripetute == {"Allegato 1 Bando": 4}
    assert togli_righe(pagine[0], ripetute) == "testo della pagina 0\n0"


def test_righe_ripetute_non_con_due_pagine():
    assert righe_ripetute(["Allegato 1 Bando\na", "Allegato 1 Bando\nb"]) == {}


# --- contatti ---


@pytest.mark.parametrize(
    "email",
    [
        "regionetoscana@postacert.toscana.it",
        "legal@cert.sviluppo.toscana.it",
        "urp_dpo@regione.toscana.it",
        "assistenza.fse@regione.toscana.it",
        "entiterritoriali@creditosportivo.it",
        "info@giovanisi.it",
    ],
)
def test_email_d_ufficio_restano(email):
    assert email_da_tenere(email)


def test_email_dedicata_al_bando_resta_con_il_titolo():
    assert email_da_tenere(
        "puntidigitalefacile@regione.toscana.it", "Punti Digitale Facile"
    )
    assert not email_da_tenere("puntidigitalefacile@regione.toscana.it")


@pytest.mark.parametrize(
    "email",
    [
        "tizio.caio@regione.toscana.it",
        "t.caio@regione.toscana.it",
        # contiene "enti" ma non all'inizio di una parte
        "clementina.caia@regione.toscana.it",
    ],
)
def test_email_nominative_si_tolgono(email):
    testo, fatte = togli_contatti(f"scrivere a {email}.")
    assert testo == f"scrivere a {EMAIL_OMESSA}."
    assert [s.tipo for s in fatte] == ["email"]


def test_telefono_sulla_riga_di_una_persona():
    testo, fatte = togli_contatti("dott. Tizio Caio tel. 055 4381234")
    assert TELEFONO_OMESSO in testo and "4381234" not in testo
    assert [s.tipo for s in fatte] == ["telefono"]


def test_numero_verde_resta():
    riga = "dott. Tizio Caio, numero verde 800.298.278"
    assert togli_contatti(riga) == (riga, [])


def test_numero_di_protocollo_resta():
    # 25205, p. 3: "Toscana Diffusa" ha la forma di un nome proprio
    riga = "“Valorizzazione della Toscana Diffusa”, trasmesse con Nota Prot. 0230434 del 07/04/2025;"
    assert togli_contatti(riga) == (riga, [])


def test_codice_fiscale_e_partita_iva_restano():
    riga = "Tizio Caio Spa - CF 00644160582 - PI 00919631002"
    assert togli_contatti(riga) == (riga, [])


@pytest.mark.parametrize(
    "ingresso, atteso",
    [
        pytest.param(
            "Responsabile del procedimento (RUP) è Tizio Caio in qualità di Responsabile",
            f"Responsabile del procedimento (RUP) è {NOME_OMESSO} in qualità di Responsabile",
            id="RUP",
        ),
        pytest.param(
            "RESPONSABILE UNICO DEL PROCEDIMENTO\nTizio Caio\n\nCONTENUTO",
            f"RESPONSABILE UNICO DEL PROCEDIMENTO\n{NOME_OMESSO}\n\nCONTENUTO",
            id="nome sulla riga dopo",
        ),
        pytest.param(
            "è il Dirigente del Settore Tizio Caio; domicilio digitale",
            f"è il Dirigente del Settore {NOME_OMESSO}; domicilio digitale",
            id="dirigente del settore",
        ),
        pytest.param(
            "il responsabile del procedimento è il dott. Tizio Caio.",
            f"il responsabile del procedimento è il dott. {NOME_OMESSO}.",
            id="con il titolo",
        ),
    ],
)
def test_nomi_dopo_le_formule(ingresso, atteso):
    testo, fatte = togli_contatti(ingresso)
    assert testo == atteso
    assert [s.tipo for s in fatte] == ["nome"]


@pytest.mark.parametrize(
    "riga",
    [
        "Dirigente del Settore Politiche Sociali;",
        "il responsabile del procedimento è il Dirigente del Settore Politiche di sostegno",
        "il responsabile del procedimento è:\nIl Settore “Produzioni agricole”",
    ],
)
def test_uffici_dopo_le_formule_restano(riga):
    assert togli_contatti(riga) == (riga, [])


# --- parole spezzate ---


def test_parole_spezzate_a_fine_riga():
    assert ricuci_parole("tale da ri- \nchiedere tecnologie") == (
        "tale da richiedere tecnologie",
        1,
    )


@pytest.mark.parametrize("testo", ["periodo 2021-\n2027", "PR-\nFESR", "ri-\nCHIEDERE"])
def test_parole_spezzate_solo_tra_minuscole(testo):
    assert ricuci_parole(testo) == (testo, 0)


# --- insieme ---


def test_pulisci_avviso():
    pagine = [
        "Allegato A\npagina 1\nRUP: Tizio Caio\n",
        "Allegato A\npagina 2 da ri-\nchiedere\n",
        "Allegato A\npagina 3 com-\nmi\nscrivere a tizio.caio@regione.toscana.it\n",
    ]
    esito = pulisci_avviso(pagine)
    assert esito.pagine[0] == f"pagina 1\nRUP: {NOME_OMESSO}\n"
    assert esito.pagine[1] == "pagina 2 da richiedere\n"
    assert [r.riga for r in esito.righe_tolte] == ["Allegato A"]
    assert [p for p, _ in esito.contatti] == [1, 3]
    assert esito.parole_ricucite == 2


def test_mascherato():
    assert mascherato("tizio.caio@regione.toscana.it") == "ti…[29]"
