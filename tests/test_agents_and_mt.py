import csv
import json
from datetime import date

import pytest

from uyari.build import run_build


def _recipe(fixture_root, tmp_path):
    p = tmp_path / "r.yaml"
    p.write_text("""id: qaa-spa.mt.test
build: data-2026.10
task: mt
language: qaa_Latn
primary: spa_Latn
directions: [spa>qaa, qaa>spa]
base_model: none/none
method: seq2seq
text_codec: {"ʼ": "'"}
train: {epochs: 1}
output: models/mt-qaa-spa-test@v0.1
""", encoding="utf-8")
    return p


def test_prepare_never_reads_test_and_codec_roundtrips(fixture_root, tmp_path):
    from uyari.csvio import read_jsonl
    from uyari.pipelines.mt.codec import Codec
    from uyari.pipelines.mt.prepare import run_prepare

    run_build(fixture_root, "data-2026.10", as_of=date(2026, 11, 2))
    out = run_prepare(fixture_root, _recipe(fixture_root, tmp_path), check_tokenizer=False)
    train = read_jsonl(out.dir / "train.jsonl")
    val = read_jsonl(out.dir / "validation.jsonl")
    assert {r["split"] for r in train} == {"train"} and {r["split"] for r in val} == {"validation"}
    assert out.stats["by_direction"]["train"]["spa>qaa"] == out.stats["by_direction"]["train"]["qaa>spa"]
    c = Codec({"ʼ": "'"})
    for r in train:
        if r["tgt_lang"] == "qaa_Latn":
            assert "ʼ" not in r["tgt_model"] and c.decode(r["tgt_model"]) == r["tgt"]


def test_retrieval_floor_scores(fixture_root, tmp_path):
    from uyari.pipelines.mt.eval import run_eval

    run_build(fixture_root, "data-2026.10", as_of=date(2026, 11, 2))
    res = run_eval(fixture_root, "retrieval", "validation", recipe=_recipe(fixture_root, tmp_path))
    v = res["validation"]
    assert v["spa>qaa"]["n"] > 0 and v["mean_chrf++"] is not None


def test_test_split_scored_once(fixture_root):
    from uyari.pipelines.mt.eval import TestAlreadyScored, run_eval

    d = fixture_root.models / "mt-qaa-spa-x@v0.1"
    d.mkdir(parents=True)
    (d / "uyari_meta.json").write_text(json.dumps({"name": d.name, "kind": "nllb"}), encoding="utf-8")
    (d / "scores.json").write_text(json.dumps({"test": {"scored_at": "2026-11-02"}}), encoding="utf-8")
    with pytest.raises(TestAlreadyScored):
        run_eval(fixture_root, str(d), "test")


