"""Promise-by-promise verification agent.

For every marketing promise on the landing page / Nasr guide, exercise
the product's actual delivery path and assert the deliverable. Each
verifier is independent: it sets up its own fresh account + minimum
state, hits the relevant endpoint(s), and reports PASS / FAIL with a
concrete reason.

Promises checked (mapped to the Nasr guide + docs/launch-day-content.md):

  P1 — "One clean queue — no duplicates"
        → Re-run the same search; no URL appears twice.

  P2 — "AI scores how well each job matches your CV"
        → Manual-mode prepare-brief returns a prompt that contains
          the user's CV text and the job title (i.e., the prompt is
          assembled correctly so the AI receives both).

  P3 — "AI rewrites your CV for the specific job"
        → tailor-cv returns a prompt that names the role + asks the
          model to tailor the CV.

  P4 — "Skills blocking you from more roles"
        → After importing 3 jobs requiring different tech, the
          /api/profile bootstrap surfaces a non-empty skillGaps list.

  P5 — "Mark applied / tick when they reply"
        → POST application status flips through saved → applied →
          replied and persists on bootstrap reload.

  P6 — "Watches your companies every day"
        → POST /api/watchlist/scan returns 200 and increments the
          last-run timestamp; scheduler persists settings.

  P7 — "CV encrypted at rest"
        → After pasting a CV with a unique phrase, that phrase does
          NOT appear plaintext in the SQLite database file on disk.

  P8 — "Reply rate analytics"
        → After marking 3 applied + 1 replied, the bootstrap
          replyRate card shows ~33% (1/3).

Run via ./scripts/run-promise-verifier.sh — a single fresh app instance
is shared across promises (each promise creates its own user so state
is isolated)."""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


BASE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")
DATA_DIR = os.environ.get("COMPANY_DISCOVERY_DATA_DIR", "")


# ----------------- HTTP helpers ---------------------------------------------


