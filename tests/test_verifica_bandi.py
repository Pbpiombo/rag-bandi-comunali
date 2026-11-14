"""Verifica delle citazioni ai singoli bandi: etichette [Dn.k] e atti.

Come test_verifica.py, non chiama il modello: costruisce risposte finte.
"""

import pytest

from src.chains.router import formatta_dati
from src.database.modelli import Risultato, VoceBando
from src.verification.controllo import numeri_atto, riassumi, verifica

PARCHEGGI = VoceBando(
    "«Bando parcheggi 2026» (Regione Toscana) | scade il 2026-11-30 "
    "| atto: decreto dirigenziale n. 18191 | url: https://esempio.it/parcheggi",
    "Portale, decreto dirigenziale n. 18191 (dati estratti il 2026-11-11)",
)
DATI_ENTI = VoceBando(
    "«Progettualità sui dati» (Regione Toscana) | a sportello fino al 2027-07-18 "
    "| atto: decreto dirigenziale n. 21441 | url: https://esempio.it/dati",
    "Portale, decreto dirigenziale n. 21441 (dati estratti il 2026-11-11)",
)
ELENCO = Risultato(
    "Bandi aperti a cui un Comune può presentare domanda (alla data del "
    "2026-11-11), 2 in archivio:\n"
    f"- [#1] {PARCHEGGI.testo}\n- [#2] {DATI_ENTI.testo}",
    fonti=[PARCHEGGI.fonte, DATI_ENTI.fonte],
    voci=[PARCHEGGI, DATI_ENTI],
)
DATI = [("bandi_aperti_per_ente", ELENCO)]


def esiti_di(risposta: str):
    return verifica(risposta, [], DATI)


# --- numeri d'atto in una citazione ---


@pytest.mark.parametrize(
    ("citazione", "attesi"),
    [
        ("decreto dirigenziale n. 18191 del 7/8/2026", ["18191"]),
        ("Decreto n. 13543/2026", ["13543"]),
        ("DGR 1081 del 7/9/2026", ["1081"]),
        ("delibera di Giunta regionale n. 894", ["894"]),
        ("decreto del 29 ottobre", []),
        ("decreto 12/10/2026", []),
        ("Regione Toscana, pag. 11", []),
    ],
)
def test_numeri_atto(citazione, attesi):
    assert numeri_atto(citazione) == attesi


# --- dati citati con l'etichetta del bando ---


def test_dato_del_bando_citato_con_la_sua_etichetta():
    esiti = esiti_di("Scade il 2026-11-30 (fonte: [D1.1], Regione).")
    assert riassumi(esiti) == {"verificato": 1, "non_trovato": 0, "non_citato": 0}
    assert esiti[0].frammenti == ["D1.1"]


def test_data_in_lettere_contro_la_riga_iso_del_bando():
    (esito,) = esiti_di("Scade il 30 novembre 2026 (fonte: [D1.1], Regione).")
    assert esito.stato == "verificato"
    assert esito.frammenti == ["D1.1"]


def test_dato_di_un_altro_bando_non_trovato_con_il_bando_giusto():
    (esito,) = esiti_di("Scade il 2026-11-30 (fonte: [D1.2], Regione).")
    assert esito.stato == "non_trovato"
    assert esito.dettaglio == "presente invece in ['D1.1']"


# --- numero del decreto nella citazione ---


def test_decreto_del_bando_citato():
    esiti = esiti_di(
        "Scade il 2026-11-30 (fonte: [D1.1], decreto dirigenziale n. 18191)."
    )
    assert [(e.tipo, e.valore, e.stato) for e in esiti] == [
        ("data", "2026-11-30", "verificato"),
        ("atto", "18191", "verificato"),
    ]


def test_decreto_di_un_altro_bando_non_trovato():
    """Il caso visto nell'app: la data giusta, il decreto di un altro bando."""
    esiti = esiti_di(
        "Scade il 2026-11-30 (fonte: [D1.1], decreto dirigenziale n. 21441)."
    )
    (atto,) = [e for e in esiti if e.tipo == "atto"]
    assert atto.stato == "non_trovato"
    assert atto.valore == "21441"
    assert atto.dettaglio == "presente invece in ['D1.2']"


