"""Scadenza letta dalla pagina della fonte, senza modello.

Molte fonti riportano un campo strutturato, con un'etichetta che e' una
regola della fonte (colonna etichetta_scadenza di fonti). Per il portale
della Regione Toscana:

    Data di scadenza presentazione domande
    31.12.2026 12:00

oppure sulla stessa riga, dopo i due punti. Se il campo c'e' e la data e'
passata da piu' di un anno, il bando e' scaduto e non serve chiamare il
modello. Il margine di un anno copre un campo sbagliato o non aggiornato
dopo una proroga.

La lettura e' volutamente rigida: vale solo un valore che e' per intero
una data (con l'ora, eventualmente, prima o dopo: "ore 13.00 del 8 maggio
2026", anche preceduto da "PROROGATO alle"). Qualunque altra cosa ("15
giorni dalla pubblicazione...", un'etichetta, due date diverse)
restituisce None e la pagina va al modello come prima.
"""

import re
from datetime import date

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
# L'ora prima della data, come la scrive il sito del GAL: "ore 13.00 del 8
# maggio 2026", "PROROGATO alle ore 13.00 del 12 ottobre 2026"
ORA_PRIMA = r"(?:prorogat[oa]\s+)?(?:alle\s+)?(?:ore\s+\d{1,2}[:.]\d{2}\s+del\s+)?"
DATA_NUMERICA = re.compile(
    rf"^{ORA_PRIMA}(\d{{1,2}})[./](\d{{1,2}})[./](\d{{4}}){ORA}$", re.IGNORECASE
)
DATA_IN_LETTERE = re.compile(
    rf"^{ORA_PRIMA}(\d{{1,2}})\s+({'|'.join(MESI)})\s+(\d{{4}}){ORA}$",
    re.IGNORECASE,
)

# Giorni oltre la scadenza dopo i quali il bando si registra come scaduto
# senza modello
MARGINE_GIORNI = 365

# Lo storico: un bando scaduto da non piu' di tanti giorni si salva
# (bandi.decidi_automatico) e compare nelle liste per tema, in un blocco a
# parte (interrogazioni_bandi.bandi_per_tema). Piu' vecchio, non si salva
# e non si elenca, ma un bando gia' in archivio si trova ancora per nome.
# Una soglia sola per salvataggio e interrogazioni. MARGINE_GIORNI non
# deve scendere sotto: la preselezione scarterebbe pagine da storico
# prima del modello.
GIORNI_STORICO = 365


def nello_storico(scadenza: str, oggi: date) -> bool:
    """La scadenza (ISO) e' passata da non piu' di GIORNI_STORICO giorni."""
    giorni = (oggi - date.fromisoformat(scadenza)).days
    return 0 < giorni <= GIORNI_STORICO


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


def _etichetta(etichetta: str) -> re.Pattern:
    """La riga che comincia con l'etichetta, con il valore dopo i due punti."""
    return re.compile(rf"^{re.escape(etichetta)}\s*:?\s*(.*)$", re.IGNORECASE)


def scadenza_dichiarata(testo: str, etichetta: str | None) -> date | None:
    """La data del campo con quell'etichetta, se leggibile.

    testo: il testo della pagina, non ritagliato; etichetta: il nome del
    campo, regola della fonte (es. "Data di scadenza presentazione
    domande"). Il valore sta sulla stessa riga o su quella dopo. Se il
    campo compare piu' volte con date diverse, o il valore non e' una
    data, restituisce None. Una fonte senza etichetta non ha il campo:
    None.
    """
    if not etichetta:
        return None
    schema = _etichetta(etichetta)
    righe = [r.strip() for r in testo.splitlines()]
    trovate = set()
    for i, riga in enumerate(righe):
        m = schema.match(riga)
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
SENZA_SCADENZA = "senza scadenza leggibile"
AL_MODELLO = "al modello"


def preselezione(
    testo: str,
    recente: bool,
    oggi: date,
    filtro_anni: bool = True,
    *,
    etichetta: str | None,
    scadenza_obbligatoria: bool = False,
) -> tuple[str, date | None]:
    """Decide, senza modello, se una pagina va mandata al modello.

    testo: il testo completo della pagina; recente: lo slug non ha un
    anno passato (elenco.recente); filtro_anni: la fonte usa il filtro
    sull'anno nello slug; etichetta: il campo della scadenza per la fonte;
    scadenza_obbligatoria: per la fonte ogni bando ha il campo leggibile.
    Restituisce l'esito e la scadenza letta dal campo, se c'e'.

    Una pagina senza scadenza leggibile, in una fonte che la richiede, si
    salta senza modello (SENZA_SCADENZA): sul sito del GAL sono le pagine
    di bando vuote, con le etichette ma senza valori. Non si registra:
    se la pagina si riempie, alla scansione dopo torna candidata.

    Il campo della pagina vale piu' dell'anno nello slug: un bando con
    "2023" nel nome ma il campo che dice 2027 va al modello. L'anno nello
    slug decide solo se il campo manca o non si legge.
    """
    scadenza = scadenza_dichiarata(testo, etichetta)
    if scaduto_da_oltre_il_margine(scadenza, oggi):
        return SCADUTO, scadenza
    if scadenza is None and scadenza_obbligatoria:
        return SENZA_SCADENZA, None
    if scadenza is None and filtro_anni and not recente:
        return ANNO_PASSATO, None
    return AL_MODELLO, scadenza


def motivo_scaduto(scadenza: date) -> str:
    """Il motivo registrato per uno scaduto letto dalla pagina.

    Comincia con "scaduto", come quello del modello: e' uno scarto
    definitivo e la pagina non viene riproposta.
    """
    return f"scaduto il {scadenza.isoformat()} (campo della pagina, senza modello)"
