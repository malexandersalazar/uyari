"""Uyari Translate: one Gradio page that serves only our own fine-tuned models.

Uyari is a working project; this page is its first step toward speech and text translation between Indigenous
and official languages, starting with Shawi.

* Three tabs, each one thing: your language -> Shawi (with Listen), Shawi -> your language, and speech
  (an official language in, Shawi out). Shawi is always on one side: Spanish <-> English and the like are
  refused (``route``). The official languages offered (Spanish, English, French, German, Italian, Portuguese)
  come from the registered models' directions.
* Muse Glimmer (open weights, served on this machine by ``uyari serve``, which the page starts when needed) by
  default; NLLB as the second choice, on a Model switch in every tab.
* Translates as you type. Under every answer: the three closest human translations (train split only).
* Listen: Shawi output read aloud by Meta's MMS voice (open weights, on this server), through the spelling
  converter in ``languages/cbt_Latn/tts.yaml``. Made on click, in its own queue, so translation never waits.
* Optional voice input in the official languages Muse Voice Transcribe takes (Spanish, English, French,
  Portuguese), **with the visitor's own Meta API key** (bring your own key): record -> transcript -> Shawi text
  -> Shawi audio, in one action. A spoken language no registered model takes into Shawi goes into Spanish first
  with Muse Spark (official-language text only, same key). The server never uses its own key, so a public link cannot spend the owner's budget; the key is used
  for that one request and never stored or logged. Shawi text and audio never leave this server. Spoken Shawi
  input comes later (there are no Shawi recordings yet, see NEEDS.md).

Run:  uyari demo --no-share      (or: make demo, with a public share link)
"""

from __future__ import annotations

import html
import json
import os
import re
import time
from functools import cache
from pathlib import Path

LANG = "cbt_Latn"
NAMES = {"spa_Latn": "Spanish", "eng_Latn": "English", "fra_Latn": "French", "deu_Latn": "German",
         "ita_Latn": "Italian", "por_Latn": "Portuguese", "cbt_Latn": "Shawi"}
CODES = {v: k for k, v in NAMES.items()}
# The language hint for Muse Voice Transcribe: the languages it takes (speech/transcribe.py), so voice input
# offers these only.
ISO1 = {"spa_Latn": "es", "eng_Latn": "en", "fra_Latn": "fr", "por_Latn": "pt"}
# Every translation: Shawi on one side, one of these on the other.
OFFICIALS = ("spa_Latn", "eng_Latn", "fra_Latn", "deu_Latn", "ita_Latn", "por_Latn")
SLOTS = {"promoted": "Glimmer · open weights", "fast": "NLLB · fast"}
REPO_URL = "https://github.com/malexandersalazar/uyari"
LINKEDIN_URL = "https://www.linkedin.com/in/malexandersalazar/"
HF_GLMmer30B_URL = "https://huggingface.co/malexandersalazar/uyari-mt-cbt-glimmer30b-qlora"
HF_NLLB_URL = "https://huggingface.co/malexandersalazar/uyari-mt-cbt-nllb1.3b"
MAX_CHARS = 1000
MAX_VOICE_SECONDS = 60  # protects the visitor's own budget: 60 s costs about $0.003
# Short and plain; general advice only (no doses, no legal deadlines). Shown for the selected language.
EXAMPLES = {
    "spa_Latn": ["Lávate las manos con agua y jabón antes de comer.",
                 "Si tu hijo tiene fiebre, llévalo a la posta de salud.",
                 "Puedes pedir ayuda en tu propia lengua.",
                 "Todos los niños tienen derecho a ir a la escuela."],
    "eng_Latn": ["Wash your hands with soap and water before eating.",
                 "If your child has a fever, take them to the health post.",
                 "You can ask for help in your own language.",
                 "Every child has the right to go to school."],
    "fra_Latn": ["Lave-toi les mains avec de l'eau et du savon avant de manger.",
                 "Si ton enfant a de la fièvre, emmène-le au poste de santé.",
                 "Tu peux demander de l'aide dans ta propre langue.",
                 "Tous les enfants ont le droit d'aller à l'école."],
    "deu_Latn": ["Wasch dir vor dem Essen die Hände mit Wasser und Seife.",
                 "Wenn dein Kind Fieber hat, bring es zur Gesundheitsstation.",
                 "Du kannst in deiner eigenen Sprache um Hilfe bitten.",
                 "Alle Kinder haben das Recht, zur Schule zu gehen."],
    "ita_Latn": ["Lavati le mani con acqua e sapone prima di mangiare.",
                 "Se tuo figlio ha la febbre, portalo al presidio sanitario.",
                 "Puoi chiedere aiuto nella tua lingua.",
                 "Tutti i bambini hanno il diritto di andare a scuola."],
    "por_Latn": ["Lave as mãos com água e sabão antes de comer.",
                 "Se seu filho estiver com febre, leve-o ao posto de saúde.",
                 "Você pode pedir ajuda na sua própria língua.",
                 "Todas as crianças têm o direito de ir à escola."],
}
VOICE_NOTE = "Meta MMS voice, trained on Bible readings; our spelling is converted automatically."
LEAD = ("Uyari is a working project. This demo is its first step toward speech and text translation between "
        "Indigenous and official languages, starting with Shawi.")
