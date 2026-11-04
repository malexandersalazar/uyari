"""``uyari``: one command per pipeline stage.

Every command takes ``--root`` (the data root; defaults to the repository) so the same code
runs on the real data and on ``tests/fixtures/root``. Heavy imports (torch, transformers)
happen inside the commands that need them.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

from uyari.paths import Paths

load_dotenv(override=False)
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (ValueError, OSError):
        pass

app = typer.Typer(no_args_is_help=True, add_completion=False, help=__doc__)
console = Console()

ingest_app = typer.Typer(no_args_is_help=True, help="One-off importers (private inputs).")
splits_app = typer.Typer(no_args_is_help=True, help="Train/validation/test assignment.")
gen_app = typer.Typer(no_args_is_help=True, help="Spanish primary-corpus generation (Meta API).")
llm_app = typer.Typer(no_args_is_help=True, help="LLM endpoints, spend ledger.")
serve_app = typer.Typer(no_args_is_help=True, help="Local Glimmer server (vLLM or llama-server).")
report_app = typer.Typer(no_args_is_help=True, help="Human-readable reports.")
asr_app = typer.Typer(no_args_is_help=True, help="Speech to text.")
tts_app = typer.Typer(no_args_is_help=True, help="Text to speech.")
primary_app = typer.Typer(no_args_is_help=True, help="Primary-corpus maintenance.")
for name, sub in [("ingest", ingest_app), ("splits", splits_app), ("generate", gen_app), ("llm", llm_app),
                  ("serve", serve_app), ("report", report_app), ("asr", asr_app), ("tts", tts_app),
                  ("primary", primary_app)]:
    app.add_typer(sub, name=name)

ROOT_OPT = typer.Option(None, "--root", help="Data root (default: the repository).")


def _paths(root: Path | None) -> Paths:
    return Paths.default(root)


def _fail(msg: str, code: int = 1):
    console.print(f"[red]{msg}[/red]")
    raise typer.Exit(code)


# ------------------------------------------------------------------------------- ingest
@ingest_app.command("xlsx")
def ingest_xlsx(config: Path = typer.Option(..., help="Private ingest config (kept outside the repository)."),
                force: bool = typer.Option(False, help="Overwrite contribution folders (before first merge only)."),
                root: Path = ROOT_OPT):
    """Spreadsheets -> primary chunks + pseudonymous contributions (+ private map, quarantine)."""
    from uyari.ingest.xlsx import run_ingest

    rep = run_ingest(_paths(root), config, force=force)
    t = Table(title="Ingest")
    t.add_column("item")
    t.add_column("value", justify="right")
    t.add_row("chunks", str(rep.chunks))
    t.add_row("chunk text whitespace fixed", str(rep.chunk_text_whitespace_fixed))
    for cid, n in rep.pairs_by_contribution.items():
        t.add_row(f"pairs {cid}", str(n))
    t.add_row("pairs total", str(rep.pairs))
    t.add_row("ids recovered by text", str(rep.recovered_ids))
    t.add_row("accepted with note", str(rep.accepted_with_note))
    t.add_row("quarantined (<private>/quarantine.csv)", str(len(rep.quarantined)))
    t.add_row("untranslated rows", str(rep.untranslated_rows))
    console.print(t)
    console.print_json(json.dumps(rep.split_report, ensure_ascii=False))


# ------------------------------------------------------------------------------- splits
@splits_app.command("assign")
def splits_assign(primary: str = "spa_Latn", root: Path = ROOT_OPT):
    """Fill empty splits (frozen once written; whole paraphrase groups; regen_of inherits)."""
    from uyari.data.primary import load_primary, rewrite_files
    from uyari.data.splits import assign_splits
    from uyari.translated import translated_chunk_ids

    p = _paths(root)
    pc = load_primary(p, primary)
    rep = assign_splits(pc, translated_chunk_ids(p, primary))
    rewrite_files(pc)
    console.print_json(json.dumps(rep.__dict__))


# ------------------------------------------------------------------------------- validate
@app.command()
def validate(strict: bool = typer.Option(False, help="Warnings that block publishing (TODO values) become errors."),
             contribution: Path = typer.Option(None, help="Validate only this contribution folder."),
             as_json: bool = typer.Option(False, "--json"),
             root: Path = ROOT_OPT):
    """Gate 1: schemas, registry, ids, normalization, duplicates, audio."""
    from uyari.validate import run_validate

    rep = run_validate(_paths(root), strict=strict, only_contribution=contribution)
    if as_json:
        print(json.dumps(rep.to_dict(), ensure_ascii=False, indent=2))
    else:
        rep.print(console)
    raise typer.Exit(0 if rep.ok else 1)


# ------------------------------------------------------------------------------- build
@app.command()
def build(tag: str = typer.Option(..., help="Build tag, e.g. data-2026.11"),
          as_of: str = typer.Option(None, help="Takedown cut-off date (YYYY-MM-DD); default today."),
          verify: bool = typer.Option(False, help="Recompute and compare against the existing manifest."),
          dry_run: bool = typer.Option(False, help="Compute counts and hashes; write nothing."),
          officials: str = typer.Option(None, help="Official languages to pair with, comma-separated (e.g. "
                                                    "spa_Latn,eng_Latn). Default: every folder under primary/."),
          root: Path = ROOT_OPT):
    """Contributions -> builds/<tag>/<lang>/{mt,asr,tts}(.test).parquet + MANIFEST.json."""
    from uyari.build import run_build

    d = date.fromisoformat(as_of) if as_of else None
    only = [x.strip() for x in officials.split(",") if x.strip()] if officials else None
    try:
        res = run_build(_paths(root), tag, as_of=d, verify=verify, dry_run=dry_run, officials=only)
    except ValueError as e:
        _fail(str(e))
    res.print(console)
    raise typer.Exit(0 if res.ok else 1)


# ------------------------------------------------------------------------------- mt
@app.command()
def prepare(recipe: Path = typer.Option(...), root: Path = ROOT_OPT):
    """Build table -> runs/<recipe>/data/{train,validation}.jsonl (directions, filters, codec, coverage)."""
    from uyari.pipelines.mt.prepare import run_prepare

    out = run_prepare(_paths(root), recipe)
    console.print_json(json.dumps(out.stats, ensure_ascii=False))


@app.command()
def train(recipe: Path = typer.Option(...),
          max_steps: int = typer.Option(None, help="Smoke runs only: stop after N optimizer steps."),
          root: Path = ROOT_OPT):
    """Train the model a recipe describes (seq2seq NLLB or QLoRA Glimmer)."""
    from uyari.pipelines.mt.train import run_train

    out = run_train(_paths(root), recipe, max_steps=max_steps)
    console.print(f"[green]trained[/green] {out}")


@app.command("eval")
def eval_cmd(model: str = typer.Option(..., help="models/<name>@vX.Y, or 'retrieval' for the floor."),
             recipe: Path = typer.Option(None, help="Needed for 'retrieval'."),
             split: str = typer.Option("validation"),
             final: bool = typer.Option(False, help="Score test. Once per model version; refuses a second time."),
             limit: int = typer.Option(None, help="Score only the first N rows per direction (smoke)."),
             root: Path = ROOT_OPT):
    """chrF++ (main) and BLEU per direction and per domain."""
    from uyari.pipelines.mt.eval import run_eval

    if split == "test" and not final:
        _fail("test is scored only with --final (once per model version)")
    scores = run_eval(_paths(root), model, split="test" if final else split, recipe=recipe, limit=limit)
    console.print_json(json.dumps(scores, ensure_ascii=False))


@app.command()
def translate(text: str, direction: str = typer.Option("spa>cbt"), model: str = typer.Option(None),
              root: Path = ROOT_OPT):
    """Translate one sentence with a trained model (default: the promoted one)."""
    from uyari.pipelines.mt.infer import translate_one

    console.print(translate_one(_paths(root), text, direction, model))


# ------------------------------------------------------------------------------- generation
@gen_app.command("plan")
def gen_plan(batch: str = typer.Option(...), n: int = typer.Option(None, help="Texts wanted (new cells)."),
             regen_from: str = typer.Option(None, help="Regenerate cells of this existing batch."),
             cells: int = typer.Option(200), model: str = typer.Option(None), root: Path = ROOT_OPT):
    """Build the generation plan on disk (runs/gen/<batch>/plan.jsonl). Idempotent."""
    from uyari.gen.plan import make_plan

    info = make_plan(_paths(root), batch, n_texts=n, regen_from=regen_from, cells=cells, model=model)
    console.print_json(json.dumps(info, ensure_ascii=False))


@gen_app.command("run")
def gen_run(batch: str = typer.Option(...), estimate: bool = typer.Option(False, help="Cost table only, no network."),
            max_usd: float = typer.Option(None), concurrency: int = typer.Option(8),
            limit: int = typer.Option(None, help="Send at most N pending units this run."),
            yes: bool = typer.Option(False, "--yes", help="Do not ask for confirmation."),
            root: Path = ROOT_OPT):
    """Send pending units to the model, validate, dedup, append to the batch CSV."""
    from uyari.gen.generate import run_generate

    run_generate(_paths(root), batch, estimate_only=estimate, max_usd=max_usd, concurrency=concurrency,
                 limit=limit, assume_yes=yes, console=console)


@gen_app.command("collect")
def gen_collect(batch: str = typer.Option(...), root: Path = ROOT_OPT):
    """Re-collect a batch from its cached responses (no API call, no cost) after a validation change."""
    from uyari.gen.generate import recollect

    recollect(_paths(root), batch, console=console)


@gen_app.command("status")
def gen_status(batch: str = typer.Option(...), root: Path = ROOT_OPT):
    from uyari.gen.plan import status

    console.print_json(json.dumps(status(_paths(root), batch), ensure_ascii=False))


@gen_app.command("dedup")
def gen_dedup(batch: str = typer.Option(...), semantic: bool = typer.Option(True),
              threshold: float = typer.Option(0.92), root: Path = ROOT_OPT):
    """Exact + embedding near-duplicates of a batch against itself and the whole primary."""
    from uyari.gen.dedup import run_dedup

    console.print_json(json.dumps(run_dedup(_paths(root), batch, semantic=semantic, threshold=threshold)))


@gen_app.command("compare")
def gen_compare(a: str = typer.Option(..., help="Batch A (e.g. 2026-06_opus48_0001)"),
                b: str = typer.Option(..., help="Batch B (the Muse batch)"),
                export_blind: bool = typer.Option(False, help="Write a blind 50+50 xlsx for a human read."),
                import_ratings: Path = typer.Option(None, help="Read the filled blind xlsx back."),
                semantic: bool = typer.Option(True), root: Path = ROOT_OPT):
    """Batch-versus-batch generation report -> reports/gen-comparison.md."""
    from uyari.gen.compare import run_compare

    out = run_compare(_paths(root), a, b, export_blind=export_blind, ratings=import_ratings, semantic=semantic)
    console.print(f"[green]wrote[/green] {out}")


# ------------------------------------------------------------------------------- llm
@llm_app.command("ping")
def llm_ping(model: str = typer.Option(None), yes: bool = typer.Option(False, "--yes"), root: Path = ROOT_OPT):
    """One ~50-token call: confirms the endpoint, response schema and usage fields."""
    from uyari.llm.client import ping

    console.print_json(json.dumps(ping(_paths(root), model, assume_yes=yes), ensure_ascii=False))


@llm_app.command("spend")
def llm_spend(root: Path = ROOT_OPT):
    from uyari.llm.ledger import Ledger

    console.print_json(json.dumps(Ledger(_paths(root)).summary()))


# ------------------------------------------------------------------------------- agents
@app.command()
def gatekeeper(contribution: Path = typer.Option(...),
               llm: str = typer.Option("glimmer-local", help="Model for the written review."),
               no_llm: bool = typer.Option(False, "--no-llm"),
               out: Path = typer.Option(None, help="Write the review markdown here."),
               root: Path = ROOT_OPT):
    """Gate 2: validator + langid + near-duplicates + nearest accepted pairs + Glimmer review (Spanish)."""
    from uyari.agents.gatekeeper.run import run_gatekeeper

    res = run_gatekeeper(_paths(root), contribution, llm=None if no_llm else llm, out=out)
    console.print(res.markdown)
    raise typer.Exit(0 if res.recommendation != "return" else 2)


@app.command()
def trainer(language: str = typer.Option("cbt_Latn"),
            open_pr: bool = typer.Option(False, help="Commit outputs to trainer/<tag> and open a PR."),
            force_build: bool = typer.Option(False), dry_run: bool = typer.Option(False),
            max_steps: int = typer.Option(None, help="Smoke runs only."),
            root: Path = ROOT_OPT):
    """build -> train -> eval -> promote -> card -> NEEDS.md (-> PR)."""
    from uyari.agents.trainer.run import run_trainer

    res = run_trainer(_paths(root), language, open_pr=open_pr, force_build=force_build, dry_run=dry_run,
                      max_steps=max_steps)
    console.print_json(json.dumps(res, ensure_ascii=False, default=str))


@app.command()
def register(model: str = typer.Option(..., help="models/<name>@vX.Y"),
             slot: str = typer.Option(None, help="promoted (the demo default) or fast (the demo's second choice). "
                                               "Default: promoted for Glimmer (QLoRA), fast for NLLB."),
             test: bool = typer.Option(True, "--test/--no-test", help="Score test once when registered."),
             force: bool = typer.Option(False, help="Register even if the rule says no. Needs --reason."),
             reason: str = typer.Option("", help="Written to models/registry.yaml with the numbers."),
             root: Path = ROOT_OPT):
    """The Trainer's promotion rule for a model trained by hand: beats the floor in every direction and the
    slot's incumbent; then test once, models/registry.yaml and the model card. Exit code 3 if not registered."""
    from uyari.agents.trainer.run import register_model

    try:
        res = register_model(_paths(root), model, slot=slot, score_test=test, force=force, reason=reason)
    except ValueError as e:
        _fail(str(e))
    console.print_json(json.dumps(res, ensure_ascii=False, default=str))
    color = {"registered": "green", "already registered": "green"}.get(res["decision"], "yellow")
    console.print(f"[{color}]{res['decision']}[/{color}] {res['model']} ({res['slot']}): {res['why']}")
    if res["decision"] == "not registered":
        raise typer.Exit(3)


