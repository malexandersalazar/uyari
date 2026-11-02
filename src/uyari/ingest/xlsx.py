"""One-off ingest of private spreadsheets into the public repository layout.

Reads (private, named in a config kept outside the repository):
  * a Spanish corpus xlsx with its design-matrix columns
  * one translation xlsx per delivered batch
  * optionally a roster, only to build the private name list for the privacy check

Writes:
  * ``primary/<primary>/chunks/generated/<batch>.csv``  (public; every matrix column kept)
  * ``languages/<lang>/contributions/<month>_<org>_<nnnn>/{contribution.yaml,pairs.csv}``
    (public; one per delivered batch; pseudonymous row ids)
  * ``<private>/translator_map.csv``  (private: pseudonym map)
  * ``<private>/quarantine.csv``      (private: rows that could not be matched, with the reason)

Invariant: ``text_id`` is ``chunk_id`` and no translation is dropped. A translated row whose
Spanish does not match its chunk goes to quarantine with the reason, never to the bin.
"""

from __future__ import annotations

import difflib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from uyari.csvio import columns, read_csv, read_yaml, write_csv, write_yaml
from uyari.data.languages import load_language
from uyari.data.primary import PrimaryCorpus, chunk_columns, load_primary, write_chunks
from uyari.data.splits import assign_splits
from uyari.gen.matrix import Matrix
from uyari.paths import Paths
from uyari.text.normalize import dedup_key, normalize_official

QUARANTINE_COLS = ["contribution", "source_row", "text_id", "reason", "similarity", "suggested_chunk_id",
                   "text_es_in_translator_file", "text_es_in_corpus", "text_shw"]
MAP_COLS = ["translator_id", "contributor_id", "contribution", "source_translator_id", "name", "source_file",
            "pairs"]


@dataclass
class IngestReport:
    chunks: int = 0
    chunk_text_whitespace_fixed: int = 0
    pairs_by_contribution: dict[str, int] = field(default_factory=dict)
    quarantined: list[dict] = field(default_factory=list)
    recovered_ids: int = 0
    accepted_with_note: int = 0
    untranslated_rows: int = 0
    split_report: dict = field(default_factory=dict)

    @property
    def pairs(self) -> int:
        return sum(self.pairs_by_contribution.values())


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def read_xlsx(path: Path, sheet: str | None = None) -> list[dict]:
    """Rows as dicts of strings (header from the first row); fully empty rows skipped.
    Each dict carries ``_row`` (1-based Excel row number) for traceability."""
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet] if sheet else wb.worksheets[0]
    it = ws.iter_rows(values_only=True)
    header = [_cell(h).strip() for h in next(it)]
    rows = []
    for i, vals in enumerate(it, start=2):
        d = {h: _cell(v) for h, v in zip(header, vals, strict=False) if h and not h.startswith("Unnamed")}
        if any(v.strip() for v in d.values()):
            d["_row"] = str(i)
            rows.append(d)
    wb.close()
    return rows


def _sim(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, dedup_key(a), dedup_key(b)).ratio()


def _corpus_rows_to_chunks(rows: list[dict], batch: str, provider: str, pv: str,
                           rep: IngestReport) -> list[dict]:
    out = []
    for r in rows:
        text = normalize_official(r["text_es"])
        if text != r["text_es"]:
            rep.chunk_text_whitespace_fixed += 1
        out.append({
            "chunk_id": r["text_id"].strip(),
            "text": text,
            "split": "",
            "origin": "synthetic",
            "status": "active",
            "supersedes": "",
            "domain_l1": r.get("domain_l1", ""),
            "domain_l2": r.get("domain_l2", ""),
            "register": r.get("register", ""),
            "acto_comunicativo": r.get("acto_comunicativo", ""),
            "tiempo_aspecto": r.get("tiempo_aspecto", ""),
            "polaridad": r.get("polaridad", ""),
            "persona_deixis": r.get("persona_deixis", ""),
            "length_bucket": r.get("length_bucket", ""),
            "word_count": r.get("word_count", ""),
            "perfil_hablante": r.get("perfil_hablante", ""),
            "tono_emocional": r.get("tono_emocional", ""),
            "discurso_conectado": (r.get("discurso_conectado", "") or "").lower(),
            "palabras_ancla": r.get("palabras_ancla", ""),
            "source_custom_id": r.get("source_custom_id", ""),
            "source_batch_id": r.get("source_batch_id", ""),
            "regen_of": "",
            "gen_model": r.get("gen_model", ""),
            "provider": provider,
            "gen_date": r.get("gen_date", ""),
            "prompt_version": pv,
        })
    return out


