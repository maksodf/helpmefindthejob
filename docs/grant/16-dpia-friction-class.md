# Data Protection Impact Assessment (DPIA) — friction-class classification feature

Date: 2026-05-21 (PART 4 Loop #76 sub-piece (f))
Status: **draft** — operator-reviewable, intended for the EU AI Act
compliance pack + GDPR Article 35 documentation set
License: Apache 2.0
Owner: Helpmefindthejob maintainer

---

## 1. What this document is

A Data Protection Impact Assessment for the **friction-class
classification** feature shipped in Phase 1 (Loops 10.1–10.3,
2026-05-20) and polished in Phase 2 #76 (sub-pieces a + b + d + e,
2026-05-21).

GDPR Article 35 requires a DPIA when processing is "likely to result
in a high risk to the rights and freedoms of natural persons." The
friction-class feature processes the user's CV text and produces a
classification slug indicating which of seven friction-class patterns
the user appears to be in (§16d Anerkennungsweg, EU Blue Card,
§24 humanitarian protection, §4 AsylG, EU citizen, Wiedereinstieg,
Quereinstieg). Several of those categories correlate with **special
category data** under GDPR Article 9 — specifically immigration /
residency status, health-profession context, and asylum status.

This document is the operator-reviewable draft. The operator (Fouad)
adapts it to the institutional wrapper (The Commons Conservancy
Programme review) and signs off before the project's first reference
deployment (Germany, Week 2 grant timeline per CLAUDE.md).

---

## 2. Processing description

### What is processed

