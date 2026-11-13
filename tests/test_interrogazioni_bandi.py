"""Interrogazioni sui bandi per tipo di ente, condizioni, sportello e dettaglio."""

import re
from datetime import date

import pytest

from src.database import interrogazioni_bandi as ib
from src.database.repertorio import _stato_bandi
from src.estrazione.beneficiari import TIPI_BENEFICIARIO
from tests.conftest import CON_DATI as COMUNE

UNIONE = "33333333333"
OGGI = date(2026, 11, 11)
BASE = "https://www.regione.toscana.it/-/"


class DataFissa(date):
    @classmethod
    def today(cls):
        return cls(OGGI.year, OGGI.month, OGGI.day)


@pytest.fixture
def db(conn, monkeypatch):
    """Il database di prova con un'Unione, una fonte e nessun bando."""
    monkeypatch.setattr(ib, "date", DataFissa)
    conn.execute(
        "INSERT INTO enti (codice_fiscale, nome, tipo, regione, provincia, fonte, "
        "verificato_il) VALUES (?, 'Unione di prova', 'unione', 'Toscana', "
        "'Pistoia', 'prova', '2026-01-01')",
        (UNIONE,),
    )
    conn.execute(
        "INSERT INTO fonti (codice, nome, url_base, schema_link, fonte, "
        "verificato_il) VALUES ('regione-toscana', 'Toscana', ?, '^/-/', 'prova', "
        "'2026-11-11')",
        (BASE,),
    )
    return conn


def bando(conn, id_bando, beneficiari=(), classificato=True, **campi):
    """Inserisce un bando aperto e le sue righe di beneficiari.

    beneficiari: (tipo, condizioni, soggetto) per ogni riga.
    """
    riga = {
        "id": id_bando,
        "titolo": f"Bando {id_bando}",
        "ente": "Regione Toscana",
        "beneficiari": "Soggetti del bando",
        "scadenza": "2026-12-31",
        "a_sportello": 0,
        "url": BASE + id_bando,
        "fonte": "prova",
        "codice_fonte": "regione-toscana",
        "verificato_il": "2026-11-11",
        "classificato_il": "2026-11-11" if classificato else None,
        **campi,
    }
    conn.execute(
        f"INSERT INTO bandi ({', '.join(riga)}) VALUES ({', '.join('?' for _ in riga)})",
        list(riga.values()),
    )
    for tipo, condizioni, soggetto in beneficiari:
        conn.execute(
            "INSERT INTO beneficiari_bando (id_bando, tipo, soggetto, condizioni, "
            "frase, origine) VALUES (?, ?, ?, ?, ?, ?)",
            (
                id_bando,
                tipo,
                soggetto,
                condizioni,
                f"frase {tipo}",
                "estrazione" if classificato else "ammette_comuni",
            ),
        )


def righe_del_bando(testo: str, id_bando: str) -> list[str]:
    """Le righe dell'elenco di un bando: l'URL chiude la riga."""
    return [r for r in testo.splitlines() if r.endswith(f"url: {BASE}{id_bando}")]


def senza_segnaposto(righe: list[str]) -> list[str]:
    """Le righe senza il segnaposto [#k] iniziale."""
    return [re.sub(r"^- \[#\d+\] ", "- ", r) for r in righe]


def test_ogni_tipo_ha_un_nome_breve():
    assert list(ib.NOMI_TIPI) == list(TIPI_BENEFICIARIO)


# --- per tipo di ente ---


def test_comune_vede_i_bandi_del_suo_tipo_e_per_requisito(db):
    bando(db, "per-comuni", [("comune", None, None)])
    bando(db, "per-unioni", [("unione_comuni", None, None)])
    bando(db, "musei", [("qualsiasi_soggetto", "titolare di un museo", "musei")])
    bando(db, "scaduto", [("comune", None, None)], scadenza="2026-01-01")

    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    assert righe_del_bando(testo, "per-comuni")
    assert righe_del_bando(testo, "musei")
    assert not righe_del_bando(testo, "per-unioni")
    assert not righe_del_bando(testo, "scaduto")
    assert "a cui un Comune può presentare domanda" in testo


def test_senza_condizioni_nessuna_etichetta(db):
    bando(db, "b", [("comune", None, None)])
    (riga,) = righe_del_bando(ib.bandi_aperti_per_ente(db, COMUNE).testo, "b")
    assert "ammesso" not in riga


def test_condizioni_come_requisito_e_soggetto_tra_parentesi(db):
    bando(db, "tpl", [("comune", "competente per il servizio di TPL", None)])
    bando(
        db,
        "musei",
        [("qualsiasi_soggetto", "titolare di un museo accreditato", "musei regionali")],
    )
    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    (tpl,) = righe_del_bando(testo, "tpl")
    assert "| ammesso se competente per il servizio di TPL |" in tpl
    (musei,) = righe_del_bando(testo, "musei")
    atteso = (
        "ammesso se titolare di un museo accreditato (nel bando: «musei regionali»)"
    )
    assert atteso in musei


def test_piu_condizioni_si_uniscono_con_oppure(db):
    bando(
        db,
        "b",
        [("comune", "sotto i 5.000 abitanti", None), ("qualsiasi_soggetto", "x", None)],
    )
    (riga,) = righe_del_bando(ib.bandi_aperti_per_ente(db, COMUNE).testo, "b")
    assert "ammesso se sotto i 5.000 abitanti oppure ammesso se x" in riga


RICERCA = "Soggetti pubblici e/o privati che operano nel campo della ricerca"


def test_soggetto_generico_con_condizioni_mostra_il_soggetto(db):
    bando(db, "ricerca", [("comune", "comprovata esperienza", RICERCA)])
    (riga,) = righe_del_bando(ib.bandi_aperti_per_ente(db, COMUNE).testo, "ricerca")
    assert f"| ammesso se comprovata esperienza (nel bando: «{RICERCA}») |" in riga


def test_soggetto_generico_senza_condizioni_ammesso_come(db):
    bando(db, "pubblici", [("comune", None, "soggetti pubblici o privati")])
    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo
    (riga,) = righe_del_bando(testo, "pubblici")
    assert "| ammesso come «soggetti pubblici o privati» nel bando |" in riga


def test_soggetto_non_generico_senza_condizioni_resta_senza_etichetta(db):
    bando(db, "b", [("comune", None, "Comuni toscani")])
    (riga,) = righe_del_bando(ib.bandi_aperti_per_ente(db, COMUNE).testo, "b")
    assert "ammesso" not in riga


def test_soggetto_generico_a_condizione_in_etichetta_e_nel_dettaglio(db):
    bando(
        db,
        "pubblici",
        [
            ("comune", None, "soggetti pubblici o privati"),
            ("terzo_settore", None, "ETS"),
        ],
        tema="ambiente",
    )
    testo = ib.bandi_per_tema(db, "ambiente").testo
    assert "[ammessi: Comuni (a condizione), terzo settore]" in testo

    dettaglio = ib.dettaglio_bando(db, "pubblici").testo
    assert "Comuni, ammesso come «soggetti pubblici o privati» nel bando" in dettaglio
    assert "terzo settore (frase del bando" in dettaglio


