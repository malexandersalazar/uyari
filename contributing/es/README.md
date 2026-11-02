# Cómo contribuir a Uyari

[English](../en/README.md) · [Español](../es/README.md) · [Português](../pt/README.md) · [Français](../fr/README.md) · [Deutsch](../de/README.md) · [Italiano](../it/README.md) · [हिन्दी](../hi/README.md) · [ไทย](../th/README.md)

Uyari reúne traducciones y grabaciones **hechas por personas** para que las lenguas originarias y otras lenguas
desatendidas tengan herramientas abiertas de traducción, en texto y en voz, hacia y desde la lengua oficial que
sus hablantes necesitan para la atención de salud, la escuela y los trámites con el Estado. Cualquier lengua
puede sumarse. Cada aporte es una carpeta; no hace falta programar.

Antes de contribuir, lee las reglas sobre derechos, consentimiento y retiro: [governance.md](governance.md).

## Qué se necesita ahora

Cada lengua tiene un `NEEDS.md` que el sistema mantiene al día. El shawi (Perú) es la primera lengua; su lista
es [`languages/cbt_Latn/NEEDS.md`](../../languages/cbt_Latn/NEEDS.md). Hoy pide:

1. **Grabaciones leídas** de traducciones que ya existen, de al menos 3 personas adultas, con su consentimiento.
2. **Más oraciones de salud y registro civil** traducidas al shawi, revisadas por un segundo lector nativo.

**Para agregar una lengua nueva**, abre un issue con su nombre, su código ISO 639-3, la lengua oficial que
necesitan sus hablantes y quién podría ser su persona responsable (steward): alguien que la hable y revise los
aportes.

## Un aporte = una carpeta = un pull request

```
languages/<language>/contributions/<YYYY-MM>_<organization>_<nnnn>/
  contribution.yaml   who (pseudonym), when, how it was made, license, consent
  pairs.csv           chunk_id, text, replaces, translator_id, notes      (text)
  audio.csv           file, chunk_id, transcript, speaker_id, style, device, notes   (audio)
  speakers.csv        speaker_id, age_band, sex, first_language, consent_ref        (audio)
  wav/                16 or 48 kHz, mono, 16-bit, 1 to 20 seconds, one person per clip
```

* Una carpeta tiene **una** lengua, **una** variedad, **una** licencia y **una** referencia de consentimiento.
* Se traduce desde las oraciones en lengua oficial de `primary/` (hoy: español, `primary/spa_Latn/chunks/`).
  Cada fila de `pairs.csv` apunta a un `chunk_id`. Se traduce la oración completa.
* Las letras de la lengua se escriben como indica su `language.yaml`. En shawi, por ejemplo, la oclusión glotal
  es **ʼ** (U+02BC); `uyari validate` muestra dónde hay que convertir `'`, `’` o `´`.
* **Nada de traducción automática ni voces sintéticas presentadas como trabajo humano.** Si una persona
  corrigió una salida automática, se declara en `contribution.yaml` (`human_post_edited_from_mt`).
* Solo personas adultas. Nada de nombres reales en los archivos: usa `t-0001`, `s-0001`. La organización que
  aporta guarda su propia lista.
* Un aporte aceptado nunca se edita: una corrección es una fila nueva en un aporte posterior con
  `replaces=<contribution>/<chunk_id>`.

## Qué pasa con tu pull request

1. **Validador** (automático): formato, códigos, ids, apóstrofos, audio.
2. **Gatekeeper** (automático, Muse Glimmer en la GPU propia del proyecto): revisa si alguna fila parece estar
   en la lengua oficial en vez de en la lengua originaria, o si fue copiada, y escribe una revisión fila por fila
   en el pull request.
3. **La persona responsable de la lengua (steward)** lee la revisión, revisa algunas filas al azar y decide. El
   contenido de salud y de consentimiento informado siempre necesita un segundo lector nativo.

Después del merge, el **Trainer** reconstruye los datos, entrena, mide y abre un pull request con los resultados.

## Retirar datos

La persona responsable o la autoridad comunal puede pedir que un aporte salga de todo entrenamiento futuro: es
una fila en [`contributing/takedowns.csv`](../takedowns.csv). Los modelos ya publicados no se pueden recuperar de
quienes ya los descargaron; sus fichas se corrigen y el siguiente entrenamiento ya no usa esos datos. Detalles:
[governance.md](governance.md#retiro).

## Contribuir código

```bash
uv sync --python 3.11 --extra dev --extra speech
uv run pytest -q
uv run ruff check src tests
git config core.hooksPath .githooks     # privacy check before every commit
```

El trabajo con GPU se hace en Ubuntu: [`docs/RUNBOOK-4090.md`](../../docs/RUNBOOK-4090.md). Todo comando que
llama a una API de pago tiene `--estimate` y usa tu propia clave (`META_API_KEY`), y los datos en lenguas
originarias nunca van a un modelo alojado por terceros (`data_policy` en `config/llm.yaml`).
