from typer.testing import CliRunner

from uyari.cli import app


def test_validate_and_build_via_cli(fixture_root):
    r = CliRunner()
    res = r.invoke(app, ["validate", "--root", str(fixture_root.data)])
    assert res.exit_code == 0, res.output
    res = r.invoke(app, ["build", "--tag", "data-2026.10", "--as-of", "2026-11-02", "--root", str(fixture_root.data)])
    assert res.exit_code == 0, res.output
    res = r.invoke(app, ["build", "--tag", "data-2026.10", "--as-of", "2026-11-02", "--verify",
                         "--root", str(fixture_root.data)])
    assert res.exit_code == 0, res.output
