<!-- SPDX-License-Identifier: Apache-2.0 -->

# Anschreiben quality walk — Aïcha (Tunisia → Berlin)

**Persona slug**: `aicha`  |  **Cohort**: `most-acute`  |  **Location**: Berlin
**Residency status**: §16d AufenthG (visa for purpose of recognition of foreign qualification)
**Friction notes**: Recognition decision letter expected in ~4 months; needs Anerkennung-friendly employers willing to begin onboarding before the letter lands.

## Fixture JD

**Scenario label**: `anerkennung_friendly_clinical`
**Job title**: Krankenpfleger / Krankenpflegerin (Anerkennung-friendly)
**Job location**: Berlin
**Company**: Beispielarbeitgeber (Berlin) (synthetic for this walk)

**Job description**:

> Krankenhaus in Berlin sucht Krankenpflegekraft. Anerkennung-friendly: Wir nehmen Bewerber:innen im laufenden Anerkennungsverfahren auf und arbeiten Sie ein, bis das Anerkennungsschreiben da ist. Erfahrung in der Geriatrie erwünscht.

## Generation metadata

- Model: Ollama `llama3.1:8b`
- Elapsed: 20.6 s
- Output length: 1546 chars
- Prompt builder: `company_discovery.motivation_letter.build_letter_prompt`
- Friction context surfaced via `residency_status` + `friction_notes` parameters

## Anschreiben output

```
Absenderzeile:
Aïcha, Berlin

Empfängeradresse:
Beispielarbeitgeber
Berlin

Date: 25.06.2023

Betreff:
Bewerbung als Krankenpflegerin

Anrede:
Sehr geehrte Damen und Herren,

Mit großer Begeisterung habe ich mich für die Stelle der Krankenpflegerin bei Beispielarbeitgeber beworben, da sie meiner Überzeugung nach den Bedürfnissen und Erwartungen von Patientinnen und Patienten in Berlin gerecht wird. Ich bin beeindruckt vom Engagement des Arbeitgebers für eine hohe Qualität der Pflege und seine Verantwortung gegenüber seinen Mitarbeitern.

In meinem bisherigen Berufsleben habe ich sieben Jahre Erfahrung als Krankenschwester im Krankenhaus gesammelt, darunter zwei Jahre in geriatrischer Betreuung. Ich bin französisch- und arabischsprachig und verfüge über ein B2-Zertifikat für Englisch sowie ein Arbeitszeugnis für Deutsch auf dem Niveau B1, das ich momentan weiterentwickle. Derzeit befindet sich mein Anerkennungsverfahren bei der BIBB/Anabin in der Auswertung.

Meine Fähigkeiten und Erfahrungen decken sich mit den Anforderungen des Jobs und ermöglichen es mir, mich schnell an die spezifischen Herausforderungen in einem Berliner Krankenhaus anzupassen. Ich bin überzeugt, dass mein Engagement und meine Pflichtbewusstsein für hervorragende Pflegeergebnisse sorgen werden.

Ich freue mich darauf, mit Ihnen persönlich zu sprechen und mehr über meine Qualifikationen und Erfahrungen zu erfahren. Bitte zögern Sie nicht, mich anzukündigen, damit ich bereit bin, einen Termin zur Besprechung einzuplanen.

Mit freundlichen Grüßen,
Aïcha
```

## Automated gate-check (machine-readable)

| Gate | Measure | Result |
|---|---|---|
| 4.2 | Forbidden-filler hits (case-insensitive, 8 patterns) | 0 PASS |
| 4.3 | Markdown-bullet lines in body | 0 PASS |
| 4.7 (role) | Role token from `persona.target_roles[:3]` present | ['Krankenpfleger'] |
| 4.7 (context) | JD-derived context tokens found (heuristic) | ['Krankenhaus', 'Berlin', 'Anerkennungsverfahren', 'Erfahrung'] (4 / 8 candidates) |

**4.7 decision rule**: PASS if `role_hits >= 1 AND context_hits >= 1`. PASS

## Human-inspection notes (operator review)

- Does the letter open with a SPECIFIC anchor (role + company + reason), not a generic opener?
- Does the Qualifications paragraph reference at least one concrete CV fact, not generic claims?
- Does the Fit paragraph close with a SPECIFIC call to action (interview request + time-window), not a platitude?
- For migrant personas (Aïcha / Yusuf / Olga / Mahmoud / Maria): is friction context surfaced authentically (not over-emphasised in the opening; woven into Qualifications where material)?
- For wider-friction personas (Käthe / Tobias): is the friction-class context present without over-claiming friction?
- Does the letter respect DIN 5008 structure (Absenderzeile / Empfänger / Date / Betreff / Anrede / Hauptteil / Schluss / Unterschrift)?
