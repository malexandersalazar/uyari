# Uyari-Methodik

[English](../../METHODOLOGY.md) · [Español](../es/METHODOLOGY.md) · [Português](../pt/METHODOLOGY.md) · [Français](../fr/METHODOLOGY.md) · **Deutsch** · [Italiano](../it/METHODOLOGY.md) · [हिन्दी](../hi/METHODOLOGY.md) · [ไทย](../th/METHODOLOGY.md)

Uyari ist eine offene Datenstruktur und ein Trainings-Toolkit, das die eigenen Übersetzungen und Aufnahmen einer
Gemeinschaft in Modelle verwandelt, zwischen einer indigenen oder anderen unterversorgten Sprache und der
Amtssprache, die ihre Sprechenden brauchen. Eine Sprache wird als Ordner hinzugefügt; Daten werden als Ordner
darin hinzugefügt; niemand ändert Code. Standardmäßig werden Metas Modelle verwendet.

Die Gründe für strukturelle Entscheidungen stehen in [`docs/decisions/`](../../docs/decisions/). Das Problem, das
Uyari angeht, mit Zahlen und Quellen, steht in [`PROBLEM.md`](PROBLEM.md).

## 1. Ziel und Umfang

**Fünf Anwendungsfälle pro Sprachpaar:**

| # | Anwendungsfall | Modelle |
|---|---|---|
| 1 | Indigener Text → Text in der Amtssprache | MT |
| 2 | Text in der Amtssprache → indigener Text | MT |
| 3 | Gesprochenes in indigener Sprache → Gesprochenes in der Amtssprache | ASR → MT → TTS |
| 4 | Gesprochenes in der Amtssprache → Gesprochenes in indigener Sprache | ASR → MT → TTS |
| 5 | Gesprochenes in indigener Sprache → indigener Text (Sprache-zu-Text) | ASR |

