# Uyari

*Uyari* means "listen" in Quechua.

## Hackathon submission: what existed before, what was built

Everything in this repository was built during the hackathon except two inputs we made before it and own.
They are disclosed here and kept in their own, labelled folders.

| | What | When | Where |
|---|---|---|---|
| **Input, made before the hackathon** | 10,000 Spanish source sentences, generated with Claude Opus 4.8 from the design matrix | June 2026 | [`primary/spa_Latn/chunks/generated/2026-06_opus48_0001.csv`](primary/spa_Latn/chunks/generated/2026-06_opus48_0001.csv) |
| **Input, made before the hackathon** | 3,578 human Shawi translations of 3,575 of those sentences, commissioned and paid for by Alexander Salazar and Yuri Cavero, the co-leads of the Shawi–Spanish case, who hold the rights and release them under CC BY 4.0 | July to October 2026 | [`languages/cbt_Latn/contributions/`](languages/cbt_Latn/contributions/) (`2026-11_uyari_0001` to `0003`), [decision 0004](docs/decisions/0004-commissioned-shawi-contributions.md), [`DATA_LICENSE.md`](DATA_LICENSE.md) |
| **Built during the hackathon** | Everything else: the toolkit ([`src/uyari/`](src/uyari/)) with its data format, validator and builds; generation on Meta models and the 101,363 Muse Spark sentences; the translation of all 111,363 sentences into seven more languages; both fine-tuned models; the Shawi voice; the demo | 2 to 4 November 2026 (UTC): git history, the `gen_date` of every batch, each model's `trained_at` | the rest of the repository |

**Fine-tuned weights, published, and where they run:**

