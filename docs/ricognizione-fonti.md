# RICOGNIZIONE FONTI DI BANDI E FINANZIAMENTI

Data: 12/11/2026

Territorio: Unione di Comuni Montani Appennino Pistoiese, Abetone
Cutigliano, San Marcello Piteglio, Sambuca Pistoiese.

## 1. STRADA 1: DA CHI I BANDI LI HA VINTI

### 1.1 Archivi atti comunali (delibere)

- L'albo pretorio non serve per lo storico (pubblicazione di circa 15
  giorni). Le delibere stanno negli archivi atti dei gestionali:
  - Abetone Cutigliano: URBI su cloud.urbi.it, DB n1201855a
  - Unione: URBI su cloud.urbi.it, DB n1202540
  - San Marcello Piteglio: URBI su asp.urbi.it, DB n90349a
  - Sambuca Pistoiese: albo.apkappa.it fino al 09/02/2026, Hypersic
    (servizionline.hspromilaprod.hypersicapp.net) dal 10/02/2026
- robots.txt: cloud.urbi.it, asp.urbi.it e albo.apkappa.it hanno
  "Disallow: /" (vietato). Hypersic non ha robots.txt (404):
  tecnicamente consentito, ma non automatizzato (copre solo Sambuca dal
  10/02/2026, valore troppo basso).
- Decisione: nessuna lettura automatica di albi o archivi atti.
  Consultazione solo a mano, facoltativa. Gli archivi non entrano nella
  tabella fonti.

### 1.2 Analisi dei file aperti

File usati:

- PNRR Regione Toscana, dati.toscana.it, dataset "regione-toscana-pnrr",
  RT-PNRR-OpenData.csv (getOpenData_v6.csv), aggiornato 23/10/2026,
  mensile, CC BY. Contiene cf_soggetto_attuatore e
  cf_soggetto_beneficiario: il file Soggetto non serve.
- OpenCoesione, progetti_esteso_TOS_20260831 (dati al 31/08/2026),
  separatore ";". Colonne CF: OC_CODFISC_ATTUATORE,
  OC_CODFISC_BENEFICIARIO, OC_CODFISC_PROGRAMMATORE. CF di persone
  fisiche non pubblicati o anonimizzati. Copre solo coesione (FESR,
  FSE, FSC, PAC): non PNRR, non FEASR/GAL, non fondi regionali propri,
  non Caript. La pagina open data inglese è ferma a settembre 2024:
  usare quella italiana.
- Elenco beneficiari PR FSE 2021-27 all'11/09/2026: 38 righe sull'area,
  ridondante con OpenCoesione. Elenco beneficiari FESR non necessario.

Regola di chiusura: soddisfatta. Trovati nel PNRR:

- Polo infanzia Pian degli Ontani, Abetone Cutigliano, M4C1 I1.1,
  455.000 € (DD MIUR 57/2022)
- Mensa scuola media Fucini, San Marcello Piteglio, M4C1 I1.2,
  500.000 €
- Scuola Rodari Campo Tizzoro, San Marcello Piteglio, M2C3 I1.1,
  1.482.462 € (avviso Nuove scuole 2/12/2021)

Altre tracce verificate:

- FSC 2021-27, Accordo per la coesione Toscana: Rondò Priscilla lotti
  1 e 2 (1 + 2 mln, decreto 15428 del 09/07/2025, DGC Abetone
  Cutigliano 139 del 18/07/2025); Casetta Pulledrari, Unione, 2,7 mln.
- PR FESR Toscana 2021-27, San Marcello Piteglio: efficientamento
  scuola Don Milani, fotovoltaico mensa Fucini e palazzetto Bardalone
  ("non avviati").
- SNAI: interventi AIB dell'Unione, "Ludoteche di montagna" Abetone
  Cutigliano.
- Legge regionale di spesa: contributo straordinario 1,5 mln 2025-26
  ad Abetone Cutigliano per impianti di risalita (non è un bando).
- PNRR digitale (PA Digitale 2026): cloud, App IO, pagoPA, SPID/CIE,
  PDND, SUAP/SUE.

Qualità dei dati:

- Nel PNRR gli enti compaiono con CF o con partita IVA. Filtrare su
  entrambi:
  - Abetone Cutigliano 90060100477 / 01906470479
  - San Marcello Piteglio 90060110476 / 01906480478
  - Sambuca Pistoiese 80009370471 / 00838200475
  - Unione 90054130472 / 01845470473
- Una riga ha la P.IVA di Abetone Cutigliano ma il nome "Comune di
  Montelupo Fiorentino": il nome dell'ente non è una chiave affidabile.
