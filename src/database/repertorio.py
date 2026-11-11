"""Repertorio chiuso di interrogazioni.

Il modello non scrive SQL: sceglie un'interrogazione di questo elenco
e ne fornisce i parametri. Le query sono scritte e verificate a mano.
"""

from collections.abc import Callable
from dataclasses import dataclass

from src.database.interrogazioni_bandi import (
    NOMI_ENTE,
    SOLO_BANDI,
    bandi_aperti_per_ente,
    bandi_in_scadenza,
    bandi_per_beneficiario,
    bandi_per_tema,
    data_di_oggi,
    dettaglio_bando,
    filtro_ente,
    tipo_ente,
)
from src.database.interrogazioni_dati import (
    dato_territoriale,
    densita_abitativa,
    popolazione_anno,
    popolazione_serie,
    popolazione_ultima,
    popolazione_variazione,
)
from src.database.modelli import Risultato
from src.database.schema import connetti
from src.estrazione.beneficiari import TIPI_BENEFICIARIO


@dataclass
class Voce:
    """Una voce del repertorio, come la vede il modello."""

    nome: str
    descrizione: str
    parametri: dict
    funzione: Callable
    per_ente: bool = False


REPERTORIO = [
    Voce(
        "popolazione_anno",
        "Numero di residenti in un anno specifico",
        {"anno": "intero, l'anno richiesto"},
        popolazione_anno,
        per_ente=True,
    ),
    Voce(
        "popolazione_ultima",
        "Il dato di popolazione più recente disponibile",
        {},
        popolazione_ultima,
        per_ente=True,
    ),
    Voce(
        "popolazione_serie",
        "L'intera serie storica della popolazione, anno per anno",
        {},
        popolazione_serie,
        per_ente=True,
    ),
    Voce(
        "popolazione_variazione",
        "Variazione della popolazione tra due anni, in valore e percentuale",
        {"da": "intero opzionale", "a": "intero opzionale"},
        popolazione_variazione,
        per_ente=True,
    ),
    Voce(
        "dato_territoriale",
        "Un dato stabile sul territorio (superficie, altitudine, ecc.)",
        {"chiave": "stringa, il nome del dato"},
        dato_territoriale,
        per_ente=True,
    ),
    Voce(
        "densita_abitativa",
        "Abitanti per chilometro quadrato, calcolata sui dati più recenti",
        {},
        densita_abitativa,
        per_ente=True,
    ),
    Voce(
        "bandi_aperti_per_ente",
        "I bandi ancora aperti a cui l'ente può presentare domanda",
        {},
        bandi_aperti_per_ente,
        per_ente=True,
    ),
    Voce(
        "bandi_in_scadenza",
        "I bandi per l'ente che scadono entro un certo numero di giorni",
        {"giorni": "intero opzionale, predefinito 60"},
        bandi_in_scadenza,
        per_ente=True,
    ),
    Voce(
        "bandi_per_beneficiario",
        "I bandi aperti per un tipo di beneficiario diverso dall'ente "
        "(imprese, associazioni, cittadini...)",
        {"tipo": "stringa, uno dei codici: " + ", ".join(TIPI_BENEFICIARIO)},
        bandi_per_beneficiario,
    ),
    Voce(
        "bandi_per_tema",
        "I bandi di un certo tema (commercio, casa, ambiente, formazione...)",
        {"tema": "stringa, il tema da cercare"},
        bandi_per_tema,
    ),
    Voce(
        "dettaglio_bando",
        "Tutti i dati strutturati di un singolo bando, per identificativo o titolo",
        {"id_bando": "stringa, identificativo o parte del titolo"},
        dettaglio_bando,
    ),
]

PER_NOME = {v.nome: v for v in REPERTORIO}


