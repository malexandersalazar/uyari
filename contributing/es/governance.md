# Gobernanza: derechos, consentimiento y retiro

[English](../en/governance.md) · [Español](../es/governance.md) · [Português](../pt/governance.md) · [Français](../fr/governance.md) · [Deutsch](../de/governance.md) · [Italiano](../it/governance.md) · [हिन्दी](../hi/governance.md) · [ไทย](../th/governance.md)

Uyari guarda palabras y voces de personas. Estas reglas se aplican a todas las lenguas y a todos los aportes.
Siguen el consentimiento libre, previo e informado (Declaración de las Naciones Unidas sobre los Derechos de los
Pueblos Indígenas; Convenio 169 de la OIT), los principios CARE para la gobernanza de datos indígenas y la
legislación nacional de cada país donde se recogen los datos.

## Quién decide

| Rol | Decide |
|---|---|
| **Mantenedor** (quien dirige el proyecto) | La estructura, los esquemas, el validador, los builds, la metodología |
| **Persona responsable de la lengua (steward)** (una por lengua, alguien que la habla) | Todo lo que ocurre dentro de esa lengua: acepta aportes, nombra a quienes revisan, registra retiros |
| **Autoridad comunal** (nombrada en `language.yaml`) | El consentimiento en nombre de la comunidad; puede pedir un retiro en cualquier momento |
| **Aportante** (una persona o una organización) | Produce aportes y elige su licencia junto con la comunidad |

Ningún agente decide: el Gatekeeper y el Trainer solo recomiendan, y es una persona quien hace el merge.

## Licencias

Cada aporte indica su licencia en `contribution.yaml`, y cada build la lleva en cada fila, para que cualquiera
que use los datos pueda filtrar por licencia.

* Por defecto: **CC BY 4.0**. Una comunidad puede elegir CC BY-SA 4.0, CC BY-NC 4.0, CC0 o su propia licencia
  comunitaria.
* La persona responsable explica lo que se gana y lo que se pierde antes de que la comunidad elija: una licencia
  no comercial impide que una empresa despliegue el traductor para un ministerio o una clínica, que suele ser la
  principal vía por la que llega a la gente.
* El código es Apache 2.0. Los pesos de los modelos, además, heredan la licencia de su modelo base.

## Consentimiento

El consentimiento es **colectivo** (la autoridad comunal acepta el propósito y la licencia) e **individual**
(cada persona adulta que traduce o habla acepta por sí misma). Las plantillas están en esta carpeta, con los
mismos nombres de archivo en todas las lenguas:

| Plantilla | Quién acepta | Se indica en |
|---|---|---|
| [`consent-collective.md`](consent-collective.md) | La autoridad comunal | `contribution.yaml` → `consent.template` |
| [`consent-individual.md`](consent-individual.md) | Cada persona que traduce y cada hablante | `speakers.csv` → `consent_ref` |
| [`commissioned-work.md`](commissioned-work.md) | Quien encargó y pagó el trabajo, como titular de los derechos | `contribution.yaml` → `consent.template` |

`contribution.yaml` indica la plantilla solo por su nombre de archivo (por ejemplo `consent-collective.md`), así
que la misma referencia vale en todas las lenguas. Las copias firmadas quedan en poder de la organización que
aporta; el repositorio guarda solo el nombre de la plantilla y la autoridad, nunca una firma ni un nombre real.

## Trabajo por encargo

Cuando las traducciones o grabaciones se encargan y se pagan, quienes pagaron tienen los derechos y eligen la
licencia; se registra `compensated: yes`, nunca un monto. Las personas que hicieron el trabajo no se identifican
en el repositorio. Una grabación de la voz de alguien siempre necesita, además, el consentimiento individual de
esa persona, sin importar quién la pagó.

## Retiro

La persona responsable o la autoridad comunal puede pedir que un aporte salga de todo entrenamiento futuro. Un
retiro es una fila en [`contributing/takedowns.csv`](../takedowns.csv):

| Columna | Significado |
|---|---|
| `contribution` | El id del aporte |
| `requested_by_role` | `steward`, `community_authority`, `contributor` o `maintainer` (un rol, nunca un nombre) |
| `request_date`, `effective_date` | Cuándo se pidió y desde cuándo los builds lo excluyen |
| `scope` | `contribution`, `text` o `audio` |
| `note` | Opcional, sin datos personales |

`uyari build` excluye el aporte de todo build cuya fecha sea igual o posterior a `effective_date`. Los modelos
ya publicados no se pueden recuperar de quienes los descargaron; sus fichas se corrigen y el siguiente
entrenamiento ya no usa esos datos.

## Protección

* Solo personas adultas. Ids seudónimos (`t-0001`, `s-0001`); los nombres reales quedan en poder de la
  organización que aporta.
* Nada de grabaciones de terceros identificables. Las oraciones de salud describen situaciones, nunca pacientes
  reales.
* Se excluye a los pueblos en aislamiento voluntario.
* Los datos en lenguas originarias nunca se envían a un modelo alojado que pueda entrenarse con ellos: cada
  modelo en `config/llm.yaml` declara qué puede ver, y el código se niega en caso contrario.
* Uso aceptable: acceso a servicios, educación y revitalización lingüística. Usar los datos o los modelos para
  vigilar, perseguir o perfilar a hablantes viola la licencia donde la licencia permite esa condición, y rompe
  la confianza donde no la permite.
