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

## Disegno dell'app (22/11/2026)

Deciso il 22/11/2026 da chi mantiene il progetto. Non si costruisce ora.

Prima parte, in tre passi:
1. elenco dei bandi, con selezione e tasto "approfondisci";
2. scheda in parole semplici dei bandi scelti: a chi è rivolto, come si
   accede, cosa si ottiene; non come si compila la domanda;
3. domande puntuali sul bando scelto.

Seconda parte, dopo: la compilazione.

Errori, per passo:
- selezione: è grave perdere un bando adatto; è tollerabile averne due
  in più, se pertinenti;
- scheda: è grave un dato sbagliato; è tollerabile una voce vuota;
- domande: è grave una risposta sbagliata data con sicurezza; è
  tollerabile "non lo trovo".

Traguardo indicato: 85-90% di risposte giuste. L'85% di recupero che si
misura nel 19d è una condizione necessaria, non quel numero: le risposte
vere si misurano nel 19e.

Conseguenze:
- **19e**: la selezione dei bandi è la fonte del filtro per bando, al
  posto di "l'app indovina il bando", nei casi in cui c'è una selezione
  ("Passo 19d", punto 7).
- **Scheda per bando**, passo a sé (passo 22 della roadmap), fuori dal
  "Parcheggio":
  - (era la seconda voce del "Parcheggio", in fondo a questo file)
    **Scheda per bando** (era la strada 4). Attacca le domande sulle voci
    ricorrenti di un bando. Aspetta la chiusura del 19d e domande non
    scritte da un modello, perché le sue otto voci sono le categorie del
    foglio dei fatti ("Passo 19d", punto 9).
  - (22/11/2026) Generata al caricamento, con una fonte per ogni riga,
    i numeri controllati dal verificatore, la voce vuota se il bando non
    lo dice. L'ordine tra la scheda e il filtro del 19e si decide a 19d
    chiuso. Voce vicina, più vecchia: la prima di "Prossimi passi, voci
    numerate", qui sotto (per chi è e per cosa si può usare, con le
    clausole citate).
