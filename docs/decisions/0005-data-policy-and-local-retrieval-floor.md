# 0005 Contributor tier never sees Shawi; the baseline is local retrieval

Muse Spark 1.3 Contributor is cheap because Meta may train on prompts and completions. That is acceptable for
synthetic Spanish and not for community translations. Every model in `config/llm.yaml` has a `data_policy`;
every call declares a `data_class`; `llm/policy.py` refuses community data to an `official_only` model.
Consequences: a hosted "retrieval baseline" and a hosted "reference translation" Gatekeeper
check are replaced by a local character n-gram retrieval floor and by Muse Glimmer on our own GPU.
