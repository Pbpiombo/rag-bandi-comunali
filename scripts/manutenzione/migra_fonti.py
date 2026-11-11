"""Migrazione una tantum di bandi.csv e scansioni.csv alla tabella fonti.

Uso:
    python -m scripts.manutenzione.migra_fonti

Aggiunge a ogni bando il codice della fonte e porta scansioni dalla
chiave slug alla chiave url (in forma canonica). Tutte le righe esistenti
vengono dal portale della Regione Toscana.

Lo script non scrive nulla se trova un problema: URL di bandi non in
forma canonica, chiavi duplicate, o scansioni con esito "salvato" il cui
URL ricostruito non corrisponde a nessun bando. In quei casi elenca le
righe e si ferma, perche' la decisione spetta a una persona.

Prima di scrivere salva una copia .bak dei due CSV. Rilanciato sui CSV
gia' migrati non cambia nulla.

Dopo la migrazione il database va ricreato:
    Remove-Item data\\db\\comune.sqlite
    python -m scripts.tutorial.step4_crea_db
"""

import csv
import shutil
import sqlite3

from src.config import PROCESSED_DIR, SQLITE_PATH
from src.database.schema import TABELLE_DA_CSV
from src.estrazione.indirizzi import url_canonico

CODICE_FONTE = "regione-toscana"


class MigrazioneFermata(Exception):
    """La migrazione ha trovato righe su cui deve decidere una persona."""

    def __init__(self, messaggio: str, righe: list[str]):
        super().__init__(messaggio)
        self.righe = righe

    def __str__(self) -> str:
        elenco = "\n".join(f"  {r}" for r in self.righe)
        return f"{self.args[0]}\n{elenco}"


def _controlla_unici(righe: list[dict], colonna: str, tabella: str) -> None:
    """Si ferma se due righe hanno lo stesso valore nella colonna."""
    visti = set()
    doppi = []
    for r in righe:
        if r[colonna] in visti:
            doppi.append(r[colonna])
        visti.add(r[colonna])

    if doppi:
        raise MigrazioneFermata(f"{tabella}: valori duplicati in '{colonna}'", doppi)


def migra_bandi(righe: list[dict], codice_fonte: str) -> list[dict]:
    """Aggiunge il codice della fonte ai bandi che non lo hanno."""
    non_canonici = [r["url"] for r in righe if url_canonico(r["url"]) != r["url"]]
    if non_canonici:
        raise MigrazioneFermata("bandi: URL non in forma canonica", non_canonici)

    migrate = []
    for r in righe:
        nuova = dict(r)
        if not nuova.get("codice_fonte"):
            nuova["codice_fonte"] = codice_fonte
        migrate.append(nuova)

    _controlla_unici(migrate, "id", "bandi")
    _controlla_unici(migrate, "url", "bandi")
    return migrate


def migra_scansioni(
    righe: list[dict],
    url_base: str,
    codice_fonte: str,
    url_bandi: set[str],
) -> list[dict]:
    """Ricostruisce l'URL di ogni scansione dallo slug, come fa scopri().

    Le scansioni gia' migrate, che hanno l'URL, restano come sono.
    """
    migrate = []
    for r in righe:
        nuova = dict(r)
        if not nuova.get("url"):
            nuova["url"] = url_canonico(f"{url_base}/-/{r['slug']}")
        if not nuova.get("codice_fonte"):
            nuova["codice_fonte"] = codice_fonte
        migrate.append(nuova)

    senza_bando = [
        f"{r['slug']}  ->  {r['url']}"
        for r in migrate
        if r["esito"] == "salvato" and r["url"] not in url_bandi
    ]
    if senza_bando:
        raise MigrazioneFermata(
            "scansioni: esito 'salvato' senza un bando con lo stesso URL",
            senza_bando,
        )

    _controlla_unici(migrate, "url", "scansioni")
    return migrate


def _leggi(tabella: str) -> list[dict]:
    percorso = PROCESSED_DIR / f"{tabella}.csv"
    with percorso.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _scrivi(tabella: str, righe: list[dict]) -> None:
    """Scrive il CSV con le colonne dello schema, salvando prima una copia."""
    percorso = PROCESSED_DIR / f"{tabella}.csv"
    copia = percorso.with_suffix(".csv.bak")

    if copia.exists():
        print(f"  copia {copia.name} gia' presente: la conservo")
    else:
        shutil.copy2(percorso, copia)
        print(f"  copia salvata in {copia.name}")

    colonne = TABELLE_DA_CSV[tabella]
    with percorso.open("w", encoding="utf-8-sig", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=colonne)
        scrittore.writeheader()
        for r in righe:
            scrittore.writerow({c: r.get(c, "") for c in colonne})


def _conteggi_database() -> dict[str, int] | None:
    """Righe di bandi e scansioni nel database, se esiste."""
    if not SQLITE_PATH.exists():
        return None
    conn = sqlite3.connect(SQLITE_PATH)
    try:
        return {
            t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            for t in ("bandi", "scansioni")
        }
    finally:
        conn.close()


def main() -> None:
    fonti = {r["codice"]: r for r in _leggi("fonti")}
    if CODICE_FONTE not in fonti:
        print(f"Fonte '{CODICE_FONTE}' assente da fonti.csv. Non migro.")
        return
    url_base = fonti[CODICE_FONTE]["url_base"]

    bandi = _leggi("bandi")
    scansioni = _leggi("scansioni")
    prima = {"bandi": len(bandi), "scansioni": len(scansioni)}
    print(f"CSV prima:      {prima}")

    nel_database = _conteggi_database()
    print(f"Database prima: {nel_database}")
    if nel_database is not None and nel_database != prima:
        print(
            "Database e CSV non coincidono: esporta prima con aggiorna_csv. Non migro."
        )
        return

    try:
        bandi = migra_bandi(bandi, CODICE_FONTE)
        scansioni = migra_scansioni(
            scansioni, url_base, CODICE_FONTE, {r["url"] for r in bandi}
        )
    except MigrazioneFermata as errore:
        print(f"\nMIGRAZIONE FERMATA, nessun file scritto.\n{errore}")
        return

    _scrivi("bandi", bandi)
    _scrivi("scansioni", scansioni)

    dopo = {"bandi": len(_leggi("bandi")), "scansioni": len(_leggi("scansioni"))}
    print(f"CSV dopo:       {dopo}")

    if dopo != prima:
        print("ATTENZIONE: il numero di righe e' cambiato. Ripristina dai .bak.")


if __name__ == "__main__":
    main()
