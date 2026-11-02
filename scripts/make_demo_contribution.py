#!/usr/bin/env python3
"""Create a DEMO contribution with four deliberate defects, for filming the Gatekeeper on a PR.

    python scripts/make_demo_contribution.py            # -> languages/cbt_Latn/contributions/2026-11_demo_0001

The rows are labelled as a demo and must never be merged:
  1. Spanish pasted in the Shawi column (the chunk's own Spanish)
  2. a row copied verbatim from an accepted contribution
  3. a Shawi sentence typed with ASCII apostrophes (') instead of the glottal-stop letter (ʼ)
  4. an unknown chunk id

Open it on a branch as a pull request; the Gatekeeper review should return it with all four flagged.
"""

from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="cbt_Latn")
    ap.add_argument("--id", default="2026-11_demo_0001")
    args = ap.parse_args()
    contrib = REPO / "languages" / args.lang / "contributions"
    accepted = sorted(p for p in contrib.iterdir() if p.is_dir() and "_demo_" not in p.name)
    pairs = [r for d in accepted for r in csv.DictReader((d / "pairs.csv").open(encoding="utf-8"))]
    chunks = {r["chunk_id"]: r for f in (REPO / "primary/spa_Latn/chunks").rglob("*.csv")
              for r in csv.DictReader(f.open(encoding="utf-8"))}
    translated = {p["chunk_id"] for p in pairs}
    rng = random.Random(4)
    free = [c for c, r in chunks.items() if c not in translated and r["split"] == "train" and r["status"] == "active"]
    a, b, c = rng.sample(free, 3)
    copied = rng.choice(pairs)
    with_apostrophes = next(p["text"] for p in pairs if p["text"].count("ʼ") >= 2).replace("ʼ", "'")
    rows = [
        [a, chunks[a]["text"], "", "t-9001", "DEMO: Spanish pasted in the Shawi column"],
        [b, copied["text"], "", "t-9001", "DEMO: copied from an accepted contribution"],
        [c, with_apostrophes, "", "t-9001", "DEMO: ASCII apostrophes"],
        ["f" * 32, "Kuwa nunsha ihpi patere.", "", "t-9001", "DEMO: unknown chunk id"],
    ]
    d = contrib / args.id
    d.mkdir(parents=True, exist_ok=True)
    (d / "contribution.yaml").write_text(yaml.safe_dump({
        "id": args.id, "language": args.lang, "variety": "_unspecified", "contributor_id": "c-9001",
        "organization": "DEMO - not real data, never merge", "collection_dates": {"start": "2026-11-02", "end": "2026-11-02"},
        "provenance": {"text": "human", "audio": "none"}, "license": "cc-by-4.0",
        "consent": {"template": "consent-collective.md", "authority": "demo"}, "compensated": "no", "fixture": True,
        "notes": "Deliberately defective contribution used to film the Gatekeeper."}, allow_unicode=True,
        sort_keys=False), encoding="utf-8")
    with (d / "pairs.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["chunk_id", "text", "replaces", "translator_id", "notes"])
        w.writerows(rows)
    print(f"wrote {d.relative_to(REPO)}; now: uyari gatekeeper --contribution {d.relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    main()
