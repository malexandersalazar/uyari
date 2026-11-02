# languages/

One folder per language: `languages/<iso639-3>_<Script>/` with `language.yaml`, `README.md`, `NEEDS.md`
(written by the Trainer) and `contributions/`.

`language.yaml` fields: `id`, `iso639_3`, `script`, `glottocode` (resolved in `registry/`), `display_name`
(endonym), `iso_name`, `primary` (the official language it translates from), `steward` (GitHub handle),
`community_authority`, `apostrophe` (canonical character), `apostrophe_variants` (mapped to it),
`training_orthography`, `trainer.recipes` (run on every qualifying merge), `trainer.min_growth`.

A new language needs two maintainers' approval. Validated by `uyari validate`.
