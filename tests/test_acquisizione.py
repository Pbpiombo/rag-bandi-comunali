"""Registro delle scansioni, salvataggio dei bandi e lettura dell'elenco,
con gli URL in forma canonica."""

import importlib
import re
import sqlite3
import sys
from pathlib import Path

import pytest

import scripts.ingestione.estrai_bando as estrai_bando
import scripts.ingestione.estrai_nuovi as estrai_nuovi
import scripts.ingestione.scopri_bandi as scopri_bandi
from src.estrazione import elenco
from src.estrazione.indirizzi import url_canonico
from src.estrazione.registro import da_non_riesaminare, registra
from src.estrazione.salva import ConflittoBando, conflitto, salva

TOSCANA = "regione-toscana"
BASE = "https://www.regione.toscana.it"
FONTE = "Portale bandi Regione Toscana"
ELENCO_REGIONE = f"{BASE}/bandi-aperti?delta=200"
PAGINE = Path(__file__).parent / "pagine"

# Estratto dell'elenco del portale, con i link nella forma reale: slug
# con "/", con ".", con caratteri codificati (%C3%A0, %C2%A0), un link
# ripetuto, una voce di servizio da escludere.
ELENCO_SALVATO = """
<a href="https://www.regione.toscana.it/-/bando-parcheggi-2026">Parcheggi</a>
<a href="https://www.regione.toscana.it/-/avviso-pubblico-per-il-sostegno-allo-sport-per-l-annualit%C3%A0-2022">Sport</a>
<a href="https://www.regione.toscana.it/-/selezione-per%C2%A0dirigente-medico-disciplina-ortopedia">Selezione</a>
<a href="https://www.regione.toscana.it/-/manifestazione-di-interesse-per-il-reperimento-di-patrimonio-immobiliare-da-destinare-ad-emergenza-abitativa-e/o-residenza-sociale-1">Emergenza</a>
<a href="https://www.regione.toscana.it/-/presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo">Museo</a>
<a href="https://www.regione.toscana.it/-/presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo-2024">Museo 2024</a>
<a href="https://www.regione.toscana.it/-/bando-legalita-scuole-a.s.-2025-26">Legalita</a>
<a href="https://www.regione.toscana.it/-/bando-parcheggi-2026">Parcheggi, di nuovo</a>
<a href="https://www.regione.toscana.it/-/accessibilita-e-uso-del-sito">Accessibilita</a>
"""


def _leggi(percorso, sql: str, parametri=()) -> list[sqlite3.Row]:
    c = sqlite3.connect(percorso)
    c.row_factory = sqlite3.Row
    try:
        return c.execute(sql, parametri).fetchall()
    finally:
        c.close()


def _riga(titolo: str = "Bando di prova") -> dict:
    return {
        "titolo": titolo,
        "ente": "Regione Toscana",
        "ammette_comuni": 1,
        "a_sportello": 0,
        "beneficiari": "Comuni",
    }


def _salva(id_bando: str, url: str, titolo: str = "Bando di prova") -> None:
    salva({**_riga(titolo), "id": id_bando}, url, FONTE, TOSCANA)


# --- salva: i tre casi di id e URL ---


