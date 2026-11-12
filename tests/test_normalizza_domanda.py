"""Normalizzazione della domanda prima di ogni ricerca dei frammenti."""

from src.chains.rag import recupera
from src.retrieval import normalizza_domanda

DOMANDA = "Quanto spetta a ciascuna Area interna nell'avviso per i capofila"


def test_le_quattro_forme_diventano_una():
    forme = [
        DOMANDA + "?",
        DOMANDA,
        DOMANDA.replace("'", "’") + "?",
        DOMANDA.replace("'", "’"),
    ]
    assert {normalizza_domanda(f) for f in forme} == {DOMANDA}


def test_virgolette_tipografiche_e_spazi():
    assert (
        normalizza_domanda("  Il bando «mercati  rionali» e “parcheggi” ?  ")
        == 'Il bando "mercati rionali" e "parcheggi"'
    )


def test_punto_interrogativo_solo_alla_fine():
    assert normalizza_domanda("Chi? Quando?") == "Chi? Quando"


class MotoreFinto:
    def __init__(self):
        self.domande = []

    def cerca(self, domanda, k=8):
        self.domande.append((domanda, k))
        return []


def test_recupera_cerca_con_la_domanda_normalizzata():
    motore = MotoreFinto()
    recupera(motore, DOMANDA.replace("'", "’") + "?", k=10)
    assert motore.domande == [(DOMANDA, 10)]
