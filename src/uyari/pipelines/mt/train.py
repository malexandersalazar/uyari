"""``uyari train --recipe R``: prepare if needed, then dispatch on the recipe's method."""

from __future__ import annotations

from pathlib import Path

from uyari.paths import Paths
from uyari.pipelines.mt.prepare import run_prepare
from uyari.recipes import load_recipe


def run_train(paths: Paths, recipe_path: Path | str, max_steps: int | None = None) -> Path:
    recipe = load_recipe(recipe_path)
    data_dir = recipe.run_dir(paths) / "data"
    if not (data_dir / "train.jsonl").is_file():
        run_prepare(paths, recipe_path)
    out = recipe.output_dir(paths)
    out.mkdir(parents=True, exist_ok=True)
    if recipe.method == "seq2seq":
        from uyari.pipelines.mt.train_nllb import train_nllb

        return train_nllb(paths, recipe, data_dir, out, max_steps=max_steps)
    if recipe.method == "qlora":
        from uyari.pipelines.mt.train_causal import train_causal

        return train_causal(paths, recipe, data_dir, out, max_steps=max_steps)
    raise ValueError(f"unknown method {recipe.method}")
