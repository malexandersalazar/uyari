# Uyari methodology

**English** · [Español](docs/es/METHODOLOGY.md) · [Português](docs/pt/METHODOLOGY.md) · [Français](docs/fr/METHODOLOGY.md) · [Deutsch](docs/de/METHODOLOGY.md) · [Italiano](docs/it/METHODOLOGY.md) · [हिन्दी](docs/hi/METHODOLOGY.md) · [ไทย](docs/th/METHODOLOGY.md)

Uyari is an open data structure and training toolkit that turns a community's own translations and
recordings into models between an Indigenous or other under-served language and the official language its
speakers need. A language is added as a folder; data is added as a folder inside it; nobody changes code.
Meta's models are the default stack.

The reasons behind structural choices are in [`docs/decisions/`](docs/decisions/). The problem this
addresses, with figures and sources, is in [`PROBLEM.md`](PROBLEM.md).

## 1. Goal and scope

**Five use cases per language pair:**

| # | Use case | Models |
|---|---|---|
| 1 | Indigenous text → official-language text | MT |
| 2 | Official-language text → Indigenous text | MT |
| 3 | Indigenous speech → official-language speech | ASR → MT → TTS |
| 4 | Official-language speech → Indigenous speech | ASR → MT → TTS |
| 5 | Indigenous speech → Indigenous text (speech-to-text) | ASR |

