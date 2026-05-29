# Source-class hierarchy doctrine

Date: 2026-05-21 (PART 8 Loop 24)
Status: project-level design principle, binding unless explicitly reopened
License: Apache 2.0

---

## Why this doctrine exists

Every claim a Helpmefindthejob output makes to a user has a source. If
the user cannot tell which source backs a claim — and how authoritative
that source is — the user has no way to verify the claim, contest it,
or escalate it. For a civic-commons tool that helps people navigate
high-stakes employment + bureaucratic decisions (visa status, language
requirements, professional recognition, salary expectations), unverifiable
claims are not acceptable.

The source-class hierarchy doctrine answers: **for each kind of claim
the system makes, which source class is authoritative, and how does the
output surface that provenance to the user?**

It complements (does not replace):

- The anti-hallucination instructions already shipped in all 9 AI prompt
  sites (PART 4 + PART 5)
- The cost-saving doctrine at [`08-cost-saving-doctrine.md`](08-cost-saving-doctrine.md)
- The EU AI Act compliance pack at [`10-ai-act-compliance.md`](10-ai-act-compliance.md)
- The transparency notice at `compliance/transparency-notice.md`

---

## The hierarchy (most authoritative → least)

| Class | Examples | Use for claims about… |
|---|---|---|
| **A — Legal / regulatory authority** | BAMF, Ausländerbehörde, Migrationsberatungsstelle, Bundesagentur für Arbeit (BfA), the operative statute itself (§16d AufenthG, EU Blue Card Directive 2021/1883, §4 AsylG) | Visa status, residence-permit compatibility, recognition (Anerkennung), legal eligibility |
| **B — Authoritative standardised taxonomy** | ESCO 1.1 (CC BY 4.0), ISCO-08, EURES, schema.org JobPosting, CEFR language framework | Occupation codes, skill codes, language proficiency mapping, JD field semantics |
| **C — Authoritative organisation-level data** | BfA 2025 shortage occupation list, KMK qualification recognition records, Bundesinstitut für Berufsbildung (BIBB), Federal Statistical Office | Shortage flags, recognition outcomes, sector statistics |
| **D — Curated project data** | `reference/esco/occupations.json`, `companies_catalog.py`, the seven-persona panel (Decision 21) | Project-specific reference data with documented provenance + version (e.g. v1-curated-2026-05-18) |
| **E — User-provided primary data** | The user's CV, the user's pasted JD, the user's chat responses | Anything the user has directly asserted about themselves or about a specific job |
| **F — Aggregator-fetched secondary data** | Adzuna postings, Personio HTML, Greenhouse JSON, scraped public career pages | Job postings, company structure data — always carry source-URL provenance |
| **G — AI inference** | Foundation-model output (OpenAI, Anthropic, Gemini, Ollama, etc.) | Restatement, summarization, structuring of A–F sources; analysis grounded in A–F |

**The rule**: claims in higher classes (A–C) are NEVER restated by an AI
without explicit citation back to the source. Claims in classes D–F are
restated with citation. Class-G AI inference is acceptable when grounded
in classes A–F via in-context evidence, never as standalone authority.

---

## How each AI prompt site already applies this

| Prompt | Source-class discipline |
|---|---|
| `build_auto_fit_prompt` | "Source confidence" instruction (`analysis.py:209`): each non-trivial claim must be tagged (a) JD text [class E], (b) candidate profile [class E], or (c) general AI inference [class G]. |
| `build_job_decision_brief_prompt` | "Use ONLY facts present in the candidate profile + the job description below" — restricts to class E. |
| `build_cover_letter_brief_prompt` | "Never invent the candidate's employers, dates, titles, achievements, certifications, language levels, or visa status" — class E restriction. "Job-specificity NON-NEGOTIABLE: reference at least 2 DISTINCT facts from the JD" — forces class-E grounding. |
| `motivation_letter.build_letter_prompt` | "Use ONLY facts present in the CV. Never invent companies, ... If <job> details are sparse, write generic-but-honest language anchored to what" — class E + honesty about source limits. |
| `cv_consult.build_consult_prompt` | "Never invent CV facts. Only point at what's missing." — class E only, no inference. |
| `cv_builder.build_format_prompt` | "Do NOT add facts the user did not write... USER NOTES (verbatim — do not invent beyond these)" — class E verbatim, with FactRatio test (`test_ai_quality_deep.FactRatioTests`) enforcing grounding. |
| `chat_router.build_ai_router_prompt` | "Never invent a company name, URL, role title, or any other fact... If you're unsure, omit the param" — class E + honesty about uncertainty. |

