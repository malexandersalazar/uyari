from uyari.privacy import run_privacy_check


def _private(fixture_root, names):
    fixture_root.private.mkdir(parents=True, exist_ok=True)
    (fixture_root.private / "privacy_names.txt").write_text("\n".join(names) + "\n", encoding="utf-8")


def test_finds_planted_name_and_respects_credits_allowlist(fixture_root):
    _private(fixture_root, ["Zacarias Quispecondori"])
    (fixture_root.data / "notes.md").write_text("Traducido por Quispecondori.\n", encoding="utf-8")
    res = run_privacy_check(fixture_root)
    assert not res.ok and "notes.md" in res.findings[0]
    (fixture_root.data / "notes.md").unlink()
    (fixture_root.data / "CREDITS.md").write_text("Zacarias Quispecondori\n", encoding="utf-8")
    (fixture_root.private / "credits_allowlist.txt").write_text("Zacarias Quispecondori\nZacarias\nQuispecondori\n",
                                                                 encoding="utf-8")
    assert run_privacy_check(fixture_root).ok


def test_skipped_without_private_list(fixture_root):
    res = run_privacy_check(fixture_root)
    assert res.ok and "skipped" in res.summary


def test_repository_is_clean(real):
    res = run_privacy_check(real)
    assert res.ok, res.findings[:10]
