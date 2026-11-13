"""Tipi e funzioni condivisi dalle interrogazioni."""

import re
from dataclasses import dataclass, field

# Il segnaposto locale di una riga di bando nel testo di un risultato:
# [#2] e' la seconda voce. Diventa [D1.2] quando si sa che il risultato e'
# il blocco D1 dei dati dati al modello.
SEGNAPOSTO = re.compile(r"\[#(\d+)\]")


# Un'etichetta di bando nella risposta del modello: [D1.2] e' la seconda
# riga del blocco D1. La stessa forma che riconosce il verificatore.
ETICHETTA_CITATA = re.compile(r"\[D(\d+)\.(\d+)\]", re.IGNORECASE)


@dataclass
class VoceBando:
    """Una riga di bando di un risultato, con la fonte di quel bando.

    titolo e url vengono dal database: li usa l'app per l'elenco dei bandi
    citati, mai il modello.
    """

    testo: str
    fonte: str
    titolo: str = ""
    url: str = ""


@dataclass
class Approfondimento:
    """Un bando pertinente con un dato mancante o incerto.

    Lo mostra l'app sotto la risposta, nella sezione "Da approfondire": il
    modello non lo vede e non lo cita. problema: in poche parole, calcolato
    a ogni domanda; contatti: quelli d'ufficio della pagina, se letti.
    """

    titolo: str
    url: str
    problema: str
    contatti: str | None = None


@dataclass
class Risultato:
    """L'esito di un'interrogazione, pronto per essere dato al modello.

    voci: le righe dei bandi, nell'ordine dei segnaposto [#1], [#2]...
    del testo; vuota per le interrogazioni che non elencano bandi.
    da_approfondire: i bandi pertinenti tenuti fuori dalla lista perche'
    manca o e' incerto un dato essenziale; non fanno parte del testo.
    """

    testo: str
    fonti: list[str] = field(default_factory=list)
    trovato: bool = True
    voci: list[VoceBando] = field(default_factory=list)
    da_approfondire: list[Approfondimento] = field(default_factory=list)


def con_etichette(testo: str, numero: int) -> str:
    """Il testo con i segnaposto [#k] sostituiti dalle etichette [Dn.k]."""
    return SEGNAPOSTO.sub(lambda m: f"[D{numero}.{m.group(1)}]", testo)


def bandi_citati(risposta: str, esiti_dati: list | None) -> list[VoceBando]:
    """I bandi che la risposta cita con un'etichetta [Dn.k], senza doppioni.

    Dn e' il blocco n degli esiti, k la sua riga di bando. Le etichette che
    non corrispondono a una riga si ignorano, come le voci senza url. Un
    bando citato piu' volte, anche da blocchi diversi, compare una volta,
    nell'ordine della prima citazione.
    """
    risultati = [risultato for _, risultato in esiti_dati or []]
    per_url: dict[str, VoceBando] = {}
    for m in ETICHETTA_CITATA.finditer(risposta):
        blocco, riga = int(m.group(1)), int(m.group(2))
        if not (1 <= blocco <= len(risultati)):
            continue
        voci = getattr(risultati[blocco - 1], "voci", None) or []
        if not (1 <= riga <= len(voci)):
            continue
        voce = voci[riga - 1]
        if voce.url:
            per_url.setdefault(voce.url, voce)
    return list(per_url.values())


def senza_segnaposto(testo: str) -> str:
    """Il testo senza i segnaposto, per cercarvi i dati citati."""
    return SEGNAPOSTO.sub("", testo)


def fonti_distinte(righe) -> list[str]:
    """Le fonti citate nelle righe, senza ripetizioni, in ordine."""
    viste = []
    for riga in righe:
        fonte = riga["fonte"]
        if fonte not in viste:
            viste.append(fonte)
    return viste
