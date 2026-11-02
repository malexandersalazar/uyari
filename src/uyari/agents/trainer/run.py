"""Trainer: build -> train -> evaluate -> promote -> card -> NEEDS.md -> pull request.

Triggered by ``.github/workflows/train.yml`` on a merge into main (self-hosted GPU runner) or by
hand. Every decision is written to ``runs/trainer/<tag>/decision.json`` and the PR body with the
numbers that produced it.

Decisions:
  * Cut a build only for a new language or >= ``min_growth`` (10%) more pairs than the latest
    build (``--force-build`` overrides).
  * Run the language's loop recipes (``language.yaml: trainer.recipes``) re-pointed at the new
    build, with the model's minor version bumped.
  * Promote only if mean validation chrF++ beats the incumbent (re-scored on the *same* build)
    by >= 0.5 on the directions both share (or adds directions and loses <= 0.5 on them) **and** every
    direction beats the retrieval floor. Validation only.
  * On promotion, and only then: score test once, write the model card, update the registry.
  * Guardrails: never merges, never reads test before promotion, never overwrites a card of an
    existing version (a new version is a new folder).
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

from uyari.build import latest_tag, load_manifest, run_build
from uyari.csvio import read_yaml, write_json, write_yaml
from uyari.data.languages import load_language
from uyari.paths import Paths
from uyari.recipes import load_recipe

PROMOTE_MARGIN = 0.5


def _mean(scores: dict, dirs: list[str]) -> float:
    vals = [scores[d]["chrf++"] or 0 for d in dirs]
    return sum(vals) / len(vals) if vals else 0.0


def promotion_margin_ok(cand: dict, inc: dict | None) -> bool:
    """Compared on the directions both models share: +0.5 mean chrF++, or, when the candidate adds
    directions the incumbent lacks (e.g. English), no more than 0.5 lost on the shared ones."""
    if inc is None:
        return True
    shared = [d for d in cand if ">" in d and d in inc]
    adds = [d for d in cand if ">" in d and d not in inc]
    if not shared:
        return True
    c, i = _mean(cand, shared), _mean(inc, shared)
    return c >= i + PROMOTE_MARGIN or (bool(adds) and c >= i - PROMOTE_MARGIN)


def _next_tag(paths: Paths) -> str:
    base = f"data-{date.today():%Y.%m}"
    if not (paths.builds / base / "MANIFEST.json").is_file():
        return base
    n = 2
    while (paths.builds / f"{base}-r{n}" / "MANIFEST.json").is_file():
        n += 1
    return f"{base}-r{n}"


def _bump(paths: Paths, output: str) -> str:
    """models/<name>@vX.Y -> next free minor version."""
    name, ver = Path(output).name.split("@v")
    major, _minor = (int(x) for x in ver.split("."))
    taken = [int(m.group(1)) for p in paths.models.glob(f"{name}@v{major}.*")
             if (m := re.search(rf"@v{major}\.(\d+)$", p.name))]
    return f"models/{name}@v{major}.{max(taken, default=-1) + 1}"


def _slot(method: str) -> str:
    return "promoted" if method == "qlora" else "fast"


def _git(paths: Paths, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=paths.code, capture_output=True, text=True, check=check)
    return r.stdout.strip()


def run_trainer(paths: Paths, language: str, open_pr: bool = False, force_build: bool = False,
                dry_run: bool = False, max_steps: int | None = None) -> dict:
    from uyari.agents.trainer.needs import write_needs
    from uyari.pipelines.mt.card import write_card
    from uyari.pipelines.mt.eval import run_eval
    from uyari.pipelines.mt.prepare import run_prepare
    from uyari.pipelines.mt.train import run_train
    from uyari.registry import promoted, set_slot
    from uyari.serve import gpu_session

    L = load_language(paths, language)
    log: dict = {"language": language, "started": date.today().isoformat(), "steps": []}

    # 1. build?
    prev = latest_tag(paths)
    prev_pairs = load_manifest(paths, prev)["languages"].get(language, {}).get("counts", {}).get("pairs") if prev else None
    probe = run_build(paths, "data-probe", dry_run=True, languages=[language])
    now_pairs = probe.manifest["languages"][language]["counts"]["pairs"]
    growth = None if not prev_pairs else (now_pairs - prev_pairs) / prev_pairs
    min_growth = float((L.cfg.get("trainer") or {}).get("min_growth", 0.10))
    worth = force_build or prev_pairs is None or (growth is not None and growth >= min_growth)
    log["build_decision"] = {"previous_tag": prev, "previous_pairs": prev_pairs, "pairs_now": now_pairs,
                             "growth": None if growth is None else round(growth, 4), "min_growth": min_growth,
                             "cut": worth}
    if not worth:
        log["result"] = "no new build: growth below threshold"
        write_needs(paths, language, prev)
        return log
    tag = _next_tag(paths)
    if dry_run:
        log["result"] = f"dry run: would cut {tag} and train {L.trainer_recipes}"
        return log
    run_build(paths, tag, languages=None)
    log["tag"] = tag
    rdir = paths.runs / "trainer" / tag
    rdir.mkdir(parents=True, exist_ok=True)

    # 2. train each loop recipe on the new build
    for rpath in L.trainer_recipes:
        base = load_recipe(paths.code / rpath)
        cfg = dict(base.cfg)
        cfg["build"] = tag
        cfg["output"] = _bump(paths, base.output)
        cfg["id"] = f"{base.id}.{tag}"
        derived = rdir / f"{cfg['id']}.yaml"
        write_yaml(derived, cfg, header=f"Derived by the Trainer from {rpath} for build {tag}.")
        step = {"recipe": rpath, "derived": str(derived.relative_to(paths.data).as_posix()), "output": cfg["output"]}
        with gpu_session(paths, f"trainer {cfg['id']}"):
            run_prepare(paths, derived)
            run_train(paths, derived, max_steps=max_steps)
            cand = run_eval(paths, cfg["output"], "validation")["validation"]
            floor = run_eval(paths, "retrieval", "validation", recipe=derived)["validation"]
            slot = _slot(cfg["method"])
            inc_ref = promoted(paths, "mt", language, slot)
            inc = None
            if inc_ref and (paths.models / inc_ref).is_dir():
                # re-score the incumbent on the same build so the comparison is fair (cheap for NLLB)
                inc = _rescore_on(paths, inc_ref, tag, rdir)
        dirs = [k for k in cand if ">" in k]
        beats_floor = all((cand[d]["chrf++"] or 0) > (floor[d]["chrf++"] or 0) for d in dirs)
        margin_ok = promotion_margin_ok(cand, inc)
        step.update({"slot": slot, "candidate": {d: cand[d]["chrf++"] for d in dirs} | {"mean": cand["mean_chrf++"]},
                     "floor": {d: floor[d]["chrf++"] for d in dirs},
                     "incumbent": inc_ref, "incumbent_same_build": inc,
                     "beats_floor": beats_floor, "beats_incumbent_by_0.5": margin_ok})
        if beats_floor and margin_ok:
            name = Path(cfg["output"]).name
            with gpu_session(paths, f"trainer test {name}"):
                test = run_eval(paths, cfg["output"], "test")["test"]
            set_slot(paths, "mt", language, slot, name,
                     reason=f"validation mean chrF++ {cand['mean_chrf++']} vs incumbent "
                            f"{(inc or {}).get('mean_chrf++')} and floor {floor['mean_chrf++']} on {tag}")
            write_card(paths, paths.models / name)
            step.update({"decision": "promoted", "test": {d: test[d]["chrf++"] for d in dirs}})
        else:
            step["decision"] = "kept incumbent"
        log["steps"].append(step)

    needs = write_needs(paths, language, tag)
    log["needs_first_line"] = needs.splitlines()[2] if len(needs.splitlines()) > 2 else ""
    write_json(rdir / "decision.json", log)
    if open_pr:
        log["pr"] = _open_pr(paths, language, tag, log)
    return log


def _rescore_on(paths: Paths, ref: str, tag: str, rdir: Path) -> dict:
    """Validation scores of an existing model on another build (written to runs/, not its card)."""
    from uyari.pipelines.mt.common import read_meta
    from uyari.pipelines.mt.eval import eval_rows, score_translator, sources_of
    from uyari.pipelines.mt.infer import load_translator

    d = paths.models / ref
    meta = read_meta(d)
    rows = eval_rows(paths, tag, meta["language"], sources_of(meta), "validation")
    res, _ = score_translator(load_translator(paths, ref), rows, [tuple(x.split(">")) for x in meta["directions"]],
                              meta["language"])
    write_json(rdir / f"rescore.{ref}.json", res)
    return res


def _scores(model_dir: Path) -> dict:
    f = model_dir / "scores.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}


def _floor(paths: Paths, model_dir: Path, build: str, language: str, dirs: list[str], split: str) -> dict:
    """Retrieval floor on the model's build and directions: the stored one if complete, else scored now
    (TF-IDF over the train pairs; seconds, no GPU)."""
    from uyari.pipelines.mt.eval import run_eval

    f = paths.runs / "retrieval" / build / language / "scores.json"
    have = (json.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}).get(split) or {}
    if all(d in have for d in dirs) and have.get("limit") is None:
        return have
    return run_eval(paths, "retrieval", split, recipe=model_dir / "recipe.yaml")[split]


def register_model(paths: Paths, ref: str, slot: str | None = None, score_test: bool = True,
                   force: bool = False, reason: str = "") -> dict:
    """The Trainer's promotion rule for a model trained outside the loop (``make train-nllb``,
    ``make train-glimmer``): same checks, same records, no build and no PR.

    1. Validation from the model's ``scores.json`` (scored now if missing), the retrieval floor on the same
       build and directions, and the slot's incumbent on the same build (stored scores, or re-scored).
    2. Registered only if every direction beats the floor and :func:`promotion_margin_ok` holds, or with
       ``force`` and a reason (written to the registry history). Then: test once, registry, model card,
       and the incumbent's card is rewritten so it no longer says it is served.

    Slot by default: ``promoted`` (the demo default) for QLoRA models, ``fast`` for seq2seq (NLLB).
    """
    from uyari.pipelines.mt.card import write_card
    from uyari.pipelines.mt.common import read_meta
    from uyari.pipelines.mt.eval import run_eval
    from uyari.registry import promoted, set_slot
    from uyari.serve import gpu_session

    name = Path(ref).name
    d = paths.models / name
    meta = read_meta(d)
    lang, build = meta["language"], meta["build"]
    slot = slot or _slot(meta["method"])
    if slot not in ("promoted", "fast"):
        raise ValueError(f"slot must be 'promoted' or 'fast', not {slot!r}")
    if force and not reason.strip():
        raise ValueError("--force needs a --reason; it is written to models/registry.yaml")

    stored = _scores(d)
    cand = stored.get("validation")
    if not cand:
        with gpu_session(paths, f"register: validation {name}"):
            cand = run_eval(paths, ref, "validation")["validation"]
    dirs = [k for k in cand if ">" in k]
    floor = _floor(paths, d, build, lang, dirs, "validation")
    inc_ref = promoted(paths, "mt", lang, slot)
    out = {"model": name, "slot": slot, "build": build,
           "candidate": {k: cand[k]["chrf++"] for k in dirs} | {"mean": round(_mean(cand, dirs), 2)},
           "floor": {k: floor[k]["chrf++"] for k in dirs} | {"mean": round(_mean(floor, dirs), 2)},
           "incumbent": inc_ref}
    if inc_ref == name:
        return {**out, "decision": "already registered", "why": f"{name} already holds the {slot} slot"}

    inc = None
    if inc_ref and (paths.models / inc_ref).is_dir():
        inc_stored = _scores(paths.models / inc_ref).get("validation")
        if read_meta(paths.models / inc_ref).get("build") == build and inc_stored:
            inc = inc_stored
        else:
            rdir = paths.runs / "register" / name
            rdir.mkdir(parents=True, exist_ok=True)
            with gpu_session(paths, f"register: re-score {inc_ref}"):
                inc = _rescore_on(paths, inc_ref, build, rdir)
    shared = [k for k in dirs if inc and k in inc]
    beats_floor = all((cand[k]["chrf++"] or 0) > (floor[k]["chrf++"] or 0) for k in dirs)
    margin_ok = promotion_margin_ok(cand, inc)
    out.update({"incumbent_shared": {k: inc[k]["chrf++"] for k in shared} if inc else None,
                "beats_floor": beats_floor, "margin_ok": margin_ok})

    if not (beats_floor and margin_ok):
        why = []
        if not beats_floor:
            why.append("below the retrieval floor in " + ", ".join(
                k for k in dirs if (cand[k]["chrf++"] or 0) <= (floor[k]["chrf++"] or 0)))
        if not margin_ok:
            why.append(f"does not beat {inc_ref} on {', '.join(shared)} "
                       f"({_mean(cand, shared):.2f} vs {_mean(inc, shared):.2f}; rule: +{PROMOTE_MARGIN}, or adds "
                       f"directions and loses <= {PROMOTE_MARGIN})")
        if not force:
            return {**out, "decision": "not registered", "why": "; ".join(why)}
        out["overridden"] = "; ".join(why)

    if score_test:
        test = stored.get("test")
        if not test:
            with gpu_session(paths, f"register: test {name}"):
                test = run_eval(paths, ref, "test")["test"]
        _floor(paths, d, build, lang, dirs, "test")
        out["test"] = {k: test[k]["chrf++"] for k in dirs if k in test}

    numbers = (f"validation mean chrF++ {out['candidate']['mean']} vs floor {out['floor']['mean']}"
               + (f" and {inc_ref} {_mean(inc, shared):.2f} on {', '.join(shared)}" if inc and shared else "")
               + f" on {build}")
    set_slot(paths, "mt", lang, slot, name,
             reason=(f"forced: {reason.strip()} ({numbers})" if out.get("overridden")
                     else f"{reason.strip()}: {numbers}" if reason.strip() else numbers))
    write_card(paths, d)
    if inc_ref and (paths.models / inc_ref / "MODEL_CARD.md").is_file():
        write_card(paths, paths.models / inc_ref)
    return {**out, "decision": "registered", "why": numbers}


def _open_pr(paths: Paths, language: str, tag: str, log: dict) -> str:
    branch = f"trainer/{tag}"
    files = [f"builds/{tag}/MANIFEST.json", f"languages/{language}/NEEDS.md", "models/registry.yaml"]
    for s in log["steps"]:
        mdir = Path(s["output"])
        for f in ("MODEL_CARD.md", "scores.json", "uyari_meta.json", "recipe.yaml"):
            if (paths.data / mdir / f).is_file():
                files.append((mdir / f).as_posix())
        if (paths.data / mdir / "eval").is_dir():
            files.append((mdir / "eval").as_posix())
    _git(paths, "checkout", "-B", branch)
    _git(paths, "add", "--", *[f for f in files if (paths.data / f).exists()])
    _git(paths, "commit", "-m", f"Trainer: build {tag} for {language}\n\n" + json.dumps(
        [{k: s.get(k) for k in ("recipe", "decision", "candidate", "floor")} for s in log["steps"]], indent=1))
    _git(paths, "push", "-u", "origin", branch)
    body = ["Automated by the Uyari Trainer.", "", f"Build `{tag}`: {log['build_decision']}", ""]
    for s in log["steps"]:
        body += [f"### {s['recipe']} → `{s['output']}`: **{s['decision']}**", "",
                 f"- validation chrF++: {s['candidate']}", f"- retrieval floor: {s['floor']}",
                 f"- incumbent ({s['incumbent']}) on this build: {(s.get('incumbent_same_build') or {}).get('mean_chrf++')}",
                 f"- test (scored once, on promotion): {s.get('test', '—')}", ""]
    needs = (paths.languages / language / "NEEDS.md").read_text(encoding="utf-8")
    body += ["---", needs]
    r = subprocess.run(["gh", "pr", "create", "--base", "main", "--head", branch, "--title",
                        f"Trainer: {language} on {tag}", "--body", "\n".join(body)],
                       cwd=paths.code, capture_output=True, text=True)
    _ = read_yaml
    return r.stdout.strip() or r.stderr.strip()