| Model | Weights | License | Where it runs |
|---|---|---|---|
| Muse Glimmer 30B QLoRA, `mt-cbt-glimmer30b-qlora@v0.4` (the demo default) | [huggingface.co/malexandersalazar/uyari-mt-cbt-glimmer30b-qlora](https://huggingface.co/malexandersalazar/uyari-mt-cbt-glimmer30b-qlora) (LoRA adapter and GGUF) | Apache 2.0 | Trained on a rented Modal H100; served on our RTX 4090 as Unsloth's 4-bit GGUF with the adapter, through llama-server |
| NLLB-200 1.3B, `mt-cbt-nllb1.3b@v0.3` | [huggingface.co/malexandersalazar/uyari-mt-cbt-nllb1.3b](https://huggingface.co/malexandersalazar/uyari-mt-cbt-nllb1.3b) | CC BY-NC 4.0 | Trained on our RTX 4090; runs on the 4090, an RTX 3060 or a CPU |

**The problem in brief.** About **476.6 million** Indigenous people — over 6% of humanity — live in
90 countries. They are nearly three times more likely to live in extreme poverty; 3,193 of 7,159 living
languages (about 45%) are endangered; 40% of people worldwide lack education in a language they understand,
up to 90% in some low- and middle-income countries.

No global count exists of who cannot use their country's official language at all. In just four Latin
American countries it is about **3.1 million**: Mexico **865,972** (direct census count), Guatemala
**~1.64M**, Peru **~335,576**, Bolivia **~267,729** — plus millions more who manage daily life but cannot
follow a diagnosis or a court hearing. Mexico's 7.36M Indigenous-language speakers alone outnumber the
speakers of Danish, Finnish or Norwegian. Seventy percent of Indigenous people live in Asia and the Pacific,
where no comparable figure exists.

The cost falls on health, schooling and justice: in Guatemala the language barrier was "the most important
obstacle" to Indigenous women's use of reproductive health services, and their maternal mortality was
**166 vs 78** per 100,000 live births; in Mexico Indigenous-language speakers average 6.2 years of
schooling, **monolinguals 1.4**; laws recognising Indigenous languages are common, interpreters are not.
Monolinguals are disproportionately older, female and non-literate — **speech is not optional**.

Full figures with sources: [`PROBLEM.md`](PROBLEM.md). How Uyari answers it:
[`METHODOLOGY.md`](METHODOLOGY.md). Both in English, Spanish, Portuguese, French, German, Italian, Hindi
and Thai ([`docs/`](docs/README.md)).

**Runs on Meta Muse Glimmer (open weights) on our own RTX 4090** (trained on a rented H100). Uyari turns a community's own
translations and recordings into translation models between any Indigenous or under-served language and the
official language its speakers need. Five use cases per language pair: text to text in both directions,
speech to speech in both directions, and speech to text for the Indigenous language. A language is a folder;
data is a folder inside it; nobody changes code.

The first language pair is **Shawi ↔ Spanish** (Peru), which began with maternal health: Shawi communities
meet health services that offer no support in their language. It is the first case, not a limit: the same
data now also pairs Shawi with **English, French, German, Italian and Portuguese**, and any language is
added as a folder.

## What exists today

| | Status |
|---|---|
| Shawi (`cbt_Latn`) ↔ Spanish, **text** | 3,575 human translations of Spanish sentences. One model per backend covers all six official languages (build `data-2026.11-six`). On the held-out test set, chrF++ es→shw / shw→es: **Muse Glimmer 30B QLoRA** (`mt-cbt-glimmer30b-qlora@v0.4`, rank 64, the demo default; trained in 108 min on a rented Modal H100 for about US$ 7, served on our 4090) **41.7 / 44.4**; **NLLB-200 1.3B** (`mt-cbt-nllb1.3b@v0.3`, 45 min on the 4090) **43.2 / 45.8**; retrieval floor 23.4 / 22.0. On validation Glimmer is 1.8 below NLLB into Shawi and 0.5 below out of it (all six languages). Decoded the same way (greedy, before 4-bit serving) it matches NLLB into Shawi: the rest is NLLB's beam search and serving Glimmer in 4 bits. Each epoch shows every Shawi sentence as a target from 2 of its 6 sources, and checkpoints are chosen by chrF++ into Shawi. |
| Shawi ↔ **English, French, German, Italian, Portuguese**, text | Every Spanish sentence has a twin with the same id in each language (machine-translated with Muse Spark), so all 3,575 human Shawi translations pair with all six. Test chrF++ into / out of Shawi, NLLB: English 43.3 / 45.5, French 43.1 / 46.3, German 42.6 / 44.1, Italian 43.2 / 44.7, Portuguese 43.3 / 43.0 (Glimmer: English 40.9 / 44.9, French 39.9 / 44.9, German 40.9 / 43.4, Italian 41.1 / 43.8, Portuguese 41.3 / 41.9). The official-language references are machine-translated; the Shawi is human ([details](primary/eng_Latn/README.md)). |
| Spanish, English, French or Portuguese **speech** in → Shawi text **and speech** out | Demo, one action: Muse Voice Transcribe (the visitor's own Meta key) → our translator → Shawi read aloud by Meta's MMS voice on our own server. That voice learned an older spelling from Bible readings, so a spelling converter ([`tts.yaml`](languages/cbt_Latn/tts.yaml)) rewrites our text for it: it can read 99.99% of the letters in our Shawi text, 86% without. Also `uyari s2s`. |
| Shawi **speech** in, and a Shawi voice of our own | **Not yet: there are no Shawi recordings.** The format, validator, build and ASR/TTS pipelines run on a labelled synthetic fixture; [`languages/cbt_Latn/NEEDS.md`](languages/cbt_Latn/NEEDS.md) asks for recordings. |
| Spanish source sentences | 111,363 chunks from a fixed design matrix: the 10,000 of June 2026, and 101,363 generated with Muse Spark 1.3 Contributor during the hackathon. Same prompt, **3.3% of the cost** with Muse Spark, **no API cost** with Muse Glimmer ([details](primary/spa_Latn/README.md)). |

## Meta models, and what each one does

| Model | Job | Where it runs |
|---|---|---|
| **Muse Glimmer 30B** (open weights, Apache 2.0) | The headline translator (QLoRA, Shawi ↔ six official languages, the demo default); the Gatekeeper agent's reviewer; free local Spanish generation | Trained on a rented Modal H100 ([`scripts/modal_glimmer.py`](scripts/modal_glimmer.py): the 4-bit model does not fit 24 GB for training); served on our RTX 4090 as Unsloth's 4-bit GGUF with the adapter, through llama-server (`uyari serve`, 16.5 GB) |
| **Muse Spark 1.3 Contributor** | Spanish source-sentence generation (about $0.02 per 1,000 sentences) and their translation into the other official languages (about $0.02 per 1,000 sentences per language); in the demo, a spoken language into Spanish only if no model takes it into Shawi (visitor's key). It never sees Shawi: the Contributor tier lets Meta train on prompts | Meta Model API |
| **Muse Voice Transcribe** | Spanish, English, French and Portuguese voice input in the demo, paid with the visitor's own key (the server never uses its own) | Meta Model API |
| NLLB-200 1.3B (CC BY-NC) | Fast baseline, the demo's second choice | RTX 3060 / 4090 / CPU |
| MMS-TTS (`facebook/mms-tts-cbt`, CC BY-NC) | Reads Shawi aloud in the demo and `uyari s2s`, through our spelling converter; replaced by a voice of our own once there are recordings | Our server, CPU |
| Omnilingual ASR | Indigenous speech input once recordings exist (zero-shot, unmeasured until then) | RTX 4090 |

**Why Meta for generation.** We regenerated 200 cells of our first Spanish batch with the identical prompt;
only the model changed. Muse Spark 1.3 Contributor cost $0.021 per 1,000 sentences against ~$0.64 for the
model we started with (3.3%). It returned well-formed output for 100% of requests (96.5% before) and wrote
slightly more varied Spanish (distinct-2 0.891 vs 0.870). The earlier model kept the length buckets a
little more often (94.5% vs 89.0%). With Muse Glimmer the same generation runs on our own GPU with no API
cost and nothing leaving our hardware. Full table: [`reports/gen-comparison.md`](reports/gen-comparison.md).

## Quick start

**Windows or Linux, data tools only (no GPU needed):**

```bash
uv sync --python 3.11 --extra dev --extra speech
uv run uyari validate                       # gate 1: schemas, ids, apostrophes, duplicates, audio
uv run uyari build --tag data-2026.11-six --as-of 2026-11-02 --officials spa_Latn,eng_Latn,fra_Latn,deu_Latn,ita_Latn,por_Latn            # contributions -> builds/<tag>/<lang>/{mt,asr,tts}.parquet + MANIFEST.json
uv run uyari build --tag data-2026.11-six --as-of 2026-11-02 --officials spa_Latn,eng_Latn,fra_Latn,deu_Latn,ita_Latn,por_Latn --verify   # recompute: same tag -> same hashes on any OS
uv run pytest -q
uv run uyari demo --no-share                # Uyari Translate on http://localhost:7860 (needs a trained model)
```

`uyari demo` without `--no-share` also prints a public `https://….gradio.live` link: a free tunnel, no ngrok
needed, valid up to a week while the process runs, new on every restart. The page serves only our
fine-tuned models and reads Shawi aloud with a voice on the same machine; its optional voice input (Spanish,
English, French, Portuguese) asks each visitor for their own Meta API key.

**The RTX 4090 (Ubuntu):** see [`docs/RUNBOOK-4090.md`](docs/RUNBOOK-4090.md).

```bash
bash scripts/setup_ubuntu.sh check && python scripts/check_4090.py   # prove the GPU stack first
bash scripts/setup_ubuntu.sh project
make build floor train-nllb train-glimmer   # retrieval floor, NLLB 1.3B (<1 h), Glimmer QLoRA (~2 h on Modal)
make demo                                    # the Gradio page (it starts the Glimmer server) with a share link
```

## The pipelines

| Stage | Command | What it does |
|---|---|---|
| Consolidate | `uyari build --tag data-YYYY.MM` | Merged contributions → one table per task per language; takedowns and corrections applied; test rows in separate files; hashed manifest |
| Training data | `uyari prepare --recipe R` | Both directions, filters, chat formatting, tokenizer coverage check, reversible `ʼ` codec |
| Train | `uyari train --recipe R` | `seq2seq` (NLLB) or `qlora` (Glimmer via Unsloth; PEFT elsewhere). Recipes are the only configuration |
| Evaluate | `uyari eval --model M` (`--final` once for test) | chrF++ and BLEU per direction and domain, against the retrieval floor |
| Generate Spanish | `uyari generate plan / run / collect / dedup / compare` | Muse Spark or Muse Glimmer; `--estimate` prints the cost before anything is sent |
| Another official language | `uyari primary translate --target eng_Latn` | Machine-translates the source sentences, same chunk ids, labelled `machine_translated`; `--estimate` first |
| Review | `uyari gatekeeper --contribution C` | Validator + language check + copied rows + Glimmer's written review, in Spanish |
| Train loop | `uyari trainer --language cbt_Latn --open-pr` | Build → train → evaluate → promote (≥ +0.5 chrF++ and above the floor) → card → `NEEDS.md` → pull request |
| Speech | `uyari transcribe`, `uyari asr infer/eval`, `uyari tts check-voice`, `uyari s2s` | Speech chain; Shawi spoken through the MMS voice and `languages/cbt_Latn/tts.yaml`; text output where no usable voice exists |

Every command takes `--root` to run on another data root (the tests use a synthetic fixture).

## Money and data

* **Bring your own key:** the demo server runs only our fine-tuned models and never uses its own API key;
  paid features (voice input) use the visitor's key, for that request only, never stored. The CLI uses
  your own `META_API_KEY`, and every paid command has `--estimate`.
* **Budget:** USD 150 for the project's own API use. Every call is in `.uyari/ledger.jsonl`; each run has a cap
  (`generate` $1, `transcribe` $2, everything else $0 because it is local). `uyari llm spend`.
  Spent so far: $15.74 (generation $2.16, translation into seven languages $13.58: the ledger cost noted on
  every batch in `primary/*/primary.yaml`). Rented GPUs (Modal, for
  Glimmer's training, six runs): about US$ 30 so far.
* **Data policy:** every model in [`config/llm.yaml`](config/llm.yaml) declares what it may see.
  Anything containing Shawi goes only to models on our own hardware, or to a GPU we rent to run our own
  training code (Glimmer on Modal; never the test split: [decision 0010](docs/decisions/0010-training-on-rented-gpus.md));
  the code refuses otherwise.
* **Privacy:** row ids are pseudonymous; `uyari privacy-check` runs before every commit.

## Repository map

```text
primary/spa_Latn/        the Spanish sentences every language translates (+ matrix.yaml for generation)
primary/<lang>/          the same sentences in English, French, German, Italian, Portuguese, Hindi and Thai
                         (machine-translated, same ids; Hindi and Thai are not trained on yet)
languages/cbt_Latn/      language.yaml, NEEDS.md, contributions/<YYYY-MM>_<org>_<nnnn>/
schemas/  registry/      JSON Schemas (column order lives here), language code tables
recipes/                 one YAML per training run
builds/<tag>/            MANIFEST.json (parquet is not in git; rebuilt from the tag)
models/                  registry.yaml, model cards and scores (weights are not in git)
reports/                 generation comparison, side-by-side translations
src/uyari/               the code (one CLI: `uyari`)
demo/                    Gradio demo (4090)
contributing/            how to contribute, rights and consent templates, takedowns.csv, in 8 languages
docs/                    PROBLEM and METHODOLOGY in 7 more languages, decisions, runbook
```

[`PROBLEM.md`](PROBLEM.md) · [`METHODOLOGY.md`](METHODOLOGY.md) · [`contributing/`](contributing/README.md) ·
[`CREDITS.md`](CREDITS.md) · Code: Apache 2.0 · Data: CC BY 4.0 ([`DATA_LICENSE.md`](DATA_LICENSE.md)) ·
Commercial use, including by companies deploying for clinics, is welcome with credit ([`NOTICE`](NOTICE))

---
*Documentation transparency: this README was enhanced with Muse Spark 1.3 Contributor. A human defined
what mattered and verified the figures against [`PROBLEM.md`](PROBLEM.md); the model condensed them into
the brief introduction above.*
