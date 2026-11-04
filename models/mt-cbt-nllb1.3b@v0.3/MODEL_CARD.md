# mt-cbt-nllb1.3b@v0.3

Text-to-text translation between **spa_Latn / eng_Latn / fra_Latn / deu_Latn / ita_Latn / por_Latn** and **cbt_Latn** (Shawi), all directions. Base model `facebook/nllb-200-distilled-1.3B` (CC BY-NC 4.0 (non-commercial; fine-tuned weights inherit it)), method `seq2seq`, trained by recipe `cbt.mt.nllb-1.3b` on build `data-2026.11-six`.

## Served by the demo

Registered as **fast** for cbt_Latn in `models/registry.yaml`. The demo serves Muse Glimmer (open weights, on our own RTX 4090) by default and NLLB as the second choice, which visitors can pick: the project's claim is that it runs on an open-weight Muse model on our own hardware. Each card has its own scores; the demo's panel shows both side by side.

## License and credit

* Weights: base model license, CC BY-NC 4.0 (non-commercial; fine-tuned weights inherit it).
* Because the base model is non-commercial, these weights cannot be used commercially, including by a company deploying them for a clinic or a ministry. The Muse Glimmer translator (Apache 2.0 base) is the one for that.
* Data: cc-by-4.0 (`DATA_LICENSE.md`). Commercial use is allowed. Credit is required whenever the data or material adapted from it is shared, and requested for every model, product or service built on it: say it comes from Uyari and link the repository (`NOTICE`).

## Scores

chrF++ is the score Uyari optimizes and reports; BLEU is reported, not optimized. The retrieval floor returns the human translation of the most similar training sentence; a model that does not beat it is not worth serving.

Scored in process.

### Validation

| Direction | chrF++ | BLEU | Retrieval floor chrF++ | Segments |
|---|---|---|---|---|
| spa_Latn>cbt_Latn | 44.0 | 7.9 | 22.6 | 328 |
| cbt_Latn>spa_Latn | 46.0 | 21.6 | 22.8 | 328 |
| eng_Latn>cbt_Latn | 43.2 | 7.2 | 21.9 | 328 |
| cbt_Latn>eng_Latn | 46.3 | 24.6 | 22.7 | 328 |
| fra_Latn>cbt_Latn | 43.5 | 7.6 | 23.3 | 328 |
| cbt_Latn>fra_Latn | 46.9 | 23.1 | 23.4 | 328 |
| deu_Latn>cbt_Latn | 43.2 | 6.9 | 22.2 | 328 |
| cbt_Latn>deu_Latn | 44.9 | 20.0 | 23.6 | 328 |
| ita_Latn>cbt_Latn | 43.4 | 7.8 | 23.3 | 328 |
| cbt_Latn>ita_Latn | 45.2 | 20.2 | 23.0 | 328 |
| por_Latn>cbt_Latn | 43.7 | 7.9 | 22.6 | 328 |
| cbt_Latn>por_Latn | 45.0 | 19.8 | 22.4 | 328 |

### Test (scored once, at promotion)

| Direction | chrF++ | BLEU | Retrieval floor chrF++ | Segments |
|---|---|---|---|---|
| spa_Latn>cbt_Latn | 43.2 | 6.3 | 23.4 | 322 |
| cbt_Latn>spa_Latn | 45.8 | 22.3 | 22.0 | 322 |
| eng_Latn>cbt_Latn | 43.3 | 6.1 | 22.2 | 322 |
| cbt_Latn>eng_Latn | 45.5 | 24.0 | 22.0 | 322 |
| fra_Latn>cbt_Latn | 43.1 | 6.7 | 23.3 | 322 |
| cbt_Latn>fra_Latn | 46.3 | 22.7 | 22.4 | 322 |
| deu_Latn>cbt_Latn | 42.6 | 5.8 | 22.5 | 322 |
| cbt_Latn>deu_Latn | 44.1 | 19.7 | 22.6 | 322 |
| ita_Latn>cbt_Latn | 43.2 | 6.5 | 23.9 | 322 |
| cbt_Latn>ita_Latn | 44.7 | 20.2 | 22.4 | 322 |
| por_Latn>cbt_Latn | 43.3 | 6.4 | 22.8 | 322 |
| cbt_Latn>por_Latn | 43.0 | 17.5 | 21.6 | 322 |

Scored 2026-11-03T21:43:49+00:00.

**Human check:** no native-speaker adequacy rating has been done yet (planned: two speakers, 100 sentences). Learned metrics such as COMET are not used into Shawi until they can be validated against human judgments.

## Data

* Build `data-2026.11-six` (`builds/data-2026.11-six/MANIFEST.json`), mt table content hash `599e690f67c80b20`.
* 3575 human Shawi translations of 3575 Spanish chunks, from 3 contributions (provenance: human). Rows by split: {'test': 1932, 'train': 17550, 'validation': 1968} (spa_Latn, eng_Latn, fra_Latn, deu_Latn, ita_Latn, por_Latn).
* Contributions excluded (takedowns, revocations): none.
* Licenses on the rows: {'cc-by-4.0': 21450}.
* The Spanish side is synthetic, from a fixed design matrix (`primary/spa_Latn/matrix.yaml`). The first 10k chunks were generated in June 2026 with Claude Opus 4.8; generation has since moved to Meta: Muse Spark 1.3 Contributor produces the same cells at 3.3% of the cost (`reports/gen-comparison.md`), and Muse Glimmer on our own GPU at no API cost. Every chunk names the model that wrote it.
* eng_Latn, fra_Latn, deu_Latn, ita_Latn, por_Latn: machine-translated from spa_Latn with the same chunk ids (`primary/<lang>/chunks/translated/`, `origin=machine_translated`). The Shawi was translated from spa_Latn, and scores into eng_Latn, fra_Latn, deu_Latn, ita_Latn, por_Latn are measured against machine-translated references.
* Splits are assigned per paraphrase group, so no paraphrase of a test sentence is in training.

## Limitations

* About 3,600 sentence pairs, one variety (unspecified), four everyday domains. Health and civic language is thin (puente_civico has the fewest pairs).
* No Shawi recordings exist yet: this model is text only, and Shawi speech recognition in the demo is unmeasured.
* Output must be checked by a Shawi speaker before any use in health, legal or civic settings.

## Intended use

Communication access, education and language revitalization. Not for surveillance, targeting or profiling of speakers.

_Generated by `uyari` from `mt-cbt-nllb1.3b@v0.3/uyari_meta.json`, `scores.json` and the build manifest._
