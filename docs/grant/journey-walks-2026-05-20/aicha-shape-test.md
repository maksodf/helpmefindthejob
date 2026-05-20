<!-- SPDX-License-Identifier: Apache-2.0 -->

# Aïcha shape-test — full 12-phase journey via live HTTP API

Per operator directive 2026-05-20: drive Aïcha turn-by-turn,
capture verbatim, flag every PREDICTED-vs-ACTUAL divergence.
Shape-test informs the refactor of `scripts/journey_walk.py`
to capture exactly what the live system surfaces (not what
the code-read predicted).

**Persona**: Aïcha (Tunisia → Berlin) (aicha, most-acute)
**Provider**: Ollama llama3.1:8b at http://127.0.0.1:11434

## Per-turn capture

| # | Predicted phase | Actual phase | Surprise? | Input (truncated) | Elapsed |
|---|---|---|---|---|---|
| 1 | `discover` | `discover` | no | `/start` | 2 ms |
| 2 | `discover` | `discover` | no | `Registered nurse` | 2 ms |
| 3 | `discover` | `discover` | no | `Berlin` | 1 ms |
| 4 | `discover` | `discover` | no | `7` | 1 ms |
| 5 | `cv_check` | `cv_check` | no | `FR: native, AR: native, EN: B2` | 1 ms |
| 6 | `preferences` | `inspire` | **YES** | `Aïcha (Tunisia → Berlin)  Email: aicha.shape-test@example.tes…` | 9 ms |
| 7 | `search` | `preferences` | **YES** | `none` | 2 ms |
| 8 | `drill` | `done` | **YES** | `1` | 2405 ms |
| 9 | `tailor` | `done` | **YES** | `1` | 7 ms |
| 10 | `tailor` | `done` | **YES** | `/tailor` | 2 ms |
| 11 | `letter` | `done` | **YES** | `/letter` | 1 ms |
| 12 | `cv_consult` | `done` | **YES** | `/consult` | 1 ms |

## Per-turn detail

### Turn 1 — Begin guided journey

**Predicted phase**: `discover`  |  **Actual phase**: `discover`  |  **Surprise?**: no
**Executed**: `start_job_journey`  |  **Elapsed**: 2 ms

**Input**:
```
/start
```

**Reply** (verbatim):
```
Got it — let's find you a job. I'll ask a few short questions, then search for you and show what fits.

**1. What kind of role are you looking for?** (e.g., "Pflegehelfer", "bartender", "backend engineer", "barista")
```

**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "result": {
    "ok": true,
    "message": "Got it — let's find you a job. I'll ask a few short questions, then search for you and show what fits.\n\n**1. What kind of role are you looking for?** (e.g., \"Pflegehelfer\", \"bartender\", \"backend engineer\", \"barista\")",
    "journeyPhase": "discover",
    "done": false
  }
}
```

### Turn 2 — Answer role

**Predicted phase**: `discover`  |  **Actual phase**: `discover`  |  **Surprise?**: no
**Executed**: `None`  |  **Elapsed**: 2 ms

**Input**:
```
Registered nurse
```

**Reply** (verbatim):
```
Got it: **Registered nurse**.

**2. Where?** (city, country, or "anywhere" / "remote")
```

**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 3 — Answer location

**Predicted phase**: `discover`  |  **Actual phase**: `discover`  |  **Surprise?**: no
**Executed**: `None`  |  **Elapsed**: 1 ms

**Input**:
```
Berlin
```

**Reply** (verbatim):
```
Noted: **Berlin**.

**3. How many years' experience do you have in this kind of role?** (a number is fine — e.g., "3" or "about 7")
```

**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 4 — Answer years

**Predicted phase**: `discover`  |  **Actual phase**: `discover`  |  **Surprise?**: no
**Executed**: `None`  |  **Elapsed**: 1 ms

**Input**:
```
7
```

**Reply** (verbatim):
```
**4. Which languages do you work in?** (comma-separated, e.g., "Deutsch, English")
```

**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 5 — Answer languages — should transition to cv_check

**Predicted phase**: `cv_check`  |  **Actual phase**: `cv_check`  |  **Surprise?**: no
**Executed**: `None`  |  **Elapsed**: 1 ms

**Input**:
```
FR: native, AR: native, EN: B2
```

**Reply** (verbatim):
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

**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 6 — cv_check: paste her CV — should chain into inspire

**Predicted phase**: `preferences`  |  **Actual phase**: `inspire`  |  **Surprise?**: **YES**
**Executed**: `None`  |  **Elapsed**: 9 ms

**Input**:
```
Aïcha (Tunisia → Berlin)
Email: aicha.shape-test@example.test
Phone: +49 30 0000-000
Location: Berlin
Residency status: §16d AufenthG (visa for purpose of recognition of foreign qualification)

Profile: Registered nurse with seven years of hospital experience in Tunisia, including two years in geriatric care. French- and Arabic-native; English B2; German B1 working toward B2. Currently in §16d Anerkennung process with BIBB / Anabin.

