"""Estrae in sequenza i bandi nuovi trovati sul portale.

Uso:
    python -u -m scripts.ingestione.estrai_nuovi --prova          mostra cosa farebbe
    python -u -m scripts.ingestione.estrai_nuovi --limite 10      estrae i primi 10
    python -u -m scripts.ingestione.estrai_nuovi --promettenti    solo quelli con indizi
    python -u -m scripts.ingestione.estrai_nuovi --tutti-gli-anni senza filtro sull'anno

L'opzione -u di Python disattiva l'accumulo dell'output, cosi' le righe
compaiono man mano invece che tutte alla fine.

Ogni bando costa una chiamata all'API. Le pagine gia' esaminate con esito
definitivo (scadute, o che non sono bandi) non vengono riproposte: il
registro delle scansioni le ricorda.

Prima del modello, una preselezione gratuita (src/estrazione/scadenza.py)
scarica ogni pagina candidata:
- se il campo "Data di scadenza presentazione domande" e' passato da piu'
  di un anno, la pagina si registra come scaduta senza modello;
- se il campo manca o non si legge e lo slug ha un anno passato, la
  pagina si salta, senza registrarla. --tutti-gli-anni disattiva questo
  filtro, e segna le pagine che avrebbe saltato: il riepilogo finale ne
  mostra gli esiti, per misurare quanti bandi aperti il filtro perde.
Con --prova la preselezione si esegue ma non registra nulla, e si stima
il costo delle estrazioni rimaste.

Alla fine si stampano i token consumati e il loro costo.
"""

import sys
import time
from datetime import datetime
from http.client import HTTPException
from zoneinfo import ZoneInfo

from anthropic import AuthenticationError, PermissionDeniedError
from langchain_core.callbacks import get_usage_metadata_callback

from src.database.schema import aggiorna_csv
from src.estrazione.bandi import (
    costruisci_estrattore,
    decidi_automatico,
    estrai,
    valida,
)
from src.estrazione.elenco import id_da_slug, scopri
from src.estrazione.pagina import a_testo, ritaglia, scarica
from src.estrazione.registro import da_non_riesaminare, registra, riepilogo
from src.estrazione.salva import salva
from src.estrazione.scadenza import (
    AL_MODELLO,
    ANNO_PASSATO,
    SCADUTO,
    motivo_scaduto,
    preselezione,
)

FONTE = "Portale bandi Regione Toscana"
PAUSA = 1.0
# Pausa tra i download della preselezione, che non chiama il modello
PAUSA_PAGINE = 0.5

# Costo misurato di un'estrazione con claude-sonnet-5, in dollari: una
# pagina che e' un bando, e una che non lo e'. Nella scansione completa
# dell'11 novembre 2026 il costo e' stato circa 0,031 $ a pagina, bando o
# no (roadmap, "In coda"). Prima erano 0,026 e 0,012 (piano-estrattore.md,
# tappa b).
COSTO_BANDO = 0.031
COSTO_NON_BANDO = 0.031

# Prezzi di claude-sonnet-5 in dollari per milione di token (listino
# Anthropic, controllato l'11 novembre 2026)
PREZZO_INGRESSO = 2.0
PREZZO_USCITA = 10.0


def opzione(nome: str, predefinito: int) -> int:
    """Legge un'opzione numerica da riga di comando."""
    if nome not in sys.argv:
        return predefinito

    posizione = sys.argv.index(nome)
    if posizione + 1 >= len(sys.argv):
        return predefinito

    try:
        return int(sys.argv[posizione + 1])
    except ValueError:
        return predefinito


def scegli_candidati() -> list:
    """I bandi da esaminare, applicando i filtri richiesti."""
    voci = scopri()
    candidati = [v for v in voci if v.nuovo]
    print(f"Nuovi rispetto all'archivio: {len(candidati)}")

    esclusi = da_non_riesaminare()
    prima = len(candidati)
    candidati = [v for v in candidati if v.url not in esclusi]

    if prima != len(candidati):
        print(f"  gia' esaminati con esito definitivo: {prima - len(candidati)}")

    if "--promettenti" in sys.argv:
        candidati = [v for v in candidati if v.promettente]
        print(f"  con indizi di pertinenza: {len(candidati)}")

    return candidati


def avrebbe_saltato(voce, esito: str, scadenza, filtro_anni: bool) -> bool:
    """La pagina va al modello solo perche' il filtro sull'anno e' spento.

    Vero se, con il filtro attivo, la preselezione l'avrebbe saltata:
    campo della scadenza assente o illeggibile e anno passato nello slug.
    """
    return (
        not filtro_anni
        and esito == AL_MODELLO
        and scadenza is None
        and not voce.recente
    )