- Il sito di San Marcello Piteglio etichetta la mensa M4C2 I1.2, il
  dataset M4C1 I1.2 (corretto il dataset).
- La farmacia (M5) elencata sul sito di San Marcello Piteglio non
  compare tra i progetti attuati dal comune: non verificato perché.

### 1.3 I comuni pubblicano bandi per le imprese

- 71 progetti OpenCoesione su 103 dei quattro enti vengono dal "Fondo
  per i comuni delle aree interne" (DPCM 24/09/2020): i comuni lo
  girano alle imprese con avvisi propri (Abetone Cutigliano 2021-2022,
  Sambuca 2020-2021).
- Il fondo copriva le annualità 2020-2022; il fondo comuni marginali
  (DPCM 30/09/2021) il 2021-2023. Flusso in esaurimento, residui spesi
  con ritardo.
- Esistono anche avvisi comunali di ristoro: San Marcello Piteglio,
  "Sostegno alle attività extra agricole" per i danni della chiusura
  del viadotto di Maresca (03/12/2025-18/12/2025), pubblicato nella
  pagina avvisi del comune.
- I comuni rilanciano bandi di altri enti (Caript Ricerca su Abetone
  Cutigliano, GAL AS01 su Sambuca).
- robots.txt siti istituzionali:
  - www.comune.abetonecutigliano.pt.it: "Disallow:" vuoto, consentito.
    Sitemap /home/info/sitemap.xml
  - www.comune.sambuca.pt.it: "Allow: /", consentito. Sitemap
    /sitemap.xml, feed RSS /it/feeds
  - www.comune.sanmarcellopiteglio.pt.it: reindirizza a
    /it-it/robots.txt, esito da rileggere con curl -L. Feed RSS
    /it-it/feed-rss. Pagina avvisi: /it-it/novita/avvisi
- Gli avvisi comunali per le imprese registrati come aiuti compaiono
  anche in Incentivi Italia (3.3); quelli per enti, cittadini e terzo
  settore no.
- Priorità avvisi comunali: media. Ingresso nella tabella fonti solo
  dopo aver verificato 2-3 avvisi reali con data per comune.

### 1.4 Decisioni strada 1

- Annullato il compito "script di ricognizione": l'analisi è fatta.
- Niente Apify né scraping per la ricognizione.
- File grezzi (contengono nomi di imprese e ditte individuali): fuori
  dal repository, non citati in documenti pubblici.

## 2. STRADA 2: CONSULENTE PILOTA (DA FARE)

Domande preparate, su casi concreti degli ultimi 12 mesi:

1. Ultimi tre bandi per cui hai preparato domanda per un cliente della
   montagna: quali erano e come li hai scoperti?
2. Quali canali controlli attivamente e con che frequenza?
3. Da chi ti arrivano segnalazioni senza cercarle (associazioni di
   categoria, CAA, Camera di commercio, GAL, comuni)?
4. Un bando scoperto troppo tardi: da dove arrivava?
5. Per le aziende agricole: passi da CAA o fascicolo ARTEA? Usi il
   cronoprogramma regionale FEASR?
6. I comuni della zona pubblicano bandi per le imprese? Te ne accorgi,
   e come?
7. Quanto prima della scadenza ti serve sapere di un bando per
   presentare domanda?
8. Quali bandi sono inutili per i tuoi clienti anche se formalmente
   applicabili?

Priorità: 1, 4, 7. La 7 decide se l'app privilegia bandi aperti o in
arrivo.

## 3. STRADE 3-4: FONTI REGIONALI, PROVINCIALI E NAZIONALI

### 3.1 Regione Toscana: pagine tematiche (oltre alla pagina bandi aperti generale, già acquisita)

a) CSR FEASR 2023-2027, bandi aperti (pagina filtro):
   <https://www.regione.toscana.it/it/sviluppo-rurale-2023-2027/bandi-aperti>
   Esempi: SRE01 giovani agricoltori 2026 (decreto 7331 dell'8/4/2026),
   SRG02 organizzazioni produttori (decreto 13255 del 15/6/2026), SRA31
   risorse genetiche forestali (decreto 14800 del 29/6/2026), SRB01
   zone montane 2026 (7,5 mln, scaduto 30/6/2026). Nessuno di questi è
   in Incentivi Italia (3.3).

   Qualità: SRA30 (BURT 31/12/2025) etichettato "Aperto": stato dalla
   scadenza.

b) Cronoprogramma bandi FEASR (bandi in arrivo):
   <https://www.regione.toscana.it/-/complemento-per-lo-sviluppo-rurale-2023-2027-bandi-in-programma>
   Ultimo aggiornamento: decisione GR 9 del 3/8/2026.

