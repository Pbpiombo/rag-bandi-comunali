"""Controllo meccanico del foglio dei fatti (scripts/diagnostica/controlla_fatti.py).

Tutto inventato: pagine, frasi, bandi, nomi. Nessun PDF, nessun Chroma.
"""

import pytest

import scripts.diagnostica.controlla_fatti as cf

PAGINA_1 = (
    "Art. 3 Beneficiari\nPossono presentare domanda i Comuni con meno di\n"
    "5.000 abitanti, singoli o associati.\n"
)
PAGINA_2 = (
    "Art. 5 Contributo\nIl contri buto massimo è di 40.000,00 euro per l’intervento.\n"
    "Tabella 1\nAzione A1\n20%\nAzione A2\n30%\n"
)
PAGINA_3 = "Art. 7 Spese\nSono ammesse le spese di proget-\ntazione e i lavori.\n"
ALTRO = "Allegato\nLe spese di progettazione sono ammesse fino al 10%.\n"


def file_pdf(id_bando, pagine, sha="a" * 64, parte="", classe="avviso", nome=None):
    return cf.FilePdf(sha, id_bando, classe, parte, nome or f"{id_bando}.pdf", pagine)


@pytest.fixture
def archivio():
    return [
        file_pdf("bando-a", [PAGINA_1, PAGINA_2, PAGINA_3]),
        file_pdf("bando-a", ["Proroga del termine al 30 novembre"], sha="p" * 64,
                 classe="proroga"),
        file_pdf("bando-b", [ALTRO], sha="b" * 64),
    ]  # fmt: skip


def fatto(frase, pagina="1", in_tabella="no", solo="", id_bando="bando-a", **altri):
    return {
        "riga": 2,
        "id_bando": id_bando,
        "tipo_fatto": "prova",
        "registro": "semplice",
        "domanda": altri.pop("domanda", "Chi può partecipare?"),
        "frase": frase,
        "pagina_fisica": pagina,
        "in_tabella": in_tabella,
        "frase_solo_in_questo_bando": solo,
        "note": altri.pop("note", ""),
        **altri,
    }


def un_frammento_per_pagina(archivio):
    """Ogni pagina in un frammento, tutto nella parte vista."""
    return {
        f.sha256: [cf.Frammento(n, n + 1, p, 10_000) for n, p in enumerate(f.pagine)]
        for f in archivio
    }


def controlla(f, archivio, frammenti=None):
    if frammenti is None:
        frammenti = un_frammento_per_pagina(archivio)
    return cf.controlla_fatto(f, archivio, frammenti)


# --- testo e livelli ---


def test_tre_livelli(archivio):
    f = archivio[0]
    assert cf.livello_nella_pagina("i Comuni con meno di", f, 1) == "a"
    # a capo, apostrofo tipografico, parola spezzata dal trattino
    assert cf.livello_nella_pagina("meno di 5.000 abitanti", f, 1) == "b"
    assert cf.livello_nella_pagina("per l'intervento", f, 2) == "b"
    assert cf.livello_nella_pagina("spese di progettazione", f, 3) == "b"
    # spazio dentro una parola
    assert cf.livello_nella_pagina("Il contributo massimo", f, 2) == "c"
    assert cf.livello_nella_pagina("contributo minimo", f, 2) is None


@pytest.mark.parametrize(
    "valore, pagine",
    [("3 e 9", [3, 9]), (5, [5]), ("3-5", [3, 4, 5]), ("11, 14", [11, 14]), (None, [])],
)
def test_pagine_dichiarate(valore, pagine):
    assert cf.pagine_dichiarate(valore) == pagine


def test_pezzi_e_celle():
    assert cf.unita_della_frase("uno [...] due", False) == [["uno"], ["due"]]
    assert cf.unita_della_frase("A1 | 20% [...] A2 | 30%", True) == [
        ["A1", "20%"],
        ["A2", "30%"],
    ]


# --- presenza e pagina ---


def test_trovata_nella_pagina_dichiarata(archivio):
    e = controlla(fatto("Possono presentare domanda i Comuni"), archivio)
    assert (e["esito"], e["livello"], e["problemi"]) == (cf.TROVATA, "a", "")


