# Le problème : le fossé linguistique dans les services de base

[English](../../PROBLEM.md) · [Español](../es/PROBLEM.md) · [Português](../pt/PROBLEM.md) · **Français** · [Deutsch](../de/PROBLEM.md) · [Italiano](../it/PROBLEM.md) · [हिन्दी](../hi/PROBLEM.md) · [ไทย](../th/PROBLEM.md)

Environ **476 millions** de personnes autochtones vivent dans 90 pays. Beaucoup d'entre elles ont affaire à des
médecins, à des formulaires de consentement, à des tribunaux et à l'état civil dans une langue officielle
qu'elles ne comprennent pas complètement. Là où on le mesure, les chiffres sont élevés : dans quatre pays
d'Amérique latine seulement, environ **3 millions** de personnes ne peuvent pas du tout utiliser la langue
officielle de leur pays. Ailleurs, la plupart du temps, on ne le compte pas.

Les modèles de base ouverts pour la parole et la traduction couvrent désormais plus de 1,600 langues. Ce qui
n'existe pas, c'est la couche qui en fait quelque chose qu'un centre de santé peut utiliser : **des modèles
évalués et gouvernés par les communautés, entre chaque langue autochtone et la langue officielle dont ses
locuteurs ont besoin, à l'écrit et à l'oral**. Uyari construit cette couche du dernier kilomètre pour n'importe
quelle langue. Il ne construit pas un modèle de base de plus.

## 1. Ampleur

