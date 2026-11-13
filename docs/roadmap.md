# Roadmap

Stato al 13 novembre 2026. Da aggiornare alla fine di ogni sottopasso.

## Fatto

- **Passo 1**: test automatici su verificatore, pulizia e divisione del testo.
- **Passo 2**: profilo dell'ente come dato. Tabella `enti` con l'Unione e i tre
  comuni, codice dell'ente lungo tutta la catena, menu nell'app, profilo anche
  nel prompt della risposta.
- **Passo 3, sottopasso fonti e chiavi**: tabella `fonti`, chiavi di `bandi` e
  `scansioni` con la fonte, acquisizione per URL canonico, conversione degli
  importi, campi bloccanti e avvisi, id univoci.
- **Corsa controllata su 10 bandi**: verificate le correzioni; costo misurato,
  circa 4.150 token in ingresso e 1.940 in uscita per bando con l'estrattore
  vecchio.
- **Passo 3, sottopasso estrattore, tappe a-d**: tabelle `beneficiari_bando`
  e `interventi_bando`, estrattore nuovo, interrogazioni per tipo di
  beneficiario, preselezione senza modello. Piano in
  `docs/piano-estrattore.md`.
- **Scansione completa con l'estrattore nuovo** (11 novembre 2026): 135
  pagine candidate, 28 bandi nuovi salvati; 18 dei 21 bandi in archivio
  riclassificati. Il filtro sull'anno nello slug non ha perso nessun bando
  aperto (0 su 31). Costo circa 5,1 $, contro 1,6–2,9 $ stimati. Corretti
  durante la corsa lo sportello senza prova e gli importi con il punto
  decimale. Misure in `docs/piano-estrattore.md`.
- **Due verifiche a mano** (11 e 12 novembre 2026): bandi scelti a caso
  dalla scansione completa, `docs/verifica-manuale-2026-11-11.csv` e
  `docs/verifica-manuale-2026-11-12.csv`; correzioni in
  `docs/piano-post-scansione.md`.
- **Tappa 5b e scadenze multiple**: tipo `professionista_autonomo`,
  `qualsiasi_soggetto` solo per i requisiti, bandi a finestre o con più
  scadenze (`docs/piano-post-scansione.md`, 5b e 5c).
- **Blocco A, verificatore** (voci 1, 3, 4 e 11 della revisione):
  `docs/piano-verificatore.md`.
- **Recupero**: normalizzazione della domanda, P2 (ricerca ristretta ai
  documenti nominati), insieme di prova di `scripts/diagnostica/prova_recupero.py`
  (`docs/prova-verificatore.md`).
- **P3, stato del bando nei frammenti** (12 novembre 2026): stato calcolato a
  ogni domanda, regola nel prompt, verificato (`src/database/stato_documenti.py`,
  `docs/prova-verificatore.md`).
- **Blocco B, voci 5 e 8** (12 novembre 2026): contributo minimo e massimo
  nella riga del bando, importi non arrotondati; "estratti il" al posto di
  "verificati il" (`docs/revisione-2026-11-12.md`).
- **Piano fonti, tappe 1-5** (12 e 13 novembre 2026): fonti, elenchi e regole
  dal database; elenco "bandi aperti" della montagna; storico dei bandi
  scaduti da meno di 12 mesi; fonte GAL MontagnAppennino (AS01, SRD 14);
  fonte Incentivi Italia dal file open data. `docs/piano-fonti.md`.
- **Correzioni dopo la tappa 4** (12 novembre 2026): interventi riservati
  nella descrizione, enti religiosi come terzo settore, AS01 riestratto
  (`docs/piano-fonti.md`).
- **Istituto per il Credito Sportivo** (13 novembre 2026): fonte nuova con
  elenco spento; Sport Missione Comune 2026 e Cultura Missione Comune 2026
  estratti, mutuo massimo per fascia nel testo dei beneficiari
  (`docs/piano-fonti.md`, quarta e quinta serie).
- **Microzonazione sismica e atto dei parcheggi** (12 novembre 2026): bandi
  sismici del 2026 trovati, tutti scaduti; atto di parcheggi-2026 corretto
  con `correggi_atti` (`docs/piano-fonti.md`, tappa 2).
- **Risposta grezza del modello conservata per ogni estrazione** (13
  novembre 2026): `dati-grezzi/estrazioni/AAAA-MM-GG_<id>.json`, fuori dal
  repository, scritta subito dopo la chiamata e prima dell'interpretazione;
  `estrai` la richiede a ogni chiamante (`src/estrazione/grezzi.py`, README).
  Origine `manuale` per le righe di `beneficiari_bando` inserite a mano
  (prima: neve investimenti 2026, "– Imprese;").
