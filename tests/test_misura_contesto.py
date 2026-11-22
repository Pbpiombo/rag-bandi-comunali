"""Misura del contesto per frammento (scripts/diagnostica/misura_recupero_avvisi.py).

Tutto inventato: bandi, frammenti, fatti, contesti. Nessun PDF, nessun
Chroma, nessun modello.
"""

from collections import Counter

import pytest

import scripts.diagnostica.genera_contesti as gc
import scripts.diagnostica.misura_recupero_avvisi as mr
from scripts.diagnostica.controlla_fatti import Frammento

CONTESTO = (
    "BANDO: Bando prova, articolo 2.\n"
    "ARGOMENTO: chi può partecipare\n"
    "SERVE A: sapere se chi alleva api può chiedere il contributo."
)


def test_testo_con_contesto():
    meta = {"fonte": "a.pdf", "chunk_num": 3}
    assert mr.testo_con_contesto("testo", meta, {("a.pdf", 3): "ctx"}) == "ctx\ntesto"
    assert mr.testo_con_contesto("testo", meta, {("a.pdf", 4): "ctx"}) == "testo"
    assert mr.testo_con_contesto("testo", meta, None) == "testo"


class StoreFinto:
    """Solo la ricerca per parole conta: quella per significato non trova niente."""

    def __init__(self, testi):
        self.testi = testi

    def get(self):
        return {
            "ids": [f"id{i}" for i in range(len(self.testi))],
            "documents": self.testi,
            "metadatas": [
                {"fonte": "a.pdf", "chunk_num": i, "id_bando": "b", "titolo": "Prova"}
                for i in range(len(self.testi))
            ],
        }

    def similarity_search(self, query, k=4, filter=None):  # noqa: A002
        return []


def test_contesto_nella_ricerca_per_parole_e_frammento_pulito():
    testi = ["alfa beta", "gamma delta", "epsilon zeta"]
    contesti = {("a.pdf", 1): "apicoltura"}
    senza = mr.apri_recupero(None, store=StoreFinto(testi))
    assert senza.cerca_nel_bando("apicoltura", "b", 3) == []
    con = mr.apri_recupero(None, store=StoreFinto(testi), contesti=contesti)
    trovati = con.cerca_nel_bando("apicoltura", "b", 3)
    assert [d.page_content for d, _, _ in trovati] == ["gamma delta"]


def test_testo_per_riordino():
    from langchain_core.documents import Document

    d = Document(page_content="frammento", metadata={"fonte": "a.pdf", "chunk_num": 0})
    assert mr.testo_per_riordino(d, None) == "frammento"
    assert mr.testo_per_riordino(d, {("a.pdf", 0): "ctx"}) == "ctx\nframmento"


# --- contesti salvati -> contesti della misura ---


def documento(n=3):
    frammenti = [
        gc.FrammentoDaContestualizzare(
            f"a::{i}", i, f"Articolo 2. Testo {i} del bando."
        )
        for i in range(n)
    ]
    return gc.Documento(
        fonte="a.pdf",
        id_bando="b",
        titolo="Bando prova",
        atto="Decreto n. 123 del 01/02/2026",
        parte="",
        testo=" ".join(f.testo for f in frammenti),
        frammenti=frammenti,
    )


def salvato(testo=CONTESTO):
    righe = gc.righe_del_contesto(testo) or {}
    voci, libero, ignote = gc.voci_dell_argomento(righe.get("argomento", ""))
    return {
        "testo": testo,
        "righe": righe,
        "argomento_voci": voci,
        "argomento_altro": libero,
        "argomento_non_ricondotto": ignote,
        "stop_reason": "end_turn",
    }


def test_contesti_da_righe_e_violazioni(monkeypatch):
    monkeypatch.setattr(gc, "QUOTA_VIOLAZIONI", 0.5)
    d = documento()
    salvati = {f.id: salvato() for f in d.frammenti}
    salvati["a::2"] = salvato(CONTESTO.replace("api", "api dal 2019"))
    contesti, violazioni = mr.contesti_da([d], salvati, "tutte")
    assert set(violazioni) == {"a::2"}
    assert set(contesti) == {("a.pdf", 0), ("a.pdf", 1)}
    assert "chi può partecipare" in contesti[("a.pdf", 0)]
    senza, _ = mr.contesti_da([d], salvati, "senza-argomento")
    assert "chi può partecipare" not in senza[("a.pdf", 0)]
    assert "alleva api" in senza[("a.pdf", 0)]
    senza_serve, _ = mr.contesti_da([d], salvati, "senza-serve-a")
    assert "alleva" not in senza_serve[("a.pdf", 0)]


