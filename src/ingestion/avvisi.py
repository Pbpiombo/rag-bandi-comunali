"""Pulizia del testo degli avvisi dei bandi, prima della divisione (19c-1).

Lavora sui testi delle pagine come escono dal lettore (pypdf), un file per
volta. Non legge file e non scrive niente: restituisce i testi puliti e
l'elenco di quello che ha cambiato, perché si possa controllare a mano.

Tre passaggi, in quest'ordine:
1. righe ripetute: intestazioni e piè di pagina presenti in più di metà
   delle pagine, con le soglie di `src/estrazione/pdf_bando.py`, che le
   segnala nell'elenco dei PDF ("righe ripetute, da togliere al
   caricamento");
2. contatti di persone: il repository è pubblico, e i frammenti finiscono
   nelle risposte. Si tolgono le email nominative, i telefoni sulla riga
   di una persona e i nomi dopo le formule del responsabile del
   procedimento. Restano PEC, caselle d'ufficio, numeri verdi, codici
   fiscali e partite IVA degli enti. Le regole sulle email e sulle
   persone vengono da `src/estrazione/contatti.py`;
3. parole spezzate a fine riga: "ri-" a fine riga e "chiedere" all'inizio
   della successiva diventano "richiedere", solo tra lettere minuscole
   (il 25% delle righe nell'avviso del decreto 22706).

La ricucitura dei numeri non sta qui: è l'opzione "prudente" di
`pulisci` in `src/ingestion/testo.py`, applicata alla divisione.
"""

import re
from dataclasses import dataclass

from src.estrazione.contatti import (
    EMAIL,
    NON_TELEFONO,
    NUMERO_VERDE,
    PAROLE_UFFICIO,
    di_persona,
    email_nominativa,
    email_ufficio,
)
from src.estrazione.pdf_bando import PAGINE_PER_RIPETUTE, RIGA_RIPETUTA_MINIMA

EMAIL_OMESSA = "[email omessa]"
TELEFONO_OMESSO = "[telefono omesso]"
NOME_OMESSO = "[nome omesso]"

# Domini di posta certificata: la PEC di un ente si tiene sempre
DOMINIO_PEC = re.compile(r"(?:^|\.)(?:postacert|pec|cert|legalmail)\.", re.IGNORECASE)

# Telefoni fissi e cellulari; i numeri verdi si riconoscono a parte
TELEFONO = re.compile(
    r"(?<![\d/])(?:\+39\s?)?(?:0\d{1,3}|3\d{2})[\s./-]?\d{3,4}[\s./-]?\d{2,4}(?![\d/])"
)

PAROLA_TELEFONO = re.compile(
    r"\b(?:tel|telefon[oi]|cell|cellulare|mobile|recapit[oi])\b", re.IGNORECASE
)

# Righe con codici d'impresa, che non sono telefoni. Oltre a quelle di
# `contatti.NON_TELEFONO`, le forme senza punti dell'avviso del Credito
# Sportivo: "CF 00644160582 - PI 00919631002 - ... REA ... ABI ... CAB"
CODICI_IMPRESA = re.compile(
    r"\b(?:C\.?\s?F|P\.?\s?I(?:VA)?|REA|ABI|CAB)\b\.?\s*:?\s*\d", re.IGNORECASE
)

# Formule dopo cui l'avviso scrive il nome di una persona. Viste il
# 20/11/2026: "RESPONSABILE UNICO DEL PROCEDIMENTO" con il nome sulla
# riga dopo (proroghe del Credito Sportivo), "Responsabile del
# procedimento (RUP) è <nome> in qualità di" (avvisi del Credito
# Sportivo), "Dirigente del Settore <nome>;" (bando parcheggi).
FORMULA_PERSONA = (
    r"(?i:responsabile\s+(?:unico\s+)?del\s+(?:presente\s+)?procedimento"
    r"(?:\s*\(rup\))?|\brup\b\)?|dirigente\s+del\s+settore)"
)
COLLEGAMENTO = (
    r"(?:\s*[:\-–]\s*|\s+(?i:è|e'|é)\s+(?i:il\s+|la\s+)?|\s+)"
    r"(?:(?i:dott|dr|ing|arch|avv|geom|prof)\.?(?i:ssa)?\s+)?"
)
PAROLA_MAIUSCOLA = r"[A-ZÀ-Ý][a-zà-ÿ']+"
NOME_DOPO_FORMULA = re.compile(
    rf"(?P<formula>{FORMULA_PERSONA}{COLLEGAMENTO})"
    rf"(?P<nome>{PAROLA_MAIUSCOLA}(?:[ \t]+{PAROLA_MAIUSCOLA}){{1,2}})"
    r"(?=[ \t]*(?:[;,.(]|in\s+qualit|\n|$))"
)

