# RICOGNIZIONE FONTI, STRADA 1 (DA CHI I BANDI LI HA VINTI)

Data: 12/11/2026.

## 1. ALBI E ARCHIVI ATTI

- L'albo pretorio non serve per lo storico: un atto resta pubblicato
  circa 15 giorni. Le delibere degli ultimi due anni stanno negli
  archivi atti dei gestionali:
  - Abetone Cutigliano: URBI (PA Digitale) su cloud.urbi.it
  - Unione Comuni Montani Appennino Pistoiese: URBI su cloud.urbi.it
  - San Marcello Piteglio: URBI su asp.urbi.it
  - Sambuca Pistoiese: albo.apkappa.it fino al 09/02/2026, Hypersic
    dal 10/02/2026
- robots.txt (verificato il 12/11/2026): cloud.urbi.it, asp.urbi.it e
  albo.apkappa.it vietano l'accesso automatico (Disallow: /). Hypersic
  non ha robots.txt, ma copre solo Sambuca dal 10/02/2026: non si
  automatizza.
- Decisione: nessuna lettura automatica di albi o archivi atti
  comunali; consultazione solo a mano e mirata. Gli archivi comunali
  non entrano nella tabella fonti.

## 2. CANALI DI FINANZIAMENTO EMERSI

- Leggi regionali di spesa: contributo straordinario ad Abetone
  Cutigliano per la revisione degli impianti di risalita, 1,5 mln tra
  2025 e 2026. Non è un bando.
- FSC 2021-2027 tramite Regione: Rondò Priscilla, decreto 15428 del
  09/07/2025. Negoziato, non a bando.
- PNRR, progetti verificati nel dataset regionale:
  - Polo infanzia Pian degli Ontani, Abetone Cutigliano, M4C1 I1.1,
    455.000 euro
  - Mensa scuola Fucini, San Marcello Piteglio, M4C1 I1.2, 500.000
    euro (il sito del comune riporta M4C2, il dataset M4C1)
  - Scuola Rodari di Campo Tizzoro, San Marcello Piteglio, M2C3 I1.1,
    1.482.462 euro
- Unione: Casetta Pulledrari (Regione, Fondo Turismo); ex stazione
  FAP, 400 mila euro da un bando per la montagna, probabilmente FOSMIT
  (dedotto, data non nota).
- GAL MontagnAppennino: bando AS01, 710.624 euro, contributi 20-80
  mila al 90%, per enti pubblici, fondazioni, associazioni,
  cooperative di comunità, Pro Loco. Scaduto alle ore 13 del
  12/10/2026, dopo la proroga pubblicata sul BURT n. 37 del
  16/09/2026.
- Imprese di Abetone Cutigliano (fonte: Regione, 10/11/2026): 6,3 mln
  di contributi regionali e FESR per impianti di risalita, custodi
  della montagna, bandi neve, innovazione, voucher garanzia,
  internazionalizzazione. Ogni voce è una linea di bando regionale da
  verificare.

## 3. FILE APERTI ANALIZZATI

- PNRR Regione Toscana (getOpenData_v6.csv, aggiornato al 23/10/2026):
  contiene i codici fiscali di attuatore e beneficiario.
- OpenCoesione, progetti in Toscana (dati al 31/08/2026): copre solo
  coesione (FESR, FSE, FSC, PAC), non PNRR, FEASR/GAL, fondi regionali
  propri, Caript.
- Elenco beneficiari PR FSE 2021-27 (all'11/09/2026): ridondante con
  OpenCoesione.
- Regola di chiusura dell'analisi soddisfatta: i tre progetti PNRR
  verificati compaiono nei dati.

## 4. QUALITÀ DEI DATI

- Nel PNRR gli enti compaiono con codice fiscale o con partita IVA:
  - Abetone Cutigliano 90060100477 / 01906470479
  - San Marcello Piteglio 90060110476 / 01906480478
  - Sambuca Pistoiese 80009370471 / 00838200475
  - Unione 90054130472 / 01845470473
- Il nome dell'ente non è una chiave affidabile: una riga ha la
  partita IVA di Abetone Cutigliano con il nome di un altro comune.

## 5. SCOPERTA

- 71 progetti OpenCoesione su 103 dell'area vengono dal Fondo per i
  comuni delle aree interne: i comuni lo girano alle imprese con
  avvisi propri (contributi a fondo perduto per attività commerciali e
  artigianali). I comuni sono quindi una fonte di bandi per imprese
  non coperta altrove.

## 6. DECISIONI

- Script di ricognizione: annullato, l'analisi è stata fatta a mano.
- Nuova candidata per la tabella fonti: le sezioni "Avvisi" dei siti
  istituzionali dei tre comuni, previa verifica del robots.txt.
- Canali da verificare: PR FESR e PR FSE+ Toscana 2021-27. Esclusi
  come fonti di bandi: FSC e SNAI (negoziati), PNRR (in chiusura nel
  2026).
- I file grezzi contengono nomi di imprese e ditte individuali:
  restano fuori dal repository e non vanno riportati in documenti
  pubblici.