**Das erste Paar ist Shawi ↔ Spanisch** (`cbt_Latn`, Glottocode `chay1248`; Peru). Es ist das erste, weil die
Arbeit dort begonnen hatte, mit Müttergesundheit ([`PROBLEM.md` §6](PROBLEM.md#6-der-erste-fall-shawi--spanisch-peru)),
nicht weil irgendetwas daran spezifisch wäre. Was es dafür gibt:

* 11,977 spanische Primär-Chunks (synthetisch, aus der Designmatrix in `primary/spa_Latn/matrix.yaml`).
* 3,578 menschliche Shawi-Übersetzungen von 3,575 davon, als Auftragsarbeit, in drei Beiträgen.
* Dieselben 11,977 Chunks auf Englisch, maschinell aus dem Spanischen übersetzt, mit denselben Chunk-IDs, sodass
  jede Shawi-Übersetzung auch ein Paar mit Englisch bildet.
* Keine Shawi-Aufnahmen. Der Audio-Pfad (Validator, Build, ASR-/TTS-Pipelines) wird an einem gekennzeichneten
  synthetischen Testdatensatz (`qaa_Latn`) erprobt, und `NEEDS.md` bittet um Aufnahmen.

| Im Umfang | Außerhalb des Umfangs |
|---|---|
| Jede Sprache mit Schriftform; das Format akzeptiert jede Schrift nach ISO 15924 (bisher ist nur die lateinische Schrift getestet) | Rein gesprochene Sprachen (das Format speichert nicht transkribiertes Audio; noch keine Pipeline nutzt es) |
| Amtssprachen als Primärsprachen: Spanisch (generiert) und Englisch (daraus maschinell übersetzt); weitere (Portugiesisch, Französisch, Hindi, Thai, …) über denselben Mechanismus | Dialektforschung: Varietäten sind ein Label an einem Beitrag |
| Übersetzungen und Aufnahmen von Menschen; maschinell geschriebener Text nur auf der Seite der Amtssprache, gekennzeichnet | Maschinelle Übersetzung, die als menschliche Arbeit ausgegeben wird |
| Eine Sprache kommt hinzu, wenn eine Gemeinschaft Daten und eine verantwortliche Person (Steward) mitbringt | Ein produktiver Inferenzdienst; die Demo ist eine Demo |

## 2. Grundsätze

1. **Der Beitrag ist die Einheit.** Daten werden als Beitragsordner abgelegt, jeder mit eigener Herkunft, Lizenz
   und Einwilligung. Zusammengeführt wird nur in Builds und Rezepten, nie durch Verschieben von Dateien.
2. **Stabile IDs, nie Positionen.** Chunk-IDs bestehen aus 32 Hex-Zeichen und werden nie wiederverwendet
   (Übersetzende arbeiten mit genau diesen IDs). Dateien können aufgeteilt oder sortiert werden, ohne dass ein
   Verweis bricht.
3. **Gemergte Beiträge sind unveränderlich.** Eine Korrektur ist ein neuer Beitrag, der angibt, was er ersetzt.
4. **Menschen übersetzen und sprechen; Maschinen dürfen nur die Seite der Amtssprache entwerfen und sagen das.**
   Jeder synthetische Chunk nennt das Modell, das ihn geschrieben hat (`gen_model`, `provider`, `prompt_version`).
5. **Einwilligung und Rückzug sind Daten.** Jeder Beitrag trägt eine Lizenz und einen Einwilligungsverweis; ein
   Rückzug ist eine CSV-Zeile, die der nächste Build anwendet.
6. **Standardcodes, einfache Namen, reproduzierbare Builds.** Sprachen werden über ISO 639-3 plus Schrift
   identifiziert (`cbt_Latn`), das Tag, das Metas Modelle verwenden. Derselbe Build-Tag erzeugt auf jedem
   Betriebssystem denselben Inhalts-Hash.
7. **Gemeinschaftsdaten verlassen nie unsere Hardware in Richtung eines Modells, das damit trainieren könnte.**
   Jedes Modell deklariert eine `data_policy`; der Code verweigert die Übergabe von Text in indigenen Sprachen an
   ein gehostetes Modell der Stufe Contributor.
8. **Kostenpflichtige APIs sind optional und werden von denen bezahlt, die sie nutzen.** Die CLI verwendet Ihren
   eigenen Schlüssel; die Demo fragt alle Besuchenden nach ihrem eigenen und führt sonst nur die feinabgestimmten
   offenen Modelle aus.

**Eine Folge.** Der Split ist eine Eigenschaft des Primär-Chunks, gilt für alle Sprachen gleich und wird pro
**Paraphrasengruppe** vergeben (die ~10 Beinahe-Paraphrasen, die eine Generierungsanfrage erzeugt hat), sodass
kein Modell im Training eine Paraphrase eines Testsatzes sehen kann.

## 3. Datenmodell

| Entität | Schlüssel | Muss enthalten |
|---|---|---|
| Primär-Chunk | `chunk_id` (32 Hex-Zeichen) | Text, Split, Herkunft, Status; jede Spalte der Designmatrix, die der Generator erfasst hat |
| Sprache | `<iso639-3>_<Script>` | Glottocode, Anzeigename, verantwortliche Person (Steward), Gemeinschaftsvertretung, kanonischer Apostroph |
| Beitrag | `<YYYY-MM>_<org>_<nnnn>` | Beitragende (pseudonym), Lizenz, Einwilligung, Herkunft, Erhebungszeitraum, Varietät |
| Paarzeile | (contribution, chunk_id) | Text, translator_id (pseudonym); `replaces` optional |
| Audiozeile | (contribution, file) | sprechende Person, Stil; chunk_id oder Transkript |
| Sprechende Person | (contribution, speaker_id) | Altersgruppe, Einwilligungsverweis |
| Build | `data-YYYY.MM[-rN]` | eine Tabelle pro Aufgabe pro Sprache, Manifest mit Datei- und Inhalts-Hashes |
| Rezept | Datei | Build, Sprache, Basismodell, Methode, Hyperparameter |
| Modellkarte | `name@vX.Y` | Build, Rezept, Lizenz des Basismodells, Validierungswerte gegenüber der Retrieval-Untergrenze, Test einmal |

Audiozeilen: Ist `chunk_id` gesetzt und `transcript` leer, hat die sprechende Person die Übersetzung des Chunks
aus demselben Beitrag vorgelesen; ist `chunk_id` leer und `transcript` gesetzt, ist es spontane Rede (Split nach
sprechender Person); sind beide leer, wird die Aufnahme gespeichert, aber nicht verwendet. Geschlossene Vokabulare
stehen in `schemas/`; der Validator lehnt jeden anderen Wert ab.

## 4. Primärkorpus

Das Primärkorpus ist die Menge der Sätze in der Amtssprache, die jede Sprache übersetzt. Derzeit ist es Spanisch
(`primary/spa_Latn/`).

**Was wir haben.** Der erste Batch, `2026-06_opus48_0001.csv`: 10,000 Chunks, im Juni 2026 mit Claude Opus 4.8
generiert, die 4 der 15 Domänen der Matrix und 37 Mikroszenarien abdecken. Jede Zeile behält ihre Matrixzelle
(Domäne, Mikroszenario, Register, kommunikativer Akt, Tempus, Polarität, Person, Längenklasse, Sprecherprofil,
Ton, zusammenhängender Diskurs, Ankerwörter, `source_custom_id`).

**Mehr generieren, mit Meta-Modellen.** `uyari generate` übernimmt von diesem Batch die Matrix, das Round-Robin
über Tempus/Polarität/Person, die Ankerwörter, den Plan auf der Festplatte mit Status pro Einheit und idempotenten
Wiederholungsläufen, den `custom_id`-Gruppenschlüssel, das Parsen, die Validierung und die Deduplizierung sowie
**den identischen Prompt** (eine festgelegte `prompt_version`), sodass ein Vergleich Modelle misst und keine
Prompt-Änderungen. 200 Zellen mit Muse Spark 1.3 Contributor neu zu generieren kostete pro 1,000 Chunks 3.3% so
viel, mit 100% wohlgeformten Antworten und etwas abwechslungsreicherem Text (`reports/gen-comparison.md`); Muse
Glimmer auf unserer eigenen GPU schafft das ohne API-Kosten. Vor dem Senden gibt `--estimate` die Kosten aus;
jeder Lauf hat eine Obergrenze; jeder Aufruf steht im Ledger.

**Nachbearbeitung.** NFC und Leerraum; 1–120 Wörter und die Längenklasse der Einheit ±30%; gesperrte städtische
Begriffe; eine Sprachprüfung; exakte Deduplizierung und Beinahe-Duplikate per Embedding (Kosinus 0.92, nach Domäne
geblockt) gegen das gesamte Primärkorpus; eine menschliche Stichprobenlesung von 2% pro Batch
(`uyari primary sample`); ein Batch mit mehr als 5% Ablehnungen wird zurückgezogen.

**Splits.** Erste Zuweisung: Validierung und Test enthalten je ~300 übersetzte Chunks, als ganze
Paraphrasengruppen aus übersetzten Gruppen, nach Domäne stratifiziert, nach Hash geordnet. Neue Gruppen: Eine
Gruppe, die eine bestehende Zelle neu generiert, erbt deren Split; andere nach Hash (5% / 5%). Einmal geschrieben,
wird der Split eingefroren.

**Weitere Primärkorpora.** Englisch (`primary/eng_Latn`) teilt die Chunk-IDs mit dem Spanischen:
`uyari primary translate` hat alle 11,977 Chunks mit Muse Spark 1.3 Contributor für US$ 0.19 maschinell
übersetzt, als `origin=machine_translated` gekennzeichnet und Split, Domäne und Paraphrasengruppe übernommen.
Weitere Amtssprachen kommen auf dieselbe Weise hinzu.

## 5. Eine Sprache hinzufügen

Ein Ordner `languages/<iso639-3>_<Script>/` mit `language.yaml` und `README.md`. Der Validator akzeptiert ihn,
wenn jeder Code in `registry/` aufgelöst wird (der ISO-639-3-Bereich für lokale Verwendung `qaa`–`qtz` wird
akzeptiert) und eine verantwortliche Person (Steward) benannt ist. Felder:
`id, iso639_3, script, glottocode, display_name, iso_name, primary, steward, community_authority, apostrophe,
apostrophe_variants, training_orthography, trainer`. Buchstaben, die Werkzeuge oft verstümmeln, werden einmal
deklariert: Im Shawi ist der Knacklaut ein Buchstabe, kanonisch `ʼ` (U+02BC), und der Validator listet
abweichende Zeichen mit der Korrektur auf.

## 6. Beitragen

Siehe [`contributing/`](../../contributing/) (Englisch, Spanisch, Portugiesisch, Französisch, Deutsch,
Italienisch, Hindi, Thai). Ein Ordner, ein Pull Request, eine Sprache, eine Varietät, eine Lizenz, ein
Einwilligungsverweis: `contribution.yaml`, `pairs.csv`, `audio.csv`, `speakers.csv`, `wav/`. Teilbeiträge sind
normal; der Build leitet aus den vorhandenen Dateien ab, was ein Ordner enthält.

## 7. Prüfung

Drei Stufen: der **Validator** (CI, jeder PR), der **Gatekeeper** (Muse Glimmer auf unserer eigenen GPU; eine
schriftliche Bewertung in der Arbeitssprache der verantwortlichen Person, Spanisch für Shawi) und der **Steward**
(die verantwortliche Person, die die Sprache spricht). Der Gatekeeper erkennt Validator-Fehler, Text in der
Amtssprache, der in die Spalte der indigenen Sprache eingefügt wurde, aus angenommenen Beiträgen kopierte Zeilen
und Text, der angenommenen Paaren nicht ähnelt; er empfiehlt Merge, Rückgabe oder Eskalation (die Bereiche
Gesundheit und Einwilligung werden immer eskaliert). Er erkennt **keine** maschinelle Übersetzung; Beitragende
bestätigen, dass keine maschinelle Ausgabe als menschliche Arbeit eingereicht wird.

## 8. Builds

`uyari build --tag data-YYYY.MM` liest jeden Beitrag, wendet `replaces` an, überspringt widerrufene Beiträge und
Rückzüge, die am oder vor `--as-of` wirksam sind, normalisiert Text, verknüpft Split und Domäne und schreibt
`builds/<tag>/<lang>/{mt,asr,tts}.parquet` (Training + Validierung) und `*.test.parquet` (Test), dazu
`MANIFEST.json`: Git-Commit, ein- und ausgeschlossene Beiträge mit Gründen, ausgeschlossene Zeilen mit Gründen,
Zeilen pro Split, Lizenzen und pro Tabelle ein Datei-`sha256` und ein kanonischer `content_sha256`. Fehlende Daten
werden abgeleitet, nie deklariert. Parquet liegt nicht in Git; der Tag baut es neu.

## 9. Agenten

| Agent | Auslöser | Entscheidet | Schreibt |
|---|---|---|---|
| **Gatekeeper** | Ein PR in `contributions/` | Merge / Rückgabe / Eskalation (nur Empfehlung) | Eine Bewertung im PR, einen Entwurf von `review.yaml` |
| **Trainer** | Ein Merge in `main` (selbst gehosteter GPU-Runner) oder manuell | Ob sich ein neuer Build lohnt (neue Sprache oder ≥10% mehr Paare); Freigabe nur, wenn jede Richtung die Retrieval-Untergrenze schlägt **und** sich chrF++ auf der Validierung in den Richtungen, die beide gemeinsam haben, um ≥0.5 gegenüber dem bisherigen Modell verbessert, neu bewertet auf demselben Build (oder der Kandidat Richtungen hinzufügt und nicht mehr als 0.5 verliert) | Build-Manifest, Modellkarte, `scores.json`, `models/registry.yaml`, `NEEDS.md`, einen Pull Request |
| Dolmetscher | (nach dem MVP) | | |

Leitplanken: Kein Agent mergt; kein Agent liest den Test-Split vor einer Freigabe; der Test wird pro Modellversion
einmal bewertet; jede Entscheidung ist eine Zeile im PR oder auf der Karte, mit den Zahlen, die zu ihr geführt
haben.

## 10. Training und Evaluation

Rezepte in `recipes/` sind die einzige Konfiguration. Ein Modell pro Backend deckt jede Amtssprache ab, die mit
der indigenen Sprache gepaart ist (derzeit Spanisch und Englisch: vier Richtungen), und jede Richtung wird auf
ihrem eigenen Sprachpaar bewertet. Referenzmodelle für Text:

* **Muse Glimmer 30B, QLoRA** (Unsloth, 4-bit, r=16, maximale Länge 512, Batch 1 × 16, 3 Epochen): das
  Hauptmodell, auf unserer RTX 4090.
* **NLLB-200 1.3B, vollständiges Fine-Tuning** (ein neues Sprach-Token, initialisiert von einer verwandten
  Sprache; `quy_Latn` für Shawi): die schnelle Baseline; trainiert auch auf einer RTX 3060 mit 12 GB in reinem
  bf16.
* **Retrieval-Untergrenze:** die menschliche Übersetzung des nächstgelegenen Trainingssatzes; lokal, kostenlos.

Die Demo stellt nur diese feinabgestimmten Modelle bereit: standardmäßig Glimmer, sobald es trainiert ist, NLLB
als schnellen Modus; die Karten sagen, welches besser abschneidet.

| Aufgabe | Metrik | Menschliche Prüfung |
|---|---|---|
| Text zu Text | chrF++ pro Richtung (BLEU berichtet, nicht optimiert) | Zwei muttersprachliche Personen bewerten 100 Sätze, wenn verfügbar |
| Sprache zu Text | CER (WER berichtet) | Akzeptanz der Transkripte bei 50 Clips |
| Text zu Sprache | Round-Trip-CER über ASR | Natürlichkeit 1–5 |
| Sprache zu Sprache | chrF++ der Ausgabe nach ASR | Aufgabenerfolg in einem vorgegebenen Dialog |

COMET und anderen gelernten Metriken wird bei Übersetzungen in indigene Sprachen nicht vertraut, bis sie an
menschlichen Urteilen validiert sind.

## 11. Governance

Code: Apache 2.0. Daten: pro Beitrag (standardmäßig CC BY 4.0; CC BY-SA, CC BY-NC oder eine Gemeinschaftslizenz
nach Wahl der Gemeinschaft), in jeder Build-Zeile mitgeführt. Die Einwilligung ist kollektiv
(Gemeinschaftsvertretung) und individuell (jede übersetzende und jede sprechende Person); Rückzüge sind Zeilen in
`contributing/takedowns.csv`. Rollen, Lizenzen, Einwilligungsvorlagen und Schutzmaßnahmen, in acht Sprachen:
[`contributing/<language>/governance.md`](../../contributing/de/governance.md).

## 12. Geld

* **Standardmäßig lokal.** Training, Evaluation, der Gatekeeper und die Demo laufen auf unseren eigenen GPUs ohne
  API-Kosten.
* **Eigener Schlüssel.** Alles, was eine kostenpflichtige API aufruft, verwendet den eigenen Meta-Schlüssel der
  aufrufenden Person: Die CLI liest `META_API_KEY`; die Demo fragt Besuchende nach ihrem, verwendet ihn nur für
  diese Anfrage, speichert ihn nie und greift nie auf den Schlüssel des Servers zurück.
* **Erst schätzen, dann ausgeben.** Preise stehen in `config/llm.yaml`; jeder LLM-Befehl schätzt seine Kosten vor
  dem Senden (tiktoken-Näherung × 1.2), die tatsächliche Nutzung jedes Aufrufs steht in `.uyari/ledger.jsonl`, und
  jeder Lauf hat eine feste Obergrenze (`generate` $1, `transcribe` $2, alles andere $0, weil es lokal läuft). Das
  eigene Entwicklungsbudget des Projekts für gehostete APIs beträgt USD 150.
