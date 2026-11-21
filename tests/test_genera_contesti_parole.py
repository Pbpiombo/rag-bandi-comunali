"""Riga PAROLE, segni automatici dei gemelli e regola delle domande a mano.

Decisioni del 21/11/2026 sul contesto per frammento. Tutto inventato;
nessuna chiamata al modello di linguaggio.
"""

from types import SimpleNamespace

import scripts.diagnostica.genera_contesti as gc
import scripts.diagnostica.misura_recupero_avvisi as mr

CONTESTO = (
    "DOVE: articolo 3\n"
    "ARGOMENTO: importi e massimali\n"
    "SERVE A: sapere quanto può ricevere al massimo un comune piccolo per "
    "sistemare le strade del territorio, e da quali regole dipende la quota "
    "che resta a carico dell'ente richiedente.\n"
    "PAROLE: contributo massimo; soldi per le strade; quanto spetta; "
    "piccoli comuni; manutenzione strade"
)


def documento(fonte="prova.pdf", id_bando="prova", testo=None, parte=""):
    corpo = "Articolo 3. Il contributo massimo è di 50.000 euro per ogni comune."
    testo = testo if testo is not None else corpo + " Testo generico. Fine."
    return gc.Documento(
        fonte=fonte,
        id_bando=id_bando,
        titolo="Bando prova strade",
        atto="Decreto n. 123 del 01/02/2026",
        parte=parte,
        testo=testo,
        frammenti=[gc.FrammentoDaContestualizzare(f"{fonte}::0", 0, corpo)],
    )


def salvato(testo, d=None):
    d = d or documento()
    risposta = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=testo)],
        usage=SimpleNamespace(
            input_tokens=1,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
            output_tokens=1,
        ),
        stop_reason="end_turn",
    )
    return gc.riga_salvata(d, d.frammenti[0], risposta)


def violazioni(testo, d=None, segni=None):
    d = d or documento()
    return gc.controlla_contesto(
        salvato(testo, d), d.frammenti[0].testo, d, segni or gc.SegniDelGemello()
    )


# --- riga PAROLE ---


def test_prompt_con_la_riga_parole():
    assert "PAROLE: da 5 a 10 parole o brevi espressioni" in gc.ISTRUZIONI
    assert "quattro righe" in gc.ISTRUZIONI
    assert "In ARGOMENTO, in SERVE A e in PAROLE" in gc.ISTRUZIONI


def test_parole_lette_e_nella_ricerca():
    righe = salvato(CONTESTO)["righe"]
    assert righe["parole"].startswith("contributo massimo; soldi")
    assert "soldi per le strade" in gc.testo_di_ricerca(righe)
    senza = gc.testo_di_ricerca(righe, mr.RIGHE_CONTESTO["senza-parole"])
    assert "soldi per le strade" not in senza and "quanto può ricevere" in senza
    assert set(mr.RIGHE_CONTESTO) == {
        "tutte",
        "senza-argomento",
        "senza-serve-a",
        "senza-parole",
    }
    assert "v1+contesto-senza-parole" in mr.MODELLI


def test_parole_con_gli_stessi_controlli():
    assert violazioni(CONTESTO) == []
    numero = CONTESTO.replace("quanto spetta", "fino a 5.000 abitanti")
    assert ("numero", "numero non nel frammento: 5.000") in violazioni(numero)
    mese = CONTESTO.replace("quanto spetta", "domanda entro marzo")
    assert ("numero", "parola non nel frammento: marzo") in violazioni(mese)
    gemello = CONTESTO.replace("quanto spetta", "azione B3")
    segni = gc.SegniDelGemello(codici={"B3"})
    assert ("gemello", "codice B3") in violazioni(gemello, segni=segni)


def test_parole_fuori_misura_non_sono_violazione():
    poche = CONTESTO.replace(
        "contributo massimo; soldi per le strade; quanto spetta; "
        "piccoli comuni; manutenzione strade",
        "strade",
    )
    d = documento()
    assert violazioni(poche, d) == []
    _, linee = gc.controlla_tutti([d], {d.frammenti[0].id: salvato(poche, d)})
    assert any(
        x.startswith("PAROLE fuori da 5-10 voci") and x.endswith(": 1") for x in linee
    )


