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

## Casi fissi

Domande reali portate dal consulente pilota, con il bando che avrebbe
dovuto trovare. Un caso fisso si registra a ogni misura, non è mai "a
freddo" e non entra nei lotti: `lotti.json` non si rifà, e una riga in
più nel file delle domande non apparterrebbe a nessun lotto. I casi
stanno fuori dal repository, in `dati-grezzi/prova/casi_fissi.txt`, con
lo stesso formato del file delle domande (`gruppo | codice | domanda |
atteso`); la modalità `--casi-fissi` di `prova_insieme` che li registra
è un compito di codice a parte (`coda.md`, "Insieme di prova: dopo").
Ente Comune di Abetone Cutigliano, data di riferimento 2026-11-16.

Per ora i casi fissi si misurano con le attese e le vietate, non con le
etichette: le etichette del bando nuovo contro le domande dell'insieme
vanno fatte prima della nuova baseline (`coda.md`, "Riscontro del
consulente pilota e fonti").

**F01** (gruppo comuni; consulente pilota, 19/11/2026):
- domanda: "bandi o contributi per associazioni ed enti in materia di
  rievocazioni storiche o culturali";
- attesa: Fondo nazionale rievocazione storica 2027 (in archivio come
  fondo-rievocazione-storica-2027, aperto dal 3/11/2026 al 31/01/2027,
  quindi aperto alla data di riferimento);
- opportunità collegata attesa, da valutare al passo 9 e oggi non
  contata come errore: Cultura Missione Comune 2026;
- vietata: l'edizione 2025 delle rievocazioni (Sostegno alle
  manifestazioni di rievocazione storica anno 2025, scaduta il
  20/02/2025) presentata come opportunità;
- forma attesa: elenco.
- Diagnosi del caso in `coda.md`, "Riscontro del consulente pilota e
  fonti (19/11/2026)".

## Foglio dei fatti (passo 19d)

