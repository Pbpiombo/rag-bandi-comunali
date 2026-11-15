# Piano: correzioni dalla diagnosi del lotto 1

Approvato il 14 novembre 2026. Viene dalla diagnosi della registrazione a
freddo del lotto 1 dell'insieme di prova (`docs/piano-insieme-prova.md`).
Se la conversazione con Claude Code viene azzerata, si riparte leggendo
questo file.

## Ordine di lavoro

1. Correzione 1 (router).
2. Correzione 2 (parametri).
3. Correzione 3 (Unione).
4. Correzione A (falsi allarmi del verificatore sui numeri).
5. Correzione C (presentazione delle risposte), aggiunta il 14 novembre
   2026 dopo una prova dall'app.
6. Una nuova registrazione dell'intero lotto 1: circa 0,90 $, non a freddo.
   Il lotto 2 resta a freddo per dopo.

La correzione A si può misurare subito con `--riverifica` sulla
registrazione a freddo del lotto 1, senza chiamate al modello. Le
correzioni 1 e 2 si misurano solo registrando di nuovo, perché
`--riverifica` non rifà il router.

Le regole di chiusura sono scritte qui prima di registrare, come vuole il
metodo dei lotti.

## Correzione 1: router

### Difetto

- A01: il router scrive un paragrafo e poi un JSON valido. `decidi`
  (`src/chains/router.py`) fa `json.loads(pulisci_json(grezzo))`, e
  `pulisci_json` toglie solo le recinzioni ```` ``` ````: il testo prima
  del JSON lo fa fallire.
- L05: due risposte vuote e una troncata, 512 token in uscita a chiamata,
  cioè il tetto di `max_tokens`. Con `claude-sonnet-5`, se il parametro
  `thinking` manca il ragionamento adattivo è attivo, i suoi token contano
  in `max_tokens` e il suo testo è vuoto per impostazione predefinita;
  `StrOutputParser` tiene solo i blocchi di testo. `stop_reason` non è
  registrato da nessuna parte.
- Quando il router fallisce, l'app mostra all'utente "Anomalia del router:
  risposta del router non interpretabile: …" con 120 caratteri del testo
  grezzo del router.

### Correzione

- `src/chains/router.py`:
  - `costruisci_router`: `max_tokens` da 512 a 2048; restituisce il
    messaggio intero (`MODELLO_ROUTER | modello`), non più la stringa, così
    `stop_reason` resta leggibile.
  - Nuova `estrai_decisione(testo)`: cerca gli oggetti JSON nel testo con
    `json.JSONDecoder().raw_decode` a partire da ogni `{`, e tiene quelli
    con `documenti` o `interrogazioni`. Uno solo, o più copie identiche: è
    la decisione. Nessuno, o più diversi: errore, come oggi.
  - `decidi`: usa `estrai_decisione`; accetta un messaggio o una stringa.
    `stop_reason` va nella decisione quando è noto. In caso di errore la
    decisione conserva l'errore, `stop_reason` e il testo grezzo intero.
- Non si usa `thinking: {"type": "disabled"}`: `claude-sonnet-5` lo
  accetta, ma restituisce un 400 su `claude-sonnet-5-5`, e il modello si
  cambia dal `.env`.
- `scripts/diagnostica/prova_insieme.py`, `RouterTriplo`: salva il testo e
  lo `stop_reason` di ogni chiamata; l'interpretabilità si giudica con
  `estrai_decisione`, come la giudica l'app.
- **B**, `app/app.py`: quando il router fallisce, il testo grezzo del
  router non va mostrato all'utente. Nell'app una riga neutra: "Non sono
  riuscito a scegliere le interrogazioni sui dati: la risposta si basa solo
  sui documenti." Il dettaglio (errore, `stop_reason`, testo grezzo) resta
  nella decisione e nei file della prova.

### Test (falliscono prima, passano dopo)

- Testo seguito da JSON (forma di A01): interpretato.
- JSON seguito da testo: interpretato.
- JSON tra recinzioni con testo intorno: interpretato.
- Due JSON diversi: errore.
- Testo senza JSON: errore.
- JSON troncato con `stop_reason: max_tokens` (modello finto): errore, con
  `max_tokens` e il testo grezzo nella decisione.
- `max_tokens` del router almeno 2048.
- `RouterTriplo` registra lo `stop_reason` di ogni chiamata.
- B: con una decisione in errore la riga dell'app è quella neutra e non
  contiene il testo grezzo né il messaggio d'errore.

### Regola di chiusura (sul lotto 1 registrato di nuovo)

- 51 risposte del router su 51 interpretabili.
- A01 decide `documenti: false`.
- L05 ha `stop_reason: end_turn`.
- Le altre 15 domande non cambiano tipo di interrogazione rispetto alla
  registrazione a freddo; ogni differenza si annota e si spiega.
- Nessun testo grezzo del router nell'interfaccia.

## Correzione 2: parametri

### Difetto

Il router ha scelto temi inesistenti ("edilizia scolastica", "dissesto
idrogeologico", "montagna") e un tipo di beneficiario inesistente
("impresa_femminile"): C04, C11, P11, P25. Nel prompt del router il tipo è
un elenco chiuso, il tema è testo libero con esempi ("casa" compreso; in archivio c'è un bando con
tema casa, il tema dell'elenco senza bandi è "pesca"). L'elenco chiuso dei temi esiste solo nel prompt
dell'estrattore (`src/estrazione/bandi.py`).

Diagnosi in sola lettura: per C04 e C11 l'archivio non ha bandi aperti
pertinenti; per P11 e P25 non ci sono bandi mirati, ma con un tipo valido
(`altra_impresa`) sarebbero usciti i bandi generici per le imprese.

### Correzione

- Costante `TEMI` in un punto comune (`src/estrazione/beneficiari.py`,
  accanto a `TIPI_BENEFICIARIO`), usata dal prompt dell'estrattore (testo
  identico a oggi) e dalla descrizione di `bandi_per_tema` in
  `src/database/repertorio.py` ("uno dei temi: …").
- `ISTRUZIONI_ROUTER` in `src/chains/router.py`: una regola ("per chi vuole
  avviare o gestire un'impresa senza un settore preciso usa altra_impresa;
  non esistono codici per genere, età o fase dell'impresa") e un esempio.
- Il repertorio resta chiuso e il modello non riprova: percorso fisso.
- I 49 bandi senza tema (tutti da Incentivi Italia, 12 non scaduti al
  14 novembre 2026) vanno in `docs/roadmap.md` come primo compito di dati
  dopo la demo.

### Test (falliscono prima, passano dopo)

- La descrizione di `bandi_per_tema` elenca tutti i `TEMI`.
- Il prompt dell'estrattore contiene esattamente gli stessi `TEMI`.
- La regola d'impresa è nelle istruzioni del router (controllo debole: il
  comportamento si misura registrando).

### Regola di chiusura (sul lotto 1 registrato di nuovo)

- Nessun tema o tipo fuori elenco nelle 51 risposte del router.
- P11 e P25 usano `bandi_per_beneficiario` con un tipo valido ed elencano
  bandi.
- C04 e C11 usano un tema dell'elenco.
- Nessun nuovo "non trovato" del verificatore.
- In C04, C11, P11, P25 nessun bando non pertinente presentato come
  pertinente (controllo a mano).

## Correzione 3: Unione di appartenenza

### Difetto

In L05 il modello attribuisce il Comune all'"Unione Comuni Garfagnana": un
frammento SNAI la nomina come capofila dell'area interna con lo stesso nome
di `area_interna` del profilo. Il profilo (`profilo_ente` in
`src/database/enti.py`) non ha l'Unione di appartenenza, e nessun dato
collega i Comuni all'Unione.

### Correzione

- `data/processed/enti.csv`: nuova colonna `unione`, con il codice fiscale
  dell'Unione per i tre Comuni. Fonte: scheda Regione Toscana
  https://www.regione.toscana.it/-/unione-di-comuni-montani-appennino-pistoiese
  (aggiornata al 04/03/2026), che elenca come membri Abetone Cutigliano,
  Sambuca Pistoiese, San Marcello Piteglio. L'URL va nella colonna della
  fonte. Il CSV si modifica solo arrivati a questa correzione, mostrando
  prima il diff.
- `DDL` e `TABELLE_DA_CSV` in `src/database/schema.py`, poi ricreazione del
  database come da CLAUDE.md.
- `profilo_ente`: il nome dell'Unione nel profilo.
- `ISTRUZIONI` in `src/chains/rag.py`, una riga: "l'Unione dell'ente è
  quella del profilo; un'Unione nominata nei frammenti come capofila di
  un'area interna non è per questo l'Unione dell'ente".

### Test (falliscono prima, passano dopo)

- `profilo_ente` di un Comune restituisce l'Unione.
- Il profilo dell'Unione resta senza questo campo.
- Lo schema carica la colonna dal CSV.

### Regola di chiusura

In L05, registrato di nuovo, nessuna attribuzione dell'ente all'Unione
Comuni Garfagnana.

## Correzione A: falsi allarmi del verificatore sui numeri

### Difetto

Righe del lotto 1 giudicate a mano `falso_allarme_data` e
`falso_allarme_numero`: "21/27" in P17, L01, L03 (da "PR FESR 21/27") e
"50.000,00" in L02, L03.

### Correzione

- Una "data" impossibile (giorno o mese fuori intervallo, come 21/27) non è
  una data: non si estrae come data. **Proposta**: si tratta come testo da
  trovare tale e quale nella fonte, e non si ignora. Motivo: un periodo di
  programmazione sbagliato ("14/20" al posto di "21/27") è un errore vero,
  e ignorarlo lo nasconderebbe. Senza un trattamento esplicito, inoltre,
  "21/27" ricadrebbe negli schemi delle quantità come "21" e "27"
  separati, che si potrebbero confermare per coincidenza con altri numeri
  della fonte. Il costo: se la fonte scrive il periodo in un'altra forma
  ("2021-2027") resta un "non trovato", che è almeno un allarme leggibile.
- Un importo con separatori delle migliaia e decimali ("50.000,00") è un
  solo valore, non 50 e 000,00.
- I numeri nei titoli dei bandi restano controllati come tutti gli altri:
  un titolo può contenere un importo vero ("fino 50 mila euro") e non deve
  diventare una zona non verificata.

### Test (falliscono prima, passano dopo)

- Le righe del lotto 1 giudicate `falso_allarme_data` e
  `falso_allarme_numero` (P17, L01, L03 "21/27"; L02, L03 "50.000,00")
  diventano casi di test.
- "50 mila" in un titolo resta verificato.

### Regola di chiusura

Alla riverifica del lotto 1 quei 7 falsi allarmi spariscono e nessun dato
oggi verificato diventa non verificato.

### Differenze con la voce 1 della roadmap

Non c'era una versione concordata di A. La voce 1 di "Dopo la demo: dalla
prova completa del 14 novembre" in `docs/roadmap.md` descrive solo il caso
"21/27" e ipotizza anche un secondo difetto ("titolo non confrontato, o
normalizzato in modo diverso"). Questo piano aggiunge il caso "50.000,00" e
la regola sui numeri nei titoli; l'ipotesi sul titolo si verifica durante
la correzione.

## Correzione C: presentazione delle risposte

Aggiunta il 14 novembre 2026, prima della nuova registrazione del lotto 1.
Viene da una risposta dell'app su "aprire un data center" (la domanda L04
del lotto 1, posta dall'app e non dallo script) e dalla risposta L02 della
registrazione a freddo.

### Difetti

- **C1**. La risposta offre azioni che l'app non sa fare: "posso
  verificare se esistono bandi più recenti non ancora presenti in questo
  archivio" (l'app non cerca sul web) e "può indicarmi ulteriori dettagli
  per un controllo mirato" (l'app non ricorda la conversazione: i dettagli
  arriverebbero come domanda nuova, senza contesto). Comprende la voce
  "il modello descrive i suoi meccanismi" della roadmap ("occorrerebbe
  interrogare nuovamente l'archivio con beneficiario...").
- **C2**. La risposta elenca "agevolazioni su finanziamenti" tra i bandi
  in archivio e poi dice che le misure generali di sostegno agli
  investimenti "non sono presenti". Nella risposta sul ristorante (L02) gli
  stessi bandi per le Pmi erano presentati come possibili, da verificare.
  Nella registrazione a freddo L04 va oltre: "Non trovo la risposta nei
  documenti disponibili", con 23 bandi per `altra_impresa` nei dati, tra
  cui i bandi Pmi a sportello senza settore.
- **C3**. "Da approfondire" si intitola "Bandi pertinenti con dati
  mancanti o incerti" e mostra la cooperazione internazionale a ogni
  domanda che passa da `bandi_per_beneficiario`. Causa: la query prende
  `HA_TIPO OR SENZA_RIGHE_BENEFICIARI`, quindi un bando classificato senza
  beneficiari entra per ogni tipo; il 14 novembre 2026 l'unico bando
  aperto in quella condizione è "PROGETTI SEMPLICI 2026 di Cooperazione
  Internazionale" (tema "sociale"). Non è pertinente: non è stato valutato.
- **C4**. In "Fonti", sotto "[D1] bandi_per_beneficiario", compare un
  elemento di elenco vuoto.
- **C5**. L02: il modello scrive "codice ATECO 56" dalla sua conoscenza,
  non dai dati ("Un ristorante normalmente ha codice ATECO 56"). Giudicato
  `errore_vero`; il verificatore lo segna non trovato, correttamente.

### Diagnosi di C4 (14 novembre 2026, senza modello)

Non riprodotto. Prove fatte con il database di oggi e Streamlit 1.63
locale:

- testo di `bandi_per_beneficiario` per tutti i 12 tipi: nessuna riga
  vuota, nessun carattere di fine riga nascosto, nessuna riga che cominci
  con un segno d'elenco senza testo;
- reso in Edge senza interfaccia con il frontend vero di Streamlit, prima
  con `st.write` del solo testo per i 12 tipi, poi con `mostra_fonti`
  dell'app nella colonna destra (colonne 3:2) con gli esiti di L04
  (`altra_impresa` e popolazione): 23 voci `<li>` per 23 bandi, nessuna
  vuota, e in ognuna il testo comincia sulla riga del pallino.

Difetto trovato nello stesso punto: le intestazioni dei gruppi
(`GRUPPO_SPORTELLO` "A sportello, finché ci sono risorse:", e allo stesso
modo `GRUPPO_SENZA_SCADENZA` e `GRUPPO_PROSSIMA`) seguono la voce
precedente senza riga vuota. In markdown sono una riga di continuazione
di quella voce: nell'app "A sportello, finché ci sono risorse:" compare in
coda alla voce [D1.5], dopo il suo indirizzo, e il gruppo non si vede.
È l'unica riga del blocco fuori dallo schema "- [#k] …"; con un'altra
versione di Streamlit (requirements: `streamlit>=1.40`, non fissata) può
essere resa in modo diverso. Ipotesi da confermare con lo screenshot della
risposta o con la versione di Streamlit dell'app online.

### Correzioni

- **C1**, `ISTRUZIONI` in `src/chains/rag.py`, sezione nuova:

  > COSA PUÒ FARE L'APP
  > L'app risponde a una domanda alla volta: non cerca su internet, non
  > ricorda le domande precedenti e non fa controlli dopo la risposta. Non
  > offrire azioni che non può eseguire (ricerche sul web o fuori
  > dall'archivio, verifiche successive, seguiti della conversazione) e non
  > chiedere a chi legge di mandarti altri dettagli. Non nominare
  > interrogazioni, parametri, codici dei tipi di beneficiario o altri
  > meccanismi interni. L'unica indicazione ammessa è: "Se vuole un
  > controllo mirato, rifaccia la domanda indicando …", con i dettagli
  > utili (per esempio settore, forma giuridica, comune della sede),
  > oppure il rimando alla pagina del bando.

- **C2**, `ISTRUZIONI`, in "BENEFICIARI DEI BANDI":

  > Se i DATI elencano bandi per un beneficiario generico (le imprese, le
  > Pmi, i datori di lavoro privati) senza un settore che escluda il caso
  > chiesto, nominali come possibili, ciascuno con la condizione da
  > verificare (settore ammesso, dimensione, sede, importi minimi). Non
  > scrivere che misure di quel genere non esistono o non sono presenti:
  > di' che non ci sono bandi specifici in archivio e che questi bandi
  > generici potrebbero valere. Nominali in modo sintetico, raggruppati
  > per tipo di aiuto (per esempio abbattimento degli interessi,
  > garanzie), con al massimo 3-5 esempi e la condizione da verificare;
  > mai l'elenco completo.

  e in "QUANDO NON RISPONDERE", dopo la frase sull'argomento vicino:

  > Un bando dei DATI che ammette il tipo di beneficiario della domanda
  > non è un argomento vicino: vale la regola sui bandi generici in
  > BENEFICIARI DEI BANDI.

  Senza questa seconda riga le due regole si contraddicono, ed è la forma
  di L04 a freddo.

- **C3**, `app/app.py`, `mostra_da_approfondire`: titolo e didascalia
  senza "pertinenti". La sezione contiene anche bandi con la scadenza
  mancante o probabilmente esauriti, non solo quelli senza beneficiari:
  la proposta "Bandi che non ho potuto valutare: beneficiari non indicati
  sulla pagina" va bene solo quando tutte le voci hanno quel problema.
  Scelto il 14 novembre 2026: titolo "Bandi che non ho potuto valutare",
  didascalia "Sulla pagina manca un dato essenziale, indicato per
  ciascuno." Ogni voce porta già il suo problema.

  Filtro sul tema o sul beneficiario della domanda: **scelta l'opzione 1**,
  ora. L'opzione 4 (beneficiari della cooperazione internazionale
  completati a mano dall'avviso, origine `manuale`) va in
  `docs/roadmap.md`, dopo la demo. Le opzioni considerate:

  1. `bandi_per_beneficiario` non mette in "Da approfondire" i bandi
     senza beneficiari: restano solo quelli che ammettono il tipo e hanno
     un problema di scadenza. I bandi senza beneficiari restano in
     `bandi_aperti_per_ente`, `bandi_in_scadenza` e `bandi_per_tema`, dove
     il contesto è l'ente o il tema. Semplice, senza modello. Perde un
     bando senza beneficiari che sarebbe davvero per quel tipo: oggi
     nessuno.
  2. I bandi senza beneficiari si mostrano solo se una parola della
     domanda compare nel titolo o negli interventi, con le regole della
     ricerca di `dettaglio_bando`. Confronto tra parole, non tra
     significati ("rifugi" e le case rifugio); con le domande vaghe la
     sezione resta quasi sempre vuota.
  3. Tabella fissa tipo di beneficiario → temi plausibili. È una scelta
     nostra, senza fonte, e i temi sono categorie larghe ("sociale").
  4. Dato: completare a mano i beneficiari dei bandi senza beneficiari,
     dall'avviso, con la frase come prova e origine `manuale`. Oggi è un
     solo bando. Toglie il caso alla radice ma si ripresenta a ogni bando
     nuovo senza beneficiari, e le righe `manuale` di `beneficiari_bando`
     non sono ancora protette dalla riestrazione (voce 8 della revisione).
     Modifica dei CSV: solo con approvazione.

  Raccomandazione: 1 subito; 4 per la cooperazione internazionale, se
  l'avviso indica i beneficiari.

- **C4**, `app/app.py`, `mostra_fonti`: prima di `st.write`, le righe di
  un blocco che non sono voci d'elenco ("- …") e non sono la prima
  diventano paragrafi a sé, con una riga vuota prima e dopo. Il testo
  dato al modello e al verificatore non cambia. Approvata e implementata.
  **Resta aperto**: l'elemento vuoto visto nell'app online non è
  riprodotto in locale (Streamlit 1.63); la voce si chiude solo dopo il
  confronto con lo screenshot e con la versione di Streamlit dell'app
  online.

  Seconda prova, 14 novembre 2026: l'app online usa Streamlit 1.67.0 su
  Python 3.14.10 (log di Streamlit Cloud). In un ambiente temporaneo con
  Streamlit 1.67.0 (su Python 3.13: la resa del markdown è del frontend,
  incluso nel pacchetto, non di Python) la copia di `mostra_fonti` di prima
  di C4, con il testo grezzo, colonne 3:2 e pagina larga, per i 12 tipi di
  `bandi_per_beneficiario` più il blocco della popolazione, a 1400, 1000 e
  390 px di larghezza: voci quante i bandi, nessuna vuota, nessuna che non
  cominci con "[D", nessuna con il testo sotto il pallino. **Non
  riprodotto: resta aperto** finché non si confronta con lo screenshot.
  Differenze rimaste rispetto all'app online: i dati (l'archivio online
  può essere di un commit diverso), l'interrogazione scelta dal router
  per quella domanda e il browser.

  Aggiornamento del 15 novembre 2026: un caso simile visto nell'app online
  sotto "Frammenti documentali" (A05), con il meccanismo trovato e
  riprodotto; vedi "Osservazioni dall'app online del 15 novembre 2026",
  punto 1.

- **C5**. Le `ISTRUZIONI` lo vietano già, in due punti: "Non usi
  conoscenze tue, non completi con ciò che ti sembra plausibile, non
  deduci" e "Ogni importo, percentuale, data, scadenza, codice o
  riferimento normativo che scrivi deve essere seguito dalla sua fonte".
  Perché non ha funzionato, secondo la diagnosi: la condizione del bando
  è espressa in codici (I 55.1, I 55.3) e la domanda no ("un
  ristorante"); per dire se il ristorante rientra, il modello deve
  collegare l'attività a un codice, e nessun dato lo fa. Le regole parlano
  dei dati dei bandi e dei frammenti; "ATECO 56" è un dato su chi chiede,
  presentato come conoscenza comune e attenuato ("normalmente", "salvo
  verifica"), e il modello non lo tratta come un dato da citare. Riga
  proposta, in "ENTE PER CUI RISPONDI" o in una sezione "CHI CHIEDE":

  > Non attribuire a chi chiede dati che non ha dichiarato e che non sono
  > nei DATI: codice ATECO, dimensione d'impresa, forma giuridica, sede.
  > Se un bando pone una condizione su un codice o su un requisito che
  > chi chiede non ha dichiarato, riporta la condizione con la sua fonte
  > e invita a verificare il proprio dato, senza dire quale sia. Esempio:
  > "il bando è riservato ai codici ATECO I 55.1 e I 55.3 (fonte: …):
  > verifichi il codice della sua attività".

- **C6**, prerequisito della registrazione,
  `scripts/diagnostica/prova_insieme.py`: una registrazione non a freddo
  non aggiunge righe a `lotto_<n>/giudizi.csv`; scrive il suo
  `giudizi.csv` nella propria cartella `lotto_<n>/<data-ora>/`. Il
  `giudizi.csv` del lotto resta solo della registrazione a freddo (e
  delle sue riverifiche). Oggi `registra` chiama `precompila_giudizi`
  sul file del lotto per ogni registrazione.

- **C7**, fonte senza "None", `fonte_bando` in
  `src/database/interrogazioni_bandi.py`: per i bandi senza atto
  (Incentivi Italia) la fonte diventava "…, CC BY 4.0, None (dati
  estratti il …)", e arriva all'interfaccia nelle righe "fonte:" di
  "Fonti" (visto nella diagnosi di C4). Senza atto, la fonte non lo
  nomina.

### Test

- C1, C2, C5: controlli deboli sulla presenza del testo nelle
  `ISTRUZIONI` (il comportamento si misura registrando).
- C3, sull'app (`streamlit.testing`): con una voce da approfondire, la
  sezione ha il titolo nuovo e nessun testo contiene "pertinenti"; senza
  voci la sezione non compare.
- C4, sull'app: il testo reso da `mostra_fonti` per un blocco con i
  gruppi "a sportello" e "senza scadenza", passato a un parser markdown
  (`markdown-it-py`, già installato con Streamlit): tante voci quante
  righe di bando, nessuna voce vuota, nessuna intestazione di gruppo
  dentro una voce.
- C3, interrogazione: con un bando senza beneficiari aperto,
  `bandi_per_beneficiario` non lo mette in "Da approfondire";
  `bandi_aperti_per_ente` sì, come prima.
- C6: una registrazione con `a_freddo` falso non modifica il
  `giudizi.csv` del lotto e scrive il suo nella propria cartella.
- C7: la fonte di un bando senza atto non contiene "None".

### Regole di chiusura (sul lotto 1 registrato di nuovo)

- Nessuna risposta offre azioni che l'app non può fare. Controllo
  automatico sulle 17 risposte, con un'espressione regolare su "posso
  verificare", "posso cercare", "posso controllare", "mi indichi",
  "può indicarmi", "mi faccia sapere", "interrogare", "parametr",
  "bandi_per_", "altra_impresa"; più la lettura a mano di tutte le
  risposte.
- In L04 i bandi generici restituiti dai dati sono nominati come
  possibili, con la condizione da verificare; nessun "Non trovo la
  risposta".
- Nessuna intestazione chiama "pertinenti" bandi non valutati (test
  dell'app e controllo a mano su una domanda dall'app).
- Nessun elemento vuoto in "Fonti" (test dell'app e controllo a mano
  sulla domanda del data center dall'app).
- In L02 nessun codice ATECO che non sia nei dati.
- In L04 i bandi generici sono raggruppati per tipo di aiuto, con al più
  3-5 esempi, non l'elenco completo.
- Dopo la registrazione, `lotto_1/giudizi.csv` è identico a prima (C6).
- Nessuna fonte con "None" nelle 17 registrazioni (C7).

## Correzione D: dalla registrazione non a freddo del lotto 1

Aggiunta il 14 novembre 2026. Viene dalla registrazione non a freddo
`dati-grezzi/prova/lotto_1/2026-11-14_140416`, fatta dopo le correzioni
1, 2, 3, A e C, confrontata con quella a freddo (`2026-11-14_114121`).
Fermata 1: solo diagnosi e proposte, nessun codice.

### D1. Risposte troncate da max_tokens

**Difetto.** L02 usa 4096 token in uscita nella risposta in tutte e due le
registrazioni, e il testo finisce a metà ("…(fon"); L03 arriva a 3128,
P18 a 2919.

**Causa.** `max_tokens=4096` del modello di risposta, in
`costruisci_catena` di `src/chains/rag.py` (con `timeout=120`). Come per il
router (correzione 1), con `claude-sonnet-5` il ragionamento adattivo è
attivo, i suoi token contano in `max_tokens` e il suo testo non arriva
nella risposta. Misura: il testo puro rende circa 2,4 caratteri per token
(A01, C11, P25 a freddo); L02 ne rende 0,63 (2599 caratteri su 4096
token), quindi circa 1.100 token di testo e 3.000 di ragionamento. A
freddo L04 rendeva 0,42 (563 caratteri su 1355 token). La risposta più
lunga osservata ha 4305 caratteri (P17 a freddo), circa 1.800 token di
testo.

**Correzione proposta.**

- `max_tokens` della risposta da 4096 a **16000**: quasi quattro volte il
  massimo osservato (4096, troncato), con spazio per circa 3.000 token di
  ragionamento più la risposta più lunga, anche raddoppiati. Resta sotto
  la soglia oltre cui l'SDK `anthropic` (1.5.0) chiede lo streaming,
  circa 21.333 token (`_calculate_nonstreaming_timeout`: 3600 s ×
  max_tokens / 128.000 > 600 s). Non costa niente se non si usa: si pagano
  i token prodotti. Una costante `MAX_TOKENS_RISPOSTA`, come
  `MAX_TOKENS_ROUTER`.
- `timeout` da 120 a 300 secondi: con 16.000 token possibili, 120 s
  potrebbero non bastare a una risposta lunga.
- Non si usa `thinking: {"type": "disabled"}`, per lo stesso motivo del
  router: dà 400 su `claude-sonnet-5-5`, e il modello si cambia dal `.env`.
- `stop_reason` della risposta: la catena oggi termina con
  `StrOutputParser`, che tiene solo il testo. Proposta: la catena assegna
  il messaggio intero del modello e ne ricava due campi, `risposta` (il
  testo, estratto come oggi) e `stop_reason_risposta`
  (`response_metadata["stop_reason"]`). Nella prova, `registra_domanda`
  salva `stop_reason_risposta` nel file della domanda, accanto a
  `stop_reason_router`; il rapporto conta le risposte finite per
  `max_tokens`, con i codici.
- Nell'app, se la risposta finisce per `max_tokens`: sopra la risposta un
  avviso (`st.warning`) "La risposta si è interrotta perché troppo lunga:
  è incompleta e può mancare l'ultima parte. Rifaccia la domanda in modo
  più circoscritto (per esempio un solo tipo di bando)." In fondo al testo
  la riga "[risposta interrotta]", così non sembra completa nemmeno se
  copiata. Verifica e fonti restano come sono.

**Test proposti.** `max_tokens` della risposta almeno 16000; con un
modello finto che restituisce `stop_reason: max_tokens` la catena espone
`stop_reason_risposta`; la prova lo salva; l'app mostra l'avviso e la riga
finale con `max_tokens` e non li mostra con `end_turn` (sull'app, con
`streamlit.testing`).

### Decisioni del 15 novembre 2026

- D1: approvato come proposto (`max_tokens` 16000, `timeout` 300,
  `stop_reason_risposta` nella prova e nel rapporto, avviso nell'app e
  "[risposta interrotta]" in fondo).
- D2: approvata la regola con l'esempio sbagliato e quello giusto. Se il
  codice ricompare dopo la misura ristretta, si accetta il limite per la
  demo. "56.10" letto come 56 e 10 va in "In coda" della roadmap, unito
  alla voce sugli identificativi con trattino spezzati.
- D3: approvata la riscrittura, senza sostituire "archivio" (sotto).
- D4: si corregge ora (sotto).
- D5: il file delle domande non si modifica (sotto).
- `--codici`: approvato come proposto.

Stato al 15 novembre 2026: D1, D3 e `--codici` implementati per primi.
D2 e D4 cambiavano l'esito di un test esistente ciascuno; modifiche
approvate e applicate dopo:

- D2: `test_c5_niente_dati_attribuiti_a_chi_chiede`
  (`tests/test_presentazione.py`) riscritto sul testo nuovo ("Non scrivere
  mai il codice ATECO", "Sbagliato:", "Giusto:", e nessun "56.10" né
  "ristorante" nelle istruzioni).
- D4: `test_decreto_con_il_blocco_non_si_controlla`
  (`tests/test_verifica_bandi.py`), che affermava il comportamento di
  prima, sostituito da due test: numero nel blocco verificato, numero
  fuori dal blocco non trovato.

**Esempio di D2, deciso il 15 novembre 2026.** L'esempio sbagliato non
contiene un codice ATECO vero né l'attività di L02: sarebbe tarare il
prompt sulla domanda con cui lo si misura, e una coppia vera
attività-codice può spingere il modello a scriverla. Testo applicato:

> Sbagliato: "Un'attività come la sua di solito ha il codice ATECO
> [codice]: verifichi il suo codice."
> Giusto: "Il bando è riservato ai codici I 55.1 e I 55.3 (fonte: [D1.4],
> <atto del bando>): verifichi se il codice della sua attività è tra
> questi."

La citazione nell'esempio giusto c'è perché le istruzioni chiedono la
fonte per ogni codice. La regola sopra, in "Regola proposta", resta come
proposta; vale il testo applicato.

La misura ristretta si fa ora, con D1-D4 applicati.

### D2. C5 non ha funzionato

**Difetto.** L02 scrive ancora "Un ristorante tipicamente ha codice ATECO
56.10, diverso da quelli indicati: verifichi…", e già prima, tra
parentesi, "l'attività di ristorazione (codice ATECO 56.10)". Il modello
ha aggiunto il "verifichi" della regola, ma ha tenuto il codice.

**Regola proposta**, al posto della sezione "CHI CHIEDE" di C5:

> CHI CHIEDE
> Non scrivere mai il codice ATECO, la dimensione d'impresa, la forma
> giuridica o la sede di chi chiede se non le ha scritte lui: nemmeno
> come ipotesi ("normalmente", "tipicamente", "di solito"), nemmeno tra
> parentesi, nemmeno seguite da "verifichi". Il codice di un'attività non
> si ricava dal nome dell'attività.
> Sbagliato: «Un ristorante tipicamente ha codice ATECO 56.10: verifichi
> il suo codice.»
> Giusto: «Il bando è riservato ai codici ATECO I 55.1 e I 55.3 (fonte:
> [D1.4], <atto del bando>): verifichi se il codice della sua attività è
> tra questi.»

**Basta un'istruzione?** Secondo me può ridurre il caso, non escluderlo.
La domanda chiede di confrontare un'attività con condizioni scritte in
codici, e il modello colma il passaggio con quello che sa; la regola di
C5 era già esplicita e il modello l'ha seguita a metà. Proposta: provare
la regola nuova sulla misura ristretta (L02 tre volte); se il codice
compare ancora, accettare il limite per la demo. Il verificatore lo
segnala già: in L02 "56" e "10" sono "non trovato, non presente in nessuna
fonte recuperata", quindi la risposta non è verde.

Osservazione sul verificatore, da mettere in coda: "56.10" è letto come
due numeri, 56 e 10, non come un codice ATECO unico (la correzione del 13
novembre riconosce "49.34.00" e "I 55.1", non un codice a due parti senza
lettera). Oggi va bene perché nessuno dei due è nelle fonti; un "10"
presente per caso in una fonte risulterebbe verificato.

### D3. C1 a metà: meccanismi interni nelle risposte "Non trovo"

**Difetto.** C11: "Per rispondere servirebbe un'interrogazione mirata ai
bandi sul tema del dissesto idrogeologico… Se vuole un controllo mirato,
rifaccia la domanda indicando questo tema specifico" (la domanda lo
diceva già); A01: "Servirebbero frammenti relativi all'apertura degli
impianti sciistici… non sono presenti tra quelli forniti"; L05: "non
rientra tra i dati statistici o i frammenti documentali a mia
disposizione".

**Causa.** Tutte e tre nascono dalla riga che segue "Non trovo la
risposta", che chiede "cosa servirebbe per rispondere" senza dire in che
termini: il modello risponde con i nomi del prompt (FRAMMENTI, DATI).

Testo attuale di "QUANDO NON RISPONDERE" (`src/chains/rag.py`):

> QUANDO NON RISPONDERE
> Se frammenti e dati non contengono la risposta, scrivi esattamente:
>   "Non trovo la risposta nei documenti disponibili."
> seguito da una riga che indica cosa servirebbe per rispondere.
> Un frammento che parla di un argomento vicino ma non della cosa chiesta
> NON è una risposta.
> Un bando dei DATI che ammette il tipo di beneficiario della domanda non
> è un argomento vicino: vale la regola sui bandi generici in BENEFICIARI
> DEI BANDI.

Riscrittura proposta:

> QUANDO NON RISPONDERE
> Se frammenti e dati non contengono la risposta, scrivi esattamente:
>   "Non trovo la risposta nei documenti disponibili."
> seguito da una riga che dice quale bando o documento servirebbe, con
> parole che chi legge capisce: per esempio "servirebbe un bando per la
> difesa del suolo" o "servirebbe il calendario di apertura degli
> impianti". Non parlare di frammenti, dati forniti, interrogazioni,
> parametri o temi dell'archivio: chi legge non li vede.
> Aggiungi "Se vuole un controllo mirato, rifaccia la domanda indicando …"
> solo se mancano dettagli che chi chiede non ha dato e che cambierebbero
> la risposta (settore, forma giuridica, comune della sede); mai per
> ripetere quello che la domanda dice già.
> Un frammento che parla di un argomento vicino ma non della cosa chiesta
> NON è una risposta.
> Un bando dei DATI che ammette il tipo di beneficiario della domanda non
> è un argomento vicino: vale la regola sui bandi generici in BENEFICIARI
> DEI BANDI.

**Archivio: deciso il 15 novembre 2026.** Le `ISTRUZIONI` usano
"archivio" in tre frasi ("di' che sono quelli in archivio con dati
completi", "di' che non ci sono bandi specifici in archivio", "il dato
non è in archivio"). "In archivio" resta ammesso, perché chi legge lo
capisce, e le tre frasi non si riscrivono. Sono vietate solo le parole
del sistema: frammenti, dati forniti, interrogazioni, parametri, temi
come termine tecnico. Nella riscrittura, quindi, il divieto è: "Non
parlare di frammenti, dati forniti, interrogazioni, parametri o temi
dell'archivio: chi legge non li vede."

**Test.** Deboli, sulla presenza del testo: la riga nuova, il divieto
delle parole del sistema, il "rifaccia la domanda" solo per i dettagli
mancanti.

### D4. C11 senza esiti del verificatore (solo diagnosi)

**Difetto.** C11 ha 0 esiti, ma la risposta contiene "(fonte: [D1], Portale
bandi Regione Toscana, decreto dirigenziale 22706 del 9 ottobre 2026)".

**Causa.** Il numero e la data stanno dentro la citazione, e il
verificatore controlla le citazioni in un punto solo, `_verifica_atti` in
`src/verification/controllo.py`, che per scelta controlla i numeri d'atto
solo nelle citazioni a un bando `[Dn.k]` o a un frammento `[n]`: "Le
citazioni a un blocco [Dn] non si controllano: non si sa di quale bando
sia l'atto." `trova_dati` lavora sul testo con le citazioni mascherate,
quindi non vede né 22706 né la data; il resto della risposta non ha
numeri. Risultato: nessun esito, e la risposta non ha né verde né rosso.

Il decreto è giusto (22706 è l'atto della riga [#1] del blocco, i
contributi per la progettualità sui dati), ma la citazione viola la regola
"Non citare con [D1] un dato che appartiene a un solo bando". Due
possibili correzioni, da decidere dopo: controllare il numero nel testo
del blocco intero (dice se l'atto esiste nel blocco, non di quale bando);
oppure segnalare come "citazione generica" un atto citato con [Dn] invece
che con [Dn.k], come già si fa per gli altri dati citati con il blocco.

**Deciso il 15 novembre 2026: correggere ora, con la prima.** Un numero
d'atto in una citazione a un blocco `[Dn]` si cerca in tutto il blocco
(il suo testo con le fonti): trovato vale verificato, non trovato vale non
trovato, con la data scritta accanto controllata come per gli altri atti.
Test: numero giusto citato con [D1] verificato; numero sbagliato citato
con [D1] non trovato.

### D5. L05, attesa mancante (solo diagnosi)

**Difetto.** L05 ha l'attesa "deve cercare anche nei bandi" mancante,
anche se il router ha usato `bandi_per_tema` con "pesca".

**Causa.** Nel file delle domande, la riga di L05 ha come atteso "deve
cercare anche nei bandi" senza il prefisso "a mano:". Lo script la legge
come titolo atteso, e `controlla_attese` cerca le attese solo tra i titoli
dei bandi citati: una frase che non è un titolo è sempre mancante. Era
mancante anche a freddo (dove il router era fallito). Lo si vede dai file
del lotto 1 (`attese`: ["deve cercare anche nei bandi"], `a_mano`:
["domanda ricostruita dalla risposta"]), senza aprire il file delle
domande. Correzione: aggiungere "a mano:" a quell'atteso nel file delle
domande (fuori dal repository); cambia l'impronta delle domande, che le
registrazioni annotano. Nel merito l'attesa è soddisfatta: il router ha
cercato nei bandi.

**Deciso il 15 novembre 2026: il file delle domande non si modifica.**
L'attesa di L05 risulta mancante per il prefisso "a mano:" assente: è un
falso mancante noto, da non contare come difetto, e da correggere nel
file a lotti finiti.

### Misura ristretta

Oggi `prova_insieme` registra solo un lotto intero: `--registra --lotto N`
prende tutte le domande del lotto. Proposta: `--codici L02,C11,A01,L05`,
solo con `--registra --lotto N`.

- Registra solo quei codici, nell'ordine dato, nella propria cartella
  `lotto_<n>/<data-ora>/`, sempre non a freddo (`a_freddo: false`), con i
  codici scelti in `meta.json` (`codici_scelti`).
- Si rifiuta se il lotto non ha ancora una registrazione a freddo
  completa: una registrazione parziale non può diventare quella a freddo.
- Si rifiuta un codice che non è nel lotto.
- Giudizi nella propria cartella (C6); `--riepilogo` non la conta, perché
  non è a freddo.
- `--riprendi` di una registrazione parziale riprende solo i codici
  scelti.
- L02 tre volte: tre corse con `--codici L02` (tre cartelle), più una con
  `--codici C11,A01,L05`. Costo stimato, dai costi misurati nella
  registrazione del 14 novembre: L02 circa 0,09 $ a corsa, che con
  `max_tokens` a 16000 può salire fino a circa 0,15 $; C11, A01, L05 circa
  0,04 $ l'una. Totale tra 0,40 e 0,60 $.

### Regole di chiusura (sulla misura ristretta)

Su L02 registrata 3 volte e su C11, A01, L05 una volta:

- nessuna risposta finisce per `max_tokens` (`stop_reason_risposta`);
- nessun codice ATECO assente dai dati (controllo automatico sui valori
  "non trovato" vicini a "ATECO", più lettura a mano);
- nessuna frase su frammenti, interrogazioni o archivi: controllo
  automatico con un'espressione regolare su "frammento", "frammenti",
  "interrogazion", "parametr", "dati forniti", "tra quelli forniti",
  "dati statistici", più lettura a mano ("archivio" è ammesso e non entra
  nel controllo);
- in C11 nessun "rifaccia la domanda" che ripete il tema già chiesto.

### Esito della misura ristretta (15 novembre 2026)

Registrazioni non a freddo con `--codici`, in `dati-grezzi/prova/lotto_1/`:
`2026-11-15_182642`, `_182748`, `_182911` (L02, tre volte) e `_183034`
(C11, A01, L05). Tutte e quattro con il proprio `giudizi.csv` (C6).

- **D1 chiusa.** 6 risposte su 6 con `stop_reason_risposta` "end_turn".
  Token in uscita della risposta: L02 2984, 4661 e 3821; L05 2528; C11
  224; A01 46. La L02 da 4661 token sarebbe stata troncata con il tetto
  vecchio di 4096.
- **D2 accettata come limite per la demo.** Un codice ATECO non presente
  nei dati compare in 1 corsa su 3 di L02 (`_182642`: "codice ATECO I
  56"), segnalato dal verificatore come non trovato. Nelle altre due
  nessun codice attribuito a chi chiede. La soluzione è in
  `docs/roadmap.md`, "Prossimi passi", voce Pratiche: tabella ATECO
  ufficiale.
- **D3 chiusa con un residuo.** C11 e A01 corrette: niente "interrogazione
  mirata" né "frammenti". L05 scrive ancora "i frammenti e i dati a
  disposizione": 1 risposta su 6 con una parola del sistema.
  Secondo residuo, nel lotto 3 a freddo (15 novembre 2026, con D3
  applicata): A03, "Quanti abitanti ha San Marcello Piteglio?", chiude con
  "Servirebbe un'interrogazione sulla popolazione specifica del Comune di
  San Marcello Piteglio". "Interrogazione" è tra le parole vietate da D3;
  la riga giusta era del tipo "servirebbe il dato ISTAT della popolazione
  di San Marcello Piteglio", o l'avviso che il profilo è di un altro ente
  (l'attesa a mano di A03). Si conta come residuo, non come difetto
  nuovo. Con l'espressione regolare della regola di chiusura di D3, le
  risposte con una parola del sistema dopo D3 sono 3 su 32: L05 della
  misura ristretta (6 risposte), A05 del lotto 2 a freddo, "frammenti"
  (13), A03 del lotto 3 a freddo, "interrogazione" (13).
- **D4 chiusa.** C11 ha 3 dati verificati; nella registrazione del 14
  novembre ne aveva 0.
- **Nota.** In una L02 (`_182748`) la delibera 704/2025 è citata con
  un'etichetta sbagliata: sta in [D1.8]. È un errore del modello, e il
  verificatore lo segnala correttamente come non trovato. Stesso caso nel
  lotto 3 a freddo: P01 cita "I 55.1" e "I 55.3" con [D1.7], mentre
  stanno in [D1.16]; il verificatore li dà non trovati, "presente invece
  in ['D1.16']", e il giudizio a mano è `errore_vero`. Due casi in due
  registrazioni: da tenere d'occhio, non da correggere ora.

Osservazione su D1, dalla verifica delle versioni del 15 novembre 2026:
con `anthropic` 1.5.0 il controllo dell'SDK che chiede lo streaming
oltre circa 21.333 token scatta solo quando il timeout non è dato; noi
passiamo `timeout=300`, quindi oggi non si applica. La scelta di 16000
resta valida; con un'altra versione dell'SDK il comportamento va
ricontrollato (vedi il confronto delle versioni prima del push).

## Confronto delle versioni prima del push (15 novembre 2026)

Locale: `.venv`, Python 3.13.12. Online: log di Streamlit Cloud del 14
novembre 2026 (`dati-grezzi/streamlit-log-2026-11-14.txt`, righe
"+ pacchetto==versione"), Python 3.14.10. Prima `requirements.txt` aveva
solo vincoli minimi (per esempio `streamlit>=1.40`): online si installava
l'ultima versione di ogni pacchetto.

| pacchetto | locale (fissato) | online il 14/11 | cambio maggiore |
|---|---|---|---|
| Python | 3.13.12 | 3.14.10 | no (versione minore) |
| anthropic | 1.5.0 | 2.8.0 | **sì** |
| langchain-anthropic | 1.7.2 | 1.7.10 | no |
| langchain-core | 1.6.2 | 1.8.0 | no |
| langchain-text-splitters | 1.1.2 | 1.1.3 | no |
| langchain-chroma | 1.1.0 | 1.1.0 | no |
| langchain-huggingface | 1.2.2 | 1.2.3 | no |
| chromadb | 1.5.9 | 1.5.9 | no |
| sentence-transformers | 6.0.1 | 6.3.0 | no |
| streamlit | 1.63.0 | 1.67.0 | no |
| psycopg[binary] | 3.3.6 | 3.3.9 | no |
| pgvector | 0.5.0 | 0.5.1 | no |
| pypdf | 6.18.1 | 7.1.0 | **sì** (solo ingestione) |
| numpy | 2.5.3 | 2.5.4 | no |
| rank-bm25 | 0.2.2 | 0.2.2 | no |
| python-dotenv | 1.2.3 | 1.2.4 | no |
| torch (non fissato) | 2.14.0 | 2.15.0 | no |
| transformers (non fissato) | 5.17.0 | 5.23.0 | no |
| pandas (non fissato) | 3.0.5 | 3.1.1 | no |

L'unico cambio maggiore rilevante per l'app è `anthropic`. L'app non lo
importa: passa da `ChatAnthropic` di `langchain-anthropic`, che riempie
`response_metadata["stop_reason"]` (letto dal router, correzione 1, e
dalla risposta, D1); il testo senza ragionamento lo estraggono `.text` e
`StrOutputParser` di `langchain-core`. `langchain-anthropic` 1.7.2 richiede
`anthropic<2.0.0`: online, con 2.8.0, girava per forza un'altra versione
(1.7.10). `pypdf` serve solo all'ingestione dei PDF, non all'app.

### Decisione (15 novembre 2026)

- Strada (a): in `requirements.txt` le versioni di `.venv` fissate con
  `==` per tutte le dipendenze dirette, più `anthropic` e
  `langchain-huggingface`, che il codice usa. Sono le versioni dei 1044
  test e della misura ristretta.
- `torch` non si fissa. Il codice non lo importa; `sentence-transformers`
  6.0.1 chiede solo `torch>=2.2`. Fissarlo a 2.14.0 imporrebbe online una
  versione mai provata lì, mentre la 2.15.0 è quella con cui l'app gira
  online oggi. Fissare `sentence-transformers` non fissa `torch`: la
  differenza possibile sono minime variazioni numeriche negli embedding
  della domanda, senza effetto atteso sul recupero.
- Python online invariato (3.14.10): non si ripubblica l'app.
- Verifica senza installare: `pip install --dry-run -r requirements.txt`
  sul `.venv` non ha niente da installare e `pip check` non trova
  conflitti; `pip install --dry-run --only-binary=:all: --python-version
  3.14 --platform manylinux…` risolve tutte le versioni fissate per Linux
  con Python 3.14 con ruote binarie (135 pacchetti; `torch` 2.15.0,
  `transformers` 5.23.0, `pandas` 3.1.1).
- Se l'installazione su Streamlit Cloud fallisce: `git revert` del commit
  delle versioni, poi Python 3.13 con una nuova pubblicazione dell'app.

## Correzione E: risposte parziali (dal lotto 2)

Aggiunta il 15 novembre 2026, dalla diagnosi della registrazione a freddo
del lotto 2 (`dati-grezzi/prova/lotto_2/2026-11-15_191851`). Solo A05; le
altre osservazioni della diagnosi vanno in roadmap (sotto).

### Difetto

A05, "Cos'è la Strategia nazionale per le aree interne?": la risposta è
"Non trovo la risposta nei documenti disponibili", con la motivazione che
lo studio CENSIS "analizza gli effetti della Strategia senza definirla".
Tra i 10 frammenti recuperati ce n'erano di utili: CENSIS pag. 39 (la
Strategia risponde allo spopolamento delle aree interne con interventi
articolati sulla specificità dei territori), pag. 38 (gli interventi che
la Strategia nazionale sta mettendo in campo contro il declino
demografico), pag. 5 (le iniziative della Missione 5 del Pnrr che la
affiancano); dall'avviso regionale (decreto 9550/2026, pag. 4) la
Strategia regionale per le aree interne (DGR 1476/2022) attuata con
l'Investimento Territoriale Integrato. Una definizione formale manca, ma
una risposta parziale con citazione era possibile.

Causa: "QUANDO NON RISPONDERE" ammette solo due casi ("Se frammenti e dati
non contengono la risposta, scrivi esattamente: …"; "Un frammento che
parla di un argomento vicino ma non della cosa chiesta NON è una
risposta"), rinforzati da "non deduci" della REGOLA FONDAMENTALE: il
modello ha letto "definizione assente" come "risposta assente".

### Regola (E1, applicata)

In `ISTRUZIONI` (`src/chains/rag.py`), "QUANDO NON RISPONDERE", prima della
riga sull'argomento vicino:

> Risposta parziale: solo se i frammenti parlano proprio della cosa
> chiesta ma non rispondono a tutto (per esempio la descrivono senza
> definirla), non scrivere "Non trovo la risposta": riporta quello che
> dicono. Ogni frase della risposta parziale ha la sua citazione (fonte:
> [n], …), non solo i dati. Quello che viene da uno studio si presenta come
> tale ("secondo lo studio …"). Chiudi con una riga su cosa manca (per
> esempio "Nei documenti disponibili non c'è una definizione formale della
> …"). Non completare con conoscenze tue. Se i frammenti parlano di un
> argomento diverso, anche vicino, la risposta resta "Non trovo la
> risposta nei documenti disponibili."

La regola dice "frammenti", non "estratti": è la parola che il prompt usa
oggi per il contesto; la rinomina è una voce a parte della roadmap.

Limite: il verificatore controlla numeri, date e atti, non le frasi
descrittive. Per questo ogni frase deve avere la sua citazione, così il
lettore può confrontarla con il frammento; la fedeltà della parafrasi si
giudica a mano.

### Test

Deboli, sulla presenza del testo (`tests/test_presentazione.py`): le
cinque condizioni della regola e la sua posizione, dopo l'inizio di
"QUANDO NON RISPONDERE" e prima della riga sull'argomento vicino.

### Regola di chiusura

- A05 (lotto 2, due corse): risponde con quello che dicono i frammenti,
  ogni frase citata, una riga su cosa manca, niente "Non trovo la
  risposta".
- Domande di controllo che devono restare "Non trovo la risposta nei
  documenti disponibili." senza descrizioni prese da argomenti vicini:
  C14, C15, C16 (lotto 2), A01, C11 (lotto 1).
- Nessun nuovo non trovato del verificatore.

Nota sul punto di partenza: a freddo C15 e C16 non erano già del tutto
"pulite". C15 nomina il «Bando Amianto Edifici Pubblici 2026» come bando
"con finalità diversa"; C16 scrive "Non trovo nei documenti disponibili
bandi specifici…" ed elenca i bandi sul tema turismo. Tutte e due passano
dai DATI (`bandi_per_tema`, nessun frammento), non dai frammenti a cui si
rivolge E1. Il confronto si fa quindi con la registrazione a freddo:
conta che E1 non aggiunga descrizioni di argomenti vicini, e che le
risposte restino "Non trovo"; i bandi vicini nominati dai dati sono un
caso da decidere a parte, insieme alla regola sui bandi generici (C2).

## Osservazioni dall'app online del 15 novembre 2026

Solo diagnosi e proposte, niente codice.

### 1. Elenchi numerati nei "Frammenti documentali"

**Osservato.** Domanda A05 ("Cos'è la Strategia nazionale per le aree
interne?"), profilo Abetone Cutigliano, prima del riavvio dell'app: sotto
alcune voci di "Frammenti documentali" elementi di elenco numerato vuoti,
"1." sotto [5], "6." sotto [6], "2." sotto [8]. Dopo il riavvio, stessa
domanda, non compaiono.

**Meccanismo, trovato e riprodotto.** `mostra_fonti` scrive il testo di
ogni frammento con `st.write`, che lo legge come markdown. Il campo è il
testo del frammento (`page_content`), non un metadato: i frammenti che
cominciano con il numero di un paragrafo dell'avviso diventano elenchi
numerati. Nella registrazione a freddo di A05 (lotto 2) sono [5] "1.
Premessa Il Programma…", [6] "6. Strumenti per la realizzazione…", [8]
"2. Obiettivi e finalità…" (decreto 9550/2026) e [10] "2. PRIME
RIFLESSIONI…" (CENSIS). Riprodotto con Streamlit 1.63 e 1.67, in Edge senza
interfaccia, con la stessa sezione di `mostra_fonti`: in [5], [6], [8] e
[10] il testo è un `<ol>` (con `start="6"` e `start="2"` dove il numero
non è 1), a una voce, con dentro tutto il frammento. Il numero del
paragrafo diventa così il numero dell'elenco, fuori dal testo.

**Non riprodotto: la voce vuota.** Nella prova locale l'elenco ha il suo
testo accanto al numero, ed è nascosto quando l'espansore è chiuso; la
voce senza testo vista online non si ottiene. Né la versione di Streamlit
né la copia del testo della pagina (provata: la selezione non riporta i
numeri) la spiegano. Perché compaia solo a volte resta aperto: il
meccanismo dipende solo dal testo del frammento, quindi con gli stessi
frammenti dovrebbe ripetersi sempre; se dopo il riavvio la domanda ha
recuperato gli stessi frammenti, la differenza sta nella resa o nella
visualizzazione, non nei dati. Serve uno screenshot dopo il riavvio con
gli espansori [5], [6], [8] aperti.

**Il "*" vuoto sotto [D1] (C4).** Stessa famiglia (testo reso come
markdown), ma non lo stesso caso: il blocco [D1] è già un elenco scritto
dal programma ("- [#k] …"), e nessuna riga dei 12 tipi di
`bandi_per_beneficiario` comincia con un segno d'elenco senza testo. Resta
aperto come C4. Chiuso il 15 novembre 2026 sera come artefatto della copia
della pagina (vedi "Decisioni e stato" sotto). La voce vuota sotto [5],
[6] e [8] ha probabilmente la stessa spiegazione, non verificata; gli
elenchi numerati di quei frammenti sono comunque corretti con
`testo_letterale`.

**Correzione proposta (non implementata).** Il testo dei frammenti si
mostra come testo, non come markdown: una funzione `testo_letterale` in
`app/app.py` che mette una barra rovesciata davanti ai caratteri che il
markdown di Streamlit interpreta (`\ ` * _ { } [ ] ( ) # + - . ! | < > $ ~`),
usata in `mostra_fonti` per il testo del frammento. Il markdown resta solo
per quello che scrive il programma (intestazioni, elenco dei bandi).
`st.text` eviterebbe il problema ma mostra il testo a larghezza fissa e
senza a capo automatico, illeggibile in una colonna stretta. Il `$` conta:
in Streamlit una coppia di `$` apre una formula.

