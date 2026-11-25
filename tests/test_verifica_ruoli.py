"""Verificatore: falsi allarmi e dato giusto nel ruolo sbagliato (25/11/2026).

Le righe dei bandi sono quelle vere passate al modello nelle risposte
salvate (lotto 1, lotto 2, domande sulla sospensione del 24/11/2026),
copiate tali e quali. Nessun modello, nessuna rete.

- abbinamento: un dato in un punto d'elenco va con la citazione del suo
  punto, non con quella del punto dopo;
- varianti di scrittura: "primo gennaio", numeri in lettere davanti a
  un'unita', "€.", orari con la virgola, ATECO a due livelli;
- la domanda: una quantita' scritta dall'utente non e' un allarme;
- intervalli di date: fine prima dell'inizio, coppia che non e' una
  finestra della fonte;
- il caso 4 (demo del 24/11/2026): "10 anni" attribuito a Sport Missione
  Comune ma presente nella riga di Cultura Missione Comune resta rosso.
"""

from decimal import Decimal

import pytest
from langchain_core.documents import Document

import src.normalizzazione as nz
import src.verification.controllo as vc
from src.database.modelli import Risultato, VoceBando


def blocco(*voci: VoceBando, intestazione="Bandi aperti (alla data del 2026-11-15)"):
    righe = "\n".join(f"- [#{k}] {v.testo}" for k, v in enumerate(voci, start=1))
    return [
        (
            "bandi_aperti_per_ente",
            Risultato(
                f"{intestazione}, {len(voci)} in archivio:\n{righe}",
                fonti=[v.fonte for v in voci],
                voci=list(voci),
            ),
        )
    ]


# --- righe vere ----------------------------------------------------------

# lotto 2, 2026-11-15_191851, C06: D1.3 e D1.4
CULTURA = VoceBando(
    "«Cultura Missione Comune 2026» (Istituto per il Credito Sportivo e Culturale "
    "S.p.A.) | a sportello fino al 2026-12-05, verificare la disponibilità delle "
    "risorse | nota: Le istanze si presentano dalle ore 12:00 del 10/06/2026 fino "
    "alle ore 23:59 del 05/12/2026, con procedura a sportello fino ad esaurimento "
    "delle risorse. Contributo: «Le istanze complete della documentazione prevista "
    "per l’ammissione al Contributo (compresa l’eventuale autorizzazione della "
    "Soprintendenza) potranno ottenere contributi per l’abbattimento totale degli "
    "interessi calcolati su mutui a tasso fisso della durata di 10 anni.» | "
    "beneficiari: Le risorse possono essere utilizzate da Comuni, Unioni di Comuni, "
    "Comuni in forma associata, Città Metropolitane, Province e Regioni. L’importo "
    "massimo di mutuo agevolabile per ciascuna istanza e complessivo è: 2 milioni di "
    "euro per i piccoli Comuni (fino a 5.000 abitanti); 4 milioni di euro per i "
    "Comuni medi (da 5.001 a 100.000,00 abitanti non capoluogo) le Unioni dei Comuni "
    "e i Comuni in forma associata; 6 milioni di euro per i Comuni capoluogo, i "
    "Comuni oltre i 100.000,00 abitanti non capoluogo, le Città Metropolitane, le "
    "Province e le Regioni . | atto: Avviso pubblico CULTURA MISSIONE COMUNE 2026, "
    "con Proroga del termine di presentazione delle istanze | url: "
    "https://www.creditosportivo.it/fondi-speciali-bandi-cultura-2026",
    "Sito Istituto per il Credito Sportivo e Culturale, Avviso pubblico CULTURA "
    "MISSIONE COMUNE 2026, con Proroga del termine di presentazione delle istanze "
    "(dati estratti il 2026-11-13)",
)
SPORT = VoceBando(
    "«Bando Sport Missione Comune 2026» (Istituto per il Credito Sportivo e "
    "Culturale S.p.A.) | finestra aperta fino al 2026-12-05 (presentazione istanza "
    "di contributo, fra 20 giorni), a sportello: verificare la disponibilità delle "
    "risorse | fase successiva, solo per chi ha superato la precedente: acquisizione "
    "e trasmissione del parere favorevole del CONI entro il 2026-12-18 | nota: Le "
    "istanze devono essere presentate entro il 05/12/2026, provviste almeno della "
    "richiesta di parere CONI; il parere favorevole del CONI può essere trasmesso "
    "successivamente entro le ore 23:59 del 18/12/2026. | beneficiari: Le risorse "
    "possono essere utilizzate da Comuni, Unioni di Comuni, Comuni in forma "
    "associata, Città Metropolitane, Province e Regioni. L’importo massimo di mutuo "
    "agevolabile per ciascuna istanza e complessivo è: 2 milioni di euro per i "
    "piccoli Comuni (fino a 5.000 abitanti); 4 milioni di euro per i Comuni medi (da "
    "5.001 a 100.000,00 abitanti non capoluogo) le Unioni dei Comuni e i Comuni in "
    "forma associata; 6 milioni di euro per i Comuni capoluogo, i Comuni oltre i "
    "100.000,00 abitanti non capoluogo, le Città Metropolitane, le Province e le "
    "Regioni . | atto: Avviso pubblico SPORT MISSIONE COMUNE 2026, con Proroga del "
    "termine di presentazione delle istanze | url: "
    "https://www.creditosportivo.it/fondi-speciali-bandi-sport-2026",
    "Sito Istituto per il Credito Sportivo e Culturale, Avviso pubblico SPORT "
    "MISSIONE COMUNE 2026, con Proroga del termine di presentazione delle istanze "
    "(dati estratti il 2026-11-13)",
)
CITAZIONE_SPORT = (
    "Avviso pubblico SPORT MISSIONE COMUNE 2026, con Proroga del termine di "
    "presentazione delle istanze"
)

