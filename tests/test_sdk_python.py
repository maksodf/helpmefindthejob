# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""Python SDK contract tests (13-plan item 8/13; gap #29).

Tests run against a mock HTTP layer (no live server boot
needed) so they're fast + deterministic. Covers:

1. **Constructor validation**: base_url required; trailing
   slashes normalised.
2. **Request shape**: GET + POST headers include session cookie
   + CSRF token + Content-Type.
3. **Error mapping**: 401 → AuthRequiredError, 404 →
   ToolNotFoundError, 400 → ToolValidationError, anything else →
   HelpmefindthejobError.
4. **Typed wrappers**: snake_case Python kwargs map to the
   camelCase payload keys the server expects.
5. **Catalogue / OpenAPI fetch**: returns shape callers can
   iterate over.
6. **SDK importability**: `from helpmefindthejob_sdk import
   Client` works from a fresh Python process (no missing
   re-exports).
"""

from __future__ import annotations

import json
import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError


# Add the SDK dir to sys.path so `from helpmefindthejob_sdk
# import ...` resolves. In production the partner would copy
# the directory into their own project.
_SDK_DIR = Path(__file__).resolve().parent.parent / "sdk" / "python"
if str(_SDK_DIR) not in sys.path:
    sys.path.insert(0, str(_SDK_DIR))


from helpmefindthejob_sdk import (  # noqa: E402
    AuthRequiredError,
    Client,
    HelpmefindthejobError,
    ToolNotFoundError,
    ToolValidationError,
)


def _make_response(body: dict | list) -> BytesIO:
    """Mock urlopen() return value."""

    raw = json.dumps(body).encode("utf-8")
    f = BytesIO(raw)
    return f


class _MockUrlopen:
    """Context-manager mock for urllib.request.urlopen."""

    def __init__(self, response_body: dict | list):
        self.response = _make_response(response_body)
        self.last_request = None

    def __call__(self, request, timeout=None):
        self.last_request = request
        return _MockResponseCM(self.response)


class _MockResponseCM:
    def __init__(self, body_stream):
        self._stream = body_stream

    def __enter__(self):
        return self._stream

    def __exit__(self, *args):
        pass


class ConstructorValidation(unittest.TestCase):
    def test_base_url_required(self):
        with self.assertRaises(ValueError):
            Client(base_url="")

    def test_trailing_slash_normalised(self):
        client = Client(base_url="https://example.com/")
        self.assertEqual(client.base_url, "https://example.com")

    def test_session_cookie_optional_at_construction(self):
        # Construction succeeds without cookie; the request will
        # fail on first call instead (clearer error site)
        client = Client(base_url="https://example.com")
        self.assertEqual(client.session_cookie, "")


class RequestHeadersShape(unittest.TestCase):
    def test_get_includes_cookie(self):
        client = Client(
            base_url="https://example.com", session_cookie="abc-123"
        )
        mock_urlopen = _MockUrlopen({"tools": []})
        with patch("helpmefindthejob_sdk.client.urllib.request.urlopen", mock_urlopen):
            client.list_tools()
        req = mock_urlopen.last_request
        self.assertEqual(req.headers.get("Cookie"), "session=abc-123")
        self.assertEqual(req.headers.get("Accept"), "application/json")

    def test_post_includes_csrf_and_content_type(self):
        client = Client(
            base_url="https://example.com",
            session_cookie="abc",
            csrf_token="xyz",
        )
        mock_urlopen = _MockUrlopen({"result": {"ok": True}})
        with patch("helpmefindthejob_sdk.client.urllib.request.urlopen", mock_urlopen):
            client.call_tool("any_tool", {"k": "v"})
        req = mock_urlopen.last_request
        self.assertEqual(req.headers.get("X-csrf-token"), "xyz")
        self.assertEqual(req.headers.get("Content-type"), "application/json")
        self.assertEqual(req.get_method(), "POST")


class CallToolErrorMapping(unittest.TestCase):
    def _client(self) -> Client:
        return Client(
            base_url="https://example.com",
            session_cookie="abc",
            csrf_token="xyz",
        )

    def _make_http_error(self, code: int, body: str = "{}") -> HTTPError:
        return HTTPError(
            url="https://example.com/api/v1/tools/any",
            code=code,
            msg="error",
            hdrs={},
            fp=BytesIO(body.encode("utf-8")),
        )

    def test_401_maps_to_auth_required(self):
        with patch(
            "helpmefindthejob_sdk.client.urllib.request.urlopen",
            side_effect=self._make_http_error(401),
        ):
            with self.assertRaises(AuthRequiredError):
                self._client().call_tool("any", {})

    def test_404_maps_to_tool_not_found(self):
        with patch(
            "helpmefindthejob_sdk.client.urllib.request.urlopen",
            side_effect=self._make_http_error(404),
        ):
            with self.assertRaises(ToolNotFoundError):
                self._client().call_tool("nonexistent", {})

    def test_400_maps_to_tool_validation(self):
        with patch(
            "helpmefindthejob_sdk.client.urllib.request.urlopen",
            side_effect=self._make_http_error(
                400, body='{"error":{"code":"invalid_payload","message":"missing_required_fields:industry"}}'
            ),
        ):
            with self.assertRaises(ToolValidationError) as cm:
                self._client().call_tool("suggest_relevant_companies", {})
            self.assertIn("industry", str(cm.exception))

    def test_500_maps_to_generic_error(self):
        with patch(
            "helpmefindthejob_sdk.client.urllib.request.urlopen",
            side_effect=self._make_http_error(500),
        ):
            with self.assertRaises(HelpmefindthejobError) as cm:
                self._client().call_tool("any", {})
            # Not the more specific subclasses
            self.assertNotIsInstance(cm.exception, AuthRequiredError)
            self.assertNotIsInstance(cm.exception, ToolNotFoundError)


class TypedWrappers(unittest.TestCase):
    def test_suggest_relevant_companies_maps_snake_to_camel(self):
        client = Client(base_url="https://example.com", session_cookie="x", csrf_token="y")
        captured_body: list[bytes] = []

        def _capture(request, timeout=None):
            if request.data:
                captured_body.append(request.data)
            return _MockResponseCM(_make_response({"result": {"suggestions": []}}))

        with patch("helpmefindthejob_sdk.client.urllib.request.urlopen", side_effect=_capture):
            client.suggest_relevant_companies(
                target_roles=["Pflegekraft", "Krankenschwester"],
                industry="Healthcare",
                location="Berlin",
            )

        sent = json.loads(captured_body[0].decode("utf-8"))
        # snake_case kwargs → camelCase payload
        self.assertEqual(sent["targetRoles"], ["Pflegekraft", "Krankenschwester"])
        self.assertEqual(sent["industry"], "Healthcare")
        self.assertEqual(sent["location"], "Berlin")

    def test_add_company_to_watchlist_optional_fields(self):
        client = Client(base_url="https://example.com", session_cookie="x", csrf_token="y")
        captured: list[bytes] = []

        def _capture(request, timeout=None):
            if request.data:
                captured.append(request.data)
            return _MockResponseCM(_make_response({"result": {"id": "c1"}}))

        with patch("helpmefindthejob_sdk.client.urllib.request.urlopen", side_effect=_capture):
            # Minimal call (no optional fields)
            client.add_company_to_watchlist(
                name="ACME GmbH",
                website_url="https://acme.example.com",
            )
        sent = json.loads(captured[0].decode("utf-8"))
        self.assertEqual(sent, {"name": "ACME GmbH", "websiteUrl": "https://acme.example.com"})

        # With optional fields
        with patch("helpmefindthejob_sdk.client.urllib.request.urlopen", side_effect=_capture):
            client.add_company_to_watchlist(
                name="ACME GmbH",
                website_url="https://acme.example.com",
                sector="Healthcare",
                watch_enabled=True,
            )
        sent_full = json.loads(captured[1].decode("utf-8"))
        self.assertEqual(sent_full["sector"], "Healthcare")
        self.assertEqual(sent_full["watchEnabled"], True)


class CatalogueAndOpenApiFetch(unittest.TestCase):
    def test_list_tools_returns_list(self):
        client = Client(base_url="https://example.com", session_cookie="x")
        mock_urlopen = _MockUrlopen({
            "tools": [
                {"name": "tool1", "description": "...", "inputSchema": {}, "restPath": "/api/v1/tools/tool1"},
                {"name": "tool2", "description": "...", "inputSchema": {}, "restPath": "/api/v1/tools/tool2"},
            ]
        })
        with patch("helpmefindthejob_sdk.client.urllib.request.urlopen", mock_urlopen):
            tools = client.list_tools()
        self.assertEqual(len(tools), 2)
        self.assertEqual(tools[0]["name"], "tool1")

    def test_get_openapi_spec_returns_dict(self):
        client = Client(base_url="https://example.com", session_cookie="x")
        mock_urlopen = _MockUrlopen({
            "openapi": "3.0.3",
            "paths": {},
        })
        with patch("helpmefindthejob_sdk.client.urllib.request.urlopen", mock_urlopen):
            spec = client.get_openapi_spec()
        self.assertEqual(spec["openapi"], "3.0.3")


class SdkSurfaceImports(unittest.TestCase):
    def test_public_exports(self):
        from helpmefindthejob_sdk import (
            AuthRequiredError,
            Client,
            HelpmefindthejobError,
            ToolNotFoundError,
            ToolValidationError,
            __version__,
        )
        # Class identity sanity
        self.assertTrue(issubclass(AuthRequiredError, HelpmefindthejobError))
        self.assertTrue(issubclass(ToolNotFoundError, HelpmefindthejobError))
        self.assertTrue(issubclass(ToolValidationError, HelpmefindthejobError))
        self.assertTrue(callable(Client))
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")


class SdkReadmePresent(unittest.TestCase):
    def test_readme_documents_quickstart(self):
        readme = (_SDK_DIR / "README.md").read_text(encoding="utf-8")
        self.assertIn("Quickstart", readme)
        self.assertIn("from helpmefindthejob_sdk import Client", readme)
        self.assertIn("base_url", readme)
        self.assertIn("session_cookie", readme)


if __name__ == "__main__":
    unittest.main()
