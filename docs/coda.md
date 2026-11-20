# Coda

Voci in attesa, spostate da `docs/roadmap.md` il 18 novembre 2026. Ogni
voce conserva il suo numero originale tra parentesi, perché i documenti più
vecchi la citano così. L'ordine di lavoro è in `docs/roadmap.md`, "Ordine
dei passi": accanto alle voci che richiama c'è "→ passo N".

## Difetti dalla prova completa del 14 novembre

Difetti e richieste emersi dalla prova completa dall'app del 14 novembre
2026, in ordine: prima i più visibili per chi usa l'app.

- (era la voce 1 dei Difetti del 14/11) **Verificatore, "21/27" letto come data** (in correzione prima della
   demo). In "PR FESR Toscana 21/27" il "21/27" è preso per una data, anche
   se il mese 27 non esiste, e risulta "non presente in nessuna fonte" pur
   stando nel titolo del bando D1.10. Due difetti: date impossibili
   accettate come date; titolo non confrontato, o normalizzato in modo
   diverso. Falso negativo frequente: molti titoli FESR contengono "21/27".
   Priorità alta.
- (era la voce 2 dei Difetti del 14/11) **Frammenti documentali non citati mostrati sotto la risposta**. Con
   `dettaglio_bando` e `documenti: true` compaiono 10 frammenti (CENSIS,
   coesione, progetto del Comune) sotto la risposta su Sport Missione
   Comune. Mostrare solo i frammenti citati.
- (era la voce 3 dei Difetti del 14/11) **Router, "Anomalia del router: risposta non interpretabile"** (in
   correzione prima della demo). Compare all'utente su una domanda fuori
   ambito (apertura degli impianti sciistici). Da unire alla voce già in
   coda sulle domande fuori ambito con frase fissa.
- (era la voce 4 dei Difetti del 14/11, → passo 2a) **Pertinenza**: nella domanda sulle attività artigianali compare il
   bando delle risorse genetiche agrarie. Controllare cosa restituisce
   `bandi_per_beneficiario` per gli artigiani.
- (era la voce 5 dei Difetti del 14/11) **"fra 16 giorni" risulta verificato**: controllare da dove viene il
   16 nella riga del bando (giorni calcolati dal programma, o
   coincidenza con un altro numero).
