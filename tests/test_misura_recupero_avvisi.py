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


# --- tempo 3, secondo giro: intestazione, divisione, pezzi spezzati ---


def test_intestazione_solo_per_gli_avvisi_e_senza_voci_vuote():
    avviso = {
        "sha256": "a" * 64,
        "titolo": "Bando parcheggi 2026",
        "parte": "",
        "riferimento_atto": "Decreto n. 1 del 2026, Allegato A",
    }
    assert mr.intestazione_di(avviso) == (
        "Bando parcheggi 2026 · Decreto n. 1 del 2026, Allegato A"
    )
    assert mr.testo_per_vettore("Art. 1", avviso, True) == (
        "Bando parcheggi 2026 · Decreto n. 1 del 2026, Allegato A\nArt. 1"
    )
    assert mr.testo_per_vettore("Art. 1", avviso, False) == "Art. 1"
    di_sempre = {"titolo": "Studio Censis"}
    assert mr.testo_per_vettore("Testo", di_sempre, True) == "Testo"


def test_impronta_dei_frammenti_non_dipende_dall_ordine():
    ids, testi = ["x::0", "x::1"], ["uno", "due"]
    metadati = [{"page": 1, "vuoto": None}, {"page": 2}]
    a = mr.impronta_frammenti(ids, testi, metadati)
    b = mr.impronta_frammenti(ids[::-1], testi[::-1], metadati[::-1])
    assert a == b
    # le voci vuote non contano, come in Chroma
    assert a == mr.impronta_frammenti(ids, testi, [{"page": 1}, {"page": 2}])
    assert a != mr.impronta_frammenti(ids, ["uno", "tre"], metadati)


def test_dimensione_dei_frammenti_cambia_e_ripristina():
    import types

    chiamate = []

    def spezza(pagine, dimensione=1500, sovrapposizione=250, **altri):
        chiamate.append((dimensione, sovrapposizione))

    modulo = types.SimpleNamespace(spezza=spezza)
    with mr.dimensione_dei_frammenti(modulo, (600, 200)):
        modulo.spezza([], ricucitura="prudente")
    modulo.spezza([])
    with mr.dimensione_dei_frammenti(modulo, None):
        modulo.spezza([])
    assert chiamate == [(600, 200), (1500, 250), (1500, 250)]
    assert modulo.spezza is spezza


def test_stato_dei_pezzi_interi_spezzati_assenti():
    f = fatto(
        2,
        "alfa",
        "Il contributo è di 40.000 euro [...] La spesa minima è di 3.000 euro"
        " [...] Pezzo che non esiste",
    )
    per_fonte = {
        "giusto.pdf": [
            fr(0, "Art. 2. Il contributo è di 40.000 euro. La spesa minima"),
            fr(1, "spesa minima è di 3.000 euro per domanda."),
        ],
        "altro.pdf": [fr(0, "Pezzo che non esiste")],
    }
    assert mr.stato_dei_pezzi(f, GIUSTI, per_fonte) == (1, 1, 1)


class EmbeddingsFinti:
    """Vettori di tre numeri dalla lunghezza del testo; nessun modello."""

    def __init__(self):
        import types

        self._client = types.SimpleNamespace(
            max_seq_length=128, tokenizer=lambda t: {"input_ids": [0, 1, 2]}
        )

    def embed_documents(self, testi):
        return [[1.0, 0.0, 0.0] if len(t) % 2 else [0.0, 1.0, 0.0] for t in testi]


