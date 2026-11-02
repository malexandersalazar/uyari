"""Response parsing and per-text validation.

Same rules as the run that produced the first 10k chunks: robust JSON parsing (fences stripped, regex
fallback), at most ``max_words`` words, the unit's length bucket with a +/-30% tolerance, banned
urban/technical terms, exact duplicates by the NFC+casefold key. Plus a Spanish check.
"""

from __future__ import annotations

import json
import math
import re

from uyari.text.langid import looks_spanish
from uyari.text.normalize import dedup_key, word_count


def parse_texts(raw_text: str) -> list[str]:
    """Strip ``` fences, try json.loads, fall back to the last {...} with a "texts" list anywhere in
    the text (a reasoning model such as Muse Glimmer may write a reasoning channel or prose around it)."""
    cleaned = re.sub(r"```(?:json)?", "", raw_text or "").strip()
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict) and isinstance(obj.get("texts"), list):
            return [t for t in obj["texts"] if isinstance(t, str)]
    except json.JSONDecodeError:
        pass
    dec, found = json.JSONDecoder(), None
    for i, ch in enumerate(cleaned):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(cleaned[i:])
        except ValueError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("texts"), list):
            found = obj
    return [t for t in found["texts"] if isinstance(t, str)] if found else []


def banned_regex(terms: list[str]) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(re.escape(t) + r"(?:e?s)?" for t in terms) + r")\b", re.IGNORECASE)


def out_of_bucket(wc: int, unit: dict, tolerance_pct: int) -> tuple[bool, int, int]:
    lo_b, hi_b = unit.get("wc_min"), unit.get("wc_max")
    if lo_b is None or hi_b is None:
        return False, 0, 0
    tol = tolerance_pct / 100
    lo, hi = math.floor(lo_b * (1 - tol)), math.ceil(hi_b * (1 + tol))
    return not (lo <= wc <= hi), lo, hi


class TextValidator:
    def __init__(self, validation_cfg: dict, seen_keys: set[str], lexicon: set[str] | None = None):
        self.max_words = int(validation_cfg.get("max_words", 120))
        self.tol = int(validation_cfg.get("length_tolerance_pct", 30))
        self.banned = banned_regex(validation_cfg.get("banned_terms") or [])
        self.seen = seen_keys
        self.lexicon = lexicon or set()

    def is_spanish(self, text: str) -> bool:
        """Function words, Spanish-only characters, or most words already in the Spanish primary.
        (Function words alone rejected short valid sentences such as "Traería plátano verde bien fresco".)"""
        if looks_spanish(text):
            return True
        words = re.findall(r"[a-záéíóúüñ]+", text.lower())
        if re.search(r"[áéíóúñ¿¡]", text.lower()):
            return True
        return bool(words) and bool(self.lexicon) and sum(w in self.lexicon for w in words) / len(words) >= 0.6

    def check(self, text, unit: dict) -> tuple[bool, str, dict]:
        """(ok, reason, info). Marks accepted texts as seen (dedup within the batch too)."""
        if not text or not isinstance(text, str) or not text.strip():
            return False, "empty", {}
        t = text.strip()
        wc = word_count(t)
        if wc == 0:
            return False, "zero_words", {}
        if wc > self.max_words:
            return False, "too_long", {"word_count": wc}
        m = self.banned.search(t)
        if m:
            return False, "banned_term", {"term": m.group(0)}
        bad, lo, hi = out_of_bucket(wc, unit, self.tol)
        if bad:
            return False, "length_out_of_bucket", {"word_count": wc, "expected": [lo, hi]}
        if not self.is_spanish(t):
            return False, "not_spanish", {}
        k = dedup_key(t)
        if k in self.seen:
            return False, "exact_duplicate", {}
        self.seen.add(k)
        return True, "ok", {"word_count": wc}