# Gradio's player autoplays a new clip, but not the same clip twice, and emptying it before a new clip leaves a
# dead element that never plays. So the player is hidden rather than emptied when the text changes (it is shown
# only while it holds the current text's audio), and Listen on a shown player restarts it in the browser with
# the player's own Play button.
REPLAY_JS = """() => {
  const box = document.getElementById('%s');
  const play = box && box.offsetParent !== null && box.querySelector('button[aria-label="Play"]');
  if (play) play.click();
}"""
# Meta "Astryx" tokens (light / dark), mapped onto Gradio's theme variables. Custom CSS loads after the
# theme CSS so these mappings win; `:root:root` also out-specifies the theme's `:root`. Dark values ride on
# Gradio's `.dark` class (on by default when the OS prefers dark), so the page tracks the system theme; the
# mappings are repeated there because `var()` resolves against the element that declares them. Blue is used
# only for actions, links and focus; everything else stays neutral gray.
CSS = """
:root:root {
  --uy-bg: #F2F4F6; --uy-surface: #FFFFFF; --uy-text: #111112; --uy-text-2: #666A72;
  --uy-text-disabled: #9FA4AB; --uy-accent: #0064E0; --uy-on-accent: #FFFFFF;
  --uy-accent-muted: #0082FB33; --uy-border: #DFE2E5;
  --uy-ease: cubic-bezier(.24, 1, .4, 1); --uy-t-fast: .175s;
  --uy-shadow-low: 0 1px 1px rgba(0,0,0,.10), 0 2px 8px rgba(5,54,89,.10);
  --uy-shadow-med: 0 1px 2px rgba(0,0,0,.10), 0 2px 12px rgba(5,54,89,.12);
  --uy-ring-selected: inset 0 0 0 2px #0171E380;
  --background-fill-primary: var(--uy-bg); --background-fill-secondary: var(--uy-bg);
  --body-text-color: var(--uy-text); --body-text-color-subdued: var(--uy-text-2);
  --block-background-fill: var(--uy-surface); --block-border-color: var(--uy-border);
  --block-border-width: 1px; --block-radius: 12px; --block-shadow: none;
  --container-radius: 12px; --panel-background-fill: var(--uy-bg);
  --border-color-primary: var(--uy-border); --border-color-accent: var(--uy-accent);
  --color-accent: var(--uy-accent); --color-accent-soft: var(--uy-accent-muted);
  --link-text-color: var(--uy-accent); --link-text-color-active: var(--uy-accent);
  --link-text-color-hover: var(--uy-accent); --link-text-color-visited: var(--uy-accent);
  --block-label-text-color: var(--uy-text); --block-title-text-color: var(--uy-text);
  --block-info-text-color: var(--uy-text-2);
  --input-background-fill: var(--uy-surface); --input-border-color: var(--uy-border);
  --input-border-width: 1px; --input-radius: 8px; --input-shadow: none;
  --input-shadow-focus: var(--uy-ring-selected); --input-border-color-focus: var(--uy-accent);
  --input-placeholder-color: var(--uy-text-disabled);
  --shadow-drop: var(--uy-shadow-low); --shadow-drop-lg: var(--uy-shadow-med);
  --button-primary-background-fill: var(--uy-accent); --button-primary-border-color: var(--uy-accent);
  --button-primary-background-fill-hover: #005FD5; --button-primary-border-color-hover: #005FD5;
  --button-primary-text-color: var(--uy-on-accent);
  --button-secondary-background-fill: var(--uy-surface); --button-secondary-background-fill-hover: #F2F2F2;
  --button-secondary-border-color: var(--uy-border); --button-secondary-border-color-hover: var(--uy-border);
  --button-secondary-text-color: var(--uy-text);
  --button-large-radius: 9999px; --button-medium-radius: 9999px; --button-small-radius: 9999px;
  --button-small-text-weight: 600;
  --button-transition: background-color var(--uy-t-fast) var(--uy-ease), border-color var(--uy-t-fast) var(--uy-ease), box-shadow var(--uy-t-fast) var(--uy-ease);
}
:root.dark, :root .dark {
  --uy-bg: #111112; --uy-surface: #1F1F22; --uy-text: #F2F4F6; --uy-text-2: #9FA4AB;
  --uy-text-disabled: #666A72; --uy-accent: #2694FE; --uy-on-accent: #FFFFFF; --uy-link: #3E9EFB;
  --uy-accent-muted: #0082FB3F; --uy-border: #494D53;
  --uy-shadow-low: 0 1px 1px rgba(0,0,0,.20), 0 2px 8px rgba(0,0,0,.20);
  --uy-shadow-med: 0 1px 2px rgba(0,0,0,.20), 0 2px 12px rgba(0,0,0,.22);
  --background-fill-primary: var(--uy-bg); --background-fill-secondary: var(--uy-bg);
  --body-text-color: var(--uy-text); --body-text-color-subdued: var(--uy-text-2);
  --block-background-fill: var(--uy-surface); --block-border-color: var(--uy-border);
  --block-border-width: 1px; --block-radius: 12px; --block-shadow: none;
  --container-radius: 12px; --panel-background-fill: var(--uy-bg);
  --border-color-primary: var(--uy-border); --border-color-accent: var(--uy-accent);
  --color-accent: var(--uy-accent); --color-accent-soft: var(--uy-accent-muted);
  --link-text-color: var(--uy-link); --link-text-color-active: var(--uy-link);
  --link-text-color-hover: var(--uy-link); --link-text-color-visited: var(--uy-link);
  --block-label-text-color: var(--uy-text); --block-title-text-color: var(--uy-text);
  --block-info-text-color: var(--uy-text-2);
  --input-background-fill: var(--uy-surface); --input-border-color: var(--uy-border);
  --input-border-width: 1px; --input-radius: 8px; --input-shadow: none;
  --input-shadow-focus: var(--uy-ring-selected); --input-border-color-focus: var(--uy-accent);
  --input-placeholder-color: var(--uy-text-disabled);
  --shadow-drop: var(--uy-shadow-low); --shadow-drop-lg: var(--uy-shadow-med);
  --button-primary-background-fill: var(--uy-accent); --button-primary-border-color: var(--uy-accent);
  --button-primary-background-fill-hover: #3C9FFE; --button-primary-border-color-hover: #3C9FFE;
  --button-primary-text-color: var(--uy-on-accent);
  --button-secondary-background-fill: var(--uy-surface); --button-secondary-background-fill-hover: #353538;
  --button-secondary-border-color: var(--uy-border); --button-secondary-border-color-hover: var(--uy-border);
  --button-secondary-text-color: var(--uy-text);
  --button-large-radius: 9999px; --button-medium-radius: 9999px; --button-small-radius: 9999px;
  --button-small-text-weight: 600;
  --button-transition: background-color var(--uy-t-fast) var(--uy-ease), border-color var(--uy-t-fast) var(--uy-ease), box-shadow var(--uy-t-fast) var(--uy-ease);
}
a {color: var(--uy-accent); text-decoration: none}
a:hover {text-decoration: underline}
table td, table th {border-color: var(--uy-border)}
:focus-visible {outline: 2px solid var(--uy-accent); outline-offset: 3px}
.uy-head h1 {margin-bottom: 0; font-size: 1.25rem; font-weight: 600; line-height: 1.25}
.uy-head p {margin-top: 4px; opacity: .8} .uy-head p.uy-lead {opacity: 1}
.uy-big textarea {font-size: 1.15rem; line-height: 1.55}
.uy-arrow {font-size: 1.8rem !important; line-height: 1; text-align: center; align-self: center; opacity: .6}
.uy-foot, .uy-small {font-size: .85rem; opacity: .8}
.uy-foot {overflow-wrap: anywhere; line-height: 1.5}
.uy-pairs table {font-size: .8rem}
.uy-pairs th {color: var(--uy-text-2); font-weight: 600}
.uy-pairs td, .uy-pairs th {border-left: none; border-right: none; padding: 6px 10px}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {transition-duration: .01ms !important; animation-duration: .01ms !important}
}
"""


