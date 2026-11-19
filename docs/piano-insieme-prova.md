# Piano: insieme di prova dell'app

Misura l'app su domande realistiche, con la stessa catena (router,
interrogazioni, risposta, verificatore) e l'ente Comune di Abetone
Cutigliano. Lo script è `scripts/diagnostica/prova_insieme.py`: i modi
(`--dividi`, `--stima`, `--registra`, `--riprendi`, `--riverifica`,
`--riepilogo`) e i file che scrive sono descritti nella sua docstring.

Le domande e le registrazioni stanno fuori dal repository, in
`dati-grezzi/prova/`: il file delle domande, `lotti.json` con la divisione
in quattro lotti stratificati per gruppo, e una cartella `lotto_<n>/` per
lotto, con le registrazioni e `giudizi.csv`. Se la conversazione con
Claude Code viene azzerata, si riparte leggendo questo file.

## Metodo dei lotti

- **Ogni lotto si registra a freddo una sola volta.** Solo dopo si leggono
  domande e risposte e lo si usa per la diagnosi. Da quel momento non è
  più una misura a freddo: le registrazioni successive dello stesso lotto
  misurano le correzioni, non la qualità su domande nuove.
- **Il lotto 4 resta chiuso fino alla verifica finale prima della demo.**
  È l'unico numero presentabile come misura su domande mai viste.
- **Il lotto 3 è di riserva**, se il lotto 2 rivela difetti gravi.
- **Alla fine, una corsa su tutti i lotti fa da controllo di
  regressione**: dice che le correzioni successive non hanno rotto quelle
  precedenti, non misura la qualità.
- **La regola di chiusura di ogni correzione si scrive prima di
  registrare**, non dopo aver visto i risultati.
- **Gli errori si contano per categoria, non solo in totale**: una
  categoria nuova conta più di un totale che scende.
- **Limite noto**: circa 12 domande a freddo per lotto danno segnali, non
  percentuali affidabili.

## Misure a freddo

Registrazioni a freddo, escluse le domande "viste" (solo nel lotto 1).
Lotto 1: `lotto_1/2026-11-14_114121`, prima delle correzioni 1, 2, 3, A,
C e D (`docs/piano-correzioni-lotto1.md`). Lotto 2:
`lotto_2/2026-11-15_191851`, commit 694936f, dopo quelle correzioni.
Lotto 3: `lotto_3/2026-11-15_215106`, commit 7117aa4, dopo la correzione
E e i punti 1-3 delle osservazioni dall'app online. Lotto 4:
`lotto_4/2026-11-15_231441`, commit 625f7d6, dopo la correzione F. Le
prime colonne
vengono da `--riepilogo`; risposte interrotte e parametri non validi sono
contati a parte, il 15 novembre 2026, dai file delle domande.

Con 12-13 domande per lotto sono **segnali, non percentuali**: una
differenza di una o due domande non dice niente da sola, conta la
categoria dell'errore.

| misura | lotto 1 | lotto 2 | lotto 3 | lotto 4 |
|---|---|---|---|---|
| domande misurate | 12 | 13 | 13 | 12 |
| errori catena / verificatore | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| router riusciti | 11/12 | 13/13 | 13/13 | 12/12 |
| anomalie del router (su 3 chiamate a domanda) | 3/36 | 0/39 | 0/39 | 0/36 |
| attese trovate | 6/6 | 3/3 | 3/3 | 5/5 |
| vietate comparse | 0 | 0 | 0 | 0 |
| dati verificati | 136 | 224 | 149 | 278 |
| non trovati | 1 | 0 | 2 | 1 |
| senza fonte | 0 | 3 | 0 | 3 |
| citati con il blocco | 0 | 0 | 0 | 0 |
| risposte interrotte per max_tokens | 0 | 0 | 0 | 0 |
| parametri non validi | 6 | 0 | 0 | 0 |
| costo medio a domanda | 0,042 $ | 0,051 $ | 0,052 $ | 0,061 $ |

Note:

- Router: nel lotto 1 una domanda su 12 (A01) non ha avuto una decisione
  leggibile e 3 chiamate su 36 erano anomale (correzione 1); nel lotto 2
  nessuna.
