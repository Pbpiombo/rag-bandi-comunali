"""Ricognizione del Portale della Regione e letture attraverso Lettore.

Senza rete: le risposte vengono da ReteFinta (tests/test_lettore_siti.py)
o da pagine salvate in tmp_path. Il database e' quello temporaneo di
db_su_file, con fonti ed elenchi veri.
"""

import csv
import sqlite3
import sys
from datetime import date
from pathlib import Path

import pytest

import scripts.ingestione.estrai_nuovi as estrai_nuovi
import scripts.ingestione.ricognizione as ricognizione
from src.estrazione import elenco, registro
from src.estrazione.pdf_bando import INTESTAZIONI_PROGETTO
from src.estrazione.salva import salva
from tests.test_lettore_siti import Errore, ReteFinta

BASE = "https://www.regione.toscana.it"
ROBOTS = f"{BASE}/robots.txt"
ELENCO_REGIONE = f"{BASE}/bandi-aperti?delta=200"
ELENCO_MONTAGNA = f"{BASE}/politiche-per-la-montagna/bandi-aperti?delta=200"
OGGI = date(2026, 11, 23)

# Le regole del robots.txt della Regione salvato il 19/11/2026 che
# contano qui: "*/ricerca" vieta anche una pagina /-/ricerca-...
ROBOTS_REGIONE = b"User-Agent: *\nDisallow: */search\nDisallow: */ricerca\n"


def _url(slug: str) -> str:
    return f"{BASE}/-/{slug}"


def _pagina(scadenza: str) -> bytes:
    """Una pagina di bando con il campo della scadenza della Regione."""
    return (
        "<html><body><h1>Bando</h1>"
        "<p>Data di scadenza presentazione domande</p>"
        f"<p>{scadenza} 12:00</p></body></html>"
    ).encode()


def _elenco(*slug: str) -> bytes:
    voci = "".join(f'<a href="{_url(s)}">{s}</a>' for s in slug)
    return (
        f"<html><body><p>Risultati: {len(slug)} Bandi</p>{voci}</body></html>".encode()
    )


def _in_archivio(
    id_bando: str, slug: str, scadenza: str | None, a_sportello: int = 0
) -> None:
    salva(
        {
            "id": id_bando,
            "titolo": f"Bando {id_bando}",
            "ente": "Regione Toscana",
            "a_sportello": a_sportello,
            "beneficiari": "Comuni",
            "scadenza": scadenza,
        },
        _url(slug),
        "Portale bandi Regione Toscana",
        "regione-toscana",
    )


def _lettore(tmp_path, risposte: dict):
    rete = ReteFinta(risposte)
    lettore = elenco.lettore_della_scansione(tmp_path / "scansione", apri=rete)
    # nessuna attesa vera tra le richieste
    lettore._dormi = lambda secondi: None
    return lettore, rete


def _registro(lettore) -> list[dict]:
    with lettore.registro.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _gruppi(rapporto) -> dict[str, set[str]]:
    gruppi: dict[str, set[str]] = {}
    for r in rapporto.righe:
        gruppi.setdefault(r.gruppo, set()).add(r.id_bando)
    return gruppi


# --- letture attraverso Lettore ---


def test_un_indirizzo_vietato_non_si_richiede_e_va_nel_registro(db_su_file, tmp_path):
    _in_archivio("ricerca-finalizzata", "ricerca-finalizzata-2026", "2026-12-31")
    vietata = _url("ricerca-finalizzata-2026")
    lettore, rete = _lettore(
        tmp_path,
        {
            ROBOTS: ROBOTS_REGIONE,
            ELENCO_REGIONE: _elenco("ricerca-finalizzata-2026"),
            ELENCO_MONTAGNA: _elenco(),
        },
    )

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    assert vietata not in rete.url_chiamati()
    vietati = [r for r in _registro(lettore) if r["url"] == vietata]
    assert [r["esito"] for r in vietati] == ["vietato dal robots.txt"]
    assert _gruppi(rapporto)[ricognizione.VIETATI] == {"ricerca-finalizzata"}