# lotto 1, 2026-11-15_182748, L02: D1.8 e D1.9
EU_BLENDING = VoceBando(
    "«Bando 2026 Pmi: sovvenzioni per abbattere interessi e costi di garanzia su "
    "finanziamenti bancari EU-Blending» (Regione Toscana) | a sportello, verificare "
    "la disponibilità delle risorse (pubblicato il 2026-04-30) | nota: Bando a "
    "sportello, aperto fino ad esaurimento delle risorse; le domande si presentano a "
    "partire dalle ore 10:00 dell'11 maggio 2026 | beneficiari: Micro e piccole "
    "medie imprese (Mpmi) e professionisti, come definite dall’allegato 1 del "
    "Regolamento UE n. 651/2014. | ammesso se operare nei settori ammissibili ai "
    "sensi della delibera di giunta regionale 704/2025 e del Fondo di garanzia per "
    "le Pmi, purché l'attività non rientri nei settori esclusi | atto: Decreto "
    "dirigenziale 9506 del 30 aprile 2026 | url: https://www.regione.toscana.it/-/"
    "bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-costi-di-garanzia-su-"
    "finanziamenti-bancari-eu-blending",
    "Portale bandi Regione Toscana, Decreto dirigenziale 9506 del 30 aprile 2026 "
    "(dati estratti il 2026-11-11)",
)
OBBLIGAZIONI = VoceBando(
    "«Contributi a copertura di spese di emissione obbligazioni, titoli di debito e "
    "commissioni di garanzia» (Regione Toscana) | a sportello, verificare la "
    "disponibilità delle risorse (pubblicato il 2026-02-04) | nota: Procedura a "
    "sportello: le domande sono accolte dal 2 febbraio 2026 ore 10:00 secondo ordine "
    "cronologico fino all'esaurimento delle risorse, non è prevista una scadenza "
    "fissa | beneficiari: le Pmi nella forma di società di capitali, nonché di "
    "società cooperative a responsabilità limitata e per azioni, diverse dalle "
    "banche, che intendono avviare un'operazione di emissione di titoli "
    "obbligazionari e/o di debito. | ammesso se le Pmi nella forma di società di "
    "capitali, nonché di società cooperative a responsabilità limitata e per "
    "azioni, diverse dalle banche, che intendono avviare un'operazione di emissione "
    "di titoli obbligazionari e/o di debito. | contributo fino al 50% | progetto "
    "ammissibile da 250.000 a 5.000.000 euro | atto: Decreto dirigenziale 1246 del "
    "23 gennaio 2026 | url: https://www.regione.toscana.it/-/contributi-a-copertura-"
    "di-spese-di-emissione-obbligazioni-titoli-di-debito-e-commissioni-di-garanzia",
    "Portale bandi Regione Toscana, Decreto dirigenziale 1246 del 23 gennaio 2026 "
    "(dati estratti il 2026-11-11)",
)

