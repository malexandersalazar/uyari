# Méthodologie d'Uyari

[English](../../METHODOLOGY.md) · [Español](../es/METHODOLOGY.md) · [Português](../pt/METHODOLOGY.md) · **Français** · [Deutsch](../de/METHODOLOGY.md) · [Italiano](../it/METHODOLOGY.md) · [हिन्दी](../hi/METHODOLOGY.md) · [ไทย](../th/METHODOLOGY.md)

Uyari est une structure de données et une boîte à outils d'entraînement ouvertes qui transforment les traductions
et les enregistrements d'une communauté en modèles entre une langue autochtone ou une autre langue mal desservie
et la langue officielle dont ses locuteurs ont besoin. Une langue s'ajoute sous forme de dossier ; les données
s'ajoutent sous forme de dossier à l'intérieur ; personne ne modifie le code. Les modèles de Meta constituent la
pile par défaut.

Les raisons des choix structurels se trouvent dans [`docs/decisions/`](../../docs/decisions/). Le problème
auquel cela répond, avec chiffres et sources, est décrit dans [`PROBLEM.md`](PROBLEM.md).

## 1. Objectif et périmètre

**Cinq cas d'usage par paire de langues :**

| # | Cas d'usage | Modèles |
|---|---|---|
| 1 | Texte autochtone → texte en langue officielle | MT |
| 2 | Texte en langue officielle → texte autochtone | MT |
| 3 | Parole autochtone → parole en langue officielle | ASR → MT → TTS |
| 4 | Parole en langue officielle → parole autochtone | ASR → MT → TTS |
| 5 | Parole autochtone → texte autochtone (parole vers texte) | ASR |

