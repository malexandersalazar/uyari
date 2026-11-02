"""Speech to speech is the chain of the three tasks: ASR -> MT -> TTS.

Spanish speech goes through Muse Voice Transcribe (or MMS); Shawi speech through Omnilingual
ASR zero-shot, labelled **unmeasured**. The output is spoken only when a voice exists for the
target language (MMS-TTS); otherwise the chain returns text and says so.
"""

from __future__ import annotations

from pathlib import Path

from uyari.paths import Paths


def run_chain(paths: Paths, audio: Path, src: str, tgt: str, model: str | None = None,
              out: Path | None = None, asr_backend: str | None = None) -> dict:
    from uyari.pipelines.asr.infer import infer_file
    from uyari.pipelines.mt.infer import translate_one
    from uyari.pipelines.tts.check_voice import accepted_texts, check_voice, synthesize

    notes = []
    backend = asr_backend or ("meta" if src == "spa_Latn" else "omniasr")
    if src != "spa_Latn":
        notes.append(f"ASR for {src} is zero-shot and unmeasured (no recordings yet)")
    text = infer_file(audio, src, backend=backend)
    translation = translate_one(paths, text, f"{src[:3]}>{tgt[:3]}", model)
    voice = check_voice(tgt[:3], accepted_texts(paths, tgt) if tgt != "spa_Latn" else None)
    audio_out = None
    if voice["exists"] and voice.get("usable") is not False:
        audio_out = synthesize(tgt[:3], translation, out or Path(audio).with_suffix(f".{tgt[:3]}.wav"))
    elif voice["exists"]:
        notes.append(f"{voice['repo']} exists but covers {voice['letter_coverage']:.0%} of the letters "
                     f"(missing {list(voice['missing_letters'])[:6]}): text output only")
    else:
        notes.append(f"no voice for {tgt} ({voice['repo']} not found): text output only")
    return {"asr_backend": backend, "transcript": text, "translation": translation, "audio_out": audio_out,
            "notes": notes}