def test_unione_vede_i_non_classificati_dei_comuni_con_la_nota(db):
    bando(db, "migrato", [("comune", None, None)], classificato=False)
    bando(db, "migrato-non-comuni", classificato=False)
    bando(db, "classificato-comuni", [("comune", None, None)])
    bando(db, "per-unioni", [("unione_comuni", None, None)])

    testo = ib.bandi_aperti_per_ente(db, UNIONE).testo

    (migrato,) = righe_del_bando(testo, "migrato")
    assert ib.NOTA_UNIONE in migrato
    (unioni,) = righe_del_bando(testo, "per-unioni")
    assert ib.NOTA_UNIONE not in unioni
    assert not righe_del_bando(testo, "migrato-non-comuni")
    assert not righe_del_bando(testo, "classificato-comuni")
    assert "a cui un'Unione di Comuni può presentare domanda" in testo


def test_comune_non_ha_la_nota_sui_migrati(db):
    bando(db, "migrato", [("comune", None, None)], classificato=False)
    (riga,) = righe_del_bando(ib.bandi_aperti_per_ente(db, COMUNE).testo, "migrato")
    assert ib.NOTA_UNIONE not in riga


def test_in_scadenza_per_ente(db):
    bando(db, "presto", [("unione_comuni", None, None)], scadenza="2026-11-20")
    bando(db, "tardi", [("unione_comuni", None, None)], scadenza="2027-06-01")
    testo = ib.bandi_in_scadenza(db, UNIONE, 30).testo
    assert righe_del_bando(testo, "presto")
    assert not righe_del_bando(testo, "tardi")
    assert testo.startswith("Bandi per Unioni di Comuni in scadenza entro 30 giorni")


def test_ente_non_gestito(db):
    r = ib.bandi_aperti_per_ente(db, "99999999999")
    assert not r.trovato


def test_nessun_bando_aperto(db):
    r = ib.bandi_aperti_per_ente(db, UNIONE)
    assert not r.trovato
    assert r.testo.startswith("Nessun bando aperto per le Unioni di Comuni")


# --- sportello ---


def test_sportello_in_un_gruppo_separato_dopo_le_scadenze(db):
    bando(db, "sportello", [("comune", None, None)], a_sportello=1, scadenza=None)
    bando(db, "scadenza", [("comune", None, None)])
    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo
    righe = testo.splitlines()
    gruppo = righe.index("A sportello, finché ci sono risorse:")
    assert righe[gruppo - 1].endswith(BASE + "scadenza")
    assert righe[gruppo + 1].endswith(BASE + "sportello")


# --- scadenza non indicata: fuori dalle liste, da approfondire ---


def test_senza_scadenza_non_sta_nella_lista_ma_da_approfondire(db):
    bando(
        db, "senza", [("comune", None, None)], scadenza=None, pubblicato_il="2026-10-01"
    )
    bando(db, "sportello", [("comune", None, None)], a_sportello=1, scadenza=None)
    bando(db, "scadenza", [("comune", None, None)])

    r = ib.bandi_aperti_per_ente(db, COMUNE)
    righe = r.testo.splitlines()

    assert righe[0].endswith("2 in archivio:")
    assert righe[1].endswith(BASE + "scadenza")
    assert righe[2] == ib.GRUPPO_SPORTELLO
    assert righe[3].endswith(BASE + "sportello")
    assert len(righe) == 4
    assert not righe_del_bando(r.testo, "senza")
    assert [(a.titolo, a.problema) for a in r.da_approfondire] == [
        ("Bando senza", ib.PROBLEMA_SCADENZA)
    ]


def test_solo_bandi_senza_scadenza(db):
    bando(
        db, "senza", [("comune", None, None)], scadenza=None, pubblicato_il="2026-10-01"
    )

    r = ib.bandi_aperti_per_ente(db, COMUNE)

    assert not r.trovato
    assert r.testo == (
        "Nessun bando aperto con dati completi per i Comuni alla data del 2026-11-11."
    )
    assert r.fonti == []
    assert [a.url for a in r.da_approfondire] == [BASE + "senza"]


def test_per_beneficiario_senza_scadenza_da_approfondire(db):
    agricolo = [("impresa_agricola", None, None)]
    bando(db, "senza", agricolo, scadenza=None, pubblicato_il="2026-10-01")
    bando(db, "sportello", agricolo, a_sportello=1, scadenza=None)
    bando(db, "scadenza", agricolo)

    r = ib.bandi_per_beneficiario(db, "impresa_agricola")
    righe = r.testo.splitlines()

    assert righe[0] == (
        "Bandi aperti per imprese agricole (alla data del 2026-11-11), 2 in archivio:"
    )
    assert righe[1].endswith(BASE + "scadenza")
    assert righe[2] == ib.GRUPPO_SPORTELLO
    assert righe[3].endswith(BASE + "sportello")
    assert len(righe) == 4
    assert [a.titolo for a in r.da_approfondire] == ["Bando senza"]


def test_il_dettaglio_dice_che_la_scadenza_non_e_indicata(db):
    bando(db, "senza", [("comune", None, None)], scadenza=None)
    assert ib.SENZA_SCADENZA in ib.dettaglio_bando(db, "senza").testo


def test_stato_bandi_conta_a_parte_i_da_approfondire(db):
    comune = [("comune", None, None)]
    bando(db, "sportello", comune, a_sportello=1, scadenza=None)
    bando(db, "scadenza", comune)
    # da approfondire, recenti: senza scadenza, sportello esaurito, senza
    # beneficiari (per tutti gli enti)
    bando(db, "senza", comune, scadenza=None, pubblicato_il="2026-10-01")
    bando(
        db,
        "esaurito",
        comune,
        a_sportello=1,
        scadenza=None,
        titolo="Fondo 2025",
        pubblicato_il="2023-01-01",
    )
    bando(db, "muto", [], pubblicato_il="2026-10-01")
    # da approfondire ma vecchio: non si mostra e non si conta
    bando(db, "vecchio", comune, scadenza=None, titolo="Festival 2021")

    assert _stato_bandi(db, COMUNE) == (
        "bandi: 6 in archivio, di cui 2 aperti a cui un Comune può presentare "
        "domanda, più 3 da approfondire"
    )


VERIFICARE = "verificare la disponibilità delle risorse"


@pytest.mark.parametrize(
    ("scadenza", "pubblicato", "atteso"),
    [
        (None, "2026-03-01", f"a sportello, {VERIFICARE} (pubblicato il 2026-03-01)"),
        (None, None, f"a sportello, {VERIFICARE} (data di pubblicazione non indicata)"),
        ("2027-07-31", None, f"a sportello fino al 2027-07-31, {VERIFICARE}"),
        # chiude oggi: ancora aperto
        ("2026-11-11", None, f"a sportello fino al 2026-11-11, {VERIFICARE}"),
        # chiuso: nessun invito a verificare le risorse
        ("2026-11-10", None, "era a sportello fino al 2026-11-10"),
        ("2026-06-30", "2024-01-01", "era a sportello fino al 2026-06-30"),
    ],
)
def test_etichetta_sportello(scadenza, pubblicato, atteso):
    riga = {"scadenza": scadenza, "pubblicato_il": pubblicato}
    assert ib.stato_sportello(riga, "2026-11-11") == atteso


def test_sportello_vecchio_probabilmente_esaurito_ma_mostrato():
    riga = {"scadenza": None, "pubblicato_il": "2024-11-10"}
    assert ib.stato_sportello(riga, "2026-11-11").endswith(
        "(pubblicato il 2024-11-10) | pubblicato da oltre 2 anni: "
        "probabilmente esaurito"
    )
    # esattamente due anni: ancora nella soglia
    riga = {"scadenza": None, "pubblicato_il": "2024-11-11"}
    assert "esaurito" not in ib.stato_sportello(riga, "2026-11-11")


