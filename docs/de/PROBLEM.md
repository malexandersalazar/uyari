# Das Problem: die Sprachlücke bei grundlegenden Diensten

[English](../../PROBLEM.md) · [Español](../es/PROBLEM.md) · [Português](../pt/PROBLEM.md) · [Français](../fr/PROBLEM.md) · **Deutsch** · [Italiano](../it/PROBLEM.md) · [हिन्दी](../hi/PROBLEM.md) · [ไทย](../th/PROBLEM.md)

Rund **476 Millionen** indigene Menschen leben in 90 Ländern. Viele von ihnen begegnen Ärztinnen und Ärzten,
Einwilligungsformularen, Gerichten und Standesämtern in einer Amtssprache, die sie nicht ganz verstehen. Wo das
gemessen wird, sind die Zahlen groß: Allein in vier lateinamerikanischen Ländern können rund **3 Millionen**
Menschen die Amtssprache ihres Landes überhaupt nicht verwenden. Anderswo wird es meist nicht erfasst.

Offene Basismodelle für Sprache und Übersetzung decken inzwischen mehr als 1,600 Sprachen ab. Was fehlt, ist die
Schicht, die daraus etwas macht, das eine Klinik nutzen kann: **evaluierte, von der Gemeinschaft verwaltete
Modelle zwischen jeder indigenen Sprache und der Amtssprache, die ihre Sprechenden brauchen, in Text und
gesprochener Sprache**. Uyari baut diese Schicht auf der letzten Meile, für jede Sprache. Es baut kein weiteres
Basismodell.

## 1. Größenordnung

| Region (IAO, 2019) | Anteil | Indigene Bevölkerung |
|---|---|---|
| Asien & Pazifik | 70.5% | >335M |
| Afrika | 16.3% | >77M |
| Lateinamerika & Karibik | 11.5% | ~55M (CEPAL 2018: 58M; 826 Völker) |
| Nordamerika | 1.6% | >7M |
| Europa & Zentralasien | 0.1% | <1M |
| **Welt** | | **476.6M (>6% der Menschheit)** |

* Indigene Menschen leben fast dreimal so häufig in extremer Armut (IAO).
* Von 7,159 lebenden Sprachen sind 3,193 (etwa 45%) gefährdet (Ethnologue, 28. Ausgabe, 2025).
* 40% der Menschen weltweit haben keinen Unterricht in einer Sprache, die sie verstehen, in manchen Ländern mit
  niedrigem und mittlerem Einkommen bis zu 90% (UNESCO GEM Report, 2025).

## 2. Menschen, die die Amtssprache nicht verwenden können

Eine weltweite Zählung gibt es nicht; nur wenige Volkszählungen stellen die Frage. Am besten erfasst ist
Lateinamerika:

| Land | Sprechende indigener Sprachen | Können die Amtssprache nicht verwenden | Quelle |
|---|---|---|---|
| Mexiko | 7,364,645 (6.1%, ab 3 Jahren) | **865,972** sprechen kein Spanisch | INEGI-Zensus 2020 (direkte Zählung) |
| Guatemala | 4,027,481 mit indigener Muttersprache | **~1.64M** (20.9% der indigenen Bevölkerung) | Instituto Cervantes 2024 (Schätzung) |
| Peru | 4,477,195 mit indigener Muttersprache (16.02%, ab 3 Jahren) | **~335,576** | Instituto Cervantes 2024 (Schätzung; der Zensus fragt nicht danach) |
| Bolivien | ~4.2M (2012) | **~267,729** | Instituto Cervantes 2024 (Schätzung) |

Das sind rund **3.1 Millionen** Menschen in vier Ländern, dazu mehrere Millionen Zweisprachige, die in der
Amtssprache einkaufen können, aber einer Diagnose oder einer Gerichtsverhandlung nicht folgen können. Dieselbe
Lücke besteht überall, wo ein Staat in einer Sprache arbeitet, die seine indigenen Bürgerinnen und Bürger nicht
sprechen; sie wird nur nicht gezählt. Siebzig Prozent der indigenen Menschen weltweit leben in Asien und im
Pazifikraum, wo es keine vergleichbare Zahl gibt.

Diese Bevölkerungsgruppen sind nicht klein. Allein in Mexiko sprechen mehr Menschen eine indigene Sprache als
Dänisch, Finnisch oder Norwegisch, und alle drei haben volle kommerzielle KI-Unterstützung.