def test_contesti_da_ferma_oltre_la_quota_o_se_mancano():
    d = documento()
    salvati = {
        f.id: salvato(CONTESTO.replace("api", "api dal 2019")) for f in d.frammenti
    }
    with pytest.raises(mr.ErroreMisura, match="oltre il 5%"):
        mr.contesti_da([d], salvati, "tutte")
    del salvati["a::0"]
    with pytest.raises(mr.ErroreMisura, match="senza contesto"):
        mr.contesti_da([d], salvati, "tutte")


# --- domande a mano ---


def fatti_finti():
    conti = {"alfa": 20, "beta": 31, "gamma": 9, mr.ESCLUSO_MANO: 4, "delta": 33}
    fatti = []
    riga = 2
    for bando, n in conti.items():
        for _ in range(n):
            foglio = 1 if riga % 2 else 2
            numero = riga if foglio == 1 else riga + mr.SCOSTAMENTO_2
            fatti.append(
                {
                    "riga": numero,
                    "foglio": foglio,
                    "id_bando": bando,
                    "titolo": f"Bando {bando}",
                    "frase": f"Frase {riga}",
                    "domanda": f"Domanda del foglio {riga}",
                }
            )
            riga += 1
    return fatti


def test_scelta_a_mano():
    fatti = fatti_finti()
    scelti = mr.scelta_a_mano(fatti)
    assert len(scelti) == 30
    assert len({(f["foglio"], f["riga"]) for f in scelti}) == 30
    per_bando = Counter(f["id_bando"] for f in scelti)
    assert mr.ESCLUSO_MANO not in per_bando
    # 93 fatti: quote 6,45 / 10 / 2,90 / 10,65 -> 6, 10, 3, 11
    assert per_bando == {"alfa": 6, "beta": 10, "gamma": 3, "delta": 11}
    assert mr.scelta_a_mano(fatti) == scelti
    assert mr.scelta_a_mano(fatti, seme=1) != scelti


def test_righe_a_mano_senza_la_domanda_del_foglio():
    righe = mr.righe_a_mano(mr.scelta_a_mano(fatti_finti()))
    assert list(righe[0]) == mr.COLONNE_MANO
    assert all(r["domanda_a_mano"] == "" for r in righe)
    assert not any("Domanda del foglio" in str(v) for r in righe for v in r.values())
    assert all(r["riga"] < mr.SCOSTAMENTO_2 for r in righe)


def scrivi_mano(percorso, righe, separatore=";"):
    linee = [separatore.join(mr.COLONNE_MANO)]
    linee += [separatore.join(str(r[c]) for c in mr.COLONNE_MANO) for r in righe]
    percorso.write_text("\n".join(linee) + "\n", encoding="utf-8-sig")


def test_con_domande_a_mano(tmp_path):
    fatti = fatti_finti()
    righe = mr.righe_a_mano(mr.scelta_a_mano(fatti))
    for r in righe:
        r["domanda_a_mano"] = f"mia domanda {r['riga']}"
    percorso = tmp_path / "mano.csv"
    scrivi_mano(percorso, righe)
    uscita = mr.con_domande_a_mano(fatti, percorso)
    assert len(uscita) == 30
    assert all(f["domanda"].startswith("mia domanda") for f in uscita)
    assert {f["riga"] for f in uscita} <= {f["riga"] for f in fatti}
    righe[0]["domanda_a_mano"] = ""
    scrivi_mano(percorso, righe, ",")
    with pytest.raises(mr.ErroreMisura, match="vuote"):
        mr.con_domande_a_mano(fatti, percorso)
    righe[0]["domanda_a_mano"] = "x"
    righe[0]["frase"] = "un'altra frase"
    scrivi_mano(percorso, righe, ",")
    with pytest.raises(mr.ErroreMisura, match="frase"):
        mr.con_domande_a_mano(fatti, percorso)