def test_pagina_diversa(archivio):
    e = controlla(fatto("Possono presentare domanda i Comuni", pagina="3"), archivio)
    assert e["esito"] == cf.PAGINA_DIVERSA
    assert "p. 1" in e["trovata_in"]
    assert cf.PAGINA_DIVERSA in e["problemi"]


def test_pagina_tra_piu_dichiarate(archivio):
    e = controlla(fatto("Sono ammesse le spese", pagina="1 e 3"), archivio)
    assert e["esito"] == cf.TROVATA


def test_frase_in_piu_pezzi(archivio):
    e = controlla(
        fatto("Art. 3 Beneficiari [...] Art. 7 Spese", pagina="1 e 3"), archivio
    )
    assert (e["esito"], e["pezzi"]) == (cf.TROVATA, 2)


def test_in_altro_bando(archivio):
    e = controlla(fatto("ammesse fino al 10%"), archivio)
    assert e["esito"] == cf.ALTRO_BANDO


def test_assente_con_il_tratto_simile(archivio):
    e = controlla(
        fatto("Il contri buto massimo è di 50.000,00 euro", pagina="2"), archivio
    )
    assert e["esito"] == cf.ASSENTE
    assert "40.000,00" in e["tratto_simile"]
    assert "«4»→«5»" in e["differenza"]
    assert e["somiglianza"] > 0.9


def test_tratto_simile_senza_la_coda_della_finestra():
    tratto, _, differenza = cf.tratto_simile("di 50 euro", "spesa di 40 euro per tutti")
    assert tratto == "di 40 euro"
    assert differenza == "«4»→«5»"


def test_bando_senza_file(archivio):
    e = controlla(fatto("ammesse fino al 10%", id_bando="bando-zeta"), archivio)
    assert cf.SENZA_FILE in e["problemi"]
    assert e["esito"] == cf.ALTRO_BANDO


def test_proroga_non_e_un_file_del_bando(archivio):
    e = controlla(fatto("Proroga del termine"), archivio)
    assert e["esito"] != cf.TROVATA


# --- tabelle ---


def test_tabella_celle_sulla_stessa_pagina(archivio):
    e = controlla(fatto("Azione A1 | 20%", pagina="2", in_tabella="sì"), archivio)
    assert (e["esito"], e["celle"], e["celle_deboli"]) == (cf.TROVATA, 2, 1)
    assert e["celle_stessa_pagina"] == "sì"


def test_tabella_celle_su_pagine_diverse(archivio):
    e = controlla(
        fatto("Art. 3 Beneficiari | 30%", pagina="1", in_tabella="sì"), archivio
    )
    assert e["esito"] == cf.CELLE_SEPARATE
    assert e["celle_stessa_pagina"] == "no"
    assert cf.CELLE_SEPARATE in e["problemi"]


def test_tabella_celle_nello_stesso_frammento(archivio):
    frammenti = {
        "a" * 64: [
            cf.Frammento(0, 2, "Tabella 1\nAzione A1\n20%", 500),
            cf.Frammento(1, 2, "Azione A2\n30%", 500),
        ]
    }
    e = controlla(
        fatto("Azione A1 | 20%", pagina="2", in_tabella="sì"), archivio, frammenti
    )
    assert e["celle_stesso_frammento"] == "sì"
    e = controlla(
        fatto("Azione A1 | 30%", pagina="2", in_tabella="sì"), archivio, frammenti
    )
    assert e["celle_stesso_frammento"] == "no"


# --- apistici ---


@pytest.fixture
def apistici():
    pagina = (
        "Azione {a}\nIl contributo è del 50% della spesa ammessa.\nRisorse {r} euro.\n"
    )
    return [
        file_pdf("api", [pagina.format(a="B1", r="10.000")], sha="1" * 64,
                 parte="Azione B1", nome="a1.pdf"),
        file_pdf("api", [pagina.format(a="B3", r="20.000")], sha="3" * 64,
                 parte="Azione B3", nome="a3.pdf"),
    ]  # fmt: skip


def test_apistici_file_della_nota_e_altri_allegati(apistici):
    e = controlla(
        fatto(
            "del 50% della spesa",
            id_bando="api",
            note="Azione B1 (Allegato A1). x",
            solo="no",
        ),
        apistici,
    )
    assert e["file_della_nota"] == "a1.pdf"
    assert e["altri_allegati"] == "Azione B3"
    assert (e["esito"], e["gemelli"]) == (cf.TROVATA, "coerente")


