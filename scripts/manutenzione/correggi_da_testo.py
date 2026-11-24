"""Corregge a mano campi dei bandi e dei beneficiari, con le frasi di un testo salvato.

Uso:
    python -m scripts.manutenzione.correggi_da_testo --prova   verifica soltanto
    python -m scripts.manutenzione.correggi_da_testo           corregge

Come correggi_atti, ma senza rete: le frasi che provano il valore corretto
si cercano (con frase_nel_testo) nel testo della pagina gia' salvato in
dati-grezzi, non in una pagina riscaricata. Per ogni correzione: la
tabella, la riga, i valori che devono esserci in archivio, i valori
corretti, le frasi e il file del testo. Si corregge solo se i valori in
archivio sono ancora tutti quelli attesi e tutte le frasi si trovano;
altrimenti si salta e lo si dice. I campi di una correzione cambiano
insieme (per esempio pubblicato_il e pubblicato_origine).

Tabelle e campi correggibili stanno in CAMPI. Una riga di
beneficiari_bando si indica con id_bando e tipo, e deve essere una sola;
la sua correzione mette origine 'manuale'.

Una riga nuova di beneficiari_bando (Aggiunta, campi in AGGIUNGIBILI) si
aggiunge solo se il bando e' in archivio, se non c'e' gia' una riga con
la stessa chiave (id_bando, tipo, frase), se ha origine 'manuale' e se la
sua frase e tutte le altre frasi di prova si trovano nel testo salvato.

Un periodo di sospensione si aggiunge allo stesso modo (sospensioni_bando,
chiave id_bando e numero); la sua riapertura e' una correzione di
riaperto_il e riapertura_frase, e riapertura_frase e' anch'essa una frase
di prova (FRASI_NEI_CAMPI). Una frase di prova vuota fa saltare la
modifica.

Con --prova, per ogni correzione si stampano anche le frasi di prova, una
per una, con "trovata: si'" o "trovata: no".

Alla fine riversa nei CSV le tabelle toccate. Rilanciarlo non cambia
nulla: una correzione gia' applicata, o una riga gia' aggiunta, si
riconosce e si salta.

Queste correzioni non sono protette da una riestrazione futura: vanno
ricontrollate se il bando si riestrae.
"""

import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

from src.config import DATI_GREZZI_DIR
from src.database.schema import aggiorna_csv, connetti
from src.estrazione.beneficiari import frase_nel_testo

# Tabella -> (campi che identificano la riga, campi correggibili)
CAMPI = {
    "bandi": (
        ("id",),
        (
            "pubblicato_il",
            "pubblicato_origine",
            "scadenza",
            "scadenza_nota",
            "riferimento_atto",
            "verificato_il",
            "beneficiari",
            "dotazione",
        ),
    ),
    "beneficiari_bando": (("id_bando", "tipo"), ("soggetto", "origine")),
    # La riapertura di una sospensione: riaperto_il con la sua frase
    "sospensioni_bando": (("id_bando", "numero"), ("riaperto_il", "riapertura_frase")),
}

# Tabella -> i campi corretti che sono frasi di prova: si cercano nel testo
# insieme alle frasi della correzione, e non possono essere vuoti
FRASI_NEI_CAMPI = {"sospensioni_bando": ("riapertura_frase",)}

# Tabella -> (campi della chiave, campi ammessi in una riga nuova)
AGGIUNGIBILI = {
    # Un periodo di sospensione; la sua frase e' quella della decorrenza
    "sospensioni_bando": (
        ("id_bando", "numero"),
        (
            "id_bando",
            "numero",
            "ambito",
            "sospeso_dal",
            "sospesi",
            "resta_aperto",
            "atto",
            "frase",
            "riaperto_il",
            "riapertura_frase",
            "verificato_il",
            "origine",
        ),
    ),
    "beneficiari_bando": (
        ("id_bando", "tipo", "frase"),
        (
            "id_bando",
            "tipo",
            "soggetto",
            "condizioni",
            "frase",
            "confidenza",
            "origine",
        ),
    ),
}