## 3. Warum das wichtig ist: Gesundheit, Bildung, Justiz

* **Gesundheit.** In Guatemala war die Sprachbarriere „das wichtigste Hindernis“ dafür, dass indigene Frauen
  Dienste der reproduktiven Gesundheit nutzen (Guttmacher-Analyse der nationalen Erhebung 2008–09), und die
  Müttersterblichkeit indigener Frauen war mehr als doppelt so hoch wie die nicht-indigener Frauen: 166 gegenüber
  78 pro 100,000 Lebendgeburten (nationale Studie 2011). In Guatemala, Mexiko, Peru und Bolivien bringen Frauen,
  die eine indigene Sprache *sprechen*, seltener in einer Gesundheitseinrichtung ein Kind zur Welt. Wo
  Krankenhäuser keine Dolmetschenden haben, scheitert die informierte Einwilligung.
* **Bildung.** Kinder, die in einer Sprache unterrichtet werden, die sie sprechen, lesen weit häufiger mit
  Verständnis (UNESCO 2025). In Mexiko haben Sprechende indigener Sprachen ab 15 Jahren im Schnitt 6.2 Schuljahre;
  **Einsprachige im Schnitt 1.4** (INEGI 2020).
* **Justiz und Verwaltung.** Gesetze, die indigene Sprachen anerkennen, sind häufig; Dolmetschende nicht. Im
  peruanischen Kongress fehlten wiederholt Dolmetschende für offizielle indigene Sprachen, und Mexiko gibt
  indigenen Sprachen rechtliche Gültigkeit, während die Umsetzung hinterherhinkt.

Einsprachige sind überproportional älter, weiblich und nicht alphabetisiert. **Gesprochene Sprache ist nicht
optional**: Textübersetzung allein erreicht sie nicht.

## 4. Was es gibt und was fehlt

| Ebene | Was es gibt | Lücke |
|---|---|---|
| Basismodelle | Meta Omnilingual ASR (1,600+ Sprachen, Apache 2.0), Omnilingual MT (1,600+), NLLB-200, MMS; Google Translate; Microsoft Translator | Meist gegen Englisch evaluiert; Qualität für die meisten indigenen Sprachen unbekannt; wenig TTS oder Sprache-zu-Sprache |
| Benchmarks | Regionale Shared Tasks wie AmericasNLP (~13 Sprachen ↔ Spanisch, nur Text) | MT von der Amtssprache in indigene Sprachen hat dort „ein Leistungsplateau erreicht“ (chrF++ etwa 13–37) |
| Gemeinschaftsprojekte | Te Hiku Media (Māori), Voces (Chile/Peru), viele lokale Pilotprojekte | Jeweils eine oder wenige Sprachen; nicht als Pipeline wiederverwendbar |

Was fehlt und wofür Uyari gebaut ist:

1. **Paare Muttersprache ↔ Amtssprache**, kein Umweg über Englisch, bei dem sich Fehler aufaddieren.
2. **Gesprochene Sprache** (ASR, TTS, Sprache-zu-Sprache) für Sprachen, deren Sprechende oft nicht lesen.
3. **Fachdaten** für Gesundheit, Einwilligung, Standesamt und Justiz.
4. **Menschliche Bewertung** durch muttersprachliche Personen und zertifizierte Dolmetschende, nicht nur
   automatische Metriken.
5. **Bewusstsein für Dialekte**: Ein Sprachname umfasst oft viele Varietäten („Quechua“ sind allein in Peru 25+).
6. **Governance**: Einwilligung, Vorteilsausgleich und Lizenzen, die mit indigener Datensouveränität vereinbar
   sind.
7. **Einsatz**, der offline auf bescheidener Hardware laufen kann.

## 5. Der Ansatz

* **Fünf Anwendungsfälle pro Sprachpaar:** indigener Text → Text in der Amtssprache, Text in der Amtssprache →
  indigener Text, Gesprochenes in indigener Sprache → Gesprochenes in der Amtssprache, Gesprochenes in der
  Amtssprache → Gesprochenes in indigener Sprache, und Sprache-zu-Text für die indigene Sprache.
* **Auf Metas offenen Basismodellen aufbauen; pro Sprache anpassen.** Ein gemeinsames mehrsprachiges Modell (Muse
  Glimmer QLoRA, NLLB-200) wird auf jedes Paar Muttersprache↔Amtssprache feinabgestimmt; eine
  Retrieval-Untergrenze hält jedes Modell ehrlich.
