"""Test del lettore dei siti (passo 19, compito 19b): senza rete, senza attese.

La rete e' una RetaFinta: per ogni indirizzo una coda di risposte (byte,
codice HTTP o eccezione); registra le chiamate con le intestazioni. Le
pause vanno in un elenco invece di aspettare.
"""

import csv
import io
import socket
import urllib.error
from datetime import UTC, datetime

import pytest

from src.estrazione import lettore_siti as ls
from src.estrazione.pdf_bando import INTESTAZIONI_PROGETTO

SITO = "https://www.sito-di-prova.it"
ROBOTS = f"{SITO}/robots.txt"
PDF = b"%PDF-1.4\nfile di prova\n%%EOF\n"


class RispostaFinta:
    def __init__(self, corpo: bytes, intestazioni: dict | None = None) -> None:
        self._corpo = io.BytesIO(corpo)
        self.headers = intestazioni or {}
        self.status = 200

    def read(self, quanti: int = -1) -> bytes:
        return self._corpo.read(quanti)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class Errore:
    """Una risposta HTTP di errore, con le sue intestazioni."""

    def __init__(self, codice: int, intestazioni: dict | None = None) -> None:
        self.codice = codice
        self.intestazioni = intestazioni or {}


class ReteFinta:
    """Per ogni url una coda di risposte; l'ultima si ripete."""

    def __init__(self, risposte: dict) -> None:
        self.risposte = {
            u: list(v) if isinstance(v, list) else [v] for u, v in risposte.items()
        }
        self.chiamate: list[tuple[str, dict]] = []

    def __call__(self, url: str, intestazioni: dict):
        self.chiamate.append((url, dict(intestazioni)))
        if url not in self.risposte:
            raise AssertionError(f"richiesta non prevista: {url}")
        coda = self.risposte[url]
        risposta = coda.pop(0) if len(coda) > 1 else coda[0]
        if isinstance(risposta, Errore):
            raise urllib.error.HTTPError(
                url, risposta.codice, "errore", risposta.intestazioni, None
            )
        if isinstance(risposta, Exception):
            raise risposta
        if isinstance(risposta, tuple):
            return RispostaFinta(*risposta)
        return RispostaFinta(risposta)

    def url_chiamati(self) -> list[str]:
        return [u for u, _ in self.chiamate]


def lettore(tmp_path, risposte: dict, **opzioni) -> tuple[ls.Lettore, ReteFinta, list]:
    rete = ReteFinta(risposte)
    pause: list[float] = []
    return (
        ls.Lettore(
            tmp_path, apri=rete, dormi=pause.append, orologio=lambda: 0.0, **opzioni
        ),
        rete,
        pause,
    )


def registro(tmp_path) -> list[dict]:
    with (tmp_path / "richieste.csv").open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# --- intestazione e nome del programma ---


def test_ogni_richiesta_porta_l_intestazione_del_progetto(tmp_path):
    let, rete, _ = lettore(
        tmp_path,
        {ROBOTS: b"User-agent: *\nDisallow:\n", f"{SITO}/a.pdf": [Errore(503), PDF]},
    )
    let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file", solo_pdf=True)
    assert len(rete.chiamate) == 3
    assert all(h == INTESTAZIONI_PROGETTO for _, h in rete.chiamate)


def test_regola_per_il_nome_del_programma(tmp_path):
    testo = (
        "User-agent: rag-bandi-comunali\nDisallow: /privato/\n\n"
        "User-agent: *\nDisallow: /pubblico/\n"
    )
    let, _, _ = lettore(tmp_path, {ROBOTS: testo.encode()})
    # la regola per il nome vale, quella per * no
    assert let.consentito(f"{SITO}/privato/a") is False
    assert let.consentito(f"{SITO}/pubblico/a") is True


