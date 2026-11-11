"""Confronta l'elenco dei bandi del portale con quelli in archivio.

Uso:
    python -m scripts.ingestione.scopri_bandi                 solo i nuovi
    python -m scripts.ingestione.scopri_bandi --tutti         anche quelli gia' noti
    python -m scripts.ingestione.scopri_bandi --promettenti   solo quelli con indizi
                                                              di pertinenza per un Comune
    python -m scripts.ingestione.scopri_bandi --comandi       stampa i comandi di estrazione
"""

import sys

from src.estrazione.elenco import gia_in_archivio, id_da_slug, scopri


def mostra_spariti(voci: list) -> None:
    """Segnala i bandi in archivio non piu' presenti nell'elenco.

    La sparizione e' un segnale: il bando puo' essere scaduto e archiviato,
    oppure chiuso in anticipo. In entrambi i casi merita un controllo.
    """
    spariti = gia_in_archivio() - {v.url for v in voci}

    if not spariti:
        return

    print("\n" + "=" * 74)
    print("DA CONTROLLARE: in archivio ma non piu' nell'elenco del portale")
    print("=" * 74)
    for s in sorted(spariti):
        print(f"  {s}")
    print("\nPossono essere scaduti e archiviati, oppure chiusi in anticipo.")


def main() -> None:
    print("Lettura dell'elenco dal portale...")
    voci = scopri()

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

    mostra_spariti(voci)


if __name__ == "__main__":
    main()
