# Revisione dei prompt, 18 novembre 2026

- Data: 18/11/2026.
- Prompt revisionati: `ISTRUZIONI` (`src/chains/rag.py`) e `ISTRUZIONI_ROUTER`
  (`src/chains/router.py`) al commit `715b411`.
- Nota: Revisione esterna da un modello. Non applicata: mappa per la divisione
  della risposta in passi (roadmap, Indicazioni del revisore tecnico, punto 6).

Il testo che segue è la revisione com'è stata ricevuta, senza correzioni.

---

Leggo i tre JSON e i due prompt nel repository, poi ti do l'elenco dei problemi.

Ho letto per intero i due prompt, `repertorio.py`, C02 e C03. Di P11 ho letto le 22 righe dei dati e, estratti con uno script, risposta, contesto, profilo e verifica; ho saltato solo il blocco `voci`, che ripete le stesse righe.

**In breve**: il difetto principale è che ISTRUZIONI descrive almeno sei forme di risposta senza un ordine di precedenza, collegate solo da rimandi locali ("non vale per…, lì vale…"). In C02 la causa è il router, non la risposta.

## 1. Contraddizioni, per gravità

**1. Rifiuto contro bandi generici, e la toppa che li collega** (b per il giudizio, a per la forma)
- «Se i frammenti parlano di un argomento diverso, anche vicino, la risposta resta "Non trovo la risposta nei documenti disponibili."»
- «Se i DATI elencano bandi per un beneficiario generico (le imprese, le Pmi, i datori di lavoro privati) senza un settore che escluda il caso chiesto, nominali come possibili»
- La toppa: «Un bando dei DATI che ammette il tipo di beneficiario della domanda non è un argomento vicino».

Presa alla lettera, la toppa vieta il rifiuto per ogni domanda del Comune: tutte le righe di `bandi_aperti_per_ente` ammettono il Comune per costruzione. Ma la regola a cui rimanda ha solo esempi privati.
Caso: C03. Sette bandi che ammettono il Comune, nessuno sugli uffici. Il modello non sa se rifiutare o elencare e inventa una terza forma.

**2. Tre formule obbligatorie per "niente di specifico"** (a)
- «scrivi esattamente: "Non trovo la risposta nei documenti disponibili."»
- «di' che non ci sono bandi specifici in archivio e che questi bandi generici potrebbero valere»
- «Non dire che non esistono altri bandi: di' che sono quelli in archivio con dati completi.»

Caso: P11 apre con «Negli archivi non risultano bandi specifici», senza "con dati completi". Intanto l'app mostra sotto un bando da approfondire sugli interessi, che il modello non vede.

**3. Il filtro dei generici guarda solo il settore** (b)
- «senza un settore che escluda il caso chiesto»
- «Un frammento che parla di un argomento vicino ma non della cosa chiesta NON è una risposta.»
- L'esempio «raggruppati per tipo di aiuto (per esempio abbattimento degli interessi, garanzie)» spinge verso aiuti che non sono a fondo perduto.

Finalità e forma dell'aiuto non sono criteri. Caso: P11, vedi sezione 4.

**4. "Non deduci" e divieto di fusione contro i confronti** (a)
- «non completi con ciò che ti sembra plausibile, non deduci»
- «Non combini mai dati di documenti diversi in una stessa affermazione.»
- L'esempio: «il Comune ne ha 1.834 (fonte: [D2], …), quindi rientra nella soglia.»

L'esempio è una deduzione e fonde due fonti in una frase. In più:
- «Se un bando indica "ammesso se ...", … riporta la condizione, non rispondere con un semplice sì.»

Caso: Fondo strade, «ammesso se popolazione fino a 5.000 abitanti, che non hanno beneficiato finora di alcun finanziamento». Una regola chiede di concludere sulla soglia, l'altra di non concludere. Il comportamento giusto (concludere sulla soglia, lasciare aperto il resto) non è scritto.

**5. Chi chiede si decide due volte, con criteri diversi** (b, meglio nel router; a per la riga fissa)
- «Se la domanda può venire da tutti e due (nessun soggetto nominato), rispondi per il soggetto privato»
- «Usalo per valutare se l'ente rientra tra i beneficiari di un bando quando a chiedere è l'ente.»
- La riga fissa: «Se a chiedere è il Comune, questi bandi non lo ammettono».

