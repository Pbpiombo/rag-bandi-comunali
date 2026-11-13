# Piano: fonti dei bandi

Data: 12 novembre 2026. Piano, nessuna modifica al codice. Le pagine sono
state scaricate e lette con il codice del progetto (`a_testo`,
`ritaglia`, `scadenza_dichiarata`) e confrontate con il database in sola
lettura. Una sola chiamata al modello, autorizzata: la riestrazione di
"premi imboschimenti" (tappa 2, note), non salvata.

Cinque tappe, nell'ordine:

1. fonti, elenchi e regole letti dal database (voce 15 di
   `docs/revisione-2026-11-12.md`), con due tipi di fonte: pagine web e
   file scaricato;
2. elenco "bandi aperti" della montagna, unica pagina regionale in più;
3. bandi scaduti da meno di 12 mesi salvati come storico;
4. fonte GAL MontagnAppennino;
5. fonte Incentivi Italia, dal file open data, senza modello per il
   file; il modello legge solo le pagine dei bandi aperti per enti
   pubblici (decisioni del 13/11/2026).

La tappa 3 viene prima del GAL: i due bandi del GAL sono scaduti, e la
corsa della tappa 4 li registrerebbe altrimenti come scarti definitivi.

### Decisioni prese il 12/11/2026, dopo la prima versione del piano

- I bandi scaduti da meno di 12 mesi si salvano come storico: mai tra
  gli aperti, ma trovabili per nome e nel dettaglio. Quelli più vecchi
  restano scarti definitivi. Gli scaduti già in `scansioni` non si
  riestraggono (tappa 3).
- "Premi imboschimenti" riestratto con una chiamata e mostrato prima di
  salvarlo (tappa 2, note). In roadmap, passo 4: anche gli scarti
  "scaduto" vanno ricontrollati con l'aggiornamento periodico.
- Tappa 2: solo l'elenco "bandi aperti" della montagna; il perché delle
  altre pagine è nella tappa 2.
- Tappa nuova, Incentivi Italia, dopo il GAL (tappa 5). La tappa 1
  prevede già il tipo di fonte "file scaricato".
- `docs/ricognizione-fonti.md` sostituito con la nota di ricognizione
  completa del 12/11/2026.

---

## 0. robots.txt (controllati il 12/11/2026)

| dominio | regole | conseguenza |
|---|---|---|
| www.regione.toscana.it | `Disallow` su `*/search`, `*/ricerca`, `/combo/*`, `*/asset_publisher/`, login | Gli elenchi `…/bandi-aperti?delta=200` e le pagine `/-/slug` sono permessi. Non si seguono le ricerche né gli indirizzi con `/asset_publisher/` nel percorso. La paginazione delle pagine tematiche passa da parametri `p_p_id=…asset_publisher…`: non è vietata alla lettera, ma non serve e non si usa. |
| www.montagnappennino.it | `Disallow: /wp-admin/` | Elenco, pagine dei bandi e allegati permessi. |
| montagnappennino.it | reindirizza a www | come sopra |
| www.incentivitalia.gov.it | Drupal standard: vietati `/admin/`, `/search/`, `/user/…`, `/node/add/` e simili | `/open-data` permesso. Il catalogo e l'API interna non si leggono in automatico (verifica umana con cookie, nota di ricognizione 3.3): solo il file. |

Controllati per completezza, non usati dal piano: giovanisi.it (tutto
permesso), sviluppo.toscana.it (`/lib/`, `/bc/` vietati),
www.artea.toscana.it (nessun robots.txt, risposta 404).

Regola che resta valida per ogni fonte o elenco futuro: robots.txt
controllato prima di inserirlo, con la data nella colonna `fonte` della
riga. Per Incentivi Italia vale anche per i domini dei
`Link_istituzionale` (tappa 5).

---

## 1. Tappa 1: fonti, elenchi e regole dal database (voce 15)

### Problema

