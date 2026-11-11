"""Interrogazioni sui bandi: filtri per apertura, beneficiari e tema.

Chi puo' presentare domanda si ricava da beneficiari_bando, non si
memorizza nel bando. I bandi non ancora riclassificati con l'estrattore
nuovo (classificato_il vuoto) hanno solo la riga 'comune' migrata dal
vecchio campo si'/no: per loro si sa se ammettono i Comuni, non gli altri
tipi di beneficiari.
"""

import sqlite3
from datetime import date

from src.database.modelli import Risultato, VoceBando
from src.estrazione.beneficiari import PER_REQUISITO, TIPI_BENEFICIARIO

# Anni dalla pubblicazione oltre i quali un bando a sportello e' segnalato
# come probabilmente esaurito. Non si esclude: fondi di garanzia e rotativi
# restano attivi anche per anni.
SOGLIA_SPORTELLO_ANNI = 2

# Tipo di ente (tabella enti) -> tipo di beneficiario
TIPO_PER_ENTE = {"comune": "comune", "unione": "unione_comuni"}

# Come si nomina un tipo di ente nei testi
NOMI_ENTE = {
    "comune": {"uno": "un Comune", "tutti": "i Comuni", "plurale": "Comuni"},
    "unione_comuni": {
        "uno": "un'Unione di Comuni",
        "tutti": "le Unioni di Comuni",
        "plurale": "Unioni di Comuni",
    },
}

# Nome breve di ogni tipo di beneficiario, per le etichette
NOMI_TIPI = {
    "comune": "Comuni",
    "unione_comuni": "Unioni di comuni",
    "altro_ente_pubblico": "altri enti pubblici",
    "impresa_agricola": "imprese agricole",
    "impresa_turistica": "imprese turistiche",
    "impresa_artigiana_commerciale": "imprese artigiane e commerciali",
    "altra_impresa": "altre imprese",
    "terzo_settore": "terzo settore",
    "cittadini_famiglie": "cittadini e famiglie",
    "ricerca_formazione": "ricerca e formazione",
    "qualsiasi_soggetto": "chi ha i requisiti indicati",
}

NON_CLASSIFICATI = "altri beneficiari non ancora classificati"
NOTA_UNIONE = "beneficiari non ancora classificati: verificare se ammette le Unioni"

# Un bando senza scadenza e non a sportello: la pagina non dice fino a
# quando si puo' presentare domanda, e non si sa se e' ancora aperto
SENZA_SCADENZA = "scadenza non indicata, da verificare sul bando"
GRUPPO_SPORTELLO = "A sportello, finché ci sono risorse:"
GRUPPO_SENZA_SCADENZA = "Scadenza non indicata, da verificare sul bando:"

# Le pagine in archivio che non sono bandi (natura 'non_bando') restano
# nel database ma non compaiono negli elenchi ne' nei conteggi
SOLO_BANDI = "bandi.natura = 'bando'"

# Un bando ammette un tipo di beneficiario: ha una riga di quel tipo.
# Il tipo e' il parametro.
HA_TIPO = (
    "EXISTS (SELECT 1 FROM beneficiari_bando AS b "
    "WHERE b.id_bando = bandi.id AND b.tipo = ?)"
)


def filtro_ente(tipo: str) -> tuple[str, list]:
    """La condizione SQL dei bandi a cui un tipo di ente puo' partecipare.

    Ammette il bando una riga del suo tipo o di qualsiasi_soggetto. Per
    l'Unione valgono anche i bandi non ancora classificati che ammettono
    i Comuni: prima della migrazione li vedeva, e la nota li segnala.
    """
    sql = f"({HA_TIPO} OR {HA_TIPO})"
    parametri = [tipo, PER_REQUISITO]
    if tipo == "unione_comuni":
        sql = f"({sql} OR (bandi.classificato_il IS NULL AND {HA_TIPO}))"
        parametri.append("comune")
    return sql, parametri


def data_di_oggi() -> date:
    """La data di oggi: l'unico punto in cui le interrogazioni la leggono."""
    return date.today()


