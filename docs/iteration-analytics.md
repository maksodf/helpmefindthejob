# Iteration analytics — SQL pack

Drop-in queries the operator runs once there are real users on the system. Each query answers one question from the tracker #65 spec ("Iterate on the differentiator features based on first 100 paying users' actual usage data") so the operator doesn't burn a quarter writing analytics infrastructure.

Run via the existing `analytics_events` + `imported_jobs` + `users` tables on the production droplet:

```sh
ssh -i ~/.ssh/helpmefindthejob root@161.35.76.8 \
  "docker exec -i helpmefindthejob-app sqlite3 /app/data/company_discovery.sqlite3 < /tmp/<query>.sql"
```

Or interactively via the admin panel's analytics widget once it ships. For now, raw SQL is the source of truth.

All queries are read-only. Idempotent. Safe to re-run.

---

## 1. Signup funnel — where do users drop off?

```sql
WITH users AS (
  SELECT
    id,
    DATE(created_at) AS signup_day,
    email_verified_at IS NOT NULL AS verified
  FROM users
  WHERE active = 1
),
activity AS (
  SELECT
    user_id,
    COUNT(*) FILTER (WHERE kind = 'cv_uploaded') AS cv_uploads,
    COUNT(*) FILTER (WHERE kind = 'auto_fit') AS auto_fits,
    COUNT(*) FILTER (WHERE kind = 'cv_tailoring') AS tailorings,
    COUNT(*) FILTER (WHERE kind = 'welcome_email_sent') AS welcomed
  FROM analytics_events
  GROUP BY user_id
)
SELECT
  u.signup_day,
  COUNT(*)                                                      AS signups,
  SUM(CASE WHEN u.verified THEN 1 ELSE 0 END)                   AS verified,
  SUM(CASE WHEN COALESCE(a.cv_uploads, 0) > 0 THEN 1 ELSE 0 END) AS cv_added,
  SUM(CASE WHEN COALESCE(a.auto_fits, 0) > 0 THEN 1 ELSE 0 END)  AS ran_autofit,
  SUM(CASE WHEN COALESCE(a.tailorings, 0) > 0 THEN 1 ELSE 0 END) AS tailored
FROM users u
LEFT JOIN activity a ON a.user_id = u.id
GROUP BY u.signup_day
ORDER BY u.signup_day;
```

**Read it as:** for each signup-day cohort, the funnel from `signups → verified → cv_added → ran_autofit → tailored`. Drop-off between any two columns identifies a friction point. The biggest drop is the highest-leverage thing to fix.

---

## 2. Day-1 retention — do users come back?

```sql
WITH first_login AS (
  SELECT id, DATE(created_at) AS day0
  FROM users
  WHERE active = 1
),
activity AS (
  SELECT
    user_id,
    DATE(created_at) AS event_day
  FROM analytics_events
  GROUP BY user_id, DATE(created_at)
)
SELECT
  fl.day0,
  COUNT(DISTINCT fl.id) AS cohort_size,
  COUNT(DISTINCT CASE WHEN a.event_day = DATE(fl.day0, '+1 day') THEN fl.id END) AS returned_d1,
  COUNT(DISTINCT CASE WHEN a.event_day = DATE(fl.day0, '+7 days') THEN fl.id END) AS returned_d7,
  COUNT(DISTINCT CASE WHEN a.event_day = DATE(fl.day0, '+30 days') THEN fl.id END) AS returned_d30
FROM first_login fl
LEFT JOIN activity a ON a.user_id = fl.id
GROUP BY fl.day0
ORDER BY fl.day0;
```

**Read it as:** D1 retention < 40% means the onboarding wizard / first-run UX is broken. D7 retention < 20% means the queue isn't surfacing useful jobs early enough. D30 retention < 10% means we have a saved-search-quality problem.

---

## 3. Reply-rate distribution — does the product work?

```sql
SELECT
  COUNT(*) FILTER (WHERE replied_at IS NOT NULL) AS replied,
  COUNT(*) FILTER (WHERE application_status IN ('applied','interview','rejected','archived')) AS total_apps,
  ROUND(
    100.0 * COUNT(*) FILTER (WHERE replied_at IS NOT NULL)
    / NULLIF(COUNT(*) FILTER (WHERE application_status IN ('applied','interview','rejected','archived')), 0),
    1
  ) AS reply_rate_pct
FROM imported_jobs;
```

