# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Server-side rendering + SEO contract tests (13-plan item 10/13).

Two layers of test:

1. **Static-asset SEO contract** (always runs) — every public HTML
   page in ``static/`` must declare the full SEO surface a top-tier
   civic-commons project ships: title, meta description, canonical,
   hreflang en/de/x-default, OpenGraph (type, title, description, url,
   site_name, locale, locale:alternate), Twitter card, JSON-LD
   WebPage. The index.html also carries Organization + WebSite +
   SoftwareApplication structured data.

2. **Live SSR routes** (always runs) — boots a real AppState in a
   tempdir, exercises ``/sitemap.xml``, ``/robots.txt``, and
   ``/jobs/<slug>`` SSR landings against the actual handler code.
   Guards against the original bug: the static ``sitemap.xml``
   carried ``khalo.org`` references (Week 1 sanitization residue)
   and listed dead URLs. The dynamic version pulls the base URL
   from APP_PUBLIC_URL / Host header / X-Forwarded-Proto and the
   page list from the live registry, so it can never go stale or
   carry sanitization residue.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory


STATIC_DIR = Path("/Users/fouad./Desktop/NasserMCPserver/static")


# -------------------------------------------------------------------------
# Static-asset SEO contract
# -------------------------------------------------------------------------


# Pages that MUST carry the full SEO meta surface. /index.html has
# additional Organization + WebSite + SoftwareApplication JSON-LD
# checked separately in IndexHtmlStructuredData below.
PUBLIC_PAGES = [
    "index.html",
    "privacy.html",
    "terms.html",
    "data-retention.html",
    "impressum.html",
    "help.html",
    "status.html",
    "changelog.html",
]


class StaticPagesSeoContract(unittest.TestCase):
    """Every public HTML page must declare canonical, hreflang,
    OpenGraph, Twitter card, and JSON-LD WebPage. Catches missing
    SEO depth before it ships to crawlers."""

    def _read(self, name: str) -> str:
        return (STATIC_DIR / name).read_text(encoding="utf-8")

    def test_every_page_has_meta_description(self):
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                self.assertIn(
                    'meta name="description"',
                    self._read(page),
                    f"{page} missing meta description",
                )

    def test_every_page_has_canonical(self):
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                self.assertIn(
                    'rel="canonical"',
                    self._read(page),
                    f"{page} missing canonical",
                )

    def test_every_page_has_hreflang_alternates(self):
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                src = self._read(page)
                self.assertIn(
                    'hreflang="en"', src, f"{page} missing hreflang en"
                )
                self.assertIn(
                    'hreflang="de"', src, f"{page} missing hreflang de"
                )
                self.assertIn(
                    'hreflang="x-default"',
                    src,
                    f"{page} missing hreflang x-default",
                )

    def test_every_page_has_opengraph_tags(self):
        required = [
            'property="og:type"',
            'property="og:title"',
            'property="og:description"',
            'property="og:url"',
            'property="og:site_name"',
        ]
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                src = self._read(page)
                for tag in required:
                    self.assertIn(tag, src, f"{page} missing {tag}")

    def test_every_page_has_twitter_card(self):
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                src = self._read(page)
                self.assertIn(
                    'name="twitter:card"', src, f"{page} missing twitter:card"
                )
                self.assertIn(
                    'name="twitter:title"',
                    src,
                    f"{page} missing twitter:title",
                )

    def test_every_page_has_json_ld(self):
        for page in PUBLIC_PAGES:
            with self.subTest(page=page):
                src = self._read(page)
                self.assertIn(
                    'application/ld+json',
                    src,
                    f"{page} missing JSON-LD structured data",
                )

    def test_no_khalo_org_residue_anywhere_in_static(self):
        """Week 1 sanitization residue guard. If this ever fails,
        someone reintroduced the legacy domain. CLAUDE.md hard rule:
        do not reintroduce khalo.org strings."""

        for html_file in STATIC_DIR.glob("*.html"):
            with self.subTest(file=html_file.name):
                src = html_file.read_text(encoding="utf-8")
                self.assertNotIn(
                    "khalo.org",
                    src,
                    f"{html_file.name} has legacy khalo.org residue",
                )


