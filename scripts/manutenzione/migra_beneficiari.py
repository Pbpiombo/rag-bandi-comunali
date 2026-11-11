"""Migrazione una tantum da ammette_comuni alla tabella beneficiari_bando.

Uso:
    python -m scripts.manutenzione.migra_beneficiari

La colonna ammette_comuni (si'/no) esce da bandi.csv. Per ogni bando che
ammetteva i Comuni si crea una riga di beneficiari_bando di tipo 'comune',
con origine 'ammette_comuni' e come frase il testo gia' verificato della
colonna beneficiari. Nessuna condizione: il vecchio campo non le conosceva.
I bandi che non ammettevano i Comuni non hanno righe: i loro beneficiari
restano da classificare (classificato_il vuoto).

Si aggiungono a bandi.csv le colonne vuote cumulabilita,
cumulabilita_frase e classificato_il, e si crea interventi_bando.csv con
la sola intestazione.

Lo script si ferma senza scrivere se trova un valore di ammette_comuni
diverso da 0 e 1, o un bando che lo ammette senza il testo dei
beneficiari. Prima di scrivere salva una copia di bandi.csv con suffisso
.pre-beneficiari.bak. Rilanciato sui CSV gia' migrati non cambia nulla.

Dopo la migrazione il database va ricreato:
    Remove-Item data\\db\\comune.sqlite
    python -m scripts.tutorial.step4_crea_db
"""

import csv
import shutil
import sqlite3

from src.config import PROCESSED_DIR, SQLITE_PATH
from src.database.schema import TABELLE_DA_CSV

SUFFISSO_COPIA = ".pre-beneficiari.bak"


class MigrazioneFermata(Exception):
    """La migrazione ha trovato righe su cui deve decidere una persona."""

    def __init__(self, messaggio: str, righe: list[str]):
        super().__init__(messaggio)
        self.righe = righe

    def __str__(self) -> str:
        elenco = "\n".join(f"  {r}" for r in self.righe)
        return f"{self.args[0]}\n{elenco}"


def migra(bandi: list[dict]) -> tuple[list[dict], list[dict]]:
    """Toglie ammette_comuni dai bandi e ne ricava le righe di beneficiari.

    Restituisce (bandi migrati, righe di beneficiari_bando). Se i bandi
    sono gia' migrati (non hanno ammette_comuni) li restituisce invariati,
    senza righe nuove.
    """
    valori_strani = [
        f"{b['id']}: ammette_comuni = {b['ammette_comuni']!r}"
        for b in bandi
        if "ammette_comuni" in b and b["ammette_comuni"] not in ("0", "1")
    ]
    if valori_strani:
        raise MigrazioneFermata("ammette_comuni diverso da 0 e 1", valori_strani)

    senza_testo = [
        b["id"]
        for b in bandi
        if b.get("ammette_comuni") == "1" and not (b.get("beneficiari") or "").strip()
    ]
    if senza_testo:
        raise MigrazioneFermata(
            "bandi che ammettono i Comuni senza beneficiari", senza_testo
        )

    migrati = []
    beneficiari = []
    for b in bandi:
        nuovo = {c: v for c, v in b.items() if c != "ammette_comuni"}
        for colonna in ("cumulabilita", "cumulabilita_frase", "classificato_il"):
            nuovo.setdefault(colonna, "")
        migrati.append(nuovo)

        if b.get("ammette_comuni") == "1":
            beneficiari.append(
                {
                    "id_bando": b["id"],
                    "tipo": "comune",
                    "soggetto": "",
                    "condizioni": "",
                    "frase": b["beneficiari"],
                    "confidenza": "",
                    "origine": "ammette_comuni",
                }
            )

    return migrati, beneficiari


def _leggi(tabella: str) -> list[dict] | None:
    percorso = PROCESSED_DIR / f"{tabella}.csv"
    if not percorso.exists():
        return None
    with percorso.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _scrivi(tabella: str, righe: list[dict]) -> None:
    colonne = TABELLE_DA_CSV[tabella]
    percorso = PROCESSED_DIR / f"{tabella}.csv"
    with percorso.open("w", encoding="utf-8-sig", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=colonne)
        scrittore.writeheader()
        for r in righe:
            scrittore.writerow({c: r.get(c, "") for c in colonne})


def _bandi_nel_database() -> int | None:
    if not SQLITE_PATH.exists():
        return None
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        return conn.execute("SELECT COUNT(*) FROM bandi").fetchone()[0]
    finally:
        conn.close()


def main() -> None:
    bandi = _leggi("bandi")
    if bandi is None:
        print("bandi.csv assente. Non migro.")
        return

    if "ammette_comuni" not in bandi[0]:
        print("bandi.csv non ha la colonna ammette_comuni: gia' migrato.")
        return

    nel_database = _bandi_nel_database()
    print(f"bandi nel CSV: {len(bandi)} | nel database: {nel_database}")
    if nel_database is not None and nel_database != len(bandi):
        print("Database e CSV non coincidono: esporta prima con aggiorna_csv.")
        return

    try:
        migrati, beneficiari = migra(bandi)
    except MigrazioneFermata as errore:
        print(f"\nMIGRAZIONE FERMATA, nessun file scritto.\n{errore}")
        return

    copia = PROCESSED_DIR / f"bandi.csv{SUFFISSO_COPIA}"
    if not copia.exists():
        shutil.copy2(PROCESSED_DIR / "bandi.csv", copia)
        print(f"  copia salvata in {copia.name}")

    _scrivi("bandi", migrati)
    _scrivi("beneficiari_bando", beneficiari)
    if _leggi("interventi_bando") is None:
        _scrivi("interventi_bando", [])

    ammessi = sum(b["ammette_comuni"] == "1" for b in bandi)
    print(f"bandi prima: {len(bandi)}, di cui {ammessi} ammettevano i Comuni")
    print(
        f"bandi dopo:  {len(_leggi('bandi'))} | "
        f"beneficiari_bando: {len(_leggi('beneficiari_bando'))} | "
        f"interventi_bando: {len(_leggi('interventi_bando'))}"
    )


if __name__ == "__main__":
    main()