# lotto 2, 2026-11-16_112154, P21: D1.2
INTERNAZIONALIZZAZIONE = VoceBando(
    "«Contributi per l'internazionalizzazione delle imprese: il bando 2026» "
    "(Regione Toscana) | scade il 2026-12-18 (fra 32 giorni) | nota: Le domande "
    "possono essere presentate dalle ore 10,00 del 18 novembre 2026 fino alle 16,00 "
    "del 18 dicembre 2026 | beneficiari: Micro e Piccole medie imprese, "
    "Professionisti | atto: Decreto dirigenziale 23729 del 23 ottobre 2026",
    "Portale bandi Regione Toscana, Decreto dirigenziale 23729 del 23 ottobre 2026 "
    "(dati estratti il 2026-11-12)",
)

# domande sulla sospensione, 24/11/2026 ("dopo"): la riga degli incentivi,
# ricostruita dal database (dati-grezzi/prova/verificatore/), nella parte
# che conta: sospensione e finestre
INCENTIVI = VoceBando(
    "«Incentivi ai datori di lavoro privati per l'occupazione dei disoccupati, "
    "annualità 2023-2025 e 2026-2027» (Regione Toscana) | SOSPESO IN PARTE dal "
    "2026-07-08 (decreto n. 742/2026 di Arti): sospeso per over 30 disoccupati "
    "licenziati dal primo gennaio 2021, over 30 disoccupati svantaggiati, over 55 "
    "disoccupati (articolo 5 lettere a, b e c), under 30 disoccupati (articolo 5 "
    "lettera d), donne disoccupate (articolo 5 lettera e); resta aperto solo per "
    "persone con disabilità, iscritte negli appositi elenchi del collocamento mirato "
    "(articolo 5 lettera f) | per la parte non sospesa: finestra aperta fino al "
    "2027-01-10 (assunzioni/trasformazioni 2026, fra 47 giorni), a sportello: "
    "verificare la disponibilità delle risorse; prossima finestra dal 2027-01-11 al "
    "2028-01-10 (assunzioni/trasformazioni 2027)",
    "Portale bandi Regione Toscana, Decreto dirigenziale Arti 848 del 2 novembre "
    "2023 (dati estratti il 2026-11-23)",
)


def esito_di(esiti, valore):
    [trovato] = [e for e in esiti if e.valore == valore]
    return trovato


# --- caso 4: dato vero del bando gemello ---------------------------------


def test_caso_4_nella_frase_resta_rosso():
    """Demo del 24/11/2026: la frase cita Sport, il dato e' nella riga di Cultura."""
    risposta = (
        "La copertura non è un contributo a fondo perduto, ma l'abbattimento "
        "totale degli interessi calcolati su mutui a tasso fisso della durata di "
        f"10 anni (fonte: [D1.2], {CITAZIONE_SPORT})."
    )
    esito = esito_di(vc.verifica(risposta, [], blocco(CULTURA, SPORT)), "10")
    assert esito.stato == "non_trovato"
    assert esito.frammenti == ["D1.2"]
    assert esito.dettaglio == "presente invece in ['D1.1']"


def test_caso_4_in_un_elenco_resta_rosso():
    """Il dato in coda al punto di Sport; il punto dopo cita Cultura."""
    risposta = (
        f"- «Bando Sport Missione Comune 2026» (fonte: [D1.2], {CITAZIONE_SPORT}): "
        "abbattimento degli interessi su mutui della durata di 10 anni.\n"
        "- «Cultura Missione Comune 2026» (fonte: [D1.1], Avviso pubblico CULTURA "
        "MISSIONE COMUNE 2026): a sportello fino al 2026-12-05."
    )
    esito = esito_di(vc.verifica(risposta, [], blocco(CULTURA, SPORT)), "10")
    assert esito.stato == "non_trovato"
    assert esito.frammenti == ["D1.2"]