# --- secondo file di domande a mano (21/11/2026) ---


def test_seconda_scelta_senza_i_fatti_della_prima():
    fatti = fatti_finti()
    primi = {mr.chiave_a_mano(f) for f in mr.scelta_a_mano(fatti)}
    secondi = mr.scelta_a_mano(fatti, seme=mr.SEME_MANO_2, esclusi=frozenset(primi))
    assert len(secondi) == 30
    assert not primi & {mr.chiave_a_mano(f) for f in secondi}
    assert mr.ESCLUSO_MANO not in {f["id_bando"] for f in secondi}
    assert mr.SEME_MANO_2 != mr.SEME_MANO
    assert secondi == mr.scelta_a_mano(
        fatti, seme=mr.SEME_MANO_2, esclusi=frozenset(primi)
    )


def test_prepara_il_secondo_file(tmp_path, monkeypatch):
    fatti = fatti_finti()
    monkeypatch.setattr(mr, "fatti_intera", lambda lato: (None, fatti, {}))
    monkeypatch.setattr(mr, "DOMANDE_A_MANO", tmp_path / "domande_a_mano.csv")
    monkeypatch.setattr(mr, "DOMANDE_A_MANO_2", tmp_path / "domande_a_mano_2.csv")
    with pytest.raises(mr.ErroreMisura, match="manca"):
        mr.esegui_prepara_a_mano(secondo=True)
    assert mr.esegui_prepara_a_mano() == 0
    assert mr.esegui_prepara_a_mano(secondo=True) == 0
    primo = mr.leggi_domande_a_mano(mr.DOMANDE_A_MANO)
    secondo = mr.leggi_domande_a_mano(mr.DOMANDE_A_MANO_2)
    assert list(secondo[0]) == mr.COLONNE_MANO
    assert len(secondo) == 30
    assert not {mr.chiave_a_mano(r) for r in primo} & {
        mr.chiave_a_mano(r) for r in secondo
    }
    # già scritto: non si sovrascrive, e le righe coincidono con la scelta
    assert mr.esegui_prepara_a_mano(secondo=True) == 0


def test_righe_vuote_saltate_con_un_avviso(tmp_path, capsys):
    fatti = fatti_finti()
    righe = mr.righe_a_mano(mr.scelta_a_mano(fatti))
    for r in righe[1:]:
        r["domanda_a_mano"] = f"mia domanda {r['riga']}"
    percorso = tmp_path / "mano.csv"
    scrivi_mano(percorso, righe)
    uscita = mr.con_domande_a_mano(fatti, percorso, salta_vuote=True)
    assert len(uscita) == 29
    avviso = capsys.readouterr().out
    assert f"foglio {righe[0]['foglio']} riga {righe[0]['riga']}" in avviso


def test_i_due_file_insieme(tmp_path):
    fatti = fatti_finti()
    prime = mr.righe_a_mano(mr.scelta_a_mano(fatti))
    esclusi = frozenset(mr.chiave_a_mano(r) for r in prime)
    seconde = mr.righe_a_mano(
        mr.scelta_a_mano(fatti, seme=mr.SEME_MANO_2, esclusi=esclusi)
    )
    for r in prime + seconde:
        r["domanda_a_mano"] = f"mia domanda {r['riga']}"
    seconde[0]["domanda_a_mano"] = ""
    uno, due = tmp_path / "uno.csv", tmp_path / "due.csv"
    scrivi_mano(uno, prime)
    scrivi_mano(due, seconde)
    assert len(mr.con_i_file_a_mano(fatti, (uno, due))) == 59
    # il secondo file non c'è ancora: si usa il primo
    assert len(mr.con_i_file_a_mano(fatti, (uno, tmp_path / "manca.csv"))) == 30
    scrivi_mano(due, prime)
    with pytest.raises(mr.ErroreMisura, match="già in un altro file"):
        mr.con_i_file_a_mano(fatti, (uno, due))


# --- contesto delle frasi, terzo file, copia .xlsx (21/11/2026 sera) ---


