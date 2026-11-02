# contributions/

One folder per contribution, `<YYYY-MM>_<org>_<nnnn>`, immutable once merged. See [`contributing/`](../../../contributing/).

| File | Columns / fields | Required when | Read by |
|---|---|---|---|
| `contribution.yaml` | `id, language, variety, contributor_id, organization, collection_dates, provenance{text,audio}, license, consent{template,authority}, compensated` | always | validate; build (license and provenance on every row) |
| `pairs.csv` | `chunk_id, text, replaces, translator_id, notes` | text contributions | build: `mt` table and audio transcripts |
| `audio.csv` | `file, chunk_id, transcript, speaker_id, style, device, notes` | audio contributions | build: `asr`, and `tts` for read clips |
| `speakers.csv` | `speaker_id, age_band, sex, first_language, consent_ref` | whenever `audio.csv` exists | validate |
| `review.yaml` | `reviewed_by, decided_on, agent_score, decision, notes` | added by the merge commit | build (`revoked` excludes) |
| `wav/` | 16/48 kHz, mono, PCM 16-bit, 1–20 s, peak −12 to −1 dBFS, under 40% silence | audio | validate, build |
