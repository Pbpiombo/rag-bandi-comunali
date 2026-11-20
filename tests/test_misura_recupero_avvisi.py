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


# --- tempo 2: metà letta, impronta, rete ---


def scrivi_divisione(cartella, righe):
    percorso = cartella / "divisione.csv"
    testo = "riga,id_bando,meta,gruppo,registro,in_tabella,pezzi,gemello,visti\n"
    testo += "".join(f"{r},{b},{m},{r},semplice,no,1,no,no\n" for r, b, m in righe)
    percorso.write_text(testo, encoding="utf-8")
    firma = mr.impronta(percorso.read_bytes())
    (cartella / "divisione.csv.sha256").write_text(f"{firma}  divisione.csv\n")
    return percorso


def test_si_legge_solo_la_meta_chiesta(tmp_path):
    percorso = scrivi_divisione(
        tmp_path, [(2, "alfa", mr.TARATURA), (3, "alfa", mr.CONTROLLO)]
    )
    righe = mr.righe_della_meta(percorso, mr.TARATURA)
    assert set(righe) == {2}
    foglio = [
        fatto(2, "alfa", "Frase di taratura."),
        fatto(3, "alfa", "Frase di controllo."),
    ]
    fatti = mr.fatti_della_meta(foglio, righe)
    assert [f["riga"] for f in fatti] == [2]
    assert all("controllo" not in f["frase"] for f in fatti)


def test_senza_opzione_si_misura_la_taratura():
    assert mr.leggi_argomenti(["--misura"]).controllo is False
    assert mr.leggi_argomenti(["--misura", "--controllo"]).controllo is True


def test_impronta_alterata_ferma(tmp_path):
    percorso = scrivi_divisione(tmp_path, [(2, "alfa", mr.TARATURA)])
    assert mr.verifica_impronta(percorso) == mr.impronta(percorso.read_bytes())
    percorso.write_text(percorso.read_text() + "4,alfa,taratura,4,caso,no,1,no,no\n")
    with pytest.raises(mr.ErroreMisura, match="sha256"):
        mr.verifica_impronta(percorso)


def test_bando_diverso_dalla_divisione_ferma(tmp_path):
    percorso = scrivi_divisione(tmp_path, [(2, "beta", mr.TARATURA)])
    righe = mr.righe_della_meta(percorso, mr.TARATURA)
    with pytest.raises(mr.ErroreMisura):
        mr.fatti_della_meta([fatto(2, "alfa", "Frase.")], righe)


def test_connessioni_vietate_e_poi_ripristinate():
    import socket

    originale = socket.create_connection
    with mr.senza_connessioni(), pytest.raises(mr.ErroreMisura, match="rete"):
        socket.create_connection(("example.invalid", 80))
    assert socket.create_connection is originale


# --- tempo 2: criterio di "trovato" ---


def fr(numero, testo, car_visti=None):
    return mr.Frammento(
        numero, 1, testo, len(testo) if car_visti is None else car_visti
    )


GIUSTI = {"giusto.pdf"}
GEMELLI_DOC = {"gemello.pdf"}


def valuta(fatto_, primi, profondi=(), per_fonte=None):
    return mr.valuta(
        fatto_, list(primi), list(profondi), GIUSTI, GEMELLI_DOC, per_fonte or {}
    )


def test_trovato_se_ogni_pezzo_sta_in_un_frammento_giusto():
    f = fatto(2, "alfa", "Il contributo è di 40.000 euro [...] entro il 30 giugno")
    primi = [
        ("altro.pdf", fr(0, "Il contributo è di 40.000 euro entro il 30 giugno")),
        ("giusto.pdf", fr(4, "Art. 5: Il contri buto è di 40.000\neuro per Comune")),
        ("giusto.pdf", fr(9, "domande entro il 30  giugno 2026")),
    ]
    esito = valuta(f, primi)
    assert esito["trovato"] is True
    assert esito["posizioni_pezzi"] == [2, 3]
    assert esito["primo_giusto"] == 2
    assert esito["cause"] == []


def test_un_pezzo_mancante_basta_per_non_trovare():
    f = fatto(2, "alfa", "Il contributo è di 40.000 euro [...] entro il 30 giugno")
    primi = [("giusto.pdf", fr(4, "Il contributo è di 40.000 euro per Comune"))]
    esito = valuta(f, primi)
    assert esito["trovato"] is False
    assert esito["posizioni_pezzi"] == [1, None]
    assert esito["primo_giusto"] == 1


