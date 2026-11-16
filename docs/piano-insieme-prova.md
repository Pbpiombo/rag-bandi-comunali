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

## Misure a freddo

Registrazioni a freddo, escluse le domande "viste" (solo nel lotto 1).
Lotto 1: `lotto_1/2026-11-14_114121`, prima delle correzioni 1, 2, 3, A,
C e D (`docs/piano-correzioni-lotto1.md`). Lotto 2:
`lotto_2/2026-11-15_191851`, commit 694936f, dopo quelle correzioni.
Lotto 3: `lotto_3/2026-11-15_215106`, commit 7117aa4, dopo la correzione
E e i punti 1-3 delle osservazioni dall'app online. Lotto 4:
`lotto_4/2026-11-15_231441`, commit 625f7d6, dopo la correzione F. Le
prime colonne
vengono da `--riepilogo`; risposte interrotte e parametri non validi sono
contati a parte, il 15 novembre 2026, dai file delle domande.

Con 12-13 domande per lotto sono **segnali, non percentuali**: una
differenza di una o due domande non dice niente da sola, conta la
categoria dell'errore.

| misura | lotto 1 | lotto 2 | lotto 3 | lotto 4 |
|---|---|---|---|---|
| domande misurate | 12 | 13 | 13 | 12 |
| errori catena / verificatore | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| router riusciti | 11/12 | 13/13 | 13/13 | 12/12 |
| anomalie del router (su 3 chiamate a domanda) | 3/36 | 0/39 | 0/39 | 0/36 |
| attese trovate | 6/6 | 3/3 | 3/3 | 5/5 |
| vietate comparse | 0 | 0 | 0 | 0 |
| dati verificati | 136 | 224 | 149 | 278 |
| non trovati | 1 | 0 | 2 | 1 |
| senza fonte | 0 | 3 | 0 | 3 |
| citati con il blocco | 0 | 0 | 0 | 0 |
| risposte interrotte per max_tokens | 0 | 0 | 0 | 0 |
| parametri non validi | 6 | 0 | 0 | 0 |
| costo medio a domanda | 0,042 $ | 0,051 $ | 0,052 $ | 0,061 $ |

Note:

- Router: nel lotto 1 una domanda su 12 (A01) non ha avuto una decisione
  leggibile e 3 chiamate su 36 erano anomale (correzione 1); nel lotto 2
  nessuna.
- Parametri non validi: temi o tipi fuori dagli elenchi chiusi di oggi
  (`TEMI`, `TIPI_BENEFICIARIO`). Nel lotto 1 sono C04, C05, C11, C12, P11,
  P25: la diagnosi della correzione 2 ne contava 4; C05 ("parcheggi") e
  C12 ("sport") non sono temi dell'elenco nemmeno loro, ma trovavano bandi
  attraverso la ricerca nei titoli. Nel lotto 2 nessuno (correzione 2).
- Risposte interrotte: nel lotto 1 il campo non c'era; dai token in uscita
  nessuna delle 12 domande misurate arriva al tetto di allora (4096). L02,
  troncata, è tra le domande "viste", escluse dalla misura (correzione D1).
- Senza fonte nel lotto 2: 3 anni nei titoli ("2021" di "FESR 2021-2027" in
  A05, "2026" in due titoli di bandi in C06), non dati della risposta.
- Il costo medio sale da 0,042 a 0,051 $. Medie per domanda della
  risposta: in ingresso da 7.778 a 10.229 token (più dati nel contesto),
  in uscita da 977 a 1.263; il router resta simile (in ingresso da 7.097
  a 7.703, in uscita da 266 a 224).
- Lotto 3: i 2 non trovati sono di P01, "I 55.1" e "I 55.3" citati con
  [D1.7] mentre stanno in [D1.16]: etichetta sbagliata del modello,
  segnalata correttamente dal verificatore (giudicati `errore_vero`; le
  altre 13 righe di `giudizi.csv` sono `corretto`). Costo stabile: medie
  della risposta 10.387 token in ingresso e 1.321 in uscita, router 7.708
  e 212. Solo C10 ha consultato i documenti. I difetti del lotto 3 non si
  vedono in queste colonne: sono due conclusioni sbagliate su dati giusti
  (P05 e P24, il profilo dell'ente preso per chi chiede) e un "Non trovo"
  con l'avviso pertinente solo nei documenti (C18): correzione F in
  `docs/piano-correzioni-lotto1.md`.
- **Lotto 4: è la verifica finale a freddo prima della demo.** Le
  correzioni successive si misurano solo su domande già viste e con la
  regressione su tutti i lotti, non più a freddo. Giudizi a mano
  (`lotto_4/giudizi.csv`, 19 righe): 14 `corretto`, 3 `errore_vero`, 2
  `falso_allarme_titolo`. Il non trovato è di P04: il decreto 23619 del
  bando welfare [D1.16] attribuito al bando Filiera SMART [D1.9], che non
  ha atto (`errore_vero`). I 3 senza fonte sono di C08, nel riepilogo
  finale senza citazione: due volte "2026" nel titolo "Missione Comune
  2026" (`falso_allarme_titolo`) e la data 2026-12-05, giusta ma non
  citata (`errore_vero`, lieve). Il terzo `errore_vero` è C19: il router
  non sceglie nessuna interrogazione (3 chiamate su 3) e la risposta è
  "Non trovo", senza inventare. Correzione G in
  `docs/piano-correzioni-lotto1.md`.