`src/estrazione/elenco.py` ha scritti nel codice il codice della fonte,
l'indirizzo dell'elenco e la base del portale; `estrai_nuovi.py` ed
`estrai_bando.py` il nome della fonte. Le regole di lettura sono del
portale regionale: forma dei collegamenti (`/-/slug`), voci escluse,
etichetta del campo di scadenza ("Data di scadenza presentazione
domande"), filtro sull'anno nello slug. La tabella `fonti` ha
`url_elenco` e `url_base`, ma nessun modulo li legge.

Emerso durante la ricognizione, da correggere qui:

- `SLUG_NEL_LINK` cerca `/-/` in qualunque collegamento, di qualunque
  dominio. Le pagine tematiche della Regione hanno un riquadro di notizie
  di `www.toscana-notizie.it/-/…`: `url_da_slug` le trasformerebbe in
  indirizzi del portale regionale che non esistono. Oggi non succede solo
  perché l'elenco generale non ha quel riquadro.
- Ogni pagina della Regione ha nel piè di pagina due collegamenti `/-/`
  (PEC e whistleblower). Sono già in `scansioni` come "non è un bando",
  quindi non costano più, ma vanno tra le voci escluse.

### Due tipi di fonte

Colonna `tipo` in `fonti`:

- `pagine`: uno o più elenchi web, da cui si scoprono pagine di bando
  che vanno alla preselezione e al modello (Regione, GAL);
- `file`: un file scaricato e letto dal codice, senza modello (Incentivi
  Italia). Il file non si scarica in automatico e non entra nel
  repository: il percorso si passa a riga di comando.

In questa tappa si fa solo la distinzione: `scopri()` scorre le fonti
`pagine`; una fonte `file` non si scarica e non si scorre, e un test lo
fissa. Il lettore del file è della tappa 5.

### Schema

Tabella nuova `elenchi`, una riga per pagina da cui si scoprono i bandi
(solo per le fonti `pagine`; per una fonte `file` la riga indica la
pagina ufficiale da cui il file si scarica, con `attivo` = 0):

```
CREATE TABLE IF NOT EXISTS elenchi (
    url           TEXT PRIMARY KEY,          -- forma canonica
    codice_fonte  TEXT NOT NULL REFERENCES fonti(codice),
    nome          TEXT NOT NULL,
    attivo        INTEGER NOT NULL DEFAULT 1 CHECK (attivo IN (0, 1)),
    fonte         TEXT NOT NULL,             -- da dove viene l'indirizzo, robots.txt controllato il …
    verificato_il TEXT NOT NULL
);
```

Colonne nuove in `fonti`, con le regole di lettura come dati:

| colonna | Regione Toscana | GAL (tappa 4) | Incentivi Italia (tappa 5) |
|---|---|---|---|
| `tipo` | `pagine` | `pagine` | `file` |
| `schema_link` | `^/(?:it/)?-/(?P<slug>…)$` (lo schema di oggi, sul solo percorso) | `^/bando/(?P<slug>[a-z0-9-]+)/?$` | vuoto |
| `esclusi` | le voci di `ESCLUSI` e `PAROLE_ESCLUSE`, più PEC e whistleblower, come un'unica espressione | vuoto | vuoto |
| `etichetta_scadenza` | `data di scadenza presentazione domande` | `termine presentazione domande` | vuoto |
| `filtro_anno_slug` | 1 | 0 | 0 |
| `scadenza_obbligatoria` | 0 | 1 | 0 |

`scadenza_obbligatoria` serve al GAL (tappa 4, problema 3), ma si crea
qui per toccare lo schema una volta sola.

`url_elenco` esce da `fonti`: l'elenco della Regione diventa la prima
riga di `elenchi`. `url_base` resta, e serve due cose: il dominio dei
collegamenti accettati (risolve il problema di toscana-notizie) e la
fonte di un indirizzo passato a mano a `estrai_bando`.

Restano nel codice, perché sono meccanica e non regole di una fonte:
lettura dei collegamenti, forma canonica, `id_da_slug`, preselezione,
margine di un anno.

Una modifica che vale per tutte le fonti: `_data` in `scadenza.py`
accetta anche la forma del GAL "[PROROGATO] [alle] ore 13.00 del 12
ottobre 2026". La regola resta rigida: il valore deve essere per intero
una data, con questi prefissi e nient'altro.

### File

| file | cosa | perché |
|---|---|---|
| `src/database/schema.py` | tabella `elenchi`, colonne nuove di `fonti` senza `url_elenco`, `elenchi` in `TABELLE_DA_CSV` dopo `fonti` | voce 15; regola di CLAUDE.md sulle tabelle nuove |
| `data/processed/fonti.csv` | colonne nuove, `url_elenco` tolta | **modifica a mano di un CSV verificato**, dichiarata qui: una riga, nessun dato nuovo, solo regole oggi scritte nel codice e copiate dalle costanti di `elenco.py` |
| `data/processed/elenchi.csv` (nuovo) | una riga: l'indirizzo che oggi è in `fonti.url_elenco` | |
| `src/estrazione/elenco.py` | `leggi_elenco(elenco, regole)` e `scopri()` che scorrono le fonti `pagine` e i loro elenchi attivi dal database; via `CODICE_FONTE`, `ELENCO`, `BASE`, `ESCLUSI`, `PAROLE_ESCLUSE`; una voce vista in più elenchi della stessa fonte compare una volta | voce 15 |
| `src/estrazione/scadenza.py` | etichetta come argomento, forma "ore … del …" | regole per fonte |
| `scripts/ingestione/estrai_nuovi.py` | nome e regole della fonte da `Voce`; via `FONTE`; stampa quante voci ha dato ogni elenco | voce 15; un elenco che smette di dare voci si vede |
| `scripts/ingestione/estrai_bando.py` | fonte ricavata dall'URL (`url_base`); via `CODICE_FONTE` e `FONTE` | voce 15 |
| `scripts/ingestione/scopri_bandi.py` | "spariti" per fonte: un bando è sparito se non c'è in nessun elenco della sua fonte; le fonti `file` non si confrontano | con più elenchi il confronto attuale darebbe falsi spariti |
| `tests/conftest.py`, `tests/test_beneficiari.py`, `tests/test_interrogazioni_bandi.py` | `INSERT INTO fonti` con le colonne nominate | gli ultimi due inseriscono per posizione e si romperebbero |
| `tests/test_fonti.py`, `tests/test_acquisizione.py`, `tests/test_scadenza.py` | test nuovi (sotto) | |
| `README.md` | tabella dei CSV e paragrafo sull'acquisizione | voce 14 |

Chi importa i nomi che spariscono: `estrai_bando.py` (`CODICE_FONTE`),
`estrai_nuovi.py` e `scopri_bandi.py` (`scopri`, `id_da_slug`,
`gia_in_archivio`), `tests/test_scadenza.py` (`anno_slug`, `recente`),
`tests/test_acquisizione.py` (`elenco.scarica`, `leggi_elenco`). Nessun
altro (cercato con grep su `src`, `scripts`, `tests`, `app`).

### Test

Tutti sul database in memoria o su `db_su_file`, con pagine salvate:

- `leggi_elenco` su un estratto di pagina tematica salvato
  (`tests/pagine/`) con un collegamento a toscana-notizie: il
  collegamento non entra;
- PEC e whistleblower esclusi con le regole lette dal database;
- due elenchi della stessa fonte con un bando in comune: una sola voce;
- un elenco con `attivo = 0` non si scarica;
- `scopri` su due fonti `pagine`, ciascuna con le sue regole: ogni voce
  ha il suo `codice_fonte`;
- una fonte `file` nel database: `scopri` non scarica nulla per lei;
- un `tipo` diverso da `pagine` e `file` è rifiutato dal vincolo;
- `scadenza_dichiarata` con un'etichetta diversa da quella regionale;
- le forme "ore 13.00 del 8 maggio 2026" e "PROROGATO alle ore 13.00 del
  12 ottobre 2026" lette; "entro 60 giorni dal 1 gennaio 2026" non letta;
- "spariti" con due elenchi: un bando presente in uno solo non è sparito;
- `fonti.csv` ed `elenchi.csv` caricati da `carica_csv` senza righe
  scartate, e le regole della Regione lette dal CSV escludono le stesse
  voci delle costanti di oggi (test sul CSV vero, in sola lettura, come
  quelli di `test_fonti.py` sulla migrazione).

I test che oggi provano `leggi_elenco` e `scopri` sull'elenco salvato
restano e devono passare senza modifiche alle attese.

### Regola di chiusura

- `ruff check` senza segnalazioni nuove, `python -m pytest` verde, con
  l'output riportato;
- database ricreato dai CSV, con `elenchi` presente dopo la ricreazione;
- `python -m scripts.ingestione.estrai_nuovi --prova` (nessuna chiamata
  al modello) dà gli **stessi candidati** di prima della modifica:
  stesso numero di "nuovi rispetto all'archivio" e stessa lista. Il
  confronto si fa salvando l'output prima e dopo;
- `grep` di `regione.toscana.it` in `src/estrazione` e
  `scripts/ingestione`: nessun risultato fuori da commenti e docstring.

### Costo

Nessuna chiamata al modello. Circa un giorno, come stimato nella revisione.

### Esito (12/11/2026)

- `fonti.csv` modificato con il diff approvato, `elenchi.csv` creato.
  Database ricreato dai CSV: nessuna riga scartata, `elenchi` presente.
- Prima di applicare il CSV: sulla pagina "Bandi aperti" salvata lo
  stesso giorno, le regole del CSV danno le stesse 160 voci del codice di
  prima, con gli stessi URL e nello stesso ordine; in meno PEC e
  whistleblower.
- `estrai_nuovi --prova`, prima e dopo: gli stessi 12 candidati, nello
  stesso ordine. "Nuovi rispetto all'archivio" passa da 124 a 122 e "già
  esaminati con esito definitivo" da 110 a 108: sono PEC e whistleblower,
  ora esclusi dalle regole invece che dal registro. Differenza prevista,
  non nei candidati.
- `grep` di `regione.toscana.it` in `src/estrazione` e
  `scripts/ingestione`: nessun risultato.
- Altri file di test con `INSERT INTO fonti` per posizione, non elencati
  sopra: `test_schema.py`, `test_stato_documenti.py`,
  `test_uguale_per_comuni.py`. Corretti allo stesso modo.
- `ruff check`: 11 segnalazioni, le stesse di prima. `pytest`: 598
  passati, 2 xfail.

---

## 2. Tappa 2: elenco "bandi aperti" della montagna

### Come sono state verificate le pagine candidate

Il 12/11/2026, per ogni pagina: scaricata con `scarica`, collegamenti
`/-/slug` letti con lo schema di `elenco.py` (solo collegamenti al
dominio della Regione, senza PEC e whistleblower), confronto per URL
canonico con `bandi` e `scansioni` (database in sola lettura). Per le
pagine mai viste: scaricate una per una e passate a
`scadenza_dichiarata`, senza modello. Il portale risponde lentamente
(da 20 secondi a un minuto a pagina).

"Nuovi" vuol dire: né in `bandi` né in `scansioni`. "Aperti" vuol dire:
con una scadenza non ancora passata.

| candidata | esiste, leggibile | collegamenti | in archivio | in `scansioni` | nuovi | di cui aperti |
|---|---|---|---|---|---|---|
| Rischio sismico: pagina principale e contributi da fondi regionali, statali, europei | sì, HTML | 26 distinti | 0 | 0 | 26 | 0 (vedi sotto) |
| Rischio sismico: fondi post-sisma | sì | 7 (eventi sismici 1997-2023) | 0 | 0 | 7 | 0, non sono bandi |
| `pr-fesr-2021-2027/bandi-aperti?delta=200` | sì | 8 | 6 | 2 | 0 | 0 |
| `pr-fse-2021-2027/bandi-aperti?delta=200` | sì | 20 | 15 | 4 | 1 | 1 |
| `pr-fse-2021-2027/bandi-opportunità` | sì | 0 diretti (contenuto paginato da `asset_publisher`) | | | | |
| `sviluppo-rurale-2023-2027/bandi-aperti?delta=200` | sì, "Risultati: 3 Bandi" | 3 | 2 | 1 | 0 | 0 |
| `sviluppo-rurale-2023-2027/bandi-in-programma` | sì | 0 bandi (solo cronoprogramma) | | | 0 | 0 |
| `politiche-per-la-montagna/bandi-aperti?delta=200` | sì, "Nessun risultato trovato" | 0 | | | 0 | 0 |
| `politiche-per-la-montagna/bandi-in-attuazione?delta=200` | sì | 23 | 0 | 0 | 23 | 0 |

Note per riga:

- **Rischio sismico.** Le 26 pagine sono schede informative per legge o
  programma ("Interventi sulle scuole l. 23/1996", "Verifiche su edifici
  pubblici - fondi Fesr 2021-2027"), non pagine di bando: nessuna ha il
  campo "Data di scadenza presentazione domande". Le pagine di bando vere
  sono un livello sotto, collegate dalle schede. Trovate tre, tutte del
  2026 e tutte scadute: microzonazione di livello 4, Fesr (27/06/2026);
  verifiche tecniche su edifici pubblici, Fesr (01/08/2026); microzonazione
  di livello 2 e 3 e analisi CLE, DGR 1081 del 7/9/2026, la voce in coda
  nella roadmap (17/10/2026). La scheda "prevenzione sismica 2026" è una
  ricognizione degli edifici già chiusa, non un bando. Nessuna delle tre
  pagine di bando è in `scansioni`, ma non c'è stata nessuna scansione
  tra il 15/09 e l'11/11, quindi non si può dire se l'elenco generale le
  avesse mentre erano aperte.
- **FESR, FSE+, sviluppo rurale.** Ogni collegamento di questi elenchi è
  anche nell'elenco generale (`bandi-aperti?delta=200`, 160 collegamenti):
  0 pagine in più. L'unica nuova, "contributi a enti locali e ETS per
  punti Digitale facile, avviso 2026", è già candidata alla prossima
  scansione dall'elenco generale.
- **Montagna, in attuazione.** 2 pagine rispondono 404; le altre 21 hanno
  la scadenza nel campo della pagina, tutte passate, dal 31/08/2020 al
  15/06/2026. Ci sono le linee emerse dalla ricognizione: custodi della
  montagna (31/12/2022), impianti di risalita "Energia in vetta"
  (30/04/2024), comprensori sciistici, cioè gli impianti di risalita per
  i soggetti pubblici (15/06/2026), mezzi antineve (05/12/2024), FOSMIT
  2023.
- **Linee per le imprese di montagna.** Bandi neve: c'è solo il "sistema
  neve 2017", chiuso. Voucher garanzia: già in archivio, 4 bandi a
  sportello sulle garanzie (abbattimento di interessi e commissioni,
  emissione di obbligazioni, turismo). Impianti di risalita e custodi
  della montagna: solo nelle pagine "in attuazione", chiusi.
- **Scartato anche:** `bandi-tutti` (1.918 voci, quasi tutte chiuse o in
  attuazione); la paginazione `asset_publisher` delle pagine dei
  programmi.

### Premi imboschimenti, riestratto il 12/11/2026

In `scansioni` la pagina
`/-/premi-annuali-ad-ettaro-per-mantenere-imboschimenti/forestazione-su-terreni-agricoli`
è "scaduto il 2026-06-30" (scansione dell'11/11), mentre l'elenco dello
sviluppo rurale la dà "Aperto". Riestratta con una chiamata (8.698 token
in ingresso, 4.816 in uscita, 0,066 $), **non salvata**:

| campo | valore estratto | prova o nota |
|---|---|---|
| natura | bando | |
| programma | Csr Feasr 2023-2027 - Intervento SRA28 | |
| apertura | 2026-01-01 | |
| scadenza | 2026-06-30 | "Per il 2026 le domande di aiuto/pagamento devono essere presentate a partire dal primo gennaio 2026 ed entro il 30 giugno 2026" |
| scadenza_nota | "Scadenza prorogata con circolare Agea del 15 maggio 2026; le domande di aiuto/sostegno possono essere presentate fino al 2029 come ultima annualità ammessa" | |
| a_sportello | sì | "le domande di aiuto/sostegno possono essere presentate a partire dal 2026 e fino a quando non si esauriscono le risorse disponibili" |
| pubblicato_il | 2026-01-21 | |
| dotazione | vuota | la pagina cita solo l'incremento di 240 mila euro (decreto 17966 del 7/8/2026) |
| riferimento_atto | Decreto dirigenziale 27357 del 24/12/2025, delibera di giunta 1745 del 22/12/2025, delibera di giunta 340 del 3/4/2023, decreto 17966 del 7/8/2026 (incremento dotazione) | |
| beneficiari | proprietari, possessori privati e loro associazioni, altri soggetti ed enti pubblici o privati, titolari di superfici che hanno avuto il sostegno SRD05 per gli imboschimenti | tipi: le quattro imprese, professionista, terzo settore; comune, unione, altro ente pubblico (confidenza media) |
| interventi | mantenimento di imboschimenti naturaliformi, di arboricoltura a ciclo breve e medio-lungo, di sistemi agroforestali | |
| problemi, avvisi | nessuno | |
| decisione di oggi | non salvato, "scaduto il 2026-06-30" | |

Lettura: lo scarto dell'11/11 era corretto per la data, sbagliato come
scarto definitivo. È un bando a domanda annuale: l'annualità 2026 si è
chiusa il 30/06, le annualità arrivano fino al 2029, e la data della
prossima non è ancora sulla pagina. Con la tappa 3 rientrerebbe nello
storico (scaduto da 135 giorni). Proposta: salvarlo dopo la tappa 3
dall'estrazione conservata, senza una nuova chiamata, con la sua
`scadenza_nota`. Nota in roadmap, passo 4.

L'estrazione è conservata fuori dal repository, in
`C:\Users\Matteo_Papucci\Desktop\programmazione\dati-grezzi\estrazioni\`:
`2026-11-12_premi-imboschimenti.json` (leggibile), `.pkl` (l'oggetto
`Estrazione`), `.testo.txt` (il testo della pagina su cui validarla).

### Decisione e motivi

Si aggiunge **solo** `politiche-per-la-montagna/bandi-aperti?delta=200`.
Oggi è vuoto e costa solo un download a scansione; è la pagina dove
compariranno le linee per la montagna (custodi, impianti, neve) quando
riapriranno, e non c'è prova che l'elenco generale le riporti.

Le altre pagine no, per questi motivi (decisione del 12/11/2026):

- **FESR, FSE+ e sviluppo rurale:** oggi contenuti per intero
  nell'elenco generale. Aggiungerli costa un download lento a ogni
  scansione e non porta nessuna pagina in più. Il controllo si rifà con
  il passo 4 della roadmap (decisioni aperte, punto 3).
- **Rischio sismico:** le pagine sono schede, non bandi. Come elenchi
  manderebbero al modello 21 pagine senza campo di scadenza (le altre 5
  hanno un anno passato nello slug e si salterebbero), per 0,65–1,28 $,
  senza nessun bando aperto. Quelle a "scadenza non determinata"
  tornerebbero al modello a ogni scansione. I bandi veri stanno un
  livello sotto, e seguire i collegamenti di secondo livello è un'altra
  regola, non giustificata da tre bandi tutti scaduti.
- **Montagna "in attuazione":** 0 aperti, tutti chiusi da 5 mesi a 6
  anni. 19 pagine si registrerebbero scadute senza modello, 2
  andrebbero al modello (circa 0,12 $), 2 fallirebbero. Anche con lo
  storico della tappa 3 entrerebbero al più le 2 chiuse a giugno 2026.
- **`bandi-tutti` e paginazione `asset_publisher`:** 1.918 voci quasi
  tutte chiuse; la seconda passa da indirizzi che è meglio non usare.

### File

| file | cosa | perché |
|---|---|---|
| `data/processed/elenchi.csv` | riga dell'elenco della montagna, con la fonte "pagina Politiche per la montagna, Bandi aperti; robots.txt controllato il …" | dato nuovo con fonte |
| `tests/pagine/montagna-bandi-aperti-vuota.html` (nuovo) | la pagina di oggi ridotta al contenuto | test sulla pagina salvata |
| `tests/test_acquisizione.py` | test sotto | |
| `docs/roadmap.md` | voci "microzonazione", "linee per le imprese di montagna" e "PR FESR e FSE+" della coda chiuse con il risultato di questa tappa | |

### Test

- elenco della montagna vuoto salvato: 0 voci, anche con i collegamenti
  del piè di pagina e del riquadro notizie presenti nella pagina;
- `scopri` con i due elenchi della Regione: le voci dell'elenco generale
  non cambiano.

### Regola di chiusura

- `ruff check` e `python -m pytest` come sopra, con l'output;
- `estrai_nuovi --prova`: l'elenco della montagna risulta letto, con 0
  voci, e i candidati sono gli stessi della tappa 1.

### Costo

Nessuna chiamata al modello. Mezz'ora, più il tempo di download.

### Esito (12/11/2026)

- Riga in `elenchi.csv`, pagina salvata
  `tests/pagine/montagna-bandi-aperti-vuota.html`, quattro test.
- `estrai_nuovi --prova`: elenco generale 160 voci, elenco della montagna
  0 voci; gli stessi 12 candidati della tappa 1, nello stesso ordine.

---

## 3. Tappa 3: bandi scaduti da meno di 12 mesi come storico

### Regola

Un bando scaduto da **365 giorni o meno** alla data dell'esame si salva,
come storico. Uno scaduto da più di 365 giorni resta uno scarto
definitivo, come oggi. Vale per la data di chiusura degli sportelli.
Gli scaduti già in `scansioni` non si toccano: niente riestrazione,
niente migrazione.

Uno storico non compare mai tra gli aperti; si trova per nome
(`dettaglio_bando`) e nell'elenco per tema, separato dagli aperti.

### Oggi

- `decidi_automatico` (`src/estrazione/bandi.py`) scarta ogni scadenza
  passata con "scaduto il …"; legge la data da `date.today()`.
- La preselezione (`scadenza.py`) registra come scaduta senza modello
  una pagina il cui campo è passato da più di `MARGINE_GIORNI` = 365
  giorni. Coincide con la soglia dello storico: una pagina più vecchia
  non arriva al modello, una più recente sì.
- Le interrogazioni degli aperti escludono già le scadenze passate:
  `bandi_aperti_per_ente` e `bandi_per_beneficiario` con `scadenza IS
  NULL OR scadenza >= oggi`, `bandi_in_scadenza` con `scadenza >= oggi`.
  Uno sportello storico ha sempre la data di chiusura, quindi resta
  fuori anche lui.
- `dettaglio_bando` mostra già "scade il … (SCADUTO da N giorni)".
- `bandi_per_tema` mette aperti e scaduti in un'unica lista, ordinata
  per scadenza decrescente, con lo stato in ogni riga. Con lo storico
  gli scaduti aumentano, e il modello potrebbe presentarli insieme agli
  aperti.

### Modifiche

`decidi_automatico(estrazione, riga, oggi=None)`:

```
GIORNI_STORICO = 365

scadenza = riga.get("scadenza")
if scadenza and scadenza < oggi:
    giorni = (oggi - scadenza).days
    if giorni <= GIORNI_STORICO:
        return True, f"storico: scaduto il {scadenza}"
    return False, f"scaduto il {scadenza}"
```

Il resto (non bando, sportello, scadenza non determinata, bassa
confidenza) resta com'è. Il motivo "storico: …" non comincia con
"scaduto": in `scansioni` la riga ha esito `salvato`, e
`da_non_riesaminare` non la considera. Un bando in archivio non torna
candidato, quindi non si riestrae a ogni scansione.

`oggi` come argomento, con `date.today()` se manca: i test non devono
dipendere dal giorno in cui girano. Chi chiama oggi (`estrai_nuovi`,
`estrai_bando`, `riclassifica_bandi`, i test) non cambia.

Interrogazioni (`src/database/interrogazioni_bandi.py`):

- `bandi_per_tema`: due blocchi, "aperti" (la stessa condizione degli
  altri elenchi) e "scaduti, solo come storico: non più aperti". Le
  righe dei due blocchi restano numerate per la citazione [Dn.k].
- `dettaglio_bando`: per un bando scaduto, prima riga "stato: scaduto il
  …, non più aperto". Lo stato è calcolato dalla data a ogni domanda,
  come in P3, e non si memorizza.
- Gli altri elenchi non cambiano: i test fissano che lo storico ne resta
  fuori.

Il prompt della risposta ha già la regola sullo stato dei frammenti
(P3). Se la prova con il modello mostra uno storico presentato come
aperto, la regola si estende alle righe [Dn], in un compito a parte.

### File

| file | cosa | perché |
|---|---|---|
| `src/estrazione/bandi.py` | `GIORNI_STORICO`, `decidi_automatico` con `oggi` e la regola dello storico | decisione del 12/11 |
| `src/database/interrogazioni_bandi.py` | `bandi_per_tema` in due blocchi, riga di stato in `dettaglio_bando` | lo storico non si confonde con gli aperti |
| `tests/test_valori.py` o `tests/test_estrattore.py` | test della decisione | |
| `tests/test_interrogazioni_bandi.py` | test delle interrogazioni | |
| `tests/test_scadenza.py` | `MARGINE_GIORNI >= GIORNI_STORICO` | se il margine scendesse sotto la soglia, la preselezione scarterebbe pagine da storico |
| `tests/dati/interrogazioni_comuni_dopo.json` | aggiornato, con le differenze mostrate e approvate a mano prima | `tests/test_uguale_per_comuni.py` chiama anche `bandi_per_tema` e `dettaglio_bando`, che cambiano |
| `README.md` | lo storico nel paragrafo sull'acquisizione | |

### Test

Decisione, con `oggi` fisso al 12/11/2026:

- scaduto ieri: salvato, "storico: scaduto il 2026-11-11";
- scaduto da 365 giorni: salvato; da 366: scartato, "scaduto il …";
- sportello con chiusura passata da 30 giorni: salvato come storico;
- scadenza futura, sportello senza data, non bando, scadenza non
  determinata: esito invariato;
- le due pagine scadute di `tests/pagine/attesi.json` (TPL 2021, musei
  2023) danno lo stesso esito di oggi, perché scadute da più di un anno;
- `registra` con il motivo dello storico: la pagina non è in
  `da_non_riesaminare` ma, essendo in archivio, non è candidata.

Interrogazioni, sul database in memoria, con un bando aperto e uno
scaduto da 30 giorni dello stesso tema e per lo stesso tipo di ente:

- `bandi_aperti_per_ente`, `bandi_per_beneficiario`,
  `bandi_in_scadenza`: solo l'aperto;
- `dettaglio_bando` per nome dello storico: trovato, con "stato:
  scaduto il …, non più aperto";
- `bandi_per_tema`: l'aperto nel primo blocco, lo storico nel secondo;
- uno sportello con chiusura passata non compare tra gli sportelli
  aperti.

### Regola di chiusura

- `ruff check` e `python -m pytest`, con l'output;
- query modificate eseguite sul database vero in sola lettura, con
  l'output di `bandi_per_tema` su un tema con scaduti;
- `estrai_nuovi --prova` invariato (la preselezione non cambia);
- nessuna riga di `scansioni` modificata (confronto del CSV prima e
  dopo).

### Costo

Nessuna chiamata al modello. Mezza giornata. Dopo la tappa, il
salvataggio di "premi imboschimenti" dall'estrazione conservata non
costa chiamate.

### Esito (12/11/2026)

- `decidi_automatico(estrazione, riga, oggi=None)`: scaduto da 1 a 365
  giorni salvato con il motivo "storico: scaduto il …", più vecchio
  scartato come prima. La soglia è una sola, `GIORNI_STORICO` in
  `src/estrazione/scadenza.py` con `nello_storico`, usata dal
  salvataggio e dalle interrogazioni.
- Regola aggiunta su richiesta: in `bandi_per_tema` il blocco "Scaduti,
  solo come storico" contiene solo gli scaduti da non più di 12 mesi;
  quelli più vecchi restano in archivio e si trovano con
  `dettaglio_bando`, non nelle liste. Un tema con soli scaduti vecchi dà
  `trovato=False`.
- `dettaglio_bando` di un bando scaduto comincia con "stato: scaduto il
  …, non più aperto".
- Riferimento di equivalenza rigenerato dopo l'approvazione: 22 voci su
  35 (6 `bandi_per_tema`, 16 `dettaglio_bando`, tutti e solo i bandi
  scaduti alla data del test), differenze nel docstring del test.
- Premi imboschimenti salvato come storico dall'estrazione in
  `dati-grezzi\estrazioni\`, senza modello:
  `premi-annuali-ad-ettaro-per-mantenere-imboschimenti-f-cee3db`, 9 righe
  di beneficiari, 4 interventi; in `scansioni` la riga passa da
  "scartato, scaduto il 2026-06-30" a "salvato, storico: scaduto il
  2026-06-30". Fuori dagli aperti, nello storico di
  `bandi_per_tema(agricoltura)`.
- Da segnalare: per uno sportello scaduto la riga del bando dice ancora
  "a sportello fino al 2026-06-30, verificare la disponibilità delle
  risorse" (`stato_sportello`). La riga di stato che la precede dice che
  è scaduto, ma l'invito a verificare le risorse non ha senso per un
  bando chiuso. Non corretto: fuori dal perimetro della tappa.

---

## 4. Tappa 4: fonte GAL MontagnAppennino

### Cosa c'è sul sito (letto il 12/11/2026)

Elenco: <https://www.montagnappennino.it/bandi-e-graduatorie/>, HTML
leggibile in UTF-8 (WordPress). Contiene 4 collegamenti a pagine
`/bando/…/`:

| pagina | contenuto | termine | stato calcolato |
|---|---|---|---|
| `/bando/aso1-investimenti-non-produttivi-…/` | AS01, 710.624,00 €, contributo 20.000–80.000 €, 90% | "PROROGATO alle ore 13.00 del 12 ottobre 2026" | scaduto da 31 giorni: storico |
| `/bando/srd-14-investimenti-produttivi-non-agricoli-in-aree-rurali/` | SRD 14, 782.480,00 €, contributo 5.000–40.000 €, 50% piccole imprese, 60% microimprese | "ore 13.00 del 8 maggio 2026" | scaduto da 188 giorni: storico |
| `/bando/3450/` | pagina vuota: etichette senza valori, etichetta "Chiuso" | — | — |
| `/bando/3451/` | pagina vuota: etichette senza valori, etichetta "In corso" | — | — |

Nessuno dei bandi è nell'archivio né in `scansioni` (0 righe con
`codice_fonte` diverso da `regione-toscana`).

I dati principali sono in forma ordinata, una etichetta per riga e il
valore sotto: "Termine presentazione domande", "Importo a Bando", "A chi
si rivolge", "Contributo minimo", "Contributo massimo", "Tasso di
sostegno", più "Intervento", "Programmazione", "Parole Chiave". Provato
con `ritaglia`: tutte queste righe restano nel testo che va al modello
(AS01 8.708 caratteri, SRD 14 4.131).

Le etichette di stato del sito non valgono nulla: AS01 e SRD 14 sono
entrambi "In corso" sulla loro pagina, e nell'elenco AS01 sta sotto
"Bandi aperti" e SRD 14 sotto "Bandi in attuazione". Si applica la
decisione già presa: lo stato si calcola dalla scadenza. Le sezioni
dell'elenco non si usano per filtrare: ogni collegamento `/bando/` è una
voce.

Territorio: la pagina "Chi siamo" del GAL dice che nel suo territorio
rientrano i comuni dell'Appennino Pistoiese.

Il sito espone anche `wp-json/wp/v2/bando` (permesso dal robots.txt), con
14 bandi: i 4 sopra e 10 della programmazione Leader 2014-2022, tutti
chiusi da più di un anno. Non si usa: l'elenco HTML basta.

### Problemi trovati

1. **Entità HTML non convertite.** `_entita` in `pagina.py` conosce 16
   entità; le pagine del GAL usano anche `&rsquo;` (24 volte in AS01),
   `&ldquo;`, `&rdquo;`, `&copy;`, `&deg;`, `&Eacute;`, `&times;`. Il
   modello riceverebbe "dell&rsquo;economia". Rimedio: `html.unescape`
   al posto della tabella. Su 9 pagine regionali scaricate per la tappa 2
   non resta nessuna entità, quindi i testi della Regione non cambiano;
   la regola di chiusura lo controlla sulle pagine salvate in
   `tests/pagine/`.
2. **Forma della scadenza.** "PROROGATO alle ore 13.00 del 12 ottobre
   2026" non è letta da `_data`: risolto nella tappa 1.
3. **Pagine vuote.** `3450` e `3451` andrebbero al modello e
   costerebbero una chiamata ciascuna a ogni scansione (lo scarto
   "scadenza non determinata" non è definitivo). Rimedio: con
   `scadenza_obbligatoria` = 1 (colonna della tappa 1), una pagina senza
   scadenza leggibile si salta senza modello e senza registrarla, e il
   riepilogo la stampa tra le "saltate, senza scadenza leggibile", così
   un bando nuovo scritto in un'altra forma si vede.
4. **PDF allegati non letti.** Si legge solo la pagina. Bando, allegati
   e BURT restano collegamenti; la loro lettura è nel passo 5 della
   roadmap ("PDF dei bandi").
5. **Proroghe.** La pagina di AS01 riporta la proroga al 12/10/2026;
   il file di Incentivi Italia ha ancora il 18/09 (nota di ricognizione,
   3.3). Per il GAL vale la pagina.

Con la tappa 3, AS01 e SRD 14 si salvano come storico: non tra gli
aperti, ma trovabili per nome.

### File

| file | cosa | perché |
|---|---|---|
| `data/processed/fonti.csv` | riga `gal-montagnappennino`: nome, `url_base`, regole della tabella della tappa 1, fonte "Sito del GAL, pagina Bandi e graduatorie; robots.txt controllato il …" | fonte nuova come dato |
| `data/processed/elenchi.csv` | riga dell'elenco del GAL | |
| `src/estrazione/pagina.py` | `html.unescape` in `_entita` | problema 1 |
| `src/estrazione/scadenza.py` | esito "senza scadenza leggibile" quando la fonte la richiede | problema 3 |
| `scripts/ingestione/estrai_nuovi.py` | conteggio e stampa delle pagine saltate per questo motivo; opzione `--fonte CODICE` | problema 3; la corsa di prova sul solo GAL senza scaricare l'elenco regionale |
| `tests/pagine/gal-as01.html`, `gal-srd14.html`, `gal-vuota.html`, `gal-elenco.html` (nuovi) | pagine salvate, ridotte al blocco del contenuto: senza piè di pagina con telefoni e indirizzi | test sulle pagine salvate; repository pubblico |
| `tests/pagine/LEGGIMI.md` | da dove vengono le pagine nuove e quando | come le altre |
| `tests/test_acquisizione.py`, `tests/test_scadenza.py`, `tests/test_estrattore.py` | test sotto | |
| `README.md` | la fonte nuova | |

Non serve un `id` con un prefisso per il GAL: `salva` rifiuta già due
bandi con lo stesso id e URL diversi (`test_stesso_id_con_url_diverso_e_rifiutato`).

### Test

- elenco GAL salvato: 4 voci, URL canonici `https://www.montagnappennino.it/bando/…`
  senza barra finale, `codice_fonte` del GAL, nessun collegamento a
  `wp-content` o a pagine non `/bando/`;
- AS01: scadenza letta 2026-10-12; SRD 14: 2026-05-08;
- pagina vuota: saltata senza modello con `scadenza_obbligatoria`,
  mandata al modello senza;
- `a_testo` su AS01: nessuna `&…;` rimasta, "dell'economia" con
  l'apostrofo tipografico;
- `a_testo` sulle pagine regionali già in `tests/pagine/`: testo
  identico a prima;
- `ritaglia` su AS01 e SRD 14 conserva le righe dei dati ordinati;
- percorso di `preseleziona` con l'elenco GAL salvato e la rete finta:
  AS01 e SRD 14 al modello, le due vuote saltate.

### Regola di chiusura

- `ruff check` e `python -m pytest`, con l'output;
- `estrai_nuovi --prova` (senza modello): candidati della Regione uguali
  a quelli della tappa 2, più 2 pagine del GAL al modello e 2 saltate
  senza scadenza leggibile;
- una corsa vera limitata al GAL (`--fonte gal-montagnappennino`): 2
  chiamate, AS01 e SRD 14 salvati con "storico: scaduto il 2026-10-12"
  e "storico: scaduto il 2026-05-08", con importi, contributo minimo e
  massimo e tasso uguali a quelli della tabella sopra. Se il modello
  legge un'altra data o un altro importo, la tappa non è chiusa;
- `dettaglio_bando("AS01")` sul database vero: trovato, con lo stato
  scaduto; `bandi_aperti_per_ente` per l'Unione: AS01 assente;
- `estrai_nuovi --prova` rilanciato subito dopo: 0 pagine del GAL al
  modello.

### Costo

2 chiamate, AS01 e SRD 14. Le pagine sono più corte di quelle regionali
(4–9 mila caratteri ritagliati); con `COSTO_BANDO` = 0,061 $ come tetto,
al più 0,12 $. Le pagine vuote non costano. Le scansioni successive non
costano finché il GAL non pubblica bandi nuovi.

### Esito (12/11/2026)

- Fonte e elenco in `fonti.csv` ed `elenchi.csv`; `html.unescape` dopo la
  tabella delle entità (otto bandi regionali dell'archivio: testo e
  ritaglio identici a prima; sulle pagine tematiche cambiano solo le
  frecce di paginazione); esito "senza scadenza leggibile"; opzione
  `--fonte`. Test in `tests/test_gal.py` sulle pagine salvate.
- Prova senza modello: 4 voci, 2 pagine vuote saltate, 2 al modello; i
  12 candidati della Regione invariati.
- Corsa: 2 chiamate, 0,106 $. AS01 salvato con "storico: scaduto il
  2026-10-12" (la proroga, non il 18/09), SRD 14 con "storico: scaduto
  il 2026-05-08". AS01: contributo 20.000–80.000 €, 90%, dotazione
  710.624 €, 8 righe di beneficiari, 7 interventi.
- Da correggere, non fatto in questa tappa:
  - gli interventi (e) viabilità rurale e (f) reti idriche sono riservati
    agli enti pubblici sulla pagina, ma `interventi_bando` non ha dove
    scriverlo: la frase salvata si ferma prima di "-> Enti pubblici", e il
    dettaglio li elenca come ammissibili per tutti;
  - "Enti religiosi" classificato come `qualsiasi_soggetto` con la
    condizione "ente religioso": la lista dei tipi non ha un tipo per gli
    enti religiosi;
  - contributo minimo e massimo salvati ma non mostrati nel dettaglio
    (voce 5 della revisione);
  - SRD 14: `contributo_perc` 65, il massimo tra 50% piccole imprese,
    60% microimprese e 65% microimprese con titolare giovane; le
    percentuali per categoria restano solo sulla pagina.

---

## 5. Tappa 5: fonte Incentivi Italia (file open data)

### La fonte

Dalla nota di ricognizione (`docs/ricognizione-fonti.md`, 3.3):
`OpenData_Incentivi.csv`, pagina <https://www.incentivitalia.gov.it/open-data>,
sezione **Incentivi**, licenza CC BY 4.0, aggiornamento settimanale,
6.095 righe e 50 colonne al 12/11/2026. Copre la CCIAA Pistoia-Prato,
parte del CSR tramite GAL, gli avvisi comunali registrati come aiuti, il
bando ISI INAIL. Non copre SRE01, SRB01, SRG02, SRA31, e non registra
tutte le proroghe (AS01: 18/09 nel file, 12/10 sulla pagina del GAL).

File già scaricato, **fuori dal repository**, con il documento dei
metadati:

```
C:\Users\Matteo_Papucci\Desktop\programmazione\dati-grezzi\incentivi-italia\2026-11-12\
```

Letto il 13/11/2026 per la misura (sotto), con script fuori dal
repository, senza modello e senza scrivere nell'archivio.

Vincoli:

- **mai la sezione Aiuti** (aiuti individuali, dati personali). Il
  lettore controlla l'intestazione e rifiuta un file che non ha le
  colonne della sezione Incentivi;
- il file, o parti di esso, non entra nel repository. I test usano
  poche righe inventate con la stessa struttura;
- il catalogo e l'API del sito non si leggono: solo il file, scaricato
  a mano e passato per percorso;
- nessuna chiamata al modello per leggere il file. Il modello legge solo
  le pagine d'ente delle righe aperte per enti pubblici (decisione 2 del
  13/11/2026, punto 4).

### Misura del 13/11/2026

Data di riferimento 13/11/2026, file del 12/11/2026.

**Il file rispetto alla nota.** 51 colonne, non 50; separatore `,`. La
colonna della dimensione si chiama `Dimensione_beneficiari` (i metadati
dicono `Dimensioni`): il lettore usa il nome del file. `Comuni` è diviso
solo da `;`, mai da `\,` come dicono i metadati. Gli elenchi dei comuni
contengono anche il vecchio nome "Abetone", ma nessuna riga ha solo i
nomi precedenti alla fusione: la corrispondenza esatta sui tre nomi
attuali non perde righe.

**Regola A/B/C della nota.**

| | totale | aperte | sportello senza chiusura | in arrivo | senza date | scadute da meno di 12 mesi | più vecchie |
|---|---|---|---|---|---|---|---|
| A | 28 | 2 | 1 | 0 | 0 | 9 | 16 |
| B | 194 | 10 | 11 | 0 | 0 | 49 | 124 |
| C | 860 | 57 | 45 | 2 | 2 | 173 | 581 |
| A, B o C | 900 | 59 | 46 | 2 | 2 | 192 | 599 |

Delle 301 righe non scadute da più di 12 mesi, raggruppate per ente
concedente: 11 del territorio, 50 della Regione per tutta la regione, 146
di enti nazionali, 14 di università e poli, **10 della Regione con un
elenco di comuni senza i nostri** (bandi di altri GAL), **70 di enti
locali di altri territori** (altre camere di commercio toscane, comuni e
regioni di altre regioni etichettati con tutte le regioni o con la
Toscana, film commission). Il rumore viene dal campo `Regioni`, non dal
confronto dei nomi.

**Campione controllato a mano:** 20 righe (10 aperte, 10 tra in arrivo e
scadute da meno di 12 mesi, seme fisso). Si applicano al territorio 12,
dipende 4, no 4. Le 17 nazionali: 11 sì, 4 dipende, 2 no (un comune
piemontese e la Regione Marche etichettati con tutte le regioni). Le 3
toscane o locali: 1 sì, 2 no (CCIAA Arezzo-Siena, FAR Maremma). Il campo
`Tipologia_Soggetto` è più largo del bando: un fondo dell'Istituto per il
Credito Sportivo indica "Ente Pubblico" mentre la descrizione esclude gli
enti territoriali; un bando del MUR riservato agli HUB del PNRR indica
"Impresa".

**Altre misure.** 31 dei 46 sportelli senza chiusura sono aperti da prima
del 2025; 7 righe hanno una chiusura di comodo tra il 2030 e il 2050. 227
delle 900 righe hanno un `Link_istituzionale` usato anche da altre righe
(73 tra le non vecchie). In `bandi` ci sono già 3 indirizzi del file (4
righe: due FSE+ sicurezza, operatore forestale, AS01).

**Regola nuova, applicata** (prima la data, poi i comuni, poi
l'ente): delle righe non scadute da più di 12 mesi con la Toscana o uno
dei nostri comuni, 62 scartate per elenco di comuni senza i nostri, 70
per ente di altro territorio, 12 da verificare (tutte scadute da meno di
12 mesi); **passano 209**: 7 del territorio, 53 regionali, 149 nazionali.
Per stato: 43 aperte, 44 sportelli senza chiusura, 2 in arrivo, 120
scadute da meno di 12 mesi.

### Resa reale (13/11/2026)

Importazione del file del 12/11/2026 (`importa_incentivi`), dopo il
controllo delle pagine degli enti, senza modello:

| stato | territorio | regionale | nazionale | totale |
|---|---|---|---|---|
| aperto | 1 | 1 | 3 | 5 |
| sportello | 0 | 8 | 4 | 12 |
| in arrivo | 0 | 0 | 0 | 0 |
| storico | 5 | 6 | 26 | 37 |
| **salvati** | **6** | **15** | **33** | **54** |

Da verificare a mano 154: data di chiusura del catalogo non trovata
sulla pagina 67; link usato da più righe 43; sportello senza chiusura
aperto da più di 2 anni 17 (decisione 1 del 13/11/2026, seconda serie);
concedente da verificare 12; robots.txt che vieta 7; pagina non
scaricata 5; robots.txt non leggibile 2; sportello con "Chiuso" sulla
pagina 1. Gia' in archivio da un'altra fonte 4 (AS01 compreso). Le 54
righe hanno solo tipi privati (211 righe di `beneficiari_bando` con
origine `catalogo`, nessuna di tipo pubblico).

Pagine per enti pubblici lette con il modello (`estrai_incentivi`), 9:
2 bandi salvati, 6 pagine che non sono bandi (sezioni informative, un
indice di avvisi, la home di un ministero), 1 pagina non trovata (404).
Costo reale 0,338 $ (0,038 $ a pagina). Enti pubblici: il fondo di
garanzia per l'impiantistica sportiva ammette `altro_ente_pubblico` ed
esclude gli enti territoriali; il bando automotive nessuno. Nessuno
ammette i comuni: `bandi_aperti_per_ente` per Abetone Cutigliano e'
rimasto identico.

I due bandi salvati dal modello sono stati poi tolti dall'archivio e
messi tra le righe da verificare (decisioni del 13/11/2026, terza serie):
il fondo per l'impiantistica sportiva mescolava due misure della stessa
pagina (la frase sugli enti pubblici era del comparto "patrimonio
culturale"); il bando automotive aveva perso le imprese (frase non
trovata nella pagina) e restava con la sola `ricerca_formazione`.

**Numeri finali:** 54 bandi in archivio da Incentivi Italia, tutti dal
file e con i soli tipi privati; 156 righe da verificare (le 154 del file
e le 2 tolte); 6 pagine del modello che non sono bandi; 1 pagina da
ritentare (404). Costo del modello 0,338 $, per nessun bando rimasto.

**Perche' la resa e' bassa.** Su 209 righe del territorio ne entrano 54,
e solo 5 aperte con una data di chiusura.
Le date del catalogo sono spesso diverse da quelle delle pagine: proroghe
non registrate (contributi all'autotrasporto: proroga al 15/10/2026 sulla
pagina), date diverse (Sea Modal Shift: 17/11 nel catalogo, 9/11 sulla
pagina), date di comodo (2035, 2050), pagine generiche al posto del bando
(poli digitali, sezioni dei siti ministeriali). Il catalogo serve a
segnalare: il dato da citare resta quello della pagina dell'ente.

Anche il modello rende poco su queste pagine: 6 delle 9 non sono bandi,
e i 2 bandi estratti non erano affidabili. Il Link_istituzionale del
catalogo punta spesso a una sezione del sito, non alla pagina del bando.

### Come entra nell'archivio

Fonte `incentivi-italia` di tipo `file` (tappa 1), con una riga in
`elenchi` (`attivo` = 0) per la pagina open data da citare.

1. **Lettura.** Separatore rilevato dal codice (`csv.Sniffer`), colonne
   per nome e mai per posizione, multivalore divisi su `\,` (Regioni,
   Dimensione, Settore, Tipologia) e `;` (Comuni), date `YYYY-MM-DD`.
2. **Regola territoriale** (decisione 1 del 13/11/2026, al posto di
   A/B/C). Decide l'ente concedente, non il campo `Regioni`:
   - la riga deve avere la Toscana in `Regioni`, oppure uno dei tre
     comuni in `Comuni`;
   - se `Comuni` non è vuoto, deve contenere uno dei tre comuni, come
     token esatto e mai per sottostringa; altrimenti è scartata, anche
     se l'ente è la Regione Toscana;
   - `Soggetto_Concedente`, con il nome normalizzato (minuscole, spazi
     compressi), si cerca in una tabella chiusa nel codice: `territorio`,
     `regionale`, `nazionale` passano; `altro territorio` è scartato;
     `da verificare` non si salva e va tra le "da verificare a mano";
   - un concedente che non è nella tabella è `da verificare`, mai
     classificato per somiglianza; lo script stampa i valori nuovi a ogni
     aggiornamento del file.

   La tabella è in `docs/concedenti-incentivi.md`, da approvare prima di
   scriverla nel codice.
3. **Stato dalle date del file, solo per scartare.** Righe con
   `Data_chiusura` passata da più di 365 giorni: scartate senza scaricare
   nulla (la stessa soglia dello storico). Le altre (aperte, in arrivo,
   sportelli senza chiusura, chiuse da meno di 12 mesi) passano al punto
   4: per loro le date del file non bastano.
4. **Scadenza controllata sulla pagina dell'ente** (`Link_istituzionale`),
   senza modello:
   - prima di scaricare, robots.txt del dominio con
     `urllib.robotparser`: se vieta, la riga va tra le "da verificare a
     mano";
   - se l'URL canonico è già in `bandi`, di qualunque fonte, la riga si
     salta: vale il bando acquisito dalla pagina, che ha le prove
     (nessun doppione, come per l'acquisizione per URL canonico);
   - un `Link_istituzionale` usato da più righe del file non è la pagina
     di un bando (è un elenco o una home): la riga va tra le "da
     verificare a mano";
   - la pagina si scarica e si cerca la `Data_chiusura` del file in
     tutte le forme (ISO, gg/mm/aaaa, gg.mm.aaaa, "gg mese aaaa"),
     con i confini numerici della voce 1. Trovata: la riga si salva, con
     la frase della pagina che la contiene come prova. Non trovata (es.
     una proroga), o pagina non scaricabile: la riga non si salva e va
     tra le "da verificare", con il motivo;
   - sportelli senza `Data_chiusura`: si salvano se la pagina risponde e
     non contiene parole di chiusura ("chiuso", "esaurite le risorse",
     "graduatoria"); altrimenti "da verificare". Si salvano con
     `a_sportello` = 1 e `pubblicato_il` = `Data_apertura`, così vale la
     regola della tappa 5a del piano post-scansione (decisione 3 del
     13/11/2026): pubblicati da più di due anni senza data di chiusura,
     "probabilmente esaurito". Sul file del 12/11/2026: 28 dei 44
     sportelli che passano la regola.
   - **righe per enti pubblici** (decisione 2 del 13/11/2026): le righe
     aperte, sportello o in arrivo con "Ente Pubblico" in
     `Tipologia_Soggetto` non si salvano dal file. La pagina del
     `Link_istituzionale` va all'estrazione con il modello, come gli
     altri bandi (`estrai_bando`), con le stesse esclusioni: robots.txt,
     link già in `bandi`, link condiviso con altre righe. Il catalogo
     non basta a dire se un comune può partecipare. Sul file del
     12/11/2026: 12 righe, 11 indirizzi, nessuna con il solo tipo "Ente
     Pubblico"; 1 indirizzo già in `bandi`, 1 condiviso da due righe
     (da verificare a mano): **9 pagine al modello, su 7 domini**.
5. **Riga di `bandi`.** `id` = `incentivi-` + `ID_Incentivo`;
   `url` = `Link_istituzionale` canonico (è la fonte da citare);
   `ente` = `Soggetto_Concedente`; `titolo`, `apertura`, `scadenza`;
   `contributo_min/max` da `Agevolazione_Concedibile_Min/Max`,
   `costo_min/max` da `Spesa_Ammessa_Min/Max`; `beneficiari` dal testo
   di `Tipologia_Soggetto` e `Dimensione_beneficiari`; `territorio` da
   `Regioni`/`Comuni`; `fonte` = "Incentivi Italia, OpenData_Incentivi.csv
   del …, CC BY 4.0"; `codice_fonte` = `incentivi-italia`. Lo stato non
   si memorizza. `Descrizione` non si copia.
6. **Tipi di beneficiario.** Corrispondenza fissa nel codice tra i
   valori di `Tipologia_Soggetto`/`Dimensione_beneficiari` e
   `TIPI_BENEFICIARIO`, scritta dopo aver letto i valori distinti del
   file e il documento dei metadati. Righe di `beneficiari_bando` con
   un'origine nuova, `catalogo` (oggi `ORIGINI` ammette `estrazione` e
   `ammette_comuni`), e come frase il valore del file. Un valore senza
   corrispondenza: nessun tipo, e un avviso, mai un tipo plausibile.
7. **Registro.** Ogni riga esaminata in `scansioni`, con chiave l'URL
   canonico, esito e motivo; le "da verificare" con esito `scartato` e un
   motivo che non comincia con "scaduto", così tornano a ogni
   aggiornamento del file.

Le righe "da verificare" non vanno al modello: si controllano a mano.
Al modello vanno solo le pagine delle righe aperte per enti pubblici
(punto 4).

Da decidere: `pubblicato_origine` oggi ammette `pubblicazione` e `atto`;
la `Data_apertura` del catalogo non è né l'una né l'altra. Proposta: un
valore nuovo, `apertura`, in `ORIGINI_PUBBLICAZIONE` e nel vincolo dello
schema (ricreazione del database, dopo l'esportazione dei CSV).

Da decidere: le righe per enti pubblici scadute da meno di 12 mesi (31,
31 indirizzi) entrerebbero nello storico con i tipi del catalogo. La
decisione 2 riguarda solo le aperte e in arrivo.

### File

| file | cosa | perché |
|---|---|---|
| `src/estrazione/incentivi.py` (nuovo) | lettura del file, controllo dell'intestazione, regola territoriale con la tabella dei concedenti approvata, controllo della data sulla pagina, righe di `bandi` e `beneficiari_bando`, elenco delle pagine per enti pubblici da passare all'estrazione | la fonte |
| `scripts/ingestione/importa_incentivi.py` (nuovo) | `--file PERCORSO`, `--prova` (conta e stampa senza scrivere), `--misura` (conteggi per classe di concedente e per stato, concedenti nuovi), esportazione dei CSV in un `finally` | |
| `src/estrazione/bandi.py`, `src/database/schema.py` | origine `apertura` per `pubblicato_il`, se approvata | regola 5a sugli sportelli |
| `docs/concedenti-incentivi.md` (nuovo, già scritto) | tabella dei concedenti da approvare | decisione 1 |
| `src/estrazione/beneficiari.py` | origine `catalogo` in `ORIGINI`; corrispondenza dei valori del file | |
| `src/database/schema.py` | il vincolo sulle origini segue `ORIGINI` | |
| `data/processed/fonti.csv`, `elenchi.csv` | riga della fonte e della pagina open data | |
| `tests/dati/incentivi_prova.csv` (nuovo) | 10-15 righe **inventate**, con le colonne del file: comuni con nomi simili (San Marcello nelle Marche, Sambuca di Sicilia), un incentivo nazionale con tutte le regioni, uno sportello, uno scaduto da 2 anni, uno da 3 mesi, due righe con lo stesso link | test senza il file vero |
| `tests/pagine/incentivi-*.html` (nuovi) | due o tre pagine d'ente **inventate**: una con la data, una senza (proroga) | test sulle pagine salvate |
| `tests/test_incentivi.py` (nuovo) | test sotto | |
| `README.md`, `docs/roadmap.md` | la fonte, e l'aggiornamento settimanale nel passo 4 | |

### Test

- file con le colonne della sezione Aiuti al posto di quelle degli
  Incentivi: rifiutato;
- separatore `;` e `,`: letto in entrambi i casi;
- multivalore `\,` e `;` divisi correttamente;
- "San Marcello" e "Sambuca di Sicilia" non passano il filtro, "San
  Marcello Piteglio" sì;
- comune di un'altra regione con tutte le regioni: scartato; Regione
  Toscana con un elenco di comuni senza i nostri: scartata; concedente
  sconosciuto: "da verificare", con l'avviso; stesso ente con maiuscole
  diverse: stessa classe;
- riga aperta con "Ente Pubblico": non salvata dal file, pagina passata
  all'estrazione (modello finto);
- sportello aperto da tre anni senza chiusura: salvato con
  `pubblicato_il`, e lo stato dice "probabilmente esaurito";
- scaduto da 2 anni: scartato senza scaricare la pagina (rete finta che
  fallisce se chiamata);
- data trovata sulla pagina in ciascuna forma: salvato con la prova;
  data assente: "da verificare", non salvato;
- robots.txt che vieta: "da verificare", pagina non scaricata;
- link già in `bandi`: saltato; link condiviso da due righe: "da
  verificare";
- valore di `Tipologia_Soggetto` sconosciuto: nessun tipo, un avviso;
- seconda importazione dello stesso file: nessuna riga in più;
- tutto sul database in memoria o su `db_su_file`.

### Regola di chiusura

- `ruff check` e `python -m pytest`, con l'output;
- `--misura` sul file vero: gli stessi conteggi della misura del
  13/11/2026 (209 righe che passano, 12 per enti pubblici), nessun
  concedente nuovo;
- `--prova` sul file vero: quante righe passano il filtro, quante
  scartate per data, quante salvabili, quante "da verificare" e perché;
- la verifica della nota ritrovata: CCIAA Pistoia-Prato presente; AS01
  saltato perché già in archivio dal GAL (tappa 4), non salvato con la
  data del file;
- `git status`: nessun file di `dati-grezzi` né sue parti nel
  repository; `grep` di un `ID_Incentivo` vero nei test: nessun
  risultato.

### Costo

Nessuna chiamata al modello per il file. Le pagine per enti pubblici: 9
sul file del 12/11/2026, al più 9 × 0,061 = **0,55 $**; a ogni
aggiornamento settimanale solo le righe nuove. Un giorno e mezzo di
lavoro, più il controllo a mano delle "da verificare". Il download delle
pagine d'ente per il controllo della data riguarda le 89 righe aperte,
sportello o in arrivo e le 120 scadute da meno di 12 mesi che passano la
regola, meno i link già in `bandi` e quelli condivisi.

---

## Riepilogo dei costi

| tappa | chiamate al modello | costo stimato | lavoro |
|---|---|---|---|
| già fatta: riestrazione di premi imboschimenti | 1 | 0,066 $ (misurato) | |
| 1. fonti ed elenchi dal database | 0 | 0 $ | un giorno |
| 2. elenco della montagna | 0 | 0 $ | mezz'ora |
| 3. storico degli scaduti | 0 | 0 $ | mezza giornata |
| 4. GAL MontagnAppennino | 2 (AS01, SRD 14) | al più 0,12 $ | mezza giornata |
| 5. Incentivi Italia | 9 (pagine per enti pubblici) | al più 0,55 $ | un giorno e mezzo |
| **totale** | **11** | **al più 0,67 $** | |

Stime con `COSTO_BANDO` = 0,061 $ come tetto per pagina (misurato il
12/11/2026). La scansione regolare successiva non è compresa: con la
tappa 2 non aggiunge pagine; l'unica pagina nuova dell'elenco generale
oggi è "Digitale facile".

Le alternative scartate, per confronto: rischio sismico come elenchi
0,65–1,28 $; montagna "in attuazione" circa 0,12 $.

## Decisioni (12/11/2026, dopo la seconda versione)

1. **Modifica a mano di `fonti.csv`** (tappa 1): approvata alle
   condizioni del piano, con il diff mostrato prima di applicarla.
2. **Premi imboschimenti:** si salva come storico dopo la tappa 3,
   dall'estrazione conservata in `dati-grezzi\estrazioni\`.
3. **Controllo degli elenchi dei programmi:** in roadmap, tra i
   requisiti dell'aggiornamento automatico (passo 4).
4. **Incentivi Italia, righe "da verificare":** si decide dopo la
   misura, alla tappa 5. Deciso il 13/11/2026: controllo a mano (sotto).

## Decisioni (13/11/2026, dopo la misura di Incentivi Italia)

1. **Regola territoriale basata sull'ente concedente** al posto di
   A/B/C (tappa 5, punto 2). La tabella dei concedenti si approva in
   `docs/concedenti-incentivi.md` prima di scriverla nel codice.
2. **Bandi per gli enti pubblici:** la tipologia del catalogo non basta.
   Le righe aperte o in arrivo che dal catalogo risultano rivolte a enti
   pubblici non si mostrano ai comuni sulla base del solo file: si
   estraggono con il modello dalla pagina del `Link_istituzionale`, come
   gli altri bandi (tappa 5, punto 4). 9 pagine, al più 0,55 $.
3. **Sportelli senza chiusura:** vale anche per questa fonte la regola
   della tappa 5a ("probabilmente esaurito" se pubblicati da più di due
   anni senza data di chiusura), con `pubblicato_il` = `Data_apertura`.
4. **Le righe "da verificare"** non vanno al modello.

## Decisioni (13/11/2026, dopo la prova di Incentivi Italia)

1. **Sportelli senza chiusura aperti da piu' di due anni** (soglia di
   `SOGLIA_SPORTELLO_ANNI`): dal file non si salvano, vanno tra le righe
   da verificare. Sul file del 12/11/2026: 17 righe, tra cui Nuova
   Sabatini e Smart&Start, ancora attive: vanno controllate a mano. Le
   righe aperte per enti pubblici vanno comunque al modello.
2. **Link condivisi:** restano da verificare. Dopo la demo, la regola
   "stesso concedente e stesse date" (roadmap, In coda).
3. **Scrittura e modello:** fatti il 13/11/2026 (resa reale sopra).
   `pubblicato_origine` ammette `apertura`; `beneficiari_bando.origine`
   ammette `catalogo`: database ricreato dai CSV, con backup e conteggi
   identici prima e dopo, salvo le righe nuove di `fonti` ed `elenchi`.

## Decisioni (13/11/2026, terza serie, dopo la lettura con il modello)

1. **Fondo di garanzia per l'impiantistica sportiva e Automotive** tolti
   dall'archivio e messi tra le righe da verificare, con il motivo
   (`scripts/manutenzione/togli_bandi_incentivi.py`, nessuna chiamata al
   modello). `estrai_incentivi` non rilegge le pagine gia' esaminate con
   esito salvato o scartato; ritenta solo le fallite.
2. **Sport Missione Comune 2026 e Cultura Missione Comune 2026**
   (Istituto per il Credito Sportivo e Culturale): da recuperare prima
   della demo. **Non sono nel catalogo** Incentivi Italia: sono
   contributi in conto interessi su mutui degli enti territoriali, non
   aiuti alle imprese. Le due righe dell'Istituto con il link condiviso
   sono i comparti del fondo per il patrimonio culturale. Pagine
   ufficiali trovate dalla home del sito: `/fondi-speciali-bandi-sport-2026/`,
   `/fondi-speciali-bandi-cultura-2026/` e la notizia della proroga al
   5/12/2026 (`/proroga-sport-missione-comune-cultura-missione-comune/`).
   robots.txt del 13/11/2026: pagine HTML permesse (vietati PDF, immagini
   e simili), `Crawl-delay: 2`. La pagina di Sport Missione Comune, letta
   senza modello, conferma la regola di chiusura: domande "a partire dalle
   ore 12,00 del 09/03/2026 e non oltre le ore 23,59 del 05/12/2026";
   "Comuni, Unioni di Comuni, Comuni in forma associata, Città
   Metropolitane, Province e Regioni"; "2 milioni di euro per i piccoli
   Comuni (fino a 5.000 abitanti)". L'estrazione aspetta una fonte nuova
   in `fonti.csv`: `estrai_bando` non estrae un dominio che non e' una
   fonte, e attribuirle a `incentivi-italia` sarebbe falso.
3. **Sport e Periferie 2026** (Dipartimento per lo Sport): non e' nel
   catalogo. Secondo la pagina ufficiale e' chiuso: domande "a partire
   dalle ore 12:00 del 4 giugno 2026 e fino alle ore 12:00 del 25 giugno
   2026"; a luglio pubblicati gli elenchi dei comuni ammessi a
   valutazione, con i termini per la documentazione progettuale dal
   22/07/2026. Non salvato.
4. **Misure nazionali per le imprese** escluse dalla regola degli
   sportelli ma ancora attive (Nuova Sabatini, Smart&Start, ISI INAIL):
   verifica a mano prima della demo, se c'e' tempo (roadmap).

## Decisioni ed esito (13/11/2026, quarta serie: Missione Comune)

1. **Fonte nuova `istituto-credito-sportivo`** (tipo `pagine`, url_base
   https://www.creditosportivo.it, schema_link sulle pagine
   `/fondi-speciali-bandi-…/`), con la home come elenco **spento**
   (`attivo` = 0): le righe di `fonti.csv` ed `elenchi.csv` approvate con
   il diff. Database ricreato: backup in
   `dati-grezzi/backup/comune-2026-11-13-prima-di-credito-sportivo.sqlite`,
   conteggi identici prima e dopo salvo le due righe nuove.
2. **Estrazione con `estrai_bando --auto`**, una chiamata per pagina,
   dopo la prova senza modello (fonte riconosciuta, robots.txt che
   permette, nessun conflitto di identificativo, frasi della regola nel
   testo): salvati `sport-missione-comune-2026` e
   `cultura-missione-comune-2026`, a sportello fino al 2026-12-05.
   Entrambi compaiono in `bandi_aperti_per_ente` per Abetone Cutigliano.
3. **Difetto trovato e corretto** in `_valida_beneficiari`
   (`src/estrazione/bandi.py`): due soggetti con lo stesso tipo e la
   stessa frase si fondevano sommando le condizioni, e un soggetto
   ammesso senza condizioni ("Comuni") prendeva quelle dell'altro
   ("Comuni in forma associata"). Ora, se uno dei due e' senza
   condizioni, la riga fusa non ne ha. Riga di Sport Missione Comune
   corretta di conseguenza (condizioni vuote per `comune` e
   `unione_comuni`), senza nuove chiamate. Da controllare nidi gratis
   2026-2027, con lo stesso schema (roadmap).
4. **Regola di chiusura di Sport Missione Comune:** scadenza 2026-12-05
   si'; Comuni e Unioni ammessi si'; presente per Abetone si'. **Il mutuo
   massimo di 2 milioni per i comuni fino a 5.000 abitanti non e' in
   nessun campo**: la pagina da' tre fasce (2, 4, 6 milioni) per tipo e
   dimensione dell'ente, ed e' l'importo del mutuo agevolabile, non il
   contributo. Il modello lo ha riconosciuto (prova di `contributo_max`)
   ma ha lasciato il valore vuoto. Da decidere dove registrarlo.

## Decisioni ed esito (13/11/2026, quinta serie)

1. **Mutuo massimo per fascia di ente**: la frase della pagina, testuale,
   aggiunta al testo dei beneficiari di Sport e Cultura Missione Comune
   ("L'importo massimo di mutuo agevolabile per ciascuna istanza e
   complessivo è: 2 milioni di euro per i piccoli Comuni (fino a 5.000
   abitanti); 4 milioni …; 6 milioni …"), letta dalla pagina al momento
   (`scripts/manutenzione/importi_missione_comune.py`). Campo strutturato
   per gli importi per fascia: roadmap, dopo la demo.
2. **Cultura Missione Comune**: `contributo_perc` svuotato (era 100,
   l'abbattimento totale degli interessi), con la frase della pagina
   nella nota. Prompt dell'estrattore, regola IMPORTI: l'abbattimento
   degli interessi di un mutuo non e' un contributo sul costo, e il mutuo
   massimo agevolabile non e' `contributo_max` ne' `costo_max`.
3. **Simulazione della fusione corretta dei beneficiari**, senza modello
   e senza scrivere. Le risposte grezze del modello sono conservate solo
   per tre bandi: premi imboschimenti (`dati-grezzi\estrazioni\`) e i due
   Missione Comune (output del 13/11/2026). Su questi la simulazione e'
   esatta: cambia solo Sport Missione Comune, gia' corretto. Per gli
   altri bandi l'archivio ha solo le righe gia' fuse: controllo della
   firma del difetto (riga con condizioni la cui frase elenca il tipo
   due volte, una voce nuda e una con la condizione) sulle 149 righe con
   condizioni: 1 candidata, amianto edifici pubblici, falso positivo (la
   condizione "con sede nel territorio della Regione Toscana" vale per
   tutti gli enti locali della frase). Nidi gratis 2026-2027: non e' il
   difetto; la frase ammette le Unioni come "esercizio associato" dei
   Comuni, con una sola voce, e i Comuni restano senza condizioni.
   Nessuna riga da correggere; la decisione resta all'utente.
