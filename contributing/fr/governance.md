# Gouvernance : droits, consentement et retrait

[English](../en/governance.md) · [Español](../es/governance.md) · [Português](../pt/governance.md) · [Français](../fr/governance.md) · [Deutsch](../de/governance.md) · [Italiano](../it/governance.md) · [हिन्दी](../hi/governance.md) · [ไทย](../th/governance.md)

Uyari conserve les mots et les voix de personnes. Ces règles s'appliquent à toutes les langues et à toutes les
contributions. Elles respectent le consentement libre, préalable et éclairé (Déclaration des Nations Unies sur les
droits des peuples autochtones ; Convention 169 de l'OIT), les principes CARE pour la gouvernance des données
autochtones, et le droit national de chaque pays où les données sont collectées.

## Qui décide

| Rôle | Décide |
|---|---|
| **Mainteneur** (la personne qui dirige le projet) | La structure, les schémas, le validateur, les builds, la méthodologie |
| **Personne responsable de la langue** (steward ; une par langue, une personne qui la parle) | Tout ce qui concerne cette langue : accepte les contributions, désigne les relecteurs, enregistre les retraits |
| **Autorité communautaire** (nommée dans `language.yaml`) | Le consentement au nom de la communauté ; peut demander un retrait à tout moment |
| **Contributeur** (une personne ou une organisation) | Produit les contributions et choisit, avec la communauté, leur licence |

Aucun agent ne décide : le Gatekeeper et le Trainer ne font que recommander, et c'est une personne qui fusionne.

## Licences

Chaque contribution indique sa licence dans `contribution.yaml`, et chaque build la reporte sur chaque ligne, de
sorte que quiconque utilise les données peut filtrer par licence.

* Par défaut : **CC BY 4.0**. Une communauté peut choisir CC BY-SA 4.0, CC BY-NC 4.0, CC0 ou sa propre licence
  communautaire.
* La personne responsable explique le compromis avant que la communauté ne choisisse : une licence non
  commerciale empêche une entreprise de déployer le traducteur pour un ministère ou un centre de santé, ce qui est
  souvent le principal moyen pour qu'il atteigne les gens.
* Le code est sous Apache 2.0. Les poids des modèles héritent aussi de la licence de leur modèle de base.

## Consentement

Le consentement est **collectif** (l'autorité communautaire accepte la finalité et la licence) et **individuel**
(chaque traducteur et chaque locuteur adulte donne son accord pour lui-même). Les modèles se trouvent dans ce
dossier, avec les mêmes noms de fichiers dans toutes les langues :

| Modèle | Qui donne son accord | Indiqué dans |
|---|---|---|
| [`consent-collective.md`](consent-collective.md) | L'autorité communautaire | `contribution.yaml` → `consent.template` |
| [`consent-individual.md`](consent-individual.md) | Chaque traducteur et chaque locuteur | `speakers.csv` → `consent_ref` |
| [`commissioned-work.md`](commissioned-work.md) | Quiconque a commandé et payé le travail, en tant que titulaire des droits | `contribution.yaml` → `consent.template` |

`contribution.yaml` désigne le modèle uniquement par son nom de fichier (par exemple `consent-collective.md`), de
sorte que la même référence vaut dans toutes les langues. Les exemplaires signés restent auprès de l'organisation
contributrice ; le dépôt ne contient que le nom du modèle et l'autorité, jamais une signature ni un vrai nom.

## Travail commandé

Lorsque des traductions ou des enregistrements sont commandés et payés, les personnes qui ont payé détiennent les
droits et choisissent la licence ; on enregistre `compensated: yes`, jamais un montant. Les personnes qui ont fait
le travail ne sont pas identifiées dans le dépôt. Un enregistrement de la voix de quelqu'un exige toujours aussi
le consentement individuel de cette personne, quel que soit celui qui l'a payé.

## Retrait

La personne responsable de la langue ou l'autorité communautaire peut demander qu'une contribution soit retirée de
tout entraînement futur. Un retrait est une ligne dans [`contributing/takedowns.csv`](../takedowns.csv) :

| Colonne | Signification |
|---|---|
| `contribution` | L'identifiant de la contribution |
| `requested_by_role` | `steward`, `community_authority`, `contributor` ou `maintainer` (un rôle, jamais un nom) |
| `request_date`, `effective_date` | Quand le retrait a été demandé, et à partir de quand les builds l'excluent |
| `scope` | `contribution`, `text` ou `audio` |
| `note` | Facultatif, sans données personnelles |

`uyari build` exclut la contribution de tout build dont la date est égale ou postérieure à `effective_date`. Les
modèles déjà publiés ne peuvent pas être récupérés auprès des personnes qui les ont téléchargés ; leurs fiches sont
corrigées et l'entraînement suivant n'utilise plus ces données.

## Protection

* Personnes adultes uniquement. Identifiants pseudonymes (`t-0001`, `s-0001`) ; les vrais noms restent auprès de
  l'organisation contributrice.
* Pas d'enregistrements de tiers identifiables. Les phrases sur la santé décrivent des situations, jamais de vrais
  patients.
* Les peuples en isolement volontaire sont exclus.
* Les données en langues autochtones ne sont jamais envoyées à un modèle hébergé qui pourrait s'entraîner dessus :
  chaque modèle de `config/llm.yaml` déclare ce qu'il peut voir, et le code refuse dans le cas contraire.
* Usage acceptable : accès aux services, éducation et revitalisation linguistique. Utiliser les données ou les
  modèles pour surveiller, cibler ou profiler les locuteurs enfreint la licence là où la licence permet cette
  condition, et rompt la confiance là où elle ne le permet pas.