**Test proposto, che fallisce oggi.** Sull'app (`streamlit.testing`):
`mostra_fonti` con un frammento il cui testo è "1. Premessa Il Programma
Regionale…"; il valore markdown reso, passato a `markdown-it-py`, non
deve contenere un elenco numerato (`ordered_list_open`), e il testo reso
deve cominciare con "1. Premessa". Oggi il primo controllo fallisce.

### 2. Cache: un push non basta a cambiare le istruzioni

**Osservato.** Dopo il push della correzione E (commit d3630c7) l'app
online rispondeva ancora ad A05 con il rifiuto vecchio; dopo il riavvio
risponde con la regola nuova.

**Confermato nel codice, due cause insieme.**

- `carica_catena` in `app/app.py` è sotto `@st.cache_resource`, con chiave
  `codice_ente`: la catena di un ente si costruisce una volta per processo,
  e con lei il prompt (`MODELLO_PROMPT`, fatto con `ISTRUZIONI` quando
  `src/chains/rag.py` viene importato). La chiave della cache comprende il
  codice della funzione decorata e i suoi argomenti, non i moduli che
  importa: un cambio in `src/` non la invalida.
- Anche senza la cache, il modulo resterebbe vecchio. Streamlit ricarica
  solo i moduli che tiene sotto controllo, cioè quelli nella cartella dello
  script principale o in una cartella del `PYTHONPATH`
  (`streamlit/watcher/local_sources_watcher.py`, `_file_should_be_watched`).
  Lo script è `app/app.py`, e `src/` sta fuori da `app/`; `app.py` aggiunge
  la radice del progetto a `sys.path`, non al `PYTHONPATH`. Così
  `src.chains.rag` resta in `sys.modules` con le `ISTRUZIONI` di quando il
  processo è partito, finché il processo non riparte.

