# Piano della fermata 2 del 19e: filtro per bando

Scritto il 28/11/2026, come piano: nessun codice dell'app, nessuna
chiamata al modello di linguaggio, nessuna rete, nessun Postgres. Fermata 2
del rilascio 2 di `docs/piano-19e.md` ("Decisioni del 25/11/2026",
correzione a, punto 4; tappa 2; sezione 5, punto 2).

Fonti lette: `docs/piano-19e.md` (tappa 2, "Decisioni del 25/11/2026",
sezione 5 punto 2), `docs/piano-fermata-1.md`, `docs/coda.md` ("Fermata 1
del 19e", "Ricerca per nome e parole comuni"), `CLAUDE.md`, e il codice di
`src/motore.py`, `src/chains/rag.py`, `src/recupero_documenti.py`,
`src/database/interrogazioni_bandi.py` (più `src/database/repertorio.py`,
`src/database/modelli.py`, `src/chains/router.py` per il percorso
dell'esito).

**Decisioni già prese** (25/11/2026 e consegna del 28/11/2026): filtro solo
con un bando trovato per nome; mai su un candidato non scelto dall'utente;
due o tre bandi trovati, nessun filtro fino alla tappa 7; nessun bando, o
bando senza frammenti, ricerca in tutto come oggi. **Un filtro sul bando
sbagliato toglie tutti i frammenti giusti: è l'errore grave di questa
fermata.**

Le misure delle sezioni 3 e 4 sono state fatte oggi, senza modello, con
`..\dati-grezzi\prova\19e\fermata-2\prova_zero_filtro.py` (SQLite in sola
lettura, frammenti per bando da `..\dati-grezzi\prova\19d\v0\frammenti.json`,
uguale al Chroma vero; Chroma non aperto). Uscite accanto:
`prova_zero_filtro_uscita.txt` e `prova_zero_filtro.json`.

## 1. Dove passa l'id del bando

Oggi l'esito di `dettaglio_bando` non porta l'id: `prepara` riceve dagli
`esiti` coppie (nome, `Risultato`), e `Risultato` ha testo, fonti,
`trovato`, voci e bandi da approfondire. Il passo che ha trovato il bando
non esce da `dettaglio_bando`.

Percorso proposto, dall'esito al motore:

1. **`src/database/interrogazioni_bandi.py`**: `trova_bandi` diventa un
   involucro di una funzione nuova, `trova_bandi_con_passo`, che restituisce
   anche il passo ("id", "titolo_intero", "titolo_parole"); `trova_bandi`
   dà gli stessi bandi di oggi, quindi i suoi chiamanti non cambiano.
   `dettaglio_bando` mette l'id in un campo nuovo del `Risultato` solo
   quando vale la condizione della sezione 3 (regola stretta). Il testo,
   `trovato`, le fonti e le voci restano identici a oggi: il modello non
   vede niente di nuovo.
2. **`src/database/modelli.py`**: `Risultato` ha un campo in più,
   `bando_per_nome: str | None = None`. `formatta_dati` usa solo il testo,
   quindi il campo non arriva al modello; `esegui_su` lo passa com'è.
3. **`src/chains/rag.py`**:
   - una funzione nuova `bando_del_filtro(esiti, con_frammenti)`: tra gli
     esiti di `dettaglio_bando`, l'id da filtrare se tutte le chiamate
     insieme danno un solo bando trovato, con `bando_per_nome` e con
     frammenti; altrimenti `None`. Pura, provata senza database;
   - una funzione nuova `recupera_nel_bando(recupero, riordino, contesti,
     domanda, id_bando, titolo, k)`, accanto a `recupera_riordinati`, che
     riproduce la condizione B della misura: domanda normalizzata, domanda
     ripulita con le parole del titolo del bando (`ripulisci_domanda` e
     `parole_titolo` di `src/recupero_documenti.py`, le stesse della
     misura), `cerca_nel_bando` del motore con `CANDIDATI_RIORDINO`
     candidati, riordino sulla domanda ripulita, primi k. Il titolo viene
     da SQLite (sezione 6, punto 4);
   - in `prepara`: dopo gli esiti, se `FILTRO_PER_BANDO` e `riordino` ci
     sono e `bando_del_filtro` dà un id, `recupera_nel_bando`; altrimenti
     il percorso di oggi (`recupera_riordinati` o `recupera`).
     `con_vicini` resta dopo, com'è. Nell'esito le origini restano quelle
     di `cerca_nel_bando` con davanti "bando: " (come fa `_segna` con
     "documento"), e l'esito ha una voce nuova `filtro_bando` (id o
     `None`), per i registri e le misure.
4. **`src/motore.py`**: `Motore.bandi_con_frammenti`, l'insieme degli
   `id_bando` dei suoi frammenti (decisione 2 della sezione 9: solo quelli
   degli avvisi). `cerca_nel_bando` non cambia: è quella misurata.
5. **`src/config.py`**: `FILTRO_PER_BANDO = False`.

`recupera`, `recupera_riordinati`, `avvolgi` e lo script di misura non
cambiano.

**Con `ORDINE_C_LR` spento** il filtro non ha effetto: `cerca_nel_bando`
esiste solo nel motore, e il numero da raggiungere (77 su 98) è c-LR in B.
Un filtro sul recupero di oggi (`RecuperoIbrido` o `RecuperoPostgres`)
sarebbe un percorso non misurato. Quindi `FILTRO_PER_BANDO` acceso conta
solo con `ORDINE_C_LR` acceso e un motore; altrimenti l'app lo scrive nel
registro all'avvio, come l'avviso di `ORDINE_C_LR` con Postgres. Sulla
demo (Postgres) non ha effetto fino alla fermata 5.

## 2. Cosa vuol dire oggi "trovato per nome"

`dettaglio_bando` dà `trovato=True` in più casi di quelli che la parola
"per nome" fa pensare:

| passo | cosa confronta | `trovato=True` quando | affidabilità per un filtro |
|---|---|---|---|
| identificativo esatto | `bandi.id` | sempre, un bando | massima: il router ha copiato l'id |
| testo intero nel titolo | il testo cercato come parole intere nel titolo | da 1 a 3 bandi | alta, con un limite: una sola parola comune ("dati", "strada") basta, se compare in un solo titolo |
| parole simili nel titolo | ogni parola cercata con una simile nel titolo (stesse 5 lettere iniziali, lunghezze entro 2) | da 1 a 3 bandi | buona; è il passo dei limiti noti sulle lettere ("prestito" e "prestatori") |
| testo dei beneficiari e degli interventi (`trova_nel_testo`) | le parole cercate fuori dal titolo | da 1 a 3 bandi | bassa: non è un nome. È qui che "caldaia" trova "calda" e "mutuo" trova il bando parcheggi |
| corrispondenza parziale | il solo titolo a cui manca una parola cercata | un bando | media: la parola mancante può essere proprio quella che distingue due bandi |
| ripiego sul testo unito, titoli simili, nessuno | — | mai (`trovato=False`) | — |

Due cose in più, dal codice:
- con più di 3 bandi `trovato=False` (l'elenco breve), con 2 o 3
  `trovato=True` (dettaglio di ciascuno): il "trovato" da solo non dice
  quanti;
- se i bandi trovati sono tutti scaduti, la tappa 6a aggiunge in fondo i
  candidati non scaduti, e `trovato` resta quello di prima.

I limiti noti diventano filtri sbagliati? Oggi no, misurato (sezione 3):
"rifugio" trova le "Case rifugio" nel testo dei beneficiari, un bando senza
frammenti; "prestito" trova due bandi ("prestatori"); "caldaia" trova
l'avviso del 2021, senza frammenti; "sportivo" trova quattro titoli e
"sportello" è solo tra i titoli simili. Ma per la ragione sbagliata: i
bandi colpiti non hanno frammenti. Con più avvisi caricati lo stesso
confronto darebbe filtri sbagliati.

## 3. Misura b: quante volte scatterebbe il filtro

**Due regole, scritte prima di guardare gli esiti** (sono nella docstring
dello script, scritta prima della prima esecuzione):

- **regola larga**, quella delle decisioni prese alla lettera:
  `trovato=True` con un solo bando, e il bando ha frammenti;
- **regola stretta**, la proposta: in più il bando viene da uno dei tre
  passi del titolo (identificativo, testo intero, parole simili), non dal
  testo dei beneficiari e degli interventi né dalla corrispondenza
  parziale; è di natura "bando"; e non c'è il blocco dei candidati non
  scaduti della tappa 6a.

Più chiamate di `dettaglio_bando` nella stessa decisione: filtro solo se
tutte insieme danno un solo bando.

Bandi con frammenti oggi: 13 (i 12 degli avvisi più `mercati-rionali-2026`,
che ha `id_bando` ma non `sha256`).

| insieme | passi | un solo bando con `trovato=True` | filtro, regola larga | filtro, regola stretta | sbagliati |
|---|---|---|---|---|---|
| 116 titoli come testo cercato | 116 testo intero nel titolo | 116 | 13 | 13 | 0: i 13 sono il bando del titolo |
| 36 parole comuni | 23 nessuno, 8 testo, 3 testo intero, 2 parole simili | 9 | 4 | 2 | 1 con la larga ("mutuo"), 0 con la stretta |
| 12 parametri salvati | 7 testo intero, 4 parole simili, 1 nessuno | 7 | 7 | 7 | 0 |
| 40 parole della strada C | 26 nessuno, 9 testo, 3 testo intero, 2 parole simili | 10 | 4 | 2 | come le 36 |

Casi in cui il filtro scatta fuori dai titoli:
- "strada" e "strade" → Fondo investimenti stradali nei piccoli Comuni
  (parole simili): stretta e larga. Pertinente; dubbio solo se la domanda
  parla d'altro e il router passa la parola come nome.
- "apicoltura" → bando per le aziende apistiche, dal testo degli
  interventi: solo larga. Bando pertinente, ma non trovato per nome.
- "mutuo" → Bando parcheggi 2026, dal testo dei beneficiari: solo larga.
  **Sbagliato**: chi scrive "mutuo" non chiede del bando parcheggi. È il
  caso che fa preferire la regola stretta.
- Tra i 12 parametri salvati: "parcheggi" (3 volte) e "fondo strade" (4
  volte), sul bando giusto con tutte e due le regole.

I 13 titoli dei bandi con frammenti filtrano tutti sul proprio bando con la
regola stretta: nessuno resta fuori.

Osservazione fatta dopo aver visto gli esiti, quindi non una regola: una
sola parola comune come parametro ("dati", "strada") passa dal testo
intero o dalle parole simili e filtra. Si guarda nella misura con il
modello (sezione 5): un filtro sbagliato lì non chiude la fermata.

## 4. Misura c: prova zero sulle decisioni del router salvate

Le "226 risposte" sono 182 dei lotti 1-3, 40 del 19e (V0 e V1) e 4 della
sospensione. Solo le 182 dei lotti hanno la decisione del router: V0 e V1
sono state registrate con il router fisso (nessuna interrogazione), la
sospensione non ha registrato la decisione. Le 20 domande vere del 25/11
sono in un documento con il nome dell'interrogazione ma non il parametro.

| insieme | con la decisione | con `dettaglio_bando` | filtrate, larga | filtrate, stretta | con frammenti |
|---|---|---|---|---|---|
| lotti 1-3 | 182 | 12 | 7 | 7 | 7 |
| 19e V0 e V1 | 0 (router fisso) | — | — | — | — |
| sospensione | 0 | — | — | — | — |
| 20 domande vere del 25/11 | parametro non salvato | 10 | non misurabile | non misurabile | — |

Le 7 filtrate, lette:
- "Il bando parcheggi chiede un progetto già approvato?" (C09, tre
  registrazioni) → Bando parcheggi 2026 (17 frammenti). Giusto.
- "Quanto si può chiedere con il fondo strade del Ministero?" (C10,
  quattro registrazioni) → Fondo investimenti stradali nei piccoli Comuni
  (5 frammenti). Giusto.
Le 5 non filtrate: "bando neve" (4 registrazioni, due bandi, nessuno con
frammenti) e C12 ("impianti sportivi mutuo agevolato", nessun bando).

**Casi dubbi**: nessuno tra i 7. Due cose da sapere:
- il fondo strade ha 5 frammenti: con il filtro il modello ne riceve al più
  5, non 10 (come nella condizione B della misura);
- delle 20 domande vere, 10 hanno scelto `dettaglio_bando`; dai bandi
  citati nelle risposte, in 7 il bando trovato ha frammenti (Cultura e
  Sport Missione Comune, Pmi 50 mila, Punti Digitale Facile due volte,
  educazione musicale, rievocazione 2027); "cloud" porta a un bando senza
  frammenti, il pulmino a nessun bando. Senza il parametro non si sa se il
  filtro sarebbe scattato: si misura con il router (sezione 5,
  decisione 6).

La prova zero su dati salvati è sottile: 7 casi, due domande. La prova vera
è la misura con il router.

## 5. Misura con il modello, solo router

**Script da scrivere** (fuori dal repository):
`..\dati-grezzi\prova\19e\fermata-2\router_filtro.py`.
- Ingressi: le 98 domande dei fogli e le 49 a mano della metà di controllo
  (lette con le funzioni dello script di misura, come nella fermata 1), con
  l'`id_bando` del fatto; in più, se si decide, le 20 domande vere del
  25/11 (decisione 6).
- Per domanda: una sola chiamata del router (`costruisci_router`), con il
  profilo dell'ente e lo stato dell'archivio come nell'app; poi
  `esegui_interrogazioni` su una copia di SQLite, con la data fissata
  (proposta 2026-11-25, decisione 6) e il codice della sezione 1 (regola
  stretta e regola larga calcolate tutte e due).
- `--stima`: costo senza modello, con le costanti di
  `scripts/diagnostica/prova_insieme.py` (lunghezza del messaggio del
  router, prezzi). `--tetto-dollari`: si ferma prima della domanda che
  farebbe superare il tetto. Senza `--tetto-dollari` non chiama il modello.
  Nessuna rete se non la chiamata del router.
- Salva, una riga per domanda in un JSON: testo del router, decisione,
  `stop_reason`, token e costo, per ogni `dettaglio_bando` il parametro,
  il passo, i bandi trovati e `trovato`; filtro larga e stretta; bando del
  fatto; esito "giusto", "sbagliato", "nessun filtro".
- Fatti trovati con il filtro dell'app, senza modello e senza motore: con
  il filtro sul bando del fatto, l'ordine dell'app è quello di B del
  riferimento (`ordini_riferimento.json`), perché il titolo in SQLite e
  quello dei frammenti coincidono per i 12 bandi degli avvisi (sezione 6,
  punto 4) e la sotto-fermata 2.2 lo verifica; senza filtro, l'ordine di A.
  Su questi ordini, `riga_misura` dello script di misura, a k=10.
- Lancio: chi mantiene il progetto.

**Costo stimato** (`--stima` simulato oggi con un messaggio di 160
caratteri): circa 1.970 token in ingresso a chiamata, prezzi del progetto 2
$ e 10 $ per milione. 147 domande: 0,70 $ con 80 token in uscita, 1,31 $
con 500, 3,59 $ al massimo dei token del router (2048). Con le 20 vere:
0,10-0,18 $ in più. Tetto proposto: 2 $.

**Regola di chiusura, scritta ora**:
- zero filtri su un bando diverso da quello del fatto, con la regola
  scelta (decisione 1). Uno solo e la fermata non chiude;
- quota delle domande filtrate riportata, senza soglia;
- fatti trovati con il filtro dell'app riportati come descrizione, attesi
  tra 71 e 77 su 98 (A e B a k=10), e 38-42 su 49 a mano.

## 6. Casi difficili

1. **I due bandi Pmi** (`…-7057d9`, "commissioni di garanzia su
   finanziamenti fino 50 mila euro", e `…-8cd3ac`, "costi di garanzia su
   finanziamenti bancari EU-Blending"), più un terzo titolo simile senza
   frammenti (`incentivi-3373`). Provati a mano dei parametri possibili:
   "Pmi", "Bando 2026 Pmi", "abbattere interessi", "bando Pmi garanzia"
   danno 2 o 3 bandi, quindi nessun filtro; "50 mila", "Pmi 50 mila",
   "fino 50 mila euro" filtrano sul 50 mila; "EU-Blending" sull'altro.
   **Rischio concreto**: "finanziamenti bancari" e "costi di garanzia"
   filtrano su EU-Blending, ma chi chiede di un "finanziamento bancario di
   30 mila" pensa al 50 mila. Se il router passa quelle parole, è un filtro
   sbagliato. Lo dirà la sezione 5; la tappa 7 è il rimedio vero.
2. **Gli apistici in quattro parti**: un solo `id_bando` (165 frammenti,
   azioni B1, B3, B4, B5 e gli allegati): il filtro tiene tutte le parti.
   "apistiche", "aziende apistiche", "apistici" filtrano; "api" e "miele"
   non trovano niente (nessun filtro); "apicoltura" arriva dal testo degli
   interventi, quindi filtra solo con la regola larga. La domanda
   sull'azione resta (caso 70).
3. **Bando trovato ma scaduto o sospeso.** Oggi tre bandi con frammenti
   sono scaduti: Punti Digitale Facile (26/11), educazione musicale di
   base (27/11), mercati rionali (15/10). Proposta: il filtro vale anche
   per lo scaduto, perché il bando è quello giusto e lo stato arriva nel
   frammento ("stato del bando", `con_stato_del_giorno`); ma non quando la
   tappa 6a aggiunge candidati non scaduti, perché allora chi chiede
   potrebbe volere uno di quelli (regola stretta). Sospensioni in archivio:
   una sola, su un bando senza frammenti. Sospeso del tutto: come lo
   scaduto (decisione 5).
4. **La domanda ripulita.** Nella misura la ripulitura usa il titolo
   dell'ultimo frammento del bando in ordine di id; nell'app userà il
   titolo in SQLite (piano della fermata 1, sezione 9, punto 6).
   Controllato oggi: per i 12 bandi degli avvisi il titolo dei frammenti è
   uno solo ed è uguale a quello in SQLite, quindi la domanda ripulita è
   identica. Differisce solo per `mercati-rionali-2026` (due parole in
   più nel titolo dei frammenti, "manifestazione" e "interesse"), che non
   è tra i bandi misurati in B. La sotto-fermata 2.2 lo verifica
   sull'identità degli ordini.
5. **Bando senza avviso ma con `id_bando`**: `mercati-rionali-2026` (117
   frammenti, documento di sempre, già su Postgres). Il filtro su di lui
   non è mai stato misurato (decisione 2).

## 7. Venti domande sulle spese: cosa ci si aspetta

Senza aprirle, solo come attesa: sono state scritte per nominare un bando
di cui l'avviso dice le spese, quindi il router dovrebbe scegliere spesso
`dettaglio_bando` e il filtro dovrebbe scattare spesso, sul bando nominato.
Il rischio è lo stesso della sezione 6: i due Pmi, e un nome dato con parole
del testo invece che del titolo (nessun filtro con la regola stretta, che
qui è il caso sicuro). Si vedranno nella fermata 5, nel "dopo".

## 8. Sotto-fermate

Ognuna in un giro. Nessuna chiama il modello di linguaggio tranne la 2.3,
che lancia chi mantiene il progetto. Regole scritte ora.

### 2.0 Prova zero, senza modello (fatta oggi)

- **Cosa cambia**: niente nel repository; lo script della sezione 3.
- **Misura**: sezioni 3 e 4.
- **Regola di chiusura**: sui 116 titoli, zero filtri su un bando diverso
  dal titolo; gli altri insiemi riportati e letti. Esito: 0 su 13.
- **Come si torna indietro**: non serve.
- **Punto di arresto**: questo piano.

### 2.1 Codice dietro l'interruttore, spento

- **Cosa cambia**: i file della sezione 1; test nuovi in
  `tests/test_filtro_bando.py`: passo restituito per ciascun passo;
  `bando_per_nome` pieno solo con la regola scelta (un caso per ogni
  esclusione: testo, parziale, due bandi, non bando, blocco 6a); più
  chiamate; bando senza frammenti; `recupera_nel_bando` chiama
  `cerca_nel_bando` e riordina sulla domanda ripulita; interruttore
  spento, `prepara` come prima; `ORDINE_C_LR` spento, nessun filtro; il
  campo non arriva nel testo dato al modello.
- **Misura senza modello**: i tre insiemi (116 titoli, 12 parametri, 36
  parole) e le 40 della strada C: testo, `trovato` e fonti di
  `dettaglio_bando` identici a prima della modifica; `bando_per_nome`
  uguale al filtro stretto dello script della 2.0, caso per caso. R2 della
  fermata 1 a interruttore spento (22 domande, due esecuzioni del codice di
  prima).
- **Regola di chiusura**: insiemi identici; `bando_per_nome` uguale alla
  2.0 in tutti i casi; R2; test nuovi visti fallire senza il pezzo che
  proteggono; ruff e pytest.
- **Come si torna indietro**: `FILTRO_PER_BANDO = False` (resta così);
  il campo nuovo non è letto da nessun altro.
- **Punto di arresto**: tabelle, ruff e pytest.

### 2.2 Identità del percorso filtrato, senza modello

- **Cosa cambia**: niente nel repository; script fuori
  (`..\dati-grezzi\prova\19e\fermata-2\identita_filtro.py`).
- **Misura**: per ogni fatto delle quattro serie, `recupera_nel_bando`
  dell'app con l'`id_bando` del fatto e il titolo da SQLite, sul motore
  dall'archivio Chroma (in copia); ordine dei 30 contro B del riferimento.
  Modalità veloce sulle 49 a mano prima delle serie intere.
- **Regola di chiusura**: 336 su 336 in B, scarto dei voti contro
  `identita.json` della 1.2 zero alla sesta cifra. Una differenza non
  spiegata e la sotto-fermata non chiude.
- **Come si torna indietro**: non serve; se non chiude, si corregge
  `recupera_nel_bando`.
- **Punto di arresto**: tabella per serie; tempi.
- Tempo macchina: circa un'ora (veloce 10 minuti).

### 2.3 Router sulle 147 domande del controllo

- **Cosa cambia**: niente nel repository; lo script della sezione 5,
  provato prima con un router finto e con `--stima`.
- **Misura**: sezione 5, lanciata da chi mantiene il progetto.
- **Regola di chiusura**: quella della sezione 5.
- **Come si torna indietro**: l'interruttore è già spento.
- **Punto di arresto**: tabella del router (scelte, filtri, giusti,
  sbagliati, nessun filtro), casi filtrati letti a mano, fatti trovati.
  Se c'è un filtro sbagliato: ci si ferma e si porta il caso a chi mantiene
  il progetto (decisione 8).

### 2.4 Chiusura

Documenti: questo piano, `piano-19e.md`, `coda.md`, `fatto.md`, roadmap.
`FILTRO_PER_BANDO` resta spento fino alla fermata 4; il README cambia
nella fermata 5.

### Stima dei giri e rischio

| sotto-fermata | giri | rischio |
|---|---|---|
| 2.0 | 1 (questo, insieme alla chiusura della fermata 1) | — |
| 2.1 | 1-1,5 | medio: `trova_bandi` si tocca, i tre insiemi devono restare identici; il campo nuovo di `Risultato` può comparire nei JSON salvati dalla prova dell'insieme |
| 2.2 | 0,5-1 | basso: i titoli coincidono, il codice è quello della misura |
| 2.3 | 0,5 più il lancio | **alto**: dipende da cosa scrive il router, che non si controlla. Un filtro sbagliato (i due Pmi, una parola comune) ferma la fermata; la correzione va misurata su domande nuove, e qui il lavoro può triplicare |
| 2.4 | 0,5 | basso |
| totale | 3,5-4,5 | |

## 9. Cose che non tornano

1. **"Trovato per nome" non è `trovato=True`.** Nel codice `trovato=True`
   comprende il testo dei beneficiari e degli interventi e la
   corrispondenza parziale. La regola larga, presa alla lettera, filtra
   "mutuo" sul bando parcheggi. Proposta: la regola stretta (decisione 1).
2. **La prova zero su dati salvati copre poco**: delle 226 risposte solo
   182 hanno la decisione, solo 12 usano `dettaglio_bando`, e sono due
   domande (parcheggi e fondo strade) ripetute. Le 20 vere non hanno il
   parametro. La prova vera è la 2.3.
3. **I limiti noti oggi non fanno danni per caso**: colpiscono bandi senza
   frammenti. Con più avvisi caricati i falsi risultati del passo del
   testo diventerebbero filtri sbagliati; con la regola stretta quel passo
   non filtra mai.
4. **Il numero atteso tra 71 e 77 non è un limite garantito.** Con tutti i
   filtri giusti, il conto è A per le non filtrate e B per le filtrate: se
   un fatto è trovato in A e non in B, il conto può scendere sotto 71. Il
   numero dei fatti "A sì, B no" sta nei CSV salvati del controllo e non è
   stato letto (decisione 7).
5. **Bandi piccoli**: con il filtro sul fondo strade il modello riceve al
   più 5 frammenti. Come nella misura in B, quindi non cambia il numero;
   cambia la risposta, che avrà meno testo. I vicini (fermata 3) ne
   aggiungono.
6. **`mercati-rionali-2026`**: ha `id_bando` senza essere un avviso, è già
   online, il titolo dei frammenti è diverso da quello in SQLite, ed è
   scaduto. Il filtro su di lui non è mai stato misurato.
7. **Una parola comune come nome** ("dati", "strada"): filtra. Visto dopo la
   misura, quindi non entra nella regola; si guarda nella 2.3.
8. **Più chiamate di `dettaglio_bando` in una decisione**: regola scritta
   (un solo bando da tutte insieme), ma nei dati salvati non c'è nessun
   caso.

## 10. Decisioni che aspettano chi mantiene il progetto

1. **Regola stretta o larga** (sezione 3). Proposta: stretta, cioè solo i
   tre passi del titolo, bando di natura "bando", nessun blocco della
   tappa 6a.
2. **Filtro solo sui bandi con frammenti di avviso** (`sha256`), quindi
   non su `mercati-rionali-2026`, finché non è misurato. Proposta: sì.
3. **Dove nasce l'id**: campo nuovo `bando_per_nome` del `Risultato`,
   riempito da `dettaglio_bando` (proposta), o una funzione a parte che
   rifà la ricerca sui parametri del router (nessun cambio a
   `dettaglio_bando`, ma la ricerca fatta due volte e due codici da tenere
   allineati).
4. **`FILTRO_PER_BANDO` solo con `ORDINE_C_LR` acceso** e un motore;
   altrimenti nessun effetto, scritto nel registro all'avvio.
5. **Scaduti e sospesi del tutto**: filtro sì, con lo stato nel frammento
   (proposta), o nessun filtro.
6. **Misura 2.3**: data fissata (proposta 2026-11-25), tetto (proposta 2
   $), e se aggiungere le 20 domande vere del 25/11 (0,10-0,18 $ in più),
   che oggi non hanno il parametro salvato.
7. **Lettura dei CSV salvati del controllo** per contare i fatti "A sì, B
   no" (sezione 9, punto 4): è un esito della metà di controllo, serve il
   via.
8. **Se la 2.3 dà un filtro sbagliato**: proposta, la fermata si ferma; la
   correzione (una regola più stretta, scritta prima) si misura con il
   router sulle 189 domande della taratura (0,9-1,7 $), non di nuovo sul
   controllo; altrimenti il filtro aspetta la tappa 7.

## 11. Una soluzione migliore

**Un filtro che sbaglia senza togliere tutto.** Oggi il filtro sostituisce
la ricerca: sul bando sbagliato, zero frammenti giusti. Alternativa: con un
bando trovato, la lista data al modello è un'unione a quote, per esempio i
primi 7 di B e i primi 3 di A senza doppioni (come le quote di `avvolgi`).
Con il bando giusto si perde poco rispetto a B; con quello sbagliato restano
i primi di A, e l'errore grave diventa tollerabile. Si misura senza modello
e senza motore, perché gli ordini interi di A e di B di ogni fatto sono già
in `ordini_riferimento.json`: si calcola il conto dei trovati per alcune
quote **sulla taratura** (189 fatti), si sceglie una quota con una regola
scritta prima, e solo dopo si guarda il controllo, una volta. Costo: un
giro in più, nessun dollaro. Non sostituisce la tappa 7: la rende meno
urgente.