@dataclass(frozen=True)
class Correzione:
    """Una correzione: dove, da che cosa, a che cosa, con quali prove."""

    tabella: str
    riga: dict
    attesi: dict
    corretti: dict
    frasi: tuple
    testo: Path


@dataclass(frozen=True)
class Aggiunta:
    """Una riga nuova: tutti i suoi campi, con le frasi che la provano.

    La frase della riga si cerca sempre nel testo, insieme a frasi.
    """

    tabella: str
    riga: dict
    frasi: tuple
    testo: Path


TESTO_RIEVOCAZIONE = (
    DATI_GREZZI_DIR / "manuali" / "2026-11-19" / "fondo-rievocazione-storica-2027.txt"
)

# Riga 355 del testo salvato, la prima frase
FRASE_BENEFICIARI_RIEVOCAZIONE = (
    "Possono presentare istanza di contributo gli Enti locali, soggetti "
    "pubblici, enti di rievocazione storica, vale a dire le associazioni di "
    "promozione sociale, le organizzazioni non lucrative di utilità sociale e "
    "le fondazioni che hanno per fine statutario la tutela e la trasmissione "
    "della memoria storica"
)

CORREZIONI_19_11 = [
    # Il modello ha preso la data del decreto (20/03/2025) al posto della
    # data di pubblicazione della pagina, righe 21 e 360 del testo salvato
    Correzione(
        tabella="bandi",
        riga={"id": "fondo-rievocazione-storica-2027"},
        attesi={"pubblicato_il": "2025-03-20", "pubblicato_origine": "atto"},
        corretti={"pubblicato_il": "2026-11-03", "pubblicato_origine": "pubblicazione"},
        frasi=("3 Novembre 2026",),
        testo=TESTO_RIEVOCAZIONE,
    ),
    # Il soggetto della riga altro_ente_pubblico era "Enti locali": il tipo
    # viene da "soggetti pubblici", riga 355 del testo salvato
    Correzione(
        tabella="beneficiari_bando",
        riga={
            "id_bando": "fondo-rievocazione-storica-2027",
            "tipo": "altro_ente_pubblico",
        },
        attesi={"soggetto": "Enti locali", "origine": "estrazione"},
        corretti={"soggetto": "soggetti pubblici", "origine": "manuale"},
        frasi=(FRASE_BENEFICIARI_RIEVOCAZIONE,),
        testo=TESTO_RIEVOCAZIONE,
    ),
]

# --- 24/11/2026: testi delle pagine salvate il 23 e il 24/11/2026 ---

MANUALI_24_11 = DATI_GREZZI_DIR / "manuali" / "2026-11-24"

ALTA_FORMAZIONE = "alta-formazione-e-ricerca-azione-bando-2026-finanziam-cbac8f"
INCENTIVI = "incentivi-ai-datori-di-lavoro-privati-per-l-occupazio-801298"
GIORNALI = "contributi-per-distribuzione-e-commercio-al-dettaglio-f747b7"

NOTA_ALTA_FORMAZIONE = (
    "Ulteriore proroga fino al 19 novembre 2026 con decreto dirigenziale "
    "23693 del 26 ottobre 2026; prima proroga al 2 novembre 2026 con decreto "
    "del 22 settembre; scadenza iniziale 15 ottobre 2026"
)
ATTO_ALTA_FORMAZIONE = (
    "Decreto dirigenziale 19633 del 25 agosto 2026, modificato con decreti "
    "21092 del 27 settembre 2026, 21570 del 28 settembre 2026 e 23693 del 26 "
    "ottobre 2026"
)

