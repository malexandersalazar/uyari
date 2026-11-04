# French primary (`fra_Latn`)

The French twin of the Spanish primary corpus: **111,363 sentences, machine-translated from the Spanish with
the same chunk ids**, so every human translation into an Indigenous language (made from the Spanish) also
pairs with French.

| | |
|---|---|
| Files | `chunks/translated/2026-11_musespark13c_0001.csv` to `_0006.csv`, the same batch files as English |
| Made by | `uyari primary translate --target fra_Latn` with **Muse Spark 1.3 Contributor**, November 2026 |
| What was sent | Spanish sentences only (official language), never Shawi |
| Cost | **US$ 1.97** for 111,363 sentences (20 per request) |
| Checks | one answer per id, 1–150 words, not left in Spanish |
| Provenance on every row | `origin=machine_translated`, `gen_model`, `provider`, `prompt_version`, `source_batch_id` |
| Split, domain, paraphrase group | copied from the Spanish chunk, so no test sentence leaks into training |

Training recipes choose their official languages (`primaries:` in `recipes/*.yaml`); the current ones use
Spanish and English only. Into French, models would be measured against machine-translated references.
