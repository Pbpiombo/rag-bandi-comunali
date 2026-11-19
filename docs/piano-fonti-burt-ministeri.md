Studio esterno da un modello, verificato a mano il 18/11/2026 sui punti indicati.

# Piano: BURT e fonti nazionali

Data: 18 novembre 2026. Studio, nessuna modifica al codice, nessuna
chiamata al modello del progetto, nessuna scrittura nell'archivio.
Risponde al punto 3 di "Priorità dopo il riscontro del consulente pilota
(18/11)" in `docs/roadmap.md` (oggi passi 11-16 dell'ordine, sezione C).

**Verifiche a mano del 18/11/2026**, che correggono il testo dello studio
dove indicato con "(verificato a mano il 18/11/2026)":

- la pagina <https://www.regione.toscana.it/burt/consultazione> dice
  "Aggiornato al: 18.11.2026": l'elenco non è in ritardo, il dubbio della
  sezione 1.1 è chiuso, e il BURT serve anche per i bandi aperti;
- robots.txt di `www.regione.toscana.it` letto il 18/11/2026: identico
  alle regole annotate il 12/11/2026 (`Disallow` su `*/search`,
  `*/ricerca`, `/combo/*`, `*/asset_publisher/`, login,
  `/tv-digitale-terrestre/*`); `/burt/consultazione` e `/documents/`
  permessi;
- robots.txt di `www.mit.gov.it` letto il 18/11/2026: nessun divieto su
  `/documentazione` né su `/index.php/documentazione`; il rifiuto della
  pagina dei contributi attivi veniva dallo strumento dello studio, non
  dal sito;
- robots.txt di `dait.interno.gov.it` letto il 18/11/2026: nessun divieto
  su `/finanza-locale/`; l'archivio delle notizie si apre.

## Come leggere questo documento

Tutte le pagine sono state consultate il 18/11/2026. Accanto a ogni
indirizzo c'è il modo in cui il dato è stato ottenuto:

- **[letta]**: pagina aperta e letta direttamente;
- **[estratto]**: testo della pagina ufficiale restituito dal motore di
  ricerca, pagina non aperta;
- **[archivio]**: dato preso dai file del repository (`bandi.csv`,
  `scansioni.csv`, i documenti in `docs/`), non riletto sul sito;
- **non verificato**: il dato viene da una fonte secondaria (stampa,
  portali di settore) o non è stato trovato sulla fonte ufficiale.

Limite dello strumento usato per lo studio: non ho potuto aprire nessun
`robots.txt` né le pagine il cui indirizzo non compariva già in un
risultato di ricerca. Dove dico "robots.txt non letto" va letto a mano
prima di qualunque scansione. Per il BURT, il MIT e la Finanza locale il
robots.txt è stato letto a mano il 18/11/2026 (vedi in testa); per le
altre fonti nazionali il limite resta.

## Sintesi

1. **Il BURT rende poco come fonte di bandi nuovi e abbastanza come
   fonte di controllo.** Su tre numeri consecutivi della Parte III
   (7, 14 e 21 ottobre 2026) ho contato 35 atti tra "Contributi e
   finanziamenti" e supplementi. Uno solo è un bando per i Comuni che il
   Portale della Regione non mostra (Festa della Toscana, Consiglio
   regionale, contributo massimo 3.000 euro, sei giorni di finestra).
   Il resto è già in archivio, oppure è una proroga o una modifica,
   oppure non riguarda il territorio. L'elenco di consultazione è
   aggiornato alla settimana corrente (verificato a mano il 18/11/2026):
   il BURT serve anche per trovare bandi aperti, non solo per il
   controllo a posteriori.
2. **Il sospetto su Incentivi Italia è confermato dai dati del
   repository.** Le 197 righe del catalogo passate dalla scansione non
   contengono nessun avviso del Ministero dell'Interno, dell'Istruzione,
   del Dipartimento disabilità, di Sport e Salute. Dei 10 bandi nazionali
   mancanti della sezione 8.4 di `ricognizione-fonti.md` ne compaiono 2,
   entrambi per imprese, entrambi finiti tra le righe da verificare.
3. **Le fonti nazionali utili ai Comuni sono poche e ognuna pubblica
   pochi avvisi l'anno.** Le tre da considerare: Ministero
   dell'Interno (Finanza locale), MIT (già in `fonti.csv`, elenco
   spento), Dipartimento per lo Sport con Sport e Salute. Il Dipartimento
   Affari regionali, che sembrava il candidato naturale per la montagna,
   non ha pubblicato negli ultimi 12 mesi nessun avviso a cui un Comune
   possa fare domanda direttamente.
4. **Ordine consigliato:** accendere l'elenco del MIT; BURT Parte III
   leggendo solo il sommario; Finanza locale; Sport. Prima di tutto,
   però, la scansione settimanale del Portale della Regione: recupera
   più del BURT e costa meno.

---

## 1. BURT

### 1.1 Come pubblica

| cosa | dato | fonte |
|---|---|---|
| Base normativa | legge regionale 23/2007 | <https://www.regione.toscana.it/burt/che-cos-e> [letta] |
| Formato | solo edizione telematica dal gennaio 2008 | stessa pagina [letta] |
| Frequenza | di norma il mercoledì, più numeri straordinari | frontespizio della Parte III n. 42, <https://www.regione.toscana.it/documents/d/guest/parte-iii-n-42-del-21-10-2026> [letta] |
| Parti | quattro, non tre | <https://www.regione.toscana.it/burt/cosa-contiene> [letta], aggiornata il 29/11/2024 |
| Supplementi | abbinati al numero ordinario, per atti voluminosi | stessa pagina [letta] |

Le quattro parti, dalla pagina "Cosa contiene":

