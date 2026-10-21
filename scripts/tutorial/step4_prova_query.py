"""Collaudo del repertorio, senza chiamare il modello."""

from src.config import ENTE_PREDEFINITO
from src.database.repertorio import descrivi_repertorio, esegui

CASI = [
    ("popolazione_ultima", {}),
    ("popolazione_anno", {"anno": 2022}),
    ("popolazione_anno", {"anno": 1990}),
    ("popolazione_serie", {}),
    ("popolazione_variazione", {}),
    ("popolazione_variazione", {"da": 2019, "a": 2024}),
    ("dato_territoriale", {"chiave": "superficie"}),
    ("dato_territoriale", {"chiave": "altitudine"}),
    ("densita_abitativa", {}),
    ("bandi_aperti_per_comuni", {}),
    ("bandi_in_scadenza", {}),
    ("bandi_in_scadenza", {"giorni": 15}),
    ("bandi_per_tema", {"tema": "commercio"}),
    ("bandi_per_tema", {"tema": "formazione"}),
    ("bandi_per_tema", {"tema": "agricoltura"}),
    ("dettaglio_bando", {"id_bando": "mercati-rionali-2026"}),
    ("dettaglio_bando", {"id_bando": "orientamento"}),
    ("dettaglio_bando", {"id_bando": "inesistente"}),
    ("query_inesistente", {}),
]


def main() -> None:
    print("REPERTORIO DISPONIBILE\n")
    print(descrivi_repertorio())

    print("\n" + "=" * 74)
    print("PROVE")
    print("=" * 74)

    for nome, parametri in CASI:
        esito = esegui(nome, parametri, ENTE_PREDEFINITO)
        segno = "OK " if esito.trovato else "-- "
        print(f"\n{segno}{nome}({parametri})")
        print(f"    {esito.testo}")
        if esito.fonti:
            for f in esito.fonti:
                print(f"    fonte: {f}")


if __name__ == "__main__":
    main()
