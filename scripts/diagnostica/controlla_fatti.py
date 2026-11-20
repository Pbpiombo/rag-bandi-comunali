"""Controllo meccanico del foglio dei fatti sui PDF degli avvisi (per il passo 19d).

Uso:
    python -u -m scripts.diagnostica.controlla_fatti --foglio PERCORSO.xlsx
        [--uscita dati-grezzi/prova/fatti_controllo_AAAA-MM-GG.csv]

Ingresso: il foglio "fatti" (id_bando, titolo, tipo_fatto, registro,
domanda, frase, pagina_fisica, in_tabella, frase_solo_in_questo_bando,
anche_sulla_pagina_web, note); le righe senza frase si saltano. I file di
ogni bando vengono da data/processed/documenti_bandi.csv (uso
"frammenti", senza le proroghe); il testo delle pagine si estrae come nel
caricamento (scripts/ingestione/carica_avvisi.pagine_del_pdf). I
frammenti si leggono da una copia temporanea di data/db/chroma, mai
dall'archivio vero, e solo quelli con il metadato sha256.

Per ogni riga:
1. la frase si divide in pezzi su " [...] "; in una riga di tabella
   (in_tabella "sì") ogni pezzo si divide in celle su " | ", e le celle
   si cercano una per una;
2. presenza a tre livelli: (a) esatta; (b) normalizzata: spazi e a capo
   ridotti a uno, apostrofi e virgolette tipografici uniformati, parola
   spezzata dal trattino a fine riga ricucita; (c) senza spazi;
3. pagina: se il pezzo non è nella pagina dichiarata (pagina_fisica, anche
   "3 e 9") si dice dove sta; una riga di tabella vale come trovata solo
   se tutte le celle stanno su una stessa pagina;
4. fuori dai file del bando: "in altro bando", o "assente" con il tratto
   più simile della pagina dichiarata e la differenza;
5. apistici (quattro allegati): la nota comincia con "Azione Bn (Allegato
   An)"; il pezzo deve stare in quell'allegato, e si dice in quali altri;
6. gemelli: in quali altri bandi o allegati compare la frase (livello c),
   confrontato con frase_solo_in_questo_bando;
7. frammenti: in quali frammenti del file il pezzo sta per intero, se è
   spezzato tra due frammenti consecutivi, e dove comincia e finisce nel
   testo vero del frammento, da confrontare con car_visti (la parte che il
   modello di embedding vede). Per le tabelle: le celle corte (meno di 4
   caratteri senza spazi, "celle deboli") e se tutte le celle stanno in un
   frammento;
8. domande con un numero che sta anche nella frase; email e telefoni in
   domanda e note (nel rapporto solo mascherati).

Uscita: un CSV con una riga per fatto e, a terminale, il riepilogo
generale, quello per bando e le righe con un problema. Nessuna rete,
nessun modello, nessuna scrittura in Chroma.
"""

import argparse
import csv
import difflib
import io
import os
import re
import shutil
import statistics
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from scripts.ingestione.carica_avvisi import NUMERO, SENZA_RETE
from src.config import CHROMA_DIR, COLLECTION_NAME, DATI_GREZZI_DIR, PROCESSED_DIR
from src.estrazione.contatti import EMAIL, NUMERO_VERDE
from src.estrazione.pdf_bando import PROROGA
from src.ingestion.avvisi import TELEFONO, mascherato, ricuci_parole

SEPARATORE_PEZZI = " [...] "
SEPARATORE_CELLE = " | "
CELLA_DEBOLE = 4  # caratteri senza spazi: sotto, la cella si trova per caso
# Nota degli apistici: "Azione B1 (Allegato A1)" nel primo foglio,
# "Azione B1, Allegato A1, par. ..." nel secondo (fatti_pdf_modello_2)
NOTA_APISTICI = re.compile(r"^\s*Azione\s+(B\d+)\s*[(,]\s*Allegato\s+(A\d+)\b")
# Coincidenze con un altro foglio: "contenuta" solo se il tratto più corto
# ha almeno tanti caratteri senza spazi; "simile" da questa somiglianza
CONTENUTA_MINIMA = 20
SIMILE_MINIMA = 0.9

