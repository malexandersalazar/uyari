from uyari.data.primary import PrimaryCorpus
from uyari.data.splits import SplitConflict, assign_splits, check_group_integrity


def corpus(n_groups=60, per=5, domains=("a", "b", "c")) -> PrimaryCorpus:
    pc = PrimaryCorpus(lang="spa_Latn")
    for g in range(n_groups):
        for k in range(per):
            cid = f"{g:04d}{k:04d}".ljust(32, "0")
            pc.chunks[cid] = {"chunk_id": cid, "split": "", "status": "active", "domain_l1": domains[g % len(domains)],
                              "source_custom_id": f"g{g}", "regen_of": ""}
    return pc


def test_initial_assignment_whole_groups_and_targets():
    pc = corpus()
    translated = {c for c in pc.chunks if int(c[:4]) % 2 == 0}  # every other group translated
    rep = assign_splits(pc, translated, target_validation=40, target_test=40)
    assert rep.mode == "initial-stratified"
    assert not check_group_integrity(pc)
    for c in pc.chunks.values():
        assert c["split"] in ("train", "validation", "test")
    # validation/test drawn only from translated groups, close to target
    for s in ("validation", "test"):
        ids = [c for c, r in pc.chunks.items() if r["split"] == s]
        assert all(c in translated for c in ids)
        assert 40 <= len(ids) <= 40 + 3 * 5 * 2


def test_deterministic_and_frozen():
    a, b = corpus(), corpus()
    tr = set(a.chunks)
    assign_splits(a, tr, 30, 30)
    assign_splits(b, tr, 30, 30)
    assert {k: v["split"] for k, v in a.chunks.items()} == {k: v["split"] for k, v in b.chunks.items()}
    before = {k: v["split"] for k, v in a.chunks.items()}
    rep = assign_splits(a, tr, 300, 300)  # different targets must not move frozen splits
    assert rep.assigned_chunks == 0
    assert {k: v["split"] for k, v in a.chunks.items()} == before


def test_regen_of_inherits_and_new_groups_hash():
    pc = corpus()
    assign_splits(pc, set(pc.chunks), 30, 30)
    test_group = next(r["source_custom_id"] for r in pc.chunks.values() if r["split"] == "test")
    for k in range(3):
        cid = f"ffff{k:04d}".ljust(32, "0")
        pc.chunks[cid] = {"chunk_id": cid, "split": "", "status": "active", "domain_l1": "a",
                          "source_custom_id": "regen-1", "regen_of": test_group}
    for k in range(2):
        cid = f"eeee{k:04d}".ljust(32, "0")
        pc.chunks[cid] = {"chunk_id": cid, "split": "", "status": "active", "domain_l1": "a",
                          "source_custom_id": "brand-new", "regen_of": ""}
    rep = assign_splits(pc, set())
    assert rep.mode == "hash-ratio"
    assert {pc.chunks[f"ffff{k:04d}".ljust(32, '0')]["split"] for k in range(3)} == {"test"}
    assert len({pc.chunks[f"eeee{k:04d}".ljust(32, '0')]["split"] for k in range(2)}) == 1


def test_straddling_group_is_an_error():
    pc = corpus(2, 2)
    ids = list(pc.chunks)
    pc.chunks[ids[0]]["split"] = "train"
    pc.chunks[ids[1]]["split"] = "test"
    try:
        assign_splits(pc, set())
    except SplitConflict:
        return
    raise AssertionError("expected SplitConflict")
