"""The demo's voice path: Spanish or English speech into Shawi, paid only with the visitor's key, and the
"What works today" panel, whose numbers must be the ones in the files. No network: HTTP is mocked."""

from __future__ import annotations

import json
import sys

import numpy as np
import pytest
import soundfile as sf

from conftest import REPO
from uyari.paths import Paths

sys.path.insert(0, str(REPO / "demo"))
from app import (  # noqa: E402  demo/app.py
    _examples_for,
    _examples_from,
    _models,
    hear,
    officials,
    pivot_byok,
    route,
    status_md,
    voice_plan,
)

SPA = {("spa_Latn", "cbt_Latn"), ("cbt_Latn", "spa_Latn")}
ENG = SPA | {("eng_Latn", "cbt_Latn"), ("cbt_Latn", "eng_Latn")}
SIX = {d for o in ("spa_Latn", "eng_Latn", "fra_Latn", "deu_Latn", "ita_Latn", "por_Latn")
       for d in ((o, "cbt_Latn"), ("cbt_Latn", o))}
NLLB, GLIMMER = "NLLB · fast", "Glimmer · open weights"


class _Resp:
    status_code = 200
    headers = {"x-request-id": "req-1"}

    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


@pytest.fixture()
def wav(tmp_path):
    p = tmp_path / "clip.wav"
    sf.write(str(p), np.zeros(16000 * 2, dtype="float32"), 16000)
    return p


