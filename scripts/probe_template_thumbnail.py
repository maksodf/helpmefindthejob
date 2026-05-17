"""R29 — runtime probe for /api/cv/template-thumbnail.

Verifies (no LLM, no auth required — this is a public preview):
  1. Endpoint returns 200 with text/html for each (template × accent).
  2. The rendered HTML carries the requested data-template + data-accent
     attributes so the picker is showing the user the *actual* template
     they'd land on, not a generic skeleton.
  3. Thumb mode strips the body margin so the sheet fills the iframe
     edge-to-edge (the marker is the inline style with margin:0).
  4. Unknown template/accent values fall back to defaults instead of
     500-ing.
  5. The believable DACH sample data is present (Maria Schmidt) so
     each preview looks like a real CV rather than placeholder text.
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROBE_DIR = Path(tempfile.mkdtemp(prefix="djs_thumb_probe_"))
os.environ["COMPANY_DISCOVERY_DATA_DIR"] = str(PROBE_DIR)

import app  # noqa: E402

TEMPLATES = ["modern", "classic", "tech", "executive", "creative", "academic"]
ACCENTS = ["indigo", "teal", "slate"]


def _start_server() -> int:
    import http.server
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.4)
    return port


def _get(port, path):
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return (resp.status,
                resp.headers.get("Content-Type", ""),
                resp.read().decode("utf-8"))


def main() -> int:
    port = _start_server()
    print(f"[probe] server up on http://127.0.0.1:{port}")
    findings: list[str] = []

    # 1+2 — every (template × accent) renders with the right markers.
    for tpl in TEMPLATES:
        for acc in ACCENTS:
            path = f"/api/cv/template-thumbnail?id={tpl}&accent={acc}&photo=0"
            status, ctype, html = _get(port, path)
            tag = f"{tpl}+{acc}"
            if status != 200:
                findings.append(f"{tag}: status {status} (want 200)")
                continue
            if "text/html" not in ctype:
                findings.append(f"{tag}: content-type {ctype!r}")
            if f'data-template="{tpl}"' not in html:
                findings.append(f"{tag}: data-template attr missing")
            if f'data-accent="{acc}"' not in html:
                findings.append(f"{tag}: data-accent attr missing")
            if "Maria Schmidt" not in html:
                findings.append(f"{tag}: sample name missing")
    if not findings:
        print(f"[probe] all 18 (template × accent) combos render correctly")

    # 3 — thumb mode strips the body margin so the sheet fills the iframe.
    status, _, html = _get(port,
        "/api/cv/template-thumbnail?id=modern&accent=indigo&photo=0")
    if "margin:0" not in html:
        findings.append("thumb-mode body margin override not injected")
    else:
        print("[probe] thumb mode strips body margin (edge-to-edge sheet)")

    # 4 — bogus template + accent fall back gracefully.
    status, _, html = _get(port,
        "/api/cv/template-thumbnail?id=robot&accent=neon&photo=0")
    if status != 200:
        findings.append(f"bogus inputs returned {status} (want 200 fallback)")
    if 'data-template="modern"' not in html:
        findings.append("bogus template did not fall back to 'modern'")
    if 'data-accent="indigo"' not in html:
        findings.append("bogus accent did not fall back to 'indigo'")
    if status == 200 and 'data-template="modern"' in html:
        print("[probe] bogus inputs fall back to modern/indigo (no 500)")

    # 5 — photo=0 sets data-photo-off="true" so portrait stays hidden.
    status, _, html = _get(port,
        "/api/cv/template-thumbnail?id=creative&accent=teal&photo=0")
    if 'data-photo-off="true"' not in html:
        findings.append("photo=0 did not set data-photo-off='true'")
    else:
        print("[probe] photo=0 disables the portrait")

    print()
    print("=" * 60)
    if findings:
        print(f"R29 TEMPLATE-THUMBNAIL PROBE — {len(findings)} FINDING(S)")
        for m in findings:
            print(f"  FAIL: {m}")
        return 1
    print("R29 TEMPLATE-THUMBNAIL PROBE — ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
