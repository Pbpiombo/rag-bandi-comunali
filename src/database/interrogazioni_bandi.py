"""Interrogazioni sui bandi: filtri per apertura, beneficiari e tema.

Chi puo' presentare domanda si ricava da beneficiari_bando, non si
memorizza nel bando. I bandi non ancora riclassificati con l'estrattore
nuovo (classificato_il vuoto) hanno solo la riga 'comune' migrata dal
vecchio campo si'/no: per loro si sa se ammettono i Comuni, non gli altri
tipi di beneficiari.
"""

import re
import sqlite3
import unicodedata
from datetime import date

from src.database.modelli import Approfondimento, Risultato, VoceBando
from src.estrazione.beneficiari import (
    PER_REQUISITO,
    TIPI_BENEFICIARIO,
    soggetto_generico,
)
from src.estrazione.scadenza import nello_storico

# Anni dalla pubblicazione oltre i quali un bando a sportello e' segnalato
# come probabilmente esaurito. Non si esclude: fondi di garanzia e rotativi
# restano attivi anche per anni.
SOGLIA_SPORTELLO_ANNI = 2

# Tipo di ente (tabella enti) -> tipo di beneficiario
TIPO_PER_ENTE = {"comune": "comune", "unione": "unione_comuni"}

# Come si nomina un tipo di ente nei testi
NOMI_ENTE = {
    "comune": {"uno": "un Comune", "tutti": "i Comuni", "plurale": "Comuni"},
    "unione_comuni": {
        "uno": "un'Unione di Comuni",
        "tutti": "le Unioni di Comuni",
        "plurale": "Unioni di Comuni",
    },
}

# Nome breve di ogni tipo di beneficiario, per le etichette
NOMI_TIPI = {
    "comune": "Comuni",
    "unione_comuni": "Unioni di comuni",
    "altro_ente_pubblico": "altri enti pubblici",
    "impresa_agricola": "imprese agricole",
    "impresa_turistica": "imprese turistiche",
    "impresa_artigiana_commerciale": "imprese artigiane e commerciali",
    "altra_impresa": "altre imprese",
    "professionista_autonomo": "professionisti e autonomi",
    "terzo_settore": "terzo settore",
    "cittadini_famiglie": "cittadini e famiglie",
    "ricerca_formazione": "ricerca e formazione",
    "qualsiasi_soggetto": "chi ha i requisiti indicati",
}

NON_CLASSIFICATI = "altri beneficiari non ancora classificati"
NOTA_UNIONE = "beneficiari non ancora classificati: verificare se ammette le Unioni"

# Un bando senza scadenza e non a sportello: la pagina non dice fino a
# quando si puo' presentare domanda, e non si sa se e' ancora aperto
SENZA_SCADENZA = "scadenza non indicata, da verificare sul bando"

# "Da approfondire": i bandi pertinenti con un dato essenziale mancante o
# incerto. Non stanno nelle liste: l'app li mostra sotto la risposta, senza
# passare dal modello. Solo i recenti, al piu' MAX_DA_APPROFONDIRE.
PROBLEMA_SCADENZA = "scadenza non indicata"
PROBLEMA_ESAURITO = "sportello probabilmente esaurito"
PROBLEMA_BENEFICIARI = "beneficiari non indicati sulla pagina"
PROBLEMA_RIMANDO = "beneficiari non indicati sulla pagina, requisiti nell'avviso"
MAX_DA_APPROFONDIRE = 10
ANNI_DA_APPROFONDIRE = 2
ANNO_NEL_TITOLO = re.compile(r"(?<!\d)(20\d{2})(?!\d)")
BENEFICIARI_NON_INDICATI = "non indicati sulla pagina"

# Un bando classificato senza righe di beneficiari: la pagina non dice chi
# puo' presentare domanda. Compare tra i bandi da approfondire per tutti.
SENZA_RIGHE_BENEFICIARI = (
    "(bandi.classificato_il IS NOT NULL AND NOT EXISTS (SELECT 1 FROM "
    "beneficiari_bando AS b WHERE b.id_bando = bandi.id))"
)
GRUPPO_SPORTELLO = "A sportello, finché ci sono risorse:"
GRUPPO_SENZA_SCADENZA = "Scadenza non indicata, da verificare sul bando:"
# Un bando a finestre tra una finestra chiusa e la prossima
GRUPPO_PROSSIMA = "Chiusi ora, con una prossima finestra:"
# I bandi scaduti da non piu' di scadenza.GIORNI_STORICO giorni: lo
# storico. Non compaiono mai tra gli aperti; nelle liste per tema stanno in
# un blocco a parte. Quelli piu' vecchi restano in archivio e si trovano
# per nome (dettaglio_bando), ma non nelle liste.
GRUPPO_STORICO = "Scaduti, solo come storico: non più aperti:"
NESSUNO_APERTO_TEMA = "Nessun bando aperto su questo tema alla data del {oggi}."

# Le pagine in archivio che non sono bandi (natura 'non_bando') restano
# nel database ma non compaiono negli elenchi ne' nei conteggi
SOLO_BANDI = "bandi.natura = 'bando'"

# Un bando ammette un tipo di beneficiario: ha una riga di quel tipo.
# Il tipo e' il parametro.
HA_TIPO = (
    "EXISTS (SELECT 1 FROM beneficiari_bando AS b "
    "WHERE b.id_bando = bandi.id AND b.tipo = ?)"
)


def filtro_ente(tipo: str) -> tuple[str, list]:
    """La condizione SQL dei bandi a cui un tipo di ente puo' partecipare.

    Ammette il bando una riga del suo tipo o di qualsiasi_soggetto. Per
    l'Unione valgono anche i bandi non ancora classificati che ammettono
    i Comuni: prima della migrazione li vedeva, e la nota li segnala.
    """
    sql = f"({HA_TIPO} OR {HA_TIPO})"
    parametri = [tipo, PER_REQUISITO]
    if tipo == "unione_comuni":
        sql = f"({sql} OR (bandi.classificato_il IS NULL AND {HA_TIPO}))"
        parametri.append("comune")
    return sql, parametri


def data_di_oggi() -> date:
    """La data di oggi: l'unico punto in cui le interrogazioni la leggono."""
    return date.today()


def tipo_ente(conn: sqlite3.Connection, codice_ente: str) -> str | None:
    """Il tipo di beneficiario corrispondente all'ente, se gestito."""
    riga = conn.execute(
        "SELECT tipo FROM enti WHERE codice_fiscale = ?", (codice_ente,)
    ).fetchone()
    return TIPO_PER_ENTE.get(riga["tipo"]) if riga else None


def _ente_non_gestito(codice_ente: str) -> Risultato:
    return Risultato(
        f"L'ente {codice_ente} non e' un Comune ne' un'Unione di Comuni in "
        "archivio: non so a quali bandi possa partecipare.",
        trovato=False,
    )