- **Parte I**: leggi, regolamenti, atti di programmazione.
- **Parte II**: atti della Regione e degli enti locali la cui
  pubblicazione è prevista da norme.
- **Parte III**: bandi e avvisi di concorso, borse di studio, incarichi,
  contributi, sovvenzioni e benefici economici della Regione, degli enti
  locali e di altri enti pubblici; anche i bandi di gara.
- **Parte IV**: atti gestionali con dati personali e graduatorie.
  **Da non leggere**: contiene dati personali, e il progetto non ne
  vuole nei file.

**Elenco consultabile.** La pagina
<https://www.regione.toscana.it/burt/consultazione> [letta] è un elenco
HTML, raggruppato per "Edizione del [data]", con un link per ogni parte e
per ogni supplemento. È lunga (circa 308.000 caratteri, centinaia di
link). I link puntano a file sotto `/documents/d/guest/`, per esempio:

- `parte-iii-n-42-del-21-10-2026`
- `parte-iii-n-40-del-07-10-2026_compressed`
- `parte-iii-n-40-bis-del-08-10-2026`
- `supp-n-241-al-bu-del-21-10-2026-piii`

Gli indirizzi non sono regolari (suffissi `_compressed`, `-1`, `bis`):
non si possono costruire, vanno letti dall'elenco.

**Ritmo osservato**, dall'elenco, tra il 2 e il 26 ottobre 2026: tre
numeri ordinari della Parte III (40, 41, 42), un "40 bis" con un solo
concorso, cinque supplementi alla Parte III (232, 233, 236, 241, 242).
Quindi circa 3 file a settimana solo per la Parte III.

**Dimensione dei file** (caratteri di testo estratto, misurati sulla
lettura): n. 42, circa 374.000, sommario fino a pagina 141; n. 41, circa
433.000, fino a pagina 154; n. 40, circa 872.000, fino a pagina 291;
supplemento 241, circa 422.000.

**Testo.** I quattro file aperti hanno testo estraibile, senza OCR. Nel
n. 40 (il file `_compressed`) l'estrazione ha difetti: parole attaccate,
intestazioni spezzate. Gli allegati secondari dei decreti (moduli,
dichiarazioni) compaiono solo come codici di controllo, non come testo;
l'allegato principale con il bando c'è per intero (supplemento 241,
bando da pagina 10).

**PDF firmati .p7m**: nessuno dei quattro file aperti lo era. Non ho
stabilito se il PDF abbia una firma interna.

**Feed RSS, open data, API**: nessun riferimento nelle pagine lette
(che-cos-e, cosa-contiene, consultazione, spazio-inserzionisti). Non
verificato oltre.

**Ricerca.** La pagina <https://www.regione.toscana.it/burt/ricerca>
non è leggibile: il mio strumento l'ha rifiutata per divieto di
robots.txt. È coerente con la regola `Disallow` su `*/ricerca` annotata
in `docs/piano-fonti.md`, sezione 0 (12/11/2026) [archivio], e confermata
dal robots.txt letto a mano il 18/11/2026. **La ricerca del BURT non si
può usare in automatico.**

**Banca dati.** I vecchi indirizzi
`www.regione.toscana.it/bancadati/BURT/Contenuto.xml?id=N` reindirizzano
a `www301.regione.toscana.it/bancadati/BURTRT/?id=N` [letta], che è
un'applicazione: la pagina restituita contiene menu e avvisi, non l'atto.
robots.txt di `www301` non letto. Da non usare.

Aggiornamento del 19/11/2026 (decisione del progetto, passo 19): le
pagine dei bandi della Regione collegano gli atti come
`www301.regione.toscana.it/bancadati/atti/Contenuto.xml?id=N&nomeFile=…`
(decreto e allegati, tra cui l'avviso). `www301` si usa solo dopo averne
letto il robots.txt: lo script `scripts/ingestione/elenco_pdf_bandi.py`
lo legge, con il lettore `src/estrazione/lettore_siti.py`, prima del
primo file chiesto a quell'host, e si ferma se non si legge.

19/11/2026: `www301.regione.toscana.it` non ha un robots.txt (verificato
il 19/11/2026): `/robots.txt` risponde 200 con una pagina HTML "La pagina
che hai richiesto non esiste..". Il lettore la registra come "assente
(pagina HTML al posto del robots.txt)" e vale come robots.txt assente:
nessuna regola, pausa di 5 secondi tra le richieste.

**robots.txt di www.regione.toscana.it**: letto a mano il 18/11/2026,
identico alle regole annotate il 12/11/2026 in `piano-fonti.md`:
`Disallow` su `*/search`, `*/ricerca`, `/combo/*`, `*/asset_publisher/`,
login, `/tv-digitale-terrestre/*`. `/burt/consultazione` e `/documents/`
sono permessi.

**Aggiornamento dell'elenco: dubbio chiuso** (verificato a mano il
18/11/2026). Durante lo studio la prima voce dell'elenco di consultazione
risultava l'edizione del 26 ottobre 2026, mentre `ricognizione-fonti.md`
(8.2) riporta un avviso pubblicato sul BURT l'11/11/2026. La pagina,
aperta a mano il 18/11/2026, dice "Aggiornato al: 18.11.2026": l'elenco
non è in ritardo, e la copia vecchia veniva dallo strumento dello studio.
Il BURT serve quindi anche per trovare bandi aperti, non solo per il
controllo a posteriori.

### 1.2 Quanto passa dal BURT senza comparire sul Portale

Campione: i tre numeri ordinari della Parte III del 7, 14 e 21 ottobre
2026 e i loro supplementi. Ho letto i sommari, e il testo solo dove
indicato. Confronto con `bandi.csv` e `scansioni.csv` del repository.