def test_decreto_inesistente():
    esiti = esiti_di("Scade il 2026-11-30 (fonte: [D1.1], decreto n. 99999).")
    (atto,) = [e for e in esiti if e.tipo == "atto"]
    assert atto.stato == "non_trovato"
    assert atto.dettaglio == "non presente nella riga del bando citato"


def test_data_del_decreto_nella_citazione_senza_data_nella_riga():
    """Il caso di parcheggi-2026 prima della correzione: atto senza data."""
    esiti = esiti_di(
        "Scade il 2026-11-30 "
        "(fonte: [D1.1], decreto dirigenziale n. 18191 del 7/8/2026)."
    )
    assert [(e.tipo, e.valore, e.stato) for e in esiti] == [
        ("data", "2026-11-30", "verificato"),
        ("atto", "18191", "verificato"),
        ("data", "7/8/2026", "non_trovato"),
    ]
    assert esiti[2].dettaglio == (
        "l'atto 18191 compare nella fonte citata senza questa data"
    )


def test_data_del_decreto_nella_citazione_con_la_data_nella_riga():
    """Dopo la correzione: la riga scrive la data in lettere, la citazione no."""
    riga = (
        "«Bando parcheggi 2026» (Regione Toscana) | scade il 2026-11-30 "
        "| atto: Decreto dirigenziale 18191 del 7 agosto 2026"
    )
    elenco = Risultato(
        f"Bandi aperti:\n- [#1] {riga}",
        fonti=["Portale"],
        voci=[VoceBando(riga, "Portale")],
    )
    esiti = verifica(
        "Scade il 30/11/2026 "
        "(fonte: [D1.1], decreto dirigenziale n. 18191 del 07-08-2026).",
        [],
        [("bandi_aperti_per_ente", elenco)],
    )
    assert [(e.tipo, e.stato) for e in esiti] == [
        ("data", "verificato"),
        ("atto", "verificato"),
        ("data", "verificato"),
    ]


def test_decreto_con_il_blocco_non_si_controlla():
    """Con [D1] non si sa a quale bando si riferisce l'atto: non si controlla."""
    esiti = esiti_di("Ci sono due bandi (fonte: [D1], decreto n. 21441).")
    assert not [e for e in esiti if e.tipo == "atto"]


# --- intestazione del blocco nella riga del bando ---

# La data dell'archivio sta solo nell'intestazione del blocco: le righe e
# le fonti dei bandi hanno la data di verifica, diversa
ELENCO_DEL_12 = Risultato(
    ELENCO.testo.replace("alla data del 2026-11-11", "alla data del 2026-11-12"),
    fonti=ELENCO.fonti,
    voci=ELENCO.voci,
)


def test_data_dell_intestazione_citata_con_la_riga_del_bando():
    """Il falso negativo della prova del 12 novembre 2026 (domande 1 e 9)."""
    (esito,) = verifica(
        "Archivio aggiornato al 12/11/2026 (fonte: [D1.2], Regione).",
        [],
        [("bandi_aperti_per_ente", ELENCO_DEL_12)],
    )
    assert esito.stato == "verificato"
    assert esito.frammenti == ["D1.2"]


def test_i_numeri_dell_intestazione_non_valgono_per_la_riga():
    """'12 in archivio' non verifica un 12 attribuito a un bando."""
    elenco = Risultato(
        ELENCO_DEL_12.testo.replace("2 in archivio", "12 in archivio"),
        fonti=ELENCO.fonti,
        voci=ELENCO.voci,
    )
    dati = [("bandi_aperti_per_ente", elenco)]
    (con_la_riga,) = verifica("Ammessi 12 progetti (fonte: [D1.2], Regione).", [], dati)
    assert con_la_riga.stato == "non_trovato"
    # citato con il blocco, il numero c'e': e' nell'intestazione del blocco
    (con_il_blocco,) = verifica("Ci sono 12 bandi (fonte: [D1], Regione).", [], dati)
    assert con_il_blocco.stato == "verificato"


