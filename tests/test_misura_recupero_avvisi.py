"""Divisione dei fatti del passo 19d (scripts/diagnostica/misura_recupero_avvisi.py).

Tutto inventato: bandi, frasi, righe. Nessun PDF, nessun Chroma.
"""

from collections import Counter

import openpyxl
import pytest

import scripts.diagnostica.misura_recupero_avvisi as mr

INTESTAZIONE = (
    "id_bando",
    "titolo",
    "tipo_fatto",
    "registro",
    "domanda",
    "frase",
    "pagina_fisica",
    "in_tabella",
    "frase_solo_in_questo_bando",
    "anche_sulla_pagina_web",
    "note",
)


def fatto(riga, id_bando, frase, registro="semplice", in_tabella="no"):
    return {
        "riga": riga,
        "id_bando": id_bando,
        "frase": frase,
        "registro": registro,
        "in_tabella": in_tabella,
    }


@pytest.fixture
def fatti():
    """Tre bandi: alfa e beta gemelli (righe 3-12 e 6-14 identiche), gamma con quattro gemelli."""
    elenco = []
    for i in range(2, 9):
        elenco.append(fatto(i, "alfa", f"Frase alfa numero {i} del bando."))
    for i in range(9, 16):
        elenco.append(fatto(i, "beta", f"Frase beta numero {i} del bando."))
    for i in range(16, 24):
        elenco.append(fatto(i, "gamma", f"Frase gamma numero {i} del bando."))
    elenco[1]["frase"] = "Il termine è di 15 giorni."  # riga 3, alfa
    elenco[10]["frase"] = (
        "Il  termine è di 15\ngiorni."  # riga 12, beta: identica senza spazi
    )
    elenco[4]["frase"] = "Massimo 20% per le piccole imprese."  # riga 6, alfa
    elenco[12]["frase"] = "Massimo 20% per le piccole imprese."  # riga 14, beta
    elenco[2]["frase"] = "Primo pezzo della risposta [...] secondo pezzo [...] terzo"
    return elenco


GEMELLI = {3, 6, 12, 14, 17, 18, 19, 20}
FISSI = ((5, 13),)


def test_stesso_seme_stessa_divisione(fatti):
    primo = mr.dividi(fatti, GEMELLI, seme=7, fissi=FISSI)
    secondo = mr.dividi(list(reversed(fatti)), GEMELLI, seme=7, fissi=FISSI)
    assert primo == secondo


def test_ogni_fatto_una_volta_e_intero(fatti):
    meta, gruppo_di, _ = mr.dividi(fatti, GEMELLI, seme=7, fissi=FISSI)
    righe = mr.righe_divisione(fatti, meta, gruppo_di, GEMELLI)
    assert sorted(r["riga"] for r in righe) == sorted(f["riga"] for f in fatti)
    assert next(r for r in righe if r["riga"] == 4)["pezzi"] == 3
    assert set(meta.values()) == {mr.TARATURA, mr.CONTROLLO}


def test_frasi_identiche_e_gruppi_fissi_nella_stessa_meta(fatti):
    for seme in range(20):
        meta, gruppo_di, _ = mr.dividi(fatti, GEMELLI, seme=seme, fissi=FISSI)
        assert gruppo_di[3] == gruppo_di[12]
        assert meta[3] == meta[12]
        assert meta[6] == meta[14]
        assert meta[3] != meta[6]  # le due coppie si dividono le metà
        assert meta[5] == meta[13]


def test_equilibrio_per_bando_e_dei_gemelli(fatti):
    for seme in range(20):
        meta, _, _ = mr.dividi(fatti, GEMELLI, seme=seme, fissi=FISSI)
        bando_di = {f["riga"]: f["id_bando"] for f in fatti}
        conta = Counter((bando_di[r], m) for r, m in meta.items())
        for b in ("alfa", "beta", "gamma"):
            assert abs(conta[(b, mr.TARATURA)] - conta[(b, mr.CONTROLLO)]) <= 1
        gemelli_gamma = Counter(meta[r] for r in (17, 18, 19, 20))
        assert gemelli_gamma[mr.TARATURA] == gemelli_gamma[mr.CONTROLLO] == 2
        tutti = Counter(meta[r] for r in GEMELLI)
        assert tutti[mr.TARATURA] == tutti[mr.CONTROLLO] == 4


def test_regole_impossibili_si_dicono(fatti, monkeypatch):
    monkeypatch.setattr(mr, "TENTATIVI_MASSIMI", 50)
    # tutto alfa in un gruppo: le metà di alfa non possono stare in equilibrio
    with pytest.raises(mr.ErroreDivisione):
        mr.dividi(fatti, GEMELLI, seme=1, fissi=((2, 3, 4, 5, 6, 7, 8),))


