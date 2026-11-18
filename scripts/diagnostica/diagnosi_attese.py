"""Diagnosi delle attese dell'insieme di prova, senza modello.

Per ogni bando atteso di una registrazione di prova_insieme dice dove si
perde, se manca dalla risposta:

- archivio: nessun titolo della tabella bandi corrisponde all'attesa;
- archivio_non_bando: corrispondono solo righe con natura 'non_bando';
- archivio_scaduto: i bandi corrispondenti sono tutti scaduti alla data
  della prova (un bando scaduto non deve comparire tra gli aperti);
- recupero: c'è almeno un bando non scaduto, ma l'attesa non compare nel
  blocco dei dati passato al modello;
- esclusione: l'attesa compare nei dati ma non tra i bandi citati;
- ok: l'attesa compare tra i bandi citati.

Le vietate si segnalano se compaiono tra i bandi citati. Una voce senza
risposta (errore della catena) ha categoria "errore".

La corrispondenza tra attesa e testo è quella di prova_insieme
(corrisponde, controlla_attese). Un'attesa che non è un titolo di bando
("deve cercare anche nei bandi") finisce in "archivio": non si indovina,
si controlla a mano.

Legge solo i JSON salvati e SQLite in sola lettura: nessuna chiamata al
modello, nessun accesso a Postgres. Lo stato dei bandi si calcola alla
data_di_oggi del meta.json della registrazione, con le funzioni delle
interrogazioni (scaduto, stato_bando).

Il database dipende dal meta.json (passo 0 della roadmap):
- con "archivio" (registrazione fatta con --archivio), un SQLite ricreato
  dai CSV di quella cartella con crea_da_csv, in una cartella temporanea
  cancellata all'uscita. Se la cartella non c'è più o la sua impronta non
  è quella del meta, errore: non si ripiega su comune.sqlite;
- senza "archivio", comune.sqlite di oggi: se i CSV di data/processed sono
  cambiati dalla prova, il rapporto lo avvisa.
Un'impronta senza versione_impronta è calcolata sui byte (prima del
18/11/2026): è "in formato vecchio, non confrontabile", non "cambiata";
con "archivio" è un errore, perché l'archivio non si può verificare.
Più registrazioni su archivi diversi si accettano, con un avviso in testa:
i totali non sono una misura appaiata. --titolo legge sempre comune.sqlite.

Uso:

    python -m scripts.diagnostica.diagnosi_attese CARTELLA [CARTELLA ...]
    python -m scripts.diagnostica.diagnosi_attese --titolo "testo" [--titolo ...]

CARTELLA è una cartella di registrazione (con meta.json e domande/).
--titolo controlla solo l'archivio per un titolo, alla data di oggi.

Uscita: rapporto.md e diagnosi.csv in dati-grezzi/diagnosi/<AAAA-MM-GG_HHMMSS>/.
"""

import argparse
import csv
import sqlite3
import sys
import tempfile
from collections import Counter
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass, field
from pathlib import Path

from scripts.diagnostica.prova_insieme import (
    FORMATO_VECCHIO,
    adesso,
    cancella_temporanea,
    celle,
    controlla_attese,
    corrisponde,
    domanda_di,
    impronta_confrontabile,
    impronta_csv,
    leggi_json,
    leggi_voci,
    nome_cartella,
    scartate,
)
from src.config import DATI_GREZZI_DIR, SQLITE_PATH
from src.database.interrogazioni_bandi import data_di_oggi, scadenze_di, scaduto
from src.database.schema import ErroreArchivio, crea_da_csv
from src.database.stato_documenti import stato_bando

CARTELLA_DIAGNOSI = DATI_GREZZI_DIR / "diagnosi"

# Il database di una registrazione senza "archivio" nel meta
DATABASE_VERO = "data/processed (comune.sqlite)"

# Categorie delle attese, nell'ordine del rapporto
OK = "ok"
ESCLUSIONE = "esclusione"
RECUPERO = "recupero"
ARCHIVIO_SCADUTO = "archivio_scaduto"
ARCHIVIO_NON_BANDO = "archivio_non_bando"
ARCHIVIO = "archivio"
ERRORE = "errore"
# Categorie delle vietate
VIETATA_CITATA = "vietata_citata"
VIETATA_NON_CITATA = "vietata_non_citata"
# Categoria di un titolo cercato con --titolo che ha un bando non scaduto
IN_ARCHIVIO = "in_archivio"