@app.command()
def needs(language: str = typer.Option("cbt_Latn"), tag: str = typer.Option(None), root: Path = ROOT_OPT):
    """Write languages/<lang>/NEEDS.md from the latest build manifest."""
    from uyari.agents.trainer.needs import write_needs

    console.print(write_needs(_paths(root), language, tag))


# ------------------------------------------------------------------------------- serving + demo
@serve_app.command("start")
def serve_start(adapter: list[str] = typer.Option(None, help="name=path LoRA adapters to expose."),
                backend: str = typer.Option("auto", help="auto | vllm | llama"),
                gguf: Path = typer.Option(None), port: int = typer.Option(8011), root: Path = ROOT_OPT):
    from uyari.serve import start

    console.print_json(json.dumps(start(_paths(root), adapters=adapter or [], backend=backend, gguf=gguf,
                                        port=port)))


@serve_app.command("stop")
def serve_stop(root: Path = ROOT_OPT):
    from uyari.serve import stop

    console.print(stop(_paths(root)))


@serve_app.command("status")
def serve_status(root: Path = ROOT_OPT):
    from uyari.serve import status

    console.print_json(json.dumps(status(_paths(root))))


@app.command()
def demo(share: bool = typer.Option(True, help="Also open a temporary public gradio.live link."),
         voice: bool = typer.Option(True, help="Voice input, paid with the visitor's own Meta key."),
         port: int = typer.Option(7860), root: Path = ROOT_OPT):
    """Gradio page: Shawi <-> Spanish, English, French, German, Italian and Portuguese (Shawi always on one side)
    with our fine-tuned models (Glimmer through `uyari serve` by default, NLLB as the second choice), the three
    closest human pairs, Shawi read aloud by the local MMS voice; optional voice input (Spanish, English, French,
    Portuguese) with the visitor's own Meta API key (the server's key is never used)."""
    sys.path.insert(0, str(_paths(root).code / "demo"))
    from app import launch  # demo/app.py

    launch(_paths(root), share=share, voice=voice, port=port)


