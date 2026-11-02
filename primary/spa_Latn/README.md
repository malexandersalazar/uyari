# primary/spa_Latn

| Batch | Chunks | Made by | Notes |
|---|---|---|---|
| `2026-06_opus48_0001` | 10,000 | Claude Opus 4.8 (Message Batches), June 2026 | First batch: 4 of the matrix's 15 domains, 37 micro-scenarios; 3,575 have Shawi translations |
| `2026-11_musespark13c_0001` | 1,977 | **Muse Spark 1.3 Contributor** (Meta Model API) | Same 200 cells, same prompt (`prompt_version` pv-337a163d411a); groups carry `regen_of` and inherit its split |

## Why generation moved to Meta

We regenerated 200 cells of the first batch with the identical prompt and matrix, so only the model
changed ([`reports/gen-comparison.md`](../../reports/gen-comparison.md)):

| | Claude Opus 4.8 | Muse Spark 1.3 Contributor | Muse Glimmer 30B (local) |
|---|---|---|---|
| Cost per 1,000 chunks | ~$0.64 (estimate, batch discount) | **$0.021** (exact, ledger): 3.3% | **$0 API cost**: runs on our RTX 4090 |
| Requests returning exactly 10 texts | 96.5% (after filtering) | **100%** | not yet measured |
| Distinct-2 / type-token ratio per cell | 0.870 / 0.556 | **0.891 / 0.588** | not yet measured |
| Strict length-bucket compliance | **94.5%** | 89.0% | not yet measured |
| Throughput | asynchronous batch | 428 chunks per minute | GPU-bound |

At 3.3% of the cost, Muse Spark gives the same structure and slightly more varied Spanish, and it
returned well-formed output for every request. Claude kept the length buckets a little more often. Muse Glimmer
generates the same cells on our own GPU (`uyari generate plan --model glimmer-local ...`), with no API
cost and nothing leaving our hardware. The Contributor tier is used for synthetic Spanish only: Meta may
train on its prompts, so it never sees Shawi.

* `matrix.yaml`: the design matrix (pinned by `tests/test_gen_port.py`).
* `primary.yaml`: batch provenance.
* Splits: validation and test hold about 330 translated chunks each, as whole paraphrase groups.
