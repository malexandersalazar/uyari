"""Gate 1: the validator. Runs on every pull request (``.github/workflows/review.yml``).

Errors block a merge. Warnings are reported; under ``--strict`` the ``todo`` warnings
(unconfirmed license, consent, steward...) become errors so nothing unconfirmed ships.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator

from uyari.csvio import columns, read_csv, read_header, read_yaml, schema
from uyari.data.contributions import CONTRIBUTION_ID, contribution_dirs, load_contribution
from uyari.data.languages import Language, list_languages, load_language
from uyari.data.primary import PrimaryCorpus, list_primaries, load_primary
from uyari.data.splits import check_group_integrity
from uyari.paths import Paths
from uyari.text.normalize import apostrophe_variants_in, normalize_official, word_count

STRICT_CODES = {"todo"}
LOCAL_USE = re.compile(r"^q[a-t][a-z]$")  # ISO 639-3 qaa-qtz


@dataclass
class Issue:
    level: str
    where: str
    row: int | None
    code: str
    message: str


@dataclass
class ValidationReport:
    strict: bool = False
    issues: list[Issue] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=dict)

    def add(self, level: str, where, code: str, message: str, row: int | None = None):
        self.issues.append(Issue(level, str(where), row, code, message))

    def is_error(self, i: Issue) -> bool:
        return i.level == "error" or (self.strict and i.code in STRICT_CODES)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if self.is_error(i)]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if not self.is_error(i)]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {"ok": self.ok, "strict": self.strict, "counts": self.counts,
                "errors": [i.__dict__ for i in self.errors], "warnings": [i.__dict__ for i in self.warnings]}

    def print(self, console, limit: int = 60) -> None:
        for title, items, color in (("ERRORS", self.errors, "red"), ("WARNINGS", self.warnings, "yellow")):
            if not items:
                continue
            console.print(f"[bold {color}]{title} ({len(items)})[/bold {color}]")
            by_code = defaultdict(list)
            for i in items:
                by_code[i.code].append(i)
            for code, its in sorted(by_code.items()):
                console.print(f"  [{color}]{code}[/{color}] x{len(its)}")
                for i in its[: max(1, limit // max(1, len(by_code)))]:
                    row = f":{i.row}" if i.row else ""
                    console.print(f"    {i.where}{row}  {i.message}")
        console.print(f"counts: {self.counts}")
        console.print("[green]OK[/green]" if self.ok else "[red]FAILED[/red]")


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(schema(name))


def _rel(paths: Paths, p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(paths.data).as_posix()
    except ValueError:
        return str(p)


def _todo_scan(obj, prefix="") -> list[str]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += _todo_scan(v, f"{prefix}{k}.")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += _todo_scan(v, f"{prefix}{i}.")
    elif isinstance(obj, str) and obj.strip().upper().startswith("TODO"):
        out.append(prefix.rstrip("."))
    return out


def _load_registry(paths: Paths) -> dict[str, set[str]]:
    def col(file: str, name: str, delim: str) -> set[str]:
        p = paths.registry / file
        if not p.is_file():
            return set()
        with p.open(encoding="utf-8", newline="") as f:
            return {r[name] for r in csv.DictReader(f, delimiter=delim)}

    return {"iso": col("iso639-3.tsv", "code", "\t"), "script": col("iso15924.tsv", "code", "\t"),
            "glotto": col("glottolog.csv", "glottocode", ",")}


# ------------------------------------------------------------------------------- primary
def _check_primary(paths: Paths, lang: str, rep: ValidationReport) -> PrimaryCorpus:
    pc = load_primary(paths, lang)
    v = _validator("chunk")
    cols = columns("chunk")
    for f in pc.files:
        if read_header(f) != cols:
            rep.add("error", _rel(paths, f), "header", f"columns must be exactly {cols}")
    for cid, f in pc.duplicates:
        rep.add("error", _rel(paths, f), "duplicate_chunk_id", f"chunk_id {cid} appears more than once")
    row_no: dict[str, int] = {}
    for f in pc.files:
        for i, r in enumerate(read_csv(f), start=2):
            row_no.setdefault(r.get("chunk_id", ""), i)
    groups = set(pc.groups())
    for cid, r in pc.chunks.items():
        where, row = _rel(paths, pc.file_of[cid]), row_no.get(cid)
        for e in v.iter_errors(r):
            rep.add("error", where, "schema", f"{'.'.join(map(str, e.path)) or 'row'}: {e.message}", row)
        if not r.get("split"):
            rep.add("error", where, "split_unassigned", f"{cid}: run `uyari splits assign`", row)
        if r.get("text") and normalize_official(r["text"]) != r["text"]:
            rep.add("error", where, "not_normalized", f"{cid}: NFC/whitespace", row)
        wc = word_count(r.get("text", ""))
        if not (1 <= wc <= 120):
            rep.add("warning", where, "length", f"{cid}: {wc} words (expected 1-120)", row)
        if r.get("supersedes") and r["supersedes"] not in pc.chunks:
            rep.add("error", where, "supersedes_unknown", f"{cid}: supersedes unknown {r['supersedes']}", row)
        if r.get("regen_of") and r["regen_of"] not in groups:
            rep.add("warning", where, "regen_of_unknown", f"{cid}: regen_of group {r['regen_of']} not found", row)
        if r.get("origin") in ("synthetic", "machine_translated") and not r.get("gen_model"):
            rep.add("warning", where, "provenance", f"{cid}: machine-made text without gen_model", row)
    for p in check_group_integrity(pc):
        rep.add("error", f"primary/{lang}", "split_group", p)
    rep.counts[f"chunks:{lang}"] = len(pc.chunks)
    return pc


# ------------------------------------------------------------------------------- language
def _check_language(paths: Paths, lang: str, reg: dict, primaries: set[str], rep: ValidationReport) -> Language:
    L = load_language(paths, lang)
    where = _rel(paths, L.dir / "language.yaml")
    for e in _validator("language").iter_errors(L.cfg):
        rep.add("error", where, "schema", f"{'.'.join(map(str, e.path)) or 'file'}: {e.message}")
    iso, script = L.cfg.get("iso639_3", ""), L.cfg.get("script", "")
    if L.cfg.get("id") != lang or f"{iso}_{script}" != lang:
        rep.add("error", where, "id", f"id/iso639_3/script must match the folder name {lang}")
    if iso not in reg["iso"] and not LOCAL_USE.match(iso):
        rep.add("error", where, "registry", f"ISO 639-3 '{iso}' not in registry/iso639-3.tsv")
    if script not in reg["script"]:
        rep.add("error", where, "registry", f"script '{script}' not in registry/iso15924.tsv")
    g = L.cfg.get("glottocode", "")
    if g and g != "TODO" and g not in reg["glotto"]:
        rep.add("error", where, "registry", f"glottocode '{g}' not in registry/glottolog.csv")
    if L.primary not in primaries:
        rep.add("error", where, "primary", f"primary '{L.primary}' has no primary/{L.primary}/chunks")
    for k in _todo_scan(L.cfg):
        rep.add("warning", where, "todo", f"{k} is TODO")
    return L


# ------------------------------------------------------------------------------- contributions
def _check_contribution(paths: Paths, d: Path, L: Language, pc: PrimaryCorpus, rep: ValidationReport,
                        global_wave_hashes: dict[str, str], accepted_text: dict[str, str]) -> None:
    c = load_contribution(d, L.id)
    base = _rel(paths, d)
    if not CONTRIBUTION_ID.match(d.name):
        rep.add("error", base, "contribution_id", "folder must be named <YYYY-MM>_<org>_<nnnn>")
    if not (d / "contribution.yaml").is_file():
        rep.add("error", base, "missing", "contribution.yaml is required")
        return
    where = f"{base}/contribution.yaml"
    for e in _validator("contribution").iter_errors(c.meta):
        rep.add("error", where, "schema", f"{'.'.join(map(str, e.path)) or 'file'}: {e.message}")
    if c.meta.get("id") != d.name:
        rep.add("error", where, "id", "id must equal the folder name")
    if c.meta.get("language") != L.id:
        rep.add("error", where, "language", f"language must be {L.id}")
    tmpl = (c.meta.get("consent") or {}).get("template", "")
    if tmpl and not str(tmpl).upper().startswith("TODO") and not (paths.contributing / "en" / tmpl).is_file():
        rep.add("warning", where, "consent_template", f"contributing/en/{tmpl} not found")
    for k in _todo_scan(c.meta):
        rep.add("warning", where, "todo", f"{k} is TODO")
    if c.revoked:
        rep.add("warning", base, "revoked", "revoked: excluded from builds")

    # pairs.csv
    if (d / "pairs.csv").is_file():
        pw = f"{base}/pairs.csv"
        if read_header(d / "pairs.csv") != columns("pair"):
            rep.add("error", pw, "header", f"columns must be exactly {columns('pair')}")
        if c.provenance_text == "none":
            rep.add("error", where, "provenance", "pairs.csv present but provenance.text is none")
        v = _validator("pair")
        seen, per_chunk = set(), defaultdict(int)
        for i, r in enumerate(c.pairs, start=2):
            for e in v.iter_errors(r):
                rep.add("error", pw, "schema", f"{'.'.join(map(str, e.path)) or 'row'}: {e.message}", i)
            cid, text = r.get("chunk_id", ""), r.get("text", "")
            if cid not in pc.chunks:
                rep.add("error", pw, "unknown_chunk", f"chunk_id {cid} is not in primary/{L.primary}", i)
            elif not pc.active(cid):
                rep.add("error", pw, "inactive_chunk", f"chunk_id {cid} is deprecated", i)
            bad = apostrophe_variants_in(text, L.apostrophe, L.apostrophe_variants)
            if bad:
                names = ", ".join(f"U+{ord(ch):04X} {ch!r}" for ch in bad)
                rep.add("error", pw, "apostrophe", f"{names} found; the glottal stop is {L.apostrophe!r} "
                                                   f"(U+{ord(L.apostrophe):04X})", i)
            if text and L.normalize(text) != text and not bad:
                rep.add("error", pw, "not_normalized", "NFC, whitespace or punctuation spacing", i)
            key = (cid, text)
            if key in seen:
                rep.add("error", pw, "duplicate_row", f"{cid}: same translation twice", i)
            seen.add(key)
            per_chunk[cid] += 1
            if cid in pc.chunks and text:
                src_wc, tgt_wc = word_count(pc.chunks[cid]["text"]), word_count(text)
                ratio = tgt_wc / max(1, src_wc)
                if tgt_wc == 0:
                    rep.add("warning", pw, "empty_translation", f"{cid}: {text!r} has no words; "
                                                                "builds leave it out", i)
                elif not (0.3 <= ratio <= 3.0):
                    rep.add("warning", pw, "length_ratio", f"{cid}: {tgt_wc}/{src_wc} words (ratio {ratio:.2f})", i)
            norm = text.casefold()
            if norm and norm in accepted_text and accepted_text[norm] != f"{c.id}/{cid}":
                rep.add("warning", pw, "copied_text", f"identical to {accepted_text[norm]}", i)
            accepted_text.setdefault(norm, f"{c.id}/{cid}")
            rp = r.get("replaces", "")
            if rp:
                tgt_c, tgt_chunk = rp.split("/", 1)
                tdir = paths.contributions_dir(L.id) / tgt_c
                if not (tdir / "pairs.csv").is_file() or tgt_chunk not in {
                        x["chunk_id"] for x in read_csv(tdir / "pairs.csv")}:
                    rep.add("error", pw, "replaces_unknown", f"replaces {rp} does not exist", i)
        for cid, n in per_chunk.items():
            if n > 1:
                rep.add("warning", pw, "multi_translation", f"{cid}: {n} translations in one contribution")
        rep.counts["pairs"] = rep.counts.get("pairs", 0) + len(c.pairs)

    # speakers.csv / audio.csv
    speakers = {r.get("speaker_id", "") for r in c.speakers}
    if (d / "speakers.csv").is_file():
        sw = f"{base}/speakers.csv"
        if read_header(d / "speakers.csv") != columns("speaker"):
            rep.add("error", sw, "header", f"columns must be exactly {columns('speaker')}")
        v = _validator("speaker")
        for i, r in enumerate(c.speakers, start=2):
            for e in v.iter_errors(r):
                rep.add("error", sw, "schema", f"{'.'.join(map(str, e.path)) or 'row'}: {e.message}", i)
    if (d / "audio.csv").is_file():
        aw = f"{base}/audio.csv"
        if read_header(d / "audio.csv") != columns("audio"):
            rep.add("error", aw, "header", f"columns must be exactly {columns('audio')}")
        if not (d / "speakers.csv").is_file():
            rep.add("error", aw, "missing", "speakers.csv is required when audio.csv exists")
        if c.provenance_audio == "none":
            rep.add("error", where, "provenance", "audio.csv present but provenance.audio is none")
        v = _validator("audio")
        own_pairs = {p["chunk_id"] for p in c.pairs}
        try:
            from uyari.audio import check_wav
        except ImportError:  # soundfile not installed: format checks skipped, reported once
            check_wav = None
            rep.add("warning", aw, "audio_checks_skipped", "install the [speech] extra to check clips")
        for i, r in enumerate(c.audio, start=2):
            for e in v.iter_errors(r):
                rep.add("error", aw, "schema", f"{'.'.join(map(str, e.path)) or 'row'}: {e.message}", i)
            if r.get("speaker_id") not in speakers:
                rep.add("error", aw, "unknown_speaker", f"{r.get('speaker_id')} not in speakers.csv", i)
            cid = r.get("chunk_id", "")
            if cid and cid not in pc.chunks:
                rep.add("error", aw, "unknown_chunk", f"chunk_id {cid} is not in primary/{L.primary}", i)
            if cid and not r.get("transcript") and cid not in own_pairs:
                rep.add("error", aw, "transcript", f"{cid}: not in this contribution's pairs.csv; "
                                                   "fill `transcript`", i)
            f = d / r.get("file", "")
            if not f.is_file():
                rep.add("error", aw, "missing_clip", f"{r.get('file')} not found", i)
                continue
            if check_wav:
                chk = check_wav(f)
                for code, msg in chk.problems:
                    rep.add("error", aw, code, f"{r.get('file')}: {msg}", i)
                if chk.sha256:
                    if chk.sha256 in global_wave_hashes:
                        rep.add("error", aw, "duplicate_clip",
                                f"{r.get('file')} identical to {global_wave_hashes[chk.sha256]}", i)
                    global_wave_hashes.setdefault(chk.sha256, f"{c.id}/{r.get('file')}")
        rep.counts["clips"] = rep.counts.get("clips", 0) + len(c.audio)

    if c.review is not None:
        for e in _validator("review").iter_errors(c.review):
            rep.add("error", f"{base}/review.yaml", "schema", e.message)


def _check_takedowns(paths: Paths, rep: ValidationReport, known: set[str]) -> None:
    p = paths.contributing / "takedowns.csv"
    if not p.is_file():
        rep.add("warning", "contributing/takedowns.csv", "missing", "no takedowns file")
        return
    if read_header(p) != columns("takedown"):
        rep.add("error", "contributing/takedowns.csv", "header", f"columns must be {columns('takedown')}")
    v = _validator("takedown")
    for i, r in enumerate(read_csv(p), start=2):
        for e in v.iter_errors(r):
            rep.add("error", "contributing/takedowns.csv", "schema", e.message, i)
        if r.get("contribution") not in known:
            rep.add("warning", "contributing/takedowns.csv", "unknown_contribution", r.get("contribution", ""), i)


def run_validate(paths: Paths, strict: bool = False, only_contribution: Path | None = None) -> ValidationReport:
    rep = ValidationReport(strict=strict)
    reg = _load_registry(paths)
    primaries = set(list_primaries(paths))
    pcs = {lang: _check_primary(paths, lang, rep) for lang in primaries}
    known, waves, accepted = set(), {}, {}
    for lang in list_languages(paths):
        L = _check_language(paths, lang, reg, primaries, rep)
        pc = pcs.get(L.primary) or PrimaryCorpus(lang=L.primary)
        for d in contribution_dirs(paths, lang):
            known.add(d.name)
            _check_contribution(paths, d, L, pc, rep, waves, accepted)
        rep.counts[f"contributions:{lang}"] = len(contribution_dirs(paths, lang))
    _check_takedowns(paths, rep, known)
    if only_contribution is not None:
        prefix = _rel(paths, Path(only_contribution))
        rep.issues = [i for i in rep.issues if i.where.startswith(prefix)]
    _ = read_yaml
    return rep
