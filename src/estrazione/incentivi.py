"""Fonte Incentivi Italia: il file open data del catalogo (piano fonti, tappa 5).

Il file OpenData_Incentivi.csv (sezione Incentivi della pagina open data
del portale, licenza CC BY 4.0) si scarica a mano e si passa per
percorso. Mai la sezione Aiuti: il lettore rifiuta un file senza le
colonne della sezione Incentivi. Nessun modello legge il file.

Per ogni riga, nell'ordine (docs/piano-fonti.md, tappa 5):

1. data: chiusa da piu' di GIORNI_STORICO giorni, si ignora;
2. territorio: la Toscana in Regioni o uno dei nostri comuni in Comuni;
   un elenco di comuni senza i nostri esclude la riga, anche se l'ente
   e' la Regione;
3. ente concedente: la classe dalla tabella chiusa CONCEDENTI
   (docs/concedenti-incentivi.md); un ente che non c'e' e' da verificare,
   mai classificato per somiglianza;
4. le righe aperte per enti pubblici non si salvano dal file: la pagina
   va letta con il modello (AL_MODELLO);
5. le altre si controllano sulla pagina dell'ente (Link_istituzionale),
   senza modello: la data di chiusura del file deve comparire nella
   pagina, uno sportello non deve avere parole di chiusura.

Una riga salvata ha solo i tipi di beneficiario privati: i tipi pubblici
si salvano solo dopo la lettura della pagina con il modello (decisione
del 13/11/2026). La nota NOTA_CATALOGO lo dice nella riga.
"""

import csv
import re
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from http.client import HTTPException
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

from src.database.interrogazioni_bandi import SOGLIA_SPORTELLO_ANNI, _anni_fa
from src.estrazione.beneficiari import TIPI_IMPRESA
from src.estrazione.indirizzi import url_canonico
from src.estrazione.pagina import INTESTAZIONI, a_testo, ritaglia
from src.estrazione.scadenza import GIORNI_STORICO, MESI

CODICE_FONTE = "incentivi-italia"

# Il testo citato come fonte di ogni bando: il file, con la sua data
NOME_FONTE = "Incentivi Italia, OpenData_Incentivi.csv del {data}, CC BY 4.0"
# Per i bandi letti con il modello: i dati vengono dalla pagina dell'ente,
# il catalogo l'ha solo segnalata
NOME_FONTE_PAGINA = (
    "Pagina dell'ente, segnalata dal catalogo Incentivi Italia "
    "(OpenData_Incentivi.csv del {data}, CC BY 4.0)"
)

# Origine di pubblicato_il per le righe di questa fonte: la data di
# apertura del catalogo, ne' la pubblicazione ne' l'atto
ORIGINE_APERTURA = "apertura"
# Origine delle righe di beneficiari_bando lette dal catalogo
ORIGINE_CATALOGO = "catalogo"

NOTA_CATALOGO = (
    "Le tipologie vengono dal catalogo Incentivi Italia; gli enti pubblici "
    "vanno verificati sulla pagina del bando."
)

# Le colonne della sezione Incentivi che il lettore usa. Un file senza
# anche una sola di queste (es. la sezione Aiuti) si rifiuta.
COLONNE = (
    "ID_Incentivo",
    "Titolo",
    "Soggetto_Concedente",
    "Data_apertura",
    "Data_chiusura",
    "Link_istituzionale",
    "Regioni",
    "Comuni",
    "Tipologia_Soggetto",
    "Dimensione_beneficiari",
    "Settore_Attivita",
    "Agevolazione_Concedibile_Min",
    "Agevolazione_Concedibile_Max",
    "Spesa_Ammessa_Min",
    "Spesa_Ammessa_Max",
)

# Separatore dei campi multivalore (Regioni, Tipologia, Dimensione,
# Settore): la sequenza di due caratteri \,
SEPARATORE = "\\,"
# Comuni: nel file del 12/11/2026 e' ";", i metadati dicono \,
SEPARATORE_COMUNI = re.compile(r";|\\,")

