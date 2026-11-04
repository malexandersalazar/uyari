# 0010 Training on rented GPUs; serving stays on our own

Muse Glimmer 30B does not fit the 24 GB RTX 4090 for QLoRA training: the 4-bit model alone needs more than the
22 GB free (`check_4090_report.json`). It is trained on a rented Modal H100 80 GB instead
(`scripts/modal_glimmer.py`), with the same code, recipe and library versions as the 4090.

What leaves our hardware: the code, the recipe and the prepared train and validation examples
(`runs/<recipe>/data`), which contain human Shawi translations. They are CC BY 4.0 and already public in this
repository, and a rented GPU runs only our code: unlike the Muse Spark Contributor tier (0005), no one trains on
what it processes. The build's test split never leaves: evaluation, test scoring and registration run on the
4090.

Serving stays on our own hardware: the 4090 serves Unsloth's 4-bit GGUF of the base with the adapter converted
to GGUF (`scripts/lora_to_gguf.py`, `uyari serve start`), and the scores in `scores.json` are of that served
form, not of the model as trained.