def _theme():
    """The Gradio theme: a Meta-blue ramp (Soft's default is indigo) and the spec's font stacks. Exact
    surfaces come from CSS; the ramp keeps everything CSS does not pin (sliders, checkboxes) in the same
    blue. Gradio is imported here so `import app` stays light where Gradio is not installed (CI)."""
    import gradio as gr

    blue = gr.themes.Color(c50="#EAF3FF", c100="#D6E8FF", c200="#B0D0FF", c300="#7DB1FB", c400="#3E9EFB",
                           c500="#1287FA", c600="#0064E0", c700="#0051B5", c800="#06438F", c900="#0A3771",
                           c950="#072747", name="uyari-blue")
    font = ("Optimistic AI VF", "Optimistic", "system-ui", "-apple-system", "Segoe UI", "Helvetica", "Arial",
            "sans-serif")
    font_mono = ("SF Mono", "Monaco", "Consolas", "monospace")
    return gr.themes.Soft(primary_hue=blue, secondary_hue=blue, font=font, font_mono=font_mono)


def _models(paths) -> dict[str, dict]:
    """label -> {"ref", "dir", "build", "base", "dirs": {(src, tgt), ...}} for the registered models."""
    from uyari.pipelines.mt.common import read_meta
    from uyari.pipelines.mt.infer import model_dir
    from uyari.registry import promoted

    out = {}
    for slot, label in SLOTS.items():
        ref = promoted(paths, "mt", LANG, slot)
        if not ref:
            continue
        d = model_dir(paths, ref)
        meta = read_meta(d)
        if meta["kind"] == "causal_lora" and not _served():
            print(f"{ref} is registered but its server is not running, so the page leaves it out: start it with "
                  "`make serve` (in process it does not fit the 4090).")
            continue
        out[label] = {"ref": ref, "dir": d, "slot": slot, "build": meta["build"], "base": meta.get("base_model", ""),
                      "dirs": {tuple(x.split(">")) for x in meta["directions"]}}
    return out


def _registered_glimmer(paths) -> bool:
    from uyari.registry import promoted

    return bool(promoted(paths, "mt", LANG, "promoted"))


def _served() -> bool:
    """Is the local model server (``uyari serve start``) answering? Muse Glimmer is used only through it."""
    from uyari.pipelines.mt.infer import _server_up

    return _server_up(os.environ.get("GLIMMER_LOCAL_URL", "http://127.0.0.1:8011/v1/chat/completions"))


