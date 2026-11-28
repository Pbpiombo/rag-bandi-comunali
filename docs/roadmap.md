# Roadmap

I documenti scritti prima del 18/11/2026 citano sezioni di questa roadmap che oggi stanno in docs/coda.md con il loro numero originale (Difetti del 14/11, Dopo la demo, Prossimi passi, In coda, priorità del consulente pilota, indicazioni del revisore tecnico) e in docs/fatto.md.

Stato al 28 novembre 2026. Da aggiornare alla fine di ogni passo.

Qui stanno solo stato, principi, ordine dei passi e decisioni prese. Il
lavoro chiuso è in `docs/fatto.md`; le voci in attesa, con il loro numero
originale, in `docs/coda.md`.

## Stato

- **Il 19d è chiuso dal 23/11/2026, sotto soglia** (`coda.md`, "Passo
  19d", punto 13, voci 19-21): c-LR tutte è la configurazione degli
  avvisi; gli avvisi vanno in produzione solo con il filtro per bando e
  con il "non lo trovo"; il numero da citare è 77 su 98 (78,6%), B, k=10,
  metà di controllo.
- **Il 19e è in corso dal 25/11/2026**, secondo `docs/piano-19e.md`,
  intero e senza perimetro ridotto (decisioni del 25/11/2026 nel piano).
  Fatte la tappa 6a, la prova di memoria e, il 28/11/2026, la fermata 1
  del rilascio 2: motore della misura in `src/motore.py`, collegato
  all'app dietro `ORDINE_C_LR`, spento (`docs/piano-fermata-1.md`).
  Prossima: la fermata 2, filtro per bando (`docs/piano-fermata-2.md`,
  proposta). Obiettivo: un'app che il consulente pilota possa
  provare tra gennaio e febbraio 2027, con buone fonti e buona qualità di
  risposta. La chiamata della prima settimana di dicembre serve a
  raccogliere informazioni (cosa chiede, da quali fonti), non a mostrare
  una demo finita.
- Baseline: la regressione finale del 16/11/2026 (commit `715b411`), 55
  domande in 4 lotti. La baseline del 16/11/2026 non corrisponde più
  all'archivio dopo il passo 2a (18/11/2026). Resta l'unico riferimento
  fino alla nuova registrazione delle 55 domande, dopo il passo 3.

Demo e riscontri del consulente pilota (18 e 19/11/2026), attese:
`docs/fatto.md`, "Spostato dalla roadmap il 23 novembre 2026".

Indicazioni del revisore tecnico (18/11): `docs/coda.md`, "Revisore
tecnico (18/11/2026)".

## Principi dell'architettura della risposta

- **"Per chi" è un filtro deciso dal codice**, a partire da chi chiede
  (ente del menu o tipo di privato). È un filtro largo, che esclude solo
  dove il bando esclude: `qualsiasi_soggetto` passa sempre (oggi
  `bandi_per_beneficiario` non lo fa passare, le interrogazioni per ente
  sì); un bando senza righe di beneficiari passa con un segno; i
  pertinenti persi dal filtro si misurano a parte.
- **"Per cosa" è un ordinamento**: tra i bandi rimasti, vicinanza a ciò
  che chi chiede vuole fare, su un testo di ricerca per bando (passo 17),
  con somiglianza di significato (embedding locali) più parole esatte,
  come il recupero ibrido dei documenti.
- **Il modello classifica i primi 10-15** (pertinente, generico possibile,
  no) con uscita strutturata; il codice decide la forma della risposta; il
  modello scrive.
- **I bandi generici stanno in una sezione separata, con un tetto.**
  "Generico" dipende dal bisogno, non dal bando. Il criterio delle
  famiglie di bisogno è un'ipotesi da provare al passo 4, non un
  principio.
- **"Chi chiede" è un passo esplicito** (passo 18).
- **Il principio copre le domande "cerca bandi".** Prima di progettare il
  passo 9 si elencano gli altri rami: scaduti recenti, bando nominato,
  scadenze e importi, documenti.
- **Filtro e ordinamento servono soprattutto ai privati.** Per i Comuni
  contano il passo 9, la copertura e gli scaduti recenti.
- **Funzioni in sequenza**; LangGraph solo con cicli o rami.
- **Il settore di chi chiede, se manca, si chiede con un menu** e si
  conserva come dato della sessione, non come memoria della chat.
- **Prova**: su 54 bandi aperti un'impresa generica ne ammette 25; sei
  bandi compaiono in 29 domande private su 30
  (`docs/piano-insieme-prova.md`, "Regola delle misure (18/11/2026)").

## Ordine dei passi

I numeri dei passi non cambiano. **Ordine di esecuzione** (25/11/2026; il
precedente, del 23/11, è in `docs/fatto.md`, "Spostato dalla roadmap il
25 novembre 2026"): 0, 1 (etichette), 2a, 17, 19a-19d (fatti); resto del
19e secondo `docs/piano-19e.md` (tappa 6a, fatta il 25/11; prova di
memoria su Streamlit e torch solo per processore, fatte il 25/11 e il
27/11, `docs/prova-memoria.md`; rilascio 2 in cinque
fermate, la prima fatta il 28/11; tappe 6b e 7); 20; 25 (insieme di domande nuovo); 24 (taglio a
livelli); le altre fonti (C, in sequenza, non in parallelo, con la
scansione regolare e il passo 23); 22; 21. Il passo 21 si fa comunque
prima di dare il link della demo a chiunque oltre al consulente pilota.
Restano da collocare, nell'ordine relativo di prima: 1 (resto: "chi
atteso", domande A, attese con polarità), 2b, 4, 3, nuova baseline, 5,
18, 8, 9; la loro posizione si decide dopo la chiamata con il consulente
pilota. Perché la nuova baseline viene dopo il passo 19: "Decisioni
prese" (19/11/2026).

### A. Misure e dati, senza modello salvo dove indicato

0. **Regola delle misure.** Tutte le misure di A e B su una copia
   congelata dei CSV e con data di riferimento 2026-11-16; data fissa e
   SQLite congelato sono un compito di codice a parte, prima della nuova
   baseline (`docs/piano-insieme-prova.md`, "Regola delle misure").
   Parti (a) e (b) fatte (`docs/fatto.md`); la parte (c) è una regola,
   non codice. La prima copia congelata si fa dopo il passo 2b.
   Fatta invece il 24/11/2026, prima di aggiungere i bandi della
   scansione, per decisione di chi mantiene il progetto
   (`dati-grezzi/archivi/2026-11-24_e26e2e30/`); dopo il 2b se ne farà
   un'altra (`docs/piano-insieme-prova.md`, "Copia congelata e opzioni").
1. **Etichette.** Schede in `dati-grezzi/etichette/2026-11-18_152225`, per
   50 domande: le 5 domande A non hanno schede e restano misurate con le
   attese attuali.
   - Resta da fare: la colonna 'chi atteso' per domanda e le 5 domande
     A (etichette fatte il 19/11/2026, `docs/fatto.md`).
   - Due o tre domande anche al consulente pilota.
   - Dalle etichette nascono le attese con polarità (proposto, non
     proposto); `forma_attesa` si calcola dalle etichette. Oggi una
     citazione fatta per escludere un bando conta come trovata (caso C03).
   - Serve un'opzione di `diagnosi_attese` per leggere le attese attuali
     invece di quelle salvate. Metodo: `docs/piano-insieme-prova.md`,
     "Regola delle misure".
2. **Pulizia dei dati**: 2a dopo il primo giro di etichette (bandi con 8
   o più tipi, aperti sospetti); 2b il resto (`altra_impresa`). La
   nuova baseline, tre registrazioni delle 55 domande (circa 10,5 $;
   assorbe il passo 6), si registra dopo i passi 19, 2b, 4 e 3
   (decisione del 19/11/2026). Dettaglio in `coda.md`, "Pulizia dei
   dati (passi 2a e 2b)".
   2a fatto il 18/11/2026 (`docs/fatto.md`).
3. **Simulazione del router, senza modello**, dopo il passo 4, sulle
   risposte grezze già salvate e solo sulle decisioni che restano al
   router: chi chiede, bando nominato o elenco, documenti sì o no.
   Strategie e casi in `coda.md`, voce 16 dei Difetti del 14/11.
4. **Confronto sull'ordinamento**, sulle etichette, solo sulle domande P e
   L: quanti bandi pertinenti stanno nei primi 10. Embedding locali,
   nessun costo. Metodo in `docs/piano-insieme-prova.md`, "Regola delle
   misure". Riprende la ricerca per bisogno (`coda.md`, voce 6 dei
   Prossimi passi) e le domande da imprenditore (voce 10 dei Difetti del
   14/11).

Passi nuovi della sezione A:

17. **Testo di ricerca per bando**: fatto il 19/11/2026
    (`docs/fatto.md`).
19. **PDF degli avvisi dei bandi aperti**: l'avviso in PDF di ogni
    bando aperto entra nell'archivio dei documenti, legato al bando con
    `id_bando`. Prerequisito del passo 9, non una correzione delle
    risposte. Dettaglio in `coda.md`, "PDF dei bandi" (passo 19).
    19a e 19b fatti il 19/11/2026, 19c il 20/11/2026: 17 file, 871
    frammenti nel Chroma locale.
    19d chiuso il 23/11/2026, sotto soglia (`coda.md`, "Passo 19d", punto
    13, voci 19-21): c-LR tutte è la configurazione degli avvisi; avvisi
    in produzione solo con il filtro per bando e il "non lo trovo";
    numero da citare 77 su 98 (78,6%), B, k=10, metà di controllo. Stato
    giorno per giorno in `docs/fatto.md`.
    19e: avvisi su Postgres insieme al filtro per bando (dalla selezione
    dei bandi, quando c'è) e rimisura del recupero su Postgres. Rimedi,
    in quest'ordine:
    1. frammenti vicini passati al modello;
    2. segnale di scarsa fiducia;
    3. secondo tentativo con altre parole;
    4. scelta guidata;
    5. domande semplici scritte al caricamento.
    Dettaglio e altre voci del 19e in `coda.md`, "Passo 19d", punto 7.
    (25/11/2026) Resto del 19e: piano a tappe e decisioni in
    `docs/piano-19e.md`. I rimedi 2, 3, 4 e 5 vengono dopo le tappe del
    piano.
24. **Taglio dei documenti a livelli** (nuovo, 25/11/2026): taglio
    secondo la struttura del bando (articolo, comma, tabella), un solo
    indice da cui si ricavano il pezzo per la ricerca, il genitore per il
    contesto e il titolo per la verifica. Sostituisce i frammenti vicini
    e richiede di rigenerare i contesti. Dopo il 19e e il passo 25.
    Dettaglio in `coda.md`, "Taglio dei documenti secondo la struttura
    del bando (22/11/2026)".
25. **Insieme di domande nuovo** (nuovo, 25/11/2026): domande scritte da
    persone, con la risposta attesa, per misurare le sostituzioni delle
    soluzioni provvisorie del 19e e le strade per le parole comuni. Voci
    vicine: il passo 5 e la nuova baseline. Motivo in `coda.md`, "Ricerca
    per nome e parole comuni (25/11/2026)", collo di bottiglia.

### B. Correzioni del flusso, con il modello

Misurate contro la baseline e l'insieme di controllo, domanda per domanda.
Regola del confronto appaiato: `docs/piano-insieme-prova.md`, "Regola
delle misure".

5. **Insieme di controllo**: domande vere dello sportello più casi senza
   risposta, registrato una volta a freddo prima delle correzioni, mai
   usato per tarare. Le tre domande già provate dal consulente pilota
   entrano subito. Vale come veto, non per scegliere (`coda.md`,
   "Insieme di prova: dopo"; `docs/piano-insieme-prova.md`).
6. **Variabilità**: sostituito dalle tre registrazioni della nuova
   baseline (passo 2).
7. **Router**: strategia e ripieghi scelti dalla simulazione del passo 3
   (`coda.md`, voce 16 dei Difetti del 14/11).
8. **Soglie di popolazione nel codice**, il minimo: la soglia come campo
   compilato a mano, con la frase di origine, e il confronto nel codice
   (fondo strade, fasce di Missione Comune); il modello spiega il
   risultato. `coda.md`, "In coda", soglie di popolazione dei bandi.
9. **Risposta in funzioni in sequenza** (classifica, forma, scrivi), con
   la mappa delle regole in `docs/revisione-prompt-2026-11-18.md`.
   Nella regola di chiusura: verifiche a mano sulle conclusioni, quota di
   bandi proposti con etichetta "no", costo e tempo per domanda.
   Dettaglio in `coda.md`, "Architettura della risposta" (era la prima
   voce dei Prossimi passi).
10. **Forma dell'aiuto** (fondo perduto, prestito, garanzia, interessi):
    estrazione come campo dei bandi rimandata; subito, etichettata a mano
    sui 54 aperti. Caso P11: la risposta raggruppa dei bandi come
    «Contributi a fondo perduto» senza appoggio nelle righe.

Passo nuovo della sezione B:

18. **Chi chiede**, prima del passo 9. In dubbio, unione dei tipi. Casi
    da coprire in `coda.md`, voce 9 dei Difetti del 14/11.

### C. Fonti, in sequenza

Studio in `docs/piano-fonti-burt-ministeri.md`.

11. **Scansione settimanale del Portale della Regione**, con i requisiti
    di `coda.md`, era la voce 3 dei Prossimi passi.

    Prima della videochiamata con il consulente pilota, una scansione a
    mano del Portale, perché la demo online usa la data vera. Tocca solo
    l'archivio vero, mai la copia congelata del passo 0.
12. **MIT**: elenco dei contributi attivi (studio, 2.3 B).
13. **BURT**: sommario della Parte III, ogni mercoledì; mai la Parte IV
    (studio, 1.3 e 3.3). Nessuno dei due casi del consulente passava
    dal BURT (19/11/2026); prima vengono i PDF dei bandi già in
    archivio (passo 19).
14. **Ministero dell'Interno, Finanza locale** (studio, 2.3 A).
15. **Dipartimento per lo Sport e Sport e Salute** (studio, 2.3 C).
16. **Misura di copertura su un elenco esterno**, prima e dopo
    (`coda.md`, "Prova di copertura" tra le voci di "Prima della demo";
    `docs/ricognizione-fonti.md`, sezione 8).
23. **Copertura dell'archivio** (nuovo, 22/11/2026), dopo il 19d: quanti
    dei bandi esistenti l'archivio ha, non solo se l'app trova quelli che
    ha. Canali paralleli per scoprire fonti e bandi mancanti, un solo
    registro delle fonti con il canale di arrivo, una sola porta
    d'ingresso (pagina ufficiale dell'ente, bando reale con la data,
    robots.txt letto), misura ricorrente una volta al mese su venti
    bandi noti. Voce vicina: il passo 16. Dettaglio in
    `coda.md`, "Copertura dell'archivio (22/11/2026)".

I due casi sono arrivati il 19/11/2026: nessuno passava dal BURT.
L'ordine dei passi 12-15 si riconferma dopo la videochiamata della prima
settimana di dicembre. Direzione generale Spettacolo: fonte inserita a
mano il 19/11/2026, elenco spento.

### D. Dopo il confronto con il consulente pilota sull'obiettivo

Profilo territoriale, pratiche, percorso guidato: documenti, figure da
coinvolgere, controllo dei documenti come lista di controllo e mai come
approvazione (`coda.md`, voci 5, 4 e 10 dei Prossimi passi).

Proposte del 19/11/2026 in docs/coda.md: valutazione a tre livelli,
interventi collegati, colonna sinistra, app in due fasi con il fascicolo.
Ordine previsto: PDF, valutazione, fascicolo.

### E. App online

20. **Tasto di segnalazione sulla risposta**, versione minima: una
    scelta tra quelle elencate in `coda.md`, "Tasto di segnalazione sulla
    risposta"; un campo libero facoltativo; salvataggio su Supabase solo
    quando l'utente preme il tasto. Dopo il passo 19c e comunque prima
    della videochiamata con il consulente pilota (prima settimana di
    dicembre). Dal 22/11/2026 (disegno dell'app): in più, solo
    nell'elenco dei bandi, un comando leggero per bando ("non c'entra con
    la mia domanda") per misurare la precisione della selezione; le
    segnalazioni stanno nel database, mai in un file del repository, con
    l'avviso a non scrivere dati personali. Dettaglio in `coda.md`,
    "Disegno dell'app (22/11/2026)".
    (25/11/2026) Viene dopo il 19e, non più prima della videochiamata:
    la chiamata serve a raccogliere informazioni.
21. **Limite di 3 domande per sessione e tetto giornaliero
    complessivo** (`coda.md`, "Sezione riservata", parte sul limite).
    Prima di dare il link della demo a chiunque oltre al consulente
    pilota.
22. **Scheda per bando** (nuovo, 22/11/2026; era nel "Parcheggio" di
    `coda.md`): in parole semplici, a chi è rivolto, come si accede, cosa
    si ottiene. Generata al caricamento, una fonte per ogni riga, numeri
    controllati dal verificatore, voce vuota se il bando non lo dice.
    L'ordine rispetto al filtro del 19e si decide a 19d chiuso. Dettaglio
    in `coda.md`, "Disegno dell'app (22/11/2026)".

### Riempitivi e passi manuali

- Senza modello: i codici spezzati in più numeri nel verificatore
  (`coda.md`, "In coda"). Le voci 17 e 18 dei Difetti del 14/11
  (verificatore) aspettano il passo 9.
- Manuali: limite di spesa mensile nella console di Anthropic, da fare
  prima di tutto il resto; HF_TOKEN
  nei secrets di Streamlit Cloud (oggi il modello degli embedding si
  scarica senza token a ogni avvio dell'app online).

### In attesa

- Dal consulente pilota: risposta alla diagnosi del 19/11/2026 e
  videochiamata nella prima settimana di dicembre; restano da ricevere le
  domande vere e le fonti che usa. Domande per la videochiamata in
  `coda.md`, 'Riscontro del consulente pilota e fonti', più le due del
  19/11 già scritte (vale la pena o cosa c'è per me; lavoro per pratica).

## Decisioni prese

- **Si acquisiscono tutti i bandi**, anche quelli per i privati, con i tipi di
  beneficiari e le condizioni. Si filtra al momento della domanda.
- **Lo stato di un bando si calcola dalla scadenza**, mai dall'etichetta del
  sito.
- **I bandi scaduti non si cancellano**: servono a riconoscere le proroghe, i
  bandi ricorrenti e a evitare di riestrarli.
- **Nessuna lettura automatica dei social**, e nessun aggiramento di
  `robots.txt` o di blocchi anti-bot.
- **Apify rimandato**: le fonti attuali sono HTML leggibile. Si rivaluta solo
  se una fonte necessaria non lo è.
- **Smistamento con un secondo modello rimandato**: il risparmio è piccolo
  rispetto alla complessità.
- **Repository pubblico** come portfolio. Nessun dato di persone entra mai nel
  repository: email, ricerche e documenti degli utenti stanno su Supabase.
- **La combinazione di bandi non la decide il sistema**: mostra la clausola di
  cumulabilità di ciascuno, la valutazione resta a chi segue la domanda.
- **ANCI Toscana e le altre fonti di scoperta segnalano, non sono fonti**:
  i dati si prendono dalla pagina ufficiale dell'ente; le schede ANCI non
  si salvano e non si citano.
- **Router: la strategia si sceglie dopo la simulazione senza modello**
  (passo 3), non a maggioranza per principio (18/11/2026).
- **BURT: solo Parte III e supplementi, dal sommario**; mai la Parte IV,
  che contiene dati personali (18/11/2026).
- **Misure su archivio congelato e data fissa** (2026-11-16), passo 0
  (18/11/2026).
- **Baseline in tre registrazioni** delle 55 domande (18/11/2026).
- **Il passo 4 viene prima del passo 3** (18/11/2026).
- **La nuova baseline si registra dopo il passo 19** e prima dei passi
  che cambiano le risposte: la regola delle misure vieta di aggiungere
  documenti durante un ciclo, e i passi 17, 19, 2b, 4 e 3 non chiamano
  il modello (19/11/2026).
- **Gli avvisi dei bandi restano nel Chroma locale finché il passo 19d
  non passa**: su Postgres, cioè nell'app online, entrano solo dopo
  (20/11/2026).
- **I link del catalogo Incentivi Italia alla banca dati del BURT non
  entrano tra i bandi**: vanno in `scansioni` come da verificare, anche
  per incentivi-5013 e incentivi-3373. Dettaglio in `coda.md`, "Pulizia
  dei dati" (19/11/2026).
- **Disegno dell'app** (22/11/2026, da chi mantiene il progetto; non si
  costruisce ora): prima parte in tre passi, errori gravi e tollerabili,
  traguardo 85-90%. Dettaglio in `coda.md`, "Disegno dell'app (22/11/2026)".
- **Configurazione degli avvisi: c-LR tutte** (23/11/2026, decisione 1
  della regola di conferma). Avvisi in produzione solo con il filtro per
  bando e il "non lo trovo" (decisione 2, sotto soglia). Numero da
  citare: 77 su 98 (78,6%), B, k=10, metà di controllo (`coda.md`,
  "Passo 19d", punto 13, voce 20).
- **Progetto in due macro parti** (23/11/2026): la prima è l'app
  attuale, in tre passi; la seconda è l'area privata, scritta come
  direzione e non come passi numerati. Dettaglio in `coda.md`, "Disegno
  dell'app (22/11/2026)", aggiunte del 23/11.
- **19e intero, senza scadenza** (25/11/2026): la chiamata di dicembre
  raccoglie informazioni; l'app da far provare al consulente pilota è
  per gennaio-febbraio 2027. Motore online: un solo motore, due archivi
  (Postgres come archivio, ricerca in memoria con lo stesso codice del
  locale), provvisorio fino al taglio a livelli o a qualche migliaio di
  frammenti. Contesti scritti dal modello su Postgres, solo per cercare.
  Filtro solo con un bando trovato per nome. Nessun avviso e nessun
  contesto nuovo prima del taglio a livelli. Elenco completo in
  `docs/piano-19e.md`, "Decisioni del 25/11/2026".
