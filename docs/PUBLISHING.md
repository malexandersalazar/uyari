# Publishing a model to Hugging Face (maintainers)

`uyari publish` writes one model repository per family, `malexandersalazar/uyari-<task>-<lang>-<base>`,
with the current version's weights or adapter and a README generated from its card, scores and build. It
refuses a model with unconfirmed contribution licenses or no test score.

Published: [`uyari-mt-cbt-nllb1.3b`](https://huggingface.co/malexandersalazar/uyari-mt-cbt-nllb1.3b) (v0.3)
and [`uyari-mt-cbt-glimmer30b-qlora`](https://huggingface.co/malexandersalazar/uyari-mt-cbt-glimmer30b-qlora)
(v0.4).

## Token

1. A new family (another language or base model) needs its repository first: create it empty on
   huggingface.co/new, with the name `--dry-run` prints, and choose its visibility there. A token limited to
   repositories cannot create them.
2. A **fine-grained** token with no user permissions and, under repository permissions, Read and Write on
   the `uyari-*` repositories only. A Read or Write preset token is either too weak or reaches every
   repository of the account.
3. `HF_TOKEN` in `.env` (gitignored). On a machine that runs CI jobs, remove it after publishing.

## Run

```bash
uv run uyari publish --model mt-cbt-nllb1.3b@v0.3 --dry-run   # review runs/hub/<repo>/README.md
uv run uyari publish --model mt-cbt-nllb1.3b@v0.3
```

A new version replaces the previous one in the same repository: one commit, tagged `vX.Y`, and files the
previous version had and this one does not are deleted. A published model cannot be recalled from people who
downloaded it ([governance](../contributing/en/governance.md)).
