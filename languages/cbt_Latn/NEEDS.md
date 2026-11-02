# What Shawi needs next

_cbt_Latn: 3,575 pairs, 0 clips. Written by the Trainer from build `data-2026.11` on 2026-11-02._

1. **Recordings.** 3,575 pairs, 0 clips. Needs *read* recordings of existing translations from at least 3 adult speakers (with consent) before speech recognition can be measured; a Shawi voice needs about one hour of read clips from one speaker.
2. **A voice in our orthography.** `facebook/mms-tts-cbt` exists (Bible recordings, cc-by-nc-4.0) but covers 86% of the letters in our text (no k, ʼ, w, ñ): it needs an orthography converter written with the steward, or a voice trained on our own recordings.
3. **Health and civic pairs.** 129 translated in health/civic domains; translate 300–500 more (the primary has 426 health/civic chunks, more can be generated). Health rows need a second native reader.
4. **Domain balance.** Fewest pairs: puente_civico (129), viaje_desplazamiento (1088).
5. **Community authority.** Agree with Shawi community organizations who is consulted on consent and may request a withdrawal, then name it in `language.yaml`.

Models: fast: `mt-cbt-spa-nllb1.3b@v0.1` (validation chrF++ 37.84).

## En español

Shawi tiene 3,575 pares traducidos y 0 grabaciones. Lo que más falta: grabaciones leídas de las traducciones existentes (al menos 3 personas adultas, con consentimiento) y más oraciones de salud y trámites. Ver `contributing/es/README.md`.
