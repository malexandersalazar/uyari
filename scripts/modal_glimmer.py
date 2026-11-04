"""Train Muse Glimmer 30B QLoRA on a Modal H100 80 GB: the same code and recipe as `make train-glimmer`.

The 4-bit model does not fit the 24 GB 4090 for training (check_4090_report.json), so only training runs here;
evaluation, registration and serving stay on the 4090 (GGUF + LoRA with llama-server).

    uv run --no-sync modal run scripts/modal_glimmer.py --step download   # base model into a Volume (CPU only)
    uv run --no-sync modal run scripts/modal_glimmer.py --step smoke      # 20 steps: memory, seconds per step
    uv run --no-sync modal run --detach scripts/modal_glimmer.py --step train
    uv run --no-sync modal run scripts/modal_glimmer.py --step score      # validation of the model as trained
    uv run --no-sync modal volume get uyari-glimmer root/models/<model> models/     # <model>: the recipe output
    uv run --no-sync modal volume get uyari-glimmer root/runs/cbt.mt.glimmer-qlora/train_log.jsonl \
        runs/cbt.mt.glimmer-qlora/

What leaves this machine: the code, the recipe, and the prepared train and validation examples
(runs/cbt.mt.glimmer-qlora/data, from `uyari prepare`). The build's test split is never uploaded
(docs/decisions/0010-training-on-rented-gpus.md). Run `uyari prepare --recipe recipes/cbt.mt.glimmer-qlora.yaml`
first.
"""

from __future__ import annotations

from pathlib import Path

import modal

REPO = Path(__file__).resolve().parents[1]
RECIPE = "recipes/cbt.mt.glimmer-qlora-r64.yaml"  # the served model's; --recipe for another
BASE = "meta-models/Muse-Glimmer-30B"
BASE_4BIT = "unsloth/Muse-Glimmer-30B-unsloth-bnb-4bit"  # what Unsloth loads for BASE in 4-bit
GPU = "H100!"  # "!": never silently upgraded, so the measured speed and price are the H100's
HOURS = 6  # hard stop for the full run: about US$ 24 at most

app = modal.App("uyari-glimmer")
runs = modal.Volume.from_name("uyari-glimmer", create_if_missing=True)  # /vol: <root>/runs, <root>/models
hf_cache = modal.Volume.from_name("uyari-hf-cache", create_if_missing=True)  # /hf: Hugging Face cache

# The versions of the 4090's project environment (uv pip list), so both run the same stack.
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("build-essential", "git")  # Triton and Unsloth compile kernels at run time
    .uv_pip_install(
        "torch==2.14.1", "torchvision==0.29.2", "triton==3.8.0", "xformers==0.0.35",
        "transformers==5.17.0", "peft==0.21.2", "trl==1.15.0", "accelerate==1.15.0", "bitsandbytes==0.50.2",
        "datasets==4.8.5", "sentencepiece==0.2.2", "protobuf==7.36.2", "safetensors==0.8.0",
        "tokenizers==0.23.3", "huggingface-hub==1.33.0", "hf-xet==1.8.0",
        "unsloth==2026.10.11", "unsloth-zoo==2026.10.11",
        # uyari's own dependencies (pyproject.toml), as far as training imports them
        "numpy==2.5.4", "pandas==3.1.0", "pyarrow==26.0.0", "pyyaml>=6.0", "jsonschema>=4.21", "typer>=0.12",
        "rich>=13", "python-dotenv>=1.0", "httpx>=0.27", "sacrebleu==2.6.0", "scikit-learn>=1.4",
    )
    .env({"HF_HOME": "/hf", "UYARI_ROOT": "/repo", "PYTHONUNBUFFERED": "1", "HF_XET_HIGH_PERFORMANCE": "1",
          "TOKENIZERS_PARALLELISM": "false"})
    .workdir("/tmp")  # Unsloth writes its compiled cache to the working directory
    .add_local_python_source("uyari")
    .add_local_dir(REPO / "schemas", "/repo/schemas")
    .add_local_dir(REPO / "config", "/repo/config")
    .add_local_dir(REPO / "recipes", "/repo/recipes")
    .add_local_file(REPO / "pyproject.toml", "/repo/pyproject.toml")
)


@app.function(image=image, volumes={"/hf": hf_cache}, timeout=3600, cpu=4, memory=8192)
def download() -> dict:
    """The 4-bit base (about 21 GB) and the original's config and tokenizer, once, without paying for a GPU."""
    import time

    from huggingface_hub import snapshot_download

    t0 = time.time()
    a = snapshot_download(BASE_4BIT)
    b = snapshot_download(BASE, allow_patterns=["*.json", "*.jinja", "*.md", "LICENSE"])
    hf_cache.commit()
    size = sum(f.stat().st_size for f in Path(a).rglob("*") if f.is_file()) / 1e9
    return {"base_4bit": a, "base_config": b, "gb": round(size, 1), "seconds": round(time.time() - t0)}


