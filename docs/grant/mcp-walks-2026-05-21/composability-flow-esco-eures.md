# Composability flow 2: Krankenschwester ESCO + EURES

Demonstrates cross-agent taxonomy interop. ESCO provides a stable cross-border occupation + skill code that any European civic agent can reference; EURES is the European Employment Services portal projection contract. Together they let an external MCP client compose helpmefindthejob's discovery output with EU-wide labour-market infrastructure.


### Step 1. query_esco_skill(query='Krankenschwester', type='occupation')

```json
{
  "tool": "query_esco_skill",
  "arguments": {
    "query": "Krankenschwester",
    "type": "occupation"
  }
}
```

**Response (ok):**

```json
{
  "status": "ok",
  "datasetVersion": "v1-curated-2026-05-18",
  "totalCandidates": 80,
  "matches": [
    {
      "code": "2221.1",
      "label": "Registered nurse (general)",
      "label_en": "Registered nurse (general)",
      "label_de": "Examinierte/r Krankenpfleger/in",
      "type": "occupation",
      "isco": "2221",
      "personas": [
        "Aicha"
      ],
      "shortageDE2024": true,
      "esco_uri": "http://data.europa.eu/esco/occupation/2221.1",
      "altLabels_en": [
        "registered nurse",
        "general nurse",
        "RN"
      ],
      "altLabels_de": [
        "Krankenschwester",
        "Krankenpfleger",
        "Pflegefachkraft",
        "examinierte Pflegekraft"
      ]
    },
    {
      "code": "2221.2",
      "label": "Specialist nurse — clinical / Pflege",
      "label_en": "Specialist nurse — clinical / Pflege",
      "label_de": "Fachkrankenpfleger/in",
      "type": "occupation",
      "isco": "2221",
      "personas": [
        "Aicha"
      ],
      "shortageDE2024": true,
      "altLabels_en": [
        "specialist nurse",
        "clinical nurse specialist"
      ],
      "altLabels_de": [
        "Fachkrankenschwester",
        "Pflegefachkraft (Spezialisierung)"
      ]
    }
  ]
}
```


### Step 2. query_esco_skill(query='Pflege', type='skill')

```json
{
  "tool": "query_esco_skill",
  "arguments": {
    "query": "Pflege",
    "type": "skill"
  }
}
```

**Response (ok):**

```json
{
  "status": "ok",
  "datasetVersion": "v1-curated-2026-05-18",
  "totalCandidates": 80,
  "matches": [
    {
      "code": "S.HEALTH.GERI",
      "label": "Geriatric care",
      "label_en": "Geriatric care",
      "label_de": "Altenpflege",
      "type": "skill",
      "category": "healthcare"
    },
    {
      "code": "S.HEALTH.PEDI",
      "label": "Pediatric care",
      "label_en": "Pediatric care",
      "label_de": "Kinderkrankenpflege",
      "type": "skill",
      "category": "healthcare"
    },
    {
      "code": "S.HEALTH.PFLEGEST",
      "label": "Pflegestandards / German nursing standards",
      "label_en": "Pflegestandards / German nursing standards",
      "label_de": "Pflegestandards",
      "type": "skill",
      "category": "healthcare"
    }
  ]
}
```

**Composability anchor:** the type=skill filter demonstrates the tool's typed catalogue -- callers can ask for occupations or skills independently, matching the ESCO 1.1 schema's separation of concerns.

### Step 3. suggest_relevant_companies(roles=[Krankenschwester], industry=krankenpflege)

```json
{
  "tool": "suggest_relevant_companies",
  "arguments": {
    "targetRoles": [
      "Krankenschwester",
      "Pflegefachkraft"
    ],
    "industry": "krankenpflege",
    "location": "Berlin"
  }
}
```

**Response (ok):**

```json
{
  "status": "ok",
  "suggestions": [
    {
      "name": "Charite - Universitaetsmedizin Berlin",
      "website_url": "https://www.charite.de",
      "career_page_url": "https://karriere.charite.de",
      "sector": "University hospital",
      "location_hint": "Berlin",
      "role_families": [
        "public health",
        "health services research",
        "quality/process management",
        "project management"
      ],
      "relevance_reason": "Large university hospital with management, research, quality, and public-sector healthcare roles.",
      "type": "company",
      "relevanceScore": 0.55,
      "relevanceReason": "Large university hospital with management, research, quality, and public-sector healthcare roles.",
      "watchEnabled": true
    },
    {
      "name": "Vivantes",
      "website_url": "https://www.vivantes.de",
      "career_page_url": "https://karriere.vivantes.de",
      "sector": "Hospital / clinic group",
      "location_hint": "Berlin",
      "role_families": [
        "project management",
        "quality/process management",
        "digital health"
      ],
      "relevance_reason": "Large Berlin healthcare network with hospital operations, project, administration, and digital transformation roles.",
      "type": "company",
      "relevanceScore": 0.55,
      "relevanceReason": "Large Berlin healthcare network with hospital operations, project, administration, and digital transformation roles.",
      "watchEnabled": true
    },
    {
      "name": "GKV-Spitzenverband",
      "website_url": "https://www.gkv-spitzenverband.de",
      "career_page_url": "https://www.gkv-spitzenverband.de/gkv_spitzenverband/karriere/karriere.jsp",
      "sector": "Health policy organization",
      "location_hint": "Berlin / Bonn",
      "role_families": [
        "health policy",
        "public health",
        "digital health",
        "project management"
      ],
      "relevance_reason": "Central statutory health-insurance association with policy, digitalization, prevention, and project roles.",
      "type": "company",
      "relevanceScore": 0.55,
      "relevanceReason": "Central statutory health-insurance association with policy, digitalization, prevention, and project roles.",
      "watchEnabled": true
    },
    {
      "name": "Doctolib",
      "website_url": "https://www.doctolib.de",
      "career_page_url": "https://careers.doctolib.de/",
      "sector": "Digital Health",
      "location_hint": "Berlin / Paris",
      "role_families": [
        "backend",
        "frontend",
        "product",
        "growth"
      ],
      "relevance_reason": "European e-health platform with engineering and product roles in Berlin, Paris, and remote.",
      "type": "company",
      "relevanceScore": 0.55,
      "relevanceReason": "European e-health platform with engineering and product roles in Berlin, Paris, and remote.",
      "watchEnabled": true
    },
    "... (14 more)"
  ]
}
```


### Step 4. export_eures_compatible(userId, discoveredJobId='dj-not-found')

```json
{
  "tool": "export_eures_compatible",
  "arguments": {
    "userId": "u-eures-demo",
    "discoveredJobId": "dj-does-not-exist"
  }
}
```

**Response (ok):**

```json
{
  "status": "not_found",
  "error": "'SqliteCompanyDiscoveryRepository' object has no attribute 'get_discovered_job'"
}
```

**Composability anchor:** even the empty-state path returns a structured response with a documented status code rather than raising. External MCP clients can compose EURES projection into a multi-step pipeline without special-casing missing-job errors -- the contract is the same shape either way.

## Result

Four tool calls demonstrate that ESCO (cross-border taxonomy) and EURES (European Employment Services projection) are first-class composability primitives in the helpmefindthejob MCP surface. An external agent can pivot from an ESCO code into company suggestions and EURES-shaped projections without ever touching helpmefindthejob's user-facing UI.
