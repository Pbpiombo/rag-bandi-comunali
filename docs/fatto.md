# Fatto

Lavoro chiuso, spostato da `docs/roadmap.md` il 18 novembre 2026. Le voci
restano come erano scritte nella roadmap; i rimandi a "In coda", "Prossimi
passi" o "Dopo la demo" ora puntano a `docs/coda.md`.

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
  Cutigliano passa da 6 a 8 bandi aperti (prima scritto "da 7 a 9";
  corretto dopo il conteggio del 15/11/2026 sulle copie del database
  prima e dopo il commit 72c3d4e: i bandi neve non sono per i Comuni).
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

## Chiuse dalla lista "Prima della demo con il consulente pilota"

Verificate il 18 novembre 2026 sui documenti e sul codice; sotto ogni voce
la prova della chiusura.

- **Prova completa dall'app online** (chiude la voce 10 della revisione,
  `docs/revisione-2026-11-12.md`).
  Chiusa: prova fatta il 14 novembre 2026; i difetti emersi sono in
  `docs/coda.md`, "Difetti dalla prova completa del 14 novembre".
- **"Da approfondire" uguale per ogni domanda** (correzione C3,
  `docs/piano-correzioni-lotto1.md`; era la voce 3 di "Dopo la demo:
  dalla prova completa del 14 novembre"): la cooperazione internazionale
  compare anche per le imprese turistiche e le aziende agricole. Deve
  seguire il tema o il beneficiario della domanda.
  Chiusa il 14 novembre 2026, opzione 1 (commit `f081f14`,
  `docs/piano-correzioni-lotto1.md`, correzione C3); l'opzione 4 è in
  `docs/coda.md`, "In coda".
- **Il modello descrive i suoi meccanismi** (correzione C1,
  `docs/piano-correzioni-lotto1.md`; era la voce 6 della stessa lista):
  "occorrerebbe interrogare nuovamente l'archivio con beneficiario...";
  una riga nel prompt.
  Chiusa il 14 novembre 2026 (commit `f081f14`), completata da D3 il 15
  novembre con un residuo (`docs/piano-correzioni-lotto1.md`, D3 ed esito
  della misura ristretta).
- **Versioni delle dipendenze fissate**: deciso il 15 novembre 2026, al
  contrario della prima idea, di fissare le versioni **locali**, già
  provate (1044 test e misura ristretta), non quelle online. In
  `requirements.txt` con `==` tutte le dipendenze dirette, più `anthropic`
  (1.5.0; online girava 2.8.0, l'unico cambio maggiore rilevante per
  l'app) e `langchain-huggingface`; `torch` non fissato. Python online
  invariato (3.14.10). Coerenza verificata con pip senza installare, anche
  per Linux con Python 3.14. Da controllare al primo avvio dopo il push:
  se l'installazione su Streamlit Cloud fallisce, `git revert` e Python
  3.13 con una nuova pubblicazione. Tabella e motivi nel piano
  (`docs/piano-correzioni-lotto1.md`, "Confronto delle versioni prima del
  push").
  Chiusa il 15 novembre 2026 (commit `ec2a5ed`).
- **Pannello, conteggio dei verificati gonfiato dalle citazioni
  ripetute** (era la voce 3 di "Dopo la demo: dalla prova completa del 14
  novembre"): lo stesso decreto contato 4 volte; nell'app online del
  15/11/2026, "Quali bandi sono aperti per il Comune?" per San Marcello
  Piteglio dà 50 verificati con "24316" ripetuto 4 volte. Mostrare e
  contare una volta ogni coppia valore-fonte, con "×n" accanto alle voci
  ripetute; verificatore e file della prova invariati. Resta da valutare,
  dopo la demo, una forma di citazione più breve nel prompt, con una
  misura prima e dopo.
  Chiusa il 15 novembre 2026 (commit `694936f`, `app/app.py`, riga
  "×n" del pannello); la citazione più breve resta da valutare.

## Fatti il 18 novembre 2026

Spostato da `docs/roadmap.md`, "Stato", il 18/11/2026.

- Fatti il 18/11/2026, senza modello: diagnosi delle attese a tre
  categorie, archivio, recupero, esclusione
  (`scripts/diagnostica/diagnosi_attese.py`); revisione esterna dei prompt
  (`docs/revisione-prompt-2026-11-18.md`); schede di etichettatura con la
  tabella "Bandi ricorrenti" (`scripts/diagnostica/schede_etichette.py`);
  studio delle fonti (`docs/piano-fonti-burt-ministeri.md`).
- **Passo 0, parti (a) e (b)** (18/11/2026, senza modello): data fissa
  con `data_fissata`, che vale anche in `src.chains.rag`; SQLite ricreato
  da una cartella di CSV con `crea_da_csv`, mai in `data/db`, e
  `connetti` puntato lì con `archivio_da`; opzioni `--data` e
  `--archivio` di `prova_insieme`, scritte in `meta.json` e rilette
  dalla ripresa (commit `e8509d1`). `diagnosi_attese` legge l'archivio
  scritto nel `meta.json`, ne controlla l'impronta e si ferma se la
  cartella manca o è cambiata, senza ripiegare su `comune.sqlite`.
  Test in `tests/test_misure_congelate.py`. Procedura della copia
  congelata in `docs/piano-insieme-prova.md`, "Regola delle misure".
- **Passo 2a** (18/11/2026, senza modello): tre correzioni a mano in
  `bandi.csv`. Filiera SMART (incentivi-4804): url della pagina della
  Regione, scadenza 2026-04-30. Edizione precedente del Bando 2026 Pmi
  EU-Blending (incentivi-3662, non un doppione dell'edizione 2026): url
  della pagina della Regione, scadenza 2026-04-30. Fondo di garanzia
  energie rinnovabili: scadenza 2021-12-31 dal decreto dirigenziale 2649
  del 27/02/2018, `verificato_il` invariato. I due indirizzi BURT
  sostituiti sono in `doppioni.csv`, perché l'importazione da Incentivi
  Italia non li salvi di nuovo. `bilancio.csv` e `turismo.csv` creati con
  la sola intestazione, così `crea_da_csv` trova tutti i CSV. Dopo la
  ricreazione del database: 112 righe in `bandi`, aperti al 16/11 da 54 a
  51; Abetone Cutigliano 7, 3 e 1 al 16/11, 1/12 e 6/12, invariati.
- **Impronta indipendente dalle fine riga** (18/11/2026, senza modello):
  `impronta_csv` calcola l'impronta sulle righe lette con `csv.reader`,
  non sui byte, con `versione_impronta` 2 dentro l'impronta; un meta
  senza versione è "in formato vecchio, non confrontabile" in
  `prova_insieme` e `diagnosi_attese` (con `archivio`, errore). Motivo:
  `core.autocrlf=true` su questa macchina, nessun `.gitattributes`; git
  riscrive le fine riga al checkout, anche dentro i campi. `esporta_csv`
  sostituisce gli a-capo dentro i campi con uno spazio, nel CSV e nel
  database. Tolto l'unico a-capo nei CSV: `scadenza_nota` di
  incentivi-8581. L'impronta di `data/processed` è la stessa prima e
  dopo un checkout simulato. Test in `tests/test_misure_congelate.py` e
  `tests/test_schema.py`.

## Fatti il 19 novembre 2026

- **Etichette dell'insieme di prova** (19/11/2026): 990 etichette su 50
  domande, da due modelli con un arbitro e revisione a mano di 96 righe
  dei Comuni. In `docs/piano-insieme-prova.md`, "Come sono state fatte le etichette".
- **Passo 17, testo di ricerca per bando** (19/11/2026, senza modello):
  `data/processed/testo_ricerca.csv`, una riga per bando, costruita da
  `scripts/manutenzione/crea_testo_ricerca.py` (`--file` il catalogo,
  `--controlla` per confrontare senza scrivere) con
  `src/ordinamento/testo_ricerca.py`. Testo: titolo; interventi in ordine
  di numero, descrizione e frase (la frase si omette se uguale alla
  descrizione); per Incentivi Italia `Descrizione`, `Obiettivo_Finalita`
  e `Settore_Attivita` di `OpenData_Incentivi.csv` del 2026-11-12;
  `Forma_agevolazione` no. Ogni riga ha la fonte di ogni parte e, per il
  catalogo, licenza CC BY 4.0 e data del file. Il file non si carica in
  SQLite (`CSV_FUORI_DATABASE` in `src/database/schema.py`), quindi
  nessuna interrogazione del repertorio lo legge; entra nell'impronta e
  nella copia congelata. Errore, senza file parziale, se il catalogo
  manca, ha una data diversa da quella nella fonte dei bandi o non
  contiene un bando. Stesso ingresso, stesso file byte per byte. Esito:
  112 bandi su 112 con un testo, tutti i 51 aperti al 16/11 compresi; 58
  con interventi (166, 590, 3686 caratteri: minimo, mediana, massimo), 49
  di Incentivi Italia (408, 1602, 7561), 5 con il solo titolo (26, 76,
  130). Test in `tests/test_testo_ricerca.py`.
- **Passo 19, compiti 19a e 19b: elenco e PDF degli avvisi della prima
  prova** (19/11/2026, senza modello): 12 bandi (immobili-emergenza-abitativa-2026 escluso, è
  un non_bando). Script `scripts/ingestione/elenco_pdf_bandi.py` in tre
  fasi (`--robots`, `--pagine`, `--file`), lettore
  `src/estrazione/lettore_siti.py`: robots.txt per nome del programma
  secondo RFC 9309, intestazione che dichiara il progetto, pause
  (Crawl-delay o 5 s), tentativi per errori temporanei e 429, rifiuti che
  fermano l'host, cache su disco, registro `richieste.csv`. Eccezione al
  robots.txt per i PDF degli avvisi (decisione del 19/11/2026, CLAUDE.md
  "Lettura dei siti"): 7 file del Credito Sportivo. Link agli atti della
  Regione su www301 (`bancadati/atti/Contenuto.xml`, nome da `nomeFile`)
  e `/documents/d/…-pdf`; www301 non ha un robots.txt (pagina HTML
  d'errore, registrata come assente). Classi: avviso, consolidato,
  proroga, modulistica, allegato, atto, da decidere, altro; versione più
  recente per data del decreto nel nome del file. Riconoscimento
  dell'avviso dalle sezioni del testo (beneficiari, spese ammissibili,
  criteri, cumulo, modalità di presentazione), soglie provvisorie: 3 per
  i link avviso o consolidato, 4 per gli altri e mai con testo da
  rivedere. Esito: 42 richieste in tutto (4 robots.txt, 12 pagine, 1
  robots.txt di www301, 25 file), nessun errore né rifiuto; avviso
  riconosciuto in 10 bandi su 12 (apistici in quattro parti); nessun
  avviso per il fondo strade (PDF del MIT con 2 sezioni) e per
  incentivi-8659 (nessun avviso tra i link della pagina). File ed elenco
  in `dati-grezzi/avvisi/2026-11-19/`, fuori dal repository. Test in
  `tests/test_lettore_siti.py`, `test_robots_rfc.py`,
  `test_robots_html.py`, `test_pdf_bando.py`, `test_documenti_regione.py`,
  `test_versioni_avviso.py`, `test_elenco_pdf_bandi.py`,
  `test_elenco_versioni.py`, `test_scelta_bandi.py`,
  `test_soglie_senza_rete.py`. CLAUDE.md: il principio 'Lettura dei siti'
  è stato riscritto il 19/11/2026 (le pagine rispettano il robots.txt; i
  PDF degli avvisi si scaricano una volta anche se vietati, quando la
  pagina del bando è consentita; un rifiuto del sito non si aggira mai).
- **Copia degli elenchi e scarti nel riepilogo** (19 novembre 2026, dalla
  diagnosi di Art Bonus e rievocazioni 2026): `estrai_nuovi` e
  `scopri_bandi` conservano ogni elenco letto in
  `dati-grezzi/elenchi/<data>/`, HTML e CSV delle voci e degli scartati,
  anche con `--prova`; il riepilogo riporta voci, totale dichiarato ("!!
  totale non letto !!" se non si riconosce), un avviso vicino a `delta` o
  `_per_page`, e i collegamenti `/-/` scartati da `schema_link` e da
  `esclusi`, con l'indirizzo (`src/estrazione/elenco.py`).
- **Fondo nazionale rievocazione storica 2027 inserito a mano** (19
  novembre 2026, dal riscontro del consulente pilota; `coda.md`,
  "Riscontro del consulente pilota e fonti"). Fonte nuova
  `ministero-cultura-spettacolo` in `fonti.csv` (Direzione generale
  Spettacolo, spettacolo.cultura.gov.it), senza riga in `elenchi.csv`:
  elenco spento, come per il MIT. Database ricreato dai CSV dopo la copia
  di sicurezza in `dati-grezzi/backup/`. La pagina è stata letta con
  `lettore_siti`, non con `estrai_bando`, che non legge il robots.txt e
  si presenta come un browser: 2 richieste di rete (robots.txt, che vieta
  solo `/wp-admin/`, e la pagina, 200, 103.939 byte), con l'intestazione
  del progetto; HTML, testo ritagliato e `richieste.csv` in
  `dati-grezzi/manuali/2026-11-19/`. Poi `estrai_bando` sul testo salvato
  (seconda forma, senza rete), id `fondo-rievocazione-storica-2027`: 1
  chiamata al modello (claude-sonnet-5), costo stimato 0,06 $
  (`COSTO_BANDO`, non misurato). Confronto campo per campo con i valori
  letti a mano: titolo ed ente tenuti come estratti (l'intestazione della
  pagina; "Ministero della Cultura - Direzione generale Spettacolo"); 0
  interventi e 0 scadenze multiple, come atteso. Due correzioni con
  `scripts/manutenzione/correggi_da_testo.py` (nuovo: frasi cercate nel
  testo già salvato, nessuna rete, corregge solo se il valore in archivio
  è ancora quello atteso, `--prova`, CSV aggiornati alla fine; test in
  `tests/test_correggi_da_testo.py`): `pubblicato_il` da 2025-03-20 (la
  data del decreto) a 2026-11-03 con origine `pubblicazione`, prova "3
  Novembre 2026"; soggetto della riga `altro_ente_pubblico` da "Enti
  locali" a "soggetti pubblici", origine `manuale`, prova la frase dei
  beneficiari della pagina. Testo di ricerca rigenerato (113 bandi,
  `--controlla`: aggiornato). Archivio: 113 bandi da 7 fonti.

## Fatti il 20 novembre 2026

- **Passo 19, compito 19c: PDF degli avvisi nel Chroma locale** (chiuso
  il 20/11/2026, senza modello). Quattro parti:
  - **19c-1, pulizia del testo** (`src/ingestion/avvisi.py`; opzione
    `ricucitura` di `pulisci` e `spezza` in `src/ingestion/testo.py`).
    Ricucitura "prudente" dei numeri: si uniscono solo gli anni spezzati
    e i numeri seguiti da /anno, perché con la ricucitura di sempre le
    celle vicine di una tabella si fondevano ("B1 40.000,00" diventava
    "B140.000,00"). Senza l'opzione `pulisci` resta quella di sempre: 0
    pagine diverse su 1010. Righe ripetute in più di metà delle pagine,
    con le soglie di `pdf_bando`. Contatti di persone: email nominative,
    telefoni sulla riga di una persona, nomi dopo le formule del
    responsabile del procedimento; restano PEC, caselle d'ufficio, numeri
    verdi e codici d'impresa. Nei 16 file 7 sostituzioni: 5 nomi e 2
    caselle d'ufficio che la regola non riconosce, tolte lo stesso.
    Parole spezzate a fine riga ricucite solo tra lettere minuscole; negli
    indirizzi web il trattino resta. Test in `tests/test_avvisi_pulizia.py`
    e `tests/test_avvisi_indirizzi.py`.
  - **19c-2, registro dei documenti** (`scripts/ingestione/registra_avvisi.py`,
    `data/processed/documenti_bandi.csv`, tra i `CSV_FUORI_DATABASE`). Una
    riga per impronta del file; più `id_bando` nella stessa cella, separati
    da "|". 25 righe: 17 con uso "frammenti" (332 pagine) e 8 solo nel
    registro (allegati, l'elenco dei codici ATECO comune ai due bandi PMI,
    la presentazione di incentivi-8659). Si genera con `--data 2026-11-19
    --data 2026-11-20`; aggiungendo una cartella le righe già presenti
    restano identiche byte per byte. Decisioni a mano nello script, ognuna
    con motivo e data. L'atto viene dal nome del file oppure è verificato
    pezzo per pezzo alla sua fonte: il titolo della prima pagina (testo
    coordinato delle risorse genetiche); la data nel testo del file, a
    qualunque pagina, e il numero di repertorio nel testo del link sulla
    pagina del bando (decreto delle rievocazioni). Mai da
    `bandi.riferimento_atto`. Test in `tests/test_registra_avvisi.py`,
    `tests/test_registra_avvisi_atti.py` e
    `tests/test_registro_piu_cartelle.py`.
  - **19c-3, caricamento** (`scripts/ingestione/carica_avvisi.py`). Solo
    Chroma, nessun import di Postgres; rete spenta per le librerie
    (`HF_HUB_OFFLINE`, `TRANSFORMERS_OFFLINE`, `ANONYMIZED_TELEMETRY`).
    Id `sha256[:16]::i`: prima di scrivere un file si tolgono i suoi
    frammenti, e il rilancio non crea doppioni. Metadati da `bandi` e dal
    registro, nessuna scadenza né stato; l'intestazione del frammento non
    entra nel testo. Misure per il 19d nei metadati: `token`, `car_visti`,
    `tabella_probabile`. Controllo dei numeri: ogni numero di un frammento
    deve stare nel testo grezzo della stessa pagina; 0 non trovati, 4
    "ricuciti alla barra" (spazi attorno a "/" nel PDF del testo
    coordinato) elencati a parte. Regola delle premesse: il testo prima
    della prima riga DECRETA non si carica. Opzioni `--prova`, `--solo`,
    `--togli-scaduti` con `--giorni` (predefinito 365); senza l'opzione
    non si toglie nulla. Test in `tests/test_carica_avvisi.py` e
    `tests/test_premesse.py`.
  - **19c-4, decreto del fondo rievocazioni** (D.M. 20 marzo 2025, rep. n.
    75). 2 richieste di rete, con l'intestazione del progetto: il
    robots.txt, che consente il file, e il PDF. Pagina del bando copiata
    da quella salvata il 19/11; tutto in `dati-grezzi/avvisi/2026-11-20/`.
    6 pagine con testo; premesse tolte fino alla riga DECRETA di pagina 2
    (3.491 caratteri); 15 frammenti. Il bando si sceglie con
    `BANDI_AGGIUNTI` di `elenco_pdf_bandi`, solo con `--bando`.
  - Stato: 17 file, 871 frammenti degli avvisi nel Chroma locale, 1187 in
    tutto con i 316 dei documenti di sempre, la cui impronta (id e testo)
    è rimasta la stessa. Copie di sicurezza in
    `dati-grezzi/backup/chroma-2026-11-20-prima-avvisi/` e
    `dati-grezzi/backup/chroma-2026-11-20-prima-decreto/`. Postgres non
    toccato.
- **Controllo meccanico del foglio dei fatti** (20/11/2026,
  `scripts/diagnostica/controlla_fatti.py`, test in
  `tests/test_controlla_fatti.py`). 81 fatti su 11 bandi, 97 pezzi: 81
  trovati nella pagina dichiarata (13 alla lettera, 54 normalizzati, 14
  solo togliendo gli spazi), 0 in altra pagina, 0 in altro bando, 0
  assenti. Esito in `dati-grezzi/prova/fatti_controllo_2026-11-20.csv`.
  Il foglio è descritto in `docs/piano-insieme-prova.md`, "Foglio dei
  fatti".
  Secondo foglio (`dati-grezzi/fatti_pdf_modello_2_2026-11-20.xlsx`, non
  modificato): 114 fatti su 11 bandi, 140 pezzi; 114 trovati nella pagina
  dichiarata (12 alla lettera, 90 normalizzati, 12 solo senza spazi), 0
  in altra pagina, 0 in altro allegato, 0 in altro bando, 0 assenti, 0
  gemelli diversi dal dichiarato; 140 pezzi interi in un frammento, 59
  nella parte vista a 128 token; 23 righe di tabella, tutte con le celle
  in un solo frammento. La lettura della nota degli apistici accetta ora
  anche la forma "Azione B1, Allegato A1, par. …". Nuova opzione
  `--confronta` (coincidenze con un altro foglio, al livello senza
  spazi): 4 righe del secondo foglio somigliano a una del primo, tutte
  frasi gemelle e nessuna copia (18 con la 18, pezzo identico; 90 con la
  70, 93 e 98 con la 67, somiglianza tra 0,97 e 0,99). Esito in
  `dati-grezzi/prova/fatti_controllo_2_2026-11-20.csv`.
- **Passo 19d, divisione dei fatti in taratura e controllo** (20/11/2026,
  prima di ogni misura; `scripts/diagnostica/misura_recupero_avvisi.py`,
  `--dividi` e `--dividi-secondo`, test in
  `tests/test_misura_recupero_avvisi.py`). Divisione per bando, a caso
  con seme scritto nel codice; si prende la prima proposta, su al più
  5.000, che rispetta tutte le regole:
  - in ogni bando e nei totali le metà differiscono al più di un fatto,
    e così le frasi gemelle;
  - le frasi identiche (livello senza spazi) stanno nella stessa metà;
    il gruppo 21-23-24 (Cultura e Sport) è fissato a mano;
  - differenze massime tra le metà: righe di tabella 1, risposte in più
    pezzi 1, domande "semplice" 3, domande "caso" 3, fatti con tutti i
    pezzi nella parte vista (`pezzi_visti`) 2.
  Primo foglio: seme `1920261120`, tentativo 1229; 40 fatti in taratura
  e 41 in controllo; `dati-grezzi/prova/fatti_divisione_2026-11-20.csv`,
  sha256 `c7180d2d953d652ab0c80aab13a0ade97f0fa8b5a691fbb96bd1171cd64c1952`.
  Una prima divisione senza le differenze massime (sha256 `2441f9b8…`)
  è stata cancellata e rifatta prima di ogni misura, perché le metà non
  erano equilibrate per registro, tabelle e risposte in più pezzi.
  Secondo foglio: seme `220261120` (`SEME_2`), tentativo 2748; 57 e 57;
  `dati-grezzi/prova/fatti_divisione_2_2026-11-20.csv`, sha256
  `4c70a94d6be4de54d24f3a3414dfcadd4d6ef280ca0e106d4e2f485b1475b173`. La
  divisione del primo foglio resta fissa: le righe del secondo che
  somigliano a una del primo vanno nella sua metà (18, 93 e 98 in
  taratura, 90 in controllo), letta solo per quelle righe dopo il
  controllo dell'impronta. Le tre coppie quasi uguali interne al secondo
  foglio (62 e 77, 93 e 98, 99 e 103) stanno nella stessa metà, per
  analogia con la regola delle frasi identiche. Nessun fatto escluso.
  Totale dei due fogli: 195 fatti, 97 in taratura e 98 in controllo
  (semplice 37 e 37, caso 60 e 61, tabella 20 e 20, più pezzi 19 e 19,
  tutti i pezzi nella parte vista 36 e 34, frasi gemelle 19 e 19).
  Rilanciati, i due comandi non riscrivono i file e dicono se la
  divisione rifatta coincide.
- **Passo 19d, script di misura del recupero sugli avvisi** (20/11/2026,
  stesso script, senza modello di linguaggio e senza Postgres). Legge la
  divisione, ne controlla l'impronta e misura solo la taratura: i fatti
  di controllo non si leggono senza `--controllo`, mai usato finora.
  - Condizione A: il percorso dell'app,
    `recupera(avvolgi(RecuperoIbrido), domanda, k)`. Condizione B
    (`RecuperoMisura`): ricerca per significato e per parole sui soli
    frammenti del bando del fatto, con la domanda ripulita da
    `ripulisci_domanda` con le parole del titolo del bando; Bi è la
    definizione della prima misura, con la domanda intera.
  - Un fatto è trovato se ogni pezzo sta, al livello senza spazi, in un
    frammento del bando giusto tra i primi k (per gli apistici,
    dell'allegato giusto). Per ogni fatto non trovato il rapporto dà la
    causa: pezzo fuori dalla parte vista, pezzo spezzato tra frammenti,
    frammento giusto oltre i primi k con la posizione fino a 50, gemello
    al posto del giusto.
  - Varianti in copie di Chroma sotto `dati-grezzi/prova/19d/`, mai nel
    Chroma vero, di cui si confrontano le impronte prima e dopo ogni
    misura: `--variante` (limite di token, intestazione nel vettore,
    frammenti più corti), `--griglia` (ampiezza e k), `--apistici` (nome
    dell'azione), `--riepilogo`.
  - Misura esatta e ripetibile (`--prepara-vettori`, `--esatta`):
    vettori e metadati letti dalla copia, prodotto scalare su tutti i
    frammenti, pari merito ordinati per id; tre processi su v0 danno gli
    stessi elenchi posizione per posizione. `--modello` per gli altri
    modelli di embedding, `--peso` per memoria e tempi.
  - Rete vietata durante le misure; l'unica eccezione autorizzata è
    stata il download dei due modelli e5 da huggingface.co.
  - `src/ingestion/testo.py`: parametri facoltativi `dimensione` e
    `sovrapposizione` di `spezza`, con i valori di sempre come
    predefiniti; il caricamento ridà gli stessi 871 frammenti con la
    stessa impronta.
  - Risultati e stato delle strade in `docs/coda.md`, "Passo 19d".
- **Passo 19d, nome dell'azione degli apistici nel registro** (21/11/2026,
  commit b2e3d42). Colonna `parte` di `data/processed/documenti_bandi.csv`
  per i quattro allegati del decreto 14025, dal titolo a pagina 1
  (`scripts/ingestione/registra_avvisi.py`); misura sui 97 fatti e
  decisione di non metterlo nel recupero in `docs/coda.md`, "Passo 19d",
  punto 5.
- **Passo 19d, contesto per frammento: script e controlli** (21/11/2026,
  commit 72c269c, f7498e7, 4c58a3a, a8ef955). Nessuna chiamata al modello
  nei test.
  - `scripts/diagnostica/genera_contesti.py`: un documento alla volta, la
    prima chiamata scrive la cache e solo dopo partono le altre; una riga
    per frammento in `dati-grezzi/prova/19d/contesto/`, ripresa senza
    rifare; tetto di spesa cumulativo; arresto se dopo la seconda chiamata
    di un documento lungo i token letti dalla cache sono zero; un
    contesto troncato si rifà una volta; `--prova --file` su un file a
    scelta; `--controlla` per i controlli senza chiamate.
  - Riga BANDO composta dal codice dal registro; righe DOVE, ARGOMENTO,
    SERVE A, PAROLE dal modello; ARGOMENTO normalizzato dal codice con
    l'elenco chiuso e le forme vicine scritte a mano, con la riga del
    modello conservata.
  - Controlli: numeri e date non nel frammento, riferimenti di struttura
    della riga DOVE, bando gemello (segni scritti a mano verificati sul
    proprio documento e segni automatici verificati sulla radice), forma.
  - `scripts/diagnostica/misura_recupero_avvisi.py`: configurazioni c-0,
    c-R, c-L, c-LR, c-LVR con il riordinatore piccolo, righe del contesto
    tolte una alla volta, 30 domande scritte a mano
    (`--prepara-domande-a-mano`, `--domande-a-mano`), etichetta di
    ARGOMENTO contro il tipo del fatto, rapporto con le regole di adozione.
  - Domande a mano (21-22/11/2026): `--prepara-domande-a-mano-2` scrive
    `domande_a_mano_2.csv`, altri 30 fatti di taratura con un seme
    diverso, nessuno del primo file, stessa esclusione del fondo strade;
    `--prepara-domande-a-mano-3` scrive `domande_a_mano_3.csv`, tutti i
    fatti di taratura rimanenti (33). `--contesto-domande-a-mano`
    riscrive il secondo e il terzo, solo se nessuna domanda è compilata,
    con file, pagina, testo prima e dopo la frase (circa 400 caratteri
    dal testo pulito) e la colonna "spiegata", più una copia .xlsx con
    il testo a capo. Con `--domande-a-mano` la misura legge i file
    insieme (la copia .xlsx se c'è, altrimenti il .csv, ignorando le
    colonne in più), salta con un avviso le righe con la domanda vuota e
    si ferma se un fatto compare due volte.
  - Generazioni, prova e regole in `docs/coda.md`, "Passo 19d", punto 13.
- **Passo 19d, misure del 22/11/2026** (codice nei commit bd09fcc e
  3f50519; rapporti in `dati-grezzi/prova/19d/contesto/`). Nessuna
  chiamata al modello di linguaggio, nessuna rete, controllo non letto.
  - Domande a mano: c-0 e c-LR con tutte le righe sulle 92 domande dei
    tre file, A e B, k=10 e k=15 (`misura_mano_22-11.txt`; esito in
    `docs/coda.md`, "Passo 19d", punto 13, voce 11). Comandi:
    `python -m scripts.diagnostica.misura_recupero_avvisi --contesto c-0 --domande-a-mano`
    e `--contesto c-LR --righe tutte --domande-a-mano`. Sezione 6 del
    rapporto del contesto (prova principale, mancati da tutte e due, dati
    secondari) calcolata con `righe_domande_a_mano`.
  - Configurazioni T, tutti i frammenti del bando al riordinatore in B:
    `--contesto T-0` e `--contesto T-R --righe tutte`, sui fogli e con
    `--domande-a-mano`; `--rapporto-T` scrive `rapporto_T_taratura.txt`
    con la regola della voce 12, i mancati da tutte, presi e persi, i
    tempi per domanda e per bando (`misura_T_22-11.txt`; esito alla voce
    13). Il json della misura ha ora il massimo del tempo per domanda e
    i tempi per bando.
  - Letture in sola lettura, senza scrivere misure:
    `mancati_mano_22-11.txt` (12 domande a mano mancate da c-0 e c-LR) e
    `mancati_da_tutte_22-11.txt` (12 domande mancate da tutte e quattro
    le configurazioni, con frammento giusto e primi tre per
    configurazione; ordine rifatto con lo stesso codice e posizioni
    uguali a quelle delle misure in 48 casi su 48). Lettura nella voce 14.
- **Passo 19d, apertura della metà di controllo** (23/11/2026; esito in
  `docs/coda.md`, "Passo 19d", punto 13, voce 20).
  - Decisione 1: c-LR tutte sostituisce c-0 (fogli, B, k=10, +15/-3,
    p 0,008; i quattro punti passano).
  - Decisione 2: 77 su 98 (78,6%), sotto l'85%: il passo si chiude con
    gli avvisi in produzione solo con il filtro per bando e il "non lo
    trovo".
- **Passo 19d chiuso** (23/11/2026), sotto soglia secondo la regola
  della voce 19 (`docs/coda.md`, "Passo 19d", punto 13). c-LR tutte è la
  configurazione degli avvisi; avvisi in produzione solo con il filtro
  per bando e il "non lo trovo"; numero da citare 77 su 98 (78,6%), B,
  k=10, metà di controllo. Il seguito è il passo 19e (roadmap).
  - Lettura a mano dei 28 mancati di c-LR in B a k=10 (voce 21), sul
    file `dati-grezzi/prova/19d/contesto/mancati_controllo_23-11.txt`,
    scritto da `mancati_controllo.py` (fuori dal repository, sola
    lettura, ordine rifatto con le funzioni della misura; posizioni
    uguali a quelle delle misure in 58 casi su 58). Revisione esterna
    alla cieca: stessa classe in 17 casi su 28.

## Spostato dalla roadmap il 23 novembre 2026

Testi tolti da `docs/roadmap.md` alla chiusura del 19d, parola per
parola; i rimandi interni sono quelli della roadmap.

**(era in "Stato" della roadmap)**

- **Gli avvisi dei bandi non vanno su Postgres finché il passo 19d non
  passa.** Dal 20/11/2026 stanno solo nel Chroma locale (passo 19c,
  `docs/fatto.md`): l'app online non li vede. Il 19d è in chiusura dal
  21/11/2026, con il perimetro concordato il 20/11 sera (`coda.md`,
  "Passo 19d", punto 10); il caricamento su Postgres è il passo 19e.
- Demo mandata al consulente pilota il 16/11/2026, riscontro ricevuto il
  18/11/2026. Revisione del revisore tecnico ricevuta il 18/11/2026.
  Revisione esterna del piano ricevuta il 18/11/2026.
- Attese: 18 sui titoli nel file delle domande, su 14 domande. La tabella
  a freddo ne conta 17: manca quella di L05, che nel lotto 1 a freddo ha
  avuto il router fallito 3 volte su 3 (attesa 0/1).

Riscontro del consulente pilota del 18/11/2026, in sintesi:
- prova con tre domande;
- su una domanda senza risultati attesi l'app non ha inventato;
- su una ha mancato due bandi, uno nazionale e uno regionale;
- su una ha trovato opportunità corrette ma generiche;
- suggerimenti: includere il BURT e provare con qualche ministero.

Riscontro del 19/11/2026: domanda e casi indicati; diagnosi in
`coda.md`, 'Riscontro del consulente pilota e fonti': un pertinente
mancato per copertura (Fondo nazionale rievocazione storica 2027),
l'altro caso non era un bando.

**(era in "Passo 0" della roadmap)**

Parti (a) e (b) fatte il 18/11/2026 (`docs/fatto.md`).

**(era in "Passo 1" della roadmap)**

- Fatto il 19/11/2026 con un metodo diverso da quello previsto: due
  modelli, un arbitro, revisione a mano di 96 righe dei Comuni. 990
  etichette, 27 incerte, forma incerta per C18 e C20. Metodo, numeri
  e limiti in docs/piano-insieme-prova.md, 'Come sono state fatte le
  etichette'. Resta da fare: la colonna 'chi atteso' per domanda e le
  5 domande A.

**(era in "Passo 2" della roadmap)**

2a fatto il 18/11/2026: scadenze corrette a mano per Filiera SMART,
per l'edizione precedente del Bando Pmi EU-Blending (incentivi-3662,
non un doppione) e per il fondo di garanzia energie rinnovabili;
aperti al 16/11 da 54 a 51. I quattro bandi con 8 o più tipi non sono
errori di classificazione ma bandi "per requisito": restano come
sono, e il rimedio è il passo 4.

**(era in "Passo 17" della roadmap)**

17. **Testo di ricerca per bando**, senza modello, in un file separato
    (`data/processed/testo_ricerca.csv`); serve solo all'ordinamento.
    Dettaglio in `coda.md`, "Testo di ricerca (passo 17)".
    Fatto il 19/11/2026 (`docs/fatto.md`).

**(era nel passo 19 della roadmap)**

19a e 19b fatti il 19/11/2026, 19c il 20/11/2026 (`docs/fatto.md`):
17 file, 871 frammenti nel Chroma locale. Prossimo: 19d, misura del
recupero sugli avvisi (`coda.md`, "Passo 19d"). Gli avvisi vanno su
Postgres solo dopo che il 19d è passato.
19d in corso dal 20/11/2026: non è più una verifica, è il lavoro che
ridisegna la ricerca nei documenti. Fatti 195, divisi in 97 di
taratura e 98 di controllo; il controllo si apre una volta sola,
sulla scelta finale. Regola di chiusura, risultati e strade in
`coda.md`, "Passo 19d".
19d in chiusura dal 21/11/2026. Misure della notte del 20/11 sui 97
fatti di taratura in `coda.md`, "Passo 19d", punti 3 e 4. Perimetro
concordato il 20/11 sera (punto 10), quattro mosse e non altre:
scelta della configurazione; nome dell'azione degli apistici nel
registro; una sola strada nuova, il contesto per frammento; apertura
del controllo, una volta, scrivendo il numero che esce anche se è
sotto l'85%. Se resta sotto la soglia, gli avvisi entrano in
produzione solo con il filtro per bando, e i casi difficili restano
in coda. Le altre idee in `coda.md`, "Parcheggio".
Al 21/11/2026 sera: nome dell'azione nel registro, fuori dal recupero
(punto 5); contesto per frammento generato sugli 871 frammenti,
controlli e misura da fare, con le regole decise prima (punto 13);
poi revisione esterna del metodo, e solo dopo l'apertura del
controllo.
19e, nuovo (20/11/2026): avvisi su Postgres insieme al filtro per
`id_bando` nell'app, e rimisura del recupero su Postgres con gli
stessi fatti, perché lì ricerca per parole e indice dei vettori sono
diversi da Chroma.
Dal 22/11/2026 (disegno dell'app, `coda.md`, "Disegno dell'app
(22/11/2026)"): quando c'è una selezione di bandi, è la selezione la
fonte del filtro, al posto di "l'app indovina il bando". L'85% di
recupero del 19d è una condizione necessaria, non il traguardo delle
risposte giuste: quelle si misurano nel 19e.
Al 22/11/2026 sera: configurazioni chiuse, nessun'altra entra nel 19d
(`coda.md`, "Passo 19d", punto 13, voce 15). Al controllo va c-LR con
tutte le righe, come candidata debole: domande a mano nuove +3 in B
(voce 11); T-0 e T-R non adottabili (voce 13). Mancano la revisione
esterna e l'apertura del controllo, nell'ordine della voce 17.
19d chiuso il 23/11/2026, sotto soglia: apertura del controllo alla
voce 20, lettura a mano dei mancati alla voce 21 (`coda.md`, "Passo
19d", punto 13).

## Fatti il 24 novembre 2026

- (24/11/2026) Scansione del Portale della Regione in due tempi
  (passo 11): ricognizione senza modello del 23/11/2026
  (`scripts/ingestione/ricognizione.py`, rapporto rifatto alla stessa
  data in `ricognizione-4.csv`) ed estrazione del 24/11/2026
  (`estrai_nuovi --fonte regione-toscana`, lanciata da chi mantiene il
  progetto). Prima dell'estrazione: copia di sicurezza del database
  (`dati-grezzi/backup/comune-2026-11-24-prima-della-scansione.sqlite`)
  e prima copia congelata dei CSV (`dati-grezzi/archivi/2026-11-24_e26e2e30/`).
  Degli elenchi: 116 voci non in archivio, 109 con esito definitivo in
  `scansioni`; restano 7 candidati. 2 saltati senza campo della
  scadenza leggibile e con un anno passato nello slug, senza
  registrarli (bando della ricerca finalizzata 2021 e 2024 del
  Ministero della Salute); 5 al modello. Salvati 3: contributi per
  distribuzione e commercio al dettaglio di giornali e pubblicazioni
  periodiche (aperto fino al 15/12/2026), partenariato europeo sulle
  malattie rare ERDERA JTC 2027 (01/02/2027), partenariato europeo
  sulla trasformazione dei sistemi sanitari e assistenziali JTC 2027
  (21/01/2027). Scartati 2 come "non è un bando": Toscana Art Bonus per
  comuni e unioni di comuni (manifestazione di interesse per un
  catalogo di progetti) e il concorso per 2 unità di istruttore
  amministrativo. Costo 0,219 $ (ingresso 40845 token, uscita 13732);
  10 richieste a `www.regione.toscana.it`. Bandi da 113 a 116,
  scansioni da 381 a 386; nei CSV solo righe aggiunte, nessuna riga
  esistente cambiata; `testo_ricerca.csv` rigenerato (3 righe nuove);
  database ricreato dai CSV con `crea_da_csv`, conteggi uguali e
  nessuno scarto. L'elenco "politiche per la montagna, bandi aperti"
  ha zero voci al 24/11/2026.
- (24/11/2026) Correzioni a mano applicate con
  `scripts/manutenzione/correggi_da_testo.py`, esteso lo stesso giorno
  (campi `scadenza`, `scadenza_nota`, `riferimento_atto`,
  `verificato_il`, `beneficiari`, `dotazione` di `bandi`; righe nuove di
  `beneficiari_bando` con la loro frase), con le frasi di prova cercate
  nei testi salvati in `dati-grezzi/manuali/2026-11-24/` (dalle pagine
  salvate il 23 e il 24/11): proroga di alta formazione e ricerca-azione
  al 24/11/2026 (decreto dirigenziale 25474 del 19/11/2026); sospensione
  degli incentivi ai datori di lavoro privati dall'8 luglio 2026 per le
  lettere a-e dell'articolo 5, aperto solo per la lettera f (decreto
  n. 742/2026 di Arti), per intero nella nota sulla scadenza e in una
  riga nei beneficiari; categoria C (i distributori, fino a 180 euro per
  Comune servito) e testo dei beneficiari senza puntini del bando dei
  giornali. In `bandi.csv` tre righe cambiate, solo nei campi corretti;
  in `beneficiari_bando.csv` una riga aggiunta. Copia di sicurezza prima
  dell'applicazione:
  `dati-grezzi/backup/comune-2026-11-24-prima-di-correggi-da-testo.sqlite`.
  Le correzioni non sono protette da una riestrazione futura.
- (24/11/2026) Passo 19e, rimedio 1 (frammenti vicini passati al
  modello): misura senza modello, risposte vere prima (V0) e dopo (V1)
  su 20 domande della metà di controllo, lettura in due fasi. V1 passa
  la regola di chiusura: costo 1,90 sul solo testo dei frammenti, danno
  zero (10 prese su 10 restano giuste, nessuna discrepanza nuova del
  verificatore), beneficio 8 casi "vicino" su 10 (0 su 10 in V0). Costo
  vero delle risposte: V0 0,710 $, V1 0,838 $ per 20 domande. Dettaglio,
  limiti e decisioni in `coda.md`, "Passo 19e, rimedio 1"; file di
  lavoro in `dati-grezzi/prova/19e/`.
- (24/11/2026) Frammenti vicini nel codice, spenti
  (`SPOSTAMENTI_VICINI = ()` in `src/config.py`; `con_vicini` in
  `src/recupero_documenti.py`, `RecuperoIbrido.frammento`, chiamata in
  `src/chains/rag.py`; 20 test in `tests/test_vicini.py`). Si accendono
  nel passo 19e con l'ordine c-LR e il filtro per bando; su Postgres serve
  ancora la query nuova. Contesto della catena uguale a quello dello
  script di misura 20 su 20; con l'interruttore spento, catena identica a
  prima della modifica su 22 domande. Incidente: un controllo ha aperto il
  Chroma vero invece di una copia, cambiata solo la tabella interna
  `acquire_write`, dati identici alla copia del 19d. Regola: ogni script
  di misura apre una copia del Chroma, mai l'originale. Dettaglio in
  `coda.md`, "Passo 19e, rimedio 1", "Codice".
- (24/11/2026) Sospensione come dato strutturato, senza modello: tabella
  `sospensioni_bando` (una riga per periodo, ambito 'tutto' / 'in_parte',
  `sospesi`, `resta_aperto`, atto, frase, riapertura), in
  `TABELLE_DA_CSV` e in `TABELLE_DOPO_LA_COPIA` (`crea_da_csv` la
  accetta assente nelle copie congelate più vecchie). Schema scelto
  perché il testo salvato degli incentivi ha già tre eventi
  (sospensione 2024 della lettera e, riapertura 2024, sospensione 2026
  delle lettere a-e). Lo stato del bando dice le sospensioni in corso
  prima di ogni "aperto" (`con_sospensione` in
  `src/database/interrogazioni_bandi.py`, usata da `formatta_bando` e da
  `stato_bando`, quindi anche dall'etichetta dei frammenti). Un bando
  sospeso del tutto esce dagli aperti e dai conteggi (terza lista di
  `dividi`, in coda agli elenchi) e da "in scadenza"; uno sospeso in
  parte resta tra gli aperti con l'avviso. Riga del periodo 2026 degli
  incentivi scritta con `correggi_da_testo` (`Aggiunta`), con 17 frasi di
  prova trovate nel testo salvato, ciascuna delle cinque categorie
  sospese e quella che resta aperta comprese; `correggi_da_testo`
  rifiuta una frase vuota e cerca anche la frase della riapertura.
  Controlli a data fissata 2026-11-24 contro il commit `3dd9ee5`:
  `formatta_bando` e `stato_bando` cambiati per 1 bando su 116; delle 39
  interrogazioni cambiano solo le 7 che contengono gli incentivi (6 per
  beneficiario, il tema "sociale"), una riga ciascuna, con intestazioni,
  gruppi e conteggi uguali; con la tabella vuota tutto identico.
  `comune.sqlite` ricreato dai CSV (conteggi uguali,
  `sospensioni_bando` 1 riga); la copia congelata si carica con la
  tabella vuota; `testo_ricerca` aggiornato. 23 test nuovi in
  `tests/test_sospensioni.py`. Restano in coda (`coda.md`,
  "Sospensioni e chiusure anticipate"): periodo 2024, pulizia di nota e
  beneficiari, categoria di `diagnosi_attese`, domande vere con la
  regola di chiusura; il ramo "sospeso del tutto" è provato solo con
  dati finti; la ricognizione copre solo le pagine della Regione.
- (24/11/2026) Domande vere sulla sospensione, prima e dopo, lanciate da
  chi mantiene il progetto (disoccupato di 57 anni in un'azienda
  agricola; persona con disabilità iscritta al collocamento mirato).
  Regola di chiusura rispettata: dopo la modifica la prima risposta dice
  che per quella categoria il bando è sospeso, la seconda che resta
  aperto. Costo 0,235 $ per quattro risposte. Limite: anche "prima" le
  risposte davano la sospensione, perché la correzione a mano del 24/11
  l'aveva già scritta in `scadenza_nota` e `beneficiari`. La prova non
  misura quindi il valore del campo strutturato (ordine garantito dal
  codice, filtro dei sospesi del tutto, resistenza a una riestrazione).
  Script e risposte in `dati-grezzi/prova/sospensione/2026-11-24/`. Voci
  nuove viste nelle risposte (verificatore, citazioni ripetute, formato
  delle date, stato accanto ai "Bandi citati") in `coda.md`, "Esito
  delle domande vere".

## Fatti il 25 novembre 2026

- (25/11/2026) Citazioni ripetute accorciate nel testo mostrato:
  `accorcia_citazioni` in `src/citazioni.py`, chiamata solo da
  `mostra_risposta`, interruttore `ACCORCIA_CITAZIONI` in
  `src/config.py`. La prima citazione di ogni etichetta resta intera, le
  successive diventano "(fonte: [L])"; ISTRUZIONI non cambia, e
  verificatore e bandi citati ricevono sempre il testo intero (sul testo
  accorciato il verificatore perderebbe 348 controlli di atti e 321 di
  date, e cambierebbe i raggruppamenti in 2 risposte). Regola di
  chiusura su 226 risposte salvate: etichette nello stesso ordine 226 su
  226; descrizione lunga una volta sola per etichetta 226 su 226, con le
  due eccezioni dichiarate (15 risposte); testo fuori dalle citazioni
  identico 226 su 226; funzione spenta identica a oggi 226 su 226; bandi
  citati identici 182 su 182; verificatore e bandi citati con il testo
  intero, prova con AppTest fatta fallire una volta. Risparmio 46-52%
  nelle risposte sugli incentivi, media 7,5% e mediana 2,9% su 226: il
  difetto è concentrato sui bandi con una catena di atti lunga. 16 test
  nuovi in `tests/test_citazioni.py`. Dettaglio e voci rimaste in
  `coda.md`, "Citazioni ripetute (25/11/2026)".
- (25/11/2026) Falsi allarmi del verificatore e dato giusto nel ruolo
  sbagliato. Censimento senza modello su 226 risposte salvate (40 del
  19e, 182 dei lotti 1-3, 4 della sospensione con le fonti ricostruite
  dal database): 31 "non trovato", classificati a mano; famiglia A
  (numero della domanda) 6, B (variante di scrittura) 8, C (dato
  abbinato alla citazione del punto successivo, famiglia nuova) 9, D
  (calcolato) 0, E (davvero assente) 8: tre allarmi su quattro erano
  falsi. Corretti: abbinamento al proprio punto d'elenco; varianti
  ("primo" nelle date, numeri in lettere davanti a un'unità, "€.",
  orari con la virgola, ATECO a due livelli); la domanda al
  verificatore con l'esito "dato della domanda" per le sole quantità;
  intervalli di date (fine prima dell'inizio; estremi non della stessa
  finestra); quantità con la forma di un anno accettata anche tra gli
  anni. Regola di chiusura sulle 226: allarmi rossi da 31 (8 veri) a 8
  (7 veri; resta falso "punto 7", dichiarato); risposte con esito ROSSO
  da 22 a 6; "non citato" da 29 a 27; casi reali 1 e 2 spariti, 3 rosso,
  4 rosso nel test. Misure sui ruoli: intervalli 14 controllati e 1
  allarme vero; regola larga dalle parole vicine 34 falsi su 34, non
  implementata; ruoli di scadenze e importi 0 effetti su 302 dati,
  rinviati. Due fermate, corrette con il rimedio più stretto (schema
  degli orari dopo "alle"; il 2021 di "primo gennaio 2021"). Testi per
  l'utente: "presenti nella fonte citata" invece di "verificati", e una
  riga fissa su cosa promette il controllo. Nuova linea di base del
  verificatore: la riesecuzione del 25/11/2026 in
  `dati-grezzi/prova/verificatore/`. 50 test nuovi in
  `tests/test_verifica_ruoli.py`. Dettaglio e voci rimaste in `coda.md`,
  "Verificatore per categoria (25/11/2026)".
- (25/11/2026) Errore tecnico mostrato all'utente (demo del 24/11, un
  traceback di trenta righe per un errore di autenticazione): in
  `main()` di `app/app.py` un errore del servizio del modello o del
  database dei documenti mostra solo "Il servizio non è disponibile in
  questo momento. Riprova tra qualche minuto.". Elenco chiuso
  `ERRORI_SERVIZIO`: da `anthropic` AuthenticationError, RateLimitError,
  APIConnectionError (con APITimeoutError), InternalServerError,
  OverloadedError, ServiceUnavailableError; da `psycopg`
  OperationalError. Ogni altro errore continua a emergere. Nel log il
  tipo e il momento, non il testo dell'errore né la domanda.
- (25/11/2026) "Sospeso" accanto ai bandi citati: sotto "Bandi citati"
  lo stato dal database alla data di oggi, "sospeso in parte dall'8
  luglio 2026" o "sospeso dall'8 luglio 2026", anche se la risposta non
  nomina la sospensione (`stato_sospensione` in `app/app.py`, con
  `sospensioni_di`, `sospensioni_attive` e `data_di_oggi`). Il bando si
  trova per url; con una sospensione totale in corso vale quella.
- (25/11/2026) Ritocchi al pannello della verifica, solo nel testo
  mostrato: le date di un intervallo rosso restano solo nella sua riga
  (tolte prima del raggruppamento, così la stessa data scritta altrove
  resta tra i presenti e il conteggio segue le righe); "1 dato senza
  fonte" e "N dati senza fonte", e così "citato/i"; i tipi in parole
  ("numero", "intervallo di date", …). Verificatore e ISTRUZIONI non
  cambiano. 33 test nuovi in `tests/test_pagina_app.py`, con AppTest e
  catene finte; nessun test esistente toccato.
- (25/11/2026) Falsi risultati della ricerca per nome, in
  `src/database/interrogazioni_bandi.py`: nel passo del titolo il testo
  cercato vale solo come parole intere ("api" non si trova più dentro
  "capitale"); due parole sono simili, per un bando dato come trovato,
  solo se le lunghezze differiscono al più di 2 lettere
  (`DIFFERENZA_SIMILE`; con 1 si perdeva "fondo strade"). I titoli
  simili, che sono un suggerimento, usano il confronto di prima
  (`_simili_largo`), perché "campo sportivo" continui a suggerire il
  Bando Sport Missione Comune. Spariti ristorante verso "ristoro
  gasolio", trattore verso "trattamento rifiuti", prestito verso
  "prestazioni veterinarie", api verso "capitale"; 116 titoli e 12
  parametri salvati identici. Limiti noti con un test ciascuno:
  "rifugio" e le "Case rifugio", "prestito" e "prestatori". 8 test
  nuovi in `tests/test_interrogazioni_bandi.py`. Dettaglio in
  `coda.md`, "Ricerca per nome e parole comuni (25/11/2026)".
- (25/11/2026) Ripiego di `dettaglio_bando` sul testo unito dei bandi
  non scaduti (titolo, beneficiari, interventi), quando nessuna strada
  trova un bando: candidati con `trovato=False` e il motivo per
  ciascuno, con la parola del bando quando è scritta in un'altra forma;
  dopo, i titoli simili non già tra i candidati
  (`candidati_testo_unito`, `testi_per_campo`, `_candidati`). C12
  ("impianti sportivi mutuo agevolato") porta a Sport Missione Comune;
  nessun altro risultato cambia sui tre insiemi; "pulmino" resta senza
  risultati. Router, repertorio e ISTRUZIONI non cambiano. 4 test nuovi
  in `tests/test_interrogazioni_bandi.py`.
- (25/11/2026) Importo della domanda nel verificatore, in
  `src/verification/controllo.py`: "dalla_domanda" vale anche per
  importi, percentuali e date, solo quando la risposta li scrive come
  dati dell'utente (possessivo, nome, "di" o "da": `dell_utente`). Il
  caso del bar ("il suo prestito di 30 mila euro") non è più rosso; lo
  stesso valore attribuito alla fonte resta rosso. 226 risposte salvate:
  nessun cambiamento. 6 test nuovi in `tests/test_verifica_ruoli.py`,
  con la riga vera del bando Pmi fino a 50 mila euro.
- (25/11/2026) Tappa 6a del piano del 19e (`docs/piano-19e.md`): in
  `dettaglio_bando`, quando i bandi trovati (per titolo o nel testo)
  sono tutti scaduti, si cercano anche i candidati del testo unito tra i
  non scaduti; gli scaduti restano mostrati come scaduti, i candidati si
  aggiungono in un blocco a parte, numerati di seguito e mai scelti
  (`_con_candidati_aperti`). Senza candidati il risultato non cambia.
  Interruttore `RIPIEGO_ANCHE_CON_SCADUTI` in `src/config.py`, lasciato
  acceso. Caso "solo scaduti" elencato prima della modifica: 62 dei 116
  titoli, 4 dei 12 parametri salvati ("neve" tre volte, "bando neve"),
  1 delle 36 parole ("fotovoltaico"), 2 delle 40 parole distinte della
  strada C ("fotovoltaico", "caldaia"); in nessuno il ripiego trova un
  candidato non scaduto. Misura prima e dopo: 116, 12, 36 e 40 su 40
  identici; per "caldaia" lo scaduto del 2021 resta solo, mostrato come
  scaduto. 4 test nuovi in `tests/test_interrogazioni_bandi.py`; quello
  sul blocco dei candidati fallisce senza la modifica, gli altri tre
  sono guardie (interruttore spento, nessun candidato, un trovato non
  scaduto). Script e uscite in `../dati-grezzi/prova/tappa-6a/`.
- (25/11/2026) Prova di memoria su Streamlit Community Cloud (prima
  fermata del resto del 19e, `docs/piano-19e.md`, sezione 8), con la
  pagina `app/prova_memoria.py` sul ramo `prova-memoria`, che non si
  unisce a `main`. Due versioni di `requirements.txt`: versione 1, torch
  2.15.0 di PyPI con 15 pacchetti `nvidia-*`; versione 2, la stessa
  2.15.0 nella build per processore, nessun pacchetto `nvidia-*`. Massimo
  dall'avvio dopo il passo 7: 1887,0 MB e 1523,6 MB; processo dopo il
  passo 7: 1727,4 e 1228,8 MB; riordino di 30 coppie, mediana: 2,862 e
  2,539 s; limite letto dal contenitore 3072 MB in entrambe; nessun
  riavvio. La regola scritta prima (540 MB a regime, 690 MB di massimo,
  10 s) non passa in nessuna delle due: le soglie venivano dal minimo
  della documentazione di Streamlit, mai misurato. Il criterio per il
  quarto caso, scritto da chi mantiene il progetto dopo la versione 1 e
  prima della versione 2 (massimo sotto 2048 MB, nessun riavvio, riordino
  sotto 10 s), passa nella versione 2 con 524,4 MB di margine (161 MB
  nella versione 1). I 30 punteggi del passo 6 sono identici nelle due
  versioni, nello stesso ordine. Decisione di chi mantiene il progetto:
  motore in memoria e requisiti della versione 2. Dettaglio in
  `docs/prova-memoria.md`; voci rimaste in `coda.md`, "Prova di memoria
  su Streamlit (25/11/2026)".

## Spostato dalla roadmap il 25 novembre 2026

Testo tolto da `docs/roadmap.md` il 25/11/2026, parola per parola,
quando l'ordine è stato sostituito da quello di `docs/piano-19e.md`; i
rimandi interni sono quelli della roadmap.

**(era la riga "Ordine di esecuzione" della roadmap, sezione "Ordine dei
passi"; fonte: `git show HEAD:docs/roadmap.md`)**

I numeri dei passi non cambiano. **Ordine di esecuzione:** 0 (fatto);
1 (etichette, fatto); 2a (fatto); 17 (fatto); 1 (resto: "chi atteso", domande
A, attese con polarità); 19 (19a, 19b, 19c fatti; 19d chiuso il
23/11/2026, sotto soglia, `docs/coda.md`, "Passo 19d", punto 13, voci
19-21; poi 19e e 22, in un ordine che si decide ora); tra le prime cose a
19d chiuso, la scansione regolare delle fonti, fatta una sola volta il
13/11/2026, prima della videochiamata di dicembre (`coda.md`, "Disegno
dell'app (22/11/2026)", aggiunte del 23/11); 20 (prima
della videochiamata della prima settimana di dicembre); 2b; 4; 3; nuova
baseline; 5; 18; 8; 9; poi le fonti (C) in sequenza, non in parallelo.
Il passo 23 (copertura dell'archivio) si fa dopo il 19d.
Il passo 21 si fa prima di dare il link della demo a chiunque oltre al
consulente pilota, in qualunque punto della sequenza. Perché la nuova
baseline viene dopo il passo 19: "Decisioni prese" (19/11/2026).

## Fatti il 27 novembre 2026

- (27/11/2026) Esito della prova di memoria riportato su `main`:
  `docs/prova-memoria.md` copiato dal ramo `prova-memoria` (stesso
  contenuto, più due righe in testa che dicono che pagina e test restano
  sul ramo e come rilanciare la prova); in `requirements.txt` la riga di
  torch per processore della versione 2, subito dopo
  `sentence-transformers==6.0.1`, identica a quella del ramo, valida solo
  su Linux. Sul PC `pip install --dry-run --no-index -r requirements.txt`
  salta la riga ("Ignoring torch: markers 'sys_platform == "linux"'
  don't match your environment") e non ha niente da installare; torch
  resta 2.14.0+cpu. La verifica della demo dopo il riavvio resta da fare
  (`coda.md`, "Prova di memoria su Streamlit (25/11/2026)"). Marcatore
  della riga ristretto a Linux, Python 3.14 e x86_64, non provato online
  (stessa voce di `coda.md`); nel README due righe sulla versione per
  processore.
- (27/11/2026) Avvisi riconosciuti da `sha256` e non da `id_bando`:
  `e_frammento_di_avviso` in `src/recupero_documenti.py`, usata in
  `con_vicini` per scegliere chi riceve vicini e chi si unisce in
  blocchi; commento di `SPOSTAMENTI_VICINI` aggiornato. Il documento di
  sempre `mercati-rionali-2026` (117 frammenti) ha `id_bando` senza
  `sha256` e non riceve più vicini. Conteggio su una copia del Chroma:
  871 frammenti con `id_bando` e `sha256`, 117 solo con `id_bando`, 199
  con nessuno dei due, 0 solo con `sha256`. In `tests/test_vicini.py`
  la funzione di supporto `frammento` dà anche `sha256` agli avvisi
  finti (i corpi dei test non cambiano); 3 test nuovi, di cui due
  falliscono con la regola vecchia. Controllo di chiusura su una copia
  del Chroma, vicini spenti, 22 domande del 24/11: contesto, documenti,
  origini e recupero identici 22 su 22 (un'esecuzione ha dato un rango
  della ricerca densa diverso in una domanda, che si ripresenta anche
  tra due esecuzioni dello stesso codice).
- (27/11/2026) Materiale per le venti domande sulle spese (fermata 2 del
  19e), fuori dal repository in `..\dati-grezzi\prova\19e\domande-spese\`:
  il foglio `domande_spese.xlsx` da riempire a mano (12 bandi con avvisi,
  20 righe assegnate con una regola scritta prima di guardare gli avvisi:
  una domanda per bando, la seconda agli 8 bandi con più frammenti,
  contando una sola volta i bandi della stessa famiglia e senza dare loro
  la seconda, cambiata così il 27/11/2026 prima che esistesse una
  domanda; senza spese ammissibili, percentuali, massimali né testo degli
  avvisi), lo script che lo scrive e lo script della registrazione
  "prima" e "dopo" (catena dell'app collegata a Postgres come la demo,
  data fissata al 25/11/2026, `--stima` e `--tetto-dollari`), provato solo
  con il modello finto. Decisi da chi mantiene il progetto: la strada del
  "prima", la chiave delle risposte (due modelli di famiglie diverse,
  arbitrato sui disaccordi) e la regola di lettura. Impronta del foglio
  vuoto `4e96dcf4…98658`. Dettaglio in `coda.md`, "Venti
  domande sulle spese (27/11/2026)".

## Fatti il 28 novembre 2026

- (28/11/2026) Foglio delle venti domande sulle spese bloccato (fermata 2
  del 19e): 20 domande scritte a mano, impronta sha256
  `21a6ae5ab8d4c7383b535721f8f1592ac1033ba7e49ac4751a235e65378e58a2`,
  copia di sola lettura `domande_spese_bloccato_2026-11-28_21a6ae5a.xlsx`
  nella stessa cartella. Controlli di forma passati: 20 righe compilate,
  id_bando uguali all'assegnazione, "chi chiede" tra i valori ammessi,
  nessuna nota. Caratteristiche dell'insieme dichiarate da chi mantiene il
  progetto: casi plausibili e non raccolti; bando sempre nominato ("bando
  noto, domanda di dettaglio"); meno di 5 domande vaghe; circa un quarto
  su chi può accedere, da tenere distinto nella lettura; molte su un
  progetto concreto. Chi chiede, nel foglio: 8 comune, 7 associazione,
  5 privato, nessuna impresa (dichiarati 7, 7 e 6). Regola di lettura
  aggiornata prima di qualunque risposta: due categorie in più, "non c'è
  in modo esplicito, ma riporta la regola più vicina con la fonte" e
  "conclude senza fonte", quest'ultima contata come difetto, con la
  condizione nuova nell'esito (nessuna "conclude senza fonte" nuova nel
  "dopo"). Stima del "prima" con `registra_risposte.py --stima`:
  0,036-0,043 $ a domanda, 0,73-0,87 $ in tutto. Dettaglio in `coda.md`,
  "Venti domande sulle spese (27/11/2026)".
- (28/11/2026) Correzione della voce qui sopra: "dichiarati 7, 7 e 6" era
  un errore di conteggio di chi ha preparato il compito, non una
  dichiarazione di chi mantiene il progetto; vale 8 comune, 7
  associazione, 5 privato, come nel foglio.
- (28/11/2026) "Prima" delle venti domande sulle spese registrato da chi
  mantiene il progetto (fermata 2 del 19e): 20 su 20, cartella
  `..\dati-grezzi\prova\19e\domande-spese\registrazioni\prima_2026-11-28_115825`,
  commit `0946db5`, modello `claude-sonnet-5`, data passata 2026-11-25,
  impronta del foglio quella del blocco; costo 0,976 $ contro una stima di
  0,73-0,87 $. Letto solo `meta.json`; le risposte si leggono nella
  fermata 5. Dettaglio in `coda.md`, "Venti domande sulle spese
  (27/11/2026)".
- (28/11/2026) Fermata 1 del 19e, sotto-fermata 1.0: riferimenti completi.
  Taratura rifatta con lo script congelato: 189 righe su 189 uguali per
  k=10 e k=15, 189 ordini di B su 189 uguali al 24/11, trovati A / B a
  k=10 fogli 76 / 83 e a mano 69 / 78. `ordini_riferimento.json`, 336
  ordini, sha256 `f6c03849…bd3420a9`. Dettaglio in `piano-fermata-1.md`,
  sotto-fermata 1.0, e in `coda.md`, "Fermata 1 del 19e".
- (28/11/2026) Fermata 1 del 19e, sotto-fermata 1.1: `src/motore.py`
  (archivio, motore in memoria, riordino), non collegato all'app; costanti
  in `src/config.py` con l'interruttore `ORDINE_C_LR` spento; 15 test
  nuovi in `tests/test_motore.py`, ciascuno visto fallire senza il suo
  pezzo. Doppione con lo script di misura annotato in `coda.md`,
  "Fermata 1 del 19e".
- (28/11/2026) Fermata 1 del 19e, sotto-fermata 1.2: identità del codice
  sugli stessi ingressi della misura. Il motore di `src/motore.py` dà gli
  stessi ordini interi del riferimento: 336 su 336 in A e 336 su 336 in B,
  compreso il caso di A con 29 posti; trovati a k=10 come attesi. Nessuna
  differenza, nessun giro di correzione, `src/motore.py` non toccato.
  Dettaglio in `piano-fermata-1.md`, sotto-fermata 1.2, e in `coda.md`,
  "Fermata 1 del 19e".
- (28/11/2026) Fermata 1 del 19e, sotto-fermata 1.3: archivio locale,
  Chroma più il file dei contesti `data/db/contesti_avvisi.jsonl` (835
  righe, fuori dal repository), scritto da
  `scripts/ingestione/esporta_contesti.py` e letto da `ArchivioChroma` con
  il controllo dell'impronta del testo. I `Frammenti` dal Chroma (in
  copia) più il file sono uguali in tutto a quelli della 1.2; modalità
  veloce 49 su 49 in A e in B, scarto dei voti 0,0; Chroma vero non
  scritto. 14 test nuovi. Dettaglio in `piano-fermata-1.md`, sotto-fermata
  1.3, e in `coda.md`, "Fermata 1 del 19e".
- (28/11/2026) Fermata 1 del 19e, sotto-fermata 1.4: motore e riordino
  collegati all'app dietro `ORDINE_C_LR` (resta spento). A interruttore
  spento la catena è identica a prima (R2: 22 su 22, nessuna differenza)
  e niente del motore si carica; acceso, i documenti dati al modello sono
  i primi 10 di A del riferimento, 49 su 49, scarto dei voti 0,0. Con
  Postgres acceso (la demo) l'interruttore non ha effetto fino alla
  fermata 5. 12 test nuovi. Dettaglio in `piano-fermata-1.md`,
  sotto-fermata 1.4, e in `coda.md`, "Fermata 1 del 19e".
- (28/11/2026) **Fermata 1 del 19e chiusa** (sotto-fermata 1.5): il motore
  della misura c-LR sta in `src/motore.py` ed è collegato all'app dietro
  `ORDINE_C_LR`, spento. Identità: 336 ordini su 336 in A e in B sulle
  quattro serie, 49 su 49 dall'archivio Chroma più il file dei contesti e
  attraverso la catena; interruttore spento identico al codice di prima.
  Pulizia finale: `ArchivioChroma` legge i contesti solo dal file;
  impronte intere del Chroma nei registri degli script di misura. Cinque
  giri contro i 4,5-6 stimati, nessun giro di correzione. Dettaglio in
  `piano-fermata-1.md`, sotto-fermata 1.5.
