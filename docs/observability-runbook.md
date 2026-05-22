<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# Observability runbook

This runbook documents how to wire the three observability backends
(Sentry / PostHog / Grafana + Prometheus) that the project supports
out-of-the-box. The substrate is **opt-in by env var** — the default
build ships with zero third-party dependencies and zero outbound
telemetry. Every backend below activates only when the operator
explicitly configures it.

Phase2-backlog #17 closure.

---

## Quick reference

| Backend | What you get | Activated by | Cost when off |
|---|---|---|---|
| **Sentry** | Captured exceptions with sanitised context tags | `HELPMEFINDTHEJOB_SENTRY_DSN` env var + `sentry-sdk` pip install | Zero — function returns False, no network call |
| **PostHog** | Product-event funnel (signups, applies, etc.) | `HELPMEFINDTHEJOB_POSTHOG_KEY` env var | Zero — function returns False, no network call |
| **Prometheus / Grafana** | HTTP request counters + duration histogram + scheduler gauge | Always on; scrape `/api/metrics` | Negligible — in-memory only; bounded label cardinality |

---

## 1. Sentry (error reporting)

### What activates

Operator sets:

```bash
export HELPMEFINDTHEJOB_SENTRY_DSN="https://<key>@sentry.io/<project>"
pip install sentry-sdk
```

After both are in place, every `report_error(exc, context=...)`
call dispatches to Sentry. The substrate auto-initialises Sentry on
the first call with `traces_sample_rate=0.0` — this disables
performance tracing (which can sample PII out of HTTP request
bodies). Only explicit `report_error` calls send data.

### What gets sent

- Exception type + traceback
- Sanitised context tags (PII keys redacted by
  `observability._sanitise_for_telemetry`)
- Severity level (default: `error`)

### What does NOT get sent

- Request bodies (no `before_send` hook is wired by default)
- User identifiers (no `set_user()` call)
- Performance traces (rate is 0.0)

If a deployer wants user-context attribution, they should wire
the HMAC-hashed audit-log user id explicitly — see
`audit_log._hash_user_id`.

### Default backend = log-only

When the DSN is unset, errors that the project itself raises into
`report_error` are silently dropped. The project's other audit
trails (HMAC-chained `audit.jsonl` + analytics events) remain the
primary record-of-truth.

---

## 2. PostHog (product analytics)

### What activates

```bash
export HELPMEFINDTHEJOB_POSTHOG_KEY="phc_<your-project-key>"
# Optional — defaults to EU host for GDPR-by-default:
export HELPMEFINDTHEJOB_POSTHOG_HOST="https://eu.posthog.com"
```

No SDK needed — the substrate uses `urllib` to POST to the
PostHog `/capture/` endpoint over plain HTTPS.

### What gets sent

Every `emit_event(name, properties=..., distinct_id=...)` call
produces:

```json
{
  "api_key": "phc_xxx",
  "event": "<event-name>",
  "properties": {
    "<sanitised properties>": "<...>",
    "$lib": "helpmefindthejob/observability",
    "$lib_version": "0.1.0"
  },
  "distinct_id": "<HMAC-hashed user id or 'anonymous'>",
  "timestamp": "2026-05-22T12:00:00Z"
}
```

### What does NOT get sent

- Plain user IDs — callers MUST pass HMAC-hashed `distinct_id`
- PII properties (email / cv_text / token / etc.) — stripped by
  `_sanitise_for_telemetry` before dispatch
- Strings > 1000 chars — truncated with `<...truncated>` suffix

### Network failure handling

PostHog dispatch has a **1.0 s timeout**. If the request times out
or fails, `emit_event` returns False — the calling code path is
unaffected. Product analytics MUST NOT slow the request path.

---

## 3. Prometheus + Grafana (metrics)

### What activates

Always-on by default. Scrape the endpoint:

```bash
curl http://<your-deployment>/api/metrics
```

The endpoint returns Prometheus exposition format (`text/plain;
version=0.0.4`) with `Cache-Control: no-store`.

### Prometheus scrape config

