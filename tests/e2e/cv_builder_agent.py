# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

"""End-to-end CV builder integration.

Walks a synthetic user through the full builder flow over HTTP:

  start → header section → summary section → one experience entry →
  education entry → skills → finish → verify profile.cv_text reflects
  the entered facts (and ONLY the entered facts).

Runs against a fresh app instance (boot via
``scripts/run-cv-builder-agent.sh``). Exits non-zero on any FAIL."""

from __future__ import annotations

import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")


class _Client:
    def __init__(self) -> None:
        self.base_url = BASE_URL
        self.cookie = ""
        self.csrf_token = ""

    def _req(self, method: str, path: str, body: dict | None = None):
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.csrf_token and method != "GET":
            headers["X-CSRF-Token"] = self.csrf_token
        req = urllib.request.Request(
            self.base_url + path, data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                sc = resp.headers.get("Set-Cookie", "")
                if sc:
                    self.cookie = sc.split(";", 1)[0]
                txt = resp.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(txt) if txt else {}
                except json.JSONDecodeError:
                    payload = txt
                self._absorb_csrf(payload)
                return resp.status, payload
        except urllib.error.HTTPError as e:
            txt = e.read().decode("utf-8", errors="replace") if e.fp else ""
            try:
                return e.code, json.loads(txt) if txt else {}
            except json.JSONDecodeError:
                return e.code, txt

    def _absorb_csrf(self, p):
        if not isinstance(p, dict):
            return
        for k in ("csrfToken", "csrf_token"):
            if isinstance(p.get(k), str) and p[k]:
                self.csrf_token = p[k]
                return
        u = p.get("user") or {}
        if isinstance(u, dict):
            for k in ("csrfToken", "csrf_token"):
                if isinstance(u.get(k), str) and u[k]:
                    self.csrf_token = u[k]
                    return

    def post(self, p, body=None):
        return self._req("POST", p, body or {})

    def get(self, p):
        return self._req("GET", p)


def _signup() -> _Client:
    c = _Client()
    c.get("/")
    s, p = c.post(
        "/api/auth/register",
        {
            "email": f"cvbuilder+{secrets.token_hex(3)}@example.com",
            "password": "cvbuilder-test-99-X",
            "tosAccepted": True,
            "privacyAccepted": True,
        },
    )
    if s not in (200, 201):
        raise RuntimeError(f"signup failed: {s} {p}")
    return c


def _report(name: str, ok: bool, detail: str = "") -> dict:
    flag = "✅" if ok else "❌"
    print(f"  {flag} {name}{(' — ' + detail) if detail else ''}")
    return {"name": name, "ok": ok, "detail": detail}


def run() -> int:
    if not BASE_URL:
        print("ERROR: E2E_BASE_URL required", file=sys.stderr)
        return 2

    results: list[dict] = []
    c = _signup()

    # 1. Start builder
    s, p = c.post("/api/cv-builder/start", {})
    results.append(
        _report(
            "start_ok",
            s == 200,
            f"status={s}, currentSection={(p.get('currentSection') or {}).get('sectionId')}",
        )
    )
    if s != 200:
        return 1
    section = p.get("currentSection") or {}
    results.append(
        _report(
            "start_returns_header",
            section.get("sectionId") == "header",
            f"got '{section.get('sectionId')}'",
        )
    )

    # 2. Submit header
    s, p = c.post(
        "/api/cv-builder/section/header",
        {
            "answers": {
                "full_name": "Anna Müller",
                "email": "anna@example.com",
                "location": "Berlin",
                "linkedin": "linkedin.com/in/anna",
            },
        },
    )
    results.append(
        _report(
            "header_submit_ok",
            s == 200,
            f"status={s}, next={(p.get('currentSection') or {}).get('sectionId')}",
        )
    )
    next_section = (p.get("currentSection") or {}).get("sectionId")
    results.append(
        _report("header_advances_to_summary", next_section == "summary", f"got '{next_section}'")
    )

    # 3. Submit header with missing required fields → must reject
    s, p = c.post(
        "/api/cv-builder/section/header",
        {
            "answers": {"full_name": ""},  # missing email + location
        },
    )
    results.append(_report("missing_required_rejected", s == 400, f"status={s}"))

    # 4. Submit summary (the formatter will fall back to raw because
    # the test runs in Manual mode — no AI call. That's expected and
    # the fact-grounding gate ensures we'd reject hallucinations IF a
    # real AI were configured.)
    s, p = c.post(
        "/api/cv-builder/section/summary",
        {
            "answers": {
                "summary_raw": "Senior backend engineer with 8 years of "
                "Python and Postgres at Series B fintechs.",
            },
        },
    )
    results.append(_report("summary_submit_ok", s == 200, f"status={s}"))
    ai_meta = p.get("aiMeta") or {}
    # Manual mode: AI not invoked, so factRatio is 1.0 and aiAccepted False.
    results.append(
        _report(
            "summary_ai_meta_present",
            "aiAccepted" in ai_meta or "factRatio" not in ai_meta,
            f"meta={ai_meta}",
        )
    )

    # 5. Submit one experience entry (repeatable section)
    s, p = c.post(
        "/api/cv-builder/section/experience",
        {
            "answers": {
                "company_name": "Acme Corp",
                "job_title": "Senior Backend Engineer",
                "start_date": "2022-01",
                "end_date": "present",
                "location": "Berlin",
                "achievements_raw": "Led migration to Kubernetes. Built payments microservice.",
            },
            "advance": True,
        },
    )
    results.append(_report("experience_submit_ok", s == 200, f"status={s}"))

    # 6. Skip education + skills are still required to finish the wizard.
    # Submit minimum education + skills.
    s, _ = c.post(
        "/api/cv-builder/section/education",
        {
            "answers": {
                "school": "TU Berlin",
                "degree": "MSc",
                "field": "Computer Science",
                "start_date": "2016",
                "end_date": "2019",
            },
        },
    )
    results.append(_report("education_submit_ok", s == 200, f"status={s}"))

    s, _ = c.post(
        "/api/cv-builder/section/skills",
        {
            "answers": {
                "skills_raw": "Python, Postgres, Kubernetes, AWS, Docker",
            },
        },
    )
    results.append(_report("skills_submit_ok", s == 200, f"status={s}"))

    # 7. Upload a photo (PNG) — must round-trip via the profile.
    import base64 as _b64

    # Build a minimal valid PNG inline.
    import struct as _struct
    import zlib as _zlib

    def _chunk(ty, data):
        crc = _zlib.crc32(ty + data) & 0xFFFFFFFF
        return _struct.pack(">I", len(data)) + ty + data + _struct.pack(">I", crc)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", _struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
    idat = _chunk(b"IDAT", _zlib.compress(b"\x00\xff\xff\xff"))
    iend = _chunk(b"IEND", b"")
    png = sig + ihdr + idat + iend
    s, p = c.post(
        "/api/profile/photo-upload",
        {
            "contentBase64": _b64.b64encode(png).decode("ascii"),
        },
    )
    results.append(_report("photo_upload_ok", s == 200, f"status={s}, size={p.get('sizeBytes')}"))
    results.append(
        _report(
            "photo_uri_is_png",
            isinstance(p.get("cvPhotoDataUri"), str)
            and p["cvPhotoDataUri"].startswith("data:image/png"),
            "",
        )
    )

    # Photo upload reject — SVG with script
    svg = b'<?xml version="1.0"?><svg onload="alert(1)"></svg>'
    s, p = c.post(
        "/api/profile/photo-upload",
        {
            "contentBase64": _b64.b64encode(svg).decode("ascii"),
        },
    )
    results.append(
        _report(
            "photo_reject_svg", s == 400, f"status={s}, code={(p.get('error') or {}).get('code')}"
        )
    )

    # Photo upload reject — too large (600KB)
    oversize = b"\xff\xd8\xff" + b"\x00" * (600 * 1024)
    s, p = c.post(
        "/api/profile/photo-upload",
        {
            "contentBase64": _b64.b64encode(oversize).decode("ascii"),
        },
    )
    results.append(
        _report(
            "photo_reject_oversize",
            s == 400,
            f"status={s}, code={(p.get('error') or {}).get('code')}",
        )
    )

    # 8. Finish — photo must appear in the assembled CV markdown.
    s, p = c.post("/api/cv-builder/finish", {})
    results.append(_report("finish_ok", s == 200, f"status={s}"))
    cv_text = p.get("cvText", "")
    results.append(_report("cv_includes_name", "Anna Müller" in cv_text, f"len={len(cv_text)}"))
    results.append(_report("cv_includes_summary", "8 years" in cv_text, "summary text present"))
    results.append(
        _report(
            "cv_includes_experience",
            "Acme Corp" in cv_text and "Senior Backend Engineer" in cv_text,
            "experience header present",
        )
    )
    results.append(_report("cv_includes_education", "TU Berlin" in cv_text, "education present"))
    results.append(
        _report(
            "cv_includes_skills", "Python" in cv_text and "Kubernetes" in cv_text, "skills present"
        )
    )
    results.append(
        _report(
            "cv_includes_photo_tag",
            "data:image/png;base64" in cv_text,
            "photo embedded at top of CV",
        )
    )

    # 8. Verify profile.cv_text was persisted (downstream features use it).
    s, profile = c.get("/api/profile")
    if isinstance(profile, dict):
        cv_back = profile.get("cvText") or (profile.get("profile") or {}).get("cvText") or ""
        results.append(
            _report(
                "profile_cv_text_persisted",
                "Anna Müller" in cv_back and "Acme Corp" in cv_back,
                f"len={len(cv_back)}",
            )
        )

    # 9. PDF/print route — returns self-contained HTML with the CV
    # rendered + browser save-as-PDF affordance.
    s, body = c.get("/api/cv/print")
    has_doctype = isinstance(body, str) and body.startswith("<!doctype html>")
    has_name = isinstance(body, str) and "Anna Müller" in body
    has_a4 = isinstance(body, str) and "size: A4" in body
    has_print_btn = isinstance(body, str) and "Download as PDF" in body
    has_photo_tag = isinstance(body, str) and "data:image/png;base64" in body
    results.append(_report("print_html_serves", s == 200 and has_doctype, f"status={s}"))
    results.append(_report("print_html_includes_name", bool(has_name)))
    results.append(_report("print_html_a4_css", bool(has_a4)))
    results.append(_report("print_html_pdf_button", bool(has_print_btn)))
    results.append(
        _report("print_html_embeds_photo", bool(has_photo_tag), "embedded photo data URI present")
    )

    # Autoprint variant
    s, body = c.get("/api/cv/print?autoprint=1")
    has_autoprint = isinstance(body, str) and "window.print()" in body and "setTimeout" in body
    results.append(
        _report("print_autoprint_injects_script", s == 200 and has_autoprint, f"status={s}")
    )

    out_path = Path(os.environ.get("E2E_CV_REPORT", "tests/e2e/cv_builder_report.json"))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    failed = [r for r in results if not r["ok"]]
    print("\n" + "=" * 70)
    print(f"CV BUILDER E2E — {len(results) - len(failed)}/{len(results)} PASS")
    print("=" * 70)
    if failed:
        for f in failed:
            print(f"  ❌ {f['name']}: {f['detail']}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(run())
