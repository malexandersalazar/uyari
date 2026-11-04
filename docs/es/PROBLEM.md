# El problema: la brecha lingüística en los servicios básicos

[English](../../PROBLEM.md) · **Español** · [Português](../pt/PROBLEM.md) · [Français](../fr/PROBLEM.md) · [Deutsch](../de/PROBLEM.md) · [Italiano](../it/PROBLEM.md) · [हिन्दी](../hi/PROBLEM.md) · [ไทย](../th/PROBLEM.md)

Unos **476 millones** de personas indígenas viven en 90 países. Muchas de ellas tratan con médicos, formularios
de consentimiento, juzgados y registros civiles en una lengua oficial que no entienden del todo. Donde esto se
mide, las cifras son grandes: solo en cuatro países de América Latina, unos **3 millones** de personas no pueden
usar en absoluto la lengua oficial de su país. En la mayoría de los demás lugares, no se cuenta.

Los modelos base abiertos de voz y traducción ya cubren más de 1,600 lenguas. Lo que no existe es la capa que
los convierte en algo que una clínica pueda usar: **modelos evaluados y gobernados por la comunidad entre cada
lengua originaria y la lengua oficial que necesitan sus hablantes, en texto y en voz**. Uyari construye esa
capa de última milla para cualquier lengua. No construye otro modelo base.

## 1. Magnitud

| Región (OIT, 2019) | Proporción | Población indígena |
|---|---|---|
| Asia y el Pacífico | 70.5% | >335M |
| África | 16.3% | >77M |
| América Latina y el Caribe | 11.5% | ~55M (CEPAL 2018: 58M; 826 pueblos) |
| América del Norte | 1.6% | >7M |
| Europa y Asia Central | 0.1% | <1M |
| **Mundo** | | **476.6M (>6% de la humanidad)** |

* Las personas indígenas tienen casi tres veces más probabilidades de vivir en pobreza extrema (OIT).
* De 7,159 lenguas vivas, 3,193 (alrededor del 45%) están en peligro (Ethnologue, 28.ª ed., 2025).
* El 40% de las personas en el mundo no recibe educación en una lengua que entiende; en algunos países de
  ingresos bajos y medianos, hasta el 90% (Informe GEM de la UNESCO, 2025).

## 2. Personas que no pueden usar la lengua oficial

No existe un recuento mundial; pocos censos hacen la pregunta. La región mejor medida es América Latina:

| País | Hablantes de lenguas originarias | No pueden usar la lengua oficial | Fuente |
|---|---|---|---|
| México | 7,364,645 (6.1%, de 3 años o más) | **865,972** no hablan español | INEGI, Censo 2020 (conteo directo) |
| Guatemala | 4,027,481 hablantes como lengua materna | **~1.64M** (20.9% de la población indígena) | Instituto Cervantes 2024 (estimación) |
| Perú | 4,477,195 hablantes como lengua materna (16.02%, de 3 años o más) | **~335,576** | Instituto Cervantes 2024 (estimación; el censo no lo pregunta) |
| Bolivia | ~4.2M (2012) | **~267,729** | Instituto Cervantes 2024 (estimación) |

Eso suma aproximadamente **3.1 millones** de personas en cuatro países, más varios millones de personas
bilingües que pueden hacer compras en la lengua oficial, pero no pueden seguir un diagnóstico ni una audiencia
judicial. La misma brecha existe dondequiera que un Estado funcione en una lengua que sus ciudadanos indígenas
no hablan; simplemente no se cuenta. El setenta por ciento de las personas indígenas del mundo vive en Asia y
el Pacífico, donde no existe una cifra comparable.

Estas poblaciones no son pequeñas. Solo los hablantes de lenguas originarias de México ya son más que los
hablantes de danés, finés o noruego, y las tres lenguas cuentan con pleno soporte comercial de IA.

## 3. Por qué importa: salud, educación, justicia

* **Salud.** En Guatemala, la barrera lingüística fue "el obstáculo más importante" para que las mujeres
  indígenas usaran los servicios de salud reproductiva (análisis de Guttmacher sobre la encuesta nacional de
  2008–09), y la mortalidad materna de las mujeres indígenas fue más del doble que la de las mujeres no
  indígenas: 166 frente a 78 por cada 100,000 nacidos vivos (estudio nacional de 2011). En Guatemala, México,
  Perú y Bolivia, las mujeres que *hablan* una lengua originaria tienen menos probabilidades de dar a luz en un
  establecimiento de salud. Donde los hospitales no tienen intérpretes, el consentimiento informado fracasa.
* **Educación.** Los niños y niñas que reciben clases en una lengua que hablan tienen muchas más probabilidades
  de leer comprendiendo lo que leen (UNESCO 2025). En México, los hablantes de lenguas originarias de 15 años o
  más tienen en promedio 6.2 años de escolaridad; **los monolingües, 1.4** (INEGI 2020).
* **Justicia y gobierno.** Las leyes que reconocen las lenguas originarias son comunes; los intérpretes, no.
  Al Congreso del Perú le han faltado intérpretes una y otra vez para las lenguas originarias oficiales, y
  México da validez legal a las lenguas originarias mientras su aplicación se queda atrás.

Entre las personas monolingües hay una proporción desmedida de personas mayores, mujeres y personas que no
saben leer ni escribir. **La voz no es opcional**: la traducción de texto, por sí sola, no llega a ellas.

## 4. Qué existe y qué falta

