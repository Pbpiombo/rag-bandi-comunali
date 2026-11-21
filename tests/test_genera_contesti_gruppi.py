"""Controlli e misura della terza mossa del 19d (21/11/2026, prima della misura).

a. forme vicine di ARGOMENTO anche dopo "altro:", normalizzazione congelata;
b. tre gruppi di violazioni: contenuto, segno automatico del gemello, forma;
c. condizione di arresto sui soli contenuto e segni automatici non tolti;
d. si scartano i contesti con violazioni vere, non quelli di sola forma;
e. il rapporto dei controlli non sovrascrive il precedente;
f. niente soglia fissa RUMORE: vale il test dei segni.
Tutto inventato; nessuna chiamata al modello di linguaggio.
"""

from types import SimpleNamespace

import pytest

import scripts.diagnostica.genera_contesti as gc
import scripts.diagnostica.misura_recupero_avvisi as mr

CULTURA = "cultura-missione-comune-2026"
SPORT = "sport-missione-comune-2026"


def documento(fonte, id_bando, testo, n=1):
    frammenti = [
        gc.FrammentoDaContestualizzare(f"{fonte}::{i}", i, f"{testo} Parte {i}.")
        for i in range(n)
    ]
    return gc.Documento(
        fonte=fonte,
        id_bando=id_bando,
        titolo="Bando prova",
        atto="Decreto n. 123 del 01/02/2026",
        parte="",
        testo=" ".join(f.testo for f in frammenti),
        frammenti=frammenti,
    )


def coppia(n=3):
    """Cultura con n frammenti; il gemello Sport con un segno automatico."""
    cultura = documento("c.pdf", CULTURA, "Il bando sostiene la cultura.", n)
    sport = documento(
        "s.pdf", SPORT, "impiantistica impiantistica impiantistica sport sport sport"
    )
    return cultura, sport


def contesto(serve="sapere chi partecipa", argomento="chi può partecipare"):
    return (
        f"DOVE: non indicato\nARGOMENTO: {argomento}\nSERVE A: {serve}\n"
        "PAROLE: chi partecipa; requisiti; enti; associazioni; domanda"
    )


def salvato(testo, d, i=0):
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
    return gc.riga_salvata(d, d.frammenti[i], risposta)


def violazioni(testo, d, segni):
    return gc.controlla_contesto(salvato(testo, d), d.frammenti[0].testo, d, segni)


# --- a. forme vicine dopo "altro:" ---


def test_forme_vicine_anche_dopo_altro():
    assert gc.normalizza_argomento("altro: varianti, modifiche non sostanziali") == (
        "varianti, proroghe e modifiche"
    )
    assert gc.normalizza_argomento("altro: spese ammissibili") == (
        "spese ammesse o escluse"
    )
    assert gc.normalizza_argomento("istruttoria; altro: graduatoria") == (
        "istruttoria e graduatoria"
    )
    # una voce c'è già: il testo libero che non si riconduce si scarta
    assert gc.normalizza_argomento("chi può partecipare; altro: requisiti penali") == (
        "chi può partecipare"
    )
    # senza forme vicine resta "altro"
    assert gc.normalizza_argomento("altro: codici Ateco") == "altro: codici Ateco"


def test_le_righe_salvate_si_rinormalizzano_dalla_riga_del_modello():
    # una riga salvata con la regola di prima: "altro:" restava "altro"
    vecchia = {
        "righe": {"argomento": "altro: varianti, modifiche"},
        "argomento_modello": "altro: varianti, modifiche",
        "argomento_voci": ["altro"],
    }
    nuova = gc.con_argomento_normalizzato(vecchia)
    assert nuova["righe"]["argomento"] == "varianti, proroghe e modifiche"
    assert nuova["argomento_voci"] == ["varianti, proroghe e modifiche"]
    assert nuova["argomento_modello"] == "altro: varianti, modifiche"
    assert gc.con_argomento_normalizzato(nuova) == nuova


def test_normalizzazione_congelata():
    # fino a fine misura (21/11/2026): se cambia, la misura non vale più
    assert gc.impronta_normalizzazione()[:12] == "d883256b1359"


# --- b. tre gruppi ---


