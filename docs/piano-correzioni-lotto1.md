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
