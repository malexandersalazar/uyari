"""The Shawi voice: spelling converter, cutting and pauses, the seed, letters left out, the audio cache, and
coverage measured after conversion. No network: the voice is a fake; the rules are the real tts.yaml."""

from __future__ import annotations

import dataclasses
import logging
import unicodedata

import numpy as np
import pytest

from conftest import REPO
from uyari.paths import Paths
from uyari.pipelines.tts import check_voice as CV
from uyari.pipelines.tts import voice as V
from uyari.pipelines.tts.voice import MmsVoice, load_config, parse_config, reading, speak

# facebook/mms-tts-cbt's single-letter vocabulary (no k, w, ñ, ʼ, ’; it has the saltillo ꞌ and the straight ').
MMS_CBT = frozenset("an|ioëthuꞌprcsyqm'áí—ódle\u0301fb ")


class FakeVoice:
    sampling_rate = 100  # one sample = 10 ms, so pauses are easy to count
    letters = MMS_CBT

    def __init__(self):
        self.calls = []

    def say(self, text, seed):
        self.calls.append((text, seed))
        return np.ones(len(text), dtype=np.float32)  # one sample per letter read


@pytest.fixture()
def cfg():
    return load_config(Paths(code=REPO, data=REPO), "cbt_Latn")


@pytest.fixture(autouse=True)
def _empty_audio_cache():
    V._audio.clear()
    yield
    V._audio.clear()


def test_rules_in_order_after_lowercase_and_nfc(cfg):
    assert cfg.voice == "facebook/mms-tts-cbt" and cfg.seed == 7
    assert cfg.convert("Kenka kiwi") == "quenca quihui"  # k before e/i -> qu, any other k -> c, w -> hu
    assert cfg.convert("Ipiʼ ipi' ipi’") == "ipiꞌ ipiꞌ ipiꞌ"
    assert cfg.convert("Ñaña") == "nyanya"
    assert cfg.convert(unicodedata.normalize("NFD", "KÁWA")) == "cáhua"  # composed again (NFC), lowercased
    # Order matters: with the plain k -> c first, "ke" would become "ce" (read /se/).
    wrong_order = parse_config({"rules": [{"find": "k", "write": "c"},
                                          {"find": "k", "before": ["e", "i"], "write": "qu"}]}, "x")
    assert wrong_order.convert("ke") == "ce"
    # Everything a Shawi sentence is made of is now in the voice's alphabet.
    said = cfg.convert("Ina nuʼwiterinkeran ñaña kenkawe")
    assert set(said) <= MMS_CBT, set(said) - MMS_CBT


def test_cut_at_punctuation_with_pauses(cfg):
    assert cfg.pieces("Ipiʼ, ¿kenka? Wa.") == [("ipiꞌ", 0.15), ("", 0.15), ("quenca", 0.35), ("hua", 0.35)]
    v = FakeVoice()
    sr, wav = speak(cfg, "Ipiʼ, ¿kenka? Wa.", v)
    assert [t for t, _ in v.calls] == ["ipiꞌ", "quenca", "hua"]
    silence = lambda s: [0.0] * round(s * sr)  # noqa: E731
    expected = [1.0] * 4 + silence(0.15) + [1.0] * 6 + silence(0.35) + [1.0] * 3  # no pause after the last piece
    assert wav.tolist() == expected
    # Marks together: the longest pause wins ("." then "¿" is a sentence pause, not two).
    v = FakeVoice()
    sr, wav = speak(cfg, "Ipi. ¿Ipi?", v)
    assert wav.tolist() == [1.0] * 3 + silence(0.35) + [1.0] * 3
    assert speak(cfg, "¿?", FakeVoice())[1].size == 0  # nothing to read is not an error


def test_seed_on_every_piece(cfg):
    v = FakeVoice()
    speak(cfg, "Ipi, ipi; ipi: ipi! Ipi.", v)
    assert len(v.calls) == 5 and {seed for _, seed in v.calls} == {7}


def test_real_voice_sets_the_seed_before_each_forward_without_touching_global_rng(monkeypatch):
    torch = pytest.importorskip("torch")

    class Tok:
        def get_vocab(self):
            return {c: i for i, c in enumerate(sorted(MMS_CBT))}

        def __call__(self, text, return_tensors):
            return {"input_ids": torch.zeros(1, len(text), dtype=torch.long)}

    class Model:
        config = type("C", (), {"sampling_rate": 16000})()

        def __call__(self, input_ids):  # VITS samples noise: the output depends on the seed
            return type("O", (), {"waveform": torch.randn(1, input_ids.shape[1] * 10)})()

    seeds = []
    real_seed = torch.manual_seed
    monkeypatch.setattr(torch, "manual_seed", lambda s: seeds.append(s) or real_seed(s))
    voice = MmsVoice(Tok(), Model())
    torch.manual_seed(123)
    seeds.clear()
    state = torch.get_rng_state()
    a, b = voice.say("ipi", 7), voice.say("ipi", 7)
    assert seeds == [7, 7] and np.array_equal(a, b)
    assert torch.equal(torch.get_rng_state(), state), "the caller's random state must not change"


def test_letters_the_voice_cannot_read_are_logged_not_raised(cfg, caplog):
    v = FakeVoice()
    with caplog.at_level(logging.WARNING, logger="uyari.tts"):
        sr, wav = speak(cfg, "Vamos con José.", v)
    assert wav.size > 0 and v.calls == [("amos con os", 7)]
    msg = caplog.text
    assert "cannot read" in msg and "v x1" in msg and "j x1" in msg and "é x1" in msg
    assert reading("vamos con josé", MMS_CBT) == "amos con os"


def test_audio_is_cached_by_text_and_rules(cfg):
    v = FakeVoice()
    first = speak(cfg, "Ipiʼ.", v)
    assert speak(cfg, "Ipiʼ.", v) is first and len(v.calls) == 1
    speak(dataclasses.replace(cfg, rules=cfg.rules[:1]), "Ipiʼ.", v)  # other rules: made again
    speak(cfg, "Ipiʼ!", v)  # other text: made again
    assert len(v.calls) == 3
    assert not first[1].flags.writeable


def test_tts_yaml_typos_are_refused():
    with pytest.raises(ValueError, match="unknown key"):
        parse_config({"rule": []}, "x")
    with pytest.raises(ValueError, match="find and write"):
        parse_config({"rules": [{"find": "k", "to": "c"}]}, "x")


def test_check_voice_measures_coverage_after_conversion(cfg, monkeypatch):
    import huggingface_hub

    info = type("I", (), {"card_data": {"license": "cc-by-nc-4.0"}})()
    monkeypatch.setattr(huggingface_hub, "model_info", lambda repo: info)
    monkeypatch.setattr(CV, "alphabet", lambda repo: MMS_CBT)
    texts = ["Kenka kiwi ipiʼ ñaña", "Nuʼwiterinkeran ina"]
    raw = CV.check_voice("cbt", texts)
    assert raw["usable"] is False and raw["letter_coverage"] < 0.9 and {"k", "w", "ʼ", "ñ"} <= set(raw["missing_letters"])
    res = CV.check_voice("cbt", texts, cfg)
    assert res["usable"] is True and res["letter_coverage"] == 1.0 and res["missing_letters"] == {}
    assert res["before_conversion"]["letter_coverage"] == raw["letter_coverage"]
    assert res["converter"] == "languages/cbt_Latn/tts.yaml"
