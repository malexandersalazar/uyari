"""``uyari primary translate``: a second primary corpus, machine-translated from the first.

Every source chunk (Spanish) gets a twin in the target official language (English) with the **same
chunk_id**, so every human translation into an Indigenous language, made from the Spanish, also pairs
with the English. The new rows say ``origin=machine_translated`` and name the model that wrote them;
split, domain and paraphrase group are copied from the source chunk, so no test sentence leaks into
training through the second language.

Official-language text only (Spanish in, English out), so the Muse Spark Contributor tier is allowed.
Each request carries ``per_request`` sentences as JSON to amortize the instructions. Every raw response
is cached in ``runs/primary-translate/<batch>/responses.jsonl`` before it is parsed, chunks already in
the output file are skipped, so a re-run never pays twice. Rejected items are retried once, one per
request; what still fails is listed in ``failures.jsonl`` and left out.
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from uyari.csvio import append_jsonl, read_csv, read_jsonl
from uyari.data.contributions import load_contributions
from uyari.data.primary import load_primary, write_chunks
from uyari.llm.catalog import load_catalog
from uyari.llm.client import LLMClient, LLMError, confirm
from uyari.llm.ledger import Ledger, RunBudget
from uyari.llm.tokens import count
from uyari.paths import Paths
from uyari.text.normalize import normalize_official, word_count

NAMES = {"spa_Latn": "Spanish", "eng_Latn": "English", "por_Latn": "Portuguese", "fra_Latn": "French",
         "deu_Latn": "German", "ita_Latn": "Italian", "hin_Deva": "Hindi", "tha_Thai": "Thai"}
COPY = ("split", "domain_l1", "domain_l2", "register", "acto_comunicativo", "tiempo_aspecto", "polaridad",
        "persona_deixis", "length_bucket", "perfil_hablante", "tono_emocional", "discurso_conectado",
        "source_custom_id")
SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["items"],
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "additionalProperties": False, "required": ["id", "text"],
        "properties": {"id": {"type": "string"}, "text": {"type": "string"}}}}},
}
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
_SPANISH = {"el", "la", "los", "las", "de", "del", "que", "y", "en", "un", "una", "con", "por", "para", "es",
            "está", "no", "se", "mi", "su", "pero", "muy", "también", "cuando", "porque", "nosotros"}
_ENGLISH = {"the", "an", "of", "and", "to", "in", "is", "are", "was", "it", "we", "you", "i", "my", "our",
            "for", "with", "on", "at", "not", "do", "this", "that", "they", "he", "she", "will", "be", "have"}


def system_prompt(src: str, tgt: str) -> str:
    s, t = NAMES.get(src, src), NAMES.get(tgt, tgt)
    return (f"You translate {s} sentences into natural, faithful {t}. Keep the meaning, register, tense and "
            f"grammatical person. Do not add, explain or drop information; keep names, numbers and local words "
            f"(e.g. place or plant names) as they are. The sentences come from everyday life, health and public "
            f"services in rural Indigenous communities. Input: a JSON list of items with an id and a {s} text. "
            f'Output: JSON {{"items": [{{"id": ..., "text": ...}}]}} with exactly one item per input id, in order.')


def prompt_version(src: str, tgt: str) -> str:
    return "tv-" + hashlib.sha1(system_prompt(src, tgt).encode("utf-8")).hexdigest()[:12]


def run_dir(paths: Paths, batch: str):
    return paths.runs / "primary-translate" / batch


def out_file(paths: Paths, tgt: str, batch: str):
    return paths.primary_dir(tgt) / "chunks" / "translated" / f"{batch}.csv"


def translated_ids(paths: Paths, lang: str) -> set[str]:
    return {p["chunk_id"] for c in load_contributions(paths, lang) for p in c.pairs if p.get("chunk_id")}


def select_chunks(paths: Paths, src: str, only_translated_in: str | None = None, limit: int | None = None
                  ) -> list[dict]:
    pc = load_primary(paths, src)
    rows = [r for r in pc.chunks.values() if r.get("status") == "active"]
    if only_translated_in:
        keep = translated_ids(paths, only_translated_in)
        rows = [r for r in rows if r["chunk_id"] in keep]
    rows.sort(key=lambda r: r["chunk_id"])
    return rows[:limit] if limit else rows


def make_requests(rows: list[dict], per_request: int) -> list[dict]:
    out = []
    for i in range(0, len(rows), per_request):
        part = rows[i:i + per_request]
        rid = "tr-" + hashlib.md5("|".join(r["chunk_id"] for r in part).encode("utf-8")).hexdigest()[:12]
        out.append({"request_id": rid, "chunks": part})
    return out


def request_prompt(req: dict) -> str:
    return json.dumps([{"id": str(n), "text": r["text"]} for n, r in enumerate(req["chunks"], 1)],
                      ensure_ascii=False)


def expected_output_tokens(req: dict, est: dict) -> int:
    per = [count(r["text"]) + float(est.get("json_overhead_tokens_per_text", 8)) + 4 for r in req["chunks"]]
    return int(sum(per) + float(est.get("reasoning_allowance_tokens", 256)))


def estimate(paths: Paths, reqs: list[dict], model: str, src: str, tgt: str) -> dict:
    cat = load_catalog(paths)
    spec, est = cat.get(model, "official"), cat.estimate
    f = float(est.get("input_safety_factor", 1.2))
    sys_t = count(system_prompt(src, tgt))
    inp = [int((sys_t + count(request_prompt(r))) * f) for r in reqs]
    out = [expected_output_tokens(r, est) for r in reqs]
    exp = sum(spec.cost(i, 0, o) for i, o in zip(inp, out, strict=True))
    lo_m, hi_m = (est.get("low_high_band") or [0.7, 1.5])
    return {"model": spec.key, "requests": len(reqs), "sentences": sum(len(r["chunks"]) for r in reqs),
            "input_tokens": sum(inp), "output_tokens": sum(out), "expected_usd": round(exp, 6),
            "low_usd": round(exp * lo_m, 6), "high_usd": round(exp * hi_m, 6)}


def parse_items(text: str) -> dict[str, str]:
    """{id: text} from the last JSON object with an ``items`` list (tolerates code fences)."""
    for m in reversed(list(re.finditer(r"\{", text))):
        try:
            obj = json.loads(text[m.start():text.rfind("}") + 1])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("items"), list):
            return {str(i.get("id")): str(i.get("text", "")) for i in obj["items"] if isinstance(i, dict)}
    return {}


def check(src_text: str, out: str, tgt: str) -> str:
    """'' if acceptable, else the reason."""
    if not out.strip():
        return "empty"
    wc = word_count(out)
    if not 1 <= wc <= 150:
        return f"{wc} words"
    if normalize_official(out).casefold() == normalize_official(src_text).casefold() and wc > 2:
        return "unchanged"
    if tgt == "eng_Latn" and wc > 3:
        words = [w.casefold() for w in _WORD.findall(out)]
        es, en = sum(w in _SPANISH for w in words), sum(w in _ENGLISH for w in words)
        if es > en:
            return "looks like Spanish"
    return ""


def _row(src_row: dict, text: str, src: str, model: str, pv: str, today: str) -> dict:
    row = {k: src_row.get(k, "") for k in COPY}
    return {**row, "chunk_id": src_row["chunk_id"], "text": normalize_official(text), "origin": "machine_translated",
            "status": "active", "supersedes": "", "word_count": str(word_count(text)), "palabras_ancla": "",
            "source_batch_id": f"{src}:{src_row.get('source_batch_id', '')}".rstrip(":"), "regen_of": "",
            "gen_model": model, "provider": "meta", "gen_date": today, "prompt_version": pv}


def run_translate(paths: Paths, batch: str, src: str = "spa_Latn", tgt: str = "eng_Latn", model: str | None = None,
                  only_translated_in: str | None = None, limit: int | None = None, per_request: int = 20,
                  estimate_only: bool = False, max_usd: float | None = None, assume_yes: bool = False,
                  concurrency: int = 8, console=None) -> dict:
    cat = load_catalog(paths)
    model = cat.get(model, "official").key
    d, out_f = run_dir(paths, batch), out_file(paths, tgt, batch)
    done = {r["chunk_id"]: r for r in read_csv(out_f)} if out_f.is_file() else {}
    rows = [r for r in select_chunks(paths, src, only_translated_in, limit) if r["chunk_id"] not in done]
    cached = {r["request_id"]: r for r in read_jsonl(d / "responses.jsonl")}
    reqs = make_requests(rows, per_request)
    to_send = [r for r in reqs if r["request_id"] not in cached]
    e = estimate(paths, to_send, model, src, tgt)
    cap = max_usd if max_usd is not None else cat.run_cap("translate")
    ledger = Ledger(paths)
    remaining = cat.total_usd - ledger.spent()
    info = {"batch": batch, "already_done": len(done), "to_translate": len(rows), "cached_requests": len(reqs) -
            len(to_send), **e, "run_cap_usd": cap, "budget_remaining_usd": round(remaining, 4)}
    if console:
        console.print_json(json.dumps(info))
    if estimate_only or not rows:
        return info
    if e["high_usd"] > cap:
        raise LLMError(f"high estimate ${e['high_usd']:.4f} exceeds the run cap ${cap:.2f}; pass --max-usd")
    if to_send and not confirm(f"Translate {e['sentences']} sentences with {model} for about "
                               f"${e['expected_usd']:.4f} (up to ${e['high_usd']:.4f})?", assume_yes):
        return {**info, "sent": 0}
    budget = RunBudget(ledger, f"translate-{batch}-{uuid.uuid4().hex[:6]}", cap_usd=cap)
    client = LLMClient(paths, model, "official", command="translate", budget=budget, batch=batch)
    sys_p, pv = system_prompt(src, tgt), prompt_version(src, tgt)

    def send(req: dict) -> dict:
        r = client.respond(sys_p, request_prompt(req), schema=SCHEMA, max_output_tokens=8192,
                           expected_cost=estimate(paths, [req], model, src, tgt)["expected_usd"])
        rec = {"request_id": req["request_id"], "chunk_ids": [c["chunk_id"] for c in req["chunks"]],
               "text": r.text, "cost_usd": r.cost_usd, "request": r.request_id}
        append_jsonl(d / "responses.jsonl", rec)
        return rec

    def run(batch_reqs: list[dict]) -> list[str]:
        errors = []
        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
            futs = {ex.submit(send, r): r for r in batch_reqs}
            for f in as_completed(futs):
                try:
                    cached[futs[f]["request_id"]] = f.result()
                except LLMError as err:
                    errors.append(f"{futs[f]['request_id']}: {err}")
        return errors

    errors = run(to_send)
    today = date.today().isoformat()

    def collect(reqs_: list[dict]) -> tuple[dict[str, dict], list[dict]]:
        good, bad = {}, []
        for req in reqs_:
            rec = cached.get(req["request_id"])
            items = parse_items(rec["text"]) if rec else {}
            for n, c in enumerate(req["chunks"], 1):
                text = items.get(str(n), "")
                reason = "no response" if rec is None else check(c["text"], text, tgt)
                if reason:
                    bad.append({"chunk": c, "reason": reason, "text": text})
                else:
                    good[c["chunk_id"]] = _row(c, text, src, model, pv, today)
        return good, bad

    good, bad = collect(reqs)
    if bad and not errors:  # one retry, one sentence per request
        retry = make_requests([b["chunk"] for b in bad], 1)
        errors += run([r for r in retry if r["request_id"] not in cached])
        g2, bad = collect(retry)
        good.update(g2)
    for b in bad:
        append_jsonl(d / "failures.jsonl", {"chunk_id": b["chunk"]["chunk_id"], "reason": b["reason"],
                                            "text": b["text"]})
    merged = {**done, **good}
    if merged:
        out_f.parent.mkdir(parents=True, exist_ok=True)
        write_chunks(out_f, [merged[k] for k in sorted(merged)])
    return {**info, "sent": len(to_send), "written": len(good), "failed": len(bad), "errors": errors[:5],
            "spent_usd": round(budget.spent_usd, 6), "file": str(out_f)}
