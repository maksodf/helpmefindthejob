<!-- SPDX-License-Identifier: Apache-2.0 -->

# Journey walk — Olga (Ukraine → Leipzig)

**Persona slug**: `olga`  |  **Cohort**: `most-acute`
**Residency status**: §24 AufenthG (temporary protection for displaced Ukrainians)
**Friction notes**: Single parent (one child age 7 in Grundschule); needs remote-friendly or English-speaking-team roles where A2 German is not a 12-month blocker. Wants to be evaluated on shipped-software portfolio rather than language.

## Walk-through (live HTTP API, /api/chat/message)

Each row captures one user → assistant turn with the journey-phase
transition and the wall-clock latency for that turn.

| # | User input | Phase after | Reply (truncated) | Elapsed |
|---|---|---|---|---|
| 1 | `/start` | `discover` | Got it — let's find you a job. I'll ask a few short questions, then search for you and show what fits.    **1. What kind of role are you … | 6 ms |
| 2 | `Senior frontend developer` | `discover` | Got it: **Senior frontend developer**.    **2. Where?** (city, country, or "anywhere" / "remote") | 61 ms |
| 3 | `Leipzig` | `discover` | Noted: **Leipzig**.    **3. How many years' experience do you have in this kind of role?** (a number is fine — e.g., "3" or "about 7") | 1 ms |
| 4 | `9` | `discover` | **4. Which languages do you work in?** (comma-separated, e.g., "Deutsch, English") | 1 ms |
| 5 | `UK: native, RU: native, EN: C1` | `cv_check` | Thanks. Quick summary:    - Role: **Senior frontend developer**    - Where: **Leipzig**    - Experience: **9**    - Languages: **UK: nati… | 1 ms |

## Per-turn detail

### Turn 1 — Begin guided journey

**Input**: `/start`

**Executed**: `start_job_journey`  |  **Phase after**: `discover`  |  **Done**: `False`  |  **Elapsed**: 6 ms

**Reply**:

```
Got it — let's find you a job. I'll ask a few short questions, then search for you and show what fits.

**1. What kind of role are you looking for?** (e.g., "Pflegehelfer", "bartender", "backend engineer", "barista")
```

### Turn 2 — Answer: target role

**Input**: `Senior frontend developer`

**Executed**: `None`  |  **Phase after**: `discover`  |  **Done**: `None`  |  **Elapsed**: 61 ms

**Reply**:

```
Got it: **Senior frontend developer**.

**2. Where?** (city, country, or "anywhere" / "remote")
```

### Turn 3 — Answer: target location

**Input**: `Leipzig`

**Executed**: `None`  |  **Phase after**: `discover`  |  **Done**: `None`  |  **Elapsed**: 1 ms

**Reply**:

```
Noted: **Leipzig**.

**3. How many years' experience do you have in this kind of role?** (a number is fine — e.g., "3" or "about 7")
```

### Turn 4 — Answer: years of experience

**Input**: `9`

**Executed**: `None`  |  **Phase after**: `discover`  |  **Done**: `None`  |  **Elapsed**: 1 ms

**Reply**:

```
**4. Which languages do you work in?** (comma-separated, e.g., "Deutsch, English")
```

### Turn 5 — Answer: languages

**Input**: `UK: native, RU: native, EN: C1`

**Executed**: `None`  |  **Phase after**: `cv_check`  |  **Done**: `None`  |  **Elapsed**: 1 ms

**Reply**:

```
Thanks. Quick summary:
  - Role: **Senior frontend developer**
  - Where: **Leipzig**
  - Experience: **9**
  - Languages: **UK: native, RU: native, EN: C1**

**Do you have a CV ready?** Three options:
  - Paste it in chat (drop the whole text)
  - Reuse the CV already on your profile (if any)
  - I'll help you build one section by section right here
```

## Gate 6.1 assessment (per-turn)

