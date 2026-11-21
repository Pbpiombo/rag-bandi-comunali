"""Contesto per frammento (scripts/diagnostica/genera_contesti.py).

Tutto inventato: documenti, frammenti, risposte. Nessuna chiamata al
modello di linguaggio: il client è finto.
"""

import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

import scripts.diagnostica.genera_contesti as gc

CONTESTO_BUONO = (
    "BANDO: Bando prova strade, articolo 3.\n"
    "ARGOMENTO: importi e massimali\n"
    "SERVE A: sapere quanto può ricevere al massimo un comune piccolo per "
    "sistemare le strade, e come si calcola la quota."
)


def documento(lungo=False, fonte="prova.pdf", id_bando="prova", parte=""):
    corpo = "Articolo 3. Il contributo massimo è di 50.000 euro per ogni comune. "
    altro = "Testo generico del bando senza numeri. " * (120 if lungo else 3)
    frammenti = [
        gc.FrammentoDaContestualizzare(f"{fonte}::{i}", i, testo)
        for i, testo in enumerate(
            [corpo.strip(), "Testo generico del bando senza numeri.", "Fine."]
        )
    ]
    return gc.Documento(
        fonte=fonte,
        id_bando=id_bando,
        titolo="Bando prova strade",
        atto="Decreto n. 123 del 01/02/2026",
        parte=parte,
        testo=corpo + altro + " Fine.",
        frammenti=frammenti,
    )


def risposta(testo=CONTESTO_BUONO, letti=0, scritti=0, stop="end_turn"):
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=testo)],
        usage=SimpleNamespace(
            input_tokens=200,
            cache_read_input_tokens=letti,
            cache_creation_input_tokens=scritti,
            output_tokens=80,
        ),
        stop_reason=stop,
        _request_id="req_prova",
    )


class ClientFinto:
    """messages.create registra gli argomenti e restituisce la risposta di `fai`."""

    def __init__(self, fai):
        self.chiamate = []
        self.messages = SimpleNamespace(create=self._crea)
        self._fai = fai

    def _crea(self, **argomenti):
        self.chiamate.append(argomenti)
        return self._fai(len(self.chiamate), argomenti)


def con_cache(numero, _):
    return risposta(scritti=1000) if numero == 1 else risposta(letti=1000)


# --- richiesta e costi ---


def test_richiesta_mette_in_cache_istruzioni_e_documento():
    d = documento()
    r = gc.richiesta(d, d.frammenti[0])
    assert r["model"] == "claude-haiku-5-5"
    assert r["system"] == gc.ISTRUZIONI
    assert r["thinking"] == {"type": "disabled"}
    primo, secondo = r["messages"][0]["content"]
    assert primo["cache_control"] == {"type": "ephemeral"}
    assert d.testo in primo["text"] and "Bando prova strade" in primo["text"]
    assert "cache_control" not in secondo
    assert d.frammenti[0].testo in secondo["text"]


def test_costo_dai_token():
    uso = {
        "input_tokens": 1_000_000,
        "cache_creation_input_tokens": 1_000_000,
        "cache_read_input_tokens": 1_000_000,
        "output_tokens": 1_000_000,
    }
    assert gc.costo(uso) == pytest.approx(0.10 + 0.125 + 0.01 + 0.50)


def test_l_impronta_cambia_con_le_istruzioni(monkeypatch):
    prima = gc.impronta_istruzioni()
    monkeypatch.setattr(gc, "ISTRUZIONI", gc.ISTRUZIONI + " ")
    assert gc.impronta_istruzioni() != prima


# --- tre righe e voci ---


def test_righe_del_contesto():
    righe = gc.righe_del_contesto(CONTESTO_BUONO)
    assert set(righe) == {"bando", "argomento", "serve_a"}
    assert righe["argomento"] == "importi e massimali"
    continua = gc.righe_del_contesto("BANDO: Bando prova\nsegue qui")
    assert continua == {"bando": "Bando prova segue qui"}
    assert gc.righe_del_contesto("Ecco il contesto\nBANDO: x") is None
    assert gc.righe_del_contesto("BANDO: x\nBANDO: y") is None


