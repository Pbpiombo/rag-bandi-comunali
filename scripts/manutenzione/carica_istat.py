"""Popolazione e superficie dei tre comuni, da due tabelle ISTAT.

Uso:
    python -m scripts.manutenzione.carica_istat --scarica
    python -m scripts.manutenzione.carica_istat --prova
    python -m scripts.manutenzione.carica_istat --scrivi

Tabella: bilancio demografico mensile (D7B) di demo.istat.it. La
popolazione al 1 gennaio di un anno e' la "popolazione inizio periodo"
del mese di gennaio, totale dei due sessi. Si usa la stessa tabella per
tutti gli anni e tutti i comuni.

--scarica interroga il modulo di ricerca della pagina pubblica, un anno e
un comune alla volta, e salva ogni risposta in data/raw/istat/ con la
data del giorno nel nome. demo.istat.it non ha robots.txt (risponde 404);
tra due richieste si aspetta ATTESA secondi.

--prova legge le risposte salvate (la piu' recente per anno e comune) e
stampa le righe che scriverebbe, con le differenze rispetto alla tabella
popolazione. Non scrive niente.

--scrivi fa lo stesso e poi sostituisce le righe dei tre comuni ed esporta
popolazione.csv. Si rifiuta se un anno definitivo gia' in archivio cambia
valore: le differenze ammesse sono solo sugli anni provvisori.

Superficie: colonna AREA_KMQ del file "Altimetria Comuni al 31 dicembre
2021" (pagina "Principali statistiche geografiche sui comuni" di
istat.it, robots.txt senza divieti), lo stesso file per i tre comuni.
--scarica lo salva in data/raw/istat/ con la data nel nome; --prova
mostra le differenze con la tabella territorio, --scrivi sostituisce la
chiave superficie dei tre comuni ed esporta territorio.csv.

I comuni sono quelli della tabella enti con il codice ISTAT.
"""

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from src.database.schema import aggiorna_csv, connetti

ANNI = range(2019, 2027)
CARTELLA = Path("data/raw/istat")
URL_RICERCA = "https://demo.istat.it/app/RPCCerca.php"
# La pagina da citare: chi controlla sceglie il comune dal menu
URL_PAGINA = "https://demo.istat.it/app/?i=D7B&a={anno}&l=it"
ATTESA = 3
FONTE = "ISTAT bilancio demografico mensile - popolazione al 1 gennaio"
# Codice del totale dei due sessi nella risposta del modulo
TOTALE = 9
# p = dato provvisorio, v = in corso di validazione (nota della tabella)
FLAG_PROVVISORI = {"p", "v"}
INTESTAZIONI = {"User-Agent": "Mozilla/5.0 (compatible; rag-bandi-comunali)"}
# Il modulo vuole anche ripartizione e regione (Centro, Toscana): senza
# risponde "Errore non specificato". I tre comuni sono in provincia di Pistoia
RIPARTIZIONE = "3"
REGIONE = "09"

URL_ALTIMETRIA = (
    "https://www.istat.it/wp-content/uploads/2026/02/"
    "Altimetria_Comuni-al-31_12_2021.xlsx"
)
NOME_ALTIMETRIA = "Altimetria_Comuni-al-31_12_2021.xlsx"
FONTE_SUPERFICIE = "ISTAT, Altimetria Comuni al 31 dicembre 2021, colonna AREA_KMQ"
XLSX = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


@dataclass
class Dato:
    """La popolazione al 1 gennaio di un comune, letta da una risposta."""

    codice_istat: str
    anno: int
    residenti: int
    provvisorio: bool


def oggi() -> str:
    return datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()


def nome_file(anno: int, codice_istat: str, giorno: str) -> str:
    return f"{giorno}_D7B_{anno}_{codice_istat}.json"


def comuni(conn) -> dict[str, str]:
    """Codice ISTAT -> codice fiscale, per i comuni della tabella enti."""
    righe = conn.execute(
        "SELECT codice_istat, codice_fiscale FROM enti "
        "WHERE tipo = 'comune' AND codice_istat IS NOT NULL ORDER BY codice_istat"
    ).fetchall()
    return {r["codice_istat"]: r["codice_fiscale"] for r in righe}


