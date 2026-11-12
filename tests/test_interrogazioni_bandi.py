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
        "INSERT INTO fonti VALUES ('regione-toscana', 'Toscana', ?, ?, 'prova', "
        "'2026-11-11')",
        (f"{BASE}elenco", BASE),
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


# --- scadenza non indicata ---


def test_senza_scadenza_in_un_gruppo_separato_dopo_lo_sportello(db):
    bando(db, "senza", [("comune", None, None)], scadenza=None)
    bando(db, "sportello", [("comune", None, None)], a_sportello=1, scadenza=None)
    bando(db, "scadenza", [("comune", None, None)])

    testo = ib.bandi_aperti_per_ente(db, COMUNE).testo
    righe = testo.splitlines()

    assert righe[0].endswith("2 in archivio:")
    assert righe[1].endswith(BASE + "scadenza")
    assert righe[2] == ib.GRUPPO_SPORTELLO
    assert righe[3].endswith(BASE + "sportello")
    assert righe[4] == "Scadenza non indicata, da verificare sul bando:"
    assert righe[5].endswith(BASE + "senza")
    assert "| scadenza non indicata, da verificare sul bando |" in righe[5]


def test_solo_bandi_senza_scadenza(db):
    bando(db, "senza", [("comune", None, None)], scadenza=None)

    r = ib.bandi_aperti_per_ente(db, COMUNE)

    assert r.trovato
    assert r.testo.startswith(
        "Nessun bando aperto di sicuro per i Comuni alla data del 2026-11-11"
    )
    assert righe_del_bando(r.testo, "senza")
    assert len(r.fonti) == 1


def test_per_beneficiario_con_i_tre_gruppi(db):
    agricolo = [("impresa_agricola", None, None)]
    bando(db, "senza", agricolo, scadenza=None)
    bando(db, "sportello", agricolo, a_sportello=1, scadenza=None)
    bando(db, "scadenza", agricolo)

    righe = ib.bandi_per_beneficiario(db, "impresa_agricola").testo.splitlines()

    assert righe[0] == (
        "Bandi aperti per imprese agricole (alla data del 2026-11-11), 2 in archivio:"
    )
    assert righe[1].endswith(BASE + "scadenza")
    assert righe[2] == ib.GRUPPO_SPORTELLO
    assert righe[3].endswith(BASE + "sportello")
    assert righe[4] == ib.GRUPPO_SENZA_SCADENZA
    assert righe[5].endswith(BASE + "senza")


def test_il_dettaglio_dice_che_la_scadenza_non_e_indicata(db):
    bando(db, "senza", [("comune", None, None)], scadenza=None)
    assert ib.SENZA_SCADENZA in ib.dettaglio_bando(db, "senza").testo


def test_stato_bandi_conta_a_parte_i_senza_scadenza(db):
    bando(db, "senza", [("comune", None, None)], scadenza=None)
    bando(db, "sportello", [("comune", None, None)], a_sportello=1, scadenza=None)
    bando(db, "scadenza", [("comune", None, None)])

    assert _stato_bandi(db, COMUNE) == (
        "bandi: 3 in archivio, di cui 2 aperti a cui un Comune può presentare "
        "domanda, più 1 con scadenza non indicata, da verificare sul bando"
    )


VERIFICARE = "verificare la disponibilità delle risorse"


@pytest.mark.parametrize(
    ("scadenza", "pubblicato", "atteso"),
    [
        (None, "2026-03-01", f"a sportello, {VERIFICARE} (pubblicato il 2026-03-01)"),
        (None, None, f"a sportello, {VERIFICARE} (data di pubblicazione non indicata)"),
        ("2027-07-31", None, f"a sportello fino al 2027-07-31, {VERIFICARE}"),
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

    ordine = ["scadenza", "sportello", "senza"]
    for k, id_bando in enumerate(ordine, start=1):
        (riga,) = righe_del_bando(r.testo, id_bando)
        assert riga.startswith(f"- [#{k}] «Bando {id_bando}»")
        assert r.voci[k - 1].testo == riga.removeprefix(f"- [#{k}] ")
        assert r.voci[k - 1].fonte.startswith("prova, ")
    assert len(r.voci) == 3


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
            "INSERT INTO scadenze_bando VALUES (?, ?, ?, ?, ?, ?, ?)",
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
