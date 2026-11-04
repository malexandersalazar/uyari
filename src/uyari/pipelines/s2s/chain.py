"""Speech to speech is the chain of the three tasks: ASR -> MT -> TTS.

Official-language speech (Spanish, English) goes through Muse Voice Transcribe; Shawi speech through
Omnilingual ASR zero-shot, labelled **unmeasured**. The output is spoken when the target language has a
usable voice (MMS-TTS, through the language's spelling converter in ``languages/<lang>/tts.yaml``);
otherwise the chain returns text and says so.
"""

from __future__ import annotations

from pathlib import Path

from uyari.paths import Paths

OFFICIAL = ("spa_Latn", "eng_Latn", "por_Latn", "fra_Latn")


def run_chain(paths: Paths, audio: Path, src: str, tgt: str, model: str | None = None,
              out: Path | None = None, asr_backend: str | None = None, assume_yes: bool = False) -> dict:
    from uyari.pipelines.asr.infer import infer_file
    from uyari.pipelines.mt.infer import translate_one
    from uyari.pipelines.tts.check_voice import accepted_texts, check_voice, synthesize
    from uyari.pipelines.tts.voice import load_config

    notes = []
    backend = asr_backend or ("meta" if src in OFFICIAL else "omniasr")
    if src not in OFFICIAL:
        notes.append(f"ASR for {src} is zero-shot and unmeasured (no recordings yet)")
    text = infer_file(audio, src, backend=backend, assume_yes=assume_yes)
    if not text:
        return {"asr_backend": backend, "transcript": "", "translation": "", "audio_out": None,
                "notes": [*notes, "nothing was transcribed"]}
    translation = translate_one(paths, text, f"{src[:3]}>{tgt[:3]}", model)
    cfg = load_config(paths, tgt)
    voice = check_voice(tgt[:3], accepted_texts(paths, tgt, limit=None) if tgt not in OFFICIAL else None, cfg)
    audio_out = None
    if voice["exists"] and voice.get("usable") is not False:
        audio_out = synthesize(tgt[:3], translation, out or Path(audio).with_suffix(f".{tgt[:3]}.wav"), cfg)
        if cfg.rules:
            notes.append(f"spoken by {voice['repo']} (Bible readings) through the spelling converter "
                         f"{cfg.source}: {voice['letter_coverage']:.2%} of the letters readable")
    elif voice["exists"]:
        notes.append(f"{voice['repo']} exists but covers {voice['letter_coverage']:.0%} of the letters "
                     f"(missing {list(voice['missing_letters'])[:6]}): text output only")
    else:
        notes.append(f"no voice for {tgt} ({voice['repo']} not found): text output only")
    return {"asr_backend": backend, "transcript": text, "translation": translation, "audio_out": audio_out,
            "notes": notes}
