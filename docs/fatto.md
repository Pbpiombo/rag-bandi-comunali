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
