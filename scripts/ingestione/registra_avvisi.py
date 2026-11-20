"""Registro dei PDF degli avvisi scaricati (passo 19, compito 19c-2).

Uso:
    python -u -m scripts.ingestione.registra_avvisi --data 2026-11-19
    python -u -m scripts.ingestione.registra_avvisi --data 2026-11-19 --controlla

Legge elenco.csv e richieste.csv di dati-grezzi/avvisi/<data>/ e scrive
data/processed/documenti_bandi.csv: una riga per impronta (sha256) di
file scaricato. Nessuna richiesta di rete: si leggono solo i file su
disco. --controlla confronta con il file esistente senza scrivere.

Colonne:
- sha256: l'impronta del file;
- id_bandi: i bandi che rimandano al file, ordinati e separati da "|";
- classe: avviso, consolidato, proroga, allegato, elenco_codici,
  presentazione;
- uso: "frammenti" (si divide e va nell'archivio dei documenti, 19c-3) o
  "solo_registro";
- parte: per un avviso in più parti, la parte (dal testo di pagina 1);
- atto: l'atto del file, dal nome del file o, per decisione a mano, dal
  titolo della prima pagina; mai da bandi.riferimento_atto (quello dei
  punti digitale cita ancora il decreto superato); atto_origine dice da
  dove;
- url_file, url_pagina, nome_file, atto: un valore per bando, nell'ordine
  di id_bandi, separati da "|" (lo stesso file ha un indirizzo e un nome
  diverso per ogni bando);
- pagine: le pagine del PDF;
- scaricato_il, eccezione_robots: dal registro delle richieste ("sì" se
  il file era vietato dal robots.txt e si è scaricato per la regola del
  progetto sugli avvisi);
- deciso_da ("script" o "a mano"), motivo, deciso_il;
- sostituisce: l'impronta della versione precedente, se c'è.

Classe e uso:
- per i file in DECISIONI_A_MANO, quelli scritti lì;
- un file segnato "avviso in più parti" da elenco_pdf_bandi: classe
  avviso, uso frammenti, parte dal testo;
- una proroga: uso frammenti;
- un avviso o un consolidato con le sezioni di un avviso, secondo la
  stessa regola di elenco_pdf_bandi (pdf_bando.e_avviso): uso frammenti;
- ogni altro file ferma lo script: va deciso a mano.

Lo script si ferma senza scrivere se un file dell'elenco non è su disco,
se la sua impronta o le sue pagine non sono quelle dell'elenco, se manca
la sua richiesta in richieste.csv o i byte non tornano, se una decisione
a mano non trova il suo file, o se un file per più bandi andrebbe diviso
in frammenti (decisione del 20/11/2026: per ora si rifiuta).

Il file non contiene la data dell'esecuzione: con gli stessi ingressi
esce uguale byte per byte.
"""

import argparse
import csv
import io
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import pypdf

from scripts.ingestione.elenco_pdf_bandi import (
    AVVISO_IN_PIU_PARTI,
    cartella_di,
    cartella_file,
    nome_del_file,
)
from src.config import PROCESSED_DIR
from src.estrazione import pdf_bando as pb

NOME_FILE = "documenti_bandi.csv"

COLONNE = [
    "sha256",
    "id_bandi",
    "classe",
    "uso",
    "parte",
    "atto",
    "atto_origine",
    "url_file",
    "url_pagina",
    "nome_file",
    "pagine",
    "scaricato_il",
    "eccezione_robots",
    "deciso_da",
    "motivo",
    "deciso_il",
    "sostituisce",
]

SEPARATORE = "|"
FRAMMENTI = "frammenti"
SOLO_REGISTRO = "solo_registro"
ELENCO_CODICI = "elenco_codici"
PRESENTAZIONE = "presentazione"
SCRIPT = "script"
A_MANO = "a mano"
NOTA_ECCEZIONE = "vietato dal robots.txt"


@dataclass(frozen=True)
class Decisione:
    """Una decisione a mano su un file, riconosciuto dall'impronta."""

    file: str  # promemoria per chi legge: il file come si chiama su disco
    classe: str
    uso: str
    motivo: str
    deciso_il: str
    # L'atto preso dal titolo della prima pagina, quando il nome del file non
    # si legge: pezzi del testo di pagina 1, uniti con ", ". Lo script
    # controlla che ogni pezzo compaia nella pagina (spazi e maiuscole a
    # parte) e scrive atto_origine "prima pagina del file".
    atto_prima_pagina: tuple[str, ...] = ()


