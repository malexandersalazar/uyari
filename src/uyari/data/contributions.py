"""Contribution folders: ``languages/<lang>/contributions/<YYYY-MM>_<org>_<nnnn>/``.

What a contribution contains is derived from which files exist (pairs, audio, speakers);
nothing declares it. A merged contribution is immutable: corrections arrive as rows in a
later contribution with ``replaces=<contribution>/<chunk_id>``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from uyari.csvio import read_csv, read_yaml
from uyari.paths import Paths

CONTRIBUTION_ID = re.compile(r"^[0-9]{4}-[0-9]{2}_[a-z0-9]+_[0-9]{4}$")


@dataclass
class Contribution:
    id: str
    lang: str
    dir: Path
    meta: dict = field(default_factory=dict)
    pairs: list[dict] = field(default_factory=list)
    audio: list[dict] = field(default_factory=list)
    speakers: list[dict] = field(default_factory=list)
    review: dict | None = None

    @property
    def has_text(self) -> bool:
        return bool(self.pairs)

    @property
    def has_audio(self) -> bool:
        return bool(self.audio)

    @property
    def license(self) -> str:
        return str(self.meta.get("license", ""))

    @property
    def provenance_text(self) -> str:
        return str((self.meta.get("provenance") or {}).get("text", ""))

    @property
    def provenance_audio(self) -> str:
        return str((self.meta.get("provenance") or {}).get("audio", ""))

    @property
    def revoked(self) -> bool:
        return bool(self.review) and self.review.get("decision") == "revoked"


def contribution_dirs(paths: Paths, lang: str) -> list[Path]:
    d = paths.contributions_dir(lang)
    if not d.is_dir():
        return []
    return sorted(p for p in d.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))


def load_contribution(d: Path, lang: str) -> Contribution:
    c = Contribution(id=d.name, lang=lang, dir=d)
    if (d / "contribution.yaml").is_file():
        c.meta = read_yaml(d / "contribution.yaml")
    if (d / "pairs.csv").is_file():
        c.pairs = read_csv(d / "pairs.csv")
    if (d / "audio.csv").is_file():
        c.audio = read_csv(d / "audio.csv")
    if (d / "speakers.csv").is_file():
        c.speakers = read_csv(d / "speakers.csv")
    if (d / "review.yaml").is_file():
        c.review = read_yaml(d / "review.yaml")
    return c


def load_contributions(paths: Paths, lang: str) -> list[Contribution]:
    return [load_contribution(d, lang) for d in contribution_dirs(paths, lang)]