| Région (OIT, 2019) | Part | Population autochtone |
|---|---|---|
| Asie et Pacifique | 70.5% | >335M |
| Afrique | 16.3% | >77M |
| Amérique latine et Caraïbes | 11.5% | ~55M (CEPAL 2018 : 58M ; 826 peuples) |
| Amérique du Nord | 1.6% | >7M |
| Europe et Asie centrale | 0.1% | <1M |
| **Monde** | | **476.6M (>6% de l'humanité)** |

* Les personnes autochtones ont près de trois fois plus de risques de vivre dans l'extrême pauvreté (OIT).
* Sur 7,159 langues vivantes, 3,193 (environ 45%) sont menacées (Ethnologue, 28e éd., 2025).
* 40% des personnes dans le monde n'ont pas accès à un enseignement dans une langue qu'elles comprennent, et
  jusqu'à 90% dans certains pays à revenu faible ou intermédiaire (UNESCO GEM Report, 2025).

## 2. Les personnes qui ne peuvent pas utiliser la langue officielle

Il n'existe aucun décompte mondial ; peu de recensements posent la question. La région la mieux mesurée est
l'Amérique latine :

| Pays | Locuteurs de langues autochtones | Ne peuvent pas utiliser la langue officielle | Source |
|---|---|---|---|
| Mexique | 7,364,645 (6.1%, 3 ans et plus) | **865,972** ne parlent pas espagnol | Recensement INEGI 2020 (décompte direct) |
| Guatemala | 4,027,481 locuteurs de langue maternelle | **~1.64M** (20.9% de la population autochtone) | Instituto Cervantes 2024 (estimation) |
| Pérou | 4,477,195 locuteurs de langue maternelle (16.02%, 3 ans et plus) | **~335,576** | Instituto Cervantes 2024 (estimation ; le recensement ne pose pas la question) |
| Bolivie | ~4.2M (2012) | **~267,729** | Instituto Cervantes 2024 (estimation) |

Cela fait environ **3.1 millions** de personnes dans quatre pays, plus plusieurs millions de bilingues qui
peuvent faire leurs courses dans la langue officielle mais ne peuvent pas suivre un diagnostic ou une audience
au tribunal. Le même fossé existe partout où un État fonctionne dans une langue que ses citoyens autochtones ne
parlent pas ; simplement, il n'est pas compté. Soixante-dix pour cent des personnes autochtones du monde vivent
en Asie et dans le Pacifique, où il n'existe aucun chiffre comparable.

Ces populations ne sont pas petites. Les locuteurs de langues autochtones du Mexique, à eux seuls, sont plus
nombreux que les locuteurs du danois, du finnois ou du norvégien, trois langues qui bénéficient toutes d'une
prise en charge complète par l'IA commerciale.

## 3. Pourquoi c'est important : santé, éducation, justice

* **Santé.** Au Guatemala, la barrière de la langue était « l'obstacle le plus important » à l'utilisation des
  services de santé reproductive par les femmes autochtones (analyse Guttmacher de l'enquête nationale
  2008–09), et la mortalité maternelle des femmes autochtones était plus du double de celle des femmes non
  autochtones : 166 contre 78 pour 100,000 naissances vivantes (étude nationale de 2011). Au Guatemala, au
  Mexique, au Pérou et en Bolivie, les femmes qui *parlent* une langue autochtone accouchent moins souvent dans
  un établissement de santé. Là où les hôpitaux n'ont pas d'interprètes, le consentement éclairé échoue.
* **Éducation.** Les enfants qui apprennent dans une langue qu'ils parlent ont beaucoup plus de chances de lire
  en comprenant (UNESCO 2025). Au Mexique, les locuteurs de langues autochtones de 15 ans et plus ont en moyenne
  6.2 années de scolarité ; **les monolingues, 1.4 en moyenne** (INEGI 2020).
* **Justice et administration.** Les lois qui reconnaissent les langues autochtones sont courantes ; les
  interprètes ne le sont pas. Le Congrès du Pérou a manqué à plusieurs reprises d'interprètes pour des langues
  autochtones officielles, et le Mexique donne une validité juridique aux langues autochtones alors que la mise
  en œuvre tarde.

Les monolingues sont, de manière disproportionnée, des personnes âgées, des femmes et des personnes non
alphabétisées. **L'oral n'est pas facultatif** : la traduction de texte seule ne les atteint pas.

## 4. Ce qui existe, et ce qui manque

| Couche | Ce qui existe | Lacune |
|---|---|---|
| Modèles de base | Meta Omnilingual ASR (1,600+ langues, Apache 2.0), Omnilingual MT (1,600+), NLLB-200, MMS ; Google Translate ; Microsoft Translator | Évalués surtout par rapport à l'anglais ; qualité inconnue pour la plupart des langues autochtones ; peu de TTS ou de parole à parole |
| Bancs d'essai | Des tâches partagées régionales, comme AmericasNLP (~13 langues ↔ espagnol, texte uniquement) | La MT langue officielle → langue autochtone y « a atteint un plateau de performance » (chrF++ d'environ 13–37) |
| Projets communautaires | Te Hiku Media (māori), Voces (Chili/Pérou), de nombreux projets pilotes locaux | Une ou quelques langues chacun ; pas réutilisables comme pipeline |

Ce qui manque, et ce pour quoi Uyari est conçu :

1. **Des paires langue native ↔ langue officielle**, et non un pivot par l'anglais qui accumule les erreurs.
2. **La parole** (ASR, TTS, parole à parole) pour des langues dont les locuteurs, souvent, ne lisent pas.
3. **Des données de domaine** pour la santé, le consentement, l'état civil et la justice.
4. **Une évaluation humaine** par des locuteurs natifs et des interprètes certifiés, pas seulement des
   métriques automatiques.
