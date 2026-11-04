# scripts/

| Script | Run on | What |
|---|---|---|
| `check_4090.py` | Ubuntu 4090, before anything else | Standalone GPU stack check: driver/CUDA/VRAM/disk, downloads (Glimmer, NLLB, omniASR), Glimmer 4-bit + LoRA 10 steps through Unsloth `FastModel` (Glimmer is image-text-to-text), NLLB one sentence, vLLM/llama-server chat, Gradio share link. Writes `check_4090_report.json` |
| `setup_ubuntu.sh check` | Ubuntu, right after the clone | Throwaway venv for `check_4090.py` |
| `setup_ubuntu.sh project` | Ubuntu, in the clone | Project venv with the GPU extras + Unsloth; vLLM as a separate uv tool |
| `modal_glimmer.py` | this machine, with a Modal token | Muse Glimmer 30B QLoRA on a rented Modal H100 80 GB (the 4-bit model does not fit the 4090 for training): base model into a Volume, a 20-step smoke run, the full recipe. Uploads the prepared train and validation examples only (decision 0010) |
| `lora_to_gguf.py` | the 4090 | A Glimmer LoRA adapter -> `adapter/adapter.gguf` for llama-server (`uyari serve start`), through llama.cpp's converter with the Q/K re-layout applied to the adapter |
| `make_demo_contribution.py` | anywhere | Creates a deliberately defective contribution (Spanish in the Shawi column, a copied row, ASCII apostrophes, an unknown id) to film the Gatekeeper. Never merge it |
