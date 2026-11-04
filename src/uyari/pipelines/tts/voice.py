"""Read text aloud with a Meta MMS voice (``facebook/mms-tts-<iso>``, CC BY-NC 4.0, local, 16 kHz).

MMS voices were trained on Bible readings, often in an older spelling than ours. ``languages/<lang>/tts.yaml``
says how to rewrite our text into the voice's alphabet (Shawi: ``k`` -> ``c``/``qu``, ``w`` -> ``hu``,
``ñ`` -> ``ny``, ``ʼ`` -> ``ꞌ``); without that file the text is read as written.

* The conversion only feeds the voice: every screen shows our spelling.
* Rules apply in order, after lowercasing and Unicode NFC.
* The voice reads no punctuation, so text is spoken in pieces cut at punctuation, joined by pauses.
* The voice samples noise: the seed is set before every piece, so the same text always sounds the same.
* Letters still outside the voice's alphabet are logged (its tokenizer drops them silently). Not an error.
* A voice loads once per process; audio is cached by text and rules.
* What the voice actually reads is the converted text filtered by its alphabet (:func:`reading`). Decoding
  its token ids does not show that: the tokenizer's pad token is the letter ``a``, placed between all letters.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import unicodedata
from collections import Counter, OrderedDict
from dataclasses import dataclass
from functools import cache
from pathlib import Path

log = logging.getLogger("uyari.tts")

APOSTROPHES = "ʼ'’"  # counted as letters: the glottal stop is a letter
CACHE_SIZE = 128
CONFIG_KEYS = {"voice", "seed", "rules", "split_at", "sentence_end", "pause_seconds"}


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text.lower())


@dataclass(frozen=True)
class Rule:
    find: tuple[str, ...]
    write: str
    before: tuple[str, ...] = ()

    def pattern(self) -> re.Pattern:
        alt = "|".join(re.escape(f) for f in sorted(self.find, key=len, reverse=True))
        ahead = "(?=" + "|".join(re.escape(b) for b in self.before) + ")" if self.before else ""
        return re.compile(f"(?:{alt}){ahead}")


@dataclass(frozen=True)
class VoiceConfig:
    """``languages/<lang>/tts.yaml``: the voice, how our spelling is rewritten for it, how text is cut."""

    voice: str
    rules: tuple[Rule, ...] = ()
    seed: int = 7
    split_at: str = ".,;:?!¿¡"
    sentence_end: str = ".?!"
    sentence_pause: float = 0.35
    comma_pause: float = 0.15
    source: str = ""  # the file it was read from ("" for the plain default)

    @property
    def key(self) -> str:
        """Changes whenever anything that changes the sound changes (the audio cache key)."""
        parts = (self.voice, self.rules, self.seed, self.split_at, self.sentence_end, self.sentence_pause,
                 self.comma_pause)
        return hashlib.sha1(repr(parts).encode("utf-8")).hexdigest()[:12]

    def convert(self, text: str) -> str:
        """Our spelling -> the voice's spelling: lowercase, NFC, then every rule in order."""
        out = _norm(text)
        for r in self.rules:
            out = r.pattern().sub(r.write, out)
        return out

    def pieces(self, text: str) -> list[tuple[str, float]]:
        """``[(converted piece, pause after it in seconds), ...]``, cut at ``split_at``. A piece cut by any
        ``sentence_end`` mark is followed by the sentence pause, by any other mark the comma pause. Pieces may
        be empty (``"¿"`` at the start); :func:`speak` skips them and keeps the longest pending pause."""
        s = self.convert(text)
        if not self.split_at:
            return [(s.strip(), 0.0)] if s.strip() else []
        marks = re.escape(self.split_at)
        out = []
        for m in re.finditer(f"([^{marks}]*)([{marks}]*)", s):
            piece, cut = m.group(1).strip(), m.group(2)
            if not piece and not cut:
                continue
            ends_sentence = any(c in self.sentence_end for c in cut)
            out.append((piece, self.sentence_pause if ends_sentence else self.comma_pause if cut else 0.0))
        return out


def _strings(v, what: str) -> tuple[str, ...]:
    items = [v] if isinstance(v, str) else list(v or [])
    if not items or not all(isinstance(x, str) and x for x in items):
        raise ValueError(f"tts.yaml: {what} must be text (quote single letters YAML could misread): {v!r}")
    return tuple(items)


def parse_config(data: dict, default_voice: str, source: str = "") -> VoiceConfig:
    unknown = set(data) - CONFIG_KEYS
    if unknown:
        raise ValueError(f"tts.yaml: unknown key(s) {sorted(unknown)}; allowed: {sorted(CONFIG_KEYS)}")
    rules = []
    for i, r in enumerate(data.get("rules") or [], 1):
        extra = set(r) - {"find", "write", "before"}
        if extra or "find" not in r or "write" not in r:
            raise ValueError(f"tts.yaml rule {i}: needs find and write (optional: before), got {sorted(r)}")
        write = r["write"]
        if not isinstance(write, str):
            raise ValueError(f"tts.yaml rule {i}: write must be text, got {write!r}")
        rules.append(Rule(find=_strings(r["find"], f"rule {i} find"), write=write,
                          before=_strings(r["before"], f"rule {i} before") if r.get("before") else ()))
    pause = data.get("pause_seconds") or {}
    d = VoiceConfig(voice=default_voice)
    return VoiceConfig(voice=data.get("voice") or default_voice, rules=tuple(rules),
                       seed=int(data.get("seed", d.seed)), split_at=str(data.get("split_at", d.split_at)),
                       sentence_end=str(data.get("sentence_end", d.sentence_end)),
                       sentence_pause=float(pause.get("sentence", d.sentence_pause)),
                       comma_pause=float(pause.get("comma", d.comma_pause)), source=source)


