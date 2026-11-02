"""Spend ledger (``.uyari/ledger.jsonl``) and budget caps.

Every real API call appends one line with the provider's reported usage and its exact cost.
Before a run: cumulative spend + the run's estimate must fit the remaining total budget and
the run cap. During a run: a request whose expected cost would cross the cap is not sent.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from uyari.csvio import append_jsonl, read_jsonl
from uyari.llm.catalog import load_catalog
from uyari.paths import Paths


class BudgetExceeded(RuntimeError):
    pass


class Ledger:
    _lock = threading.Lock()

    def __init__(self, paths: Paths):
        self.paths = paths
        self.path = paths.state / "ledger.jsonl"
        self.catalog = load_catalog(paths)

    def entries(self) -> list[dict]:
        return read_jsonl(self.path)

    def spent(self, run_id: str | None = None, batch: str | None = None) -> float:
        total = 0.0
        for e in self.entries():
            if run_id and e.get("run_id") != run_id:
                continue
            if batch and e.get("batch") != batch:
                continue
            total += float(e.get("cost_usd", 0))
        return total

    def record(self, **entry) -> None:
        entry = {"at": datetime.now(UTC).isoformat(timespec="seconds"), **entry}
        with self._lock:
            append_jsonl(self.path, entry)

    def summary(self) -> dict:
        by_model, by_cmd = defaultdict(float), defaultdict(float)
        n = 0
        for e in self.entries():
            by_model[e.get("model", "?")] += float(e.get("cost_usd", 0))
            by_cmd[e.get("command", "?")] += float(e.get("cost_usd", 0))
            n += 1
        total = sum(by_model.values())
        return {"calls": n, "spent_usd": round(total, 6), "budget_usd": self.catalog.total_usd,
                "remaining_usd": round(self.catalog.total_usd - total, 6),
                "by_model": {k: round(v, 6) for k, v in by_model.items()},
                "by_command": {k: round(v, 6) for k, v in by_cmd.items()}}


@dataclass
class RunBudget:
    """The cap for one command run, enforced before every request."""

    ledger: Ledger
    run_id: str
    cap_usd: float
    spent_usd: float = 0.0

    def __post_init__(self):
        self._lock = threading.Lock()
        self.reserved_usd = 0.0  # expected cost of requests in flight
        self._remaining0 = self.ledger.catalog.total_usd - self.ledger.spent()

    @property
    def remaining_total(self) -> float:
        return self._remaining0 - self.spent_usd

    def check_plan(self, expected_usd: float) -> None:
        if expected_usd > self.cap_usd:
            raise BudgetExceeded(f"estimate ${expected_usd:.4f} exceeds this run's cap ${self.cap_usd:.2f} "
                                 "(raise it with --max-usd, or --limit the run)")
        if expected_usd > self.remaining_total:
            raise BudgetExceeded(f"estimate ${expected_usd:.4f} exceeds the remaining project budget "
                                 f"${self.remaining_total:.2f}")

    def reserve(self, expected_usd: float) -> bool:
        """Hold ``expected_usd`` for a request about to be sent; False if it would cross a cap.
        Requests in flight count against the cap, so concurrency cannot overshoot it."""
        with self._lock:
            committed = self.spent_usd + self.reserved_usd + expected_usd
            if committed > self.cap_usd or committed > self._remaining0:
                return False
            self.reserved_usd += expected_usd
            return True

    def charge(self, cost_usd: float, reserved_usd: float = 0.0) -> None:
        """Settle a request: release its reservation, record its real cost."""
        with self._lock:
            self.reserved_usd = max(0.0, self.reserved_usd - reserved_usd)
            self.spent_usd += cost_usd

    def release(self, reserved_usd: float) -> None:
        with self._lock:
            self.reserved_usd = max(0.0, self.reserved_usd - reserved_usd)
