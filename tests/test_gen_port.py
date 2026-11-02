"""Generation keeps the June 2026 batch's matrix and prompt byte-identical (pinned prompt_version),
and its parsing and validation rules."""

from pathlib import Path

import pytest

from uyari.csvio import read_yaml
from uyari.gen.collect import TextValidator, parse_texts
from uyari.gen.matrix import Matrix
from uyari.gen.prompts import SYSTEM_PROMPT, build_prompt

REPO = Path(__file__).resolve().parents[1]
PINNED = "pv-337a163d411a"  # recorded on every chunk of primary/spa_Latn/.../2026-06_opus48_0001.csv


@pytest.fixture(scope="module")
def matrix():
    return Matrix.load(REPO / "primary/spa_Latn/matrix.yaml")


def test_prompt_version_is_pinned(matrix):
    assert matrix.prompt_version() == PINNED, "prompt or matrix changed: new batches would not be comparable"


def test_prompt_version_matches_the_published_batches(matrix):
    import csv

    for f in (REPO / "primary/spa_Latn/chunks/generated").glob("*.csv"):
        with f.open(encoding="utf-8", newline="") as fh:
            versions = {r["prompt_version"] for r in csv.DictReader(fh)}
        assert versions == {PINNED}, f.name


def test_prompt_renders_every_branch(matrix):
    base = {"n_texts": 10, "domain_l1": "salud_cuerpo", "domain_l2": "el niño tiene fiebre",
            "acto_comunicativo": "consejo_advertencia", "register": "casual", "tiempo_aspecto": "futuro",
            "polaridad": "negativo", "persona_deixis": "3a", "perfil_hablante": "partera",
            "tono_emocional": "preocupado"}
    plain = build_prompt({**base, "length_bucket": "media", "discurso_conectado": False, "palabras_ancla": []},
                         matrix.lengths)
    rich = build_prompt({**base, "length_bucket": "larga", "discurso_conectado": True,
                         "palabras_ancla": ["fiebre", "remedio"]}, matrix.lengths)
    assert "Genera 10 textos" in plain and "Palabras ancla" not in plain
    assert "Genera 10 pasajes" in rich and "Palabras ancla: fiebre, remedio" in rich
    assert SYSTEM_PROMPT.startswith("Eres un generador experto")


def test_parse_texts():
    assert parse_texts('```json\n{"texts": ["a", "b"]}\n```') == ["a", "b"]
    assert parse_texts('Aquí tienes: {"texts": ["uno"]} gracias') == ["uno"]
    assert parse_texts("nada") == []


def test_validator_reasons():
    v = TextValidator(read_yaml(REPO / "primary/spa_Latn/matrix.yaml")["validation"], set(),
                      lexicon={"traería", "plátano", "verde", "bien", "fresco"})
    unit = {"wc_min": 3, "wc_max": 8}
    assert v.check("Mañana vamos a la chacra con mi hermano.", unit)[0]
    assert v.check("Mañana vamos a la chacra con mi hermano.", unit)[1] == "exact_duplicate"
    assert v.check("Fuimos al supermercado con la familia hoy.", unit)[1] == "banned_term"
    assert v.check("Uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce.", unit)[1] == \
        "length_out_of_bucket"
    assert v.check("Kuwa nunsha ihpi patere wakirawe nanpi.", unit)[1] == "not_spanish"
    assert v.check("Traería plátano verde bien fresco", unit)[0], "short valid Spanish must pass via the lexicon"