5. **La prise en compte des dialectes** : un même nom de langue recouvre souvent de nombreuses variétés
   (« quechua » en désigne plus de 25 rien qu'au Pérou).
6. **Une gouvernance** : consentement, partage des bénéfices et licences compatibles avec la souveraineté des
   données autochtones.
7. **Un déploiement** qui peut fonctionner hors ligne sur du matériel modeste.

## 5. L'approche

* **Cinq cas d'usage par paire de langues :** texte autochtone → texte en langue officielle, texte en langue
  officielle → texte autochtone, parole autochtone → parole en langue officielle, parole en langue officielle →
  parole autochtone, et parole vers texte pour la langue autochtone.
* **S'appuyer sur les modèles de base ouverts de Meta ; adapter par langue.** Affiner un modèle multilingue
  partagé (Muse Glimmer QLoRA, NLLB-200) sur chaque paire native↔officielle ; un plancher de récupération oblige
  chaque modèle à rester honnête.
* **Parole à parole en cascade** (ASR → MT → TTS), avec le texte visible au milieu pour qu'une personne puisse
  vérifier un diagnostic ou un formulaire de consentement avant qu'il soit prononcé.
* **Le budget, ce sont les données.** Par langue, environ 5–20k phrases de domaine, 4–10 h de parole lue par une
  seule personne pour une voix (une voix shipibo-konibo a atteint un MOS de 4.01 avec ~4 h) et 10–50 h de parole
  transcrite. Le calcul représente une petite part du coût (une estimation d'ingénierie, pas un chiffre publié).
* **N'importe quelle langue, sans modifier le code.** Une langue est un dossier ; les données d'une communauté
  sont un dossier à l'intérieur. Le côté langue officielle est un corpus partagé (l'espagnol d'abord ; les autres
  langues officielles par le même mécanisme).
* **Gouvernance dès la conception** : consentement libre, préalable et éclairé (UNDRIP, convention 169 de l'OIT), principes
  CARE, licences par contribution, retrait sous forme de ligne de données, contributeurs rémunérés, et peuples en
  isolement volontaire explicitement exclus.
* **Les interprètes comme créateurs et évaluateurs de données**, et non comme des personnes remplacées par
  l'outil.
* **Mesurer l'impact, pas seulement le chrF++** : compréhension du consentement, réalisation des visites
  prénatales, délai d'accès au service.

## 6. Le premier cas : shawi ↔ espagnol (Pérou)

Le shawi vient en premier parce que le travail y avait déjà commencé, et non parce que le problème est péruvien.
Le cas shawi–espagnol a commencé par la santé maternelle : les communautés shawi ont affaire à des services de
santé qui n'offrent aucun accompagnement dans leur langue. Les porteurs du cas ont fait réaliser des traductions
humaines, et ces traductions sont les premières données d'Uyari. Rien dans le code n'est propre au shawi.

| Indicateur | Chiffre | Source |
|---|---|---|
| Peuples / langues autochtones au Pérou | 55 peuples ; 48 langues officielles | MinCul (2025–26) |
| Langue maternelle autochtone, 3 ans et plus | 4,477,195 ; quechua 3,799,780 ; aymara 450,010 | Recensement 2017 (via MinCul 2024) |
| Langue maternelle shawi | 17,241 | MinCul BDPI (recensement 2017) |
| Interprètes inscrits | **859** (ReNITLI), couvrant 39 des 48 langues | MinCul (janv. 2025) |

Environ 5,200 locuteurs de langue maternelle par interprète inscrit, et neuf langues sans aucun interprète.
Seuls 23.1% des foyers où la langue maternelle d'un parent est autochtone ont un enfant qui la parle (INEI 2017) ;
la population monolingue vieillit, et le temps qui reste pour enregistrer des aînés qui parlent couramment la
langue se réduit.

## Réserves

* Les chiffres de population sont des estimations de 2010–2019. Les définitions (surtout pour la Chine et l'Inde)
  font varier les totaux mondiaux de plus de 100M.
* Seul le chiffre de 865,972 pour le Mexique est un décompte direct, issu du recensement, des personnes qui ne
  parlent pas la langue officielle. Les chiffres du Pérou, du Guatemala et de la Bolivie sont des estimations de
  l'Instituto Cervantes 2024, tirées d'indicateurs indirects d'analphabétisme, et peuvent être surestimés.
* Les affirmations sur la qualité des modèles de base sont autodéclarées et centrées sur l'anglais. Il existe peu
  d'évaluations indépendantes entre les langues autochtones et les langues officielles de leurs pays.
* Les questions des recensements diffèrent : celui du Pérou demande la langue maternelle, et non la maîtrise de
  la langue officielle, et les bases d'âge diffèrent (3+ contre 5+) ; il faut donc toujours les préciser.
