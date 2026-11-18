# Roadmap

Stato al 18 novembre 2026. Da aggiornare alla fine di ogni passo.

Qui stanno solo stato, principi, ordine dei passi e decisioni prese. Il
lavoro chiuso è in `docs/fatto.md`; le voci in attesa, con il loro numero
originale, in `docs/coda.md`.

## Stato

- Demo mandata al consulente pilota il 16/11/2026, riscontro ricevuto il
  18/11/2026. Revisione del revisore tecnico ricevuta il 18/11/2026.
- Baseline: la regressione finale del 16/11/2026 (commit `715b411`), 55
  domande in 4 lotti. Vale fino alla pulizia dei dati (passo 2); dopo,
  la baseline è la nuova registrazione delle 55 domande.
- Fatti il 18/11/2026, senza modello: diagnosi delle attese a tre
  categorie, archivio, recupero, esclusione
  (`scripts/diagnostica/diagnosi_attese.py`); revisione esterna dei prompt
  (`docs/revisione-prompt-2026-11-18.md`); schede di etichettatura con la
  tabella "Bandi ricorrenti" (`scripts/diagnostica/schede_etichette.py`);
  studio delle fonti (`docs/piano-fonti-burt-ministeri.md`).

Riscontro del consulente pilota del 18/11/2026, in sintesi:
- prova con tre domande;
- su una domanda senza risultati attesi l'app non ha inventato;
- su una ha mancato due bandi, uno nazionale e uno regionale;
- su una ha trovato opportunità corrette ma generiche;
- suggerimenti: includere il BURT e provare con qualche ministero.

Indicazioni del revisore tecnico (18/11), ricevute:
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

## Principi dell'architettura della risposta

- **"Per chi" è un filtro deciso dal codice**: chi chiede (ente del menu o
  tipo di privato) esclude con certezza i bandi a cui non può partecipare.
- **"Per cosa" è un ordinamento**: tra i bandi rimasti, vicinanza a ciò
  che chi chiede vuole fare, su titolo, interventi e finalità, con
  somiglianza di significato (embedding locali) più parole esatte, come il
  recupero ibrido dei documenti.
- **Il modello classifica i primi 10-15** (pertinente, generico possibile,
  no) con uscita strutturata; il codice decide la forma della risposta; il
  modello scrive.
- **Funzioni in sequenza**; LangGraph solo con cicli o rami.
- **Il settore di chi chiede, se manca, si chiede con un menu** e si
  conserva come dato della sessione, non come memoria della chat.
- **Prova**: tabella "Bandi ricorrenti" del 18/11/2026. Su 54 bandi aperti
  un'impresa generica ne ammette 25; i bandi per assunzioni compaiono in 29
  domande private su 30.

## Ordine dei passi

### A. Misure e dati, senza modello salvo dove indicato

1. **Etichette.** Schede in `dati-grezzi/etichette/2026-11-18_152225`.
   Primo giro a mano su C02, C03, C07, C14, P03, P09, P11, P22, P24, L02;
   poi il confronto con un secondo modello sulle stesse 10; poi il resto.
   Dalle etichette nascono le attese con polarità (proposto, non proposto,
   forma attesa): oggi una citazione fatta per escludere un bando conta
   come trovata (caso C03). Serve un'opzione di `diagnosi_attese` per
   leggere le attese attuali invece di quelle salvate. Metodo:
   `docs/piano-insieme-prova.md`.
