"""Scadenza letta dalla pagina del portale, senza modello.

Il portale della Regione Toscana riporta spesso un campo strutturato:

    Data di scadenza presentazione domande
    31.12.2026 12:00

oppure sulla stessa riga, dopo i due punti. Se il campo c'e' e la data e'
passata da piu' di un anno, il bando e' scaduto e non serve chiamare il
modello. Il margine di un anno copre un campo sbagliato o non aggiornato
dopo una proroga.

La lettura e' volutamente rigida: vale solo un valore che e' per intero
una data (con l'ora, eventualmente). Qualunque altra cosa ("15 giorni
dalla pubblicazione...", un'etichetta, due date diverse) restituisce None
e la pagina va al modello come prima.
"""

import re
from datetime import date

ETICHETTA = re.compile(
    r"^data di scadenza presentazione domande\s*:?\s*(.*)$", re.IGNORECASE
)

MESI = {
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}

ORA = r"(?:\s+(?:ore\s+)?\d{1,2}[:.]\d{2})?"
DATA_NUMERICA = re.compile(rf"^(\d{{1,2}})[./](\d{{1,2}})[./](\d{{4}}){ORA}$")
DATA_IN_LETTERE = re.compile(
    rf"^(\d{{1,2}})\s+({'|'.join(MESI)})\s+(\d{{4}}){ORA}$", re.IGNORECASE
)

# Giorni oltre la scadenza dopo i quali il bando si registra come scaduto
# senza modello
MARGINE_GIORNI = 365


def _data(valore: str) -> date | None:
    """Il valore come data, solo se e' per intero una data."""
    valore = valore.strip().rstrip(".").strip()
    if m := DATA_NUMERICA.match(valore):
        giorno, mese, anno = int(m[1]), int(m[2]), int(m[3])
    elif m := DATA_IN_LETTERE.match(valore):
        giorno, mese, anno = int(m[1]), MESI[m[2].lower()], int(m[3])
    else:
        return None
    try:
        return date(anno, mese, giorno)
    except ValueError:
        return None


def scadenza_dichiarata(testo: str) -> date | None:
    """La data del campo "Data di scadenza presentazione domande", se leggibile.

    testo: il testo della pagina, non ritagliato. Se il campo compare piu'
    volte con date diverse, o il valore non e' una data, restituisce None.
    """
    righe = [r.strip() for r in testo.splitlines()]
    trovate = set()
    for i, riga in enumerate(righe):
        m = ETICHETTA.match(riga)
        if not m:
            continue
        valore = m[1] or (righe[i + 1] if i + 1 < len(righe) else "")
        data = _data(valore)
        if data is None:
            return None
        trovate.add(data)

    return trovate.pop() if len(trovate) == 1 else None


def scaduto_da_oltre_il_margine(scadenza: date | None, oggi: date) -> bool:
    """La scadenza e' passata da piu' di MARGINE_GIORNI giorni."""
    return scadenza is not None and (oggi - scadenza).days > MARGINE_GIORNI


# Esiti della preselezione
SCADUTO = "scaduto"
ANNO_PASSATO = "anno passato nello slug"
AL_MODELLO = "al modello"


def preselezione(
    testo: str, recente: bool, oggi: date, filtro_anni: bool = True
) -> tuple[str, date | None]:
    """Decide, senza modello, se una pagina va mandata al modello.

    testo: il testo completo della pagina; recente: lo slug non ha un
    anno passato (elenco.recente). Restituisce l'esito e la scadenza
    letta dal campo, se c'e'.

    Il campo della pagina vale piu' dell'anno nello slug: un bando con
    "2023" nel nome ma il campo che dice 2027 va al modello. L'anno nello
    slug decide solo se il campo manca o non si legge.
    """
    scadenza = scadenza_dichiarata(testo)
    if scaduto_da_oltre_il_margine(scadenza, oggi):
        return SCADUTO, scadenza
    if scadenza is None and filtro_anni and not recente:
        return ANNO_PASSATO, None
    return AL_MODELLO, scadenza


def motivo_scaduto(scadenza: date) -> str:
    """Il motivo registrato per uno scaduto letto dalla pagina.

    Comincia con "scaduto", come quello del modello: e' uno scarto
    definitivo e la pagina non viene riproposta.
    """
    return f"scaduto il {scadenza.isoformat()} (campo della pagina, senza modello)"