# Apostrofi e virgolette tipografici, ricondotti a quelli dritti (come
# src.retrieval._TIPOGRAFICI, che non si importa per non caricare Chroma)
TIPOGRAFICI = str.maketrans(
    {"’": "'", "‘": "'", "`": "'", "“": '"', "”": '"', "«": '"', "»": '"'}
)

LIVELLI = ("a", "b", "c")
TROVATA = "trovata"
PAGINA_DIVERSA = "pagina diversa"
CELLE_SEPARATE = "celle su pagine diverse"
ALTRO_ALLEGATO = "in altro allegato"
ALTRO_BANDO = "in altro bando"
ASSENTE = "assente"
SENZA_FILE = "bando senza file nel registro"

COLONNE = [
    "riga",
    "id_bando",
    "tipo_fatto",
    "registro",
    "in_tabella",
    "pezzi",
    "celle",
    "celle_deboli",
    "esito",
    "livello",
    "pagina_dichiarata",
    "trovata_in",
    "file_della_nota",
    "altri_allegati",
    "altri_bandi",
    "pezzi_in_altri_bandi",
    "solo_dichiarato",
    "solo_calcolato",
    "gemelli",
    "celle_stessa_pagina",
    "celle_stesso_frammento",
    "frammenti",
    "pezzi_interi",
    "pezzi_spezzati",
    "pezzi_visti",
    "posizioni",
    "tratto_simile",
    "somiglianza",
    "differenza",
    "numeri_della_frase_nella_domanda",
    "contatti",
    "problemi",
    "nell_altro_foglio",
]


# --- testo ---


def livello_b(testo: str) -> str:
    """Spazi e a capo ridotti a uno, tipografici uniformati, parole ricucite."""
    testo = testo.replace("\u00a0", " ").translate(TIPOGRAFICI)
    testo, _ = ricuci_parole(testo)
    return " ".join(testo.split())


def livello_c(testo: str) -> str:
    """Il livello b senza nessuno spazio."""
    return "".join(livello_b(testo).split())


def compatto_con_mappa(testo: str) -> tuple[str, list[int]]:
    """Il testo senza spazi (livello c) e, per ogni carattere, la sua posizione nel testo vero.

    Serve per i frammenti, già ricuciti al caricamento: la traduzione dei
    tipografici è un carattere per un carattere, quindi le posizioni
    restano quelle del testo vero.
    """
    tradotto = testo.replace("\u00a0", " ").translate(TIPOGRAFICI)
    caratteri, mappa = [], []
    for posizione, carattere in enumerate(tradotto):
        if not carattere.isspace():
            caratteri.append(carattere)
            mappa.append(posizione)
    return "".join(caratteri), mappa


def pagine_dichiarate(valore) -> list[int]:
    """'3 e 9', '3, 9', 3 -> i numeri; '3-5' -> 3, 4, 5."""
    pagine: list[int] = []
    for a, b in re.findall(r"(\d+)(?:\s*-\s*(\d+))?", str(valore or "")):
        pagine += list(range(int(a), int(b) + 1)) if b else [int(a)]
    return pagine


def unita_della_frase(frase: str, in_tabella: bool) -> list[list[str]]:
    """I pezzi della frase; per una tabella, le celle di ogni pezzo."""
    pezzi = [p.strip() for p in str(frase).split(SEPARATORE_PEZZI) if p.strip()]
    if not in_tabella:
        return [[p] for p in pezzi]
    return [[c.strip() for c in p.split(SEPARATORE_CELLE) if c.strip()] for p in pezzi]


# --- file e pagine ---


@dataclass
class FilePdf:
    """Un file del registro con il testo delle pagine ai tre livelli."""

    sha256: str
    id_bando: str
    classe: str
    parte: str
    nome_file: str
    pagine: list[str]
    pagine_b: list[str] = field(init=False)
    pagine_c: list[str] = field(init=False)

    def __post_init__(self):
        self.pagine_b = [livello_b(p) for p in self.pagine]
        self.pagine_c = ["".join(p.split()) for p in self.pagine_b]

    @property
    def etichetta(self) -> str:
        return f"{self.id_bando}" + (f" ({self.parte})" if self.parte else "")


