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

## Roadmap

In coda: scadenze multiple (GOL), tirocini classificati
`qualsiasi_soggetto`, categoria per professionisti e lavoratori autonomi,
microzonazione fuori dall'elenco (sostituisce la riga esistente),
appartenenza dei comuni all'Unione nel profilo.