def test_ogni_richiesta_porta_l_intestazione_del_progetto(db_su_file, tmp_path):
    _in_archivio("bando-uguale", "bando-uguale-2026", "2027-01-31")
    lettore, rete = _lettore(
        tmp_path,
        {
            ROBOTS: ROBOTS_REGIONE,
            ELENCO_REGIONE: _elenco("bando-uguale-2026"),
            ELENCO_MONTAGNA: _elenco(),
            _url("bando-uguale-2026"): _pagina("31.01.2027"),
        },
    )

    ricognizione.ricognisci(lettore, OGGI)

    assert len(rete.chiamate) == 4
    assert all(h == INTESTAZIONI_PROGETTO for _, h in rete.chiamate)
    assert "rag-bandi-comunali" in INTESTAZIONI_PROGETTO["User-Agent"]


def test_su_403_la_ricognizione_si_ferma(db_su_file, tmp_path):
    """Una pagina rifiutata ferma l'host: nessun'altra richiesta, mai con
    un'altra intestazione, e i bandi rimasti restano da verificare."""
    _in_archivio("bando-a", "bando-a-rifiutato", "2026-12-31")
    _in_archivio("bando-b", "bando-b-mai-chiesto", "2026-12-31")
    lettore, rete = _lettore(
        tmp_path,
        {
            ROBOTS: ROBOTS_REGIONE,
            ELENCO_REGIONE: _elenco("bando-a-rifiutato", "bando-b-mai-chiesto"),
            ELENCO_MONTAGNA: _elenco(),
            _url("bando-a-rifiutato"): Errore(403),
        },
    )

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    assert rapporto.interrotta
    assert _url("bando-b-mai-chiesto") not in rete.url_chiamati()
    assert rete.url_chiamati().count(_url("bando-a-rifiutato")) == 1
    da_verificare = [
        r for r in rapporto.righe if r.gruppo == ricognizione.DA_VERIFICARE
    ]
    assert {r.id_bando for r in da_verificare} == {"bando-a", "bando-b"}
    # spariti non calcolati su una corsa interrotta
    assert ricognizione.SPARITI not in _gruppi(rapporto)


def test_su_403_in_preselezione_estrai_nuovi_si_ferma(
    db_su_file, tmp_path, monkeypatch
):
    """Una pagina vietata non si richiede e non va al modello; dopo un 403
    nessun'altra pagina si richiede; nulla si registra in scansioni."""
    monkeypatch.setattr(sys, "argv", ["estrai_nuovi", "--fonte", "regione-toscana"])
    # gli elenchi conservati vanno in tmp_path, non in dati-grezzi
    monkeypatch.setattr(estrai_nuovi, "ELENCHI_DIR", tmp_path / "elenchi")
    lettore, rete = _lettore(
        tmp_path,
        {
            ROBOTS: ROBOTS_REGIONE,
            ELENCO_REGIONE: _elenco(
                "ricerca-vietata-2026", "bando-primo-rifiutato", "bando-secondo-mai"
            ),
            ELENCO_MONTAGNA: _elenco(),
            _url("bando-primo-rifiutato"): Errore(403),
        },
    )
    candidati = estrai_nuovi.scegli_candidati(lettore)

    al_modello, _ = estrai_nuovi.preseleziona(candidati, prova=False, lettore=lettore)

    assert al_modello == []
    assert elenco.da_fermare(lettore)
    assert _url("ricerca-vietata-2026") not in rete.url_chiamati()
    assert _url("bando-secondo-mai") not in rete.url_chiamati()
    assert sqlite3.connect(db_su_file).execute(
        "SELECT COUNT(*) FROM scansioni"
    ).fetchone() == (0,)


# --- ricognizione su pagine salvate ---


def _salva_pagina(cartella: Path, sotto: str, url: str, contenuto: bytes) -> None:
    percorso = cartella / sotto / f"{elenco.nome_file(url)}.html"
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_bytes(contenuto)


