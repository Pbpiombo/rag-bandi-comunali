"""L'elenco dei bandi citati nella risposta, scritto dall'app.

Titolo e url vengono dalle voci dei risultati, cioe' dal database: della
risposta si usano solo le etichette [Dn.k].
"""

from src.database.modelli import Risultato, VoceBando, bandi_citati

NEVE = VoceBando("riga neve", "fonte", titolo="Bando neve", url="https://a/neve")
STRADE = VoceBando(
    "riga strade", "fonte", titolo="Fondo strade", url="https://b/strade"
)
SENZA_URL = VoceBando("riga", "fonte", titolo="Senza pagina")

ESITI = [
    ("bandi_aperti_per_ente", Risultato("elenco", voci=[NEVE, STRADE, SENZA_URL])),
    ("popolazione", Risultato("1834 abitanti")),
    ("dettaglio_bando", Risultato("dettaglio", voci=[STRADE])),
]


def test_un_bando_citato_ha_titolo_e_url():
    risposta = "Scade il 16 novembre (fonte: [D1.1], decreto n. 5)."

    assert bandi_citati(risposta, ESITI) == [NEVE]


def test_nell_ordine_della_prima_citazione_e_senza_doppioni():
    risposta = (
        "Strade (fonte: [D1.2], avviso). Neve [D1.1]. Ancora strade "
        "(fonte: [d1.2], avviso), e di nuovo neve (fonte: [D1.1], decreto)."
    )

    assert bandi_citati(risposta, ESITI) == [STRADE, NEVE]


def test_lo_stesso_bando_in_due_blocchi_compare_una_volta():
    risposta = "Strade (fonte: [D1.2], avviso) e (fonte: [D3.1], avviso)."

    assert bandi_citati(risposta, ESITI) == [STRADE]


def test_etichette_inesistenti_si_ignorano():
    risposta = "(fonte: [D9.1]) (fonte: [D1.7]) (fonte: [D2.1]) (fonte: [D0.1])"

    assert bandi_citati(risposta, ESITI) == []


def test_un_blocco_senza_riga_non_e_un_bando():
    risposta = "1834 abitanti (fonte: [D2], ISTAT); elenco (fonte: [D1])."

    assert bandi_citati(risposta, ESITI) == []


def test_una_voce_senza_url_non_si_mostra():
    assert bandi_citati("(fonte: [D1.3], atto)", ESITI) == []


def test_risposta_senza_etichette_o_senza_dati():
    assert bandi_citati("Non trovo la risposta nei documenti disponibili.", ESITI) == []
    assert bandi_citati("(fonte: [D1.1])", None) == []
