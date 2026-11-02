"""Training-data generation: build table -> model-ready examples.

``uyari prepare --recipe R`` reads ``builds/<tag>/<lang>/mt.parquet`` (train + validation;
the test file is never opened here), applies the recipe's filters, expands each pair into the
recipe's directions, formats chat prompts for causal LMs, and checks that the tokenizer can
represent every character (after the recipe's codec). Output:

  runs/<recipe id>/data/train.jsonl, validation.jsonl, stats.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from uyari.build import load_manifest, read_table
from uyari.csvio import write_json, write_jsonl
from uyari.paths import Paths
from uyari.pipelines.mt import prompts
from uyari.pipelines.mt.codec import Codec
from uyari.recipes import Recipe, load_recipe


class CoverageError(RuntimeError):
    pass


@dataclass
class Prepared:
    dir: Path
    stats: dict = field(default_factory=dict)


def examples_for(rows: list[dict], recipe: Recipe) -> list[dict]:
    """Expand build rows (official -> Indigenous) into directed examples (canonical text). A row pairs one
    official language with the Indigenous one; it feeds the directions between those two."""
    out = []
    dirs = recipe.directions()
    for r in rows:
        if r["src_lang"] not in recipe.sources or r["tgt_lang"] != recipe.language:
            continue
        for s, t in dirs:
            if recipe.official_of(s, t) != r["src_lang"]:
                continue
            src, tgt = (r["src_text"], r["tgt_text"]) if s == r["src_lang"] else (r["tgt_text"], r["src_text"])
            out.append({
                "id": f"{r['chunk_id']}:{s[:3]}>{t[:3]}:{hashlib.sha1(r['tgt_text'].encode('utf-8')).hexdigest()[:8]}",
                "chunk_id": r["chunk_id"], "split": r["split"], "domain": r["domain"],
                "src_lang": s, "tgt_lang": t, "src": src, "tgt": tgt,
                "contribution": r["contribution"]})
    return out


def apply_filters(rows: list[dict], recipe: Recipe) -> list[dict]:
    f = recipe.filters
    if f.get("provenance"):
        rows = [r for r in rows if r["provenance"] in f["provenance"]]
    if f.get("licenses"):
        rows = [r for r in rows if r["license"] in f["licenses"]]
    return rows


def model_view(ex: dict, recipe: Recipe, codec: Codec) -> dict:
    """What the model reads/writes: codec applied to the Indigenous side only."""
    enc = lambda lang, s: codec.encode(s) if lang == recipe.language else s  # noqa: E731
    m = {**ex, "src_model": enc(ex["src_lang"], ex["src"]), "tgt_model": enc(ex["tgt_lang"], ex["tgt"])}
    if recipe.method == "qlora":
        m["prompt"] = prompts.messages(ex["src_lang"], ex["tgt_lang"], m["src_model"])
        m["completion"] = [{"role": "assistant", "content": m["tgt_model"]}]
    return m


def check_coverage(recipe: Recipe, texts: list[str]) -> dict:
    """Characters the tokenizer cannot represent (maps to unk). Byte-level BPE has full coverage."""
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(recipe.base_model)
    chars = sorted({ch for t in texts for ch in t if not ch.isspace()})
    unk = tok.unk_token_id
    bad = []
    if unk is not None:
        for ch in chars:
            ids = tok(ch, add_special_tokens=False)["input_ids"]
            if unk in ids:
                bad.append(ch)
    import unicodedata

    letters = [c for c in bad if unicodedata.category(c)[0] in ("L", "M")]
    other = [c for c in bad if c not in letters]
    return {"chars": len(chars), "unk_chars": [f"U+{ord(c):04X} {c}" for c in letters],
            "unk_punctuation": [f"U+{ord(c):04X} {c}" for c in other], "tokenizer": type(tok).__name__}


def run_prepare(paths: Paths, recipe_path: Path | str, check_tokenizer: bool = True) -> Prepared:
    recipe = load_recipe(recipe_path)
    codec = Codec(recipe.codec)
    rows = apply_filters(read_table(paths, recipe.build, recipe.language, "mt"), recipe)
    exs = examples_for(rows, recipe)
    by_split = {s: [e for e in exs if e["split"] == s] for s in ("train", "validation")}
    indig = [e["src"] for e in exs if e["src_lang"] == recipe.language] + \
            [e["tgt"] for e in exs if e["tgt_lang"] == recipe.language]
    clash = codec.check_reversible(indig)
    if clash:
        raise CoverageError(f"codec not reversible: {len(clash)} texts already contain {list(codec.rev)} "
                            f"(e.g. {clash[0][:60]!r})")
    stats = {
        "recipe": recipe.id, "build": recipe.build,
        "build_content_sha256": load_manifest(paths, recipe.build)["languages"][recipe.language]["tables"]["mt"][
            "content_sha256"],
        "rows_after_filters": len(rows),
        "examples": {s: len(v) for s, v in by_split.items()},
        "by_direction": {s: dict(Counter(f"{e['src_lang'][:3]}>{e['tgt_lang'][:3]}" for e in v))
                         for s, v in by_split.items()},
        "codec": recipe.codec,
    }
    if check_tokenizer:
        model_texts = [codec.encode(t) for t in indig] + [e["src"] for e in exs if e["src_lang"] in recipe.sources]
        cov = check_coverage(recipe, model_texts)
        stats["coverage"] = cov
        if cov["unk_chars"]:
            raise CoverageError(f"tokenizer of {recipe.base_model} cannot represent {cov['unk_chars']}; add them "
                                "to the recipe's text_codec")
    out = recipe.run_dir(paths) / "data"
    for s, v in by_split.items():
        write_jsonl(out / f"{s}.jsonl", [model_view(e, recipe, codec) for e in v])
    write_json(out / "stats.json", stats)
    _ = json
    return Prepared(dir=out, stats=stats)
