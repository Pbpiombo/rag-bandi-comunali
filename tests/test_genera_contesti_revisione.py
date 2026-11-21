"""Revisione del 21/11/2026 del contesto per frammento (genera_contesti.py).

Riga BANDO composta dal programma, righe DOVE / ARGOMENTO / SERVE A del
modello, controlli rivisti, segni del gemello verificati, troncamento
rifatto una volta, prova su un file a scelta. Tutto inventato; nessuna
chiamata al modello di linguaggio.
"""

import json
from types import SimpleNamespace

import pytest

import scripts.diagnostica.genera_contesti as gc
import scripts.diagnostica.misura_recupero_avvisi as mr

CONTESTO = (
    "DOVE: articolo 3 «Contributo», paragrafo 4.2.2\n"
    "ARGOMENTO: importi e massimali; riferimenti normativi\n"
    "SERVE A: sapere quanto può ricevere al massimo un comune piccolo per "
    "sistemare le strade del territorio, e da quali regole dipende la quota "
    "che resta a carico dell'ente richiedente."
)
TITOLO_API = (
    "Sostegno agli investimenti strutturali nelle aziende apistiche: azioni B1–B3–B4–B5"
)


def documento(
    fonte="prova.pdf", id_bando="prova", parte="", titolo="Bando prova strade"
):
    corpo = (
        # 4.2.2 apre una riga, come nei PDF: dal 21/11/2026 un riferimento
        # senza parola davanti vale solo se nel documento apre una riga
        "Articolo 3. Contributo.\n4.2.2 Importo. Il contributo massimo è di 50.000 "
        "euro per ogni comune. "
    )
    frammenti = [
        gc.FrammentoDaContestualizzare(f"{fonte}::{i}", i, testo)
        for i, testo in enumerate([corpo.strip(), "Testo generico.", "Fine."])
    ]
    return gc.Documento(
        fonte=fonte,
        id_bando=id_bando,
        titolo=titolo,
        atto="Decreto n. 123 del 01/02/2026",
        parte=parte,
        testo=corpo + "Testo generico. Fine.",
        frammenti=frammenti,
    )


def dato(testo, d=None, stop="end_turn"):
    d = d or documento()
    risposta = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=testo)],
        usage=SimpleNamespace(
            input_tokens=10,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
            output_tokens=10,
        ),
        stop_reason=stop,
    )
    return gc.riga_salvata(d, d.frammenti[0], risposta)


def violazioni(testo, d=None, frammento=None, segni=None):
    d = d or documento()
    frammento = frammento if frammento is not None else d.frammenti[0].testo
    return gc.controlla_contesto(
        dato(testo, d), frammento, d, segni or gc.SegniDelGemello()
    )


# --- riga BANDO composta dal programma ---


def test_riga_bando_composta_e_azione_sola():
    api = documento(
        fonte="decreto-allegato-a3-x.pdf",
        parte="Azione B3: Ripopolamento patrimonio apistico",
        titolo=TITOLO_API,
    )
    riga = gc.riga_bando(api)
    assert riga == (
        "Sostegno agli investimenti strutturali nelle aziende apistiche; "
        "Decreto n. 123 del 01/02/2026; Azione B3: Ripopolamento patrimonio apistico"
    )
    assert "B1" not in riga and "B4" not in riga
    assert "B1" not in gc.blocco_documento(api)
    # senza azione nella parte il titolo resta com'è
    assert gc.riga_bando(documento()).startswith("Bando prova strade; Decreto")


def test_la_riga_bando_del_modello_si_scarta():
    salvato = dato("BANDO: un altro titolo\n" + CONTESTO)
    assert salvato["righe"]["bando"] == gc.riga_bando(documento())
    assert salvato["bando_scritto_dal_modello"] == "un altro titolo"
    assert salvato["righe"]["dove"].startswith("articolo 3")
    assert salvato["argomento_voci"] == ["importi e massimali", "riferimenti normativi"]


def test_testo_di_ricerca_con_dove():
    righe = dato(CONTESTO)["righe"]
    testo = gc.testo_di_ricerca(righe)
    assert testo.startswith("Bando prova strade") and "articolo 3" in testo
    # aggiornato il 21/11/2026 con la riga PAROLE (decisione 2)
    assert mr.RIGHE_CONTESTO["tutte"] == (
        "bando",
        "dove",
        "argomento",
        "serve_a",
        "parole",
    )
    assert "dove" in mr.RIGHE_CONTESTO["senza-serve-a"]


