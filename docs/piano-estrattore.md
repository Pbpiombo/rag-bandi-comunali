# Piano: estrattore nuovo (passo 3)

Piano approvato l'11 novembre 2026. Se la conversazione con Claude Code viene
azzerata, si riparte leggendo questo file.

## Obiettivo

Acquisire tutti i bandi, non solo quelli per i Comuni, registrando per
ciascuno chi può partecipare, a quali condizioni, cosa finanzia e se è
cumulabile con altri finanziamenti. Ogni informazione con la frase del bando
da cui viene, controllata sulla pagina.

## Decisioni

- **Tipi di beneficiari**: lista chiusa in `src/estrazione/beneficiari.py`.
  Enti pubblici (`comune`, `unione_comuni`, `altro_ente_pubblico`), imprese
  (`impresa_agricola`, `impresa_turistica`, `impresa_artigiana_commerciale`,
  `altra_impresa`), `terzo_settore`, `cittadini_famiglie`,
  `ricerca_formazione`, `qualsiasi_soggetto` (beneficiario definito da un
  requisito; condizioni obbligatorie).
- **Regole di corrispondenza** (`TERMINI`) applicate dal codice, non solo dal
  prompt: "enti locali" comprende comune, unione di comuni e altri enti
  pubblici. La regola "imprese senza settore" per ora è solo nel prompt.
- **Musei ed ecomusei di rilevanza regionale**: `qualsiasi_soggetto` con la
  condizione, non `comune`.
- **Procedure non di finanziamento** (es. qualifica di museo): `non_bando`,
  scarto definitivo.
- **Scarti**: solo `non_bando` e scaduti sono definitivi. Il tipo di
  beneficiario non è più motivo di scarto. La scadenza non determinata è uno
  scarto non definitivo.
- **Bandi a sportello**: si salvano, con `pubblicato_il`. Etichetta calcolata
  "a sportello, verificare la disponibilità delle risorse"; oltre 2 anni
  dalla pubblicazione, avviso "probabilmente esaurito". Mostrati con l'avviso,
  non esclusi. La soglia è una costante.
- **Frasi controllate sulla pagina**: beneficiari, interventi, cumulabilità,
  scadenza e sportello (bloccanti se la frase non si trova), data di
  pubblicazione e importi (vuoti con avviso). Lo sportello si controlla solo
  quando è vero.
- **`ammette_comuni` tolto** da `bandi`: si ricava da `beneficiari_bando`.
- **Smistamento con un modello più economico**: rimandato.
- **Test con il modello vero**: marcati `modello`, esclusi per impostazione
  predefinita, lanciati solo su richiesta.

## Tappe

- **a. Schema e migrazione**: fatta. Test di equivalenza per i comuni su 35
  interrogazioni.
- **b. Estrattore**: fatta, con il controllo delle prove esteso a scadenza,
  sportello, pubblicazione e importi. I 3 test con il modello vero passano.
  Costo misurato (`claude-sonnet-5`): circa 0,026 $ per bando (4.230 token in
  ingresso, 1.760 in uscita), circa 0,012 $ per una pagina che non è un bando.
