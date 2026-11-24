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
from src.estrazione import elenco, registro, sospensione
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
    """La decodifica sta in elenco._titolo_da_slug: vale per tutti gli
    script che usano le voci degli elenchi (scopri)."""
    assert elenco._titolo_da_slug(slug) == titolo


# --- finestre del bando (scadenze_bando) ---


def _finestra(db: Path, id_bando: str, numero: int, scadenza: str, genere="domanda"):
    conn = sqlite3.connect(db)
    conn.execute(
        "INSERT INTO scadenze_bando "
        "(id_bando, numero, genere, descrizione, scadenza, frase, origine) "
        "VALUES (?, ?, ?, ?, ?, ?, 'manuale')",
        (id_bando, numero, genere, f"finestra {numero}", scadenza, f"frase {numero}"),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def bandi_a_finestre(cartella_salvata, db_su_file):
    """Tre bandi a piu' finestre, in archivio con l'ultima, e una fase
    successiva (numero 2) che non e' una finestra:

    - a-finestre: il campo dice la seconda finestra, 15/12/2026;
    - finestra-passata: il campo dice la prima, 15/11/2026, gia' passata
      ma dopo la scansione del 13/11;
    - fase-successiva: il campo dice la data della fase successiva.
    """
    campi = (
        ("a-finestre", "15.12.2026"),
        ("finestra-passata", "15.11.2026"),
        ("fase-successiva", "20.12.2026"),
    )
    # nell'elenco, perche' non risultino spariti
    _salva_pagina(
        cartella_salvata,
        "elenchi",
        ELENCO_MONTAGNA,
        _elenco(*(f"{id_bando}-2026" for id_bando, _ in campi)),
    )
    for id_bando, campo in campi:
        _in_archivio(id_bando, f"{id_bando}-2026", "2027-03-31")
        _finestra(db_su_file, id_bando, 1, "2026-11-15")
        _finestra(db_su_file, id_bando, 2, "2026-12-20", genere="fase_successiva")
        _finestra(db_su_file, id_bando, 3, "2026-12-15")
        _finestra(db_su_file, id_bando, 4, "2027-03-31")
        _salva_pagina(
            cartella_salvata, "pagine", _url(f"{id_bando}-2026"), _pagina(campo)
        )
    return cartella_salvata


def test_il_campo_che_indica_una_finestra_non_e_un_cambiamento(bandi_a_finestre):
    """Il campo coincide con una finestra (solo le righe "domanda", in
    ordine di numero): invariato con la nota, e la scadenza che vale resta
    quella dell'archivio, quindi una finestra passata non fa scaduto il
    bando. La data di una fase successiva non e' una finestra: cambiato."""
    lettore = elenco.lettore_della_scansione(bandi_a_finestre, senza_rete=True)

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    assert _note(rapporto, "a-finestre") == {
        ricognizione.INVARIATI: "il campo indica la finestra n. 2 di 3"
    }
    note_passata = _note(rapporto, "finestra-passata")
    assert note_passata[ricognizione.INVARIATI] == (
        "il campo indica la finestra n. 1 di 3"
    )
    assert ricognizione.SCADUTI not in note_passata
    assert _note(rapporto, "fase-successiva") == {
        ricognizione.CAMBIATI: "archivio 2027-03-31, pagina 2026-12-20"
    }
    assert _gruppi(rapporto)[ricognizione.CAMBIATI] == {
        "bando-cambiato",
        "fase-successiva",
    }


# --- nota "possibile sospensione" ---

# Dalla pagina degli incentivi ai datori di lavoro privati salvata il
# 23/11/2026 (titolo del paragrafo, poi il paragrafo, intero)
SOSPENSIONE_VERA = (
    "<p><br /><strong>Sospensione del bando per i seguenti destinatari:</strong></p>"
)
PRIMA_FRASE_VERA = (
    "La sospensione decorre dal 8 luglio 2026, data di pubblicazione del "
    "decreto n. 742/2026 di Arti sul Burt."
)
SECONDA_FRASE_VERA = (
    "Di conseguenza, con riferimento alle categorie di destinatari sopra "
    "indicate, saranno istruite soltanto le domande presentate entro l'8 "
    "luglio 2026, fermo restando che la concessione del contributo resta "
    "subordinata alla disponibilità delle risorse finanziarie."
)


def _pagina_uguale(cartella: Path, corpo: str) -> None:
    _salva_pagina(
        cartella, "pagine", _url("bando-uguale-2026"), _pagina_con("31.01.2027", corpo)
    )


def test_la_frase_vera_di_sospensione_da_la_nota(cartella_salvata):
    """Il gruppo non cambia e nessuna data cambia: il bando senza
    differenze entra tra gli invariati con la sola nota."""
    _pagina_uguale(cartella_salvata, SOSPENSIONE_VERA)
    lettore = elenco.lettore_della_scansione(cartella_salvata, senza_rete=True)

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    [riga] = [r for r in rapporto.righe if r.id_bando == "bando-uguale"]
    assert (riga.gruppo, riga.nota) == (
        ricognizione.INVARIATI,
        "possibile sospensione: Sospensione del bando per i seguenti destinatari:",
    )
    assert (riga.scadenza_archivio, riga.scadenza_pagina) == (
        "2027-01-31",
        "2027-01-31",
    )


@pytest.mark.parametrize(
    "corpo",
    [
        "<p>CHIUSURA ANTICIPATA del bando per esaurimento.</p>",
        "<p>Le risorse   esaurite non consentono altre domande.</p>",
        '<a href="/documents/d/guest/decreto-sospeso-il-bando.pdf">Decreto</a>',
    ],
)
def test_sospensione_in_maiuscolo_su_piu_spazi_o_nel_nome_di_un_allegato(
    cartella_salvata, corpo
):
    _pagina_uguale(cartella_salvata, corpo)
    lettore = elenco.lettore_della_scansione(cartella_salvata, senza_rete=True)

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    nota = _note(rapporto, "bando-uguale")[ricognizione.INVARIATI]
    assert nota.startswith("possibile sospensione: ")


@pytest.mark.parametrize(
    "formula",
    [
        "Le domande si presentano salvo esaurimento delle risorse.",
        "Le domande si presentano fino ad esaurimento delle risorse.",
        "In caso di esaurimento delle risorse il bando chiude.",
        "La Regione si riserva la possibilità di sospendere il bando.",
    ],
)
def test_le_formule_di_rito_non_danno_la_nota_di_sospensione(cartella_salvata, formula):
    _pagina_uguale(cartella_salvata, f"<p>{formula}</p>")
    lettore = elenco.lettore_della_scansione(cartella_salvata, senza_rete=True)

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    pagina = _pagina_con("31.01.2027", formula).decode()
    assert ricognizione.nota_di_sospensione(pagina) is None
    assert _note(rapporto, "bando-uguale") == {}


# --- opzioni --oggi e --testi ---


def _main(monkeypatch, cartella: Path, *opzioni: str) -> None:
    monkeypatch.setattr(
        sys, "argv", ["ricognizione", "--pagine-salvate", str(cartella), *opzioni]
    )
    monkeypatch.setattr(ricognizione, "data_di_oggi", lambda: OGGI)
    ricognizione.main()


def _righe_csv(percorso: Path) -> set[tuple[str, str]]:
    with percorso.open(encoding="utf-8-sig") as f:
        return {(r["gruppo"], r["id_bando"]) for r in csv.DictReader(f)}


def test_oggi_da_riga_di_comando_sostituisce_la_data_di_oggi(
    cartella_salvata, monkeypatch
):
    """bando-scaduto scade il 16/11: con la data di oggi (23/11) e' tra
    gli scaduti, con --oggi 2026-11-15 no."""
    _main(monkeypatch, cartella_salvata, "--oggi", "2026-11-15")

    righe = _righe_csv(cartella_salvata / "ricognizione.csv")
    assert (ricognizione.SCADUTI, "bando-scaduto") not in righe
    assert (ricognizione.CAMBIATI, "bando-cambiato") in righe


def test_oggi_non_valido_ferma_lo_script(cartella_salvata, monkeypatch):
    with pytest.raises(SystemExit, match="AAAA-MM-GG"):
        _main(monkeypatch, cartella_salvata, "--oggi", "23/11/2026")


def test_testi_scrive_finestre_date_e_frasi_intere(bandi_a_finestre, monkeypatch):
    """Un file per ogni cambiato e per ogni bando con possibile
    sospensione, anche se invariato; le frasi lunghe, o con "n. 742",
    restano intere."""
    frase_lunga = (
        "Le domande di finanziamento possono essere presentate entro il "
        "31 gennaio 2027, termine che vale per tutte le categorie di "
        "destinatari indicate all'articolo 5 del bando, comprese quelle "
        "ammesse con riserva dopo la verifica dei requisiti di accesso."
    )
    assert len(frase_lunga) > 200
    _pagina_uguale(
        bandi_a_finestre,
        f"{SOSPENSIONE_VERA}<p>{PRIMA_FRASE_VERA} {SECONDA_FRASE_VERA}</p>"
        f"<p>{frase_lunga}</p>",
    )

    _main(monkeypatch, bandi_a_finestre, "--testi")

    cartella = bandi_a_finestre / "ricognizione-testi"
    assert sorted(p.name for p in cartella.iterdir()) == [
        "bando-cambiato.txt",
        "bando-uguale.txt",
        "fase-successiva.txt",
    ]
    fase = (cartella / "fase-successiva.txt").read_text(encoding="utf-8")
    assert "Scadenza in archivio: 2027-03-31" in fase
    assert "Scadenza dal campo della pagina: 2026-12-20" in fase
    assert "  2. 2026-12-20 (fase_successiva, manuale): frase 2" in fase
    assert "  4. 2027-03-31 (domanda, manuale): frase 4" in fase
    uguale = (cartella / "bando-uguale.txt").read_text(encoding="utf-8")
    scadenza, sospensione = uguale.split("Frasi della pagina con una parola di")
    # con una data e una parola di scadenza
    assert f"  - {frase_lunga}\n" in scadenza
    assert f"  - {SECONDA_FRASE_VERA}\n" in scadenza
    # con una parola di sospensione; "n. 742" non spezza la frase
    assert "  - Sospensione del bando per i seguenti destinatari:\n" in sospensione
    assert f"  - {PRIMA_FRASE_VERA}\n" in sospensione


# --- esclusioni dalla nota "possibile sospensione" (24/11/2026) ---

# Frasi vere delle pagine salvate il 23/11/2026, una per ognuno dei cinque
# bandi in cui la nota scattava senza una sospensione, con la regola che
# le esclude; le ultime due sono estratti delle frasi sull'assunzione di
# donne e di Just in Time, in cui una sola regola esclude.
ESCLUSE_VERE = [
    (
        # contributi agli enti locali per lo sviluppo di progettualita' sui dati
        (
            "La Regione Toscana si riserva la facoltà di prevedere la chiusura "
            "anticipata dello sportello per esaurimento delle risorse finanziarie "
            "disponibili."
        ),
        [sospensione.RISERVA],
    ),
    (
        # contributi ai datori di lavoro per l'assunzione di donne
        (
            "12) alla data dell'assunzione non hanno in atto, nelle unità "
            "produttive toscane interessate dall’assunzione, sospensioni dal "
            "lavoro connesse a trattamenti di Cassa Integrazione Guadagni "
            "Straordinaria, Fondo di Integrazione Salariale per le causali "
            "previste in materia di cassa integrazione guadagni straordinaria o "
            "altro ammortizzatore sociale equivalente, salvo i casi di lavoratori "
            "assunti/trasformati inquadrati ad un livello, una mansione o una "
            "qualifica professionale diversa da quella posseduta dai lavoratori "
            "sospesi;"
        ),
        [sospensione.RISERVA, sospensione.LAVORO],
    ),
    (
        # contributi individuali per le donne in percorsi di uscita dalla violenza
        (
            "La chiusura del bando è il 31 dicembre 2026, salvo chiusura "
            "anticipata per esaurimento delle risorse."
        ),
        [sospensione.RISERVA],
    ),
    (
        # contributi per attivare tirocini non curriculari
        (
            "La domanda di contributo può essere presentata dal giorno successivo "
            "alla pubblicazione del bando sul Burt (27 marzo 2024) ossia dal 28 "
            "marzo 2024 fino al 31 dicembre 2026, salvo chiusura anticipata per "
            "esaurimento risorse annuali disponibili."
        ),
        [sospensione.RISERVA],
    ),
    (
        # voucher formativi Just in Time per l'occupabilita' 2.0
        (
            "Il Settore Formazione per l’inserimento lavorativo, in caso di "
            "esaurimento delle risorse o altre motivazione di interesse pubblico, "
            "si riserva la possibilità di sospendere, chiudere o prorogare "
            "l’avviso, dandone tempestiva comunicazione sulle pagine web dedicate "
            "all’avviso pubblico per voucher just in time per l’occupabilità 2.0 "
            "www.regione.toscana.it/bando2025-voucher-formazioneJustinTime, e su "
            "www.giovanisi.it e attraverso la pubblicazione del decreto di "
            "sospensione/chiusura/proroga dell’Avviso sul BURT."
        ),
        [sospensione.RISERVA, sospensione.BARRE],
    ),
    (
        # estratto della frase sull'assunzione di donne, pagina salvata il
        # 23/11/2026: qui, senza "salvo", solo la regola del lavoro la esclude
        (
            "una qualifica professionale diversa da quella posseduta dai "
            "lavoratori sospesi;"
        ),
        [sospensione.LAVORO],
    ),
    (
        # estratto della frase di Just in Time, pagina salvata il 23/11/2026:
        # qui solo la regola delle barre la esclude
        (
            "attraverso la pubblicazione del decreto di "
            "sospensione/chiusura/proroga dell’Avviso sul BURT"
        ),
        [sospensione.BARRE],
    ),
]


@pytest.mark.parametrize(("frase", "regole"), ESCLUSE_VERE)
def test_le_formule_vere_del_23_11_sono_escluse_con_la_loro_regola(frase, regole):
    esame = sospensione.esamina(f"<html><body><p>{frase}</p></body></html>")

    assert esame.valide == []
    assert [(e.frase, e.regole) for e in esame.escluse] == [(frase, regole)]


@pytest.mark.parametrize(
    "frase",
    [
        # dalla pagina degli incentivi ai datori di lavoro privati, 23/11/2026
        "Sospensione del bando per i seguenti destinatari:",
        # la parola chiave viene prima di "salvo": non e' esclusa
        "Il bando è sospeso, salvo nuove risorse.",
    ],
)
def test_una_sospensione_vera_da_la_nota(frase):
    html = f"<html><body><p>{frase}</p></body></html>"

    assert sospensione.nota_di_sospensione(html) == f"possibile sospensione: {frase}"
    assert sospensione.esamina(html).escluse == []


def test_un_bando_con_sole_frasi_escluse_non_ha_la_nota_ma_ha_il_suo_testo(
    cartella_salvata, monkeypatch
):
    """Nessuna riga nel rapporto per bando-uguale (nessuna differenza,
    nessuna nota); il file dei testi si scrive lo stesso, con le frasi
    escluse e la regola, in una sezione a parte. Le prime quattro frasi
    vere: la quinta (Just in Time) contiene "proroga" e darebbe la nota di
    proroga."""
    corpo = "".join(f"<p>{frase}</p>" for frase, _ in ESCLUSE_VERE[:4])
    _pagina_uguale(cartella_salvata, corpo)

    _main(monkeypatch, cartella_salvata, "--testi")

    righe = _righe_csv(cartella_salvata / "ricognizione.csv")
    assert not any(id_bando == "bando-uguale" for _, id_bando in righe)
    testo = (cartella_salvata / "ricognizione-testi" / "bando-uguale.txt").read_text(
        encoding="utf-8"
    )
    valide, escluse = testo.split("Frasi escluse come formule di rito")
    assert "Frasi della pagina con una parola di sospensione (0):" in valide
    assert escluse.startswith(" (4):\n")
    for frase, regole in ESCLUSE_VERE[:4]:
        assert f"  - {frase} [esclusa: {'; '.join(regole)}]\n" in escluse


def test_la_nota_di_proroga_non_si_spezza_a_decreto_n(cartella_salvata):
    """Frase vera della pagina delle celebrazioni storiche salvata il
    23/11/2026: prima la nota cominciava da "20217 del 14 settembre"."""
    frase = (
        "Con Decreto Dirigenziale n. 20217 del 14 settembre 2026 è stata "
        "disposta la proroga del termine per la presentazione delle domande."
    )
    _pagina_uguale(cartella_salvata, f"<p>{frase}</p>")
    lettore = elenco.lettore_della_scansione(cartella_salvata, senza_rete=True)

    rapporto = ricognizione.ricognisci(lettore, OGGI)

    assert _note(rapporto, "bando-uguale") == {
        ricognizione.INVARIATI: f"possibile proroga: {frase}"
    }
