# What Shawi needs next

_cbt_Latn: 3,575 pairs, 0 clips. Written by the Trainer from build `data-2026.11-six` on 2026-11-03._

1. **Recordings.** 3,575 pairs, 0 clips. Needs *read* recordings of existing translations from at least 3 adult speakers (with consent) before speech recognition can be measured; a Shawi voice needs about one hour of read clips from one speaker.
2. **Our own voice.** `facebook/mms-tts-cbt` (Bible recordings, cc-by-nc-4.0) reads our text through a spelling converter (`languages/cbt_Latn/tts.yaml`): 86% of the letters as written, 99.99% after. A voice of our own, in our spelling, comes from the read recordings above.
3. **Health and civic pairs.** 129 translated in health/civic domains; translate 300–500 more (the primary has 13,697 health/civic chunks, more can be generated). Health rows need a second native reader.
4. **Domain balance.** Fewest pairs: puente_civico (129), viaje_desplazamiento (1088).
5. **Community authority.** Agree with Shawi community organizations who is consulted on consent and may request a withdrawal, then name it in `language.yaml`.

Models: promoted: `mt-cbt-glimmer30b-qlora@v0.4` (validation chrF++ 43.46); fast: `mt-cbt-nllb1.3b@v0.3` (validation chrF++ 44.59).

## En español

Shawi tiene 3,575 pares traducidos y 0 grabaciones. Lo que más falta: grabaciones leídas de las traducciones existentes (al menos 3 personas adultas, con consentimiento) y más oraciones de salud y trámites. Ver `contributing/es/README.md`.
