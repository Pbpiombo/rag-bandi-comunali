"""Testo di ricerca per bando (passo 17 della roadmap).

Per ogni bando un testo su cui il passo 4 calcolera' la somiglianza con
la domanda. Si costruisce senza modello da:

- il titolo del bando (bandi.csv);
- gli interventi del bando, descrizione e frase, in ordine di numero
  (interventi_bando.csv); la frase si omette se e' uguale alla
  descrizione;
- per i bandi di Incentivi Italia, dal file del catalogo
  (OpenData_Incentivi.csv, CC BY 4.0): Descrizione, Obiettivo_Finalita e
  Settore_Attivita. Forma_agevolazione non entra: e' un aiuto per
  l'etichettatura a mano del passo 10.

Il testo sta in data/processed/testo_ricerca.csv, mai in bandi.csv (la
regola "Descrizione non si copia" resta valida per bandi.csv), e non si
carica in SQLite (CSV_FUORI_DATABASE in src/database/schema.py): nessuna
interrogazione del repertorio lo legge. Serve solo all'ordinamento: non
va al modello che scrive e non si cita.

La costruzione e' ripetibile: stessi CSV e stesso catalogo danno lo
stesso file, byte per byte (righe in ordine di id_bando, nessuna data di
costruzione). Se il catalogo serve e manca, o ha una data diversa da
quella registrata nei bandi, o non contiene uno dei bandi, si solleva
ErroreTestoRicerca: niente testo parziale.
"""

import csv
import io
import re
from pathlib import Path

from src.estrazione import incentivi as inc

NOME_FILE = "testo_ricerca.csv"

COLONNE = [
    "id_bando",
    "testo",
    "parti",
    "fonte_titolo",
    "fonte_interventi",
    "fonte_catalogo",
    "licenza_catalogo",
    "data_catalogo",
]

# Le colonne del catalogo che entrano nel testo, nell'ordine
COLONNE_TESTO_CATALOGO = ("Descrizione", "Obiettivo_Finalita", "Settore_Attivita")
# Le colonne multivalore, con il separatore \, del catalogo
COLONNE_MULTI = ("Obiettivo_Finalita", "Settore_Attivita")
COLONNE_CATALOGO = ("ID_Incentivo", *COLONNE_TESTO_CATALOGO)

LICENZA_CATALOGO = "CC BY 4.0"
FONTE_CATALOGO = "Incentivi Italia, OpenData_Incentivi.csv del {data}"
# La data del file nella fonte dei bandi di Incentivi Italia: vale per
# NOME_FONTE e per NOME_FONTE_PAGINA di src/estrazione/incentivi.py
DATA_NELLA_FONTE = re.compile(r"OpenData_Incentivi\.csv del (\d{4}-\d{2}-\d{2})")
PREFISSO_ID = "incentivi-"

# Le parti del testo, come si scrivono nella colonna parti
TITOLO = "titolo"
INTERVENTI = "interventi"
CATALOGO = "catalogo"

# Tra una parte e l'altra del testo
SEPARATORE = ". "


class ErroreTestoRicerca(Exception):
    """Il testo di ricerca non si puo' costruire per intero."""


def _pulito(testo: str | None) -> str:
    """Spazi e a-capo compressi in un solo spazio."""
    return " ".join((testo or "").split())


def _leggi_csv(percorso: Path) -> list[dict]:
    if not percorso.is_file():
        raise ErroreTestoRicerca(f"CSV non trovato: {percorso}")
    with percorso.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def del_catalogo(bando: dict) -> bool:
    """Il bando viene da Incentivi Italia."""
    return bando.get("codice_fonte") == inc.CODICE_FONTE


