"""Gatekeeper (gate 2): reviews a contribution and writes its findings in Spanish.

Deterministic checks first (they decide), then Muse Glimmer on our own GPU writes the
row-by-row review and scores a 20-row sample 1-5 against the nearest accepted human pairs.
Glimmer is the default because the review reads Shawi: a hosted Contributor-tier model is
refused by the data-policy guard. If the local server is down, the report says so and the
deterministic findings stand alone.

What it catches: validator failures (unknown ids, wrong apostrophes, schema), Spanish pasted
in the Shawi column, rows copied from accepted contributions, text unlike any accepted Shawi.
What it does NOT do: detect machine translation. Do not claim it.

Recommendation: ``return`` (blocking findings), ``escalate`` (health or consent domains always
need the steward plus a second native reader), else ``merge``. The steward decides.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from uyari.csvio import write_yaml
from uyari.data.contributions import load_contribution, load_contributions
from uyari.data.languages import load_language
from uyari.data.primary import load_primary
from uyari.paths import Paths
from uyari.text.langid import CharNgramLangID
from uyari.validate import run_validate

HEALTH_DOMAINS = {"salud_cuerpo", "puente_civico", "salud_triaje", "consentimiento_informado"}
PROMPT_FILE = Path(__file__).with_name("prompt.md")
SAMPLE = 20
SHOW = 15


@dataclass
class GatekeeperResult:
    contribution: str
    recommendation: str = "merge"
    score: float | None = None
    findings: dict = field(default_factory=dict)
    markdown: str = ""


def _ngrams(text: str, n: int = 3) -> set[str]:
    t = f"  {text.lower()}  "
    return {t[i:i + n] for i in range(len(t) - n + 1)}


def run_gatekeeper(paths: Paths, contribution: Path, llm: str | None = "glimmer-local",
                   out: Path | None = None) -> GatekeeperResult:
    cdir = Path(contribution).resolve()
    lang = cdir.parent.parent.name
    L = load_language(paths, lang)
    c = load_contribution(cdir, lang)
    pc = load_primary(paths, L.primary)
    res = GatekeeperResult(contribution=c.id)
    F = res.findings

    # 1. validator, restricted to this contribution
    v = run_validate(paths, strict=False, only_contribution=cdir)
    F["validator_errors"] = [i.__dict__ for i in v.errors]
    F["validator_warnings"] = [i.__dict__ for i in v.warnings if i.code != "todo"]
    F["todo"] = [i.message for i in v.warnings if i.code == "todo"]

    # accepted = every other contribution of this language
    accepted = [p for o in load_contributions(paths, lang) if o.id != c.id and not o.revoked for p in o.pairs]
    acc_text = {p["text"].casefold(): p["chunk_id"] for p in accepted}
    acc_ngrams = set().union(*(_ngrams(p["text"]) for p in accepted)) if accepted else set()
    rows = [p for p in c.pairs if p.get("text")]

    # 2. language check
    spanish_like, unusual = [], []
    if rows and accepted:
        sp = [r["text"] for r in random.Random(7).sample(list(pc.chunks.values()), min(4000, len(pc.chunks)))]
        clf = CharNgramLangID().fit({L.id: [p["text"] for p in accepted][:4000], L.primary: sp})
        for r, (label, prob) in zip(rows, clf.predict([r["text"] for r in rows]), strict=True):
            if label == L.primary and prob >= 0.8:
                spanish_like.append({"chunk_id": r["chunk_id"], "text": r["text"], "p": round(prob, 2)})
            else:
                ng = _ngrams(r["text"])
                oov = len(ng - acc_ngrams) / max(1, len(ng))
                if oov > 0.5:
                    unusual.append({"chunk_id": r["chunk_id"], "text": r["text"], "unseen_trigrams": round(oov, 2)})
    F["spanish_like"], F["unusual"] = spanish_like, unusual

    # 3. copied rows (exact and near) against accepted pairs; repeated text inside the contribution
    copied, repeated = [], []
    seen_here = defaultdict(list)
    for r in rows:
        k = r["text"].casefold()
        if k in acc_text:
            copied.append({"chunk_id": r["chunk_id"], "text": r["text"], "same_as_chunk": acc_text[k], "kind": "exact"})
        seen_here[k].append(r["chunk_id"])
    if rows and accepted:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit([p["text"] for p in accepted] +
                                                                         [r["text"] for r in rows])
        A = vec.transform([p["text"] for p in accepted])
        Q = vec.transform([r["text"] for r in rows])
        sims = (Q @ A.T).toarray()
        exact_ids = {x["chunk_id"] for x in copied}
        for i, r in enumerate(rows):
            j = sims[i].argmax()
            if sims[i, j] >= 0.95 and r["chunk_id"] not in exact_ids:
                copied.append({"chunk_id": r["chunk_id"], "text": r["text"], "same_as_chunk": accepted[j]["chunk_id"],
                               "kind": f"near ({sims[i, j]:.2f})"})
    for k, ids in seen_here.items():
        if len(set(ids)) > 1:
            repeated.append({"text": k, "chunk_ids": sorted(set(ids))})
    F["copied"], F["repeated_within"] = copied, repeated

    # 4. sample with nearest accepted pairs (by Spanish source similarity)
    sample = random.Random(c.id).sample(rows, min(SAMPLE, len(rows)))
    if accepted and sample:
        from sklearn.feature_extraction.text import TfidfVectorizer

        acc_src = [pc.chunks[p["chunk_id"]]["text"] if p["chunk_id"] in pc.chunks else "" for p in accepted]
        vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4)).fit(acc_src)
        S = (vec.transform([pc.chunks.get(r["chunk_id"], {}).get("text", "") for r in sample]) @
             vec.transform(acc_src).T).toarray()
        for i, r in enumerate(sample):
            r["_es"] = pc.chunks.get(r["chunk_id"], {}).get("text", "")
            r["_near"] = [{"es": acc_src[j], "shw": accepted[j]["text"]} for j in S[i].argsort()[::-1][:3]]
    domains = {pc.chunks[r["chunk_id"]].get("domain_l1", "") for r in rows if r["chunk_id"] in pc.chunks}
    F["domains"] = sorted(domains)

    # 5. decision (deterministic)
    n = max(1, len(rows))
    blocking = []
    if F["validator_errors"]:
        blocking.append(f"{len(F['validator_errors'])} error(es) del validador")
    if len(spanish_like) / n > 0.05 or (spanish_like and len(rows) < 40):
        blocking.append(f"{len(spanish_like)} fila(s) parecen español")
    if len(copied) / n > 0.05 or (copied and len(rows) < 40):
        blocking.append(f"{len(copied)} fila(s) copiadas de contribuciones aceptadas")
    if blocking:
        res.recommendation = "return"
    elif domains & HEALTH_DOMAINS:
        res.recommendation = "escalate"
    F["blocking"] = blocking

    # 6. Glimmer review (local; community data never leaves the machine)
    llm_part, llm_note = None, ""
    if llm and sample:
        try:
            llm_part = _llm_review(paths, llm, L, c.id, sample, F)
            scores = [x.get("score") for x in llm_part.get("rows", []) if isinstance(x.get("score"), int | float)]
            res.score = round(sum(scores) / len(scores), 2) if scores else None
        except Exception as e:  # noqa: BLE001 - the report must still be written
            llm_note = f"Revisión con {llm} no disponible ({type(e).__name__}: {str(e)[:160]}). Solo chequeos deterministas."
    elif not llm:
        llm_note = "Ejecutado con --no-llm: solo chequeos deterministas."

    res.markdown = _markdown(c, L, res, F, sample, llm_part, llm_note, llm)
    d = paths.runs / "gatekeeper" / c.id
    d.mkdir(parents=True, exist_ok=True)
    (d / "review.draft.md").write_text(res.markdown, encoding="utf-8", newline="\n")
    write_yaml(d / "review.draft.yaml", {
        "reviewed_by": f"gatekeeper ({llm or 'no-llm'})", "decided_on": datetime.now(UTC).date().isoformat(),
        "agent_score": res.score, "decision": "in_review",
        "notes": f"recommendation: {res.recommendation}; " + "; ".join(blocking or ["no blocking findings"])})
    if out:
        Path(out).write_text(res.markdown, encoding="utf-8", newline="\n")
    return res


def _llm_review(paths: Paths, model: str, L, cid: str, sample: list[dict], F: dict) -> dict:
    from uyari.llm.client import LLMClient

    cl = LLMClient(paths, model, "community", "gatekeeper")
    items = []
    for r in sample:
        near = "\n".join(f"    - es: {x['es']}\n      shw: {x['shw']}" for x in r.get("_near", []))
        items.append(f"- chunk_id: {r['chunk_id']}\n  es: {r.get('_es', '')}\n  shw: {r['text']}\n  "
                     f"pares_aceptados_cercanos:\n{near}")
    findings = {k: len(v) for k, v in F.items() if isinstance(v, list)}
    prompt = (f"Contribución {cid} ({L.cfg.get('display_name', L.id)}).\nHallazgos automáticos: "
              f"{json.dumps(findings, ensure_ascii=False)}\n\nMuestra de filas:\n" + "\n".join(items))
    schema = {"type": "object", "additionalProperties": False, "required": ["rows", "summary"], "properties": {
        "summary": {"type": "string"},
        "rows": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                            "required": ["chunk_id", "score", "reason"], "properties": {
                                                "chunk_id": {"type": "string"},
                                                "score": {"type": "integer", "minimum": 1, "maximum": 5},
                                                "reason": {"type": "string"}}}}}}
    r = cl.respond(PROMPT_FILE.read_text(encoding="utf-8"), prompt, schema=schema, max_output_tokens=3000,
                   temperature=0.0)
    return extract_json(r.text, required="rows")


def extract_json(text: str, required: str) -> dict:
    """The last JSON object in ``text`` that has key ``required`` (reasoning models may write a
    reasoning channel, fences or prose around it)."""
    dec = json.JSONDecoder()
    found = None
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
        except ValueError:
            continue
        if isinstance(obj, dict) and required in obj:
            found = obj
    if found is None:
        raise ValueError(f"no JSON object with '{required}' in the model output")
    return found


def _markdown(c, L, res: GatekeeperResult, F: dict, sample, llm_part, llm_note, llm) -> str:
    rec = {"merge": "✅ **Recomendación: aceptar (merge)**", "return": "↩️ **Recomendación: devolver (return)**",
           "escalate": "⚠️ **Recomendación: escalar a la persona responsable (steward) y a un segundo lector nativo**"}
    lines = [f"## Revisión automática (Gatekeeper) — `{c.id}`", "", rec[res.recommendation], ""]
    if F["blocking"]:
        lines += ["Motivos: " + "; ".join(F["blocking"]) + ".", ""]
    if res.recommendation == "escalate":
        lines += [f"La contribución incluye dominios de salud o trámites ({', '.join(sorted(set(F['domains']) & HEALTH_DOMAINS))}): "
                  "siempre requiere la firma de la persona responsable y un segundo lector nativo.", ""]
    lines += [f"Filas revisadas: {len(c.pairs)} · Puntaje de consistencia (muestra): "
              f"{res.score if res.score is not None else '—'} / 5", ""]

    def section(title, items, fmt):
        out = [f"### {title} ({len(items)})", ""]
        if not items:
            return out + ["Sin hallazgos.", ""]
        out += [fmt(x) for x in items[:SHOW]]
        if len(items) > SHOW:
            out.append(f"- … y {len(items) - SHOW} más")
        return out + [""]

    lines += section("Validador: errores", F["validator_errors"],
                     lambda i: f"- fila {i['row'] or '—'} · `{i['code']}` · {i['message']}")
    lines += section("Filas que parecen español", F["spanish_like"],
                     lambda x: f"- `{x['chunk_id'][:8]}` (p={x['p']}): {x['text'][:90]}")
    lines += section("Filas copiadas de contribuciones aceptadas", F["copied"],
                     lambda x: f"- `{x['chunk_id'][:8]}` {x['kind']} igual a `{x['same_as_chunk'][:8]}`: {x['text'][:70]}")
    lines += section("Texto poco parecido al shawi aceptado", F["unusual"],
                     lambda x: f"- `{x['chunk_id'][:8]}` ({int(100 * x['unseen_trigrams'])}% de trigramas nuevos): {x['text'][:80]}")
    lines += section("Mismo texto para varias oraciones", F["repeated_within"],
                     lambda x: f"- {len(x['chunk_ids'])} oraciones: {x['text'][:80]}")
    lines += section("Validador: advertencias", F["validator_warnings"],
                     lambda i: f"- fila {i['row'] or '—'} · `{i['code']}` · {i['message']}")
    if F["todo"]:
        lines += ["### Campos por confirmar", "", *[f"- {t}" for t in F["todo"]], ""]
    lines += [f"### Muestra revisada por {llm or 'nadie (sin LLM)'}", ""]
    if llm_part:
        lines += [llm_part.get("summary", ""), "", "| chunk | puntaje | motivo |", "|---|---|---|"]
        lines += [f"| `{x.get('chunk_id', '')[:8]}` | {x.get('score')} | {x.get('reason', '')} |" for x in llm_part.get("rows", [])]
    else:
        lines += [llm_note]
    lines += ["", "_Este reporte no detecta traducción automática; la decisión final es de la persona "
                  "responsable de la lengua (steward)._"]
    _ = sample
    return "\n".join(lines) + "\n"