# Decisioni a mano (verifica del 19/11/2026 in docs/coda.md, passo 19,
# "Verifica a mano dei PDF"; decisioni del 20/11/2026 sul compito 19c-2).
DECISIONI_A_MANO = {
    "aa0d0bd1b0192161369309f812926f41f9d9d632dab6a829038d17b9bc746bb1": Decisione(
        "testo-coordinato-bando-sra-aca-16b-8ac2656c.pdf",
        pb.CONSOLIDATO,
        FRAMMENTI,
        "testo coordinato del bando, 5 sezioni su 5; atto dal titolo della "
        "prima pagina, perché il nome del file non si legge",
        "2026-11-20",
        atto_prima_pagina=(
            "Allegato A",
            (
                'SRA16-ACA16.B "Recupero, caratterizzazione, monitoraggio, '
                "valorizzazione e tutela delle risorse genetiche locali a rischio "
                'di estinzione"'
            ),
            "Bando - annualità 2026",
        ),
    ),
    "33fd1f31f1f4df657c9d433981aa3534f4ba90010ea8cc893289fab792d4d15b": Decisione(
        "avviso_pubblico_prot_26286_del_03_11_2026-74a82f09.pdf",
        pb.AVVISO,
        FRAMMENTI,
        "il PDF del MIT è l'avviso, anche con 2 sezioni su 5 (verifica a mano)",
        "2026-11-19",
    ),
    "76235291c283eb5927bd64b002cb8a77eb8f045b76061352ffcf9ea11aead518": Decisione(
        "presentazione-vcc-sportello_beneficiari-bb991ad7.pdf",
        PRESENTAZIONE,
        SOLO_REGISTRO,
        "presentazione del ministero, non l'avviso (verifica a mano)",
        "2026-11-19",
    ),
    "044e2481a87058b6c2f4d17dcd63b04134a3dd48269fed05520366274ea13bb9": Decisione(
        "decreto_n-9505_del_30-04-2026-allegato-5-a0bbd55d.pdf",
        pb.ALLEGATO,
        SOLO_REGISTRO,
        "Allegato 5 Obblighi di pubblicità: falso positivo tra gli allegati "
        "richiamati per beneficiari o ATECO",
        "2026-11-19",
    ),
    "ad1962a982b9d7c340ef49be65a3c9b2479cadaf1fee25c621a60915b5135064": Decisione(
        "decreto_n-9506_del_30-04-2026-allegato-5-8c67f937.pdf",
        pb.ALLEGATO,
        SOLO_REGISTRO,
        "Allegato 5 Obblighi di pubblicità: falso positivo tra gli allegati "
        "richiamati per beneficiari o ATECO",
        "2026-11-19",
    ),
    "ba3fda061179274ec660f088650c411738c894bcc5c501c06f86e1e7f2c07e37": Decisione(
        "decreto_n-9505_del_30-04-2026-allegato-4 e 9506 allegato 4 (stesso file)",
        ELENCO_CODICI,
        SOLO_REGISTRO,
        "elenco di soli codici ATECO e NACE: non si divide in frammenti",
        "2026-11-20",
    ),
    "366dd59b5a42a6d1e41d0e990cc53fc6ad28aa61fc5bbd4fea362f020560242b": Decisione(
        "decreto_n-9505_del_30-04-2026-allegato-1b-54f077dd.pdf",
        pb.ALLEGATO,
        SOLO_REGISTRO,
        "allegato richiamato (progetti green): solo registro, per ora",
        "2026-11-20",
    ),
    "04af40f47cf7ec53fddaf216082ecd3a78d9c8dbce9fbd19c4bd7ad7899d35a6": Decisione(
        "all--d-convenzione-modalita-operative-contributi-fci-cmc2026-78c4faeb.pdf",
        pb.ALLEGATO,
        SOLO_REGISTRO,
        "allegato richiamato (convenzione): solo registro, per ora",
        "2026-11-20",
    ),
    "d1650982b790ac24ba5a99e3635c5ae97867924353398742171e90fb133e74a4": Decisione(
        "all--b-regolamento-fondo-contibuti-interessi-sport-9e92e049.pdf",
        pb.ALLEGATO,
        SOLO_REGISTRO,
        "allegato richiamato (regolamento del fondo): solo registro, per ora",
        "2026-11-20",
    ),
    "db280083618b7f5d2768ce418e3825513156be6fb6a751cbf14c877920285848": Decisione(
        "all--d-convenzione-modalita-operative-erogazione-contributi-23f4e4a6.pdf",
        pb.ALLEGATO,
        SOLO_REGISTRO,
        "allegato richiamato (convenzione): solo registro, per ora",
        "2026-11-20",
    ),
}

