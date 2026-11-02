"""Build the synthetic fixture data root used by the tests (and by hand to exercise the audio path).

    python tests/fixtures/make_fixture.py tests/fixtures/root

Language ``qaa_Latn`` (ISO 639-3 local-use range): pseudo-language text generated from
syllables, 40 Spanish chunks in 10 paraphrase groups, two contributions (text + audio; a
correction with ``replaces``), synthetic WAV clips that pass the audio checks. Everything is
labelled as a fixture; nothing here is real language data.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import yaml

ROOT_FILES = {
    "contributing/en/consent-collective.md": "# Fixture consent template\n",
    "contributing/takedowns.csv": "contribution,requested_by_role,request_date,effective_date,scope,note\n",
}
SPANISH = [
    "El niño tiene fiebre desde ayer y no quiere comer.", "Mañana vamos a la chacra con mi hermano.",
    "La lluvia no deja salir a los pescadores.", "Mi abuela cuenta historias junto al fuego.",
    "Vendemos plátanos en el pueblo cada semana.", "El camino al río está lleno de lodo.",
    "Mi madre prepara caldo de pescado para todos.", "La canoa espera en la orilla del río.",
    "Los niños aprenden a leer en la escuela.", "Mi padre regresa del monte al anochecer.",
]
SYL = ["ku", "nu", "wa", "ʼi", "pi", "ra", "ke", "sha", "we", "na", "hu", "ta", "aʼ", "ma", "ya", "wi", "chi", "hpa"]


def pseudo(rng: random.Random, n_words: int) -> str:
    words = ["".join(rng.choice(SYL) for _ in range(rng.randint(2, 4))) for _ in range(n_words)]
    return (" ".join(words)).capitalize() + "."


def write_wav(path: Path, seconds: float, freq: float, sr: int = 16000) -> None:
    import numpy as np
    import soundfile as sf

    t = np.arange(int(sr * seconds)) / sr
    env = 0.6 + 0.4 * np.sin(2 * np.pi * 2.0 * t)  # keeps every 20 ms frame above the silence floor
    x = 0.45 * env * np.sin(2 * np.pi * freq * t)  # peak ~ -6.9 dBFS
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), x.astype("float32"), sr, subtype="PCM_16")


def make_root(root: Path, with_audio: bool = True) -> Path:
    import csv

    root = Path(root)
    rng = random.Random(7)
    for rel, text in ROOT_FILES.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
    cols = ["chunk_id", "text", "split", "origin", "status", "supersedes", "domain_l1", "domain_l2", "register",
            "acto_comunicativo", "tiempo_aspecto", "polaridad", "persona_deixis", "length_bucket", "word_count",
            "perfil_hablante", "tono_emocional", "discurso_conectado", "palabras_ancla", "source_custom_id",
            "source_batch_id", "regen_of", "gen_model", "provider", "gen_date", "prompt_version"]
    chunks = []
    splits = ["train"] * 6 + ["validation"] * 2 + ["test"] * 2
    for g in range(10):
        for k in range(4):
            cid = f"{g:02d}{k:02d}".ljust(32, "a")
            text = SPANISH[g] if k == 0 else f"{SPANISH[g][:-1]}, dice {['mamá', 'papá', 'el abuelo'][k - 1]}."
            chunks.append({"chunk_id": cid, "text": text, "split": splits[g], "origin": "synthetic", "status": "active",
                           "domain_l1": ["salud_cuerpo", "comida_cocina"][g % 2] if g < 2 else ["viaje", "familia"][g % 2],
                           "domain_l2": "fixture", "word_count": str(len(text.split())),
                           "register": "casual", "acto_comunicativo": "narracion", "tiempo_aspecto": "presente",
                           "polaridad": "afirmativo", "persona_deixis": "3a", "length_bucket": "muy_corta",
                           "perfil_hablante": "abuela", "tono_emocional": "neutral",
                           "palabras_ancla": "río;canoa;lluvia",
                           "source_custom_id": f"fixture-group-{g:02d}", "source_batch_id": "fixture",
                           "gen_model": "fixture", "provider": "fixture", "discurso_conectado": "false"})
    p = root / "primary/spa_Latn/chunks/generated/fixture.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for c in chunks:
            w.writerow({k: c.get(k, "") for k in cols})

    lang = root / "languages/qaa_Latn"
    lang.mkdir(parents=True, exist_ok=True)
    (lang / "language.yaml").write_text(yaml.safe_dump({
        "id": "qaa_Latn", "iso639_3": "qaa", "script": "Latn", "glottocode": "", "display_name": "Fixture",
        "iso_name": "Fixture (local use)", "primary": "spa_Latn", "steward": "fixture-steward",
        "community_authority": "fixture", "apostrophe": "ʼ",
        "trainer": {"recipes": [], "min_growth": 0.1}}, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def contribution(cid, pairs, audio=None, speakers=None, prov_audio="none"):
        d = lang / "contributions" / cid
        d.mkdir(parents=True, exist_ok=True)
        (d / "contribution.yaml").write_text(yaml.safe_dump({
            "id": cid, "language": "qaa_Latn", "variety": "_unspecified", "contributor_id": "c-0001",
            "organization": "Fixture org", "collection_dates": {"start": "2026-10-01", "end": "2026-10-31"},
            "provenance": {"text": "human", "audio": prov_audio}, "license": "cc-by-4.0",
            "consent": {"template": "consent-collective.md", "authority": "fixture"}, "compensated": "no",
            "fixture": True}, allow_unicode=True, sort_keys=False), encoding="utf-8")
        with (d / "pairs.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["chunk_id", "text", "replaces", "translator_id", "notes"])
            w.writerows(pairs)
        if audio is not None:
            with (d / "audio.csv").open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(["file", "chunk_id", "transcript", "speaker_id", "style", "device", "notes"])
                w.writerows(audio)
            with (d / "speakers.csv").open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(["speaker_id", "age_band", "sex", "first_language", "consent_ref"])
                w.writerows(speakers)
        return d

    pairs = [[c["chunk_id"], pseudo(rng, len(c["text"].split())), "", "t-0001", ""] for c in chunks[:36]]
    audio = [["wav/clip_001.wav", chunks[0]["chunk_id"], "", "s-0001", "read", "fixture-mic", ""],
             ["wav/clip_002.wav", chunks[24]["chunk_id"], "", "s-0001", "read", "fixture-mic", ""],
             ["wav/clip_003.wav", chunks[32]["chunk_id"], "", "s-0002", "read", "fixture-mic", ""],
             ["wav/clip_004.wav", "", pseudo(rng, 5), "s-0002", "spontaneous", "fixture-mic", ""]]
    speakers = [["s-0001", "30-44", "f", "qaa", "fixture-consent-1"], ["s-0002", "45-59", "m", "qaa", "fixture-consent-2"]]
    d1 = contribution("2026-10_fixture_0001", pairs, audio if with_audio else None, speakers if with_audio else None,
                      "field_recording" if with_audio else "none")
    if with_audio:
        for i, freq in enumerate([220, 330, 440, 550], 1):
            write_wav(d1 / f"wav/clip_{i:03d}.wav", 2.0 + i * 0.25, freq)
    contribution("2026-11_fixture_0002", [[chunks[1]["chunk_id"], pseudo(rng, 6),
                                           f"2026-10_fixture_0001/{chunks[1]['chunk_id']}", "t-0002", "correction"]])
    return root


if __name__ == "__main__":
    out = make_root(Path(sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/root"))
    print(f"fixture root: {out}")
