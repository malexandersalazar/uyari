"""Language checks used by generation (is this Spanish?) and the Gatekeeper (does a Shawi
row look like Spanish, or like nothing in the corpus?).

* ``looks_spanish``: function-word heuristic, no model, for synthetic Spanish post-processing.
* ``CharNgramLangID``: character n-gram classifier trained on accepted text of the primary and
  of the language (scikit-learn, seconds to train, nothing leaves the machine).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SPANISH_FUNCTION_WORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al", "a", "en", "y", "o", "que",
    "por", "para", "con", "sin", "se", "no", "es", "son", "está", "están", "mi", "mis", "tu", "tus", "su",
    "sus", "lo", "le", "les", "me", "te", "nos", "yo", "tú", "él", "ella", "ellos", "ellas", "nosotros",
    "muy", "más", "pero", "cuando", "como", "porque", "si", "ya", "hay", "este", "esta", "ese", "esa",
    "aquí", "allí", "también", "hasta", "desde", "sobre", "entre", "todo", "toda", "todos", "todas",
    "vamos", "voy", "va", "fue", "era", "será", "tengo", "tiene", "hace", "dice", "puedo", "puede",
}
_WORD = re.compile(r"[a-záéíóúüñ]+", re.IGNORECASE)


def function_word_share(text: str) -> float:
    words = [w.lower() for w in _WORD.findall(text)]
    if not words:
        return 0.0
    return sum(w in SPANISH_FUNCTION_WORDS for w in words) / len(words)


def looks_spanish(text: str, min_share: float = 0.12) -> bool:
    words = _WORD.findall(text)
    if len(words) < 4:
        return function_word_share(text) > 0 or bool(re.search(r"[áéíóúñ¿¡]", text))
    return function_word_share(text) >= min_share


@dataclass
class CharNgramLangID:
    """Binary-or-more classifier; ``fit({"cbt_Latn": [...], "spa_Latn": [...]})``."""

    model: object = None
    labels: list[str] | None = None

    def fit(self, texts_by_label: dict[str, list[str]]) -> CharNgramLangID:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline

        X, y = [], []
        for label, texts in texts_by_label.items():
            X += texts
            y += [label] * len(texts)
        self.model = make_pipeline(
            TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 4), sublinear_tf=True, min_df=2),
            LogisticRegression(max_iter=2000, C=4.0))
        self.model.fit(X, y)
        self.labels = list(self.model.classes_)
        return self

    def predict(self, texts: list[str]) -> list[tuple[str, float]]:
        probs = self.model.predict_proba(texts)
        return [(self.labels[i.argmax()], float(i.max())) for i in probs]
