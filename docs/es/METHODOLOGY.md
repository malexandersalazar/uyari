# Metodología de Uyari

[English](../../METHODOLOGY.md) · **Español** · [Português](../pt/METHODOLOGY.md) · [Français](../fr/METHODOLOGY.md) · [Deutsch](../de/METHODOLOGY.md) · [Italiano](../it/METHODOLOGY.md) · [हिन्दी](../hi/METHODOLOGY.md) · [ไทย](../th/METHODOLOGY.md)

Uyari es una estructura de datos abierta y un conjunto de herramientas de entrenamiento que convierte las
traducciones y grabaciones propias de una comunidad en modelos entre una lengua originaria u otra lengua
desatendida y la lengua oficial que necesitan sus hablantes. Una lengua se agrega como una carpeta; los datos se
agregan como una carpeta dentro de ella; nadie cambia el código. Por defecto, se usan los modelos de Meta.

Las razones de las decisiones de estructura están en [`docs/decisions/`](../../docs/decisions/). El problema que
esto aborda, con cifras y fuentes, está en [`PROBLEM.md`](PROBLEM.md).

## 1. Objetivo y alcance

**Cinco casos de uso por par de lenguas:**

| # | Caso de uso | Modelos |
|---|---|---|
| 1 | Texto en lengua originaria → texto en lengua oficial | MT |
| 2 | Texto en lengua oficial → texto en lengua originaria | MT |
| 3 | Voz en lengua originaria → voz en lengua oficial | ASR → MT → TTS |
| 4 | Voz en lengua oficial → voz en lengua originaria | ASR → MT → TTS |
| 5 | Voz en lengua originaria → texto en lengua originaria (voz a texto) | ASR |