def livello_nella_pagina(testo: str, f: FilePdf, pagina: int) -> str | None:
    """Il primo livello a cui il testo sta nella pagina (da 1), o None."""
    if testo in f.pagine[pagina - 1]:
        return "a"
    if livello_b(testo) in f.pagine_b[pagina - 1]:
        return "b"
    if livello_c(testo) and livello_c(testo) in f.pagine_c[pagina - 1]:
        return "c"
    return None


def dove(testo: str, file_: list[FilePdf]) -> list[tuple[FilePdf, int, str]]:
    """Tutte le pagine dei file in cui il testo sta, con il livello."""
    return [
        (f, n, livello)
        for f in file_
        for n in range(1, len(f.pagine) + 1)
        if (livello := livello_nella_pagina(testo, f, n))
    ]


def peggiore(livelli) -> str:
    return max(livelli, key=LIVELLI.index)


# --- frammenti ---


@dataclass
class Frammento:
    chunk_num: int
    pagina: int
    testo: str
    car_visti: int
    compatto: str = field(init=False)
    mappa: list[int] = field(init=False)

    def __post_init__(self):
        self.compatto, self.mappa = compatto_con_mappa(self.testo)


def posizione(testo_c: str, fr: Frammento) -> tuple[int, int] | None:
    """Inizio e fine (esclusa) del testo nel testo vero del frammento."""
    k = fr.compatto.find(testo_c)
    if k < 0 or not testo_c:
        return None
    return fr.mappa[k], fr.mappa[k + len(testo_c) - 1] + 1


def _unione(a: str, b: str) -> str:
    """Due frammenti consecutivi uniti senza ripetere la sovrapposizione."""
    for lunghezza in range(min(len(a), len(b)), 0, -1):
        if a.endswith(b[:lunghezza]):
            return a + b[lunghezza:]
    return a + b


@dataclass
class NeiFrammenti:
    interi: list[tuple[int, int, int, int]]  # (chunk_num, inizio, fine, car_visti)
    spezzato: tuple[int, int] | None  # (chunk_num, chunk_num successivo)

    @property
    def visto(self) -> bool:
        return any(fine <= visti for _, _, fine, visti in self.interi)


def nei_frammenti(testo: str, frammenti: list[Frammento]) -> NeiFrammenti:
    testo_c = livello_c(testo)
    interi = [
        (fr.chunk_num, *pos, fr.car_visti)
        for fr in frammenti
        if (pos := posizione(testo_c, fr))
    ]
    spezzato = None
    if not interi:
        for a, b in zip(frammenti, frammenti[1:], strict=False):
            if testo_c in _unione(a.compatto, b.compatto):
                spezzato = (a.chunk_num, b.chunk_num)
                break
    return NeiFrammenti(interi, spezzato)


def celle_in_un_frammento(celle: list[str], frammenti: list[Frammento]) -> list[int]:
    """I frammenti che contengono tutte le celle."""
    return [
        fr.chunk_num
        for fr in frammenti
        if all(livello_c(c) in fr.compatto for c in celle)
    ]


# --- tratto più simile ---


def tratto_simile(testo: str, pagina: str) -> tuple[str, float, str]:
    """Il tratto della pagina più simile al testo, la somiglianza e la differenza."""
    a, b = livello_b(pagina), livello_b(testo)
    if not a or not b:
        return "", 0.0, ""
    blocco = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(
        0, len(a), 0, len(b)
    )
    inizio = max(0, blocco.a - blocco.b)
    tratto = a[inizio : inizio + len(b) + 10]
    confronto = difflib.SequenceMatcher(None, tratto, b, autojunk=False)
    ultima = confronto.get_opcodes()[-1]
    if ultima[0] == "delete" and ultima[2] == len(tratto):
        # la coda della finestra in più non è una differenza
        tratto = tratto[: ultima[1]]
        confronto = difflib.SequenceMatcher(None, tratto, b, autojunk=False)
    differenze = [
        f"«{tratto[i1:i2]}»→«{b[j1:j2]}»"
        for tag, i1, i2, j1, j2 in confronto.get_opcodes()
        if tag != "equal"
    ]
    return tratto, round(confronto.ratio(), 3), "; ".join(differenze[:6])


# --- un fatto ---


def contatti_in(testo: str) -> list[str]:
    """Email e telefoni del testo, mascherati."""
    trovati = [m.group(0) for m in EMAIL.finditer(testo)]
    trovati += [m.group(0) for m in TELEFONO.finditer(testo)]
    trovati += [m.group(0) for m in NUMERO_VERDE.finditer(testo)]
    return [mascherato(t) for t in dict.fromkeys(trovati)]


