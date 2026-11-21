"""Registro dei PDF degli avvisi (compito 19c-2), su una cartella di prova.

Nessuna rete: elenco.csv, richieste.csv e i PDF (pdf_minimo di
tests/test_pdf_bando.py) si scrivono in tmp_path; le decisioni a mano si
sostituiscono con monkeypatch.
"""

import csv
import re

import pytest

import scripts.ingestione.registra_avvisi as script
from scripts.ingestione.elenco_pdf_bandi import (
    AVVISO_IN_PIU_PARTI,
    cartella_file,
    nome_del_file,
)
from src.database.schema import CSV_FUORI_DATABASE, TABELLE_DA_CSV
from src.estrazione import pdf_bando as pb
from tests.test_pdf_bando import pdf_minimo

DATA = "2026-11-19"

TESTO_AVVISO = [
    [
        "Soggetti beneficiari: i Comuni",
        "Spese ammissibili: lavori",
        "Criteri di valutazione",
        "Cumulo con altri aiuti",
        "Modalita di presentazione della domanda",
    ]
]

URL_DECRETO = (
    "https://www301.regione.toscana.it/bancadati/atti/Contenuto.xml"
    "?id={id}&nomeFile=Decreto+n.{numero}+del+01-02-2026-+Allegato+{allegato}+"
)
URL_CREDITO = "https://www.creditosportivo.it/u/{nome}.pdf"

COLONNE_ELENCO = list(pb.COLONNE_ELENCO)
COLONNE_RICHIESTE = [
    "ora",
    "tipo",
    "host",
    "url",
    "tentativo",
    "esito",
    "codice",
    "byte",
    "attesa",
    "nota",
]


class Archivio:
    """Una cartella dati-grezzi/avvisi/<data> di prova, riga per riga."""

    def __init__(self, cartella):
        self.cartella = cartella
        self.elenco: list[dict] = []
        self.richieste: list[dict] = []

    def aggiungi(
        self,
        id_bando,
        url,
        classe,
        contenuto,
        sezioni="",
        nota="",
        pagine=None,
        byte=None,
    ):
        percorso = cartella_file(self.cartella, id_bando) / nome_del_file(
            url, script.nome_originale(url)
        )
        percorso.parent.mkdir(parents=True, exist_ok=True)
        percorso.write_bytes(contenuto)
        riga = dict.fromkeys(COLONNE_ELENCO, "")
        riga.update(
            id_bando=id_bando,
            url_pagina=f"https://www.esempio.it/-/{id_bando}",
            n=str(len(self.elenco) + 1),
            classe=classe,
            url_file=url,
            pagine=str(pagine or contenuto.count(b"/Type /Page ")),
            giudizio=pb.LEGGIBILE,
            sha256=pb.impronta_file(percorso),
            sezioni=sezioni,
        )
        self.elenco.append(riga)
        self.richieste.append(
            dict(
                ora="2026-11-19T14:26:27+01:00",
                tipo="file",
                host="www.esempio.it",
                url=url,
                tentativo="1",
                esito="ok",
                codice="200",
                byte=str(byte or len(contenuto)),
                attesa="0",
                nota=nota,
            )
        )
        return percorso

    def scrivi(self):
        for nome, colonne, righe in (
            ("elenco.csv", COLONNE_ELENCO, self.elenco),
            ("richieste.csv", COLONNE_RICHIESTE, self.richieste),
        ):
            with (self.cartella / nome).open(
                "w", encoding="utf-8-sig", newline=""
            ) as f:
                scrittore = csv.DictWriter(f, fieldnames=colonne)
                scrittore.writeheader()
                scrittore.writerows(righe)
        return self.cartella


CODICI = pdf_minimo([["01.11 Coltivazione di cereali"]] * 3)
DECISIONE_CODICI = script.Decisione(
    "codici", script.ELENCO_CODICI, script.SOLO_REGISTRO, "solo codici", "2026-11-20"
)