**El primer par es shawi ↔ español** (`cbt_Latn`, glottocode `chay1248`; Perú). Es el primero porque el trabajo
ya había empezado allí, con la salud materna ([`PROBLEM.md` §6](PROBLEM.md#6-el-primer-caso-shawi--español-perú)),
no porque haya algo específico de este par. Lo que existe para él:

* 11,977 fragmentos primarios en español (sintéticos, a partir de la matriz de diseño en
  `primary/spa_Latn/matrix.yaml`).
* 3,578 traducciones humanas al shawi de 3,575 de ellos, trabajo por encargo, en tres aportes.
* Los mismos 11,977 fragmentos en inglés, traducidos automáticamente del español con los mismos ids de
  fragmento, de modo que cada traducción al shawi también forma un par con el inglés.
* Ninguna grabación en shawi. La ruta de audio (validador, build, flujos de ASR/TTS) se prueba con datos de
  prueba sintéticos y etiquetados (`qaa_Latn`), y `NEEDS.md` pide grabaciones.

| Dentro del alcance | Fuera del alcance |
|---|---|
| Cualquier lengua con forma escrita; el formato acepta todas las escrituras de ISO 15924 (hasta ahora solo se ha probado la escritura latina) | Lenguas solo orales (el formato guarda audio sin transcribir; todavía ningún flujo lo usa) |
| Lenguas oficiales como primarias: el español (generado) y el inglés (traducido automáticamente a partir de él); otras (portugués, francés, hindi, tailandés, …) por el mismo mecanismo | Investigación dialectal: las variedades son una etiqueta en un aporte |
| Traducciones y grabaciones humanas; texto escrito por máquina solo del lado de la lengua oficial, etiquetado | Traducción automática presentada como trabajo humano |
| Una lengua se incorpora cuando una comunidad aporta datos y una persona responsable (steward) | Un servicio de inferencia en producción; la demo es una demo |

## 2. Principios

1. **El aporte es la unidad.** Los datos se archivan como carpetas de aporte, cada una con su propia
   procedencia, licencia y consentimiento. Los datos se juntan solo en los builds y en las recetas, nunca
   moviendo archivos.
2. **IDs estables, nunca posiciones.** Los ids de fragmento son de 32 caracteres hexadecimales y nunca se
   reutilizan (quienes traducen trabajan con estos mismos ids). Los archivos se pueden dividir u ordenar sin
   romper ninguna referencia.
3. **Los aportes aceptados son inmutables.** Una corrección es un aporte nuevo que dice qué reemplaza.
4. **Las personas traducen y hablan; las máquinas solo pueden redactar el lado de la lengua oficial, y lo
   declaran.** Cada fragmento sintético nombra el modelo que lo escribió (`gen_model`, `provider`,
   `prompt_version`).
5. **El consentimiento y el retiro son datos.** Cada aporte lleva una licencia y una referencia de
   consentimiento; un retiro es una fila de CSV que el siguiente build aplica.
6. **Códigos estándar, nombres simples, builds reproducibles.** Las lenguas se identifican por ISO 639-3 más la
   escritura (`cbt_Latn`), la etiqueta que usan los modelos de Meta. La misma etiqueta de build produce el mismo
   hash de contenido en cualquier sistema operativo.
7. **Los datos de la comunidad nunca salen de nuestro hardware hacia un modelo que pueda entrenarse con ellos.**
   Cada modelo declara una `data_policy`; el código se niega a enviar texto en lengua originaria a un modelo
   alojado del nivel Contributor.
8. **Las API de pago son opcionales y las paga quien las usa.** La CLI usa tu propia clave; la demo le pide la
   suya a cada visitante y, si no la da, solo ejecuta los modelos abiertos con ajuste fino.

**Una consecuencia.** La partición es una propiedad del fragmento primario, compartida por todas las lenguas, y
se asigna por **grupo de paráfrasis** (las ~10 paráfrasis cercanas que produjo una misma solicitud de
generación), de modo que ningún modelo pueda ver en el entrenamiento una paráfrasis de una oración de prueba.

## 3. Modelo de datos

| Entidad | Clave | Debe tener |
|---|---|---|
| Fragmento primario | `chunk_id` (32-hex) | texto, partición, origen, estado; cada columna de la matriz de diseño que registró el generador |
| Lengua | `<iso639-3>_<Script>` | glottocode, nombre visible, persona responsable (steward), autoridad comunal, apóstrofo canónico |
| Aporte | `<YYYY-MM>_<org>_<nnnn>` | aportante (seudónimo), licencia, consentimiento, procedencia, fechas de recolección, variedad |
| Fila de par | (aporte, chunk_id) | texto, translator_id (seudónimo); `replaces` opcional |
| Fila de audio | (aporte, archivo) | hablante, estilo; chunk_id o transcripción |
| Hablante | (aporte, speaker_id) | rango de edad, referencia de consentimiento |
| Build | `data-YYYY.MM[-rN]` | una tabla por tarea y por lengua, manifiesto con hashes de archivo y de contenido |
| Receta | archivo | build, lengua, modelo base, método, hiperparámetros |
| Ficha del modelo | `name@vX.Y` | build, receta, licencia del modelo base, puntajes de validación frente al piso de recuperación, prueba una sola vez |

Filas de audio: `chunk_id` con valor y `transcript` vacío significa que el hablante leyó la traducción de ese
fragmento que contiene el aporte; `chunk_id` vacío con `transcript` con valor es habla espontánea (se reparte
entre particiones por hablante); con ambos vacíos, se guarda y no se usa. Los vocabularios cerrados están en
`schemas/`; el validador rechaza cualquier otro valor.

## 4. Corpus primario

El corpus primario es el conjunto de oraciones en lengua oficial que todas las lenguas traducen. Hoy es el
español (`primary/spa_Latn/`).

**Lo que tenemos.** El primer lote, `2026-06_opus48_0001.csv`: 10,000 fragmentos generados en junio de 2026 con
Claude Opus 4.8, que cubren 4 de los 15 dominios de la matriz y 37 microescenarios. Cada fila conserva su celda
de la matriz (dominio, microescenario, registro, acto comunicativo, tiempo verbal, polaridad, persona, rango de
longitud, perfil del hablante, tono, discurso conectado, palabras ancla, `source_custom_id`).

**Generar más, con modelos de Meta.** `uyari generate` conserva la matriz de ese lote, su rotación por tiempo
verbal/polaridad/persona, las palabras ancla, el plan en disco con estado por unidad y reejecuciones
idempotentes, la clave de grupo `custom_id`, el análisis de las respuestas, la validación y la deduplicación, y
**el prompt idéntico** (un único `prompt_version` fijado), de modo que una comparación mida modelos y no cambios
de prompt. Regenerar 200 celdas con Muse Spark 1.3 Contributor costó, por cada 1,000 fragmentos, el 3.3% de lo
que costó el primer lote, con 100% de respuestas bien formadas y un texto algo más variado
(`reports/gen-comparison.md`); Muse Glimmer en nuestra propia GPU lo hace sin costo de API. Antes de enviar,
`--estimate` muestra el costo; cada ejecución tiene un tope; cada llamada queda en el registro de costos.

**Posprocesamiento.** NFC y espacios en blanco; de 1 a 120 palabras y el rango de longitud de la unidad ±30%;
términos urbanos prohibidos; una verificación del idioma; deduplicación exacta y de casi duplicados por
embeddings (coseno 0.92, agrupando por dominio) contra todo el corpus primario; una lectura humana de control
del 2% por lote (`uyari primary sample`); un lote con más del 5% de rechazos se retira.

**Particiones.** Primera asignación: validación y prueba tienen ~300 fragmentos traducidos cada una, en grupos
de paráfrasis completos tomados de grupos traducidos, estratificados por dominio y ordenados por hash. Grupos
nuevos: un grupo que regenera una celda existente hereda su partición; los demás, por hash (5% / 5%). Una vez
escritas, quedan congeladas.

**Más corpus primarios.** El inglés (`primary/eng_Latn`) comparte los ids de fragmento con el español:
`uyari primary translate` tradujo automáticamente los 11,977 fragmentos con Muse Spark 1.3 Contributor por
US$ 0.19, con la etiqueta `origin=machine_translated` y copiando la partición, el dominio y el grupo de
paráfrasis. Las demás lenguas oficiales se agregan de la misma manera.

## 5. Agregar una lengua

Una carpeta `languages/<iso639-3>_<Script>/` con `language.yaml` y `README.md`. El validador la acepta cuando
todos los códigos se resuelven en `registry/` (se acepta el rango de uso local de ISO 639-3 `qaa`–`qtz`) y hay
una persona responsable nombrada. Campos: `id, iso639_3, script, glottocode, display_name, iso_name, primary,
steward, community_authority, apostrophe, apostrophe_variants, training_orthography, trainer`. Las letras que
las herramientas suelen alterar se declaran una sola vez: en shawi la oclusión glotal es una letra, cuya forma
canónica es `ʼ` (U+02BC), y el validador lista los caracteres variantes junto con la corrección.

## 6. Cómo contribuir

Ver [`contributing/`](../../contributing/) (inglés, español, portugués, francés, alemán, italiano, hindi,
tailandés). Una carpeta, un pull request, una lengua, una variedad, una licencia, una referencia de
consentimiento: `contribution.yaml`, `pairs.csv`, `audio.csv`, `speakers.csv`, `wav/`. Los aportes parciales
son normales; el build deduce lo que contiene una carpeta según los archivos que existen.

## 7. Revisión

Tres controles: el **validador** (CI, en cada PR), el **Gatekeeper** (Muse Glimmer en nuestra propia GPU; una
revisión escrita en la lengua de trabajo de la persona responsable, español para el shawi) y la **persona
responsable** (steward; alguien que habla la lengua). El Gatekeeper detecta fallas del validador, texto en
lengua oficial pegado en la columna de la lengua originaria, filas copiadas de aportes aceptados y texto que no
se parece a los pares aceptados; recomienda aceptar, devolver o escalar (los dominios de salud y consentimiento
siempre se escalan). **No** detecta traducción automática; quienes aportan declaran que no presentan ninguna
salida automática como trabajo humano.

## 8. Builds

`uyari build --tag data-YYYY.MM` lee todos los aportes, aplica `replaces`, omite los aportes revocados y los
retiros con fecha de vigencia igual o anterior a `--as-of`, normaliza el texto, une la partición y el dominio, y
escribe `builds/<tag>/<lang>/{mt,asr,tts}.parquet` (entrenamiento + validación) y `*.test.parquet` (prueba),
además de `MANIFEST.json`: commit de git, aportes incluidos y excluidos con sus motivos, filas excluidas con sus
motivos, filas por partición, licencias y, por cada tabla, un `sha256` del archivo y un `content_sha256`
canónico. Los datos que faltan se deducen, nunca se declaran. Los archivos Parquet no están en git; la etiqueta
los reconstruye.

## 9. Agentes

| Agente | Disparador | Decide | Escribe |
|---|---|---|---|
| **Gatekeeper** | Un PR hacia `contributions/` | aceptar / devolver / escalar (solo recomienda) | Una revisión en el PR, un borrador de `review.yaml` |
| **Trainer** | Un merge a `main` (runner propio con GPU), o a mano | Si vale la pena generar un build (lengua nueva o ≥10% más pares); promover solo si cada dirección supera el piso de recuperación **y**, en las direcciones que ambos comparten, el chrF++ de validación mejora ≥0.5 sobre el modelo vigente, reevaluado con el mismo build (o el candidato agrega direcciones y no pierde más de 0.5) | Manifiesto del build, ficha del modelo, `scores.json`, `models/registry.yaml`, `NEEDS.md`, un pull request |
| Interpreter | (después del MVP) | | |

Salvaguardas: ningún agente hace el merge; ningún agente lee la partición de prueba antes de una promoción; la
prueba se evalúa una sola vez por versión de modelo; cada decisión es una línea en el PR o en la ficha, con los
números que la produjeron.

## 10. Entrenamiento y evaluación

Las recetas en `recipes/` son la única configuración. Un modelo por backend cubre cada lengua oficial
emparejada con la originaria (hoy español e inglés: cuatro direcciones), y cada dirección se evalúa en su
propio par de lenguas. Modelos de referencia para texto:

* **Muse Glimmer 30B, QLoRA** (Unsloth, 4-bit, r=16, longitud máxima 512, lote 1 × 16, 3 épocas): el modelo
  principal, en nuestra RTX 4090.
* **NLLB-200 1.3B, ajuste fino completo** (un token de lengua nuevo inicializado a partir de una lengua
  emparentada; `quy_Latn` para el shawi): la línea de base rápida; también se entrena en una RTX 3060 de 12 GB
  en bf16 puro.
* **Piso de recuperación:** la traducción humana de la oración de entrenamiento más cercana; local, gratuito.

La demo sirve solo estos modelos con ajuste fino: Glimmer por defecto una vez entrenado, NLLB como modo rápido;
las fichas indican cuál obtiene mejor puntaje.

| Tarea | Puntaje | Control humano |
|---|---|---|
| Texto a texto | chrF++ por dirección (se reporta BLEU, no se optimiza) | Dos hablantes nativos califican 100 oraciones, cuando los hay |
| Voz a texto | CER (se reporta WER) | Aceptabilidad de la transcripción en 50 clips |
| Texto a voz | CER de ida y vuelta mediante ASR | Naturalidad de 1 a 5 |
| Voz a voz | chrF++ de la salida después de ASR | Éxito de la tarea en un diálogo con guion |

COMET y otras métricas aprendidas no se consideran confiables hacia lenguas originarias hasta que se validen
frente a juicios humanos.

## 11. Gobernanza

Código: Apache 2.0. Datos: por aporte (por defecto CC BY 4.0; CC BY-SA, CC BY-NC o una licencia comunitaria,
según elija la comunidad), registrada en cada fila de cada build. El consentimiento es colectivo (autoridad
comunal) e individual (cada hablante y cada persona que traduce); los retiros son filas en
`contributing/takedowns.csv`. Roles, licencias, plantillas de consentimiento y protecciones, en ocho lenguas:
[`contributing/<language>/governance.md`](../../contributing/es/governance.md).

## 12. Dinero

* **Local por defecto.** El entrenamiento, la evaluación, el Gatekeeper y la demo funcionan en nuestras propias
  GPU, sin costo de API.
* **Usa tu propia clave.** Todo lo que llama a una API de pago usa la clave de Meta de quien la llama: la CLI lee
  `META_API_KEY`; la demo pide a cada visitante la suya, la usa solo para esa solicitud y nunca la guarda, y
  nunca recurre a la clave del servidor.
* **Estimar antes de gastar.** Los precios están en `config/llm.yaml`; cada comando de LLM estima su costo antes
  de enviar (aproximación con tiktoken × 1.2), el uso real de cada llamada queda en `.uyari/ledger.jsonl`, y cada
  ejecución tiene un tope estricto (`generate` $1, `transcribe` $2, todo lo demás $0 porque corre localmente). El
  presupuesto propio del proyecto para API alojadas durante el desarrollo es de USD 150.
