"""NLLB-200 full fine-tune, both directions, with a new language token.

A small explicit loop (no Trainer) so the behaviour is the same across transformers versions:
NLLB's input format is built by hand — source ``[src_lang] X </s>``, labels
``[tgt_lang] Y </s>``, decoder start ``</s>``, and ``forced_bos_token_id`` = target language
at generation. The new language token (``cbt_Latn``) is added and its embedding initialised
from a related language (``new_lang_token_init``).

Checkpoint selection: after each epoch, greedy chrF++ on a fixed validation subset; the best
epoch is saved to ``<output>/weights``. The test split is never read here.
"""

from __future__ import annotations

import math
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


def ensure_lang_tokens(tok, model, langs: list[str], init_from: str | None) -> list[str]:
    """Add missing language-code tokens; initialise their embeddings. Returns the added codes."""
    import torch

    missing = [lang for lang in langs if tok.convert_tokens_to_ids(lang) in (None, tok.unk_token_id)]
    if not missing:
        return []
    tok.add_tokens(missing, special_tokens=True)
    model.resize_token_embeddings(len(tok))
    emb = model.get_input_embeddings().weight
    with torch.no_grad():
        src = tok.convert_tokens_to_ids(init_from) if init_from else None
        for lang in missing:
            new = tok.convert_tokens_to_ids(lang)
            if src is not None and src != tok.unk_token_id:
                emb[new] = emb[src].clone()
    return missing


def encode_pair(tok, src_lang: str, src: str, tgt_lang: str | None, tgt: str | None, max_len: int):
    s = tok(src, add_special_tokens=False)["input_ids"][: max_len - 2]
    ids = [tok.convert_tokens_to_ids(src_lang), *s, tok.eos_token_id]
    if tgt is None:
        return ids, None
    t = tok(tgt, add_special_tokens=False)["input_ids"][: max_len - 2]
    return ids, [tok.convert_tokens_to_ids(tgt_lang), *t, tok.eos_token_id]


def generate(model, tok, texts: list[str], src_lang: str, tgt_lang: str, num_beams: int = 4,
             max_new_tokens: int = 256, batch_size: int = 32, max_len: int = 256) -> list[str]:
    import torch

    device = next(model.parameters()).device
    order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
    out: list[str] = [""] * len(texts)
    forced = tok.convert_tokens_to_ids(tgt_lang)
    model.eval()
    for b in range(0, len(order), batch_size):
        idx = order[b:b + batch_size]
        enc = [encode_pair(tok, src_lang, texts[i], None, None, max_len)[0] for i in idx]
        width = max(map(len, enc))
        ids = torch.full((len(enc), width), tok.pad_token_id, dtype=torch.long)
        att = torch.zeros_like(ids)
        for k, e in enumerate(enc):
            ids[k, : len(e)] = torch.tensor(e)
            att[k, : len(e)] = 1
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
            gen = model.generate(input_ids=ids.to(device), attention_mask=att.to(device),
                                 forced_bos_token_id=forced, num_beams=num_beams,
                                 max_new_tokens=max_new_tokens)
        for k, text in zip(idx, tok.batch_decode(gen, skip_special_tokens=True), strict=True):
            out[k] = text.strip()
    return out


def _collate(batch, pad_id):
    import torch

    w_in = max(len(b[0]) for b in batch)
    w_lab = max(len(b[1]) for b in batch)
    ids = torch.full((len(batch), w_in), pad_id, dtype=torch.long)
    att = torch.zeros_like(ids)
    lab = torch.full((len(batch), w_lab), -100, dtype=torch.long)
    for k, (i, label) in enumerate(batch):
        ids[k, : len(i)] = torch.tensor(i)
        att[k, : len(i)] = 1
        lab[k, : len(label)] = torch.tensor(label)
    return ids, att, lab


