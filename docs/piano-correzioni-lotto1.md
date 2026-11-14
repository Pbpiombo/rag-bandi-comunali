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
5. Una nuova registrazione dell'intero lotto 1: circa 0,90 $, non a freddo.
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
un elenco chiuso, il tema è testo libero con esempi ("casa" compreso, che in
archivio non c'è). L'elenco chiuso dei temi esiste solo nel prompt
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
