"""Valori confrontabili: numeri, date, orari e riferimenti in una sola forma.

Funzioni pure: niente database, niente modello.
"""

from decimal import Decimal

import pytest

from src.normalizzazione import (
    articolo,
    atti_con_data,
    data,
    giorno_mese,
    numero,
    orario,
    periodo,
    riferimento,
    valori,
)

# --- numeri ---


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [
        ("322,00", "322"),
        ("€ 322,00", "322"),
        ("322 euro", "322"),
        ("19.570,00", "19570"),
        ("12.500", "12500"),
        ("1.200.000,00", "1200000"),
        ("9.2", "9.2"),
        ("9,2", "9.2"),
        ("343423.56", "343423.56"),
        ("19,5 milioni di euro", "19500000"),
        ("19.5 milioni", "19500000"),
        ("2 mila", "2000"),
        ("1,2 miliardi", "1200000000"),
    ],
)
def test_numero(testo, atteso):
    assert numero(testo) == Decimal(atteso)


def test_gli_zeri_decimali_non_contano():
    assert numero("322,00") == numero("322") == numero("322.00")


def test_lo_stesso_importo_con_e_senza_moltiplicatore():
    assert numero("19,5 milioni") == numero("19.500.000")
    assert numero("19,8 milioni") != numero("19.5 milioni")


@pytest.mark.parametrize("testo", ["1.2345", "trecento", "", "12,5,3", "€"])
def test_non_numeri(testo):
    assert numero(testo) is None


# --- date ---


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [
        ("2027-07-31", "2027-07-31"),
        ("31/07/2027", "2027-07-31"),
        ("31-07-2027", "2027-07-31"),
        ("31.07.2027", "2027-07-31"),
        ("1/1/2026", "2026-01-01"),
        ("31 luglio 2027", "2027-07-31"),
        ("31 Luglio 2027", "2027-07-31"),
        ("1° gennaio 2026", "2026-01-01"),
        ("1º gennaio 2026", "2026-01-01"),
        ("13 novembre 2026", "2026-11-13"),
    ],
)
def test_data(testo, atteso):
    assert data(testo) == atteso


@pytest.mark.parametrize(
    "testo", ["31/02/2026", "41/20/2022", "2026-13-01", "31 giugno 2026", "luglio"]
)
def test_date_impossibili_o_non_date(testo):
    assert data(testo) is None


def test_tre_e_tredici_novembre_sono_diversi():
    assert data("3 novembre 2026") != data("13 novembre 2026")


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [
        ("15 ottobre", "10-15"),
        ("30/06", "06-30"),
        ("29 febbraio", "02-29"),
        ("31/06", None),
        ("41/2022", None),
    ],
)
def test_giorno_mese(testo, atteso):
    assert giorno_mese(testo) == atteso


# --- orari ---


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [
        ("12:00", "12:00"),
        ("ore 12", "12:00"),
        ("ore 12.00", "12:00"),
        ("ore 9.30", "09:30"),
        ("25:00", None),
    ],
)
def test_orario(testo, atteso):
    assert orario(testo) == atteso


# --- valori di un testo ---


def test_le_cifre_di_una_data_non_sono_numeri():
    v = valori("Domande entro il 28/04/2026.")
    assert v.date == {"2026-04-28"}
    assert v.giorni_mese == {"04-28"}
    assert v.anni == {2026}
    assert v.numeri == set()


def test_una_percentuale_non_ne_contiene_un_altra():
    v = valori("Il contributo e' pari all'80% della spesa.")
    assert v.percentuali == {Decimal(80)}
    assert Decimal(8) not in v.percentuali
    assert v.numeri == set()


@pytest.mark.parametrize(
    "testo", ["pari a 80 per cento", "pari a 80 punti percentuali", "pari a 80 %"]
)
def test_forme_della_percentuale(testo):
    assert valori(testo).percentuali == {Decimal(80)}


def test_un_importo_non_ne_contiene_un_altro():
    v = valori("Contributo fino a € 150.000,00.")
    assert v.numeri == {Decimal(150000)}
    assert Decimal(50000) not in v.numeri


def test_un_giorno_non_ne_contiene_un_altro():
    v = valori("Le domande si presentano entro il 13 novembre 2026.")
    assert v.date == {"2026-11-13"}
    assert "2026-11-03" not in v.date


def test_importo_con_moltiplicatore():
    v = valori("Una dotazione complessiva di 19.5 milioni di euro.")
    assert v.numeri == {numero("19,5 milioni")}


def test_tabella_di_importi():
    v = valori("Costo per personale € 9.000,00 € 9.000,00 € 18.000,00")
    assert v.numeri == {Decimal(9000), Decimal(18000)}


def test_anno_da_solo_e_anche_un_numero():
    v = valori("Programma operativo nel 2026, per 1834 abitanti.")
    assert v.anni == {2026}
    assert v.numeri == {Decimal(2026), Decimal(1834)}


