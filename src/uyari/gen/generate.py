"""``uyari generate run``: send pending plan units to the model, validate, stage.

Meta Responses API calls (Muse Spark) or a local OpenAI-compatible server (Muse Glimmer), with
bounded concurrency and retries. Responses arrive inline, so collection happens in the same run.

Never pays twice: every raw response is appended to ``runs/gen/<batch>/responses.jsonl``
before it is parsed; a unit whose response is cached is collected from the cache.

Outputs (staging; ``uyari generate dedup`` publishes the clean batch into primary/):
  runs/gen/<batch>/raw.csv            accepted texts, chunk columns, append-only
  runs/gen/<batch>/text_hashes.txt    dedup keys already written (append-only sidecar)
  runs/gen/<batch>/failures.jsonl     every rejected text or failed unit, with the reason
"""

from __future__ import annotations

import hashlib
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean

from rich.table import Table

from uyari.csvio import append_csv, append_jsonl, read_csv, read_jsonl
from uyari.data.primary import chunk_columns, load_primary
from uyari.gen.collect import TextValidator, parse_texts
from uyari.gen.matrix import Matrix
from uyari.gen.plan import PRIMARY, batch_dir, load_plan, now_iso, save_plan
from uyari.gen.prompts import SYSTEM_PROMPT, TEXTS_SCHEMA, build_prompt
from uyari.llm.catalog import load_catalog
from uyari.llm.client import LLMClient, LLMError, confirm
from uyari.llm.ledger import BudgetExceeded, Ledger, RunBudget
from uyari.llm.tokens import count
from uyari.paths import Paths
from uyari.text.normalize import dedup_key, normalize_official


def expected_output_tokens(unit: dict, m: Matrix, est: dict) -> int:
    mid = (unit["wc_min"] + unit["wc_max"]) / 2
    per_text = mid * float(est.get("output_tokens_per_word", 2.0)) + float(est.get("json_overhead_tokens_per_text", 8))
    return int(unit["n_texts"] * per_text + float(est.get("reasoning_allowance_tokens", 256)))


def estimate(paths: Paths, units: list[dict], m: Matrix, model: str) -> dict:
    cat = load_catalog(paths)
    spec, est = cat.get(model), cat.estimate
    f = float(est.get("input_safety_factor", 1.2))
    sys_t = count(SYSTEM_PROMPT)
    inp = [int((sys_t + count(build_prompt(u, m.lengths))) * f) for u in units]
    out = [expected_output_tokens(u, m, est) for u in units]
    exp = sum(spec.cost(i, 0, o) for i, o in zip(inp, out, strict=True))
    lo_m, hi_m = (est.get("low_high_band") or [0.7, 1.5])
    return {"model": spec.key, "requests": len(units), "texts": sum(u["n_texts"] for u in units),
            "input_tokens": sum(inp), "output_tokens": sum(out), "expected_usd": exp, "low_usd": exp * lo_m,
            "high_usd": exp * hi_m, "per_request_usd": [spec.cost(i, 0, o) for i, o in zip(inp, out, strict=True)],
            "price_per_mtok": {"input": spec.price_input, "cached": spec.price_cached, "output": spec.price_output}}


def _print_estimate(console, e: dict, cap: float, remaining: float) -> None:
    t = Table(title=f"Estimate ({e['model']}; tiktoken o200k approximation, not the provider's tokenizer)")
    t.add_column("item")
    t.add_column("value", justify="right")
    for k, v in [("requests", e["requests"]), ("texts requested", e["texts"]),
                 ("input tokens", f"{e['input_tokens']:,}"), ("output tokens (incl. reasoning allowance)",
                                                              f"{e['output_tokens']:,}"),
                 ("expected USD", f"${e['expected_usd']:.4f}"),
                 ("range USD", f"${e['low_usd']:.4f} - ${e['high_usd']:.4f}"),
                 ("run cap USD", f"${cap:.2f}"), ("project budget remaining", f"${remaining:.2f}")]:
        t.add_row(k, str(v))
    console.print(t)