- (era la voce 6 dei Difetti del 14/11) **Bando CCIAA Pistoia-Prato promozione turistica 2026, beneficiari dal
   catalogo imprecisi** ("Consorzio, Micro/Piccola/Media impresa", "enti
   pubblici da verificare"). Nell'edizione 2025 erano ammessi consorzi,
   società consortili e cooperative senza scopo di lucro per la promozione
   del territorio, e fondazioni culturali della tabella regionale; i Comuni
   davano solo dichiarazioni di condivisione (punteggio). Verificare a mano
   la pagina 2026.
- (era la voce 7 dei Difetti del 14/11) **La frase "i beneficiari pubblici vanno verificati sulla pagina"
   ricorre anche dove non serve**: controllare da dove nasce.
- (era la voce 8 dei Difetti del 14/11) **Scelta tra Comuni e Unione nell'interfaccia**: decidere dopo il
   riscontro del consulente pilota.
- (era la voce 9 dei Difetti del 14/11) **Ente del profilo diverso dal comune nominato nella domanda** ("Ho un
   ristorante a San Marcello" con il profilo di Abetone): il modello lo
   segnala. Valutare un avviso dell'app o la scelta automatica dell'ente.
   Secondo caso, P08 del lotto 2 ("Ho un negozio di alimentari a Sambuca",
   profilo di Abetone): il modello non segnala la differenza, ma scrive
   "Sambuca Pistoiese ricade in Toscana, ma questo dato non risulta tra
   quelli in mio possesso": usa una conoscenza sua e insieme dichiara che
   non è nei dati, perché il programma passa solo il profilo dell'ente del
   menu, mentre la tabella `enti` ha Sambuca Pistoiese con la regione.
   Soluzione proposta: il programma riconosce nella domanda i nomi dei
   comuni della tabella `enti`, senza modello (confronto di testo), e
   aggiunge un blocco "comune nominato nella domanda" con regione,
   provincia, Unione e fonte; il codice dell'ente resta passato dal
   programma.

   Dettaglio del passo 18 della roadmap, spostato il 18/11/2026: Casi da
   coprire: menu "Comune" e domanda da privato; soggetti di due tipi;
   chi vuole aprire un'attività; il consulente che chiede per conto di
   altri; comune nominato diverso dal profilo.
- (era la voce 10 dei Difetti del 14/11, → passo 4) **Domande da imprenditore** ("vorrei aprire una palestra", "un laghetto
    da pesca"): restituiscono soprattutto bandi generici per PMI a
    sportello. Valutare la ricerca per bisogno, già nei prossimi passi
    (voce 6).
- (era la voce 11 dei Difetti del 14/11) **"Frammenti" nel prompt e nell'app, da rinominare insieme**: il
    modello di risposta legge "frammento" o "frammenti" in 12 punti (10
    righe delle `ISTRUZIONI`, l'intestazione "FRAMMENTI:" del messaggio, il
    segnaposto "(nessun frammento documentale)") e ripete la parola nelle
    risposte nonostante il divieto di D3 (A05 del lotto 2, L05 del lotto
    1); nell'app il pannello "Fonti" si intitola "Frammenti documentali".
    Proposta: "estratti dei documenti" in tutti e due ("ESTRATTI DEI
    DOCUMENTI:", "[numero dell'estratto]", "(nessun estratto dei
    documenti)"), e "DATI:" in "DATI DELL'ARCHIVIO:", da cui nascono "i dati
    a disposizione" e "i dati in mio possesso" (P08). Etichette [n] e
    [Dn.k], forma "(fonte: …)" e verificatore invariati; divieto di D3
    aggiornato. Misura con `--codici` su A05 (lotto 2) e L05 (lotto 1), con
    l'espressione regolare di controllo estesa a "a disposizione" e "in mio
    possesso".
- (era la voce 12 dei Difetti del 14/11) **Catena ricostruita da sola dopo un push**, da provare con calma: oggi
    dopo un push che tocca `src/` serve il riavvio dell'app online (README,
    "App online"), perché Streamlit non ricarica i moduli di `src/` e la
    catena è in `st.cache_resource`. Proposta del 15/11/2026, da
    rivalutare insieme alla struttura dell'app e non una decisione presa:
    l'impronta dei file `.py` di `src/` calcolata a ogni esecuzione dello
    script; se cambia, si tolgono i moduli `src.*` da `sys.modules` e
    l'impronta entra nella chiave di `carica_catena` e `carica_recupero`.
    È un requisito dell'aggiornamento settimanale (Prossimi passi, voce
    3), dove i push li fa GitHub Actions. Scartate:
    `server.folderWatchList` (percorsi assoluti, diversi in locale e
    online), lo script spostato nella radice (cambia il file principale su
    Streamlit Cloud), `importlib.reload` (non ricarica chi importa il
    modulo). Diagnosi in `docs/piano-correzioni-lotto1.md`, "Osservazioni
    dall'app online del 15 novembre 2026", punto 2.
- (era la voce 13 dei Difetti del 14/11) **Due dati incompleti trovati nello storico** (diagnosi di G1, 16
    novembre 2026, `docs/piano-correzioni-lotto1.md`, correzione G):
    - SRA28 (premi annuali per gli imboschimenti): la `frase` delle righe
      di `beneficiari_bando` è tagliata prima di "SRD05" ("… che hanno
      beneficiato di un sostegno per gli impianti di imboschimento").
      Il requisito c'è nelle `condizioni` e nel campo beneficiari di
      `bandi`;
    - Nidi gratis 2026-2027: il secondo termine, il 6/10/2026 per i Comuni
      già candidati, è solo nella `scadenza_nota`, non in
      `scadenze_bando`.
- (era la voce 14 dei Difetti del 14/11, → passo 2a) **Risorse genetiche forestali 2026 e SRA28, frase classificata sotto
    quasi tutti i tipi**: "proprietari, possessori, pubblici o privati …"
    ha una riga per quasi ogni tipo di beneficiario (anche
    `impresa_turistica`, `professionista_autonomo`,
    `cittadini_famiglie`), con la condizione su ogni riga. Questi bandi
    compaiono a quasi ogni domanda d'impresa: da rivedere nel controllo
    degli scarti.
- (era la voce 15 dei Difetti del 14/11) **`scadenza_nota` confrontata con la frase della pagina**, come i
    beneficiari: oggi la nota estratta dal modello non ha una prova. Caso
    di SRA28: la nota ("le domande … fino al 2029 come ultima annualità
    ammessa") è vera, ma non dice che le annualità valgono solo per chi
    ha già l'impegno SRD05.
- (era la voce 16 dei Difetti del 14/11, → passi 3 e 7) **Decisione del router a maggioranza tra le 3 chiamate**, da
    proporre come modifica al codice a parte. Oggi l'app usa la prima
    chiamata, e le tre non sono sempre d'accordo: nella regressione del
    16/11/2026 C02, C12, P09 e P22 hanno cambiato interrogazione o perso
    la seconda, e la stessa variabilità c'era già prima della correzione
    G (`docs/piano-correzioni-lotto1.md`, correzione G5). Fa parte
    dell'architettura della risposta in due passi, prima voce dei
    "Prossimi passi".

    Casi di prova, dalla regressione finale del 16/11/2026: P22, C02 e
    P24.
    - **P22 è il primo caso da usare per misurare il router a
      maggioranza.** Passa da 4 bandi citati a freddo a "Non trovo".
      Prima di G 2 chiamate del router su 3 sceglievano
      `bandi_per_beneficiario` più `bandi_per_tema`; dopo G, 9 chiamate
      su 9 scelgono solo `bandi_per_beneficiario`. È uno spostamento
      sistematico, non variabilità: la maggioranza non lo correggerebbe.
    - **Prima di cambiare il router** va capito se lo spostamento
      dipende dalla voce `bandi_scaduti_per_ente` nel repertorio o
      dall'esempio aggiunto nelle istruzioni del router (correzione G1).
    - **C02**: spostamento più debole, `bandi_aperti_per_ente` scelta in
      2 chiamate su 3 prima di G e in 4 su 9 dopo.
    - **P24** cita 1 bando invece di 2: il router sceglie una sola
      interrogazione tra tema e beneficiario.

    La strategia (maggioranza, unione, ripieghi) si sceglie dopo la
    simulazione senza modello: "Indicazioni del revisore tecnico
    (18/11)", punti 3 e 4 (oggi in coda.md,
    "Revisore tecnico (18/11/2026)", "Ordine dei passi proposto, superato").

    Dettaglio del passo 3 della roadmap, spostato il 18/11/2026: Quattro
    strategie: prima chiamata (oggi), maggioranza, unione delle scelte
    delle chiamate, unione più ripieghi nel codice. Un tema fuori elenco
    conta come anomalia (caso P11: tema "montagna").
- (era la voce 17 dei Difetti del 14/11, → riempitivi) **Verificatore, citazione posta prima della condizione**: il dato si
    cerca anche nella citazione precedente della stessa voce di elenco.
    Caso P01 della regressione finale del 16/11/2026: la citazione sta
    prima della condizione, e la delibera 704/2025 viene associata al
    bando successivo ("presente invece in D1.8").
- (era la voce 18 dei Difetti del 14/11, → riempitivi) **Verificatore, orari**: "16,00" e "16:00" letti come orario e
    confrontati con il testo della fonte. Caso P21 della regressione
    finale del 16/11/2026: "16,00" risulta non trovato (falso allarme).

## Da "Prima della demo con il consulente pilota", ancora aperte

- (era tra le voci di "Prima della demo") **Toscana Art Bonus**, da estrarre quando esce l'avviso (dal 1°
  dicembre), dal recupero dei bandi aperti mancanti
  (`docs/ricognizione-fonti.md`, sezione 8).
- (era tra le voci di "Prima della demo") **Controllo degli scarti**: un file con le righe da verificare e gli
  scarti definitivi, con titolo, ente e motivo, ordinati mettendo in cima
  quelli che nominano comuni, enti locali, montagna, impianti, sport,
  scuole, turismo, imprese agricole o turistiche. Da includere:
  - le 6 righe di `beneficiari_bando` in archivio la cui frase non nomina
    il soggetto (controllo del 13/11/2026, attivo solo sulle estrazioni
    nuove): "Bando 2026 Pmi" (4 righe, frase "I suddetti soggetti devono
    operare nei settori ammissibili…"), scuole paritarie ("Famiglie" con
    i requisiti del bambino), alta formazione ("Università pubbliche" con
    la frase sul partenariato). Da correggere alla prossima riestrazione
    di quei bandi;
  - `incentivi-2504`: la sua pagina ha i contatti di un polo digitale del
    Friuli Venezia Giulia (IP4FVG); verificare perché è in archivio, se
    la regola territoriale di Incentivi Italia lo lascia passare per
    errore;
  - i bandi con dati mancanti non recenti (pubblicati da più di due anni,
    o con l'anno nel titolo più vecchio dell'anno scorso), che la sezione
    "Da approfondire" dell'app non mostra: es. festival 2021 e 2022,
    rievocazioni 2021.
- (era tra le voci di "Prima della demo", → passo 16) **Prova di copertura**: elenco esterno di bandi rilevanti per il
  territorio nel 2026 (schede ANCI, BURT, consulente pilota). La
  ricognizione ANCI è la prima misura.
- (era tra le voci di "Prima della demo") **Regola "niente si scarta in silenzio"**: righe da verificare e scarti in
  un elenco che si rilegge a ogni aggiornamento.
- (era tra le voci di "Prima della demo") **Insieme di prova dell'estrattore**: dai bandi delle due verifiche a
  mano, con i valori controllati sulla pagina, per misurare quanti campi
  coincidono dopo ogni modifica al prompt o alle regole.
- (era tra le voci di "Prima della demo") **Barra laterale, tabelle vuote**: scelta di presentazione per le righe
  "bilancio: VUOTA" e "turismo: VUOTA" che compaiono oggi. Da decidere:
  nasconderle o riformularle come dati in arrivo.
- (era tra le voci di "Prima della demo", → passo 2a) **Se c'è tempo: Nuova Sabatini, Smart&Start, ISI INAIL verificati a
  mano**, con la frase della pagina come prova: misure nazionali per le
  imprese escluse dalla regola degli sportelli ma ancora attive
  (Incentivi Italia, tappa 5: sportelli senza chiusura aperti da più di
  due anni, 17 righe da verificare).

## Primo compito di dati dopo la demo

- **Bandi senza tema**: 49 bandi in archivio non hanno tema, tutti da
  Incentivi Italia (`OpenData_Incentivi.csv`); 12 sono aperti al
  14 novembre 2026 (calcolato con `scaduto`). `bandi_per_tema` non li
  trova mai, nemmeno con un tema dell'elenco chiuso `TEMI`
  (`src/estrazione/beneficiari.py`). Assegnare il tema, con la fonte, a
  partire dagli aperti. Viene dalla correzione 2 di
  `docs/piano-correzioni-lotto1.md`.

## Architettura della risposta

Era la prima voce dei "Prossimi passi", prima delle voci numerate. → passo 9;
i principi sono in `docs/roadmap.md`.

Oggi il modello decide insieme tre cose: quali bandi sono pertinenti, la
forma della risposta e il testo. Lo guida un prompt con molte regole che
interagiscono. Caso del 16/11/2026: G3, corretta da sola, ha trasformato
8 risposte in rifiuti (`docs/piano-correzioni-lotto1.md`, correzione
G5).

Proposta:
- (1) il modello classifica ogni bando dei dati come pertinente,
  generico possibile o non pertinente, con la frase che lo giustifica,
  in uscita strutturata;
- (2) il codice decide la forma: "Non trovo", solo bandi generici,
  oppure bandi pertinenti;
- (3) il modello scrive il testo dentro quella forma.

Insieme:
- router con la strategia scelta dopo la simulazione (unione,
  maggioranza o prima chiamata, più ripieghi nel codice), per esempio il
  ripiego sull'elenco dei bandi aperti per l'ente (caso C02). Vedi la voce
  16 di "Dopo la demo: dalla prova completa del 14 novembre" e
  "Indicazioni del revisore tecnico (18/11)", punti 3 e 4 (oggi in
  coda.md, "Revisore tecnico (18/11/2026)", "Ordine dei passi proposto, superato");
- distinzione tra bandi generici per imprese, che valgono per quasi ogni
  investimento, e bandi a scopo preciso per enti, che non vanno proposti
  come generici;
- dati ordinati per vicinanza alla domanda, invece di elenchi piatti;
- meno regole nel prompt, scritte come tabella di decisione;
- attese di prova sulla forma della risposta: non comincia con "Non
  trovo", nomina X come generico, non nomina Y.

Realizzazione come flusso a passi fissi, non come agente libero. Si
parte con funzioni semplici in sequenza; LangGraph serve solo con rami
o cicli (punto 6 delle Indicazioni del revisore tecnico; oggi in coda.md,
"Revisore tecnico (18/11/2026)", "Ordine dei passi proposto, superato").
- Il modello decide solo in punti definiti: router, classificazione,
  scrittura, ed eventualmente un validatore che segnala bandi omessi o
  affermazioni senza supporto.
- Il validatore si tara sui giudizi a mano, come il modello giudice
  ("Insieme di prova: dopo").
- I giri sono limitati.
- Ripieghi e forma della risposta li decide il codice.

## Prossimi passi, voci numerate

- (era la voce 1 dei Prossimi passi) **Scheda per bando**: per chi è e per cosa si può usare, divisa per tipo di
   beneficiario, con le clausole citate. Quello che il bando dice e i possibili
   usi proposti dal sistema restano visibilmente separati.
- (era la voce 2 dei Prossimi passi) **Riepilogo**: bandi nuovi con le loro schede, filtrati sulle sue
   ricerche scritte in un file. Prima mandato a mano, poi automatico.
- (era la voce 3 dei Prossimi passi, → passo 11) **Aggiornamento almeno una volta a settimana**: GitHub Actions lancia la
   scansione, salva CSV e database, manda il riepilogo. La frequenza non può
   essere più bassa: dalla ricognizione ANCI del 13 novembre 2026, con due
   sole scansioni della Regione (15/09 e 11/11) il bando Pro Loco identità
   locali è stato aperto e chiuso tra l'una e l'altra, e Punti Digitale
   Facile è uscito il giorno stesso della scansione. Oltre ai bandi nuovi,
   si ricontrollano i bandi aperti e quelli chiusi da poco, per le proroghe:
   la riclassificazione dell'11 novembre 2026 ha trovato le risorse
   genetiche forestali prorogate al 13 novembre, mentre l'archivio le dava
   scadute il 30 settembre. Per ogni pagina si conserva un'impronta del
   testo: un bando aperto si riestrae solo se la sua pagina è cambiata,
   così il ricontrollo non costa una nuova estrazione a ogni giro.

   Anche gli scarti "scaduto" di `scansioni` vanno ricontrollati, non
   solo i bandi in archivio. Caso del 12 novembre 2026: "premi annuali
   ad ettaro per mantenere imboschimenti" (SRA28) è registrato come
   "scaduto il 2026-06-30", che è uno scarto definitivo, ma è un bando
   a domanda annuale: il 30 giugno è il termine dell'annualità 2026, e
   le domande si possono presentare fino all'annualità 2029. La pagina
   regionale lo dà "Aperto". Riestratto quel giorno con una chiamata,
   senza salvarlo (`docs/piano-fonti.md`).

   **Requisiti da completare prima di attivarlo** (dettagli nelle voci
   indicate di `docs/revisione-2026-11-12.md`):
   - voce 2: l'estrattore controlla che il valore compaia nella sua prova,
     con il modulo di normalizzazione del blocco A;
   - voce 7: le pagine scadute da poco tornano candidate, per le proroghe;
   - voce 8: le correzioni a mano su `bandi` protette dalla riestrazione;
     anche le righe di `beneficiari_bando` con origine `manuale`, come le
     date `manuale` di `scadenze_bando`: oggi `salva` sostituisce tutte le
     righe dei beneficiari di un bando riestratto, e la riga "– Imprese;"
     di neve investimenti 2026 andrebbe persa;
   - voce 9: nessuna desincronizzazione tra database e CSV (righe scartate
     al caricamento, ricreazione su database esistente, esportazione solo
     a fine corsa);
   - voce 13: test del percorso di `estrai_nuovi` su pagine salvate;
   - voce 15: fonte dei bandi letta dalla tabella `fonti`;
   - controllo periodico, senza modello, degli elenchi "bandi aperti"
     dei programmi (PR FESR, PR FSE+, sviluppo rurale): le pagine che
     hanno in più rispetto all'elenco generale. Il 12 novembre 2026
     erano contenuti per intero nell'elenco generale, e per questo non
     sono stati aggiunti come elenchi (`docs/piano-fonti.md`, tappa 2);
   - ricostruzione automatica della catena dopo un push: con i push
     automatici di GitHub Actions nessuno fa Reboot app, e l'app
     mostrerebbe istruzioni o archivio vecchi. Vedi la voce 12 di "Dopo
     la demo: dalla prova completa del 14 novembre".
- (era la voce 4 dei Prossimi passi, → D) **Pratiche (progetti seguiti)**: per un beneficiario preciso, una
   scheda strutturata (attività con forma giuridica, ATECO, sede,
   dimensione; bandi seguiti con stato; scadenze; documenti; note), ogni
   dato con la sua fonte ("dichiarato dall'utente il …" distinto da
   "verificato su …"). La chat legge e aggiorna la scheda, non è la
   memoria. Avvisi sui bandi nuovi abbinati alla scheda senza modello.
   Seguito di conversazione: decidere quale contesto passa alla domanda
   successiva e come il verificatore tratta i dati citati in una
   risposta precedente. Unisce le voci 8 e 10. Richiede prima le voci 1 e
   3. Prima di costruirla: obblighi sui dati personali (informativa,
   consenso, conservazione, eventuale pagamento) e cosa serve al
   consulente pilota per seguire una pratica.

   - Tabella ATECO ufficiale (classificazione ISTAT ATECO 2025 e tavola di
     raccordo ATECO 2025-2022, con fonte per riga) per mostrare i codici
     candidati con la descrizione ufficiale e verificare i codici citati;
     mai per attribuire un codice a chi chiede. Caso: L02 ha scritto 56.10
     dalla memoria del modello, codice della classificazione precedente
     (dal 1° aprile 2025 la ristorazione è 56.11.x). Richiede anche le
     condizioni ATECO dei bandi estratte come codici.
- (era la voce 5 dei Prossimi passi, → D) **Profilo territoriale dell'ente**: per ciascun comune, con fonte per
   ogni dato, riserve naturali statali (in montagna pistoiese risultano
   riserve biogenetiche come Abetone, Campolino, Pian degli Ontani,
   Acquerino: comune di appartenenza da verificare), siti Natura 2000
   (ZSC/ZPS) e obbligo di valutazione di incidenza, vincolo idrogeologico
   e paesaggistico, piani urbanistici. Serve alle pratiche (autorizzazioni
   per le attività) e ai bandi con premialità per aree protette o Natura
   2000. Raccoglie le voci spostate qui il 15 novembre 2026:
   - altitudine dei tre comuni (minima, massima, del centro) dallo stesso
     file "Altimetria Comuni al 31 dicembre 2021", con un'interrogazione
     per i dati del territorio; serve alla domanda sull'altitudine
     scartata tra gli esempi (era in coda, dopo la demo);
   - zona sismica dei tre comuni: riferimento OPCM 3274/2003 aggiornata
     dalla DGRT 421 del 26/05/2014, da verificare sull'allegato e su
     eventuali aggiornamenti (era in coda);
   - colonna `montano` nel profilo: i tre comuni sono totalmente montani
     (Delib. CR 10/2025) (era in coda);
   - premialità per area interna (Punti Digitale Facile, categorie D, E,
     F): categoria dell'area interna del Comune nel profilo dell'ente,
     con fonte ufficiale (era la voce 9 di "Dopo la demo: dalla prova
     completa del 14 novembre").
- (era la voce 6 dei Prossimi passi, → passo 4) **Ricerca per bisogno**: l'utente descrive cosa vuole fare, il sistema cerca
   tra gli interventi ammissibili. Caso di prova: "devo rifare la piazza"
   → bando mercati rionali. (Lo stato del bando nei frammenti è già fatto,
   P3.)

   **PDF dei bandi**: solo bandi aperti, o chiusi da poco se ricorrenti, e
   rivolti ai tipi di beneficiari serviti. Per ogni bando solo il testo
   del bando o dell'avviso; modulistica conservata come collegamento,
   non indicizzata; decreti, graduatorie e rettifiche esclusi salvo
   quelle che cambiano scadenze o requisiti. Scelta degli allegati prima
   con le etichette della pagina. PDF scansionati riconosciuti con la
   densità di testo e segnati "da OCR", non indicizzati in automatico:
   l'OCR sbaglia i numeri, e il verificatore li darebbe per buoni. File
   .pdf.p7m da aprire prima della lettura. Se pagina e testo del bando
   non coincidono, vale il testo del bando.

   Lettura dei PDF: valutare PyMuPDF al posto di pypdf (ordine del testo,
   tabelle, immagini). Il testo dentro le immagini richiede comunque
   l'OCR e resta "da OCR", non indicizzato in automatico. PyMuPDF è
   AGPL: da riconsiderare se il servizio diventa a pagamento.
   L'alternativa con licenza permissiva per le tabelle è pdfplumber, da
   provare. Per il passo 19 si usa il lettore attuale; la valutazione di
   PyMuPDF viene dopo la prima prova, se i testi estratti non bastano.

   **PDF degli avvisi dei bandi aperti (passo 19, 19/11/2026).**
   L'avviso in PDF dei bandi aperti entra nell'archivio dei documenti,
   legato al bando con `id_bando`; è un prerequisito del passo 9, non
   una correzione delle risposte.
   - prima prova su circa 12 bandi: gli 8 con "non_basta" nelle
     etichette più i bandi aperti per il Comune non già compresi;
   - uno script propone per ogni bando i link ai PDF con etichetta,
     numero di pagine e leggibilità del testo; l'elenco si approva a
     mano prima di caricare;
   - solo l'avviso, più un allegato se la pagina vi rimanda per
     beneficiari o codici ATECO; i PDF scansionati restano "da OCR";
     lettore attuale, nessuna dipendenza nuova;
   - solo file consentiti dai robots.txt; per i siti non regionali il
     robots.txt si legge prima, uno per uno;
   - fuori dal passo: estrazione di punteggio minimo, criteri,
     premialità e cumulo dagli avvisi;
   - nota: oggi l'app consulta i documenti solo quando il router lo
     decide, quindi il caricamento da solo non migliora le domande
     "ci sono bandi per…".
   - Tre tipi di pagina, visti il 19/11/2026: pagine ricche (per
     esempio Credito Sportivo); pagine brevi che rimandano al PDF (per
     esempio il bando parcheggi); notizie al posto della pagina del
     bando (fondo strade del ministero: un solo intervento estratto).
     Anche le pagine ricche si approfondiscono molto nel PDF.
   - La scansione della Regione (`scopri_bandi`, `elenco.py`) non legge
     il robots.txt: da aggiungere prima della prossima scansione. Da
     decidere a parte: `INTESTAZIONI` si presenta come un browser. Al
     compito 19b si prova, sui quattro host della prima prova, se
     un'intestazione che dichiara il progetto viene accettata; se un
     host la rifiuta, decide chi mantiene il progetto, host per host.
   - Il modello di embedding ha `max_seq_length` 128: la parte densa
     della ricerca vede circa il primo terzo di un frammento di 1500
     caratteri. Da misurare al compito 19d prima di cambiare la
     divisione in frammenti o il modello. (20/11/2026: misura zero più
     sotto, "Passo 19d".)
   - **Stesso file per più bandi**: "Codici Ateco ammissibili" (PMI 50
     mila, decreto 9505 All. 4) e "Codici attività ammissibili" (PMI EU
     blending, decreto 9506 All. 4) hanno lo stesso sha256. Il registro
     del 19c va tenuto per impronta del file, con più `id_bando` per un
     file, non una copia per bando; Chroma accetta un solo valore per
     metadato, quindi il legame bando-frammento passa dal registro.
     (19c, 20/11/2026: fatto così, `id_bandi` con "|"; un file con uso
     "frammenti" per più bandi ferma il caricamento. La versione di Chroma
     in uso, 1.5.9, accetta metadati a lista: provato in memoria il
     20/11/2026, non usato.)
   - **Allegati di soli codici**: gli elenchi di codici ATECO o NACE (236
     pagine) non si dividono in frammenti di testo come un avviso: si
     caricano come dato strutturato o si escludono dall'archivio dei
     documenti. Da decidere al 19c. (Deciso il 20/11/2026: classe
     `elenco_codici`, uso `solo_registro`.)
   - **Falso positivo tra gli allegati richiamati**: "Allegato 5 Obblighi
     di pubblicità" (PMI 50 mila e PMI EU blending) è stato scaricato come
     allegato richiamato per beneficiari o ATECO, ma non lo è: la ricerca
     di "beneficiari" vicino a "Allegato N" è troppo larga. Da restringere
     prima del prossimo giro. (20/11/2026: i due file sono nel registro
     con uso `solo_registro`, decisione a mano; la ricerca resta da
     restringere.)
   - **Scadenze spesso assenti dai PDF**: l'avviso consolidato dei punti
     digitale (decreto 25205) non contiene la scadenza, che sta nella
     pagina e in `bandi.csv` (26/11/2026). Conferma la decisione del
     19/11/2026: per scadenza e stato vale l'archivio, mai il PDF. Il
     `riferimento_atto` dei punti digitale non cita il decreto 25205 da
     cui viene il testo consolidato: da aggiornare prima di usarlo
     nell'intestazione dei frammenti. (19c, 20/11/2026: l'atto dei
     frammenti viene dal registro, "Decreto n. 25205 del 16/11/2026,
     Allegato A", non da `bandi.riferimento_atto`; la correzione
     dell'archivio resta al passo 2b.)
   - **Bandi senza avviso riconosciuto**: fondo strade (il PDF del MIT ha
     3 pagine e 2 sezioni su 5) e incentivi-8659 (tra i link della pagina
     MIMIT ci sono solo guide e presentazioni). Restano senza avviso
     finché non si decide a mano. (Deciso a mano il 20/11/2026 nel
     registro: fondo strade "avviso" con uso "frammenti"; incentivi-8659
     "presentazione" con uso `solo_registro`.)
   - **Soglie provvisorie**: 3 sezioni per i link avviso o consolidato, 4
     per le altre classi e mai con testo "da rivedere", tarate il
     19/11/2026 su 12 bandi. Vanno riviste con più bandi.
   - **Verifica a mano dei PDF del 19/11/2026**: per i 10 bandi con
     l'avviso riconosciuto, i 15 file sono il testo del bando.
     fondo-strade-piccoli-comuni-2026: il PDF del MIT (3 pagine) è
     l'avviso vero, da segnare come avviso deciso a mano al 19c.
     incentivi-8659: il file è una presentazione del ministero, non
     l'avviso, da etichettare come tale. In 4 bandi su 12 la scadenza
     non è scritta come data nel PDF.

   **Passo 19d: misura del recupero sugli avvisi (20/11/2026).** Si fa
   sul Chroma locale; gli avvisi vanno su Postgres solo se il 19d passa.
   1. Misura zero, presa prima di ogni modifica (controllo del foglio dei
      fatti, `scripts/diagnostica/controlla_fatti.py`, 20/11/2026): 42
      pezzi su 97 stanno nella parte che il modello di embedding vede
      (limite di 128 token, [CLS] e [SEP] compresi; `car_visti` nei
      metadati di ogni frammento). 754 frammenti su 871 superano i 128
      token. Peggiori: risorse genetiche 1 su 7, Punti Digitale e fondo
      strade 2 su 7. Tutti i 97 pezzi stanno interi in un frammento.
   2. Tre ricerche di sola similarità del 20/11/2026, fatte prima del
      caricamento del decreto delle rievocazioni: zero su tre con il
      frammento giusto tra i primi cinque. Per la cultura ("mutuo
      massimo per un Comune sotto i 5000 abitanti per la cultura") esce
      l'avviso Sport, con le fasce, prima di quello Cultura, di cui esce
      solo la prima pagina; per l'azione B1 degli apistici l'allegato A1
      non compare (escono A3, A4, A5 e il testo coordinato delle risorse
      genetiche); per i Punti Digitale escono cinque frammenti del 25205,
      nessuno quello dei criteri (p. 14).
   3. Varianti da provare, sugli stessi fatti: limite a 512 token;
      frammenti più corti; intestazione (titolo, parte, atto) dentro il
      testo su cui si calcola il vettore, oggi è solo nei metadati;
      filtro per `id_bando`; ricerca per parole accanto a quella per
      significato. La regola di chiusura si fissa prima di guardare i
      numeri.
   4. Come si misura: sul frammento atteso del CSV di controllo
      (`dati-grezzi/prova/fatti_controllo_2026-11-20.csv`) e sul bando
      giusto, non sulla presenza della frase; con `RecuperoIbrido`, non
      con la sola similarità; fatti divisi a caso in due metà, taratura e
      controllo, con seme fisso e per bando, divisione decisa prima.
   5. Documenti gemelli: Cultura e Sport Missione Comune, i due bandi PMI,
      i quattro allegati degli apistici. Nel foglio dei fatti 4 frasi di
      controllo sono identiche tra bandi (righe 21 e 24 tra Cultura e
      Sport, 56 e 64 tra i due PMI) e 4 tra allegati (righe 68, 70, 72 e
      74 degli apistici); la riga 23 è quasi gemella (un pezzo identico
      nell'avviso Sport, l'altro diverso per una cifra). Per le colonne
      sui gemelli vale il valore calcolato dal controllo
      (`solo_calcolato`), non quello scritto nel foglio, che in 45 righe
      era vuoto.
   6. Date nei frammenti che contraddicono l'archivio: nell'avviso (p. 9)
      e nella proroga (p. 1) di Cultura e di Sport Missione Comune c'è il
      termine di prima della proroga, 30/09/2026, accanto al 05/12/2026
      che è in archivio; nel decreto delle rievocazioni c'è "30 maggio
      2025" per l'annualità 2025 (Art. 2), mentre la scadenza in archivio
      è il 31/01/2027. Caso fisso del 19d: la risposta deve dare la data
      dell'archivio.
   7. Se cambia il limite dei token o la dimensione dei frammenti, i
      vettori si ricalcolano tutti, Chroma e Postgres, prima della nuova
      baseline.

   **Prima della nuova baseline: i 5 documenti di sempre (20/11/2026).**
   I 5 documenti di produzione vanno ricaricati con la pulizia prudente:
   28 frammenti su 316 hanno numeri fusi dalla ricucitura di sempre
   (Censis 21 su 75, requisito associativo 4 su 21, Decreto 9550 2 su 76,
   SNAI C3 1 su 27, Decreto 13287 0 su 117; misura su una copia di Chroma,
   senza correggere niente). Tra le fusioni del 9550 ce n'è una giusta,
   "200.00 0,00" che diventa "200.000,00", che la regola prudente non
   farebbe. `ingest_tutti` su Postgres aggiunge senza togliere i
   frammenti già presenti: rilanciato così, li raddoppierebbe.

   **Limiti noti del caricamento (19c, 20/11/2026).**
   - pypdf mette spazi dentro alcune parole: 14 frasi su 81 del foglio
     dei fatti si trovano solo togliendo gli spazi. Da verificare
     l'effetto sul verificatore dell'app, che confronta i dati con il
     testo del frammento.
   - Trattino negli indirizzi web, nei 16 file del 19/11: 22 indirizzi
     spezzati su un trattino a fine riga, 19 giusti e 3 sbagliati nel
     22706, dove il trattino era sillabazione ("docs.ita-lia",
     "sft.svi-luppo", "fir-ma"); 1 indirizzo non corretto nel 13512 (p.
     16, già spezzato da spazi nel PDF: resta "carta-aiutiitalia").
     Strada possibile: leggere l'indirizzo dalle annotazioni di
     collegamento del PDF.
   - `tabella_probabile` non è affidabile: è un indizio, non una regola
     (segna la Tab. 1 del bando PMI 50 mila, non la tabella di una riga
     degli apistici a p. 2).
   - "DECRETA:" con i due punti non fa scattare la regola delle premesse.
   - `livello` vuoto: l'etichetta del frammento mostra "?".
   - I link ai moduli restano fuori dal 19c: il registro ha una riga per
     file scaricato.
   - Il controllo dei numeri è una regola di ogni caricamento futuro: il
     rapporto di `--prova` si guarda prima di scrivere.
   - I metadati dei PDF (autore e simili) non entrano mai in registro,
     frammenti o file delle richieste (verificato il 20/11/2026 sul
     decreto delle rievocazioni).
- (era la voce 7 dei Prossimi passi, → principio "per chi", → passo 18) **Privati nell'app**: selettore pubblico/privato e tipo di privato a
   macrogruppi. Insieme, l'abbinamento strutturato tra interventi e tipi
   di beneficiario: oggi la riserva sta solo nel testo della descrizione
   ("Adeguamento e ampliamento della viabilità rurale, solo enti
   pubblici", AS01 del GAL), e un terzo settore che chiede quali
   interventi può fare non riceve un filtro, solo il testo.
- (era la voce 8 dei Prossimi passi, → passo 21) **Sezione riservata**: accesso, iscrizioni con mail e ricerche salvate su
   Supabase, tasto "aggiorna adesso" che lancia il processo su GitHub,
   segnalazione manuale di un bando. Parte pubblica limitata a 3 domande per
   sessione, con un tetto giornaliero complessivo e un invito a scrivere per
   l'accesso.
- (nuova, 19/11/2026, → passo 20) **Tasto di segnalazione sulla risposta**, prima di
   pubblicare il link della demo, insieme al limite per sessione e al
   tetto giornaliero della voce precedente:
   - una scelta tra: un dato è sbagliato; manca un bando che conosco
     (con un campo: quale); un bando proposto non c'entra; un bando
     proposto è scaduto o non più disponibile; un link o una fonte non
     si apre; non ha trovato niente ma mi aspettavo qualcosa; la
     risposta è poco chiara; risposta utile;
   - campo libero facoltativo;
   - si salvano con la segnalazione: domanda, ente del menu, risposta,
     bandi citati, esito del verificatore, commit e impronta delle
     istruzioni, data;
   - il testo della domanda si salva solo quando l'utente preme il
     tasto, con una riga che dice cosa viene salvato e di non scrivere
     dati personali; nessun account;
   - ogni segnalazione è un caso per l'insieme di controllo del passo 5.
- (era la voce 9 dei Prossimi passi) **Newsletter come segnali**: casella dedicata iscritta alle newsletter di
   Regione, fondazioni e GAL; i link estratti passano dalla verifica sulla
   pagina ufficiale.
- (era la voce 10 dei Prossimi passi, → D) **Percorso guidato per gli iscritti**: passi definiti dal bando (requisiti,
   documenti, scadenze intermedie, contatti), controllo dei documenti con ogni
   requisito citato. Percorso a passi fissi, non un agente libero.
   Figure da coinvolgere (per esempio tecnico abilitato, commercialista,
   progettista) ricavate dal testo del bando con la frase di origine, mai
   dedotte dal modello senza fonte.
- (era la voce 11 dei Prossimi passi) **Docker** per Postgres con pgvector in locale.

## In coda

- (→ passo 19) Dopo la demo. Avviso del decreto 9550 del 28/04/2026 (rafforzamento
  amministrativo dei Capofila delle Aree interne) nella tabella dei
  bandi, con la sua fonte: oggi sta solo nell'archivio documentale, unica
  opportunità di finanziamento che manca dalla tabella (C18 del lotto 3,
  correzione F2 di `docs/piano-correzioni-lotto1.md`). Servono la pagina
  ufficiale e la data del BURT, perché il termine è "il trentesimo giorno
  successivo alla pubblicazione" e il documento non dà la data; e un tipo
  di beneficiario per i Capofila dell'area interna, altrimenti il bando
  compare a tutti i comuni o a nessuno. Da fare insieme ai PDF dei bandi
  (voce 4 dei prossimi passi).
- Dopo la demo. Elenco dei documenti dato al router: titolo, tipo e atto
  di ciascun documento dai metadati del vector store (uguali in Chroma e
  in Postgres), accanto al contenuto dell'archivio numerico, con la regola
  "documenti: true anche quando una domanda generica sui bandi riguarda
  l'oggetto di un avviso dell'elenco". Costo stimato: circa 150 token per
  5 documenti, per 3 chiamate del router, meno di 0,001 $ a domanda.
  Scartata l'alternativa di consultare sempre i documenti per "ci sono
  bandi per …": circa +5.900 token in ingresso alla risposta, +0,012 $ a
  domanda, con frammenti per lo più fuori tema (correzione F2).
- Dopo la demo. Tetto giornaliero complessivo di domande, con un contatore
  su Supabase, prima di pubblicare il link dell'app: il limite per
  sessione da solo non basta.
- Dopo la demo. Nota sotto la casella delle domande: le domande vanno a un
  servizio di AI, niente dati personali.
- Prima del post su LinkedIn. Domande fuori ambito: il router le
  riconosce e l'app risponde con una frase fissa, senza chiamare il
  modello di risposta né il recupero.
- Dopo la demo. Post su LinkedIn dopo la risposta del consulente pilota,
  con video o schermate, link al repository e al README.
- Dopo la demo. Registro delle decisioni (`docs/decisioni.md`): una scheda
  per decisione (problema, alternative, misura, scelta, perché, cosa resta
  aperto), scritto per poterlo spiegare a voce.
- Dopo la demo. Controlli automatici su GitHub: `ruff` e `pytest` a ogni
  push.
- Dopo la demo. Fonti di scoperta da valutare, nell'ordine: BURT parte III
  (per misurare la copertura della fonte regionale e recuperare i bandi
  aperti e chiusi tra due scansioni), Uncem, associazioni di categoria
  della montagna, Toscana Notizie, Cesvot, Giovanisì, ANCI nazionale.
  Stessa regola di ANCI Toscana: segnalano, i dati si prendono dalla
  pagina ufficiale. Toscana Notizie e Cesvot provati a mano il
  19/11/2026: esito in 'Riscontro del consulente pilota e fonti'.

  Buco ancora aperto: nella misura di copertura del 13/11/2026 mancano
  tutti i 10 bandi di enti nazionali segnalati da ANCI Toscana
  (`docs/ricognizione-fonti.md`, 8.4). Il fondo strade MIT è nel recupero
  prima della demo; degli altri nove, quelli rivolti anche ai comuni sono
  arredi didattici (Istruzione), jazz 2027 (Cultura, autonomie
  territoriali) e Vita & Opportunità (comuni come partner); gli altri sei
  sono per imprese o terzo settore.
- Dopo la demo. Beneficiari della cooperazione internazionale ("PROGETTI
  SEMPLICI 2026 di Cooperazione Internazionale") completati a mano
  dall'avviso, con la frase come prova e origine `manuale` (opzione 4
  della correzione C3, `docs/piano-correzioni-lotto1.md`). Prima, la
  protezione delle righe `manuale` dalla riestrazione (voce 8 della
  revisione).
- Dopo la demo, salvo problemi di avvio prima. App online più leggera:
  torch solo CPU e chromadb non necessari (l'app online usa Postgres);
  oggi si installano circa 2,5 GB di librerie CUDA per niente. Da
  provare su Streamlit Cloud.
- Dopo la demo. Revisione dei test: segnalare quelli che ricopiano il
  codice invece di proteggere un comportamento.
- (→ passo 2b) Dopo la demo. Simulazione senza modello: quanti bandi per "PMI" o
  "imprese" senza settore sono classificati solo come `altra_impresa`, e
  quindi non compaiono nelle ricerche per settore (turistiche, artigiane
  e commerciali, agricole). Caso del 13/11/2026: il minibond.
- Dopo la demo. Regola che riconosce "professionisti" da solo come
  `professionista_autonomo` (oggi solo "liberi professionisti"), da
  provare sui casi in cui la parola indica consulenze e non beneficiari;
  poi il bando IGP (`produzioni-artigianali-e-industriali-…-fa7c57`:
  «le Pmi, inclusi i professionisti, in forma aggregata»).
- Dopo la demo. Regola per i bandi pubblicati su due domini (Regione e
  Sviluppo Toscana, poi BURT e le altre fonti), da scrivere prima di
  accendere l'elenco di Sviluppo Toscana (oggi `attivo` = 0). Caso del
  13/11/2026: Digitale P.A. su sviluppo.toscana.it è lo stesso bando di
  "Contributi agli enti locali per lo sviluppo di progettualità sui dati"
  già in archivio dalla Regione (decreto 22706 del 9/10/2026); con l'elenco
  acceso sarebbero doppioni anche IGP, le due 1.3.2 PMI, PMI turismo e
  Minibond.
  Primo pezzo fatto il 13/11/2026: `data/processed/doppioni.csv`, un file
  per i doppioni tra tutte le fonti (indirizzo, fonte, id tenuto, motivo,
  data, differenze accettate), letto oggi dall'importazione di Incentivi
  Italia; da far leggere anche a Sviluppo Toscana e BURT.
- Dopo la demo. Soglie di popolazione dei bandi (es. comuni fino a 5.000
  abitanti, fondo strade MIT) confrontate con i dati ISTAT del comune:
  oggi la soglia sta solo nelle condizioni dei beneficiari, e il bando
  compare a tutti i comuni.
  Dettaglio del passo 8 della roadmap, spostato il 18/11/2026: Nella
  prova, alcune domande con San Marcello Piteglio come ente (7.410
  abitanti; Abetone Cutigliano 1.834).
  Esempio per il passo 8 (20/11/2026): nella risposta al caso fisso F01
  del 19/11/2026, dopo l'inserimento del fondo rievocazioni, è il
  modello a confrontare la popolazione con la soglia di Cultura Missione
  Comune (1.834 abitanti, piccoli Comuni fino a 5.000) e a concludere "e
  rientra quindi in questa fascia" (`dati-grezzi/caso_F01_risposte_2026-11-19.md`).
  È il confronto che il passo 8 porta nel codice.
- Dopo la demo. Campo strutturato per gli importi per fascia di ente (es.
  mutuo massimo di 2, 4 o 6 milioni secondo tipo e dimensione dell'ente,
  Sport e Cultura Missione Comune): oggi la frase della pagina sta nel
  testo dei beneficiari.
- Dopo la demo. Aggiunta di fonti dall'interfaccia, in tre passi:
  l'utente segnala una fonte; il sistema prova da solo robots.txt,
  lettura dell'elenco e due o tre bandi d'esempio, con il costo; una
  persona approva prima che la fonte entri in `fonti.csv`.
- Dopo la demo. Lista di controllo scritta per ogni fonte nuova:
  robots.txt, elenco leggibile, tre bandi verificati a mano sulla
  pagina, costo per bando, regola di chiusura.
- Dopo la demo. Incentivi Italia, link condivisi: oggi una riga con un
  `Link_istituzionale` usato da più righe del file è da verificare a mano
  (43 righe sul file del 12/11/2026). Molte sono misure sorelle sulla
  stessa pagina di bando (sezioni regionali del bando ISI, bandi R&S 1 e
  2, tax credit della stessa sessione). Regola da valutare: il link
  condiviso è ammesso se le righe hanno lo stesso concedente e le stesse
  date (`docs/piano-fonti.md`, tappa 5).
- Elenco dell'Istituto per il Credito Sportivo: se un giorno si attiva
  (oggi `attivo` = 0), la scansione deve rispettare il `Crawl-delay: 2`
  del robots.txt: oggi `estrai_nuovi` aspetta 0,5 s tra i download e 1 s
  tra le estrazioni.
- Verificare sulla pagina della Regione il fondo di garanzia energie
  rinnovabili del 2014 (stato e "contributo fino all'80%"). Dopo la
  riclassificazione e' senza scadenza e non a sportello: la pagina non ne
  parla.
- Fuso orario: `date.today()` in 6 punti (DTZ011), mentre altri 2 punti
  usano già `Europe/Rome` (`salva.py`, `grezzi.py`): a ridosso della
  mezzanotte uno stesso salvataggio può avere due date diverse.
- Verificatore, identificativi e codici spezzati in più numeri:
  "2023-0118" (linea di credito EU blending della BEI) è letto come 2023
  e 0118; "56.10" (codice ATECO a due parti senza lettera, L02 del lotto
  1) come 56 e 10. Come i codici ATECO prima della correzione del 13
  novembre 2026: un pezzo presente per caso in una fonte risulta
  verificato (correzione D2, `docs/piano-correzioni-lotto1.md`).
- Segnalazioni ruff ISC004 e BLE001 negli script.
- Due xfail di `pulisci`: numeri separati da virgola, intestazione con spazi.
- Regola "imprese senza settore" applicata anche nel codice, non solo nel
  prompt.
- Avvisi sui bandi salvati visibili nell'app (perché una dotazione è vuota).
- Righe di `scansioni` con slug tagliati: da ripulire.
- Link simbolici `.claude/skills` e `.agents/skills` verso `.venv` nel repo.
- Fine riga CRLF/LF.
- Appartenenza dei comuni all'Unione nel profilo dell'ente.
- Dalla scansione completa dell'11 novembre 2026:
  - `COSTO_NON_BANDO` in `estrai_nuovi` da rimisurare su pagine che non
    sono bandi: oggi vale 0,031 $, la media della scansione con bandi e non
    bandi insieme, quindi per eccesso. `COSTO_BANDO` e' 0,061 $, misurato
    sulla riestrazione di 10 bandi del 12 novembre 2026;
  - i bandi in archivio che il modello giudica non bandi restano senza
    `classificato_il` e `riclassifica_bandi` li riesamina a ogni lancio:
    decidere se segnarli o toglierli;
  - le pagine a "scadenza non determinata" (es. ricerca finalizzata 2021 e
    2024) tornano candidate a ogni scansione e si pagano ogni volta;
  - 16 valori vecchi mantenuti nella riclassificazione, da controllare a
    mano (elenco nel rapporto della scansione);
  - i 9 bandi salvati nella prima corsa, prima della correzione degli
    importi con il punto decimale, possono avere importi vuoti.
- `data/db/comune.sqlite` sotto git: compare modificato a ogni ricreazione
  anche con i dati identici. Prima di toglierlo dal repository, l'app deve
  ricrearlo dai CSV all'avvio, perché la demo su Streamlit Cloud lo legge
  dal repository.
- Sicurezza e salute nei luoghi di lavoro 2026: la pagina dice che il bando
  è approvato con decreto 13543 del 15 giugno 2026 e, poco sotto, che testo
  e allegati sono approvati con decreto 13542 dello stesso giorno. In
  archivio c'è 13543: da controllare sul decreto.
- Le correzioni a mano sui campi di `bandi` (atti, note, sportello: script
  `correggi_atti` e `applica_regole_verifica` del 12 novembre 2026) non sono
  protette da una riestrazione futura, a differenza delle date di
  `scadenze_bando` con origine `manuale`. Alla prossima scansione,
  controllare che non siano tornate ai valori di prima.
- Test di equivalenza: un bando di prova per i privati
  (`professionista_autonomo`, `qualsiasi_soggetto` sostituito dalle regole),
  prima del selettore pubblico/privato.
- Perché Chroma ordina meglio di Postgres sulle stesse domande, dato che
  la demo usa Postgres. In `scripts/diagnostica/prova_recupero.py` del
  12 novembre 2026 il costo giornaliero (322,00 €) e i costi indiretti
  sono 1ª su Chroma e 4ª su Postgres. La parte densa dà le stesse
  posizioni sui due motori, quindi la differenza sta nella parte
  lessicale: BM25 in memoria contro `ts_rank_cd` con la domanda in OR e
  le radici delle parole in italiano. Una domanda va in senso opposto (i
  1.904 comuni: 2ª su Postgres, 4ª su Chroma).
- P2, casi rimasti aperti (`docs/prova-verificatore.md`): i contributi dei
  mercati rionali, con parole diverse dal testo, e la domanda su due
  avvisi; il termine di presentazione al limite (8ª su Postgres, 10ª su
  Chroma); la domanda di controllo sulla rendicontazione dei mercati
  rionali, che con P2 scende dalla 5ª alla 7ª su Postgres. Rilanciare
  `scripts/diagnostica/prova_recupero.py` a ogni modifica del recupero o
  dell'archivio.
- Indice HNSW su Postgres e ricerca ristretta a un documento. Su `chunk`
  c'è `chunk_embedding_idx` (HNSW, `hnsw.ef_search` = 40). Con 316
  frammenti il pianificatore sceglie la scansione sequenziale, quindi la
  ricerca densa è esatta (misurato il 12 novembre 2026 con `EXPLAIN
  ANALYZE`). Quando l'archivio crescerà con i PDF dei bandi, potrà passare
  all'indice: il filtro sul documento si applica dopo i 40 candidati
  dell'indice, e la ricerca ristretta di P2 resta con pochi frammenti o
  nessuno. Forzando l'indice oggi, 6 ricerche ristrette su 25 restituiscono
  meno righe (3 invece di 20 per la quota di ciascuna Area interna).
  Rimedi da valutare allora: `hnsw.iterative_scan` di pgvector 0.8,
  `ef_search` più alto per le ricerche ristrette, o ricerca esatta quando
  c'è il filtro.
- Dalla ricognizione delle fonti del 12 novembre 2026
  (`docs/ricognizione-fonti.md`):
  - nuova fonte candidata: le sezioni "Avvisi" dei siti istituzionali dei
    tre comuni, che pubblicano bandi per le imprese (es. contributi dal
    Fondo per i comuni delle aree interne). Prima di tutto verificare il
    robots.txt di ciascun dominio;
  - nella tabella `enti`, valutare la partita IVA come secondo
    identificativo degli enti (nei dati PNRR compaiono con l'una o con
    l'altra).
- (nuova, 19/11/2026) **Notifica degli errori a chi mantiene l'app**, in
  due parti:
  - archivio: alla fine di ogni aggiornamento delle fonti un rapporto di
    manutenzione con righe scartate, link che non si aprono, scansioni
    fallite, bandi senza scadenza (→ passo 11);
  - app online: registro su Supabase degli errori della catena, del
    router e del verificatore, con un riepilogo periodico.
  L'indirizzo a cui notificare sta nei segreti, mai nel repository.
- (nuova, 19/11/2026) **Pagine di prova con il totale vero**
  ("Risultati: N") dell'elenco generale della Regione, prese dalla prima
  copia in `dati-grezzi/elenchi/`: estratto in `tests/pagine/`, riga in
  `LEGGIMI.md`, e correzione di `totale_dichiarato` se la forma reale è
  diversa da quella della nota in `piano-fonti.md`.
- (nuova, 19/11/2026) `estrai_bando` legge le pagine con l'intestazione
  di un browser e senza robots.txt, e non stampa token né costo: va
  allineato a `lettore_siti` e deve dire quanto ha speso.
- (nuova, 19/11/2026) Data di pubblicazione presa dalla data del decreto
  citato nel testo (fondo rievocazioni, 19/11/2026): un caso solo. Se si
  ripete, diventa una regola nel codice o una riga nel prompt
  dell'estrattore.

## Insieme di prova: dopo

→ passo 5 per l'insieme di controllo.

Metodo in `docs/piano-insieme-prova.md`.

- (nuova, 19/11/2026) **Casi fissi**: `docs/piano-insieme-prova.md`,
  sezione "Casi fissi" (F01, la domanda del consulente pilota del
  19/11/2026).
- (nuova, 19/11/2026) **Modalità `--casi-fissi` di `prova_insieme`**, con
  il file `dati-grezzi/prova/casi_fissi.txt`: compito di codice a parte.
- **`--riepilogo` conta i giudizi a mano**: legge
  `dati-grezzi/prova/lotto_<n>/giudizi.csv` e conta i giudizi per
  categoria, sulle righe della registrazione a freddo. Il campione dei
  verificati va estratto una volta sola, alla registrazione a freddo:
  oggi una riverifica lo riestrae da un insieme cambiato e aggiunge righe
  nuove a `giudizi.csv`.
- **Insieme generato**: circa 150 domande che coprono la griglia tipo di
  beneficiario × tipo di richiesta (bandi, scadenza, importo, requisiti,
  territorio) × tema × forma (precisa, vaga, sgrammaticata, doppia, fuori
  ambito), con profili diversi di chi chiede. Solo misure automatiche
  (router, parametri non validi, "non trovo", esiti del verificatore,
  costi) più un campione di 20 risposte giudicato a mano. Prima della demo
  solo se il resto è chiuso.
  Asse in più, il tipo di fonte: domande sui documenti, con la risposta
  attesa completa, parziale o "non trovo"; domande di controllo su
  argomenti vicini assenti dai documenti; domande miste, bando più
  contesto normativo. Nei lotti 1 e 2 A05 è l'unica domanda che il router
  ha mandato solo ai documenti (A01 e L05 del lotto 1 ci sono finite solo
  per il router fallito): la parte documentale dell'app e la regola E
  (`docs/piano-correzioni-lotto1.md`) sono misurate su una domanda sola.
- **Modello giudice**: solo dopo averlo tarato su un numero sufficiente di
  giudizi a mano. La stessa taratura vale per il validatore
  dell'architettura della risposta in due passi (prima voce dei
  "Prossimi passi").

## Revisore tecnico (18/11/2026)

Spostato da `docs/roadmap.md` il 18/11/2026.

### Indicazioni ricevute

- separare classificazione, scelta della forma e scrittura;
- confronti numerici (popolazione e soglia del bando) nel codice, con il
  modello che spiega il risultato. Oggi `ISTRUZIONI` vieta le deduzioni
  ma chiede di concludere sulla soglia;
- funzioni in sequenza finché il flusso è lineare, LangGraph solo con
  rami o cicli (per esempio rigenerare se il verificatore fallisce);
- baseline prima di cambiare;
- router: voto più ripieghi nel codice, e provare l'unione delle scelte
  delle chiamate al posto della maggioranza, misurando bandi recuperati e
  bandi fuori tema aggiunti;
- per ogni errore distinguere: bando non in archivio, non recuperato,
  recuperato ma escluso dalla risposta;
- verifiche a mano sulle conclusioni (attribuzione, ammissibilità), che
  il verificatore non controlla;
- confronti domanda per domanda, esecuzioni ripetute per misurare la
  variabilità, insieme di controllo nuovo mai usato per tarare, con casi
  senza risposta e domande scritte da chi lavora nei Comuni.

### Priorità dopo il riscontro del consulente pilota (18/11)

Superate dall'ordine dei passi di docs/roadmap.md. Conservate perché
docs/piano-fonti-burt-ministeri.md e questa sezione le citano per
numero. Fonte: commit fbe391c.

Riscontro del consulente pilota del 18/11/2026, in sintesi:
- prova con tre domande;
- su una domanda senza risultati attesi l'app non ha inventato;
- su una ha mancato due bandi, uno nazionale e uno regionale;
- su una ha trovato opportunità corrette ma generiche;
- suggerimenti: includere il BURT e provare con qualche ministero.

Ordine dei prossimi passi:

1. (→ fatta il 19/11/2026, vedi 'Riscontro del consulente pilota e fonti') (→ "In attesa" della roadmap) **Diagnosi dei due bandi mancati**, appena arrivano domanda e titoli.
   Per ciascun bando, verificare se è in archivio:
   - se c'è, la causa è il router;
   - se non c'è, è la copertura.

   Le domande diventano casi fissi dell'insieme di prova ("Insieme di
   prova: dopo"). Nessuna chiamata al modello per la diagnosi.
2. (→ passi 3 e 7, router; passi 11-16, fonti) **Primo cantiere, scelto dalla diagnosi**:
   - copertura delle fonti, se i bandi mancano dall'archivio (punto 3);
   - router, se ci sono: voce 16 di questa sezione (maggioranza tra le 3
     chiamate) e ripieghi nel codice ("Prossimi passi", architettura
     della risposta in due passi).

   Con un caso per tipo, prima le fonti.
3. (→ fatto il 18/11) **Studio del BURT e di due o tre ministeri, senza codice**:
   - come pubblicano, robots.txt, quota in PDF, frequenza, filtro sui
     comuni montani;
   - per i ministeri, scelta di quali coprire con il consulente pilota e
     confronto con quanto copre già Incentivi Italia.

   Esito: un piano scritto in `docs/piano-fonti-burt-ministeri.md`.
   Probabile prerequisito: la lettura dei PDF ("Prossimi passi", voce 6,
   "Lettura dei PDF"). Riprende le voci di "In coda" sulle fonti di
   scoperta da valutare (BURT parte III, e il buco dei bandi di enti
   nazionali nella misura del 13/11/2026) e sulla lista di controllo per
   ogni fonte nuova.
4. (→ passo 16) **Misura di copertura ripetuta su un elenco esterno**, prima e dopo le
   nuove fonti: quella del 13/11/2026 non è stata ripetuta. È la "Prova di
   copertura" di "Prima della demo con il consulente pilota".
5. (→ passo 9) **Ammissibilità più stretta** (risposte "generalmente adatte"): nodo di
   classificazione dell'architettura a passi ("Prossimi passi",
   architettura della risposta in due passi, passo 1).
6. (→ passo 11) **Aggiornamento periodico delle fonti** ("Prossimi passi", voce 3):
   diventa necessario con l'aumento delle fonti.
7. (→ D della roadmap) **Fasi successive** (documenti da preparare, figure da coinvolgere,
   controllo dei documenti): dopo il confronto con il consulente pilota
   sull'obiettivo dello strumento. Vedi "Prossimi passi", voce 10
   (percorso guidato), che copre documenti, figure da coinvolgere e
   controllo dei documenti.

### Ordine dei passi proposto, superato

Superato dall'ordine dei passi di docs/roadmap.md. Conservato perché
coda.md, docs/revisione-prompt-2026-11-18.md e
scripts/diagnostica/schede_etichette.py lo citano per numero.
Testo copiato da `git show fbe391c:docs/roadmap.md`, righe 376-422;
accanto a ogni punto il passo della roadmap che lo ha assorbito.

1. (→ Stato e passo 2 della roadmap) **Baseline**: la regressione finale del 16/11/2026 (commit `715b411`),
   già registrata.
2. (→ Stato e "In attesa" della roadmap) **Diagnosi a tre categorie** (archivio, recupero, esclusione), senza
   modello. Per ogni attesa delle 55 domande e per i bandi mancati
   segnalati dal consulente pilota, cercare il titolo:
   - nel database (non c'è: archivio);
   - nel blocco dati salvato nel JSON della prova (non c'è: recupero);
   - nei bandi citati (non c'è: esclusione).

   Comprende il punto 1 delle priorità qui sopra.
3. (→ passo 3) **Simulazione del router senza modello**, sulle risposte grezze già
   salvate (`grezzi_router`). Quattro strategie:
   - prima chiamata (oggi);
   - maggioranza (voce 16 di "Difetti dalla prova completa del 14
     novembre");
   - unione delle scelte delle chiamate;
   - unione più ripieghi (per esempio, con un Comune, aggiungere
     `bandi_aperti_per_ente`).

   Interrogazioni eseguite nel codice. Misure per domanda: attese
   presenti nei dati, numero di bandi in più rispetto alla prima
   chiamata.
4. (→ passo 7) **Scelta di strategia e ripieghi** in base al punto 3, poi
   implementazione e misura con il modello contro la baseline, domanda
   per domanda. Sostituisce la maggioranza data per scontata nella voce
   16 e nella prima voce dei "Prossimi passi".
5. (→ passo 8) **Soglie di popolazione confrontate nel codice**; il modello spiega il
   risultato.
6. (→ passo 9) **Risposta in funzioni in sequenza** (classifica, forma, scrivi):
   l'architettura della risposta in due passi, prima voce dei "Prossimi
   passi". LangGraph solo con cicli o rami. Mappa delle regole dei due
   prompt per passo, con contraddizioni e ridondanze:
   `docs/revisione-prompt-2026-11-18.md` (revisione esterna, non
   applicata).
7. (→ passi 2 e 5) **Esecuzioni ripetute sulle domande instabili; insieme di controllo**
   con domande reali dello sportello, mai usato per tarare ("Insieme di
   prova: dopo").
8. (→ passo 10) **Forma dell'aiuto come campo dei bandi** (fondo perduto, prestito,
   garanzia, abbattimento degli interessi), con la frase di origine. Caso
   P11: la risposta raggruppa dei bandi come «Contributi a fondo perduto»
   senza appoggio nelle righe, e l'attesa a mano «distinguere fondo
   perduto da prestiti e garanzie» oggi si può soddisfare solo dai titoli.
9. (→ passo 1) **Attese con polarità** ("proposto", "non proposto", forma attesa):
   oggi una citazione fatta per escludere un bando conta come trovata.
   Caso C03 della regressione del 16/11/2026: la risposta cita Punti
   Digitale Facile per dire che non lo presenta come pertinente, e
   `attese_esito` lo segna trovato.

## Pulizia dei dati (passi 2a e 2b)

Dettaglio del passo 2, spostato da `docs/roadmap.md` il 18/11/2026.

- **2a**, dopo il primo giro di etichette. Bandi con 8 o più tipi:
  quattro in archivio, due aperti al 16/11 (risorse genetiche agrarie,
  12 tipi; fondo di garanzia, 9) e due no (risorse genetiche
  forestali, 11; premi per gli imboschimenti, 9). Deciso il 18/11/2026: i
  quattro bandi con 8 o più tipi non si correggono. Sono bandi 'per
  requisito', la classificazione rispecchia la pagina. Vedi
  docs/roadmap.md, passo 2a. Poi gli
  aperti sospetti: Tax credit cinema 2024, sportelli senza chiusura
  aperti da più di due anni (`coda.md`, "Nuova Sabatini, Smart&Start,
  ISI INAIL" tra le voci di "Prima della demo").
- **2b**: il resto, con la simulazione "PMI senza settore" di
  `coda.md`. `altra_impresa` ha due significati: impresa senza settore
  nelle estrazioni vecchie; settore senza un tipo suo in Incentivi
  Italia. I bandi per imprese senza settore prendono i quattro tipi
  d'impresa; quelli di un settore senza tipo restano `altra_impresa`.
  Al 16/11, tra gli aperti: `altra_impresa` 25, turistica 23, artigiana
  e commerciale 19, agricola 14.

Dalla pulizia non ci si aspetta un calo dei bandi ricorrenti oltre
risorse genetiche. La nuova baseline (dopo i passi 19, 2b, 4 e 3,
decisione del 19/11/2026): tre registrazioni delle 55 domande, circa
10,5 $; assorbe il passo 6.

Rimaste dopo il passo 2a (18/11/2026):

- **Fondo di garanzia energie rinnovabili**: aprire a mano il decreto
  dirigenziale 2649 del 27/02/2018 nella banca dati degli atti della
  Regione e, se confermato, aggiornare `verificato_il`. La scadenza
  2021-12-31 oggi non è protetta da una riestrazione esplicita
  (`estrai_bando --auto`, `riclassifica_bandi --id`): la protezione, una
  riga "manuale" in `scadenze_bando`, aspetta la frase letta a mano.
- **incentivi-5013 e incentivi-3373** hanno il link alla banca dati del
  BURT: pagina vera da cercare a mano.
- **Link alla banca dati del BURT** (decisione del 19/11/2026): una riga
  del catalogo Incentivi Italia il cui indirizzo porta a
  regione.toscana.it/bancadati o a www301.regione.toscana.it non entra
  tra i bandi; va nel registro delle scansioni come "da verificare:
  pagina del bando non trovata". Vale anche per incentivi-5013 e
  incentivi-3373, che escono dalle risposte finché non hanno una
  pagina vera. È una modifica al codice dell'importazione, da fare
  insieme al passo 19. Il controllo dei doppioni resta prima di questo:
  le due righe di protezione di incentivi-3662 e incentivi-4804 in
  doppioni.csv devono continuare a valere.
- **incentivi-3373** (abbattimento interessi sotto 50.000 euro, 2024) è
  probabilmente l'edizione precedente del Bando 2026 Pmi fino a 50 mila
  euro: da verificare come si è fatto per incentivi-3662.
- **Tax credit cinema anno 2024** (incentivi-3838) risulta aperto: data
  di chiusura della sessione da verificare.
- **`doppioni.csv` protegge anche due correzioni a mano dell'indirizzo**
  (incentivi-3662 e incentivi-4804, dal BURT alla pagina della Regione):
  è una soluzione provvisoria, la protezione vera è la voce sulle
  correzioni a mano protette dalla riestrazione.
- **`_frase` in `src/estrazione/incentivi.py`** può tenere un a-capo
  della pagina dentro la frase: oggi lo corregge l'esportazione
  (`esporta_csv`), la correzione alla fonte è da fare.
- (→ passo 2b, 19/11/2026) **`riferimento_atto` dei punti digitale**
  (contributi-a-enti-locali-e-ets-per-punti-digitale-fac-8db4be): oggi è
  "Decreto dirigenziale 24316 del 30 ottobre 2026, modificato con decreto
  24443 del 6 novembre 2026"; va aggiornato con il decreto 25205 del
  16/11/2026, da cui viene il testo consolidato dell'avviso, dopo averlo
  verificato sulla pagina del bando.
- (→ passo 2b, 19/11/2026) **Aziende apistiche, scadenze diverse per
  azione** (sostegno-agli-investimenti-strutturali-aziende-apisti-401650):
  4 dicembre 2026 per le azioni B1, B3 e B5; 21 maggio 2027 per la B4,
  dall'allegato A4. In archivio c'è solo il 4 dicembre. Da verificare
  sulla pagina del bando e da decidere come rappresentare un bando con
  più scadenze.

Dal passo 19c (20/11/2026), confrontando gli avvisi caricati con
l'archivio e con le pagine salvate il 19/11:

- (→ passo 2b) **Fondo strade** (fondo-strade-piccoli-comuni-2026): in
  archivio c'è la frase della pagina (riservato a chi non ha mai avuto il
  finanziamento, salvo i Comuni con un finanziamento parziale "inferiore
  al 50%" che non abbiano avviato le procedure di affidamento dei
  lavori). Mancano le annualità dell'esclusione, 2023, 2024 e 2025 con
  gli scorrimenti, che stanno nell'avviso. Pagina e avviso divergono:
  "inferiore al 50%" e la condizione sull'affidamento sulla pagina,
  "minore o pari al 50%" nell'avviso, che sull'affidamento non dice
  nulla.
- (→ passo 2b) **Punti Digitale**
  (contributi-a-enti-locali-e-ets-per-punti-digitale-fac-8db4be): l'avviso
  dà un tasso forfettario del 20% dei costi diretti per il personale; la
  pagina cita una scheda del preventivo con un tasso "fino al 40%", che
  è il massimo del regolamento UE 2021/1060, art. 56, citato anche
  nell'avviso.
- (→ passo 2b) **Cultura Missione Comune**: 5 milioni di euro di
  contributi in conto interessi, giusto in archivio. Un comunicato parla
  di un importo di mutui più alto: è un caso che può confondere la
  risposta. L'importo del comunicato non è tra i file salvati e qui non
  si riporta.
- (→ passo 2b) **Fondo rievocazioni** (fondo-rievocazione-storica-2027):
  nel decreto il fine statutario (tutela e trasmissione della memoria
  storica) riguarda gli enti di rievocazione storica, cioè associazioni
  di promozione sociale, onlus e fondazioni, non gli enti locali e i
  soggetti pubblici; punteggio minimo 61 su 100.
- Restano le voci già note qui sopra: scadenza dell'azione B4 degli
  apistici, `riferimento_atto` dei Punti Digitale (decreto 25205),
  `altra_impresa`.

## Testo di ricerca (passo 17)

Dettaglio del passo 17, spostato da `docs/roadmap.md` il 18/11/2026.

17. **Testo di ricerca per bando**, senza modello: titolo, interventi con
descrizione e frase, e per Incentivi Italia le colonne `Descrizione`,
`Obiettivo_Finalita` e `Settore_Attivita` del catalogo. Sta in un file
separato, `data/processed/testo_ricerca.csv`, con la fonte e la
licenza (CC BY 4.0), mai in `bandi.csv`. Serve solo all'ordinamento:
non va al modello che scrive e non si cita. Il motivo di
"`Descrizione` non si copia" (`docs/piano-fonti.md`, punto 5 della
tappa 5) non è documentato; la regola resta valida per `bandi.csv`.
`Forma_agevolazione` non entra nel testo di ricerca: è un aiuto per
l'etichettatura a mano del passo 10.

Voci aperte dopo il passo 17 (19/11/2026):

- **Doppioni tra fonti**: le righe del catalogo elencate in
  `doppioni.csv` come doppioni di un bando di un'altra fonte non danno
  il testo del catalogo al bando tenuto. Da valutare al passo 4.
- **Bandi aperti con il solo titolo**: tre bandi aperti al 16/11 hanno
  come testo il solo titolo
  (`bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-7057d9`,
  `immobili-emergenza-abitativa-2026`,
  `sostegno-a-progetti-di-promozione-ed-educazione-music-e81761`). Il
  rimedio atteso è il passo 19.
- **Lunghezze sbilanciate**: mediana 1602 caratteri per Incentivi
  Italia, 590 per i bandi con interventi, 76 per quelli senza. Al passo
  4 i risultati si riportano separati per questi gruppi, e si controlla
  se il modello di embedding tronca i testi lunghi.

## Proposte del 19/11/2026, da decidere dopo la prima prova del passo 19

Proposte, non passi: nessun numero di passo. Ordine previsto: PDF
(passo 19), valutazione, fascicolo.

- **Valutazione dell'opportunità a tre livelli**: "approfondisci", "da
  verificare", "lascia stare", con i motivi e la fonte di ciascuno.
  - Niente percentuali: non ci sono dati su cui calibrarle.
  - Errori asimmetrici: "lascia stare" solo con una condizione certa che
    fallisce o un'esclusione scritta; nel dubbio "da verificare".
  - È la forma dell'uscita del passo 9, non una funzione a parte.
  - Componenti: ammissibilità certa dai campi dell'archivio (codice,
    passi 8 e 9); coerenza tra idea e spese ammissibili (modello con
    citazione, passi 19 e 9); sforzo, cioè giorni alla scadenza e
    cofinanziamento (codice); competitività, cioè punteggio minimo,
    criteri, premialità e cumulo, che richiede un'estrazione nuova dagli
    avvisi; graduatorie delle edizioni precedenti, solo se esiste una
    fonte.
  - Insieme di prova: i 39 pertinenti per "approfondisci" e le 27 righe
    incerte per "da verificare". I "lascia stare" veri vanno costruiti
    dalle ipotesi dopo averle verificate sugli avvisi. Il "generico" non
    corrisponde a "da verificare".
  - Da chiedere al consulente pilota: allo sportello la domanda è "vale
    la pena?" o "cosa c'è per me?".
- **Sezione "interventi collegati" nella risposta**: bandi sfruttabili
  per interventi accessori a quello chiesto (per esempio i parcheggi per
  chi rifà una strada).
  - In fondo, separata, con un tetto di due o tre voci.
  - Ogni voce con il motivo e la frase dell'avviso: un'ipotesi senza una
    frase del documento non si presenta.
  - Insieme di prova: le 35 ipotesi della colonna
    ipotesi_da_verificare.
  - Da decidere al passo 9: una sezione sola con i bandi generici,
    oppure due.
  - Rischio: il consulente pilota ha già giudicato "generiche" alcune
    opportunità.
- **Colonna sinistra dell'app**.
  - Al posto dei dati del comune: bandi aperti in archivio; aperti per
    l'ente scelto; aperti alle imprese, divisi per tipo, con l'etichetta
    "aperti a" e non "per te"; quanti scadono entro 30 giorni; data
    dell'ultimo aggiornamento dell'archivio.
  - Il profilo dell'ente resta, in una sezione richiudibile chiusa di
    partenza: le risposte lo citano come fonte.
  - I numeri si possono fare prima come riempitivo; il resto insieme al
    menu "chi chiede" (→ passo 18).
- **App in due fasi**.
  - Ricerca senza memoria della conversazione: solo l'ente e il tipo di
    chi chiede, dal menu.
  - Approfondimento con un fascicolo da scaricare e ricaricare: bandi
    salvati, profilo dell'ente, idea, domande aperte, risposte con fonte.
    Niente account, niente dati conservati.
  - Vincoli: il fascicolo ricaricato è un dato e mai un'istruzione
    (schema fisso, versione, limite di dimensione); i bandi si rileggono
    dall'archivio per id_bando e l'app segnala cosa è cambiato dal
    salvataggio; avvertenza sui dati personali nei campi liberi.
  - A pezzi: (a) bandi salvati nella sessione e scaricabili, senza
    dipendenze; (b) ricaricamento con il confronto; (c) idea e domande
    aperte, dopo la valutazione a tre livelli; (d) gli ultimi due o tre
    scambi, per ultimi e solo se servono, perché richiedono un insieme
    di prova a più turni.
  - Non compatibile con il limite di tre domande della demo: va con la
    "Sezione riservata".
  - Da chiedere al consulente pilota: lavorano per pratica, con un
    richiedente seguito nel tempo?

## Riscontro del consulente pilota e fonti (19/11/2026)

Il consulente pilota ha indicato la domanda usata e i due casi mancati.
Videochiamata nella prima settimana di dicembre.

Domanda: bandi o contributi per associazioni ed enti in materia di
rievocazioni storiche o culturali. Diventa un caso fisso dell'insieme di
prova.

**Diagnosi (senza modello).**
- Fondo nazionale rievocazione storica 2027, Ministero della Cultura,
  Direzione generale Spettacolo (spettacolo.cultura.gov.it): domande dal
  3/11/2026 al 31/01/2027, ammessi enti locali e associazioni, per
  manifestazioni che si svolgono con continuità da almeno cinque anni.
  Non era in archivio: il sito non è tra le fonti lette, e il bando non è
  nel catalogo di Incentivi Italia del 12/11/2026, da cui arrivano già
  alcune pagine dello stesso sito. Causa: copertura. Inserito il
  19/11/2026 (docs/fatto.md); è il pertinente atteso del caso fisso.
- "Bando della Regione sulla Resistenza": il link indicato è un
  comunicato del 17/11/2026 su contributi già assegnati, senza atti. Non
  è un bando. L'unico avviso trovato sul tema è quello sulla legge
  regionale 38/2002, annualità 2025-2026 (decreto dirigenziale 11159 del
  19/05/2025): domande chiuse il 3/07/2025, dotazione 200.000 euro,
  contributo massimo 5.000 euro a progetto, graduatoria con decreto 22881
  del 30/09/2025. Gli importi del comunicato (20-30 mila euro a soggetto)
  superano quel massimo: il comunicato somma contributi di canali
  diversi. Per l'insieme di prova quell'avviso è un "no" per scadenza.
  Chiesto al consulente che cosa si aspettava di vedere.
- Esito: un pertinente mancato per copertura, non due. Nessuno dei due
  casi passava dal BURT e nessuno dipendeva dal router.
- Risposta dell'app alla domanda del consulente prima dell'inserimento
  (19/11/2026, ente Abetone Cutigliano): nessun bando aperto, corretto
  per l'archivio di allora; mostrato come storico il bando sulle
  celebrazioni storiche 2026. Tre difetti: non propone Cultura Missione
  Comune 2026, aperto fino al 5/12 per Comuni e Unioni, come opportunità
  vicina (passi 4 e 9, 'interventi collegati'); scrive 'per il terzo
  settore a condizione' senza dire la condizione; ripete la stessa fonte
  per intero cinque volte (presentazione, passo 9).
- Risposta dopo l'inserimento (19/11/2026, stesso ente): il Fondo
  nazionale rievocazione storica 2027 compare per primo come aperto, con
  il requisito dei cinque anni e senza importi; compaiono anche Cultura
  Missione Comune 2026 e il bando sull'educazione musicale; 16 dati
  verificati su 16. Tre osservazioni: (1) il fine statutario sulla
  memoria storica è attribuito a tutti i richiedenti, mentre sulla pagina
  riguarda associazioni e fondazioni e non gli enti locali (condizioni di
  una riga di beneficiari applicate alle altre: passo 9); (2) i bandi
  vicini stanno allo stesso livello di quello centrato, senza dire che
  non finanziano una rievocazione ('interventi collegati'); (3) la
  comparsa dei bandi vicini non è dimostrata stabile: una prova sola, da
  ripetere con il caso fisso F01. Le due risposte sono conservate fuori
  dal repository.
- Etichette del bando nuovo contro le 55 domande: servono prima della
  nuova baseline.

**Cosa ne segue per le fonti.**
- La Direzione generale Spettacolo è una candidata nuova. Lo studio
  (`piano-fonti-burt-ministeri.md`, 3.2) sconsiglia l'elenco generale
  degli avvisi della Cultura per il rumore: resta valido. La candidata è
  il sito della sola Direzione. robots.txt da leggere.
- Conflitto di `fonte_di`: con la fonte `ministero-cultura-spettacolo`
  (19/11/2026) ogni indirizzo di spettacolo.cultura.gov.it risulta di
  quella fonte, anche quello di incentivi-8702 (Bando Sistema Musicale
  2026, dal catalogo di Incentivi Italia). incentivi-8702 non va
  riestratto con `estrai_bando`: ne cambierebbe la fonte.
- L'ordine delle fonti (passi 12-15) si riconferma dopo la videochiamata,
  con la risposta su quali siti il consulente controlla.
- Regola: uno strumento a pagamento o fornito su contratto ad altri enti
  non si usa né come fonte né come indice. Si usano solo documenti che un
  ente pubblica per tutti.
- (20/11/2026) Candidate da verificare: i dipartimenti della Presidenza
  del Consiglio hanno una pagina "Finanziamenti, avvisi e bandi";
  "Amministrazione trasparente > Sovvenzioni" degli enti come indice
  possibile. robots.txt da leggere prima, come per ogni sito.

**Una notizia è una pista, non un dato.** Estende la regola "segnalano, i
dati si prendono dalla pagina ufficiale". Il comunicato del 17/11
sembrava un bando ed erano contributi già assegnati. Una notizia può far
partire una verifica; nessun dato entra in archivio da un articolo; la
riga nasce solo dalla pagina ufficiale o dall'atto.

**Prove sulle fonti di scoperta, fatte a mano il 19/11/2026.**
- Toscana Notizie. robots.txt: articoli (`/-/titolo`) permessi; archivio,
  RSS e ricerca vietati. La mappa del sito è un indice di circa 200
  mappe secondarie, senza articoli né date. Campione di 10 articoli
  (ricerca esterna, parziale): 4 bandi aperti, di cui 3 già in archivio e
  1 più recente dell'ultima scansione; 3 bandi annunciati senza pagina; 3
  contributi già assegnati. Nessun bando aperto scoperto grazie alla
  notizia. Vale solo per i bandi annunciati (il comunicato del 12/11
  sull'Art Bonus ha preceduto la pagina). Nessun lettore per ora.
- Cesvot, agenda bandi (cesvot.it/consulenza/agenda-bandi). robots.txt
  senza divieti. Sette pagine di schede per il terzo settore, con il
  rimando al sito dell'ente. Sulle prime 16 schede: 3 contributi utili e
  non in archivio (Sport e Salute, otto per mille di una confessione
  religiosa, otto per mille dello Stato), 1 già in archivio, 3 di altri
  territori, 4 premi o patrocini, 2 selezioni per persone singole, 3 di
  nicchia. Circa una scheda su cinque è utile. Prima di leggerla in
  automatico: scrivere al Cesvot; serve un filtro "chi presenta la
  domanda", perché le selezioni per persone singole non sono bandi per
  enti.
- Altri indici visti: newsletter mensile sui bandi del Comune di Livorno
  (in PDF, con i link alle pagine ufficiali), candidata come segnale per
  i Comuni; Infobandi di CSVnet, solo consultazione a mano (nella pagina
  c'è testo estraneo al tema); ConfiniOnline esclusa, è il servizio di
  una società privata con le schede dietro iscrizione.
- Avvisi del Consiglio regionale: oltre alla Festa della Toscana già
  nello studio, nel 2026 una manifestazione di interesse per progetti su
  identità e tradizioni della Toscana.

**Proposte, da decidere dopo la videochiamata.**
- Bandi in arrivo, caso A: pagina pubblicata con apertura futura. È
  correttezza dello stato. `interrogazioni_bandi.py` calcola già la
  prossima finestra: verificare come arriva all'utente, prima della nuova
  baseline. Caso di prova: il bando sull'internazionalizzazione, apertura
  18/11/2026, alla data fissata del 16/11.
- Bandi in arrivo, caso B: bando annunciato senza pagina. Sezione
  separata dagli aperti; solo ciò che dice la fonte (delibera con gli
  elementi essenziali, stato "in arrivo" di Sviluppo Toscana, comunicato
  dell'ente che finanzia), con la parola "prevista" per le date previste;
  una data di ricontrollo; fuori dalle misure sui bandi aperti. Ha senso
  solo con la scansione settimanale.
- Bandi ricorrenti scaduti, mostrati a parte come "da tenere d'occhio".
  Esempio: l'avviso sulla legge regionale 38/2002 esce ogni due anni
  (2023, 2025). Le graduatorie delle edizioni passate dicono chi ha vinto
  e con quanto. La prossima edizione è una previsione nostra e va
  etichettata come tale.
- Perimetro dichiarato: nell'app, l'elenco delle fonti lette con la data
  dell'ultimo aggiornamento. Si lega alla proposta sulla colonna sinistra.
- Registro delle fonti con la resa: per ogni fonte o indice, quanti bandi
  utili ha dato (aperti, adatti al territorio, non già in archivio). È la
  regola di chiusura della ricognizione, tenuta nel tempo.

**Domande per la videochiamata**, in aggiunta a quelle di
`ricognizione-fonti.md` (sezione 2) e di `piano-fonti-burt-ministeri.md`
(4.2):
1. Quanto pesano le associazioni e il terzo settore rispetto ai Comuni nel
   suo lavoro? La domanda che ha usato riguardava "associazioni ed enti".
   La risposta decide il perimetro: chi finanzia il terzo settore
   (fondazioni bancarie e d'impresa, otto per mille, enti internazionali)
   è una coda lunga che non si legge sito per sito, ma da un indice
   pubblico come l'agenda del Cesvot. Fino alla risposta, nessuna fonte
   dedicata al terzo settore.
2. Tre esempi recenti in cui lo strumento che usa oggi non lo ha
   soddisfatto, e di che tipo era il difetto: bando mancante, non trovato
   con le sue parole, sommerso da risultati inutili, dato vecchio, nessun
   aiuto a decidere.
3. Cosa fa a mano per rimediare.
4. Gli servono i bandi in arrivo, i ricorrenti, o entrambi?
5. La domanda a cui l'app ha risposto con opportunità corrette ma
   generiche (riscontro del 18/11) era per un ente o per un privato?