def beneficiari_di(conn: sqlite3.Connection, id_bando: str) -> list:
    """Le righe di beneficiari_bando di un bando, in ordine di tipo."""
    return conn.execute(
        "SELECT * FROM beneficiari_bando WHERE id_bando = ? ORDER BY tipo, frase",
        (id_bando,),
    ).fetchall()


def euro(valore) -> str:
    """Formatta un importo con il separatore di migliaia italiano.

    Python usa la convenzione americana con la virgola; qui serve il punto
    per le migliaia e la virgola per i decimali. I centesimi si scrivono
    solo se ci sono: un importo arrotondato all'euro e' un valore che nel
    bando non esiste, e il verificatore lo confermerebbe confrontandolo
    con questa riga (voce 5 della revisione).
    """
    if not valore:
        return "?"
    if float(valore).is_integer():
        return f"{valore:,.0f}".replace(",", ".")
    americano = f"{valore:,.2f}"
    return americano.replace(",", "_").replace(".", ",").replace("_", ".")


def _anni_fa(oggi: str, anni: int) -> str:
    """La data di oggi spostata indietro di alcuni anni."""
    giorno = date.fromisoformat(oggi)
    try:
        return giorno.replace(year=giorno.year - anni).isoformat()
    except ValueError:  # 29 febbraio
        return giorno.replace(year=giorno.year - anni, day=28).isoformat()


def probabilmente_esaurito(riga, oggi: str) -> bool:
    """Uno sportello senza data di chiusura pubblicato da oltre la soglia."""
    pubblicato = riga["pubblicato_il"]
    return bool(
        riga["a_sportello"]
        and not riga["scadenza"]
        and pubblicato
        and pubblicato < _anni_fa(oggi, SOGLIA_SPORTELLO_ANNI)
    )


def stato_sportello(riga, oggi: str) -> str:
    """Lo stato di un bando a sportello, con l'invito a verificare le risorse.

    L'avviso "probabilmente esaurito" vale solo per gli sportelli senza data
    di chiusura: con una scadenza futura lo sportello e' aperto fino a quella
    data, salvo esaurimento delle risorse, che l'invito a verificare dice gia'.
    Uno sportello con la data di chiusura passata e' chiuso: nessun invito
    a verificare le risorse.
    """
    pubblicato = riga["pubblicato_il"]
    if riga["scadenza"] and riga["scadenza"] < oggi:
        return f"era a sportello fino al {riga['scadenza']}"
    if riga["scadenza"]:
        return (
            f"a sportello fino al {riga['scadenza']}, "
            "verificare la disponibilità delle risorse"
        )

    quando = (
        f"pubblicato il {pubblicato}"
        if pubblicato
        else "data di pubblicazione non indicata"
    )
    testo = f"a sportello, verificare la disponibilità delle risorse ({quando})"
    if pubblicato and pubblicato < _anni_fa(oggi, SOGLIA_SPORTELLO_ANNI):
        testo += (
            f" | pubblicato da oltre {SOGLIA_SPORTELLO_ANNI} anni: "
            "probabilmente esaurito"
        )
    return testo


def come_requisito(b) -> bool:
    """La riga va mostrata con il soggetto del bando.

    Vale per qualsiasi_soggetto e per i soggetti generici ("soggetti
    pubblici e/o privati che operano nel campo della ricerca"): il tipo
    da solo perderebbe la qualificazione.
    """
    return b["tipo"] == PER_REQUISITO or soggetto_generico(b["soggetto"])


def caso_ammissione(b) -> str:
    """Una riga di beneficiari come caso di ammissione."""
    if b["condizioni"]:
        caso = f"ammesso se {b['condizioni']}"
        if come_requisito(b) and b["soggetto"]:
            caso += f" (nel bando: «{b['soggetto']}»)"
        return caso
    return f"ammesso come «{b['soggetto']}» nel bando"


def ammissione(beneficiari: list, tipo: str) -> str | None:
    """Come e' ammesso un tipo di ente, se ci sono condizioni.

    Senza condizioni restituisce None: il bando e' nell'elenco perche'
    l'ente e' ammesso, e non serve dirlo. Con piu' righe, le condizioni
    si uniscono con "oppure". Per qualsiasi_soggetto e per i soggetti
    generici si aggiunge, tra parentesi, il soggetto come lo chiama il
    bando; senza condizioni, "ammesso come «...» nel bando".
    """
    pertinenti = [b for b in beneficiari if b["tipo"] in (tipo, PER_REQUISITO)]
    if not pertinenti or any(
        b["tipo"] == tipo and not b["condizioni"] and not come_requisito(b)
        for b in pertinenti
    ):
        return None

    return " oppure ".join(caso_ammissione(b) for b in pertinenti)


def scadenze_di(conn: sqlite3.Connection, id_bando: str) -> list:
    """Le righe di scadenze_bando di un bando, in ordine di numero.

    Ci sono solo per i bandi con piu' date: per gli altri l'elenco e' vuoto
    e lo stato si calcola da bandi.scadenza.
    """
    return conn.execute(
        "SELECT * FROM scadenze_bando WHERE id_bando = ? ORDER BY numero",
        (id_bando,),
    ).fetchall()


def finestre(scadenze: list, oggi: str) -> tuple[list, list, object]:
    """Le date di genere 'domanda': tutte, quelle aperte oggi, la prossima.

    Una finestra e' aperta se l'apertura e' passata o vuota e la scadenza
    non e' passata. La prossima e' quella che apre per prima dopo oggi.
    """
    domande = [s for s in scadenze if s["genere"] == "domanda"]
    aperte = [
        s
        for s in domande
        if (not s["apertura"] or s["apertura"] <= oggi) and s["scadenza"] >= oggi
    ]
    future = [s for s in domande if s["apertura"] and s["apertura"] > oggi]
    prossima = min(future, key=lambda s: s["apertura"]) if future else None
    return domande, aperte, prossima


def _fra(scadenza: str, oggi: str) -> int:
    return (date.fromisoformat(scadenza) - date.fromisoformat(oggi)).days


def _giorni(quanti: int) -> str:
    return "1 giorno" if quanti == 1 else f"{quanti} giorni"


def tra_quanto(giorni: int) -> str:
    """Quanto manca a una scadenza, o da quanto e' passata.

    "oggi", "fra 1 giorno", "fra 12 giorni", "SCADUTO da 3 giorni".
    """
    if giorni < 0:
        return f"SCADUTO da {_giorni(-giorni)}"
    if giorni == 0:
        return "oggi"
    return f"fra {_giorni(giorni)}"


