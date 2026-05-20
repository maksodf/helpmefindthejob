<!-- SPDX-License-Identifier: Apache-2.0 -->

# Journey walk — Aïcha (Tunisia → Berlin)

**Persona slug**: `aicha`  |  **Cohort**: `most-acute`
**Residency status**: §16d AufenthG (visa for purpose of recognition of foreign qualification)
**Friction notes**: Recognition decision letter expected in ~4 months; needs Anerkennung-friendly employers willing to begin onboarding before the letter lands.

## Walk-through (live HTTP API, /api/chat/message)

Each row captures one user → assistant turn with the journey-phase
transition and the wall-clock latency for that turn.

| # | User input | Phase after | Reply (truncated) | Elapsed |
|---|---|---|---|---|
| 1 | `/start` | `discover` | Got it — let's find you a job. I'll ask a few short questions, then search for you and show what fits.    **1. What kind of role are you … | 2 ms |
| 2 | `Registered nurse` | `None` | Got it: **Registered nurse**.    **2. Where?** (city, country, or "anywhere" / "remote") | 2 ms |
| 3 | `Berlin` | `None` | Noted: **Berlin**.    **3. How many years' experience do you have in this kind of role?** (a number is fine — e.g., "3" or "about 7") | 1 ms |
| 4 | `7` | `None` | **4. Which languages do you work in?** (comma-separated, e.g., "Deutsch, English") | 1 ms |
| 5 | `FR: native, AR: native, EN: B2` | `None` | Thanks. Quick summary:    - Role: **Registered nurse**    - Where: **Berlin**    - Experience: **7**    - Languages: **FR: native, AR: na… | 1 ms |

## Per-turn detail

### Turn 1 — Begin guided journey

**Input**: `/start`

**Executed**: `start_job_journey`  |  **Phase after**: `discover`  |  **Done**: `False`  |  **Elapsed**: 2 ms

**Reply**:

```
Got it — let's find you a job. I'll ask a few short questions, then search for you and show what fits.

**1. What kind of role are you looking for?** (e.g., "Pflegehelfer", "bartender", "backend engineer", "barista")
```

### Turn 2 — Answer: target role

**Input**: `Registered nurse`

**Executed**: `None`  |  **Phase after**: `None`  |  **Done**: `None`  |  **Elapsed**: 2 ms

**Reply**:

```
Got it: **Registered nurse**.

**2. Where?** (city, country, or "anywhere" / "remote")
```

### Turn 3 — Answer: target location

**Input**: `Berlin`

**Executed**: `None`  |  **Phase after**: `None`  |  **Done**: `None`  |  **Elapsed**: 1 ms

**Reply**:

```
Noted: **Berlin**.

**3. How many years' experience do you have in this kind of role?** (a number is fine — e.g., "3" or "about 7")
```

### Turn 4 — Answer: years of experience

**Input**: `7`

**Executed**: `None`  |  **Phase after**: `None`  |  **Done**: `None`  |  **Elapsed**: 1 ms

**Reply**:

```
**4. Which languages do you work in?** (comma-separated, e.g., "Deutsch, English")
```

### Turn 5 — Answer: languages

**Input**: `FR: native, AR: native, EN: B2`

**Executed**: `None`  |  **Phase after**: `None`  |  **Done**: `None`  |  **Elapsed**: 1 ms

**Reply**:

```
Thanks. Quick summary:
  - Role: **Registered nurse**
  - Where: **Berlin**
  - Experience: **7**
  - Languages: **FR: native, AR: native, EN: B2**

**Do you have a CV ready?** Three options:
  - Paste it in chat (drop the whole text)
  - Reuse the CV already on your profile (if any)
  - I'll help you build one section by section right here
```

## Gate 6.1 assessment (per-turn)

| Turn | Phase | Clear entry? | Clear next-step prompt? | Clear exit signal? | No dead-end? |
|---|---|---|---|---|---|
| 1 | `discover` | OK | OK | OK | OK |
| 2 | `None` | OK | OK | NEEDS_REVIEW | OK |
| 3 | `None` | OK | OK | NEEDS_REVIEW | OK |
| 4 | `None` | OK | OK | NEEDS_REVIEW | OK |
| 5 | `None` | OK | OK | NEEDS_REVIEW | OK |

## Operator inspection notes

- Does each phase make it clear WHERE the user is in the 12-phase flow?
- Is the next-step prompt unambiguous (one specific question, not a wall of options)?
- Does the exit signal (phase advance) come back to the UI clearly?
- For migrant personas: is friction context handled gracefully throughout, OR does the journey assume baseline German fluency / German-format CV?
- For wider-friction personas (Käthe / Tobias): does the same UI work without over-emphasising friction they don't have?

