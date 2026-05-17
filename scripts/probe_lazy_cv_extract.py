"""R28.1 — end-to-end probe for lazy CV extraction on first print.

Verifies:
  1. User uploads cv_text via /api/profile (no extraction yet).
  2. /api/profile reports cvDocumentReady=false.
  3. First hit to /api/cv/print silently runs extraction (stubbed
     LLM returns canned data).
  4. cv_document is now persisted.
  5. /api/profile reports cvDocumentReady=true.
  6. Second print does NOT re-extract (no extra LLM call).
"""

from __future__ import annotations

import json
import os
import secrets
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_lazy_extract_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)
os.environ["DIRECTJOB_MANAGED_AI_KEY"] = "sk-ant-stub"
os.environ["DIRECTJOB_MANAGED_AI_PROVIDER"] = "anthropic"
os.environ["DIRECTJOB_REGISTER_LIMIT"] = "999"
os.environ["DIRECTJOB_ALLOW_REGISTRATION"] = "true"
os.environ["DIRECTJOB_LLM_DAILY_CAP"] = "0"

import app  # noqa: E402
from company_discovery import analysis as A  # noqa: E402


# Count how many times _dispatch_provider runs to confirm the second
# print does NOT re-extract.
DISPATCH_COUNT = {"n": 0}


def _fake_dispatch(prompt, provider, runtime_credential, *,
                    task="", record_call=None):
    """Returns canned CV-extract JSON; counts calls."""
    DISPATCH_COUNT["n"] += 1
    return A.AnalysisExecutionResult(
        status="completed",
        provider_id="anthropic",
        invocation_mode="api",
        prompt=prompt,
        output="""{
            "full_name": "Probe User",
            "headline": "Senior bartender",
            "location": "Berlin",
            "contacts": [{"label": "Email", "value": "probe@example.com"}],
            "summary": "Six years behind the bar at Z-Bar Berlin.",
            "experience": [{
                "title": "Bartender",
                "company": "Z-Bar",
                "location": "Berlin",
                "start": "2019",
                "end": "present",
                "description": "Crafted cocktails, ran the bar.",
                "bullets": ["Doubled cocktail-menu revenue"]
            }],
            "education": [],
            "skills": ["Mixology", "Cash handling"],
            "languages": [{"language": "German", "level": "C1"}],
            "certifications": [],
            "publications": []
        }""",
        input_tokens=400,
        output_tokens=200,
        model_used="claude-haiku-4-5",
    )


def _start_server() -> int:
    import http.server
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)
    return port


def _post(port, path, payload, cookie=None, csrf=None):
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    if csrf:
        headers["X-CSRF-Token"] = csrf
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body, method="POST", headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return (resp.status,
                json.loads(resp.read().decode("utf-8")),
                resp.headers.get("Set-Cookie") or "")


def _get(port, path, cookie, csrf, *, text=False):
    headers = {"Cookie": cookie, "X-CSRF-Token": csrf}
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read().decode("utf-8")
        return resp.status, (raw if text else json.loads(raw))


def main() -> int:
    # Patch the dispatcher BEFORE the server starts so the
    # /api/cv/print path picks up our stub.
    A._dispatch_provider = _fake_dispatch  # type: ignore[assignment]
    # Also propagate consent so the auto-extract gate passes.
    # We mark a bypass via env so _ai_consent_satisfied returns True.
    # (Easier: set ai_consent_at after registration via /api/profile.)

    port = _start_server()
    print(f"[probe] server up on http://127.0.0.1:{port}")
    findings: list[str] = []

    # 1. Register the admin user.
    email = f"lazy-ex+{secrets.token_hex(2)}@example.com"
    status, body, set_cookie = _post(port, "/api/auth/register", {
        "email": email, "password": "lazy-pass-9X-test",
        "tosAccepted": True, "privacyAccepted": True,
    })
    if status != 201:
        print(f"register failed: {status} {body}")
        return 1
    cookie = set_cookie.split(";")[0]
    csrf = (body.get("user") or {}).get("csrfToken") or ""

    # 2. Paste cv_text via /api/profile (no extraction triggered).
    _post(port, "/api/profile",
          {"cvText": "Six years at Z-Bar Berlin. German C1."},
          cookie=cookie, csrf=csrf)

    # The user's provider config is "manual" by default — the
    # lazy-extract gate skips manual. We need to flip provider to
    # "managed". Touching /api/ai-provider would normally require
    # consent etc. — easier: bypass by setting ai_provider directly
    # on STATE for this probe user.
    eff_uid = app.STATE.effective_user_id(
        (body.get("user") or {}).get("id"))
    from company_discovery.ai_providers import AIProviderConfig
    app.STATE.ai_providers[eff_uid] = AIProviderConfig(
        provider_id="managed", invocation_mode="api")
    # Mark consent so _ai_consent_satisfied passes — managed bypasses
    # consent in R23.3, so no extra config needed.

    # 3. /api/profile should report cvDocumentReady=false now.
    s, prof = _get(port, "/api/profile", cookie, csrf)
    if (prof.get("profile") or {}).get("cvDocumentReady") is not False:
        findings.append("cvDocumentReady should be False before first print")
    print(f"[probe] before print: cvDocumentReady = "
          f"{(prof.get('profile') or {}).get('cvDocumentReady')}")

    # 4. First /api/cv/print — should trigger lazy extraction.
    dispatch_before = DISPATCH_COUNT["n"]
    s, html = _get(port, "/api/cv/print", cookie, csrf, text=True)
    if s != 200:
        findings.append(f"first /api/cv/print returned {s}")
    if DISPATCH_COUNT["n"] != dispatch_before + 1:
        findings.append(
            f"expected 1 dispatch on first print, got "
            f"{DISPATCH_COUNT['n'] - dispatch_before}")
    if "Probe User" not in html:
        findings.append("extracted name not rendered after first print")
    else:
        print(f"[probe] first print triggered extraction "
              f"+ rendered 'Probe User'")

    # 5. /api/profile now reports cvDocumentReady=true.
    s, prof = _get(port, "/api/profile", cookie, csrf)
    if (prof.get("profile") or {}).get("cvDocumentReady") is not True:
        findings.append("cvDocumentReady should be True after first print")
    print(f"[probe] after print: cvDocumentReady = "
          f"{(prof.get('profile') or {}).get('cvDocumentReady')}")

    # 6. Second print — NO additional extraction call.
    dispatch_after_first = DISPATCH_COUNT["n"]
    _get(port, "/api/cv/print", cookie, csrf, text=True)
    if DISPATCH_COUNT["n"] != dispatch_after_first:
        findings.append(
            f"second print should NOT re-extract; dispatch count went "
            f"{dispatch_after_first} → {DISPATCH_COUNT['n']}")
    else:
        print(f"[probe] second print served from cached cv_document "
              f"(no extra LLM call)")

    print()
    print("=" * 60)
    if findings:
        print(f"LAZY CV EXTRACT PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("LAZY CV EXTRACT PROBE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