def test_periodo():
    v = valori("Programmazione 2021-2027.")
    assert v.periodi == {"2021-2027"}
    assert v.anni == {2021, 2027}
    assert v.riferimenti == set()
    assert v.numeri == set()


def test_periodo_con_la_barra_e_anche_un_riferimento():
    v = valori("Quadro economico a.s. 2026/2027")
    assert v.periodi == {"2026-2027"}
    assert v.riferimenti == {"2026/2027"}


def test_riferimento_normativo():
    v = valori("ai sensi della legge n. 41/2022 e dell'art. 54")
    assert v.riferimenti == {"41/2022"}
    assert v.articoli == {"art 54"}
    assert v.numeri == set()


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [
        ("decreto n. 1234 del 12/03/2026", {"1234/2026"}),
        ("decreto dirigenziale 18191 del 7/8/2026", {"18191/2026"}),
        ("DGR n. 1081 del 7 settembre 2026", {"1081/2026"}),
        ("delibera n. 894 dell'11/02/2025", {"894/2025"}),
        ("decreto del 29/10/2026", set()),
        ("entro il 15 del mese, cioè il 15/10/2026", set()),
    ],
)
def test_atto_con_data_vale_anche_come_riferimento(testo, atteso):
    assert valori(testo).riferimenti == atteso


def test_atti_con_data_sono_coppie():
    testo = (
        "Decreto dirigenziale n. 9550 del 28/04/2026, modificato con decreto "
        "21128 del 24 settembre 2026"
    )
    assert atti_con_data(testo) == {
        ("9550", "2026-04-28"),
        ("21128", "2026-09-24"),
    }
    assert atti_con_data("decreto dirigenziale n. 18191") == set()


def test_l_atto_con_data_resta_numero_e_data():
    v = valori("decreto n. 1234 del 12/03/2026")
    assert v.numeri == {Decimal(1234)}
    assert v.date == {"2026-03-12"}


def test_un_importo_non_e_un_articolo():
    v = valori("Il diritto di segreteria e' di 54 euro.")
    assert v.articoli == set()
    assert v.numeri == {Decimal(54)}


def test_articolo_con_comma():
    v = valori("ai sensi dell'articolo 54, comma 2, e del par. 3")
    assert v.articoli == {"art 54", "art 54 comma 2", "par 3"}
    assert v.numeri == set()


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [
        ("art. 54", "art 54"),
        ("art 54", "art 54"),
        ("articolo 54", "art 54"),
        ("art. 54, comma 2", "art 54 comma 2"),
        ("par. 3", "par 3"),
        ("paragrafo 3", "par 3"),
        ("punto 3", "punto 3"),
        ("lett. 3", "lett 3"),
        ("54", None),
    ],
)
def test_articolo(testo, atteso):
    assert articolo(testo) == atteso


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [("n. 41/2022", "41/2022"), ("41/2022", "41/2022"), ("n. 041/2022", "41/2022")],
)
def test_riferimento(testo, atteso):
    assert riferimento(testo) == atteso


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [
        ("2021-2027", "2021-2027"),
        ("2021 – 2027", "2021-2027"),
        ("2026/2027", "2026-2027"),
    ],
)
def test_periodo_scritto_da_solo(testo, atteso):
    assert periodo(testo) == atteso


def test_date_senza_anno():
    v = valori("entro il 30/06 o, per la seconda finestra, il 15 ottobre")
    assert v.giorni_mese == {"06-30", "10-15"}
    assert v.date == set()


def test_orari():
    v = valori("entro le ore 12:00 del 15/10/2026, oppure alle 9:30")
    assert v.orari == {"12:00", "09:30"}
    assert v.date == {"2026-10-15"}


def test_codici():
    v = valori("CUP J51B21000420006, CIG 12345678-9")
    assert v.codici == {"J51B21000420006", "12345678-9"}


def test_data_iso_e_in_lettere_coincidono():
    assert valori("scade il 2027-07-31").date == valori("scade il 31 luglio 2027").date


# --- codici con i punti e trattini tipografici (prova del 13/11/2026) ---


def test_codici_ateco_sono_un_valore_solo():
    v = valori("settori ATECO 49.34.00, 93.11.90 e codice primario I 55.1 (alberghi)")
    assert v.codici == {"49.34.00", "93.11.90", "I55.1"}
    assert v.numeri == set()


def test_codice_con_sezione_vale_anche_senza_lettera():
    assert valori("codice I 55.10.00").codici == {"I55.10.00", "55.10.00"}


@pytest.mark.parametrize(
    ("testo", "numero_atteso"),
    [
        ("il valore 55.1 della tabella", Decimal("55.1")),
        ("a 12.5 chilometri", Decimal("12.5")),
    ],
)
def test_due_livelli_senza_lettera_maiuscola_restano_numeri(testo, numero_atteso):
    v = valori(testo)
    assert v.codici == set()
    assert numero_atteso in v.numeri


def test_trattini_tipografici_nelle_date_della_fonte():
    assert "2026-11-13" in valori("scade il 2026\u201111\u201113").date
    assert "2026-11-13" in valori("scade il 13\u201211\u20122026").date