def train_nllb(paths: Paths, recipe: Recipe, data_dir: Path, out_dir: Path, max_steps: int | None = None) -> Path:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, get_linear_schedule_with_warmup

    from uyari.pipelines.mt.metrics import corpus_scores

    cfg = recipe.train
    seed = int(cfg.get("seed", 7))
    seed_everything(seed)
    log = TrainLog(recipe.run_dir(paths) / "train_log.jsonl")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    precision = cfg.get("precision", "bf16_mixed")
    dtype = torch.bfloat16 if precision == "bf16_pure" else torch.float32

    tok = AutoTokenizer.from_pretrained(recipe.base_model)
    model = AutoModelForSeq2SeqLM.from_pretrained(recipe.base_model, dtype=dtype)
    added = ensure_lang_tokens(tok, model, [*recipe.sources, recipe.language], recipe.cfg.get("new_lang_token_init"))
    model.to(device)
    if cfg.get("gradient_checkpointing"):
        model.gradient_checkpointing_enable()
        model.config.use_cache = False

    max_len = int(cfg.get("max_len", 256))
    train = load_split(data_dir, "train")
    val = load_split(data_dir, "validation")
    enc = [encode_pair(tok, r["src_lang"], r["src_model"], r["tgt_lang"], r["tgt_model"], max_len) for r in train]
    lengths = [len(a) + len(b) for a, b in enc]
    bs, accum = int(cfg.get("batch_size", 16)), int(cfg.get("grad_accum", 1))
    epochs = int(cfg.get("epochs", 3))
    steps_per_epoch = math.ceil(math.ceil(len(enc) / bs) / accum)
    total = min(max_steps or cfg.get("max_steps") or 10**9, steps_per_epoch * epochs)
    epochs = min(epochs, math.ceil(total / steps_per_epoch))

    params = [p for p in model.parameters() if p.requires_grad]
    if cfg.get("optimizer", "adafactor") == "adafactor":
        from transformers.optimization import Adafactor

        opt = Adafactor(params, lr=float(cfg.get("lr", 1e-4)), scale_parameter=False, relative_step=False,
                        warmup_init=False, weight_decay=float(cfg.get("weight_decay", 0.0)))
    else:
        opt = torch.optim.AdamW(params, lr=float(cfg.get("lr", 1e-4)), weight_decay=float(cfg.get("weight_decay", 0.0)))
    sched = get_linear_schedule_with_warmup(opt, int(total * float(cfg.get("warmup_ratio", 0.05))), total)
    autocast = precision == "bf16_mixed" and device == "cuda"

    ev = recipe.eval
    sel = selection_subset(val, int(ev.get("select_limit", 200)))
    log(event="start", recipe=recipe.id, examples=len(enc), steps=total, epochs=epochs, added_tokens=added,
        device=device, precision=precision)
    step, best = 0, -1.0
    weights = out_dir / "weights"
    for epoch in range(epochs):
        model.train()
        batches = length_bucketed_batches(lengths, bs, seed, epoch)
        running = 0.0
        for bi, b in enumerate(batches):
            ids, att, lab = _collate([enc[i] for i in b], tok.pad_token_id)
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=autocast):
                loss = model(input_ids=ids.to(device), attention_mask=att.to(device), labels=lab.to(device)).loss
            (loss / accum).backward()
            running += loss.item()
            if (bi + 1) % accum == 0 or bi == len(batches) - 1:
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
                step += 1
                if step % 20 == 0 or step == 1:
                    log(event="step", epoch=epoch, step=step, loss=round(running / (bi + 1), 4),
                        lr=sched.get_last_lr()[0])
                if step >= total:
                    break
        # checkpoint selection on validation (never test)
        hyps, refs = [], []
        for d in sorted({(r["src_lang"], r["tgt_lang"]) for r in sel}):
            rs = [r for r in sel if (r["src_lang"], r["tgt_lang"]) == d]
            hyps += generate(model, tok, [r["src_model"] for r in rs], d[0], d[1], num_beams=1,
                             max_new_tokens=int(ev.get("max_new_tokens", 256)),
                             batch_size=int(ev.get("batch_size", 32)), max_len=max_len)
            refs += [r["tgt_model"] for r in rs]
        score = corpus_scores(hyps, refs)["chrf++"] or 0.0
        log(event="epoch", epoch=epoch, step=step, selection_chrf=score, best=max(best, score))
        if score > best:
            best = score
            model.save_pretrained(weights, safe_serialization=True)
            tok.save_pretrained(weights)
            write_meta(out_dir, recipe, "nllb", {"weights": "weights", "best_epoch": epoch, "steps": step,
                                                 "selection_chrf_greedy": score, "added_tokens": added,
                                                 "selection_examples": len(sel)})
        if step >= total:
            break
    log(event="done", best_selection_chrf=best)
    return out_dir