def stato_finestre(riga, scadenze: list, oggi: str) -> str | None:
    """Lo stato di un bando con piu' date, calcolato dalle righe.

    None se il bando non ha date di genere 'domanda' o sono tutte passate:
    allora vale lo stato calcolato da bandi.scadenza.
    """
    domande, aperte, prossima = finestre(scadenze, oggi)
    if not domande or not (aperte or prossima):
        return None

    dopo = (
        f"prossima finestra dal {prossima['apertura']} al {prossima['scadenza']} "
        f"({prossima['descrizione']})"
        if prossima
        else None
    )
    if not aperte:
        return f"chiuso ora, {dopo}"

    stato = "; ".join(
        f"finestra aperta fino al {s['scadenza']} ({s['descrizione']}, "
        f"{tra_quanto(_fra(s['scadenza'], oggi))})"
        for s in aperte
    )
    if riga["a_sportello"]:
        stato += ", a sportello: verificare la disponibilità delle risorse"
    if dopo:
        stato += f"; {dopo}"
    return stato


def scaduto(riga, scadenze: list, oggi: str) -> bool:
    """Il bando e' scaduto alla data oggi (ISO): storico, non aperto.

    Come in stato_documenti.stato_bando: un bando con piu' date segue le
    sue finestre, e non e' scaduto se ne ha una aperta o futura; gli altri
    sono scaduti se la scadenza e' passata, anche a sportello. La stessa
    condizione degli elenchi degli aperti (scadenza IS NULL OR scadenza >=
    oggi), con le finestre in piu'.
    """
    if stato_finestre(riga, scadenze, oggi):
        return False
    return bool(riga["scadenza"]) and riga["scadenza"] < oggi


def scadenza_vicina(riga, scadenze: list, oggi: str) -> str | None:
    """La prossima data entro cui presentare domanda.

    Per un bando con piu' date, la scadenza della finestra aperta che chiude
    per prima, o None se nessuna e' aperta; per gli altri, bandi.scadenza.
    """
    domande, aperte, _ = finestre(scadenze, oggi)
    if domande:
        return min((s["scadenza"] for s in aperte), default=None)
    return riga["scadenza"]


def fasi_successive(scadenze: list, oggi: str) -> str | None:
    """Le scadenze per chi ha gia' superato una fase, se non passate.

    Non aprono il bando a nuove domande: si mostrano solo come informazione.
    """
    fasi = [
        f"{s['descrizione']} entro il {s['scadenza']}"
        for s in scadenze
        if s["genere"] == "fase_successiva" and s["scadenza"] >= oggi
    ]
    if not fasi:
        return None
    return "fase successiva, solo per chi ha superato la precedente: " + "; ".join(fasi)


def formatta_bando(
    riga,
    oggi: str,
    nota: str | None = None,
    scadenze: list = (),
    chiusura_sportello: str | None = None,
) -> str:
    """Una riga di bando in forma leggibile.

    nota: come e' ammesso l'ente, o perche' va verificato; si aggiunge
    dopo i beneficiari. scadenze: le righe di scadenze_bando, per i bandi
    con piu' date. chiusura_sportello: per gli elenchi delle scadenze, la
    data di chiusura di uno sportello, che prende il posto dello stato.
    """
    pezzi = [f"«{riga['titolo']}» ({riga['ente']})"]

    stato_date = stato_finestre(riga, scadenze, oggi)
    if chiusura_sportello:
        quando = tra_quanto(_fra(chiusura_sportello, oggi))
        pezzi.append(
            f"a sportello, chiude il {chiusura_sportello} ({quando}), "
            "salvo esaurimento delle risorse"
        )
    elif stato_date:
        pezzi.append(stato_date)
    elif riga["a_sportello"]:
        pezzi.append(stato_sportello(riga, oggi))
    elif riga["scadenza"]:
        quando = tra_quanto(_fra(riga["scadenza"], oggi))
        pezzi.append(f"scade il {riga['scadenza']} ({quando})")
    else:
        pezzi.append(SENZA_SCADENZA)

    fasi = fasi_successive(scadenze, oggi)
    if fasi:
        pezzi.append(fasi)

    if riga["scadenza_nota"]:
        pezzi.append(f"nota: {riga['scadenza_nota']}")

    pezzi.append(f"beneficiari: {riga['beneficiari'] or BENEFICIARI_NON_INDICATI}")

    if nota:
        pezzi.append(nota)

    if riga["contributo_perc"]:
        pezzi.append(f"contributo fino al {riga['contributo_perc']:.0f}%")

    # Quanto si puo' chiedere: la domanda piu' probabile su un bando
    if riga["contributo_min"] and riga["contributo_max"]:
        pezzi.append(
            f"contributo da {euro(riga['contributo_min'])} "
            f"a {euro(riga['contributo_max'])} euro"
        )
    elif riga["contributo_max"]:
        pezzi.append(f"contributo fino a {euro(riga['contributo_max'])} euro")
    elif riga["contributo_min"]:
        pezzi.append(f"contributo da almeno {euro(riga['contributo_min'])} euro")

    if riga["costo_min"] and riga["costo_max"]:
        pezzi.append(
            f"progetto ammissibile da {euro(riga['costo_min'])} "
            f"a {euro(riga['costo_max'])} euro"
        )
    elif riga["costo_max"]:
        pezzi.append(f"progetto fino a {euro(riga['costo_max'])} euro")
    elif riga["costo_min"]:
        pezzi.append(f"progetto da almeno {euro(riga['costo_min'])} euro")

    if riga["premialita"]:
        pezzi.append(f"premialità: {riga['premialita']}")

    # L'atto sta nella riga del bando: il modello lo cita insieme
    # all'etichetta di quel bando, non lo prende dall'intestazione del blocco
    pezzi.append(f"atto: {riga['riferimento_atto'] or 'non indicato'}")
    pezzi.append(f"url: {riga['url']}")

    return " | ".join(pezzi)


def fonte_bando(riga) -> str:
    """La fonte di un bando, con la data in cui i dati sono stati estratti.

    La colonna si chiama verificato_il, ma per i bandi e' la data
    dell'estrazione automatica, non di una verifica umana (voce 8 della
    revisione): "estratti il", non "verificati il".
    """
    return (
        f"{riga['fonte']}, {riga['riferimento_atto']} "
        f"(dati estratti il {riga['verificato_il']})"
    )


def nota_per_ente(conn: sqlite3.Connection, riga, tipo: str) -> str | None:
    """La nota di un bando nell'elenco di un tipo di ente."""
    beneficiari = beneficiari_di(conn, riga["id"])
    if tipo == "unione_comuni" and riga["classificato_il"] is None:
        if not any(b["tipo"] in (tipo, PER_REQUISITO) for b in beneficiari):
            return NOTA_UNIONE
    return ammissione(beneficiari, tipo)


