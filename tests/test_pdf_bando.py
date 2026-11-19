"""Test dell'elenco dei PDF della pagina di un bando (passo 19, compito 19a).

Pagine salvate (tests/pagine) e PDF scritti a mano nel test: mai i siti.
"""

import csv
import io
import urllib.request
from pathlib import Path

import pytest

from src.estrazione import pdf_bando as pb

PAGINE = Path(__file__).parent / "pagine"

URL_AS01 = (
    "https://www.montagnappennino.it/bando/aso1-investimenti-non-produttivi-"
    "e-per-lo-sviluppo-socio-economico-delle-ree-rurali/"
)
URL_SRD14 = (
    "https://www.montagnappennino.it/bando/srd-14-investimenti-produttivi-"
    "non-agricoli-in-aree-rurali/"
)
URL_SINTETICA = "https://www.regione.toscana.it/-/bando-di-prova-2026"
UPLOADS = "https://www.montagnappennino.it/wp-content/uploads/2026"


def leggi(nome: str) -> str:
    return (PAGINE / nome).read_text(encoding="utf-8")


def per_nome(collegamenti) -> dict[str, pb.Collegamento]:
    return {c.nome_file: c for c in collegamenti}


def classi(righe) -> dict[str, str]:
    return {r["url_file"].rsplit("/", 1)[-1]: r["classe"] for r in righe}


# --- PDF minimi scritti a mano, senza dipendenze ---


def _stringa_pdf(testo: str) -> str:
    return testo.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_minimo(pagine: list[list[str]]) -> bytes:
    """Un PDF con una riga di testo per ogni stringa, pagina per pagina."""
    quante = len(pagine)
    figli = " ".join(f"{4 + 2 * i} 0 R" for i in range(quante))
    oggetti = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{figli}] /Count {quante} >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for i, righe in enumerate(pagine):
        testo = " ".join(f"({_stringa_pdf(r)}) Tj T*" for r in righe)
        flusso = f"BT /F1 10 Tf 12 TL 50 780 Td {testo} ET"
        oggetti.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {5 + 2 * i} 0 R >>"
        )
        oggetti.append(f"<< /Length {len(flusso)} >>\nstream\n{flusso}\nendstream")

    contenuto = b"%PDF-1.4\n"
    posizioni = []
    for numero, oggetto in enumerate(oggetti, start=1):
        posizioni.append(len(contenuto))
        contenuto += f"{numero} 0 obj\n{oggetto}\nendobj\n".encode("latin-1")
    inizio_xref = len(contenuto)
    contenuto += f"xref\n0 {len(oggetti) + 1}\n0000000000 65535 f \n".encode()
    contenuto += b"".join(f"{p:010d} 00000 n \n".encode() for p in posizioni)
    contenuto += (
        f"trailer\n<< /Size {len(oggetti) + 1} /Root 1 0 R >>\n"
        f"startxref\n{inizio_xref}\n%%EOF\n"
    ).encode()
    return contenuto


RIGA_LUNGA = (
    "Possono presentare domanda i Comuni con popolazione inferiore a cinquemila "
    "abitanti, singoli o associati, per interventi di manutenzione straordinaria"
)


def scrivi_pdf(cartella: Path, nome: str, pagine: list[list[str]]) -> Path:
    percorso = cartella / nome
    percorso.write_bytes(pdf_minimo(pagine))
    return percorso


# --- link ai documenti: pagina vera ---


def test_link_della_pagina_vera_del_gal():
    collegamenti = pb.link_ai_documenti(leggi("gal-as01.html"), URL_AS01)
    nomi = [c.nome_file for c in collegamenti]

    # 20 link a PDF nella pagina, 16 file diversi
    assert len(collegamenti) == 16
    assert len(set(nomi)) == 16
    # nell'ordine della pagina
    assert nomi[:3] == [
        "2026_13_risposta_GAL-MontagnAppennino.pdf",
        "Raccordo-ALL-A-versione-semplificata.pdf",
        "Raccordo-ALL-A-versione-completa.pdf",
    ]
    assert all(
        c.url.startswith("https://www.montagnappennino.it/") for c in collegamenti
    )
    assert all(c.host == "www.montagnappennino.it" for c in collegamenti)
    assert all(c.url.lower().endswith(".pdf") for c in collegamenti)

    errata = per_nome(collegamenti)["167_2026-ERRATA-CORRIGE.pdf"]
    assert errata.url == f"{UPLOADS}/05/167_2026-ERRATA-CORRIGE.pdf"
    assert errata.testo == "(Scarica la nota)"


