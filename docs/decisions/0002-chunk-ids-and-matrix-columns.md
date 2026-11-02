# 0002 Keep the original ids and every matrix column

The 32-hex id each Spanish sentence was generated with is its `chunk_id`; the translations already reference
it, so it is stable by construction. The chunk schema is extended to the data: every design-matrix column of
the corpus is kept with its original name (`domain_l1`, `acto_comunicativo`, ..., `source_custom_id` as the
paraphrase-group id). Translations live in contributions, not next to the Spanish text.
