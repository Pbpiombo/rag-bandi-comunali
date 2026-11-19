"""Test dello script dell'elenco dei PDF (passo 19, compito 19b).

Siti finti (ReteFinta di tests/test_lettore_siti.py) e PDF scritti nel
test (pdf_minimo di tests/test_pdf_bando.py): nessuna rete, nessuna attesa.
"""

import csv

import pytest

import scripts.ingestione.elenco_pdf_bandi as script
from src.estrazione import pdf_bando as pb
from src.estrazione.lettore_siti import Lettore
from tests.test_lettore_siti import Errore, ReteFinta
from tests.test_pdf_bando import pdf_minimo

RT = "https://www.regione-prova.it"
MIT = "https://www.mit-prova.it"
FILE_MIT = "https://files.mit-prova.it"
LIBERO = b"User-agent: *\nDisallow:\n"

TESTO = (
    "Il presente articolo disciplina in modo dettagliato le condizioni, i termini "
    "e le procedure previste dall'avviso, secondo la normativa vigente"
)
AVVISO = pdf_minimo(
    [
        ["REGIONE DI PROVA", "Avviso pubblico 2026", TESTO, TESTO],
        [
            "Art. 3 Soggetti beneficiari",
            "Imprese con codici ATECO di cui all'Allegato B",
            TESTO,
        ],
        [
            "Art. 5 Spese ammissibili",
            "Art. 7 Modalita' di presentazione della domanda",
            TESTO,
        ],
    ]
)
NON_AVVISO = pdf_minimo(
    [["Relazione illustrativa", "Testo senza sezioni di un avviso"]]
)

PAGINA_A = f"""
<a href="{RT}/doc/avviso.pdf">Avviso pubblico</a>
<a href="{RT}/doc/allegato-b.pdf">Allegato B - Codici ATECO</a>
<a href="{RT}/doc/allegato-c.pdf">Allegato C - Relazione tecnica</a>
<a href="{RT}/doc/modulo.pdf">Modulo di domanda</a>
<a href="{RT}/doc/firmato.pdf.p7m">Decreto firmato</a>
"""
PAGINA_B = "".join(
    f'<a href="{RT}/doc/b{n}.pdf">Documento {n}</a>' for n in range(1, 7)
)
NOTIZIA = f"""
<a href="{MIT}/news/notizia">Notizia</a>
<a href="{MIT}/documentazione/avviso-2026">Leggi l'avviso pubblico</a>
"""
PAGINA_AVVISO_MIT = f'<a href="{FILE_MIT}/avviso-mit.pdf">Avviso pubblico</a>'

BANDI = [
    ("bando-a", f"{RT}/-/bando-a"),
    ("bando-b", f"{RT}/-/bando-b"),
    ("fondo-strade-piccoli-comuni-2026", f"{MIT}/news/notizia"),
]


def sito() -> dict:
    return {
        f"{RT}/robots.txt": LIBERO,
        f"{MIT}/robots.txt": LIBERO,
        f"{FILE_MIT}/robots.txt": Errore(404),
        f"{RT}/-/bando-a": PAGINA_A.encode(),
        f"{RT}/-/bando-b": PAGINA_B.encode(),
        f"{MIT}/news/notizia": NOTIZIA.encode(),
        f"{MIT}/documentazione/avviso-2026": PAGINA_AVVISO_MIT.encode(),
        f"{RT}/doc/avviso.pdf": AVVISO,
        f"{RT}/doc/allegato-b.pdf": NON_AVVISO,
        f"{RT}/doc/allegato-c.pdf": NON_AVVISO,
        **{f"{RT}/doc/b{n}.pdf": NON_AVVISO for n in range(1, 7)},
        f"{FILE_MIT}/avviso-mit.pdf": AVVISO,
    }


def prepara(tmp_path, risposte=None, **opzioni):
    rete = ReteFinta(risposte or sito())
    lettore = Lettore(
        tmp_path, apri=rete, dormi=lambda _s: None, orologio=lambda: 0.0, **opzioni
    )
    return lettore, rete


