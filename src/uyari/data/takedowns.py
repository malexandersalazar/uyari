"""Takedowns: ``contributing/takedowns.csv``. A row removes a contribution from every build
whose ``as_of`` date is on or after the row's ``effective_date``."""

from __future__ import annotations

from datetime import date

from uyari.csvio import columns, read_csv, write_csv
from uyari.paths import Paths


def takedowns_path(paths: Paths):
    return paths.contributing / "takedowns.csv"


def load_takedowns(paths: Paths) -> list[dict]:
    p = takedowns_path(paths)
    return read_csv(p) if p.is_file() else []


def active_takedowns(paths: Paths, as_of: date) -> dict[str, dict]:
    """contribution id -> takedown row, for rows effective on or before ``as_of``."""
    out: dict[str, dict] = {}
    for r in load_takedowns(paths):
        try:
            eff = date.fromisoformat(r.get("effective_date", ""))
        except ValueError:
            continue
        if eff <= as_of:
            out[r["contribution"]] = r
    return out


def ensure_takedowns_file(paths: Paths) -> None:
    p = takedowns_path(paths)
    if not p.exists():
        write_csv(p, [], columns("takedown"))