NOTA_INCENTIVI = (
    "Il campo strutturato della pagina indica scadenza 10/01/2027, ma il "
    "testo riporta anche una finestra di domanda fino al 10/01/2028 per le "
    "assunzioni/trasformazioni realizzate nel 2027; il bando è stato "
    "prorogato dalla scadenza iniziale del 10 gennaio 2026 al 10 gennaio 2027 "
    "e successivamente aperta una nuova finestra fino al 10 gennaio 2028."
)
BENEFICIARI_INCENTIVI = (
    "Il bando è rivolto a datori di lavoro privati (imprese, enti, "
    "associazioni, liberi professionisti e piu in generale tutti i datori di "
    "lavoro privati ad esclusione delle persone fisiche in qualita di datori "
    "di lavoro domestico)"
)
ATTO_INCENTIVI = (
    "Decreto dirigenziale Arti 848 del 2 novembre 2023, modificato con "
    "decreto 995 del 27 dicembre 2023, rettificato con decreto Arti 689 del "
    "29 luglio 2025, rifinanziato con decreto Arti 1043 del 18 novembre 2025, "
    "modificato con decreto Arti 1189 del 29 dicembre 2025, rifinanziato con "
    "decreto Arti 1019 del 3 settembre 2026, modificato con decreto Arti 1318 "
    "del 6 novembre 2026"
)
SOSPENSIONE_INCENTIVI = (
    "Sospeso dall'8 luglio 2026 (decreto n. 742/2026 di Arti) per le "
    "categorie di destinatari dell'articolo 5 lettere a, b, c, d, e (over 30 "
    "disoccupati licenziati dal primo gennaio 2021, over 30 disoccupati "
    "svantaggiati, over 55 disoccupati, under 30 disoccupati, donne "
    "disoccupate): per queste si istruiscono solo le domande presentate "
    "entro l'8 luglio 2026. Resta aperto solo per l'assunzione di persone "
    "con disabilità iscritte negli elenchi del collocamento mirato "
    "(articolo 5 lettera f)."
)
# Nei beneficiari una riga sola; la sospensione per intero sta nella nota
# sulla scadenza (decisione del 24/11/2026: formatta_bando mostra le due di
# seguito)
APERTO_SOLO_LETTERA_F = (
    "Dall'8 luglio 2026 il bando è aperto solo per l'assunzione di persone "
    "con disabilità iscritte negli elenchi del collocamento mirato (articolo "
    "5 lettera f); per le altre categorie è sospeso."
)

# Le frasi della pagina degli incentivi, righe 122-127 del testo salvato.
# "Il bando resta aperto solo per" ha uno spazio dopo le virgolette, come
# sulla pagina.
FRASI_SOSPENSIONE_INCENTIVI = (
    (
        "La sospensione decorre dal 8 luglio 2026, data di pubblicazione del "
        "decreto n. 742/2026 di Arti sul Burt."
    ),
    (
        'Il bando resta aperto solo per " Persone con disabilità, iscritte negli '
        "appositi elenchi del collocamento mirato di cui all’art.8 delle L. "
        "68/1999, assunte a tempo indeterminato o a tempo determinato con un "
        "contratto della durata di almeno 12 mesi (articolo 5 lettera f del "
        "bando)."
    ),
    "Sospensione del bando per i seguenti destinatari:",
    (
        "over 30 disoccupati licenziati dal primo gennaio 2021, over 30 "
        "disoccupati svantaggiati, over 55 disoccupati, di cui all'articolo 5 "
        "lettere a), b) e c) del bando"
    ),
    "under 30 disoccupati, di cui all'articolo 5 lettera d) del bando",
    "donne disoccupate, di cui all'articolo 5 lettera e) del bando",
    "saranno istruite soltanto le domande presentate entro l'8 luglio 2026",
)