def test_testo_prima_e_dopo_senza_parole_tagliate():
    testo = "uno due tre quattro FRASE cinque sei sette otto"
    a = testo.index("FRASE")
    b = a + len("FRASE")
    assert mr.testo_prima(testo, a, 100) == "uno due tre quattro"
    assert mr.testo_dopo(testo, b, 100) == "cinque sei sette otto"
    # 10 caratteri: "e quattro " -> la parola "tre" tagliata si toglie
    assert mr.testo_prima(testo, a, 10) == "… quattro"
    assert mr.testo_dopo(testo, b, 9) == "cinque …"


def test_celle_di_una_tabella_in_ordine():
    testo = "1. Criterio uno (max 10 punti) 2. Criterio due (max 10 punti) dopo"
    fr = Frammento(-1, 0, testo, len(testo))
    a, b = mr.tratto_del_pezzo(["Criterio due", "(max 10 punti)"], fr)
    assert testo[a:b] == "Criterio due (max 10 punti)"
    # ogni cella per sé prende il primo "(max 10 punti)", prima del criterio
    assert mr.contiene(["Criterio due", "(max 10 punti)"], fr)[0] < a
    # celle in un altro ordine nel testo: come contiene
    assert mr.tratto_del_pezzo(["dopo", "Criterio uno"], fr) == mr.contiene(
        ["dopo", "Criterio uno"], fr
    )
    assert mr.tratto_del_pezzo(["assente"], fr) is None


def documenti_finti(fatti):
    testo = " ".join(
        f"Testo prima della frase. Frase {mr.riga_nel_foglio(f['riga'])} bis. "
        "Testo dopo la frase."
        for f in fatti
    )
    return [
        gc.Documento(
            fonte="a.pdf",
            id_bando="",
            titolo="Bando prova",
            atto="",
            parte="Azione B1",
            testo=testo,
        )
    ]


def per_bando_finto(fatti):
    return {
        b: [{"nome_file": "a.pdf", "parte": ""}] for b in {f["id_bando"] for f in fatti}
    }


def test_contesto_delle_frasi():
    fatti = fatti_finti()
    for f in fatti:
        f["frase"] = f"Frase {mr.riga_nel_foglio(f['riga'])} bis"
        f["pagina_fisica"] = 3.0
    fatti[0]["frase"] += " [...] " + fatti[5]["frase"]
    fatti[1]["frase"] = "una frase che nel testo non c'è"
    documenti = documenti_finti(fatti)
    contesti = mr.contesto_delle_frasi(fatti[:3], per_bando_finto(fatti), documenti)
    uno = contesti[mr.chiave_a_mano(fatti[2])]
    assert set(uno) == set(mr.COLONNE_CONTESTO)
    assert uno["file"] == "a.pdf (Azione B1)"
    assert uno["pagina"] == "3"
    assert uno["testo_prima"].endswith("Testo prima della frase.")
    assert uno["testo_dopo"].startswith(". Testo dopo la frase.")
    assert uno["spiegata"] == ""
    # due pezzi: un contesto per pezzo, il file una volta sola
    due = contesti[mr.chiave_a_mano(fatti[0])]
    assert due["file"] == "a.pdf (Azione B1)"
    assert due["testo_prima"].startswith("[pezzo 1] ")
    assert "\n\n[pezzo 2] " in due["testo_prima"]
    assert "\n\n[pezzo 2] " in due["testo_dopo"]
    assert contesti[mr.chiave_a_mano(fatti[1])]["file"] == mr.NON_TROVATA


