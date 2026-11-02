# primary/

The official-language sentences ("chunks") every language translates, one folder per primary language.

`primary/<lang>/chunks/**/<batch>.csv`, columns from `schemas/chunk.json` (order fixed):

| Column | Meaning |
|---|---|
| `chunk_id` | 32-hex id, never reused |
| `text` | 1–3 sentences read as one utterance; never edited after publication |
| `split` | `train`, `validation`, `test`; per paraphrase group; frozen once written (`uyari splits assign`) |
| `origin` | `imported`, `synthetic`, `human`, `machine_translated` |
| `status` | `active` or `deprecated` (deprecated chunks keep their translations but leave training) |
| `supersedes` | the chunk this one corrects |
| `domain_l1` to `palabras_ancla` | the design-matrix cell the generator used (see `spa_Latn/matrix.yaml`) |
| `source_custom_id` | the generation request, which is the paraphrase group |
| `source_batch_id`, `gen_model`, `provider`, `gen_date`, `prompt_version` | provenance of synthetic text |
| `regen_of` | the group this one regenerates (same cell, another model); inherits its split |

Written by `uyari ingest` and `uyari generate dedup`; read by `validate`, `build`, `generate`.

## Generating more Spanish

Generation runs on Meta models: **Muse Spark 1.3 Contributor** through the Meta Model API (about
$0.02 per 1,000 chunks, 3.3% of what the first batch cost; see `spa_Latn/README.md`) or **Muse Glimmer
30B** on our own GPU at no API cost. Every run prints its cost estimate before sending anything
(`uyari generate run --estimate`) and stops at its cap.
