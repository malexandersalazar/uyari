# config/

`llm.yaml`: model catalog (endpoint environment variables, API kind, prices per 1M tokens or per audio hour,
`data_policy`), the USD 150 budget and per-run caps, estimate settings, and the default model for
official-language data and for community data. Read by `src/uyari/llm/`. Secrets live in `.env` (gitignored).