@pytest.fixture()
def meta(monkeypatch):
    """Muse Voice Transcribe hears English; Muse Spark answers in Spanish. Records every request."""
    import httpx

    seen = []

    def post(url, **kw):
        if "/asr/" in url:
            seen.append(("transcribe", kw["headers"], json.loads(kw["files"]["request"][1])))
            return _Resp({"transcript": "Where is the health post?"})
        seen.append(("spark", kw["headers"], kw["json"]))
        answer = {"items": [{"id": "1", "text": "¿Dónde está la posta de salud?"}]}
        return _Resp({"output_text": json.dumps(answer), "usage": {"input_tokens": 200, "output_tokens": 20}})

    monkeypatch.setattr(httpx, "post", post)
    for var in ("META_API_URL", "META_TRANSCRIBE_URL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("META_API_KEY", "server-key")
    return seen


def test_shawi_is_always_on_one_side():
    """Official -> Shawi and Shawi -> official, each in its own tab; Spanish <-> English and anything else is
    refused, not routed."""
    assert officials({NLLB: {"dirs": ENG}}, into=True) == ["Spanish", "English"]
    assert officials({NLLB: {"dirs": ENG}}, into=False) == ["Spanish", "English"]
    assert officials({NLLB: {"dirs": SPA}}, into=True) == ["Spanish"]
    assert officials({NLLB: {"dirs": {("spa_Latn", "cbt_Latn")}}}, into=False) == []
    for s, t in [("Spanish", "Shawi"), ("English", "Shawi"), ("Shawi", "Spanish"), ("Shawi", "English")]:
        assert route({NLLB: {"dirs": ENG}}, NLLB, s, t) == NLLB
    six = ["Spanish", "English", "French", "German", "Italian", "Portuguese"]
    assert officials({NLLB: {"dirs": SIX}}, into=True) == six == officials({NLLB: {"dirs": SIX}}, into=False)
    for name in six:
        assert route({NLLB: {"dirs": SIX}}, NLLB, name, "Shawi") == route({NLLB: {"dirs": SIX}}, NLLB, "Shawi",
                                                                          name) == NLLB
    for s, t in [("English", "Spanish"), ("Spanish", "English"), ("French", "German"), ("Italian", "Portuguese"),
                 ("Spanish", "Spanish"), ("Shawi", "Shawi"), ("Thai", "Shawi"), ("Shawi", "Hindi"), (None, "Shawi")]:
        with pytest.raises(ValueError, match="Shawi on one side"):
            route({NLLB: {"dirs": SIX}}, NLLB, s, t)
    for s, t in [("Shawi", "English"), ("French", "Shawi")]:
        with pytest.raises(ValueError, match="not available yet"):
            route({NLLB: {"dirs": SPA}}, NLLB, s, t)
    both = {NLLB: {"dirs": SPA}, GLIMMER: {"dirs": ENG}}
    assert route(both, NLLB, "English", "Shawi") == GLIMMER  # another model that can
    assert all(len(_examples_for(name)) == 4 for name in six) and _examples_for("Shawi") == []


def test_shawi_examples_are_short_human_training_sentences(monkeypatch):
    import uyari.build

    def row(i, domain, text, split="train", src="spa_Latn"):
        return {"chunk_id": f"c{i:02d}", "domain": domain, "tgt_text": text, "split": split, "src_lang": src}

    five = "uno dos tres cuatro cinco"
    rows = [row(1, "salud_cuerpo", f"{five} a"), row(2, "puente_civico", f"{five} b"),
            row(3, "puente_civico", f"{five} c"), row(4, "comercio_intercambio", f"{five} d"),
            row(5, "comercio_intercambio", f"{five} e"), row(6, "viaje_desplazamiento", f"{five} f"),
            row(0, "salud_cuerpo", "too short"), row(7, "salud_cuerpo", f"{five} {five}"),
            row(8, "salud_cuerpo", f"{five} ?"), row(9, "salud_cuerpo", f"{five} v", split="validation"),
            row(10, "salud_cuerpo", f"{five} en", src="eng_Latn")]
    monkeypatch.setattr(uyari.build, "read_table", lambda paths, build, lang, task: rows)
    models = {NLLB: {"dirs": ENG, "build": "b"}}
    assert _examples_from(None, models) == [[f"{five} a"], [f"{five} b"], [f"{five} d"], [f"{five} f"]]
    assert _examples_from(None, {NLLB: {"dirs": {("spa_Latn", "cbt_Latn")}, "build": "b"}}) == []


def test_voice_plan_prefers_a_registered_english_model():
    assert voice_plan({NLLB: {"dirs": SPA}}, NLLB, "spa_Latn") == (NLLB, False)
    assert voice_plan({NLLB: {"dirs": SPA}}, NLLB, "eng_Latn") == (NLLB, True)  # through Spanish
    both = {NLLB: {"dirs": SPA}, GLIMMER: {"dirs": ENG}}
    assert voice_plan(both, NLLB, "eng_Latn") == (GLIMMER, False)
    assert voice_plan(both, NLLB, "spa_Latn") == (NLLB, False)


def test_english_without_an_english_model_goes_through_spanish_with_the_visitor_key(fixture_root, wav, meta):
    r = hear(fixture_root, {NLLB: {"dirs": SPA}}, str(wav), "visitor-key", "English", NLLB)
    assert r["ok"] and r["text"] == "¿Dónde está la posta de salud?" and r["src"] == "Spanish" and r["mode"] == NLLB
    assert r["heard"] == "Where is the health post?"  # shown as heard; the Spanish is what gets translated
    assert "Muse Spark" in r["note"] and "Where is the health post?" in r["note"]
    kinds = [k for k, _, _ in meta]
    assert kinds == ["transcribe", "spark"]
    assert all(h["Authorization"] == "Bearer visitor-key" for _, h, _ in meta), "never the server's key"
    assert meta[0][2]["languageBias"] == ["english"]
    spark = meta[1][2]
    assert spark["model"] == "muse-spark-1.3-contributor"
    assert json.loads(spark["input"]) == {"items": [{"id": "1", "text": "Where is the health post?"}]}
    assert not (fixture_root.state / "ledger.jsonl").exists(), "a visitor's spend is not the project's"


def test_english_with_a_registered_english_model_skips_muse_spark(fixture_root, wav, meta):
    both = {NLLB: {"dirs": SPA}, GLIMMER: {"dirs": ENG}}
    r = hear(fixture_root, both, str(wav), "visitor-key", "English", NLLB)
    assert r["ok"] and r["text"] == "Where is the health post?" and r["src"] == "English" and r["mode"] == GLIMMER
    assert "Muse Spark" not in r["note"]
    assert [k for k, _, _ in meta] == ["transcribe"]


def test_spanish_speech_is_transcribed_as_spanish(fixture_root, wav, meta):
    r = hear(fixture_root, {NLLB: {"dirs": SPA}}, str(wav), "visitor-key", "Spanish", NLLB)
    assert r["ok"] and r["src"] == "Spanish" and meta[0][2]["languageBias"] == ["spanish"] and len(meta) == 1


def test_no_key_no_call_and_errors_never_echo_the_key(fixture_root, wav, meta, monkeypatch):
    r = hear(fixture_root, {NLLB: {"dirs": SPA}}, str(wav), "  ", "English", NLLB)
    assert not r["ok"] and "key" in r["note"] and meta == []
    assert pivot_byok(fixture_root, "Hello", "") == ("", "Enter your own Meta API key. This server does not use "
                                                           "its own key.")
    import httpx

    def fail(url, **kw):  # noqa: ARG001
        raise RuntimeError("refused for visitor-key")

    monkeypatch.setattr(httpx, "post", fail)
    text, msg = pivot_byok(fixture_root, "Hello", "visitor-key")
    assert text == "" and "visitor-key" not in msg and "***" in msg


def test_the_pivot_refuses_anything_but_official_languages(fixture_root):
    from uyari.llm.pivot import translate_official

    with pytest.raises(ValueError):
        translate_official(fixture_root, "Ipiʼ", "cbt_Latn", "spa_Latn", api_key="visitor-key")


def test_panel_numbers_are_the_files_numbers():
    real = Paths(code=REPO, data=REPO)
    if not (REPO / "models/registry.yaml").is_file():
        pytest.skip("no registered model")
    models = _models(real)
    md = status_md(real, models, {"before": 0.8598, "after": 0.9999})
    for m in models.values():
        scores = json.loads((m["dir"] / "scores.json").read_text(encoding="utf-8"))
        for split in ("validation", "test"):
            for key, s in scores[split].items():
                if ">" in key:
                    assert f"{s['chrf++']:.1f}" in md, (split, key)
        assert f"{scores['validation']['mean_chrf++']:.2f}" in md
        assert m["ref"] in md
    import re

    import yaml

    hist = yaml.safe_load((REPO / "models/registry.yaml").read_text(encoding="utf-8"))["mt"]["cbt_Latn"]["history"]
    for m in models.values():  # the floor the registry recorded when the served model was registered
        reason = [h["reason"] for h in hist if h["to"] == m["ref"]][-1]
        floor = float(re.search(r"floor (\d+(?:\.\d+)?)", reason).group(1))
        assert f"against a retrieval floor of {floor:.2f}" in md
    man = json.loads((REPO / f"builds/{m['build']}/MANIFEST.json").read_text(encoding="utf-8"))["languages"]["cbt_Latn"]
    assert f"{man['counts']['pairs']:,} human Shawi translations" in md
    health = sum(man["counts"]["chunks_translated_by_domain"].get(d, 0) for d in ("salud_cuerpo", "puente_civico"))
    assert f"{health:,} of the {man['counts']['pairs']:,} pairs" in md
    assert "99.99%" in md and "86%" in md and "NEEDS.md" in md and "Recordings" in md
    assert "Spanish → Shawi" in md and "Shawi → English" in md


def test_the_page_starts_the_glimmer_server_only_when_it_is_needed(fixture_root, monkeypatch):
    import atexit
    import signal

    import app

    import uyari.serve as serve

    started = []
    monkeypatch.setattr(serve, "start", lambda paths, **kw: started.append(kw) or {"ready": True})
    monkeypatch.setattr(atexit, "register", lambda *a: None)  # the page stops a server it started on exit
    monkeypatch.setattr(signal, "signal", lambda *a: None)
    monkeypatch.setattr(serve, "default_adapters", lambda paths: [])
    assert app.ensure_glimmer_server(fixture_root) is None and started == []  # no Glimmer registered
    monkeypatch.setattr(serve, "default_adapters", lambda paths: ["mt-cbt=/models/x/adapter"])
    monkeypatch.setattr(app, "_served", lambda: True)
    assert app.ensure_glimmer_server(fixture_root) is None and started == []  # already answering
    monkeypatch.setattr(app, "_served", lambda: False)
    assert app.ensure_glimmer_server(fixture_root) is None and len(started) == 1  # started here

    def fail(paths, **kw):
        raise RuntimeError("no GGUF")

    monkeypatch.setattr(serve, "start", fail)
    assert "no GGUF" in app.ensure_glimmer_server(fixture_root)  # the page says why Glimmer is missing
