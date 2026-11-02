"""``config/llm.yaml``: model catalog, prices, budget and estimate settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from uyari.csvio import read_yaml
from uyari.paths import Paths


@dataclass
class ModelSpec:
    key: str
    provider: str
    api: str
    data_policy: str
    model_id: str = ""
    url_env: str = ""
    default_url: str = ""
    key_env: str = ""
    model_id_env: str = ""
    price_input: float = 0.0
    price_cached: float = 0.0
    price_output: float = 0.0
    price_audio_hour: float = 0.0
    batch_discount: float = 0.0
    request_defaults: dict = field(default_factory=dict)

    @property
    def url(self) -> str:
        return os.environ.get(self.url_env, "") or self.default_url

    @property
    def api_key(self) -> str:
        return os.environ.get(self.key_env, "") if self.key_env else ""

    @property
    def resolved_model_id(self) -> str:
        return os.environ.get(self.model_id_env, "") or self.model_id if self.model_id_env else self.model_id

    def cost(self, input_tokens: int = 0, cached_tokens: int = 0, output_tokens: int = 0) -> float:
        """USD. ``input_tokens`` includes the cached ones (as the APIs report them)."""
        uncached = max(0, input_tokens - cached_tokens)
        return (uncached * self.price_input + cached_tokens * self.price_cached
                + output_tokens * self.price_output) / 1_000_000

    def audio_cost(self, seconds: float) -> float:
        return seconds / 3600 * self.price_audio_hour


@dataclass
class Catalog:
    models: dict[str, ModelSpec]
    budget: dict
    estimate: dict
    defaults: dict

    def get(self, key: str | None, data_class: str = "official") -> ModelSpec:
        key = key or self.defaults.get(data_class)
        if key not in self.models:
            raise KeyError(f"model '{key}' not in config/llm.yaml ({sorted(self.models)})")
        return self.models[key]

    def run_cap(self, command: str) -> float:
        caps = self.budget.get("per_run_max_usd") or {}
        return float(caps.get(command, caps.get("default", 0.0)))

    @property
    def total_usd(self) -> float:
        return float(self.budget.get("total_usd", 0.0))


def load_catalog(paths: Paths) -> Catalog:
    cfg = read_yaml(paths.config / "llm.yaml")
    models = {}
    for k, m in (cfg.get("models") or {}).items():
        p = m.get("price_per_mtok") or {}
        models[k] = ModelSpec(
            key=k, provider=m.get("provider", ""), api=m.get("api", ""), data_policy=m.get("data_policy", "none"),
            model_id=m.get("model_id", k), url_env=m.get("url_env", ""), default_url=m.get("default_url", ""),
            key_env=m.get("key_env", ""), model_id_env=m.get("model_id_env", ""),
            price_input=float(p.get("input", 0) or 0), price_cached=float(p.get("cached_input", 0) or 0),
            price_output=float(p.get("output", 0) or 0),
            price_audio_hour=float(m.get("price_per_audio_hour", 0) or 0),
            batch_discount=float(m.get("batch_discount", 0) or 0),
            request_defaults=dict(m.get("request_defaults") or {}))
    return Catalog(models=models, budget=cfg.get("budget") or {}, estimate=cfg.get("estimate") or {},
                   defaults=cfg.get("defaults") or {})