- **c. Interrogazioni**: fatta. Test di equivalenza aggiornato: 31
  interrogazioni su 35 cambiano testo, tutte per modifiche volute e
  approvate una per una; riferimento in
  `tests/dati/interrogazioni_comuni_dopo.json`.
  - `bandi_aperti_per_ente` e `bandi_in_scadenza` per ente (`per_ente=True`):
    il tipo viene da `enti.tipo`; valgono le righe del tipo e di
    `qualsiasi_soggetto`.
  - Condizioni scritte come requisito del richiedente e mostrate come
    "ammesso se …"; per `qualsiasi_soggetto` il soggetto del bando tra
    parentesi. Regola aggiunta al prompt dell'estrattore.
  - Unione: vede anche i bandi non classificati con la riga `comune`
    migrata, con la nota "beneficiari non ancora classificati: verificare se
    ammette le Unioni".
  - `bandi_per_tema`: "[ammessi: …]" per i classificati; per i non
    classificati "[ammessi: Comuni; altri beneficiari non ancora
    classificati]" o "[NON per i Comuni; altri beneficiari non ancora
    classificati]".
  - Sportello in un gruppo separato: "a sportello, verificare la
    disponibilità delle risorse (pubblicato il … / data di pubblicazione non
    indicata)", oppure "a sportello fino al …, verificare la disponibilità
    delle risorse"; oltre `SOGLIA_SPORTELLO_ANNI` (2) "probabilmente
    esaurito".
  - `bandi_per_beneficiario(tipo)` nuova; `dettaglio_bando` con beneficiari,
    interventi e cumulabilità (per le righe migrate senza la frase, che
    ripeterebbe il testo di `beneficiari`); `stato_archivio` conta gli aperti
    per l'ente.
  - Alias `AMMETTE_COMUNI` tolto; la data di oggi si legge solo in
    `data_di_oggi()`.
  - Musei: il modello scrive la condizione come accreditamento del museo
    ("validamente accreditato e non decaduto, elencato nell'Allegato A…"),
    fedele alla pagina, che non nomina il titolare. Forma accettata; il
    soggetto tra parentesi dice di chi si parla. Nessuna deduzione di
    "titolare di".
- **d. Contenimento del costo**: fatta. Preselezione senza modello in
  `src/estrazione/scadenza.py`, usata da `estrai_nuovi`: scarica ogni pagina
  candidata e decide prima del modello.
  - Campo "Data di scadenza presentazione domande" passato da più di un anno
    (`MARGINE_GIORNI` = 365): la pagina si registra come scaduta, motivo
    "scaduto il … (campo della pagina, senza modello)", scarto definitivo.
    Lettura rigida: vale solo un valore che è per intero una data; altrimenti
    decide il modello.
  - Anno nello slug fino a due anni fa (`elenco.recente`): la pagina si salta
    senza registrarla, **solo se il campo manca o non si legge**. Il campo vale
    più dello slug: "…-il-bando-2023" con il campo a 31.12.2027 va al modello.
    Filtro predefinito; `--tutti-gli-anni` lo disattiva. Tolta `--recenti`.
  - Corretta la regex dell'anno nello slug: in "…-2023-2025" il secondo anno
    andava perso (7 slug su 135 avevano l'anno sbagliato).
  - `--prova` esegue la preselezione senza registrare e stima il costo.
  - Misura dell'11 novembre 2026 sui 135 candidati: 52 con il campo, 50
    leggibili (14 scaduti da oltre un anno, 2 da meno, 34 aperti); 69 con
    l'anno nello slug, 38 fino al 2024. Esclusi: 14 dal campo, 31 dallo slug
    senza campo leggibile. **Restano 90 per il modello**: tra 1,08 $ (nessun
    bando) e 2,34 $ (tutti bandi).

## Dopo il piano

Scansione completa: 90 candidati per il modello (1,08–2,34 $), più i 21
bandi in archivio da riclassificare (circa 0,55 $). In tutto, circa
1,6–2,9 $.

## Scansione completa dell'11 novembre 2026

Eseguita con `--tutti-gli-anni`, per misurare cosa perde il filtro
sull'anno. Strumenti aggiunti:
- `scripts/manutenzione/riclassifica_bandi.py`: riestrae i bandi in
  archivio non ancora classificati. Non scrive nulla se la pagina non si
  scarica, se la validazione fallisce o se il modello dice `non_bando`;
  un campo pieno che torna vuoto conserva il valore vecchio e si elenca a
  parte con il motivo, da controllare a mano.
- `estrai_nuovi`: segna le pagine che il filtro sull'anno avrebbe saltato
  e ne riporta gli esiti; conta i token e il costo; si ferma su credito
  esaurito o autenticazione senza registrare la pagina come fallita.

### Correzioni fatte durante la scansione

La prima corsa si e' fermata dopo 36 pagine: tutti i falliti (11, piu' 2
nella riclassificazione) erano bandi a sportello. Il modello scriveva
`a_sportello` come `true` nudo, senza la frase, e il controllo della prova
lo bloccava. Corretti:
- prompt: anche `a_sportello` e' un oggetto con la prova, con due esempi;
- codice: un `false` nudo si accetta senza prova; un `true` resta
  bloccante senza la frase verificata;
