"""Registro da più cartelle e atto a mano verificato (compito 19c-4).

Usa la cartella di prova di tests/test_registra_avvisi.py; tutto inventato.
"""

import pytest

import scripts.ingestione.elenco_pdf_bandi as elenco
import scripts.ingestione.registra_avvisi as script
from src.estrazione import pdf_bando as pb
from tests.test_pdf_bando import pdf_minimo
from tests.test_registra_avvisi import TESTO_AVVISO, URL_CREDITO, URL_DECRETO, Archivio

VECCHIA = "2026-11-19"
NUOVA = "2026-11-20"
PRIMA_PAGINA = ["IL MINISTRO DELLA PROVA", "Criteri di accesso al fondo", "testo"]
ULTIMA_PAGINA = [
    "Il presente decreto e' trasmesso.",
    "Roma, 3 febbraio 2025",
    "IL MINISTRO",
]
URL_DECRETO_NUOVO = URL_CREDITO.format(nome="BANDO-DM-03.02.2025-n.-12_Criteri-signed")
LINK = "D.M. 3 febbraio 2025, rep. n. 12"


@pytest.fixture
def cartelle(tmp_path, monkeypatch):
    monkeypatch.setattr(script, "DECISIONI_A_MANO", {})
    vecchia = Archivio(tmp_path / VECCHIA)
    vecchia.aggiungi(
        "bando-a",
        URL_DECRETO.format(id=1, numero=100, allegato="A"),
        pb.AVVISO,
        pdf_minimo(TESTO_AVVISO),
    )
    vecchia.aggiungi(
        "bando-a",
        URL_CREDITO.format(nome="Avviso-n.-1-Prova-Proroga-del-termine"),
        pb.PROROGA,
        pdf_minimo([["Proroga del termine"]]),
    )
    nuova = Archivio(tmp_path / NUOVA)
    nuova.aggiungi(
        "bando-n",
        URL_DECRETO_NUOVO,
        pb.AVVISO,
        pdf_minimo([PRIMA_PAGINA, *TESTO_AVVISO, ULTIMA_PAGINA]),
    )
    scrivi_pagina(tmp_path / NUOVA, LINK)
    return vecchia.scrivi(), nuova.scrivi(), nuova


def scrivi_pagina(cartella, testo_del_link):
    """La pagina salvata del bando, con il link al decreto."""
    pagina = elenco.file_pagina(cartella, "bando-n")
    pagina.parent.mkdir(parents=True, exist_ok=True)
    pagina.write_text(
        f'<html><body><a href="{URL_DECRETO_NUOVO}">{testo_del_link}</a></body></html>',
        encoding="utf-8",
    )


def righe_del_file(percorso):
    return percorso.read_bytes().decode("utf-8-sig").split("\r\n")


def test_le_righe_vecchie_restano_identiche(cartelle, tmp_path):
    vecchia, nuova, _ = cartelle
    processed = tmp_path / "processed"
    processed.mkdir()
    assert script.main(["--data", VECCHIA], [vecchia], processed) == 0
    prima = righe_del_file(processed / script.NOME_FILE)
    assert (
        script.main(["--data", VECCHIA, "--data", NUOVA], [vecchia, nuova], processed)
        == 0
    )
    dopo = righe_del_file(processed / script.NOME_FILE)
    # ogni riga di prima c'è ancora, carattere per carattere; una sola in più
    assert [r for r in prima if r not in dopo] == []
    assert len([r for r in dopo if r]) == len([r for r in prima if r]) + 1
    nuove = [r for r in dopo if r not in prima]
    assert len(nuove) == 1 and "bando-n" in nuove[0]


def test_ordine_delle_cartelle_indifferente(cartelle, tmp_path):
    vecchia, nuova, _ = cartelle
    a = script.costruisci_da([(vecchia, VECCHIA), (nuova, NUOVA)])
    b = script.costruisci_da([(nuova, NUOVA), (vecchia, VECCHIA)])
    assert a == b


def test_data_della_cartella_di_ogni_file(cartelle):
    vecchia, nuova, _ = cartelle
    righe = script.costruisci_da([(vecchia, VECCHIA), (nuova, NUOVA)])
    deciso_il = {r["id_bandi"]: r["deciso_il"] for r in righe}
    assert deciso_il == {"bando-a": VECCHIA, "bando-n": NUOVA}


