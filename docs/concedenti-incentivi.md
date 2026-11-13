# Concedenti di Incentivi Italia: classificazione da approvare

Data: 13 novembre 2026. Proposta, non ancora nel codice. Serve alla regola
territoriale della fonte Incentivi Italia (`docs/piano-fonti.md`, tappa 5,
"Regola territoriale"): decide l'ente concedente, non il campo `Regioni`.

Elenco ricavato dal file `OpenData_Incentivi.csv` del 12/11/2026: i valori
distinti di `Soggetto_Concedente` nelle righe non scadute da più di 12 mesi
che passavano la vecchia regola A/B/C (301 righe, 72 valori), più 3 valori
del territorio o della Regione presenti solo in righe più vecchie.

## Classi

| classe | effetto |
|---|---|
| `territorio` | passa |
| `regionale` | passa |
| `nazionale` | passa |
| `altro territorio` | scartata, qualunque cosa dica `Regioni` |
| `da verificare` | non salvata; tra le "da verificare a mano", con il motivo |

Un concedente che non è nella tabella è trattato come `altro territorio`
quando la riga ha un elenco di comuni senza i nostri (la riga è già
scartata dall'elenco), altrimenti come `da verificare`: mai classificato
per somiglianza del nome. Ogni aggiornamento del file stampa i valori
nuovi, da aggiungere alla tabella a mano.

Confronto sul nome normalizzato: minuscole e spazi compressi, per il resto
esatto. Nel file lo stesso ente compare con maiuscole diverse.

Le colonne "righe" e "aperte" contano le righe del file del 12/11/2026 non
scadute da più di 12 mesi (aperte = aperte, sportelli senza chiusura, in
arrivo). Servono a pesare l'errore, non entrano nel codice.

## territorio (2 + 2 fuori dai 72)

| concedente | righe | aperte | motivo |
|---|---|---|---|
| Camera di Commercio Industria Artigianato e Agricoltura di Pistoia-Prato | 6 | 1 | camera di commercio competente |
| Comune di San Marcello Piteglio | 1 | 0 | comune dell'Unione |
| COMUNE DI ABETONE CUTIGLIANO | 0 | 0 | comune dell'Unione; solo in righe più vecchie |
| MontagnAppennino scrl | 0 | 0 | GAL del territorio; solo in righe più vecchie |

Sambuca Pistoiese e l'Unione non compaiono nel file: se compariranno,
cadranno tra le "da verificare" e si aggiungeranno qui.

## regionale (2 + 1 fuori dai 72)

| concedente | righe | aperte | motivo |
|---|---|---|---|
| Regione Toscana | 60 | 20 | Regione; le righe con un elenco di comuni senza i nostri (bandi di altri GAL, FAR Maremma) sono scartate dall'elenco |
| Regione Toscana - Giunta | 3 | 0 | come sopra |
| Sviluppo Toscana S.p.A. | 0 | 0 | agenzia regionale che gestisce i bandi della Regione; solo in righe più vecchie |

## nazionale (24)

| concedente | righe | aperte | motivo |
|---|---|---|---|
| Agenzia nazionale per l'attrazione degli investimenti e lo sviluppo d'impresa S.p.A. - Invitalia (05678721001) | 2 | 1 | agenzia nazionale |
| Agenzia per la Cybersicurezza Nazionale | 4 | 2 | agenzia nazionale |
| Gestore dei Servizi Energetici GSE S.p.A. | 1 | 1 | società pubblica nazionale |
| ICE-Agenzia per la promozione all'estero e l'internazionalizzazione delle imprese italiane | 1 | 1 | agenzia nazionale |
| INNOGEST S.G.R. S.p.A. | 1 | 1 | gestore del Fondo nazionale innovazione per conto del MIMIT |
| Invitalia - Agenzia nazionale per l'attrazione degli investimenti e lo sviluppo d'impresa S.p.A. | 4 | 4 | agenzia nazionale |
| Istituto Nazionale per l'Assicurazione contro gli Infortuni sul Lavoro - INAIL | 2 | 1 | ente nazionale; le righe sono le sezioni toscane del bando ISI |
| Istituto per il Credito Sportivo | 4 | 4 | banca pubblica nazionale |
| Ministero degli Affari Esteri e della Cooperazione Internazionale | 3 | 3 | ministero |
| Ministero del Lavoro e delle Politiche Sociali | 1 | 1 | ministero |
| Ministero del turismo | 2 | 0 | ministero |
| Ministero dell'ambiente e della sicurezza energetica | 7 | 4 | ministero |
| Ministero dell'Economia e delle Finanze | 1 | 0 | ministero |
| MINISTERO DELL'UNIVERSITA' E DELLA RICERCA | 2 | 1 | ministero |
| Ministero della Cultura | 26 | 12 | ministero |
| Ministero della Cultura - Direzione Generale Spettacolo | 1 | 1 | ministero |
| Ministero delle Imprese e del Made in Italy | 53 | 11 | ministero (vedi nota 1) |
| Ministero delle Imprese e del Made in Italy - Dipartimento per le politiche per le imprese - Direzione generale per gli incentivi alle imprese | 4 | 2 | ministero |
| Ministero delle Imprese e del Made in Italy - Direzione generale per gli incentivi alle imprese | 6 | 6 | ministero |
| Ministero delle Infrastrutture e dei Trasporti - Direzione Generale per i porti, la logistica e l'intermodalità | 1 | 0 | ministero |
| Ministero delle infrastrutture e della mobilita' sostenibili | 6 | 4 | ministero |
| Presidenza del Consiglio dei Ministri | 9 | 0 | governo |
| Presidenza del Consiglio dei Ministri - Dipartimento per l'informazione e l'editoria | 1 | 1 | governo |
| SIMEST | 7 | 7 | società pubblica nazionale; una riga ha un elenco di comuni toscani che comprende i nostri (danni da alluvione) e passa |

## da verificare (10)

Università, enti di ricerca, poli e competence center: i loro bandi "a
cascata" sono spesso limitati a un territorio, a una filiera o ai partner
di un progetto. Le 12 righe sono tutte scadute da meno di 12 mesi: nessuna
aperta.

| concedente | righe | aperte | motivo |
|---|---|---|---|
| ARTES 4.0 I - Advanced Robotics and enabling digital TEchnologies & Systems 4.0 | 1 | 0 | competence center |
| Consiglio Nazionale delle Ricerche - CNR | 1 | 0 | ente di ricerca, bando di progetto |
| Consorzio MedITECH | 1 | 0 | competence center |
| START 4.0 | 2 | 0 | competence center |
| Universita' degli Studi di Bari Aldo Moro | 2 | 0 | bando a cascata |
| Universita' degli Studi di Camerino | 1 | 0 | ecosistema dell'innovazione |
| Universita' degli Studi di Firenze | 1 | 0 | ecosistema dell'innovazione toscano |
| Universita' degli Studi di Padova | 1 | 0 | bando a cascata |
| Universita' degli Studi di Roma 'Tor Vergata' | 1 | 0 | bando di progetto |
| UNIVERSITA' DELLA CALABRIA | 1 | 0 | bando a cascata |

## altro territorio (34)

Enti locali di altre province o regioni. Molte righe sono etichettate nel
file con tutte le regioni o con la sola Toscana: il campo `Regioni` non è
affidabile per questi enti.

| concedente | righe | aperte | motivo |
|---|---|---|---|
| Autorita' di Sistema portuale del Mare Adriatico centro-settentrionale | 1 | 0 | porti dell'Adriatico |
| Camera di Commercio Arezzo Siena | 9 | 6 | altra camera toscana |
| Camera di Commercio della Maremma e del Tirreno | 9 | 0 | altra camera toscana |
| Camera di Commercio Industria Artigianato e Agricoltura di Pordenone Udine | 1 | 0 | Friuli-Venezia Giulia |
| Camera di commercio, industria, artigianato e agricoltura della Toscana Nord Ovest | 9 | 0 | altra camera toscana (Lucca, Massa-Carrara, Pisa) |
| Camera di Commercio, Industria, Artigianato e Agricoltura di Firenze | 6 | 2 | altra camera toscana |
| Comune di Aliano | 1 | 0 | Basilicata |
| Comune di Arezzo | 2 | 0 | altro comune toscano |
| Comune di Arona | 1 | 0 | Piemonte |
| Comune di Belmonte Castello | 1 | 0 | Lazio |
| comune di castelnuovo rangone | 1 | 1 | Emilia-Romagna |
| COMUNE DI CIVIDALE DEL FRIULI | 1 | 1 | Friuli-Venezia Giulia |
| Comune di Genova | 1 | 1 | Liguria |
| Comune di Laviano | 1 | 0 | Campania |
| COMUNE DI MONFUMO | 1 | 1 | Veneto |
| Comune di Napoli | 1 | 0 | Campania |
| Comune di Pratovecchio Stia | 1 | 1 | altro comune toscano |
| Comune di Ravenna | 2 | 1 | Emilia-Romagna |
| Comune di Savignano sul Rubicone | 1 | 0 | Emilia-Romagna |
| Comune di Sogliano al Rubicone | 1 | 0 | Emilia-Romagna |
| Comune di Torino | 1 | 0 | Piemonte |
| COMUNE DI TREVIGLIO | 1 | 1 | Lombardia |
| Comunita' Montana Lario Intelvese | 2 | 0 | Lombardia (errore di etichetta noto) |
| Fondazione Calabria Film Commission | 1 | 1 | Calabria |
| Fondazione Film Commission di Roma e del Lazio | 1 | 0 | Lazio |
| Fondazione Lucana Film Commission | 1 | 1 | Basilicata |
| Provincia Autonoma di Trento | 1 | 1 | Trentino |
| Regione Autonoma della Sardegna | 1 | 0 | Sardegna |
| Regione Autonoma della Sardegna - Servizio lingua e cultura sarda, Editoria e Informazione | 1 | 0 | Sardegna |
| Regione Autonoma della Sardegna - Servizio Sport, Spettacolo e Cinema | 1 | 0 | Sardegna (elenco di tutti i comuni italiani) |
| Regione Autonoma Friuli-Venezia Giulia | 4 | 0 | Friuli-Venezia Giulia |
| Regione Autonoma Valle D'Aosta | 1 | 1 | Valle d'Aosta |
| Regione Lombardia | 1 | 1 | Lombardia |
| Regione Marche | 2 | 0 | Marche (una riga con l'elenco di tutti i comuni italiani) |

Altri 17 concedenti (comuni toscani come Pistoia, Prato, Pescia, Siena;
confidi; COSVIG; due voci ministeriali sulle zone franche) compaiono solo
in righe con un elenco di comuni senza i nostri: sono scartate prima di
guardare l'ente, e non servono in tabella.

## Note

1. **MIMIT e poli digitali.** Sotto "Ministero delle Imprese e del Made in
   Italy" ci sono 31 manifestazioni di interesse dei poli europei di
   innovazione digitale (EDIH, Seal of Excellence), alcuni regionali (es.
   Alto Adige). Passano come nazionali; sono tutte scadute (26 il
   30/04/2026, 5 il 31/12/2025).
   Se ricompaiono aperte, si valuta una classe per titolo.
2. **Rumore che la tabella non toglie:** il territorio scritto solo nel
   titolo (es. ristori per Massa e Carrara, concedente Regione Toscana);
   destinatari diversi da quelli del campo `Tipologia_Soggetto`.
