"""``uyari serve``: one local OpenAI-compatible server for Muse Glimmer on the 4090.

The base model answers the Gatekeeper; LoRA adapters (``name=path``) answer the demo and
``uyari eval``. One copy of the model sits in VRAM. Backend: llama-server with a GGUF of the base (Unsloth's
4-bit ``Muse-Glimmer-30B-UD-Q4_K_XL``, 15 GB, from the Hugging Face cache or ``GLIMMER_GGUF``) and each
adapter's ``adapter.gguf`` (``scripts/lora_to_gguf.py``); vLLM otherwise. vLLM cannot load the 4-bit
checkpoint (it rejects bitsandbytes), so ``auto`` takes llama-server whenever a GGUF is there.

``gpu_session()`` is the GPU lock the Trainer takes: it stops the server around a GPU job and
restarts it afterwards, so serving and training never fight for the 24 GB.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

from uyari.paths import Paths


class GpuBusy(RuntimeError):
    pass


def _state(paths: Paths) -> Path:
    return paths.state / "serve.json"


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
        return str(pid) in out.stdout
    try:  # a server this process started and that has exited is a zombie until reaped: reap it, it is gone
        if os.waitpid(pid, os.WNOHANG)[0] == pid:
            return False
    except ChildProcessError:  # not our child
        pass
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _kill(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        return
    with contextlib.suppress(OSError):
        os.killpg(pid, signal.SIGTERM)
    for _ in range(30):
        if not _alive(pid):
            return
        time.sleep(1)
    with contextlib.suppress(OSError):
        os.killpg(pid, signal.SIGKILL)


def _ready(port: int) -> bool:
    import httpx

    try:
        return httpx.get(f"http://127.0.0.1:{port}/v1/models", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


GGUF_REPO, GGUF_FILE = "unsloth/Muse-Glimmer-30B-GGUF", "Muse-Glimmer-30B-UD-Q4_K_XL.gguf"


def default_gguf() -> Path | None:
    """``GLIMMER_GGUF``, else Unsloth's 4-bit GGUF if it is in the Hugging Face cache (never downloaded here)."""
    env = os.environ.get("GLIMMER_GGUF")
    if env:
        return Path(env)
    try:
        from huggingface_hub import try_to_load_from_cache
    except ImportError:
        return None
    f = try_to_load_from_cache(GGUF_REPO, GGUF_FILE)
    return Path(f) if isinstance(f, str) else None


def gguf_lora(adapter_dir: str | Path) -> Path:
    """The GGUF form of a PEFT adapter folder, as llama-server loads it."""
    f = Path(adapter_dir) / "adapter.gguf"
    if not f.is_file():
        raise RuntimeError(f"{f} missing: run `uv run --no-sync python scripts/lora_to_gguf.py {adapter_dir}`")
    return f


def default_adapters(paths: Paths) -> list[str]:
    """``name=path`` for every causal LoRA model registered in models/registry.yaml."""
    from uyari.pipelines.mt.common import read_meta
    from uyari.registry import load

    out = []
    for _lang, slots in (load(paths).get("mt") or {}).items():
        for slot in ("promoted", "fast"):
            ref = slots.get(slot)
            d = paths.models / ref if ref else None
            if d and (d / "uyari_meta.json").is_file():
                meta = read_meta(d)
                name = (meta.get("eval") or {}).get("server_adapter")
                if meta["kind"] == "causal_lora" and name:
                    out.append(f"{name}={d / meta.get('adapter', 'adapter')}")
    return sorted(set(out))


def status(paths: Paths) -> dict:
    s = json.loads(_state(paths).read_text(encoding="utf-8")) if _state(paths).is_file() else {}
    if s:
        s["alive"] = _alive(int(s.get("pid", 0)))
        s["ready"] = _ready(int(s.get("port", 8011)))
    return s or {"running": False}


def start(paths: Paths, adapters: list[str] | None = None, backend: str = "auto", gguf: Path | None = None,
          port: int = 8011, wait_s: int = 900) -> dict:
    st = status(paths)
    if st.get("alive"):
        return {**st, "note": "already running"}
    base = os.environ.get("GLIMMER_MODEL_ID", "meta-models/Muse-Glimmer-30B")
    adapters = adapters or default_adapters(paths)
    log = paths.state / "serve.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd: list[str] = []
    gguf = gguf or default_gguf()
    if backend == "auto":
        backend = "llama" if gguf and shutil.which("llama-server") else "vllm"
    if backend == "vllm" and shutil.which("vllm"):
        backend = "vllm"
        cmd = [shutil.which("vllm"), "serve", base, "--port", str(port), "--max-model-len", "2048",
               "--quantization", "bitsandbytes", "--gpu-memory-utilization", "0.90"]
        if adapters:
            cmd += ["--enable-lora", "--max-lora-rank", "16", "--lora-modules", *adapters]
    elif backend == "llama" and shutil.which("llama-server"):
        if not gguf:
            raise RuntimeError("llama-server needs --gguf (Glimmer converted to GGUF)")
        # 8 slots of 1,024 tokens: a translation prompt is about 100 tokens plus at most 256 generated, and
        # `uyari eval` sends 8 at a time. One adapter at a time: llama-server applies every --lora to every request.
        cmd = [shutil.which("llama-server"), "-m", str(gguf), "--port", str(port), "-ngl", "999", "-c", "8192",
               "-np", "8"]
        if len(adapters) > 1:
            raise RuntimeError(f"llama-server applies every adapter to every request; start one of {adapters}")
        for a in adapters:
            cmd += ["--lora", str(gguf_lora(a.split("=", 1)[1]).resolve())]
    else:
        raise RuntimeError("no server backend: `uv tool install vllm` (Linux) or put llama-server on PATH")
    kw = {"start_new_session": True} if sys.platform != "win32" else {
        "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}  # type: ignore[attr-defined]
    with log.open("ab") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, **kw)
    state = {"pid": proc.pid, "backend": backend, "port": port, "base": base, "adapters": adapters,
             "cmd": cmd, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}
    _state(paths).write_text(json.dumps(state, indent=2), encoding="utf-8")
    t0 = time.time()
    while time.time() - t0 < wait_s:
        if _ready(port):
            return {**state, "ready": True, "seconds": round(time.time() - t0)}
        if proc.poll() is not None:
            raise RuntimeError(f"server exited ({proc.returncode}); see {log}")
        time.sleep(5)
    return {**state, "ready": False, "note": f"not ready after {wait_s}s; see {log}"}


def stop(paths: Paths) -> str:
    st = status(paths)
    if not st.get("pid"):
        return "not running"
    _kill(int(st["pid"]))
    _state(paths).unlink(missing_ok=True)
    return f"stopped pid {st['pid']}"


@contextlib.contextmanager
def gpu_session(paths: Paths, reason: str, restart_server: bool = True):
    """Exclusive GPU use: lock file + stop the server for the duration, restart it after."""
    lock = paths.state / "gpu.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        try:
            other = json.loads(lock.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            other = {}
        if _alive(int(other.get("pid", 0))):
            raise GpuBusy(f"GPU busy: {other.get('reason')} (pid {other.get('pid')})")
        lock.unlink(missing_ok=True)
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"pid": os.getpid(), "reason": reason, "at": time.strftime("%Y-%m-%dT%H:%M:%S")}, f)
    was = status(paths)
    if was.get("alive"):
        stop(paths)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)
        if restart_server and was.get("alive"):
            start(paths, adapters=default_adapters(paths) or was.get("adapters"), backend=was.get("backend", "auto"),
                  port=int(was.get("port", 8011)), wait_s=5)
