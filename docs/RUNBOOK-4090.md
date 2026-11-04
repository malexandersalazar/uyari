# Runbook: the RTX 4090 (Ubuntu)

Runs unattended: no command asks for input, every step says what "done" looks like, and nothing is edited
by hand. If a "done" check fails, stop and report the step with the last 40 lines of its log.

## Before you start (once, by the machine's owner)

1. `git clone https://github.com/malexandersalazar/uyari.git && cd uyari`
2. `.env` at the repository root, from `.env.example`. `META_API_KEY` is used only by paid commands, and
   nothing in this runbook calls one. No `HF_TOKEN`: every download is public and ungated, and only
   `uyari publish` (not part of this runbook) needs one.
3. `gh auth login` and a git identity (`git config user.name`, `git config user.email`), so step 3 can push.
4. A Modal account with a payment method, and `uv run --no-sync modal token new` once in the clone: Muse
   Glimmer trains on a rented H100 (the 4-bit model does not fit the 4090 for training; decision 0010).
5. llama.cpp built with CUDA in `~/llama.cpp`, with `llama-server` on the `PATH`: the 4090 serves Glimmer
   with it, and `scripts/lora_to_gguf.py` uses its converter (`LLAMA_CPP` for another checkout).

Everything below runs from the repository root.

## Rules

* Long steps run in the background and log to `runs/` (gitignored). Read the log; don't block on the command.
* No paid API calls: `uyari transcribe`, `uyari generate run`, `uyari primary translate` and `uyari llm ping`
  are out of scope. The one paid step is Glimmer's training on Modal inside step 2 (about US$7 a run, on the
  owner's Modal account).
* Don't edit `models/registry.yaml`, model cards or `scores.json` by hand, and don't run
  `uyari register --force` or `uyari eval --final`. Registering and the one-time test score happen inside
  step 2, by rule; overriding the rule is the owner's decision.
* Never commit `.env`, weights, adapters or anything under `runs/`.

## 0. GPU check

Start this first: it downloads Glimmer (~60 GB) into the Hugging Face cache, where training finds it later.
The check uses its own throwaway venv, so a broken GPU stack shows up before the project is installed.

```bash
bash scripts/setup_ubuntu.sh check
mkdir -p runs
(set -a && . ./.env && set +a && HF_HUB_ENABLE_HF_TRANSFER=1 \
  nohup ~/uyari-check-venv/bin/python scripts/check_4090.py > runs/check_4090.log 2>&1 &)
```

Done: `pgrep -f check_4090.py` prints nothing, and `check_4090_report.json` has PASS for `env`,
`download`, `unsloth`, `nllb`, `server` and `gradio`. Also read:

* `unsloth` fails on a 24 GB card: the 4-bit model does not fit for training. Expected; Glimmer trains on
  Modal (step 2). Not a reason to stop.
* `server` may fail too (vLLM rejects the 4-bit checkpoint). `uyari serve start` uses llama-server with
  Unsloth's 4-bit GGUF instead: `uv run --no-sync hf download unsloth/Muse-Glimmer-30B-GGUF
  Muse-Glimmer-30B-UD-Q4_K_XL.gguf` (15 GB) puts it in the cache where it is found.
* `download` failing with 401 or 403: every model it fetches is public and ungated, so the repo id is wrong
  or the repository changed (moved, gated or removed). Stop and report it.

## 1. Project setup and verify

```bash
bash scripts/setup_ubuntu.sh project
uv run --no-sync pytest -q
uv run --no-sync uyari validate --strict
uv run --no-sync uyari build --tag data-2026.11-six --as-of 2026-11-02 \
  --officials spa_Latn,eng_Latn,fra_Latn,deu_Latn,ita_Latn,por_Latn --verify
