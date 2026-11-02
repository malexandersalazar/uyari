# Metodologia do Uyari

[English](../../METHODOLOGY.md) · [Español](../es/METHODOLOGY.md) · **Português** · [Français](../fr/METHODOLOGY.md) · [Deutsch](../de/METHODOLOGY.md) · [Italiano](../it/METHODOLOGY.md) · [हिन्दी](../hi/METHODOLOGY.md) · [ไทย](../th/METHODOLOGY.md)

O Uyari é uma estrutura de dados aberta e um kit de ferramentas de treinamento que transforma as traduções e
gravações da própria comunidade em modelos entre uma língua indígena, ou outra língua pouco atendida, e a
língua oficial de que os seus falantes precisam. Uma língua é adicionada como uma pasta; os dados são
adicionados como uma pasta dentro dela; ninguém muda código. Os modelos da Meta são o stack padrão.

Os motivos por trás das escolhas estruturais estão em [`docs/decisions/`](../../docs/decisions/). O problema
que isto aborda, com números e fontes, está em [`PROBLEM.md`](PROBLEM.md).

## 1. Objetivo e escopo

**Cinco casos de uso por par de línguas:**

| # | Caso de uso | Modelos |
|---|---|---|
| 1 | Texto indígena → texto na língua oficial | MT |
| 2 | Texto na língua oficial → texto indígena | MT |
| 3 | Voz indígena → voz na língua oficial | ASR → MT → TTS |
| 4 | Voz na língua oficial → voz indígena | ASR → MT → TTS |
| 5 | Voz indígena → texto indígena (voz para texto) | ASR |