Serve a misurare il recupero sugli avvisi dei bandi (`coda.md`, "Passo
19d"). Sta fuori dal repository, in
`dati-grezzi/fatti_pdf_modello_2026-11-20.xlsx`, e non si corregge a
mano: se un fatto è sbagliato, lo si segna e si fa un foglio nuovo, con
la data nel nome.

**Come è fatto.** Tre fogli. "leggimi" ha le regole di compilazione.
"bandi" ha una riga per bando della prima prova del passo 19, con la
scadenza in archivio, la pagina, il PDF dell'avviso, le pagine e se il
testo si seleziona. "fatti" ha le colonne `id_bando`, `titolo`,
`tipo_fatto`, `registro`, `domanda`, `frase`, `pagina_fisica`,
`in_tabella`, `frase_solo_in_questo_bando`, `anche_sulla_pagina_web` e
`note`. 91 righe, 81 con la frase, su 11 bandi.
- Due registri di domanda (`registro`): "semplice", come la farebbe una
  persona allo sportello (40 righe), e "caso", una situazione concreta
  (41 righe).
- Risposte in più punti: la frase è divisa in pezzi con " [...] " (14
  frasi); il tipo di fatto lo dice con "(più punti)".
- Righe di tabella (`in_tabella` "sì", 17 righe): le celle sono separate
  da " | ".
- `pagina_fisica` è la pagina del file PDF, anche più di una ("3 e 9").
- Frasi di controllo sui gemelli: `frase_solo_in_questo_bando` dice se
  la frase sta solo in quel bando (27 "sì", 9 "no", 45 vuote). Per i
  documenti gemelli (Cultura e Sport Missione Comune, i due bandi PMI, i
  quattro allegati degli apistici) vale il valore calcolato dal
  controllo, non quello scritto.
- Negli apistici la nota comincia con l'azione e l'allegato ("Azione B1
  (Allegato A1)"; nel secondo foglio "Azione B1, Allegato A1, par. …").

**Chi lo compila.** Un modello, con le regole scritte nel foglio
"leggimi": la frase copiata dal PDF senza cambiare una parola, da 8 a 30
parole; la pagina del lettore, non quella stampata; nessun dato
personale; nessuna parafrasi; nessun fatto da un PDF scansionato.

**Come si verifica.** `scripts/diagnostica/controlla_fatti.py`, senza
rete e senza modello, sul testo delle pagine estratto come nel
caricamento e su una copia temporanea di Chroma. Per ogni pezzo, e per
ogni cella delle righe di tabella:
- presenza a tre livelli: alla lettera; normalizzata (spazi, virgolette
  tipografiche, parole spezzate a fine riga); senza spazi;
- pagina dichiarata, altre pagine, altri bandi, assenza con il tratto
  più simile;
- per gli apistici, l'allegato della nota;
- gemelli;
- frammenti che contengono il pezzo, con inizio e fine sul testo vero
  del frammento confrontati con `car_visti`;
- domande con un numero della frase, contatti in domanda e note.

Esiti del 20/11/2026: 81 fatti, 97 pezzi; 81 trovati nella pagina
dichiarata (13 alla lettera, 54 normalizzati, 14 solo senza spazi), 0
assenti; 97 pezzi interi in un frammento, 42 nella parte vista dal
modello di embedding; una riga sola con un problema, la 23, quasi
gemella. Uscita in `dati-grezzi/prova/fatti_controllo_2026-11-20.csv`,
una riga per fatto.

**Secondo foglio (20/11/2026).** `dati-grezzi/fatti_pdf_modello_2_2026-11-20.xlsx`,
stesse colonne e stesse regole del primo, compilato da un modello e non
corretto a mano: 114 fatti sugli stessi 11 bandi, 140 pezzi, 34 domande
"semplice" e 80 "caso", 23 righe di tabella, 24 risposte in più pezzi.
Serve a portare i fatti a 195, perché con 40 fatti per metà differenze di
1-3 fatti restavano nel rumore; dal 20/11/2026 sera due configurazioni si
confrontano con il test esatto dei segni sulle coppie discordanti, e la
soglia fissa di 1-3 fatti non vale più (`coda.md`, "Passo 19d", punto 2). Esiti
del controllo: 114 trovati nella pagina dichiarata (12 alla lettera, 90
normalizzati, 12 solo senza spazi), 0 assenti, 0 in altro bando; 140
pezzi interi in un frammento, 59 nella parte vista. Con `--confronta` si
controllano le frasi uguali o quasi a quelle del primo foglio: 4 righe,
tutte frasi gemelle. Uscita in
`dati-grezzi/prova/fatti_controllo_2_2026-11-20.csv`.

### Divisione in taratura e controllo

I fatti si dividono in due metà prima di ogni misura, e la divisione
non cambia più: la taratura serve a scegliere, il controllo a
confermare la scelta finale. Metodo
(`scripts/diagnostica/misura_recupero_avvisi.py`, `--dividi` e
`--dividi-secondo`):
- per bando, a caso, con il seme scritto nel codice; si prende la prima
  proposta, su al più 5.000, che rispetta tutte le regole, e se non ce
  n'è nessuna lo script si ferma e dice quale regola non si soddisfa,
  senza allentarne nessuna;
- in ogni bando e nei totali le due metà differiscono al più di un
  fatto, e così le frasi gemelle;
- frasi identiche (livello senza spazi) nella stessa metà; anche le
  frasi quasi uguali, tra fogli diversi e dentro lo stesso foglio;
- differenze massime: righe di tabella 1, risposte in più pezzi 1,
  domande "semplice" 3, domande "caso" 3, fatti con tutti i pezzi nella
  parte vista 2;
- un foglio nuovo non tocca la divisione dei fogli precedenti: le sue
  righe simili a una riga già divisa vanno nella metà di quella, letta
  solo per quelle righe dopo il controllo dell'impronta;
- un fatto non trovato dal controllo meccanico resta fuori, elencato;
- il file della divisione ha la sua impronta in un `.sha256` accanto,
  e ogni misura la verifica prima di leggere.

| foglio | seme | file | sha256 | taratura | controllo |
|---|---|---|---|---|---|
| primo | `1920261120` | `fatti_divisione_2026-11-20.csv` | `c7180d2d…1952` | 40 | 41 |
| secondo | `220261120` | `fatti_divisione_2_2026-11-20.csv` | `4c70a94d…b173` | 57 | 57 |
| insieme | | | | 97 | 98 |

Impronte intere e conteggi per tipo in `docs/fatto.md` (20/11/2026).

**La metà di controllo non si legge senza un via esplicito** di chi
mantiene il progetto: né domande, né frasi, né esiti, e nessuna misura
la apre senza l'opzione `--controllo`. Si apre una volta sola, sulla
scelta finale del passo (`coda.md`, "Passo 19d", punto 1).