def data_catalogo_registrata(bandi: list[dict]) -> str | None:
    """La data del file del catalogo scritta nella fonte dei bandi.

    None se nessun bando viene da Incentivi Italia. Errore se una fonte
    non ha la data, o se i bandi ne hanno piu' d'una.
    """
    date = set()
    senza = []
    for bando in bandi:
        if not del_catalogo(bando):
            continue
        trovata = DATA_NELLA_FONTE.search(bando.get("fonte") or "")
        if trovata:
            date.add(trovata.group(1))
        else:
            senza.append(bando["id"])
    if senza:
        raise ErroreTestoRicerca(
            "bandi di Incentivi Italia senza la data del file nella fonte: "
            + ", ".join(sorted(senza))
        )
    if len(date) > 1:
        raise ErroreTestoRicerca(
            "i bandi di Incentivi Italia citano file del catalogo di date "
            f"diverse ({', '.join(sorted(date))}): serve un solo file"
        )
    return date.pop() if date else None


def id_incentivo(id_bando: str) -> str:
    """L'ID_Incentivo del catalogo da cui viene un bando."""
    if not id_bando.startswith(PREFISSO_ID):
        raise ErroreTestoRicerca(
            f"il bando {id_bando} viene da Incentivi Italia ma l'id non "
            f"comincia con '{PREFISSO_ID}'"
        )
    return id_bando[len(PREFISSO_ID) :]


def testi_catalogo(
    percorso: str | Path | None,
    data_file: str | None,
    data_registrata: str,
    ids: list[str],
) -> dict[str, dict]:
    """Le righe del catalogo degli ID_Incentivo indicati.

    Errore se il file non c'e', se la sua data non e' quella registrata
    nei bandi, se mancano colonne o se manca uno degli ID.
    """
    if percorso is None or not Path(percorso).is_file():
        raise ErroreTestoRicerca(
            f"file del catalogo non trovato: {percorso}; serve "
            f"OpenData_Incentivi.csv del {data_registrata}, registrato nei bandi"
        )
    if data_file != data_registrata:
        raise ErroreTestoRicerca(
            f"il file del catalogo e' del {data_file}, i bandi citano quello "
            f"del {data_registrata}: serve lo stesso file"
        )
    try:
        righe = inc.leggi_righe(percorso, COLONNE_CATALOGO)
    except inc.FileNonValido as errore:
        raise ErroreTestoRicerca(str(errore)) from errore

    per_id: dict[str, list[dict]] = {}
    for riga in righe:
        per_id.setdefault(riga["ID_Incentivo"].strip(), []).append(riga)
    mancanti = [i for i in ids if i not in per_id]
    if mancanti:
        raise ErroreTestoRicerca(
            "ID_Incentivo assenti dal file del catalogo: " + ", ".join(sorted(mancanti))
        )
    doppi = [i for i in ids if len(per_id[i]) > 1]
    if doppi:
        raise ErroreTestoRicerca(
            "ID_Incentivo ripetuti nel file del catalogo: " + ", ".join(sorted(doppi))
        )
    return {i: per_id[i][0] for i in ids}


def _pezzo_catalogo(riga: dict, colonna: str) -> str:
    valore = riga.get(colonna) or ""
    if colonna in COLONNE_MULTI:
        valore = ", ".join(v.strip() for v in valore.split(inc.SEPARATORE) if v.strip())
    return _pulito(valore)


def testo_bando(
    titolo: str, interventi: list[dict], catalogo: dict | None
) -> tuple[str, list[str]]:
    """Il testo di ricerca di un bando e le parti che lo compongono.

    interventi: le righe di interventi_bando del bando, in qualunque
    ordine; si ordinano per numero.
    """
    pezzi = []
    parti = []

    if _pulito(titolo):
        pezzi.append(_pulito(titolo))
        parti.append(TITOLO)

    pezzi_interventi = []
    for intervento in sorted(interventi, key=lambda r: int(r["numero"])):
        descrizione = _pulito(intervento.get("descrizione"))
        frase = _pulito(intervento.get("frase"))
        if descrizione:
            pezzi_interventi.append(descrizione)
        if frase and frase.casefold() != descrizione.casefold():
            pezzi_interventi.append(frase)
    if pezzi_interventi:
        pezzi.extend(pezzi_interventi)
        parti.append(INTERVENTI)

    if catalogo is not None:
        pezzi_catalogo = [_pezzo_catalogo(catalogo, c) for c in COLONNE_TESTO_CATALOGO]
        pezzi_catalogo = [p for p in pezzi_catalogo if p]
        if pezzi_catalogo:
            pezzi.extend(pezzi_catalogo)
            parti.append(CATALOGO)

    # Un punto finale di un pezzo non si raddoppia con il separatore
    testo = SEPARATORE.join(p.rstrip(" .") for p in pezzi if p.rstrip(" ."))
    return testo, parti