def test_copia_ridivisa_con_gli_stessi_id_dei_frammenti_tolti(tmp_path, monkeypatch):
    import chromadb
    from chromadb.config import Settings
    from langchain_core.documents import Document

    import src.vectorstore
    from src.config import COLLECTION_NAME

    sorgente = tmp_path / "chroma_vero"
    cliente = chromadb.PersistentClient(
        path=str(sorgente), settings=Settings(anonymized_telemetry=False)
    )
    collezione = cliente.create_collection(COLLECTION_NAME)
    sha = "a" * 64
    vecchi = [
        Document(
            page_content=f"Avviso, frammento {n}.",
            metadata={"sha256": sha, "chunk_num": n},
        )
        for n in range(2)
    ]
    collezione.add(
        ids=[f"{sha[:16]}::{n}" for n in range(2)] + ["sempre::0"],
        documents=[d.page_content for d in vecchi] + ["Documento di sempre."],
        metadatas=[d.metadata for d in vecchi]
        + [{"fonte": "censis.pdf", "chunk_num": 0}],
        embeddings=[[1.0, 0.0, 0.0]] * 3,
    )
    del cliente
    nuovi = [
        Document(page_content=f"Corto {n}.", metadata={"sha256": sha, "chunk_num": n})
        for n in range(3)
    ]
    monkeypatch.setattr(
        mr, "frammenti_avvisi", lambda frammenti: vecchi if frammenti is None else nuovi
    )
    monkeypatch.setattr(src.vectorstore, "crea_embeddings", EmbeddingsFinti)

    info = mr.prepara_copia(
        tmp_path / "v3", mr.Variante(frammenti=(600, 200)), sorgente
    )

    copia = chromadb.PersistentClient(
        path=str(tmp_path / "v3" / "chroma"),
        settings=Settings(anonymized_telemetry=False),
    ).get_collection(COLLECTION_NAME)
    dati = copia.get()
    assert sorted(dati["ids"]) == sorted(
        [f"{sha[:16]}::{n}" for n in range(3)] + ["sempre::0"]
    )
    assert "Corto 0." in dati["documents"]
    assert info["ricostruzione"] == (2, 2, True)


# --- terzo giro ---


def test_con_ampiezza_passa_l_ampiezza_alla_ricerca():
    chiamate = []

    class Base:
        def titoli(self):
            return {"a.pdf": "Titolo"}

        def cerca(self, domanda, k=8, ampiezza=20, fonte=None):
            chiamate.append((domanda, k, ampiezza, fonte))
            return []

    recupero = mr.ConAmpiezza(Base(), 50)
    recupero.cerca("domanda?", k=15, fonte="a.pdf")
    mr.Profondo(Base()).cerca("altra?", k=10)
    assert chiamate == [
        ("domanda?", 15, 50, "a.pdf"),
        ("altra?", 10, mr.PROFONDITA, None),
    ]
    assert recupero.titoli() == {"a.pdf": "Titolo"}


def test_testo_lessicale_con_il_prefisso_solo_per_i_file_dati():
    prefissi = {"a4.pdf": "Azione B4: Razionalizzazione della transumanza"}
    assert mr.testo_lessicale("Testo.", {"fonte": "a4.pdf"}, prefissi) == (
        "Azione B4: Razionalizzazione della transumanza\nTesto."
    )
    assert mr.testo_lessicale("Testo.", {"fonte": "a5.pdf"}, prefissi) == "Testo."
    assert mr.testo_lessicale("Testo.", {"fonte": "a4.pdf"}, None) == "Testo."


def test_distanza_dai_primi_e_fatto_completo_con_i_vicini():
    per_fonte = {
        "giusto.pdf": [
            fr(0, "apertura"),
            fr(1, "Il contributo è di 40.000 euro"),
            fr(2, "voce a"),
            fr(3, "voce b"),
        ],
        "altro.pdf": [fr(0, "x"), fr(1, "voce c")],
    }
    primi = [("giusto.pdf", per_fonte["giusto.pdf"][1]), ("altro.pdf", fr(0, "x"))]
    distanze = [
        mr.distanza_dai_primi([t], primi, GIUSTI, per_fonte)
        for t in ("Il contributo è di 40.000 euro", "voce a", "voce b", "voce c")
    ]
    # voce c sta accanto a un frammento tra i primi, ma di un documento non giusto
    assert distanze == [0, 1, 2, None]
    assert mr.completo_con_vicini([0, 1], 1)
    assert not mr.completo_con_vicini([0, 2], 1)
    assert mr.completo_con_vicini([0, 2], 2)
    assert not mr.completo_con_vicini([0, None], 2)


def test_parole_in_comune_senza_parole_funzionali_e_con_la_radice():
    domanda = "Qual è la durata massima del nostro progetto finanziato col'Azione B4?"
    pezzo = "I progetti hanno una durata di 12 mesi; azione B4."
    nella_domanda, comuni = mr.parole_in_comune(domanda, pezzo)
    assert nella_domanda == [
        "durata",
        "massima",
        "progetto",
        "finanziato",
        "azione",
        "b4",
    ]
    # "progetto" e "progetti" hanno le stesse prime 5 lettere
    assert comuni == ["durata", "progetto", "azione", "b4"]