- importi: un punto seguito da 1 o 2 cifre finali e' decimale ("19.5
  milioni", "343423.56"), seguito da 3 resta delle migliaia ("12.500").

Verifica su tre pagine prima di rilanciare: voucher just in time e
biotrituratori con lo sportello provato dalla frase; fondo di garanzia
energie rinnovabili `false`, perche' la pagina non nomina sportello ne'
scadenza (accettato: il valore vecchio non aveva prova).

### Esiti

Pagine candidate 135: 14 scadute secondo il campo della pagina, senza
modello; 121 esaminate dal modello.

| esito | pagine |
|---|---|
| salvati | 28 (16 a sportello, 12 con scadenza) |
| scaduti | 52 (38 dal modello, 14 dal campo) |
| non bandi | 45 |
| scadenza non determinata | 3 |
| scadenza a bassa confidenza | 1 |
| falliti | 6 |

Falliti: 5 senza beneficiari con frase verificata (in 3 anche il campo
`beneficiari` vuoto), 1 con la prova della scadenza non trovata.

Riclassificazione dei 21 bandi in archivio (due corse): 18 classificati,
3 che il modello giudica non bandi (lasciati come erano: una
manifestazione di interesse e due pagine diventate graduatorie), 1 di
questi fallito alla seconda corsa sulla prova della scadenza. Valori
vecchi mantenuti perche' il nuovo e' vuoto: 16, in 11 bandi.

### Filtro sull'anno nello slug

Le 31 pagine che il filtro avrebbe saltato (anno passato nello slug,
campo della scadenza assente o illeggibile): **nessuna aperta**. 18
scadute, 11 non bandi, 2 a scadenza non determinata. Esaminarle e' costato
circa 0,94 $. Il filtro resta attivo per impostazione predefinita.

### Costo reale

| corsa | estrazioni | token ingresso | token uscita | costo | stima |
|---|---|---|---|---|---|
| riclassificazione 1 | 21 | 138.290 | 50.795 | 0,785 $ | 0,55 $ |
| riclassificazione 2 | 5 | 27.952 | 9.935 | 0,155 $ | 0,13 $ |
| scansione 1, interrotta | 36 | non misurati | | circa 1,1 $ | |
| scansione 2 | 97 | 566.775 | 179.813 | 2,932 $ | 1,16–2,52 $ |
| verifica su 3 pagine | 3 | non misurati | | circa 0,1 $ | |

Misurato 3,87 $; con le due corse non misurate, circa 5,1 $ contro i
1,6–2,9 $ previsti. Per estrazione 0,030–0,037 $, con 5.600–6.600 token
in ingresso contro i 4.230 della tappa b: il prompt e' cresciuto con le
tappe c e d, e le pagine reali sono piu' lunghe di quelle di prova. Una
pagina che non e' un bando non costa sensibilmente meno: la stima
"tra non bando e bando" va sostituita con circa 0,031 $ a pagina.

### Bandi classificati

46 bandi classificati, 31 aperti (compresi gli sportelli). Per tipo di
beneficiario, bandi in tutto e aperti: altra_impresa 13/10,
ricerca_formazione 11/7, comune 10/2, cittadini_famiglie 10/8,
altro_ente_pubblico 9/4, terzo_settore 9/4, impresa_agricola 8/7,
unione_comuni 7/1, impresa_turistica 5/4, qualsiasi_soggetto 4/3,
impresa_artigiana_commerciale 4/3. Aperti per almeno un tipo di ente
pubblico: 5.

Verifica a mano di 20 bandi scelti a caso (seme 20261111): fatta l'11
novembre 2026 su 23 bandi (i 20 a caso e 3 aperti per enti pubblici), con
la seconda verifica del 12 novembre sui 10 riestratti. Risultati in
`docs/verifica-manuale-2026-11-11.csv`, `docs/verifica-manuale-2026-11-12.csv`
e nel README (sezione "Misure"); correzioni in `docs/piano-post-scansione.md`.