---

## How each authoritative-claim site already applies this

| Code site | Claim | Source class | Provenance handling |
|---|---|---|---|
| `widening.py:LOCATION_CAVEAT_TEXT` | "changing your search location may not be compatible with your current residence-permit ties" | A (legal) | Refuses to give legal advice; directs the user to BAMF / Ausländerbehörde / Migrationsberatungsstelle (class-A authoritative bodies). Operator-verbatim text; never AI-generated. |
| `mcp_tools.py:query_esco_skill` | ESCO occupation / skill codes + labels | B (taxonomy) | Returns `datasetVersion: "v1-curated-2026-05-18"` in the tool response. Per-entry `esco_uri` provides the authoritative ESCO URL. `altLabels_de/en` traceable to ESCO 1.1 alternativeLabel records. |
| `reference/esco/occupations.json` | Occupation entries | B + C | Top-level `attribution` field cites ISCO-08 + ESCO 1.1 CC BY 4.0; `sourceTaxonomies` lists. Per-entry `shortageDE2024: true` flag is the BfA 2025 shortage-occupation reference (class C). |
| `mcp_tools.py:propose_referral` | "Composition pattern 1 (sequential handoff) per `09-mcp-composition.md`" | D (curated doctrine) | Citation in the tool description itself. |
| `mcp_tools.py:record_user_outcome` | "primary measurement substrate for partner-pilot evidence (`08-cost-saving-doctrine.md` §1, §2, §8)" | D (curated doctrine) | Citation in the tool description itself. |
| `persona_fixtures.py` (Aïcha) | "§16d AufenthG (visa for purpose of recognition of foreign qualification)" | A (statute) | Cites the statute by section number. |

---

## What PART 8 adds on top

This pass ships:

- **Loop 24 (this commit)**: the doctrine document; transparency-notice
  extension cross-referencing the hierarchy; code-level provenance
  comments at the doctrine-applying call sites.
- **Loop 25**: structural citation markers in the cover-letter and
  motivation-letter prompts so the user-visible output carries inline
  footnotes (`[JD]` / `[CV]` markers) for class-E grounding. UI renders
  the markers so the user can verify each claim against the source.
- **Loop 26**: golden-output structural test rig at
  `tests/test_ai_output_invariants.py` — fixed CV+JD pair → assert
  structural invariants on the AI output (contains role title, contains
  company name, contains at least 2 JD-derived facts, no claim outside
  CV/JD). Catches prompt-template regressions in CI without an LLM.
- **Loop 27**: PART 8 closure synthesis.

---

## What this doctrine does NOT cover