# --- abbinamento al proprio punto d'elenco ----------------------------------


def test_dato_in_coda_al_punto_va_con_la_citazione_del_punto():
    """Lotto 1, L02: il 704 e' nella riga di EU-Blending, il punto dopo cita le obbligazioni."""
    risposta = (
        "- «Bando 2026 Pmi: sovvenzioni […] EU-Blending» (fonte: [D1.1], Decreto "
        "dirigenziale 9506 del 30 aprile 2026): condizione da verificare, settori "
        "ammissibili ai sensi della delibera 704/2025.\n"
        "- «Contributi a copertura di spese di emissione obbligazioni, titoli di "
        "debito e commissioni di garanzia» (fonte: [D1.2], Decreto dirigenziale 1246 "
        "del 23 gennaio 2026): condizione da verificare."
    )
    esito = esito_di(
        vc.verifica(risposta, [], blocco(EU_BLENDING, OBBLIGAZIONI)), "704"
    )
    assert esito.stato == "verificato"
    assert esito.frammenti == ["D1.1"]


def test_fuori_da_un_elenco_resta_la_citazione_successiva():
    """Una riga che non e' un punto d'elenco ("... sono:") non cambia abbinamento."""
    risposta = (
        "Il Comune ha 1834 abitanti (fonte: [D2], ISTAT); i bandi per i piccoli "
        "Comuni fino a 5.000 abitanti sono:\n"
        "Cultura Missione Comune (fonte: [D1.1], Avviso pubblico CULTURA)."
    )
    dati = blocco(CULTURA) + [
        ("popolazione", Risultato("Dato più recente: 1834 abitanti.", fonti=["ISTAT"]))
    ]
    esito = esito_di(vc.verifica(risposta, [], dati), "5.000")
    assert esito.stato == "verificato"
    assert esito.frammenti == ["D1.1"]


# --- varianti di scrittura ------------------------------------------------


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [
        ("primo gennaio 2021", "2021-01-01"),
        ("Primo aprile 2026", "2026-04-01"),
        ("1° gennaio 2021", "2021-01-01"),
    ],
)
def test_primo_nelle_date(testo, atteso):
    assert nz.data(testo) == atteso


def test_primo_gennaio_della_fonte_conferma_1_gennaio():
    """Caso 2: la risposta scrive "1° gennaio 2021", la riga "primo gennaio 2021"."""
    risposta = (
        "Sono sospesi gli over 30 disoccupati licenziati dal 1° gennaio 2021 "
        "(fonte: [D1.1], Decreto dirigenziale Arti 848)."
    )
    esito = esito_di(vc.verifica(risposta, [], blocco(INCENTIVI)), "1° gennaio 2021")
    assert esito.stato == "verificato"


@pytest.mark.parametrize(
    ("parola", "atteso"),
    [
        ("centoventi", 120),
        ("cinquantasette", 57),
        ("ventisei", 26),
        ("quaranta", 40),
        ("ventuno", 21),
        ("trentotto", 38),
        ("duemila", 2000),
        ("milleduecento", 1200),
        ("cinquantuno", 51),
        ("dieci", 10),
        ("ventitré", 23),
        ("tavolo", None),
        ("venticinquenne", None),
    ],
)
def test_numero_in_lettere(parola, atteso):
    assert nz.numero_in_lettere(parola) == atteso


def test_numeri_in_lettere_della_fonte_solo_davanti_a_un_unita():
    v = nz.valori(
        "età non superiore a quaranta anni; detengono il cinquantuno per cento"
    )
    assert Decimal(40) in v.numeri
    assert Decimal(51) in v.percentuali
    # senza unita' le parole restano parole: "una", "sei", "otto"
    assert nz.valori("una domanda, sei tu, otto volte").numeri == set()


