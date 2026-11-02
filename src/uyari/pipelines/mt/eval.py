"""``uyari eval``: chrF++ (main) and BLEU per direction and per domain.

Validation selects and compares models (any number of times). Test is scored with ``--final``
once per model version: ``scores.json`` refuses a second test entry. Hypotheses are saved next
to the scores (``eval/<split>.<src>-<tgt>.jsonl``) for the side-by-side page.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from uyari.build import read_table
from uyari.csvio import write_json, write_jsonl
from uyari.paths import Paths
from uyari.pipelines.mt.common import read_meta
from uyari.pipelines.mt.metrics import by_group, corpus_scores
from uyari.recipes import load_recipe


class TestAlreadyScored(RuntimeError):
    pass


def eval_rows(paths: Paths, tag: str, lang: str, primaries: str | list[str], split: str) -> list[dict]:
    primaries = [primaries] if isinstance(primaries, str) else list(primaries)
    rows = read_table(paths, tag, lang, "mt", test=(split == "test"))
    return [r for r in rows if r["split"] == split and r["src_lang"] in primaries]


def sources_of(meta: dict) -> list[str]:
    return list(meta.get("primaries") or [meta["primary"]])


def score_translator(tr, rows: list[dict], directions: list[tuple[str, str]], language: str,
                     limit: int | None = None) -> tuple[dict, dict[str, list[dict]]]:
    """Score every direction on the rows of its own language pair. ``language`` is the Indigenous one."""
    res, hyps_out = {}, {}
    for s, t in directions:
        off = t if s == language else s
        rs = sorted((r for r in rows if r["src_lang"] == off), key=lambda r: (r["chunk_id"], r["tgt_text"]))
        if limit:
            rs = rs[:limit]
        src = [r["src_text"] if s == off else r["tgt_text"] for r in rs]
        ref = [r["tgt_text"] if s == off else r["src_text"] for r in rs]
        uniq = sorted(set(src))
        hyp_map = dict(zip(uniq, tr.translate(uniq, s, t), strict=True))
        hyp = [hyp_map[x] for x in src]
        key = f"{s[:3]}>{t[:3]}"
        res[key] = {**corpus_scores(hyp, ref), "by_domain": by_group(hyp, ref, [r["domain"] for r in rs])}
        hyps_out[key] = [{"chunk_id": r["chunk_id"], "domain": r["domain"], "src": a, "ref": b, "hyp": h}
                         for r, a, b, h in zip(rs, src, ref, hyp, strict=True)]
    vals = [v["chrf++"] for v in res.values() if v["chrf++"] is not None]
    res["mean_chrf++"] = round(sum(vals) / len(vals), 2) if vals else None
    return res, hyps_out


def _write_hyps(d: Path, split: str, hyps: dict[str, list[dict]]) -> None:
    for key, rows in hyps.items():
        write_jsonl(d / "eval" / f"{split}.{key.replace('>', '-')}.jsonl", rows)


def run_eval(paths: Paths, ref: str, split: str = "validation", recipe: Path | str | None = None,
             limit: int | None = None) -> dict:
    stamp = datetime.now(UTC).isoformat(timespec="seconds")
    if ref == "retrieval":
        if recipe is None:
            raise ValueError("--recipe is required for the retrieval floor (it names the build and language)")
        from uyari.pipelines.mt.infer import RetrievalTranslator

        rc = load_recipe(recipe)
        tr = RetrievalTranslator(paths, rc.build, rc.language)
        rows = eval_rows(paths, rc.build, rc.language, rc.sources, split)
        res, hyps = score_translator(tr, rows, rc.directions(), rc.language, limit)
        d = paths.runs / "retrieval" / rc.build / rc.language
        prev = json.loads((d / "scores.json").read_text(encoding="utf-8")) if (d / "scores.json").is_file() else {}
        old = prev.get(split) or {}
        # keep directions scored earlier by a recipe with other sources (e.g. Spanish only), same limit only
        kept = {k: v for k, v in old.items() if ">" in k} if old.get("limit") == limit else {}
        prev[split] = {**kept, **res, "scored_at": stamp, "limit": limit}
        write_json(d / "scores.json", prev)
        _write_hyps(d, split, hyps)
        return {"model": "retrieval", "build": rc.build, split: res}

    from uyari.pipelines.mt.infer import load_translator, model_dir

    d = model_dir(paths, ref)
    meta = read_meta(d)
    scores_f = d / "scores.json"
    scores = json.loads(scores_f.read_text(encoding="utf-8")) if scores_f.is_file() else {}
    if split == "test" and "test" in scores:
        raise TestAlreadyScored(f"{meta['name']} already has a test score ({scores['test'].get('scored_at')}); "
                                "test is scored once per model version")
    lim = limit if limit is not None else (meta.get("eval") or {}).get("limit")
    tr = load_translator(paths, ref)
    rows = eval_rows(paths, meta["build"], meta["language"], sources_of(meta), split)
    dirs = [tuple(x.split(">")) for x in meta["directions"]]
    res, hyps = score_translator(tr, rows, dirs, meta["language"], lim)
    scores[split] = {**res, "scored_at": stamp, "limit": lim, "backend": type(tr).__name__}
    write_json(scores_f, scores)
    _write_hyps(d, split, hyps)
    return {"model": meta["name"], "build": meta["build"], split: res}
