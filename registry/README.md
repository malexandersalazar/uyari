# registry/

Code tables the validator resolves every language id against. They are a **subset** of the
standards, covering the pilot and official languages; add a row when a language is added.

| File | Columns | Source |
|---|---|---|
| `iso639-3.tsv` | `code, name, scope, type, note` | SIL ISO 639-3 code tables (https://iso639-3.sil.org) |
| `iso15924.tsv` | `code, name` | Unicode ISO 15924 (https://unicode.org/iso15924) |
| `glottolog.csv` | `glottocode, name, iso639_3` | Glottolog (https://glottolog.org) |

ISO 639-3 reserves `qaa`–`qtz` for local use; the validator accepts them without a row.
The test fixture language `qaa_Latn` uses that range.

Read by: `src/uyari/validate.py`.
