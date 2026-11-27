# Prova di memoria su Streamlit Cloud

Su `main` dal 27/11/2026 c'è solo questo documento, copiato dal ramo `prova-memoria`: la pagina `app/prova_memoria.py` e i suoi test `tests/test_prova_memoria.py` restano sul ramo.
Per rilanciare la prova: online, un'app nuova su Streamlit Community Cloud dal ramo `prova-memoria` con file `app/prova_memoria.py`, come nella sezione 4; in locale, dal ramo, `streamlit run app/prova_memoria.py` con `PROVA_MEMORIA_CHROMA` su una copia del Chroma (sezione 1).

Prima fermata del resto del 19e (`docs/piano-19e.md`, sezione 8,
"Decisioni del 25/11/2026", decisione 7 e "Prova di memoria su
Streamlit, senza toccare la demo pubblica"). Sta sul ramo
`prova-memoria`, che non si unisce a `main`. La demo pubblica e
`app/app.py` non cambiano.

## 1. Cosa misura la pagina

`app/prova_memoria.py` è una pagina Streamlit a sé. Non importa la catena
né `src.config`, non usa la chiave del modello di linguaggio, non scrive
nel database e non mostra il testo dei frammenti né il contenuto dei
secrets. Ogni passo ha il suo pulsante e si può premere solo dopo il
precedente:

1. memoria del processo all'avvio, più i dati della macchina (versione
   di Python, processore, processori visti, quota di processore del
   contenitore, numero di pacchetti `nvidia-*` installati);