def costruisci(
    cartella: str | Path,
    percorso_catalogo: str | Path | None = None,
    data_file: str | None = None,
) -> list[dict]:
    """Le righe di testo_ricerca.csv, dai CSV di cartella e dal catalogo.

    cartella: data/processed o una copia congelata; si leggono bandi.csv
    e interventi_bando.csv, non SQLite. percorso_catalogo e data_file
    servono solo se ci sono bandi di Incentivi Italia.
    """
    cartella = Path(cartella)
    bandi = _leggi_csv(cartella / "bandi.csv")
    interventi = _leggi_csv(cartella / "interventi_bando.csv")

    ids_bandi = {b["id"] for b in bandi}
    orfani = sorted({r["id_bando"] for r in interventi} - ids_bandi)
    if orfani:
        raise ErroreTestoRicerca(
            "interventi di bandi assenti da bandi.csv: " + ", ".join(orfani)
        )
    per_bando: dict[str, list[dict]] = {}
    for riga in interventi:
        per_bando.setdefault(riga["id_bando"], []).append(riga)

    data_registrata = data_catalogo_registrata(bandi)
    catalogo: dict[str, dict] = {}
    if data_registrata is not None:
        ids = [id_incentivo(b["id"]) for b in bandi if del_catalogo(b)]
        catalogo = testi_catalogo(percorso_catalogo, data_file, data_registrata, ids)

    righe = []
    for bando in sorted(bandi, key=lambda b: b["id"]):
        dal_catalogo = (
            catalogo[id_incentivo(bando["id"])] if del_catalogo(bando) else None
        )
        testo, parti = testo_bando(
            bando["titolo"], per_bando.get(bando["id"], []), dal_catalogo
        )
        if not testo:
            raise ErroreTestoRicerca(f"il bando {bando['id']} non ha nessun testo")
        con_catalogo = CATALOGO in parti
        righe.append(
            {
                "id_bando": bando["id"],
                "testo": testo,
                "parti": ";".join(parti),
                "fonte_titolo": bando["fonte"] if TITOLO in parti else "",
                "fonte_interventi": bando["fonte"] if INTERVENTI in parti else "",
                "fonte_catalogo": (
                    FONTE_CATALOGO.format(data=data_registrata) if con_catalogo else ""
                ),
                "licenza_catalogo": LICENZA_CATALOGO if con_catalogo else "",
                "data_catalogo": data_registrata if con_catalogo else "",
            }
        )
    return righe


def in_byte(righe: list[dict]) -> bytes:
    """Il contenuto del file: UTF-8 con BOM e fine riga \\r\\n, come esporta_csv."""
    buffer = io.StringIO(newline="")
    scrittore = csv.DictWriter(buffer, fieldnames=COLONNE, lineterminator="\r\n")
    scrittore.writeheader()
    for riga in righe:
        scrittore.writerow(riga)
    return buffer.getvalue().encode("utf-8-sig")


def scrivi(righe: list[dict], percorso: str | Path) -> None:
    """Scrive il file, sostituendolo."""
    Path(percorso).write_bytes(in_byte(righe))


def righe_lette(contenuto: bytes) -> list[list[str]]:
    """Le righe del file come le legge csv.reader: fine riga e BOM non contano."""
    return list(csv.reader(io.StringIO(contenuto.decode("utf-8-sig"), newline="")))


def uguale_al_file(righe: list[dict], percorso: str | Path) -> bool:
    """Il file esistente ha le stesse righe di quelle costruite.

    Il confronto e' sulle righe lette, come l'impronta dei CSV: un
    checkout con fine riga diverse non conta come differenza.
    """
    percorso = Path(percorso)
    if not percorso.is_file():
        return False
    return righe_lette(percorso.read_bytes()) == righe_lette(in_byte(righe))