def tipo_ente(conn: sqlite3.Connection, codice_ente: str) -> str | None:
    """Il tipo di beneficiario corrispondente all'ente, se gestito."""
    riga = conn.execute(
        "SELECT tipo FROM enti WHERE codice_fiscale = ?", (codice_ente,)
    ).fetchone()
    return TIPO_PER_ENTE.get(riga["tipo"]) if riga else None


def _ente_non_gestito(codice_ente: str) -> Risultato:
    return Risultato(
        f"L'ente {codice_ente} non e' un Comune ne' un'Unione di Comuni in "
        "archivio: non so a quali bandi possa partecipare.",
        trovato=False,
    )


def beneficiari_di(conn: sqlite3.Connection, id_bando: str) -> list:
    """Le righe di beneficiari_bando di un bando, in ordine di tipo."""
    return conn.execute(
        "SELECT * FROM beneficiari_bando WHERE id_bando = ? ORDER BY tipo, frase",
        (id_bando,),
    ).fetchall()


def euro(valore) -> str:
    """Formatta un importo con il separatore di migliaia italiano.

    Python usa la convenzione americana con la virgola; qui serve il punto.
    """
    if not valore:
        return "?"
    return f"{valore:,.0f}".replace(",", ".")


def _anni_fa(oggi: str, anni: int) -> str:
    """La data di oggi spostata indietro di alcuni anni."""
    giorno = date.fromisoformat(oggi)
    try:
        return giorno.replace(year=giorno.year - anni).isoformat()
    except ValueError:  # 29 febbraio
        return giorno.replace(year=giorno.year - anni, day=28).isoformat()


def stato_sportello(riga, oggi: str) -> str:
    """Lo stato di un bando a sportello, con l'invito a verificare le risorse."""
    pubblicato = riga["pubblicato_il"]
    if riga["scadenza"]:
        testo = (
            f"a sportello fino al {riga['scadenza']}, "
            "verificare la disponibilità delle risorse"
        )
    else:
        quando = (
            f"pubblicato il {pubblicato}"
            if pubblicato
            else "data di pubblicazione non indicata"
        )
        testo = f"a sportello, verificare la disponibilità delle risorse ({quando})"

    if pubblicato and pubblicato < _anni_fa(oggi, SOGLIA_SPORTELLO_ANNI):
        testo += (
            f" | pubblicato da oltre {SOGLIA_SPORTELLO_ANNI} anni: "
            "probabilmente esaurito"
        )
    return testo


def ammissione(beneficiari: list, tipo: str) -> str | None:
    """Come e' ammesso un tipo di ente, se ci sono condizioni.

    Senza condizioni restituisce None: il bando e' nell'elenco perche'
    l'ente e' ammesso, e non serve dirlo. Con piu' righe, le condizioni
    si uniscono con "oppure". Per qualsiasi_soggetto si aggiunge, tra
    parentesi, il soggetto come lo chiama il bando.
    """
    pertinenti = [b for b in beneficiari if b["tipo"] in (tipo, PER_REQUISITO)]
    if not pertinenti or any(
        b["tipo"] == tipo and not b["condizioni"] for b in pertinenti
    ):
        return None

    casi = []
    for b in pertinenti:
        caso = f"ammesso se {b['condizioni']}"
        if b["tipo"] == PER_REQUISITO and b["soggetto"]:
            caso += f" (nel bando: «{b['soggetto']}»)"
        casi.append(caso)
    return " oppure ".join(casi)