```

Done: tests pass, `validate` prints OK, and `build --verify` prints OK (same content hashes as on Windows).
`--officials` keeps the build to the languages the recipes train on: every other folder under `primary/`
(Hindi, Thai) would add rows and change the tag's hashes. `make all` writes the tables.

## 2. Train and register

```bash
nohup make all > runs/make-all.log 2>&1 &
```

| Step | What it does | Time |
|---|---|---|
| `build` | `builds/data-2026.11-six` tables (Spanish, English, French, German, Italian, Portuguese), same hashes as the manifest | about a minute |
| `floor` | Retrieval floor, all twelve directions (six official languages ↔ Shawi) | seconds |
| `train-nllb` | NLLB 1.3B → `models/mt-cbt-nllb1.3b@v0.3`, then registers it as `fast` | about 1 h |
| `train-glimmer` | Muse Glimmer 30B QLoRA on a Modal H100 (`scripts/modal_glimmer.py`), then here: the adapter as GGUF, `uyari serve start`, validation through the server, and registration as `promoted` (the demo default) | about 2 h on Modal (about US$7; its log streams into `runs/make-all.log`), then about 1 h of scoring here |
| `needs` | `languages/cbt_Latn/NEEDS.md` | seconds |
| `report` | `reports/side-by-side.html` with the registered models | minutes |

The English, French, German, Italian and Portuguese sentences (`primary/<lang>`) are machine-translated
from the Spanish with the same chunk ids, so every human Shawi translation pairs with all six. One model per
backend covers all twelve directions.

Each training target ends with `uyari register`, the rule the Trainer agent applies after a merge:

* every direction beats the retrieval floor, and
* the model beats whoever holds its slot: +0.5 mean chrF++ on the directions both share, or it adds
  directions and loses at most 0.5 on the shared ones. NLLB v0.3 competes with v0.2 (Spanish and English)
  for `fast`; Glimmer competes with the Glimmer it would replace (v0.4) for `promoted`.

Glimmer and NLLB never compete with each other: the demo serves Glimmer by default and NLLB as the second
choice. A model that passes gets its test score (once), its line in `models/registry.yaml` and its model
card. One that fails stays unregistered; the log says why (`not registered … : <reason>`, then
`Error 3 (ignored)`) and the rest goes on.

Done: `pgrep -f "make all"` prints nothing, `runs/make-all.log` has no unignored `Error`, and
`models/registry.yaml` has Glimmer v0.4 under `promoted` and NLLB v0.3 under `fast`. Report any
`not registered` line as it is; don't retry with `--force`.

If Glimmer fails on Modal, run `nohup make train-glimmer-spa > runs/glimmer-spa.log 2>&1 &` (Spanish ↔
Shawi only, fewer examples, also on Modal; it registers itself the same way), then `make needs report`.

## 3. Publish the results

```bash
git add builds models languages/cbt_Latn/NEEDS.md reports/side-by-side.html
git commit -m "Glimmer v0.4 and NLLB v0.3: six languages, scores, model cards, registry"
git push origin main
```

Use exactly this commit message, on `main`. Weights and adapters are gitignored, so `git add models` adds
only cards, scores, recipes and evaluation outputs; `git add builds` adds only the new tag's manifest.

## 4. Demo

```bash
nohup make demo > runs/demo.log 2>&1 &
grep -o "https://[a-z0-9]*\.gradio\.live" runs/demo.log      # repeat until it prints the link
```

Done: the `gradio.live` link opens the page and translates both ways. Report the link.

The page starts the Glimmer server itself when Glimmer is registered and nothing answers on port 8011
(llama-server, 16.5 GB of the 4090), and stops it when the page stops. It serves only the registered models:
Glimmer by default and NLLB as the second choice, on a Model switch in every tab. Three tabs: your language →
Shawi, Shawi → your language (Spanish, English, French, German, Italian or Portuguese; Shawi is always on one
side), and speech. It reads Shawi aloud with Meta's MMS voice on the CPU (`facebook/mms-tts-cbt`, 145 MB,
fetched from Hugging Face on the first start; without it the page still translates and hides Listen). Its
optional voice input (Spanish, English, French or Portuguese, through Muse Voice Transcribe) asks each visitor
for their own Meta API key; the server's key is never used (`uyari demo --no-voice` hides it). The link is a
free tunnel: it lasts up to a week or until the process stops, and it changes on every restart.

If the Glimmer server cannot start (no GGUF in the cache, no `llama-server`), the page serves NLLB alone and
says why under the Model switch and in `runs/demo.log`.

## 5. Agents on video (owner)

* Self-hosted runner: first set *Settings → Actions → General → Require approval for all outside
  collaborators*, then register this machine with labels `self-hosted, linux, gpu` and create
  `/opt/uyari/.venv` with `UV_PROJECT_ENVIRONMENT=/opt/uyari/.venv bash scripts/setup_ubuntu.sh project`.
* Gatekeeper: `python scripts/make_demo_contribution.py` on a branch, open a PR, the review appears.
* Trainer: merge a contribution; `train.yml` builds, trains NLLB, evaluates, promotes and opens a PR
  with the card and `NEEDS.md`.

## Money

Nothing in this runbook calls a paid API. Glimmer's training rents a Modal H100 (about US$7 a run, the
owner's Modal account; its usage page has the bill). The demo's voice input is paid by each visitor's own
key. `uyari llm spend` shows the API ledger.