def test_senza_regola_per_il_nome_valgono_quelle_per_tutti(tmp_path):
    testo = "User-agent: altro-programma\nDisallow: /pubblico/\n\nUser-agent: *\nDisallow: /tutti/\n"
    let, _, _ = lettore(tmp_path, {ROBOTS: testo.encode()})
    assert let.consentito(f"{SITO}/tutti/a") is False
    assert let.consentito(f"{SITO}/pubblico/a") is True


# --- pause ---


def test_pausa_dal_crawl_delay(tmp_path):
    let, _, pause = lettore(
        tmp_path,
        {
            ROBOTS: b"User-agent: *\nCrawl-delay: 2\n",
            f"{SITO}/a": b"<html></html>",
            f"{SITO}/b": b"<html></html>",
        },
    )
    let.prendi(f"{SITO}/a", tmp_path / "a.html", "pagina")
    let.prendi(f"{SITO}/b", tmp_path / "b.html", "pagina")
    # nessuna pausa prima del robots.txt, la prima richiesta all'host
    assert pause == [2.0, 2.0]


def test_pausa_predefinita_senza_crawl_delay(tmp_path):
    let, _, pause = lettore(
        tmp_path, {ROBOTS: b"User-agent: *\nDisallow:\n", f"{SITO}/a": b"<html></html>"}
    )
    let.prendi(f"{SITO}/a", tmp_path / "a.html", "pagina")
    assert pause == [ls.PAUSA_PREDEFINITA]


# --- robots.txt ---


def test_robots_assente_permette(tmp_path):
    let, _, _ = lettore(tmp_path, {ROBOTS: Errore(404)})
    assert let.regole(SITO).esito == ls.ASSENTE
    assert let.consentito(f"{SITO}/a") is True


@pytest.mark.parametrize("codice", [401, 403])
def test_robots_rifiutato_ferma_l_host(tmp_path, codice):
    let, rete, _ = lettore(tmp_path, {ROBOTS: Errore(codice)})
    esito = let.prendi(f"{SITO}/a", tmp_path / "a.html", "pagina")
    assert esito.stato == ls.HOST_FERMATO
    assert SITO.split("//")[1] in let.fermati
    assert rete.url_chiamati() == [ROBOTS]
    # nessun'altra richiesta all'host
    assert (
        let.prendi(f"{SITO}/b", tmp_path / "b.html", "pagina").stato == ls.HOST_FERMATO
    )
    assert rete.url_chiamati() == [ROBOTS]


def test_robots_illeggibile_dopo_i_tentativi(tmp_path):
    let, rete, pause = lettore(tmp_path, {ROBOTS: Errore(503)})
    with pytest.raises(ls.RobotsIlleggibile):
        let.consentito(f"{SITO}/a")
    # primo tentativo e tre nuovi, con le attese crescenti
    assert rete.url_chiamati() == [ROBOTS] * 4
    assert pause == [10, 30, 60]


def test_robots_illeggibile_permesso_a_mano(tmp_path):
    let, _, _ = lettore(
        tmp_path,
        {ROBOTS: socket.timeout("tempo scaduto")},
        permetti_senza_robots={"www.sito-di-prova.it"},
    )
    assert let.consentito(f"{SITO}/a") is True
    scelte = [r for r in registro(tmp_path) if r["tipo"] == "scelta"]
    assert [r["esito"] for r in scelte] == [ls.PERMESSO_A_MANO]


def test_robots_conservato_e_non_richiesto_di_nuovo(tmp_path):
    let, rete, _ = lettore(tmp_path, {ROBOTS: b"User-agent: *\nCrawl-delay: 3\n"})
    let.regole(SITO)
    assert (tmp_path / "robots" / "www.sito-di-prova.it.txt").exists()

    di_nuovo, rete2, _ = lettore(tmp_path, {})
    regole = di_nuovo.regole(SITO)
    assert rete2.chiamate == []
    assert regole.crawl_delay == 3.0
    assert len(rete.chiamate) == 1


