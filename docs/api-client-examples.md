<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright (c) 2026 Helpmefindthejob contributors -->

# API client examples — Python, JavaScript, curl

**Audience**: developers integrating Helpmefindthejob's HTTP API into custom workflows. For MCP-client integrations, see [`mcp-integration-guide.md`](mcp-integration-guide.md). For OpenAPI reference, the live `/api/docs` page on any running instance is the canonical source of truth.

**Base URL** for examples below: `https://helpmefindthejob.org` (or your self-hosted URL). All examples use a session cookie for authentication; obtain it via `POST /api/auth/register` or `POST /api/auth/login`.

---

## 1. Registration + sign-in (Python)

```python
import json
import urllib.request
import http.cookiejar


BASE = "https://helpmefindthejob.org"

# Cookie jar persists the session
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

# Register
req = urllib.request.Request(
    f"{BASE}/api/auth/register",
    data=json.dumps({
        "email": "you@example.com",
        "password": "long-strong-password-here",
        "name": "Your Name",
        "acceptTerms": True,
        "acceptPrivacy": True,
    }).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with opener.open(req) as resp:
    user = json.loads(resp.read())["user"]
    print(f"Registered as {user['email']} (id={user['id']})")
# The session cookie is now in `jar` — reuse `opener` for subsequent calls.
```

---

## 2. Update profile (Python)

```python
profile_body = {
    "persona": "aicha",
    "name": "Aïcha",
    "language": "en",
    "ai_provider": "manual",
    "target_roles": ["Registered nurse", "Krankenpfleger"],
    "target_locations": ["Berlin"],
    "cvText": "Registered nurse with 7 years of hospital experience…",
}
req = urllib.request.Request(
    f"{BASE}/api/profile",
    data=json.dumps(profile_body).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with opener.open(req) as resp:
    print(json.loads(resp.read()))
```

---

## 3. Add a company to the watchlist (JavaScript / Node 18+)

Uses the built-in `fetch` API; no dependencies.

```javascript
const BASE = "https://helpmefindthejob.org";

// Re-use the jar between calls: store the Set-Cookie value yourself.
let sessionCookie = ""; // populated by the register/login response

async function addCompany(name, careerPageUrl) {
  const r = await fetch(`${BASE}/api/companies`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Cookie: sessionCookie,
    },
    body: JSON.stringify({
      name,
      website_url: careerPageUrl.replace(/\/karriere.*$/, ""),
      career_page_url: careerPageUrl,
      sector: "Hospital",
    }),
  });
  if (!r.ok) throw new Error(`POST /api/companies failed: ${r.status}`);
  return r.json();
}

const c = await addCompany(
  "Charité Berlin",
  "https://www.charite.de/karriere/"
);
console.log(`Watched company ${c.id} (${c.name})`);
```

---

## 4. Trigger a fit-score on every imported job (curl)

```bash
# 1. Login (cookies into a jar file)
JAR=$(mktemp)
curl -sS -c "$JAR" -X POST https://helpmefindthejob.org/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"…"}' > /dev/null

# 2. Trigger fit-scoring for every imported-but-unscored job
curl -sS -b "$JAR" -X POST https://helpmefindthejob.org/api/imported/auto-fit-unscored \
  -H 'Content-Type: application/json' \
  -d '{}'
```

The response is a JSON `{ "queued": <n>, "estimatedSeconds": <n> }`. The actual scoring happens asynchronously; poll `GET /api/imported` to see scores land.

---

## 5. GDPR Article 20 portable export (curl)

```bash
# 1. Login (as above)
JAR=$(mktemp)
curl -sS -c "$JAR" -X POST https://helpmefindthejob.org/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"…"}' > /dev/null

# 2. Pull the full Article 20 bundle
curl -sS -b "$JAR" https://helpmefindthejob.org/api/data/export > export.json
jq 'keys' export.json
# Expected: 19 top-level keys (user, profile, companies, discoveredJobs,
# importedJobs, scans, savedSearches, watchlistSchedule, aiProvider,
# chatHistory, journeyState, analyticsEvents, supportTickets,
# pushSubscriptions, workspaceMemberships, appVersion, schemaVersion,
# exportedAt, _exportWarnings)

# 3. Per-format exports (job-data subset)
curl -sS -b "$JAR" https://helpmefindthejob.org/api/exports/imported.csv > jobs.csv
curl -sS -b "$JAR" https://helpmefindthejob.org/api/exports/imported.md > jobs.md
```

See [`compliance/article-20-export-proof.md`](https://github.com/maksodf/helpmefindthejob/blob/main/compliance/article-20-export-proof.md) for the recorded round-trip evidence.

---

## 6. Chat-router slash command (Python)

```python
chat_body = {"message": "/find Krankenpfleger in Berlin", "session": "default"}
req = urllib.request.Request(
    f"{BASE}/api/chat/message",
    data=json.dumps(chat_body).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with opener.open(req) as resp:
    payload = json.loads(resp.read())
    reply = payload.get("reply", "")
    state = payload.get("session", {}).get("phase", "")
    print(f"phase={state}  reply={reply[:200]}…")
```

---

## 7. Health and metrics

```bash
# Lightweight liveness probe (for k8s / docker compose)
curl -sS https://helpmefindthejob.org/api/health
# {"ok": true}

# Detailed health (every subsystem)
curl -sS https://helpmefindthejob.org/api/health?detailed=1 | jq '.'
# { "ok": true, "subsystems": { "audit_log": "ok", "encryption_at_rest": "ok", ... } }

# Prometheus-format metrics (operator monitoring)
curl -sS https://helpmefindthejob.org/api/metrics
```

---

## 8. Rate limits and quotas

Per-user defaults: 50 scans / day, 50 AI calls / day, 3 active concurrent scans. The response carries the running quota state under `quotas` for every authenticated call so a client doesn't have to make a separate request:

```python
with opener.open(urllib.request.Request(f"{BASE}/api/profile")) as resp:
    payload = json.loads(resp.read())
    quotas = payload.get("quotas", {})
    print(f"scans today: {quotas.get('scansToday')}/{quotas.get('scansLimitPerDay')}")
```

When a quota is exhausted, calls return `429 Too Many Requests` with `Retry-After` set to the next reset window.

---

## 9. Error shape (RFC 7807-style)

Every error response has this shape:

```json
{
  "type": "https://helpmefindthejob.org/errors/quota-exceeded",
  "title": "AI call quota exceeded for today",
  "status": 429,
  "detail": "You have used 50 of 50 AI calls today; quota resets at 00:00 UTC.",
  "instance": "/api/chat/message"
}
```

The `type` URI is a stable identifier suitable for client-side branching; the `title` and `detail` are human-readable English.

---

## 10. OpenAPI spec

The full OpenAPI 3.1 spec is served at `GET /api/openapi.json`. Render it as interactive docs at `/api/docs`. The spec is auto-generated from the route definitions in `app.py`; any drift between code and spec is a bug — file an issue.

To regenerate clients (TypeScript, Python, Go, Rust, …) use OpenAPI Generator:

```bash
openapi-generator-cli generate \
  -i https://helpmefindthejob.org/api/openapi.json \
  -g typescript-fetch \
  -o ./helpmefindthejob-client
```

---

## What this guide does NOT cover

- WebSocket endpoints (none currently — the chat surface is request/response)
- Server-Sent Events (used by streaming AI flows; documented in `/api/docs`)
- Admin endpoints (`/api/admin/*`; documented but require the `admin` role)
- Webhook endpoints (Stripe billing, push notifications, GitHub event ingestion)
- Custom MCP integration — see [`mcp-integration-guide.md`](mcp-integration-guide.md)
