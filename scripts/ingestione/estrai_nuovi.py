"""Estrae in sequenza i bandi nuovi trovati sul portale.

Uso:
    python -u -m scripts.estrai_nuovi --prova        mostra cosa farebbe
    python -u -m scripts.estrai_nuovi --limite 10    estrae i primi 10
    python -u -m scripts.estrai_nuovi --promettenti  solo quelli con indizi
    python -u -m scripts.estrai_nuovi --recenti      esclude gli anni passati

L'opzione -u di Python disattiva l'accumulo dell'output, cosi' le righe
compaiono man mano invece che tutte alla fine.

Ogni bando costa una chiamata all'API. Le pagine gia' esaminate con esito
definitivo (scadute, non pertinenti) non vengono riproposte: il registro
delle scansioni le ricorda.
"""

import sys
import time

from src.database.schema import aggiorna_csv
from src.estrazione.bandi import (
    costruisci_estrattore,
    decidi_automatico,
    estrai,
    valida,
)
from src.estrazione.elenco import scopri
from src.estrazione.pagina import prendi
from src.estrazione.registro import da_non_riesaminare, registra, riepilogo
from src.estrazione.salva import salva

FONTE = "Portale bandi Regione Toscana"
PAUSA = 1.0


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
    candidati = [v for v in candidati if v.slug not in esclusi]

    if prima != len(candidati):
        print(f"  gia' esaminati con esito definitivo: {prima - len(candidati)}")

    if "--promettenti" in sys.argv:
        candidati = [v for v in candidati if v.promettente]
        print(f"  con indizi di pertinenza: {len(candidati)}")

    if "--recenti" in sys.argv:
        candidati = [v for v in candidati if v.recente]
        print(f"  senza anni passati nel nome: {len(candidati)}")

    limite = opzione("--limite", len(candidati))
    return candidati[:limite]


def esamina(estrattore, voce) -> tuple[str, str]:
    """Estrae un bando e decide se salvarlo. Restituisce (esito, motivo)."""
    testo = prendi(voce.url)
    campi = estrai(estrattore, testo)
    riga, problemi = valida(campi)

    if problemi:
        return "fallito", "; ".join(problemi[:2])

    riga["id"] = voce.slug[:60]
    salvare, motivo = decidi_automatico(campi, riga)

    if salvare:
        salva(riga, voce.url, FONTE)
        return "salvato", motivo

    return "scartato", motivo


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
    candidati = scegli_candidati()

    print(f"\nCandidati da estrarre: {len(candidati)}")

    if "--prova" in sys.argv:
        for v in candidati:
            print(f"  {v.slug}")
        print("\nProva: nessuna estrazione eseguita.")
        print(f"\n{riepilogo()}")
        return

    if not candidati:
        print("Nessun bando nuovo da esaminare.")
        print(f"\n{riepilogo()}")
        return

    estrattore = costruisci_estrattore()
    esiti = {"salvato": [], "scartato": [], "fallito": []}

    for numero, v in enumerate(candidati, start=1):
        print(f"\n[{numero}/{len(candidati)}] {v.slug[:60]}")

        interrompi = False

        try:
            esito, motivo = esamina(estrattore, v)
        except Exception as errore:
            esito, motivo = "fallito", str(errore)[:100]
            testo = str(errore).lower()
            interrompi = "credit balance" in testo or "authentication" in testo

        esiti[esito].append((v.slug, motivo))
        registra(v.slug, esito, motivo[:100])

        marca = "SALVATO" if esito == "salvato" else esito
        print(f"    {marca} ({motivo[:70]})")

        if interrompi:
            print("\nINTERROTTO: problema di credito o autenticazione.")
            break

        time.sleep(PAUSA)

    mostra_riepilogo(esiti)
    print(f"\n{riepilogo()}")
    aggiorna_csv("bandi", "scansioni")


if __name__ == "__main__":
    main()