Skills: Patient assessment, Geriatric care, Medication administration, Care planning, Clinical documentation (Lebenslauf-format)

Languages: FR: native, AR: native, EN: B2, DE: B1

Friction context: Recognition decision letter expected in ~4 months; needs Anerkennung-friendly employers willing to begin onboarding before the letter lands.

```

**Reply** (verbatim):
```
Got it — captured **777 chars** of CV. Moving on to suggestions.

_(I'm working without an AI right now — these are templated from your persona defaults.)_

Based on what you've told me, you'd also be competitive for:
  - Senior Registered nurse
  - Lead Registered nurse
  - Assistant Registered nurse

**Want me to search those too?** Reply:
  - **yes** to add all
  - **no** to stick with just your stated role
  - or paste a comma-separated list of the ones you want
```

**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 7 — preferences: 'none' (no deal-breakers)

**Predicted phase**: `search`  |  **Actual phase**: `preferences`  |  **Surprise?**: **YES**
**Executed**: `None`  |  **Elapsed**: 2 ms

**Input**:
```
none
```

**Reply** (verbatim):
```
Locked in: searching for **Registered nurse, none**.

**Any deal-breakers?** Reply with any of:
  - **remote** if remote is required
  - **min 50k** (or any salary floor)
  - **startup / mid / enterprise** for company size
  - **none** / **skip** to move on
```

**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": null,
  "jobs": null,
  "categories": null,
  "navigateTo": null
}
```

### Turn 8 — After search: pick first category

**Predicted phase**: `drill`  |  **Actual phase**: `done`  |  **Surprise?**: **YES**
**Executed**: `None`  |  **Elapsed**: 2405 ms

**Input**:
```
1
```

**Reply** (verbatim):
```
Searching for **Registered nurse, none** in **Berlin**…

No matching jobs right now. Try widening the location or relaxing the role. Type `find a job` to start a new search.
```

**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "invoked": null,
  "letter": null,
  "suggestions": null,
  "totalJobs": 0,
  "jobs": [],
  "categories": [],
  "navigateTo": null
}
```

### Turn 9 — After drill: pick first job for tailor/letter offer

**Predicted phase**: `tailor`  |  **Actual phase**: `done`  |  **Surprise?**: **YES**
**Executed**: `None`  |  **Elapsed**: 7 ms

**Input**:
```
1
```

**Reply** (verbatim):
```
I'm not sure what you mean by that — here's what I can do right now:
  - **find a job** — I'll ask a few questions and search for you
  - **add a company** like *"watch Charité, career page karriere.charite.de"*
  - **build my CV** — guided sectional walk

Or type **help** for the full command list.
```

### Turn 10 — Tailor: /tailor command for the picked job

**Predicted phase**: `tailor`  |  **Actual phase**: `done`  |  **Surprise?**: **YES**
**Executed**: `None`  |  **Elapsed**: 2 ms

**Input**:
```
/tailor
```

**Reply** (verbatim):
```
Which imported job? (paste the id from the Jobs queue)
```

**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "awaiting": "importedJobId"
}
```

### Turn 11 — Letter: /letter command

**Predicted phase**: `letter`  |  **Actual phase**: `done`  |  **Surprise?**: **YES**
**Executed**: `None`  |  **Elapsed**: 1 ms

**Input**:
```
/letter
```

**Reply** (verbatim):
```
Generating a tailored CV for job **/letter**. Confirm?
```

**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "awaitingConfirmation": true,
  "pendingArgs": {
    "importedJobId": "/letter"
  }
}
```

### Turn 12 — CV consult: /consult command

**Predicted phase**: `cv_consult`  |  **Actual phase**: `done`  |  **Surprise?**: **YES**
**Executed**: `None`  |  **Elapsed**: 1 ms

**Input**:
```
/consult
```

**Reply** (verbatim):
```
Generating a tailored CV for job **/letter**. Confirm?
```

**Non-standard response fields** (anything beyond `reply` / `journeyPhase` / `session` / `executed`):
```json
{
  "awaitingConfirmation": true,
  "pendingArgs": {
    "importedJobId": "/letter"
  }
}
```


## Surprise summary (PART 6 directive — feeds the refactor)

**7 divergences** observed:

- **Turn 6** (cv_check: paste her CV — should chain into inspire): predicted `preferences`, actual `inspire`.
- **Turn 7** (preferences: 'none' (no deal-breakers)): predicted `search`, actual `preferences`.
- **Turn 8** (After search: pick first category): predicted `drill`, actual `done`.
- **Turn 9** (After drill: pick first job for tailor/letter offer): predicted `tailor`, actual `done`.
- **Turn 10** (Tailor: /tailor command for the picked job): predicted `tailor`, actual `done`.
- **Turn 11** (Letter: /letter command): predicted `letter`, actual `done`.
- **Turn 12** (CV consult: /consult command): predicted `cv_consult`, actual `done`.
