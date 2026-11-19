"""Soglie di e_avviso per classe, "avviso in piu' parti" e --senza-rete.

Decisioni del 19/11/2026 sul passo 19. Siti finti e PDF scritti nel test:
nessuna rete, nessuna attesa. Con --senza-rete ogni richiesta fa fallire
il test.
"""

import pytest

import scripts.ingestione.elenco_pdf_bandi as script
from src.estrazione import lettore_siti as ls
from src.estrazione import pdf_bando as pb
from tests.test_elenco_pdf_bandi import AVVISO, BANDI, RT, prepara, sito, stati
from tests.test_elenco_versioni import AVVISO_QUATTRO


def sezioni(quante: int) -> pb.Sezioni:
    nomi = list(pb.SEZIONI)[:quante]
    return pb.Sezioni(pagine=5, trovate={n: [1] for n in nomi}, contrari={})


# --- soglia per classe ---


@pytest.mark.parametrize(
    ("classe", "quante", "giudizio", "atteso"),
    [
        (pb.AVVISO, 3, pb.LEGGIBILE, True),
        (pb.CONSOLIDATO, 3, pb.LEGGIBILE, True),
        (pb.AVVISO, 3, pb.DA_RIVEDERE, True),
        (None, 3, None, True),
        (pb.ALLEGATO, 3, pb.LEGGIBILE, False),
        (pb.ALLEGATO, 4, pb.LEGGIBILE, True),
        (pb.ALTRO, 3, pb.DA_RIVEDERE, False),
        (pb.ALTRO, 4, pb.DA_RIVEDERE, False),
        (pb.ALTRO, 5, pb.LEGGIBILE, True),
    ],
)
def test_soglia_per_classe(classe, quante, giudizio, atteso):
    assert pb.e_avviso(sezioni(quante), classe, giudizio)[0] is atteso


def test_nota_della_soglia_per_classe():
    _, nota = pb.e_avviso(sezioni(3), pb.ALLEGATO, pb.LEGGIBILE)
    assert nota == "3 sezioni su 5: ne servono 4 per la classe allegato"
    _, nota = pb.e_avviso(sezioni(4), pb.ALTRO, pb.DA_RIVEDERE)
    assert nota.startswith("testo da rivedere")
    assert pb.SEZIONI_MINIME_ALTRE == 4


# --- avviso in piu' parti solo senza link di classe avviso ---


def test_allegato_richiamato_con_le_sezioni_non_fa_piu_parti(tmp_path):
    # l'avviso richiama l'Allegato B per i codici ATECO; l'allegato ha 4
    # sezioni: prima del 19/11/2026 erano "avviso in piu' parti"
    risposte = {**sito(), f"{RT}/doc/allegato-b.pdf": AVVISO_QUATTRO}
    lettore, _ = prepara(tmp_path, risposte)
    script.fase_pagine(lettore, BANDI[:1], tmp_path, stampa=lambda *_: None)
    righe = script.fase_file(lettore, BANDI[:1], tmp_path, stampa=lambda *_: None)
    assert stati(righe, "bando-a")["allegato-b.pdf"] == script.SCARICATO
    assert not [r for r in righe if script.AVVISO_IN_PIU_PARTI in r["sezioni"]]


# --- --senza-rete ---


def vietata(url, _intestazioni):
    raise AssertionError(f"richiesta con --senza-rete: {url}")


def test_lettore_senza_rete_non_chiede_niente(tmp_path):
    (tmp_path / "presente.pdf").write_bytes(AVVISO)
    lettore = ls.Lettore(tmp_path, apri=vietata, dormi=lambda _s: None, senza_rete=True)
    presente = lettore.prendi("https://x.it/a.pdf", tmp_path / "presente.pdf", "file")
    assert presente.stato == ls.GIA_PRESENTE
    mancante = lettore.prendi("https://x.it/b.pdf", tmp_path / "mancante.pdf", "file")
    assert mancante.stato == ls.NON_TENTATO_SENZA_RETE
    assert not (tmp_path / "mancante.pdf").exists()


def test_lettore_senza_rete_ferma_ogni_richiesta(tmp_path):
    lettore = ls.Lettore(tmp_path, apri=vietata, dormi=lambda _s: None, senza_rete=True)
    with pytest.raises(ls.SenzaRete):
        lettore.regole("https://x.it/pagina")


def test_ricomposizione_senza_rete(tmp_path):
    lettore, rete = prepara(tmp_path)
    script.fase_pagine(lettore, BANDI[:2], tmp_path, stampa=lambda *_: None)
    script.fase_file(lettore, BANDI[:2], tmp_path, stampa=lambda *_: None)
    # un file sparisce dalla cartella
    tolto = next(script.cartella_file(tmp_path, "bando-b").glob("*.pdf"))
    tolto.unlink()

    senza = ls.Lettore(tmp_path, apri=vietata, dormi=lambda _s: None, senza_rete=True)
    righe = script.fase_file(senza, BANDI[:2], tmp_path, stampa=lambda *_: None)
    valori = list(stati(righe, "bando-b").values())
    # 3 file restano; il tolto e quelli oltre il vecchio tetto (ora non
    # piu' raggiunto) non si chiedono
    assert valori.count(ls.GIA_PRESENTE) == 3
    assert valori.count(ls.NON_TENTATO_SENZA_RETE) == 3
    assert stati(righe, "bando-a")["avviso.pdf"] == ls.GIA_PRESENTE
    assert (tmp_path / "elenco.csv").exists()


def test_main_senza_rete(tmp_path):
    lettore, rete = prepara(tmp_path)
    script.fase_pagine(lettore, BANDI[:1], tmp_path, stampa=lambda *_: None)
    chiamate_prima = len(rete.chiamate)
    lettore.cartella = tmp_path
    lettore._apri = vietata
    assert (
        script.main(["--file", "--senza-rete"], lettore=lettore, bandi=BANDI[:1]) == 0
    )
    assert len(rete.chiamate) == chiamate_prima


def test_senza_rete_vale_solo_per_i_file(tmp_path, capsys):
    lettore = ls.Lettore(tmp_path, apri=vietata, dormi=lambda _s: None)
    assert script.main(["--pagine", "--senza-rete"], lettore=lettore, bandi=BANDI) == 1
    assert "solo con --file" in capsys.readouterr().err