def test_nome_dell_azione_dalla_riga_del_titolo():
    pagine = [
        (
            "Delibera n. 649\nIntervento B Azione B4: Razionalizzazione della "
            "transumanza\nDisposizioni"
        ),
        "Azione B4 - altro testo",
    ]
    assert mr.nome_dell_azione(pagine, "B4") == (
        1,
        "Intervento B Azione B4: Razionalizzazione della transumanza",
        "Azione B4: Razionalizzazione della transumanza",
    )
    assert mr.nome_dell_azione(pagine, "B5") is None


def test_copia_con_la_parte_cambia_solo_i_vettori_dei_file_dati(tmp_path, monkeypatch):
    import chromadb
    from chromadb.config import Settings

    import src.vectorstore
    from src.config import COLLECTION_NAME

    sorgente = tmp_path / "v0" / "chroma"
    cliente = chromadb.PersistentClient(
        path=str(sorgente), settings=Settings(anonymized_telemetry=False)
    )
    cliente.create_collection(COLLECTION_NAME).add(
        ids=["a4::0", "a4::1", "a5::0"],
        documents=["Testo uno.", "Testo due.", "Testo tre."],
        metadatas=[{"fonte": "a4.pdf"}, {"fonte": "a4.pdf"}, {"fonte": "a5.pdf"}],
        embeddings=[[0.0, 0.0, 1.0]] * 3,
    )
    del cliente
    prima = mr.impronte_cartella(sorgente)
    monkeypatch.setattr(src.vectorstore, "crea_embeddings", EmbeddingsFinti)

    info = mr.prepara_copia_parte(
        tmp_path / "v0+parte", sorgente, {"a4.pdf": "Azione B4: X"}, None
    )

    assert info == {"frammenti": 2, "per_fonte": {"a4.pdf": 2}, "totale": 3}
    assert mr.impronte_cartella(sorgente) == prima
    dati = (
        chromadb.PersistentClient(
            path=str(tmp_path / "v0+parte" / "chroma"),
            settings=Settings(anonymized_telemetry=False),
        )
        .get_collection(COLLECTION_NAME)
        .get(include=["documents", "embeddings"])
    )
    per_id = dict(zip(dati["ids"], dati["embeddings"], strict=True))
    assert list(per_id["a5::0"]) == [0.0, 0.0, 1.0]
    assert list(per_id["a4::0"]) != [0.0, 0.0, 1.0]
    assert sorted(dati["documents"]) == ["Testo due.", "Testo tre.", "Testo uno."]


def test_griglia_solo_sulle_basi_v0_e_v1(tmp_path):
    with pytest.raises(mr.ErroreMisura, match="base 'v2'"):
        mr.esegui_griglia(tmp_path / "f.xlsx", tmp_path / "d.csv", mr.TARATURA, "v2")


# --- quarto giro: ricerca esatta ---


class EmbeddingsDomanda:
    """embed_query restituisce un vettore fisso e ricorda il testo ricevuto."""

    def __init__(self, vettore):
        self.vettore = vettore
        self.ricevuti = []

    def embed_query(self, testo):
        self.ricevuti.append(testo)
        return self.vettore


def store_esatto(embeddings, prefisso=""):
    import math

    r = 1 / math.sqrt(2)
    return mr.StoreEsatto(
        ["c", "a", "b", "d"],
        ["tre", "uno", "due", "quattro"],
        [
            {"fonte": "x.pdf", "id_bando": "alfa"},
            {"fonte": "x.pdf", "id_bando": "alfa"},
            {"fonte": "y.pdf", "id_bando": "beta"},
            {"fonte": "y.pdf", "id_bando": "alfa"},
        ],
        [[1.0, 0.0], [r, r], [1.0, 0.0], [0.0, 1.0]],
        embeddings,
        prefisso,
    )


def test_store_esatto_ordina_per_prodotto_scalare_e_pari_merito_per_id():
    embeddings = EmbeddingsDomanda([1.0, 0.0])
    store = store_esatto(embeddings, "query: ")
    risultati = store.similarity_search("domanda?", k=4)
    # b e c hanno lo stesso punteggio: prima b, per id
    assert [d.page_content for d in risultati] == ["due", "tre", "uno", "quattro"]
    assert embeddings.ricevuti == ["query: domanda?"]
    assert store.get()["ids"] == ["c", "a", "b", "d"]


