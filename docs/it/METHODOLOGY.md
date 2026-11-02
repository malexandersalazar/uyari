# Metodologia di Uyari

[English](../../METHODOLOGY.md) · [Español](../es/METHODOLOGY.md) · [Português](../pt/METHODOLOGY.md) · [Français](../fr/METHODOLOGY.md) · [Deutsch](../de/METHODOLOGY.md) · **Italiano** · [हिन्दी](../hi/METHODOLOGY.md) · [ไทย](../th/METHODOLOGY.md)

Uyari è una struttura di dati e un kit di strumenti di addestramento aperti che trasformano le traduzioni e le
registrazioni di una comunità in modelli tra una lingua indigena o un'altra lingua poco supportata e la lingua
ufficiale di cui hanno bisogno i suoi parlanti. Una lingua si aggiunge come cartella; i dati si aggiungono come
cartella al suo interno; nessuno modifica il codice. I modelli di Meta sono lo stack predefinito.

Le ragioni delle scelte strutturali sono in [`docs/decisions/`](../../docs/decisions/). Il problema che il
progetto affronta, con dati e fonti, è in [`PROBLEM.md`](PROBLEM.md).

## 1. Obiettivo e ambito

**Cinque casi d'uso per coppia di lingue:**

| # | Caso d'uso | Modelli |
|---|---|---|
| 1 | Testo in lingua indigena → testo in lingua ufficiale | MT |
| 2 | Testo in lingua ufficiale → testo in lingua indigena | MT |
| 3 | Voce in lingua indigena → voce in lingua ufficiale | ASR → MT → TTS |
| 4 | Voce in lingua ufficiale → voce in lingua indigena | ASR → MT → TTS |
| 5 | Voce in lingua indigena → testo in lingua indigena (da voce a testo) | ASR |

