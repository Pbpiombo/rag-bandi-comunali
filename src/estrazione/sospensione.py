"""Indizio di una sospensione o di una chiusura anticipata, senza modello.

Stesso meccanismo della proroga (src/estrazione/proroga.py): parole
chiave (PAROLE) nelle frasi intere del testo della pagina e nei nomi dei
file collegati, senza distinguere maiuscole e accenti, come parole
intere. Il risultato e' solo un indizio con la frase in cui compare: non
cambia il gruppo del rapporto e nessuna data. Lo stato calcolato dalla
scadenza non vede le sospensioni (docs/coda.md, voce del 24/11/2026).

Le formule di rito dei bandi a sportello ("salvo esaurimento", "fino ad
esaurimento", "in caso di esaurimento delle risorse", "si riserva la
possibilita' di sospendere") non contengono nessuna di queste parole
intere, e non danno la nota.

Esclusioni (REGOLE), decise il 24/11/2026 sui casi veri delle pagine
salvate il 23/11/2026. Una parola chiave non conta se:
- RISERVA: nella stessa frase, prima di lei, c'e' "salvo" o "si riserva
  la facolta' / la possibilita' / il diritto di" ("salvo chiusura
  anticipata per esaurimento delle risorse"; "si riserva la facolta' di
  prevedere la chiusura anticipata dello sportello"). Dopo non conta:
  "Il bando e' sospeso, salvo nuove risorse" da' la nota;
- LAVORO: e' in "sospensione (sospensioni) dal lavoro", "lavoratori
  sospesi", "lavoratrici sospese" (requisiti sulla Cassa integrazione);
- BARRE: ha una barra subito prima o subito dopo, come nell'elenco di
  rito "decreto di sospensione/chiusura/proroga".
Una frase da' la nota se almeno una delle sue parole chiave conta; se
nessuna conta, la frase e' esclusa, con le regole che l'hanno esclusa, e
resta visibile nei file di --testi della ricognizione.

Caso vero, sulla pagina salvata il 23/11/2026: "Sospensione del bando
per i seguenti destinatari:" (incentivi ai datori di lavoro privati per
l'occupazione dei disoccupati, sospeso dall'8 luglio 2026 per cinque
categorie di destinatari).
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from src.estrazione.proroga import LUNGHEZZA_MASSIMA, candidate, normalizza

# Le parole e le espressioni, gia' senza accenti e in minuscolo
PAROLE = (
    "sospensione",
    "sospeso",
    "sospesa",
    "sospesi",
    "sospese",
    "chiusura anticipata",
    "chiuso anticipatamente",
    "chiusa anticipatamente",
    "risorse esaurite",
    "esaurite le risorse",
    "fondi esauriti",
)


def _schema(espressioni) -> re.Pattern:
    """Parole intere; tra le parole di un'espressione, uno spazio qualunque."""
    alternative = "|".join(r"\s+".join(e.split()) for e in espressioni)
    return re.compile(rf"(?<!\w)(?:{alternative})(?!\w)")


SCHEMA = _schema(PAROLE)

PREFISSO = "possibile sospensione: "

RISERVA = (
    'preceduta da "salvo" o da "si riserva la facoltà / la possibilità / il diritto di"'
)
LAVORO = 'altro significato: "sospensione dal lavoro", "lavoratori sospesi"'
BARRE = 'elenco con le barre ("sospensione/chiusura/proroga")'

PRIMA_DELLA_PAROLA = _schema(
    (
        "salvo",
        "si riserva la facolta di",
        "si riserva la possibilita di",
        "si riserva il diritto di",
    )
)
ALTRO_SIGNIFICATO = _schema(
    (
        "sospensione dal lavoro",
        "sospensioni dal lavoro",
        "lavoratori sospesi",
        "lavoratrici sospese",
    )
)
BARRA_PRIMA = re.compile(r"/\s*$")
BARRA_DOPO = re.compile(r"^\s*/")


def _riserva(testo: str, parola: re.Match) -> bool:
    return bool(PRIMA_DELLA_PAROLA.search(testo, 0, parola.start()))


def _lavoro(testo: str, parola: re.Match) -> bool:
    return any(
        a.start() <= parola.start() and parola.end() <= a.end()
        for a in ALTRO_SIGNIFICATO.finditer(testo)
    )


def _barre(testo: str, parola: re.Match) -> bool:
    return bool(
        BARRA_PRIMA.search(testo[: parola.start()])
        or BARRA_DOPO.search(testo[parola.end() :])
    )


# Le regole di esclusione, con il nome che va nei file di --testi
REGOLE: tuple[tuple[str, Callable[[str, re.Match], bool]], ...] = (
    (RISERVA, _riserva),
    (LAVORO, _lavoro),
    (BARRE, _barre),
)


@dataclass
class Esclusa:
    frase: str
    regole: list[str]


@dataclass
class Esame:
    # le frasi e i nomi di file che danno la nota, interi
    valide: list[str] = field(default_factory=list)
    # quelle in cui ogni parola chiave e' esclusa da una regola
    escluse: list[Esclusa] = field(default_factory=list)


def esamina(html: str) -> Esame:
    """Le frasi intere e i nomi di file con una parola di PAROLE (candidate),
    divise tra valide ed escluse da REGOLE, senza ripetizioni."""
    esame, viste = Esame(), set()
    for frase in candidate(html):
        testo = normalizza(frase)
        parole = list(SCHEMA.finditer(testo))
        if not parole or frase in viste:
            continue
        viste.add(frase)
        regole_delle_parole = [
            [nome for nome, regola in REGOLE if regola(testo, p)] for p in parole
        ]
        if all(regole_delle_parole):
            regole = list(dict.fromkeys(r for rr in regole_delle_parole for r in rr))
            esame.escluse.append(Esclusa(frase, regole))
        else:
            esame.valide.append(frase)
    return esame


def nota_di_sospensione(html: str) -> str | None:
    """La nota del rapporto, "possibile sospensione: <frase>", con la
    prima frase valida tagliata a 200 battute, o None."""
    valide = esamina(html).valide
    return PREFISSO + valide[0][:LUNGHEZZA_MASSIMA] if valide else None


def frasi_di_sospensione(html: str) -> list[str]:
    """Le frasi e i nomi di file che danno la nota, interi."""
    return esamina(html).valide
