# Zu Uyari beitragen

[English](../en/README.md) · [Español](../es/README.md) · [Português](../pt/README.md) · [Français](../fr/README.md) · [Deutsch](../de/README.md) · [Italiano](../it/README.md) · [हिन्दी](../hi/README.md) · [ไทย](../th/README.md)

Uyari sammelt Übersetzungen und Aufnahmen, **die von Menschen gemacht wurden**, damit indigene und andere
unterversorgte Sprachen offene Übersetzungswerkzeuge erhalten, in Text und gesprochener Sprache, von und in die
Amtssprache, die ihre Sprechenden für Gesundheitsversorgung, Schule und Behörden brauchen. Jede Sprache kann
dazukommen. Jeder Beitrag ist ein Ordner; Programmierkenntnisse sind nicht nötig.

Lesen Sie vor dem Beitragen die Regeln zu Rechten, Einwilligung und Rückzug: [governance.md](governance.md).

## Was jetzt gebraucht wird

Jede Sprache hat eine `NEEDS.md`, die das System aktuell hält. Shawi (Peru) ist die erste Sprache; ihre Liste
ist [`languages/cbt_Latn/NEEDS.md`](../../languages/cbt_Latn/NEEDS.md). Derzeit werden gebraucht:

1. **Vorgelesene Aufnahmen** vorhandener Übersetzungen von mindestens 3 Erwachsenen, mit deren Einwilligung.
2. **Mehr Sätze aus Gesundheitswesen und Standesamt**, ins Shawi übersetzt und von einer zweiten
   muttersprachlichen Person geprüft.

**Um eine neue Sprache hinzuzufügen**, eröffnen Sie ein Issue mit ihrem Namen, ihrem ISO-639-3-Code, der
Amtssprache, die ihre Sprechenden brauchen, und der Angabe, wer als verantwortliche Person (Steward) infrage käme
(eine Person, die die Sprache spricht und Beiträge prüft).

## Ein Beitrag = ein Ordner = ein Pull Request

```
languages/<language>/contributions/<YYYY-MM>_<organization>_<nnnn>/
  contribution.yaml   who (pseudonym), when, how it was made, license, consent
  pairs.csv           chunk_id, text, replaces, translator_id, notes      (text)
  audio.csv           file, chunk_id, transcript, speaker_id, style, device, notes   (audio)
  speakers.csv        speaker_id, age_band, sex, first_language, consent_ref        (audio)
  wav/                16 or 48 kHz, mono, 16-bit, 1 to 20 seconds, one person per clip
```

* Ein Ordner hat **eine** Sprache, **eine** Varietät, **eine** Lizenz und **einen** Einwilligungsverweis.
* Übersetzt wird aus den Sätzen in der Amtssprache in `primary/` (derzeit: Spanisch,
  `primary/spa_Latn/chunks/`). Jede Zeile in `pairs.csv` verweist auf eine `chunk_id`. Übersetzt wird der ganze
  Satz.
* Die Buchstaben der Sprache werden so geschrieben, wie es ihre `language.yaml` vorgibt. Im Shawi zum Beispiel
  ist der Knacklaut **ʼ** (U+02BC); `uyari validate` zeigt, wo `'`, `’` oder `´` umgewandelt werden müssen.
* **Keine maschinelle Übersetzung und keine synthetischen Stimmen als menschliche Arbeit ausgeben.** Hat eine
  Person maschinelle Ausgaben korrigiert, wird das in `contribution.yaml` angegeben
  (`human_post_edited_from_mt`).
* Nur Erwachsene. Keine echten Namen in den Dateien: Verwenden Sie `t-0001`, `s-0001`. Die beitragende
  Organisation führt ihre eigene Liste.
* Ein angenommener Beitrag wird nie geändert: Eine Korrektur ist eine neue Zeile in einem späteren Beitrag mit
  `replaces=<contribution>/<chunk_id>`.

## Was mit Ihrem Pull Request passiert

1. **Validator** (automatisch): Format, Codes, IDs, Apostrophe, Audio.
2. **Gatekeeper** (automatisch, Muse Glimmer auf der projekteigenen GPU): prüft, ob Zeilen nach der Amtssprache
   statt nach der indigenen Sprache aussehen oder kopiert wurden, und schreibt eine zeilenweise Bewertung in den
   Pull Request.
3. **Die für die Sprache verantwortliche Person (Steward)** liest die Bewertung, prüft Stichproben und
   entscheidet. Inhalte zu Gesundheit und informierter Einwilligung brauchen immer eine zweite
   muttersprachliche Prüfung.

Nach dem Merge baut der **Trainer** die Daten neu, trainiert, misst und öffnet einen Pull Request mit den
Ergebnissen.

## Daten zurückziehen

Die verantwortliche Person oder die Gemeinschaftsvertretung kann verlangen, dass ein Beitrag aus jedem künftigen
Training entfernt wird: Das ist eine Zeile in [`contributing/takedowns.csv`](../takedowns.csv). Bereits
veröffentlichte Modelle können von denen, die sie heruntergeladen haben, nicht zurückgeholt werden; ihre
Modellkarten werden korrigiert, und das nächste Training verwendet diese Daten nicht mehr. Details:
[governance.md](governance.md#daten-zurückziehen).

## Code beitragen

```bash
uv sync --python 3.11 --extra dev --extra speech
uv run pytest -q
uv run ruff check src tests
git config core.hooksPath .githooks     # privacy check before every commit
```

GPU-Arbeit läuft unter Ubuntu: [`docs/RUNBOOK-4090.md`](../../docs/RUNBOOK-4090.md). Jeder Befehl, der eine
kostenpflichtige API aufruft, hat `--estimate` und verwendet Ihren eigenen Schlüssel (`META_API_KEY`), und Daten
in indigenen Sprachen gehen nie an ein gehostetes Modell (`data_policy` in `config/llm.yaml`).
