# Linux / the RTX 4090. On Windows call the `uyari` commands directly.
PY  ?= uv run --no-sync
TAG ?= data-2026.11-six
AS_OF ?= 2026-11-02
OFFICIALS ?= spa_Latn,eng_Latn,fra_Latn,deu_Latn,ita_Latn,por_Latn
NLLB ?= models/mt-cbt-nllb1.3b@v0.3
GLIMMER ?= models/mt-cbt-glimmer30b-qlora@v0.4
GLIMMER_RECIPE ?= recipes/cbt.mt.glimmer-qlora-r64.yaml
.DEFAULT_GOAL := env-check

.PHONY: all env-check setup test validate build floor train-nllb train-glimmer train-nllb-spa train-glimmer-spa serve demo needs report privacy

# Every train-* target ends with `uyari register`: the Trainer's promotion rule (beats the retrieval floor in
# every direction and the slot's incumbent), then test once, models/registry.yaml and the model card.
# A model that fails the rule is left unregistered: make prints why and goes on ("Error 3 (ignored)").

all: build floor train-nllb train-glimmer needs report   ## everything after setup, in order (hours: run it in tmux)

env-check:        ## prove the GPU stack (Unsloth, NLLB, vLLM, Gradio) before anything else
	python scripts/check_4090.py
setup:
	bash scripts/setup_ubuntu.sh project
test:
	$(PY) pytest -q
validate:
	$(PY) uyari validate
build:            ## the recipes' official languages only, so a new primary/ folder never changes a tag
	$(PY) uyari build --tag $(TAG) --as-of $(AS_OF) --officials $(OFFICIALS)
floor:            ## retrieval floor for all twelve directions (six official languages <-> Shawi)
	$(PY) uyari eval --model retrieval --recipe recipes/cbt.mt.nllb-1.3b.yaml
train-nllb:       ## NLLB 1.3B, six official languages <-> Shawi (about an hour on the 4090) -> the fast slot
	$(PY) uyari prepare --recipe recipes/cbt.mt.nllb-1.3b.yaml
	$(PY) uyari train --recipe recipes/cbt.mt.nllb-1.3b.yaml
	$(PY) uyari eval --model $(NLLB)
	-$(PY) uyari register --model $(NLLB)
# Glimmer trains on a rented Modal H100 (`uv run modal token new` once; the 4-bit model does not fit the 4090
# for training) and is scored, registered and served here: the adapter as GGUF on llama-server.
train-glimmer:    ## Muse Glimmer 30B QLoRA rank 64, six languages <-> Shawi (about 2 h on Modal, about US$7) -> promoted
	$(PY) uyari prepare --recipe $(GLIMMER_RECIPE)
	$(PY) modal run scripts/modal_glimmer.py --step train --recipe $(GLIMMER_RECIPE)
	$(PY) modal volume get --force uyari-glimmer root/$(GLIMMER) models/
	$(PY) python scripts/lora_to_gguf.py $(GLIMMER)/adapter
	-$(PY) uyari serve stop
	$(PY) uyari serve start --adapter mt-cbt=$(GLIMMER)/adapter
	$(PY) uyari eval --model $(GLIMMER)
	-$(PY) uyari register --model $(GLIMMER)
train-nllb-spa:   ## the Spanish-only NLLB (v0.1; no longer served)
	$(PY) uyari prepare --recipe recipes/cbt-spa.mt.nllb-1.3b.yaml
	$(PY) uyari train --recipe recipes/cbt-spa.mt.nllb-1.3b.yaml
	$(PY) uyari eval --model models/mt-cbt-spa-nllb1.3b@v0.1
train-glimmer-spa: ## fallback: Glimmer on Spanish <-> Shawi only, on Modal like train-glimmer
	$(PY) uyari prepare --recipe recipes/cbt-spa.mt.glimmer-qlora.yaml
	$(PY) modal run scripts/modal_glimmer.py --step train --recipe recipes/cbt-spa.mt.glimmer-qlora.yaml
	$(PY) modal volume get --force uyari-glimmer root/models/mt-cbt-spa-glimmer30b-qlora@v0.1 models/
	$(PY) python scripts/lora_to_gguf.py models/mt-cbt-spa-glimmer30b-qlora@v0.1/adapter
	-$(PY) uyari serve stop
	$(PY) uyari serve start --adapter mt-cbt-spa=models/mt-cbt-spa-glimmer30b-qlora@v0.1/adapter
	$(PY) uyari eval --model models/mt-cbt-spa-glimmer30b-qlora@v0.1
	-$(PY) uyari register --model models/mt-cbt-spa-glimmer30b-qlora@v0.1
serve:            ## Muse Glimmer with the registered adapter on llama-server (4-bit GGUF, 16.5 GB of the 4090)
	$(PY) uyari serve start
demo:             ## the page (it starts the Glimmer server if needed, stops it on exit); a public share link
	$(PY) uyari demo --share
needs:
	$(PY) uyari needs --language cbt_Latn
report:
	$(PY) uyari report side-by-side --n 20
privacy:
	$(PY) uyari privacy-check
