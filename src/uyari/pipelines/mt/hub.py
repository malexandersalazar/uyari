"""A Hugging Face model repository for a trained translator (``uyari publish``).

The repository holds what someone needs to run the model and to decide whether to: the weights (``weights/``)
or the adapter (``adapter/``: PEFT safetensors and the GGUF llama.cpp loads), and a README.md with the Hub
metadata, usage that was run before it was written here, the test scores, the license and the limitations.
The rest stays in the GitHub repository and is linked, not copied: the full model card (validation and test
per direction, BLEU, the retrieval floor), the recipe, the build, the data and the governance.

One repository per model family (``<namespace>/uyari-<task>-<lang>-<base>``) holds its current version: the
README names it, a tag marks it (``v0.3``), and files an earlier version had and this one does not are deleted.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

from uyari.build import load_manifest
from uyari.paths import Paths
from uyari.pipelines.mt import prompts
from uyari.pipelines.mt.common import read_meta
from uyari.registry import load as load_registry
from uyari.serve import GGUF_FILE, GGUF_REPO

GITHUB = "https://github.com/malexandersalazar/uyari"
BLOB = f"{GITHUB}/blob/main"
AUTHOR = "Alexander Salazar"

HUB_LICENSES = {"facebook/nllb-200": "cc-by-nc-4.0", "meta-models/Muse-Glimmer": "apache-2.0"}
LICENSE_NAMES = {"cc-by-nc-4.0": "CC BY-NC 4.0", "apache-2.0": "Apache 2.0", "cc-by-4.0": "CC BY 4.0"}
BASE_NAMES = {"facebook/nllb-200-distilled-1.3B": "NLLB-200 distilled 1.3B",
              "meta-models/Muse-Glimmer-30B": "Muse Glimmer 30B"}
ISO639_1 = {"spa": "es", "eng": "en", "fra": "fr", "deu": "de", "ita": "it", "por": "pt", "hin": "hi", "tha": "th"}
EXAMPLES = {"spa_Latn": "El niño tiene fiebre desde ayer.", "eng_Latn": "The child has had a fever since yesterday."}
GGUF_BASES = {"meta-models/Muse-Glimmer-30B": (GGUF_REPO, GGUF_FILE)}  # what adapter.gguf applies to


def repo_name(model: str) -> str:
    """``mt-cbt-nllb1.3b@v0.3`` -> ``uyari-mt-cbt-nllb1.3b`` (Hub names cannot hold ``@``)."""
    return "uyari-" + model.split("@")[0]


def _prefixed(table: dict, base: str, default=None):
    return next((v for k, v in table.items() if base.startswith(k)), default)


def _short(lang: str) -> str:
    return prompts.name(lang).split(" (")[0]


def _and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _num(n: int) -> str:
    return ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"][n] if 0 <= n < 10 else str(n)


def _key(src: str, tgt: str) -> str:
    return f"{src[:3]}>{tgt[:3]}"


def _source_dir(model_dir: Path, meta: dict) -> Path:
    return model_dir / (meta.get("adapter") or meta.get("weights") or "weights")


def files_to_upload(model_dir: Path, meta: dict) -> list[Path]:
    """Everything in ``weights/`` or ``adapter/`` but PEFT's template README (the Hub README replaces it)."""
    return sorted(f for f in _source_dir(model_dir, meta).iterdir() if f.is_file() and f.name != "README.md")


def linked_paths(meta: dict) -> list[str]:
    """Repository paths the README links to."""
    return [f"models/{meta['name']}/MODEL_CARD.md", f"recipes/{meta['recipe_file']}",
            f"builds/{meta['build']}/MANIFEST.json", f"languages/{meta['language']}/README.md", "DATA_LICENSE.md",
            "NOTICE", "contributing/en/governance.md"]


def unpushed_links(paths: Paths, meta: dict) -> list[str]:
    """Linked paths not on origin/main as of the last fetch: those links resolve once they are pushed."""
    missing = []
    for p in linked_paths(meta):
        r = subprocess.run(["git", "cat-file", "-e", f"origin/main:{p}"], cwd=paths.data, capture_output=True)
        if r.returncode != 0:
            missing.append(p)
    return missing