def run_ingest(paths: Paths, config_path: Path, force: bool = False) -> IngestReport:
    cfg = read_yaml(config_path)
    base = paths.data
    rep = IngestReport()
    lang = load_language(paths, cfg["language"])
    primary = cfg.get("primary", lang.primary)
    ccfg = cfg["contributions"]
    accept_sim = float(cfg.get("similarity_accept", 0.9))

    # ---- primary chunks -------------------------------------------------------------
    matrix = Matrix.load(paths.primary_dir(primary) / "matrix.yaml")
    pv = matrix.prompt_version()
    corpus_rows = read_xlsx(base / cfg["corpus"]["file"])
    chunks = _corpus_rows_to_chunks(corpus_rows, cfg["corpus"]["batch"], cfg["corpus"].get("provider", ""),
                                    pv, rep)
    chunk_file = paths.primary_dir(primary) / "chunks" / "generated" / f"{cfg['corpus']['batch']}.csv"
    if chunk_file.exists():  # never lose frozen splits on a re-run
        old = {r["chunk_id"]: r for r in read_csv(chunk_file)}
        for c in chunks:
            if old.get(c["chunk_id"], {}).get("split"):
                c["split"] = old[c["chunk_id"]]["split"]
    by_id = {c["chunk_id"]: c for c in chunks}
    by_text = {}
    for c in chunks:
        by_text.setdefault(dedup_key(c["text"]), c["chunk_id"])
    rep.chunks = len(chunks)

    # ---- roster (private) -----------------------------------------------------------
    roster = {}
    if cfg.get("roster") and (base / cfg["roster"]).is_file():
        for r in read_xlsx(base / cfg["roster"]):
            roster[r.get("translator_id", "")] = r.get("translator_name", "")

    # ---- contributions --------------------------------------------------------------
    map_rows, translated = [], set()
    for n, t in enumerate(cfg["translators"], start=1):
        cid = f"{ccfg['month']}_{ccfg['org_slug']}_{n:04d}"
        tid, contributor = f"t-{n:04d}", f"c-{n:04d}"
        cdir = paths.contributions_dir(lang.id) / cid
        if cdir.exists() and not force:
            raise FileExistsError(f"{cdir} exists; merged contributions are immutable (use --force only "
                                  "before the first merge)")
        pairs, seen = [], set()
        for r in read_xlsx(base / t["file"]):
            text_id = r.get("text_id", "").strip()
            es = r.get("text_es", "")
            shw = r.get("text_shw", "")
            q = {"contribution": cid, "source_row": r["_row"], "text_id": text_id,
                 "text_es_in_translator_file": es, "text_es_in_corpus": by_id.get(text_id, {}).get("text", ""),
                 "text_shw": shw, "similarity": "", "suggested_chunk_id": ""}
            note = ""
            if not shw.strip():
                # Untranslated row, unless the Spanish cell holds something else (shifted cells).
                if text_id in by_id and es.strip() and dedup_key(es) != dedup_key(by_id[text_id]["text"]):
                    rep.quarantined.append({**q, "reason": "text_es differs and text_shw empty "
                                                           "(shifted cells? Shawi text in the Spanish column)",
                                            "similarity": f"{_sim(es, by_id[text_id]['text']):.3f}"})
                else:
                    rep.untranslated_rows += 1
                continue
            if not text_id:
                hit = by_text.get(dedup_key(es))
                if hit:
                    text_id, note = hit, "id recovered by exact Spanish text match"
                    rep.recovered_ids += 1
                else:
                    rep.quarantined.append({**q, "reason": "no text_id and Spanish text matches no chunk"})
                    continue
            if text_id not in by_id:
                rep.quarantined.append({**q, "reason": "text_id not in the corpus"})
                continue
            corpus_es = by_id[text_id]["text"]
            if dedup_key(es) != dedup_key(corpus_es):
                s = _sim(es, corpus_es)
                other = by_text.get(dedup_key(es))
                if other and other != text_id:
                    rep.quarantined.append({**q, "reason": "Spanish in translator file is a different chunk",
                                            "similarity": f"{s:.3f}", "suggested_chunk_id": other})
                    continue
                if s >= accept_sim:
                    note = f"Spanish edited by translator before translating (similarity {s:.2f})"
                    rep.accepted_with_note += 1
                else:
                    rep.quarantined.append({**q, "reason": "Spanish in translator file differs from the chunk",
                                            "similarity": f"{s:.3f}"})
                    continue
            text = lang.normalize(shw)
            if (text_id, text) in seen:
                continue
            seen.add((text_id, text))
            pairs.append({"chunk_id": text_id, "text": text, "replaces": "", "translator_id": tid,
                          "notes": note})
            translated.add(text_id)

        pairs.sort(key=lambda p: (p["chunk_id"], p["text"]))
        meta = {
            "id": cid,
            "language": lang.id,
            "variety": ccfg.get("variety", "_unspecified"),
            "contributor_id": contributor,
            "organization": ccfg["organization"],
            "collection_dates": dict(ccfg.get("collection_dates") or {"start": "TODO", "end": "TODO"}),
            "provenance": {"text": "human", "audio": "none"},
            "license": ccfg.get("license", "TODO"),
            "consent": dict(ccfg.get("consent") or {"template": "consent-collective.md", "authority": "TODO"}),
            "compensated": ccfg.get("compensated", "TODO"),
            "source_primary": f"{primary}/{cfg['corpus']['batch']}",
        }
        write_yaml(cdir / "contribution.yaml", meta,
                   header=f"Contribution {cid}: human translations into {lang.id} of primary {primary}.\n"
                          "Pseudonymous row ids. Immutable once merged.")
        write_csv(cdir / "pairs.csv", pairs, columns("pair"))
        rep.pairs_by_contribution[cid] = len(pairs)
        map_rows.append({"translator_id": tid, "contributor_id": contributor, "contribution": cid,
                         "source_translator_id": str(t.get("source_translator_id", "")),
                         "name": roster.get(str(t.get("source_translator_id", "")), ""),
                         "source_file": t["file"], "pairs": len(pairs)})

    # ---- splits, then write the primary file ------------------------------------------
    write_chunks(chunk_file, chunks)
    pc: PrimaryCorpus = load_primary(paths, primary)
    split_rep = assign_splits(pc, translated)
    write_chunks(chunk_file, [pc.chunks[c["chunk_id"]] for c in chunks])
    rep.split_report = split_rep.__dict__

    # ---- private outputs --------------------------------------------------------------
    write_csv(paths.private / "translator_map.csv", map_rows, MAP_COLS)
    write_csv(paths.private / "quarantine.csv", rep.quarantined, QUARANTINE_COLS)
    _ = Counter, chunk_columns
    return rep