# Il periodo di sospensione dall'8/07/2026, in sospensioni_bando (decisione
# del 24/11/2026). Le categorie si scrivono con le parole della pagina
# (righe 123-125 e 127 del testo salvato) e ciascuna e' anche una frase di
# prova: se una non si trova, la riga non si scrive. Il periodo precedente
# (sospensione della lettera e dal 24/07/2024, riapertura dopo il
# 23/10/2024, righe 150-154) e' in coda: la data di riapertura e' da
# interpretare.
CATEGORIE_SOSPESE_INCENTIVI = (
    "over 30 disoccupati licenziati dal primo gennaio 2021",
    "over 30 disoccupati svantaggiati",
    "over 55 disoccupati",
    "under 30 disoccupati",
    "donne disoccupate",
)
CATEGORIA_APERTA_INCENTIVI = (
    "Persone con disabilità, iscritte negli appositi elenchi del collocamento mirato"
)
SOSPESI_INCENTIVI = (
    f"{CATEGORIE_SOSPESE_INCENTIVI[0]}, {CATEGORIE_SOSPESE_INCENTIVI[1]}, "
    f"{CATEGORIE_SOSPESE_INCENTIVI[2]} (articolo 5 lettere a, b e c), "
    f"{CATEGORIE_SOSPESE_INCENTIVI[3]} (articolo 5 lettera d), "
    f"{CATEGORIE_SOSPESE_INCENTIVI[4]} (articolo 5 lettera e)"
)
RESTA_APERTO_INCENTIVI = (
    f"solo per {CATEGORIA_APERTA_INCENTIVI[0].lower()}"
    f"{CATEGORIA_APERTA_INCENTIVI[1:]} (articolo 5 lettera f)"
)
# Riga 126 del testo salvato, la prima frase
FRASE_DECORRENZA_INCENTIVI = (
    "La sospensione decorre dal 8 luglio 2026, data di pubblicazione del "
    "decreto n. 742/2026 di Arti sul Burt."
)

BENEFICIARI_GIORNALI = (
    "Possono presentare domanda: A) Soggetti iscritti al Registro delle "
    "Imprese... B) Soggetti iscritti al Registro delle Imprese... C) Soggetti "
    "iscritti al Registro delle Imprese..."
)

# Righe 98, 101 e 102 del testo salvato. Le prime due sono le frasi delle
# righe A e B gia' in beneficiari_bando; la terza ha gli spazi accanto alle
# virgolette come sulla pagina, che il modello aveva tolto: per questo
# l'estrazione del 24/11 l'ha scartata (frase_nel_testo).
FRASE_GIORNALI_A = (
    "A) Soggetti iscritti al Registro delle Imprese presso la Camera di "
    "commercio industria artigianato agricoltura, Cciaa (risultanti impresa "
    "attiva), oppure titolari di una partita Iva attiva, esercenti punti "
    "vendita con sede nei territori classificati come “Toscana diffusa”"
)
FRASE_GIORNALI_B = (
    "B) Soggetti iscritti al Registro delle Imprese presso la Cciaa "
    "(risultanti impresa attiva), oppure titolari di una partita Iva attiva, "
    "esercenti punti vendita esclusivi per la rivendita di giornali e riviste "
    "(edicole) codice Ateco primario 47.62.10 “Commercio al dettaglio di "
    "giornali e altre pubblicazioni periodiche” aventi sede su tutto il "
    "restante territorio regionale."
)
FRASE_GIORNALI_C = (
    "C) Soggetti iscritti al Registro delle Imprese presso la Cciaa "
    "(risultanti impresa attiva), oppure titolari di una partita Iva attiva, "
    "che esercitano attività di distribuzione con codice Ateco 46.18.3 “ "
    "Attività di intermediari del commercio all’ingrosso di libri, giornali, "
    "riviste e articoli di cancelleria ” il cui codice Ateco 2007-2022 fosse "
    "82.99.20 “Agenzie di distribuzione di libri, giornali e riviste”."
)