@pytest.fixture
def archivio(tmp_path, monkeypatch):
    """Un avviso, una proroga, un avviso in più parti, un file per due bandi."""
    a = Archivio(tmp_path)
    a.aggiungi(
        "bando-a",
        URL_DECRETO.format(id=1, numero=100, allegato="A"),
        pb.AVVISO,
        pdf_minimo(TESTO_AVVISO),
    )
    a.aggiungi(
        "bando-a",
        URL_CREDITO.format(nome="Avviso-n.-1-Prova-Proroga-del-termine"),
        pb.PROROGA,
        pdf_minimo([["Proroga del termine"]]),
        nota="vietato dal robots.txt, scaricato per la regola del progetto sugli avvisi",
    )
    a.aggiungi(
        "bando-d",
        URL_DECRETO.format(id=4, numero=400, allegato="A2"),
        pb.ALLEGATO,
        pdf_minimo([["Allegato A2 Intervento B Azione B2: prova"], ["testo"]]),
        sezioni=f"5 su 5 | {AVVISO_IN_PIU_PARTI}",
    )
    for id_bando, numero in (("bando-c", 300), ("bando-b", 200)):
        a.aggiungi(
            id_bando,
            URL_DECRETO.format(id=numero, numero=numero, allegato="4"),
            pb.ALLEGATO,
            CODICI,
        )
    impronta_codici = a.elenco[-1]["sha256"]
    monkeypatch.setattr(script, "DECISIONI_A_MANO", {impronta_codici: DECISIONE_CODICI})
    return a


def per_bandi(righe):
    return {r["id_bandi"]: r for r in righe}


# --- l'atto dal nome del file ---


@pytest.mark.parametrize(
    "url, atto, origine",
    [
        (
            (
                "https://www301.regione.toscana.it/bancadati/atti/Contenuto.xml?id=5519398"
                "&nomeFile=Decreto+n.13512+del+19-06-2026-+Allegato+1+"
            ),
            "Decreto n. 13512 del 19/06/2026, Allegato 1",
            script.DA_NOME_DECRETO,
        ),
        (
            (
                "https://www301.regione.toscana.it/bancadati/atti/Contenuto.xml?id=5512621"
                "&nomeFile=Decreto_n.9505_del_30-04-2026-Allegato-1B"
            ),
            "Decreto n. 9505 del 30/04/2026, Allegato 1B",
            script.DA_NOME_DECRETO,
        ),
        (
            (
                "https://www301.regione.toscana.it/bancadati/atti/Contenuto.xml?id=5527492"
                "&nomeFile=Decreto+n.18191+del+07-08-2026-+Allegato+A_+"
            ),
            "Decreto n. 18191 del 07/08/2026, Allegato A",
            script.DA_NOME_DECRETO,
        ),
        (
            (
                "https://www.mit.gov.it/nfsmitgov/files/media/notizia/2026-11/"
                "avviso_pubblico_prot_26286_del_03_11_2026.pdf"
            ),
            "Avviso pubblico prot. 26286 del 03/11/2026",
            script.DA_NOME_PROTOCOLLO,
        ),
        (
            (
                "https://www.creditosportivo.it/icsc/wp-content/uploads/2026/06/"
                "AVVISO-PUBBLICO-CULTURA-MISSIONE-COMUNE-2026.pdf"
            ),
            "AVVISO PUBBLICO CULTURA MISSIONE COMUNE 2026",
            script.DA_NOME_TITOLO,
        ),
    ],
)
def test_atto_dal_nome(url, atto, origine):
    assert script.atto_dal_nome(script.nome_originale(url)) == (atto, origine)


# --- il registro ---


def test_una_riga_per_impronta(archivio):
    righe = script.costruisci(archivio.scrivi(), DATA)
    assert len(righe) == 4
    assert [r["id_bandi"] for r in righe] == sorted(r["id_bandi"] for r in righe)
    assert list(righe[0]) == script.COLONNE


