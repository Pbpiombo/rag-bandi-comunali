# Piano: insieme di prova dell'app

Misura l'app su domande realistiche, con la stessa catena (router,
interrogazioni, risposta, verificatore) e l'ente Comune di Abetone
Cutigliano. Lo script è `scripts/diagnostica/prova_insieme.py`: i modi
(`--dividi`, `--stima`, `--registra`, `--riprendi`, `--riverifica`,
`--riepilogo`) e i file che scrive sono descritti nella sua docstring.

Le domande e le registrazioni stanno fuori dal repository, in
`dati-grezzi/prova/`: il file delle domande, `lotti.json` con la divisione
in quattro lotti stratificati per gruppo, e una cartella `lotto_<n>/` per
lotto, con le registrazioni e `giudizi.csv`. Se la conversazione con
Claude Code viene azzerata, si riparte leggendo questo file.

## Metodo dei lotti

- **Ogni lotto si registra a freddo una sola volta.** Solo dopo si leggono
  domande e risposte e lo si usa per la diagnosi. Da quel momento non è
  più una misura a freddo: le registrazioni successive dello stesso lotto
  misurano le correzioni, non la qualità su domande nuove.
- **Il lotto 4 resta chiuso fino alla verifica finale prima della demo.**
  È l'unico numero presentabile come misura su domande mai viste.
- **Il lotto 3 è di riserva**, se il lotto 2 rivela difetti gravi.
- **Alla fine, una corsa su tutti i lotti fa da controllo di
  regressione**: dice che le correzioni successive non hanno rotto quelle
  precedenti, non misura la qualità.
- **La regola di chiusura di ogni correzione si scrive prima di
  registrare**, non dopo aver visto i risultati.
- **Gli errori si contano per categoria, non solo in totale**: una
  categoria nuova conta più di un totale che scende.
- **Limite noto**: circa 12 domande a freddo per lotto danno segnali, non
  percentuali affidabili.
