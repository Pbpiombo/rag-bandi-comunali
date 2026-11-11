"""Caricamento dei CSV nello schema."""

import csv

from src.database import schema

COLONNE_VECCHIE = [
    c for c in schema.TABELLE_DA_CSV["bandi"] if c not in ("natura", "natura_motivo")
]


def test_un_csv_senza_le_colonne_nuove_prende_i_valori_predefiniti(
    conn, tmp_path, monkeypatch
):
    """Un bandi.csv esportato prima della colonna natura si carica ancora."""
    monkeypatch.setattr(schema, "PROCESSED_DIR", tmp_path)
    conn.execute(
        "INSERT INTO fonti VALUES ('regione-toscana', 'Toscana', 'x', 'y', 'prova', "
        "'2026-11-11')"
    )
    riga = {c: "" for c in COLONNE_VECCHIE}
    riga.update(
        id="vecchio",
        titolo="Bando",
        ente="Regione Toscana",
        beneficiari="Comuni",
        a_sportello="0",
        url="https://www.regione.toscana.it/-/vecchio",
        fonte="prova",
        codice_fonte="regione-toscana",
        verificato_il="2026-11-11",
    )
    with (tmp_path / "bandi.csv").open("w", encoding="utf-8-sig", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=COLONNE_VECCHIE)
        scrittore.writeheader()
        scrittore.writerow(riga)

    assert schema.carica_csv(conn, "bandi", schema.TABELLE_DA_CSV["bandi"]) == 1
    righe = conn.execute("SELECT natura, natura_motivo FROM bandi").fetchall()
    assert [tuple(r) for r in righe] == [("bando", None)]
