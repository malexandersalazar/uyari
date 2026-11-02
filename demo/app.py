"""Uyari Translate: one Gradio page that serves only our own fine-tuned models.

* Shawi <-> Spanish today; Shawi <-> English as soon as a model trained on both is registered (the
  languages on the page come from the registered models, so nothing here changes).
* Muse Glimmer (open weights, local) by default once it is trained; NLLB as the fast model.
* Translates as you type. Under every answer: the three closest human translations (train split only).
* Optional Spanish voice input through Muse Voice Transcribe, **with the visitor's own Meta API key**
  (bring your own key). The server never uses its own key, so a public link cannot spend the owner's
  budget; the key is used for that one request and never stored or logged. Official language only:
  spoken Shawi is not supported yet (there are no Shawi recordings, see NEEDS.md).

Run:  uyari demo --no-share      (or: make demo, which first starts the Glimmer server)
"""

from __future__ import annotations

import os
import time
from functools import cache
from pathlib import Path

LANG = "cbt_Latn"
NAMES = {"spa_Latn": "Spanish", "eng_Latn": "English", "cbt_Latn": "Shawi"}
CODES = {v: k for k, v in NAMES.items()}
SLOTS = {"promoted": "Glimmer · open weights", "fast": "NLLB · fast"}
REPO_URL = "https://github.com/malexandersalazar/uyari"
MAX_CHARS = 1000
MAX_VOICE_SECONDS = 60  # protects the visitor's own budget: 60 s costs about $0.003
EXAMPLES = {
    "spa_Latn": ["¿Dónde está la posta de salud?", "Me duele la cabeza desde ayer y tengo fiebre.",
                 "Mañana vamos a la chacra con mis hijos."],
    "eng_Latn": ["Where is the health post?", "My head has hurt since yesterday and I have a fever.",
                 "Tomorrow we are going to the field with my children."],
}
CSS = """
.uy-head h1 {margin-bottom: 0} .uy-head p {margin-top: 4px; opacity: .8}
#uy-src textarea, #uy-out textarea {font-size: 1.15rem; line-height: 1.55}
#uy-swap {align-self: end; font-size: 1.3rem}
.uy-foot {font-size: .85rem; opacity: .8}
"""


def _models(paths) -> dict[str, dict]:
    """label -> {"ref": model name, "dirs": {(src, tgt), ...}, "build": tag} for the registered models."""
    from uyari.pipelines.mt.common import read_meta
    from uyari.pipelines.mt.infer import model_dir
    from uyari.registry import promoted

    out = {}
    for slot, label in SLOTS.items():
        ref = promoted(paths, "mt", LANG, slot)
        if not ref:
            continue
        meta = read_meta(model_dir(paths, ref))
        out[label] = {"ref": ref, "build": meta["build"],
                      "dirs": {tuple(d.split(">")) for d in meta["directions"]}}
    return out


@cache
def _translator(paths, ref: str):
    from uyari.pipelines.mt.infer import load_translator

    return load_translator(paths, ref)


@cache
def _index(paths, build: str, src: str, tgt: str):
    from uyari.pipelines.mt.retrieval import build_index

    official = tgt if src == LANG else src
    return build_index(paths, build, LANG, official, src, tgt)


def _pairs_md(pairs: list[dict], src: str, tgt: str) -> str:
    if not pairs:
        return ""
    rows = "\n".join(f"| {p['src']} | {p['tgt']} | {p['score']:.2f} |" for p in pairs)
    note = (" The English side is machine-translated from Spanish; the Shawi is human."
            if "eng_Latn" in (src, tgt) else "")
    return (f"**Closest human translations** from the training data.{note}\n\n"
            f"| {NAMES[src]} | {NAMES[tgt]} | similarity |\n|---|---|---|\n{rows}")


def _examples(paths, models: dict) -> list[list[str]]:
    """A few official-language examples per available source, plus two short human Shawi sentences."""
    from uyari.build import read_table

    srcs = {s for m in models.values() for s, _ in m["dirs"]}
    ex = [[t, NAMES[s]] for s in ("spa_Latn", "eng_Latn") if s in srcs for t in EXAMPLES[s]]
    if LANG in srcs:
        build = next(iter(models.values()))["build"]
        rows = sorted((r for r in read_table(paths, build, LANG, "mt") if r["split"] == "train"),
                      key=lambda r: r["chunk_id"])
        short = [r["tgt_text"] for r in rows if 5 <= len(r["tgt_text"].split()) <= 9][:2]
        ex += [[t, "Shawi"] for t in short]
    return ex