- **Correzioni dalla diagnosi dei falliti** (13 novembre 2026): spazio
  prima di `; , : .` ignorato nel confronto delle frasi (borse di
  mobilità); il soggetto di un beneficiario deve comparire nella sua frase,
  solo per le estrazioni nuove; prompt con la frase come tratto continuo
  della pagina (neve investimenti, provato senza salvare: "– Imprese;").
- **Bandi con dati mancanti** (13 novembre 2026): un bando senza
  beneficiari sulla pagina si salva con i beneficiari vuoti e la frase di
  rimando all'avviso; sezione "Da approfondire" dell'app (solo recenti, al
  più 10); contatti d'ufficio letti dal codice (`src/estrazione/contatti.py`).
  `scripts/manutenzione/aggiungi_contatti.py` provato solo con `--prova`.
  Riepilogo della barra laterale allineato: i bandi da approfondire non
  sono tra gli aperti, si contano a parte, solo i recenti. Contatti
  scritti per 43 bandi su 112 con `aggiungi_contatti --scrivi`, dopo la
  rilettura dell'esito della prova
  (`dati-grezzi/contatti/2026-11-13_prova-contatti.csv`).
- **Ricognizione di ANCI Toscana** (13 novembre 2026): prima misura di
  copertura, 8 bandi su 31 pertinenti in archivio, 8 su 20 sulle fonti già
  acquisite; Sviluppo Toscana come elenco in più (`docs/ricognizione-fonti.md`,
  sezione 8).
- **Router e bandi nominati** (13 novembre 2026): se la domanda nomina un
  bando (titolo, nome proprio o oggetto) il router usa `dettaglio_bando`
  con le parole del titolo, non `bandi_per_tema`. Prima "mercati rionali"
  era cercato come tema e non trovava il bando, classificato "commercio".
  Provato su 5 domande: mercati rionali, parcheggi e Sport Missione Comune
  vanno a `dettaglio_bando` e trovano un solo bando ciascuna; "bandi per il
  commercio" resta `bandi_per_tema`, "bandi aperti per il Comune" resta
  `bandi_aperti_per_ente`.
- **Supabase che non va in pausa** (13 novembre 2026): workflow
  `.github/workflows/tieni_sveglio.yml`, una lettura ogni 3 giorni con
  `scripts/manutenzione/tieni_sveglio.py` (connessione in sola lettura,
  secret `DATABASE_URL` con la stringa del pooler). Primo lancio manuale
  da GitHub riuscito.
- **Domande d'esempio dell'app** (13 novembre 2026): 7 domande per il
  consulente, su due righe (`app/app.py`): bandi aperti e in scadenza per
  il Comune, Sport Missione Comune, imprese turistiche, aziende agricole,
  costo giornaliero dell'avviso per il rafforzamento amministrativo,
  popolazione. Router e interrogazioni provati su ciascuna, senza il
  modello di risposta. Limiti: la domanda sulla popolazione non ha dati
  per l'Unione, solo per i tre comuni; la domanda su Sport Missione
  Comune nomina un bando, ma la risposta sta nei dati del bando, non nei
  frammenti. L'esempio del router passa da "impianti di risalita"
  (nessun bando con quel titolo, il router lo usava anche per le domande
  sulle imprese turistiche) ad "aziende apistiche".
- **Dati ISTAT dei tre comuni** (13 novembre 2026):
  `scripts/manutenzione/carica_istat.py` (`--scarica`, `--prova`,
  `--scrivi`). Popolazione al 1° gennaio 2019-2026 di Abetone Cutigliano,
  Sambuca Pistoiese e San Marcello Piteglio dalla stessa tabella, il
  bilancio demografico mensile di demo.istat.it (2025 e 2026 provvisori);
  indirizzo della pagina e data di scaricamento nella fonte di ogni riga.
  Gli 8 valori di Abetone coincidono con quelli già in archivio; i valori
  2019-2024 coincidono con i file annuali `D7B<anno>.csv.zip`. Superficie
  dei tre comuni dal file ISTAT "Altimetria Comuni al 31 dicembre 2021",
  colonna `AREA_KMQ`. **Dato verificato modificato**: la superficie di
  Abetone Cutigliano passa da 74,94 a 74,99 kmq, per avere i tre comuni
  dallo stesso file; la fonte del 74,94 era solo "ISTAT", senza tabella.
  File scaricati in `data/raw/istat/`, non versionata.
- **Blocco B, voce 6** (13 novembre 2026): `dettaglio_bando` non sceglie
  più a caso tra titoli simili. Fino a 3 bandi il dettaglio di ciascuno,
  oltre un elenco breve; nessun bando, i 5 titoli più simili invece di
  tutti gli identificativi. Provato su "neve" e "Missione Comune" (due
  dettagli ciascuno).