# I comuni dell'Unione, come li scrive il catalogo
COMUNI_TERRITORIO = ("Abetone Cutigliano", "San Marcello Piteglio", "Sambuca Pistoiese")

# Classi dell'ente concedente
TERRITORIO = "territorio"
REGIONALE = "regionale"
NAZIONALE = "nazionale"
ALTRO_TERRITORIO = "altro territorio"
DA_VERIFICARE = "da verificare"
CLASSI_AMMESSE = (TERRITORIO, REGIONALE, NAZIONALE)

# La tabella dei concedenti approvata (docs/concedenti-incentivi.md): i
# nomi come li scrive il file; il confronto e' sul nome normalizzato
CONCEDENTI = {
    TERRITORIO: (
        "Camera di Commercio Industria Artigianato e Agricoltura di Pistoia-Prato",
        "Comune di San Marcello Piteglio",
        "COMUNE DI ABETONE CUTIGLIANO",
        "MontagnAppennino scrl",
    ),
    REGIONALE: (
        "Regione Toscana",
        "Regione Toscana - Giunta",
        "Sviluppo Toscana S.p.A.",
    ),
    NAZIONALE: (
        (
            "Agenzia nazionale per l'attrazione degli investimenti e lo sviluppo "
            "d'impresa S.p.A. - Invitalia (05678721001)"
        ),
        "Agenzia per la Cybersicurezza Nazionale",
        "Gestore dei Servizi Energetici GSE S.p.A.",
        (
            "ICE-Agenzia per la promozione all'estero e l'internazionalizzazione "
            "delle imprese italiane"
        ),
        "INNOGEST S.G.R. S.p.A.",
        (
            "Invitalia - Agenzia nazionale per l'attrazione degli investimenti e lo "
            "sviluppo d'impresa S.p.A."
        ),
        "Istituto Nazionale per l'Assicurazione contro gli Infortuni sul Lavoro - INAIL",
        "Istituto per il Credito Sportivo",
        "Ministero degli Affari Esteri e della Cooperazione Internazionale",
        "Ministero del Lavoro e delle Politiche Sociali",
        "Ministero del turismo",
        "Ministero dell'ambiente e della sicurezza energetica",
        "Ministero dell'Economia e delle Finanze",
        "MINISTERO DELL'UNIVERSITA' E DELLA RICERCA",
        "Ministero della Cultura",
        "Ministero della Cultura - Direzione Generale Spettacolo",
        "Ministero delle Imprese e del Made in Italy",
        (
            "Ministero delle Imprese e del Made in Italy - Dipartimento per le "
            "politiche per le imprese - Direzione generale per gli incentivi alle imprese"
        ),
        (
            "Ministero delle Imprese e del Made in Italy - Direzione generale per gli "
            "incentivi alle imprese"
        ),
        (
            "Ministero delle Infrastrutture e dei Trasporti - Direzione Generale per i "
            "porti, la logistica e l'intermodalità"
        ),
        "Ministero delle infrastrutture e della mobilita' sostenibili",
        "Presidenza del Consiglio dei Ministri",
        (
            "Presidenza del Consiglio dei Ministri - Dipartimento per l'informazione e "
            "l'editoria"
        ),
        "SIMEST",
    ),
    DA_VERIFICARE: (
        "ARTES 4.0 I - Advanced Robotics and enabling digital TEchnologies & Systems 4.0",
        "Consiglio Nazionale delle Ricerche - CNR",
        "Consorzio MedITECH",
        "START 4.0",
        "Universita' degli Studi di Bari Aldo Moro",
        "Universita' degli Studi di Camerino",
        "Universita' degli Studi di Firenze",
        "Universita' degli Studi di Padova",
        "Universita' degli Studi di Roma 'Tor Vergata'",
        "UNIVERSITA' DELLA CALABRIA",
    ),
    ALTRO_TERRITORIO: (
        "Autorita' di Sistema portuale del Mare Adriatico centro-settentrionale",
        "Camera di Commercio Arezzo Siena",
        "Camera di Commercio della Maremma e del Tirreno",
        "Camera di Commercio Industria Artigianato e Agricoltura di Pordenone Udine",
        (
            "Camera di commercio, industria, artigianato e agricoltura della Toscana "
            "Nord Ovest"
        ),
        "Camera di Commercio, Industria, Artigianato e Agricoltura di Firenze",
        "Comune di Aliano",
        "Comune di Arezzo",
        "Comune di Arona",
        "Comune di Belmonte Castello",
        "comune di castelnuovo rangone",
        "COMUNE DI CIVIDALE DEL FRIULI",
        "Comune di Genova",
        "Comune di Laviano",
        "COMUNE DI MONFUMO",
        "Comune di Napoli",
        "Comune di Pratovecchio Stia",
        "Comune di Ravenna",
        "Comune di Savignano sul Rubicone",
        "Comune di Sogliano al Rubicone",
        "Comune di Torino",
        "COMUNE DI TREVIGLIO",
        "Comunita' Montana Lario Intelvese",
        "Fondazione Calabria Film Commission",
        "Fondazione Film Commission di Roma e del Lazio",
        "Fondazione Lucana Film Commission",
        "Provincia Autonoma di Trento",
        "Regione Autonoma della Sardegna",
        (
            "Regione Autonoma della Sardegna - Servizio lingua e cultura sarda, "
            "Editoria e Informazione"
        ),
        "Regione Autonoma della Sardegna - Servizio Sport, Spettacolo e Cinema",
        "Regione Autonoma Friuli-Venezia Giulia",
        "Regione Autonoma Valle D'Aosta",
        "Regione Lombardia",
        "Regione Marche",
    ),
}