CORREZIONI_24_11 = [
    # Proroga al 24/11/2026: riga 95 del testo salvato ("In evidenza"), con
    # la riga 114 per il decreto 25369 e la riga 96 per la proroga di prima
    Correzione(
        tabella="bandi",
        riga={"id": ALTA_FORMAZIONE},
        attesi={
            "scadenza": "2026-11-19",
            "scadenza_nota": NOTA_ALTA_FORMAZIONE,
            "riferimento_atto": ATTO_ALTA_FORMAZIONE,
            "verificato_il": "2026-11-11",
        },
        corretti={
            "scadenza": "2026-11-24",
            "scadenza_nota": (
                "Ulteriore proroga fino al 24 novembre 2026, confermata con "
                "decreto dirigenziale 25474 del 19 novembre 2026, che corregge "
                "un errore materiale sulla data nel decreto 25369 del 18 "
                "novembre 2026; proroga precedente fino al 19 novembre 2026 con "
                "decreto dirigenziale 23693 del 26 ottobre 2026; prima proroga "
                "al 2 novembre 2026 con decreto del 22 settembre; scadenza "
                "iniziale 15 ottobre 2026"
            ),
            "riferimento_atto": (
                "Decreto dirigenziale 19633 del 25 agosto 2026, modificato con "
                "decreti 21092 del 27 settembre 2026, 21570 del 28 settembre "
                "2026, 23693 del 26 ottobre 2026, 25369 del 18 novembre 2026 e "
                "25474 del 19 novembre 2026"
            ),
            "verificato_il": "2026-11-23",
        },
        frasi=(
            (
                "confermata l'ulteriore proroga fino al 24 novembre 2026 per "
                "presentare domanda, con decreto dirigenziale 25474 del 19 "
                "novembre 2026"
            ),
            (
                "che corregge un errore materiale sulla data nel testo del "
                "decreto 25369 del 18 novembre di ulteriore proroga"
            ),
            (
                "entro il 24 novembre 2026 per ulteriore proroga con decreto "
                "25369 del 18 novembre 2026"
            ),
            (
                "Ulteriore proroga fino al 19 novembre 2026 con decreto "
                "dirigenziale 23693 del 26 ottobre 2026"
            ),
        ),
        testo=MANUALI_24_11 / f"{ALTA_FORMAZIONE}.txt",
    ),
    # Sospensione dall'8/07/2026 per l'articolo 5 lettere a-e, aperto solo
    # per la lettera f: in testa alla nota sulla scadenza e ai beneficiari
    Correzione(
        tabella="bandi",
        riga={"id": INCENTIVI},
        attesi={
            "scadenza_nota": NOTA_INCENTIVI,
            "beneficiari": BENEFICIARI_INCENTIVI,
            "riferimento_atto": ATTO_INCENTIVI,
            "verificato_il": "2026-11-13",
        },
        corretti={
            "scadenza_nota": f"{SOSPENSIONE_INCENTIVI} {NOTA_INCENTIVI}",
            "beneficiari": f"{APERTO_SOLO_LETTERA_F} {BENEFICIARI_INCENTIVI}",
            "riferimento_atto": (
                f"{ATTO_INCENTIVI}; sospeso per l'articolo 5 lettere a-e con "
                "decreto n. 742/2026 di Arti, pubblicato sul Burt l'8 luglio 2026"
            ),
            "verificato_il": "2026-11-23",
        },
        frasi=FRASI_SOSPENSIONE_INCENTIVI,
        testo=MANUALI_24_11 / f"{INCENTIVI}.txt",
    ),
    # Il testo dei beneficiari senza puntini, con le tre categorie della
    # pagina (righe 97-102 del testo salvato)
    Correzione(
        tabella="bandi",
        riga={"id": GIORNALI},
        attesi={"beneficiari": BENEFICIARI_GIORNALI},
        corretti={
            "beneficiari": (
                "Possono presentare domanda i soggetti iscritti al Registro "
                "delle Imprese presso la Cciaa (risultanti impresa attiva), "
                "oppure titolari di una partita Iva attiva: A) esercenti punti "
                "vendita con sede nei territori classificati come Toscana "
                "diffusa; B) esercenti punti vendita esclusivi per la rivendita "
                "di giornali e riviste (edicole), codice Ateco primario "
                "47.62.10, con sede nel resto del territorio regionale; C) "
                "distributori, con codice Ateco 46.18.3 (codice Ateco "
                "2007-2022 82.99.20, agenzie di distribuzione di libri, "
                "giornali e riviste)"
            ),
        },
        frasi=(
            "Possono presentare domanda:",
            FRASE_GIORNALI_A,
            FRASE_GIORNALI_B,
            FRASE_GIORNALI_C,
        ),
        testo=MANUALI_24_11 / f"{GIORNALI}.txt",
    ),
    # La categoria C, scartata dall'estrazione del 24/11: soggetto, tipo e
    # condizioni come li aveva proposti il modello, piu' il massimale della
    # riga 115 del testo salvato; frase della pagina
    Aggiunta(
        tabella="beneficiari_bando",
        riga={
            "id_bando": GIORNALI,
            "tipo": "altra_impresa",
            "soggetto": (
                "Soggetti iscritti al Registro delle Imprese presso la Cciaa "
                "(risultanti impresa attiva), oppure titolari di una partita Iva "
                "attiva, che esercitano attività di distribuzione"
            ),
            "condizioni": (
                "che esercitano attività di distribuzione con codice Ateco "
                "46.18.3, il cui codice Ateco 2007-2022 fosse 82.99.20 Agenzie di "
                "distribuzione di libri, giornali e riviste; fino a 180 euro per "
                "Comune servito"
            ),
            "frase": FRASE_GIORNALI_C,
            "confidenza": "alta",
            "origine": "manuale",
        },
        frasi=(
            (
                "Per i distributori come specificato al paragrafo 2.1, lettera "
                "C), fino a 180 euro per Comune servito."
            ),
        ),
        testo=MANUALI_24_11 / f"{GIORNALI}.txt",
    ),
    # Il periodo di sospensione dall'8/07/2026 come dato strutturato: lo
    # stato del bando lo dice prima delle finestre. scadenza_nota e
    # beneficiari restano come sono (la pulizia e' un passo a parte).
    # verificato_il: la data in cui la pagina e' stata salvata, come nella
    # correzione della riga di bandi qui sopra.
    Aggiunta(
        tabella="sospensioni_bando",
        riga={
            "id_bando": INCENTIVI,
            "numero": 1,
            "ambito": "in_parte",
            "sospeso_dal": "2026-07-08",
            "sospesi": SOSPESI_INCENTIVI,
            "resta_aperto": RESTA_APERTO_INCENTIVI,
            "atto": "decreto n. 742/2026 di Arti",
            "frase": FRASE_DECORRENZA_INCENTIVI,
            "verificato_il": "2026-11-23",
            "origine": "manuale",
        },
        frasi=(
            *FRASI_SOSPENSIONE_INCENTIVI,
            *CATEGORIE_SOSPESE_INCENTIVI,
            CATEGORIA_APERTA_INCENTIVI,
            "articolo 5 lettera f",
            "decreto n. 742/2026 di Arti",
        ),
        testo=MANUALI_24_11 / f"{INCENTIVI}.txt",
    ),
]

