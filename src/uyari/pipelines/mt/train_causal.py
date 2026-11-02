"""QLoRA fine-tune of a causal LM translator (Muse Glimmer 30B on the 4090).

Muse Glimmer is an image-text-to-text model (``MuseGlimmerForConditionalGeneration``: a vision
tower + a 52-layer text decoder). We fine-tune text only: LoRA on the language layers, vision
frozen, prompts rendered with the processor's chat template using list-style text content.

Backends:
  * ``unsloth`` (Linux, the 4090): ``FastModel`` (multimodal-aware; ``FastLanguageModel`` for
    text-only models), 4-bit + LoRA, Unsloth gradient checkpointing, vision layers frozen.
  * ``peft`` (any OS): transformers + bitsandbytes 4-bit + PEFT LoRA
    (``AutoModelForImageTextToText`` when the config has a vision tower). Used by the smoke recipe
    on Windows to exercise the same data path with a tiny model.

One explicit loop for both, loss on the completion only: the chat template renders
prompt + completion, the prompt part is masked with -100. Checkpoint selection by validation
loss each epoch (generation on a 30B model is too slow to run every epoch); chrF++ comes from
``uyari eval`` afterwards. Only the adapter is saved (``<output>/adapter``).
"""

from __future__ import annotations

import math
import re
from pathlib import Path

from uyari.paths import Paths
from uyari.pipelines.mt.common import (
    TrainLog,
    length_bucketed_batches,
    load_split,
    seed_everything,
    write_meta,
)
from uyari.recipes import Recipe

ALL_LINEAR = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
# PEFT regex: the language model's linear layers only (never the vision tower or the projector)
LANGUAGE_LINEAR = r"^(?!.*(vision|visual|image|projector|mm_)).*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)$"


class ChatText:
    """Chat rendering + tokenization for a tokenizer or a multimodal processor."""

    def __init__(self, obj, template_kwargs: dict | None = None):
        self.proc = obj
        self.tok = getattr(obj, "tokenizer", obj)
        self.multimodal = self.tok is not obj
        self.kwargs = dict(template_kwargs or {})  # e.g. Glimmer: {"reasoning_strength": "low"}
        if self.tok.pad_token is None:
            self.tok.pad_token = self.tok.eos_token

    def _msgs(self, msgs: list[dict]) -> list[dict]:
        if not self.multimodal:
            return msgs
        return [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in msgs]

    def text(self, msgs: list[dict], generation_prompt: bool) -> str:
        templ = self.proc if getattr(self.proc, "chat_template", None) else self.tok
        return templ.apply_chat_template(self._msgs(msgs), add_generation_prompt=generation_prompt, tokenize=False,
                                         **self.kwargs)

    def stop_ids(self) -> list[int]:
        ids = {self.tok.eos_token_id}
        for t in ("<|eot|>", "<|eot_id|>", "<|end|>", "<end_of_turn>", "<|im_end|>"):
            i = self.tok.convert_tokens_to_ids(t)
            if isinstance(i, int) and i >= 0 and i != self.tok.unk_token_id:
                ids.add(i)
        return sorted(i for i in ids if i is not None)

    def ids(self, text: str) -> list[int]:
        return list(self.tok(text, add_special_tokens=False)["input_ids"])

    def save(self, path: str) -> None:
        self.proc.save_pretrained(path)


def render(chat: ChatText, prompt: list[dict], completion: list[dict] | None):
    """Token ids for prompt (+ completion) and the labels (prompt masked with -100).
    Prompt and completion are tokenized separately so training and inference see the same prompt ids."""
    p_text = chat.text(prompt, True)
    p_ids = chat.ids(p_text)
    if completion is None:
        return p_ids, None
    full_text = chat.text(prompt + completion, False)
    if full_text.startswith(p_text):
        c_ids = chat.ids(full_text[len(p_text):])
    else:  # template re-renders the prompt differently: fall back to the bare completion + EOS
        c_ids = chat.ids(completion[0]["content"] + (chat.tok.eos_token or ""))
    return p_ids + c_ids, [-100] * len(p_ids) + c_ids


