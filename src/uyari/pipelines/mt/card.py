"""MODEL_CARD.md for a trained translator: build, recipe, base model and its license, data
by provenance and license, validation (and, once, test) scores against the retrieval floor,
which model the demo serves and why, and plain limitations."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from uyari.build import load_manifest, read_table
from uyari.paths import Paths
from uyari.pipelines.mt.common import read_meta
from uyari.registry import load as load_registry

BASE_LICENSES = {
    "facebook/nllb-200": "CC BY-NC 4.0 (non-commercial; fine-tuned weights inherit it)",
    "meta-models/Muse-Glimmer": "Apache 2.0",
    "HuggingFaceTB/SmolLM2": "Apache 2.0",
}


def base_license(base: str) -> str:
    for k, v in BASE_LICENSES.items():
        if base.startswith(k):
            return v
    return "see the base model's card"


def _license_lines(base: str, lic: dict) -> list[str]:
    base_lic = base_license(base)
    lines = [f"* Weights: base model license, {base_lic}."]
    if "non-commercial" in base_lic:
        lines.append("* Because the base model is non-commercial, these weights cannot be used commercially, "
                     "including by a company deploying them for a clinic or a ministry. The Muse Glimmer "
                     "translator (Apache 2.0 base) is the one for that.")
    data = ", ".join(sorted(lic)) or "none"
    lines.append(f"* Data: {data} (`DATA_LICENSE.md`). Commercial use is allowed. Credit is required whenever "
                 "the data or material adapted from it is shared, and requested for every model, product or "
                 "service built on it: say it comes from Uyari and link the repository (`NOTICE`)."
                 if "TODO" not in lic else
                 f"* Data: {data}. **Not licensed yet; do not redistribute these weights.**")
    return lines


def _fmt(x) -> str:
    return "—" if x is None else f"{x:.1f}" if isinstance(x, float) else str(x)


def write_card(paths: Paths, model_dir: Path, demo_note: str = "") -> Path:
    meta = read_meta(model_dir)
    scores = json.loads((model_dir / "scores.json").read_text(encoding="utf-8")) if (model_dir / "scores.json").is_file() else {}
    floor_f = paths.runs / "retrieval" / meta["build"] / meta["language"] / "scores.json"
    floor = json.loads(floor_f.read_text(encoding="utf-8")) if floor_f.is_file() else {}
    man = load_manifest(paths, meta["build"])["languages"][meta["language"]]
    reg = (load_registry(paths).get("mt") or {}).get(meta["language"]) or {}
    slot = [k for k in ("promoted", "fast") if reg.get(k) == meta["name"]]
    dirs = meta["directions"]

    def row(split, d):
        s = (scores.get(split) or {}).get(f"{d.split('>')[0][:3]}>{d.split('>')[1][:3]}") or {}
        f = (floor.get(split) or {}).get(f"{d.split('>')[0][:3]}>{d.split('>')[1][:3]}") or {}
        return f"| {d} | {_fmt(s.get('chrf++'))} | {_fmt(s.get('bleu'))} | {_fmt(f.get('chrf++'))} | {s.get('n', '—')} |"

    srcs = list(meta.get("primaries") or [meta["primary"]])
    mine = [r for test in (False, True) for r in read_table(paths, meta["build"], meta["language"], "mt", test=test)
            if r["src_lang"] in srcs]
    lic = dict(Counter(r["license"] for r in mine)) or man.get("licenses", {})
    rows_by_split = dict(sorted(Counter(r["split"] for r in mine).items()))
    extra = srcs[1:]
    lines = [
        f"# {meta['name']}",
        "",
        f"Text-to-text translation between **{' / '.join(srcs)}** and **{meta['language']}** (Shawi), "
        f"{'both' if len(srcs) == 1 else 'all'} directions. Base model `{meta['base_model']}` ({base_license(meta['base_model'])}), method "
        f"`{meta['method']}`, trained by recipe `{meta['recipe_id']}` on build `{meta['build']}`.",
        "",
        "## Served by the demo",
        "",
        (f"Registered as **{', '.join(slot)}** for {meta['language']} in `models/registry.yaml`. " if slot else
         "Not currently registered in `models/registry.yaml`. ") + (demo_note or (
            "The demo serves Muse Glimmer (open weights, on our own RTX 4090) by default and NLLB as its fast "
            "mode, whichever scores higher: the project's claim is that it runs on an open-weight Muse model on "
            "our own hardware. Both scores are on both cards.")),
        "",
        "## License and credit",
        "",
        *_license_lines(meta["base_model"], lic),
        "",
        "## Scores",
        "",
        "chrF++ is the score Uyari optimizes and reports; BLEU is reported, not optimized. The retrieval floor "
        "returns the human translation of the most similar training sentence; a model that does not beat it "
        "is not worth serving.",
        "",
        "### Validation",
        "",
        "| Direction | chrF++ | BLEU | Retrieval floor chrF++ | Segments |",
        "|---|---|---|---|---|",
        *[row("validation", d) for d in dirs],
        "",
        "### Test (scored once, at promotion)",
        "",
    ]
    if "test" in scores:
        lines += ["| Direction | chrF++ | BLEU | Retrieval floor chrF++ | Segments |", "|---|---|---|---|---|",
                  *[row("test", d) for d in dirs], "", f"Scored {scores['test'].get('scored_at')}."]
    else:
        lines += ["Not scored yet. `uyari eval --final` writes it once per model version."]
    lines += [
        "",
        "**Human check:** no native-speaker adequacy rating has been done yet (planned: two speakers, 100 "
        "sentences). Learned metrics such as COMET are not used into Shawi until they can be validated against "
        "human judgments.",
        "",
        "## Data",
        "",
        f"* Build `{meta['build']}` (`builds/{meta['build']}/MANIFEST.json`), mt table content hash "
        f"`{man['tables']['mt']['content_sha256'][:16]}`.",
        f"* {man['counts']['pairs']} human Shawi translations of {man['counts']['chunks_translated']} Spanish chunks, "
        f"from {len(man['contributions']['included'])} contributions (provenance: human). Rows by split: "
        f"{rows_by_split} ({', '.join(srcs)}).",
        f"* Contributions excluded (takedowns, revocations): {man['contributions']['excluded'] or 'none'}.",
        f"* Licenses on the rows: {lic}." + (" **The contribution licenses are not confirmed yet (TODO); do not "
                                             "redistribute these weights until they are.**" if "TODO" in lic else ""),
        "* The Spanish side is synthetic, from a fixed design matrix (`primary/spa_Latn/matrix.yaml`). The first "
        "10k chunks were generated in June 2026 with Claude Opus 4.8; generation has since moved to Meta: Muse "
        "Spark 1.3 Contributor produces the same cells at 3.3% of the cost (`reports/gen-comparison.md`), and "
        "Muse Glimmer on our own GPU at no API cost. Every chunk names the model that wrote it.",
        *([f"* {', '.join(extra)}: machine-translated from {srcs[0]} with the same chunk ids "
           f"(`primary/<lang>/chunks/translated/`, `origin=machine_translated`). The Shawi was translated from "
           f"{srcs[0]}, and scores into {', '.join(extra)} are measured against machine-translated references."]
          if extra else []),
        "* Splits are assigned per paraphrase group, so no paraphrase of a test sentence is in training.",
        "",
        "## Limitations",
        "",
        "* About 3,600 sentence pairs, one variety (unspecified), four everyday domains. "
        "Health and civic language is thin (puente_civico has the fewest pairs).",
        "* No Shawi recordings exist yet: this model is text only, and Shawi speech recognition in the demo is "
        "unmeasured.",
        "* Output must be checked by a Shawi speaker before any use in health, legal or civic settings.",
        "",
        "## Intended use",
        "",
        "Communication access, education and language revitalization. Not for surveillance, targeting or "
        "profiling of speakers.",
        "",
        f"_Generated by `uyari` from `{model_dir.name}/uyari_meta.json`, `scores.json` and the build manifest._",
    ]
    out = model_dir / "MODEL_CARD.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return out