2. **Pulizia dei dati, in un blocco solo:**
   - classificazioni troppo larghe: risorse genetiche agrarie, 12 tipi, in
     50 domande su 50; controllare ogni bando con 8 o più tipi (`coda.md`,
     voci 4 e 14 dei Difetti del 14/11);
   - bandi aperti sospetti: Tax credit cinema 2024, sportelli senza
     chiusura aperti da più di due anni (`coda.md`, "Nuova Sabatini,
     Smart&Start, ISI INAIL" tra le voci di "Prima della demo").

   Poi una nuova baseline: 55 domande, circa 3,5 $.
3. **Simulazione del router, senza modello**, sulle risposte grezze già
   salvate. Quattro strategie: prima chiamata (oggi), maggioranza, unione
   delle scelte delle chiamate, unione più ripieghi nel codice. Un tema
   fuori elenco conta come anomalia (caso P11: tema "montagna"). Casi in
   `coda.md`, voce 16 dei Difetti del 14/11.
4. **Confronto tra la ricerca attuale e "filtro per chi più ordinamento per
   cosa"** sulle etichette: quanti bandi pertinenti stanno nei primi 10.
   Embedding locali, nessun costo. Riprende la ricerca per bisogno
   (`coda.md`, voce 6 dei Prossimi passi) e le domande da imprenditore
   (voce 10 dei Difetti del 14/11).

### B. Correzioni del flusso, con il modello

Misurate contro la baseline e l'insieme di controllo, domanda per domanda.

5. **Insieme di controllo**: domande vere dello sportello più casi senza
   risposta, registrato una volta a freddo prima delle correzioni, mai
   usato per tarare (`coda.md`, "Insieme di prova: dopo";
   `docs/piano-insieme-prova.md`).
6. **Variabilità**: due ripetizioni delle 55 domande sulla baseline.
7. **Router**: strategia e ripieghi scelti dalla simulazione del passo 3
   (`coda.md`, voce 16 dei Difetti del 14/11).
8. **Soglie di popolazione nel codice**, con la soglia come campo
   strutturato e la frase di origine; il modello spiega il risultato
   (`coda.md`, "In coda", soglie di popolazione dei bandi).
9. **Risposta in funzioni in sequenza** (classifica, forma, scrivi), con
   la mappa delle regole in `docs/revisione-prompt-2026-11-18.md`.
   Dettaglio in `coda.md`, "Architettura della risposta" (era la prima
   voce dei Prossimi passi).
10. **Forma dell'aiuto come campo dei bandi** (fondo perduto, prestito,
    garanzia, interessi), con la frase di origine. Caso P11: la risposta
    raggruppa dei bandi come «Contributi a fondo perduto» senza appoggio
    nelle righe.

### C. Fonti, binario parallelo

Studio in `docs/piano-fonti-burt-ministeri.md`.

11. **Scansione settimanale del Portale della Regione**, con la sua lista
    di requisiti (`coda.md`, era la voce 3 dei Prossimi passi).
12. **MIT**: elenco dei contributi attivi (studio, 2.3 B).
13. **BURT**: sommario della Parte III, ogni mercoledì; mai la Parte IV
    (studio, 1.3 e 3.3).
14. **Ministero dell'Interno, Finanza locale** (studio, 2.3 A).
15. **Dipartimento per lo Sport e Sport e Salute** (studio, 2.3 C).
16. **Misura di copertura su un elenco esterno**, prima e dopo
    (`coda.md`, "Prova di copertura" tra le voci di "Prima della demo";
    `docs/ricognizione-fonti.md`, sezione 8).

L'ordine delle fonti va riconfermato quando arrivano i due bandi mancati
dal consulente pilota.

### D. Dopo il confronto con il consulente pilota sull'obiettivo

Profilo territoriale, pratiche, percorso guidato: documenti, figure da
coinvolgere, controllo dei documenti come lista di controllo e mai come
approvazione (`coda.md`, voci 5, 4 e 10 dei Prossimi passi).

### Riempitivi e passi manuali

- Senza modello: verificatore, voci 17 e 18 dei Difetti del 14/11 e i
  codici spezzati in più numeri (`coda.md`, "In coda").
- Manuali: limite di spesa mensile nella console di Anthropic; HF_TOKEN
  nei secrets di Streamlit Cloud (oggi il modello degli embedding si
  scarica senza token a ogni avvio dell'app online).

### In attesa

- Dal consulente pilota: i due bandi mancati, le domande vere, le fonti
  che usa. Con i bandi mancati, diagnosi a tre categorie senza modello
  (archivio, recupero, esclusione) e domande come casi fissi dell'insieme
  di prova.
- La revisione esterna del piano.

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
