"""Insieme di prova del recupero documentale, senza modello.

Per ogni domanda indica il documento e la frase che devono comparire in
almeno uno dei primi 10 frammenti, e misura la posizione su Postgres e su
Chroma con `cerca(domanda, k=10)`, come fa l'app. Se il frammento atteso
non c'è, riporta la sua posizione nella lista densa e in quella lessicale
(fino a 100).

Un frammento conta come trovato se appartiene al documento atteso e ne
contiene la frase, a meno di spazi e a capo. Il confronto è sul testo e
non sull'identificativo, perché Chroma e Postgres numerano i chunk in modo
diverso. Una frase vuota vale per qualunque frammento del documento: serve
per i dati che arrivano dall'intestazione costruita con i metadati, come il
numero dell'atto.

Ogni domanda si misura in più forme (apostrofo dritto e tipografico, con e
senza "?" finale) e conta la posizione peggiore: il 12 novembre 2026 la
stessa domanda copiata con l'apostrofo tipografico ha perso nell'app un
frammento che la prova trovava.

Ogni domanda si misura con tre percorsi: il motore nudo con la domanda
come arriva (prima), il motore nudo con la domanda normalizzata da
`recupera` della catena (senza P2), e il motore avvolto in
`RecuperoPerDocumento` attraverso `recupera` (P2: il percorso dell'app).
Le domande sono in due gruppi: le 15 di prova e le 5 di controllo
(`python -m scripts.diagnostica.prova_recupero controllo` misura solo
queste). La regola di chiusura
(`docs/prova-verificatore.md`, P2): nessun frammento atteso che era nei
primi 10 prima, nella forma peggiore, ne esce, su nessuno dei due motori.
Ogni spostamento è riportato; quelli di più di 3 posizioni sono segnati a
parte.

Uso: python -m scripts.diagnostica.prova_recupero
"""

import re
import sys
from dataclasses import dataclass

from langchain_core.documents import Document

from src.chains.rag import recupera
from src.pgstore import RecuperoPostgres
from src.recupero_documenti import RecuperoPerDocumento, documenti_nominati
from src.retrieval import RecuperoIbrido

K = 10
PROFONDITA = 100

AVVISO_CAPOFILA = "Decreto n.9550"
AVVISO_MERCATI = "Decreto_n.13287"
LUDOTECHE = "PROGETTO_DEF_SNAI_C3"
LINEE_GUIDA_SNAI = "4_evoluzione"
STUDIO_CENSIS = "2_contributo-censis"


@dataclass(frozen=True)
class Atteso:
    """Frammento atteso: inizio del nome del file sorgente e frase contenuta."""

    fonte: str
    frase: str


@dataclass(frozen=True)
class Domanda:
    testo: str
    attesi: tuple[Atteso, ...]
    nota: str
    # Motivo per cui la domanda resta fuori dai primi 10 anche dopo P2.
    # Un caso aperto non conta per la regola di chiusura, ma si misura.
    aperto: str = ""


