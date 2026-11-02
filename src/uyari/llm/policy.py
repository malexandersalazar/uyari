"""Data-policy guard: which data a model may see.

Every LLM call declares a ``data_class``:
  * ``official``  : official-language text only (synthetic Spanish, Spanish speech)
  * ``community`` : anything containing an Indigenous language or a community contribution

A model's ``data_policy`` (config/llm.yaml):
  * ``official_only`` : refuses ``community`` (the Muse Spark Contributor tier: Meta may train
                        on prompts and completions)
  * ``any``           : local models on our own hardware
  * ``none``          : never called (price references)
"""

from __future__ import annotations

from uyari.llm.catalog import ModelSpec

DATA_CLASSES = ("official", "community")


class PolicyError(PermissionError):
    pass


def check(spec: ModelSpec, data_class: str) -> None:
    if data_class not in DATA_CLASSES:
        raise PolicyError(f"unknown data_class {data_class!r}; use one of {DATA_CLASSES}")
    if spec.data_policy == "none":
        raise PolicyError(f"{spec.key} is a price reference only and is never called")
    if data_class == "community" and spec.data_policy != "any":
        raise PolicyError(
            f"{spec.key} has data_policy={spec.data_policy}: it must never see Indigenous-language or "
            "community data. Use a local model (glimmer-local).")
