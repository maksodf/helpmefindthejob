# ESCO + EURES integration

**Status**: shipped in Week 2 §2.4. Curated subset under `reference/esco/`; full ESCO dataset import is post-grant scope.

This document is the operational reference for how DirectJob Scout uses the **ESCO** (European Skills, Competences, Qualifications and Occupations) and **EURES** (European Employment Services) standards. It complements [`docs/mcp-server.md`](mcp-server.md) (which describes the MCP tools that surface these standards) and [`STANDARDS.md`](../STANDARDS.md) (which lists the standards we cite).

---

## Why these standards

The project's mission — captured in [`docs/grant/01-project-brief.md`](grant/01-project-brief.md) — is to put bureaucratic-navigation knowledge in the hands of anyone facing structural labor-market friction across the EU, with migrants and EU-mobile workers as the most acute use case (see Decision 21 in `docs/grant/04-research-and-decisions.md`). Bureaucratic navigation in this domain depends on agreeing on what *occupations* and *skills* are. ESCO and EURES are the canonical EU vocabularies:

- **ESCO** is the European Commission's pan-EU classification of ~3,000 occupations and ~13,000 skills, multilingually labelled in all 24 EU official languages plus Norwegian, Icelandic, and Arabic. Maintained by the Directorate-General for Employment, Social Affairs and Inclusion. Published as CSV, RDF, and SKOS under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
- **EURES** is the EU portal for cross-border employment services. Its [job-posting schema](https://eures.europa.eu/eures-services/eures-services-european-online-job-day_en) is the de-facto interoperability format for job listings shared between European public employment services and is closely aligned with [schema.org JobPosting](https://schema.org/JobPosting).

Adopting these standards has three concrete consequences for the project:

1. **A user's CV maps to ESCO codes** rather than to a project-specific taxonomy. A user moving between deployments — or between civic agents (DirectJob Scout → a housing or residency agent that also reads ESCO) — carries the same skill identifiers everywhere.
2. **A job listing exports in EURES shape** so a partner Beratungsstelle or Jobcenter can feed our discovered jobs into their own EURES-aware pipeline without bespoke transformation.
3. **NLnet reviewers see real standards alignment**, not just a "we support open standards" sentence in the README. The codes are in the codebase, in the data, and in the audit-log entries.

---

## What ships in §2.4

| Artefact | Location | Status |
|---|---|---|
| Curated 30-occupation reference dataset | [`reference/esco/occupations.json`](../reference/esco/occupations.json) | Shipped |
| Curated 50-skill reference dataset | [`reference/esco/skills.json`](../reference/esco/skills.json) | Shipped |
| Loader + persona-panel coverage tests | [`company_discovery/mcp_tools.py:_load_esco_reference_dataset`](../company_discovery/mcp_tools.py), [`tests/test_phase12_esco_eures.py`](../tests/test_phase12_esco_eures.py) | Shipped |
| ESCO-backed `query_esco_skill` MCP tool | [`mcp_server.py`](../mcp_server.py) (catalogue v0.2.0) | Shipped |
| EURES-shaped `export_eures_compatible` MCP tool | same | Shipped (projection shape; end-to-end with persisted jobs lands in §2.6) |
| Full ESCO dataset import (3,000 occupations / 13,000 skills, all 27 ESCO languages) | not in this commit | **Post-grant scope** (see "Upgrade path" below) |

---

## Reference-dataset schema

### `reference/esco/occupations.json`

```jsonc
{
  "schemaVersion": "0.1.0",
  "datasetVersion": "v1-curated-2026-05-18",
  "attribution": "Codes and concept structure derived from ISCO-08 / ESCO 1.1...",
  "license": "CC-BY-4.0",
  "sourceTaxonomies": ["ISCO-08", "ESCO v1.1"],
  "coveragePolicy": "Persona-panel-aligned subset.",
  "entries": [
    {
      "code":             "2221.1",                            // ESCO leaf code (ISCO + ESCO suffix)
      "isco":             "2221",                              // ISCO-08 4-digit unit group
      "label_en":         "Registered nurse (general)",        // English display label
      "label_de":         "Examinierte/r Krankenpfleger/in",   // German display label
      "personas":         ["Aicha"],                           // Which persona archetype(s) this serves
      "shortageDE2024":   true,                                // On the BA 2025 shortage list
      "esco_uri":         "http://data.europa.eu/esco/occupation/2221.1"  // Optional canonical URI
    },
    // ... 29 more
  ]
}
```

### `reference/esco/skills.json`

```jsonc
{
  "schemaVersion": "0.1.0",
  "datasetVersion": "v1-curated-2026-05-18",
  "attribution": "Skill identifiers and labels derived from ESCO v1.1 skills pillar...",
  "license": "CC-BY-4.0",
  "sourceTaxonomy": "ESCO v1.1 (skills pillar) + DigComp 2.2 + CEFR",
  "coveragePolicy": "Persona-panel-aligned subset of high-frequency skills.",
  "entries": [
    {
      "code":     "S.LANG.DE.B2",                  // Project-internal stable identifier
      "label_en": "German B2 (CEFR — Upper Intermediate)",
      "label_de": "Deutsch B2 (Obere Mittelstufe)",
      "category": "language",                       // language | healthcare | engineering | it | trade | cross-cutting
      "cefr":     "B2"                              // Optional, for language skills
    },
    // ... 49 more
  ]
}
```

## Persona-panel coverage

Each occupation entry carries a `personas` array linking it back to the [seven-persona panel](grant/07-personas.md). The pull-through:

| Persona | Profession archetype | Linked occupation codes (selection) |
|---|---|---|
| **Aïcha** (Tunisia, nurse, §16d Anerkennung) | Healthcare | 2221.1, 2221.2, 2222.1, 5321.1, 2264.1, 2269.1, 3258.1, 3251.1 |
| **Yusuf** (Turkey, mechanical engineer, Blue Card) | Engineering | 2144.1, 2151.1, 2142.1, 2141.1, 2144.2, 2152.1 |
| **Olga** (Ukraine, frontend dev, §24) | IT / tech | 2512.1, 2513.1, 2512.2, 2522.1, 2511.1, 2511.2 |
| **Mahmoud** (Syria, trade apprentice, subsidiary protection) | Construction trades | 7126.1, 7411.1, 7115.1, 7512.1, 7112.1, 3434.1 |
| **Maria** (Romania, care worker, EU citizen) | Home-based care | 5321.1, 5321.2, 5322.1, 5311.1, 4222.1 |
| **Käthe** (Germany, returning nurse after 12 yr caregiving) | Healthcare (re-entrant) | shares 2221.1, 2221.2, 2222.1 with Aïcha — `personas` array extension to the JSON dataset lands in a follow-up commit |
| **Tobias** (Germany, commercial → civic-tech developer) | IT / tech (sector pivot) | shares 2512.1, 2513.1, 2511.1 with Olga — `personas` array extension to the JSON dataset lands in a follow-up commit |

(Some codes appear under more than one persona — e.g. 5321.1 covers both Aïcha and Maria via the Pflegehelfer pathway; the same code-reuse pattern applies for Käthe-with-Aïcha and Tobias-with-Olga.)

The skill entries are categorised (`language`, `healthcare`, `engineering`, `it`, `trade`, `cross-cutting`) rather than persona-mapped because skills compose across personas more loosely. Roughly:

| Skill category | Entries | Serves |
|---|---:|---|
| `language` | 5 | All personas (CEFR-graded German + English) |
| `healthcare` | 10 | Aïcha, Maria |
| `engineering` | 8 | Yusuf |
| `it` | 15 | Olga |
| `trade` | 8 | Mahmoud |
| `cross-cutting` | 4 | All personas (customer service, project management, communication, problem-solving) |
| **Total** | **50** | |

## Coverage relative to the Bundesagentur 2025 shortage list

The Bundesagentur für Arbeit 2025 shortage-occupations statement names 163 shortage occupations across the German labour market. The `shortageDE2024: true` flag on each occupation entry tracks intersection with that list. As of v1-curated-2026-05-18 the curated set covers **21 of the 30 occupations** as Bundesagentur-flagged shortages, concentrated in healthcare, engineering, IT, and construction trades — the four areas the persona panel was designed around.

A reviewer cross-checking the project's "cost-saving doctrine mechanism 1" (lower advisor caseload per case served — most acute for the migrant subset) claim can use this overlap to verify that the project is genuinely targeting where institutional cost relief is most acute, not painting the persona panel against a generic labour-market backdrop.

## Loader behaviour

`company_discovery.mcp_tools._load_esco_reference_dataset()` resolves the two JSON files from `reference/esco/` relative to the package root. The loader:

- caches the merged dataset for the process lifetime (the file is repo-tracked reference data, not user data; no need to refresh)
- normalises both files into a single list with `type` set to `"occupation"` or `"skill"` so the `query_esco_skill` tool can filter
- preserves all optional fields (`isco`, `category`, `cefr`, `personas`, `shortageDE2024`, `esco_uri`) on each match record
- exposes a single `label` field set to `label_en` for back-compat with the §2.3 mini-dataset shape, while also surfacing `label_en` and `label_de` separately for locale-aware consumers
- falls back to the inline `_ESCO_REFERENCE_DATASET_FALLBACK` 12-entry mini-set if either file is missing (e.g. some Python packaging configurations strip `reference/`). The `query_esco_skill` response's `datasetVersion` field is `v1-curated-2026-05-18` for the full path and `v0-mini-fallback` for the fallback so callers can branch.

## EURES projection shape

`export_eures_compatible` projects a stored `DiscoveredJob` onto a JSON document that maps to the EURES JobPosting fields most public-employment-service integrators consume:

| EURES field | Maps from | Notes |
|---|---|---|
| `id` | DiscoveredJob.id | Stable internal id |
| `title` | DiscoveredJob.title | |
| `datePosted` | DiscoveredJob.posted_at or .created_at | ISO 8601 |
| `validThrough` | DiscoveredJob.valid_until | ISO 8601 if known |
| `hiringOrganization.name` | DiscoveredJob.company / .company_name | |
| `hiringOrganization.url` | DiscoveredJob.company_url | |
| `jobLocation.addressLocality` | DiscoveredJob.location | |
| `jobLocation.addressCountry` | DiscoveredJob.country | ISO 3166-1 alpha-2 if known |
| `description` | DiscoveredJob.description | Plain text or markdown |
| `url` | DiscoveredJob.url | Source URL |
| `employmentType` | DiscoveredJob.employment_type | full-time / part-time / temporary etc. |
| `sourceProvider` | DiscoveredJob.source or .provider | Aggregator id |
| `schemaConformance` | constant `"EURES-compatible-subset-v0"` | Versioned conformance flag — bump when fields change |

The projection is deliberately a **subset** of full EURES. Fields that EURES expects but DirectJob Scout does not yet capture (e.g., language-of-posting, qualification-required references, sectoral classification per NACE) are absent rather than fabricated. As the project's job-discovery pipeline starts capturing these fields, the projection expands without changing existing fields — backwards-compatible at the consumer level.

A reviewer wanting to validate the projection against a real EURES schema can use the [EURES XSD](https://eures.europa.eu/eures-services/eures-services-european-online-job-day_en) published by the European Commission; the JSON projection lines up with the equivalent XML-element names so the mapping is one-step.

## Upgrade path — full ESCO dataset

The current curated subset (80 entries) is sufficient to:

1. demonstrate the standards-alignment claim end-to-end,
2. validate the loader + `query_esco_skill` MCP-tool surface against real codes, and
3. cover every persona archetype's primary occupation and skill mix.

The full ESCO dataset (~3,000 occupations, ~13,000 skills, all 27 ESCO languages, ~80 MB) is **not** in this commit because:

- repo bloat: shipping 80 MB of JSON in every clone is hostile to contributors
- localisation noise: 27 languages × 16k entries is ~430k label rows we do not currently need
- maintenance: the ESCO dataset updates roughly annually; a build-time fetch is safer than a baked snapshot

The upgrade path lands as **Phase 2** work after the grant sprint:

1. **Build step**: a `scripts/fetch_esco.py` that pulls the canonical CSV/SKOS bundle from the ESCO API (or the CC-BY mirror at the EU Open Data Portal) into a `data/esco/` build-artefact directory.
2. **Cached index**: a small SQLite or `marisa-trie`-shaped index for substring lookup that scales to 16k entries without burning a megabyte of RAM per query.
3. **Loader switch**: `_load_esco_reference_dataset()` adopts the index, with the curated v1 file becoming the fallback for offline / packaging-stripped environments.
4. **Multilingual surface**: `query_esco_skill` gains a `locale` parameter that returns labels in the requested locale (currently EN / DE only; full upgrade unlocks all 27 ESCO languages).
5. **Cross-deployment caching**: institutional deployers can opt into a shared ESCO index over a CDN rather than every deployment fetching the upstream dataset.

The curated v1 dataset and the v2 full-dataset loader share the same `query_esco_skill` response shape, so existing consumers do not need to change.

## How to use it in code

### Direct API call

```python
from company_discovery.mcp_tools import _load_esco_reference_dataset

dataset = _load_esco_reference_dataset()
# dataset is a list of {code, label, label_en, label_de, type, ...} records.
```

### Via the MCP tool

```jsonc
// MCP tools/call payload
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "query_esco_skill",
    "arguments": {"query": "krankenpfleger", "type": "occupation", "limit": 5}
  }
}
```

Sample response:

```jsonc
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [{"type": "text", "text": "{\"status\":\"ok\",\"datasetVersion\":\"v1-curated-2026-05-18\",\"totalCandidates\":80,\"matches\":[{\"code\":\"2221.1\",\"label\":\"Registered nurse (general)\",\"label_en\":\"Registered nurse (general)\",\"label_de\":\"Examinierte/r Krankenpfleger/in\",\"type\":\"occupation\",\"isco\":\"2221\",\"personas\":[\"Aicha\"],\"shortageDE2024\":true,\"esco_uri\":\"http://data.europa.eu/esco/occupation/2221.1\"}]}"}],
    "isError": false
  }
}
```

## Attribution

The codes, concept structure, and labels reflected in `reference/esco/occupations.json` and `reference/esco/skills.json` derive from:

- **ISCO-08** (International Labour Organization, public domain)
- **ESCO v1.1** (European Commission, Directorate-General for Employment, Social Affairs and Inclusion; published under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/))
- **CEFR** (Council of Europe, public domain)
- **DigComp 2.2** (Joint Research Centre of the European Commission, public domain)

DirectJob Scout acknowledges and complies with the CC BY 4.0 attribution requirement; this document is the attribution surface.

## See also

- [`docs/mcp-server.md`](mcp-server.md) — operational reference for `query_esco_skill` and `export_eures_compatible`
- [`docs/grant/09-mcp-composition.md`](grant/09-mcp-composition.md) — composition spec; ESCO is the cross-agent shared taxonomy
- [`STANDARDS.md`](../STANDARDS.md) — every standard the project cites
- [ESCO project homepage](https://esco.ec.europa.eu/)
- [EURES portal](https://eures.europa.eu/)
- [ESCO API documentation](https://ec.europa.eu/esco/api/doc/esco_api_doc.html)