# Tipologia_Soggetto -> tipi di beneficiario. IMPRESE: i tipi d'impresa
# secondo Settore_Attivita. PUBBLICO: non si salva dal catalogo.
IMPRESE = "imprese"
PUBBLICO = "pubblico"
TIPOLOGIE = {
    "Impresa": IMPRESE,
    "Impresa - SU/PMI innovativa": IMPRESE,
    "Impresa - prevalenza femminile": IMPRESE,
    "Impresa - prevalenza giovanile": IMPRESE,
    "Impresa da costituire - Altro": IMPRESE,
    "Impresa da costituire - Femminile": IMPRESE,
    "Impresa da costituire - Giovanile": IMPRESE,
    "Consorzio": IMPRESE,
    "Rete d'impresa": IMPRESE,
    "Istituto finanziario": ("altra_impresa",),
    "Professionista": ("professionista_autonomo",),
    "Associazione fra professionisti": ("professionista_autonomo",),
    "Cooperative/Associazioni Non Profit": ("terzo_settore",),
    "Università/Ente di Ricerca": ("ricerca_formazione",),
    "Cittadino": ("cittadini_famiglie",),
    "Ente Pubblico": PUBBLICO,
}

# Settore_Attivita -> tipo d'impresa. I settori del file senza un tipo
# proprio sono altra_impresa; un settore che non e' qui da' un avviso.
SETTORI = {
    "Agricoltura, silvicoltura e pesca": "impresa_agricola",
    "Turismo": "impresa_turistica",
    "Alberghiero": "impresa_turistica",
    "Artigianato": "impresa_artigiana_commerciale",
    "Commercio": "impresa_artigiana_commerciale",
    "Ristorazione": "impresa_artigiana_commerciale",
    "Agroalimentare": "altra_impresa",
    "Altri servizi": "altra_impresa",
    "Autoveicoli e altri mezzi di trasporto": "altra_impresa",
    "Chimica e Farmaceutica": "altra_impresa",
    "Cultura": "altra_impresa",
    "Edilizia": "altra_impresa",
    "Elettronica": "altra_impresa",
    "Fornitura Energia, Acqua e gestione Rifiuti": "altra_impresa",
    "ICT": "altra_impresa",
    "Meccanica": "altra_impresa",
    "Metallurgia": "altra_impresa",
    "Mobili, Legno e Carta": "altra_impresa",
    "Moda e Tessile": "altra_impresa",
    "Salute": "altra_impresa",
    "Servizi di trasporto": "altra_impresa",
}