# Parole che dicono un ufficio, non una persona: "Dirigente del Settore
# Politiche Sociali" non ha un nome da togliere
PAROLE_DI_ENTE = {
    "settore", "servizio", "ufficio", "direzione", "area", "regione",
    "toscana", "giunta", "comune", "provincia", "fondo", "fondi", "sistemi",
    "politiche", "infrastrutture", "mobilità", "programmazione", "attività",
    "istituto", "gestione", "sviluppo", "sostegno", "economia",
}  # fmt: skip


@dataclass(frozen=True)
class Sostituzione:
    """Un contatto tolto: il tipo, il testo originale e quello nuovo."""

    tipo: str  # "email", "telefono", "nome"
    prima: str
    dopo: str


@dataclass(frozen=True)
class RigaTolta:
    """Una riga ripetuta tolta, con le pagine in cui compariva."""

    riga: str
    pagine: int


# --- 1. righe ripetute ---


def righe_ripetute(pagine: list[str]) -> dict[str, int]:
    """Le righe presenti in più di metà delle pagine, con quante pagine.

    Stesse soglie di `pdf_bando.indicatori`: almeno PAGINE_PER_RIPETUTE
    pagine nel file, righe di almeno RIGA_RIPETUTA_MINIMA caratteri (i
    numeri di pagina non contano).
    """
    if len(pagine) < PAGINE_PER_RIPETUTE:
        return {}
    per_riga: dict[str, int] = {}
    for pagina in pagine:
        for riga in {r.strip() for r in pagina.splitlines()}:
            if len(riga) >= RIGA_RIPETUTA_MINIMA:
                per_riga[riga] = per_riga.get(riga, 0) + 1
    return {r: n for r, n in per_riga.items() if n > len(pagine) / 2}


def togli_righe(testo: str, righe: set[str] | dict[str, int]) -> str:
    """Il testo senza le righe indicate (confronto sulla riga ripulita)."""
    return "\n".join(r for r in testo.split("\n") if r.strip() not in righe)


# --- 2. contatti ---


def email_da_tenere(email: str, titolo: str | None = None) -> bool:
    """La PEC e le caselle d'ufficio si tengono; le altre si tolgono.

    A differenza di `contatti.email_ufficio`, una casella con la forma
    nominativa si tiene se una sua parte comincia con una parola d'ufficio
    ("urp_dpo@", "assistenza.fse@"): la parola deve aprire la parte, così
    un nome che la contiene ("valentina.rossi" ha "enti") non passa.
    """
    locale, _, dominio = email.partition("@")
    if DOMINIO_PEC.search(dominio):
        return True
    if email_nominativa(email):
        parti = re.split(r"[._-]", locale.lower())
        return any(p.startswith(u) for p in parti for u in PAROLE_UFFICIO)
    return email_ufficio(email, titolo)


def _togli_email(riga: str, titolo: str | None, fatte: list) -> str:
    def sostituisci(m: re.Match) -> str:
        email = m.group(0).rstrip(".")
        if email_da_tenere(email, titolo):
            return m.group(0)
        fatte.append(Sostituzione("email", email, EMAIL_OMESSA))
        return EMAIL_OMESSA + m.group(0)[len(email) :]

    return EMAIL.sub(sostituisci, riga)


def _togli_telefoni(riga: str, prima: str, fatte: list) -> str:
    """Toglie i telefoni di una riga con una parola da telefono ("tel."...),
    se la riga o quella prima nomina una persona.

    I numeri verdi restano sempre; codice fiscale e partita IVA (riga con
    "C.F.", "P.IVA"...) non sono telefoni e non si toccano.
    """
    if NON_TELEFONO.search(riga) or CODICI_IMPRESA.search(riga):
        return riga
    # Senza una parola da telefono il numero è un altro dato: "Nota Prot.
    # 0230434" accanto a "Toscana Diffusa" (25205, p. 3) non si tocca
    if not PAROLA_TELEFONO.search(riga):
        return riga
    if not (di_persona(riga) or di_persona(prima)):
        return riga

    def sostituisci(m: re.Match) -> str:
        if NUMERO_VERDE.fullmatch(m.group(0).strip()):
            return m.group(0)
        fatte.append(Sostituzione("telefono", m.group(0), TELEFONO_OMESSO))
        return TELEFONO_OMESSO

    return TELEFONO.sub(sostituisci, riga)


