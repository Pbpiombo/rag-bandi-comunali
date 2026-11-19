"""Lettura dei siti per il passo 19: robots.txt, pause, tentativi, cache.

Tutta la rete del compito 19b passa da qui, con le regole di CLAUDE.md
("Lettura dei siti") e del 19/11/2026:

- ogni richiesta porta INTESTAZIONI_PROGETTO, sempre la stessa: mai un
  secondo tentativo con un'altra intestazione;
- il robots.txt di ogni host si legge prima di ogni altra richiesta a
  quell'host, e si interroga con il nome del programma (NOME_PROGRAMMA),
  non con l'intera intestazione: una regola per quel nome vale, in sua
  assenza valgono le regole per "*";
- tra due richieste allo stesso host, il Crawl-delay o PAUSA_PREDEFINITA;
- errore temporaneo (5xx, tempo scaduto, connessione caduta): dopo il
  primo tentativo, fino a 3 nuovi tentativi, con le attese di
  ATTESE_ERRORE_TEMPORANEO;
- 429: si aspetta Retry-After, o ATTESA_429, fino a 2 nuovi tentativi;
  poi l'host si ferma;
- robots.txt che non si legge dopo i tentativi: RobotsIlleggibile. Non si
  decide da soli: chi chiama si ferma, o permette l'host in modo
  esplicito (permetti_senza_robots), e la scelta va nel registro;
- 401 o 403 sul robots.txt o su una pagina: l'host e' rifiutato, nessuna
  altra richiesta;
- 401, 403 o 404 su un file: quel file e' rifiutato o non trovato, si
  passa al successivo; dopo RIFIUTI_PER_FERMARE rifiuti di fila sullo
  stesso host, l'host si ferma;
- quello che e' gia' nella cartella non si richiede: robots.txt, pagine
  e file.

Ogni richiesta, e ogni scelta, e' una riga di richieste.csv nella
cartella. La funzione che apre gli indirizzi, la pausa e l'orologio si
possono sostituire: i test girano senza rete e senza attese vere.
"""

import csv
import json
import socket
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
from zoneinfo import ZoneInfo

from src.estrazione.incentivi import indirizzo_ascii
from src.estrazione.pdf_bando import INTESTAZIONI_PROGETTO

# Il nome con cui si interroga il robots.txt
NOME_PROGRAMMA = "rag-bandi-comunali"

PAUSA_PREDEFINITA = 5.0  # secondi, se l'host non indica un Crawl-delay
ATTESE_ERRORE_TEMPORANEO = (10, 30, 60)  # secondi, prima di ogni nuovo tentativo
ATTESA_429 = 60  # secondi, se Retry-After manca o non si legge
NUOVI_TENTATIVI_429 = 2
ATTESA_429_MASSIMA = 600  # un Retry-After piu' lungo non si aspetta: l'host si ferma
RIFIUTI_PER_FERMARE = 3
TIMEOUT = 30
BLOCCO = 64 * 1024

FUSO = ZoneInfo("Europe/Rome")

# Esiti di una richiesta
OK = "ok"
GIA_PRESENTE = "già presente"
VIETATO = "vietato dal robots.txt"
RIFIUTATO = "rifiutato"
NON_TROVATO = "non trovato"
ERRORE = "errore"
TROPPO_GRANDE = "troppo grande"
NON_PDF = "non PDF"
HOST_FERMATO = "host fermato"

# Esiti del robots.txt
LETTO = "letto"
ASSENTE = "assente"
ROBOTS_RIFIUTATO = "rifiutato"
PERMESSO_A_MANO = "permesso a mano senza robots.txt"