**Proposta (non implementata).** Una versione del codice calcolata a ogni
esecuzione dello script: l'impronta dei file `.py` di `src/`. Se cambia
rispetto a quella con cui sono stati caricati i moduli, si tolgono i
moduli `src.*` da `sys.modules` (così l'import successivo legge il codice
nuovo) e la versione entra nella chiave di `carica_catena` e di
`carica_recupero` (così la cache costruisce una catena nuova). Un push
basta: alla prima domanda dopo il push la catena si ricostruisce.
Alternative scartate: `server.folderWatchList` vuole percorsi assoluti,
diversi in locale e su Streamlit Cloud; spostare lo script nella radice
del progetto metterebbe `src/` sotto controllo, ma su Streamlit Cloud
cambia il percorso del file principale dell'app; `importlib.reload` di
singoli moduli non ricarica chi li importa. Test: con la versione
cambiata, la cache restituisce una catena diversa e `sys.modules` non ha
più i moduli vecchi.

### 3. Nome del modello

`src/config.py`: `MODEL_NAME = os.getenv("MODEL_NAME", "claude-sonnet-5")`,
dopo `load_dotenv` del `.env` della radice. Lo usano la risposta
(`src/chains/rag.py`), il router (`src/chains/router.py`) e l'estrattore.
L'app non legge `st.secrets` direttamente; su Streamlit Cloud le voci di
primo livello dei secrets arrivano anche come variabili d'ambiente, quindi
vale `MODEL_NAME` dei secrets se c'è, altrimenti il predefinito
`claude-sonnet-5`. In locale il `.env` ha `MODEL_NAME=claude-sonnet-5`,
come il README. I secrets online da qui non si vedono.

