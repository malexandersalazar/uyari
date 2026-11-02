# Governança: direitos, consentimento e retirada

[English](../en/governance.md) · [Español](../es/governance.md) · [Português](../pt/governance.md) · [Français](../fr/governance.md) · [Deutsch](../de/governance.md) · [Italiano](../it/governance.md) · [हिन्दी](../hi/governance.md) · [ไทย](../th/governance.md)

O Uyari guarda as palavras e as vozes das pessoas. Estas regras valem para todas as línguas e todas as
contribuições. Elas seguem o consentimento livre, prévio e informado (Declaração das Nações Unidas sobre os
Direitos dos Povos Indígenas; Convenção 169 da OIT), os princípios CARE para a governança de dados indígenas
e a legislação nacional de cada país onde os dados são coletados.

## Quem decide

| Papel | Decide |
|---|---|
| **Mantenedor** (quem lidera o projeto) | Estrutura, esquemas, validador, builds, a metodologia |
| **Pessoa responsável pela língua (steward)** (uma por língua, alguém que fala a língua) | Tudo dentro dessa língua: aceita contribuições, designa revisores, registra retiradas |
| **Autoridade comunitária** (nomeada em `language.yaml`) | O consentimento em nome da comunidade; pode pedir uma retirada a qualquer momento |
| **Contribuidor** (uma pessoa ou uma organização) | Produz contribuições e escolhe, junto com a comunidade, a licença delas |

Nenhum agente decide: o Gatekeeper e o Trainer só recomendam, e é uma pessoa que faz o merge.

## Licenças

Cada contribuição indica a sua licença em `contribution.yaml`, e todo build a leva em cada linha, para que
qualquer pessoa que use os dados possa filtrar por licença.

* Padrão: **CC BY 4.0**. Uma comunidade pode escolher CC BY-SA 4.0, CC BY-NC 4.0, CC0 ou a sua própria
  licença comunitária.
* A pessoa responsável explica os prós e contras antes de a comunidade escolher: uma licença não comercial
  impede que uma empresa implante o tradutor para um ministério ou uma clínica, o que muitas vezes é a
  principal forma de ele chegar às pessoas.
* O código é Apache 2.0. Os pesos dos modelos também herdam a licença do seu modelo de base.

## Consentimento

O consentimento é **coletivo** (a autoridade comunitária concorda com a finalidade e com a licença) e
**individual** (cada tradutor e falante adulto concorda por si). Os modelos de termo estão nesta pasta, com os
mesmos nomes de arquivo em todas as línguas:

| Modelo de termo | Quem concorda | Indicado em |
|---|---|---|
| [`consent-collective.md`](consent-collective.md) | A autoridade comunitária | `contribution.yaml` → `consent.template` |
| [`consent-individual.md`](consent-individual.md) | Cada tradutor e falante | `speakers.csv` → `consent_ref` |
| [`commissioned-work.md`](commissioned-work.md) | Quem encomendou e pagou o trabalho, como titular dos direitos | `contribution.yaml` → `consent.template` |

O `contribution.yaml` indica o modelo de termo só pelo nome do arquivo (por exemplo `consent-collective.md`),
para que a mesma referência valha em todas as línguas. As cópias assinadas ficam com a organização que
contribui; o repositório guarda só o nome do modelo e a autoridade, nunca uma assinatura ou um nome real.

## Trabalho encomendado

Quando traduções ou gravações são encomendadas e pagas, quem pagou detém os direitos e escolhe a licença;
registra-se `compensated: yes`, nunca um valor. As pessoas que fizeram o trabalho não são identificadas no
repositório. A gravação da voz de alguém sempre precisa também do consentimento individual dessa pessoa,
independentemente de quem tenha pago por ela.

## Retirada de dados

Uma pessoa responsável pela língua ou uma autoridade comunitária pode pedir que uma contribuição saia de todo
treinamento futuro. A retirada é uma linha em [`contributing/takedowns.csv`](../takedowns.csv):

| Coluna | Significado |
|---|---|
| `contribution` | O id da contribuição |
| `requested_by_role` | `steward`, `community_authority`, `contributor` ou `maintainer` (um papel, nunca um nome) |
| `request_date`, `effective_date` | Quando foi pedida e a partir de quando os builds a excluem |
| `scope` | `contribution`, `text` ou `audio` |
| `note` | Opcional, sem dados pessoais |

`uyari build` exclui a contribuição de todo build cuja data seja igual ou posterior a `effective_date`. Modelos
já publicados não podem ser recuperados de quem já os baixou; as suas fichas são corrigidas e o próximo
treinamento já não usa esses dados.

## Proteção

* Somente pessoas adultas. Ids pseudônimos (`t-0001`, `s-0001`); os nomes reais ficam com a organização que
  contribui.
* Nenhuma gravação de terceiros identificáveis. As frases de saúde descrevem situações, nunca pacientes reais.
* Os povos em isolamento voluntário estão excluídos.
* Os dados em línguas indígenas nunca são enviados a um modelo hospedado que possa treinar com eles: todo
  modelo em `config/llm.yaml` declara o que pode ver, e o código recusa qualquer outro envio.
* Uso aceitável: acesso a serviços, educação e revitalização linguística. Usar os dados ou os modelos para
  vigiar, tomar como alvo ou traçar o perfil de falantes viola a licença onde a licença permite essa condição,
  e quebra a confiança onde não permite.
