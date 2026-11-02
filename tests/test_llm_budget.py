import pytest

from uyari.llm import policy
from uyari.llm.catalog import load_catalog
from uyari.llm.client import LLMClient
from uyari.llm.ledger import BudgetExceeded, Ledger, RunBudget


def test_cost_arithmetic(fixture_root):
    spec = load_catalog(fixture_root).models["muse-spark-1.3-contributor"]
    # 1M input of which 400k cached, 1M output: 0.6*0.10 + 0.4*0.002 + 1*0.20
    assert spec.cost(1_000_000, 400_000, 1_000_000) == pytest.approx(0.06 + 0.0008 + 0.20)
    voice = load_catalog(fixture_root).models["muse-voice-transcribe"]
    assert voice.audio_cost(1800) == pytest.approx(0.09)


def test_cap_refuses_and_reserve(fixture_root):
    b = RunBudget(Ledger(fixture_root), "run1", cap_usd=0.05)
    with pytest.raises(BudgetExceeded):
        b.check_plan(0.06)
    assert b.reserve(0.03)
    assert not b.reserve(0.03), "an in-flight reservation must count against the cap"
    b.charge(0.01, reserved_usd=0.03)  # settled cheaper than expected: room frees up
    assert b.reserve(0.03)
    b.release(0.03)
    assert b.spent_usd == pytest.approx(0.01) and b.reserved_usd == pytest.approx(0.0)


def test_total_budget_counts_ledger(fixture_root):
    led = Ledger(fixture_root)
    led.record(run_id="x", command="generate", model="m", cost_usd=149.99)
    b = RunBudget(led, "run2", cap_usd=5.0)
    with pytest.raises(BudgetExceeded):
        b.check_plan(0.05)
    assert led.summary()["remaining_usd"] == pytest.approx(0.01)


def test_policy_refuses_shawi_to_contributor_tier(fixture_root, monkeypatch):
    cat = load_catalog(fixture_root)
    with pytest.raises(policy.PolicyError):
        policy.check(cat.models["muse-spark-1.3-contributor"], "community")
    with pytest.raises(policy.PolicyError):
        policy.check(cat.models["claude-opus-4-8"], "official")
    policy.check(cat.models["glimmer-local"], "community")
    monkeypatch.setenv("META_API_KEY", "x")
    with pytest.raises(policy.PolicyError):
        LLMClient(fixture_root, "muse-spark-1.3-contributor", "community", "gatekeeper")


def test_defaults_route_community_to_local(fixture_root):
    cat = load_catalog(fixture_root)
    assert cat.get(None, "community").key == "glimmer-local"
    assert cat.get(None, "official").key == "muse-spark-1.3-contributor"