def ensure_glimmer_server(paths) -> str | None:
    """Start the model server when a Muse Glimmer adapter is registered and nothing answers yet, so ``uyari
    demo`` serves Glimmer without ``make serve`` first. A server started here is stopped when the page stops.
    Returns why Glimmer is unavailable, or None."""
    import atexit
    import signal
    import sys

    from uyari.serve import default_adapters, start, stop

    if not default_adapters(paths) or _served():
        return None
    print("Starting the Muse Glimmer server (llama-server, about 16.5 GB of GPU memory) ...", flush=True)
    try:
        st = start(paths, wait_s=600)
    except Exception as e:  # noqa: BLE001 - the page still serves NLLB; say why Glimmer is missing
        return f"its server could not start ({e})"
    if not st.get("ready"):
        return f"its server did not answer ({st.get('note', 'see .uyari/serve.log')})"
    atexit.register(stop, paths)
    # SIGTERM (``kill``, ``pkill``) skips atexit by default: turn it into a normal exit, so the server stops too.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    return None


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


def officials(models: dict, into: bool) -> list[str]:
    """The official languages some registered model translates into Shawi (``into``) or Shawi into."""
    return [NAMES[o] for o in OFFICIALS
            if any(((o, LANG) if into else (LANG, o)) in m["dirs"] for m in models.values())]


def route(models: dict, mode: str, s_name: str, t_name: str) -> str:
    """The model label for ``s_name`` -> ``t_name`` (the selected one if it can). Shawi must be on one side and
    Spanish or English on the other: Spanish <-> English, Shawi -> Shawi and anything else is refused."""
    s, t = CODES.get(s_name), CODES.get(t_name)
    if {s, t} not in [{LANG, o} for o in OFFICIALS]:
        raise ValueError("Every translation here has Shawi on one side and Spanish or English on the other.")
    for label in [mode, *models]:
        if label in models and (s, t) in models[label]["dirs"]:
            return label
    raise ValueError(f"{s_name} → {t_name} is not available yet.")


def _examples_for(name: str) -> list[list[str]]:
    """The examples of one official language, as Dataset samples."""
    return [[t] for t in EXAMPLES.get(CODES.get(name, ""), [])]


def _examples_from(paths, models: dict) -> list[list[str]]:
    """Four short human Shawi sentences from the training data: two health or civic, two everyday."""
    from uyari.agents.trainer.needs import HEALTH
    from uyari.build import read_table

    if not officials(models, into=False):
        return []
    build = next(iter(models.values()))["build"]
    rows = sorted((r for r in read_table(paths, build, LANG, "mt")
                   if r["split"] == "train" and r["src_lang"] == "spa_Latn" and "?" not in r["tgt_text"]
                   and 5 <= len(r["tgt_text"].split()) <= 9), key=lambda r: r["chunk_id"])
    health = [r for r in rows if r["domain"] in HEALTH][:2]
    first = {}
    for r in rows:
        if r["domain"] not in HEALTH:
            first.setdefault(r["domain"], r)
    return [[r["tgt_text"]] for r in health + [first[d] for d in sorted(first)][:2]]


# ------------------------------------------------------------------------------------ the Shawi voice
@cache
def _voice_cfg(paths):
    from uyari.pipelines.tts.voice import load_config

    return load_config(paths, LANG)


def shawi_audio(paths, text: str):
    """``(sampling_rate, int16 array)`` of Shawi ``text`` (our spelling) from the local MMS voice."""
    import numpy as np

    from uyari.pipelines.tts.voice import speak

    sr, wav = speak(_voice_cfg(paths), text)
    return sr, (np.clip(wav, -1.0, 1.0) * 32767).astype(np.int16)


def voice_coverage(paths) -> dict:
    """How much of our accepted Shawi text the voice can read, as written and after conversion."""
    from uyari.pipelines.tts.check_voice import accepted_texts
    from uyari.pipelines.tts.voice import coverage, get_voice

    cfg = _voice_cfg(paths)
    texts, letters = accepted_texts(paths, LANG, limit=None), get_voice(cfg.voice).letters
    return {"before": coverage(texts, letters)["letter_coverage"],
            "after": coverage(texts, letters, cfg)["letter_coverage"] if cfg.rules else None}


# ------------------------------------------------------------------------------------ voice input (visitor's key)
def transcribe_byok(paths, audio_path: str | None, api_key: str | None, language: str = "es") -> tuple[str, str]:
    """(transcript, message). Uses only the key typed by the visitor; never the server's environment."""
    if not audio_path:
        return "", ""
    key = (api_key or "").strip()
    if not key:
        return "", "Enter your own Meta API key to use voice input. This server does not use its own key."
    from uyari.speech.transcribe import transcribe_file

    try:
        r = transcribe_file(paths, Path(audio_path), api_key=key, max_seconds=MAX_VOICE_SECONDS,
                            command="demo-byok", language=language)
    except Exception as e:  # noqa: BLE001 - show the reason, never the key
        msg = str(e).replace(key, "***")
        return "", f"Could not transcribe: {msg}"
    return r.get("text", ""), f"Transcribed with your key: {r['seconds']:.0f} s, about US$ {r['cost_usd']:.5f}."


def pivot_byok(paths, text: str, api_key: str | None, src: str = "eng_Latn") -> tuple[str, str]:
    """(Spanish, message): an official language -> Spanish with Muse Spark and the visitor's key only.
    Official-language text only."""
    key = (api_key or "").strip()
    if not key:
        return "", "Enter your own Meta API key. This server does not use its own key."
    from uyari.llm.pivot import translate_official

    try:
        r = translate_official(paths, text, src, "spa_Latn", api_key=key)
    except Exception as e:  # noqa: BLE001 - show the reason, never the key
        return "", f"Could not translate the {NAMES[src]} into Spanish: {str(e).replace(key, '***')}"
    return r["text"], f"about US$ {r['cost_usd']:.5f}"