**Read it as:** below 5% reply rate is alarmingly low — either the saved searches surface bad-fit roles (queue quality) or the cover-letter drafts are weak (CV-tailoring quality). Above 25% is suspiciously high — investigate whether users are only marking obvious replies (selection bias).

---

## 4. Skill-gap atlas — what gaps come up most?

```sql
WITH gaps_extracted AS (
  SELECT
    json_extract(payload, '$.gaps') AS gaps_json
  FROM imported_jobs_payload
  WHERE json_extract(payload, '$.gaps') IS NOT NULL
)
SELECT
  TRIM(LOWER(value)) AS skill,
  COUNT(*)           AS occurrences
FROM gaps_extracted, json_each(gaps_json)
WHERE value IS NOT NULL AND LENGTH(TRIM(value)) > 0
GROUP BY TRIM(LOWER(value))
ORDER BY occurrences DESC
LIMIT 20;
```

**Read it as:** the top 20 skills the auto-fit AI has flagged as "demanded but missing" across the entire user base. If "Kubernetes" appears 200 times, that's a content opportunity — write a "/learn/kubernetes-for-DACH-engineers" guide and link from the skill-gap card.

(SQLite-specific: requires the json1 extension, which is built into the standard `sqlite3` binary in Docker. Adjust the CTE name `imported_jobs_payload` to match the actual table.)

---

## 5. CV-variant attribution — which tailoring wins?

```sql
WITH variant_outcomes AS (
  SELECT
    j.user_id,
    json_extract(v.value, '$.index')           AS variant_index,
    json_extract(v.value, '$.attributedReply') AS attributed_reply
  FROM imported_jobs j, json_each(j.cv_variants) v
)
SELECT
  variant_index,
  COUNT(*)                                            AS times_tailored,
  SUM(CASE WHEN attributed_reply = 1 THEN 1 ELSE 0 END) AS replies_attributed,
  ROUND(
    100.0 * SUM(CASE WHEN attributed_reply = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
    1
  ) AS rate_pct
FROM variant_outcomes
GROUP BY variant_index
ORDER BY variant_index;
```

**Read it as:** if variant 2 has a 40% reply rate vs variant 1 at 10%, the second-pass tailoring earns a real reply lift. Surface that as a recommendation in the UI: "Most users see better replies after their second tailor — try once more."

---

## 6. Onboarding email open / click rate (proxy)

The transactional outbox doesn't track opens (we don't pixel-track per the privacy-first stance — see `docs/cookie-audit.md`). The proxy: how soon after a drip email did the user run their first auto-fit / saved-search?

```sql
SELECT
  DATE(u.created_at) AS signup_day,
  COUNT(DISTINCT u.id) AS cohort_size,
  AVG(
    CASE
      WHEN u.drip_day3_sent_at IS NOT NULL THEN
        (julianday(MIN(a.created_at)) - julianday(u.drip_day3_sent_at)) * 24
      END
  ) AS avg_hours_to_first_action_after_day3
FROM users u
LEFT JOIN analytics_events a
  ON a.user_id = u.id
 AND a.kind IN ('saved_search_created', 'auto_fit', 'cv_uploaded')
 AND a.created_at > u.drip_day3_sent_at
WHERE u.drip_day3_sent_at IS NOT NULL
GROUP BY DATE(u.created_at)
ORDER BY DATE(u.created_at);
```

**Read it as:** the day-3 drip is doing its job if `avg_hours_to_first_action_after_day3` is < 24h for the cohort. > 72h means users aren't reading or aren't motivated. Try a different subject line; A/B via #61.

---

## When to run

- **Weekly**, every Monday morning, for the first 90 days post-launch.
- **Monthly** thereafter — by then the cohort sizes are big enough that weekly noise dominates.
- After **any** product release flagged "expected to move metrics" in the changelog: re-run within 48h to verify direction-of-effect.

Track the running numbers in a single sheet (signup_day | signups | verified | d1 | d7 | reply_rate | top_gap | top_variant). One row per week. After three months that sheet IS the iteration roadmap.

## What NOT to over-fit

- **Single-week noise.** Cohorts < 30 are noise. Don't iterate on a 5-user cohort.
- **Self-reported feedback.** Two enthusiastic users != product-market fit. Trust the retention curve, not the testimonials.
- **Vanity metrics.** Total signups grow monotonically by definition. The metric that moves with product quality is D7 retention, not cumulative signups.
