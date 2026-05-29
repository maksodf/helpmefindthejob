# AI provider honesty matrix — open-source local vs cloud

Date: 2026-05-21 (PART 10 Loop 31)
Status: project-level design doctrine, binding unless explicitly reopened
License: Apache 2.0

---

## Why this doctrine exists

Helpmefindthejob is BYO-AI by design: the user picks from one of 11
AI providers (`company_discovery/ai_providers.py`) ranging from
locally-hosted Ollama through commercial cloud APIs (OpenAI,
Anthropic, Google, DeepSeek, OpenRouter) to manual handoff. The
project's civic-commons positioning means we MUST be honest with the
user about what they are choosing when they pick one over another.

This doctrine answers, in writing, the question the project must not
fudge: **"is local AI as good as cloud AI?"**

It does not answer "which provider should I use?" — that is a user
decision driven by user priorities. The doctrine surfaces the
tradeoffs so the user can make an informed choice.

---

## The matrix (per-provider tradeoffs)

| Provider | Mode | Quality (frontier ≅ 100) | Latency (typical) | Privacy (data egress) | Cost per request | EU AI Act surface | Key tradeoff |
|---|---|---|---|---|---|---|---|
| **Ollama / local** | `local_http` | 50-75 (model-dependent: `llama3.1:8b` ≈ 60; `mistral-nemo` ≈ 65; quantised 70b ≈ 75) | 30-90 s (CPU); 5-20 s (GPU) | **None** — runs on user's machine, no egress | Zero (electricity + hardware) | None — no third-party processor | Privacy + zero variable cost; quality + speed cost |
| **OpenAI** (BYO key) | `api` | 85-100 (`gpt-4o-mini` ≈ 85; `gpt-4o` ≈ 95; `gpt-4-turbo` ≈ 100) | 1-5 s | CV + JD slice → OpenAI (US-based, see OpenAI DPA) | ~$0.001-0.03 per cover letter | OpenAI is the processor; user contracts directly | Best quality + speed; data egress + per-token cost |
| **Anthropic / Claude** (BYO key) | `api`, `cli` | 85-100 (`claude-3-haiku` ≈ 85; `claude-3-5-sonnet` ≈ 95; `claude-opus-4` ≈ 100) | 1-5 s | CV + JD slice → Anthropic (US-based, see Anthropic DPA) | ~$0.001-0.05 per cover letter | Anthropic is the processor | Highest single-prompt-quality at the frontier; data egress + cost |
| **Google Gemini** (BYO key) | `api` | 80-95 (`gemini-flash` ≈ 80; `gemini-pro` ≈ 95) | 1-3 s | CV + JD slice → Google (US-based, see Google AI DPA) | ~$0.001-0.02 per cover letter | Google is the processor | Strong multilingual incl. German; data egress + Google ecosystem ties |
| **DeepSeek** (BYO key) | `api` | 75-90 | 2-8 s | CV + JD slice → DeepSeek (PRC-based — see country-specific data-residency note below) | ~$0.0001-0.005 per cover letter | DeepSeek is the processor — **PRC jurisdiction** | Lowest cost-per-token at quality; jurisdictional / data-residency considerations |
| **OpenRouter** (BYO key) | `api` | Variable — depends on routed model | 1-15 s | CV + JD → OpenRouter → routed model provider | Variable | OpenRouter routes; user must check the routed model's DPA | Access to many models via one key; routing transparency depends on user choosing the model |
| **Codex CLI** (local auth) | `cli` | Inherits the underlying model's quality (whatever the user's Codex setup uses) | Whatever the CLI returns | Depends on Codex configuration | Whatever the Codex plan covers | Inherits Codex's compliance posture | User reuses an existing CLI authentication; quality + privacy = whatever Codex carries |
| **Claude Code** (local auth) | `cli` | Inherits the user's Claude Code setup (Sonnet 4.6 / Opus 4.7 typical) | 2-10 s | CV + JD slice → Anthropic via the user's Claude Code account | Whatever the Claude Code subscription covers | Anthropic via the user's account | No separate API key — reuses Claude Code auth; data egress still goes to Anthropic |
| **Manual handoff** | `manual` | Equal to whatever AI the user runs the prompt through manually | User-paced | **User controls** entirely — they decide what to paste where | Whatever the destination AI charges | User is the data controller for the relay | Full user agency over what gets sent; manual workflow overhead |
| **Custom** | `api / cli / local_http` | Whatever the configured endpoint returns | Whatever the endpoint returns | Whatever the endpoint does with the data | Whatever the endpoint charges | Operator / user contracts directly with whoever owns the endpoint | Escape hatch for org-specific or future providers |
| **Managed** (operator-side key) | `api` | Whatever model the operator wired (typically a frontier cloud model) | 1-5 s | CV + JD slice → operator's chosen processor via the operator's key | Bundled into the user's Plan (€5/mo waitlist) | Operator is the processor toward Anthropic / OpenAI / Google | Zero-config UX; the operator (not user) chose the upstream processor — picked transparently in operator config |

