"""The design matrix (``primary/<lang>/matrix.yaml``) and ``prompt_version``."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from uyari.csvio import read_yaml
from uyari.gen.prompts import SYSTEM_PROMPT, build_prompt

# Axes that shape the prompt. Validation settings are excluded on purpose: changing a
# post-processing threshold must not change prompt_version.
_PROMPT_AXES = ("domains", "actos", "registros", "tiempos", "polaridades", "personas",
                "perfiles", "tonos", "anclas", "lengths", "discurso_conectado",
                "texts_per_request", "n_palabras_ancla")


@dataclass
class Matrix:
    path: Path
    cfg: dict

    @classmethod
    def load(cls, path: Path) -> Matrix:
        return cls(path=Path(path), cfg=read_yaml(path))

    def __getitem__(self, k):
        return self.cfg[k]

    @property
    def lengths(self) -> dict:
        return self.cfg["lengths"]

    @property
    def validation(self) -> dict:
        return self.cfg.get("validation", {})

    def prompt_version(self) -> str:
        return prompt_version(self.cfg)


def _probe_units(cfg: dict) -> list[dict]:
    """Four renders covering every template branch (connected x anchors)."""
    base = {"n_texts": cfg["texts_per_request"], "domain_l1": "D", "domain_l2": "M",
            "acto_comunicativo": "A", "register": "R", "tiempo_aspecto": "T", "polaridad": "P",
            "persona_deixis": "X", "perfil_hablante": "H", "tono_emocional": "N",
            "length_bucket": next(iter(cfg["lengths"]))}
    out = []
    for conectado in (False, True):
        for anclas in ([], ["a1", "a2"]):
            out.append({**base, "discurso_conectado": conectado, "palabras_ancla": anclas})
    return out


def prompt_version(cfg: dict) -> str:
    """Hash of the system prompt, the template (rendered on probe units) and the axes."""
    payload = {
        "system": SYSTEM_PROMPT,
        "template": [build_prompt(u, cfg["lengths"]) for u in _probe_units(cfg)],
        "axes": {k: cfg.get(k) for k in _PROMPT_AXES},
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return "pv-" + hashlib.sha256(blob).hexdigest()[:12]