def load_config(paths, lang: str) -> VoiceConfig:
    """The language's ``tts.yaml``, or the plain MMS voice for its ISO code with default cutting."""
    from uyari.csvio import read_yaml

    default = f"facebook/mms-tts-{lang.split('_')[0]}"
    f = Path(paths.language_dir(lang)) / "tts.yaml"
    if not f.is_file():
        return VoiceConfig(voice=default)
    try:
        source = f.relative_to(paths.data).as_posix()
    except ValueError:
        source = str(f)
    return parse_config(read_yaml(f), default, source=source)


# ----------------------------------------------------------------------------------------------- the voice
@cache
def alphabet(repo: str) -> frozenset[str]:
    """The voice's letters (its tokenizer vocabulary), without loading the model."""
    from transformers import AutoTokenizer

    return frozenset(k for k in AutoTokenizer.from_pretrained(repo).get_vocab() if len(k) == 1)


def reading(piece: str, letters: frozenset[str]) -> str:
    """What the voice reads of a converted piece: only its own letters (the tokenizer drops the rest)."""
    return re.sub(r"\s+", " ", "".join(c for c in piece if c in letters)).strip()


def unread(text: str, letters: frozenset[str]) -> Counter:
    """Letters and digits the voice would skip."""
    return Counter(c for c in text if c.isalnum() and c not in letters)


def coverage(texts: list[str], letters: frozenset[str], cfg: VoiceConfig | None = None) -> dict:
    """Share of letters (``ʼ`` counts as one) the voice can read, before or after ``cfg``'s conversion."""
    conv = cfg.convert if cfg else _norm
    counts = Counter(ch for t in texts for ch in conv(t) if ch.isalpha() or ch in APOSTROPHES)
    total = sum(counts.values())
    missing = {ch: n for ch, n in sorted(counts.items(), key=lambda kv: -kv[1]) if ch not in letters}
    return {"letters": total, "letter_coverage": round(1 - sum(missing.values()) / (total or 1), 4),
            "missing_letters": missing}


class MmsVoice:
    """One loaded MMS-TTS voice on the CPU (fast enough: about 12x real time, and it leaves the GPU to MT)."""

    def __init__(self, tokenizer, model):
        self.tok, self.model = tokenizer, model
        self.letters = frozenset(k for k in tokenizer.get_vocab() if len(k) == 1)
        self.sampling_rate = int(model.config.sampling_rate)
        self._lock = threading.Lock()

    @classmethod
    def load(cls, repo: str) -> MmsVoice:
        from transformers import AutoTokenizer, VitsModel

        return cls(AutoTokenizer.from_pretrained(repo), VitsModel.from_pretrained(repo).eval())

    def say(self, text: str, seed: int):
        """Float32 mono audio for text already in the voice's alphabet. The seed is set right before the
        forward pass, in a forked generator so no one else's random state changes."""
        import torch

        inputs = self.tok(text, return_tensors="pt")
        with self._lock, torch.random.fork_rng(devices=[]), torch.no_grad():
            torch.manual_seed(seed)
            wav = self.model(**inputs).waveform[0]
        return wav.float().cpu().numpy()


@cache
def get_voice(repo: str) -> MmsVoice:
    log.info("loading voice %s", repo)
    return MmsVoice.load(repo)


_audio: OrderedDict = OrderedDict()
_audio_lock = threading.Lock()


def speak(cfg: VoiceConfig, text: str, voice=None) -> tuple[int, object]:
    """``(sampling_rate, float32 mono numpy array)`` for ``text`` in our spelling (read-only array)."""
    import numpy as np

    voice = voice or get_voice(cfg.voice)
    key = (cfg.voice, cfg.key, text)
    with _audio_lock:
        if key in _audio:
            _audio.move_to_end(key)
            return _audio[key]
    sr = voice.sampling_rate
    parts, pending, left = [], 0.0, Counter()
    for piece, pause in cfg.pieces(text):
        left.update(unread(piece, voice.letters))
        said = reading(piece, voice.letters)
        if not said:
            pending = max(pending, pause)
            continue
        if parts:
            parts.append(np.zeros(int(round(pending * sr)), dtype=np.float32))
        parts.append(np.asarray(voice.say(said, cfg.seed), dtype=np.float32))
        pending = pause
    if left:
        log.warning("%s cannot read %s (left out, not an error) in: %s", cfg.voice,
                    ", ".join(f"{c} x{n}" for c, n in left.most_common()), text[:120])
    wav = np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)
    wav.setflags(write=False)
    res = (sr, wav)
    with _audio_lock:
        _audio[key] = res
        while len(_audio) > CACHE_SIZE:
            _audio.popitem(last=False)
    return res


def write_wav(path, sr: int, wav) -> str:
    import soundfile as sf

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), wav, sr, subtype="PCM_16")
    return str(path)
