# models/

`models/<task>-<lang>-<base>@v<major>.<minor>/`: `uyari_meta.json` (what produced it), `recipe.yaml`,
`scores.json` (validation; test once), `eval/` (hypotheses), `MODEL_CARD.md` (written by `uyari`), and the
weights (`weights/` or `adapter/`, never in git: Hugging Face or the training machine).

`registry.yaml`: which model each task and language serves (`promoted`: the demo default, Glimmer;
`fast`: NLLB), with a history of every change and its reason.
