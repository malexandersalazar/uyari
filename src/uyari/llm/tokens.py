"""Token counting for estimates. Muse tokenizers are not public; tiktoken ``o200k_base`` is the
approximation, multiplied by a safety factor (``config/llm.yaml: estimate``). Estimates are
labelled as such; the ledger records the provider's real ``usage``."""

from __future__ import annotations

from functools import cache


@cache
def _enc(name: str):
    try:
        import tiktoken

        return tiktoken.get_encoding(name)
    except Exception:  # noqa: BLE001 - offline or missing: fall back to a character heuristic
        return None


def count(text: str, encoding: str = "o200k_base") -> int:
    enc = _enc(encoding)
    if enc is None:
        return max(1, int(len(text) / 3.5))
    return len(enc.encode(text, disallowed_special=()))
