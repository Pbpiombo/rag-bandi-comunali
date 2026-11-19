"""Link ai documenti nelle pagine dei bandi della Regione Toscana (passo 19).

Estratti delle 8 pagine della Regione salvate il 19/11/2026 dalla fase
--pagine di elenco_pdf_bandi (tests/pagine/regione-documenti-*.html): i
soli <a> verso documenti, nell'ordine della pagina. Nessuna rete.
"""

from pathlib import Path

import pytest

import scripts.ingestione.elenco_pdf_bandi as script
from src.estrazione import pdf_bando as pb

PAGINE = Path(__file__).parent / "pagine"
RT = "https://www.regione.toscana.it/-/"

ESTRATTI = {
    "parcheggi": (f"{RT}bando-parcheggi-2026", 2),
    "punti-digitale": (
        f"{RT}contributi-a-enti-locali-e-ets-per-punti-digitale-facile-avviso-2026",
        21,
    ),
    "dati": (
        f"{RT}contributi-agli-enti-locali-per-lo-sviluppo-di-progettualit%C3%A0-sui-dati-il-bando-2026",
        15,
    ),
    "risorse-genetiche": (
        (
            f"{RT}contributi-per-uso-e-gestione-sostenibile-delle-risorse-genetiche-agrarie-"
            "specie-erbacee-specie-legnose-da-frutto-bovini-e-ovini-autoctoni"
        ),
        8,
    ),
    "pmi-50mila": (
        (
            f"{RT}bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-commissioni-di-garanzia-"
            "su-finanziamenti-fino-50-mila-euro"
        ),
        12,
    ),
    "pmi-eu-blending": (
        (
            f"{RT}bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-costi-di-garanzia-su-"
            "finanziamenti-bancari-eu-blending"
        ),
        13,
    ),
    "apistici": (
        f"{RT}sostegno-agli-investimenti-strutturali-aziende-apistiche-azioni-b1-b3-b4-b5",
        6,
    ),
    "educazione-musicale": (
        f"{RT}sostegno-a-progetti-di-promozione-ed-educazione-musicale-di-base-2026",
        9,
    ),
}


def collegamenti(nome: str) -> list[pb.Collegamento]:
    url, _ = ESTRATTI[nome]
    html = (PAGINE / f"regione-documenti-{nome}.html").read_text(encoding="utf-8")
    return pb.link_ai_documenti(html, url)


def righe(nome: str) -> list[dict]:
    return pb.righe_elenco(nome, ESTRATTI[nome][0], collegamenti(nome))


def per_etichetta(nome: str) -> dict[str, dict]:
    return {r["etichetta"]: r for r in righe(nome)}


# --- rilevatore ---


@pytest.mark.parametrize("nome", list(ESTRATTI))
def test_documenti_trovati_in_ogni_pagina(nome):
    assert len(collegamenti(nome)) == ESTRATTI[nome][1]


def test_atto_della_banca_dati_con_nomefile_decodificato():
    atto, avviso = collegamenti("parcheggi")
    assert atto.host == "www301.regione.toscana.it"
    assert atto.nome_file == "Decreto n.18191 del 07-08-2026.pdf"
    assert avviso.nome_file == "Decreto n.18191 del 07-08-2026- Allegato A_.pdf"
    assert avviso.testo == "Allegato A Bando Parcheggi 2026"
    assert "Contenuto.xml?id=" in avviso.url
    assert avviso.p7m is False


def test_documento_del_portale_con_suffisso_pdf():
    primo = collegamenti("risorse-genetiche")[0]
    assert primo.url.endswith(
        "/documents/d/guest/testo-coordinato-bando-sra-aca-16b-pdf"
    )
    assert primo.nome_file == "testo-coordinato-bando-sra-aca-16b.pdf"
    assert primo.host == "www.regione.toscana.it"


@pytest.mark.parametrize(
    "nome", ["punti-digitale", "risorse-genetiche", "educazione-musicale"]
)
def test_moduli_docx_ods_xlsx_restano_fuori(nome):
    html = (PAGINE / f"regione-documenti-{nome}.html").read_text(encoding="utf-8")
    assert any(s in html for s in ("-docx", "-ods", "-xlsx"))
    for c in collegamenti(nome):
        assert not c.url.endswith(("-docx", "-ods", "-xlsx", ".doc", ".xls"))
        assert c.nome_file.endswith((".pdf", ".p7m"))