def test_url_vietato_non_si_chiede(tmp_path):
    let, rete, _ = lettore(tmp_path, {ROBOTS: b"User-agent: *\nDisallow: /a\n"})
    assert let.prendi(f"{SITO}/a", tmp_path / "a.html", "pagina").stato == ls.VIETATO
    assert rete.url_chiamati() == [ROBOTS]


# --- errori temporanei e 429 ---


@pytest.mark.parametrize(
    "temporaneo",
    [Errore(503), urllib.error.URLError("connessione caduta"), TimeoutError("tempo")],
)
def test_errore_temporaneo_si_ritenta(tmp_path, temporaneo):
    let, rete, pause = lettore(
        tmp_path,
        {ROBOTS: Errore(404), f"{SITO}/a.pdf": [temporaneo, temporaneo, PDF]},
    )
    esito = let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file", solo_pdf=True)
    assert esito.stato == ls.OK
    assert rete.url_chiamati().count(f"{SITO}/a.pdf") == 3
    # pausa tra robots e file, poi le attese dei tentativi
    assert pause == [ls.PAUSA_PREDEFINITA, 10, 30]


def test_errore_temporaneo_esaurito(tmp_path):
    let, rete, _ = lettore(
        tmp_path, {ROBOTS: Errore(404), f"{SITO}/a.pdf": Errore(502)}
    )
    esito = let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file")
    assert esito.stato == ls.ERRORE
    assert rete.url_chiamati().count(f"{SITO}/a.pdf") == 4
    assert not (tmp_path / "a.pdf").exists()


def test_429_aspetta_retry_after(tmp_path):
    let, _, pause = lettore(
        tmp_path,
        {
            ROBOTS: Errore(404),
            f"{SITO}/a.pdf": [Errore(429, {"Retry-After": "7"}), PDF],
        },
    )
    assert let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file").stato == ls.OK
    assert 7.0 in pause


def test_429_senza_retry_after_aspetta_60(tmp_path):
    let, _, pause = lettore(
        tmp_path, {ROBOTS: Errore(404), f"{SITO}/a.pdf": [Errore(429), PDF]}
    )
    assert let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file").stato == ls.OK
    assert float(ls.ATTESA_429) in pause


def test_429_ripetuto_ferma_l_host(tmp_path):
    let, rete, _ = lettore(
        tmp_path, {ROBOTS: Errore(404), f"{SITO}/a.pdf": Errore(429)}
    )
    esito = let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file")
    assert esito.stato == ls.RIFIUTATO
    # primo tentativo e due nuovi
    assert rete.url_chiamati().count(f"{SITO}/a.pdf") == 3
    assert "www.sito-di-prova.it" in let.fermati


def test_retry_after_come_data():
    adesso = datetime(2026, 11, 20, 10, 0, 0, tzinfo=UTC)
    assert ls.attesa_retry_after("Fri, 20 Nov 2026 10:00:30 GMT", adesso) == 30.0
    assert ls.attesa_retry_after("non una data") == float(ls.ATTESA_429)


# --- rifiuti ---


@pytest.mark.parametrize("codice", [401, 403])
def test_pagina_rifiutata_ferma_l_host(tmp_path, codice):
    let, rete, _ = lettore(tmp_path, {ROBOTS: Errore(404), f"{SITO}/a": Errore(codice)})
    assert let.prendi(f"{SITO}/a", tmp_path / "a.html", "pagina").stato == ls.RIFIUTATO
    # mai un secondo tentativo, nemmeno con un'altra intestazione
    assert rete.url_chiamati().count(f"{SITO}/a") == 1
    assert (
        let.prendi(f"{SITO}/b", tmp_path / "b.html", "pagina").stato == ls.HOST_FERMATO
    )
    assert f"{SITO}/b" not in rete.url_chiamati()