def formatta_bando(riga, oggi: str, nota: str | None = None) -> str:
    """Una riga di bando in forma leggibile.

    nota: come e' ammesso l'ente, o perche' va verificato; si aggiunge
    dopo i beneficiari.
    """
    pezzi = [f"«{riga['titolo']}» ({riga['ente']})"]

    if riga["a_sportello"]:
        pezzi.append(stato_sportello(riga, oggi))
    elif riga["scadenza"]:
        giorni = (date.fromisoformat(riga["scadenza"]) - date.fromisoformat(oggi)).days
        stato = f"scade il {riga['scadenza']}"
        if giorni >= 0:
            stato += f" (fra {giorni} giorni)"
        else:
            stato += f" (SCADUTO da {abs(giorni)} giorni)"
        pezzi.append(stato)
    else:
        pezzi.append(SENZA_SCADENZA)

    if riga["scadenza_nota"]:
        pezzi.append(f"nota: {riga['scadenza_nota']}")

    pezzi.append(f"beneficiari: {riga['beneficiari']}")

    if nota:
        pezzi.append(nota)

    if riga["contributo_perc"]:
        pezzi.append(f"contributo fino al {riga['contributo_perc']:.0f}%")

    if riga["costo_min"] and riga["costo_max"]:
        pezzi.append(
            f"progetto ammissibile da {euro(riga['costo_min'])} "
            f"a {euro(riga['costo_max'])} euro"
        )
    elif riga["costo_max"]:
        pezzi.append(f"progetto fino a {euro(riga['costo_max'])} euro")
    elif riga["costo_min"]:
        pezzi.append(f"progetto da almeno {euro(riga['costo_min'])} euro")

    if riga["premialita"]:
        pezzi.append(f"premialità: {riga['premialita']}")

    # L'atto sta nella riga del bando: il modello lo cita insieme
    # all'etichetta di quel bando, non lo prende dall'intestazione del blocco
    pezzi.append(f"atto: {riga['riferimento_atto'] or 'non indicato'}")
    pezzi.append(f"url: {riga['url']}")

    return " | ".join(pezzi)


def fonte_bando(riga) -> str:
    """La fonte di un bando, con la data in cui è stata verificata."""
    return (
        f"{riga['fonte']}, {riga['riferimento_atto']} "
        f"(dati verificati il {riga['verificato_il']})"
    )


def nota_per_ente(conn: sqlite3.Connection, riga, tipo: str) -> str | None:
    """La nota di un bando nell'elenco di un tipo di ente."""
    beneficiari = beneficiari_di(conn, riga["id"])
    if tipo == "unione_comuni" and riga["classificato_il"] is None:
        if not any(b["tipo"] in (tipo, PER_REQUISITO) for b in beneficiari):
            return NOTA_UNIONE
    return ammissione(beneficiari, tipo)


class RigheBandi:
    """Le righe di bandi di un risultato, ciascuna con la fonte del suo bando.

    Ogni riga riceve nel testo il segnaposto [#k], nell'ordine in cui si
    scrive; la voce k di Risultato.voci e' la stessa riga.
    """

    def __init__(self) -> None:
        self.voci: list[VoceBando] = []

    def numera(self, riga, testo: str) -> str:
        """Il testo della riga preceduto dal suo segnaposto."""
        self.voci.append(VoceBando(testo, fonte_bando(riga)))
        return f"[#{len(self.voci)}] {testo}"


def _elenco(conn, righe, oggi: str, tipo: str, numerate: RigheBandi) -> str:
    return "\n".join(
        f"- {numerate.numera(r, formatta_bando(r, oggi, nota_per_ente(conn, r, tipo)))}"
        for r in righe
    )


def senza_scadenza(riga) -> bool:
    """Un bando che non e' a sportello e non ha scadenza."""
    return not riga["a_sportello"] and not riga["scadenza"]


def gruppi_aperti(righe: list) -> tuple[list, list, list]:
    """Divide i bandi non scaduti: con scadenza, a sportello, senza scadenza.

    Solo i primi due sono aperti di sicuro; per i bandi senza scadenza la
    pagina non dice fino a quando si puo' presentare domanda.
    """
    a_scadenza = [r for r in righe if not r["a_sportello"] and r["scadenza"]]
    a_sportello = [r for r in righe if r["a_sportello"]]
    da_verificare = [r for r in righe if senza_scadenza(r)]
    return a_scadenza, a_sportello, da_verificare