- Claims about the future ("you will get an offer", "the market is
  improving") — these are out of scope; the system does not make
  predictive claims.
- Personal advice ("you should take this offer") — out of scope; the
  system surfaces options, never recommends.
- Claims about third parties not in the data we hold ("Charité is a
  great employer") — these get carefully-framed soft language anchored
  in concrete public data (sector, scale, role families), never as
  endorsements.

These exclusions are intentional and align with the project's civic-
commons positioning: we are a tool that helps users make their own
decisions with verifiable inputs, not an oracle that makes decisions
for them.

---

## Cross-references

- EU AI Act Article 50 (transparency obligations) — [`10-ai-act-compliance.md`](10-ai-act-compliance.md)
- Cost-saving doctrine mechanisms 1, 2, 8 — [`08-cost-saving-doctrine.md`](08-cost-saving-doctrine.md)
- Project-level lessons learned — [`13-lessons-learned.md`](13-lessons-learned.md)
- User-facing transparency notice — `compliance/transparency-notice.md`
- Cost-saving evidence substrate (outcome events) — `mcp_tools.py:record_user_outcome`
- PART 5 prompt-template review (closure) — `docs/grant/anschreiben-quality-walks-2026-05-20/`
- PART 7 MCP composability closure — `part-7-closure-2026-05-21.md` (historical artefact, removed in 2026-05-23 docs cleanup; substantive output lives in `09-mcp-composition.md` and `STANDARDS.md`)

---

## Append log

- **2026-05-21**: Initial doctrine published as part of PART 8 Loop 24
  (Accuracy + citation discipline). Hierarchy A–G defined; per-prompt
  and per-authoritative-claim audits documented; Loops 25–27 in-flight
  for citation markers, golden tests, and closure.
- **2026-05-24**: pre-submission re-verification anchor. Method: drift-check every Class-A through Class-D source named in the hierarchy table above + the verification table in `docs/grant/application-draft-2026-05-19.md` (which has its own 4-pass dated audit trail through 2026-05-22). Result:
  - **Class A (Legal / regulatory)**: All citations resolve. EU AI Act Regulation (EU) 2024/1689 at `eur-lex.europa.eu/eli/reg/2024/1689/oj` — verified active; Article 6 + Annex III §4 + Article 113 transition timeline confirmed unchanged. §16d AufenthG at `gesetze-im-internet.de/aufenthg/__16d.html`, §4 AsylG at `gesetze-im-internet.de/asylvfg_1992/__4.html`, §6a SGB II at `gesetze-im-internet.de/sgb_2/__6a.html`, Article 91e GG at `gesetze-im-internet.de/gg/art_91e.html`, EU Blue Card Directive 2021/1883 at `eur-lex.europa.eu/eli/dir/2021/1883/oj` — all four primary-source URLs WebFetch-resolvable. GDPR Regulation (EU) 2016/679 at `eur-lex.europa.eu/eli/reg/2016/679/oj` — stable.
  - **Class B (Authoritative standardised taxonomy)**: All citations resolve. ESCO 1.1 at `esco.ec.europa.eu` (DG Employment-hosted), EURES at `eures.ec.europa.eu`, schema.org JobPosting at `schema.org/JobPosting`, CEFR at `coe.int/en/web/common-european-framework-reference-languages`, ISCO-08 at `ilo.org/public/english/bureau/stat/isco/isco08/`, JSON Schema 2020-12 at `json-schema.org/draft/2020-12/schema` — all verified active.
  - **Class C (Authoritative organisation-level data)**: 1 of 4 verified primary-source citable, 3 of 4 carry the reword-with-citation per the application-draft pass-3 audit trail (2026-05-22; 8-route WebFetch exhaustion documented for BMAS, BAMF, OECD). The reword approach holds — the underlying sources (OECD Economic Surveys Germany 2025; BAMF-NAvI directory; BMAS Optionskommunen list) remain the documented authority but the headline numerical claim is not led with in the application body. See pass-3 entry + pass-4 entry in `application-draft-2026-05-19.md`.
  - **Class D (Curated project data)**: All cite a versioned, committed source-of-truth file. `reference/esco/occupations.json`, `companies_catalog.py`, `company_discovery/persona_fixtures.py` (Decision 21 seven-persona panel) all carry the canonical content and the test suite (`tests/test_seed_personas.py`, `tests/test_bias_methodology.py`, `tests/test_taxonomy_persona_coverage.py`) pins them.
  - **Citation-marker discipline**: ai-prompt sites at `company_discovery/analysis.py::build_*_prompt` continue to surface source-class anchors in the prompt scaffolding (per Loop 25). Spot-check 2026-05-24: `build_auto_fit_prompt` (anchor scale references §16d / Blaue Karte / Wiedereinstiegsprogramm as Class-A citations); `build_cv_tailoring_prompt` (friction-keyword tokens drawn from Class-A residency-status vocabulary).
  - **Overall verdict**: source-class hierarchy doctrine fully honoured at submission time. Every external claim in the public-facing artefacts traces to a Class-A through Class-D source per this table; any claim that didn't reach a primary URL after the 8-route audit is reworded rather than stated as a precise figure (the doctrine's intended fallback). 30-day freshness window per the plan box: all Class A + B URLs verified active 2026-05-24; Class C reword status carried from 2026-05-22 pass-3 + reconfirmed pass-4 2026-05-24; Class D source-of-truth files live in the tracked git tree with date stamps.
