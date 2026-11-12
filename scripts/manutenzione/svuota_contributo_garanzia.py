"""Svuota contributo_perc del fondo di garanzia energie rinnovabili.

Uso:
    python -m scripts.manutenzione.svuota_contributo_garanzia

Script una tantum (docs/piano-post-scansione.md, tappa 5a.2). Nella
verifica a mano dell'11 novembre 2026 l'80% del bando risulta la quota
garantita del prestito, non la quota del costo coperta da un contributo.
Il valore veniva dall'estrattore vecchio ed era stato mantenuto dalla
fusione di riclassifica_bandi, perche' il nuovo lo lasciava vuoto.

E' una modifica ai dati verificati: alla fine riversa bandi nel CSV.
Rilanciarlo non cambia nulla.
"""

from src.database.schema import aggiorna_csv, connetti

ID_BANDO = "avviso-fondo-di-garanzia-energie-rinnovabili"


def svuota() -> str:
    """Svuota il campo e dice cosa e' successo."""
    conn = connetti()
    try:
        riga = conn.execute(
            "SELECT contributo_perc FROM bandi WHERE id = ?", (ID_BANDO,)
        ).fetchone()
        if riga is None:
            return "NON TROVATO"
        if riga["contributo_perc"] is None:
            return "gia' vuoto"
        conn.execute(
            "UPDATE bandi SET contributo_perc = NULL WHERE id = ?", (ID_BANDO,)
        )
        conn.commit()
        return f"svuotato (era {riga['contributo_perc']})"
    finally:
        conn.close()


def main() -> None:
    print(f"  {ID_BANDO}: {svuota()}")
    aggiorna_csv("bandi")


if __name__ == "__main__":
    main()