- **Domande che escono dal bando** (esempio: "quali sono le risorse
  genetiche iscritte ai Repertori regionali?"): la risposta giusta oggi è
  "il bando rimanda a quel documento, che non è tra quelli caricati".
  Caricare i documenti richiamati resta in "Parcheggio".

Aggiunte (22/11/2026, prima della misura delle domande a mano):
- **Più bandi insieme.** Nel passo 1 si possono selezionare più bandi
  insieme; la scheda del passo 2 e le domande del passo 3 valgono per
  tutti quelli selezionati.
- **Durata della selezione.** Nella prima parte la selezione vale per la
  sessione in corso. Il salvataggio dei bandi scelti sta nella seconda
  parte, quella che accompagna nella stesura della domanda.
- **Segnalazione degli errori**, da definire nel passo 20 ("Tasto di
  segnalazione sulla risposta", più sotto): un comando in fondo a ogni
  risposta, con un campo libero; in più, solo nell'elenco del passo 1, un
  comando leggero per ogni bando ("non c'entra con la mia domanda"), che
  serve a misurare la precisione della selezione con dati veri. Le
  segnalazioni stanno nel database, mai in un file del repository, con
  un avviso a non scrivere dati personali.
- **Domande puntuali e domande a elenco** ("come ottengo di più?", "cosa
  posso comprare?"): le seconde hanno la risposta in più passaggi. La
  misura del 19d le conta trovate solo se compare il passaggio del
  fatto: è un limite della misura da ricordare quando si leggono i
  mancati, e un motivo in più per la scheda del passo 2.

Aggiunte (23/11/2026, decise in chat da chi mantiene il progetto):
- **Due macro parti.** La prima è l'app attuale, nei tre passi qui
  sopra; il passo 3 comprende le domande complesse e i chiarimenti sui
  bandi scelti: le domande tecniche di dettaglio stanno qui. La seconda
  parte è l'area privata (qui sotto).
- **Scansione regolare delle fonti.** La prima parte la richiede già. È
  stata fatta una sola volta, il 13/11/2026: da riprendere tra le prime
  cose a 19d chiuso, prima della videochiamata di dicembre (roadmap,
  "Ordine dei passi").
- **Area privata, seconda parte**, scritta come direzione e non come
  passi numerati: bandi salvati in cartelle per progetto; profilo
  (azienda, comune, tecnico); seguito per compilare le domande e trovare
  tecnici; notifiche dei bandi nuovi, che riusano la scansione della
  prima parte. Richiede profili e quindi dati personali: mai nel
  repository. Argomento per la videochiamata con il consulente pilota:
  cosa userebbe davvero. Voci vicine: "Sezione riservata" e "Percorso
  guidato per gli iscritti" (Prossimi passi).
- **Tre tipi di domanda**: puntuale, a elenco, di significato. Per
  quelle di significato la risposta non sta nel bando: l'app può
  rispondere solo dichiarando che è una spiegazione generale e non un
  dato del bando, tenuta separata. Termini per il glossario in
  "Parcheggio", "Glossario".

Testo della decisione com'era in roadmap, "Decisioni prese" (spostato
il 23/11/2026):
- **Disegno dell'app** (22/11/2026, da chi mantiene il progetto; non si
  costruisce ora): prima parte in tre passi, elenco dei bandi con
  selezione e "approfondisci", scheda dei bandi scelti (passo 22),
  domande puntuali sul bando scelto, anche su più bandi selezionati
  insieme; la selezione vale per la sessione, il salvataggio dei bandi
  scelti sta nella seconda parte, la compilazione, che viene dopo. Errori
  gravi: perdere un bando adatto, un dato sbagliato nella scheda, una
  risposta sbagliata data con sicurezza; tollerabili: due bandi in più se
  pertinenti, una voce vuota, "non lo trovo". Traguardo indicato: 85-90%
  di risposte giuste. Dettaglio in `coda.md`, "Disegno dell'app
  (22/11/2026)".

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

   **Letture dei siti e stato dei requisiti** (23/11/2026, scansione in
   due tempi: ricognizione senza modello, poi estrazione scelta a mano da
   chi mantiene il progetto). La scansione del 13/11/2026 è stata fatta
   senza leggere il robots.txt e con l'intestazione di un browser
   (`INTESTAZIONI` di `src/estrazione/pagina.py`). Dal controllo del
   23/11/2026, senza rete, gli indirizzi letti allora risultano permessi
   dal robots.txt della Regione salvato il 19/11/2026, tranne uno su 205:
   `regione.toscana.it/ricerca-atti`, vietato da `Disallow: */ricerca`.
   I 205 sono tutti gli indirizzi su `regione.toscana.it` in `scansioni`,
   di ogni scansione e fonte; permessi anche i due elenchi e i 64 bandi
   della Regione in archivio.
   Da questa scansione in poi le letture di elenchi e pagine di
   `estrai_nuovi` e della ricognizione (`scripts/ingestione/ricognizione.py`)
   passano da `Lettore` (`src/estrazione/lettore_siti.py`): robots.txt
   letto, intestazione del progetto, pausa per host, stop su 401 e 403
   senza un secondo tentativo con un'altra intestazione, registro in
   `dati-grezzi/scansioni/<data>/richieste.csv`.
   - chiuso: robots.txt letto prima di elenchi e pagine, in `estrai_nuovi`
     e nella ricognizione; `scopri_bandi` no, legge ancora con
     `scarica`;
   - chiuso: intestazione del progetto su tutte le letture di
     `estrai_nuovi` e della ricognizione (decisione del 23/11/2026);
   - in parte: ricontrollo dei bandi aperti e chiusi da poco, per le
     proroghe. La ricognizione rilegge, senza modello, la pagina dei
     bandi della Regione aperti o scaduti da non più di 60 giorni e
     confronta la scadenza del campo con l'archivio; il rapporto non
     cambia l'archivio, la riestrazione resta a mano. Gli scarti
     "scaduto" di `scansioni` scaduti da non più di 60 giorni si
     rileggono anche loro (gruppo "già viste", voce 7, caso SRA28);
     resta aperta l'impronta del testo (corretto il 24/11/2026: prima
     diceva che restavano aperti anche gli scarti "scaduto");
   - in parte, voce 13: test di `estrai_nuovi` con `Lettore` e pagine
     finte (pagina vietata, 403 in preselezione), in
     `tests/test_ricognizione.py`; il percorso fino all'estrazione no;
   - in parte, voce 9: se un host si ferma durante la preselezione, gli
     scaduti già registrati si esportano in `scansioni.csv`; il resto
     della voce resta aperto;
   - aperti: voce 2, voce 8, impronta del testo, elenchi dei programmi,
     GitHub Actions e ricostruzione dopo il push. Voce 15 era già fatta.
   - (23/11/2026) `riclassifica_bandi` non si lancia finché non legge
     attraverso `Lettore`. Si porta su `Lettore` prima del secondo tempo,
     solo se la ricognizione trova bandi cambiati.
   - (23/11/2026) Requisito aperto: togliere il percorso senza `Lettore`
     da `src/estrazione/elenco.py` e `scripts/ingestione/estrai_nuovi.py`
     (richiede di portare `tests/test_acquisizione.py` e
     `tests/test_gal.py` su una rete finta di `Lettore`), e portare su
     `Lettore` gli altri script che leggono i siti: `scopri_bandi`,
     `estrai_bando`, `estrai_incentivi`, `importa_incentivi`,
     `aggiungi_contatti`, `applica_regole_verifica`, `correggi_atti`,
     `correggi_doppioni_tenuti`, `importi_missione_comune`,
     `carica_istat`. Fino ad allora non si lanciano contro i siti.
   - (23/11/2026) Nella ricognizione c'è la nota "possibile proroga" per
     parole chiave (`src/estrazione/proroga.py`: proroga, prorogato,
     prorogata, prorogati, differimento, differito, riapertura dei
     termini, riaperti i termini, come parole intere, nel testo della
     pagina e nei nomi dei file collegati). La data prorogata si estrae
     nel secondo tempo dall'atto, con la frase di prova.
   - (23/11/2026) Le pagine lette da ogni scansione restano salvate nella
     cartella del giorno in `dati-grezzi/scansioni/` e non si cancellano:
     sono il materiale da cui ricavare in seguito le voci della traccia,
     senza rileggere i siti. Le pagine dei bandi chiusi spariscono dal
     Portale, quindi una scansione saltata è storia persa.
   - (23/11/2026) Requisito aperto, collegato alla voce 7, idea di chi
     mantiene il progetto del 23/11/2026: **traccia dei bandi non
     estratti**. Per le pagine non estratte per intero (scadute alla
     scoperta, vietate dal robots.txt) si salva una riga in una tabella a
     parte, con il suo CSV, fuori dalla tabella dei bandi: l'app non le
     propone come bandi e le usa solo per le domande sul cumulo e per
     l'avviso "questo bando di solito esce in questo periodo". L'esito
     "scaduto" non è definitivo per 60 giorni. Voci in tre tipi:
     - lette dalla pagina, senza modello, con la pagina come fonte:
       titolo, indirizzo, ente e ufficio responsabile; scadenza, data di
       pubblicazione e di apertura; data di scoperta e dell'ultimo
       controllo; elenco di provenienza; titoli e indirizzi degli atti
       allegati; possibile proroga; motivo della mancata estrazione;
       impronta del testo della pagina; programma o fondo, se la pagina
       lo dice;
     - ricavate dal codice confrontando più bandi, da scrivere come
       ipotesi e non come fatti: anno dell'edizione; famiglia del bando
       (titolo senza l'anno); possibile edizione precedente; ricorrente
       (almeno due edizioni della stessa famiglia); periodo abituale di
       uscita. L'archivio parte da novembre 2026: la storia si costruisce
       scansione dopo scansione;
     - interpretate, con il modello o a mano: a chi è destinato (se la
       pagina non ha un campo apposito), tipo di procedura, dotazione e
       importo massimo, com'è andata (graduatoria, fondi esauriti); bandi
       citati dentro il bando.

     In più, per ogni riga, il livello di completezza: traccia minima,
     estratto, verificato a mano. Fuori dalla traccia: "se si è avuto
     accesso al bando" è un'informazione su un utente, sta nell'area
     privata (seconda parte) e non entra nel repository. Ordine: prima si
     guarda quali campi la pagina della Regione espone in modo ordinato,
     sulle pagine salvate dalla ricognizione; poi un piano breve in
     `docs/`; si costruisce dopo la videochiamata di dicembre, dove si
     chiede al consulente pilota quali voci userebbe.
   - (23/11/2026) La prima ricognizione ha riletto 111 pagine già viste,
     per una definizione troppo larga di "nuovi": 166 richieste invece
     delle 62 stimate, tutte permesse dal robots.txt, con le pause e con
     codice 200. Corretto lo stesso giorno: "nuovi" sono le voci degli
     elenchi che non sono né in `bandi` né in `scansioni`; quelle in
     `scansioni` vanno nel gruppo "già viste", con l'esito e il motivo di
     allora, e la loro pagina si rilegge solo se l'esito non è definitivo
     o se erano scadute da non più di 60 giorni. Un bando a sportello in
     archivio senza scadenza nel campo della pagina va tra gli
     "invariati" con la nota "a sportello", non tra i "da verificare".
   - (23/11/2026) Esito della ricognizione: 5 voci mai viste, 6 bandi con
     scadenza diversa tra archivio e pagina, 2 scaduti dal 13/11, nessuno
     sparito, nessuno vietato.
   - (23/11/2026) Osservazione: in due dei sei casi (mercati rionali,
     percorsi formativi) l'archivio ha una data successiva a quella del
     campo della pagina, e il testo della pagina dice la proroga: il
     campo non sempre viene aggiornato dopo una proroga.
   - (23/11/2026) L'elenco "bandi aperti" del Portale contiene voci
     scadute da anni (dal 2013): conferma che lo stato si calcola dalla
     scadenza.
   - (24/11/2026) Requisito: il campo "scadenza" della pagina non è
     affidabile da solo. Il 23/11 mercati rionali, percorsi formativi e
     voucher Just in Time avevano il campo vecchio o sbagliato e il testo
     giusto (verifica di chi mantiene il progetto). Sul valore decide il
     testo, con la frase di prova; il campo resta un indizio per la
     ricognizione.
   - (24/11/2026) Nella ricognizione, se la data del campo coincide con
     una delle finestre del bando in `scadenze_bando` (solo le righe di
     genere "domanda", in ordine di numero), il bando va tra gli
     "invariati" con la nota "il campo indica la finestra n. X di Y", e la
     scadenza che vale per scaduti e spariti resta quella dell'archivio.
     Rapporto rifatto dalle pagine salvate del 23/11 alla stessa data
     (`ricognizione-3.csv`, `--oggi 2026-11-23`): 4 cambiati invece di 6;
     dopo la laurea (finestra 3 di 4) e incentivi ai datori di lavoro
     privati (finestra 4 di 5) passano tra gli invariati.
   - (24/11/2026) Requisito aperto: lo stesso confronto con le finestre
     in `preselezione` (`src/estrazione/scadenza.py`) e in `estrai_nuovi`,
     che oggi confrontano solo con `bandi.scadenza`. Non fatto: deciso il
     24/11/2026 di tenerlo per dopo.
   - (24/11/2026) Opzioni nuove della ricognizione: `--oggi AAAA-MM-GG`,
     per rifare il rapporto di una cartella salvata alla sua data, e
     `--testi`, che accanto al rapporto scrive per ogni bando cambiato, e
     per ogni bando con la nota "possibile sospensione", le righe di
     `scadenze_bando`, la data del campo e le frasi intere della pagina
     con una data e una parola di scadenza o di sospensione.
   - (24/11/2026) Nota "possibile sospensione" nella ricognizione, con lo
     stesso meccanismo della proroga (`src/estrazione/sospensione.py`:
     sospensione, sospeso, sospesa, sospesi, sospese, chiusura
     anticipata, chiuso anticipatamente, chiusa anticipatamente, risorse
     esaurite, esaurite le risorse, fondi esauriti). Non cambia il gruppo
     né le date. Sul rapporto del 23/11 scatta per sei bandi; uno solo è
     una sospensione vera (incentivi ai datori di lavoro privati). Gli
     altri cinque hanno formule non coperte dalle esclusioni: "salvo
     chiusura anticipata per esaurimento delle risorse" (due bandi per
     le donne in percorsi di uscita dalla violenza), "si riserva la
     facoltà di prevedere la chiusura anticipata dello sportello"
     (progettualità sui dati), "decreto di sospensione/chiusura/proroga"
     dentro la riserva di sospendere (Just in Time), "lavoratori sospesi"
     per la Cassa integrazione (assunzione di donne). Da decidere se
     togliere queste formule.
     Deciso il 24/11/2026 da chi mantiene il progetto, su quei cinque casi
     veri: tre esclusioni (`REGOLE` in `src/estrazione/sospensione.py`).
     Una parola chiave non conta se (a) nella stessa frase, prima di lei,
     c'è "salvo" o "si riserva la facoltà / la possibilità / il diritto
     di"; (b) è in "sospensione (sospensioni) dal lavoro", "lavoratori
     sospesi", "lavoratrici sospese"; (c) ha una barra subito prima o
     dopo ("sospensione/chiusura/proroga"). Una parola chiave che viene
     prima di "salvo" conta: "Il bando è sospeso, salvo nuove risorse" dà
     la nota. Le frasi escluse non spariscono: con `--testi` vanno nel
     file del bando, nella sezione "Frasi escluse come formule di rito",
     con la regola che le ha escluse, e il file si scrive anche per un
     bando che ha solo frasi escluse (che per questo non ha la nota e non
     entra tra gli invariati). Rapporto rifatto alla stessa data
     (`ricognizione-4.csv`): 1 possibile sospensione (incentivi ai datori
     di lavoro privati), 4 cambiati, 18 invariati. Sulle 163 pagine
     salvate del 23/11 le regole escludono 12 frasi su 7 pagine, tutte
     formule "salvo chiusura anticipata" o già tra i cinque casi; restano
     valide, con un altro significato, "sospesi dall'accreditamento" e
     "sospeso l'assegno di ricollocazione", su due voci già viste che la
     ricognizione non rilegge. Nello stesso giorno la nota di proroga
     usa le frasi intere di `--testi`, che non si spezzano a "n." o
     "art.": sul rapporto del 23/11 cambia una nota (celebrazioni
     storiche).
   - (24/11/2026) Errore in archivio: incentivi ai datori di lavoro
     privati per l'occupazione dei disoccupati
     (`incentivi-ai-datori-di-lavoro-privati-per-l-occupazio-801298`) è
     aperto in archivio fino al 10/01/2028, ma è sospeso dall'8/07/2026
     per le categorie dell'articolo 5 lettere a, b, c, d, e (decreto
     n. 742/2026 di Arti), aperto solo per la lettera f. Fonte: pagina
     del bando salvata il 23/11/2026. Da correggere nel secondo tempo.
   - (24/11/2026) Scansione del Portale della Regione in due tempi:
     ricognizione del 23/11 ed estrazione del 24/11 (`estrai_nuovi
     --fonte regione-toscana`). 116 voci non in archivio, 109 con esito
     definitivo, 2 saltate senza campo leggibile (ricerca finalizzata
     2021 e 2024), 5 al modello: 3 salvate (contributi per
     distribuzione e commercio al dettaglio di giornali; partenariato
     europeo malattie rare ERDERA JTC 2027; partenariato europeo
     trasformazione dei sistemi sanitari JTC 2027) e 2 scartate come
     "non è un bando" (Toscana Art Bonus per comuni e unioni di comuni;
     concorso per 2 unità di istruttore amministrativo). Costo 0,219 $.
     L'elenco "politiche per la montagna, bandi aperti" ha zero voci al
     24/11/2026. Copia di sicurezza del database e prima copia
     congelata dei CSV fatte prima. Dettaglio in `fatto.md`, "Fatti il
     24 novembre 2026".
   - (24/11/2026) Osservazioni dalla lettura a mano delle righe nuove,
     da decidere, nessuna corretta:
     - contributi per giornali: la categoria C dei beneficiari (i
       distributori, fino a 180 euro per Comune servito) non è in
       `beneficiari_bando`. Il controllo della frase l'ha scartata:
       sulla pagina c'è uno spazio dopo la virgoletta che apre e prima
       di quella che chiude ("“ Attività … cancelleria ”"), il modello
       le ha scritte senza, e `frase_nel_testo` toglie lo spazio solo
       prima di ; , : . In `bandi.beneficiari` le tre categorie sono
       scritte con i puntini ("A) Soggetti iscritti al Registro delle
       Imprese... B) ... C) ..."); dotazione vuota (200 + 200 + 50 mila
       euro sulla pagina);
     - partenariato ERDERA: dotazione vuota (la pagina dice 300.000 euro
       più 30.000 per le associazioni di pazienti);
     - nei due partenariati la Regione chiede un modulo almeno 10 giorni
       prima della scadenza della pre-proposal, e THCS anche una
       lettera di interesse almeno 30 giorni prima: date che non sono in
       `scadenze_bando`.
   - (24/11/2026) Restano aperti: la proroga di alta formazione e
     ricerca-azione al 24/11/2026 (decreto dirigenziale 25474 del
     19/11/2026), la sospensione degli incentivi ai datori di lavoro
     privati, le due ricerche finalizzate (2021 e 2024) che tornano
     candidate a ogni scansione, il GAL MontagnAppennino da ricognire a
     parte.
   - (24/11/2026) Difetto trovato: `frase_nel_testo`
     (`src/estrazione/beneficiari.py`) scarta una frase vera quando la
     pagina ha uno spazio dopo la virgoletta che apre o prima di quella
     che chiude, e il modello la copia senza. Caso: la categoria C del
     bando dei giornali ("“ Attività … cancelleria ”"). Lo stesso spazio
     c'è sulla pagina degli incentivi ai datori di lavoro privati ('Il
     bando resta aperto solo per " Persone…'). Da correggere come
     compito a sé, provando la modifica su tutte le pagine e le
     estrazioni salvate per contare quante frasi scartate in passato
     recupererebbe. Per la categoria C la correzione a mano è preparata in
     `correggi_da_testo` (frase copiata dalla pagina con gli spazi).
   - (24/11/2026) Dati non presi dall'estrazione del 24/11 e non
     corretti: dotazione del partenariato sulle malattie rare ERDERA
     (300 mila euro più 30 mila per le associazioni di pazienti); termini
     interni della Regione nei due partenariati (modulo 10 giorni prima
     della scadenza della pre-proposal, lettera di interesse 30 giorni
     prima per THCS). Anche la dotazione dei giornali resta vuota: la
     pagina dà tre quote (200, 200 e 50 mila euro) e nessun totale.
   - (24/11/2026) I 24 falliti di `scansioni`: 17 sono indirizzi tagliati
     alla prima lettera accentata (per esempio "…avviso-di-mobilit"), già
     trattati nella forma completa (salvati o scartati); 2 falliti per
     dotazione non convertibile (corsi di lingua e cultura italiana per il
     terzo settore, pesca e acquacoltura indennizzi), bandi veri persi per
     un difetto di lettura dell'importo; gli altri 5 sono 404 (4 della
     Regione, uno di Incentivi Italia). Proposta: marcare i 17 con un
     motivo che dica che l'indirizzo completo è già trattato.
   - (24/11/2026) Un bando per i datori di lavoro (`incentivi-4939`,
     contributi a sostegno dell'occupazione dei tirocinanti under 35, dal
     catalogo Incentivi Italia) è registrato con il solo tipo "cittadini e
     famiglie": il tipo viene dalla voce "Cittadino" del catalogo.
   - (24/11/2026) Da decidere: se `data/db/comune.sqlite` deve restare
     tracciato da git, visto che i CSV sono la fonte di verità. Oggi
     l'app online lo legge dal repository (`connetti`, `SQLITE_PATH` in
     `src/config.py`) e non lo ricrea dai CSV all'avvio; è la voce già
     in coda "`data/db/comune.sqlite` sotto git" e il punto 10 della
     revisione del 12/11/2026, ancora aperto. L'estrazione del 24/11 lo ha
     modificato insieme ai CSV.
   - (24/11/2026) Toscana Art Bonus per comuni e unioni: rivolto ai comuni
     interessati dai Progetti di Paesaggio approvati o avviati e dagli
     studi di fattibilità elencati sulla pagina, non a tutti; l'elenco di
     quei comuni non è in archivio (vedi "Profilo dei comuni").
   - (24/11/2026) Correzioni a mano applicate con `correggi_da_testo`,
     con le frasi di prova dei testi salvati in
     `dati-grezzi/manuali/2026-11-24/`: proroga di alta formazione e
     ricerca-azione al 24/11/2026; sospensione degli incentivi ai datori
     di lavoro privati dall'8 luglio 2026 per le lettere a-e
     dell'articolo 5; categoria C e testo dei beneficiari del bando dei
     giornali. Le correzioni non sono protette da una riestrazione
     futura: se uno di questi bandi si riestrae, vanno rifatte o
     ricontrollate (dettaglio in `fatto.md`, "Fatti il 24 novembre
     2026").
   - (24/11/2026) La dotazione del bando dei giornali resta vuota: la
     pagina dà tre quote (200 mila, 200 mila, 50 mila euro) e nessun
     totale, e la somma non è un dato della fonte. Serve un campo di testo
     per le dotazioni in più quote: da decidere con il passo 2b.
   - (24/11/2026) Deciso da chi mantiene il progetto: la demo online
     legge `data/db/comune.sqlite` committato e non lo ricrea dai CSV,
     per questo resta sotto git (risponde alla riga "Da decidere" qui
     sopra; resta aperta la voce "`data/db/comune.sqlite` sotto git", che
     chiede di ricrearlo all'avvio prima di toglierlo).
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
     (23/11/2026: fatto per `estrai_nuovi` e per la ricognizione, che
     leggono con `Lettore` e l'intestazione del progetto; `scopri_bandi`
     no. Stato in "Prossimi passi, voci numerate", voce del passo 11,
     "Letture dei siti e stato dei requisiti".)
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
   - **I PDF restano fuori da Supabase** (20/11/2026): l'app usa solo i
     frammenti; il registro (`data/processed/documenti_bandi.csv`) ha
     per ogni file l'indirizzo da cui è stato scaricato e l'impronta.
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
   **Chiuso il 23/11/2026, sotto soglia** secondo la regola del punto 13,
   voce 19 (esito alla voce 20, lettura a mano dei mancati alla voce 21).
   Conseguenze: c-LR tutte è la configurazione degli avvisi; gli avvisi
   vanno in produzione solo con il filtro per bando e con il "non lo
   trovo"; il numero da citare è 77 su 98 (78,6%), B, k=10, metà di
   controllo.
   Stato al 21/11/2026: in chiusura, con il perimetro del punto 10. Non è
   più una verifica, è il lavoro che ridisegna la ricerca nei documenti.
   Al 21/11/2026 sera: mossa 2 fatta (punto 5); mossa 3, il contesto per
   frammento, generata sugli 871 frammenti e non ancora controllata né
   misurata (punto 13); mosse 1 e 4 dopo quella misura (punto 13,
   "Prossimo compito").
   Dalla notte del 20/11/2026 le misure sono sulla taratura intera, 97
   fatti dei due fogli, con la misura esatta (punto 3); quelle sui primi
   40 fatti restano, superate. Il controllo non è mai stato letto.
   Script e divisione in `docs/fatto.md` (20/11/2026); rapporti e copie
   di Chroma in `dati-grezzi/prova/19d/`: `riepilogo_taratura_97.txt` e,
   per la notte, la cartella `notte/` (`parte1_configurazioni_taratura.txt`,
   `parte2_curve_taratura.txt`, `parte3_piu_pezzi_taratura.txt`,
   `parte4_riordinatore_taratura.txt`).
   1. **Regola di chiusura, com'è ora.** Sulla metà di controllo, nella
      condizione B (filtro sul bando, domanda ripulita), la scelta finale
      passa se trova almeno l'85% dei fatti, se non è più di 10 punti
      sotto la taratura, e se nessuna frase di controllo dei gemelli è
      presa dal bando sbagliato. La condizione A si misura e si riporta
      senza soglia; lì i gemelli si contano, non sono un veto. Varianti e
      combinazioni si scelgono tutte sulla taratura, in B e a parità in
      A; il controllo si apre una volta sola, sulla scelta finale, con un
      via esplicito. Il ramo "sotto il 75% dopo tutte le varianti ci si
      ferma e si ripensa il modo di spezzare i documenti" non è stato
      toccato. Correzioni, tutte prima di aprire il controllo:
      - soglia di passaggio dell'85% fissata nella fase di
        pianificazione, prima della consegna del passo e prima di ogni
        misura: la prima proposta era 75%, alzata da chi mantiene il
        progetto perché troppo bassa per informazioni tecniche;
      - ramo tra 75 e 85%: la ricerca per parole che doveva aggiungere
        c'era già (`RecuperoIbrido` unisce BM25 e ricerca per significato
        con RRF), quindi prima della divisione è diventato "la variante
        migliore combinata con la seconda"; annullato prima del secondo
        giro di varianti;
      - B ridefinita dopo la prima misura di taratura (21 su 40 con la
        domanda intera): filtro sul bando più `ripulisci_domanda` con le
        parole del titolo del bando del fatto. Dove non c'è un tratto che
        nomina il bando la domanda resta intera, e la punteggiatura
        rimasta orfana resta, come nell'app. La definizione vecchia resta
        nei rapporti come Bi;
      - dal quarto giro vale la misura esatta (punto 6).
   2. **Come si leggono i numeri.** Dal 20/11/2026 sera due
      configurazioni si confrontano con il test esatto dei segni, a due
      code, sulle coppie discordanti: i fatti trovati da una sola delle
      due. "Entro il rumore" vuol dire p maggiore di 0,05. Si riportano
      sempre i guadagnati e i persi, con le righe, non solo la
      differenza dei totali: due configurazioni con lo stesso totale
      possono trovare fatti diversi. La misura esatta è identica da un
      processo all'altro (punto 6), quindi il rumore è quello del
      campione di fatti, non della ricerca. Prima valeva una soglia fissa:
      con 40 fatti un fatto vale 2,5 punti, e la ricerca di Chroma
      oscillava di un fatto da un processo all'altro, quindi differenze di
      1-3 fatti erano "entro il rumore"; la soglia è sostituita dal test.
      Per questo il foglio è stato portato a 195 fatti (81 del primo
      foglio e 114 del secondo), 97 di taratura e 98 di controllo: sul
      controllo l'85% sono 84 fatti, sulla taratura 83 (82,45). Righe del
      secondo foglio scritte come 2:N.
   3. **Risultati sulla taratura.** Misura esatta, ampiezza 20 per
      lista, fatti trovati su 97, A / B. "1° B" e "≤5 B": fatti con il
      primo frammento giusto al 1° posto e tra i primi 5, in B (non
      dipendono da k). Fonte: `notte/parte1_configurazioni_taratura.txt`
      e `riepilogo_taratura_97.txt`.

      | configurazione | k=10 | k=15 | 1° B | ≤5 B |
      |---|---|---|---|---|
      | v0: 128 token, frammenti del caricamento | 42 / 60 | 53 / 71 | 20 | 45 |
      | v1: 512 token | 45 / 62 | 50 / 66 | 21 | 52 |
      | v2: intestazione nel vettore | 47 / 54 | 54 / 61 | 18 | 44 |
      | v1+v2 | 40 / 54 | 44 / 61 | 22 | 44 |
      | e5-small, 512 token | 48 / 63 | 55 / 74 | 26 | 52 |
      | e5-base, 512 token | 54 / 66 | 60 / 77 | 33 | 60 |

      Confronti con p ≤ 0,05 (tutti gli altri sono entro il rumore; righe
      di guadagnati e persi nel file della parte 1):
      - e5-base contro v0, k=10, A: guadagnati 14, persi 2, p = 0,004; in
        B guadagnati 10, persi 4, p = 0,180, entro il rumore;
      - v2 contro v0, k=15, B: guadagnati 2, persi 12, p = 0,013;
      - v1+v2 contro v0, k=15: A guadagnati 3, persi 12, p = 0,035; B
        guadagnati 3, persi 13, p = 0,021;
      - v1+v2 contro v1, k=10, B: guadagnati 2, persi 10, p = 0,039;
      - k=15 contro k=10, sempre senza fatti persi: v0 +11 in A e in B (p
        = 0,001); e5-small +7 in A (0,016) e +11 in B (0,001); e5-base +6
        in A (0,031) e +11 in B (0,001); v2 +7 in A e in B (0,016); v1+v2
        +7 in B (0,016), +4 in A (0,125, entro il rumore); v1 +5 in A
        (0,062) e +4 in B (0,125), entro il rumore.

      Curva dei frammenti (condizione B, fatti trovati su 97, e caratteri
      del testo dei frammenti passati al modello, media per fatto; fonte
      `notte/parte2_curve_taratura.txt`, punto a):

      | k | 5 | 8 | 10 | 12 | 15 | 20 | 25 | 30 |
      |---|---|---|---|---|---|---|---|---|
      | v0 | 42 | 58 | 60 | 67 | 71 | 75 | 79 | 81 |
      | caratteri v0 | 5.803 | 9.190 | 11.509 | 13.780 | 17.122 | 22.438 | 27.282 | 31.727 |
      | e5-small | 49 | 60 | 63 | 67 | 74 | 78 | 81 | 82 |
      | caratteri e5-small | 5.882 | 9.343 | 11.652 | 13.998 | 17.359 | 22.701 | 27.436 | 31.502 |

      Con v0 i pezzi presi dal gemello compaiono da k=20 (1 a k=20 e 25,
      2 a k=30); con e5-small sono 1 a ogni k.

      Riordinatore (fonte `notte/parte4_riordinatore_taratura.txt`): 30
      candidati dal recupero di oggi (A: `recupera` dell'app con k=30; B:
      ricerca nel bando con la domanda ripulita), un voto per ogni coppia
      domanda e frammento, si tengono i primi 10 o 15; a parità di voto,
      l'ordine di prima. Fatti trovati, A / B:

      | base | riordinatore | k=10 | k=15 | 1° B | ≤5 B |
      |---|---|---|---|---|---|
      | v0 | nessuno | 42 / 60 | 53 / 71 | 20 | 45 |
      | v0 | osiria (italiano) | 58 / 72 | 62 / 78 | 50 | 69 |
      | v0 | mmarco (multilingue) | 58 / 73 | 62 / 77 | 51 | 69 |
      | e5-small | nessuno | 48 / 63 | 55 / 74 | 26 | 52 |
      | e5-small | osiria | 58 / 76 | 63 / 80 | 50 | 71 |
      | e5-small | mmarco | 59 / 75 | 63 / 79 | 51 | 73 |

      Riordino contro nessun riordino, stessa base e stesso k:

      | | k=10 A | k=10 B | k=15 A | k=15 B |
      |---|---|---|---|---|
      | osiria su v0 | +17 −1, p = 0,000 | +14 −2, p = 0,004 | +11 −2, p = 0,022 | +8 −1, p = 0,039 |
      | mmarco su v0 | +17 −1, p = 0,000 | +14 −1, p = 0,001 | +11 −2, p = 0,022 | +8 −2, p = 0,109, entro il rumore |
      | osiria su e5-small | +12 −2, p = 0,013 | +17 −4, p = 0,007 | +12 −4, p = 0,077, entro il rumore | +8 −2, p = 0,109, entro il rumore |
      | mmarco su e5-small | +13 −2, p = 0,007 | +17 −5, p = 0,017 | +12 −4, p = 0,077, entro il rumore | +8 −3, p = 0,227, entro il rumore |

      Calcolati il 21/11/2026 dai CSV di `notte/riordino/`, senza nuove
      ricerche: osiria contro mmarco, stessa base e stesso k, al più 2
      fatti discordanti, p = 1 in tutti gli otto confronti; e5-small
      contro v0, entrambi riordinati, entro il rumore in tutti gli otto
      (p da 0,289 a 1); riordino k=15 contro riordino k=10, nessun fatto
      perso (i primi 15 contengono i primi 10), guadagni da 4 a 6, p =
      0,031 solo per osiria su v0 in B (+6), negli altri sette tra 0,062
      e 0,125, entro il rumore.

      **Risultati sulla taratura dei primi 40 fatti, superati dalla misura
      sui 97 qui sopra.** Trovati su 40;
      ampiezza 20 dove non è scritto altro; "≤5 B" è il numero di fatti
      con il primo frammento giusto tra i primi 5, in B.

      | configurazione | ricerca | k | A | Bi | B | ≤5 B |
      |---|---|---|---|---|---|---|
      | v0: 128 token, frammenti del caricamento | Chroma | 10 | 16 | 21 | 26 | 17 |
      | v1: 512 token | Chroma | 10 | 19 | 26 | 28 | 22 |
      | v2: intestazione nel vettore | Chroma | 10 | 21 | 22 | 27 | 18 |
      | v3: frammenti da 600 caratteri, 200 di sovrapposizione | Chroma | 10 | 10 | 14 | 16 | 16 |
      | v1+v2 | Chroma | 10 | 16 | 20 | 25 | 19 |
      | v1+v2+v3 | Chroma | 10 | 14 | 14 | 18 | 14 |
      | v0, ampiezza 50 | Chroma | 10 | 14 | – | 22 | – |
      | v0 | Chroma | 15 | 23 | – | 32 | – |
      | v0, ampiezza 50 | Chroma | 15 | 20 | – | 26 | – |
      | v1, ampiezza 50 | Chroma | 10 | 17 | – | 27 | – |
      | v1 | Chroma | 15 | 24 | – | 32 | – |
      | v1, ampiezza 50 | Chroma | 15 | 21 | – | 31 | – |
      | v0 | esatta | 10 | 16 | – | 26 | 17 |
      | v0 | esatta | 15 | 23 | – | 32 | 17 |
      | e5-small, 512 token | esatta | 10 | 18 | – | 24 | 22 |
      | e5-small, 512 token | esatta | 15 | 22 | – | 31 | 22 |
      | e5-base, 512 token | esatta | 10 | 20 | – | 28 | 24 |
      | e5-base, 512 token | esatta | 15 | 25 | – | 34 | 24 |

      Primo frammento giusto al 1° posto, in B: v0 7, v1 10, e5-small 12,
      e5-base 15. Nessuna frase gemella presa dal bando sbagliato, salvo
      con e5-base sulla riga 74 (punto 4). Il nome dell'azione degli
      apistici è misurato solo sulle sue righe (punto 5).
   4. **Stato delle strade dopo la notte del 20/11/2026** (97 fatti di
      taratura, misura esatta; numeri al punto 3 e nei file di `notte/`).
      - Riordinatore: **guadagno dimostrato con 10 frammenti**, su v0 e su
        e5-small, in A e in B (p da 0,000 a 0,017). I due provati sono
        `osiria/minilm-l12-h384-italian-cross-encoder` (italiano, licenza
        MIT) e `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`
        (multilingue, Apache-2.0): l'italiano fa quanto il multilingue
        (al più 2 fatti discordanti, p = 1) con circa un quinto della
        memoria, 148-155 MB in più dopo il caricamento contro 728-775
        (su disco 129 MB contro 470). Costo: con 30 candidati, in media
        da 3,9 a 5,4 secondi a domanda su questo computer (Windows, solo
        processore): osiria 5,0-5,4 s in A e 4,3-4,6 in B, mmarco 4,4-4,5
        in A e 3,9-4,0 in B. Da ridurre e da misurare su Streamlit
        Community Cloud prima di adottarlo. Entrambi leggono al più 512
        token, domanda e frammento insieme: con osiria 5 coppie su 2907
        in A (v0) e 4 su 2901 (e5-small) li superano, sempre lo stesso
        frammento, e si taglia la fine del frammento ("longest_first");
        in B nessuna; con mmarco nessuna. Effetto anche sulla posizione:
        primo frammento giusto al 1° posto in B da 20 a 50-51 su v0, da
        26 a 50-51 su e5-small.
      - Modello di embedding: **resta quello di oggi** (v0). e5-small non
        lo batte in nessun confronto (p da 0,180 a 0,791); e5-base solo
        con k=10 in A (+14 −2, p = 0,004), non in B (p = 0,180) né con
        k=15 (p = 0,118 in A, 0,180 in B). Con il riordinatore la
        differenza tra e5-small e v0 sparisce (p da 0,289 a 1); e5-base
        con il riordinatore non è misurato. Peso in memoria più sotto,
        invariato.
      - Limite a 512 token (v1): **chiuso**, non adottato. Contro v0 entro
        il rumore: k=10 B +8 −6 (p = 0,791), k=15 B +3 −8 (p = 0,227), A
        p = 0,607 e 0,508.
      - Intestazione fissa nel vettore (v2): **chiusa**, non adottata. k=10
        B +5 −11 (p = 0,210); k=15 B +2 −12 (p = 0,013), peggiore in modo
        dimostrato. La somma v1+v2 è peggiore di v0 con k=15 (A +3 −12, p
        = 0,035; B +3 −13, p = 0,021) e di v1 con k=10 in B (+2 −10, p =
        0,039).
      - Pesi della fusione: **chiusi**, resta 0,5. Peso della ricerca per
        significato in B con k=10: v0 60 a 0,5, 55 a 0,6, 0,7 e 0,8 (+3
        −8, p = 0,227), 52 a 0,9 (+6 −14, p = 0,115); e5-small 63, 62,
        62, 63, 64, sempre p = 1.
      - 15 frammenti contro 10: senza riordinatore **guadagno dimostrato**,
        senza fatti persi, su v0, e5-small ed e5-base (p da 0,001 a
        0,031; numeri al punto 3). Con il riordinatore i primi 15
        contengono i primi 10, quindi nessun fatto perso, ma il guadagno è
        di 4-6 fatti: dimostrato solo per osiria su v0 in B (72 a 78, p =
        0,031); negli altri sette confronti p da 0,062 a 0,125, entro il
        rumore. Costo in testo: in B su v0 da 11.509 a 17.122 caratteri in
        media per fatto, +49%.
      - Frammenti vicini (per ogni frammento tra i primi 10 anche i vicini
        nello stesso file; v0, B, k=10, 60 trovati senza vicini, 11.509
        caratteri in media): a distanza 1 +13 fatti (3 in più pezzi) con
        25.217 caratteri, 2,2 volte; a distanza 2 +19 (7) con 35.220, 3,1
        volte; a distanza 3 +26 (9) con 43.647, 3,8 volte; a distanza 5
        +31 (11) con 56.166, 4,9 volte; la pagina intera +11 (2) con
        24.212, 2,1 volte. Su e5-small (63 senza vicini, 11.652 caratteri):
        +19, +21, +22, +26 e +18, con 24.206, 33.660, 42.090, 54.278 e
        22.940 caratteri. Per confronto, senza vicini, v0 con k=20 trova
        75 (+15) con 22.438 caratteri e con k=30 81 (+21) con 31.727.
        Fonte: `notte/parte3_piu_pezzi_taratura.txt`.
      - Tetto: tra i 30 candidati da cui parte il riordinatore il
        frammento giusto c'è in 65 fatti in A e 81 in B su v0, in 68 e 82
        su e5-small. In B sono sotto gli 83 fatti dell'85% della
        taratura: nessun riordino dei primi 30 può superarli. I migliori
        con il riordinatore arrivano a 78-80 in B con k=15.
      - Frasi gemelle prese dal bando sbagliato, prima del giusto (19 fatti
        con frase gemella; in B è il veto della regola di chiusura):
        - B: v0 nessuna con k=10 e k=15; v1 la 2:92, più un altro fatto
          (2:103); v2 nessuna, un altro fatto (2:99); v1+v2 la 2:92;
          e5-small la 2:92; e5-base la 74 e la 2:92, e con k=10 la 74 ha
          il gemello tra i primi 10 senza il giusto. Con il riordinatore:
          su v0 nessuna con k=10, la 2:106 con k=15, con entrambi i
          riordinatori; su e5-small nessuna.
        - A: v0 la 2:12 con k=10, la 2:12 e la 2:73 con k=15; v1 nessuna;
          v2 nessuna, ma il gemello tra i primi k senza il giusto in 3
          fatti con k=10 (2:105, 2:106, 2:107) e 2 con k=15; v1+v2 nessuna,
          gemello senza giusto nella 74; e5-small la 2:92; e5-base la 74,
          la 2:69 e la 2:92. Con il riordinatore: la 2:73 su v0, la 2:85 su
          e5-small, con k=10 e k=15.
      - Risposte in più pezzi (19 fatti su 97): trovati in B senza
        riordinatore v0 6 con k=10 e 9 con k=15, e5-small 9 e 11, e5-base
        8 e 12; con il riordinatore su v0 10 e 11, su e5-small 11-12 e 13.
        Distanza tra i pezzi su v0: in 9 fatti stanno nello stesso
        frammento (89, 2:18, 2:30, 2:47, 2:54, 2:67, 2:71, 2:82, 2:114), in
        7 a 1-2 frammenti, in 3 a 5-7 frammenti (16, 30, 45; al più 3
        pagine, la 45).
      - Apistici (14 fatti di taratura), per allegato, trovati in B:

        | configurazione | A1 (2) | A3 (3) | A4 (4) | A5 (5) | tutti |
        |---|---|---|---|---|---|
        | v0, k=10 | 2 | 1 | 1 | 0 | 4 |
        | v0, k=15 | 2 | 1 | 2 | 0 | 5 |
        | e5-small, k=10 | 0 | 1 | 1 | 2 | 4 |
        | e5-small, k=15 | 0 | 2 | 2 | 2 | 6 |
        | e5-base, k=10 | 1 | 1 | 1 | 1 | 4 |
        | e5-base, k=15 | 2 | 2 | 2 | 2 | 8 |
        | v0 riordinato (osiria e mmarco), k=10 | 2 | 2 | 2 | 2 | 8 |
        | v0 riordinato (osiria e mmarco), k=15 | 2 | 2 | 2 | 3 | 9 |
        | e5-small, osiria, k=10 e k=15 | 2 | 3 | 2 | 1 | 8 |
        | e5-small, mmarco, k=10 | 2 | 3 | 1 | 1 | 7 |
        | e5-small, mmarco, k=15 | 2 | 3 | 2 | 1 | 8 |

        Le righe senza riordinatore vengono da
        `notte/parte2_curve_taratura.txt` (punto e), quelle con il
        riordinatore sono contate il 21/11/2026 dai CSV di
        `notte/riordino/`. Tutte le misure sono senza il nome dell'azione
        nel registro (punto 5).
      - Frammenti più corti, ampiezza 50, vicini a ±1 e ±2, peso in
        memoria, parole in comune: misure sui 40 fatti, nella lista qui
        sotto; le prime due non sono state rimisurate sui 97.

      **Stato delle strade al 20/11/2026 sera, sui primi 40 fatti**
      (superato dalla lista qui sopra, salvo dove questa lo richiama):
      - Frammenti più corti (v3, v1+v2+v3): **scartata**, scarto grande
        (B da 26 a 16, A da 16 a 10; per esempio la riga 63 in B scende
        dal 1° al 25° posto).
      - Ampiezza 50: **non adottata** (B 22 contro 26 su v0, 27 contro 28
        su v1).
      - Limite a 512 token (v1), intestazione nel vettore (v2) e la loro
        somma: **non dimostrate**, né in meglio né in peggio (B 28, 27 e
        25 contro 26). La base resta v0, la più semplice.
      - Vicini (frammenti a ±1 o ±2 nello stesso file): **accantonata**.
        Con ±1 nessuna risposta in più pezzi diventa intera; con ±2 una o
        due (la 23; la 29 in v0 B, la 89 in v1 B).
      - Nome dell'azione degli apistici: **adottato**, da scrivere nel
        registro in un compito a parte (punto 5).
      - k=15: **candidato**, scarto grande senza fatti persi (misura
        esatta su v0: B da 26 a 32, A da 16 a 23). Costo: circa il 50% di
        testo in più al modello, in media 5.566 caratteri per domanda in B
        e 5.698 in A.
      - Modelli e5 (e5-small ed e5-base, 512 token, prefissi "query: " e
        "passage: "): **non dimostrati** nei fatti trovati (B 24 e 28
        contro 26 con k=10; 31 e 34 contro 32 con k=15). Scarto grande
        invece sulla posizione del primo frammento giusto in B: tra i
        primi 5 in 17 fatti con v0, 22 con e5-small, 24 con e5-base; al
        1° posto in 7, 12 e 15. Con e5-base scatta la regola dei gemelli
        sulla riga 74 (azione B5): con k=10 il gemello è tra i primi 10 e
        il giusto no, con k=15 il pezzo è preso prima dal gemello, in A e
        in B; misura fatta senza il nome dell'azione. Nessuna decisione
        presa.
      - Peso in memoria (Windows, memoria del processo dopo il caricamento
        del solo modello; su Linux i valori assoluti cambiano): v0 1240
        MB, di cui 750 per il modello, 23,5 ms per domanda, 458 MB su
        disco; e5-small 1269 MB (+779), 24,7 ms, 470 MB; e5-base 1881 MB
        (+1391), 59,7 ms, 1082 MB. e5-small pesa quanto il modello di
        oggi; e5-base costa circa 640 MB in più, contro circa 690 MB di
        Streamlit Community Cloud, e porterebbe la colonna di Postgres da
        `vector(384)` a 768 dimensioni. Il recupero locale (modello,
        Chroma e BM25, su una copia) occupa 1304 MB. La memoria dell'app
        non si è misurata: avviarla apre Postgres o riscrive
        `chroma.sqlite3` del Chroma vero.
      - Parole in comune tra domanda ripulita e pezzo (v1, B; parole
        significative, prime 5 lettere come `_simili`): mediana 2 su 6
        nei 28 fatti trovati, 1 su 8 nei 12 non trovati; quattro non
        trovati non ne hanno nessuna (18, 29, 51, 58). Quasi tutto il
        lavoro lo fa la ricerca per significato: è il motivo della prova
        dei modelli e5.
      - Non provate: domande generate o contesto per frammento al
        caricamento, scheda per bando, riordinatore locale, glossario
        (punto 8); spazi spuri di pypdf sistemati al caricamento (riga
        51; 14 frasi su 81 del primo foglio trovate solo senza spazi).
        Esclusa dal vincolo del punto 8: scomporre la domanda in più
        ricerche, che costa una chiamata al modello a ogni domanda.
        Sconsigliata nel secondo giro, non decisa: l'intestazione nella
        ricerca per parole, uguale per tutti i candidati in B; ha senso
        solo per la parte degli apistici, che cambia da un allegato
        all'altro.
   5. **Nome dell'azione degli apistici** (decreto n. 14025 del
      18/06/2026). Fonte: il titolo a pagina 1 di ogni allegato, per
      esempio "Intervento B Azione B1: Lotta a parassiti e malattie".
      Valori per la colonna `parte` del registro, decisi il 20/11/2026 e
      scritti il 21/11/2026 (più sotto):
      - Allegato A1: "Azione B1: Lotta a parassiti e malattie";
      - Allegato A3: "Azione B3: Ripopolamento patrimonio apistico";
      - Allegato A4: "Azione B4: Razionalizzazione della transumanza";
      - Allegato A5: "Azione B5: Acquisto di attrezzature e sistemi di
        gestione".
      Prova sulle copie `v0+parte` e `v1+parte` (parte nel vettore e nella
      ricerca per parole, testo del frammento pulito), righe di taratura
      67, 71, 72 e 74: la 71 in B su v0 entra nei primi 10 (9° posto); la
      74 in B sale (dal 32° al 16° su v0, dal 39° al 12° su v1) senza
      entrare nei primi 10; la 72 resta oltre il 50°. Nessun pezzo preso
      dal gemello.
      **Scritti nel registro il 21/11/2026** (commit b2e3d42): colonna
      `parte` di `data/processed/documenti_bandi.csv`, i quattro valori qui
      sopra, ricavati dal titolo a pagina 1 di ogni allegato. Misura sui 97
      fatti di taratura, copia `v0+parte` (parte davanti al testo del
      vettore e della ricerca per parole dei soli allegati con il nome;
      fonte `dati-grezzi/prova/19d/v0+parte97/parte_taratura_97.txt`):
      - senza riordinatore, contro v0: B k=10 63 contro 60 (+3 −0, p =
        0,250), k=15 73 contro 71 (+2 −0, p = 0,500); A k=10 42 contro 42,
        k=15 52 contro 53; tutti entro il rumore;
      - con osiria, contro osiria su v0: B k=10 72 contro 72 (nessun fatto
        discordante), k=15 77 contro 78 (persa la 2:106, p = 1); A 58 e 62
        uguali; entro il rumore.
      Decisione del 21/11/2026: il nome dell'azione sta nel registro e non
      entra nel recupero (né nel vettore né nella ricerca per parole),
      perché con il riordinatore non dà guadagno. Eccezione: la riga BANDO
      del contesto per frammento, composta dal programma, riporta la parte
      (punto 13); per questo i 14 fatti degli apistici si riportano a parte
      in ogni tabella di quella misura. Riserva: se il riordinatore non
      fosse adottabile su Streamlit Community Cloud, il nome dell'azione
      nel recupero si rimisura senza riordinatore.
   6. **Scoperte sul sistema.**
      - `avvolgi` restringe la ricerca per 19 domande di taratura su 40:
        17 al documento giusto, 2 al giusto più il gemello (righe 55 e 63:
        decreti 13512 e 9506, i due bandi PMI, perché le parole della
        domanda stanno in entrambi i titoli). Le altre 21 non sono
        riconosciute: 9 senza parola del documento ("bando", "avviso"), 8
        con una sola parola del titolo (ne servono 2), 4 degli apistici
        senza nessuna ("chi alleva api" contro "aziende apistiche").
      - Chroma non è ripetibile: l'indice HNSW su disco del Chroma vero ha
        1015 vettori su 1187, e a ogni apertura Chroma riapplica in
        memoria le 819 operazioni rimaste in coda; su quattro passate
        della stessa misura una ha dato un fatto diverso (riga 31 in A,
        v1). Vale anche per l'app. Aprire una copia, anche in sola
        lettura, cambia `chroma.sqlite3`. La misura esatta (prodotto
        scalare su tutti i frammenti) è identica da un processo all'altro
        e su v0 dà gli stessi esiti e le stesse posizioni dell'indice di
        Chroma (0 fatti cambiano esito, con k=10 e con k=15).
      - In produzione, letto dal codice senza connettersi: la ricerca per
        significato è `embedding <=> … ORDER BY distanza LIMIT`
        (`src/pgstore.py`) e il README crea un indice HNSW, quindi è
        approssimata se l'indice è stato creato come scritto. Con
        l'indice, il filtro per documento (`metadata->>'fonte'`) si
        applica dopo la lettura dell'indice e può restituire meno
        frammenti di quelli chiesti. La ricerca per parole è il full-text
        italiano di Postgres (`to_tsquery`, `ts_rank_cd`), non BM25. Le
        misure su Chroma non valgono come misure della produzione.
      - Copertura dell'archivio (21/11/2026, sola lettura; fonte
        `dati-grezzi/prova/19d/archivio/rapporto_archivio_taratura.txt`,
        script accanto). Per ogni fatto di taratura, la frase contro i
        campi dell'archivio del suo bando (`bandi`, `beneficiari_bando`,
        `interventi_bando`, `scadenze_bando`, `testo_ricerca`); confronto
        meccanico su date intere, percentuali e numeri di almeno tre cifre,
        sulle parole per le frasi senza numeri. Su 97: 7 sì, 6 in parte, 7
        dubbi da guardare a mano, 77 no. Due dei 7 sì sono probabili
        coincidenze (righe 53 e 2:75: il solo numero in comune è il 651
        del regolamento 651/2014). Dei 25 fatti che osiria su v0 non trova
        in B con k=10, uno è sì (2:75, dubbio) e uno in parte (2:98).
        Campi vuoti su 113 bandi: `beneficiari_rimando` 113,
        `cumulabilita` 109, `premialita` 102, `costo_min` 95,
        `contributo_perc` 93, `contributo_min` 90, `dotazione` 67,
        `costo_max` 59, `contributo_max` 39; nessuna riga in
        `scadenze_bando` per 108 bandi, in `interventi_bando` per 55.
        L'app passa questi campi al modello solo se il router sceglie
        `dettaglio_bando` (`src/chains/router.py:62-66`, punto 7), e degli
        interventi passa genere e descrizione, non la frase
        (`src/database/interrogazioni_bandi.py`, `_dettaglio`);
        `testo_ricerca` non arriva al modello. Conseguenza per il passo 2b
        ("Pulizia dei dati"): le risposte di dettaglio sui bandi vengono
        dai frammenti, non dall'archivio; il 2b resta la correzione dei
        campi sbagliati elencati in quella sezione, non il loro
        riempimento per coprire le domande di dettaglio.
   7. **Conseguenza per il passo 19e** (nuovo, 20/11/2026: caricamento
      degli avvisi su Postgres). Comprende il filtro per `id_bando`
      nell'app: se una variante passa in B, gli avvisi vanno su Postgres
      solo insieme a quel filtro (decisione del 20/11/2026); oggi l'app
      non filtra per bando, e il filtro di Postgres è per file. Il
      recupero va rimisurato su Postgres con gli stessi fatti e la stessa
      divisione.
      Dove agganciare il filtro (letto dal codice il 21/11/2026, `src/`
      non toccato): quando la domanda nomina un bando il router sceglie
      `dettaglio_bando` (`src/chains/router.py:62-66`). In
      `src/chains/rag.py`, `prepara` (riga 377) esegue prima le
      interrogazioni (riga 381) e poi cerca i frammenti con `recupera`
      sulla domanda intera, senza filtro per bando (righe 385-386); oggi
      l'unico restringimento è `avvolgi` (riga 367,
      `src/recupero_documenti.py:272`), che lavora sui titoli dei
      documenti. Il filtro va tra i due passi: dall'id del bando trovato da
      `dettaglio_bando` (`trova_bandi`) al filtro dei frammenti.
      Idea per le domande ambigue (21/11/2026, da progettare nel 19e):
      l'app chiede quale bando. Un candidato: filtro su quel bando; due o
      tre: mostra i nomi e chiede; nessuno: cerca in tutto e lo dice; bando
      in più parti (gli allegati degli apistici): chiede la parte.
      Accanto (22/11/2026, da non fare ora): l'app chiede un chiarimento
      anche quando il bando è chiaro ma la domanda è vaga, invece di
      rispondere a caso. Serve un segnale calcolabile, per esempio il
      punteggio del riordinatore basso sul primo frammento, oppure i primi
      quasi alla pari su argomenti diversi. Si misura sulle domande a
      mano: quanto il segnale distingue i fatti trovati da quelli mancati.
      Fonte del filtro (22/11/2026, "Disegno dell'app (22/11/2026)"):
      quando chi usa l'app ha selezionato dei bandi, il filtro prende i
      bandi dalla selezione, al posto di "l'app indovina il bando"; le
      regole qui sopra restano per i casi senza selezione.
      Regola per il caricamento (22/11/2026, dal 19e in avanti): ogni
      bando nuovo entra con 6 domande scritte a mano da chi mantiene il
      progetto prima di aprire il PDF, ognuna con la frase esatta trovata
      a mano, il file e la pagina; si segnano anche i casi in cui nel
      bando la risposta non c'è. Materiale per il 19e dalla compilazione
      del secondo file di domande a mano: un criterio di punteggio letto
      come requisito di accesso (punto 13, voce 10, "Cambio del piano").
      Aggiunte del 22/11/2026 sera, dopo la lettura dei mancati (punto 13,
      voce 14):
      - **Frammenti vicini**: quando la ricerca sceglie un frammento, al
        modello vanno anche il precedente e il successivo. Misurato sul
        recupero nella notte del 20/11 (punto 4, "Frammenti vicini"; v0,
        B, k=10): da 60 trovati, a distanza 1 +13 fatti con 25.217
        caratteri in media contro 11.509, 2,2 volte. Da riprovare sulle
        risposte vere. Costo stimato in pianificazione, non misurato:
        circa un centesimo in più a domanda; nessun indice da rifare.
        Risolve quando il pezzo mancante è accanto, non quando è lontano.
        Con il taglio per struttura ("Taglio dei documenti secondo la
        struttura del bando (22/11/2026)") diventa "l'unità intera che
        contiene il pezzo". Da decidere insieme a "Documento intero quando
        il bando è noto" (Parcheggio), per il bando selezionato e corto.
      - **Scalini al momento della domanda**: risposta dai primi
        frammenti; se la ricerca è poco sicura, allarga ai vicini o a
        tutto il bando; se è ancora poco sicura, l'app chiede di
        precisare; se non trova, lo dice. Dipende da un segnale
        calcolabile, il punteggio del riordinatore, misurabile sulle 92
        domande a mano (è il segnale della voce "Accanto" qui sopra). No a
        due indici dello stesso archivio.
      - **Colonna "approfondimento"** nei fogli delle domande a mano, per
        le domande che vengono dopo la risposta: proposta, non creata.
      Blocco del 19e del 23/11/2026, dopo la lettura dei mancati del
      controllo (punto 13, voce 21); era nel passo 19 della roadmap, che
      ora ne tiene solo l'elenco dei rimedi. Gli scalini qui sopra
      diventano il segnale di scarsa fiducia e la scelta guidata.
      **19e** (ordine del 23/11/2026, dalla lettura dei mancati del
      controllo; prima versione, del 22/11: frammenti vicini e scalini al
      momento della domanda, `coda.md`, "Passo 19d", punto 7). Rimedi, in
      quest'ordine:
      1. frammenti vicini passati al modello (misurati sul recupero il
         20/11);
      2. segnale di scarsa fiducia: il sistema si accorge che i frammenti
         trovati c'entrano poco;
      3. secondo tentativo con altre parole (idea di chi mantiene il
         progetto, 23/11/2026). Quando il segnale di scarsa fiducia scatta,
         un modello piccolo riceve la domanda e gli argomenti del bando
         scelto e indica quali c'entrano, con le parole del bando; la
         ricerca si ripete con quelle parole, senza che l'utente veda
         niente. Quali righe dei contesti dare al modello piccolo è da
         decidere con una prova: ARGOMENTO è un elenco chiuso di 21 voci,
         probabilmente troppo generico; SERVE A e PAROLE hanno parole più
         vicine a quelle dell'utente. Costa solo nei casi dubbi, non a ogni
         domanda; niente da mantenere per bando; si toglie senza rifare
         l'archivio. Il verificatore e il "non lo trovo" restano invariati.
         Attacca i mancati per parole diverse. Tra i 28 mancati del
         controllo sono cinque (punto 13, voce 21, punto 5.3): 22 e 48 dei fogli e
         2:100 a mano non arrivano in nessun modo; 46 e 60 dei fogli
         arrivano già per altra via (altro passaggio; frammenti vicini). Da
         solo ne cura quindi tre: è una leva più piccola dei frammenti
         vicini. Da misurare su domande nuove: la metà di controllo è spesa;
      4. scelta guidata (idea di chi mantiene il progetto, 23/11/2026):
         quando il segnale scatta, l'app propone tre argomenti vicini presi
         dal bando (dalle righe ARGOMENTO e SERVE A dei contesti, senza
         chiamata al modello), con una spiegazione in parole semplici e
         l'uscita "nessuno di questi". Testo che non dà la colpa
         all'utente: "Non trovo un punto preciso su questo. Nel bando ci
         sono questi argomenti vicini: quale ti interessa?". Le domande
         mancate non erano poco chiare: il difetto è che il sistema non sa
         di aver sbagliato, per questo viene dopo il segnale;
      5. domande in parole semplici scritte al caricamento per ogni
         frammento, al posto della riscrittura della domanda a ogni
         richiesta (che costa per domanda e, senza conoscere il bando,
         indovina i termini).
      Altre voci del 19e:
      - verificare se il contesto penalizza le tabelle lunghe (casi 2:100
        e 64);
      - taglio per struttura, da decidere prima di allargare l'archivio,
        perché dopo ogni bando va ricaricato (`coda.md`, "Taglio dei
        documenti secondo la struttura del bando (22/11/2026)"); casi del
        23/11: 2:51, 59, 64, 2:100, 68;
      - per gli apistici l'app chiede quale azione (caso 70);
      - se la domanda non nomina l'azione e la regola è identica negli
        allegati, la risposta dice che vale per tutte le azioni (casi 68 e
        2:96, contestati);
      - due modifiche allo script di misura proposte da Claude Code il
        23/11: salvare nelle misure l'ordine dei primi 15 frammenti in B;
        elencare prima di misurare le righe compilate con la colonna
        "spiegata" vuota.
      In Parcheggio (`coda.md`): la domanda ripulita dal titolo del bando
      lascia un buco nella frase.
   8. **Strade da provare, nell'ordine** (superato dal perimetro del
      punto 10, 20/11/2026 sera: la strada 1 è fatta, punto 3; la 2 resta;
      la 3 è l'unica strada nuova, limitata al contesto per frammento; il
      riordinatore e k=15 della 5 sono misurati, punto 4; le strade 4, 6
      e 7 sono in "Parcheggio", in fondo a questo file; dal 22/11/2026 la
      strada 4 è un passo a sé, "Disegno dell'app (22/11/2026)"):
      1. rimisura sui 97 fatti di taratura;
      2. nome dell'azione degli apistici nel registro;
      3. contesto per frammento scritto dal modello al caricamento
         (Contextual Retrieval) o domande generate per frammento;
      4. scheda per bando;
      5. riordinatore locale dei primi 30-50, o k=15;
      6. glossario;
      7. addestrare il modello di embedding piccolo sui testi dei bandi,
         in locale, con le coppie domanda e frammento generate al
         caricamento: le stesse della strada 3, una spesa sola per due
         usi. Condizioni:
         - viene dopo aver provato quelle coppie come aiuto alla ricerca;
         - si addestra su una parte dei bandi e si misura su bandi interi
           tenuti fuori, altrimenti il modello impara i documenti a
           memoria e la misura è falsata;
         - i documenti gemelli si gestiscono con il registro: una frase
           identica in un altro allegato non è un esempio sbagliato;
         - va deciso dove pubblicare e mantenere il modello addestrato,
           che non può stare nel repository.
      Vincolo: nessun costo fisso a ogni domanda dell'utente; le chiamate
      al modello sono ammesse solo al caricamento. Più strade insieme: nel
      trovare i risultati si uniscono, il dato lo decide il verificatore
      sul testo; un punteggio di affidabilità solo quando sarà tarabile.
      Limiti già visti: con k fisso le strade si dividono gli stessi
      posti; per sapere quale contribuisce se ne toglie una alla volta;
      il verificatore controlla che un dato citato sia giusto, non che un
      elenco sia completo.
   9. **Avvertenze.** Le domande dei due fogli le ha scritte un modello:
      per le tecniche in cui un modello scrive testo di ricerca (domande
      generate, contesto per frammento) la misura può gonfiarsi per
      somiglianza, e serve un riscontro su una trentina di domande
      scritte a mano. Per costruzione sono favoriti anche la scheda per
      bando, le cui otto voci sono le categorie del foglio, e un glossario
      scritto dopo aver visto i fatti di taratura. Limite della misura:
      per la riga 58 lo stesso termine sta anche al par. 5.2.2, quindi una
      risposta giusta può esistere anche se il fatto risulta mancato.
   10. **Perimetro di chiusura del 19d** (concordato il 20/11/2026 sera).
       Quattro mosse, e non altre:
       1. scelta della configurazione, sulla taratura;
       2. nome dell'azione degli apistici nel registro (punto 5);
       3. una sola strada nuova: il contesto per frammento (conteggi al
          punto 11, lavoro e regole al punto 13);
       4. apertura del controllo, una volta, con il via esplicito; il
          numero che esce si scrive anche se è sotto l'85%.
       Se resta sotto la soglia, gli avvisi entrano in produzione solo con
       il filtro per bando (punto 7, passo 19e), e i casi difficili restano
       in coda. Le altre idee vanno in "Parcheggio", in fondo a questo
       file.
   11. **Conteggi per il documento intero e per il contesto per
       frammento** (fonte `notte/parte2_curve_taratura.txt`, punti c e d).
       Token contati con il tokenizzatore di
       `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
       (sentencepiece di XLM-RoBERTa), senza i token speciali: è il più
       vicino disponibile in locale senza chiamare il modello di
       linguaggio, e i token del modello di linguaggio possono differire.
       Testo pulito come prima della divisione in frammenti (premesse
       tolte, `pulisci_avviso`, pulizia prudente, pagine d'indice e troppo
       corte saltate); ogni frammento compare tale e quale nel testo
       pulito del suo file.

       | file | token del documento | frammenti | token dei frammenti |
       |---|---|---|---|
       | proroga Cultura Missione Comune (f6c3e017) | 464 | 2 | 514 |
       | proroga Sport Missione Comune (f672a3f8) | 529 | 2 | 529 |
       | avviso Cultura Missione Comune (130702f4) | 11.672 | 48 | 11.968 |
       | avviso Sport Missione Comune (8041f3d1) | 11.217 | 45 | 11.462 |
       | avviso prot. 26286 del 03/11/2026, fondo strade (74a82f09) | 983 | 5 | 1.068 |
       | DM 20/03/2025 n. 75, rievocazioni (32d5ca6d) | 3.292 | 15 | 3.418 |
       | decreto 13512, allegato 1 (6cbea075) | 32.969 | 126 | 36.063 |
       | decreto 14025, allegato A1 (e268ff8c) | 8.665 | 39 | 9.119 |
       | decreto 14025, allegato A3 (bd90bf80) | 8.877 | 40 | 9.384 |
       | decreto 14025, allegato A4 (764c40fe) | 9.225 | 45 | 9.944 |
       | decreto 14025, allegato A5 (955dbd58) | 9.087 | 41 | 9.589 |
       | decreto 18191, allegato A (adcdddd6) | 4.436 | 17 | 4.614 |
       | decreto 22706, allegato A (67198f2e) | 18.953 | 79 | 19.712 |
       | decreto 24161, allegato A (e42abdab) | 5.166 | 24 | 5.324 |
       | decreto 25205, allegato A (fc71cd53) | 15.441 | 61 | 17.107 |
       | decreto 9506, allegato 1 (9de93696) | 32.038 | 125 | 34.972 |
       | testo coordinato SRA ACA 16b (8ac2656c) | 37.352 | 157 | 39.979 |
       | totale, 17 file (912.384 caratteri) | 210.366 | 871 | 224.766 |

       Per bando, i suoi file insieme (per la strada del documento intero
       quando il bando è noto, in "Parcheggio"):

       | bando | file | token |
       |---|---|---|
       | bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-7057d9 | 1 | 32.969 |
       | bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-8cd3ac | 1 | 32.038 |
       | contributi-a-enti-locali-e-ets-per-punti-digitale-fac-8db4be | 1 | 15.441 |
       | contributi-agli-enti-locali-per-lo-sviluppo-di-proget-01bfe9 | 1 | 18.953 |
       | contributi-per-uso-e-gestione-sostenibile-delle-risor-9d883c | 1 | 37.352 |
       | cultura-missione-comune-2026 | 2 | 12.136 |
       | fondo-rievocazione-storica-2027 | 1 | 3.292 |
       | fondo-strade-piccoli-comuni-2026 | 1 | 983 |
       | parcheggi-2026 | 1 | 4.436 |
       | sostegno-a-progetti-di-promozione-ed-educazione-music-e81761 | 1 | 5.166 |
       | sostegno-agli-investimenti-strutturali-aziende-apisti-401650 | 4 | 35.854 |
       | sport-missione-comune-2026 | 2 | 11.746 |

       Per confronto, in B su v0 con k=10 il testo dei frammenti passati
       al modello è in media di 11.509 caratteri per fatto (punto 3).

       Contesto per frammento, una chiamata per frammento che rilegge il
       suo documento dalla cache; ipotesi: 60 token di istruzione e 100
       di uscita per frammento. Totali in token, per i 17 file:
       - scrittura in cache (ogni documento una volta): 210.366;
       - lettura dalla cache (ogni frammento rilegge il suo documento):
         19.263.701; senza la prima chiamata di ogni file, 19.053.335;
       - ingresso non in cache (frammento più istruzione): 277.026;
       - uscita: 87.100.
   12. **Controllo dei download dei riordinatori** (notte del 20/11/2026).
       La regola era: non scaricare un modello che chiede un accesso,
       l'accettazione di una licenza o l'esecuzione di codice del modello.
       Nessuno dei due ha accesso riservato o licenza da accettare. Il
       repository di mmarco contiene uno script di addestramento
       (`train_script.py`), che il primo controllo automatico ha
       rifiutato. È stato giudicato non codice che il modello chiede di
       eseguire: la configurazione non ha `auto_map`, il modello si carica
       con `trust_remote_code=False`, e lo script non si scarica. Il
       controllo è stato ristretto agli script Python di primo livello
       che non sono di addestramento (`codice_del_modello` nello script di
       misura, con un test), e mmarco è stato scaricato senza onnx,
       openvino, `pytorch_model.bin` e lo script. Decisione rivista e
       accettata da chi mantiene il progetto il 21/11/2026. I modelli
       stanno nella cache di Hugging Face, fuori dal repository.
   13. **Terza mossa: contesto per frammento** (21/11/2026; perimetro,
       punto 10, voce 3). Per ogni frammento degli avvisi un modello
       (claude-haiku-5-5) riceve il documento intero, in cache, e il
       frammento, e scrive alcune righe che lo collocano nel documento.
       Servono solo alla ricerca: il testo del frammento, che si cita e
       che il verificatore controlla, resta pulito e separato. Script in
       `docs/fatto.md` (21/11/2026); file in
       `dati-grezzi/prova/19d/contesto/`.
       1. **Prima generazione** (impronta delle istruzioni e3ef7c9ca5ad):
          871 frammenti, spesa stimata 0,5708 dollari, 81 contesti troncati
          dal limite di 300 token in uscita. Archiviata in
          `contesti_v1.jsonl` e non si misura: 258 contesti su 871 (29,6%)
          con violazioni su numeri o gemello, 408 (46,8%) con almeno una
          violazione (`passo1_controlli_v1.txt`, `controllo_contesti_v1.txt`).
          Cause, classificate dopo il controllo senza cambiarlo: numeri
          presenti nel documento ma non nel frammento (199 occorrenze, tra
          cui il "50.000,00" del bando 13512 in 40 frammenti), numeri di
          paragrafo senza "par." (23), nessun numero assente dal
          documento; per il gemello, la riga BANDO degli apistici che copia
          la lista "azioni B1–B3–B4–B5" del titolo (113 frammenti) e
          "commissioni di garanzia" nel 9506 (44), un segno scelto a mano
          che compare nel testo del 9506 stesso.
       2. **Revisione**, l'unica prevista, nata dai controlli e non dai
          risultati di ricerca, che non sono stati calcolati
          (`revisione_21-11.txt`):
          - la riga BANDO la compone il codice dal registro: titolo, atto e
            parte (per gli apistici la sola azione del file, senza la
            lista del titolo); uguale per tutti i frammenti di un file;
          - il modello scrive DOVE (articolo, paragrafo o sezione, con i
            soli numeri di struttura), ARGOMENTO (da una a tre voci di un
            elenco chiuso), SERVE A (una frase con le parole di un
            ufficio o di un'impresa) e PAROLE (da 5 a 10 parole o brevi
            espressioni di ricerca, senza numeri né nome del bando);
          - elenco di ARGOMENTO allargato da 10 a 21 voci: le 11 nuove
            coprono 378 delle 570 descrizioni libere finite in "altro"
            nella prima generazione, 135 erano già voci dell'elenco, 57
            restano "altro";
          - in ARGOMENTO, SERVE A e PAROLE solo numeri, date e parole di
            numero del frammento, anche il numero dell'atto; nella riga
            DOVE solo riferimenti di struttura del documento;
          - limite in uscita a 600 token, un contesto troncato si rifà una
            volta; segni del gemello verificati sul proprio documento, più
            fino a 3 segni automatici per coppia;
          - impronta delle istruzioni a758adc6d26c.
       3. **Prova sull'allegato A3** degli apistici (40 frammenti, 0,0153
          dollari; `diagnosi_prova_a3.txt`). Il rapporto della prova dava 12
          frammenti con violazioni su 40, perché nella prova i gemelli non
          venivano caricati; con i gemelli, 15 su 40. Tutti difetti di
          forma o falsi allarmi, nessun numero inventato: 6 nella riga DOVE
          (paragrafi veri, "1.1," o "2.", che il controllo non
          riconosceva), 7 in ARGOMENTO (voci fuori dall'elenco), 4 sul
          gemello (il segno automatico "attrezzatura", mentre l'A3 dice
          "attrezzature"). Dopo quattro correzioni del codice (controllo
          DOVE allargato, ARGOMENTO normalizzato dal codice con un elenco di
          forme vicine scritto a mano, gemelli caricati nella prova, radice
          di 6 lettere nei segni automatici): 0 su 40, impronta invariata.
          Avvertenza: quello zero è ottenuto sugli stessi 40 frammenti
          usati per correggere i controlli, quindi non vale come verifica.
       4. **Generazione completa** (21/11/2026): 871 chiamate, 871
          frammenti salvati, spesa stimata 0,5675 dollari, 1510 secondi
          (dal terminale di chi mantiene il progetto; nel file, 1508
          secondi tra il primo e l'ultimo salvataggio), impronta
          a758adc6d26c, nessun contesto troncato. File `contesti.jsonl`.
          Controlli e misura sugli 871 non ancora fatti.
       5. **Regole decise prima di guardare i controlli sugli 871**
          (21/11/2026):
          - condizione di arresto: violazioni vere sopra il 5% dei
            frammenti;
          - niente altra revisione del prompt: i falsi allarmi si
            correggono nel codice;
          - i contesti con violazioni vere si scartano sempre, e quei
            frammenti entrano nella misura senza contesto;
          - le violazioni da segno automatico del gemello si contano a
            parte e si leggono una per una; la soglia dei segni resta a 3
            occorrenze; un segno si toglie solo se tutti i suoi casi sono
            usi generici;
          - l'elenco delle forme vicine di ARGOMENTO resta congelato fino a
            fine misura;
          - una configurazione non si adotta se guadagna con le domande dei
            fogli ma non con le domande scritte a mano.
          Regole già in vigore: si adotta solo se guadagna in B sia con
          k=10 sia con k=15 contro c-0 (più guadagnati che persi, p ≤ 0,05);
          sulle 30 domande scritte a mano (`domande_a_mano.csv`) il guadagno
          netto in B "resta" se è positivo e almeno metà di quello con le
          domande del foglio sugli stessi fatti.
       6. **Prossimo compito**, nell'ordine (superato dalla voce 17,
          22/11/2026, e dalle voci 19 e 20, 23/11/2026):
          1. i controlli sugli 871 contesti della generazione completa
             (`genera_contesti --controlla`);
          2. se le violazioni vere su numeri o gemello restano entro il 5%,
             la misura sulla taratura: c-0 (deve ridare osiria su v0 della
             notte, riga per riga), c-R, c-L, c-LR, c-LVR; righe tolte una
             alla volta; domande a mano; etichetta di ARGOMENTO contro il
             tipo del fatto;
          3. revisione esterna del metodo prima di aprire la metà di
             controllo;
          4. apertura del controllo una sola volta, con il via esplicito;
          5. il numero che esce si scrive anche se è sotto l'85%.
       7. **Controlli sugli 871 contesti** (21/11/2026; numeri da
          `dati-grezzi/prova/19d/contesto/misura_21-11.txt`, passo 1).
          Partenza: 51 violazioni vere su 871 (5,9%), sopra la soglia di 43;
          la misura non partiva. Lette a mano, le 51 erano: 16 falsi allarmi
          del controllo (A), 26 riferimenti normativi o numero dell'atto
          nella riga DOVE (B), 5 dati del documento che il frammento non ha
          (C), 2 riferimenti di struttura assenti dal documento (D), 2 segni
          del gemello scelti a mano, "bancari" (E). Un segno automatico
          tolto dopo la lettura ("normativa antimafia", 1 caso, uso
          generico). Correzioni del controllo decise dopo aver visto le
          violazioni, prompt e impronte invariati (a758adc6d26c, d883256b1359):
          nella riga DOVE i paragrafi a tre livelli e gli intervalli non
          sono date se ogni paragrafo apre una riga del documento; un
          riferimento vale se apre una riga del documento o se sta nel
          frammento. Effetto: 15 frammenti in meno, gli stessi 15 della
          classe A tranne "cento per cento" (22706 #54), che resta. Numero
          finale: 36 violazioni vere su 871 (4,1%), tutte di contenuto, e i
          36 contesti si scartano; 1 di sola forma resta. Il 5,9% di
          partenza resta il dato del controllo deciso prima.
       8. **Esito della misura sulla taratura** (21/11/2026; 97 fatti,
          ricerca esatta, osiria su 30 candidati; 835 frammenti con
          contesto, 36 senza; numeri da `misura_21-11.txt`, passi 2-4, e
          `rapporto_contesto_taratura.txt`). c-0 ridà osiria su v0 della
          notte riga per riga, a k=10 e a k=15.
          - Fatti trovati su 97, A / B, e in B guadagnati/persi contro c-0
            con p:
            - c-0: k=10 58 / 72; k=15 62 / 78;
            - c-R: k=10 64 / 79 (+8/-1, p 0,039); k=15 65 / 80 (+3/-1,
              p 0,625);
            - c-L: k=10 66 / 75 (+4/-1, p 0,375); k=15 71 / 81 (+5/-2,
              p 0,453);
            - c-LR: k=10 76 / 83 (+14/-3, p 0,013); k=15 77 / 85 (+9/-2,
              p 0,065);
            - c-LVR: k=10 69 / 80 (+14/-6, p 0,115); k=15 69 / 80 (+10/-8,
              p 0,815).
          - Nessuna delle cinque soddisfa la regola di adozione. c-LR, la
            migliore in B, la manca a k=15 (p 0,065).
          - Righe tolte una alla volta su c-LR, in B, k=10 / k=15:
            senza-bando 76 / 82; senza-dove 85 / 87 (p 0,001 / 0,004);
            senza-argomento 83 / 85 (p 0,007 / 0,039); senza-serve-a
            78 / 83; senza-parole 81 / 85 (p 0,035 / 0,039). senza-dove,
            senza-argomento e senza-parole passano la regola, ma sono
            state scelte dopo aver visto i risultati, fra sei varianti: non
            si adottano.
          - Domande a mano: 29 su 30 (la riga 93 del foglio 2 ha la
            domanda vuota, tolta da una copia del file). In B, contro c-0
            (22 a k=10 e a k=15): c-R +2/-0, c-L +1/-0, c-LR +2/-0, c-LVR
            +2/-2 (netto 0, veto), uguali a k=10 e a k=15; nessun p sotto
            0,05.
          - Etichetta ARGOMENTO del primo frammento giusto contro il tipo
            del fatto: coincide 69 su 97; dei 28 che non coincidono, 10
            hanno solo "altro"; la confusione più frequente è procedura ->
            rendicontazione e pagamento (4).
          - Tempo per domanda con il riordinatore, in B: c-0 5,0 secondi,
            c-LR 5,9; coppie oltre 512 token in A: c-LR 702 su 2909.
          Cosa i numeri non dicono (dal rapporto in chat del 21/11/2026,
          ricopiato dalla trascrizione della sessione):
          - **La misura che soddisfa la regola è stata scelta dopo.** c-LR senza-dove soddisfa la regola, ma l'ho trovata tra sei varianti misurate dopo aver visto i risultati. È un caso di confronti multipli, e quei p non hanno il peso di una misura decisa prima.
            - Il guadagno sopra c-LR completo è di 2 fatti, cioè 52 e 74 a k=10 e 74 e 2:114 a k=15. È troppo poco per dire che DOVE danneggia.
            - Una ragione possibile è che DOVE allunga le coppie oltre il limite di 512 token: togliendolo le coppie oltre il limite scendono da 702 a 332. Non l'ho verificato.
          - **Le domande a mano sono troppo poche per misurare.** Su 29 domande i netti sono di +1 o +2, e servono solo da veto. Il veto non vale per le righe tolte, che non sono state misurate a mano.
          - **Il guadagno potrebbe venire da somiglianze di testo.** Nella sezione 5 del rapporto, per 12 dei 14 fatti guadagnati da c-LR a k=10 le parole della domanda trovano corrispondenza solo nel contesto, soprattutto nelle righe BANDO e SERVE A. Domande e contesti li ha scritti un modello: parte del guadagno può essere somiglianza di stile tra i due e non un recupero vero.
          - **I 97 fatti sono quelli su cui il controllo è stato tarato.** La metà di controllo non è stata letta.
          - **Il dato sul gemello conta fatti, non frammenti.** Misura i fatti in cui il gemello arriva prima del giusto, non quanti frammenti del gemello entrano tra i primi k.
          - **Due imprecisioni nel codice, non corrette.** Nel rapporto la sezione 6 porta ancora il titolo fisso "30 fatti". Al passo 4, `VOCE_DEL_TIPO` assegna "definizione" alla voce "altro", quindi il fatto 2:46, etichettato "definizioni", conta come non coincidente.
          - **Una soluzione forse migliore, non provata.** Il riordinatore taglia una coppia su quattro, quindi il contesto aggiunto sottrae spazio al testo del frammento. Si potrebbe dare al riordinatore solo BANDO e SERVE A, cioè le due righe senza le quali si perdono più fatti. In alternativa, si potrebbe mettere il contesto dopo il testo e lasciarlo tagliare, invece di metterlo davanti.
          Note al testo ricopiato (21/11/2026): "i netti sono di +1 o +2"
          vale per c-R, c-L e c-LR; c-LVR ha netto 0. "Il controllo è stato
          tarato" vuol dire che sui 97 fatti di taratura sono state scelte
          le configurazioni e le correzioni, non i controlli dei contesti,
          che sono stati corretti sugli 871 contesti.
       9. **Decisioni** (21/11/2026, dopo la misura):
          - niente adottato;
          - c-LVR chiusa;
          - prima di decidere, altre 30 domande a mano
            (`domande_a_mano_2.csv`, fatti di taratura non già nel primo
            file). Regola fissata prima di vedere il risultato: un netto da
            -1 a +2 su 29 non decide;
          - la regola di conferma sulla metà di controllo si scrive dopo la
            revisione esterna e prima dell'apertura.
      10. **Piano delle domande a mano** (deciso il 21/11/2026 sera):
          - chi mantiene il progetto scrive una domanda a mano per tutti i
            fatti dei due fogli, circa 190, in blocchi da 30-35;
          - prima la taratura (primo file già fatto, 29 domande; poi il
            secondo e il terzo), poi misura di c-0 e c-LR soltanto;
          - poi revisione esterna, configurazione candidata e regola di
            conferma scritte e committate;
          - solo dopo si scrivono le domande sui fatti di controllo, e la
            metà di controllo si apre una volta sola, con le domande dei
            fogli e con quelle a mano;
          - nessun modello scrive o riscrive una domanda. Si può spiegare
            cosa dice una frase; le righe spiegate si segnano nella colonna
            "spiegata" e si misurano anche a parte;
          - la regola per leggere il risultato sulle domande a mano di
            taratura si scrive prima di misurare: non è ancora scritta.
            (Scritta il 22/11/2026, prima della misura: "Regola di
            lettura decisa", in fondo a questa voce.)

          File della taratura (22/11/2026, in
          `dati-grezzi/prova/19d/contesto/`): `domande_a_mano.csv` 30
          fatti, 29 domande (la riga 93 del foglio 2 è vuota);
          `domande_a_mano_2` 30 fatti e `domande_a_mano_3` 33 fatti (tutti
          i rimanenti), in .csv e in copia .xlsx, con file, pagina, testo
          prima e dopo la frase presi dal testo pulito e la colonna
          "spiegata", domande vuote. In tutto 93 fatti: i 4 del fondo
          strade restano fuori, perché i suoi contesti si sono visti nella
          prova della generazione (il file della prova è l'avviso del fondo
          strade). Questo piano supera le "altre 30 domande a mano" della
          voce 9; la regola fissata lì ("un netto da -1 a +2 su 29 non
          decide") era per il secondo blocco da solo.

          **Cambio del piano** (22/11/2026, prima di qualunque misura sulle
          domande a mano del secondo e del terzo file). Superano il primo
          punto dell'elenco qui sopra ("una domanda a mano per tutti i
          fatti dei due fogli, circa 190") e, per il controllo, il quarto
          ("solo dopo si scrivono le domande sui fatti di controllo");
          gli altri punti restano.
          - Taratura: i tre file, 92 domande in tutto (29 + 30 + 33). Il
            secondo è compilato (`domande_a_mano_2.xlsx`, 30 domande; 3
            righe segnate nella colonna "spiegata", scritte "si" senza
            accento: quando la misura leggerà la colonna, "si" e "sì"
            valgono uguale). Il terzo è stato rigenerato vuoto il
            22/11/2026 con due correzioni al testo intorno alla frase:
            le celle di una riga di tabella si cercano nel tratto più
            corto in cui stanno tutte (prima la prima cella si agganciava
            alla sua prima occorrenza: foglio 2 riga 80, "Media impresa"
            preso dal punto 4.2.11 invece che dalla tabella di p. 13); un
            fatto a più pezzi ha nella colonna testo_prima ogni pezzo di
            seguito con il suo prima e il suo dopo, e in testo_dopo solo
            una nota che lo dice. Il secondo file è stato compilato con la
            forma di prima.
          - Controllo: non una domanda a mano per ogni fatto, ma circa 50,
            cinque per bando, scelte con un seme fisso dopo che
            configurazione candidata e regola di conferma sono committate.
          - Motivo: le domande sullo stesso documento non sono
            indipendenti; dieci bandi valgono come dieci prove più che
            come cento. Molte domande sugli stessi bandi servono a
            confrontare due configurazioni, non a dire se l'app regge su
            un bando nuovo.
          - Regola nuova per il caricamento, dal 19e in avanti: scritta al
            punto 7 qui sopra.
          - Osservazione dalla compilazione del secondo file: in 3 domande
            su 30 un criterio di punteggio è stato letto come requisito di
            accesso ("posso accedere?" dove la risposta è "dà punti"). È un
            errore che farà anche chi usa l'app: materiale per il 19e.
          - **Proposta** di regola per leggere il risultato sulla
            taratura, da confermare prima della misura (non ancora
            confermata): prova principale sulle domande nuove, cioè il
            secondo e il terzo file, 63 domande; confermata se in B a k=10
            i presi superano i persi con p ≤ 0,05 e a k=15 non peggiora;
            bocciata se a k=10 i presi non superano i persi; in mezzo,
            candidata debole, e decide il controllo. Le righe "spiegata"
            si leggono anche a parte. Le 92 insieme sono un dato
            secondario. (Superata dalla regola qui sotto, 22/11/2026.)
          - **Regola di lettura decisa** (22/11/2026, prima della misura
            sulle domande a mano del secondo e del terzo file; non più una
            proposta). Verifica dei file prima della misura: 29, 30 e 33
            domande compilate, 92 in tutto; righe segnate nella colonna
            "spiegata" 0, 3 e 5, tutte scritte "si".
            - Prova principale: le 63 domande nuove (secondo e terzo
              file), condizione B, c-LR con tutte le righe contro c-0.
            - Confermata: a k=10 i presi superano i persi con p ≤ 0,05 al
              test dei segni, e a k=15 il netto è ≥ 0.
            - Bocciata: a k=10 i presi non superano i persi.
            - In mezzo: candidata debole, decide la metà di controllo.
            - Dati secondari, da riportare e non da usare per decidere: le
              92 insieme; le righe spiegate e le non spiegate separate; la
              condizione A; il primo file da solo.
            - Nota: le righe di tabella e a più pezzi del secondo file sono
              state compilate con il contesto poco chiaro (la forma di
              prima, vedi sopra).
            Nel rapporto (`--rapporto-contesto`, sezione 6): "si" e "sì"
            valgono uguale nella colonna "spiegata"; prova principale,
            domande che né c-0 né c-LR trovano, dati secondari con presi,
            persi, netto e p; una configurazione misurata su domande
            diverse da quelle di c-0 (le 29 di ieri) si salta.
      11. **Esito della misura delle domande a mano** (22/11/2026; numeri
          da `dati-grezzi/prova/19d/contesto/misura_mano_22-11.txt`). c-0 e
          c-LR con tutte le righe, 92 domande a mano dei tre file (29 + 30
          + 33), A e B, k=10 e k=15. Le 29 del primo file ridanno riga per
          riga le misure del 21/11 (`misure_mano_29`).
          - Prova principale, 63 domande nuove, B, c-LR contro c-0: k=10
            54 contro 51, presi 5, persi 2, netto +3, p 0,453; k=15 56
            contro 53, presi 4, persi 1, netto +3, p 0,375. Secondo la
            regola della voce 10: **candidata debole**, decide la metà di
            controllo.
          - Con le domande dei fogli il netto di c-LR in B a k=10 era +11
            su 97 (+14/-3, voce 8); con le 63 nuove a mano è +3: parte del
            guadagno dei fogli era somiglianza tra testi scritti da modelli
            (domande dei fogli e contesti). In A il guadagno resta forte
            anche a mano: +17 su 63 a k=10, nessun perso; +18 su 92.
          - Totali sulle 92: c-0 A 51 e 59, B 73 e 75 (k=10 e k=15); c-LR A
            69 e 74, B 78 e 80.
          Cosa i numeri non dicono (da `misura_mano_22-11.txt`, ricopiato
          dal file):
          - Il test ha poca forza. Sulle 63 in B le coppie discordanti sono 7 a k=10:
            con 7 coppie la regola conferma solo con 7 presi e 0 persi (p 0,016);
            6 a 1 dà p 0,125. Con c-0 che in B trova già 51 su 63, lo spazio per
            guadagnare è di 12 domande. "Candidata debole" qui vuol dire anche "la
            prova non poteva distinguere un guadagno piccolo".
          - Le 63 domande non sono indipendenti: stanno su 9 bandi (14 sui due PMI, 10
            sugli apistici). Il test dei segni le tratta come indipendenti.
          - In A (percorso dell'app senza restringere al bando) c-LR guadagna molto
            di più: +17 su 63 a k=10, nessun perso. La regola decide su B, e A è un
            dato secondario; il guadagno in A non dice niente su B.
          - Il guadagno in B è piccolo in ogni parte: spiegate +2 e +1, terzo file +2 e
            +2, secondo file +1 e +1 (k=10 e k=15). Tra
            le 55 non spiegate il netto è +1 a k=10 e +2 a k=15. Le spiegate sono 8:
            troppo poche per leggerle.
          - Il secondo file è stato compilato con il contesto delle frasi nella forma
            di prima (tabelle e fatti a più pezzi poco chiari): non è separabile
            dall'effetto del file.
          - La regola del 21/11 (voce 5), su tutte le 92: a k=10 "si riduce" (foglio
            +11, a mano +5), a k=15 "resta" (+7 e +5). Dato secondario.
          - Tetto in B: c-LR ha il giusto tra i 30 candidati in 83 casi su 92 e lo
            trova nei primi 15 in 80. Delle 11 domande che nessuna delle due trova a
            k=15, almeno 8 non sono tra i 30 candidati di c-LR (9 fuori dai
            candidati, 12 mancati a k=15; non contato riga per riga): il limite è la ricerca
            prima del riordinatore, non il riordinatore. Sono concentrate: 4
            apistici, 3 Missione Comune (Cultura 18, Sport 29 e 30), 2 sviluppo
            progetti (01bfe9, 2:39 e 2:43), 1 Punti Digitale, 1 PMI.
          - Le domande a elenco ("cosa posso comprare?") contano trovate solo se
            compare il passaggio del fatto: alcuni mancati possono avere una
            risposta giusta in un altro passaggio. Non verificato riga per riga.
          - c-LR supera i 512 token in 648 coppie su B: il contesto toglie testo al
            frammento nel riordinatore. Il peso di questo non è misurato.
          Nota al testo ricopiato (22/11/2026, dalla lettura dei mancati,
          `mancati_mano_22-11.txt`): contati riga per riga, gli 11 sono 8
          con almeno un pezzo fuori dai 30 candidati di c-LR (29, 2:24,
          2:39, 2:75, 2:95, 2:99, 2:106, 2:107) e 3 con tutti i pezzi tra i
          candidati e un pezzo oltre il 15° posto dopo il riordino (18, 30,
          2:43). "Il limite è la ricerca prima del riordinatore" vale per
          gli 8.
      12. **Decisione del 22/11/2026, presa dopo aver visto i risultati
          della voce 11** (e quindi scritta come tale): una sola
          configurazione in più si misura sulla taratura. Motivi: con la
          selezione come filtro (disegno dell'app) la condizione che conta
          è B; dopo l'apertura del controllo non si può più scegliere.
          - **T-0**: bando noto, tutti i frammenti del bando al
            riordinatore, senza ricerca prima e senza contesto.
          - **T-R**: come T-0, con il contesto (tutte le righe) nel testo
            dato al riordinatore.
          Regola, scritta prima della misura. Una T si adotta come
          candidata per il controllo solo se, contro c-0 in B:
          - sulle 92 domande a mano, a k=10, i presi superano i persi con
            p ≤ 0,05, e a k=15 il netto è ≥ 0;
          - sulle 97 domande dei fogli il netto è ≥ 0 a k=10 e a k=15;
          - nessun pezzo preso dal gemello in più rispetto a c-0;
          - tempo per domanda: mediana non oltre il doppio di c-0 e massimo
            non oltre 30 secondi. Se passa tutto tranne il tempo, si scrive
            "adottabile solo se si risolve il tempo" e non va al controllo.
          Se passano tutte e due, va la migliore a k=10 sulle domande a
          mano; a parità T-0, che non dipende dai contesti. Se non passa
          nessuna, al controllo va c-LR come candidata debole.
          Nel codice (`misura_recupero_avvisi.py`, `--contesto T-0` o
          `--contesto T-R`, poi `--rapporto-T`): la condizione A delle T è
          quella di c-0 (T-0) e di c-R (T-R), perché il bando noto cambia
          solo B. Il tempo è quello del riordinatore per domanda, come per
          c-0 (la ricerca prima non è contata, e nelle T non c'è). "Pezzo
          dal gemello": fatti con `B_pezzo_dal_gemello`, contati sulle 97 e
          sulle 92, a k=10 e a k=15. Di c-0 la misura salvata ha solo la
          mediana del tempo, non il massimo, che la regola chiede solo alle
          T.
      13. **Esito della misura delle T** (22/11/2026 sera; numeri da
          `dati-grezzi/prova/19d/contesto/misura_T_22-11.txt`, che
          contiene parola per parola `rapporto_T_taratura.txt`). T-0 e T-R
          in B, k=10 e k=15, sulle 97 domande dei fogli e sulle 92 a mano;
          `misura_recupero_avvisi.py` invariato durante la misura (sha256
          uguale prima e dopo). Secondo la regola della voce 12, scritta
          prima della misura, punto per punto:
          - T-0: 1 no (a mano, k=10, presi 6, persi 1, p 0,125; k=15 netto
            +3); 2 sì (fogli, netto +5 a k=10 e +6 a k=15); 3 no (fogli,
            k=10, fatti con un pezzo dal gemello prima del giusto: c-0 0,
            T-0 1); 4 no (mediana 11,248 s sui fogli e 11,435 s a mano,
            contro i limiti 10,584 e 10,214; massimo 27,114 e 24,130 s,
            sotto i 30). **Non adottabile.**
          - T-R: 1 no (a mano, k=10, presi 9, persi 4, p 0,267; k=15 netto
            +6); 2 sì (+11 a k=10 e a k=15); 3 no (fogli, k=10: c-0 0, T-R
            1); 4 no (mediana 14,561 e 14,035 s; massimo 32,466 e 39,618
            s, oltre i 30). **Non adottabile.**
          - Al controllo va **c-LR con tutte le righe, come candidata
            debole**.
          - Domande a mano in B, su 92: k=10 c-0 73, c-LR 78, T-0 78, T-R
            78; k=15 c-0 75, c-LR 80, T-0 78, T-R 81.
          - Tempi del riordinatore in B, mediana per domanda: c-0 5,292 s
            sui fogli e 5,107 a mano; c-LR 6,099 e 6,438; T-0 11,248 e
            11,435; T-R 14,561 e 14,035. Coppie in B: c-0 2642 sui fogli e
            2602 a mano, T 8915 e 8730. Per bando, i quattro lunghi (i due
            PMI, risorse genetiche, apistici) stanno tra 20 e 30 s di
            mediana con T-0 e T-R; gli altri sotto i 15 s. Tempi per bando
            in `misura_T_22-11.txt`, sezione 4.
          - Sospensione del PC. Regola decisa prima di vedere i tempi: una
            domanda con tempo anomalo si esclude dal massimo solo se gli
            orari dimostrano che cade nell'intervallo di sospensione; la
            mediana non si tocca. Dal registro di sistema: una sola
            sospensione, dalle 18:53:18 alle 18:53:36 (circa 17 s), dentro
            la corsa T-R a mano. Lo script registra per ogni domanda la
            durata e non l'orario, quindi la sospensione non si dimostra su
            nessuna domanda: nessuna esclusa, il massimo di 39,618 s
            (apistici) resta e la regola si applica. Le altre tre corse non
            hanno sospensioni.
          Cosa i numeri non dicono (da `misura_T_22-11.txt`, ricopiato dal
          file):
          - Il punto 3 conta i fatti, non dice se sono gli stessi. Nei fogli k=10
            c-0 ha 0 fatti con un pezzo dal gemello, T-0 ha la riga 74 (non
            trovata), T-R la riga 72 (trovata). A mano il conteggio è 1 e 1 ma i
            fatti sono diversi: c-0 la 1092, T-0 la 1092, T-R la 72. Tutti nel
            bando apistici. Il NO del punto 3 viene da un solo fatto.
          - c-LR tutte, che va al controllo, a mano ha 2 fatti dal gemello (72,
            1107) contro 1 di c-0: la regola del punto 3 vale per le T, non per
            c-LR, ma il dato c’è.
          - I tempi sono di una corsa sola, su questo PC, senza ripetizioni: non
            dicono quanto variano. I massimi di c-0 e c-LR non sono registrati
            nelle loro misure: il confronto con c-0 è solo sulle mediane.
          - Il tempo è quello del solo riordinatore; il tempo in app comprende
            anche il recupero e la risposta.
          - Le 92 a mano comprendono le 29 misurate il 21/11, prima delle 63
            nuove: non sono tutte fresche.
          - Sui fogli T-R fa +11 con p 0,027 (k=10) e 0,019 (k=15), ma i fogli
            sono le domande su cui sono state disegnate le configurazioni; la
            regola decide sulle domande a mano.
          Note al testo ricopiato: 1092 e 1107 sono le righe 2:92 e 2:107
          (numerazione interna della misura); "i fatti sono diversi" vale
          per T-R, mentre T-0 ha lo stesso fatto di c-0.
          Conclusione: dare al riordinatore tutti i frammenti del bando
          costa circa 3,4 volte le coppie (da 2,1 a 2,75 volte la mediana
          del tempo di c-0) e porta allo stesso numero a k=10 sulle domande a mano
          (78 per c-LR, T-0 e T-R); il limite non è il numero dei
          candidati.
      14. **Lettura dei mancati** (22/11/2026, fatta in pianificazione da
          chi mantiene il progetto dopo aver visto i casi in
          `mancati_mano_22-11.txt` e `mancati_da_tutte_22-11.txt`). È un
          giudizio: non cambia la misura né la regola.
          1. I 12 mancati a mano da c-0 e c-LR (gli 11 a k=15 più la 89,
             mancata a k=10):
             - mancati veri: 29, 2:39, 2:43, 2:106;
             - risposta trovata o quasi, manca un pezzo di contorno: 18,
               30, 2:99, 2:107;
             - risposta probabile da un altro passaggio, o domanda a
               elenco: 2:24, 2:75;
             - domanda che punta altrove: 2:95;
             - al limite: 89.
          2. I nove fatti mancati da tutte e quattro le configurazioni
             (c-0, c-LR tutte, T-0, T-R tutte; 18, 29, 58, 2:43, 2:107,
             2:114 nei fogli; 18, 29, 30, 89, 2:43, 2:99 a mano):
             - l'app avrebbe la risposta in 18 a mano, 30, 2:99 e 58; per
               la 58 il paragrafo 5.2.2 dice la stessa cosa del passaggio
               del foglio ed è tra i primi tre in tutte e quattro (frammento
               #28 dell'allegato 1 del 13512; già al punto 9, avvertenze);
             - lo risolvono i frammenti vicini: 2:43;
             - al limite: 89 e 2:114;
             - mancati veri: 29 e 2:107 nei fogli.
          3. Conseguenze:
             - la misura è severa: 80 su 92 a k=15 con c-LR; contando i
               casi in cui la risposta c'era, la stima è circa 86. La
               stima sta accanto al numero e non al suo posto; "parziale"
               vuol dire incompleta; il numero vero viene dalle risposte
               complete del 19e;
             - i fatti a più pezzi penalizzano;
             - apistici: 4 mancati su 11 a k=15 (2:95, 2:99, 2:106,
               2:107); la ricerca pesca negli allegati delle altre azioni.
               Dopo la selezione del bando serve chiedere per quale
               azione.
          4. Il prossimo guadagno non viene dalla ricerca ma dal taglio dei
             documenti ("Taglio dei documenti secondo la struttura del
             bando (22/11/2026)", più sotto) e da cosa si passa al modello
             (punto 7, frammenti vicini e scalini).
      15. **Regola di perimetro** (22/11/2026 pomeriggio): nessun'altra
          configurazione entra nel 19d. Il perimetro del punto 10 si è
          allargato tre volte: contesto per frammento (voce 3 del punto
          10), domande a mano (voci 10 e 11), T (voci 12 e 13).
      16. **Da chiarire prima di aprire il controllo.** La regola di
          chiusura (punto 1) dice che nessuna frase di controllo dei
          gemelli deve essere presa dal bando sbagliato. Con le domande a
          mano c-LR ha 2 fatti in cui arriva prima un allegato diverso
          dello stesso bando apistici (72 e 2:107, a k=10 e a k=15), contro
          1 di c-0 (2:92). Va deciso e scritto se gli allegati dello stesso
          bando contano come bando sbagliato.
      17. **Cosa resta per chiudere il 19d**, in ordine (fatto il
          23/11/2026: voci 19, 20 e 21):
          1. revisione esterna (domande alla voce 18);
          2. regola di conferma scritta e committata;
          3. circa 50 domande a mano sul controllo, cinque per bando (voce
             10, "Cambio del piano");
          4. apertura del controllo una volta sola, base e candidata
             insieme;
          5. documenti, chiusura, push.
      18. **Domande per la revisione esterna:**
          - regola di conferma con k=10 come prova principale, perché è il
            k dell'app, e k=15 come controllo che non peggiori: è un
            cambio fatto dopo aver visto la taratura e prima di vedere il
            controllo; è difendibile?
          - la candidata è debole (fogli +11 a k=10, 63 domande nuove a
            mano +3): ha senso portarla al controllo o conviene chiudere
            con la base?
          - gli allegati dello stesso bando contano come gemello (voce 16)?
          - sul controllo decidono le 98 domande dei fogli o le circa 50 a
            mano?
          - il criterio "tutti i pezzi" va tenuto così, con la lettura a
            mano accanto, o cambiato?
      19. **Regola di conferma sulla metà di controllo** (decisa il
          23/11/2026, prima dell'apertura del controllo). È una modifica
          della regola originaria (voce 5, "Regole già in vigore": "si
          adotta solo se guadagna in B sia con k=10 sia con k=15 contro c-0
          (più guadagnati che persi, p ≤ 0,05)"), fatta il 23/11/2026 dopo
          aver visto la taratura e prima di aprire il controllo, su
          indicazione della revisione esterna. Cosa cambia: k=10, il k
          dell'app, è la prova principale; k=15 controlla solo che non
          peggiori.
          - **Decisione 1, quale configurazione.** c-LR tutte sostituisce
            c-0 solo se, in B:
            1. a k=10, sulle 98 domande dei fogli, i presi superano i persi
               con p ≤ 0,05 (test esatto dei segni, a due code);
            2. a k=10, sulle domande a mano del controllo, i presi superano
               i persi. Questo punto non chiede un p, di proposito: con
               circa 50 domande la serie fa da veto e non da prova; 0 presi
               e 0 persi lascia c-0;
            3. a k=15, su tutte e due le serie, il netto è ≥ 0, con l'elenco
               delle regressioni (fatti trovati da c-0 e non da c-LR);
            4. a k=10, sulle 98 domande dei fogli, il netto resta positivo
               togliendo un bando qualunque. Si chiede solo il netto
               positivo, non il p, di proposito: è un controllo sulla
               direzione.
            Se manca un punto, resta c-0. Le due serie non si sommano mai.
          - **Decisione 2, chiusura del passo.** Sulla configurazione
            scelta, 98 domande dei fogli, B, k=10: almeno 85%, e non più di
            10 punti sotto la taratura della stessa configurazione, stessa
            serie, stesso k (c-LR 83 su 97, 85,6%; c-0 72 su 97, 74,2%; voce
            8). Sotto soglia il passo si chiude lo stesso, con gli avvisi in
            produzione solo con il filtro per bando e il "non lo trovo".
          - **Correzione di un difetto della bozza** (23/11/2026). La bozza
            chiedeva anche "nessun pezzo preso da un bando diverso". In B
            quella clausola non può scattare: la ricerca in B si fa solo
            dentro il bando (`cerca_nel_bando` con l'`id_bando` del fatto),
            quindi un altro `id_bando` non entra mai tra i primi k. Per
            questo è tolta. I gemelli tra bandi si contano in A e si
            riportano, senza veto.
          - **Allegati dello stesso bando** (risponde alla voce 16). La
            misura principale non cambia: conta l'allegato giusto. I pezzi
            presi da un altro allegato si contano a parte, distinguendo
            quelli con testo identico parola per parola, e si leggono a
            mano con quattro casi:
            1. testo identico e applicabile: corretto;
            2. stessa informazione riferita a un'altra azione: errato;
            3. informazione simile non pertinente: errato;
            4. documento di un altro bando: errato.
            Non fanno scattare veti. Casi letti il 23/11/2026 in taratura,
            sui testi dei frammenti della copia v0, tutti con testo
            identico parola per parola (l'applicabilità non è stata
            giudicata). Le misure salvate dicono che un altro allegato
            arriva prima, non quale: i frammenti qui sotto sono quelli
            degli altri allegati che contengono il pezzo.
            - 72 (c-LR, a mano; giusto A4 #25 p. 8, 2° posto): "A parità
              di punteggio è prioritaria la domanda che richiede il
              contributo più basso." e la frase successiva, 38 parole,
              identiche in A1 #22, A5 #23 e A3 #22.
            - 2:107 (c-LR, a mano; giusto A5, paragrafo 6.5, diviso tra #30
              e #31): il paragrafo 6.5 "Controlli in loco", 121 parole,
              identico in A4 #34, A1 #31 e A3 #31, dove sta intero in un
              frammento solo.
            - 2:92 (c-0, a mano; giusto A1 #20 p. 7, 2° posto): la riga 5
              della tabella dei criteri (giovane tra 18 e 40 anni, 2,5
              punti), 25 parole, identica in A4 #22, A5 #20 e A3 #20.
          - **Accanto, senza peso nella decisione:** risultati per bando;
            condizione A, con i gemelli tra bandi; lettura a mano dei
            mancati con le classi del 22/11 (voce 14).
          - **Domande a mano del controllo:** cinque fatti per bando scelti
            con un seme fisso, tutti se il bando ne ha meno; fondo strade
            escluso come in taratura (voce 10); domande scritte prima di
            ogni misura sul controllo, da chi mantiene il progetto, nessun
            modello; colonna "spiegata" come in taratura.
          - **Cosa ci si aspetta, scritto prima.** c-0 in taratura è al 74%
            sui fogli a k=10 (72 su 97): se la candidata non passa, il
            passo si chiude con ogni probabilità sotto soglia. È un esito
            previsto dalla regola.
          - **Indipendenza in taratura** (23/11/2026, dalle misure salvate,
            nessuna misura nuova;
            `dati-grezzi/prova/19d/contesto/per_bando_23-11.txt`). c-LR
            contro c-0, in B. Netto per bando sulle 97 dei fogli a k=10:
            sviluppo progetti (01bfe9) +4; i due PMI, Punti Digitale e
            apistici +2 ciascuno (apistici +3/-1); musica +1; Cultura,
            Sport, fondo strade e parcheggi 0; risorse genetiche -2.
            Bandi con netto positivo, zero e negativo:
            - fogli, k=10: 6, 4, 1; k=15: 5, 5, 1;
            - a mano (92 domande, 10 bandi), k=10: 6, 3, 1; k=15: 5, 5, 0.
            Togliendo un bando alla volta, il netto più basso è: fogli k=10
            +7 (senza 01bfe9, p 0,092, contro +11 e p 0,013 con tutti);
            fogli k=15 +3 (senza 01bfe9, p 0,453); a mano +4 a k=10 e a
            k=15. Nessun bando porta il netto a zero o sotto. Conclusione:
            il guadagno è diffuso ma piccolo; senza il bando 01bfe9 il p sui
            fogli a k=10 sale a 0,092.
          - **Esito della revisione esterna** (23/11/2026; testo in
            `dati-grezzi/prova/19d/contesto/revisione_esterna_23-11.txt`;
            i numeri che cita sono stati confrontati con le voci 11 e 14).
            Cinque punti:
            1. i fatti non sono osservazioni indipendenti, perché stanno su
               pochi bandi: verificare il guadagno per bando e togliendo un
               bando alla volta. Accolto: misura per bando del 23/11 qui
               sopra e punto 4 della decisione 1;
            2. domande dei fogli e domande a mano misurano cose diverse e
               non si sommano; le domande a mano si scelgono a caso, cinque
               per bando, senza guardare il controllo. Accolto, tranne una
               parte (sotto);
            3. il passaggio a k=10 principale e k=15 di controllo è
               difendibile se dichiarato come modifica della regola, con
               una non inferiorità esplicita: netto ≥ 0 a k=15 con l'elenco
               delle regressioni. Accolto;
            4. c-LR va al controllo come ipotesi da verificare, non come
               configurazione già vincente; se non passa resta la base.
               Accolto: decisione 1, "se manca un punto, resta c-0";
            5. il criterio "tutti i pezzi" si tiene come misura principale,
               con la lettura a mano come misura secondaria; per gli
               allegati, quattro casi decisi prima dell'apertura. Accolto.
            Non accolto, l'unico: la revisione propone che decidano le 98
            domande dei fogli da sole, con le domande a mano come verifica
            secondaria. Motivo: in taratura le domande dei fogli favoriscono
            la candidata (in B, k=10, +11 sulle 97 dei fogli contro +3 sulle
            63 nuove a mano, voce 11); si richiedono tutte e due le serie.
            In fondo la revisione distingue due decisioni: superare l'85% e
            dimostrare che la candidata è meglio della base sono due cose
            diverse. La prima riguarda la qualità del recupero (decisione
            2), la seconda l'effetto della modifica (decisione 1); una
            candidata può superare l'85% senza dare ragioni sufficienti per
            sostituire la base.
      20. **Esito dell'apertura della metà di controllo (23/11/2026).**
          Numeri da `dati-grezzi/prova/19d/contesto/rapporto_apertura_controllo.txt`,
          scritto da `--apertura --controllo` secondo la regola della voce
          19; i candidati tra i 30 dai json delle misure in
          `dati-grezzi/prova/19d/contesto/misure/`.
          - **Lancio.** Una sola volta, il 23/11/2026, da chi mantiene il
            progetto, verso le 14:39 (dalle date dei file: domande a mano
            salvate alle 14:38, prima misura chiusa alle 14:55 dopo 995 s,
            rapporto scritto alle 15:31). Impronta dello script prima
            216d67cc8abc, dopo 216d67cc8abc: uguali. 98 domande dei fogli e
            49 a mano: la riga del foglio 1 numero 57 aveva la domanda vuota
            ed è stata saltata.
          - **Procedimento** (aggiunto il 23/11/2026, dalla chat di
            pianificazione). Regola (commit 7024a80) e codice della misura
            (commit 43c2860) pubblicati prima dell'apertura. Domande a mano
            del controllo scritte da chi mantiene il progetto con lo stesso
            procedimento della taratura: spiegazioni su richiesta, controllo
            "punta al fatto?", lettura del file intero con la segnalazione
            delle sole frasi capite in un altro senso. Tre righe segnalate
            (righe 37, 40 e 48 del foglio di calcolo, cioè i fatti 2:40,
            2:59 e 2:96) e riscritte da chi mantiene il progetto prima
            della misura.
          - **Decisione 1**, c-LR tutte contro c-0, in B:
            1. fogli, k=10: presi 15, persi 3, netto +12, p 0,008: sì. Persi
               2:14, 2:83, 2:100;
            2. a mano, k=10: presi 4, persi 1, netto +3, p 0,375 (nessun p
               richiesto): sì. Perso 64;
            3. k=15, netto ≥ 0: fogli presi 12, persi 1, netto +11, p 0,003,
               regressione 2:76; a mano presi 4, persi 2, netto +2, p 0,688,
               regressioni 59 e 64: sì;
            4. fogli, k=10, togliendo un bando alla volta: netto più basso
               +9 (senza il PMI 7057d9, presi 12, persi 3, p 0,035): sì.
            Esito: **c-LR sostituisce c-0**.
          - **Decisione 2**, c-LR, fogli, B, k=10: 77 su 98, 78,6%. Almeno
            85%: no. Taratura della stessa configurazione 83 su 97, 85,6%;
            scarto -7,0 punti, entro i 10. Esito: **sotto soglia**: il passo
            si chiude lo stesso, con gli avvisi in produzione solo con il
            filtro per bando e il "non lo trovo".
          - **Taratura e controllo**, fogli, B, k=10:

            | configurazione | taratura | controllo |
            |---|---|---|
            | c-0 | 72 su 97 (74,2%) | 65 su 98 (66,3%) |
            | c-LR tutte | 83 su 97 (85,6%) | 77 su 98 (78,6%) |

            Il guadagno è confermato; il livello assoluto della taratura
            era più alto di 7-8 punti per entrambe. Il numero da citare da
            qui in avanti è quello del controllo.
          - **Attesa scritta prima e com'è andata.** La candidata è passata;
            la chiusura è comunque sotto soglia.
          - **Accanto, senza peso nella decisione.**
            - Per bando, B, k=10: fogli 6 bandi con netto positivo, 5 a
              zero, nessuno negativo; a mano 3, 6 e 1 (PMI 8cd3ac, -1).
            - Condizione A, c-LR contro c-0: fogli k=10 71 contro 42 (+32,
              -3, netto +29, p 0,000), k=15 74 contro 52 (+25, -3, netto
              +22); a mano k=10 38 contro 29 (+10, -1, netto +9, p 0,012),
              k=15 40 contro 33 (+7, -0, netto +7, p 0,016).
            - Gemelli tra bandi, in A: pezzo dal bando gemello prima del
              giusto, fogli c-0 3 (2:15, 2:70, 2:84) e c-LR 4 (2:66, 2:70,
              2:72, 2:84) a k=10 e k=15; a mano c-0 3 a k=10 (2:15, 2:70,
              2:83) e 4 a k=15 (in più 59), c-LR 2 (2:70, 2:84). Gemello
              senza il giusto: 0 ovunque.
            - Candidati tra i 30 (giusto tra i candidati prima del
              riordino): fogli, B, c-0 76 e c-LR 88 su 98; A 56 e 75. A
              mano, B, 43 e 43 su 49; A 36 e 41.
            - Tempi del riordinatore per domanda, B: fogli c-0 mediana
              4,567 s, massimo 9,183 s; c-LR 5,292 s e 7,006 s. A mano c-0
              4,019 s e 5,116 s; c-LR 5,639 s e 7,205 s. Misure intere: fogli
              995 s e 1065 s, a mano 421 s e 571 s.
            - Pezzi presi da un altro allegato degli apistici, tutti con
              testo identico parola per parola (il tratto del pezzo; il
              frammento intorno può essere diverso, per esempio nel fatto 70
              azione e contributo massimo cambiano: sezione 4 di
              `mancati_controllo_23-11.txt`): fogli 70 e 2:102, a mano 68
              e 2:96. Da leggere a mano con i quattro casi della voce 19.
            - Mancati di c-LR in B a k=10: 21 dei fogli e 7 a mano, per la
              lettura a mano con le classi del 22/11.
          - **Dichiarazione: colonna "spiegata".** Nel file
            `domande_a_mano_controllo.xlsx` le righe 6 e 40 del foglio di
            calcolo, cioè i fatti 19 (foglio 1 riga 19) e 2:59 (foglio 2
            riga 59), erano
            domande spiegate senza il "si" nella colonna "spiegata". Il
            file non è stato modificato. Tabella ricalcolata dalle misure
            salvate contando quelle due come spiegate; tutte e due sono
            trovate da c-0 e da c-LR a k=10 e a k=15, quindi presi e persi
            non cambiano. B, a mano:

            | | rapporto | corretta |
            |---|---|---|
            | k=10, spiegate | 18: c-0 13, c-LR 14; +2 -1, netto +1, p 1,000 | 20: c-0 15, c-LR 16; +2 -1, netto +1, p 1,000 |
            | k=10, non spiegate | 31: c-0 26, c-LR 28; +2 -0, netto +2, p 0,500 | 29: c-0 24, c-LR 26; +2 -0, netto +2, p 0,500 |
            | k=15, spiegate | 18: c-0 13, c-LR 14; +2 -1, netto +1, p 1,000 | 20: c-0 15, c-LR 16; +2 -1, netto +1, p 1,000 |
            | k=15, non spiegate | 31: c-0 27, c-LR 28; +2 -1, netto +1, p 1,000 | 29: c-0 25, c-LR 26; +2 -1, netto +1, p 1,000 |
      21. **Lettura a mano dei mancati del controllo (23/11/2026).** È un
          giudizio, accanto alla misura e senza peso sull'esito (voci 19 e
          20). Numeri della misura da `rapporto_apertura_controllo.txt` e
          `mancati_controllo_23-11.txt`, in `dati-grezzi/prova/19d/contesto/`.
          1. **Metodo e limiti.** I 28 mancati di c-LR in B a k=10 (21 dei
             fogli, 7 a mano) sono stati letti dalla chat di pianificazione
             sul file `mancati_controllo_23-11.txt`, che mostra le prime 200
             battute dei primi 10 frammenti arrivati. Tre frammenti sono
             stati poi letti per intero (allegato A4 degli apistici #40;
             testo coordinato delle risorse genetiche #35 e #88): due
             nascondevano la risposta. Il numero dei mancati veri qui sotto
             è quindi un massimo, non un conteggio esatto.
          2. **Classi, fogli (21):**
             - mancato vero, 10: 2:14, 2:76, 2:83, 2:100, 22, 34, 48, 68,
               2:90, 2:101;
             - frammento giusto vicino (numero prima o dopo) a uno dei primi
               10, 7: 59, 60, 92, 2:62, 2:66, 2:96, 2:112;
             - risposta in un altro passaggio arrivato tra i primi 10, 2: 46
               (frammento #88, criteri di selezione, cita il punto CR03) e
               2:48 (frammento #35, "solo per uno dei 3 Settori");
             - parte della risposta, 1: 2:32;
             - dato giusto da un allegato sbagliato, 1: 70.
             **Classi, a mano (7):**
             - mancato vero, 1: 2:100;
             - frammento giusto vicino, 3: 59, 64, 2:51;
             - l'app risponderebbe, contestato, 2: 68 e 2:96;
             - parte della risposta, 1: 2:32.
          3. **I quattro casi degli allegati degli apistici** (sezione 4 del
             file; i quattro casi della voce 19).
             - 70: resta mancato. Il minimo di 1.800 euro è uguale in B3, B4
               e B5, ma arriva il frammento di B5 con il massimo di 30.000
               euro al posto di 4.500; in B1 il minimo è 1.200. Dato giusto,
               fonte sbagliata e dato diverso accanto.
             - 68 e 2:96 a mano: la domanda non nomina l'azione e la regola
               è identica nei quattro allegati; contano come mancati perché
               il foglio lega il fatto a un allegato.
             - 2:102: trovato al quinto posto, regola identica ovunque.
          4. **Revisione esterna alla cieca** (ChatGPT, stesso file, senza
             le classi della chat). Stessa classe in 17 casi su 28. Le 11
             differenze:
             - 3 sul confine tra mancato vero e parte della risposta (2:100,
               48, 2:90): in ogni caso l'app non risponde;
             - 2 dove la chat aveva letto il frammento intero (46, 2:48);
             - 4 dove nel file c'era un vicino o un segno non visto dal
               revisore (59 e 92 dei fogli, 70, 2:51 a mano);
             - 2 disaccordi veri (68 e 2:96 a mano: "allegato sbagliato" per
               il revisore). Restano scritti come contestati.
             Osservazioni del revisore sulle domande: nella 2:32 a mano "la
             data in cui viene presentato il bando" è ambigua; la 2:51 e la
             2:96 a mano puntano più alla tabella che alla frase.
          5. **Cosa dice la lettura.**
             1. I frammenti vicini sono il primo rimedio: 7 casi su 21 nei
                fogli, 3 su 7 a mano. È un'ipotesi letta su 200 battute, da
                misurare.
             2. Senza i vicini alcuni casi sono pericolosi e non solo
                mancati: nella 2:51 a mano arriva la tabella dei costi orari
                con la sola riga "Basso"; nella 59 dei fogli arriva il
                requisito senza la durata, con "per tre anni" del punto
                successivo subito sotto. Sono tabelle ed elenchi spezzati
                dal taglio.
             3. Circa metà dei mancati veri è questione di parole:
                magazzino, di tasca nostra, telecamere di controllo,
                università, Banca europea degli investimenti contro BEI.
                Sono cinque casi: 22 e 48 dei fogli e 2:100 a mano non
                arrivano in nessun modo; 46 e 60 dei fogli arrivano già per
                altra via (altro passaggio; frammenti vicini).
             4. Due dei quattro persi rispetto a c-0 sono frammenti di
                tabella (2:100 dei fogli dal primo al dodicesimo posto; 64 a
                mano fuori dai 30 candidati). Ipotesi da verificare, non
                conclusione: il contesto in testa può spingere le righe di
                una tabella lunga oltre la parte che il riordinatore legge.
             5. Nei bandi la stessa regola è spesso scritta in più punti: la
                misura ne conta uno, l'app li può usare tutti. La misura
                severa resta pessimista.
             6. La metà di controllo ora è spesa: i rimedi provati su queste
                domande non sono più una conferma pulita. Le conferme
                successive si fanno su domande nuove (sei a mano per ogni
                bando nuovo, punto 7) e sulle risposte vere.
          Rimedi e voci che ne vengono: punto 7 (dettaglio) e roadmap,
          passo 19e (elenco).

   **Piano del 19d del 20/11/2026 mattina** (testo di prima, invariato; i
   punti 3 e 4 sono superati dai punti 1-3 qui sopra):
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
   Limiti dei piani gratuiti, dalle pagine ufficiali lette il 20/11/2026
   da chi mantiene il progetto: Supabase mette in pausa il progetto dopo
   una settimana di inattività; Streamlit Community Cloud mette l'app in
   pausa dopo 12 ore senza visite e dà da 690 MB a 2,7 GB di memoria. Da
   tenere presenti prima di dare il link (passo 21) e nella scelta del
   modello di embedding (più sopra, "Passo 19d", punto 4).
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
  (27/11/2026) Per torch superata: provata nella prova di memoria del
  25/11/2026 e portata su `main` con la riga di torch per processore
  ("Prova di memoria su Streamlit (25/11/2026)"). Resta aperta la parte
  su chromadb.
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
  Aggiornamento del 20/11/2026, insieme di prova grande: almeno 200
  domande, non prima della nuova baseline. Fonti: le domande vere
  raccolte con il tasto di segnalazione (passo 20); domande scritte da
  più modelli diversi sugli stessi fatti, con una colonna per l'autore;
  una parte scritta da persone. Il costo vero sono le etichette, non le
  domande. Motivo: nel 19d le domande dei fogli dei fatti le ha scritte
  un modello, e le tecniche in cui un modello scrive testo di ricerca
  vanno misurate anche su domande d'altra origine ("Passo 19d", punto
  9).
- (23/11/2026) **L'insieme di prova del 19d pende verso il dettaglio
  tecnico** (tabelle, commi), perché i fatti sono stati presi leggendo i
  PDF riga per riga. Le domande di chi arriva per la prima volta sono
  meno rappresentate e andranno misurate con la scheda (passo 22). Le
  domande di dettaglio si fanno dopo aver scelto il bando: la condizione
  B corrisponde all'uso vero.
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
- (→ passo 2b, 21/11/2026) **Copertura dell'archivio**: dei 97 fatti di
  taratura solo 7 hanno la risposta nei campi dell'archivio, e molti campi
  di dettaglio sono vuoti per la maggior parte dei bandi ("Passo 19d",
  punto 6). Le risposte di dettaglio vengono dai frammenti; il 2b corregge
  i campi sbagliati, non li riempie per coprire quelle domande.

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

## Copertura dell'archivio (22/11/2026)

Voce nuova, in coda come passo a sé, da fare a 19d chiuso. Voci vicine,
più vecchie: "Prova di copertura" (→ passo 16, in "Da 'Prima della demo
con il consulente pilota', ancora aperte") e `docs/piano-fonti-burt-ministeri.md`.

- Oggi si misura se l'app trova i bandi che ha, non quanti dei bandi
  esistenti ha. Per chi usa l'app un bando assente è un errore come un
  bando non trovato.
- Canali paralleli per scoprire fonti e bandi mancanti: il consulente
  pilota; la ricerca web per argomento a partire dalle domande; la
  ricerca manuale di chi mantiene il progetto; le delibere dei tre comuni
  e dell'Unione; il sommario del BURT; le newsletter del territorio; il
  totale dichiarato dalle pagine elenco.
- Un solo registro delle fonti, con una colonna per il canale da cui la
  fonte è arrivata. Una sola porta d'ingresso: pagina ufficiale dell'ente
  che emette, un bando reale con la data, robots.txt letto.
- Ricerca web:
  - è un controllo fuori linea, non una risposta all'utente;
  - produce sospetti da verificare a mano;
  - alla ricerca va l'argomento, non il testo scritto da chi ha chiesto;
  - i siti che raccolgono bandi di altri valgono come segnali, non come
    fonte;
  - ogni risultato va in una di quattro caselle: in archivio, scaduto,
    fuori territorio, mancante;
  - di ogni mancante si cerca la causa: fonte non nel registro, bando
    perso dalla scansione, bando scartato da un filtro.
- Misura ricorrente: una volta al mese, venti bandi noti da fonti
  indipendenti; si conta quanti erano in archivio a quella data.
- Prima prova a mano, un'ora: dieci argomenti dalle domande di prova.
- (23/11/2026) Un canale in più: i bandi citati dentro altri bandi, da
  estrarre dai PDF già caricati; ogni citazione senza corrispondenza in
  archivio è un candidato da verificare. Un bando scaduto non è sempre
  irrilevante: per il cumulo conta anche il bando chiuso. Resta la
  decisione che l'app mostra la clausola di ciascun bando e non decide la
  combinazione (roadmap, "Decisioni prese").

## Taglio dei documenti secondo la struttura del bando (22/11/2026)

Voce nuova, fuori dal Parcheggio perché attacca un difetto misurato e
costa di più farla dopo. Si aggancia al ramo della regola di chiusura
del 19d "ci si ferma e si ripensa il modo di spezzare i documenti"
("Passo 19d", punto 1), mai toccato fino a oggi. Viene dalla lettura dei
mancati ("Passo 19d", punto 13, voce 14).

- Difetto misurato il 22/11: la risposta è spezzata tra frammenti, per
  il taglio a lunghezza fissa.
- Cura della causa: tagliare per articolo, comma, tabella con le sue
  intestazioni, elenco con la sua frase introduttiva.
- Rischi: frammenti troppo grandi o troppo piccoli. Regole: un tetto di
  lunghezza, scendendo di livello (comma, lettera, poi lunghezza); ogni
  pezzo porta in testa la sua intestazione.
- Vincolo di tempo: da decidere prima di ampliare l'archivio, perché
  dopo ogni bando va ricaricato. Costa rifare frammenti, contesti e
  misure. I fatti e le domande a mano restano validi.
- Il riconoscitore dei titoli è la parte difficile (il 21/11 una regola
  semplice sbagliava una riga su due, dato riferito da chi mantiene il
  progetto e non scritto nei file) e serve a due cose: il taglio e la
  riga DOVE scritta dal codice, già in Parcheggio ("Riga DOVE ricavata
  dal programma").
- Era un requisito iniziale del progetto: non spezzare articoli e commi.
- (24/11/2026) Requisito: le tabelle restano intere se corte; se lunghe
  si tagliano per righe, ripetendo intestazione e titolo della tabella in
  ogni pezzo.
- (24/11/2026) Requisito: l'unità passata al modello ha un tetto di
  dimensione, e ogni pezzo porta il titolo della sezione o dell'articolo
  a cui appartiene.
- (24/11/2026) Passo preliminare: provare sui 25 PDF già scaricati un
  lettore che riconosce le tabelle (per esempio pdfplumber o PyMuPDF),
  contando le tabelle trovate e guardandone una decina a mano. Oggi i PDF
  si leggono con pypdf, che restituisce solo testo. I modelli che
  riscrivono la pagina da immagine si valutano solo se questi falliscono
  o per gli avvisi scansionati, e sempre con un controllo: ogni numero
  della tabella ricostruita deve comparire nel testo estratto da pypdf.
- (25/11/2026) Proposta: un solo taglio a livelli invece di più tagli
  indipendenti. Si taglia al livello più piccolo (comma, riga di
  tabella) e ogni pezzo conosce il genitore (articolo o tabella) e il
  titolo della sezione. Dallo stesso indice si ricavano tre cose: il
  pezzo piccolo per la ricerca, il genitore entro un tetto per il
  contesto passato al modello, il titolo per la verifica e per la
  categoria del dato ("Verificatore per categoria (25/11/2026)"). Il
  vicino diventa il fratello sotto lo stesso genitore: è la V3 che il
  24/11 non si è potuta misurare ("Passo 19e, rimedio 1").
- (25/11/2026) Verifica a cascata sullo stesso indice: prima il pezzo
  citato, poi il genitore. Allargare il testo di confronto rende il
  controllo più permissivo, quindi il genitore non trasforma un rosso in
  verde: dà un terzo esito, "trovato in un altro punto dello stesso
  articolo".
- (25/11/2026) Etichette scritte sul pezzo al momento del taglio, ciascuna
  con la sua origine: posizione, bando, unità di struttura, categoria.
  Posizione e bando sono certe e ci sono già. L'unità di struttura
  (articolo, comma, riga di tabella) manca. La categoria (scadenze,
  importi, requisiti, beneficiari, atti) è un'interpretazione: può avere
  più valori, e dove la regola non è sicura resta vuota. Per il
  verificatore vale la categoria ricavata dal titolo con una regola;
  quella scritta da un modello solo come ripiego dichiarato.
- (25/11/2026) Esito della parte E dell'"Inventario delle scritture
  (25/11/2026)", sui 25 PDF del registro letti con pypdf. Schemi dei
  titoli: "Art. N" in 6 PDF (in 2 il titolo sta sulla riga dopo), "N.
  Titolo" o "N TITOLO" in 16 (in 11 avvisi con un livello "N.M" sotto),
  nessuno in 3. Regola scritta prima di guardare: catena 1, 2, 3, … di almeno 3
  titoli senza buchi; righe dello stesso schema fuori dalla catena al
  più il 20%; testo prima del primo titolo al più il 15%. Con la regola:
  13 sì, 10 no, 2 non servono. Letti a mano i titoli di ogni catena:
  - affidabile con regole semplici: 16 PDF (25205, 18191, 24161, i 4
    allegati 14025, DM 75, gli avvisi e le due convenzioni di Cultura e
    Sport Missione Comune, il regolamento del fondo sport, 13512, 9506
    allegato 1, testo coordinato SRA16-ACA16). Quattro di questi la
    regola li respingeva per il "rumore": sono commi ed elenchi numerati,
    che la catena già scarta; uno (DM 75) per il 18% di testo prima
    dell'articolo 1, che sono i "VISTO" del decreto. Servono tre accorgimenti: gli "Art."
    prima dei numeri, lo stesso stile del titolo 1 (maiuscolo o no),
    titoli di al più 14 parole; senza, la catena prendeva i commi (22706,
    DM 75) e le righe della tabella dei punteggi (14025);
  - non affidabile: 4. Elenco dei codici ATECO (allegato 4 di 9505 e
    9506, una tabella di 236 pagine); allegato 1B di 9505 (elenco tecnico
    con note numerate); presentazione del voucher (diapositive, 83% del
    testo fuori); 22706 (articoli giusti, ma il 26% del testo, le
    definizioni, sta prima dell'articolo 1 senza numero);
  - non serve: 5 (le due proroghe di una pagina, l'avviso del fondo
    strade di 3 pagine, gli allegati 5 di 9505 e 9506 di 2 pagine, che la
    regola dava per buoni a torto: la catena erano commi).
  Dimensioni delle unità nei 16 affidabili: media da 1.200 a 6.800
  caratteri, massimo fino a 25.000 (13512, 9506, testo coordinato): in
  quei tre il livello "N.M" (24-37 titoli) serve per stare sotto un
  tetto. Testo fuori da ogni unità: dallo 0,4% al 18% (indice e
  premesse). Script e uscite in `dati-grezzi/prova/inventario/`
  (`struttura.py`, `struttura_uscita_2026-11-25.txt`).
- (25/11/2026) Passo successivo già previsto, invariato: la prova di un
  lettore che riconosce le tabelle sui 25 PDF (punto del 24/11 qui
  sopra). Indizio economico, non una misura: pypdf in modalità layout,
  pagina con almeno 3 righe con due salti di 5 o più spazi. 334 pagine su
  633; tolte le 236 dell'elenco dei codici, 98 su 397. L'indizio è
  rozzo: l'avviso di Sport Missione Comune ne ha 16 su 17, quello di
  Cultura, con la stessa struttura, 3 su 18.

## Bandi a più finestre: la prossima finestra aperta (24/11/2026)

Voce nuova, fuori dal Parcheggio, da decidere insieme al passo 2b.

- Per i bandi a più finestre l'app mostra l'ultima scadenza; all'utente
  serve la prossima finestra aperta e la condizione delle successive
  (per esempio "solo se resta budget").
- Caso: dopo la laurea (`dopo-la-laurea-finanziamenti-per-progetti-di-informaz-851fa7`),
  in archivio fino al 15/07/2027, finestra in corso fino all'11/12/2026
  (terza di quattro in `scadenze_bando`).
- Da decidere come mostrarlo.

## Sospensioni e chiusure anticipate (24/11/2026)

Voce nuova, fuori dal Parcheggio, accanto a quella sulle finestre, da
decidere insieme al passo 2b.

- Lo stato calcolato dalla scadenza non vede le sospensioni e le
  chiusure anticipate. Caso: incentivi ai datori di lavoro privati,
  aperto in archivio fino al 10/01/2028, sospeso dall'8/07/2026 per
  cinque categorie di destinatari (decreto n. 742/2026 di Arti); vedi
  "Letture dei siti e stato dei requisiti", righe del 24/11/2026.
- Serve un posto in archivio per "sospeso", anche solo per alcune
  categorie di destinatari, con la frase di prova, e l'app lo deve dire.
- Fino ad allora la ricognizione lo segnala con la nota "possibile
  sospensione" (`src/estrazione/sospensione.py`).

### Campo strutturato della sospensione (24/11/2026)

- (24/11/2026) Fatto, senza modello (dettaglio in `fatto.md`, 24/11/2026):
  tabella `sospensioni_bando`, una riga per periodo di sospensione, con
  `ambito` ('tutto' / 'in_parte'), `sospeso_dal`, `sospesi` (per chi),
  `resta_aperto` (cosa resta aperto), `atto`, `frase`, `riaperto_il` e
  `riapertura_frase`, `verificato_il`, `origine` 'manuale'. Un periodo
  vale da `sospeso_dal` al giorno prima di `riaperto_il`. Si scrive solo
  con `correggi_da_testo`, con tutte le frasi trovate nel testo salvato;
  l'estrazione non la scrive.
- (24/11/2026) Perché una tabella e non quattro colonne in `bandi.csv`:
  il testo salvato del bando degli incentivi ha già tre eventi, non uno.
  Sospensione della lettera e dal 24/07/2024 (decreto Arti 622 del
  19/07/2024, righe 152-154), riapertura per la lettera e dopo il
  23/10/2024 (decreto Arti 841 del 14/10/2024, righe 150-151), e
  sospensione delle lettere a-e dall'8/07/2026 (decreto n. 742/2026,
  righe 122-128). Con le colonne la riapertura non ha posto, e passare
  dopo alla tabella vorrebbe dire due cambi di schema, due impronte e due
  ricreazioni del database. Costo della tabella: `crea_da_csv` accetta
  vuote le tabelle di `TABELLE_DOPO_LA_COPIA` (oggi solo
  `sospensioni_bando`), perché la copia congelata
  `2026-11-24_e26e2e30` non ha il CSV e non si modifica.
- (24/11/2026) In coda: il periodo 2024 degli incentivi (sospensione e
  riapertura della lettera e). La data di riapertura è da interpretare:
  le domande si presentano "successivamente al 23 ottobre 2024", per
  assunzioni dal 25 luglio 2024. Da decidere se `riaperto_il` è il 23 o
  il 24/10/2024 prima di scrivere la riga.
- (24/11/2026) In coda: pulizia di `scadenza_nota` e `beneficiari` degli
  incentivi. Dopo il campo strutturato la sospensione si legge tre volte
  nella riga (in testa, nella nota, nei beneficiari). Decisione del
  24/11/2026: restano come sono in questo passo; la pulizia è un passo a
  parte, dopo aver visto l'uscita dell'app.
- (24/11/2026) In coda: `diagnosi_attese` riceve le sospensioni nella
  frase dello stato (`stato_bando`), ma la categoria resta APERTO o
  A_SPORTELLO anche per un bando sospeso del tutto: allinearla vuol dire
  una categoria nuova, non solo passare le sospensioni.
- (24/11/2026) Limite: il ramo "sospeso del tutto" (fuori dagli aperti,
  dai conteggi e da "in scadenza", in coda agli elenchi sotto "Sospesi
  del tutto, ora non si presentano domande:") è provato solo con dati
  finti (`tests/test_sospensioni.py`). Nell'archivio l'unico caso vero è
  una sospensione parziale.
- (24/11/2026) Limite: la ricognizione, che segnala "possibile
  sospensione", legge solo le pagine della Regione dei bandi aperti (o
  scaduti da poco). Catalogo Incentivi Italia e altre fonti non sono
  coperti. Il 23/11/2026 (`ricognizione-4.csv`) l'unica nota vera era
  quella degli incentivi. La ricognizione rilegge anche le pagine dei
  bandi sospesi del tutto (è così che si scopre una riapertura), con un
  test che lo controlla; la nota resta un avviso e non scrive il campo.
- (24/11/2026) Da fare, chiamando il modello (da lanciare a mano): due
  domande vere prima e dopo, a data fissata 2026-11-24. (1) "Ho
  un'azienda agricola e vorrei assumere un disoccupato di 57 anni: c'è
  un incentivo della Regione?" (2) "Voglio assumere una persona con
  disabilità iscritta al collocamento mirato: posso chiedere l'incentivo
  regionale per le assunzioni?" Regola di chiusura, decisa prima delle
  risposte: dopo la modifica la 1 dice che per quel caso il bando è
  sospeso, senza presentarlo come aperto; la 2 dice che per quel caso
  resta aperto. Se la 1 dice ancora "aperto" senza la sospensione, il
  passo non è chiuso e si apre un lavoro sul prompt (`ISTRUZIONI` non
  toccate in questo passo).

### Esito delle domande vere (24/11/2026)

Lanciate da chi mantiene il progetto il 24/11/2026, con
`domande_sospensione.py`. Script e risposte sono in
`dati-grezzi/prova/sospensione/2026-11-24/` (`risposte_prima.json`,
`risposte_dopo.json`).

- (24/11/2026) Regola rispettata. Dopo la modifica la risposta alla
  domanda sul disoccupato di 57 anni dice che per quella categoria (over
  55 disoccupati) il bando è sospeso; quella sulla persona con disabilità
  dice che resta aperto. Costo 0,235 $ per quattro risposte (0,2355 $
  nei due file).
- (24/11/2026) Limite: anche "prima" la risposta dava la sospensione,
  perché la correzione a mano del 24/11 l'aveva già scritta in
  `scadenza_nota` e `beneficiari`. La prova quindi non mostra un
  miglioramento delle risposte dovuto al campo strutturato. Il campo vale
  per tre cose: l'ordine garantito dal codice, il filtro dei sospesi del
  tutto, e il fatto che una riestrazione non lo cancella. Nessuna delle
  tre è misurata dalle due domande.

Voci nuove, viste nelle risposte vere. Ciascuna è stata vista su quattro
risposte e non è ancora misurata.

- (24/11/2026) Verificatore, dato giusto nel ruolo sbagliato. Nella
  risposta "dopo" alla seconda domanda la finestra successiva è scritta
  "dal 2027-01-11 al 2027-01-10 (anno 2028)" invece che al 2028-01-10.
  L'esito è VERDE perché 2027-01-10 compare nella fonte, come fine
  dell'altra finestra. Vista su quattro risposte, non ancora misurata.
  (25/11/2026) misurata e corretta: ora rosso, "Verificatore per
  categoria (25/11/2026)".
- (24/11/2026) Verificatore, falsi allarmi. Un numero scritto
  dall'utente nella domanda (57) è segnato come non trovato; "1° gennaio
  2021" non è riconosciuto come "primo gennaio 2021". Esito ROSSO su due
  risposte corrette. Visti su quattro risposte, non ancora misurati.
  (25/11/2026) misurati e corretti: il 57 è un "dato della domanda",
  "1° gennaio 2021" è presente; "Verificatore per categoria
  (25/11/2026)".
- (24/11/2026) Citazioni: il `riferimento_atto` lungo degli incentivi
  (sette decreti più la sospensione) è ripetuto per intero a ogni frase,
  4 o 5 volte per risposta nei due file. Da decidere una forma breve dopo
  la prima citazione. Visto su quattro risposte, non ancora misurato.
  (25/11/2026) fatta nel testo mostrato: "Citazioni ripetute
  (25/11/2026)".
- (24/11/2026) Date in formato AAAA-MM-GG nelle risposte "dopo", prese
  dal testo dello stato ("sospeso in parte dal 2026-07-08"). Da valutare
  il formato "8 luglio 2026" nel testo passato al modello, tenendo conto
  di come il verificatore riconosce le date. Visto su quattro risposte,
  non ancora misurato.
- (24/11/2026) Proposta: lo stato "sospeso" o "sospeso in parte"
  scritto dal codice accanto ai bandi sotto "Bandi citati", preso dal
  database come titolo e indirizzo, senza passare dal modello. Vista su
  quattro risposte, non ancora misurata.

## Cosa entra in archivio (24/11/2026)

Decisione di chi mantiene il progetto del 24/11/2026. Voce nuova,
fuori dal Parcheggio.

L'app nasce per chi ha un'attività o un ente, o vuole avviarne una;
mostra anche le occasioni che non sono bandi a contributo e le misure
rivolte alle persone, perché un comune, un ente del terzo settore o
un'azienda possono averne bisogno per i propri cittadini, utenti o
dipendenti.

Una voce entra se valgono tutte e tre le condizioni:
1. viene da un ente pubblico o da un'istituzione, comprese banche e
   fondazioni;
2. si presenta una domanda o un modulo, con una scadenza e una
   procedura;
3. ne può arrivare denaro o un vantaggio economico, diretto o
   indiretto.

Restano fuori, per natura e non per destinatario: concorsi e selezioni
di personale, posti di lavoro, ricerca di professionisti,
accreditamenti senza vantaggio economico, graduatorie ed esiti. I
contributi per assumere personale restano dentro.

Ogni voce porta due etichette sempre visibili: il tipo (bando a
contributo, manifestazione di interesse, altri da definire) e a chi è
rivolta (imprese, enti e comuni, terzo settore, chi avvia un'attività,
persone).

Le misure per le persone entrano solo se passano le tre condizioni e
stanno nelle fonti già seguite: non si cercano fonti apposta.

Caso che ha portato alla decisione: Toscana Art Bonus per comuni e
unioni, manifestazione di interesse aperta fino al 31/03/2027, scartata
il 24/11 come "non è un bando".

Servono: un campo "tipo" in archivio, la resa delle due etichette
nell'app, un'istruzione nuova per il modello che estrae; le etichette
dell'insieme di prova valgono per i soli bandi a contributo. Fino ad
allora "non è un bando" è uno scarto definitivo e queste pagine non si
rileggono: da decidere insieme al passo 2b e alla traccia dei bandi non
estratti.

Numeri al 24/11/2026, letti dal database senza modificarlo:
- scarti "non è un bando" in `scansioni`: 56 (50 della Regione, 6 di
  Incentivi Italia). Per genere, dal motivo scritto dal modello:
  accreditamento, riconoscimento o iscrizione a un elenco 18; concorso,
  selezione di personale o incarico 15; graduatoria o esito 11; pagina
  informativa o di navigazione 8; manifestazione di interesse 1 (Art
  Bonus; un'altra, per un elenco di soggetti garanti, è contata tra gli
  elenchi); altro 3 (individuazione delle associazioni di gestori di
  scuole più rappresentative, due; un video-concorso con vincitore).
  Il motivo parla di vantaggio economico non diretto in 3: Art Bonus,
  catalogo dell'offerta formativa Just in Time, elenco dei soggetti
  garanti della linea di credito BEI. Per queste pagine il modello non
  scrive titolo e scadenza: si fermano al campo `natura`;
- bandi in archivio per tipo di beneficiario (bandi distinti): altra
  impresa 65, impresa turistica 41, impresa artigiana o commerciale 39,
  impresa agricola 28, professionista o autonomo 26, terzo settore 22,
  ricerca e formazione 21, comune 20, altro ente pubblico 17, unione di
  comuni 15, cittadini e famiglie 11, qualsiasi soggetto 1; senza righe
  di beneficiari 3. Con il solo tipo "cittadini e famiglie" 7 (uno,
  `incentivi-4939`, ha il tipo dal catalogo Incentivi Italia ma il
  titolo parla di contributi ai datori di lavoro); 4 hanno "cittadini e
  famiglie" insieme ad altri tipi. Per chi avvia un'impresa: la linea A1
  del bando PMI fino a 50 mila euro
  (`bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-7057d9`) e
  `incentivi-3373`, che sembra la stessa misura vista da Incentivi
  Italia (non verificato). Nessun bando trovato per chi non è ancora
  costituito.

## Età dell'impresa e chi deve ancora costituirla (24/11/2026)

Requisito nuovo del 24/11/2026, voce fuori dal Parcheggio, da decidere
insieme al passo 2b. Per rispondere a "ci sono bandi per chi vuole
aprire?" e "posso accedere appena apro?" serve sapere, per ogni bando,
da quanto tempo deve esistere l'impresa e se può fare domanda chi non è
ancora costituito. Esempio: linea A1 del bando PMI fino a 50 mila euro,
per imprese nate da non più di 36 mesi.

Cosa c'è oggi (24/11/2026), da una ricerca nei campi di testo di
`bandi`, `beneficiari_bando`, `interventi_bando`, `scadenze_bando` e
`testo_ricerca.csv`:
- nessun campo apposito. L'età dell'impresa compare per 2 bandi, che
  sembrano la stessa misura da due fonti: per il bando PMI
  (`…-7057d9`) solo in `beneficiari_bando.condizioni` e `frase` della
  riga dei liberi professionisti della linea A1 ("con inizio attività
  nei 36 mesi precedenti la data di presentazione della domanda"),
  mentre le righe delle imprese sono tutte della linea B; per
  `incentivi-3373` solo in `testo_ricerca.csv` ("la cui costituzione è
  avvenuta nel corso dei 36 mesi precedenti"), che l'utente non vede;
- `incentivi-3904` e `incentivi-4819`: "sede operativa costituita da
  almeno 6 mesi in una regione del Sud Italia", condizione per una
  quota a fondo perduto, solo in `testo_ricerca.csv`;
- le altre corrispondenze trovate non riguardano l'età dell'impresa:
  "costituite da almeno tre imprese/professionisti" (composizione delle
  forme associative, bandi Neve e internazionalizzazione), ATS
  "costituite o costituende" (raggruppamenti di soggetti), "start-up
  innovative" (`incentivi-7933`, dove i beneficiari sono gli incubatori).

## Profilo dei comuni (24/11/2026)

Voce nuova, fuori dal Parcheggio, idea di chi mantiene il progetto del
24/11/2026.

- Molti bandi rimandano a elenchi esterni da cui dipende l'accesso:
  comuni montani, Toscana diffusa, aree interne, territorio del GAL,
  Progetti di Paesaggio (caso: Toscana Art Bonus, riga del 24/11/2026 in
  "Letture dei siti e stato dei requisiti").
- Per ogni comune seguito una scheda con le sue appartenenze. Ogni voce
  ha valore, atto da cui viene, indirizzo e data dell'ultimo controllo;
  senza fonte resta vuota.
- Serve a rispondere a "il mio comune rientra?".
- Aggiornamento: a ogni scansione il codice confronta l'impronta della
  pagina di ciascun elenco e segnala se è cambiata, e segnala se un bando
  nuovo cita un atto più recente di quello in scheda; la lettura a mano
  si fa solo quando qualcosa cambia.
- Primo passo, a mano: i tre comuni pilota e l'Unione, con ogni dato
  verificato sull'atto ufficiale.
- Lo stesso vale per elenchi di soggetti non pubblici, se compaiono:
  fonte dichiarata e verificabile, valutati caso per caso.
- Collegata a "Documenti richiamati dal bando" del Parcheggio, dove la
  Toscana diffusa era già il primo documento da caricare.

### Primo contenuto verificato (24/11/2026)

Solo documento: nessuna tabella e nessun codice. Letto da chi mantiene il
progetto.

- Fonte: allegato A della deliberazione del Consiglio regionale della
  Toscana n. 10 del 12 marzo 2025, letto sul sito della Regione il
  24/11/2026. URL:
  https://www.regione.toscana.it/documents/d/guest/deliberazione-del-consiglio-n-10-del-12-03-2025-allegato-a-pdf
- Abetone Cutigliano (codice 47023): totalmente montano; aree interne
  classe F Ultraperiferico; Toscana diffusa (TD).
- Sambuca Pistoiese (codice 47018): totalmente montano; aree interne
  classe D Intermedio; Toscana diffusa (TD).
- San Marcello Piteglio (codice 47024): totalmente montano; aree interne
  classe D Intermedio; Toscana diffusa (TD).
- L'Unione di Comuni Montani Appennino Pistoiese (provincia di Pistoia)
  è composta da Abetone Cutigliano, Sambuca Pistoiese e San Marcello
  Piteglio. Fonte: pagina della Regione Toscana "Ambiti delle Unioni di
  comuni", https://www.regione.toscana.it/-/unioni-di-comuni-ambiti,
  letta il 24/11/2026.
- Avvertenza: appartenere all'Unione e usare un servizio associato
  dell'Unione sono due cose diverse (esempio: Marliana per la protezione
  civile); nel profilo vanno in righe distinte. Marliana non è nel
  territorio pilota: nessun valore scritto per quel comune.
- Da verificare, senza valore scritto: l'elenco nazionale dei comuni
  montani (visto solo su una bozza di febbraio, non sull'atto finale) e
  tutte le altre appartenenze indicate dalla ricerca del 24/11/2026.
- Regola: una riga entra nel profilo solo dopo la lettura dell'atto
  ufficiale, con atto, indirizzo e data di lettura.
- Esempio da tenere: la categoria A del bando dei giornali
  (`contributi-per-distribuzione-e-commercio-al-dettaglio-f747b7`) è
  riservata ai punti vendita con sede nella Toscana diffusa; i tre comuni
  pilota sono TD, quindi un punto vendita dei tre comuni può fare
  domanda.
- La ricerca per esteso sta fuori dal repository, in
  `dati-grezzi/ricerche/2026-11-24/`.

## Ordine delle voci intorno alla chiamata con il consulente pilota (24/11/2026)

Ordine approvato in chat da chi mantiene il progetto il 24/11/2026, in
vista della chiamata con il consulente pilota (prima settimana di
dicembre).

Criterio: prima della chiamata entra solo ciò che il consulente vedrebbe
come errore o che serve a fargli domande precise.

Prima della chiamata, in quest'ordine:
1. frammenti vicini passati al modello (passo 19e, rimedio 1; regola di
   chiusura nella voce qui sotto) e una ventina di risposte vere da
   leggere;
   (24/11/2026) fatta per la parte di misura e codice (V1 passa; vicini
   nel codice, spenti; "Passo 19e, rimedio 1", "Esito della lettura").
   Resta aperta "una ventina di risposte vere da leggere";
2. campo "sospeso" nello stato del bando: il caso degli incentivi ai
   datori di lavoro mostra "finestra aperta" prima della nota di
   sospensione ("Sospensioni e chiusure anticipate (24/11/2026)");
   (24/11/2026) fatta: tabella `sospensioni_bando`, sospensione prima di
   ogni "aperto", domande vere con la regola rispettata ("Campo
   strutturato della sospensione (24/11/2026)", "Esito delle domande
   vere");
3. controllo del passo 20;
4. incrocio delle due ricerche sui bandi con l'archivio, solo come elenco
   di fonti mancanti.

(24/11/2026) Candidati a salire prima della chiamata, da decidere al
prossimo giro, non ora: le citazioni con l'atto lungo ripetuto a ogni
frase e i falsi allarmi del verificatore (numero scritto dall'utente,
"1°" e "primo"). Visti nelle domande vere sulla sospensione ("Esito delle
domande vere", in "Sospensioni e chiusure anticipate (24/11/2026)").

(25/11/2026) Ordine deciso in chat da chi mantiene il progetto il
25/11/2026. Prima della chiamata, in quest'ordine:
1. citazioni ripetute (fatto, "Citazioni ripetute (25/11/2026)");
2. falsi allarmi del verificatore;
   (25/11/2026) fatto: "Verificatore per categoria (25/11/2026)";
3. errore tecnico mostrato all'utente;
4. "sospeso" accanto ai bandi citati;
5. poi la ventina di risposte vere, il controllo del passo 20,
   l'incrocio delle ricerche.

(25/11/2026) Ordine aggiornato, prima della chiamata:
1. citazioni ripetute (fatto);
2. verificatore (fatto);
3. inventario delle scritture ("Inventario delle scritture
   (25/11/2026)": misura fatta, correzioni da decidere);
4. errore tecnico mostrato all'utente;
   (25/11/2026) fatto;
5. "sospeso" accanto ai bandi citati;
   (25/11/2026) fatto;
6. poi le risposte vere, il controllo del passo 20, l'incrocio delle
   ricerche.

(25/11/2026) Restano, prima della chiamata: la ventina di risposte vere,
il controllo del passo 20, l'incrocio delle ricerche.

(25/11/2026) Superati, per decisione di chi mantiene il progetto: gli
ordini "prima della chiamata" qui sopra e il perimetro ridotto di
`docs/piano-19e.md` (sezione 4, domanda 7). La chiamata serve a
raccogliere informazioni, non a mostrare una demo finita; il 19e si fa
intero, senza scadenza, poi il passo 20 e il resto dell'ordine della
roadmap. Ordine e decisioni in `docs/piano-19e.md`, "Decisioni del
25/11/2026".

Dopo la chiamata, in aggiunta all'elenco qui sotto: date in formato
italiano e urgenza delle scadenze vicine.

Dopo la chiamata:
- dotazione in più quote (passo 2b);
- profilo dei comuni come tabella ("Profilo dei comuni (24/11/2026)");
- età dell'impresa ("Età dell'impresa e chi deve ancora costituirla
  (24/11/2026)");
- bandi annunciati;
- traccia dei bandi non estratti;
- etichette di tipo e destinatario;
- "ammesso se che" in `descrivi_beneficiari`, da provare su tutte le
  righe dei beneficiari, riportando quante cambiano;
- virgolette in `frase_nel_testo`;
- taglio dei documenti secondo la struttura ("Taglio dei documenti
  secondo la struttura del bando (22/11/2026)").

## Passo 19e, rimedio 1: regola di chiusura dei frammenti vicini (24/11/2026)

Regola scritta il 24/11/2026, prima di ogni misura del rimedio.

Premessa: la metà di controllo è stata aperta e letta il 23/11/2026, e il
rimedio è stato scelto guardando quei casi ("Passo 19d", punto 13, voce
21). Per questo non si può dare una percentuale nuova: il numero da citare
resta 78,6% (77 su 98, B, k=10, metà di controllo).

- **Costo**: il testo passato al modello, in media per domanda, non supera
  il doppio di oggi.
- **Danno**: su 10 domande a cui oggi l'app risponde bene, nessuna
  peggiora e il verificatore non segnala discrepanze nuove. Basta un
  peggioramento per non chiudere.
- **Beneficio**: sui 10 casi classificati "vicino" il 23/11/2026, almeno 6
  risposte giuste con la fonte giusta. Risultato atteso 8; tra 6 e 7 passa
  ma si annota come più debole del previsto.
- **Fermata**: al massimo due versioni provate. Se nessuna passa, il
  rimedio va in Parcheggio e si passa al rimedio 2.
- **Cosa si potrà dire se passa**: "non costa troppo e non rovina le
  risposte buone". Non che l'app è salita di percentuale.

### Misura senza modello e decisioni (24/11/2026)

Decisioni prese da chi mantiene il progetto il 24/11/2026, prima di
leggere le risposte. File di lavoro fuori dal repository, in
`dati-grezzi/prova/19e/`.

- (24/11/2026) Esito della misura senza modello (c-LR tutte, B, k=10,
  metà di controllo): V1 (frammento prima e frammento dopo) porta il
  frammento atteso in 9 casi "vicino" su 10, con rapporto 1,90 sul solo
  testo dei frammenti (1,38 sul messaggio intero); 119 prese su 119
  conservate. V2 (solo il frammento dopo): 6 su 10, rapporto 1,48. V3
  (prima e dopo dentro la stessa sezione) non misurabile: i frammenti non
  hanno un'indicazione di sezione o articolo. Degli altri 18 mancati
  nessuno recuperato. I mancati del 23/11/2026 sono 28, non 29: il
  ventinovesimo caso del file, il 2:102 dei fogli, è trovato ed è lì solo
  per la sezione degli allegati.
- (24/11/2026) Versione scelta: V1.
- (24/11/2026) Seconda e ultima versione, se V1 non passa: dipende da un
  conteggio sulle risposte V0. Se in V0 almeno 6 dei 10 casi "vicino"
  dichiarano di non trovare la risposta o di averla incompleta, la
  seconda versione è "vicini solo al secondo tentativo" (prima risposta
  con i 10 frammenti; se il modello dichiara di non trovare o che il dato
  è incompleto, seconda risposta con i vicini). Altrimenti la seconda
  versione è V1 solo sui primi 5 frammenti (7 su 10, rapporto 1,42).
  Motivo: V1 aggiunge i vicini anche dove non servono; la versione a due
  tentativi non tocca le domande già buone, ma funziona solo se il
  modello ammette di non trovare invece di rispondere sbagliando.
- (24/11/2026) Nota di metodo: i vicini sono una toppa al taglio a numero
  di caratteri; la cura è il taglio secondo la struttura, già in coda
  ("Taglio dei documenti secondo la struttura del bando (22/11/2026)").
- (24/11/2026) Il costo si giudica sul solo testo dei frammenti.
- (24/11/2026) Il danno si conta solo sulle domande risposte bene in V0;
  se sono meno di 8, se ne aggiungono con la stessa regola delle 10
  prese.
- (24/11/2026) Lettura alla cieca: le due risposte compaiono come A e B
  in ordine casuale.
- (24/11/2026) Variabilità: una domanda buona che peggiora si rilancia
  una volta (V0 e V1) e conta come danno solo se V1 è peggiore anche la
  seconda volta; se il beneficio esce 6 o 7 su 10 si rilanciano i casi
  "vicino" risultati giusti e contano solo quelli che restano giusti.
- (24/11/2026) Il codice nell'app si scrive solo se la versione passa la
  lettura; all'implementazione il contesto dell'app deve coincidere con
  quello dello script su 20 domande su 20, a data fissata.
- (24/11/2026) Voce nuova, da valutare: la catena non imposta la
  temperatura del modello, quindi la stessa domanda può dare risposte
  diverse.
- (24/11/2026) Voce nuova, da valutare dopo il rimedio 1: le pagine di
  Cultura e Sport Missione Comune hanno una sezione di domande frequenti
  con chiarimenti che l'avviso non contiene. Prima si misura l'app su
  quelle domande così com'è, poi si caricano come documenti e si
  rimisura. I testi stanno in `dati-grezzi/manuali/2026-11-24/` (file
  `faq_*.txt`), le domande candidate in
  `dati-grezzi/manuali/2026-11-24/domande_candidate_2026-11-24.xlsx`.
- (24/11/2026) Lettura delle risposte in due fasi. Fase 1: ogni risposta
  si giudica da sola, senza l'altra versione accanto, in due file da 20
  (`lettura_singole_2026-11-24_parte1.xlsx` e `_parte2.xlsx`): in ogni
  file ogni domanda compare una volta sola, con 10 risposte V0 e 10 V1
  mescolate, e la seconda parte si legge in un altro momento; la chiave
  sta in un file separato. Fase 2: il confronto tra le due risposte, A e
  B in ordine casuale (`lettura_a_mano_2026-11-24.xlsx`), solo dopo la
  fase 1. Il file da 40 righe `lettura_singole_2026-11-24.xlsx` resta ma
  non si usa: le due copie di una domanda vi stavano troppo vicine. I
  giudizi si uniscono con `unisci_giudizi.py`. Tutto in
  `dati-grezzi/prova/19e/`.
- (24/11/2026) "In parte" non conta come giusta per il beneficio.
- (24/11/2026) Per il danno, una presa che passa da "sì" in V0 a "in
  parte" o "no" in V1 è un peggioramento; il danno si conta solo sulle
  prese con "sì" in V0.
- (24/11/2026) "Dichiara di non trovare: in parte" vale come "sì" per la
  soglia dei 6 sui casi "vicino" in V0.
- (24/11/2026) Con un disaccordo tra i lettori vale la colonna
  "concordato", compilata dopo il confronto; finché ci sono disaccordi
  senza giudizio concordato, `unisci_giudizi.py` dà i conteggi per
  lettore ma non l'esito della regola.
- (24/11/2026) Applicazione più stretta della voce qui sopra, approvata
  da chi mantiene il progetto: `unisci_giudizi.py` lavora in due tempi.
  Prima scrive solo `disaccordi_<data>.csv` (numero, parte, colonna, i due
  giudizi; niente domanda né versione) e si ferma; il rapporto si
  produce solo quando ogni disaccordo ha il suo concordato. Un rapporto
  di un giro precedente, se lo script si ferma, si rinomina con
  "_superato_<ora>".

### Esito della lettura (24/11/2026)

- (24/11/2026) Esito di `unisci_giudizi.py` del 24/11/2026
  (`dati-grezzi/prova/19e/rapporto_giudizi_2026-11-24.txt`): costo 1,90,
  passa; danno passa, 10 prese su 10 restano giuste e nessuna
  discrepanza nuova del verificatore; beneficio passa, 8 casi "vicino"
  su 10 giusti con la fonte giusta in V1 (0 su 10 in V0). **V1 passa.**
  Verificatore, 20 risposte per versione: V0 verificato 178, non_trovato
  5, non_citato 5; V1 verificato 173, non_trovato 2, non_citato 0. Costo
  vero per 20 domande: V0 0,710 $, V1 0,838 $.
- (24/11/2026) In V0 tutti e 10 i casi "vicino" dichiarano di non trovare
  la risposta o di averla incompleta. È il dato di partenza per il
  rimedio 2 (segnale di poca sicurezza) e per il rimedio 3 (secondo
  tentativo).
- (24/11/2026) La versione "vicini solo al secondo tentativo" non si
  implementa: V1 è passata, e in costo le due strade si equivalgono (0,6
  centesimi in più sempre, contro 4,2 centesimi solo quando scatta, cioè
  pari intorno al 15% delle domande), mentre il secondo tentativo
  raddoppia l'attesa.
- (24/11/2026) Limiti dell'esito:
  - il beneficio era atteso, perché i casi erano noti;
  - danno zero su 10 domande e una sola esecuzione: esclude un danno
    frequente, non uno raro;
  - i lettori sono stati due modelli di famiglie diverse più un terzo di
    controllo, con arbitrato di chi mantiene il progetto su 3
    disaccordi, tutti sulla colonna "dichiara"; la lettura a mano di chi
    mantiene il progetto non è stata praticabile;
  - la misura è sull'ordine c-LR, non ancora nell'app;
  - restano fuori a mano 59 (frammento a due posti) e a mano 64.
- (24/11/2026) Terzo lettore, di controllo, fuori dallo script: differisce
  dal giudizio finale in 3 righe su 40. Due sulla colonna "dichiara":
  a mano 2:51 in V0 (finale "in parte", terzo lettore "sì") e a mano 64
  in V1 (finale "in parte", terzo lettore "no"). Una sulla colonna
  "giusta": fogli 64 in V0, una presa (finale "sì", con i due lettori
  d'accordo; terzo lettore "in parte"). Nessuna cambia l'esito: con il
  giudizio del terzo lettore le prese giuste in V0 sarebbero 9, sopra il
  minimo di 8, nessuna peggiorata; i casi "vicino" giusti in V1 restano
  8 e quelli che in V0 dichiarano di non trovare restano 10.
- (24/11/2026) Voce nuova, requisito per la scheda del bando e per le
  risposte: mostrare accanto a ogni dato la frase esatta del documento,
  perché una risposta sbagliata può sembrare giusta a chi non ha il
  testo davanti. Caso: obblighi "dopo il saldo" dati al posto di quelli
  "fino al saldo".
- (24/11/2026) Voce nuova: `unisci_giudizi.py` dovrebbe dire quali righe
  hanno un concordato non ammesso e cosa contengono (oggi dà solo il
  numero). Il caso reale è stato un "sì" salvato da Excel con una
  codifica diversa.

### Codice (24/11/2026)

- (24/11/2026) I vicini sono nel codice e spenti: `con_vicini` in
  `src/recupero_documenti.py`, `RecuperoIbrido.frammento` in
  `src/retrieval.py`, la chiamata in `prepara` di `src/chains/rag.py`,
  l'interruttore `SPOSTAMENTI_VICINI = ()` in `src/config.py`; test in
  `tests/test_vicini.py`. Si accendono con `(-1, 1)` nel passo 19e,
  insieme all'ordine c-LR e al filtro per bando: sono misurati solo
  sull'ordine c-LR in condizione B. Su Postgres serve ancora la query
  nuova per prendere un frammento da (fonte, chunk_num); finché manca,
  con Postgres i vicini restano spenti anche a interruttore acceso.
- (24/11/2026) Controllo di coincidenza: sulle 20 domande della lettura,
  a data fissata al 24/11/2026 e con l'interruttore acceso dallo script,
  il contesto prodotto dalla catena coincide carattere per carattere con
  quello passato al modello dallo script di misura (risposte V1): 20 su
  20 (`dati-grezzi/prova/19e/controllo_contesto_app.py`). Con
  l'interruttore spento, contesto, documenti e origini della catena su
  Chroma sono identici a quelli del codice dell'ultimo commit prima della
  modifica, su 22 domande (le 2 di `confronta_recupero` e le 20 della
  lettura).
- (24/11/2026) Incidente: un controllo fuori dal repository ha aperto il
  Chroma vero invece di una copia. È cambiata solo la tabella interna
  `acquire_write` (il registro dei blocchi di scrittura); i dati,
  confrontati tabella per tabella con la copia del 19d, sono identici. Lo
  script ora lavora su una copia. **Regola da ricordare: ogni script di
  misura apre una copia del Chroma, mai l'originale.**

## Citazioni ripetute (25/11/2026)

Difetto visto nelle domande vere sulla sospensione ("Esito delle domande
vere", 24/11/2026): il `riferimento_atto` degli incentivi ai datori di
lavoro (sette decreti più la sospensione) ripetuto per intero a ogni
frase, 4 o 5 volte per risposta.

- (25/11/2026) Fatto: `accorcia_citazioni` in `src/citazioni.py`,
  chiamata solo da `mostra_risposta` in `app/app.py`, con l'interruttore
  `ACCORCIA_CITAZIONI` in `src/config.py`. La prima citazione di ogni
  etichetta resta intera; le successive con la stessa descrizione
  diventano "(fonte: [L])", o "(fonte: [L], pag. N)" se cambia solo la
  pagina. Restano come sono: più etichette nella stessa parentesi,
  descrizioni diverse per la stessa etichetta, "fonte: profilo
  dell'ente", citazioni senza descrizione o non riconosciute dagli schemi
  del verificatore. ISTRUZIONI non cambia. 16 test nuovi in
  `tests/test_citazioni.py`.
- (25/11/2026) Regola di chiusura, con la funzione vera, su 226 risposte
  salvate (40 del passo 19e, 4 della sospensione, 182 delle 26
  registrazioni dei lotti 1-3; il lotto 4 non è stato aperto):
  1. stesse etichette nello stesso ordine: 226 su 226;
  2. descrizione lunga una volta sola per etichetta: 226 su 226, con le
     due eccezioni dichiarate; 15 risposte le toccano (13 con più
     etichette nella stessa parentesi, 2 con descrizioni diverse per la
     stessa etichetta);
  3. testo fuori dalle citazioni identico: 226 su 226;
  4. funzione spenta, testo identico a oggi: 226 su 226;
  5. bandi citati identici: 182 su 182;
  6. verificatore e bandi citati ricevono il testo intero: prova con
     AppTest sull'app intera, fatta fallire una volta passando loro il
     testo accorciato.
- (25/11/2026) Il numero onesto: risparmio 46-52% nelle risposte sugli
  incentivi; su 226 risposte media 7,5%, mediana 2,9%. Il difetto è
  concentrato sui bandi con una catena di atti lunga; nella risposta
  tipica le citazioni occupano circa un quinto del testo (media 20,5%,
  mediana 19,6%) e questo accorciamento ne toglie poco.
- (25/11/2026) Perché il verificatore riceve sempre il testo intero: sul
  testo accorciato perderebbe 348 controlli di atti e 321 di date scritti
  nelle citazioni ripetute, e cambierebbe i raggruppamenti delle fonti in
  2 risposte (lotto 1 P10, lotto 3 C17), perché le distanze tra le
  citazioni si accorciano.
- (25/11/2026) Nota: rieseguito sulle fonti salvate, il verificatore dà
  l'esito salvato in 217 risposte su 222 (le 4 della sospensione non
  hanno le fonti). Le 5 differenze sono nelle prime due registrazioni del
  lotto 1 del 14/11 (`2026-11-14_114121`, `2026-11-14_140416`); non
  controllate riga per riga.
- (25/11/2026) Da decidere dopo la lettura delle risposte vere per il
  consulente: citazioni ridotte alla sola etichetta ed elenco "Fonti
  citate" sotto la risposta, scritto dal codice con i dati del database.
  Chiude anche il vuoto della colonna Fonti, dove l'atto di un bando non
  è collegato alla sua etichetta (le fonti del blocco Dn sono didascalie
  senza etichetta).
- (25/11/2026) Più avanti: permettere "(fonte: [L])" nelle ripetizioni
  dentro ISTRUZIONI (oggi "Usi sempre questa forma esatta, anche quando
  ripeti un dato già citato"), con regressione contro la baseline.
- Script, misure e uscite fuori dal repository, in
  `dati-grezzi/prova/citazioni/` (`misura_citazioni.py`,
  `differenze_verifica.py`, `chiusura_funzione_vera.py`).

## Verificatore per categoria (25/11/2026)

Nasce da un caso reale ("Esito delle domande vere", 24/11/2026): nella
risposta "dopo" alla domanda sulla persona con disabilità la finestra
successiva è scritta "dal 2027-01-11 al 2027-01-10 (anno 2028)" invece
che al 2028-01-10, con esito VERDE, perché 2027-01-10 compare nella
fonte come fine dell'altra finestra. Il dato è vero, il ruolo è
sbagliato: il controllo di presenza non lo può vedere.

- (25/11/2026) Proposta di chi mantiene il progetto: passare dal
  controllo di presenza al controllo per categoria. Ogni dato si cerca
  nella parte della fonte che parla di quella cosa: scadenze, importi,
  requisiti, beneficiari, atti.
- (25/11/2026) Da dove si parte: dai casi in cui il ruolo si riconosce
  con certezza. Gli intervalli di date "dal X al Y", dove la fine prima
  dell'inizio è un errore senza bisogno della fonte, e dove la coppia
  deve corrispondere a una finestra della fonte, non solo i due estremi
  presi uno per uno. I tipi distinti già separati dall'archivio: nella
  riga di un bando scadenze, finestre, importi minimi e massimi,
  percentuale e dotazione sono scritti dal codice con frasi fisse, e il
  loro ruolo è certo.
- (25/11/2026) Limite: capire la categoria del dato nella risposta
  richiede di leggere la frase. Le parole vicine bastano solo nei casi
  chiari ("scade il", "dal … al …"); "dal" da solo vale anche per un
  evento ("verificatisi a partire dal 14/03/2025"), una sospensione o un
  requisito ("licenziati dal 1° gennaio 2021").
- (25/11/2026) Legame con il "Taglio dei documenti secondo la struttura
  del bando": per i frammenti dei documenti la categoria della fonte
  viene dal titolo della sezione o dell'articolo a cui il pezzo
  appartiene, che il taglio a livelli darebbe per ogni pezzo. Finché il
  taglio non c'è, il controllo per categoria vale solo per le righe dei
  bandi.
- (25/11/2026) Misura senza modello su 226 risposte salvate (40 del
  19e, 182 dei lotti 1-3, 4 della sospensione con le fonti ricostruite
  dal database): 14 intervalli di date con i due estremi nella fonte; 1
  con la fine prima dell'inizio, ed è il caso reale; nessun altro
  intervallo che non corrisponda come coppia a una finestra della fonte.
  183 date dopo "scade il / scadenza / fino al / entro il" citate con la
  riga di un bando: nessuna è un altro campo della riga. Script e uscite
  fuori dal repository, in `dati-grezzi/prova/verificatore/`.
- (25/11/2026) Censimento degli allarmi sulle 226 risposte, senza
  modello: 31 "non trovato", classificati a mano uno per uno. Famiglia A,
  numero scritto nella domanda: 6 (57 due volte, 26, 120 tre volte; la
  domanda degli alveari scrive "centoventi" in lettere). B, variante di
  scrittura della stessa data o dello stesso numero: 8 ("1° gennaio" e
  "primo gennaio", "quaranta", "€. 34,00", orari con la virgola, "punto
  7" contro il titolo di sezione "7."). C, famiglia nuova: 9. D,
  calcolato dal modello: 0, la famiglia non esiste nei dati. E, davvero
  assente: 8 (codice ATECO 56 o 56.10 dalla conoscenza del modello).
  Tre allarmi su quattro erano falsi (23 su 31). Elenco e classificazione
  in `dati-grezzi/prova/verificatore/` (`allarmi_2026-11-25.csv`,
  `classificazione_a_mano_2026-11-25.csv`).
- (25/11/2026) Famiglia nuova: dato abbinato alla citazione del punto
  successivo. In un elenco, "- «EU-Blending» (fonte: [D1.8]): … delibera
  704/2025.⏎- «Obbligazioni» (fonte: [D1.9])": il 704 sta dopo la
  citazione del suo punto, e il verificatore lo cercava nella citazione
  che lo segue, quella del punto dopo. Dei 12 "presente invece in", 9
  erano questa famiglia e 3 coincidenze; nessuno un errore vero del
  modello.
- (25/11/2026) Misure sui ruoli. Intervalli di date: 14 con i due
  estremi nella fonte citata, 1 allarme vero (il caso reale, fine prima
  dell'inizio), nessun falso. Regola larga, ruolo della data dalle parole
  vicine: 34 allarmi, 34 falsi su 34 (orari, "a partire dal" di un evento
  nel titolo, fine di un intervallo letta come apertura, apertura solo
  nella nota, "scaduto dal", "sospeso dal", "licenziati dal"): non
  implementata. Ruoli di scadenze e importi dalle frasi fisse delle righe
  dei bandi: 0 effetti su 302 dati (183 scadenze, 119 importi e
  percentuali), rinviati.
- (25/11/2026) Corretto, in `src/verification/controllo.py`,
  `src/normalizzazione.py` e `app/app.py`:
  1. un dato in un punto d'elenco va con la citazione del suo punto, anche
     se la citazione dopo lo contiene (`citazioni_del_dato`);
  2. varianti di scrittura: "primo" nelle date; numeri in lettere solo
     davanti a un'unità ("quaranta anni", "cinquantuno per cento"); "€."
     prima dell'importo; orari con la virgola dopo "ore", e dopo "alle" e
     "dalle" con virgola o punto; ATECO a due livelli dopo la parola
     "ATECO" letto come un codice solo;
  3. la domanda al verificatore (parametro `domanda`, passato dall'app):
     una quantità non trovata nella fonte ma scritta nella domanda, anche
     in lettere, ha l'esito `dalla_domanda`, né presente né allarme; date,
     importi e percentuali della domanda restano al controllo normale;
  4. intervalli "dal X al Y": fine prima dell'inizio rossa anche senza
     fonte; estremi nella fonte citata ma non della stessa finestra
     rossi, con il dettaglio "estremi presenti, ma non della stessa
     finestra";
  5. una quantità con la forma di un anno (1900-2099) si accetta anche
     tra gli anni della fonte (seconda fermata, sotto).
  50 test nuovi in `tests/test_verifica_ruoli.py`, con le righe vere dei
  bandi; ognuno fatto fallire una volta senza la modifica, salvo le
  protezioni che valgono prima e dopo (il caso 4 nella frase, come nella
  demo del 24/11; la riga che non è un punto d'elenco; "1°"; "ore 9.30";
  il 57 senza domanda; la finestra giusta).
- (25/11/2026) Regola di chiusura, riesecuzione sulle 226 risposte (222
  più le 4 della sospensione con le fonti ricostruite), verificatore
  dell'ultimo commit contro quello nuovo; le registrazioni dei lotti non
  si riscrivono:
  - allarmi rossi: 31 prima (8 veri, 23 falsi), 8 dopo (7 veri, 1
    falso). Restano: 6 della famiglia E (l'ATECO 56.10 da quattro
    allarmi a due, dichiarato), il caso 3 ora rosso, "punto 7" ancora
    rosso, dichiarato. Spariti 26 righe, cioè 24 al netto dell'ATECO,
    ciascuno elencato con famiglia e motivo; nati 3, il caso 3 e i due
    "56.10";
  - casi reali: 1 e 2 spariti, 3 rosso, 4 rosso (test);
  - risposte con esito ROSSO: 22 prima, 6 dopo (4 della famiglia E, 1
    "punto 7", 1 il caso 3); 11 passano da rosso a verde, 6 da rosso ad
    arancione per i "non citato" che avevano già;
  - "non citato": 29 prima, 27 dopo; i 2 tolti sono quantità della
    domanda (57, 120), ora "dato della domanda";
  - esiti "dato della domanda": 8.
  Previsione rifatta dopo il controllo sugli alveari (A 6, E 8):
  spariscono 24 al netto, nasce 1; misurato uguale.
- (25/11/2026) Due fermate. Prima: lo schema nuovo degli orari dopo
  "alle" con i due punti prendeva "alle 25:61", che un test esistente
  vuole letterale; corretto restringendo lo schema a virgola e punto,
  senza toccare il test. Seconda: con "primo gennaio 2021" ora data, il
  2021 della fonte è passato dai numeri agli anni, e "dal 2021," (con la
  virgola, quindi una quantità) è diventato un falso allarme; corretto
  accettando una quantità con la forma di un anno anche tra gli anni,
  solo nel confronto in `presente`. Lo schema degli anni non è cambiato.
- (25/11/2026) Nuova linea di base: da oggi i numeri del verificatore non
  sono confrontabili con quelli registrati prima del 25/11/2026. Per i
  confronti futuri (taglio a livelli, ordine c-LR nell'app) vale la
  riesecuzione di oggi sulle 226 risposte, in
  `dati-grezzi/prova/verificatore/` (`chiusura.py`,
  `chiusura_uscita_2026-11-25.txt`).
- (25/11/2026) Cosa promette il verificatore: dice se numeri, date,
  importi e atti della risposta compaiono nella fonte citata; non dice se
  la risposta è completa o se risponde alla domanda. Testi per l'utente
  cambiati di conseguenza: "1 dato citato non è stato trovato nella fonte
  indicata." / "N dati citati non sono stati trovati nella fonte
  indicata." più "Controllare a mano prima di riutilizzare la risposta.";
  verde "N dati presenti nella fonte citata."; sotto la verifica, sempre,
  "Il controllo riguarda numeri, date, importi e atti: dice se compaiono
  nella fonte citata, non se la risposta è completa."; il dato della
  domanda come nota senza colore. La parola "verificati" non compare più
  nei testi per l'utente (anche nel messaggio arancione). Sotto un rosso,
  dove sta il dato: in nessuna fonte, in un altro bando, in un altro
  documento, in un altro punto dello stesso documento (sempre rosso).
  Test esistenti toccati, solo le asserzioni su queste frasi:
  `tests/test_verifica.py` (tre) e `tests/test_pannello_verifica.py`
  (una).
- (25/11/2026) In coda. Verifica per unità della risposta, punto d'elenco
  o frase, come forma generale: ogni dato si confronta con le citazioni
  della sua unità, non con la più vicina in caratteri; l'abbinamento al
  punto d'elenco di oggi ne è il caso più semplice. Ogni script che salva
  risposte vere salva anche documenti ed esiti, come i lotti: le 4 della
  sospensione si sono misurate solo ricostruendo le fonti dal database.
  "Punto 7" e gli altri casi strutturali (il numero di una sezione nel
  titolo del pezzo) rimandati al taglio a livelli.
- (25/11/2026) Limite noto: più un numero è corto, meno vale averlo
  trovato nella fonte. Casi visti: il 57 trovato in un'altra riga; il 56
  trovato in "fra 56 giorni", lo stato del bando calcolato dal codice,
  che fa parte del testo di confronto di ogni frammento. Misura sulle 226
  risposte ("Inventario delle scritture (25/11/2026)", parte F): 147
  numeri di una o due cifre con esito presente (86 quantità, 57
  percentuali, 4 importi); 134 hanno nella fonte la stessa parola vicina
  (l'unità dopo o la parola prima); i 13 senza, letti a mano, non sono
  coincidenze (3 righe di tabella, 4 altre scritture come "quaranta
  anni" o "€. 34,00", 2 "/00" di "cinquemilioni/00" letti come il numero
  0, 3 numeri d'atto o di titolo presenti davvero, 1 "under 35"). In
  media il 4% dei numeri da 10 a 99 compare nella fonte citata (mediana
  1%, massimo 23%): è la probabilità che un numero di due cifre sbagliato
  passi lo stesso. Le quantità di una cifra la risposta non le controlla.
  Una coincidenza vera non si può escludere da qui: la stima vale per un
  errore a caso, non per un errore vicino al valore giusto.
- (25/11/2026) Ritocchi al pannello della verifica, da fare con il
  prossimo compito sull'app: le date di un intervallo rosso non compaiono
  tra i dati presenti; messaggio arancione al singolare e al plurale;
  etichette dei tipi in parole per l'utente.
  (25/11/2026) Fatti, solo in `app/app.py` (vedi `fatto.md`, "Fatti il
  25 novembre 2026"). Le forme "dato/i" e "citato/i" nascono in
  `giudizio` del verificatore e lì restano: le accorda il pannello. Il
  tipo "letterale" ("21/27") non ha un'etichetta nell'elenco deciso e
  resta col suo nome; un importo come "5.000 euro" il verificatore lo
  legge come quantità, e il pannello lo mostra come "numero".

## Inventario delle scritture (25/11/2026)

Nasce dai casi del 25/11/2026 ("Verificatore per categoria"): scritture
che il verificatore non riconosceva ("primo gennaio 2021", "alle 16,00",
un codice ATECO letto come due numeri, "del 12 marzo 2025, n. 10").
Invece di aspettare la prossima, si è guardato come sono scritte le cose
in tutto il materiale salvato. Solo misura: il codice non cambia.

- (25/11/2026) Materiale, senza modello, senza rete, senza Postgres, il
  Chroma solo in copia: 163 pagine delle scansioni (1.011.364 caratteri;
  7 pagine salvate due volte contate una); 25 PDF del registro, letti con
  pypdf e puliti come al caricamento (2.184.183 caratteri, di cui
  1.097.982 dell'elenco dei codici ATECO); 7 testi copiati a mano,
  domande frequenti comprese (67.446); 1.322 righe delle colonne di testo
  dei CSV di `data/processed` (444.035). Esclusi: gli elenchi delle
  scansioni, i testi delle ricognizioni, le 13 pagine dei bandi salvate
  con i PDF, la copia `.bak` e `scansione.log`.
- (25/11/2026) Ogni forma è letta da due lati, sul solo testo della
  forma: come la fonte (`valori`, `date_degli_atti`, `intervalli`) e come
  la risposta (`trova_dati`). "Non riconosciuta": letta male, a metà o per
  niente in almeno metà delle occorrenze, da almeno uno dei due lati.

| Parte | Forme trovate | Non riconosciute | Occorrenze toccate |
| --- | --- | --- | --- |
| A. Date, orari, importi, percentuali | 38 | 7 | 187 su 6.730 |
| B. Intervalli di date | 110 intervalli | 4 scritture | 41 intervalli su 110 |
| C. Codici | 16 | 4 | 3.472 su 12.702 (3.455 nell'elenco ATECO) |
| D. Riferimenti normativi | 36 | 11 | 1.057 su 4.894 |
| E. Titoli nei 25 PDF | 6 schemi | 4 PDF non affidabili | 16 PDF affidabili, 5 non servono |
| F. Soglie | 592 numeri dopo un confronto | solo conteggio | 147 numeri corti, 0 coincidenze |

- (25/11/2026) A. Riconosciute tutte le forme frequenti: date in cifre,
  in lettere, con "1°" e "primo", ISO; orari con "ore" e con "alle";
  importi con € o "euro" prima o dopo, "mila", "milioni", "€."; per
  cento. Non riconosciute: numeri in lettere davanti a una parola che
  il codice non conosce come unità (143: "due tranche", "tre linee");
  orari con i secondi (16: "ore 23:59:59" letto 23:59 più il numero 59,
  "23.59.59" letto come un codice); date spezzate dall'estrazione del PDF
  (23: "06-⏎02-1996", "21 maggio 202 7"); periodi con il secondo anno a
  due cifre (3: "a.s. 2025-26"); mese abbreviato (1: "10 SET 2026"); anno
  a due cifre (1). Mai trovate: "h 12" (le 5 "h" sono "Allegato 1H" e
  "48 h" di validità), "EUR", migliaia con spazio o apostrofo, k€ e M€,
  giorno in lettere. "21/27" e "LR 32/02" letti come letterali, come
  previsto.
- (25/11/2026) B. Su 4.314 date, l'espressione davanti dice il ruolo con
  certezza solo con l'orario: "fino alle ore … del" (20 su 20 scadenza
  della domanda), "a partire dalle ore … del" (12 su 12 apertura),
  "entro e non oltre le ore … del" (14 su 16 scadenza), "dalle ore …
  del" (11 su 12 apertura); e "del" dopo un numero d'atto (20 su 20).
  Senza orario no: "entro il" 8 su 20 scadenza della domanda (gli altri:
  stipula del mutuo, liquidazione, progetto definitivo, registrazione a
  un evento); "dal" 7 su 20 apertura; "a partire dal" 12 su 20 (gli altri
  requisiti ed eventi: "licenziamento a partire dal", "verificatisi a
  partire dal"); "a decorrere dal" 1 su 8; "tra il" quasi sempre il
  periodo di un evento (8 su 12, predazioni). Campioni letti a mano in
  `campioni_parte_b.txt`. Scadenze relative ("entro 30 giorni dalla
  pubblicazione"): 165, in 41 bandi; 7 di questi senza una data preceduta
  da una parola di scadenza (3 sono gruppi di PDF il cui termine può stare
  solo sulla pagina del bando, da controllare). Nell'archivio 11 bandi su
  116 senza scadenza in data, tutti a sportello. Intervalli: 41 su 110
  non letti come coppia da `intervalli`: primo estremo senza anno (20,
  "dal 1 febbraio al 31 maggio 2025"), inciso tra parentesi tra le due
  date (8, "dal 7 novembre (giorno successivo alla pubblicazione…) fino
  al"), secondo estremo dopo "ed entro il" (5), trattino tra due date
  (3), altro (5). Restano senza il controllo della coppia, non danno
  falsi allarmi.
- (25/11/2026) C. ATECO a tre livelli (9.183, quasi tutti nell'elenco) e
  con la lettera di sezione ("I 55.1") letti come un codice; a due
  livelli senza la parola "ATECO" letti come un decimale (3.455
  nell'elenco, 12 fuori); "sezione B" e "codici 38, 39, 41" (divisioni a
  due cifre in un elenco) non letti come codici. "ATECO 56" senza punto:
  mai nel materiale. CUP con la forma piena: 1. NACE solo come parola (8),
  CPV, CIG e codice ISTAT mai. Codici degli interventi ("SRA29",
  "SRD01"): 81, la fonte ne legge il numero (29), la risposta no.
  Identificativi che possono essere di persone, non riportati: nessun
  codice fiscale alfanumerico; 7 numeri di 11 cifre (partita Iva o codice
  fiscale di un ente) in 5 documenti, 2 PDF e 3 testi copiati a mano.
- (25/11/2026) D. Riconosciuti: "art. N", "articolo N", "art. N, comma
  M", "L.R. N/aaaa", "DGR N/aaaa", "D.Lgs. N/aaaa", "Reg. (UE) n.
  651/2014", e gli atti "n. N del data" (fonte 349 su 349). Non
  riconosciuti: atto con la data prima del numero (594: "legge 7 agosto
  1990, n. 241", "D.Lgs. 6 settembre 2011, n. 159", "del 12 marzo 2025, n.
  10"), letto come una data più un numero da entrambi i lati; "n. N del
  data" senza il nome dell'atto (120) e "BURT n. N del data" (58), atti
  per la fonte, data più numero per la risposta; nel lato della risposta
  anche qualifiche che `SCHEMA_ATTO_TESTO` non conosce ("DELIBERA G.R. n.
  990 del …", "delibera giunta regionale 409 del …", "decreto Arti 1189
  del …", "decreto legislativo 385 del …", "n. n."): 158 occorrenze in
  forme altrimenti riconosciute; "punto 6.1" e "paragrafo 2.1" (168)
  letti "punto 6" e "par 2", il sottopunto si perde; "artt. 46 e 47" (74)
  letti come numeri; "Reg. (UE) 2016/679" con il numero sotto le 4 cifre
  (77) letto come due numeri; "n. 61/R" (30) letto come il numero 61.
  "Allegato A" (1.558), "lettera f)" (77), "comma 2" da solo (61): non
  sono valori, il codice non li legge.
- (25/11/2026) F. Numeri dopo un confronto ("almeno", "fino a",
  "massimo di", "inferiore a", "under", "over"…): 592 in 182 documenti.
  A che cosa: euro 25%, termini in giorni, mesi o anni 24%, età 13%,
  percentuali 9%, punti 4%, abitanti 3%, persone o progetti 3%, superfici
  2%, dipendenti 1%, altro 16%. Numeri corti: vedi "Limite noto" in
  "Verificatore per categoria (25/11/2026)".
- (25/11/2026) Script, uscite e occorrenze fuori dal repository, in
  `dati-grezzi/prova/inventario/` (`materiale.py`, `inventario.py`,
  `struttura.py`, `numeri_corti.py`, `inventario_uscita_completa_2026-11-25.txt`,
  `forme.json`, `occorrenze/`).

## Risposte vere sulla demo (25/11/2026)

- (25/11/2026) Lettura di 20 risposte vere sulla demo: 13 buone, 5
  oneste ma generiche, 1 con esito giusto e strada sbagliata, 1
  sbagliata. Nessun dato inventato, nessun bando scaduto dato per aperto.
- (25/11/2026) I tre difetti principali:
  1. manca la profondità sulle spese ammissibili, perché gli avvisi non
     sono online: conferma la priorità del 19e;
  2. la ricerca per nome che non trova e si ferma: l'utente descrive il
     bando con parole sue ("il bando per chi fa il miele") e l'app lo
     prende per un titolo;
  3. l'importo della domanda segnato in rosso ("30 mila" del prestito
     dell'utente, non trovato nella fonte citata): lo stato
     "dalla_domanda", limitato alle quantità il 25/11/2026, è risultato
     troppo stretto alla prima risposta vera.
- (25/11/2026) Correzione di una ipotesi fatta in chat: l'ordinamento
  "per cosa" (passo 4) non risulta il difetto principale, perché il
  bando giusto viene trovato quasi sempre.
- (25/11/2026) Difetti minori:
  1. "Bandi che non ho potuto valutare" con un bando estraneo alla
     domanda;
  2. la frase "Se a chiedere fosse il Comune" in una risposta a
     un'impresa;
  3. il dato dell'utente sugli abitanti scartato a favore di quello
     dell'ente;
  4. l'urgenza segnalata solo a volte;
  5. le date nel formato tecnico;
  6. il pannello della verifica con i pezzi di frase tagliati.
- (25/11/2026) Decisione di chi mantiene il progetto: l'app offre tutte
  e due le strade, la domanda complessa diretta e il percorso a passi;
  con la domanda diretta, se è incerta sul bando, mostra i candidati e
  chiede quale. La scheda del passo 22 deve essere raggiungibile
  dall'elenco e dalla domanda diretta.
- (25/11/2026) Le risposte da mostrare al consulente pilota come esempi:
  l'edicola, Sport Missione Comune in forma associata, il circolo e lo
  SPID, il disoccupato di 57 anni, la domanda del consulente pilota
  sulle rievocazioni.

## Ricerca per nome e parole comuni (25/11/2026)

Nasce dal secondo difetto della demo ("Risposte vere sulla demo",
sopra): l'utente descrive il bando con parole sue ("il bando per chi fa
il miele") e l'app lo cerca come un titolo, non lo trova e si ferma.
Misure senza modello; script e uscite in
`dati-grezzi/prova/risposte-vere/2026-11-25/` e
`dati-grezzi/prova/parole-ricerca/`.

- (25/11/2026) Falsi risultati della ricerca per nome, trovati e
  corretti (fatto, vedi `fatto.md`). Il passo del titolo confrontava il
  testo cercato anche dentro le parole, e due parole con le stesse 5
  lettere iniziali valevano simili a qualunque lunghezza. Prima e dopo,
  sulle 36 parole comuni dell'insieme di misura:

  | parola | prima | dopo |
  |---|---|---|
  | api | apistiche e "capitale" (incubatori) | nessuno |
  | ristorante | "ristoro per acquisto gasolio" | nessuno |
  | trattore | "trattamento dei rifiuti" (scaduto) | nessuno |
  | prestito | "prestazioni veterinarie" e due "prestatori" | i due "prestatori" (limite noto) |

  Restano uguali i veri: apicoltura, edicola, albergo, strada, impianti
  sportivi, assunzione. I 116 titoli usati come testo cercato e i 12
  parametri salvati di `dettaglio_bando`: identici.
- (25/11/2026) Soglia scelta: parole intere nel passo del titolo, e
  prefisso comune solo se le lunghezze differiscono al più di 2
  lettere (`DIFFERENZA_SIMILE`). Con 1 si perdeva "fondo strade" nelle
  4 risposte salvate (strade e stradali differiscono di 2 lettere).
  Una regola più stretta (la parola più corta senza la vocale finale
  all'inizio della più lunga) toglieva anche "prestatori" ma perdeva
  "apicoltura" (apicoltori): scartata.
- (25/11/2026) Limiti noti, che una regola sulle lettere non separa,
  documentati da un test ciascuno: "rifugio" trova le "Case rifugio"
  (stessa parola, altro significato); "prestito" trova "prestatori"
  (stesse 5 lettere, 2 di differenza). Serve il significato.
- (25/11/2026) Regola stretta per i bandi dati come trovati, larga per
  i titoli simili. Motivo: un bando trovato è un'affermazione, un
  titolo simile è un suggerimento dichiarato come tale. L'ha fatta
  emergere "campo sportivo": con la regola stretta anche nei simili
  spariva il Bando Sport Missione Comune ("sportivo" e "sport", 3
  lettere) e saliva primo "Nuovo sportello Net Zero". Limite noto:
  tra i titoli simili "sportivo" assomiglia ancora a "sportello" (Net
  Zero resta nell'elenco, dopo il Bando Sport).
- (25/11/2026) Ripiego sul testo unito del bando (fatto): quando nessuna
  strada trova un bando, si cercano tutte le parole nel titolo, nei
  beneficiari (la frase del bando e le righe di `beneficiari_bando`) e
  negli interventi dei bandi non scaduti. Il risultato sono candidati,
  con `trovato=False` e il motivo per ciascuno ("trovato per 'mutuo',
  'agevolato' (nel bando 'agevolabile') nei beneficiari; 'impianti',
  'sportivi' negli interventi"), mai un bando trovato per nome. In
  coda, i titoli simili che non sono già tra i candidati. Misura: tra i
  tre insiemi cambia solo C12 ("impianti sportivi mutuo agevolato"),
  che porta a Sport Missione Comune; nessun candidato nuovo tra le
  altre parole comuni; "pulmino" resta senza risultati.
- (25/11/2026) Tappa 3, parole comuni per trovare un bando: decisione di
  chi mantiene il progetto, niente elenco di corrispondenze tenuto a
  mano, perché non regge quando i bandi aumentano. Ordine delle strade,
  dalla più solida: C, testo completo del bando (pagina salvata e
  avvisi); A, note esplicative ATECO dell'Istat; B, parole scritte da
  un modello al caricamento, solo per ciò che resta scoperto. Motivo
  dell'ordine: una parola presa dal testo del bando ha una fonte
  (file e pagina), una parola scritta da un modello no. Il progetto si
  conferma dopo la ricerca (sotto).
- (25/11/2026) Strada C, misura senza modello. Testo completo per 42
  bandi non scaduti su 51 (pagina salvata per 37, avvisi per 13; i 9
  senza testo vengono tutti dal catalogo Incentivi Italia). Il
  confronto di `dettaglio_bando` sul testo completo fa troppo rumore
  ("giornali" trova "giorni" in 34 bandi, "trattore" trova "trattato"
  in 13): sul testo completo serve la stessa parola, o la stessa con
  la vocale finale diversa (arnia e arnie; "ch" e "gh" come "c" e "g":
  biblioteca e biblioteche), e mai una parola che non distingue i
  bandi ("banda" non trova "bando"). Con questa regola, sulle 46
  parole (le 36 più arnie, miele, alveari, telecamere,
  videosorveglianza, pulmino, costumi, insegnante, caldaia, bagni): 71
  coppie parola-bando, 30 pertinenti, 38 no, 3 dipende da chi chiede.
  Dove entrerebbe davvero, cioè come ripiego per le parole che oggi non
  trovano niente: 20 coppie, 8 pertinenti; con "almeno 2 occorrenze nel
  bando" 10 coppie, 8 pertinenti, nessuna pertinente persa, 2 no ("API"
  come sigla nel bando sui dati, "trattore stradale" in una tabella).
  Arnie, miele, alveari portano al bando per le aziende apistiche
  (negli allegati A1 e A5 del decreto 14025); "banda" all'educazione
  musicale di base; "biblioteca" a Cultura Missione Comune; "costumi"
  alla rievocazione storica. "Caldaia" è nel bando Pmi 50 mila
  (allegato 1B, solo nel registro), ma oggi `dettaglio_bando` la trova
  già, nel testo dei beneficiari, nell'«Avviso fondo di garanzia energie
  rinnovabili», scaduto nel 2021: il ripiego non entra. La ricerca nel
  testo di oggi non esclude gli scaduti; da decidere se debba farlo.
  Restano scoperti palestra e campo sportivo (il bando Sport scrive
  "impianto sportivo"), telecamere, pulmino.
- (25/11/2026) Parole citate per escluderle: una regola sulle parole
  vicine ("esclus", "non ammiss"… nei 200 caratteri prima) ha preso
  l'unico caso con tutte le occorrenze escluse ("frigo bar" tra le
  spese escluse), ma non si può dire con una regola in generale: le
  esclusioni stanno spesso in una sezione intitolata "spese non
  ammissibili" con l'elenco righe più sotto, fuori da qualunque
  finestra, e "ad eccezione di" rovescia il senso. Si potrà dire con il
  titolo della sezione, che darà il taglio a livelli.
- (25/11/2026) Strada C nell'app online, senza copiare il testo delle
  pagine nel repository pubblico: una tabella di parole per bando,
  `parole_bando` (id_bando, parola normalizzata, fonte: pagina o
  avviso, file, pagina del PDF, occorrenze), costruita al caricamento.
  Dimensioni oggi: 34.283 righe su 42 bandi (5,4 MB in CSV), 16.131 con
  almeno 2 occorrenze (2,6 MB). A mille bandi sarebbero circa 400.000
  righe: non un CSV del repository, ma una tabella costruita dal
  caricamento in Postgres. Le parole vengono dagli avvisi: va decisa
  con il 19e (vedi "Mai" in CLAUDE.md). Nel blocco dei dati il motivo
  si leggerebbe "trovato perché nell'avviso compare 'arnie' (allegato
  A1, pag. 4)".
- (25/11/2026) Strada A, senza rete. L'elenco ATECO tra i PDF è
  l'allegato 4 dei decreti 9505 e 9506 del 30/04/2026 (236 pagine):
  solo codici e titoli, ATECO 2025 e 2022 a confronto, con
  l'ammissibilità al bando; non le note esplicative. Ci sono
  "Apicoltura", "Stampa di giornali", "Bar e altri esercizi simili
  senza cucina", "Attività di servizi di ristorazione"; non ci sono
  "miele", "arnie", "ristorante", "edicola", "agriturismo". Codici ATECO
  nei dati strutturati: 2 bandi aperti su 51 (giornali, turismo); la
  parola "ATECO" nel testo completo: 8. Versioni citate dai bandi:
  2007 (4 bandi) e 2025 (3); la 2022 compare solo nell'allegato 4,
  come colonna di corrispondenza (da verificare che sia
  l'aggiornamento 2022 della 2007). Le note Istat della ricerca sono
  del 2025: per i bandi che citano la 2007 serve una tabella di
  raccordo. Le note non si scaricano in questo giro.
- (25/11/2026) Strada B, solo disegno: script
  `dati-grezzi/prova/parole-ricerca/genera_parole.py` (`--stima`,
  `--solo N`, ripresa per impronta, `--finto`, `--foglio`), provato solo
  con il modello finto. Al modello titolo, beneficiari e interventi;
  regole: solo parole e modi di dire, da 5 a 12, nessun numero, data,
  importo, sigla o nome di ente, niente parole di qualunque bando, niente
  parole del titolo, mai cose escluse; controlli meccanici sulla
  risposta. Uscita: un CSV con id_bando, parole, origine "modello",
  modello, data, impronta dell'ingresso, rigenerato solo quando
  l'ingresso del bando cambia; in `data/processed` solo dopo il foglio
  di controllo a mano (una riga per bando, colonna "c'entrano? sì / no
  / togliere questa"); tabella accettata vuota nelle copie più vecchie.
  Uso solo nel ripiego, dopo R1, e solo per cercare; motivo nel blocco:
  "trovato per le parole di ricerca (scritte da un modello, non dal
  bando)". Contro il rumore: un'espressione nelle parole di più del 5%
  dei bandi è segnata nel foglio, soglia da tarare dopo la generazione.
  Filtro suggerito dalla ricerca (Doc2Query--): tenere un'espressione
  solo se, cercata sull'archivio, ritrova il proprio bando tra i primi;
  si farebbe con la ricerca per significato che c'è già, al
  caricamento. Costo stimato per 113 bandi: circa 1,6 dollari con
  claude-opus-5-5 (tetto 4,8 con il massimo di token), 0,8 con
  claude-sonnet-5-5.
- (25/11/2026) Cosa dice la ricerca fatta in parallelo (Studio esterno,
  25/11/2026, non verificato a mano): le parole comuni spesso sono già
  nel testo completo e negli allegati, non nel titolo; l'unico
  vocabolario pubblico che collega parole comuni e codici sono le note
  esplicative ATECO 2025 dell'Istat (voce dell'apicoltura: "produzione
  di miele, cera di api, propoli"); le parole generate senza filtro
  introducono rumore. Limiti dichiarati dalla ricerca stessa: le prove
  sui portali non sono state eseguite (incentivi.gov.it ha bloccato
  l'accesso, il portale toscano ha ignorato il parametro di ricerca);
  le misure pubblicate sono solo in inglese o su testi tradotti a
  macchina. La misura della strada C, sopra, conferma il primo punto
  sui nostri bandi: arnie, miele e alveari sono negli allegati del
  bando apistico.
- (25/11/2026) In coda, dopo la chiamata: requisiti dell'utente ("ho 26
  anni" e simili). Sono requisiti, non parole da cercare. Parte 1: il
  modello li estrae dalla domanda libera, il codice li confronta con i
  campi dei bandi, l'app mostra cosa ha capito e l'utente corregge;
  niente filtro obbligatorio, niente salvato. I campi li decidono i
  bandi (i requisiti più ricorrenti), ognuno con la frase del bando; un
  solo elenco di campi per bandi, domanda e profilo. Un campo vuoto non
  esclude un bando ("requisito da verificare"). Collegato a "Età
  dell'impresa e chi deve ancora costituirla (24/11/2026)".
- (25/11/2026) In coda, parte 2, privata: profilo generale sempre attivo
  (tipo di soggetto, sede, forma giuridica, anno di costituzione,
  dimensione, settore) più una scheda per ogni progetto, legata ai
  bandi scelti, con i campi che quel bando chiede, aggiunti via via.
  Niente si salva senza conferma dell'utente; ogni dato salvato ha data
  e origine. La scheda mostra cosa manca. Dati nel database con
  accesso, mai nel repository; informativa, consenso e cancellazione
  da verificare sulle fonti ufficiali prima di aprire a utenti veri.
- (25/11/2026) Importo della domanda nel verificatore (fatto): lo stato
  "dalla_domanda" vale anche per importi, percentuali e date, con la
  guardia: solo quando la risposta scrive il valore come dato
  dell'utente, possessivo più nome più "di" o "da" subito prima ("il
  suo prestito di 30 mila"). Rischio misurato prima: senza la guardia,
  il valore della domanda attribuito alla fonte ("il bando vale fino a
  50 mila (fonte: [D1])" con la fonte che dice 40.000) perdeva
  l'allarme. Sulle 226 risposte salvate: nessun cambiamento, perché
  nessuna domanda salvata contiene un importo, una percentuale o una
  data che la risposta ripete; la chiusura poggia sui 6 test nuovi, un
  caso per verso. Limite: le date si scrivono di solito con "del" o
  "dal" ("la sua iscrizione del 3 marzo"), che la guardia non prende;
  allargarla alle preposizioni articolate va misurato con risposte
  vere che lo contengano.
- (25/11/2026) Soluzioni provvisorie dichiarate e cosa le sostituirà: i
  frammenti vicini, dal taglio a livelli; le citazioni accorciate,
  dall'elenco "Fonti citate" scritto dal codice; le correzioni a mano
  sui bandi, dalla protezione dalle riestrazioni. Stima per sostituirle
  tutte: tre o quattro settimane dopo la chiamata, con l'avvertenza che
  il 19d aveva richiesto il triplo del previsto.
- (25/11/2026) Collo di bottiglia dichiarato: l'insieme di domande
  scritte da persone con la risposta attesa. Senza quello le
  sostituzioni si costruiscono ma non si misurano; vale anche per le
  strade A, B e C (le 36 parole sono scelte da chi sviluppa, non da chi
  chiede).
- (25/11/2026) In coda: la frase "in archivio non c'è un bando con quel
  nome" della regola "BANDO CERCATO PER NOME" in `ISTRUZIONI`, da
  cambiare con una regressione contro la baseline (la domanda sul
  pulmino non nominava un bando); l'istruzione del router "per il suo
  oggetto", che manda a `dettaglio_bando` anche domande che non
  nominano un bando, da cambiare con la stessa regola.
- (25/11/2026) Regola decisa da chi mantiene il progetto: a una domanda
  generica l'app indica i bandi pertinenti in breve e rimanda alla
  scheda per i dettagli; a una domanda specifica su un bando nominato
  risponde in modo esauriente. Quando ci sarà la scheda del passo 22,
  il rimando sostituisce frasi come "non trovo l'elenco delle spese
  ammissibili".
- (25/11/2026) Ordine prima della chiamata, aggiornato: parole comuni
  per trovare un bando, poi il passo 20, poi l'incrocio delle ricerche.
- (25/11/2026) Ordine aggiornato, supera la riga "Ordine prima della
  chiamata, aggiornato" qui sopra. La strada C dipende dagli avvisi
  online (le parole delle arnie stanno negli allegati A1 e A5, che oggi
  sono solo nel Chroma locale), quindi confluisce nel resto del 19e.
  Ordine: resto del 19e, poi il passo 20, poi l'incrocio delle ricerche.
  Se alla chiamata il 19e non è finito, il caso delle arnie si mostra
  come limite dichiarato, con la causa misurata: le parole ci sono negli
  allegati del bando, che non sono ancora nell'app online. Piano in
  `docs/piano-19e.md`.
- (25/11/2026) Decisione sulla strada C: al posto della tabella
  `parole_bando` fatta in casa, ricerca lessicale con uno stemmer
  italiano raggruppata per bando (testo pieno di Postgres con
  configurazione italiana, o il BM25 che il recupero ibrido usa già sui
  frammenti). Motivi: plurali e derivati gestiti bene; ordina i
  candidati invece di tagliarli; cresce con l'archivio. La tabella
  `parole_bando` (voce "Strada C nell'app online" qui sopra) resta
  descritta come alternativa scartata. Come si fa, con i limiti
  trovati leggendo registro e codice: `docs/piano-19e.md`, tappa 6b.
- (25/11/2026) Nota di metodo sulla misura della strada C: la soglia
  "almeno 2 occorrenze nel bando" è stata scelta dopo aver visto i
  risultati sulle stesse parole, quindi l'esito (10 coppie, 8
  pertinenti, nella voce "Strada C, misura senza modello" qui sopra)
  vale come indicazione e non come misura. Un motivo in più per
  ordinare i candidati e non tagliarli.
- (25/11/2026) Decisione su "caldaia": quando la ricerca nel testo trova
  solo bandi scaduti, il ripiego tra i non scaduti deve entrare lo
  stesso. Si fa dentro il 19e, con misura sui tre insiemi (le 36 parole
  comuni, i 116 titoli usati come testo cercato, i 12 parametri salvati
  di `dettaglio_bando`).
- (25/11/2026) La strada A scende di priorità: i codici ATECO sono nei
  dati strutturati di 2 bandi aperti su 51.
- (25/11/2026) Strada B: lo script `genera_parole.py` resta fuori dal
  repository e non si lancia finché le strade C e A non sono misurate;
  il modello e l'opzione di ripiego su un altro modello sono da
  verificare prima.
- (25/11/2026) In coda, dopo la chiamata: prova di DSPy su un solo pezzo
  (la scelta del router o l'estrazione dei requisiti dalla domanda), in
  una cartella a parte, con misura prima e dopo e un insieme di prova
  separato. Non sulla catena principale finché non c'è il nuovo insieme
  di domande con la risposta attesa.
- (25/11/2026) Tappa 6a fatta (vedi `fatto.md`): ripiego tra i non
  scaduti anche quando i bandi trovati sono tutti scaduti, interruttore
  `RIPIEGO_ANCHE_CON_SCADUTI` acceso. Sui dati di oggi non cambia
  nessuna risposta: nei 69 casi "solo scaduti" dei quattro insiemi
  nessun bando non scaduto ha tutte le parole cercate. Serve quando ne
  arriverà uno (per esempio la nuova edizione di un bando neve).
- (25/11/2026) Correzione di un dato della voce "Strada C, misura senza
  modello" qui sopra: le "46 parole" sono 40 distinte, perché 6 delle
  10 aggiunte (arnie, miele, alveari, telecamere, videosorveglianza,
  pulmino) erano già tra le 36 (letto da `strada_c.py`, che toglie i
  doppioni).
- (25/11/2026) Scoperta sulla "caldaia": la parola non compare
  nell'«Avviso fondo di garanzia energie rinnovabili». `dettaglio_bando`
  lo trova perché "caldaia" e "calda" (in "acqua calda sanitaria", negli
  interventi) hanno le stesse 5 lettere iniziali e lunghezze entro 2
  lettere: è lo stesso limite noto di "prestito" e "prestatori". La
  frase "oggi `dettaglio_bando` la trova già, nel testo dei beneficiari"
  della voce sulla strada C va letta così: un falso risultato, negli
  interventi. Da tenere presente nella 6b: uno stemmer dovrebbe
  separare "caldaia" da "calda" (da verificare con lo stemmer scelto);
  la regola delle 5 lettere no.

## Prova di memoria su Streamlit (25/11/2026)

Dettaglio in `docs/prova-memoria.md` (copiato su `main` il 27/11/2026;
pagina e test restano sul ramo `prova-memoria`).

- (25/11/2026) Esito in breve. Versione 1 dei requisiti (torch 2.15.0 di
  PyPI, 15 pacchetti `nvidia-*`): massimo dall'avvio dopo il passo 7
  1887,0 MB, processo dopo il passo 7 1727,4 MB, riordino di 30 coppie
  2,862 s di mediana. Versione 2 (torch 2.15.0 per processore, nessun
  pacchetto `nvidia-*`): 1523,6 MB, 1228,8 MB, 2,539 s. Limite letto dal
  contenitore 3072 MB in entrambe, nessun riavvio, i 30 punteggi del
  passo 6 identici e nello stesso ordine.
- (25/11/2026) La regola scritta prima (sotto 540 MB a regime, sotto
  690 MB di massimo, riordino sotto 10 s) non passa in nessuna delle due
  versioni, e non si cambia: le soglie venivano dal minimo di 690 MB
  della documentazione di Streamlit, mai misurato, mentre il limite letto
  dal contenitore è 3072 MB.
- (25/11/2026) Criterio di decisione per il quarto caso ("la regola non
  passa, ma l'app arriva in fondo"), scritto da chi mantiene il progetto
  dopo la versione 1 e prima della versione 2: massimo dall'avvio dopo il
  passo 7 sotto 2048 MB (due terzi di 3072), nessun riavvio, riordino
  sotto 10 s di mediana. Passa nella versione 2 con 524,4 MB di margine;
  nella versione 1 il margine era di 161 MB.
- (25/11/2026) Decisione di chi mantiene il progetto: motore in memoria e
  requisiti della versione 2. La riga di torch per processore va su
  `main` come compito a parte, con una verifica della demo dopo il
  riavvio.
- (25/11/2026) Streamlit Community Cloud è l'ambiente dei test e della
  demo, non quello definitivo: quando l'app sarà aperta a più utenti
  passerà a uno spazio a pagamento. Le soglie e il criterio della prova
  valgono per questo spazio e non sono requisiti del prodotto; al cambio
  di spazio la misura si rifà con la stessa pagina.
- (25/11/2026) Streamlit trova due file di requisiti, `requirements.txt` e
  `pyproject.toml`, e usa il primo (avviso nel registro
  dell'installazione). Oggi va bene; se `pyproject.toml` un giorno
  elencasse dipendenze, la scelta va ricontrollata.
- (25/11/2026) Per la fermata 5: con `pgvector` 0.5.0 la lettura dei
  vettori da Postgres (`register_vector`) restituisce un oggetto
  `pgvector.Vector`, non un array numpy, e va convertito (come fa
  `a_vettore` nella pagina di prova). E va misurata l'app vera, non solo
  la pagina: catena, LangChain, Anthropic, SQLite e sessioni nella prova
  non c'erano (stima di circa 150 MB in più, mai misurata).
- (27/11/2026) Riportato su `main`: `docs/prova-memoria.md` e la riga di
  torch della versione 2 in `requirements.txt` (vedi `fatto.md`). Restano
  da fare, a mano, dopo il push: la verifica della demo dopo il riavvio
  (nel registro dell'installazione torch con `+cpu` e nessun pacchetto
  `nvidia-`), la cancellazione dell'app di prova dal pannello e, con
  l'esito scritto qui, la rimozione del ramo `prova-memoria`, quando lo
  decide chi mantiene il progetto.
- (27/11/2026) Su `main` la riga di torch ha un marcatore più stretto di
  quello del ramo: `sys_platform == "linux" and python_version == "3.14"
  and platform_machine == "x86_64"` invece del solo `sys_platform ==
  "linux"`, perché la ruota è solo per Python 3.14 su x86_64 e con il
  marcatore largo un Linux con un altro Python o su ARM fallirebbe
  l'installazione. Questa forma **non è stata provata online prima del
  push su `main`**: la prova di memoria ha usato quella del ramo, e il
  compito del 27/11 è senza rete. Controllata solo in locale con il
  parser di `packaging` (vero su Linux 3.14 x86_64; falso su Linux 3.12
  x86_64, su Linux 3.14 aarch64 e sul PC) e con `pip install --dry-run
  --no-index`. Da guardare nel registro del primo riavvio della demo:
  `+ torch==2.15.0+cpu` e nessun pacchetto `nvidia-`. Se il marcatore
  risultasse falso online, l'installazione non fallisce: torch torna in
  silenzio quello di PyPI, con le librerie CUDA. Lo stesso succede se si
  cambia la versione di Python dell'app: la riga va cambiata insieme.
- (27/11/2026) Promemoria 1 della prova fatto (vedi `fatto.md`): gli
  avvisi si riconoscono da `sha256` (`e_frammento_di_avviso` in
  `src/recupero_documenti.py`), non da `id_bando`. Gli script di misura
  non sono stati toccati: dove distinguono gli avvisi usano già `sha256`.
  Con i vicini accesi, sulle 22 domande del 24/11, i blocchi dei mercati
  rionali spariscono in 8 domande e quelli degli avvisi restano uguali:
  va tenuto presente nella fermata 3. Promemoria 2 e 3 restano per la
  fermata 1 e la fermata 5.

## Venti domande sulle spese (27/11/2026)

Fermata 2 del resto del 19e (`docs/piano-19e.md`, sezione 8, "Correzione
a"). Le domande misurano il difetto 1 ("Risposte vere sulla demo
(25/11/2026)"): risposte oneste ma generiche sulle spese ammissibili. Le
domande restano fuori dal repository; qui vanno solo numero, data e
impronta del file.

- (27/11/2026) Foglio da riempire:
  `..\dati-grezzi\prova\19e\domande-spese\domande_spese.xlsx`, scritto da
  `prepara_foglio.py` nella stessa cartella (copia del Chroma e SQLite in
  sola lettura, nessun modello). Tre schede: "leggimi" (cosa scrivere e
  come), "bandi" (i 12 bandi con avvisi caricati come frammenti: id_bando,
  titolo, ente, chi può chiedere, cosa finanzia, stato al 27/11/2026,
  campi usati), "domande" (20 righe assegnate, con chi chiede da scegliere
  tra impresa, comune, associazione e privato, domanda e note vuote).
  Impronta sha256 del foglio vuoto, con la regola di assegnazione del
  27/11/2026 qui sotto:
  `4e96dcf4130fe34c162ebdecec1bfc92dce1402b52301207575468fcb1a98658`
  (sostituisce `a674a404…10acf`, il foglio con la prima versione della
  regola). Il file xlsx porta la data in cui è stato scritto: rigenerato
  dà un'impronta diversa anche senza cambiamenti nelle righe.
- (27/11/2026) Tutte e venti le domande si scrivono a mano, da chi
  mantiene il progetto. È la proposta della sezione 10 del piano; la
  correzione b prevedeva 14 domande dal foglio delle candidate e 6 a mano.
  Il foglio delle candidate non è stato aperto: le sue domande restano per
  il passo 25.
- (27/11/2026) Regola di assegnazione, scritta prima di guardare il
  contenuto degli avvisi (usa solo il numero di frammenti per bando, un
  metadato): una domanda per ciascuno dei 12 bandi; una seconda agli 8
  bandi con più frammenti di avviso, contando una sola volta i bandi della
  stessa famiglia e senza dare loro la seconda; 12 + 8 = 20. Righe 1-12 il
  primo giro, 13-20 il secondo, ciascuno in ordine alfabetico di
  id_bando. Due domande: apicoltura (165 frammenti), risorse genetiche
  agrarie (157), dati degli enti locali (79), Punti Digitale Facile (61),
  Cultura Missione Comune (50), Sport Missione Comune (47), educazione
  musicale (24), parcheggi (17). Una domanda: i due bandi Pmi per gli
  interessi (126 e 125), rievocazione storica (15), fondo strade (5).
  Nessun pareggio all'ottavo posto.
- (27/11/2026) La regola è stata cambiata il 27/11/2026, prima che
  esistesse una sola domanda, da chi mantiene il progetto. La prima
  versione ("una seconda agli 8 bandi con più frammenti", senza famiglie)
  dava due domande a ciascuno dei due bandi Pmi per gli interessi (7057d9
  e 8cd3ac), quasi gemelli: 4 domande su 20 a una sola famiglia. Le due
  domande liberate vanno ai bandi successivi per numero di frammenti,
  educazione musicale e parcheggi. I due bandi Pmi restano distinti, con
  una domanda ciascuno, e non si uniscono, perché distinguerli è una
  difficoltà nota del filtro per bando.
- (27/11/2026) Cosa c'è nella scheda "bandi" e cosa volutamente no. Chi
  può chiedere: `bandi.beneficiari`, o la sua prima frase (Cultura e Sport
  Missione Comune: la seconda frase ha i massimali del mutuo), o i
  soggetti di `beneficiari_bando` (apicoltura, Pmi fino a 50 mila,
  parcheggi), o `bandi.territorio` (fondo strade). Cosa finanzia: gli
  interventi di genere "intervento" di `interventi_bando`, mai quelli di
  genere "spesa" (che sono proprio le spese ammissibili: tre per Cultura e
  per Sport, sette per le risorse genetiche); senza interventi, il titolo.
  Stato: `stato_bando` con scadenze e sospensioni. Non ci sono spese
  ammissibili, percentuali, massimali né testo degli avvisi. Limiti
  dichiarati: il titolo di un bando Pmi contiene "fino 50 mila euro";
  l'apicoltura ha tra gli interventi "acquisto di attrezzature e sistemi
  di gestione"; per la rievocazione storica il titolo dice poco. Restano
  come sono, per decisione di chi mantiene il progetto (27/11/2026): sono
  cose che un utente vede nell'app prima di chiedere.
- (27/11/2026) Strada scelta per il "prima", approvata da chi mantiene il
  progetto: la catena dell'app in locale collegata a Postgres come la
  demo, lanciata da chi mantiene il progetto con `registra_risposte.py`
  (stessa cartella), sul commit della demo e con la cartella di lavoro
  pulita. La catena in locale sul Chroma non va bene, perché il Chroma ha
  gli avvisi. Router chiamato una volta, come nella demo; data fissata al
  25/11/2026 (tutti i 12 bandi erano aperti), la stessa per il "dopo".
  Il "dopo" costruirà la catena con la funzione dell'app (fermata 5 del
  piano). Stima: 0,036-0,043 $ a domanda,
  0,73-0,87 $ per 20. Lo script salva per ogni domanda risposta,
  frammenti e metadati, bandi citati, esito del verificatore, testo e
  decisione del router, dati delle interrogazioni, costo e momento; nel
  file `meta.json` commit, impronta delle istruzioni e del foglio, modello,
  data fissata e tetto. Provato solo con modello, router e recupero finti,
  e con la rete bloccata: 20 su 20 registrate; con un tetto di 0,01 $ si
  ferma prima della prima domanda; rifiuta un foglio con un'impronta
  diversa, il "prima" senza Postgres e una cartella di lavoro con
  modifiche.
- (27/11/2026) Chiave delle risposte (dove sta la risposta nell'avviso,
  file e pagina, o "non c'è"), decisa da chi mantiene il progetto: si
  prepara dopo il blocco del foglio, mai prima, e prima di leggere
  qualunque risposta, "prima" o "dopo". Senza modello si fa l'aiuto: per
  ogni domanda, le pagine candidate dell'avviso del suo bando con la
  ricerca per parole ristretta a quel bando. Con quell'aiuto due modelli di
  famiglie diverse preparano la chiave ciascuno per conto proprio; chi
  mantiene il progetto arbitra solo i disaccordi.
- (27/11/2026) Regola di lettura, scritta prima che esistano le risposte
  e approvata così da chi mantiene il progetto.
  Le due risposte di ogni domanda si leggono insieme, alla cieca: etichette
  A e B estratte a caso per domanda, senza sapere quale sia il "prima".
  Due lettori di famiglie diverse e arbitrato sui disaccordi, come il
  24/11. Ogni risposta prende una sola categoria, con la chiave accanto:
  "giusta e precisa" (dà quello che la chiave indica, con la fonte),
  "onesta ma generica" (non sbaglia ma non dà il contenuto, per esempio
  rimanda all'avviso), "non c'è, detto bene" (la chiave dice che non c'è e
  la risposta lo dice), "dato sbagliato" (un dato in contrasto con la
  chiave o senza fonte), "fuori tema". Esito, come nella fermata 5: nessun
  "dato sbagliato" nuovo nel "dopo"; il numero delle risposte "giuste e
  precise" prima e dopo si riporta senza soglia. L'esito del verificatore
  si riporta accanto, non sostituisce la lettura.
- (28/11/2026) Foglio bloccato il 28/11/2026: 20 domande, scritte a mano
  da chi mantiene il progetto. Impronta sha256 di
  `..\dati-grezzi\prova\19e\domande-spese\domande_spese.xlsx`:
  `21a6ae5ab8d4c7383b535721f8f1592ac1033ba7e49ac4751a235e65378e58a2`.
  Copia di sola lettura nella stessa cartella,
  `domande_spese_bloccato_2026-11-28_21a6ae5a.xlsx`, con la stessa
  impronta. Al momento del blocco il file risultava aperto in un altro
  programma (c'era il file di blocco `~$domande_spese.xlsx`): l'impronta
  è quella dei byte su disco, letti in condivisione senza scrivere; il
  foglio va chiuso senza salvare, altrimenti l'impronta cambia e
  `registra_risposte.py` rifiuta il lancio. Controlli di forma, sulla
  copia: tre schede; 20 righe compilate (righe 2-21, nessuna vuota),
  numerate da 1 a 20; id_bando e titolo uguali all'assegnazione del foglio
  vuoto (regola del 27/11/2026 qui sopra) in 20 righe su 20; "chi chiede"
  sempre tra i valori ammessi; nessuna riga con una nota (quindi nessun
  "la so").
- (28/11/2026) Caratteristiche dell'insieme, dichiarate da chi mantiene il
  progetto. Le domande sono casi plausibili scritti immedesimandosi in chi
  chiede, non casi reali raccolti. Tutte nominano il bando in modo
  esplicito: misurano il caso "bando noto, domanda di dettaglio", non
  quello delle parole comuni. Poche sono vaghe o mal poste, meno delle 5
  chieste dal leggimi, e non se ne aggiungono perché il file è già stato
  letto. Circa un quarto riguarda chi può accedere o a quali condizioni
  più che le spese in senso stretto: nella lettura va tenuto distinto.
  Molte chiedono se un progetto concreto rientra nel bando. Chi chiede:
  dichiarati 7 comune, 7 associazione, 6 privato, nessuna impresa; nel
  foglio bloccato risultano 8 comune (righe 4, 5, 6, 8, 9, 13, 14, 17),
  7 associazione (3, 7, 10, 12, 16, 18, 20), 5 privato (1, 2, 11, 15,
  19), nessuna impresa. Vale il foglio; la colonna non arriva all'app.
- (28/11/2026) Aggiunta alla regola di lettura, scritta dopo il blocco del
  foglio e prima che esista una sola risposta, "prima" o "dopo", decisa da
  chi mantiene il progetto. Motivo: molte domande chiedono se un progetto
  concreto rientra nel bando, e l'avviso spesso non nomina quel caso. Due
  categorie in più, accanto alle cinque della regola del 27/11/2026:
  "non c'è in modo esplicito, ma riporta la regola più vicina con la
  fonte" (la risposta dice cosa l'avviso non nomina, cita le voci ammesse
  più vicine con fonte e pagina, e lascia la conclusione all'ente o
  all'utente); "conclude senza fonte" (la risposta afferma che il caso è
  ammesso o escluso quando l'avviso non lo dice). "Conclude senza fonte"
  si conta come difetto. Esito, aggiornato: nessun "dato sbagliato" nuovo
  e nessuna "conclude senza fonte" nuova nel "dopo"; il numero delle
  risposte "giuste e precise" prima e dopo si riporta senza soglia.
- (28/11/2026) Requisito di prodotto, deciso da chi mantiene il progetto:
  davanti a un caso che l'avviso non nomina, l'app si avvicina con le
  citazioni e mai con le conclusioni. Riguarda `ISTRUZIONI`, che in questo
  giro non si toccano: da valutare dopo la fermata 5 del 19e, con le venti
  risposte come prova e con una regressione contro la baseline
  (`docs/piano-insieme-prova.md`).
- (28/11/2026) Correzione della voce "Caratteristiche dell'insieme" qui
  sopra: "dichiarati 7 comune, 7 associazione, 6 privato" era un errore di
  conteggio di chi ha preparato il compito, non una dichiarazione di chi
  mantiene il progetto. Vale 8 comune, 7 associazione, 5 privato, come nel
  foglio.
- (28/11/2026) "Prima" registrato da chi mantiene il progetto: 20 domande
  su 20, cartella
  `..\dati-grezzi\prova\19e\domande-spese\registrazioni\prima_2026-11-28_115825`,
  costo 0,976 $ (0,9755) contro la stima di 0,73-0,87 $, sotto il tetto di
  1,50 $. Letto solo `meta.json`; le risposte (file da 01 a 20) non si
  leggono fino alla fermata 5. Da `meta.json`: commit `0946db5`, senza
  modifiche non salvate; modello `claude-sonnet-5`; recupero `postgres`;
  data passata 2026-11-25; ente 90060100477; impronta delle istruzioni
  `03472bc0`, la stessa che dà il codice di quel commit; impronta del
  foglio `21a6ae5a…78e58a2`, quella del blocco; dalle 11:58:25 alle
  12:06:00; nessun fermo. Non torna solo il costo: in media 0,049 $ a
  domanda contro la stima alta di 0,0434 $ scritta nello stesso file,
  cioè il 12% sopra la stima alta (0,868 $ per 20). La causa non si cerca
  ora, perché servirebbe aprire i file delle risposte; per il "dopo" la
  stima si alza di conseguenza, e il tetto di 1,50 $ lascia margine.

## Insieme di domande nuovo, passo 25 (28/11/2026)

Dal documento di lavoro "insieme di domande nuovo" (28/11/2026), fuori dal
repository. Voce per il passo 25 della roadmap; vicine: "Insieme di prova:
dopo" (insieme generato) e "Ricerca per nome e parole comuni
(25/11/2026)", collo di bottiglia.

- (28/11/2026) Domande scritte da più modelli di famiglie diverse e in
  vesti diverse.
- (28/11/2026) Livelli etichettati: diretta, con sinonimi, vaga, presa
  alla larga, malformata, fuori tema.
- (28/11/2026) Gergo del mestiere e gergo amministrativo, presi da fonti
  reali.
- (28/11/2026) Chi legge l'avviso non scrive la domanda.
- (28/11/2026) Controllo del codice sulle parole in comune.
- (28/11/2026) Chiave verificata da una seconda famiglia.
- (28/11/2026) Metà chiusa con impronta.
- (28/11/2026) Le domande generate non sostituiscono quelle raccolte da
  persone.

## Fermata 1 del 19e: motore in `src/` (28/11/2026)

Piano in `docs/piano-fermata-1.md`, decisioni del 28/11/2026 nella sezione
omonima.

- (28/11/2026) Sotto-fermata 1.0 chiusa: lo script di misura congelato
  (impronta `216d67cc8abc`, uguale prima e dopo) rifà la taratura con
  189 righe su 189 uguali ai CSV salvati, a k=10 e a k=15, e 189 ordini
  di B su 189 uguali al 24/11. Trovati A / B a k=10: fogli 76 / 83, a mano
  69 / 78, come atteso. `ordini_riferimento.json` (336 ordini, quattro
  serie, in `..\dati-grezzi\prova\19e\fermata-1\riferimenti\`), sha256
  `f6c038498092a9a1246132c515801114522fcc3a8238055371b28815bd3420a9`, è
  il riferimento di R1 (decisione 4).
- (28/11/2026) Sotto-fermata 1.1: `src/motore.py`, non importato da
  nessuno. Contiene `Frammenti` (sempre ordinati per id, vettori in
  float32, con `to_numpy()` per i vettori di Postgres), `ArchivioChroma`
  (sola lettura, contesti dati da fuori fino alla 1.3), `RicercaEsatta`
  (prodotto scalare in float64, pari merito per id), `Motore` (BM25 con il
  contesto davanti, `cerca` di `RecuperoIbrido` ereditata,
  `cerca_nel_bando`), `Riordino` con `riordina` (coppie con il contesto
  davanti, ultima colonna dei voti, pari merito nell'ordine di prima,
  origine "riordino #n"), caricamento dei due modelli alle revisioni
  fissate (decisione 5), `versioni()` per il registro. I documenti
  restituiti hanno il testo pulito e i metadati del frammento, mai il
  contesto. In `src/config.py`: `ORDINE_C_LR = False`,
  `CANDIDATI_RIORDINO = 30`, modello e revisioni.
- (28/11/2026) Doppione da togliere (decisione 1): `testo_con_contesto`,
  `controlla_normalizzati`, `StoreEsatto` (in `src/` è `RicercaEsatta`),
  la costruzione del BM25 e `cerca_nel_bando` di `RecuperoMisura`,
  `riordina`, l'ordine per id di `esporta_frammenti` stanno sia in
  `scripts/diagnostica/misura_recupero_avvisi.py` sia in `src/motore.py`.
  Lo script resta il riferimento finché valgono gli ordini del 19d; il
  doppione si toglie, se si vuole, dopo la fermata 5 o al taglio a
  livelli.
- (28/11/2026) Test: `tests/test_motore.py`, 15 test (punti 1-5 e 7 della
  sezione 7 del piano, la parte del punto 6 sul motore, le revisioni dei
  modelli). Ognuno visto fallire con almeno una di 19 varianti del motore
  senza il pezzo che protegge. Restano alla 1.4 il punto 6 nella catena e
  il punto 8; alla 1.3 il punto 9.

## Parcheggio

Idee che non interrompono il lavoro in corso (nuova, 21/11/2026). Regola:
un'idea nuova interrompe il compito aperto solo se attacca un difetto
misurato, se costa di più farla dopo che adesso, e se si può misurare con
quello che c'è già. Altrimenti va qui, con due righe, e si riprende a
compito chiuso.

- **Addestramento del modello di embedding** sui testi dei bandi (era la
  strada 7 del punto 8 di "Passo 19d", con le sue condizioni). Attacca la
  ricerca per significato, che fa quasi tutto il lavoro. Aspetta le coppie
  domanda e frammento generate al caricamento e la decisione su dove
  pubblicare e mantenere il modello addestrato.
- **Glossario** (era la strada 6). Attacca le parole dell'utente diverse
  da quelle del bando ("chi alleva api" contro "aziende apistiche",
  "Passo 19d", punto 6). Aspetta fatti non ancora visti, perché scritto
  dopo la taratura sarebbe favorito. Termini raccolti il 23/11/2026
  ("Disegno dell'app", tre tipi di domanda): plafond, ESL, intensità di
  aiuto, riserve dell'appaltatore, cofinanziamento, accantonamento,
  commissioni di garanzia, linee del bando, spese generali, economie e
  ribassi di gara, lettera di endorsement, capofila, costi standard del
  personale, Autorità di Gestione, punteggio e graduatoria.
  (23/11/2026) Un glossario a mano cresce a ogni bando e va mantenuto:
  prima si prova il secondo tentativo con altre parole (roadmap, 19e).
- **Documento intero quando il bando è noto.** Attacca le risposte in più
  pezzi e il tetto dei 30 candidati ("Passo 19d", punto 4). Aspetta una
  decisione di chi mantiene il progetto, perché aumenta il testo di ogni
  risposta: da 983 a 37.352 token per bando ("Passo 19d", punto 11).
- **Insieme di prova grande** (voce di "Insieme di prova: dopo",
  aggiornamento del 20/11/2026). Attacca il rumore di un campione di 97
  fatti e le domande scritte da un solo modello. Aspetta la nuova
  baseline.
- **Revisione del metodo da parte di altri modelli.** Attacca gli errori
  di metodo che chi misura non vede. (Anticipata il 21/11/2026: si fa
  prima di aprire la metà di controllo, "Passo 19d", punto 13, "Prossimo
  compito".) Aspetta la chiusura del 19d; il
  documento che ne esce segue la regola delle revisioni esterne
  (intestazione e verifica a mano prima di salvarlo).
  (23/11/2026) Revisione 1 fatta il 23/11/2026: cinque punti, quattro
  accolti e uno in parte, da cui la regola in due decisioni ("Passo
  19d", punto 13, voce 19). Lo stesso giorno la classificazione dei
  mancati del controllo è stata ricontrollata alla cieca (voce 21).
- **Riordinatore più grande.** Attacca i fatti che i due riordinatori
  provati non portano nei primi 10 o 15. Aspetta la misura dei tempi del
  riordinatore piccolo su Streamlit Community Cloud (oggi 4-5 secondi a
  domanda con 30 candidati); il guadagno resta limitato dal tetto dei 30
  candidati, 81-82 fatti in B ("Passo 19d", punto 4).
- **Riga DOVE ricavata dal programma** (proposta del 21/11/2026):
  l'intestazione di paragrafo più vicina prima del frammento nel testo
  pulito, invece che scritta dal modello. Attacca i 23 riferimenti di
  paragrafo segnalati nella prima generazione ("Passo 19d", punto 13).
  Oggi non serve: sulla prova dell'A3 il controllo allargato dà lo
  stesso risultato. Aspetta un estrattore delle intestazioni, che non c'è.
- **Togliere solo la frase che viola** invece dell'intero contesto
  (proposta del 21/11/2026). Attacca il 29,6% di contesti esclusi nella
  prima generazione ("Passo 19d", punto 13). Non costa di più farla dopo.
- **Forme vicine anche dopo "altro:"** in ARGOMENTO (approvata il
  21/11/2026): applicare l'elenco delle forme vicine anche al testo che il
  modello scrive dopo "altro:" (caso dell'A3, frammento 0: "altro:
  intestazione del bando e indice delle sezioni"). Si fa nel prossimo
  compito di codice; l'elenco resta congelato fino a fine misura ("Passo
  19d", punto 13, regole), quindi va fatta prima della misura o dopo la sua
  fine.
- **Contesto dopo il testo invece che davanti** (21/11/2026). Attacca le
  coppie del riordinatore oltre 512 token, dove oggi a essere tagliata è la
  fine del frammento ("Passo 19d", punto 13, voce 8). Aspetta la decisione
  dopo le seconde domande a mano.
- **Solo BANDO e SERVE A al riordinatore** (21/11/2026). Sono le due righe
  senza le quali c-LR perde più fatti in B (76 e 78 contro 83 a k=10).
  Aspetta la decisione dopo le seconde domande a mano; sarebbe una variante
  scelta dopo i risultati.
- **Coppie oltre 512 token** (21/11/2026). Con il contesto nel
  riordinatore, circa una coppia su quattro (c-LR, A: 702 su 2909) supera il
  limite e viene tagliata. Da misurare quanto pesa prima di cambiare
  l'ordine o le righe.
- **Due imprecisioni del rapporto del contesto** (21/11/2026): il titolo
  "30 fatti" della sezione 6 è fisso anche quando le domande a mano sono
  meno (29); `VOCE_DEL_TIPO` porta "definizione" su "altro", mentre
  "definizioni" è una voce dell'elenco (fatto 2:46). Correzioni piccole, da
  fare a misura chiusa. (22/11/2026: il titolo fisso "30 fatti" è
  corretto; `VOCE_DEL_TIPO` resta.)
- **Documenti richiamati dal bando** (nuova, 22/11/2026). Attacca le
  domande che escono dal bando (esempio: "quali sono le risorse genetiche
  iscritte ai Repertori regionali?"), per cui oggi la risposta giusta è
  "il bando rimanda a quel documento, che non è tra quelli caricati"
  ("Disegno dell'app (22/11/2026)"). Aspetta il disegno dell'app.
  (23/11/2026) Esempio: "il mio Comune è nella Toscana diffusa?" ha la
  risposta negli atti regionali richiamati. La Toscana diffusa compare in
  almeno tre bandi (parcheggi, educazione musicale, apistici): è il primo
  documento richiamato da caricare.
  (24/11/2026) Collegata alla voce "Profilo dei comuni (24/11/2026)",
  fuori dal Parcheggio: le appartenenze dei comuni agli elenchi
  richiamati (Toscana diffusa compresa) stanno lì, con atto e data.
- **Domanda ripulita con un buco** (23/11/2026). La domanda ripulita dal
  titolo del bando lascia un buco nella frase (resta "al" seguito dai due
  punti o dal punto di domanda). Osservazione del revisore esterno; non è
  un difetto misurato.
- **Via di mezzo tra 30 candidati e tutto il bando** (22/11/2026), per
  esempio 60 frammenti dalla ricerca nel bando al riordinatore. Attacca
  il tempo delle T sui bandi lunghi ("Passo 19d", punto 13, voce 13).
  Fuori dal 19d per la regola di perimetro (voce 15); andrebbe misurata
  con una regola scritta prima.
- **Scartate il 22/11/2026**, con il motivo:
  - frammenti più grandi: il modello di embedding legge solo l'inizio
    (128 token, "Passo 19d", piano del 20/11, punto 1); i frammenti più
    corti del 20/11 andavano peggio (v3, B da 26 a 16 sui 40 fatti,
    punto 4); rifarli invalida le misure;
  - doppia ricerca con frammenti grandi e piccoli e voto: c'è già la
    fusione con il riordinatore; i pesi della fusione non spostavano
    niente (punto 4); due indici da mantenere.
- **Orario di ogni domanda nella misura** (22/11/2026). Lo script di
  misura registra la durata di ogni domanda ma non l'orario; aggiungere
  l'orario renderebbe applicabile la regola della sospensione del PC
  ("Passo 19d", punto 13, voce 13) in una futura misura dei tempi.
- **Docker per l'app** (27/11/2026, dalla prova di memoria del
  25/11/2026). Un'immagine con l'app e le sue dipendenze fissate, torch
  per processore compreso. Servirà al passaggio a uno spazio a pagamento,
  quando l'app sarà aperta a più utenti (Streamlit Community Cloud è
  l'ambiente dei test e della demo, "Prova di memoria su Streamlit
  (25/11/2026)"); lì la misura di memoria si rifà. Oggi non serve. Diversa
  dalla voce 11 dei Prossimi passi, Docker per Postgres con pgvector in
  locale.
