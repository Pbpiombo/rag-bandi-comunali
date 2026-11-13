"""Completa i bandi della Regione che restano al posto dei doppioni.

Uso:
    python -m scripts.manutenzione.correggi_doppioni_tenuti --prova   verifica soltanto
    python -m scripts.manutenzione.correggi_doppioni_tenuti           corregge

Script una tantum (doppioni tra Incentivi Italia e la Regione, decisioni
del 13 novembre 2026, passo A). Prima di togliere un doppione, la versione
tenuta deve avere tutto quello che la tolta aveva di vero. Il confronto
campo per campo ha trovato tre lacune, verificate sulla pagina della
Regione:
- professionisti tra i beneficiari, ma senza il tipo
  professionista_autonomo (tre bandi BEI);
- i due massimali dei minibond, 20.000 euro per la consulenza e 30 mila
  per le commissioni di garanzia, che il bando tenuto non riporta. Il
  contributo massimo resta vuoto: sono due massimali distinti, e la
  somma sarebbe un valore calcolato. Vanno tra le spese, ciascuno con la
  sua frase.
Una correzione trovata sulle stesse pagine, decisa il 13 novembre 2026:
nel bando EU-Blending i professionisti erano classificati come
cittadini_famiglie (soggetto «professionisti»): classificazione
sbagliata, la riga si toglie (il tipo giusto e' aggiunto sopra). Il
costo massimo del bando turismo, che sembrava mancare, era gia' in
archivio (5.000.000 euro): nulla da scrivere.

Gli importi del catalogo Incentivi Italia non si riportano: si scrive solo
cio' che dice la pagina della Regione. Ogni riga ha la sua frase; la
pagina si riscarica e ogni frase si cerca con frase_nel_testo. Si
inserisce solo se tutte le frasi si trovano; una riga gia' presente non
si tocca. Prima di scrivere, copia del database in dati-grezzi/backup.
Alla fine riversa beneficiari_bando e interventi_bando nei CSV.
Rilanciarlo non cambia nulla.

Le righe di beneficiari hanno origine 'manuale'; quelle degli interventi
non hanno un'origine, e una nuova estrazione del bando le sostituirebbe:
vanno ricontrollate alla prossima scansione, come le correzioni di
correggi_atti.
"""

import sys
from http.client import HTTPException

from src.database.schema import aggiorna_csv, connetti
from src.estrazione.beneficiari import frase_nel_testo
from src.estrazione.doppioni import copia_di_sicurezza
from src.estrazione.pagina import prendi

TURISMO = "settore-turismo-sovvenzioni-per-abbattere-gli-interes-3b9deb"
EU_BLENDING = "bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-8cd3ac"
FINO_50MILA = "bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-7057d9"
MINIBOND = "contributi-a-copertura-di-spese-di-emissione-obbligaz-d5ca7a"

CONDIZIONI_EU_BLENDING = (
    "operare nei settori ammissibili ai sensi della delibera di giunta "
    "regionale 704/2025 e del Fondo di garanzia per le Pmi, purché "
    "l'attività non rientri nei settori esclusi"
)

# Righe di beneficiari_bando: id del bando -> (tipo, soggetto, condizioni,
# frase). La frase e' quella della pagina; si cerca prima di inserire.
BENEFICIARI = [
    (
        TURISMO,
        "professionista_autonomo",
        "professionisti",
        (
            "operanti nel settore turismo, con codice Ateco primario I 55.1 "
            "(Alberghi e strutture simili) o I 55.3 (Aree di campeggio e aree "
            "attrezzate per roulotte)"
        ),
        "Sono soggetti destinatari Mpmi e professionisti.",
    ),
    (
        EU_BLENDING,
        "professionista_autonomo",
        "professionisti",
        CONDIZIONI_EU_BLENDING,
        (
            "Micro e piccole medie imprese (Mpmi) e professionisti, come definite "
            "dall’allegato 1 del Regolamento UE n. 651/2014"
        ),
    ),
    (
        FINO_50MILA,
        "professionista_autonomo",
        "Linea A1: liberi professionisti",
        (
            "giovanili, femminili o destinatari di ammortizzatori sociali, con "
            "inizio attività nei 36 mesi precedenti la data di presentazione "
            "della domanda (solo linea A1)"
        ),
        (
            "Linea A1: Micro e piccole Imprese, così come definite dall’allegato 1 "
            "del Regolamento UE 651/2014 e successive modifiche e integrazioni , "
            "giovanili, femminili o destinatari di ammortizzatori sociali, "
            "compresi i liberi professionisti, la cui costituzione è avvenuta nel "
            "corso dei 36 mesi precedenti la data di presentazione della domanda"
        ),
    ),
]

# Righe di interventi_bando: (id del bando, numero, descrizione, frase).
# La frase dei 30 mila euro e' copiata com'e' sulla pagina, refuso compreso
# ("i mporto"): altrimenti non si ritroverebbe.
SPESE = [
    (
        MINIBOND,
        3,
        (
            "Spese di consulenza per l'emissione: contributo del 50%, per un "
            "importo massimo di 20.000 euro"
        ),
        (
            "contributo diretto alle spese di consulenza sostenute per l’emissione "
            "pari al 50%, per un importo massimo di euro 20.000,00"
        ),
    ),
    (
        MINIBOND,
        4,
        (
            "Commissioni di garanzia: contributo a completa copertura, per un "
            "importo massimo di 30 mila euro"
        ),
        (
            "contributo in c/commissioni di garanzia a completa copertura delle "
            "commissioni di garanzia in quanto è prevista la concessione di una "
            "garanzia del titolo obbligazionario/di debito attraverso la "
            "riassicurazione alla Sezione speciale – Regione Toscana del Fondo di "
            "garanzia , di cui alla legge 662/1996, ai sensi dell’art. 17 del Reg. "
            "(UE) 651/2014 e per un i mporto massimo di 30 mila euro"
        ),
    ),
]