def test_stesso_file_in_due_cartelle(cartelle):
    vecchia, _, _ = cartelle
    with pytest.raises(script.ErroreRegistro, match="nelle cartelle"):
        script.costruisci_da([(vecchia, VECCHIA), (vecchia, NUOVA)])


def test_una_cartella_per_ogni_data(cartelle, tmp_path):
    vecchia, _, _ = cartelle
    assert script.main(["--data", VECCHIA, "--data", NUOVA], [vecchia], tmp_path) == 1


# --- atto a mano verificato sulla prima pagina ---


DATA_NEL_FILE = script.Prova("data", "3 febbraio 2025", script.NEL_FILE)
NUMERO_NEL_LINK = script.Prova("numero di repertorio", "rep. n. 12", script.NEL_LINK)


def _con_decisione(nuova, monkeypatch, prove):
    decisione = script.Decisione(
        "decreto",
        pb.AVVISO,
        script.FRAMMENTI,
        "decreto di criteri generali",
        NUOVA,
        atto="D.M. 3 febbraio 2025, rep. n. 12",
        prove=prove,
    )
    monkeypatch.setattr(
        script, "DECISIONI_A_MANO", {nuova.elenco[-1]["sha256"]: decisione}
    )


def test_prova_su_una_pagina_diversa_dalla_prima(cartelle, monkeypatch):
    _, cartella, nuova = cartelle
    _con_decisione(nuova, monkeypatch, (DATA_NEL_FILE,))
    (riga,) = script.costruisci(cartella, NUOVA)
    assert riga["atto"] == "D.M. 3 febbraio 2025, rep. n. 12"
    assert riga["atto_origine"] == "a mano; data nel testo del file a pagina 3"
    assert (riga["classe"], riga["uso"], riga["deciso_da"]) == (
        pb.AVVISO,
        script.FRAMMENTI,
        script.A_MANO,
    )


def test_prova_sul_testo_del_link(cartelle, monkeypatch):
    _, cartella, nuova = cartelle
    _con_decisione(nuova, monkeypatch, (DATA_NEL_FILE, NUMERO_NEL_LINK))
    (riga,) = script.costruisci(cartella, NUOVA)
    assert riga["atto_origine"] == (
        "a mano; data nel testo del file a pagina 3; numero di repertorio nel "
        "testo del link sulla pagina del bando, assente nel testo del file"
    )


@pytest.mark.parametrize(
    "prove, testo_del_link, errore",
    [
        pytest.param(
            (NUMERO_NEL_LINK,), "D.M. 3 febbraio 2025", "non è nel testo del link",
            id="numero assente dal link",
        ),
        pytest.param(
            (script.Prova("data", "4 febbraio 2025", script.NEL_FILE),), LINK,
            "non è nel testo del file", id="data assente dal file",
        ),
        pytest.param((), LINK, "senza prove", id="nessuna prova"),
    ],
)  # fmt: skip
def test_prova_che_manca(cartelle, monkeypatch, prove, testo_del_link, errore):
    _, cartella, nuova = cartelle
    scrivi_pagina(cartella, testo_del_link)
    _con_decisione(nuova, monkeypatch, prove)
    with pytest.raises(script.ErroreRegistro, match=errore):
        script.costruisci(cartella, NUOVA)


def test_link_assente_dalla_pagina(cartelle, monkeypatch):
    _, cartella, nuova = cartelle
    elenco.file_pagina(cartella, "bando-n").write_text(
        "<html></html>", encoding="utf-8"
    )
    _con_decisione(nuova, monkeypatch, (NUMERO_NEL_LINK,))
    with pytest.raises(script.ErroreRegistro, match="nessun link al file"):
        script.costruisci(cartella, NUOVA)


# --- bandi aggiunti alla prova ---


def test_bandi_aggiunti_solo_con_bando():
    assert elenco.ids_della_prova([]) == elenco.PRIMA_PROVA
    aggiunto = elenco.BANDI_AGGIUNTI[0]
    assert elenco.ids_della_prova([aggiunto]) == (*elenco.PRIMA_PROVA, aggiunto)
    bandi = [
        (i, f"https://www.prova.it/{i}") for i in elenco.ids_della_prova([aggiunto])
    ]
    assert elenco.scegli_bandi(bandi, [aggiunto]) == [bandi[-1]]
    with pytest.raises(elenco.ErroreElenco):
        elenco.scegli_bandi(bandi, ["bando-sconosciuto"])
