"""Le righe del pannello di verifica: colore, contesto e collegamenti.

Il contesto e' un ritaglio di 40 caratteri della risposta, e puo' tagliare
a meta' una citazione: "], decreto). Ci sono bandi..." o "(fonte: [D1".
Dentro :red[...] una parentesi quadra non protetta chiude il colore in
anticipo, e il resto della riga esce rotto (prova in Edge del 14 novembre
2026). Nessun modello, nessuna rete.
"""

import pytest

from app.app import riga_esito
from src.database.modelli import VoceBando
from src.verification.controllo import Esito

URL = "https://www.regione.toscana.it/-/bando-parcheggi-2026"
COLLEGAMENTI = {"D1.1": VoceBando("riga", "fonte", titolo="Parcheggi", url=URL)}


def fine_del_colore(riga: str) -> int:
    """La posizione della ']' che chiude il colore, saltando quelle protette.

    -1 se il colore non si chiude mai.
    """
    inizio = riga.index("[") + 1
    profondita = 1
    i = inizio
    while i < len(riga):
        carattere = riga[i]
        if carattere == "\\":
            i += 2
            continue
        if carattere == "[":
            profondita += 1
        elif carattere == "]":
            profondita -= 1
            if profondita == 0:
                return i
        i += 1
    return -1


@pytest.mark.parametrize(
    ("stato", "colore"), [("non_trovato", ":red["), ("citazione_generica", ":orange[")]
)
@pytest.mark.parametrize(
    "contesto",
    [
        # comincia con la ']' di una citazione tagliata
        "], decreto). Ci sono bandi con scadenza 2026-11-30 (fonte: [D1], Portale).",
        # finisce con una '[' rimasta aperta
        "Il bando parcheggi scade il 2027-01-15 (fonte: [D1",
    ],
)
def test_il_contesto_non_chiude_il_colore(stato, colore, contesto):
    e = Esito("data", "2026-11-30", ["D1.1"], stato, contesto=contesto)

    riga = riga_esito(e, COLLEGAMENTI)

    assert riga.startswith(colore)
    assert fine_del_colore(riga) == len(riga) - 1
    # il collegamento all'etichetta del bando resta intatto, dentro il colore
    assert f"[D1.1](<{URL}>)" in riga


def test_il_contesto_protetto_si_legge_uguale():
    e = Esito(
        "data",
        "2026-11-30",
        ["D1"],
        "non_trovato",
        contesto="], decreto). (fonte: [D1]",
    )

    riga = riga_esito(e, COLLEGAMENTI)

    assert r"_\], decreto). (fonte: \[D1\]_" in riga


def test_un_dato_verificato_non_ha_colore_e_ha_il_collegamento():
    e = Esito("atto", "18191", ["D1.1"], "verificato", contesto="(fonte: [D1.1], decr")

    riga = riga_esito(e, COLLEGAMENTI)

    assert not riga.startswith(":")
    assert f"→ fonti [D1.1](<{URL}>)" in riga
    assert r"(fonte: \[D1.1\], decr" in riga


# --- Citazioni ripetute: una riga e un conteggio per dato e fonti ---


def test_tre_occorrenze_con_la_stessa_fonte_diventano_una_riga():
    from app.app import raggruppa_esiti

    stesso = [Esito("atto", "24316", ["D1.1"], "verificato") for _ in range(3)]
    gruppi = raggruppa_esiti(stesso)

    assert [(e.valore, n) for e, n in gruppi] == [("24316", 3)]
    assert "×3" in riga_esito(gruppi[0][0], COLLEGAMENTI, gruppi[0][1])
    assert "×" not in riga_esito(gruppi[0][0], COLLEGAMENTI)


def test_lo_stesso_valore_con_fonti_diverse_resta_in_due_righe():
    from app.app import raggruppa_esiti

    esiti = [
        Esito("atto", "24316", ["D1.1"], "verificato"),
        Esito("atto", "24316", ["D1.2"], "verificato"),
        Esito("atto", "24316", ["D1.1"], "verificato"),
    ]
    assert [(e.frammenti, n) for e, n in raggruppa_esiti(esiti)] == [
        (["D1.1"], 2),
        (["D1.2"], 1),
    ]


