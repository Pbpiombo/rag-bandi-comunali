"""Fase dei file: proroghe, versioni, consolidato, avviso in piu' parti.

Decisioni del 19/11/2026 sul passo 19. Siti finti e PDF scritti nel test,
come in tests/test_elenco_pdf_bandi.py: nessuna rete, nessuna attesa.
"""

import pytest

import scripts.ingestione.elenco_pdf_bandi as script
from tests.test_elenco_pdf_bandi import (
    AVVISO,
    NON_AVVISO,
    RT,
    TESTO,
    VIETA_PDF,
    prepara,
    sito,
    stati,
)
from tests.test_pdf_bando import pdf_minimo

ATTI = "https://www301.regione-prova.it/bancadati/atti/Contenuto.xml"
BANDO = [("bando-a", f"{RT}/-/bando-a")]


def con_pagina(html: str, **altri) -> dict:
    return {
        **sito(),
        f"{RT}/-/bando-a": html.encode(),
        "https://www301.regione-prova.it/robots.txt": b"User-agent: *\nDisallow:\n",
        **altri,
    }


def esegui(tmp_path, risposte, bandi=BANDO):
    lettore, rete = prepara(tmp_path, risposte)
    stampato: list[str] = []
    script.fase_pagine(lettore, bandi, tmp_path, stampa=stampato.append)
    righe = script.fase_file(lettore, bandi, tmp_path, stampa=stampato.append)
    return righe, rete, "\n".join(stampato)


# --- proroga ---

PAGINA_PROROGA = f"""
<a href="{RT}/doc/avviso.pdf">Avviso pubblico</a>
<a href="{RT}/doc/proroga.pdf">Proroga dei termini di presentazione</a>
<a href="{RT}/doc/allegato-c.pdf">Allegato C - Relazione tecnica</a>
"""


def test_proroga_scaricata_dopo_l_avviso(tmp_path):
    risposte = con_pagina(PAGINA_PROROGA, **{f"{RT}/doc/proroga.pdf": NON_AVVISO})
    righe, rete, _ = esegui(tmp_path, risposte)
    assert stati(righe, "bando-a") == {
        "avviso.pdf": script.SCARICATO,
        "proroga.pdf": script.SCARICATO,
        "allegato-c.pdf": script.NON_NECESSARIO,
    }
    chiamati = rete.url_chiamati()
    assert chiamati.index(f"{RT}/doc/avviso.pdf") < chiamati.index(
        f"{RT}/doc/proroga.pdf"
    )


def test_proroga_conta_nel_tetto(tmp_path, monkeypatch):
    monkeypatch.setattr(script, "FILE_PER_BANDO", 1)
    risposte = con_pagina(PAGINA_PROROGA, **{f"{RT}/doc/proroga.pdf": NON_AVVISO})
    righe, rete, _ = esegui(tmp_path, risposte)
    assert stati(righe, "bando-a")["proroga.pdf"] == script.OLTRE_IL_TETTO
    assert f"{RT}/doc/proroga.pdf" not in rete.url_chiamati()


def test_proroga_vietata_si_scarica_con_l_eccezione(tmp_path):
    risposte = con_pagina(
        PAGINA_PROROGA,
        **{f"{RT}/robots.txt": VIETA_PDF, f"{RT}/doc/proroga.pdf": NON_AVVISO},
    )
    righe, _, _ = esegui(tmp_path, risposte)
    assert stati(righe, "bando-a")["proroga.pdf"] == script.SCARICATO_ECCEZIONE


# --- versioni ---

PAGINA_VERSIONI = f"""
<a href="{ATTI}?id=1&amp;nomeFile=Decreto+n.24443+del+06-11-2026-+Allegato+A">Avviso pubblico / Bando testo con la prima correzione</a>
<a href="{ATTI}?id=2&amp;nomeFile=Decreto+n.25205+del+16-11-2026-+Allegato+A">Avviso pubblico / Bando testo corretto definitivo</a>
"""


def test_versione_superata_non_si_scarica(tmp_path):
    risposte = con_pagina(
        PAGINA_VERSIONI,
        **{f"{ATTI}?id=2&nomeFile=Decreto+n.25205+del+16-11-2026-+Allegato+A": AVVISO},
    )
    righe, rete, stampato = esegui(tmp_path, risposte)
    stato = {r["etichetta"]: r["stato_scarico"] for r in righe}
    assert (
        stato["Avviso pubblico / Bando testo con la prima correzione"]
        == script.VERSIONE_SUPERATA
    )
    assert (
        stato["Avviso pubblico / Bando testo corretto definitivo"] == script.SCARICATO
    )
    assert not [u for u in rete.url_chiamati() if "id=1" in u]
    assert f"escluso: 1 ({script.VERSIONE_SUPERATA})" in stampato


