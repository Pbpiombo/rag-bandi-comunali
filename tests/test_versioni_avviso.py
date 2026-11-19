"""Classi e versioni dei testi dei bandi (passo 19, decisioni del 19/11/2026).

Sugli estratti delle pagine della Regione salvate il 19/11/2026
(tests/pagine/regione-documenti-*.html) e su etichette scritte nel test.
Nessuna rete.
"""

from datetime import date

import pytest

from src.estrazione import pdf_bando as pb
from tests.test_documenti_regione import per_etichetta, righe

# --- consolidato: parole di una versione solo in un testo ---


def test_allegato_aggiornato_resta_allegato():
    # caso reale: "Progetti ammissibili ... Allegato 1A aggiornato"
    riga = next(
        r for r in righe("pmi-50mila") if "Allegato 1A aggiornato" in r["etichetta"]
    )
    assert riga["classe"] == pb.ALLEGATO


@pytest.mark.parametrize(
    ("estratto", "etichetta"),
    [
        ("punti-digitale", "Avviso pubblico / Bando testo corretto definitivo"),
        ("risorse-genetiche", "testo del bando aggiornato"),
        ("pmi-50mila", "testo del bando aggiornato alle modifiche"),
    ],
)
def test_versioni_di_un_testo_sono_consolidato(estratto, etichetta):
    assert per_etichetta(estratto)[etichetta]["classe"] == pb.CONSOLIDATO


@pytest.mark.parametrize(
    ("etichetta", "attesa"),
    [
        ("Avviso definitivo", pb.CONSOLIDATO),
        ("Bando coordinato con le modifiche", pb.CONSOLIDATO),
        ("Elenco definitivo dei soggetti", pb.DA_DECIDERE),
        ("Scheda corretta", pb.ALTRO),
    ],
)
def test_parole_di_versione_senza_testo_bando_o_avviso(etichetta, attesa):
    assert pb.classifica(etichetta, "documento.pdf")[0] == attesa


# --- proroga ---


@pytest.mark.parametrize(
    "etichetta",
    [
        "Proroga del termine ultimo di presentazione delle istanze",
        "Rettifica dell'avviso",
        "Differimento dei termini",
        "Riapertura dei termini",
        "Errata corrige",
    ],
)
def test_classe_proroga(etichetta):
    assert pb.classifica(etichetta, "documento.pdf")[0] == pb.PROROGA


def test_proroga_subito_dopo_l_avviso():
    righe_ = [
        {"n": 1, "classe": pb.ALLEGATO, "motivo_classe": "", "p7m": "no"},
        {"n": 2, "classe": pb.PROROGA, "motivo_classe": "", "p7m": "no"},
        {"n": 3, "classe": pb.AVVISO, "motivo_classe": "", "p7m": "no"},
        {
            "n": 4,
            "classe": pb.ALLEGATO,
            "motivo_classe": pb.PROBABILE_AVVISO,
            "p7m": "no",
        },
    ]
    assert [r["n"] for r in pb.ordine_di_scarico(righe_)] == [3, 2, 4, 1]


# --- parole nuove ---


def test_elementi_essenziali_e_un_atto():
    assert (
        per_etichetta("punti-digitale")["elementi essenziali del bando"]["classe"]
        == pb.ATTO
    )


@pytest.mark.parametrize(
    "etichetta",
    [
        "Chiamata di progetti",
        "Invito a presentare proposte",
        "Manifestazione di interesse",
    ],
)
def test_parole_nuove_dell_avviso(etichetta):
    assert pb.classifica(etichetta, "documento.pdf")[0] == pb.AVVISO


def test_chiamata_di_progetti_reale():
    riga = per_etichetta("educazione-musicale")["Chiamata di progetti (Allegato A)"]
    assert riga["classe"] == pb.AVVISO


def test_formulario_e_modulistica():
    assert (
        per_etichetta("risorse-genetiche")["nuovo Formulario per Piano progettuale"][
            "classe"
        ]
        == pb.MODULISTICA
    )
    assert (
        per_etichetta("punti-digitale")["Istruzioni compilazione Formulario progetto"][
            "classe"
        ]
        == pb.MODULISTICA
    )


# --- versioni ---


def test_data_dal_nome_del_file():
    atto = {
        "url_file": "https://x.it/bancadati/atti/Contenuto.xml?id=1&nomeFile=Decreto+n.25205+del+16-11-2026"
    }
    assert pb.data_del_documento(atto) == date(2026, 11, 16)
    sottolineato = {
        "url_file": "https://x.it/a/Decreto_n.9505_del_30-04-2026-Allegato-1.pdf"
    }
    assert pb.data_del_documento(sottolineato) == date(2026, 4, 30)
    senza = {"url_file": "https://x.it/documents/d/guest/testo-coordinato-bando-pdf"}
    assert pb.data_del_documento(senza) is None


def test_vince_il_decreto_piu_recente_punti_digitale():
    superate, problema = pb.versioni(righe("punti-digitale"))
    assert problema is None
    assert [r["etichetta"] for r in superate] == [
        "Avviso pubblico / Bando testo con la prima correzione"
    ]


def test_vince_il_consolidato_piu_recente_pmi():
    superate, problema = pb.versioni(righe("pmi-50mila"))
    assert problema is None
    assert [r["etichetta"] for r in superate] == ["testo del bando"]


@pytest.mark.parametrize(
    "estratto",
    ["parcheggi", "dati", "risorse-genetiche", "pmi-eu-blending", "apistici"],
)
def test_una_sola_versione_nulla_di_superato(estratto):
    assert pb.versioni(righe(estratto)) == ([], None)


def riga_versione(n, classe, url):
    return {
        "n": n,
        "classe": classe,
        "etichetta": f"v{n}",
        "url_file": url,
        "p7m": "no",
    }


def test_data_non_ricavabile_non_si_sceglie():
    righe_ = [
        riga_versione(1, pb.AVVISO, "https://x.it/a/Decreto_del_01-02-2026.pdf"),
        riga_versione(
            2, pb.CONSOLIDATO, "https://x.it/documents/d/testo-coordinato-pdf"
        ),
    ]
    superate, problema = pb.versioni(righe_)
    assert superate == []
    assert problema.startswith("data non ricavabile")
    assert "2 (v2)" in problema


def test_stessa_data_non_si_sceglie():
    righe_ = [
        riga_versione(1, pb.AVVISO, "https://x.it/a/Decreto_del_01-02-2026-All-A.pdf"),
        riga_versione(
            2, pb.CONSOLIDATO, "https://x.it/a/Decreto_del_01-02-2026-All-1.pdf"
        ),
    ]
    superate, problema = pb.versioni(righe_)
    assert superate == []
    assert problema.startswith("stessa data (2026-02-01)")


def test_p7m_e_modulistica_non_sono_versioni():
    righe_ = [
        riga_versione(1, pb.AVVISO, "https://x.it/a/avviso.pdf"),
        {**riga_versione(2, pb.AVVISO, "https://x.it/a/avviso.pdf.p7m"), "p7m": "sì"},
    ]
    assert pb.versioni(righe_) == ([], None)