class Collector:
    """Parse, validate and stage the texts of one response.

    Staged chunk ids are deterministic (``md5(batch:custom_id:index)``) so re-collecting the same
    cached responses gives the same rows. Writes raw.csv first, then the hash sidecar (a crash
    between them can only duplicate, never lose)."""

    def __init__(self, paths: Paths, batch: str, meta: dict, m: Matrix):
        self.d, self.batch, self.meta = batch_dir(paths, batch), batch, meta
        pc = load_primary(paths, PRIMARY)
        published = [r for r in pc.chunks.values() if r.get("source_batch_id") != batch]
        seen = {dedup_key(r["text"]) for r in published}
        self.hashes_f = self.d / "text_hashes.txt"
        if self.hashes_f.is_file():
            seen |= {line.strip() for line in self.hashes_f.open(encoding="utf-8") if line.strip()}
        if (self.d / "raw.csv").is_file():
            seen |= {dedup_key(r["text"]) for r in read_csv(self.d / "raw.csv")}
        self.validator = TextValidator(m.validation, seen, lexicon=spanish_lexicon(published))
        self.counts: Counter = Counter()
        self.cols = chunk_columns()

    def collect(self, unit: dict, resp: dict) -> None:
        texts = parse_texts(resp.get("text", ""))
        self.counts["texts_returned"] += len(texts)
        self.counts[f"returned_{len(texts)}"] += 1
        rows, new_hashes = [], []
        for i, t in enumerate(texts):
            ok, why, info = self.validator.check(t, unit)
            if not ok:
                self.counts[f"rejected_{why}"] += 1
                append_jsonl(self.d / "failures.jsonl", {"custom_id": unit["custom_id"], "reason": why, "text": t,
                                                         **info, "at": now_iso()})
                continue
            text = normalize_official(t)
            cid = hashlib.md5(f"{self.batch}:{unit['custom_id']}:{i}".encode()).hexdigest()  # noqa: S324 - an id
            rows.append({"chunk_id": cid, "text": text, "split": "", "origin": "synthetic",
                         "status": "active", "supersedes": "", "domain_l1": unit["domain_l1"],
                         "domain_l2": unit["domain_l2"], "register": unit["register"],
                         "acto_comunicativo": unit["acto_comunicativo"], "tiempo_aspecto": unit["tiempo_aspecto"],
                         "polaridad": unit["polaridad"], "persona_deixis": unit["persona_deixis"],
                         "length_bucket": unit["length_bucket"], "word_count": info["word_count"],
                         "perfil_hablante": unit["perfil_hablante"], "tono_emocional": unit["tono_emocional"],
                         "discurso_conectado": "true" if unit["discurso_conectado"] else "false",
                         "palabras_ancla": ";".join(unit["palabras_ancla"]),
                         "source_custom_id": unit["custom_id"], "source_batch_id": self.batch,
                         "regen_of": unit.get("regen_of", ""), "gen_model": self.meta["model_id"],
                         "provider": self.meta["provider"], "gen_date": resp.get("sent_at") or now_iso(),
                         "prompt_version": self.meta["prompt_version"]})
            new_hashes.append(dedup_key(text))
        append_csv(self.d / "raw.csv", rows, self.cols)
        with self.hashes_f.open("a", encoding="utf-8", newline="\n") as f:
            f.writelines(h + "\n" for h in new_hashes)
        self.counts["texts_accepted"] += len(rows)
        unit["status"] = "done"


def spanish_lexicon(rows: list[dict]) -> set[str]:
    """Lower-cased word forms of the published Spanish primary (for the Spanish check)."""
    import re

    return {w for r in rows for w in re.findall(r"[a-záéíóúüñ]+", r["text"].lower())}


def recollect(paths: Paths, batch: str, console=None) -> dict:
    """Rebuild the staged batch from the cached responses: no API call, no cost. Use after a
    validation rule changes. Request failures are kept; text rejections are recomputed."""
    units, meta = load_plan(paths, batch)
    m = Matrix.load(paths.data / meta["matrix"])
    d = batch_dir(paths, batch)
    latest = {r["custom_id"]: r for r in read_jsonl(d / "responses.jsonl")}
    kept = [f for f in read_jsonl(d / "failures.jsonl") if f.get("reason") == "request_failed"]
    for f in ("raw.csv", "text_hashes.txt", "failures.jsonl"):
        (d / f).unlink(missing_ok=True)
    for f in kept:
        append_jsonl(d / "failures.jsonl", f)
    col = Collector(paths, batch, meta, m)
    for u in units:
        if u["custom_id"] in latest:
            col.collect(u, latest[u["custom_id"]])
    save_plan(paths, batch, units)
    out = {"recollected_units": sum(1 for u in units if u["custom_id"] in latest), "api_calls": 0, **dict(col.counts)}
    if console:
        console.print_json(data=out)
    return out


