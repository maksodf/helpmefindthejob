# Composability flow 1: Aicha (16d Anerkennungsweg)

Persona: Aicha -- Tunisian nurse on Germany's 16d Anerkennungsweg. Friction class: visa-constrained migrant, regulated profession. Demonstrates: ESCO taxonomy lookup -> curated company suggestions -> watchlist creation -> direct HTML job extraction -> portable civic profile -> housing-agent referral -> outcome event recorded.

All 7 tool calls succeed against a fresh data dir (no prior repository state).

### Step 1. query_esco_skill(query='Pflegehelfer', type='occupation')

```json
{
  "tool": "query_esco_skill",
  "arguments": {
    "query": "Pflegehelfer",
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
      "code": "5321.1",
      "label": "Healthcare assistant / Pflegehelfer",
      "label_en": "Healthcare assistant / Pflegehelfer",
      "label_de": "Pflegehelfer/in",
      "type": "occupation",
      "isco": "5321",
      "personas": [
        "Aicha",
        "Maria"
      ],
      "shortageDE2024": true
    },
    {
      "code": "5321.2",
      "label": "Geriatric care assistant",
      "label_en": "Geriatric care assistant",
      "label_de": "Altenpflegehelfer/in",
      "type": "occupation",
      "isco": "5321",
      "personas": [
        "Maria"
      ],
      "shortageDE2024": true
    }
  ]
}
```

**Composability anchor:** ESCO code `5321.1` (Pflegehelfer/in) is a stable cross-border identifier that downstream civic agents (housing, recognition, language schools) can reference without re-classifying Aicha's profession.

### Step 2. suggest_relevant_companies(targetRoles, industry=healthcare)

```json
{
  "tool": "suggest_relevant_companies",
  "arguments": {
    "targetRoles": [
      "Pflegehelfer",
      "Pflegefachkraft"
    ],
    "industry": "healthcare",
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
      "relevanceScore": 0.65,
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
      "relevanceScore": 0.65,
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
      "relevanceScore": 0.65,
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
      "relevanceScore": 0.65,
      "relevanceReason": "European e-health platform with engineering and product roles in Berlin, Paris, and remote.",
      "watchEnabled": true
    },
    "... (14 more)"
  ]
}
```


### Step 3. add_company_to_watchlist(userId, name, websiteUrl)

```json
{
  "tool": "add_company_to_watchlist",
  "arguments": {
    "userId": "u-aicha",
    "name": "Charite - Universitaetsmedizin Berlin",
    "websiteUrl": "https://pflege-berlin-mitte.example.invalid",
    "sector": "healthcare",
    "notes": "Surfaced from ESCO occupation lookup + curated suggestion."
  }
}
```

**Response (ok):**

```json
{
  "status": "ok",
  "company": {
    "user_id": "u-aicha",
    "name": "Charite - Universitaetsmedizin Berlin",
    "website_url": "https://pflege-berlin-mitte.example.invalid",
    "career_page_url": null,
    "sector": "healthcare",
    "relevance_score": null,
    "relevance_reason": null,
    "watch_enabled": true,
    "notes": "Surfaced from ESCO occupation lookup + curated suggestion.",
    "id": "company_895757a548014462bad1a85cd30a217b",
    "created_at": "2026-05-20T22:54:02.050163+00:00",
    "updated_at": "2026-05-20T22:54:02.050170+00:00"
  }
}
```

**Composability anchor:** company id `company_895757a548014462bad1a85cd30a217b` is now the shared key for subsequent extract / scan / consent calls.

### Step 4. extract_direct_jobs_from_company_site(html=<fixture>)

```json
{
  "tool": "extract_direct_jobs_from_company_site",
  "arguments": {
    "userId": "u-aicha",
    "companyId": "company_895757a548014462bad1a85cd30a217b",
    "pageUrl": "https://pflege-berlin-mitte.example.invalid/karriere",
    "html": "<HTML fixture: 30 lines with JSON-LD JobPosting>"
  }
}
```

**Response (ok):**

```json
{
  "status": "ok",
  "jobs": [
    {
      "user_id": "u-aicha",
      "source_url": "https://pflege-berlin-mitte.example.invalid/karriere",
      "title": "Pflegehelfer:in (m/w/d) -- Anerkennungsweg",
      "company_id": "company_895757a548014462bad1a85cd30a217b",
      "location": "Berlin, DE",
      "raw_snippet": "Pflegehelfer:in (m/w/d) -- Anerkennungsweg",
      "raw_description": "Wir begleiten internationale Pflegekraefte durch die Anerkennung nach 16d AufenthG. Sprachkurs B1 und supervisierte Praxis vor Ort.",
      "structured_data": {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "title": "Pflegehelfer:in (m/w/d) -- Anerkennungsweg",
        "description": "Wir begleiten internationale Pflegekraefte durch die Anerkennung nach 16d AufenthG. Sprachkurs B1 und supervisierte Praxis vor Ort.",
        "datePosted": "2026-05-15",
        "validThrough": "2026-07-15",
        "employmentType": "FULL_TIME",
        "hiringOrganization": {
          "@type": "Organization",
          "name": "Pflege Berlin Mitte gGmbH"
        },
        "jobLocation": {
          "@type": "Place",
          "address": {
            "@type": "PostalAddress",
            "addressLocality": "Berlin",
            "postalCode": "10115",
            "addressCountry": "DE"
          }
        }
      },
      "confidence_score": 1.0,
      "imported_job_id": null,
      "auto_fit_score": null,
      "auto_fit_reason": null,
      "auto_fit_at": null,
      "auto_fit_provider_id": null,
      "also_seen_at": {},
      "gaps": [],
      "id": "discovered_job_ab90aa329bc94f2193ae14f0baa72d77",
      "discovered_at": "2026-05-20T22:54:02.051164+00:00",
      "created_at": "2026-05-20T22:54:02.051167+00:00",
      "updated_at": "2026-05-20T22:54:02.051167+00:00"
    }
  ]
}
```