def test_file_per_due_bandi(archivio):
    riga = per_bandi(script.costruisci(archivio.scrivi(), DATA))["bando-b|bando-c"]
    assert riga["classe"] == script.ELENCO_CODICI
    assert riga["uso"] == script.SOLO_REGISTRO
    assert riga["deciso_da"] == script.A_MANO
    assert riga["deciso_il"] == "2026-11-20"
    assert riga["atto"] == (
        "Decreto n. 200 del 01/02/2026, Allegato 4|"
        "Decreto n. 300 del 01/02/2026, Allegato 4"
    )
    assert [u.split("id=")[1][:3] for u in riga["url_file"].split("|")] == [
        "200",
        "300",
    ]
    assert riga["url_pagina"].split("|") == [
        "https://www.esempio.it/-/bando-b",
        "https://www.esempio.it/-/bando-c",
    ]
    assert len(riga["nome_file"].split("|")) == 2


def test_regole_dello_script(archivio):
    righe = script.costruisci(archivio.scrivi(), DATA)
    del_bando_a = {r["classe"]: r for r in righe if r["id_bandi"] == "bando-a"}
    avviso, proroga = del_bando_a[pb.AVVISO], del_bando_a[pb.PROROGA]
    assert (avviso["classe"], avviso["uso"], avviso["deciso_da"]) == (
        pb.AVVISO,
        script.FRAMMENTI,
        script.SCRIPT,
    )
    assert avviso["motivo"] == "5 sezioni su 5"
    assert avviso["deciso_il"] == DATA
    assert avviso["eccezione_robots"] == "no"
    assert (proroga["classe"], proroga["uso"]) == (pb.PROROGA, script.FRAMMENTI)
    assert proroga["eccezione_robots"] == "sì"
    assert proroga["scaricato_il"] == "2026-11-19"
    in_parti = per_bandi(righe)["bando-d"]
    assert (in_parti["classe"], in_parti["parte"]) == (pb.AVVISO, "Azione B2: prova")
    assert in_parti["pagine"] == "2"


# --- nome dell'azione di un avviso in più parti ---


@pytest.fixture
def senza_decisioni(monkeypatch):
    monkeypatch.setattr(script, "DECISIONI_A_MANO", {})


def riga_in_parti(tmp_path, prima_pagina):
    """La riga del registro di un solo avviso in più parti, con questa pagina 1."""
    a = Archivio(tmp_path)
    a.aggiungi(
        "bando-d",
        URL_DECRETO.format(id=4, numero=400, allegato="A2"),
        pb.ALLEGATO,
        pdf_minimo([prima_pagina, ["testo"]]),
        sezioni=f"5 su 5 | {AVVISO_IN_PIU_PARTI}",
    )
    (riga,) = script.costruisci(a.scrivi(), DATA)
    return riga


SOLO_CODICE_B2 = script.PARTE_SOLO_CODICE.format(codice="B2")


def test_parte_con_il_nome_dal_titolo(tmp_path, senza_decisioni):
    riga = riga_in_parti(
        tmp_path,
        [
            "Allegato A3",
            "Intervento B Azione B3: Ripopolamento patrimonio apistico",
            "Disposizioni e modalita attuative",
        ],
    )
    assert riga["parte"] == "Azione B3: Ripopolamento patrimonio apistico"
    assert riga["motivo"] == (
        f"{AVVISO_IN_PIU_PARTI} (elenco_pdf_bandi); {script.PARTE_DAL_TITOLO}"
    )


@pytest.mark.parametrize(
    "prima_pagina",
    [
        # "Azione B2:" solo dentro una frase del testo, che continua alla riga dopo
        [
            "Allegato A2",
            "Sono ammesse le spese previste dall'Azione B2: arnie, telaini, fogli cerei,",
            "nei limiti indicati al paragrafo 4 del presente bando",
        ],
        # nome oltre i 100 caratteri
        ["Intervento B Azione B2: " + "parola " * 20],
        # senza i due punti
        ["Intervento B Azione B2 Lotta a parassiti e malattie"],
        # parola spezzata a fine riga
        ["Intervento B Azione B2: Acquisto di attrez-", "zature"],
        # nome vuoto
        ["Intervento B Azione B2:"],
    ],
    ids=["frase", "oltre-100", "senza-due-punti", "parola-spezzata", "vuoto"],
)
def test_parte_solo_codice_senza_titolo(tmp_path, prima_pagina, senza_decisioni):
    riga = riga_in_parti(tmp_path, prima_pagina)
    assert riga["parte"] == "Azione B2"
    assert (
        riga["motivo"] == f"{AVVISO_IN_PIU_PARTI} (elenco_pdf_bandi); {SOLO_CODICE_B2}"
    )