def stati(righe, id_bando) -> dict[str, str]:
    return {
        (r["url_file"].rsplit("/", 1)[-1] or r["etichetta"]): r["stato_scarico"]
        for r in righe
        if r["id_bando"] == id_bando
    }


def esegui_fino_ai_file(tmp_path, bandi=BANDI, risposte=None):
    lettore, rete = prepara(tmp_path, risposte)
    righe_stampate: list[str] = []
    script.fase_pagine(lettore, bandi, tmp_path, stampa=righe_stampate.append)
    righe = script.fase_file(lettore, bandi, tmp_path, stampa=righe_stampate.append)
    return righe, rete, "\n".join(righe_stampate)


# --- fase robots ---


def test_fase_robots_stampa_il_testo_e_i_permessi(tmp_path):
    lettore, _ = prepara(tmp_path)
    stampato: list[str] = []
    assert script.fase_robots(lettore, BANDI, stampa=stampato.append) is True
    testo = "\n".join(stampato)
    assert "User-agent: *\nDisallow:" in testo
    assert testo.count("consentita:") == 3


def test_fase_robots_si_ferma_su_una_pagina_vietata(tmp_path):
    risposte = {**sito(), f"{RT}/robots.txt": b"User-agent: *\nDisallow: /-/bando-b\n"}
    lettore, _ = prepara(tmp_path, risposte)
    stampato: list[str] = []
    assert script.fase_robots(lettore, BANDI, stampa=stampato.append) is False
    assert any("VIETATA: bando-b" in r for r in stampato)


def test_fase_robots_si_ferma_su_un_rifiuto(tmp_path):
    lettore, _ = prepara(tmp_path, {**sito(), f"{MIT}/robots.txt": Errore(403)})
    stampato: list[str] = []
    assert script.fase_robots(lettore, BANDI, stampa=stampato.append) is False
    assert any("HOST FERMATO" in r for r in stampato)


def test_fase_robots_illeggibile_indica_l_opzione(tmp_path):
    lettore, _ = prepara(tmp_path, {**sito(), f"{MIT}/robots.txt": Errore(500)})
    stampato: list[str] = []
    assert script.fase_robots(lettore, BANDI, stampa=stampato.append) is False
    assert any("--senza-robots www.mit-prova.it" in r for r in stampato)


# --- fase pagine ---


def test_notizia_seguita_di_un_passaggio(tmp_path):
    lettore, rete = prepara(tmp_path)
    stampato: list[str] = []
    script.fase_pagine(lettore, BANDI, tmp_path, stampa=stampato.append)
    assert script.file_pagina(
        tmp_path, "fondo-strade-piccoli-comuni-2026", seguita=True
    ).exists()
    assert rete.url_chiamati().count(f"{MIT}/documentazione/avviso-2026") == 1
    collegamenti = script.collegamenti_del_bando(tmp_path, *BANDI[2])
    assert [c.url for c in collegamenti] == [f"{FILE_MIT}/avviso-mit.pdf"]
    assert any(
        "host dei file da controllare" in r and "files.mit-prova.it" in r
        for r in stampato
    )


def test_notizia_con_due_candidati_non_si_segue(tmp_path):
    notizia = NOTIZIA + f'<a href="{MIT}/avvisi">Tutti gli avvisi</a>'
    lettore, rete = prepara(
        tmp_path, {**sito(), f"{MIT}/news/notizia": notizia.encode()}
    )
    stampato: list[str] = []
    script.fase_pagine(lettore, BANDI[2:], tmp_path, stampa=stampato.append)
    assert f"{MIT}/documentazione/avviso-2026" not in rete.url_chiamati()
    assert any("2 link verso un avviso, nessuno seguito" in r for r in stampato)