def test_voci_dell_argomento():
    voci, libero, ignote = gc.voci_dell_argomento(
        "Spese ammesse o escluse; cumulo con altri aiuti."
    )
    assert voci == ["spese ammesse o escluse", "cumulo con altri aiuti"]
    assert (libero, ignote) == ("", [])
    voci, libero, _ = gc.voci_dell_argomento("altro: definizioni dei termini")
    assert voci == ["altro"] and libero == "definizioni dei termini"
    _, _, ignote = gc.voci_dell_argomento("requisiti tecnici")
    assert ignote == ["requisiti tecnici"]


# --- generazione, ripresa, arresti ---


def test_genera_salva_una_riga_per_frammento(tmp_path):
    d = documento(lungo=True)
    client = ClientFinto(con_cache)
    percorso = tmp_path / "contesti.jsonl"
    conti = gc.genera([d], client, percorso, tetto=1.0)
    assert conti["chiamate"] == 3
    righe = [json.loads(x) for x in percorso.read_text(encoding="utf-8").splitlines()]
    assert [r["chunk_num"] for r in righe] == [0, 1, 2]
    primo = righe[0]
    assert primo["id"] == d.frammenti[0].id
    assert primo["cache_creation_input_tokens"] == 1000
    assert righe[1]["cache_read_input_tokens"] == 1000
    assert primo["argomento_voci"] == ["importi e massimali"]
    assert primo["impronta"] == gc.impronta_istruzioni()
    assert primo["sha256_frammento"] == d.frammenti[0].sha256


def test_ripresa_senza_rifare(tmp_path):
    d = documento(lungo=True)
    percorso = tmp_path / "contesti.jsonl"
    gc.genera([d], ClientFinto(con_cache), percorso, tetto=1.0)
    di_nuovo = ClientFinto(con_cache)
    conti = gc.genera([d], di_nuovo, percorso, tetto=1.0)
    assert conti["chiamate"] == 0 and di_nuovo.chiamate == []


def test_ripresa_dopo_interruzione(tmp_path):
    d = documento(lungo=True)
    percorso = tmp_path / "contesti.jsonl"
    gc.genera([d], ClientFinto(con_cache), percorso, tetto=1.0)
    righe = percorso.read_text(encoding="utf-8").splitlines()
    # l'ultima riga troncata, come dopo un'interruzione durante la scrittura
    percorso.write_text("\n".join([righe[0], righe[1][:30]]) + "\n", encoding="utf-8")
    client = ClientFinto(con_cache)
    gc.genera([d], client, percorso, tetto=1.0)
    assert len(client.chiamate) == 2


def test_arresto_sul_tetto_prima_di_chiamare(tmp_path):
    client = ClientFinto(con_cache)
    with pytest.raises(gc.ArrestoGenerazione, match="tetto"):
        gc.genera([documento()], client, tmp_path / "c.jsonl", tetto=1e-9)
    assert client.chiamate == []


def test_il_tetto_conta_i_lanci_precedenti(tmp_path):
    d = documento(lungo=True)
    percorso = tmp_path / "c.jsonl"
    gc.genera([d], ClientFinto(con_cache), percorso, tetto=1.0)
    speso = sum(r["costo_dollari"] for r in gc.leggi_salvati(percorso).values())
    altro = documento(lungo=True, fonte="altro.pdf")
    client = ClientFinto(con_cache)
    tetto = speso + gc.costo_massimo(altro, altro.frammenti[0]) / 2
    with pytest.raises(gc.ArrestoGenerazione, match="tetto"):
        gc.genera([d, altro], client, percorso, tetto=tetto)
    assert client.chiamate == []


def test_arresto_se_la_cache_non_legge_su_un_documento_lungo(tmp_path):
    percorso = tmp_path / "c.jsonl"
    client = ClientFinto(lambda n, _: risposta(scritti=1000 if n == 1 else 0))
    with pytest.raises(gc.ArrestoGenerazione, match="cache"):
        gc.genera([documento(lungo=True)], client, percorso, tetto=1.0)
    assert len(client.chiamate) == 2
    assert len(percorso.read_text(encoding="utf-8").splitlines()) == 2


def test_documento_corto_senza_cache_non_ferma(tmp_path):
    client = ClientFinto(lambda n, _: risposta())
    conti = gc.genera([documento()], client, tmp_path / "c.jsonl", tetto=1.0)
    assert conti["chiamate"] == 3


