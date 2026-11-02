"""Reversible character codec applied only at a model's edges.

Storage and evaluation always use the canonical text (``ʼ`` U+02BC). Some tokenizers do not
know a character (NLLB's SentencePiece maps U+02BC to ``<unk>``); the recipe then declares a
``text_codec`` such as ``{"ʼ": "'"}``. Encode before the model reads Indigenous text, decode
what it writes. The mapped-to character must not otherwise occur in that text, or decoding is
not exact; ``check_reversible`` verifies this on the training data.
"""

from __future__ import annotations


class Codec:
    def __init__(self, mapping: dict[str, str] | None):
        self.fwd = dict(mapping or {})
        self.rev = {v: k for k, v in self.fwd.items()}

    def __bool__(self) -> bool:
        return bool(self.fwd)

    def encode(self, text: str) -> str:
        for a, b in self.fwd.items():
            text = text.replace(a, b)
        return text

    def decode(self, text: str) -> str:
        for b, a in self.rev.items():
            text = text.replace(b, a)
        return text

    def check_reversible(self, texts: list[str]) -> list[str]:
        """Texts that already contain a mapped-to character (would decode wrongly)."""
        return [t for t in texts if any(b in t for b in self.rev)]