def test_segno_automatico_e_segno_a_mano_in_gruppi_diversi():
    cultura, sport = coppia(1)
    segni = gc.segni_del_gemello(cultura, [sport])
    assert "impiantistica" in segni.automatici
    # "sport" è anche frequente nel gemello, ma è scelto a mano e verificato
    assert "sport" in segni.frasi and "sport" not in segni.automatici
    automatico = violazioni(contesto("sapere dell'impiantistica"), cultura, segni)
    assert automatico == [(gc.GEMELLO_AUTOMATICO, "nome 'impiantistica'")]
    assert gc.gruppi_di(automatico) == {gc.AUTOMATICO}
    a_mano = violazioni(contesto("sapere dello sport"), cultura, segni)
    assert a_mano == [("gemello", "nome 'sport'")]
    assert gc.gruppi_di(a_mano) == {gc.CONTENUTO}
    numero = violazioni(contesto("sapere chi partecipa dal 2019"), cultura, segni)
    assert gc.gruppi_di(numero) == {gc.CONTENUTO}
    forma = violazioni(contesto("sapere chi partecipa?"), cultura, segni)
    assert gc.gruppi_di(forma) == {gc.FORMA}
    assert not gc.da_scartare(forma)
    assert gc.da_scartare(automatico) and gc.da_scartare(a_mano)


def test_rapporto_dei_tre_gruppi():
    cultura, sport = coppia(3)
    salvati = {
        cultura.frammenti[0].id: salvato(contesto("sapere dello sport"), cultura, 0),
        cultura.frammenti[1].id: salvato(
            contesto("sapere dell'impiantistica?"), cultura, 1
        ),
        cultura.frammenti[2].id: salvato(contesto("sapere chi partecipa?"), cultura, 2),
        sport.frammenti[0].id: salvato(contesto(), sport, 0),
    }
    violati, linee = gc.controlla_tutti([cultura, sport], salvati)
    assert len(violati) == 3
    testo = "\n".join(linee)
    assert "almeno una violazione: 3" in testo
    assert "  contenuto (numeri, date, segni del gemello" in testo
    assert "codici di altre azioni, numeri d'atto): 1 (25.0%)" in testo
    assert "  segno automatico del gemello: 1 (25.0%), di cui senza" in testo
    assert "  forma: 2 (50.0%), di cui di sola forma 1" in testo
    assert "Violazioni vere (contenuto, o segno automatico non tolto): 2 (50.0%)" in (
        testo
    )
    assert "  c.pdf: 3 / 3, 3; 1, 1, 2; 2" in linee
    assert "gemello automatico: nome 'impiantistica'" in testo


# --- c. segni automatici tolti dopo la lettura ---


def test_file_dei_segni_tolti(tmp_path):
    assert gc.leggi_segni_tolti(tmp_path / "manca.txt") == set()
    percorso = tmp_path / "tolti.txt"
    percorso.write_text(
        "# usi generici, letti a mano\n\nc.pdf | Impiantistica\n", encoding="utf-8"
    )
    assert gc.leggi_segni_tolti(percorso) == {("c.pdf", "impiantistica")}
    percorso.write_text("c.pdf impiantistica\n", encoding="utf-8")
    with pytest.raises(gc.ArrestoGenerazione, match="riga 1"):
        gc.leggi_segni_tolti(percorso)


def test_si_toglie_solo_un_segno_automatico():
    cultura, sport = coppia(1)
    salvati = {
        cultura.frammenti[0].id: salvato(
            contesto("sapere dell'impiantistica"), cultura
        ),
        sport.frammenti[0].id: salvato(contesto(), sport),
    }
    con, _ = gc.controlla_tutti([cultura, sport], salvati)
    assert cultura.frammenti[0].id in con
    tolti = {("c.pdf", "impiantistica")}
    senza, linee = gc.controlla_tutti([cultura, sport], salvati, tolti=tolti)
    assert not senza
    assert any("automatici tolti dopo la lettura impiantistica" in x for x in linee)
    assert any("tolti dopo la lettura: c.pdf | impiantistica" in x for x in linee)
    with pytest.raises(gc.ArrestoGenerazione, match="non sono automatici"):
        gc.controlla_tutti([cultura, sport], salvati, tolti={("c.pdf", "sport")})
    with pytest.raises(gc.ArrestoGenerazione, match="file sconosciuti"):
        gc.controlla_tutti([cultura, sport], salvati, tolti={("x.pdf", "sport")})