**La première paire est shawi ↔ espagnol** (`cbt_Latn`, glottocode `chay1248` ; Pérou). Elle est la première
parce que le travail y avait commencé, avec la santé maternelle
([`PROBLEM.md` §6](PROBLEM.md#6-le-premier-cas--shawi--espagnol-pérou)), et non parce que quoi que ce soit lui
serait propre. Ce qui existe pour elle :

* 11,977 segments primaires en espagnol (synthétiques, issus de la matrice de conception de
  `primary/spa_Latn/matrix.yaml`).
* 3,578 traductions humaines en shawi de 3,575 d'entre eux, un travail commandé, sous forme de trois
  contributions.
* Les mêmes 11,977 segments en anglais, traduits automatiquement depuis l'espagnol avec les mêmes identifiants
  de segment, de sorte que chaque traduction en shawi forme aussi une paire avec l'anglais.
* Aucun enregistrement en shawi. Le parcours audio (validateur, build, pipelines ASR/TTS) est testé sur un jeu
  d'essai synthétique étiqueté (`qaa_Latn`), et `NEEDS.md` demande des enregistrements.

| Dans le périmètre | Hors périmètre |
|---|---|
| Toute langue qui a une forme écrite ; le format accepte toutes les écritures ISO 15924 (seule l'écriture latine est testée pour l'instant) | Les langues uniquement orales (le format stocke l'audio non transcrit ; aucun pipeline ne l'utilise encore) |
| Les langues officielles comme corpus primaires : l'espagnol (généré) et l'anglais (traduit automatiquement depuis l'espagnol) ; les autres (portugais, français, hindi, thaï, …) par le même mécanisme | La recherche dialectale : les variétés sont une étiquette sur une contribution |
| Traductions et enregistrements humains ; texte écrit par une machine uniquement du côté de la langue officielle, et étiqueté | La traduction automatique présentée comme un travail humain |
| Une langue rejoint le projet quand une communauté apporte des données et une personne responsable | Un service d'inférence en production ; la démo est une démo |

## 2. Principes

1. **La contribution est l'unité.** Les données sont classées en dossiers de contribution, chacun avec sa propre
   provenance, sa licence et son consentement. Le regroupement ne se fait que dans les builds et les recettes,
   jamais en déplaçant des fichiers.
2. **Des identifiants stables, jamais des positions.** Les identifiants de segment font 32 caractères
   hexadécimaux et ne sont jamais réutilisés (les traducteurs travaillent à partir de ces mêmes identifiants). Les
   fichiers peuvent être découpés ou triés sans casser une référence.
3. **Les contributions fusionnées sont immuables.** Une correction est une nouvelle contribution qui indique ce
   qu'elle remplace.
4. **Les humains traduisent et parlent ; les machines peuvent seulement rédiger un brouillon du côté de la langue
   officielle, et le signalent.** Chaque segment synthétique nomme le modèle qui l'a écrit (`gen_model`,
   `provider`, `prompt_version`).
5. **Le consentement et le retrait sont des données.** Chaque contribution porte une licence et une référence de
   consentement ; un retrait est une ligne CSV que le build suivant applique.
6. **Codes standard, noms simples, builds reproductibles.** Les langues sont identifiées par leur code ISO 639-3
   plus l'écriture (`cbt_Latn`), l'étiquette des modèles de Meta. Le même tag de build produit le même hash de
   contenu sur n'importe quel OS.
7. **Les données communautaires ne quittent jamais notre matériel pour un modèle qui pourrait s'entraîner
   dessus.** Chaque modèle déclare une `data_policy` ; le code refuse d'envoyer du texte en langue autochtone à un
   modèle hébergé de niveau Contributor.
8. **Les API payantes sont facultatives et payées par qui les utilise.** La CLI utilise votre propre clé ; la
   démo demande la sienne à chaque visiteur et, sinon, n'exécute que les modèles ouverts affinés.

**Une conséquence.** La partition est une propriété du segment primaire, partagée par toutes les langues, et
elle est attribuée par **groupe de paraphrases** (les ~10 quasi-paraphrases produites par une même requête de
génération), de sorte qu'aucun modèle ne peut voir à l'entraînement une paraphrase d'une phrase de test.

## 3. Modèle de données

| Entité | Clé | Doit avoir |
|---|---|---|
| Segment primaire | `chunk_id` (32-hex) | texte, partition, origine, statut ; chaque colonne de la matrice de conception enregistrée par le générateur |
| Langue | `<iso639-3>_<Script>` | glottocode, nom d'affichage, personne responsable, autorité communautaire, apostrophe canonique |
| Contribution | `<YYYY-MM>_<org>_<nnnn>` | contributeur (pseudonyme), licence, consentement, provenance, dates de collecte, variété |
| Ligne de paire | (contribution, chunk_id) | texte, translator_id (pseudonyme) ; `replaces` facultatif |
| Ligne audio | (contribution, file) | locuteur, style ; chunk_id ou transcription |
| Locuteur | (contribution, speaker_id) | tranche d'âge, référence de consentement |
| Build | `data-YYYY.MM[-rN]` | une table par tâche et par langue, un manifeste avec les hash des fichiers et du contenu |
| Recette | fichier | build, langue, modèle de base, méthode, hyperparamètres |
| Fiche de modèle | `name@vX.Y` | build, recette, licence du modèle de base, scores de validation par rapport au plancher de récupération, test une seule fois |

Lignes audio : `chunk_id` renseigné et `transcript` vide signifie que le locuteur a lu la traduction du segment
faite dans cette contribution ; `chunk_id` vide et `transcript` renseigné, c'est de la parole spontanée
(partitionnée par locuteur) ; si les deux sont vides, la ligne est stockée mais pas utilisée. Les vocabulaires
fermés se trouvent dans `schemas/` ; le validateur rejette toute autre valeur.

## 4. Corpus primaire

Le corpus primaire est l'ensemble des phrases en langue officielle que chaque langue traduit. Aujourd'hui, c'est
l'espagnol (`primary/spa_Latn/`).

**Ce que nous avons.** Le premier lot, `2026-06_opus48_0001.csv` : 10,000 segments générés en juin 2026 avec
Claude Opus 4.8, couvrant 4 des 15 domaines de la matrice et 37 micro-scénarios. Chaque ligne conserve sa cellule
de la matrice (domaine, micro-scénario, registre, acte communicatif, temps, polarité, personne, tranche de
longueur, profil du locuteur, ton, discours suivi, mots d'ancrage, `source_custom_id`).

**En générer davantage, avec les modèles de Meta.** `uyari generate` conserve la matrice de ce lot, sa rotation
(round-robin) sur temps/polarité/personne, les mots d'ancrage, le plan sur disque avec un statut par unité et des
relances idempotentes, la clé de groupe `custom_id`, l'analyse, la validation et la déduplication, et **le prompt
identique** (une seule `prompt_version` figée), de sorte qu'une comparaison mesure les modèles, et non des
modifications du prompt. Régénérer 200 cellules avec Muse Spark 1.3 Contributor a coûté, par 1,000 segments,
3.3% du coût du lot d'origine, avec 100% de réponses bien formées et un texte légèrement plus varié
(`reports/gen-comparison.md`) ; Muse Glimmer sur notre propre GPU le fait sans coût d'API. Avant l'envoi,
`--estimate` affiche le coût ; chaque exécution est plafonnée ; chaque appel est inscrit dans le registre.

**Post-traitement.** NFC et espaces ; 1–120 mots et la tranche de longueur de l'unité ±30% ; termes urbains
interdits ; une vérification de la langue ; déduplication exacte et quasi-doublons par embeddings (cosinus 0.92,
par blocs de domaine) sur l'ensemble du corpus primaire ; une relecture humaine par sondage de 2% par lot
(`uyari primary sample`), et un lot qui dépasse 5% de rejets est retiré.

**Partitions.** Première attribution : la validation et le test contiennent chacun ~300 segments traduits, sous
forme de groupes de paraphrases entiers pris parmi les groupes traduits, stratifiés par domaine, ordonnés par
hash. Nouveaux groupes : un groupe qui régénère une cellule existante hérite de sa partition ; les autres sont
répartis par hash (5% / 5%). Figées une fois écrites.

**D'autres corpus primaires.** L'anglais (`primary/eng_Latn`) partage les identifiants de segment avec le
corpus espagnol : `uyari primary translate` a traduit automatiquement les 11,977 segments avec Muse Spark 1.3
Contributor pour US$ 0.19 ; ils sont étiquetés `origin=machine_translated`, et leur partition, leur domaine et
leur groupe de paraphrases sont copiés. Les autres langues officielles s'ajoutent de la même façon.

## 5. Ajouter une langue

Un dossier `languages/<iso639-3>_<Script>/` avec `language.yaml` et `README.md`. Le validateur l'accepte quand
chaque code se résout dans `registry/` (la plage à usage local `qaa`–`qtz` d'ISO 639-3 est acceptée) et qu'une
personne responsable est nommée. Champs :
`id, iso639_3, script, glottocode, display_name, iso_name, primary, steward, community_authority, apostrophe,
apostrophe_variants, training_orthography, trainer`. Les lettres que les outils abîment souvent sont déclarées
une seule fois : en shawi, le coup de glotte est une lettre, `ʼ` (U+02BC) en forme canonique, et le validateur
liste les caractères variantes avec la correction.

## 6. Contribuer

Voir [`contributing/`](../../contributing/) (anglais, espagnol, portugais, français, allemand, italien, hindi,
thaï). Un dossier, une pull request, une langue, une variété, une licence, une référence de consentement :
`contribution.yaml`, `pairs.csv`, `audio.csv`, `speakers.csv`, `wav/`. Les contributions partielles sont
normales ; le build déduit ce que contient un dossier à partir des fichiers présents.

## 7. Revue

Trois filtres : le **validateur** (CI, chaque PR), le **Gatekeeper** (Muse Glimmer sur notre propre GPU ; une
revue écrite dans la langue de travail de la personne responsable, l'espagnol pour le shawi), et la **personne
responsable de la langue** (steward, une personne qui parle la langue). Le Gatekeeper repère les échecs du
validateur, le texte en langue officielle collé dans la colonne de la langue autochtone, les lignes copiées de
contributions acceptées et le texte qui ne ressemble pas aux paires acceptées ; il recommande de fusionner, de
renvoyer ou de faire remonter (les domaines de la santé et du consentement remontent toujours). Il ne détecte
**pas** la traduction automatique ; les contributeurs attestent qu'aucune sortie automatique n'est soumise comme
travail humain.

## 8. Builds

`uyari build --tag data-YYYY.MM` lit chaque contribution, applique `replaces`, ignore les contributions révoquées
et les retraits effectifs à la date `--as-of` ou avant, normalise le texte, joint la partition et le domaine, et
écrit `builds/<tag>/<lang>/{mt,asr,tts}.parquet` (entraînement + validation) et `*.test.parquet` (test), ainsi
que `MANIFEST.json` : commit git, contributions incluses et exclues avec leurs motifs, lignes exclues avec leurs
motifs, lignes par partition, licences et, pour chaque table, un `sha256` de fichier et un `content_sha256`
canonique. Les données manquantes sont déduites, jamais déclarées. Le Parquet n'est pas dans git ; le tag permet
de le reconstruire.

## 9. Agents

| Agent | Déclencheur | Décide | Écrit |
|---|---|---|---|
| **Gatekeeper** | Une PR vers `contributions/` | fusionner / renvoyer / faire remonter (recommandation seulement) | Une revue sur la PR, un brouillon de `review.yaml` |
| **Trainer** | Une fusion dans `main` (runner GPU auto-hébergé), ou à la main | S'il vaut la peine de produire un build (nouvelle langue ou ≥10% de paires en plus) ; ne promeut que si chaque direction bat le plancher de récupération **et** si, sur les directions communes aux deux modèles, le chrF++ de validation progresse de ≥0.5 par rapport au modèle en place, réévalué sur le même build (ou si le candidat ajoute des directions et ne perd pas plus de 0.5) | Manifeste du build, fiche de modèle, `scores.json`, `models/registry.yaml`, `NEEDS.md`, une pull request |
| Interpreter | (après le MVP) | | |

Garde-fous : aucun agent ne fusionne ; aucun agent ne lit la partition de test avant une promotion ; le test est
évalué une seule fois par version de modèle ; chaque décision est une ligne sur la PR ou sur la fiche, avec les
chiffres qui l'ont produite.

## 10. Entraînement et évaluation

Les recettes de `recipes/` sont la seule configuration. Un modèle par backend couvre chaque langue officielle
associée à la langue autochtone (aujourd'hui l'espagnol et l'anglais : quatre directions), et chaque direction
est évaluée sur sa propre paire de langues. Modèles de référence pour le texte :

* **Muse Glimmer 30B, QLoRA** (Unsloth, 4 bits, r=16, longueur max. 512, batch 1 × 16, 3 époques) : le modèle
  phare, sur notre RTX 4090.
* **NLLB-200 1.3B, affinage complet** (un nouveau jeton de langue initialisé à partir d'une langue apparentée ;
  `quy_Latn` pour le shawi) : la référence rapide ; s'entraîne aussi sur une RTX 3060 de 12 Go en bf16 pur.
* **Plancher de récupération :** la traduction humaine de la phrase d'entraînement la plus proche ; local,
  gratuit.

La démo ne sert que ces modèles affinés : Glimmer par défaut une fois entraîné, NLLB en mode rapide ; les fiches
indiquent lequel obtient le meilleur score.

| Tâche | Score | Vérification humaine |
|---|---|---|
| Texte vers texte | chrF++ par direction (BLEU rapporté, non optimisé) | Deux locuteurs natifs notent 100 phrases quand c'est possible |
| Parole vers texte | CER (WER rapporté) | Acceptabilité de la transcription sur 50 extraits |
| Texte vers parole | CER aller-retour via l'ASR | Naturel 1–5 |
| Parole vers parole | chrF++ de la sortie après ASR | Réussite de la tâche sur un dialogue scénarisé |

On ne se fie pas à COMET ni aux autres métriques apprises pour la traduction vers les langues autochtones tant
qu'elles n'ont pas été validées par rapport à des jugements humains.

## 11. Gouvernance

Code : Apache 2.0. Données : par contribution (CC BY 4.0 par défaut ; CC BY-SA, CC BY-NC ou une licence
communautaire, au choix de la communauté), reportée sur chaque ligne de build. Le consentement est collectif
(autorité communautaire) et individuel (chaque locuteur et chaque traducteur) ; les retraits sont des lignes dans
`contributing/takedowns.csv`. Rôles, licences, modèles de formulaires de consentement et protections, en huit
langues : [`contributing/<language>/governance.md`](../../contributing/fr/governance.md).

## 12. Coûts

* **Local par défaut.** L'entraînement, l'évaluation, le Gatekeeper et la démo tournent sur nos propres GPU, sans
  coût d'API.
* **Apportez votre propre clé.** Tout ce qui appelle une API payante utilise la propre clé Meta de l'appelant :
  la CLI lit `META_API_KEY` ; la démo demande leur clé aux visiteurs, l'utilise pour cette seule requête et ne la
  stocke jamais, et ne se rabat jamais sur la clé du serveur.
* **Estimer avant de dépenser.** Les prix se trouvent dans `config/llm.yaml` ; chaque commande LLM estime son
  coût avant l'envoi (approximation tiktoken × 1.2), l'usage réel de chaque appel est dans `.uyari/ledger.jsonl`,
  et chaque exécution a un plafond strict (`generate` $1, `transcribe` $2, tout le reste $0 parce que cela tourne
  en local). Le budget de développement propre au projet pour les API hébergées est de USD 150.
