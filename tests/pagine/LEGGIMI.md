# Pagine salvate per i test dell'estrattore

Tre pagine reali del portale bandi della Regione Toscana, salvate l'11
novembre 2026 come testo, cioe' come le riceve il modello: l'HTML passato per
`a_testo` e `ritaglia` di `src/estrazione/pagina.py`.

| File | Pagina |
|---|---|
| `tpl.txt` | https://www.regione.toscana.it/-/contributi-per-sostenere-il-trasporto-pubblico-locale-nelle-aree-deboli |
| `musei.txt` | https://www.regione.toscana.it/-/bando-per-contributo-ordinario-ai-musei-ed-ecomusei-di-rilevanza-regionale |
| `qualifica.txt` | https://www.regione.toscana.it/-/presentazione-istanze-preliminari-per-riconoscimento-qualifica-di-museo/ecomuseo |

Per ogni pagina, `<nome>.risposta.json` e' la risposta corretta del modello,
scritta a mano: le frasi sono copiate dal testo. `tests/test_estrattore.py` la
fa passare per `interpreta`, `valida` e `decidi_automatico` senza chiamare il
modello. `tests/test_estrattore_reale.py` chiama il modello vero sulle stesse
pagine; e' marcato `modello` e non parte con `python -m pytest`.

## Pagine per la scadenza letta senza modello

Due pagine salvate l'11 novembre 2026 con il solo `a_testo`, senza
`ritaglia`: la preselezione di `src/estrazione/scadenza.py` legge il testo
completo. Le usa `tests/test_scadenza.py`.

| File | Pagina | Perche' |
|---|---|---|
| `estero.txt` | https://www.regione.toscana.it/-/lavorare-all-estero-borse-di-mobilit%C3%A0-professionale-per-disoccupati-o-inattivi-il-bando-2023 | "2023" nello slug, ma il campo dice 31.12.2027: va al modello |
| `scuole-paritarie.txt` | https://www.regione.toscana.it/-/avviso-pubblico-individuazione-gestori-scuole-paritarie-private-pi%C3%B9-rappresentative-a-livello-regionale | il campo c'e' ma non e' una data ("15 giorni dalla pubblicazione...") |

## Elenchi delle fonti

Estratti di pagine elenco, con i soli collegamenti: gli `href` reali,
nell'ordine della pagina. Li usa `tests/test_acquisizione.py` per provare la
lettura degli elenchi con le regole di `data/processed/fonti.csv`.

| File | Pagina | Perche' |
|---|---|---|
| `regione-sviluppo-rurale-bandi-aperti.html` | https://www.regione.toscana.it/sviluppo-rurale-2023-2027/bandi-aperti?delta=200, scaricata il 12 novembre 2026 | tre bandi, tre notizie di www.toscana-notizie.it con `/-/` nell'indirizzo, i collegamenti del piè di pagina (PEC, whistleblower, atti di notifica, accessibilità) |
| `montagna-bandi-aperti-vuota.html` | https://www.regione.toscana.it/politiche-per-la-montagna/bandi-aperti?delta=200, scaricata il 12 novembre 2026 | nessun bando ("Nessun risultato trovato"): solo menu della sezione e collegamenti del piè di pagina, che non devono dare voci |

## Pagine del GAL MontagnAppennino

Il blocco `<main>` delle pagine del sito, scaricate il 12 novembre 2026: senza
intestazione e piè di pagina, che contengono i contatti del GAL. HTML reale,
con le entità (`&rsquo;`, `&ldquo;`) come le scrive il sito. Le usa
`tests/test_gal.py`.

| File | Pagina | Perche' |
|---|---|---|
| `gal-elenco.html` | https://www.montagnappennino.it/bandi-e-graduatorie/ | l'elenco: quattro collegamenti `/bando/`, più allegati e pagine di servizio |
| `gal-as01.html` | https://www.montagnappennino.it/bando/aso1-investimenti-non-produttivi-e-per-lo-sviluppo-socio-economico-delle-ree-rurali/ | "PROROGATO alle ore 13.00 del 12 ottobre 2026"; etichetta "In corso" benché scaduto |
| `gal-srd14.html` | https://www.montagnappennino.it/bando/srd-14-investimenti-produttivi-non-agricoli-in-aree-rurali/ | "ore 13.00 del 8 maggio 2026" |
| `gal-vuota.html` | https://www.montagnappennino.it/bando/3450/ | pagina di bando vuota: etichette senza valori |

