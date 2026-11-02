"""Deduplication of a generated batch, then publication.

Two passes, keep-first, as for the first 10k: exact (NFC + casefold + whitespace) and
near-duplicates by sentence embeddings (``paraphrase-multilingual-MiniLM-L12-v2``, cosine
>= 0.92, blocked by ``domain_l1``). New: the whole existing primary is indexed first as
already-kept rows, so a new text near any published chunk is dropped too.

Writes ``primary/spa_Latn/chunks/generated/<batch>.csv`` (the clean batch), assigns splits
(``regen_of`` inherits, others by hash), and ``runs/gen/<batch>/dedup_{report.json,review.csv}``.
"""

from __future__ import annotations

from collections import Counter

from uyari.csvio import read_csv, write_csv, write_json
from uyari.data.primary import load_primary, rewrite_files, write_chunks
from uyari.data.splits import assign_splits
from uyari.gen.plan import PRIMARY, batch_dir
from uyari.paths import Paths
from uyari.text.normalize import dedup_key

EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def near_duplicates(texts: list[str], blocks: list[str], n_anchor: int, threshold: float) -> list[dict]:
    """Rows i >= n_anchor dropped when a kept row with a smaller index is within ``threshold``.
    Rows < n_anchor (the existing primary) are always kept. Returns [{idx, kept_idx, similarity}]."""
    from sentence_transformers import SentenceTransformer
    from sklearn.neighbors import NearestNeighbors

    model = SentenceTransformer(EMBED_MODEL)
    by_block: dict[str, list[int]] = {}
    for i, b in enumerate(blocks):
        by_block.setdefault(b, []).append(i)
    drops = []
    for _b, idxs in by_block.items():
        if not any(i >= n_anchor for i in idxs) or len(idxs) < 2:
            continue
        emb = model.encode([texts[i] for i in idxs], batch_size=256, normalize_embeddings=True,
                           show_progress_bar=False)
        nn = NearestNeighbors(metric="cosine").fit(emb)
        dists, vecs = nn.radius_neighbors(emb, radius=1.0 - threshold)
        kept: set[int] = set()
        for pos, i in enumerate(idxs):
            if i < n_anchor:
                kept.add(pos)
                continue
            best = None
            for dd, v in zip(dists[pos], vecs[pos], strict=True):
                if v >= pos or v not in kept:
                    continue
                sim = 1.0 - float(dd)
                if best is None or sim > best[0]:
                    best = (sim, int(v))
            if best is None:
                kept.add(pos)
            else:
                drops.append({"idx": i, "kept_idx": idxs[best[1]], "similarity": round(best[0], 4)})
    return drops


def run_dedup(paths: Paths, batch: str, semantic: bool = True, threshold: float = 0.92) -> dict:
    d = batch_dir(paths, batch)
    raw = read_csv(d / "raw.csv")
    pc = load_primary(paths, PRIMARY)
    existing = [r for r in pc.chunks.values() if r.get("source_batch_id") != batch]
    seen = {dedup_key(r["text"]) for r in existing}
    exact, survivors = 0, []
    for r in raw:
        k = dedup_key(r["text"])
        if k in seen:
            exact += 1
            continue
        seen.add(k)
        survivors.append(r)
    drops = []
    if semantic and survivors:
        texts = [r["text"] for r in existing] + [r["text"] for r in survivors]
        blocks = [r.get("domain_l1", "") for r in existing] + [r.get("domain_l1", "") for r in survivors]
        drops = near_duplicates(texts, blocks, len(existing), threshold)
    drop_idx = {x["idx"] - len(existing) for x in drops}
    clean = [r for i, r in enumerate(survivors) if i not in drop_idx]
    review = []
    for x in drops:
        new = survivors[x["idx"] - len(existing)]
        kept = existing[x["kept_idx"]] if x["kept_idx"] < len(existing) else survivors[x["kept_idx"] - len(existing)]
        review.append({"chunk_id": new["chunk_id"], "text": new["text"], "kept_chunk_id": kept["chunk_id"],
                       "kept_text": kept["text"], "kept_from": "primary" if x["kept_idx"] < len(existing) else "batch",
                       "similarity": x["similarity"]})
    out = paths.primary_dir(PRIMARY) / "chunks" / "generated" / f"{batch}.csv"
    write_chunks(out, clean)
    pc = load_primary(paths, PRIMARY)
    srep = assign_splits(pc, set())
    rewrite_files(pc)
    report = {"batch": batch, "raw": len(raw), "exact_duplicates": exact, "near_duplicates": len(drops),
              "near_vs_primary": sum(1 for r in review if r["kept_from"] == "primary"),
              "near_within_batch": sum(1 for r in review if r["kept_from"] == "batch"),
              "clean": len(clean), "threshold": threshold, "model": EMBED_MODEL if semantic else None,
              "by_domain": dict(Counter(r["domain_l1"] for r in clean)), "split_mode": srep.mode,
              "published": str(out.relative_to(paths.data).as_posix())}
    write_json(d / "dedup_report.json", report)
    write_csv(d / "dedup_review.csv", review, ["chunk_id", "text", "kept_chunk_id", "kept_text", "kept_from",
                                               "similarity"])
    return report