@pytest.fixture
def cartella_salvata(db_su_file, tmp_path):
    """Archivio con tre bandi della Regione e una cartella di pagine salvate.

    - bando-cambiato: in archivio 2026-12-01, la pagina dice 15.12.2026;
    - bando-scaduto: scaduto il 16/11, dopo la scansione del 13/11;
    - bando-uguale: stessa scadenza;
    - bando-nuovo-2026: nell'elenco, non in archivio.
    """
    _in_archivio("bando-cambiato", "bando-cambiato-2026", "2026-12-01")
    _in_archivio("bando-scaduto", "bando-scaduto-2026", "2026-11-16")
    _in_archivio("bando-uguale", "bando-uguale-2026", "2027-01-31")

    cartella = tmp_path / "salvate"
    _salva_pagina(
        cartella,
        "elenchi",
        ELENCO_REGIONE,
        _elenco("bando-cambiato-2026", "bando-uguale-2026", "bando-nuovo-2026"),
    )
    _salva_pagina(cartella, "elenchi", ELENCO_MONTAGNA, _elenco())
    for slug, scadenza in (
        ("bando-cambiato-2026", "15.12.2026"),
        ("bando-scaduto-2026", "16.11.2026"),
        ("bando-uguale-2026", "31.01.2027"),
    ):
        _salva_pagina(cartella, "pagine", _url(slug), _pagina(scadenza))
    return cartella


def test_cambiati_scaduti_e_nuovi_dalle_pagine_salvate(cartella_salvata):
    lettore = elenco.lettore_della_scansione(cartella_salvata, senza_rete=True)

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    gruppi = _gruppi(rapporto)
    assert gruppi[ricognizione.CAMBIATI] == {"bando-cambiato"}
    assert gruppi[ricognizione.SCADUTI] == {"bando-scaduto"}
    assert gruppi[ricognizione.NUOVI] == {"bando-nuovo-2026"}
    assert ricognizione.SPARITI not in gruppi
    assert not rapporto.interrotta
    [cambiato] = [r for r in rapporto.righe if r.gruppo == ricognizione.CAMBIATI]
    assert (cambiato.scadenza_archivio, cambiato.scadenza_pagina) == (
        "2026-12-01",
        "2026-12-15",
    )


def test_pagine_salvate_da_riga_di_comando_scrive_solo_il_rapporto(
    cartella_salvata, db_su_file, monkeypatch, capsys
):
    """--pagine-salvate: nessuna richiesta, il rapporto nella cartella, il
    database come prima."""
    prima = (
        sqlite3.connect(db_su_file)
        .execute("SELECT id, scadenza FROM bandi ORDER BY id")
        .fetchall()
    )
    monkeypatch.setattr(
        sys, "argv", ["ricognizione", "--pagine-salvate", str(cartella_salvata)]
    )
    monkeypatch.setattr(ricognizione, "data_di_oggi", lambda: OGGI)

    ricognizione.main()

    with (cartella_salvata / "ricognizione.csv").open(encoding="utf-8-sig") as f:
        righe = list(csv.DictReader(f))
    assert {(r["gruppo"], r["id_bando"]) for r in righe} >= {
        (ricognizione.CAMBIATI, "bando-cambiato"),
        (ricognizione.SCADUTI, "bando-scaduto"),
        (ricognizione.NUOVI, "bando-nuovo-2026"),
    }
    conn = sqlite3.connect(db_su_file)
    assert (
        conn.execute("SELECT id, scadenza FROM bandi ORDER BY id").fetchall() == prima
    )
    assert conn.execute("SELECT COUNT(*) FROM scansioni").fetchone() == (0,)
    assert "Richieste fatte ai siti: 0" in capsys.readouterr().out


def test_un_bando_nuovo_ha_la_scadenza_letta_dalla_sua_pagina(cartella_salvata):
    """La pagina di una voce nuova si legge: la scadenza del campo va nel
    rapporto; se il campo non si legge, "non leggibile"."""
    _salva_pagina(
        cartella_salvata, "pagine", _url("bando-nuovo-2026"), _pagina("20.12.2026")
    )
    _salva_pagina(
        cartella_salvata,
        "elenchi",
        ELENCO_MONTAGNA,
        _elenco("bando-senza-campo-2026"),
    )
    _salva_pagina(
        cartella_salvata,
        "pagine",
        _url("bando-senza-campo-2026"),
        b"<html><body><p>Bando senza il campo della scadenza</p></body></html>",
    )
    lettore = elenco.lettore_della_scansione(cartella_salvata, senza_rete=True)

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    nuovi = {
        r.id_bando: r.scadenza_pagina
        for r in rapporto.righe
        if r.gruppo == ricognizione.NUOVI
    }
    assert nuovi == {
        "bando-nuovo-2026": "2026-12-20",
        "bando-senza-campo-2026": ricognizione.NON_LEGGIBILE,
    }


