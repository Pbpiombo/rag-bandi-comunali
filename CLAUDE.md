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
  file esistente il motivo. Aspetta l'approvazione.
- Se sposti o rinomini una funzione, cerca in tutto il progetto chi la
  importa e aggiorna ogni punto.
- Non lanciare `ruff format` su tutto il progetto: solo sui file modificati.
- Le query SQL sono stringhe e `ruff` non le controlla: ogni query nuova o
  modificata va eseguita almeno una volta, o coperta da un test.
- I test usano il database in memoria di `tests/conftest.py`, mai quello vero.
  Per il codice che legge pagine web, test su pagine salvate, non sui siti.
- Una tabella nuova in SQLite va aggiunta a `TABELLE_DA_CSV` ed esportata,
  altrimenti si perde alla prima ricreazione del database.

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

## Mai

- Committare `.env` o qualunque credenziale.
- Fare commit o push se non richiesto esplicitamente.
- Usare `--unsafe-fixes` di ruff.
- Modificare i CSV in `data/processed/` a mano senza dirlo: sono dati
  verificati.
- Leggere domande, rapporti o giudizi di un lotto dell'insieme di prova non
  ancora registrato a freddo, e aprire il lotto 4 senza un'istruzione
  esplicita (`docs/piano-insieme-prova.md`, "Metodo dei lotti").
- - Il repository è pubblico: niente nomi di persone, email o dati
  personali nei file. Per le persone si usa il ruolo.