def numeri_della_frase_nella_domanda(domanda: str, frase: str) -> list[str]:
    nella_frase = set(NUMERO.findall(frase))
    return [n for n in dict.fromkeys(NUMERO.findall(domanda)) if n in nella_frase]


def _formato_dove(trovati) -> str:
    return "; ".join(f"{f.nome_file} p. {n} ({livello})" for f, n, livello in trovati)


def controlla_fatto(
    fatto: dict,
    file_: list[FilePdf],
    frammenti: dict[str, list[Frammento]],
) -> dict:
    """L'esito di tutti i controlli su una riga del foglio."""
    in_tabella = str(fatto.get("in_tabella") or "").strip().lower() == "sì"
    unita = unita_della_frase(fatto["frase"], in_tabella)
    dichiarate = pagine_dichiarate(fatto.get("pagina_fisica"))
    id_bando = fatto["id_bando"]
    del_bando = [f for f in file_ if f.id_bando == id_bando and f.classe != PROROGA]
    nota = NOTA_APISTICI.match(str(fatto.get("note") or ""))
    file_nota = None
    if nota:
        file_nota = next(
            (f for f in del_bando if f.parte == f"Azione {nota.group(1)}"), None
        )
    propri = [file_nota] if file_nota else del_bando
    altri_allegati_del_bando = [f for f in del_bando if f not in propri]
    altri = [f for f in file_ if f.id_bando != id_bando]
    problemi: list[str] = []

    esito: dict = dict.fromkeys(COLONNE, "")
    celle = [c for pezzo in unita for c in pezzo]
    esito.update(
        riga=fatto["riga"],
        id_bando=id_bando,
        tipo_fatto=fatto.get("tipo_fatto") or "",
        registro=fatto.get("registro") or "",
        in_tabella="sì" if in_tabella else "no",
        pezzi=len(unita),
        celle=len(celle) if in_tabella else "",
        celle_deboli=(
            sum(len("".join(c.split())) < CELLA_DEBOLE for c in celle)
            if in_tabella
            else ""
        ),
        pagina_dichiarata=", ".join(map(str, dichiarate)),
        file_della_nota=file_nota.nome_file if file_nota else "",
    )
    if not del_bando:
        problemi.append(SENZA_FILE)

    # presenza e pagina, pezzo per pezzo
    livelli_pezzi: list[str] = []
    pagine_trovate: list[str] = []
    pezzi_fuori_pagina = 0
    pezzi_mancanti: list[list[str]] = []
    pagina_dei_pezzi: list[tuple[FilePdf, int] | None] = []
    stessa_pagina_tabella: list[bool] = []
    for pezzo in unita:
        if in_tabella:
            # una pagina in cui ci sono tutte le celle, preferendo le dichiarate
            candidate = [
                (f, n)
                for f in propri
                for n in range(1, len(f.pagine) + 1)
                if all(livello_nella_pagina(c, f, n) for c in pezzo)
            ]
            candidate.sort(key=lambda fn: fn[1] not in dichiarate)
            if candidate:
                f, n = candidate[0]
                livello = peggiore(livello_nella_pagina(c, f, n) for c in pezzo)
                livelli_pezzi.append(livello)
                pagine_trovate.append(f"{f.nome_file} p. {n} ({livello})")
                pagina_dei_pezzi.append((f, n))
                pezzi_fuori_pagina += n not in dichiarate
                stessa_pagina_tabella.append(True)
                continue
            sparse = [dove(c, propri) for c in pezzo]
            stessa_pagina_tabella.append(False)
            if all(sparse):
                pagine_trovate.append(
                    "celle: " + " / ".join(_formato_dove(s[:2]) for s in sparse)
                )
                problemi.append(CELLE_SEPARATE)
            pezzi_mancanti.append(pezzo)
            pagina_dei_pezzi.append(None)
            continue
        trovati = dove(pezzo[0], propri)
        if not trovati:
            pezzi_mancanti.append(pezzo)
            pagina_dei_pezzi.append(None)
            continue
        trovati.sort(key=lambda t: (t[1] not in dichiarate, LIVELLI.index(t[2])))
        f, n, livello = trovati[0]
        livelli_pezzi.append(livello)
        pagine_trovate.append(_formato_dove(trovati[:3]))
        pagina_dei_pezzi.append((f, n))
        pezzi_fuori_pagina += n not in dichiarate

    esito["trovata_in"] = " || ".join(pagine_trovate)
    if in_tabella:
        esito["celle_stessa_pagina"] = "sì" if all(stessa_pagina_tabella) else "no"

    if not pezzi_mancanti:
        esito["esito"] = PAGINA_DIVERSA if pezzi_fuori_pagina else TROVATA
        esito["livello"] = peggiore(livelli_pezzi)
    else:
        nel_bando = [
            p
            for p in pezzi_mancanti
            if all(dove(c, altri_allegati_del_bando) for c in p)
        ]
        altrove = [p for p in pezzi_mancanti if all(dove(c, altri) for c in p)]
        if file_nota and len(nel_bando) == len(pezzi_mancanti):
            esito["esito"] = ALTRO_ALLEGATO
        elif len(altrove) == len(pezzi_mancanti) and not livelli_pezzi:
            esito["esito"] = ALTRO_BANDO
        elif CELLE_SEPARATE in problemi and len(pezzi_mancanti) == len(unita):
            esito["esito"] = CELLE_SEPARATE
        else:
            esito["esito"] = ASSENTE
        if esito["esito"] == ASSENTE:
            primo = pezzi_mancanti[0]
            testo = " ".join(primo)
            pagine_viste = [
                f.pagine[n - 1]
                for f in propri
                for n in dichiarate
                if 1 <= n <= len(f.pagine)
            ] or [p for f in propri for p in f.pagine[:1]]
            migliore = max(
                (tratto_simile(testo, p) for p in pagine_viste),
                key=lambda t: t[1],
                default=("", 0.0, ""),
            )
            esito["tratto_simile"], esito["somiglianza"], esito["differenza"] = migliore
    if esito["esito"] != TROVATA:
        problemi.append(esito["esito"])

    # gli altri allegati dello stesso bando in cui compare la frase (apistici)
    allegati_gemelli = [
        f.parte or f.nome_file
        for f in altri_allegati_del_bando
        if all(livello_c(c) in "".join(f.pagine_c) for c in celle)
    ]
    esito["altri_allegati"] = "; ".join(allegati_gemelli)
    if nota:
        if file_nota is None:
            problemi.append(f"nessun file per l'azione {nota.group(1)} della nota")

    # gemelli: gli altri bandi in cui compare la frase intera (livello c)
    gemelli = sorted(
        {
            f.etichetta
            for f in altri
            if all(livello_c(c) in "".join(f.pagine_c) for c in celle)
        }
    )
    esito["altri_bandi"] = "; ".join(gemelli)
    # anche pezzo per pezzo: una frase quasi gemella ha qualche pezzo altrove
    if len(unita) > 1:
        esito["pezzi_in_altri_bandi"] = " || ".join(
            f"pezzo {i}: "
            + (
                "; ".join(
                    sorted(
                        {
                            f.etichetta
                            for f in altri
                            if all(livello_c(c) in "".join(f.pagine_c) for c in pezzo)
                        }
                    )
                )
                or "-"
            )
            for i, pezzo in enumerate(unita, start=1)
        )
    dichiarato = str(fatto.get("frase_solo_in_questo_bando") or "").strip().lower()
    # "altri id_bando o allegati": negli apistici una frase di un allegato che
    # compare anche negli altri allegati non è sola
    calcolato = "no" if gemelli or allegati_gemelli else "sì"
    esito["solo_dichiarato"] = dichiarato
    esito["solo_calcolato"] = calcolato
    if not dichiarato:
        esito["gemelli"] = f"vuoto, calcolato {calcolato}"
    elif dichiarato == calcolato:
        esito["gemelli"] = "coerente"
    else:
        esito["gemelli"] = (
            "sì ma trovato altrove"
            if dichiarato == "sì"
            else "no ma non trovato altrove"
        )
        problemi.append(f"gemelli: {esito['gemelli']}")

    # frammenti
    interi = spezzati = visti = 0
    numeri, posizioni = [], []
    tabella_in_un_frammento: list[bool] = []
    for pezzo, dove_pezzo in zip(unita, pagina_dei_pezzi, strict=True):
        f = dove_pezzo[0] if dove_pezzo else (propri[0] if propri else None)
        del_file = frammenti.get(f.sha256, []) if f else []
        if in_tabella:
            comuni = celle_in_un_frammento(pezzo, del_file)
            tabella_in_un_frammento.append(bool(comuni))
            if comuni:
                interi += 1
                fr = next(x for x in del_file if x.chunk_num == comuni[0])
                fini = [posizione(livello_c(c), fr) for c in pezzo]
                inizio, fine = min(p[0] for p in fini), max(p[1] for p in fini)
                visti += fine <= fr.car_visti
                numeri.append(",".join(map(str, comuni)))
                posizioni.append(f"{fr.chunk_num}:{inizio}-{fine}/{fr.car_visti}")
            else:
                numeri.append("-")
                posizioni.append("-")
            continue
        risultato = nei_frammenti(pezzo[0], del_file)
        if risultato.interi:
            interi += 1
            visti += risultato.visto
            numeri.append(",".join(str(c) for c, *_ in risultato.interi))
            c, inizio, fine, car_visti = risultato.interi[0]
            posizioni.append(f"{c}:{inizio}-{fine}/{car_visti}")
        elif risultato.spezzato:
            spezzati += 1
            numeri.append(f"{risultato.spezzato[0]}+{risultato.spezzato[1]}")
            posizioni.append("spezzato")
        else:
            numeri.append("-")
            posizioni.append("-")
    if in_tabella:
        esito["celle_stesso_frammento"] = "sì" if all(tabella_in_un_frammento) else "no"
    esito.update(
        frammenti=" || ".join(numeri),
        pezzi_interi=interi,
        pezzi_spezzati=spezzati,
        pezzi_visti=visti,
        posizioni=" || ".join(posizioni),
    )
    if interi + spezzati < len(unita) and not pezzi_mancanti:
        problemi.append("pezzo in nessun frammento")

    # domanda e contatti
    numeri_domanda = numeri_della_frase_nella_domanda(
        str(fatto.get("domanda") or ""), str(fatto["frase"])
    )
    esito["numeri_della_frase_nella_domanda"] = "; ".join(numeri_domanda)
    if numeri_domanda:
        problemi.append("la domanda contiene un numero della frase")
    contatti = contatti_in(f"{fatto.get('domanda') or ''}\n{fatto.get('note') or ''}")
    esito["contatti"] = "; ".join(contatti)
    if contatti:
        problemi.append("email o telefono in domanda o note")

    esito["problemi"] = "; ".join(dict.fromkeys(problemi))
    return esito