def descrivi_repertorio() -> str:
    """Il catalogo in forma testuale, da mettere nel prompt del router."""
    righe = []
    for v in REPERTORIO:
        if v.parametri:
            par = ", ".join(f"{k} ({d})" for k, d in v.parametri.items())
        else:
            par = "nessun parametro"
        righe.append(f"- {v.nome}: {v.descrizione}. Parametri: {par}")
    return "\n".join(righe)


def esegui(nome: str, parametri: dict, codice_ente: str) -> Risultato:
    """Esegue un'interrogazione del repertorio."""
    if nome not in PER_NOME:
        return Risultato(
            f"Interrogazione '{nome}' non presente nel repertorio.",
            trovato=False,
        )
    voce = PER_NOME[nome]
    parametri = {
        chiave: valore
        for chiave, valore in parametri.items()
        if chiave != "codice_ente"
    }
    conn = connetti()
    try:
        if voce.per_ente:
            return voce.funzione(conn, codice_ente, **parametri)
        return voce.funzione(conn, **parametri)
    except TypeError as errore:
        return Risultato(f"Parametri non validi: {errore}", trovato=False)
    finally:
        conn.close()


def stato_archivio(codice_ente: str) -> str:
    """Riepilogo di cosa contiene davvero il database, per il router."""
    conn = connetti()
    try:
        righe = []

        pop = conn.execute(
            "SELECT COUNT(*), MIN(anno), MAX(anno) FROM popolazione WHERE codice_ente = ?",
            (codice_ente,),
        ).fetchone()
        righe.append(
            f"popolazione: {pop[0]} anni, dal {pop[1]} al {pop[2]}"
            if pop[0]
            else "popolazione: VUOTA"
        )

        bil = conn.execute(
            "SELECT COUNT(*) FROM bilancio WHERE codice_ente = ?", (codice_ente,)
        ).fetchone()[0]
        righe.append(
            f"bilancio: {bil} voci"
            if bil
            else "bilancio: VUOTA, nessun dato disponibile"
        )

        tur = conn.execute(
            "SELECT COUNT(*) FROM turismo WHERE codice_ente = ?", (codice_ente,)
        ).fetchone()[0]
        righe.append(
            f"turismo: {tur} rilevazioni"
            if tur
            else "turismo: VUOTA, nessun dato disponibile"
        )

        chiavi = conn.execute(
            "SELECT chiave FROM territorio WHERE codice_ente = ?", (codice_ente,)
        ).fetchall()
        elenco = ", ".join(r["chiave"] for r in chiavi) or "nessuna"
        righe.append(f"territorio: chiavi disponibili: {elenco}")

        righe.append(_stato_bandi(conn, codice_ente))

        return "\n".join(f"- {r}" for r in righe)
    finally:
        conn.close()


def _stato_bandi(conn, codice_ente: str) -> str:
    """La riga dei bandi nel riepilogo: quanti, e quanti aperti per l'ente."""
    totale = conn.execute(f"SELECT COUNT(*) FROM bandi WHERE {SOLO_BANDI}").fetchone()[
        0
    ]
    if not totale:
        return "bandi: VUOTA, nessun dato disponibile"

    tipo = tipo_ente(conn, codice_ente)
    if tipo is None:
        return f"bandi: {totale} in archivio"

    oggi = data_di_oggi().isoformat()
    filtro, parametri = filtro_ente(tipo)
    aperti, da_verificare = conn.execute(
        f"SELECT COUNT(*), SUM(classificato_il IS NULL) FROM bandi "
        f"WHERE {filtro} AND {SOLO_BANDI} AND (scadenza IS NULL OR scadenza >= ?)",
        (*parametri, oggi),
    ).fetchone()
    testo = (
        f"bandi: {totale} in archivio, di cui {aperti} aperti a cui "
        f"{NOMI_ENTE[tipo]['uno']} può presentare domanda"
    )
    if tipo == "unione_comuni" and da_verificare:
        testo += f" ({da_verificare} con beneficiari non ancora classificati)"
    return testo
