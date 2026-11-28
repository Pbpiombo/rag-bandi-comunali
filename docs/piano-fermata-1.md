# Piano della fermata 1 del 19e: motore della misura in `src/`

Scritto il 28/11/2026, come piano: nessun codice dell'app, nessuna
chiamata al modello di linguaggio, nessuna rete, nessun Postgres. Fermata 1
del rilascio 2 di `docs/piano-19e.md` (sezione 8, "Correzione a", punto 3;
sezione 6, "Un'impostazione migliore"; "Decisioni del 25/11/2026",
decisioni 1 e 2; "Correzione d").

Fonti lette: `docs/piano-19e.md`, `CLAUDE.md`, `docs/coda.md` ("Passo
19d", punto 13, voci 19-21; "Prova di memoria su Streamlit (25/11/2026)";
le voci del 27/11 sugli avvisi riconosciuti da `sha256`; la voce sulla
ricerca di Chroma non ripetibile, punto 6 del "Passo 19d"),
`docs/prova-memoria.md` (promemoria in fondo e sezione 5), `docs/fatto.md`
(27/11/2026), e il codice di `scripts/diagnostica/misura_recupero_avvisi.py`,
`scripts/diagnostica/genera_contesti.py` (lettura dei contesti),
`src/retrieval.py`, `src/pgstore.py`, `src/recupero_documenti.py`,
`src/chains/rag.py`, `src/config.py`, `src/vectorstore.py`, `app/app.py`,
più gli script fuori dal repository `..\dati-grezzi\prova\19e\rifai_ordini.py`
e `controllo_contesto_app.py`.

Le decisioni che il piano chiede sono raccolte in fondo (sezione 10).

## 1. Prova zero (28/11/2026)

Domanda: lo script di misura, così com'è oggi (impronta `216d67cc8abc`),
riproduce ancora le misure salvate del 19d? Senza modello di linguaggio,
senza rete, con il Chroma vero aperto solo in copia.

**Campione**: c-LR tutte, la configurazione da portare in `src/`; la metà
di controllo intera, 98 domande dei fogli e 49 a mano; condizioni A e B,
k=10 e k=15. Perché basta, e perché non meno:
- è la metà da cui vengono i numeri della regola di chiusura (77 su 98 in
  B, 71 su 98 in A);
- A non era mai stata rifatta dopo il 23/11. B sulle quattro serie sì: il
  24/11 `rifai_ordini.py` ha dato 672 posizioni uguali su 672;
- un campione più piccolo (le sole 49 a mano) non avrebbe controllato
  nessuno dei numeri citati;
- la taratura usa lo stesso codice e gli stessi ingressi: si rifà nella
  sotto-fermata 1.0, quando servono i suoi ordini di A.

**Script**: `..\dati-grezzi\prova\19e\fermata-1\prova-zero\prova_zero.py`.
Chiama le funzioni dello script senza cambiarle: contesti, `apri_contesto`
sui vettori v0, osiria in locale, `misura_riordinata`. Per avere gli ordini
interi registra da fuori i candidati passati a `trovato_in` e gli indici
restituiti da `riordina`. Uscita: `ordini_prova_zero.json` nella stessa
cartella (impronta `20b42441e55375e7…`), con gli ordini interi dei 30 in A
e in B, e il registro `prova_zero.log`.

**Esito: riesce.**

| serie | righe uguali k=10 | righe uguali k=15 | ordini di B uguali al 24/11 | trovati A / B, k=10 | trovati A / B, k=15 |
|---|---|---|---|---|---|
| fogli | 98 su 98 | 98 su 98 | 98 su 98 | 71 / 77 | 74 / 83 |
| a mano | 49 su 49 | 49 su 49 | 49 su 49 | 38 / 42 | 40 / 42 |

- "Righe uguali" vuol dire tutte le colonne del CSV salvato: posizioni dei
  pezzi, posizioni profonde, primo giusto, trovato, cause, gemelli, in A e
  in B. Non ci sono differenze da spiegare.
- Candidati tra i 30 uguali a quelli del 23/11: fogli A 75 e B 88, a mano
  A 41 e B 43.
- In A l'ordine intero non si può confrontare con un file del 19d, perché
  non è mai stato salvato (sezione 9, punto 1). Le colonne coincidono, e
  gli ordini di oggi diventano il riferimento.
- Tempi: 1922 s in tutto (fogli 1227 s, a mano 598 s). Mediana del
  riordino per domanda: fogli A 6,21 s e B 6,15 s; a mano A 5,97 s e B
  5,93 s. Il 23/11 erano 5,49 e 5,29 s sui fogli, 5,64 s in B a mano:
  oggi circa il 15% più lento sullo stesso PC, senza effetti sugli ordini.
- Chroma vero: impronte dei 6 file uguali prima e dopo, controllate dallo
  script e di nuovo a parte.

**Contesti contro il Chroma di oggi** (copia del Chroma vero nella
cartella temporanea della sessione, sola lettura, nessuna scrittura):
- il Chroma di oggi e v0 (`v0\frammenti.json`, `v0\vettori.npy`)
  coincidono in tutto: 1187 frammenti, stessi id, testi e metadati, e
  vettori uguali bit per bit, 1187 su 1187;
- gli 871 contesti di `contesti.jsonl` corrispondono uno a uno agli 871
  frammenti degli avvisi (con `sha256`): stesso insieme di (fonte,
  chunk_num), impronta del testo uguale in 871 casi su 871, id uguale in
  871 su 871, una sola impronta delle istruzioni (`a758adc6d26c`);
- scartati 36, i 36 attesi (elenco del 21/11 in
  `..\dati-grezzi\prova\19d\contesto\misura_21-11.txt`, passo 1.6):
  - 13512: #0 #1 #2 #78 #102 #104 #124 #125;
  - 22706: #8 #9 #13 #14 #15 #16 #54;
  - 25205: #37 #54 #55 #56 #58;
  - 9506: #78 #89 #98 #99 #111;
  - SRA-ACA16: #11 #101 #150 #151;
  - 24161: #21 #22 #23;
  - 18191 #10, A3 #36, A4 #21, Sport #9.
  Con il contesto restano 835 frammenti;
