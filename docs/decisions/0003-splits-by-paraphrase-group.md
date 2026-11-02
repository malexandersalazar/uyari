# 0003 Splits by paraphrase group

Each generation request produced ~10 near-paraphrases (`source_custom_id`). Splitting by chunk would put
paraphrases of test sentences in training. The unit is the group. First assignment takes ~300 translated
chunks each for validation and test from translated groups (only 36% of the corpus is translated, so drawing
from all groups would leave ~100), stratified by domain, ordered by hash. A regenerated cell (`regen_of`)
inherits its source group's split. Splits are frozen once written.
