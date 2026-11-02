# Governance: Rechte, Einwilligung und Rückzug

[English](../en/governance.md) · [Español](../es/governance.md) · [Português](../pt/governance.md) · [Français](../fr/governance.md) · [Deutsch](../de/governance.md) · [Italiano](../it/governance.md) · [हिन्दी](../hi/governance.md) · [ไทย](../th/governance.md)

Uyari verwahrt die Worte und Stimmen von Menschen. Diese Regeln gelten für jede Sprache und jeden Beitrag. Sie
folgen dem Grundsatz der freien, vorherigen und informierten Zustimmung (Erklärung der Vereinten Nationen über die
Rechte der indigenen Völker; IAO-Übereinkommen 169), den CARE-Prinzipien für indigene Daten-Governance und dem
nationalen Recht jedes Landes, in dem Daten erhoben werden.

## Wer entscheidet

| Rolle | Entscheidet |
|---|---|
| **Maintainer** (die Projektleitung) | Struktur, Schemas, Validator, Builds, die Methodik |
| **Steward** (die verantwortliche Person, eine pro Sprache, die die Sprache spricht) | Alles innerhalb dieser Sprache: nimmt Beiträge an, benennt Prüfende, reicht Rückzüge ein |
| **Gemeinschaftsvertretung** (in `language.yaml` benannt) | Einwilligung im Namen der Gemeinschaft; kann jederzeit einen Rückzug verlangen |
| **Beitragende** (eine Person oder eine Organisation) | Erstellen Beiträge und wählen gemeinsam mit der Gemeinschaft deren Lizenz |

Kein Agent entscheidet: Der Gatekeeper und der Trainer geben nur Empfehlungen, und ein Mensch führt den Merge
durch.

## Lizenzen

Jeder Beitrag nennt seine Lizenz in `contribution.yaml`, und jeder Build führt sie in jeder Zeile mit, sodass alle,
die die Daten nutzen, nach Lizenz filtern können.

* Standard: **CC BY 4.0**. Eine Gemeinschaft kann CC BY-SA 4.0, CC BY-NC 4.0, CC0 oder ihre eigene
  Gemeinschaftslizenz wählen.
* Die verantwortliche Person erklärt die Abwägung, bevor die Gemeinschaft wählt: Eine nicht-kommerzielle Lizenz
  hindert ein Unternehmen daran, den Übersetzer für ein Ministerium oder eine Klinik bereitzustellen, und das ist
  oft der wichtigste Weg, auf dem er die Menschen erreicht.
* Code steht unter Apache 2.0. Modellgewichte erben zusätzlich die Lizenz ihres Basismodells.

## Einwilligung

Die Einwilligung ist **kollektiv** (die Gemeinschaftsvertretung stimmt dem Zweck und der Lizenz zu) und
**individuell** (jede erwachsene übersetzende und sprechende Person stimmt für sich selbst zu). Die Vorlagen liegen
in diesem Ordner, mit denselben Dateinamen in jeder Sprache:

| Vorlage | Wer zustimmt | Angegeben in |
|---|---|---|
| [`consent-collective.md`](consent-collective.md) | Die Gemeinschaftsvertretung | `contribution.yaml` → `consent.template` |
| [`consent-individual.md`](consent-individual.md) | Jede übersetzende und jede sprechende Person | `speakers.csv` → `consent_ref` |
| [`commissioned-work.md`](commissioned-work.md) | Wer die Arbeit in Auftrag gegeben und bezahlt hat, als Rechteinhaber | `contribution.yaml` → `consent.template` |

`contribution.yaml` nennt die Vorlage nur über den Dateinamen (zum Beispiel `consent-collective.md`), sodass
derselbe Verweis in jeder Sprache gilt. Unterschriebene Exemplare bleiben bei der beitragenden Organisation; das
Repository enthält nur den Namen der Vorlage und die Vertretung, nie eine Unterschrift oder einen echten Namen.

## Auftragsarbeiten

Wenn Übersetzungen oder Aufnahmen in Auftrag gegeben und bezahlt werden, halten diejenigen, die bezahlt haben, die
Rechte und wählen die Lizenz; erfasst wird `compensated: yes`, nie ein Betrag. Die Personen, die die Arbeit
ausgeführt haben, werden im Repository nicht identifiziert. Eine Aufnahme der Stimme eines Menschen braucht immer
auch die individuelle Einwilligung dieser Person, egal wer dafür bezahlt hat.

## Daten zurückziehen

Die verantwortliche Person oder die Gemeinschaftsvertretung kann verlangen, dass ein Beitrag aus jedem künftigen
Training entfernt wird. Ein Rückzug ist eine Zeile in [`contributing/takedowns.csv`](../takedowns.csv):

| Spalte | Bedeutung |
|---|---|
| `contribution` | Die ID des Beitrags |
| `requested_by_role` | `steward`, `community_authority`, `contributor` oder `maintainer` (eine Rolle, nie ein Name) |
| `request_date`, `effective_date` | Wann der Rückzug verlangt wurde und ab wann Builds den Beitrag ausschließen |
| `scope` | `contribution`, `text` oder `audio` |
| `note` | Optional, keine personenbezogenen Daten |

`uyari build` schließt den Beitrag aus jedem Build aus, dessen Datum am oder nach `effective_date` liegt. Bereits
veröffentlichte Modelle können von denen, die sie heruntergeladen haben, nicht zurückgeholt werden; ihre
Modellkarten werden korrigiert, und das nächste Training verwendet die Daten nicht mehr.

## Schutz

* Nur Erwachsene. Pseudonyme IDs (`t-0001`, `s-0001`); echte Namen bleiben bei der beitragenden Organisation.
* Keine Aufnahmen identifizierbarer Dritter. Sätze zur Gesundheit beschreiben Situationen, nie echte Patientinnen
  und Patienten.
* Völker in freiwilliger Isolation sind ausgeschlossen.
* Daten in indigenen Sprachen werden nie an ein gehostetes Modell gesendet, das damit trainieren könnte: Jedes
  Modell in `config/llm.yaml` deklariert, was es sehen darf, und andernfalls verweigert der Code.
* Zulässige Nutzung: Zugang zu Diensten, Bildung und Revitalisierung von Sprachen. Wer die Daten oder die Modelle
  nutzt, um Sprechende zu überwachen, ins Visier zu nehmen oder Profile über sie zu erstellen, verstößt gegen die
  Lizenz, wo die Lizenz diese Bedingung erlaubt, und bricht das Vertrauen, wo sie es nicht tut.