# --- coincidenze con un altro foglio ---


def pezzi_c(frase: str) -> list[str]:
    """I pezzi della frase al livello senza spazi (le celle restano unite)."""
    return [livello_c(p) for p in str(frase).split(SEPARATORE_PEZZI) if p.strip()]


def coincidenze(fatto: dict, altri: list[dict]) -> list[tuple[int, str]]:
    """(riga dell'altro foglio, tipo) per le frasi dell'altro foglio che coincidono.

    Al livello senza spazi: "frase identica"; "pezzo identico" (un pezzo
    uguale a un pezzo o alla frase dell'altra riga); "contenuta" (un pezzo
    o la frase dentro l'altra frase o un suo pezzo, o il contrario, se il
    più corto ha almeno CONTENUTA_MINIMA caratteri); "simile 0.xx"
    (somiglianza tra le frasi almeno SIMILE_MINIMA). Per ogni riga
    dell'altro foglio si dice il tipo più forte.
    """
    frase = livello_c(str(fatto["frase"]))
    miei = [*pezzi_c(fatto["frase"]), frase]
    uscita = []
    for altro in altri:
        sua = livello_c(str(altro["frase"]))
        suoi = [*pezzi_c(altro["frase"]), sua]
        if frase == sua:
            uscita.append((altro["riga"], "frase identica"))
        elif set(miei) & set(suoi):
            uscita.append((altro["riga"], "pezzo identico"))
        elif any(
            min(len(a), len(b)) >= CONTENUTA_MINIMA and (a in b or b in a)
            for a in miei
            for b in suoi
        ):
            uscita.append((altro["riga"], "contenuta"))
        else:
            somiglianza = difflib.SequenceMatcher(None, frase, sua).ratio()
            if somiglianza >= SIMILE_MINIMA:
                uscita.append((altro["riga"], f"simile {somiglianza:.2f}"))
    return uscita


