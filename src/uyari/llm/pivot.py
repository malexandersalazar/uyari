"""One official-language sentence into another with Muse Spark (the demo: English -> Spanish).

Used by the demo's English voice input while no English -> Shawi model is registered: the English is put
into Spanish here, and our own model takes the Spanish into Shawi. Official-language text only
(``data_class="official"``, enforced by ``llm/policy.py``); Shawi never comes here. Paid with the caller's
own key (bring your own key): the server's key is never used and nothing is written to the ledger.
Same instructions and output schema as ``uyari primary translate``.
"""

from __future__ import annotations

import json

from uyari.gen.translate_primary import NAMES, SCHEMA, system_prompt
from uyari.llm.client import LLMClient, LLMError
from uyari.paths import Paths


def translate_official(paths: Paths, text: str, src: str, tgt: str, api_key: str, model: str | None = None,
                       timeout: float = 60.0) -> dict:
    """``{"text", "model", "cost_usd"}``. Raises ``LLMError`` on a failed or malformed answer."""
    if src not in NAMES or tgt not in NAMES:
        raise ValueError(f"official languages only ({sorted(NAMES)}), not {src} -> {tgt}")
    client = LLMClient(paths, model, "official", command="demo-pivot", api_key=api_key)
    prompt = json.dumps({"items": [{"id": "1", "text": text}]}, ensure_ascii=False)
    r = client.respond(system_prompt(src, tgt), prompt, schema=SCHEMA, max_output_tokens=1024, timeout=timeout,
                       max_retries=1)
    try:
        out = json.loads(r.text)["items"][0]["text"].strip()
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise LLMError(f"unexpected answer from {client.spec.key}: {r.text[:200]}") from e
    if not out:
        raise LLMError(f"{client.spec.key} returned an empty translation")
    return {"text": out, "model": client.spec.key, "cost_usd": r.cost_usd}