def test_frammento_di_un_altro_bando_non_vale():
    f = fatto(2, "alfa", "Il contributo è di 40.000 euro")
    esito = valuta(f, [("altro.pdf", fr(0, "Il contributo è di 40.000 euro"))])
    assert esito["trovato"] is False
    assert esito["primo_giusto"] is None


def test_tabella_tutte_le_celle_nello_stesso_frammento():
    f = fatto(2, "alfa", "Azione A1 | 20%", in_tabella="sì")
    insieme = [("giusto.pdf", fr(3, "Tabella 1\nAzione A1\n20%\nAzione A2\n30%"))]
    assert valuta(f, insieme)["trovato"] is True
    separate = [
        ("giusto.pdf", fr(3, "Tabella 1\nAzione A1")),
        ("giusto.pdf", fr(4, "20%\nAzione A2\n30%")),
    ]
    assert valuta(f, separate)["trovato"] is False


def test_documenti_del_fatto_apistici_e_bandi_gemelli(monkeypatch):
    monkeypatch.setattr(
        mr, "GEMELLI_DEI_BANDI", {"cultura": "sport", "sport": "cultura"}
    )
    registro = {
        "api": [
            {"nome_file": "a1.pdf", "parte": "Azione B1"},
            {"nome_file": "a3.pdf", "parte": "Azione B3"},
        ],
        "cultura": [
            {"nome_file": "cultura.pdf", "parte": ""},
            {"nome_file": "cultura-proroga.pdf", "parte": ""},
        ],
        "sport": [{"nome_file": "sport.pdf", "parte": ""}],
    }
    apistico = {"riga": 9, "id_bando": "api", "note": "Azione B3 (Allegato A3). Par. 2"}
    assert mr.documenti_del_fatto(apistico, registro) == ({"a3.pdf"}, {"a1.pdf"})
    cultura = {"riga": 10, "id_bando": "cultura", "note": ""}
    assert mr.documenti_del_fatto(cultura, registro) == (
        {"cultura.pdf", "cultura-proroga.pdf"},
        {"sport.pdf"},
    )


# --- tempo 2: cause dei mancati ---


def test_causa_gemello_al_posto_del_giusto():
    f = fatto(2, "alfa", "Le spese generali non sono ammesse.")
    testo = "Art. 4 Le spese generali non sono ammesse."
    primi = [("gemello.pdf", fr(1, testo))]
    per_fonte = {"giusto.pdf": [fr(7, testo)]}
    esito = valuta(
        f, primi, profondi=[*primi, ("giusto.pdf", fr(7, testo))], per_fonte=per_fonte
    )
    assert esito["trovato"] is False
    assert esito["pezzo_dal_gemello"] is True
    assert esito["gemello_senza_giusto"] is True
    assert mr.GEMELLO in esito["cause"][0]
    assert "posizione 2" in esito["cause"][0]


def test_causa_fuori_vista_e_posizione_oltre_i_primi():
    f = fatto(2, "alfa", "La spesa minima ammissibile è di 3.000 euro")
    testo = "Premessa lunga. " * 10 + "La spesa minima ammissibile è di 3.000 euro."
    giusto = fr(5, testo, car_visti=40)
    primi = [("giusto.pdf", fr(i, f"Altro testo {i}")) for i in range(10)]
    profondi = [*primi, *[("altro.pdf", fr(20 + i, "x")) for i in range(6)]]
    profondi.append(("giusto.pdf", giusto))
    esito = valuta(f, primi, profondi, per_fonte={"giusto.pdf": [giusto]})
    assert esito["trovato"] is False
    cause = esito["cause"][0]
    assert mr.FUORI_VISTA in cause
    assert "posizione 17" in cause
    assert mr.GEMELLO not in cause


def test_causa_oltre_la_profondita():
    f = fatto(2, "alfa", "La spesa minima ammissibile è di 3.000 euro")
    giusto = fr(5, "La spesa minima ammissibile è di 3.000 euro.")
    esito = valuta(f, [], [], per_fonte={"giusto.pdf": [giusto]})
    assert f"oltre i primi {mr.PROFONDITA}" in esito["cause"][0]
    assert mr.FUORI_VISTA not in esito["cause"][0]


def test_causa_pezzo_spezzato_tra_frammenti():
    f = fatto(2, "alfa", "La spesa minima ammissibile è di 3.000 euro")
    per_fonte = {
        "giusto.pdf": [
            fr(0, "Art. 3. La spesa minima ammissibile"),
            fr(1, "ammissibile è di 3.000 euro per domanda."),
        ]
    }
    esito = valuta(f, [], [], per_fonte=per_fonte)
    assert esito["cause"] == [mr.SPEZZATO]