def test_il_prompt_non_chiede_la_riga_bando():
    assert "DOVE:" in gc.ISTRUZIONI and "BANDO:" not in gc.ISTRUZIONI
    assert "da una a tre voci" in gc.ISTRUZIONI
    assert all(v in gc.ISTRUZIONI for v in gc.VOCI)
    assert gc.MAX_TOKENS >= 600


# --- controlli rivisti ---


def test_contesto_rivisto_senza_violazioni():
    assert violazioni(CONTESTO) == []


def test_la_riga_bando_composta_non_si_controlla():
    api = documento(parte="Azione B3: Ripopolamento", titolo=TITOLO_API)
    segni = gc.SegniDelGemello(codici={"B1"})
    d = dato(CONTESTO, api)
    d["righe"]["bando"] = "Titolo con B1 e 9.999 euro"
    assert gc.controlla_contesto(d, api.frammenti[0].testo, api, segni) == []


def test_numeri_della_riga_dove():
    fuori = CONTESTO.replace("articolo 3", "articolo 9")
    assert any("riferimento non nel documento" in x for _, x in violazioni(fuori))
    senza_par = CONTESTO.replace("paragrafo 4.2.2", "4.2.2")
    assert violazioni(senza_par) == []
    assente = CONTESTO.replace("paragrafo 4.2.2", "16.4")
    assert ("numero", "riferimento non nel documento: '16.4'") in violazioni(assente)
    data = CONTESTO.replace("paragrafo 4.2.2", "entro il 30/06/2026")
    assert any("non di struttura" in x for _, x in violazioni(data))
    mese = CONTESTO.replace("paragrafo 4.2.2", "dal mese di marzo")
    assert any("riga DOVE: marzo" in x for _, x in violazioni(mese))


def test_numeri_di_argomento_e_serve_a_solo_dal_frammento():
    atto = CONTESTO.replace("un comune piccolo", "un comune, decreto 123,")
    assert ("numero", "numero non nel frammento: 123") in violazioni(atto)
    nel_frammento = CONTESTO.replace("al massimo", "al massimo 50.000 euro")
    assert violazioni(nel_frammento) == []
    lettere = CONTESTO.replace("al massimo", "al massimo cinquanta mila euro")
    assert sum(t == "numero" for t, _ in violazioni(lettere)) == 2


def test_struttura_non_scambia_le_migliaia():
    assert gc.STRUTTURA.findall("4.2.2 e 16.4 e 1.3.2.1") == [
        "4.2.2",
        "16.4",
        "1.3.2.1",
    ]
    assert gc.STRUTTURA.findall("50.000 e 1.242.000 e 18.000,00 e 18.06.2026") == []


def test_mancano_argomento_o_serve_a():
    solo_dove = "DOVE: articolo 3"
    assert ("forma", "manca ARGOMENTO o SERVE A") in violazioni(solo_dove)


# --- gemelli: segni verificati ---


def test_segno_scartato_se_compare_nel_proprio_documento():
    cultura = documento(fonte="cultura.pdf", id_bando="cultura-missione-comune-2026")
    sport = documento(fonte="sport.pdf", id_bando="sport-missione-comune-2026")
    segni = gc.segni_del_gemello(cultura, [sport])
    assert "sport" in segni.frasi
    cultura.testo += " Restano esclusi gli impianti per lo sport."
    segni = gc.segni_del_gemello(cultura, [sport])
    assert "sport" not in segni.frasi and "sport" in segni.scartati


def test_coppia_senza_segni_nel_rapporto():
    cultura = documento(fonte="cultura.pdf", id_bando="cultura-missione-comune-2026")
    sport = documento(fonte="sport.pdf", id_bando="sport-missione-comune-2026")
    cultura.testo += " sport"
    sport.testo += " cultura"
    linee = gc.linee_dei_segni([cultura, sport])
    assert all("rimasti NESSUNO" in x for x in linee) and len(linee) == 2