class RigheBandi:
    """Le righe di bandi di un risultato, ciascuna con la fonte del suo bando.

    Ogni riga riceve nel testo il segnaposto [#k], nell'ordine in cui si
    scrive; la voce k di Risultato.voci e' la stessa riga.
    """

    def __init__(self) -> None:
        self.voci: list[VoceBando] = []

    def numera(self, riga, testo: str) -> str:
        """Il testo della riga preceduto dal suo segnaposto."""
        self.voci.append(
            VoceBando(
                testo,
                fonte_bando(riga),
                titolo=riga["titolo"] or "",
                url=riga["url"] or "",
            )
        )
        return f"[#{len(self.voci)}] {testo}"


def _elenco(
    conn,
    righe,
    oggi: str,
    tipo: str,
    numerate: RigheBandi,
    chiusure: dict | None = None,
) -> str:
    """chiusure: id -> data di chiusura degli sportelli, per le scadenze."""
    chiusure = chiusure or {}
    return "\n".join(
        "- "
        + numerate.numera(
            r,
            formatta_bando(
                r,
                oggi,
                nota_per_ente(conn, r, tipo),
                scadenze_di(conn, r["id"]),
                chiusura_sportello=chiusure.get(r["id"]),
            ),
        )
        for r in righe
    )


def senza_scadenza(riga) -> bool:
    """Un bando che non e' a sportello e non ha scadenza."""
    return not riga["a_sportello"] and not riga["scadenza"]


def senza_beneficiari(riga, beneficiari: list) -> bool:
    """La pagina non dice chi puo' presentare domanda.

    Un bando classificato senza righe di beneficiari: si e' salvato con i
    beneficiari vuoti. I bandi non ancora classificati non contano.
    """
    return riga["classificato_il"] is not None and not beneficiari


def problema(conn: sqlite3.Connection, riga, oggi: str) -> str | None:
    """Il dato essenziale che manca o e' incerto, in poche parole; None se chiaro.

    Si calcola a ogni domanda, non si memorizza. Un bando con un problema
    non sta nelle liste principali: va nella sezione "Da approfondire".
    """
    pezzi = []
    if senza_beneficiari(riga, beneficiari_di(conn, riga["id"])):
        pezzi.append(
            PROBLEMA_RIMANDO if riga["beneficiari_rimando"] else PROBLEMA_BENEFICIARI
        )
    domande, _, _ = finestre(scadenze_di(conn, riga["id"]), oggi)
    if not domande:
        if senza_scadenza(riga):
            pezzi.append(PROBLEMA_SCADENZA)
        elif probabilmente_esaurito(riga, oggi):
            pezzi.append(PROBLEMA_ESAURITO)
    return "; ".join(pezzi) or None


def anni_nel_titolo(titolo: str) -> list[int]:
    """Gli anni scritti nel titolo (es. "bando 2026-2027" -> [2026, 2027])."""
    return [int(a) for a in ANNO_NEL_TITOLO.findall(titolo or "")]


def recente(riga, oggi: str) -> bool:
    """Pubblicato negli ultimi anni, o con un anno recente nel titolo.

    Solo i bandi recenti compaiono in "Da approfondire": i piu' vecchi
    (es. festival 2021) finiscono nel controllo degli scarti.
    """
    pubblicato = riga["pubblicato_il"]
    if pubblicato and pubblicato >= _anni_fa(oggi, ANNI_DA_APPROFONDIRE):
        return True
    anni = anni_nel_titolo(riga["titolo"])
    return bool(anni) and max(anni) >= date.fromisoformat(oggi).year - 1


def _quando(riga) -> str:
    """La data per ordinare dal piu' recente: pubblicazione, o anno del titolo."""
    anni = anni_nel_titolo(riga["titolo"])
    return riga["pubblicato_il"] or (f"{max(anni)}-01-01" if anni else "")


def da_approfondire(con_problema: list, oggi: str) -> list[Approfondimento]:
    """Le voci della sezione "Da approfondire": recenti, al piu' MAX, in ordine.

    con_problema: coppie (riga del bando, problema).
    """
    recenti = [(r, p) for r, p in con_problema if recente(r, oggi)]
    recenti.sort(key=lambda coppia: _quando(coppia[0]), reverse=True)
    return [
        Approfondimento(r["titolo"], r["url"], p, r["contatti"])
        for r, p in recenti[:MAX_DA_APPROFONDIRE]
    ]


def dividi(conn: sqlite3.Connection, righe: list, oggi: str) -> tuple[list, list]:
    """I bandi chiari, e quelli con un problema con il loro problema."""
    chiari, con_problema = [], []
    for r in righe:
        p = problema(conn, r, oggi)
        if p:
            con_problema.append((r, p))
        else:
            chiari.append(r)
    return chiari, con_problema


def gruppi_aperti(conn: sqlite3.Connection, righe: list, oggi: str) -> tuple:
    """Divide i bandi non scaduti in quattro gruppi.

    Con scadenza, a sportello, senza scadenza, e chiusi ora con una
    prossima finestra. Solo i primi due sono aperti di sicuro; per i bandi
    senza scadenza la pagina non dice fino a quando si puo' presentare
    domanda. Per i bandi con piu' date lo stato si calcola dalle righe di
    scadenze_bando: con una finestra aperta stanno nei primi due gruppi,
    tra due finestre nel quarto; con tutte le date passate non compaiono.
    """
    a_scadenza, a_sportello, da_verificare, prossima = [], [], [], []
    for r in righe:
        domande, aperte, dopo = finestre(scadenze_di(conn, r["id"]), oggi)
        if domande:
            if aperte:
                (a_sportello if r["a_sportello"] else a_scadenza).append(r)
            elif dopo:
                prossima.append(r)
        elif r["a_sportello"]:
            a_sportello.append(r)
        elif r["scadenza"]:
            a_scadenza.append(r)
        else:
            da_verificare.append(r)
    return a_scadenza, a_sportello, da_verificare, prossima


def testo_gruppi(intestazione: str, gruppi: tuple, elenco) -> str:
    """L'elenco dei bandi non scaduti, nei quattro gruppi di gruppi_aperti.

    intestazione: la prima riga, per i bandi aperti di sicuro (con scadenza
    o a sportello); elenco: la funzione che scrive le righe di un gruppo.
    """
    a_scadenza, a_sportello, da_verificare, prossima = gruppi
    testo = intestazione
    if a_scadenza:
        testo += f"\n{elenco(a_scadenza)}"
    if a_sportello:
        testo += f"\n{GRUPPO_SPORTELLO}\n{elenco(a_sportello)}"
    if da_verificare:
        testo += f"\n{GRUPPO_SENZA_SCADENZA}\n{elenco(da_verificare)}"
    if prossima:
        testo += f"\n{GRUPPO_PROSSIMA}\n{elenco(prossima)}"
    return testo


def nessuno_aperto(per_chi: str, oggi: str, gruppi: tuple) -> str:
    """L'intestazione quando nessun bando e' aperto di sicuro."""
    if gruppi[2]:
        return (
            f"Nessun bando aperto di sicuro per {per_chi} alla data del "
            f"{oggi}: nessuno ha una scadenza futura o e' a sportello."
        )
    return f"Nessun bando aperto ora per {per_chi} alla data del {oggi}."