CATEGORIE = (
    OK,
    ESCLUSIONE,
    RECUPERO,
    ARCHIVIO_SCADUTO,
    ARCHIVIO_NON_BANDO,
    ARCHIVIO,
    ERRORE,
    VIETATA_CITATA,
    VIETATA_NON_CITATA,
    IN_ARCHIVIO,
)

# Stato di un bando alla data della prova
APERTO = "aperto"
A_SPORTELLO = "a sportello"
SCADUTO = "scaduto"

NON_BANDO = "non_bando"

COLONNE_CSV = (
    "registrazione",
    "lotto",
    "data_prova",
    "codice",
    "tipo",
    "testo",
    "n_titoli",
    "titoli_e_stati",
    "nei_dati",
    "citata",
    "categoria",
)


class ErroreDiagnosi(Exception):
    """Un errore da mostrare senza traccia."""


@dataclass
class TitoloInArchivio:
    """Una riga della tabella bandi il cui titolo corrisponde all'attesa."""

    id: str
    titolo: str
    natura: str
    stato: str
    frase: str

    def descrizione(self) -> str:
        testo = f"{self.titolo} [{self.id}]: {self.stato} ({self.frase})"
        if self.natura == NON_BANDO:
            testo += f"; natura {NON_BANDO}"
        return testo


@dataclass
class Diagnosi:
    """L'esito di un'attesa, di una vietata o di un titolo cercato."""

    registrazione: str
    lotto: str
    data_prova: str
    codice: str
    tipo: str
    testo: str
    titoli: list[TitoloInArchivio] = field(default_factory=list)
    nei_dati: bool | None = None
    citata: bool | None = None
    categoria: str = ""

    def riga_csv(self) -> dict:
        return {
            "registrazione": self.registrazione,
            "lotto": self.lotto,
            "data_prova": self.data_prova,
            "codice": self.codice,
            "tipo": self.tipo,
            "testo": self.testo,
            "n_titoli": len(self.titoli),
            "titoli_e_stati": " || ".join(t.descrizione() for t in self.titoli),
            "nei_dati": si_no(self.nei_dati),
            "citata": si_no(self.citata),
            "categoria": self.categoria,
        }


def si_no(valore: bool | None) -> str:
    if valore is None:
        return ""
    return "sì" if valore else "no"


# --- Archivio ---