def test_apistici_frase_di_un_altro_allegato(apistici):
    e = controlla(
        fatto("Risorse 20.000 euro", id_bando="api", note="Azione B1 (Allegato A1). x"),
        apistici,
    )
    assert e["esito"] == cf.ALTRO_ALLEGATO


def test_apistici_con_il_nome_dell_azione_nel_registro(apistici):
    """Con la parte "Azione B1: <nome>" (registra_avvisi) il file della nota è lo stesso."""
    nomi = {"B1": "Lotta a parassiti e malattie", "B3": "Ripopolamento"}
    con_nome = [
        cf.FilePdf(
            f.sha256, f.id_bando, f.classe, f"{f.parte}: {nomi[f.parte[-2:]]}",
            f.nome_file, f.pagine,
        )
        for f in apistici
    ]  # fmt: skip
    e = controlla(
        fatto(
            "del 50% della spesa",
            id_bando="api",
            note="Azione B1 (Allegato A1). x",
            solo="no",
        ),
        con_nome,
    )
    assert e["file_della_nota"] == "a1.pdf"
    assert (e["esito"], e["gemelli"]) == (cf.TROVATA, "coerente")


# --- gemelli ---


def test_gemelli(archivio):
    archivio.append(file_pdf("bando-c", [PAGINA_1], sha="c" * 64))
    frase = "Possono presentare domanda i Comuni"
    e = controlla(fatto(frase, solo="sì"), archivio)
    assert e["altri_bandi"] == "bando-c"
    assert e["gemelli"] == "sì ma trovato altrove"
    assert "gemelli" in e["problemi"]
    e = controlla(fatto("Art. 7 Spese", pagina="3", solo="no"), archivio)
    assert e["gemelli"] == "no ma non trovato altrove"
    e = controlla(fatto(frase), archivio)
    assert (e["gemelli"], e["solo_calcolato"]) == ("vuoto, calcolato no", "no")


def test_pezzi_in_altri_bandi(archivio):
    archivio.append(file_pdf("bando-c", [PAGINA_1], sha="c" * 64))
    e = controlla(
        fatto("Art. 3 Beneficiari [...] Art. 7 Spese", pagina="1 e 3"), archivio
    )
    assert e["altri_bandi"] == ""
    assert e["pezzi_in_altri_bandi"] == "pezzo 1: bando-c || pezzo 2: -"


# --- frammenti ---


def test_posizione_sul_testo_vero():
    testo = "Art. 5\nIl  contri buto\nmassimo è di 40.000,00 euro"
    fr = cf.Frammento(0, 1, testo, 30)
    inizio, fine = cf.posizione(cf.livello_c("contributo massimo"), fr)
    assert testo[inizio:fine] == "contri buto\nmassimo"


def test_intero_e_parte_vista():
    testo = "Premessa lunga. " * 5 + "Il contributo massimo è di 40.000,00 euro."
    frammenti = [cf.Frammento(3, 1, testo, 50), cf.Frammento(4, 1, "altro testo", 50)]
    dentro = cf.nei_frammenti("Premessa lunga.", frammenti)
    assert [c for c, *_ in dentro.interi] == [3] and dentro.visto
    fuori = cf.nei_frammenti("40.000,00 euro", frammenti)
    assert fuori.interi and not fuori.visto
    _, inizio, fine, visti = fuori.interi[0]
    assert testo[inizio:fine] == "40.000,00 euro" and fine > visti


def test_spezzato_tra_due_frammenti_con_sovrapposizione():
    a = cf.Frammento(0, 1, "uno due tre quattro cinque", 100)
    b = cf.Frammento(1, 1, "quattro cinque sei sette", 100)
    risultato = cf.nei_frammenti("tre quattro cinque sei", [a, b])
    assert risultato.interi == [] and risultato.spezzato == (0, 1)


def test_frammenti_nel_controllo(archivio):
    frammenti = {"a" * 64: [cf.Frammento(0, 1, PAGINA_1, 60)]}
    e = controlla(fatto("Possono presentare domanda"), archivio, frammenti)
    assert (e["frammenti"], e["pezzi_interi"], e["pezzi_visti"]) == ("0", 1, 1)
    assert e["posizioni"] == "0:19-45/60"
    assert PAGINA_1[19:45] == "Possono presentare domanda"


