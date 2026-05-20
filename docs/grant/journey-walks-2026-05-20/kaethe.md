<!-- SPDX-License-Identifier: Apache-2.0 -->

# Journey walk — Käthe (German, nursing re-entrant)

**Persona slug**: `kaethe`  |  **Cohort**: `wider-friction`
**Residency status**: German citizen (Freizügigkeit not applicable)
**Friction notes**: 12-year clinical absence: digital patient-record systems, electronic medication management, infection-control protocols, mandatory CE hours all changed since 2013. Hospitals expect a Wiedereinstiegsprogramm or Auffrischung course; her old CV reads as obsolete for 2026 conventions.

## Walk-through (live HTTP API, /api/chat/message)

Each row captures one user → assistant turn with the journey-phase
transition and the wall-clock latency for that turn.

| # | User input | Phase after | Reply (truncated) | Elapsed |
|---|---|---|---|---|
| 1 | `/start` | `discover` | Got it — let's find you a job. I'll ask a few short questions, then search for you and show what fits.    **1. What kind of role are you … | 1 ms |
| 2 | `Krankenschwester (Wiedereinstieg)` | `discover` | Got it: **Krankenschwester (Wiedereinstieg)**.    **2. Where?** (city, country, or "anywhere" / "remote") | 1 ms |
| 3 | `Berlin` | `discover` | Noted: **Berlin**.    **3. How many years' experience do you have in this kind of role?** (a number is fine — e.g., "3" or "about 7") | 1 ms |
| 4 | `14` | `discover` | **4. Which languages do you work in?** (comma-separated, e.g., "Deutsch, English") | 1 ms |
| 5 | `DE: native, EN: B1-clinical` | `cv_check` | Thanks. Quick summary:    - Role: **Krankenschwester (Wiedereinstieg)**    - Where: **Berlin**    - Experience: **14**    - Languages: **… | 1 ms |

## Per-turn detail

### Turn 1 — Begin guided journey

**Input**: `/start`

**Executed**: `start_job_journey`  |  **Phase after**: `discover`  |  **Done**: `False`  |  **Elapsed**: 1 ms

**Reply**:

```
Got it — let's find you a job. I'll ask a few short questions, then search for you and show what fits.

**1. What kind of role are you looking for?** (e.g., "Pflegehelfer", "bartender", "backend engineer", "barista")
```

### Turn 2 — Answer: target role

**Input**: `Krankenschwester (Wiedereinstieg)`

**Executed**: `None`  |  **Phase after**: `discover`  |  **Done**: `None`  |  **Elapsed**: 1 ms

**Reply**:

```
Got it: **Krankenschwester (Wiedereinstieg)**.

**2. Where?** (city, country, or "anywhere" / "remote")
```

### Turn 3 — Answer: target location

**Input**: `Berlin`

**Executed**: `None`  |  **Phase after**: `discover`  |  **Done**: `None`  |  **Elapsed**: 1 ms

**Reply**:

```
Noted: **Berlin**.

**3. How many years' experience do you have in this kind of role?** (a number is fine — e.g., "3" or "about 7")
```

### Turn 4 — Answer: years of experience

**Input**: `14`

**Executed**: `None`  |  **Phase after**: `discover`  |  **Done**: `None`  |  **Elapsed**: 1 ms

**Reply**:

```
**4. Which languages do you work in?** (comma-separated, e.g., "Deutsch, English")
```

### Turn 5 — Answer: languages

**Input**: `DE: native, EN: B1-clinical`

**Executed**: `None`  |  **Phase after**: `cv_check`  |  **Done**: `None`  |  **Elapsed**: 1 ms

**Reply**:

```
Thanks. Quick summary:
  - Role: **Krankenschwester (Wiedereinstieg)**
  - Where: **Berlin**
  - Experience: **14**
  - Languages: **DE: native, EN: B1-clinical**

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

