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

## In corso

Verifica a mano di 20 bandi scelti a caso dalla scansione completa.

## Prima della demo con il consulente pilota

- **Tappa 5b del piano post-scansione**: tipi di beneficiari per i privati,
  cioè il tipo nuovo `professionista_autonomo` (5b.1) e `qualsiasi_soggetto`
  solo per i requisiti (5b.2). Dettagli in `docs/piano-post-scansione.md`.
- **Domande d'esempio dell'app**: sostituite con domande sui bandi pensate
  per il consulente.
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
  in `docs/prova-verificatore.md`).

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
   - voce 15: fonte dei bandi letta dalla tabella `fonti`.
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
- Bando microzonazione sismica (DGR 1081 del 7/9/2026, premialità Toscana
  Diffusa): fuori dall'elenco dei bandi aperti del portale, quindi la
  scansione non lo vede. Cercarlo su un'altra pagina o fonte.
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
- Atto senza data in parcheggi-2026: `riferimento_atto` non riporta la
  data del decreto 18191 del 7/8/2026 (verifica a mano dell'11 novembre
  2026).
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