def test_store_esatto_con_il_filtro_e_k():
    store = store_esatto(EmbeddingsDomanda([1.0, 0.0]))
    per_bando = store.similarity_search("d?", k=2, filter={"id_bando": "alfa"})
    assert [d.page_content for d in per_bando] == ["tre", "uno"]
    per_fonte = store.similarity_search("d?", k=5, filter={"fonte": "y.pdf"})
    assert [d.page_content for d in per_fonte] == ["due", "quattro"]


def test_store_esatto_rifiuta_vettori_non_normalizzati():
    with pytest.raises(mr.ErroreMisura, match="non normalizzati"):
        mr.StoreEsatto(["a"], ["t"], [{}], [[2.0, 0.0]], EmbeddingsDomanda([1.0, 0.0]))


def test_vettori_salvati_e_riletti_uguali(tmp_path):
    ids, testi, metadati = ["a", "b"], ["uno", "due"], [{"fonte": "x"}, {}]
    firma = mr.salva_vettori(tmp_path, ids, testi, metadati, [[1.0, 0.0], [0.0, 1.0]])
    letti = mr.leggi_vettori(tmp_path)
    assert letti[:3] == (ids, testi, metadati)
    assert letti[3].tolist() == [[1.0, 0.0], [0.0, 1.0]]
    assert firma == mr.impronta_frammenti(ids, testi, metadati)


def test_prefissi_dei_modelli_e5():
    for nome in ("e5-small", "e5-base"):
        assert mr.MODELLI[nome].domanda == "query: "
        assert mr.MODELLI[nome].passaggio == "passage: "
        assert mr.MODELLI[nome].limite == 512
    assert mr.MODELLI["v0"] == mr.Modello(mr.MODELLI["v0"].nome)
    assert mr.testi_con_prefisso(["a", "b"], "passage: ") == [
        "passage: a",
        "passage: b",
    ]


def test_esiti_diversi_tra_due_misure():
    prima = {"2": True, "10": False, "3": True}
    dopo = {"2": True, "10": True, "3": False}
    assert mr.esiti_diversi(prima, dopo) == ["3", "10"]
    with pytest.raises(mr.ErroreMisura):
        mr.esiti_diversi(prima, {"2": True})


def test_memoria_del_processo_positiva():
    assert mr.memoria_del_processo() > 0


# --- secondo foglio: divisione con vincoli ---


def test_proposta_senza_vincoli_come_prima():
    import random

    per_bando = {"alfa": [2, 3, 4, 5, 6], "beta": [7, 8, 9]}
    assert mr.proposta(random.Random(7), per_bando) == mr.proposta(
        random.Random(7), per_bando, {}
    )


def test_divisione_rispetta_i_vincoli(fatti):
    vincoli = {2: mr.CONTROLLO, 16: mr.TARATURA, 17: mr.TARATURA}
    meta, _, _ = mr.dividi(fatti, GEMELLI, fissi=FISSI, vincoli=vincoli)
    assert all(meta[r] == m for r, m in vincoli.items())
    per_bando = Counter((f["id_bando"], meta[f["riga"]]) for f in fatti)
    for b in ("alfa", "beta", "gamma"):
        assert abs(per_bando[(b, mr.TARATURA)] - per_bando[(b, mr.CONTROLLO)]) <= 1


def test_vincoli_impossibili_si_dicono(fatti):
    # quattro righe di gamma (8 fatti) in taratura e due gemelli già
    # obbligati: le regole non si possono rispettare
    vincoli = {r: mr.TARATURA for r in (16, 17, 18, 19, 20)}
    with pytest.raises(mr.ErroreDivisione, match="nessuna divisione valida"):
        mr.dividi(fatti, GEMELLI, fissi=FISSI, vincoli=vincoli)


def test_vincoli_dal_primo_foglio():
    primo = [
        {
            "riga": 5,
            "frase": "Il contributo massimo è di 9.000,00 euro per beneficiario.",
        },
        {"riga": 6, "frase": "Testo diverso del primo foglio, senza relazione."},
        {
            "riga": 7,
            "frase": "Il contributo massimo è di 9.000,00 euro per beneficiario.",
        },
    ]
    nuovi = [
        {
            "riga": 2,
            "frase": "Il contributo massimo è di 4.500,00 euro per beneficiario.",
        },
        {"riga": 3, "frase": "Una frase che nel primo foglio non c'è affatto."},
    ]
    vincoli, descrizioni = mr.vincoli_dal_primo(
        nuovi, primo, {5: mr.TARATURA, 6: mr.CONTROLLO, 7: mr.TARATURA}
    )
    assert vincoli == {2: mr.TARATURA}
    assert descrizioni[2].startswith("riga 5: simile")
    with pytest.raises(mr.ErroreDivisione, match="metà diverse"):
        mr.vincoli_dal_primo(nuovi, primo, {5: mr.TARATURA, 7: mr.CONTROLLO})


