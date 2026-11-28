"""File dei contesti per frammento degli avvisi (fermata 1 del 19e, sotto-fermata 1.3).

Uso:
    python -u -m scripts.ingestione.esporta_contesti            # confronta
    python -u -m scripts.ingestione.esporta_contesti --scrivi   # scrive

Scrive data/db/contesti_avvisi.jsonl (src/motore.py, FILE_CONTESTI), che
ArchivioChroma legge in locale (decisione 2 del 28/11/2026: strada 2 di
docs/piano-fermata-1.md, sezione 4). I contesti sono esattamente quelli
della misura del 19d: contesti_della_misura(..., "tutte") di
scripts/diagnostica/misura_recupero_avvisi.py, cioè le righe "tutte"
(testo_di_ricerca) dei contesti generati, senza i contesti scartati dai
controlli (835 contesti e 36 scartati il 28/11/2026). Lo script di misura
non cambia: qui si chiamano le sue funzioni.

Una riga per contesto, in ordine di (fonte, chunk_num):
- fonte, chunk_num: il frammento;
- sha256_testo: l'impronta del testo pulito del frammento, su cui il
  contesto è stato scritto (la stessa di sha256_frammento dei contesti
  generati; si controlla che coincidano);
- contesto: il testo composto, come la misura lo mette davanti al testo;
- origine: "modello" (i contesti sono scritti da un modello: servono solo a
  cercare, non si citano e non si mostrano);
- impronta_istruzioni: l'impronta delle istruzioni con cui il contesto è
  stato generato.

Senza --scrivi confronta con il file esistente e dice cosa scriverebbe; con
--scrivi scrive, ma non sovrascrive un file esistente con un contenuto
diverso (si sposta o si cancella a mano, dopo averlo guardato). Nessuna
chiamata al modello di linguaggio, nessuna rete: legge i contesti salvati,
i vettori di v0 e i PDF degli avvisi in dati-grezzi. Non scrive nel Chroma.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from src.motore import CAMPI_CONTESTO, FILE_CONTESTI, impronta_testo

ORIGINE = "modello"
RIGHE = "tutte"


class ErroreEsportazione(Exception):
    """Un motivo per non scrivere il file."""


def righe_del_file(contesti: dict, documenti, salvati: dict) -> list[dict]:
    """Le righe del file, in ordine di (fonte, chunk_num).

    contesti: per (fonte, chunk_num), come li dà contesti_della_misura.
    documenti: quelli di genera_contesti.leggi_documenti (fonte, frammenti
    con id, chunk_num e testo). salvati: i contesti generati, per id.
    """
    frammenti = {(d.fonte, f.chunk_num): f for d in documenti for f in d.frammenti}
    righe = []
    for chiave in sorted(contesti):
        if chiave not in frammenti:
            raise ErroreEsportazione(f"contesto senza frammento: {chiave}")
        frammento = frammenti[chiave]
        salvato = salvati[frammento.id]
        impronta = impronta_testo(frammento.testo)
        if salvato.get("sha256_frammento") != impronta:
            raise ErroreEsportazione(
                f"{chiave}: l'impronta del testo non è quella su cui il contesto "
                "è stato scritto"
            )
        righe.append(
            {
                "fonte": chiave[0],
                "chunk_num": chiave[1],
                "sha256_testo": impronta,
                "contesto": contesti[chiave],
                "origine": ORIGINE,
                "impronta_istruzioni": salvato["impronta"],
            }
        )
    for riga in righe:
        if tuple(riga) != CAMPI_CONTESTO:
            raise ErroreEsportazione(
                f"campi diversi da quelli del motore: {tuple(riga)}"
            )
    return righe


def testo_del_file(righe: list[dict]) -> str:
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in righe)


def sha(testo: str) -> str:
    return hashlib.sha256(testo.encode("utf-8")).hexdigest()


def confronta(percorso: Path, testo: str) -> tuple[bool, str]:
    """(uguale, descrizione) del file esistente rispetto al testo da scrivere."""
    nuove = testo.splitlines()
    if not percorso.exists():
        return False, f"{percorso.name} non c'è: si scriverebbero {len(nuove)} righe"
    vecchio = percorso.read_text(encoding="utf-8")
    if vecchio == testo:
        return True, f"{percorso.name} è già uguale: {len(nuove)} righe"
    vecchie = vecchio.splitlines()

    def chiave(riga: dict) -> tuple:
        return riga.get("fonte"), riga.get("chunk_num")

    prima = {chiave(json.loads(r)): r for r in vecchie if r.strip()}
    dopo = {chiave(json.loads(r)): r for r in nuove}
    tolte = sorted(set(prima) - set(dopo))
    aggiunte = sorted(set(dopo) - set(prima))
    cambiate = sorted(c for c in set(prima) & set(dopo) if prima[c] != dopo[c])
    return False, (
        f"{percorso.name} è diverso: {len(vecchie)} righe ora, {len(nuove)} da "
        f"scrivere; aggiunte {len(aggiunte)} {aggiunte[:5]}, tolte {len(tolte)} "
        f"{tolte[:5]}, cambiate {len(cambiate)} {cambiate[:5]}"
    )


def scrivi(percorso: Path, testo: str) -> str:
    """Scrive il file; non sovrascrive un file esistente con contenuto diverso."""
    uguale, descrizione = confronta(percorso, testo)
    if uguale:
        return f"niente da scrivere: {descrizione}"
    if percorso.exists():
        raise ErroreEsportazione(
            f"non si sovrascrive: {descrizione}. Si guarda il file, poi si sposta "
            "o si cancella a mano"
        )
    percorso.parent.mkdir(parents=True, exist_ok=True)
    provvisorio = percorso.with_name(percorso.name + ".nuovo")
    with provvisorio.open("w", encoding="utf-8", newline="\n") as f:
        f.write(testo)
    provvisorio.replace(percorso)
    return (
        f"scritto {percorso.name}: {len(testo.splitlines())} righe, sha256 {sha(testo)}"
    )


def contesti_della_misura():
    """(documenti, salvati, contesti, scartati) come la misura del 19d, senza rete."""
    from scripts.diagnostica import misura_recupero_avvisi as mr
    from scripts.ingestione.carica_avvisi import senza_rete

    senza_rete()
    with mr.senza_connessioni():
        documenti, salvati = mr.leggi_contesti_generati()
        contesti, scartati = mr.contesti_della_misura(documenti, salvati, RIGHE)
    return documenti, salvati, contesti, scartati


def principale(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scrivi", action="store_true", help="scrive il file")
    parser.add_argument("--file", type=Path, default=FILE_CONTESTI)
    args = parser.parse_args(argv)

    documenti, salvati, contesti, scartati = contesti_della_misura()
    frammenti = sum(len(d.frammenti) for d in documenti)
    print(
        f"frammenti degli avvisi {frammenti}, con contesto {len(contesti)}, "
        f"scartati dai controlli {len(scartati)}"
    )
    chiavi_scartate = {
        (d.fonte, f.chunk_num)
        for d in documenti
        for f in d.frammenti
        if f.id in scartati
    }
    righe = righe_del_file(contesti, documenti, salvati)
    dentro = chiavi_scartate & {(r["fonte"], r["chunk_num"]) for r in righe}
    if dentro:
        raise ErroreEsportazione(f"contesti scartati nel file: {sorted(dentro)}")
    impronte = sorted({r["impronta_istruzioni"][:12] for r in righe})
    testo = testo_del_file(righe)
    print(
        f"righe {len(righe)}, impronte delle istruzioni {impronte}, sha256 {sha(testo)}"
    )
    if not args.scrivi:
        uguale, descrizione = confronta(args.file, testo)
        print(descrizione + ("" if uguale else " (con --scrivi)"))
        return 0 if uguale else 1
    try:
        print(scrivi(args.file, testo))
    except ErroreEsportazione as errore:
        print(f"FERMO: {errore}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(principale())