def test_arresto_conta_contenuto_e_automatici_non_tolti():
    cultura, sport = coppia(20)
    salvati = {
        f.id: salvato(contesto(), cultura, i) for i, f in enumerate(cultura.frammenti)
    }
    salvati[sport.frammenti[0].id] = salvato(contesto(), sport)
    # due di sola forma su 21: sopra il 5%, ma la forma non conta
    for i in (0, 1):
        salvati[cultura.frammenti[i].id] = salvato(
            contesto("sapere chi partecipa?"), cultura, i
        )
    contesti, scartati = mr.contesti_da([cultura, sport], salvati, "tutte")
    assert scartati == {}
    # due da segno automatico: contano, e la misura si ferma
    for i in (0, 1):
        salvati[cultura.frammenti[i].id] = salvato(
            contesto("sapere dell'impiantistica"), cultura, i
        )
    with pytest.raises(mr.ErroreMisura, match="violazioni vere 2 su 21"):
        mr.contesti_da([cultura, sport], salvati, "tutte")
    # tolto il segno dopo la lettura, non contano più
    tolti = {("c.pdf", "impiantistica")}
    contesti, scartati = mr.contesti_da([cultura, sport], salvati, "tutte", tolti)
    assert scartati == {}
    assert len(contesti) == 21


# --- d. cosa si scarta ---


def test_si_scartano_solo_i_contesti_con_violazioni_vere(monkeypatch):
    monkeypatch.setattr(gc, "QUOTA_VIOLAZIONI", 0.9)
    cultura, sport = coppia(3)
    salvati = {
        cultura.frammenti[0].id: salvato(contesto("sapere dello sport"), cultura, 0),
        cultura.frammenti[1].id: salvato(
            contesto("sapere dell'impiantistica"), cultura, 1
        ),
        cultura.frammenti[2].id: salvato(contesto("sapere chi partecipa?"), cultura, 2),
        sport.frammenti[0].id: salvato(contesto(), sport),
    }
    contesti, scartati = mr.contesti_da([cultura, sport], salvati, "tutte")
    assert set(scartati) == {cultura.frammenti[0].id, cultura.frammenti[1].id}
    # il contesto di sola forma entra nella misura
    assert set(contesti) == {("c.pdf", 2), ("s.pdf", 0)}
    assert "chi partecipa?" in contesti[("c.pdf", 2)]


# --- e. il rapporto non sovrascrive ---


def test_il_rapporto_dei_controlli_non_sovrascrive(tmp_path, monkeypatch):
    cultura, sport = coppia(1)
    monkeypatch.setattr(gc, "leggi_documenti", lambda: [cultura, sport])
    monkeypatch.setattr(gc, "CARTELLA", tmp_path)
    monkeypatch.setattr(gc, "FILE_CONTESTI", tmp_path / "contesti.jsonl")
    for d in (cultura, sport):
        gc.aggiungi(gc.FILE_CONTESTI, salvato(contesto(), d))
    vecchio = tmp_path / "controllo_contesti.txt"
    vecchio.write_text("rapporto di prima\n", encoding="utf-8")
    assert gc.main(["--controlla"]) == 0
    assert gc.main(["--controlla"]) == 0
    scritti = sorted(tmp_path.glob("controllo_contesti_*.txt"))
    assert len(scritti) == 2
    assert vecchio.read_text(encoding="utf-8") == "rapporto di prima\n"
    assert all(
        "Controlli sui contesti generati" in p.read_text("utf-8") for p in scritti
    )
    primo = gc.percorso_del_rapporto(False, "2026-11-21_120000")
    assert primo.name == "controllo_contesti_2026-11-21_120000.txt"
    primo.write_text("x", encoding="utf-8")
    assert gc.percorso_del_rapporto(False, "2026-11-21_120000").name == (
        "controllo_contesti_2026-11-21_120000_2.txt"
    )
    assert gc.percorso_del_rapporto(True, "2026-11-21_120000").name == (
        "controllo_contesti_prova_2026-11-21_120000.txt"
    )


# --- f. test dei segni al posto della soglia fissa ---


def test_niente_soglia_fissa_vale_il_test_dei_segni():
    assert not hasattr(mr, "RUMORE")
    # +4 senza nessun perso: oltre la vecchia soglia di 3, ma p = 0,125
    assert mr.nota_dei_segni(4, 0) == "p = 0,125; entro il rumore"
    assert mr.nota_dei_segni(6, 0) == "p = 0,031"
    assert mr.differenza(26, 30) == "+4"