def test_link_senza_testo_prendono_il_nome_del_file():
    collegamenti = per_nome(pb.link_ai_documenti(leggi("gal-as01.html"), URL_AS01))
    bando = collegamenti["Bando-AS01-13.05.2026.pdf"]
    assert bando.testo == ""
    assert pb.etichetta(bando) == "Bando AS01 13.05.2026"

    generico = collegamenti["2026_13_risposta_GAL-MontagnAppennino.pdf"]
    assert generico.testo == "CLICCA QUI"
    assert pb.etichetta(generico) == "2026 13 risposta GAL MontagnAppennino"


# --- classificazione ---


def test_classi_sulle_pagine_del_gal():
    righe_as01 = pb.righe_elenco(
        "as01", URL_AS01, pb.link_ai_documenti(leggi("gal-as01.html"), URL_AS01)
    )
    righe_srd14 = pb.righe_elenco(
        "srd14", URL_SRD14, pb.link_ai_documenti(leggi("gal-srd14.html"), URL_SRD14)
    )
    as01 = classi(righe_as01)
    srd14 = classi(righe_srd14)

    assert as01["Bando-AS01-13.05.2026.pdf"] == pb.AVVISO
    assert as01["167_2026-ERRATA-CORRIGE.pdf"] == pb.PROROGA
    assert as01["Delibera-1_2026-approvaz.-elenco-Int.-SRD14.pdf"] == pb.DA_DECIDERE
    assert as01["estratto-PARTE-III-n.-37-del-16.09.2026.pdf"] == pb.DA_DECIDERE
    assert as01["estrattoPARTE-III-n.-20-del-20.05.2026.pdf"] == pb.DA_DECIDERE
    assert as01["Allegato-A-AS01-TIPOLOGIE-SPESA.pdf"] == pb.ALLEGATO
    assert srd14["36_2026-BURT.pdf"] == pb.DA_DECIDERE
    # "versione completa" non e' un testo consolidato
    assert as01["Raccordo-ALL-A-versione-completa.pdf"] != pb.CONSOLIDATO
    assert pb.CONSOLIDATO not in as01.values()


@pytest.mark.parametrize(
    ("etichetta", "nome_file", "attesa"),
    [
        ("Allegato B - Modulo di domanda", "allegato-b.pdf", pb.MODULISTICA),
        ("Avviso – testo coordinato con le modifiche", "avviso.pdf", pb.CONSOLIDATO),
        ("Avviso aggiornato alle modifiche del 2026", "avviso.pdf", pb.CONSOLIDATO),
        ("Proroga dei termini dell'avviso", "proroga.pdf", pb.PROROGA),
        ("Decreto dirigenziale 18191", "dd-18191.pdf", pb.ATTO),
        ("Avviso pubblico", "avviso-2026.pdf", pb.AVVISO),
        ("Allegato C - Tabella dei punteggi", "all-c.pdf", pb.ALLEGATO),
        ("Informativa", "informativa.pdf", pb.ALTRO),
    ],
)
def test_ordine_delle_regole(etichetta, nome_file, attesa):
    assert pb.classifica(etichetta, nome_file)[0] == attesa


@pytest.mark.parametrize("etichetta", ["Allegato A", "All. A", "ALLEGATO A."])
def test_solo_allegato_a_e_probabile_avviso(etichetta):
    classe, motivo = pb.classifica(etichetta, "documento.pdf")
    assert classe == pb.ALLEGATO
    assert pb.PROBABILE_AVVISO in motivo


