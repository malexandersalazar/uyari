# Runbook: the RTX 4090 (Ubuntu)

Copy-paste order. Every step says what "done" looks like.

## 0. Before the clone (today, in parallel with the code)

```bash
bash scripts/setup_ubuntu.sh check            # throwaway venv in ~/uyari-check-venv
source ~/uyari-check-venv/bin/activate
HF_HUB_ENABLE_HF_TRANSFER=1 python scripts/check_4090.py
```

Done: `check_4090_report.json` has PASS for `env`, `download`, `unsloth`, `nllb`, `server`, `gradio`.
Glimmer is ~60 GB to download: start it first. Things to read in the report:

* `unsloth.peak_vram_gib`: must leave headroom under 24 GB at length 512 (training uses the same loader).
* `unsloth.loader`: `FastModel` (Glimmer is image-text-to-text; vision frozen).
* `server.backend`: `vllm` or `llama-server`. If neither passes, the demo runs Glimmer in process
  (`uyari demo` works without a server; slower first answer).

## 1. Clone and verify

```bash
git clone https://github.com/malexandersalazar/uyari.git && cd uyari
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

Model weights are not in git. The demo's current fast model, `models/mt-cbt-spa-nllb1.3b@v0.1/weights`
(2.6 GB), is on the Windows PC: copy that folder over, or let `make train-nllb` below replace it.

## 2. Floor, NLLB, Glimmer (Spanish and English <-> Shawi)

The English sentences (`primary/eng_Latn`) are machine-translated from the Spanish with the same chunk
ids, so every human Shawi translation pairs with both. One model per backend covers all four directions.

```bash
make floor                              # retrieval floor, 4 directions (seconds)
make train-nllb                         # about 1 h -> models/mt-cbt-nllb1.3b@v0.2
make train-glimmer                      # hours -> models/mt-cbt-glimmer30b-qlora@v0.1
                                        # watch runs/cbt.mt.glimmer-qlora/train_log.jsonl
```

Short on time: `make train-glimmer-spa` trains Glimmer on Spanish <-> Shawi only (fewer examples,
`models/mt-cbt-spa-glimmer30b-qlora@v0.1`).

## 3. Register, cards, test once

Register Glimmer as the demo default, and the new NLLB as the fast model if its Spanish scores are not
worse than v0.1's (38.0 / 37.7 validation chrF++):

```bash
uv run --no-sync python -c "from uyari.paths import Paths; from uyari.registry import set_slot; p=Paths.default(); set_slot(p,'mt','cbt_Latn','promoted','mt-cbt-glimmer30b-qlora@v0.1','demo default: open-weight Muse on our GPU'); set_slot(p,'mt','cbt_Latn','fast','mt-cbt-nllb1.3b@v0.2','fast mode, Spanish and English')"
uv run --no-sync uyari eval --model models/mt-cbt-glimmer30b-qlora@v0.1 --final   # once
uv run --no-sync uyari eval --model models/mt-cbt-nllb1.3b@v0.2 --final           # once
uv run --no-sync python -c "from uyari.paths import Paths; from uyari.pipelines.mt.card import write_card; p=Paths.default(); [write_card(p, p.models/m) for m in ('mt-cbt-glimmer30b-qlora@v0.1','mt-cbt-nllb1.3b@v0.2')]"
make report needs
```

The demo picks up English automatically once a registered model has the English directions.

## 4. Demo

```bash
make demo          # Glimmer server + Gradio with a share link; open it on a phone
```

The page serves only our fine-tuned models. Its optional Spanish voice input (Muse Voice Transcribe) asks
each visitor for their own Meta API key; the server's `.env` key is never used (`uyari demo --no-voice`
hides it). The share link (`https://….gradio.live`) is a free tunnel: no ngrok needed, it lasts up to a week
or until the process stops, and it changes on every restart.

## 5. Agents on video

* Self-hosted runner: register this machine with labels `self-hosted, linux, gpu`; create
  `/opt/uyari/.venv` with `UV_PROJECT_ENVIRONMENT=/opt/uyari/.venv bash scripts/setup_ubuntu.sh project`.
* Gatekeeper: `python scripts/make_demo_contribution.py` on a branch, open a PR, the review appears.
* Trainer: merge a contribution; `train.yml` builds, trains NLLB, evaluates, promotes and opens a PR
  with the card and `NEEDS.md`.

## Money

Nothing in this runbook calls a paid API except `uyari transcribe` ($0.18 per audio hour, capped at $2
per run). The demo's voice input is paid by each visitor's own key. `uyari llm spend` shows the ledger.