def test_sportello_vecchio_con_scadenza_senza_avviso():
    # con una data di chiusura lo sportello e' aperto fino a quella data
    riga = {"scadenza": "2026-12-31", "pubblicato_il": "2024-03-13"}
    assert ib.stato_sportello(riga, "2026-11-11") == (
        f"a sportello fino al 2026-12-31, {VERIFICARE}"
    )


# --- per tema, per beneficiario, dettaglio ---


def test_etichetta_tipi(db):
    bando(
        db,
        "b",
        [("comune", "sotto i 5.000 abitanti", None), ("impresa_agricola", None, None)],
        tema="agricoltura",
    )
    bando(
        db, "migrato", [("comune", None, None)], classificato=False, tema="agricoltura"
    )
    bando(db, "migrato-no", classificato=False, tema="agricoltura")
    testo = ib.bandi_per_tema(db, "agricoltura").testo

    (b,) = senza_segnaposto(righe_del_bando(testo, "b"))
    assert b.startswith("- [ammessi: Comuni (a condizione), imprese agricole]")
    (m,) = senza_segnaposto(righe_del_bando(testo, "migrato"))
    assert m.startswith(
        "- [ammessi: Comuni; altri beneficiari non ancora classificati]"
    )
    (n,) = senza_segnaposto(righe_del_bando(testo, "migrato-no"))
    assert n.startswith(
        "- [NON per i Comuni; altri beneficiari non ancora classificati]"
    )


def test_per_beneficiario(db):
    bando(db, "agricolo", [("impresa_agricola", "con sede in montagna", None)])
    bando(db, "migrato", [("comune", None, None)], classificato=False)
    r = ib.bandi_per_beneficiario(db, "impresa_agricola")

    (riga,) = righe_del_bando(r.testo, "agricolo")
    assert "ammesso se con sede in montagna" in riga
    assert not righe_del_bando(r.testo, "migrato")
    assert "1 bandi aperti in archivio hanno beneficiari non ancora classificati" in (
        r.testo
    )


def test_per_beneficiario_tipo_sconosciuto(db):
    r = ib.bandi_per_beneficiario(db, "astronauti")
    assert not r.trovato
    assert "impresa_agricola (imprese agricole)" in r.testo


def test_dettaglio_con_beneficiari_interventi_e_cumulabilita(db):
    bando(
        db,
        "tpl",
        [("comune", "competente per il TPL", "Enti locali competenti")],
        cumulabilita="non cumulabile con altri contributi",
        cumulabilita_frase="Il contributo non è cumulabile",
    )
    db.execute(
        "INSERT INTO interventi_bando VALUES ('tpl', 1, 'spesa', 'acquisto autobus', "
        "'frase')"
    )
    testo = ib.dettaglio_bando(db, "tpl").testo

    assert (
        "beneficiari ammessi: Comuni, ammesso se competente per il TPL "
        "(frase del bando: «frase comune»)"
    ) in testo
    assert "interventi e spese ammissibili: spesa: acquisto autobus" in testo
    assert (
        "cumulabilità: non cumulabile con altri contributi "
        "(frase del bando: «Il contributo non è cumulabile»)"
    ) in testo


# --- riepilogo per il router ---


def test_stato_bandi_per_unione(db):
    bando(db, "migrato", [("comune", None, None)], classificato=False)
    bando(db, "per-unioni", [("unione_comuni", None, None)])
    bando(db, "scaduto", [("unione_comuni", None, None)], scadenza="2026-01-01")

    assert _stato_bandi(db, UNIONE) == (
        "bandi: 3 in archivio, di cui 2 aperti a cui un'Unione di Comuni può "
        "presentare domanda (1 con beneficiari non ancora classificati)"
    )
    assert _stato_bandi(db, COMUNE) == (
        "bandi: 3 in archivio, di cui 1 aperti a cui un Comune può presentare domanda"
    )


def test_dettaglio_dei_migrati_senza_la_frase_ripetuta(db):
    bando(db, "migrato", [("comune", None, None)], classificato=False)
    bando(db, "migrato-no", classificato=False)

    assert (
        "| beneficiari ammessi: Comuni; altri beneficiari non ancora classificati |"
        in ib.dettaglio_bando(db, "migrato").testo
    )
    assert (
        "| beneficiari ammessi: non i Comuni; altri beneficiari non ancora "
        "classificati |" in ib.dettaglio_bando(db, "migrato-no").testo
    )


# --- pagine in archivio che non sono bandi ---

NON_BANDO = {"natura": "non_bando", "natura_motivo": "graduatoria di un bando chiuso"}


def test_un_non_bando_non_compare_negli_elenchi(db):
    bando(db, "vero", [("comune", None, None)], tema="cultura")
    bando(db, "graduatoria", [("comune", None, None)], tema="cultura", **NON_BANDO)

    elenchi = [
        ib.bandi_aperti_per_ente(db, COMUNE).testo,
        ib.bandi_in_scadenza(db, COMUNE, 60).testo,
        ib.bandi_per_tema(db, "cultura").testo,
        ib.bandi_per_beneficiario(db, "comune").testo,
    ]
    for testo in elenchi:
        assert righe_del_bando(testo, "vero")
        assert not righe_del_bando(testo, "graduatoria")


def test_un_non_bando_non_si_conta(db):
    bando(db, "vero", [("comune", None, None)])
    bando(db, "graduatoria", [("comune", None, None)], **NON_BANDO)

    assert _stato_bandi(db, COMUNE) == (
        "bandi: 1 in archivio, di cui 1 aperti a cui un Comune può presentare domanda"
    )


def test_solo_non_bandi_aperti_vuol_dire_nessun_bando(db):
    bando(db, "graduatoria", [("comune", None, None)], **NON_BANDO)

    r = ib.bandi_aperti_per_ente(db, COMUNE)

    assert not r.trovato
    assert "ce ne sono 0 rivolti" in r.testo


def test_il_dettaglio_di_un_non_bando_dice_perche(db):
    bando(db, "graduatoria", [("comune", None, None)], **NON_BANDO)

    r = ib.dettaglio_bando(db, "graduatoria")

    assert r.testo == (
        "[#1] «Bando graduatoria» non e' un bando: graduatoria di un bando chiuso "
        f"| url: {BASE}graduatoria"
    )


# --- un'etichetta per bando ---


def test_ogni_riga_ha_il_suo_segnaposto_e_la_sua_voce(db):
    """La numerazione segue l'ordine delle righe, anche attraverso i gruppi."""
    bando(db, "sportello", [("comune", None, None)], a_sportello=1, scadenza=None)
    bando(db, "senza", [("comune", None, None)], scadenza=None)
    bando(db, "scadenza", [("comune", None, None)], riferimento_atto="decreto n. 1")

    r = ib.bandi_aperti_per_ente(db, COMUNE)

    # il bando senza scadenza non e' nella lista: non ha un segnaposto
    ordine = ["scadenza", "sportello"]
    for k, id_bando in enumerate(ordine, start=1):
        (riga,) = righe_del_bando(r.testo, id_bando)
        assert riga.startswith(f"- [#{k}] «Bando {id_bando}»")
        assert r.voci[k - 1].testo == riga.removeprefix(f"- [#{k}] ")
        assert r.voci[k - 1].fonte.startswith("prova, ")
    assert len(r.voci) == 2