def _card_section(card: str, heading: str) -> str:
    m = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |^_Generated|\Z)", card, re.M | re.S)
    return m.group(1).strip() if m else ""


def _py_str(s: str) -> str:
    return json.dumps(s, ensure_ascii=False)


def _system_py() -> str:
    parts = re.split(r"(?<=\. )", prompts.SYSTEM)
    return "SYSTEM = (" + "\n          ".join(_py_str(p) for p in parts if p) + ")"


def _fill(template: str, **kw) -> str:
    for k, v in kw.items():
        template = template.replace(f"<<{k}>>", v)
    return template


def _example(meta: dict) -> tuple[str, str]:
    src = next((p for p in meta["primaries"] if p in EXAMPLES), meta["primaries"][0])
    return src, EXAMPLES.get(src, EXAMPLES["eng_Latn"])


NLLB_USAGE = '''```python
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

repo = "<<REPO>>"
device = "cuda" if torch.cuda.is_available() else "cpu"
tok = AutoTokenizer.from_pretrained(repo)
model = AutoModelForSeq2SeqLM.from_pretrained(
    repo, dtype=torch.bfloat16 if device == "cuda" else torch.float32).to(device).eval()


def translate(text, src, tgt):
<<ENCODE>>    tok.src_lang = src
    inputs = tok(text, return_tensors="pt").to(device)
    out = model.generate(**inputs, forced_bos_token_id=tok.convert_tokens_to_ids(tgt), num_beams=4)
    result = tok.decode(out[0], skip_special_tokens=True)
<<DECODE>>


print(translate(<<TEXT>>, "<<SRC>>", "<<LANG>>"))
```'''

GLIMMER_SERVER = '''```bash
hf download <<GGUF_REPO>> <<GGUF_FILE>> --local-dir .
hf download <<REPO>> adapter.gguf --local-dir .
llama-server -m <<GGUF_FILE>> --lora adapter.gguf -ngl 999 --port 8080 \\
  --chat-template-kwargs '<<KWARGS_JSON>>'
```

```python
import requests

<<SYSTEM>>


def translate(text, src, tgt):
    r = requests.post("http://127.0.0.1:8080/v1/chat/completions", json={
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": f"Translate from {src} to {tgt}:\\n{text}"}],
        "temperature": 0, "max_tokens": 256})
    return r.json()["choices"][0]["message"]["content"].strip()


print(translate(<<TEXT>>, "<<SRC>>", "<<LANG>>"))
```'''

GLIMMER_PEFT = '''```python
import torch
from peft import PeftModel
from transformers import AutoModelForImageTextToText, AutoProcessor

repo = "<<REPO>>"
processor = AutoProcessor.from_pretrained(repo)
model = AutoModelForImageTextToText.from_pretrained(
    "<<PEFT_BASE>>", dtype=torch.bfloat16, device_map="cuda")
model = PeftModel.from_pretrained(model, repo, autocast_adapter_dtype=False).eval()

<<SYSTEM>>


def translate(text, src, tgt):
    messages = [{"role": "system", "content": [{"type": "text", "text": SYSTEM}]},
                {"role": "user", "content": [{"type": "text", "text": f"Translate from {src} to {tgt}:\\n{text}"}]}]
    inputs = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True,
                                           return_tensors="pt", <<KWARGS_PY>>).to(model.device)
    out = model.generate(**inputs, max_new_tokens=256, do_sample=False)
    raw = processor.decode(out[0, inputs["input_ids"].shape[1]:])  # ' to=user<|message|>…<|eot|>'
    return raw.split("<|message|>")[-1].split("<|eot|>")[0].strip()


print(translate(<<TEXT>>, "<<SRC>>", "<<LANG>>"))
```'''