def test_impronta_diversa_ferma(tmp_path):
    percorso = tmp_path / "c.jsonl"
    percorso.write_text(json.dumps({"id": "x", "impronta": "vecchia"}) + "\n")
    with pytest.raises(gc.ArrestoGenerazione, match="altre istruzioni"):
        gc.genera([documento()], ClientFinto(con_cache), percorso, tetto=1.0)


def test_rifiuto_salvato_vuoto(tmp_path):
    client = ClientFinto(lambda n, _: risposta(testo="no", stop="refusal"))
    percorso = tmp_path / "c.jsonl"
    gc.genera([documento()], client, percorso, tetto=1.0)
    dato = next(iter(gc.leggi_salvati(percorso).values()))
    assert dato["testo"] == "" and dato["stop_reason"] == "refusal"


def _richiesta_http():
    return httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def test_chiama_ripete_e_poi_si_ferma():
    errore = anthropic.APIConnectionError(request=_richiesta_http())

    def fai(n, _):
        if n < 3:
            raise errore
        return risposta()

    assert gc.chiama(ClientFinto(fai), {}, attesa=0).stop_reason == "end_turn"

    def sempre(n, _):
        raise errore

    with pytest.raises(gc.ArrestoGenerazione, match="di fila"):
        gc.chiama(ClientFinto(sempre), {}, attesa=0)


def test_chiama_non_ripete_una_richiesta_rifiutata():
    risposta_http = httpx2.Response(400, request=_richiesta_http())
    errore = anthropic.BadRequestError("no", response=risposta_http, body=None)
    client = ClientFinto(lambda n, _: (_ for _ in ()).throw(errore))
    with pytest.raises(gc.ArrestoGenerazione, match="non si ripete"):
        gc.chiama(client, {}, attesa=0)
    assert len(client.chiamate) == 1


def test_main_senza_tetto():
    assert gc.main(["--prova"]) == 2


# --- ingressi ---


def test_controlla_documenti(monkeypatch):
    monkeypatch.setattr(gc, "NUMERO_FILE", 1)
    monkeypatch.setattr(gc, "NUMERO_FRAMMENTI", 3)
    d = documento()
    gc.controlla_documenti([d])
    d.frammenti[1].testo = "Frase che nel documento non c'è."
    with pytest.raises(gc.ArrestoGenerazione, match="non nel testo"):
        gc.controlla_documenti([d])


def test_contatti_rimasti():
    assert gc.contatti_rimasti("Scrivere a protocollo@pec.ente.it", None) == []
    rimasti = gc.contatti_rimasti("Referente: nome.cognome@ente.it", None)
    assert rimasti and rimasti[0].startswith("email")
    assert gc.contatti_rimasti("tel. 0573 123456", None)


# --- controlli ---


def dato(testo, stop="end_turn"):
    righe = gc.righe_del_contesto(testo) or {}
    voci, libero, ignote = gc.voci_dell_argomento(righe.get("argomento", ""))
    return {
        "testo": testo,
        "righe": righe,
        "argomento_voci": voci,
        "argomento_altro": libero,
        "argomento_non_ricondotto": ignote,
        "stop_reason": stop,
    }


def violazioni(testo, frammento=None, d=None, segni=None):
    d = d or documento()
    frammento = frammento if frammento is not None else d.frammenti[0].testo
    return gc.controlla_contesto(
        dato(testo), frammento, d, segni or gc.SegniDelGemello()
    )


def test_contesto_buono_senza_violazioni():
    assert violazioni(CONTESTO_BUONO) == []


def test_numero_non_nel_frammento():
    testo = CONTESTO_BUONO.replace("comune piccolo", "comune sotto i 5.000 abitanti")
    assert ("numero", "numero non nel frammento: 5.000") in violazioni(testo)
    nel_frammento = CONTESTO_BUONO.replace("al massimo", "al massimo 50.000 euro")
    assert violazioni(nel_frammento) == []


def test_numeri_dell_atto_e_riferimenti_ammessi():
    testo = CONTESTO_BUONO.replace("articolo 3", "articolo 3, decreto 123 del 2026")
    assert violazioni(testo) == []
    fuori = CONTESTO_BUONO.replace("articolo 3", "articolo 9")
    assert any(t == "numero" for t, _ in violazioni(fuori))


