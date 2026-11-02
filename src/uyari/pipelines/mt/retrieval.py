"""The retrieval floor and the "closest human pairs".

Translation by retrieval: return the human translation of the most similar *training* source
sentence (character n-gram TF-IDF, cosine). It costs nothing, sends nothing anywhere, and is
the floor every trained model must beat on validation. The same index gives the demo and the
Gatekeeper their three closest human pairs. It never indexes validation or test rows.
"""

from __future__ import annotations

from dataclasses import dataclass

from uyari.build import read_table
from uyari.paths import Paths


@dataclass
class PairIndex:
    src_lang: str
    tgt_lang: str
    src: list[str]
    tgt: list[str]
    meta: list[dict]
    _vec: object = None
    _mat: object = None

    def fit(self) -> PairIndex:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True, lowercase=True)
        self._mat = self._vec.fit_transform(self.src)
        return self

    def nearest(self, texts: list[str], k: int = 3) -> list[list[tuple[int, float]]]:
        import numpy as np

        q = self._vec.transform(texts)
        sims = (q @ self._mat.T).toarray()
        out = []
        for row in sims:
            idx = np.argsort(-row)[:k]
            out.append([(int(i), float(row[i])) for i in idx])
        return out

    def translate(self, texts: list[str]) -> list[str]:
        return [self.tgt[n[0][0]] for n in self.nearest(texts, k=1)]

    def closest_pairs(self, text: str, k: int = 3) -> list[dict]:
        return [{"src": self.src[i], "tgt": self.tgt[i], "score": round(s, 3), **self.meta[i]}
                for i, s in self.nearest([text], k=k)[0]]


def build_index(paths: Paths, tag: str, lang: str, primary: str, src_lang: str, tgt_lang: str,
                splits: tuple[str, ...] = ("train",)) -> PairIndex:
    rows = [r for r in read_table(paths, tag, lang, "mt") if r["split"] in splits and r["src_lang"] == primary]
    if src_lang == primary:
        src, tgt = [r["src_text"] for r in rows], [r["tgt_text"] for r in rows]
    else:
        src, tgt = [r["tgt_text"] for r in rows], [r["src_text"] for r in rows]
    meta = [{"chunk_id": r["chunk_id"], "contribution": r["contribution"], "domain": r["domain"]} for r in rows]
    return PairIndex(src_lang=src_lang, tgt_lang=tgt_lang, src=src, tgt=tgt, meta=meta).fit()
