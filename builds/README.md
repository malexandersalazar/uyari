# builds/

`uyari build --tag data-YYYY.MM` writes `builds/<tag>/MANIFEST.json` (in git) and the tables (not in git;
rebuild them from the tag; `--verify` recomputes and compares hashes).

| Table | Columns |
|---|---|
| `<lang>/mt.parquet`, `mt.test.parquet` | `chunk_id, split, domain, src_lang, src_origin, src_text, tgt_lang, tgt_text, contribution, translator_id, provenance, license` (the source is always a primary; trainers swap for the other direction) |
| `<lang>/asr.parquet`, `asr.test.parquet` | `file, lang, transcript, speaker_id, style, split, chunk_id, contribution, license` |
| `<lang>/tts.parquet`, `tts.test.parquet` | `file, lang, transcript, speaker_id, split, chunk_id, contribution, license` (read clips only) |

`MANIFEST.json`: `tag`, `as_of`, `git`, `uyari_version`, and per language `contributions.included/excluded`
(with reasons), `rows_excluded` (reasons), `counts`, `licenses`, and per table `rows` by split, `sha256` /
`test_sha256` (file bytes) and `content_sha256` / `test_content_sha256` (canonical rows, identical on every OS).
