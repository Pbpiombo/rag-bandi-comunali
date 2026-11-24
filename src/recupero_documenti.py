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

    def frammento(self, fonte: str, chunk_num: int) -> Document | None:
        """Il frammento (fonte, chunk_num) dal recupero avvolto, se lo sa dare.

        Un recupero senza il metodo `frammento` (oggi Postgres) restituisce
        sempre None: i frammenti vicini restano spenti.
        """
        prendi = getattr(self.base, "frammento", None)
        return prendi(fonte, chunk_num) if prendi else None

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


# --- Frammenti vicini (passo 19e, rimedio 1) ---

# Sovrapposizione più corta di così: due frammenti contigui si uniscono con
# un a capo. Il divisore ripete fino a CHUNK_OVERLAP caratteri dentro la
# stessa pagina, ma non sempre (non quando taglia su un titolo di
# paragrafo) e mai tra due pagine.
SOVRAPPOSIZIONE_MINIMA = 30


def unisci_testi(a: str, b: str) -> str:
    """Due frammenti contigui, a prima di b, senza ripetere la sovrapposizione."""
    for n in range(min(len(a), len(b)), SOVRAPPOSIZIONE_MINIMA - 1, -1):
        if a.endswith(b[:n]):
            return a + b[n:]
    return a + "\n" + b


def _blocco(membri: list[Document]) -> Document:
    """Un documento solo per frammenti contigui dello stesso file, in ordine.

    Metadati del primo frammento; la pagina è "n-m" se il blocco passa su più
    pagine; `vicini` elenca i chunk_num del blocco.
    """
    testo = membri[0].page_content
    for documento in membri[1:]:
        testo = unisci_testi(testo, documento.page_content)
    meta = dict(membri[0].metadata)
    pagine = sorted({d.metadata.get("page") for d in membri})
    meta["page"] = pagine[0] if len(pagine) == 1 else f"{pagine[0]}-{pagine[-1]}"
    meta["vicini"] = [d.metadata.get("chunk_num") for d in membri]
    return Document(page_content=testo, metadata=meta)


def con_vicini(risultati: list, prendi, spostamenti: tuple[int, ...]) -> list:
    """I risultati con i frammenti vicini dei frammenti degli avvisi.

    risultati: tuple (documento, punteggio, origini) in ordine di ricerca.
    prendi(fonte, chunk_num): il frammento, o None se non c'è (fuori dal
    file, o recupero che non lo sa dare). spostamenti: per esempio (-1, 1),
    il frammento prima e quello dopo.

    Solo i frammenti con id_bando (gli avvisi) ricevono vicini e si uniscono;
    gli altri restano come sono. Regole, come nella misura del 24/11/2026
    (dati-grezzi/prova/19e/vicini.py): mai vicini di un altro file; un vicino
    già tra i risultati non si ripete; i frammenti contigui dello stesso file
    diventano un blocco solo, in ordine di documento; i blocchi seguono
    l'ordine del loro frammento meglio piazzato. Pura: non tocca i database.
    """
    if not spostamenti or not risultati:
        return risultati
    scelti: dict[tuple, tuple[int, Document]] = {}
    for rango, (documento, _, _) in enumerate(risultati):
        scelti.setdefault(chiave_di(documento), (rango, documento))
    dei_risultati = set(scelti)
    for rango, (documento, _, _) in enumerate(risultati):
        if not documento.metadata.get("id_bando"):
            continue
        fonte, numero = chiave_di(documento)
        for spostamento in spostamenti:
            chiave = (fonte, numero + spostamento)
            if chiave in dei_risultati or chiave in scelti:
                continue
            vicino = prendi(fonte, numero + spostamento)
            if vicino is not None and chiave_di(vicino) == chiave:
                scelti[chiave] = (rango, vicino)

    def avviso(chiave: tuple) -> bool:
        return bool(scelti[chiave][1].metadata.get("id_bando"))

    blocchi: list[list[tuple]] = []
    for chiave in sorted(c for c in scelti if avviso(c)):
        fonte, numero = chiave
        if blocchi and blocchi[-1][-1] == (fonte, numero - 1):
            blocchi[-1].append(chiave)
        else:
            blocchi.append([chiave])
    blocchi += [[c] for c in scelti if not avviso(c)]
    blocchi.sort(key=lambda b: min(scelti[c][0] for c in b))

    originali = {chiave_di(d): (p, o) for d, p, o in risultati}
    uscita = []
    for blocco in blocchi:
        dai_risultati = [c for c in blocco if c in originali]
        punteggio = max(originali[c][0] for c in dai_risultati)
        origini = [o for c in dai_risultati for o in originali[c][1]]
        if len(blocco) > 1:
            origini.append("vicini: " + ", ".join(str(c[1]) for c in blocco))
        membri = [scelti[c][1] for c in blocco]
        documento = _blocco(membri) if avviso(blocco[0]) else membri[0]
        uscita.append((documento, punteggio, origini))
    return uscita


def _segna(elemento: tuple, etichetta: str) -> tuple:
    documento, punteggio, origini = elemento
    return documento, punteggio, [f"{etichetta}: {o}" for o in origini]


def avvolgi(recupero) -> "RecuperoPerDocumento":
    """Avvolge un recupero, se non lo è già."""
    if isinstance(recupero, RecuperoPerDocumento):
        return recupero
    return RecuperoPerDocumento(recupero)