CORREZIONI = [*CORREZIONI_19_11, *CORREZIONI_24_11]


def _controlla(correzione: Correzione) -> None:
    """La correzione tocca solo righe e campi ammessi."""
    chiave, correggibili = CAMPI[correzione.tabella]
    assert tuple(correzione.riga) == chiave, correzione.riga
    assert set(correzione.attesi) == set(correzione.corretti), correzione
    assert set(correzione.corretti) <= set(correggibili), correzione.corretti


def _controlla_aggiunta(aggiunta: Aggiunta) -> None:
    """La riga nuova ha la chiave intera, solo campi ammessi e origine
    'manuale'."""
    chiave, ammessi = AGGIUNGIBILI[aggiunta.tabella]
    assert set(chiave) <= set(aggiunta.riga), aggiunta.riga
    assert set(aggiunta.riga) <= set(ammessi), aggiunta.riga
    assert aggiunta.riga.get("origine") == "manuale", aggiunta.riga


def frasi_di_prova(modifica: Correzione | Aggiunta) -> tuple:
    """Le frasi da cercare nel testo.

    Per un'aggiunta anche la sua frase (e la frase della riapertura, se
    c'e'); per una correzione anche i campi di FRASI_NEI_CAMPI.
    """
    if isinstance(modifica, Aggiunta):
        proprie = (modifica.riga.get("frase"),)
        if modifica.riga.get("riapertura_frase") is not None:
            proprie += (modifica.riga["riapertura_frase"],)
        return (*proprie, *modifica.frasi)
    campi = FRASI_NEI_CAMPI.get(modifica.tabella, ())
    return (
        *(modifica.corretti[c] for c in campi if c in modifica.corretti),
        *modifica.frasi,
    )


