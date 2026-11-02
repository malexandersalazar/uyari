"""Generation prompts: the exact prompt used for the June 2026 batch.

The prompt text does not change between models, only the transport, so a comparison between
batches measures models, not prompt edits. ``tests/test_gen_port.py`` pins ``prompt_version``
(pv-337a163d411a, recorded on every chunk of that batch).
"""

from __future__ import annotations

SYSTEM_PROMPT = (
    "Eres un generador experto de oraciones en español para construir un corpus que "
    "será traducido al shawi (chayahuita), una lengua amazónica del Perú. Escribes "
    "español claro, cotidiano y concreto, propio de la vida de una comunidad rural "
    "amazónica, con ortografía correcta (tildes y la letra ñ). Respondes SIEMPRE y "
    "ÚNICAMENTE con JSON válido, sin texto adicional ni marcas de código."
)


def build_prompt(u: dict, lengths: dict) -> str:
    """Render the user prompt for one generation unit.

    ``lengths`` maps bucket -> {"phrase", ...} (``matrix.yaml``).
    """
    length_phrase = lengths[u["length_bucket"]]["phrase"]
    conectado = u.get("discurso_conectado", False)
    anclas = u.get("palabras_ancla") or []
    unidad_sing = "pasaje" if conectado else "texto"
    unidad_plur = "pasajes" if conectado else "textos"
    if conectado:
        forma_regla = (
            f"- Cada {unidad_sing} debe ser un texto COHESIVO de 3 a 6 oraciones "
            "encadenadas entre sí: usa conectores, anáfora y un mismo hilo temático. "
            "NO es una lista de oraciones sueltas ni una sola oración larga; es un "
            "párrafo que fluye de forma natural.\n"
        )
    else:
        forma_regla = (
            f"- Cada {unidad_sing} es independiente y autónomo; no encadenes unos con "
            "otros ni los conviertas en un párrafo.\n"
        )
    linea_anclas = f"Palabras ancla: {', '.join(anclas)}\n" if anclas else ""
    regla_anclas = (
        f"- PALABRAS ANCLA: reparte las palabras ancla entre los {u['n_texts']} "
        f"{unidad_plur} de forma NATURAL: cada palabra ancla debe aparecer en al "
        f"menos uno de los {unidad_plur} (en cualquier forma flexionada), pero NO "
        f"metas todas las anclas en cada {unidad_sing} ni fuerces una palabra "
        "donde no encaje.\n"
    ) if anclas else ""
    return f"""Genera {u['n_texts']} {unidad_plur} en ESPAÑOL, DISTINTOS entre sí.

Tema: {u['domain_l1']} > {u['domain_l2']}
Acto comunicativo: {u['acto_comunicativo']}
Registro: {u['register']}
Tiempo/aspecto verbal predominante: {u['tiempo_aspecto']}
Polaridad/modalidad: {u['polaridad']}
Persona/deixis: {u['persona_deixis']}
Perfil del hablante: {u['perfil_hablante']}
Tono: {u['tono_emocional']}
{linea_anclas}Longitud de cada {unidad_sing}: {length_phrase}

REGLAS:
{forma_regla}{regla_anclas}- Escribe español con ortografía correcta: usa tildes y la letra ñ donde corresponda.
  No elimines ni reemplaces caracteres del español (NO escribas "nino" por "niño",
  ni "rio" por "río").
- Lenguaje cotidiano, concreto y simple. Frases naturales, no artificiales.
- El contenido debe poder existir en la vida de una comunidad amazónica rural
  (familia, río, monte, chacra, pesca, caza, comida, salud, clima, animales,
  plantas, relaciones, trabajo comunal).
- PROHIBIDO: tecnicismos científicos, jerga, marcas comerciales, nombres propios
  de personas o lugares reales, referencias urbanas (metro, semáforo, rascacielos,
  supermercado), finanzas abstractas, tecnología especializada.
- Conceptos puente (salud pública, escuela, vacunas, derechos, trámites) SÍ se
  permiten, pero en lenguaje llano que un hablante explicaría a un vecino.
- Respeta el tiempo verbal, la polaridad y la persona indicados.
- Cada {unidad_sing} debe ser DIFERENTE en contenido y forma. Nada de relleno ni repeticiones.

Responde SOLO con JSON, sin texto antes ni después:
{{"texts": ["...", "...", "..."]}}"""


# JSON schema for structured output on the Responses API. The prompt also asks for this shape
# in prose ({"texts": [...]}); parse_texts() still accepts free text as a fallback.
TEXTS_SCHEMA = {
    "type": "object",
    "properties": {"texts": {"type": "array", "items": {"type": "string"}}},
    "required": ["texts"],
    "additionalProperties": False,
}