PROVA = [
    Domanda(
        "Qual è il costo massimo giornaliero per un incarico professionale?",
        (Atteso(AVVISO_CAPOFILA, "322,00"),),
        "domanda d'esempio dell'app",
    ),
    Domanda(
        "Qual è il costo massimo giornaliero per un incarico professionale "
        "nell'avviso per il rafforzamento amministrativo dei capofila delle "
        "aree interne?",
        (Atteso(AVVISO_CAPOFILA, "322,00"),),
        "domanda 4 della prova del verificatore: nomina l'avviso",
    ),
    Domanda(
        "Quale percentuale di costi indiretti è ammessa nello stesso avviso, "
        "e in base a quale norma?",
        (Atteso(AVVISO_CAPOFILA, "pari al 7%"),),
        "domanda 5 della prova del verificatore",
    ),
    Domanda(
        "Entro quando e a che ora va presentata la domanda per l'avviso sul "
        "rafforzamento amministrativo?",
        (Atteso(AVVISO_CAPOFILA, "ore 12:00 del trentesimo giorno"),),
        "domanda 6 della prova del verificatore",
    ),
    Domanda(
        "Entro quando va presentata la relazione annuale?",
        (Atteso(AVVISO_CAPOFILA, "31 marzo di ogni anno"),),
        "domanda d'esempio dell'app",
    ),
    Domanda(
        "Con quale decreto è stato approvato l'avviso per i mercati rionali, "
        "e quali contributi prevede?",
        (Atteso(AVVISO_MERCATI, "non più dell’80%"),),
        "domanda 7 della prova del verificatore: nomina l'avviso",
        aperto=(
            "parole diverse tra domanda e testo: si chiedono i 'contributi', "
            "il frammento dice 'il contributo concedibile ... non più "
            "dell'80%'. Non è tra i primi 30 nemmeno nella ricerca ristretta "
            "all'avviso, con la domanda intera o ripulita"
        ),
    ),
    Domanda(
        "Nell'avviso per i mercati rionali, qual è il costo minimo e massimo "
        "di un progetto ammissibile?",
        (Atteso(AVVISO_MERCATI, "non inferiore a 25.000,00"),),
        "nomina l'avviso",
    ),
    Domanda(
        "Qual è il costo totale del progetto Ludoteche di montagna per "
        "l'Appennino Pistoiese?",
        (Atteso(LUDOTECHE, "19.570,00"),),
        "nomina il progetto",
    ),
    Domanda(
        "Quando il requisito associativo è assolto per i comuni già associati "
        "in un'Unione di Comuni montani?",
        (Atteso(LINEE_GUIDA_SNAI, "il requisito associativo risulta assolto se"),),
        "",
    ),
    Domanda(
        "Quanti comuni italiani sono classificati come ultraperiferici?",
        (Atteso(STUDIO_CENSIS, "382 Comuni"),),
        "",
    ),
    Domanda(
        "Chi può presentare domanda nell'avviso per il rafforzamento "
        "amministrativo e chi nell'avviso per i mercati rionali?",
        (
            Atteso(AVVISO_CAPOFILA, "I soggetti beneficiari del sostegno"),
            Atteso(AVVISO_MERCATI, "2.1 Beneficiari Possono presentare domanda"),
        ),
        "nomina due avvisi",
        aperto=(
            "due domande in una: tolti i nomi degli avvisi resta 'chi può "
            "presentare domanda ... e chi', troppo generico. Nelle ricerche "
            "ristrette i frammenti sono tra il 10º e il 26º posto"
        ),
    ),
    Domanda(
        "Con quale decreto è stato approvato l'avviso per il rafforzamento "
        "amministrativo?",
        (Atteso(AVVISO_CAPOFILA, ""),),
        "nomina l'avviso; l'atto è nell'intestazione di ogni frammento",
    ),
    Domanda(
        "Quanto spetta a ciascuna Area interna nell'avviso per il "
        "rafforzamento amministrativo dei capofila?",
        (Atteso(AVVISO_CAPOFILA, "244.475,00"),),
        "nomina l'avviso; risposta in una pagina introduttiva (pag. 5)",
    ),
    Domanda(
        "Quanti comuni sono compresi nelle aree interne della strategia 2021-2027?",
        (Atteso(STUDIO_CENSIS, "1.904 comuni"),),
        "parole dei titoli senza nominare un documento",
    ),
    Domanda(
        "L'avviso per il rafforzamento amministrativo chiede la relazione sul "
        "processo di associazionismo: come deve dimostrare l'Area "
        "l'effettività della gestione associata?",
        (Atteso(LINEE_GUIDA_SNAI, "tenuta a dimostrare l’effettività"),),
        "nomina un avviso, risposta in un altro documento",
    ),
]