def frase_vuota(modifica: Correzione | Aggiunta) -> bool:
    """Una delle frasi di prova e' vuota o mancante: la modifica si rifiuta."""
    return any(not (f or "").strip() for f in frasi_di_prova(modifica))


def correggi(
    conn: sqlite3.Connection, correzione: Correzione, testo: str | None, prova: bool
) -> str:
    """Verifica e applica una correzione; dice cosa e' successo.

    testo: il testo salvato in cui cercare le frasi; None se il file manca.
    """
    _controlla(correzione)
    campi = list(correzione.corretti)
    dove = " AND ".join(f"{c} = ?" for c in correzione.riga)
    righe = conn.execute(
        f"SELECT {', '.join(campi)} FROM {correzione.tabella} WHERE {dove}",
        tuple(correzione.riga.values()),
    ).fetchall()
    if not righe:
        return "NON TROVATO"
    if len(righe) > 1:
        return f"SALTATO: {len(righe)} righe corrispondono, ne serve una"

    attuale = dict(zip(campi, righe[0], strict=True))
    if attuale == correzione.corretti:
        return "gia' corretto"
    diversi = {c: v for c, v in attuale.items() if v != correzione.attesi[c]}
    if diversi:
        return f"SALTATO: in archivio {diversi}, attesi {correzione.attesi}"

    if frase_vuota(correzione):
        return "SALTATO: una frase di prova e' vuota"
    if testo is None:
        return f"SALTATO: testo non trovato ({correzione.testo})"
    mancanti = [f for f in frasi_di_prova(correzione) if not frase_nel_testo(f, testo)]
    if mancanti:
        return f"SALTATO: frasi non trovate nel testo: {mancanti}"

    cambi = ", ".join(
        f"{c}: «{attuale[c]}» -> «{correzione.corretti[c]}»" for c in campi
    )
    if prova:
        return f"da correggere: {cambi}"
    imposta = ", ".join(f"{c} = ?" for c in campi)
    conn.execute(
        f"UPDATE {correzione.tabella} SET {imposta} WHERE {dove}",
        (*correzione.corretti.values(), *correzione.riga.values()),
    )
    return f"corretto: {cambi}"


