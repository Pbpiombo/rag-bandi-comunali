# Roadmap

I documenti scritti prima del 18/11/2026 citano sezioni di questa roadmap che oggi stanno in docs/coda.md con il loro numero originale (Difetti del 14/11, Dopo la demo, Prossimi passi, In coda, priorità del consulente pilota, indicazioni del revisore tecnico) e in docs/fatto.md.

Stato al 20 novembre 2026. Da aggiornare alla fine di ogni passo.

Qui stanno solo stato, principi, ordine dei passi e decisioni prese. Il
lavoro chiuso è in `docs/fatto.md`; le voci in attesa, con il loro numero
originale, in `docs/coda.md`.

## Stato

- **Gli avvisi dei bandi non vanno su Postgres finché il passo 19d non
  passa.** Dal 20/11/2026 stanno solo nel Chroma locale (passo 19c,
  `docs/fatto.md`): l'app online non li vede. Il 19d è in corso; il
  caricamento su Postgres è il passo 19e.
- Demo mandata al consulente pilota il 16/11/2026, riscontro ricevuto il
  18/11/2026. Revisione del revisore tecnico ricevuta il 18/11/2026.
  Revisione esterna del piano ricevuta il 18/11/2026.
- Baseline: la regressione finale del 16/11/2026 (commit `715b411`), 55
  domande in 4 lotti. La baseline del 16/11/2026 non corrisponde più
  all'archivio dopo il passo 2a (18/11/2026). Resta l'unico riferimento
  fino alla nuova registrazione delle 55 domande, dopo il passo 3.
- Attese: 18 sui titoli nel file delle domande, su 14 domande. La tabella
  a freddo ne conta 17: manca quella di L05, che nel lotto 1 a freddo ha
  avuto il router fallito 3 volte su 3 (attesa 0/1).

Riscontro del consulente pilota del 18/11/2026, in sintesi:
- prova con tre domande;
- su una domanda senza risultati attesi l'app non ha inventato;
- su una ha mancato due bandi, uno nazionale e uno regionale;
- su una ha trovato opportunità corrette ma generiche;
- suggerimenti: includere il BURT e provare con qualche ministero.

Riscontro del 19/11/2026: domanda e casi indicati; diagnosi in
`coda.md`, 'Riscontro del consulente pilota e fonti': un pertinente
mancato per copertura (Fondo nazionale rievocazione storica 2027),
l'altro caso non era un bando.

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

I numeri dei passi non cambiano. **Ordine di esecuzione:** 0 (fatto);
1 (etichette, fatto); 2a (fatto); 17 (fatto); 1 (resto: "chi atteso", domande
A, attese con polarità); 19 (19a, 19b e 19c fatti, 19d in corso, poi 19e); 20 (prima
della videochiamata della prima settimana di dicembre); 2b; 4; 3; nuova
baseline; 5; 18; 8; 9; poi le fonti (C) in sequenza, non in parallelo.
Il passo 21 si fa prima di dare il link della demo a chiunque oltre al
consulente pilota, in qualunque punto della sequenza. Perché la nuova
baseline viene dopo il passo 19: "Decisioni prese" (19/11/2026).

### A. Misure e dati, senza modello salvo dove indicato

0. **Regola delle misure.** Tutte le misure di A e B su una copia
   congelata dei CSV e con data di riferimento 2026-11-16; data fissa e
   SQLite congelato sono un compito di codice a parte, prima della nuova
   baseline (`docs/piano-insieme-prova.md`, "Regola delle misure").
   Parti (a) e (b) fatte il 18/11/2026 (`docs/fatto.md`); la parte (c)
   è una regola, non codice. La prima copia congelata si fa dopo il
   passo 2b.
1. **Etichette.** Schede in `dati-grezzi/etichette/2026-11-18_152225`, per
   50 domande: le 5 domande A non hanno schede e restano misurate con le
   attese attuali.
   - Fatto il 19/11/2026 con un metodo diverso da quello previsto: due
     modelli, un arbitro, revisione a mano di 96 righe dei Comuni. 990
     etichette, 27 incerte, forma incerta per C18 e C20. Metodo, numeri
     e limiti in docs/piano-insieme-prova.md, 'Come sono state fatte le
     etichette'. Resta da fare: la colonna 'chi atteso' per domanda e le
     5 domande A.
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
   2a fatto il 18/11/2026: scadenze corrette a mano per Filiera SMART,
   per l'edizione precedente del Bando Pmi EU-Blending (incentivi-3662,
   non un doppione) e per il fondo di garanzia energie rinnovabili;
   aperti al 16/11 da 54 a 51. I quattro bandi con 8 o più tipi non sono
   errori di classificazione ma bandi "per requisito": restano come
   sono, e il rimedio è il passo 4.
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

17. **Testo di ricerca per bando**, senza modello, in un file separato
    (`data/processed/testo_ricerca.csv`); serve solo all'ordinamento.
    Dettaglio in `coda.md`, "Testo di ricerca (passo 17)".
    Fatto il 19/11/2026 (`docs/fatto.md`).
19. **PDF degli avvisi dei bandi aperti**: l'avviso in PDF di ogni
    bando aperto entra nell'archivio dei documenti, legato al bando con
    `id_bando`. Prerequisito del passo 9, non una correzione delle
    risposte. Dettaglio in `coda.md`, "PDF dei bandi" (passo 19).
    19a e 19b fatti il 19/11/2026, 19c il 20/11/2026 (`docs/fatto.md`):
    17 file, 871 frammenti nel Chroma locale. Prossimo: 19d, misura del
    recupero sugli avvisi (`coda.md`, "Passo 19d"). Gli avvisi vanno su
    Postgres solo dopo che il 19d è passato.
    19d in corso dal 20/11/2026: non è più una verifica, è il lavoro che
    ridisegna la ricerca nei documenti. Fatti 195, divisi in 97 di
    taratura e 98 di controllo; il controllo si apre una volta sola,
    sulla scelta finale. Regola di chiusura, risultati e strade in
    `coda.md`, "Passo 19d".
    19e, nuovo (20/11/2026): avvisi su Postgres insieme al filtro per
    `id_bando` nell'app, e rimisura del recupero su Postgres con gli
    stessi fatti, perché lì ricerca per parole e indice dei vettori sono
    diversi da Chroma.

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
    dicembre).
21. **Limite di 3 domande per sessione e tetto giornaliero
    complessivo** (`coda.md`, "Sezione riservata", parte sul limite).
    Prima di dare il link della demo a chiunque oltre al consulente
    pilota.

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