def apri_in_lettura(percorso: Path | None = None) -> sqlite3.Connection:
    """La connessione a SQLite in sola lettura: il file non si crea né si modifica.

    Senza percorso, SQLITE_PATH, letto al momento della chiamata.
    """
    percorso = percorso or SQLITE_PATH
    if not percorso.exists():
        raise ErroreDiagnosi(f"database non trovato: {percorso}")
    conn = sqlite3.connect(f"{percorso.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def file_cambiati(prima: dict, ora: dict) -> list[str]:
    """I CSV con impronta diversa, aggiunti o tolti, dai dizionari "file"."""
    return sorted(n for n in set(prima) | set(ora) if prima.get(n) != ora.get(n))


@contextmanager
def database_dell_archivio(
    cartella: Path, impronta_attesa: dict
) -> Iterator[tuple[sqlite3.Connection, list[str]]]:
    """Il SQLite ricreato dai CSV di un archivio congelato, in sola lettura.

    Prima controlla che la cartella esista e che la sua impronta sia
    impronta_attesa (l'impronta_csv del meta); altrimenti ErroreDiagnosi,
    senza ripiegare su comune.sqlite. Il SQLite sta in una cartella
    temporanea, mai in data/db, cancellata all'uscita. Restituisce la
    connessione e gli avvisi (righe scartate dai CSV).
    """
    if not cartella.is_dir():
        raise ErroreDiagnosi(
            f"archivio non trovato: {cartella}; la diagnosi non ripiega su "
            "comune.sqlite"
        )
    attesa = impronta_attesa.get("complessiva")
    if not attesa:
        raise ErroreDiagnosi(
            f"impronta dell'archivio {cartella} mancante nel meta.json: "
            "l'archivio non si può verificare"
        )
    if not impronta_confrontabile(impronta_attesa):
        raise ErroreDiagnosi(
            f"impronta dell'archivio {cartella} nel meta.json {FORMATO_VECCHIO}: "
            "l'archivio non si può verificare e la diagnosi non ripiega su "
            "comune.sqlite"
        )
    ora = impronta_csv(cartella)
    if ora["complessiva"] != attesa:
        cambiati = file_cambiati(impronta_attesa.get("file") or {}, ora["file"])
        raise ErroreDiagnosi(
            f"l'impronta dell'archivio {cartella} è cambiata dalla registrazione "
            f"({attesa[:16]} nel meta, {ora['complessiva'][:16]} ora; file "
            f"cambiati: {', '.join(cambiati) or 'non indicati nel meta'}): "
            "la diagnosi non ripiega su comune.sqlite"
        )

    temporanea = Path(tempfile.mkdtemp(prefix="diagnosi_archivio_"))
    try:
        percorso = temporanea / "archivio.sqlite"
        try:
            conteggi = crea_da_csv(percorso, cartella)
        except ErroreArchivio as errore:
            raise ErroreDiagnosi(str(errore)) from errore
        avvisi = []
        if scartate(conteggi):
            avvisi.append(f"righe scartate dai CSV dell'archivio: {scartate(conteggi)}")
        conn = apri_in_lettura(percorso)
        try:
            yield conn, avvisi
        finally:
            conn.close()
    finally:
        cancella_temporanea(temporanea)


def stato_alla_data(conn: sqlite3.Connection, riga, oggi: str) -> tuple[str, str]:
    """Lo stato del bando alla data oggi (ISO) e la frase completa.

    Scaduto come negli elenchi degli aperti (scaduto, finestre comprese);
    poi a sportello o aperto. La frase è quella di stato_bando.
    """
    scadenze = scadenze_di(conn, riga["id"])
    frase = stato_bando(riga, scadenze, oggi)
    if scaduto(riga, scadenze, oggi):
        return SCADUTO, frase
    if riga["a_sportello"]:
        return A_SPORTELLO, frase
    return APERTO, frase


def titoli_in_archivio(
    conn: sqlite3.Connection, atteso: str, oggi: str
) -> list[TitoloInArchivio]:
    """Le righe di bandi il cui titolo corrisponde all'attesa, con lo stato a oggi."""
    titoli = []
    for riga in conn.execute("SELECT * FROM bandi ORDER BY titolo, id").fetchall():
        if not corrisponde(atteso, riga["titolo"]):
            continue
        stato, frase = stato_alla_data(conn, riga, oggi)
        titoli.append(
            TitoloInArchivio(riga["id"], riga["titolo"], riga["natura"], stato, frase)
        )
    return titoli


def categoria_archivio(titoli: list[TitoloInArchivio], non_scaduto: str) -> str:
    """La categoria dalla sola presenza in archivio.

    Le righe non_bando si contano ma non decidono: se ci sono solo quelle,
    archivio_non_bando. non_scaduto è la categoria con almeno un bando non
    scaduto: recupero per le attese, in_archivio per i titoli cercati.
    """
    if not titoli:
        return ARCHIVIO
    bandi = [t for t in titoli if t.natura != NON_BANDO]
    if not bandi:
        return ARCHIVIO_NON_BANDO
    if any(t.stato != SCADUTO for t in bandi):
        return non_scaduto
    return ARCHIVIO_SCADUTO


# --- Registrazioni ---


def senza_risposta(voce: dict) -> bool:
    return bool(voce.get("errore")) or "risposta" not in voce


def titoli_citati(voce: dict) -> list[str]:
    """I titoli dei bandi citati, come li passa verifica_risposta a controlla_attese."""
    return [v.get("titolo") or v.get("url") for v in voce.get("bandi_citati", [])]


def diagnosi_voce(
    conn: sqlite3.Connection,
    voce: dict,
    oggi: str,
    registrazione: str = "",
    lotto: str = "",
) -> tuple[list[Diagnosi], list[str]]:
    """Le diagnosi delle attese e delle vietate di una voce, e gli avvisi."""
    domanda = domanda_di(voce)
    avvisi = []
    errore = senza_risposta(voce)
    citati = controlla_attese(domanda, titoli_citati(voce))
    nei_dati = controlla_attese(domanda, [voce.get("dati") or ""])

    salvate = voce.get("attese_esito") or {}
    if not errore and salvate and salvate.get("trovate") != citati["trovate"]:
        avvisi.append(
            f"{domanda.codice}: attese trovate diverse da quelle salvate "
            f"({salvate.get('trovate')} contro {citati['trovate']})"
        )

    def nuova(tipo: str, testo: str) -> Diagnosi:
        return Diagnosi(registrazione, lotto, oggi, domanda.codice, tipo, testo)

    diagnosi = []
    for atteso in domanda.attese:
        d = nuova("attesa", atteso)
        d.titoli = titoli_in_archivio(conn, atteso, oggi)
        if errore:
            d.categoria = ERRORE
        else:
            d.citata = atteso in citati["trovate"]
            d.nei_dati = atteso in nei_dati["trovate"]
            if d.citata:
                d.categoria = OK
            elif d.nei_dati:
                d.categoria = ESCLUSIONE
            else:
                d.categoria = categoria_archivio(d.titoli, RECUPERO)
        diagnosi.append(d)

    for vietata in domanda.vietate:
        d = nuova("vietata", vietata)
        d.titoli = titoli_in_archivio(conn, vietata, oggi)
        if errore:
            d.categoria = ERRORE
        else:
            d.citata = vietata in citati["vietate_comparse"]
            d.nei_dati = vietata in nei_dati["vietate_comparse"]
            d.categoria = VIETATA_CITATA if d.citata else VIETATA_NON_CITATA
        diagnosi.append(d)
    return diagnosi, avvisi


@dataclass
class Registrazione:
    """Una cartella di registrazione diagnosticata."""

    nome: str
    lotto: str
    data_prova: str
    commit: str
    voci: int
    diagnosi: list[Diagnosi]
    avvisi: list[str]
    archivio: str = DATABASE_VERO


def leggi_meta(cartella: Path) -> dict:
    """Il meta.json di una registrazione, con la data della prova."""
    percorso_meta = cartella / "meta.json"
    if not percorso_meta.exists():
        raise ErroreDiagnosi(f"meta.json mancante in {cartella}")
    meta = leggi_json(percorso_meta)
    if not meta.get("data_di_oggi"):
        raise ErroreDiagnosi(f"data_di_oggi mancante in {percorso_meta}")
    return meta


def descrizione_archivio(meta: dict) -> str:
    """Il database di una registrazione come lo mostra il rapporto."""
    if not meta.get("archivio"):
        return DATABASE_VERO
    impronta = (meta.get("impronta_csv") or {}).get("complessiva") or ""
    return f"{meta['archivio']} ({impronta[:16]})"


def diagnosi_cartella(conn: sqlite3.Connection, cartella: Path) -> Registrazione:
    """Le diagnosi di tutte le voci con attese o vietate di una registrazione.

    conn è il database della registrazione: con "archivio" nel meta, quello
    di database_dell_archivio, che ne ha già controllato l'impronta.
    """
    meta = leggi_meta(cartella)
    oggi = meta["data_di_oggi"]

    nome = f"{cartella.parent.name}/{cartella.name}"
    lotto = str(meta.get("lotto", ""))
    avvisi = []
    impronta_meta = meta.get("impronta_csv") or {}
    impronta = impronta_meta.get("complessiva")
    if not meta.get("archivio") and impronta:
        if not impronta_confrontabile(impronta_meta):
            avvisi.append(
                f"l'impronta dei CSV di data/processed nel meta è {FORMATO_VECCHIO}: "
                "non si sa se l'archivio letto è quello della registrazione"
            )
        elif impronta != impronta_csv()["complessiva"]:
            avvisi.append(
                "i CSV di data/processed sono cambiati dalla prova: l'archivio "
                "letto non è quello della registrazione"
            )
    voci = leggi_voci(cartella)
    mancanti = len(meta.get("codici", [])) - len(voci)
    if mancanti:
        avvisi.append(f"{mancanti} domande del meta senza file in domande/")

    diagnosi = []
    for voce in voci:
        if not voce.get("attese") and not voce.get("vietate"):
            continue
        righe, avvisi_voce = diagnosi_voce(conn, voce, oggi, nome, lotto)
        diagnosi.extend(righe)
        avvisi.extend(avvisi_voce)
    return Registrazione(
        nome,
        lotto,
        oggi,
        (meta.get("commit") or "")[:7],
        len(voci),
        diagnosi,
        avvisi,
        descrizione_archivio(meta),
    )


def diagnosi_titolo(conn: sqlite3.Connection, testo: str, oggi: str) -> Diagnosi:
    """Il solo controllo dell'archivio per un titolo, alla data oggi."""
    d = Diagnosi("--titolo", "", oggi, "", "titolo", testo)
    d.titoli = titoli_in_archivio(conn, testo, oggi)
    d.categoria = categoria_archivio(d.titoli, IN_ARCHIVIO)
    return d


# --- Uscita ---


def scrivi_csv(percorso: Path, diagnosi: list[Diagnosi]) -> None:
    with percorso.open("w", encoding="utf-8", newline="") as f:
        scrittore = csv.DictWriter(f, fieldnames=COLONNE_CSV)
        scrittore.writeheader()
        for d in diagnosi:
            scrittore.writerow(d.riga_csv())


def cella_titoli(titoli: list[TitoloInArchivio]) -> str:
    if not titoli:
        return "nessuno"
    return f"{len(titoli)}: " + "<br>".join(celle(t.descrizione()) for t in titoli)


def tabella_diagnosi(diagnosi: list[Diagnosi]) -> list[str]:
    righe = [
        (
            "| codice | tipo | testo | titoli in archivio (stato) | nei dati | citata "
            "| categoria |"
        ),
        "|---|---|---|---|---|---|---|",
    ]
    for d in diagnosi:
        righe.append(
            f"| {celle(d.codice)} | {d.tipo} | {celle(d.testo)} "
            f"| {cella_titoli(d.titoli)} | {si_no(d.nei_dati)} "
            f"| {si_no(d.citata)} | **{d.categoria}** |"
        )
    return righe


def tabella_totali(registrazioni: list[Registrazione]) -> list[str]:
    conteggi = {r.nome: Counter(d.categoria for d in r.diagnosi) for r in registrazioni}
    totale = sum(conteggi.values(), Counter())
    nomi = [r.nome for r in registrazioni]
    righe = [
        "| categoria | " + " | ".join(nomi) + " | totale |",
        "|---|" + "---|" * (len(nomi) + 1),
    ]
    for categoria in CATEGORIE:
        if not totale[categoria]:
            continue
        valori = " | ".join(str(conteggi[n][categoria]) for n in nomi)
        righe.append(f"| {categoria} | {valori} | {totale[categoria]} |")
    return righe


def rapporto(
    registrazioni: list[Registrazione], titoli: list[Diagnosi], momento: str
) -> str:
    su_archivio = any(r.archivio != DATABASE_VERO for r in registrazioni)
    righe = [
        "# Diagnosi delle attese",
        "",
        f"- generato: {momento}",
    ]
    if registrazioni:
        righe.append(
            "- database delle registrazioni: colonna «archivio» della tabella "
            "Registrazioni (sola lettura)"
        )
    if titoli:
        riga = (
            f"- database di --titolo: {SQLITE_PATH} (sola lettura), alla data di oggi"
        )
        if su_archivio:
            riga += (
                "; la ricerca per titolo è su comune.sqlite, non sull'archivio "
                "delle registrazioni"
            )
        righe.append(riga)
    righe += [
        (
            "- stato dei bandi alla data della prova di ogni registrazione; "
            "per --titolo alla data di oggi"
        ),
        "",
    ]
    if registrazioni:
        righe += [
            "## Registrazioni",
            "",
            "| registrazione | lotto | data della prova | commit | voci | archivio |",
            "|---|---|---|---|---|---|",
        ]
        righe += [
            f"| {r.nome} | {r.lotto} | {r.data_prova} | {r.commit} | {r.voci} "
            f"| {celle(r.archivio)} |"
            for r in registrazioni
        ]
        righe += ["", "## Totali per categoria", "", *tabella_totali(registrazioni)]

        avvisi = [f"- {r.nome}: {a}" for r in registrazioni for a in r.avvisi]
        if len({r.archivio for r in registrazioni}) > 1:
            avvisi.insert(
                0,
                "- registrazioni su archivi diversi: i totali per categoria non "
                "sono una misura appaiata",
            )
        if avvisi:
            righe += ["", "## Avvisi", "", *avvisi]

        vietate = [
            d
            for r in registrazioni
            for d in r.diagnosi
            if d.categoria == VIETATA_CITATA
        ]
        righe += ["", "## Vietate citate", ""]
        righe += [f"- {d.registrazione} {d.codice}: {d.testo}" for d in vietate] or [
            "Nessuna."
        ]

        da_controllare = [
            d for r in registrazioni for d in r.diagnosi if d.categoria == ARCHIVIO
        ]
        righe += ["", "## Da controllare a mano (archivio)", ""]
        righe += [
            f"- {d.registrazione} {d.codice}: {d.testo}" for d in da_controllare
        ] or ["Nessuna."]

        for r in registrazioni:
            righe += ["", f"## {r.nome} (data della prova {r.data_prova})", ""]
            righe += tabella_diagnosi(r.diagnosi) if r.diagnosi else ["Nessuna attesa."]

    if titoli:
        righe += [
            "",
            f"## Titoli cercati (--titolo), stato al {titoli[0].data_prova}",
            "",
            "| titolo | titoli in archivio (stato) | categoria |",
            "|---|---|---|",
        ]
        righe += [
            f"| {celle(d.testo)} | {cella_titoli(d.titoli)} | **{d.categoria}** |"
            for d in titoli
        ]
    return "\n".join(righe) + "\n"


def scrivi_uscita(
    cartella: Path, registrazioni: list[Registrazione], titoli: list[Diagnosi]
) -> Path:
    """Scrive rapporto.md e diagnosi.csv in cartella, creandola."""
    cartella.mkdir(parents=True, exist_ok=True)
    tutte = [d for r in registrazioni for d in r.diagnosi] + titoli
    scrivi_csv(cartella / "diagnosi.csv", tutte)
    (cartella / "rapporto.md").write_text(
        rapporto(registrazioni, titoli, adesso().isoformat(timespec="seconds")),
        encoding="utf-8",
    )
    return cartella


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("cartelle", nargs="*", type=Path, help="registrazioni")
    parser.add_argument(
        "--titolo",
        action="append",
        default=[],
        help="controlla solo l'archivio per questo titolo (ripetibile)",
    )
    argomenti = parser.parse_args(argv)
    if not argomenti.cartelle and not argomenti.titolo:
        parser.error("serve almeno una cartella di registrazione o un --titolo")
    return argomenti


def main(argv: list[str] | None = None) -> Path:
    argomenti = leggi_argomenti(argv)
    with ExitStack() as contesti:
        vero = []
        archivi = {}

        def connessione_vera() -> sqlite3.Connection:
            """comune.sqlite, aperto solo se serve."""
            if not vero:
                vero.append(apri_in_lettura())
                contesti.callback(vero[0].close)
            return vero[0]

        registrazioni = []
        for c in argomenti.cartelle:
            meta = leggi_meta(c)
            if not meta.get("archivio"):
                registrazioni.append(diagnosi_cartella(connessione_vera(), c))
                continue
            impronta = meta.get("impronta_csv") or {}
            chiave = (meta["archivio"], impronta.get("complessiva"))
            if chiave not in archivi:
                archivi[chiave] = contesti.enter_context(
                    database_dell_archivio(Path(meta["archivio"]), impronta)
                )
            conn, avvisi = archivi[chiave]
            r = diagnosi_cartella(conn, c)
            r.avvisi = [*avvisi, *r.avvisi]
            registrazioni.append(r)
        oggi = data_di_oggi().isoformat()
        titoli = [
            diagnosi_titolo(connessione_vera(), t, oggi) for t in argomenti.titolo
        ]
    cartella = scrivi_uscita(
        CARTELLA_DIAGNOSI / nome_cartella(adesso()), registrazioni, titoli
    )
    print(f"Rapporto: {cartella / 'rapporto.md'}")
    print(f"CSV: {cartella / 'diagnosi.csv'}")
    return cartella


if __name__ == "__main__":
    try:
        main()
    except ErroreDiagnosi as errore:
        print(f"Errore: {errore}")
        sys.exit(1)