## Pagine d'ente inventate per Incentivi Italia

Pagine **inventate**, non scaricate: nessuna parte del file open data o dei
siti degli enti entra nel repository. Le usa `tests/test_incentivi.py`, con le
righe inventate di `tests/dati/incentivi_prova.csv`, per il controllo della
data di chiusura sulla pagina dell'ente (`src/estrazione/incentivi.py`).

| File | Perche' |
|---|---|
| `incentivi-con-data.html` | la data di chiusura del catalogo c'e' ("entro le ore 12:00 del 31/12/2026") |
| `incentivi-proroga.html` | c'e' un'altra data (proroga): la data del catalogo non si trova |
| `incentivi-sportello.html` | sportello senza parole di chiusura |
| `incentivi-sportello-chiuso.html` | sportello "chiuso per esaurimento delle risorse" |

## Link ai PDF della pagina di un bando (passo 19, compito 19a)

Le usa `tests/test_pdf_bando.py` per `src/estrazione/pdf_bando.py`: link ai
PDF, etichette e classi proposte. Usa anche le pagine vere del GAL
`gal-as01.html` e `gal-srd14.html` (sezione sopra): 20 link a PDF in
`gal-as01.html`, 16 file diversi, link senza testo, "Leggi" e "CLICCA QUI".

| File | Perche' |
|---|---|
| `pdf-regione-sintetica.html` | pagina **costruita a mano, non reale**, sul modello di una pagina di bando della Regione Toscana; indirizzi inventati. Link relativi e assoluti, `.PDF` maiuscolo, `.pdf/uuid?t=…`, un `.p7m`, un link a un altro host, un'ancora, un mailto e un `ftp://`. Le pagine vere si salvano nel compito 19b |

## Documenti delle pagine dei bandi della Regione (passo 19, compito 19b)

Estratti delle 8 pagine della Regione Toscana salvate il 19/11/2026 dalla
fase `--pagine` di `scripts/ingestione/elenco_pdf_bandi.py`: i soli `<a>`
verso documenti (`bancadati/atti/Contenuto.xml` su www301, `/documents/`,
`.pdf`, `.p7m`), nell'ordine della pagina, senza menu né contatti. Gli
estratti danno gli stessi link, con gli stessi testi, delle pagine intere.
Li usa `tests/test_documenti_regione.py`.

| File | Bando |
|---|---|
| `regione-documenti-parcheggi.html` | parcheggi-2026 |
| `regione-documenti-punti-digitale.html` | contributi-a-enti-locali-e-ets-per-punti-digitale-fac-8db4be |
| `regione-documenti-dati.html` | contributi-agli-enti-locali-per-lo-sviluppo-di-proget-01bfe9 |
| `regione-documenti-risorse-genetiche.html` | contributi-per-uso-e-gestione-sostenibile-delle-risor-9d883c |
| `regione-documenti-pmi-50mila.html` | bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-7057d9 |
| `regione-documenti-pmi-eu-blending.html` | bando-2026-pmi-sovvenzioni-per-abbattere-interessi-e-8cd3ac |
| `regione-documenti-apistici.html` | sostegno-agli-investimenti-strutturali-aziende-apisti-401650 |
| `regione-documenti-educazione-musicale.html` | sostegno-a-progetti-di-promozione-ed-educazione-music-e81761 |

Limite noto (19/11/2026): in `regione-documenti-risorse-genetiche.html` il
link "Disposizioni per la costituzione ed aggiornamento del Fascicolo
Aziendale ... Dichiarazione unica aziendale" (`allA_DA140_15.pdf`) prende la
classe modulistica per la parola "dichiarazione", ma e' una disposizione, non
un modulo. La regola resta com'e' (decisione del 19/11/2026): il file non si
scarica.