Il sommario della Parte III è diviso in sezioni fisse: Supplementi,
Concorsi, Contributi e finanziamenti, Incarichi, Borse di studio, Avvisi
di gara, Altri avvisi. Interessano solo "Contributi e finanziamenti" e
"Supplementi".

| numero | atti in "Contributi e finanziamenti" | atti nei supplementi | totale |
|---|---|---|---|
| n. 40 del 07/10 | 9 | 2 | 11 |
| n. 41 del 14/10 | 14 | 2 | 16 |
| n. 42 del 21/10 | 3 | 5 | 8 |
| **totale** | **26** | **9** | **35** |

Cosa sono i 35 atti:

**Già in archivio (10 atti).** Operatori forestali (decreto 22694),
progettualità sui dati (22706), Assegno formazione GOL (modifica, 22705),
alta formazione e ricerca-azione (modifica, 21570), risorse genetiche
agrarie (proroga, 21441), incentivi ARTI ai datori di lavoro privati (tre
atti di proroga e rettifica), i due bandi neve (22460 e 22552). I due bandi neve però sono
in archivio da Sviluppo Toscana, non dal Portale: il BURT li avrebbe
trovati comunque (supplemento 241).

**Bandi nuovi per il territorio, non in archivio (4 casi, 13 atti).**

1. **Festa della Toscana 2026**, Consiglio regionale, decreto 915 del
   7/10/2026. Parte III n. 42, da pagina 39. Possono fare domanda gli enti
   locali, oltre a università, scuole ed enti del terzo settore (pagina
   50). Scadenza alle 15:00 del 27/10/2026 (pagina 51). Contributo fino
   all'80% delle spese e comunque non oltre 3.000 euro (pagina 55).
   Stanziamento 255.000 euro (pagina 42). Il bando rimanda al sito del
   Consiglio regionale, sezione "Avvisi, bandi e gare" [letta, nel testo
   del BURT]. In `scansioni.csv` non c'è nessun indirizzo che lo riguardi
   [archivio]: indizio che non sia sul Portale della Giunta, ma **non
   verificato** sul Portale. È l'unico bando per i Comuni del campione che
   il BURT aggiunge.
2. **Pro Loco, identità locali 2026**, decreto 22288 del 7/10/2026. Parte
   III n. 41, pagina 41. È sul Portale, ma si è aperto e chiuso tra due
   scansioni (`ricognizione-fonti.md`, 8.2). Qui il BURT fa da rete di
   sicurezza.
3. **ARTI, Fondo regionale per l'occupazione delle persone con
   disabilità** (legge 68/99): dieci avvisi per datori di lavoro privati,
   Parte III n. 41, pagine 78-87. Due sono del settore di Pisa e Massa
   Carrara; per gli altri otto il sommario non dice il territorio. Non ho
   stabilito se uno riguarda Pistoia. Le pagine di `arti.toscana.it` su
   questo fondo sono in `scansioni.csv` come righe da verificare del
   catalogo Incentivi Italia [archivio].
4. **Animazione per reti di welfare territoriale 2026-2027**, decreto
   21180 del 22/09/2026, supplemento 232. Beneficiari non letti.

**Modifiche di bandi non in archivio (5 atti).** SRG10 (incremento di
dotazione), SRA30 benessere animale (modifica), valorizzazione
dell'immagine della Toscana (integrazione di risorse), due atti ARTEA sui
vigneti.

**Fuori dal territorio o dal perimetro (7 atti).** Pesca e acquacoltura
(FEAMPA e i due bandi del GAL Pesca), servizio civile (due avvisi per i
giovani), due premi del CORECOM.

**Lettura.** In tre settimane il BURT aggiunge al Portale un solo bando
per i Comuni, piccolo e con una finestra di sei giorni: con una scansione
settimanale l'app lo mostrerebbe aperto per pochi giorni o mai. Il valore
vero è altrove:

- **emittenti che il Portale non copre**: Consiglio regionale, ARTI,
  ARTEA, GAL. La proroga dell'AS01 del GAL MontagnAppennino era nel BURT
  n. 37 del 16/09/2026 [archivio];
- **proroghe e modifiche con la data**: nel campione 12 atti su 35
  modificano un bando esistente (proroghe, nuovi termini, rettifiche,
  risorse);
- **data di pubblicazione**: serve per i termini "entro N giorni dalla
  pubblicazione sul BURT", come l'avviso del decreto 9550 del 28/04/2026
  in coda nella roadmap;
- **controllo di copertura** della fonte regionale (roadmap, punto 4).

**Stima annua, debole.** Tre settimane di un solo mese non bastano per
una stima seria. Come ordine di grandezza: 10-20 bandi utili l'anno che
il Portale non mostra o che la scansione perde, quasi tutti piccoli o di
emittenti minori. Va rimisurata su due o tre mesi.

**Alternativa più economica per lo stesso risultato.** La scansione
settimanale del Portale recupera i bandi aperti e chiusi tra due
scansioni (9 dei 12 regionali mancanti nella misura del 13/11). La pagina
"Avvisi, bandi e gare" del Consiglio regionale coprirebbe l'unico caso
nuovo del campione; non l'ho studiata.

### 1.3 Come filtrare senza leggere tutto

1. Leggere solo l'elenco di consultazione e prendere i link nuovi di
   Parte III e supplementi `piii`. Mai Parte I, II e IV.
2. Di ogni file, leggere solo il sommario: sta nelle prime 5-7 pagine.
3. Tenere solo le sezioni "Contributi e finanziamenti" e "Supplementi".
   Nel campione sono 35 atti su circa 70 voci totali.
4. Scartare per emittente e parole dell'oggetto: FEAMPA, pesca, servizio
   civile, CORECOM, sanità.
