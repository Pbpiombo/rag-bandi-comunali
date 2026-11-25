# Piano del resto del passo 19e

Scritto il 25/11/2026, solo come piano: nessun codice, nessuna misura,
nessuna chiamata al modello. Fonti lette: `docs/roadmap.md` (passo 19,
"Decisioni prese"), `docs/coda.md` ("Passo 19d", punti 7, 10 e 13, voci
19-21; "Disegno dell'app (22/11/2026)"; "Ordine delle voci intorno alla
chiamata"; "Passo 19e, rimedio 1"; "Taglio dei documenti secondo la
struttura del bando"; "Risposte vere sulla demo"; "Ricerca per nome e
parole comuni"), `docs/fatto.md` (19d), `CLAUDE.md` ("Mai"), e il codice
di `src/config.py`, `src/retrieval.py`, `src/pgstore.py`,
`src/recupero_documenti.py`, `src/chains/rag.py`, `app/app.py`,
`scripts/ingestione/carica_avvisi.py`, `scripts/diagnostica/genera_contesti.py`
e `data/processed/documenti_bandi.csv`.

Le decisioni che il piano chiede a chi mantiene il progetto sono raccolte
in fondo ("Decisioni che aspettano chi mantiene il progetto").

## 1. Da dove si parte

Letto dal codice e dai file il 25/11/2026:

- **Nell'app non c'è l'ordine c-LR.** Il recupero dell'app è l'ibrido
  senza riordinatore (densa più BM25 unite con RRF, `src/retrieval.py`;
  su Postgres densa più testo pieno, `src/pgstore.py`). Il riordinatore
  (osiria) e i contesti per frammento esistono solo nello script di
  misura (`scripts/diagnostica/misura_recupero_avvisi.py`) e nei file
  fuori dal repository (`..\dati-grezzi\prova\19d\contesto\contesti.jsonl`,
  871 righe). c-LR vuol dire: contesto davanti al testo nella ricerca
  lessicale (L) e nel riordinatore (R).
- **Il controllo di coincidenza del 24/11 (20 su 20) non prova che l'app
  sappia fare c-LR**: lo script `controllo_contesto_app.py` passa alla
  catena gli ordini già calcolati (`ordini_c-LR_24-11.json`) e controlla
  solo il contesto con i vicini.
- **Il filtro per bando non c'è.** L'unico restringimento è `avvolgi`
  (`src/recupero_documenti.py`), che lavora sui titoli dei documenti e
  sul campo `fonte`, non su `id_bando`. Nella misura del 19d la
  condizione B usa `cerca_nel_bando` con l'`id_bando` del fatto, cioè
  il bando giusto dato dalla misura.
- **I vicini sono nel codice, spenti** (`SPOSTAMENTI_VICINI = ()` in
  `src/config.py`); su Postgres manca il modo di prendere un frammento da
  (fonte, chunk_num), quindi restano spenti anche a interruttore acceso.
- **"Non lo trovo" c'è già nelle ISTRUZIONI**: "Non trovo la risposta
  nei documenti disponibili." più una riga su cosa servirebbe, con la
  regola sulle risposte parziali. Nella misura dei vicini, in V0 tutti
  e 10 i casi "vicino" dichiaravano di non trovare o di avere la
  risposta incompleta.
- **Avvisi**: 25 righe nel registro, 17 con uso "frammenti" (871
  frammenti nel Chroma locale, 1187 in tutto con gli altri documenti),
  8 "solo_registro". Gli allegati A1 e A5 degli apistici (dove stanno
  arnie, miele, alveari) sono "frammenti"; l'allegato 1B del bando Pmi
  50 mila (dove sta "caldaia") è "solo_registro".
- **Online**: l'app usa `RecuperoPostgres` (`app/app.py`); la tabella
  `chunk` non ha gli avvisi (CLAUDE.md, "Mai").

## 2. Differenze tra i documenti e l'elenco del compito

1. **(a) "ordine c-LR nell'app" non è un interruttore**: sono tre pezzi
   (riordinatore nell'app, contesti caricati accanto ai frammenti,
   ricerca lessicale sul testo con il contesto). È la tappa più grande.
2. **(a) "77 su 98" è un numero in B**, cioè con il bando giusto già
   dato. Nell'app il bando lo sceglie il router più `trova_bandi`. Senza
   filtro (A) c-LR fa 71 su 98 (`coda.md`, voce 20, "Accanto"). Il numero
   dell'app starà tra i due, e dipende da quante volte il filtro prende
   il bando giusto.
3. **(d) "non lo trovo" e i rimedi 2 e 3 non sono la stessa cosa nei
   documenti.** La condizione per mettere online gli avvisi è il "non lo
   trovo" (decisione 2 del 19d); i rimedi 2 (segnale di scarsa fiducia) e
   3 (secondo tentativo) sono altre voci del 19e, in quest'ordine dopo i
   vicini. Il "non lo trovo" esiste già come regola delle ISTRUZIONI:
   nel piano diventa una misura (tappa 4), non un pezzo da costruire.
   I rimedi 2, 3 e 5 vanno dopo la chiamata.
4. **(e) il rimedio 4 non è la scelta del bando incerto.** Nella roadmap
   e in `coda.md` ("Passo 19d", punto 7) il rimedio 4 propone tre
   **argomenti dentro il bando** quando scatta il segnale di scarsa
   fiducia, quindi dipende dal rimedio 2. La scelta quando il **bando** è
   incerto è un'altra voce: "Idea per le domande ambigue" (21/11) e la
   decisione del 25/11 ("se è incerta sul bando, mostra i candidati e
   chiede quale"). Il piano tiene la seconda (tappa 7) e lascia il
   rimedio 4 dopo la chiamata.
5. **(c) i vicini sono misurati solo sull'ordine c-LR in B**
   (`src/config.py`, commento all'interruttore): accenderli senza c-LR e
   senza filtro non è la configurazione misurata.
6. **(g) la strada C sui frammenti copre 12 bandi, non 42.** La misura
   della strada C usava il testo completo (pagine salvate per 37 bandi,
   avvisi per 13). Le pagine salvate non sono in nessun indice; i
   frammenti degli avvisi coprono 12 bandi (17 file "frammenti").
   Arnie, miele, alveari, banda, biblioteca, costumi stanno in file
   "frammenti" (da ricontrollare uno per uno prima di misurare);
   "caldaia" no.
7. **Il numero della nota di metodo**: nel compito "8 su 11"; in
   `coda.md` ("Strada C, misura senza modello") con "almeno 2
   occorrenze" sono 10 coppie, 8 pertinenti, 2 no. Nella riga nuova ho
   scritto 10 coppie e 8 pertinenti.
8. **Roadmap non allineata**: dice "19e e 22, in un ordine che si decide
   ora" e "Stato al 23 novembre"; l'ordine nuovo (resto del 19e, poi
   passo 20, poi incrocio) è solo in `coda.md`. Aggiornare la roadmap è
   un compito a parte, da approvare.

## 3. Le tappe

Numerazione delle tappe di questo piano, non dei passi della roadmap.
Corrispondenza con l'elenco del compito: tappa 1 = (a), 2 = (b), 3 = (c),
4 = (d), 5 = (f), 6a e 6b = (g), 7 = (e) nel senso del punto 4 qui sopra.

Ogni tappa ha il suo interruttore in `src/config.py`, spento finché la
regola di chiusura non passa, come `SPOSTAMENTI_VICINI` e
`ACCORCIA_CITAZIONI`. Ogni script di misura apre una copia del Chroma,
mai l'originale (incidente del 24/11).

### Tappa 6a. Ripiego anche quando si trovano solo bandi scaduti ("caldaia")

Viene prima delle altre perché è piccola, non tocca gli avvisi e può
andare online da sola.

- **Cosa cambia**: `src/database/interrogazioni_bandi.py`
  (`dettaglio_bando`): se tutti i bandi trovati sono scaduti, si esegue
  anche il ripiego sul testo unito tra i non scaduti, e il blocco dei
  dati porta entrambe le cose (lo scaduto come scaduto, i candidati come
  candidati). Test nuovo in `tests/` sul database in memoria, che fallisce
  senza la modifica. Interruttore `RIPIEGO_ANCHE_CON_SCADUTI`.
- **Dipende da**: niente. **Sblocca**: la tappa 6b, che userà lo stesso
  punto di ingresso.
- **Misura, senza modello**: i tre insiemi (36 parole comuni, 116
  titoli, 12 parametri salvati) più le 46 parole della strada C, prima e
  dopo, con gli script di `..\dati-grezzi\prova\parole-ricerca\` e
  `..\dati-grezzi\prova\risposte-vere\2026-11-25\`. Prima di misurare si
  elenca quali righe cadono nel caso "solo scaduti".
- **Regola di chiusura**: cambiano solo le righe del caso "solo scaduti";
  i 116 titoli e i 12 parametri restano identici; nessun bando scaduto
  diventa "trovato" non scaduto. Atteso per "caldaia": lo scaduto del
  2021 resta mostrato come scaduto; un candidato aperto solo se il testo
  unito lo contiene (l'allegato 1B è "solo_registro", quindi è possibile
  che il risultato onesto sia "nessun candidato aperto").
- **Cosa può andare storto**: un candidato estraneo accanto allo scaduto.
  Si torna indietro con l'interruttore.
- **Punto di arresto**: tabella prima e dopo delle righe cambiate, esito
  di ruff e pytest.

### Tappa 1. Ordine c-LR nell'app

- **Cosa cambia**:
  - `src/riordino.py` (nuovo): il riordinatore osiria caricato una volta,
    con la stessa preparazione delle coppie della misura (contesto
    davanti, tetto di 512 token, 30 candidati).
  - contesti accanto ai frammenti: un campo `contesto` nei metadati dei
    frammenti degli avvisi, caricato da `contesti.jsonl` con uno script
    nuovo in `scripts/ingestione/` (scrive nel Chroma vero: copia di
    sicurezza prima, in `..\dati-grezzi\backup\`). I 36 frammenti con il
    contesto scartato restano senza, come nella misura.
  - `src/retrieval.py`: la ricerca lessicale sul testo con il contesto
    davanti (`testo_lessicale` della misura, spostata in `src/` con
    l'aggiornamento di chi la importa); il testo citato e verificato
    resta quello pulito.
  - `src/chains/rag.py` (`recupera`): candidati, poi riordino, poi k=10.
  - `src/config.py`: `ORDINE_C_LR = False`, `CANDIDATI_RIORDINO = 30`.
- **Dipende da**: la decisione sul motore online (sezione 5,
  "Cose che non tornano", punto 1). **Sblocca**: tappe 2, 3 e 5.
- **Misura, senza modello**: identità con gli ordini salvati della
  misura del 19d (`..\dati-grezzi\prova\19d\contesto\misure\`): il
  percorso dell'app, su una copia del Chroma, deve dare gli stessi primi
  10 frammenti nello stesso ordine, in A e in B (in B con l'`id_bando`
  del fatto passato a mano), sulle quattro serie (97 e 98 dei fogli, 92 e
  49 a mano). Non si sceglie niente: le serie spese servono solo come
  controllo di uguaglianza.
- **Regola di chiusura**: 100% degli ordini identici; quindi in B k=10
  77 su 98 sul controllo e 83 su 97 sulla taratura, in A 71 su 98. Ogni
  differenza si spiega una per una (per esempio parità di punteggio); se
  ne resta una non spiegata, non chiude. Con l'interruttore spento,
  contesto e frammenti identici al codice di oggi sulle 22 domande del
  controllo del 24/11. Tempo del riordino annotato (mediana attesa
  intorno ai 5,3 secondi in locale), senza veto.
- **Cosa può andare storto**: versioni diverse della libreria che
  cambiano i punteggi; contesti legati agli id dei frammenti della copia
  v0 che non corrispondono più al Chroma vero (si controlla prima, come
  il 24/11 per i testi). Interruttore `ORDINE_C_LR`.
- **Punto di arresto**: tabella delle identità per serie e condizione,
  tempi, esito di ruff e pytest.

### Tappa 2. Filtro per bando quando il bando è noto

- **Cosa cambia**: `src/chains/rag.py` (`prepara`: l'`id_bando` arriva
  dall'esito di `dettaglio_bando` al recupero), `src/recupero_documenti.py`
  (ricerca ristretta a un `id_bando`), `src/retrieval.py` (filtro su
  `id_bando` nella densa e nella lessicale, con i pesi BM25 calcolati su
  tutto l'indice come in `cerca_nel_bando`), `src/config.py`
  (`FILTRO_PER_BANDO = False`). Regole: un solo bando trovato per nome e
  con frammenti: filtro; due o tre: nessun filtro fino alla tappa 7;
  nessuno, o bando senza frammenti: ricerca in tutto, come oggi.
- **Dipende da**: tappa 1 (il 77 su 98 è c-LR in B). **Sblocca**: 3, 5, 7.
- **Misura senza modello**: sulle decisioni del router già salvate (226
  risposte dei lotti 1-3 e delle prove del 19e e della sospensione, più
  le 20 vere del 25/11), quale filtro prenderebbe l'app; lettura a mano
  dei casi filtrati.
- **Misura con il modello, solo router**: le 98 domande dei fogli e le
  49 a mano del controllo, per vedere se il bando del filtro è quello del
  fatto. Lancio di chi mantiene il progetto, con uno script da scrivere
  in questa tappa (in `..\dati-grezzi\prova\19e\`), con `--stima` e
  `--tetto-dollari`. Costo: il router è una chiamata corta; come tetto
  superiore, una risposta intera misurata il 24/11 costava circa 0,04 $,
  quindi 147 domande stanno sotto i 6 $, quasi certamente molto meno.
- **Regola di chiusura**: zero filtri su un bando sbagliato (un filtro
  sbagliato toglie tutti i frammenti giusti: errore grave); quota dei
  filtrati riportata senza soglia; numero dei fatti trovati con il
  filtro dell'app riportato come descrizione, atteso tra 71 e 77 su 98.
- **Cosa può andare storto**: i due bandi PMI con parole del titolo in
  comune (decreti 13512 e 9506); gli apistici in quattro parti (il filtro
  tiene tutte le parti; la domanda sull'azione resta, caso 70).
  Interruttore `FILTRO_PER_BANDO`.
- **Punto di arresto**: casi filtrati letti a mano, tabella del router
  sulle 147 domande, esito di ruff e pytest.

### Tappa 3. Vicini accesi

- **Cosa cambia**: `SPOSTAMENTI_VICINI = (-1, 1)`; su Postgres, se si
  resta sul motore di oggi, una query per prendere più frammenti da
  (fonte, chunk_num) in una sola chiamata, in `src/pgstore.py`.
- **Dipende da**: 1 e 2. **Sblocca**: 5.
- **Misura senza modello**: il controllo di coincidenza del 24/11 rifatto
  con gli ordini calcolati dall'app, non passati da file: 20 su 20.
- **Regola di chiusura**: 20 su 20 contesti identici a quelli delle
  risposte V1; testo dei frammenti non oltre il doppio (misurato 1,90).
- **Cosa può andare storto**: niente di nuovo rispetto al 24/11; si
  spegne con l'interruttore.
- **Punto di arresto**: esito del confronto.

### Tappa 4. "Non lo trovo", misurato

- **Cosa cambia**: niente nel codice, se la misura passa.
- **Dipende da**: 1, 2, 3. **Sblocca**: 5 (è la seconda condizione di
  CLAUDE.md).
- **Materiale**: le domande candidate sulle pagine di domande frequenti
  di Cultura e Sport Missione Comune
  (`..\dati-grezzi\manuali\2026-11-24\domande_candidate_2026-11-24.xlsx`),
  mai usate per misurare: alcune hanno la risposta solo nelle domande
  frequenti, non nell'avviso, e lì la risposta giusta è "non lo trovo" o
  una risposta parziale dichiarata. Si scelgono 20 domande con una
  regola scritta prima: 10 con la risposta nei frammenti passati al
  modello, 10 senza (deciso senza modello, guardando i frammenti).
- **Misura con il modello**: lancio di chi mantiene il progetto, con la
  catena dell'app su Chroma e le tre tappe accese; circa 0,84 $ per 20
  domande (costo vero di V1, 24/11). Lettura alla cieca come il 24/11.
- **Regola di chiusura**: sulle 10 senza risposta nei frammenti, nessuna
  risposta sbagliata data con sicurezza (una sola: si annota e si
  rilancia; due: non chiude); sulle 10 con la risposta, almeno 8 giuste
  con la fonte giusta.
- **Se non passa**: il rimedio 2 (segnale di scarsa fiducia) diventa
  condizione per la tappa 5, e la tappa 5 slitta dopo la chiamata.
- **Punto di arresto**: rapporto dei giudizi.

### Tappa 5. Avvisi nell'app online

- **Cosa cambia**: `scripts/ingestione/carica_avvisi.py`, opzione nuova
  per Postgres: copia dal Chroma testi, metadati (con `contesto`) e
  vettori, così i vettori sono gli stessi bit; prima toglie solo le righe
  degli avvisi (quelle con il metadato `sha256`), quindi si può
  rilanciare. Opzione di controllo dell'allineamento: confronta senza
  scrivere l'insieme (fonte, chunk_num, impronta del testo, impronta del
  contesto) tra Chroma e Postgres. `app/app.py` e `src/pgstore.py` solo
  secondo la decisione sul motore (sezione 5, punto 1).
- **Dipende da**: 1-4 chiusi e il via esplicito di chi mantiene il
  progetto (CLAUDE.md, "Mai"). **Sblocca**: 6b online, 7 con il filtro.
- **Misura**: identità degli ordini online contro quelli locali sulle 98
  e 49 domande del controllo (lancio di chi mantiene il progetto, con la
  rete; nessun modello di linguaggio); poi le 20 domande vere del 25/11
  rilanciate da chi mantiene il progetto sulla demo, lette a mano prima
  e dopo; tempi e memoria su Streamlit Cloud (sezione 4, domanda 4).
- **Regola di chiusura**: allineamento 1187 su 1187 righe uguali; ordini
  identici al locale (con il motore in memoria) o una regola nuova
  scritta prima della misura (con il motore di Postgres); sulle 20 vere
  nessuna risposta peggiorata e nessun dato sbagliato nuovo; tempo del
  recupero con il riordino sotto i 10 secondi di mediana su 10 domande;
  nessun riavvio dell'app per memoria su 20 domande di fila.
- **Come si torna indietro**: copia della tabella `chunk` prima del
  caricamento, in `..\dati-grezzi\backup\`; togliere gli avvisi è una
  sola cancellazione delle righe con `sha256`; gli interruttori delle
  tappe 1-3 tornano spenti con un riavvio.
- **Punto di arresto**: prima del caricamento, per il via; dopo, con
  allineamento, identità, tempi, memoria e la lettura delle 20 vere.

### Tappa 6b. Ricerca lessicale per bando (strada C)

- **Cosa cambia**: un indice lessicale a parte, con lo stemmer italiano
  (Snowball), sui frammenti degli avvisi, raggruppato per `id_bando`
  (punteggio del bando dai suoi frammenti migliori), usato solo nel
  ripiego di `dettaglio_bando` e solo tra i non scaduti. Il risultato
  usa il formato dei candidati già esistente (`trovato=False` e il
  motivo, "nell'avviso compare 'arnie' (allegato A1, pag. 4)"), così
  ISTRUZIONI non cambia. È un indice a parte: l'indice lessicale del
  recupero non si tocca, perché è quello misurato (tappa 1). File:
  `src/` (modulo nuovo o `src/retrieval.py`), `src/chains/rag.py`
  (le interrogazioni ricevono solo la connessione SQLite: il ripiego sui
  frammenti va chiamato da `prepara`), `src/config.py`,
  `requirements.txt` se serve una libreria per lo stemmer (da
  approvare).
- **Dipende da**: 6a; online, da 5 (arnie e miele sono negli allegati
  A1 e A5). **Sblocca**: 7 con candidati migliori.
- **Misura senza modello**: le 46 parole e i tre insiemi, prima e dopo.
  Prima di misurare si scrive, dal registro, quali delle 8 coppie
  pertinenti della strada C vengono da un file "frammenti".
- **Regola di chiusura**: i tre insiemi identici (il ripiego entra solo
  quando niente trova); per le parole che oggi non trovano niente, il
  bando pertinente tra i primi 3 candidati per almeno 6 delle coppie
  pertinenti che stanno nei frammenti (attese: arnie, miele, alveari,
  banda, biblioteca, costumi); al primo posto un bando non pertinente al
  massimo 2 volte. Nessuna soglia di occorrenze: si ordina, non si taglia.
- **Cosa può andare storto**: parole citate per escluderle (limite
  noto, voce del 25/11); sigle ("API"). Interruttore.
- **Punto di arresto**: tabella parola per parola.

### Tappa 7. Scelta del bando quando è incerto

- **Cosa cambia**: `app/app.py`: quando `dettaglio_bando` dà due o tre
  candidati (titoli simili o ripiego), l'app li mostra con "nessuno di
  questi"; la scelta va nello stato della sessione e diventa il filtro
  della tappa 2; la domanda si ripete. `src/chains/rag.py`, per passare
  il bando scelto. Test con AppTest. Interruttore.
- **Dipende da**: 2 (e 6b per candidati migliori). Può andare online
  dopo 6a anche senza avvisi, solo come scelta del bando.
- **Misura**: AppTest sul comportamento; lettura a mano sulle 46 parole
  e sulle 20 domande vere: ogni caso con due o tre candidati mostra la
  scelta, nessun caso con un solo bando trovato la mostra.
- **Punto di arresto**: esito dei test e una decina di schermate o
  testi letti.

## 4. Risposte alle domande

**1. Ordine e perché.** 6a, 1, 2, 3, 4, 5, 6b, 7. La 6a per prima
perché è piccola e indipendente. Poi 1-4 nell'ordine delle dipendenze:
il 77 su 98 vale con c-LR e il bando dato (1 e 2), i vicini sono misurati
solo lì (3), il "non lo trovo" si misura sulla catena finale (4). La 5
viene dopo, perché CLAUDE.md la condiziona a filtro, "non lo trovo",
rimisura e via esplicito. La 6b online richiede gli avvisi online. La 7
per ultima, perché è la più costosa da fare bene nell'interfaccia.
Online da sole: 6a; 7 nella versione senza avvisi. Solo insieme: 1, 2,
3 e 4 non hanno effetto online senza la 5 (i contesti esistono solo per
gli avvisi), e la 5 non può partire senza di loro.

**2. Cosa si misura davvero.** Forte: le identità senza modello (tappe 1,
3, 5): le serie spese servono a controllare che l'app riproduca la
misura, non a scegliere. Debole: quanto il filtro prende il bando giusto
su domande vere; il "non lo trovo" su 20 domande; il beneficio sulle
spese ammissibili; la scelta guidata. Da leggere a mano: le 20 domande
vere del 25/11 rilanciate da chi mantiene il progetto prima e dopo la
tappa 5; le domande sulle pagine di domande frequenti (tappa 4). Proposta
in più: prima della tappa 5, una ventina di domande nuove sulle spese
ammissibili dei 12 bandi con avvisi, scritte a mano e messe da parte
senza leggere le risposte: è l'unica misura nuova del difetto 1.

**3. Avvisi online.** CLAUDE.md: online solo nel 19e, insieme al filtro
per bando e al "non lo trovo", dopo la rimisura su Postgres e con il via
esplicito. Da decidere: se l'identità con il locale vale come rimisura
(sezione 5, punto 1); se i contesti, testo scritto da un modello e mai
mostrato, possono stare su Postgres. Spazio, stima non misurata: per
riga circa 1,5 kB di testo, 1,5 kB di vettore (384 numeri), 0,5-1 kB di
metadati e contesto, più l'indice; per 871 frammenti circa 5 MB. Il
Chroma locale intero (1187 frammenti) occupa 22 MB su disco. Il limite
del database nel piano gratuito di Supabase è da rileggere sulla pagina
ufficiale (in `coda.md` sono annotati solo pausa e memoria di
Streamlit): con 500 MB, che è il valore che ricordo ma non ho
verificato, oggi c'è margine; a mille bandi con 50 frammenti l'uno
(circa 250 MB) no. Allineamento: il caricamento copia dal Chroma, e il
controllo dell'allineamento confronta le impronte; si lancia dopo ogni
caricamento. Da zero: cancellazione delle righe degli avvisi e nuovo
caricamento; per tutto l'archivio, `TRUNCATE chunk`, `ingest_tutti` e
poi gli avvisi, sempre dopo una copia della tabella.

**4. Tempi e memoria su Streamlit Cloud.** Sappiamo: riordino c-LR in B
sul PC di chi mantiene il progetto, mediana 5,3 s e massimo 7,2 s sui
fogli, 5,6 e 7,2 a mano (voce 20); 4-5 s è il numero di c-0. Non
sappiamo: i tempi su Streamlit Cloud (processore condiviso), i tempi in A
(30 candidati da tutto l'archivio), la memoria di oggi dell'app (modello
di embedding già caricato) e quanto aggiunge il riordinatore; Streamlit
dà da 690 MB a 2,7 GB. Da misurare nella tappa 5: tempo del recupero e
del riordino stampato nel registro dell'app su 10 domande, memoria
occupata dopo il caricamento dei modelli, 20 domande di fila senza
riavvio. Il riordinatore online si scarica da Hugging Face a ogni avvio
(e HF_TOKEN non è ancora nei secrets).

**5. Cosa sostituirà il taglio a livelli.** I vicini (diventano i
fratelli sotto lo stesso genitore); i contesti per frammento (si
rigenerano dopo il nuovo taglio, a pagamento); i 512 token del
riordinatore con il contesto davanti; gli ordini salvati del 19d (non
varranno più). Restano: filtro per bando, caricamento su Postgres con il
controllo dell'allineamento, "non lo trovo", ricerca per bando della
strada C (cambia solo l'indice), scelta del bando. Quindi: nessun
avviso nuovo e nessuna generazione di contesti nuova prima del taglio a
livelli; nella tappa 1 si caricano solo gli 871 contesti esistenti; si
investe nel caricamento ripetibile (tappa 5), che serve anche dopo.

**6. Giri di lavoro.** 6a: 1. Tappa 1: 2-3. Tappa 2: 1-2 più il lancio
del router. Tappa 3: mezzo. Tappa 4: 1 più la lettura. Tappa 5: 2-3.
Tappa 6b: 1-2. Tappa 7: 2. Totale 10-15 giri. Rischio di triplicare:
tappa 1 (riordinatore e contesti nell'app, come nel 19d), tappa 5 (prima
volta online con modelli nuovi: memoria, rete, Supabase), tappa 7
(interfaccia e stato della sessione). Basso nelle tappe 3, 4 e 6a.

**7. Perimetro ridotto prima della chiamata.** 6a, 1, 2 (solo bando
trovato per nome, nessuna scelta), 3, 4, 5. È l'unica strada che
attacca il difetto 1 (profondità sulle spese ammissibili), che nelle 20
risposte vere pesa di più (5 risposte oneste ma generiche) del difetto 2.
Del difetto 2 entra solo la 6a; arnie e miele restano un limite
dichiarato con la causa misurata. Non si accorcia togliendo la tappa 1:
la configurazione decisa per gli avvisi è c-LR, e i vicini sono misurati
solo lì. Se non basta il tempo neanche per questo, prima della chiamata
va solo la 6a, e gli avvisi si mostrano al consulente pilota in locale.
Il passo 20 e l'incrocio delle ricerche, nell'ordine nuovo, vengono
dopo: con il perimetro ridotto è probabile che il passo 20 non entri
prima della chiamata.

## 5. Cose che non tornano

1. **Il motore online non è quello misurato.** Su Postgres la ricerca
   per parole è il testo pieno con le parole in OR e `ts_rank_cd`, non
   BM25, e la ricerca per significato passa da un indice HNSW
   approssimato; la misura del 19d usa BM25 e la ricerca esatta. Il 77
   su 98 non si trasferisce.
   - Alternativa A, portare c-LR su Postgres e rimisurare: scala meglio;
     ma due motori da mantenere, numeri locali che non valgono online,
     una regola nuova da scrivere e una misura nuova con la rete.
   - Alternativa B, Postgres solo come archivio: all'avvio l'app legge
     dalla tabella testi, metadati e vettori e cerca in memoria con lo
     stesso codice del locale (BM25 e prodotto scalare esatto, come la
     misura): la rimisura diventa un controllo di identità, i vicini non
     hanno bisogno di query nuove, il filtro è lo stesso. Contro: memoria
     e tempo di avvio crescono con l'archivio (oggi pochi MB; a 50.000
     frammenti circa 150 MB) e non è la via che il README descrive.
   - Alternativa C, tenere il motore di Postgres e accettare un numero
     nuovo: meno codice, ma un numero non confrontabile con il 19d.
   - Sceglierei B, fino al taglio a livelli o a qualche migliaio di
     frammenti. Serve il via di chi mantiene il progetto, anche per dire
     se l'identità vale come la "rimisura su Postgres" di CLAUDE.md.
2. **Il filtro dipende dal riconoscimento del bando**, che oggi non
   trova i bandi descritti con parole comuni: proprio i casi della strada
   C restano senza filtro. Alternative: filtro solo con un bando trovato
   per nome (sicuro, copre meno); filtro anche sul primo candidato del
   ripiego (copre di più, rischia il filtro sbagliato, errore grave);
   filtro dalla scelta dell'utente (tappa 7). Sceglierei la prima subito
   e la terza con la tappa 7; mai il filtro su un candidato non scelto.
3. **La strada C sui frammenti non vede le pagine salvate**, e "caldaia"
   sta in un file "solo_registro". Alternative: frammenti degli avvisi
   soli (subito, 12 bandi); aggiungere il testo delle pagine salvate
   come documenti (copre 37 bandi in più, ma è altro testo online e un
   caricamento in più, da decidere); caricare come frammenti anche gli
   allegati "solo_registro" (cambia il registro, con ricadute sulla
   misura del 19d). Sceglierei la prima prima della chiamata e le pagine
   dopo, con una decisione.
4. **I contesti sono legati agli 871 frammenti della copia v0** e scritti
   da un modello. Un avviso nuovo o un nuovo taglio li rende da
   rigenerare. Alternative: caricare gli 871 e fermare gli avvisi nuovi
   fino al taglio a livelli; oppure generare i contesti a ogni avviso
   nuovo con lo script esistente (costo piccolo, ma lavoro buttato al
   taglio). Sceglierei la prima.
5. **Memoria su Streamlit**: oggi si installano anche le librerie CUDA
   (circa 2,5 GB, voce "App online più leggera"), e il riordinatore
   aggiunge un secondo modello. Se l'app supera la memoria, la demo cade.
   Alternative: misurare nella tappa 5 e tornare indietro se serve;
   oppure fare prima "App online più leggera" (torch solo per processore).
   Sceglierei di misurare prima di caricare: avvio dell'app con il
   riordinatore e senza avvisi, a interruttori spenti tranne il modello
   caricato.
6. **Licenza e scaricamento del riordinatore** online: nel 19d è stato
   scaricato una volta come eccezione alla rete; online si scarica a ogni
   avvio. Da verificare la licenza del modello osiria prima della tappa
   5 (verifica sulla pagina del modello, non fatta).
7. **Il rimedio 4 e il passo 22**: la scheda del bando, quando c'è,
   sostituisce frasi come "non trovo l'elenco delle spese ammissibili"
   (regola del 25/11). L'ordine tra il 22 e il filtro resta non deciso
   in roadmap.

## 6. Un'impostazione migliore

Invece di sette tappe con una sola uscita online alla fine, due rilasci:

- **Rilascio 1, subito**: la 6a, online da sola.
- **Rilascio 2, un pacchetto**: "un solo motore, due archivi"
  (alternativa B del punto 1): si sposta in `src/` il motore della misura
  (BM25, prodotto scalare esatto, contesto, riordinatore, filtro per
  `id_bando`, vicini), che legge i frammenti dal Chroma in locale e da
  Postgres online. Le tappe 1, 2, 3 e 5 diventano lo stesso lavoro, e
  la loro misura diventa una sola prova di identità con gli ordini del
  19d, in locale e online. La tappa 4 resta la sola misura con il
  modello prima di accendere. Rischio: è un cambio più grande in un solo
  giro; si contiene tenendo il motore attuale dietro un interruttore
  finché l'identità non passa.

## 7. Decisioni che aspettano chi mantiene il progetto

1. Motore online: A, B o C (sezione 5, punto 1), e se l'identità con il
   locale vale come rimisura per CLAUDE.md.
2. Contesti scritti da un modello su Postgres: sì o no.
3. Ordine delle tappe e perimetro prima della chiamata (sezione 4,
   domande 1 e 7); in particolare se il passo 20 può scendere dopo la
   chiamata.
4. Filtro solo con bando trovato per nome, per ora (sezione 5, punto 2).
5. Strada C sui soli frammenti prima della chiamata; pagine salvate dopo
   (punto 3).
6. Niente avvisi nuovi né contesti nuovi prima del taglio a livelli
   (punto 4).
7. Prima la prova di memoria su Streamlit o prima "App online più
   leggera" (punto 5).
8. Le venti domande nuove sulle spese ammissibili, scritte a mano prima
   della tappa 5 (sezione 4, domanda 2).
9. Libreria per lo stemmer in `requirements.txt` (tappa 6b).
10. Aggiornamento della roadmap con l'ordine nuovo, come compito a parte.

## 8. Decisioni del 25/11/2026

Decise da chi mantiene il progetto il 25/11/2026, dopo la lettura di
questo piano. Le sezioni 1-7 restano come erano: dove questa sezione le
contraddice, vale questa.

**Contesto nuovo.** La chiamata con il consulente pilota della prima
settimana di dicembre serve a raccogliere informazioni (cosa chiede, da
quali fonti), non a mostrare una demo finita. L'obiettivo è un'app che
il consulente pilota possa provare tra gennaio e febbraio 2027, con
buone fonti e buona qualità di risposta. Quindi il 19e si fa intero e
bene, senza perimetro ridotto e senza scadenza: la sezione 4, domanda 7,
è superata.

### Le decisioni

1. **Motore online: alternativa B, nella forma della sezione 6** (un
   solo motore, due archivi). L'identità degli ordini con il locale vale
   come la "rimisura su Postgres" di CLAUDE.md. È una soluzione
   provvisoria fino al taglio a livelli (passo 24) o a qualche migliaio
   di frammenti: allora si rivaluta l'alternativa A. Testo proposto per
   CLAUDE.md qui sotto, da approvare; CLAUDE.md non è stato modificato.
2. **Contesti scritti dal modello su Postgres: sì**, con origine
   "modello", usati solo per cercare (ricerca per parole e
   riordinatore), mai citati né mostrati; il verificatore lavora solo
   sul testo pulito. Un test lo fissa: si scrive nella fermata 1, quando
   il campo `contesto` entra nel codice, perché un test scritto oggi non
   potrebbe fallire senza la modifica. Il test controlla che, con un
   frammento che ha nel contesto un numero assente dal testo, il numero
   non compaia nel contesto dato al modello di risposta, né nel testo
   dato al verificatore, né nelle fonti mostrate.
3. **19e intero, nessun perimetro ridotto.** Il passo 20 viene dopo il
   19e.
4. **Filtro solo con un bando trovato per nome**, mai su un candidato
   non scelto dall'utente. Con la tappa 7, anche il bando scelto
   dall'utente.
5. **Strada C sui frammenti degli avvisi.** Le pagine salvate dopo, con
   una decisione a parte.
6. **Nessun avviso nuovo e nessun contesto nuovo prima del taglio a
   livelli.**
7. **Prova di memoria su Streamlit subito dopo la 6a**, prima del
   resto; torch solo per processore da fare comunque. Progetto della
   prova qui sotto.
8. **Venti domande nuove sulle spese ammissibili: sì.** Regola di
   divisione qui sotto, correzione b.
9. **Libreria per lo stemmer**: si decide alla 6b.
10. **Roadmap**: aggiornata il 25/11/2026 con l'ordine nuovo.

### Verifiche sulle pagine ufficiali (25/11/2026)

Fatte da chi mantiene il progetto il 25/11/2026, riportate qui:

- il riordinatore osiria è sotto licenza MIT (scheda del modello su
  Hugging Face). Il progetto usa la versione L12:
  `osiria/minilm-l12-h384-italian-cross-encoder` (`RIORDINATORI` e
  `RIORDINATORE_PICCOLO` in `scripts/diagnostica/misura_recupero_avvisi.py`);
  nella cache locale occupa 129 MB;
- il piano gratuito di Supabase dà 500 MB di database per progetto e 5
  GB di traffico in uscita. Questo sostituisce il "500 MB che ricordo ma
  non ho verificato" della sezione 4, domanda 3.

### Traffico in uscita per avvio, con il motore in memoria

Stima, non misurata. A ogni avvio l'app legge tutta la tabella `chunk`:
testo (circa 1,5 kB), metadati (circa 0,5 kB), contesto per gli avvisi
(circa 1 kB) e vettore di 384 numeri. Il vettore pesa circa 1,5 kB in
forma binaria, circa 4 kB se arriva come testo (il formato predefinito
di psycopg per i risultati). Per 1187 righe: da 4 a 8 MB per avvio. Con
5 GB al mese sono da 600 a 1200 avvii al mese, più le altre
interrogazioni. Un avvio c'è a ogni riattivazione dopo la pausa di 12
ore, a ogni riavvio dal pannello e a ogni nuovo contenitore. Da misurare
nella prova di memoria (sotto) e di nuovo nella fermata 5: byte letti
per avvio e numero di avvii in una settimana. Accorgimento già previsto:
leggere i vettori in forma binaria.

### Testo proposto per CLAUDE.md, sezione "Mai"

Voce di oggi:

> - Caricare gli avvisi dei bandi su Postgres (l'app online) fuori dal passo
>   19e. Il 19d è chiuso sotto soglia (23/11/2026): gli avvisi vanno online
>   solo insieme al filtro per bando e al "non lo trovo", dopo la rimisura
>   su Postgres prevista nel 19e e con il via esplicito di chi mantiene il
>   progetto. Fino ad allora stanno solo nel Chroma locale.

Voce proposta:

> - Caricare gli avvisi dei bandi su Postgres (l'app online) fuori dal passo
>   19e. Il 19d è chiuso sotto soglia (23/11/2026): gli avvisi vanno online
>   solo insieme al filtro per bando e al "non lo trovo", dopo la rimisura
>   su Postgres prevista nel 19e e con il via esplicito di chi mantiene il
>   progetto. Fino ad allora stanno solo nel Chroma locale. Con il motore in
>   memoria (un solo motore, due archivi: `docs/piano-19e.md`, "Decisioni
>   del 25/11/2026") la rimisura è l'identità degli ordini: l'app online
>   deve dare, sulle serie del 19d, gli stessi primi 10 frammenti nello
>   stesso ordine dell'app in locale. Se cambia il motore (taglio a
>   livelli, ricerca fatta da Postgres), serve una rimisura nuova con una
>   regola scritta prima.

Voce nuova proposta, nella sezione "Principi del progetto":

> - I contesti per frammento scritti da un modello servono solo a cercare:
>   non si citano, non si mostrano e non arrivano al verificatore, che
>   lavora sul testo pulito del frammento.

### Correzione a: il rilascio 2 in fermate

Sostituisce l'elenco delle tappe 1, 2, 3 e 5 della sezione 3 e il
rilascio 2 della sezione 6. Ordine complessivo del resto del 19e:

0. **Tappa 6a**: fatta il 25/11/2026 (sezione 9).
1. **Prova di memoria su Streamlit e torch solo per processore** (sotto).
   Arresto: tabella di memoria, tempi e traffico; proposta della modifica
   a `requirements.txt`.
2. **Le venti domande sulle spese ammissibili**, scritte e messe da
   parte prima di cambiare il motore (correzione b), con la registrazione
   "prima" sull'app di oggi, lanciata da chi mantiene il progetto (circa
   0,04 $ a domanda, dal costo vero di V0 e V1 del 24/11: circa 0,80 $).
   Arresto: domande salvate, risposte non lette fino alla fermata 5.
3. **Fermata 1: motore della misura in `src/`.** BM25 e prodotto
   scalare esatto in memoria, contesto davanti al testo nella ricerca per
   parole, riordinatore osiria L12 su 30 candidati, k=10; letto dal
   Chroma in locale. Dietro un interruttore; spento, l'app resta quella
   di oggi. Sotto-fermata, correzione d: prima di scrivere il campo
   `contesto` nel Chroma vero, copia di sicurezza in
   `..\dati-grezzi\backup\` e **fermata per il via** di chi mantiene il
   progetto. Regola di chiusura: quella della tappa 1 (identità al 100%
   con gli ordini salvati del 19d sulle quattro serie, in A e in B;
   interruttore spento identico al codice di oggi sulle 22 domande del
   24/11); più il test della decisione 2. Arresto: tabella delle
   identità, tempi, ruff e pytest.
4. **Fermata 2: filtro per bando** (solo bando trovato per nome, con
   frammenti). Regola di chiusura della tappa 2: zero filtri su un bando
   sbagliato, sulle decisioni del router salvate e sul lancio del solo
   router per le 147 domande del controllo (lanciato da chi mantiene il
   progetto, con `--stima` e `--tetto-dollari`, tetto superiore 6 $).
   Arresto: casi filtrati letti a mano, tabella del router.
5. **Fermata 3: vicini accesi.** Regola di chiusura della tappa 3 (20
   su 20 contesti identici a V1, con gli ordini calcolati dall'app;
   testo dei frammenti non oltre il doppio). Con il motore in memoria
   non serve una query nuova su Postgres. Arresto: esito del confronto.
6. **Fermata 4: misura del "non lo trovo"** sulle domande delle pagine
   di domande frequenti (correzione b), con la regola della tappa 4.
   Arresto: rapporto dei giudizi. Se non passa, il rimedio 2 diventa
   condizione della fermata 5.
7. **Fermata 5: online.** Copia della tabella `chunk`; **fermata per il
   via** prima del caricamento; caricamento degli avvisi con i contesti
   (origine "modello") copiati dal Chroma; controllo dell'allineamento;
   identità degli ordini online contro locale sulle 98 e 49 domande del
   controllo; traffico per avvio; registrazione "dopo" delle venti
   domande sulle spese ammissibili e delle 20 domande vere del 25/11,
   lette a mano prima e dopo. Regola di chiusura: quella della tappa 5,
   con l'identità al 100%; sulle venti domande sulle spese nessun dato
   sbagliato nuovo, e il numero delle risposte giuste prima e dopo
   riportato senza soglia (è la prima misura del difetto 1, non una
   decisione). Arresto: dopo il caricamento, con tutti i numeri. Poi il
   README (correzione c).
8. **Tappa 6b** e **tappa 7**, come nella sezione 3.

### Correzione b: le domande delle pagine di domande frequenti

Il file `..\dati-grezzi\manuali\2026-11-24\domande_candidate_2026-11-24.xlsx`
ha 171 domande. Per scrivere questa regola sono state lette solo la
scheda "leggimi" e le colonne di classificazione (origine, bando,
chi_parla, tema, giudizio, scelta_finale), non le domande, i motivi, le
fonti e le risposte. La colonna "scelta_finale" è vuota, e per il
foglio "le risposte non sono ancora state cercate negli avvisi".

Regola, decisa prima di aprire le domande; ogni domanda va al più in un
uso:

1. **Tappa 4 ("non lo trovo")**: tutte e sole le righe con origine "FAQ
   ufficiale": **44** (24 Sport Missione Comune, 20 Cultura Missione
   Comune). Sono le sole con una risposta ufficiale, che serve a sapere
   se la risposta sta nell'avviso. Delle 44 se ne usano 20, con la
   regola della tappa 4 (10 con la risposta nei frammenti passati al
   modello, 10 senza), prese nell'ordine della colonna "n"; le altre 24
   restano per il passo 25.
2. **Venti domande sulle spese ammissibili**: le righe con origine
   diversa da "FAQ ufficiale", tema nella famiglia delle spese ("spese",
   "cosa si può pagare", anche con la nota sulla risposta assente, "cosa
   si può comprare", "spese ammissibili", "acquisti", "beneficiari/spese"),
   giudizio "tenere" e bando tra i 12 con avvisi caricati come frammenti:
   **14**. Le altre 6 le scrive a mano chi mantiene il progetto, sugli
   stessi 12 bandi, prima di guardare le 14. Con giudizio "riserva" ce ne
   sono altre 3: non entrano.
3. **Tutte le altre righe** (113: le 127 non FAQ meno le 14) non entrano
   in nessuna delle due misure e restano per il passo 25.

Limite: le 14 sono scritte o trovate da modelli, quindi più vicine
allo stile dei contesti (il rischio della voce 9 del punto 7 del 19d).
Vedi la sezione 10.

### Correzione c: il README

Con il motore in memoria il README non descrive più il sistema (tabella
"`RecuperoIbrido` / `RecuperoPostgres`", ricerca lessicale "full-text
italiano di Postgres", sezione su Postgres con pgvector). Va aggiornato
quando il rilascio 2 è online, nella fermata 5, con il motivo della
scelta: le misure del 19d valgono online solo se online gira lo stesso
motore; Postgres fa da archivio; si rivaluta la ricerca fatta da
Postgres al taglio a livelli o oltre qualche migliaio di frammenti.

### Correzione d: il campo contesto nel Chroma vero

Prima di scrivere il campo `contesto` nel Chroma vero: copia di
sicurezza della cartella `data\db\chroma` in `..\dati-grezzi\backup\`,
e fermata per il via di chi mantiene il progetto (fermata 1 qui sopra).

### Prova di memoria su Streamlit, senza toccare la demo pubblica

Scopo: sapere prima di scrivere il motore se l'app ci sta con due
modelli (embedding e riordinatore), quanto tempo prende il riordino sul
processore di Streamlit Cloud, quanto traffico fa la lettura della
tabella, e quanto cambia con torch solo per processore.

**Cosa scrive Claude Code**, in un ramo a parte `prova-memoria`, che non
si unisce a `main`:

- `app/prova_memoria.py`, una pagina che non importa `src.config` (non
  serve la chiave del modello) e mostra, passo per passo: memoria
  occupata dal processo (dal file `/proc/self/status`, riga `VmRSS`, e
  il massimo dal modulo `resource`; nessuna libreria nuova) all'avvio,
  dopo il modello di embedding, dopo il riordinatore L12, dopo la
  lettura della tabella `chunk`; byte letti dalla tabella, in forma
  testo e binaria; tempo di 10 riordini di 30 coppie prese dai frammenti
  letti; tempo di 10 ricerche esatte in memoria. Solo lettura sulla
  tabella; nessuna chiamata al modello di linguaggio.
- due versioni di `requirements.txt` sul ramo, in due commit: quella di
  oggi, e una con torch solo per processore (riga
  `--extra-index-url https://download.pytorch.org/whl/cpu` e torch con
  il suffisso `+cpu`; in locale c'è già la 2.14.0+cpu).

**Cosa fa a mano chi mantiene il progetto:**

1. approva commit e push del ramo `prova-memoria` (CLAUDE.md: niente
   push senza approvazione);
2. su Streamlit Community Cloud, "Create app": stesso repository, ramo
   `prova-memoria`, file `app/prova_memoria.py`, un indirizzo diverso da
   quello della demo; nelle impostazioni di condivisione, se disponibile,
   visibilità ristretta (da verificare sulla pagina di Streamlit);
3. nei secrets della nuova app solo `DATABASE_URL` (meglio un utente di
   Postgres con la sola lettura sulla tabella `chunk`, se si vuole
   crearlo su Supabase) e `HF_TOKEN` se c'è; nessuna chiave di
   Anthropic;
4. apre la pagina, aspetta la fine, copia i numeri; poi "Reboot" dopo il
   secondo commit (torch per processore) e ricopia i numeri; annota il
   tempo di installazione mostrato nel registro di Streamlit;
5. alla fine cancella la seconda app; il ramo si toglie quando l'esito
   della prova è scritto in `coda.md`.

La demo pubblica non cambia: altro ramo, altra app, stessi dati letti
in sola lettura. Regola di lettura, scritta prima: si va avanti con il
motore in memoria se la memoria dopo la lettura della tabella resta
sotto 540 MB (i 690 MB del minimo di Streamlit meno 150 MB di margine
per la catena e Streamlit), e se 30 coppie si riordinano in meno di 10
secondi di mediana. Se no, si torna a questo piano prima della fermata
1.

## 9. Tappa 6a, esito (25/11/2026)

- Caso "solo scaduti", elencato prima di toccare il codice
  (`..\dati-grezzi\prova\tappa-6a\casi_solo_scaduti_uscita.txt`): 62 dei
  116 titoli; 4 dei 12 parametri salvati ("neve" tre volte, "bando
  neve"); 1 delle 36 parole ("fotovoltaico"); 2 delle parole della
  strada C ("fotovoltaico", "caldaia"). Le "46 parole" sono 40 distinte:
  6 delle 10 aggiunte erano già tra le 36. In nessun caso il ripiego
  trova un candidato non scaduto.
- Misura prima e dopo
  (`..\dati-grezzi\prova\tappa-6a\misura_6a_uscita.txt`): 116 su 116,
  12 su 12, 36 su 36, 40 su 40 identici (testo, trovato, fonti, voci).
  Per "caldaia" il blocco dei dati è identico prima e dopo: lo scaduto
  del 2021, mostrato come scaduto, e nessun candidato aperto.
- Regola di chiusura: passa. L'interruttore `RIPIEGO_ANCHE_CON_SCADUTI`
  resta acceso: oggi non cambia niente, e quando entrerà un bando non
  scaduto con le parole cercate (per esempio una nuova edizione di un
  bando neve) comparirà come candidato.
- Scoperta: "caldaia" non è nell'avviso del fondo di garanzia; lo
  trova "calda" ("acqua calda sanitaria") per la regola delle 5 lettere.
  Annotata in `coda.md`.

## 10. Soluzioni migliori, viste in questo giro

- **Venti domande sulle spese tutte a mano.** Le 14 del foglio delle
  candidate sono scritte da modelli; sul difetto 1 la misura più pulita
  è con 20 domande scritte da chi mantiene il progetto prima di vedere le
  candidate, come le domande a mano del 19d. Le 14 resterebbero per il
  passo 25. Costa più lavoro a mano.
- **Leggere la tabella una volta sola per contenitore**, con
  `st.cache_resource` (come oggi per il recupero), e i vettori in forma
  binaria: riduce il traffico per avvio. Va nel motore della fermata 1,
  non come passo a parte.