def test_la_riga_del_bando_contiene_il_suo_atto(db):
    bando(db, "con-atto", [("comune", None, None)], riferimento_atto="decreto n. 18191")
    bando(db, "senza-atto", [("comune", None, None)])
    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    (con,) = righe_del_bando(testo, "con-atto")
    assert con.endswith(f"| atto: decreto n. 18191 | url: {BASE}con-atto")
    (senza,) = righe_del_bando(testo, "senza-atto")
    assert f"| atto: non indicato | url: {BASE}senza-atto" in senza


def test_il_dettaglio_e_una_sola_voce_con_l_atto_una_volta(db):
    bando(db, "b", [("comune", None, None)], riferimento_atto="decreto n. 7")
    r = ib.dettaglio_bando(db, "b")
    assert r.testo.startswith("[#1] «Bando b»")
    assert r.testo.count("atto: decreto n. 7") == 1
    assert [v.testo for v in r.voci] == [r.testo.removeprefix("[#1] ")]


# --- bandi a finestre o con piu' scadenze (oggi: 2026-11-11) ---

# Le quattro finestre di "dopo la laurea": la terza e' aperta oggi
FINESTRE_LAUREA = [
    ("domanda", "prima finestra", "2025-08-21", "2025-10-31"),
    ("domanda", "seconda finestra", "2026-06-15", "2026-07-15"),
    ("domanda", "terza finestra", "2026-11-11", "2026-12-11"),
    ("domanda", "quarta finestra", "2027-06-15", "2027-07-15"),
]


def scadenze(conn, id_bando, righe):
    """Inserisce le righe di scadenze_bando: (genere, descrizione, apertura, scadenza)."""
    for numero, (genere, descrizione, apertura, scadenza) in enumerate(righe, 1):
        conn.execute(
            "INSERT INTO scadenze_bando (id_bando, numero, genere, descrizione, "
            "apertura, scadenza, frase) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (id_bando, numero, genere, descrizione, apertura, scadenza, "frase"),
        )


def test_finestra_aperta_con_la_prossima(db):
    bando(db, "laurea", [("comune", None, None)], scadenza="2027-07-15")
    scadenze(db, "laurea", FINESTRE_LAUREA)

    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    assert testo.startswith("Bandi aperti a cui un Comune può presentare domanda")
    assert ib.GRUPPO_PROSSIMA not in testo
    (riga,) = righe_del_bando(testo, "laurea")
    assert (
        "| finestra aperta fino al 2026-12-11 (terza finestra, fra 30 giorni); "
        "prossima finestra dal 2027-06-15 al 2027-07-15 (quarta finestra) |"
    ) in riga


def test_tra_due_finestre_nel_gruppo_dei_chiusi_ora(db):
    bando(db, "laurea", [("comune", None, None)], scadenza="2027-07-15")
    scadenze(db, "laurea", [FINESTRE_LAUREA[1], FINESTRE_LAUREA[3]])
    bando(db, "aperto", [("comune", None, None)])

    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    assert "1 in archivio:" in testo
    gruppo = testo.split(ib.GRUPPO_PROSSIMA)[1]
    (riga,) = righe_del_bando(gruppo, "laurea")
    assert (
        "| chiuso ora, prossima finestra dal 2027-06-15 al 2027-07-15 "
        "(quarta finestra) |"
    ) in riga
    assert _stato_bandi(db, COMUNE) == (
        "bandi: 2 in archivio, di cui 1 aperti a cui un Comune può presentare "
        "domanda, più 1 chiusi ora, con una prossima finestra"
    )


def test_solo_bandi_tra_due_finestre(db):
    bando(db, "laurea", [("comune", None, None)], scadenza="2027-07-15")
    scadenze(db, "laurea", [FINESTRE_LAUREA[1], FINESTRE_LAUREA[3]])

    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    assert testo.startswith(
        "Nessun bando aperto ora per i Comuni alla data del 2026-11-11.\n"
        f"{ib.GRUPPO_PROSSIMA}"
    )


def test_tutte_le_finestre_passate_non_si_mostra(db):
    # bandi.scadenza futura per errore: lo stato si calcola dalle righe
    bando(db, "vecchio", [("comune", None, None)], scadenza="2027-07-15")
    scadenze(db, "vecchio", FINESTRE_LAUREA[:2])
    bando(db, "aperto", [("comune", None, None)])

    r = ib.bandi_aperti_per_ente(db, COMUNE)

    assert not righe_del_bando(r.testo, "vecchio")
    assert len(r.fonti) == 1


def test_in_scadenza_conta_la_finestra_aperta(db):
    # bandi.scadenza e' oltre i 60 giorni, ma la finestra aperta chiude prima
    bando(db, "laurea", [("comune", None, None)], scadenza="2027-07-15")
    scadenze(db, "laurea", FINESTRE_LAUREA)
    bando(db, "tra-finestre", [("comune", None, None)], scadenza="2027-07-15")
    scadenze(db, "tra-finestre", [FINESTRE_LAUREA[1], FINESTRE_LAUREA[3]])
    bando(db, "vicino", [("comune", None, None)], scadenza="2026-12-20")
    bando(db, "lontano", [("comune", None, None)], scadenza="2027-03-01")

    testo = ib.bandi_in_scadenza(db, COMUNE).testo

    assert righe_del_bando(testo, "laurea")
    assert righe_del_bando(testo, "vicino")
    assert not righe_del_bando(testo, "tra-finestre")
    assert not righe_del_bando(testo, "lontano")
    # in ordine di scadenza effettiva: 11/12 prima del 20/12
    assert testo.index("Bando laurea") < testo.index("Bando vicino")


def test_fase_successiva_solo_come_informazione(db):
    bando(db, "jtc", [("comune", None, None)], scadenza="2027-01-20")
    scadenze(
        db,
        "jtc",
        [
            ("domanda", "pre-proposta", None, "2027-01-20"),
            ("fase_successiva", "proposta completa", None, "2027-05-25"),
        ],
    )

    (riga,) = righe_del_bando(ib.bandi_aperti_per_ente(db, COMUNE).testo, "jtc")

    assert (
        "| finestra aperta fino al 2027-01-20 (pre-proposta, fra 70 giorni) |" in riga
    )
    assert (
        "| fase successiva, solo per chi ha superato la precedente: "
        "proposta completa entro il 2027-05-25 |"
    ) in riga

    dettaglio = ib.dettaglio_bando(db, "jtc").testo
    assert (
        "date del bando: pre-proposta (domanda), entro il 2027-01-20 "
        "(frase del bando: «frase»); proposta completa (fase successiva), "
        "entro il 2027-05-25"
    ) in dettaglio


def test_sportello_con_misure_a_scadenze_diverse(db):
    bando(db, "gol", [("comune", None, None)], a_sportello=1, scadenza="2027-06-30")
    scadenze(
        db,
        "gol",
        [
            ("domanda", "Misura 1", None, "2026-07-31"),
            ("domanda", "Misura 2", None, "2027-06-30"),
        ],
    )

    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    gruppo = testo.split(ib.GRUPPO_SPORTELLO)[1]
    (riga,) = righe_del_bando(gruppo, "gol")
    assert (
        "| finestra aperta fino al 2027-06-30 (Misura 2, fra 231 giorni), "
        f"a sportello: {VERIFICARE} |"
    ) in riga


