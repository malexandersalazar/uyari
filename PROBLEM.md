# The problem: the language gap in basic services

**English** · [Español](docs/es/PROBLEM.md) · [Português](docs/pt/PROBLEM.md) · [Français](docs/fr/PROBLEM.md) · [Deutsch](docs/de/PROBLEM.md) · [Italiano](docs/it/PROBLEM.md) · [हिन्दी](docs/hi/PROBLEM.md) · [ไทย](docs/th/PROBLEM.md)

About **476 million** Indigenous people live in 90 countries. Many of them meet doctors, consent forms,
courts and civil registries in an official language they do not fully understand. Where this is measured,
the numbers are large: in just four Latin American countries, about **3 million** people cannot use their
country's official language at all. Elsewhere it is mostly not counted.

Open base models for speech and translation now cover more than 1,600 languages. What does not exist is the
layer that turns them into something a clinic can use: **evaluated, community-governed models between each
Indigenous language and the official language its speakers need, in text and in speech**. Uyari builds that
last-mile layer for any language. It does not build another base model.

## 1. Scale

| Region (ILO, 2019) | Share | Indigenous population |
|---|---|---|
| Asia & Pacific | 70.5% | >335M |
| Africa | 16.3% | >77M |
| Latin America & Caribbean | 11.5% | ~55M (CEPAL 2018: 58M; 826 peoples) |
| Northern America | 1.6% | >7M |
| Europe & Central Asia | 0.1% | <1M |
| **World** | | **476.6M (>6% of humanity)** |

* Indigenous people are nearly three times more likely to live in extreme poverty (ILO).
* Of 7,159 living languages, 3,193 (about 45%) are endangered (Ethnologue, 28th ed., 2025).
* 40% of people worldwide lack education in a language they understand, up to 90% in some low- and
  middle-income countries (UNESCO GEM Report, 2025).

## 2. People who cannot use the official language

No global count exists; few censuses ask the question. The best-measured region is Latin America:

| Country | Indigenous-language speakers | Cannot use the official language | Source |
|---|---|---|---|
| Mexico | 7,364,645 (6.1%, aged 3+) | **865,972** do not speak Spanish | INEGI Census 2020 (direct count) |
| Guatemala | 4,027,481 mother-tongue speakers | **~1.64M** (20.9% of the Indigenous population) | Instituto Cervantes 2024 (estimate) |
| Peru | 4,477,195 mother-tongue speakers (16.02%, aged 3+) | **~335,576** | Instituto Cervantes 2024 (estimate; the census does not ask) |
| Bolivia | ~4.2M (2012) | **~267,729** | Instituto Cervantes 2024 (estimate) |

That is roughly **3.1 million** people in four countries, plus several million bilinguals who can shop in
the official language but cannot follow a diagnosis or a court hearing. The same gap exists wherever a state
works in a language its Indigenous citizens do not speak; it is simply not counted. Seventy percent of the
world's Indigenous people live in Asia and the Pacific, where no comparable figure exists.

These populations are not small. Mexico's Indigenous-language speakers alone outnumber the speakers of
Danish, Finnish or Norwegian, all of which have full commercial AI support.

## 3. Why it matters: health, education, justice

* **Health.** In Guatemala the language barrier was "the most important obstacle" to Indigenous women's use of
  reproductive health services (Guttmacher analysis of the 2008–09 national survey), and Indigenous women's
  maternal mortality was more than twice that of non-Indigenous women: 166 vs 78 per 100,000 live births
  (2011 national study). Across Guatemala, Mexico, Peru and Bolivia, women who *speak* an Indigenous language
  are less likely to give birth in a facility. Where hospitals have no interpreters, informed consent fails.
* **Education.** Children taught in a language they speak are far more likely to read with understanding
  (UNESCO 2025). In Mexico, Indigenous-language speakers aged 15+ average 6.2 years of schooling;
  **monolinguals average 1.4** (INEGI 2020).
* **Justice and government.** Laws that recognize Indigenous languages are common; interpreters are not.
  Peru's Congress has repeatedly lacked interpreters for official Indigenous languages, and Mexico gives
  Indigenous languages legal validity while implementation lags.

Monolinguals are disproportionately older, female and non-literate. **Speech is not optional**: text
translation alone does not reach them.

## 4. What exists, and what is missing