- Parametri non validi: temi o tipi fuori dagli elenchi chiusi di oggi
  (`TEMI`, `TIPI_BENEFICIARIO`). Nel lotto 1 sono C04, C05, C11, C12, P11,
  P25: la diagnosi della correzione 2 ne contava 4; C05 ("parcheggi") e
  C12 ("sport") non sono temi dell'elenco nemmeno loro, ma trovavano bandi
  attraverso la ricerca nei titoli. Nel lotto 2 nessuno (correzione 2).
- Risposte interrotte: nel lotto 1 il campo non c'era; dai token in uscita
  nessuna delle 12 domande misurate arriva al tetto di allora (4096). L02,
  troncata, è tra le domande "viste", escluse dalla misura (correzione D1).
- Senza fonte nel lotto 2: 3 anni nei titoli ("2021" di "FESR 2021-2027" in
  A05, "2026" in due titoli di bandi in C06), non dati della risposta.
- Il costo medio sale da 0,042 a 0,051 $. Medie per domanda della
  risposta: in ingresso da 7.778 a 10.229 token (più dati nel contesto),
  in uscita da 977 a 1.263; il router resta simile (in ingresso da 7.097
  a 7.703, in uscita da 266 a 224).
- Lotto 3: i 2 non trovati sono di P01, "I 55.1" e "I 55.3" citati con
  [D1.7] mentre stanno in [D1.16]: etichetta sbagliata del modello,
  segnalata correttamente dal verificatore (giudicati `errore_vero`; le
  altre 13 righe di `giudizi.csv` sono `corretto`). Costo stabile: medie
  della risposta 10.387 token in ingresso e 1.321 in uscita, router 7.708
  e 212. Solo C10 ha consultato i documenti. I difetti del lotto 3 non si
  vedono in queste colonne: sono due conclusioni sbagliate su dati giusti
  (P05 e P24, il profilo dell'ente preso per chi chiede) e un "Non trovo"
  con l'avviso pertinente solo nei documenti (C18): correzione F in
  `docs/piano-correzioni-lotto1.md`.
- **Lotto 4: è la verifica finale a freddo prima della demo.** Le
  correzioni successive si misurano solo su domande già viste e con la
  regressione su tutti i lotti, non più a freddo. Giudizi a mano
  (`lotto_4/giudizi.csv`, 19 righe): 14 `corretto`, 3 `errore_vero`, 2
  `falso_allarme_titolo`. Il non trovato è di P04: il decreto 23619 del
  bando welfare [D1.16] attribuito al bando Filiera SMART [D1.9], che non
  ha atto (`errore_vero`). I 3 senza fonte sono di C08, nel riepilogo
  finale senza citazione: due volte "2026" nel titolo "Missione Comune
  2026" (`falso_allarme_titolo`) e la data 2026-12-05, giusta ma non
  citata (`errore_vero`, lieve). Il terzo `errore_vero` è C19: il router
  non sceglie nessuna interrogazione (3 chiamate su 3) e la risposta è
  "Non trovo", senza inventare. Correzione G in
  `docs/piano-correzioni-lotto1.md`.
- **Regressione finale (16/11/2026, commit 715b411)**, dopo le
  correzioni G e G5. Non è una misura a freddo e non entra nella
  tabella. 55 domande sui 4 lotti; router 55/55 con 0 anomalie; 0
  risposte interrotte; costo 3,44 $. Degli 8 rifiuti introdotti da G ne
  sono rientrati 6; C02 e P22 no, per la scelta del router (per P22 uno
  spostamento sistematico dopo G). Attese mancate: L05, mai
  soddisfatta, e C02. 6 non trovati in 4 domande, nessun errore
  vero. Esito: correzioni chiuse, piano B non necessario. Dettagli in
  `docs/piano-correzioni-lotto1.md`, "Regressione finale".

## Regola delle misure (18/11/2026)

Spostata da `docs/roadmap.md` il 18/11/2026: passo 0, metodo delle
etichette del passo 1, metodo del passo 4, regola del confronto
appaiato della sezione B, riga "Prova" dei principi.

Aggiunte il 18/11/2026, fino ad allora solo nelle conversazioni: le
definizioni e le regole dell'etichettatura ("Etichettatura: definizioni
e regole", dopo il metodo delle etichette).

### Passo 0

**Regola delle misure.** Tutte le misure di A e B su una copia
congelata dei CSV e con data di riferimento 2026-11-16. Motivo: 54
bandi aperti al 16/11, 43 al 1/12. Per il Comune 7 al 16/11, 3 al
1/12, 1 dal 6/12: 4 scadono tra il 26 e il 30/11 e 2 il 5/12. Sono 7
come li mostra l'app; la query ne trova 8, e l'ottavo (fondo di
garanzia energie rinnovabili) è senza scadenza, non a sportello e non
recente. Tre parti:
- (a) data fissa 2026-11-16, sostituita anche in `src.chains.rag` e
  letta da `prova_insieme` per `meta.json`;
- (b) SQLite ricreato dai CSV congelati, con `connetti` puntato lì e
  l'impronta calcolata su quella cartella;
- (c) i documenti non si congelano: nessuna ingestione tra la baseline
  e i confronti di un ciclo, altrimenti si rifà la baseline.

(a) e (b) sono un compito di codice a parte, con i suoi test, prima
della nuova baseline.

Verifica del 18/11/2026: 52 bandi aperti al 18/11.

**Copia congelata e opzioni** (18/11/2026). (a) e (b) fatte il
18/11/2026. Nessuna copia esiste ancora: la prima si fa dopo il passo
2b.

Procedura per creare la copia:
- working tree pulito (`git status --porcelain` vuoto): la copia è
  quella dei CSV del commit corrente;
- cartella `dati-grezzi/archivi/<data della copia>_<prime 8 cifre
  dell'impronta>/`, per esempio `2026-11-20_3fa91c02`. Nel nome mai la
  data di riferimento delle misure: quella sta in `--data` e in
  `meta.json`;
- prima della copia, `python -m scripts.manutenzione.crea_testo_ricerca
  --file <OpenData_Incentivi.csv> --controlla` deve dire "aggiornato":
  altrimenti il testo di ricerca (passo 17) è vecchio rispetto ai bandi
  e va rigenerato senza `--controlla`, e il working tree non è più pulito
  (19/11/2026);
- si copiano solo i CSV delle tabelle di `TABELLE_DA_CSV` e di
  `CSV_FUORI_DATABASE` (`src/database/schema.py`), non il resto di
  `data/processed` (copie `.bak`, pagine `.txt`, `scansione.log`,
  `doppioni.csv`). `CSV_FUORI_DATABASE` (oggi `testo_ricerca.csv`, dal
  19/11/2026) entra nella copia e nell'impronta ma non in SQLite: il
  passo 4 dovrà leggerlo dalla copia e fermarsi se manca.
  `crea_da_csv` si rifiuta se manca un CSV di `TABELLE_DA_CSV`. `bilancio.csv` e
  `turismo.csv` sono in `data/processed` dal passo 2a (18/11/2026),
  vuoti con la sola intestazione;
- `origine.txt` nella cartella, con il commit, la data della copia e
  l'impronta complessiva calcolata da `impronta_csv` sulla copia, la
  stessa che finisce in `meta.json`;
- l'impronta (versione 2, dal 18/11/2026: `versione_impronta` dentro
  `impronta_csv`) è calcolata sulle righe lette con `csv.reader`, non
  sui byte: fine riga e BOM non contano, le righe vuote sì. Una copia
  fatta da un checkout con fine riga diverse ha la stessa impronta. Nei
  CSV non ci sono a-capo dentro i campi: `esporta_csv` li sostituisce
  con uno spazio, nel CSV e nel database, e lo stampa. Un `meta.json`
  con un'impronta senza versione è "in formato vecchio, non
  confrontabile", non "cambiato": `prova_insieme` lo dice alla ripresa,
  `diagnosi_attese` nel rapporto e, con `archivio`, si ferma con un
  errore;
