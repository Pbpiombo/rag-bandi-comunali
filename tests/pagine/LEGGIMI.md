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