| Layer | What exists | Gap |
|---|---|---|
| Base models | Meta Omnilingual ASR (1,600+ languages, Apache 2.0), Omnilingual MT (1,600+), NLLB-200, MMS; Google Translate; Microsoft Translator | Evaluated mostly against English; quality unknown for most Indigenous languages; little TTS or speech-to-speech |
| Benchmarks | Regional shared tasks, such as AmericasNLP (~13 languages ↔ Spanish, text only) | Official-language → Indigenous MT has "reached a performance plateau" there (chrF++ about 13–37) |
| Community projects | Te Hiku Media (Māori), Voces (Chile/Peru), many local pilots | One or a few languages each; not reusable as a pipeline |

Missing, and what Uyari is built for:

1. **Native ↔ official-language pairs**, not a pivot through English that compounds errors.
2. **Speech** (ASR, TTS, speech-to-speech) for languages whose speakers often do not read.
3. **Domain data** for health, consent, civil registry and justice.
4. **Human evaluation** by native speakers and certified interpreters, not only automatic metrics.
5. **Dialect awareness**: one language name often covers many varieties ("Quechua" is 25+ in Peru alone).
6. **Governance**: consent, benefit sharing and licenses compatible with Indigenous data sovereignty.
7. **Deployment** that can run offline on modest hardware.

## 5. The approach

* **Five use cases per language pair:** Indigenous text → official text, official text → Indigenous text,
  Indigenous speech → official speech, official speech → Indigenous speech, and speech-to-text for the
  Indigenous language.
* **Build on Meta's open base models; adapt per language.** Fine-tune a shared multilingual model (Muse
  Glimmer QLoRA, NLLB-200) on each native↔official pair; a retrieval floor keeps every model honest.
* **Speech-to-speech as a cascade** (ASR → MT → TTS), with the text visible in the middle so a person can check
  a diagnosis or a consent form before it is spoken.
* **Data is the budget.** Per language, roughly 5–20k domain sentences, 4–10 h of single-speaker read speech
  for a voice (a Shipibo-Konibo voice reached MOS 4.01 from ~4 h) and 10–50 h of transcribed speech. Compute is
  a small fraction of the cost (an engineering estimate, not a published figure).
* **Any language, no code changes.** A language is a folder; a community's data is a folder inside it. The
  official-language side is a shared corpus (Spanish first; other official languages by the same mechanism).
* **Governance by design**: free, prior and informed consent (UNDRIP, ILO C169), the CARE principles,
  per-contribution licenses, withdrawal as a data row, paid contributors, and peoples in voluntary isolation
  explicitly excluded.
* **Interpreters as data creators and evaluators**, not people displaced by the tool.
* **Measure impact, not only chrF++**: consent comprehension, prenatal visit completion, time to service.

## 6. The first case: Shawi ↔ Spanish (Peru)

Shawi is first because the work had already started there, not because the problem is Peruvian. The
Shawi–Spanish case began with maternal health: Shawi communities meet health services that offer no support
in their language. Its leads had human translations made, and those translations are Uyari's first data.
Nothing in the code is specific to Shawi.

| Indicator | Figure | Source |
|---|---|---|
| Indigenous peoples / languages in Peru | 55 peoples; 48 official languages | MinCul (2025–26) |
| Indigenous mother tongue, aged 3+ | 4,477,195; Quechua 3,799,780; Aymara 450,010 | 2017 census (via MinCul 2024) |
| Shawi mother tongue | 17,241 | MinCul BDPI (2017 census) |
| Registered interpreters | **859** (ReNITLI), covering 39 of 48 languages | MinCul (Jan 2025) |

About 5,200 mother-tongue speakers per registered interpreter, and nine languages with none. Only 23.1% of
households where a parent's mother tongue is Indigenous have a child who speaks it (INEI 2017); the
monolingual population is ageing, so the window to record fluent elders is closing.

## Caveats

* Population figures are 2010–2019 estimates. Definitions (especially for China and India) move global totals
  by more than 100M.
* Only Mexico's 865,972 is a direct census count of people who do not speak the official language. The Peru,
  Guatemala and Bolivia figures are Instituto Cervantes 2024 estimates from illiteracy proxies and may
  overstate.
* Base-model quality claims are self-reported and English-centric. Few independent evaluations exist between
  Indigenous languages and the official languages of their countries.
* Census questions differ: Peru's asks for mother tongue, not official-language proficiency, and age bases
  differ (3+ vs 5+), so always state them.
