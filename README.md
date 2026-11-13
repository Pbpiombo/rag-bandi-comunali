# RAG Bandi Comunali

Assistente per la programmazione territoriale dei piccoli comuni montani.
Trova i bandi a cui un ente può partecipare, spiega cosa serve per presentare
domanda, e **cita la fonte di ogni dato che riporta**.

Il progetto nasce da un interesse personale e da contatti con chi lavora sui bandi nei comuni montani. È un progetto di portfolio, ma la struttura è pensata per diventare uno strumento reale: costruita per un’Unione di comuni, si può estendere ad altri enti e ad altre fonti di bandi.


**[Prova la demo online](https://rag-bandi-comunali-yxhfmuxc5k4cg96rnxeeka.streamlit.app/)**

Caso di studio: l'**Unione di Comuni Montani Appennino Pistoiese** e i suoi
tre comuni, Abetone Cutigliano, Sambuca Pistoiese e San Marcello Piteglio, tutti
nell'area interna Garfagnana - Lunigiana - Media Valle del Serchio - Appennino
Pistoiese. L'utente sceglie da un menu l'ente per cui sta lavorando, e il
sistema risponde per quell'ente.

## In breve

- **Cosa fa**: risponde sui bandi per l'ente scelto (aperti, in scadenza, per tipo di beneficiario, dettaglio di un bando) e sui documenti in archivio, citando la fonte di ogni dato.
- **Fonti**: 112 bandi da 6 fonti (Regione Toscana, Incentivi Italia, GAL MontagnAppennino, Sviluppo Toscana, Istituto per il Credito Sportivo e Culturale, Ministero delle Infrastrutture), dati ISTAT dei tre comuni, 5 avvisi e studi in PDF.
- **Controllo dei dati**: un verificatore meccanico cerca ogni dato citato nella fonte dichiarata; l'estrazione dei bandi è misurata con verifiche a mano sulle pagine ufficiali.
- **Misure**: verifica a mano di 23 bandi, scadenza corretta in 21; seconda verifica sui 10 bandi riestratti: scadenza corretta in 10, beneficiari in 7 e parzialmente in 3. Due prove con il modello: 138 dati segnati come verificati, nessun falso positivo. Recupero: 13 frammenti attesi su 16 tra i primi 10, 5 su 5 nelle domande di controllo.
- **Limiti principali**: il verificatore controlla che un dato esista nella fonte, non che sia completo o attribuito alla cosa giusta; le fonti non coprono tutto (prima misura su un elenco esterno, il 13 novembre prima dei recuperi: 8 bandi su 31); gli aggiornamenti si lanciano a mano.

---

## Il problema

Le opportunità di finanziamento per un comune sono sparse in decine di
documenti: avvisi regionali, linee guida nazionali, delibere, studi di settore.
Chi segue i bandi per un ente o per un'impresa ha due problemi: trovare l'informazione, e
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
   dichiarata, come valore intero: "8%" non si conferma con "80%". O c'è, o
   non c'è.

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

La popolazione dell'ente non sta nel profilo, che non è una fonte
verificabile: a ogni domanda il programma aggiunge ai dati un blocco con
l'ultima popolazione ISTAT del comune, con anno e fonte, che il modello cita
come gli altri dati e il verificatore controlla. Serve a confrontare l'ente
con le soglie dei bandi (es. i mutui di Missione Comune, 2 milioni fino a
5.000 abitanti). Per l'Unione il blocco non c'è, e il modello dice che il
dato non è disponibile.

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
coincidono nei dati citati. L'ordine dei frammenti invece può cambiare: su
alcune domande Chroma mette il frammento decisivo più in alto di Postgres
(il costo giornaliero di un avviso è 1° su Chroma e 4° su Postgres), per la
diversa ricerca lessicale.

### Il catalogo dei bandi

I bandi stanno nel database, uno per riga, con chi può presentare domanda,
gli interventi ammessi, le date, gli importi e la frase della pagina da cui
viene ogni dato. Si acquisiscono da queste fonti:

| Fonte | Come si legge | Bandi |
|---|---|---|
| Portale bandi Regione Toscana | pagine web, due elenchi | 54 |
| Incentivi Italia | file open data del catalogo nazionale | 54 |
| GAL MontagnAppennino | pagine web | 2 |
| Sviluppo Toscana | pagine indicate a mano | 2 |
| Istituto per il Credito Sportivo e Culturale | pagine indicate a mano | 2 |
| Ministero delle Infrastrutture e dei Trasporti | pagine indicate a mano | 1 |

"Pagine indicate a mano" vuol dire che l'elenco della fonte non si scansiona
in automatico: le pagine dei bandi si acquisiscono una per una, per
indirizzo. In archivio ci sono anche 3 pagine che non sono bandi (due
graduatorie e una manifestazione di interesse), tenute per dire perché non
lo sono. Le schede di ANCI Toscana servono a
scoprire i bandi, ma non sono una fonte: i dati si prendono sempre dalla
pagina ufficiale dell'ente. I social non si leggono, e `robots.txt` si
rispetta sempre.

Il router sceglie una di queste interrogazioni:

- **bandi aperti per l'ente**: quelli a cui l'ente scelto può presentare
  domanda, con gli sportelli in un gruppo a parte e l'invito a verificare
  le risorse;
- **bandi in scadenza** entro un numero di giorni: anche gli sportelli con
  una data di chiusura nella finestra, segnalati come "a sportello, chiude
  il …, salvo esaurimento delle risorse";
- **bandi per tipo di beneficiario**: imprese agricole, turistiche,
  artigiane, terzo settore, cittadini e gli altri tipi della lista chiusa;
- **bandi per tema**: se il tema in archivio non corrisponde, si cercano le
  parole nei titoli, e lo si dice;
- **dettaglio di un bando**, cercato per titolo. Fino a 3 bandi che
  corrispondono, il dettaglio di ciascuno; oltre, un elenco breve senza
  sceglierne uno. Se nessun titolo corrisponde, si cercano le parole nei
  beneficiari e negli interventi ("impianti di risalita" trova i bandi
  neve). Poi la corrispondenza parziale: se a un solo titolo manca una
  sola delle parole cercate, se ne dà il dettaglio dicendo quale parola
  manca ("fondo strade MIT piccoli comuni" trova il fondo per le strade
  dei piccoli Comuni, che non contiene "MIT"). Altrimenti si propongono i
  5 titoli più simili.

**Lo stato di un bando si calcola a ogni domanda** dalla scadenza, anche nei
frammenti dei documenti. I bandi scaduti non si cancellano: servono a
riconoscere proroghe e bandi ricorrenti. Gli elenchi per tema mostrano, in
un blocco separato, quelli scaduti da meno di 12 mesi; il dettaglio di un
bando scaduto comincia con "scaduto il …, non più aperto".

**Da approfondire.** Gli elenchi contengono solo i bandi con i dati
essenziali. Sotto la risposta, una sezione scritta dall'app e non dal
modello elenca i bandi pertinenti a cui manca un dato (scadenza non
indicata, beneficiari non indicati sulla pagina, sportello probabilmente
esaurito): solo i recenti, al più 10, con i contatti d'ufficio della
pagina. I contatti li legge il codice (`src/estrazione/contatti.py`), mai
nomi o email di persone: nel dubbio resta il collegamento alla pagina. Oggi
li hanno 43 bandi su 112, e compaiono anche nel dettaglio.

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
  Per evitarlo, il workflow `.github/workflows/tieni_sveglio.yml` lancia ogni
  3 giorni `scripts/manutenzione/tieni_sveglio.py`, che fa una sola lettura
  in sola lettura. Serve il secret `DATABASE_URL` del repository (Settings →
  Secrets and variables → Actions) con la stringa del pooler: i runner di
  GitHub non hanno IPv6. Lo script si lancia anche a mano
  (`python -m scripts.manutenzione.tieni_sveglio`). GitHub sospende i workflow
  programmati dopo 60 giorni senza commit: in quel caso va riattivato dalla
  scheda Actions.

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
| `fonti.csv` | i siti da cui si acquisiscono i bandi, con il tipo (pagine web o file scaricato) e le regole per leggerli |
| `elenchi.csv` | le pagine elenco di ogni fonte da cui si scoprono i bandi, anche più d'una per fonte |
| `bandi.csv` | il catalogo dei bandi estratti |
| `beneficiari_bando.csv` | chi può presentare domanda per ogni bando: tipo, soggetto, condizioni, frase della pagina |
| `interventi_bando.csv` | interventi e spese ammissibili, ciascuno con la sua frase |
| `scadenze_bando.csv` | le date dei bandi a finestre o con più scadenze |
| `scansioni.csv` | il registro delle pagine delle fonti già esaminate |

Popolazione e superficie dei tre comuni si caricano da ISTAT con uno script,
che salva i file scaricati in `data/raw/istat/` e scrive nella fonte di ogni
riga l'indirizzo e la data:

```bash
python -m scripts.manutenzione.carica_istat --scarica   # scarica i file ISTAT
python -m scripts.manutenzione.carica_istat --prova     # mostra le differenze, non scrive
python -m scripts.manutenzione.carica_istat --scrivi    # scrive ed esporta i CSV
```

La popolazione al 1° gennaio viene dal bilancio demografico mensile di
demo.istat.it, la superficie dal file "Altimetria Comuni al 31 dicembre 2021".
`--scrivi` si rifiuta se cambierebbe la popolazione di un anno definitivo già
in archivio: possono cambiare solo gli anni provvisori.

Ogni dato numerico è legato al suo ente con una chiave esterna verso la tabella
`enti`: una riga con un codice ente inesistente viene rifiutata al caricamento,
invece di finire nel database collegata a nessuno.

Dopo ogni estrazione, le tabelle dei bandi (bandi, beneficiari, interventi,
scadenze) e le scansioni vengono riversate dal database nei CSV.
Il database è quindi **usa e getta**: quando cambia la struttura di una tabella
si cancella e si ricrea senza perdere nulla.

```powershell
Remove-Item data\db\comune.sqlite
python -m scripts.tutorial.step4_crea_db
```

### Popolare il catalogo dei bandi

Le fonti dei bandi sono dati, non codice. `fonti.csv` dice per ogni sito il
dominio, la forma dei collegamenti alle pagine dei bandi, le voci di servizio
da ignorare, il nome del campo con la data di scadenza e se usare il filtro
sull'anno nel nome della pagina; `elenchi.csv` dice da quali pagine partire.
Aggiungere una fonte o un elenco vuol dire aggiungere una riga, dopo averne
controllato il `robots.txt`. Le fonti di tipo "file" (un file scaricato e
letto dal codice) non hanno elenchi da scansionare.

```bash
# scopre quali bandi sono comparsi negli elenchi delle fonti
python -m scripts.ingestione.scopri_bandi --promettenti

# estrae un singolo bando, con conferma
python -m scripts.ingestione.estrai_bando <url> <identificativo> --salva-testo

# estrae in sequenza i bandi nuovi e li salva da solo
python -u -m scripts.ingestione.estrai_nuovi --prova
python -u -m scripts.ingestione.estrai_nuovi --limite 10

# Incentivi Italia: il file open data, scaricato a mano fuori dal repository
python -u -m scripts.ingestione.importa_incentivi --file PERCORSO --prova
python -u -m scripts.ingestione.estrai_incentivi --file PERCORSO --prova

# contatti d'ufficio dei bandi già in archivio, senza modello
python -u -m scripts.manutenzione.aggiungi_contatti --prova
```

Ogni campo estratto arriva con un livello di confidenza e la frase della
pagina da cui è stato ricavato, e il codice controlla che la frase ci sia
davvero. Le due vie di estrazione si comportano in modo diverso:

- `estrai_bando` è **assistita**: mostra i campi e chiede conferma prima di
  salvare;
- `estrai_nuovi` ed `estrai_incentivi` sono **automatiche**: salvano senza
  conferma, scartano solo le pagine che non sono bandi o sono scadute da più
  di un anno, e mettono da parte quelle con la scadenza incerta.
  L'affidabilità dell'estrazione automatica si misura a campione, con le
  verifiche a mano descritte in fondo.

`importa_incentivi` non chiama il modello: legge il file e salva le misure
che non riguardano gli enti pubblici; quelle aperte agli enti pubblici le
legge `estrai_incentivi` dalla pagina ufficiale, come gli altri bandi.

Un bando con dati essenziali mancanti non si scarta e non si nasconde. Se la
pagina non dice chi può presentare domanda (es. "nell'avviso sono indicati i
requisiti"), il bando si salva con i beneficiari vuoti e la frase che rimanda
all'avviso, e compare nella sezione **Da approfondire** dell'app (vedi "Il
catalogo dei bandi").

Ogni risposta del modello si conserva tale e quale, con il testo che gli è
stato inviato, in `dati-grezzi/estrazioni/` accanto al progetto, fuori dal
repository: un file `AAAA-MM-GG_<id del bando>.json` per estrazione, anche
quando l'estrazione fallisce. `src/estrazione/grezzi.py` (`rileggi`) permette
di rifare la validazione dopo una modifica alle regole senza ripagare il
modello.

### Interrogare

```bash
streamlit run app/app.py
python -m scripts.tutorial.step3_verifica "Quali bandi sono aperti per il Comune?"
```

Nell'app si sceglie l'ente dal menu nella barra laterale, che riassume anche
cosa c'è in archivio per quell'ente. Sopra la casella delle domande ci
sono sette domande d'esempio pensate per il consulente pilota: bandi aperti e
in scadenza per il Comune, un bando nominato, bandi per le imprese turistiche
e agricole, un dato di un avviso, la popolazione. L'interfaccia mostra la
risposta, la sezione "Da approfondire", il pannello di verifica dei dati
citati con il contesto di ciascuno, e le fonti navigabili: cliccando su un
frammento se ne legge il testo originale.

Gli script da riga di comando non hanno un menu, e lavorano sull'ente indicato
da `ENTE_PREDEFINITO` in `src/config.py`.

### Confrontare i due recuperi

```bash
python -m scripts.diagnostica.confronta_recupero
```

Esegue le stesse domande su entrambe le versioni e stampa le risposte affiancate
con l'esito della verifica, per controllare che la scelta del vector store non
cambi i dati citati.

```bash
python -m scripts.diagnostica.prova_recupero
```

L'insieme di prova del recupero, senza modello: 20 domande, ciascuna con il
documento e la frase che devono comparire tra i primi 10 frammenti, misurate
su Postgres e su Chroma. Va rilanciato a ogni modifica del recupero o
dell'archivio.

### Test

```bash
python -m pytest
```

Test automatici su verificatore, pulizia e divisione del testo, recupero,
interrogazioni, profilo degli enti, router, estrattore e regole di
salvataggio, fonti, Incentivi Italia, contatti, dati ISTAT. Sono gratuiti e
istantanei: non chiamano il modello e non toccano il database vero, ma
lavorano su un database SQLite creato in memoria con lo stesso schema. Il
codice che legge pagine web si prova su pagine salvate in `tests/pagine/`,
non sui siti.

Un test di equivalenza confronta il testo delle interrogazioni sui bandi,
su un archivio di prova fisso, con un riferimento salvato (`tests/dati/interrogazioni_comuni_dopo.json`):
ogni cambiamento del testo che arriva al modello si vede, e va approvato.

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
├── normalizzazione.py     numeri, date e riferimenti ridotti a valori confrontabili
├── vectorstore.py         punto unico di accesso a Chroma
├── retrieval.py           recupero ibrido su Chroma (denso + BM25, fusione RRF)
├── pgstore.py             recupero ibrido su Postgres (pgvector + full-text)
├── recupero_documenti.py  ricerca ristretta ai documenti nominati nella domanda
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
├── manutenzione/          correzioni, caricamenti ISTAT, contatti, Supabase sveglio
├── diagnostica/           ispezione, confronto e prova del recupero
└── tutorial/              passaggi di costruzione, in ordine

tests/
├── conftest.py            database di prova in memoria, condiviso dai test
├── dati/, pagine/         riferimenti e pagine web salvate
└── test_*.py              un file per componente

app/                       interfaccia Streamlit
docs/                      roadmap, piani, revisioni, verifiche a mano
.github/workflows/         lettura periodica su Supabase
data/
├── raw/                   PDF e file ISTAT originali (non versionati)
├── processed/             CSV dei dati strutturati, fonte di verità
└── db/                    SQLite, rigenerabile dai CSV
```

In `src/` la logica riusabile, in `scripts/` i punti da cui viene lanciata.
Fuori dal repository, in `dati-grezzi/` accanto al progetto, stanno le
risposte grezze del modello, gli esiti delle prove e le copie di sicurezza.

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
- **Il verificatore controlla i valori, non gli abbinamenti.** Un dato è
  verificato se il suo valore compare nella fonte citata, non se è
  attribuito alla cosa giusta: un numero di abitanti riferito all'anno
  sbagliato, o l'importo di un intervento attribuito a un altro, passano
  se entrambi i valori sono nella fonte.
- **Non sa quali documenti dovrebbe avere.** Risponde solo su ciò che è in
  archivio, e lo dichiara quando non basta.
- **Il recupero può mancare il frammento decisivo.** Una domanda
  sull'ammissibilità può non recuperare il paragrafo dei beneficiari, anche se è
  in archivio; il sistema allora risponde con cautela invece di concludere.
- **Il recupero ha casi non risolti.** Quando una domanda nomina un avviso
  per titolo ("nel bando X, quanto…") si cerca anche dentro quell'avviso.
  Restano due casi: una domanda che usa parole diverse dal testo
  ("contributi" dove il bando dice "contributo concedibile") e una che
  chiede di due avvisi insieme. Un frammento è al limite: il termine di
  presentazione di un avviso è 8° su Postgres e 10° su Chroma.
- **Le fonti non coprono tutti i bandi.** Sei fonti; mancano il Bollettino
  ufficiale della Regione e le sezioni "Avvisi" dei siti dei comuni. Nella
  prima misura su un elenco esterno (le schede di ANCI Toscana, 13 novembre
  2026) erano in archivio 8 bandi pertinenti su 31. I 3 bandi aperti
  mancanti che riguardavano i comuni o il territorio, più un quarto trovato
  su Sviluppo Toscana, sono stati recuperati lo stesso giorno; la misura
  non è stata ripetuta.
- **La ricerca di un bando per nome confronta parole, non significati.**
  "Rifugi" trova un bando che nomina le case rifugio per le donne vittime di
  violenza; "piste da sci" non trova niente, anche se i bandi neve
  riguardano le stazioni sciistiche.
- **Una domanda riguarda un ente alla volta.** Non esiste ancora una vista su
  tutta l'area, del tipo "quali bandi può usare ciascuno dei nostri comuni".
- **Nessun dato numerico per l'Unione.** Popolazione e superficie ci sono
  per i tre comuni; per l'Unione il sistema dichiara che il dato non è
  disponibile, invece di sommare quelli dei comuni.
- **L'estrazione automatica salva senza lettura umana.** La frase di ogni
  dato si controlla sulla pagina, ma l'affidabilità del contenuto è misurata
  a campione, non garantita bando per bando.
- **Gli aggiornamenti si lanciano a mano.** Scansioni delle fonti, caricamento
  dei dati ISTAT e dei contatti partono da uno script: non c'è ancora un
  aggiornamento periodico. Ogni riga porta la data in cui è stata estratta o
  verificata.
- **Le date di riferimento seguono l'orologio del server**, non il fuso
  italiano: a ridosso della mezzanotte lo stato di una scadenza può risultare
  sfasato.
- **Le scadenze dopo la domanda si tracciano solo in parte.** Le fasi
  successive scritte nella pagina del bando (es. il parere del CONI entro
  una data) si mostrano come informazione; rendicontazioni, SAL e relazioni
  periodiche il sistema le legge nei documenti ma non le traccia.
- **La ricerca lessicale su Postgres unisce i termini con OR.** Trova sempre
  qualcosa, ma può promuovere un frammento che ripete un termine comune senza
  essere pertinente. BM25 pesa i termini per rarità e su questo si comporta
  meglio.
- **Nessuna memoria conversazionale.** Ogni domanda è indipendente: un seguito
  come "e quanto possono chiedere?" non eredita il soggetto da quella prima.

## Misure

**Estrazione dei bandi.** Verifica dell'11 novembre 2026 su 23 bandi (20
scelti a caso e 3 aperti per enti pubblici), confrontando i dati estratti
con la pagina ufficiale di ciascun bando; le righe con errori sono state
ricontrollate dall'autore sulle pagine e sui testi dei bandi. Scadenza
corretta in 21, sportello e atto in 23, beneficiari corretti in 17,
parzialmente in 3, errati in 3. Gli errori si concentrano sui bandi a
più scadenze e sulla classificazione dei beneficiari privati e dei
soggetti pubblici generici (`docs/verifica-manuale-2026-11-11.csv`).

Seconda verifica del 12 novembre 2026 sui 10 bandi riestratti dopo le
correzioni: scadenza corretta in 10, sportello in 8, atto in 8 (2
parziali), beneficiari corretti in 7 e parzialmente in 3, nessuno
errato (`docs/verifica-manuale-2026-11-12.csv`).

**Verificatore, con il modello.** Prova del 12 novembre 2026 su 9
domande: 100 dati segnati come verificati, nessun falso positivo; 2 falsi
negativi, entrambi per una data presa dall'intestazione del blocco di
dati, poi corretti. Seconda prova dello stesso giorno, dall'app, su 3
domande scelte per le correzioni del recupero e dello stato dei bandi: 38
dati verificati, nessun errore (`docs/prova-verificatore.md`).

**Recupero dei documenti.** Prova su 20 domande, ciascuna in 4 forme: tra
i primi 10 ci sono 13 frammenti attesi su 16 nelle 15 domande di prova e 5
su 5 nelle 5 di controllo, su Postgres e su Chroma. Le domande di
controllo sono state scritte dopo aver deciso tutto sulle altre 15.

## Dove va

Trovare i bandi giusti, con le date vere, è il primo passo; il secondo è seguire la domanda. L’obiettivo è un sistema che, scelto un bando, guidi la costruzione della domanda passo per passo: quali documenti servono, quali si possono compilare in autonomia, quando serve un tecnico e di che tipo. Intorno a questo, un aggiornamento periodico delle fonti con avviso via mail quando compare un bando pertinente, e un calendario delle scadenze con promemoria sugli step preliminari.

## Stato

Prototipo funzionante, sviluppato come progetto di apprendimento e portfolio.
Non è un prodotto: non è in produzione, non ha autenticazione, e i dati vanno
verificati prima di essere usati in un atto amministrativo.

## Licenza

MIT.