def test_coppie_quasi_nello_stesso_foglio():
    elenco = [
        {
            "riga": 2,
            "frase": "Spese ammissibili per la sede [...] arredi e attrezzature",
        },
        {"riga": 3, "frase": "Altra frase del bando con un testo diverso"},
        {"riga": 4, "frase": "Spese ammissibili per la sede [...] lavori edili"},
    ]
    assert mr.coppie_quasi(elenco) == ((2, 4),)


def test_metà_del_primo_solo_le_righe_chieste_e_impronta(tmp_path):
    percorso = tmp_path / "divisione.csv"
    dati = b"riga,meta\n2,taratura\n3,controllo\n4,taratura\n"
    percorso.write_bytes(dati)
    (tmp_path / "divisione.csv.sha256").write_text(
        f"{mr.impronta(dati)}  divisione.csv\n", encoding="utf-8"
    )
    assert mr.metà_del_primo(percorso, {3}) == {3: mr.CONTROLLO}
    percorso.write_bytes(dati + b"5,controllo\n")
    with pytest.raises(mr.ErroreDivisione, match="impronta"):
        mr.metà_del_primo(percorso, {3})


# --- taratura intera: i due fogli insieme ---


def test_unisci_fogli_sposta_le_righe_del_secondo_e_ferma_sulle_doppie():
    primo = [fatto(18, "alfa", "Frase del primo.")]
    secondo = [fatto(18, "alfa", "Frase del secondo."), fatto(5, "beta", "Altra.")]
    uniti = mr.unisci_fogli([(primo, 0), (secondo, mr.SCOSTAMENTO_2)])
    assert [(f["riga"], f["foglio"]) for f in uniti] == [(18, 1), (1018, 2), (1005, 2)]
    assert primo[0]["riga"] == 18 and secondo[0]["riga"] == 18  # ingressi intatti
    with pytest.raises(mr.ErroreMisura, match="righe uguali"):
        mr.unisci_fogli([(primo, 0), (secondo, 0)])


def test_nome_e_foglio_della_riga():
    assert mr.nome_della_riga("18") == "18"
    assert mr.nome_della_riga(1018) == "2:18"
    assert mr.foglio_della_riga("74") == 1
    assert mr.foglio_della_riga("1074") == 2


def test_causa_del_fatto_la_prima_che_si_applica():
    profonda = f"(ampiezza {mr.PROFONDITA})"
    assert (
        mr.causa_del_fatto(f"frammento giusto in posizione 12 {profonda}")
        == mr.CAUSA_OLTRE_15
    )
    # risposta in più pezzi: conta il pezzo messo peggio
    assert (
        mr.causa_del_fatto(
            f"pezzo 1: frammento giusto in posizione 12 {profonda} / "
            f"pezzo 2: frammento giusto in posizione 31 {profonda}"
        )
        == mr.CAUSA_OLTRE_50
    )
    assert (
        mr.causa_del_fatto(f"frammento giusto in posizione 16 {profonda}")
        == mr.CAUSA_OLTRE_30
    )
    assert (
        mr.causa_del_fatto(f"frammento giusto oltre i primi {mr.PROFONDITA}")
        == mr.CAUSA_OLTRE
    )
    assert (
        mr.causa_del_fatto(f"frammento giusto in posizione 14 {profonda}; {mr.GEMELLO}")
        == mr.CAUSA_GEMELLO
    )
    assert (
        mr.causa_del_fatto(
            f"{mr.FUORI_VISTA}; frammento giusto in posizione 20 {profonda}; "
            f"{mr.GEMELLO}"
        )
        == mr.CAUSA_FUORI_VISTA
    )
    assert mr.causa_del_fatto(mr.SPEZZATO) == mr.CAUSA_SPEZZATO
    assert mr.causa_del_fatto(mr.ASSENTE_FRAMMENTI) == mr.CAUSA_ASSENTE
    with pytest.raises(mr.ErroreMisura, match="non riconosciuta"):
        mr.causa_del_fatto("altro")


