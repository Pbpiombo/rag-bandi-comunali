"""Per i comuni, le interrogazioni sui bandi danno il testo atteso.

Il primo riferimento era stato catturato con il codice e lo schema
precedenti alla tabella beneficiari_bando, quando i bandi avevano la
colonna ammette_comuni, sui 21 bandi di allora (dati/bandi_prima.csv) e
con la data fissata al 2026-11-11. Nella tappa a il testo per i comuni era
identico a quello.

Il riferimento attuale (dati/interrogazioni_comuni_dopo.json) e' quello
della tappa c delle interrogazioni (piano-estrattore.md), sugli stessi
bandi e con la stessa data. Rispetto al primo cambia solo dove il testo
cambia di proposito, differenze approvate una per una:
- bandi_aperti_per_comuni diventa bandi_aperti_per_ente, con l'ente;
- i bandi a sportello sono in un gruppo separato, con l'invito a
  verificare le risorse ("a sportello fino al None" non c'e' piu');
- bandi_per_tema: [COMUNI AMMESSI] e [NON per i Comuni] diventano
  l'elenco dei tipi, con "altri beneficiari non ancora classificati";
- dettaglio_bando: "Comuni ammessi: SI'/NO" diventa "beneficiari
  ammessi: ...";
- stato_archivio conta i bandi aperti per l'ente, non tutti.

Aggiornato l'11 novembre 2026 (punto 3 di piano-post-scansione.md), con
tre differenze approvate una per una:
- ogni riga di bando comincia con il segnaposto [#k], che diventa [Dn.k]
  nel blocco dei dati dato al modello;
- ogni riga di bando contiene "atto: <riferimento_atto>" prima dell'url;
- nel dettaglio l'atto passa dalla fine del testo alla riga del bando.

Il test migra quei bandi con lo script di migrazione, li carica nello
schema attuale ed esegue le stesse interrogazioni: il testo, le fonti e
l'esito devono coincidere con il riferimento.
"""

import csv
import json
import sqlite3
from datetime import date
from pathlib import Path

import pytest

from scripts.manutenzione.migra_beneficiari import migra
from src.database import interrogazioni_bandi, repertorio, schema
from src.database.interrogazioni_bandi import (
    bandi_aperti_per_ente,
    bandi_in_scadenza,
    bandi_per_tema,
    dettaglio_bando,
)

DATI = Path(__file__).parent / "dati"
BANDI_PRIMA = DATI / "bandi_prima.csv"
RIFERIMENTO = DATI / "interrogazioni_comuni_dopo.json"

OGGI = date(2026, 11, 11)
COMUNE = "90060100477"


class DataFissa(date):
    """Una data il cui oggi e' sempre OGGI."""

    @classmethod
    def today(cls):
        return cls(OGGI.year, OGGI.month, OGGI.day)


def leggi_bandi_prima() -> list[dict]:
    with BANDI_PRIMA.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def risultati_per_comuni(percorso_db: Path) -> dict:
    """Esegue le interrogazioni sui bandi viste da un comune.

    Restituisce, per ogni chiamata, testo, fonti ed esito. Il database e'
    quello in percorso_db; la data e' fissata dal chiamante.
    """
    conn = sqlite3.connect(percorso_db)
    conn.row_factory = sqlite3.Row
    try:
        temi = [
            r["tema"]
            for r in conn.execute(
                "SELECT DISTINCT tema FROM bandi WHERE tema IS NOT NULL ORDER BY tema"
            )
        ]
        ids = [r["id"] for r in conn.execute("SELECT id FROM bandi ORDER BY id")]

        chiamate = {
            "bandi_aperti_per_ente": lambda: bandi_aperti_per_ente(conn, COMUNE)
        }
        chiamate["bandi_in_scadenza(60)"] = lambda: bandi_in_scadenza(conn, COMUNE)
        chiamate["bandi_in_scadenza(400)"] = lambda: bandi_in_scadenza(
            conn, COMUNE, 400
        )
        for tema in [*temi, "pesca"]:
            chiamate[f"bandi_per_tema({tema})"] = lambda t=tema: bandi_per_tema(conn, t)
        for id_bando in [*ids, "inesistente"]:
            chiamate[f"dettaglio_bando({id_bando})"] = lambda i=id_bando: (
                dettaglio_bando(conn, i)
            )

        risultati = {}
        for nome, chiamata in chiamate.items():
            r = chiamata()
            risultati[nome] = {"testo": r.testo, "fonti": r.fonti, "trovato": r.trovato}
    finally:
        conn.close()

    s = repertorio.stato_archivio(COMUNE)
    risultati["stato_archivio"] = {"testo": s, "fonti": [], "trovato": True}
    return risultati


@pytest.fixture
def data_fissa(monkeypatch):
    monkeypatch.setattr(interrogazioni_bandi, "date", DataFissa)


def test_interrogazioni_uguali_per_i_comuni(tmp_path, monkeypatch, data_fissa):
    percorso = tmp_path / "prova.sqlite"
    monkeypatch.setattr(schema, "SQLITE_PATH", percorso)

    bandi, beneficiari = migra(leggi_bandi_prima())

    conn = sqlite3.connect(percorso)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(schema.DDL)
    conn.execute(
        "INSERT INTO fonti (codice, nome, url_base, schema_link, fonte, "
        "verificato_il) VALUES ('regione-toscana', 'Portale bandi Regione Toscana', "
        "'https://www.regione.toscana.it', '^/-/', 'prova', '2026-11-11')"
    )
    conn.execute(
        "INSERT INTO enti (codice_fiscale, nome, tipo, regione, provincia, fonte, "
        "verificato_il) VALUES (?, 'Comune di prova', 'comune', 'Toscana', "
        "'Pistoia', 'prova', '2026-11-11')",
        (COMUNE,),
    )
    for tabella, righe in (("bandi", bandi), ("beneficiari_bando", beneficiari)):
        # Solo le colonne che i dati di allora hanno: quelle aggiunte dopo
        # (es. natura) prendono il valore predefinito dello schema
        colonne = [
            c for c in schema.TABELLE_DA_CSV[tabella] if any(c in r for r in righe)
        ]
        conn.executemany(
            f"INSERT INTO {tabella} ({', '.join(colonne)}) "
            f"VALUES ({', '.join('?' for _ in colonne)})",
            [[r.get(c) or None for c in colonne] for r in righe],
        )
    conn.commit()
    conn.close()

    attesi = json.loads(RIFERIMENTO.read_text(encoding="utf-8"))
    ottenuti = risultati_per_comuni(percorso)

    assert list(ottenuti) == list(attesi)
    for nome, atteso in attesi.items():
        assert ottenuti[nome] == atteso, nome