def test_pezzo_in_nessun_frammento(archivio):
    e = controlla(fatto("Possono presentare domanda"), archivio, frammenti={})
    assert e["esito"] == cf.TROVATA
    assert e["problemi"] == "pezzo in nessun frammento"


# --- domanda e contatti ---


def test_numero_della_frase_nella_domanda(archivio):
    e = controlla(
        fatto("meno di 5.000 abitanti", domanda="Vale per i Comuni sotto 5.000?"),
        archivio,
    )
    assert e["numeri_della_frase_nella_domanda"] == "5.000"
    assert "numero della frase" in e["problemi"]


def test_contatti_nelle_note_mascherati(archivio):
    e = controlla(
        fatto("i Comuni", note="chiesto a tizio.caio@esempio.it, tel. 055 1234567"),
        archivio,
    )
    assert "tizio" not in e["contatti"] and "ti…[" in e["contatti"]
    assert "05…[" in e["contatti"]
    assert "email o telefono" in e["problemi"]


# --- foglio ---


def test_leggi_foglio_salta_le_righe_senza_frase(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    libro = openpyxl.Workbook()
    foglio = libro.active
    foglio.title = "fatti"
    foglio.append(["id_bando", "frase", "pagina_fisica"])
    foglio.append([" bando-a ", "una frase", 3])
    foglio.append(["bando-a", None, 4])
    foglio.append(["bando-b", "altra frase", "1 e 2"])
    percorso = tmp_path / "fatti.xlsx"
    libro.save(percorso)
    fatti = cf.leggi_foglio(percorso)
    assert [(f["riga"], f["id_bando"]) for f in fatti] == [
        (2, "bando-a"),
        (4, "bando-b"),
    ]


def test_riepilogo_e_tabella_per_bando(archivio):
    esiti = [
        controlla(fatto("Possono presentare domanda i Comuni"), archivio),
        controlla(fatto("ammesse fino al 10%"), archivio),
    ]
    righe = cf.riepilogo(esiti)
    assert righe[0] == "Fatti controllati: 2 (pezzi 2)"
    assert "in altro bando 1" in righe[2]
    tabella = cf.per_bando(esiti)
    assert tabella[2].startswith("| bando-a | 2 | 1 | 0 | 0 | 1 |")
    assert len(cf.con_problemi(esiti)) == 1


# --- secondo foglio ---


def test_nota_degli_apistici_nelle_due_forme():
    for nota in (
        "Azione B3 (Allegato A3). Par. 2",
        "Azione B3, Allegato A3, par. 3.3.",
    ):
        assert cf.NOTA_APISTICI.match(nota).groups() == ("B3", "A3")
    assert cf.NOTA_APISTICI.match("Azione B3, par. 3.3") is None


def test_apistici_con_la_nota_del_secondo_foglio(apistici):
    e = controlla(
        fatto(
            "del 50% della spesa",
            id_bando="api",
            note="Azione B1, Allegato A1, par. 8.1, tabella.",
            solo="no",
        ),
        apistici,
    )
    assert e["file_della_nota"] == "a1.pdf"
    assert e["altri_allegati"] == "Azione B3"


def test_coincidenze_con_un_altro_foglio():
    primo = [
        {"riga": 5, "frase": "Il contributo è di 40.000 euro"},
        {"riga": 6, "frase": "Sono ammesse le spese tecniche [...] entro il 10%"},
        {"riga": 7, "frase": "I Comuni con meno di 5.000 abitanti possono partecipare"},
        {"riga": 8, "frase": "La domanda si presenta entro il 30 giugno 2026"},
        {"riga": 9, "frase": "Testo che non c'entra"},
    ]
    nuovo = {
        "frase": "Il contributo   è di 40.000 euro [...] entro il 10% "
        "[...] Comuni con meno di 5.000 abitanti"
    }
    assert cf.coincidenze(nuovo, primo) == [
        (5, "pezzo identico"),
        (6, "pezzo identico"),
        (7, "contenuta"),
    ]
    assert cf.coincidenze({"frase": "Il contributo è di 40.000 euro"}, primo) == [
        (5, "frase identica")
    ]
    simile = cf.coincidenze(
        {"frase": "La domanda si presenta entro il 30 giugno 2025"}, primo
    )
    assert simile[0][0] == 8 and simile[0][1].startswith("simile 0.9")
