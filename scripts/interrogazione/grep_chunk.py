"""Cerca una stringa letterale dentro i chunk salvati in Chroma."""

import sys

from src.vectorstore import apri_store


def main() -> None:
    if len(sys.argv) < 2:
        print('Uso: python -m scripts.grep_chunk "stringa da cercare"')
        return

    ago = " ".join(sys.argv[1:]).lower()
    dati = apri_store().get()

    trovati = 0
    for testo, meta in zip(dati["documents"], dati["metadatas"], strict=True):
        compatto = " ".join(testo.split())

        if ago in compatto.lower():
            trovati += 1
            posizione = compatto.lower().index(ago)
            inizio = max(0, posizione - 120)
            fine = min(len(compatto), posizione + len(ago) + 120)

            print(
                f"\n--- {meta.get('ente')} | p. {meta.get('page')} "
                f"| chunk {meta.get('chunk_num')} ---"
            )
            print(f"    ...{compatto[inizio:fine]}...")

    print(f"\nTrovato in {trovati} chunk su {len(dati['documents'])}.")


if __name__ == "__main__":
    main()
