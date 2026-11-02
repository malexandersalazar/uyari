"""Bring your own key: the demo's voice input must never use or charge the server's own Meta key."""

from __future__ import annotations

import sys

import numpy as np
import pytest
import soundfile as sf

from conftest import REPO
from uyari.speech.transcribe import transcribe_file

sys.path.insert(0, str(REPO / "demo"))
from app import transcribe_byok  # noqa: E402  demo/app.py


class _Resp:
    status_code = 200
    headers = {"x-request-id": "req-1"}

    @staticmethod
    def json():
        return {"transcript": "¿Dónde está la posta?", "audioDurationMs": 2000}


@pytest.fixture()
def wav(tmp_path):
    p = tmp_path / "clip.wav"
    sf.write(str(p), np.zeros(16000 * 2, dtype="float32"), 16000)
    return p


@pytest.fixture()
def calls(monkeypatch):
    import httpx

    seen = []
    monkeypatch.setattr(httpx, "post", lambda url, **kw: seen.append(kw["headers"]) or _Resp())
    monkeypatch.setenv("META_API_KEY", "server-key")
    return seen


def test_byok_uses_only_the_visitor_key_and_skips_the_ledger(fixture_root, wav, calls):
    r = transcribe_file(fixture_root, wav, api_key="visitor-key")
    assert r["text"] == "¿Dónde está la posta?" and r["paid_by"] == "caller"
    assert calls == [{"Authorization": "Bearer visitor-key"}]
    assert not (fixture_root.state / "ledger.jsonl").exists(), "a visitor's spend is not the project's"


def test_empty_byok_key_never_falls_back_to_the_environment(fixture_root, wav, calls):
    with pytest.raises(ValueError):
        transcribe_file(fixture_root, wav, api_key="  ")
    heard, note = transcribe_byok(fixture_root, str(wav), "")
    assert heard == "" and "key" in note
    assert calls == []


def test_byok_length_limit_and_key_never_echoed(fixture_root, wav, calls):
    with pytest.raises(ValueError):
        transcribe_file(fixture_root, wav, api_key="visitor-key", max_seconds=1)
    heard, note = transcribe_byok(fixture_root, str(wav), "visitor-key")
    assert heard and "visitor-key" not in note
    assert calls == [{"Authorization": "Bearer visitor-key"}]


def test_cli_path_still_uses_env_key_and_ledger(fixture_root, wav, calls):
    r = transcribe_file(fixture_root, wav, assume_yes=True)
    assert r["paid_by"] == "env" and calls == [{"Authorization": "Bearer server-key"}]
    assert (fixture_root.state / "ledger.jsonl").is_file()
