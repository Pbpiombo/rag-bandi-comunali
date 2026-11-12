"""Recupero con i documenti nominati nella domanda (proposta P2).

Una domanda come "nell'avviso per i mercati rionali, quanto...?" contiene
parole del titolo che compaiono in quasi tutti i chunk di quel documento:
fanno salire le pagine introduttive a scapito di quella che risponde.

Se la domanda nomina uno o due documenti, alla ricerca generale (la
domanda intera, come prima) si affianca una ricerca ristretta a ciascun
documento, con la domanda ripulita dal tratto che nomina il documento
("l'avviso per i mercati rionali"). I posti si dividono tra le liste a
quote fisse. La ricerca generale non si toglie mai: la risposta può stare
in un documento diverso da quello nominato.

Misure del 12 novembre 2026 (`scripts/diagnostica/prova_recupero.py`):
- togliere tutte le parole del titolo ovunque nella domanda faceva uscire
  dai primi 10 la domanda sul termine di presentazione, e toglieva
  "contributi" da "quali contributi prevede";
- fondere le liste con RRF invece che a quote faceva uscire la domanda che
  nomina un avviso ma ha la risposta in un altro documento.

Collegato alla catena (src/chains/rag.py). Scollegato una volta: con le
domande in quattro forme (apostrofo dritto o tipografico, con o senza
"?") e la domanda normalizzata senza "?" finale, faceva uscire dai primi
10 su Postgres il termine di presentazione. Con la normalizzazione che
chiude la domanda con "?" rispetta la regola: 13 frammenti su 16 tra i
primi 10 invece di 11, e nessuna uscita nemmeno nelle 5 domande di
controllo scritte dopo. Il termine di presentazione resta al limite, 8º
su Postgres e 10º su Chroma.

Le funzioni di scelta e di divisione sono pure e si provano senza database.
"""

import math
import re

from langchain_core.documents import Document

# Parte dei posti che resta alla ricerca generale, secondo quanti documenti
# sono nominati. Il resto si divide in parti uguali tra i documenti.
# Con k=10: 5+5 per un documento, 4+3+3 per due.
QUOTA_GENERALE = {1: 0.5, 2: 0.4}

# Con più documenti nominati la domanda è troppo generica: nessuna
# restrizione.
MASSIMO_DOCUMENTI = max(QUOTA_GENERALE)

# Parole minime del titolo che la domanda deve contenere.
MINIMO_PAROLE_TITOLO = 2

# Parole con cui una domanda nomina un documento. Senza una di queste la
# restrizione non scatta: "aree interne" in una domanda generale non è il
# nome di un avviso.
PAROLE_DOCUMENTO = {
    "avviso",
    "bando",
    "progetto",
    "decreto",
    "delibera",
    "documento",
    "linee",
    "guida",
    "studio",
    "rapporto",
    "scheda",
    "allegato",
}

# Parole del titolo che non lo distinguono.
PAROLE_VUOTE = {
    "il", "lo", "la", "i", "gli", "le", "un", "uno", "una",
    "di", "del", "dello", "della", "dei", "degli", "delle",
    "a", "al", "allo", "alla", "ai", "agli", "alle",
    "da", "dal", "dallo", "dalla", "dai", "dagli", "dalle",
    "in", "nel", "nello", "nella", "nei", "negli", "nelle",
    "su", "sul", "sullo", "sulla", "sui", "sugli", "sulle",
    "con", "per", "tra", "fra", "e", "ed", "o", "che", "cui",
    "pubblico", "pubblica", "progetti", "presente",
}  # fmt: skip

# Parole da cui comincia il tratto della domanda che nomina un documento e
# che si toglie nella ricerca ristretta. "Decreto" e "delibera" restano
# fuori: in "con quale decreto è stato approvato" sono ciò che si chiede.
PAROLE_INTRODUTTIVE = PAROLE_DOCUMENTO - {"decreto", "delibera"}

# Preposizioni con apostrofo, che possono stare dentro il tratto.
ELISIONI = {"l", "nell", "dell", "all", "sull", "dall"}

SCHEMA_PAROLA = r"\w+(?:[./-]\w+)*"


def parole(testo: str) -> list[str]:
    """Parole minuscole; i codici come '2021-2027' o 'c3.1' restano interi."""
    return re.findall(SCHEMA_PAROLA, testo.lower())


def parole_titolo(titolo: str) -> set[str]:
    """Parole del titolo che possono identificarlo."""
    return {
        p
        for p in parole(titolo)
        if p not in PAROLE_VUOTE and p not in PAROLE_DOCUMENTO and len(p) > 1
    }


def documenti_nominati(domanda: str, titoli: dict[str, str]) -> dict[str, set[str]]:
    """Documenti che la domanda nomina, con le parole del titolo trovate.

    `titoli` va dalla fonte (nome del file) al titolo. Un documento è
    candidato se la domanda contiene una parola che introduce un documento
    e almeno MINIMO_PAROLE_TITOLO parole del suo titolo. Tra i candidati si
    tolgono quelli le cui parole trovate sono contenute strettamente in
    quelle di un altro: con "bando sistemi museali 2026" resta il 2026, non
    il 2025. Oltre MASSIMO_DOCUMENTI candidati non si nomina nessuno.
    """
    nella_domanda = set(parole(domanda))
    if not nella_domanda & PAROLE_DOCUMENTO:
        return {}

    candidati = {}
    for fonte, titolo in titoli.items():
        trovate = parole_titolo(titolo) & nella_domanda
        if len(trovate) >= MINIMO_PAROLE_TITOLO:
            candidati[fonte] = trovate

    nominati = {
        fonte: trovate
        for fonte, trovate in candidati.items()
        if not any(
            trovate < altre for altra, altre in candidati.items() if altra != fonte
        )
    }

    if len(nominati) > MASSIMO_DOCUMENTI:
        return {}
    return nominati