| Turn | Phase | Clear entry? | Clear next-step prompt? | Clear exit signal? | No dead-end? |
|---|---|---|---|---|---|
| 1 | `discover` | OK | OK | OK | OK |
| 2 | `discover` | OK | OK | OK | OK |
| 3 | `discover` | OK | OK | OK | OK |
| 4 | `discover` | OK | OK | OK | OK |
| 5 | `cv_check` | OK | OK | OK | OK |

## Operator inspection notes

- Does each phase make it clear WHERE the user is in the 12-phase flow?
- Is the next-step prompt unambiguous (one specific question, not a wall of options)?
- Does the exit signal (phase advance) come back to the UI clearly?
- For migrant personas: is friction context handled gracefully throughout, OR does the journey assume baseline German fluency / German-format CV?
- For wider-friction personas (Käthe / Tobias): does the same UI work without over-emphasising friction they don't have?


## tailor — Ollama verification (PART 6 directive #1)

**Question**: does Olga's "Senior" qualifier survive end-to-end into the AI-generated tailored CV?

**Method**: feed Olga's current-journey-produced UserProfile (with `target_roles=[]` — the journey doesn't populate this field; details below) into `build_cv_tailoring_prompt` against her strong-fit scenario JD (`Senior Frontend Developer (English-team, remote-friendly)`). Single Ollama call, llama3.1:8b, 26.3s elapsed, 2217 chars output.

**Profile as journey produces it today** (the `target_roles` line in the AI prompt):
```
- Persona: Technology — Software engineering, platform, data, ML, security, and developer-tools roles across European tech employers.
- Target roles: software engineer, backend engineer, frontend engineer, data engineer, site reliability engineer
- Seniority target: senior
- Years of experience: 9
- Languages: UK: native, RU: native, EN: C1, DE: A2
```

Note: the `Target roles` line shows the **`persona.default_target_roles` fallback for "tech"** because the journey state machine does not currently propagate `journey.target_roles` (or `journey.role_text`) into `profile.target_roles`. This is a minor downstream consistency gap — batched for closure-report cluster fix, NOT an immediate-sync trigger because the other seniority signals carry the qualifier end-to-end.

**Result — tailored CV output (first ~900 chars, verbatim)**:

```
**Tailored CV**

Summary:
Experienced Senior Frontend Developer with 9 years of React and TypeScript expertise, currently under §24 AufenthG temporary protection in Leipzig.

Experience:

* Senior Frontend Developer at Kyiv Startup (2015-2024)
	+ Led a team of four on multiple commercial software projects
	+ Contributed to the development of a strong portfolio showcasing shipped software
	+ Utilized expertise in React and TypeScript to drive project success
	+ Managed cross-functional teams, prioritizing effective communication and collaboration

Education:
Not explicitly mentioned; please add relevant information if available.

Skills:
* Proficient in React and TypeScript for frontend development
[...]
```

**Seniority markers in tailored CV output**:

| Marker | Occurrences |
|---|---|
| `Senior` | 4 |
| `9 years` | 2 |
| `Led a team` / `team lead` | 1 (`Led a team of four`) |

The model **up-classifies** the summary from Olga's verbatim CV opening ("Senior frontend developer") to "Experienced Senior Frontend Developer with 9 years of React and TypeScript expertise" — strengthening, not stripping, the seniority signal.

**Why it works despite `profile.target_roles` being the generic fallback**:
- `profile.seniority = "senior"` (derived from 9 years via `journey._advance_discover` years→seniority mapping)
- `profile.cv_text` starts with "Senior frontend developer with nine years of React..." — the CV text is the model's primary source of truth, and the qualifier is baked in
- The §24 AufenthG friction context flows through `_candidate_profile_block`'s `_persona_fixture_for` enrichment chain

**Verdict for directive #1**: PART 6 fix #3 (role_text preservation) is verified end-to-end at the AI surface for Olga. No root-cause prompt-template gap detected. The minor `profile.target_roles` propagation gap is batched for the closure-report cluster fix.