def fonti_dei_gruppi(righe: list, gruppi: tuple) -> list[str]:
    """Le fonti dei bandi mostrati, nell'ordine delle righe.

    Un bando con tutte le finestre passate non sta in nessun gruppo e non
    e' mostrato: la sua fonte non si elenca.
    """
    mostrati = {r["id"] for gruppo in gruppi for r in gruppo}
    return [fonte_bando(r) for r in righe if r["id"] in mostrati]


def bandi_aperti_per_ente(conn: sqlite3.Connection, codice_ente: str) -> Risultato:
    """I bandi ancora aperti a cui l'ente può presentare domanda."""
    tipo = tipo_ente(conn, codice_ente)
    if tipo is None:
        return _ente_non_gestito(codice_ente)
    nomi = NOMI_ENTE[tipo]
    oggi = data_di_oggi().isoformat()
    filtro, parametri = filtro_ente(tipo)

    tutte = conn.execute(
        f"""
        SELECT * FROM bandi
        WHERE ({filtro} OR {SENZA_RIGHE_BENEFICIARI})
          AND {SOLO_BANDI}
          AND (scadenza IS NULL OR scadenza >= ?)
        ORDER BY a_sportello, scadenza
        """,
        (*parametri, oggi),
    ).fetchall()
    righe, con_problema = dividi(conn, tutte, oggi)
    approfondire = da_approfondire(con_problema, oggi)

    if not righe:
        totale = conn.execute(
            f"SELECT COUNT(*) FROM bandi WHERE {filtro} AND {SOLO_BANDI}", parametri
        ).fetchone()[0]
        testo = (
            f"Nessun bando aperto per {nomi['tutti']} alla data del {oggi}. "
            f"In archivio ce ne sono {totale} rivolti a {nomi['tutti']}, "
            "tutti scaduti."
            if not con_problema
            else f"Nessun bando aperto con dati completi per {nomi['tutti']} "
            f"alla data del {oggi}."
        )
        return Risultato(testo, trovato=False, da_approfondire=approfondire)

    gruppi = gruppi_aperti(conn, righe, oggi)
    aperti = len(gruppi[0]) + len(gruppi[1])
    intestazione = (
        f"Bandi aperti a cui {nomi['uno']} può presentare domanda "
        f"(alla data del {oggi}), {aperti} in archivio:"
        if aperti
        else nessuno_aperto(nomi["tutti"], oggi, gruppi)
    )
    numerate = RigheBandi()
    testo = testo_gruppi(
        intestazione,
        gruppi,
        lambda gruppo: _elenco(conn, gruppo, oggi, tipo, numerate),
    )

    return Risultato(
        testo,
        fonti=fonti_dei_gruppi(righe, gruppi),
        voci=numerate.voci,
        da_approfondire=approfondire,
    )


def bandi_in_scadenza(
    conn: sqlite3.Connection, codice_ente: str, giorni: int = 60
) -> Risultato:
    """I bandi per l'ente che scadono entro un certo numero di giorni.

    Entrano anche gli sportelli con una data di chiusura nella finestra,
    segnalati come sportelli: possono chiudere prima, se finiscono le
    risorse. Gli sportelli senza data di chiusura restano fuori.
    """
    tipo = tipo_ente(conn, codice_ente)
    if tipo is None:
        return _ente_non_gestito(codice_ente)
    plurale = NOMI_ENTE[tipo]["plurale"]
    oggi = data_di_oggi()
    limite = date.fromordinal(oggi.toordinal() + giorni).isoformat()
    filtro, parametri = filtro_ente(tipo)

    # bandi.scadenza e' l'ultima data: per un bando a finestre la scadenza
    # che conta e' quella della finestra aperta, che si calcola dalle righe
    candidati = conn.execute(
        f"""
        SELECT * FROM bandi
        WHERE ({filtro} OR {SENZA_RIGHE_BENEFICIARI})
          AND {SOLO_BANDI}
          AND scadenza >= ?
        ORDER BY scadenza
        """,
        (*parametri, oggi.isoformat()),
    ).fetchall()
    in_scadenza = []
    for r in candidati:
        scadenza = scadenza_vicina(r, scadenze_di(conn, r["id"]), oggi.isoformat())
        if scadenza and scadenza <= limite:
            in_scadenza.append((scadenza, r))
    ordinate = [r for _, r in sorted(in_scadenza, key=lambda coppia: coppia[0])]
    righe, con_problema = dividi(conn, ordinate, oggi.isoformat())
    approfondire = da_approfondire(con_problema, oggi.isoformat())

    if not righe:
        return Risultato(
            f"Nessun bando per {plurale} in scadenza nei prossimi {giorni} giorni.",
            trovato=False,
            da_approfondire=approfondire,
        )

    numerate = RigheBandi()
    chiusure = {r["id"]: s for s, r in in_scadenza if r["a_sportello"]}
    elenco = _elenco(conn, righe, oggi.isoformat(), tipo, numerate, chiusure)

    return Risultato(
        f"Bandi per {plurale} in scadenza entro {giorni} giorni:\n{elenco}",
        fonti=[fonte_bando(r) for r in righe],
        voci=numerate.voci,
        da_approfondire=approfondire,
    )


def etichetta_tipi(riga, beneficiari: list) -> str:
    """I tipi ammessi da un bando, per gli elenchi non legati a un ente.

    Un tipo con tutte le righe condizionate e' segnato "a condizione".
    Per i bandi non ancora classificati si sa solo se ammettono i Comuni.
    """
    if riga["classificato_il"] is None:
        if any(b["tipo"] == "comune" for b in beneficiari):
            return f"[ammessi: Comuni; {NON_CLASSIFICATI}]"
        return f"[NON per i Comuni; {NON_CLASSIFICATI}]"

    nomi = []
    for tipo in TIPI_BENEFICIARIO:
        righe = [b for b in beneficiari if b["tipo"] == tipo]
        if righe:
            condizionato = all(b["condizioni"] or come_requisito(b) for b in righe)
            nomi.append(NOMI_TIPI[tipo] + (" (a condizione)" if condizionato else ""))
    return f"[ammessi: {', '.join(nomi)}]"