### Step 5. get_user_profile_for_consent(userId, scopes)

```json
{
  "tool": "get_user_profile_for_consent",
  "arguments": {
    "userId": "u-aicha",
    "scopes": [
      "identity",
      "residence",
      "employment"
    ]
  }
}
```

**Response (ok):**

```json
{
  "status": "ok",
  "profile": {
    "userId": "u-aicha",
    "scopes": [
      "identity",
      "residence",
      "employment"
    ],
    "schemaVersion": "0.1.0",
    "consentRecordedAt": "2026-05-20T22:54:02+00:00",
    "identity": {
      "userId": "u-aicha",
      "displayName": null,
      "publicHandle": null,
      "preferredLocale": "en"
    },
    "residence": {
      "country": null,
      "statusType": null,
      "workAuthorisation": null
    },
    "employment": {
      "currentStatus": null,
      "targetRoleFamilies": [],
      "languageLevels": {},
      "escoSkillCodes": [],
      "watchedCompanies": 0
    }
  }
}
```

**Composability anchor:** an external civic agent (housing-agent, language-school-agent, recognition-agent) can read this profile with Aicha's explicit consent and compose its own recommendations without round-tripping through helpmefindthejob's UI.

### Step 6. propose_referral(targetAgent='housing-agent')

```json
{
  "tool": "propose_referral",
  "arguments": {
    "userId": "u-aicha",
    "targetAgent": "housing-agent",
    "reason": "Aicha is searching for a 16d-Anerkennung clinical placement in Berlin and will need temporary housing close to the partner clinic. The housing-agent can use the residence + employment scopes from get_user_profile_for_consent above to filter listings near the watchlisted clinic.",
    "context": {
      "city": "Berlin",
      "esco_code": "5321.1",
      "watchlist_company_id": "company_895757a548014462bad1a85cd30a217b"
    }
  }
}
```

**Response (ok):**

```json
{
  "status": "ok",
  "referral": {
    "referralId": "ref-e725168e0c91",
    "schemaVersion": "0.1.0",
    "issuedAt": "2026-05-20T22:54:02+00:00",
    "sourceAgent": "helpmefindthejob",
    "targetAgent": "housing-agent",
    "userId": "u-aicha",
    "intent": "proposed",
    "priority": "routine",
    "reasonCode": "Aicha is searching for a 16d-Anerkennung clinical placement in Berlin and will need temporary housing close to the partner clinic. The housing-agent can use the residence + employment scopes from get_user_profile_for_consent above to filter listings near the watchlisted clinic.",
    "supportingInfo": {
      "city": "Berlin",
      "esco_code": "5321.1",
      "watchlist_company_id": "company_895757a548014462bad1a85cd30a217b"
    },
    "userConsentRequired": true
  }
}
```


### Step 7. record_user_outcome(jobId, outcomeType='applied')

```json
{
  "tool": "record_user_outcome",
  "arguments": {
    "userId": "u-aicha",
    "jobId": "job-company_895757a548014462bad1a85cd30a217b",
    "outcomeType": "applied",
    "note": "Applied to 'Pflegehelfer:in (m/w/d) -- Anerkennungsweg' via direct company portal."
  }
}
```

**Response (ok):**

```json
{
  "status": "ok",
  "event": {
    "outcomeId": "out-6c2787b0f298",
    "userId": "u-aicha",
    "jobId": "job-company_895757a548014462bad1a85cd30a217b",
    "outcomeType": "applied",
    "occurredAt": "2026-05-20T22:54:02+00:00",
    "recordedAt": "2026-05-20T22:54:02+00:00",
    "schemaVersion": "0.1.0",
    "note": "Applied to 'Pflegehelfer:in (m/w/d) -- Anerkennungsweg' via direct company portal."
  }
}
```


## Result

Seven distinct MCP tools, composed into a single user-meaningful outcome: Aicha now has a curated company watchlist, an extracted job posting, a portable consent-scoped civic profile, a housing-agent referral, and a recorded application outcome -- all driven by an external MCP client against a stateless server instance.

Cost-saving doctrine measurement (08-cost-saving-doctrine.md mechanisms 1, 2, 8): the record_user_outcome event in step 7 is the primary substrate partner-pilot evidence is built from.
