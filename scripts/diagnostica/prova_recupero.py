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

Ogni domanda si misura due volte: con il motore nudo (prima di P2) e con
il motore avvolto in `RecuperoPerDocumento` (dopo P2, come lo usa la
catena). Il criterio di P2 (`docs/prova-verificatore.md`): tutti i
frammenti attesi nei primi 10 su entrambi i motori, e nessuno di quelli
che c'erano prima ne esce. Ogni spostamento è riportato; quelli di più di
3 posizioni sono segnati a parte.

Uso: python -m scripts.diagnostica.prova_recupero
"""

import re
from dataclasses import dataclass

from langchain_core.documents import Document

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


def misura(motori: dict) -> list[dict]:
    """Una riga per (domanda, frammento atteso, motore), prima e dopo P2.

    Prima: il motore nudo. Dopo: lo stesso motore avvolto in
    RecuperoPerDocumento, come lo usa la catena.
    """
    righe = []
    for indice, domanda in enumerate(PROVA, start=1):
        for nome, (base, avvolto) in motori.items():
            prima = [doc for doc, _, _ in base.cerca(domanda.testo, k=K)]
            dopo = [doc for doc, _, _ in avvolto.cerca(domanda.testo, k=K)]
            nominati = documenti_nominati(domanda.testo, avvolto.titoli)
            for atteso in domanda.attesi:
                p_prima = posizione(prima, atteso)
                p_dopo = posizione(dopo, atteso)
                righe.append(
                    {
                        "indice": indice,
                        "motore": nome,
                        "fonte": atteso.fonte,
                        "prima": p_prima,
                        "dopo": p_dopo,
                        "esito_prima": esito_di(
                            p_prima, nome, base, domanda.testo, atteso
                        ),
                        "esito_dopo": f"{p_dopo}ª" if p_dopo else "assente",
                        "spostamento": spostamento(p_prima, p_dopo),
                        "nominati": sorted(f[:20] for f in nominati),
                    }
                )
    return righe


def main() -> None:
    motori = {}
    for nome, base in (("postgres", RecuperoPostgres()), ("chroma", RecuperoIbrido())):
        motori[nome] = (base, RecuperoPerDocumento(base))
    righe = misura(motori)

    for indice, domanda in enumerate(PROVA, start=1):
        nota = f"  [{domanda.nota}]" if domanda.nota else ""
        print(f"\n{indice}. {domanda.testo}{nota}")
        if domanda.aperto:
            print(f"   CASO APERTO: {domanda.aperto}")
        proprie = [r for r in righe if r["indice"] == indice]
        print(f"   documenti nominati: {proprie[0]['nominati'] or 'nessuno'}")
        for r in proprie:
            print(
                f"   {r['motore']:8}  {r['fonte']:20}  prima {r['esito_prima']:38}"
                f"  dopo {r['esito_dopo']:8}  {r['spostamento']}"
            )

    for nome in motori:
        proprie = [r for r in righe if r["motore"] == nome]
        prima = sum(1 for r in proprie if r["prima"])
        dopo = sum(1 for r in proprie if r["dopo"])
        print(
            f"\n{nome}: nei primi {K} {prima} frammenti attesi su {len(proprie)}"
            f" prima, {dopo} dopo"
        )

    da_guardare = [r for r in righe if "!!" in r["spostamento"]]
    print(f"\nDa guardare (uscite o più di 3 posizioni): {len(da_guardare)}")
    for r in da_guardare:
        print(f"   {r['indice']}. {r['motore']} {r['fonte']}: {r['spostamento']}")

    # Regola di chiusura di P2: nessuna domanda che funzionava esce dai
    # primi 10, su nessuno dei due motori.
    uscite = [r for r in righe if r["prima"] and not r["dopo"]]
    aperti = [i for i, d in enumerate(PROVA, start=1) if d.aperto]
    giudizio = "RISPETTATA" if not uscite else f"NON RISPETTATA ({len(uscite)} uscite)"
    print(f"\nRegola di chiusura di P2: {giudizio}. Casi aperti: {aperti}")


if __name__ == "__main__":
    main()