# Righe di beneficiari_bando da togliere: (id del bando, tipo, soggetto,
# motivo). Si toglie solo la riga con quel tipo e quel soggetto.
DA_TOGLIERE = [
    (
        EU_BLENDING,
        "cittadini_famiglie",
        "professionisti",
        (
            "professionisti classificati come cittadini e famiglie: il tipo "
            "giusto e' professionista_autonomo"
        ),
    ),
]


def pagina(conn, id_bando: str, pagine: dict) -> str | None:
    """Il testo della pagina del bando, scaricato una volta sola."""
    if id_bando not in pagine:
        riga = conn.execute(
            "SELECT url FROM bandi WHERE id = ?", (id_bando,)
        ).fetchone()
        if riga is None:
            pagine[id_bando] = None
        else:
            try:
                pagine[id_bando] = prendi(riga["url"])
            except (OSError, HTTPException):
                pagine[id_bando] = None
    return pagine[id_bando]


def da_fare(conn, pagine: dict) -> list[tuple[str, str, tuple]]:
    """Le correzioni ancora da applicare, con l'esito di ciascuna."""
    esiti = []
    for id_bando, tipo, soggetto, condizioni, frase in BENEFICIARI:
        presente = conn.execute(
            "SELECT 1 FROM beneficiari_bando WHERE id_bando = ? AND tipo = ?",
            (id_bando, tipo),
        ).fetchone()
        voce = ("beneficiari_bando", (id_bando, tipo, soggetto, condizioni, frase))
        if presente:
            esiti.append((f"{id_bando}: {tipo} gia' presente", "", voce))
            continue
        testo = pagina(conn, id_bando, pagine)
        if testo is None:
            esiti.append((f"{id_bando}: SALTATO, pagina non scaricata", "", voce))
        elif not frase_nel_testo(frase, testo):
            esiti.append((f"{id_bando}: SALTATO, frase non trovata", "", voce))
        else:
            esiti.append((f"{id_bando}: aggiungere {tipo}", "inserire", voce))

    for id_bando, numero, descrizione, frase in SPESE:
        presente = conn.execute(
            "SELECT descrizione FROM interventi_bando WHERE id_bando = ? AND numero = ?",
            (id_bando, numero),
        ).fetchone()
        voce = ("interventi_bando", (id_bando, numero, descrizione, frase))
        if presente:
            stato = "gia' presente" if presente[0] == descrizione else "OCCUPATO"
            esiti.append((f"{id_bando}: spesa {numero} {stato}", "", voce))
            continue
        testo = pagina(conn, id_bando, pagine)
        if testo is None:
            esiti.append((f"{id_bando}: SALTATO, pagina non scaricata", "", voce))
        elif not frase_nel_testo(frase, testo):
            esiti.append((f"{id_bando}: SALTATO, frase non trovata", "", voce))
        else:
            esiti.append(
                (f"{id_bando}: aggiungere la spesa {numero}", "inserire", voce)
            )

    for id_bando, tipo, soggetto, motivo in DA_TOGLIERE:
        presente = conn.execute(
            "SELECT 1 FROM beneficiari_bando WHERE id_bando = ? AND tipo = ? "
            "AND soggetto = ?",
            (id_bando, tipo, soggetto),
        ).fetchone()
        voce = ("togli_beneficiario", (id_bando, tipo, soggetto))
        if presente:
            esiti.append((f"{id_bando}: togliere {tipo} ({motivo})", "togliere", voce))
        else:
            esiti.append((f"{id_bando}: {tipo} gia' tolto", "", voce))

    return esiti


def applica(conn, tabella: str, valori: tuple) -> None:
    """Applica una correzione verificata."""
    if tabella == "beneficiari_bando":
        conn.execute(
            "INSERT INTO beneficiari_bando (id_bando, tipo, soggetto, condizioni, "
            "frase, confidenza, origine) VALUES (?, ?, ?, ?, ?, 'alta', 'manuale')",
            valori,
        )
    elif tabella == "interventi_bando":
        conn.execute(
            "INSERT INTO interventi_bando (id_bando, numero, genere, descrizione, "
            "frase) VALUES (?, ?, 'spesa', ?, ?)",
            valori,
        )
    else:
        conn.execute(
            "DELETE FROM beneficiari_bando WHERE id_bando = ? AND tipo = ? "
            "AND soggetto = ?",
            valori,
        )


def main() -> None:
    prova = "--prova" in sys.argv
    conn = connetti()
    try:
        esiti = da_fare(conn, {})
        for messaggio, _, _ in esiti:
            print(f"  {messaggio}")
        da_applicare = [voce for _, azione, voce in esiti if azione]
        if prova or not da_applicare:
            print("\nProva: nulla modificato." if prova else "\nNulla da fare.")
            return
        copia = copia_di_sicurezza(conn, "correggi-doppioni-tenuti")
        print(f"\nBackup: {copia}")
        for tabella, valori in da_applicare:
            applica(conn, tabella, valori)
        conn.commit()
        print(f"Applicate {len(da_applicare)} correzioni.")
    finally:
        conn.close()
    aggiorna_csv("beneficiari_bando", "interventi_bando")


if __name__ == "__main__":
    main()