@pytest.mark.parametrize(
    ("etichetta", "nome_file", "attesa"),
    [
        # altre parole nell'etichetta: non e' solo "Allegato A"
        ("Allegato A - Tipologie di spesa", "all-a.pdf", pb.ALLEGATO),
        # una parola decisiva nel nome del file decide la classe
        ("Allegato A", "allegato-a-avviso.pdf", pb.AVVISO),
        ("Allegato B", "allegato-b.pdf", pb.ALLEGATO),
    ],
)
def test_probabile_avviso_solo_per_allegato_a_senza_altro(etichetta, nome_file, attesa):
    classe, motivo = pb.classifica(etichetta, nome_file)
    assert classe == attesa
    assert pb.PROBABILE_AVVISO not in motivo


# --- link ai documenti: pagina sintetica della Regione ---


def test_link_della_pagina_sintetica():
    collegamenti = pb.link_ai_documenti(
        leggi("pdf-regione-sintetica.html"), URL_SINTETICA
    )
    url = [c.url for c in collegamenti]
    base = "https://www.regione.toscana.it"

    assert url == [
        f"{base}/documents/d/guest/decreto-99999-2026-pdf.pdf",
        f"{base}/documents/10180/123456/Allegato+A.pdf/0a1b2c3d-uuid?t=1730000000",
        f"{base}/documents/10180/123456/Allegato%20B%20-%20Modulo%20di%20domanda.PDF",
        f"{base}/-/documenti/avviso-testo-coordinato.pdf",
        f"{base}/documents/d/guest/proroga-termini.pdf",
        f"{base}/documents/d/guest/allegato-a-firmato.pdf.p7m",
        "https://www.burt.regione.toscana.it/estratto-parte-iii-n-40.pdf",
    ]
    nomi = per_nome(collegamenti)
    assert nomi["Allegato+A.pdf"].testo == "Allegato A"
    assert "Allegato B - Modulo di domanda.pdf" in nomi
    # il link con l'icona viene prima, ma conta il testo del secondo
    assert nomi["proroga-termini.pdf"].testo == "Proroga dei termini dell'avviso"
    # "Leggi" cede il posto al title
    assert nomi["estratto-parte-iii-n-40.pdf"].testo == "Estratto del BURT"

    p7m = [c.nome_file for c in collegamenti if c.p7m]
    assert p7m == ["allegato-a-firmato.pdf.p7m"]

    host = {c.host for c in collegamenti}
    assert host == {"www.regione.toscana.it", "www.burt.regione.toscana.it"}


def test_classi_della_pagina_sintetica():
    collegamenti = pb.link_ai_documenti(
        leggi("pdf-regione-sintetica.html"), URL_SINTETICA
    )
    righe = pb.righe_elenco("prova", URL_SINTETICA, collegamenti)
    assert [r["classe"] for r in righe] == [
        pb.ATTO,
        pb.ALLEGATO,
        pb.MODULISTICA,
        pb.CONSOLIDATO,
        pb.PROROGA,
        pb.ALLEGATO,
        pb.DA_DECIDERE,
    ]
    assert pb.PROBABILE_AVVISO in righe[1]["motivo_classe"]
    assert [r["p7m"] for r in righe].count("sì") == 1


# --- indicatori di leggibilita' ---


def test_pdf_leggibile(tmp_path):
    percorso = scrivi_pdf(tmp_path, "avviso.pdf", [[RIGA_LUNGA] * 4 for _ in range(3)])
    ind = pb.indicatori_pdf(percorso)
    assert ind.pagine == 3
    assert ind.pagine_vuote == 0
    assert ind.caratteri_per_pagina > pb.CARATTERI_MINIMI_PER_PAGINA
    assert pb.giudizio(ind)[0] == pb.LEGGIBILE


def test_pdf_senza_testo_e_da_ocr(tmp_path):
    percorso = scrivi_pdf(tmp_path, "scansione.pdf", [[], [], [RIGA_LUNGA]])
    ind = pb.indicatori_pdf(percorso)
    assert ind.pagine == 3
    assert ind.pagine_vuote == 2
    assert pb.giudizio(ind) == (pb.DA_OCR, "2 pagine su 3 senza testo")