5. Confrontare numero e data dell'atto con `riferimento_atto` di
   `bandi.csv`: i decreti della Giunta hanno la stessa numerazione sul
   BURT, sul Portale e su Sviluppo Toscana (22460, 22552, 22694, 22706
   combaciano). La chiave deve includere l'emittente: ARTI, ARTEA e
   Consiglio regionale hanno numerazioni proprie (ARTI 1160, Consiglio
   915).
6. Solo per gli atti rimasti, leggere le pagine dell'atto.

Un filtro per "montagna" o "aree interne" sul sommario non funziona: gli
oggetti non lo dicono quasi mai. Il filtro realistico è per sezione, per
emittente e per esclusione.

### 1.4 Rischi

- **Doppioni.** Quasi tutti i bandi della Giunta stanno anche sul
  Portale, e alcuni su Sviluppo Toscana. Senza il confronto sul numero
  d'atto il BURT triplica le righe. Serve `doppioni.csv`, come già
  previsto in roadmap.
- **Solo PDF.** Nessuna versione HTML degli atti. La lettura dei PDF
  (roadmap, "Prossimi passi", voce 6) è un prerequisito per usare il BURT
  come fonte di dati. Per usarlo come fonte di scoperta basta il
  sommario.
- **Qualità dell'estrazione.** Nel file `_compressed` il testo ha parole
  attaccate: un verificatore che cerca la frase esatta può fallire.
- **OCR.** Non necessario nei quattro file aperti. Non verificato per gli
  avvisi inseriti da enti locali e per gli anni precedenti.
- **Volume.** Un bando occupa decine di pagine: Festa della Toscana va da
  pagina 39 a pagina 67. A circa 2.600 caratteri per pagina sono circa
  75.000 caratteri per un contributo da 3.000 euro. Il costo per bando
  utile è alto.
- **Atti che non sono bandi.** Proroghe, rettifiche, incrementi di
  dotazione: vanno agganciati al bando esistente, non salvati come bandi.
- **Ritardo dell'elenco: escluso** (verificato a mano il 18/11/2026,
  "Aggiornato al: 18.11.2026"). Resta il rischio opposto: con una lettura
  settimanale, un bando con una finestra di pochi giorni può aprirsi e
  chiudersi tra due letture, come Festa della Toscana.

---

## 2. Ministeri e fonti nazionali

### 2.1 Confronto con Incentivi Italia

Dal repository, senza rileggere il file open data.

- I 54 bandi salvati da Incentivi Italia hanno solo tipi di beneficiario
  privati; nessuna riga di tipo pubblico. Le 9 pagine "per enti pubblici"
  lette con il modello non hanno prodotto nessun bando per i Comuni
  (`piano-fonti.md`, "Resa reale") [archivio].
- Domini delle 197 righe del catalogo in `scansioni.csv` [archivio]:
  mimit.gov.it 35, cinema.cultura.gov.it 18, regione.toscana.it 23 (15
  più 8 su www301),
  simest.it 10, mit.gov.it 7, arti.toscana.it 6, ptpo.camcom.it 6,
  sviluppo.toscana.it 6, gse.it 5.
- Le 7 righe del MIT sono tutte per imprese di trasporto (autotrasporto,
  ferrobonus, marebonus, rinnovo del parco veicolare). Il fondo strade per
  i piccoli Comuni non c'è.
