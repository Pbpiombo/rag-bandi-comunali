"""Confronta gli elenchi delle fonti con i bandi in archivio.

Uso:
    python -m scripts.ingestione.scopri_bandi                 solo i nuovi
    python -m scripts.ingestione.scopri_bandi --tutti         anche quelli gia' noti
    python -m scripts.ingestione.scopri_bandi --promettenti   solo quelli con indizi
                                                              di pertinenza per un Comune
    python -m scripts.ingestione.scopri_bandi --comandi       stampa i comandi di estrazione
"""

import sys

from src.estrazione.elenco import (
    gia_in_archivio,
    id_da_slug,
    leggi_elenchi,
    scopri,
)


def spariti(letti: list) -> set[str]:
    """I bandi in archivio che nessun elenco della loro fonte riporta piu'.

    Si confronta fonte per fonte: un bando e' sparito solo se manca da
    tutti gli elenchi della sua fonte. Una fonte con un elenco che non si
    e' scaricato non si confronta, per non dare falsi spariti; le fonti
    di tipo 'file' non hanno elenchi e non si confrontano.
    """
    per_fonte: dict[str, set[str]] = {}
    incomplete = set()
    for letto in letti:
        visti = per_fonte.setdefault(letto.fonte.codice, set())
        visti.update(url for _, url in letto.collegamenti)
        if letto.errore:
            incomplete.add(letto.fonte.codice)

    return {
        url
        for codice, visti in per_fonte.items()
        if codice not in incomplete
        for url in gia_in_archivio(codice) - visti
    }


def mostra_spariti(letti: list) -> None:
    """Segnala i bandi in archivio non piu' presenti negli elenchi.

    La sparizione e' un segnale: il bando puo' essere scaduto e archiviato,
    oppure chiuso in anticipo. In entrambi i casi merita un controllo.
    """
    for letto in letti:
        if letto.errore:
            print(f"\nElenco non letto, fonte non confrontata: {letto.elenco.url}")
            print(f"  {letto.errore}")

    spariti_ora = spariti(letti)

    if not spariti_ora:
        return

    print("\n" + "=" * 74)
    print("DA CONTROLLARE: in archivio ma non piu' negli elenchi della fonte")
    print("=" * 74)
    for s in sorted(spariti_ora):
        print(f"  {s}")
    print("\nPossono essere scaduti e archiviati, oppure chiusi in anticipo.")


def main() -> None:
    print("Lettura degli elenchi delle fonti...")
    letti = leggi_elenchi()
    voci = scopri(letti)

    nuove = [v for v in voci if v.nuovo]
    note = [v for v in voci if not v.nuovo]

    print(f"\nBandi nell'elenco: {len(voci)}")
    print(f"  gia' in archivio: {len(note)}")
    print(f"  nuovi:            {len(nuove)}")

    mostrare = voci if "--tutti" in sys.argv else nuove

    if "--promettenti" in sys.argv:
        mostrare = [v for v in mostrare if v.promettente]
        print(f"  con indizi di pertinenza: {len(mostrare)}")

    if "--recenti" in sys.argv:
        mostrare = [v for v in mostrare if v.recente]
        print(f"  senza anni passati nel nome: {len(mostrare)}")

    print()

    if not mostrare:
        print("Nessun bando da mostrare.")
    elif "--comandi" in sys.argv:
        print("=" * 74)
        print("COMANDI DI ESTRAZIONE")
        print("=" * 74)
        for v in mostrare:
            print(f"\n# {v.titolo}")
            print(
                f"python -m scripts.ingestione.estrai_bando {v.url} {id_da_slug(v.slug, v.url)}"
            )
    else:
        print("=" * 74)
        for v in mostrare:
            marca = "NUOVO" if v.nuovo else "     "
            anno = f" [{v.anno}]" if v.anno else ""
            print(f"{marca}  #{v.posizione:<3} {v.titolo}{anno}")
            print(f"       {v.url}")

    mostra_spariti(letti)


if __name__ == "__main__":
    main()
