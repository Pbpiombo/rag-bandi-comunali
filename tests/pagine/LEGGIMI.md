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
