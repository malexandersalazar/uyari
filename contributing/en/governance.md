# Governance: rights, consent and withdrawal

[English](../en/governance.md) · [Español](../es/governance.md) · [Português](../pt/governance.md) · [Français](../fr/governance.md) · [Deutsch](../de/governance.md) · [Italiano](../it/governance.md) · [हिन्दी](../hi/governance.md) · [ไทย](../th/governance.md)

Uyari holds people's words and voices. These rules apply to every language and every contribution. They
follow free, prior and informed consent (UN Declaration on the Rights of Indigenous Peoples; ILO Convention
169), the CARE principles for Indigenous data governance, and the national law of each country where data is
collected.

## Who decides

| Role | Decides |
|---|---|
| **Maintainer** (the project lead) | Structure, schemas, validator, builds, the methodology |
| **Steward** (one per language, a person who speaks it) | Everything inside that language: accepts contributions, names reviewers, files withdrawals |
| **Community authority** (named in `language.yaml`) | Consent on behalf of the community; may request a withdrawal at any time |
| **Contributor** (a person or an organization) | Produces contributions and chooses, with the community, their license |

No agent decides: the Gatekeeper and the Trainer only recommend, and a person merges.

## Licenses

Each contribution names its license in `contribution.yaml`, and every build carries it on every row, so
anyone using the data can filter by license.

* Default: **CC BY 4.0**. A community may choose CC BY-SA 4.0, CC BY-NC 4.0, CC0 or its own community license.
* The steward explains the trade-off before the community chooses: a non-commercial license stops a company
  from deploying the translator for a ministry or a clinic, which is often the main way it reaches people.
* Code is Apache 2.0. Model weights also inherit the license of their base model.

## Consent

Consent is **collective** (the community authority agrees to the purpose and the license) and **individual**
(each adult translator and speaker agrees for themselves). The templates are in this folder, with the same
file names in every language:

| Template | Who agrees | Named in |
|---|---|---|
| [`consent-collective.md`](consent-collective.md) | The community authority | `contribution.yaml` → `consent.template` |
| [`consent-individual.md`](consent-individual.md) | Each translator and speaker | `speakers.csv` → `consent_ref` |
| [`commissioned-work.md`](commissioned-work.md) | Whoever commissioned and paid for the work, as rights holder | `contribution.yaml` → `consent.template` |

`contribution.yaml` names the template by file name only (for example `consent-collective.md`), so the same
reference holds in every language. Signed copies stay with the contributing organization; the repository
holds only the template name and the authority, never a signature or a real name.

## Commissioned work

When translations or recordings are commissioned and paid for, the people who paid hold the rights and choose
the license; `compensated: yes` is recorded, never an amount. The individuals who did the work are not
identified in the repository. A recording of someone's voice always also needs that person's individual
consent, whoever paid for it.

## Withdrawal

A steward or community authority can ask for a contribution to leave all future training. Withdrawal is one
row in [`contributing/takedowns.csv`](../takedowns.csv):

| Column | Meaning |
|---|---|
| `contribution` | The contribution id |
| `requested_by_role` | `steward`, `community_authority`, `contributor` or `maintainer` (a role, never a name) |
| `request_date`, `effective_date` | When it was asked for, and from when builds exclude it |
| `scope` | `contribution`, `text` or `audio` |
| `note` | Optional, no personal data |

`uyari build` excludes the contribution from every build whose date is on or after `effective_date`. Models
already published cannot be recalled from people who downloaded them; their cards are corrected and the next
training run no longer uses the data.

## Protection

* Adults only. Pseudonymous ids (`t-0001`, `s-0001`); real names stay with the contributing organization.
* No recordings of identifiable third parties. Health sentences describe situations, never real patients.
* Peoples in voluntary isolation are excluded.
* Indigenous-language data is never sent to a hosted model that may train on it: every model in
  `config/llm.yaml` declares what it may see, and the code refuses otherwise.
* Acceptable use: access to services, education and language revitalization. Using the data or the models to
  surveil, target or profile speakers breaks the license where the license allows that condition, and breaks
  trust where it does not.
