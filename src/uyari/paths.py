"""Where things live.

Two roots, usually the same directory:

* ``code`` holds what the tools need to run: ``schemas/``, ``registry/``, ``config/``,
  ``recipes/``.
* ``data`` holds what the tools read and write: ``primary/``, ``languages/``,
  ``contributing/`` (guides, consent templates, takedowns), ``builds/``, ``models/``, ``runs/``, ``reports/``, ``.uyari/``.

Tests point ``data`` at ``tests/fixtures/root`` and keep ``code`` at the repository.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def find_repo_root(start: Path | None = None) -> Path:
    """Walk up from ``start`` (or the CWD) to the folder holding ``schemas/`` and ``config/``."""
    env = os.environ.get("UYARI_ROOT")
    if env:
        return Path(env).resolve()
    here = (start or Path.cwd()).resolve()
    for p in [here, *here.parents]:
        if (p / "schemas").is_dir() and (p / "config").is_dir() and (p / "pyproject.toml").is_file():
            return p
    # Fall back to the installed package location (src/uyari/ -> repo root).
    pkg = Path(__file__).resolve().parents[2]
    if (pkg / "schemas").is_dir():
        return pkg
    raise FileNotFoundError("Cannot find the Uyari repository root (set UYARI_ROOT).")


@dataclass(frozen=True)
class Paths:
    code: Path
    data: Path

    @classmethod
    def default(cls, data: Path | str | None = None) -> Paths:
        code = find_repo_root()
        return cls(code=code, data=Path(data).resolve() if data else code)

    # ---- code side
    @property
    def schemas(self) -> Path:
        return self.code / "schemas"

    @property
    def registry(self) -> Path:
        return self.code / "registry"

    @property
    def config(self) -> Path:
        return self.code / "config"

    @property
    def recipes(self) -> Path:
        return self.code / "recipes"

    # ---- data side
    @property
    def primary(self) -> Path:
        return self.data / "primary"

    def primary_dir(self, lang: str) -> Path:
        return self.primary / lang

    @property
    def languages(self) -> Path:
        return self.data / "languages"

    def language_dir(self, lang: str) -> Path:
        return self.languages / lang

    def contributions_dir(self, lang: str) -> Path:
        return self.language_dir(lang) / "contributions"

    @property
    def contributing(self) -> Path:
        return self.data / "contributing"

    @property
    def builds(self) -> Path:
        return self.data / "builds"

    @property
    def models(self) -> Path:
        return self.data / "models"

    @property
    def runs(self) -> Path:
        return self.data / "runs"

    @property
    def reports(self) -> Path:
        return self.data / "reports"

    @property
    def state(self) -> Path:
        """Local, gitignored state: spend ledger, GPU lock, caches."""
        return self.data / ".uyari"

    @property
    def private(self) -> Path:
        """Private inputs (ingest configs, the privacy check's name list): ``$UYARI_PRIVATE_DIR``,
        else ``<data>/.private`` (gitignored). Never published."""
        env = os.environ.get("UYARI_PRIVATE_DIR")
        return Path(env) if env else self.data / ".private"
