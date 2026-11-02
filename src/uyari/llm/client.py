"""One client for the Meta Responses API and local OpenAI-compatible chat servers.

Every call goes through the data-policy guard and the spend ledger. The Responses API shape:

    POST $META_API_URL  {model, instructions, input, max_output_tokens,
                         text: {format: {type: json_schema, ...}}, reasoning: {effort}}
    -> {output_text | output[].content[].text, usage: {input_tokens, output_tokens,
        input_tokens_details.cached_tokens, output_tokens_details.reasoning_tokens}}

Optional parameters the server rejects (400 naming them) are dropped once and remembered in
``.uyari/api_compat.json``; ``uyari llm ping`` shows what was accepted.
"""

from __future__ import annotations

import json
import random
import sys
import time
import uuid
from dataclasses import dataclass, field

import httpx

from uyari.csvio import write_json
from uyari.llm import policy
from uyari.llm.catalog import ModelSpec, load_catalog
from uyari.llm.ledger import Ledger, RunBudget
from uyari.llm.tokens import count
from uyari.paths import Paths

RETRY_STATUS = {408, 409, 429, 500, 502, 503, 504}


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    request_id: str = ""
    raw: dict = field(default_factory=dict)


def confirm(question: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    if not sys.stdin or not sys.stdin.isatty():
        print(f"{question} -> not confirmed (non-interactive; pass --yes)")
        return False
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes", "s", "si", "sí")


def _extract_text(data: dict) -> str:
    if isinstance(data.get("output_text"), str) and data["output_text"]:
        return data["output_text"]
    parts = []
    for item in data.get("output") or []:
        for c in item.get("content") or []:
            if c.get("type") in ("output_text", "text") and c.get("text"):
                parts.append(c["text"])
    if parts:
        return "".join(parts)
    ch = data.get("choices")
    if ch:
        return ch[0].get("message", {}).get("content") or ""
    return ""


def _usage(data: dict) -> tuple[int, int, int, int]:
    u = data.get("usage") or {}
    inp = int(u.get("input_tokens", u.get("prompt_tokens", 0)) or 0)
    out = int(u.get("output_tokens", u.get("completion_tokens", 0)) or 0)
    cached = int((u.get("input_tokens_details") or u.get("prompt_tokens_details") or {}).get("cached_tokens", 0) or 0)
    reasoning = int((u.get("output_tokens_details") or u.get("completion_tokens_details") or {}).get(
        "reasoning_tokens", 0) or 0)
    return inp, cached, out, reasoning


class LLMClient:
    def __init__(self, paths: Paths, model: str | None, data_class: str, command: str,
                 budget: RunBudget | None = None, batch: str = ""):
        self.paths = paths
        self.catalog = load_catalog(paths)
        self.spec: ModelSpec = self.catalog.get(model, data_class)
        policy.check(self.spec, data_class)
        self.data_class, self.command, self.batch = data_class, command, batch
        self.ledger = Ledger(paths)
        self.run_id = budget.run_id if budget else uuid.uuid4().hex[:12]
        self.budget = budget
        self._compat_path = paths.state / "api_compat.json"
        self._compat = json.loads(self._compat_path.read_text(encoding="utf-8")) if self._compat_path.is_file() else {}
        if self.spec.api in ("responses",) and not self.spec.api_key:
            raise LLMError(f"{self.spec.key_env} is not set (see .env.example)")
        if not self.spec.url:
            raise LLMError(f"{self.spec.url_env} is not set")

    # ---------------------------------------------------------------- estimates
    def estimate_cost(self, instructions: str, prompt: str, expected_output_tokens: int) -> float:
        f = float(self.catalog.estimate.get("input_safety_factor", 1.2))
        inp = int((count(instructions) + count(prompt)) * f)
        return self.spec.cost(inp, 0, expected_output_tokens)

    # ---------------------------------------------------------------- requests
    def _body(self, instructions: str, prompt: str, schema: dict | None, max_output_tokens: int,
              temperature: float | None) -> dict:
        skip = set(self._compat.get(self.spec.key, {}).get("drop", []))
        if self.spec.api == "responses":
            body = {"model": self.spec.resolved_model_id, "instructions": instructions, "input": prompt,
                    "max_output_tokens": max_output_tokens}
            if schema is not None and "text.format" not in skip:
                body["text"] = {"format": {"type": "json_schema", "name": "output", "schema": schema,
                                           "strict": True}}
            for k, v in self.spec.request_defaults.items():
                if k not in skip:
                    body[k] = v
            if temperature is not None and "temperature" not in skip:
                body["temperature"] = temperature
            return body
        body = {"model": self.spec.resolved_model_id, "max_tokens": max_output_tokens,
                "messages": [{"role": "system", "content": instructions}, {"role": "user", "content": prompt}]}
        for k, v in self.spec.request_defaults.items():  # e.g. chat_template_kwargs for the local server
            if k not in skip:
                body[k] = v
        if temperature is not None:
            body["temperature"] = temperature
        if schema is not None and "response_format" not in skip:
            body["response_format"] = {"type": "json_schema", "json_schema": {"name": "output", "schema": schema}}
        return body

    def _remember_drop(self, param: str) -> None:
        self._compat.setdefault(self.spec.key, {}).setdefault("drop", [])
        if param not in self._compat[self.spec.key]["drop"]:
            self._compat[self.spec.key]["drop"].append(param)
            write_json(self._compat_path, self._compat)

    def respond(self, instructions: str, prompt: str, schema: dict | None = None, max_output_tokens: int = 4096,
                temperature: float | None = None, expected_cost: float = 0.0, meta: dict | None = None,
                timeout: float = 300.0, max_retries: int = 5) -> LLMResponse:
        if self.budget and not self.budget.reserve(expected_cost):
            raise LLMError(f"run cap ${self.budget.cap_usd:.2f} reached (spent ${self.budget.spent_usd:.4f})")
        try:
            return self._respond(instructions, prompt, schema, max_output_tokens, temperature, expected_cost, meta,
                                 timeout, max_retries)
        except BaseException:
            if self.budget:
                self.budget.release(expected_cost)
            raise

    def _respond(self, instructions, prompt, schema, max_output_tokens, temperature, expected_cost, meta,
                 timeout, max_retries) -> LLMResponse:
        headers = {"Content-Type": "application/json"}
        if self.spec.api_key:
            headers["Authorization"] = f"Bearer {self.spec.api_key}"
        attempt, dropped = 0, 0
        while True:
            body = self._body(instructions, prompt, schema, max_output_tokens, temperature)
            t0 = time.time()
            try:
                r = httpx.post(self.spec.url, headers=headers, json=body, timeout=timeout)
            except httpx.HTTPError as e:
                if attempt < max_retries:
                    attempt += 1
                    time.sleep(min(60, 2 ** attempt + random.random()))
                    continue
                raise LLMError(f"network error after {attempt} retries: {e}") from e
            if r.status_code in RETRY_STATUS and attempt < max_retries:
                attempt += 1
                wait = float(r.headers.get("retry-after", 0) or 0) or min(60, 2 ** attempt + random.random())
                time.sleep(wait)
                continue
            if r.status_code == 400 and dropped < 3:
                msg = r.text.lower()
                for param, needle in (("reasoning", "reasoning"), ("text.format", "format"),
                                      ("temperature", "temperature"), ("response_format", "response_format")):
                    if needle in msg and param not in self._compat.get(self.spec.key, {}).get("drop", []):
                        self._remember_drop(param)
                        dropped += 1
                        break
                else:
                    raise LLMError(f"HTTP 400: {r.text[:500]}")
                continue
            if r.status_code >= 400:
                raise LLMError(f"HTTP {r.status_code}: {r.text[:500]}")
            data = r.json()
            inp, cached, out, reasoning = _usage(data)
            cost = self.spec.cost(inp, cached, out)
            resp = LLMResponse(text=_extract_text(data), input_tokens=inp, cached_tokens=cached, output_tokens=out,
                               reasoning_tokens=reasoning, cost_usd=cost, latency_s=round(time.time() - t0, 2),
                               request_id=r.headers.get("x-request-id", "") or str(data.get("id", "")), raw=data)
            if self.budget:
                self.budget.charge(cost, reserved_usd=expected_cost)
            self.ledger.record(run_id=self.run_id, command=self.command, model=self.spec.key, batch=self.batch,
                               data_class=self.data_class, input_tokens=inp, cached_tokens=cached,
                               output_tokens=out, reasoning_tokens=reasoning, cost_usd=round(cost, 8),
                               request_id=resp.request_id, latency_s=resp.latency_s, **(meta or {}))
            return resp


def ping(paths: Paths, model: str | None = None, assume_yes: bool = False) -> dict:
    """One tiny call to confirm the endpoint, the response shape and the usage fields."""
    cat = load_catalog(paths)
    spec = cat.get(model, "official")
    instructions, prompt = "Responde solo con JSON.", 'Devuelve {"texts": ["listo"]}.'
    est = spec.cost(int((count(instructions) + count(prompt)) * 1.2) + 20, 0, 300)
    if not confirm(f"Ping {spec.key} at {spec.url} (about ${est:.6f})?", assume_yes):
        return {"sent": False, "estimate_usd": est}
    ledger = Ledger(paths)
    budget = RunBudget(ledger, uuid.uuid4().hex[:12], cap_usd=max(0.01, est * 10))
    cl = LLMClient(paths, spec.key, "official", "llm-ping", budget)
    from uyari.gen.prompts import TEXTS_SCHEMA

    r = cl.respond(instructions, prompt, schema=TEXTS_SCHEMA, max_output_tokens=300, expected_cost=est)
    return {"sent": True, "model": spec.key, "url": spec.url, "text": r.text[:200],
            "usage": {"input": r.input_tokens, "cached": r.cached_tokens, "output": r.output_tokens,
                      "reasoning": r.reasoning_tokens},
            "cost_usd": r.cost_usd, "latency_s": r.latency_s, "request_id": r.request_id,
            "response_keys": sorted(r.raw.keys()), "usage_raw": r.raw.get("usage"),
            "dropped_params": cl._compat.get(spec.key, {}).get("drop", [])}
