"""Quattro modifiche del 21/11/2026 dopo la prova sull'allegato A3.

Riga DOVE allargata, ARGOMENTO normalizzato con le forme vicine, gemelli
caricati nella prova, segni automatici verificati sulla radice. Tutto
inventato; nessuna chiamata al modello di linguaggio.
"""

import json
from types import SimpleNamespace

import scripts.diagnostica.genera_contesti as gc

CORPO = (
    "1.1 Finalità e obiettivi\n"
    "Il bando sostiene le aziende.\n"
    "2. REQUISITI DI ACCESSO\n"
    "Possono partecipare gli apicoltori.\n"
    "7.1 Trattamento dei dati personali\n"
    "3. I dati sono trattati dalla Regione.\n"
)


def documento(fonte="a.pdf", id_bando="b", parte="", testo=CORPO):
    return gc.Documento(
        fonte=fonte,
        id_bando=id_bando,
        titolo="Bando prova",
        atto="Decreto n. 123 del 01/02/2026",
        parte=parte,
        testo=testo,
        frammenti=[gc.FrammentoDaContestualizzare(f"{fonte}::0", 0, testo)],
    )


def contesto(dove, argomento="chi può partecipare", serve="sapere chi partecipa"):
    return (
        f"DOVE: {dove}\nARGOMENTO: {argomento}\nSERVE A: {serve}\n"
        "PAROLE: chi partecipa; requisiti; apicoltori; aziende; domanda"
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


# --- 1. riga DOVE ---


def test_riferimento_seguito_da_punteggiatura():
    assert violazioni(contesto('1.1, "Finalità e obiettivi"')) == []
    assert violazioni(contesto("paragrafi 1.1 e 7.1, trattamento")) == []


def test_numero_solo_che_apre_una_riga():
    assert violazioni(contesto("2. REQUISITI DI ACCESSO, lettera a)")) == []
    assert violazioni(contesto("7.1, paragrafi 2 e 3")) == []


def test_numero_inventato_resta_una_violazione():
    solo = violazioni(contesto("5. CONTROLLI, lettera b)"))
    assert ("numero", "numero non di struttura nella riga DOVE: 5") in solo
    struttura = violazioni(contesto("9.4, Verifiche finali"))
    assert ("numero", "riferimento non nel documento: '9.4'") in struttura


def test_numero_nel_testo_ma_non_a_inizio_riga():
    # "4" sta nel testo del documento, ma non apre nessuna riga
    d = documento(testo=CORPO + "Si veda il punto 4 della delibera.\n")
    trovate = violazioni(contesto("punto 4"), d)
    assert trovate == []  # con la parola davanti vale la regola di prima
    assert ("numero", "numero non di struttura nella riga DOVE: 4") in violazioni(
        contesto("4, delibera"), d
    )


def test_data_nella_riga_dove():
    trovate = violazioni(contesto("2. REQUISITI, entro il 30/06/2026"))
    assert ("numero", "numero non di struttura nella riga DOVE (data): 30/06/2026") in (
        trovate
    )


# --- 2. ARGOMENTO normalizzato ---


def test_normalizza_le_sette_righe_della_prova():
    casi = {
        "obblighi, vincoli e revoche; cause di forza maggiore;": (
            "obblighi, vincoli e revoche"
        ),
        "criteri di priorità; punteggi e criteri di valutazione": (
            "punteggi e criteri di valutazione"
        ),
        "obblighi, vincoli e revoche; rinunce al sostegno": (
            "obblighi, vincoli e revoche"
        ),
        "varianti, modifiche non sostanziali": "varianti, proroghe e modifiche",
        "trattamento dei dati personali; riferimenti normativi; finalità del "
        "trattamento; titolare del trattamento": (
            "trattamento dei dati personali; riferimenti normativi"
        ),
        "spese e massimali; spese ammesse o escluse": "spese ammesse o escluse",
        "spese ammissibili; spese escluse; documenti da allegare": (
            "spese ammesse o escluse; documenti da allegare"
        ),
    }
    for originale, atteso in casi.items():
        assert gc.normalizza_argomento(originale) == atteso, originale


def test_normalizza_massimo_tre_e_altro():
    quattro = "definizioni; glossario; controlli; istruttoria; privacy"
    assert gc.normalizza_argomento(quattro) == (
        "definizioni; controlli e sanzioni; istruttoria e graduatoria"
    )
    assert gc.normalizza_argomento("polizze assicurative; leasing") == (
        "altro: polizze assicurative, leasing"
    )
    assert gc.normalizza_argomento("altro: codici Ateco") == "altro: codici Ateco"
    misto = "chi può partecipare; altro: requisiti penali"
    assert gc.normalizza_argomento(misto) == "chi può partecipare"


def test_forme_vicine_solo_verso_voci_dell_elenco():
    assert set(gc.FORME_VICINE) <= set(gc.VOCI)
    forme = [f for lista in gc.FORME_VICINE.values() for f in lista]
    assert len(forme) == len(set(forme))
    assert not set(forme) & set(gc.VOCI)


def test_il_file_tiene_la_riga_del_modello():
    dato = salvato(
        contesto("2. REQUISITI", "spese ammissibili; cause di forza maggiore")
    )
    assert dato["righe"]["argomento"] == "spese ammesse o escluse"
    assert dato["argomento_modello"] == "spese ammissibili; cause di forza maggiore"
    assert dato["argomento_voci"] == ["spese ammesse o escluse"]
    assert "spese ammesse o escluse" in gc.testo_di_ricerca(dato["righe"])


def test_si_normalizza_anche_leggendo_righe_vecchie(tmp_path):
    vecchio = {
        "id": "x",
        "impronta": "i",
        "righe": {"argomento": "varianti; titolare del trattamento"},
        "argomento_voci": [],
    }
    percorso = tmp_path / "c.jsonl"
    percorso.write_text(json.dumps(vecchio) + "\n", encoding="utf-8")
    letto = gc.leggi_salvati(percorso)["x"]
    assert letto["righe"]["argomento"] == "varianti, proroghe e modifiche"
    assert letto["argomento_modello"] == "varianti; titolare del trattamento"


# --- 3. gemelli nella prova ---


def apistici():
    a1 = documento(fonte="decreto-allegato-a1-x.pdf", parte="Azione B1: Lotta")
    a3 = documento(fonte="decreto-allegato-a3-x.pdf", parte="Azione B3: Ripopolamento")
    return a1, a3


def test_controlli_della_prova_caricano_i_gemelli(tmp_path, monkeypatch):
    a1, a3 = apistici()
    monkeypatch.setattr(gc, "leggi_documenti", lambda: [a1, a3])
    monkeypatch.setattr(gc, "CARTELLA", tmp_path)
    monkeypatch.setattr(gc, "FILE_PROVA", tmp_path / "prova.jsonl")
    dato = salvato(
        contesto("2. REQUISITI", serve="sapere chi partecipa all'azione B3"), a1
    )
    gc.aggiungi(gc.FILE_PROVA, dato)
    assert gc.main(["--controlla", "--prova"]) == 0
    (scritto,) = tmp_path.glob("controllo_contesti_prova_*.txt")
    rapporto = scritto.read_text(encoding="utf-8")
    assert "gemello: codice B3" in rapporto
    assert "decreto-allegato-a3-x.pdf" not in rapporto.split("Per file:")[1]


def test_controlla_tutti_cerca_i_gemelli_fra_tutti():
    a1, a3 = apistici()
    dato = salvato(
        contesto("2. REQUISITI", serve="sapere chi partecipa all'azione B3"), a1
    )
    senza, _ = gc.controlla_tutti([a1], {a1.frammenti[0].id: dato})
    con, _ = gc.controlla_tutti([a1], {a1.frammenti[0].id: dato}, [a1, a3])
    assert not senza
    assert ("gemello", "codice B3") in con[a1.frammenti[0].id]


# --- 4. segni automatici sulla radice ---


def test_segno_automatico_verificato_sulla_radice():
    proprio = documento(testo="Si finanziano attrezzature e arnie.")
    gemello = documento(
        fonte="g.pdf",
        id_bando="altro",
        testo="attrezzatura attrezzatura attrezzatura nomadismo nomadismo nomadismo",
    )
    assert gc.segni_automatici(proprio, gemello) == ["nomadismo"]


def test_coppia_verificata_sulle_radici():
    proprio = documento(testo="Il bando per la cultura. Lo sport non è ammesso.")
    gemello = documento(
        fonte="g.pdf", id_bando="altro", testo="bando sport; bando sport; bando sport"
    )
    assert "bando sport" in gc.segni_automatici(proprio, gemello)
    # le radici di "bando sportivo" stanno insieme in "bando sportiva"
    gemello_lungo = documento(
        fonte="g.pdf",
        id_bando="altro",
        testo="bando sportivo; bando sportivo; bando sportivo",
    )
    vicini = documento(testo="Il bando sportiva per la cultura.")
    assert "bando sportivo" not in gc.segni_automatici(vicini, gemello_lungo)
    assert "bando sportivo" in gc.segni_automatici(proprio, gemello_lungo) or (
        "sportivo" in gc.segni_automatici(proprio, gemello_lungo)
    )


def test_il_segno_si_cerca_nel_contesto_com_e():
    segni = gc.SegniDelGemello(frasi={"nomadismo"})
    assert ("gemello", "nome 'nomadismo'") in violazioni(
        contesto("2. REQUISITI", serve="sapere del nomadismo"), segni=segni
    )
    assert (
        violazioni(contesto("2. REQUISITI", serve="sapere dei nomadi"), segni=segni)
        == []
    )