def bandi_per_tema(conn: sqlite3.Connection, tema: str) -> Risultato:
    """I bandi di un certo tema, con l'indicazione se aperti e per chi.

    Prima gli aperti, poi lo storico: gli scaduti da non piu' di
    GIORNI_STORICO giorni. Gli scaduti piu' vecchi non si elencano. Se non
    resta nessun bando da elencare, trovato e' False.

    Il tema in archivio e' una categoria generale: se non trova niente, si
    cercano le parole nei titoli (trova_bandi), e lo si dice in testa.
    """
    oggi = data_di_oggi().isoformat()

    righe = conn.execute(
        f"SELECT * FROM bandi WHERE tema LIKE ? AND {SOLO_BANDI} "
        "ORDER BY scadenza DESC",
        (f"%{tema.lower()}%",),
    ).fetchall()
    intestazione = f"Bandi sul tema '{tema}' in archivio:\n"

    if not righe:
        nei_titoli = [r for r in trova_bandi(conn, tema) if r["natura"] == "bando"]
        # Lo stesso ordine della query sul tema: in SQLite i NULL vanno in
        # fondo con DESC
        righe = sorted(nei_titoli, key=lambda r: r["scadenza"] or "", reverse=True)
        intestazione = (
            f"Nessun bando con il tema '{tema}'; questi bandi lo nominano nel titolo:\n"
        )

    if not righe:
        temi = conn.execute(
            f"SELECT DISTINCT tema FROM bandi WHERE tema IS NOT NULL AND {SOLO_BANDI}"
        ).fetchall()
        elenco = ", ".join(r["tema"] for r in temi) or "nessuno"
        return Risultato(
            f"Nessun bando sul tema '{tema}'. Temi in archivio: {elenco}.",
            trovato=False,
        )

    # Gli aperti prima, gli scaduti da meno di un anno in un blocco a parte:
    # lo storico non si confonde con le opportunita' di oggi. La
    # numerazione prosegue. Gli scaduti piu' vecchi non entrano.
    giorno = date.fromisoformat(oggi)
    aperti, storici, con_problema = [], [], []
    for r in righe:
        scadenze = scadenze_di(conn, r["id"])
        if not scaduto(r, scadenze, oggi):
            p = problema(conn, r, oggi)
            if p:
                con_problema.append((r, p))
            else:
                aperti.append((r, scadenze))
        elif nello_storico(r["scadenza"], giorno):
            storici.append((r, scadenze))

    numerate = RigheBandi()

    def elenco(gruppo):
        return "\n".join(
            "- "
            + numerate.numera(
                r,
                f"{etichetta_tipi(r, beneficiari_di(conn, r['id']))} "
                f"{formatta_bando(r, oggi, scadenze=scadenze)}",
            )
            for r, scadenze in gruppo
        )

    testo = intestazione
    testo += elenco(aperti) if aperti else NESSUNO_APERTO_TEMA.format(oggi=oggi)
    if storici:
        testo += f"\n{GRUPPO_STORICO}\n{elenco(storici)}"

    return Risultato(
        testo,
        fonti=[fonte_bando(r) for r, _ in [*aperti, *storici]],
        voci=numerate.voci,
        trovato=bool(aperti or storici),
        da_approfondire=da_approfondire(con_problema, oggi),
    )


def bandi_per_beneficiario(conn: sqlite3.Connection, tipo: str) -> Risultato:
    """I bandi aperti che ammettono un tipo di beneficiario della lista chiusa."""
    if tipo not in TIPI_BENEFICIARIO:
        validi = ", ".join(f"{t} ({n})" for t, n in NOMI_TIPI.items())
        return Risultato(
            f"Tipo di beneficiario '{tipo}' sconosciuto. Tipi validi: {validi}.",
            trovato=False,
        )
    oggi = data_di_oggi().isoformat()

    tutte = conn.execute(
        f"""
        SELECT * FROM bandi
        WHERE ({HA_TIPO} OR {SENZA_RIGHE_BENEFICIARI})
          AND {SOLO_BANDI}
          AND (scadenza IS NULL OR scadenza >= ?)
        ORDER BY a_sportello, scadenza
        """,
        (tipo, oggi),
    ).fetchall()
    righe, con_problema = dividi(conn, tutte, oggi)
    approfondire = da_approfondire(con_problema, oggi)

    # I bandi aperti non classificati: se ammettono questo tipo non si sa,
    # salvo per i Comuni, che hanno la riga migrata
    da_classificare = conn.execute(
        "SELECT COUNT(*) FROM bandi WHERE classificato_il IS NULL "
        f"AND {SOLO_BANDI} AND (scadenza IS NULL OR scadenza >= ?)",
        (oggi,),
    ).fetchone()[0]
    avvertenza = (
        f"\n{da_classificare} bandi aperti in archivio hanno beneficiari non "
        "ancora classificati: potrebbero ammettere anche questo tipo."
        if da_classificare and tipo != "comune"
        else ""
    )

    nome = NOMI_TIPI[tipo]
    if not righe:
        return Risultato(
            f"Nessun bando aperto per {nome} alla data del {oggi}.{avvertenza}",
            trovato=False,
            da_approfondire=approfondire,
        )

    numerate = RigheBandi()

    def elenco(gruppo):
        return "\n".join(
            "- "
            + numerate.numera(
                r,
                formatta_bando(
                    r,
                    oggi,
                    ammissione(beneficiari_di(conn, r["id"]), tipo),
                    scadenze_di(conn, r["id"]),
                ),
            )
            for r in gruppo
        )

    gruppi = gruppi_aperti(conn, righe, oggi)
    aperti = len(gruppi[0]) + len(gruppi[1])
    intestazione = (
        f"Bandi aperti per {nome} (alla data del {oggi}), {aperti} in archivio:"
        if aperti
        else nessuno_aperto(nome, oggi, gruppi)
    )
    return Risultato(
        testo_gruppi(intestazione, gruppi, elenco) + avvertenza,
        fonti=fonti_dei_gruppi(righe, gruppi),
        voci=numerate.voci,
        da_approfondire=approfondire,
    )


def descrivi_beneficiari(riga, beneficiari: list) -> str:
    """I beneficiari di un bando, ciascuno con condizioni e frase del bando."""
    voci = []
    for b in beneficiari:
        voce = NOMI_TIPI[b["tipo"]]
        if b["condizioni"] or come_requisito(b):
            voce += f", {caso_ammissione(b)}"
        # Le righe migrate hanno come frase il testo di beneficiari, che il
        # dettaglio mostra gia'. Quelle del catalogo hanno il valore del
        # file, non una frase del bando.
        if b["origine"] == "catalogo":
            voce += f" (dal catalogo Incentivi Italia: «{b['frase']}»)"
        elif b["origine"] != "ammette_comuni":
            voce += f" (frase del bando: «{b['frase']}»)"
        voci.append(voce)

    if riga["classificato_il"] is None:
        if not voci:
            voci.append("non i Comuni")
        voci.append(NON_CLASSIFICATI)
    elif not voci:
        voci.append(BENEFICIARI_NON_INDICATI)
        if riga["beneficiari_rimando"]:
            voci.append(
                f"la pagina rimanda all'avviso: «{riga['beneficiari_rimando']}»"
            )
    return "; ".join(voci)