def leggi_risposta(testo: str, anno: int, codice_istat: str) -> Dato:
    """Il totale di gennaio dalla risposta JSON del modulo di ricerca.

    Si ferma se la risposta non e' del comune o dell'anno chiesti, o se
    manca la riga di gennaio: un dato mancante non si sostituisce.
    """
    risposta = json.loads(testo)
    if not risposta.get("Status"):
        raise ValueError(
            f"{anno} {codice_istat}: risposta senza dati "
            f"({risposta.get('message') or risposta.get('Messaggio')})"
        )

    titolo = risposta.get("caption", "")
    if f"anno {anno}" not in titolo:
        raise ValueError(f"{anno} {codice_istat}: la tabella e' «{titolo}»")

    gennaio = [
        r
        for r in risposta["datatable"]["data"]
        if r["codistat"] == codice_istat and r["mese"] == 1 and r["sesso"] == TOTALE
    ]
    if len(gennaio) != 1:
        raise ValueError(
            f"{anno} {codice_istat}: {len(gennaio)} righe del totale di gennaio"
        )

    riga = gennaio[0]
    return Dato(
        codice_istat=codice_istat,
        anno=anno,
        residenti=int(riga["pop_iniziale"]),
        provvisorio=(riga.get("flag") or "").lower() in FLAG_PROVVISORI,
    )


def riga_popolazione(dato: Dato, codice_ente: str, giorno: str) -> dict:
    """La riga per la tabella popolazione, con indirizzo e data nella fonte."""
    fonte = FONTE + (" (dato provvisorio)" if dato.provvisorio else "")
    fonte += f" | {URL_PAGINA.format(anno=dato.anno)} | scaricato il {giorno}"
    return {
        "codice_ente": codice_ente,
        "anno": dato.anno,
        "residenti": dato.residenti,
        "fonte": fonte,
        "data_rilevazione": f"{dato.anno}-01-01",
    }


def differenze(nuove: list[dict], esistenti: dict) -> tuple[list[str], list[str]]:
    """Confronto con la tabella: (ammesse, bloccanti).

    esistenti: (codice_ente, anno) -> (residenti, fonte). Un anno che
    resta provvisorio, o che era provvisorio e ora e' definitivo, puo'
    cambiare; un anno definitivo no.
    """
    ammesse, bloccanti = [], []
    for riga in nuove:
        chiave = (riga["codice_ente"], riga["anno"])
        if chiave not in esistenti:
            continue
        vecchi, fonte = esistenti[chiave]
        if vecchi == riga["residenti"]:
            continue
        nota = (
            f"{riga['codice_ente']} {riga['anno']}: {vecchi} in archivio, "
            f"{riga['residenti']} nel file nuovo"
        )
        if "provvisorio" in fonte or "provvisorio" in riga["fonte"]:
            ammesse.append(nota)
        else:
            bloccanti.append(nota)
    return ammesse, bloccanti


def scarica(codici_istat: list[str]) -> None:
    CARTELLA.mkdir(parents=True, exist_ok=True)
    giorno = oggi()
    for anno in ANNI:
        for codice in codici_istat:
            corpo = urllib.parse.urlencode(
                {
                    "a": anno,
                    "ripartizione": RIPARTIZIONE,
                    "regione": REGIONE,
                    "comune": codice,
                    "provincia": codice[:3],
                    "hid-i": "D7B",
                    "hid-a": anno,
                    "hid-l": "it",
                    "hid-cat": "D7B",
                    "hid-dati": "dati-form-0",
                    "hid-tavola": "tavola-form-0",
                }
            ).encode()
            richiesta = urllib.request.Request(
                URL_RICERCA, data=corpo, headers=INTESTAZIONI
            )
            with urllib.request.urlopen(richiesta, timeout=60) as risposta:
                testo = risposta.read().decode("utf-8")
            # Si controlla subito: una risposta sbagliata non si salva
            leggi_risposta(testo, anno, codice)
            percorso = CARTELLA / nome_file(anno, codice, giorno)
            percorso.write_text(testo, encoding="utf-8")
            print(f"  {percorso}")
            time.sleep(ATTESA)