def preseleziona(candidati: list, prova: bool) -> tuple[list[tuple], set[str]]:
    """Scarica le pagine e toglie, senza modello, quelle da non estrarre.

    Restituisce (voce, testo ritagliato) per le pagine da mandare al
    modello, e gli slug di quelle che il filtro sull'anno avrebbe
    saltato (vuoto se il filtro e' attivo). Gli scaduti letti dal campo
    si registrano, salvo in prova. Una pagina che non si scarica va al
    modello con testo None: esamina riprova a scaricarla e, se fallisce
    ancora, la registra come fallita.
    """
    filtro_anni = "--tutti-gli-anni" not in sys.argv
    oggi = datetime.now(ZoneInfo("Europe/Rome")).date()
    al_modello, scaduti, anni_passati = [], 0, 0
    dal_filtro = set()

    print(f"\nPreselezione senza modello di {len(candidati)} pagine...")
    for v in candidati:
        try:
            completo = a_testo(scarica(v.url))
        except (OSError, HTTPException) as errore:
            print(f"  {v.slug[:60]}: pagina non scaricata ({errore})")
            al_modello.append((v, None))
            continue

        esito, scadenza = preselezione(completo, v.recente, oggi, filtro_anni)
        if esito == SCADUTO:
            scaduti += 1
            print(f"  {v.slug[:60]}: {motivo_scaduto(scadenza)}")
            if not prova:
                registra(
                    v.url, v.codice_fonte, v.slug, "scartato", motivo_scaduto(scadenza)
                )
        elif esito == ANNO_PASSATO:
            anni_passati += 1
        else:
            al_modello.append((v, ritaglia(completo)))
            if avrebbe_saltato(v, esito, scadenza, filtro_anni):
                dal_filtro.add(v.slug)
        time.sleep(PAUSA_PAGINE)

    print(f"  scaduti secondo il campo della pagina: {scaduti}")
    if filtro_anni:
        print(f"  saltati per l'anno nello slug, senza campo leggibile: {anni_passati}")
    else:
        print(
            "  con l'anno passato nello slug e senza campo leggibile, "
            f"che il filtro avrebbe saltato: {len(dal_filtro)}"
        )
    print(f"  da mandare al modello: {len(al_modello)}")
    return al_modello, dal_filtro


def stima_costo(quanti: int) -> str:
    """Il costo stimato di quanti estrazioni: tutte non bandi o tutte bandi."""
    return (
        f"tra {quanti * COSTO_NON_BANDO:.2f} $ (se nessuno fosse un bando) "
        f"e {quanti * COSTO_BANDO:.2f} $ (se tutti lo fossero)"
    )


def errore_bloccante(errore: Exception) -> bool:
    """Credito esaurito o autenticazione rifiutata: inutile proseguire.

    Ogni estrazione successiva fallirebbe allo stesso modo, e registrare
    le pagine come fallite confonderebbe un problema dell'account con un
    problema della pagina.
    """
    if isinstance(errore, (AuthenticationError, PermissionDeniedError)):
        return True
    testo = str(errore).lower()
    return "credit balance" in testo or "authentication" in testo


def costo_reale(uso: dict) -> tuple[int, int, float]:
    """Token in ingresso, in uscita e costo in dollari.

    uso: il dizionario usage_metadata del contatore di LangChain, una
    voce per modello.
    """
    ingresso = sum(u.get("input_tokens", 0) for u in uso.values())
    uscita = sum(u.get("output_tokens", 0) for u in uso.values())
    costo = (ingresso * PREZZO_INGRESSO + uscita * PREZZO_USCITA) / 1_000_000
    return ingresso, uscita, costo


def mostra_costo(uso: dict, estrazioni: int) -> None:
    """Stampa i token consumati e il costo, in tutto e per estrazione."""
    ingresso, uscita, costo = costo_reale(uso)
    print(f"\nTOKEN: ingresso {ingresso}, uscita {uscita}; costo {costo:.3f} $")
    if estrazioni:
        print(
            f"  per estrazione ({estrazioni}): ingresso {ingresso // estrazioni}, "
            f"uscita {uscita // estrazioni}, costo {costo / estrazioni:.4f} $"
        )


def esamina(estrattore, voce, testo: str | None) -> tuple[str, str, str]:
    """Estrae un bando e decide se salvarlo.

    testo: il testo della pagina, gia' scaricato dalla preselezione; se
    e' None la pagina si riscarica. Restituisce (esito, motivo, avvisi).
    Il motivo di un fallimento elenca tutti i problemi; gli avvisi i
    campi e le voci lasciati vuoti.
    """
    if testo is None:
        testo = ritaglia(a_testo(scarica(voce.url)))
    estrazione = estrai(estrattore, testo)
    riga, problemi, avvisi = valida(estrazione, testo)
    avvisi = "; ".join(avvisi)

    if problemi:
        return "fallito", "; ".join(problemi), avvisi

    riga["id"] = id_da_slug(voce.slug, voce.url)
    salvare, motivo = decidi_automatico(estrazione, riga)

    if salvare:
        salva(riga, voce.url, FONTE, voce.codice_fonte)
        return "salvato", motivo, avvisi

    return "scartato", motivo, avvisi


