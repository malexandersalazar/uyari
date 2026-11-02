# Uyari

**Runs on Meta Muse Glimmer (open weights) on our own RTX 4090.** Uyari turns a community's own
translations and recordings into translation models between any Indigenous or under-served language and the
official language its speakers need. Five use cases per language pair: text to text in both directions,
speech to speech in both directions, and speech to text for the Indigenous language. A language is a folder;
data is a folder inside it; nobody changes code.

*Uyari* means "listen" in Quechua.

> About 476 million Indigenous people live in 90 countries, and many of them meet doctors, consent forms
> and courts in an official language they do not fully understand. Why this matters, with sources:
> [`PROBLEM.md`](PROBLEM.md). How Uyari answers it: [`METHODOLOGY.md`](METHODOLOGY.md). Both in English,
> Spanish, Portuguese, French, German, Italian, Hindi and Thai ([`docs/`](docs/README.md)).

The first language pair is **Shawi ↔ Spanish** (Peru), which began with maternal health: Shawi communities
meet health services that offer no support in their language. It is the first case, not a limit: the same
data now also pairs Shawi with **English**, and any language is added as a folder.

## What exists today

| | Status |
|---|---|
| Shawi (`cbt_Latn`) ↔ Spanish, **text** | 3,578 human translations of 10,000+ Spanish sentences. Trained and measured: NLLB-200 1.3B reaches chrF++ **38.2** (es→shw) and **36.5** (shw→es) on the held-out test set, against a retrieval floor of 23.4 / 22.0. Muse Glimmer 30B QLoRA is the next run on the 4090. |
| Shawi ↔ **English**, text | Every Spanish sentence now has an English twin with the same id (11,977, machine-translated with Muse Spark for **US$ 0.19**), so all 3,575 human Shawi translations also pair with English. Retrieval floor 21.9 (en→shw) / 22.7 (shw→en). One model per backend for all four directions trains on the 4090 next ([details](primary/eng_Latn/README.md)). |
| Spanish **speech** in → Shawi text out | Demo: Muse Voice Transcribe, paid with the visitor's own Meta key → translator. |
| Shawi **speech** | **Not yet: there are no Shawi recordings.** The format, validator, build and ASR/TTS pipelines run on a labelled synthetic fixture; [`languages/cbt_Latn/NEEDS.md`](languages/cbt_Latn/NEEDS.md) asks for recordings. |
| Spanish source sentences | 11,977 chunks from a fixed design matrix. Generation now runs on Meta: same prompt, **3.3% of the cost** with Muse Spark, **no API cost** with Muse Glimmer ([details](primary/spa_Latn/README.md)). |

## Meta models, and what each one does

| Model | Job | Where it runs |
|---|---|---|
| **Muse Glimmer 30B** (open weights, Apache 2.0) | The headline translator (QLoRA, Shawi ↔ Spanish and English); the Gatekeeper agent's reviewer; free local Spanish generation | Our RTX 4090 (`uyari serve`) |
| **Muse Spark 1.3 Contributor** | Spanish source-sentence generation (about $0.02 per 1,000 sentences) and their English translation ($0.19 for all 11,977). It never sees Shawi: the Contributor tier lets Meta train on prompts | Meta Model API |
| **Muse Voice Transcribe** | Spanish voice input in the demo, paid with the visitor's own key (the server never uses its own) | Meta Model API |
| NLLB-200 1.3B (CC BY-NC) | Fast baseline, the demo's "fast mode", the public Hugging Face Space | RTX 3060 / 4090 / CPU |
| Omnilingual ASR, MMS-TTS | Indigenous speech once recordings exist (zero-shot, unmeasured until then) | RTX 4090 |

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
uv run uyari build --tag data-2026.11       # contributions -> builds/<tag>/<lang>/{mt,asr,tts}.parquet + MANIFEST.json
uv run uyari build --tag data-2026.11 --verify   # recompute: same tag -> same hashes on any OS
uv run pytest -q
uv run uyari demo --no-share                # Uyari Translate on http://localhost:7860 (needs a trained model)
```

`uyari demo` without `--no-share` also prints a public `https://….gradio.live` link: a free tunnel, no ngrok
needed, valid up to a week while the process runs, new on every restart. The page serves only our
fine-tuned models; its optional Spanish voice input asks each visitor for their own Meta API key.

**The RTX 4090 (Ubuntu):** see [`docs/RUNBOOK-4090.md`](docs/RUNBOOK-4090.md).

```bash
bash scripts/setup_ubuntu.sh check && python scripts/check_4090.py   # prove the GPU stack first
bash scripts/setup_ubuntu.sh project
make build floor train-nllb train-glimmer   # retrieval floor, NLLB 1.3B (<1 h), Glimmer QLoRA (hours)
make demo                                    # Glimmer server + Gradio page with a share link
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
| Speech | `uyari transcribe`, `uyari asr infer/eval`, `uyari tts check-voice`, `uyari s2s` | Speech chain; text output where no usable voice exists |

Every command takes `--root` to run on another data root (the tests use a synthetic fixture).

## Money and data

* **Bring your own key:** the demo server runs only our fine-tuned models and never uses its own API key;
  paid features (Spanish voice) use the visitor's key, for that request only, never stored. The CLI uses
  your own `META_API_KEY`, and every paid command has `--estimate`.
* **Budget:** USD 150 for the project's own API use. Every call is in `.uyari/ledger.jsonl`; each run has a cap
  (`generate` $1, `transcribe` $2, everything else $0 because it is local). `uyari llm spend`.
  Spent so far: $0.23 (generation $0.042, English translation $0.186).
* **Data policy:** every model in [`config/llm.yaml`](config/llm.yaml) declares what it may see.
  Anything containing Shawi goes only to models on our own hardware; the code refuses otherwise.
* **Privacy:** row ids are pseudonymous; `uyari privacy-check` runs before every commit.

## Repository map

```text
primary/spa_Latn/        the Spanish sentences every language translates (+ matrix.yaml for generation)
primary/eng_Latn/        the same sentences in English (machine-translated, same ids)
languages/cbt_Latn/      language.yaml, NEEDS.md, contributions/<YYYY-MM>_<org>_<nnnn>/
schemas/  registry/      JSON Schemas (column order lives here), language code tables
recipes/                 one YAML per training run
builds/<tag>/            MANIFEST.json (parquet is not in git; rebuilt from the tag)
models/                  registry.yaml, model cards and scores (weights are not in git)
reports/                 generation comparison, side-by-side translations
src/uyari/               the code (one CLI: `uyari`)
demo/  space/            Gradio demo (4090) and the public CPU Space
contributing/            how to contribute, rights and consent templates, takedowns.csv, in 8 languages
docs/                    PROBLEM and METHODOLOGY in 7 more languages, decisions, runbook
```

[`PROBLEM.md`](PROBLEM.md) · [`METHODOLOGY.md`](METHODOLOGY.md) · [`contributing/`](contributing/README.md) ·
[`CREDITS.md`](CREDITS.md) · Code: Apache 2.0 · Data: CC BY 4.0 ([`DATA_LICENSE.md`](DATA_LICENSE.md)) ·
Commercial use, including by companies deploying for clinics, is welcome with credit ([`NOTICE`](NOTICE))