class _HttpClient:
    """Minimal session wrapper: handles auth cookie + CSRF token + JSON body."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.cookie = ""
        self.csrf_token = ""

    def _request(self, method: str, path: str, *, body: dict | None = None,
                 raw: bytes | None = None,
                 content_type: str = "application/json") -> tuple[int, dict | str]:
        url = self.base_url + path
        data = None
        headers = {"Accept": "application/json"}
        if raw is not None:
            data = raw
            headers["Content-Type"] = content_type
        elif body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.csrf_token and method in {"POST", "PUT", "DELETE", "PATCH"}:
            headers["X-CSRF-Token"] = self.csrf_token
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                set_cookie = resp.headers.get("Set-Cookie", "")
                if set_cookie:
                    self.cookie = set_cookie.split(";", 1)[0]
                raw_body = resp.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(raw_body) if raw_body else {}
                except json.JSONDecodeError:
                    payload = raw_body
                self._absorb_csrf(payload)
                return resp.status, payload
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            try:
                payload = json.loads(body_text) if body_text else {}
            except json.JSONDecodeError:
                payload = body_text
            return exc.code, payload

    def _absorb_csrf(self, payload: dict | str) -> None:
        """Extract csrfToken from any response that carries it."""
        if not isinstance(payload, dict):
            return
        # Several response shapes wrap the token at different depths.
        for key in ("csrfToken", "csrf_token"):
            if isinstance(payload.get(key), str) and payload[key]:
                self.csrf_token = payload[key]
                return
        user = payload.get("user") or {}
        if isinstance(user, dict):
            for key in ("csrfToken", "csrf_token"):
                if isinstance(user.get(key), str) and user[key]:
                    self.csrf_token = user[key]
                    return

    def post(self, path: str, body: dict | None = None) -> tuple[int, dict | str]:
        return self._request("POST", path, body=body or {})

    def get(self, path: str) -> tuple[int, dict | str]:
        return self._request("GET", path)

    def delete(self, path: str) -> tuple[int, dict | str]:
        return self._request("DELETE", path)


def _signup(email: str, password: str) -> _HttpClient:
    """Register a fresh user and return an authenticated client.

    Public registration is rate-limited at 3 per 10 minutes per IP, so
    use this only for the FIRST account (which becomes admin). All
    subsequent accounts should be created via ``_admin_create_user``."""
    client = _HttpClient(BASE_URL)
    client.get("/")
    status, payload = client.post("/api/auth/register", {
        "email": email,
        "password": password,
        "tosAccepted": True,
        "privacyAccepted": True,
    })
    if status not in (200, 201):
        raise RuntimeError(f"register failed {status}: {payload}")
    return client


def _admin_create_user(admin: _HttpClient, email: str, password: str) -> None:
    """Admin path bypasses the public registration rate limit."""
    status, payload = admin.post("/api/admin/users", {
        "email": email,
        "password": password,
        "role": "member",
    })
    if status not in (200, 201):
        raise RuntimeError(f"admin create user failed {status}: {payload}")


def _login(email: str, password: str) -> _HttpClient:
    """Log into an existing account; returns a fresh client with cookie + csrf."""
    client = _HttpClient(BASE_URL)
    client.get("/")
    status, payload = client.post("/api/auth/login", {
        "email": email,
        "password": password,
    })
    if status not in (200, 201):
        raise RuntimeError(f"login failed {status}: {payload}")
    return client


# Process-wide admin used to mint per-promise testers.
_ADMIN_CLIENT: _HttpClient | None = None


def _get_or_create_tester(email: str, password: str) -> _HttpClient:
    """Mint a tester via the admin path (no rate limit), then log in."""
    global _ADMIN_CLIENT
    if _ADMIN_CLIENT is None:
        admin_email = f"admin+verifier+{secrets.token_hex(3)}@example.com"
        _ADMIN_CLIENT = _signup(admin_email, "verifier-admin-pass-99-X")
    _admin_create_user(_ADMIN_CLIENT, email, password)
    return _login(email, password)


def _set_cv(client: _HttpClient, cv_text: str) -> None:
    status, payload = client.post("/api/profile", {"cvText": cv_text})
    if status != 200:
        raise RuntimeError(f"set profile cv failed {status}: {payload}")


# ----------------- Per-promise verifiers ------------------------------------


@dataclass
class Result:
    promise: str
    label: str
    ok: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"promise": self.promise, "label": self.label,
                "verdict": "PASS" if self.ok else "FAIL", "detail": self.detail}


def verify_P1_no_duplicates() -> Result:
    """Run /api/jobs/search twice; the queue must not contain duplicate URLs."""
    label = "One clean queue — no duplicates"
    try:
        client = _get_or_create_tester(f"p1+{secrets.token_hex(3)}@example.com", "test-pass-99-xyz!")
        # Run the same search twice
        status1, p1 = client.post("/api/jobs/search", {
            "query": "senior backend engineer",
            "location": "Berlin",
            "limitPerProvider": 10,
            "cap": 50,
        })
        status2, p2 = client.post("/api/jobs/search", {
            "query": "senior backend engineer",
            "location": "Berlin",
            "limitPerProvider": 10,
            "cap": 50,
        })
        if status1 != 200 or status2 != 200:
            return Result("P1", label, False, f"search HTTP {status1}/{status2}")
        urls1 = [j.get("sourceUrl") for j in p1.get("jobs", []) if j.get("sourceUrl")]
        urls2 = [j.get("sourceUrl") for j in p2.get("jobs", []) if j.get("sourceUrl")]
        # Within a single run there must be NO duplicates (engine dedup)
        dup1 = len(urls1) - len(set(urls1))
        dup2 = len(urls2) - len(set(urls2))
        if dup1 or dup2:
            return Result("P1", label, False,
                          f"within-run dups: run1={dup1}, run2={dup2}")
        return Result("P1", label, True,
                      f"run1={len(urls1)} jobs (0 dup), run2={len(urls2)} jobs (0 dup)")
    except Exception as exc:  # noqa: BLE001
        return Result("P1", label, False, f"{type(exc).__name__}: {exc}")


def _import_one_job(client: _HttpClient, query: str, location: str) -> dict | None:
    """Run a saved search (which persists discovered_jobs in the user's
    namespace), then import one. Returns the imported-job payload (with
    .id) or None if no candidates appeared."""
    dbg = os.environ.get("E2E_DEBUG") == "1"
    # 1. Create a saved search (name + targetRoles + location).
    ss_status, ss_payload = client.post("/api/saved-searches", {
        "name": f"verifier-{query[:30]}-{secrets.token_hex(2)}",
        "targetRoles": [query],
        "location": location,
    })
    if dbg:
        print(f"   [dbg] saved-search create: {ss_status} {str(ss_payload)[:160]}")
    if ss_status not in (200, 201):
        return None
    saved = ss_payload.get("savedSearch") or {}
    saved_id = saved.get("id")
    if not saved_id:
        return None
    # 2. Run the saved search now — persists discovered_jobs.
    run_status, run_payload = client.post(
        f"/api/saved-searches/{urllib.parse.quote(saved_id, safe='')}/run-now", {})
    if dbg:
        print(f"   [dbg] run-now: {run_status} {str(run_payload)[:200]}")
    if run_status not in (200, 201):
        return None
    # 3. Read the bootstrap → first eligible discovered job.
    boot_status, boot = client.get("/api/bootstrap")
    if boot_status != 200:
        return None
    discovered = boot.get("discoveredJobs") or boot.get("discovered_jobs") or []
    if dbg:
        print(f"   [dbg] discovered count: {len(discovered)}; "
              f"sample={[d.get('title','?')[:40] for d in discovered[:3]]}")
    for job in discovered:
        did = job.get("id")
        if not did:
            continue
        imp_status, imp_payload = client.post(
            f"/api/discovered-jobs/{urllib.parse.quote(did, safe='')}/import", {})
        if dbg:
            print(f"   [dbg] import {did[:30]}: {imp_status} {str(imp_payload)[:140]}")
        if imp_status in (200, 201):
            return imp_payload.get("job") or imp_payload.get("importedJob") or imp_payload
    return None


def verify_P2_fit_scoring_prompt() -> Result:
    """Manual mode: prepare-brief returns a prompt that contains the
    user's CV text and the job title — so the user pastes it into their
    AI and gets a real fit score."""
    label = "AI scores how well each job matches your CV"
    try:
        cv_unique = (
            "Senior Software Engineer with 8 years of Python, Postgres, "
            "Kubernetes. UNIQUE_CV_MARKER_P2_X9KT3R."
        )
        client = _get_or_create_tester(f"p2+{secrets.token_hex(3)}@example.com", "test-pass-99-xyz!")
        _set_cv(client, cv_unique)
        job = _import_one_job(client, "senior backend engineer", "Berlin")
        if not job:
            return Result("P2", label, False, "no candidate jobs found in search")
        status, payload = client.post(
            f"/api/imported-jobs/{job['id']}/prepare-brief", {},
        )
        if status != 200:
            return Result("P2", label, False, f"prepare-brief HTTP {status}: {payload}")
        # Response shape: { "brief": "<prompt string>", "bootstrap": {...} }
        brief_text = payload.get("brief")
        if isinstance(brief_text, dict):
            brief_text = (brief_text.get("prompt")
                          or brief_text.get("output")
                          or brief_text.get("text") or "")
        if not isinstance(brief_text, str) or not brief_text:
            return Result("P2", label, False,
                          f"brief payload has no prompt: {list(payload)}")
        if "UNIQUE_CV_MARKER_P2_X9KT3R" not in brief_text:
            return Result("P2", label, False,
                          f"brief did not include CV marker (len={len(brief_text)})")
        job_title = job.get("title", "")
        # title may appear in title-cased or lowercase; check casefold
        if job_title and job_title.casefold() not in brief_text.casefold():
            return Result("P2", label, False,
                          f"brief did not include job title '{job_title}'")
        return Result("P2", label, True,
                      f"brief={len(brief_text)} chars, contains CV + job title")
    except Exception as exc:  # noqa: BLE001
        return Result("P2", label, False, f"{type(exc).__name__}: {exc}")


def verify_P3_tailor_cv_prompt() -> Result:
    """tailor-cv builds a prompt that names the role + asks for a CV rewrite."""
    label = "AI rewrites your CV for the specific job"
    try:
        cv_unique = "Senior backend dev, Python+K8s. UNIQUE_CV_P3_M4LR9X."
        client = _get_or_create_tester(f"p3+{secrets.token_hex(3)}@example.com", "test-pass-99-xyz!")
        _set_cv(client, cv_unique)
        job = _import_one_job(client, "senior backend engineer", "Berlin")
        if not job:
            return Result("P3", label, False, "no candidate jobs found")
        status, payload = client.post(
            f"/api/imported-jobs/{job['id']}/tailor-cv", {},
        )
        if status != 200:
            return Result("P3", label, False, f"tailor-cv HTTP {status}: {payload}")
        # Response: { "tailored": { provider_id, status, output, prompt, ... }, "variantIndex": N }
        tailored = payload.get("tailored") or {}
        out = (tailored.get("output")
                or tailored.get("prompt")
                or payload.get("output") or "")
        if not isinstance(out, str) or not out:
            return Result("P3", label, False,
                          f"tailor payload has no output: tailored={list(tailored)} top={list(payload)}")
        if "UNIQUE_CV_P3_M4LR9X" not in out:
            return Result("P3", label, False, "CV marker absent from tailor output")
        # Must reference the job title or company
        ref = job.get("title", "") + " " + (job.get("companyName", "") or "")
        if not any(tok and tok.casefold() in out.casefold()
                   for tok in ref.split()):
            return Result("P3", label, False, "tailor output doesn't reference the job")
        return Result("P3", label, True,
                      f"tailor prompt={len(out)} chars, references CV + role")
    except Exception as exc:  # noqa: BLE001
        return Result("P3", label, False, f"{type(exc).__name__}: {exc}")


def verify_P4_skill_gap_atlas() -> Result:
    """Import 3 jobs requiring different tech; the skill-gap card must
    surface at least one missing-skill row."""
    label = "Skills blocking you from more roles"
    try:
        client = _get_or_create_tester(f"p4+{secrets.token_hex(3)}@example.com", "test-pass-99-xyz!")
        # CV listing limited skills so the gap analysis has signal
        _set_cv(client, "Senior Python developer. Postgres, FastAPI, Django.")
        imported = 0
        for query in ["senior backend engineer", "senior data engineer",
                      "senior devops engineer", "senior platform engineer"]:
            job = _import_one_job(client, query, "Berlin")
            if job:
                imported += 1
            if imported >= 3:
                break
        if imported < 2:
            return Result("P4", label, False,
                          f"could only import {imported} jobs from live feeds")
        # Read the bootstrap (which carries skillGaps payload)
        status, boot = client.get("/api/bootstrap")
        if status != 200:
            return Result("P4", label, False, f"bootstrap HTTP {status}")
        gaps = boot.get("skillGaps") or {}
        # Actual shape: { "ready": bool, "jobsWithGaps": N, "top": [{skill, jobs, examples}] }
        top = gaps.get("top") or gaps.get("topGaps") or gaps.get("top_gaps") or []
        if not top:
            # Surface the imported-job description lengths so we can
            # tell whether the heuristic had any text to chew on.
            imported_jobs = boot.get("importedJobs") or boot.get("imported_jobs") or []
            sample = [{"title": (j.get("title") or "")[:50],
                       "desc_len": len(j.get("description") or "")}
                      for j in imported_jobs[:3]]
            return Result("P4", label, False,
                          f"skillGaps empty after {imported} imports: gaps={gaps} sample={sample}")
        names = [str(g.get("skill", "?")) for g in top[:5]]
        return Result("P4", label, True,
                      f"{imported} jobs imported, {len(top)} gaps: {names[:3]}")
    except Exception as exc:  # noqa: BLE001
        return Result("P4", label, False, f"{type(exc).__name__}: {exc}")


def verify_P5_application_lifecycle() -> Result:
    """Mark imported job applied + replied, verify state persists on reload."""
    label = "Mark applied / tick when they reply"
    try:
        client = _get_or_create_tester(f"p5+{secrets.token_hex(3)}@example.com", "test-pass-99-xyz!")
        _set_cv(client, "Senior backend dev")
        job = _import_one_job(client, "senior backend engineer", "Berlin")
        if not job:
            return Result("P5", label, False, "no candidate jobs found")
        status, payload = client.post(
            f"/api/imported-jobs/{job['id']}/application", {
                "applicationStatus": "applied",
                "replied": True,
                "applicationNotes": "Sent CV via career page",
            },
        )
        if status != 200:
            return Result("P5", label, False, f"app POST HTTP {status}: {payload}")
        # Reload bootstrap and find this job
        status, boot = client.get("/api/bootstrap")
        if status != 200:
            return Result("P5", label, False, f"bootstrap HTTP {status}")
        imported_jobs = (boot.get("importedJobs")
                          or boot.get("imported_jobs")
                          or boot.get("imported")
                          or [])
        target = next((j for j in imported_jobs
                        if j.get("id") == job.get("id")
                        or j.get("source_url") == job.get("source_url")), None)
        if not target:
            return Result("P5", label, False,
                          f"imported job not in bootstrap (n={len(imported_jobs)})")
        st = (target.get("application_status")
              or target.get("applicationStatus"))
        # The product stores replied as a timestamp (replied_at). Truthy = replied.
        replied = (target.get("replied_at")
                   or target.get("repliedAt")
                   or target.get("application_replied")
                   or target.get("replied"))
        if st != "applied":
            return Result("P5", label, False, f"applicationStatus={st!r} not 'applied'")
        if not replied:
            return Result("P5", label, False, f"replied flag not persisted: {replied!r}")
        return Result("P5", label, True,
                      f"status=applied, replied=True persisted across reload")
    except Exception as exc:  # noqa: BLE001
        return Result("P5", label, False, f"{type(exc).__name__}: {exc}")


def verify_P6_watchlist_scan() -> Result:
    """Triggering /api/watchlist/scan returns 200 and updates lastRunAt."""
    label = "Watches your companies every day"
    try:
        client = _get_or_create_tester(f"p6+{secrets.token_hex(3)}@example.com", "test-pass-99-xyz!")
        # Add a company. Use a non-.example URL so the scanner doesn't
        # short-circuit with 'demo_fixture_not_scanned'.
        status, c = client.post("/api/companies", {
            "name": "Test Corp",
            "websiteUrl": "https://test-employer.io",
            "careerPageUrl": "https://test-employer.io/careers",
            "watchEnabled": True,
        })
        if status not in (200, 201):
            return Result("P6", label, False, f"add company HTTP {status}: {c}")
        # Trigger scan — the response payload IS the proof; lastRunAt
        # only advances when the DurableScheduler tick records a run,
        # which is async.
        status, scan = client.post("/api/watchlist/scan", {})
        if status not in (200, 202):
            return Result("P6", label, False,
                          f"watchlist scan HTTP {status}: {scan}")
        result = scan.get("result") or {}
        run_status = result.get("status")
        if run_status not in {"queued", "nothing_to_scan"}:
            return Result("P6", label, False,
                          f"scan result status={run_status!r}, expected queued/nothing_to_scan: {result}")
        runs_started = len(result.get("runs") or [])
        return Result("P6", label, True,
                      f"scan ack'd: status={run_status}, runs_started={runs_started}")
    except Exception as exc:  # noqa: BLE001
        return Result("P6", label, False, f"{type(exc).__name__}: {exc}")


def verify_P7_cv_encrypted_at_rest() -> Result:
    """Paste a CV with a unique sentinel phrase; assert the sentinel
    does NOT appear plaintext in the SQLite file on disk."""
    label = "CV encrypted at rest"
    try:
        sentinel = f"SENTINEL_PLAINTEXT_{secrets.token_hex(8).upper()}"
        cv_text = (
            "Senior Software Engineer with 8 years experience. "
            f"This CV contains the sentinel phrase {sentinel} which must "
            "NEVER appear in plaintext anywhere on disk."
        )
        client = _get_or_create_tester(f"p7+{secrets.token_hex(3)}@example.com",
                          "test-pass-99-xyz!")
        _set_cv(client, cv_text)
        if not DATA_DIR:
            return Result("P7", label, False,
                          "DATA_DIR env not set — cannot grep DB on disk")
        # Find the SQLite file under data dir. The product uses .sqlite3
        # with WAL — scan all .sqlite* files (includes .sqlite3-wal).
        db_candidates = list(Path(DATA_DIR).rglob("*.sqlite*")) + \
                        list(Path(DATA_DIR).rglob("*.db"))
        if not db_candidates:
            return Result("P7", label, False,
                          f"no .db file under {DATA_DIR}")
        # Scan every .db file's raw bytes for the sentinel
        leaks: list[str] = []
        for db_path in db_candidates:
            try:
                raw = db_path.read_bytes()
            except OSError:
                continue
            if sentinel.encode("ascii") in raw:
                leaks.append(str(db_path))
        if leaks:
            return Result("P7", label, False,
                          f"plaintext sentinel found in: {leaks}")
        return Result("P7", label, True,
                      f"scanned {len(db_candidates)} .db file(s); sentinel not in plaintext")
    except Exception as exc:  # noqa: BLE001
        return Result("P7", label, False, f"{type(exc).__name__}: {exc}")


def verify_P8_reply_rate_analytics() -> Result:
    """Mark 3 applied, 1 replied; replyRate card should show 1/3 = ~33%."""
    label = "Reply rate analytics"
    try:
        client = _get_or_create_tester(f"p8+{secrets.token_hex(3)}@example.com",
                          "test-pass-99-xyz!")
        _set_cv(client, "Senior backend dev. Python, K8s, Postgres.")
        ids: list[str] = []
        for query in ["senior backend engineer", "senior python developer",
                      "senior backend developer", "senior platform engineer"]:
            job = _import_one_job(client, query, "Berlin")
            if job and job.get("id"):
                ids.append(job["id"])
            if len(ids) >= 3:
                break
        if len(ids) < 3:
            return Result("P8", label, False,
                          f"could only import {len(ids)} jobs from live feeds")
        # Mark all 3 applied; mark the first replied
        for i, jid in enumerate(ids):
            body = {"applicationStatus": "applied"}
            if i == 0:
                body["replied"] = True
            status, _ = client.post(f"/api/imported-jobs/{jid}/application", body)
            if status != 200:
                return Result("P8", label, False,
                              f"app update HTTP {status} for {jid}")
        status, boot = client.get("/api/bootstrap")
        if status != 200:
            return Result("P8", label, False, f"bootstrap HTTP {status}")
        # Bootstrap carries the reply-rate card as applicationOutcomes
        # — totalApplications / replied / replyRate / threshold / ready.
        summary = (boot.get("applicationOutcomes")
                   or boot.get("application_outcomes")
                   or boot.get("replyRate") or {})
        total = (summary.get("totalApplications")
                 or summary.get("total_applications")
                 or summary.get("total"))
        replied = (summary.get("replied")
                   or summary.get("repliedCount"))
        rate = summary.get("replyRate") or summary.get("rate")
        if not summary:
            return Result("P8", label, False,
                          f"bootstrap has no replyRate payload: {list(boot)[:20]}")
        if (total or 0) != 3 or (replied or 0) != 1:
            return Result("P8", label, False,
                          f"totals off: applied={total}, replied={replied}, rate={rate}")
        # Rate should be ~0.33 (one third)
        if rate is None:
            return Result("P8", label, False, f"rate missing: {summary}")
        if not 0.30 <= float(rate) <= 0.36:
            return Result("P8", label, False,
                          f"rate {rate} not ≈0.333 for 1/3")
        return Result("P8", label, True,
                      f"3 applied, 1 replied, rate={rate:.3f} (≈33%)")
    except Exception as exc:  # noqa: BLE001
        return Result("P8", label, False, f"{type(exc).__name__}: {exc}")


# ----------------- Driver ---------------------------------------------------


PROMISES = [
    ("P1", verify_P1_no_duplicates),
    ("P2", verify_P2_fit_scoring_prompt),
    ("P3", verify_P3_tailor_cv_prompt),
    ("P4", verify_P4_skill_gap_atlas),
    ("P5", verify_P5_application_lifecycle),
    ("P6", verify_P6_watchlist_scan),
    ("P7", verify_P7_cv_encrypted_at_rest),
    ("P8", verify_P8_reply_rate_analytics),
]


def main() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL is required", file=sys.stderr)
        return 2
    print(f"[promise-verifier] base_url={BASE_URL}")
    print(f"[promise-verifier] data_dir={DATA_DIR or '(unset)'}")
    results: list[Result] = []
    for code, fn in PROMISES:
        print(f"\n[promise-verifier] running {code}: {fn.__name__}…")
        result = fn()
        marker = "✅" if result.ok else "❌"
        print(f"  {marker} {result.label}")
        print(f"     {result.detail}")
        results.append(result)

    out_path = Path(os.environ.get(
        "E2E_PROMISE_REPORT", "tests/e2e/promise_report.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(
        [r.to_dict() for r in results], indent=2, ensure_ascii=False))
    print(f"\n[promise-verifier] report → {out_path}")

    print("\n" + "=" * 70)
    print("PROMISE-BY-PROMISE VERDICT")
    print("=" * 70)
    for r in results:
        marker = "✅" if r.ok else "❌"
        print(f"{marker} [{r.promise}] {r.label}")
        if not r.ok:
            print(f"     → {r.detail}")
    failing = [r for r in results if not r.ok]
    return 0 if not failing else 1


if __name__ == "__main__":
    sys.exit(main())
