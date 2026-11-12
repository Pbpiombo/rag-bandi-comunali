# Prova del verificatore con il modello vero

Preparata il 12 novembre 2026, alla fine del blocco A
(`docs/piano-verificatore.md`). Da lanciare a mano dall'app: ogni domanda
costa due chiamate al modello, il router e la risposta.

## Prima di cominciare

- `streamlit run app/app.py`, con il `.env` della demo. Con
  `USA_POSTGRES=1` il progetto Supabase deve essere attivo: se è in pausa
  risponde `tenant/user ... not found` e va ripristinato dal pannello.
- I risultati dipendono dalla data. Il bando risorse genetiche forestali
  scade il 13 novembre 2026: lanciata il 12 compare come "fra 1 giorno",
  il 13 come "oggi", dal 14 non compare più.
- Per ogni dato segnato, il confronto si fa con il pannello **Fonti** a
  destra: le righe `[Dn.k]` dei bandi e il testo dei frammenti `[n]`.

## Cosa si guarda

Per ogni risposta:

1. il colore del pannello: verde solo se ogni dato è verificato, arancione
   con dati senza fonte o citati con il blocco, rosso con un dato non
   trovato;
2. **falsi positivi**: un dato con ✓ che nella fonte citata non c'è, o c'è
   con un altro valore. È l'errore più grave, quello che il blocco A deve
   eliminare;
3. **falsi negativi**: un dato con ✗ che nella fonte citata c'è. Per
   ognuno si annota la forma in cui il modello l'ha scritto: è il caso da
   aggiungere al collaudo;
4. che date, decreti, articoli e percentuali compaiano nel pannello: un
   dato che c'è nella risposta ma non nel pannello non è stato riconosciuto.

## Domande

Ente: Comune di Abetone Cutigliano, salvo dove indicato.

| # | domanda | cosa mette alla prova | dove sono i valori giusti |
|---|---|---|---|
| 1 | Quali bandi sono aperti per il Comune e con quale decreto sono stati approvati? | date ISO delle righe scritte in italiano; decreti nelle citazioni `[Dn.k]` e nel testo | righe `[D1.k]`: risorse genetiche forestali (13/11/2026, decreto 14800 del 29 giugno 2026 e modifiche), uso e gestione sostenibile delle risorse (30/11/2026, decreti 20043 e 21441), parcheggi (30/11/2026, decreto 18191), sviluppo di progetti degli enti locali (sportello fino al 18/07/2027, decreto 22706 del 9 ottobre 2026), fondo di garanzia energie rinnovabili |
| 2 | Quali bandi per il Comune scadono entro la fine del mese? | `bandi_in_scadenza`; giorni mancanti ("fra 18 giorni") | le stesse righe; lo sportello con chiusura non compare (voce 12 della revisione, blocco B) |
| 3 | Con quale decreto è stato approvato il bando parcheggi, e di che data è? | data di un atto che in archivio non ha data | la riga dice solo "Decreto dirigenziale 18191". Corretto: il modello dice che la data non c'è. Se la scrive, il numero è ✓ e la data ✗ con "compare nella fonte citata senza questa data" |
| 4 | Qual è il costo massimo giornaliero per un incarico professionale nell'avviso per il rafforzamento amministrativo dei capofila delle aree interne? | importo nei frammenti; atto con numero e data nei metadati del frammento | € 322,00; decreto dirigenziale n. 9550 del 28/04/2026 nell'intestazione del frammento |
| 5 | Quale percentuale di costi indiretti è ammessa nello stesso avviso, e in base a quale norma? | percentuale, articolo, riferimento n/aaaa | 7%; art. 54 del Reg. UE 2021/1060 |
| 6 | Entro quando e a che ora va presentata la domanda per l'avviso sul rafforzamento amministrativo? | orari; date senza anno o relative | secondo i metadati dell'ingestione, ore 12:00 del trentesimo giorno dalla pubblicazione sul BURT, senza data assoluta. Il modello non vede quel metadato: orario e termine devono stare nel testo del frammento citato |
| 7 | Con quale decreto è stato approvato l'avviso per i mercati rionali, e quali contributi prevede? | atto nei metadati, importi | decreto dirigenziale n. 13287 del 10/06/2026; importi nel testo dei frammenti |
| 8 | Quanti abitanti ha il Comune e com'è cambiata la popolazione negli ultimi anni? | dati `[D1]`, percentuale calcolata | blocco della popolazione: numeri e variazione percentuale con un decimale |
| 9 | (Unione di Comuni) A quali bandi può partecipare l'Unione? | stessa prova della 1 su un altro ente | righe `[D1.k]` dell'Unione: quattro bandi, senza parcheggi |

