# Come contribuire a Uyari

[English](../en/README.md) · [Español](../es/README.md) · [Português](../pt/README.md) · [Français](../fr/README.md) · [Deutsch](../de/README.md) · [Italiano](../it/README.md) · [हिन्दी](../hi/README.md) · [ไทย](../th/README.md)

Uyari raccoglie traduzioni e registrazioni **fatte da persone** perché le lingue indigene e altre lingue poco
supportate abbiano strumenti di traduzione aperti, nel testo e nella voce, verso e dalla lingua ufficiale di cui
i loro parlanti hanno bisogno per la sanità, la scuola e la pubblica amministrazione. Qualsiasi lingua può
partecipare. Ogni contributo è una cartella; non serve saper programmare.

Prima di contribuire, leggi le regole su diritti, consenso e ritiro: [governance.md](governance.md).

## Che cosa serve adesso

Ogni lingua ha un `NEEDS.md` che il sistema mantiene aggiornato. Lo shawi (Perù) è la prima lingua; il suo
elenco è [`languages/cbt_Latn/NEEDS.md`](../../languages/cbt_Latn/NEEDS.md). Oggi chiede:

1. **Registrazioni lette** di traduzioni già esistenti, da almeno 3 persone adulte, con il loro consenso.
2. **Più frasi di sanità e di stato civile** tradotte in shawi, controllate da un secondo lettore madrelingua.

**Per aggiungere una nuova lingua**, apri una issue con il suo nome, il suo codice ISO 639-3, la lingua
ufficiale di cui hanno bisogno i suoi parlanti e chi potrebbe esserne la persona responsabile (steward:
qualcuno che la parla e rivede i contributi).

## Un contributo = una cartella = una pull request

```
languages/<language>/contributions/<YYYY-MM>_<organization>_<nnnn>/
  contribution.yaml   who (pseudonym), when, how it was made, license, consent
  pairs.csv           chunk_id, text, replaces, translator_id, notes      (text)
  audio.csv           file, chunk_id, transcript, speaker_id, style, device, notes   (audio)
  speakers.csv        speaker_id, age_band, sex, first_language, consent_ref        (audio)
  wav/                16 or 48 kHz, mono, 16-bit, 1 to 20 seconds, one person per clip
```

* Una cartella ha **una** lingua, **una** varietà, **una** licenza e **un** riferimento di consenso.
* Si traduce dalle frasi in lingua ufficiale in `primary/` (oggi: spagnolo, `primary/spa_Latn/chunks/`). Ogni
  riga di `pairs.csv` rimanda a un `chunk_id`. Si traduce la frase intera.
* Le lettere della lingua si scrivono come indica il suo `language.yaml`. In shawi, per esempio, l'occlusiva
  glottidale è **ʼ** (U+02BC); `uyari validate` mostra dove `'`, `’` o `´` vanno convertiti.
* **Niente traduzione automatica né voci sintetiche presentate come lavoro umano.** Se una persona ha corretto
  un'uscita automatica, va dichiarato in `contribution.yaml` (`human_post_edited_from_mt`).
* Solo persone adulte. Niente nomi reali nei file: si usano `t-0001`, `s-0001`. L'organizzazione che
  contribuisce conserva il proprio elenco.
* Un contributo accettato non si modifica mai: una correzione è una nuova riga in un contributo successivo con
  `replaces=<contribution>/<chunk_id>`.

## Che cosa succede alla tua pull request

1. **Validatore** (automatico): formato, codici, id, apostrofi, audio.
2. **Gatekeeper** (automatico, Muse Glimmer sulla GPU del progetto): controlla se alcune righe sembrano scritte
   nella lingua ufficiale invece che in quella indigena, o sono state copiate, e scrive una revisione riga per
   riga nella pull request.
3. **La persona responsabile della lingua (steward)** legge la revisione, controlla alcune righe a campione e
   decide. I contenuti di sanità e di consenso informato richiedono sempre un secondo lettore madrelingua.

Dopo il merge, il **Trainer** ricostruisce i dati, addestra, misura e apre una pull request con i risultati.

## Ritirare dati

La persona responsabile o l'autorità comunitaria può chiedere che un contributo esca da ogni addestramento
futuro: è una riga in [`contributing/takedowns.csv`](../takedowns.csv). I modelli già pubblicati non possono
essere recuperati da chi li ha scaricati; le loro schede vengono corrette e l'addestramento successivo non usa
più quei dati. Dettagli: [governance.md](governance.md#ritiro).

## Contribuire al codice

```bash
uv sync --python 3.11 --extra dev --extra speech
uv run pytest -q
uv run ruff check src tests
git config core.hooksPath .githooks     # privacy check before every commit
```

Il lavoro su GPU si fa su Ubuntu: [`docs/RUNBOOK-4090.md`](../../docs/RUNBOOK-4090.md). Ogni comando che chiama
un'API a pagamento ha `--estimate` e usa la tua chiave (`META_API_KEY`), e i dati in lingua indigena non vanno
mai a un modello ospitato da terzi (`data_policy` in `config/llm.yaml`).