def test_codici_delle_altre_azioni_solo_nelle_righe_del_modello():
    a1 = documento(
        fonte="decreto-allegato-a1-x.pdf",
        id_bando="api",
        parte="Azione B1: Lotta a parassiti e malattie",
        titolo=TITOLO_API,
    )
    a3 = documento(
        fonte="decreto-allegato-a3-x.pdf",
        id_bando="api",
        parte="Azione B3: Ripopolamento patrimonio apistico",
        titolo=TITOLO_API,
    )
    segni = gc.segni_del_gemello(a1, gc.gemelli_dei_file([a1, a3])[a1.fonte])
    assert {"B3", "A3"} <= segni.codici
    # il titolo proprio contiene "B3": il codice resta un segno solo se non è
    # nel testo del documento, e il titolo con la lista non entra nella riga
    assert "B3" not in gc.riga_bando(a1)
    nel_serve = CONTESTO.replace("sistemare le strade", "l'azione B3")
    trovate = gc.controlla_contesto(
        dato(nel_serve, a1), a1.frammenti[0].testo, a1, segni
    )
    assert ("gemello", "codice B3") in trovate


def test_il_codice_nel_proprio_documento_si_scarta():
    a1 = documento(
        fonte="decreto-allegato-a1-x.pdf",
        id_bando="api",
        parte="Azione B1: Lotta",
        titolo=TITOLO_API,
    )
    a3 = documento(
        fonte="decreto-allegato-a3-x.pdf",
        id_bando="api",
        parte="Azione B3: Ripopolamento",
        titolo=TITOLO_API,
    )
    a1.testo += " Le azioni B1 e B3 sono attivate."
    segni = gc.segni_del_gemello(a1, [a3])
    assert "B3" in segni.scartati and "B3" not in segni.codici


# --- troncamento rifatto una volta ---


def risposta(stop, uscita=100):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=CONTESTO)],
        usage=SimpleNamespace(
            input_tokens=100,
            cache_read_input_tokens=0,
            cache_creation_input_tokens=0,
            output_tokens=uscita,
        ),
        stop_reason=stop,
    )


class Client:
    def __init__(self, esiti):
        self.esiti = list(esiti)
        self.chiamate = 0
        self.messages = SimpleNamespace(create=self._crea)

    def _crea(self, **_):
        self.chiamate += 1
        return self.esiti.pop(0)


def test_troncato_si_rifa_una_volta(tmp_path):
    d = documento()
    d.frammenti = d.frammenti[:1]
    client = Client([risposta("max_tokens", 600), risposta("end_turn")])
    percorso = tmp_path / "c.jsonl"
    conti = gc.genera([d], client, percorso, tetto=1.0)
    assert client.chiamate == 2 and conti["chiamate"] == 2
    righe = [json.loads(x) for x in percorso.read_text(encoding="utf-8").splitlines()]
    assert len(righe) == 1
    assert righe[0]["stop_reason"] == "end_turn" and righe[0]["rifatto"] is True
    assert righe[0]["output_tokens_primo_tentativo"] == 600
    attesa = gc.costo(
        {
            "input_tokens": 200,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "output_tokens": 700,
        }
    )
    assert righe[0]["costo_dollari"] == pytest.approx(attesa)
    assert conti["spesi"] == pytest.approx(attesa)


def test_troncato_due_volte_non_si_rifa_ancora(tmp_path):
    d = documento()
    d.frammenti = d.frammenti[:1]
    client = Client([risposta("max_tokens"), risposta("max_tokens")])
    gc.genera([d], client, tmp_path / "c.jsonl", tetto=1.0)
    assert client.chiamate == 2
    salvato = next(iter(gc.leggi_salvati(tmp_path / "c.jsonl").values()))
    assert salvato["stop_reason"] == "max_tokens"


# --- prova su un file a scelta e rapporto ---


def test_prova_su_un_file_a_scelta():
    a, b = documento(fonte="a.pdf"), documento(fonte="b.pdf")
    assert gc.documenti_della_prova([a, b], "b.pdf") == [b]
    with pytest.raises(gc.ArrestoGenerazione, match="non è tra"):
        gc.documenti_della_prova([a, b], "c.pdf")
    assert gc.main(["--file", "b.pdf", "--tetto-dollari", "0.1"]) == 2


def test_rapporto_dice_la_revisione():
    d = documento()
    salvati = {d.frammenti[0].id: dato(CONTESTO, d)}
    _, linee = gc.controlla_tutti([d], salvati)
    assert gc.NOTA_REVISIONE in linee
    assert any("non i risultati di ricerca" in x for x in linee)