## Risultati

Prova del 12 novembre 2026, lanciata dall'app: 9 domande, 100 dati
segnati come verificati, nessun falso positivo, 2 falsi negativi. Le
citazioni generiche (≈) non sono state contate a parte.

| # | colore | ✓ | ✗ | ? | falsi positivi | falsi negativi | note |
|---|---|---|---|---|---|---|---|
| 1 | rosso | 17 | 1 | 0 | 0 | 1 | "archivio aggiornato al 12/11/2026" citato con [D1.3]: la data sta nell'intestazione del blocco ("alla data del 2026-11-12"), non nella riga |
| 2 | verde | 32 | 0 | 0 | 0 | 0 | |
| 3 | arancione | 2 | 0 | 3 | 0 | 0 | |
| 4 | arancione | 0 | 0 | 1 | 0 | 0 | risposta "non trovo" su € 322,00: il frammento di pag. 11 non è stato recuperato (sotto, recupero) |
| 5 | arancione | 5 | 0 | 3 | 0 | 0 | recuperata la pag. 11 dello stesso avviso |
| 6 | verde | 5 | 0 | 0 | 0 | 0 | |
| 7 | verde | 13 | 0 | 0 | 0 | 0 | il bando mercati rionali, scaduto il 15/10/2026, presentato dai frammenti come attuale |
| 8 | verde | 11 | 0 | 0 | 0 | 0 | |
| 9 | rosso | 15 | 1 | 0 | 0 | 1 | stesso falso negativo della domanda 1 |
| | | **100** | **2** | **7** | **0** | **2** | |

## Esito: correzione fatta

**Falsi negativi delle domande 1 e 9.** Il testo di confronto di `[Dn.k]`
comprende ora anche l'intestazione del blocco, cioè il testo prima della
prima riga di bando (`intestazione_di` in `src/verification/controllo.py`).
Così la data dell'archivio, citata con la riga di un bando, si trova. Casi
in `tests/test_verifica_bandi.py`: "aggiornato al 12/11/2026" con
l'intestazione del 2026-11-12 risulta verificato; "13/11/2026" risulta
non trovato. Il primo falliva prima della correzione.

Effetto collaterale, accettato: un valore dell'intestazione vale per ogni
riga del blocco. Oggi l'intestazione contiene la data e il numero dei
bandi in archivio.

## Esito: proposte, non implementate

### P1. Atti con "Regionale Toscana" tra la parola e il numero

"Delibera di Giunta Regionale Toscana n. 546" viene letta come quantità
546. `SCHEMA_ATTO_TESTO` ammette tra la parola e il numero solo un
elenco chiuso di qualificazioni, e "Toscana" non c'è. Le citazioni
(`SCHEMA_NUMERO_ATTO`, fino a 40 caratteri liberi) e `atti_con_data` la
riconoscono già.

Proposta: si allarga l'elenco chiuso, senza ammettere parole libere.
- Si aggiungono "toscana", "regione toscana", "della regione toscana",
  "RT", come qualificazioni ripetibili.
- Si aggiungono le parole "DGRT" e "D.G.R.T.".
- Le parole libere restano escluse anche con "n." obbligatorio: "il
  decreto stabilisce n. 10 posti" diventerebbe l'atto 10.

Casi: la frase sopra come atto 546, verificato su una fonte che la
riporta; "Decreto del Presidente della Giunta Regionale Toscana n. 12"
come atto; "il decreto stabilisce n. 10 posti" non atto. Costo: un'ora.

### P2. Recupero della domanda 4

Indagine con `recupero.cerca(domanda, k=10)`, come nell'app, senza
modello di risposta. Il chunk con € 322,00 (pag. 11, id 33) e quello
precedente, che lo ripete nella sovrapposizione, contengono "parametro di
costo giornata/uomo pari al massimo a € 322,00".