@report_app.command("side-by-side")
def report_sbs(n: int = typer.Option(20), models: list[str] = typer.Option(None),
               root: Path = ROOT_OPT):
    from uyari.report.side_by_side import run_side_by_side

    console.print(f"[green]wrote[/green] {run_side_by_side(_paths(root), n=n, models=models or None)}")


# ------------------------------------------------------------------------------- speech
@app.command()
def transcribe(audio: Path, estimate: bool = typer.Option(False), yes: bool = typer.Option(False, "--yes"),
               root: Path = ROOT_OPT):
    """Spanish speech -> text with Muse Voice Transcribe (official language only)."""
    from uyari.speech.transcribe import transcribe_file

    console.print_json(json.dumps(transcribe_file(_paths(root), audio, estimate_only=estimate, assume_yes=yes),
                                  ensure_ascii=False))


@asr_app.command("infer")
def asr_infer(audio: Path, lang: str = typer.Option("spa_Latn"), backend: str = typer.Option("mms")):
    from uyari.pipelines.asr.infer import infer_file

    console.print(infer_file(audio, lang, backend=backend))


@asr_app.command("eval")
def asr_eval(tag: str = typer.Option(...), lang: str = typer.Option(...), backend: str = typer.Option("mms"),
             split: str = typer.Option("validation"), root: Path = ROOT_OPT):
    from uyari.pipelines.asr.eval import run_asr_eval

    console.print_json(json.dumps(run_asr_eval(_paths(root), tag, lang, backend=backend, split=split)))