def test_quaranta_anni_della_fonte_conferma_40():
    """19e, 08_a-mano_59_V1: l'avviso scrive "quaranta anni"."""
    frammento = Document(
        page_content=(
            "a) per le imprese individuali, l’età del titolare dell’impresa non deve "
            "essere superiore a quaranta anni al momento della costituzione"
        ),
        metadata={"ente": "Regione Toscana"},
    )
    risposta = (
        "Il titolare deve avere un'età non superiore a 40 anni (fonte: [1], Regione)."
    )
    assert esito_di(vc.verifica(risposta, [frammento]), "40").stato == "verificato"


def test_euro_con_il_punto_prima_dell_importo():
    """19e, 10_a-mano_2-51_V0: "€. 34,00" era letto come l'importo "."."""
    frammento = Document(
        page_content="Basso €. 30,00 €. 34,00 €. 32,00",
        metadata={"ente": "Regione Toscana"},
    )
    risposta = (
        "Il costo orario è pari a €. 34,00 per le Università (fonte: [1], Regione)."
    )
    esiti = vc.verifica(risposta, [frammento])
    assert [(e.tipo, e.valore, e.stato) for e in esiti] == [
        ("importo", "34,00", "verificato")
    ]


@pytest.mark.parametrize(
    ("testo", "atteso"),
    [("ore 10,00", "10:00"), ("ore 16,00", "16:00"), ("ore 9.30", "09:30")],
)
def test_orario_con_la_virgola(testo, atteso):
    assert nz.orario(testo) == atteso


def test_orari_con_la_virgola_nella_fonte_e_nella_risposta():
    """Lotto 2, P21: "ore 16,00" e "alle 16,00", senza il finto dato "00"."""
    risposta = (
        "Le domande si possono presentare dalle ore 10,00 del 18 novembre 2026 fino "
        "alle ore 16,00 del 18 dicembre 2026 (fonte: [D1.1], Decreto dirigenziale "
        "23729 del 23 ottobre 2026)."
    )
    esiti = vc.verifica(risposta, [], blocco(INTERNAZIONALIZZAZIONE))
    assert [e for e in esiti if e.stato != "verificato"] == []
    assert "00" not in [e.valore for e in esiti]


def test_orario_alle_con_i_minuti_nella_fonte():
    assert "16:00" in nz.valori("fino alle 16,00 del 18 dicembre 2026").orari
    # "alle" senza minuti, o seguito da euro, non e' un orario
    assert nz.valori("alle 16 imprese").orari == set()
    assert nz.valori("dalle 10,50 euro").orari == set()


def test_ateco_a_due_livelli_e_un_codice_solo():
    """Lotto 1, L02: "codice ATECO 56.10" erano due quantita', 56 e 10."""
    dati = vc.trova_dati("ristorazione (codice ATECO 56.10). Le segnalo")
    assert [(d.tipo, d.valore) for d in dati] == [("codice", "56.10")]


# --- la domanda -------------------------------------------------------------

RISPOSTA_57 = (
    "Un disoccupato di 57 anni rientra nella categoria over 55 disoccupati "
    "(fonte: [D1.1], Decreto dirigenziale Arti 848)."
)


def test_quantita_della_domanda_non_e_un_allarme():
    """Caso 1: il 57 e' l'eta' scritta dall'utente."""
    domanda = "Vorrei assumere un disoccupato di 57 anni: c'è un incentivo?"
    esiti = vc.verifica(RISPOSTA_57, [], blocco(INCENTIVI), domanda=domanda)
    assert esito_di(esiti, "57").stato == "dalla_domanda"
    assert esito_di(esiti, "55").stato == "verificato"
    assert vc.giudizio(esiti)[0] == "verde"
    # verificati: il 55 e l'atto 848 della citazione
    assert vc.riassumi(esiti) == {
        "verificato": 2,
        "non_trovato": 0,
        "non_citato": 0,
        "dalla_domanda": 1,
    }


def test_senza_la_domanda_resta_rosso():
    esiti = vc.verifica(RISPOSTA_57, [], blocco(INCENTIVI))
    assert esito_di(esiti, "57").stato == "non_trovato"


