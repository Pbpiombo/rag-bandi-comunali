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
- **Passo 3, sottopasso estrattore, tappe a e b**: tabelle `beneficiari_bando`
  e `interventi_bando`, estrattore nuovo. Piano in `docs/piano-estrattore.md`.

## In corso

Sottopasso estrattore: controllo delle prove di scadenza e importi, test con il
modello vero, tappe c e d. Poi la scansione completa.

## Prossimi passi, in ordine

1. **Fine del passo 3**: indirizzo dell'elenco e regole del portale lette dalla
   tabella `fonti`; fonte nuova GAL MontagnAppennino; verifica a mano di 20
   bandi scelti a caso, con il risultato nel README.
2. **Scheda per bando**: per chi è e per cosa si può usare, divisa per tipo di
   beneficiario, con le clausole citate. Quello che il bando dice e i possibili
   usi proposti dal sistema restano visibilmente separati.
3. **Riepilogo per Cosimo**: bandi nuovi con le loro schede, filtrati sulle sue
   ricerche scritte in un file. Prima mandato a mano, poi automatico.
4. **Aggiornamento ogni due settimane**: GitHub Actions lancia la scansione,
   salva CSV e database, manda il riepilogo.
5. **Ricerca per bisogno**: l'utente descrive cosa vuole fare, il sistema cerca
   tra gli interventi ammissibili. Caso di prova: "devo rifare la piazza"
   → bando mercati rionali. Nei frammenti documentali, lo stato del bando
   (scaduto o aperto) arriva al modello.
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

- Popolazione di Sambuca Pistoiese e San Marcello Piteglio dalla tabella ISTAT
  (prompt per Claude Code pronto). Tutti e tre i comuni dalla stessa tabella.
- Zona sismica dei tre comuni: riferimento OPCM 3274/2003 aggiornata dalla DGRT
  421 del 26/05/2014, da verificare sull'allegato e su eventuali aggiornamenti.
- Colonna `montano` nel profilo: i tre comuni sono totalmente montani
  (Delib. CR 10/2025).
- Verificare sulla pagina della Regione il fondo di garanzia energie
  rinnovabili del 2014 (stato e "contributo fino all'80%").
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
  Diffusa): verificare che compaia dopo la scansione completa.

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
