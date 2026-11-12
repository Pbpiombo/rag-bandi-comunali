# Roadmap

Stato al 11 novembre 2026. Da aggiornare alla fine di ogni sottopasso.

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

- **Piano fonti, tappa 1** (12 novembre 2026, voce 15 della revisione):
  fonti, elenchi e regole di lettura dal database (`fonti.csv`,
  `elenchi.csv`), tipi di fonte "pagine" e "file". Esito in
  `docs/piano-fonti.md`.
- **Piano fonti, tappe 2 e 3** (12 novembre 2026): elenco "bandi aperti"
  della montagna; bandi scaduti da meno di 12 mesi salvati come storico,
  mai tra gli aperti, in un blocco a parte nelle liste per tema e
  trovabili per nome. Premi imboschimenti (SRA28) salvato come storico.

## In corso

Verifica a mano di 20 bandi scelti a caso dalla scansione completa.

## Prima della demo con il consulente pilota

- **Tappa 5b del piano post-scansione**: tipi di beneficiari per i privati,
  cioè il tipo nuovo `professionista_autonomo` (5b.1) e `qualsiasi_soggetto`
  solo per i requisiti (5b.2). Dettagli in `docs/piano-post-scansione.md`.
- **Domande d'esempio dell'app**: sostituite con domande sui bandi pensate
  per il consulente. Non devono nominare un avviso per titolo ("nel bando
  X, quanto…"): con P2 il recupero cerca anche dentro l'avviso nominato,
  ma restano casi non risolti e un frammento al limite
  (`docs/prova-verificatore.md`, P2).
- **Dati ISTAT di Sambuca Pistoiese e San Marcello Piteglio** caricati
  (prompt per Claude Code pronto). Tutti e tre i comuni dalla stessa tabella.
- **Blocco A, verificatore** (voci 1, 3, 4 e 11 di
  `docs/revisione-2026-11-12.md`): confronto su valori interi e non su
  sottostringhe; date in tutte le forme ricondotte a una sola; numeri di
  decreto e delibera nel testo della risposta controllati come dati;
  pannello di verifica non verde se non ha verificato niente;
  `step3_verifica` riparato. Piano in `docs/piano-verificatore.md`.
- **Blocco B, dati mostrati e documenti** (voci 5, 6, 10, 12 e 14 della
  revisione, e l'etichetta "dati verificati il" della voce 8): contributo
  minimo e massimo e territorio nelle righe dei bandi, importi senza
  arrotondamento; `dettaglio_bando` che non sceglie a caso tra titoli
  simili; database della demo allineato ai CSV; sportelli con data di
  chiusura in `bandi_in_scadenza`; README e docs/ allineati al codice;
  "estratti il" al posto di "verificati il" per le date di estrazione;
  stato del bando (scaduto o aperto) nei frammenti documentali, spostato
  qui dal passo 5 dopo la prova del 12 novembre 2026, in cui il bando
  mercati rionali, scaduto, è stato presentato come attuale (proposta P3
  in `docs/prova-verificatore.md`). **Fatto il 12 novembre 2026**: stato
  calcolato a ogni domanda e scritto nell'intestazione del frammento,
  regola nel prompt, verificatore che confronta anche quella riga
  (`src/database/stato_documenti.py`). Provato con il modello: stato
  citato e verificato (`docs/prova-verificatore.md`).
  Quando una domanda nomina un bando, il router deve usare
  `dettaglio_bando` invece di `bandi_per_tema`. Caso: "mercati rionali"
  cercato come tema non trova il bando, classificato con il tema
  "commercio", e il modello riporta che l'archivio non ha
  corrispondenze.

## Prossimi passi, in ordine

1. **Fine del passo 3**: indirizzo dell'elenco e regole del portale lette dalla
   tabella `fonti`; fonte nuova GAL MontagnAppennino; verifica a mano di 20
   bandi scelti a caso, con il risultato nel README.
2. **Scheda per bando**: per chi è e per cosa si può usare, divisa per tipo di
   beneficiario, con le clausole citate. Quello che il bando dice e i possibili
   usi proposti dal sistema restano visibilmente separati.
3. **Riepilogo**: bandi nuovi con le loro schede, filtrati sulle sue
   ricerche scritte in un file. Prima mandato a mano, poi automatico.
4. **Aggiornamento ogni due settimane**: GitHub Actions lancia la scansione,
   salva CSV e database, manda il riepilogo. Oltre ai bandi nuovi, si
   ricontrollano i bandi aperti e quelli chiusi da poco, per le proroghe:
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
5. **Ricerca per bisogno**: l'utente descrive cosa vuole fare, il sistema cerca
   tra gli interventi ammissibili. Caso di prova: "devo rifare la piazza"
   → bando mercati rionali. (Lo stato del bando nei frammenti è passato al
   blocco B, prima della demo.)

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
6. **Privati nell'app**: selettore pubblico/privato e tipo di privato a
   macrogruppi.
7. **Sezione riservata**: accesso, iscrizioni con mail e ricerche salvate su
   Supabase, tasto "aggiorna adesso" che lancia il processo su GitHub,
   segnalazione manuale di un bando. Parte pubblica limitata a 3 domande per
   sessione, con un tetto giornaliero complessivo e un invito a scrivere per
   l'accesso.
8. **Newsletter come segnali**: casella dedicata iscritta alle newsletter di
   Regione, fondazioni e GAL; i link estratti passano dalla verifica sulla
   pagina ufficiale.
9. **Percorso guidato per gli iscritti**: passi definiti dal bando (requisiti,
   documenti, scadenze intermedie, contatti), controllo dei documenti con ogni
   requisito citato. Percorso a passi fissi, non un agente libero.
10. **Docker** per Postgres con pgvector in locale.

## In coda

- Zona sismica dei tre comuni: riferimento OPCM 3274/2003 aggiornata dalla DGRT
  421 del 26/05/2014, da verificare sull'allegato e su eventuali aggiornamenti.
- Colonna `montano` nel profilo: i tre comuni sono totalmente montani
  (Delib. CR 10/2025).
- Verificare sulla pagina della Regione il fondo di garanzia energie
  rinnovabili del 2014 (stato e "contributo fino all'80%"). Dopo la
  riclassificazione e' senza scadenza e non a sportello: la pagina non ne
  parla.
- Fuso orario: `date.today()` in 9 punti (DTZ011).
- Segnalazioni ruff ISC004 e BLE001 negli script.
- Due xfail di `pulisci`: numeri separati da virgola, intestazione con spazi.
- Regola "imprese senza settore" applicata anche nel codice, non solo nel
  prompt.
- Avvisi sui bandi salvati visibili nell'app (perché una dotazione è vuota).
- Righe di `scansioni` con slug tagliati: da ripulire.
- Link simbolici `.claude/skills` e `.agents/skills` verso `.venv` nel repo.
- Fine riga CRLF/LF.
- Supabase in pausa dopo inattività: tenerlo sveglio o cambiare piano.
- Limite di spesa mensile nella console di Anthropic.
- ~~Bando microzonazione sismica (DGR 1081 del 7/9/2026, premialità
  Toscana Diffusa)~~: trovato il 12 novembre 2026 nella sezione rischio
  sismico, un livello sotto le schede: scaduto il 17/10/2026, come gli
  altri due bandi sismici del 2026 (microzonazione di livello 4 il 27/06,
  verifiche tecniche l'01/08). Le pagine della sezione non sono state
  aggiunte come elenchi: sono schede, non bandi (`docs/piano-fonti.md`,
  tappa 2).
- Scadenze multiple nello stesso bando (es. assegno formazione GOL, Misura
  1 al 31 luglio 2026 o 2027, Misura 2 al 30 giugno 2027): oggi
  l'estrattore ne tiene una sola.
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
- ~~Atto senza data in parcheggi-2026~~: corretto il 12 novembre 2026 con
  `correggi_atti` ("Decreto dirigenziale 18191 del 7 agosto 2026", dal
  link "Testo decreto 18191 del 07-08-2026" della pagina).
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
- P2, ricerca ristretta ai documenti nominati: collegata. Il 12 novembre
  2026 è stata scollegata e poi ricollegata. Con la domanda normalizzata
  senza "?" finale faceva uscire su Postgres il termine di presentazione
  (7ª → assente). Con il "?" sempre aggiunto rispetta la regola: 13
  frammenti su 16 invece di 11 nelle 15 domande di prova, e nessuna uscita
  nelle 5 di controllo, scritte dopo. Provate e scartate: ripulitura di
  tutte le parole del titolo e fusione con RRF (dettagli nel modulo).
  Restano da seguire:
  - i casi aperti: i contributi dei mercati rionali, con parole diverse
    dal testo, e la domanda su due avvisi;
  - il termine di presentazione al limite: 8ª su Postgres, 10ª su Chroma;
  - la domanda di controllo sulla rendicontazione dei mercati rionali,
    che con P2 scende dalla 5ª alla 7ª su Postgres.

  Rilanciare `scripts/diagnostica/prova_recupero.py` a ogni modifica del
  recupero o dell'archivio.
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
  - ~~le linee di bando regionali per le imprese emerse~~: verificate il
    12 novembre 2026. Voucher garanzia già in archivio (4 bandi);
    impianti di risalita e custodi della montagna solo tra i bandi chiusi
    della sezione montagna; bandi neve solo il "sistema neve 2017".
    Aggiunto l'elenco "bandi aperti" della montagna, vuoto quel giorno
    (`docs/piano-fonti.md`, tappa 2);
  - ~~verificare se la pagina dei bandi aperti già acquisita copre i bandi
    del PR FESR e del PR FSE+ Toscana 2021-27~~: sì, il 12 novembre 2026
    gli elenchi dei due programmi e dello sviluppo rurale erano contenuti
    per intero in quello generale. Il controllo si ripete con
    l'aggiornamento periodico (passo 4);
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