Il router ha già deciso scegliendo l'interrogazione, e la regola della risposta dipende da quella scelta («e i DATI sono bandi per un tipo di beneficiario privato»).
Caso: "Ci sono bandi per il turismo?" porta a `bandi_per_tema`, con righe `[ammessi: Comuni, …]`. Lì la riga fissa è falsa.

**6. Bandi scaduti: tre percorsi, tre comportamenti** (a)
- «Questa sezione non vale per il gruppo "Scaduti, solo come storico" degli elenchi per tema.» Nessun'altra regola dice cosa farne.
- «Un bando scaduto non si presenta come opportunità attuale: se ne riporta il contenuto insieme allo stato»
- «Per ciascuno cita la scadenza con l'etichetta del bando.»

Lo stesso bando scaduto va riportato se arriva da un frammento, dettagliato se arriva da `bandi_scaduti_per_ente`, senza regola se arriva da un elenco per tema.
Caso: C02, [D1.3] Toscana diffusa, scaduto da 17 giorni, con il Comune in Toscana diffusa: la risposta tace.

**7. Bando cercato per nome contro il router** (a per l'innesco, b per "stesso argomento")
- Router: «per titolo, per nome proprio o per il suo oggetto ("il bando per i mercati rionali"), usa dettaglio_bando»
- Risposta: «in archivio non c'è un bando con quel nome» e «il nome del bando l'ha già dato chi chiede».

Caso: "Quanto dà il bando per le strade franate?". Nessun nome dato; se `dettaglio_bando` non trova niente, il rifiuto è obbligato anche se il Fondo strade è in archivio. Le altre intestazioni di `dettaglio_bando` («Corrispondenza parziale per», trovato nei beneficiari o negli interventi, elenco breve oltre 3) non hanno alcuna regola.

**8. DATI "certificati" contro gerarchia delle fonti** (a)
- «Provengono da un archivio statistico interrogato con query verificate, non da testo estratto. Sono affidabili»
- «avviso_pubblico e delibere: vincolano»
- «li riporti entrambi, separatamente, … e segnali che si riferiscono ad ambiti distinti»

Le righe dei bandi sono testo estratto («dati estratti il»). Caso ipotetico: "Quando scade il bando mercati rionali?", con un frammento che riporta il 15/09/2026 e i DATI il 15/10 prorogato. La fusione impone di chiamarli "ambiti distinti", ed è falso: uno è superato.

**9. «Usi sempre questa forma esatta» contro altre quattro forme di citazione** (c, componibile dal codice)
La forma con «pag. <n>» è dichiarata unica; poi arrivano «(fonte: [D1], <fonte indicata>)», «(fonte: [D1.2], <atto del bando>)», la forma senza atto e «(fonte: profilo dell'ente)». P11 ne produce una sesta: «(fonte: [D1.5], fonte Incentivi Italia, …)».

**10. «Se non ricevi alcun DATO…»: regola irraggiungibile** (a)
`con_popolazione` aggiunge sempre un blocco, quindi per un Comune i DATI non sono mai vuoti. Il segnaposto «(nessun dato numerico richiesto)» afferma comunque sempre il primo dei due casi che la regola chiede di distinguere.

**11. Meccanismi interni e "controllo mirato": stesso divieto, ambiti diversi** (c)
- «Non parlare di frammenti, dati forniti, interrogazioni, parametri o temi dell'archivio» sta dentro QUANDO NON RISPONDERE.
- «Non nominare interrogazioni, parametri, codici dei tipi di beneficiario» sta in COSA PUÒ FARE L'APP.

P11 scrive «i dati disponibili non specificano» in una risposta che non è un rifiuto: vietato dalla prima lista, non dalla seconda. Lo stesso vale per «Se vuole un controllo mirato»: condizionato nella prima sezione, libero nella seconda.

## 2. Dove dovrebbe vivere ogni regola

| Sezione | Gruppo | Nota |
|---|---|---|
| Regola fondamentale | c | "Non deduci" va tolto: le deduzioni ammesse passano ad a e b |
| Citazione obbligatoria, etichette, atto della riga | c | Se il passo 3 riceve le citazioni già composte, diventa a |
| Divieto di fusione, gerarchia, studio | c | Il conflitto frammento/DATI sullo stesso bando è a |
| Indirizzi web, valore calcolato, data dell'archivio | c | |
| "Nessun DATO" | a | Il codice sa cosa ha interrogato |
| Scelta tra rifiuto, parziale, generici, elenco | a | A partire dalle etichette del passo 1 |
| "Argomento vicino", pertinenza dei frammenti | b | |
| Frase esatta del rifiuto | a | Testo fisso: lo scrive il codice |
| Riga "servirebbe…" | c | |
| "Controllo mirato" | b poi a | Il classificatore dice quali condizioni restano aperte |
| Bando per nome | a | L'innesco è una stringa del codice; "stesso argomento" è b |
| Cosa può fare l'app, punteggiatura | c | I trattini sono anche controllabili a valle |
| Soglia di abitanti, regione, Toscana diffusa, "non verificato" | a | Campi strutturati contro profilo |
| "Ammesso se" | a o c | a se la condizione è un campo; altrimenti c |
| "Non classificati", "a sportello", "dati completi" | a | Già nel testo della riga o noto al codice |
| Chi chiede | b | Una volta sola, nel router o nel passo 1 |
| Riga "Se a chiedere è il Comune" | a | Dipende da `[ammessi: …]` |
| Divieto su ATECO, forma giuridica, sede | c | |
| Generici: quali | b | Con finalità e forma dell'aiuto, non solo settore |
| Generici: tetto 3-5, mai elenco completo | a | |
| Generici: raggruppamento | c | |
| Scaduti, stato nei frammenti | a | Nota su annualità e "ricorrente" restano c |

## 3. Ridondanze

- Argomento vicino: due frasi consecutive in QUANDO NON RISPONDERE, più PERTINENZA.
- Conoscenze proprie: REGOLA FONDAMENTALE e «Non completare con conoscenze tue».
- Non dedurre: REGOLA FONDAMENTALE, «dillo, invece di dedurlo», «nemmeno come ipotesi», «Non fare previsioni».
- Atto di un altro bando: «non attribuire a un bando l'atto di un altro» e «Non prendere mai un atto da un'altra riga».
- Studio: «non va mai presentato come una prescrizione» e «si presenta come tale».
- Scaduto non è opportunità: in entrambe le sezioni sugli scaduti.
- Meccanismi interni: due liste diverse (punto 11).
- "Controllo mirato": tre volte.
- Sportello: la regola ripete ciò che ogni riga già dice.
- Doppia citazione nella soglia: detta due volte nello stesso capoverso.

## 4. I tre JSON

**C02: causa nel router.** Il Fondo strade ha tema `mobilita` in `bandi.csv`; il router ha chiesto `bandi_per_tema` con `territorio`, tre volte su tre. Il bando non è mai arrivato al modello, e con quei dati il rifiuto è coerente con il prompt. `docs/piano-insieme-prova.md` dice la stessa cosa. Due difetti secondari lato risposta:
- La riga «servirebbe un bando specifico per la difesa del suolo» ricalca l'esempio del prompt e dichiara assente dall'archivio ciò che non è stato cercato.
- Il silenzio su [D1.3] viene dal punto 6.

**C03: punti 1 e 2.** La risposta chiude con «Non trovo quindi, tra i bandi in archivio…», una parafrasi a metà tra rifiuto e generici. Cita Punti Digitale Facile per dire «non lo presento come pertinente»: PERTINENZA dice «li ignori, senza citarli» solo per i frammenti. Effetto sulla misura: `attese_esito` segna il bando come trovato e il giudizio è verde, ma la risposta lo ha scartato e ne ha taciuto la scadenza a 10 giorni. Il test passa per corrispondenza di stringa. La condizione «ubicato in Toscana» risolta con il profilo è il punto 4.

**P11: punto 3.** Internazionalizzazione, registrazione IGP e cloud vengono proposti a chi vuole aprire un'attività, perché il filtro guarda solo il settore. Il titolo «Contributi a fondo perduto per progetti d'impresa» non ha appoggio: le righe dicono «contributo fino a…», mai "fondo perduto". Il verificatore non lo vede perché non è un numero. Il secondo gruppo (interessi e garanzie) segue l'esempio del prompt. In `bandi.csv` non c'è una colonna per la forma dell'aiuto: il criterio a mano «distinguere fondo perduto da prestiti e garanzie» oggi si può soddisfare solo dai titoli.

## 5. ISTRUZIONI_ROUTER

1. **Comune più argomento: due regole, nessuna precedenza.** «Una domanda come "possiamo partecipare a qualche bando?" richiede bandi_aperti_per_ente» contro «bandi_per_tema serve solo per le domande generiche su un argomento». C02 e C03 hanno la stessa struttura e vanno su interrogazioni diverse. Il Fondo strade era la riga 3 di `bandi_aperti_per_ente` in C03.
2. **Tutti e sette gli esempi hanno al massimo un'interrogazione.** «Puoi indicare entrambe le cose» parla di documenti più interrogazioni, non di due interrogazioni. Nei tre JSON: una sola, nove chiamate su nove.
3. **Temi senza definizione.** Il router riceve dodici parole. "Strada franata" sta tra territorio, mobilità e ambiente, e il ripiego sui titoli scatta solo se il tema è vuoto.
4. **Scadenze e importi assegnati a due archivi.** Il documentale «Risponde a domande su regole, requisiti, scadenze, importi di bandi»; più sotto, per «scadenze o ammissibilità, usa le interrogazioni sui bandi». E «Elenca una o più interrogazioni se la domanda riguarda dati numerici»: i bandi non lo sono.
5. **L'esempio «Quali sono i requisiti per accedere al bando?»** dà zero interrogazioni, contro la regola sull'ammissibilità.
6. **Tabella VUOTA:** «non attivare i documenti: il dato non è disponibile in nessun archivio» contro «"documenti": true se la domanda riguarda… contenuti di atti». Una domanda sui flussi turistici perde anche gli studi.
7. **Un solo tipo di beneficiario per chiamata.** Un agriturismo sta sia in `impresa_agricola` sia in `impresa_turistica`; nessun esempio mostra due chiamate.
8. **Oggetto contro argomento:** il confine tra `dettaglio_bando` e `bandi_per_tema` non è definito. Vedi punto 7 della sezione 1.

## Cosa non posso stabilire dai file

- Se con `bandi_aperti_per_ente` la risposta avrebbe nominato il Fondo strade: i tuoi documenti dicono di sì nelle registrazioni precedenti, questi tre JSON non lo provano.
- Se l'eco di "difesa del suolo" in C02 viene dall'esempio del prompt o dalla domanda.
- Con che criterio sono assegnati i temi ai bandi.
- Se l'archivio documentale contiene il testo del bando sulle progettualità sui dati. In C03 `documenti` è false e le righe di elenco non riportano gli interventi finanziati, quindi la pertinenza è giudicata dal solo titolo. Il passo di classificazione avrà lo stesso limite se riceve le stesse righe.
- Il caso del punto 8 (due date per i mercati rionali) è costruito dai metadati: non ho una registrazione in cui succede.

---

## Controllo delle citazioni (18/11/2026)

67 citazioni tra « ». Ognuna è cercata a meno di spazi e a capo:
- nel valore di `ISTRUZIONI` e `ISTRUZIONI_ROUTER`, identici al commit
  `715b411` (nessuna modifica a `src/` fino a `d8677a0`);
- per quelle che citano risposte, dati o attese, nei JSON della regressione
  finale del 16/11/2026: C03 e P11 in `lotto_1/2026-11-16_111330`, C02 in
  `lotto_4/2026-11-16_113300`. La revisione non dice quale registrazione ha
  letto: è un'ipotesi.

Con "…" dentro la citazione, i tratti si cercano nell'ordine, a meno di 400
caratteri l'uno dall'altro; con "…" in fondo, si cerca il tratto che lo
precede.

Esito:
- **64 trovate** nel file indicato dal contesto.
- **1 diversa**: «servirebbe un bando specifico per la difesa del suolo»
  (C02). Nella risposta comincia con la maiuscola, «Servirebbe…», all'inizio
  della seconda riga; il resto coincide.
- **2 non nei prompt ma nel codice**, coerenti con quello che la revisione
  dice di loro:
  - «Corrispondenza parziale per»: intestazione di `dettaglio_bando`, in
    `src/database/interrogazioni_bandi.py`;
  - «(nessun dato numerico richiesto)»: il segnaposto dei DATI vuoti, in
    `src/chains/rag.py` (riga 383), fuori da `ISTRUZIONI`.

Citazioni trovate nei JSON e non nei prompt:
- risposta di P11: «Negli archivi non risultano bandi specifici», «i dati
  disponibili non specificano», «Contributi a fondo perduto per progetti
  d'impresa», «(fonte: [D1.5], fonte Incentivi Italia, …)»;
- risposta di C03: «Non trovo quindi, tra i bandi in archivio…», «non lo
  presento come pertinente»;
- dati di C03: la riga del Fondo strade, «ammesso se popolazione fino a
  5.000 abitanti, …», e «ubicato in Toscana»;
- dati dei tre JSON: «dati estratti il»;
- dati e risposta di P11: «contributo fino a…»;
- attesa a mano di P11: «distinguere fondo perduto da prestiti e garanzie».
