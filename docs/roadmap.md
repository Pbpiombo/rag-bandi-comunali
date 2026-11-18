# Roadmap

I documenti scritti prima del 18/11/2026 citano sezioni di questa roadmap che oggi stanno in docs/coda.md con il loro numero originale (Difetti del 14/11, Dopo la demo, Prossimi passi, In coda, priorità del consulente pilota, indicazioni del revisore tecnico) e in docs/fatto.md.

Stato al 18 novembre 2026. Da aggiornare alla fine di ogni passo.

Qui stanno solo stato, principi, ordine dei passi e decisioni prese. Il
lavoro chiuso è in `docs/fatto.md`; le voci in attesa, con il loro numero
originale, in `docs/coda.md`.

## Stato

- Demo mandata al consulente pilota il 16/11/2026, riscontro ricevuto il
  18/11/2026. Revisione del revisore tecnico ricevuta il 18/11/2026.
  Revisione esterna del piano ricevuta il 18/11/2026.
- Baseline: la regressione finale del 16/11/2026 (commit `715b411`), 55
  domande in 4 lotti. Vale fino alla pulizia dei dati (passo 2); dopo,
  la baseline è la nuova registrazione delle 55 domande.
- Attese: 18 sui titoli nel file delle domande, su 14 domande. La tabella
  a freddo ne conta 17: manca quella di L05, che nel lotto 1 a freddo ha
  avuto il router fallito 3 volte su 3 (attesa 0/1).

Riscontro del consulente pilota del 18/11/2026, in sintesi:
- prova con tre domande;
- su una domanda senza risultati attesi l'app non ha inventato;
- su una ha mancato due bandi, uno nazionale e uno regionale;
- su una ha trovato opportunità corrette ma generiche;
- suggerimenti: includere il BURT e provare con qualche ministero.

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

I numeri dei passi non cambiano. **Ordine di esecuzione:** 0; 1 (primo
giro); 2a; 17; 1 (resto); 2b e nuova baseline; 4; 3; 5; 18; 8; 9; poi C
in sequenza, non in parallelo.

### A. Misure e dati, senza modello salvo dove indicato

0. **Regola delle misure.** Tutte le misure di A e B su una copia
   congelata dei CSV e con data di riferimento 2026-11-16; data fissa e
   SQLite congelato sono un compito di codice a parte, prima della nuova
   baseline (`docs/piano-insieme-prova.md`, "Regola delle misure").
1. **Etichette.** Schede in `dati-grezzi/etichette/2026-11-18_152225`, per
   50 domande: le 5 domande A non hanno schede e restano misurate con le
   attese attuali.
   - Primo giro a mano su C02, C03, C07, C14, P03, P09, P11, P22, P24,
     L02; due o tre domande anche al consulente pilota.
   - Dalle etichette nascono le attese con polarità (proposto, non
     proposto); `forma_attesa` si calcola dalle etichette. Oggi una
     citazione fatta per escludere un bando conta come trovata (caso C03).
   - Serve un'opzione di `diagnosi_attese` per leggere le attese attuali
     invece di quelle salvate. Metodo: `docs/piano-insieme-prova.md`,
     "Regola delle misure".
2. **Pulizia dei dati**: 2a dopo il primo giro di etichette (bandi con 8
   o più tipi, aperti sospetti); 2b il resto (`altra_impresa`). Poi la
   nuova baseline: tre registrazioni delle 55 domande, circa 10,5 $;
   assorbe il passo 6. Dettaglio in `coda.md`, "Pulizia dei dati (passi
   2a e 2b)".
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

Passo nuovo della sezione A:

17. **Testo di ricerca per bando**, senza modello, in un file separato
    (`data/processed/testo_ricerca.csv`); serve solo all'ordinamento.
    Dettaglio in `coda.md`, "Testo di ricerca (passo 17)".

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
    (studio, 1.3 e 3.3).
14. **Ministero dell'Interno, Finanza locale** (studio, 2.3 A).
15. **Dipartimento per lo Sport e Sport e Salute** (studio, 2.3 C).
16. **Misura di copertura su un elenco esterno**, prima e dopo
    (`coda.md`, "Prova di copertura" tra le voci di "Prima della demo";
    `docs/ricognizione-fonti.md`, sezione 8).

I passi 13, 14 e 15 sono fermi finché non arrivano i due bandi mancati
dal consulente pilota; allora si riconferma l'ordine delle fonti.

### D. Dopo il confronto con il consulente pilota sull'obiettivo

Profilo territoriale, pratiche, percorso guidato: documenti, figure da
coinvolgere, controllo dei documenti come lista di controllo e mai come
approvazione (`coda.md`, voci 5, 4 e 10 dei Prossimi passi).

### Riempitivi e passi manuali

- Senza modello: i codici spezzati in più numeri nel verificatore
  (`coda.md`, "In coda"). Le voci 17 e 18 dei Difetti del 14/11
  (verificatore) aspettano il passo 9.
- Manuali: limite di spesa mensile nella console di Anthropic; HF_TOKEN
  nei secrets di Streamlit Cloud (oggi il modello degli embedding si
  scarica senza token a ogni avvio dell'app online).

### In attesa

- Dal consulente pilota: i due bandi mancati, le domande vere, le fonti
  che usa; e se la domanda con risposte "generiche" era per un ente o per
  un privato. Con i bandi mancati, diagnosi a tre categorie senza modello
  (archivio, recupero, esclusione) e domande come casi fissi dell'insieme
  di prova.

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
