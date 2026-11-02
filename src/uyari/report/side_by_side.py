"""Side-by-side page: validation sentences with the human reference, each model and the
retrieval floor. Judges read this; nobody reads chrF++.

``uyari report side-by-side --n 20`` -> ``reports/side-by-side.html`` (static, self-contained).
Sentences are picked deterministically, half per direction, stratified by domain.
"""

from __future__ import annotations

import hashlib
import html
import json
from collections import defaultdict
from pathlib import Path

from uyari.csvio import read_jsonl
from uyari.paths import Paths
from uyari.pipelines.mt.common import read_meta
from uyari.pipelines.mt.metrics import sentence_chrf
from uyari.registry import load as load_registry

LANG = "cbt_Latn"
NAME = {"spa": "Spanish", "eng": "English", "cbt": "Shawi"}


def _label(key: str) -> str:
    s, t = key.split("-")
    return f"{NAME.get(s, s)} → {NAME.get(t, t)}"


def _pick(rows: list[dict], n: int) -> list[dict]:
    by_dom = defaultdict(list)
    for r in sorted(rows, key=lambda r: hashlib.sha256(r["chunk_id"].encode()).hexdigest()):
        by_dom[r["domain"]].append(r)
    out, i = [], 0
    doms = sorted(by_dom)
    while len(out) < n and any(by_dom.values()):
        d = doms[i % len(doms)]
        if by_dom[d]:
            out.append(by_dom[d].pop(0))
        i += 1
    return out


def run_side_by_side(paths: Paths, n: int = 20, models: list[str] | None = None) -> Path:
    reg = (load_registry(paths).get("mt") or {}).get(LANG) or {}
    models = models or [m for m in (reg.get("fast"), reg.get("promoted")) if m]
    if not models:
        raise RuntimeError("no models given and none registered")
    metas = {m: read_meta(paths.models / m) for m in models}
    build = metas[models[0]]["build"]
    floor_dir = paths.runs / "retrieval" / build / LANG / "eval"
    sections, summary = [], []
    keys = [f"{s[:3]}-{t[:3]}" for s, t in (d.split(">") for d in metas[models[0]]["directions"])]
    for key in keys:
        hyps = {m: {r["chunk_id"] + r["ref"]: r for r in read_jsonl(paths.models / m / "eval" / f"validation.{key}.jsonl")}
                for m in models}
        floor = {r["chunk_id"] + r["ref"]: r for r in read_jsonl(floor_dir / f"validation.{key}.jsonl")}
        base = list(hyps[models[0]].values())
        if not base:
            raise RuntimeError(f"no validation hypotheses for {models[0]} ({key}); run `uyari eval` first")
        rows = _pick(base, n // 2)
        trs = []
        for r in rows:
            k = r["chunk_id"] + r["ref"]
            cells = [f"<td class='src'>{html.escape(r['src'])}</td>", f"<td class='ref'>{html.escape(r['ref'])}</td>"]
            for m in models:
                h = hyps[m].get(k, {}).get("hyp", "")
                cells.append(f"<td>{html.escape(h)}<span class='s'>chrF++ {sentence_chrf(h, r['ref'])}</span></td>")
            fh = floor.get(k, {}).get("hyp", "")
            cells.append(f"<td class='floor'>{html.escape(fh)}<span class='s'>chrF++ {sentence_chrf(fh, r['ref'])}</span></td>")
            trs.append(f"<tr><td class='dom'>{html.escape(r['domain'])}</td>{''.join(cells)}</tr>")
        head = "".join(f"<th>{html.escape(m)}</th>" for m in models)
        sections.append(f"<h2>{_label(key)}</h2><div class='wrap'><table><thead><tr><th>Domain</th><th>Source</th>"
                        f"<th>Reference</th>{head}<th>Retrieval floor</th></tr></thead>"
                        f"<tbody>{''.join(trs)}</tbody></table></div>")
    def line(name: str, sc: dict) -> str:
        parts = [f"{_label(k)} {sc.get(k.replace('-', '>'), {}).get('chrf++', '—')}" for k in keys]
        return f"<li><b>{html.escape(name)}</b>: chrF++ " + ", ".join(parts) + "</li>"

    for m in models:
        summary.append(line(m, json.loads((paths.models / m / "scores.json").read_text(encoding="utf-8"))
                            .get("validation", {})))
    summary.append(line("Retrieval floor", json.loads((floor_dir.parent / "scores.json").read_text(encoding="utf-8"))
                        .get("validation", {})))
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Uyari side by side</title>
<style>
:root{{--bg:#fbfaf7;--fg:#1d1b18;--muted:#6b665e;--line:#e4dfd6;--ref:#eef6ee;--floor:#f5f3ef;--acc:#7a4b1f}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16140f;--fg:#ece7de;--muted:#a39d92;--line:#2e2a23;--ref:#1c2a1d;--floor:#1f1c17;--acc:#e0a96d}}}}
body{{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;padding:24px 16px}}
main{{max-width:1200px;margin:0 auto}} h1{{margin:0 0 4px}} h2{{margin-top:32px;color:var(--acc)}}
p,li{{color:var(--muted)}} .wrap{{overflow-x:auto}} table{{border-collapse:collapse;width:100%;min-width:900px}}
th,td{{border-bottom:1px solid var(--line);padding:10px 8px;vertical-align:top;text-align:left}}
th{{font-size:13px;color:var(--muted);font-weight:600}} td.ref{{background:var(--ref)}} td.floor{{background:var(--floor)}}
td.dom{{font-size:12px;color:var(--muted)}} .s{{display:block;font-size:12px;color:var(--muted);margin-top:4px}}
</style></head><body><main>
<h1>Uyari · Shawi translation, side by side</h1>
<p>{n} <b>validation</b> sentences per direction (never seen in training, nor any paraphrase of them), picked
deterministically across domains. The green column is the human reference; the last column is the floor: the
human translation of the most similar training sentence. Build <code>{html.escape(build)}</code>.</p>
<ul>{''.join(summary)}</ul>
{''.join(sections)}
<p>Sentence-level chrF++ is noisy; the corpus scores above are the ones that count. Generated by <code>uyari report side-by-side</code>.</p>
</main></body></html>"""
    out = paths.reports / "side-by-side.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8", newline="\n")
    return out