def formato_coincidenze(trovate: list[tuple[int, str]]) -> str:
    return "; ".join(f"riga {r}: {tipo}" for r, tipo in trovate)


# --- ingressi ---


def leggi_foglio(percorso: Path, foglio: str = "fatti") -> list[dict]:
    """Le righe del foglio con una frase, con il numero di riga del foglio."""
    import openpyxl

    libro = openpyxl.load_workbook(percorso, read_only=True, data_only=True)
    try:
        righe = list(libro[foglio].iter_rows(values_only=True))
    finally:
        libro.close()
    intestazione = [str(c).strip() if c is not None else "" for c in righe[0]]
    fatti = []
    for numero, valori in enumerate(righe[1:], start=2):
        fatto = dict(zip(intestazione, valori, strict=False))
        if fatto.get("frase") and str(fatto["frase"]).strip():
            fatto["riga"] = numero
            fatto["id_bando"] = str(fatto.get("id_bando") or "").strip()
            fatti.append(fatto)
    return fatti


def file_del_registro() -> list[FilePdf]:
    """I file con uso "frammenti" del registro, con il testo delle pagine."""
    from scripts.ingestione.carica_avvisi import (
        leggi_registro,
        pagine_del_pdf,
        percorso_del_file,
    )
    from scripts.ingestione.registra_avvisi import NOME_FILE

    return [
        FilePdf(
            r["sha256"],
            r["id_bandi"],
            r["classe"],
            r["parte"],
            r["nome_file"],
            pagine_del_pdf(percorso_del_file(r)),
        )
        for r in leggi_registro(PROCESSED_DIR / NOME_FILE)
    ]