- **Ricerca fuori dal tema e dal titolo** (13 novembre 2026), i due limiti
  emersi dalla prova della voce 6: `bandi_per_tema`, se il tema non trova
  niente, cerca le parole nei titoli e lo dice in testa ("bandi sulla
  conciliazione": i 5 bandi, tutti con tema "sociale"); `dettaglio_bando`,
  se nessun titolo corrisponde, cerca tutte le parole nei beneficiari
  (soggetto, frase, condizioni) e negli interventi, con le stesse regole
  (fino a 3 il dettaglio, oltre l'elenco), e solo dopo i titoli simili
  ("impianti di risalita": i due bandi neve). Limite: il confronto è tra
  parole, non tra significati ("rifugi" trova un bando che nomina le case
  rifugio per le donne vittime di violenza).
- **Blocco B, voce 12** (13 novembre 2026): gli sportelli con la data di
  chiusura nella finestra entrano in `bandi_in_scadenza`, con "a
  sportello, chiude il …, salvo esaurimento delle risorse". La domanda
  d'esempio "Quali bandi per il Comune scadono nei prossimi 30 giorni?"
  passa da 5 a 7 bandi: si aggiungono Sport e Cultura Missione Comune
  (chiusura il 5 dicembre).
- **Recupero dei bandi aperti mancanti** (13 novembre 2026,
  `docs/ricognizione-fonti.md`, sezione 8): Sviluppo Toscana e Ministero
  delle Infrastrutture come fonti, con le pagine indicate a mano
  (l'elenco di Sviluppo Toscana non è ancora acceso); i due bandi neve,
  Punti Digitale Facile, fondo strade MIT per i piccoli comuni. Abetone
  Cutigliano passa da 7 a 9 bandi aperti.
- **Blocco B, voce 14** (13 novembre 2026): README allineato a quello che
  l'app fa oggi. Sezione "In breve" in cima; catalogo dei bandi (fonti,
  interrogazioni, storico, "Da approfondire", contatti); estrazione
  assistita e automatica distinte; limiti aggiornati (Unioni e dati dei
  comuni superati, copertura e ricerca per parole nuovi); misure in una
  sezione a parte, con la seconda prova con il modello. Revisione con lo
  stato di ogni voce chiusa; piani dell'estrattore e post-scansione con i
  rimandi agli esiti.
- **Verificatore, codici ATECO e trattini** (13 novembre 2026, primo dei
  quattro difetti della prova completa dall'app): i codici con i punti
  ("49.34.00", "I 55.1") sono un valore solo, nella risposta e nella
  fonte, invece di numeri sciolti (11 "non trovato" su una risposta
  giusta); i trattini tipografici (U+2010-2013, U+2212) valgono "-" prima
  del confronto. Casi N27-N31 nel collaudo; i 18 casi originali invariati.
- **Popolazione dell'ente nei dati** (13 novembre 2026, secondo difetto):
  a ogni domanda il programma aggiunge il blocco "popolazione dell'ente"
  con l'ultima popolazione ISTAT, anno e fonte (`con_popolazione` in
  `src/chains/rag.py`), citabile e verificato come gli altri dati; niente
  per l'Unione. Provato con il modello: "mutuo massimo in Sport Missione
  Comune" per Abetone sceglie la fascia dei 2 milioni con 1.834 abitanti,
  9 dati verificati su 9. Poi una regola con esempio nel prompt: nel
  confronto, soglia citata con l'etichetta del bando e popolazione con la
  sua, ciascuna dopo il proprio numero (una prova aveva dato rosso per
  "fino a 5.000 abitanti … 1.834 (fonte: [D2])"). Tre prove su "bandi
  aperti" per Abetone: verde, verde, arancione, nessun rosso.
- **Corrispondenza parziale nella ricerca per nome** (13 novembre 2026):
  `dettaglio_bando` dava "non trovo" sul "fondo strade MIT" perché "MIT"
  non è nel titolo. Ora, se nessun titolo contiene tutte le parole e uno
  solo ne manca una (con almeno 3 parole cercate), se ne dà il dettaglio
  con in testa la parola mancante; a pari merito, i titoli simili come
  prima. Il router non mette più in id_bando il nome dell'ente che emette
  il bando (MIT, Regione, GAL, ICS...). Provato con il modello per
  Abetone: risposta corretta, 10 dati verificati su 10.
- **Bandi citati sotto la risposta** (13 novembre 2026): l'app elenca i
  bandi citati con [Dn.k], con titolo e collegamento alla pagina ufficiale
  dal database (`bandi_citati` in `src/database/modelli.py`); il prompt
  di risposta vieta al modello di scrivere indirizzi. Provato su "bandi
  aperti" e "fondo strade" per Abetone: 8 e 1 bandi citati, nessun
  indirizzo nelle risposte.
- **Doppioni tra Incentivi Italia e la Regione** (13 novembre 2026):
  cercati senza modello (titolo, date, indirizzo), 5 coppie confermate
  sulle pagine. Prima le versioni della Regione completate con la frase
  della pagina (`correggi_doppioni_tenuti`: professionisti in tre bandi
  BEI, i due massimali dei minibond tra le spese, tolta una riga
  `cittadini_famiglie` sbagliata); poi `togli_doppioni --scrivi`, con
  confronto campo per campo e controllo delle interrogazioni: tolti 4
  (turismo BEI, EU-Blending 2026, finanziamenti fino a 50 mila, donne
  datori di lavoro). Il minibond (`incentivi-8026`) si era fermato: la
  versione della Regione non aveva i tipi impresa artigiana/commerciale e
  turistica; aggiunti con la frase della pagina (Pmi in forma di società
  di capitali o cooperative, di qualunque settore), poi tolto anche lui:
  5 doppioni tolti. `data/processed/doppioni.csv` è il primo pezzo della
  regola dei due domini (vedi "In coda").
- **Atti di Cultura Missione Comune e del fondo strade MIT** (13 novembre
  2026, quarto difetto della prova completa), con `correggi_atti` e le
  frasi della pagina: Cultura senza atto diventa «Avviso pubblico CULTURA
  MISSIONE COMUNE 2026, con Proroga del termine di presentazione delle
  istanze», come Sport; il fondo strade passa dal nome del file a «Avviso
  pubblico 2026, prot. 26286 del 3 novembre 2026».
- **Numeri di protocollo nel verificatore** (13 novembre 2026): "prot."
  e "protocollo n." valgono come numeri d'atto, come decreti e delibere,
  nelle citazioni, nel testo e nel legame con la data. Prima un protocollo
  con una cifra sbagliata risultava verificato. Casi N32-N35 nel collaudo.

## In corso

Nessun compito in corso: le prossime voci sono quelle della sezione
successiva.

## Prima della demo con il consulente pilota

**Mandare la demo entro il 23 novembre 2026**: dopo scadono i due bandi
neve (16 e 23 novembre), e la domanda d'esempio sulle imprese turistiche
perde i suoi esempi migliori.

- **Prova completa dall'app online** (chiude la voce 10 della revisione,
  `docs/revisione-2026-11-12.md`).
- **Toscana Art Bonus**, da estrarre quando esce l'avviso (dal 1°
  dicembre), dal recupero dei bandi aperti mancanti
  (`docs/ricognizione-fonti.md`, sezione 8).
