# RAG Bandi Comunali

Assistente per la programmazione territoriale dei piccoli comuni montani.
Trova i bandi a cui un ente può partecipare, spiega cosa serve per presentare
domanda, e **cita la fonte di ogni dato che riporta**.

Il progetto nasce da un interesse personale e da contatti con chi lavora sui bandi nei comuni montani. È un progetto di portfolio, ma la struttura è pensata per diventare uno strumento reale: costruita per un’Unione di comuni, si può estendere ad altri enti e ad altre fonti di bandi


**[Prova la demo online](https://rag-bandi-comunali-yxhfmuxc5k4cg96rnxeeka.streamlit.app/)**

Caso di studio: l'**Unione di Comuni Montani Appennino Pistoiese** e i suoi
tre comuni, Abetone Cutigliano, Sambuca Pistoiese e San Marcello Piteglio, tutti
nell'area interna Garfagnana - Lunigiana - Media Valle del Serchio - Appennino
Pistoiese. L'utente sceglie da un menu l'ente per cui sta lavorando, e il
sistema risponde per quell'ente.

---

## Il problema

Le opportunità di finanziamento per un comune sono sparse in decine di
documenti: avvisi regionali, linee guida nazionali, delibere, studi di settore.
Chi deve scrivere un piano d'azione ha due problemi: trovare l'informazione, e
non sbagliarla. Un importo o una scadenza errati in un atto amministrativo sono
un danno reale.

Un modello linguistico da solo non risolve né l'uno né l'altro: produce comunque
una risposta, plausibile e potenzialmente inventata.

## L'approccio

Tre presidi sovrapposti, di cui l'ultimo non probabilistico.

1. **Frammenti etichettati.** Ogni pezzo di documento passato al modello porta
   con sé ente, tipo di atto, livello di governo e pagina.
2. **Prompt vincolante.** Ogni importo, data o codice deve essere seguito dalla
   sua fonte; è vietato combinare dati di documenti diversi in una stessa
   affermazione; se i frammenti non contengono la risposta, il sistema lo
   dichiara invece di costruire qualcosa.
3. **Verifica meccanica.** Ogni dato citato viene cercato nel testo della fonte
   dichiarata. O c'è, o non c'è.

Il terzo strato è coperto da test automatici, con casi positivi e negativi, che
dimostrano che il controllo intercetta davvero gli errori invece di limitarsi a
non segnalare nulla.

## Come funziona

Il sistema tiene due archivi separati, e un router decide quale interrogare.

| Archivio | Contiene | Risponde a |
|---|---|---|
| Vector store | Testo dei documenti, diviso in chunk | "Cosa dice questo bando?" |
| Database relazionale | Enti, bandi, demografia, dati territoriali | "Quali bandi possiamo usare?" |

I dati numerici **non** stanno nel vector store: una ricerca semantica su una
tabella può restituire il valore vicino a quello giusto, e il modello lo
presenterebbe come corretto. Una query SQL o restituisce il valore esatto o non
restituisce niente.

### Il profilo dell'ente

Ogni ente ha un profilo, letto dalla tabella `enti`: tipo (comune o unione),
regione, provincia, area interna, se è capofila dell'area, se rientra in
Toscana Diffusa. Ogni valore ha la sua fonte nel CSV da cui viene caricato.

Il profilo arriva in due punti. Il router lo usa per capire se una domanda
riguarda bandi a cui l'ente può accedere. Il modello che scrive la risposta lo
usa per valutare l'ammissibilità, e lo cita come fonte quando lo fa. Un valore
non verificato resta tale: il sistema lo dichiara, invece di trattarlo come un
no.

Il codice dell'ente lo sceglie l'utente dal menu, e il programma lo passa a ogni
interrogazione. **Il modello non lo vede e non può sceglierlo**: decide quale
interrogazione eseguire e con quali parametri, mai su quale ente. Ogni dato
numerico è legato al suo ente nel database, e le interrogazioni filtrano sempre
per quell'ente: un comune senza dati di popolazione ottiene "dato non
disponibile", non i numeri di un altro comune.

### Il recupero documentale

Il recupero è **ibrido**: somiglianza semantica (embedding multilingua,
calcolati in locale) unita a corrispondenza lessicale esatta, con fusione RRF.
Serve perché la ricerca densa non sa agganciare codici e riferimenti normativi
come `41/2022` o un CUP.

Il vector store esiste in due versioni intercambiabili, che espongono la stessa
interfaccia:

| | `RecuperoIbrido` | `RecuperoPostgres` |
|---|---|---|
| Vettori | Chroma, su disco | Postgres + pgvector |
| Ricerca lessicale | BM25 in memoria | full-text italiano di Postgres |
| Dove gira | in locale | Postgres gestito (Supabase) |

La scelta si fa con la variabile d'ambiente `USA_POSTGRES`. La catena riceve
l'oggetto di recupero come parametro e non sa quale dei due stia usando: chiede
`recupero.cerca(domanda, k=k)` e riceve una lista di tuple. Nell'app il recupero
è uno solo, condiviso da tutti gli enti, perché i documenti sono gli stessi.

Le risposte delle due versioni sono state confrontate sulle stesse domande e
coincidono nei dati citati.

---

## Installazione

Serve Python 3.10 o superiore.

```bash
git clone https://github.com/Pbpiombo/rag-bandi-comunali.git
cd rag-bandi-comunali

python -m venv .venv
.\.venv\Scripts\Activate.ps1      # Windows
source .venv/bin/activate         # macOS e Linux

pip install -r requirements.txt
pip install -r requirements-dev.txt   # ruff e pytest, per lo sviluppo
```

Crea un file `.env` nella radice:

```
ANTHROPIC_API_KEY=sk-ant-...
MODEL_NAME=claude-sonnet-5
USA_POSTGRES=1
DATABASE_URL=postgresql://utente:password@host:5432/postgres
```

La chiave API si ottiene su [console.anthropic.com](https://console.anthropic.com).
Conviene impostare un limite di spesa nella sezione Billing, e ricordare che le
chiavi possono avere una scadenza.

`DATABASE_URL` serve solo con `USA_POSTGRES=1`; con `USA_POSTGRES=0` il sistema
usa Chroma in locale e la variabile si può omettere.

Crea le cartelle dei dati non versionate:

```bash
mkdir -p data/raw data/db
```

### Postgres con pgvector

Serve un Postgres con l'estensione `vector` attiva. La via più breve è un
progetto su [Supabase](https://supabase.com), dove l'estensione è già
disponibile.

Nell'editor SQL del pannello:

```sql
create extension if not exists vector;

CREATE TABLE chunk (
    id bigserial PRIMARY KEY,
    testo text NOT NULL,
    metadata jsonb,
    embedding vector(384)
);

alter table chunk enable row level security;

CREATE INDEX ON chunk USING hnsw (embedding vector_cosine_ops);
```

Il `384` è la dimensione dei vettori prodotti dal modello di embedding
configurato in `src/config.py`. Cambiando modello va cambiata anche qui, e
l'indice va ricostruito. Per verificarla:
`len(crea_embeddings().embed_query("test"))`.

`vector_cosine_ops` deve corrispondere all'operatore usato nelle query (`<=>`,
distanza coseno): se non corrispondono l'indice esiste ma non viene mai usato.

Due note sulla connessione:

- su reti senza IPv6 la connessione diretta `db.<progetto>.supabase.co` non si
  risolve. Va usata quella del **connection pooler**, che contiene
  `pooler.supabase.com` e ha l'utente nella forma `postgres.<idprogetto>`;
- sul piano gratuito Supabase mette in pausa i progetti inattivi. Un progetto in
  pausa risponde `tenant/user ... not found`: va ripristinato dal pannello.

## I documenti

`data/raw/` non è versionato. Vanno scaricati a mano i PDF su cui il sistema
deve rispondere. Quelli usati nello sviluppo:

- **Avviso PR FESR Toscana, Sub-Azione 5.2.1.5**: rafforzamento amministrativo
  dei Capofila delle Aree interne (decreto 9550 del 28/04/2026)
- **Linee guida SNAI**: evoluzione del requisito associativo 2021-2027
  (Dipartimento per le politiche di coesione)
- **Contributo CENSIS**: analisi di gruppi omogenei di territori nelle aree
  interne
- **Progetto C3.1 Ludoteche di montagna**: albo pretorio del Comune
- **Avviso mercati rionali**: contributi ai Comuni (decreto 13287 del 10/06/2026)

Requisito: PDF **testuali**, non scansioni. Il sistema lo verifica in fase di
ispezione.

I metadati di ogni documento si dichiarano in
`scripts/ingestione/ingest_tutti.py`.

---

## Uso

### Ingestione dei documenti

```bash
python -m scripts.diagnostica.ispeziona_pdf     # pagine, densità di testo, indici
python -m scripts.ingestione.ingest_tutti       # estrae, pulisce, divide, indicizza
```

L'ingestione scrive su entrambi i vector store. Il primo avvio scarica il
modello di embedding e lo tiene in cache.

Reindicizzando, Chroma sovrascrive i chunk esistenti perché usa identificativi
deterministici; la tabella `chunk` su Postgres no, perché gli id sono generati
da `bigserial`. Prima di una reindicizzazione completa va svuotata:

```sql
TRUNCATE chunk RESTART IDENTITY;
```

### Enti, dati numerici e catalogo dei bandi

```bash
python -m scripts.tutorial.step4_crea_db        # crea le tabelle e carica i CSV
python -m scripts.interrogazione.db_mostra      # ispeziona il contenuto
```

I CSV in `data/processed/` sono la fonte dei dati strutturati, e sono versionati.
Contengono dati pubblici verificati a mano, con la fonte e la data di verifica
per ogni riga:

| File | Contenuto |
|---|---|
| `enti.csv` | i quattro enti, con codice fiscale, codice ISTAT e profilo |
| `popolazione.csv`, `territorio.csv` | dati numerici, ciascuno legato al suo ente |
| `bandi.csv` | il catalogo dei bandi estratti |
| `scansioni.csv` | il registro delle pagine del portale già esaminate |

Ogni dato numerico è legato al suo ente con una chiave esterna verso la tabella
`enti`: una riga con un codice ente inesistente viene rifiutata al caricamento,
invece di finire nel database collegata a nessuno.

Dopo ogni estrazione, bandi e scansioni vengono riversati dal database nei CSV.
Il database è quindi **usa e getta**: quando cambia la struttura di una tabella
si cancella e si ricrea senza perdere nulla.

```powershell
Remove-Item data\db\comune.sqlite
python -m scripts.tutorial.step4_crea_db
```

### Popolare il catalogo dei bandi

```bash
# scopre quali bandi sono comparsi sul portale
python -m scripts.ingestione.scopri_bandi --promettenti

# estrae un singolo bando, con conferma
python -m scripts.ingestione.estrai_bando <url> <identificativo> --salva-testo

# estrae in sequenza i bandi nuovi, con soglia automatica
python -u -m scripts.ingestione.estrai_nuovi --limite 10
```

L'estrazione è **assistita, non automatica**: ogni campo arriva con un livello
di confidenza e la frase del documento da cui è stato ricavato. I campi critici
(scadenza, ammissibilità del beneficiario) richiedono conferma.

### Interrogare

```bash
streamlit run app/app.py
python -m scripts.tutorial.step3_verifica "Quali bandi sono aperti per il Comune?"
```

Nell'app si sceglie l'ente dal menu nella barra laterale. L'interfaccia mostra
la risposta, il pannello di verifica dei dati citati con il contesto di
ciascuno, e le fonti navigabili: cliccando su un frammento se ne legge il testo
originale.

Gli script da riga di comando non hanno un menu, e lavorano sull'ente indicato
da `ENTE_PREDEFINITO` in `src/config.py`.

### Confrontare i due recuperi

```bash
python -m scripts.diagnostica.confronta_recupero
```

Esegue le stesse domande su entrambe le versioni e stampa le risposte affiancate
con l'esito della verifica, per controllare che la scelta del vector store non
cambi i dati citati.

### Test

```bash
python -m pytest
```

Test automatici su verificatore, pulizia e divisione del testo, interrogazioni,
lettura degli enti e descrizione del profilo. Sono gratuiti e istantanei: non
chiamano il modello e non toccano il database vero, ma lavorano su un database
SQLite creato in memoria con lo stesso schema.

I difetti noti e non ancora corretti sono scritti come test `xfail`: falliscono
apposta, e quando il difetto viene corretto pytest segnala che l'etichetta va
tolta.

Le regole di `ruff` sono fissate in `pyproject.toml`, insieme alla versione in
`requirements-dev.txt`, così che i controlli siano gli stessi su ogni macchina.

---

## Struttura

```
src/
├── config.py              configurazione ed ente predefinito
├── vectorstore.py         punto unico di accesso a Chroma
├── retrieval.py           recupero ibrido su Chroma (denso + BM25, fusione RRF)
├── pgstore.py             recupero ibrido su Postgres (pgvector + full-text)
├── ingestion/
│   ├── pdf_ingest.py      lettura dei PDF e scrittura su Chroma
│   └── testo.py           pulizia del testo e divisione in chunk
├── chains/                catena LCEL e router
├── database/
│   ├── schema.py          schema SQLite, caricamento ed esportazione dei CSV
│   ├── enti.py            profilo ed elenco degli enti
│   ├── repertorio.py      catalogo chiuso delle interrogazioni
│   └── interrogazioni_*   query scritte e verificate a mano
├── estrazione/            acquisizione assistita dei bandi dal web
└── verification/          verifica meccanica dei dati citati

scripts/
├── ingestione/            popolamento degli archivi
├── interrogazione/        ricerche dirette sugli archivi
├── diagnostica/           ispezione e confronto
└── tutorial/              passaggi di costruzione, in ordine

tests/
├── conftest.py            database di prova in memoria, condiviso dai test
└── test_*.py              un file per componente

app/                       interfaccia Streamlit
data/
├── raw/                   PDF originali (non versionati)
├── processed/             CSV dei dati strutturati, fonte di verità
└── db/                    SQLite, rigenerabile dai CSV
```

In `src/` la logica riusabile, in `scripts/` i punti da cui viene lanciata.

---

## Scelte tecniche, e perché

**Embedding in locale.** Costo zero per indicizzare, e il testo dei documenti
non esce dalla macchina. Verso l'API viaggiano solo la domanda e i frammenti
recuperati, al momento di generare la risposta.

**Niente text-to-SQL.** Il modello non scrive query: sceglie da un repertorio
chiuso di interrogazioni parametriche, scritte e verificate a mano. Una query
generata liberamente può essere sbagliata in modi difficili da accorgersene, e
produrrebbe un numero plausibile e falso.

**L'ente lo sceglie il programma, non il modello.** Il codice dell'ente arriva
dal menu e viene passato alle interrogazioni come argomento separato dai
parametri decisi dal modello. Anche se il modello provasse a indicarlo, il
valore verrebbe scartato.

**Niente agent.** Il percorso è fisso: il router decide una volta, il codice
esegue, il modello genera. Un agent sceglierebbe le azioni in un ciclo, con un
numero di passi imprevedibile. Qui la tracciabilità viene prima della
flessibilità: si sa sempre cosa è stato consultato e perché.

**Lo stato di un bando si calcola, non si memorizza.** Un campo "aperto/chiuso"
sarebbe vecchio il giorno dopo. Nella scansione iniziale, **84 bandi su 136**
dichiarati aperti dal portale regionale risultavano scaduti leggendone il testo:
alcuni dal 2013.

**I metadati delle fonti non sono affidabili.** Campi strutturati che
contraddicono il testo, stati mai aggiornati, date di rendicontazione presentate
come scadenze di presentazione. L'estrattore è istruito a fidarsi del testo e a
segnalare la discrepanza.

**I CSV sono la fonte, il database è una copia.** Un file SQLite è binario: su
GitHub non si vede cosa cambia tra un commit e l'altro. I CSV sì. Tenere la
verità nei CSV rende ogni modifica ai dati leggibile e reversibile.

**Postgres con pgvector accanto a Chroma.** Chroma è un file su disco: va bene
in locale, non dove il filesystem è effimero. Postgres tiene vettori e dati
numerici nello stesso sistema, la ricerca lessicale diventa nativa invece che
ricostruita in memoria a ogni avvio, e i filtri sui metadati sono SQL invece di
una sintassi a dizionario. Il costo è una dipendenza esterna, ed è il motivo per
cui Chroma resta disponibile.

**Il recupero è un'interfaccia, non un'implementazione.** La catena chiede
`recupero.cerca(domanda, k=k)` e riceve una lista di tuple: non sa quale vector
store ci sia sotto. Sostituirne uno costa una riga.

**Misurare prima di correggere.** Le scelte di struttura sono state guidate da
misure, non da principi. Un esempio: spostare la pulizia del testo in un modulo
separato da Chroma non accorciava i tempi di import; la misura ha mostrato che
il costo era nel pacchetto dello splitter, che carica `transformers` e
`sentence_transformers`. Rimandarne l'import dentro la funzione che lo usa ha
portato il tempo da circa 18 secondi a mezzo secondo.

---

## Limiti

Vale la pena elencarli con la stessa precisione di ciò che il sistema fa.

- **Non garantisce la completezza.** Il verificatore controlla che i dati citati
  esistano nella fonte; non può sapere cosa è stato omesso.
- **Il verificatore controlla quantità, date e riferimenti normativi.** Una
  risposta fatta di soli nomi propri passa senza rilievi, perché non contiene
  nulla di misurabile. Segnala anche riferimenti nominati come "cosa
  servirebbe", che non sono dati.
- **Non sa quali documenti dovrebbe avere.** Risponde solo su ciò che è in
  archivio, e lo dichiara quando non basta.
- **Il recupero può mancare il frammento decisivo.** Una domanda
  sull'ammissibilità può non recuperare il paragrafo dei beneficiari, anche se è
  in archivio; il sistema allora risponde con cautela invece di concludere.
- **Una domanda riguarda un ente alla volta.** Non esiste ancora una vista su
  tutta l'area, del tipo "quali bandi può usare ciascuno dei nostri comuni".
- **I bandi distinguono solo se ammettono i comuni.** Non è registrato se
  ammettono le Unioni: per l'Unione l'ammissibilità va verificata sul testo.
- **Dati numerici solo per Abetone Cutigliano.** Per gli altri enti il sistema
  dichiara che il dato non è disponibile.
- **L'estrazione è assistita.** I campi critici richiedono lettura umana delle
  prove: è la condizione a cui i valori risultano affidabili.
- **I dati si aggiornano a mano.** Ogni riga porta la data in cui è stata
  verificata.
- **Le date di riferimento seguono l'orologio del server**, non il fuso
  italiano: a ridosso della mezzanotte lo stato di una scadenza può risultare
  sfasato.
- **Le scadenze post-aggiudicazione non sono gestite.** Rendicontazioni, SAL,
  relazioni periodiche: il sistema le legge nei documenti ma non le traccia.
- **La ricerca lessicale su Postgres unisce i termini con OR.** Trova sempre
  qualcosa, ma può promuovere un frammento che ripete un termine comune senza
  essere pertinente. BM25 pesa i termini per rarità e su questo si comporta
  meglio.
- **Nessuna memoria conversazionale.** Ogni domanda è indipendente: un seguito
  come "e quanto possono chiedere?" non eredita il soggetto da quella prima.

## Dove va

Trovare i bandi non è il collo di bottiglia degli enti piccoli: lo è avere chi segue la redazione della domanda. L’obiettivo è un sistema che, scelto un bando, guidi la costruzione della domanda passo per passo: quali documenti servono, quali si possono compilare in autonomia, quando serve un tecnico e di che tipo. Intorno a questo, un aggiornamento periodico delle fonti con avviso via mail quando compare un bando pertinente, e un calendario delle scadenze con promemoria sugli step preliminari.

## Stato

Prototipo funzionante, sviluppato come progetto di apprendimento e portfolio.
Non è un prodotto: non è in produzione, non ha autenticazione, e i dati vanno
verificati prima di essere usati in un atto amministrativo.

## Licenza

MIT.
