"""Privacy check: no personal names in any publishable file.

Names to look for come from a private list kept outside the repository:
``<private>/privacy_names.txt`` (one name per line), where ``<private>`` is ``$UYARI_PRIVATE_DIR``
or ``<data>/.private`` (gitignored). An ingest map (``translator_map.csv`` with a ``name``
column) is read too if present. Every file git would publish (tracked + untracked-not-ignored)
is scanned, case-insensitively, for each full name and each name part of 4+ letters.

Names a person consented to publish go in ``<private>/credits_allowlist.txt`` and are then
allowed in ``CREDITS.md`` only. Without a name list there is nothing to compare against and the
check reports it as skipped. ``.githooks/pre-commit`` runs it before every commit.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from uyari.csvio import read_csv
from uyari.paths import Paths

SKIP_DIRS = {".git", ".venv", ".private", "runs", ".uyari", "__pycache__", ".pytest_cache", ".ruff_cache",
             "node_modules", "weights", "adapter", "checkpoints"}
BINARY_EXT = {".parquet", ".safetensors", ".bin", ".pt", ".wav", ".png", ".jpg", ".xlsx", ".gguf", ".zip", ".model"}


@dataclass
class PrivacyResult:
    ok: bool = True
    findings: list[str] = field(default_factory=list)
    summary: str = ""
    scanned: int = 0


def _names(paths: Paths) -> tuple[list[str], set[str]]:
    names: set[str] = set()
    plain = paths.private / "privacy_names.txt"
    if plain.is_file():
        names |= {x.strip() for x in plain.read_text(encoding="utf-8").splitlines() if x.strip()}
    mapping = paths.private / "translator_map.csv"
    if mapping.is_file():
        names |= {r["name"].strip() for r in read_csv(mapping) if r.get("name")}
    allow = set()
    a = paths.private / "credits_allowlist.txt"
    if a.is_file():
        allow = {x.strip().casefold() for x in a.read_text(encoding="utf-8").splitlines() if x.strip()}
    tokens = set()
    for n in names:
        tokens.add(n)
        tokens.update(p for p in re.split(r"\s+", n) if len(p) >= 4)
    return sorted(tokens, key=len, reverse=True), allow


def _files(paths: Paths) -> list[Path]:
    try:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=paths.data,
                             capture_output=True, check=True)
        return [paths.data / p for p in out.stdout.decode("utf-8").split("\0") if p]
    except (OSError, subprocess.SubprocessError):
        files = []
        for root, dirs, fs in os.walk(paths.data):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            files += [Path(root) / f for f in fs]
        return files


def _pattern(tokens: list[str]) -> re.Pattern:
    return re.compile(r"(?<![\w])(" + "|".join(re.escape(t) for t in tokens) + r")(?![\w])", re.IGNORECASE)


def find_names(paths: Paths, text: str) -> list[str] | None:
    """Private names in a text published outside the repository (a Hugging Face README); None without a list."""
    tokens, _ = _names(paths)
    return sorted({m.group(1) for m in _pattern(tokens).finditer(text)}) if tokens else None


def run_privacy_check(paths: Paths) -> PrivacyResult:
    tokens, allow = _names(paths)
    res = PrivacyResult()
    if not tokens:
        res.summary = f"skipped: no private name list ({paths.private / 'privacy_names.txt'}) on this machine"
        return res
    pat = _pattern(tokens)
    for f in _files(paths):
        if f.suffix.lower() in BINARY_EXT or any(part in SKIP_DIRS for part in f.relative_to(paths.data).parts):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        res.scanned += 1
        for i, line in enumerate(text.splitlines(), 1):
            for m in pat.finditer(line):
                if f.name == "CREDITS.md" and m.group(1).casefold() in allow:
                    continue
                res.findings.append(f"{f.relative_to(paths.data).as_posix()}:{i}: '{m.group(1)}'")
    res.ok = not res.findings
    res.summary = (f"scanned {res.scanned} publishable files for {len(tokens)} private tokens: "
                   + ("clean" if res.ok else f"{len(res.findings)} finding(s)"))
    return res