def test_file_rifiutato_o_non_trovato_si_passa_al_successivo(tmp_path):
    let, rete, _ = lettore(
        tmp_path,
        {
            ROBOTS: Errore(404),
            f"{SITO}/a.pdf": Errore(403),
            f"{SITO}/b.pdf": Errore(404),
            f"{SITO}/c.pdf": PDF,
        },
    )
    assert let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file").stato == ls.RIFIUTATO
    assert (
        let.prendi(f"{SITO}/b.pdf", tmp_path / "b.pdf", "file").stato == ls.NON_TROVATO
    )
    assert let.prendi(f"{SITO}/c.pdf", tmp_path / "c.pdf", "file").stato == ls.OK
    assert let.fermati == {}
    assert rete.url_chiamati().count(f"{SITO}/a.pdf") == 1


def test_tre_file_rifiutati_di_fila_fermano_l_host(tmp_path):
    rifiuti = {f"{SITO}/{n}.pdf": Errore(403) for n in range(1, 5)}
    let, rete, _ = lettore(tmp_path, {ROBOTS: Errore(404), **rifiuti})
    stati = [
        let.prendi(u, tmp_path / u.rsplit("/", 1)[1], "file").stato for u in rifiuti
    ]
    assert stati == [ls.RIFIUTATO] * 3 + [ls.HOST_FERMATO]
    assert f"{SITO}/4.pdf" not in rete.url_chiamati()


def test_un_file_buono_azzera_i_rifiuti_di_fila(tmp_path):
    risposte = {
        f"{SITO}/1.pdf": Errore(403),
        f"{SITO}/2.pdf": Errore(403),
        f"{SITO}/3.pdf": PDF,
        f"{SITO}/4.pdf": Errore(403),
        f"{SITO}/5.pdf": Errore(403),
    }
    let, _, _ = lettore(tmp_path, {ROBOTS: Errore(404), **risposte})
    for url in risposte:
        let.prendi(url, tmp_path / url.rsplit("/", 1)[1], "file")
    assert let.fermati == {}


# --- file gia' presenti, tetti, contenuto ---


def test_file_gia_presente_nessuna_richiesta(tmp_path):
    (tmp_path / "a.pdf").write_bytes(PDF)
    let, rete, _ = lettore(tmp_path, {})
    esito = let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file")
    assert esito.stato == ls.GIA_PRESENTE
    assert rete.chiamate == []


def test_content_length_oltre_il_tetto(tmp_path):
    let, _, _ = lettore(
        tmp_path,
        # il corpo sta nel tetto: solo Content-Length lo ferma
        {ROBOTS: Errore(404), f"{SITO}/a.pdf": (PDF, {"Content-Length": "999999"})},
    )
    esito = let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file", massimo_byte=100)
    assert esito.stato == ls.TROPPO_GRANDE
    assert not (tmp_path / "a.pdf").exists()


def test_flusso_oltre_il_tetto(tmp_path):
    let, _, _ = lettore(tmp_path, {ROBOTS: Errore(404), f"{SITO}/a.pdf": PDF * 100})
    esito = let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file", massimo_byte=100)
    assert esito.stato == ls.TROPPO_GRANDE
    assert not (tmp_path / "a.pdf").exists()


def test_contenuto_non_pdf(tmp_path):
    let, _, _ = lettore(
        tmp_path, {ROBOTS: Errore(404), f"{SITO}/a.pdf": b"<html>accesso negato</html>"}
    )
    esito = let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file", solo_pdf=True)
    assert esito.stato == ls.NON_PDF
    assert not (tmp_path / "a.pdf").exists()


def test_registro_delle_richieste(tmp_path):
    let, _, _ = lettore(
        tmp_path, {ROBOTS: Errore(404), f"{SITO}/a.pdf": [Errore(503), PDF]}
    )
    let.prendi(f"{SITO}/a.pdf", tmp_path / "a.pdf", "file")
    righe = registro(tmp_path)
    assert list(righe[0]) == ls.COLONNE_REGISTRO
    assert [(r["tipo"], r["esito"], r["codice"]) for r in righe] == [
        ("robots", ls.ERRORE, "404"),
        ("file", ls.ERRORE, "503"),
        ("file", ls.OK, "200"),
    ]