def test_contesto_riscrive_solo_se_le_domande_sono_vuote(tmp_path, monkeypatch):
    fatti = fatti_finti()
    for f in fatti:
        f["frase"] = f"Frase {mr.riga_nel_foglio(f['riga'])} bis"
    monkeypatch.setattr(
        mr, "fatti_intera", lambda lato: (None, fatti, per_bando_finto(fatti))
    )
    monkeypatch.setattr(gc, "leggi_documenti", lambda: documenti_finti(fatti))
    righe = mr.righe_a_mano(mr.scelta_a_mano(fatti, seme=mr.SEME_MANO_2))
    due = tmp_path / "domande_a_mano_2.csv"
    mr.scrivi_csv_a_mano(due, righe, mr.COLONNE_MANO)
    assert mr.esegui_contesto_a_mano((due, tmp_path / "manca.csv")) == 0
    riscritte = mr.leggi_domande_a_mano(due)
    assert list(riscritte[0]) == mr.COLONNE_MANO_CONTESTO
    assert [mr.chiave_a_mano(r) for r in riscritte] == [
        mr.chiave_a_mano(r) for r in righe
    ]
    assert all(r["testo_prima"] and r["spiegata"] == "" for r in riscritte)
    copia = due.with_suffix(".xlsx")
    assert mr.leggi_domande_a_mano(copia) == riscritte
    # la misura legge il file con le colonne in più (qui la copia .xlsx)
    for r in riscritte:
        r["domanda_a_mano"] = f"mia domanda {r['riga']}"
    mr.scrivi_xlsx_a_mano(copia, riscritte, mr.COLONNE_MANO_CONTESTO)
    assert len(mr.con_i_file_a_mano(fatti, (due,))) == 30
    # una domanda compilata, nel .csv o nella copia: non si riscrive
    with pytest.raises(mr.ErroreMisura, match="già compilate"):
        mr.esegui_contesto_a_mano((due,))
    copia.unlink()
    riscritte[0]["domanda_a_mano"] = ""
    mr.scrivi_csv_a_mano(due, riscritte, mr.COLONNE_MANO_CONTESTO)
    with pytest.raises(mr.ErroreMisura, match="già compilate"):
        mr.esegui_contesto_a_mano((due,))


def test_terzo_file_con_tutti_i_rimanenti(tmp_path, monkeypatch, capsys):
    fatti = fatti_finti()
    monkeypatch.setattr(mr, "fatti_intera", lambda lato: (None, fatti, {}))
    percorsi = tuple(tmp_path / f"domande_a_mano{c}.csv" for c in ("", "_2", "_3"))
    for nome, p in zip(
        ("DOMANDE_A_MANO", "DOMANDE_A_MANO_2", "DOMANDE_A_MANO_3"),
        percorsi,
        strict=True,
    ):
        monkeypatch.setattr(mr, nome, p)
    assert mr.esegui_prepara_a_mano() == 0
    with pytest.raises(mr.ErroreMisura, match="manca"):
        mr.esegui_prepara_a_mano(terzo=True)
    assert mr.esegui_prepara_a_mano(secondo=True) == 0
    assert mr.esegui_prepara_a_mano(terzo=True) == 0
    assert "fuori per l'esclusione" in capsys.readouterr().out
    file = [mr.leggi_domande_a_mano(p) for p in percorsi]
    # 97 fatti, 4 del fondo strade: 93 - 30 - 30
    assert [len(f) for f in file] == [30, 30, 33]
    chiavi = [mr.chiave_a_mano(r) for f in file for r in f]
    assert len(set(chiavi)) == 93
    for p, righe in zip(percorsi, file, strict=True):
        for r in righe:
            r["domanda_a_mano"] = f"mia domanda {r['riga']}"
        mr.scrivi_csv_a_mano(p, righe, mr.COLONNE_MANO)
    assert len(mr.con_i_file_a_mano(fatti, percorsi)) == 93
    # un fatto due volte, tra due file o nello stesso: si ferma
    mr.scrivi_csv_a_mano(percorsi[2], file[2] + file[1][:1], mr.COLONNE_MANO)
    with pytest.raises(mr.ErroreMisura, match="già in un altro file"):
        mr.con_i_file_a_mano(fatti, percorsi)
    mr.scrivi_csv_a_mano(percorsi[2], file[2] + file[2][:1], mr.COLONNE_MANO)
    with pytest.raises(mr.ErroreMisura, match="due volte"):
        mr.con_i_file_a_mano(fatti, percorsi)