def _togli_nomi(testo: str, fatte: list) -> str:
    def sostituisci(m: re.Match) -> str:
        nome = m.group("nome")
        if any(p.lower() in PAROLE_DI_ENTE for p in nome.split()):
            return m.group(0)
        fatte.append(Sostituzione("nome", nome, NOME_OMESSO))
        return m.group("formula") + NOME_OMESSO

    return NOME_DOPO_FORMULA.sub(sostituisci, testo)


def togli_contatti(
    testo: str, titolo: str | None = None
) -> tuple[str, list[Sostituzione]]:
    """Il testo senza i contatti di persone, e le sostituzioni fatte.

    `titolo`: il titolo del bando, per riconoscere le caselle dedicate
    ("puntidigitalefacile@" per "Punti Digitale Facile"), come in
    `contatti.email_ufficio`.

    Un nome sotto un titolo ("dott. Nome Cognome") senza una delle formule
    non si riconosce: il rapporto del caricamento serve a vederli.
    """
    fatte: list[Sostituzione] = []
    testo = _togli_nomi(testo, fatte)
    righe = testo.split("\n")
    nuove = []
    prima = ""
    for riga in righe:
        nuova = _togli_email(riga, titolo, fatte)
        nuova = _togli_telefoni(nuova, prima, fatte)
        nuove.append(nuova)
        prima = riga
    return "\n".join(nuove), fatte


# --- 3. parole spezzate ---

PAROLA_SPEZZATA = re.compile(r"(?<=[a-zà-ÿ])-[ \t]*\n[ \t]*(?=[a-zà-ÿ])")


def _in_un_indirizzo(testo: str, posizione: int) -> bool:
    """Il pezzo che finisce in `posizione` fa parte di un indirizzo web.

    Il pezzo va dall'ultimo spazio o a capo al trattino; un indirizzo
    contiene "://" o comincia con "www.", anche dopo una parentesi o una
    virgoletta aperta.
    """
    inizio = max(testo.rfind(s, 0, posizione) for s in (" ", "\t", "\n")) + 1
    pezzo = testo[inizio:posizione]
    return "://" in pezzo or pezzo.lstrip("(<[«\"'").startswith("www.")


def ricuci_parole(testo: str) -> tuple[str, int]:
    """Unisce le parole spezzate a fine riga, e dice quante.

    Solo tra lettere minuscole: "2021-\\n2027" e "PR-\\nFESR" restano.
    Un trattino vero a fine riga ("socio-\\neconomico") si perde: la
    parola resta comunque leggibile. In un indirizzo web il trattino
    resta ("https://www.regione.toscana.it/agricoltura-e-" e
    "alimentazione/..." sulla riga dopo): lì è quasi sempre vero, e senza
    l'indirizzo non si apre.
    """

    def unisci(m: re.Match) -> str:
        return "-" if _in_un_indirizzo(testo, m.start()) else ""

    return PAROLA_SPEZZATA.subn(unisci, testo)


# --- insieme ---


@dataclass
class EsitoPulizia:
    """I testi puliti di un file e quello che è stato cambiato."""

    pagine: list[str]
    righe_tolte: list[RigaTolta]
    contatti: list[tuple[int, Sostituzione]]  # (pagina, sostituzione)
    parole_ricucite: int


def pulisci_avviso(pagine: list[str], titolo: str | None = None) -> EsitoPulizia:
    """Applica i tre passaggi ai testi delle pagine di un file.

    Le pagine si contano da 1 nell'esito, come nei metadati dei frammenti.
    """
    ripetute = righe_ripetute(pagine)
    pulite: list[str] = []
    contatti: list[tuple[int, Sostituzione]] = []
    ricucite = 0
    for numero, testo in enumerate(pagine, start=1):
        testo = togli_righe(testo, ripetute)
        testo, fatte = togli_contatti(testo, titolo)
        contatti += [(numero, s) for s in fatte]
        testo, n = ricuci_parole(testo)
        ricucite += n
        pulite.append(testo)
    return EsitoPulizia(
        pagine=pulite,
        righe_tolte=[RigaTolta(r, n) for r, n in sorted(ripetute.items())],
        contatti=contatti,
        parole_ricucite=ricucite,
    )


def mascherato(testo: str) -> str:
    """Le prime due lettere e la lunghezza: per i rapporti, mai il dato intero."""
    return f"{testo[:2]}…[{len(testo)}]"