def test_versioni_senza_data_si_ferma(tmp_path, capsys):
    pagina = f"""
    <a href="{RT}/doc/avviso.pdf">Avviso pubblico</a>
    <a href="{RT}/documents/d/guest/testo-coordinato-bando-pdf">testo del bando aggiornato</a>
    """
    lettore, rete = prepara(tmp_path, con_pagina(pagina))
    assert script.main(["--pagine"], lettore=lettore, bandi=BANDO) == 0
    assert script.main(["--file"], lettore=lettore, bandi=BANDO) == 1
    errore = capsys.readouterr().err
    assert "bando-a: data non ricavabile" in errore
    assert not [u for u in rete.url_chiamati() if u.endswith((".pdf", "-pdf"))]


# --- consolidato ---


def test_avviso_sostituito_dal_consolidato_a_mano(tmp_path):
    pagina = f'<a href="{RT}/doc/avviso.pdf">Avviso pubblico</a>'
    lettore, rete = prepara(tmp_path, con_pagina(pagina))
    script.fase_pagine(lettore, BANDO, tmp_path, stampa=lambda *_: None)
    cartella = script.cartella_file(tmp_path, "bando-a")
    cartella.mkdir(parents=True)
    (cartella / "testo-coordinato-bando.pdf").write_bytes(AVVISO)

    righe = script.fase_file(lettore, BANDO, tmp_path, stampa=lambda *_: None)
    assert stati(righe, "bando-a")["avviso.pdf"] == script.SOSTITUITO
    assert f"{RT}/doc/avviso.pdf" not in rete.url_chiamati()


def test_dopo_un_avviso_non_consolidato_resta_non_necessario(tmp_path):
    pagina = f'<a href="{RT}/doc/avviso.pdf">Avviso pubblico</a>'
    lettore, _ = prepara(tmp_path, con_pagina(pagina))
    script.fase_pagine(lettore, BANDO, tmp_path, stampa=lambda *_: None)
    cartella = script.cartella_file(tmp_path, "bando-a")
    cartella.mkdir(parents=True)
    (cartella / "avviso-messo-a-mano.pdf").write_bytes(AVVISO)

    righe = script.fase_file(lettore, BANDO, tmp_path, stampa=lambda *_: None)
    assert stati(righe, "bando-a")["avviso.pdf"] == script.NON_NECESSARIO


# --- avviso in piu' parti ---

PAGINA_PARTI = f"""
<a href="{ATTI}?id=10&amp;nomeFile=Decreto+n.14025+del+18-06-2026">Testo Atto</a>
<a href="{ATTI}?id=11&amp;nomeFile=Decreto+n.14025+del+18-06-2026-+Allegato+A1">Allegato A1 - Azione B1. Disposizioni</a>
<a href="{ATTI}?id=13&amp;nomeFile=Decreto+n.14025+del+18-06-2026-+Allegato+A3">Allegato A3 - Azione B3. Disposizioni</a>
"""


# Un allegato vale come avviso con 4 sezioni (soglia del 19/11/2026):
# beneficiari, spese ammissibili, modalita' di presentazione e criteri
AVVISO_QUATTRO = pdf_minimo(
    [
        ["REGIONE DI PROVA", "Disposizioni per l'azione", TESTO, TESTO],
        ["Art. 3 Soggetti beneficiari", TESTO],
        ["Art. 5 Spese ammissibili", "Art. 7 Presentazione della domanda", TESTO],
        ["Art. 8 Criteri di valutazione", TESTO],
    ]
)


def url_atto(numero: int, nome: str) -> str:
    return f"{ATTI}?id={numero}&nomeFile={nome}"


def test_avviso_in_piu_parti(tmp_path):
    risposte = con_pagina(
        PAGINA_PARTI,
        **{
            url_atto(11, "Decreto+n.14025+del+18-06-2026-+Allegato+A1"): AVVISO_QUATTRO,
            url_atto(13, "Decreto+n.14025+del+18-06-2026-+Allegato+A3"): AVVISO_QUATTRO,
        },
    )
    righe, rete, _ = esegui(tmp_path, risposte)
    parti = [r for r in righe if script.AVVISO_IN_PIU_PARTI in r["sezioni"]]
    assert [r["etichetta"] for r in parti] == [
        "Allegato A1 - Azione B1. Disposizioni",
        "Allegato A3 - Azione B3. Disposizioni",
    ]
    stato = {r["etichetta"]: r["stato_scarico"] for r in righe}
    assert stato["Testo Atto"] == script.NON_NECESSARIO
    assert not [u for u in rete.url_chiamati() if "id=10" in u]


def test_un_solo_allegato_con_le_sezioni_non_e_in_piu_parti(tmp_path):
    risposte = con_pagina(
        PAGINA_PARTI,
        **{
            url_atto(11, "Decreto+n.14025+del+18-06-2026-+Allegato+A1"): AVVISO_QUATTRO,
            url_atto(13, "Decreto+n.14025+del+18-06-2026-+Allegato+A3"): NON_AVVISO,
        },
    )
    righe, _, _ = esegui(tmp_path, risposte)
    assert not [r for r in righe if script.AVVISO_IN_PIU_PARTI in r["sezioni"]]


@pytest.mark.parametrize("classe", [script.pb.PROROGA])
def test_proroga_nelle_classi_dell_eccezione(classe):
    assert classe in script.CLASSI_ECCEZIONE
