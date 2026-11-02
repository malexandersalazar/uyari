"""Chat prompts for causal-LM translators (Glimmer QLoRA and the LLM baselines)."""

from __future__ import annotations

LANG_NAMES = {
    "spa_Latn": "Spanish",
    "eng_Latn": "English",
    "por_Latn": "Portuguese",
    "fra_Latn": "French",
    "cbt_Latn": "Shawi (Chayahuita)",
    "quy_Latn": "Ayacucho Quechua",
    "quz_Latn": "Cusco Quechua",
    "ayr_Latn": "Aymara",
    "cni_Latn": "Asháninka",
    "agr_Latn": "Awajún",
    "shp_Latn": "Shipibo-Konibo",
}

SYSTEM = (
    "You are a professional translator between Indigenous languages and official languages. "
    "Translate faithfully, without adding or removing information, and reply with the translation only."
)


def name(lang: str) -> str:
    return LANG_NAMES.get(lang, lang)


def user_prompt(src_lang: str, tgt_lang: str, text: str) -> str:
    return f"Translate from {name(src_lang)} to {name(tgt_lang)}:\n{text}"


def messages(src_lang: str, tgt_lang: str, text: str) -> list[dict]:
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_prompt(src_lang, tgt_lang, text)}]