# Stato dalle date del file
APERTO = "aperto"
SPORTELLO = "sportello"
IN_ARRIVO = "in arrivo"
SENZA_DATE = "senza date"
STORICO = "storico"
SCADUTO = "scaduto"
# Gli stati in cui una riga per enti pubblici va al modello
VIVI = (APERTO, SPORTELLO, IN_ARRIVO)

# Esiti dell'esame di una riga
IGNORATA = "ignorata"
GIA_IN_ARCHIVIO = "gia' in archivio"
AL_MODELLO = "al modello"
PAGINA = "da controllare sulla pagina"
SALVABILE = "salvabile"
# DA_VERIFICARE e' anche un esito: la riga non si salva e si controlla a mano

# Parole che dicono uno sportello chiuso. "graduatoria" e' nel piano: una
# pagina che la pubblica non e' piu' uno sportello aperto da salvare senza
# controllo.
CHIUSURA = re.compile(
    r"\b(?:chius[oa]|esaurit[ei]\s+(?:le\s+)?risorse|risorse\s+esaurit[ei]"
    r"|graduatori[ae])\b",
    re.IGNORECASE,
)

# Lunghezza massima della frase della pagina riportata come prova
PROVA_MAX = 300


class FileNonValido(ValueError):
    """Il file non e' la sezione Incentivi del catalogo."""


@dataclass
class Incentivo:
    """Una riga del file, con i valori gia' divisi e convertiti."""

    id: str
    titolo: str
    concedente: str
    apertura: date | None
    chiusura: date | None
    link: str
    regioni: list[str]
    comuni: list[str]
    tipologie: list[str]
    dimensioni: list[str]
    settori: list[str]
    contributo_min: float | None
    contributo_max: float | None
    costo_min: float | None
    costo_max: float | None

    @property
    def url(self) -> str:
        return url_canonico(self.link) if self.link else ""

    @property
    def nostri_comuni(self) -> list[str]:
        return [c for c in COMUNI_TERRITORIO if c in self.comuni]


@dataclass
class Esame:
    """L'esito dell'esame di una riga, prima e dopo la pagina."""

    incentivo: Incentivo
    stato: str
    classe: str | None
    esito: str
    motivo: str
    prova: str | None = None
    avvisi: list[str] = field(default_factory=list)
    # la riga di bandi, preparata per le righe salvabili
    riga: dict | None = None


def normalizza_nome(nome: str) -> str:
    """Il nome di un ente per il confronto: minuscole, spazi compressi."""
    return " ".join((nome or "").lower().split())


_CLASSE_DI = {
    normalizza_nome(nome): classe
    for classe, nomi in CONCEDENTI.items()
    for nome in nomi
}


def classe_concedente(nome: str) -> str | None:
    """La classe dell'ente concedente, o None se non e' nella tabella."""
    return _CLASSE_DI.get(normalizza_nome(nome))


def _multi(valore: str) -> list[str]:
    return [v.strip() for v in (valore or "").split(SEPARATORE) if v.strip()]


def _comuni(valore: str) -> list[str]:
    return [v.strip() for v in SEPARATORE_COMUNI.split(valore or "") if v.strip()]


def _data(valore: str) -> date | None:
    try:
        return date.fromisoformat((valore or "").strip()[:10])
    except ValueError:
        return None


def _importo(valore: str) -> float | None:
    """Un importo del file; zero o vuoto non e' un valore."""
    try:
        numero = float((valore or "").strip())
    except ValueError:
        return None
    return numero if numero > 0 else None


def _incentivo(riga: dict) -> Incentivo:
    return Incentivo(
        id=riga["ID_Incentivo"].strip(),
        titolo=" ".join(riga["Titolo"].split()),
        concedente=riga["Soggetto_Concedente"].strip(),
        apertura=_data(riga["Data_apertura"]),
        chiusura=_data(riga["Data_chiusura"]),
        link=riga["Link_istituzionale"].strip(),
        regioni=_multi(riga["Regioni"]),
        comuni=_comuni(riga["Comuni"]),
        tipologie=_multi(riga["Tipologia_Soggetto"]),
        dimensioni=_multi(riga["Dimensione_beneficiari"]),
        settori=_multi(riga["Settore_Attivita"]),
        contributo_min=_importo(riga["Agevolazione_Concedibile_Min"]),
        contributo_max=_importo(riga["Agevolazione_Concedibile_Max"]),
        costo_min=_importo(riga["Spesa_Ammessa_Min"]),
        costo_max=_importo(riga["Spesa_Ammessa_Max"]),
    )