- **Controllo degli scarti**: un file con le righe da verificare e gli
  scarti definitivi, con titolo, ente e motivo, ordinati mettendo in cima
  quelli che nominano comuni, enti locali, montagna, impianti, sport,
  scuole, turismo, imprese agricole o turistiche. Da includere:
  - le 6 righe di `beneficiari_bando` in archivio la cui frase non nomina
    il soggetto (controllo del 13/11/2026, attivo solo sulle estrazioni
    nuove): "Bando 2026 Pmi" (4 righe, frase "I suddetti soggetti devono
    operare nei settori ammissibili…"), scuole paritarie ("Famiglie" con
    i requisiti del bambino), alta formazione ("Università pubbliche" con
    la frase sul partenariato). Da correggere alla prossima riestrazione
    di quei bandi;
  - `incentivi-2504`: la sua pagina ha i contatti di un polo digitale del
    Friuli Venezia Giulia (IP4FVG); verificare perché è in archivio, se
    la regola territoriale di Incentivi Italia lo lascia passare per
    errore;
  - i bandi con dati mancanti non recenti (pubblicati da più di due anni,
    o con l'anno nel titolo più vecchio dell'anno scorso), che la sezione
    "Da approfondire" dell'app non mostra: es. festival 2021 e 2022,
    rievocazioni 2021.
- **Prova di copertura**: elenco esterno di bandi rilevanti per il
  territorio nel 2026 (schede ANCI, BURT, consulente pilota). La
  ricognizione ANCI è la prima misura.
- **Regola "niente si scarta in silenzio"**: righe da verificare e scarti in
  un elenco che si rilegge a ogni aggiornamento.
- **Insieme di prova dell'estrattore**: dai bandi delle due verifiche a
  mano, con i valori controllati sulla pagina, per misurare quanti campi
  coincidono dopo ogni modifica al prompt o alle regole.
- **Limite di spesa mensile nella console di Anthropic**: si imposta a mano
  nella console, non dal codice (spostata qui dalla coda).
- **Se c'è tempo: Nuova Sabatini, Smart&Start, ISI INAIL verificati a
  mano**, con la frase della pagina come prova: misure nazionali per le
  imprese escluse dalla regola degli sportelli ma ancora attive
  (Incentivi Italia, tappa 5: sportelli senza chiusura aperti da più di
  due anni, 17 righe da verificare).