@tts_app.command("check-voice")
def tts_check_voice(iso: str = typer.Argument("cbt"), root: Path = ROOT_OPT):
    """Does an MMS-TTS voice exist for this language, and does its alphabet cover our accepted text (before and
    after the spelling converter in languages/<lang>/tts.yaml)?"""
    from uyari.data.languages import list_languages
    from uyari.pipelines.tts.check_voice import accepted_texts, check_voice
    from uyari.pipelines.tts.voice import load_config

    p = _paths(root)
    lang = next((x for x in list_languages(p) if x.startswith(iso + "_")), None)
    cfg = load_config(p, lang) if lang else None
    res = check_voice(iso, accepted_texts(p, lang, limit=None) if lang else None, cfg)
    console.print_json(json.dumps(res, ensure_ascii=False))
    if "letter_coverage" in res:
        def left(m):
            return ", ".join(f"{c} {n}" for c, n in m.items()) or "none"
        before = res.get("before_conversion")
        if before:
            console.print(f"{res['repo']}: {before['letter_coverage']:.2%} of {before['letters']:,} letters as written "
                          f"(cannot read: {left(before['missing_letters'])}); {res['letter_coverage']:.2%} after "
                          f"{res['converter']} (cannot read: {left(res['missing_letters'])}).")
        else:
            console.print(f"{res['repo']}: {res['letter_coverage']:.2%} of {res['letters']:,} letters "
                          f"(cannot read: {left(res['missing_letters'])}).")
        color = "green" if res["usable"] else "red"
        console.print(f"[{color}]{'usable' if res['usable'] else 'not usable'}[/{color}]")