- la copia non si modifica mai dopo la prima registrazione: se i dati
  cambiano, se ne fa una nuova, con una cartella nuova.

Opzioni:
- `prova_insieme --registra --lotto N --data 2026-11-16 --archivio
  CARTELLA`: data fissata e SQLite ricreato dai CSV di CARTELLA in una
  cartella temporanea, mai in `data/db`. `meta.json` ha `data_fissata`,
  `archivio` e l'impronta della cartella. Una sola delle due opzioni
  si può, con un avviso nel rapporto. La ripresa (`--riprendi`) rilegge
  data e archivio da `meta.json`.
- `diagnosi_attese` legge l'archivio dal `meta.json` della
  registrazione: se la cartella non c'è più o la sua impronta è
  cambiata si ferma con un errore, senza ripiegare su `comune.sqlite`.
  Registrazioni su archivi diversi si accettano, con un avviso in
  testa al rapporto: i totali non sono una misura appaiata. `--titolo`
  cerca sempre su `comune.sqlite` alla data di oggi, e il rapporto lo
  dice.

### Metodo delle etichette (passo 1)

Metodo previsto il 18/11/2026 e non seguito: le etichette sono state
fatte come descritto in 'Come sono state fatte le etichette'. Resta
valido l'ultimo punto, sui bandi senza etichetta nei primi 10 del
passo 4.