def tratti_da_togliere(domanda: str, parole_dei_titoli: set[str]) -> list[tuple]:
    """Tratti della domanda che nominano un documento, come (inizio, fine).

    Un tratto comincia da una parola che introduce un documento e prosegue
    finché le parole seguenti sono del titolo o vuote, separate solo da
    spazi o apostrofi; finisce sull'ultima parola del titolo. La
    punteggiatura lo chiude.
    """
    parole_trovate = list(re.finditer(SCHEMA_PAROLA, domanda))
    tratti = []
    i = 0
    while i < len(parole_trovate):
        if parole_trovate[i].group(0).lower() not in PAROLE_INTRODUTTIVE:
            i += 1
            continue
        j = fine = i
        while j + 1 < len(parole_trovate):
            separatore = domanda[
                parole_trovate[j].end() : parole_trovate[j + 1].start()
            ]
            seguente = parole_trovate[j + 1].group(0).lower()
            if not re.fullmatch(r"[\s']*", separatore):
                break
            if seguente in parole_dei_titoli:
                j = fine = j + 1
            elif seguente in PAROLE_VUOTE or seguente in ELISIONI:
                j += 1
            else:
                break
        if fine > i:
            tratti.append((parole_trovate[i].start(), parole_trovate[fine].end()))
            i = fine + 1
        else:
            i += 1
    return tratti


def ripulisci_domanda(domanda: str, parole_dei_titoli: set[str]) -> str:
    """Toglie i tratti che nominano i documenti, lasciando il resto.

    "Con quale decreto è stato approvato l'avviso per i mercati rionali, e
    quali contributi prevede?" diventa "Con quale decreto è stato approvato
    l', e quali contributi prevede?": "contributi" è anche nel titolo, ma
    fuori dal tratto è il contenuto della domanda e resta.
    """
    for inizio, fine in reversed(tratti_da_togliere(domanda, parole_dei_titoli)):
        domanda = domanda[:inizio] + domanda[fine:]
    return " ".join(domanda.split())


def dividi_posti(k: int, documenti: int) -> list[int]:
    """Posti della ricerca generale e di ciascun documento, in quest'ordine."""
    if documenti == 0:
        return [k]
    per_documento = math.floor(k * (1 - QUOTA_GENERALE[documenti]) / documenti)
    return [k - per_documento * documenti] + [per_documento] * documenti


def chiave_di(documento: Document) -> tuple:
    """Identificatore di un chunk, uguale su Postgres e su Chroma."""
    meta = documento.metadata
    return (meta.get("fonte"), meta.get("chunk_num"))


def unisci(liste: list[list], posti: list[int], k: int) -> list:
    """Prende a turno dalle liste fino ai rispettivi posti, senza doppioni.

    Ogni elemento è una tupla (documento, punteggio, origini). Se una lista
    non riempie i suoi posti, quelli rimasti si riempiono a turno con il
    seguito delle liste, cominciando dalla ricerca generale.
    """
    scelti: list = []
    viste: set = set()
    indici = [0] * len(liste)

    def prossimo(i: int):
        while indici[i] < len(liste[i]):
            elemento = liste[i][indici[i]]
            indici[i] += 1
            if chiave_di(elemento[0]) not in viste:
                return elemento
        return None

    for limiti in (posti, [k] * len(liste)):
        presi = [0] * len(liste)
        attive = True
        while attive and len(scelti) < k:
            attive = False
            for i in range(len(liste)):
                if len(scelti) >= k or presi[i] >= limiti[i]:
                    continue
                elemento = prossimo(i)
                if elemento is None:
                    continue
                scelti.append(elemento)
                viste.add(chiave_di(elemento[0]))
                presi[i] += 1
                attive = True
        if len(scelti) >= k:
            break

    return scelti


class RecuperoPerDocumento:
    """Avvolge un recupero con `cerca(domanda, k, fonte=None)` e `titoli()`."""

    def __init__(self, base) -> None:
        self.base = base
        self.titoli = base.titoli()

    def cerca(
        self, domanda: str, k: int = 8
    ) -> list[tuple[Document, float, list[str]]]:
        nominati = documenti_nominati(domanda, self.titoli)
        if not nominati:
            return self.base.cerca(domanda, k=k)

        da_togliere = set().union(*nominati.values())
        ripulita = ripulisci_domanda(domanda, da_togliere)

        liste = [self.base.cerca(domanda, k=k)]
        for fonte in nominati:
            ristretta = self.base.cerca(ripulita, k=k, fonte=fonte)
            liste.append([_segna(elemento, "documento") for elemento in ristretta])

        return unisci(liste, dividi_posti(k, len(nominati)), k)


def _segna(elemento: tuple, etichetta: str) -> tuple:
    documento, punteggio, origini = elemento
    return documento, punteggio, [f"{etichetta}: {o}" for o in origini]


def avvolgi(recupero) -> "RecuperoPerDocumento":
    """Avvolge un recupero, se non lo è già."""
    if isinstance(recupero, RecuperoPerDocumento):
        return recupero
    return RecuperoPerDocumento(recupero)