def test_quantita_della_domanda_in_lettere():
    """19e, 06_fogli_2-96: la domanda scrive "centoventi", la risposta "120"."""
    frammento = Document(
        page_content="Priorità: fra 40 e 100 alveari; oltre 100 alveari.",
        metadata={"ente": "Regione Toscana"},
    )
    risposta = (
        "Un apicoltore con 120 alveari supera la soglia dei 100 (fonte: [1], Regione)."
    )
    domanda = "Ho centoventi alveari: che punteggio ho?"
    esiti = vc.verifica(risposta, [frammento], domanda=domanda)
    assert esito_di(esiti, "120").stato == "dalla_domanda"


def test_quantita_della_domanda_senza_citazione():
    risposta = "Per un disoccupato di 57 anni la categoria è sospesa."
    domanda = "Vorrei assumere un disoccupato di 57 anni"
    esiti = vc.verifica(risposta, [], blocco(INCENTIVI), domanda=domanda)
    assert esito_di(esiti, "57").stato == "dalla_domanda"


def test_data_della_domanda_resta_al_controllo_normale():
    domanda = "Il bando scade il 2026-12-31?"
    risposta = "Sì, scade il 2026-12-31 (fonte: [D1.1], Avviso pubblico CULTURA)."
    esiti = vc.verifica(risposta, [], blocco(CULTURA), domanda=domanda)
    assert esito_di(esiti, "2026-12-31").stato == "non_trovato"


def test_quantita_della_domanda_trovata_nella_fonte_resta_verificata():
    domanda = "Il comune ha meno di 5.000 abitanti"
    risposta = "Per i piccoli Comuni fino a 5.000 abitanti (fonte: [D1.1], Avviso)."
    esiti = vc.verifica(risposta, [], blocco(CULTURA), domanda=domanda)
    assert esito_di(esiti, "5.000").stato == "verificato"


# --- intervalli -------------------------------------------------------------


def test_intervallo_con_la_fine_prima_dell_inizio_senza_fonte():
    risposta = "È prevista una finestra dal 2027-01-11 al 2027-01-10."
    [esito] = [e for e in vc.verifica(risposta, []) if e.tipo == "intervallo"]
    assert esito.stato == "non_trovato"
    assert esito.dettaglio == "la fine viene prima dell'inizio"


def test_caso_3_e_rosso():
    """Domande sulla sospensione, "dopo", seconda risposta."""
    risposta = (
        "È prevista anche una finestra successiva dal 2027-01-11 al 2027-01-10 "
        "(anno 2028) per le assunzioni o trasformazioni realizzate nel 2027 "
        "(fonte: [D1.1], Decreto dirigenziale Arti 848)."
    )
    esiti = vc.verifica(risposta, [], blocco(INCENTIVI))
    [esito] = [e for e in esiti if e.tipo == "intervallo"]
    assert esito.stato == "non_trovato"
    assert esito.frammenti == ["D1.1"]
    assert vc.giudizio(esiti)[0] == "rosso"


def test_estremi_presenti_ma_non_della_stessa_finestra():
    risposta = (
        "Si può presentare domanda dal 2026-07-08 al 2028-01-10 "
        "(fonte: [D1.1], Decreto dirigenziale Arti 848)."
    )
    esiti = vc.verifica(risposta, [], blocco(INCENTIVI))
    [esito] = [e for e in esiti if e.tipo == "intervallo"]
    assert esito.stato == "non_trovato"
    assert esito.dettaglio == "estremi presenti, ma non della stessa finestra"


def test_finestra_giusta_nessun_esito_in_piu():
    risposta = (
        "È prevista una finestra dal 2027-01-11 al 2028-01-10 "
        "(fonte: [D1.1], Decreto dirigenziale Arti 848)."
    )
    esiti = vc.verifica(risposta, [], blocco(INCENTIVI))
    assert [e.tipo for e in esiti if e.tipo == "intervallo"] == []
    assert vc.giudizio(esiti)[0] == "verde"


# --- testo mostrato all'utente ---------------------------------------------


