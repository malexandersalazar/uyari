"""Uyari on a free CPU Hugging Face Space: NLLB-200 1.3B fine-tuned for Shawi <-> Spanish.

Standalone (no Uyari package): the model repo holds the fine-tuned weights with the added
``cbt_Latn`` language token; this file reproduces the input format and the ``ʼ`` codec.
The full demo (Muse Glimmer by default, closest human pairs, Spanish voice with the visitor's own
Meta key) runs on the project's own GPU; this Space is the always-on public version.
"""

from __future__ import annotations

import os

import gradio as gr
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODEL_REPO = os.environ.get("UYARI_MODEL_REPO", "malexandersalazar/uyari-mt-cbt-nllb1.3b")
CODEC = {"ʼ": "'"}  # NLLB's SentencePiece has no U+02BC; mapped at the edges only
tok = AutoTokenizer.from_pretrained(MODEL_REPO)
model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_REPO, dtype=torch.float32).eval()
torch.set_num_threads(max(1, os.cpu_count() or 1))

DIRS = {"Spanish → Shawi": ("spa_Latn", "cbt_Latn"), "Shawi → Spanish": ("cbt_Latn", "spa_Latn")}


def translate(text: str, direction: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    src, tgt = DIRS[direction]
    if src == "cbt_Latn":
        for a, b in CODEC.items():
            text = text.replace(a, b)
    ids = [tok.convert_tokens_to_ids(src), *tok(text, add_special_tokens=False)["input_ids"][:254], tok.eos_token_id]
    with torch.no_grad():
        out = model.generate(input_ids=torch.tensor([ids]), forced_bos_token_id=tok.convert_tokens_to_ids(tgt),
                             num_beams=4, max_new_tokens=200)
    res = tok.decode(out[0], skip_special_tokens=True).strip()
    if tgt == "cbt_Latn":
        for a, b in CODEC.items():
            res = res.replace(b, a)
    return res


demo = gr.Interface(
    fn=translate,
    inputs=[gr.Textbox(label="Text", lines=3), gr.Radio(list(DIRS), value="Spanish → Shawi", label="Direction")],
    outputs=gr.Textbox(label="Translation", lines=3),
    title="Uyari Translate · Shawi ↔ Spanish",
    description=("Translation between Shawi (Chayahuita, Peru) and Spanish, trained on about 3,600 human "
                 "translations. Fast model (NLLB-200 1.3B, CPU; non-commercial license). Open source: "
                 "https://github.com/malexandersalazar/uyari. Have a Shawi speaker check any translation before "
                 "using it for health care or legal matters."),
    examples=[["El niño tiene fiebre desde ayer.", "Spanish → Shawi"],
              ["Mañana vamos a la chacra con mi hermano.", "Spanish → Shawi"]],
)

if __name__ == "__main__":
    demo.launch()
