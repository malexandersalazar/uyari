"""The paid path, end to end, against a mocked Meta Responses API: plan -> calls -> ledger ->
idempotent re-run -> dedup -> publish into primary with inherited splits. No network."""

import json
import shutil
from pathlib import Path

import httpx
import pytest

from uyari.csvio import read_csv, read_jsonl

REPO = Path(__file__).resolve().parents[1]

TEXTS = ["Mi abuela camina con la canoa.", "La lluvia cae sobre el río.", "Vamos al río con la abuela.",
         "El río crece con la lluvia.", "Mi tía rema en la canoa.", "La canoa espera en el río.",
         "Hoy no hay lluvia en el monte.", "El niño mira la canoa.", "La abuela lava en el río.",
         "Con la lluvia todo está verde."]


@pytest.fixture()
def mocked(fixture_root, monkeypatch):
    shutil.copy(REPO / "primary/spa_Latn/matrix.yaml", fixture_root.primary_dir("spa_Latn") / "matrix.yaml")
    monkeypatch.setenv("META_API_KEY", "test-key")
    monkeypatch.setenv("META_API_URL", "http://mock.local/v1/responses")
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None, **kw):  # noqa: A002
        calls.append(json)
        k = len(calls)
        texts = [f"{t[:-1]} número {k}." for t in TEXTS]
        body = {"id": f"resp_{k}", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": __import__("json").dumps({"texts": texts}, ensure_ascii=False)}]}],
            "usage": {"input_tokens": 500, "output_tokens": 800, "input_tokens_details": {"cached_tokens": 100}}}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr("uyari.llm.client.httpx.post", fake_post)
    return fixture_root, calls


def test_generate_pay_once_ledger_and_publish(mocked):
    from uyari.gen.dedup import run_dedup
    from uyari.gen.generate import run_generate
    from uyari.gen.plan import make_plan
    from uyari.llm.ledger import Ledger

    root, calls = mocked
    info = make_plan(root, "2026-11_mock_0001", regen_from="fixture", cells=3)
    assert info["units"] == 3
    est = run_generate(root, "2026-11_mock_0001", estimate_only=True)
    assert not calls and est["expected_usd"] > 0

    res = run_generate(root, "2026-11_mock_0001", assume_yes=True, concurrency=2)
    assert res["sent"] == 3 and len(calls) == 3
    body = calls[0]
    assert body["model"] == "muse-spark-1.3-contributor" and body["text"]["format"]["type"] == "json_schema"
    led = Ledger(root).entries()
    assert len(led) == 3
    per_call = (400 * 0.10 + 100 * 0.002 + 800 * 0.20) / 1_000_000
    assert led[0]["cost_usd"] == pytest.approx(per_call)
    assert res["texts_accepted"] == 30

    again = run_generate(root, "2026-11_mock_0001", assume_yes=True)
    assert again["sent"] == 0 and len(calls) == 3, "a re-run must never pay twice"

    rep = run_dedup(root, "2026-11_mock_0001", semantic=False)
    assert rep["clean"] == 30
    published = read_csv(root.primary_dir("spa_Latn") / "chunks/generated/2026-11_mock_0001.csv")
    src_split = {r["source_custom_id"]: r["split"] for r in
                 read_csv(root.primary_dir("spa_Latn") / "chunks/generated/fixture.csv")}
    for r in published:
        assert r["regen_of"] and r["split"] == src_split[r["regen_of"]]
        assert r["gen_model"] == "muse-spark-1.3-contributor" and r["origin"] == "synthetic"
    assert read_jsonl(root.runs / "gen/2026-11_mock_0001/responses.jsonl")


def test_cap_stops_the_run(mocked):
    from uyari.gen.generate import run_generate
    from uyari.gen.plan import make_plan
    from uyari.llm.ledger import BudgetExceeded

    root, calls = mocked
    make_plan(root, "2026-11_mock_0002", regen_from="fixture", cells=3)
    with pytest.raises(BudgetExceeded):
        run_generate(root, "2026-11_mock_0002", max_usd=0.0000001, assume_yes=True)
    assert not calls
    _ = json