@app.command()
def s2s(audio: Path, src: str = typer.Option("spa_Latn"), tgt: str = typer.Option("cbt_Latn"),
        model: str = typer.Option(None), out: Path = typer.Option(None),
        yes: bool = typer.Option(False, "--yes", help="Do not ask before the paid transcription."),
        root: Path = ROOT_OPT):
    """Speech -> text -> translation -> speech (Shawi through the MMS voice and its spelling converter; text
    output when no usable voice exists)."""
    from uyari.pipelines.s2s.chain import run_chain

    console.print_json(json.dumps(run_chain(_paths(root), audio, src, tgt, model=model, out=out, assume_yes=yes),
                                  ensure_ascii=False))


# ------------------------------------------------------------------------------- privacy
@app.command("privacy-check")
def privacy_check(root: Path = ROOT_OPT):
    """Fail if any publishable file contains a name from the private name list."""
    from uyari.privacy import run_privacy_check

    res = run_privacy_check(_paths(root))
    for f in res.findings:
        console.print(f"[red]{f}[/red]")
    console.print(res.summary)
    raise typer.Exit(0 if res.ok else 1)


# ------------------------------------------------------------------------------- publish
@app.command("publish")
def publish(model: str = typer.Option(..., help="models/<name>@vX.Y"),
            namespace: str = typer.Option(None, help="Hugging Face user or organization (default: HF_TOKEN's user)."),
            private: bool = typer.Option(True, "--private/--public", help="Visibility when the repository is created; "
                                                                           "an existing repository keeps its own."),
            dry_run: bool = typer.Option(False, "--dry-run", help="Write runs/hub/<repo>/README.md and list the "
                                                                    "files; upload nothing."),
            root: Path = ROOT_OPT):
    """Publish a model to Hugging Face: weights or adapter, and a README generated from its card, scores and
    build (usage, test scores, license, limitations; the rest is linked to GitHub). One commit, tagged vX.Y."""
    from uyari.pipelines.mt.hub import publish as run_publish

    res = run_publish(_paths(root), model, namespace=namespace, private=private, dry_run=dry_run)
    if res["links_not_on_origin_main"]:
        console.print("[yellow]README links that resolve only after a push to origin/main:[/yellow] "
                      + ", ".join(res["links_not_on_origin_main"]))
    console.print_json(json.dumps(res, ensure_ascii=False))


