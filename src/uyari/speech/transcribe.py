"""Spanish speech to text with Muse Voice Transcribe (Meta Model API, batch: one POST per file).

Official language only (``data_policy: official_only``): never send Indigenous-language audio here.
Cost is priced by audio duration ($0.18 per hour). ``POST /v1/asr/transcribe`` with a multipart body
(a JSON ``request`` part and the ``audio`` part, mono 16-bit WAV at 16 kHz), as in Meta's model cookbook
(``06_muse_voice``); the URL can be overridden with ``META_TRANSCRIBE_URL``.

Two ways to pay:

* **Your own key from the environment** (the CLI, ``api_key=None``): ``META_API_KEY`` is used, the
  ``transcribe`` run cap applies ($2, config/llm.yaml) and every call is in the ledger.
* **Bring your own key** (the demo, ``api_key="..."``): only the key passed in is used, never the
  environment, so a public demo cannot spend the server owner's budget. The caller pays, so the call is
  not counted against the project's budget and nothing about it (key, audio, text) is stored.
"""

from __future__ import annotations

import io
import json
import uuid
from pathlib import Path

from uyari.llm import policy
from uyari.llm.catalog import load_catalog
from uyari.llm.client import confirm
from uyari.llm.ledger import Ledger, RunBudget
from uyari.paths import Paths

LANGUAGE_BIAS = {"es": "spanish", "en": "english", "pt": "portuguese", "fr": "french"}


def duration_s(path: Path) -> float:
    import soundfile as sf

    info = sf.info(str(path))
    return info.frames / info.samplerate


def wav16k(path: Path) -> bytes:
    """Mono 16-bit PCM WAV at 16 kHz, the format the endpoint accepts (browser recordings are often 48 kHz)."""
    import soundfile as sf

    from uyari.pipelines.asr.infer import _load_16k

    buf = io.BytesIO()
    sf.write(buf, _load_16k(Path(path)), 16000, subtype="PCM_16", format="WAV")
    return buf.getvalue()


def request_parts(spec, audio: Path, language: str) -> dict:
    """Multipart body of POST /v1/asr/transcribe (Meta model cookbook, 06_muse_voice)."""
    req = {"mode": "PUSH_TO_TALK", "model": spec.model_id, "audioEncoding": "WAV"}
    if language in LANGUAGE_BIAS:
        req["languageBias"] = [LANGUAGE_BIAS[language]]
    return {"request": (None, json.dumps(req), "application/json"),
            "audio": (Path(audio).with_suffix(".wav").name, wav16k(audio), "audio/wav")}


def transcribe_file(paths: Paths, audio: Path, estimate_only: bool = False, assume_yes: bool = False,
                    language: str = "es", command: str = "transcribe", api_key: str | None = None,
                    max_seconds: float | None = None) -> dict:
    import httpx

    cat = load_catalog(paths)
    spec = cat.get("muse-voice-transcribe")
    policy.check(spec, "official")
    secs = duration_s(audio)
    est = spec.audio_cost(secs)
    byok = api_key is not None
    out = {"file": str(audio), "seconds": round(secs, 2), "estimate_usd": round(est, 6), "url": spec.url}
    if max_seconds is not None and secs > max_seconds:
        raise ValueError(f"audio is {secs:.0f}s; the limit is {max_seconds:.0f}s")
    if estimate_only:
        return out
    if byok:
        key = api_key.strip()
        if not key:
            raise ValueError("no API key given")
        budget = None
    else:
        key = spec.api_key
        ledger = Ledger(paths)
        budget = RunBudget(ledger, f"{command}-{uuid.uuid4().hex[:6]}", cap_usd=cat.run_cap("transcribe"))
        budget.check_plan(est)
        if not confirm(f"Transcribe {secs:.1f}s with {spec.key} (about ${est:.5f})?", assume_yes):
            return {**out, "sent": False}
        if not key:
            raise RuntimeError(f"{spec.key_env} not set")
    r = httpx.post(spec.url, headers={"Authorization": f"Bearer {key}"}, files=request_parts(spec, audio, language),
                   timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
    data = r.json()
    text = data.get("transcript") or " ".join(t.get("transcript", "") for t in data.get("turns") or [])
    if budget is not None:
        ledger.record(run_id=budget.run_id, command=command, model=spec.key, data_class="official",
                      audio_seconds=round(secs, 2), cost_usd=round(est, 8),
                      request_id=r.headers.get("x-request-id", ""))
    return {**out, "sent": True, "text": text.strip(), "cost_usd": round(est, 8), "paid_by": "caller" if byok else "env"}
