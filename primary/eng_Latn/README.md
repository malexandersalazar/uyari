# English primary (`eng_Latn`)

The English twin of the Spanish primary corpus: **11,977 sentences, machine-translated from the Spanish
with the same chunk ids**, so every human translation into an Indigenous language (made from the Spanish)
also pairs with English. This is how Uyari trains English ↔ Shawi without any English ↔ Shawi human
translations.

| | |
|---|---|
| File | `chunks/translated/2026-11_musespark13c_0001.csv` |
| Made by | `uyari primary translate --batch 2026-11_musespark13c_0001` with **Muse Spark 1.3 Contributor** |
| What was sent | Spanish sentences only (official language), never Shawi |
| Cost | **US$ 0.186** for 11,977 sentences (599 requests of 20; estimate before sending: $0.23) |
| Rejected | 0 (checks: one answer per id, 1–150 words, not left in Spanish) |
| Provenance on every row | `origin=machine_translated`, `gen_model`, `provider`, `prompt_version`, `source_batch_id` |
| Split, domain, paraphrase group | copied from the Spanish chunk, so no test sentence leaks into training |

**What this means for scores.** The Shawi side is always human. Into English, models are measured against
machine-translated references, and the model cards say so.

Other official languages (Portuguese, French, …) are added the same way:

```bash
uv run uyari primary translate --batch <YYYY-MM>_<model>_<nnnn> --target por_Latn --estimate
```
