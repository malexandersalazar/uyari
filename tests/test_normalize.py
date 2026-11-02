from uyari.text.normalize import (
    CANONICAL_APOSTROPHE,
    apostrophe_variants_in,
    dedup_key,
    normalize_indigenous,
    normalize_official,
    word_count,
)


def test_apostrophe_variants_become_modifier_letter():
    for v in ["'", "’", "´", "`", "‘", "ʻ"]:
        assert normalize_indigenous(f"ipi{v}") == "ipi" + CANONICAL_APOSTROPHE
    assert CANONICAL_APOSTROPHE == "ʼ"


def test_whitespace_newlines_and_punctuation_spacing():
    assert normalize_indigenous("¿ Ku  nañanteranwe\nnuyahsha ?") == "¿Ku nañanteranwe nuyahsha?"
    assert normalize_official("  perdonar\t y   seguir ") == "perdonar y seguir"


def test_official_text_keeps_apostrophes():
    assert normalize_official("l'eau") == "l'eau"


def test_nfc():
    decomposed = "niño"  # n + combining tilde
    assert normalize_official(decomposed) == "niño"


def test_variant_detection_and_counts():
    assert apostrophe_variants_in("wa'kirawe ma´ni") == ["'", "´"]
    assert word_count("¿Qué pasa, hermano?") == 3
    assert dedup_key("  Río  ") == dedup_key("río")