@pytest.mark.parametrize(
    ("giorni", "atteso"),
    [
        (0, "oggi"),
        (1, "fra 1 giorno"),
        (2, "fra 2 giorni"),
        (-1, "SCADUTO da 1 giorno"),
        (-5, "SCADUTO da 5 giorni"),
    ],
)
def test_tra_quanto(giorni, atteso):
    assert ib.tra_quanto(giorni) == atteso


def test_scade_oggi_e_domani_nella_riga(db):
    bando(db, "oggi", [("comune", None, None)], scadenza="2026-11-11")
    bando(db, "domani", [("comune", None, None)], scadenza="2026-11-12")
    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    (oggi,) = righe_del_bando(testo, "oggi")
    assert "| scade il 2026-11-11 (oggi) |" in oggi
    (domani,) = righe_del_bando(testo, "domani")
    assert "| scade il 2026-11-12 (fra 1 giorno) |" in domani


# --- storico degli scaduti (piano fonti, tappa 3) ---

SCADUTO_DA_30 = "2026-10-12"


def _aperto_e_storico(db, **campi) -> None:
    """Un bando aperto e uno scaduto da 30 giorni, stessi tipi e tema."""
    tipi = [("comune", None, None), ("unione_comuni", None, None)]
    bando(db, "aperto", tipi, tema="ambiente", **campi)
    bando(db, "storico", tipi, tema="ambiente", scadenza=SCADUTO_DA_30)


def test_lo_storico_non_e_tra_gli_aperti_per_ente(db):
    _aperto_e_storico(db)
    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    assert righe_del_bando(testo, "aperto")
    assert not righe_del_bando(testo, "storico")


def test_lo_storico_non_e_tra_gli_aperti_per_beneficiario(db):
    _aperto_e_storico(db)
    testo = ib.bandi_per_beneficiario(db, "comune").testo

    assert righe_del_bando(testo, "aperto")
    assert not righe_del_bando(testo, "storico")


def test_lo_storico_non_e_in_scadenza(db):
    _aperto_e_storico(db, scadenza="2026-11-30")
    testo = ib.bandi_in_scadenza(db, COMUNE, 60).testo

    assert righe_del_bando(testo, "aperto")
    assert not righe_del_bando(testo, "storico")


def test_sportello_con_chiusura_passata_non_e_tra_gli_sportelli(db):
    bando(db, "chiuso", [("comune", None, None)], a_sportello=1, scadenza=SCADUTO_DA_30)
    bando(db, "aperto", [("comune", None, None)], a_sportello=1, scadenza=None)
    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    assert righe_del_bando(testo, "aperto")
    assert not righe_del_bando(testo, "chiuso")


def test_il_dettaglio_dello_storico_comincia_con_lo_stato(db):
    _aperto_e_storico(db)

    storico = ib.dettaglio_bando(db, "storico")
    aperto = ib.dettaglio_bando(db, "aperto")

    assert storico.trovato
    assert storico.testo.startswith(
        "[#1] stato: scaduto il 2026-10-12, non più aperto | «Bando storico»"
    )
    assert "SCADUTO da 30 giorni" in storico.testo
    assert "stato:" not in aperto.testo


def test_per_tema_lo_storico_sta_in_un_blocco_a_parte(db):
    _aperto_e_storico(db)
    r = ib.bandi_per_tema(db, "ambiente")
    prima, dopo = r.testo.split(ib.GRUPPO_STORICO)

    assert righe_del_bando(prima, "aperto")
    assert not righe_del_bando(prima, "storico")
    (storico,) = righe_del_bando(dopo, "storico")
    # la numerazione prosegue dopo gli aperti, e le fonti seguono lo stesso ordine
    assert storico.startswith("- [#2] ")
    assert [v.testo.split(" ")[-1] for v in r.voci] == [
        BASE + "aperto",
        BASE + "storico",
    ]
    assert len(r.fonti) == 2


def test_per_tema_solo_storico(db):
    bando(
        db, "storico", [("comune", None, None)], tema="ambiente", scadenza=SCADUTO_DA_30
    )
    r = ib.bandi_per_tema(db, "ambiente")

    assert ib.NESSUNO_APERTO_TEMA.format(oggi="2026-11-11") in r.testo
    assert righe_del_bando(r.testo.split(ib.GRUPPO_STORICO)[1], "storico")


def test_per_tema_senza_storico_nessun_blocco(db):
    bando(db, "aperto", [("comune", None, None)], tema="ambiente")
    assert ib.GRUPPO_STORICO not in ib.bandi_per_tema(db, "ambiente").testo


def test_una_finestra_futura_non_e_storico(db):
    """Un bando a piu' date con la scadenza passata ma una finestra futura
    non e' scaduto: segue le sue finestre."""
    bando(db, "finestre", [("comune", None, None)], scadenza=SCADUTO_DA_30)
    scadenze(
        db,
        "finestre",
        [
            ("domanda", "Prima finestra", "2026-09-01", SCADUTO_DA_30),
            ("domanda", "Seconda finestra", "2027-01-10", "2027-02-10"),
        ],
    )

    assert not ib.scaduto(
        db.execute("SELECT * FROM bandi WHERE id = 'finestre'").fetchone(),
        ib.scadenze_di(db, "finestre"),
        "2026-11-11",
    )
    assert "stato:" not in ib.dettaglio_bando(db, "finestre").testo


# --- per tema solo lo storico degli ultimi 12 mesi ---

# OGGI e' il 2026-11-11: 365 giorni prima e' il 2025-11-11, 366 il 2025-11-10
SUL_LIMITE = "2025-11-11"
OLTRE_IL_LIMITE = "2025-11-10"


def test_per_tema_lo_storico_si_ferma_a_dodici_mesi(db):
    tipi = [("comune", None, None)]
    bando(db, "aperto", tipi, tema="ambiente")
    bando(db, "limite", tipi, tema="ambiente", scadenza=SUL_LIMITE)
    bando(db, "vecchio", tipi, tema="ambiente", scadenza=OLTRE_IL_LIMITE)

    r = ib.bandi_per_tema(db, "ambiente")
    storico = r.testo.split(ib.GRUPPO_STORICO)[1]

    assert righe_del_bando(storico, "limite")
    assert not righe_del_bando(r.testo, "vecchio")
    assert len(r.fonti) == 2


def test_lo_scaduto_da_piu_di_un_anno_si_trova_per_nome(db):
    bando(
        db,
        "vecchio",
        [("comune", None, None)],
        tema="ambiente",
        scadenza=OLTRE_IL_LIMITE,
    )

    r = ib.dettaglio_bando(db, "vecchio")

    assert r.trovato
    assert r.testo.startswith("[#1] stato: scaduto il 2025-11-10, non più aperto |")


def test_tema_con_soli_scaduti_vecchi(db):
    """Nessun bando da elencare: lo si dice, senza blocco dello storico."""
    bando(
        db,
        "vecchio",
        [("comune", None, None)],
        tema="ambiente",
        scadenza=OLTRE_IL_LIMITE,
    )

    r = ib.bandi_per_tema(db, "ambiente")

    assert not r.trovato
    assert ib.NESSUNO_APERTO_TEMA.format(oggi="2026-11-11") in r.testo
    assert ib.GRUPPO_STORICO not in r.testo
    assert r.fonti == []


