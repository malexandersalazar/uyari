# 0006 Spanish generation runs on Meta models, with the same prompt

The first 10,000 Spanish chunks were generated in June 2026 with Claude Opus 4.8. Generation now runs on
Meta models: Muse Spark 1.3 Contributor through the Meta Model API, or Muse Glimmer 30B on our own GPU.

To make the switch measurable, `uyari generate` keeps the first batch's design matrix, sampling rules,
plan-on-disk with idempotent re-runs, `custom_id` group key, parsing, validation and embedding
deduplication, and the identical prompt (`prompt_version` pv-337a163d411a is pinned by the tests).
Regenerating 200 of its cells with Muse Spark cost 3.3% as much per 1,000 chunks, with 100% well-formed
responses and slightly more varied text, and slightly lower length-bucket compliance
(`reports/gen-comparison.md`). Muse Glimmer removes the API cost entirely and keeps everything on our
hardware.

Additions: a Spanish check, deduplication against the whole primary, cost estimates before every run, per-run
caps and a spend ledger. New-cell plans interleave micro-scenarios so even small batches cover every domain.
