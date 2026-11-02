"""Generation plan on disk (``runs/gen/<batch>/plan.jsonl``). State lives on disk, every unit has a status, re-running only sends
units still ``pending``; ``custom_id`` is the paraphrase-group id that joins everything.

Two modes:
  * new cells (``--n``): matrix sampling (round-robin tense/polarity/person, seeded random
    act/register/profile/tone/length, anchor words, connected-discourse quota). Units are
    interleaved across micro-scenarios so even a small batch covers every domain.
  * regenerate (``--regen-from <batch> --cells N``): rebuild N existing units exactly from the
    rows of an existing batch (every matrix column is on every row) for a like-for-like
    comparison. New groups carry ``regen_of`` and inherit the source group's split.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import UTC, datetime
from random import Random

from uyari.csvio import read_csv, read_jsonl, read_yaml, write_jsonl, write_yaml
from uyari.data.primary import chunk_files
from uyari.gen.matrix import Matrix
from uyari.paths import Paths

PRIMARY = "spa_Latn"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def slug(text: str, maxlen: int = 10) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "", t.lower())[:maxlen] or "x"


def make_custom_id(batch: str, idx: int, dominio: str, acto: str) -> str:
    h = hashlib.sha1(f"{batch}:{idx}".encode()).hexdigest()[:12]
    return f"{slug(dominio, 10)}-{slug(acto, 6)}-{h}"


def batch_dir(paths: Paths, batch: str):
    return paths.runs / "gen" / batch


def _unit(m: Matrix, cid: str, dominio: str, micro: str, acto: str, registro: str, tiempo: str, polaridad: str,
          persona: str, perfil: str, tono: str, length_bucket: str, anclas: list[str], conectado: bool,
          regen_of: str = "") -> dict:
    lb = m.lengths[length_bucket]
    return {"custom_id": cid, "domain_l1": dominio, "domain_l2": micro, "acto_comunicativo": acto,
            "register": registro, "tiempo_aspecto": tiempo, "polaridad": polaridad, "persona_deixis": persona,
            "length_bucket": length_bucket, "wc_min": lb["wc_min"], "wc_max": lb["wc_max"],
            "perfil_hablante": perfil, "tono_emocional": tono, "palabras_ancla": anclas,
            "discurso_conectado": conectado, "n_texts": m["texts_per_request"], "regen_of": regen_of,
            "status": "pending", "attempts": 0, "created_at": now_iso()}


def plan_new_cells(m: Matrix, batch: str, n_texts: int) -> list[dict]:
    rng = Random(int(m["seed"]) + int(hashlib.sha1(batch.encode()).hexdigest()[:6], 16))
    micros = [(d, s) for d, ms in m["domains"].items() for s in ms]
    n_units = math.ceil(n_texts / m["texts_per_request"])
    keys = list(m.lengths)
    weights = [m.lengths[k]["weight"] for k in keys]
    T, P, X = m["tiempos"], m["polaridades"], m["personas"]
    units = []
    for idx in range(n_units):
        dominio, micro = micros[idx % len(micros)]
        tiempo = T[idx % len(T)]
        polaridad = P[(idx // len(T)) % len(P)]
        persona = X[(idx // (len(T) * len(P))) % len(X)]
        acto, registro = rng.choice(m["actos"]), rng.choice(m["registros"])
        perfil, tono = rng.choice(m["perfiles"]), rng.choice(m["tonos"])
        lb = rng.choices(keys, weights=weights)[0]
        n_a = int(m["n_palabras_ancla"])
        anclas = rng.sample(m["anclas"][dominio], min(n_a, len(m["anclas"][dominio]))) if n_a > 0 else []
        units.append(_unit(m, make_custom_id(batch, idx, dominio, acto), dominio, micro, acto, registro, tiempo,
                           polaridad, persona, perfil, tono, lb, anclas, False))
    dc = m["discurso_conectado"]
    target = round(float(dc["ratio"]) * len(units))
    elig = [u for u in units if u["domain_l1"] in dc["domains"] or u["acto_comunicativo"] in dc["actos"]]
    rng.shuffle(elig)
    for u in elig[:target]:
        u["discurso_conectado"] = True
        u["length_bucket"] = rng.choice(dc["lengths"])
        u["wc_min"], u["wc_max"] = m.lengths[u["length_bucket"]]["wc_min"], m.lengths[u["length_bucket"]]["wc_max"]
    return units


def plan_regen(paths: Paths, m: Matrix, batch: str, source_batch: str, cells: int) -> list[dict]:
    files = [f for f in chunk_files(paths, PRIMARY) if f.stem == source_batch]
    if not files:
        raise FileNotFoundError(f"no primary/{PRIMARY}/chunks/**/{source_batch}.csv")
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in read_csv(files[0]):
        if r.get("status") == "active":
            groups[r["source_custom_id"]].append(r)
    by_domain: dict[str, list[str]] = defaultdict(list)
    for g, rows in groups.items():
        by_domain[rows[0]["domain_l1"]].append(g)
    total = sum(len(v) for v in by_domain.values())
    order = lambda g: hashlib.sha256(f"{batch}:{g}".encode()).hexdigest()  # noqa: E731
    chosen = []
    for d in sorted(by_domain):
        k = max(1, round(cells * len(by_domain[d]) / total))
        chosen += sorted(by_domain[d], key=order)[:k]
    chosen = sorted(chosen, key=order)[:cells]
    units = []
    for idx, g in enumerate(sorted(chosen)):
        r = groups[g][0]
        anclas = [a for a in (r.get("palabras_ancla") or "").split(";") if a]
        units.append(_unit(m, make_custom_id(batch, idx, r["domain_l1"], r["acto_comunicativo"]), r["domain_l1"],
                           r["domain_l2"], r["acto_comunicativo"], r["register"], r["tiempo_aspecto"],
                           r["polaridad"], r["persona_deixis"], r["perfil_hablante"], r["tono_emocional"],
                           r["length_bucket"], anclas, (r.get("discurso_conectado") or "").lower() == "true",
                           regen_of=g))
    return units


def make_plan(paths: Paths, batch: str, n_texts: int | None = None, regen_from: str | None = None,
              cells: int = 200, model: str | None = None) -> dict:
    d = batch_dir(paths, batch)
    if (d / "plan.jsonl").is_file():
        return {"batch": batch, "existing": True, **status(paths, batch)}
    m = Matrix.load(paths.primary_dir(PRIMARY) / "matrix.yaml")
    if regen_from:
        units = plan_regen(paths, m, batch, regen_from, cells)
    elif n_texts:
        units = plan_new_cells(m, batch, n_texts)
    else:
        raise ValueError("give --n (new cells) or --regen-from (regenerate existing cells)")
    from uyari.llm.catalog import load_catalog

    spec = load_catalog(paths).get(model, "official")
    write_jsonl(d / "plan.jsonl", units)
    write_yaml(d / "batch.yaml", {"batch": batch, "model": spec.key, "model_id": spec.model_id,
                                  "provider": spec.provider, "matrix": f"primary/{PRIMARY}/matrix.yaml",
                                  "prompt_version": m.prompt_version(), "regen_from": regen_from or "",
                                  "cells": len(units), "created_at": now_iso()})
    return {"batch": batch, "existing": False, "units": len(units),
            "texts_expected": sum(u["n_texts"] for u in units),
            "by_domain": dict(Counter(u["domain_l1"] for u in units)), "prompt_version": m.prompt_version()}


def load_plan(paths: Paths, batch: str) -> tuple[list[dict], dict]:
    d = batch_dir(paths, batch)
    if not (d / "plan.jsonl").is_file():
        raise FileNotFoundError(f"no plan for {batch}: run `uyari generate plan --batch {batch} ...`")
    return read_jsonl(d / "plan.jsonl"), read_yaml(d / "batch.yaml")


def save_plan(paths: Paths, batch: str, units: list[dict]) -> None:
    write_jsonl(batch_dir(paths, batch) / "plan.jsonl", units)


def status(paths: Paths, batch: str) -> dict:
    units, meta = load_plan(paths, batch)
    d = batch_dir(paths, batch)
    raw = d / "raw.csv"
    from uyari.llm.ledger import Ledger

    return {"model": meta.get("model"), "units": len(units), "by_status": dict(Counter(u["status"] for u in units)),
            "texts_staged": max(0, sum(1 for _ in raw.open(encoding="utf-8")) - 1) if raw.is_file() else 0,
            "spent_usd": round(Ledger(paths).spent(batch=batch), 6), "prompt_version": meta.get("prompt_version")}