# La finestra di bandi_in_scadenza: "in scadenza entro 30 giorni". Nella
# prova dall'app (domanda d'esempio sui prossimi 30 giorni) il 30 citato
# con [D1.1] risultava non trovato. Il conteggio dell'intestazione resta
# escluso.
IN_SCADENZA = Risultato(
    "Bandi per i Comuni in scadenza entro 30 giorni (alla data del 2026-11-12), "
    f"4 in archivio:\n- [#1] {PARCHEGGI.testo}\n- [#2] {DATI_ENTI.testo}",
    fonti=ELENCO.fonti,
    voci=ELENCO.voci,
)


def test_la_finestra_dell_intestazione_vale_per_la_riga():
    (esito,) = verifica(
        "Scade nei prossimi 30 giorni (fonte: [D1.1], Regione).",
        [],
        [("bandi_in_scadenza", IN_SCADENZA)],
    )
    assert esito.stato == "verificato"
    assert esito.frammenti == ["D1.1"]


def test_una_finestra_diversa_non_vale_per_la_riga():
    (esito,) = verifica(
        "Scade nei prossimi 31 giorni (fonte: [D1.1], Regione).",
        [],
        [("bandi_in_scadenza", IN_SCADENZA)],
    )
    assert esito.stato == "non_trovato"


def test_il_conteggio_accanto_alla_finestra_non_vale_per_la_riga():
    """Con la finestra nell'intestazione, "12 in archivio" resta escluso."""
    elenco = Risultato(
        IN_SCADENZA.testo.replace("4 in archivio", "12 in archivio"),
        fonti=ELENCO.fonti,
        voci=ELENCO.voci,
    )
    (esito,) = verifica(
        "Ammessi 12 progetti (fonte: [D1.1], Regione).",
        [],
        [("bandi_in_scadenza", elenco)],
    )
    assert esito.stato == "non_trovato"


def test_quattro_in_archivio_non_verifica_un_quattro():
    """Il caso "4 in archivio": il 4 non e' mai verificato con la riga."""
    esiti = verifica(
        "Sono 4 i bandi in scadenza (fonte: [D1.1], Regione).",
        [],
        [("bandi_in_scadenza", IN_SCADENZA)],
    )
    assert not [e for e in esiti if e.valore == "4" and e.stato == "verificato"]


def test_data_dell_intestazione_falsificata():
    (esito,) = verifica(
        "Archivio aggiornato al 13/11/2026 (fonte: [D1.2], Regione).",
        [],
        [("bandi_aperti_per_ente", ELENCO_DEL_12)],
    )
    assert esito.stato == "non_trovato"


# --- citazione generica ---


def test_dato_di_un_solo_bando_citato_con_il_blocco():
    (esito,) = esiti_di("Scade il 2026-11-30 (fonte: [D1], Regione).")
    assert esito.stato == "citazione_generica"
    assert esito.dettaglio == (
        "presente solo nel bando [D1.1]: va citato con la sua etichetta"
    )
    assert riassumi([esito]) == {
        "verificato": 0,
        "non_trovato": 0,
        "non_citato": 0,
        "citazione_generica": 1,
    }


def test_dato_comune_a_piu_bandi_citato_con_il_blocco():
    (esito,) = esiti_di("Verificati il 2026-11-11 (fonte: [D1], Regione).")
    assert esito.stato == "verificato"


# --- blocco dei dati per il modello ---


def test_formatta_dati_mette_le_etichette():
    testo = formatta_dati([*DATI, ("bandi_per_tema", ELENCO)])
    assert "- [D1.1] «Bando parcheggi 2026»" in testo
    assert "- [D2.2] «Progettualità sui dati»" in testo
    assert "[#" not in testo
