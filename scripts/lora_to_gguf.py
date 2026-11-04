"""A Muse Glimmer LoRA adapter (PEFT, from `uyari train`) -> a GGUF LoRA that llama-server loads with `--lora`.

    uv run --no-sync python scripts/lora_to_gguf.py models/<model>/adapter            # writes adapter/adapter.gguf

llama.cpp's `convert_lora_to_gguf.py` reuses the Glimmer model converter, which only handles full weights:
it re-lays out Q and K for rope (transformers keeps them in rotate-half order) and adds QK-norm weights that
absorb `qk_scale_factor`. For an adapter, W = B @ A, so the re-layout of W's rows is the same re-layout of
B's rows, and no norm weights belong in it. This wrapper patches exactly that and runs llama.cpp's script.
`LLAMA_CPP` is the llama.cpp checkout (default ~/llama.cpp); the base model's config comes from the Hugging
Face cache.
"""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

BASE = "meta-models/Muse-Glimmer-30B"
HEADS = {".self_attn.q_proj.": "num_attention_heads", ".self_attn.k_proj.": "num_key_value_heads"}


def patch(llama: Path) -> None:
    sys.path[:0] = [str(llama), str(llama / "gguf-py")]
    import conversion.muse_glimmer as mg
    from conversion.base import TextModel

    full_weights = mg.MuseGlimmerModel.modify_tensors

    def modify_tensors(self, data_torch, name, bid):
        if type(data_torch).__name__ != "LoraTorchTensor":
            yield from full_weights(self, data_torch, name, bid)
            return
        for part, key in HEADS.items():
            if part in name:
                a, b = data_torch.get_lora_A_B()
                n, (rows, rank) = int(self.hparams[key]), b.shape
                b = b.view(n, 2, rows // n // 2, rank).transpose(1, 2).reshape(rows, rank)
                data_torch = type(data_torch)(a, b)
        yield from TextModel.modify_tensors(self, data_torch, name, bid)

    mg.MuseGlimmerModel.modify_tensors = modify_tensors


def main(adapter: str, out: str | None = None) -> None:
    from huggingface_hub import snapshot_download

    llama = Path(os.environ.get("LLAMA_CPP", "~/llama.cpp")).expanduser()
    base = snapshot_download(BASE, allow_patterns=["*.json", "*.jinja"])
    out = out or str(Path(adapter) / "adapter.gguf")
    patch(llama)
    sys.argv = ["convert_lora_to_gguf.py", adapter, "--base", base, "--outfile", out, "--outtype", "f16"]
    runpy.run_path(str(llama / "convert_lora_to_gguf.py"), run_name="__main__")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    main(*sys.argv[1:])