def leggi_salvati(codici: dict[str, str]) -> list[dict]:
    """Le righe dalle risposte salvate, la piu' recente per anno e comune."""
    righe = []
    for anno in ANNI:
        for codice_istat, codice_ente in codici.items():
            trovati = sorted(CARTELLA.glob(f"*_D7B_{anno}_{codice_istat}.json"))
            if not trovati:
                raise FileNotFoundError(
                    f"manca la risposta per {anno} {codice_istat}: lanciare --scarica"
                )
            percorso = trovati[-1]
            giorno = percorso.name.split("_", 1)[0]
            dato = leggi_risposta(
                percorso.read_text(encoding="utf-8"), anno, codice_istat
            )
            righe.append(riga_popolazione(dato, codice_ente, giorno))
    return righe


def righe_xlsx(percorso: Path) -> list[list[str]]:
    """Le righe di tutti i fogli di un xlsx, come testo.

    Basta la libreria standard: un xlsx e' uno zip di XML. Le celle vuote
    non scritte nel file non si ricostruiscono: le colonne usate qui sono
    sempre piene.
    """
    righe = []
    with zipfile.ZipFile(percorso) as z:
        condivise = []
        if "xl/sharedStrings.xml" in z.namelist():
            radice = ET.fromstring(z.read("xl/sharedStrings.xml"))
            condivise = [
                "".join(t.text or "" for t in si.iter(f"{XLSX}t"))
                for si in radice.findall(f"{XLSX}si")
            ]
        fogli = sorted(
            n
            for n in z.namelist()
            if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
        )
        for foglio in fogli:
            for riga in ET.fromstring(z.read(foglio)).iter(f"{XLSX}row"):
                valori = []
                for cella in riga.findall(f"{XLSX}c"):
                    v = cella.find(f"{XLSX}v")
                    testo = v.text if v is not None and v.text else ""
                    if cella.get("t") == "s" and testo:
                        testo = condivise[int(testo)]
                    valori.append(testo)
                righe.append(valori)
    return righe


def superfici(righe: list[list[str]], codici_istat: list[str]) -> dict[str, float]:
    """Codice ISTAT -> superficie in kmq, arrotondata a due decimali.

    PRO_COM nel file e' un numero (47023): si completa con gli zeri
    iniziali. Si ferma se manca l'intestazione o un comune.
    """
    for i, riga in enumerate(righe):
        if "PRO_COM" in riga and "AREA_KMQ" in riga:
            col_comune = riga.index("PRO_COM")
            col_area = riga.index("AREA_KMQ")
            dati = righe[i + 1 :]
            break
    else:
        raise ValueError("intestazione con PRO_COM e AREA_KMQ non trovata")

    trovate = {}
    for riga in dati:
        if len(riga) <= max(col_comune, col_area) or not riga[col_comune]:
            continue
        codice = riga[col_comune].zfill(6)
        if codice in codici_istat:
            trovate[codice] = round(float(riga[col_area]), 2)

    mancanti = [c for c in codici_istat if c not in trovate]
    if mancanti:
        raise ValueError(f"comuni senza superficie nel file: {mancanti}")
    return trovate


def riga_superficie(codice_ente: str, valore: float, giorno: str) -> dict:
    """La riga per la tabella territorio, con indirizzo e data nella fonte."""
    return {
        "codice_ente": codice_ente,
        "chiave": "superficie",
        "valore": valore,
        "unita": "kmq",
        "fonte": f"{FONTE_SUPERFICIE} | {URL_ALTIMETRIA} | scaricato il {giorno}",
    }