def test_suffisso_p7m_del_portale():
    html = '<a href="/documents/d/guest/avviso-firmato-pdf-p7m">Avviso firmato</a>'
    (c,) = pb.link_ai_documenti(html, f"{RT}bando")
    assert c.nome_file == "avviso-firmato-pdf.p7m"
    assert c.p7m is True
    assert pb.da_non_scaricare(pb.righe_elenco("x", f"{RT}bando", [c])[0]) == "p7m"


def test_lo_stesso_atto_in_http_e_https_e_uno_solo():
    # id=5512636 compare due volte in http ("testo del bando") e una in https ("Bando")
    trovati = [c for c in collegamenti("pmi-eu-blending") if "id=5512636" in c.url]
    assert len(trovati) == 1
    assert trovati[0].url.startswith("https://")
    assert trovati[0].testo == "testo del bando"


def test_atto_senza_nomefile_non_e_un_documento():
    html = '<a href="https://www301.regione.toscana.it/bancadati/atti/Contenuto.xml?id=1">Atto</a>'
    assert pb.link_ai_documenti(html, f"{RT}bando") == []


# --- classi: testo del link e nomeFile insieme ---


def test_il_testo_del_link_decide_quando_nomefile_e_generico():
    assert (
        per_etichetta("parcheggi")["Allegato A Bando Parcheggi 2026"]["classe"]
        == pb.AVVISO
    )
    assert per_etichetta("dati")["Avviso pubblico / Bando"]["classe"] == pb.AVVISO
    assert per_etichetta("dati")["Schema di domanda"]["classe"] == pb.MODULISTICA


def test_nomefile_testo_coordinato_rende_consolidato():
    riga = per_etichetta("risorse-genetiche")["testo del bando aggiornato"]
    assert riga["classe"] == pb.CONSOLIDATO


def test_testo_atto_con_nomefile_muto():
    # esempio reale: nomeFile=2024AD005000 uguale per atto e allegati
    assert pb.classifica("Testo Atto", "2024AD005000.pdf")[0] == pb.ATTO
    assert pb.classifica("Allegato 1", "2024AD005000.pdf")[0] == pb.ALLEGATO
    assert per_etichetta("apistici")["Testo Atto"]["classe"] == pb.ATTO


# --- istanza ---


@pytest.mark.parametrize(
    ("etichetta", "nome_file", "attesa"),
    [
        (
            "All. A Istanza di ammissione a contributo Cultura MC2026",
            "all-a.pdf",
            pb.MODULISTICA,
        ),
        ("Istanza di contributo", "istanza.pdf", pb.MODULISTICA),
        ("Avviso per la presentazione di istanze", "avviso.pdf", pb.AVVISO),
        ("Bando: modalità delle istanze", "documento.pdf", pb.AVVISO),
        # un'altra parola della modulistica resta modulistica
        ("Avviso - modulo di istanza", "modulo.pdf", pb.MODULISTICA),
    ],
)
def test_istanza_e_modulistica_salvo_avviso_o_bando(etichetta, nome_file, attesa):
    assert pb.classifica(etichetta, nome_file)[0] == attesa


# --- altro su un host diverso dalla pagina ---


def test_altro_su_altro_host_escluso_con_il_motivo():
    host_pagina = {"www.regione.toscana.it"}
    regolamento = next(r for r in righe("punti-digitale") if "1060" in r["etichetta"])
    assert regolamento["classe"] == pb.ALTRO
    assert regolamento["host_file"] == "politichecoesione.governo.it"
    assert script.esclusione(regolamento, host_pagina) == script.ALTRO_ALTRO_HOST
    assert regolamento not in script.da_scaricare(righe("punti-digitale"), host_pagina)


def test_altro_sullo_stesso_host_e_altre_classi_su_altro_host_restano():
    host_pagina = {"www.regione.toscana.it"}
    stesso_host = {
        "classe": pb.ALTRO,
        "host_file": "www.regione.toscana.it",
        "p7m": "no",
    }
    assert script.esclusione(stesso_host, host_pagina) is None
    # gli atti su www301 sono un altro host, ma non sono di classe altro
    atto = per_etichetta("parcheggi")["Testo decreto 18191 del 07-08-2026"]
    assert atto["host_file"] == "www301.regione.toscana.it"
    assert script.esclusione(atto, host_pagina) is None
