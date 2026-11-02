#!/usr/bin/env bash
# Uyari setup for the Ubuntu RTX 4090 box.
#
#   bash scripts/setup_ubuntu.sh check     # before cloning: a throwaway venv to run check_4090.py
#   bash scripts/setup_ubuntu.sh project   # inside the cloned repo: project venv + GPU extras
#
# Requires: NVIDIA driver already installed (nvidia-smi works). CUDA toolkit is NOT
# needed; PyTorch wheels on Linux ship their own CUDA runtime.
set -euo pipefail

MODE="${1:-project}"

if ! command -v nvidia-smi >/dev/null; then
  echo "nvidia-smi not found. Install the driver first: sudo ubuntu-drivers install && reboot" >&2
  exit 1
fi
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
uv python install 3.11

# vLLM lives in its own tool venv: its torch pin must not fight Unsloth's.
uv tool install --python 3.11 vllm || echo "WARN: vllm install failed; the check will try llama-server"

export PYTHONUTF8=1

case "$MODE" in
  check)
    VENV="${UYARI_CHECK_VENV:-$HOME/uyari-check-venv}"
    uv venv --python 3.11 "$VENV"
    # shellcheck disable=SC1091
    source "$VENV/bin/activate"
    uv pip install unsloth "trl" "datasets" "transformers" "accelerate" "bitsandbytes" \
      "sentencepiece" "huggingface_hub[hf_transfer]" "sacrebleu" "gradio"
    echo
    echo "Next:"
    echo "  source $VENV/bin/activate"
    echo "  huggingface-cli login            # if the Glimmer repo is gated"
    echo "  HF_HUB_ENABLE_HF_TRANSFER=1 python scripts/check_4090.py"
    ;;
  project)
    uv sync --extra ml --extra speech --extra demo --extra dev
    # Unsloth is installed on top of the locked env (Linux only; not in uv.lock because
    # its torch/xformers pins move faster than the lock). Run GPU commands with --no-sync.
    uv pip install unsloth
    echo
    echo "Next:"
    echo "  uv run --no-sync pytest -q"
    echo "  uv run --no-sync uyari build --tag data-2026.11"
    echo "  uv run --no-sync uyari train --recipe recipes/cbt-spa.mt.glimmer-qlora.yaml"
    ;;
  *)
    echo "usage: $0 [check|project]" >&2
    exit 2
    ;;
esac
