# scripts/

| Script | Run on | What |
|---|---|---|
| `check_4090.py` | Ubuntu 4090, before anything else | Standalone GPU stack check: driver/CUDA/VRAM/disk, downloads (Glimmer, NLLB, omniASR), Glimmer 4-bit + LoRA 10 steps through Unsloth `FastModel` (Glimmer is image-text-to-text), NLLB one sentence, vLLM/llama-server chat, Gradio share link. Writes `check_4090_report.json` |
| `setup_ubuntu.sh check` | Ubuntu, before cloning | Throwaway venv for `check_4090.py` |
| `setup_ubuntu.sh project` | Ubuntu, in the clone | Project venv with the GPU extras + Unsloth; vLLM as a separate uv tool |
| `make_demo_contribution.py` | anywhere | Creates a deliberately defective contribution (Spanish in the Shawi column, a copied row, ASCII apostrophes, an unknown id) to film the Gatekeeper. Never merge it |
