"""Contatti d'ufficio letti dal testo, senza dati di persone.

Testi inventati sul modello delle pagine viste il 13/11/2026; nessun
nome o indirizzo reale di persona.
"""

import pytest

from src.estrazione.contatti import (
    contatti_da_testo,
    email_nominativa,
    email_ufficio,
)


@pytest.mark.parametrize(
    "email",
    [
        "mario.rossi@regione.toscana.it",
        "m.rossi@regione.toscana.it",
        "mario_rossi@esempio.it",
        "mario-rossi@esempio.it",
        "Anna.Maria.Bianchi@esempio.it",
        "mario.rossi2@esempio.it",
    ],
)
def test_le_email_nominative_si_riconoscono(email):
    assert email_nominativa(email)
    assert not email_ufficio(email, "Bando Neve 2026")


@pytest.mark.parametrize(
    ("email", "titolo"),
    [
        ("info@creditosportivo.it", None),
        ("avvisosociale2026@regione.toscana.it", None),
        ("puntidigitalefacile@regione.toscana.it", "Rete dei Punti Digitale Facile"),
        ("sistemaneve@sviluppo.toscana.it", "Bando Neve Spese di Funzionamento 2026"),
        ("supportoneve@sviluppo.toscana.it", None),
        ("entiterritoriali@creditosportivo.it", None),
    ],
)
def test_le_email_d_ufficio_passano(email, titolo):
    assert email_ufficio(email, titolo)


def test_nel_dubbio_un_email_si_scarta():
    # Ne' parola d'ufficio, ne' cifra, ne' parola del titolo: potrebbe
    # essere una persona
    assert not email_ufficio("mrossi@esempio.it", "Bando parcheggi 2026")


def test_contatti_di_una_pagina_con_email_e_numero_verde():
    testo = (
        "Per saperne di più\n"
        "scrivere a puntidigitalefacile@regione.toscana.it .\n"
        "Assistenza: numero verde 800 123 456\n"
        "Partita IVA 01234567890\n"
    )

    assert contatti_da_testo(testo, "Rete dei Punti Digitale Facile") == (
        "email: puntidigitalefacile@regione.toscana.it; telefono: 800 123 456"
    )


def test_la_riga_di_una_persona_non_da_contatti():
    testo = (
        "Supporto ai contenuti: scrivere a mario.rossi@regione.toscana.it, "
        "tel. 055 1234567\n"
        "Orari di apertura:\n"
        "Ufficio bandi: tel. 055 7654321\n"
    )

    assert contatti_da_testo(testo) == "telefono: 055 7654321"


# I casi della prova del 13/11/2026, con nomi inventati


@pytest.mark.parametrize(
    "testo",
    [
        "Mario Rossi - tel. 055/4380000 (ufficio)\n",
        "Referenti per l'ufficio:\nMario Rossi:\ntel.: 055/4380000 - 055/4380001\n",
        "mail: mario.rossi@regione.toscana.it\nTelefono ufficio: 055/4380000\n",
        "Settore: tel. 055/4380000, e-mail: mario.rossi @regione.toscana.it\n",
        "Ufficio: contattare Anna Bianchi al numero 0664000000\n",
    ],
)
def test_i_numeri_vicini_a_una_persona_si_scartano(testo):
    assert contatti_da_testo(testo) is None


def test_un_numero_senza_un_servizio_nominato_si_scarta():
    testo = "oppure contattare il numero 0554380000 martedì dalle 10 alle 12\n"

    assert contatti_da_testo(testo) is None


def test_un_servizio_di_assistenza_tiene_il_suo_numero():
    testo = (
        "Per le imprese è attivo un servizio di assistenza telefonica al "
        "numero 06-77700000 dal lunedì al venerdì\n"
    )

    assert contatti_da_testo(testo) == "telefono: 06-77700000"


def test_i_telefoni_con_un_titolo_di_persona_si_scartano():
    testo = "Referente: dott. Rossi, tel. 055 1234567\n"

    assert contatti_da_testo(testo) is None


def test_un_numero_senza_parola_d_ufficio_non_e_un_telefono():
    testo = "Decreto 12345 del 06 11 2026, protocollo 0551234567\n"

    assert contatti_da_testo(testo) is None


def test_cellulari_fax_e_righe_del_sito_si_scartano():
    testo = (
        "Contatti: tel. 333 1234567\n"
        "Fax 0583 123456\n"
        "Hai problemi di navigazione? Scrivici a comunicazione@esempio.it\n"
    )

    assert contatti_da_testo(testo) is None


def test_senza_contatti_restituisce_none():
    assert contatti_da_testo("Il bando finanzia interventi sulle strade.") is None


def test_lo_stesso_numero_in_forme_diverse_compare_una_volta():
    testo = (
        "Numero verde 800327723\n"
        "Assistenza: numero verde 800 327 723\n"
        "Servizio clienti: +39 06 1234567, oppure 06-1234567\n"
    )

    assert contatti_da_testo(testo) == "telefono: 800327723, +39 06 1234567"


def test_gli_indirizzi_ripetuti_compaiono_una_volta():
    testo = "Scrivere a info@esempio.it\nOppure a INFO@esempio.it.\n"

    assert contatti_da_testo(testo) == "email: info@esempio.it"