### Quality scale notes

The "Quality" column uses an informal 0-100 scale anchored at *frontier
cloud models in mid-2026*. It is meant to communicate ordering and
rough magnitude, not to be a benchmark score. The PART 5 bias-
methodology run (Ollama `llama3.1:8b`, 70 scenarios, 7-persona panel)
landed within ±10 of the operator's target tolerance bands on fit-
scoring — which is the empirical anchor for the Ollama row.

For a head-to-head ordered comparison on this project's actual prompts,
the operator can run the bias-methodology suite against any provider:
```
HELPMEFINDTHEJOB_RUN_BIAS_METHODOLOGY=1 python3 -m unittest tests.test_bias_methodology -v
```
swapping the `provider` fixture in `setUpClass`. PART 5 covered Ollama;
swapping to Anthropic / OpenAI is operator-machine work, not CI work.

---

## Per-use-case recommendation (NOT a single "best provider")

The project does NOT recommend a single provider. Use the matrix
above + your own priorities to pick. As a structured starting point,
here are tradeoffs by use case:

### Fit scoring (10 jobs × ~1k tokens each)

- **Privacy-first**: Ollama. Per-request privacy + zero variable cost
  outweigh the quality gap on a task with a numeric output that doesn't
  need frontier reasoning.
- **Speed-first**: Anthropic Haiku or OpenAI `gpt-4o-mini` via BYO
  key. Sub-second per-job latency on a batch of 10 is materially
  better than 30-90s × 10 with local AI.
- **Cost-first**: DeepSeek (be aware of the PRC-jurisdiction note);
  alternatively Ollama for zero variable cost.

### Cover-letter / motivation-letter drafting

- **Privacy-first**: Ollama with a 7-13B+ model. The PART 5 walks
  show coherent DACH-norm output is achievable locally.
- **Quality-first**: Anthropic Sonnet or Opus, or OpenAI `gpt-4o`.
  Frontier models produce noticeably more idiomatic German + better
  job-specificity reference density (citations to JD facts).
- **Honest about the gap**: a German `Bewerbungsschreiben` at the
  Anthropic Sonnet quality bar typically requires Ollama 13B+ at
  high quantisation; an 8B quantised local model trails noticeably
  on idiom + specificity.

### CV consult (improvement suggestions)

- **Privacy-first**: Ollama. The PART 5 bias-methodology run
  documented Ollama can suggest tailoring directions without
  inventing facts (the `FactRatio` test enforces this) on the
  7-persona panel.
