# Revisione del progetto, 12 novembre 2026

Revisione in sola lettura: nessun file modificato oltre a questo, nessuna
chiamata al modello. Stato di partenza: `python -m pytest` 373 passati,
3 deselezionati, 2 xfail; `ruff check` 11 segnalazioni, quelle già note.
Database e CSV coincidono riga per riga in tutte le tabelle (controllato
con una lettura in sola lettura di `comune.sqlite`).

I casi del verificatore riportati sotto sono stati eseguiti davvero, con
`verifica()` su testi costruiti a mano. I dati citati vengono da
interrogazioni in sola lettura sul database attuale.

## Riepilogo

| # | Problema | Quando | Costo |
|---|---|---|---|
| 1 | Il verificatore confronta per sottostringa: 8% passa contro 80% | prima della demo | mezza giornata |
| 2 | Estrattore: si controlla che la prova sia nella pagina, non che il valore sia nella prova | prima dell'aggiornamento automatico | 1 giorno |
| 3 | I decreti scritti nel testo della risposta non vengono controllati | prima della demo | mezza giornata |
| 4 | Date ISO nelle righe dei bandi, date in italiano nelle risposte: falsi "non trovato" | prima della demo | 2-3 ore |
| 5 | `contributo_max` estratto in 23 bandi e mai mostrato; importi arrotondati all'euro | prima della demo | 2 ore |
| 6 | `dettaglio_bando` sceglie a caso tra titoli simili | prima della demo | 1-2 ore |
| 7 | Una pagina registrata come scaduta non si riesamina mai: proroghe perse | prima dell'aggiornamento automatico | 1-2 ore |
| 8 | Correzioni a mano sovrascritte dalla riestrazione; "dati verificati il" è la data di estrazione | prima dell'aggiornamento automatico | 1 giorno |
| 9 | Tre punti in cui database e CSV si separano | prima dell'aggiornamento automatico | mezza giornata |
| 10 | La demo legge il `comune.sqlite` del repository | prima della demo | 1 ora subito, mezza giornata la soluzione |
| 11 | Pannello di verifica verde con zero dati verificati; `step3_verifica` si interrompe | prima della demo | 1 ora |
| 12 | `bandi_in_scadenza` esclude gli sportelli con data di chiusura | prima della demo | 1-2 ore |
| 13 | Test assenti sul percorso di `estrai_nuovi` e sui confronti del verificatore | prima dell'aggiornamento automatico | 1 giorno |
| 14 | README e documenti in docs/ non allineati al codice | prima della demo | 2 ore |
| 15 | La fonte dei bandi è scritta nel codice; la tabella `fonti` non viene letta | prima dell'aggiornamento automatico | 1 giorno |

---

## 1. Il verificatore confronta per sottostringa

**Dove.** `src/verification/controllo.py:270-273`: un dato è verificato se
il suo valore normalizzato compare *dentro* il testo della fonte
(`any(v in testi[e] for v in varianti)`). Lo stesso alle righe 248-254 e
289-290. Per i numeri d'atto il controllo con i confini esiste già
(`contiene_numero`, righe 159-161), per gli altri dati no.

Casi eseguiti, tutti con esito `verificato`:

| risposta | fonte |
|---|---|
| "copre l'8% (fonte: [1])" | "pari all'80% della spesa" |
| "fino a € 50.000 (fonte: [1])" | "fino a € 150.000,00" |
| "scadono il 3 novembre 2026 (fonte: [1])" | "entro il 13 novembre 2026" |
| "mancano 26 giorni (fonte: [D1.1])" | riga del bando con "fra 261 giorni" |

Per percentuali e importi lo schema cattura solo le cifre (`SCHEMI`,
righe 47-54): "8" cercato in un blocco [Dn] che contiene date, URL e
importi si trova quasi sempre.