def test_copia_xlsx_testo_a_capo_e_letta_dalla_misura(tmp_path):
    from openpyxl import load_workbook

    fatti = fatti_finti()
    for f in fatti:
        f["frase"] = f"=1+{f['riga']} non è una formula"
    righe = mr.righe_a_mano(mr.scelta_a_mano(fatti))
    for r in righe:
        r["domanda_a_mano"] = f"mia domanda {r['riga']}\nsu due righe"
    csv_ = tmp_path / "mano.csv"
    copia = csv_.with_suffix(".xlsx")
    mr.scrivi_xlsx_a_mano(copia, righe, mr.COLONNE_MANO)
    foglio = load_workbook(copia).active
    assert foglio.freeze_panes == "A2"
    assert all(c.alignment.wrap_text for riga in foglio.iter_rows() for c in riga)
    assert all(c.data_type == "s" for riga in foglio.iter_rows() for c in riga)
    lette = mr.leggi_domande_a_mano(copia)
    assert [r["domanda_a_mano"] for r in lette] == [r["domanda_a_mano"] for r in righe]
    assert lette[0]["riga"] == str(righe[0]["riga"])
    # c'è solo la copia: la misura legge quella
    assert mr.file_da_leggere(csv_) == copia
    assert len(mr.con_i_file_a_mano(fatti, (csv_,))) == 30
    # anche il .csv con domande compilate: si ferma
    mr.scrivi_csv_a_mano(csv_, righe, mr.COLONNE_MANO)
    with pytest.raises(mr.ErroreMisura, match="una copia sola"):
        mr.con_i_file_a_mano(fatti, (csv_,))
    copia.unlink()
    assert mr.file_da_leggere(csv_) == csv_


# --- regole ---


def righe_b(trovati: list[bool]):
    return [
        {"riga": str(i), "B_trovato": "sì" if t else "no"}
        for i, t in enumerate(trovati)
    ]


def test_regola_di_adozione():
    base = {10: righe_b([False] * 20), 15: righe_b([False] * 20)}
    meglio = {
        10: righe_b([True] * 8 + [False] * 12),
        15: righe_b([True] * 8 + [False] * 12),
    }
    assert mr.adottabile(base, meglio)
    solo_k10 = {10: meglio[10], 15: righe_b([True] * 2 + [False] * 18)}
    assert not mr.adottabile(base, solo_k10)


def test_regola_delle_domande_a_mano():
    assert mr.esito_a_mano(4, 2) == "resta"
    assert mr.esito_a_mano(4, 1) == "si riduce"
    assert mr.esito_a_mano(4, 0) == "non resta"
    assert mr.esito_a_mano(4, -1) == "non resta"
    assert mr.esito_a_mano(0, 3).startswith("nessun guadagno")


# --- argomento contro tipo del fatto ---


def test_conta_argomenti():
    fr = [
        Frammento(0, 1, "Possono partecipare le aziende apistiche iscritte.", 999),
        Frammento(1, 1, "Il contributo massimo è di 5.000 euro.", 999),
    ]
    frammenti_per_fonte = {"a.pdf": fr}
    file_per_bando = {"b": [{"nome_file": "a.pdf", "parte": ""}]}
    fatti = [
        {
            "riga": 2,
            "id_bando": "b",
            "tipo_fatto": "chi può partecipare",
            "frase": "Possono partecipare le aziende apistiche iscritte.",
        },
        {
            "riga": 3,
            "id_bando": "b",
            "tipo_fatto": "importo o massimale (più punti)",
            "frase": "Il contributo massimo è di 5.000 euro.",
        },
        {
            "riga": 4,
            "id_bando": "b",
            "tipo_fatto": "procedura",
            "frase": "Frase che non sta in nessun frammento.",
        },
    ]
    id_di = {("a.pdf", 0): "a::0", ("a.pdf", 1): "a::1"}
    salvati = {
        "a::0": {"argomento_voci": ["chi può partecipare"]},
        "a::1": {"argomento_voci": ["spese ammesse o escluse"]},
    }
    esiti = mr.conta_argomenti(
        fatti, file_per_bando, frammenti_per_fonte, id_di, salvati, {}
    )
    per_riga = {e["riga"]: e for e in esiti}
    assert per_riga[2]["voce"] in per_riga[2]["primo"]
    assert per_riga[3]["voce"] == "importi e massimali"
    assert per_riga[3]["voce"] not in per_riga[3]["primo"]
    assert per_riga[4]["stato"] == "senza frammento"
    esclusi = mr.conta_argomenti(
        fatti, file_per_bando, frammenti_per_fonte, id_di, salvati, {"a::0": []}
    )
    assert esclusi[0]["stato"] == "contesto escluso"
    linee = mr.righe_argomenti(esiti)
    assert any("coincide nel primo frammento 1 su 2" in x for x in linee)


