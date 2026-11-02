"""Text normalization shared by ingest, validate, build and the pipelines.

The glottal stop is a *letter* in Shawi (``ipiʼ``). Contributors type it as ``'``, ``´``,
`````, ``’`` and others; the canonical form is the modifier letter apostrophe ``ʼ``
(U+02BC), which word tokenizers do not treat as punctuation. ``language.yaml`` declares the
canonical character and the variants that map to it.
"""

from __future__ import annotations

import re
import unicodedata

CANONICAL_APOSTROPHE = "ʼ"  # ʼ MODIFIER LETTER APOSTROPHE
DEFAULT_APOSTROPHE_VARIANTS = (
    "'",  # U+0027 APOSTROPHE
    "’",  # ’ RIGHT SINGLE QUOTATION MARK
    "‘",  # ‘ LEFT SINGLE QUOTATION MARK
    "´",  # ´ ACUTE ACCENT
    "`",  # U+0060 GRAVE ACCENT
    "ʻ",  # ʻ MODIFIER LETTER TURNED COMMA
    "ʹ",  # ʹ MODIFIER LETTER PRIME
    "′",  # ′ PRIME
)

_WS = re.compile(r"\s+")
_SPACE_AFTER_OPEN = re.compile(r"([¿¡])\s+")
_SPACE_BEFORE_CLOSE = re.compile(r"\s+([?!.,;:])")


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def collapse_whitespace(text: str) -> str:
    """Newlines, tabs and runs of spaces become one space; ends are stripped."""
    return _WS.sub(" ", text).strip()


def fix_punct_spacing(text: str) -> str:
    """``¿ Ku`` -> ``¿Ku``; ``perdonar ;`` -> ``perdonar;``."""
    text = _SPACE_AFTER_OPEN.sub(r"\1", text)
    return _SPACE_BEFORE_CLOSE.sub(r"\1", text)


def canonical_apostrophe(text: str, canonical: str = CANONICAL_APOSTROPHE,
                         variants: tuple[str, ...] | list[str] = DEFAULT_APOSTROPHE_VARIANTS) -> str:
    for v in variants:
        if v != canonical:
            text = text.replace(v, canonical)
    return text


def normalize_official(text: str) -> str:
    """Official-language (primary) text: NFC and whitespace only. Apostrophes untouched."""
    return collapse_whitespace(nfc(text))


def normalize_indigenous(text: str, canonical: str = CANONICAL_APOSTROPHE,
                         variants: tuple[str, ...] | list[str] = DEFAULT_APOSTROPHE_VARIANTS) -> str:
    """Indigenous-language text: NFC, whitespace, punctuation spacing, canonical apostrophe."""
    text = collapse_whitespace(nfc(text))
    text = fix_punct_spacing(text)
    return canonical_apostrophe(text, canonical, variants)


def apostrophe_variants_in(text: str, canonical: str = CANONICAL_APOSTROPHE,
                           variants: tuple[str, ...] | list[str] = DEFAULT_APOSTROPHE_VARIANTS) -> list[str]:
    """Which non-canonical apostrophe characters appear in ``text`` (for validator messages)."""
    return sorted({v for v in variants if v != canonical and v in text})


def word_count(text: str) -> int:
    """Word count used by generation validation and the length checks."""
    return len([w for w in re.sub(r"[.,!?¡¿:;]", " ", text).split() if w.strip()])


def dedup_key(text: str) -> str:
    """Exact-duplicate key: NFC, casefold, collapsed whitespace."""
    return _WS.sub(" ", nfc(text)).strip().casefold()


def is_normalized_indigenous(text: str, canonical: str = CANONICAL_APOSTROPHE,
                             variants: tuple[str, ...] | list[str] = DEFAULT_APOSTROPHE_VARIANTS) -> bool:
    return text == normalize_indigenous(text, canonical, variants)