# Gruppo di controllo, scritto il 12 novembre 2026 dopo tutte le decisioni
# prese sulle 15 domande sopra: domande mai usate prima, con la risposta
# in frammenti diversi. Servono a non scegliere solo in base alle domande
# su cui si è già deciso. Regola per ricollegare P2: nessun frammento
# atteso che è tra i primi 10 senza P2 (domanda normalizzata) ne esce con
# P2, in nessuna forma peggiore e su nessuno dei due motori.
CONTROLLO = [
    Domanda(
        "Nell'avviso per il rafforzamento amministrativo dei capofila, per "
        "quanti anni va conservata la documentazione?",
        (Atteso(AVVISO_CAPOFILA, "periodo non inferiore a 10 anni"),),
        "nomina l'avviso; pag. 17",
    ),
    Domanda(
        "Nell'avviso per i mercati rionali, quale anticipo del contributo si "
        "può chiedere?",
        (Atteso(AVVISO_MERCATI, "anticipo del 40% del contributo"),),
        "nomina l'avviso; pag. 18",
    ),
    Domanda(
        "Entro quanto va presentata la rendicontazione finale nell'avviso per "
        "i mercati rionali?",
        (Atteso(AVVISO_MERCATI, "termine perentorio di 90 giorni"),),
        "nomina l'avviso in fondo alla domanda; pag. 16",
    ),
    Domanda(
        "Quanti interventi conta il gruppo di aree interne chiamato «Povertà "
        "dietro l'angolo»?",
        (Atteso(STUDIO_CENSIS, "874 in totale"),),
        "non nomina documenti; pag. 28",
    ),
    Domanda(
        "Quale sentenza della Corte costituzionale ha giudicato l'obbligo di "
        "gestione associata per i comuni sotto i 5.000 abitanti?",
        (Atteso(LINEE_GUIDA_SNAI, "2019 n. 33"),),
        "non nomina documenti; pag. 8",
    ),
]


def elenco(gruppi: tuple[str, ...] = ("prova", "controllo")) -> list[tuple]:
    """Le domande da misurare: (etichetta, gruppo, domanda)."""
    tutte = [(str(i), "prova", d) for i, d in enumerate(PROVA, start=1)] + [
        (f"C{i}", "controllo", d) for i, d in enumerate(CONTROLLO, start=1)
    ]
    return [voce for voce in tutte if voce[1] in gruppi]


def normalizza(testo: str) -> str:
    return re.sub(r"\s+", " ", testo)


def corrisponde(documento: Document, atteso: Atteso) -> bool:
    fonte = documento.metadata.get("fonte", "")
    return fonte.startswith(atteso.fonte) and normalizza(atteso.frase) in (
        normalizza(documento.page_content)
    )


def posizione(documenti: list[Document], atteso: Atteso) -> int | None:
    """Posizione (da 1) del primo frammento che corrisponde, o None."""
    for numero, documento in enumerate(documenti, start=1):
        if corrisponde(documento, atteso):
            return numero
    return None


def liste_separate(nome: str, recupero, domanda: str) -> tuple[list, list]:
    """Lista densa e lessicale fino a PROFONDITA, per spiegare un'assenza."""
    if nome == "postgres":
        densa = recupero._densa(domanda, PROFONDITA)
    else:
        densa = recupero.store.similarity_search(domanda, k=PROFONDITA)
    return densa, recupero._lessicale(domanda, PROFONDITA)


def descrivi(numero: int | None) -> str:
    return f"{numero}ª" if numero else f"oltre {PROFONDITA}"


def esito_di(numero: int | None, nome: str, recupero, domanda: str, atteso) -> str:
    """Posizione nei primi K o, se assente, nelle liste densa e lessicale."""
    if numero:
        return f"{numero}ª"
    densa, lessicale = liste_separate(nome, recupero, domanda)
    return (
        f"assente (densa {descrivi(posizione(densa, atteso))},"
        f" lessicale {descrivi(posizione(lessicale, atteso))})"
    )


