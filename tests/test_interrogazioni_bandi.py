"""Interrogazioni sui bandi per tipo di ente, condizioni, sportello e dettaglio."""

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

    (b,) = righe_del_bando(testo, "b")
    assert b.startswith("- [ammessi: Comuni (a condizione), imprese agricole]")
    (m,) = righe_del_bando(testo, "migrato")
    assert m.startswith(
        "- [ammessi: Comuni; altri beneficiari non ancora classificati]"
    )
    (n,) = righe_del_bando(testo, "migrato-no")
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
        "«Bando graduatoria» non e' un bando: graduatoria di un bando chiuso "
        f"| url: {BASE}graduatoria"
    )