- Zero righe da dait.interno.gov.it, dai siti dell'Istruzione, dal
  Dipartimento disabilità, da sportesalute.eu. Una sola da
  sport.governo.it (credito d'imposta per le sponsorizzazioni). Due da
  affariregionali.it, entrambe con pagina non trovata (404).

**Conclusione.** Il catalogo copre gli incentivi alle imprese dei
ministeri economici, il cinema, la CCIAA. Non copre gli avvisi rivolti ai
Comuni. Limite: vedo solo le righe passate dal filtro del progetto (197
su 6.095), non il file intero.

### 2.2 I casi di prova della sezione 8.4

| bando | fonte ufficiale | stato al 18/11/2026 | in Incentivi Italia |
|---|---|---|---|
| Fondo investimenti stradali nei piccoli Comuni 2026 (MIT) | <https://www.mit.gov.it/comunicazione/news/fondo-piccoli-comuni-online-lavviso-pubblico-2026> [estratto]; avviso prot. 26286 del 03/11/2026 in PDF sullo stesso sito | aperto fino alle 12:00 del 30/11/2026; già in archivio | no |
| Arredi didattici innovativi per nidi e scuole dell'infanzia (Istruzione) | avviso del 03/02/2026; quello per il Mezzogiorno è su <https://pn20212027.istruzione.it/wp-content/uploads/2026/02/m_pi.AOOGABMI.REGISTRO-UFFICIALEU.0022870.03-02-2026.pdf> [estratto]. L'avviso gemello per il centro-nord, Toscana compresa: indirizzo ufficiale **non verificato**. Graduatorie su <https://pnrr.istruzione.it/news> [letta], voce del 07/04/2026 | scaduto il 03/03/2026 | no |
| Promozione della musica jazz 2027 (Cultura) | <https://cultura.gov.it/comunicato/bando-per-la-promozione-della-musica-jazz-anno-2027-avviso-pubblico-e-apertura-dei-termini-di-presentazione-delle-domande> [estratto]; D.D.G. 14/07/2026 rep. 1285 su spettacolo.cultura.gov.it | chiuso: contributi assegnati con decreto del 27/10/2026 [estratto]. Scadenza non letta | no |
| Nuova Sabatini (MIMIT) | <https://www.mimit.gov.it/index.php/it/incentivi/agevolazioni-per-gli-investimenti-delle-pmi-in-beni-strumentali-nuova-sabatini> [archivio] | sportello | sì, riga da verificare |
| Bando ISI (INAIL) | <https://www.inail.it/portale/prevenzione-e-sicurezza/it/prevenzione-e-sicurezza/finanziamenti-per-la-sicurezza/incentivi-alle-imprese/bando-isi-2025.html> [archivio] | non letto | sì, riga da verificare |
| Parco Agrisolare (MASAF con GSE) | avviso MASAF del febbraio 2026, domande sul portale del GSE dal 10/03 al 09/04/2026: **non verificato**, solo fonti secondarie | scaduto | no |
| Vita & Opportunità (Presidenza del Consiglio, disabilità) | avviso del 14/02/2026: <https://ministrodisabilita.gov.it/media/gdvbd5om/avviso-vita-e-opportunità_14022026.pdf> [estratto]. Sportello non competitivo, reti con capofila un ente del terzo settore | date dello sportello (02/03-29/08/2026): **non verificato** | no |
| Fabbrica, spazi civici per la gioventù (Sport e Salute) | <https://www.sportesalute.eu/fabbrica.html> [estratto]; elenco <https://www.sportesalute.eu/bandi-e-avvisi.html> [estratto] | aperto dal 04/11 al 18/12/2026 ore 12:00. Attenzione: la piattaforma `bandi.sportesalute.eu` mostra accanto al titolo "chiude il 28 novembre 2026", da chiarire | no |
| Zenit (Fondo per la Repubblica Digitale) | sito ufficiale del Fondo non trovato nelle ricerche: **non verificato** | scaduto il 18/09/2026 secondo la stampa | no |
| Formazione IA (Fondimpresa) | **non stabilito** | | no |

Otto casi su dieci stanno su siti che non sono fonti e non sono nel
catalogo. Solo tre riguardano i Comuni, come già scritto in roadmap:
strade, arredi, jazz. A questi si aggiunge Vita & Opportunità, dove il
Comune entra come partner.

### 2.3 I candidati

#### A. Ministero dell'Interno, Finanza locale

- **Dove pubblica.** Archivio delle notizie:
  <https://dait.interno.gov.it/finanza-locale/notizie> [estratto]. Ogni
  comunicato ha una pagina HTML datata
  (`/finanza-locale/notizie/comunicato-del-GG-mese-AAAA`) che rimanda al
  decreto in PDF (`/finanza-locale/documentazione/decreto-…`).
- **Esempi degli ultimi 16 mesi** [estratto]:
  - comunicato del 21/07/2025: istanza dei Comuni per le opere di messa
    in sicurezza di edifici e territorio, annualità 2026-2028
    (<https://dait.interno.gov.it/finanza-locale/notizie/comunicato-del-21-luglio-2025>);
  - comunicato del 21/11/2025: istanza per il contributo alla spesa di
    progettazione, annualità 2026
    (<https://dait.interno.gov.it/finanza-locale/notizie/comunicato-del-21-novembre-2025>);
  - comunicato del 26/03/2026: certificazione per il contributo ai Comuni
    con spese da sentenze di risarcimento per calamità o cedimenti
    (<https://dait.interno.gov.it/finanza-locale/notizie/comunicato-del-26-marzo-2026>);
  - contributo 2026 alle unioni di comuni e comunità montane per i
    servizi associati: comunicato in Gazzetta Ufficiale del 29/01/2026
    (<https://www.gazzettaufficiale.it/eli/id/2026/01/29/26A00351>), e
    comunicato del 22/10/2026 sulla quantificazione. **Riguarda
    direttamente l'Unione.**
- **Formato.** Comunicato HTML breve, decreto e modello in PDF.
- **Frequenza.** Più comunicati a settimana, ma quasi tutti sono riparti
  e pagamenti senza domanda. Quelli con istanza o certificazione: 3-5
  l'anno, stima dagli esempi sopra.
- **robots.txt**: letto a mano il 18/11/2026, nessun divieto su
  `/finanza-locale/`. L'archivio delle notizie si apre: l'errore avuto
  durante lo studio veniva dallo strumento dello studio.
- **Feed, open data**: non stabilito.
- **Critica.** Non sono bandi in senso stretto: sono istanze annuali che
  il ragioniere di ogni Comune conosce già, con modelli e piattaforma
  propri (TBEL). Il valore per l'app è ricordare le scadenze, non far
  scoprire qualcosa. Va chiesto al consulente se le considera nel suo
  lavoro.

#### B. Ministero delle Infrastrutture e dei Trasporti

- Già in `fonti.csv` (`ministero-infrastrutture`), elenco News spento.
- **Esempi** [estratto]: fondo strade piccoli Comuni (03/11/2026); fondo
  idrico, bando per investimenti infrastrutturali (30/04/2026,
  <https://www.mit.gov.it/comunicazione/news/fondo-idrico-apre-il-bando-per-nuovi-investimenti-infrastrutturali>,
  rivolto ai soggetti proponenti del settore idrico); avviso per
  l'elenco di enti e associazioni per l'educazione stradale (domande
  entro il 16/11/2026, dalla home del sito).
- **Elenco.** La sezione News è generale: tra le notizie del ministro e
  gli avvisi il rumore è alto. Esiste una pagina più adatta, "Bonus e
  finanziamenti a cittadini, enti locali ed imprese", con la sezione dei
  contributi attivi
  (<https://mit.gov.it/index.php/documentazione/bonus-e-finanziamenti-cittadini-enti-locali-ed-imprese>)
  [estratto]. Durante lo studio lo strumento l'ha rifiutata; il rifiuto
  veniva dallo strumento, non dal sito (verificato a mano il 18/11/2026).
- **robots.txt**: letto a mano il 18/11/2026 su `www.mit.gov.it`, nessun
  divieto su `/documentazione` né su `/index.php/documentazione`.
  `fonti.csv` lo dava per controllato il 13/11/2026 [archivio], senza le
  righe annotate.
- **Frequenza per i Comuni**: 1-3 avvisi l'anno, stima.

#### C. Dipartimento per lo Sport (Presidenza del Consiglio) e Sport e Salute

- **Dove pubblica.** Piattaforma <https://avvisibandi.sport.governo.it/en-US>
  [letta]: elenco HTML con stato (aperto, chiuso), data di chiusura e
  destinatari (Enti, Cittadini). Nove voci visibili, altre dietro "Vedi
  altri". Le schede hanno apertura, scadenza e destinatari
  (<https://avvisibandi.sport.governo.it/bandi/699d5d516166f9f16884719b>
  [estratto]). Notizie su `www.sport.governo.it/it/bandi-e-avvisi/…`.
- **Difetto dell'elenco**: quasi tutte le voci puntano allo stesso PDF,
  probabilmente per un errore della pagina. I link vanno presi dalle
  schede.
- **Esempi per i Comuni:**
  - Sport e Periferie 2026, 100 milioni, domande dal 04/06 al 25/06/2026.
    L'avviso
    (<https://www.sport.governo.it/media/o1nffgnf/avviso-sport-e-periferie-2026.pdf>
    [letta]) ammette i Comuni sopra i 5.000 abitanti; quelli sotto solo
    con un accordo con enti locali confinanti che raggiunga la soglia
    (art. 3). **Abetone Cutigliano, con 1.834 abitanti, da solo è
    escluso.** La notizia sul sito dice invece che l'avviso è rivolto a
    tutti i Comuni italiani: la pagina HTML non basta, serve il PDF;
  - eventi sportivi di rilevanza nazionale e internazionale 2026, Comuni
    tra i destinatari, aperto fino al 01/12/2026
    (<https://avvisibandi.sport.governo.it/bandi/69f9e0e94ea041522d70640b>
    [estratto]).
- **Per il terzo settore sportivo**: oratori, impianti natatori; su Sport
  e Salute "Fabbrica" e "Lo sport è vita".
- **robots.txt** di sport.governo.it, avvisibandi.sport.governo.it e
  sportesalute.eu: non letti.
- **Frequenza**: 1-2 avvisi l'anno per i Comuni, 4-6 per associazioni
  sportive ed enti del terzo settore.

#### D. Scartati o da rimandare

- **Dipartimento per gli Affari regionali e le Autonomie.** Il FOSMIT
  viene ripartito alle Regioni; la pagina del fondo
  (<https://www.affariregionali.it/it/aree-tematiche/montagna/fondi-montagna/fondo-per-lo-sviluppo-delle-montagne-italiane/fondo-per-lo-sviluppo-delle-montagne-italiane/>
  [letta]) non mostra, negli ultimi 12 mesi, nessun avviso a cui un
  Comune possa fare domanda al Dipartimento. L'ultima voce è un decreto
  del 06/08/2026 sui termini di conclusione degli interventi. Gli avvisi
  per imprese collegati dal menu risalgono al 2023. **Rende zero oggi.**
  Conferma la nota di `ricognizione-fonti.md` (3.1): il FOSMIT arriva
  dalla Regione.
- **Ministero della Cultura.** L'elenco degli avvisi
  (<https://cultura.gov.it/categorie/comunicati/avvisi?slug=avvisi&page=262>
  [letta]) ha 4.009 voci in 268 pagine, 15 per pagina, e mescola bandi di
  contributo, gare, concorsi, mobilità del personale. Tra le 15 voci
  lette, 3 riguardano bandi di contributo. Rumore troppo alto per il volume
  utile. Se serve, il sito della Direzione generale Spettacolo è più
  mirato: non studiato.
- **Ministero dell'Istruzione.** <https://pnrr.istruzione.it/news>
  [letta]: 12 voci per pagina, 11 pagine. Tra aprile e novembre 2026 una
  sola voce è un avviso per gli enti locali (01/06/2026, esigenze urgenti
  per completare interventi di edilizia scolastica). Gli avvisi per i
  Comuni presuppongono un intervento PNRR già finanziato. Volume: 2-3
  l'anno, tutti condizionati.
- **Ministero del Turismo.** Candidato per le imprese della montagna:
  ristori per gli impianti nei comuni appenninici (avviso del
  30/05/2025), misura "Montagna Italia", fondo per le imprese del turismo
  2026. **Tutto non verificato** sul sito del ministero: ho solo fonti
  secondarie e decreti che citano l'avviso. Da studiare se il consulente
  conferma l'interesse.
- **Dipartimento disabilità, Fondo per la Repubblica Digitale,
  Fondimpresa.** Avvisi occasionali per il terzo settore o per imprese,
  non per i Comuni. Non giustificano una fonte.

#### E. Piattaforme nazionali

- **PA digitale 2026**: una sola riga in `scansioni.csv`, con robots.txt
  che vieta la pagina [archivio]. Non studiata oltre.
- **Gazzetta Ufficiale**: i comunicati del Ministero dell'Interno escono
  anche lì, con indirizzi stabili (`/eli/id/AAAA/MM/GG/codice`). Potrebbe
  essere una fonte di scoperta per tutti i ministeri. Non studiata.
- Una piattaforma unica degli avvisi dello Stato agli enti locali: **non
  l'ho trovata**.

---

## 3. Confronto e raccomandazione

### 3.1 Tabella

Volumi: stime deboli, dagli esempi raccolti. "Sovrapposizione" è rispetto
alle sei fonti attuali.

| fonte | cosa pubblica | formato | frequenza | robots.txt | feed, open data | sovrapposizione | bandi utili l'anno | difficoltà | motivo |
|---|---|---|---|---|---|---|---|---|---|
| BURT Parte III, solo sommario | tutti i bandi e avvisi di Regione, Consiglio, agenzie, enti locali | elenco HTML, atti in PDF | settimanale, circa 3 file | letto il 18/11/2026: elenco e `/documents/` permessi; ricerca vietata | nessuno trovato | molto alta con il Portale | 10-20 non visti altrimenti | media | il sommario è regolare; gli indirizzi dei file no |
| BURT Parte III, testo dei bandi | come sopra | PDF da 140 a 290 pagine | come sopra | come sopra | nessuno trovato | molto alta | gli stessi | alta | decine di pagine per bando, estrazione a tratti difettosa |
| Interno, Finanza locale | istanze e certificazioni per contributi statali a Comuni e Unioni | comunicato HTML, decreto PDF | 3-5 istanze l'anno tra molti riparti | letto il 18/11/2026: nessun divieto su `/finanza-locale/`; archivio leggibile | non stabilito | nessuna | 3-5 | media | comunicati brevi e datati, ma quasi tutti riparti senza domanda |
| MIT | avvisi per Comuni, imprese di trasporto, cittadini | notizia HTML, avviso PDF | 1-3 l'anno per i Comuni | letto il 18/11/2026: nessun divieto su `/documentazione` | non stabilito | già fonte, elenco spento | 1-3 | bassa | la notizia HTML contiene già beneficiari, importi e date |
| Dipartimento per lo Sport | avvisi per Comuni e associazioni sportive | elenco HTML con stato e date, avviso PDF | 5-8 l'anno in tutto | non letto | non stabilito | quasi nessuna | 1-2 Comuni, 4-6 terzo settore | bassa per l'elenco, media per l'avviso | le soglie di popolazione stanno solo nel PDF |
| Sport e Salute | avvisi per associazioni sportive ed enti del terzo settore | elenco HTML, avviso PDF | 3-5 l'anno | non letto | non stabilito | nessuna | 3-5, nessuno per i Comuni | bassa | elenco con apertura e chiusura in chiaro |
| Istruzione (PNRR e PN Scuola) | avvisi per scuole, pochi per enti locali | elenco HTML, avviso PDF | 2-3 l'anno per enti locali | non letto | nessuno nella pagina | nessuna | 0-2 | media | avvisi riservati a chi ha già un intervento PNRR |
| Cultura, elenco avvisi | bandi, gare, concorsi insieme | elenco HTML di 268 pagine, avviso PDF | decine di voci al mese | non letto | nessuno nella pagina | parziale (cinema) | 1-3 | alta | rumore: 3 bandi su 15 voci |
| Affari regionali | decreti di riparto del FOSMIT | HTML, decreti PDF | 1-2 voci l'anno | non letto | non stabilito | il FOSMIT arriva dalla Regione | 0 | n.d. | nessun avviso per i Comuni in 12 mesi |
| Turismo | avvisi per imprese turistiche e impianti | non verificato | non verificato | non letto | non stabilito | 2 righe del catalogo, inutili | non stabilito | non stabilita | da studiare |

### 3.2 Ordine consigliato

**0. Prima delle fonti nuove: scansione settimanale del Portale della
Regione.** Nella misura del 13/11 mancavano 12 bandi regionali su 18, e 9
per la frequenza delle scansioni. Nessuna fonte di questo studio recupera
altrettanto. È il punto 6 delle priorità in roadmap: lo metterei prima.

**1. MIT: accendere l'elenco.** La fonte c'è già, il caso di prova (fondo
strade) è in archivio, la notizia HTML porta i dati essenziali. Resta da
scegliere la pagina elenco: News è rumorosa, la pagina dei contributi
attivi è quella giusta, e il robots.txt non la vieta (letto a mano il
18/11/2026). Costo basso, 1-3 bandi l'anno.

**2. BURT Parte III, solo sommario, come fonte di scoperta e di
controllo.** Non come fonte di estrazione. Motivi: l'ha chiesto il
consulente; serve alla misura di copertura; dà proroghe e date di
pubblicazione; trova anche bandi aperti, perché l'elenco è aggiornato
alla settimana corrente; sta su un dominio di cui le regole sono note e
riverificate il 18/11/2026. Per ogni atto nuovo, il dato si prende dalla
pagina dell'ente, se esiste; solo se non esiste si leggono le pagine del
BURT, che è comunque la pubblicazione ufficiale e si può citare con
numero, data e pagina. Il dubbio sul ritardo dell'elenco è chiuso
(verificato a mano il 18/11/2026): la lettura va fatta ogni mercoledì.

**3. Interno, Finanza locale.** È l'unico canale dei contributi statali
ai Comuni e all'Unione, e non è coperto da niente. L'accesso è verificato
(robots.txt e archivio delle notizie, 18/11/2026). Lo metto terzo e non
primo perché il consulente potrebbe dire che quelle istanze le segue già
la ragioneria.

**4. Dipartimento per lo Sport, poi Sport e Salute.** Elenchi puliti, ma
pochi avvisi, e il principale del 2026 esclude da solo un Comune di 1.834
abitanti. Utile soprattutto per il terzo settore sportivo.

**Da non aggiungere ora:** Affari regionali, elenco generale della
Cultura, Istruzione, fondi privati. **Da studiare solo se il consulente
lo chiede:** Turismo.

Con la regola di chiusura della ricognizione (una fonte entra se in 12
mesi ha pubblicato almeno un bando applicabile non presente altrove):
MIT, BURT, Finanza locale e Sport la superano; Affari regionali no.

### 3.3 Lista di controllo per la prima fonte nuova: BURT Parte III

Il MIT è già una fonte; la prima nuova è il BURT.

**robots.txt.** Dominio `www.regione.toscana.it`, letto a mano il
18/11/2026: identico alle regole annotate il 12/11/2026, `Disallow` su
`*/search`, `*/ricerca`, `/combo/*`, `*/asset_publisher/`, login,
`/tv-digitale-terrestre/*`. Conseguenze: `/burt/consultazione` e
`/documents/` permessi; `/burt/ricerca` vietata;
`www301.regione.toscana.it` da non usare finché non se ne legge il
robots.txt. **Da fare:** annotare la data del 18/11/2026 nella riga di
`fonti.csv`, quando la fonte entra. (19/11/2026: il robots.txt di
`www301` lo legge lo script dei PDF degli avvisi prima del primo file;
vedi "Banca dati" sopra.)

**Elenco leggibile.** <https://www.regione.toscana.it/burt/consultazione>:
HTML, un link per file, senza paginazione. Regola per i link: tenere
quelli che contengono `parte-iii-` oppure finiscono in `-piii`. Elenco
aggiornato alla settimana corrente ("Aggiornato al: 18.11.2026",
verificato a mano).

**Tre bandi d'esempio.**

| bando | dove | cosa serve per leggerlo |
|---|---|---|
| Festa della Toscana 2026 (Consiglio regionale, decreto 915 del 07/10/2026) | <https://www.regione.toscana.it/documents/d/guest/parte-iii-n-42-del-21-10-2026>, pagine 39-67 | PDF, testo estraibile. Beneficiari a pagina 50, scadenza a pagina 51, importo a pagina 55. Non in archivio |
| Pro Loco, identità locali 2026 (decreto 22288 del 07/10/2026) | <https://www.regione.toscana.it/documents/d/guest/parte-iii-n-41-del-14-10-2026>, da pagina 41 | PDF. Esiste anche la pagina HTML sul Portale: i dati vanno presi da lì. Serve a provare il recupero di un bando perso tra due scansioni |
| Bando neve, spese di funzionamento 2026 (decreto 22460 del 10/10/2026) | <https://www.regione.toscana.it/documents/d/guest/supp-n-241-al-bu-del-21-10-2026-piii>, decreto a pagina 4, bando da pagina 10, termini a pagina 22 | PDF. Già in archivio da Sviluppo Toscana: serve a provare il riconoscimento del doppione sul numero d'atto |

**Cosa serve nel codice, in sintesi.** Lettura del PDF limitata a un
intervallo di pagine; riconoscimento del sommario e delle sue sezioni;
confronto di numero, data ed emittente dell'atto con `bandi.csv`;
`doppioni.csv` letto anche da questa fonte; un esito "proroga o modifica
di un bando esistente" distinto da "bando nuovo".

**Costo per bando.** Sommario: poche pagine a settimana, senza modello se
il riconoscimento è a regole. Testo di un bando: da 30.000 a 80.000
caratteri. Da misurare sui tre esempi prima di decidere.

**Regola di chiusura proposta.** Su quattro numeri consecutivi:
(a) tutti gli atti di "Contributi e finanziamenti" e dei supplementi
classificati come già in archivio, proroga, bando nuovo o fuori
perimetro, con zero errori nel controllo a mano; (b) i due bandi neve e
gli altri già in archivio riconosciuti come doppioni; (c) almeno un bando
nuovo applicabile al territorio. Se (c) fallisce su quattro numeri, il
BURT resta solo strumento di misura e non entra in `fonti.csv`.

---

## 4. Domande aperte

### 4.1 Cosa non ho stabilito

1. Il contenuto dei robots.txt delle fonti nazionali diverse da MIT e
   Finanza locale (Sport, Sport e Salute, Istruzione, Cultura, Affari
   regionali, Turismo) e di `www301.regione.toscana.it`. Quelli del BURT,
   del MIT e della Finanza locale sono stati letti a mano il 18/11/2026.
2. ~~Se l'elenco di consultazione del BURT è in ritardo di tre
   settimane.~~ Chiuso il 18/11/2026: non lo è.
3. ~~Se la pagina dei contributi attivi del MIT è vietata dal robots.txt
   o solo a quell'indirizzo.~~ Chiuso il 18/11/2026: non è vietata.
4. ~~Se l'archivio delle notizie della Finanza locale si lascia leggere
   in automatico.~~ Chiuso il 18/11/2026: robots.txt senza divieti,
   archivio leggibile.
5. Se il bando Festa della Toscana è anche sul Portale della Giunta.
6. Se uno dei dieci avvisi ARTI sulla legge 68/99 riguarda Pistoia.
7. Quanto pubblica il Ministero del Turismo e dove.
8. La fonte ufficiale degli avvisi Zenit e Fondimpresa.
9. Se esistono feed RSS per le fonti candidate.
10. Se il file completo di Incentivi Italia contiene avvisi per i Comuni
    che il filtro del progetto scarta.
11. La stima annua del BURT: tre settimane di ottobre non bastano.

### 4.2 Da chiedere al consulente pilota

1. **I due bandi mancati**: titolo, ente e dove li ha visti. Senza
   questo l'ordine qui sopra è una scommessa.
2. **Quali ministeri segue davvero** per l'Unione, e con che frequenza.
3. **Le istanze della Finanza locale** (messa in sicurezza,
   progettazione, contributo per i servizi associati): le segue il consulente o
   la ragioneria? Le vuole nell'app?
4. **Il BURT**: lo legge ogni settimana? Quale parte e quali sezioni? Lo
   usa per trovare bandi o per le date e le proroghe?
5. **Soglia di interesse**: un contributo da 3.000 euro con sei giorni di
   finestra gli serve, o è rumore?
6. **Bandi che ammettono i piccoli Comuni solo in forma associata** (Sport
   e Periferie 2026): l'Unione li considera?
7. **Emittenti regionali fuori dalla Giunta**: Consiglio regionale, ARTI,
   ARTEA. Li segue?
8. **Imprese della montagna**: gli servono Turismo e Sport e Salute, o il
   suo lavoro è solo sugli enti?
9. **Fonti di segnalazione che usa già** (newsletter, ANCI, Uncem): per
   decidere se una fonte di scoperta in più serve.