def transcribe_byok(paths, audio_path: str | None, api_key: str | None) -> tuple[str, str]:
    """(transcript, message). Uses only the key typed by the visitor; never the server's environment."""
    if not audio_path:
        return "", ""
    key = (api_key or "").strip()
    if not key:
        return "", "Enter your own Meta API key to use voice input. This server does not use its own key."
    from uyari.speech.transcribe import transcribe_file

    try:
        r = transcribe_file(paths, Path(audio_path), api_key=key, max_seconds=MAX_VOICE_SECONDS,
                            command="demo-byok")
    except Exception as e:  # noqa: BLE001 - show the reason, never the key
        msg = str(e).replace(key, "***")
        return "", f"Could not transcribe: {msg}"
    return r.get("text", ""), f"Transcribed with your key: {r['seconds']:.0f} s, about US$ {r['cost_usd']:.5f}."


def launch(paths, share: bool = True, voice: bool = True, port: int = 7860):
    import gradio as gr

    models = _models(paths)
    if not models:
        raise SystemExit("No registered models in models/registry.yaml. Train and register one first.")
    default_mode = SLOTS["promoted"] if SLOTS["promoted"] in models else next(iter(models))

    every = sorted({NAMES[x] for m in models.values() for d in m["dirs"] for x in d})

    def pick(mode: str, s_name: str | None, t_name: str | None) -> tuple[str, str]:
        """The requested pair if this model has it, else the closest pair it does have."""
        dirs = {(NAMES[a], NAMES[b]) for a, b in models[mode]["dirs"]}
        if (s_name, t_name) in dirs:
            return s_name, t_name
        same_src = sorted(b for a, b in dirs if a == s_name)
        if same_src:
            return s_name, same_src[0]
        return ("Spanish", "Shawi") if ("Spanish", "Shawi") in dirs else sorted(dirs)[0]

    def translate(text, s_name, t_name, mode):
        text = (text or "").strip()[:MAX_CHARS]
        if not text:
            return "", "", ""
        if s_name == t_name:
            return text, "Choose two different languages.", ""
        s, t = CODES[s_name], CODES[t_name]
        label = mode if (s, t) in models[mode]["dirs"] else next(
            (k for k, m in models.items() if (s, t) in m["dirs"]), None)
        if label is None:
            return "", f"{s_name} → {t_name} is not available yet.", ""
        ref = models[label]["ref"]
        t0 = time.time()
        try:
            out = _translator(paths, ref).translate([text], s, t)[0]
        except Exception as e:  # noqa: BLE001 - say what failed instead of a blank box
            return "", f"The model failed: {e}", ""
        info = f"<sub>{label} · `{ref}` · {time.time() - t0:.1f} s</sub>"
        pairs = _index(paths, models[label]["build"], s, t).closest_pairs(text, k=3)
        return out, info, _pairs_md(pairs, s, t)

    def on_source(s_name, t_name, mode, text):
        s_name, t_name = pick(mode, s_name, t_name)
        return (gr.update(value=t_name), *translate(text, s_name, t_name, mode))

    def on_mode(mode, s_name, t_name, text):
        s_name, t_name = pick(mode, s_name, t_name)
        return gr.update(value=s_name), gr.update(value=t_name), *translate(text, s_name, t_name, mode)

    def on_swap(s_name, t_name, text, out, mode):
        new_text = out or text
        o, i, p = translate(new_text, t_name, s_name, mode)
        return gr.update(value=t_name), gr.update(value=s_name), new_text, o, i, p

    def from_voice(audio_path, api_key, t_name, mode):
        heard, note = transcribe_byok(paths, audio_path, api_key)
        if not heard:
            return gr.update(), gr.update(), gr.update(), "", note, ""
        s_name, t_name = pick(mode, "Spanish", t_name)
        out, info, pairs = translate(heard, s_name, t_name, mode)
        return gr.update(value=s_name), gr.update(value=t_name), heard, out, f"{note}<br>{info}", pairs

    s0, t0 = pick(default_mode, "Spanish", "Shawi")
    translate("Hola", s0, t0, default_mode)  # warm up: load the model and the index before the first visitor
    english_ready = any(("eng_Latn", LANG) in m["dirs"] for m in models.values())

    with gr.Blocks(title="Uyari Translate · Shawi", analytics_enabled=False) as demo:
        gr.HTML("<div class='uy-head'><h1>Uyari Translate</h1><p>Shawi (Chayahuita, Peru) ↔ Spanish"
                + (" and English" if english_ready else "") + ", trained on human translations. This server runs "
                "only our own fine-tuned open models.</p></div>")
        with gr.Row(equal_height=True):
            src_lang = gr.Dropdown(every, value=s0, label="From", scale=5)
            swap = gr.Button("⇄", elem_id="uy-swap", scale=1, min_width=56)
            tgt_lang = gr.Dropdown(every, value=t0, label="To", scale=5)
        with gr.Row(equal_height=True):
            src = gr.Textbox(lines=6, max_length=MAX_CHARS, show_label=False, elem_id="uy-src", autofocus=True,
                             placeholder="Type or paste text. It translates as you type.")
            out = gr.Textbox(lines=6, show_label=False, interactive=False, elem_id="uy-out", buttons=["copy"],
                             placeholder="Translation")
        with gr.Row():
            mode = gr.Radio(list(models), value=default_mode, label="Model", scale=4)
            btn = gr.Button("Translate", variant="primary", scale=1)
        info = gr.Markdown()
        pairs = gr.Markdown()
        gr.Examples(_examples(paths, models), inputs=[src, src_lang], label="Try an example")
        if voice:
            with gr.Accordion("Speak Spanish (optional, uses your own Meta API key)", open=False):
                gr.Markdown("Speech is transcribed by **Muse Voice Transcribe** with **your** Meta API key, so the "
                            f"cost goes to your account (US$ 0.18 per audio hour; at most {MAX_VOICE_SECONDS} s per "
                            "recording). The key is used for that one request and is never stored or logged. Spanish "
                            "only: Shawi audio is never sent to outside services.")
                api_key = gr.Textbox(label="Your Meta API key", type="password",
                                     placeholder="Used for this request only")
                audio = gr.Audio(sources=["microphone"], type="filepath", label="Microphone (Spanish)")
                audio.stop_recording(from_voice, [audio, api_key, tgt_lang, mode],
                                     [src_lang, tgt_lang, src, out, info, pairs])
        gr.Markdown(
            f"<div class='uy-foot'>Open source: models, data and code at <a href='{REPO_URL}'>{REPO_URL}</a>. "
            "Data CC BY 4.0 · NLLB weights CC BY-NC 4.0 (non-commercial) · Muse Glimmer Apache 2.0.<br>"
            "Machine translation can be wrong: have a Shawi speaker check anything used for health care or legal "
            "matters. Spoken Shawi is not supported yet (there are no Shawi recordings)."
            + ("" if english_ready else " English ↔ Shawi is being trained next.") + "</div>")

        args = [src, src_lang, tgt_lang, mode]
        live = {"trigger_mode": "always_last", "show_progress": "hidden", "concurrency_id": "mt"}
        src.change(translate, args, [out, info, pairs], **live)
        src.submit(translate, args, [out, info, pairs], concurrency_id="mt")
        btn.click(translate, args, [out, info, pairs], concurrency_id="mt")
        src_lang.change(on_source, [src_lang, tgt_lang, mode, src], [tgt_lang, out, info, pairs], **live)
        tgt_lang.change(translate, args, [out, info, pairs], **live)
        mode.change(on_mode, [mode, src_lang, tgt_lang, src], [src_lang, tgt_lang, out, info, pairs], **live)
        swap.click(on_swap, [src_lang, tgt_lang, src, out, mode], [src_lang, tgt_lang, src, out, info, pairs],
                   concurrency_id="mt")
    demo.queue(default_concurrency_limit=1).launch(
        share=share, server_name=os.environ.get("UYARI_DEMO_HOST", "0.0.0.0"), server_port=port,
        theme=gr.themes.Soft(), css=CSS)
