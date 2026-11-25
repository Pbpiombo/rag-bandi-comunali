"""Citazioni ripetute accorciate nel testo mostrato all'utente.

Il modello cita ogni dato con la forma intera, anche quando ripete la
stessa fonte (ISTRUZIONI, "CITAZIONE OBBLIGATORIA"). Con un atto lungo,
come i sette decreti degli incentivi ai datori di lavoro, la stessa
descrizione compare 4 o 5 volte per risposta. Qui la prima citazione di
ogni etichetta resta intera e le successive con la stessa descrizione
diventano la sola etichetta: "(fonte: [D1.13])".

Agisce solo sul testo mostrato. Il verificatore e i bandi citati ricevono
sempre il testo intero: sul testo accorciato il verificatore perderebbe i
controlli degli atti e delle date scritti nelle citazioni ripetute
(misura del 25/11/2026 su 226 risposte salvate, docs/coda.md, "Citazioni
ripetute (25/11/2026)").

Le citazioni si riconoscono con gli schemi del verificatore
(SCHEMA_CITAZIONE, ETICHETTA, inizio_citazione). Tutto quello che non ha
la forma "fonte: [etichetta], descrizione" con una sola etichetta resta
com'e'.
"""

import re

from src.verification.controllo import ETICHETTA, SCHEMA_CITAZIONE, inizio_citazione

_FLAG = re.DOTALL | re.IGNORECASE

# Una citazione con una sola etichetta in testa e la sua descrizione:
# "fonte: [D1.13], Decreto dirigenziale ...". La descrizione non contiene
# un'altra etichetta: "fonte: [3], ...; fonte: [7], ..." resta com'e'
_FORMA = re.compile(
    rf"(?P<parola>fonte:)\s*\[(?P<etichetta>{ETICHETTA})\]\s*"
    rf"(?:,\s*(?P<descrizione>(?:(?!\[{ETICHETTA}\]).)*\S))?\s*",
    _FLAG,
)

# La pagina in fondo alla descrizione: ", pag. 6", ", pagg. 6-7", ", pp. 3 e 4"
_PAGINA = re.compile(
    r"^(?P<base>.*?)(?:,\s*(?P<pagina>(?:pagg?|pp?)\.\s*[\d\s\-–,e]+))?$", _FLAG
)


def _normale(testo: str) -> str:
    """Il testo per il confronto: spazi uniti, senza maiuscole."""
    return " ".join(testo.split()).casefold()


def accorcia_citazioni(testo: str) -> str:
    """Il testo con le citazioni ripetute ridotte alla sola etichetta.

    - La prima citazione di un'etichetta con la descrizione resta intera.
    - Le successive con la stessa descrizione diventano "(fonte: [L])";
      se cambia solo la pagina, "(fonte: [L], pag. N)".
    - Una descrizione diversa per la stessa etichetta, piu' etichette
      nella stessa parentesi, una citazione senza etichetta ("fonte:
      profilo dell'ente") o senza descrizione restano come sono.
    - Il testo prima di "fonte:" dentro la parentesi resta, e cosi' tutto
      il testo fuori dalle citazioni.

    Funzione pura: lo stesso testo da' sempre lo stesso risultato.
    """
    viste: dict[str, tuple[str, str]] = {}

    def sostituisci(m: re.Match) -> str:
        blocco = m.group(0)
        inizio = inizio_citazione(blocco)
        forma = _FORMA.fullmatch(blocco[inizio:-1])
        if inizio == 0 or forma is None or not forma.group("descrizione"):
            return blocco

        etichetta = forma.group("etichetta").upper()
        parti = _PAGINA.match(forma.group("descrizione"))
        base = _normale(parti.group("base"))
        pagina = _normale(parti.group("pagina") or "")

        if etichetta not in viste:
            viste[etichetta] = (base, pagina)
            return blocco
        base_prima, pagina_prima = viste[etichetta]
        if base != base_prima:
            return blocco

        coda = ""
        if pagina and pagina != pagina_prima:
            coda = f", {parti.group('pagina').strip()}"
        return (
            f"{blocco[:inizio]}{forma.group('parola')} "
            f"[{forma.group('etichetta')}]{coda})"
        )

    return re.sub(SCHEMA_CITAZIONE, sostituisci, testo, flags=_FLAG)