@pytest.mark.parametrize(
    ("dettaglio", "documenti", "atteso"),
    [
        (
            "non presente in nessuna fonte recuperata",
            [],
            "Non trovato in nessuna fonte recuperata.",
        ),
        (
            "presente invece in ['D1.6']",
            [],
            "Non trovato nella fonte citata: è invece nella riga di un altro bando, D1.6.",
        ),
        (
            "presente invece in ['2']",
            [
                Document(page_content="a", metadata={"fonte": "avviso_a.pdf"}),
                Document(page_content="b", metadata={"fonte": "avviso_b.pdf"}),
            ],
            "Non trovato nella fonte citata: è invece in un altro documento, [2].",
        ),
        (
            "presente invece in ['2']",
            [
                Document(page_content="a", metadata={"fonte": "avviso_a.pdf"}),
                Document(page_content="b", metadata={"fonte": "avviso_a.pdf"}),
            ],
            (
                "Non trovato nel punto citato: è in un altro punto dello stesso "
                "documento, [2]."
            ),
        ),
        (
            "estremi presenti, ma non della stessa finestra",
            [],
            "Estremi presenti, ma non della stessa finestra.",
        ),
    ],
)
def test_spiegazione_del_rosso(dettaglio, documenti, atteso):
    import app.app as applicazione

    e = vc.Esito("quantita", "10", ["1"], "non_trovato", dettaglio)
    assert applicazione.spiega_dettaglio(e, documenti) == atteso


def test_frase_della_citazione_generica():
    """Il dettaglio del verificatore con la maiuscola e il punto finale.

    Prima l'app mostrava il dettaglio tale e quale: "presente solo nel
    bando [D1.1]: va citato con la sua etichetta".
    """
    import app.app as applicazione

    e = vc.Esito(
        "data",
        "2026-11-30",
        ["D1"],
        "citazione_generica",
        "presente solo nel bando [D1.1]: va citato con la sua etichetta",
    )
    assert applicazione.spiega_dettaglio(e, []) == (
        "Presente solo nel bando [D1.1]: va citato con la sua etichetta."
    )


def test_anno_scritto_come_quantita_e_trovato_tra_gli_anni():
    """Domande sulla sospensione, "dopo", seconda risposta (testo vero).

    "dal 2021," con la virgola e' una quantita', non un anno; la riga
    scrive "dal primo gennaio 2021", che ora e' una data: il 2021 sta tra
    gli anni della fonte, non tra i numeri.
    """
    risposta = (
        "Per tutte le altre categorie di disoccupati (over 30 licenziati dal 2021, "
        "over 30 svantaggiati, over 55, under 30, donne disoccupate) il bando è "
        "invece sospeso dall'8 luglio 2026, e si istruiscono solo le domande "
        "presentate entro quella data (fonte: [D1.1], Decreto dirigenziale Arti 848)."
    )
    esito = esito_di(vc.verifica(risposta, [], blocco(INCENTIVI)), "2021")
    assert esito.tipo == "quantita"
    assert esito.stato == "verificato"


# --- testi del giudizio e del pannello ----------------------------------------


def test_rosso_con_un_dato_al_singolare():
    livello, messaggio = vc.giudizio([vc.Esito("quantita", "10", ["1"], "non_trovato")])
    assert (livello, messaggio) == (
        "rosso",
        (
            "1 dato citato non è stato trovato nella fonte indicata. "
            "Controllare a mano prima di riutilizzare la risposta."
        ),
    )


def test_rosso_con_piu_dati_al_plurale():
    esiti = [vc.Esito("quantita", n, ["1"], "non_trovato") for n in ("10", "20", "30")]
    assert vc.giudizio(esiti)[1] == (
        "3 dati citati non sono stati trovati nella fonte indicata. "
        "Controllare a mano prima di riutilizzare la risposta."
    )


def pagina_con_promessa():
    # AppTest esegue solo il corpo di questa funzione
    from app.app import mostra_verifica

    mostra_verifica({"risposta": "Nessun numero qui.", "documenti": []})


def test_la_promessa_della_verifica_compare_sempre():
    from streamlit.testing.v1 import AppTest

    import app.app as applicazione

    pagina = AppTest.from_function(pagina_con_promessa, default_timeout=30)
    pagina.run()
    assert not pagina.exception, pagina.exception
    assert [c.value for c in pagina.caption][-1] == applicazione.PROMESSA_VERIFICA
    assert applicazione.PROMESSA_VERIFICA == (
        "Il controllo riguarda numeri, date, importi e atti: dice se compaiono "
        "nella fonte citata, non se la risposta è completa."
    )