def test_fase_file_senza_pagina_salvata(tmp_path):
    lettore, rete = prepara(tmp_path)
    stampato: list[str] = []
    script.fase_file(lettore, BANDI[:1], tmp_path, stampa=stampato.append)
    assert rete.chiamate == []
    assert any("pagina non salvata" in r for r in stampato)


# --- fase file ---


def test_ci_si_ferma_all_avviso_piu_gli_allegati_richiamati(tmp_path):
    righe, rete, _ = esegui_fino_ai_file(tmp_path, BANDI[:1])
    assert stati(righe, "bando-a") == {
        "avviso.pdf": script.SCARICATO,
        "allegato-b.pdf": script.SCARICATO,
        "allegato-c.pdf": script.NON_NECESSARIO,
        "modulo.pdf": "modulistica",
        "firmato.pdf.p7m": "p7m",
    }
    chiamati = rete.url_chiamati()
    assert f"{RT}/doc/allegato-c.pdf" not in chiamati
    assert f"{RT}/doc/modulo.pdf" not in chiamati
    assert f"{RT}/doc/firmato.pdf.p7m" not in chiamati


def test_nessun_avviso_tetto_per_bando(tmp_path):
    righe, rete, stampato = esegui_fino_ai_file(tmp_path, BANDI[1:2])
    valori = list(stati(righe, "bando-b").values())
    assert valori.count(script.SCARICATO) == script.FILE_PER_BANDO == 4
    assert valori.count(script.OLTRE_IL_TETTO) == 2
    assert f"{RT}/doc/b5.pdf" not in rete.url_chiamati()
    assert "Nessun avviso riconosciuto: bando-b" in stampato


def test_tetto_complessivo(tmp_path, monkeypatch):
    monkeypatch.setattr(script, "FILE_IN_TUTTO", 1)
    righe, rete, _ = esegui_fino_ai_file(tmp_path, BANDI[:2])
    assert stati(righe, "bando-a")["avviso.pdf"] == script.SCARICATO
    assert stati(righe, "bando-a")["allegato-b.pdf"] == script.OLTRE_IL_TETTO
    assert set(stati(righe, "bando-b").values()) == {script.OLTRE_IL_TETTO}
    assert f"{RT}/doc/b1.pdf" not in rete.url_chiamati()


def test_notizia_avviso_su_altro_host_dopo_il_suo_robots(tmp_path):
    righe, rete, _ = esegui_fino_ai_file(tmp_path, BANDI[2:])
    chiamati = rete.url_chiamati()
    assert chiamati.index(f"{FILE_MIT}/robots.txt") < chiamati.index(
        f"{FILE_MIT}/avviso-mit.pdf"
    )
    assert stati(righe, "fondo-strade-piccoli-comuni-2026") == {
        "avviso-mit.pdf": script.SCARICATO
    }


def test_file_messo_a_mano(tmp_path):
    lettore, rete = prepara(tmp_path)
    script.fase_pagine(lettore, BANDI[:1], tmp_path, stampa=lambda *_: None)
    cartella = script.cartella_file(tmp_path, "bando-a")
    cartella.mkdir(parents=True)
    (cartella / "avviso-messo-a-mano.pdf").write_bytes(AVVISO)

    righe = script.fase_file(lettore, BANDI[:1], tmp_path, stampa=lambda *_: None)
    a_mano = [r for r in righe if r["stato_scarico"] == script.A_MANO]
    assert [r["etichetta"] for r in a_mano] == ["avviso messo a mano"]
    assert a_mano[0]["sezioni"].startswith("3 su 5")
    # l'avviso a mano basta: il link dell'avviso non si chiede, l'allegato
    # richiamato si'
    assert f"{RT}/doc/avviso.pdf" not in rete.url_chiamati()
    assert stati(righe, "bando-a")["avviso.pdf"] == script.NON_NECESSARIO
    assert stati(righe, "bando-a")["allegato-b.pdf"] == script.SCARICATO


