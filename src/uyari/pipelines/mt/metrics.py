"""chrF++ (the score Uyari optimizes and reports) and BLEU (reported, not optimized).

COMET and other learned metrics are not used into Indigenous languages until a language has
enough human judgments to validate them.
"""

from __future__ import annotations

from collections import defaultdict


def corpus_scores(hyps: list[str], refs: list[str]) -> dict:
    from sacrebleu.metrics import BLEU, CHRF

    if not hyps:
        return {"chrf++": None, "bleu": None, "n": 0}
    chrf = CHRF(word_order=2).corpus_score(hyps, [refs])
    bleu = BLEU(tokenize="13a").corpus_score(hyps, [refs])
    return {"chrf++": round(chrf.score, 2), "bleu": round(bleu.score, 2), "n": len(hyps)}


def by_group(hyps: list[str], refs: list[str], groups: list[str]) -> dict:
    buckets: dict[str, tuple[list, list]] = defaultdict(lambda: ([], []))
    for h, r, g in zip(hyps, refs, groups, strict=True):
        buckets[g][0].append(h)
        buckets[g][1].append(r)
    return {g: corpus_scores(h, r) for g, (h, r) in sorted(buckets.items())}


def sentence_chrf(hyp: str, ref: str) -> float:
    from sacrebleu.metrics import CHRF

    return round(CHRF(word_order=2).sentence_score(hyp, [ref]).score, 1)
