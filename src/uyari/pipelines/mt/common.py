"""Shared training utilities (seeding, batching, logging, metadata)."""

from __future__ import annotations

import json
import random
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path

from uyari.csvio import append_jsonl, read_jsonl, write_json
from uyari.recipes import Recipe

META_FILE = "uyari_meta.json"


def seed_everything(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def length_bucketed_batches(lengths: list[int], batch_size: int, seed: int, epoch: int) -> list[list[int]]:
    """Shuffle, sort within mega-batches by length (less padding), shuffle the batches."""
    rng = random.Random(seed * 1000 + epoch)
    idx = list(range(len(lengths)))
    rng.shuffle(idx)
    mega = batch_size * 50
    batches = []
    for i in range(0, len(idx), mega):
        chunk = sorted(idx[i:i + mega], key=lambda j: lengths[j])
        batches += [chunk[k:k + batch_size] for k in range(0, len(chunk), batch_size)]
    rng.shuffle(batches)
    return batches


def load_split(data_dir: Path, split: str) -> list[dict]:
    rows = read_jsonl(Path(data_dir) / f"{split}.jsonl")
    if not rows and split == "train":
        raise FileNotFoundError(f"{data_dir}/train.jsonl is empty or missing: run `uyari prepare`")
    return rows


def selection_subset(rows: list[dict], limit: int | None, seed: int = 7) -> list[dict]:
    """Deterministic, direction-balanced subset of validation used for checkpoint selection."""
    if not limit or len(rows) <= limit:
        return rows
    by_dir: dict[str, list[dict]] = {}
    for r in rows:
        by_dir.setdefault(f"{r['src_lang']}>{r['tgt_lang']}", []).append(r)
    per = max(1, limit // len(by_dir))
    out = []
    for k in sorted(by_dir):
        rs = sorted(by_dir[k], key=lambda r: r["id"])
        random.Random(seed).shuffle(rs)
        out += rs[:per]
    return out


class TrainLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.t0 = time.time()

    def __call__(self, **kv) -> None:
        kv = {"t": round(time.time() - self.t0, 1), **kv}
        append_jsonl(self.path, kv)
        print(json.dumps(kv, ensure_ascii=False), flush=True)


def write_meta(out_dir: Path, recipe: Recipe, kind: str, extra: dict) -> None:
    meta = {
        "name": recipe.model_name, "kind": kind, "recipe_id": recipe.id,
        "recipe_file": Path(recipe.path).name, "build": recipe.build, "language": recipe.language,
        "primary": recipe.primary, "primaries": recipe.sources, "directions": [f"{s}>{t}" for s, t in recipe.directions()],
        "base_model": recipe.base_model, "method": recipe.method, "codec": recipe.codec,
        "eval": recipe.eval, "chat_template_kwargs": recipe.cfg.get("chat_template_kwargs") or {},
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"), **extra,
    }
    write_json(Path(out_dir) / META_FILE, meta)
    shutil.copyfile(recipe.path, Path(out_dir) / "recipe.yaml")


def read_meta(model_dir: Path) -> dict:
    return json.loads((Path(model_dir) / META_FILE).read_text(encoding="utf-8"))
