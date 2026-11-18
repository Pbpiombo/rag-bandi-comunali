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
   provare.
- (era la voce 7 dei Prossimi passi, → principio "per chi", → passo 18) **Privati nell'app**: selettore pubblico/privato e tipo di privato a
   macrogruppi. Insieme, l'abbinamento strutturato tra interventi e tipi
   di beneficiario: oggi la riserva sta solo nel testo della descrizione
   ("Adeguamento e ampliamento della viabilità rurale, solo enti
   pubblici", AS01 del GAL), e un terzo settore che chiede quali
   interventi può fare non riceve un filtro, solo il testo.
- (era la voce 8 dei Prossimi passi) **Sezione riservata**: accesso, iscrizioni con mail e ricerche salvate su
   Supabase, tasto "aggiorna adesso" che lancia il processo su GitHub,
   segnalazione manuale di un bando. Parte pubblica limitata a 3 domande per
   sessione, con un tetto giornaliero complessivo e un invito a scrivere per
   l'accesso.
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

- Dopo la demo. Avviso del decreto 9550 del 28/04/2026 (rafforzamento
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
  pagina ufficiale.

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

## Insieme di prova: dopo

→ passo 5 per l'insieme di controllo.

Metodo in `docs/piano-insieme-prova.md`.

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

1. (→ "In attesa" della roadmap) **Diagnosi dei due bandi mancati**, appena arrivano domanda e titoli.
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
risorse genetiche. Poi la nuova baseline: tre registrazioni delle 55
domande, circa 10,5 $; assorbe il passo 6.

Rimaste dopo il passo 2a (18/11/2026):

- **Fondo di garanzia energie rinnovabili**: aprire a mano il decreto
  dirigenziale 2649 del 27/02/2018 nella banca dati degli atti della
  Regione e, se confermato, aggiornare `verificato_il`. La scadenza
  2021-12-31 oggi non è protetta da una riestrazione esplicita
  (`estrai_bando --auto`, `riclassifica_bandi --id`): la protezione, una
  riga "manuale" in `scadenze_bando`, aspetta la frase letta a mano.
- **incentivi-5013 e incentivi-3373** hanno il link alla banca dati del
  BURT: pagina vera da cercare a mano.
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
