"""Recipes: one YAML file configures one training run. Nothing is configurable from the
command line (except ``--max-steps`` for smoke runs)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from jsonschema import Draft202012Validator

from uyari.csvio import read_yaml, schema
from uyari.paths import Paths


class RecipeError(ValueError):
    pass


@dataclass
class Recipe:
    path: Path
    cfg: dict

    @property
    def id(self) -> str:
        return self.cfg["id"]

    @property
    def build(self) -> str:
        return self.cfg["build"]

    @property
    def language(self) -> str:
        return self.cfg["language"]

    @property
    def sources(self) -> list[str]:
        """Official languages this recipe pairs with ``language`` (``primaries``, else ``[primary]``)."""
        return list(self.cfg.get("primaries") or [self.cfg["primary"]])

    @property
    def primary(self) -> str:
        return self.sources[0]

    def official_of(self, s: str, t: str) -> str:
        """The official-language side of a direction."""
        return t if s == self.language else s

    @property
    def method(self) -> str:
        return self.cfg["method"]

    @property
    def base_model(self) -> str:
        return self.cfg["base_model"]

    @property
    def train(self) -> dict:
        return self.cfg.get("train", {})

    @property
    def eval(self) -> dict:
        return self.cfg.get("eval", {})

    @property
    def lora(self) -> dict:
        return self.cfg.get("lora", {})

    @property
    def codec(self) -> dict[str, str]:
        return dict(self.cfg.get("text_codec") or {})

    @property
    def filters(self) -> dict:
        return self.cfg.get("filters") or {}

    def directions(self) -> list[tuple[str, str]]:
        """[("spa_Latn", "cbt_Latn"), ...] from ``spa>cbt`` strings."""
        by_iso = {x.split("_")[0]: x for x in [*self.sources, self.language]}
        out = []
        for d in self.cfg.get("directions") or [f"{self.primary[:3]}>{self.language[:3]}"]:
            s, t = d.split(">")
            if s not in by_iso or t not in by_iso:
                raise RecipeError(f"direction {d} must use {sorted(by_iso)}")
            out.append((by_iso[s], by_iso[t]))
        return out

    @property
    def output(self) -> str:
        return self.cfg["output"]

    @property
    def model_name(self) -> str:
        return Path(self.output).name

    def output_dir(self, paths: Paths) -> Path:
        return paths.data / self.output

    def run_dir(self, paths: Paths) -> Path:
        return paths.runs / self.id


def load_recipe(path: Path | str) -> Recipe:
    path = Path(path)
    cfg = read_yaml(path)
    errs = sorted(Draft202012Validator(schema("recipe")).iter_errors(cfg), key=lambda e: list(e.path))
    if errs:
        raise RecipeError("; ".join(f"{'.'.join(map(str, e.path)) or 'recipe'}: {e.message}" for e in errs))
    if not re.match(r"^[a-z0-9.\-]+@v\d+\.\d+$", Path(cfg["output"]).name):
        raise RecipeError("output must be models/<task>-<lang>-<base>@v<major>.<minor>")
    return Recipe(path=path, cfg=cfg)