COLONNE_REGISTRO = [
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


class RobotsIlleggibile(Exception):
    """Il robots.txt di un host non si legge: si decide a mano."""

    def __init__(self, host: str, motivo: str) -> None:
        super().__init__(f"robots.txt di {host} non leggibile: {motivo}")
        self.host = host
        self.motivo = motivo


@dataclass
class RegoleHost:
    """Il robots.txt di un host, come e' stato letto."""

    host: str
    url: str
    esito: str
    codice: int | None = None
    testo: str = ""
    crawl_delay: float | None = None


@dataclass
class Esito:
    """L'esito della richiesta di una pagina o di un file."""

    url: str
    stato: str
    codice: int | None = None
    byte: int = 0
    percorso: Path | None = None
    nota: str = ""

    @property
    def presente(self) -> bool:
        return self.stato in (OK, GIA_PRESENTE)


def _apri(url: str, intestazioni: dict):
    richiesta = urllib.request.Request(indirizzo_ascii(url), headers=intestazioni)
    return urllib.request.urlopen(richiesta, timeout=TIMEOUT)


def host_di(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def radice(url: str) -> str:
    parti = urlsplit(url)
    return urlunsplit((parti.scheme, parti.netloc, "", "", ""))


def _temporaneo(errore: Exception) -> bool:
    if isinstance(errore, urllib.error.HTTPError):
        return errore.code >= 500
    return isinstance(
        errore, (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError)
    )


def attesa_retry_after(valore: str | None, adesso: datetime | None = None) -> float:
    """I secondi indicati da Retry-After (numero o data), o ATTESA_429."""
    if not valore:
        return float(ATTESA_429)
    valore = valore.strip()
    if valore.isdigit():
        return float(valore)
    try:
        quando = parsedate_to_datetime(valore)
    except (TypeError, ValueError):
        return float(ATTESA_429)
    adesso = adesso or datetime.now(UTC)
    return max(0.0, (quando - adesso).total_seconds())


class Lettore:
    """Le richieste a piu' host, con le regole del modulo."""

    def __init__(
        self,
        cartella: str | Path,
        apri: Callable | None = None,
        dormi: Callable[[float], None] | None = None,
        orologio: Callable[[], float] | None = None,
        permetti_senza_robots: set[str] | None = None,
    ) -> None:
        self.cartella = Path(cartella)
        self._apri = apri or _apri
        self._dormi = dormi or time.sleep
        self._orologio = orologio or time.monotonic
        self.permetti_senza_robots = {h.lower() for h in permetti_senza_robots or ()}
        self._regole: dict[str, RegoleHost] = {}
        self._parser: dict[str, RobotFileParser] = {}
        self._ultima: dict[str, float] = {}
        self._rifiuti_di_fila: dict[str, int] = {}
        self.fermati: dict[str, str] = {}

    # --- registro ---

    @property
    def registro(self) -> Path:
        return self.cartella / "richieste.csv"

    def annota(
        self,
        tipo,
        host,
        url,
        esito,
        tentativo="",
        codice="",
        byte="",
        attesa="",
        nota="",
    ):
        """Una riga di richieste.csv: una richiesta o una scelta."""
        self.cartella.mkdir(parents=True, exist_ok=True)
        nuovo = not self.registro.exists()
        with self.registro.open(
            "a", encoding="utf-8-sig" if nuovo else "utf-8", newline=""
        ) as f:
            scrittore = csv.DictWriter(
                f, fieldnames=COLONNE_REGISTRO, lineterminator="\r\n"
            )
            if nuovo:
                scrittore.writeheader()
            scrittore.writerow(
                {
                    "ora": datetime.now(FUSO).isoformat(timespec="seconds"),
                    "tipo": tipo,
                    "host": host,
                    "url": url,
                    "tentativo": tentativo,
                    "esito": esito,
                    "codice": codice,
                    "byte": byte,
                    "attesa": attesa,
                    "nota": nota,
                }
            )

    def ferma(self, host: str, motivo: str) -> None:
        if host not in self.fermati:
            self.fermati[host] = motivo
            self.annota("scelta", host, "", HOST_FERMATO, nota=motivo)

    # --- pause e richieste ---

    def pausa(self, host: str) -> float:
        """I secondi tra due richieste all'host: Crawl-delay o PAUSA_PREDEFINITA."""
        regole = self._regole.get(host)
        if regole and regole.crawl_delay is not None:
            return regole.crawl_delay
        return PAUSA_PREDEFINITA

    def _aspetta_turno(self, host: str) -> float:
        if host not in self._ultima:
            return 0.0
        mancano = self.pausa(host) - (self._orologio() - self._ultima[host])
        if mancano > 0:
            self._dormi(mancano)
            return mancano
        return 0.0

    def _richiesta(self, tipo: str, url: str, massimo_byte: int | None):
        """GET con i tentativi; restituisce (codice, byte) o solleva l'errore finale.

        Errori temporanei e 429 si ritentano qui; gli altri errori HTTP
        si sollevano subito. Oltre massimo_byte solleva ValueError.
        """
        host = host_di(url)
        tentativo = 0
        temporanei = 0
        troppe = 0
        attesa_extra = 0.0
        while True:
            tentativo += 1
            if attesa_extra:
                # l'attesa del nuovo tentativo vale anche come pausa
                # dell'host; se e' piu' breve, si aspetta la differenza
                resto = self.pausa(host) - attesa_extra
                if resto > 0:
                    self._dormi(resto)
                attesa = attesa_extra + max(resto, 0.0)
            else:
                attesa = self._aspetta_turno(host)
            attesa_extra = 0.0
            try:
                with self._apri(url, dict(INTESTAZIONI_PROGETTO)) as risposta:
                    self._ultima[host] = self._orologio()
                    lunghezza = risposta.headers.get("Content-Length")
                    if massimo_byte and lunghezza and lunghezza.isdigit():
                        if int(lunghezza) > massimo_byte:
                            raise ValueError(f"Content-Length {lunghezza}")
                    corpo = bytearray()
                    while blocco := risposta.read(BLOCCO):
                        corpo.extend(blocco)
                        if massimo_byte and len(corpo) > massimo_byte:
                            raise ValueError(f"oltre {massimo_byte} byte")
                    codice = getattr(risposta, "status", 200)
                self.annota(
                    tipo, host, url, OK, tentativo, codice, len(corpo), f"{attesa:g}"
                )
                return codice, bytes(corpo)
            except ValueError as errore:
                self._ultima[host] = self._orologio()
                self.annota(tipo, host, url, TROPPO_GRANDE, tentativo, nota=str(errore))
                raise
            except urllib.error.HTTPError as errore:
                self._ultima[host] = self._orologio()
                self.annota(
                    tipo,
                    host,
                    url,
                    ERRORE,
                    tentativo,
                    errore.code,
                    attesa=f"{attesa:g}",
                )
                if errore.code == 429 and troppe < NUOVI_TENTATIVI_429:
                    secondi = attesa_retry_after(
                        errore.headers.get("Retry-After") if errore.headers else None
                    )
                    if secondi <= ATTESA_429_MASSIMA:
                        troppe += 1
                        self._dormi(secondi)
                        attesa_extra = secondi
                        continue
                if _temporaneo(errore) and temporanei < len(ATTESE_ERRORE_TEMPORANEO):
                    secondi = ATTESE_ERRORE_TEMPORANEO[temporanei]
                    temporanei += 1
                    self._dormi(secondi)
                    attesa_extra = secondi
                    continue
                raise
            except (
                urllib.error.URLError,
                TimeoutError,
                socket.timeout,
                ConnectionError,
            ) as errore:
                self._ultima[host] = self._orologio()
                self.annota(
                    tipo,
                    host,
                    url,
                    ERRORE,
                    tentativo,
                    attesa=f"{attesa:g}",
                    nota=str(errore),
                )
                if temporanei < len(ATTESE_ERRORE_TEMPORANEO):
                    secondi = ATTESE_ERRORE_TEMPORANEO[temporanei]
                    temporanei += 1
                    self._dormi(secondi)
                    attesa_extra = secondi
                    continue
                raise

    # --- robots.txt ---

    def _file_robots(self, host: str) -> Path:
        return self.cartella / "robots" / f"{host}.json"

    def regole(self, url: str) -> RegoleHost:
        """Il robots.txt dell'host di url, letto una volta e conservato.

        Solleva RobotsIlleggibile se non si legge dopo i tentativi e
        l'host non e' tra quelli permessi a mano.
        """
        host = host_di(url)
        if host in self._regole:
            return self._regole[host]

        salvato = self._file_robots(host)
        if salvato.exists():
            regole = RegoleHost(**json.loads(salvato.read_text(encoding="utf-8")))
            return self._tieni(regole)

        indirizzo = radice(url) + "/robots.txt"
        try:
            _, corpo = self._richiesta("robots", indirizzo, None)
            regole = RegoleHost(
                host, indirizzo, LETTO, 200, corpo.decode("utf-8", errors="replace")
            )
        except urllib.error.HTTPError as errore:
            if errore.code in (404, 410):
                regole = RegoleHost(host, indirizzo, ASSENTE, errore.code)
            elif errore.code in (401, 403):
                regole = RegoleHost(host, indirizzo, ROBOTS_RIFIUTATO, errore.code)
            else:
                return self._illeggibile(host, indirizzo, f"HTTP {errore.code}")
        except (
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            ConnectionError,
            ValueError,
        ) as errore:
            return self._illeggibile(host, indirizzo, str(errore))

        if regole.esito == LETTO:
            parser = RobotFileParser()
            parser.parse(regole.testo.splitlines())
            ritardo = parser.crawl_delay(NOME_PROGRAMMA)
            regole.crawl_delay = float(ritardo) if ritardo is not None else None
        salvato.parent.mkdir(parents=True, exist_ok=True)
        salvato.write_text(
            json.dumps(regole.__dict__, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        if regole.esito == LETTO:
            (salvato.with_suffix(".txt")).write_text(regole.testo, encoding="utf-8")
        return self._tieni(regole)

    def _illeggibile(self, host: str, indirizzo: str, motivo: str) -> RegoleHost:
        if host not in self.permetti_senza_robots:
            raise RobotsIlleggibile(host, motivo)
        self.annota("scelta", host, indirizzo, PERMESSO_A_MANO, nota=motivo)
        # non si conserva: alla prossima esecuzione si riprova a leggerlo
        regole = RegoleHost(host, indirizzo, PERMESSO_A_MANO)
        self._regole[host] = regole
        return regole

    def _tieni(self, regole: RegoleHost) -> RegoleHost:
        self._regole[regole.host] = regole
        if regole.esito == LETTO:
            parser = RobotFileParser()
            parser.parse(regole.testo.splitlines())
            self._parser[regole.host] = parser
        if regole.esito == ROBOTS_RIFIUTATO:
            self.ferma(regole.host, f"robots.txt rifiutato (HTTP {regole.codice})")
        return regole

    def consentito(self, url: str) -> bool:
        """L'url si puo' chiedere: host non fermato e robots.txt che lo permette."""
        host = host_di(url)
        if host in self.fermati:
            return False
        regole = self.regole(url)
        if regole.esito in (ASSENTE, PERMESSO_A_MANO):
            return True
        if regole.esito == LETTO:
            return self._parser[host].can_fetch(NOME_PROGRAMMA, url)
        return False

    # --- pagine e file ---

    def prendi(
        self,
        url: str,
        destinazione: str | Path,
        tipo: str,
        massimo_byte: int | None = None,
        solo_pdf: bool = False,
    ) -> Esito:
        """Scarica url in destinazione, se non c'e' gia'.

        tipo: "pagina" (401 e 403 fermano l'host) o "file" (401, 403 e
        404 valgono per il file; RIFIUTI_PER_FERMARE rifiuti di fila
        fermano l'host).
        """
        destinazione = Path(destinazione)
        if destinazione.exists():
            return Esito(url, GIA_PRESENTE, percorso=destinazione)
        host = host_di(url)
        if host in self.fermati:
            return Esito(url, HOST_FERMATO, nota=self.fermati[host])
        if not self.consentito(url):
            if host in self.fermati:
                return Esito(url, HOST_FERMATO, nota=self.fermati[host])
            self.annota(tipo, host, url, VIETATO)
            return Esito(url, VIETATO)

        try:
            codice, corpo = self._richiesta(tipo, url, massimo_byte)
        except ValueError as errore:
            return Esito(url, TROPPO_GRANDE, nota=str(errore))
        except urllib.error.HTTPError as errore:
            return self._errore_http(tipo, host, url, errore.code)
        except (
            urllib.error.URLError,
            TimeoutError,
            socket.timeout,
            ConnectionError,
        ) as errore:
            return Esito(url, ERRORE, nota=str(errore))

        if solo_pdf and b"%PDF" not in corpo[:1024]:
            self.annota(
                "scelta", host, url, NON_PDF, nota="il contenuto non comincia con %PDF"
            )
            return Esito(url, NON_PDF, codice, len(corpo))

        self._rifiuti_di_fila[host] = 0
        destinazione.parent.mkdir(parents=True, exist_ok=True)
        provvisorio = destinazione.with_name(destinazione.name + ".parziale")
        provvisorio.write_bytes(corpo)
        provvisorio.replace(destinazione)
        return Esito(url, OK, codice, len(corpo), destinazione)

    def _errore_http(self, tipo: str, host: str, url: str, codice: int) -> Esito:
        if codice == 429:
            self.ferma(host, "HTTP 429 anche dopo i nuovi tentativi")
            return Esito(url, RIFIUTATO, codice, nota="429")
        if codice in (401, 403):
            if tipo == "pagina":
                self.ferma(host, f"pagina rifiutata (HTTP {codice})")
                return Esito(url, RIFIUTATO, codice)
            self._rifiuti_di_fila[host] = self._rifiuti_di_fila.get(host, 0) + 1
            if self._rifiuti_di_fila[host] >= RIFIUTI_PER_FERMARE:
                self.ferma(host, f"{RIFIUTI_PER_FERMARE} file rifiutati di fila")
            return Esito(url, RIFIUTATO, codice)
        if codice in (404, 410):
            return Esito(url, NON_TROVATO, codice)
        return Esito(url, ERRORE, codice)
