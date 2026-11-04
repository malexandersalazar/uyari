"""Translators behind one interface: ``translate(texts, src_lang, tgt_lang) -> list[str]``.

* ``NllbTranslator``      a trained NLLB model (``models/<name>/weights``)
* ``CausalTranslator``    base causal LM + LoRA adapter, in process (Unsloth or PEFT)
* ``ServerTranslator``    the same adapter served by ``uyari serve`` (vLLM / llama-server)
* ``RetrievalTranslator`` the floor: the human translation of the nearest training source

Input and output text is always canonical (``ʼ``); each translator applies its model's codec.
"""

from __future__ import annotations

import os
from functools import cache
from pathlib import Path

from uyari.paths import Paths
from uyari.pipelines.mt.codec import Codec
from uyari.pipelines.mt.common import read_meta


class Translator:
    name = "translator"
    language = ""

    def __init__(self, codec: dict | None = None, language: str = ""):
        self.codec = Codec(codec)
        self.language = language

    def _in(self, texts, src_lang):
        return [self.codec.encode(t) for t in texts] if src_lang == self.language else list(texts)

    def _out(self, texts, tgt_lang):
        return [self.codec.decode(t) for t in texts] if tgt_lang == self.language else list(texts)

    def translate(self, texts: list[str], src_lang: str, tgt_lang: str) -> list[str]:
        return self._out(self._run(self._in(texts, src_lang), src_lang, tgt_lang), tgt_lang)

    def _run(self, texts, src_lang, tgt_lang):
        raise NotImplementedError


class NllbTranslator(Translator):
    def __init__(self, model_dir: Path, meta: dict):
        super().__init__(meta.get("codec"), meta["language"])
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.name = meta["name"]
        w = Path(model_dir) / meta.get("weights", "weights")
        self.tok = AutoTokenizer.from_pretrained(w)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            w, dtype=torch.bfloat16 if device == "cuda" else torch.float32).to(device).eval()
        self.ev = meta.get("eval") or {}

    def _run(self, texts, src_lang, tgt_lang):
        from uyari.pipelines.mt.train_nllb import generate

        return generate(self.model, self.tok, texts, src_lang, tgt_lang,
                        num_beams=int(self.ev.get("num_beams", 4)),
                        max_new_tokens=int(self.ev.get("max_new_tokens", 256)),
                        batch_size=int(self.ev.get("batch_size", 32)))


class CausalTranslator(Translator):
    def __init__(self, model_dir: Path, meta: dict):
        super().__init__(meta.get("codec"), meta["language"])
        from uyari.pipelines.mt.train_causal import load_model
        from uyari.recipes import load_recipe

        self.name = meta["name"]
        recipe = load_recipe(Path(model_dir) / "recipe.yaml")
        self.model, self.chat, _ = load_model(recipe, for_training=False,
                                             adapter_dir=Path(model_dir) / meta.get("adapter", "adapter"))
        self.ev = meta.get("eval") or {}

    def _run(self, texts, src_lang, tgt_lang):
        from uyari.pipelines.mt import prompts
        from uyari.pipelines.mt.train_causal import generate

        return generate(self.model, self.chat, [prompts.messages(src_lang, tgt_lang, t) for t in texts],
                        max_new_tokens=int(self.ev.get("max_new_tokens", 256)),
                        batch_size=int(self.ev.get("batch_size", 8)))


class ServerTranslator(Translator):
    """Calls the local OpenAI-compatible server with the LoRA adapter name as the model."""

    def __init__(self, meta: dict, url: str, model_name: str):
        super().__init__(meta.get("codec"), meta["language"])
        self.name, self.url, self.model_name = meta["name"], url, model_name
        self.ev = meta.get("eval") or {}
        self.template_kwargs = meta.get("chat_template_kwargs") or {}

    def _run(self, texts, src_lang, tgt_lang):
        from concurrent.futures import ThreadPoolExecutor

        import httpx

        from uyari.pipelines.mt import prompts
        from uyari.pipelines.mt.train_causal import clean_completion

        def one(t):
            body = {"model": self.model_name, "messages": prompts.messages(src_lang, tgt_lang, t), "temperature": 0,
                    "max_tokens": int(self.ev.get("max_new_tokens", 256))}
            if self.template_kwargs:  # same template variables as training (vLLM: chat_template_kwargs)
                body["chat_template_kwargs"] = self.template_kwargs
            r = httpx.post(self.url, timeout=300, json=body)
            r.raise_for_status()
            return clean_completion(r.json()["choices"][0]["message"]["content"] or "")

        with ThreadPoolExecutor(max_workers=int(self.ev.get("server_concurrency", 8))) as ex:
            return list(ex.map(one, texts))


class RetrievalTranslator(Translator):
    def __init__(self, paths: Paths, tag: str, language: str, primary: str | None = None):
        super().__init__(None, language)
        self.name = "retrieval"
        self.paths, self.tag = paths, tag
        self._idx = {}

    def index(self, src_lang, tgt_lang):
        from uyari.pipelines.mt.retrieval import build_index

        key = (src_lang, tgt_lang)
        if key not in self._idx:
            official = tgt_lang if src_lang == self.language else src_lang
            self._idx[key] = build_index(self.paths, self.tag, self.language, official, src_lang, tgt_lang)
        return self._idx[key]

    def _run(self, texts, src_lang, tgt_lang):
        return self.index(src_lang, tgt_lang).translate(texts)


def model_dir(paths: Paths, ref: str) -> Path:
    p = Path(ref)
    if p.is_dir():
        return p
    for cand in (paths.data / ref, paths.models / ref):
        if cand.is_dir():
            return cand
    raise FileNotFoundError(f"model {ref} not found under {paths.models}")


def _server_up(url: str) -> bool:
    import httpx

    try:
        return httpx.get(url.replace("/chat/completions", "/models"), timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


def load_translator(paths: Paths, ref: str, prefer_server: bool = True) -> Translator:
    d = model_dir(paths, ref)
    meta = read_meta(d)
    if meta["kind"] == "nllb":
        return NllbTranslator(d, meta)
    if meta["kind"] == "causal_lora":
        url = os.environ.get("GLIMMER_LOCAL_URL", "http://127.0.0.1:8011/v1/chat/completions")
        adapter_name = (meta.get("eval") or {}).get("server_adapter")
        if prefer_server and adapter_name and _server_up(url):
            return ServerTranslator(meta, url, adapter_name)
        return CausalTranslator(d, meta)
    raise ValueError(f"unknown model kind {meta['kind']}")


@cache
def _cached(paths: Paths, ref: str) -> Translator:
    return load_translator(paths, ref)


def translate_one(paths: Paths, text: str, direction: str, ref: str | None = None) -> str:
    from uyari.registry import promoted

    s, t = direction.split(">")
    officials = {"spa": "spa_Latn", "eng": "eng_Latn", "fra": "fra_Latn", "deu": "deu_Latn", "ita": "ita_Latn",
                 "por": "por_Latn"}
    full = {**officials, "cbt": "cbt_Latn"}
    lang = full.get(t if s in officials else s, "cbt_Latn")  # the Indigenous side names the registry entry
    ref = ref or promoted(paths, "mt", lang) or promoted(paths, "mt", lang, "fast")
    if not ref:
        raise RuntimeError("no model given and none registered (models/registry.yaml)")
    return _cached(paths, ref).translate([text], full.get(s, s), full.get(t, t))[0]