@primary_app.command("translate")
def primary_translate(batch: str = typer.Option(..., help="Output batch id, e.g. 2026-11_musespark13c_0001"),
                      source: str = typer.Option("spa_Latn"), target: str = typer.Option("eng_Latn"),
                      model: str = typer.Option(None, help="Default: the official-language model in config/llm.yaml."),
                      only_translated_in: str = typer.Option(None, help="Only chunks already translated into this "
                                                                         "language (e.g. cbt_Latn)."),
                      limit: int = typer.Option(None, help="First N chunks only (a canary)."),
                      source_batch: str = typer.Option(None, help="Only chunks whose source_batch_id is this "
                                                                    "(e.g. a new generation batch)."),
                      per_request: int = typer.Option(20), concurrency: int = typer.Option(8),
                      estimate: bool = typer.Option(False, help="Cost table only, no network."),
                      max_usd: float = typer.Option(None), yes: bool = typer.Option(False, "--yes"),
                      root: Path = ROOT_OPT):
    """A second primary corpus (e.g. English), machine-translated from the first, same chunk ids."""
    from uyari.gen.translate_primary import run_translate

    res = run_translate(_paths(root), batch, source, target, model, only_translated_in, limit, per_request,
                        estimate, max_usd, yes, concurrency, console=console, source_batch=source_batch)
    if not estimate:
        console.print_json(json.dumps(res, ensure_ascii=False))


@primary_app.command("sample")
def primary_sample(batch: str = typer.Option(...), pct: float = typer.Option(2.0), lang: str = "spa_Latn",
                   root: Path = ROOT_OPT):
    """Export a random pct% of a batch for the human spot read (reports/spot/<batch>.xlsx)."""
    from uyari.gen.spot import export_spot

    console.print(f"[green]wrote[/green] {export_spot(_paths(root), lang, batch, pct)}")


@primary_app.command("deprecate")
def primary_deprecate(chunk_ids: list[str], lang: str = "spa_Latn", root: Path = ROOT_OPT):
    """Mark chunks deprecated (never edited, never deleted; translations keep pointing at them)."""
    from uyari.data.primary import load_primary, rewrite_files

    p = _paths(root)
    pc = load_primary(p, lang)
    for c in chunk_ids:
        if c not in pc.chunks:
            _fail(f"unknown chunk {c}")
        pc.chunks[c]["status"] = "deprecated"
    rewrite_files(pc)
    console.print(f"deprecated {len(chunk_ids)} chunk(s)")


if __name__ == "__main__":
    app()