def mostra_dal_filtro(esiti: dict, dal_filtro: set[str]) -> None:
    """Gli esiti delle pagine che il filtro sull'anno avrebbe saltato."""
    if not dal_filtro:
        return

    righe = [
        (esito, slug, motivo)
        for esito, voci in esiti.items()
        for slug, motivo in voci
        if slug in dal_filtro
    ]
    print(
        f"\nPAGINE CHE IL FILTRO SULL'ANNO AVREBBE SALTATO: {len(dal_filtro)}, "
        f"esaminate {len(righe)}"
    )
    for esito in ("salvato", "scartato", "fallito"):
        scelte = [r for r in righe if r[0] == esito]
        print(f"  {esito}: {len(scelte)}")
        for _, slug, motivo in scelte:
            print(f"    {slug[:55]:55} {motivo[:60]}")


def mostra_riepilogo(esiti: dict) -> None:
    """Stampa il riepilogo finale, raggruppando gli scarti per motivo."""
    print("\n" + "=" * 74)
    print(
        f"RIEPILOGO: {len(esiti['salvato'])} salvati, "
        f"{len(esiti['scartato'])} scartati, "
        f"{len(esiti['fallito'])} falliti"
    )
    print("=" * 74)

    if esiti["salvato"]:
        print("\nSALVATI")
        for slug, motivo in esiti["salvato"]:
            print(f"  {slug[:55]:55} {motivo}")

    if esiti["fallito"]:
        print("\nFALLITI")
        for slug, motivo in esiti["fallito"]:
            print(f"  {slug[:55]:55} {motivo[:60]}")

    if esiti["scartato"]:
        print("\nScartati per motivo:")
        conteggio = {}
        for _, motivo in esiti["scartato"]:
            chiave = motivo.split(" il ")[0].split(" fino")[0]
            conteggio[chiave] = conteggio.get(chiave, 0) + 1
        for motivo, quanti in sorted(conteggio.items(), key=lambda x: -x[1]):
            print(f"  {quanti:3}  {motivo}")


def main() -> None:
    prova = "--prova" in sys.argv
    candidati, dal_filtro = preseleziona(scegli_candidati(), prova)
    candidati = candidati[: opzione("--limite", len(candidati))]

    print(f"\nCandidati da estrarre: {len(candidati)}")
    print(f"Costo stimato: {stima_costo(len(candidati))}")

    if prova:
        for v, _ in candidati:
            marca = "  [anno passato, senza campo]" if v.slug in dal_filtro else ""
            print(f"  {v.slug}{marca}")
        print("\nProva: nessuna estrazione eseguita, nulla registrato.")
        print(f"\n{riepilogo()}")
        return

    if not candidati:
        print("Nessun bando nuovo da esaminare.")
        print(f"\n{riepilogo()}")
        return

    estrattore = costruisci_estrattore()
    esiti = {"salvato": [], "scartato": [], "fallito": []}

    with get_usage_metadata_callback() as contatore:
        for numero, (v, testo) in enumerate(candidati, start=1):
            print(f"\n[{numero}/{len(candidati)}] {v.slug[:60]}")

            try:
                esito, motivo, avvisi = esamina(estrattore, v, testo)
            except Exception as errore:
                if errore_bloccante(errore):
                    # La pagina non e' fallita: non si registra, e alla
                    # prossima scansione torna candidata
                    print(
                        f"\nINTERROTTO: problema di credito o autenticazione ({errore})"
                    )
                    break
                esito, motivo, avvisi = "fallito", str(errore), ""

            esiti[esito].append((v.slug, motivo))
            registra(v.url, v.codice_fonte, v.slug, esito, motivo, avvisi)

            marca = "SALVATO" if esito == "salvato" else esito
            if v.slug in dal_filtro:
                marca += " [anno passato, senza campo]"
            print(f"    {marca} ({motivo[:70]})")
            if avvisi:
                print(f"    avvisi: {avvisi[:70]}")

            time.sleep(PAUSA)

    mostra_riepilogo(esiti)
    mostra_dal_filtro(esiti, dal_filtro)
    mostra_costo(contatore.usage_metadata, sum(len(e) for e in esiti.values()))
    print(f"\n{riepilogo()}")
    aggiorna_csv(
        "bandi", "beneficiari_bando", "interventi_bando", "scadenze_bando", "scansioni"
    )


if __name__ == "__main__":
    main()