```yaml
# prometheus.yml
scrape_configs:
  - job_name: helpmefindthejob
    metrics_path: /api/metrics
    scrape_interval: 30s
    static_configs:
      - targets: ['helpmefindthejob.example.com:443']
        labels:
          environment: production
          deployer: my-ngo
```

### Built-in metrics

| Name | Kind | Labels | What it measures |
|---|---|---|---|
| `helpmefindthejob_http_requests_total` | counter | method, status_class | Every HTTP request. status_class is `2xx`/`3xx`/`4xx`/`5xx`/`unknown` — bounded cardinality. |
| `helpmefindthejob_http_request_duration_seconds` | histogram | method | Per-request duration. Default buckets cover 5ms → 60s (AI-call latency upper bound). |
| `helpmefindthejob_scheduler_active_jobs` | gauge | (none) | Number of enabled scheduled scan jobs. Refreshed on every scrape. |

### Cardinality discipline

- **Method** is capped at 8 characters and only takes standard HTTP
  verbs.
- **status_class** is one of 5 values.
- We intentionally do NOT label by full URL path — `/jobs/<slug>`,
  `/api/companies/<id>` etc. would explode cardinality. Deployers
  needing per-path drill-down should wire app-level
  instrumentation around specific routes (call
  `observability.inc("<your_metric>", labels=...)`).

### Adding custom metrics

```python
from company_discovery.observability import inc, observe, set_gauge

# Counter:
inc("my_metric", labels={"feature": "fit_score"})

# Histogram (auto-buckets):
observe("my_latency", elapsed_seconds, labels={"provider": "openai"})

# Gauge (overwrites):
set_gauge("my_queue_depth", current_depth)
```

All three functions are thread-safe (single process-local lock).
Process restart zeroes the registry — durable history comes from
Prometheus's own retention.

### Sample Grafana dashboard queries

```promql
# Request rate by method (req/s)
rate(helpmefindthejob_http_requests_total[5m])

# 95th-percentile response time per method
histogram_quantile(
  0.95,
  sum(rate(helpmefindthejob_http_request_duration_seconds_bucket[5m])) by (le, method)
)

# Error rate (4xx + 5xx)
sum(rate(helpmefindthejob_http_requests_total{status_class=~"4xx|5xx"}[5m]))
  / sum(rate(helpmefindthejob_http_requests_total[5m]))
```

---

## 4. PII discipline across all three backends

Every backend goes through `_sanitise_for_telemetry` before
dispatch:

```python
_PII_KEYS = {
    "email", "email_address", "cv_text", "cv", "cvText",
    "password", "password_hash", "token", "authorization",
    "auth", "session_token", "api_key", "apikey",
    "phone", "phone_number", "address", "name", "full_name",
    "first_name", "last_name", "given_name", "surname",
    "ssn", "passport", "national_id",
}
```

Match is **case-insensitive**. Long strings (> 1000 chars) are
truncated with a `<...truncated>` suffix. Nested dicts + lists
are walked recursively.

If a deployer adds a new property that should be treated as PII,
they should extend `_PII_KEYS` in
`company_discovery/observability.py` (and add a test case in
`tests/test_observability_substrate.py`).

---

## 5. Cost framing

Observability is operator-side infrastructure. Helpmefindthejob
maintainers don't operate a central telemetry endpoint — every
deployer brings their own (Sentry account / PostHog account /
Prometheus host). This matches the project's federated
deployment doctrine.

For a small NGO deployment, the recommended stack is:

- **Errors**: Sentry's free tier (5,000 errors/month)
- **Product analytics**: PostHog Cloud EU free tier (1M events/
  month) — note the EU host for GDPR-by-default
- **Metrics**: self-hosted Prometheus + Grafana (free, ~$5/mo on
  any small VM)

Total typical cost for a deployment serving 1000 active users: $0–$15/month.

---

## Provenance

Authored 2026-05-22 (phase2-backlog #17). Substrate implemented in
`company_discovery/observability.py`. Tests in
`tests/test_observability_substrate.py` pin: env-gate honoured, PII
sanitiser, Prometheus exposition format, /api/metrics live
endpoint, HTTP-request auto-instrumentation via the
`Handler.log_request` override.
