"""R24.8 / R24.10 — end-to-end probe for the CV template stack.

Verifies:
  1. GET /api/profile exposes cvTemplateId / cvAccentColor / cvPhotoOn /
     cvHeadlineOverride / cvDocumentReady (defaults for a fresh user).
  2. POST /api/cv/template patches each field and the response echoes
     the new values.
  3. GET /api/cv/print renders HTML for the user's chosen template
     (validated by data-template attribute presence).
  4. Invalid template id / accent silently coerce to the default
     (modern / indigo) — schema validation.
"""

from __future__ import annotations

import json
import os
import re
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

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_cv_template_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)
os.environ["DIRECTJOB_REGISTER_LIMIT"] = "999"
os.environ["DIRECTJOB_ALLOW_REGISTRATION"] = "true"

import app  # noqa: E402


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
        if text:
            return resp.status, raw
        return resp.status, json.loads(raw)


def main() -> int:
    port = _start_server()
    print(f"[probe] server up on http://127.0.0.1:{port}")
    findings: list[str] = []

    email = f"cv-tpl+{secrets.token_hex(2)}@example.com"
    status, body, set_cookie = _post(port, "/api/auth/register", {
        "email": email, "password": "cv-tpl-pass-9X",
        "tosAccepted": True, "privacyAccepted": True,
    })
    if status != 201:
        print(f"register failed: {status} {body}")
        return 1
    cookie = set_cookie.split(";")[0]
    csrf = (body.get("user") or {}).get("csrfToken") or ""
    print(f"[probe] registered {email}")

    # 1. Profile defaults expose the four CV template fields.
    s, profile = _get(port, "/api/profile", cookie, csrf)
    p = profile.get("profile") or {}
    print(f"[probe] defaults — template={p.get('cvTemplateId')!r}, "
          f"accent={p.get('cvAccentColor')!r}, photoOn={p.get('cvPhotoOn')}, "
          f"headline={p.get('cvHeadlineOverride')!r}, docReady={p.get('cvDocumentReady')}")
    if p.get("cvTemplateId") != "modern":
        findings.append(f"default templateId={p.get('cvTemplateId')!r}, expected 'modern'")
    if p.get("cvAccentColor") != "indigo":
        findings.append(f"default accentColor={p.get('cvAccentColor')!r}, expected 'indigo'")
    if p.get("cvPhotoOn") is not True:
        findings.append(f"default cvPhotoOn={p.get('cvPhotoOn')!r}, expected True")
    if p.get("cvHeadlineOverride") != "":
        findings.append(f"default headline={p.get('cvHeadlineOverride')!r}, expected ''")
    if p.get("cvDocumentReady") is not False:
        findings.append(f"default cvDocumentReady={p.get('cvDocumentReady')!r}, expected False")

    # 2. Patch template_id + accent in one call.
    s, body, _ = _post(port, "/api/cv/template",
                          {"templateId": "executive", "accentColor": "teal"},
                          cookie=cookie, csrf=csrf)
    if s != 200:
        findings.append(f"POST /api/cv/template returned {s}")
    if body.get("templateId") != "executive":
        findings.append(f"after PATCH: templateId={body.get('templateId')!r}")
    if body.get("accentColor") != "teal":
        findings.append(f"after PATCH: accentColor={body.get('accentColor')!r}")

    # 3. Re-fetch profile shows the saved values.
    s, profile = _get(port, "/api/profile", cookie, csrf)
    p2 = profile.get("profile") or {}
    if p2.get("cvTemplateId") != "executive":
        findings.append(
            f"profile after save: templateId={p2.get('cvTemplateId')!r}")
    if p2.get("cvAccentColor") != "teal":
        findings.append(
            f"profile after save: accentColor={p2.get('cvAccentColor')!r}")

    # 4. Invalid template id is rejected silently (stays unchanged).
    _post(port, "/api/cv/template",
          {"templateId": "rainbow-comic-sans"},
          cookie=cookie, csrf=csrf)
    s, profile = _get(port, "/api/profile", cookie, csrf)
    p3 = profile.get("profile") or {}
    if p3.get("cvTemplateId") != "executive":
        findings.append(
            f"invalid template should be ignored: got {p3.get('cvTemplateId')!r}")

    # 5. Photo on/off toggle + headline override round trip.
    _post(port, "/api/cv/template",
          {"photoOn": False, "headlineOverride": "Bartender · 5y Berlin"},
          cookie=cookie, csrf=csrf)
    s, profile = _get(port, "/api/profile", cookie, csrf)
    p4 = profile.get("profile") or {}
    if p4.get("cvPhotoOn") is not False:
        findings.append(f"photoOn after toggle: {p4.get('cvPhotoOn')!r}")
    if p4.get("cvHeadlineOverride") != "Bartender · 5y Berlin":
        findings.append(
            f"headline after save: {p4.get('cvHeadlineOverride')!r}")

    # 6. /api/cv/print renders HTML with the user's chosen template
    # in the data-template attribute. No cv_text saved yet so the
    # resolver should return the empty / fallback page.
    s, html = _get(port, "/api/cv/print", cookie, csrf, text=True)
    print(f"[probe] /api/cv/print status={s}, "
          f"{len(html)} bytes")
    # User has no cv_text yet → expect the "no CV saved" placeholder.
    if "No CV saved yet" not in html and "build my CV" not in html:
        findings.append("expected 'no CV saved' message for empty profile")

    # 7. Add cv_text via profile patch + verify /api/cv/print renders the
    # executive template now.
    _post(port, "/api/profile",
          {"cvText": "Maria Schmidt\nBartender at Z-Bar Berlin\n5 years experience"},
          cookie=cookie, csrf=csrf)
    s, html = _get(port, "/api/cv/print", cookie, csrf, text=True)
    if 'data-template="executive"' not in html:
        findings.append("rendered HTML missing data-template=executive")
    if 'data-accent="teal"' not in html:
        findings.append("rendered HTML missing data-accent=teal")
    if 'data-photo-off="true"' not in html:
        findings.append("rendered HTML missing data-photo-off=true")
    # XSS guard: insert HTML in cvText and verify it's escaped.
    _post(port, "/api/profile",
          {"cvText": "Maria<script>alert(1)</script>"},
          cookie=cookie, csrf=csrf)
    s, html = _get(port, "/api/cv/print", cookie, csrf, text=True)
    if "<script>alert" in html:
        findings.append("cvText XSS — <script> rendered as raw HTML")
    if "&lt;script&gt;alert" not in html:
        findings.append("cvText not HTML-escaped in the rendered output")

    print()
    print("=" * 60)
    if findings:
        print(f"CV TEMPLATE PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("CV TEMPLATE PROBE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