def frammenti_da_copia(cartella: Path = CHROMA_DIR) -> dict[str, list[Frammento]]:
    """I frammenti con sha256, letti da una copia temporanea della cartella di Chroma."""
    for nome, valore in SENZA_RETE.items():
        os.environ[nome] = valore
    import chromadb
    from chromadb.config import Settings

    temporanea = Path(tempfile.mkdtemp(prefix="chroma_copia_"))
    try:
        copia = temporanea / "chroma"
        shutil.copytree(cartella, copia)
        cliente = chromadb.PersistentClient(
            path=str(copia), settings=Settings(anonymized_telemetry=False)
        )
        dati = cliente.get_collection(COLLECTION_NAME).get(
            include=["documents", "metadatas"]
        )
        per_file: dict[str, list[Frammento]] = {}
        for testo, meta in zip(dati["documents"], dati["metadatas"], strict=True):
            if meta.get("sha256"):
                per_file.setdefault(meta["sha256"], []).append(
                    Frammento(meta["chunk_num"], meta["page"], testo, meta["car_visti"])
                )
        del cliente
    finally:
        shutil.rmtree(temporanea, ignore_errors=True)
    for lista in per_file.values():
        lista.sort(key=lambda fr: fr.chunk_num)
    return per_file


# --- rapporto ---


def scrivi_csv(esiti: list[dict], percorso: Path) -> None:
    buffer = io.StringIO(newline="")
    scrittore = csv.DictWriter(buffer, fieldnames=COLONNE, lineterminator="\r\n")
    scrittore.writeheader()
    scrittore.writerows(esiti)
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_bytes(buffer.getvalue().encode("utf-8-sig"))