def test_il_dettaglio_di_uno_sportello_chiuso_non_invita_a_verificare(db):
    bando(db, "chiuso", [("comune", None, None)], a_sportello=1, scadenza="2026-06-30")

    testo = ib.dettaglio_bando(db, "chiuso").testo

    assert "| era a sportello fino al 2026-06-30 |" in testo
    assert VERIFICARE not in testo


# --- voce 5: contributo minimo e massimo, importi senza arrotondamento ---


@pytest.mark.parametrize(
    ("valore", "atteso"),
    [
        (1200000, "1.200.000"),
        (1200000.0, "1.200.000"),
        (84552097.68, "84.552.097,68"),
        (9188.49, "9.188,49"),
        (25449.6, "25.449,60"),
        (None, "?"),
    ],
)
def test_euro_senza_arrotondamento(valore, atteso):
    assert ib.euro(valore) == atteso


@pytest.mark.parametrize(
    ("campi", "atteso"),
    [
        (
            {"contributo_min": 20000, "contributo_max": 80000},
            "| contributo da 20.000 a 80.000 euro |",
        ),
        ({"contributo_max": 9188.49}, "| contributo fino a 9.188,49 euro |"),
        ({"contributo_min": 5000}, "| contributo da almeno 5.000 euro |"),
    ],
)
def test_contributo_nella_riga_e_nel_dettaglio(db, campi, atteso):
    bando(db, "importi", [("comune", None, None)], **campi)

    (riga,) = righe_del_bando(ib.bandi_aperti_per_ente(db, COMUNE).testo, "importi")
    assert atteso in riga
    assert atteso in ib.dettaglio_bando(db, "importi").testo


def test_senza_contributo_nessuna_voce(db):
    bando(db, "senza", [("comune", None, None)])
    assert "contributo da" not in ib.dettaglio_bando(db, "senza").testo


# --- voce 8: la data della fonte e' quella dell'estrazione ---


def test_la_fonte_dice_estratti_il(db):
    bando(db, "fonte", [("comune", None, None)], riferimento_atto="Decreto 1 del 2026")
    [fonte] = ib.dettaglio_bando(db, "fonte").fonti

    assert fonte == "prova, Decreto 1 del 2026 (dati estratti il 2026-11-11)"
    assert "verificati" not in fonte


# --- da approfondire ---

RIMANDO = "Nell'avviso pubblico sono indicati i requisiti"


def muto(db, id_bando, **campi):
    """Un bando salvato con i beneficiari vuoti: la pagina non li dice."""
    bando(db, id_bando, [], **campi)
    db.execute("UPDATE bandi SET beneficiari = NULL WHERE id = ?", (id_bando,))


def test_un_bando_senza_beneficiari_e_da_approfondire_per_tutti(db):
    muto(
        db,
        "muto",
        pubblicato_il="2026-10-01",
        beneficiari_rimando=RIMANDO,
        contatti="email: bandi@regione.toscana.it",
    )
    bando(db, "chiaro", [("comune", None, None)])

    for r in (
        ib.bandi_aperti_per_ente(db, COMUNE),
        ib.bandi_aperti_per_ente(db, UNIONE),
        ib.bandi_per_beneficiario(db, "impresa_agricola"),
        ib.bandi_per_beneficiario(db, "cittadini_famiglie"),
        ib.bandi_in_scadenza(db, COMUNE),
    ):
        assert not righe_del_bando(r.testo, "muto")
        assert [(a.titolo, a.problema, a.contatti) for a in r.da_approfondire] == [
            ("Bando muto", ib.PROBLEMA_RIMANDO, "email: bandi@regione.toscana.it")
        ]


def test_senza_rimando_il_problema_e_solo_beneficiari_non_indicati(db):
    muto(db, "muto", pubblicato_il="2026-10-01")

    (voce,) = ib.bandi_aperti_per_ente(db, COMUNE).da_approfondire

    assert voce.problema == ib.PROBLEMA_BENEFICIARI
    assert voce.contatti is None


def test_uno_sportello_probabilmente_esaurito_e_da_approfondire(db):
    bando(
        db,
        "vecchio",
        [("comune", None, None)],
        a_sportello=1,
        scadenza=None,
        titolo="Fondo rotativo 2025",
        pubblicato_il="2023-01-10",
    )

    r = ib.bandi_aperti_per_ente(db, COMUNE)

    assert not righe_del_bando(r.testo, "vecchio")
    assert [a.problema for a in r.da_approfondire] == [ib.PROBLEMA_ESAURITO]


@pytest.mark.parametrize(
    ("titolo", "pubblicato", "mostrato"),
    [
        ("Bando muto", "2024-11-11", True),  # esattamente due anni
        ("Bando muto", "2024-11-10", False),
        ("Bando muto", None, False),
        ("Festival 2021", None, False),
        ("Festival 2025", None, True),  # l'anno scorso
        ("Avviso 2023-2026", "2020-01-01", True),
    ],
)
def test_solo_i_bandi_recenti_sono_da_approfondire(db, titolo, pubblicato, mostrato):
    muto(db, "muto", titolo=titolo, pubblicato_il=pubblicato)

    r = ib.bandi_aperti_per_ente(db, COMUNE)

    assert bool(r.da_approfondire) == mostrato


def test_al_piu_dieci_da_approfondire_i_piu_recenti_in_cima(db):
    for giorno in range(1, 13):
        muto(
            db,
            f"muto{giorno:02d}",
            pubblicato_il=f"2026-10-{giorno:02d}",
        )

    voci = ib.bandi_aperti_per_ente(db, COMUNE).da_approfondire

    assert [v.titolo for v in voci] == [f"Bando muto{g:02d}" for g in range(12, 2, -1)]


def test_per_tema_gli_aperti_con_un_problema_sono_da_approfondire(db):
    muto(db, "muto", tema="cultura", pubblicato_il="2026-10-01")
    bando(db, "chiaro", [("comune", None, None)], tema="cultura")

    r = ib.bandi_per_tema(db, "cultura")

    assert righe_del_bando(r.testo, "chiaro")
    assert not righe_del_bando(r.testo, "muto")
    assert [a.titolo for a in r.da_approfondire] == ["Bando muto"]


def test_il_dettaglio_dice_problema_beneficiari_e_contatti(db):
    muto(
        db,
        "muto",
        pubblicato_il="2026-10-01",
        beneficiari_rimando=RIMANDO,
        contatti="email: bandi@regione.toscana.it",
    )

    testo = ib.dettaglio_bando(db, "muto").testo

    assert "| beneficiari: non indicati sulla pagina |" in testo
    assert (
        "beneficiari ammessi: non indicati sulla pagina; la pagina rimanda "
        f"all'avviso: «{RIMANDO}»"
    ) in testo
    assert "| contatti: email: bandi@regione.toscana.it" in testo
    assert f"| da approfondire: {ib.PROBLEMA_RIMANDO}" in testo


def test_il_dettaglio_di_un_bando_chiaro_non_ha_problemi_ne_contatti_vuoti(db):
    bando(db, "chiaro", [("comune", None, None)])

    testo = ib.dettaglio_bando(db, "chiaro").testo

    assert "da approfondire" not in testo
    assert "contatti:" not in testo


# --- dettaglio_bando: ricerca per titolo, piu' bandi, nessun bando ---


def test_l_identificativo_esatto_vince_sui_titoli(db):
    bando(db, "neve", titolo="Bando neve")
    bando(db, "neve-investimenti", titolo="Bando neve investimenti")

    r = ib.dettaglio_bando(db, "neve")

    assert r.trovato
    assert len(r.voci) == 1
    assert "«Bando neve»" in r.testo
    assert "Più bandi" not in r.testo


