"""Generation comparison between two batches of the same cells -> ``reports/gen-comparison.md``.

Batch A is the existing Claude Opus 4.8 batch; batch B regenerated the same matrix cells with
the same prompt (``regen_of``). Only metrics that can be measured fairly are filled; the 10k
was already filtered and deduplicated before it reached us, so A's rejection/duplicate rates
and throughput are "not recorded" unless the original ``corpus_data/`` logs are supplied.
No Shawi text is involved.
"""

from __future__ import annotations

import random
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from uyari.csvio import read_csv, read_jsonl, read_yaml, write_csv
from uyari.data.primary import chunk_files
from uyari.gen.collect import parse_texts
from uyari.gen.matrix import Matrix
from uyari.gen.plan import PRIMARY, batch_dir, load_plan
from uyari.gen.prompts import SYSTEM_PROMPT, build_prompt
from uyari.llm.catalog import load_catalog
from uyari.llm.ledger import Ledger
from uyari.llm.tokens import count
from uyari.paths import Paths
from uyari.text.normalize import dedup_key, word_count

NR = "not recorded"


def _batch_rows(paths: Paths, batch: str) -> list[dict]:
    f = [x for x in chunk_files(paths, PRIMARY) if x.stem == batch]
    return read_csv(f[0]) if f else []


def distinct2(texts: list[str]) -> float:
    bigrams, total = set(), 0
    for t in texts:
        w = t.lower().split()
        bg = list(zip(w, w[1:], strict=False))
        bigrams.update(bg)
        total += len(bg)
    return len(bigrams) / total if total else 0.0


def ttr(texts: list[str]) -> float:
    w = [x for t in texts for x in t.lower().split()]
    return len(set(w)) / len(w) if w else 0.0


def bucket_hit(rows: list[dict], lengths: dict) -> float:
    hits = [lengths[r["length_bucket"]]["wc_min"] <= word_count(r["text"]) <= lengths[r["length_bucket"]]["wc_max"]
            for r in rows if r.get("length_bucket") in lengths]
    return sum(hits) / len(hits) if hits else 0.0


def per_cell(rows: list[dict], key: str, fn) -> float:
    g = defaultdict(list)
    for r in rows:
        g[r[key]].append(r["text"])
    vals = [fn(v) for v in g.values() if len(v) > 1]
    return mean(vals) if vals else 0.0


def _pct(x) -> str:
    return f"{100 * x:.1f}%" if isinstance(x, float) else str(x)