def test_mese_e_parole_di_numero():
    testo = CONTESTO_BUONO.replace("la quota", "la quota entro marzo")
    assert ("numero", "parola non nel frammento: marzo") in violazioni(testo)
    mila = CONTESTO_BUONO.replace("la quota", "la quota di cinquanta mila")
    assert sum(t == "numero" for t, _ in violazioni(mila)) == 2


def test_forma():
    assert ("forma", "vuoto") in violazioni("")
    assert ("forma", "domanda") in violazioni(CONTESTO_BUONO + " Quanto spetta?")
    assert ("forma", "premessa") in violazioni("Ecco il contesto:\n" + CONTESTO_BUONO)
    assert any(t == "forma" for t, _ in violazioni("Un testo senza righe"))
    lungo = CONTESTO_BUONO + " parola" * 200
    assert any("troppo lungo" in x for _, x in violazioni(lungo))
    copiato = (
        "BANDO: Bando prova strade\nARGOMENTO: importi e massimali\nSERVE A: "
        "Il contributo massimo è di 50.000 euro per ogni comune"
    )
    assert any("copiato" in x for _, x in violazioni(copiato))
    assert ("forma", "stop_reason max_tokens") in gc.controlla_contesto(
        dato(CONTESTO_BUONO, "max_tokens"),
        documento().frammenti[0].testo,
        documento(),
        gc.SegniDelGemello(),
    )


def test_solo_bando_ammesso():
    assert violazioni("BANDO: Bando prova strade, indice.") == []


def test_argomento_non_ricondotto():
    testo = CONTESTO_BUONO.replace("importi e massimali", "requisiti tecnici")
    assert any("non ricondotto" in x for _, x in violazioni(testo))


def apistici():
    nomi = {
        "A1": "Azione B1: Lotta a parassiti e malattie",
        "A3": "Azione B3: Ripopolamento patrimonio apistico",
    }
    return [
        documento(fonte=f"decreto-allegato-{a.lower()}-x.pdf", id_bando="api", parte=p)
        for a, p in nomi.items()
    ]


def test_gemello_tra_allegati():
    a1, a3 = apistici()
    segni = gc.segni_del_gemello(a1, gc.gemelli_dei_file([a1, a3])[a1.fonte])
    assert {"B3", "A3"} <= segni.codici
    assert "ripopolamento patrimonio apistico" in segni.frasi
    testo = CONTESTO_BUONO.replace("articolo 3", "azione B3")
    trovate = violazioni(testo, d=a1, segni=segni)
    assert ("gemello", "codice B3") in trovate
    # ammesso se il frammento parla proprio dell'altra azione
    frammento = a1.frammenti[0].testo + " Vale anche per l'azione B3."
    assert ("gemello", "codice B3") not in violazioni(
        testo, frammento=frammento, d=a1, segni=segni
    )


def test_gemello_tra_bandi():
    cultura = documento(fonte="cultura.pdf", id_bando="cultura-missione-comune-2026")
    sport = documento(fonte="sport.pdf", id_bando="sport-missione-comune-2026")
    gemelli = gc.gemelli_dei_file([cultura, sport])
    assert gemelli[cultura.fonte] == [sport]
    segni = gc.segni_del_gemello(cultura, gemelli[cultura.fonte])
    testo = CONTESTO_BUONO.replace("strade", "strade e lo sport")
    assert ("gemello", "nome 'sport'") in violazioni(testo, d=cultura, segni=segni)
    sportello = CONTESTO_BUONO.replace("strade", "strade allo sportello")
    assert violazioni(sportello, d=cultura, segni=segni) == []


def test_controlla_tutti_conta_e_rapporta():
    d = documento()
    salvati = {
        d.frammenti[0].id: dato(CONTESTO_BUONO),
        d.frammenti[1].id: dato(CONTESTO_BUONO.replace("piccolo", "di 7 abitanti")),
    }
    violati, linee = gc.controlla_tutti([d], salvati)
    assert list(violati) == [d.frammenti[1].id]
    assert any("almeno una violazione: 1" in x for x in linee)


def test_testo_di_ricerca():
    righe = gc.righe_del_contesto(CONTESTO_BUONO)
    assert gc.testo_di_ricerca(righe, ("bando", "serve_a")).startswith("Bando prova")
    assert "importi" not in gc.testo_di_ricerca(righe, ("bando", "serve_a"))
