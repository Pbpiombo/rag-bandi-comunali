"""Test della lettura dei dati ISTAT: bilancio demografico e superfici.

Le risposte sono estratti salvati del modulo di demo.istat.it (solo
gennaio e febbraio), non richieste al sito; il file delle superfici e'
un xlsx minimo costruito nel test.
"""

import json
import zipfile
from pathlib import Path

import pytest

from scripts.manutenzione.carica_istat import (
    Dato,
    differenze,
    leggi_risposta,
    riga_popolazione,
    riga_superficie,
    righe_xlsx,
    superfici,
)

DATI = Path(__file__).parent / "dati"
ABETONE_2026 = (DATI / "istat_D7B_2026_047023.json").read_text(encoding="utf-8")
SAMBUCA_2019 = (DATI / "istat_D7B_2019_047018.json").read_text(encoding="utf-8")


def test_totale_di_gennaio_provvisorio():
    dato = leggi_risposta(ABETONE_2026, 2026, "047023")
    assert dato == Dato("047023", 2026, 1834, provvisorio=True)


def test_anno_definitivo():
    dato = leggi_risposta(SAMBUCA_2019, 2019, "047018")
    assert dato == Dato("047018", 2019, 1539, provvisorio=False)


def test_anno_diverso_da_quello_chiesto():
    with pytest.raises(ValueError, match="la tabella"):
        leggi_risposta(ABETONE_2026, 2025, "047023")


def test_comune_diverso_da_quello_chiesto():
    with pytest.raises(ValueError, match="0 righe"):
        leggi_risposta(ABETONE_2026, 2026, "047018")


def test_manca_gennaio():
    risposta = json.loads(ABETONE_2026)
    risposta["datatable"]["data"] = [
        r for r in risposta["datatable"]["data"] if r["mese"] != 1
    ]
    with pytest.raises(ValueError, match="0 righe"):
        leggi_risposta(json.dumps(risposta), 2026, "047023")


def test_risposta_di_errore():
    errore = '{"type":"error","message":"Errore non specificato"}'
    with pytest.raises(ValueError, match="Errore non specificato"):
        leggi_risposta(errore, 2026, "047023")


def test_fonte_con_indirizzo_data_e_provvisorio():
    riga = riga_popolazione(Dato("047023", 2026, 1834, True), "CF", "2026-11-13")
    assert riga["data_rilevazione"] == "2026-01-01"
    assert "(dato provvisorio)" in riga["fonte"]
    assert "https://demo.istat.it/app/?i=D7B&a=2026&l=it" in riga["fonte"]
    assert "scaricato il 2026-11-13" in riga["fonte"]

    definitivo = riga_popolazione(Dato("047018", 2019, 1539, False), "CF", "x")
    assert "provvisorio" not in definitivo["fonte"]


def test_cambia_un_anno_definitivo_blocca():
    nuove = [riga_popolazione(Dato("047023", 2019, 2000, False), "CF", "g")]
    ammesse, bloccanti = differenze(nuove, {("CF", 2019): (2019, "ISTAT")})
    assert ammesse == []
    assert bloccanti == ["CF 2019: 2019 in archivio, 2000 nel file nuovo"]


def test_cambia_un_anno_provvisorio_e_ammesso():
    nuove = [riga_popolazione(Dato("047023", 2025, 1830, False), "CF", "g")]
    esistenti = {("CF", 2025): (1829, "ISTAT ... (dato provvisorio)")}
    ammesse, bloccanti = differenze(nuove, esistenti)
    assert len(ammesse) == 1
    assert bloccanti == []


def test_valori_uguali_e_righe_nuove_non_sono_differenze():
    nuove = [
        riga_popolazione(Dato("047023", 2019, 2019, False), "CF", "g"),
        riga_popolazione(Dato("047018", 2019, 1539, False), "ALTRO", "g"),
    ]
    assert differenze(nuove, {("CF", 2019): (2019, "ISTAT")}) == ([], [])


def xlsx_minimo(percorso: Path, righe: list[list[str]]) -> Path:
    """Un xlsx con un foglio e le stringhe condivise, come quello ISTAT."""
    condivise: list[str] = []
    celle = []
    for riga in righe:
        valori = []
        for valore in riga:
            try:
                float(valore)
                valori.append(f"<c><v>{valore}</v></c>")
            except ValueError:
                condivise.append(valore)
                valori.append(f'<c t="s"><v>{len(condivise) - 1}</v></c>')
        celle.append(f"<row>{''.join(valori)}</row>")
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    with zipfile.ZipFile(percorso, "w") as z:
        z.writestr(
            "xl/sharedStrings.xml",
            f"<sst {ns}>"
            + "".join(f"<si><t>{s}</t></si>" for s in condivise)
            + "</sst>",
        )
        z.writestr(
            "xl/worksheets/sheet1.xml",
            f"<worksheet {ns}><sheetData>{''.join(celle)}</sheetData></worksheet>",
        )
    return percorso


RIGHE_ALTIMETRIA = [
    ["DATI COMUNALI", "DATI ALTIMETRICI"],
    ["COD_REG", "PRO_COM", "COMUNE", "AREA_KMQ", "ALT MIN"],
    ["9", "47018", "Sambuca Pistoiese", "77.239330628999909", "377"],
    ["9", "47023", "Abetone Cutigliano", "74.9917891099999", "544"],
    ["1", "1001", "Agliè", "13.146257666099901", "279"],
]


def test_superfici_dal_file_dell_altimetria(tmp_path):
    percorso = xlsx_minimo(tmp_path / "a.xlsx", RIGHE_ALTIMETRIA)
    valori = superfici(righe_xlsx(percorso), ["047023", "047018"])
    assert valori == {"047023": 74.99, "047018": 77.24}


def test_comune_senza_superficie(tmp_path):
    percorso = xlsx_minimo(tmp_path / "a.xlsx", RIGHE_ALTIMETRIA)
    with pytest.raises(ValueError, match="047024"):
        superfici(righe_xlsx(percorso), ["047023", "047024"])


def test_file_senza_intestazione():
    with pytest.raises(ValueError, match="intestazione"):
        superfici([["PRO_COM", "COMUNE"], ["47023", "Abetone"]], ["047023"])


def test_fonte_della_superficie():
    riga = riga_superficie("CF", 74.99, "2026-11-13")
    assert riga["chiave"] == "superficie"
    assert riga["unita"] == "kmq"
    assert "Altimetria Comuni al 31 dicembre 2021, colonna AREA_KMQ" in riga["fonte"]
    assert "Altimetria_Comuni-al-31_12_2021.xlsx" in riga["fonte"]
    assert "scaricato il 2026-11-13" in riga["fonte"]