def test_file_messo_a_mano_con_il_nome_del_link_e_gia_presente(tmp_path):
    lettore, rete = prepara(tmp_path)
    script.fase_pagine(lettore, BANDI[:1], tmp_path, stampa=lambda *_: None)
    nome = script.nome_del_file(f"{RT}/doc/avviso.pdf", "avviso.pdf")
    cartella = script.cartella_file(tmp_path, "bando-a")
    cartella.mkdir(parents=True)
    (cartella / nome).write_bytes(AVVISO)

    righe = script.fase_file(lettore, BANDI[:1], tmp_path, stampa=lambda *_: None)
    assert stati(righe, "bando-a")["avviso.pdf"] == "già presente"
    assert f"{RT}/doc/avviso.pdf" not in rete.url_chiamati()


def test_ripresa_senza_nuove_richieste(tmp_path):
    esegui_fino_ai_file(tmp_path)
    lettore, rete = prepara(tmp_path)
    script.fase_pagine(lettore, BANDI, tmp_path, stampa=lambda *_: None)
    script.fase_file(lettore, BANDI, tmp_path, stampa=lambda *_: None)
    assert rete.chiamate == []


def test_elenco_con_le_colonne_nuove(tmp_path):
    esegui_fino_ai_file(tmp_path, BANDI[:1])
    with (tmp_path / "elenco.csv").open(encoding="utf-8-sig", newline="") as f:
        righe = {r["url_file"].rsplit("/", 1)[-1]: r for r in csv.DictReader(f)}
    avviso = righe["avviso.pdf"]
    assert avviso["sezioni"].startswith("3 su 5; beneficiari p. 2")
    assert avviso["anteprima"].startswith("REGIONE DI PROVA / Avviso pubblico 2026 / ")
    assert len(avviso["anteprima"]) == pb.CARATTERI_ANTEPRIMA
    assert avviso["giudizio"] == pb.LEGGIBILE
    assert righe["allegato-b.pdf"]["sezioni"].startswith("0 su 5")
    assert all(r["decisione"] == "" for r in righe.values())
    assert righe["modulo.pdf"]["pagine"] == ""


# --- uso ---


def test_bandi_della_prova(tmp_path):
    percorso = tmp_path / "bandi.csv"
    percorso.write_text("id,url\nuno,https://a.it/1\ndue,\n", encoding="utf-8")
    assert script.bandi_della_prova(percorso, ("uno",)) == [("uno", "https://a.it/1")]
    with pytest.raises(script.ErroreElenco, match="due"):
        script.bandi_della_prova(percorso, ("uno", "due"))
    assert len(script.PRIMA_PROVA) == 12
    assert "immobili-emergenza-abitativa-2026" not in script.PRIMA_PROVA


def test_main_si_ferma_se_il_robots_di_un_file_non_si_legge(tmp_path, capsys):
    risposte = {**sito(), f"{FILE_MIT}/robots.txt": Errore(503)}
    lettore, rete = prepara(tmp_path, risposte)
    assert script.main(["--pagine"], lettore=lettore, bandi=BANDI[2:]) == 0
    assert script.main(["--file"], lettore=lettore, bandi=BANDI[2:]) == 1
    assert "--senza-robots files.mit-prova.it" in capsys.readouterr().err
    assert f"{FILE_MIT}/avviso-mit.pdf" not in rete.url_chiamati()


def test_main_senza_robots_permesso_a_mano(tmp_path):
    risposte = {**sito(), f"{FILE_MIT}/robots.txt": Errore(503)}
    lettore, rete = prepara(
        tmp_path, risposte, permetti_senza_robots={"files.mit-prova.it"}
    )
    assert script.main(["--pagine"], lettore=lettore, bandi=BANDI[2:]) == 0
    assert script.main(["--file"], lettore=lettore, bandi=BANDI[2:]) == 0
    assert f"{FILE_MIT}/avviso-mit.pdf" in rete.url_chiamati()