def testo_gruppi(intestazione: str, gruppi: tuple, elenco) -> str:
    """L'elenco dei bandi non scaduti, in tre gruppi.

    intestazione: la prima riga, per i bandi aperti di sicuro (con scadenza
    o a sportello); elenco: la funzione che scrive le righe di un gruppo.
    """
    a_scadenza, a_sportello, da_verificare = gruppi
    testo = intestazione
    if a_scadenza:
        testo += f"\n{elenco(a_scadenza)}"
    if a_sportello:
        testo += f"\n{GRUPPO_SPORTELLO}\n{elenco(a_sportello)}"
    if da_verificare:
        testo += f"\n{GRUPPO_SENZA_SCADENZA}\n{elenco(da_verificare)}"
    return testo


def bandi_aperti_per_ente(conn: sqlite3.Connection, codice_ente: str) -> Risultato:
    """I bandi ancora aperti a cui l'ente può presentare domanda."""
    tipo = tipo_ente(conn, codice_ente)
    if tipo is None:
        return _ente_non_gestito(codice_ente)
    nomi = NOMI_ENTE[tipo]
    oggi = data_di_oggi().isoformat()
    filtro, parametri = filtro_ente(tipo)

    righe = conn.execute(
        f"""
        SELECT * FROM bandi
        WHERE {filtro}
          AND {SOLO_BANDI}
          AND (scadenza IS NULL OR scadenza >= ?)
        ORDER BY a_sportello, scadenza
        """,
        (*parametri, oggi),
    ).fetchall()

    if not righe:
        totale = conn.execute(
            f"SELECT COUNT(*) FROM bandi WHERE {filtro} AND {SOLO_BANDI}", parametri
        ).fetchone()[0]
        return Risultato(
            f"Nessun bando aperto per {nomi['tutti']} alla data del {oggi}. "
            f"In archivio ce ne sono {totale} rivolti a {nomi['tutti']}, "
            "tutti scaduti.",
            trovato=False,
        )

    gruppi = gruppi_aperti(righe)
    aperti = len(gruppi[0]) + len(gruppi[1])
    intestazione = (
        f"Bandi aperti a cui {nomi['uno']} può presentare domanda "
        f"(alla data del {oggi}), {aperti} in archivio:"
        if aperti
        else f"Nessun bando aperto di sicuro per {nomi['tutti']} alla data del "
        f"{oggi}: nessuno ha una scadenza futura o e' a sportello."
    )
    numerate = RigheBandi()
    testo = testo_gruppi(
        intestazione,
        gruppi,
        lambda gruppo: _elenco(conn, gruppo, oggi, tipo, numerate),
    )

    return Risultato(testo, fonti=[fonte_bando(r) for r in righe], voci=numerate.voci)


def bandi_in_scadenza(
    conn: sqlite3.Connection, codice_ente: str, giorni: int = 60
) -> Risultato:
    """I bandi per l'ente che scadono entro un certo numero di giorni."""
    tipo = tipo_ente(conn, codice_ente)
    if tipo is None:
        return _ente_non_gestito(codice_ente)
    plurale = NOMI_ENTE[tipo]["plurale"]
    oggi = data_di_oggi()
    limite = date.fromordinal(oggi.toordinal() + giorni).isoformat()
    filtro, parametri = filtro_ente(tipo)

    righe = conn.execute(
        f"""
        SELECT * FROM bandi
        WHERE {filtro}
          AND {SOLO_BANDI}
          AND a_sportello = 0
          AND scadenza BETWEEN ? AND ?
        ORDER BY scadenza
        """,
        (*parametri, oggi.isoformat(), limite),
    ).fetchall()

    if not righe:
        return Risultato(
            f"Nessun bando per {plurale} in scadenza nei prossimi {giorni} giorni.",
            trovato=False,
        )

    numerate = RigheBandi()
    elenco = _elenco(conn, righe, oggi.isoformat(), tipo, numerate)

    return Risultato(
        f"Bandi per {plurale} in scadenza entro {giorni} giorni:\n{elenco}",
        fonti=[fonte_bando(r) for r in righe],
        voci=numerate.voci,
    )