**La prima coppia è shawi ↔ spagnolo** (`cbt_Latn`, glottocode `chay1248`; Perù). È la prima perché lì il
lavoro era già cominciato, con la salute materna ([`PROBLEM.md` §6](PROBLEM.md#6-il-primo-caso-shawi--spagnolo-perù)),
non perché qualcosa sia specifico di questa coppia. Che cosa esiste per essa:

* 11,977 segmenti (chunk) primari in spagnolo (sintetici, dalla matrice di progettazione in
  `primary/spa_Latn/matrix.yaml`).
* 3,578 traduzioni umane in shawi di 3,575 di questi segmenti, lavoro su commissione, in tre contributi.
* Gli stessi 11,977 segmenti in inglese, tradotti automaticamente dallo spagnolo con gli stessi id dei
  segmenti, così ogni traduzione in shawi forma una coppia anche con l'inglese.
* Nessuna registrazione in shawi. Il percorso audio (validatore, build, pipeline ASR/TTS) viene messo alla prova
  su un insieme di dati di prova sintetico ed etichettato (`qaa_Latn`), e `NEEDS.md` chiede registrazioni.

| Nell'ambito | Fuori ambito |
|---|---|
| Qualsiasi lingua con una forma scritta; il formato accetta ogni scrittura ISO 15924 (finora è testata solo la scrittura latina) | Lingue solo orali (il formato conserva audio non trascritto; nessuna pipeline lo usa ancora) |
| Lingue ufficiali come corpus primari: lo spagnolo (generato) e l'inglese (tradotto automaticamente dallo spagnolo); le altre (portoghese, francese, hindi, thai, …) con lo stesso meccanismo | Ricerca dialettale: le varietà sono un'etichetta su un contributo |
| Traduzioni e registrazioni umane; testo scritto da macchine solo sul lato della lingua ufficiale, ed etichettato | Traduzione automatica presentata come lavoro umano |
| Una lingua entra quando una comunità porta dati e una persona responsabile (steward) | Un servizio di inferenza in produzione; la demo è una demo |

## 2. Principi

1. **L'unità è il contributo.** I dati si archiviano come cartelle di contributo, ciascuna con la propria
   provenienza, licenza e consenso. I dati si mettono insieme solo nelle build e nelle ricette, mai spostando file.
2. **ID stabili, mai posizioni.** Gli id dei segmenti sono di 32 caratteri esadecimali e non si riusano mai (chi
   traduce lavora proprio da questi id). I file si possono dividere o ordinare senza rompere un riferimento.
3. **I contributi integrati con il merge sono immutabili.** Una correzione è un nuovo contributo che dice che
   cosa sostituisce.
4. **Le persone traducono e parlano; le macchine possono solo fare una bozza del lato della lingua ufficiale, e
   lo dichiarano.** Ogni segmento sintetico indica il modello che l'ha scritto (`gen_model`, `provider`,
   `prompt_version`).
5. **Consenso e ritiro sono dati.** Ogni contributo porta una licenza e un riferimento di consenso; un ritiro è
   una riga CSV che la build successiva applica.
6. **Codici standard, nomi semplici, build riproducibili.** Le lingue sono identificate da ISO 639-3 più la
   scrittura (`cbt_Latn`), il tag dei modelli di Meta. Lo stesso tag di build produce lo stesso hash del
   contenuto su qualsiasi sistema operativo.
7. **I dati delle comunità non lasciano mai il nostro hardware verso un modello che potrebbe addestrarsi su di
   essi.** Ogni modello dichiara una `data_policy`; il codice si rifiuta di inviare testo in lingua indigena a
   un modello ospitato da terzi di livello Contributor.
8. **Le API a pagamento sono facoltative e le paga chi le usa.** La CLI usa la tua chiave; la demo chiede a ogni
   visitatore la sua e altrimenti esegue solo i modelli aperti con fine-tuning.

**Una conseguenza.** La partizione (split) è una proprietà del segmento primario, condivisa da tutte le lingue,
ed è assegnata per **gruppo di parafrasi** (le ~10 parafrasi quasi equivalenti prodotte da una stessa richiesta
di generazione), così nessun modello può vedere in addestramento una parafrasi di una frase di test.

## 3. Modello dei dati

| Entità | Chiave | Deve avere |
|---|---|---|
| Segmento primario | `chunk_id` (32 esadecimali) | testo, partizione, origine, stato; ogni colonna della matrice di progettazione registrata dal generatore |
| Lingua | `<iso639-3>_<Script>` | glottocode, nome visualizzato, steward, autorità comunitaria, apostrofo canonico |
| Contributo | `<YYYY-MM>_<org>_<nnnn>` | contributore (pseudonimo), licenza, consenso, provenienza, date di raccolta, varietà |
| Riga di coppia | (contributo, chunk_id) | testo, translator_id (pseudonimo); `replaces` facoltativo |
| Riga audio | (contributo, file) | parlante, stile; chunk_id o trascrizione |
| Parlante | (contributo, speaker_id) | fascia d'età, riferimento di consenso |
| Build | `data-YYYY.MM[-rN]` | una tabella per compito per lingua, manifest con hash dei file e dei contenuti |
| Ricetta | file | build, lingua, modello di base, metodo, iperparametri |
| Scheda del modello | `name@vX.Y` | build, ricetta, licenza del modello di base, punteggi di validazione rispetto alla soglia di recupero, test una sola volta |

Righe audio: `chunk_id` compilato e `transcript` vuoto significa che chi parla ha letto la traduzione del
segmento contenuta in quel contributo; `chunk_id` vuoto con `transcript` compilato è parlato spontaneo
(assegnato alle partizioni per parlante); se sono vuoti entrambi, la riga si conserva e non si usa. I
vocabolari chiusi sono in `schemas/`; il validatore rifiuta qualsiasi altro valore.

## 4. Corpus primario

Il corpus primario è l'insieme delle frasi in lingua ufficiale che ogni lingua traduce. Oggi è lo spagnolo
(`primary/spa_Latn/`).

**Che cosa abbiamo.** Il primo lotto, `2026-06_opus48_0001.csv`: 10,000 segmenti generati a giugno 2026 con
Claude Opus 4.8, che coprono 4 dei 15 domini della matrice e 37 micro-scenari. Ogni riga conserva la sua cella
della matrice (dominio, micro-scenario, registro, atto comunicativo, tempo verbale, polarità, persona, fascia di
lunghezza, profilo di chi parla, tono, discorso connesso, parole àncora, `source_custom_id`).

**Generarne altri, con modelli Meta.** `uyari generate` mantiene la matrice di quel lotto, la sua rotazione
(round-robin) su tempo verbale/polarità/persona, le parole àncora, il piano su disco con stato per unità e
riesecuzioni idempotenti, la chiave di gruppo `custom_id`, il parsing, la validazione e la deduplicazione, e **lo
stesso identico prompt** (un solo `prompt_version` fissato), così un confronto misura i modelli, non le modifiche
al prompt. Rigenerare 200 celle con Muse Spark 1.3 Contributor è costato, per 1,000 segmenti, il 3.3% del costo
originale, con il 100% di risposte ben formate e un testo leggermente più vario (`reports/gen-comparison.md`);
Muse Glimmer sulla nostra GPU lo fa senza costi di API. Prima dell'invio, `--estimate` stampa il costo; ogni
esecuzione ha un tetto; ogni chiamata è nel registro (ledger).

**Post-elaborazione.** NFC e spazi; 1–120 parole e la fascia di lunghezza dell'unità ±30%; termini urbani
vietati; un controllo della lingua; deduplicazione esatta e quasi-duplicati tramite embedding (coseno 0.92, a
blocchi per dominio) rispetto a tutto il corpus primario; una lettura umana a campione del 2% per lotto
(`uyari primary sample`); un lotto con oltre il 5% di scarti viene ritirato.

**Partizioni.** Prima assegnazione: validazione e test contengono ~300 segmenti tradotti ciascuna, come gruppi
di parafrasi interi presi tra i gruppi tradotti, stratificati per dominio, ordinati per hash. Gruppi nuovi: un
gruppo che rigenera una cella esistente ne eredita la partizione; gli altri per hash (5% / 5%). Una volta
scritte, le partizioni sono congelate.

**Altri corpus primari.** L'inglese (`primary/eng_Latn`) condivide gli id dei segmenti con lo spagnolo:
`uyari primary translate` ha tradotto automaticamente tutti gli 11,977 segmenti con Muse Spark 1.3 Contributor
per US$ 0.19, con l'etichetta `origin=machine_translated` e copiando partizione, dominio e gruppo di parafrasi.
Le altre lingue ufficiali si aggiungono allo stesso modo.

## 5. Aggiungere una lingua

Una cartella `languages/<iso639-3>_<Script>/` con `language.yaml` e `README.md`. Il validatore la accetta quando
ogni codice si risolve in `registry/` (si accetta l'intervallo ISO 639-3 per uso locale `qaa`–`qtz`) e viene
indicata una persona responsabile (steward). Campi:
`id, iso639_3, script, glottocode, display_name, iso_name, primary, steward, community_authority, apostrophe,
apostrophe_variants, training_orthography, trainer`. Le lettere che gli strumenti spesso storpiano si dichiarano
una volta sola: in shawi l'occlusiva glottidale è una lettera, canonica `ʼ` (U+02BC), e il validatore elenca i
caratteri varianti con la correzione.

## 6. Contribuire

Vedi [`contributing/`](../../contributing/) (inglese, spagnolo, portoghese, francese, tedesco, italiano, hindi,
thai). Una cartella, una pull request, una lingua, una varietà, una licenza, un riferimento di consenso:
`contribution.yaml`, `pairs.csv`, `audio.csv`, `speakers.csv`, `wav/`. I contributi parziali sono normali; la
build ricava che cosa contiene una cartella dai file che esistono.

## 7. Revisione

Tre filtri: il **validatore** (CI, ogni PR), il **Gatekeeper** (Muse Glimmer sulla nostra GPU; una revisione
scritta nella lingua di lavoro della persona responsabile, lo spagnolo per lo shawi) e la **persona
responsabile della lingua** (steward: qualcuno che parla la lingua). Il Gatekeeper intercetta gli errori del
validatore, il testo in lingua ufficiale incollato nella colonna della lingua indigena, le righe copiate da
contributi accettati e il testo diverso dalle coppie accettate; raccomanda merge, restituzione o escalation (i
domini salute e consenso vanno sempre in escalation). **Non** rileva la traduzione automatica; chi contribuisce
attesta che nessun output automatico viene presentato come lavoro umano.

## 8. Build

`uyari build --tag data-YYYY.MM` legge ogni contributo, applica `replaces`, salta i contributi revocati e i
ritiri con decorrenza pari o anteriore a `--as-of`, normalizza il testo, associa partizione e dominio, e scrive
`builds/<tag>/<lang>/{mt,asr,tts}.parquet` (addestramento + validazione) e `*.test.parquet` (test), più
`MANIFEST.json`: commit git, contributi inclusi ed esclusi con i motivi, righe escluse con i motivi, righe per
partizione, licenze e, per ogni tabella, un `sha256` del file e un `content_sha256` canonico. I dati mancanti si
ricavano, non si dichiarano mai. Il Parquet non è in git; il tag lo ricostruisce.

## 9. Agenti

| Agente | Attivazione | Decide | Scrive |
|---|---|---|---|
| **Gatekeeper** | Una PR in `contributions/` | merge / restituzione / escalation (solo raccomandazione) | Una revisione sulla PR, una bozza di `review.yaml` |
| **Trainer** | Un merge in `main` (runner GPU sul nostro hardware), o a mano | Se vale la pena creare una build (lingua nuova o ≥10% di coppie in più); promuove solo se ogni direzione supera la soglia di recupero **e**, sulle direzioni comuni ai due modelli, il chrF++ di validazione migliora di ≥0.5 rispetto al modello in carica rivalutato sulla stessa build (oppure il candidato aggiunge direzioni e non perde più di 0.5) | Manifest della build, scheda del modello, `scores.json`, `models/registry.yaml`, `NEEDS.md`, una pull request |
| Interprete | (dopo l'MVP) | | |

Salvaguardie: nessun agente fa merge; nessun agente legge la partizione di test prima di una promozione; il test
si valuta una sola volta per versione del modello; ogni decisione è una riga sulla PR o sulla scheda con i
numeri che l'hanno prodotta.

## 10. Addestramento e valutazione

Le ricette in `recipes/` sono l'unica configurazione. Un modello per backend copre ogni lingua ufficiale
abbinata a quella indigena (oggi spagnolo e inglese: quattro direzioni), e ogni direzione viene valutata sulla
propria coppia di lingue. Modelli di riferimento per il testo:

* **Muse Glimmer 30B, QLoRA** (Unsloth, 4-bit, r=16, lunghezza massima 512, batch 1 × 16, 3 epoche): il modello
  principale, sulla nostra RTX 4090.
* **NLLB-200 1.3B, fine-tuning completo** (un nuovo token di lingua inizializzato da una lingua affine;
  `quy_Latn` per lo shawi): la baseline rapida; si addestra anche su una RTX 3060 da 12 GB in bf16 puro.
* **Soglia di recupero (retrieval floor):** la traduzione umana della frase di addestramento più vicina; locale,
  gratuita.

La demo serve solo questi modelli con fine-tuning: Glimmer come predefinito una volta addestrato, NLLB come
modalità rapida; le schede dicono quale ottiene il punteggio più alto.

| Compito | Punteggio | Controllo umano |
|---|---|---|
| Da testo a testo | chrF++ per direzione (BLEU riportato, non ottimizzato) | Due parlanti nativi valutano 100 frasi, quando disponibili |
| Da voce a testo | CER (WER riportato) | Accettabilità della trascrizione su 50 clip |
| Da testo a voce | CER di andata e ritorno tramite ASR | Naturalezza 1–5 |
| Da voce a voce | chrF++ dell'output dopo ASR | Riuscita del compito su un dialogo predefinito |

COMET e le altre metriche apprese non sono considerate affidabili per la traduzione verso le lingue indigene
finché non vengono validate rispetto a giudizi umani.

## 11. Governance

Codice: Apache 2.0. Dati: per contributo (predefinita CC BY 4.0; CC BY-SA, CC BY-NC o una licenza comunitaria, a
scelta della comunità), riportata su ogni riga delle build. Il consenso è collettivo (autorità comunitaria) e
individuale (ogni parlante e ogni traduttore); i ritiri sono righe in `contributing/takedowns.csv`. Ruoli,
licenze, modelli di consenso e tutele, in otto lingue:
[`contributing/<language>/governance.md`](../../contributing/it/governance.md).

## 12. Costi

* **Locale per impostazione predefinita.** Addestramento, valutazione, il Gatekeeper e la demo girano sulle
  nostre GPU senza costi di API.
* **Usa la tua chiave.** Tutto ciò che chiama un'API a pagamento usa la chiave Meta di chi la chiama: la CLI
  legge `META_API_KEY`; la demo chiede ai visitatori la loro, la usa solo per quella richiesta e non la conserva
  mai, e non ripiega mai sulla chiave del server.
* **Stimare prima di spendere.** I prezzi sono in `config/llm.yaml`; ogni comando LLM stima il proprio costo
  prima dell'invio (approssimazione tiktoken × 1.2), l'uso reale di ogni chiamata è in `.uyari/ledger.jsonl`, e
  ogni esecuzione ha un tetto rigido (`generate` $1, `transcribe` $2, tutto il resto $0 perché gira in locale).
  Il budget di sviluppo del progetto per le API ospitate è di USD 150.