def load_model(recipe: Recipe, for_training: bool = True, adapter_dir: Path | None = None):
    """(model, ChatText, backend). 4-bit base + LoRA on the language layers (new, or from ``adapter_dir``)."""
    import torch

    lcfg = recipe.lora
    backend = lcfg.get("backend", "unsloth")
    max_len = int(recipe.train.get("max_len", 512))
    r, alpha, drop = int(lcfg.get("r", 16)), int(lcfg.get("alpha", 32)), float(lcfg.get("dropout", 0.0))
    tkw = recipe.cfg.get("chat_template_kwargs") or {}
    if backend == "unsloth":
        try:
            from unsloth import FastModel as Fast  # multimodal-aware (Glimmer is image-text-to-text)
            generic = True
        except ImportError:
            try:
                from unsloth import FastLanguageModel as Fast
                generic = False
            except ImportError as e:
                raise RuntimeError("Unsloth is not installed (Linux: `uv pip install unsloth`); "
                                   "set lora.backend: peft to use plain PEFT") from e
        model, proc = Fast.from_pretrained(model_name=str(adapter_dir or recipe.base_model), max_seq_length=max_len,
                                           load_in_4bit=True, dtype=None)
        if adapter_dir is None:
            kw = {"r": r, "lora_alpha": alpha, "lora_dropout": drop, "bias": "none",
                  "use_gradient_checkpointing": "unsloth", "random_state": int(recipe.train.get("seed", 7))}
            if generic:
                kw.update(finetune_vision_layers=False, finetune_language_layers=True,
                          finetune_attention_modules=True, finetune_mlp_modules=True)
            else:
                kw["target_modules"] = ALL_LINEAR if lcfg.get("target", "all-linear") == "all-linear" else lcfg["target"]
            model = Fast.get_peft_model(model, **kw)
        if not for_training:
            Fast.for_inference(model)
        return model, ChatText(proc, tkw), backend

    from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoConfig, BitsAndBytesConfig

    cfg = AutoConfig.from_pretrained(recipe.base_model)
    multimodal = getattr(cfg, "vision_config", None) is not None
    if multimodal:
        from transformers import AutoModelForImageTextToText as AutoModel
        from transformers import AutoProcessor as AutoProc
    else:
        from transformers import AutoModelForCausalLM as AutoModel
        from transformers import AutoTokenizer as AutoProc
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                               bnb_4bit_compute_dtype=torch.bfloat16) if lcfg.get("load_in_4bit", True) else None
    chat = ChatText(AutoProc.from_pretrained(str(adapter_dir) if adapter_dir else recipe.base_model), tkw)
    model = AutoModel.from_pretrained(recipe.base_model, quantization_config=quant, dtype=torch.bfloat16,
                                      device_map={"": 0} if torch.cuda.is_available() else None)
    if adapter_dir is not None:
        model = PeftModel.from_pretrained(model, str(adapter_dir), is_trainable=for_training)
    else:
        if quant is not None:
            model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
        if lcfg.get("target", "all-linear") == "all-linear":
            target = LANGUAGE_LINEAR if multimodal else "all-linear"
        else:
            target = lcfg["target"]
        model = get_peft_model(model, LoraConfig(r=r, lora_alpha=alpha, lora_dropout=drop, target_modules=target,
                                                 task_type="CAUSAL_LM"))
    if not for_training:
        model.eval()
    return model, chat, backend


def _collate(batch, pad_id):
    import torch

    w = max(len(b[0]) for b in batch)
    ids = torch.full((len(batch), w), pad_id, dtype=torch.long)
    att = torch.zeros_like(ids)
    lab = torch.full((len(batch), w), -100, dtype=torch.long)
    for k, (i, label) in enumerate(batch):
        ids[k, : len(i)] = torch.tensor(i)
        att[k, : len(i)] = 1
        lab[k, : len(label)] = torch.tensor(label)
    return ids, att, lab


