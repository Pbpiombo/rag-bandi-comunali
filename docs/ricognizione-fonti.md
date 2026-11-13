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
9. Quanto tempo ti prende, in una settimana tipo, controllare i bandi e
   verificarne date e requisiti?
10. Usate un'applicazione o un servizio per trovare i bandi? Quale?

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

## 8. ANCI TOSCANA (13/11/2026)

ANCI Toscana come strumento per trovare enti e bandi, non come fonte.
Le schede ANCI non si salvano e non si citano: ogni dato sotto viene
dalla pagina ufficiale dell'ente. Nessuna chiamata al modello, nessuna
scrittura nell'archivio (letto in sola lettura).

### 8.1 Il sito

- robots.txt di ancitoscana.it: `User-agent: *` con `Disallow:` vuoto,
  tutto permesso; nessun blocco per i crawler di IA. WordPress, API
  `wp-json` leggibile.
- Schede dei bandi: categoria `bandi` (`/categorie/bandi/`), schede
  dello Sportello Montagna; 35 nel 2026, più 2 senza categoria. La
  categoria `notizie-montagna` nel 2026 non contiene bandi.
- Newsletter (generale e Sportello Montagna): solo iscrizione con un
  modulo Google, nessun archivio pubblico trovato. C'è anche un canale
  WhatsApp, escluso (social).
- Enti emittenti delle schede 2026 che non sono nella tabella `fonti`:
  ministeri (MIT, Istruzione, Cultura, MIMIT, MASAF/GSE), INAIL, Sport
  e Salute, Presidenza del Consiglio (disabilità), Fondo per la
  Repubblica Digitale, Fondimpresa, Cesvot, Sviluppo Toscana,
  Commissione europea ed European Urban Initiative, sei GAL fuori
  territorio. robots.txt controllati il 13/11/2026: tutti permettono
  le pagine segnalate; urban-initiative.eu vieta per nome ClaudeBot e
  anthropic-ai.

### 8.2 Stato dalla pagina ufficiale

Date lette dalle pagine il 13/11/2026 (`scarica`, `a_testo`, e
`scadenza_dichiarata` per le pagine regionali), non dalle schede ANCI.
Elenco generale della Regione riletto lo stesso giorno: 159 voci.

| bando | pagina ufficiale | apertura | chiusura | stato al 13/11 | perché la scansione non l'ha visto |
|---|---|---|---|---|---|
| Punti Digitale Facile, avviso 2026 | regione.toscana.it | 12/11/2026 | 26/11/2026 ore 12 | **aperto** | pubblicato sul BURT l'11/11, giorno della scansione: non era ancora nell'elenco; oggi c'è, candidato alla prossima |
| Sistema neve 2026, spese di funzionamento | sviluppo.toscana.it | 19/10/2026 ore 10 | 16/11/2026 ore 16 | **aperto** | solo su sviluppo.toscana.it, non nell'elenco della Regione |
| Fondo investimenti stradali nei piccoli comuni 2026 (comuni fino a 5.000 abitanti) | mit.gov.it | 10/11/2026 ore 12 | 30/11/2026 ore 12 | **aperto** | il MIT non è una fonte |
| Toscana Art Bonus, avviso per Comuni e Unioni in un Progetto di Paesaggio | toscana-notizie.it (comunicato del 12/11/2026) | 01/12/2026 | 31/03/2027 | **in arrivo** | avviso approvato dalla Giunta, "presto verrà pubblicato": non c'è ancora la pagina del bando. Date dal comunicato, da ricontrollare sull'avviso |
| Pro Loco, identità locali | regione.toscana.it | BURT 14/10/2026 | 03/11/2026 ore 13 | scaduto il 03/11/2026 | |
| Pro Loco, annualità 2026 | regione.toscana.it | BURT 08/07/2026 | 07/08/2026 ore 13 | scaduto il 07/08/2026 | |
| Progetti culturali per la popolazione carceraria 2026-27 | regione.toscana.it | 29/07/2026 | 07/09/2026 ore 12 | scaduto il 07/09/2026 | |
| Verifiche tecniche sismiche su edifici pubblici | regione.toscana.it | 02/07/2026 ore 12 | 01/08/2026 | scaduto il 01/08/2026 | |
| Farmacie disagiate 2026 | regione.toscana.it | | 03/07/2026 (frase nel testo, nessun campo di scadenza) | scaduto il 03/07/2026 | |
| SRE01 Giovani agricoltori 2026 | regione.toscana.it | 04/05/2026 | 22/06/2026 ore 13 (prorogato due volte) | scaduto il 22/06/2026 | |
| Campi estivi con pernottamento 2026 | regione.toscana.it | 10/06/2026 | 30/06/2026 ore 23.59 | scaduto il 30/06/2026 | |
| Festival di spettacolo dal vivo 2026 | regione.toscana.it | BURT 25/02/2026 | 03/04/2026 ore 15 | scaduto il 03/04/2026 | |
| Interventi in ambito sociale 2026 | regione.toscana.it | 22/01/2026 | 18/03/2026 ore 23.59 (prorogato) | scaduto il 18/03/2026 | |
| Centri commerciali naturali 2026 | sviluppo.toscana.it | 27/07/2026 ore 12 | 01/10/2026 ore 12 | scaduto il 01/10/2026 | |
| Arredi didattici innovativi per nidi e scuole dell'infanzia | istruzione.it | avviso 03/02/2026 | 03/03/2026 ore 18 | scaduto il 03/03/2026 | |