**Perché conta.** È il caso che il progetto promette di escludere: un
importo o una percentuale sbagliati presentati con il segno di spunta.
Nessuno dei 18 casi di `tests/test_verifica.py` lo prova (7% contro 15% non
sono uno dentro l'altro).

**Costo.** Mezza giornata. Cercare il valore con i confini numerici, come
fa già `contiene_numero` (`(?<![\d.])valore(?![\d])` sul testo
normalizzato), e aggiungere i quattro casi sopra come test negativi. Il
test di equivalenza non cambia: riguarda le interrogazioni, non il
verificatore.

**Quando.** Prima della demo.

## 2. Estrattore: il valore non si confronta con la sua prova

**Dove.** `src/estrazione/bandi.py:593-627` (`_verifica_prove`): si
controlla che la frase di prova compaia nella pagina, ma non che contenga
il valore. Una scadenza `2026-12-31` con prova "entro il 30 novembre
2026", copiata esattamente, passa. Lo stesso per gli importi e per le
righe di `scadenze_bando` (`_valida_scadenze`, riga 756).

**Perché conta.** Il verificatore delle risposte controlla i dati dei bandi
sulla riga del database ([Dn.k]), non sulla pagina. Un valore sbagliato
in estrazione viene quindi dato per verificato in ogni risposta. Oggi le
verifiche a mano (23 + 10 bandi) fanno da rete; con l'aggiornamento
automatico salva senza nessuno che guardi.

**Costo.** Un giorno. Per le date: leggere dalla prova le date
(gg/mm/aaaa, "30 novembre 2026"), convertirle in ISO e pretendere che il
valore sia tra quelle, con un problema bloccante per la scadenza. Per gli
importi: il numero convertito deve comparire nella prova, altrimenti il
valore si svuota con un avviso. Le prove non sono salvate nel database:
i 46 bandi in archivio non si possono ricontrollare senza riscaricare le
pagine, quindi va previsto uno script che riscarica e confronta, senza
modello.

**Quando.** Prima dell'aggiornamento automatico.

## 3. I decreti scritti nel testo della risposta non vengono controllati

**Dove.** `src/verification/controllo.py:16-20` e `:131`: `SCHEMA_ATTO`
maschera "decreto n. 9999 del 01/01/2026" ovunque nella risposta, non
solo dentro le citazioni. `_verifica_atti` (righe 338-352) controlla i
numeri d'atto solo nelle citazioni a [Dn.k]. Caso eseguito: "approvato
con decreto n. 9999 del 01/01/2026 (fonte: [1])" con una fonte che dice
1234 produce **nessun esito**, e l'app scrive "Nessun dato numerico da
verificare in questa risposta" (`app/app.py:70-72`).

**Perché conta.** Il numero del decreto è il dato che chi segue la
domanda copia in un atto. Il piano post-scansione (punto 3) è nato
proprio da decreti scambiati tra bandi; il controllo copre solo la forma
di citazione in cui l'errore è stato visto.

**Costo.** Mezza giornata. Mascherare `SCHEMA_ATTO` solo dentro le
citazioni e trattare i numeri d'atto del testo come dati, con
`numeri_atto` e `contiene_numero`, sulle fonti citate dopo di essi.

**Quando.** Prima della demo.

## 4. Date in formati diversi: falsi "non trovato"

**Dove.** Le righe dei bandi scrivono le date in ISO
(`interrogazioni_bandi.py:332`, "scade il 2027-07-31"); il verificatore
confronta il testo così com'è (`controllo.py:104-119` non tocca le date).
Caso eseguito: "scade il 31/07/2027 (fonte: [D1.1])" contro la riga
"scade il 2027-07-31" dà `non_trovato`, "non presente in nessuna fonte
recuperata". Lo stesso per "31 luglio 2027". I test usano solo date ISO
(`tests/test_verifica.py:144`).

**Perché conta.** Una data giusta segnata in rosso davanti al consulente
toglie credibilità al pannello di verifica più di qualunque altro errore.
Dipende solo da come il modello sceglie di scrivere la data.

**Costo.** 2-3 ore. Convertire in ISO, prima del confronto, le date dei
due lati (gg/mm/aaaa, gg-mm-aaaa, "gg mese aaaa"), con un test per
formato.

**Quando.** Prima della demo.

## 5. Importi estratti e mai mostrati, importi arrotondati

**Dove.** `formatta_bando` (`interrogazioni_bandi.py:314-369`) e
`dettaglio_bando` (`:754-814`) non mostrano mai `contributo_min`,
`contributo_max` né `territorio`. Nel database `contributo_max` è pieno in
23 bandi su 46, `territorio` in 44. `euro()` (`:121-128`) arrotonda
all'euro: la dotazione di GOL, 84.552.097,68, diventa "84.552.098"; 8
bandi hanno centesimi nella dotazione, 2 nel contributo.

**Perché conta.** "Quanto può chiedere un Comune?" è la domanda più
probabile in una demo sui bandi, e il dato c'è ma il modello non lo
riceve: risponde dai frammenti o dice che non lo trova. Gli importi
arrotondati sono valori che nel bando non esistono, e il verificatore li
conferma perché li confronta con la riga già arrotondata.

**Costo.** 2 ore, più l'approvazione delle differenze nel riferimento di
equivalenza (`tests/dati/interrogazioni_comuni_dopo.json`).

**Quando.** Prima della demo.

## 6. `dettaglio_bando` sceglie a caso tra titoli simili

**Dove.** `interrogazioni_bandi.py:756-759`: `WHERE id = ? OR titolo LIKE
?` con `fetchone()` e senza `ORDER BY`. Il router non conosce gli id, e
passa una parte del titolo (`repertorio.py:120`). Nel database attuale
"conciliazione" corrisponde a 5 bandi, "formazione" a 5.

**Perché conta.** Il modello riceve il dettaglio di un bando diverso da
quello chiesto, lo presenta come quello chiesto, e il verificatore
conferma ogni dato perché è nella riga citata.

**Costo.** 1-2 ore. Con più corrispondenze, restituire l'elenco di titoli
e id con `trovato=False` invece di sceglierne uno; un test.

**Quando.** Prima della demo.

## 7. Le pagine scadute non si riesaminano mai

**Dove.** `src/estrazione/registro.py:12` e `:50-70`: ogni motivo che
inizia con "scaduto" è definitivo. In `scansioni` ce ne sono 65, tre
scaduti dopo maggio 2026 (TRANSCAN JTC 2026 il 21/07, premi per gli
imboschimenti il 30/06, musei ed ecomusei il 08/06).

**Perché conta.** Il passo 4 della roadmap prevede di ricontrollare le
proroghe, ma solo per i bandi in archivio. Una pagina giudicata scaduta
il giorno prima di una proroga resta fuori per sempre. È anche lo stato
"scaduto" memorizzato e riusato, contro il principio "lo stato si
calcola dalla scadenza".

**Costo.** 1-2 ore. Leggere la data dal motivo ("scaduto il AAAA-MM-GG")
e considerarlo definitivo solo oltre una soglia, come `MARGINE_GIORNI` in
`src/estrazione/scadenza.py`; due test in `test_acquisizione.py`.

**Quando.** Prima dell'aggiornamento automatico.

## 8. Correzioni a mano sovrascritte, e "verificato" che vuol dire "estratto"

**Dove.** `src/estrazione/salva.py:237-265`: ogni salvataggio riscrive
tutte le colonne di `bandi` e mette `verificato_il` a oggi. Le correzioni
di `correggi_atti` e `applica_regole_verifica` (12 novembre) non sono
protette, a differenza delle date con origine `manuale` (già in coda
nella roadmap). In più, `fonte_bando` (`interrogazioni_bandi.py:372-377`)
scrive al modello "(dati verificati il …)" con quella data: per 46 bandi
su 46 è la data dell'estrazione automatica, non di una verifica umana.
`territorio.csv` non ha alcuna data di verifica.

**Perché conta.** Con la riestrazione periodica dei bandi aperti, le
correzioni verificate a mano tornano ai valori sbagliati senza avviso. La
dicitura "dati verificati" fa presentare al modello un'estrazione
automatica come dato controllato, contro il principio "ogni dato ha la
sua fonte e la data di verifica".

**Costo.** Un giorno per la protezione (una colonna con i campi corretti
a mano, rispettata da `salva` e dalla fusione di `riclassifica_bandi`).
L'etichetta si cambia in pochi minuti ("estratti il …") e conviene farlo
subito.

**Quando.** Prima dell'aggiornamento automatico; l'etichetta prima della
demo.

## 9. Tre punti in cui database e CSV si separano

**Dove.**

- `src/database/schema.py:327-335`: `carica_csv` scarta le righe che
  violano un vincolo, stampa e prosegue. Basta rinominare un tipo in
  `TIPI_BENEFICIARIO`: alla ricreazione le righe di quel tipo spariscono, e
  il primo `aggiorna_csv("beneficiari_bando")` le cancella anche dal CSV.
- `scripts/tutorial/step4_crea_db.py` su un database esistente fa solo
  `INSERT OR REPLACE`: una riga tolta dal CSV resta nel database, e la
  prossima esportazione la rimette nel CSV.
- `scripts/ingestione/estrai_nuovi.py:359` e
  `scripts/manutenzione/riclassifica_bandi.py:359` esportano solo alla fine
  della corsa. Un Ctrl+C (`KeyboardInterrupt` non è preso da `except
  Exception`) o un errore fuori dal ciclo lasciano il database avanti ai
  CSV. In GitHub Actions, con un database che non sopravvive alla corsa,
  vuol dire estrazioni pagate e perse.

**Perché conta.** I CSV sono la fonte di verità e il database è "usa e
getta": tutti e tre i casi rompono questa regola senza messaggi d'errore.

**Costo.** Mezza giornata. `carica_csv` che si ferma con un errore se
scarta righe; `step4_crea_db` che parte sempre da un database vuoto;
esportazione in un `finally`.

**Quando.** Prima dell'aggiornamento automatico.

## 10. La demo legge il database del repository

**Dove.** `data/db/comune.sqlite` è versionato e l'app lo legge
(`app/app.py:158`, `src/config.py:26`). Ora risultano modificati, e non
committati, sia il database sia i CSV di `bandi`, `beneficiari_bando` e
`interventi_bando`. Nulla controlla che il database committato
corrisponda ai CSV committati.

**Perché conta.** Un commit che porta i CSV ma non il database (o il
contrario) e la demo mostra dati diversi da quelli verificati, senza che
nessun test se ne accorga. Il punto è già in coda nella roadmap, ma
lì non è legato alla demo.

**Costo.** Subito, un'ora: committare insieme database e CSV e
ricontrollare con un confronto riga per riga. Soluzione: l'app ricrea il
database dai CSV all'avvio, in una cartella temporanea; mezza giornata.

**Quando.** Prima della demo.

## 11. Pannello di verifica verde con zero dati verificati

**Dove.** `app/app.py:74-83`: il messaggio verde compare quando non ci
sono `non_trovato`, anche se tutti i dati sono `non_citato` o
`citazione_generica`. Una risposta con tre importi senza fonte mostra "0
dati verificati nella fonte citata" in verde. In
`scripts/tutorial/step3_verifica.py:9-13` manca `citazione_generica` in
`SIMBOLI`: alla riga 59 lo script si ferma con `KeyError` alla prima
citazione generica.

**Perché conta.** Il colore è quello che il consulente guarda. Lo script
è quello indicato dal README per interrogare da riga di comando.

**Costo.** Un'ora: verde solo se tutti i dati sono verificati, arancione
con dati non citati o generici; il simbolo mancante.

**Quando.** Prima della demo.

## 12. `bandi_in_scadenza` esclude gli sportelli con data di chiusura

**Dove.** `interrogazioni_bandi.py:557`, `AND a_sportello = 0`. Nel
database 15 bandi a sportello hanno una data di chiusura, tra cui
"promozione della conciliazione vita-lavoro 2026" (16/11/2026) e, per
Comuni e Unione, i contributi agli enti locali per lo sviluppo di
progetti (18/07/2027).

**Perché conta.** "Cosa scade nei prossimi due mesi?" è una domanda da
demo. Uno sportello con chiusura il 31/12 scade il 31/12 come un bando a
graduatoria, e oggi non compare.

**Costo.** 1-2 ore: includerli, con l'invito a verificare le risorse
nella riga (c'è già, `stato_sportello`); aggiornare
`test_in_scadenza_per_ente` e il riferimento di equivalenza se cambia.

**Quando.** Prima della demo.

## 13. Test assenti dove l'errore costa di più

**Dove.**

- Il percorso di `estrai_nuovi` (preselezione, `esamina`, `salva`,
  `registra`, esportazione) non ha un test: `tests/test_riclassifica.py:5`
  importa da lì solo `errore_bloccante`. È il codice che girerà da solo
  in GitHub Actions.
- Il verificatore non ha casi negativi di sottostringa (voce 1), di
  formato delle date (voce 4) o di decreti nel testo (voce 3).
- `app/app.py` non ha test: la logica del colore (voce 11) è lì.

**Perché conta.** Le voci 1, 3, 4 e 11 sarebbero emerse da un test; le
modifiche delle voci 7-9 toccano proprio il percorso non coperto.

**Costo.** Un giorno: un test di `estrai_nuovi` con un estrattore finto e
le pagine salvate in `tests/pagine/`, sul database di `conftest.py`;
spostare la scelta del colore in una funzione di `controllo.py`, che si
può provare senza Streamlit.

**Quando.** Prima dell'aggiornamento automatico; i casi del verificatore
insieme alle voci 1, 3 e 4.

## 14. Documenti non allineati al codice

**Dove.**

- `README.md:42`, "O c'è, o non c'è": vero solo come sottostringa (voce 1).
- `README.md:241-248`: la tabella dei CSV elenca enti, popolazione,
  territorio, bandi, scansioni; mancano `fonti`, `beneficiari_bando`,
  `interventi_bando`, `scadenze_bando`. "Dopo ogni estrazione, bandi e
  scansioni vengono riversati": oggi sono cinque tabelle.
- `README.md:270-272`, "assistita, non automatica… i campi critici
  richiedono conferma": vale per `estrai_bando`, non per `estrai_nuovi`,
  che salva da solo.
- `README.md:432`, "I bandi distinguono solo se ammettono i comuni. Non è
  registrato se ammettono le Unioni": superato, `beneficiari_bando` ha 10
  righe `unione_comuni` e tutti i 46 bandi sono classificati.
- `docs/roadmap.md:3` "Stato al 11 novembre", `:28-30` "In corso: verifica
  a mano di 20 bandi", `:34` tappa 5b "prima della demo": tutto fatto.
  `:116` "oggi l'estrattore ne tiene una sola": c'è `scadenze_bando`.
  `:100` "`date.today()` in 9 punti": oggi 6 in `src/`, più 2 punti che
  usano già `Europe/Rome` (`salva.py:130`, `estrai_nuovi.py:139`), quindi
  due date diverse nello stesso salvataggio a ridosso della mezzanotte.
- `docs/piano-estrattore.md:199` "risultato da aggiungere" e
  `docs/piano-post-scansione.md:282` (scadenze multiple, professionisti in
  coda): fatti.

**Perché conta.** Il README è la pagina da cui parte il link alla demo; le
frasi superate descrivono limiti che non ci sono più e garanzie più forti
di quelle reali.

**Costo.** 2 ore.

**Quando.** Prima della demo.

## 15. La fonte dei bandi è scritta nel codice

**Dove.** `src/estrazione/elenco.py:14-16` (codice, URL dell'elenco e
base del portale regionale), `scripts/ingestione/estrai_nuovi.py:58` e
`scripts/ingestione/estrai_bando.py:37` (nome della fonte). La tabella
`fonti` ha `url_elenco` e `url_base`, ma nessun modulo li legge.

**Perché conta.** Il primo passo della roadmap (GAL MontagnAppennino) e
l'aggiornamento periodico su più fonti richiedono di scorrere le fonti;
oggi aggiungerne una vuol dire duplicare script. Anche le regole di
lettura della pagina (preselezione sul campo "Data di scadenza
presentazione domande", filtro sull'anno nello slug) sono del portale
regionale e vanno legate alla fonte.

**Costo.** Un giorno, con i test di `test_fonti.py` da estendere.

**Quando.** Prima dell'aggiornamento automatico (è il passo 1 della
roadmap).
