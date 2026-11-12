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

Da compilare. Una riga per domanda; nelle note, per ogni falso positivo o
negativo: il dato come l'ha scritto il modello, la fonte citata, il valore
nella fonte.

| # | colore | ✓ | ✗ | ? | ≈ | falsi positivi | falsi negativi | note |
|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | |
| 2 | | | | | | | | |
| 3 | | | | | | | | |
| 4 | | | | | | | | |
| 5 | | | | | | | | |
| 6 | | | | | | | | |
| 7 | | | | | | | | |
| 8 | | | | | | | | |
| 9 | | | | | | | | |

## Dopo la prova

- Un falso positivo: si ferma tutto, e il caso diventa un test negativo in
  `tests/test_verifica.py` prima di qualunque correzione.
- Un falso negativo: il caso diventa un test, e si decide se allargare il
  riconoscimento (una forma di data o di numero mancante) o se il modello
  ha scritto il dato in una forma non controllabile.
- Il risultato va nel README, accanto alle due verifiche a mano dei bandi.
