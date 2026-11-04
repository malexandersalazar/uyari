"""Is there a usable MMS-TTS voice for a language? (``facebook/mms-tts-<iso>``, CC BY-NC 4.0).

Existing is not enough: MMS voices were trained on Bible recordings, often in another spelling.
``check_voice`` measures how many letters of the accepted text the voice's alphabet covers **after** the
language's spelling converter (``languages/<lang>/tts.yaml``, see ``voice.py``), and before it for the
record; a voice that would still drop letters is reported unusable. (Shawi: ``mms-tts-cbt`` has no ``k``,
``w``, ``ñ`` or ``ʼ``; it covers 86% of our letters as written and 99.99% after conversion.)
"""

from __future__ import annotations

from uyari.pipelines.tts.voice import VoiceConfig, alphabet, coverage, load_config, speak, write_wav

MIN_COVERAGE = 0.98


def check_voice(iso: str, texts: list[str] | None = None, cfg: VoiceConfig | None = None) -> dict:
    cfg = cfg or VoiceConfig(voice=f"facebook/mms-tts-{iso}")
    repo = cfg.voice
    try:
        from huggingface_hub import model_info

        info = model_info(repo)
        lic = (info.card_data or {}).get("license") if info.card_data else None
    except Exception as e:  # noqa: BLE001 - 404 or offline
        return {"iso": iso, "repo": repo, "exists": False, "usable": False, "detail": type(e).__name__}
    out = {"iso": iso, "repo": repo, "exists": True, "license": lic}
    if not texts:
        out["usable"] = None
        return out
    letters = alphabet(repo)
    raw = coverage(texts, letters)
    if cfg.rules:
        after = coverage(texts, letters, cfg)
        out.update({"converter": cfg.source or "inline", "letter_coverage": after["letter_coverage"],
                    "missing_letters": after["missing_letters"], "letters": after["letters"],
                    "before_conversion": {k: raw[k] for k in ("letter_coverage", "missing_letters", "letters")}})
    else:
        out.update({"letter_coverage": raw["letter_coverage"], "missing_letters": raw["missing_letters"],
                    "letters": raw["letters"]})
    out["usable"] = out["letter_coverage"] >= MIN_COVERAGE
    if not out["usable"]:
        out["note"] = ("the voice's alphabet does not cover this language's text: it would drop letters. "
                       "Needs a spelling converter (languages/<lang>/tts.yaml), or a voice trained on our recordings.")
    return out


def accepted_texts(paths, lang: str, limit: int | None = 2000) -> list[str]:
    from uyari.data.contributions import load_contributions

    return [p["text"] for c in load_contributions(paths, lang) for p in c.pairs][:limit]


def synthesize(iso: str, text: str, out_path, cfg: VoiceConfig | None = None) -> str:
    """Speak ``text`` (our spelling) to a 16-bit WAV, through ``cfg``'s converter, cutting and seed."""
    sr, wav = speak(cfg or VoiceConfig(voice=f"facebook/mms-tts-{iso}"), text)
    return write_wav(out_path, sr, wav)


__all__ = ["MIN_COVERAGE", "accepted_texts", "check_voice", "load_config", "synthesize"]
