"""``NEEDS.md``: what a language is missing, written from the build manifest. The system says
what it lacks; the first line is the next contribution to ask for."""

from __future__ import annotations

import json
from datetime import date

from uyari.build import latest_tag, load_manifest
from uyari.data.languages import load_language
from uyari.data.primary import load_primary
from uyari.paths import Paths
from uyari.registry import load as load_registry
from uyari.validate import run_validate

HEALTH = ("salud_cuerpo", "puente_civico")


def needs_items(paths: Paths, lang: str, tag: str | None = None) -> tuple[list[str], dict]:
    tag = tag or latest_tag(paths)
    m = load_manifest(paths, tag)["languages"][lang]
    L = load_language(paths, lang)
    c = m["counts"]
    items = []
    if c["clips"] == 0:
        items.append(f"**Recordings.** {c['pairs']:,} pairs, 0 clips. Needs *read* recordings of existing "
                     "translations from at least 3 adult speakers (with consent) before speech recognition can be "
                     "measured; a Shawi voice needs about one hour of read clips from one speaker.")
    elif c["read_clips"] < 600:
        items.append(f"**More recordings.** {c['clips']} clips from {c['speakers']} speaker(s); a voice needs "
                     "about one hour of read clips from one speaker.")
    try:
        from uyari.pipelines.tts.check_voice import accepted_texts, check_voice
        from uyari.pipelines.tts.voice import load_config

        cfg = load_config(paths, lang)
        v = check_voice(L.iso, accepted_texts(paths, lang, limit=None), cfg)
        if v.get("exists") and v.get("usable") is False:
            miss = ", ".join(list(v["missing_letters"])[:4])
            items.append(f"**A voice in our orthography.** `{v['repo']}` exists (Bible recordings, {v.get('license')}) "
                         f"but covers {v['letter_coverage']:.0%} of the letters in our text (no {miss}): it needs a "
                         f"spelling converter (`languages/{lang}/tts.yaml`) written with the steward, or a voice "
                         "trained on our own recordings.")
        elif v.get("exists") and v.get("before_conversion"):
            items.append(f"**Our own voice.** `{v['repo']}` (Bible recordings, {v.get('license')}) reads our text "
                         f"through a spelling converter (`{v['converter']}`): "
                         f"{v['before_conversion']['letter_coverage']:.0%} of the letters as written, "
                         f"{v['letter_coverage']:.2%} after. A voice of our own, in our spelling, comes from the read "
                         "recordings above.")
    except Exception:  # noqa: BLE001 - offline: skip the voice line
        pass
    pc = load_primary(paths, L.primary)
    translated = c.get("chunks_translated_by_domain", {})
    health = sum(translated.get(d, 0) for d in HEALTH)
    open_health = sum(1 for r in pc.chunks.values() if r.get("domain_l1") in HEALTH and r["status"] == "active")
    items.append(f"**Health and civic pairs.** {health} translated in health/civic domains; translate 300–500 more "
                 f"(the primary has {open_health:,} health/civic chunks, more can be generated). Health rows need a "
                 "second native reader.")
    weakest = sorted(translated.items(), key=lambda kv: kv[1])[:2]
    if weakest:
        items.append("**Domain balance.** Fewest pairs: " + ", ".join(f"{d} ({n})" for d, n in weakest) + ".")
    todo = [i.message for i in run_validate(paths).warnings if i.code == "todo" and lang in i.where]
    if todo:
        fields = sorted({m.removesuffix(" is TODO") for m in todo})
        items.append(f"**Confirm {len(todo)} governance field(s)** ({', '.join(fields)}) before weights are "
                     "redistributed.")
    if str(L.cfg.get("community_authority", "")).lower().startswith("to be agreed"):
        items.append("**Community authority.** Agree with Shawi community organizations who is consulted on consent "
                     "and may request a withdrawal, then name it in `language.yaml`.")
    reg = (load_registry(paths).get("mt") or {}).get(lang) or {}
    score = {}
    for slot in ("promoted", "fast"):
        ref = reg.get(slot)
        f = paths.models / ref / "scores.json" if ref else None
        if f and f.is_file():
            v = json.loads(f.read_text(encoding="utf-8")).get("validation", {})
            score[slot] = {"model": ref, "mean_chrf++": v.get("mean_chrf++")}
    return items, {"tag": tag, "counts": c, "models": score}


def write_needs(paths: Paths, lang: str, tag: str | None = None) -> str:
    items, info = needs_items(paths, lang, tag)
    L = load_language(paths, lang)
    c = info["counts"]
    head = f"{lang}: {c['pairs']:,} pairs, {c['clips']} clips"
    models = "; ".join(f"{k}: `{v['model']}` (validation chrF++ {v['mean_chrf++']})" for k, v in info["models"].items())
    lines = [f"# What {L.cfg.get('display_name', lang)} needs next", "",
             f"_{head}. Written by the Trainer from build `{info['tag']}` on {date.today().isoformat()}._", ""]
    lines += [f"{i}. {x}" for i, x in enumerate(items, 1)]
    lines += ["", f"Models: {models or 'none promoted yet'}.", "",
              "## En español", "",
              f"{L.cfg.get('display_name', lang)} tiene {c['pairs']:,} pares traducidos y {c['clips']} grabaciones. "
              "Lo que más falta: grabaciones leídas de las traducciones existentes (al menos 3 personas adultas, con "
              "consentimiento) y más oraciones de salud y trámites. Ver `contributing/es/README.md`.", ""]
    text = "\n".join(lines)
    (L.dir / "NEEDS.md").write_text(text, encoding="utf-8", newline="\n")
    return text