def test_differenza_entro_il_rumore():
    assert mr.differenza(26, 29) == "+3 (entro il rumore)"
    assert mr.differenza(26, 26) == "0 (entro il rumore)"
    assert mr.differenza(30, 26) == "-4"
    assert mr.differenza(26, 32) == "+6"


def riga_finta(riga, id_bando, trovato_b, **altro):
    """Una riga di misura come la scrive scrivi_misura, con valori di comodo."""
    r = dict.fromkeys(mr.COLONNE_MISURA, "")
    r.update(
        riga=str(riga),
        id_bando=id_bando,
        registro="semplice",
        in_tabella="no",
        pezzi="1",
        gemello="no",
    )
    for c in mr.CONDIZIONI_MISURA:
        r.update(
            {
                f"{c}_trovato": "no",
                f"{c}_gemello_senza_giusto": "no",
                f"{c}_pezzo_dal_gemello": "no",
            }
        )
    r["B_trovato"] = "sì" if trovato_b else "no"
    r.update(altro)
    return r


def test_rapporto_intero_per_bando_gemelli_e_cause():
    profonda = f"(ampiezza {mr.PROFONDITA})"
    v0 = [
        riga_finta(2, "alfa", True, B_primo_giusto="1", A_trovato="sì"),
        riga_finta(
            3,
            "alfa",
            False,
            B_cause=f"frammento giusto in posizione 12 {profonda}",
            gemello="sì",
            B_pezzo_dal_gemello="sì",
        ),
        riga_finta(1002, "beta", False, B_cause=mr.SPEZZATO, pezzi="2"),
        riga_finta(
            1003,
            "beta",
            False,
            B_cause=f"{mr.FUORI_VISTA}; frammento giusto in posizione 20 {profonda}",
        ),
    ]
    e5 = [
        riga_finta(2, "alfa", True, B_primo_giusto="4"),
        riga_finta(3, "alfa", True, B_primo_giusto="2", gemello="sì"),
        riga_finta(1002, "beta", True, B_primo_giusto="9", pezzi="2"),
        riga_finta(1003, "beta", False),
    ]
    linee = mr.rapporto_intero({("v0", 10): v0, ("e5-small", 10): e5}, "taratura")
    testo = "\n".join(linee)
    tutti = next(x for x in linee if x.startswith("tutti"))
    assert tutti.split()[1:] == ["4", "1", "/", "1", "0", "/", "3"]
    secondo = next(x for x in linee if x.startswith("secondo foglio"))
    assert secondo.split()[2:] == ["2", "0", "/", "0", "0", "/", "1"]
    assert "v0 k=10        B: frasi gemelle 1 (3)" in testo
    assert (
        "e5-small k=10 B: 3 contro 1, +2 (entro il rumore); ora trovati 3, 2:2" in testo
    )
    alfa = next(x for x in linee if x.startswith("alfa"))
    assert alfa.split() == ["alfa", "2", "1", "/", "1", "0", "/", "2"]
    assert "Non trovati in v0, condizione B, k=10: 3" in testo
    assert f"  {mr.CAUSA_FUORI_VISTA}: 1 ({mr.CAUSA_OLTRE_30} 1)" in linee
    i = linee.index(f"  {mr.CAUSA_SPEZZATO}: 1 ({mr.SENZA_POSIZIONE} 1)")
    assert linee[i + 1].startswith("    2:2 (beta, semplice, pezzi 2")
    assert f"  {mr.CAUSA_OLTRE_15}: 1" in linee


def test_righe_diverse_dal_primo_foglio():
    vecchie = [riga_finta(2, "alfa", True), riga_finta(3, "alfa", False)]
    nuove = [
        riga_finta(2, "alfa", True),
        riga_finta(3, "alfa", True),
        riga_finta(1002, "beta", False),
    ]
    assert mr.righe_diverse_dal_primo(vecchie, nuove) == ["3"]
    with pytest.raises(mr.ErroreMisura, match="non sono le stesse"):
        mr.righe_diverse_dal_primo(vecchie, nuove[:1])


def test_opzioni_della_taratura_intera():
    argomenti = mr.leggi_argomenti(["--esatta-intera", "--modello", "e5-base"])
    assert argomenti.esatta_intera and argomenti.modello == "e5-base"
    assert argomenti.controllo is False
    assert mr.leggi_argomenti(["--riepilogo-intero"]).riepilogo_intero
    assert mr.main(["--esatta-intera", "--riepilogo-intero"]) == 2