c) Politiche per la montagna, bandi aperti e in attuazione:
   <https://www.regione.toscana.it/politiche-per-la-montagna>
   Esempi: impianti aree sciabili (decreto 9092 del 23/4/2026, scaduto
   15/6/2026, graduatoria 4/8/2026), Residenzialità Toscana diffusa
   2025 (scaduto 9/11/2025), edicole montane 450 mila € (annunciato
   11/11/2026, stato da verificare). In Incentivi Italia compaiono voci
   per residenzialità, aree sciabili, Custodi della montagna, Sistema
   neve 2025, edicole 2025: edizioni da verificare.

- FOSMIT arriva tramite Regione: nessuna fonte nazionale separata.
- robots.txt www.regione.toscana.it: consentito, tranne ricerca e URL
  con "/asset_publisher/" (Liferay). Seguire solo link senza
  /asset_publisher/; in alternativa sitemap /sitemap.xml.

### 3.2 Camera di commercio Pistoia-Prato

- Pagina agevolazioni:
  <https://www.ptpo.camcom.it/servizi/agevol/agevolazioni.php>
- Bandi annuali ricorrenti (1,3 mln stanziati il 6/8/2026):
  digitalizzazione 4.0 e transizione energetica, formazione
  scuola-lavoro e competenze, turismo e cultura, internazionalizzazione,
  accompagnamenti export.
- robots.txt: consentito, tranne /php/, /ricerca/ e albo camerale.
- Coperta interamente da Incentivi Italia (3.3), con i bandi presenti
  entro la data di apertura: la pagina non serve come fonte, solo come
  verifica.
- NewsBandi resta un segnale per bandi di altri enti.

### 3.3 Incentivi Italia: file open data del catalogo (fonte primaria)

- Portale MIMIT (ex incentivi.gov.it, ora www.incentivitalia.gov.it),
  fusione con il Registro nazionale aiuti (Codice degli incentivi,
  D.Lgs. 184/2025).
- File: OpenData_Incentivi.csv dalla pagina
  <https://www.incentivitalia.gov.it/open-data>, sezione Incentivi.
  Scaricabile senza autenticazione (lo SPID serve solo per le funzioni
  avanzate del catalogo). Metadati: Metadati_Scheda_Incentivi_Italia
  (docx). Licenza CC BY 4.0, aggiornamento settimanale.
- Non usare la sezione Aiuti (aiuti individuali con dati personali).
- robots.txt (12/11/2026): standard Drupal, /open-data consentito. Il
  sito dichiara cookie di verifica umana: catalogo e API interna
  (/api/incentivi/calendario) non si leggono in automatico. Solo il
  file.
- "Programmi e Ricognizioni" (incentivi dei 3 anni successivi): dal
  2027.

Struttura del file (12/11/2026): 6.095 righe, 50 colonne, 18 MB,
separatore rilevato automaticamente. Colonne utili: ID_Incentivo,
Titolo, Descrizione, Soggetto_Concedente, Amministrazione_responsabile,
Data_apertura, Data_chiusura, Link_istituzionale, Regioni, Comuni,
Ambito_territoriale, Forma_agevolazione, Dimensione_beneficiari,
Tipologia_Soggetto, Obiettivo_Finalita, Settore_Attivita,
Agevolazione_Concedibile_Min/Max, Spesa_Ammessa_Min/Max.

- Date in formato YYYY-MM-DD: Data_apertura in 6.067 righe,
  Data_chiusura in 5.872 (assente per sportelli aperti). 14 righe con
  apertura futura (in arrivo).
- Link_istituzionale compilato al 100%: punta al sito dell'ente (CCIAA,
  comune, GAL, Regione). È la fonte da citare nell'app.
- Multivalore separati da `\,` (Regioni, Dimensione, Settore,
  Tipologia) e da `;` (Comuni).
- Regioni: gli incentivi nazionali elencano tutte le regioni (665 righe
  con 15+ regioni). Non esiste un valore "Nazionale".
- Comuni: lista dei comuni ammessi. Filtrare con corrispondenza esatta
  del token ("Abetone Cutigliano", "San Marcello Piteglio", "Sambuca
  Pistoiese"), mai per sottostringa (falsi positivi: San Marcello nelle
  Marche, Sambuca di Sicilia). Risultati: Abetone Cutigliano 24, San
  Marcello Piteglio 27, Sambuca Pistoiese 24. Escludendo le liste molto
  lunghe restano bandi pertinenti: CCIAA Pistoia-Prato, GAL
  MontagnAppennino AS01, PR FESR, SRG07, fondo aree interne.
