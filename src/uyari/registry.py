"""``models/registry.yaml``: which model each task and language serves.

    mt:
      cbt_Latn:
        promoted: mt-cbt-spa-glimmer30b-qlora@v0.1   # the demo default
        fast: mt-cbt-spa-nllb1.3b@v0.1               # the demo's fast mode / HF Space
        history: [...]
"""

from __future__ import annotations

from datetime import UTC, datetime

from uyari.csvio import read_yaml, write_yaml
from uyari.paths import Paths


def _path(paths: Paths):
    return paths.models / "registry.yaml"


def load(paths: Paths) -> dict:
    p = _path(paths)
    return read_yaml(p) if p.is_file() else {}


def promoted(paths: Paths, task: str, lang: str, slot: str = "promoted") -> str | None:
    return ((load(paths).get(task) or {}).get(lang) or {}).get(slot)


def set_slot(paths: Paths, task: str, lang: str, slot: str, name: str, reason: str) -> None:
    reg = load(paths)
    entry = reg.setdefault(task, {}).setdefault(lang, {})
    prev = entry.get(slot)
    entry[slot] = name
    entry.setdefault("history", []).append({
        "at": datetime.now(UTC).isoformat(timespec="seconds"), "slot": slot, "from": prev, "to": name,
        "reason": reason})
    write_yaml(_path(paths), reg, header="Which model each task/language serves. Written by the Trainer "
                                         "and by `uyari register`, both with the promotion rule. Never edit history.")