2. modello di embedding (`paraphrase-multilingual-MiniLM-L12-v2`, lo
   stesso dell'app): tempo dell'import di torch e sentence-transformers,
   tempo di scaricamento e caricamento insieme (come fa l'app), versione
   di torch, thread di torch;
3. riordinatore `osiria/minilm-l12-h384-italian-cross-encoder`: tempo di
   scaricamento (solo i file elencati in `FILE_RIORDINATORE`, come nel
   19d) e tempo di caricamento, separati; MB su disco;
4. intera tabella `chunk` di Postgres, in sola lettura (transazione
   `READ ONLY`), con testi, metadati e vettori in forma binaria: righe,
   byte letti per colonna (somma delle celle come arrivano dal server,
   senza l'involucro del protocollo), tempo;
5. indice lessicale BM25 in memoria, con lo stesso `tokenizza` di
   `src/retrieval.py` (copiato, perché quel modulo importa `src.config`);
6. riordino di 30 coppie ripetuto 10 volte: mediana e massimo. Le 30
   coppie sono la domanda fissa "Entro quale data devono essere sostenute
   le spese?" con i 30 frammenti più vicini per prodotto scalare esatto.
   Nello stesso passo: tempo di 10 ricerche dense esatte e di 10 ricerche
   BM25, se i punteggi sono identici tra le 10 ripetizioni, e per ognuno
   dei 30 frammenti un'impronta del testo (i primi 10 caratteri dello
   SHA-1), il prodotto scalare e il punteggio del riordinatore;
7. memoria dopo 20 riordini di fila, con mediana e massimo dei loro
   tempi.

Per ogni passo la pagina riporta la memoria del processo (`VmRSS` da
`/proc/self/status`), il massimo raggiunto (`VmHWM`) e, se il sistema li
espone, la memoria e il limite del contenitore (cgroup). Su Windows, solo
per la prova in locale, riporta il working set e il suo picco. Alla fine
stampa un riepilogo in testo semplice, con il pulsante per copiarlo, e
l'esito della regola.

Se la lettura da Postgres non riesce, la pagina mostra solo il tipo
dell'errore: il messaggio di una connessione può contenere l'indirizzo
del database.

Dal 25/11/2026, dopo la prima prova online (sezione 9): un errore in
qualsiasi passo si mostra con il solo tipo, i passi già fatti restano
visibili e il riepilogo parziale, con l'errore in fondo, si può copiare
comunque. In testa il riepilogo dice in che ambiente è stato preso:
versione di Python, versione di torch e se torch vede una scheda
grafica. Prima del passo 2 torch non si importa (il suo import è
misurato lì): la versione viene dai metadati del pacchetto, che non
sempre portano il suffisso della build (sul PC "2.14.0" contro
"2.14.0+cpu"). Dopo il passo 2 il riepilogo usa `torch.__version__` e
aggiunge la versione CUDA della build ("nessuna" per quella per
processore).

**Opzione per la prova in locale.** Se la variabile d'ambiente
`PROVA_MEMORIA_CHROMA` indica la cartella di una copia del Chroma, la
pagina mostra un interruttore per leggere i frammenti da lì al posto
della tabella. Online la variabile non c'è: l'interruttore non compare
e la pagina legge solo da Postgres. Se la cartella è il Chroma vero
(`data/db/chroma`), la pagina si ferma. Dal Chroma si tolgono gli avvisi
(metadato `id_bando`), perché oggi online non ci sono; i byte sono una
stima (testo in UTF-8, metadati in JSON, 4 byte per numero del vettore).
Corretto il 25/11/2026: il segno degli avvisi è il metadato `sha256`, non
`id_bando`, che ha anche un documento di sempre (sezione 10, "199 contro
316").

## 2. Regola scritta prima di misurare

Si va avanti con il motore in memoria se, nella stessa esecuzione:

- la memoria del processo dopo il passo 7 resta **sotto 540 MB**,
- il massimo raggiunto dall'avvio, letto dopo il passo 7, resta **sotto
  690 MB**, e
- il riordino di 30 coppie sta **sotto 10 secondi di mediana** (passo 6).

Se una delle tre condizioni manca, o il massimo non è leggibile, la
versione "non passa". La regola non si cambia dopo aver visto i numeri.

**Il massimo è cumulativo.** È `VmHWM` di `/proc/self/status`: il picco
della memoria del processo dall'avvio, non quello del singolo passo.
Letto dopo il passo 7 copre quindi tutti i passi; nei passi intermedi
cresce solo quando un passo supera il picco precedente.

**Perché due soglie diverse.** 540 MB riguarda la memoria a regime,
quella che il processo tiene dopo aver caricato tutto: è il minimo di
690 MB meno 150 MB di margine per quello che la pagina non carica.
690 MB riguarda il picco: è il limite oltre il quale il contenitore può
cadere anche se lo supera per un istante, quindi il massimo non ha
margine ma non deve mai arrivarci.

**Osservazione senza soglia.** Si registra se l'app arriva in fondo ai
7 passi senza riavviarsi (la pagina che torna al passo 1, o un messaggio
di Streamlit sul limite di risorse). Non entra nell'esito della regola.

**Da dove viene il 540.** Dal piano del 19e (sezione 8, "Prova di
memoria su Streamlit"): i 690 MB di memoria minima di un'app su Streamlit
Community Cloud, meno 150 MB di margine per quello che la pagina non
carica (catena, librerie di LangChain e Anthropic, SQLite, le sessioni).
I 690 MB vengono dalla pagina dei limiti delle risorse di Streamlit, non
riletta in questo giro (vedi sezione 6). Il piano diceva "dopo la lettura
della tabella"; il compito del 25/11 dice "dopo il passo 7", che viene
dopo i riordini ed è quindi più severo: vale il passo 7. La pagina
mostra il limite del contenitore, se il sistema lo espone. Se è diverso
da 690 MB si annota, ma la soglia resta 540 MB per questa prova.

**Cosa si fa in ciascun caso.**

- **Passa con entrambe le versioni di `requirements.txt`.** Si va avanti
  con il motore in memoria (fermata 1 del piano). Torch solo per
  processore si fa comunque (decisione 7) come compito a parte su `main`,
  prima della fermata 5, dopo il confronto dei punteggi della sezione 5.
- **Passa solo con torch per processore.** Si va avanti con il motore in
  memoria, ma torch per processore diventa una condizione: va su `main`
  prima che il motore vada online (fermata 5), con il confronto dei
  punteggi e con un controllo che la demo di oggi parta con la versione
  nuova.
- **Non passa con nessuna delle due.** Ci si ferma e si torna a
  `docs/piano-19e.md` prima della fermata 1. Gli aumenti passo per passo
  dicono cosa pesa di più: la tabella (passi 4 e 5) porta verso
  l'alternativa A; il riordinatore (passi 3, 6 e 7) porta verso un
  riordinatore spento online o più leggero; se il processo è già vicino
  alla soglia dopo il passo 2, il problema c'è anche senza il 19e. In
  ogni caso serve una decisione nuova, presa senza ritoccare la soglia.
- **La regola non passa, ma l'app arriva in fondo ai 7 passi senza
  riavviarsi.** Non si va avanti in automatico. Si riportano i numeri a
  chi mantiene il progetto, che decide tra alleggerire (torch per
  processore, un solo modello caricato alla volta, riordinatore più
  piccolo) e cambiare servizio. Che l'app abbia retto non basta: la
  regola resta quella scritta prima.

## 3. Le due versioni di `requirements.txt`

**Versione 1, quella di oggi.** È il `requirements.txt` del ramo, uguale
a quello di `main` al commit `2639453`. Il ramo `prova-memoria` parte con
questa versione.

**Versione 2, torch solo per processore.** Cambiano due righe, entrambe
aggiunte; nessuna si toglie:

```
--extra-index-url https://download.pytorch.org/whl/cpu
torch==2.14.0+cpu
```

La prima riga va in cima al file, la seconda accanto a
`sentence-transformers==6.0.1`. Il resto del file non cambia.

Perché: `torch` oggi non è in `requirements.txt` e arriva come dipendenza
di `sentence-transformers`. Su Linux il torch di PyPI si porta dietro le
librerie CUDA (pacchetti `nvidia-*`, circa 2,5 GB secondo la voce "App
online più leggera" di `docs/coda.md`), inutili senza scheda grafica. Il
torch dell'indice `whl/cpu` non le ha. La versione `2.14.0+cpu` è quella
installata nel PC (letta oggi con `torch.__version__`), quindi online
gira la stessa versione con cui sono stati misurati i punteggi del 19d.
La pagina conferma quale versione gira online: il passo 1 conta i
pacchetti `nvidia-*` installati e il passo 2 riporta la versione di
torch.

`chromadb` (la voce di `coda.md` lo dà come non necessario online) resta:
`src/vectorstore.py` importa `langchain_chroma` all'avvio, e toglierlo è
un altro compito.

Applico la versione 2 al `requirements.txt` del ramo solo dopo la prima
misura (passo 6 della sezione 4), come modifica separata.

**Torch per processore può cambiare i punteggi del riordinatore?** Sì,
ma solo nelle ultime cifre, e non per il fatto di essere "per
processore". Online non c'è scheda grafica, quindi anche oggi il calcolo
si fa sul processore. Le differenze possibili vengono da tre cose: la
build di torch (quella di PyPI per Linux e quella `+cpu` sono compilate
in modo diverso), il processore (istruzioni AVX2 o AVX-512, che cambiano
l'ordine delle somme) e il numero di thread. Il PC ha già la `+cpu`,
quindi la versione 2 avvicina l'ambiente online a quello locale invece
di allontanarlo. Sul PC due punteggi vicini differiscono anche di 3
milionesimi (posizioni 22 e 23 del riepilogo del PC), quindi un'inversione
nelle ultime posizioni dei 30 è possibile. Tra i primi 10 lo scarto
minimo sul PC è di 0,0004. Come si controlla è scritto nella sezione 5.

Altre due differenze tra PC e online, annotate il 25/11/2026 dopo la
prima prova online: la **versione di Python** (`.venv` del PC 3.13.12,
online 3.14.10, sia la demo sia l'app di prova) e la **versione di
torch** (PC 2.14.0+cpu, online 2.15.0 dall'indice PyPI, non fissata in
`requirements.txt`: decisione del 15/11/2026 in
`docs/piano-correzioni-lotto1.md`, "Confronto delle versioni prima del
push"). Python di per sé non fa i conti del riordinatore, ma le ruote di
torch e numpy sono compilate per ciascuna versione di Python: anche
queste possono cambiare le ultime cifre. Il confronto della sezione 5 le
copre insieme alle altre.

**Versione 2 per uv e Python 3.14 (proposta del 25/11/2026, non
applicata).** La prima prova online (sezione 9) ha mostrato che Streamlit
Cloud installa con `uv` e che l'app gira con Python 3.14.10. Le due righe
sopra, così come sono, con `uv` non sono sicure:

- `uv`, con la sua strategia di base (`first-index`), cerca ogni pacchetto
  prima negli indici di `--extra-index-url` e si ferma al primo indice che
  lo ha, senza guardare PyPI. L'indice `whl/cpu` di PyTorch ospita anche
  pacchetti non suoi (per esempio `numpy`, `pillow`, `sympy`,
  `networkx`, `jinja2`, `filelock`, `fsspec`): se lì non c'è
  `numpy==2.5.3`, l'installazione fallisce; i pacchetti non fissati
  prenderebbero la versione di quell'indice, non quella di PyPI. Con
  `pip` gli indici si mescolano e il problema non c'è.
- `torch==2.14.0+cpu` porterebbe online una versione mai provata lì
  (contro la decisione del 15/11) e diversa dalla 2.15.0 della prova
  della versione 1: il confronto tra versione 1 e versione 2 misurerebbe
  insieme due cambi, la build e la versione.

Proposta: al posto delle due righe, una sola riga con l'indirizzo
diretto della ruota, limitata a Linux, accanto a
`sentence-transformers==6.0.1`:

```
torch @ https://download.pytorch.org/whl/cpu/torch-2.15.0%2Bcpu-cp314-cp314-manylinux_2_28_x86_64.whl ; sys_platform == "linux"
```

Senza `--extra-index-url`, quindi gli altri pacchetti restano su PyPI. La
versione resta 2.15.0, quella che gira online oggi: tra versione 1 e
versione 2 cambia solo la build. Il segno `sys_platform == "linux"` lascia
il PC com'è (su Windows la riga si salta e vale il torch del `.venv`).
La ruota vale solo per Python 3.14 su x86_64: se si cambia la versione di
Python dell'app, la riga va cambiata insieme.

Da verificare prima di applicarla (non fatto: in questo giro niente
rete): che il file esista con questo nome esatto nell'indice
`https://download.pytorch.org/whl/torch/` (l'etichetta della piattaforma,
qui `manylinux_2_28_x86_64`, può essere diversa), e che la ruota per
Python 3.14 ci sia anche per 2.14.0, se si preferisse la versione del PC.
Il 15/11 `pip --dry-run` per Linux e Python 3.14 risolveva torch 2.15.0
da PyPI, quindi una ruota `cp314` della 2.15.0 esiste; quella `+cpu`
non l'ho vista.

**Versione 2 applicata (25/11/2026, dopo la versione 1).** Chi mantiene
il progetto ha verificato la ruota sulla pagina ufficiale dell'indice di
PyTorch. In `requirements.txt` c'è una sola riga nuova, subito dopo
`sentence-transformers==6.0.1`:

```
torch @ https://download-r2.pytorch.org/whl/cpu/torch-2.15.0%2Bcpu-cp314-cp314-manylinux_2_28_x86_64.whl#sha256=f089c94912c955269a20e5fee6b6a371209b610849c9ece26e908a748d87a723 ; sys_platform == "linux"
```

Resta la 2.15.0 della versione 1: cambia solo la build. Sul PC la riga
si salta: `pip install --dry-run --no-index -r requirements.txt` dà
"Ignoring torch: markers 'sys_platform == "linux"' don't match your
environment", non ha niente da installare, e torch resta 2.14.0+cpu.

Rischi, da guardare nel registro dell'installazione:
- **L'impronta nel frammento dell'indirizzo** (`#sha256=…`). `pip` la
  controlla. Per `uv` mi aspetto lo stesso, ma non l'ho verificato sulla
  sua documentazione (niente rete in questo giro). Se `uv` la rifiutasse,
  l'installazione fallisce in modo visibile nel registro, non in
  silenzio: in quel caso si toglie il frammento e si riprova.
- **Il dominio** `download-r2.pytorch.org` è quello indicato dalla pagina
  dell'indice; se un giorno l'indirizzo cambiasse, l'installazione
  fallirebbe, e la riga va aggiornata.
- **Legata a Python 3.14 su x86_64**: se si cambia la versione di Python
  dell'app, la riga va cambiata insieme.

**Allineare il PC è possibile, non fatto.** Sulla stessa pagina c'è anche
la ruota per Windows (`win_amd64`) della 2.15.0+cpu, per Python 3.13 e
per 3.14 (verificato da chi mantiene il progetto). Il PC potrebbe quindi
avere la stessa versione e la stessa build dell'app online; resterebbero
diversi il sistema e il processore. È un compito a parte.

## 4. Passi a mano su Streamlit Community Cloud

Tutti i file vanno in `..\dati-grezzi\prova\memoria\` (fuori dal
repository). Lì c'è già `riepilogo_pc_2026-11-25.txt`, la prova in
locale (sezione 7).

1. **Commit e push del ramo** `prova-memoria` con `app/prova_memoria.py`
   e questo documento; `requirements.txt` resta la versione 1.
2. **Nuova app**: "Create app", stesso repository, ramo `prova-memoria`,
   file principale `app/prova_memoria.py`, un indirizzo diverso da quello
   della demo. Nelle impostazioni avanzate, la versione di Python della
   demo pubblica (3.14; il PC ha 3.13, sezione 3) e i secrets: solo
   `DATABASE_URL`, più `HF_TOKEN` se lo si vuole
   usare. Nessuna chiave di Anthropic. Se c'è, visibilità ristretta.
3. **Registro dell'installazione, versione 1.** Da "Manage app", copiare
   il registro dall'inizio fino a quando l'app parte e salvarlo come
   `log_installazione_v1.txt`. Annotare in testa al file il tempo di
   installazione e se compaiono pacchetti `nvidia-`.
4. **Misura, versione 1.** Aprire la pagina in una sola scheda, premere i
   pulsanti da 1 a 7 in ordine, aspettando la fine di ognuno. Copiare il
   riepilogo (pulsante di copia del riquadro in fondo) in
   `riepilogo_v1.txt`. Non aprire altre schede durante la misura: ogni
   scheda carica i suoi modelli.
5. **Ripetizione, versione 1** (facoltativa, consigliata): "Reboot app"
   dal pannello, poi di nuovo il passo 4, in `riepilogo_v1_bis.txt`. Dice
   quanto variano i numeri tra un avvio e l'altro.
6. **Versione 2.** Mi scrivi di applicarla; io modifico solo
   `requirements.txt`, tu fai commit e push. Se l'app non reinstalla da
   sola, "Reboot app". Registro in `log_installazione_v2.txt`, come al
   passo 3: il torch installato deve avere `+cpu` e non devono comparire
   pacchetti `nvidia-`.
7. **Misura, versione 2**, come al passo 4, in `riepilogo_v2.txt` (ed
   eventualmente `riepilogo_v2_bis.txt` dopo un altro "Reboot app").
8. **Fine**: cancellare l'app di prova dal pannello di Streamlit. Il ramo
   si toglie quando l'esito è scritto in `docs/coda.md`.

Poi mi dici che i file ci sono: scrivo la tabella (memoria per passo,
tempi, byte, esito della regola per le due versioni) e la proposta per
`requirements.txt` di `main`.

**Passi a mano per la versione 2 (aggiornati il 25/11/2026, dopo la
versione 1).** Sostituiscono i passi 6 e 7 qui sopra. La riga di torch è
già in `requirements.txt` (sezione 3, "Versione 2 applicata").

1. **Commit e push** del ramo `prova-memoria` con `requirements.txt`,
   `app/prova_memoria.py`, questo documento e i test.
2. **Reboot app, sempre.** Streamlit, dopo un push, può accorgersi da
   solo che `requirements.txt` è cambiato (non verificato, sezione 6,
   punto 8), ma con `uv pip install` sull'ambiente esistente i pacchetti
   `nvidia-*` già installati resterebbero lì: `uv pip install` aggiunge e
   cambia, non toglie quello che nessuno chiede più. Il "Reboot app" dal
   pannello ("Manage app", menu con i tre puntini) riparte da capo.
3. **Come si capisce se ha reinstallato.** Nel registro ("Manage app")
   compare un blocco nuovo con l'ora dopo il push o il reboot:
   "📦 Processing dependencies...", "Using uv pip install.", "Resolved …
   packages", "Installed … packages". Se il blocco nuovo non c'è,
   l'ambiente non è stato rifatto: di nuovo "Reboot app".
4. **Cosa controllare nel registro.**
   - nessuna riga con `nvidia-` (né "Downloading nvidia-…" né
     "+ nvidia-…");
   - la riga di torch è `+ torch==2.15.0+cpu (from https://download-r2.pytorch.org/…)`
     o simile: deve esserci `+cpu`;
   - nessun errore sull'impronta (`hash`, `sha256`) o sull'indirizzo.
   Se l'installazione fallisce, si copia il registro e ci si ferma: la
   versione 2 non si misura.
5. **Cosa controllare nella pagina, prima di premere i pulsanti.** Dopo il
   passo 1: "pacchetti nvidia installati 0". Se sono più di 0 l'ambiente
   non è stato rifatto: "Delete app" e "Create app" con le stesse
   impostazioni (ramo `prova-memoria`, `app/prova_memoria.py`, Python 3.14,
   secrets), poi di nuovo il registro. Dopo il passo 2, in testa al
   riepilogo: "torch: 2.15.0+cpu" e "CUDA nella build di torch: nessuna".
6. **Misura.** Una sola scheda, pulsanti da 1 a 7 in ordine, aspettando la
   fine di ognuno; si annota se l'app si riavvia.
7. **Cosa salvare**, in `..\dati-grezzi\prova\memoria\`:
   - `log_installazione_v2.txt`: il registro dall'inizio fino a quando
     l'app parte, con in testa il tempo di installazione e se compaiono
     pacchetti `nvidia-`;
   - `riepilogo_v2.txt`: il riepilogo della pagina (pulsante di copia del
     riquadro in fondo), anche se un passo non riesce;
   - facoltativo, `riepilogo_v2_bis.txt` dopo un altro "Reboot app".
8. **Fine**: come il passo 8 sopra. Poi mi dici che i file ci sono.

**Facoltativo: utente di sola lettura su Supabase.** La pagina apre già
la transazione in sola lettura. Un utente di Postgres con il solo
`SELECT` su `chunk` è una protezione in più; la tabella ha la sicurezza
per riga attiva (README), quindi a un utente nuovo serve anche una
policy di lettura. Da fare solo se lo si vuole: non è necessario per la
misura.

## 5. Confronto dei punteggi (per la fermata 1)

Il riepilogo riporta, per i 30 frammenti del passo 6, impronta del
testo, prodotto scalare e punteggio del riordinatore, in ordine di
riordino. I riepiloghi `v1`, `v2` e del PC si confrontano così:

1. **Stesso insieme?** Si contano le impronte in comune tra online e PC.
   Il PC legge dal Chroma senza avvisi (199 frammenti); online si legge la
   tabella. Se le righe e le impronte non coincidono, gli archivi
   differiscono e il confronto si fa solo sulle impronte comuni. Questo è
   già un dato utile per l'identità della fermata 5.
   Corretto il 25/11/2026: i 199 venivano da una regola di esclusione
   sbagliata; senza avvisi il Chroma ha 316 frammenti, come la tabella
   online (sezione 10, "199 contro 316").
2. **Stesso ordine?** Sulle impronte comuni, l'ordine del riordinatore
   online deve essere lo stesso del PC.
3. **Quanto differiscono i punteggi?** Scarto massimo, per il prodotto
   scalare e per il riordinatore.

Nella fermata 1 il motore nuovo ricalcola sul PC gli stessi numeri con il
codice di `src/` e li confronta con `riepilogo_v1.txt` e
`riepilogo_v2.txt`. Se l'ordine dei 30 è identico e gli scarti sono
nelle ultime cifre, la build di torch non conta. Se l'ordine cambia, lo
si riporta prima di andare avanti, perché l'identità degli ordini della
fermata 5 sarebbe a rischio. In quel caso si sceglie la versione di torch
che dà l'ordine del PC, se una delle due lo dà.

## 6. Cose che non so, da verificare sulle pagine ufficiali

Non verificate in rete in questo giro:

1. Se Streamlit Community Cloud permette una seconda app dallo stesso
   repository su un altro ramo. Credo di sì (ogni app è repository, ramo
   e file), ma non l'ho verificato.
   **Chiusa dalla prima prova online (25/11/2026):** sì, l'app di prova
   gira dal ramo `prova-memoria` accanto alla demo.
2. Quali secrets servono: per la pagina solo `DATABASE_URL` (più
   `HF_TOKEN` facoltativo). La pagina legge prima la variabile d'ambiente,
   poi `st.secrets`; non so se Streamlit Cloud espone i secrets anche come
   variabili d'ambiente, ma con `st.secrets` funziona comunque.
3. Se il riordinatore si scarica senza `HF_TOKEN`. È un modello pubblico
   e credo di sì, con limiti di frequenza più bassi per chi non si
   identifica. Il tempo di scaricamento del passo 3 lo dirà.
   **Chiusa dalla prima prova online (25/11/2026):** sì, il passo 3 è
   riuscito senza `HF_TOKEN`.
4. Il minimo di 690 MB di memoria e come si applica il limite (cosa
   succede quando lo si supera: riavvio, messaggio, app ferma).
   **Chiusa in parte dalla versione 1 completa (25/11/2026):** il limite
   letto dal contenitore è 3072 MB e l'app ha retto a 1887 MB di massimo
   senza riavviarsi (sezione 10). Cosa succede oltre il limite resta da
   vedere.
5. Se Streamlit Cloud installa con `uv` o con `pip`, e come tratta
   `--extra-index-url`. Con `uv` l'indice di PyTorch potrebbe avere la
   precedenza anche per pacchetti che ospita a sua volta (per esempio
   `numpy`), e se lì manca la versione bloccata l'installazione fallisce.
   Se succede, la riga di torch si può sostituire con l'indirizzo diretto
   della ruota per la versione di Python scelta. Da guardare nel registro
   del passo 6.
   **Chiusa in parte dalla prima prova online (25/11/2026):** installa con
   `uv`. Come tratta `--extra-index-url` resta da vedere; per non
   dipenderne, la proposta della sezione 3 usa l'indirizzo diretto.
6. Se la ruota `torch==2.14.0+cpu` esiste per Linux x86_64 e Python 3.14
   nell'indice `whl/cpu` (e la `2.15.0+cpu`, sezione 3, proposta per uv).
7. Quali versioni di Python si possono scegliere e se si scelgono solo
   alla creazione dell'app.
8. Se un push che cambia `requirements.txt` fa reinstallare l'app da
   sola.
9. Se c'è la visibilità ristretta per un'app nel piano gratuito.
10. Se `/proc/self/status` e i file del cgroup sono leggibili nel
    contenitore. Se non lo sono, la pagina ricade su `resource` per il
    massimo, e senza `VmRSS` la memoria del processo risulta 0: il
    riepilogo dice allora "non leggibile" e la misura va rivista.
    **Chiusa dalla versione 1 completa (25/11/2026):** si leggono sia
    `/proc/self/status` sia i file del cgroup v2 (`memory.current`,
    `memory.max`). Come leggere la riga "contenitore": sezione 10.

## 7. Prova in locale (25/11/2026)

La pagina gira in locale sulla copia del Chroma, senza rete e senza
Postgres. Ho fatto la prova con lo strumento di prova di Streamlit
(`AppTest`): pagina vera, sette pulsanti premuti in ordine, variabili
`HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE` e `ANONYMIZED_TELEMETRY` spente
e ogni connessione di rete bloccata. La copia del Chroma era nella
cartella temporanea della sessione. Riepilogo in
`..\dati-grezzi\prova\memoria\riepilogo_pc_2026-11-25.txt`.

I numeri del PC valgono solo come controllo di funzionamento. Su
Windows il working set di torch è molto più grande che su Linux, e
`AppTest` aggiunge il suo peso. Concordano con il 19d: il riordinatore
aggiunge circa 150 MB (148-155 nel 19d) e il riordino di 30 coppie prende
4,7 secondi di mediana (5,0-5,4 nel 19d, `docs/coda.md`, "Passo 19d").
Due giri hanno dato gli stessi 30 punteggi fino alla sesta cifra.

## 8. Soluzioni migliori

- **Regola sul picco, non solo sulla memoria finale.** Un contenitore si
  ferma quando la memoria supera il limite anche per un istante. Sul PC
  il picco dopo il passo 2 è più alto della memoria finale del passo
  (circa 1460 MB contro 1190). La pagina riporta già il massimo
  (`VmHWM`). Proposta, da decidere **prima** della misura: aggiungere la
  condizione "massimo sotto 540 MB", o leggere il dato del contenitore.
  Senza una decisione, vale la regola come è scritta.
  **Chiusa il 25/11/2026, prima della misura:** accolta con soglia
  690 MB e non 540 (sezione 2, "Perché due soglie diverse").
- **Thread di torch.** Online `os.cpu_count()` può vedere i processori
  della macchina e non la quota del contenitore. Torch allora apre più
  thread di quanti ne può usare, e il riordino rallenta. La pagina
  riporta thread e quota. Se il tempo è vicino alla soglia, fissare i
  thread alla quota nel motore della fermata 1 è una correzione a costo
  zero sui punteggi (da confermare con il confronto della sezione 5).

## 9. Prima prova online, 25/11/2026

Versione 1 dei requisiti, app di prova sul ramo `prova-memoria`. Numeri
riportati da chi mantiene il progetto; il riepilogo copiato non c'è,
perché la pagina si è fermata al passo 4 prima della correzione sotto.

**Ambiente.** Installazione con `uv`; Python 3.14.10; torch 2.15.0 con le
librerie `nvidia-*` (la build di PyPI, non quella per processore).

| passo | memoria del processo | massimo dall'avvio |
|---|---|---|
| 1. avvio | 93,7 MB | 95,5 MB |
| 2. modello di embedding | 1295,8 MB | 1340,0 MB |
| 3. riordinatore (scaricato senza `HF_TOKEN`) | 1337,7 MB | 1426,0 MB |
| 4. tabella da Postgres | `TypeError`, vedi sotto | |

L'app non si è riavviata.

**Cosa dicono.**

- La regola della sezione 2 non passa già al passo 2: 1295,8 MB a regime
  contro la soglia di 540, e 1340,0 MB di massimo contro 690. I passi
  dopo possono solo aggiungere. Resta da misurare il riordino (passo 6),
  ma l'esito della versione 1 non può più cambiare.
- L'app regge a circa 1,4 GB senza riavviarsi: il limite vero del
  contenitore è sopra i 690 MB. Il 690 resta la soglia della regola,
  che non si cambia dopo aver visto i numeri; per decidere conta il caso
  "la regola non passa, ma l'app arriva in fondo" della sezione 2, se
  l'app arriva davvero in fondo ai 7 passi.
- Il riordinatore aggiunge circa 40 MB a regime (1337,7 − 1295,8 = 41,9)
  e circa 86 MB di massimo (1426,0 − 1340,0). Sul PC ne aggiungeva circa
  150 (sezione 7).
- Il peso è nel modello di embedding con torch: dal passo 1 al passo 2
  il processo cresce di circa 1200 MB. Il modello in sé pesa meno della
  metà (`model.safetensors` 470.641.600 byte, letto il 25/11/2026 nella
  cache del PC); il resto è torch, che nella build di PyPI
  carica anche le sue librerie per la scheda grafica. È l'ipotesi che la
  versione 2 (torch per processore) mette alla prova.
- Su Linux il passo 2 pesa più che sul PC (1295,8 MB contro 1195,7 di
  working set su Windows): il contrario di quanto la sezione 7 si
  aspettava. È coerente con l'ipotesi sopra: il torch del PC è già quello
  per processore.

**L'errore del passo 4 e la causa.** `TypeError` nella riga
`np.vstack([np.asarray(r[3], dtype=np.float32) for r in righe])` di
`leggi_da_postgres`; il messaggio è oscurato da Streamlit. Causa,
riprodotta in locale senza Postgres: con `pgvector` 0.5.0 (la versione di
`requirements.txt`) il loader che `register_vector` registra restituisce
un oggetto `pgvector.Vector`, non un array numpy come le versioni
precedenti, e `np.asarray` su un `Vector` dà `TypeError: float() argument
must be a string or a real number, not 'Vector'`. Il codice dell'app non
se n'era accorto perché `src/pgstore.py` scrive i vettori ma non li
rilegge: legge solo la distanza calcolata da Postgres.

Correzione del 25/11/2026: `a_vettore` in `app/prova_memoria.py`
converte ogni valore in un vettore numpy, qualunque forma abbia (oggetto
`Vector`; byte nel formato binario di pgvector; testo `[...]`; lista,
tupla o array). Una forma non riconosciuta dà un errore con il tipo
Python e la lunghezza del valore, mai il contenuto. Test con valori finti
in `tests/test_prova_memoria.py`, che sta solo su questo ramo.

**Cose da verificare che la prova ha chiuso** (sezione 6): Streamlit
Cloud installa con `uv` (punto 5, in parte); il riordinatore si scarica
senza `HF_TOKEN` (punto 3); una seconda app dallo stesso repository su un
altro ramo si può creare (punto 1). Anche il punto 10 è chiuso per la
memoria del processo: `VmRSS` e `VmHWM` si leggono (valori diversi da
zero). Per i file del cgroup serve il riepilogo copiato.

**Prossimo passo.** Push della correzione sul ramo, "Reboot app" e di
nuovo i passi da 1 a 7 (sezione 4, passo 4), copiando il riepilogo in
`riepilogo_v1.txt` anche se un passo non riesce. Poi la versione 2,
secondo la proposta per `uv` della sezione 3, dopo la verifica del nome
della ruota.

## 10. Versione 1 completa, 25/11/2026

Riepilogo in `..\dati-grezzi\prova\memoria\riepilogo_v1.txt`, registro
dell'installazione in `log_installazione_v1.txt`, nella stessa cartella
(un riepilogo parziale di prima della correzione del passo 4 è in
`riepilogo_v1_parziale.txt`). Python 3.14.10, torch 2.15.0+cu132 (la
build di PyPI, con 15 pacchetti `nvidia-*`), installazione con `uv`;
processore AMD EPYC 7B13, 16 processori visti, 8 thread di torch.

| passo | processo (MB) | aumento | massimo dall'avvio | contenitore |
|---|---|---|---|---|
| 1. avvio | 91,0 | | 92,6 | 3064,2 |
| 2. modello di embedding | 1289,2 | +1198,2 | 1333,1 | 3026,5 |
| 3. riordinatore | 1333,5 | +44,2 | 1421,3 | 2993,3 |
| 4. tabella | 1344,7 | +11,2 | 1421,3 | 3008,2 |
| 5. indice lessicale | 1346,0 | +1,3 | 1421,3 | 3009,6 |
| 6. riordino, 30 coppie × 10 | 1718,2 | +372,2 | 1887,0 | 2892,8 |
| 7. 20 riordini di fila | 1727,4 | +9,2 | 1887,0 | 2901,3 |

Limite del contenitore letto dalla pagina: 3072 MB, uguale in tutti i
passi. Tabella: 316 righe, 1.046.890 byte (id 2528, testo 352.682,
metadati 205.040, vettori 486.640), lettura in 4,3 s. Riordino di 30
coppie: mediana 2,862 s, massimo 3,091; nei 20 di fila mediana 2,780,
massimo 3,305; punteggi identici tra le ripetizioni. Riordinatore
scaricato senza `HF_TOKEN` in 2,7 s. L'app non si è riavviata.

Esito della regola scritta prima (sezione 2): **non passa**. Memoria
dopo il passo 7 1727,4 MB contro 540, massimo 1887,0 contro 690; il
riordino passa (2,862 s contro 10). La regola non si tocca.

**Cosa dicono.**

- Le soglie di 540 e 690 MB poggiavano sul minimo della documentazione di
  Streamlit, mai misurato. Il limite letto dal contenitore è 3072 MB: il
  processo ha usato al massimo il 61% del limite.
- Caricare il riordinatore aggiunge circa 44 MB, ma usarlo ne aggiunge
  circa 370 a regime (passo 6) e porta il massimo a 1887 MB: sono le
  memorie di lavoro di torch per un lotto di 30 coppie, che restano al
  processo dopo il primo riordino.
- Tabella e indice lessicale aggiungono circa 12 MB in tutto (11,2 + 1,3):
  tenere i 316 frammenti in memoria costa poco.
- Tra il passo 6 e il 7 quasi nessuna crescita (+9,2 MB) e il massimo non
  cambia: 20 riordini di fila non accumulano memoria.
- Il peso resta il modello di embedding con torch: +1198 MB al passo 2.

**La riga "contenitore".** La pagina la legge da
`/sys/fs/cgroup/memory.current` (cgroup v2; il file `cpu.max` letto al
passo 1 conferma la versione), con il limite da `memory.max`. È la
memoria addebitata a tutto il contenitore, che comprende la **cache dei
file**: le pagine dei file letti o scritti di recente, che il sistema
tiene in memoria finché c'è posto e libera quando serve. Al passo 1 vale
3064 MB con il processo a 91: quasi tutto il resto è, con ogni
probabilità, la cache dei pacchetti appena scaricati e installati da `uv`
(il registro scarica circa 2,1 GB compressi di sole librerie
`nvidia-*`, più 514 MB di torch). Poi scende mentre il processo cresce di 1,6 GB: il sistema
libera la cache per far posto. Il numero è quindi **fuorviante**: sembra
un contenitore pieno al 99,7% fin dall'avvio, mentre dice solo che la
cache ha riempito lo spazio libero. Il contenitore si ferma per la
memoria che non si può liberare, non per la cache.

Correzione nella pagina (25/11/2026): accanto a "contenitore" la pagina
riporta, da `memory.stat`, la parte anonima (`anon`, la memoria dei
processi che non si libera), la cache dei file (`file`) e la memoria
senza la cache inattiva (`memory.current` meno `inactive_file`, la misura
che usano anche i sistemi di orchestrazione dei contenitori). Del
processo riporta anche le due parti di `VmRSS`: `RssAnon` e `RssFile`
(i file mappati, per esempio le librerie di torch). La regola e il
criterio non usano questi numeri: servono a leggere i riepiloghi.

**199 contro 316.** Nella prova in locale la tabella aveva 199 righe
"senza avvisi"; online 316. Il numero giusto per "tutto tranne gli
avvisi" è **316**: nel Chroma locale ci sono 1187 frammenti, 871 degli
avvisi e 316 dei documenti di sempre (`docs/fatto.md`, stato del 19c),
e online ci sono solo i documenti di sempre. La causa era la regola di
esclusione della pagina, che toglieva ogni frammento con `id_bando`.
Ma `scripts/ingestione/ingest_tutti.py` dà `id_bando` anche a un
documento di sempre (`mercati-rionali-2026`, 117 frammenti), che quindi
spariva dal conto locale: 871 + 117 = 988 esclusi, 199 tenuti. Conteggio
sui metadati di una copia del Chroma (25/11/2026): 871 frammenti con
`id_bando` e `sha256`, 117 con `id_bando` senza `sha256`, 199 senza
nessuno dei due. Solo gli avvisi hanno `sha256` (l'impronta del PDF,
scritta da `carica_avvisi`). Correzione: la pagina riconosce un avviso da
`sha256` (`e_frammento_di_avviso`), con un test che fallisce con la regola
vecchia. Rilanciata in locale, la pagina legge 316 righe ed esclude 871
avvisi.

Questo conto servirà al **controllo di allineamento della fermata 5**:
l'app online e quella in locale devono lavorare sullo stesso insieme, e
"tutto tranne gli avvisi" sono 316 frammenti (testo 352.682 byte, uguale
in locale e online). Un filtro sugli avvisi basato su `id_bando` darebbe
un insieme diverso.

**Confronto dei punteggi (sezione 5).**

- Con il riepilogo del PC di prima della correzione
  (`riepilogo_pc_2026-11-25.txt`, 199 righe): 17 impronte in comune su
  30, perché mancavano i 117 frammenti dei mercati rionali. Sulle 17 lo
  stesso ordine del riordinatore.
- Con la prova in locale dopo la correzione (25/11/2026, 316 righe,
  Python 3.13.12, torch 2.14.0+cpu, riepilogo nella cartella temporanea
  della sessione, non salvato): **30 impronte in comune su 30, nello
  stesso ordine**, primi 10 compresi. Scarto massimo del prodotto scalare:
  0 alla sesta cifra decimale; scarto massimo del punteggio del
  riordinatore: 0,000001. Con 6 cifre stampate non si vede di più.
- Quindi tra PC (Windows, Intel, Python 3.13, torch 2.14.0+cpu) e online
  (Linux, AMD, Python 3.14, torch 2.15.0+cu132) l'ordine dei 30 è
  identico. La versione 2 cambia solo la build di torch: il confronto si
  ripete sul suo riepilogo.

## 11. Criterio per il quarto caso, scritto dopo la versione 1

**Scritto il 25/11/2026 dopo aver visto i numeri della versione 1 e
prima della versione 2**, da chi mantiene il progetto. Non sostituisce la
regola della sezione 2, che resta com'è e continua a non passare: è il
criterio con cui si decide il quarto caso ("la regola non passa, ma l'app
arriva in fondo ai 7 passi senza riavviarsi").

Si va avanti con il motore in memoria se, nella versione scelta dei
requisiti:

- il massimo dall'avvio dopo il passo 7 resta **sotto 2048 MB**, due terzi
  del limite di 3072 MB letto dal contenitore nella versione 1;
- l'app arriva in fondo ai 7 passi **senza riavviarsi**;
- il riordino di 30 coppie sta **sotto 10 secondi di mediana** (passo 6).

La soglia di 2048 MB è fissa: se il limite letto cambia, si annota, ma la
soglia resta. La pagina stampa il criterio in un blocco separato dopo la
regola, con il limite letto dal contenitore. Sul riavvio la pagina può
dire solo che i 7 passi sono nella stessa sessione (un riavvio azzera la
pagina); un riavvio prima della misura va annotato a mano.

Con i numeri della versione 1 il criterio sarebbe soddisfatto (1887,0 MB,
nessun riavvio, 2,862 s), ma con 161 MB di margine; la versione 2 dice
se torch per processore ne dà di più.

## 12. Versione 2 e confronto, 25/11/2026

Riepilogo in `..\dati-grezzi\prova\memoria\riepilogo_v2.txt`, registro
dell'installazione in `log_installazione_v2.txt`, nella stessa cartella.
Python 3.14.10, torch 2.15.0+cpu ("CUDA nella build di torch: nessuna"),
installazione con `uv` dopo "Reboot app"; stessa macchina della versione 1
(AMD EPYC 7B13, 16 processori visti, 8 thread di torch).

**Versione 2, passo per passo** (MB; "senza cache inattiva" è la memoria
del contenitore meno `inactive_file`, sezione 10):

| passo | processo | aumento | massimo dall'avvio | processo anon | contenitore senza cache inattiva |
|---|---|---|---|---|---|
| 1. avvio | 95,5 | | 95,5 | 73,0 | 309,3 |
| 2. modello di embedding | 933,2 | +837,7 | 977,0 | 770,2 | 1084,3 |
| 3. riordinatore | 975,6 | +42,4 | 1063,5 | 807,7 | 1128,0 |
| 4. tabella | 986,9 | +11,3 | 1063,5 | 811,8 | 1134,6 |
| 5. indice lessicale | 988,2 | +1,4 | 1063,5 | 813,2 | 1135,8 |
| 6. riordino, 30 coppie × 10 | 1375,9 | +387,7 | 1523,6 | 996,0 | 1356,1 |
| 7. 20 riordini di fila | 1228,8 | −147,2 | 1523,6 | 848,8 | 1207,8 |

Limite del contenitore: 3072 MB in tutti i passi. Tabella: 316 righe,
1.046.890 byte, lettura in 4,2 s (come nella versione 1). L'app non si è
riavviata.

La riga "contenitore" ora si legge: al passo 1 vale 2249,3 MB, di cui
1974,5 di cache dei file e 98,7 di memoria anonima. È la conferma della
spiegazione della sezione 10: il numero alto era cache.

**Confronto con la versione 1.**

| | versione 1 (torch di PyPI) | versione 2 (torch per processore) | differenza |
|---|---|---|---|
| processo dopo l'embedding (passo 2) | 1289,2 MB | 933,2 MB | −356,0 MB |
| massimo dall'avvio dopo il passo 7 | 1887,0 MB | 1523,6 MB | −363,4 MB |
| processo dopo il passo 7 | 1727,4 MB | 1228,8 MB | −498,6 MB |
| riordino di 30 coppie (passo 6), mediana / massimo | 2,862 / 3,091 s | 2,539 / 3,374 s | |
| 20 riordini di fila (passo 7), mediana / massimo | 2,780 / 3,305 s | 2,538 / 2,668 s | |
| import di torch e sentence-transformers | 26,7 s | 17,1 s | |
| scaricamento di torch (registro) | 514,2 MiB | 199,8 MiB | |
| preparazione dei pacchetti (registro, "Prepared") | 153 pacchetti in 44,68 s | 134 pacchetti in 6,40 s | |
| pacchetti `nvidia-*` installati | 15 | 0 | |

I tempi del riordino sono della stessa grandezza nelle due versioni (una
misura per versione, quindi le differenze di pochi decimi non dicono
molto). Nella versione 2 il processo scende di 147 MB dal passo 6 al 7
(la parte anonima passa da 996,0 a 848,8 MB): torch restituisce parte
della memoria di lavoro; il massimo resta quello del passo 6.

**Esiti.**

- Regola scritta prima (sezione 2): **non passa in entrambe le versioni**.
  Versione 2: 1228,8 MB dopo il passo 7 contro 540, massimo 1523,6 contro
  690, riordino 2,539 s contro 10 (passa).
- Criterio per il quarto caso (sezione 11): **passa nella versione 2**,
  con 524,4 MB di margine sotto i 2048 (1523,6 MB di massimo), nessun
  riavvio, riordino a 2,539 s. Nella versione 1 il margine era di 161 MB.

**Confronto dei 30 punteggi tra versione 1 e versione 2**, fatto sui due
riepiloghi: 30 impronte in comune su 30, **stesso ordine**; scarto
massimo del prodotto scalare 0 e del punteggio del riordinatore 0, alla
sesta cifra decimale stampata. Le 30 righe delle impronte sono identiche
carattere per carattere. Alla precisione del riepilogo, la build di torch
non cambia né l'ordine né i punteggi. Con la prova in locale (sezione 10)
le 30 coincidevano già nello stesso ordine, con scarto massimo 0,000001.

**Cose da verificare che la prova chiude** (sezioni 3 e 6):

- `uv` accetta l'indirizzo diretto della ruota: il registro riporta
  `+ torch==2.15.0+cpu (from https://download-r2.pytorch.org/whl/cpu/torch-2.15.0%2Bcpu-cp314-cp314-manylinux_2_28_x86_64.whl#sha256=…)`.
- L'impronta `sha256` nel frammento dell'indirizzo è accettata: nessun
  errore nel registro e torch installato.
- Dopo "Reboot app" l'ambiente si rifà da capo: il registro riparte da
  "Starting up repository" e "Cloning", installa 134 pacchetti, nessuno
  `nvidia-`, e il passo 1 conta 0 pacchetti `nvidia-*`. Resta aperto se un
  push che cambia `requirements.txt` reinstalla da solo (sezione 6, punto
  8): il registro del push della versione 2 non c'è.
- Nel registro c'è anche un avviso: Streamlit trova due file di requisiti
  (`requirements.txt` e `pyproject.toml`) e usa `requirements.txt`. Oggi
  va bene; se `pyproject.toml` un giorno elencasse dipendenze, la scelta
  andrebbe ricontrollata. Alle 15:27:19 il registro mostra un
  aggiornamento del codice dal repository ("Updated app") senza nuova
  installazione; il riepilogo ha comunque i 7 passi nella stessa sessione.

**Lezione di metodo.** Le soglie di 540 e 690 MB venivano dal minimo
scritto nella documentazione di Streamlit, mai misurato; il limite letto
dal contenitore è 3072 MB.

**Limiti della prova.**

- Una domanda sola ("Entro quale data devono essere sostenute le spese?"),
  con 30 coppie per riordino.
- Una sessione sola, una scheda: nessuna misura con più utenti insieme.
- La pagina e non l'app vera: la catena, LangChain, Anthropic, SQLite e le
  sessioni dell'app non ci sono; la stima è di circa 150 MB in più
  (sezione 2), mai misurata.
- Una misura per versione: nessuna ripetizione dopo un altro "Reboot app".

**Decisione di chi mantiene il progetto (25/11/2026).** Si va avanti con
il motore in memoria e con i requisiti della versione 2. La riga di torch
per processore va portata su `main` come compito a parte, con una
verifica della demo dopo il riavvio. L'app vera va misurata alla
fermata 5.

**Il ramo.** `prova-memoria` non si unisce a `main`. L'app di prova si
cancella dal pannello di Streamlit.

**A cosa serve questo spazio** (deciso da chi mantiene il progetto il
25/11/2026). Streamlit Community Cloud è l'ambiente dei test e della
demo, non quello definitivo: quando l'app sarà aperta a più utenti
passerà a uno spazio a pagamento. Quindi:

- le soglie e il criterio di questo documento valgono per questo spazio e
  non sono requisiti del prodotto;
- non si ottimizza oltre per i limiti gratuiti: lotti più piccoli e
  riordinatore più leggero restano possibilità, da usare solo se un test
  si blocca;
- al cambio di spazio la misura si rifà con questa stessa pagina
  (`app/prova_memoria.py`, su questo ramo);
- la soglia "qualche migliaio di frammenti" per il motore in memoria
  (`docs/piano-19e.md`, sezione 8; `docs/roadmap.md`) dipende dalla
  memoria disponibile e andrà rivista allora.

**Promemoria per i compiti su `main`** (cose emerse dalla prova che
riguardano il codice vero):

1. Gli avvisi si riconoscono da `sha256`, non da `id_bando`:
   `src/recupero_documenti.py` (i frammenti vicini) e il commento di
   `SPOSTAMENTI_VICINI` in `src/config.py` usano `id_bando`, che ha anche
   il documento di sempre `mercati-rionali-2026` (sezione 10, "199 contro
   316").
2. La lettura dei vettori da Postgres con `register_vector` di `pgvector`
   0.5.0 restituisce un oggetto `pgvector.Vector`, non un array numpy
   (sezione 9): il motore della fermata 1 deve convertirlo, come fa
   `a_vettore` nella pagina.
3. Se serve margine di memoria, la prima mossa è il riordino in lotti più
   piccoli: il primo riordino di 30 coppie aggiunge circa 370-390 MB e
   fissa il massimo (passo 6 in entrambe le versioni). Solo se un test si
   blocca: in questo spazio non si ottimizza oltre ("A cosa serve questo
   spazio", sopra).