- Prima del primo giro: definizione scritta di "generico", con esempi;
  colonna "chi atteso" per domanda.
- Confronto con un secondo modello sulle stesse 10: regola di chiusura
  in "Etichettatura: definizioni e regole".
- Un bando senza etichetta nei primi 10 del passo 4 si etichetta, non
  conta come "no".

### Etichettatura: definizioni e regole

**Gruppi delle domande.** C comuni, P privati, A aperte, L "viste":
usate durante lo sviluppo, solo nel lotto 1, mai a freddo.

**Giudizi delle schede.**
- **pertinente**: chi chiede può partecipare, anche a una condizione, e
  lo scopo rientra in ciò che il bando finanzia;
- **generico**: non pensato per lo scopo ma potrebbe finanziarlo
  (credito, interessi, garanzie per qualunque Pmi); si nomina in fondo;
- **no**: chi chiede non può partecipare, oppure lo scopo non c'entra,
  oppure è scaduto e la domanda cerca opportunità attuali.

Gli scaduti possono essere pertinenti solo per le domande sullo
storico. Nel dubbio si sceglie un giudizio e si scrive "dubbio" nella
nota.

Esempi: l'abbattimento interessi è generico per un investimento e "no"
per un'assunzione; un incentivo all'assunzione è pertinente per P05 e
P24 e "no" per P01.

Pertinenza e ipotesi di utilizzo sono due cose distinte. Se il bando
può finanziare proprio l'intervento chiesto, anche a una condizione, è
pertinente o generico. Se per usarlo serve un progetto diverso da
quello chiesto, è 'no' per la pertinenza, e l'idea va nella colonna
ipotesi_da_verificare. Le ipotesi sono idee di utilizzo, non giudizi.

**Forma attesa**, calcolata dai giudizi:
- `elenco`: almeno un pertinente;
- `solo_generici`: nessun pertinente, almeno un generico;
- `non_trovo`: altrimenti.

**Procedura.** Valeva per l'etichettatura a mano. Per le 96 righe
giudicate a mano resta valido: si lavora su una copia fuori dal
repository e non si guardano le risposte dell'app.
- Si lavora su una copia delle schede, fuori dal repository.
- Non si guardano le risposte dell'app.
- Prima il giro per domanda, poi il controllo di coerenza per bando.
- Si segna il tempo.
- Le schede non si rigenerano finché i giudizi stanno solo nella copia.

**Regola di chiusura del confronto con il secondo modello.** Non
applicata: sostituita il 18/11/2026 dal metodo descritto in 'Come sono
state fatte le etichette'.
- Passa con un accordo di almeno l'85% e al massimo un disaccordo
  "pertinente contro no" per domanda.
- Se passa, il modello propone le altre 40 e si rivedono tutte; se no,
  si etichettano tutte a mano.
- L'accordo per classe si riporta, non è una soglia.

### Come sono state fatte le etichette (18-19/11/2026)

Le etichette sono giudizi sulla base della pagina web del bando, cioè
delle stesse informazioni che l'app ha oggi. Non sono giudizi sugli
avvisi in PDF. Quando l'archivio leggerà i PDF, le righe di quei bandi
vanno rietichettate.

**Metodo.** Due modelli indipendenti hanno giudicato le 888 righe non
automatiche. Un terzo modello ha fatto da arbitro sui 112 disaccordi,
con il testo delle pagine web, indicando la frase che decide oppure
"non_basta" quando la pagina non bastava. 102 righe sono "no"
automatici: il Comune non è tra i beneficiari. A mano sono state
giudicate 96 righe, tutte dei Comuni: 8 nelle domande C01-C03 e le 88
righe in cui entrambi i modelli dicevano "no" a un bando aperto nelle
domande C04-C20.

