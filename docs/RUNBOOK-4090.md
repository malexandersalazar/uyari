# Runbook: the RTX 4090 (Ubuntu)

Copy-paste order. Every step says what "done" looks like. Nothing in it is edited or typed by hand.

## 0. Clone, then check the GPU stack

The repository is public, so the clone needs no login. Start this first: the check downloads Glimmer
(~60 GB) into the Hugging Face cache, where training finds it later.

```bash
git clone https://github.com/malexandersalazar/uyari.git && cd uyari
bash scripts/setup_ubuntu.sh check            # a separate throwaway venv (~/uyari-check-venv) for the check
source ~/uyari-check-venv/bin/activate
HF_HUB_ENABLE_HF_TRANSFER=1 python scripts/check_4090.py
deactivate
```

If the Glimmer download answers 401 or 403, run `huggingface-cli login` and start the check again.

Done: `check_4090_report.json` has PASS for `env`, `download`, `unsloth`, `nllb`, `server`, `gradio`.
Things to read in the report:

* `unsloth.peak_vram_gib`: must leave headroom under 24 GB at length 512 (training uses the same loader).
* `unsloth.loader`: `FastModel` (Glimmer is image-text-to-text; vision frozen).
* `server.backend`: `vllm` or `llama-server`. If neither passes, the demo runs Glimmer in process
  (`uyari demo` works without a server; slower first answer).

## 1. Project setup and verify

```bash
bash scripts/setup_ubuntu.sh project
git config core.hooksPath .githooks                         # privacy check before every commit
cp .env.example .env                                        # META_API_KEY only for paid commands
uv run --no-sync pytest -q                                  # same tests as on Windows
uv run --no-sync uyari validate --strict
uv run --no-sync uyari build --tag data-2026.11 --as-of 2026-11-02 --verify   # content hashes equal Windows'
```

The private name list for the privacy check stays outside the repository. Copy it to the Ubuntu box (for
example `~/uyari-private/privacy_names.txt`) and `export UYARI_PRIVATE_DIR=~/uyari-private` before
committing from there; without it the hook prints "skipped".

## 2. Train and register: one command

```bash
tmux new -s uyari          # hours of training; tmux keeps it running if SSH drops (back in: tmux attach -t uyari)
make all
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

**Registering is automatic.** Each training target ends with `uyari register`, the same rule the Trainer
agent applies after a merge:

* every direction beats the retrieval floor, and
* the model beats whoever holds its slot: +0.5 mean chrF++ on the directions both share, or it adds
  directions (English) and loses at most 0.5 on the shared ones. NLLB v0.2 competes with v0.1 (Spanish
  only, 38.0 / 37.7) for `fast`; Glimmer has no incumbent for `promoted`.

Glimmer and NLLB never compete with each other: the demo serves Glimmer by default and NLLB as its fast
mode. If a model passes, test is scored once and `models/registry.yaml` and its model card are written. If
not, make prints why (`Error 3 (ignored)`), the model stays unregistered and the rest goes on.

Done: `cat models/registry.yaml` shows Glimmer under `promoted` and NLLB v0.2 under `fast`.

* Short on time: `make train-glimmer-spa` trains Glimmer on Spanish ↔ Shawi only (fewer examples) and
  registers it the same way.
* If NLLB v0.2 is not registered, `fast` stays v0.1, whose weights are not in git: copy
  `models/mt-cbt-spa-nllb1.3b@v0.1/weights` (2.6 GB) from the Windows PC, or run `make train-nllb-spa`.
* To serve a model the rule rejected, decide it explicitly:
  `uv run --no-sync uyari register --model models/<name> --force --reason "..."`. The reason and the numbers
  go into the registry history.

## 3. Demo

```bash
make demo          # Glimmer server + Gradio with a share link; open it on a phone
```

The page serves only the registered models and shows English once one of them has the English
directions. Its optional Spanish voice input (Muse Voice Transcribe) asks each visitor for their own Meta
API key; the server's `.env` key is never used (`uyari demo --no-voice` hides it). The share link
(`https://….gradio.live`) is a free tunnel: no ngrok needed, it lasts up to a week or until the process
stops, and it changes on every restart.

## 4. Publish the results

```bash
gh auth login                                  # once, to push from this machine
export UYARI_PRIVATE_DIR=~/uyari-private       # the pre-commit privacy check
git add models languages/cbt_Latn/NEEDS.md reports/side-by-side.html
git commit -m "Glimmer and NLLB v0.2: scores, model cards, registry"
git push
```

Weights and adapters are gitignored, so `git add models` adds only cards, scores, recipes and evaluation
outputs.

## 5. Agents on video

* Self-hosted runner: register this machine with labels `self-hosted, linux, gpu`; create
  `/opt/uyari/.venv` with `UV_PROJECT_ENVIRONMENT=/opt/uyari/.venv bash scripts/setup_ubuntu.sh project`.
* Gatekeeper: `python scripts/make_demo_contribution.py` on a branch, open a PR, the review appears.
* Trainer: merge a contribution; `train.yml` builds, trains NLLB, evaluates, promotes and opens a PR
  with the card and `NEEDS.md`.

## Money

Nothing in this runbook calls a paid API except `uyari transcribe` ($0.18 per audio hour, capped at $2
per run). The demo's voice input is paid by each visitor's own key. `uyari llm spend` shows the ledger.