def test_due_bandi_danno_il_dettaglio_di_entrambi(db):
    bando(db, "funz", titolo="Bando Neve Spese di Funzionamento 2026")
    bando(db, "inv", titolo="Bando Neve Spese di Investimento 2026")

    r = ib.dettaglio_bando(db, "neve")

    righe = r.testo.splitlines()
    assert righe[0] == (
        "Più bandi corrispondono a 'neve' (2): ecco il dettaglio di tutti."
    )
    assert righe[1].startswith("[#1] «Bando Neve Spese di Funzionamento 2026»")
    assert righe[2].startswith("[#2] «Bando Neve Spese di Investimento 2026»")
    assert r.testo.count("dotazione complessiva") == 2
    assert r.trovato
    assert len(r.voci) == 2
    # Stessa fonte per i due bandi nel database di prova: non si ripete
    assert len(r.fonti) == 1


def test_tre_bandi_danno_ancora_i_dettagli(db):
    for numero in range(3):
        bando(db, f"c{numero}", titolo=f"Conciliazione vita-lavoro {numero}")

    r = ib.dettaglio_bando(db, "conciliazione")

    assert r.trovato
    assert r.testo.count("dotazione complessiva") == 3


def test_quattro_bandi_danno_l_elenco_senza_dettaglio(db):
    for numero in range(4):
        bando(db, f"c{numero}", titolo=f"Conciliazione vita-lavoro {numero}")

    r = ib.dettaglio_bando(db, "conciliazione")

    righe = r.testo.splitlines()
    assert righe[0] == (
        "Più bandi corrispondono a 'conciliazione' (4): nessuno è stato "
        "scelto. Per il dettaglio serve il titolo di uno di questi."
    )
    assert [riga[:7] for riga in righe[1:]] == [f"- [#{k}] " for k in (1, 2, 3, 4)]
    assert "dotazione complessiva" not in r.testo
    assert not r.trovato
    assert len(r.voci) == 4


def test_l_elenco_si_ferma_a_dieci(db):
    for numero in range(12):
        bando(db, f"f{numero:02}", titolo=f"Formazione continua {numero:02}")

    r = ib.dettaglio_bando(db, "formazione")

    assert len(r.voci) == ib.MAX_CORRISPONDENZE
    assert r.testo.endswith("E altri 2: il testo cercato è troppo generico.")


def test_l_elenco_dice_quali_bandi_sono_scaduti(db):
    for numero in range(4):
        bando(db, f"c{numero}", titolo=f"Conciliazione {numero}")
    db.execute("UPDATE bandi SET scadenza = '2026-10-01' WHERE id = 'c0'")

    r = ib.dettaglio_bando(db, "conciliazione")

    assert "- [#1] stato: scaduto il 2026-10-01, non più aperto |" in r.testo


def test_parole_in_ordine_diverso(db):
    bando(db, "sport", titolo="Bando Sport Missione Comune 2026")
    bando(db, "cultura", titolo="Cultura Missione Comune 2026")

    r = ib.dettaglio_bando(db, "Missione Comune Sport")

    assert len(r.voci) == 1
    assert "«Bando Sport Missione Comune 2026»" in r.testo


def test_parole_vuote_e_plurali(db):
    bando(db, "parcheggi", titolo="Bando parcheggi 2026")

    assert ib.dettaglio_bando(db, "il bando per il parcheggio").trovato


def test_senza_maiuscole_e_accenti(db):
    bando(db, "motoria", titolo="Contributi per l'Attività Motoria")

    assert len(ib.dettaglio_bando(db, "attivita motoria").voci) == 1


def test_nessun_bando_da_i_titoli_piu_simili(db):
    # 4 parole su 6 (ne mancano due: niente corrispondenza parziale), 3 su
    # 6, nessuna: il terzo resta fuori
    bando(db, "piste", titolo="Impianti di risalita, piste e rifugi 2025")
    bando(db, "neve", titolo="Impianti di innevamento e sentieri")
    bando(db, "parcheggi", titolo="Bando parcheggi 2026")
    cercato = "impianti di risalita, innevamento, piste, rifugi e sentieri"

    r = ib.dettaglio_bando(db, cercato)

    assert not r.trovato
    assert r.voci == []
    assert r.testo == (
        f"Nessun bando corrisponde a '{cercato}'. "
        "Titoli più simili in archivio, dal più vicino: "
        "«Impianti di risalita, piste e rifugi 2025» (id: piste); "
        "«Impianti di innevamento e sentieri» (id: neve)."
    )


def test_al_piu_cinque_titoli_simili(db):
    for numero in range(7):
        bando(db, f"i{numero}", titolo=f"Impianti sportivi {numero}")

    r = ib.dettaglio_bando(db, "impianti di risalita")

    assert r.testo.count("(id: i") == ib.MAX_SIMILI


def test_nessun_titolo_simile(db):
    bando(db, "parcheggi", titolo="Bando parcheggi 2026")

    r = ib.dettaglio_bando(db, "piste da sci")

    assert not r.trovato
    assert r.testo == (
        "Nessun bando corrisponde a 'piste da sci', e nessun titolo in "
        "archivio è simile."
    )


# --- corrispondenza parziale: un solo titolo a cui manca una parola ---

STRADE = "Fondo investimenti stradali nei piccoli Comuni - Avviso pubblico 2026"


def test_manca_una_parola_e_un_solo_titolo_dettaglio(db):
    bando(db, "strade", COMUNI, titolo=STRADE)
    bando(db, "parcheggi", titolo="Fondo parcheggi 2026")

    r = ib.dettaglio_bando(db, "fondo strade MIT piccoli comuni")

    righe = r.testo.splitlines()
    assert righe[0] == (
        "Corrispondenza parziale per 'fondo strade MIT piccoli comuni': il "
        "titolo non contiene 'MIT'."
    )
    assert righe[1].startswith(f"[#1] «{STRADE}»")
    assert "dotazione complessiva" in r.testo
    assert r.trovato
    assert len(r.voci) == 1


def test_manca_una_parola_a_pari_merito_titoli_simili(db):
    bando(db, "strade", titolo=STRADE)
    bando(db, "ponti", titolo="Fondo ponti nei piccoli Comuni")

    r = ib.dettaglio_bando(db, "fondo strade ponti piccoli comuni")

    assert not r.trovato
    assert r.voci == []
    assert r.testo.startswith(
        "Nessun bando corrisponde a 'fondo strade ponti piccoli comuni'. "
        "Titoli più simili in archivio"
    )
    assert "(id: strade)" in r.testo
    assert "(id: ponti)" in r.testo


def test_mancano_due_parole_titoli_simili(db):
    bando(db, "strade", titolo=STRADE)

    r = ib.dettaglio_bando(db, "fondo strade MIT ANAS piccoli comuni")

    assert not r.trovato
    assert r.testo == (
        "Nessun bando corrisponde a 'fondo strade MIT ANAS piccoli comuni'. "
        f"Titoli più simili in archivio, dal più vicino: «{STRADE}» (id: strade)."
    )


def test_con_due_parole_cercate_nessuna_corrispondenza_parziale(db):
    bando(db, "strade", titolo=STRADE)

    assert not ib.dettaglio_bando(db, "strade MIT").trovato


