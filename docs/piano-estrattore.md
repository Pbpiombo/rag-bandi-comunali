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
- **Frasi controllate sulla pagina**: beneficiari, interventi, cumulabilità; da
  estendere a scadenza e sportello (bloccanti se la frase non si trova) e a
  data di pubblicazione e importi (vuoti con avviso).
- **`ammette_comuni` tolto** da `bandi`: si ricava da `beneficiari_bando`.
- **Smistamento con un modello più economico**: rimandato.
- **Test con il modello vero**: marcati `modello`, esclusi per impostazione
  predefinita, lanciati solo su richiesta.

## Tappe

- **a. Schema e migrazione**: fatta. Test di equivalenza per i comuni su 35
  interrogazioni.
- **b. Estrattore**: fatta. Da completare il controllo delle frasi di
  scadenza, sportello, pubblicazione e importi; da lanciare i 3 test con il
  modello vero.
- **c. Interrogazioni**: `bandi_aperti_per_ente` per tipo di ente, etichette
  con le condizioni, `bandi_per_beneficiario`, gruppo "a sportello",
  `dettaglio_bando` con beneficiari, interventi e cumulabilità. Togliere
  l'alias provvisorio `AMMETTE_COMUNI`. Aggiornare il test di equivalenza dove
  il testo cambia di proposito.
- **d. Contenimento del costo**: scadenza letta dalla pagina senza modello
  (margine di un anno), filtro sull'anno nello slug. Prima della scansione
  completa.

## Dopo il piano

Scansione completa: circa 135 candidati, più i 21 bandi in archivio da
riclassificare.