# Atto dal nome del file: decreto della Regione e protocollo del MIT
DECRETO = re.compile(
    r"Decreto\s+n\.?\s*(\d+)\s+del\s+(\d{1,2})-(\d{1,2})-(\d{4})[\s-]*"
    r"Allegato[\s-]*([A-Za-z0-9]+)",
    re.IGNORECASE,
)
PROTOCOLLO = re.compile(
    r"avviso\s+pubblico\s+prot\s+(\d+)\s+del\s+(\d{2})\s+(\d{2})\s+(\d{4})",
    re.IGNORECASE,
)
DA_NOME_DECRETO = "nome del file: decreto"
DA_NOME_PROTOCOLLO = "nome del file: protocollo"
DA_NOME_TITOLO = "nome del file: titolo, senza numero d'atto"
DA_PRIMA_PAGINA = "prima pagina del file"

# La parte di un avviso in più parti, dalla prima pagina ("Azione B1")
PARTE = re.compile(r"\bAzione\s+(B\d+)\b")


class ErroreRegistro(Exception):
    """Un ingresso che non torna: si riporta, non si indovina."""


def nome_originale(url_file: str) -> str:
    """Il nome del documento nel link, come lo calcola elenco_pdf_bandi."""
    nome = pb.nome_del_documento(urlsplit(url_file))
    if nome is None:
        raise ErroreRegistro(f"link senza nome di documento: {url_file}")
    return nome


def atto_dal_nome(nome: str) -> tuple[str, str]:
    """L'atto e la sua origine dal nome del documento nel link."""
    base = re.sub(r"\.(pdf|p7m)$", "", nome, flags=re.IGNORECASE)
    base = " ".join(re.sub(r"[_+]+", " ", base).split())
    m = DECRETO.search(base)
    if m:
        numero, giorno, mese, anno, allegato = m.groups()
        return (
            (
                f"Decreto n. {numero} del {int(giorno):02d}/{int(mese):02d}/{anno}, "
                f"Allegato {allegato.upper()}"
            ),
            DA_NOME_DECRETO,
        )
    m = PROTOCOLLO.search(base)
    if m:
        numero, giorno, mese, anno = m.groups()
        return (
            f"Avviso pubblico prot. {numero} del {giorno}/{mese}/{anno}",
            DA_NOME_PROTOCOLLO,
        )
    return " ".join(base.replace("-", " ").split()), DA_NOME_TITOLO


def _per_confronto(testo: str) -> str:
    return " ".join(testo.split()).casefold()


def atto_dalla_prima_pagina(
    f: "FileScaricato", decisione: Decisione
) -> tuple[str, str]:
    """L'atto dai pezzi della decisione, dopo averli trovati a pagina 1."""
    pagina = _per_confronto(pagine_pdf(f.percorso)[0])
    for pezzo in decisione.atto_prima_pagina:
        if _per_confronto(pezzo) not in pagina:
            raise ErroreRegistro(
                f"{f.percorso.name}: '{pezzo}' non è nella prima pagina del file"
            )
    return ", ".join(decisione.atto_prima_pagina), DA_PRIMA_PAGINA


def leggi_csv(percorso: Path) -> list[dict]:
    if not percorso.is_file():
        raise ErroreRegistro(f"file non trovato: {percorso}")
    with percorso.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def richieste_dei_file(righe: list[dict]) -> dict[str, dict]:
    """La prima richiesta riuscita di ogni file, per indirizzo."""
    trovate: dict[str, dict] = {}
    for riga in righe:
        if riga["tipo"] == "file" and riga["esito"] == "ok":
            trovate.setdefault(riga["url"], riga)
    return trovate


def pagine_pdf(percorso: Path) -> list[str]:
    """I testi delle pagine, letti come li legge elenco_pdf_bandi."""
    from src.ingestion.pdf_ingest import carica_pdf

    return [p.page_content for p in carica_pdf(percorso)]


@dataclass
class FileScaricato:
    """Una riga di elenco.csv con il suo file su disco."""

    riga: dict
    percorso: Path
    nome_originale: str
    richiesta: dict