# --- nota "possibile proroga" ---

ALLEGATO_PROROGA = (
    "https://www.regione.toscana.it/documents/10180/0/"
    "Decreto-Proroga-del-termine-ultimo-di-presentazione.pdf"
)


def _pagina_con(scadenza: str, corpo: str) -> bytes:
    """Una pagina con il campo della scadenza e un altro contenuto."""
    return _pagina(scadenza).replace(b"</body>", corpo.encode() + b"</body>")


def _note(rapporto, id_bando: str) -> dict[str, str]:
    return {r.gruppo: r.nota for r in rapporto.righe if r.id_bando == id_bando}


def test_proroga_nel_titolo_di_un_allegato_da_la_nota(cartella_salvata):
    """Il nome del file dice "Proroga", il testo del collegamento no: la
    nota c'e', con il nome del file; il bando, senza differenze, entra tra
    gli invariati. Una pagina senza quelle parole resta senza nota."""
    _salva_pagina(
        cartella_salvata,
        "pagine",
        _url("bando-uguale-2026"),
        _pagina_con("31.01.2027", f'<a href="{ALLEGATO_PROROGA}">Scarica</a>'),
    )
    lettore = elenco.lettore_della_scansione(cartella_salvata, senza_rete=True)

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    assert _note(rapporto, "bando-uguale") == {
        ricognizione.INVARIATI: "possibile proroga: "
        "Decreto-Proroga-del-termine-ultimo-di-presentazione.pdf"
    }
    assert "proroga" not in _note(rapporto, "bando-cambiato")[ricognizione.CAMBIATI]


def test_proroga_nel_testo_si_aggiunge_alla_nota_senza_cambiare_il_gruppo(
    cartella_salvata,
):
    _salva_pagina(
        cartella_salvata,
        "pagine",
        _url("bando-cambiato-2026"),
        _pagina_con(
            "15.12.2026",
            "<p>In evidenza: la scadenza è stata PROROGATA. Altre notizie.</p>",
        ),
    )
    lettore = elenco.lettore_della_scansione(cartella_salvata, senza_rete=True)

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    assert _note(rapporto, "bando-cambiato") == {
        ricognizione.CAMBIATI: "archivio 2026-12-01, pagina 2026-12-15; "
        "possibile proroga: In evidenza: la scadenza è stata PROROGATA."
    }


def test_improrogabile_non_da_la_nota(cartella_salvata):
    """ "Improrogabile" contiene "proroga" ma dice il contrario: e' la forma
    comune nei bandi ("termine perentorio e improrogabile")."""
    _salva_pagina(
        cartella_salvata,
        "pagine",
        _url("bando-uguale-2026"),
        _pagina_con(
            "31.01.2027",
            "<p>Le domande vanno presentate entro il termine perentorio e "
            "improrogabile indicato. Il termine non è prorogabile.</p>",
        ),
    )
    lettore = elenco.lettore_della_scansione(cartella_salvata, senza_rete=True)

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    assert _note(rapporto, "bando-uguale") == {}


# --- voci gia' viste, bandi a sportello, titoli ---


def _gia_vista(slug: str, motivo: str) -> None:
    registro.registra(_url(slug), "regione-toscana", slug, "scartato", motivo)


