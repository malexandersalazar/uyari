# O problema: a barreira linguística nos serviços básicos

[English](../../PROBLEM.md) · [Español](../es/PROBLEM.md) · **Português** · [Français](../fr/PROBLEM.md) · [Deutsch](../de/PROBLEM.md) · [Italiano](../it/PROBLEM.md) · [हिन्दी](../hi/PROBLEM.md) · [ไทย](../th/PROBLEM.md)

Cerca de **476 milhões** de pessoas indígenas vivem em 90 países. Muitas delas se deparam com médicos, termos
de consentimento, tribunais e registros civis numa língua oficial que não entendem por completo. Onde isso é
medido, os números são grandes: em apenas quatro países da América Latina, cerca de **3 milhões** de pessoas
não conseguem usar de forma alguma a língua oficial do seu país. Em outros lugares, em geral, isso não é
contado.

Os modelos abertos de base para voz e tradução já cobrem mais de 1,600 línguas. O que não existe é a camada
que os transforma em algo que uma clínica possa usar: **modelos avaliados e governados pela comunidade entre
cada língua indígena e a língua oficial de que os seus falantes precisam, em texto e em voz**. O Uyari constrói
essa camada de última milha para qualquer língua. Ele não constrói mais um modelo de base.

## 1. Escala

| Região (OIT, 2019) | Proporção | População indígena |
|---|---|---|
| Ásia e Pacífico | 70.5% | >335M |
| África | 16.3% | >77M |
| América Latina e Caribe | 11.5% | ~55M (CEPAL 2018: 58M; 826 povos) |
| América do Norte | 1.6% | >7M |
| Europa e Ásia Central | 0.1% | <1M |
| **Mundo** | | **476.6M (>6% da humanidade)** |

* Pessoas indígenas têm quase três vezes mais probabilidade de viver em pobreza extrema (OIT).
* Das 7,159 línguas vivas, 3,193 (cerca de 45%) estão ameaçadas (Ethnologue, 28ª ed., 2025).
* 40% das pessoas no mundo não recebem educação numa língua que entendem, e até 90% em alguns países de renda
  baixa e média (UNESCO GEM Report, 2025).

## 2. Pessoas que não conseguem usar a língua oficial

Não existe uma contagem global; poucos censos fazem essa pergunta. A região mais bem medida é a América Latina:

| País | Falantes de línguas indígenas | Não conseguem usar a língua oficial | Fonte |
|---|---|---|---|
| México | 7,364,645 (6.1%, 3 anos ou mais) | **865,972** não falam espanhol | INEGI, Censo 2020 (contagem direta) |
| Guatemala | 4,027,481 falantes de língua materna | **~1.64M** (20.9% da população indígena) | Instituto Cervantes 2024 (estimativa) |
| Peru | 4,477,195 falantes de língua materna (16.02%, 3 anos ou mais) | **~335,576** | Instituto Cervantes 2024 (estimativa; o censo não faz essa pergunta) |
| Bolívia | ~4.2M (2012) | **~267,729** | Instituto Cervantes 2024 (estimativa) |

São cerca de **3.1 milhões** de pessoas em quatro países, além de vários milhões de bilíngues que conseguem
fazer compras na língua oficial, mas não conseguem acompanhar um diagnóstico ou uma audiência judicial. A mesma
lacuna existe onde quer que um Estado funcione numa língua que os seus cidadãos indígenas não falam; ela apenas
não é contada. Setenta por cento das pessoas indígenas do mundo vivem na Ásia e no Pacífico, onde não existe
um número comparável.

Essas populações não são pequenas. Só os falantes de línguas indígenas do México já são mais numerosos que os
falantes de dinamarquês, finlandês ou norueguês, e todas essas línguas têm suporte completo de IA comercial.

## 3. Por que isso importa: saúde, educação, justiça

* **Saúde.** Na Guatemala, a barreira linguística era "o obstáculo mais importante" para o uso de serviços de
  saúde reprodutiva por mulheres indígenas (análise do Guttmacher sobre a pesquisa nacional de 2008–09), e a
  mortalidade materna das mulheres indígenas era mais que o dobro da das mulheres não indígenas: 166 contra 78
  por 100,000 nascidos vivos (estudo nacional de 2011). Na Guatemala, no México, no Peru e na Bolívia, as
  mulheres que *falam* uma língua indígena têm menos probabilidade de dar à luz numa unidade de saúde. Onde os
  hospitais não têm intérpretes, o consentimento informado fracassa.
* **Educação.** Crianças que aprendem numa língua que falam têm muito mais probabilidade de ler com
  compreensão (UNESCO 2025). No México, os falantes de línguas indígenas com 15 anos ou mais têm em média 6.2
  anos de escolaridade; **os monolíngues têm em média 1.4** (INEGI 2020).
* **Justiça e governo.** Leis que reconhecem as línguas indígenas são comuns; intérpretes, não. O Congresso do
  Peru ficou repetidas vezes sem intérpretes para as línguas indígenas oficiais, e o México dá validade legal
  às línguas indígenas enquanto a implementação fica para trás.

Os monolíngues são, em proporção desmedida, pessoas mais velhas, mulheres e pessoas não alfabetizadas. **A voz
não é opcional**: a tradução de texto, sozinha, não chega até essas pessoas.

## 4. O que existe e o que falta