def scarica_altimetria() -> None:
    richiesta = urllib.request.Request(URL_ALTIMETRIA, headers=INTESTAZIONI)
    with urllib.request.urlopen(richiesta, timeout=120) as risposta:
        contenuto = risposta.read()
    percorso = CARTELLA / f"{oggi()}_{NOME_ALTIMETRIA}"
    percorso.write_bytes(contenuto)
    print(f"  {percorso}")


def leggi_superfici(codici: dict[str, str]) -> list[dict]:
    """Le righe di territorio dal file dell'altimetria piu' recente."""
    trovati = sorted(CARTELLA.glob(f"*_{NOME_ALTIMETRIA}"))
    if not trovati:
        raise FileNotFoundError(f"manca {NOME_ALTIMETRIA}: lanciare --scarica")
    percorso = trovati[-1]
    giorno = percorso.name.split("_", 1)[0]
    valori = superfici(righe_xlsx(percorso), list(codici))
    return [riga_superficie(codici[c], v, giorno) for c, v in valori.items()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    gruppo = parser.add_mutually_exclusive_group(required=True)
    gruppo.add_argument("--scarica", action="store_true")
    gruppo.add_argument("--prova", action="store_true")
    gruppo.add_argument("--scrivi", action="store_true")
    argomenti = parser.parse_args()

    conn = connetti()
    codici = comuni(conn)
    if argomenti.scarica:
        scarica(list(codici))
        scarica_altimetria()
        return 0

    nuove = leggi_salvati(codici)
    esistenti = {
        (r["codice_ente"], r["anno"]): (r["residenti"], r["fonte"])
        for r in conn.execute("SELECT * FROM popolazione")
    }
    for riga in nuove:
        print(f"  {riga['codice_ente']} {riga['anno']} {riga['residenti']:>6}  ")
        print(f"      {riga['fonte']}")
    ammesse, bloccanti = differenze(nuove, esistenti)
    print(f"\nDifferenze sugli anni provvisori: {len(ammesse)}")
    for nota in ammesse:
        print(f"  {nota}")
    print(f"Differenze sugli anni definitivi: {len(bloccanti)}")
    for nota in bloccanti:
        print(f"  {nota}")

    nuove_superfici = leggi_superfici(codici)
    vecchie_superfici = {
        r["codice_ente"]: r["valore"]
        for r in conn.execute(
            "SELECT codice_ente, valore FROM territorio WHERE chiave = 'superficie'"
        )
    }
    print("\nSuperficie:")
    for riga in nuove_superfici:
        vecchia = vecchie_superfici.get(riga["codice_ente"])
        if vecchia is None:
            stato = "nuova"
        elif vecchia == riga["valore"]:
            stato = "uguale"
        else:
            stato = f"CAMBIA da {vecchia}"
        print(f"  {riga['codice_ente']} {riga['valore']} kmq ({stato})")
        print(f"      {riga['fonte']}")

    if argomenti.prova:
        print("\nProva: niente scritto.")
        return 0
    if bloccanti:
        print("\nNon scrivo: un anno definitivo cambierebbe valore.")
        return 1

    with conn:
        conn.executemany(
            "DELETE FROM popolazione WHERE codice_ente = ?",
            [(c,) for c in codici.values()],
        )
        conn.executemany(
            "INSERT INTO popolazione "
            "(codice_ente, anno, residenti, fonte, data_rilevazione) "
            "VALUES (:codice_ente, :anno, :residenti, :fonte, :data_rilevazione)",
            nuove,
        )
        conn.executemany(
            "DELETE FROM territorio WHERE codice_ente = ? AND chiave = 'superficie'",
            [(c,) for c in codici.values()],
        )
        conn.executemany(
            "INSERT INTO territorio (codice_ente, chiave, valore, unita, fonte) "
            "VALUES (:codice_ente, :chiave, :valore, :unita, :fonte)",
            nuove_superfici,
        )
    conn.close()
    aggiorna_csv("popolazione", "territorio")
    print(
        f"\nScritte {len(nuove)} righe di popolazione e "
        f"{len(nuove_superfici)} superfici; CSV esportati."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