def run_compare(paths: Paths, a: str, b: str, export_blind: bool = False, ratings: Path | None = None,
                semantic: bool = True) -> Path:
    units, meta = load_plan(paths, b)
    m = Matrix.load(paths.data / meta["matrix"])
    cells = {u["regen_of"] for u in units if u.get("regen_of")}
    rows_a = [r for r in _batch_rows(paths, a) if r["source_custom_id"] in cells]
    db = batch_dir(paths, b)
    rows_b_clean = _batch_rows(paths, b)
    rows_b_raw = read_csv(db / "raw.csv") if (db / "raw.csv").is_file() else []
    responses = read_jsonl(db / "responses.jsonl")
    failures = [f for f in read_jsonl(db / "failures.jsonl") if f.get("reason") != "request_failed"]
    dedup = read_yaml(db / "dedup_report.json") if (db / "dedup_report.json").is_file() else {}
    cat = load_catalog(paths)
    claude, muse = cat.models["claude-opus-4-8"], cat.get(meta["model"])

    # cost per 1,000 chunks
    spent_b = Ledger(paths).spent(batch=b)
    cost_b = spent_b / len(rows_b_clean) * 1000 if rows_b_clean else None
    groups_a = defaultdict(list)
    for r in rows_a:
        groups_a[r["source_custom_id"]].append(r)
    in_tok = out_tok = 0
    for rs in groups_a.values():
        u = {**rs[0], "n_texts": m["texts_per_request"], "palabras_ancla": [x for x in rs[0]["palabras_ancla"].split(";") if x],
             "discurso_conectado": rs[0]["discurso_conectado"] == "true"}
        in_tok += count(SYSTEM_PROMPT) + count(build_prompt(u, m.lengths))
        out_tok += count('{"texts": [' + ", ".join(f'"{r["text"]}"' for r in rs) + "]}")
    cost_a_full = claude.cost(in_tok, 0, out_tok)
    cost_a = cost_a_full * (1 - claude.batch_discount)
    cost_a_k = cost_a / len(rows_a) * 1000 if rows_a else None

    # B rates
    returned = sum(len(parse_texts(r.get("text", ""))) for r in responses)
    rejected = Counter(f["reason"] for f in failures)
    exact10_b = sum(1 for r in responses if len(parse_texts(r.get("text", ""))) == m["texts_per_request"]) / len(responses) if responses else None
    exact10_a = sum(1 for rs in groups_a.values() if len(rs) == m["texts_per_request"]) / len(groups_a) if groups_a else None
    dup_b = None
    if dedup and rows_b_raw:
        dup_b = (dedup.get("exact_duplicates", 0) + dedup.get("near_duplicates", 0)) / len(rows_b_raw)
    wall = None
    if responses:
        from datetime import datetime

        ts = sorted(datetime.fromisoformat(r["sent_at"]) for r in responses)
        span = (ts[-1] - ts[0]).total_seconds() + mean(r["latency_s"] for r in responses)
        wall = len(rows_b_raw) / (span / 60) if span > 0 else None

    # human blind read
    human = {"A": NR, "B": NR}
    blind_dir = paths.reports / "blind"
    if export_blind:
        rng = random.Random(7)
        sa = rng.sample(rows_a, min(50, len(rows_a)))
        sb = rng.sample(rows_b_clean, min(50, len(rows_b_clean)))
        items = [("A", r) for r in sa] + [("B", r) for r in sb]
        rng.shuffle(items)
        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = "lectura"
        ws.append(["id", "texto", "aceptable (si/no)", "comentario"])
        key = []
        for i, (src, r) in enumerate(items, 1):
            ws.append([i, r["text"], "", ""])
            key.append({"id": i, "batch": src, "chunk_id": r["chunk_id"]})
        blind_dir.mkdir(parents=True, exist_ok=True)
        wb.save(blind_dir / f"{a}_vs_{b}.xlsx")
        write_csv(paths.runs / "gen" / "compare" / f"{a}_vs_{b}.key.csv", key, ["id", "batch", "chunk_id"])
    if ratings:
        from uyari.ingest.xlsx import read_xlsx

        key = {r["id"]: r["batch"] for r in read_csv(paths.runs / "gen" / "compare" / f"{a}_vs_{b}.key.csv")}
        votes = defaultdict(list)
        for r in read_xlsx(Path(ratings)):
            v = (r.get("aceptable (si/no)") or "").strip().lower()
            if v:
                votes[key[r["id"]]].append(v in ("si", "sí", "yes", "y", "s"))
        human = {k: f"{100 * sum(v) / len(v):.0f}% of {len(v)}" for k, v in votes.items()} | \
                {k: NR for k in ("A", "B") if k not in votes}

    rows = [
        ("Model", "claude-opus-4-8 (Message Batches)", f"{muse.key}"),
        ("Matrix cells (same prompt, `prompt_version`)", f"{len(groups_a)} ({rows_a[0]['prompt_version'] if rows_a else ''})",
         f"{len(units)} ({meta['prompt_version']})"),
        ("Chunks after validation and dedup", len(rows_a), len(rows_b_clean)),
        ("Cost per 1,000 chunks (USD)",
         f"~${cost_a_k:.3f} (estimate: tiktoken o200k on prompts + surviving texts, list ${claude.price_input}/"
         f"${claude.price_output} per MTok, 50% batch discount)" if cost_a_k else NR,
         f"${cost_b:.4f} (ledger, exact)" if cost_b is not None else NR),
        ("Validation rejection rate", NR + " (the 10k arrived already filtered)",
         _pct(sum(rejected.values()) / returned) if returned else NR),
        ("Rejections by reason", NR, dict(rejected) or "none"),
        ("Duplicate rate (exact + embedding, within batch and vs. the 10k)", NR + " (already deduplicated)",
         _pct(dup_b) if dup_b is not None else NR),
        ("Length-bucket hit rate (strict bucket, no tolerance; final chunks of both)", _pct(bucket_hit(rows_a, m.lengths)),
         _pct(bucket_hit(rows_b_clean, m.lengths))),
        ("Requests returning exactly 10 texts", _pct(exact10_a) + " (after filtering: lower bound)" if exact10_a is not None else NR,
         _pct(exact10_b) if exact10_b is not None else NR),
        ("Distinct-2 per cell (mean)", f"{per_cell(rows_a, 'source_custom_id', distinct2):.3f}",
         f"{per_cell(rows_b_clean, 'source_custom_id', distinct2):.3f}"),
        ("Type-token ratio per cell (mean)", f"{per_cell(rows_a, 'source_custom_id', ttr):.3f}",
         f"{per_cell(rows_b_clean, 'source_custom_id', ttr):.3f}"),
        ("Human spot read: acceptable (blind, 50 each)", human.get("A", NR), human.get("B", NR)),
        ("Throughput (chunks per minute, wall clock)", NR + " (asynchronous batch)", f"{wall:.1f}" if wall else NR),
    ]
    ratio = f"{100 * cost_b / cost_a_k:.1f}%" if cost_b and cost_a_k else "n/a"
    md = [f"# Generation comparison: {a} vs {b}", "",
          "Same matrix cells, same system prompt and template (identical `prompt_version`); only the model and "
          "the transport differ. Generated by `uyari generate compare`.", "",
          "| Measure | A: Claude Opus 4.8 | B: Muse Spark 1.3 Contributor |", "|---|---|---|"]
    md += [f"| {k} | {va} | {vb} |" for k, va, vb in rows]
    md += ["", "## Notes", "",
           f"* Muse Spark's cost per 1,000 chunks is **{ratio}** of the first batch's. Muse Glimmer generates the "
           "same cells on our own GPU with no API cost (`uyari generate plan --model glimmer-local`).",
           "* The Contributor tier's price includes Meta's right to train on prompts and completions. That is "
           "acceptable for synthetic Spanish and is why that tier never sees Indigenous-language data "
           "(`data_policy: official_only` in `config/llm.yaml`).",
           "* The first batch's cost is an estimate from token counts (tiktoken approximation; output counted from "
           "the texts that survived filtering, so it is a lower bound). Muse Spark's is the ledger's exact spend, "
           f"at the list price of ${muse.price_input} / ${muse.price_output} per million tokens.",
           "* Rows marked \"not recorded\" could not be measured for the first batch: it arrived already filtered "
           "and deduplicated."]
    out = paths.reports / "gen-comparison.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    _ = semantic, dedup_key
    return out
