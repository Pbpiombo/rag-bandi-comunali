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
