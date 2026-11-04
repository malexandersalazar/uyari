# recipes/

One YAML per training run (`schemas/recipe.json`); nothing is configurable from the command line except
`--max-steps` for smoke runs.

| Field | Meaning |
|---|---|
| `id` | recipe name |
| `build` | build tag it trains on |
| `task`, `language`, `primary`, `directions` | e.g. `mt`, `cbt_Latn`, `spa_Latn`, `[spa>cbt, cbt>spa]` |
| `splits` | always `{train: train, validation: validation}`; test only via `uyari eval --final` |
| `filters` | `provenance`, `licenses` |
| `base_model`, `method` | `seq2seq` (NLLB) or `qlora` (causal LM + LoRA) |
| `lora` | `r, alpha, dropout, target, backend` (`unsloth` or `peft`) |
| `new_lang_token_init` | NLLB: the language whose embedding seeds the new token |
| `text_codec` | reversible character map at the model edges (`{"ʼ": "'"}` for NLLB) |
| `train` | `epochs, max_steps, lr, optimizer, precision, batch_size, grad_accum, max_len, warmup_ratio, seed` |
| `eval` | decoding settings; `server_adapter` for the served LoRA |
| `output` | `models/<task>-<lang>-<base>@v<major>.<minor>` (major: base model; minor: build) |

| Recipe | Hardware | Purpose |
|---|---|---|
| `cbt-spa.mt.glimmer-qlora.yaml` | 4090 (Linux, Unsloth) | headline model |
| `cbt-spa.mt.nllb-1.3b.yaml` | 4090 | fast baseline, the Trainer loop |
| `cbt-spa.mt.nllb-1.3b-3060.yaml` | 3060 12 GB | same model in pure bf16 |
| `cbt-spa.mt.smoke.yaml`, `cbt-spa.mt.smoke-qlora.yaml` | any GPU | end-to-end smoke tests |
