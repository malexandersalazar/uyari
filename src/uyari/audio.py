"""Audio clip checks (validator) and helpers.

A clip must be 16 or 48 kHz, mono, 16-bit PCM WAV, 1-20 s long, peak between -12 and -1
dBFS (audible, not clipped) and under 40% silence.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

SAMPLE_RATES = (16000, 48000)
MIN_S, MAX_S = 1.0, 20.0
PEAK_MIN_DB, PEAK_MAX_DB = -12.0, -1.0
SILENCE_DB = -40.0
MAX_SILENCE = 0.40


@dataclass
class ClipCheck:
    path: Path
    problems: list[tuple[str, str]] = field(default_factory=list)  # (code, message)
    seconds: float = 0.0
    sample_rate: int = 0
    peak_db: float = 0.0
    silence: float = 0.0
    sha256: str = ""


def check_wav(path: Path) -> ClipCheck:
    import numpy as np
    import soundfile as sf

    res = ClipCheck(path=Path(path))
    try:
        info = sf.info(str(path))
    except Exception as e:  # noqa: BLE001
        res.problems.append(("audio_unreadable", f"cannot read: {e}"))
        return res
    res.sample_rate = info.samplerate
    res.seconds = info.frames / info.samplerate if info.samplerate else 0.0
    if info.format != "WAV" or info.subtype != "PCM_16":
        res.problems.append(("audio_format", f"{info.format}/{info.subtype}; need WAV PCM_16"))
    if info.samplerate not in SAMPLE_RATES:
        res.problems.append(("audio_rate", f"{info.samplerate} Hz; need 16000 or 48000"))
    if info.channels != 1:
        res.problems.append(("audio_channels", f"{info.channels} channels; need mono"))
    if not (MIN_S <= res.seconds <= MAX_S):
        res.problems.append(("audio_duration", f"{res.seconds:.2f} s; need {MIN_S}-{MAX_S} s"))
    data, sr = sf.read(str(path), dtype="int16", always_2d=True)
    res.sha256 = hashlib.sha256(data.tobytes()).hexdigest()
    x = data[:, 0].astype(np.float32) / 32768.0
    peak = float(np.max(np.abs(x))) if x.size else 0.0
    res.peak_db = 20 * np.log10(peak) if peak > 0 else -120.0
    if not (PEAK_MIN_DB <= res.peak_db <= PEAK_MAX_DB):
        res.problems.append(("audio_peak", f"peak {res.peak_db:.1f} dBFS; need {PEAK_MIN_DB} to {PEAK_MAX_DB}"))
    frame = max(1, int(sr * 0.02))
    n = len(x) // frame
    if n:
        rms = np.sqrt(np.mean(x[: n * frame].reshape(n, frame) ** 2, axis=1) + 1e-12)
        res.silence = float(np.mean(20 * np.log10(rms) < SILENCE_DB))
        if res.silence > MAX_SILENCE:
            res.problems.append(("audio_silence", f"{res.silence:.0%} silence; need < {MAX_SILENCE:.0%}"))
    return res
