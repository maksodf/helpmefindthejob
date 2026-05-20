<!-- SPDX-License-Identifier: Apache-2.0 -->

# Anschreiben quality walk — Yusuf (Turkey → Munich)

**Persona slug**: `yusuf`  |  **Cohort**: `most-acute`  |  **Location**: Munich
**Residency status**: EU Blue Card pending, employer-sponsored
**Friction notes**: Wants comparison across Munich / Stuttgart / Ingolstadt for the first 6-12 months; needs structured post-arrival timeline (Anmeldung, Steuer-ID, Krankenkasse, school-place for elder child).

## Fixture JD

**Scenario label**: `bluecard_automotive_engineer`
**Job title**: Mechanical Design Engineer (EU Blue Card, English-speaking team)
**Job location**: Munich
**Company**: Beispielarbeitgeber (Munich) (synthetic for this walk)

**Job description**:

> Mid-size automotive supplier in Munich seeks Mechanical Design Engineer with 10+ years experience. English-speaking team; German A1+ sufficient. EU Blue Card sponsorship offered. ISO 9001 background preferred.

## Generation metadata

- Model: Ollama `llama3.1:8b`
- Elapsed: 13.4 s
- Output length: 1432 chars
- Prompt builder: `company_discovery.motivation_letter.build_letter_prompt`
- Friction context surfaced via `residency_status` + `friction_notes` parameters

## Anschreiben output

```
Absenderzeile: Yusuf München

Empfängeradresse: Beispielarbeitgeber München

Date: 10.02.2023

Betreff: Bewerbung als Mechanical Design Engineer

Sehr geehrte Damen und Herren,

Mein Interesse an der Stelle als Mechanical Design Engineer bei Beispielarbeitgeber in München entstand, nachdem ich die Beschreibung des Jobs studiert hatte. Ich bin beeindruckt von der Möglichkeit, meine 13 Jahre Erfahrung im Bereich der Automobilindustrie, insbesondere beim VW- und Mercedes-Gespann, für ein renommiertes Unternehmen wie Beispielarbeitgeber einzusetzen.

Als mechanical engineer verfüge ich über einen Bachelor-Abschluss an der ITÜ Istanbul und bin ISO 9001-Leit-auditor. Meine Sprachkenntnisse in Türkisch sind muttersprachlich, während meine Englischkenntnisse auf B2-Niveau liegen und ich mich gerade noch A2-Niveau in Deutsch verbessere. Da mein EU-Blue-Carrier antragsfortschritt ist, bin ich sicher, dass ich die Anforderungen der Stelle erfüllen kann.

Ich möchte betonen, wie wichtig es für mich ist, ein Unternehmen zu finden, das nicht nur technische Expertise bietet, sondern auch eine positive Atmosphäre fördert. Ich habe mich auch überzeugt, dass Beispielarbeitgeber ein solches Unternehmen ist und daher freue ich mich auf die Gelegenheit, mein Wissen in diesem Bereich einzubringen. Ich bitte Sie darum, mich zu einem Interview einzuladen, damit wir uns persönlich kennenlernen können.

Mit freundlichen Grüßen,

Yusuf
```

## Automated gate-check (machine-readable)

| Gate | Measure | Result |
|---|---|---|
| 4.2 | Forbidden-filler hits (case-insensitive, 8 patterns) | 0 PASS |
| 4.3 | Markdown-bullet lines in body | 0 PASS |
| 4.7 (role) | Role token from `persona.target_roles[:3]` present | ['Mechanical engineer'] |
| 4.7 (context) | JD-derived context tokens found (heuristic) | ['Mechanical', 'Design', 'Engineer', 'Blue'] (4 / 8 candidates) |

**4.7 decision rule**: PASS if `role_hits >= 1 AND context_hits >= 1`. PASS

## Human-inspection notes (operator review)

- Does the letter open with a SPECIFIC anchor (role + company + reason), not a generic opener?
- Does the Qualifications paragraph reference at least one concrete CV fact, not generic claims?
- Does the Fit paragraph close with a SPECIFIC call to action (interview request + time-window), not a platitude?
- For migrant personas (Aïcha / Yusuf / Olga / Mahmoud / Maria): is friction context surfaced authentically (not over-emphasised in the opening; woven into Qualifications where material)?
- For wider-friction personas (Käthe / Tobias): is the friction-class context present without over-claiming friction?
- Does the letter respect DIN 5008 structure (Absenderzeile / Empfänger / Date / Betreff / Anrede / Hauptteil / Schluss / Unterschrift)?
