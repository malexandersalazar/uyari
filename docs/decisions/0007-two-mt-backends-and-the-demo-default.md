# 0007 Two MT backends; Glimmer is the demo default

NLLB-200 1.3B trains in under an hour and is a strong low-resource baseline, but its weights are CC BY-NC and
it is not an open-weight Muse model. Muse Glimmer 30B (Apache 2.0) is trained with QLoRA on the 4090. The demo
serves Glimmer by default and NLLB as fast mode regardless of which scores higher, because the project's claim
is "runs on an open-weight Muse model on our own hardware"; both model cards state both scores and why.
NLLB's tokenizer has no `ʼ` (U+02BC), so its recipes map it to `'` at the model edges (a reversible codec,
checked on the training data); storage and evaluation always use `ʼ`.