def spostamento(prima: int | None, dopo: int | None) -> str:
    """Descrive il cambio di posizione; '!!' segna i casi da guardare."""
    if prima == dopo:
        return "invariata" if prima else "ancora assente"
    if dopo is None:
        return "!! USCITA dai primi 10"
    if prima is None:
        return "entrata"
    differenza = dopo - prima
    segno = "scesa" if differenza > 0 else "salita"
    avviso = "  !! più di 3 posizioni" if abs(differenza) > 3 else ""
    return f"{segno} di {abs(differenza)}{avviso}"


def forme(testo: str) -> dict[str, str]:
    """La stessa domanda come può arrivare dall'utente.

    Apostrofo dritto o tipografico (una domanda copiata da un documento ha
    il secondo), con o senza punto interrogativo finale. Le forme uguali
    compaiono una volta sola.
    """
    dritto = testo.replace("’", "'")
    tipografico = dritto.replace("'", "’")
    risultato: dict[str, str] = {}
    for nome, base in (("dritto", dritto), ("tipografico", tipografico)):
        senza = base.rstrip("?").rstrip()
        for variante, forma in (
            (f"{nome} con ?", senza + "?"),
            (f"{nome} senza ?", senza),
        ):
            if forma not in risultato.values():
                risultato[variante] = forma
    return risultato


def peggiore(posizioni: list[int | None]) -> int | None:
    """La posizione peggiore; un'assenza è peggio di qualunque posizione."""
    return None if None in posizioni else max(posizioni)


PERCORSI = ("prima", "normalizzata", "P2")


def misura(motori: dict, domande: list[tuple]) -> list[dict]:
    """Una riga per (domanda, frammento atteso, motore), con tre percorsi.

    - prima: il motore nudo, con la domanda come arriva (prima di P2);
    - normalizzata: il motore nudo, con la domanda normalizzata da
      `recupera` della catena;
    - P2: il motore avvolto in RecuperoPerDocumento, attraverso `recupera`,
      come lo usa la catena (src/chains/rag.py).

    Ogni domanda si misura in tutte le sue forme; per ogni percorso conta
    la posizione peggiore tra le forme.
    """
    righe = []
    for indice, gruppo, domanda in domande:
        varianti = forme(domanda.testo)
        for nome, (base, avvolto) in motori.items():
            ricerche = {
                "prima": lambda t, b=base: b.cerca(t, k=K),
                "normalizzata": lambda t, b=base: recupera(b, t, k=K),
                "P2": lambda t, a=avvolto: recupera(a, t, k=K),
            }
            liste = {
                (p, v): [doc for doc, _, _ in ricerche[p](t)]
                for p in PERCORSI
                for v, t in varianti.items()
            }
            nominati = documenti_nominati(domanda.testo, avvolto.titoli)
            for atteso in domanda.attesi:
                per_forma = {
                    p: {v: posizione(liste[(p, v)], atteso) for v in varianti}
                    for p in PERCORSI
                }
                peggio = {p: peggiore(list(per_forma[p].values())) for p in PERCORSI}
                forma_peggiore = next(
                    v for v in varianti if per_forma["prima"][v] == peggio["prima"]
                )
                righe.append(
                    {
                        "indice": indice,
                        "gruppo": gruppo,
                        "motore": nome,
                        "fonte": atteso.fonte,
                        "peggio": peggio,
                        "per_forma": per_forma,
                        "esito_prima": esito_di(
                            peggio["prima"],
                            nome,
                            base,
                            varianti[forma_peggiore],
                            atteso,
                        ),
                        "nominati": sorted(f[:20] for f in nominati),
                    }
                )
    return righe


def breve(numero: int | None) -> str:
    return str(numero) if numero else "-"


def uscite_di(righe: list[dict], percorso: str) -> list[dict]:
    """Righe che nel 'prima' (forma peggiore) erano nei primi K e nel
    percorso indicato (forma peggiore) non ci sono più."""
    return [r for r in righe if r["peggio"]["prima"] and not r["peggio"][percorso]]


