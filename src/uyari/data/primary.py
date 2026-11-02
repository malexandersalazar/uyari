"""Primary corpus: official-language chunks every language translates.

``primary/<lang>/chunks/**/<batch>.csv``; one row per chunk, columns from
``schemas/chunk.json``. A chunk id is never reused; published text is never edited (a
wrong chunk is deprecated and a corrected one created with ``supersedes``).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from uyari.csvio import columns, read_csv, write_csv
from uyari.paths import Paths


def chunk_columns() -> list[str]:
    return columns("chunk")


def list_primaries(paths: Paths) -> list[str]:
    if not paths.primary.is_dir():
        return []
    return sorted(p.name for p in paths.primary.iterdir() if (p / "chunks").is_dir())


def chunk_files(paths: Paths, lang: str) -> list[Path]:
    d = paths.primary_dir(lang) / "chunks"
    return sorted(d.rglob("*.csv")) if d.is_dir() else []


@dataclass
class PrimaryCorpus:
    lang: str
    chunks: dict[str, dict] = field(default_factory=dict)  # chunk_id -> row (first seen)
    file_of: dict[str, Path] = field(default_factory=dict)
    duplicates: list[tuple[str, Path]] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)

    def active(self, chunk_id: str) -> bool:
        r = self.chunks.get(chunk_id)
        return bool(r) and r.get("status") == "active"

    def groups(self) -> dict[str, list[str]]:
        """group id -> chunk ids. The group is ``source_custom_id`` (else the chunk itself)."""
        g: dict[str, list[str]] = defaultdict(list)
        for cid, r in self.chunks.items():
            g[group_of(r)].append(cid)
        return dict(g)


def group_of(row: dict) -> str:
    return row.get("source_custom_id") or row["chunk_id"]


def load_primary(paths: Paths, lang: str) -> PrimaryCorpus:
    pc = PrimaryCorpus(lang=lang)
    for f in chunk_files(paths, lang):
        pc.files.append(f)
        for r in read_csv(f):
            cid = r.get("chunk_id", "")
            if cid in pc.chunks:
                pc.duplicates.append((cid, f))
                continue
            pc.chunks[cid] = r
            pc.file_of[cid] = f
    return pc


def write_chunks(path: Path, rows: list[dict]) -> int:
    return write_csv(path, rows, chunk_columns())


def rewrite_files(pc: PrimaryCorpus) -> None:
    """Write every file of the corpus back, preserving each file's row order."""
    for f in pc.files:
        ids = [r["chunk_id"] for r in read_csv(f)]
        write_chunks(f, [pc.chunks[i] for i in ids if pc.file_of.get(i) == f])
