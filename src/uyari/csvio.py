"""CSV and YAML I/O with the project's fixed conventions.

UTF-8, LF line endings, header row, comma separator, minimal quoting, every value a
string, empty string for unknown. Column order comes from the ``x-columns`` keyword of
the matching schema in ``schemas/`` so it is defined once.

Writing is atomic (temp file + replace) and byte-identical on Windows and Linux.
"""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable, Mapping
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from uyari.paths import find_repo_root


@cache
def schema(name: str) -> dict:
    """Load ``schemas/<name>.json``."""
    path = find_repo_root() / "schemas" / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def columns(schema_name: str) -> list[str]:
    return list(schema(schema_name)["x-columns"])


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV as a list of dicts of strings (missing cells become "")."""
    with Path(path).open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [{k: (v if v is not None else "") for k, v in row.items() if k is not None} for row in reader]


def read_header(path: Path) -> list[str]:
    with Path(path).open(encoding="utf-8", newline="") as f:
        return next(csv.reader(f), [])


def _atomic_write_text(path: Path, write) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        write(f)
    Path(tmp).replace(path)


def write_csv(path: Path, rows: Iterable[Mapping[str, Any]], cols: list[str]) -> int:
    """Write rows with exactly ``cols`` in order. Returns the number of rows written."""
    n = 0

    def _w(f):
        nonlocal n
        w = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        w.writerow(cols)
        for r in rows:
            w.writerow(["" if r.get(c) is None else str(r.get(c)) for c in cols])
            n += 1

    _atomic_write_text(path, _w)
    return n


def append_csv(path: Path, rows: Iterable[Mapping[str, Any]], cols: list[str]) -> int:
    """Append rows (creating the file with a header if needed). Never truncates."""
    path = Path(path)
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        if new:
            w.writerow(cols)
        for r in rows:
            w.writerow(["" if r.get(c) is None else str(r.get(c)) for c in cols])
            n += 1
    return n


def read_yaml(path: Path) -> dict:
    with Path(path).open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def write_yaml(path: Path, data: Mapping[str, Any], header: str = "") -> None:
    body = yaml.safe_dump(dict(data), allow_unicode=True, sort_keys=False, width=100)

    def _w(f):
        if header:
            f.write("".join(f"# {line}\n" if line else "#\n" for line in header.splitlines()))
        f.write(body)

    _atomic_write_text(path, _w)


def write_json(path: Path, data: Any) -> None:
    def _w(f):
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    _atomic_write_text(path, _w)


def read_jsonl(path: Path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    def _w(f):
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    _atomic_write_text(path, _w)


def append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
