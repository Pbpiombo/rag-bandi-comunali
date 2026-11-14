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
