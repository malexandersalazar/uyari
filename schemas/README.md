# schemas/

One JSON Schema per file type. `src/uyari/validate.py` applies them with `jsonschema`
(Draft 2020-12). CSV schemas carry the **column order** in the `x-columns` keyword: CSV
writers and the validator read it from there, so it is defined once.

| Schema | Validates | Notes |
|---|---|---|
| `chunk.json` | each row of `primary/<lang>/chunks/**/*.csv` | Keeps every design-matrix column of the corpus |
| `pair.json` | each row of `pairs.csv` | `translator_id` is pseudonymous (`t-0001`) |
| `audio.json` | each row of `audio.csv` | `file` is relative to the contribution folder |
| `speaker.json` | each row of `speakers.csv` | pseudonymous; adults only |
| `takedown.json` | each row of `contributing/takedowns.csv` | |
| `language.json` | `languages/<id>/language.yaml` | |
| `contribution.json` | `contribution.yaml` | `TODO` is schema-valid but fails `uyari validate --strict` |
| `review.json` | `review.yaml` | |
| `recipe.json` | `recipes/*.yaml` | |

CSV rules: UTF-8, LF line endings, header row, comma separator, minimal quoting. An empty
cell means unknown; the word `null` is never written.
