from datetime import date

from uyari.build import read_table, run_build


def test_build_is_reproducible(fixture_root):
    a = run_build(fixture_root, "data-2026.10", as_of=date(2026, 11, 2))
    first = a.manifest["languages"]["qaa_Latn"]["tables"]
    b = run_build(fixture_root, "data-2026.10", as_of=date(2026, 11, 2))
    second = b.manifest["languages"]["qaa_Latn"]["tables"]
    for t in ("mt", "asr", "tts"):
        assert first[t]["content_sha256"] == second[t]["content_sha256"]
        assert first[t]["sha256"] == second[t]["sha256"]
    assert run_build(fixture_root, "data-2026.10", as_of=date(2026, 11, 2), verify=True).ok


def test_test_rows_only_in_test_files(fixture_root):
    run_build(fixture_root, "data-2026.10", as_of=date(2026, 11, 2))
    for task in ("mt", "asr", "tts"):
        assert all(r["split"] != "test" for r in read_table(fixture_root, "data-2026.10", "qaa_Latn", task))
        assert all(r["split"] == "test" for r in read_table(fixture_root, "data-2026.10", "qaa_Latn", task, test=True))


def test_replaces_audio_resolution_and_tts_read_only(fixture_root):
    res = run_build(fixture_root, "data-2026.10", as_of=date(2026, 11, 2))
    lm = res.manifest["languages"]["qaa_Latn"]
    assert lm["rows_excluded"].get("replaced") == 1
    asr = read_table(fixture_root, "data-2026.10", "qaa_Latn", "asr") + \
        read_table(fixture_root, "data-2026.10", "qaa_Latn", "asr", test=True)
    assert len(asr) == 4 and all(r["transcript"] for r in asr)
    assert lm["counts"]["read_clips"] == 3


def test_takedown_excludes_contribution(fixture_root):
    tk = fixture_root.data / "contributing/takedowns.csv"
    with tk.open("a", encoding="utf-8", newline="") as f:
        f.write("2026-10_fixture_0001,steward,2026-11-01,2026-11-01,contribution,test\n")
    before = run_build(fixture_root, "data-2026.10", as_of=date(2026, 10, 31), dry_run=True)
    after = run_build(fixture_root, "data-2026.10", as_of=date(2026, 11, 2), dry_run=True)
    assert before.manifest["languages"]["qaa_Latn"]["counts"]["pairs"] > 1
    excl = after.manifest["languages"]["qaa_Latn"]["contributions"]["excluded"]
    assert excl and excl[0]["id"] == "2026-10_fixture_0001"
    assert after.manifest["languages"]["qaa_Latn"]["counts"]["clips"] == 0


def test_officials_limits_the_languages_paired_and_keeps_the_hash(fixture_root):
    import shutil

    import pytest

    as_of = date(2026, 11, 2)
    before = run_build(fixture_root, "t", as_of=as_of, dry_run=True).manifest["languages"]["qaa_Latn"]
    extra = fixture_root.primary_dir("fra_Latn") / "chunks" / "translated"
    extra.mkdir(parents=True)
    shutil.copy(fixture_root.primary_dir("spa_Latn") / "chunks/generated/fixture.csv", extra / "fixture.csv")

    every = run_build(fixture_root, "t", as_of=as_of, dry_run=True).manifest["languages"]["qaa_Latn"]
    assert every["officials"] == ["fra_Latn", "spa_Latn"]
    assert sum(every["tables"]["mt"]["rows"].values()) == 2 * sum(before["tables"]["mt"]["rows"].values())

    only = run_build(fixture_root, "t", as_of=as_of, dry_run=True, officials=["spa_Latn"]).manifest
    only = only["languages"]["qaa_Latn"]
    assert only["officials"] == ["spa_Latn"]
    for t in ("mt", "asr", "tts"):  # a new language folder does not change a build that leaves it out
        assert only["tables"][t]["content_sha256"] == before["tables"][t]["content_sha256"]
    with pytest.raises(ValueError, match="primary"):
        run_build(fixture_root, "t", as_of=as_of, dry_run=True, officials=["fra_Latn"])
    with pytest.raises(ValueError, match="no primary corpus"):
        run_build(fixture_root, "t", as_of=as_of, dry_run=True, officials=["spa_Latn", "xxx_Latn"])