def test_righe_ripetute_contate(tmp_path):
    intestazione = "REGIONE TOSCANA - Avviso pubblico di prova"
    pagine = [
        [intestazione, f"Articolo {n}. {RIGA_LUNGA}", "Pag.", f"{n}"]
        for n in range(1, 5)
    ]
    ind = pb.indicatori_pdf(scrivi_pdf(tmp_path, "intestato.pdf", pagine))
    # l'intestazione si conta; "Pag.", ripetuta ma brevissima, no
    assert ind.righe_ripetute == 1
    esito, motivo = pb.giudizio(ind)
    assert esito == pb.LEGGIBILE
    assert "1 righe ripetute" in motivo


def test_molte_righe_brevi_da_rivedere(tmp_path):
    tabella = ["Voce", "Importo", "Spese tecniche", "10.000", "Lavori", "90.000"]
    pagine = [tabella * 8 for _ in range(3)]
    ind = pb.indicatori_pdf(scrivi_pdf(tmp_path, "tabella.pdf", pagine))
    assert ind.righe_brevi > pb.QUOTA_RIGHE_BREVI
    assert pb.giudizio(ind)[0] == pb.DA_RIVEDERE


def test_parole_spezzate_da_rivedere():
    pagina = "\n".join([f"{RIGA_LUNGA[:60]} manuten-", "zione straordinaria"] * 10)
    ind = pb.indicatori([pagina] * 3)
    assert ind.parole_spezzate > pb.QUOTA_PAROLE_SPEZZATE
    assert pb.giudizio(ind)[0] == pb.DA_RIVEDERE


def test_impronta_del_file(tmp_path):
    percorso = scrivi_pdf(tmp_path, "a.pdf", [[RIGA_LUNGA]])
    assert pb.impronta_file(percorso) == pb.impronta_file(percorso)
    assert len(pb.impronta_file(percorso)) == 64


# --- elenco ---


def test_elenco_colonne_e_decisione_vuota(tmp_path):
    collegamenti = pb.link_ai_documenti(
        leggi("pdf-regione-sintetica.html"), URL_SINTETICA
    )
    percorso = scrivi_pdf(tmp_path, "a.pdf", [[RIGA_LUNGA] * 4] * 2)
    letti = {
        collegamenti[1].url: (pb.indicatori_pdf(percorso), pb.impronta_file(percorso))
    }
    righe = pb.righe_elenco("prova", URL_SINTETICA, collegamenti, letti)
    file_elenco = tmp_path / "elenco.csv"
    pb.scrivi_elenco(righe, file_elenco)

    with file_elenco.open(encoding="utf-8-sig", newline="") as f:
        lette = list(csv.DictReader(f))
    assert list(lette[0]) == pb.COLONNE_ELENCO
    assert all(r["decisione"] == "" for r in lette)
    # indicatori solo per il file letto
    assert lette[1]["pagine"] == "2"
    assert lette[1]["giudizio"] == pb.LEGGIBILE
    assert lette[0]["pagine"] == "" and lette[0]["giudizio"] == ""


def test_elenco_ripetibile_e_ordinato():
    righe_a = pb.righe_elenco(
        "b", URL_AS01, pb.link_ai_documenti(leggi("gal-as01.html"), URL_AS01)
    )
    righe_b = pb.righe_elenco(
        "a", URL_SRD14, pb.link_ai_documenti(leggi("gal-srd14.html"), URL_SRD14)
    )
    primo = pb.contenuto_elenco(righe_a + righe_b)
    assert primo == pb.contenuto_elenco(list(reversed(righe_b + righe_a)))
    lette = list(csv.DictReader(io.StringIO(primo.decode("utf-8-sig"))))
    assert [r["id_bando"] for r in lette] == ["a"] * len(righe_b) + ["b"] * len(righe_a)


def test_elenco_senza_dati_personali():
    vietate = ("nome", "email", "mail", "telefono", "pec", "responsabile", "contatt")
    assert not [c for c in pb.COLONNE_ELENCO if any(v in c for v in vietate)]


