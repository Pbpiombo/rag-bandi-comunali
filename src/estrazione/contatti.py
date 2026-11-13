"""Contatti d'ufficio di un bando, letti dal testo della pagina senza modello.

Si tengono solo email e telefoni d'ufficio: il repository e' pubblico, e
nei CSV non entrano dati di persone. Nel dubbio un contatto si scarta, e
resta il collegamento alla pagina del bando.

Email: si tiene solo se la parte prima della @
- non e' nominativa: due parti di lettere separate da un punto, un
  trattino basso o un trattino (nome.cognome@, n.cognome@, nome_cognome@);
- e dice di essere un ufficio: contiene una parola d'ufficio (info, bandi,
  sportello, assistenza...), oppure una cifra (avvisosociale2026@),
  oppure una parola di almeno quattro lettere del titolo del bando
  (puntidigitalefacile@ per "Punti Digitale Facile").
Un indirizzo come mrossi@ non e' riconoscibile come nominativo, ma non
passa la seconda condizione: si scarta.

Telefoni: i numeri verdi (800, 803) sempre; gli altri numeri fissi solo
su una riga che nomina un servizio (ufficio, settore, URP, centralino,
assistenza, servizio, help desk, sportello), e mai se sulla riga o su
quella prima c'e' una persona: un nome proprio (due parole maiuscole di
seguito), un titolo (dott., sig. ...) o un'email nominativa, anche
scritta con uno spazio prima della @. Mai partita IVA, codice fiscale,
fax e cellulari. Nella prova del 13/11/2026 le pagine regionali davano
"Nome Cognome - tel. 055/..." e "Telefono: ..." sotto l'email di un
referente: la regola di prima li lasciava passare.

Una riga con un'email nominativa e' la riga di una persona: nessun suo
contatto si tiene.

Le righe del sito (redazione, privacy, problemi di navigazione) non sono
contatti del bando.
"""

import re
import unicodedata

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Anche con gli spazi attorno alla @, come capita nelle pagine: serve solo
# a riconoscere la riga di una persona
EMAIL_SPAZIATA = re.compile(r"[\w.+-]+\s?@\s?[\w-]+(?:\.[\w-]+)+")
NOMINATIVA = re.compile(r"^[a-z]+[._-][a-z]+(?:[._-][a-z]+)*\d*$")

PAROLE_UFFICIO = (
    "info",
    "bandi",
    "bando",
    "avvis",
    "sportell",
    "segreteri",
    "urp",
    "assistenz",
    "support",
    "helpdesk",
    "protocollo",
    "pec",
    "contribut",
    "uffici",
    "settore",
    "serviz",
    "finanziament",
    "agevolazion",
    "incentiv",
    "enti",
    "gal",
    "direzion",
    "contatt",
)

# Numeri verdi, fissi (prefisso 0) e cellulari (prefisso 3, scartati)
NUMERO_VERDE = re.compile(r"(?<!\d)80[03][\s.]?\d{3}[\s.]?\d{3}(?!\d)")
FISSO = re.compile(
    r"(?<![\d/])(?:\+39\s?)?0\d{1,3}[\s./-]?\d{3,4}[\s./-]?\d{2,4}(?![\d/])"
)

RIGA_SERVIZIO = re.compile(
    r"numero verde|centralino|uffici|settore|\burp\b|sportello|assistenza|"
    r"serviz|help ?desk",
    re.IGNORECASE,
)
TITOLI_PERSONA = re.compile(
    r"\b(?:dott|dr|sig|ing|arch|avv|geom|rag|prof)\.?(?:ssa)?\s+[A-Z]",
)
# Un nome proprio: due parole maiuscole di seguito. Prende anche "Regione
# Toscana": un numero si perde, mai una persona si tiene
NOME_PROPRIO = re.compile(r"\b[A-ZÀ-Ý][a-zà-ÿ']+\s+[A-ZÀ-Ý][a-zà-ÿ']+")
NON_TELEFONO = re.compile(
    r"partita iva|p\.\s?iva|c\.\s?f\.|codice fiscale|\bfax\b", re.IGNORECASE
)
RIGA_DEL_SITO = re.compile(
    r"navigazione|redazione|privacy|cookie|accessibilit|note legali|whistleblow",
    re.IGNORECASE,
)


def _senza_accenti(testo: str) -> str:
    forma = unicodedata.normalize("NFKD", testo.lower())
    return "".join(c for c in forma if not unicodedata.combining(c))


def parole_titolo(titolo: str | None) -> set[str]:
    """Le parole di almeno quattro lettere del titolo, senza accenti."""
    return {p for p in re.findall(r"[a-z]{4,}", _senza_accenti(titolo or ""))}


def email_nominativa(email: str) -> bool:
    """La parte prima della @ ha la forma di un nome e un cognome."""
    return bool(NOMINATIVA.match(email.split("@", 1)[0].lower()))


def email_ufficio(email: str, titolo: str | None = None) -> bool:
    """L'email e' d'ufficio, secondo le regole del modulo."""
    if email_nominativa(email):
        return False
    locale = _senza_accenti(email.split("@", 1)[0])
    return (
        any(p in locale for p in PAROLE_UFFICIO)
        or any(c.isdigit() for c in locale)
        or any(p in locale for p in parole_titolo(titolo))
    )


def di_persona(riga: str) -> bool:
    """La riga nomina una persona: nome proprio, titolo o email nominativa."""
    return bool(
        NOME_PROPRIO.search(riga)
        or TITOLI_PERSONA.search(riga)
        or any(
            email_nominativa(e.replace(" ", "")) for e in EMAIL_SPAZIATA.findall(riga)
        )
    )


def _telefoni(riga: str, prima: str) -> list[str]:
    """I numeri d'ufficio della riga; prima: la riga precedente."""
    numeri = [m.group(0) for m in NUMERO_VERDE.finditer(riga)]
    if (
        RIGA_SERVIZIO.search(riga)
        and not NON_TELEFONO.search(riga)
        and not di_persona(riga)
        and not di_persona(prima)
    ):
        numeri += [m.group(0) for m in FISSO.finditer(riga)]
    return [" ".join(n.split()) for n in numeri]


def contatti_da_testo(testo: str, titolo: str | None = None) -> str | None:
    """I contatti d'ufficio della pagina in una riga, oppure None.

    testo: il testo della pagina (quello mandato al modello); titolo: il
    titolo del bando, per riconoscere le email dedicate al bando.
    """
    email, telefoni = [], []
    prima = ""
    for riga in testo.splitlines():
        spaziate = [e.replace(" ", "") for e in EMAIL_SPAZIATA.findall(riga)]
        if not RIGA_DEL_SITO.search(riga) and not any(
            email_nominativa(e) for e in spaziate
        ):
            trovate = [e.rstrip(".") for e in EMAIL.findall(riga)]
            email += [e.lower() for e in trovate if email_ufficio(e, titolo)]
            telefoni += _telefoni(riga, prima)
        prima = riga

    # Lo stesso numero scritto in forme diverse (800327723 e 800 327 723)
    # compare una volta, nella prima forma trovata
    unici: dict[str, str] = {}
    for numero in telefoni:
        unici.setdefault(re.sub(r"\D", "", numero.removeprefix("+39")), numero)

    pezzi = []
    if email:
        pezzi.append("email: " + ", ".join(dict.fromkeys(email)))
    if unici:
        pezzi.append("telefono: " + ", ".join(unici.values()))
    return "; ".join(pezzi) or None