def test_parte_solo_codice_nel_rapporto(tmp_path, capsys, senza_decisioni):
    a = Archivio(tmp_path / "avvisi")
    a.cartella.mkdir()
    a.aggiungi(
        "bando-d",
        URL_DECRETO.format(id=4, numero=400, allegato="A2"),
        pb.ALLEGATO,
        pdf_minimo([["Intervento B Azione B2 senza titolo"], ["testo"]]),
        sezioni=f"5 su 5 | {AVVISO_IN_PIU_PARTI}",
    )
    uscita = tmp_path / "processed"
    uscita.mkdir()
    codice = script.main(["--data", DATA], a.scrivi(), uscita)
    assert codice == 0
    assert "Attenzione: " in capsys.readouterr().out
    assert "Azione B2, senza nome" in "\n".join(
        script.parti_senza_nome(script.costruisci(a.cartella, DATA))
    )


# I quattro allegati veri degli apistici (decreto n. 14025 del 18/06/2026) e i
# nomi decisi in docs/coda.md, passo 19d, punto 5. I file stanno in
# dati-grezzi/, fuori dal repository: senza, il test si salta.
APISTICI = {
    "decreto-n-14025-del-18-06-2026--allegato-a1-e268ff8c.pdf": (
        "Azione B1: Lotta a parassiti e malattie"
    ),
    "decreto-n-14025-del-18-06-2026--allegato-a3-bd90bf80.pdf": (
        "Azione B3: Ripopolamento patrimonio apistico"
    ),
    "decreto-n-14025-del-18-06-2026--allegato-a4-764c40fe.pdf": (
        "Azione B4: Razionalizzazione della transumanza"
    ),
    "decreto-n-14025-del-18-06-2026--allegato-a5-955dbd58.pdf": (
        "Azione B5: Acquisto di attrezzature e sistemi di gestione"
    ),
}
BANDO_APISTICI = "sostegno-agli-investimenti-strutturali-aziende-apisti-401650"


def test_nomi_delle_azioni_dai_quattro_allegati_veri():
    from scripts.ingestione.elenco_pdf_bandi import cartella_di

    cartella = cartella_file(cartella_di("2026-11-19"), BANDO_APISTICI)
    percorsi = {nome: cartella / nome for nome in APISTICI}
    if not all(p.is_file() for p in percorsi.values()):
        pytest.skip("allegati degli apistici non su disco (dati-grezzi/)")
    trovati = {}
    for nome, percorso in percorsi.items():
        f = script.FileScaricato(
            {"sezioni": AVVISO_IN_PIU_PARTI, "id_bando": BANDO_APISTICI},
            percorso,
            nome,
            {},
        )
        scelta, parte = script.decisione_dello_script(f, DATA)
        assert scelta["motivo"].endswith(script.PARTE_DAL_TITOLO)
        trovati[nome] = parte
    assert trovati == APISTICI


def test_totali(archivio):
    righe = script.costruisci(archivio.scrivi(), DATA)
    assert script.totali(righe) == (3, 1 + 1 + 2)


# --- quando lo script si ferma ---


def test_file_mancante(archivio):
    cartella = archivio.scrivi()
    next(cartella.rglob("*.pdf")).unlink()
    with pytest.raises(script.ErroreRegistro, match="non trovato su disco"):
        script.costruisci(cartella, DATA)


def test_impronta_diversa(archivio):
    cartella = archivio.scrivi()
    percorso = next(cartella.rglob("*.pdf"))
    percorso.write_bytes(percorso.read_bytes() + b"\n")
    with pytest.raises(script.ErroreRegistro, match="impronta diversa"):
        script.costruisci(cartella, DATA)


