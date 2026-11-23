"""Apertura della metà di controllo (regola del 23/11/2026, coda.md punto 13
voce 19): domande a mano del controllo, decisioni 1 e 2, rapporto e comando.

Tutto inventato: fatti, misure, frammenti. Nessun PDF, nessun Chroma, nessun
modello, nessuna misura vera.
"""

import json

import pytest

import scripts.diagnostica.misura_recupero_avvisi as mr
from scripts.diagnostica.controlla_fatti import Frammento

# --- domande a mano della metà ---


def fatti_finti():
    return [
        {
            "riga": riga,
            "foglio": 1,
            "id_bando": "alfa",
            "titolo": "Bando alfa",
            "frase": f"Frase {riga}",
            "domanda": f"Domanda del foglio {riga}",
        }
        for riga in range(2, 8)
    ]


def scrivi_a_mano(percorso, righe, xlsx=False):
    colonne = mr.COLONNE_MANO_CONTESTO
    righe = [{c: str(r.get(c, "")) for c in colonne} for r in righe]
    if xlsx:
        mr.scrivi_xlsx_a_mano(percorso, righe, colonne)
    else:
        mr.scrivi_csv_a_mano(percorso, righe, colonne)


def riga_a_mano(riga, domanda, spiegata=""):
    return {
        "riga": riga,
        "foglio": 1,
        "titolo": "Bando alfa",
        "frase": f"Frase {riga}",
        "domanda_a_mano": domanda,
        "spiegata": spiegata,
    }


def test_file_a_mano_del_lato():
    assert mr.file_a_mano_del_lato(mr.CONTROLLO) == (mr.DOMANDE_A_MANO_CONTROLLO,)
    assert mr.file_a_mano_del_lato(mr.TARATURA) == (
        mr.DOMANDE_A_MANO,
        mr.DOMANDE_A_MANO_2,
        mr.DOMANDE_A_MANO_3,
    )


def test_sul_controllo_si_legge_solo_il_file_del_controllo(tmp_path, monkeypatch):
    fatti = fatti_finti()
    lati = []

    def intera(lato):
        lati.append(lato)
        return None, fatti, {}

    monkeypatch.setattr(mr, "fatti_intera", intera)
    # i file di taratura ci sono ma non si devono leggere: colonne sbagliate
    for nome in ("DOMANDE_A_MANO", "DOMANDE_A_MANO_2", "DOMANDE_A_MANO_3"):
        p = tmp_path / f"{nome}.csv"
        p.write_text("colonna_sbagliata\n1\n", encoding="utf-8")
        monkeypatch.setattr(mr, nome, p)
    controllo = tmp_path / "domande_a_mano_controllo.csv"
    monkeypatch.setattr(mr, "DOMANDE_A_MANO_CONTROLLO", controllo)
    # il .csv come lo scrive --prepara-domande-a-mano-controllo, domande vuote
    scrivi_a_mano(controllo, [riga_a_mano(2, ""), riga_a_mano(3, "")])
    # la copia .xlsx, se c'è, è quella che si legge; la riga vuota si salta
    scrivi_a_mano(
        controllo.with_suffix(".xlsx"),
        [riga_a_mano(2, "mia 2", "sì"), riga_a_mano(3, ""), riga_a_mano(5, "mia 5")],
        xlsx=True,
    )
    con_mano, _ = mr.fatti_della_misura(mr.CONTROLLO, True)
    assert lati == [mr.CONTROLLO]
    assert [(f["riga"], f["domanda"]) for f in con_mano] == [
        (2, "mia 2"),
        (5, "mia 5"),
    ]
    senza, _ = mr.fatti_della_misura(mr.CONTROLLO, False)
    assert senza == fatti
    assert mr.spiegate_del_lato(mr.CONTROLLO) == {"2": True, "5": False}
    # sulla taratura si leggono i tre file di sempre (qui con colonne sbagliate)
    with pytest.raises(mr.ErroreMisura, match="servono le colonne"):
        mr.fatti_della_misura(mr.TARATURA, True)


# --- righe di misura finte ---


