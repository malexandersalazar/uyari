# Il problema: il divario linguistico nei servizi di base

[English](../../PROBLEM.md) · [Español](../es/PROBLEM.md) · [Português](../pt/PROBLEM.md) · [Français](../fr/PROBLEM.md) · [Deutsch](../de/PROBLEM.md) · **Italiano** · [हिन्दी](../hi/PROBLEM.md) · [ไทย](../th/PROBLEM.md)

Circa **476 milioni** di persone indigene vivono in 90 paesi. Molte di loro hanno a che fare con medici, moduli
di consenso, tribunali e uffici di stato civile in una lingua ufficiale che non capiscono del tutto. Dove questo
si misura, i numeri sono grandi: in soli quattro paesi dell'America Latina, circa **3 milioni** di persone non
sanno usare affatto la lingua ufficiale del proprio paese. Altrove, per lo più, non si conta.

I modelli di base aperti per la voce e la traduzione coprono ormai più di 1,600 lingue. Quello che non esiste è
lo strato che li trasforma in qualcosa che un ambulatorio possa usare: **modelli valutati e governati dalle
comunità, tra ogni lingua indigena e la lingua ufficiale di cui hanno bisogno i suoi parlanti, nel testo e nella
voce**. Uyari costruisce questo strato dell'ultimo miglio per qualsiasi lingua. Non costruisce un altro modello
di base.

## 1. Dimensioni

