"""--bando, --solo-primo e cosa e' arrivato per ogni file (passo 19, 19b).

Siti finti e PDF scritti nel test: nessuna rete, nessuna attesa.
"""

import pytest

import scripts.ingestione.elenco_pdf_bandi as script
from src.estrazione import lettore_siti as ls
from tests.test_elenco_pdf_bandi import (
    AVVISO,
    BANDI,
    NON_AVVISO,
    RT,
    prepara,
    sito,
    stati,
)
from tests.test_lettore_siti import ROBOTS, SITO, Errore, lettore

# --- --bando ---


def test_scegli_un_bando():
    assert script.scegli_bandi(BANDI, ["bando-b"]) == [BANDI[1]]
    assert script.scegli_bandi(BANDI, []) == BANDI


def test_bando_non_della_prova_e_un_errore():
    with pytest.raises(script.ErroreElenco, match="non della prova: altro"):
        script.scegli_bandi(BANDI, ["bando-a", "altro"])


def test_main_con_bando_tocca_solo_quel_bando(tmp_path):
    lettore_, rete = prepara(tmp_path)
    assert (
        script.main(["--pagine", "--bando", "bando-a"], lettore=lettore_, bandi=BANDI)
        == 0
    )
    assert f"{RT}/-/bando-a" in rete.url_chiamati()
    assert f"{RT}/-/bando-b" not in rete.url_chiamati()
    assert not [u for u in rete.url_chiamati() if "mit-prova" in u]


def test_main_con_bando_estraneo_esce_con_errore(tmp_path, capsys):
    lettore_, rete = prepara(tmp_path)
    assert (
        script.main(["--file", "--bando", "altro"], lettore=lettore_, bandi=BANDI) == 1
    )
    assert "non della prova" in capsys.readouterr().err
    assert rete.chiamate == []


# --- --solo-primo ---


def test_solo_primo_si_ferma_se_il_primo_non_e_un_avviso(tmp_path):
    # l'avviso del bando non ha le sezioni: senza --solo-primo si passerebbe
    # agli allegati
    risposte = {**sito(), f"{RT}/doc/avviso.pdf": NON_AVVISO}
    lettore_, rete = prepara(tmp_path, risposte)
    script.fase_pagine(lettore_, BANDI[:1], tmp_path, stampa=lambda *_: None)
    righe = script.fase_file(
        lettore_, BANDI[:1], tmp_path, stampa=lambda *_: None, solo_primo=True
    )
    assert stati(righe, "bando-a")["avviso.pdf"] == script.SCARICATO
    assert stati(righe, "bando-a")["allegato-b.pdf"] == script.NON_TENTATO
    assert stati(righe, "bando-a")["allegato-c.pdf"] == script.NON_TENTATO
    assert [u for u in rete.url_chiamati() if u.endswith(".pdf")] == [
        f"{RT}/doc/avviso.pdf"
    ]


def test_solo_primo_si_ferma_se_il_primo_non_e_un_pdf(tmp_path):
    risposte = {**sito(), f"{RT}/doc/avviso.pdf": b"PK\x03\x04 documento odt"}
    lettore_, rete = prepara(tmp_path, risposte)
    script.fase_pagine(lettore_, BANDI[:1], tmp_path, stampa=lambda *_: None)
    righe = script.fase_file(
        lettore_, BANDI[:1], tmp_path, stampa=lambda *_: None, solo_primo=True
    )
    assert stati(righe, "bando-a")["avviso.pdf"] == ls.NON_PDF
    assert [u for u in rete.url_chiamati() if u.endswith(".pdf")] == [
        f"{RT}/doc/avviso.pdf"
    ]


def test_main_passa_solo_primo(tmp_path):
    lettore_, rete = prepara(tmp_path, {**sito(), f"{RT}/doc/avviso.pdf": NON_AVVISO})
    script.main(["--pagine", "--bando", "bando-a"], lettore=lettore_, bandi=BANDI)
    assert (
        script.main(
            ["--file", "--bando", "bando-a", "--solo-primo"],
            lettore=lettore_,
            bandi=BANDI,
        )
        == 0
    )
    assert [u for u in rete.url_chiamati() if u.endswith(".pdf")] == [
        f"{RT}/doc/avviso.pdf"
    ]


# --- cosa e' arrivato ---


def test_esito_con_content_type_e_primi_byte(tmp_path):
    let, _, _ = lettore(
        tmp_path,
        {
            ROBOTS: Errore(404),
            f"{SITO}/a.pdf": (AVVISO, {"Content-Type": "application/pdf"}),
        },
    )
    esito = let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file", solo_pdf=True)
    assert esito.tipo_contenuto == "application/pdf"
    assert esito.inizio.startswith(b"%PDF-1.4")
    assert len(esito.inizio) == ls.INIZIO_BYTE


def test_non_pdf_dice_cosa_e_arrivato(tmp_path):
    let, _, _ = lettore(
        tmp_path,
        {
            ROBOTS: Errore(404),
            f"{SITO}/a.pdf": (b"<html>pagina</html>", {"Content-Type": "text/html"}),
        },
    )
    esito = let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file", solo_pdf=True)
    assert esito.stato == ls.NON_PDF
    assert esito.tipo_contenuto == "text/html"
    assert esito.inizio == b"<html>pagina</ht"


def test_la_fase_file_stampa_una_riga_per_file(tmp_path):
    lettore_, _ = prepara(tmp_path)
    stampato: list[str] = []
    script.fase_pagine(lettore_, BANDI[:1], tmp_path, stampa=lambda *_: None)
    script.fase_file(lettore_, BANDI[:1], tmp_path, stampa=stampato.append)
    righe = [r for r in stampato if r.startswith("  bando-a #")]
    assert righe[0].startswith("  bando-a #1: ok, HTTP 200, Content-Type ?, ")
    assert "primi byte b'%PDF-1.4" in righe[0]