## Prossimi passi, in ordine

1. **Scheda per bando**: per chi è e per cosa si può usare, divisa per tipo di
   beneficiario, con le clausole citate. Quello che il bando dice e i possibili
   usi proposti dal sistema restano visibilmente separati.
2. **Riepilogo**: bandi nuovi con le loro schede, filtrati sulle sue
   ricerche scritte in un file. Prima mandato a mano, poi automatico.
3. **Aggiornamento almeno una volta a settimana**: GitHub Actions lancia la
   scansione, salva CSV e database, manda il riepilogo. La frequenza non può
   essere più bassa: dalla ricognizione ANCI del 13 novembre 2026, con due
   sole scansioni della Regione (15/09 e 11/11) il bando Pro Loco identità
   locali è stato aperto e chiuso tra l'una e l'altra, e Punti Digitale
   Facile è uscito il giorno stesso della scansione. Oltre ai bandi nuovi,
   si ricontrollano i bandi aperti e quelli chiusi da poco, per le proroghe:
   la riclassificazione dell'11 novembre 2026 ha trovato le risorse
   genetiche forestali prorogate al 13 novembre, mentre l'archivio le dava
   scadute il 30 settembre. Per ogni pagina si conserva un'impronta del
   testo: un bando aperto si riestrae solo se la sua pagina è cambiata,
   così il ricontrollo non costa una nuova estrazione a ogni giro.

   Anche gli scarti "scaduto" di `scansioni` vanno ricontrollati, non
   solo i bandi in archivio. Caso del 12 novembre 2026: "premi annuali
   ad ettaro per mantenere imboschimenti" (SRA28) è registrato come
   "scaduto il 2026-06-30", che è uno scarto definitivo, ma è un bando
   a domanda annuale: il 30 giugno è il termine dell'annualità 2026, e
   le domande si possono presentare fino all'annualità 2029. La pagina
   regionale lo dà "Aperto". Riestratto quel giorno con una chiamata,
   senza salvarlo (`docs/piano-fonti.md`).

   **Requisiti da completare prima di attivarlo** (dettagli nelle voci
   indicate di `docs/revisione-2026-11-12.md`):
   - voce 2: l'estrattore controlla che il valore compaia nella sua prova,
     con il modulo di normalizzazione del blocco A;
   - voce 7: le pagine scadute da poco tornano candidate, per le proroghe;
   - voce 8: le correzioni a mano su `bandi` protette dalla riestrazione;
     anche le righe di `beneficiari_bando` con origine `manuale`, come le
     date `manuale` di `scadenze_bando`: oggi `salva` sostituisce tutte le
     righe dei beneficiari di un bando riestratto, e la riga "– Imprese;"
     di neve investimenti 2026 andrebbe persa;
   - voce 9: nessuna desincronizzazione tra database e CSV (righe scartate
     al caricamento, ricreazione su database esistente, esportazione solo
     a fine corsa);
   - voce 13: test del percorso di `estrai_nuovi` su pagine salvate;
   - voce 15: fonte dei bandi letta dalla tabella `fonti`;
   - controllo periodico, senza modello, degli elenchi "bandi aperti"
     dei programmi (PR FESR, PR FSE+, sviluppo rurale): le pagine che
     hanno in più rispetto all'elenco generale. Il 12 novembre 2026
     erano contenuti per intero nell'elenco generale, e per questo non
     sono stati aggiunti come elenchi (`docs/piano-fonti.md`, tappa 2).
4. **Ricerca per bisogno**: l'utente descrive cosa vuole fare, il sistema cerca
   tra gli interventi ammissibili. Caso di prova: "devo rifare la piazza"
   → bando mercati rionali. (Lo stato del bando nei frammenti è già fatto,
   P3.)

   **PDF dei bandi**: solo bandi aperti, o chiusi da poco se ricorrenti, e
   rivolti ai tipi di beneficiari serviti. Per ogni bando solo il testo
   del bando o dell'avviso; modulistica conservata come collegamento,
   non indicizzata; decreti, graduatorie e rettifiche esclusi salvo
   quelle che cambiano scadenze o requisiti. Scelta degli allegati prima
   con le etichette della pagina. PDF scansionati riconosciuti con la
   densità di testo e segnati "da OCR", non indicizzati in automatico:
   l'OCR sbaglia i numeri, e il verificatore li darebbe per buoni. File
   .pdf.p7m da aprire prima della lettura. Se pagina e testo del bando
   non coincidono, vale il testo del bando.