| Item | Description |
|---|---|
| Input | The user's CV text (provided by the user via paste in the chat OR assembled from the 5-question sectional CV-build flow). |
| Inference | A purely **deterministic** classifier (`company_discovery/friction_classifier.py`) substring-matches the CV against curated marker patterns. **No AI / no third-party processor / no statistical learning.** Two-stage algorithm: STRONG_MARKERS (e.g. `§16d AufenthG`, `EU Blue Card`, `§24 AufenthG`, `§4 AsylG`, `Wiedereinstieg`, `Quereinstieg`) take precedence; SCORED_PATTERNS (soft markers like `Pflegehelfer`, `nurse`, `mechanical engineer`) fall back. Alphabetical tie-break for ties. |
| Output | One of 8 values: `aicha` / `yusuf` / `olga` / `mahmoud` / `maria` / `kaethe` / `tobias` / `""` (unclassified). |
| Storage | `UserProfile.friction_class` field in the project's sqlite database. Persisted alongside other profile fields. |
| Telemetry | One internal analytics event per classification with `resolved` slug + `confidence` (strong/scored/none) + `match_count` + `tied_slugs` (Phase 2 #76(b)) + `source` (paste / cv_build_via_chat / reclassify_button / chat_change / chat_skip). The event payload is the slug + counts, **never the CV text or any verbatim CV excerpt**. |

### Where the classification happens

- **In-process**: the classifier runs in the same Python process that
  serves the user's request. No network call, no third-party API.
- **No egress**: the CV text used as input never leaves the
  deployment's process. The friction_class output **does** travel
  alongside the CV when the user invokes an AI call (see §7 below)
  — that's the only path where any classifier-derived value leaves
  the deployment.

### How the classifier is triggered

Three trigger paths exist post-Phase 2 #76:

1. **Paste-branch** (`company_discovery/journey.py:1448`): when the
   user pastes their CV into the chat, the journey classifier hook
   runs `classify_with_telemetry(msg)` and stores the result on
   `UserProfile.friction_class`.
2. **CV-build-via-chat completion** (sub-piece e, journey.py:1485):
   when the 5-question sectional flow assembles the CV text, the
   classifier runs on the assembled output.
3. **Explicit user actions**: re-classify button (Settings →
   Friction-class card → "Re-classify from current CV") and chat
   tokens (`/friction <slug>` / `change classification` /
   `skip classification`).

---

## 3. Purpose

The friction-class slug routes downstream UX so that users facing
specific bureaucratic / regulatory frictions get appropriate help:

- **§16d Anerkennungsweg (Aïcha)**: search affordances mention
  Anerkennung-friendly employers; AI prompts inject Anerkennung context
  so cover letters reference the friction honestly.
- **EU Blue Card (Yusuf)**: visa-portability assumption; no
  Ausländerbehörde caveat on location-widening affordance
  (`company_discovery/widening.py:LOCATION_CAVEAT_TEXT`).
- **§24 humanitarian / §4 AsylG (Olga / Mahmoud)**: status-aware
  framing; the system never invents legal advice, always directs to
  BAMF / Ausländerbehörde / Migrationsberatungsstelle for class A
  legal questions per the source-class hierarchy doctrine
  ([14-source-class-hierarchy.md](14-source-class-hierarchy.md)).
- **EU citizen (Maria)**: no visa constraints; standard widening
  affordances.
- **Wiedereinstieg (Käthe)**: career-break-aware AI prompts; CV
  tailoring foregrounds re-entry skills.
- **Quereinstieg (Tobias)**: career-changer framing; transferable-
  skill mapping in tailoring.

**The classification's purpose is BENEFICIARY**: improve outcomes for
users in legally-fragile situations who'd otherwise get generic
advice. This aligns with the project's stated civic-commons mission
(CLAUDE.md: "an open-source EU-wide civic employment commons … puts
that knowledge directly into the hands of anyone facing structural
friction in the European labor market").

---

## 4. Lawful basis under GDPR

### Primary basis

**Article 6(1)(b) — Performance of a contract**: the user signs up to
use Helpmefindthejob, which is contractually offered as a
friction-aware tool. Routing the UX based on the user's documented
friction context is necessary to deliver the service the user
requested.

### Secondary basis for special category data

Some friction-class outputs correlate with Article 9 special category
data:
- Immigration / residency status (Articles 9 / national security
  concerns vary by jurisdiction — Germany treats this as sensitive
  but not §9 SCD strictly; treat as elevated-risk in this DPIA)
- Health-profession context (Aïcha + Maria are nurses; doesn't
  itself reveal health data **about the user**, but reveals
  professional context)
- Asylum context (Mahmoud's §4 AsylG slug — sensitive)

**Lawful basis for SCD processing**: **Article 9(2)(a) — Explicit
consent**. The user voluntarily provides their CV (which contains
the underlying markers) AND the
[transparency notice](../../compliance/transparency-notice.md) section
"Friction-class inference (deterministic, internal)" explicitly
discloses the classification, its purpose, and the user's rights.
Users can clear the friction_class field any time (Settings card +
chat `/skip-friction` command).

---

## 5. Data minimisation

### What is NOT stored

- The CV text used for classification is stored separately
  (`UserProfile.cv_text`) **for the user's own use** (CV editing,
  AI cover-letter drafts). The classification step does not create a
  copy of the CV.
- The exact patterns that matched are **not stored** — only the
  resolved slug + counts. We can't reconstruct which marker fired
  from the persisted state.
- No verbatim CV excerpts ever appear in audit logs, telemetry, or
  the friction_class field.

### What IS stored

- One slug per user, kept up-to-date on every classification trigger
  (paste / build-completion / manual change). Re-classification
  semantics: unconditional overwrite, so a re-paste that doesn't
  classify clears the slug (operator-spec: stale > none).

### Retention

Friction-class slug retention follows the same lifecycle as the
parent `UserProfile`. When a user deletes their account
(`chat_handler_delete_account` in `app.py`), the slug is deleted
along with the profile. There is no separate retention policy for
the slug beyond the profile's.

---

## 6. Data subjects

- **Helpmefindthejob users**: voluntarily signed-up, provided their
  CV.
- **No third-party data subjects**: the classifier processes only
  the signed-up user's own CV. CVs mentioning other people (e.g. "I
  managed a team of X") are processed for the signed-up user's
  classification only; the other people's names are not extracted
  or stored as separate records.

---

## 7. Recipients of the friction_class output

| Recipient | Why | Egress? |
|---|---|---|
| The user themselves | Settings → Friction-class card displays the slug; chat reply suffix on paste mentions the inferred class | No — within deployment |
| AI provider (when invoked) | The user's CV + the resolved friction_class context is included in AI prompts (`analysis.py` friction-context wiring) so the AI knows e.g. "this is an Aïcha §16d candidate". When the user has chosen Ollama (local AI), no egress. When the user has chosen a cloud AI (OpenAI / Anthropic / etc.), the slug **does** egress as part of the prompt. | **Yes**, when the user explicitly chose a cloud AI provider. Disclosed in the transparency notice's "What data is sent to the AI" section + the "Honesty matrix" doctrine ([15-ai-provider-honesty-matrix.md](15-ai-provider-honesty-matrix.md)). |
| External civic agents (MCP composability) | `get_user_profile_for_consent` MCP tool can include the slug under the "employment" scope. **Only when the user has explicitly consented to share** (the MCP tool emits the consent receipt; an external agent reading the profile sees consent provenance). | Optional / consent-gated |
| Internal analytics | Server-side analytics events; payloads contain slug + counts only, never CV text. Used for production accuracy refinement (Phase 2 #76 sub-piece c). | No — within deployment |

**No automated decision-making with legal effect**: the friction_class
slug routes UX (which affordances to show, which prompt context to
inject) but **does not make decisions ABOUT the user** (no
employment screening, no automated rejection, no scoring).

---

## 8. Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Misclassification — user labeled with a class they're not in | Medium (deterministic classifier has edge cases) | Low–Medium (downstream UX shows generic / off-target affordances) | (a) Soft / non-gating: user proceeds with normal flow regardless. (b) Phase 2 #76(a) chat affordance lets user override via `change classification` / `skip classification`. (c) Phase 2 #76(d) Settings card lets user re-classify or clear. (d) Phase 2 #76(b) reconciliation banner surfaces persona/friction mismatch. (e) Phase 2 #76(b) tied_slugs surfaces ambiguous classifications so the user can override. |
| Sensitive-class data persisted | Medium (slug is one of 8 values, some are sensitive) | High (residency / asylum status is GDPR Article 9) | (a) Stored on the user's own profile, deletable by the user. (b) Never aggregated, never shared without consent. (c) Transparency notice discloses both the inference and the user's control over it. (d) Account deletion removes the slug. (e) DPIA-equivalent privacy review committed as part of grant compliance pack (this document). |
| Data egress to cloud AI | Low if user picks local AI (Ollama) | Medium if user picks cloud AI | (a) AI provider choice is the user's, defaulting to "manual" (no AI). (b) Honesty matrix ([15-ai-provider-honesty-matrix.md](15-ai-provider-honesty-matrix.md)) discloses egress at the picker, in EN + DE. (c) Project's "no silent rerouting" doctrine: system never sends to a provider the user didn't pick. (d) AI Act Article 12 audit log records every AI invocation (ai_invocation event with response_hash + duration_ms + outcome). |
| Pattern fragility — classifier patterns drift relative to real-world CV vocabulary | Medium (real users may not write `§16d AufenthG` verbatim) | Low (drift produces misclassification, not data leak) | Phase 2 #76(c) — post-deployment telemetry-driven pattern refinement. Backlog item until production telemetry is available. |
| Discrimination — friction-class biases search results | Low (deterministic classifier; same friction class → same affordances by design) | High (would violate non-discrimination principles) | (a) PART 5 bias-methodology suite tested fit-scoring across the 7-persona panel (Aïcha / Yusuf / Olga / Mahmoud / Maria / Käthe / Tobias) and asserted within-tolerance band scoring. (b) `tests/test_widening.py` regression-pins the visa-aware persona ordering so e.g. visa-constrained personas see relocation caveats. (c) No persona's friction-class denies a user any feature; all features are available to all classes. |
| Bias amplification in AI prompts when friction_class is injected | Medium | Medium | PART 8 source-class hierarchy doctrine: AI prompts treat friction_class as class-G inference (must be grounded in class-E user CV/JD when surfaced in user-facing output). Cover-letter prompts inject the friction context (residency_status / friction_notes) only when the user's CV documents it; the AI is constrained to weave it in only where it materially helps the application (motivation_letter.py:121 friction_clause). |

---

## 9. Special category data assessment

The friction-class slug **infers** sensitive context but **does not
create** new sensitive data. The user's CV already contains the
markers (`§16d AufenthG`, `Anerkennung`, etc.); the classifier just
indexes them. From a GDPR-Article-9-creation perspective, the
inference does not generate new SCD beyond what the user provided.

That said, the *organisation* of those markers into a class slug is
itself a low-risk data-organisation operation that GDPR Article 9
attaches to. We treat the slug as elevated-risk per §4 and §7 above.

---

## 10. Necessity and proportionality

### Why this processing is necessary

Without friction-class routing, the system would either:

(a) **Treat everyone the same** — generic advice that fails the
acute-friction users (visa-constrained migrants, asylum, etc.) the
project's mission targets.

(b) **Ask the user to pick a persona explicitly** at sign-up —
imposes a UX burden + relies on users self-classifying without
domain expertise.

The deterministic classifier path is the **most data-minimising** way
to deliver friction-aware UX: it uses only data the user voluntarily
provided (CV), runs in-process (no egress), and is fully overridable
by the user.

### Why this processing is proportionate

The slug is a single low-cardinality value (8 possibilities including
empty). It powers UX routing, not decisions about the user. It is
fully user-controllable (re-classify, change, clear). The
transparency notice + honesty matrix + this DPIA together make the
user fully informed about the inference.

---

## 11. Consultation

| Party | Status |
|---|---|
| Data subjects | Transparency notice + Settings UI + chat affordances let users see the inference, override it, or opt out. Phase 2 follow-on: user-facing FAQ section addressing "what is friction-class classification?" — pending. |
| Data Protection Officer | The Commons Conservancy programme review process (operator action, Week 2 grant timeline) is the appropriate DPO consultation route. |
| Supervisory authority | Not required pre-deployment for this risk level. Operator engages BfDI / state-level DPA if and when a deployer requests it. |

---

## 12. Compliance audit notes

### Article 12 audit log

Friction-class classification events emit `friction_class_classified`
analytics events. Source tags distinguish the trigger:
- `paste` — user pasted their CV
- `cv_build_via_chat` — user completed the sectional build
- `reclassify_button` — Settings → Re-classify
- `chat_change` — user typed `/friction <slug>` or "change classification"
- `chat_skip` — user typed `/skip-friction` or "skip classification"

`friction_class_cleared` events emit on the clear path with the
prior slug + source tag (`clear_button` / `chat_skip`).

These events live alongside the AI Act Article 12 `ai_invocation`
+ `mcp_tool_invocation` events in the same audit-log emitter.

### AI Act Article 50 transparency

The transparency notice + this DPIA + the source-class hierarchy
+ the honesty matrix collectively satisfy Article 50 for the
friction-class feature:
- The user is told that AI-derived inferences and deterministic
  inferences both exist (transparency notice)
- The classifier is named, the algorithm is described (this DPIA)
- The user's controls (override / clear / opt-out) are documented
  (transparency notice + Settings card UI)

---

## 13. What this document does NOT cover

- **The wider AI Act compliance pack** — see
  [10-ai-act-compliance.md](10-ai-act-compliance.md).
- **The source-class hierarchy doctrine for all claims** — see
  [14-source-class-hierarchy.md](14-source-class-hierarchy.md).
- **The AI provider honesty matrix** — see
  [15-ai-provider-honesty-matrix.md](15-ai-provider-honesty-matrix.md).
- **The cost-saving doctrine** — see
  [08-cost-saving-doctrine.md](08-cost-saving-doctrine.md).
- **The wider GDPR audit** (other data processing in the system) —
  this document is scoped to the friction-class classification
  feature only.

---

## 14. Sign-off

| Role | Name | Date | Notes |
|---|---|---|---|
| DPIA drafter | Coding agent (Claude Opus 4.7 1M) | 2026-05-21 | Draft for operator review |
| Operator review | Fouad | _pending_ | Adapts to institutional wrapper, signs off pre-deployment |
| The Commons Conservancy programme review | _pending_ | _Week 2 grant timeline_ | Programme review process |
| First-deployer DPO acknowledgment | _pending per deployer_ | — | Each deployer reviews + acknowledges in their own context |

---

## Cross-references

- [`10-ai-act-compliance.md`](10-ai-act-compliance.md) — EU AI Act
  compliance pack (Article 12 audit log, Article 50 transparency).
- [`14-source-class-hierarchy.md`](14-source-class-hierarchy.md) —
  7-level source-class hierarchy (this DPIA's class-A / class-G
  references map onto it).
- [`15-ai-provider-honesty-matrix.md`](15-ai-provider-honesty-matrix.md)
  — per-provider tradeoffs (the AI-egress risk in §7 above maps to
  this matrix).
- `compliance/transparency-notice.md` — user-facing transparency notice
  ("Friction-class inference (deterministic, internal)" section).
- `company_discovery/friction_classifier.py` — the implementation
  (STRONG_MARKERS + SCORED_PATTERNS + ClassificationResult).
- PART 5 bias-methodology: 7-persona × 10-scenario fit-scoring
  bias tests + `test_bias_methodology.py`.
- PART 6 Bug F Option B (Loops 10.1-10.3): Phase 1 substrate that
  this DPIA reviews.

---

## Append log

- **2026-05-21**: Initial draft published as Phase 2 #76 sub-piece (f).
  Operator review + The Commons Conservancy programme review pending.