def voice_plan(models: dict, mode: str, lang: str) -> tuple[str, bool]:
    """(model label, through Spanish?) for speech in ``lang`` into Shawi. A registered ``lang`` -> Shawi model
    first (the selected one if it can); a language with no such model goes into Spanish first."""
    tries = [(lang, False)] + ([("spa_Latn", True)] if lang != "spa_Latn" else [])
    for src, pivot in tries:
        for label in [mode, *models]:
            if label in models and (src, LANG) in models[label]["dirs"]:
                return label, pivot
    raise ValueError(f"no registered model translates {NAMES.get(lang, lang)} or Spanish into Shawi")


def hear(paths, models: dict, audio_path: str | None, api_key: str | None, mic_name: str, mode: str) -> dict:
    """Spoken Spanish or English -> the text our model will put into Shawi.
    ``{"ok", "heard" (the transcript), "text", "src" (language name of ``text``), "mode" (model label),
    "note"}``; on failure ``ok`` is False and ``note`` says why. Only the visitor's key is used, for both paid
    steps."""
    lang = CODES[mic_name]
    heard, note = transcribe_byok(paths, audio_path, api_key, language=ISO1[lang])
    if not heard:
        return {"ok": False, "note": note or "Nothing was heard. Try again a little closer to the microphone."}
    label, pivot = voice_plan(models, mode, lang)
    if not pivot:
        return {"ok": True, "heard": heard, "text": heard, "src": mic_name, "mode": label, "note": note}
    spanish, msg = pivot_byok(paths, heard, api_key, src=lang)
    if not spanish:
        return {"ok": False, "note": msg}
    note += (f"<br>Heard in {mic_name}: “{html.escape(heard)}”. No {mic_name} → Shawi model is registered yet, "
             f"so **Muse Spark** put it into Spanish with your key ({msg}), and our model put the Spanish into "
             "Shawi.")
    return {"ok": True, "heard": heard, "text": spanish, "src": "Spanish", "mode": label, "note": note}