def leggi_file(percorso: str | Path) -> list[Incentivo]:
    """Le righe del file, con le colonne lette per nome.

    Il separatore si rileva dal file. Un file senza le colonne della
    sezione Incentivi solleva FileNonValido.
    """
    with Path(percorso).open(encoding="utf-8-sig", newline="") as f:
        testo = f.read()

    try:
        dialetto = csv.Sniffer().sniff(testo[:20000], delimiters=",;")
    except csv.Error as errore:
        raise FileNonValido(f"separatore non riconosciuto: {errore}") from errore

    # Le descrizioni superano il limite predefinito del modulo csv
    csv.field_size_limit(10_000_000)
    lettore = csv.DictReader(testo.splitlines(keepends=True), dialect=dialetto)
    mancanti = [c for c in COLONNE if c not in (lettore.fieldnames or [])]
    if mancanti:
        raise FileNonValido(
            "non e' la sezione Incentivi del catalogo: mancano le colonne "
            + ", ".join(mancanti)
        )
    return [_incentivo(r) for r in lettore]


def stato(incentivo: Incentivo, oggi: date) -> str:
    """Lo stato dalle date del file, solo per decidere: non si memorizza."""
    if incentivo.apertura and incentivo.apertura > oggi:
        return IN_ARRIVO
    if incentivo.chiusura is None:
        return SPORTELLO if incentivo.apertura else SENZA_DATE
    if incentivo.chiusura >= oggi:
        return APERTO
    if (oggi - incentivo.chiusura).days <= GIORNI_STORICO:
        return STORICO
    return SCADUTO


def link_condivisi(incentivi: list[Incentivo]) -> set[str]:
    """Gli URL canonici usati da piu' righe del file: elenchi o home, non bandi."""
    conteggio = Counter(i.url for i in incentivi if i.url)
    return {u for u, n in conteggio.items() if n > 1}


def esamina(
    incentivo: Incentivo,
    oggi: date,
    condivisi: set[str],
    altre_fonti: set[str],
) -> Esame:
    """Decide, senza rete, che cosa fare di una riga.

    condivisi: gli URL usati da piu' righe del file; altre_fonti: gli URL
    gia' in bandi o in scansioni con un'altra fonte, che hanno la
    precedenza (vale il bando acquisito dalla pagina, con le sue prove).
    """
    st = stato(incentivo, oggi)

    def esame(esito, motivo, classe=None):
        return Esame(incentivo, st, classe, esito, motivo)

    if st == SCADUTO:
        return esame(IGNORATA, "scaduto da piu' di 12 mesi secondo il catalogo")

    nostri = incentivo.nostri_comuni
    if "Toscana" not in incentivo.regioni and not nostri:
        return esame(IGNORATA, "fuori dalla Toscana")
    if incentivo.comuni and not nostri:
        return esame(IGNORATA, "elenco di comuni senza i nostri")

    classe = classe_concedente(incentivo.concedente)
    if classe is None:
        return esame(
            DA_VERIFICARE, f"concedente non in tabella: {incentivo.concedente}"
        )
    if classe == ALTRO_TERRITORIO:
        return esame(IGNORATA, "ente di altro territorio", classe)
    if classe == DA_VERIFICARE:
        return esame(
            DA_VERIFICARE, f"concedente da verificare: {incentivo.concedente}", classe
        )

    if st == SENZA_DATE:
        return esame(DA_VERIFICARE, "nessuna data nel catalogo", classe)
    if not incentivo.url:
        return esame(DA_VERIFICARE, "nessun Link_istituzionale", classe)
    if incentivo.url in altre_fonti:
        return esame(GIA_IN_ARCHIVIO, "gia' in archivio da un'altra fonte", classe)
    if incentivo.url in condivisi:
        return esame(
            DA_VERIFICARE,
            "Link_istituzionale usato da piu' righe del file: non e' la pagina "
            "di un bando",
            classe,
        )
    if st in VIVI and "Ente Pubblico" in incentivo.tipologie:
        return esame(
            AL_MODELLO,
            "per enti pubblici: la pagina va letta con il modello",
            classe,
        )
    # Uno sportello senza chiusura aperto da anni e' probabilmente esaurito:
    # dal file non si salva, si controlla a mano (decisione del 13/11/2026).
    # La soglia e' quella dell'avviso "probabilmente esaurito".
    if st == SPORTELLO and incentivo.apertura.isoformat() < _anni_fa(
        oggi.isoformat(), SOGLIA_SPORTELLO_ANNI
    ):
        return esame(
            DA_VERIFICARE,
            f"sportello senza chiusura aperto da piu' di {SOGLIA_SPORTELLO_ANNI} "
            f"anni (dal {incentivo.apertura.isoformat()})",
            classe,
        )
    return esame(PAGINA, "", classe)