def descrivi_scadenze(scadenze: list) -> str:
    """Tutte le date di un bando con piu' date, con la frase del bando."""
    voci = []
    for s in scadenze:
        periodo = (
            f"dal {s['apertura']} al {s['scadenza']}"
            if s["apertura"]
            else f"entro il {s['scadenza']}"
        )
        genere = "domanda" if s["genere"] == "domanda" else "fase successiva"
        voci.append(
            f"{s['descrizione']} ({genere}), {periodo} "
            f"(frase del bando: «{s['frase']}»)"
        )
    return "; ".join(voci)


# Ricerca di un bando per nome (dettaglio_bando). Il router passa una parte
# del titolo, non l'identificativo: piu' bandi possono corrispondere.
# Fino a MAX_DETTAGLI si danno tutti i dettagli; oltre, un elenco breve di
# al piu' MAX_CORRISPONDENZE righe, senza sceglierne uno.
MAX_DETTAGLI = 3
MAX_CORRISPONDENZE = 10
# Nessun bando: al piu' MAX_SIMILI titoli, con almeno SOGLIA_SIMILI delle
# parole cercate presenti nel titolo
MAX_SIMILI = 5
SOGLIA_SIMILI = 0.5
# Parole che non distinguono un bando da un altro
PAROLE_VUOTE = frozenset(
    "bando bandi avviso avvisi contributi contributo per il lo la di dei degli "
    "delle del della e a i gli le nel nella nei al alle ai con su da in un una "
    "che cosa".split()
)
# Due parole lunghe almeno tanto si considerano simili se iniziano con le
# stesse PREFISSO_SIMILE lettere: "parcheggio" e "parcheggi"
PREFISSO_SIMILE = 5
# Corrispondenza parziale: un solo titolo a cui manca una sola parola
# cercata, purche' ne contenga almeno due (con meno parole cercate, una
# mancante e' troppo)
MIN_PAROLE_PARZIALE = 3


def _normale(testo: str) -> str:
    """Minuscolo e senza accenti, per confrontare titoli e testo cercato."""
    scomposto = unicodedata.normalize("NFKD", testo.casefold())
    return scomposto.encode("ascii", "ignore").decode()


def _parole(testo: str) -> list[str]:
    """Le parole che distinguono un titolo: almeno 3 lettere, non vuote."""
    return [
        p
        for p in re.findall(r"[a-z0-9]+", _normale(testo))
        if len(p) >= 3 and p not in PAROLE_VUOTE
    ]


def _simili(a: str, b: str) -> bool:
    if a == b:
        return True
    corta = min(len(a), len(b))
    return corta >= PREFISSO_SIMILE and a[:PREFISSO_SIMILE] == b[:PREFISSO_SIMILE]


def _quota_parole(cercate: list[str], titolo: str) -> float:
    """La quota delle parole cercate che ha una parola simile nel titolo."""
    nel_titolo = _parole(titolo)
    presenti = sum(any(_simili(p, t) for t in nel_titolo) for p in cercate)
    return presenti / len(cercate)


def trova_bandi(conn: sqlite3.Connection, cercato: str) -> list:
    """I bandi che corrispondono al testo cercato, in tre passi.

    1. identificativo esatto: vince sempre;
    2. il testo compare nel titolo (senza maiuscole e accenti);
    3. tutte le parole del testo hanno una parola simile nel titolo, in
       qualunque ordine.
    Ci si ferma al primo passo che trova qualcosa.
    """
    riga = conn.execute("SELECT * FROM bandi WHERE id = ?", (cercato,)).fetchone()
    if riga is not None:
        return [riga]

    tutti = conn.execute("SELECT * FROM bandi ORDER BY titolo, id").fetchall()
    testo = _normale(cercato).strip()
    if testo:
        nel_titolo = [r for r in tutti if testo in _normale(r["titolo"])]
        if nel_titolo:
            return nel_titolo

    parole = _parole(cercato)
    if not parole:
        return []
    return [r for r in tutti if _quota_parole(parole, r["titolo"]) == 1]


def trova_nel_testo(conn: sqlite3.Connection, cercato: str) -> list:
    """I bandi che nominano tutte le parole cercate fuori dal titolo.

    Il testo di un bando e' l'insieme dei suoi beneficiari (soggetto,
    frase, condizioni) e delle descrizioni dei suoi interventi: un bando
    neve nomina gli "impianti di risalita" nelle condizioni, non nel titolo.
    """
    parole = _parole(cercato)
    if not parole:
        return []

    testi: dict[str, list[str]] = {}
    for r in conn.execute(
        "SELECT id_bando, coalesce(soggetto, '') || ' ' || frase || ' ' || "
        "coalesce(condizioni, '') AS testo FROM beneficiari_bando "
        "UNION ALL SELECT id_bando, descrizione FROM interventi_bando"
    ):
        testi.setdefault(r["id_bando"], []).append(r["testo"])

    ids = [i for i, t in testi.items() if _quota_parole(parole, " ".join(t)) == 1]
    if not ids:
        return []
    return conn.execute(
        f"SELECT * FROM bandi WHERE id IN ({', '.join('?' for _ in ids)}) "
        "ORDER BY titolo, id",
        ids,
    ).fetchall()


def corrispondenza_parziale(conn: sqlite3.Connection, cercato: str) -> tuple | None:
    """Il solo titolo a cui manca una sola delle parole cercate, e la parola.

    Si usa quando nessun titolo le contiene tutte: "fondo strade MIT piccoli
    comuni" ritrova il «Fondo investimenti stradali nei piccoli Comuni», che
    non contiene "MIT". Se piu' titoli mancano di una sola parola, a pari
    merito, non se ne sceglie nessuno (None), come se ne mancassero due.
    """
    parole = _parole(cercato)
    if len(parole) < MIN_PAROLE_PARZIALE:
        return None
    candidati = []
    for r in conn.execute("SELECT * FROM bandi ORDER BY titolo, id"):
        nel_titolo = _parole(r["titolo"])
        mancanti = [p for p in parole if not any(_simili(p, t) for t in nel_titolo)]
        if len(mancanti) == 1:
            candidati.append((r, mancanti[0]))
    if len(candidati) != 1:
        return None
    riga, manca = candidati[0]
    return riga, _forma_scritta(cercato, manca)


def _forma_scritta(cercato: str, parola: str) -> str:
    """La parola come e' scritta nel testo cercato ("MIT", non "mit")."""
    for p in re.findall(r"\w+", cercato):
        if _normale(p) == parola:
            return p
    return parola


def titoli_simili(conn: sqlite3.Connection, cercato: str) -> list:
    """I bandi con il titolo piu' vicino al testo cercato, dal piu' vicino."""
    parole = _parole(cercato)
    if not parole:
        return []
    tutti = conn.execute("SELECT id, titolo FROM bandi ORDER BY titolo, id")
    punteggi = [(_quota_parole(parole, r["titolo"]), r) for r in tutti]
    vicini = [(q, r) for q, r in punteggi if q >= SOGLIA_SIMILI]
    vicini.sort(key=lambda coppia: -coppia[0])
    return [r for _, r in vicini[:MAX_SIMILI]]