def _usage_nllb(model_dir: Path, meta: dict, repo_id: str, info: dict) -> str:
    lang = meta["language"]
    codec = meta.get("codec") or {}
    enc = "".join(f"        text = text.replace({_py_str(a)}, {_py_str(b)})\n" for a, b in codec.items())
    dec = "".join(f".replace({_py_str(b)}, {_py_str(a)})" for a, b in codec.items())
    src, text = _example(meta)
    code = _fill(NLLB_USAGE, REPO=repo_id, TEXT=_py_str(text), SRC=src, LANG=lang,
                 ENCODE=f"    if src == \"{lang}\":\n{enc}" if codec else "",
                 DECODE=(f"    return result{dec} if tgt == \"{lang}\" else result" if codec else "    return result"))
    codes = ", ".join(f"`{x}` ({_short(x)})" for x in [lang, *meta["primaries"]])
    lines = ["## Usage", "", code, "", f"Language codes: {codes}."]
    for a, b in codec.items():
        what = "its glottal stop" if a == info.get("apostrophe") else "the letter"
        lines += ["", f"{info.get('display_name') or _short(lang)} writes {what} as {a} (U+{ord(a):04X}), which NLLB's "
                      f"vocabulary does not have: the model reads and writes `{b}` instead, so map it at the edges as "
                      "above."]
    return "\n".join(lines)


def _usage_glimmer(model_dir: Path, meta: dict, repo_id: str, info: dict) -> str:
    adapter = _source_dir(model_dir, meta)
    peft_base = json.loads((adapter / "adapter_config.json").read_text(encoding="utf-8"))["base_model_name_or_path"]
    kw = meta.get("chat_template_kwargs") or {}
    src, text = _example(meta)
    common = dict(REPO=repo_id, SYSTEM=_system_py(), TEXT=_py_str(text), SRC=prompts.name(src),
                  LANG=prompts.name(meta["language"]))
    names = ", ".join(prompts.name(x) for x in [meta["language"], *meta["primaries"]])
    lines = ["## Usage", "",
             "The adapter is here twice: `adapter.gguf` for llama.cpp and `adapter_model.safetensors` for PEFT. "
             f"Prompts name the languages: {names}."]
    gguf = GGUF_BASES.get(meta["base_model"])
    if gguf and (adapter / "adapter.gguf").is_file():
        lines += ["", "### llama.cpp (fits a 24 GB GPU; how the scores below were measured)", "",
                  _fill(GLIMMER_SERVER, GGUF_REPO=gguf[0], GGUF_FILE=gguf[1], KWARGS_JSON=json.dumps(kw), **common)]
    lines += ["", "### Transformers and PEFT (more than 24 GB of GPU memory)", "",
              _fill(GLIMMER_PEFT, PEFT_BASE=peft_base,
                    KWARGS_PY=", ".join(f"{k}={_py_str(v)}" for k, v in kw.items()), **common)]
    if kw:
        lines += ["", "The chat-template settings ("
                  + ", ".join(f"`{k}={v}`" for k, v in kw.items()) + ") are the ones the adapter was trained with."]
    return "\n".join(lines)


USAGE = {"facebook/nllb-200": _usage_nllb, "meta-models/Muse-Glimmer": _usage_glimmer}


def _siblings(paths: Paths, meta: dict, namespace: str) -> list[tuple[str, str, str]]:
    """(repo id, base name, license) of the other models registered for this language."""
    slots = (load_registry(paths).get("mt") or {}).get(meta["language"]) or {}
    out = []
    for name in dict.fromkeys(slots.get(k) for k in ("promoted", "fast")):
        if not name or name == meta["name"] or not (paths.models / name).is_dir():
            continue
        base = read_meta(paths.models / name)["base_model"]
        out.append((f"{namespace}/{repo_name(name)}", BASE_NAMES.get(base, base),
                    LICENSE_NAMES.get(_prefixed(HUB_LICENSES, base, ""), "see its card")))
    return out


