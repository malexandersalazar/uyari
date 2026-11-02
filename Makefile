# Linux / the RTX 4090. On Windows call the `uyari` commands directly.
PY  ?= uv run --no-sync
TAG ?= data-2026.11

.PHONY: env-check setup test validate build floor train-nllb train-glimmer train-nllb-spa train-glimmer-spa serve demo needs report privacy

env-check:        ## prove the GPU stack (Unsloth, NLLB, vLLM, Gradio) before anything else
	python scripts/check_4090.py
setup:
	bash scripts/setup_ubuntu.sh project
test:
	$(PY) pytest -q
validate:
	$(PY) uyari validate
build:
	$(PY) uyari build --tag $(TAG)
floor:            ## retrieval floor for all four directions (Spanish and English <-> Shawi)
	$(PY) uyari eval --model retrieval --recipe recipes/cbt.mt.nllb-1.3b.yaml
train-nllb:       ## NLLB 1.3B, Spanish + English <-> Shawi (about an hour)
	$(PY) uyari prepare --recipe recipes/cbt.mt.nllb-1.3b.yaml
	$(PY) uyari train --recipe recipes/cbt.mt.nllb-1.3b.yaml
	$(PY) uyari eval --model models/mt-cbt-nllb1.3b@v0.2
train-glimmer:    ## Muse Glimmer 30B QLoRA, Spanish + English <-> Shawi (the headline model; hours)
	$(PY) uyari prepare --recipe recipes/cbt.mt.glimmer-qlora.yaml
	$(PY) uyari train --recipe recipes/cbt.mt.glimmer-qlora.yaml
	$(PY) uyari eval --model models/mt-cbt-glimmer30b-qlora@v0.1
train-nllb-spa:   ## the Spanish-only NLLB (what the demo serves today)
	$(PY) uyari prepare --recipe recipes/cbt-spa.mt.nllb-1.3b.yaml
	$(PY) uyari train --recipe recipes/cbt-spa.mt.nllb-1.3b.yaml
	$(PY) uyari eval --model models/mt-cbt-spa-nllb1.3b@v0.1
train-glimmer-spa: ## fallback if time is short: Glimmer on Spanish <-> Shawi only
	$(PY) uyari prepare --recipe recipes/cbt-spa.mt.glimmer-qlora.yaml
	$(PY) uyari train --recipe recipes/cbt-spa.mt.glimmer-qlora.yaml
	$(PY) uyari eval --model models/mt-cbt-spa-glimmer30b-qlora@v0.1
serve:
	$(PY) uyari serve start
demo: serve
	$(PY) uyari demo --share
needs:
	$(PY) uyari needs --language cbt_Latn
report:
	$(PY) uyari report side-by-side --n 20
privacy:
	$(PY) uyari privacy-check