def test_stesso_id_e_stesso_url_aggiorna(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Prima versione")
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Seconda versione")

    righe = _leggi(db_su_file, "SELECT id, titolo, codice_fonte FROM bandi")
    assert [tuple(r) for r in righe] == [
        ("parcheggi-2026", "Seconda versione", TOSCANA)
    ]


def test_stesso_id_con_url_diverso_e_rifiutato(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Originale")

    with pytest.raises(ConflittoBando, match="parcheggi-2026"):
        _salva("parcheggi-2026", f"{BASE}/-/altro-bando", "Intruso")

    righe = _leggi(db_su_file, "SELECT id, url, titolo FROM bandi")
    assert [tuple(r) for r in righe] == [
        ("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Originale")
    ]


def test_stesso_url_con_id_diverso_e_rifiutato(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Originale")

    with pytest.raises(ConflittoBando, match="parcheggi-2026"):
        _salva("bando-parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026", "Intruso")

    righe = _leggi(db_su_file, "SELECT id, titolo FROM bandi")
    assert [tuple(r) for r in righe] == [("parcheggi-2026", "Originale")]


def test_il_conflitto_si_vede_anche_con_url_scritto_diversamente(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026")

    with pytest.raises(ConflittoBando):
        _salva("altro-id", "http://www.regione.toscana.it/-/bando-parcheggi-2026/")


def test_salva_scrive_url_canonico(db_su_file):
    _salva(
        "parcheggi-2026",
        "http://www.regione.toscana.it/-/bando-parcheggi-2026/?utm_source=x",
    )

    righe = _leggi(db_su_file, "SELECT url FROM bandi")
    assert righe[0]["url"] == f"{BASE}/-/bando-parcheggi-2026"


def test_conflitto_prima_di_salvare(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026")

    assert conflitto("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026") is None
    assert conflitto("nuovo-id", f"{BASE}/-/bando-nuovo") is None
    assert conflitto("parcheggi-2026", f"{BASE}/-/altro") is not None
    assert conflitto("altro-id", f"{BASE}/-/bando-parcheggi-2026/") is not None


# --- registro delle scansioni ---


def test_registra_due_volte_la_stessa_pagina_lascia_una_riga(db_su_file):
    registra(f"{BASE}/-/bando-x", TOSCANA, "bando-x", "fallito", "errore di rete")
    registra(
        f"{BASE}/-/bando-x/", TOSCANA, "bando-x", "scartato", "scaduto il 2025-01-01"
    )

    righe = _leggi(db_su_file, "SELECT url, esito, motivo FROM scansioni")
    assert [tuple(r) for r in righe] == [
        (f"{BASE}/-/bando-x", "scartato", "scaduto il 2025-01-01")
    ]


def test_da_non_riesaminare_restituisce_url_con_esito_definitivo(db_su_file):
    registra(
        f"{BASE}/-/scaduto", TOSCANA, "scaduto", "scartato", "scaduto il 2025-01-01"
    )
    registra(
        f"{BASE}/-/graduatoria",
        TOSCANA,
        "graduatoria",
        "scartato",
        "non e' un bando: graduatoria",
    )
    registra(
        f"{BASE}/-/incerto", TOSCANA, "incerto", "scartato", "scadenza non determinata"
    )
    registra(f"{BASE}/-/rotto", TOSCANA, "rotto", "fallito", "scaduto il 2025-01-01")

    assert da_non_riesaminare() == {f"{BASE}/-/scaduto", f"{BASE}/-/graduatoria"}


def test_gli_scarti_per_tipo_di_beneficiario_tornano_candidati(db_su_file):
    """I bandi si acquisiscono per ogni tipo di beneficiario: questi scarti
    delle scansioni passate non sono piu' definitivi."""
    registra(
        f"{BASE}/-/privati", TOSCANA, "privati", "scartato", "non ammette i Comuni"
    )
    registra(
        f"{BASE}/-/incerto",
        TOSCANA,
        "incerto",
        "scartato",
        "ammette_comuni a bassa confidenza",
    )

    assert da_non_riesaminare() == set()


def test_registra_conserva_motivo_e_avvisi_per_intero(db_su_file):
    motivo = "; ".join(f"campo_{i}: campo obbligatorio mancante" for i in range(10))
    avvisi = (
        "dotazione: valore '238.440,00 euro (con possibile incremento "
        "fino a 3.485.957,00 euro)' non convertibile, lasciato vuoto"
    )
    registra(f"{BASE}/-/bando-x", TOSCANA, "bando-x", "fallito", motivo, avvisi)

    riga = _leggi(db_su_file, "SELECT motivo, avvisi FROM scansioni")[0]
    assert len(motivo) > 100
    assert (riga["motivo"], riga["avvisi"]) == (motivo, avvisi)


def test_registra_senza_avvisi_lascia_la_colonna_vuota(db_su_file):
    registra(f"{BASE}/-/bando-x", TOSCANA, "bando-x", "scartato", "scaduto")
    assert _leggi(db_su_file, "SELECT avvisi FROM scansioni")[0]["avvisi"] is None


# --- lettura dell'elenco ---


@pytest.fixture
def elenco_salvato(monkeypatch):
    """L'elenco del portale letto dall'estratto salvato, non dal sito."""
    monkeypatch.setattr(elenco, "scarica", lambda url, timeout=30: ELENCO_SALVATO)


EMERGENZA = (
    "manifestazione-di-interesse-per-il-reperimento-di-patrimonio-"
    "immobiliare-da-destinare-ad-emergenza-abitativa-e/o-residenza-sociale-1"
)


def _slug_letti(url_elenco: str = ELENCO_REGIONE) -> list[str]:
    """Gli slug letti dall'elenco indicato, con le regole del database."""
    [letto] = [x for x in elenco.leggi_elenchi() if x.elenco.url == url_elenco]
    return [slug for slug, _ in letto.collegamenti]


def test_leggi_elenco_conserva_slug_interi(db_su_file, elenco_salvato):
    """Slug con "/", "." e caratteri codificati non vengono tagliati."""
    assert _slug_letti() == [
        "bando-parcheggi-2026",
        "avviso-pubblico-per-il-sostegno-allo-sport-per-l-annualit%C3%A0-2022",
        "selezione-per%C2%A0dirigente-medico-disciplina-ortopedia",
        EMERGENZA,
        "presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo",
        "presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo-2024",
        "bando-legalita-scuole-a.s.-2025-26",
    ]


def test_scopri_riconosce_i_bandi_in_archivio_per_url(db_su_file, elenco_salvato):
    """Il bando con "/" nello slug, salvato con un id nostro, non e' nuovo."""
    url_emergenza = f"{BASE}/-/{EMERGENZA}"
    _salva("immobili-emergenza-abitativa-2026", url_emergenza)

    voci = {v.url: v for v in elenco.scopri()}

    assert not voci[url_emergenza].nuovo
    assert voci[f"{BASE}/-/bando-parcheggi-2026"].nuovo
    assert all(v.codice_fonte == TOSCANA for v in voci.values())
    assert len(voci) == 7


def test_gia_in_archivio_restituisce_url_canonici(db_su_file):
    _salva("parcheggi-2026", f"{BASE}/-/bando-parcheggi-2026")
    assert elenco.gia_in_archivio() == {f"{BASE}/-/bando-parcheggi-2026"}


# --- identificativo ricavato dallo slug ---


def _url(slug: str) -> str:
    """L'URL canonico di una pagina del portale regionale con quello slug."""
    return url_canonico(f"{BASE}/-/{slug}")


def _id(slug: str) -> str:
    return elenco.id_da_slug(slug, _url(slug))


def test_id_da_slug_corto_resta_uguale():
    assert _id("bando-parcheggi-2026") == "bando-parcheggi-2026"


def test_id_da_slug_decodifica_e_toglie_accenti_barre_e_punti():
    assert _id("sport-annualit%C3%A0-2022") == "sport-annualita-2022"
    assert _id("selezione-per%C2%A0dirigente") == "selezione-per-dirigente"
    assert _id("museo/ecomuseo-2024") == "museo-ecomuseo-2024"
    assert _id("scuole-a.s.-2025-26") == "scuole-a-s-2025-26"


def test_id_da_slug_lungo_finisce_con_codice_dall_url():
    identificativo = _id(EMERGENZA)

    assert len(identificativo) <= elenco.LUNGHEZZA_ID
    assert re.fullmatch(r"[a-z0-9-]+-[0-9a-f]{6}", identificativo)
    assert identificativo.startswith("manifestazione-di-interesse-per-il-reper")
    assert _id(EMERGENZA) == identificativo


def test_slug_lunghi_con_lo_stesso_inizio_danno_id_diversi():
    """Le tre pagine museo/ecomuseo hanno i primi 60 caratteri uguali."""
    inizio = "presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo"
    slug = [f"{inizio}/ecomuseo", f"{inizio}/ecomuseo-2024", f"{inizio}/ecomuseo-x"]

    identificativi = {_id(s) for s in slug}

    assert len(identificativi) == 3
    assert all(len(i) <= elenco.LUNGHEZZA_ID for i in identificativi)


def test_id_da_slug_lunghi_non_vanno_in_conflitto_al_salvataggio(db_su_file):
    inizio = "presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo"
    for s in (f"{inizio}/ecomuseo", f"{inizio}/ecomuseo-2024"):
        url = _url(s)
        _salva(elenco.id_da_slug(s, url), url)

    assert len(_leggi(db_su_file, "SELECT id FROM bandi")) == 2


# --- scopri_bandi --comandi ---


def test_comandi_usano_il_percorso_giusto_del_modulo(
    db_su_file, elenco_salvato, monkeypatch, capsys
):
    monkeypatch.setattr(sys, "argv", ["scopri_bandi", "--comandi"])

    scopri_bandi.main()

    comandi = [
        r for r in capsys.readouterr().out.splitlines() if r.startswith("python -m")
    ]
    assert len(comandi) == 7
    for comando in comandi:
        _, _, modulo, url, identificativo = comando.split(" ")
        assert modulo == "scripts.ingestione.estrai_bando"
        assert url.startswith(f"{BASE}/-/")
        assert re.fullmatch(r"[a-z0-9-]{1,60}", identificativo)
    importlib.import_module(modulo)


# --- fonti, elenchi e regole lette dal database ---

URL_RURALE = f"{BASE}/sviluppo-rurale-2023-2027/bandi-aperti?delta=200"
RURALE = (PAGINE / "regione-sviluppo-rurale-bandi-aperti.html").read_text(
    encoding="utf-8"
)
BANDI_RURALE = [
    (
        "risorse-genetiche-forestali-contributi-per-conservazione-uso-e-sviluppo-"
        "sostenibile-il-bando-2026"
    ),
    (
        "contributi-per-uso-e-gestione-sostenibile-delle-risorse-genetiche-agrarie-"
        "specie-erbacee-specie-legnose-da-frutto-bovini-e-ovini-autoctoni"
    ),
    (
        "premi-annuali-ad-ettaro-per-mantenere-imboschimenti/forestazione-su-terreni-"
        "agricoli"
    ),
]
GAL = "gal-prova"
BASE_GAL = "https://www.gal-prova.it"


def _scrivi(percorso, sql: str, parametri=()) -> None:
    c = sqlite3.connect(percorso)
    try:
        c.execute("PRAGMA foreign_keys = ON")
        c.execute(sql, parametri)
        c.commit()
    finally:
        c.close()


def _elenco(percorso, url: str, codice: str = TOSCANA, attivo: int = 1) -> None:
    _scrivi(
        percorso,
        "INSERT INTO elenchi (url, codice_fonte, nome, attivo, fonte, verificato_il) "
        "VALUES (?, ?, 'prova', ?, 'prova', '2026-11-12')",
        (url, codice, attivo),
    )


def _fonte_gal(percorso) -> None:
    """Una seconda fonte di pagine, con regole diverse da quelle regionali."""
    _scrivi(
        percorso,
        "INSERT INTO fonti (codice, nome, tipo, url_base, schema_link, "
        "etichetta_scadenza, fonte, verificato_il) VALUES (?, 'GAL di prova', "
        "'pagine', ?, ?, 'Termine presentazione domande', 'prova', '2026-11-12')",
        (GAL, BASE_GAL, r"^/(?P<percorso>bando/(?P<slug>[a-z0-9-]+))/?$"),
    )


def _pagine(monkeypatch, pagine: dict) -> list[str]:
    """scarica restituisce l'HTML previsto per ogni indirizzo.

    Un indirizzo non previsto fa fallire il test; un valore che e' un
    errore viene sollevato. Restituisce gli indirizzi scaricati.
    """
    scaricati = []

    def finto(url, timeout=30):
        scaricati.append(url)
        risposta = pagine[url]
        if isinstance(risposta, Exception):
            raise risposta
        return risposta

    monkeypatch.setattr(elenco, "scarica", finto)
    return scaricati


def test_notizie_e_piede_di_pagina_esclusi(db_su_file, monkeypatch):
    """Le notizie di toscana-notizie.it hanno /-/ ma un altro dominio."""
    _elenco(db_su_file, URL_RURALE)
    _pagine(monkeypatch, {ELENCO_REGIONE: "", URL_RURALE: RURALE})

    assert _slug_letti(URL_RURALE) == BANDI_RURALE


def test_url_ricostruito_dal_percorso_della_fonte(db_su_file, monkeypatch):
    _elenco(db_su_file, URL_RURALE)
    _pagine(monkeypatch, {ELENCO_REGIONE: "", URL_RURALE: RURALE})

    [letto] = [x for x in elenco.leggi_elenchi() if x.elenco.url == URL_RURALE]

    assert [u for _, u in letto.collegamenti] == [_url(s) for s in BANDI_RURALE]


def test_collegamento_con_it_nel_percorso_e_relativo(db_su_file, monkeypatch):
    """/it/-/slug e /-/slug relativo danno lo stesso URL di quello assoluto."""
    html = (
        '<a href="/it/-/bando-parcheggi-2026">a</a>'
        '<a href="/-/bando-parcheggi-2026">b</a>'
        '<a href="http://regione.toscana.it/-/bando-sport-2026/">c</a>'
    )
    _pagine(monkeypatch, {ELENCO_REGIONE: html})

    [letto] = elenco.leggi_elenchi()

    assert letto.collegamenti == [
        ("bando-parcheggi-2026", _url("bando-parcheggi-2026")),
        ("bando-sport-2026", _url("bando-sport-2026")),
    ]


@pytest.mark.parametrize(
    "slug",
    [
        "accessibilita-e-uso-del-sito",
        "atti-di-notifica",
        "bandi-di-concorso-e-avvisi",
        "note-legali",
        "mappa-del-sito",
        "amministrazione-trasparente",
        "newsletter-della-giunta",
        "posta-elettronica-certificata-pec",
        (
            "tutela-del-dipendente-che-segnala-illeciti-whistleblower-la-disciplina-"
            "dal-15-luglio-2023"
        ),
    ],
)
def test_voci_di_servizio_escluse_dalle_regole(db_su_file, monkeypatch, slug):
    html = (
        f'<a href="{BASE}/-/{slug}">x</a><a href="{BASE}/-/bando-di-prova-2026">y</a>'
    )
    _pagine(monkeypatch, {ELENCO_REGIONE: html})

    assert _slug_letti() == ["bando-di-prova-2026"]


def test_le_voci_escluse_per_nome_intero_non_escludono_altri_slug(
    db_su_file, monkeypatch
):
    """'atti-di-notifica' e' escluso per intero, come prima: non per prefisso."""
    html = f'<a href="{BASE}/-/atti-di-notifica-contributi-2026">x</a>'
    _pagine(monkeypatch, {ELENCO_REGIONE: html})

    assert _slug_letti() == ["atti-di-notifica-contributi-2026"]


def test_stesso_bando_in_due_elenchi_della_stessa_fonte(db_su_file, monkeypatch):
    _elenco(db_su_file, URL_RURALE)
    _pagine(monkeypatch, {ELENCO_REGIONE: RURALE, URL_RURALE: RURALE})

    voci = elenco.scopri()

    assert [v.slug for v in voci] == BANDI_RURALE
    # la voce resta con l'elenco in cui e' comparsa per prima
    assert {v.elenco for v in voci} == {ELENCO_REGIONE}
    assert [v.posizione for v in voci] == [1, 2, 3]


def test_elenco_non_attivo_non_si_scarica(db_su_file, monkeypatch):
    _elenco(db_su_file, URL_RURALE, attivo=0)
    scaricati = _pagine(monkeypatch, {ELENCO_REGIONE: ELENCO_SALVATO})

    elenco.leggi_elenchi()

    assert scaricati == [ELENCO_REGIONE]


def test_ogni_fonte_con_le_sue_regole(db_su_file, monkeypatch):
    _fonte_gal(db_su_file)
    _elenco(db_su_file, f"{BASE_GAL}/bandi/", codice=GAL)
    pagina_gal = (
        '<a href="/bando/as01-investimenti/">AS01</a>'
        f'<a href="{BASE_GAL}/chi-siamo/">chi siamo</a>'
        f'<a href="{BASE_GAL}/wp-content/uploads/bando.pdf">bando</a>'
        f'<a href="{BASE}/-/bando-parcheggi-2026">un bando regionale</a>'
    )
    _pagine(
        monkeypatch, {ELENCO_REGIONE: ELENCO_SALVATO, f"{BASE_GAL}/bandi/": pagina_gal}
    )

    voci = elenco.scopri()
    del_gal = [v for v in voci if v.codice_fonte == GAL]

    assert [(v.slug, v.url) for v in del_gal] == [
        ("as01-investimenti", f"{BASE_GAL}/bando/as01-investimenti")
    ]
    assert del_gal[0].fonte.nome == "GAL di prova"
    assert del_gal[0].fonte.etichetta_scadenza == "Termine presentazione domande"
    assert not del_gal[0].fonte.filtro_anno_slug
    regionali = [v for v in voci if v.codice_fonte == TOSCANA]
    assert len(regionali) == 7
    assert all(v.fonte.filtro_anno_slug for v in regionali)


def test_fonte_di_tipo_file_non_si_scarica(db_su_file, monkeypatch):
    _scrivi(
        db_su_file,
        "INSERT INTO fonti (codice, nome, tipo, url_base, fonte, verificato_il) "
        "VALUES ('file-prova', 'File di prova', 'file', 'https://file-prova.it', "
        "'prova', '2026-11-12')",
    )
    # anche con un elenco attivo: una fonte 'file' non ha elenchi da leggere
    _elenco(db_su_file, "https://file-prova.it/open-data", codice="file-prova")
    scaricati = _pagine(monkeypatch, {ELENCO_REGIONE: ELENCO_SALVATO})

    voci = elenco.scopri()

    assert scaricati == [ELENCO_REGIONE]
    assert {v.codice_fonte for v in voci} == {TOSCANA}


def test_elenco_che_non_si_scarica_non_ferma_gli_altri(db_su_file, monkeypatch):
    _elenco(db_su_file, URL_RURALE)
    _pagine(monkeypatch, {ELENCO_REGIONE: OSError("timeout"), URL_RURALE: RURALE})

    letti = {x.elenco.url: x for x in elenco.leggi_elenchi()}

    assert letti[ELENCO_REGIONE].errore == "timeout"
    assert letti[ELENCO_REGIONE].collegamenti == []
    assert [s for s, _ in letti[URL_RURALE].collegamenti] == BANDI_RURALE


def test_sparito_solo_se_manca_da_tutti_gli_elenchi_della_fonte(
    db_su_file, monkeypatch
):
    _elenco(db_su_file, URL_RURALE)
    nel_secondo = _url(BANDI_RURALE[0])
    in_nessuno = _url("bando-chiuso-2025")
    _salva("nel-secondo", nel_secondo)
    _salva("in-nessuno", in_nessuno)
    _pagine(monkeypatch, {ELENCO_REGIONE: ELENCO_SALVATO, URL_RURALE: RURALE})

    assert scopri_bandi.spariti(elenco.leggi_elenchi()) == {in_nessuno}


def test_fonte_con_un_elenco_non_letto_non_si_confronta(db_su_file, monkeypatch):
    _elenco(db_su_file, URL_RURALE)
    _salva("in-nessuno", _url("bando-chiuso-2025"))
    _pagine(monkeypatch, {ELENCO_REGIONE: OSError("timeout"), URL_RURALE: RURALE})

    assert scopri_bandi.spariti(elenco.leggi_elenchi()) == set()


def test_fonte_di_dal_dominio(db_su_file):
    assert elenco.fonte_di(f"{BASE}/-/bando").codice == TOSCANA
    assert elenco.fonte_di("http://regione.toscana.it/-/bando").codice == TOSCANA
    assert elenco.fonte_di("https://www.toscana-notizie.it/-/notizia") is None


def test_estrai_bando_rifiuta_un_dominio_che_non_e_una_fonte(
    db_su_file, monkeypatch, tmp_path, capsys
):
    testo = tmp_path / "pagina.txt"
    testo.write_text("testo del bando", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["estrai_bando", str(testo), "https://altro.it/bando", "id"]
    )

    def nessun_modello():
        raise AssertionError("il modello non va chiamato")

    monkeypatch.setattr(estrai_bando, "costruisci_estrattore", nessun_modello)

    estrai_bando.main()

    assert "Nessuna fonte nel database" in capsys.readouterr().out


# --- preselezione con le regole della fonte ---


def _voce(slug: str, filtro_anno_slug: bool) -> elenco.Voce:
    fonte = elenco.Fonte(
        codice=TOSCANA,
        nome=FONTE,
        tipo="pagine",
        url_base=BASE,
        schema_link="^/-/",
        esclusi=None,
        etichetta_scadenza="Data di scadenza presentazione domande",
        filtro_anno_slug=filtro_anno_slug,
        scadenza_obbligatoria=False,
    )
    return elenco.Voce(
        slug=slug,
        url=_url(slug),
        codice_fonte=TOSCANA,
        titolo=slug,
        nuovo=True,
        promettente=False,
        anno=elenco.anno_slug(slug),
        recente=elenco.recente(slug),
        posizione=1,
        fonte=fonte,
        elenco=ELENCO_REGIONE,
    )


@pytest.fixture
def senza_rete(monkeypatch):
    """La preselezione legge la pagina indicata, senza pause."""

    def con_pagina(testo: str) -> None:
        monkeypatch.setattr(estrai_nuovi, "scarica", lambda url: testo)

    monkeypatch.setattr(estrai_nuovi.time, "sleep", lambda s: None)
    monkeypatch.setattr(sys, "argv", ["estrai_nuovi", "--prova"])
    return con_pagina


@pytest.mark.parametrize(("filtro", "al_modello"), [(True, 0), (False, 1)])
def test_il_filtro_sull_anno_e_una_regola_della_fonte(senza_rete, filtro, al_modello):
    """Una pagina senza campo e con un anno passato nello slug: la salta
    solo una fonte che usa il filtro."""
    senza_rete("pagina senza campo")

    candidati, _ = estrai_nuovi.preseleziona([_voce("bando-2019", filtro)], prova=True)

    assert len(candidati) == al_modello


def test_la_preselezione_legge_l_etichetta_della_fonte(senza_rete):
    senza_rete("Data di scadenza presentazione domande\n31.12.2020")

    voci = [_voce("bando-senza-anno", True)]
    candidati, _ = estrai_nuovi.preseleziona(voci, prova=True)

    # scaduto da oltre un anno secondo il campo: non va al modello
    assert candidati == []