def _nessun_bando(conn: sqlite3.Connection, cercato: str) -> Risultato:
    simili = titoli_simili(conn, cercato)
    if not simili:
        return Risultato(
            f"Nessun bando corrisponde a '{cercato}', e nessun titolo in "
            "archivio è simile.",
            trovato=False,
        )
    elenco = "; ".join(f"«{r['titolo']}» (id: {r['id']})" for r in simili)
    return Risultato(
        f"Nessun bando corrisponde a '{cercato}'. Titoli più simili in "
        f"archivio, dal più vicino: {elenco}.",
        trovato=False,
    )


def _riga_breve(conn: sqlite3.Connection, riga, oggi: str) -> str:
    """Una riga dell'elenco dei bandi che corrispondono, senza dettaglio."""
    if riga["natura"] == "non_bando":
        return f"«{riga['titolo']}» non e' un bando | url: {riga['url']}"
    scadenze = scadenze_di(conn, riga["id"])
    stato = (
        f"stato: scaduto il {riga['scadenza']}, non più aperto | "
        if scaduto(riga, scadenze, oggi)
        else ""
    )
    return stato + formatta_bando(riga, oggi, scadenze=scadenze)


def dettaglio_bando(conn: sqlite3.Connection, id_bando: str) -> Risultato:
    """Tutti i dati strutturati di un bando, cercato per id o titolo.

    Si cerca prima nei titoli (trova_bandi); se nessun titolo corrisponde,
    nei beneficiari e negli interventi (trova_nel_testo), e lo si dice in
    testa. Poi il solo titolo a cui manca una parola
    (corrispondenza_parziale), con la parola mancante in testa. Un bando: il
    suo dettaglio. Fino a MAX_DETTAGLI: il dettaglio di ciascuno, numerato.
    Oltre: l'elenco breve, senza sceglierne uno (trovato=False). Nessuno: i
    titoli piu' simili, mai l'elenco completo.
    """
    trovati = trova_bandi(conn, id_bando)
    nel_testo = False
    if not trovati:
        trovati = trova_nel_testo(conn, id_bando)
        nel_testo = True
    oggi = data_di_oggi().isoformat()
    numerate = RigheBandi()
    if not trovati:
        parziale = corrispondenza_parziale(conn, id_bando)
        if parziale is None:
            return _nessun_bando(conn, id_bando)
        riga, manca = parziale
        testa = (
            f"Corrispondenza parziale per '{id_bando}': il titolo non contiene "
            f"'{manca}'."
        )
        return Risultato(
            testa + "\n" + numerate.numera(riga, _dettaglio(conn, riga, oggi)),
            fonti=[fonte_bando(riga)],
            voci=numerate.voci,
        )

    quanti = len(trovati)
    if nel_testo:
        testa = (
            f"Nessun titolo corrisponde a '{id_bando}'; questi bandi lo "
            f"nominano nei beneficiari o negli interventi ({quanti})."
        )
        tutti, nessuno = " Ecco il dettaglio di tutti.", " Nessuno è stato scelto."
    else:
        testa = f"Più bandi corrispondono a '{id_bando}' ({quanti}):"
        tutti, nessuno = " ecco il dettaglio di tutti.", " nessuno è stato scelto."

    if quanti <= MAX_DETTAGLI:
        righe = [numerate.numera(r, _dettaglio(conn, r, oggi)) for r in trovati]
        if nel_testo or quanti > 1:
            righe.insert(0, testa + (tutti if quanti > 1 else ""))
        return Risultato(
            "\n".join(righe),
            fonti=list(dict.fromkeys(fonte_bando(r) for r in trovati)),
            voci=numerate.voci,
        )

    mostrati = trovati[:MAX_CORRISPONDENZE]
    intestazione = (
        f"{testa}{nessuno} Per il dettaglio serve il titolo di uno di questi."
    )
    righe = [
        intestazione,
        *("- " + numerate.numera(r, _riga_breve(conn, r, oggi)) for r in mostrati),
    ]
    if quanti > MAX_CORRISPONDENZE:
        righe.append(
            f"E altri {quanti - MAX_CORRISPONDENZE}: il testo cercato è troppo "
            "generico."
        )
    return Risultato(
        "\n".join(righe),
        fonti=list(dict.fromkeys(fonte_bando(r) for r in mostrati)),
        trovato=False,
        voci=numerate.voci,
    )


def _dettaglio(conn: sqlite3.Connection, riga, oggi: str) -> str:
    """Il testo del dettaglio di un bando, senza il segnaposto."""
    if riga["natura"] == "non_bando":
        # La pagina e' in archivio ma non e' un'opportunita': si dice
        # perche', senza i dati del bando
        return (
            f"«{riga['titolo']}» non e' un bando: {riga['natura_motivo']} "
            f"| url: {riga['url']}"
        )

    scadenze = scadenze_di(conn, riga["id"])
    # Lo stato prima di tutto, calcolato ora: un bando dello storico non
    # va presentato come un'opportunita' aperta
    stato = (
        [f"stato: scaduto il {riga['scadenza']}, non più aperto"]
        if scaduto(riga, scadenze, oggi)
        else []
    )
    pezzi = [
        *stato,
        formatta_bando(riga, oggi, scadenze=scadenze),
        "beneficiari ammessi: "
        + descrivi_beneficiari(riga, beneficiari_di(conn, riga["id"])),
    ]
    if scadenze:
        pezzi.append("date del bando: " + descrivi_scadenze(scadenze))

    interventi = conn.execute(
        "SELECT * FROM interventi_bando WHERE id_bando = ? ORDER BY numero",
        (riga["id"],),
    ).fetchall()
    if interventi:
        pezzi.append(
            "interventi e spese ammissibili: "
            + "; ".join(f"{i['genere']}: {i['descrizione']}" for i in interventi)
        )

    if riga["cumulabilita"]:
        pezzi.append(
            f"cumulabilità: {riga['cumulabilita']} "
            f"(frase del bando: «{riga['cumulabilita_frase']}»)"
        )

    dotazione = (
        f"{euro(riga['dotazione'])} euro" if riga["dotazione"] else "non indicata"
    )
    pezzi.append(f"dotazione complessiva: {dotazione}")

    # Solo i contatti d'ufficio letti dal codice; senza, vale l'url del bando
    if riga["contatti"]:
        pezzi.append(f"contatti: {riga['contatti']}")
    if not scaduto(riga, scadenze, oggi):
        da_vedere = problema(conn, riga, oggi)
        if da_vedere:
            pezzi.append(f"da approfondire: {da_vedere}")

    # Un bando, una sola voce: l'atto e' gia' nella riga del bando
    return " | ".join(pezzi)
