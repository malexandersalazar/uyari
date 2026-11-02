# Governance: diritti, consenso e ritiro

[English](../en/governance.md) · [Español](../es/governance.md) · [Português](../pt/governance.md) · [Français](../fr/governance.md) · [Deutsch](../de/governance.md) · [Italiano](../it/governance.md) · [हिन्दी](../hi/governance.md) · [ไทย](../th/governance.md)

Uyari custodisce le parole e le voci delle persone. Queste regole valgono per ogni lingua e ogni contributo.
Seguono il consenso libero, previo e informato (Dichiarazione delle Nazioni Unite sui diritti dei popoli
indigeni; Convenzione OIL 169), i principi CARE per la governance dei dati indigeni e la legge nazionale di ogni
paese in cui si raccolgono i dati.

## Chi decide

| Ruolo | Decide |
|---|---|
| **Maintainer** (chi guida il progetto) | Struttura, schemi, validatore, build, la metodologia |
| **Persona responsabile della lingua (steward)** (una per lingua, che la parla) | Tutto ciò che riguarda quella lingua: accetta i contributi, nomina chi fa le revisioni, registra i ritiri |
| **Autorità comunitaria** (indicata in `language.yaml`) | Il consenso a nome della comunità; può chiedere un ritiro in qualsiasi momento |
| **Contributore** (una persona o un'organizzazione) | Produce i contributi e ne sceglie, con la comunità, la licenza |

Nessun agente decide: il Gatekeeper e il Trainer si limitano a raccomandare, e il merge lo fa una persona.

## Licenze

Ogni contributo indica la propria licenza in `contribution.yaml`, e ogni build la riporta su ogni riga, così
chiunque usi i dati può filtrarli per licenza.

* Predefinita: **CC BY 4.0**. Una comunità può scegliere CC BY-SA 4.0, CC BY-NC 4.0, CC0 o una propria licenza
  comunitaria.
* Prima che la comunità scelga, la persona responsabile spiega il compromesso: una licenza non commerciale
  impedisce a un'azienda di mettere in servizio il traduttore per un ministero o un ambulatorio, che spesso è il
  modo principale in cui arriva alle persone.
* Il codice è Apache 2.0. I pesi dei modelli ereditano anche la licenza del loro modello di base.

## Consenso

Il consenso è **collettivo** (l'autorità comunitaria accetta lo scopo e la licenza) e **individuale** (ogni
traduttore e ogni parlante adulto accetta per sé). I modelli sono in questa cartella, con gli stessi nomi di
file in ogni lingua:

| Modello | Chi dà il consenso | Indicato in |
|---|---|---|
| [`consent-collective.md`](consent-collective.md) | L'autorità comunitaria | `contribution.yaml` → `consent.template` |
| [`consent-individual.md`](consent-individual.md) | Ogni traduttore e ogni parlante | `speakers.csv` → `consent_ref` |
| [`commissioned-work.md`](commissioned-work.md) | Chi ha commissionato e pagato il lavoro, in quanto titolare dei diritti | `contribution.yaml` → `consent.template` |

`contribution.yaml` indica il modello solo con il nome del file (per esempio `consent-collective.md`), così lo
stesso riferimento vale in ogni lingua. Le copie firmate restano all'organizzazione che contribuisce; il
repository conserva solo il nome del modello e l'autorità, mai una firma o un nome reale.

## Lavoro su commissione

Quando traduzioni o registrazioni sono commissionate e pagate, chi ha pagato detiene i diritti e sceglie la
licenza; si registra `compensated: yes`, mai un importo. Le persone che hanno svolto il lavoro non sono
identificate nel repository. Una registrazione della voce di qualcuno richiede sempre anche il consenso
individuale di quella persona, chiunque l'abbia pagata.

## Ritiro

La persona responsabile o l'autorità comunitaria può chiedere che un contributo esca da ogni addestramento
futuro. Il ritiro è una riga in [`contributing/takedowns.csv`](../takedowns.csv):

| Colonna | Significato |
|---|---|
| `contribution` | L'id del contributo |
| `requested_by_role` | `steward`, `community_authority`, `contributor` o `maintainer` (un ruolo, mai un nome) |
| `request_date`, `effective_date` | Quando è stato chiesto e da quando le build lo escludono |
| `scope` | `contribution`, `text` o `audio` |
| `note` | Facoltativa, senza dati personali |

`uyari build` esclude il contributo da ogni build con data uguale o successiva a `effective_date`. I modelli già
pubblicati non possono essere recuperati da chi li ha scaricati; le loro schede vengono corrette e
l'addestramento successivo non usa più quei dati.

## Tutela

* Solo persone adulte. Id pseudonimi (`t-0001`, `s-0001`); i nomi reali restano all'organizzazione che
  contribuisce.
* Nessuna registrazione di terze persone identificabili. Le frasi sulla salute descrivono situazioni, mai
  pazienti reali.
* I popoli in isolamento volontario sono esclusi.
* I dati in lingua indigena non vengono mai inviati a un modello ospitato da terzi che potrebbe addestrarsi su
  di essi: ogni modello in `config/llm.yaml` dichiara che cosa può vedere, e in caso contrario il codice si
  rifiuta.
* Uso accettabile: accesso ai servizi, istruzione e rivitalizzazione linguistica. Usare i dati o i modelli per
  sorvegliare, prendere di mira o profilare i parlanti viola la licenza dove la licenza consente quella
  condizione, e viola la fiducia dove non la consente.