def riepilogo(esiti: list[dict]) -> list[str]:
    def conta(chiave, valore):
        return sum(e[chiave] == valore for e in esiti)

    def somma(chiave):
        return sum(int(e[chiave] or 0) for e in esiti)

    pezzi = somma("pezzi")
    livelli = ", ".join(f"{v} {conta('livello', v)}" for v in LIVELLI)
    esiti_conta = (
        f"trovata {conta('esito', TROVATA)}, pagina diversa "
        f"{conta('esito', PAGINA_DIVERSA)}, celle su pagine diverse "
        f"{conta('esito', CELLE_SEPARATE)}, in altro allegato "
        f"{conta('esito', ALTRO_ALLEGATO)}, in altro bando "
        f"{conta('esito', ALTRO_BANDO)}, assente {conta('esito', ASSENTE)}"
    )
    vuoti = sum(e["gemelli"].startswith("vuoto") for e in esiti)
    diversi = sum(e["gemelli"] not in ("coerente", "") for e in esiti) - vuoti
    frammenti = (
        f"Pezzi interi in un frammento {somma('pezzi_interi')}, spezzati "
        f"{somma('pezzi_spezzati')}, dentro la parte vista {somma('pezzi_visti')} "
        f"(su {pezzi})"
    )
    tabelle = (
        f"Righe di tabella {conta('in_tabella', 'sì')}: celle deboli "
        f"{somma('celle_deboli')}, tutte le celle in un frammento "
        f"{conta('celle_stesso_frammento', 'sì')}"
    )
    gemelli = f"Gemelli diversi dal dichiarato: {diversi}; colonna vuota, valore calcolato: {vuoti}"
    return [
        f"Fatti controllati: {len(esiti)} (pezzi {pezzi})",
        f"Trovati per livello: {livelli}",
        f"Esiti: {esiti_conta}",
        gemelli,
        frammenti,
        tabelle,
    ]


def per_bando(esiti: list[dict]) -> list[str]:
    righe = [
        "| id_bando | fatti | a | b | c | con problemi | pezzi interi | pezzi visti |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for id_bando in sorted({e["id_bando"] for e in esiti}):
        del_bando = [e for e in esiti if e["id_bando"] == id_bando]
        conta = [sum(e["livello"] == livello for e in del_bando) for livello in LIVELLI]
        pezzi = sum(int(e["pezzi"]) for e in del_bando)
        righe.append(
            f"| {id_bando} | {len(del_bando)} | {conta[0]} | {conta[1]} | {conta[2]} | "
            f"{sum(bool(e['problemi']) for e in del_bando)} | "
            f"{sum(int(e['pezzi_interi']) for e in del_bando)}/{pezzi} | "
            f"{sum(int(e['pezzi_visti']) for e in del_bando)}/{pezzi} |"
        )
    return righe


def con_problemi(esiti: list[dict]) -> list[str]:
    return [
        f"riga {e['riga']} ({e['id_bando']}, {e['tipo_fatto']}): {e['problemi']}"
        for e in esiti
        if e["problemi"]
    ]


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--foglio", required=True, type=Path)
    parser.add_argument(
        "--confronta",
        type=Path,
        help="un altro foglio dei fatti: coincidenze delle frasi (livello c)",
    )
    parser.add_argument(
        "--uscita",
        type=Path,
        default=DATI_GREZZI_DIR / "prova" / "fatti_controllo_2026-11-20.csv",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    argomenti = leggi_argomenti(argv)
    if not argomenti.foglio.is_file():
        print(f"Errore: foglio non trovato: {argomenti.foglio}", file=sys.stderr)
        return 1
    fatti = leggi_foglio(argomenti.foglio)
    file_ = file_del_registro()
    frammenti = frammenti_da_copia()
    esiti = [controlla_fatto(f, file_, frammenti) for f in fatti]
    if argomenti.confronta:
        altri = leggi_foglio(argomenti.confronta)
        for fatto, esito in zip(fatti, esiti, strict=True):
            esito["nell_altro_foglio"] = formato_coincidenze(coincidenze(fatto, altri))
    scrivi_csv(esiti, argomenti.uscita)
    print("\n".join(riepilogo(esiti)))
    print()
    print("\n".join(per_bando(esiti)))
    problemi = con_problemi(esiti)
    print(f"\nRighe con un problema: {len(problemi)}")
    print("\n".join(problemi))
    somiglianze = [float(e["somiglianza"]) for e in esiti if e["somiglianza"] != ""]
    if somiglianze:
        print(
            f"Somiglianza mediana degli assenti: {statistics.median(somiglianze):.3f}"
        )
    if argomenti.confronta:
        uguali = [e for e in esiti if e["nell_altro_foglio"]]
        print(f"\nCoincidenze con {argomenti.confronta.name}: {len(uguali)} righe")
        print("\n".join(f"riga {e['riga']}: {e['nell_altro_foglio']}" for e in uguali))
    print(f"\nScritto: {argomenti.uscita}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