**The first pair is Shawi ↔ Spanish** (`cbt_Latn`, glottocode `chay1248`; Peru). It is first because the work
had started there, with maternal health ([`PROBLEM.md` §6](PROBLEM.md#6-the-first-case-shawi--spanish-peru)),
not because anything is specific to it. What exists for it:

* 11,977 Spanish primary chunks (synthetic, from the design matrix in `primary/spa_Latn/matrix.yaml`).
* 3,578 human Shawi translations of 3,575 of them, commissioned work, as three contributions.
* The same 11,977 chunks in English, machine-translated from the Spanish with the same chunk ids, so every
  Shawi translation also pairs with English.
* No Shawi recordings. The audio path (validator, build, ASR/TTS pipelines) is exercised on a labelled
  synthetic fixture (`qaa_Latn`), and `NEEDS.md` asks for recordings.

| In scope | Out of scope |
|---|---|
| Any language with a written form; the format accepts every ISO 15924 script (only Latin script is tested so far) | Speech-only languages (the format stores untranscribed audio; no pipeline uses it yet) |
| Official languages as primaries: Spanish (generated) and English (machine-translated from it); others (Portuguese, French, Hindi, Thai, …) by the same mechanism | Dialect research: varieties are a label on a contribution |
| Human translations and recordings; machine-written text only on the official-language side, labelled | Machine translation presented as human work |
| A language joins when a community brings data and a steward | A production inference service; the demo is a demo |

## 2. Principles

1. **The contribution is the unit.** Data is filed as contribution folders, each with its own provenance,
   license and consent. Pooling happens only in builds and recipes, never by moving files.
2. **Stable IDs, never positions.** Chunk ids are 32-hex and never reused (translators work from these same
   ids). Files can be split or sorted without breaking a reference.
3. **Merged contributions are immutable.** A correction is a new contribution that says what it replaces.
4. **Humans translate and speak; machines may only draft the official-language side, and say so.** Every
   synthetic chunk names the model that wrote it (`gen_model`, `provider`, `prompt_version`).
5. **Consent and withdrawal are data.** Every contribution carries a license and a consent reference; a
   withdrawal is a CSV row that the next build applies.
6. **Standard codes, plain names, reproducible builds.** Languages are keyed by ISO 639-3 plus script
   (`cbt_Latn`), Meta's model tag. The same build tag produces the same content hash on any OS.
7. **Community data never leaves our hardware for a model that may train on it.** Every model declares a
   `data_policy`; the code refuses Indigenous-language text to a hosted Contributor-tier model.
8. **Paid APIs are optional and paid by whoever uses them.** The CLI uses your own key; the demo asks each
   visitor for theirs and otherwise runs only the fine-tuned open models.

**One consequence.** The split is a property of the primary chunk, shared by every language, and is assigned
per **paraphrase group** (the ~10 near-paraphrases one generation request produced), so no model can see a
paraphrase of a test sentence in training.

## 3. Data model

| Entity | Key | Must have |
|---|---|---|
| Primary chunk | `chunk_id` (32-hex) | text, split, origin, status; every design-matrix column the generator recorded |
| Language | `<iso639-3>_<Script>` | glottocode, display name, steward, community authority, canonical apostrophe |
| Contribution | `<YYYY-MM>_<org>_<nnnn>` | contributor (pseudonymous), license, consent, provenance, collection dates, variety |
| Pair row | (contribution, chunk_id) | text, translator_id (pseudonymous); `replaces` optional |
| Audio row | (contribution, file) | speaker, style; chunk_id or transcript |
| Speaker | (contribution, speaker_id) | age band, consent reference |
| Build | `data-YYYY.MM[-rN]` | one table per task per language, manifest with file and content hashes |
| Recipe | file | build, language, base model, method, hyperparameters |
| Model card | `name@vX.Y` | build, recipe, base model license, validation scores vs the retrieval floor, test once |

Audio rows: `chunk_id` set and `transcript` empty means the speaker read that contribution's translation of the
chunk; `chunk_id` empty with `transcript` set is spontaneous speech (split by speaker); both empty is stored
and unused. Closed vocabularies are in `schemas/`; the validator rejects any other value.

## 4. Primary corpus

The primary corpus is the set of official-language sentences that every language translates. Today it is
Spanish (`primary/spa_Latn/`).

**What we have.** The first batch, `2026-06_opus48_0001.csv`: 10,000 chunks generated in June 2026 with
Claude Opus 4.8, covering 4 of the matrix's 15 domains and 37 micro-scenarios. Every row keeps its matrix
cell (domain, micro-scenario, register, communicative act, tense, polarity, person, length bucket, speaker
profile, tone, connected discourse, anchor words, `source_custom_id`).

**Generating more, on Meta models.** `uyari generate` keeps that batch's matrix, its round-robin over
tense/polarity/person, anchor words, plan on disk with per-unit status and idempotent re-runs, `custom_id` group
key, parsing, validation and deduplication, and **the identical prompt** (one pinned `prompt_version`), so a
comparison measures models, not prompt edits. Regenerating 200 cells with Muse Spark 1.3 Contributor cost
3.3% as much per 1,000 chunks, with 100% well-formed responses and slightly more varied text
(`reports/gen-comparison.md`); Muse Glimmer on our own GPU does it with no API cost. Before sending,
`--estimate` prints the cost; each run is capped; every call is in the ledger.

**Post-processing.** NFC and whitespace; 1–120 words and the unit's length bucket ±30%; banned urban terms; a
language check; exact deduplication and embedding near-duplicates (cosine 0.92, blocked by domain) against the
whole primary; a 2% human spot read per batch (`uyari primary sample`), a batch over 5% rejects withdrawn.

**Splits.** First assignment: validation and test hold ~300 translated chunks each, as whole paraphrase groups
from translated groups, stratified by domain, ordered by hash. New groups: a group that regenerates an existing
cell inherits its split; others by hash (5% / 5%). Frozen once written.

**More primaries.** English (`primary/eng_Latn`) shares chunk ids with the Spanish: `uyari primary translate`
machine-translated all 11,977 chunks with Muse Spark 1.3 Contributor for US$ 0.19, labelled
`origin=machine_translated`, with split, domain and paraphrase group copied. Other official languages are
added the same way.

## 5. Adding a language

A folder `languages/<iso639-3>_<Script>/` with `language.yaml` and `README.md`. The validator accepts it when every
code resolves in `registry/` (ISO 639-3 local-use `qaa`–`qtz` is accepted) and a steward is named. Fields:
`id, iso639_3, script, glottocode, display_name, iso_name, primary, steward, community_authority, apostrophe,
apostrophe_variants, training_orthography, trainer`. Letters that tools often mangle are declared once: in
Shawi the glottal stop is a letter, canonical `ʼ` (U+02BC), and the validator lists variant characters with
the fix.

## 6. Contributing

See [`contributing/`](contributing/) (English, Spanish, Portuguese, French, German, Italian, Hindi, Thai). One
folder, one pull request, one language, one variety, one license, one consent reference: `contribution.yaml`,
`pairs.csv`, `audio.csv`, `speakers.csv`, `wav/`. Partial contributions are normal; the build derives what a
folder contains from which files exist.

## 7. Review

Three gates: the **validator** (CI, every PR), the **Gatekeeper** (Muse Glimmer on our own GPU; a written review
in the steward's working language, Spanish for Shawi), and the **steward** (a person who speaks the language).
The Gatekeeper catches validator failures, official-language text pasted in the Indigenous-language column,
rows copied from accepted contributions and text unlike accepted pairs; it recommends merge, return or
escalate (health and consent domains always escalate). It does **not** detect machine translation;
contributors attest that no machine output is submitted as human work.

## 8. Builds

`uyari build --tag data-YYYY.MM` reads every contribution, applies `replaces`, skips revoked contributions and
withdrawals effective on or before `--as-of`, normalizes text, joins the split and domain, and writes
`builds/<tag>/<lang>/{mt,asr,tts}.parquet` (train + validation) and `*.test.parquet` (test), plus
`MANIFEST.json`: git commit, contributions included and excluded with reasons, rows excluded with reasons, rows
per split, licenses, and per table a file `sha256` and a canonical `content_sha256`. Missing data is derived,
never declared. Parquet is not in git; the tag rebuilds it.

## 9. Agents

| Agent | Trigger | Decides | Writes |
|---|---|---|---|
| **Gatekeeper** | A PR into `contributions/` | merge / return / escalate (recommendation only) | A review on the PR, a draft `review.yaml` |
| **Trainer** | A merge into `main` (self-hosted GPU runner), or by hand | Whether a build is worth cutting (new language or ≥10% more pairs); promote only if every direction beats the retrieval floor **and**, on the directions both share, validation chrF++ improves ≥0.5 over the incumbent re-scored on the same build (or the candidate adds directions and loses no more than 0.5) | Build manifest, model card, `scores.json`, `models/registry.yaml`, `NEEDS.md`, a pull request |
| Interpreter | (after the MVP) | | |

Guardrails: no agent merges; no agent reads the test split before a promotion; test is scored once per model
version; every decision is a line on the PR or the card with the numbers that produced it.

## 10. Training and evaluation

Recipes in `recipes/` are the only configuration. One model per backend covers every official language
paired with the Indigenous one (today Spanish and English: four directions), and each direction is scored
on its own language pair. Reference models for text:

* **Muse Glimmer 30B, QLoRA** (Unsloth, 4-bit, r=16, max length 512, batch 1 × 16, 3 epochs): the headline
  model, on our RTX 4090.
* **NLLB-200 1.3B, full fine-tune** (a new language token initialised from a related language; `quy_Latn` for
  Shawi): the fast baseline; also trains on a 12 GB RTX 3060 in pure bf16.
* **Retrieval floor:** the human translation of the nearest training sentence; local, free.

The demo serves only these fine-tuned models: Glimmer by default once trained, NLLB as fast mode; the cards
say which scores higher.

| Task | Score | Human check |
|---|---|---|
| Text to text | chrF++ per direction (BLEU reported, not optimized) | Two native speakers rate 100 sentences when available |
| Speech to text | CER (WER reported) | Transcript acceptability on 50 clips |
| Text to speech | Round-trip CER through ASR | Naturalness 1–5 |
| Speech to speech | chrF++ of the output after ASR | Task success on a scripted dialogue |

COMET and other learned metrics are not trusted into Indigenous languages until validated against human judgments.

## 11. Governance

Code: Apache 2.0. Data: per contribution (default CC BY 4.0; CC BY-SA, CC BY-NC or a community license by the
community's choice), carried on every build row. Consent is collective (community authority) and individual
(each speaker and translator); withdrawals are rows in `contributing/takedowns.csv`. Roles, licenses, consent
templates and protections, in eight languages: [`contributing/<language>/governance.md`](contributing/en/governance.md).

## 12. Money

* **Local by default.** Training, evaluation, the Gatekeeper and the demo run on our own GPUs at no API cost.
* **Bring your own key.** Anything that calls a paid API uses the caller's own Meta key: the CLI reads
  `META_API_KEY`; the demo asks visitors for theirs, uses it for that request only and never stores it, and
  never falls back to the server's key.
* **Estimate before spending.** Prices live in `config/llm.yaml`; every LLM command estimates its cost before
  sending (tiktoken approximation × 1.2), every call's real usage is in `.uyari/ledger.jsonl`, and each run has
  a hard cap (`generate` $1, `transcribe` $2, everything else $0 because it runs locally). The project's own
  development budget for hosted APIs is USD 150.
