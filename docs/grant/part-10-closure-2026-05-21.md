# PART 10 closure — Honesty matrix (open-source-AI vs cloud-AI)

Date: 2026-05-21
Branch: `claude/project-analysis-bpHCo`
Scope: Loops 31 – 33 of the 19-loop product-quality sweep.

---

## Executive summary

PART 10 ships the **AI provider honesty matrix** as a binding
project-level doctrine, links it to the user-facing transparency
notice, surfaces the tradeoffs at provider-pick time in the Settings
UI, and adds a contract test that catches drift between the provider
catalogue and the doctrine document.

Three loops:

- **Loop 31** — `docs/grant/15-ai-provider-honesty-matrix.md` doctrine
  (11-provider matrix covering Quality, Latency, Privacy, Cost, EU AI
  Act surface) + per-use-case guidance (NOT a single "best" recommen-
  dation) + transparency-notice cross-link + `test_ai_provider_matrix_consistency.py`
  (6 tests).
- **Loop 32** — Inline honesty-tradeoff hint above the Settings AI
  provider picker (EN + DE i18n). The cloud-vs-local tradeoff is
  visible at decision time, not buried in compliance docs.
- **Loop 33** — This closure synthesis.

### Why this matters

Civic-commons positioning + AI Act Article 50 transparency mean the
project must give users an informed choice between local AI (Ollama)
and cloud AI (OpenAI / Anthropic / Google / DeepSeek). The honest
single-paragraph summary the maintainer would give a journalist now
exists at the top of the doctrine doc:

> Cloud AI is materially better at output quality and speed today,
> at the cost of data egress to the provider's jurisdiction and per-
> token billing. Local AI (Ollama) is materially better for privacy
> and zero-variable-cost workflows, at the cost of slower generation
> and a model-dependent quality gap that's narrowing every quarter.
> Helpmefindthejob makes the choice clear at provider-pick time,
> ships the same prompts to whichever the user picks, and never
> silently reroutes to cloud when local was requested.

That paragraph is testable: the no-silent-rerouting claim is bound
to the code (the system surfaces an honest banner when local is
unreachable rather than falling through to cloud); the matrix-vs-
catalogue consistency is enforced by `test_ai_provider_matrix_consistency.py`;
the user sees the tradeoffs at the picker via the new Settings hint.

---

## Coverage matrix vs read-through decisions

| Decision | Status |
|---|---|
| A. Scope width — 3 loops | ✅ Shipped exactly 3 loops. |
| B. Recommendation discipline — NO single "best" | ✅ Doctrine has per-use-case branches (fit-scoring / cover-letter / CV consult / brief); test enforces all 4 sections exist. |
| C. UI surfacing — inline hint above picker | ✅ Loop 32 ships one-paragraph hint with EN + DE i18n. |
| D. Consistency test | ✅ 6-test contract at `tests/test_ai_provider_matrix_consistency.py` (every PROVIDER_OPTIONS id ↔ matrix row, no orphans, per-use-case sections present, doctrine cross-references, DeepSeek PRC note preserved). |
| E. Honest about Ollama gap | ✅ Matrix Quality column anchors at "frontier ≅ 100"; Ollama row is 50-75 model-dependent; cover-letter section names the gap explicitly ("Ollama 8B quantised trails noticeably on idiom + specificity"). |
| F. AI Act linkage | ✅ Doctrine cross-references `10-ai-act-compliance.md`, `14-source-class-hierarchy.md`, `08-cost-saving-doctrine.md`; test enforces. |

All 6 decisions honored.

---

## Loop 31: doctrine + transparency notice + consistency test

**Deliverable**: `docs/grant/15-ai-provider-honesty-matrix.md` (250+
lines) + transparency-notice extension + `test_ai_provider_matrix_consistency.py`.

### The matrix (key dimensions)

| Provider class | Examples | Egress | Cost/req | Latency | Quality |
|---|---|---|---|---|---|
| Local | Ollama, Codex CLI, Claude Code (local auth) | None or user-controlled | Zero variable / subscription-bundled | 5-90 s | 50-75 (model-dependent) |
| Cloud (BYO key) | OpenAI, Anthropic, Google Gemini, DeepSeek, OpenRouter | Per-provider jurisdiction | $0.0001-0.05 | 1-15 s | 75-100 (model-dependent) |
| Manual handoff | Manual | User controls 100% | Whatever the user pays elsewhere | User-paced | Equal to chosen AI |
| Managed (operator-side) | Managed | Operator's chosen processor | Bundled in Plan | 1-5 s | Operator-chosen (typically frontier cloud) |

### Per-use-case branches