| Capa | Qué existe | Brecha |
|---|---|---|
| Modelos base | Meta Omnilingual ASR (1,600+ lenguas, Apache 2.0), Omnilingual MT (1,600+), NLLB-200, MMS; Google Translate; Microsoft Translator | Evaluados sobre todo frente al inglés; calidad desconocida para la mayoría de las lenguas originarias; poca síntesis de voz (TTS) o traducción de voz a voz |
| Benchmarks | Tareas compartidas regionales, como AmericasNLP (~13 lenguas ↔ español, solo texto) | Ahí, la traducción automática de lengua oficial → lengua originaria "llegó a una meseta de rendimiento" (chrF++ de alrededor de 13–37) |
| Proyectos comunitarios | Te Hiku Media (maorí), Voces (Chile/Perú), muchos pilotos locales | Una o pocas lenguas cada uno; no se pueden reutilizar como una cadena de procesamiento |

Lo que falta, y para lo que está hecho Uyari:

1. **Pares lengua originaria ↔ lengua oficial**, no un pivote a través del inglés que acumula errores.
2. **Voz** (ASR, TTS, voz a voz) para lenguas cuyos hablantes a menudo no leen.
3. **Datos de dominio** para salud, consentimiento, registro civil y justicia.
4. **Evaluación humana** por hablantes nativos e intérpretes certificados, no solo métricas automáticas.
5. **Atención a los dialectos**: un solo nombre de lengua suele abarcar muchas variedades ("quechua" son más
   de 25 solo en el Perú).
6. **Gobernanza**: consentimiento, distribución de beneficios y licencias compatibles con la soberanía de
   datos indígenas.
7. **Despliegue** que pueda funcionar sin conexión en hardware modesto.

## 5. El enfoque

* **Cinco casos de uso por par de lenguas:** texto en lengua originaria → texto en lengua oficial, texto en
  lengua oficial → texto en lengua originaria, voz en lengua originaria → voz en lengua oficial, voz en lengua
  oficial → voz en lengua originaria, y voz a texto para la lengua originaria.
* **Construir sobre los modelos base abiertos de Meta; adaptar por lengua.** Ajustar un modelo multilingüe
  compartido (Muse Glimmer QLoRA, NLLB-200) con cada par lengua originaria↔lengua oficial; un piso de
  recuperación mantiene honesto a cada modelo.
* **Voz a voz como cascada** (ASR → MT → TTS), con el texto visible en el medio para que una persona pueda
  revisar un diagnóstico o un formulario de consentimiento antes de que se diga en voz alta.
* **El presupuesto se va en datos.** Por lengua, aproximadamente 5–20k oraciones de dominio, 4–10 h de habla
  leída por una sola persona para una voz (una voz en shipibo-konibo alcanzó un MOS de 4.01 con ~4 h) y 10–50 h
  de habla transcrita. El cómputo es una pequeña fracción del costo (una estimación de ingeniería, no una cifra
  publicada).
* **Cualquier lengua, sin cambios en el código.** Una lengua es una carpeta; los datos de una comunidad son una
  carpeta dentro de ella. El lado de la lengua oficial es un corpus compartido (primero el español; otras
  lenguas oficiales por el mismo mecanismo).
* **Gobernanza desde el diseño**: consentimiento libre, previo e informado (UNDRIP, Convenio 169 de la OIT), los principios
  CARE, licencias por aporte, el retiro como una fila de datos, pago a quienes aportan, y exclusión explícita
  de los pueblos en aislamiento voluntario.
* **Los intérpretes como creadores y evaluadores de datos**, no como personas desplazadas por la herramienta.
* **Medir el impacto, no solo chrF++**: comprensión del consentimiento, controles prenatales completados,
  tiempo hasta recibir el servicio.

## 6. El primer caso: shawi ↔ español (Perú)

El shawi es el primero porque el trabajo ya había empezado allí, no porque el problema sea peruano. El caso
shawi–español empezó con la salud materna: las comunidades shawi acuden a servicios de salud que no ofrecen
apoyo en su lengua. Para este caso se encargaron traducciones hechas por personas, y esas traducciones
son los primeros datos de Uyari. Nada en el código es específico del shawi.

| Indicador | Cifra | Fuente |
|---|---|---|
| Pueblos indígenas / lenguas originarias en el Perú | 55 pueblos; 48 lenguas oficiales | MinCul (2025–26) |
| Lengua materna originaria, de 3 años o más | 4,477,195; quechua 3,799,780; aimara 450,010 | Censo 2017 (vía MinCul 2024) |
| Lengua materna shawi | 17,241 | MinCul BDPI (censo 2017) |
| Intérpretes registrados | **859** (ReNITLI), que cubren 39 de 48 lenguas | MinCul (ene. 2025) |

Hay unos 5,200 hablantes de lengua materna por cada intérprete registrado, y nueve lenguas no tienen ninguno.
Solo el 23.1% de los hogares donde la lengua materna del padre o de la madre es originaria tiene un hijo o hija
que la habla (INEI 2017); la población monolingüe está envejeciendo, así que se está cerrando la oportunidad de
grabar a las personas mayores que hablan la lengua con fluidez.

## Salvedades

* Las cifras de población son estimaciones de 2010–2019. Las definiciones (sobre todo para China e India)
  cambian los totales mundiales en más de 100M.
* Solo los 865,972 de México son un conteo censal directo de personas que no hablan la lengua oficial. Las
  cifras de Perú, Guatemala y Bolivia son estimaciones del Instituto Cervantes 2024 basadas en indicadores
  indirectos de analfabetismo y pueden sobrestimar la cifra real.
* Las afirmaciones sobre la calidad de los modelos base son autodeclaradas y centradas en el inglés. Hay pocas
  evaluaciones independientes entre lenguas originarias y las lenguas oficiales de sus países.
* Las preguntas de los censos difieren: el del Perú pregunta por la lengua materna, no por el dominio de la
  lengua oficial, y las edades de referencia difieren (3+ frente a 5+), así que siempre hay que indicarlas.
