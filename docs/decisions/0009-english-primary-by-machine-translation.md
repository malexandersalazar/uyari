# 0009 English as a second primary, machine-translated, and one model per language

Judges, funders and many contributors read English, and an English ↔ Shawi translator reaches more people
than a Spanish-only one. There are no human English ↔ Shawi translations, but every human Shawi translation
was made from a Spanish chunk with a stable `chunk_id`.

So the Spanish primary was machine-translated into English (`uyari primary translate`, Muse Spark 1.3
Contributor: only Spanish is sent, never Shawi). Each English chunk keeps the Spanish chunk's id, split,
domain and paraphrase group, and says `origin=machine_translated` with the model that wrote it. The build
already pairs every human translation with every primary that has its chunk, so English ↔ Shawi rows appear
with no change to the data format.

One model per backend now covers all four directions (recipes take `primaries: [spa_Latn, eng_Latn]`),
so the demo and the registry keep one promoted and one fast model per language. Each direction is evaluated
on its own language pair; English references are machine translations, and the model cards say so.

The Trainer compares a candidate with the incumbent on the directions both share: +0.5 mean chrF++, or, when
the candidate adds directions, no more than 0.5 lost on the shared ones. Every direction must still beat
the retrieval floor.