def _bad_contribution(fixture_root):
    base = fixture_root.data / "languages/qaa_Latn/contributions"
    good = list(csv.DictReader((base / "2026-10_fixture_0001/pairs.csv").open(encoding="utf-8")))
    d = base / "2026-11_demo_0001"
    d.mkdir()
    (d / "contribution.yaml").write_text((base / "2026-11_fixture_0002/contribution.yaml").read_text(encoding="utf-8")
                                         .replace("2026-11_fixture_0002", "2026-11_demo_0001"), encoding="utf-8")
    rows = [
        ["0900" + "a" * 28, "El niño tiene fiebre desde ayer y no quiere comer nada.", "", "t-0003", ""],  # Spanish
        [good[5]["chunk_id"], good[5]["text"], "", "t-0003", ""],                                   # copied row
        ["0901" + "a" * 28, "kuwa'nu hpana'ra", "", "t-0003", ""],                                    # ASCII apostrophe
        ["f" * 32, "kunuwa shawera", "", "t-0003", ""],                                               # unknown id
    ]
    with (d / "pairs.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["chunk_id", "text", "replaces", "translator_id", "notes"])
        w.writerows(rows)
    return d


def test_gatekeeper_flags_the_four_demo_defects(fixture_root):
    from uyari.agents.gatekeeper.run import run_gatekeeper

    res = run_gatekeeper(fixture_root, _bad_contribution(fixture_root), llm=None)
    F = res.findings
    codes = {e["code"] for e in F["validator_errors"]}
    assert res.recommendation == "return"
    assert {"apostrophe", "unknown_chunk"} <= codes
    assert F["spanish_like"], "Spanish pasted in the Shawi column was not flagged"
    assert F["copied"], "copied row was not flagged"
    assert "Recomendación: devolver" in res.markdown


def test_needs_md(fixture_root):
    from uyari.agents.trainer.needs import write_needs

    run_build(fixture_root, "data-2026.10", as_of=date(2026, 11, 2))
    text = write_needs(fixture_root, "qaa_Latn", "data-2026.10")
    assert "clips" in text and (fixture_root.data / "languages/qaa_Latn/NEEDS.md").is_file()


def test_asr_eval_plumbing_on_fixture(fixture_root):
    from uyari.pipelines.asr.eval import run_asr_eval

    run_build(fixture_root, "data-2026.10", as_of=date(2026, 11, 2))
    res = run_asr_eval(fixture_root, "data-2026.10", "qaa_Latn", backend="null", split="train")
    assert res["clips"] >= 1 and res["label"] == "plumbing test only"


def test_promotion_compares_shared_directions_and_allows_added_ones():
    from uyari.agents.trainer.run import promotion_margin_ok

    def sc(**kw):
        return {k.replace("_", ">"): {"chrf++": v} for k, v in kw.items()}

    inc = sc(spa_cbt=38.0, cbt_spa=37.7)
    assert promotion_margin_ok(sc(spa_cbt=38.6, cbt_spa=38.2), inc)
    assert not promotion_margin_ok(sc(spa_cbt=38.1, cbt_spa=37.8), inc), "same directions need +0.5"
    assert promotion_margin_ok(sc(spa_cbt=37.8, cbt_spa=37.6, eng_cbt=30.0, cbt_eng=29.0), inc), "adds English"
    assert not promotion_margin_ok(sc(spa_cbt=36.0, cbt_spa=36.0, eng_cbt=30.0, cbt_eng=29.0), inc), "regresses"
    assert promotion_margin_ok(sc(spa_cbt=10.0), None)


def _fake_model(fixture_root, tmp_path, name, val, test=None):
    d = fixture_root.models / name
    d.mkdir(parents=True)
    (d / "recipe.yaml").write_text(_recipe(fixture_root, tmp_path).read_text(encoding="utf-8"), encoding="utf-8")
    (d / "uyari_meta.json").write_text(json.dumps({
        "name": name, "kind": "nllb", "method": "seq2seq", "language": "qaa_Latn", "build": "data-2026.10",
        "primary": "spa_Latn", "directions": ["spa_Latn>qaa_Latn", "qaa_Latn>spa_Latn"]}), encoding="utf-8")
    sc = {"validation": {k: {"chrf++": v} for k, v in val.items()} | {"mean_chrf++": sum(val.values()) / 2}}
    if test:
        sc["test"] = {k: {"chrf++": v} for k, v in test.items()}
    (d / "scores.json").write_text(json.dumps(sc), encoding="utf-8")
    return f"models/{name}"


def test_register_applies_the_trainer_rule(fixture_root, tmp_path, monkeypatch):
    import uyari.pipelines.mt.card as card
    from uyari.agents.trainer.run import register_model
    from uyari.registry import load, promoted

    cards = []

    def fake_card(paths, d, demo_note=""):
        cards.append(d.name)
        (d / "MODEL_CARD.md").write_text("card", encoding="utf-8")

    monkeypatch.setattr(card, "write_card", fake_card)
    run_build(fixture_root, "data-2026.10", as_of=date(2026, 11, 2))
    t = {"spa>qaa": 90.0, "qaa>spa": 90.0}

    low = _fake_model(fixture_root, tmp_path, "mt-qaa-spa-low@v0.1", {"spa>qaa": 0.1, "qaa>spa": 0.1}, t)
    r = register_model(fixture_root, low)
    assert r["decision"] == "not registered" and "floor" in r["why"] and not promoted(fixture_root, "mt", "qaa_Latn", "fast")

    a = _fake_model(fixture_root, tmp_path, "mt-qaa-spa-a@v0.1", {"spa>qaa": 90.0, "qaa>spa": 90.0}, t)
    r = register_model(fixture_root, a)
    assert r["decision"] == "registered" and r["slot"] == "fast" and r["test"] == t
    assert promoted(fixture_root, "mt", "qaa_Latn", "fast") == "mt-qaa-spa-a@v0.1" and cards == ["mt-qaa-spa-a@v0.1"]
    assert register_model(fixture_root, a)["decision"] == "already registered"

    b = _fake_model(fixture_root, tmp_path, "mt-qaa-spa-b@v0.1", {"spa>qaa": 90.2, "qaa>spa": 90.2}, t)
    r = register_model(fixture_root, b)
    assert r["decision"] == "not registered" and "does not beat mt-qaa-spa-a@v0.1" in r["why"]
    with pytest.raises(ValueError):
        register_model(fixture_root, b, force=True)
    r = register_model(fixture_root, b, force=True, reason="demo needs it")
    assert r["decision"] == "registered" and cards[-2:] == ["mt-qaa-spa-b@v0.1", "mt-qaa-spa-a@v0.1"]
    last = load(fixture_root)["mt"]["qaa_Latn"]["history"][-1]
    assert last["to"] == "mt-qaa-spa-b@v0.1" and last["reason"].startswith("forced: demo needs it")


def test_clean_completion_keeps_the_translation():
    from uyari.pipelines.mt.train_causal import clean_completion

    assert clean_completion(" to=user<|message|>Yaʼi waʼwaruʼsa.<|eot|>") == "Yaʼi waʼwaruʼsa."
    # a stray channel marker after the translation must not leave an empty answer
    assert clean_completion("Yaʼi waʼwaruʼsa aʼchinpeike paʼ<|message|>") == "Yaʼi waʼwaruʼsa aʼchinpeike paʼ"
    assert clean_completion(" to=user<|message|>Ipiʼ<|message|><|eot|>") == "Ipiʼ"
    assert clean_completion("<|channel|>analysis<|message|>think<|end|><|start|>assistant<|channel|>final"
                            "<|message|>Ipiʼ<|eot|>") == "Ipiʼ"
    assert clean_completion("Ipiʼ\nsecond line") == "Ipiʼ" and clean_completion("<|message|>") == ""


def test_into_rotation_keeps_k_sources_per_target_and_every_example_out():
    from collections import Counter

    from uyari.pipelines.mt.train_causal import into_rotation

    offs = ["spa_Latn", "eng_Latn", "fra_Latn", "deu_Latn", "ita_Latn", "por_Latn"]
    rows = [{"chunk_id": f"c{c}", "src_lang": o, "tgt_lang": "cbt_Latn", "tgt": f"shawi {c}"} for c in range(30)
            for o in offs]
    rows += [{"chunk_id": f"c{c}", "src_lang": "cbt_Latn", "tgt_lang": o, "tgt": f"{o} {c}"} for c in range(30)
             for o in offs]
    assert into_rotation(rows, "cbt_Latn", None, 7, 0) == list(range(len(rows)))
    e0, e1 = into_rotation(rows, "cbt_Latn", 2, 7, 0), into_rotation(rows, "cbt_Latn", 2, 7, 1)
    for idx in (e0, e1):
        kept = [rows[i] for i in idx]
        assert sum(r["tgt_lang"] != "cbt_Latn" for r in kept) == 180  # every direction out of Shawi
        assert set(Counter(r["chunk_id"] for r in kept if r["tgt_lang"] == "cbt_Latn").values()) == {2}
    assert e0 == into_rotation(rows, "cbt_Latn", 2, 7, 0) and e0 != e1  # deterministic, rotates per epoch
    sources = Counter(rows[i]["src_lang"] for e in range(30) for i in into_rotation(rows, "cbt_Latn", 2, 7, e)
                      if rows[i]["tgt_lang"] == "cbt_Latn")
    assert set(sources) == set(offs) and max(sources.values()) < 2 * min(sources.values())  # all six, balanced


def test_selection_on_into_and_the_subset():
    from uyari.pipelines.mt.train_causal import selection_metric, selection_rows

    sc = {"spa>cbt": 40.0, "eng>cbt": 42.0, "cbt>spa": 50.0, "cbt>eng": 48.0}
    assert selection_metric(sc, "cbt_Latn", "into") == {"score": 41.0, "into": 41.0, "out": 49.0, "all": 45.0}
    assert selection_metric(sc, "cbt_Latn")["score"] == 45.0
    with pytest.raises(ValueError):
        selection_metric(sc, "cbt_Latn", "best")
    rows = [{"id": f"{c}:{d}", "src_lang": d[0], "tgt_lang": d[1]} for c in range(100)
            for d in [("spa_Latn", "cbt_Latn"), ("eng_Latn", "cbt_Latn"), ("cbt_Latn", "spa_Latn"), ("cbt_Latn", "eng_Latn")]]
    sub = selection_rows(rows, "cbt_Latn", {"select_into": 30, "select_out": 10}, 7)
    from collections import Counter

    assert Counter((r["src_lang"], r["tgt_lang"]) for r in sub) == {
        ("spa_Latn", "cbt_Latn"): 30, ("eng_Latn", "cbt_Latn"): 30, ("cbt_Latn", "spa_Latn"): 10,
        ("cbt_Latn", "eng_Latn"): 10}
    assert len(selection_rows(rows, "cbt_Latn", {"select_limit": 40}, 7)) == 40
