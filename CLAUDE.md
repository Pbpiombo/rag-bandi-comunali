# CLAUDE.md

Istruzioni per lavorare su questo repository. Valgono per ogni sessione.

## Il progetto

Assistente RAG per la programmazione territoriale dell'Unione di Comuni Montani
Appennino Pistoiese e dei suoi tre comuni. Risponde sui bandi citando la fonte
di ogni dato; un verificatore meccanico controlla che ogni dato citato compaia
nella fonte dichiarata. L'utente sceglie l'ente da un menu nell'app.

- Recupero documentale: Postgres con pgvector (Supabase) in produzione, Chroma
  in locale. Entrambi dietro la stessa interfaccia `cerca(domanda, k)`.
- Dati strutturati: SQLite in `data/db/comune.sqlite`, **rigenerato dai CSV**
  in `data/processed/`, che sono la fonte di verità.
- Due canali di acquisizione:
  - documenti PDF verso il vector store (`scripts/ingestione/ingest_tutti.py`,
    `src/ingestion/`);
  - bandi verso la tabella `bandi` (`src/estrazione/`, `scopri_bandi`,
    `estrai_bando`, `estrai_nuovi`), con `scansioni` come registro delle
    pagine già esaminate.
- Dati grezzi (PDF scaricati, pagine salvate, registri delle richieste,
  prove, copie di sicurezza) in `dati-grezzi/`, accanto alla cartella del
  progetto, non dentro: sono fuori dal repository.

Lingua: codice, commenti, docstring e README in **italiano**, come il resto
del progetto. Rispondi sempre in italiano, anche dopo un /clear.

## Comandi

```
python -m pytest                                  # test
ruff check                                        # controlli
ruff format <file modificati>                     # formattazione
python -m scripts.tutorial.step4_crea_db          # crea e popola SQLite dai CSV
streamlit run app/app.py                          # interfaccia
```

Il registro dei PDF degli avvisi (`data/processed/documenti_bandi.csv`) si
genera da tutte le cartelle degli scarichi insieme:
`python -m scripts.ingestione.registra_avvisi --data 2026-11-19 --data 2026-11-20`
(con `--controlla` confronta senza scrivere). Una cartella in più si aggiunge
come un altro `--data`.

Per ricreare il database dopo una modifica allo schema:
`Remove-Item data\db\comune.sqlite`, poi `step4_crea_db`. Prima, verifica che
bandi e scansioni siano esportati nei CSV (`aggiorna_csv` in `schema.py`).

## Prima di dichiarare finito un compito

- `ruff check`: nessuna segnalazione nuova rispetto a prima. Le segnalazioni
  già note (BLE001, ISC004, DTZ011) sono in coda e non vanno aumentate.
- `python -m pytest`: tutti i test passano; i test `xfail` restano tali.
- Riporta l'**output** di entrambi, non un riassunto.
- Se hai modificato uno script, importalo per verificare che parta:
  `python -c "import scripts.<cartella>.<nome>"`.

## Regole per le modifiche

- Un compito alla volta. Non toccare file estranei al compito.
- Prima di implementare, proponi: file da creare o modificare, e per ogni
  file esistente il motivo. Aspetta l'approvazione. Vale anche per i
  documenti in `docs/`.
- Se il messaggio chiede di vedere prima il diff o il piano, mostralo e
  fermati: non applicare.
- Se sposti o rinomini una funzione, cerca in tutto il progetto chi la
  importa e aggiorna ogni punto.
- Non lanciare `ruff format` su tutto il progetto: solo sui file modificati.
- Le query SQL sono stringhe e `ruff` non le controlla: ogni query nuova o
  modificata va eseguita almeno una volta, o coperta da un test.
- I test usano il database in memoria di `tests/conftest.py`, mai quello vero.
  Per il codice che legge pagine web, test su pagine salvate, non sui siti.
- Un test nuovo deve fallire senza la modifica che protegge: verificalo
  prima di dichiararlo.
- Se un test esistente va modificato, fermati prima e spiega perché.
- `ISTRUZIONI` e `ISTRUZIONI_ROUTER` non si modificano senza una regressione
  contro la baseline (`docs/piano-insieme-prova.md`). Le revisioni esterne
  dei prompt non si applicano direttamente.
- Una tabella nuova in SQLite va aggiunta a `TABELLE_DA_CSV` ed esportata,
  altrimenti si perde alla prima ricreazione del database.
- - Quando proponi un comando di commit, aggiungi sempre in fondo
  -m "Co-Authored-By: <il tuo modello> <noreply@anthropic.com>".
- A fine giornata si propone il push, anche a passo aperto, perché il
  lavoro del giorno non resti solo in locale. Il push si fa solo con
  l'approvazione esplicita (vedi "Mai").
- Prima di approvare un file prodotto (rapporto, CSV, foglio), se ne
  leggono alcune righe vere, non solo il riepilogo o il conteggio.