def riga(numero, bando, trovato, a_trovato=None, **altro):
    return {
        "riga": str(numero),
        "id_bando": bando,
        "B_trovato": "sì" if trovato else "no",
        "A_trovato": "sì" if (trovato if a_trovato is None else a_trovato) else "no",
        "A_pezzo_dal_gemello": "no",
        "A_gemello_senza_giusto": "no",
        "B_pezzo_dal_gemello": "no",
        "B_cause": "" if trovato else "frammento giusto oltre i primi 50",
        **altro,
    }


def serie(trovati_base, trovati_cand, bandi):
    """(base, candidata) con gli stessi fatti; trovati_* sono insiemi di righe."""
    righe = range(1, len(bandi) + 1)
    base = [riga(r, bandi[r - 1], r in trovati_base) for r in righe]
    cand = [riga(r, bandi[r - 1], r in trovati_cand) for r in righe]
    return base, cand


def per_k(base, cand, base15=None, cand15=None):
    return (
        {10: base, 15: base15 or base},
        {10: cand, 15: cand15 or cand},
    )


BANDI = ["a"] * 4 + ["b"] * 4 + ["c"] * 4


def fogli_che_passano():
    # sei presi, due per bando, nessun perso: p 0,031
    return serie({11, 12}, {1, 2, 5, 6, 9, 10, 11, 12}, BANDI)


def test_decisione_1_sostituisce_se_passano_tutti_e_quattro():
    bf, cf = per_k(*fogli_che_passano())
    bm, cm = per_k(*serie({1}, {1, 2}, BANDI))
    esito = mr.decisione_1(bf, cf, bm, cm)
    assert esito.punti == {"1": True, "2": True, "3": True, "4": True}
    assert esito.esito == "c-LR sostituisce c-0"


def test_decisione_1_mano_zero_e_zero_lascia_c0():
    bf, cf = per_k(*fogli_che_passano())
    bm, cm = per_k(*serie({1}, {1}, BANDI))
    esito = mr.decisione_1(bf, cf, bm, cm)
    assert not esito.punti["2"]
    assert esito.esito == "resta c-0"
    # il punto 2 non chiede un p: un preso e nessun perso basta
    bm, cm = per_k(*serie(set(), {3}, BANDI))
    assert mr.decisione_1(bf, cf, bm, cm).punti["2"]


def test_decisione_1_p_oltre_la_soglia_sui_fogli():
    # cinque presi e nessun perso: p 0,0625
    bf, cf = per_k(*serie(set(), {1, 2, 5, 6, 9}, BANDI))
    bm, cm = per_k(*serie(set(), {1}, BANDI))
    esito = mr.decisione_1(bf, cf, bm, cm)
    assert not esito.punti["1"]
    assert esito.esito == "resta c-0"


def test_decisione_1_k15_netto_negativo_con_le_regressioni():
    bf, cf = per_k(*fogli_che_passano())
    b10, c10 = serie(set(), {1}, BANDI)
    b15, c15 = serie({4, 8}, {1}, BANDI)
    bm, cm = per_k(b10, c10, b15, c15)
    esito = mr.decisione_1(bf, cf, bm, cm)
    assert not esito.punti["3"]
    assert any("regressioni (2): 4 a, 8 b" in linea for linea in esito.linee)


def test_decisione_1_netto_a_zero_togliendo_un_bando():
    bandi = ["a"] * 6 + ["b"] * 6
    bm, cm = per_k(*serie(set(), {1}, BANDI))
    # sei presi tutti nel bando a (p 0,031): senza a il netto è zero
    bf, cf = per_k(*serie(set(), {1, 2, 3, 4, 5, 6}, bandi))
    assert mr.netto_senza_ogni_bando(bf[10], cf[10]) == {"a": (0, 0), "b": (6, 0)}
    esito = mr.decisione_1(bf, cf, bm, cm)
    assert esito.punti["1"]
    assert not esito.punti["4"]
    assert esito.esito == "resta c-0"
    # cinque in a e uno in b: senza a resta +1, solo il netto conta
    bf, cf = per_k(*serie(set(), {1, 2, 3, 4, 5, 7}, bandi))
    assert mr.decisione_1(bf, cf, bm, cm).punti["4"]


