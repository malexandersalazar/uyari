"""The build: the only thing a pipeline trains on.

``uyari build --tag data-YYYY.MM`` turns the merged contributions into one table per task per
language, hashed and documented, so two people training from the same tag get the same data.

1. Reads every contribution; applies ``replaces``; skips revoked contributions and those in
   ``contributing/takedowns.csv`` effective on or before ``as_of``.
2. Normalizes text (NFC, whitespace, the language's canonical apostrophe).
3. Resolves audio transcripts from ``pairs.csv`` when ``transcript`` is empty.
4. Joins each row to its chunk's split and domain.
5. Writes ``builds/<tag>/<lang>/{mt,asr,tts}.parquet`` (train + validation) and
   ``{mt,asr,tts}.test.parquet`` (test, separate so no loader includes it by accident).
6. Writes ``MANIFEST.json``: git commit, contributions included/excluded with reasons, per-table
   ``sha256`` (file bytes) and ``content_sha256`` (canonical rows; the cross-OS invariant),
   rows per split, licenses.

Missing data is derived, never declared: a row lacking something a task needs is simply
absent from that task's table, and the manifest counts show what each language is missing.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from uyari import __version__
from uyari.csvio import write_json
from uyari.data.contributions import load_contributions
from uyari.data.languages import list_languages, load_language
from uyari.data.primary import PrimaryCorpus, list_primaries, load_primary
from uyari.data.splits import _unit
from uyari.data.takedowns import active_takedowns
from uyari.paths import Paths
from uyari.text.normalize import normalize_official, word_count

MT_COLS = ["chunk_id", "split", "domain", "src_lang", "src_origin", "src_text", "tgt_lang", "tgt_text",
           "contribution", "translator_id", "provenance", "license"]
ASR_COLS = ["file", "lang", "transcript", "speaker_id", "style", "split", "chunk_id", "contribution", "license"]
TTS_COLS = ["file", "lang", "transcript", "speaker_id", "split", "chunk_id", "contribution", "license"]
TABLES = {"mt": MT_COLS, "asr": ASR_COLS, "tts": TTS_COLS}


@dataclass
class BuildResult:
    tag: str
    out_dir: Path
    manifest: dict = field(default_factory=dict)
    ok: bool = True
    verify_diffs: list[str] = field(default_factory=list)
    dry_run: bool = False

    def print(self, console) -> None:
        for lang, m in self.manifest.get("languages", {}).items():
            console.print(f"[bold]{lang}[/bold] (primary {m['primary']})")
            for t, info in m["tables"].items():
                console.print(f"  {t:<4} {info['rows']}  content {info['content_sha256'][:12]}")
            console.print(f"  included: {[c['id'] for c in m['contributions']['included']]}")
            if m["contributions"]["excluded"]:
                console.print(f"  excluded: {m['contributions']['excluded']}")
            if m["rows_excluded"]:
                console.print(f"  rows excluded: {m['rows_excluded']}")
        for d in self.verify_diffs:
            console.print(f"[red]{d}[/red]")
        if self.dry_run:
            console.print("[yellow]dry run: nothing written[/yellow]")
        else:
            console.print(f"manifest: {self.out_dir / 'MANIFEST.json'}")
        console.print("[green]OK[/green]" if self.ok else "[red]FAILED[/red]")


def _git(paths: Paths) -> dict:
    def run(*args):
        try:
            return subprocess.run(["git", *args], cwd=paths.code, capture_output=True, text=True,
                                  timeout=10, check=True).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    commit = run("rev-parse", "HEAD")
    return {"commit": commit, "dirty": bool(run("status", "--porcelain")) if commit else None}


def content_sha256(rows: list[dict], cols: list[str]) -> str:
    h = hashlib.sha256()
    for r in rows:
        h.update(json.dumps({c: r.get(c, "") for c in cols}, ensure_ascii=False, sort_keys=True).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write_parquet(path: Path, rows: list[dict], cols: list[str]) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    schema = pa.schema([(c, pa.string()) for c in cols])
    table = pa.Table.from_pylist([{c: str(r.get(c, "")) for c in cols} for r in rows], schema=schema)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    pq.write_table(table, tmp, compression="zstd", use_dictionary=True, write_statistics=False,
                   row_group_size=1_000_000)
    tmp.replace(path)


def _sort_key(cols: list[str]):
    return lambda r: tuple(str(r.get(c, "")) for c in cols)


def _audio_split(contribution: str, speaker: str) -> str:
    u = _unit(f"spk:{contribution}/{speaker}")
    return "test" if u < 0.05 else "validation" if u < 0.10 else "train"


def _build_language(paths: Paths, lang: str, primaries: dict[str, PrimaryCorpus], as_of: date) -> tuple[dict, dict]:
    L = load_language(paths, lang)
    pc = primaries[L.primary]
    others = {k: v for k, v in primaries.items() if k != L.primary}
    takedowns = active_takedowns(paths, as_of)
    contribs = load_contributions(paths, lang)
    included, excluded = [], []
    rows: dict[str, list[dict]] = {t: [] for t in TABLES}
    rx: Counter = Counter()

    # replaces: (contribution, chunk) pairs superseded by a later row
    replaced = set()
    for c in contribs:
        for p in c.pairs:
            if p.get("replaces"):
                replaced.add(tuple(p["replaces"].split("/", 1)))

    for c in contribs:
        td = takedowns.get(c.id)
        if c.revoked:
            excluded.append({"id": c.id, "reason": "revoked (review.yaml)"})
            continue
        if td and td.get("scope") == "contribution":
            excluded.append({"id": c.id, "reason": f"takedown effective {td['effective_date']}"})
            continue
        drop_text = bool(td and td.get("scope") == "text")
        drop_audio = bool(td and td.get("scope") == "audio")
        lic, prov = c.license, c.provenance_text
        n_pairs = n_clips = 0
        pair_text: dict[str, str] = {}
        for p in ([] if drop_text else c.pairs):
            cid = p["chunk_id"]
            chunk = pc.chunks.get(cid)
            if chunk is None:
                rx["unknown_chunk"] += 1
                continue
            if chunk.get("status") != "active":
                rx["deprecated_chunk"] += 1
                continue
            if (c.id, cid) in replaced:
                rx["replaced"] += 1
                continue
            tgt = L.normalize(p["text"])
            if word_count(tgt) == 0:
                rx["empty_translation"] += 1
                continue
            pair_text.setdefault(cid, tgt)
            for src_lang, src in [(L.primary, chunk), *[(k, o.chunks.get(cid)) for k, o in others.items()]]:
                if src is None or src.get("status") != "active":
                    continue
                rows["mt"].append({
                    "chunk_id": cid, "split": chunk["split"], "domain": chunk.get("domain_l1", ""),
                    "src_lang": src_lang, "src_origin": src.get("origin", ""),
                    "src_text": normalize_official(src["text"]), "tgt_lang": lang, "tgt_text": tgt,
                    "contribution": c.id, "translator_id": p.get("translator_id", ""),
                    "provenance": prov, "license": lic})
            n_pairs += 1
        for a in ([] if drop_audio else c.audio):
            cid = a.get("chunk_id", "")
            transcript = a.get("transcript", "") or pair_text.get(cid, "")
            if not transcript:
                rx["untranscribed_clip"] += 1
                continue
            if cid:
                chunk = pc.chunks.get(cid)
                if chunk is None or chunk.get("status") != "active":
                    rx["clip_inactive_chunk"] += 1
                    continue
                split = chunk["split"]
            else:
                split = _audio_split(c.id, a["speaker_id"])
            rel = (c.dir / a["file"]).resolve().relative_to(paths.data).as_posix()
            base = {"file": rel, "lang": lang, "transcript": L.normalize(transcript),
                    "speaker_id": f"{c.id}/{a['speaker_id']}", "split": split, "chunk_id": cid,
                    "contribution": c.id, "license": lic}
            rows["asr"].append({**base, "style": a.get("style", "")})
            if a.get("style") == "read":
                rows["tts"].append(base)
            n_clips += 1
        included.append({"id": c.id, "pairs": n_pairs, "clips": n_clips, "license": lic,
                         "provenance": c.meta.get("provenance", {}),
                         "translators": len({p.get("translator_id") for p in c.pairs})})

    for t, cols in TABLES.items():
        rows[t].sort(key=_sort_key(cols))
    lang_manifest = {
        "primary": L.primary,
        "officials": sorted([L.primary, *others]),
        "contributions": {"included": included, "excluded": excluded},
        "rows_excluded": dict(rx),
        "counts": {
            "pairs": sum(1 for r in rows["mt"] if r["src_lang"] == L.primary),
            "chunks_translated": len({r["chunk_id"] for r in rows["mt"]}),
            "clips": len(rows["asr"]),
            "read_clips": len(rows["tts"]),
            "speakers": len({r["speaker_id"] for r in rows["asr"]}),
            "chunks_translated_by_domain": dict(Counter(r["domain"] for r in rows["mt"]
                                                        if r["src_lang"] == L.primary)),
        },
        "licenses": dict(Counter(r["license"] for r in rows["mt"])),
    }
    return lang_manifest, rows


def run_build(paths: Paths, tag: str, as_of: date | None = None, verify: bool = False,
              dry_run: bool = False, languages: list[str] | None = None,
              officials: list[str] | None = None) -> BuildResult:
    """``officials``: the official languages each Indigenous text is paired with (default: every folder under
    ``primary/``). A build tag is only reproducible with the same list, so the manifest records it."""
    as_of = as_of or date.today()
    out_dir = paths.builds / tag
    res = BuildResult(tag=tag, out_dir=out_dir, dry_run=dry_run or verify)
    langs = languages or list_languages(paths)
    available = list_primaries(paths)
    if officials is None:
        names = available
    else:
        unknown = sorted(set(officials) - set(available))
        if unknown:
            raise ValueError(f"no primary corpus for {unknown} (have {available})")
        needed = sorted({load_language(paths, lang).primary for lang in langs} - set(officials))
        if needed:
            raise ValueError(f"officials must include each language's primary: add {needed}")
        names = sorted(set(officials))
    primaries = {p: load_primary(paths, p) for p in names}
    manifest = {"tag": tag, "as_of": as_of.isoformat(), "uyari_version": __version__, "git": _git(paths),
                "languages": {}}
    for lang in langs:
        lm, rows = _build_language(paths, lang, primaries, as_of)
        lm["tables"] = {}
        for t, cols in TABLES.items():
            main = [r for r in rows[t] if r["split"] in ("train", "validation")]
            test = [r for r in rows[t] if r["split"] == "test"]
            info = {"file": f"{lang}/{t}.parquet", "test_file": f"{lang}/{t}.test.parquet",
                    "rows": dict(Counter(r["split"] for r in rows[t])),
                    "content_sha256": content_sha256(main, cols),
                    "test_content_sha256": content_sha256(test, cols)}
            if not res.dry_run:
                write_parquet(out_dir / info["file"], main, cols)
                write_parquet(out_dir / info["test_file"], test, cols)
                info["sha256"] = file_sha256(out_dir / info["file"])
                info["test_sha256"] = file_sha256(out_dir / info["test_file"])
            lm["tables"][t] = info
        manifest["languages"][lang] = lm
    res.manifest = manifest

    if verify:
        mf = out_dir / "MANIFEST.json"
        if not mf.is_file():
            res.ok = False
            res.verify_diffs.append(f"{mf} not found")
            return res
        old = json.loads(mf.read_text(encoding="utf-8"))
        for lang, lm in manifest["languages"].items():
            for t, info in lm["tables"].items():
                o = old.get("languages", {}).get(lang, {}).get("tables", {}).get(t, {})
                for k in ("content_sha256", "test_content_sha256"):
                    if o.get(k) != info[k]:
                        res.ok = False
                        res.verify_diffs.append(f"{lang}/{t} {k}: manifest {o.get(k, '')[:12]} != now {info[k][:12]}")
                for k, fk in (("sha256", "file"), ("test_sha256", "test_file")):
                    f = out_dir / info[fk]
                    if o.get(k) and f.is_file() and file_sha256(f) != o[k]:
                        res.ok = False
                        res.verify_diffs.append(f"{lang}/{t} {k}: parquet bytes changed since the manifest")
        return res

    if not dry_run:
        write_json(out_dir / "MANIFEST.json", manifest)
    _ = defaultdict
    return res


def latest_tag(paths: Paths) -> str | None:
    if not paths.builds.is_dir():
        return None
    tags = sorted(p.name for p in paths.builds.iterdir() if (p / "MANIFEST.json").is_file())
    return tags[-1] if tags else None


def load_manifest(paths: Paths, tag: str) -> dict:
    return json.loads((paths.builds / tag / "MANIFEST.json").read_text(encoding="utf-8"))


def read_table(paths: Paths, tag: str, lang: str, task: str, test: bool = False) -> list[dict]:
    import pyarrow.parquet as pq

    f = paths.builds / tag / lang / f"{task}{'.test' if test else ''}.parquet"
    if not f.is_file():
        raise FileNotFoundError(f"{f} missing: run `uyari build --tag {tag}`")
    return pq.read_table(f).to_pylist()