def test_tabella_per_bando():
    collegamenti = pb.link_ai_documenti(
        leggi("pdf-regione-sintetica.html"), URL_SINTETICA
    )
    tabella = pb.tabella_elenco(pb.righe_elenco("prova", URL_SINTETICA, collegamenti))
    assert tabella.startswith(f"prova — {URL_SINTETICA}")
    assert tabella.count("\n| ") == 1 + len(collegamenti)


# --- nessuna rete ---


def test_nessuna_richiesta_di_rete(monkeypatch, tmp_path):
    def vietata(*_args, **_kwargs):
        raise AssertionError("richiesta di rete")

    monkeypatch.setattr(urllib.request, "urlopen", vietata)
    collegamenti = pb.link_ai_documenti(
        leggi("pdf-regione-sintetica.html"), URL_SINTETICA
    )
    percorso = scrivi_pdf(tmp_path, "a.pdf", [[RIGA_LUNGA]])
    letti = {
        collegamenti[0].url: (pb.indicatori_pdf(percorso), pb.impronta_file(percorso))
    }
    righe = pb.righe_elenco("prova", URL_SINTETICA, collegamenti, letti)
    pb.scrivi_elenco(righe, tmp_path / "elenco.csv")
    assert pb.tabella_elenco(righe)


def test_intestazione_che_dichiara_il_progetto():
    assert "rag-bandi-comunali" in pb.INTESTAZIONI_PROGETTO["User-Agent"]


# --- compito 19b: sezioni, anteprima, ordine di scarico, richiami ---

PAGINE_AVVISO = [
    "REGIONE TOSCANA\nAvviso pubblico per il sostegno dei parcheggi\nArt. 1 Finalità",
    "Art. 3 Soggetti beneficiari\nPossono presentare domanda i Comuni.",
    "Art. 5 Spese ammissibili\nSono ammesse le spese tecniche.",
    "Art. 7 Criteri di valutazione e punteggio\nArt. 8 Cumulo con altri aiuti",
    "Art. 9 Modalità di presentazione della domanda",
]


def test_sezioni_con_le_pagine():
    sezioni = pb.sezioni_avviso(PAGINE_AVVISO)
    assert sezioni.trovate == {
        "beneficiari": [2],
        "spese ammissibili": [3],
        "criteri o punteggio": [4],
        "cumulo": [4],
        "modalità di presentazione": [5],
    }
    assert sezioni.contrari == {}
    assert pb.e_avviso(sezioni) == (True, "")


def test_soglia_delle_sezioni():
    due = pb.sezioni_avviso(["Soggetti beneficiari", "Spese ammissibili"])
    assert pb.e_avviso(due) == (False, f"2 sezioni su {len(pb.SEZIONI)}")
    tre = pb.sezioni_avviso(["Soggetti beneficiari", "Spese ammissibili", "Cumulo"])
    assert pb.e_avviso(tre)[0] is True
    assert pb.SEZIONI_MINIME_AVVISO == 3


def test_segnali_contrari():
    pagine = [
        "IL DIRIGENTE\nDECRETA\ndi approvare l'avviso",
        "Il sottoscritto (nome e cognome)\ndichiara di essere",
        "si decreta in minuscolo",
    ]
    sezioni = pb.sezioni_avviso(pagine)
    assert sezioni.contrari == {pb.DECRETA: [1], pb.SOTTOSCRITTO: [2]}


def test_modulo_non_e_un_avviso():
    modulo = [
        f"Il sottoscritto dichiara\n{s}"
        for s in ("beneficiari", "spese ammissibili", "cumulo")
    ]
    esito, nota = pb.e_avviso(pb.sezioni_avviso(modulo))
    assert esito is False
    assert nota.startswith("modulo")


def test_decreto_con_l_avviso_allegato():
    pagine = ["IL DIRIGENTE\nDECRETA\ndi approvare l'Allegato A", *PAGINE_AVVISO[1:]]
    sezioni = pb.sezioni_avviso(pagine)
    assert pb.e_avviso(sezioni) == (True, "decreto con l'avviso allegato da pag. 2")
    testo = pb.testo_sezioni(sezioni)
    assert testo.startswith("5 su 5; beneficiari p. 2;")
    assert "contrari: DECRETA p. 1" in testo
    assert testo.endswith("decreto con l'avviso allegato da pag. 2")