def test_decisione_2_soglia_e_punti_sotto_la_taratura():
    def righe(trovati, n):
        return [riga(r, "a", r <= trovati) for r in range(1, n + 1)]

    assert mr.decisione_2("c-LR", righe(85, 100), (95, 100))[0]
    # 85% esatto passa; 11 punti sotto la taratura no
    assert not mr.decisione_2("c-LR", righe(85, 100), (96, 100))[0]
    assert not mr.decisione_2("c-LR", righe(84, 100), (84, 100))[0]
    ok, linee = mr.decisione_2("c-0", righe(73, 98), mr.TARATURA_APERTURA["c-0"])
    assert not ok
    assert linee[-1] == "  esito: " + mr.SOTTO_SOGLIA
    assert "73 su 98, 74,5%" in linee[0]


def test_allegato_identico_parola_per_parola():
    giusto = Frammento(3, 1, "Premessa. Il contributo è pari al 50%. Altro.", 99)
    uguale = Frammento(7, 1, "Altro testo. Il contributo è pari al 50%.", 99)
    spazi = Frammento(9, 1, "Il contributo è pari al 50 %. Fine.", 99)
    fatto = {"frase": "Il contributo è pari al 50%.", "in_tabella": "no"}
    frammenti = {"a1.pdf": [giusto], "a3.pdf": [uguale], "a4.pdf": [spazi]}
    esito = mr.allegato_identico(fatto, {"a1.pdf"}, {"a3.pdf"}, frammenti)
    assert esito == "pezzo 1: testo identico parola per parola in a3.pdf #7"
    esito = mr.allegato_identico(fatto, {"a1.pdf"}, {"a3.pdf", "a4.pdf"}, frammenti)
    assert esito == "pezzo 1: NON identico in a4.pdf #9"
    assert "nessun frammento" in mr.allegato_identico(
        fatto, {"a1.pdf"}, {"a5.pdf"}, frammenti
    )


# --- rapporto e comando dell'apertura, su misure finte ---


def misure_finte(fogli=(72, 83, 97), mano=(7, 8, 10)):
    """Le misure di c-0 e c-LR tutte, per serie: (trovati c-0, trovati c-LR, n)."""
    misure = {}
    for serie_, (tb, tc, n) in (("fogli", fogli), ("mano", mano)):
        bandi = [f"bando-{r % 4}" for r in range(1, n + 1)]
        base, cand = serie(set(range(1, tb + 1)), set(range(1, tc + 1)), bandi)
        misure[serie_] = {("c-0", mr.NESSUNA): base, ("c-LR", "tutte"): cand}
    return misure


def prepara_misure(lato, **conti):
    """Scrive le misure finte, k=10 e 15, con il .json, nella cartella del contesto."""
    misure = misure_finte(**conti)
    for serie_, mano_ in mr.SERIE_APERTURA:
        for chiave, righe in misure[serie_].items():
            scrivi_misura_finta(chiave, lato, mano_, righe)
    return misure


def scrivi_misura_finta(chiave, lato, mano, righe):
    (mr.CARTELLA_CONTESTO / "misure").mkdir(parents=True, exist_ok=True)
    for k in mr.K_ESATTI:
        mr.scrivi_misura(mr.file_contesto(*chiave, k, lato, mano), righe)
    dati = {
        "tempo_per_domanda_s": {"A": {"mediana": 1.0}, "B": {"mediana": 1.5}},
        "tempo_s": 12.0,
    }
    mr.file_contesto(*chiave, mr.K, lato, mano).with_suffix(".json").write_text(
        json.dumps(dati), encoding="utf-8"
    )


@pytest.fixture
def cartella(tmp_path, monkeypatch):
    monkeypatch.setattr(mr, "CARTELLA_CONTESTO", tmp_path)
    for nome in (
        "DOMANDE_A_MANO",
        "DOMANDE_A_MANO_2",
        "DOMANDE_A_MANO_3",
        "DOMANDE_A_MANO_CONTROLLO",
    ):
        monkeypatch.setattr(mr, nome, tmp_path / f"{nome}.csv")
    return tmp_path