def run_generate(paths: Paths, batch: str, estimate_only: bool = False, max_usd: float | None = None,
                 concurrency: int = 8, limit: int | None = None, assume_yes: bool = False, console=None):
    units, meta = load_plan(paths, batch)
    m = Matrix.load(paths.data / meta["matrix"])
    if m.prompt_version() != meta["prompt_version"]:
        raise RuntimeError(f"matrix/prompt changed since the plan was made ({meta['prompt_version']} -> "
                           f"{m.prompt_version()}); start a new batch")
    d = batch_dir(paths, batch)
    cached = {r["custom_id"]: r for r in read_jsonl(d / "responses.jsonl")}
    pending = [u for u in units if u["status"] == "pending"]
    to_send = [u for u in pending if u["custom_id"] not in cached]
    to_collect = [u for u in pending if u["custom_id"] in cached]
    if limit:
        to_send = to_send[:limit]

    cat = load_catalog(paths)
    ledger = Ledger(paths)
    cap = cat.run_cap("generate") if max_usd is None else float(max_usd)
    e = estimate(paths, to_send, m, meta["model"])
    if console:
        _print_estimate(console, e, cap, cat.total_usd - ledger.spent())
        if to_collect:
            console.print(f"{len(to_collect)} unit(s) already paid for: collected from responses.jsonl")
    if estimate_only:
        return e
    budget = RunBudget(ledger, f"gen-{batch}-{uuid.uuid4().hex[:6]}", cap_usd=cap)
    if to_send:
        budget.check_plan(e["expected_usd"])
        if not confirm(f"Send {len(to_send)} request(s) to {meta['model']}, expected ${e['expected_usd']:.4f} "
                       f"(cap ${cap:.2f})?", assume_yes):
            return {"sent": 0}

    col = Collector(paths, batch, meta, m)
    counts = col.counts
    collect = col.collect
    by_cid = {u["custom_id"]: u for u in units}

    for u in to_collect:
        collect(u, cached[u["custom_id"]])

    client = LLMClient(paths, meta["model"], "official", "generate", budget, batch=batch) if to_send else None
    per_req = dict(zip([u["custom_id"] for u in to_send], e["per_request_usd"], strict=True))

    def send(u: dict) -> tuple[dict, dict | None, str]:
        u["attempts"] = u.get("attempts", 0) + 1
        try:
            r = client.respond(SYSTEM_PROMPT, build_prompt(u, m.lengths), schema=TEXTS_SCHEMA, max_output_tokens=4096,
                               expected_cost=per_req[u["custom_id"]], meta={"custom_id": u["custom_id"]})
        except (LLMError, BudgetExceeded) as ex:
            return u, None, str(ex)
        rec = {"custom_id": u["custom_id"], "text": r.text, "input_tokens": r.input_tokens,
               "cached_tokens": r.cached_tokens, "output_tokens": r.output_tokens,
               "reasoning_tokens": r.reasoning_tokens, "cost_usd": r.cost_usd, "latency_s": r.latency_s,
               "request_id": r.request_id, "sent_at": now_iso()}
        append_jsonl(d / "responses.jsonl", rec)
        return u, rec, ""

    t0 = time.time()
    done = 0
    stop_reason = ""
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        futs = [ex.submit(send, u) for u in to_send]
        for fut in as_completed(futs):
            u, rec, err = fut.result()
            unit = by_cid[u["custom_id"]]
            if rec is None:
                counts["failed_requests"] += 1
                append_jsonl(d / "failures.jsonl", {"custom_id": u["custom_id"], "reason": "request_failed",
                                                    "error": err[:300], "at": now_iso()})
                if "cap" in err:
                    stop_reason = err
                continue
            collect(unit, rec)
            done += 1
            if done % 20 == 0:
                save_plan(paths, batch, units)
                if console:
                    console.print(f"  {done}/{len(to_send)} done, spent ${budget.spent_usd:.4f}")
    save_plan(paths, batch, units)
    wall = time.time() - t0
    lat = [r["latency_s"] for r in read_jsonl(d / "responses.jsonl")]
    summary = {"sent": done, "collected_from_cache": len(to_collect), "spent_usd": round(budget.spent_usd, 6),
               "estimate_usd": round(e["expected_usd"], 6), "wall_seconds": round(wall, 1),
               "texts_per_minute": round(counts["texts_accepted"] / (wall / 60), 1) if wall > 0 and done else None,
               "mean_latency_s": round(mean(lat), 2) if lat else None, **dict(counts)}
    if stop_reason:
        summary["stopped"] = stop_reason
    if console:
        console.print_json(data=summary)
    return summary