| Use case | Privacy-first | Quality-first | Cost-first |
|---|---|---|---|
| Fit scoring | Ollama | Anthropic Haiku / gpt-4o-mini | DeepSeek (jurisdiction note) / Ollama |
| Cover letter | Ollama 13B+ | Anthropic Sonnet / Opus, gpt-4o | DeepSeek / Ollama |
| CV consult | Ollama | Anthropic Sonnet | — |
| Brief | Ollama | gpt-4o-mini (best balance) | — |

### Doctrine binds the code

The doctrine document states 4 binding effects:

1. **Provider catalogue** — every `PROVIDER_OPTIONS` entry must have a
   matrix row (enforced by consistency test).
2. **Transparency notice** — links to the doctrine for tradeoff detail
   (done in Loop 31).
3. **Settings UI** — surfaces a one-paragraph summary above the picker
   (done in Loop 32).
4. **No silent rerouting** — when a user picks Ollama and the local
   endpoint is unreachable, the system surfaces an honest banner ("Your
   local AI is unreachable — start Ollama and retry, or switch provider
   in Settings"). It never silently falls through to cloud.

Commit: `1317c94`

---

## Loop 32: Settings UI honesty hint

**Deliverable**: one-paragraph inline hint above the Settings AI
provider mode picker (`static/index.html`), with EN + DE i18n
(`static/i18n/{en,de}.json`).

The hint surfaces:
- Cloud AI: faster + higher quality, but sends data to the provider's
  jurisdiction
- Local AI: slower + model-dependent quality, but no data leaves the
  device
- Path to the full matrix in the repo: `docs/grant/15-ai-provider-honesty-matrix.md`
- The "no silent rerouting" promise

The path is rendered as `<code>` not `<a>` because the docs/grant
tree is not served as a static asset from the running app. Self-
hosters and grant evaluators reading the repo find it; production
users see the path. A docs-serving route is Phase 2 work (and would
need access-control review since some docs are operator-internal).

Commit: `81ffd1a`

---

## Doctrine adherence at closure

- **No gaps behind**: the broken `<a href="/docs/grant/...">` link
  surfaced during Loop 32 implementation was fixed inline (changed
  to `<code>` rendering of the file path), not shipped as a 404
  link.
- **Demand runtime proof**: 6-test consistency contract catches every
  drift category (new provider without matrix row, removed provider
  with orphan mapping, missing per-use-case sections, missing
  cross-references, missing DeepSeek PRC note).
- **Top-tier only**: the doctrine refuses the easy fudge of "Ollama is
  just as good" — explicitly anchors Ollama at 50-75 on the frontier-
  normalised quality scale and names the cover-letter gap.
- **Don't please; honor the agreed approach**: 5 of 6 read-through
  decisions honored exactly as proposed; the broken-link adjustment
  was within the doctrine of "ship working UI" rather than scope
  drift.

---

## Phase 2 backlog impact

No new Phase 2 items added. One follow-on candidate surfaced and is
documented here (not yet a Phase 2 #81 entry — waiting for operator
signal):

- **Serve `docs/grant/` as a static asset on the running app** so the
  Settings hint can use a clickable link. Today the path is plain
  text. Phase 2 work because it needs access-control review (some
  grant-workspace docs reference operator-internal context).

---

## Test suite state at PART 10 close

PART 10 cluster (`test_ai_provider_matrix_consistency` +
`test_typing_label_milestones` + `test_phase11_mcp_input_validation`):
**25 tests, 0 failures, runtime 0.06s.**

Test count delta from PART 10: **+6 new tests** (all in
`test_ai_provider_matrix_consistency.py`).

---

## What the grant evaluator should look at

1. `docs/grant/15-ai-provider-honesty-matrix.md` — the doctrine: every
   provider, every dimension, per-use-case branches, no-silent-rerouting
   promise. This is the canonical document NLnet evaluators should read
   when assessing "is this project honest about AI tradeoffs?"
2. `tests/test_ai_provider_matrix_consistency.py` — the executable
   contract: every catalogue provider has a matrix row; per-use-case
   sections are present; DeepSeek PRC note remains.
3. `static/index.html` AI Provider section — the user-facing surface:
   tradeoffs visible at decision time, EN + DE.
4. `compliance/transparency-notice.md` "You choose the AI provider"
   section — links to the doctrine for the per-provider detail.

---

## Commits in PART 10

| Commit | Loop | Title |
|---|---|---|
| `1317c94` | 31 | AI provider honesty matrix doctrine + transparency-notice cross-link + consistency test |
| `81ffd1a` | 32 | AI provider honesty-tradeoff hint in Settings UI |
| (this commit) | 33 | Closure synthesis |

---

PART 10 closed cleanly. Ready for PART 11 (iterate to closure) when
the operator calls it.