Perché mancano gli scaduti regionali: la Regione è stata scansionata
solo il 15/09/2026 (42 pagine) e l'11/11/2026 (135). Otto bandi
avevano già chiuso prima del 15/09; Pro Loco identità è stato aperto
e chiuso tra le due scansioni (14/10–03/11). Oggi nessuno è più
nell'elenco dei bandi aperti. Tutti sono scaduti da meno di 12 mesi:
con la regola dello storico sarebbero salvabili, se la scansione li
trovasse. L'etichetta "Stato" delle pagine regionali dice "In corso"
per quasi tutti: non conta, vale la scadenza.

### 8.3 Sviluppo Toscana

- Pubblica i bandi regionali che gestisce su
  `https://www.sviluppo.toscana.it/bando/<slug>/`. Elenco HTML
  leggibile: `/bandi/`, con filtro `?_stato=aperto`, `in-scadenza`,
  `in-arrivo`; 12 voci per pagina, pagine successive in
  `/bandi/page/N/?_stato=…`.
- robots.txt: su `www.sviluppo.toscana.it` risponde 404 (nessuna
  regola); su `sviluppo.toscana.it` vieta solo `/lib/` e `/bc/`.
- Oggi, per l'etichetta del sito: 39 "aperto", 1 "in scadenza" (neve,
  spese di funzionamento), 2 "in arrivo" (Energia immobili imprese,
  Energia imprese processi produttivi). Delle 39 "aperto", 29 sono
  procedure di rendicontazione o varianti per bandi già chiusi (slug
  con `_rend`, `_var`, `rendicontazione`, `varianti`), non bandi
  aperti a nuove domande. L'etichetta non è affidabile: la rete degli
  incubatori risulta "aperto" con il termine al 30/04/2024.
- **Bandi aperti a nuove domande, secondo le date della pagina: 9.**
  Con una data di chiusura: neve spese di investimento 2026 (fino al
  23/11/2026), neve spese di funzionamento 2026 (fino al 16/11/2026),
  IGP (fino al 31/12/2026). A sportello: Digitale P.A., datalake
  SmarToscana (riaperto con decreto 22706 del 09/10/2026, domande dal
  22/10/2026, per Comuni e Unioni di Comuni), 1.3.2 PMI BEI ed. 2026,
  1.3.2 PMI fino a 50.000 € ed. 2026, Minibond, PMI turismo, Campiano
  Montieri 2024 (territorio di altri comuni). FUNT 2025 riguarda
  progetti già ammessi dal Ministero del Turismo.
- Già in archivio, dalle pagine della Regione o dal catalogo Incentivi
  Italia: IGP, le due 1.3.2, Minibond, PMI turismo. **Mancano i due
  bandi neve e Digitale P.A.**, che nell'elenco generale della Regione
  non ci sono: Digitale P.A. è per i comuni e l'Unione, i bandi neve
  per i gestori degli impianti della Montagna Pistoiese.

### 8.4 Prima misura di copertura

Schede ANCI 2026 (37), contate per bando segnalato. Esclusi: sei GAL
fuori territorio (10 bandi), bandi europei (LIFE, CERV, European Urban
Initiative: segnalati da ANCI, esclusi per la demo), Sport Act
(Interreg Marittimo, area che esclude Pistoia), le schede di
programmazione che non sono bandi (cronoprogrammi FESR e FEASR, misure
PRAF 2026).

| gruppo | pertinenti | in archivio | mancano | perché mancano |
|---|---|---|---|---|
| Regione Toscana | 18 | 6 | 12 | 9 scaduti prima della scansione o tra le due scansioni (8.2); 2 solo su sviluppo.toscana.it (neve funzionamento, aperto; centri commerciali naturali, scaduto); 1 pubblicato il giorno della scansione (Digitale facile, aperto) |
| GAL MontagnAppennino | 2 | 2 | 0 | |
| Cesvot con fondi regionali (Siete presente, giovanisi.it) | 1 | 0 | 1 | ente non nella tabella `fonti` |
| enti nazionali | 10 | 0 | 10 | ente non nella tabella `fonti`. Nuova Sabatini e ISI INAIL sono nel catalogo Incentivi Italia, tra le righe da verificare a mano |
| **totale** | **31** | **8** | **23** | |

In archivio: amianto, mercati rionali, nidi gratis, Toscana Diffusa,
produzione di spettacolo dal vivo, riuso, AS01, SRD 14. Gli enti
nazionali sono MIT (fondo strade, aperto), Istruzione (arredi,
scaduto), Cultura (jazz 2027), MIMIT (Nuova Sabatini), INAIL (ISI),
MASAF con GSE (Parco Agrisolare), Presidenza del Consiglio (Vita &
Opportunità), Sport e Salute (Fabbrica spazi civici), Fondo per la
Repubblica Digitale (Zenit), Fondimpresa (formazione IA). Lo stato
dalla pagina ufficiale è stato letto solo per MIT e Istruzione.

Toscana Art Bonus non viene da una scheda ANCI e non è nel conteggio.

Lettura: copertura 8 su 31 (26%). Sui soli bandi regionali e del GAL,
le fonti già acquisite, 8 su 20: le mancanze vengono dalla frequenza
delle scansioni (due in due mesi) e da Sviluppo Toscana, non dalle
fonti mancanti. Oggi sono aperti e assenti dall'archivio tre bandi
segnalati da ANCI che riguardano i comuni o il territorio (Digitale
facile, neve funzionamento, fondo strade MIT), più due trovati su
Sviluppo Toscana e non segnalati (Digitale P.A., neve investimenti).