def test_cause_per_pezzo_in_una_risposta_in_piu_pezzi():
    f = fatto(2, "alfa", "Il contributo è di 40.000 euro [...] entro il 30 giugno")
    per_fonte = {"giusto.pdf": [fr(0, "Il contributo è di 40.000 euro.")]}
    primi = [("giusto.pdf", fr(0, "Il contributo è di 40.000 euro."))]
    esito = valuta(f, primi, primi, per_fonte=per_fonte)
    assert esito["cause"] == [f"pezzo 2: {mr.ASSENTE_FRAMMENTI}"]


def test_posizioni_profonde_per_pezzo():
    f = fatto(2, "alfa", "Il contributo è di 40.000 euro [...] entro il 30 giugno")
    primi = [("giusto.pdf", fr(0, "Il contributo è di 40.000 euro."))]
    profondi = [
        *primi,
        ("altro.pdf", fr(1, "x")),
        ("giusto.pdf", fr(5, "entro il 30 giugno")),
    ]
    esito = valuta(f, primi, profondi)
    assert esito["posizioni_pezzi"] == [1, None]
    assert esito["posizioni_profonde"] == [1, 3]


# --- tempo 3: restrizioni, domanda ripulita, parte vista, confronto ---


def test_classe_della_restrizione():
    giusti, gemelli = {"a.pdf", "a-proroga.pdf"}, {"b.pdf"}
    assert mr.classe_restrizione(set(), giusti, gemelli) == ""
    assert mr.classe_restrizione({"a.pdf"}, giusti, gemelli) == mr.RISTRETTA_GIUSTO
    assert (
        mr.classe_restrizione({"a.pdf", "b.pdf"}, giusti, gemelli)
        == mr.RISTRETTA_GEMELLO
    )
    assert (
        mr.classe_restrizione({"a.pdf", "c.pdf"}, giusti, gemelli) == mr.RISTRETTA_ALTRO
    )
    assert mr.classe_restrizione({"b.pdf"}, giusti, gemelli) == mr.RISTRETTA_SBAGLIATO


def test_domanda_ripulita_come_l_app():
    titolo = "Bando parcheggi 2026"
    # il tratto che nomina il bando si toglie; la virgola orfana resta, come nell'app
    assert (
        mr.domanda_ripulita("Col bando parcheggi, chi paga gli interessi?", titolo)
        == "Col , chi paga gli interessi?"
    )
    # senza un tratto che nomina il bando la domanda resta intera
    domanda = "Quali parcheggi si possono finanziare?"
    assert mr.domanda_ripulita(domanda, titolo) == domanda


class TokenizerFinto:
    """Un token per parola, più [CLS] e [SEP]; offset sul testo vero."""

    def __call__(self, testo, return_offsets_mapping=False):
        import re

        parole = [(m.start(), m.end()) for m in re.finditer(r"\S+", testo)]
        return {
            "input_ids": [0] * (len(parole) + 2),
            "offset_mapping": [(0, 0), *parole, (0, 0)],
        }


def test_car_visti_con_il_limite():
    testo = "uno due tre quattro cinque"
    assert mr.car_visti(TokenizerFinto(), testo, 10) == len(testo)
    # limite 4: [CLS], due parole, [SEP]
    assert mr.car_visti(TokenizerFinto(), testo, 4) == len("uno due")


def test_cambi_di_esito_tra_varianti():
    base = [
        {"riga": "2", "A_trovato": "sì"},
        {"riga": "3", "A_trovato": "no"},
        {"riga": "10", "A_trovato": "no"},
    ]
    variante = [
        {"riga": "2", "A_trovato": "no"},
        {"riga": "3", "A_trovato": "sì"},
        {"riga": "10", "A_trovato": "sì"},
    ]
    assert mr.cambi_di_esito(base, variante, "A") == (["3", "10"], ["2"])
    with pytest.raises(mr.ErroreMisura):
        mr.cambi_di_esito(base, variante[:2], "A")


def test_copia_senza_limite_non_tocca_la_sorgente(tmp_path):
    sorgente = tmp_path / "chroma_vero"
    sorgente.mkdir()
    (sorgente / "chroma.sqlite3").write_bytes(b"dati")
    prima = mr.impronte_cartella(sorgente)
    assert mr.prepara_copia(tmp_path / "v0", None, sorgente) == {}
    assert mr.impronte_cartella(tmp_path / "v0" / "chroma") == prima
    assert mr.impronte_cartella(sorgente) == prima
