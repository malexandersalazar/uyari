---
title: Uyari Translate · Shawi ↔ Spanish
emoji: 🗣️
colorFrom: yellow
colorTo: green
sdk: gradio
app_file: app.py
pinned: false
license: cc-by-nc-4.0
---

# Uyari Translate · Shawi ↔ Spanish (public CPU demo)

The always-on public version of the Uyari translator: NLLB-200 1.3B fine-tuned on about 3,600
human Shawi–Spanish translations. The full demo (Muse Glimmer by default, the closest human
pairs under every answer, Spanish voice input paid with the visitor's own Meta key) runs on the project's own GPU.

* Weights: NLLB-200 derivative, **CC BY-NC 4.0** (non-commercial), inherited from the base model.
* Data, scores and limitations: see the model card in the model repository and the Uyari repository.

## Publishing (maintainers)

The model repository is written by `uyari publish` (it refuses unconfirmed contribution licenses). It needs
`HF_TOKEN` in `.env`: first create the empty repositories on huggingface.co/new (`uyari-mt-cbt-nllb1.3b`,
`uyari-mt-cbt-glimmer30b-qlora`; private), then a **fine-grained** token with no user permissions and, under
repository permissions, Read and Write on those repositories only. A token limited to repositories cannot
create them, and a Read or Write preset token is either too weak or reaches every repository of the account.
Then:

```bash
uv run uyari publish --model mt-cbt-nllb1.3b@v0.3 --dry-run   # review runs/hub/<repo>/README.md
uv run uyari publish --model mt-cbt-nllb1.3b@v0.3             # private on creation; --public to skip that
hf upload --repo-type space <namespace>/uyari space .
# Space setting, if the namespace is not malexandersalazar: UYARI_MODEL_REPO=<namespace>/uyari-mt-cbt-nllb1.3b
```
