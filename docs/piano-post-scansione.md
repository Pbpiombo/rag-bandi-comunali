# Piano: correzioni dopo la scansione completa

Piano approvato l'11 novembre 2026, dopo la prova dell'app su Abetone
Cutigliano. Se la conversazione con Claude Code viene azzerata, si riparte
leggendo questo file.

Ordine: 4, 1, 2, 3. Fermata dopo ogni punto, con `ruff check`,
`python -m pytest` e l'importazione degli script modificati.

## 4. Foglio per la verifica a mano

- `docs/verifica-manuale-2026-11-11.csv`, UTF-8 con BOM.
- Righe: i 20 bandi del campione (seme 20261111, tra i bandi classificati
  l'11 novembre 2026) e i 5 aperti per almeno un tipo di ente pubblico;
  parcheggi-2026 e medicina personalizzata JTC 2027 sono in entrambi,
  quindi 23 righe (fatto).
- Colonne: id, gruppo (campione / aperti enti pubblici / entrambi), url,
  stato (calcolato all'11 novembre 2026), scadenza, a_sportello,
  tipi_beneficiari, condizioni (ciascuna preceduta dal suo tipo),
  riferimento_atto; vuote: scadenza_ok, sportello_ok, beneficiari_ok,
  atto_ok, note.
- Generato da uno script fuori dal repository; nel repository solo il CSV.

## 1. Non bandi: marcati ed esclusi, non cancellati

- `bandi.natura` (`'bando'` predefinito, `'non_bando'`) e
  `bandi.natura_motivo`, anche in `TABELLE_DA_CSV`; database ricreato dai
  CSV.
- `segna_non_bando(id, motivo)` in `src/estrazione/salva.py`: imposta
  natura, motivo e `classificato_il`, cosi' la riga non si riesamina.
- `riclassifica_bandi`: su `non_bando` chiama `segna_non_bando`.
- Interrogazioni di elenco e conteggi (`stato_archivio` compreso): solo
  `natura = 'bando'`, con una condizione condivisa. `dettaglio_bando`
  mostra la riga con "non e' un bando: <motivo>".
- Scansioni: una riga in `bandi` non e' gia' piu' candidata.
- Le tre righe attuali (immobili-emergenza-abitativa-2026,
  sistemi-museali-2026, spettacolo-dal-vivo-2026) si segnano con uno script
  una tantum, con i motivi registrati nel log della riclassificazione.
- Fatto. In piu' del previsto: `salva` rimette `natura = 'bando'` quando
  una pagina viene salvata come bando; `carica_csv` e il test di
  equivalenza inseriscono solo le colonne presenti nei dati, cosi' una
  colonna nuova prende il valore predefinito invece di un NULL esplicito.
  Database ricreato dai CSV con gli stessi conteggi; riferimento del test
  di equivalenza invariato.

## 2. Scadenza non indicata e non a sportello

- Terzo gruppo "Scadenza non indicata, da verificare" in
  `bandi_aperti_per_ente` e `bandi_per_beneficiario`.
- `formatta_bando` scrive lo stesso stato nella riga.
- `stato_archivio` li conta a parte rispetto agli aperti.
- Fatto. In piu' del previsto: `bandi_per_beneficiario` ha ora anche il
  gruppo dei bandi a sportello, come `bandi_aperti_per_ente` (i gruppi
  sono scritti da una funzione comune); se ci sono solo bandi senza
  scadenza, l'intestazione dice che nessun bando e' aperto di sicuro e il
  gruppo segue. Riferimento del test di equivalenza invariato.

## 3. Un'etichetta per bando e controllo del decreto citato

Causa verificata nel database: i decreti sono corretti e diversi per ogni
bando. Il modello li confondeva perche' la riga del bando non conteneva il
suo atto, e tutte le fonti stavano insieme nell'intestazione del blocco
[D1]. Il verificatore non se ne accorgeva perche' maschera la citazione
prima di cercare i dati.

- `Risultato.voci`: per ogni bando la riga e la sua fonte. Nel testo le
  righe dei bandi hanno un segnaposto locale `[#k]`, che diventa `[Dn.k]`
  quando si conosce il numero del blocco.
- Ogni riga di bando contiene `atto: <riferimento_atto>`.
- `formatta_dati` e il pannello delle fonti mostrano le etichette.
- Prompt: il dato di un bando si cita con la sua etichetta,
  `(fonte: [D1.2], <atto>)`.
- Verificatore:
  - citazioni `Dn.k`; testo di confronto di `Dn.k` = riga piu' fonte;
    `Dn` = blocco intero con le fonti;
  - i numeri di decreto o delibera nella citazione a `Dn.k` devono
    comparire nella riga di quel bando, altrimenti "non trovato" con
    "presente invece in ...";
  - un dato presente in un solo bando ma citato con `[Dn]`: esito
    "citazione generica", con il bando giusto nel dettaglio.
- I 18 casi originali di `test_verifica.py` passano senza modifiche; se
  uno cambia, ci si ferma e si spiega perche'.
- Test di equivalenza: le differenze del riferimento si approvano una per
  una prima di aggiornarlo.
- Fatto. Le tre differenze del riferimento di equivalenza (segnaposto
  [#k], "atto:" nella riga del bando, atto spostato nel dettaglio) sono
  state approvate e il riferimento rigenerato.
  I 18 casi di test_verifica.py passano senza modifiche; i casi nuovi
  sono in test_verifica_bandi.py. Scelte: la classe si chiama VoceBando
  (Voce esiste gia' nel repertorio); un numero d'atto si controlla solo
  nelle citazioni a [Dn.k]; riassumi conta citazione_generica solo quando
  c'e'; gli anni non danno mai "citazione generica".

## 5. Qualita' dell'estrattore, dalla verifica a mano

Approvato come proposto, dopo il punto 3. Viene dalla colonna note del foglio
`verifica-manuale-2026-11-11.csv` compilato. Sette righe hanno un "no" o
un "parziale": internazionalizzazione, conciliazione per lavoratrici,
dopo la laurea, welfare aziendale, tirocini per donne, assegno GOL,
risorse genetiche forestali.

Ordine interno, con una fermata dopo ogni passo: 5a (punti 4 e 5),
5b (punti 2 e 3), 5c (punto 1), 5d (nuova estrazione).

### 5a.1 "Probabilmente esaurito" solo senza data di chiusura (punto 4)

- `stato_sportello`: l'avviso si aggiunge solo se `scadenza` e' vuota.
  Uno sportello con data di chiusura futura e' aperto fino a quella data,
  salvo esaurimento delle risorse, che l'invito a verificare dice gia'.
- Test: uno sportello con scadenza e pubblicato da oltre due anni non ha
  l'avviso. Il riferimento di equivalenza non cambia: i bandi del test non
  hanno pubblicato_il.

### 5a.2 contributo_perc del fondo di garanzia (punto 5)

- Script una tantum, come segna_non_bandi: svuota `contributo_perc` di
  avviso-fondo-di-garanzia-energie-rinnovabili ed esporta bandi.csv. E'
  una modifica ai dati verificati, motivata dalla verifica a mano: 80 e'
  la quota garantita del prestito.
- Il valore veniva dall'estrattore vecchio ed era stato mantenuto dalla
  fusione di riclassifica_bandi, perche' il nuovo lo lasciava vuoto.
- Prompt, regola IMPORTI: contributo_perc e' la quota del costo coperta
  dal contributo, non la quota garantita di un prestito o di una garanzia.

### 5b.1 Tipo nuovo: professionisti e lavoratori autonomi (punto 2)

- `professionista_autonomo`: "liberi professionisti, lavoratori autonomi,
  titolari di impresa individuale", dopo altra_impresa nella lista; nome
  breve "professionisti e autonomi". `cittadini_famiglie` diventa
  "persone fisiche, famiglie, studenti, lavoratori dipendenti".
- Regole di corrispondenza: liberi professionisti, lavoratori autonomi,
  titolari di impresa individuale. Le pagine usano anche le forme
  "libere/i professioniste/i", "lavoratrici/lavoratori autonome/i",
  "titolari d'impresa individuale": le regole diventano espressioni
  regolari con i confini di parola, che coprono queste forme. Il prompt
  continua a mostrarle come espressioni leggibili.
- Il vincolo sui tipi nello schema viene dalla lista: il database si
  ricrea dai CSV, che non cambiano.
- Decisione: "titolari di impresa individuale" solo in
  professionista_autonomo. Da ricordare quando si progetta il selettore
  dei privati: la ditta individuale va trattata anche nelle categorie di
  impresa (es. un B&B a ditta individuale cerca come impresa_turistica).

### 5b.2 qualsiasi_soggetto solo per i requisiti (punto 3)

- Regole nuove:
  - "privati", "soggetti privati", "datori di lavoro": i tipi privati,
    cioe' le quattro imprese, professionista_autonomo, terzo_settore,
    cittadini_famiglie;
  - "soggetti pubblici": comune, unione_comuni, altro_ente_pubblico;
  - "pubblici o privati", "pubblici e/o privati", "pubblici e privati",
    "pubblico o privato": tutti i tipi tranne qualsiasi_soggetto.
- Nel codice: se le regole trovano dei tipi per un soggetto classificato
  qualsiasi_soggetto, quel tipo si sostituisce con i tipi trovati, con un
  avviso; le condizioni passano alle righe nuove. Cosi' "soggetti
  ospitanti privati" non compare piu' ai Comuni, e "pubblici o privati"
  compare anche a comune e unione_comuni.
- Prompt: qualsiasi_soggetto solo se il bando definisce chi partecipa con
  un requisito e non nomina nessun tipo di soggetto, neanche generico
  (privati, soggetti pubblici, datori di lavoro).
- Regola aggiunta per GOL: "organismi formativi" e "enti di formazione"
  comprendono ricerca_formazione.

### 5c. Bandi a finestre o con piu' scadenze (punto 1)

- Tabella nuova `scadenze_bando`: id_bando, numero, genere ('domanda' o
  'fase_successiva'), descrizione, apertura, scadenza, frase. In
  `TABELLE_DA_CSV`, esportata. Righe solo per i bandi con piu' date: gli
  altri restano come sono.
  - 'domanda': un periodo in cui si presenta domanda (una finestra, o una
    misura con la sua scadenza, come GOL).
  - 'fase_successiva': una scadenza per chi ha gia' superato una fase
    (la proposta completa dopo la pre-proposta, JTC 2027); non apre il
    bando a nuove domande e si mostra solo come informazione.
- `bandi.scadenza` resta "la data ultima per presentare domanda": l'ultima
  scadenza 'domanda'. Il codice la calcola dalle righe e segnala con un
  avviso se il modello ne ha indicata un'altra.
- Lo stato si calcola dalle righe, non si memorizza:
  - aperto: c'e' una finestra con apertura passata o vuota e scadenza
    futura; la riga dice "finestra aperta fino al X" e, se c'e',
    "prossima finestra dal A al B";
  - tra due finestre: gruppo nuovo "Chiusi ora, con una prossima
    finestra", e `stato_archivio` li conta a parte;
  - `bandi_in_scadenza` usa la scadenza della finestra aperta.
- Estrattore: chiave nuova "scadenze", un elenco con genere, descrizione,
  apertura, scadenza e la frase copiata; solo se la pagina ha piu' date.
  Ogni frase si cerca nella pagina, come per i beneficiari; due date in
  contraddizione (GOL, 31/07/2026 e 31/07/2027 per la stessa misura) vanno
  in scadenza_nota con confidenza bassa.
- Il test di equivalenza non cambia: i bandi del test non hanno righe in
  `scadenze_bando`.

### 5d. Nuova estrazione delle righe con "no" o "parziale"

- `riclassifica_bandi --id ID` (ripetibile): riestrae i bandi indicati
  anche se gia' classificati; `--prova` con la stima del costo. La fusione
  resta com'e': i valori vecchi mantenuti si elencano.
- Prima, senza modello: applicare le regole nuove ai soggetti gia' in
  archivio per trovare gli altri bandi la cui classificazione
  cambierebbe (es. "Altri soggetti pubblici e/o privati" in risorse
  genetiche agrarie). L'elenco si approva prima di riestrarli.
- Dopo: un foglio nuovo con le sole righe riestratte, nello stesso
  formato, per ricontrollarle.

### Punto 5: fatto (12 novembre 2026)

Tappe 5a-5d fatte, con le aggiunte decise strada facendo:

- 5a: "probabilmente esaurito" solo per gli sportelli senza data di
  chiusura; contributo_perc del fondo di garanzia svuotato
  (`svuota_contributo_garanzia`).
- 5b: tipo `professionista_autonomo`; regole come espressioni regolari con
  i confini di parola. Le regole generiche (privati, datori di lavoro,
  pubblici e/o privati...) stanno in `GENERICI` e si applicano solo per
  sostituire qualsiasi_soggetto, mai per aggiungere tipi a un soggetto gia'
  classificato. Le righe con un soggetto generico si mostrano con il
  soggetto del bando ("nel bando: «...»"). Regole aggiunte: "enti
  formativi" (GOL).
- 5c: tabella `scadenze_bando`, gruppo "Chiusi ora, con una prossima
  finestra". Righe inserite a mano (`inserisci_finestre`) per dopo la
  laurea, GOL e JTC 2027, con origine `manuale`: una riestrazione non le
  sostituisce mai, e le date diverse proposte dal modello si elencano da
  rivedere. GOL: Misura 1 al 31/07/2027 (la pagina riporta anche il
  31/07/2026, detto nella descrizione), Misura 2 al 30/06/2027;
  bandi.scadenza a 2027-07-31. In piu': esportazione dei CSV in ordine di
  chiave primaria, "oggi" e "fra 1 giorno" nelle righe.
- 5d: riestratti 10 bandi (dopo la laurea escluso: la sua scadenza era gia'
  corretta a mano). Costo reale 0,608 $, cioe' 0,061 $ a bando:
  `COSTO_BANDO` aggiornato; `COSTO_NON_BANDO` (0,031 $) da rimisurare.

Verifiche a mano:

- prima, 11 novembre 2026, 23 bandi: scadenza corretta in 21, sportello e
  atto in 23, beneficiari corretti in 17, parzialmente in 3, errati in 3
  (`verifica-manuale-2026-11-11.csv`);
- seconda, 12 novembre 2026, sui 10 bandi riestratti: scadenza corretta in
  10, sportello in 8, atto in 8 (2 parziali), beneficiari corretti in 7 e
  parzialmente in 3, nessuno errato (`verifica-manuale-2026-11-12.csv`).

Correzioni finali, dopo la seconda verifica:

- regole e prompt: "privati", "soggetti privati", "datori di lavoro" (e
  quindi "soggetti ospitanti privati") non comprendono cittadini_famiglie;
  "pubblici e/o privati" si'. Reti, consorzi, associazioni di imprese ai
  tipi di impresa, di professionisti a professionista_autonomo; con un
  settore, o "consorzi" e "forme associative" da soli, nessuna regola.
  Nel prompt: forme associative mai qualsiasi_soggetto; sportello e data
  di chiusura non si contraddicono; riferimento_atto con i decreti che
  modificano scadenze o requisiti, non quelli su graduatorie, elenchi o
  modulistica;
- regola nel codice: "salvo (l')esaurimento (anticipato) delle risorse"
  rende il bando a sportello, con la frase come prova;
- dati, senza modello (`applica_regole_verifica`): tolte le righe
  cittadini_famiglie di welfare aziendale e tirocini; a sportello le due
  linee della conciliazione per i lavoratori indipendenti (voucher e
  contributo);
- dati a mano (`correggi_atti`), con le frasi della pagina verificate:
  decreti di modifica aggiunti agli atti di risorse forestali (valore
  precedente alla 5d), contributo della conciliazione, sicurezza sul
  lavoro, mercati rionali, percorsi formativi ecosistemi; scadenza_nota
  della conciliazione per lavoratrici riscritta con le due frasi della
  pagina;
- riestratta l'internazionalizzazione (0,047 $): le forme associative
  vanno ai tipi di impresa e a professionista_autonomo.

Rimasti in coda nella roadmap: la contraddizione 13542/13543 della
sicurezza sul lavoro, e le correzioni a mano sui campi di `bandi`, non
protette da una riestrazione futura.

### Per quando l'estrattore leggera' i PDF dei bandi

- Nei bandi dei fondi europei la voce "Beneficiari" puo' indicare chi
  gestisce l'operazione (es. ARTI), non chi presenta la domanda: chi
  presenta la domanda e' nell'articolo "Soggetti ammessi alla
  presentazione delle domande".
- Pagina web e testo del bando possono non coincidere (es. dotazione 2026
  dei tirocini: 147.523,40 nel PDF, 147.532,40 sulla pagina): vale il
  testo del bando.

## Roadmap

In coda: scadenze multiple (GOL), tirocini classificati
`qualsiasi_soggetto`, categoria per professionisti e lavoratori autonomi,
microzonazione fuori dall'elenco (sostituisce la riga esistente),
appartenenza dei comuni all'Unione nel profilo.

Stato al 13 novembre 2026 (`docs/roadmap.md`, "Fatto"):

- scadenze multiple: fatto (5c, tabella `scadenze_bando`);
- tirocini e `qualsiasi_soggetto`: fatto (5b, `qualsiasi_soggetto` solo
  per i requisiti);
- professionisti e lavoratori autonomi: fatto (5b, tipo
  `professionista_autonomo`);
- microzonazione: fatto il 12 novembre, bandi del 2026 trovati, tutti
  scaduti;
- appartenenza dei comuni all'Unione nel profilo: ancora in coda.