def test_solo_indice_vale_senza_serve_a():
    assert violazioni("DOVE: non indicato\nARGOMENTO: indice o intestazione") == []
    altra_voce = "DOVE: non indicato\nARGOMENTO: definizioni"
    assert ("forma", "manca ARGOMENTO o SERVE A") in violazioni(altra_voce)


# --- segni automatici ---


def test_segni_automatici_frequenti_e_assenti():
    proprio = documento(testo="Il bando finanzia la cultura e i musei del comune.")
    gemello = documento(
        fonte="g.pdf",
        id_bando="altro",
        testo=(
            "palestra palestra palestra impianto impianto impianto atleti atleti "
            "atleti spogliatoi spogliatoi spogliatoi campo campo"
        ),
    )
    scelti = gc.segni_automatici(proprio, gemello)
    assert scelti == ["atleti", "impianto", "palestra"]
    assert "campo" not in scelti  # due volte sole


def test_segno_automatico_sotto_la_frequenza_minima():
    proprio = documento(testo="Il bando finanzia la cultura.")
    gemello = documento(fonte="g.pdf", id_bando="altro", testo="campo campo atleti")
    assert gc.segni_automatici(proprio, gemello) == []


def test_segno_automatico_presente_nel_proprio_si_scarta():
    proprio = documento(testo="Ristrutturazione della palestra comunale.")
    gemello = documento(
        fonte="g.pdf", id_bando="altro", testo="palestra palestra palestra atleti"
    )
    assert "palestra" not in gc.segni_automatici(proprio, gemello)


def test_coppia_di_parole_che_nel_proprio_non_sta_insieme():
    proprio = documento(testo="Il bando per la cultura. Lo sport non è ammesso.")
    gemello = documento(
        fonte="g.pdf",
        id_bando="altro",
        testo="bando sport; bando sport; bando sport; cultura",
    )
    assert "bando sport" in gc.segni_automatici(proprio, gemello)


def test_segni_automatici_verificati_sul_bando_intero():
    proroga = documento(fonte="proroga.pdf", id_bando="cultura", testo="Proroga.")
    gemello = documento(
        fonte="sport.pdf", id_bando="sport", testo="soggetto soggetto soggetto"
    )
    assert gc.segni_automatici(proroga, gemello) == ["soggetto"]
    avviso = documento(
        fonte="avviso.pdf", id_bando="cultura", testo="Il soggetto richiedente."
    )
    del_bando = gc.altri_del_bando(proroga, [proroga, avviso, gemello])
    assert del_bando == "Il soggetto richiedente."
    assert gc.segni_automatici(proroga, gemello, del_bando) == []


def test_automatici_uniti_ai_segni_e_nel_rapporto():
    cultura = documento(
        fonte="c.pdf", id_bando="cultura-missione-comune-2026", testo="cultura sport"
    )
    sport = documento(
        fonte="s.pdf",
        id_bando="sport-missione-comune-2026",
        testo="impiantistica impiantistica impiantistica",
    )
    segni = gc.segni_del_gemello(cultura, [sport])
    assert "impiantistica" in segni.automatici and "impiantistica" in segni.frasi
    assert "sport" in segni.scartati
    linee = gc.linee_dei_segni([cultura, sport])
    assert any("c.pdf" in x and "automatici impiantistica" in x for x in linee)


# --- regola delle domande a mano ---


def righe_b(trovati):
    return [
        {"riga": str(i), "B_trovato": "sì" if t else "no"}
        for i, t in enumerate(trovati)
    ]


def test_non_si_adotta_se_non_guadagna_con_le_domande_a_mano():
    base = {k: righe_b([False] * 20) for k in mr.K_ESATTI}
    meglio = {k: righe_b([True] * 8 + [False] * 12) for k in mr.K_ESATTI}
    base_mano = {k: righe_b([False] * 6) for k in mr.K_ESATTI}
    mano_meglio = {
        k: righe_b([True, False, False, False, False, False]) for k in mr.K_ESATTI
    }
    mano_uguale = {k: righe_b([False] * 6) for k in mr.K_ESATTI}
    assert mr.adottabile(base, meglio)
    assert mr.adottabile_con_mano(base, meglio, base_mano, mano_meglio)
    assert not mr.adottabile_con_mano(base, meglio, base_mano, mano_uguale)
    solo_k10 = {10: mano_meglio[10], 15: mano_uguale[15]}
    assert not mr.adottabile_con_mano(base, meglio, base_mano, solo_k10)