| Regione (OIL, 2019) | Quota | Popolazione indigena |
|---|---|---|
| Asia e Pacifico | 70.5% | >335M |
| Africa | 16.3% | >77M |
| America Latina e Caraibi | 11.5% | ~55M (CEPAL 2018: 58M; 826 popoli) |
| America settentrionale | 1.6% | >7M |
| Europa e Asia centrale | 0.1% | <1M |
| **Mondo** | | **476.6M (>6% dell'umanità)** |

* Le persone indigene hanno una probabilità quasi tre volte maggiore di vivere in povertà estrema (OIL).
* Delle 7,159 lingue vive, 3,193 (circa il 45%) sono in pericolo (Ethnologue, 28ª ed., 2025).
* Il 40% delle persone nel mondo non riceve un'istruzione in una lingua che capisce, fino al 90% in alcuni paesi
  a basso e medio reddito (UNESCO GEM Report, 2025).

## 2. Persone che non sanno usare la lingua ufficiale

Non esiste un conteggio globale; pochi censimenti pongono la domanda. La regione misurata meglio è l'America
Latina:

| Paese | Parlanti di lingue indigene | Non sanno usare la lingua ufficiale | Fonte |
|---|---|---|---|
| Messico | 7,364,645 (6.1%, da 3 anni in su) | **865,972** non parlano spagnolo | INEGI, censimento 2020 (conteggio diretto) |
| Guatemala | 4,027,481 di lingua materna | **~1.64M** (20.9% della popolazione indigena) | Instituto Cervantes 2024 (stima) |
| Perù | 4,477,195 di lingua materna (16.02%, da 3 anni in su) | **~335,576** | Instituto Cervantes 2024 (stima; il censimento non lo chiede) |
| Bolivia | ~4.2M (2012) | **~267,729** | Instituto Cervantes 2024 (stima) |

Sono circa **3.1 milioni** di persone in quattro paesi, più diversi milioni di persone bilingui che sanno fare
la spesa nella lingua ufficiale ma non riescono a seguire una diagnosi o un'udienza in tribunale. Lo stesso
divario esiste ovunque uno Stato lavori in una lingua che i suoi cittadini indigeni non parlano; semplicemente
non viene contato. Il settanta per cento delle persone indigene del mondo vive in Asia e nel Pacifico, dove non
esiste un dato comparabile.

Non sono popolazioni piccole. I soli parlanti di lingue indigene del Messico sono più numerosi dei parlanti di
danese, finlandese o norvegese, lingue che hanno tutte un pieno supporto commerciale di IA.

## 3. Perché conta: salute, istruzione, giustizia

* **Salute.** In Guatemala la barriera linguistica era "l'ostacolo più importante" all'uso dei servizi di salute
  riproduttiva da parte delle donne indigene (analisi del Guttmacher sull'indagine nazionale 2008–09), e la
  mortalità materna delle donne indigene era più del doppio di quella delle donne non indigene: 166 contro 78
  ogni 100,000 nati vivi (studio nazionale del 2011). In Guatemala, Messico, Perù e Bolivia, le donne che
  *parlano* una lingua indigena hanno meno probabilità di partorire in una struttura sanitaria. Dove gli
  ospedali non hanno interpreti, il consenso informato fallisce.
* **Istruzione.** I bambini a cui si insegna in una lingua che parlano hanno molte più probabilità di leggere
  capendo ciò che leggono (UNESCO 2025). In Messico, i parlanti di lingue indigene dai 15 anni in su hanno in
  media 6.2 anni di scolarizzazione; **i monolingui, in media 1.4** (INEGI 2020).
* **Giustizia e pubblica amministrazione.** Le leggi che riconoscono le lingue indigene sono comuni; gli
  interpreti no. Il Congresso del Perù è rimasto più volte senza interpreti per le lingue indigene ufficiali, e
  il Messico dà validità legale alle lingue indigene mentre l'attuazione resta indietro.

Tra i monolingui sono sovrarappresentate le persone anziane, le donne e le persone non alfabetizzate. **La voce
non è facoltativa**: la sola traduzione del testo non le raggiunge.

## 4. Che cosa esiste e che cosa manca

| Livello | Che cosa esiste | Lacuna |
|---|---|---|
| Modelli di base | Meta Omnilingual ASR (1,600+ lingue, Apache 2.0), Omnilingual MT (1,600+), NLLB-200, MMS; Google Translate; Microsoft Translator | Valutati soprattutto rispetto all'inglese; qualità sconosciuta per la maggior parte delle lingue indigene; poco TTS e poca traduzione da voce a voce |
| Benchmark | Shared task regionali, come AmericasNLP (~13 lingue ↔ spagnolo, solo testo) | Lì la MT lingua ufficiale → lingua indigena "ha raggiunto un plateau di prestazioni" (chrF++ circa 13–37) |
| Progetti comunitari | Te Hiku Media (māori), Voces (Cile/Perù), molti progetti pilota locali | Una o poche lingue ciascuno; non riutilizzabili come pipeline |

Che cosa manca, ed è ciò per cui è fatto Uyari:

1. **Coppie lingua nativa ↔ lingua ufficiale**, non un passaggio attraverso l'inglese che somma gli errori.
2. **Voce** (ASR, TTS, da voce a voce) per lingue i cui parlanti spesso non leggono.
3. **Dati di dominio** per salute, consenso, stato civile e giustizia.
4. **Valutazione umana** da parte di parlanti nativi e interpreti certificati, non solo metriche automatiche.
5. **Attenzione ai dialetti**: un solo nome di lingua copre spesso molte varietà ("quechua" ne indica 25+ nel
   solo Perù).
6. **Governance**: consenso, condivisione dei benefici e licenze compatibili con la sovranità indigena sui dati.
7. **Messa in opera** che possa funzionare offline su hardware modesto.

## 5. L'approccio

* **Cinque casi d'uso per coppia di lingue:** testo indigeno → testo ufficiale, testo ufficiale → testo
  indigeno, voce indigena → voce ufficiale, voce ufficiale → voce indigena, e da voce a testo per la lingua
  indigena.
* **Partire dai modelli di base aperti di Meta; adattarli lingua per lingua.** Fare il fine-tuning di un modello
  multilingue condiviso (Muse Glimmer QLoRA, NLLB-200) su ogni coppia lingua nativa↔lingua ufficiale; una soglia
  di recupero (retrieval floor) tiene onesto ogni modello.
* **Da voce a voce in cascata** (ASR → MT → TTS), con il testo visibile nel mezzo, così una persona può
  controllare una diagnosi o un modulo di consenso prima che venga pronunciato.
* **Il budget sono i dati.** Per lingua, circa 5–20k frasi di dominio, 4–10 h di parlato letto da un solo
  parlante per una voce sintetica (una voce shipibo-konibo ha raggiunto MOS 4.01 con ~4 h) e 10–50 h di parlato
  trascritto. Il calcolo è una piccola frazione del costo (una stima ingegneristica, non un dato pubblicato).
* **Qualsiasi lingua, senza modifiche al codice.** Una lingua è una cartella; i dati di una comunità sono una
  cartella al suo interno. Il lato della lingua ufficiale è un corpus condiviso (prima lo spagnolo; le altre
  lingue ufficiali con lo stesso meccanismo).
* **Governance fin dalla progettazione**: consenso libero, previo e informato (UNDRIP, Convenzione OIL 169), i principi
  CARE, licenze per contributo, il ritiro come riga di dati, chi contribuisce viene pagato, e i popoli in
  isolamento volontario sono esclusi esplicitamente.
* **Interpreti come creatori e valutatori di dati**, non persone sostituite dallo strumento.
* **Misurare l'impatto, non solo chrF++**: comprensione del consenso, visite prenatali completate, tempo per
  ottenere il servizio.

## 6. Il primo caso: shawi ↔ spagnolo (Perù)

Lo shawi è il primo perché lì il lavoro era già cominciato, non perché il problema sia peruviano. Il caso
shawi–spagnolo è nato dalla salute materna: le comunità shawi si rivolgono a servizi sanitari che non offrono
alcun supporto nella loro lingua. Per questo caso sono state commissionate traduzioni umane, e quelle traduzioni
sono i primi dati di Uyari. Niente nel codice è specifico dello shawi.

| Indicatore | Dato | Fonte |
|---|---|---|
| Popoli / lingue indigene in Perù | 55 popoli; 48 lingue ufficiali | MinCul (2025–26) |
| Lingua materna indigena, da 3 anni in su | 4,477,195; quechua 3,799,780; aymara 450,010 | censimento 2017 (tramite MinCul 2024) |
| Lingua materna shawi | 17,241 | MinCul BDPI (censimento 2017) |
| Interpreti registrati | **859** (ReNITLI), per 39 delle 48 lingue | MinCul (gennaio 2025) |

Circa 5,200 parlanti di lingua materna per ogni interprete registrato, e nove lingue senza nessuno. Solo il 23.1%
delle famiglie in cui la lingua materna di un genitore è indigena ha un figlio o una figlia che la parla (INEI
2017); la popolazione monolingue sta invecchiando, quindi si sta chiudendo la finestra per registrare gli
anziani che la parlano con fluidità.

## Avvertenze

* I dati sulla popolazione sono stime del 2010–2019. Le definizioni (soprattutto per Cina e India) spostano i
  totali globali di oltre 100M.
* Solo gli 865,972 del Messico sono un conteggio censuario diretto delle persone che non parlano la lingua
  ufficiale. I dati di Perù, Guatemala e Bolivia sono stime dell'Instituto Cervantes 2024 basate su indicatori
  indiretti di analfabetismo e potrebbero essere sovrastimati.
* Le affermazioni sulla qualità dei modelli di base sono dichiarate da chi li sviluppa e centrate sull'inglese.
  Esistono poche valutazioni indipendenti tra le lingue indigene e le lingue ufficiali dei loro paesi.
* Le domande dei censimenti variano: quello del Perù chiede la lingua materna, non la competenza nella lingua
  ufficiale, e le età di riferimento variano (3+ contro 5+), quindi vanno sempre indicate.