# --- ricerca fuori dal tema e fuori dal titolo ---

# Un beneficiario: senza, il bando va tra quelli da approfondire
COMUNI = [("comune", None, None)]


def test_tema_assente_cerca_nei_titoli(db):
    bando(
        db,
        "welfare",
        COMUNI,
        titolo="Conciliazione vita-lavoro: welfare",
        tema="sociale",
    )
    bando(db, "voucher", COMUNI, titolo="Conciliazione: voucher", tema="sociale")
    bando(db, "altro", titolo="Bando parcheggi", tema="territorio")

    r = ib.bandi_per_tema(db, "conciliazione")

    righe = r.testo.splitlines()
    assert righe[0] == (
        "Nessun bando con il tema 'conciliazione'; questi bandi lo nominano nel titolo:"
    )
    assert len(r.voci) == 2
    assert "parcheggi" not in r.testo
    assert r.trovato


def test_tema_presente_non_cerca_nei_titoli(db):
    bando(db, "a", COMUNI, titolo="Conciliazione", tema="sociale")
    bando(db, "b", COMUNI, titolo="Bando per la socialità", tema="cultura")

    r = ib.bandi_per_tema(db, "sociale")

    assert r.testo.startswith("Bandi sul tema 'sociale' in archivio:")
    assert len(r.voci) == 1


def test_tema_e_titoli_assenti(db):
    bando(db, "a", titolo="Bando parcheggi", tema="territorio")

    r = ib.bandi_per_tema(db, "conciliazione")

    assert not r.trovato
    assert r.testo.startswith("Nessun bando sul tema 'conciliazione'. Temi in")


def interventi(conn, id_bando, *descrizioni):
    for numero, descrizione in enumerate(descrizioni, start=1):
        conn.execute(
            "INSERT INTO interventi_bando (id_bando, numero, genere, descrizione, "
            "frase) VALUES (?, ?, 'intervento', ?, 'frase')",
            (id_bando, numero, descrizione),
        )


def test_un_bando_che_lo_nomina_nei_beneficiari(db):
    condizioni = "gestire impianti di risalita in Toscana"
    bando(db, "funz", [("impresa_turistica", condizioni, "Imprese")], titolo="Neve")
    bando(db, "altro", [("comune", None, None)], titolo="Parcheggi")

    r = ib.dettaglio_bando(db, "impianti di risalita")

    righe = r.testo.splitlines()
    assert righe[0] == (
        "Nessun titolo corrisponde a 'impianti di risalita'; questi bandi lo "
        "nominano nei beneficiari o negli interventi (1)."
    )
    assert righe[1].startswith("[#1] «Neve»")
    assert r.trovato
    assert len(r.voci) == 1


def test_due_bandi_tra_beneficiari_e_interventi(db):
    bando(db, "funz", [("impresa_turistica", "gestire impianti di risalita", None)])
    bando(db, "inv", titolo="Neve investimenti")
    interventi(db, "inv", "modernizzazione degli impianti di risalita")

    r = ib.dettaglio_bando(db, "impianti di risalita")

    assert r.testo.splitlines()[0] == (
        "Nessun titolo corrisponde a 'impianti di risalita'; questi bandi lo "
        "nominano nei beneficiari o negli interventi (2). Ecco il dettaglio di "
        "tutti."
    )
    assert r.testo.count("dotazione complessiva") == 2


def test_piu_di_tre_bandi_nel_testo_danno_l_elenco(db):
    for numero in range(4):
        bando(db, f"i{numero}", titolo=f"Bando {numero}")
        interventi(db, f"i{numero}", "impianti di risalita")

    r = ib.dettaglio_bando(db, "impianti di risalita")

    assert r.testo.splitlines()[0] == (
        "Nessun titolo corrisponde a 'impianti di risalita'; questi bandi lo "
        "nominano nei beneficiari o negli interventi (4). Nessuno è stato "
        "scelto. Per il dettaglio serve il titolo di uno di questi."
    )
    assert not r.trovato
    assert "dotazione complessiva" not in r.testo


def test_tutte_le_parole_nel_testo(db):
    bando(db, "funz", [("impresa_turistica", "gestire impianti sportivi", None)])
    interventi(db, "funz", "piste da sci")

    r = ib.dettaglio_bando(db, "impianti di risalita")

    assert r.testo.startswith("Nessun bando corrisponde a 'impianti di risalita'")


def test_il_titolo_ha_la_precedenza_sul_testo(db):
    bando(db, "titolo", titolo="Impianti di risalita 2026")
    bando(db, "testo", [("impresa_turistica", "gestire impianti di risalita", None)])

    r = ib.dettaglio_bando(db, "impianti di risalita")

    assert len(r.voci) == 1
    assert r.testo.startswith("[#1] «Impianti di risalita 2026»")


# --- sportelli con data di chiusura nelle scadenze (voce 12) ---


def test_sportello_con_chiusura_nella_finestra(db):
    bando(db, "sport", [("comune", None, None)], a_sportello=1, scadenza="2026-12-05")
    bando(db, "graduatoria", [("comune", None, None)], scadenza="2026-11-30")

    testo = ib.bandi_in_scadenza(db, COMUNE, 30).testo

    [riga] = righe_del_bando(testo, "sport")
    assert (
        "| a sportello, chiude il 2026-12-05 (fra 24 giorni), salvo esaurimento "
        "delle risorse |"
    ) in riga
    assert "verificare la disponibilità" not in riga
    # in ordine di chiusura, tra i bandi a graduatoria
    assert testo.index("Bando graduatoria") < testo.index("Bando sport")


def test_sportello_che_chiude_dopo_la_finestra(db):
    bando(db, "tardi", [("comune", None, None)], a_sportello=1, scadenza="2027-07-18")

    r = ib.bandi_in_scadenza(db, COMUNE, 30)

    assert not r.trovato


def test_sportello_senza_chiusura_resta_fuori(db):
    bando(db, "aperto", [("comune", None, None)], a_sportello=1, scadenza=None)

    assert not ib.bandi_in_scadenza(db, COMUNE, 30).trovato


def test_sportello_a_finestre_chiude_con_la_finestra_aperta(db):
    # Come Sport Missione Comune: finestra fino al 5/12, poi una fase
    # successiva che non riapre il bando
    bando(db, "coni", [("comune", None, None)], a_sportello=1, scadenza="2026-12-18")
    scadenze(
        db,
        "coni",
        [
            ("domanda", "istanza", "2026-03-09", "2026-12-05"),
            ("fase_successiva", "parere CONI", None, "2026-12-18"),
        ],
    )

    testo = ib.bandi_in_scadenza(db, COMUNE, 30).testo

    [riga] = righe_del_bando(testo, "coni")
    assert "a sportello, chiude il 2026-12-05 (fra 24 giorni)" in riga


def test_gli_altri_elenchi_non_cambiano_per_gli_sportelli(db):
    bando(db, "sport", [("comune", None, None)], a_sportello=1, scadenza="2026-12-05")

    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo

    assert (
        "a sportello fino al 2026-12-05, verificare la disponibilità delle risorse"
    ) in testo


def test_la_voce_porta_titolo_e_url_del_bando(db):
    bando(db, "parcheggi", COMUNI, titolo="Bando parcheggi 2026")

    (voce,) = ib.dettaglio_bando(db, "parcheggi").voci

    assert voce.titolo == "Bando parcheggi 2026"
    assert voce.url == BASE + "parcheggi"
