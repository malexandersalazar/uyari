"""Speech-to-text backends.

* ``mms``     facebook/mms-1b-all (transformers, any OS): CTC with a per-language adapter.
* ``omniasr`` Omnilingual ASR (``pip install omnilingual-asr``, Linux): zero-shot for the
              pilot languages; Shawi is listed but **unmeasured** until recordings exist.
* ``meta``    Muse Voice Transcribe (Spanish only; costs money; see uyari.speech.transcribe).
* ``null``    returns "" (plumbing tests on the synthetic fixture).
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

MMS = "facebook/mms-1b-all"
OMNI = "omniASR_LLM_7B"


@cache
def _mms(iso: str):
    import torch
    from transformers import AutoProcessor, Wav2Vec2ForCTC

    proc = AutoProcessor.from_pretrained(MMS)
    model = Wav2Vec2ForCTC.from_pretrained(MMS)
    proc.tokenizer.set_target_lang(iso)
    model.load_adapter(iso)
    return proc, model.to("cuda" if torch.cuda.is_available() else "cpu").eval()


def _load_16k(path: Path):
    import numpy as np
    import soundfile as sf

    x, sr = sf.read(str(path), dtype="float32", always_2d=True)
    x = x.mean(axis=1)
    if sr != 16000:
        n = int(len(x) * 16000 / sr)
        x = np.interp(np.linspace(0, len(x), n, endpoint=False), np.arange(len(x)), x).astype("float32")
    return x


def infer_file(audio: Path, lang: str, backend: str = "mms") -> str:
    iso = lang.split("_")[0]
    if backend == "null":
        return ""
    if backend == "mms":
        import torch

        proc, model = _mms(iso)
        inputs = proc(_load_16k(audio), sampling_rate=16000, return_tensors="pt").to(model.device)
        with torch.no_grad():
            ids = model(**inputs).logits.argmax(-1)[0]
        return proc.decode(ids).strip()
    if backend == "omniasr":
        from omnilingual_asr.models.inference.pipeline import ASRInferencePipeline  # Linux only

        pipe = ASRInferencePipeline(model_card=OMNI)
        return pipe.transcribe([str(audio)], lang=[lang], batch_size=1)[0]
    if backend == "meta":
        if lang != "spa_Latn":
            raise ValueError("Muse Voice Transcribe is used for Spanish only")
        from uyari.paths import Paths
        from uyari.speech.transcribe import transcribe_file

        return transcribe_file(Paths.default(), Path(audio), assume_yes=False).get("text", "")
    raise ValueError(f"unknown backend {backend}")
