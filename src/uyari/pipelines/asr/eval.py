"""ASR evaluation: CER (word boundaries are not standardized in many Indigenous orthographies)
and WER, on a build's ``asr.parquet``. A language with 0 clips has nothing to measure; the
fixture language ``qaa_Latn`` exercises the wiring."""

from __future__ import annotations

from uyari.build import read_table
from uyari.paths import Paths
from uyari.pipelines.asr.infer import infer_file


def run_asr_eval(paths: Paths, tag: str, lang: str, backend: str = "mms", split: str = "validation") -> dict:
    import jiwer

    rows = read_table(paths, tag, lang, "asr", test=(split == "test"))
    rows = [r for r in rows if r["split"] == split]
    if not rows:
        return {"lang": lang, "split": split, "clips": 0, "note": "no clips: nothing to measure (see NEEDS.md)"}
    refs = [r["transcript"] for r in rows]
    hyps = [infer_file(paths.data / r["file"], lang, backend=backend) for r in rows]
    safe = [h if h else "∅" for h in hyps]
    return {"lang": lang, "split": split, "clips": len(rows), "backend": backend,
            "cer": round(jiwer.cer(refs, safe), 4), "wer": round(jiwer.wer(refs, safe), 4),
            "label": "measured" if backend != "null" else "plumbing test only"}
