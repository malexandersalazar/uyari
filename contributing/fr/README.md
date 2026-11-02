# Contribuer à Uyari

[English](../en/README.md) · [Español](../es/README.md) · [Português](../pt/README.md) · [Français](../fr/README.md) · [Deutsch](../de/README.md) · [Italiano](../it/README.md) · [हिन्दी](../hi/README.md) · [ไทย](../th/README.md)

Uyari rassemble des traductions et des enregistrements **faits par des personnes** afin que les langues
autochtones et d'autres langues mal desservies disposent d'outils de traduction ouverts, à l'écrit et à l'oral,
vers et depuis la langue officielle dont leurs locuteurs ont besoin pour les soins de santé, l'école et
l'administration. Toute langue peut rejoindre le projet. Chaque contribution est un dossier ; il n'est pas
nécessaire de programmer.

Avant de contribuer, lisez les règles sur les droits, le consentement et le retrait : [governance.md](governance.md).

## Ce dont nous avons besoin maintenant

Chaque langue a un fichier `NEEDS.md` que le système tient à jour. Le shawi (Pérou) est la première langue ; sa
liste est [`languages/cbt_Latn/NEEDS.md`](../../languages/cbt_Latn/NEEDS.md). Aujourd'hui, elle demande :

1. **Des enregistrements lus** de traductions existantes, par au moins 3 personnes adultes, avec leur
   consentement.
2. **Davantage de phrases sur la santé et l'état civil** traduites en shawi, vérifiées par un second lecteur
   natif.

**Pour ajouter une nouvelle langue**, ouvrez une issue avec son nom, son code ISO 639-3, la langue officielle dont
ses locuteurs ont besoin, et la personne qui pourrait en être responsable (steward : une personne qui la parle et
qui relit les contributions).

## Une contribution = un dossier = une pull request

```
languages/<language>/contributions/<YYYY-MM>_<organization>_<nnnn>/
  contribution.yaml   who (pseudonym), when, how it was made, license, consent
  pairs.csv           chunk_id, text, replaces, translator_id, notes      (text)
  audio.csv           file, chunk_id, transcript, speaker_id, style, device, notes   (audio)
  speakers.csv        speaker_id, age_band, sex, first_language, consent_ref        (audio)
  wav/                16 or 48 kHz, mono, 16-bit, 1 to 20 seconds, one person per clip
```

* Un dossier contient **une** langue, **une** variété, **une** licence et **une** référence de consentement.
* Traduisez à partir des phrases en langue officielle de `primary/` (aujourd'hui : l'espagnol,
  `primary/spa_Latn/chunks/`). Chaque ligne de `pairs.csv` renvoie à un `chunk_id`. Traduisez la phrase entière.
* Écrivez les lettres de la langue comme l'indique son `language.yaml`. En shawi, par exemple, le coup de glotte
  est **ʼ** (U+02BC) ; `uyari validate` indique où `'`, `’` ou `´` doivent être convertis.
* **Pas de traduction automatique ni de voix synthétiques présentées comme un travail humain.** Si une personne
  a corrigé une sortie automatique, déclarez-le dans `contribution.yaml` (`human_post_edited_from_mt`).
* Personnes adultes uniquement. Pas de vrais noms dans les fichiers : utilisez `t-0001`, `s-0001`. L'organisation
  contributrice conserve sa propre liste.
* Une contribution acceptée n'est jamais modifiée : une correction est une nouvelle ligne dans une contribution
  ultérieure avec `replaces=<contribution>/<chunk_id>`.

## Ce qui arrive à votre pull request

1. **Validateur** (automatique) : format, codes, identifiants, apostrophes, audio.
2. **Gatekeeper** (automatique, Muse Glimmer sur le GPU du projet) : vérifie si des lignes ressemblent à la
   langue officielle plutôt qu'à la langue autochtone, ou si elles ont été copiées, et écrit une revue ligne par
   ligne sur la pull request.
3. **La personne responsable de la langue (steward)** lit la revue, contrôle des lignes par sondage et décide.
   Les contenus de santé et de consentement éclairé exigent toujours un second lecteur natif.

Après la fusion, le **Trainer** reconstruit les données, entraîne, mesure et ouvre une pull request avec les
résultats.

## Retirer des données

La personne responsable de la langue ou l'autorité communautaire peut demander qu'une contribution soit retirée de
tout entraînement futur : c'est une ligne dans [`contributing/takedowns.csv`](../takedowns.csv). Les modèles déjà
publiés ne peuvent pas être récupérés auprès des personnes qui les ont téléchargés ; leurs fiches sont corrigées
et l'entraînement suivant n'utilise plus ces données. Détails : [governance.md](governance.md#retrait).

## Contribuer au code

```bash
uv sync --python 3.11 --extra dev --extra speech
uv run pytest -q
uv run ruff check src tests
git config core.hooksPath .githooks     # privacy check before every commit
```

Le travail sur GPU se fait sous Ubuntu : [`docs/RUNBOOK-4090.md`](../../docs/RUNBOOK-4090.md). Chaque commande qui
appelle une API payante dispose de `--estimate` et utilise votre propre clé (`META_API_KEY`), et les données en
langues autochtones ne sont jamais envoyées à un modèle hébergé (`data_policy` dans `config/llm.yaml`).