def file_dell_elenco(cartella: Path) -> list[FileScaricato]:
    """Le righe di elenco.csv con un file, verificate sul disco e sulle richieste."""
    elenco = leggi_csv(cartella / "elenco.csv")
    richieste = richieste_dei_file(leggi_csv(cartella / "richieste.csv"))
    trovati = []
    for riga in elenco:
        if not riga["sha256"]:
            continue
        originale = nome_originale(riga["url_file"])
        percorso = cartella_file(cartella, riga["id_bando"]) / nome_del_file(
            riga["url_file"], originale
        )
        dove = f"{riga['id_bando']} #{riga['n']}"
        if not percorso.is_file():
            raise ErroreRegistro(f"{dove}: file non trovato su disco: {percorso}")
        impronta = pb.impronta_file(percorso)
        if impronta != riga["sha256"]:
            raise ErroreRegistro(
                f"{dove}: impronta diversa da quella dell'elenco "
                f"({impronta[:12]} invece di {riga['sha256'][:12]})"
            )
        richiesta = richieste.get(riga["url_file"])
        if richiesta is None:
            raise ErroreRegistro(f"{dove}: nessuna richiesta riuscita in richieste.csv")
        if int(richiesta["byte"]) != percorso.stat().st_size:
            raise ErroreRegistro(
                f"{dove}: {percorso.stat().st_size} byte su disco, "
                f"{richiesta['byte']} nel registro delle richieste"
            )
        pagine = len(pypdf.PdfReader(str(percorso)).pages)
        if str(pagine) != riga["pagine"]:
            raise ErroreRegistro(
                f"{dove}: {pagine} pagine, {riga['pagine']} nell'elenco"
            )
        trovati.append(FileScaricato(riga, percorso, originale, richiesta))
    return trovati


def decisione_dello_script(f: FileScaricato, data: str) -> tuple[dict, str]:
    """Classe, uso, motivo e data dalle regole; e la parte, per un avviso in più parti."""
    riga = f.riga
    if AVVISO_IN_PIU_PARTI in riga["sezioni"]:
        testo = pagine_pdf(f.percorso)[0]
        m = PARTE.search(testo)
        if not m:
            raise ErroreRegistro(
                f"{f.percorso.name}: avviso in più parti senza 'Azione Bn' a pagina 1"
            )
        return {
            "classe": pb.AVVISO,
            "uso": FRAMMENTI,
            "motivo": f"{AVVISO_IN_PIU_PARTI} (elenco_pdf_bandi)",
            "deciso_il": data,
        }, f"Azione {m.group(1)}"
    if riga["classe"] == pb.PROROGA:
        return {
            "classe": pb.PROROGA,
            "uso": FRAMMENTI,
            "motivo": "proroga del termine",
            "deciso_il": data,
        }, ""
    if riga["classe"] in pb.CLASSI_DI_AVVISO:
        sezioni = pb.sezioni_avviso(pagine_pdf(f.percorso))
        avviso, nota = pb.e_avviso(sezioni, riga["classe"], riga["giudizio"])
        if avviso:
            motivo = f"{len(sezioni.trovate)} sezioni su {len(pb.SEZIONI)}"
            return {
                "classe": riga["classe"],
                "uso": FRAMMENTI,
                "motivo": motivo + (f"; {nota}" if nota else ""),
                "deciso_il": data,
            }, ""
    raise ErroreRegistro(
        f"{riga['id_bando']} #{riga['n']} ({f.percorso.name}, sha256 "
        f"{riga['sha256'][:12]}): nessuna regola lo decide, va in DECISIONI_A_MANO"
    )


