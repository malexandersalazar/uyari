"""Language folders: ``languages/<iso639-3>_<Script>/language.yaml``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from uyari.csvio import read_yaml
from uyari.paths import Paths
from uyari.text.normalize import (
    CANONICAL_APOSTROPHE,
    DEFAULT_APOSTROPHE_VARIANTS,
    normalize_indigenous,
)


@dataclass
class Language:
    id: str
    dir: Path
    cfg: dict = field(default_factory=dict)

    @property
    def iso(self) -> str:
        return self.id.split("_")[0]

    @property
    def primary(self) -> str:
        return self.cfg.get("primary", "spa_Latn")

    @property
    def apostrophe(self) -> str:
        return self.cfg.get("apostrophe") or CANONICAL_APOSTROPHE

    @property
    def apostrophe_variants(self) -> tuple[str, ...]:
        return tuple(self.cfg.get("apostrophe_variants") or DEFAULT_APOSTROPHE_VARIANTS)

    def normalize(self, text: str) -> str:
        return normalize_indigenous(text, self.apostrophe, self.apostrophe_variants)

    @property
    def normalizer(self) -> Callable[[str], str]:
        return self.normalize

    @property
    def trainer_recipes(self) -> list[str]:
        return list((self.cfg.get("trainer") or {}).get("recipes") or [])


def list_languages(paths: Paths) -> list[str]:
    if not paths.languages.is_dir():
        return []
    return sorted(p.name for p in paths.languages.iterdir() if (p / "language.yaml").is_file())


def load_language(paths: Paths, lang: str) -> Language:
    d = paths.language_dir(lang)
    f = d / "language.yaml"
    if not f.is_file():
        raise FileNotFoundError(f"{f} not found (is '{lang}' a language folder?)")
    return Language(id=lang, dir=d, cfg=read_yaml(f))