def etichetta_tipi(riga, beneficiari: list) -> str:
    """I tipi ammessi da un bando, per gli elenchi non legati a un ente.

    Un tipo con tutte le righe condizionate e' segnato "a condizione".
    Per i bandi non ancora classificati si sa solo se ammettono i Comuni.
    """
    if riga["classificato_il"] is None:
        if any(b["tipo"] == "comune" for b in beneficiari):
            return f"[ammessi: Comuni; {NON_CLASSIFICATI}]"
        return f"[NON per i Comuni; {NON_CLASSIFICATI}]"

    nomi = []
    for tipo in TIPI_BENEFICIARIO:
        righe = [b for b in beneficiari if b["tipo"] == tipo]
        if righe:
            condizionato = all(b["condizioni"] for b in righe)
            nomi.append(NOMI_TIPI[tipo] + (" (a condizione)" if condizionato else ""))
    return f"[ammessi: {', '.join(nomi)}]"


def bandi_per_tema(conn: sqlite3.Connection, tema: str) -> Risultato:
    """I bandi di un certo tema, con l'indicazione se aperti e per chi."""
    oggi = data_di_oggi().isoformat()

    righe = conn.execute(
        f"SELECT * FROM bandi WHERE tema LIKE ? AND {SOLO_BANDI} "
        "ORDER BY scadenza DESC",
        (f"%{tema.lower()}%",),
    ).fetchall()

    if not righe:
        temi = conn.execute(
            f"SELECT DISTINCT tema FROM bandi WHERE tema IS NOT NULL AND {SOLO_BANDI}"
        ).fetchall()
        elenco = ", ".join(r["tema"] for r in temi) or "nessuno"
        return Risultato(
            f"Nessun bando sul tema '{tema}'. Temi in archivio: {elenco}.",
            trovato=False,
        )

    numerate = RigheBandi()
    elenco = "\n".join(
        "- "
        + numerate.numera(
            r,
            f"{etichetta_tipi(r, beneficiari_di(conn, r['id']))} "
            f"{formatta_bando(r, oggi)}",
        )
        for r in righe
    )

    return Risultato(
        f"Bandi sul tema '{tema}' in archivio:\n{elenco}",
        fonti=[fonte_bando(r) for r in righe],
        voci=numerate.voci,
    )


def bandi_per_beneficiario(conn: sqlite3.Connection, tipo: str) -> Risultato:
    """I bandi aperti che ammettono un tipo di beneficiario della lista chiusa."""
    if tipo not in TIPI_BENEFICIARIO:
        validi = ", ".join(f"{t} ({n})" for t, n in NOMI_TIPI.items())
        return Risultato(
            f"Tipo di beneficiario '{tipo}' sconosciuto. Tipi validi: {validi}.",
            trovato=False,
        )
    oggi = data_di_oggi().isoformat()

    righe = conn.execute(
        f"""
        SELECT * FROM bandi
        WHERE {HA_TIPO}
          AND {SOLO_BANDI}
          AND (scadenza IS NULL OR scadenza >= ?)
        ORDER BY a_sportello, scadenza
        """,
        (tipo, oggi),
    ).fetchall()

    # I bandi aperti non classificati: se ammettono questo tipo non si sa,
    # salvo per i Comuni, che hanno la riga migrata
    da_classificare = conn.execute(
        "SELECT COUNT(*) FROM bandi WHERE classificato_il IS NULL "
        f"AND {SOLO_BANDI} AND (scadenza IS NULL OR scadenza >= ?)",
        (oggi,),
    ).fetchone()[0]
    avvertenza = (
        f"\n{da_classificare} bandi aperti in archivio hanno beneficiari non "
        "ancora classificati: potrebbero ammettere anche questo tipo."
        if da_classificare and tipo != "comune"
        else ""
    )

    nome = NOMI_TIPI[tipo]
    if not righe:
        return Risultato(
            f"Nessun bando aperto per {nome} alla data del {oggi}.{avvertenza}",
            trovato=False,
        )

    numerate = RigheBandi()

    def elenco(gruppo):
        return "\n".join(
            "- "
            + numerate.numera(
                r,
                formatta_bando(
                    r, oggi, ammissione(beneficiari_di(conn, r["id"]), tipo)
                ),
            )
            for r in gruppo
        )

    gruppi = gruppi_aperti(righe)
    aperti = len(gruppi[0]) + len(gruppi[1])
    intestazione = (
        f"Bandi aperti per {nome} (alla data del {oggi}), {aperti} in archivio:"
        if aperti
        else f"Nessun bando aperto di sicuro per {nome} alla data del {oggi}: "
        "nessuno ha una scadenza futura o e' a sportello."
    )
    return Risultato(
        testo_gruppi(intestazione, gruppi, elenco) + avvertenza,
        fonti=[fonte_bando(r) for r in righe],
        voci=numerate.voci,
    )


