<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Friction-Class Specification, v0.1

**Status**: draft for community comment.
**License**: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) —
this specification is published as a contribution to the civic-services
commons. Implementations are encouraged.
**Editor**: helpmefindthejob contributors, with intent to transfer
custodianship to [The Commons Conservancy](https://commonsconservancy.org)
upon programme acceptance.
**Reference implementation**: [helpmefindthejob](https://github.com/maksodf/helpmefindthejob)
(Apache-2.0).
**Companion documents**: [civic-services mesh README](../mesh/README.md),
[AI Act audit-log schema](../compliance/audit-log-schema.md).

---

## Abstract

This specification defines **friction-class** — a structured way for
civic-services agents (employment, housing, social-services,
Anerkennung, legal-aid, …) to classify users by the **patterns of
bureaucratic friction they face**, rather than by demographic categories
(nationality, ethnicity, religion).

The classification produces a stable cohort identifier each agent can
use to (a) tailor decision logic, (b) measure outcomes, (c) coordinate
across the civic-services mesh — without ever sharing demographic
attributes between agents.

Adoption is a strictly opt-in act by the user (Article 7 GDPR
consent). Agents that adopt this specification MUST emit a
classification + receipt the user can verify offline.

---

## 1. Why "friction-class" instead of demographic classification

Civic-services products that segment users by nationality, ethnicity,
or religion accumulate three kinds of harm:

1. **Disparate impact.** Demographic categories are correlated with
   policy outcomes via the SYSTEMS the user faces, not via the
   user's identity. A Tunisian nurse and a Filipino nurse face the
   same §16d Anerkennungsverfahren — friction is in the pathway,
   not the person.

2. **Stigma.** Storing "is_migrant: true" against a user record
   marks them in a way that survives the lifetime of the data — and
   leaks into other systems (insurance underwriting, credit scoring,
   surveillance).

3. **Brittleness.** Demographic categories under-cover legitimate
   users (a third-generation child of Turkish guest workers facing
   the Quereinstieg friction class is not "a migrant" but faces
   bureaucratic friction the platform should recognise).

**Friction-class is policy-pathway-keyed**, not person-keyed. The
class identifies WHAT the user is navigating, not WHO the user is.
A user can be in multiple friction classes simultaneously
(`anerkennung_track` + `wiedereinstieg_after_career_break`) and can
exit a class as their pathway completes.

---

## 2. The seven friction classes (v0.1)

Each class is identified by a stable slug + a human-readable label
in EN and DE. Slugs use lowercase ASCII letters, digits and
underscores; max 32 characters; first character must be a letter.

| Slug                        | Label (EN)                                      | Cohort axis        |
|----------------------------|--------------------------------------------------|--------------------|
| `aicha_paragraph_16d`       | §16d Anerkennung-track (regulated profession)    | most-acute migrant |
| `yusuf_blue_card`           | EU Blue Card / high-skill third-country worker   | most-acute migrant |
| `olga_paragraph_24`         | §24 temporary protection (Ukraine + future)      | most-acute migrant |
| `mahmoud_paragraph_4_asylg` | §4 AsylG subsidiary protection                   | most-acute migrant |
| `maria_eu_citizen_intra_eu` | EU citizen exercising Freizügigkeit              | most-acute migrant |
| `kaethe_wiedereinstieg`     | Re-entry after career break (parental leave +)   | wider friction     |
| `tobias_quereinstieg`       | Career-change / cross-industry transition        | wider friction     |

**Cohort axes** are an orthogonal grouping for bias-methodology
fairness comparison. The v0.1 axes are:

- **most-acute migrant** (5 classes) — users facing the highest
  bureaucratic friction from the residency / recognition pathway.
- **wider friction** (2 classes) — users facing significant
  bureaucratic friction NOT rooted in migration (re-entry,
  cross-industry).

A v0.2 of this specification is expected to add classes outside the
employment domain (housing-friction, family-friction,
healthcare-access-friction). The slug + label pattern stays stable
across versions.

---

## 3. Classification signals

Agents implementing this spec SHOULD derive friction-class assignment
from **biographical pathway signals** the user explicitly provides,
NOT from inferred demographic attributes.

The canonical signals (v0.1) are:

| Signal               | Type      | Source                                                                           |
|----------------------|-----------|----------------------------------------------------------------------------------|
| `residency_status`   | string    | User-confirmed value from a controlled vocabulary (see §3.1)                     |
| `qualification_field`| string    | User-confirmed value from ESCO occupations / skills                              |
| `career_intent`      | string    | User-confirmed from `{job_search, career_change, re_entry, anerkennung_path}`    |
| `country_of_origin`  | string    | OPTIONAL — only when relevant to a recognition pathway (e.g. Anerkennung)         |
| `time_since_last_employment` | int (months) | OPTIONAL — supports re-entry detection                                  |
| `years_experience`   | int       | OPTIONAL — disambiguates Quereinstieg vs early-career                            |

Agents MUST NOT use the following signals for classification:
nationality (vs residency status), ethnicity, religion,
political affiliation, sexual orientation, gender identity.

### 3.1 Controlled vocabulary for `residency_status`

| Value             | German label                                         |
|-------------------|------------------------------------------------------|
| `paragraph_16d`   | Aufenthaltserlaubnis § 16d (Anerkennung)             |
| `blue_card`       | Blaue Karte EU                                       |
| `paragraph_24`    | Aufenthaltserlaubnis § 24 (temporärer Schutz)        |
| `paragraph_4_asylg`| Subsidiärer Schutz § 4 AsylG                        |
| `eu_freizugigkeit`| Freizügigkeit EU                                     |
| `niederlassung`   | Niederlassungserlaubnis                              |
| `german_citizen`  | Deutsche Staatsangehörigkeit                         |
| `other`           | Sonstiger Aufenthaltstitel                           |

Implementations adding values SHOULD propose them via the
specification's issue tracker before deployment so the controlled
vocabulary stays coordinated across agents.

---

## 4. Classification output contract

A classifier producing a friction-class assignment MUST return a
structured object with the following minimum fields:

```json
{
  "schemaVersion": "0.1.0",
  "frictionClass": "aicha_paragraph_16d",
  "cohortAxis": "most-acute migrant",
  "confidence": 0.92,
  "signalsConsidered": ["residency_status", "qualification_field"],
  "classifiedAt": "2026-05-21T13:42:00Z",
  "issuingAgent": "did:web:helpmefindthejob.org",
  "userConsentReceivedAt": "2026-05-21T13:40:00Z"
}
```

Field semantics:

- `confidence` — float in `[0, 1]`. Implementations SHOULD calibrate
  via held-out test sets and publish their calibration curve.
- `signalsConsidered` — array of signal names actually used to make
  the decision. NOT a list of signals the user supplied; this is the
  AUDIT surface.
- `userConsentReceivedAt` — ISO 8601 timestamp of the most recent
  consent capture. Classifiers MUST refuse to emit when no consent
  has been recorded.

---

## 5. Trust Receipt requirement

Every friction-class assignment MUST be accompanied by a
**Trust Receipt** the user can download. The receipt schema is
defined in [`helpmefindthejob/company_discovery/trust_receipt.py`](
../company_discovery/trust_receipt.py); a v1 receipt for a
friction-class decision uses `decisionType: "friction_class"`.

The receipt allows the user to prove — without trusting the
agent — that:

1. WHEN the classification was made
2. WHICH signals were used (via `metadata.signalsConsidered`)
3. WHO issued it (via `issuerDid`)
4. WHAT the classification was (via `responseHash` + the
   receipt's `metadata.frictionClass`)
5. THAT no demographic signals were used (the receipt's
   audit-log linkage allows cross-checking against the deployer's
   audit log)

---

## 6. Cross-agent transmission

When a user consents to share their friction-class assignment with
another agent (via `propose_referral` or a portable Verifiable
Credential), the receiving agent:

- MUST verify the Trust Receipt's signature before acting
- MUST re-confirm the user's consent to use this class for THIS
  agent's decision (consent does not transfer transitively)
- MUST emit its own Trust Receipt for any downstream decision

The recommended cross-agent transmission shape is a W3C Verifiable
Credential of type `FrictionClassCredential`:

```json
{
  "@context": [
    "https://www.w3.org/ns/credentials/v2",
    "https://helpmefindthejob.org/vc/friction-class/v1"
  ],
  "type": ["VerifiableCredential", "FrictionClassCredential"],
  "issuer": "did:web:helpmefindthejob.org",
  "validFrom": "2026-05-21T13:42:00Z",
  "credentialSubject": {
    "id": "did:web:user.example.com:opaque-hash",
    "frictionClass": "aicha_paragraph_16d",
    "cohortAxis": "most-acute migrant",
    "confidence": 0.92,
    "signalsConsidered": ["residency_status", "qualification_field"]
  },
  "proof": { ... Ed25519 signature ... }
}
```

The reference implementation's anerkennung-agent
(`mesh/anerkennung_agent.py`) consumes this credential shape.

---

## 7. Rendering & UI contract

Implementations rendering a friction-class to the user MUST:

1. Show the human-readable label (EN or DE per user locale), NOT
   the slug.
2. Surface the `confidence` value when below 0.80 ("we're not sure
   yet — please confirm").
3. Allow the user to **dispute** the classification in one click;
   the dispute MUST flow back to the classifier as
   `friction_class_dispute` evidence the classifier improves from.
4. Display any institutional caveat that applies to the class
   (e.g. for `aicha_paragraph_16d`: "Some applications may require
   contact with the Ausländerbehörde before submission").

---

## 8. Fairness contract

Implementations claiming compliance with this specification SHOULD:

- Run the [bias methodology test harness](
  ../docs/grant/methodology.md) (or equivalent) across all 7
  friction classes and publish the comparative report.
- Document any per-class accuracy variance > 10 percentage points
  vs the cross-class mean.
- Publish per-class refusal rates (cap-exhausted, consent-missing,
  signals-insufficient) so deployer policy can be audited.

---

## 9. Versioning

This specification follows semantic versioning. Within a major
version, the set of friction-classes and signals is additive only —
new classes / signals may be added; existing ones MAY NOT be
removed or have their semantics changed.

The current version is v0.1. v1.0 will be cut when:

1. At least three independent reference implementations exist
2. At least one civic-services deployer has run the fairness
   contract end-to-end and published the report
3. The Commons Conservancy programme has formally accepted
   custodianship

---

## 10. Open questions for v0.2

1. Should `wiedereinstieg` cover only parental leave or any career
   break > 12 months?
2. Is a separate class for `paragraph_4a_asylg` (humanitarian
   protection, time-limited) warranted, or does it fold into
   `paragraph_4_asylg`?
3. How should classes overlap (a user can be both `tobias_quereinstieg`
   AND `kaethe_wiedereinstieg`)? Should the output be a SINGLE class
   or a SET?
4. Should we add a `cohortAxis = wider-friction` class for users
   over 50 facing age-discrimination friction?

Comments welcome at the project's issue tracker.

---

## 11. References

- [GDPR Article 22 — automated decision-making](https://gdpr-info.eu/art-22-gdpr/)
- [EU AI Act, Article 50 — transparency obligations](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=OJ%3AL_202401689)
- [W3C Verifiable Credentials Data Model v2.0](https://www.w3.org/TR/vc-data-model-2.0/)
- [ESCO classification](https://esco.ec.europa.eu/)
- [EURES portal](https://eures.ec.europa.eu/)
- [Bundesagentur für Arbeit — Anerkennung](https://www.arbeitsagentur.de/karriere-und-weiterbildung/qualifizierte-berufstaetige/anerkennung-auslaendischer-berufsabschluesse)

---

## Changelog

- **2026-05-21** — v0.1 draft published. 7 friction classes,
  2 cohort axes, controlled residency-status vocabulary, Trust
  Receipt + Verifiable Credential transmission contract.