- Nei file del repository i percorsi verso dati-grezzi si scrivono relativi
  (`..\dati-grezzi\...`), mai assoluti.

## Documenti

- `docs/roadmap.md` contiene solo stato, principi, ordine dei passi e
  decisioni, e deve restare leggibile in una volta: intorno alle 200 righe,
  senza un limite rigido. Il lavoro chiuso sta in `docs/fatto.md`, le voci
  in attesa in `docs/coda.md`, il dettaglio nei `docs/piano-*.md`. Non si
  taglia contenuto per rientrare in un numero. La roadmap si rivede a ogni
  chiusura di passo: le parti fatte scendono in `docs/fatto.md`.
- Quando si divide o si sposta un documento, il testo si sposta parola per
  parola e non si cancella. Ogni voce spostata porta "(era la voce N di …)".
- Se una parte viene riassorbita invece che spostata, dichiaralo e cerca in
  `docs/`, `src/` e `scripts/` chi la cita per numero.
- I numeri dei passi della roadmap non cambiano: gli altri documenti li
  citano. I passi nuovi prendono un numero nuovo, e l'ordine di lavoro sta
  nella riga "Ordine di esecuzione".
- Un testo vecchio da ricopiare si prende da un file o da un commit
  (`git show <commit>:<file>`), con la fonte scritta accanto. Mai dalla
  memoria della sessione.
- I documenti scritti da un modello esterno hanno in testa "Revisione
  esterna" o "Studio esterno", e si salvano solo dopo un controllo delle
  citazioni o una verifica a mano, con le righe verificate marcate
  "verificato a mano il …".

## Principi del progetto

- Il modello non scrive SQL: sceglie un'interrogazione dal repertorio chiuso
  (`src/database/repertorio.py`) e ne indica i parametri.
- Il codice dell'ente lo passa il programma, mai il modello. Le interrogazioni
  per ente hanno `per_ente=True` e ricevono il codice come argomento separato.
- Ogni dato in `data/processed/` ha la sua fonte e la data di verifica. Non
  inserire dati senza fonte; un dato non verificato resta vuoto, non diventa
  un valore plausibile.
- Lo stato di un bando (aperto o chiuso) si calcola dalla scadenza, non si
  memorizza.
- Percorso fisso, niente agent: il router decide una volta, il codice esegue.
- Lettura dei siti: per le pagine si rispettano i limiti espliciti,
  cioè robots.txt, blocchi tecnici e condizioni d'uso scritte. I PDF
  degli avvisi dei bandi si scaricano una volta sola anche se il
  robots.txt li vieta, quando la pagina del bando è consentita, con
  pause tra le richieste e con l'intestazione che dichiara il progetto;
  ogni caso si annota nel registro delle richieste. Un rifiuto tecnico
  del sito è un limite: non si aggira, si riporta. Dove non c'è un
  limite esplicito, le pagine pubbliche si leggono, con poche richieste.
- I contesti per frammento scritti da un modello servono solo a cercare: non
  si citano, non si mostrano e non arrivano al verificatore, che lavora sul
  testo pulito del frammento.

## Mai

- Committare `.env` o qualunque credenziale.
- Fare commit o push se non richiesto esplicitamente.
- Usare `--unsafe-fixes` di ruff.
- Caricare gli avvisi dei bandi su Postgres (l'app online) fuori dal passo
  19e. Il 19d è chiuso sotto soglia (23/11/2026): gli avvisi vanno online
  solo insieme al filtro per bando e al "non lo trovo", dopo la rimisura
  su Postgres prevista nel 19e e con il via esplicito di chi mantiene il
  progetto. Fino ad allora stanno solo nel Chroma locale. Con il motore in
  memoria (un solo motore, due archivi: `docs/piano-19e.md`, "Decisioni del
  25/11/2026") la rimisura è l'identità degli ordini: l'app online deve dare,
  sulle serie del 19d, gli stessi primi 10 frammenti nello stesso ordine
  dell'app in locale. Se cambia il motore (taglio a livelli, ricerca fatta da
  Postgres), serve una rimisura nuova con una regola scritta prima.
- Modificare i CSV in `data/processed/` a mano senza dirlo: sono dati
  verificati.
- Leggere domande, rapporti o giudizi di un lotto dell'insieme di prova non
  ancora registrato a freddo, e aprire il lotto 4 senza un'istruzione
  esplicita (`docs/piano-insieme-prova.md`, "Metodo dei lotti").
- Leggere la metà di controllo dei fatti (domande, frasi, esiti) o
  misurarla senza un via esplicito (`docs/piano-insieme-prova.md`,
  "Divisione in taratura e controllo").
- Rigenerare le schede di etichettatura senza un'istruzione esplicita: i
  giudizi a mano stanno solo nella copia di lavoro, fuori dal repository.
- Mettere nei file nomi di persone, email o dati personali: il repository
  è pubblico. Per le persone si usa il ruolo ("consulente pilota",
  "revisore tecnico").
