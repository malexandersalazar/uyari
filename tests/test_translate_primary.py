"""Second primary by machine translation, against a mocked Meta Responses API: same chunk ids, copied
splits, labelled provenance, pay once, Spanish-looking output rejected and retried. No network."""

import json

import httpx
import pytest

from uyari.csvio import read_csv, read_jsonl
from uyari.data.primary import load_primary


@pytest.fixture()
def mocked(fixture_root, monkeypatch):
    monkeypatch.setenv("META_API_KEY", "test-key")
    monkeypatch.setenv("META_API_URL", "http://mock.local/v1/responses")
    calls = []

    def fake_post(url, headers=None, json=None, timeout=None, **kw):  # noqa: A002
        calls.append(json)
        items = __import__("json").loads(json["input"])
        out = [{"id": it["id"], "text": "Esto sigue en español y no es la traducción." if "SPANISH" in it["text"]
                and len(items) > 1 else f"The English version number {it['id']} of this sentence."}
               for it in items]
        body = {"id": f"resp_{len(calls)}", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": __import__("json").dumps({"items": out})}]}],
            "usage": {"input_tokens": 300, "output_tokens": 200}}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr("uyari.llm.client.httpx.post", fake_post)
    return fixture_root, calls


def test_translate_primary_same_ids_splits_and_pay_once(mocked):
    from uyari.gen.translate_primary import out_file, run_translate

    root, calls = mocked
    src = load_primary(root, "spa_Latn")
    est = run_translate(root, "2026-11_mock_0001", estimate_only=True, per_request=3)
    assert not calls and est["expected_usd"] > 0 and est["sentences"] == len(src.chunks)

    res = run_translate(root, "2026-11_mock_0001", per_request=3, assume_yes=True, concurrency=2)
    assert res["written"] == len(src.chunks) and res["failed"] == 0
    rows = read_csv(out_file(root, "eng_Latn", "2026-11_mock_0001"))
    assert {r["chunk_id"] for r in rows} == set(src.chunks)
    for r in rows:
        s = src.chunks[r["chunk_id"]]
        assert r["split"] == s["split"] and r["source_custom_id"] == s.get("source_custom_id", "")
        assert r["origin"] == "machine_translated" and r["gen_model"] == "muse-spark-1.3-contributor"
        assert r["text"].startswith("The English version")
    assert calls[0]["text"]["format"]["type"] == "json_schema"

    n = len(calls)
    again = run_translate(root, "2026-11_mock_0001", per_request=3, assume_yes=True)
    assert len(calls) == n and again["to_translate"] == 0, "a re-run must not pay again"


def test_spanish_output_is_rejected_then_retried_alone(mocked, fixture_root):
    from uyari.data.primary import write_chunks
    from uyari.gen.translate_primary import check, run_translate

    assert check("Hola, ¿cómo estás hoy?", "Esto sigue en español y no es la traducción.", "eng_Latn")
    assert check("Hola", "Hello, how are you today?", "eng_Latn") == ""
    pc = load_primary(fixture_root, "spa_Latn")
    f = pc.files[0]
    rows = read_csv(f)
    rows[0]["text"] = "SPANISH " + rows[0]["text"]
    write_chunks(f, rows)
    root, calls = mocked
    res = run_translate(root, "2026-11_mock_0002", per_request=50, assume_yes=True)
    assert res["failed"] == 0 and len(calls) == 2, "one batch call, then the rejected item alone"
    assert not read_jsonl(root.runs / "primary-translate" / "2026-11_mock_0002" / "failures.jsonl")
    assert json.loads(calls[1]["input"])[0]["text"].startswith("SPANISH")