@app.function(image=image, gpu=GPU, volumes={"/vol": runs, "/hf": hf_cache}, timeout=HOURS * 3600)
def train(root: str = "/vol/root", max_steps: int | None = None, recipe: str = RECIPE) -> dict:
    """``run_train`` on the uploaded examples. The Volume is committed every 10 minutes, so an interrupted run
    keeps its log and the adapter of its best epoch so far."""
    import subprocess
    import threading
    import time

    import torch
    import unsloth  # noqa: F401  first, before transformers and peft, or it runs without its optimizations

    from uyari.paths import Paths
    from uyari.pipelines.mt.train import run_train

    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
                         capture_output=True, text=True).stdout.strip()
    print(f"gpu: {gpu} | torch {torch.__version__} cuda {torch.version.cuda} available {torch.cuda.is_available()}",
          flush=True)
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available in the container")
    stop = threading.Event()

    def commit_every_10_min():
        while not stop.wait(600):
            runs.commit()

    threading.Thread(target=commit_every_10_min, daemon=True).start()
    t0 = time.time()
    try:
        out = run_train(Paths(code=Path("/repo"), data=Path(root)), f"/repo/{recipe}", max_steps=max_steps)
    finally:
        stop.set()
        runs.commit()
    return {"gpu": gpu, "output": str(out), "seconds": round(time.time() - t0),
            "peak_vram_gib": round(torch.cuda.max_memory_reserved() / 2**30, 1)}


@app.function(image=image, gpu=GPU, volumes={"/vol": runs, "/hf": hf_cache}, timeout=2 * 3600)
def score(name: str, build: str, lang: str) -> dict:
    """Validation chrF++ of the model as trained (4-bit base + adapter, in process), to compare with the served
    GGUF form scored on the 4090. Validation only: the test split is never uploaded."""
    import json
    import shutil

    import unsloth  # noqa: F401

    from uyari.paths import Paths
    from uyari.pipelines.mt.eval import run_eval

    src, dst = Path("/vol/root/models") / name, Path("/vol/check/models") / name
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("scores.json", "eval", "*.gguf"))
    meta = json.loads((dst / "uyari_meta.json").read_text(encoding="utf-8"))
    meta["eval"]["batch_size"] = 32  # scoring speed only: greedy decoding either way
    (dst / "uyari_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    if not (Path("/vol/check/builds") / build / lang / "mt.parquet").is_file():
        raise RuntimeError("upload the build's mt.parquet first (--step score does)")
    res = run_eval(Paths(code=Path("/repo"), data=Path("/vol/check")), str(dst), "validation")
    runs.commit()
    return res


def _data(recipe: str) -> str:
    from uyari.recipes import load_recipe

    return f"runs/{load_recipe(REPO / recipe).id}/data"


def _upload(root: str, recipe: str) -> None:
    """The prepared examples into the Volume under ``root`` (replacing what is there)."""
    data = _data(recipe)
    local = REPO / data
    if not (local / "train.jsonl").is_file():
        raise SystemExit(f"{local}/train.jsonl missing: run `uyari prepare --recipe {recipe}` first")
    with runs.batch_upload(force=True) as up:
        for name in ("train.jsonl", "validation.jsonl", "stats.json"):
            up.put_file(local / name, f"/{root}/{data}/{name}")


@app.local_entrypoint()
def main(step: str = "smoke", recipe: str = RECIPE):
    if step == "download":
        print(download.remote())
    elif step == "smoke":  # its own root, so its log and adapter never mix with the real run
        try:
            runs.remove_file("/smoke", recursive=True)
        except FileNotFoundError:
            pass
        _upload("smoke", recipe)
        print(train.remote(root="/vol/smoke", max_steps=20, recipe=recipe))
    elif step == "train":
        _upload("root", recipe)
        print(train.remote(root="/vol/root", recipe=recipe))
    elif step == "score":  # the build's train + validation table (mt.parquet; never mt.test.parquet)
        import json

        from uyari.recipes import load_recipe

        rc = load_recipe(REPO / recipe)
        table = f"builds/{rc.build}/{rc.language}/mt.parquet"
        with runs.batch_upload(force=True) as up:
            up.put_file(REPO / table, f"/check/{table}")
        res = score.remote(Path(rc.output).name, rc.build, rc.language)
        out = REPO / "runs" / rc.id / f"validation-in-process.{Path(rc.output).name}.json"
        out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        print({k: v["chrf++"] for k, v in res["validation"].items() if ">" in k}, "->", out)
    else:
        raise SystemExit("--step download | smoke | train | score")