Se online il valore è diverso: risposta e router girano su un altro
modello, e le misure della prova (fatte in locale, con il modello scritto
nel `meta.json` di ogni registrazione) non valgono per l'app online. Due
punti del codice dipendono dal modello: `max_tokens` della risposta (16000)
e del router (2048) sono tarati sul ragionamento adattivo di
`claude-sonnet-5`, e il parametro `thinking: disabled` non si usa perché
su `claude-sonnet-5-5` dà errore 400 (correzione 1). Da controllare nei
secrets di Streamlit Cloud; da valutare se mostrare il nome del modello
nella barra laterale, come la data dell'archivio.

### Decisioni e stato (15 novembre 2026)

- **Punto 1, applicato.** `testo_letterale` in `app/app.py` mette una barra
  rovesciata davanti ai caratteri del markdown (barra rovesciata, `` ` ``,
  `*`, `_`, graffe, quadre, tonde, `#`, `+`, `-`, `.`, `!`, `|`, `<`, `>`,
  `$`, `~`), solo per il testo dei frammenti in `mostra_fonti`; il blocco
  dei dati resta markdown. Test sull'app (`tests/test_presentazione.py`):
  un frammento "1. Premessa…" non dà `ordered_list_open` e il testo reso
  comincia con "1. Premessa"; un frammento con due `$` li ha tutti e due
  preceduti dalla barra e resi come testo. Tutti e due falliscono con il
  codice di prima (provato rimettendo il testo com'era). La voce vuota
  vista online e il "*" sotto [D1] restano aperti. Il "*" sotto [D1] è
  chiuso il 15 novembre 2026 sera come artefatto della copia (C4, ultima
  voce di questo elenco); la voce vuota sotto [5], [6] e [8] ha
  probabilmente la stessa spiegazione, non verificata.
- **Punto 2, la ricostruzione automatica non si implementa** (né la
  pulizia di `sys.modules` né l'impronta nella chiave della cache): va in
  `docs/roadmap.md`, "Dopo la demo", da provare con calma. Al suo posto:
  - `impronta_istruzioni()` in `src/chains/rag.py`: i primi 8 caratteri
    dello sha256 di `ISTRUZIONI` più `ISTRUZIONI_ROUTER` (che sta in
    `src/chains/router.py`). Le descrizioni del repertorio, che il router
    riceve a ogni domanda, non ne fanno parte;
  - nella barra laterale la riga "Modello: <MODEL_NAME> · istruzioni
    <impronta>" (`riga_versione` in `app/app.py`);
  - nel README, sezione "App online", la procedura: dopo un push che tocca
    `src/`, Reboot app da Streamlit Cloud, poi confronto dell'impronta
    della barra laterale con quella locale (`python -c "from src.config
    import MODEL_NAME; from src.chains.rag import impronta_istruzioni;
    print(MODEL_NAME, impronta_istruzioni())"`);
  - test: l'impronta cambia se cambiano `ISTRUZIONI` o
    `ISTRUZIONI_ROUTER`; la riga compare nella barra laterale (AppTest) e
    `main` la scrive.
- **Punto 3**: il nome del modello è ora visibile nella barra laterale,
  nella stessa riga dell'impronta.
- **C4, chiuso come artefatto della copia, non come difetto** (15 novembre
  2026, sera). App online con commit 625f7d6 e impronta delle istruzioni
  1d4591b8, domanda "Vorrei prendere un giovane in tirocinio, ci sono
  incentivi?". Con gli espansori di "Fonti" chiusi, la copia della pagina
  mostrava due elementi di elenco vuoti sotto [D1]; con gli espansori
  aperti la copia mostra tutto il testo di [D1] (22 bandi e le righe
  "fonte:") e poi [D2], senza voci vuote. A schermo non compaiono voci
  vuote. Le voci vuote erano il contenuto degli espansori chiusi, che la
  copia non riporta. Gli elenchi numerati dei frammenti ("1. Premessa"
  ecc., punto 1) erano invece un difetto vero, già corretto con
  `testo_letterale`.

## Correzione F: dal lotto 3

Aggiunta il 15 novembre 2026, dalla diagnosi della registrazione a freddo
del lotto 3 (`dati-grezzi/prova/lotto_3/2026-11-15_215106`, commit
7117aa4). Ordine: prima F1, poi F2.

### Decisioni e stato (15 novembre 2026)

- **F1a approvata e applicata** in `src/chains/rag.py`: "ENTE DI
  RIFERIMENTO" al posto di "ENTE PER CUI RISPONDI", nelle `ISTRUZIONI` e
  nell'intestazione del messaggio umano; in "CHI CHIEDE", prima del
  divieto di D2, la regola per privato, ente e caso ambiguo (risposta per
  il privato, al più una riga "Se a chiedere è il Comune, …"; "l'Unione"
  se l'ente di riferimento è l'Unione). **Differenza dalla proposta**:
  negli esempi del privato senza soggetto, "vorrei assumere" e "prendere
  un tirocinante" sono sostituiti da "vorrei inserire un apprendista" e
  "devo comprare un macchinario", e la riga del caso ambiguo dice
  "riservati a <beneficiari del bando>" invece di "datori di lavoro
  privati". Motivo, lo stesso di D2: le prime due sono le domande P05 e
  P24 con cui si misura la regola, e tarare il prompt su di esse
  renderebbe la misura inutile. Un test lo protegge.
- **F1b non implementata**: solo se F1a non regge alla misura.
- **F2: scelta (c2)**, limite accettato per la demo: C18 resta "Non
  trovo", corretto per "bandi aperti per il Comune". (b) e (c1) vanno in
  `docs/roadmap.md`, "Dopo la demo", con il costo stimato.
- **F3 approvata e applicata** (sotto).

### F1. Il profilo dell'ente preso per chi chiede (P24, P05)

**Difetto.** P24, "Vorrei prendere un giovane in tirocinio, ci sono
incentivi?": il router sceglie `bandi_per_beneficiario` con
`altra_impresa`, la risposta trova i due bandi per datori di lavoro
privati (tirocinanti under 35, [D1.19]; tirocini per donne in uscita
dalla violenza, [D1.17]) e poi conclude: "Il Comune di Abetone Cutigliano
è un ente pubblico (fonte: profilo dell'ente) … non rientra tra i
beneficiari di queste due misure". **P05 ("Vorrei assumere una persona,
ci sono incentivi?") ha lo stesso difetto**: tre bandi per datori di
lavoro privati, poi "un Comune non rientra tra i beneficiari previsti".
L'attesa di P05 risulta trovata perché il bando è tra i citati, ma la
conclusione è sbagliata.

Estensione, cercata con un'espressione regolare su tutte le risposte del
gruppo privati registrate (lotti 1, 2, 3): oltre a P05 e P24, solo P18
del lotto 1 a freddo ("il profilo per cui rispondo è il Comune …, non una
startup innovativa"), sparita nella registrazione successiva. Le altre
domande del gruppo dichiarano chi chiede ("ho un albergo", "sono una
guida ambientale", "la mia impresa") e non hanno il difetto. P05 e P24
non lo dichiarano: descrivono un'azione da datore di lavoro, e il
modello riempie il soggetto mancante con il profilo.

**Causa.** Tre punti del prompt dicono che l'ente del profilo è chi
chiede, e nessuno dice il contrario:

- `ISTRUZIONI`, "ENTE PER CUI RISPONDI": "Ricevi il profilo dell'ente che
  pone la domanda … Usalo per valutare se l'ente rientra tra i
  beneficiari di un bando."
- il messaggio umano di `MODELLO_PROMPT` comincia con "ENTE PER CUI
  RISPONDI:" seguito dal profilo;
- "CHI CHIEDE" parla solo dei dati da non attribuire (ATECO, dimensione,
  forma, sede: D2), non di chi sia chi chiede.

Il router invece separa già i due casi ("Per i bandi rivolti ad altri
soggetti del territorio (imprese, associazioni, cittadini) usa
bandi_per_beneficiario"), e in P05 e P24 ha scelto bene. Il modello di
risposta non riceve quella distinzione.

**Regola proposta (F1a)**, solo `ISTRUZIONI` e l'intestazione del
messaggio umano in `src/chains/rag.py`:

- "ENTE PER CUI RISPONDI" diventa "ENTE DI RIFERIMENTO", con la prima
  frase: "Ricevi il profilo dell'ente di riferimento: indica il
  territorio e l'ente per cui lavora l'app, non per forza chi scrive la
  domanda. Usalo per valutare se l'ente rientra tra i beneficiari di un
  bando quando a chiedere è l'ente." Il resto della sezione resta.
  Stessa intestazione nel messaggio umano.
- In "CHI CHIEDE", prima del divieto di D2:

  > Chi chiede può essere l'ente di riferimento o un soggetto del suo
  > territorio. È un soggetto del territorio quando la domanda parla di
  > un'impresa, un'attività, una professione, un'associazione o di sé
  > come privato ("ho un albergo", "sono una guida", "la mia azienda"),
  > o descrive un'azione da datore di lavoro o da impresa senza nominare
  > l'ente ("vorrei assumere", "prendere un tirocinante", "aprire
  > un'attività"), e i DATI sono bandi per un tipo di beneficiario
  > privato. In quel caso i requisiti dei bandi si confrontano con quello
  > che dice chi chiede, mai con il profilo: non scrivere che l'ente non
  > rientra tra i beneficiari. Il profilo serve solo per il territorio.
  > Se la domanda può venire da tutti e due (nessun soggetto nominato),
  > rispondi per il soggetto privato e aggiungi al più una riga: "Se a
  > chiedere è il Comune, questi bandi non lo ammettono: sono per datori
  > di lavoro privati (fonte: …)."
  > È l'ente quando la domanda dice "il Comune", "l'Unione", "possiamo
  > partecipare", "il nostro ente", o parla di opere, uffici e servizi
  > pubblici.

**Come si distingue nella domanda.** Soggetto privato dichiarato
(attività, professione, "la mia impresa"): privato. Ente nominato o
"noi" con oggetti pubblici (piazza, uffici, illuminazione pubblica):
ente. Nessun soggetto e azione da datore di lavoro o da impresa: privato,
con la riga per il caso Comune. Il segnale di riserva è la scelta del
router, visibile al modello nell'intestazione del blocco ("interrogazione:
bandi_per_beneficiario", "Bandi aperti per altre imprese").

**Casi ambigui.**

- "Vorrei assumere una persona" (P05): anche un Comune assume, ma con
  concorsi, non con incentivi all'occupazione. Si risponde per il privato,
  con la riga sul Comune.
- Domande senza soggetto su oggetti che hanno tutti e due ("il
  fotovoltaico", "un edificio"): P09 dice "su un'azienda" ed è privata;
  senza "azienda" decide il router (ente o beneficiario), e la risposta
  segue i DATI.
- Privato che nomina un comune diverso dal profilo ("ho un negozio a
  Sambuca" con il profilo di Abetone): il comune della domanda vale per
  la sede, il profilo no; è la voce 13 della roadmap, non F1.
- Terzo per conto di un cliente ("un mio cliente ha un albergo"): si
  tratta come il cliente dichiarato.
- Persona che vuole avviare un'attività ("sono giovane e voglio aprire
  un'azienda agricola", P03): è un privato anche se l'impresa non esiste
  ancora; i requisiti di costituzione restano condizioni da verificare.
- Associazioni, enti del terzo settore, parrocchie: privati ai fini di F1,
  anche se la parola "ente" compare.

**Alternativa (F1b), solo se F1a non passa la regola di chiusura.** Il
programma aggiunge al messaggio una riga "CHI CHIEDE: un soggetto del
territorio diverso dall'ente (tipo: <tipo>)" quando tutte le
interrogazioni scelte sono `bandi_per_beneficiario`; nessuna riga con
interrogazioni miste o per ente. Pro: deterministica, si prova senza
modello, nello spirito di "il router decide una volta, il codice
esegue". Contro: eredita gli errori del router e non copre le domande con
interrogazioni miste (P09: `bandi_per_beneficiario` e `bandi_per_tema`).

**Test.** F1a: deboli, sul testo (`tests/test_presentazione.py`):
l'intestazione nuova in `ISTRUZIONI` e nel messaggio umano, nessuna
"ente che pone la domanda", la regola in "CHI CHIEDE" prima del divieto
di D2 con i tre casi (privato, ente, ambiguo). F1b, se serve: con una
decisione di soli `bandi_per_beneficiario` il messaggio ha la riga, con
`bandi_aperti_per_ente` o mista no.

### F2. C18: l'avviso pertinente sta solo nei documenti

**Difetto.** C18, "Ci sono bandi per rafforzare gli uffici tecnici con
personale?": router `bandi_aperti_per_ente`, `documenti: false`, in
tutte e tre le chiamate; risposta "Non trovo la risposta nei documenti
disponibili." Nell'archivio documentale c'è l'avviso regionale del
decreto 9550 del 28/04/2026 (PR FESR 2021-2027, sub-azione 5.2.1.5),
"Progetti di rafforzamento amministrativo degli enti Capofila delle Aree
interne", che ammette personale dipendente con contratto a tempo
determinato (paragrafo 6).

**Perché il router non ha consultato i documenti.** Le istruzioni del
router (`ISTRUZIONI_ROUTER`, `src/chains/router.py`) mandano le domande
sui bandi alle interrogazioni: "Quando la domanda riguarda opportunità di
finanziamento, bandi aperti, scadenze o ammissibilità, usa le
interrogazioni sui bandi. Una domanda come 'possiamo partecipare a
qualche bando?' richiede bandi_aperti_per_ente". "documenti": true è
riservato a "regole, procedure o contenuti di atti" e al bando nominato
("usa dettaglio_bando … e metti 'documenti': true"). Due degli esempi
("Ci sono bandi aperti per le aziende agricole…", "Vorrei avviare una
nuova attività: ci sono contributi?") hanno `documenti: false`. C18 è
una domanda generica sui bandi, senza bando nominato: per le istruzioni,
la scelta del router è quella giusta.

**L'avviso non è nella tabella dei bandi.** Né in `bandi.csv` né in
`scansioni.csv` c'è il decreto 9550 o una pagina sul rafforzamento
amministrativo delle aree interne. I due canali di acquisizione sono
separati: il PDF è entrato nel vector store con l'ingestione dei
documenti; la tabella si riempie dagli elenchi "bandi aperti" di
`elenchi.csv`, scansionati la prima volta il 15 settembre 2026. Il
termine dell'avviso è "il trentesimo giorno successivo alla
pubblicazione sul BURT" (paragrafo 11): la data assoluta non è nel
documento (i metadati del vector store hanno `data_scadenza` vuota e
"data assoluta non indicata nel documento"). Con il decreto del 28
aprile, la pagina era con ogni probabilità già fuori dagli elenchi
"bandi aperti" al 15 settembre: è un'ipotesi, da verificare con la data
del BURT.

**Anche nella tabella, C18 non lo troverebbe con `bandi_aperti_per_ente`,
per due motivi.** I beneficiari sono solo i sei Capofila delle Aree
interne, con una quota fissa di 244.475,00 euro ciascuno e procedura
negoziale (paragrafi 3 e 4); per l'area di Abetone Cutigliano è l'Unione
Comuni Garfagnana, e il profilo ha `capofila_area: no`. E l'avviso è con
ogni probabilità scaduto. Inoltre il personale serve all'attuazione
della Strategia d'area e alla governance, non agli uffici tecnici del
Comune: per la regola dell'argomento vicino, anche con i documenti la
risposta potrebbe restare "Non trovo". La risposta utile sarebbe: nessun
bando aperto per il Comune; c'è stato un avviso regionale per il
Capofila dell'Area interna, che può assumere personale a tempo
determinato per la Strategia, chiuso (o con il termine da verificare).

**Opportunità solo nei documenti (stima in sola lettura).** L'archivio
documentale ha 5 PDF, 316 frammenti: lo studio CENSIS (75), le linee
guida SNAI sul requisito associativo (21), il progetto "Ludoteche di
montagna" del Comune (27), l'avviso 9550 (76) e l'avviso dei mercati
rionali, decreto 13287 del 10/06/2026 (117). Gli avvisi sono due: i
mercati rionali sono anche in tabella (`mercati-rionali-2026`, scaduto il
15/10/2026); il 9550 è l'**unica** opportunità solo nei documenti. Lo
studio e le linee guida nominano finanziamenti come analisi (importi
2014-2020 per cluster), non come avvisi; il progetto è un intervento già
finanziato dall'APQ. Il numero crescerà con i PDF dei bandi (voce 4 dei
prossimi passi), che però entrano collegati a un bando della tabella.

**Alternative.**

- **(a) Il router consulta i documenti per "ci sono bandi/finanziamenti
  per …".** Pro: trova gli avvisi solo nei documenti, una riga nelle
  istruzioni. Contro: oggi ne guadagna un avviso su cinque PDF, e per C18
  quell'avviso non è per il Comune; aggiunge a quasi ogni domanda sui
  bandi 10 frammenti per lo più fuori tema (CENSIS, ludoteche), con il
  rischio che E1 (risposta parziale) o un argomento vicino entrino nelle
  risposte "Non trovo" di controllo (C01, C20); i frammenti non sanno lo
  stato del bando quando la scadenza non è una data (il 9550). **Costo**:
  le risposte con documenti hanno 9.400-10.000 token in ingresso contro
  3.760-4.030 senza, a parità di dati (A01, A05 contro A01, A02, A03):
  circa +5.900 token, cioè +0,012 $ a domanda a 2 $ per milione. Nel
  lotto 3 le domande sui bandi con `documenti: false` sono 10 su 13:
  circa +0,12 $ a lotto, costo medio da 0,052 a circa 0,061 $ (più
  qualche token in uscita, non stimato).
- **(b) L'avviso entra nella tabella dei bandi con la sua fonte.** Pro:
  stato calcolato dalla scadenza, interrogazioni e verificatore come per
  ogni bando, storico dei bandi scaduti. Contro: serve la pagina
  ufficiale e la data del BURT per la scadenza (un dato non verificato
  resta vuoto, e senza scadenza va in "Da approfondire"); non esiste un
  tipo di beneficiario "capofila dell'area interna", e senza quello o
  compare a tutti i comuni o a nessuno; per C18 non cambia niente, perché
  è scaduto e non per il Comune.
- **(c1) Il router riceve l'elenco dei documenti.** Accanto a
  "CONTENUTO EFFETTIVO DELL'ARCHIVIO NUMERICO", una sezione con titolo,
  tipo e atto di ciascun documento, letti dai metadati del vector store
  (gli stessi in Chroma e in Postgres), e una regola: "documenti: true
  anche quando la domanda generica sui bandi riguarda l'oggetto di un
  avviso dell'elenco". Pro: costo piccolo (circa 150 token per 5
  documenti, per 3 chiamate del router: meno di 0,001 $ a domanda);
  documenti consultati solo quando serve; C01 e C20 restano senza
  documenti. Contro: giudizio del router sul confronto tra domanda e
  titolo; con molti PDF l'elenco cresce; una funzione nuova
  nell'interfaccia del recupero, con test sui due motori.
- **(c2) Limite accettato per la demo.** La risposta "Non trovo" è
  corretta per "bandi aperti per il Comune", e la riga "servirebbe un
  bando … per il finanziamento di personale tecnico negli uffici
  comunali" è leggibile. Dopo la demo, (b) insieme ai PDF dei bandi e a un
  tipo di beneficiario per i Capofila.

**Raccomandazione.** Prima della demo c2, o c1 se si vuole che C18
nomini l'avviso; (a) no: costa su ogni domanda e mette a rischio le
risposte di controllo per un solo avviso. (b) dopo la demo.

**Test (solo con c1).** L'elenco dei documenti nel prompt del router
ha un titolo per documento, uguale da Chroma e da Postgres (test su un
archivio in memoria); la regola nuova è nelle istruzioni del router
(debole).

### F3. Niente trattini lunghi

**Richiesta.** Le risposte e le righe dell'app non usano il trattino
lungo (—) né quello medio (–) come segno di inciso.

**Applicato.**

- `ISTRUZIONI`, sezione nuova "PUNTEGGIATURA" dopo "COSA PUÒ FARE
  L'APP": niente trattino lungo né medio come inciso, al loro posto
  virgole, due punti o parentesi; i titoli dei bandi si riportano come
  sono scritti nei DATI, anche con un trattino.
- `app/app.py`, `mostra_da_approfondire`: "titolo — motivo · contatti"
  diventa "titolo: motivo · contatti". Era l'unico "—" nelle stringhe
  dell'app e di `src/database/`. I titoli dei bandi non si toccano: sono
  dati della fonte.

**Test** (`tests/test_presentazione.py`): la regola è nelle istruzioni;
nessun "—" né "–" nelle costanti di testo di `app/*.py` e
`src/database/*.py` (letti con `ast`, comprese le parti delle f-string);
"Da approfondire" con un titolo che contiene "–" e "—" lo mostra intatto,
con ": " come separatore.

### Test di F1

`tests/test_presentazione.py`: intestazione "ENTE DI RIFERIMENTO" nelle
istruzioni e nel messaggio umano, nessun "ENTE PER CUI RISPONDI" né
"ente che pone la domanda"; in "CHI CHIEDE" privato, ente e caso
ambiguo, in quest'ordine e prima del divieto di D2; nessun "assumere" né
"tirocin" nelle istruzioni. Tutti, tranne l'ultimo, falliscono con il
codice di prima (provato).

### Regola di chiusura (scritta prima di registrare)

Misura ristretta con `--codici` sul lotto 3, non a freddo:
`--codici P24,P05` due volte e `--codici C18,C01,C20,C17,C10,P01,P07` una
volta. Costo stimato dai costi a freddo: circa 0,27 $ per le due corse di
P24 e P05, circa 0,35 $ per le altre, totale circa 0,62 $.

- **F1.** In P24 e P05 (4 risposte) nessuna conclusione sull'ente del
  profilo: controllo automatico con un'espressione regolare su "non
  rientra", "ente pubblico", "amministrazione pubblica", "in quanto
  (ente|amministrazione)" e su "(fonte: profilo dell'ente)", più lettura a
  mano. I bandi per datori di lavoro privati sono presentati come
  possibili, con le condizioni (datore privato, sede in Toscana);
  ammessa al più una riga per il caso in cui chieda il Comune. P05 trova
  ancora il bando atteso.
- **F1, controlli.** C17 e C10 (chiede l'ente) usano ancora il profilo:
  C17 elenca i bandi aperti per il Comune (attese 2/2), C10 confronta la
  soglia di 5.000 abitanti con la popolazione del Comune. P01 e P07
  (privati dichiarati) non cambiano tipo di risposta.
- **F2 (c2).** C18 entra nella misura come controllo: resta "Non trovo la
  risposta nei documenti disponibili.", con una riga su cosa servirebbe
  senza parole del sistema. C01 e C20 restano `documenti: false` e "Non
  trovo la risposta nei documenti disponibili."
- **F3.** Nessun "—" né "–" usato come inciso nelle 11 risposte misurate
  (controllo automatico sui due caratteri, poi a mano: un trattino dentro
  il titolo di un bando, come nei DATI, è ammesso).
- Nessun nuovo non trovato del verificatore; nessuna risposta interrotta.

### Esito della misura ristretta (15 novembre 2026)

Cartelle `dati-grezzi/prova/lotto_3/2026-11-15_225703`, `_225811` e
`_225921`. Regola di chiusura rispettata.

- **F1.** P24 e P05 rispondono a chi scrive in 4 corse su 4, con la riga
  "Se a chiedere è il Comune ..." dove serve.
- **F1, controlli.** C17 e C10 usano il profilo; P01 e P07 invariati.
- **F2 (c2).** C01, C20 e C18 restano "Non trovo".
- **F3.** Nessun trattino lungo nelle 11 risposte.

### Da contare nel lotto 4, senza correggerli ora

Due schemi ricorrenti, da contare nella registrazione del lotto 4:

- **Numero ripetuto in una frase "verifichi ..." dopo la citazione.** Viene
  legato alla citazione successiva (P05: "under 35" cercato in D1.16 invece
  che in D1.19) o resta senza fonte (app online: "Verifichi sulla pagina
  del bando under 35 ..." segnato "?", con il semaforo arancione su una
  risposta corretta). Nasce dalle frasi "verifichi" di C5 e D2.
- **Delibera di giunta regionale 704/2025 citata con l'etichetta
  sbagliata**, per la terza volta (L02 `_182748`; P01 `_225921`, con D1.9
  invece di D1.8), sempre nell'elenco dei bandi PMI simili.
