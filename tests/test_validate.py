import csv

import yaml

from uyari.validate import run_validate


def _codes(rep):
    return {i.code for i in rep.errors}


def test_fixture_is_valid(fixture_root):
    rep = run_validate(fixture_root, strict=True)
    assert rep.ok, [i.__dict__ for i in rep.errors]
    assert rep.counts["clips"] == 4


def test_rejections(fixture_root):
    d = fixture_root.data / "languages/qaa_Latn/contributions/2026-11_fixture_0002"
    with (d / "pairs.csv").open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["f" * 32, "kunuwa", "", "t-0002", ""])          # unknown chunk
        w.writerow(["0300" + "a" * 28, "wa'kirawe", "", "t-0002", ""])  # ASCII apostrophe
    meta = yaml.safe_load((d / "contribution.yaml").read_text(encoding="utf-8"))
    meta["license"] = "all-rights-reserved"
    (d / "contribution.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")
    rep = run_validate(fixture_root)
    assert {"unknown_chunk", "apostrophe", "schema"} <= _codes(rep)


def test_todo_blocks_only_under_strict(fixture_root):
    d = fixture_root.data / "languages/qaa_Latn/contributions/2026-11_fixture_0002"
    meta = yaml.safe_load((d / "contribution.yaml").read_text(encoding="utf-8"))
    meta["license"] = "TODO"
    (d / "contribution.yaml").write_text(yaml.safe_dump(meta), encoding="utf-8")
    assert run_validate(fixture_root).ok
    assert not run_validate(fixture_root, strict=True).ok


def test_audio_checks(fixture_root):
    import numpy as np
    import soundfile as sf

    wav = fixture_root.data / "languages/qaa_Latn/contributions/2026-10_fixture_0001/wav/clip_001.wav"
    sf.write(str(wav), np.zeros(16000 * 3, dtype="float32"), 16000, subtype="PCM_16")  # silent: peak and silence fail
    codes = _codes(run_validate(fixture_root))
    assert {"audio_peak", "audio_silence"} <= codes


def test_real_data_has_no_errors(real):
    assert run_validate(real).ok