- da sapere per il motore: `get()` di Chroma non restituisce i frammenti
  in ordine di id. La misura li ordina per id (`esporta_frammenti`), e da
  quell'ordine dipendono i pari merito. Nel Chroma 20 testi sono ripetuti
  in 44 frammenti.

**Librerie**: torch 2.14.0, sentence-transformers 6.0.1, transformers
5.17.0, chromadb 1.5.9, numpy 2.5.3 e rank-bm25 0.2.2 sono installati
dall'11-12/09/2026, prima del 19d; Python 3.13.12.

## 2. Inventario: dove sta oggi il motore misurato

Il motore misurato è c-LR tutte: ricerca per significato esatta sui
vettori v0, ricerca per parole (BM25) con il contesto davanti al testo,
fusione RRF, 30 candidati al riordinatore osiria L12 con il contesto
davanti, primi 10. In A i candidati vengono dal percorso dell'app
(`avvolgi` più `recupera`), in B dalla ricerca ristretta al bando.

Righe di `scripts/diagnostica/misura_recupero_avvisi.py` all'impronta
`216d67cc8abc` (la stessa dell'apertura del controllo del 23/11/2026,
ricontrollata oggi).

| pezzo | dove sta | da cosa dipende | si sposta così com'è? | chi lo importa oggi |
|---|---|---|---|---|
| contesto davanti al testo | `testo_con_contesto`, r. 1042 | niente | sì, pura | lo script (`apri_recupero`, `esegui_prepara_vettori`, `testo_per_riordino`); `tests/test_misura_contesto.py` |
| indice BM25 sul testo con il contesto | `RecuperoMisura.__init__`, r. 949-975, classe definita dentro `apri_recupero` | `BM25Okapi`, `tokenizza` (`src/retrieval.py`), `testo_lessicale` (con `prefissi=None` non cambia il testo) | no: è una classe chiusa in una funzione, va riscritta come classe del modulo nuovo, con lo stesso calcolo | nessuno da fuori (la usano `apri_contesto` e `apri_recupero_esatto` dello script) |
| ricerca per parole ristretta a un documento | `RecuperoIbrido._lessicale`, `src/retrieval.py` r. 89 | `self.bm25`, `self.documenti` | già in `src/`; il motore la eredita o la copia | `RecuperoIbrido.cerca` |
| ricerca per significato esatta | `StoreEsatto`, r. 2558; `controlla_normalizzati`, r. 2548 | numpy, `Document`, embeddings con `embed_query` | quasi: cambia solo l'eccezione (`ErroreMisura` è dello script) | lo script; `tests/test_misura_recupero_avvisi.py` (3 usi); `..\dati-grezzi\prova\19d\contesto\mancati_*.py` |
| lettura dell'archivio | `esporta_frammenti`, r. 2606 (Chroma, ordinato per id); `leggi_vettori`, r. 2646 (file di v0) | chromadb, numpy | riscritta come "archivio Chroma"; `leggi_vettori` resta nello script | lo script; `genera_contesti.leggi_documenti` usa `leggi_vettori` |
| embeddings delle domande | `crea_embeddings_di(MODELLI["v0"])`, r. 2662 | `HuggingFaceEmbeddings`, normalizzati | non serve: è la stessa configurazione di `crea_embeddings` di `src/vectorstore.py` (stesso modello, nessun limite) | lo script |
| fusione RRF, ricerca generale | `RecuperoIbrido.cerca`, `src/retrieval.py` r. 106 | `store.similarity_search`, `_lessicale`, `COSTANTE_RRF = 60`, ampiezza 20 | già in `src/`; il motore la usa con lo store esatto | l'app, lo script (eredità) |
| percorso di A | `avvolgi` e `RecuperoPerDocumento` (`src/recupero_documenti.py`), `recupera` (`src/chains/rag.py` r. 43) | `titoli()`, `cerca(domanda, k, fonte)` | già in `src/`, non si tocca | l'app; lo script (`misura_riordinata`, r. 5228, con k=30) |
| ricerca ristretta a un bando | `RecuperoMisura.cerca_nel_bando`, r. 977 | `store.similarity_search` con filtro `id_bando`, BM25 su tutto l'indice, pesi 2·0,5 = 1 | no: chiusa nella classe; si riscrive identica come metodo del motore | lo script; `..\dati-grezzi\prova\19e\rifai_ordini.py`, `vicini.py`, `mancati_controllo.py` |
| domanda ripulita in B | `domanda_ripulita`, r. 1091, con il titolo da `frammenti_della_copia`, r. 1894 | `parole_titolo`, `ripulisci_domanda` (`src/recupero_documenti.py`); titolo dell'ultimo frammento del bando in ordine di id | resta nello script: è come la misura costruisce la domanda di B, non un pezzo del motore (sezione 8, punto 6) | lo script, gli script del 19e |
| coppie per il riordinatore | `testo_per_riordino`, r. 5186; dentro `misura_riordinata`, r. 5246-5250 | `testo_con_contesto`; `CrossEncoder.predict` | `testo_per_riordino` sì; la parte del ciclo che forma le coppie e chiama `predict` va estratta dal ciclo, che mescola motore e valutazione | lo script; `tests/test_misura_contesto.py` (2 usi); gli script del 19e |
| tetto dei 512 token | non è codice dello script: è `max_seq_length` del modello (512) e il troncamento di `CrossEncoder.predict` in sentence-transformers 6.0.1 | versione della libreria e revisione del modello | si riproduce caricando lo stesso modello con la stessa libreria; revisione da fissare (sezione 8, punto 5) | — |
| 30 candidati | `CANDIDATI = 30`, r. 3629 | — | una costante in `src/config.py` | lo script |
| ordine dopo il riordino | `riordina`, r. 4380 | numpy | sì, pura (cambia l'eccezione) | lo script; `tests/test_misura_recupero_avvisi.py` (3 usi); gli script del 19e |
| caricamento del riordinatore | `esegui_contesto`, r. 5964 | `CrossEncoder(RIORDINATORI["osiria"], trust_remote_code=False, local_files_only=True)` | si riscrive come funzione di caricamento, con `local_files_only` solo in locale | lo script |
| contesti per frammento | `contesti_da`, `contesti_della_misura`, `contesti_per_frammento`, r. 5107-5174 | `genera_contesti` (controlli, segni tolti, testo dei PDF), `testo_di_ricerca` | no: servono una volta sola, per scrivere i contesti nell'archivio (sezione 4); il motore legge solo il testo già composto | lo script, gli script del 19e, `tests/test_genera_contesti_gruppi.py` e `tests/test_misura_contesto.py` (`contesti_da`) |

Due cose che l'inventario mostra e che il piano del 19e non diceva:

- `recupera` non si può cambiare: lo script la chiama per i candidati di A
  (`recupera(app, domanda, k=CANDIDATI)`). Il riordino va in una funzione
  nuova accanto, non dentro `recupera` (piano del 19e, tappa 1, "src/chains/rag.py
  (recupera)"; sezione 8, punto 2).
- Il riordino sta fuori da `avvolgi`. Se il recupero passato alla catena
  riordinasse dentro `cerca`, `RecuperoPerDocumento` riordinerebbe ogni
  lista prima di unirle: non è il percorso misurato. Ordine misurato:
  `avvolgi(motore)`, 30 candidati, poi riordino sulla domanda
  normalizzata, poi i primi k.

## 3. Disegno: un solo motore, due archivi

### Pezzi

1. **Archivio**: dà una sola cosa, `Frammenti` (id, testi, metadati,
   matrice dei vettori, contesti per (fonte, chunk_num)), **ordinata per
   id**. Due realizzazioni:
   - `ArchivioChroma(cartella)`: `get(include=["documents", "metadatas",
     "embeddings"])` sulla collezione, poi ordine per id (come
     `esporta_frammenti`); i contesti da dove li mette la sezione 4.
   - `ArchivioPostgres` (fermata 5, non in questa fermata): una sola
     lettura della tabella, vettori in forma binaria, convertiti da
     `pgvector.Vector` a numpy (promemoria 2 di `docs/prova-memoria.md`),
     stesso ordine per id (sezione 8, punto 2).
2. **Motore in memoria** (`src/motore.py`, nome da confermare), uguale nei
   due casi, costruito da `Frammenti` e dagli embeddings delle domande:
   - `documenti`, `titoli()`, `frammento(fonte, chunk_num)` (così i vicini
     funzionano anche online, senza query nuove);
   - ricerca per significato esatta (prodotto scalare, pari merito per id:
     `StoreEsatto` copiato);
   - BM25 sul testo con il contesto davanti, punteggi su tutto l'indice;
   - `cerca(domanda, k, ampiezza=20, fonte=None)`: la fusione di
     `RecuperoIbrido.cerca`, con lo store esatto;
   - `cerca_nel_bando(domanda, id_bando, k, ampiezza=20)`: copia di
     quella della misura (serve alla fermata 2 e all'identità in B).
   - I documenti restituiti hanno **il testo pulito e i metadati del
     frammento**, mai il contesto: il contesto vive in un dizionario a
     parte del motore e non entra in nessun `Document`.
3. **Riordino** (stesso modulo o `src/riordino.py`): carica osiria L12
   una volta; `riordina_candidati(domanda, candidati, contesti)` forma le
   coppie (domanda normalizzata, contesto + "\n" + testo), chiama
   `predict`, ordina con `riordina` (copiata), restituisce i primi k con
   il voto e le origini più "riordino #n".
4. **Porta d'ingresso**: in `src/chains/rag.py` una funzione nuova,
   `recupera_riordinati(recupero, riordino, domanda, k)`, che fa
   `recupera(recupero, domanda, k=CANDIDATI_RIORDINO)` e poi il riordino.
   `prepara` la usa al posto di `recupera` solo con l'interruttore acceso;
   `con_vicini` resta dopo, com'è (vicini spenti in questa fermata).
   `costruisci_catena` e `carica_recupero` di `app/app.py` scelgono
   l'archivio: Chroma in locale, Postgres online (alla fermata 5).
5. **Interruttore** in `src/config.py`: `ORDINE_C_LR = False` e
   `CANDIDATI_RIORDINO = 30`. Spento: `RecuperoIbrido` su Chroma (o
   `RecuperoPostgres`) e `recupera`, cioè l'app di oggi riga per riga.
   Acceso: motore in memoria più riordino. Un solo interruttore, perché la
   configurazione misurata è una sola (sezione 10, decisione 3).

### Lo script di misura e le funzioni del motore

Proposta: **in questa fermata si copia, non si sposta.** Lo script resta
com'è, con l'impronta `216d67cc8abc` dell'apertura del controllo, e fa da
riferimento: l'identità della fermata confronta il motore di `src/` con
lo script, non con una copia di se stesso. Così le misure congelate del
19d non possono cambiare, perché il codice che le ha prodotte non cambia,
e i test e gli script fuori dal repository che usano `mr.riordina`,
`mr.StoreEsatto`, `mr.testo_con_contesto` continuano a funzionare.

Il doppione (circa 120 righe: `testo_con_contesto`, `riordina`,
`StoreEsatto`, `cerca_nel_bando`, la costruzione del BM25) si annota in
`coda.md` e si toglie, se si vuole, dopo la fermata 5 o al taglio a
livelli, quando gli ordini del 19d non varranno più. Se invece chi
mantiene il progetto vuole lo spostamento subito (CLAUDE.md, "Se sposti o
rinomini una funzione"), si fa come ultima sotto-fermata, dopo
l'identità: lo script importa da `src/` con gli stessi nomi, si cercano
tutti gli importatori (tabella qui sopra, anche fuori dal repository), e
la prova zero si rifà con lo script nuovo; l'impronta dello script cambia
e si annota.

## 4. I contesti: tre strade

I contesti di oggi: 871 righe in `..\dati-grezzi\prova\19d\contesto\contesti.jsonl`,
legate a id, fonte, chunk_num e impronta del testo; la misura usa le 835
non scartate, composte con le righe "tutte" (`testo_di_ricerca`), per
(fonte, chunk_num).

**Strada 1, campo `contesto` nei metadati del Chroma** (il piano del 19e,
tappa 1 e correzione d).
- Locale, pro: un solo posto; i contesti viaggiano con il frammento.
- Locale, contro: si scrive nel Chroma vero (copia di sicurezza, fermata
  per il via); ogni scrittura aggiunge operazioni alla coda dell'indice
  HNSW, che oggi non è ripetibile (punto 6 del "Passo 19d"), quindi può
  cambiare la ricerca dell'app a interruttore spento proprio mentre se ne
  controlla l'identità; il campo entra nei metadati di ogni `Document` del
  recupero di oggi (`RecuperoIbrido` legge tutti i metadati), quindi
  anche a interruttore spento i documenti non sono più identici a oggi, e
  il contesto viaggia fino al blocco dello stato, all'app e al
  verificatore, dove la decisione 2 non lo vuole.
- Postgres, fermata 5: la copia dal Chroma porta il campo nel `jsonb`
  `metadata`; semplice, ma lo stesso rischio di fuga nei metadati.
- Taglio a livelli: si riscrive il Chroma intero comunque; pari.

**Strada 2, file a parte letto dal motore in locale, tabella o colonna a
parte online.**
- Locale, pro: il Chroma vero non si scrive; i metadati dei frammenti
  restano identici a oggi; il contesto per costruzione non è nei
  `Document`. Ogni riga porta (fonte, chunk_num, impronta del testo del
  frammento, testo del contesto composto, origine "modello", impronta
  delle istruzioni `a758adc6d26c`): un contesto vale solo se l'impronta
  del testo coincide, quindi un nuovo caricamento non può attaccarlo al
  frammento sbagliato, e il motore all'avvio conta e riporta quelli che
  non tornano.
- Locale, contro: due cose da tenere allineate (Chroma e file); serve un
  posto per il file (proposta: `data/db/contesti_avvisi.jsonl`, accanto al
  Chroma, fuori dal repository con una riga in `.gitignore`; decisione 2).
- Postgres, fermata 5: una tabella `contesto` (o una colonna) caricata
  dallo stesso file, con lo stesso controllo dell'impronta; il motore la
  legge nella stessa lettura dell'avvio.
- Taglio a livelli: si rigenera il file, con un'impronta nuova; nessuna
  scrittura nel Chroma vecchio.

**Strada 3, contesti composti dal codice a ogni avvio** da `contesti.jsonl`
con `contesti_della_misura` (come fa la misura). Pro: nessun file nuovo.
Contro: l'app dipenderebbe da `scripts/diagnostica/genera_contesti.py`,
dai PDF in `dati-grezzi` e dai controlli dei contesti; online non c'è
`dati-grezzi`. Scartata.

**Scelgo la strada 2.** Lo script che scrive il file
(`scripts/ingestione/esporta_contesti.py`, nuovo) usa
`contesti_della_misura(..., "tutte")` dello script di misura, cioè esattamente
il dizionario della misura: 835 contesti, nessuno dei 36 scartati. Non
scrive nel Chroma vero, quindi copia di sicurezza e fermata per il via
del Chroma non servono; la modalità manuale resta (lo script scrive solo
con `--scrivi`, senza confronta e dice cosa scriverebbe; non sovrascrive
un file esistente con un'impronta diversa). Se chi mantiene il progetto
preferisce la strada 1: copia di sicurezza di `data\db\chroma` in
`..\dati-grezzi\backup\`, fermata per il via prima della scrittura,
scrittura solo con `--scrivi`, e la regola dell'interruttore spento
(sezione 6, regola R2) va controllata prima e dopo la scrittura.

## 5. Cosa entra subito dalle scoperte recenti

- **Avvisi riconosciuti da `sha256`**: il motore usa
  `e_frammento_di_avviso` per i contesti (solo i frammenti degli avvisi
  ne hanno uno, e il file lo verifica: ogni riga deve cadere su un
  frammento con `sha256`) e lascia a `con_vicini` le sue regole.
- **Ricerca di Chroma non ripetibile**: l'identità si fa solo sul motore
  esatto, mai sull'indice HNSW. A interruttore spento l'app resta su
  Chroma e quindi resta non ripetibile: la regola R2 della sezione 6 ne
  tiene conto. L'ordine di `get()` di Chroma non è l'ordine per id
  (controllato oggi): il motore ordina sempre per id, perché pari merito
  e ordine del BM25 dipendono da quell'ordine, e nel Chroma ci sono 20
  testi ripetuti in 44 frammenti (pari merito esatti, per esempio negli
  allegati degli apistici).
- **Vettori da Postgres come `pgvector.Vector`**: va nell'interfaccia
  dell'archivio ora (la conversione è dell'archivio, il motore riceve una
  matrice numpy); il codice di `ArchivioPostgres` si scrive nella fermata
  5, con un test su un oggetto finto con `to_numpy()`.
- **torch e Python diversi tra PC e online** (PC Python 3.13.12, torch
  2.14.0+cpu; online 3.14, torch 2.15.0+cpu): nella fermata 1 non
  contano, tutto è in locale. Il motore scrive nel registro, all'avvio,
  versioni di Python, torch, sentence-transformers e le revisioni dei due
  modelli, così la fermata 5 confronta gli ambienti prima degli ordini. Il
  confronto dei 30 punteggi della sezione 5 di `docs/prova-memoria.md` si
  rifà con il codice di `src/` nella sotto-fermata 1.4, come chiede quel
  documento.

## 6. Sotto-fermate

Ognuna sta in un giro. Nessuna chiama il modello di linguaggio o la rete.
Le regole sono scritte ora, prima di ogni codice.

Numeri attesi dai CSV salvati (c-LR tutte, fatti trovati):

| serie | A k=10 | A k=15 | B k=10 | B k=15 |
|---|---|---|---|---|
| controllo, fogli (98) | 71 | 74 | 77 | 83 |
| controllo, a mano (49) | 38 | 40 | 42 | 42 |
| taratura, fogli (97) | 76 | 77 | 83 | 85 |
| taratura, a mano (92) | 69 | 74 | 78 | 80 |

**Regola R1, identità del motore.** Su tutte e quattro le serie, in A e in
B: l'ordine intero dei 30 candidati riordinati del motore è identico, posto
per posto, all'ordine di riferimento (sezione 1 e sotto-fermata 1.0): 336
su 336 in A e 336 su 336 in B. Di conseguenza i primi 10 e i primi 15 sono
identici e i numeri sono quelli della tabella. Una differenza si spiega
una per una (per esempio pari merito); una sola differenza non spiegata e
la sotto-fermata non chiude. Una differenza spiegata non chiude lo stesso:
si corregge il motore finché è identico.

**Regola R2, interruttore spento.** Sulle 22 domande del controllo del
24/11/2026, con la catena dell'app (router fisso, modello finto, data
fissata): contesto, documenti, origini e recupero identici a quelli del
codice di `main` prima della modifica. Poiché la ricerca di Chroma non è
ripetibile, il codice di prima si esegue **due volte** prima del
confronto; una differenza è ammessa solo se compare già tra le due
esecuzioni del codice di prima (come il 27/11/2026: un rango della ricerca
densa in una domanda). Ogni differenza si elenca.

**Regola R3, nessuna fuga del contesto** (decisione 2 del 25/11/2026): il
test della sezione 7, punto 6.

### 1.0 Riferimenti completi

- **Cosa cambia**: niente nel repository. Lo script della prova zero
  (`..\dati-grezzi\prova\19e\fermata-1\prova-zero\prova_zero.py`) si
  rilancia sulla metà di taratura (97 fogli, 92 a mano). Esce
  `ordini_riferimento.json` con gli ordini interi in A e in B delle
  quattro serie, e la sua impronta.
- **Misura senza modello**: righe della misura contro i CSV salvati
  (tutte le colonne, k=10 e k=15); ordini di B contro
  `ordini_c-LR_24-11.json`.
- **Regola di chiusura**: come la prova zero, sulle due serie di
  taratura: 189 su 189 righe identiche per k, 189 su 189 ordini di B
  identici.
- **Come si torna indietro**: non serve.
- **Punto di arresto**: tabella; impronta del file dei riferimenti.
- Tempo macchina: circa 35 minuti.

**Stato (28/11/2026): chiusa.** Script
`..\dati-grezzi\prova\19e\fermata-1\riferimenti\riferimenti_taratura.py`,
copia di `prova_zero.py` con una sola differenza nel calcolo
(`LATO = mr.TARATURA`), più l'unione con gli ordini della prova zero.
Registro `riferimenti_taratura.log` nella stessa cartella.

| serie | righe uguali k=10 | righe uguali k=15 | ordini di B uguali al 24/11 | trovati A / B, k=10 | trovati A / B, k=15 |
|---|---|---|---|---|---|
| fogli | 97 su 97 | 97 su 97 | 97 su 97 | 76 / 83 | 77 / 85 |
| a mano | 92 su 92 | 92 su 92 | 92 su 92 | 69 / 78 | 74 / 80 |

- Nessuna riga diversa; numeri uguali a quelli della tabella qui sopra.
- Candidati tra i 30: fogli A 77 e B 87, a mano A 76 e B 83.
- `ordini_riferimento.json` (cartella `riferimenti`): 336 ordini, le
  quattro serie (controllo dalla prova zero, identici a
  `ordini_prova_zero.json`; taratura da questa esecuzione), sha256
  `f6c038498092a9a1246132c515801114522fcc3a8238055371b28815bd3420a9`.
  I 336 ordini di B sono uguali a `ordini_c-LR_24-11.json`. In A gli
  ordini hanno 30 posti in 335 casi e 29 in uno; in B meno di 30 quando
  il bando ha meno candidati.
- Tempi: 2639 s in tutto (fogli 1441 s, a mano 1099 s). Mediana del
  riordino: fogli A 7,20 s e B 7,09 s; a mano A 5,91 s e B 5,80 s. I
  fogli della taratura stanno sopra la forchetta 5,3-6,2 s della 1.2,
  che resta senza veto.
- Chroma vero: impronte dei 6 file uguali prima e dopo.
- Da sapere: Python avvisa di una sequenza `\p` non valida nella
  docstring dello script (solo testo, nessun effetto sul calcolo).

### 1.1 Motore e riordino in `src/`, non collegati

- **Cosa cambia**: `src/motore.py` (nuovo: `Frammenti`, `ArchivioChroma`,
  motore in memoria, riordino); `src/config.py` (`ORDINE_C_LR = False`,
  `CANDIDATI_RIORDINO = 30`, revisioni dei modelli); test nuovi (sezione
  7). Nessuna modifica a `src/chains/rag.py`, `app/app.py`, allo script di
  misura.
- **Misura senza modello**: i test; `python -c "import src.motore"`.
- **Regola di chiusura**: test nuovi verdi, ciascuno visto fallire senza
  il pezzo che protegge; pytest con gli stessi numeri di prima più i test
  nuovi; ruff con 11 segnalazioni.
- **Come si torna indietro**: si toglie il modulo; niente lo importa.
- **Punto di arresto**: elenco dei test, uscita di ruff e pytest.

**Stato (28/11/2026): fatta, in attesa del via.** `src/motore.py`
(`Frammenti`, `matrice_di`, `frammenti_da_get`, `ArchivioChroma`,
`testo_con_contesto`, `RicercaEsatta`, `Motore`, `riordina`, `Riordino`,
`carica_embeddings`, `carica_riordinatore`, `versioni`); `src/config.py`
(`ORDINE_C_LR = False`, `CANDIDATI_RIORDINO = 30`, `MODELLO_RIORDINO`,
`REVISIONE_RIORDINO`, `REVISIONE_EMBEDDING`); `tests/test_motore.py`, 15
test, ciascuno visto fallire con almeno una variante del motore senza il
pezzo che protegge (19 varianti). Scelte da sapere:
- `Motore` eredita da `RecuperoIbrido` come `RecuperoMisura`: `cerca`,
  `_lessicale`, `titoli` e `frammento` non sono copiati ma sono gli stessi
  dell'app;
- `ArchivioChroma` riceve i contesti da fuori: la lettura del file è
  della 1.3;
- `Riordino` non cambia la domanda: in A la normalizza chi chiama
  (`recupera_riordinati`, 1.4), in B arriva ripulita, come nella misura.
Test della sezione 7 rimandati: il punto 6 nella parte della catena e il
punto 8 alla 1.4; il punto 9 alla 1.3 (file dei contesti).

### 1.2 Identità del codice, sugli stessi ingressi della misura

- **Cosa cambia**: niente nel repository. Script fuori dal repository
  (`..\dati-grezzi\prova\19e\fermata-1\identita.py`): costruisce il motore
  da `v0\frammenti.json` e `v0\vettori.npy` e dai contesti di
  `contesti_della_misura` (gli stessi ingressi dello script), e per ogni
  domanda delle quattro serie calcola l'ordine dei 30 in A (con
  `avvolgi(motore)` e `recupera_riordinati` costruita nello script) e in B
  (con `cerca_nel_bando` e la domanda ripulita come la misura).
- **Misura senza modello**: confronto con i riferimenti.
- **Regola di chiusura**: R1.
- **Come si torna indietro**: non serve; se non chiude, si corregge
  `src/motore.py` e si rilancia.
- **Punto di arresto**: tabella delle identità per serie e condizione,
  ogni differenza, tempi del riordino (mediana attesa tra 5,3 e 6,2 s, i
  numeri del 23/11 e della prova zero, senza veto).
- Tempo macchina: circa un'ora per le quattro serie; una modalità veloce
  sulle 49 a mano del controllo (circa 10 minuti) per i giri di
  correzione.

**Stato (28/11/2026): chiusa, R1 rispettata.** Script
`..\dati-grezzi\prova\19e\fermata-1\identita.py` (sha256 `43378cd3…6581017e`),
registri `identita_veloce.log` e `identita.log`, uscita `identita.json`
(sha256 `ec4025ac…bbcfb`) con ordini, voti e candidati del motore. A:
`avvolgi(motore)`, `recupera` con 30 candidati e la domanda com'è scritta,
riordino sulla domanda normalizzata (`recupera_riordinati` costruita nello
script). B: `cerca_nel_bando` e riordino con la domanda ripulita come nella
misura (titolo da `frammenti_della_copia`). Modelli solo in locale, alle
revisioni fissate.

| serie | ordini A uguali | ordini B uguali | righe della misura uguali k=10 / k=15 | trovati A / B, k=10 | mediana del riordino A / B |
|---|---|---|---|---|---|
| controllo, fogli | 98 su 98 | 98 su 98 | 98 / 98 | 71 / 77 | 5,96 / 5,87 s |
| controllo, a mano | 49 su 49 | 49 su 49 | 49 / 49 | 38 / 42 | 5,85 / 5,77 s |
| taratura, fogli | 97 su 97 | 97 su 97 | 97 / 97 | 76 / 83 | 6,01 / 6,01 s |
| taratura, a mano | 92 su 92 | 92 su 92 | 92 / 92 | 69 / 78 | 5,96 / 5,87 s |

- 336 su 336 in A e 336 su 336 in B, compreso il caso di A con 29 posti
  (taratura, fogli, riga 31: `recupera` dà 29 candidati, come nel
  riferimento).
- Modalità veloce, prima delle serie intere: 49 su 49 in A e in B, righe
  della misura 49 su 49 a k=10 e k=15; 686 s in tutto.
- Nessuna differenza: zero giri di correzione, `src/motore.py` e
  `tests/test_motore.py` non toccati.
- Controllo in più, non chiesto da R1: le righe della misura
  (`riga_misura` dello script) rifatte sugli ordini del motore sono uguali
  ai CSV salvati del 19d in tutte le colonne, a k=10 e a k=15.
- Tempi: 4091 s in tutto (fogli 1162 e 1167 s, a mano 570 e 1110 s);
  caricamento di motore e modelli 24,5 s. Mediane del riordino dentro la
  forchetta 5,3-6,2 s.
- Impronta dello script di misura `216d67cc8abc` all'inizio e alla fine;
  Chroma vero mai aperto, impronte dei 6 file uguali prima e dopo.

### 1.3 Archivio locale: Chroma più il file dei contesti

- **Cosa cambia**: `scripts/ingestione/esporta_contesti.py` (nuovo),
  `.gitignore` (una riga, se si sceglie `data/db/`), `ArchivioChroma`
  legge il file. Scrittura del file solo con `--scrivi`.
- **Misura senza modello**: `Frammenti` letto dal Chroma vero (aperto in
  copia) più il file, confrontato con `Frammenti` della 1.2 (file di v0 e
  contesti della misura): stessi id nello stesso ordine, testi, metadati,
  matrice bit per bit, stesso dizionario dei contesti (835 voci, nessuna
  delle 36 scartate). Poi la 1.2 in modalità veloce con l'archivio
  Chroma.
- **Regola di chiusura**: uguaglianza esatta dei `Frammenti` (oggi attesa:
  Chroma e v0 coincidono in tutto, sezione 1); 49 su 49 ordini identici in
  A e in B nella modalità veloce.
- **Come si torna indietro**: si cancella il file; il Chroma non è stato
  scritto.
- **Punto di arresto**: esito del confronto; righe del file lette a
  campione (CLAUDE.md, "Prima di approvare un file prodotto").

### 1.4 Collegamento all'app dietro l'interruttore

- **Cosa cambia**: `src/chains/rag.py` (`recupera_riordinati`; in
  `prepara` la scelta con `ORDINE_C_LR`; `costruisci_catena` costruisce
  motore e riordino se l'interruttore è acceso e non arriva un recupero);
  `app/app.py` (`carica_recupero`: con l'interruttore acceso e
  `USA_POSTGRES` spento, motore su Chroma; con Postgres resta
  `RecuperoPostgres` fino alla fermata 5); test nuovi.
- **Misura senza modello**: R2 a interruttore spento; a interruttore acceso,
  la catena (router fisso, modello finto) sulle 49 a mano del controllo:
  i documenti dati al modello sono i primi 10 di A del riferimento, nello
  stesso ordine; confronto dei 30 punteggi della sezione 5 di
  `docs/prova-memoria.md` con il codice di `src/`; memoria del processo
  dopo il caricamento dei due modelli; tempo del riordino.
- **Regola di chiusura**: R2; 49 su 49 identici attraverso la catena; R3;
  ruff e pytest. Tempo e memoria annotati, senza veto.
- **Come si torna indietro**: `ORDINE_C_LR = False` (è il valore che resta
  su `main` alla fine della fermata).
- **Punto di arresto**: tabelle, uscite di ruff e pytest; proposta del
  commit.

### 1.5 Chiusura

Documenti: `piano-19e.md`, `coda.md` (il doppione della sezione 3 come voce),
`fatto.md`, roadmap. L'interruttore resta spento fino alla fermata 3
(vicini) e alla misura della fermata 4; il README cambia nella fermata 5.

## 7. I test

Senza caricare modelli, con il database in memoria di `tests/conftest.py`
dove serve, embeddings finti (vettori fissati per testo) e riordinatore
finto (voti da un dizionario):

1. archivio: frammenti dati in disordine escono ordinati per id (fallisce
   senza l'ordinamento: è il caso di `get()` di Chroma);
2. ricerca esatta: due vettori identici, vince l'id minore (fallisce se il
   pari merito dipende dall'ordine di arrivo);
3. BM25 con il contesto: una parola solo nel contesto trova il frammento,
   e il `Document` restituito ha il testo pulito;
4. ricerca ristretta: pesi delle parole calcolati su tutto l'indice (stessi
   punteggi della ricerca generale) e solo frammenti del bando;
5. fusione: sullo stesso archivio finto, `cerca` del motore dà gli stessi
   risultati, punteggi e origini di `RecuperoIbrido.cerca` costruito con
   `__new__` (come in `tests/test_vicini.py`);
6. contesto mai fuori dal motore (decisione 2): un frammento con nel
   contesto un numero assente dal testo; nella catena con modello finto il
   numero non compare nel contesto dato al modello, né nel testo dato al
   verificatore, né nei documenti dell'esito (le fonti mostrate). Si
   verifica che fallisca con una variante del motore che mette il contesto
   nel testo;
7. riordino: coppie (domanda normalizzata, contesto + a capo + testo),
   pari merito nell'ordine di prima, voti a due colonne presi dall'ultima;
8. porta d'ingresso: `recupera_riordinati` chiede 30 candidati ad
   `avvolgi` e riordina fuori; con l'interruttore spento `prepara` chiama
   `recupera` come oggi;
9. file dei contesti: riga con l'impronta del testo diversa scartata e
   contata; riga su un frammento senza `sha256` rifiutata.

Fuori dal repository restano l'identità (1.2, 1.3, 1.4) e la prova zero:
caricano i due modelli veri. Tempi: i test nuovi stanno nei secondi; la
1.2 intera circa un'ora, la modalità veloce circa 10 minuti; la R2 pochi
minuti (22 domande, due esecuzioni di prima e una di dopo).

## 8. Stima dei giri e rischio

| sotto-fermata | giri | rischio di triplicare |
|---|---|---|
| 1.0 | 0,5 (quasi tutto tempo macchina) | basso: è lo stesso script della prova zero |
| 1.1 | 1-1,5 | basso |
| 1.2 | 1 | **alto**: ogni differenza di ordine va inseguita fino al pari merito o al calcolo che la causa |
| 1.3 | 0,5-1 | medio: file nuovo, allineamento |
| 1.4 | 1-1,5 | **alto**: catena, `avvolgi`, vicini, cache di Streamlit, R2 con Chroma non ripetibile |
| 1.5 | 0,5 | basso |
| totale | 4,5-6 | il piano del 19e dava 2-3 giri alla tappa 1 |

Confronto con il 19d. Lì il tempo è andato in: una non ripetibilità
scoperta a misura avviata (Chroma), che ha chiesto la misura esatta e il
rifacimento dei vettori; un controllo che ha aperto il Chroma vero;
controlli dei contesti corretti dopo aver visto le violazioni; più varianti
aperte insieme. Qui: la non ripetibilità è già nota e l'identità si fa solo
sul motore esatto; la strada 2 non scrive nel Chroma vero; le regole e i
numeri attesi sono scritti ora; una sola configurazione. Resta il rischio
che un'identità al 100% sia più difficile del previsto per un dettaglio di
calcolo (ordine delle somme, `float32` contro `float64`, ordine delle
liste nella fusione): per questo la 1.2 confronta il codice sugli stessi
ingressi della misura prima di cambiare archivio.

## 9. Cose che non tornano

1. **Le misure del 19d non hanno gli ordini di A.** I CSV tengono solo le
   posizioni dei pezzi giusti, il trovato e le cause; gli unici ordini
   interi salvati sono quelli di c-LR in B (`ordini_c-LR_24-11.json`, 336,
   rifatti il 24/11). "100% degli ordini identici in A" non si può
   controllare contro un file del 19d. Alternative: (a) identità in A
   sulle sole colonne della misura (posizioni, trovato), più debole; (b)
   ordini di A rigenerati oggi dallo script congelato, controllati contro
   i CSV colonna per colonna (prova zero e 1.0), e identità del motore
   contro quelli. Scelgo (b).
2. **Il tie-break della misura è l'id di Chroma**, e Postgres non lo ha: la
   tabella `chunk` ha un suo `id` numerico, e le 316 righe di oggi sono
   state caricate da `ingest_tutti` con `salva_chunk_in_db`, che calcola
   i vettori una seconda volta, a parte da quelli del Chroma: uguali
   probabilmente, non per costruzione. Per l'identità online della fermata 5 l'archivio
   Postgres deve dare gli stessi id e gli stessi vettori. Alternative: (a)
   alla fermata 5 si ricarica tutta la tabella (1187 righe) dal Chroma,
   con l'id di Chroma in una colonna o nei metadati e i vettori copiati;
   (b) si cambia il tie-break in (fonte, chunk_num), che c'è in tutti e
   due gli archivi, ma allora i riferimenti del 19d valgono solo se la 1.2
   mostra che il cambio non tocca nessun ordine, e la regola andrebbe
   scritta prima. Scelgo (a); l'interfaccia dell'archivio lo prevede da
   subito.
3. **"A interruttore spento identico a oggi" non è garantito** con la
   ricerca di Chroma non ripetibile (il 27/11 un rango è cambiato tra due
   esecuzioni dello stesso codice). Alternative: regola R2 (due esecuzioni
   di prima, differenze ammesse solo se già tra quelle); oppure misurare
   l'interruttore spento su una copia del Chroma ricostruita senza coda
   (cambia l'app di oggi, no). Scelgo R2.
4. **`recupera` non si può cambiare** (sezione 2): il piano del 19e la
   indicava come punto del riordino. Funzione nuova accanto.
5. **Il tetto dei 512 token non è codice nostro**: dipende dalla versione
   di sentence-transformers (fissata a 6.0.1 in `requirements.txt`) e dalla
   revisione del modello osiria, che online si scarica a ogni avvio dalla
   revisione "main". Una revisione nuova del modello cambierebbe i
   punteggi senza che nessuno se ne accorga. Revisioni locali di oggi:
   osiria `93b6993d59559da31b64bcc7bbb74ac1f7cda4b8`, MiniLM
   `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. Proposta: il motore le
   passa come `revision=` al caricamento (decisione 5). Vale anche per il
   modello di embedding dell'app di oggi, ma lì non si tocca in questa
   fermata.
6. **La domanda di B nella misura usa il titolo dell'ultimo frammento del
   bando** in ordine di id (`frammenti_della_copia`), non il titolo del
   bando in SQLite. Non è un difetto del motore: in B la domanda ripulita
   la costruisce chi chiama. Ma il filtro della fermata 2 partirà dal
   bando trovato da `dettaglio_bando`: il percorso dell'app in B non sarà
   quello misurato, come già detto nel piano del 19e (numero atteso tra 71
   e 77). Da tenere presente nella fermata 2.
7. **I contesti erano legati agli id della copia v0**: controllato oggi,
   il Chroma vero ha gli stessi id, testi, metadati e vettori di v0, quindi
   nessun problema ora. Ma un nuovo caricamento (ingest o carica_avvisi)
   cambierebbe gli id: per questo il file dei contesti si lega a (fonte,
   chunk_num, impronta del testo), non all'id.
8. **La strada 1 del piano del 19e (campo nei metadati del Chroma)
   contraddice la regola dell'interruttore spento** e la decisione 2
   (sezione 4). Scelgo la strada 2.

## 10. Decisioni che aspettano chi mantiene il progetto

1. **Copia o spostamento** (sezione 3): proposta copia, con lo script di
   misura congelato come riferimento e il doppione annotato in coda.
2. **Contesti: strada 2** (file a parte in locale, tabella a parte online)
   o strada 1 (campo nel Chroma, con copia di sicurezza e via). Con la
   strada 2: dove sta il file (proposta `data/db/contesti_avvisi.jsonl`,
   fuori dal repository con una riga in `.gitignore`), e se online i
   contesti stanno in una tabella a parte o in una colonna di `chunk` (si
   può decidere alla fermata 5).
3. **Un solo interruttore** (`ORDINE_C_LR`) per motore e riordino.
4. **Ordini di A rigenerati oggi** come riferimento di R1 (sezione 9,
   punto 1).
5. **Revisioni dei modelli fissate** nel motore (sezione 9, punto 5).
6. **Regola R2** per l'interruttore spento, con due esecuzioni del codice di
   prima.
7. **Fermata 5, già ora**: ricaricare tutta la tabella `chunk` dal Chroma
   con l'id di Chroma (sezione 9, punto 2); non cambia niente adesso, ma
   l'interfaccia dell'archivio si scrive così.
8. **Costo del "dopo"** delle venti domande sulle spese: stima da alzare
   dopo il "prima" a 0,976 $ (fuori da questa fermata, ma la stima va
   rifatta prima del lancio).

## Decisioni del 28/11/2026

Prese da chi mantiene il progetto sulle voci della sezione 10, prima della
sotto-fermata 1.0.

1. Copia e non spostamento: lo script di misura resta congelato e fa da
   riferimento; il doppione si annota in coda.
2. Contesti: strada 2, file a parte `data/db/contesti_avvisi.jsonl`, fuori
   dal repository con una riga in `.gitignore`; online tabella o colonna si
   decide alla fermata 5.
3. Un solo interruttore, `ORDINE_C_LR`.
4. Gli ordini di A rigenerati il 28/11/2026 dallo script congelato sono il
   riferimento di R1.
5. Revisioni dei due modelli fissate nel motore.
6. Regola R2 con due esecuzioni del codice di prima.
7. Ricarica dell'intera tabella dal Chroma alla fermata 5: si decide
   allora; l'interfaccia dell'archivio lo prevede da subito.
8. La stima del costo del "dopo" si rifà prima del lancio.
9. Regola in più per R1: se dopo due giri di correzione l'identità non è
   al 100%, ci si ferma e si porta l'elenco delle differenze a chi mantiene
   il progetto. La regola non si allenta senza una sua decisione.

## 11. Una soluzione migliore

Tre cambi rispetto al piano del 19e, già dentro le sezioni sopra, raccolti
qui perché sono scelte e non dettagli:

- **Lo script di misura come oracolo.** Copiare invece di spostare tiene
  fermo il codice che ha prodotto i numeri del 19d: l'identità diventa
  "il motore nuovo dà gli stessi ordini del codice che ha misurato", e non
  "il codice spostato dà gli stessi ordini di se stesso". Il doppione è il
  prezzo, ed è temporaneo.
- **L'identità a due gradini.** Prima il codice sugli stessi ingressi
  della misura (1.2), poi l'archivio (1.3), poi la catena (1.4): ogni
  differenza ha una sola causa possibile per gradino.
- **L'identità dell'archivio come uguaglianza esatta, senza modelli.**
  Se l'archivio dà gli stessi id, testi, metadati, vettori bit per bit e
  contesti, il motore deterministico dà gli stessi ordini. Alla fermata 5
  questo vuol dire: prima il controllo dell'allineamento (1187 righe, bit
  per bit, con l'id di Chroma), che si fa in secondi; solo dopo gli ordini
  online, che restano la rimisura di CLAUDE.md ma diventano una conferma
  e non la prima prova.