# ------------------------------------------------------------------------------------ what works / what's next
def _read_json(f) -> dict:
    try:
        return json.loads(Path(f).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _floor(paths, m: dict) -> tuple[dict, float | None]:
    """Retrieval floor: per direction if it was scored on this machine (runs/, validation), and the mean that
    models/registry.yaml recorded when the model was registered."""
    from uyari.registry import load

    per = _read_json(paths.runs / "retrieval" / m["build"] / LANG / "scores.json").get("validation") or {}
    hist = ((load(paths).get("mt") or {}).get(LANG) or {}).get("history") or []
    reason = next((h.get("reason", "") for h in reversed(hist) if h.get("to") == m["ref"]), "")
    found = re.search(r"floor (\d+(?:\.\d+)?)", reason)
    return per, float(found.group(1)) if found else None


def _and(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1] if names else ""


def _scores_table(paths, models: dict) -> list[str]:
    """One row per direction (into Shawi first): each model's validation and held-out test chrF++, and the
    retrieval floor of the build they share."""
    def k(d):
        return f"{d[0][:3]}>{d[1][:3]}"

    every = set().union(*(m["dirs"] for m in models.values())) if models else set()
    dirs = [(o, LANG) for o in OFFICIALS if (o, LANG) in every] + [(LANG, o) for o in OFFICIALS if (LANG, o) in every]
    builds = {m["build"] for m in models.values()}
    floor = _floor(paths, next(iter(models.values())))[0] if len(builds) == 1 else {}
    sc = {label: _read_json(Path(m["dir"]) / "scores.json") for label, m in models.items()}

    def cell(x):
        return "—" if x is None else f"{x:.1f}"

    head = ["Direction", *[f"{label.split(' ·')[0]} validation" for label in models],
            *[f"{label.split(' ·')[0]} test" for label in models], *(["Floor"] if floor else [])]
    rows = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for d in dirs:
        v = [cell(((sc[label].get("validation") or {}).get(k(d)) or {}).get("chrf++")) for label in models]
        t = [cell(((sc[label].get("test") or {}).get(k(d)) or {}).get("chrf++")) for label in models]
        f = [cell((floor.get(k(d)) or {}).get("chrf++"))] if floor else []
        rows.append(f"| {NAMES[d[0]]} → {NAMES[d[1]]} | " + " | ".join(v + t + f) + " |")
    return ["chrF++ per direction (validation; test is scored once, at registration):", "", *rows]


def status_md(paths, models: dict, voice: dict | None = None) -> str:
    """The "What works today and what's next" panel. Every number comes from a file: models/registry.yaml, the
    model's scores.json, the build's MANIFEST.json and languages/cbt_Latn/NEEDS.md (the voice line from the
    accepted text and tts.yaml)."""
    from uyari.agents.trainer.needs import HEALTH
    from uyari.build import load_manifest

    def k(d):
        return f"{d[0][:3]}>{d[1][:3]}"

    english = any(("eng_Latn", LANG) in m["dirs"] for m in models.values())
    lines = ["**What works today**", ""]
    for label, m in models.items():
        sc = _read_json(Path(m["dir"]) / "scores.json")
        val = sc.get("validation") or {}
        _, mean_floor = _floor(paths, m)
        official = _and([NAMES[o] for o in OFFICIALS if (o, LANG) in m["dirs"] or (LANG, o) in m["dirs"]])
        line = (f"* **Text, Shawi ↔ {official}**: `{m['ref']}` ({label}), fine-tuned from Meta's open "
                f"`{m['base'] or 'base model'}` on build `{m['build']}`.")
        if val.get("mean_chrf++") is not None and mean_floor is not None:
            line += (f" Validation chrF++ mean {val['mean_chrf++']:.2f} against a retrieval floor of "
                     f"{mean_floor:.2f}.")
        lines.append(line)
    lines += ["", *_scores_table(paths, models), ""]
    build = next(iter(models.values()))["build"] if models else None
    man = (load_manifest(paths, build).get("languages") or {}).get(LANG, {}) if build else {}
    counts = man.get("counts") or {}
    if counts:
        n_contrib = len((man.get("contributions") or {}).get("included") or [])
        lines.append(f"* **Data**: {counts['pairs']:,} human Shawi translations from {n_contrib} contributions "
                     f"(build `{build}`), {counts['clips']} recordings.")
    spoken = _and([NAMES[o] for o in ISO1])
    lines.append(f"* **Speech in**: {spoken} through Muse Voice Transcribe, with your own key."
                 + ("" if english else " English goes through Spanish (Muse Spark, same key) until the English "
                                       "model is registered."))
    if voice:
        cov = (f": it can read {voice['after']:.2%} of the letters in our Shawi text after spelling conversion "
               f"({voice['before']:.0%} as written)" if voice.get("after") is not None else "")
        lines.append(f"* **Speech out**: Shawi read aloud by Meta's MMS voice on this server{cov}.")
    lines += ["", "<span class='uy-small'>chrF++ (0 to 100, higher is better) measures how much of a human "
                  "translation the output matches, letter by letter and word by word; the retrieval floor is the "
                  "score of simply returning the human translation of the most similar training sentence, and a "
                  "model must beat it to be served.</span>", "", "**What's next**", ""]
    by_domain = counts.get("chunks_translated_by_domain") or {}
    nxt = []
    if counts:
        health = sum(by_domain.get(d, 0) for d in HEALTH)
        nxt.append(f"**More health and civic sentences**: {health:,} of the {counts['pairs']:,} pairs today.")
        nxt.append(f"**Shawi recordings**: {counts['clips']} so far. Read recordings from consenting speakers make "
                   "Shawi speech input possible to measure.")
    else:
        nxt += ["**More health and civic sentences.**", "**Shawi recordings**, for Shawi speech input."]
    nxt.append("**Our own Shawi voice**, in our spelling, from those recordings.")
    if not english:
        nxt.append("**The English model**: one model for Spanish and English ↔ Shawi, trained next.")
    if not any(m["slot"] == "promoted" for m in models.values()):
        nxt.append("**Muse Glimmer**: Meta's open-weight 30B model, fine-tuned for Shawi, as the default "
                   "translator once it beats NLLB.")
    lines += [f"{i}. {x}" for i, x in enumerate(nxt, 1)]
    needs = paths.language_dir(LANG) / "NEEDS.md"
    if needs.is_file():
        titles = re.findall(r"^\d+\. \*\*(.+?)\.?\*\*", needs.read_text(encoding="utf-8"), re.M)
        lines += ["", f"What the data asks for, written by the Trainer "
                      f"([NEEDS.md]({REPO_URL}/blob/main/languages/{LANG}/NEEDS.md)): " + " · ".join(titles) + "."]
    return "\n".join(lines)


# ------------------------------------------------------------------------------------ the page
def launch(paths, share: bool = True, voice: bool = True, port: int = 7860):
    import gradio as gr

    glimmer_missing = ensure_glimmer_server(paths)
    models = _models(paths)
    if not models:
        raise SystemExit("No registered models in models/registry.yaml. Train and register one first.")
    if SLOTS["promoted"] not in models and glimmer_missing is None and _registered_glimmer(paths):
        glimmer_missing = "its server is not running (start it with `make serve`)"
    model_note = f"Muse Glimmer is unavailable: {glimmer_missing}." if glimmer_missing else None
    default_mode = SLOTS["promoted"] if SLOTS["promoted"] in models else next(iter(models))
    into, out_of = officials(models, into=True), officials(models, into=False)
    if not into:
        raise SystemExit("No registered model translates an official language into Shawi.")
    shawi = NAMES[LANG]

    def translate(text, s_name, t_name, mode):
        """(translation, info line, closest human pairs) for one direction with Shawi on one side."""
        text = (text or "").strip()[:MAX_CHARS]
        if not text:
            return "", "", ""
        try:
            label = route(models, mode, s_name, t_name)
        except ValueError as e:
            return "", str(e), ""
        s, t = CODES[s_name], CODES[t_name]
        ref = models[label]["ref"]
        t0 = time.time()
        try:
            out = _translator(paths, ref).translate([text], s, t)[0]
        except Exception as e:  # noqa: BLE001 - say what failed instead of a blank box
            return "", f"The model failed: {e}", ""
        info = f"<sub>{label} · `{ref}` · {time.time() - t0:.1f} s</sub>"
        pairs = _index(paths, models[label]["build"], s, t).closest_pairs(text, k=3)
        return out, info, _pairs_md(pairs, s, t)

    def speak(text):
        """The player showing Shawi audio for ``text``, and the text it was made from."""
        text = (text or "").strip()
        if not text:
            return gr.update(visible=False), ""
        try:
            return gr.update(value=shawi_audio(paths, text), visible=True), text
        except Exception as e:  # noqa: BLE001
            raise gr.Error(f"The Shawi voice failed: {e}", print_exception=False) from e

    def listen(text, said):
        """Listen: a new text is spoken here; the same text again was already restarted by REPLAY_JS."""
        if said and (text or "").strip() == said:
            return gr.update(), gr.update()
        return speak(text)

    def on_record(audio_path, api_key, mic_name, mode):
        if not audio_path:
            raise gr.Error("No recording.", visible=False, print_exception=False)
        r = hear(paths, models, audio_path, api_key, mic_name, mode)
        if not r["ok"]:  # stops the chain: nothing is translated or spoken
            raise gr.Error(r["note"], print_exception=False)
        # Old Shawi is cleared and the player hidden; the new audio then plays by itself, even if it is the same.
        return r["heard"], r["note"], r, "", "", gr.update(visible=False)

    def on_heard(r):
        out, info, _ = translate(r["text"], r["src"], shawi, r["mode"])
        if not out:
            raise gr.Error(info or "Nothing to translate.", print_exception=False)
        return out, info

    for label in models:  # warm up: load every model and the index before the first visitor
        translate("Hola", into[0], shawi, label)
    english_ready = "English" in into
    spoken = [NAMES[o] for o in ISO1]  # what Muse Voice Transcribe takes
    pivoted = [n for n in spoken if n not in into]  # spoken, but no registered model takes it into Shawi
    try:  # load the voice once, before the first visitor; without it the page still translates
        shawi_audio(paths, "Ipiʼ.")
        coverage = voice_coverage(paths)
        can_speak = True
    except Exception as e:  # noqa: BLE001 - offline with no cached voice, or no torch
        print(f"Shawi voice unavailable, Listen is hidden: {e}")
        coverage, can_speak = None, False

    def pickers(left, right, left_choices, right_choices):
        """From -> To. The Shawi side is fixed; only the official language can be chosen."""
        with gr.Row(equal_height=True):
            a = gr.Dropdown(left_choices, value=left, label="From", interactive=len(left_choices) > 1, scale=5)
            gr.HTML("<div class='uy-arrow'>→</div>", scale=1, min_width=56, container=False)
            b = gr.Dropdown(right_choices, value=right, label="To", interactive=len(right_choices) > 1, scale=5)
        return a, b

    def text_panel(placeholder):
        with gr.Row():
            with gr.Column():
                src = gr.Textbox(lines=5, max_length=MAX_CHARS, show_label=False, elem_classes="uy-big",
                                 placeholder=placeholder)
            with gr.Column() as right:
                out = gr.Textbox(lines=5, show_label=False, interactive=False, elem_classes="uy-big",
                                 buttons=["copy"], placeholder="Translation")
        return src, out, right

    def player(label, elem_id):
        """Hidden until there is audio (see REPLAY_JS)."""
        with gr.Column(visible=can_speak):
            audio = gr.Audio(type="numpy", interactive=False, autoplay=True, label=label, buttons=["download"],
                             visible=False, elem_id=elem_id)
            gr.Markdown(f"<span class='uy-small'>{VOICE_NOTE}</span>")
        return audio

    def model_row(button: bool = True):
        """The Model switch (Glimmer by default, NLLB second), with the tab's Translate button, as before."""
        with gr.Row(equal_height=True):
            m = gr.Radio(list(models), value=default_mode, label="Model", interactive=len(models) > 1, scale=4,
                         info=model_note)
            btn = gr.Button("Translate", variant="primary", scale=1) if button else None
        return m, btn

    official_names = _and(list(dict.fromkeys(into + out_of)))
    with gr.Blocks(title="Uyari Translate · Shawi", analytics_enabled=False) as demo:
        gr.HTML(f"<div class='uy-head'><h1>Uyari Translate</h1><p class='uy-lead'>{LEAD}</p><p>Shawi (Chayahuita, "
                f"Peru) ↔ {official_names}, trained on human translations. This server runs only our own "
                "fine-tuned open models.</p></div>")
        with gr.Tabs():
            # 1. Official -> Shawi, with Listen.
            with gr.Tab("Your language → Shawi"):
                a_lang, a_tgt = pickers(into[0], shawi, into, [shawi])
                a_src, a_out, a_right = text_panel("Type or paste text in the language chosen above. It "
                                                   "translates as you type.")
                with a_right:
                    a_say = gr.Button("▶ Listen", variant="secondary", size="sm", visible=can_speak)
                    a_audio = player("Shawi audio", "uy-a-player")
                a_said = gr.State("")
                a_mode, a_btn = model_row()
                a_info, a_pairs = gr.Markdown(), gr.Markdown(elem_classes="uy-pairs")
                # Examples in the selected language only (a Dataset, so its samples follow "From").
                a_ex = gr.Dataset(components=[a_src], samples=_examples_for(into[0]), label="Try an example")
            # 2. Shawi -> official, text only.
            if out_of:
                with gr.Tab("Shawi → your language"):
                    b_src_lang, b_lang = pickers(shawi, out_of[0], [shawi], out_of)
                    b_src, b_out, _ = text_panel("Type or paste Shawi. It translates as you type.")
                    b_mode, b_btn = model_row()
                    b_info, b_pairs = gr.Markdown(), gr.Markdown(elem_classes="uy-pairs")
                    examples = _examples_from(paths, models)
                    if examples:
                        gr.Examples(examples, inputs=[b_src], label="Try a Shawi sentence from our data")
                    gr.Markdown("<span class='uy-small'>Spoken Shawi comes later: there are no Shawi recordings "
                                "yet.</span>")
            # 3. Speech: an official language in, Shawi text and audio out.
            if voice:
                with gr.Tab("🎙 Speak, hear Shawi"):
                    pivot_note = ("" if not pivoted else
                                  f" {_and(pivoted)} {'is' if len(pivoted) == 1 else 'are'} first put into Spanish "
                                  "by **Muse Spark** (official-language text only, also paid with your key, a "
                                  "fraction of a cent), and our model puts the Spanish into Shawi.")
                    gr.Markdown(f"Speak {_and(spoken).replace(' and ', ' or ')} and hear it in Shawi. Your speech "
                                "is transcribed by "
                                "**Muse Voice Transcribe** with **your own** Meta API key, so the cost goes to your "
                                f"account (US$ 0.18 per audio hour; at most {MAX_VOICE_SECONDS} s per recording). "
                                f"The key is used for that one request and is never stored or logged.{pivot_note} "
                                "The Shawi is made and read aloud on this server; Shawi text and audio never "
                                "leave it.")
                    with gr.Row():
                        api_key = gr.Textbox(label="Your Meta API key", type="password", scale=3,
                                             placeholder="Used for this request only")
                        mic_lang = gr.Radio(spoken, value=spoken[0], label="I will speak", scale=2)
                    v_mode, _ = model_row(button=False)
                    mic = gr.Audio(sources=["microphone"], type="filepath", label="Record, then stop")
                    with gr.Row():
                        v_heard = gr.Textbox(lines=3, label="What we heard", interactive=False)
                        v_out = gr.Textbox(lines=3, label="Shawi", interactive=False, buttons=["copy"],
                                           elem_classes="uy-big")
                    v_audio = player("Shawi audio", "uy-v-player")
                    v_note, v_info = gr.Markdown(), gr.Markdown()
                    v_req = gr.State({})
        with gr.Accordion("What works today and what's next", open=False):
            gr.Markdown(status_md(paths, models, coverage))
        gr.Markdown(
            f"<div class='uy-foot'>Open source: data and code on <a href='{REPO_URL}'>GitHub</a>; models "
            f"(<a href='{HF_GLMmer30B_URL}'>Glimmer 30B QLoRA</a> · <a href='{HF_NLLB_URL}'>NLLB 1.3B</a>) on "
            "Hugging Face. "
            "Data CC BY 4.0 · NLLB weights CC BY-NC 4.0 (non-commercial) · Muse Glimmer Apache 2.0 · MMS voice "
            "CC BY-NC 4.0.<br>Machine translation can be wrong: have a Shawi speaker check anything used for health "
            "care or legal matters. Shawi output can be heard; Shawi speech input comes later."
            + ("" if english_ready else " English ↔ Shawi is being trained next.")
            + f"<br>Designed by Muse Spark 1.3 Contributor · Built by "
            f"<a href='{LINKEDIN_URL}'>@malexandersalazar</a>.</div>")

        live = {"trigger_mode": "always_last", "show_progress": "hidden", "concurrency_id": "mt"}
        tabs = [(a_src, a_lang, a_tgt, a_out, a_info, a_pairs, a_btn, a_mode)]
        if out_of:
            tabs.append((b_src, b_src_lang, b_lang, b_out, b_info, b_pairs, b_btn, b_mode))
        for src, s_lang, t_lang, out, info, pairs, btn, mode in tabs:
            args, outs = [src, s_lang, t_lang, mode], [out, info, pairs]
            src.change(translate, args, outs, **live)
            src.submit(translate, args, outs, concurrency_id="mt")
            btn.click(translate, args, outs, concurrency_id="mt")
            s_lang.change(translate, args, outs, **live)
            t_lang.change(translate, args, outs, **live)
            mode.change(translate, args, outs, **live)
        a_ex.click(lambda sample: sample[0], a_ex, a_src, queue=False, show_progress="hidden")
        a_lang.change(lambda n: gr.update(samples=_examples_for(n)), a_lang, a_ex, queue=False,
                      show_progress="hidden")
        if can_speak:
            # Speech is made on click, in its own queue: typing never waits for the voice.
            a_say.click(None, None, None, js=REPLAY_JS % "uy-a-player", queue=False).then(
                listen, [a_out, a_said], [a_audio, a_said], concurrency_id="tts")
            # Audio made for an earlier text is hidden (not emptied, see REPLAY_JS) as soon as the text changes.
            a_out.change(lambda o, s: (gr.update(), s) if s and (o or "").strip() == s else
                         (gr.update(visible=False), ""), [a_out, a_said], [a_audio, a_said], queue=False,
                         show_progress="hidden")
        if voice:
            # One action: record -> transcript -> Shawi text -> Shawi audio, which plays by itself.
            rec = mic.stop_recording(on_record, [mic, api_key, mic_lang, v_mode],
                                     [v_heard, v_note, v_req, v_out, v_info, v_audio],
                                     concurrency_id="voice-in", concurrency_limit=4)
            rec = rec.success(on_heard, v_req, [v_out, v_info], concurrency_id="mt")
            if can_speak:
                rec.success(lambda t: speak(t)[0], v_out, v_audio, concurrency_id="tts")
    demo.queue(default_concurrency_limit=1).launch(
        share=share, server_name=os.environ.get("UYARI_DEMO_HOST", "0.0.0.0"), server_port=port,
        theme=_theme(), css=CSS)
