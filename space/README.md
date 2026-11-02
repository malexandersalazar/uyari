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

Confirm the contribution licenses first (the model card says whether they are set). Then:

```bash
huggingface-cli upload <org>/mt-cbt-spa-nllb1.3b models/mt-cbt-spa-nllb1.3b@v0.1/weights . 
huggingface-cli upload <org>/mt-cbt-spa-nllb1.3b models/mt-cbt-spa-nllb1.3b@v0.1/MODEL_CARD.md README.md
huggingface-cli upload --repo-type space <org>/uyari space .
# Space setting: UYARI_MODEL_REPO=<org>/mt-cbt-spa-nllb1.3b
```