def test_anteprima_prima_pagina_con_testo():
    assert (
        pb.anteprima(["", "  Riga uno  \n\nRiga   due", "altro"])
        == "Riga uno / Riga due"
    )
    lunga = pb.anteprima(["x" * 500])
    assert len(lunga) == pb.CARATTERI_ANTEPRIMA
    assert lunga.endswith("…")


def riga_finta(n, classe, motivo="", p7m="no", etichetta="", url=""):
    return {
        "n": n,
        "classe": classe,
        "motivo_classe": motivo,
        "p7m": p7m,
        "etichetta": etichetta,
        "url_file": url or f"https://x.it/{n}.pdf",
    }


def test_ordine_di_scarico():
    righe = [
        riga_finta(1, pb.DA_DECIDERE),
        riga_finta(2, pb.ALTRO),
        riga_finta(3, pb.ATTO),
        riga_finta(4, pb.ALLEGATO),
        riga_finta(5, pb.ALLEGATO, f"'allegat'; {pb.PROBABILE_AVVISO}"),
        riga_finta(6, pb.AVVISO),
        riga_finta(7, pb.CONSOLIDATO),
        riga_finta(8, pb.MODULISTICA),
        riga_finta(9, pb.ALLEGATO, p7m="sì"),
    ]
    assert [r["n"] for r in pb.ordine_di_scarico(righe)] == [7, 6, 5, 4, 3, 2, 1]
    assert pb.da_non_scaricare(righe[7]) == "modulistica"
    assert pb.da_non_scaricare(righe[8]) == "p7m"


def test_allegati_richiamati_per_beneficiari_o_ateco():
    righe = [
        riga_finta(1, pb.ALLEGATO, etichetta="Allegato B - Codici ammessi"),
        riga_finta(2, pb.ALLEGATO, etichetta="Allegato C - Schema di relazione"),
        riga_finta(
            3, pb.ALLEGATO, url="https://x.it/All_D_beneficiari.pdf", etichetta="Elenco"
        ),
        riga_finta(4, pb.MODULISTICA, etichetta="Allegato E - Modulo"),
    ]
    testi = [
        "Le imprese con codici ATECO di cui all'Allegato B possono partecipare.",
        "I soggetti beneficiari sono elencati nell'Allegato D.",
        "La relazione segue l'Allegato C. Allegato al presente avviso.",
        "beneficiari: si veda l'Allegato E",
    ]
    scelte = pb.allegati_richiamati(testi, righe)
    # B per i codici ATECO, D per i beneficiari; C non e' richiamato per
    # questi motivi; E e' modulistica
    assert [r["n"] for r in scelte] == [1, 3]


def test_link_verso_la_pagina_dell_avviso():
    html = """
    <a href="/comunicazione/news/notizia">Questa notizia</a>
    <a href="/documentazione/avviso-pubblico-2026">Leggi l'avviso pubblico</a>
    <a href="/documentazione/avviso-pubblico-2026#modulistica">Modulistica</a>
    <a href="/files/avviso.pdf">Avviso in PDF</a>
    <a href="mailto:avvisi@mit.gov.it">Scrivi</a>
    <a href="/contatti">Contatti</a>
    """
    pagina = "https://www.mit.gov.it/comunicazione/news/notizia"
    assert pb.link_verso_avviso(html, pagina) == [
        "https://www.mit.gov.it/documentazione/avviso-pubblico-2026"
    ]


def test_riga_a_mano():
    riga = pb.riga_a_mano("prova", URL_SINTETICA, 9, "Avviso_pubblico_firmato.pdf")
    assert riga["etichetta"] == "Avviso pubblico firmato"
    assert riga["classe"] == pb.AVVISO
    assert riga["url_file"] == ""
    assert set(riga) == set(pb.COLONNE_ELENCO)