def train_causal(paths: Paths, recipe: Recipe, data_dir: Path, out_dir: Path, max_steps: int | None = None) -> Path:
    import torch
    from transformers import get_linear_schedule_with_warmup

    cfg = recipe.train
    seed = int(cfg.get("seed", 7))
    seed_everything(seed)
    log = TrainLog(recipe.run_dir(paths) / "train_log.jsonl")
    model, chat, backend = load_model(recipe, for_training=True)
    pad_id = chat.tok.pad_token_id
    device = next(p for p in model.parameters()).device
    max_len = int(cfg.get("max_len", 512))

    def encode(rows):
        out, skipped = [], 0
        for r in rows:
            ids, lab = render(chat, r["prompt"], r["completion"])
            if len(ids) > max_len:
                skipped += 1
                ids, lab = ids[:max_len], lab[:max_len]
            out.append((ids, lab))
        return out, skipped

    train, skipped = encode(load_split(data_dir, "train"))
    val, _ = encode(load_split(data_dir, "validation")[: int(recipe.eval.get("loss_limit", 400))])
    lengths = [len(a) for a, _ in train]
    bs, accum = int(cfg.get("batch_size", 1)), int(cfg.get("grad_accum", 16))
    epochs = int(cfg.get("epochs", 3))
    steps_per_epoch = math.ceil(math.ceil(len(train) / bs) / accum)
    total = min(max_steps or cfg.get("max_steps") or 10**9, steps_per_epoch * epochs)
    epochs = min(epochs, math.ceil(total / steps_per_epoch))

    params = [p for p in model.parameters() if p.requires_grad]
    if cfg.get("optimizer", "adamw_8bit") == "adamw_8bit":
        import bitsandbytes as bnb

        opt = bnb.optim.AdamW8bit(params, lr=float(cfg.get("lr", 1e-4)), weight_decay=0.0)
    else:
        opt = torch.optim.AdamW(params, lr=float(cfg.get("lr", 1e-4)), weight_decay=0.0)
    sched = get_linear_schedule_with_warmup(opt, int(total * float(cfg.get("warmup_ratio", 0.03))), total)
    log(event="start", recipe=recipe.id, backend=backend, examples=len(train), truncated=skipped, steps=total,
        epochs=epochs, trainable_params=sum(p.numel() for p in params))

    def val_loss() -> float:
        model.eval()
        tot, n = 0.0, 0
        with torch.no_grad():
            for i in range(0, len(val), max(1, bs)):
                ids, att, lab = _collate(val[i:i + max(1, bs)], pad_id)
                with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                    loss = model(input_ids=ids.to(device), attention_mask=att.to(device), labels=lab.to(device)).loss
                tot += loss.item()
                n += 1
        model.train()
        return tot / max(1, n)

    step, best = 0, float("inf")
    adapter = out_dir / "adapter"
    model.train()
    for epoch in range(epochs):
        batches = length_bucketed_batches(lengths, bs, seed, epoch)
        running = 0.0
        for bi, b in enumerate(batches):
            ids, att, lab = _collate([train[i] for i in b], pad_id)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                loss = model(input_ids=ids.to(device), attention_mask=att.to(device), labels=lab.to(device)).loss
            (loss / accum).backward()
            running += loss.item()
            if (bi + 1) % accum == 0 or bi == len(batches) - 1:
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
                step += 1
                if step % 10 == 0 or step == 1:
                    mem = torch.cuda.max_memory_reserved() / 2**30 if torch.cuda.is_available() else 0
                    log(event="step", epoch=epoch, step=step, loss=round(running / (bi + 1), 4),
                        lr=sched.get_last_lr()[0], peak_vram_gib=round(mem, 2))
                if step >= total:
                    break
        vl = val_loss()
        log(event="epoch", epoch=epoch, step=step, val_loss=round(vl, 4))
        if vl < best:
            best = vl
            model.save_pretrained(str(adapter))
            chat.save(str(adapter))
            write_meta(out_dir, recipe, "causal_lora", {"adapter": "adapter", "backend": backend, "best_epoch": epoch,
                                                        "steps": step, "selection_val_loss": round(vl, 4)})
        if step >= total:
            break
    log(event="done", best_val_loss=best)
    return out_dir


def generate(model, chat: ChatText, prompts: list[list[dict]], max_new_tokens: int = 256,
             batch_size: int = 8) -> list[str]:
    """Greedy decoding, left padding, batches sorted by length."""
    import torch

    device = next(model.parameters()).device
    tok = chat.tok
    enc = [render(chat, p, None)[0] for p in prompts]
    order = sorted(range(len(enc)), key=lambda i: len(enc[i]))
    out = [""] * len(enc)
    for b in range(0, len(order), batch_size):
        idx = order[b:b + batch_size]
        w = max(len(enc[i]) for i in idx)
        ids = torch.full((len(idx), w), tok.pad_token_id, dtype=torch.long)
        att = torch.zeros_like(ids)
        for k, i in enumerate(idx):
            ids[k, w - len(enc[i]):] = torch.tensor(enc[i])
            att[k, w - len(enc[i]):] = 1
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
            gen = model.generate(input_ids=ids.to(device), attention_mask=att.to(device), do_sample=False,
                                 max_new_tokens=max_new_tokens, pad_token_id=tok.pad_token_id,
                                 eos_token_id=chat.stop_ids())
        for k, i in enumerate(idx):
            out[i] = clean_completion(tok.decode(gen[k, w:], skip_special_tokens=False))
    return out


_SPECIAL = re.compile(r"<\|[^|>]{1,40}\|>|<end_of_turn>|</s>|<eos>")


def clean_completion(text: str) -> str:
    """The translation from a raw completion: after the last channel marker (``<|message|>``, Glimmer's
    ATEM format), before any special token, first line only."""
    if "<|message|>" in text:
        text = text.rsplit("<|message|>", 1)[1]
    m = _SPECIAL.search(text)
    if m:
        text = text[: m.start()]
    return text.strip().split("\n")[0].strip()