def descrivi_beneficiari(riga, beneficiari: list) -> str:
    """I beneficiari di un bando, ciascuno con condizioni e frase del bando."""
    voci = []
    for b in beneficiari:
        voce = NOMI_TIPI[b["tipo"]]
        if b["condizioni"]:
            voce += f", ammesso se {b['condizioni']}"
        if b["tipo"] == PER_REQUISITO and b["soggetto"]:
            voce += f" (nel bando: «{b['soggetto']}»)"
        # Le righe migrate hanno come frase il testo di beneficiari, che il
        # dettaglio mostra gia'
        if b["origine"] != "ammette_comuni":
            voce += f" (frase del bando: «{b['frase']}»)"
        voci.append(voce)

    if riga["classificato_il"] is None:
        if not voci:
            voci.append("non i Comuni")
        voci.append(NON_CLASSIFICATI)
    return "; ".join(voci)


def dettaglio_bando(conn: sqlite3.Connection, id_bando: str) -> Risultato:
    """Tutti i dati strutturati di un singolo bando."""
    riga = conn.execute(
        "SELECT * FROM bandi WHERE id = ? OR titolo LIKE ?",
        (id_bando, f"%{id_bando}%"),
    ).fetchone()

    if riga is None:
        ids = conn.execute("SELECT id FROM bandi").fetchall()
        return Risultato(
            f"Nessun bando corrisponde a '{id_bando}'. "
            f"Identificativi in archivio: {', '.join(r['id'] for r in ids)}.",
            trovato=False,
        )

    oggi = data_di_oggi().isoformat()
    if riga["natura"] == "non_bando":
        # La pagina e' in archivio ma non e' un'opportunita': si dice
        # perche', senza i dati del bando
        numerate = RigheBandi()
        testo = numerate.numera(
            riga,
            f"«{riga['titolo']}» non e' un bando: {riga['natura_motivo']} "
            f"| url: {riga['url']}",
        )
        return Risultato(testo, fonti=[fonte_bando(riga)], voci=numerate.voci)

    pezzi = [
        formatta_bando(riga, oggi),
        "beneficiari ammessi: "
        + descrivi_beneficiari(riga, beneficiari_di(conn, riga["id"])),
    ]

    interventi = conn.execute(
        "SELECT * FROM interventi_bando WHERE id_bando = ? ORDER BY numero",
        (riga["id"],),
    ).fetchall()
    if interventi:
        pezzi.append(
            "interventi e spese ammissibili: "
            + "; ".join(f"{i['genere']}: {i['descrizione']}" for i in interventi)
        )

    if riga["cumulabilita"]:
        pezzi.append(
            f"cumulabilità: {riga['cumulabilita']} "
            f"(frase del bando: «{riga['cumulabilita_frase']}»)"
        )

    dotazione = (
        f"{euro(riga['dotazione'])} euro" if riga["dotazione"] else "non indicata"
    )
    pezzi.append(f"dotazione complessiva: {dotazione}")

    # Un solo bando, una sola voce: l'atto e' gia' nella riga del bando
    numerate = RigheBandi()
    testo = numerate.numera(riga, " | ".join(pezzi))
    return Risultato(testo, fonti=[fonte_bando(riga)], voci=numerate.voci)