def aggiungi(
    conn: sqlite3.Connection, aggiunta: Aggiunta, testo: str | None, prova: bool
) -> str:
    """Verifica e inserisce una riga nuova; dice cosa e' successo.

    testo: il testo salvato in cui cercare le frasi; None se il file manca.
    """
    _controlla_aggiunta(aggiunta)
    riga = aggiunta.riga
    if not conn.execute(
        "SELECT 1 FROM bandi WHERE id = ?", (riga["id_bando"],)
    ).fetchone():
        return "NON TROVATO: il bando non e' in archivio"

    chiave = AGGIUNGIBILI[aggiunta.tabella][0]
    campi = list(riga)
    esistente = conn.execute(
        f"SELECT {', '.join(campi)} FROM {aggiunta.tabella} "
        f"WHERE {' AND '.join(f'{c} = ?' for c in chiave)}",
        tuple(riga[c] for c in chiave),
    ).fetchone()
    if esistente is not None:
        if dict(zip(campi, esistente, strict=True)) == riga:
            return "gia' aggiunta"
        return "SALTATO: c'e' gia' una riga con la stessa chiave, diversa"

    if frase_vuota(aggiunta):
        return "SALTATO: una frase di prova e' vuota"
    if testo is None:
        return f"SALTATO: testo non trovato ({aggiunta.testo})"
    mancanti = [f for f in frasi_di_prova(aggiunta) if not frase_nel_testo(f, testo)]
    if mancanti:
        return f"SALTATO: frasi non trovate nel testo: {mancanti}"

    valori = ", ".join(f"{c}: «{v}»" for c, v in riga.items())
    if prova:
        return f"da aggiungere: {valori}"
    conn.execute(
        f"INSERT INTO {aggiunta.tabella} ({', '.join(campi)}) "
        f"VALUES ({', '.join('?' for _ in campi)})",
        tuple(riga.values()),
    )
    return f"aggiunta: {valori}"


def leggi_testo(percorso: Path) -> str | None:
    """Il testo salvato, o None se il file manca."""
    return percorso.read_text(encoding="utf-8") if percorso.exists() else None


def _dove(modifica: Correzione | Aggiunta) -> str:
    """La riga toccata, per i messaggi: per un'aggiunta senza la frase."""
    campi = (
        {c: v for c, v in modifica.riga.items() if c in ("id_bando", "tipo")}
        if isinstance(modifica, Aggiunta)
        else modifica.riga
    )
    return ", ".join(f"{c}={v}" for c, v in campi.items())


def applica(
    conn: sqlite3.Connection, correzioni: list[Correzione | Aggiunta], prova: bool
) -> tuple[list[str], set[str]]:
    """Le correzioni e le aggiunte, in ordine: i messaggi e le tabelle
    modificate."""
    messaggi, toccate = [], set()
    for modifica in correzioni:
        testo = leggi_testo(modifica.testo)
        if isinstance(modifica, Aggiunta):
            esito = aggiungi(conn, modifica, testo, prova)
        else:
            esito = correggi(conn, modifica, testo, prova)
        messaggi.append(f"{modifica.tabella} [{_dove(modifica)}]: {esito}")
        if esito.startswith(("corretto", "aggiunta")):
            toccate.add(modifica.tabella)
    return messaggi, toccate


def dettaglio_frasi(modifica: Correzione | Aggiunta) -> list[str]:
    """Le frasi di prova, una per riga, con l'esito della ricerca nel testo."""
    testo = leggi_testo(modifica.testo)
    if testo is None:
        return [f"    testo non trovato: {modifica.testo}"]
    return [
        f"    trovata: {'si' if frase_nel_testo(f or '', testo) else 'NO'}: «{f}»"
        for f in frasi_di_prova(modifica)
    ]


def main(correzioni: list[Correzione | Aggiunta] | None = None) -> None:
    prova = "--prova" in sys.argv
    correzioni = correzioni or CORREZIONI
    conn = connetti()
    try:
        messaggi, toccate = applica(conn, correzioni, prova)
        conn.commit()
    finally:
        conn.close()

    for modifica, messaggio in zip(correzioni, messaggi, strict=True):
        print(f"  {messaggio}")
        if prova:
            print("\n".join(dettaglio_frasi(modifica)))
    if prova:
        print("\nProva: nulla modificato.")
        return
    if toccate:
        aggiorna_csv(*sorted(toccate))


if __name__ == "__main__":
    main()