**Giudizio finale di ogni riga**, per chiave (codice, id_bando), dalla
priorità più alta:
1. giudizio a mano della revisione dei Comuni;
2. giudizio a mano nel foglio di controllo, dove compilato;
3. arbitro; con "non_basta": generico se nessuno dei due modelli aveva
   detto "no", altrimenti "no";
4. accordo dei due modelli;
5. automatici.

**Scadenza.** Non la giudica chi etichetta, la applica una regola: se
il bando è scaduto alla data di riferimento (16/11/2026) e la domanda
non è sullo storico (C19), l'etichetta è "no". Il giudizio sul
contenuto resta nella colonna giudizio_contenuto.

**Righe incerte.** Una riga è incerta se la nota di chi ha giudicato a
mano esprime un dubbio o rimanda al PDF, se l'arbitro dice "non_basta",
oppure se è un "generico" dato a mano nella revisione dei Comuni.
L'etichetta resta, con incerta = sì.

**Forma attesa di ogni domanda**, calcolata dalle etichette: "elenco"
con almeno un pertinente; "solo_generici" senza pertinenti ma con
almeno un generico; "non_trovo" altrimenti. Se la forma cambia
togliendo le righe incerte, la domanda ha "forma incerta" e non si usa
per giudicare l'app finché non si leggono i PDF.

**Regola per la misura.** Una riga "generico" è neutra: non conta come
errore né se l'app la cita né se non la cita. Contano come errori solo
i pertinenti mancati e i "no" presentati come opportunità.

**Numeri al 19/11/2026**, sull'archivio dopo il passo 2a:
- 990 righe su 50 domande: 836 no, 115 generici, 39 pertinenti; 28
  decise dalla regola della scadenza;
- fonti: 88 dalla revisione dei Comuni, 8 dal foglio di controllo, 112
  dall'arbitro, 680 dall'accordo dei modelli, 102 automatici;
- 27 righe incerte: 14 dalla revisione, 13 "non_basta" dell'arbitro;
  16 nei Comuni e 11 nei privati;
- forme attese: 20 elenco, 29 solo_generici, 1 non_trovo (C07);
- forma incerta: C18 e C20;
- 35 ipotesi di utilizzo conservate, tutte sulle domande dei Comuni.

**Limiti.**
- Sono etichette di modelli, riviste a mano solo in parte e solo per i
  Comuni. Le righe dei privati (P e L) non hanno revisione umana.
- L'accordo tra i due modelli è dell'87% su tutte le righe, ma del 49%
  sulle 221 righe in cui almeno uno dei due non dice "no": il confine
  di "generico" è largo.
- Nella revisione dei Comuni, su 88 "no" concordi dei modelli ne sono
  stati cambiati 5, tutti in generici dubbi. Con la regola che separa
  la pertinenza dalle ipotesi di utilizzo, il "no" dei modelli regge.
- Per molti bandi, soprattutto dei Comuni, requisiti e spese decisive
  stanno negli avvisi in PDF. Le righe incerte ne sono l'elenco
  minimo, non completo.
- Le etichette dipendono dallo stato dei bandi in archivio: dopo ogni
  correzione di una scadenza vanno ricalcolate.
- Le 5 domande A non hanno etichette.

**Uso.** Confronti tra varianti sullo stesso insieme. Non servono a
dire quanto l'app è corretta in assoluto.

### Metodo del confronto sull'ordinamento (passo 4)

Tre bracci: ricerca attuale; filtro per chi più ordinamento per cosa; lo
stesso con le famiglie di bisogno. Risultati separati per bandi con e
senza interventi; pertinenti persi dal filtro contati a parte.

### Regola del confronto appaiato (sezione B)

Regola per B: confronto appaiato domanda per domanda, con la soglia
decisa prima; una variante passa solo se i miglioramenti netti superano i
cambi osservati tra le ripetizioni della baseline.

### Prova: tabella "Bandi ricorrenti"

- **Prova**: tabella "Bandi ricorrenti" del 18/11/2026. Su 54 bandi aperti
  un'impresa generica ne ammette 25. Sei bandi compaiono in 29 domande
  private su 30: quattro per assunzioni e tirocini, più il welfare
  aziendale e cloud e cyber security; risorse genetiche agrarie compare
  in 30 su 30.