def test_una_voce_gia_scartata_non_e_tra_i_nuovi_e_non_si_richiede(
    db_su_file, tmp_path
):
    """Scartata per scadenza (2021) o perche' non e' un bando: esito
    definitivo. Va tra le gia' viste con il motivo di allora, e la sua
    pagina non si chiede: ReteFinta rifiuta ogni indirizzo non previsto."""
    _gia_vista("bando-vecchio-2021", "scaduto il 2021-10-30")
    _gia_vista("graduatoria-2025", "non e' un bando: graduatoria")
    lettore, rete = _lettore(
        tmp_path,
        {
            ROBOTS: ROBOTS_REGIONE,
            ELENCO_REGIONE: _elenco("bando-vecchio-2021", "graduatoria-2025"),
            ELENCO_MONTAGNA: _elenco(),
        },
    )

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    gruppi = _gruppi(rapporto)
    assert ricognizione.NUOVI not in gruppi
    assert gruppi[ricognizione.GIA_VISTE] == {"bando-vecchio-2021", "graduatoria-2025"}
    assert _url("bando-vecchio-2021") not in rete.url_chiamati()
    assert _url("graduatoria-2025") not in rete.url_chiamati()
    [vecchio] = [r for r in rapporto.righe if r.id_bando == "bando-vecchio-2021"]
    assert "scartato" in vecchio.nota and "scaduto il 2021-10-30" in vecchio.nota
    assert vecchio.scadenza_pagina == ""


def test_una_voce_con_esito_non_definitivo_si_rilegge(db_su_file, tmp_path):
    """ "Scadenza non determinata" non e' definitivo; uno scaduto da meno di
    GIORNI_FINESTRA giorni si rilegge per le proroghe. Le due pagine si
    chiedono e la scadenza letta va nella riga delle gia' viste."""
    _gia_vista("bando-incerto-2026", "scadenza non determinata")
    _gia_vista("bando-appena-scaduto-2026", "scaduto il 2026-11-01")
    lettore, rete = _lettore(
        tmp_path,
        {
            ROBOTS: ROBOTS_REGIONE,
            ELENCO_REGIONE: _elenco("bando-incerto-2026", "bando-appena-scaduto-2026"),
            ELENCO_MONTAGNA: _elenco(),
            _url("bando-incerto-2026"): _pagina("31.12.2026"),
            _url("bando-appena-scaduto-2026"): _pagina("15.12.2026"),
        },
    )

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    assert _url("bando-incerto-2026") in rete.url_chiamati()
    assert _url("bando-appena-scaduto-2026") in rete.url_chiamati()
    viste = {
        r.id_bando: r.scadenza_pagina
        for r in rapporto.righe
        if r.gruppo == ricognizione.GIA_VISTE
    }
    assert viste == {
        "bando-incerto-2026": "2026-12-31",
        "bando-appena-scaduto-2026": "2026-12-15",
    }


def test_un_bando_a_sportello_senza_campo_va_tra_gli_invariati(db_su_file, tmp_path):
    """A sportello in archivio, nessuna data nel campo della pagina: non
    e' da verificare, e' invariato con la nota "a sportello". Lo stesso
    caso, non a sportello, resta da verificare."""
    _in_archivio("sportello", "sportello-2026", None, a_sportello=1)
    _in_archivio("senza-campo", "senza-campo-2026", None)
    senza_campo = b"<html><body><p>Domande fino a esaurimento</p></body></html>"
    lettore, _ = _lettore(
        tmp_path,
        {
            ROBOTS: ROBOTS_REGIONE,
            ELENCO_REGIONE: _elenco("sportello-2026", "senza-campo-2026"),
            ELENCO_MONTAGNA: _elenco(),
            _url("sportello-2026"): senza_campo,
            _url("senza-campo-2026"): senza_campo,
        },
    )

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    assert _note(rapporto, "sportello") == {ricognizione.INVARIATI: "a sportello"}
    assert set(_note(rapporto, "senza-campo")) == {ricognizione.DA_VERIFICARE}


@pytest.mark.parametrize(
    ("slug", "titolo"),
    [
        # dagli elenchi della Regione letti il 23/11/2026
        (
            "riconoscimento-delle-attivit-c3-a0-di-formazione",
            "Riconoscimento delle attività di formazione",
        ),
        (
            "concorso-per-2-unit%C3%A0-di-istruttore",
            "Concorso per 2 unità di istruttore",
        ),
        ("2%c2%b0-bando-per-accoglienza", "2° bando per accoglienza"),
        ("selezione-per%C2%A0dirigente-medico", "Selezione per dirigente medico"),
        # parole che somigliano a byte restano parole
        ("bando-de-ab-2026", "Bando de ab 2026"),
    ],
)
def test_titolo_leggibile_decodifica_le_lettere_accentate(slug, titolo):
    assert ricognizione.titolo_leggibile(slug) == titolo
