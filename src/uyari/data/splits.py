"""Train / validation / test assignment.

Rules (docs/decisions/0003-splits-by-paraphrase-group.md):

1. The split is a property of the primary chunk, shared by every language that translates it.
2. The unit is the **paraphrase group** (``source_custom_id``): the ~10 near-paraphrases one
   generation request produced never straddle two splits, or a test sentence would leak into
   training through its paraphrase.
3. A group that regenerates an existing cell (``regen_of``) inherits that cell's split.
4. Splits are frozen: a non-empty split is never changed.
5. First assignment for a primary: validation and test get ``target`` *translated* chunks each,
   built from whole translated groups ordered by ``sha256(salt + group)`` and stratified by
   ``domain_l1``. Everything else goes to train.
6. Later groups (new generated batches): hash of the group id, 5% validation, 5% test.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from uyari.data.primary import PrimaryCorpus, group_of

SALT = "uyari-split-v1"
SPLITS = ("train", "validation", "test")


def _h(key: str) -> int:
    return int(hashlib.sha256((SALT + key).encode("utf-8")).hexdigest(), 16)


def _unit(key: str) -> float:
    return (_h(key) % 1_000_000) / 1_000_000


class SplitConflict(ValueError):
    pass


@dataclass
class SplitReport:
    assigned_chunks: int = 0
    mode: str = ""
    chunks_by_split: dict[str, int] = field(default_factory=dict)
    translated_by_split: dict[str, int] = field(default_factory=dict)
    groups_by_split: dict[str, int] = field(default_factory=dict)


def group_splits(pc: PrimaryCorpus) -> dict[str, str]:
    """group id -> its split ('' if none of its chunks has one). Raises on a straddling group."""
    out: dict[str, str] = {}
    for gid, cids in pc.groups().items():
        seen = {pc.chunks[c]["split"] for c in cids if pc.chunks[c].get("split")}
        if len(seen) > 1:
            raise SplitConflict(f"group {gid} straddles splits {sorted(seen)}")
        out[gid] = seen.pop() if seen else ""
    return out


def assign_splits(pc: PrimaryCorpus, translated: set[str], target_validation: int = 300,
                  target_test: int = 300, ratio_validation: float = 0.05,
                  ratio_test: float = 0.05) -> SplitReport:
    """Fill empty splits in place (``pc.chunks`` rows). Returns a report."""
    gsplit = group_splits(pc)
    groups = pc.groups()

    # Rule 3: regen_of inheritance (a regenerated cell takes its source group's split).
    for gid, cids in groups.items():
        if gsplit[gid]:
            continue
        sources = {pc.chunks[c].get("regen_of", "") for c in cids} - {""}
        inherited = {gsplit.get(s, "") for s in sources} - {""}
        if len(inherited) > 1:
            raise SplitConflict(f"group {gid} regenerates groups in different splits: {sorted(inherited)}")
        if inherited:
            gsplit[gid] = inherited.pop()

    rep = SplitReport()
    inherited_groups = sum(1 for g, cids in groups.items() if gsplit[g] and not any(pc.chunks[c].get("split") for c in cids))
    has_eval = any(s in ("validation", "test") for s in gsplit.values())
    unsplit = [g for g, s in gsplit.items() if not s]

    if not has_eval and unsplit:
        rep.mode = "initial-stratified"
        n_trans = {g: sum(1 for c in groups[g] if c in translated) for g in unsplit}
        cands = [g for g in unsplit if n_trans[g] > 0]
        domain = {g: pc.chunks[groups[g][0]].get("domain_l1", "") for g in cands}
        total = sum(n_trans[g] for g in cands) or 1
        per_domain: dict[str, list[str]] = defaultdict(list)
        for g in cands:
            per_domain[domain[g]].append(g)
        for d in sorted(per_domain):
            gs = sorted(per_domain[d], key=_h)
            share = sum(n_trans[g] for g in gs) / total
            q_test, q_val = target_test * share, target_validation * share
            got_test = got_val = 0
            for g in gs:
                if got_test < q_test:
                    gsplit[g] = "test"
                    got_test += n_trans[g]
                elif got_val < q_val:
                    gsplit[g] = "validation"
                    got_val += n_trans[g]
                else:
                    break
        for g in unsplit:
            if not gsplit[g]:
                gsplit[g] = "train"
    elif unsplit:
        rep.mode = "hash-ratio"
        for g in unsplit:
            u = _unit(g)
            gsplit[g] = "test" if u < ratio_test else "validation" if u < ratio_test + ratio_validation else "train"
    else:
        rep.mode = "regen-inherited" if inherited_groups else "nothing-to-assign"

    for gid, cids in groups.items():
        for c in cids:
            row = pc.chunks[c]
            if not row.get("split"):
                row["split"] = gsplit[gid]
                rep.assigned_chunks += 1

    rep.chunks_by_split = dict(Counter(r["split"] for r in pc.chunks.values()))
    rep.translated_by_split = dict(Counter(pc.chunks[c]["split"] for c in translated if c in pc.chunks))
    rep.groups_by_split = dict(Counter(gsplit.values()))
    return rep


def check_group_integrity(pc: PrimaryCorpus) -> list[str]:
    """Problems for the validator: straddling groups, regen_of pointing at another split."""
    problems: list[str] = []
    try:
        gsplit = group_splits(pc)
    except SplitConflict as e:
        return [str(e)]
    for cid, r in pc.chunks.items():
        src = r.get("regen_of", "")
        if src and src in gsplit and gsplit[src] and r.get("split") and r["split"] != gsplit[src]:
            problems.append(f"chunk {cid}: regen_of group {src} is '{gsplit[src]}' but chunk is '{r['split']}'")
    _ = group_of  # re-exported for callers that need the group rule
    return problems