| Camada | O que existe | Lacuna |
|---|---|---|
| Modelos de base | Meta Omnilingual ASR (1,600+ línguas, Apache 2.0), Omnilingual MT (1,600+), NLLB-200, MMS; Google Translate; Microsoft Translator | Avaliados sobretudo em relação ao inglês; qualidade desconhecida para a maioria das línguas indígenas; pouco TTS ou tradução de voz para voz |
| Benchmarks | Tarefas compartilhadas regionais, como a AmericasNLP (~13 línguas ↔ espanhol, só texto) | A tradução automática língua oficial → língua indígena "atingiu um platô de desempenho" ali (chrF++ por volta de 13–37) |
| Projetos comunitários | Te Hiku Media (maori), Voces (Chile/Peru), muitos pilotos locais | Uma ou poucas línguas cada; não reutilizáveis como pipeline |

O que falta, e para o que o Uyari foi feito:

1. **Pares língua nativa ↔ língua oficial**, e não uma ponte pelo inglês que acumula erros.
2. **Voz** (ASR, TTS, voz para voz) para línguas cujos falantes muitas vezes não leem.
3. **Dados de domínio** para saúde, consentimento, registro civil e justiça.
4. **Avaliação humana** por falantes nativos e intérpretes certificados, e não só métricas automáticas.
5. **Atenção aos dialetos**: um nome de língua muitas vezes abrange muitas variedades ("quéchua" são mais de 25
   só no Peru).
6. **Governança**: consentimento, repartição de benefícios e licenças compatíveis com a soberania indígena
   sobre os dados.
7. **Implantação** que possa rodar offline em hardware modesto.

## 5. A abordagem

* **Cinco casos de uso por par de línguas:** texto indígena → texto oficial, texto oficial → texto indígena,
  voz indígena → voz oficial, voz oficial → voz indígena, e voz para texto na língua indígena.
* **Construir sobre os modelos abertos de base da Meta; adaptar por língua.** Fazer o ajuste fino (fine-tuning)
  de um modelo multilíngue compartilhado (Muse Glimmer QLoRA, NLLB-200) em cada par nativo↔oficial; um piso de
  recuperação mantém cada modelo honesto.
* **Voz para voz em cascata** (ASR → MT → TTS), com o texto visível no meio, para que uma pessoa possa conferir
  um diagnóstico ou um termo de consentimento antes que ele seja falado.
* **Os dados são o orçamento.** Por língua, aproximadamente 5–20k frases de domínio, 4–10 h de fala lida por uma
  única pessoa para criar uma voz (uma voz em shipibo-konibo chegou a MOS 4.01 com ~4 h) e 10–50 h de fala
  transcrita. A computação é uma pequena fração do custo (uma estimativa de engenharia, não um número
  publicado).
* **Qualquer língua, sem mudar o código.** Uma língua é uma pasta; os dados de uma comunidade são uma pasta
  dentro dela. O lado da língua oficial é um corpus compartilhado (espanhol primeiro; outras línguas oficiais
  pelo mesmo mecanismo).
* **Governança desde a concepção**: consentimento livre, prévio e informado (UNDRIP, Convenção 169 da OIT), os princípios
  CARE, licenças por contribuição, a retirada como uma linha de dados, contribuidores remunerados e os povos em
  isolamento voluntário explicitamente excluídos.
* **Intérpretes como criadores e avaliadores de dados**, e não como pessoas substituídas pela ferramenta.
* **Medir o impacto, não só o chrF++**: compreensão do consentimento, realização das consultas de pré-natal,
  tempo até o atendimento.

## 6. O primeiro caso: shawi ↔ espanhol (Peru)

O shawi vem primeiro porque o trabalho já tinha começado ali, e não porque o problema seja peruano. O caso
shawi–espanhol começou pela saúde materna: as comunidades shawi recorrem a serviços de saúde que não oferecem
nenhum apoio na sua língua. Quem lidera o caso mandou fazer traduções humanas, e essas traduções são os
primeiros dados do Uyari. Nada no código é específico do shawi.

| Indicador | Número | Fonte |
|---|---|---|
| Povos / línguas indígenas no Peru | 55 povos; 48 línguas oficiais | MinCul (2025–26) |
| Língua materna indígena, 3 anos ou mais | 4,477,195; quéchua 3,799,780; aimará 450,010 | Censo de 2017 (via MinCul 2024) |
| Língua materna shawi | 17,241 | MinCul BDPI (censo de 2017) |
| Intérpretes registrados | **859** (ReNITLI), cobrindo 39 de 48 línguas | MinCul (jan. 2025) |

São cerca de 5,200 falantes de língua materna por intérprete registrado, e nove línguas não têm nenhum. Só em
23.1% dos domicílios onde a língua materna de um dos pais é indígena há um filho ou filha que a fala (INEI
2017); a população monolíngue está envelhecendo, e por isso a janela para gravar pessoas idosas fluentes está
se fechando.

## Ressalvas

* Os números de população são estimativas de 2010–2019. As definições (sobretudo para a China e a Índia)
  alteram os totais globais em mais de 100M.
* Só os 865,972 do México são uma contagem censitária direta de pessoas que não falam a língua oficial. Os
  números do Peru, da Guatemala e da Bolívia são estimativas do Instituto Cervantes 2024, feitas a partir de
  indicadores indiretos de analfabetismo, e podem estar superestimados.
* As afirmações sobre a qualidade dos modelos de base são autodeclaradas e centradas no inglês. Existem poucas
  avaliações independentes entre as línguas indígenas e as línguas oficiais dos seus países.
* As perguntas dos censos variam: o do Peru pergunta pela língua materna, e não pelo domínio da língua oficial,
  e as idades de referência diferem (3+ vs 5+); por isso, é preciso sempre indicá-las.
