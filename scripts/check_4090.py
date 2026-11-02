#!/usr/bin/env python3
"""Uyari GPU environment check for the Ubuntu RTX 4090 box.

Standalone: imports nothing from the Uyari package, so it can run before the
repository is cloned. Run it inside the venv created by ``scripts/setup_ubuntu.sh``.

Each step prints PASS/FAIL/SKIP with its duration; a JSON summary is written to
``check_4090_report.json`` at the end. A failing step never stops later steps.

Steps
  env       driver, CUDA, VRAM, free disk where the Hugging Face cache lives
  download  Muse Glimmer, NLLB-200 1.3B, omniASR-CTC-1B (hours on a slow link)
  unsloth   load Glimmer in 4-bit, 10-step QLoRA on dummy data, peak VRAM
  nllb      translate one sentence with NLLB-200 1.3B
  server    start vLLM (or llama-server) with Glimmer and answer one chat request
  gradio    hello-world with share=True; prints the public link to open on a phone

Usage
  python scripts/check_4090.py                       # all steps
  python scripts/check_4090.py --steps env,unsloth   # subset
  python scripts/check_4090.py --glimmer-id meta-models/Muse-Glimmer-30B
  python scripts/check_4090.py --skip-download       # weights already in the cache
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import urllib.request
from pathlib import Path

DEFAULT_GLIMMER = "meta-models/Muse-Glimmer-30B"
DEFAULT_NLLB = "facebook/nllb-200-distilled-1.3B"
DEFAULT_OMNIASR = "facebook/omniASR-CTC-1B"
GLIMMER_BF16_GB = 58

RESULTS: list[dict] = []


def step(name: str):
    """Decorator: time a step, catch every exception, record PASS/FAIL/SKIP."""

    def wrap(fn):
        def run(args):
            if name not in args.steps:
                return
            print(f"\n=== {name} ===", flush=True)
            t0 = time.time()
            status, detail = "PASS", {}
            try:
                detail = fn(args) or {}
                if detail.get("_skip"):
                    status = "SKIP"
            except Exception as exc:  # noqa: BLE001 - a check must never crash the run
                status = "FAIL"
                detail = {"error": f"{type(exc).__name__}: {exc}", "trace": traceback.format_exc(limit=3)}
            dt = round(time.time() - t0, 1)
            detail.pop("_skip", None)
            RESULTS.append({"step": name, "status": status, "seconds": dt, **detail})
            print(f"--> {name}: {status} ({dt}s) {json.dumps({k: v for k, v in detail.items() if k != 'trace'}, ensure_ascii=False)}", flush=True)

        return run

    return wrap


def hf_cache_dir() -> Path:
    return Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface"))


@step("env")
def check_env(args) -> dict:
    out: dict = {"python": sys.version.split()[0]}
    smi = shutil.which("nvidia-smi")
    if not smi:
        raise RuntimeError("nvidia-smi not found: install the NVIDIA driver first")
    q = subprocess.run(
        [smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
        capture_output=True, text=True, check=True,
    )
    out["gpu"] = q.stdout.strip()
    import torch

    out["torch"] = torch.__version__
    out["torch_cuda"] = torch.version.cuda
    out["cuda_available"] = torch.cuda.is_available()
    if not torch.cuda.is_available():
        raise RuntimeError("torch cannot see the GPU (CPU-only wheel or driver/CUDA mismatch)")
    props = torch.cuda.get_device_properties(0)
    out["vram_gib"] = round(props.total_memory / 2**30, 1)
    out["bf16"] = torch.cuda.is_bf16_supported()
    cache = hf_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    free_gb = shutil.disk_usage(cache).free / 1e9
    out["hf_cache"] = str(cache)
    out["free_disk_gb"] = round(free_gb, 1)
    if free_gb < GLIMMER_BF16_GB + 20:
        out["warning"] = f"less than {GLIMMER_BF16_GB + 20} GB free; Glimmer BF16 alone is ~{GLIMMER_BF16_GB} GB"
    return out


@step("download")
def check_download(args) -> dict:
    if args.skip_download:
        return {"_skip": True, "reason": "--skip-download"}
    from huggingface_hub import snapshot_download

    out = {}
    for repo in [args.glimmer_id, args.nllb_id, args.omniasr_id]:
        t0 = time.time()
        try:
            path = snapshot_download(repo_id=repo)
            size = sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file()) / 1e9
            out[repo] = {"ok": True, "gb": round(size, 1), "seconds": round(time.time() - t0)}
        except Exception as exc:  # noqa: BLE001
            out[repo] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    if not out[args.glimmer_id]["ok"]:
        raise RuntimeError(f"Glimmer download failed: {out[args.glimmer_id]['error']} "
                           "(check the repo id, `huggingface-cli login`, and the license gate)")
    return out


@step("unsloth")
def check_unsloth(args) -> dict:
    """Same loading path as recipes/cbt-spa.mt.glimmer-qlora.yaml: Glimmer is image-text-to-text, so
    Unsloth's multimodal-aware FastModel, 4-bit, LoRA on the language layers, vision frozen; then 10
    optimizer steps at max length 512 (batch 1) on chat-formatted dummy pairs, loss on the answer only."""
    try:
        from unsloth import FastModel as Fast  # import before transformers, as Unsloth requires
        generic = True
    except ImportError:
        from unsloth import FastLanguageModel as Fast
        generic = False
    import torch

    torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    model, proc = Fast.from_pretrained(model_name=args.glimmer_id, max_seq_length=512, load_in_4bit=True, dtype=None)
    load_s = round(time.time() - t0, 1)
    kw = {"r": 16, "lora_alpha": 32, "lora_dropout": 0.0, "bias": "none", "random_state": 7,
          "use_gradient_checkpointing": "unsloth"}
    if generic:
        kw.update(finetune_vision_layers=False, finetune_language_layers=True,
                  finetune_attention_modules=True, finetune_mlp_modules=True)
    else:
        kw["target_modules"] = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    model = Fast.get_peft_model(model, **kw)
    tok = getattr(proc, "tokenizer", proc)
    multimodal = tok is not proc
    tmpl = proc if getattr(proc, "chat_template", None) else tok

    def chat(msgs, gen):
        if multimodal:
            msgs = [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in msgs]
        return tmpl.apply_chat_template(msgs, add_generation_prompt=gen, tokenize=False, reasoning_strength="low")

    def ids(text):
        return tok(text, add_special_tokens=False)["input_ids"]

    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)
    model.train()
    losses = []
    for i in range(10):
        p = [{"role": "user", "content": f"Traduce del español al shawi:\nFrase de prueba número {i}."}]
        full = chat(p + [{"role": "assistant", "content": f"prueba {i}"}], False)
        p_txt = chat(p, True)
        p_ids, c_ids = ids(p_txt), ids(full[len(p_txt):]) if full.startswith(p_txt) else ids(f"prueba {i}")
        x = torch.tensor([p_ids + c_ids], device="cuda")
        y = torch.tensor([[-100] * len(p_ids) + c_ids], device="cuda")
        with torch.autocast("cuda", dtype=torch.bfloat16):
            loss = model(input_ids=x, labels=y).loss
        loss.backward()
        opt.step()
        opt.zero_grad(set_to_none=True)
        losses.append(round(loss.item(), 4))
    peak = torch.cuda.max_memory_reserved() / 2**30
    Fast.for_inference(model)
    q = torch.tensor([ids(chat([{"role": "user", "content": "Di hola en una palabra."}], True))], device="cuda")
    gen = model.generate(input_ids=q, max_new_tokens=24)
    reply = tok.decode(gen[0][q.shape[1]:], skip_special_tokens=False)
    del model, opt
    torch.cuda.empty_cache()
    return {"loader": "FastModel" if generic else "FastLanguageModel", "multimodal_processor": multimodal,
            "load_seconds": load_s, "losses": losses, "peak_vram_gib": round(peak, 2),
            "raw_reply": reply.strip()[:80]}


@step("nllb")
def check_nllb(args) -> dict:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(args.nllb_id, src_lang="spa_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(args.nllb_id, torch_dtype=torch.bfloat16).to("cuda")
    batch = tok(["El niño tiene fiebre desde ayer."], return_tensors="pt").to("cuda")
    out = model.generate(**batch, forced_bos_token_id=tok.convert_tokens_to_ids("eng_Latn"), max_new_tokens=40)
    text = tok.batch_decode(out, skip_special_tokens=True)[0]
    apostrophe_ok = tok.unk_token_id not in tok("ipiʼ")["input_ids"]
    del model
    torch.cuda.empty_cache()
    return {"spa_to_eng": text, "tokenizer_knows_U+02BC": apostrophe_ok}


def _wait_http(url: str, timeout_s: int) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:  # noqa: S310 - localhost only
                if r.status == 200:
                    return True
        except Exception:  # noqa: BLE001
            time.sleep(5)
    return False


def _chat(port: int, model: str) -> str:
    body = json.dumps({"model": model, "max_tokens": 16,
                       "messages": [{"role": "user", "content": "Responde solo: hola"}]}).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:  # noqa: S310 - localhost only
        return json.loads(r.read())["choices"][0]["message"]["content"]


@step("server")
def check_server(args) -> dict:
    port = args.port
    attempts = []
    vllm = shutil.which("vllm")
    if vllm:
        cmd = [vllm, "serve", args.glimmer_id, "--port", str(port), "--max-model-len", "2048",
               "--quantization", "bitsandbytes", "--gpu-memory-utilization", "0.92",
               "--enable-lora", "--max-lora-rank", "16"]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        try:
            if _wait_http(f"http://127.0.0.1:{port}/v1/models", args.server_timeout):
                reply = _chat(port, args.glimmer_id)
                return {"backend": "vllm", "reply": reply.strip()[:60], "cmd": " ".join(cmd)}
            attempts.append({"backend": "vllm", "error": "did not become ready",
                             "stderr_tail": (proc.stderr.read() if proc.poll() is not None else "")[-800:]})
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
    else:
        attempts.append({"backend": "vllm", "error": "`vllm` not on PATH (uv tool install vllm)"})

    llama = shutil.which("llama-server")
    if llama and args.gguf:
        cmd = [llama, "-m", args.gguf, "--port", str(port), "-ngl", "999", "-c", "2048"]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            if _wait_http(f"http://127.0.0.1:{port}/v1/models", args.server_timeout):
                return {"backend": "llama-server", "reply": _chat(port, "glimmer").strip()[:60],
                        "cmd": " ".join(cmd), "vllm_attempt": attempts}
            attempts.append({"backend": "llama-server", "error": "did not become ready"})
        finally:
            proc.terminate()
    else:
        attempts.append({"backend": "llama-server", "error": "not on PATH or --gguf not given"})
    raise RuntimeError(json.dumps(attempts, ensure_ascii=False))


@step("gradio")
def check_gradio(args) -> dict:
    import gradio as gr

    demo = gr.Interface(fn=lambda s: f"Uyari check OK: {s}", inputs="text", outputs="text",
                        title="Uyari 4090 check")
    _, local_url, share_url = demo.launch(share=True, prevent_thread_lock=True)
    print(f"\n    Open on a phone within {args.gradio_wait}s: {share_url}\n", flush=True)
    time.sleep(args.gradio_wait)
    demo.close()
    if not share_url:
        raise RuntimeError("no share link (outbound connection to gradio.live blocked?)")
    return {"local_url": local_url, "share_url": share_url}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", default="env,download,unsloth,nllb,server,gradio")
    ap.add_argument("--glimmer-id", default=DEFAULT_GLIMMER)
    ap.add_argument("--nllb-id", default=DEFAULT_NLLB)
    ap.add_argument("--omniasr-id", default=DEFAULT_OMNIASR)
    ap.add_argument("--skip-download", action="store_true")
    ap.add_argument("--gguf", default="", help="GGUF path for the llama-server fallback")
    ap.add_argument("--port", type=int, default=8011)
    ap.add_argument("--server-timeout", type=int, default=900, help="seconds to wait for the server")
    ap.add_argument("--gradio-wait", type=int, default=60)
    ap.add_argument("--report", default="check_4090_report.json")
    args = ap.parse_args()
    args.steps = set(s.strip() for s in args.steps.split(",") if s.strip())

    for fn in (check_env, check_download, check_unsloth, check_nllb, check_server, check_gradio):
        fn(args)

    Path(args.report).write_text(json.dumps(RESULTS, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n=== SUMMARY ===")
    for r in RESULTS:
        print(f"  {r['status']:<4}  {r['step']:<9} {r['seconds']:>8}s")
    print(f"Report: {args.report}")
    return 0 if all(r["status"] != "FAIL" for r in RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