def test_anche_non_trovati_e_senza_fonte_si_uniscono_ma_non_tra_stati_diversi():
    from app.app import raggruppa_esiti

    esiti = [
        Esito("quantita", "56", [], "non_citato"),
        Esito("quantita", "56", [], "non_citato"),
        Esito("quantita", "7.000", ["D1"], "non_trovato"),
        Esito("quantita", "7.000", ["D1"], "non_trovato"),
        Esito("quantita", "7.000", ["D1"], "verificato"),
    ]
    assert [(e.stato, e.valore, n) for e, n in raggruppa_esiti(esiti)] == [
        ("non_citato", "56", 2),
        ("non_trovato", "7.000", 2),
        ("verificato", "7.000", 1),
    ]


def dati_parcheggi():
    """Un blocco con un bando, come lo da' bandi_aperti_per_ente."""
    from src.database.modelli import Risultato

    voce = VoceBando(
        "«Bando parcheggi 2026» (Regione Toscana) | scade il 2026-11-30 "
        "| atto: decreto dirigenziale n. 18191 | url: https://esempio.it/p",
        "Portale, decreto dirigenziale n. 18191 (dati estratti il 2026-11-11)",
        titolo="Bando parcheggi 2026",
        url="https://esempio.it/p",
    )
    risultato = Risultato(
        f"Bandi aperti (alla data del 2026-11-11), 1 in archivio:\n- [#1] {voce.testo}",
        fonti=[voce.fonte],
        voci=[voce],
    )
    return [("bandi_aperti_per_ente", risultato)]


def pagina_verifica(risposta):
    # Copia di dati_parcheggi: AppTest esegue solo il corpo di questa funzione
    from app.app import mostra_verifica
    from src.database.modelli import Risultato, VoceBando

    voce = VoceBando(
        "«Bando parcheggi 2026» (Regione Toscana) | scade il 2026-11-30 "
        "| atto: decreto dirigenziale n. 18191 | url: https://esempio.it/p",
        "Portale, decreto dirigenziale n. 18191 (dati estratti il 2026-11-11)",
        titolo="Bando parcheggi 2026",
        url="https://esempio.it/p",
    )
    risultato = Risultato(
        f"Bandi aperti (alla data del 2026-11-11), 1 in archivio:\n- [#1] {voce.testo}",
        fonti=[voce.fonte],
        voci=[voce],
    )
    mostra_verifica(
        {
            "risposta": risposta,
            "documenti": [],
            "esiti_dati": [("bandi_aperti_per_ente", risultato)],
        }
    )


def test_il_pannello_conta_e_mostra_una_volta_le_citazioni_ripetute():
    from streamlit.testing.v1 import AppTest

    from src.verification.controllo import verifica

    citazione = "(fonte: [D1.1], decreto dirigenziale n. 18191)"
    risposta = " ".join(
        f"Il bando parcheggi scade il 2026-11-30 {citazione}." for _ in range(3)
    )
    pagina = AppTest.from_function(
        pagina_verifica, kwargs={"risposta": risposta}, default_timeout=30
    )
    pagina.run()
    assert not pagina.exception, pagina.exception

    # Il verificatore resta com'e': ogni citazione ha i suoi esiti
    grezzi = [e.valore for e in verifica(risposta, [], dati_parcheggi())]
    assert sorted(grezzi) == ["18191"] * 3 + ["2026-11-30"] * 3
    [messaggio] = [e.value for e in pagina.success]
    assert messaggio == "Dati verificati nella fonte citata: 2."
    righe = [e.value for e in pagina.markdown]
    assert any("**2026-11-30**" in r and "×3" in r for r in righe)
    assert any("**18191**" in r and "×3" in r for r in righe)