def main() -> None:
    motori = {}
    for nome, base in (("postgres", RecuperoPostgres()), ("chroma", RecuperoIbrido())):
        motori[nome] = (base, RecuperoPerDocumento(base))
    # Con l'argomento "controllo" o "prova" si misura un solo gruppo
    gruppi = tuple(sys.argv[1:]) or ("prova", "controllo")
    domande = elenco(gruppi)
    righe = misura(motori, domande)

    for indice, gruppo, domanda in domande:
        nota = f"  [{domanda.nota}]" if domanda.nota else ""
        print(f"\n{indice}. ({gruppo}) {domanda.testo}{nota}")
        if domanda.aperto:
            print(f"   CASO APERTO: {domanda.aperto}")
        proprie = [r for r in righe if r["indice"] == indice]
        print(f"   documenti nominati: {proprie[0]['nominati'] or 'nessuno'}")
        for r in proprie:
            p = r["peggio"]
            print(
                f"   {r['motore']:8}  {r['fonte']:20}  prima {r['esito_prima']:38}"
                f"  normalizzata {breve(p['normalizzata']):3}"
                f"  P2 {breve(p['P2']):3}  {spostamento(p['prima'], p['P2'])}"
            )
            for percorso in PERCORSI:
                dettaglio = ", ".join(
                    f"{v} {breve(n)}" for v, n in r["per_forma"][percorso].items()
                )
                print(f"      {percorso:12} per forma: {dettaglio}")

    for gruppo in gruppi:
        for nome in motori:
            proprie = [
                r for r in righe if r["motore"] == nome and r["gruppo"] == gruppo
            ]
            conti = ", ".join(
                f"{p} {sum(1 for r in proprie if r['peggio'][p])}" for p in PERCORSI
            )
            print(
                f"\n{gruppo}, {nome}: frammenti attesi nei primi {K} su"
                f" {len(proprie)}, forma peggiore: {conti}"
            )

    for percorso in ("normalizzata", "P2"):
        spostate = [
            r
            for r in righe
            if "!!" in spostamento(r["peggio"]["prima"], r["peggio"][percorso])
        ]
        print(f"\nDa guardare per {percorso} (uscite o più di 3 posizioni):")
        for r in spostate:
            print(
                f"   {r['indice']}. {r['motore']} {r['fonte']}: "
                f"{spostamento(r['peggio']['prima'], r['peggio'][percorso])}"
            )

    # Regola di chiusura: nessuna domanda che funzionava prima (forma
    # peggiore) esce dai primi 10, su nessuno dei due motori.
    aperti = [i for i, g, d in domande if d.aperto]
    della_prova = [r for r in righe if r["gruppo"] == "prova"]
    for percorso in ("normalizzata", "P2") if della_prova else ():
        uscite = uscite_di(della_prova, percorso)
        giudizio = (
            "RISPETTATA" if not uscite else f"NON RISPETTATA ({len(uscite)} uscite)"
        )
        print(f"\nRegola di chiusura, {percorso}: {giudizio}. Casi aperti: {aperti}")

    # Gruppo di controllo: P2 non deve far uscire nessun frammento che è
    # tra i primi 10 senza P2 (domanda normalizzata)
    del_controllo = [r for r in righe if r["gruppo"] == "controllo"]
    if del_controllo:
        uscite = [
            r
            for r in del_controllo
            if r["peggio"]["normalizzata"] and not r["peggio"]["P2"]
        ]
        for r in uscite:
            print(f"   uscita con P2: {r['indice']}. {r['motore']} {r['fonte']}")
        giudizio = (
            "RISPETTATA" if not uscite else f"NON RISPETTATA ({len(uscite)} uscite)"
        )
        print(f"\nRegola del gruppo di controllo, P2 contro senza P2: {giudizio}")


if __name__ == "__main__":
    main()
