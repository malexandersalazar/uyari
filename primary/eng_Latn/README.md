# English primary (`eng_Latn`)

The English twin of the Spanish primary corpus: **111,363 sentences, machine-translated from the Spanish
with the same chunk ids**, so every human translation into an Indigenous language (made from the Spanish)
also pairs with English. This is how Uyari trains English ↔ Shawi without any English ↔ Shawi human
translations.

| | |
|---|---|
| Files | `chunks/translated/2026-11_musespark13c_0001.csv` (the first 11,977 Spanish chunks), then `_0002` to `_0006` (one per new Spanish batch, same id) |
| Made by | `uyari primary translate` with **Muse Spark 1.3 Contributor** |
| What was sent | Spanish sentences only (official language), never Shawi |
| Cost | **US$ 1.74** for 111,363 sentences: $0.186 for the first 11,977 (599 requests of 20), $1.56 for the rest |
| Rejected | 0 (checks: one answer per id, 1–150 words, not left in Spanish) |
| Provenance on every row | `origin=machine_translated`, `gen_model`, `provider`, `prompt_version`, `source_batch_id` |
| Split, domain, paraphrase group | copied from the Spanish chunk, so no test sentence leaks into training |

**What this means for scores.** The Shawi side is always human. Into English, models are measured against
machine-translated references, and the model cards say so.

Portuguese, French, German, Italian, Hindi and Thai are made the same way, with the same batch files
(`primary/<lang>/`). A new Spanish batch is translated into every language with its own id:

```bash
uv run uyari primary translate --batch <batch> --source-batch <batch> --target por_Latn --estimate
```

A chunk a language already has is never translated again, so re-running a command only fills gaps.