def test_byte_diversi_dal_registro_delle_richieste(archivio):
    archivio.richieste[0]["byte"] = "1"
    with pytest.raises(script.ErroreRegistro, match="registro delle richieste"):
        script.costruisci(archivio.scrivi(), DATA)


def test_pagine_diverse_dall_elenco(archivio):
    archivio.elenco[0]["pagine"] = "9"
    with pytest.raises(script.ErroreRegistro, match="pagine"):
        script.costruisci(archivio.scrivi(), DATA)


def test_file_senza_regola(archivio):
    archivio.aggiungi(
        "bando-e",
        URL_DECRETO.format(id=5, numero=500, allegato="B"),
        pb.ALLEGATO,
        pdf_minimo([["Allegato B"]]),
    )
    with pytest.raises(script.ErroreRegistro, match="DECISIONI_A_MANO"):
        script.costruisci(archivio.scrivi(), DATA)


def test_decisione_a_mano_senza_file(archivio, monkeypatch):
    decisioni = {**script.DECISIONI_A_MANO, "f" * 64: DECISIONE_CODICI}
    monkeypatch.setattr(script, "DECISIONI_A_MANO", decisioni)
    with pytest.raises(script.ErroreRegistro, match="senza file"):
        script.costruisci(archivio.scrivi(), DATA)


def test_file_per_due_bandi_da_dividere(archivio, monkeypatch):
    impronta = next(iter(script.DECISIONI_A_MANO))
    da_dividere = script.Decisione("x", pb.AVVISO, script.FRAMMENTI, "prova", DATA)
    monkeypatch.setattr(script, "DECISIONI_A_MANO", {impronta: da_dividere})
    with pytest.raises(script.ErroreRegistro, match="per 2 bandi"):
        script.costruisci(archivio.scrivi(), DATA)


# --- scrittura e rilancio ---


def test_rilancio_stesso_file_byte_per_byte(archivio, tmp_path, capsys):
    cartella = archivio.scrivi()
    processed = tmp_path / "processed"
    processed.mkdir()
    argomenti = ["--data", DATA]
    assert script.main(argomenti, cartella, processed) == 0
    primo = (processed / script.NOME_FILE).read_bytes()
    assert primo.startswith("﻿".encode()) and b"\r\n" in primo
    assert script.main(argomenti, cartella, processed) == 0
    assert (processed / script.NOME_FILE).read_bytes() == primo
    assert script.main([*argomenti, "--controlla"], cartella, processed) == 0
    assert "aggiornato" in capsys.readouterr().out


def test_controlla_non_scrive(archivio, tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    assert (
        script.main(["--data", DATA, "--controlla"], archivio.scrivi(), processed) == 1
    )
    assert not (processed / script.NOME_FILE).exists()


def test_errore_non_scrive(archivio, tmp_path):
    archivio.richieste[0]["byte"] = "1"
    processed = tmp_path / "processed"
    processed.mkdir()
    assert script.main(["--data", DATA], archivio.scrivi(), processed) == 1
    assert not (processed / script.NOME_FILE).exists()


# --- il registro vero ---


def test_registro_fuori_dal_database():
    assert "documenti_bandi" in CSV_FUORI_DATABASE
    assert "documenti_bandi" not in TABELLE_DA_CSV
    assert script.NOME_FILE == "documenti_bandi.csv"


CLASSI = {
    pb.AVVISO,
    pb.CONSOLIDATO,
    pb.PROROGA,
    pb.ALLEGATO,
    script.ELENCO_CODICI,
    script.PRESENTAZIONE,
}


def test_decisioni_a_mano_complete():
    """Ogni decisione ha impronta, classe, uso, motivo e data."""
    for impronta, d in script.DECISIONI_A_MANO.items():
        assert re.fullmatch(r"[0-9a-f]{64}", impronta)
        assert d.classe in CLASSI
        assert d.uso in (script.FRAMMENTI, script.SOLO_REGISTRO)
        assert d.motivo and d.file
        assert re.fullmatch(r"2026-\d\d-\d\d", d.deciso_il)