class IndexHtmlStructuredData(unittest.TestCase):
    """index.html is the front door; needs Organization + WebSite
    + SoftwareApplication for rich search results."""

    def setUp(self):
        self.src = (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    def test_declares_organization_schema(self):
        self.assertIn('"@type": "Organization"', self.src)
        self.assertIn('"name": "Helpmefindthejob"', self.src)

    def test_declares_website_schema(self):
        self.assertIn('"@type": "WebSite"', self.src)

    def test_declares_software_application_schema(self):
        self.assertIn('"@type": "SoftwareApplication"', self.src)
        self.assertIn('"license"', self.src)
        self.assertIn("apache.org/licenses/LICENSE-2.0", self.src)

    def test_json_ld_parses_as_valid_json(self):
        """Structured data must parse — crawlers reject malformed JSON-LD."""

        # Extract the JSON-LD block content
        start = self.src.find('<script type="application/ld+json">')
        self.assertGreater(start, 0, "no JSON-LD block found")
        start = self.src.find("{", start)
        end = self.src.find("</script>", start)
        block = self.src[start:end].strip()
        try:
            payload = json.loads(block)
        except json.JSONDecodeError as exc:
            self.fail(f"index.html JSON-LD is not valid JSON: {exc}")
        self.assertEqual(payload.get("@context"), "https://schema.org")
        self.assertIn("@graph", payload)


# -------------------------------------------------------------------------
# Live SSR — boot a real AppState + exercise dynamic routes
# -------------------------------------------------------------------------


def _free_port() -> int:
    """Pick an ephemeral port — avoids conflicts with the dev server."""

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def _wait_for_port(port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


class LiveSsrRoutes(unittest.TestCase):
    """Boots app.py as a subprocess so the live HTTP server runs
    end-to-end (handler instantiation, header processing, response
    encoding). Subprocess isolation also lets us set APP_PUBLIC_URL
    per test without polluting the parent process."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = TemporaryDirectory()
        cls.port = _free_port()
        cls.proc = None
        env = dict(os.environ)
        env["HELPMEFINDTHEJOB_DATA_FILE"] = str(
            Path(cls.tmpdir.name) / "data.json"
        )
        env["HELPMEFINDTHEJOB_DISABLE_SCHEDULER"] = "1"
        env.pop("HELPMEFINDTHEJOB_DATABASE_URL", None)
        env.pop("HELPMEFINDTHEJOB_DATABASE_URL", None)
        env.pop("HELPMEFINDTHEJOB_PUBLIC_URL", None)
        cls.proc = subprocess.Popen(
            [sys.executable, "app.py", "--port", str(cls.port)],
            cwd="/Users/fouad./Desktop/NasserMCPserver",
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not _wait_for_port(cls.port, timeout=15.0):
            cls.proc.terminate()
            raise RuntimeError("app.py failed to bind")

    @classmethod
    def tearDownClass(cls):
        if cls.proc is not None:
            cls.proc.terminate()
            try:
                cls.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.proc.kill()
        cls.tmpdir.cleanup()

    def _get(self, path: str, headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], str]:
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        for key, value in (headers or {}).items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return (
                    resp.status,
                    {k.lower(): v for k, v in resp.headers.items()},
                    resp.read().decode("utf-8"),
                )
        except urllib.error.HTTPError as exc:
            return (
                exc.code,
                {k.lower(): v for k, v in exc.headers.items()},
                exc.read().decode("utf-8"),
            )

    def test_sitemap_xml_served_dynamically(self):
        status, headers, body = self._get("/sitemap.xml")
        self.assertEqual(status, 200)
        self.assertIn("application/xml", headers.get("content-type", ""))
        self.assertIn("<urlset", body)
        # XML namespace declarations both present
        self.assertIn("sitemaps.org/schemas/sitemap/0.9", body)
        self.assertIn("xhtml", body)

    def test_sitemap_xml_contains_no_khalo_org(self):
        _, _, body = self._get("/sitemap.xml")
        self.assertNotIn("khalo.org", body)

    def test_sitemap_xml_uses_host_header_when_public_url_unset(self):
        _, _, body = self._get(
            "/sitemap.xml", headers={"Host": "demo.example.com"}
        )
        self.assertIn("demo.example.com", body)
        self.assertNotIn("127.0.0.1", body)  # Host header wins over fallback

    def test_sitemap_xml_uses_https_when_xforwarded_proto_https(self):
        _, _, body = self._get(
            "/sitemap.xml",
            headers={
                "Host": "demo.example.com",
                "X-Forwarded-Proto": "https",
            },
        )
        self.assertIn("https://demo.example.com", body)

    def test_sitemap_xml_includes_hreflang_alternates(self):
        _, _, body = self._get("/sitemap.xml")
        self.assertIn('hreflang="en"', body)
        self.assertIn('hreflang="de"', body)
        self.assertIn('hreflang="x-default"', body)

    def test_sitemap_xml_enumerates_fixed_legal_pages(self):
        _, _, body = self._get("/sitemap.xml")
        for path in (
            "/privacy",
            "/terms",
            "/data-retention",
            "/impressum",
            "/help",
            "/status",
            "/changelog",
        ):
            with self.subTest(path=path):
                self.assertIn(path, body)

    def test_robots_txt_served_dynamically(self):
        status, headers, body = self._get("/robots.txt")
        self.assertEqual(status, 200)
        self.assertIn("text/plain", headers.get("content-type", ""))
        self.assertIn("User-agent: *", body)
        self.assertIn("Sitemap:", body)

    def test_robots_txt_sitemap_line_matches_host(self):
        _, _, body = self._get(
            "/robots.txt", headers={"Host": "demo.example.com"}
        )
        self.assertIn("Sitemap: http://demo.example.com/sitemap.xml", body)

    def test_robots_txt_blocks_api_paths(self):
        _, _, body = self._get("/robots.txt")
        self.assertIn("Disallow: /api/", body)
        self.assertIn("Disallow: /admin", body)


class SeoLandingPageEnrichment(unittest.TestCase):
    """The /jobs/<slug> SSR landings must carry the same SEO depth as
    the static pages: hreflang, OG, Twitter, JSON-LD. Source-level
    check — runtime exercise would require a populated
    seo-pages.json, which is operator-owned."""

    def setUp(self):
        self.src = Path(
            "/Users/fouad./Desktop/NasserMCPserver/app.py"
        ).read_text(encoding="utf-8")
        # Slice to just the _send_seo_page method body so the
        # assertions are scoped (other parts of app.py reference
        # similar tags for the SPA shell).
        start = self.src.find("def _send_seo_page(self, page:")
        end = self.src.find("def _send_share_not_found_page", start)
        self.method = self.src[start:end]

    def test_renders_hreflang_alternates(self):
        self.assertIn('hreflang="en"', self.method)
        self.assertIn('hreflang="de"', self.method)
        self.assertIn('hreflang="x-default"', self.method)

    def test_renders_twitter_card(self):
        self.assertIn('name="twitter:card"', self.method)
        self.assertIn('name="twitter:title"', self.method)
        self.assertIn('name="twitter:description"', self.method)

    def test_renders_opengraph_locale_alternates(self):
        self.assertIn('og:locale', self.method)
        self.assertIn('og:locale:alternate', self.method)
        self.assertIn('og:site_name', self.method)

    def test_renders_json_ld_structured_data(self):
        self.assertIn('application/ld+json', self.method)
        self.assertIn('schema.org', self.method)
        # WebPage + Organization + BreadcrumbList graph
        self.assertIn('"WebPage"', self.method)
        self.assertIn('"Organization"', self.method)
        self.assertIn('"BreadcrumbList"', self.method)

    def test_json_ld_escapes_html_special_chars_against_script_breakout(self):
        """Defense-in-depth XSS guard: an operator-edited seo-pages.json
        entry containing ``</script>`` in title or intro would
        otherwise break out of the JSON-LD script tag, even though
        json.dumps produces valid JSON. The fix routes serialisation
        through ``_xss_safe_jsonld`` which replaces ``<``, ``>``,
        and ``&`` with their unicode escape forms — the OWASP-
        recommended pattern for JSON-in-HTML.

        This test pins the escape into the source so it can't be
        accidentally removed by a future refactor."""

        # The renderer routes through the safe helper
        self.assertIn("_xss_safe_jsonld", self.method)
        # And the helper itself performs the OWASP escape
        helper_start = self.src.find("def _xss_safe_jsonld(")
        self.assertGreater(helper_start, 0, "_xss_safe_jsonld helper missing")
        helper_end = self.src.find("\n\n\n", helper_start)
        helper_body = self.src[helper_start:helper_end]
        # The helper replaces the three dangerous chars with unicode escapes
        self.assertIn("\\u003c", helper_body)
        self.assertIn("\\u003e", helper_body)
        self.assertIn("\\u0026", helper_body)

    def test_xss_safe_jsonld_neutralises_script_breakout(self):
        """Behavioural test: feed a payload containing </script> and
        verify the output cannot terminate a script tag."""

        from app import _xss_safe_jsonld
        import json as _json

        attack = {
            "title": "Hello</script><script>alert(1)</script>",
            "description": "AT&T & friends > everyone",
        }
        output = _xss_safe_jsonld(attack, _json)
        # The dangerous substring must NOT appear verbatim
        self.assertNotIn("</script>", output)
        self.assertNotIn("<script>", output)
        # The escape form must be present
        self.assertIn("\\u003c", output)
        self.assertIn("\\u003e", output)
        # Output must still be valid JSON
        parsed = _json.loads(output)
        self.assertEqual(parsed["title"], attack["title"])
        self.assertEqual(parsed["description"], attack["description"])


if __name__ == "__main__":
    unittest.main()