def readme(paths: Paths, model: str, namespace: str) -> str:
    model_dir = paths.models / model
    meta = read_meta(model_dir)
    lang, prims, base = meta["language"], list(meta["primaries"]), meta["base_model"]
    usage = _prefixed(USAGE, base)
    if usage is None:
        raise ValueError(f"no Hub usage written for base {base}: add one to uyari.pipelines.mt.hub.USAGE")
    hub_license = _prefixed(HUB_LICENSES, base)
    man = load_manifest(paths, meta["build"])["languages"][lang]
    data_lic = man.get("licenses") or {}
    if not data_lic or any("TODO" in k for k in data_lic):
        raise ValueError(f"data licenses not confirmed on build {meta['build']}: {data_lic}")
    scores = json.loads((model_dir / "scores.json").read_text(encoding="utf-8"))
    if "test" not in scores:
        raise ValueError(f"{model} has no test scores: `uyari eval --final` first")
    test = scores["test"]
    floor_f = paths.runs / "retrieval" / meta["build"] / lang / "scores.json"
    floor = (json.loads(floor_f.read_text(encoding="utf-8")).get("test") or {}) if floor_f.is_file() else {}
    card_md = (model_dir / "MODEL_CARD.md").read_text(encoding="utf-8")
    info = yaml.safe_load((paths.language_dir(lang) / "language.yaml").read_text(encoding="utf-8"))
    shawi = info.get("display_name") or _short(lang)
    adapter = meta["kind"] == "causal_lora"
    repo_id = f"{namespace}/{repo_name(model)}"
    version = model.split("@")[1]
    siblings = _siblings(paths, meta, namespace)
    dirs = [(p, lang) for p in prims] + [(lang, p) for p in prims]

    results = []
    for s, t in dirs:
        r = test.get(_key(s, t)) or {}
        if r.get("chrf++") is None:
            continue
        metrics = [{"type": "chrf", "value": round(r["chrf++"], 2), "name": "chrF++"}]
        if r.get("bleu") is not None:
            metrics.append({"type": "bleu", "value": round(r["bleu"], 2), "name": "BLEU"})
        results.append({"task": {"type": "translation", "name": f"Translation {_short(s)} to {_short(t)}"},
                        "dataset": {"type": "uyari", "name": f"Uyari {meta['build']} ({_short(s)}-{_short(t)})",
                                    "split": "test"},
                        "metrics": metrics})
    iso_name = (info.get("iso_name") or "").split(" (")[0]
    front = {
        "license": hub_license,
        "language": [ISO639_1.get(x[:3], x[:3]) for x in [lang, *prims]],
        "language_details": ", ".join([lang, *prims]),
        "library_name": "peft" if adapter else "transformers",
        "pipeline_tag": "translation",
        "base_model": base,
        "base_model_relation": "adapter" if adapter else "finetune",
        "tags": list(dict.fromkeys(t for t in [
            "translation", "uyari", shawi.lower(), iso_name.lower().replace(" ", "-"), "indigenous-languages",
            "low-resource", *(["lora", "qlora", "gguf"] if adapter else ["nllb"])] if t)),
        "metrics": ["chrf", "bleu"],
        "model-index": [{"name": repo_name(model), "results": results}],
    }

    others = ", ".join(_short(p) for p in prims)
    n_dirs = len(meta["directions"])
    base_name = BASE_NAMES.get(base, base)
    if adapter:
        r = json.loads((_source_dir(model_dir, meta) / "adapter_config.json").read_text(encoding="utf-8"))["r"]
        what = (f"A LoRA adapter (rank {r}, trained with QLoRA) for [`{base}`](https://huggingface.co/{base}).")
    else:
        added = lang in (meta.get("added_tokens") or [])
        what = (f"A full fine-tune of [`{base}`](https://huggingface.co/{base})"
                + (f" that adds {shawi} as a new language, `{lang}`." if added else "."))
    sib = ""
    if siblings:
        sib = " The other Uyari model" + ("s" if len(siblings) > 1 else "") + f" for {shawi}: " + "; ".join(
            f"[`{rid}`](https://huggingface.co/{rid}) ({bn}, {lic})" for rid, bn, lic in siblings) + "."

    head = [
        f"# Uyari · {shawi} ↔ {others} ({base_name})",
        "",
        f"Translation between [{shawi}]({BLOB}/languages/{lang}/README.md) "
        f"({iso_name or shawi}, ISO 639-3 `{info.get('iso639_3', lang[:3])}`) and "
        f"{_and([_short(p) for p in prims])}, "
        f"in all {n_dirs} directions. {what} Part of [Uyari]({GITHUB}), an open toolkit, data and models for "
        "translation between Indigenous and official languages.",
        "",
        f"Version **{version}** (`{model}` in Uyari), trained {str(meta.get('trained_at', ''))[:10]} on build "
        f"`{meta['build']}`.{sib}",
    ]

    n = max((test.get(_key(s, t)) or {}).get("n", 0) for s, t in dirs)
    table = ["| | Into " + shawi + " | From " + shawi + " |", "|---|---|---|"]
    for p in prims:
        into, out = test.get(_key(p, lang)) or {}, test.get(_key(lang, p)) or {}
        fmt = lambda x: "—" if x is None else f"{x:.1f}"  # noqa: E731
        table.append(f"| {_short(p)} | {fmt(into.get('chrf++'))} | {fmt(out.get('chrf++'))} |")
    fl = [v["chrf++"] for k, v in floor.items() if isinstance(v, dict) and v.get("chrf++") is not None
          and k in {_key(s, t) for s, t in dirs}]
    notes = []
    if fl:
        notes.append(f"The retrieval floor, the human translation of the most similar training sentence, scores "
                     f"{min(fl):.1f}–{max(fl):.1f} in every direction.")
    mt_refs = prims[1:]
    if mt_refs:
        notes.append(f"The {_and([_short(p) for p in mt_refs])} references are machine translations of the "
                     f"{_short(prims[0])}, and "
                     f"no {shawi} speaker has rated the output yet.")
    else:
        notes.append(f"No {shawi} speaker has rated the output yet.")
    notes.append(f"Validation and test per direction, with BLEU and the floor: [full model card]({BLOB}/models/"
                 f"{model}/MODEL_CARD.md).")
    scored = (" Scored through llama.cpp, as in the first usage example."
              if test.get("backend") == "ServerTranslator" else "")
    results_md = ["## Results", "",
                  f"chrF++ on the test split, scored once when this version was promoted ({n} sentences per "
                  f"direction).{scored}", "", *table, "", " ".join(notes)]

    counts = man.get("counts") or {}
    domains = len(counts.get("chunks_translated_by_domain") or {})
    lic_names = ", ".join(LICENSE_NAMES.get(k, k) for k in data_lic)
    recipe = yaml.safe_load((model_dir / "recipe.yaml").read_text(encoding="utf-8")) or {}
    if adapter:
        acfg = json.loads((_source_dir(model_dir, meta) / "adapter_config.json").read_text(encoding="utf-8"))
        method = (f"QLoRA, rank {acfg['r']}, on the language layers of the 4-bit base "
                  f"`{acfg['base_model_name_or_path']}`; the vision layers are not adapted. {meta['steps']:,} steps.")
    else:
        init = recipe.get("new_lang_token_init")
        method = (f"Full fine-tune, {meta['steps']:,} steps"
                  + (f"; the `{lang}` embedding starts from {_short(init)} (`{init}`)." if init else "."))
    training = [
        "## Training", "",
        f"* Data: {counts.get('pairs', '?'):,} human {shawi} translations of {_short(prims[0])} sentences"
        + (f" in {_num(domains)} everyday domains" if domains else "")
        + f", from {len((man.get('contributions') or {}).get('included') or [])} contributions ({lic_names}). "
        f"The {_short(prims[0])} sentences are synthetic, written by language models from a fixed design matrix"
        + (f"; the other {_num(len(mt_refs))} languages are machine translations of the {_short(prims[0])}." if mt_refs
           else "."),
        "* Splits by paraphrase group, so no paraphrase of a test sentence is in training.",
        f"* {method}",
        f"* Recipe [`{meta['recipe_id']}`]({BLOB}/recipes/{meta['recipe_file']}), build "
        f"[`{meta['build']}`]({BLOB}/builds/{meta['build']}/MANIFEST.json).",
    ]

    lic_lines = [f"* Weights: {LICENSE_NAMES.get(hub_license, hub_license)}, inherited from the base model."]
    if "nc" in hub_license.split("-"):
        free = [(rid, lic) for rid, _, lic in siblings if "NC" not in lic]
        lic_lines[0] += " Non-commercial" + (
            f": for commercial use, see [`{free[0][0]}`](https://huggingface.co/{free[0][0]}) ({free[0][1]})."
            if free else ".")
    lic_lines += [
        f"* Training data: {lic_names} ([`DATA_LICENSE.md`]({BLOB}/DATA_LICENSE.md)). If you build on this model, "
        f"say it comes from Uyari and link the repository ([`NOTICE`]({BLOB}/NOTICE)).",
        f"* A community or a contributor can withdraw their data ([governance]({BLOB}/contributing/en/governance.md)):"
        " later versions leave it out and this card says so.",
    ]
    citation = ["## Citation", "", "```bibtex", "@software{uyari2026,", f"  author = {{{AUTHOR}}},",
                "  title  = {Uyari: open toolkit, data and models for translation between Indigenous and official "
                "languages},", "  year   = {2026},", f"  url    = {{{GITHUB}}}", "}", "```"]

    body = [*head, "", usage(model_dir, meta, repo_id, info), "", *results_md, "", *training, "",
            "## Limitations", "", _card_section(card_md, "Limitations"), "",
            "## Intended use", "", _card_section(card_md, "Intended use"), "",
            "## License", "", *lic_lines, "", *citation]
    fm = yaml.safe_dump(front, sort_keys=False, allow_unicode=True, width=1000)
    return f"---\n{fm}---\n\n" + "\n".join(body) + "\n"


