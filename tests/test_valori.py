"""Conversione dei valori estratti e distinzione tra problemi e avvisi.

I valori di dotazione sono quelli reali che hanno fatto fallire le
scansioni del portale toscano (scansioni.csv, esito "fallito"), riportati
come li ha registrati il motivo, compresi i due troncati a 100 caratteri.
"""

import pytest

from src.estrazione.bandi import CAMPI, Campo, converti_importo, valida

# (valore reale, numero atteso)
CONVERTIBILI = [
    # punto per le migliaia
    ("300.000 euro", 300000),
    ("400.000 euro", 400000),
    ("600.000 euro", 600000),
    ("1.000.000 euro", 1000000),
    ("1.850.000 euro", 1850000),
    ("262.070.000 euro", 262070000),
    ("905.131 euro", 905131),
    # con i decimali
    ("1.000.000,00 euro", 1000000),
    ("600.000,00 euro", 600000),
    ("1.200.000,00 euro", 1200000),
    ("159.178,81 euro", 159178.81),
    ("708.454,40 euro", 708454.40),
    ("2.125.363,20 euro", 2125363.20),
    ("769.378,67 euro", 769378.67),
    ("200.153,95 euro", 200153.95),
    ("7.695.865,25 euro", 7695865.25),
    # senza separatori
    ("300000 euro", 300000),
    # milioni
    ("100 milioni di euro", 100_000_000),
    ("150 milioni di euro", 150_000_000),
    ("2 milioni di euro", 2_000_000),
    # altri formati richiesti
    ("1,2 milioni di euro", 1_200_000),
    ("fino a 50.000 euro", 50000),
    ("€ 300.000", 300000),
    ("300.000,00 €", 300000),
]

# (valore reale o richiesto, motivo atteso)
NON_CONVERTIBILI = [
    (
        (
            "300.000 euro per Aziende/Enti SSR ed enti di ricerca toscani, "
            "più 30.000 euro per"
        ),
        "contiene piu' di un importo",
    ),
    (
        "238.440,00 euro (con possibile incremento fino a 3.485.957,00 euro)",
        "contiene piu' di un importo",
    ),
    ("da 10.000 a 50.000 euro", "contiene piu' di un importo"),
    ("oltre 310 milioni di euro", "importo non esatto"),
    ("circa 200.000 euro", "importo non esatto"),
    ("12.5", "separatori non riconosciuti"),
    ("a seconda della graduatoria", "formato non riconosciuto"),
]


@pytest.mark.parametrize(("valore", "atteso"), CONVERTIBILI)
def test_importi_reali_si_convertono(valore, atteso):
    assert converti_importo("dotazione", valore) == (pytest.approx(atteso), None)


@pytest.mark.parametrize(("valore", "motivo"), NON_CONVERTIBILI)
def test_importi_ambigui_restano_vuoti_con_il_motivo(valore, motivo):
    assert converti_importo("dotazione", valore) == (None, motivo)


def test_i_numeri_restituiti_come_numeri_passano_invariati():
    assert converti_importo("dotazione", 300000) == (300000.0, None)
    assert converti_importo("contributo_perc", 80.5) == (80.5, None)


def test_un_vero_falso_non_e_un_importo():
    assert converti_importo("dotazione", True)[0] is None


def test_fino_a_vale_solo_per_i_tetti():
    assert converti_importo("contributo_max", "fino a 50.000 euro") == (50000, None)
    assert converti_importo("costo_min", "fino a 50.000 euro") == (
        None,
        "indica un tetto, non un minimo",
    )


# --- valida: problemi e avvisi ---


def _campi(**valori) -> list[Campo]:
    """Un bando completo e valido, con i valori indicati al posto dei predefiniti."""
    predefiniti = {
        "titolo": "Bando di prova",
        "ente": "Regione Toscana",
        "beneficiari": "Comuni della Toscana",
        "ammette_comuni": True,
        "a_sportello": False,
        "scadenza": "2026-12-31",
    }
    predefiniti.update(valori)
    return [
        Campo(nome, predefiniti.get(nome), "alta", "", critico)
        for nome, (_, critico) in CAMPI.items()
    ]


def test_bando_valido_senza_problemi_ne_avvisi():
    riga, problemi, avvisi = valida(_campi(dotazione="300.000 euro"))
    assert (problemi, avvisi) == ([], [])
    assert riga["dotazione"] == 300000


@pytest.mark.parametrize(
    ("campo", "valore"),
    [
        ("dotazione", "oltre 310 milioni di euro"),
        ("costo_max", "da 10.000 a 50.000 euro"),
        ("contributo_perc", "80%"),
        ("apertura", "1 marzo 2026"),
    ],
)
def test_campo_non_bloccante_resta_vuoto_con_avviso(campo, valore):
    riga, problemi, avvisi = valida(_campi(**{campo: valore}))

    assert problemi == []
    assert riga[campo] is None
    assert len(avvisi) == 1
    assert avvisi[0].startswith(f"{campo}: valore '{valore}'")
    assert avvisi[0].endswith("lasciato vuoto")


@pytest.mark.parametrize(
    ("campo", "valore"),
    [
        ("scadenza", "31 marzo 2026"),
        ("a_sportello", "forse"),
        ("ammette_comuni", "dipende"),
    ],
)
def test_campo_bloccante_non_convertibile_e_un_problema(campo, valore):
    _, problemi, avvisi = valida(_campi(**{campo: valore}))

    assert any(p.startswith(f"{campo}: valore '{valore}'") for p in problemi)
    assert avvisi == []


@pytest.mark.parametrize("campo", ["titolo", "ente", "beneficiari", "ammette_comuni"])
def test_campo_bloccante_mancante_e_un_problema(campo):
    _, problemi, _ = valida(_campi(**{campo: None}))
    assert any(p.startswith(campo) for p in problemi)


def test_scadenza_assente_non_e_un_problema_di_validazione():
    """Senza scadenza decide decidi_automatico, non valida."""
    _, problemi, _ = valida(_campi(scadenza=None))
    assert problemi == []


def test_a_sportello_assente_vale_zero():
    riga, problemi, _ = valida(_campi(a_sportello=None))
    assert (riga["a_sportello"], problemi) == (0, [])