- Ambito_territoriale: compilato solo in 729 righe. Filtro aggiuntivo,
  non primario.
- Errore di etichetta noto: Comunità Montana Lario Intelvese
  (Lombardia) taggata Toscana.

Copertura verificata:

- \+ CCIAA Pistoia-Prato: tutti i bandi noti 2024-2026.
- \+ GAL MontagnAppennino AS01 (20/05/2026-18/09/2026), link al sito del
  GAL. La pagina del GAL indica una proroga al 12/10/2026 (BURT n. 37
  del 16/09/2026), che il file non riporta: le date del catalogo
  possono non registrare le proroghe.
- \+ CSR: 15 bandi toscani con codice d'intervento, molti 2026 tramite
  GAL (SRD14, SRE04, SRD13, SRD09). Mancano SRE01, SRB01, SRG02, SRA31.
- \+ Comuni: Abetone Cutigliano (fondo aree interne 2022), San Marcello
  Piteglio (attività extra agricole, viadotto di Maresca). Nessun bando
  di Sambuca Pistoiese o dell'Unione.
- \+ Bando ISI INAIL: presente ("Avviso pubblico ISI 2025 - Toscana").

Regola di filtraggio proposta (da decidere):

- A. Comuni contiene esattamente uno dei tre comuni, oppure
- B. Soggetto_Concedente o Amministrazione_responsabile è uno dei
  quattro enti, la CCIAA Pistoia-Prato, il GAL MontagnAppennino o la
  Regione Toscana, oppure
- C. Regioni contiene Toscana e Comuni è vuoto (incentivi regionali o
  nazionali senza elenco di comuni).

Stato sempre calcolato da Data_apertura e Data_chiusura, mai
dall'etichetta. Da misurare: quante righe passano e quanto rumore
resta (prova a mano su un campione prima di fissare la regola).

### 3.4 INAIL bando ISI

- Bando annuale per le imprese: coperto da Incentivi Italia.

## 4. STRADA 5: EUROPA DIRETTA

- Esclusa. Interreg Italia-Francia Marittimo copre in Toscana solo
  Massa-Carrara, Lucca, Pisa, Livorno, Grosseto: Pistoia esclusa.
  Nessuna traccia di altri programmi diretti (LIFE, Horizon) per i
  quattro enti. I fondi europei arrivano tramite Regione e GAL.

## 5. QUADRO DELLE FONTI

| Fonte | Per chi | Priorità |
|---|---|---|
| Regione, bandi aperti generale | tutti | già acquisita |
| GAL MontagnAppennino | enti, terzo settore, imprese | prossima fonte da acquisire |
| Caript | enti, terzo settore | già nota |
| Incentivi Italia (file CSV) | imprese, nazionale, CCIAA | alta |
| Regione, CSR bandi aperti | aziende agricole e forestali | alta |
| Regione, cronoprogramma FEASR | come sopra (in arrivo) | alta |
| Regione, Politiche per la montagna | enti montani, imprese | alta |
| Avvisi siti comunali | enti, cittadini, terzo settore | media, dopo verifica |
| CCIAA agevolazioni | imprese | verifica (coperta) |
| NewsBandi CCIAA | segnale | segnale |
| INAIL ISI | imprese | coperta |
| FOSMIT, FSC, SNAI, PNRR | enti | escluse o coperte |
| Archivi atti comunali, Interreg | - | escluse |

## 6. REGOLA DI CHIUSURA DELLA RICOGNIZIONE

Una fonte entra solo se negli ultimi 12 mesi ha pubblicato almeno un
bando applicabile al territorio non presente in altre fonti acquisite.
La ricognizione è chiusa dopo due fonti candidate consecutive senza
apporto.

## 7. AZIONI APERTE (in ordine)

1. Decidere la regola di filtraggio del CSV Incentivi Italia (3.3) e
   misurarne il rumore su un campione.
2. Verificare se i bandi d'esempio CSR e montagna compaiono nella
   pagina bandi aperti regionale già acquisita.
3. robots.txt di San Marcello Piteglio con curl -L.
4. Verificare 2-3 avvisi reali con data sui siti dei tre comuni (quelli
   non destinati alle imprese, che Incentivi Italia non copre).
5. Intervista al consulente pilota (domande al punto 2).
6. Pista L.R. Toscana 45/2025 art. 6 (Buggiano): probabilmente ristori
   per la chiusura di ponti e viadotti (anche Pescia, Uzzano, San
   Marcello Piteglio), da verificare.
