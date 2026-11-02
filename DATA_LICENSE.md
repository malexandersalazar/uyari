# Data license

Data in this repository is licensed **per contribution**: each `contribution.yaml` names its license, and
every build carries it on every row (`license` column), so anyone can filter.

## What the project wants

Uyari exists so that clinics, hospitals, schools and public offices can use these translators, through any
provider, including companies that charge for deploying or supporting them. What we ask in return is
**credit**: the people who use a product built on Uyari should be able to learn that its models and data are
open here, and that they can reuse or extend them.

## The options

| License | Commercial use (e.g. a company deploying it for a hospital) | Credit required | Derived data must keep the same license | For Uyari |
|---|---|---|---|---|
| **CC BY 4.0** (default) | Yes | Yes | No | **Recommended**: anyone can deploy it, and everyone must credit |
| CC BY-SA 4.0 | Yes | Yes | Yes (share-alike) | Possible, but some companies and governments avoid share-alike terms |
| CC BY-NC 4.0 | **No** | Yes | No | Blocks the main route to clinics: a company hired by a ministry is commercial use |
| CC0 | Yes | **No** | No | No credit, so people may never learn the models are open |
| Community license | As written | As written | As written | For a community that needs its own terms; reviewed case by case |

A community that contributes its own data still chooses its license
([`contributing/en/governance.md`](contributing/en/governance.md)); the steward explains this table first. A
build can mix licenses, and a model inherits the most restrictive license of the rows it was trained on, so
recipes can filter rows by license.

## How to credit

CC BY 4.0 requires, whenever the data or material adapted from it is shared, the source, a link to the
license, and a note if it was changed. Please credit Uyari like this (the same text is in [`NOTICE`](NOTICE)):

> Uyari: open translation data and models between Indigenous and official languages, created by Alexander
> Salazar. Shawi–Spanish translations © 2026 Alexander Salazar and Yuri Cavero, CC BY 4.0.
> https://github.com/malexandersalazar/uyari

For models, products and services built on the data, we ask for the same credit where users can see it, for
example on an "About" page.

**The limit, stated plainly:** no standard open license can force a company that only *runs* a model as a
service, without redistributing the data or the weights, to show credit to its users. CC BY binds whoever
shares the data or an adaptation of it; Apache 2.0 binds whoever redistributes the code or the weights (they
must keep `NOTICE`). Stronger terms would need a custom license, which hospitals' and governments' lawyers
tend to reject, so Uyari keeps standard licenses and asks.

## The data today

* **Shawi–Spanish translations** (`2026-11_uyari_0001` to `0003`): **CC BY 4.0**. Commissioned work; the rights
  are held by Alexander Salazar and Yuri Cavero, who lead the Shawi–Spanish case. Collected from 2026-06-01 to
  2026-11-01. Translation continues; later work is added as new contributions.
* **Spanish primary sentences** (`primary/`): synthetic text generated for this project. **CC BY 4.0.**

## Code and models

* Code: Apache 2.0 ([`LICENSE`](LICENSE)). Keep [`NOTICE`](NOTICE) when redistributing it.
* Model weights also carry the license of their base model, whatever the data license:
  * **NLLB-200 fine-tunes: CC BY-NC 4.0** (Meta's license for NLLB-200), so **non-commercial only**. They
    are fine for research, evaluation and the free public demo, not for a company's clinic deployment.
  * **Muse Glimmer fine-tunes: Apache 2.0** (the base model's license); Uyari releases its adapters under
    Apache 2.0 with `NOTICE`. Commercial use is allowed: this is the model for clinics.

## Acceptable use

Communication access, education and language revitalization. Use for surveillance, targeting or profiling of
speakers is a license violation where the license allows the condition, and a public breach of trust where it
does not.
