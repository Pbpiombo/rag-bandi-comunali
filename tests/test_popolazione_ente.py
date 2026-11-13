"""La popolazione dell'ente nei dati dati al modello, aggiunta dal programma.

Database su file temporaneo (db_su_file), perche' le interrogazioni aprono
la connessione da se'. Nessuna chiamata al modello.
"""

import sqlite3

import pytest

from src.chains.rag import BLOCCO_POPOLAZIONE, con_popolazione
from src.chains.router import formatta_dati
from src.database.modelli import Risultato
from src.verification.controllo import riassumi, verifica

COMUNE = "11111111111"
UNIONE = "33333333333"
FONTE = (
    "ISTAT bilancio demografico mensile - popolazione al 1 gennaio (dato provvisorio)"
)


@pytest.fixture
def archivio(db_su_file):
    """Un comune con la popolazione, e un'Unione senza."""
    c = sqlite3.connect(db_su_file)
    c.executemany(
        "INSERT INTO enti (codice_fiscale, nome, tipo, regione, provincia, fonte, "
        "verificato_il) VALUES (?, ?, ?, 'Toscana', 'Pistoia', 'prova', "
        "'2026-01-01')",
        [(COMUNE, "Comune di prova", "comune"), (UNIONE, "Unione di prova", "unione")],
    )
    c.executemany(
        "INSERT INTO popolazione (codice_ente, anno, residenti, fonte) "
        "VALUES (?, ?, ?, ?)",
        [(COMUNE, 2025, 1829, FONTE), (COMUNE, 2026, 1834, FONTE)],
    )
    c.commit()
    c.close()


def test_si_aggiunge_per_un_comune_con_dati(archivio):
    bandi = ("bandi_aperti_per_ente", Risultato("Bandi aperti: nessuno."))

    esiti = con_popolazione([bandi], COMUNE)

    assert [nome for nome, _ in esiti] == ["bandi_aperti_per_ente", BLOCCO_POPOLAZIONE]
    _, popolazione = esiti[1]
    assert popolazione.testo == "Dato più recente: 1834 abitanti al 1 gennaio 2026."
    assert popolazione.fonti == [FONTE]


def test_non_si_duplica_se_il_router_l_ha_chiesta(archivio):
    gia_chiesta = ("popolazione_variazione", Risultato("Tra il 2025 e il 2026..."))

    assert con_popolazione([gia_chiesta], COMUNE) == [gia_chiesta]


def test_non_si_aggiunge_per_l_unione(archivio):
    assert con_popolazione([], UNIONE) == []


def test_il_dato_aggiunto_si_verifica(archivio):
    esiti = con_popolazione([], COMUNE)
    assert "[D1] interrogazione: popolazione dell'ente" in formatta_dati(esiti)

    giusta = "Il Comune ha 1834 abitanti (fonte: [D1], ISTAT), sotto i 5.000."
    sbagliata = "Il Comune ha 1843 abitanti (fonte: [D1], ISTAT)."

    assert riassumi(verifica(giusta, [], esiti))["verificato"] == 1
    assert riassumi(verifica(sbagliata, [], esiti))["non_trovato"] == 1
