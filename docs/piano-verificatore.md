# Piano: blocco A, verificatore

Approvato il 12 novembre 2026, con le decisioni in fondo al file. Copre
le voci 1, 3, 4 e 11
di `docs/revisione-2026-11-12.md`. Se la conversazione con Claude Code
viene azzerata, si riparte leggendo questo file.

## Obiettivo

Un dato è verificato solo se il suo **valore** compare nella fonte
citata. Non basta che la sua scrittura sia contenuta in un'altra
("8" dentro "80", "50000" dentro "150000", "3 novembre" dentro "13
novembre"). Uno stesso valore, scritto in forme diverse, si riconosce
come uguale ("31/07/2027", "31 luglio 2027", "2027-07-31"). Il pannello
dell'app non dà il verde se non ha verificato niente.

## Decisioni proposte

### Un modulo unico per i valori: `src/normalizzazione.py`

Sta in `src/` e non in `src/verification/`: lo useranno sia il
verificatore sia, per la voce 2, l'estrattore. Funzioni pure, senza
database né modello:

- `numero(testo) -> Decimal | None`: un numero scritto all'italiana. La
  regola del punto è quella che l'estrattore usa già
  (`DECIMALE_COL_PUNTO` in `src/estrazione/bandi.py`): un punto seguito da
  tre cifre separa le migliaia ("12.500" = 12500), seguito da una o due
  cifre finali è decimale ("9.2" = 9,2). La virgola è sempre decimale. Gli
  zeri decimali non contano: "322,00" e "322" sono lo stesso valore.
- `data(testo) -> str | None`: una data in ISO. Forme riconosciute:
  - ISO, `2027-07-31`;
  - numeriche, `31/07/2027`, `31-07-2027`, `31.07.2027`, con giorno e mese
    di una o due cifre;
  - in lettere, `31 luglio 2027`, anche con `1°` o `1º` per il primo del
    mese.

  Giorno e mese devono esistere: `41/20/2022` non è una data.
- `giorno_mese(testo) -> str | None`: per le date senza anno ("15
  ottobre", "30/06"), nella forma `MM-GG`.
- `valori(testo) -> Valori`: tutti i valori di un testo, divisi per
  famiglia: date (ISO), giorni del mese (`MM-GG`, ricavati anche dalle
  date complete), anni, orari, percentuali, numeri, riferimenti. Si
  leggono in quest'ordine, e una porzione già letta non si rilegge, come
  fa oggi `trova_dati`: le cifre di "28/04/2026" sono una data, non i
  numeri 28, 4 e 2026. L'anno di una data però si conta anche tra gli
  anni, così "nel 2026" resta verificabile su un testo che contiene solo
  "28/04/2026".
- `MESI` passa da `controllo.py` a questo modulo.

### Confronto su valori interi, mai su sottostringhe

Per ogni fonte (frammento `n`, blocco `Dn`, bando `Dn.k`) si calcola una
volta `valori(testo)`. Un dato della risposta si converte con le stesse
funzioni e si cerca nella famiglia giusta:

| tipo del dato | si cerca tra |
|---|---|
| importo, quantità | i numeri e le percentuali della fonte (un importo in una tabella spesso è scritto senza "€") |
| percentuale | solo le percentuali della fonte: "7%" non si conferma con un "art. 7" |
| data con anno | le date della fonte |
| data senza anno | i giorni del mese della fonte |
| anno | gli anni della fonte, comprese le date |
| orario | gli orari della fonte |
| riferimento ("41/2022", "art. 54"), codice (CUP, CIG) | i riferimenti e i codici della fonte, come parole intere, con i confini |

Il testo normalizzato con `normalizza` non serve più al confronto: la
funzione si toglie, e con lei la variante `re.sub(r"\.00$", ...)`.
Restano invariati `trova_citazioni`, `frammenti_citati`,
`FINESTRA_CITAZIONE` e la logica di `citazione_generica`, che passa dal
confronto per sottostringa (`voci_con`) all'appartenenza ai valori del
bando.

### Numeri di decreto e delibera nel testo della risposta

Oggi `SCHEMA_ATTO` maschera ogni riferimento ad atto, ovunque sia, e i
numeri d'atto si controllano solo nelle citazioni a `[Dn.k]`.

- La maschera vale solo **dentro le citazioni** `(fonte: ...)`. Fuori,
  "decreto dirigenziale n. 9550 del 28/04/2026" diventa un dato di tipo
  `atto` con valore `9550`. La data dell'atto fa parte del riferimento e
  non si controlla da sola: si maschera insieme al numero.
- Lo schema del numero d'atto nel testo è più stretto di quello delle
  citazioni (`SCHEMA_NUMERO_ATTO`). Tra la parola (decreto, delibera,
  deliberazione, DGR, DD, D.G.R., D.D.) e il numero sono ammesse solo
  qualificazioni ("dirigenziale", "regionale", "di Giunta regionale", "del
  Presidente") e "n.", "n°", "numero". Così "Il decreto prevede € 322,00"
  non produce un atto 322: è il caso 15 del collaudo, che deve restare
  com'è.
- Un atto nel testo si controlla sulle fonti citate dopo di esso, come
  ogni altro dato, con `contiene_numero`.
- Per i frammenti documentali il testo di confronto **degli atti** è il
  testo del frammento più `riferimento_atto` e `titolo` dei metadati.
  Sono i campi che il modello vede nell'intestazione `[n] ... atto: ...`
  (`etichetta` in `src/chains/rag.py`). Per gli altri dati il testo di
  confronto resta il solo testo del frammento: una data presente solo
  nell'intestazione non si deve verificare.
- `_verifica_atti` sulle citazioni a `[Dn.k]` resta com'è. In più
  controlla anche i numeri d'atto delle citazioni a un frammento `[n]`,
  sul testo di confronto degli atti appena descritto. Non si estende
  alle citazioni a `[Dn]`: con il blocco non si sa di quale bando sia
  l'atto (`test_decreto_con_il_blocco_non_si_controlla`, invariato).
- "D.Lgs. 231/2007" e simili restano riferimenti normativi (tipo
  `riferimento`), non atti: sono già controllati così (caso 18).

### Pannello di verifica

- Funzione nuova `giudizio(esiti) -> tuple[str, str]` in
  `controllo.py`, che restituisce il livello e il messaggio. Si prova
  senza Streamlit.
  - `rosso`: almeno un `non_trovato`;
  - `verde`: almeno un dato verificato che non sia un anno, e nessun
    `non_citato` né `citazione_generica`;
  - `arancione`: nessun `non_trovato`, ma dati non citati o citati con il
    blocco, oppure nessun dato verificato a parte gli anni;
  - `nessuno`: nessun dato da verificare.
- `app/app.py` usa `giudizio` al posto del confronto attuale (righe
  74-83).
- `scripts/tutorial/step3_verifica.py`: `citazione_generica` in `SIMBOLI`
  (oggi si ferma con `KeyError`), e il riepilogo finale stampa anche le
  citazioni generiche quando ci sono.
- `scripts/diagnostica/confronta_recupero.py` stampa `riassumi` così com'è
  e non ha `SIMBOLI`: non cambia.

## File

| file | cosa |
|---|---|
| `src/normalizzazione.py` | nuovo: `numero`, `data`, `giorno_mese`, `valori`, `MESI` |
| `tests/test_normalizzazione.py` | nuovo: ogni forma di data e di numero, valori impossibili, ordine di lettura |
| `src/verification/controllo.py` | confronto sui valori; atti nel testo; testo degli atti dei frammenti con i metadati; `giudizio` |
| `tests/test_verifica.py` | casi nuovi del collaudo (sotto); test di `giudizio` |
| `tests/test_verifica_bandi.py` | un caso: data in lettere contro la riga ISO del bando |
| `app/app.py` | il pannello usa `giudizio` |
| `scripts/tutorial/step3_verifica.py` | `SIMBOLI` completo, riepilogo |

Chi importa da `controllo.py`: `app/app.py`,
`scripts/tutorial/step3_verifica.py`,
`scripts/diagnostica/confronta_recupero.py` (`riassumi`, `verifica`) e
`tests/test_verifica_bandi.py` (anche `numeri_atto`). Nessuno importa
`normalizza`, `maschera_citazioni`, `trova_dati`, `SCHEMI` o `MESI`, quindi
spostarli o toglierli non tocca altri file.

L'estrattore non cambia in questo blocco: userà il modulo per la voce 2,
prima dell'aggiornamento automatico.

## I 18 casi originali

I 17 casi di `CASI` e `test_tipi_data_e_orario`. Effetto previsto delle
regole nuove:

| # | caso | atteso oggi | con le regole nuove |
|---|---|---|---|
| 1 | importo corretto | 1 verificato | invariato |
| 2 | importo INVENTATO | 1 non trovato | invariato |
| 3 | importo giusto, frammento SBAGLIATO | 1 non trovato | invariato |
| 4 | importo SENZA citazione | 1 non citato | invariato |
| 5 | cifra alterata di poco | 1 non trovato | invariato |
| 6 | percentuale corretta | 1 verificato | invariato: "7%" è tra le percentuali del frammento 3 |
| 7 | percentuale INVENTATA | 1 non trovato | invariato |
| 8 | formattazione diversa dello stesso importo | 1 verificato | invariato: 322,00 euro = € 322,00 |
| 9 | rifiuto: nessun dato | niente | invariato |
| 10 | dato numerico corretto | 1 verificato | invariato |
| 11 | dato numerico ALTERATO | 1 non trovato | invariato |
| 12 | **riferimento all'atto in prosa, non citazione** | 1 verificato | **1 verificato, 1 non trovato** |
| 13 | citazione con testo prima di fonte | 1 verificato | invariato |
| 14 | importo con decimali non spezzato | 1 verificato | invariato |
| 15 | importo tra nome atto e data NON deve sparire | 1 verificato, 1 non trovato | invariato, con lo schema stretto dell'atto |
| 16 | separatore migliaia dentro una frase | 2 verificati | invariato |
| 17 | data ISO e orario sono date | 2 non trovati | invariato |
| 18 | riferimento normativo corretto ma assente | 1 non trovato | invariato |
| 18b | `test_tipi_data_e_orario` | tipi e valori | invariato: i tipi restano `data` e i valori come scritti |

### Il caso 12 cambia: perché, e cosa propongo

Risposta: "Secondo il Decreto dirigenziale n. 9550 del 28/04/2026, il
costo è € 322,00 (fonte: [1], Regione, pag. 11)."

Il caso è nato per controllare che il riferimento all'atto non faccia
sparire l'importo, e quella parte resta vera: € 322,00 è ancora
verificato. Ma con la voce 3 il decreto 9550 diventa un dato, e il
frammento 1 non lo contiene, né nel testo né nei metadati
(`{"ente": "Regione Toscana", "pagina": 11}`). L'esito corretto è quindi
"non trovato": il decreto è citato su una fonte che non lo riporta, cioè
proprio l'errore che oggi passa senza segnalazioni.

Proposta: il caso resta con la stessa risposta e gli stessi frammenti.
Cambiano l'atteso, `{"verificato": 1, "non_trovato": 1, "non_citato": 0}`,
e il nome, che diventa "atto in prosa: importo verificato, decreto non
nella fonte". Accanto si aggiunge un caso gemello che verifica il decreto
(sotto, caso N8). In alternativa si potrebbe aggiungere
`riferimento_atto` ai metadati del frammento 1. Non lo propongo: il caso
15 cita la stessa data 28/04/2026 sul frammento 1 e si aspetta "non
trovato", e lo resta solo se la data dei metadati vale per gli atti e
non per le date, come previsto sopra. È una dipendenza fragile tra due
casi.

**Da approvare prima di toccarlo.**

## Casi nuovi del collaudo, in `test_verifica.py`

Un quarto frammento, aggiunto in fondo a `FRAMMENTI` (non cambia la
numerazione dei primi tre):

> "Il contributo è pari all'80% della spesa ammissibile, fino a
> € 150.000,00. Le domande si presentano entro il 13 novembre 2026. Il
> bando è approvato con decreto dirigenziale n. 1234 del 12/03/2026."

E un risultato di bando per le date in formati diversi, con la riga
"«Bando di prova» (Regione Toscana) | scade il 2027-07-31 (fra 261
giorni) | atto: decreto dirigenziale n. 18191".

| # | caso | risposta (abbreviata) | atteso |
|---|---|---|---|
| N1 | percentuale contenuta in un'altra | "copre l'8% (fonte: [4])" | 1 non trovato |
| N2 | percentuale intera, controllo | "copre l'80% (fonte: [4])" | 1 verificato |
| N3 | importo contenuto in un altro | "fino a € 50.000 (fonte: [4])" | 1 non trovato |
| N4 | importo intero, controllo | "fino a € 150.000 (fonte: [4])" | 1 verificato |
| N5 | giorno contenuto in un altro | "entro il 3 novembre 2026 (fonte: [4])" | 1 non trovato |
| N6 | giorno intero, controllo | "entro il 13 novembre 2026 (fonte: [4])" | 1 verificato |
| N7 | decreto inventato nel testo | "approvato con decreto n. 9999 del 12/03/2026 (fonte: [4])" | 1 non trovato, tipo `atto` |
| N8 | decreto giusto nel testo | "approvato con decreto dirigenziale n. 1234 del 12/03/2026 (fonte: [4])" | 1 verificato, tipo `atto` |
| N9 | data numerica contro riga ISO | "scade il 31/07/2027 (fonte: [D1.1], decreto dirigenziale n. 18191)" | 2 verificati (data e atto) |
| N10 | data in lettere contro riga ISO | "scade il 31 luglio 2027 (fonte: [D1.1], ...)" | 2 verificati |
| N11 | giorni contenuti in un altro numero | "mancano 26 giorni (fonte: [D1.1], ...)" | 1 non trovato, 1 verificato (l'atto) |

Gli anni non compaiono negli attesi: nessuna di queste risposte ne
contiene uno da solo.

Test di `giudizio`, sugli esiti costruiti a mano: solo anni verificati
(arancione), un verificato e un non citato (arancione), un non trovato
(rosso), tutti verificati (verde), nessun esito (nessuno).

## Ordine e fermate

Una fermata dopo ogni passo, con `ruff check`, `python -m pytest` e
l'output di entrambi.

1. `src/normalizzazione.py` e i suoi test. Nessun altro file cambia.
2. Confronto sui valori in `controllo.py`; casi N1-N6, N9-N11. I 18 casi
   originali devono passare tutti senza modifiche: il caso 12 non cambia
   ancora, perché gli atti nel testo arrivano al passo 3.
3. Atti nel testo e testo degli atti dei frammenti con i metadati; casi
   N7-N8; caso 12 aggiornato **solo se approvato**. Prima di toccarlo,
   l'output del test fallito, per vedere che fallisce come previsto e non
   in un altro modo.
4. `giudizio`, pannello dell'app, `step3_verifica`; importazione degli
   script modificati (`python -c "import scripts.tutorial.step3_verifica"`).
   Controllo a mano dell'app con una risposta già salvata, senza
   chiamare il modello: `mostra_verifica` riceve un dizionario.

Il test di equivalenza (`tests/test_uguale_per_comuni.py`) non dipende
dal verificatore e non deve cambiare.

## Decisioni del 12 novembre 2026

- Caso 12: nuovo atteso approvato (1 verificato, 1 non trovato). Il nome
  dice cosa controlla ora: "atto in prosa: importo verificato, decreto
  assente dalla fonte". Caso gemello N12: lo stesso decreto citato su un
  quinto frammento che lo riporta nei metadati (`riferimento_atto`) e
  contiene € 322,00: 2 verificati, l'importo e l'atto.
- Percentuali: contano anche i "punti percentuali", e nient'altro.
- Importi con moltiplicatore, aggiunti al collaudo. Il quarto frammento
  contiene anche "una dotazione complessiva di 19.5 milioni di euro":
  - N13: "19,5 milioni di euro (fonte: [4])", 1 verificato;
  - N14: "19,8 milioni di euro (fonte: [4])", 1 non trovato.

  `numero` e `valori` leggono "mila", "milioni", "miliardi" e "mln" come
  l'estrattore (`MOLTIPLICATORI` in `src/estrazione/bandi.py`): il valore è
  quello moltiplicato, così "19,5 milioni" e "19.500.000" coincidono.
- Alla fine del passo 4 si prepara la prova con il modello vero, senza
  lanciarla: la fa l'utente dall'app.
- Articoli (decisione del passo 2): "art. 54" si confronta solo con gli
  articoli della fonte, mai con i suoi numeri; lo stesso per i
  riferimenti n/aaaa, solo con i riferimenti. Famiglia `articoli` in
  `Valori`, con articoli, paragrafi, punti e lettere; i loro numeri non
  sono piu' tra i numeri. Casi N15 (art. 54 su un frammento con "54
  euro": non trovato) e N16 (art. 54 nel frammento: verificato).
- Riferimenti n/aaaa (decisione del passo 3): "1234/2026" e' verificato
  se la fonte contiene quella forma oppure lo stesso numero d'atto con
  una data dello stesso anno ("decreto n. 1234 del 12/03/2026"). Casi N17
  (verificato) e N18 (1234/2025, non trovato). In piu' del previsto: N19
  e N20, il decreto nella citazione di un frammento, verificato sui
  metadati del frammento 5 e non trovato sul frammento 1.
- Data di un atto (decisione prima del passo 4): la data di "decreto
  9550 del 28/04/2026" scritto nel testo e' un esito a se', di tipo
  `data`. Si cerca dove e' stato trovato il numero, quindi anche nei
  metadati del frammento, e deve comparire insieme a quel numero
  (`atti_con_data` in `src/normalizzazione.py`). Se il numero non e' stato
  trovato, la data non si giudica: l'esito dell'atto copre gia' il
  riferimento, e il caso 12 resta com'era. Le altre date si cercano solo
  nel testo. Casi N21 (numero e data nei metadati: 2 verificati) e N22
  (data diversa: data non trovata, con la data della fonte nel
  dettaglio); N8 e N12 passano a 2 e 3 verificati.
- Prova con il modello vero: `docs/prova-verificatore.md`.

## Decisioni dopo la prova (12 novembre 2026)

- Confermato: la data di un atto non si giudica se il numero non e'
  trovato.
- La data si controlla anche per gli atti scritti nelle citazioni a
  `[Dn.k]` e a `[n]` (`date_degli_atti` in `src/normalizzazione.py`), con
  la stessa regola. Prima, l'atto di parcheggi-2026 e' stato completato
  con la data (`correggi_atti`). Casi N19 (3 verificati), N23 (data
  sbagliata nella citazione) e due casi in `test_verifica_bandi.py`
  (riga senza data, riga con data in lettere).
- Per `[Dn.k]` vale solo la **data** dell'intestazione del blocco, non i
  suoi numeri: "12 in archivio" non verifica un 12 citato con la riga di
  un bando, e lo verifica se citato con `[Dn]`.
- P1: elenco chiuso delle qualificazioni allargato ("toscana", "regione
  toscana", "della regione toscana", "RT"), parole "DGRT" e "D.G.R.T.";
  parole libere sempre escluse. Caso N24 e `test_che_cosa_e_un_atto`.
- P4: limite aggiunto al README.
- P2 e P3 approvate, da fare dopo. P2 parte da un insieme di prova del
  recupero, senza modello.