def publish(paths: Paths, model: str, namespace: str | None = None, private: bool = True,
            dry_run: bool = False) -> dict:
    """Write the README to ``runs/hub/<repo>/README.md``; unless ``dry_run``, create or update the repository
    in one commit and tag it with the version."""
    from uyari.privacy import find_names

    model_dir = paths.models / model
    meta = read_meta(model_dir)
    if not namespace:
        from huggingface_hub import HfApi

        try:
            namespace = HfApi().whoami()["name"]
        except Exception as e:  # noqa: BLE001 - no token, bad token, offline
            raise RuntimeError(f"pass --namespace, or set HF_TOKEN in .env ({e})") from e
    repo_id = f"{namespace}/{repo_name(model)}"
    text = readme(paths, model, namespace)
    found = find_names(paths, text)
    if found:
        raise RuntimeError(f"private names in the README: {found}")
    stage = paths.runs / "hub" / repo_name(model)
    stage.mkdir(parents=True, exist_ok=True)
    (stage / "README.md").write_text(text, encoding="utf-8", newline="\n")
    files = files_to_upload(model_dir, meta)
    version = model.split("@")[1]
    out = {"repo": repo_id, "url": f"https://huggingface.co/{repo_id}", "version": version,
           "private": private, "readme": str(stage / "README.md"),
           "files": [f.name for f in files] + ["README.md"],
           "upload_gb": round(sum(f.stat().st_size for f in files) / 1e9, 2),
           "privacy": "skipped: no private name list on this machine" if found is None else "clean",
           "links_not_on_origin_main": unpushed_links(paths, meta)}
    if dry_run:
        return out

    from huggingface_hub import CommitOperationAdd, CommitOperationDelete, HfApi

    api = HfApi()
    api.create_repo(repo_id, private=private, exist_ok=True)
    keep = {f.name for f in files} | {"README.md", ".gitattributes"}
    ops = [CommitOperationDelete(path_in_repo=p) for p in api.list_repo_files(repo_id) if p not in keep]
    ops += [CommitOperationAdd(path_in_repo=f.name, path_or_fileobj=str(f)) for f in files]
    ops.append(CommitOperationAdd(path_in_repo="README.md", path_or_fileobj=text.encode("utf-8")))
    info = api.create_commit(repo_id, operations=ops, commit_message=f"Uyari {model} (build {meta['build']})")
    api.create_tag(repo_id, tag=version, revision=info.oid, exist_ok=True)
    out["commit"] = info.oid
    out["deleted"] = [o.path_in_repo for o in ops if isinstance(o, CommitOperationDelete)]
    return out