5. **Privati nell'app**: selettore pubblico/privato e tipo di privato a
   macrogruppi. Insieme, l'abbinamento strutturato tra interventi e tipi
   di beneficiario: oggi la riserva sta solo nel testo della descrizione
   ("Adeguamento e ampliamento della viabilità rurale, solo enti
   pubblici", AS01 del GAL), e un terzo settore che chiede quali
   interventi può fare non riceve un filtro, solo il testo.
6. **Sezione riservata**: accesso, iscrizioni con mail e ricerche salvate su
   Supabase, tasto "aggiorna adesso" che lancia il processo su GitHub,
   segnalazione manuale di un bando. Parte pubblica limitata a 3 domande per
   sessione, con un tetto giornaliero complessivo e un invito a scrivere per
   l'accesso.
7. **Newsletter come segnali**: casella dedicata iscritta alle newsletter di
   Regione, fondazioni e GAL; i link estratti passano dalla verifica sulla
   pagina ufficiale.
8. **Percorso guidato per gli iscritti**: passi definiti dal bando (requisiti,
   documenti, scadenze intermedie, contatti), controllo dei documenti con ogni
   requisito citato. Percorso a passi fissi, non un agente libero.
9. **Docker** per Postgres con pgvector in locale.

## In coda

- Dopo la demo. Altitudine dei tre comuni (minima, massima, del centro)
  dallo stesso file "Altimetria Comuni al 31 dicembre 2021", con
  un'interrogazione per i dati del territorio. Serve alla domanda
  sull'altitudine scartata tra gli esempi.
- Dopo la demo. Tetto giornaliero complessivo di domande, con un contatore
  su Supabase, prima di pubblicare il link dell'app: il limite per
  sessione da solo non basta.
- Dopo la demo. Nota sotto la casella delle domande: le domande vanno a un
  servizio di AI, niente dati personali.
- Prima del post su LinkedIn. Domande fuori ambito: il router le
  riconosce e l'app risponde con una frase fissa, senza chiamare il
  modello di risposta né il recupero.
- Dopo la demo. Post su LinkedIn dopo la risposta del consulente pilota,
  con video o schermate, link al repository e al README.
- Dopo la demo. Registro delle decisioni (`docs/decisioni.md`): una scheda
  per decisione (problema, alternative, misura, scelta, perché, cosa resta
  aperto), scritto per poterlo spiegare a voce.
- Dopo la demo. Controlli automatici su GitHub: `ruff` e `pytest` a ogni
  push.
- Dopo la demo. Fonti di scoperta da valutare, nell'ordine: BURT parte III
  (per misurare la copertura della fonte regionale e recuperare i bandi
  aperti e chiusi tra due scansioni), Uncem, associazioni di categoria
  della montagna, Toscana Notizie, Cesvot, Giovanisì, ANCI nazionale.
  Stessa regola di ANCI Toscana: segnalano, i dati si prendono dalla
  pagina ufficiale.

  Buco ancora aperto: nella misura di copertura del 13/11/2026 mancano
  tutti i 10 bandi di enti nazionali segnalati da ANCI Toscana
  (`docs/ricognizione-fonti.md`, 8.4). Il fondo strade MIT è nel recupero
  prima della demo; degli altri nove, quelli rivolti anche ai comuni sono
  arredi didattici (Istruzione), jazz 2027 (Cultura, autonomie
  territoriali) e Vita & Opportunità (comuni come partner); gli altri sei
  sono per imprese o terzo settore.
- Dopo la demo. Revisione dei test: segnalare quelli che ricopiano il
  codice invece di proteggere un comportamento.
- Dopo la demo. Simulazione senza modello: quanti bandi per "PMI" o
  "imprese" senza settore sono classificati solo come `altra_impresa`, e
  quindi non compaiono nelle ricerche per settore (turistiche, artigiane
  e commerciali, agricole). Caso del 13/11/2026: il minibond.
- Dopo la demo. Regola che riconosce "professionisti" da solo come
  `professionista_autonomo` (oggi solo "liberi professionisti"), da
  provare sui casi in cui la parola indica consulenze e non beneficiari;
  poi il bando IGP (`produzioni-artigianali-e-industriali-…-fa7c57`:
  «le Pmi, inclusi i professionisti, in forma aggregata»).
- Dopo la demo. Regola per i bandi pubblicati su due domini (Regione e
  Sviluppo Toscana, poi BURT e le altre fonti), da scrivere prima di
  accendere l'elenco di Sviluppo Toscana (oggi `attivo` = 0). Caso del
  13/11/2026: Digitale P.A. su sviluppo.toscana.it è lo stesso bando di
  "Contributi agli enti locali per lo sviluppo di progettualità sui dati"
  già in archivio dalla Regione (decreto 22706 del 9/10/2026); con l'elenco
  acceso sarebbero doppioni anche IGP, le due 1.3.2 PMI, PMI turismo e
  Minibond.
  Primo pezzo fatto il 13/11/2026: `data/processed/doppioni.csv`, un file
  per i doppioni tra tutte le fonti (indirizzo, fonte, id tenuto, motivo,
  data, differenze accettate), letto oggi dall'importazione di Incentivi
  Italia; da far leggere anche a Sviluppo Toscana e BURT.
- Dopo la demo. Soglie di popolazione dei bandi (es. comuni fino a 5.000
  abitanti, fondo strade MIT) confrontate con i dati ISTAT del comune:
  oggi la soglia sta solo nelle condizioni dei beneficiari, e il bando
  compare a tutti i comuni.
- Dopo la demo. Campo strutturato per gli importi per fascia di ente (es.
  mutuo massimo di 2, 4 o 6 milioni secondo tipo e dimensione dell'ente,
  Sport e Cultura Missione Comune): oggi la frase della pagina sta nel
  testo dei beneficiari.
- Dopo la demo. Aggiunta di fonti dall'interfaccia, in tre passi:
  l'utente segnala una fonte; il sistema prova da solo robots.txt,
  lettura dell'elenco e due o tre bandi d'esempio, con il costo; una
  persona approva prima che la fonte entri in `fonti.csv`.
- Dopo la demo. Lista di controllo scritta per ogni fonte nuova:
  robots.txt, elenco leggibile, tre bandi verificati a mano sulla
  pagina, costo per bando, regola di chiusura.
- Dopo la demo. Incentivi Italia, link condivisi: oggi una riga con un
  `Link_istituzionale` usato da più righe del file è da verificare a mano
  (43 righe sul file del 12/11/2026). Molte sono misure sorelle sulla
  stessa pagina di bando (sezioni regionali del bando ISI, bandi R&S 1 e
  2, tax credit della stessa sessione). Regola da valutare: il link
  condiviso è ammesso se le righe hanno lo stesso concedente e le stesse
  date (`docs/piano-fonti.md`, tappa 5).
- Elenco dell'Istituto per il Credito Sportivo: se un giorno si attiva
  (oggi `attivo` = 0), la scansione deve rispettare il `Crawl-delay: 2`
  del robots.txt: oggi `estrai_nuovi` aspetta 0,5 s tra i download e 1 s
  tra le estrazioni.
- Zona sismica dei tre comuni: riferimento OPCM 3274/2003 aggiornata dalla DGRT
  421 del 26/05/2014, da verificare sull'allegato e su eventuali aggiornamenti.
- Colonna `montano` nel profilo: i tre comuni sono totalmente montani
  (Delib. CR 10/2025).
- Verificare sulla pagina della Regione il fondo di garanzia energie
  rinnovabili del 2014 (stato e "contributo fino all'80%"). Dopo la
  riclassificazione e' senza scadenza e non a sportello: la pagina non ne
  parla.
- Fuso orario: `date.today()` in 6 punti (DTZ011), mentre altri 2 punti
  usano già `Europe/Rome` (`salva.py`, `grezzi.py`): a ridosso della
  mezzanotte uno stesso salvataggio può avere due date diverse.
- Segnalazioni ruff ISC004 e BLE001 negli script.
- Due xfail di `pulisci`: numeri separati da virgola, intestazione con spazi.
- Regola "imprese senza settore" applicata anche nel codice, non solo nel
  prompt.
- Avvisi sui bandi salvati visibili nell'app (perché una dotazione è vuota).
- Righe di `scansioni` con slug tagliati: da ripulire.
- Link simbolici `.claude/skills` e `.agents/skills` verso `.venv` nel repo.
- Fine riga CRLF/LF.
- Appartenenza dei comuni all'Unione nel profilo dell'ente.
- Dalla scansione completa dell'11 novembre 2026:
  - `COSTO_NON_BANDO` in `estrai_nuovi` da rimisurare su pagine che non
    sono bandi: oggi vale 0,031 $, la media della scansione con bandi e non
    bandi insieme, quindi per eccesso. `COSTO_BANDO` e' 0,061 $, misurato
    sulla riestrazione di 10 bandi del 12 novembre 2026;
  - i bandi in archivio che il modello giudica non bandi restano senza
    `classificato_il` e `riclassifica_bandi` li riesamina a ogni lancio:
    decidere se segnarli o toglierli;
  - le pagine a "scadenza non determinata" (es. ricerca finalizzata 2021 e
    2024) tornano candidate a ogni scansione e si pagano ogni volta;
  - 16 valori vecchi mantenuti nella riclassificazione, da controllare a
    mano (elenco nel rapporto della scansione);
  - i 9 bandi salvati nella prima corsa, prima della correzione degli
    importi con il punto decimale, possono avere importi vuoti.
- `data/db/comune.sqlite` sotto git: compare modificato a ogni ricreazione
  anche con i dati identici. Prima di toglierlo dal repository, l'app deve
  ricrearlo dai CSV all'avvio, perché la demo su Streamlit Cloud lo legge
  dal repository.
- Sicurezza e salute nei luoghi di lavoro 2026: la pagina dice che il bando
  è approvato con decreto 13543 del 15 giugno 2026 e, poco sotto, che testo
  e allegati sono approvati con decreto 13542 dello stesso giorno. In
  archivio c'è 13543: da controllare sul decreto.
- Le correzioni a mano sui campi di `bandi` (atti, note, sportello: script
  `correggi_atti` e `applica_regole_verifica` del 12 novembre 2026) non sono
  protette da una riestrazione futura, a differenza delle date di
  `scadenze_bando` con origine `manuale`. Alla prossima scansione,
  controllare che non siano tornate ai valori di prima.
- Test di equivalenza: un bando di prova per i privati
  (`professionista_autonomo`, `qualsiasi_soggetto` sostituito dalle regole),
  prima del selettore pubblico/privato.
- Perché Chroma ordina meglio di Postgres sulle stesse domande, dato che
  la demo usa Postgres. In `scripts/diagnostica/prova_recupero.py` del
  12 novembre 2026 il costo giornaliero (322,00 €) e i costi indiretti
  sono 1ª su Chroma e 4ª su Postgres. La parte densa dà le stesse
  posizioni sui due motori, quindi la differenza sta nella parte
  lessicale: BM25 in memoria contro `ts_rank_cd` con la domanda in OR e
  le radici delle parole in italiano. Una domanda va in senso opposto (i
  1.904 comuni: 2ª su Postgres, 4ª su Chroma).
- P2, casi rimasti aperti (`docs/prova-verificatore.md`): i contributi dei
  mercati rionali, con parole diverse dal testo, e la domanda su due
  avvisi; il termine di presentazione al limite (8ª su Postgres, 10ª su
  Chroma); la domanda di controllo sulla rendicontazione dei mercati
  rionali, che con P2 scende dalla 5ª alla 7ª su Postgres. Rilanciare
  `scripts/diagnostica/prova_recupero.py` a ogni modifica del recupero o
  dell'archivio.
- Indice HNSW su Postgres e ricerca ristretta a un documento. Su `chunk`
  c'è `chunk_embedding_idx` (HNSW, `hnsw.ef_search` = 40). Con 316
  frammenti il pianificatore sceglie la scansione sequenziale, quindi la
  ricerca densa è esatta (misurato il 12 novembre 2026 con `EXPLAIN
  ANALYZE`). Quando l'archivio crescerà con i PDF dei bandi, potrà passare
  all'indice: il filtro sul documento si applica dopo i 40 candidati
  dell'indice, e la ricerca ristretta di P2 resta con pochi frammenti o
  nessuno. Forzando l'indice oggi, 6 ricerche ristrette su 25 restituiscono
  meno righe (3 invece di 20 per la quota di ciascuna Area interna).
  Rimedi da valutare allora: `hnsw.iterative_scan` di pgvector 0.8,
  `ef_search` più alto per le ricerche ristrette, o ricerca esatta quando
  c'è il filtro.
- Dalla ricognizione delle fonti del 12 novembre 2026
  (`docs/ricognizione-fonti.md`):
  - nuova fonte candidata: le sezioni "Avvisi" dei siti istituzionali dei
    tre comuni, che pubblicano bandi per le imprese (es. contributi dal
    Fondo per i comuni delle aree interne). Prima di tutto verificare il
    robots.txt di ciascun dominio;
  - nella tabella `enti`, valutare la partita IVA come secondo
    identificativo degli enti (nei dati PNRR compaiono con l'una o con
    l'altra).

## Decisioni prese

- **Si acquisiscono tutti i bandi**, anche quelli per i privati, con i tipi di
  beneficiari e le condizioni. Si filtra al momento della domanda.
- **Lo stato di un bando si calcola dalla scadenza**, mai dall'etichetta del
  sito.
- **I bandi scaduti non si cancellano**: servono a riconoscere le proroghe, i
  bandi ricorrenti e a evitare di riestrarli.
- **Nessuna lettura automatica dei social**, e nessun aggiramento di
  `robots.txt` o di blocchi anti-bot.
- **Apify rimandato**: le fonti attuali sono HTML leggibile. Si rivaluta solo
  se una fonte necessaria non lo è.
- **Smistamento con un secondo modello rimandato**: il risparmio è piccolo
  rispetto alla complessità.
- **Repository pubblico** come portfolio. Nessun dato di persone entra mai nel
  repository: email, ricerche e documenti degli utenti stanno su Supabase.
- **La combinazione di bandi non la decide il sistema**: mostra la clausola di
  cumulabilità di ciascuno, la valutazione resta a chi segue la domanda.
- **ANCI Toscana e le altre fonti di scoperta segnalano, non sono fonti**:
  i dati si prendono dalla pagina ufficiale dell'ente; le schede ANCI non
  si salvano e non si citano.
