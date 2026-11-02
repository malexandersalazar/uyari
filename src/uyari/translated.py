"""Which primary chunks have at least one human translation (any language)."""

from __future__ import annotations

from uyari.data.contributions import load_contributions
from uyari.data.languages import list_languages, load_language
from uyari.paths import Paths


def translated_chunk_ids(paths: Paths, primary: str) -> set[str]:
    out: set[str] = set()
    for lang in list_languages(paths):
        if load_language(paths, lang).primary != primary:
            continue
        for c in load_contributions(paths, lang):
            out.update(p["chunk_id"] for p in c.pairs)
    return out
