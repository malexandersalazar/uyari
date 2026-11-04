# models/

`models/<task>-<lang>-<base>@v<major>.<minor>/`: `uyari_meta.json` (what produced it), `recipe.yaml`,
`scores.json` (validation; test once), `eval/` (hypotheses), `MODEL_CARD.md` (written by `uyari`), and the
weights (`weights/` or `adapter/`, never in git: Hugging Face or the training machine).

**Published weights** (both trained during the hackathon):
[`uyari-mt-cbt-glimmer30b-qlora`](https://huggingface.co/malexandersalazar/uyari-mt-cbt-glimmer30b-qlora)
(v0.4, Apache 2.0, the demo default, served on our RTX 4090 as a 4-bit GGUF through llama-server) and
[`uyari-mt-cbt-nllb1.3b`](https://huggingface.co/malexandersalazar/uyari-mt-cbt-nllb1.3b) (v0.3, CC BY-NC 4.0,
runs on a GPU or a CPU).

`registry.yaml`: which model each task and language serves (`promoted`: the demo default, Glimmer;
`fast`: NLLB), with a history of every change and its reason.