**O primeiro par é shawi ↔ espanhol** (`cbt_Latn`, glottocode `chay1248`; Peru). Ele vem primeiro porque o
trabalho tinha começado ali, pela saúde materna ([`PROBLEM.md` §6](PROBLEM.md#6-o-primeiro-caso-shawi--espanhol-peru)),
e não porque algo seja específico dele. O que existe para ele:

* 11,977 trechos (chunks) primários em espanhol (sintéticos, a partir da matriz de design em
  `primary/spa_Latn/matrix.yaml`).
* 3,578 traduções humanas para o shawi de 3,575 desses trechos, trabalho encomendado, em três contribuições.
* Os mesmos 11,977 trechos em inglês, traduzidos automaticamente do espanhol com os mesmos ids de trecho, de
  modo que toda tradução para o shawi também forma um par com o inglês.
* Nenhuma gravação em shawi. O caminho do áudio (validador, build, pipelines de ASR/TTS) é testado com dados
  sintéticos de teste rotulados como tais (`qaa_Latn`), e o `NEEDS.md` pede gravações.

| Dentro do escopo | Fora do escopo |
|---|---|
| Qualquer língua com forma escrita; o formato aceita todas as escritas ISO 15924 (por enquanto, só a escrita latina foi testada) | Línguas só faladas (o formato armazena áudio não transcrito; nenhum pipeline o usa ainda) |
| Línguas oficiais como corpus primário: espanhol (gerado) e inglês (traduzido automaticamente a partir dele); outras (português, francês, híndi, tailandês, …) pelo mesmo mecanismo | Pesquisa dialetal: as variedades são um rótulo numa contribuição |
| Traduções e gravações humanas; texto escrito por máquina só do lado da língua oficial, e rotulado | Tradução automática apresentada como trabalho humano |
| Uma língua entra quando uma comunidade traz dados e uma pessoa responsável pela língua (steward) | Um serviço de inferência em produção; a demo é uma demo |

## 2. Princípios

1. **A contribuição é a unidade.** Os dados são registrados como pastas de contribuição, cada uma com a sua
   própria proveniência, licença e consentimento. O agrupamento acontece só nos builds e nas receitas, nunca
   movendo arquivos.
2. **IDs estáveis, nunca posições.** Os ids de trecho são hexadecimais de 32 dígitos e nunca são reutilizados
   (os tradutores trabalham com esses mesmos ids). Os arquivos podem ser divididos ou ordenados sem quebrar
   nenhuma referência.
3. **Uma contribuição depois do merge é imutável.** Uma correção é uma nova contribuição que diz o que ela
   substitui.
4. **Pessoas traduzem e falam; as máquinas só podem fazer o rascunho do lado da língua oficial, e devem
   dizê-lo.** Todo trecho sintético nomeia o modelo que o escreveu (`gen_model`, `provider`, `prompt_version`).
5. **Consentimento e retirada são dados.** Toda contribuição carrega uma licença e uma referência de
   consentimento; uma retirada é uma linha de CSV que o próximo build aplica.
6. **Códigos padrão, nomes simples, builds reproduzíveis.** As línguas são identificadas pelo código ISO 639-3
   mais a escrita (`cbt_Latn`), a tag de modelo da Meta. A mesma tag de build produz o mesmo hash de conteúdo
   em qualquer sistema operacional.
7. **Os dados da comunidade nunca saem do nosso hardware para um modelo que possa treinar com eles.** Todo
   modelo declara uma `data_policy`; o código se recusa a enviar texto em língua indígena a um modelo
   hospedado do nível Contributor.
8. **As APIs pagas são opcionais e pagas por quem as usa.** A CLI usa a sua própria chave; a demo pede a chave
   de cada visitante e, sem ela, roda só os modelos abertos com ajuste fino.

**Uma consequência.** A partição (split) é uma propriedade do trecho primário, compartilhada por todas as
línguas, e é atribuída por **grupo de paráfrases** (as ~10 paráfrases próximas que um pedido de geração
produziu), de modo que nenhum modelo possa ver no treinamento uma paráfrase de uma frase de teste.

## 3. Modelo de dados

| Entidade | Chave | Precisa ter |
|---|---|---|
| Trecho primário | `chunk_id` (32-hex) | texto, partição, origem, status; cada coluna da matriz de design que o gerador registrou |
| Língua | `<iso639-3>_<Script>` | glottocode, nome de exibição, pessoa responsável (steward), autoridade comunitária, apóstrofo canônico |
| Contribuição | `<YYYY-MM>_<org>_<nnnn>` | contribuidor (pseudônimo), licença, consentimento, proveniência, datas de coleta, variedade |
| Linha de par | (contribuição, chunk_id) | texto, translator_id (pseudônimo); `replaces` opcional |
| Linha de áudio | (contribuição, arquivo) | falante, estilo; chunk_id ou transcrição |
| Falante | (contribuição, speaker_id) | faixa etária, referência de consentimento |
| Build | `data-YYYY.MM[-rN]` | uma tabela por tarefa e por língua, manifesto com hashes de arquivo e de conteúdo |
| Receita | arquivo | build, língua, modelo de base, método, hiperparâmetros |
| Ficha do modelo | `name@vX.Y` | build, receita, licença do modelo de base, pontuações de validação comparadas ao piso de recuperação, teste avaliado uma única vez |

Linhas de áudio: `chunk_id` preenchido e `transcript` vazio significa que a pessoa leu a tradução do trecho
feita nessa contribuição; `chunk_id` vazio com `transcript` preenchido é fala espontânea (a partição é feita
por falante); com os dois vazios, o áudio é armazenado e não é usado. Os vocabulários fechados estão em
`schemas/`; o validador rejeita qualquer outro valor.

## 4. Corpus primário

O corpus primário é o conjunto de frases na língua oficial que todas as línguas traduzem. Hoje ele está em
espanhol (`primary/spa_Latn/`).

**O que temos.** O primeiro lote, `2026-06_opus48_0001.csv`: 10,000 trechos gerados em junho de 2026 com o
Claude Opus 4.8, cobrindo 4 dos 15 domínios da matriz e 37 microcenários. Cada linha mantém a sua célula da
matriz (domínio, microcenário, registro, ato comunicativo, tempo verbal, polaridade, pessoa, faixa de
comprimento, perfil do falante, tom, discurso conectado, palavras-âncora, `source_custom_id`).

**Gerar mais, com modelos da Meta.** `uyari generate` mantém a matriz desse lote, o seu rodízio (round-robin)
entre tempo verbal/polaridade/pessoa, as palavras-âncora, o plano em disco com status por unidade e
reexecuções idempotentes, a chave de grupo `custom_id`, o parsing, a validação e a deduplicação, e **o prompt
idêntico** (uma única `prompt_version` fixada), para que uma comparação meça modelos, e não edições de prompt.
Regenerar 200 células com o Muse Spark 1.3 Contributor custou 3.3% do custo original por 1,000 trechos, com
100% de respostas bem formadas e um texto um pouco mais variado (`reports/gen-comparison.md`); o Muse Glimmer
na nossa própria GPU faz isso sem custo de API. Antes de enviar, `--estimate` mostra o custo; cada execução
tem um teto; toda chamada fica no registro (ledger).

**Pós-processamento.** NFC e espaços em branco; 1–120 palavras e a faixa de comprimento da unidade ±30%;
termos urbanos proibidos; uma verificação de língua; deduplicação exata e de quase-duplicatas por embeddings
(cosseno 0.92, com blocagem por domínio) contra todo o corpus primário; uma leitura humana por amostragem de
2% de cada lote (`uyari primary sample`); um lote com mais de 5% de rejeições é retirado.

**Partições.** Primeira atribuição: validação e teste têm ~300 trechos traduzidos cada, como grupos de
paráfrases inteiros tirados dos grupos traduzidos, estratificados por domínio e ordenados por hash. Grupos
novos: um grupo que regenera uma célula existente herda a partição dela; os demais, por hash (5% / 5%). As
partições ficam congeladas depois de escritas.

**Outros corpora primários.** O inglês (`primary/eng_Latn`) compartilha os ids de trecho com o espanhol:
`uyari primary translate` traduziu automaticamente todos os 11,977 trechos com o Muse Spark 1.3 Contributor
por US$ 0.19, rotulados como `origin=machine_translated`, com a partição, o domínio e o grupo de paráfrases
copiados. As outras línguas oficiais são adicionadas da mesma forma.

## 5. Adicionar uma língua

Uma pasta `languages/<iso639-3>_<Script>/` com `language.yaml` e `README.md`. O validador a aceita quando todo
código se resolve em `registry/` (o intervalo de uso local `qaa`–`qtz` da ISO 639-3 é aceito) e há uma pessoa
responsável (steward) designada. Campos:
`id, iso639_3, script, glottocode, display_name, iso_name, primary, steward, community_authority, apostrophe,
apostrophe_variants, training_orthography, trainer`. As letras que as ferramentas costumam estragar são
declaradas uma única vez: em shawi, a oclusiva glotal é uma letra, com forma canônica `ʼ` (U+02BC), e o
validador lista os caracteres variantes junto com a correção.

## 6. Contribuir

Veja [`contributing/`](../../contributing/) (inglês, espanhol, português, francês, alemão, italiano, híndi,
tailandês). Uma pasta, um pull request, uma língua, uma variedade, uma licença, uma referência de
consentimento: `contribution.yaml`, `pairs.csv`, `audio.csv`, `speakers.csv`, `wav/`. Contribuições parciais
são normais; o build deduz o que uma pasta contém a partir dos arquivos que existem nela.

## 7. Revisão

Três filtros: o **validador** (CI, a cada PR), o **Gatekeeper** (Muse Glimmer na nossa própria GPU; uma
revisão escrita na língua de trabalho da pessoa responsável, espanhol no caso do shawi) e a **pessoa
responsável pela língua (steward)** (alguém que fala a língua). O Gatekeeper detecta falhas do validador,
texto na língua oficial colado na coluna da língua indígena, linhas copiadas de contribuições aceitas e texto
diferente dos pares aceitos; ele recomenda merge, devolução ou escalonamento (os domínios de saúde e de
consentimento sempre são escalonados). Ele **não** detecta tradução automática; quem contribui declara que
nenhuma saída de máquina é enviada como trabalho humano.

## 8. Builds

`uyari build --tag data-YYYY.MM` lê todas as contribuições, aplica `replaces`, ignora as contribuições
revogadas e as retiradas que vigoram em `--as-of` ou antes, normaliza o texto, junta a partição e o domínio e
escreve `builds/<tag>/<lang>/{mt,asr,tts}.parquet` (treino + validação) e `*.test.parquet` (teste), além de
`MANIFEST.json`: commit do git, contribuições incluídas e excluídas com os motivos, linhas excluídas com os
motivos, linhas por partição, licenças e, por tabela, um `sha256` do arquivo e um `content_sha256` canônico.
Os dados ausentes são deduzidos, nunca declarados. O Parquet não fica no git; a tag o reconstrói.

## 9. Agentes

| Agente | Gatilho | Decide | Escreve |
|---|---|---|---|
| **Gatekeeper** | Um PR para `contributions/` | merge / devolver / escalar (só recomendação) | Uma revisão no PR, um rascunho de `review.yaml` |
| **Trainer** | Um merge em `main` (runner de GPU auto-hospedado) ou manualmente | Se vale a pena gerar um build (língua nova ou ≥10% mais pares); promove só se todas as direções superarem o piso de recuperação **e**, nas direções que os dois compartilham, o chrF++ de validação melhorar ≥0.5 em relação ao modelo em uso, repontuado no mesmo build (ou se o candidato adicionar direções e não perder mais de 0.5) | Manifesto do build, ficha do modelo, `scores.json`, `models/registry.yaml`, `NEEDS.md`, um pull request |
| Interpreter | (depois do MVP) | | |

Salvaguardas: nenhum agente faz merge; nenhum agente lê a partição de teste antes de uma promoção; o teste é
avaliado uma vez por versão de modelo; toda decisão é uma linha no PR ou na ficha, com os números que a
produziram.

## 10. Treinamento e avaliação

As receitas em `recipes/` são a única configuração. Um modelo por backend cobre cada língua oficial
emparelhada com a indígena (hoje espanhol e inglês: quatro direções), e cada direção é pontuada no seu próprio
par de línguas. Modelos de referência para texto:

* **Muse Glimmer 30B, QLoRA** (Unsloth, 4-bit, r=16, comprimento máximo 512, batch 1 × 16, 3 épocas): o
  modelo principal, na nossa RTX 4090.
* **NLLB-200 1.3B, ajuste fino completo** (um novo token de língua inicializado a partir de uma língua
  aparentada; `quy_Latn` para o shawi): a linha de base rápida; também treina numa RTX 3060 de 12 GB em bf16
  puro.
* **Piso de recuperação:** a tradução humana da frase de treinamento mais próxima; local, gratuito.

A demo serve só estes modelos com ajuste fino: o Glimmer por padrão, depois de treinado, e o NLLB como modo
rápido; as fichas dizem qual pontua mais alto.

| Tarefa | Pontuação | Verificação humana |
|---|---|---|
| Texto para texto | chrF++ por direção (BLEU informado, não otimizado) | Dois falantes nativos avaliam 100 frases, quando houver |
| Voz para texto | CER (WER informado) | Aceitabilidade da transcrição em 50 clipes |
| Texto para voz | CER de ida e volta via ASR | Naturalidade 1–5 |
| Voz para voz | chrF++ da saída após ASR | Sucesso da tarefa num diálogo roteirizado |

O COMET e outras métricas aprendidas não são considerados confiáveis na tradução para línguas indígenas
enquanto não forem validados contra julgamentos humanos.

## 11. Governança

Código: Apache 2.0. Dados: por contribuição (padrão CC BY 4.0; CC BY-SA, CC BY-NC ou uma licença comunitária,
por escolha da comunidade), levada em cada linha do build. O consentimento é coletivo (autoridade
comunitária) e individual (cada falante e tradutor); as retiradas são linhas em `contributing/takedowns.csv`.
Papéis, licenças, modelos de termo de consentimento e proteções, em oito línguas:
[`contributing/<language>/governance.md`](../../contributing/pt/governance.md).

## 12. Dinheiro

* **Local por padrão.** O treinamento, a avaliação, o Gatekeeper e a demo rodam nas nossas próprias GPUs, sem
  custo de API.
* **Traga a sua própria chave.** Tudo o que chama uma API paga usa a chave da Meta de quem faz a chamada: a
  CLI lê `META_API_KEY`; a demo pede a chave de cada visitante, usa-a só naquela requisição, nunca a armazena
  e nunca recorre à chave do servidor.
* **Estimar antes de gastar.** Os preços ficam em `config/llm.yaml`; todo comando de LLM estima o seu custo
  antes de enviar (aproximação com tiktoken × 1.2), o uso real de cada chamada fica em `.uyari/ledger.jsonl`, e
  cada execução tem um limite rígido (`generate` $1, `transcribe` $2, todo o resto $0 porque roda localmente).
  O orçamento de desenvolvimento do próprio projeto para APIs hospedadas é de USD 150.
