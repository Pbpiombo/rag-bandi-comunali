"""Caricamento dei CSV nello schema ed esportazione in ordine stabile."""

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


# --- esportazione: ordine stabile per chiave primaria ---


def test_esporta_in_ordine_di_chiave_primaria(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(schema, "PROCESSED_DIR", tmp_path)
    conn.execute(
        "INSERT INTO fonti VALUES ('f', 'Fonte', 'https://x/e', 'https://x', 'p', "
        "'2026-11-11')"
    )
    for id_bando in ("b", "a"):
        conn.execute(
            "INSERT INTO bandi (id, titolo, ente, beneficiari, url, fonte, "
            "codice_fonte, verificato_il) VALUES (?, 'T', 'E', 'B', ?, 'p', 'f', "
            "'2026-11-11')",
            (id_bando, f"https://x/{id_bando}"),
        )
    # inserite fuori ordine: numero 2 prima di 1, bando b prima di a
    for id_bando, numero in (("b", 2), ("b", 1), ("a", 2), ("a", 1)):
        conn.execute(
            "INSERT INTO interventi_bando VALUES (?, ?, 'spesa', 'd', 'f')",
            (id_bando, numero),
        )

    colonne = schema.TABELLE_DA_CSV["interventi_bando"]
    schema.esporta_csv(conn, "interventi_bando", colonne)

    with (tmp_path / "interventi_bando.csv").open(encoding="utf-8-sig") as f:
        righe = [(r["id_bando"], r["numero"]) for r in csv.DictReader(f)]
    assert righe == [("a", "1"), ("a", "2"), ("b", "1"), ("b", "2")]


def test_chiave_primaria_composta(conn):
    assert schema.chiave_primaria(conn, "beneficiari_bando") == [
        "id_bando",
        "tipo",
        "frase",
    ]
    assert schema.chiave_primaria(conn, "scadenze_bando") == ["id_bando", "numero"]