| domanda | Postgres, posizione nei 10 | Chroma + BM25 |
|---|---|---|
| esempio dell'app: "Qual è il costo massimo giornaliero per un incarico professionale?" | 4ª | 1ª |
| domanda 4: la stessa, più "nell'avviso per il rafforzamento amministrativo dei capofila delle aree interne" | assente (densa 15ª, lessicale 22ª) | assente (BM25 16ª) |
| domanda 5, stesso avviso | 4ª | 1ª |

La domanda d'esempio dell'app funziona. La domanda 4 fallisce per la
parte che nomina il documento: quelle parole compaiono in quasi tutti i
76 chunk dell'avviso, e tirano su i chunk introduttivi (pagg. 8-9) a
scapito di quello che risponde. Allargare la fusione non serve: con 30,
40 e 60 candidati per lista il chunk resta fuori dai 10 su Postgres. Con
BM25 il peso per rarità non basta, perché quelle parole sono rare
nell'archivio ma comuni nel documento.

Proposta, senza modello:
1. Se le parole della domanda coprono gran parte del titolo di un
   documento in archivio (metadato `titolo`), il recupero si restringe
   a quel documento.
2. Quelle parole si tolgono dalla domanda di ricerca.

Per la domanda 4 la ricerca diventa quella dell'esempio dell'app,
ristretta all'avviso 9550. Già senza restrizione il chunk è 4° su
Postgres e 1° su Chroma, e restringere a un documento non può farlo
scendere.
- La scelta del documento è una funzione pura, provata con i titoli in
  archivio, senza database.
- Il filtro è una clausola `WHERE metadata->>'titolo' = %s` su Postgres e
  `where={"titolo": ...}` su Chroma.
- Verifica: le 9 domande della prova con il solo recupero, controllando
  che il frammento decisivo entri nei 10.

Costo: mezza giornata. È la domanda tipica del consulente ("nel bando X,
quanto…"), quindi va prima della demo.

### P3. Stato del bando nei frammenti (passa al blocco B)

I 117 chunk dell'avviso mercati rionali hanno già, su Postgres,
`id_bando = mercati-rionali-2026`. Gli altri documenti non sono bandi del
catalogo, o non hanno l'id. Non serve reindicizzare.

Proposta:
- **Calcolo dello stato.** In `prepara` (`src/chains/rag.py`), per ogni
  frammento con `id_bando` si calcola lo stato del bando al momento della
  domanda, con le funzioni delle interrogazioni (`stato_finestre`,
  `stato_sportello`, `tra_quanto`). Il risultato va in un metadato del
  documento recuperato, `stato_bando`: si calcola a ogni domanda e non si
  memorizza da nessuna parte, come vuole il principio.
- **Intestazione.** `etichetta` aggiunge `stato del bando: scaduto il
  2026-10-15 (alla data del 2026-11-12)`.
- **Prompt.** Regola nuova: un bando con stato "scaduto" non si presenta
  come opportunità attuale; se ne riportano il contenuto e lo stato.
- **Verificatore.** Il testo di confronto di un frammento comprende anche
  `stato_bando`, come per i metadati dell'atto. Altrimenti "scaduto il
  15/10/2026 (fonte: [3])" risulterebbe non trovato.
- **Documenti senza `id_bando`.** Si cerca il bando dal numero d'atto
  (13287 sta in `bandi.riferimento_atto` di mercati-rionali-2026). Se ci
  sono zero o più bandi corrispondenti, nessuno stato: meglio niente che
  uno sbagliato.

Casi: frammento di un bando scaduto, aperto, a sportello e senza bando
collegato; verifica della data di scadenza citata dal frammento. Costo:
mezza giornata.

### P4. Limite del README

Testo proposto, per l'elenco dei limiti:

> **Il verificatore controlla i valori, non gli abbinamenti.** Un dato è
> verificato se il suo valore compare nella fonte citata, non se è
> attribuito alla cosa giusta: un numero di abitanti riferito all'anno
> sbagliato, o l'importo di un intervento attribuito a un altro, passano
> se entrambi i valori sono nella fonte.

## Dopo la prova

- Un falso positivo: si ferma tutto, e il caso diventa un test negativo in
  `tests/test_verifica.py` prima di qualunque correzione.
- Un falso negativo: il caso diventa un test, e si decide se allargare il
  riconoscimento (una forma di data o di numero mancante) o se il modello
  ha scritto il dato in una forma non controllabile.
- Il risultato va nel README, accanto alle due verifiche a mano dei bandi.
