from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests" / "fixtures"))

from make_fixture import make_root  # noqa: E402

from uyari.paths import Paths  # noqa: E402


@pytest.fixture()
def fixture_root(tmp_path, monkeypatch) -> Paths:
    monkeypatch.delenv("UYARI_PRIVATE_DIR", raising=False)  # the fixture's private dir is <root>/.private
    root = make_root(tmp_path / "root")
    return Paths(code=REPO, data=root)


@pytest.fixture()
def real() -> Paths:
    p = Paths(code=REPO, data=REPO)
    if not (REPO / "primary/spa_Latn/chunks/generated/2026-06_opus48_0001.csv").is_file():
        pytest.skip("real primary corpus not present")
    return p
