"""Premesse dei decreti e scelta dei file (scripts/ingestione/carica_avvisi.py).

Se nel testo di un file c'è una riga con la sola parola DECRETA, il testo
che la precede non si carica. Pagine e frasi inventate.
"""

import pytest

import scripts.ingestione.carica_avvisi as script
from tests.test_carica_avvisi import (  # noqa: F401
    PARAGRAFO,
    Tokenizer,
    db,
    riga_registro,
)

VISTO = "VISTO il decreto legislativo di prova;\nVISTA la legge di prova;\n"
ARTICOLO = "Art. 1\n(Finalità)\n1. Il presente decreto disciplina il fondo di prova.\n"


def test_riga_sola_scatta():
    pagine = [VISTO, "VISTO ancora;\n  DECRETA  \n" + ARTICOLO]
    tenute, premesse = script.togli_premesse(pagine)
    assert tenute == ["", ARTICOLO]
    assert premesse == script.Premesse(
        2, len(VISTO) + len("VISTO ancora;\n  DECRETA  \n")
    )


def test_lettere_separate_da_spazi():
    tenute, premesse = script.togli_premesse([VISTO + "D E C R E T A\n" + ARTICOLO])
    assert tenute == [ARTICOLO] and premesse.pagina == 1


@pytest.mark.parametrize(
    "riga",
    [
        "Il Ministro decreta che il fondo sia ripartito",
        "Il Ministro DECRETA quanto segue",
        "DECRETA:",
        "decreta",
    ],
)
def test_non_scatta(riga):
    pagine = [VISTO + riga + "\n" + ARTICOLO]
    assert script.togli_premesse(pagine) == (pagine, None)


def test_file_senza_la_riga_resta_identico():
    pagine = [VISTO, ARTICOLO, "Roma, 1 gennaio 2026\n"]
    tenute, premesse = script.togli_premesse(pagine)
    assert tenute is not pagine and tenute == pagine and premesse is None


def test_vale_la_prima_occorrenza():
    pagine = [VISTO + "DECRETA\n" + ARTICOLO + "DECRETA\nArt. 2\n"]
    tenute, _ = script.togli_premesse(pagine)
    assert tenute == [ARTICOLO + "DECRETA\nArt. 2\n"]


def test_il_primo_frammento_comincia_dopo_decreta(db):  # noqa: F811
    pagine = [
        VISTO + PARAGRAFO * 3,
        "Altre premesse.\nDECRETA\n" + ARTICOLO + PARAGRAFO * 2,
    ]
    esito = script.frammenti_del_file(riga_registro(), pagine, db, Tokenizer())
    assert esito.frammenti[0].page_content.startswith("Art. 1")
    assert esito.frammenti[0].metadata["page"] == 2
    assert all("VISTO" not in d.page_content for d in esito.frammenti)
    assert esito.premesse.pagina == 2
    assert (1, "premesse") in esito.saltate
    assert any("premesse tolte" in r for r in script.rapporto_file(esito))


def test_rapporto_senza_premesse(db):  # noqa: F811
    esito = script.frammenti_del_file(riga_registro(), [PARAGRAFO * 3], db, Tokenizer())
    assert esito.premesse is None
    assert any(
        "premesse: nessuna riga DECRETA" in r for r in script.rapporto_file(esito)
    )


# --- scelta dei file con --solo ---


def test_solo_un_file():
    righe = [
        riga_registro(sha256="a" * 64, nome_file="a.pdf"),
        riga_registro(sha256="b" * 64, nome_file="b.pdf"),
    ]
    assert script.scegli_righe(righe, []) == righe
    assert script.scegli_righe(righe, ["b" * 64]) == righe[1:]
    assert script.scegli_righe(righe, ["a.pdf"]) == righe[:1]
    with pytest.raises(script.ErroreCaricamento, match="non nel registro"):
        script.scegli_righe(righe, ["c.pdf"])
    assert script.leggi_argomenti(["--solo", "a.pdf"]).solo == ["a.pdf"]
    assert script.leggi_argomenti([]).solo == []