def test_rapporto_apertura_sulla_taratura(cartella):
    prepara_misure(mr.TARATURA)
    assert mr.esegui_rapporto_apertura(mr.TARATURA, ("a" * 64, "a" * 64)) == 0
    testo = (cartella / "rapporto_apertura_taratura.txt").read_text(encoding="utf-8")
    assert "PROVA A SECCO" in testo
    assert "presi 11, persi 0, netto +11" in testo
    assert "esito: c-LR sostituisce c-0" in testo
    assert "c-LR, fogli, B, k=10: 83 su 97, 85,6%" in testo
    assert "esito: supera la soglia" in testo
    assert "Le due serie non si sommano mai." in testo
    assert "uguali" in testo
    # i mancati per la lettura a mano, in ordine di riga
    assert "[fogli] c-LR k=10: 14" in testo


def test_rapporto_apertura_si_ferma_se_la_taratura_non_e_quella_della_regola(
    cartella,
):
    prepara_misure(mr.TARATURA, fogli=(70, 83, 97))
    with pytest.raises(mr.ErroreMisura, match="taratura di c-0"):
        mr.esegui_rapporto_apertura(mr.TARATURA)


def test_rapporto_apertura_sul_controllo_dice_se_le_domande_non_sono_98(cartella):
    prepara_misure(mr.CONTROLLO, fogli=(70, 71, 97))
    mr.esegui_rapporto_apertura(mr.CONTROLLO)
    testo = (cartella / "rapporto_apertura_controllo.txt").read_text(encoding="utf-8")
    assert "PROVA A SECCO" not in testo
    assert "Domande dei fogli 97 (la regola parla di 98)" in testo
    assert "esito: resta c-0" in testo
    assert "c-0, fogli, B, k=10: 70 su 97" in testo


def test_apertura_sulla_taratura_riusa_le_misure_salvate(cartella, monkeypatch):
    prepara_misure(mr.TARATURA)
    chiamate = []

    def non_si_misura(*argomenti):
        raise AssertionError("la prova a secco non rifà le misure salvate")

    monkeypatch.setattr(mr, "esegui_contesto", non_si_misura)
    monkeypatch.setattr(
        mr, "fatti_della_misura", lambda lato, mano: chiamate.append((lato, mano))
    )
    assert mr.esegui_apertura(mr.TARATURA) == 0
    assert chiamate == [(mr.TARATURA, True)]
    assert (cartella / "rapporto_apertura_taratura.txt").exists()


def test_apertura_sul_controllo_una_volta_sola(cartella, monkeypatch):
    finte = misure_finte()
    ordine = []

    def misura_finta(lato, nome, righe, mano):
        ordine.append((lato, nome, righe, mano))
        serie_ = "mano" if mano else "fogli"
        scrivi_misura_finta((nome, righe), lato, mano, finte[serie_][(nome, righe)])
        return 0

    monkeypatch.setattr(mr, "esegui_contesto", misura_finta)
    monkeypatch.setattr(
        mr,
        "fatti_della_misura",
        lambda lato, mano: ordine.append(("controllo a mano",)),
    )
    (cartella / "misure").mkdir()
    assert mr.esegui_apertura(mr.CONTROLLO) == 0
    assert ordine == [
        ("controllo a mano",),
        (mr.CONTROLLO, "c-0", mr.NESSUNA, False),
        (mr.CONTROLLO, "c-LR", "tutte", False),
        (mr.CONTROLLO, "c-0", mr.NESSUNA, True),
        (mr.CONTROLLO, "c-LR", "tutte", True),
    ]
    testo = (cartella / "rapporto_apertura_controllo.txt").read_text(encoding="utf-8")
    assert "Impronta dello script" in testo
    # una seconda volta si ferma prima di misurare
    ordine.clear()
    with pytest.raises(mr.ErroreMisura, match="una volta sola"):
        mr.esegui_apertura(mr.CONTROLLO)
    assert ordine == []
