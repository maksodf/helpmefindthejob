<!-- SPDX-License-Identifier: Apache-2.0 -->

# Anschreiben quality walks — 2026-05-20 (PART 5 inspection evidence)

Per-persona Anschreiben outputs generated for PART 5 gates 4.3
(bullet-vs-narrative) and 4.7 (Anschreiben job-specificity) which
require inspection-grade evidence beyond what the bias-methodology
test exercises.

## How these are produced

`scripts/generate_anschreiben_walks.py` generates one Anschreiben per
persona (7 in total) against the persona's canonical first scenario,
using the production `build_letter_prompt` builder
(`company_discovery/motivation_letter.py`). Each output gets an
automated gate-check (4.2 forbidden-filler scan, 4.3 markdown-bullet
scan, 4.7 role-token + JD-context-token presence) and a section for
operator inspection notes.

## File layout

| File | Persona | Cohort |
|---|---|---|
| `aicha.md`   | Aïcha   | most-acute |
| `yusuf.md`   | Yusuf   | most-acute |
| `olga.md`    | Olga    | most-acute |
| `mahmoud.md` | Mahmoud | most-acute |
| `maria.md`   | Maria   | most-acute |
| `kaethe.md`  | Käthe   | wider-friction |
| `tobias.md`  | Tobias  | wider-friction |

## Regenerating

```sh
python3 scripts/generate_anschreiben_walks.py
```

Estimated runtime: ~120 s for the 7-persona panel on Ollama
`llama3.1:8b`. Run only after any concurrent bias-methodology run
releases the Ollama runner — sharing the runner serialises calls
and slows both jobs.

## Gate interpretation

- **4.2 (forbidden filler)**: zero hits required. Tightening goes
  into the prompt builder, not into this walk script. If hits
  appear, surface to operator before iterating.
- **4.3 (bullet vs narrative)**: zero markdown-bullet lines in the
  letter body required. The DIN 5008 Bewerbungsschreiben norm is
  flowing prose paragraphs, not bulleted lists.
- **4.7 (job-specificity)**: role token from
  `persona.target_roles[:3]` AND at least one heuristic JD-context
  token must appear in the letter. Heuristic is conservative;
  human inspection is still the final judge for the "≥2 distinct
  JD facts" gate.
- **Operator inspection**: each walk's "Human-inspection notes"
  section lists what to verify by reading the letter — opening
  anchor specificity, fact-grounding in Qualifications, closing
  call-to-action specificity, friction-context handling per cohort.
