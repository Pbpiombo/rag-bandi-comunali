# Prova di memoria su Streamlit Cloud

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

**Opzione per la prova in locale.** Se la variabile d'ambiente
`PROVA_MEMORIA_CHROMA` indica la cartella di una copia del Chroma, la
pagina mostra un interruttore per leggere i frammenti da lì al posto
della tabella. Online la variabile non c'è: l'interruttore non compare
e la pagina legge solo da Postgres. Se la cartella è il Chroma vero
(`data/db/chroma`), la pagina si ferma. Dal Chroma si tolgono gli avvisi
(metadato `id_bando`), perché oggi online non ci sono; i byte sono una
stima (testo in UTF-8, metadati in JSON, 4 byte per numero del vettore).

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

## 4. Passi a mano su Streamlit Community Cloud

Tutti i file vanno in `..\dati-grezzi\prova\memoria\` (fuori dal
repository). Lì c'è già `riepilogo_pc_2026-11-25.txt`, la prova in
locale (sezione 7).

1. **Commit e push del ramo** `prova-memoria` con `app/prova_memoria.py`
   e questo documento; `requirements.txt` resta la versione 1.
2. **Nuova app**: "Create app", stesso repository, ramo `prova-memoria`,
   file principale `app/prova_memoria.py`, un indirizzo diverso da quello
   della demo. Nelle impostazioni avanzate, la versione di Python del PC
   (3.13) e i secrets: solo `DATABASE_URL`, più `HF_TOKEN` se lo si vuole
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
2. Quali secrets servono: per la pagina solo `DATABASE_URL` (più
   `HF_TOKEN` facoltativo). La pagina legge prima la variabile d'ambiente,
   poi `st.secrets`; non so se Streamlit Cloud espone i secrets anche come
   variabili d'ambiente, ma con `st.secrets` funziona comunque.
3. Se il riordinatore si scarica senza `HF_TOKEN`. È un modello pubblico
   e credo di sì, con limiti di frequenza più bassi per chi non si
   identifica. Il tempo di scaricamento del passo 3 lo dirà.
4. Il minimo di 690 MB di memoria e come si applica il limite (cosa
   succede quando lo si supera: riavvio, messaggio, app ferma).
5. Se Streamlit Cloud installa con `uv` o con `pip`, e come tratta
   `--extra-index-url`. Con `uv` l'indice di PyTorch potrebbe avere la
   precedenza anche per pacchetti che ospita a sua volta (per esempio
   `numpy`), e se lì manca la versione bloccata l'installazione fallisce.
   Se succede, la riga di torch si può sostituire con l'indirizzo diretto
   della ruota per la versione di Python scelta. Da guardare nel registro
   del passo 6.
6. Se la ruota `torch==2.14.0+cpu` esiste per Linux x86_64 e Python 3.13
   nell'indice `whl/cpu`.
7. Quali versioni di Python si possono scegliere e se si scelgono solo
   alla creazione dell'app.
8. Se un push che cambia `requirements.txt` fa reinstallare l'app da
   sola.
9. Se c'è la visibilità ristretta per un'app nel piano gratuito.
10. Se `/proc/self/status` e i file del cgroup sono leggibili nel
    contenitore. Se non lo sono, la pagina ricade su `resource` per il
    massimo, e senza `VmRSS` la memoria del processo risulta 0: il
    riepilogo dice allora "non leggibile" e la misura va rivista.

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