* **Sprache-zu-Sprache als Kaskade** (ASR → MT → TTS), mit sichtbarem Text in der Mitte, damit ein Mensch eine
  Diagnose oder ein Einwilligungsformular prüfen kann, bevor es ausgesprochen wird.
* **Daten sind das Budget.** Pro Sprache etwa 5–20k Fachsätze, 4–10 h vorgelesene Sprache einer einzigen
  sprechenden Person für eine Stimme (eine Shipibo-Konibo-Stimme erreichte MOS 4.01 mit ~4 h) und 10–50 h
  transkribierte Sprache. Rechenleistung ist ein kleiner Bruchteil der Kosten (eine technische Schätzung, keine
  veröffentlichte Zahl).
* **Jede Sprache, ohne Codeänderungen.** Eine Sprache ist ein Ordner; die Daten einer Gemeinschaft sind ein Ordner
  darin. Die Seite der Amtssprache ist ein gemeinsames Korpus (zuerst Spanisch; weitere Amtssprachen über
  denselben Mechanismus).
* **Governance von Anfang an**: freie, vorherige und informierte Zustimmung (UNDRIP, IAO-Übereinkommen 169), die
  CARE-Prinzipien, Lizenzen pro Beitrag, Rückzug als Datenzeile, bezahlte Beitragende, und Völker in freiwilliger
  Isolation ausdrücklich ausgeschlossen.
* **Dolmetschende erstellen und bewerten Daten**, statt von dem Werkzeug verdrängt zu werden.
* **Wirkung messen, nicht nur chrF++**: Verständnis der Einwilligung, wahrgenommene Vorsorgetermine in der
  Schwangerschaft, Zeit bis zur Versorgung.

## 6. Der erste Fall: Shawi ↔ Spanisch (Peru)

Shawi ist der erste Fall, weil die Arbeit dort bereits begonnen hatte, nicht weil das Problem peruanisch ist. Der
Fall Shawi–Spanisch begann mit Müttergesundheit: Shawi-Gemeinschaften treffen auf Gesundheitsdienste, die keine
Unterstützung in ihrer Sprache bieten. Die Leitung des Falls ließ Übersetzungen von Menschen anfertigen, und diese
Übersetzungen sind Uyaris erste Daten. Nichts im Code ist spezifisch für Shawi.

| Indikator | Zahl | Quelle |
|---|---|---|
| Indigene Völker / Sprachen in Peru | 55 Völker; 48 Amtssprachen | MinCul (2025–26) |
| Indigene Muttersprache, ab 3 Jahren | 4,477,195; Quechua 3,799,780; Aymara 450,010 | Zensus 2017 (über MinCul 2024) |
| Muttersprache Shawi | 17,241 | MinCul BDPI (Zensus 2017) |
| Registrierte Dolmetschende | **859** (ReNITLI), für 39 von 48 Sprachen | MinCul (Jan 2025) |

Auf eine registrierte dolmetschende Person kommen etwa 5,200 Menschen mit indigener Muttersprache, und neun
Sprachen haben gar keine. Nur in 23.1% der Haushalte, in denen die Muttersprache eines Elternteils indigen ist,
gibt es ein Kind, das sie spricht (INEI 2017); die einsprachige Bevölkerung altert, daher schließt sich das
Zeitfenster, um ältere Menschen aufzunehmen, die die Sprache fließend sprechen.

## Einschränkungen

* Die Bevölkerungszahlen sind Schätzungen aus 2010–2019. Je nach Definition (vor allem für China und Indien)
  verschieben sich die weltweiten Summen um mehr als 100M.
* Nur die 865,972 für Mexiko sind eine direkte Zensuszählung von Menschen, die die Amtssprache nicht sprechen. Die
  Zahlen für Peru, Guatemala und Bolivien sind Schätzungen des Instituto Cervantes 2024, abgeleitet aus
  Analphabetismus als Näherungswert, und könnten zu hoch sein.
* Angaben zur Qualität der Basismodelle stammen von den Anbietern selbst und sind auf Englisch ausgerichtet. Es
  gibt nur wenige unabhängige Evaluationen zwischen indigenen Sprachen und den Amtssprachen ihrer Länder.
* Zensusfragen unterscheiden sich: Perus Zensus fragt nach der Muttersprache, nicht nach der Beherrschung der
  Amtssprache, und die Altersgrenzen unterscheiden sich (3+ gegenüber 5+), daher immer angeben.