def test_righe_senza_frase_escluse(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "GRUPPI_FISSI", ())
    libro = openpyxl.Workbook()
    foglio = libro.active
    foglio.title = "fatti"
    foglio.append(INTESTAZIONE)
    foglio.append(("alfa", "", "", "semplice", "D?", "Una frase.", 1, "no", "", "", ""))
    foglio.append(("alfa", "", "", None, None, None, None, None, None, None, None))
    foglio.append(("beta", "", "", "caso", "D?", "Altra frase.", 2, "sì", "", "", ""))
    percorso = tmp_path / "fatti.xlsx"
    libro.save(percorso)
    controllo = tmp_path / "controllo.csv"
    controllo.write_text(
        "riga,id_bando,solo_calcolato,pezzi,pezzi_visti\n2,alfa,sì,1,1\n4,beta,no,1,0\n",
        encoding="utf-8",
    )
    uscita = tmp_path / "divisione.csv"

    assert mr.esegui_divisione(percorso, controllo, uscita) == 0

    righe = uscita.read_text(encoding="utf-8").splitlines()
    assert [r.split(",")[0] for r in righe[1:]] == ["2", "4"]
    firma = (tmp_path / "divisione.csv.sha256").read_text(encoding="utf-8").split()[0]
    assert firma == mr.impronta(uscita.read_bytes())


def test_divisione_esistente_non_si_sovrascrive(tmp_path, fatti, monkeypatch):
    monkeypatch.setattr(mr, "leggi_foglio", lambda _p: fatti)
    monkeypatch.setattr(mr, "leggi_controllo", lambda _p: controllo_di(fatti))
    monkeypatch.setattr(mr, "GRUPPI_FISSI", ())
    uscita = tmp_path / "divisione.csv"
    foglio = tmp_path / "f.xlsx"
    foglio.write_bytes(b"finto")
    assert mr.esegui_divisione(foglio, tmp_path / "c.csv", uscita) == 0
    assert mr.esegui_divisione(foglio, tmp_path / "c.csv", uscita) == 0
    uscita.write_text("alterato\n", encoding="utf-8")
    assert mr.esegui_divisione(foglio, tmp_path / "c.csv", uscita) == 1
    assert uscita.read_text(encoding="utf-8") == "alterato\n"


def controllo_di(fatti):
    return {
        f["riga"]: {"id_bando": f["id_bando"], "gemello": False, "visti": False}
        for f in fatti
    }


def test_bando_diverso_nel_controllo_ferma(fatti):
    controllo = controllo_di(fatti)
    controllo[3]["id_bando"] = "beta"
    with pytest.raises(mr.ErroreDivisione):
        mr.controlla_ingressi(fatti, controllo, ())


def test_righe_diverse_tra_foglio_e_controllo_fermano(fatti):
    controllo = controllo_di(fatti)
    del controllo[3]
    with pytest.raises(mr.ErroreDivisione):
        mr.controlla_ingressi(fatti, controllo, ())


# --- le quattro condizioni della regola 5 ---


def squilibrio(meta, righe):
    lati = Counter(meta[r] for r in righe)
    return abs(lati[mr.TARATURA] - lati[mr.CONTROLLO])


def rispettata_e_necessaria(fatti, nome, righe, massimo):
    """Con la condizione, nessun seme la viola; senza, almeno un seme sì."""
    con = {nome: massimo}
    for seme in range(20):
        meta, _, _ = mr.dividi(fatti, GEMELLI, seme=seme, fissi=FISSI, condizioni=con)
        assert squilibrio(meta, righe) <= massimo
    senza = [
        mr.dividi(fatti, GEMELLI, seme=s, fissi=FISSI, condizioni={})[0]
        for s in range(20)
    ]
    assert any(squilibrio(meta, righe) > massimo for meta in senza)


def test_condizione_righe_di_tabella(fatti):
    righe = {2, 4, 7, 9, 11, 15, 16, 21}
    for f in fatti:
        f["in_tabella"] = "sì" if f["riga"] in righe else "no"
    rispettata_e_necessaria(fatti, "righe di tabella", righe, 1)


def test_condizione_risposte_in_piu_pezzi(fatti):
    righe = {4, 7, 8, 10, 15, 16, 22, 23}
    for f in fatti:
        if f["riga"] in righe and f["riga"] != 4:
            f["frase"] = f"Pezzo uno della riga {f['riga']} [...] pezzo due"
    assert {f["riga"] for f in fatti if mr.numero_pezzi(f) > 1} == righe
    rispettata_e_necessaria(fatti, "risposte in più pezzi", righe, 1)


def test_condizione_registro_semplice_e_caso(fatti):
    caso = {2, 4, 5, 7, 9, 10, 11, 14, 16, 17, 21, 22}
    for f in fatti:
        f["registro"] = "caso" if f["riga"] in caso else "semplice"
    semplice = {f["riga"] for f in fatti} - caso
    rispettata_e_necessaria(fatti, "registro caso", caso, 3)
    rispettata_e_necessaria(fatti, "registro semplice", semplice, 3)


def test_condizione_parte_vista(fatti):
    righe = {2, 4, 5, 6, 8, 9, 11, 13, 16, 18, 21, 23}
    for f in fatti:
        f["visti"] = f["riga"] in righe
    rispettata_e_necessaria(fatti, "tutti i pezzi nella parte vista", righe, 2)


def test_condizione_impossibile_si_nomina(fatti, monkeypatch):
    monkeypatch.setattr(mr, "TENTATIVI_MASSIMI", 50)
    for f in fatti:
        f["in_tabella"] = "sì" if f["riga"] == 2 else "no"
    # una sola riga di tabella: la differenza tra le metà è sempre 1
    with pytest.raises(mr.ErroreDivisione, match="righe di tabella: violata in 50"):
        mr.dividi(
            fatti, GEMELLI, seme=1, fissi=FISSI, condizioni={"righe di tabella": 0}
        )
