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
prompt + completion, the prompt part is masked with -100. Checkpoint selection:

* ``eval.selection: chrf``: greedy chrF++ on a fixed, direction-balanced validation subset every
  ``select_every`` epochs and at the end; the adapter with the best score is kept. The subset is
  ``select_limit`` examples, or ``select_into`` per direction into the Indigenous language plus ``select_out``
  per direction out of it. ``select_on: into`` scores only the directions into it (``all``, the default, the
  mean over every direction). Validation loss is still logged each epoch, not used.
* ``train.into_sources_per_target: k``: with several official languages, each Indigenous target sentence
  appears once per official language and is memorized that many times faster than the directions out of it.
  Each epoch keeps it from only ``k`` of them (rotating with the epoch); the directions out of it keep all.
* otherwise validation loss each epoch (v0.1; it stopped Glimmer after one epoch).

Only the adapter is saved (``<output>/adapter``).
"""

from __future__ import annotations

import math
import random
import re
from pathlib import Path

from uyari.paths import Paths
from uyari.pipelines.mt.common import (
    TrainLog,
    length_bucketed_batches,
    load_split,
    seed_everything,
    selection_subset,
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


def into_rotation(rows: list[dict], language: str, k: int | None, seed: int, epoch: int) -> list[int]:
    """Indices of ``rows`` to train on this epoch: every example out of ``language``, and each target sentence
    into it from only ``k`` of its source languages, chosen anew each epoch (all of them if ``k`` is None)."""
    if not k:
        return list(range(len(rows)))
    groups: dict[tuple, list[int]] = {}
    for i, r in enumerate(rows):
        if r["tgt_lang"] == language:
            groups.setdefault((r["chunk_id"], r["tgt"]), []).append(i)
    rng = random.Random(seed * 7919 + epoch)
    drop = set()
    for key in sorted(groups):
        idx = groups[key]
        if len(idx) > k:
            drop |= set(idx) - set(rng.sample(idx, k))
    return [i for i in range(len(rows)) if i not in drop]


def selection_rows(rows: list[dict], language: str, ev: dict, seed: int) -> list[dict]:
    """The fixed validation subset for chrF++ selection (see the module docstring)."""
    if "select_into" not in ev and "select_out" not in ev:
        return selection_subset(rows, int(ev.get("select_limit", 480)), seed)
    into = [r for r in rows if r["tgt_lang"] == language]
    out = [r for r in rows if r["tgt_lang"] != language]
    n_into = len({r["src_lang"] for r in into})
    n_out = len({r["tgt_lang"] for r in out})
    return (selection_subset(into, int(ev.get("select_into", 40)) * n_into, seed)
            + selection_subset(out, int(ev.get("select_out", 40)) * n_out, seed))


def selection_metric(scores: dict, language: str, on: str = "all") -> dict:
    """``{"score": what selection maximizes, "into": mean into ``language``, "out": mean out of it}`` from
    per-direction chrF++ (``{"spa>cbt": 41.2, ...}``)."""
    iso = language[:3]
    into = [v for k, v in scores.items() if k.endswith(f">{iso}")]
    out = [v for k, v in scores.items() if k.startswith(f"{iso}>")]
    mean = lambda xs: round(sum(xs) / len(xs), 2) if xs else None  # noqa: E731
    res = {"into": mean(into), "out": mean(out), "all": mean(into + out)}
    if on not in res:
        raise ValueError(f"eval.select_on must be into, out or all, not {on!r}")
    return {"score": res[on] if res[on] is not None else res["all"], **res}


def set_mode(model, backend: str, inference: bool) -> None:
    """Switch between generation and training (Unsloth patches both ways; PEFT is eval/train)."""
    if backend == "unsloth":
        try:
            from unsloth import FastModel as Fast
        except ImportError:
            from unsloth import FastLanguageModel as Fast
        (Fast.for_inference if inference else Fast.for_training)(model)
    else:
        model.eval() if inference else model.train()


def selection_score(model, chat, backend: str, rows: list[dict], max_new_tokens: int, batch_size: int) -> dict:
    """``{"mean": mean chrF++ over directions, "<src>><tgt>": chrF++, ...}`` of greedy outputs on ``rows``."""
    from uyari.pipelines.mt.metrics import corpus_scores

    set_mode(model, backend, inference=True)
    try:
        hyps = generate(model, chat, [r["prompt"] for r in rows], max_new_tokens=max_new_tokens,
                        batch_size=batch_size)
    finally:
        set_mode(model, backend, inference=False)
    out = {}
    for d in sorted({(r["src_lang"], r["tgt_lang"]) for r in rows}):
        idx = [i for i, r in enumerate(rows) if (r["src_lang"], r["tgt_lang"]) == d]
        out[f"{d[0][:3]}>{d[1][:3]}"] = corpus_scores([hyps[i] for i in idx], [rows[i]["tgt_model"] for i in idx])[
            "chrf++"] or 0.0
    out = {"mean": round(sum(out.values()) / max(1, len(out)), 2), **out}
    return out


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

    train_rows = load_split(data_dir, "train")
    train, skipped = encode(train_rows)
    val_rows = load_split(data_dir, "validation")
    val, _ = encode(val_rows[: int(recipe.eval.get("loss_limit", 400))])
    ev = recipe.eval
    by_chrf = ev.get("selection") == "chrf"
    select_on = ev.get("select_on", "all")
    sel = selection_rows(val_rows, recipe.language, ev, seed) if by_chrf else []
    k_into = cfg.get("into_sources_per_target")
    lengths = [len(a) for a, _ in train]
    bs, accum = int(cfg.get("batch_size", 1)), int(cfg.get("grad_accum", 16))
    epochs = int(cfg.get("epochs", 3))
    per_epoch = len(into_rotation(train_rows, recipe.language, k_into, seed, 0))
    steps_per_epoch = math.ceil(math.ceil(per_epoch / bs) / accum)
    total = min(max_steps or cfg.get("max_steps") or 10**9, steps_per_epoch * epochs)
    epochs = min(epochs, math.ceil(total / steps_per_epoch))

    params = [p for p in model.parameters() if p.requires_grad]
    if cfg.get("optimizer", "adamw_8bit") == "adamw_8bit":
        import bitsandbytes as bnb

        opt = bnb.optim.AdamW8bit(params, lr=float(cfg.get("lr", 1e-4)), weight_decay=0.0)
    else:
        opt = torch.optim.AdamW(params, lr=float(cfg.get("lr", 1e-4)), weight_decay=0.0)
    sched = get_linear_schedule_with_warmup(opt, int(total * float(cfg.get("warmup_ratio", 0.03))), total)
    every = max(1, round(steps_per_epoch * float(ev.get("select_every", 1.0)))) if by_chrf else 0
    log(event="start", recipe=recipe.id, backend=backend, examples=len(train), examples_per_epoch=per_epoch,
        truncated=skipped, steps=total, epochs=epochs, trainable_params=sum(p.numel() for p in params),
        selection=(f"chrf ({select_on}) on {len(sel)} validation examples every {every} steps" if by_chrf
                   else "val_loss"))

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
    best_chrf = -1.0
    adapter = out_dir / "adapter"

    def select(epoch: int) -> None:
        """chrF++ selection point: keep the adapter if its score (``select_on``) is the best so far."""
        nonlocal best_chrf
        sc = selection_score(model, chat, backend, sel, int(ev.get("max_new_tokens", 256)),
                             int(ev.get("select_batch_size", ev.get("batch_size", 8))))
        m = selection_metric({k: v for k, v in sc.items() if k != "mean"}, recipe.language, select_on)
        better = m["score"] > best_chrf
        log(event="select", epoch=round(step / steps_per_epoch, 2), step=step, selection_chrf=m["score"],
            into=m["into"], out=m["out"], by_direction={k: v for k, v in sc.items() if k != "mean"}, kept=better)
        if better:
            best_chrf = m["score"]
            model.save_pretrained(str(adapter))
            chat.save(str(adapter))
            write_meta(out_dir, recipe, "causal_lora", {
                "adapter": "adapter", "backend": backend, "selection": "chrf", "best_epoch": epoch,
                "best_epochs_done": round(step / steps_per_epoch, 2), "steps": step,
                "selection_chrf_greedy": m["score"], "selection_on": select_on, "selection_into": m["into"],
                "selection_out": m["out"], "selection_by_direction": {k: v for k, v in sc.items() if k != "mean"},
                "selection_examples": len(sel), "into_sources_per_target": k_into})

    model.train()
    for epoch in range(epochs):
        idx = into_rotation(train_rows, recipe.language, k_into, seed, epoch)
        batches = [[idx[j] for j in b] for b in length_bucketed_batches([lengths[i] for i in idx], bs, seed, epoch)]
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
                if by_chrf and (step % every == 0 or step >= total):
                    select(epoch)
                if step >= total:
                    break
        vl = val_loss()
        log(event="epoch", epoch=epoch, step=step, val_loss=round(vl, 4))
        if not by_chrf and vl < best:
            best = vl
            model.save_pretrained(str(adapter))
            chat.save(str(adapter))
            write_meta(out_dir, recipe, "causal_lora", {"adapter": "adapter", "backend": backend, "best_epoch": epoch,
                                                        "steps": step, "selection_val_loss": round(vl, 4)})
        if step >= total:
            break
    log(event="done", **({"best_selection_chrf": best_chrf} if by_chrf else {"best_val_loss": best}))
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
_HEADER = re.compile(r"^(?:\s|<\|[^|>]{1,40}\|>|to=\S+|assistant|final|analysis|commentary)*$")


def clean_completion(text: str) -> str:
    """The translation from a raw completion: the last non-empty message after a channel marker
    (``<|message|>``, Glimmer's ATEM format), before any special token, first line only. A stray marker after
    the translation (``…paʼ<|message|>``, which the model sometimes emits) is ignored rather than leaving
    nothing."""
    if "<|message|>" in text:
        segs = text.split("<|message|>")
        body = [p for p in segs[1:] if _SPECIAL.split(p, 1)[0].strip()]
        # A server may already have cut the header (`` to=user<|message|>``): then the text is before the marker.
        text = body[-1] if body else "" if _HEADER.match(segs[0]) else segs[0]
    m = _SPECIAL.search(text)
    if m:
        text = text[: m.start()]
    return text.strip().split("\n")[0].strip()