def _forme_data(giorno: date) -> list[re.Pattern]:
    """La data in tutte le forme della pagina, con i confini numerici."""
    g, m, a = giorno.day, giorno.month, giorno.year
    gg = f"0?{g}" if g < 10 else str(g)
    mm = f"0?{m}" if m < 10 else str(m)
    mese = next(nome for nome, numero in MESI.items() if numero == m)
    return [
        re.compile(rf"(?<!\d){a}-{m:02d}-{g:02d}(?!\d)"),
        re.compile(rf"(?<![\d.,/]){gg}\s?([/.\-])\s?{mm}\s?\1\s?{a}(?!\d)"),
        re.compile(rf"(?<!\d){gg}(?:°|º)?\s+{mese}\s+{a}(?!\d)", re.IGNORECASE),
    ]


def _frase(testo: str, inizio: int, fine: int) -> str:
    """La riga del testo attorno a una corrispondenza, accorciata se lunga."""
    da = testo.rfind("\n", 0, inizio) + 1
    a = testo.find("\n", fine)
    a = len(testo) if a == -1 else a
    if a - da > PROVA_MAX:
        da = max(da, inizio - PROVA_MAX // 2)
        a = min(a, fine + PROVA_MAX // 2)
    return testo[da:a].strip()


def cerca_data(testo: str, giorno: date) -> str | None:
    """La frase della pagina che contiene la data, in qualunque forma."""
    for schema in _forme_data(giorno):
        trovata = schema.search(testo)
        if trovata:
            return _frase(testo, trovata.start(), trovata.end())
    return None


def parola_di_chiusura(testo: str) -> str | None:
    """La frase della pagina con una parola di chiusura, se c'e'."""
    trovata = CHIUSURA.search(testo)
    return _frase(testo, trovata.start(), trovata.end()) if trovata else None


def _scarica_robots(url: str) -> str:
    richiesta = urllib.request.Request(url, headers=INTESTAZIONI)
    with urllib.request.urlopen(richiesta, timeout=30) as risposta:
        return risposta.read().decode("utf-8", errors="ignore")


class Robots:
    """Le regole di robots.txt di ogni dominio, lette una volta.

    Un robots.txt assente (404, 410) permette tutto; 401 e 403 vietano
    tutto, come urllib.robotparser; altri errori: non leggibile (None).
    """

    def __init__(self, scarica=None) -> None:
        self._scarica = scarica or _scarica_robots
        self._regole: dict[str, RobotFileParser | bool | None] = {}

    def _leggi(self, dominio_url: str) -> RobotFileParser | bool | None:
        try:
            testo = self._scarica(dominio_url + "/robots.txt")
        except urllib.error.HTTPError as errore:
            if errore.code in (404, 410):
                return True
            if errore.code in (401, 403):
                return False
            return None
        except OSError:
            return None
        regole = RobotFileParser()
        regole.parse(testo.splitlines())
        return regole

    def _regole_di(self, url: str) -> RobotFileParser | bool | None:
        parti = urlsplit(url)
        dominio_url = urlunsplit((parti.scheme, parti.netloc, "", "", ""))
        if dominio_url not in self._regole:
            self._regole[dominio_url] = self._leggi(dominio_url)
        return self._regole[dominio_url]

    def permesso(self, url: str) -> bool | None:
        """Il percorso si puo' scaricare; None se robots.txt non si legge."""
        regole = self._regole_di(url)
        if isinstance(regole, bool) or regole is None:
            return regole
        return regole.can_fetch("*", url)

    def attesa(self, url: str) -> float:
        """I secondi da aspettare tra due download dal dominio (Crawl-delay).

        0 se robots.txt non ne indica.
        """
        regole = self._regole_di(url)
        if isinstance(regole, RobotFileParser):
            return float(regole.crawl_delay("*") or 0)
        return 0.0


def indirizzo_ascii(url: str) -> str:
    """L'URL con i caratteri non ASCII codificati (%C3%A0 per "à").

    Il catalogo scrive alcuni link con le lettere accentate, che urllib
    non sa inviare. I caratteri gia' codificati e la punteggiatura degli
    URL restano come sono.
    """
    return quote(url, safe=":/?#[]@!$&'()*+,;=%~")


def controlla_pagina(esame: Esame, scarica, robots: Robots) -> Esame:
    """Controlla sulla pagina dell'ente una riga da salvare, senza modello.

    scarica: la funzione che scarica l'HTML di una pagina. Con una data di
    chiusura, la data deve comparire nella pagina, e la sua frase diventa
    la prova; senza, la pagina deve rispondere e non avere parole di
    chiusura. Altrimenti la riga e' da verificare, con il motivo.
    """
    incentivo = esame.incentivo
    url = indirizzo_ascii(incentivo.url)
    permesso = robots.permesso(url)
    if permesso is None:
        return _da_verificare(esame, "robots.txt del dominio non leggibile")
    if not permesso:
        return _da_verificare(esame, "robots.txt vieta la pagina")

    try:
        html = scarica(url)
    except (OSError, HTTPException, ValueError) as errore:
        return _da_verificare(esame, f"pagina non scaricata ({errore})")
    testo = a_testo(html)

    if incentivo.chiusura:
        frase = cerca_data(testo, incentivo.chiusura)
        if frase is None:
            return _da_verificare(
                esame,
                f"data di chiusura del catalogo ({incentivo.chiusura.isoformat()}) "
                "non trovata sulla pagina",
            )
        esame.prova = frase
    else:
        frase = parola_di_chiusura(ritaglia(testo))
        if frase:
            return _da_verificare(esame, f"sportello, la pagina dice «{frase}»")

    esame.esito = SALVABILE
    return esame


def _da_verificare(esame: Esame, motivo: str) -> Esame:
    esame.esito = DA_VERIFICARE
    esame.motivo = motivo
    return esame


def tipi_impresa(settori: list[str], avvisi: list[str]) -> list[str]:
    """I tipi d'impresa dei settori; senza settori, tutti i tipi d'impresa."""
    if not settori:
        return list(TIPI_IMPRESA)
    tipi = []
    for settore in settori:
        tipo = SETTORI.get(settore)
        if tipo is None:
            avvisi.append(f"Settore_Attivita sconosciuto: '{settore}', nessun tipo")
        elif tipo not in tipi:
            tipi.append(tipo)
    return tipi


def beneficiari_privati(incentivo: Incentivo, avvisi: list[str]) -> list[dict]:
    """Le righe di beneficiari_bando dei tipi privati del catalogo.

    Una per tipologia e tipo, con il valore del file come soggetto e come
    frase. Ente Pubblico non da' righe: i tipi pubblici si salvano solo
    dopo la lettura della pagina con il modello. Un valore sconosciuto non
    da' righe e aggiunge un avviso, mai un tipo plausibile.
    """
    righe, viste = [], set()
    for tipologia in incentivo.tipologie:
        regola = TIPOLOGIE.get(tipologia)
        if regola is None:
            avvisi.append(f"Tipologia_Soggetto sconosciuta: '{tipologia}', nessun tipo")
            continue
        if regola == PUBBLICO:
            continue
        tipi = tipi_impresa(incentivo.settori, avvisi) if regola == IMPRESE else regola
        for tipo in tipi:
            if (tipo, tipologia) in viste:
                continue
            viste.add((tipo, tipologia))
            righe.append(
                {
                    "tipo": tipo,
                    "soggetto": tipologia,
                    "condizioni": None,
                    "frase": tipologia,
                    "confidenza": None,
                    "origine": ORIGINE_CATALOGO,
                }
            )
    return righe


def _territorio(incentivo: Incentivo) -> str:
    if incentivo.nostri_comuni:
        return "Comuni: " + ", ".join(incentivo.nostri_comuni)
    if len(incentivo.regioni) >= 15:
        return f"nazionale ({len(incentivo.regioni)} regioni nel catalogo)"
    return ", ".join(incentivo.regioni)


def _beneficiari_testo(incentivo: Incentivo) -> str:
    testo = "Dal catalogo Incentivi Italia: " + ", ".join(incentivo.tipologie)
    if incentivo.dimensioni:
        testo += "; dimensione: " + ", ".join(incentivo.dimensioni)
    return f"{testo}. {NOTA_CATALOGO}"


def riga_bando(esame: Esame, avvisi: list[str]) -> dict:
    """La riga di bandi per salva(), con i beneficiari privati.

    url, fonte, codice_fonte e verificato_il li mette salva(). Lo stato
    non si memorizza; Descrizione non si copia.
    """
    incentivo = esame.incentivo
    sportello = incentivo.chiusura is None
    if sportello:
        nota = "sportello senza data di chiusura nel catalogo Incentivi Italia"
    else:
        nota = (
            "data di chiusura dal catalogo Incentivi Italia, trovata sulla pagina: "
            f"«{esame.prova}»"
        )
    return {
        "id": f"incentivi-{incentivo.id}",
        "titolo": incentivo.titolo,
        "ente": incentivo.concedente,
        "apertura": incentivo.apertura.isoformat() if incentivo.apertura else None,
        "scadenza": incentivo.chiusura.isoformat() if incentivo.chiusura else None,
        "scadenza_nota": nota,
        "a_sportello": 1 if sportello else 0,
        "beneficiari": _beneficiari_testo(incentivo),
        "territorio": _territorio(incentivo),
        "costo_min": incentivo.costo_min,
        "costo_max": incentivo.costo_max,
        "contributo_min": incentivo.contributo_min,
        "contributo_max": incentivo.contributo_max,
        # Per gli sportelli la data di apertura e' l'indizio dell'eta' del
        # bando: la regola "probabilmente esaurito" la legge da qui
        "pubblicato_il": (
            incentivo.apertura.isoformat() if sportello and incentivo.apertura else None
        ),
        "pubblicato_origine": ORIGINE_APERTURA
        if sportello and incentivo.apertura
        else None,
        "beneficiari_ammessi": beneficiari_privati(incentivo, avvisi),
    }


def prepara_salvataggio(esame: Esame) -> dict | None:
    """La riga da salvare, o None se il catalogo non ha tipi privati.

    Una riga con soli enti pubblici non si salva dal catalogo: diventa da
    verificare, perche' i tipi pubblici richiedono la lettura della pagina.
    """
    riga = riga_bando(esame, esame.avvisi)
    if not riga["beneficiari_ammessi"]:
        _da_verificare(
            esame,
            "nessun tipo privato nel catalogo: i tipi pubblici richiedono la "
            "lettura della pagina con il modello",
        )
        return None
    return riga


def motivo_salvato(esame: Esame) -> str:
    """Il motivo registrato in scansioni per una riga salvata."""
    incentivo = esame.incentivo
    if incentivo.chiusura is None:
        return "a sportello (catalogo Incentivi Italia, pagina controllata)"
    quando = incentivo.chiusura.isoformat()
    if esame.stato == STORICO:
        return f"storico: scaduto il {quando} (catalogo, data trovata sulla pagina)"
    return f"aperto fino al {quando} (catalogo, data trovata sulla pagina)"
