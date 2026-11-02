# Como contribuir com o Uyari

[English](../en/README.md) · [Español](../es/README.md) · [Português](../pt/README.md) · [Français](../fr/README.md) · [Deutsch](../de/README.md) · [Italiano](../it/README.md) · [हिन्दी](../hi/README.md) · [ไทย](../th/README.md)

O Uyari reúne traduções e gravações **feitas por pessoas** para que as línguas indígenas e outras línguas
pouco atendidas tenham ferramentas abertas de tradução, em texto e em voz, de e para a língua oficial de que
os seus falantes precisam no atendimento de saúde, na escola e diante do governo. Qualquer língua pode
participar. Cada contribuição é uma pasta; não é preciso programar.

Antes de contribuir, leia as regras sobre direitos, consentimento e retirada: [governance.md](governance.md).

## O que é necessário agora

Cada língua tem um `NEEDS.md` que o sistema mantém atualizado. O shawi (Peru) é a primeira língua; a sua
lista é [`languages/cbt_Latn/NEEDS.md`](../../languages/cbt_Latn/NEEDS.md). Hoje ela pede:

1. **Gravações lidas** de traduções já existentes, feitas por pelo menos 3 pessoas adultas, com o seu
   consentimento.
2. **Mais frases de saúde e de registro civil** traduzidas para o shawi, revisadas por um segundo leitor nativo.

**Para adicionar uma nova língua**, abra uma issue com o nome dela, o seu código ISO 639-3, a língua oficial
de que os seus falantes precisam e quem poderia ser a pessoa responsável por ela (steward: alguém que fala a
língua e revisa as contribuições).

## Uma contribuição = uma pasta = um pull request

```
languages/<language>/contributions/<YYYY-MM>_<organization>_<nnnn>/
  contribution.yaml   who (pseudonym), when, how it was made, license, consent
  pairs.csv           chunk_id, text, replaces, translator_id, notes      (text)
  audio.csv           file, chunk_id, transcript, speaker_id, style, device, notes   (audio)
  speakers.csv        speaker_id, age_band, sex, first_language, consent_ref        (audio)
  wav/                16 or 48 kHz, mono, 16-bit, 1 to 20 seconds, one person per clip
```

* Uma pasta tem **uma** língua, **uma** variedade, **uma** licença e **uma** referência de consentimento.
* Traduza a partir das frases na língua oficial que estão em `primary/` (hoje: espanhol,
  `primary/spa_Latn/chunks/`). Cada linha de `pairs.csv` aponta para um `chunk_id`. Traduza a frase inteira.
* Escreva as letras da língua como indica o seu `language.yaml`. Em shawi, por exemplo, a oclusiva glotal é
  **ʼ** (U+02BC); `uyari validate` mostra onde `'`, `’` ou `´` devem ser convertidos.
* **Nada de tradução automática nem vozes sintéticas apresentadas como trabalho humano.** Se uma pessoa
  corrigiu uma saída automática, declare isso em `contribution.yaml` (`human_post_edited_from_mt`).
* Somente pessoas adultas. Nada de nomes reais nos arquivos: use `t-0001`, `s-0001`. A organização que
  contribui guarda a sua própria lista.
* Uma contribuição aceita nunca é editada: uma correção é uma nova linha numa contribuição posterior com
  `replaces=<contribution>/<chunk_id>`.

## O que acontece com o seu pull request

1. **Validador** (automático): formato, códigos, ids, apóstrofos, áudio.
2. **Gatekeeper** (automático, Muse Glimmer na GPU do próprio projeto): verifica se as linhas parecem estar na
   língua oficial em vez da língua indígena, ou se foram copiadas, e escreve uma revisão linha por linha no
   pull request.
3. **A pessoa responsável pela língua (steward)** lê a revisão, confere algumas linhas por amostragem e
   decide. Conteúdo de saúde e de consentimento informado sempre precisa de um segundo leitor nativo.

Depois do merge, o **Trainer** reconstrói os dados, treina, mede e abre um pull request com os resultados.

## Retirar dados

A pessoa responsável ou a autoridade comunitária pode pedir que uma contribuição saia de todo treinamento
futuro: é uma linha em [`contributing/takedowns.csv`](../takedowns.csv). Modelos já publicados não podem ser
recuperados de quem já os baixou; as suas fichas são corrigidas e o próximo treinamento já não usa esses
dados. Detalhes: [governance.md](governance.md#retirada-de-dados).

## Contribuir com código

```bash
uv sync --python 3.11 --extra dev --extra speech
uv run pytest -q
uv run ruff check src tests
git config core.hooksPath .githooks     # privacy check before every commit
```

O trabalho com GPU roda no Ubuntu: [`docs/RUNBOOK-4090.md`](../../docs/RUNBOOK-4090.md). Todo comando que
chama uma API paga tem `--estimate` e usa a sua própria chave (`META_API_KEY`), e dados em línguas indígenas
nunca vão para um modelo hospedado (`data_policy` em `config/llm.yaml`).
