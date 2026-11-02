# Contributing to Uyari

[English](../en/README.md) · [Español](../es/README.md) · [Português](../pt/README.md) · [Français](../fr/README.md) · [Deutsch](../de/README.md) · [Italiano](../it/README.md) · [हिन्दी](../hi/README.md) · [ไทย](../th/README.md)

Uyari collects translations and recordings **made by people** so that Indigenous and other under-served
languages get open translation tools, in text and in speech, to and from the official language their speakers
need for health care, school and government. Any language can join. Each contribution is a folder; you do not
need to program.

Before contributing, read the rules on rights, consent and withdrawal: [governance.md](governance.md).

## What is needed now

Every language has a `NEEDS.md` that the system keeps up to date. Shawi (Peru) is the first language; its
list is [`languages/cbt_Latn/NEEDS.md`](../../languages/cbt_Latn/NEEDS.md). Today it asks for:

1. **Read recordings** of existing translations, by at least 3 adults, with their consent.
2. **More health and civil-registry sentences** translated into Shawi, checked by a second native reader.

**To add a new language**, open an issue with its name, its ISO 639-3 code, the official language its
speakers need, and who could act as its steward (a person who speaks it and reviews contributions).

## One contribution = one folder = one pull request

```
languages/<language>/contributions/<YYYY-MM>_<organization>_<nnnn>/
  contribution.yaml   who (pseudonym), when, how it was made, license, consent
  pairs.csv           chunk_id, text, replaces, translator_id, notes      (text)
  audio.csv           file, chunk_id, transcript, speaker_id, style, device, notes   (audio)
  speakers.csv        speaker_id, age_band, sex, first_language, consent_ref        (audio)
  wav/                16 or 48 kHz, mono, 16-bit, 1 to 20 seconds, one person per clip
```

* A folder has **one** language, **one** variety, **one** license and **one** consent reference.
* Translate from the official-language sentences in `primary/` (today: Spanish, `primary/spa_Latn/chunks/`).
  Each row of `pairs.csv` points at a `chunk_id`. Translate the whole sentence.
* Write the language's letters as its `language.yaml` says. In Shawi, for example, the glottal stop is **ʼ**
  (U+02BC); `uyari validate` shows where `'`, `’` or `´` must be converted.
* **No machine translation or synthetic voices presented as human work.** If a person corrected machine
  output, declare it in `contribution.yaml` (`human_post_edited_from_mt`).
* Adults only. No real names in the files: use `t-0001`, `s-0001`. The contributing organization keeps its
  own list.
* An accepted contribution is never edited: a correction is a new row in a later contribution with
  `replaces=<contribution>/<chunk_id>`.

## What happens to your pull request

1. **Validator** (automatic): format, codes, ids, apostrophes, audio.
2. **Gatekeeper** (automatic, Muse Glimmer on the project's own GPU): checks whether rows look like the
   official language instead of the Indigenous one, or were copied, and writes a row-by-row review on the
   pull request.
3. **The language steward** reads the review, spot-checks rows and decides. Health and informed-consent
   content always needs a second native reader.

After the merge, the **Trainer** rebuilds the data, trains, measures and opens a pull request with the results.

## Withdrawing data

A steward or community authority can ask for a contribution to leave all future training: it is one row in
[`contributing/takedowns.csv`](../takedowns.csv). Models already published cannot be recalled from people who
downloaded them; their cards are corrected and the next training run no longer uses that data. Details:
[governance.md](governance.md#withdrawal).

## Contributing code

```bash
uv sync --python 3.11 --extra dev --extra speech
uv run pytest -q
uv run ruff check src tests
git config core.hooksPath .githooks     # privacy check before every commit
```

GPU work runs on Ubuntu: [`docs/RUNBOOK-4090.md`](../../docs/RUNBOOK-4090.md). Every command that calls a
paid API has `--estimate` and uses your own key (`META_API_KEY`), and Indigenous-language data never goes to
a hosted model (`data_policy` in `config/llm.yaml`).
