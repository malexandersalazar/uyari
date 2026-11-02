# Runbook: the RTX 4090 (Ubuntu)

Runs unattended: no command asks for input, every step says what "done" looks like, and nothing is edited
by hand. If a "done" check fails, stop and report the step with the last 40 lines of its log.

## Before you start (once, by the machine's owner)

1. `git clone https://github.com/malexandersalazar/uyari.git && cd uyari`
2. `.env` at the repository root, from `.env.example`. Set `HF_TOKEN` if the Glimmer download needs a
   login. `META_API_KEY` is used only by paid commands, and nothing in this runbook calls one.
3. `gh auth login` and a git identity (`git config user.name`, `git config user.email`), so step 3 can push.

Everything below runs from the repository root.

## Rules

* Long steps run in the background and log to `runs/` (gitignored). Read the log; don't block on the command.
* No paid API calls: `uyari transcribe`, `uyari generate run`, `uyari primary translate` and `uyari llm ping`
  are out of scope.
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

* `unsloth.peak_vram_gib`: must leave headroom under 24 GB at length 512 (training uses the same loader).
* `unsloth.loader`: `FastModel` (Glimmer is image-text-to-text; vision frozen).
* `server.backend`: `vllm` or `llama-server`. If neither passes, the demo runs Glimmer in process (slower
  first answer); that is not a reason to stop.
* `download` failing with 401 or 403: `HF_TOKEN` is missing from `.env`. Stop and report it.

## 1. Project setup and verify

```bash
bash scripts/setup_ubuntu.sh project
uv run --no-sync pytest -q
uv run --no-sync uyari validate --strict
uv run --no-sync uyari build --tag data-2026.11 --as-of 2026-11-02 --verify
```

Done: tests pass, `validate` prints OK, and `build --verify` prints OK (same content hashes as on Windows).

## 2. Train and register

```bash
nohup make all > runs/make-all.log 2>&1 &
```

| Step | What it does | Time |
|---|---|---|
| `floor` | Retrieval floor, all four directions (Spanish and English ↔ Shawi) | seconds |
| `train-nllb` | NLLB 1.3B → `models/mt-cbt-nllb1.3b@v0.2`, then registers it as `fast` | about 1 h |
| `train-glimmer` | Muse Glimmer 30B QLoRA → `models/mt-cbt-glimmer30b-qlora@v0.1`, then registers it as `promoted` (the demo default) | hours; progress in `runs/cbt.mt.glimmer-qlora/train_log.jsonl` |
| `needs` | `languages/cbt_Latn/NEEDS.md` | seconds |
| `report` | `reports/side-by-side.html` with the registered models | minutes |

The English sentences (`primary/eng_Latn`) are machine-translated from the Spanish with the same chunk
ids, so every human Shawi translation pairs with both. One model per backend covers all four directions.

Each training target ends with `uyari register`, the rule the Trainer agent applies after a merge:

* every direction beats the retrieval floor, and
* the model beats whoever holds its slot: +0.5 mean chrF++ on the directions both share, or it adds
  directions (English) and loses at most 0.5 on the shared ones. NLLB v0.2 competes with v0.1 (Spanish
  only, 38.0 / 37.7) for `fast`; Glimmer has no incumbent for `promoted`.

Glimmer and NLLB never compete with each other: the demo serves Glimmer by default and NLLB as its fast
mode. A model that passes gets its test score (once), its line in `models/registry.yaml` and its model
card. One that fails stays unregistered; the log says why (`not registered … : <reason>`, then
`Error 3 (ignored)`) and the rest goes on.

Done: `pgrep -f "make all"` prints nothing, `runs/make-all.log` has no unignored `Error`, and
`models/registry.yaml` has Glimmer under `promoted` and NLLB v0.2 under `fast`. Report any
`not registered` line as it is; don't retry with `--force`.

If Glimmer runs out of memory or time, run `nohup make train-glimmer-spa > runs/glimmer-spa.log 2>&1 &`
(Spanish ↔ Shawi only, fewer examples; it registers itself the same way), then `make needs report`.

## 3. Publish the results

```bash
git add models languages/cbt_Latn/NEEDS.md reports/side-by-side.html
git commit -m "Glimmer and NLLB v0.2: scores, model cards, registry"
git push origin main
```

Use exactly this commit message, on `main`. Weights and adapters are gitignored, so `git add models` adds
only cards, scores, recipes and evaluation outputs.

## 4. Demo

```bash
nohup make demo > runs/demo.log 2>&1 &
grep -o "https://[a-z0-9]*\.gradio\.live" runs/demo.log      # repeat until it prints the link
```

Done: the `gradio.live` link opens the page and translates in both directions. Report the link.

The page serves only the registered models and shows English once one of them has the English
directions. Its optional Spanish voice input (Muse Voice Transcribe) asks each visitor for their own Meta
API key; the server's key is never used (`uyari demo --no-voice` hides it). The link is a free tunnel: it
lasts up to a week or until the process stops, and it changes on every restart.

If NLLB v0.2 was not registered, `fast` is still v0.1, whose weights are not in git: the owner copies
`models/mt-cbt-spa-nllb1.3b@v0.1/weights` (2.6 GB) from the Windows PC, or run `make train-nllb-spa`.

## 5. Agents on video (owner)

* Self-hosted runner: first set *Settings → Actions → General → Require approval for all outside
  collaborators*, then register this machine with labels `self-hosted, linux, gpu` and create
  `/opt/uyari/.venv` with `UV_PROJECT_ENVIRONMENT=/opt/uyari/.venv bash scripts/setup_ubuntu.sh project`.
* Gatekeeper: `python scripts/make_demo_contribution.py` on a branch, open a PR, the review appears.
* Trainer: merge a contribution; `train.yml` builds, trains NLLB, evaluates, promotes and opens a PR
  with the card and `NEEDS.md`.

## Money

Nothing in this runbook calls a paid API. The demo's voice input is paid by each visitor's own key.
`uyari llm spend` shows the ledger.