- **Insight-depth-first**: Anthropic Sonnet. Frontier models surface
  subtler suggestions ("re-emphasise X because the JD repeats it
  in the role responsibilities").

### Brief / job-decision summary

- **Privacy-first**: Ollama.
- **Best balance**: OpenAI `gpt-4o-mini` — fast + cheap + adequate
  for a structured analytical task.

### Slash-command intent routing (chat router)

- **Recommend deterministic templates**: this surface is best served
  by the project's deterministic parser + keyword router. The AI
  router is the third layer behind slash + keyword. None of the AI
  providers significantly improves on the deterministic layer for
  this surface — it's intent classification, not generation.

---

## The honest single-paragraph summary

The shortest honest answer the maintainer would give a journalist:

> **Cloud AI is materially better at output quality and speed today,
> at the cost of data egress to the provider's jurisdiction and
> per-token billing. Local AI (Ollama) is materially better for
> privacy and zero-variable-cost workflows, at the cost of slower
> generation and a model-dependent quality gap that's narrowing every
> quarter. Helpmefindthejob makes the choice clear at provider-pick
> time, ships the same prompts to whichever the user picks, and
> never silently reroutes to cloud when local was requested.**

---

## How this doctrine binds the code

1. **Provider catalogue** (`company_discovery/ai_providers.py`
   `PROVIDER_OPTIONS`) — every entry must have a row in this
   document. The contract test
   `tests/test_ai_provider_matrix_consistency.py` enforces this.
2. **Transparency notice** (`compliance/transparency-notice.md` —
   "You choose the AI provider" section) — links to this document
   for the per-provider tradeoff detail.
3. **Settings UI** (`static/index.html` — AI provider picker) —
   surfaces a one-paragraph inline summary above the picker so the
   tradeoffs are visible at decision time, not buried in docs.
4. **No silent rerouting**: when a user picks Ollama and the local
   endpoint is unreachable, the system surfaces an honest banner ("Your
   local AI is unreachable — start Ollama and retry, or switch
   provider in Settings"). It never silently falls through to a
   cloud provider the user did not pick.

---

## Cross-references

- [`10-ai-act-compliance.md`](10-ai-act-compliance.md) — EU AI Act
  Article 50 (transparency) + Article 12 (audit log)
- [`14-source-class-hierarchy.md`](14-source-class-hierarchy.md) —
  AI inference is class G; this matrix lets the user see which
  provider sits behind their class-G inference
- [`08-cost-saving-doctrine.md`](08-cost-saving-doctrine.md) — the
  zero-variable-cost path (Ollama / manual / deterministic) is the
  project's cost-saving floor; cloud provider use is a user-paid
  upgrade
- PART 5 anschreiben quality walks at
  `docs/grant/anschreiben-quality-walks-2026-05-20/` — empirical
  Ollama-on-this-project's-prompts evidence
- PART 8 closure — `part-8-closure-2026-05-21.md` (historical artefact, removed in 2026-05-23 docs cleanup; substantive findings are summarised inline in this matrix) —
  citation discipline applies to every provider equally; class-E
  grounding tests don't care which model is behind the call

---

## Append log

- **2026-05-21**: Initial doctrine published as PART 10 Loop 31
  (Honesty matrix: open-source-AI vs cloud-AI). 11-provider matrix +
  per-use-case recommendations + binding-on-code surface defined.
  Cross-references to AI Act + source-class doctrine + cost-saving
  doctrine.
- **2026-05-24** (PlanTowardPerfection box 2.8.5 — what-we-know-we-don't-know
  appendix): the matrix above carries verified rows for the providers
  the maintainer has exercised live + dispatcher-shape tested for the
  rest. This appendix names the residual unknowns explicitly so a
  reviewer + a deployer can scope their own pre-production validation.

  **Live-exercised at v0.80.0** (latency / cost / output-quality measured
  on the project's own prompts within the last 30 days):
  - `deepseek` — 70 data points in `bias-comparative-report-2026-05-21.md`;
    measured per-persona mean fit-score 56.4–74.3; OOB rate 13.0 % at
    the 2026-05-19 polished-cohort run; cost ~€0.00 (cached replay
    against `data/bias_comparative_cache/`); first-token latency
    sub-second on the maintainer's network. **Re-verified 2026-05-29**:
    a direct `/chat/completions` round-trip through the current
    `_execute_openai_compatible` adapter returned `status=completed`,
    confirming the live cloud-API path still works after the v0.80.0
    catalogue + audit-log changes — i.e. the dispatcher itself, not a
    cached replay.
  - `ollama` (local `llama3.1:8b`) — 70 data points in the same report;
    measured per-persona mean fit-score 50.4–67.4; OOB rate carries
    the same 13.0 % baseline; cost €0.00 by construction (local-only);
    first-token latency depends on hardware, ~3-6 s on M-series Mac.

  **Dispatcher-shape tested but NOT live-key-exercised** at v0.80.0:
  - `openai`, `anthropic`, `gemini`, `openrouter` — the dispatcher
    layer in `company_discovery/ai_providers.py` has unit tests
    covering the request-shape, response-parsing, and error-class
    handling per provider. What HAS NOT been measured: actual
    per-persona output quality, latency-under-real-network-conditions,
    cost-per-1k-tokens against the project's actual prompts, output
    OOB rate. Bias-comparative-report-v2 (scaffolded in
    `compliance/accuracy-and-bias-testing.md` §10) is the path to
    measuring these 4 providers live — gated on the deployer providing
    API keys + cost-cap budgets per the v2 reproducibility recipe.
  - `codex_cli`, `claude_code` — these are local-CLI shims that
    subprocess out to the user's installed Codex CLI / Claude Code.
    Dispatcher-shape tested via subprocess mocks; actual behaviour is
    "whatever the user's local CLI does", which is by-design out-of-
    scope for the project's verification surface. Per the BYO-AI
    contract the deployer is the one with skin in the game on the
    output quality these surfaces produce.

  **What this means for a NLnet reviewer or institutional deployer**:
  the matrix above is honest about what's verified vs. what's not.
  An institutional deployer choosing between providers should:
  1. Decide on cost vs. data-egress posture (use the §"Data egress
     posture" column above).
  2. Run the bias-methodology-v2 recipe in
     `compliance/accuracy-and-bias-testing.md` §10 against their
     chosen provider with their own API key + cost-cap budget.
  3. Compare the resulting per-persona means + OOB rate against the
     deepseek + ollama baselines in `bias-comparative-report-2026-05-21.md`.
  4. Document the choice in the deployer's
     `compliance/transparency-notice.md` `[Deployer-managed addendum]`
     so end-users see which provider's data-flow disclosure applies.

  Steps 2–4 are the deployer-side verification surface; the project
  side cannot validate against providers without the deployer's keys.
  This appendix exists so that gap is recorded honestly rather than
  glossed.
