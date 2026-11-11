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