def costruisci(cartella: Path, data: str) -> list[dict]:
    """Le righe del registro, ordinate, dai file dell'elenco di una cartella."""
    scaricati = file_dell_elenco(cartella)
    per_impronta: dict[str, list[FileScaricato]] = {}
    for f in scaricati:
        per_impronta.setdefault(f.riga["sha256"], []).append(f)

    usate = set(DECISIONI_A_MANO) & set(per_impronta)
    for impronta in sorted(set(DECISIONI_A_MANO) - usate):
        raise ErroreRegistro(
            f"decisione a mano senza file nell'elenco: {impronta[:12]} "
            f"({DECISIONI_A_MANO[impronta].file})"
        )

    righe = []
    for impronta, copie in per_impronta.items():
        copie = sorted(copie, key=lambda f: f.riga["id_bando"])
        id_bandi = [f.riga["id_bando"] for f in copie]
        if len(set(id_bandi)) != len(id_bandi):
            raise ErroreRegistro(
                f"{impronta[:12]}: lo stesso file due volte per un bando"
            )
        decisione = DECISIONI_A_MANO.get(impronta)
        if decisione:
            scelta = {
                "classe": decisione.classe,
                "uso": decisione.uso,
                "motivo": decisione.motivo,
                "deciso_il": decisione.deciso_il,
            }
            parte, deciso_da = "", A_MANO
        else:
            scelte = [decisione_dello_script(f, data) for f in copie]
            scelta, parte = scelte[0]
            if any(s != scelte[0] for s in scelte):
                raise ErroreRegistro(f"{impronta[:12]}: regole diverse per i bandi")
            deciso_da = SCRIPT
        if scelta["uso"] == FRAMMENTI and len(copie) > 1:
            raise ErroreRegistro(
                f"{impronta[:12]}: un file per {len(copie)} bandi da dividere in "
                "frammenti: per ora non si fa (decisione del 20/11/2026)"
            )

        if decisione and decisione.atto_prima_pagina:
            atti = [atto_dalla_prima_pagina(f, decisione) for f in copie]
        else:
            atti = [atto_dal_nome(f.nome_originale) for f in copie]
        origini = {origine for _, origine in atti}
        date = {f.richiesta["ora"][:10] for f in copie}
        eccezioni = {
            "sì" if f.richiesta["nota"].startswith(NOTA_ECCEZIONE) else "no"
            for f in copie
        }
        for nome, valori in (
            ("origine dell'atto", origini),
            ("data di scarico", date),
            ("eccezione al robots.txt", eccezioni),
        ):
            if len(valori) > 1:
                raise ErroreRegistro(f"{impronta[:12]}: {nome} diversa tra i bandi")

        righe.append(
            {
                "sha256": impronta,
                "id_bandi": SEPARATORE.join(id_bandi),
                **{k: scelta[k] for k in ("classe", "uso")},
                "parte": parte,
                "atto": SEPARATORE.join(a for a, _ in atti),
                "atto_origine": origini.pop(),
                "url_file": SEPARATORE.join(f.riga["url_file"] for f in copie),
                "url_pagina": SEPARATORE.join(f.riga["url_pagina"] for f in copie),
                "nome_file": SEPARATORE.join(f.percorso.name for f in copie),
                "pagine": copie[0].riga["pagine"],
                "scaricato_il": date.pop(),
                "eccezione_robots": eccezioni.pop(),
                "deciso_da": deciso_da,
                "motivo": scelta["motivo"],
                "deciso_il": scelta["deciso_il"],
                "sostituisce": "",
            }
        )
    return sorted(righe, key=lambda r: (r["id_bandi"], r["nome_file"]))


def in_byte(righe: list[dict]) -> bytes:
    """Il contenuto del file: UTF-8 con BOM e fine riga \\r\\n, come gli altri CSV."""
    buffer = io.StringIO(newline="")
    scrittore = csv.DictWriter(buffer, fieldnames=COLONNE, lineterminator="\r\n")
    scrittore.writeheader()
    for riga in righe:
        scrittore.writerow(riga)
    return buffer.getvalue().encode("utf-8-sig")


def totali(righe: list[dict]) -> tuple[int, int]:
    """File e pagine con uso "frammenti"."""
    da_dividere = [r for r in righe if r["uso"] == FRAMMENTI]
    return len(da_dividere), sum(int(r["pagine"]) for r in da_dividere)


def leggi_argomenti(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--data", required=True, help="la cartella dati-grezzi/avvisi/<AAAA-MM-GG>"
    )
    parser.add_argument(
        "--controlla",
        action="store_true",
        help="confronta con il file esistente, senza scrivere",
    )
    return parser.parse_args(argv)


def main(
    argv: list[str] | None = None,
    cartella_avvisi: Path | None = None,
    cartella_processed: Path | None = None,
) -> int:
    argomenti = leggi_argomenti(argv)
    cartella = cartella_avvisi or cartella_di(argomenti.data)
    destinazione = (cartella_processed or PROCESSED_DIR) / NOME_FILE
    try:
        righe = costruisci(cartella, argomenti.data)
    except ErroreRegistro as errore:
        print(f"Errore: {errore}", file=sys.stderr)
        return 1

    contenuto = in_byte(righe)
    file_frammenti, pagine_frammenti = totali(righe)
    riepilogo = (
        f"{len(righe)} file; uso frammenti: {file_frammenti} file, "
        f"{pagine_frammenti} pagine"
    )
    if argomenti.controlla:
        if destinazione.is_file() and destinazione.read_bytes() == contenuto:
            print(f"{destinazione.name}: aggiornato ({riepilogo})")
            return 0
        print(f"{destinazione.name}: diverso o mancante ({riepilogo})", file=sys.stderr)
        return 1

    destinazione.write_bytes(contenuto)
    print(f"{destinazione.name}: scritto ({riepilogo})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
