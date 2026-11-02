"""Is there a usable MMS-TTS voice for a language? (``facebook/mms-tts-<iso>``, CC BY-NC 4.0).

Existing is not enough: MMS voices were trained on Bible recordings, often in another
orthography. ``check_voice`` also measures how many letters of the accepted text the voice's
character vocabulary covers; a voice that would silently drop letters is reported unusable.
(Shawi: ``mms-tts-cbt`` exists but has no ``k``, ``w`` or ``ʼ``: it reads a Spanish-based
orthography. Using it needs an orthography converter at the edge, or our own recordings.)
"""

from __future__ import annotations

from collections import Counter

MIN_COVERAGE = 0.98


def check_voice(iso: str, texts: list[str] | None = None) -> dict:
    repo = f"facebook/mms-tts-{iso}"
    try:
        from huggingface_hub import model_info

        info = model_info(repo)
        lic = (info.card_data or {}).get("license") if info.card_data else None
    except Exception as e:  # noqa: BLE001 - 404 or offline
        return {"iso": iso, "repo": repo, "exists": False, "usable": False, "detail": type(e).__name__}
    out = {"iso": iso, "repo": repo, "exists": True, "license": lic}
    if texts:
        from transformers import AutoTokenizer

        vocab = set(AutoTokenizer.from_pretrained(repo).get_vocab())
        letters = Counter(ch for t in texts for ch in t.lower() if ch.isalpha() or ch in "ʼ'")
        total = sum(letters.values()) or 1
        missing = {ch: n for ch, n in letters.items() if ch not in vocab}
        cov = 1 - sum(missing.values()) / total
        out.update({"letter_coverage": round(cov, 4),
                    "missing_letters": dict(sorted(missing.items(), key=lambda kv: -kv[1])),
                    "usable": cov >= MIN_COVERAGE})
        if not out["usable"]:
            out["note"] = ("the voice's alphabet does not cover this language's text: it would drop letters. "
                           "Needs an orthography converter at the edge, or a voice trained on our recordings.")
    else:
        out["usable"] = None
    return out


def accepted_texts(paths, lang: str, limit: int = 2000) -> list[str]:
    from uyari.data.contributions import load_contributions

    return [p["text"] for c in load_contributions(paths, lang) for p in c.pairs][:limit]


def synthesize(iso: str, text: str, out_path) -> str:
    import soundfile as sf
    import torch
    from transformers import AutoTokenizer, VitsModel

    repo = f"facebook/mms-tts-{iso}"
    tok = AutoTokenizer.from_pretrained(repo)
    model = VitsModel.from_pretrained(repo)
    with torch.no_grad():
        wav = model(**tok(text, return_tensors="pt")).waveform[0].numpy()
    sf.write(str(out_path), wav, model.config.sampling_rate, subtype="PCM_16")
    return str(out_path)