def test_parole_dal_contesto():
    fr = Frammento(0, 1, "Possono partecipare le aziende apistiche iscritte.", 999)
    fatto = {"riga": 2, "frase": "Possono partecipare le aziende apistiche iscritte."}
    righe = {"bando": "Bando prova", "serve_a": "sapere se chi alleva api partecipa"}
    _, solo = mr.parole_dal_contesto(
        fatto,
        "chi alleva api può partecipare",
        {"a.pdf"},
        {"a.pdf": [fr]},
        lambda fonte, chunk: righe,
    )
    assert "alleva" in solo["serve_a"]
    assert "partecipare" not in solo["serve_a"]
    assert solo["bando"] == []


def test_configurazioni_e_vettori():
    assert mr.nome_dei_vettori(mr.CONFIG_CONTESTO["c-LR"], "tutte") == "v0"
    nome = mr.nome_dei_vettori(mr.CONFIG_CONTESTO["c-LVR"], "senza-serve-a")
    assert mr.MODELLI[nome].limite == 512
    assert mr.MODELLI[nome].contesto == "senza-serve-a"
    assert mr.CONFIG_CONTESTO["c-0"].descrizione() == "contesto in: nessuna parte"


def test_rapporto_conta_le_righe_dei_fatti_guadagnati(tmp_path, monkeypatch):
    # sezione 5 con un fatto guadagnato in B le cui parole stanno solo nel
    # contesto: prima del 21/11/2026 Counter.update sommava le liste di parole
    def riga(trovato):
        return {
            "riga": "2",
            "id_bando": "b",
            "gemello": "no",
            "domanda_B": "chi alleva",
            "A_trovato": "no",
            "B_trovato": trovato,
            "A_primo_giusto": "",
            "B_primo_giusto": "1" if trovato == "sì" else "",
            "A_pezzo_dal_gemello": "no",
            "B_pezzo_dal_gemello": "no",
        }

    base = {k: [riga("no")] for k in mr.K_ESATTI}
    meglio = {k: [riga("sì")] for k in mr.K_ESATTI}
    misure = {("c-0", mr.NESSUNA): base, ("c-L", "tutte"): meglio}
    tempo = {"media": 0.1}
    for nome in ("c-0", "c-L"):
        (tmp_path / f"{nome}.json").write_text(
            '{"trovati_tra_i_candidati": {"A": 0, "B": 1}, "lunghezza_massima": 512,'
            ' "tempo_per_domanda_s": {"A": %s, "B": %s},'
            ' "coppie_troncate": {"A": 0, "B": 0}, "coppie": {"A": 1, "B": 1}}'
            % (str(tempo).replace("'", '"'), str(tempo).replace("'", '"')),
            encoding="utf-8",
        )
    monkeypatch.setattr(mr, "CARTELLA_CONTESTO", tmp_path)
    monkeypatch.setattr(
        mr, "misure_contesto", lambda lato, mano: {} if mano else misure
    )
    monkeypatch.setattr(mr, "file_contesto", lambda nome, *a: tmp_path / f"{nome}.csv")
    monkeypatch.setattr(mr, "file_riordino", lambda *a: tmp_path / "manca.csv")
    monkeypatch.setattr(mr, "leggi_contesti_generati", lambda: ([], {}))
    monkeypatch.setattr(mr, "contesti_della_misura", lambda *a: ({}, {}))
    fatto = {"riga": 2, "id_bando": "b", "domanda": "chi alleva"}
    monkeypatch.setattr(mr, "fatti_intera", lambda lato: (None, [fatto], {}))
    monkeypatch.setattr(mr, "frammenti_dei_vettori", lambda: ({}, {}))
    monkeypatch.setattr(mr, "documenti_del_fatto", lambda f, fb: ({"a.pdf"}, set()))
    monkeypatch.setattr(
        mr,
        "parole_dal_contesto",
        lambda *a: (
            [],
            {"serve_a": ["alleva", "api"], "parole": ["alleva"], "bando": []},
        ),
    )
    assert mr.esegui_rapporto_contesto(mr.TARATURA) == 0
    testo = (tmp_path / f"rapporto_contesto_{mr.TARATURA}.txt").read_text(
        encoding="utf-8"
    )
    for k in mr.K_ESATTI:
        assert (
            f"c-L tutte k={k}: guadagnati 1, con parole solo nel contesto 1; "
            "per riga: SERVE A 1, PAROLE 1"
        ) in testo
