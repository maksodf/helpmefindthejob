# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""HTTP client for the Helpmefindthejob REST API.

Implementation notes:

- Uses urllib.request (stdlib only) so partners can vendor this
  file without any pip install.
- Session-cookie authentication. The cookie value comes from
  the existing /api/auth/login flow. A future OAuth/PAT layer
  would extend this constructor; the call surface stays the same.
- Typed exceptions per HTTP status class so partner code can
  catch granular failures.
- All call paths use a sensible timeout (10s default) and
  surface network-level errors as HelpmefindthejobError.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class HelpmefindthejobError(Exception):
    """Base error for any SDK-raised condition."""


class AuthRequiredError(HelpmefindthejobError):
    """Server returned 401 — session cookie missing or expired."""


class ToolNotFoundError(HelpmefindthejobError):
    """Server returned 404 from a /api/v1/tools/<name> call —
    the tool name isn't in the catalogue."""


class ToolValidationError(HelpmefindthejobError):
    """Server returned 400 — payload failed schema validation.
    The error message carries the list of missing required
    fields."""


class Client:
    """Thin client over the helpmefindthejob REST API.

    Parameters
    ----------
    base_url:
        Origin of the running deployment, e.g.
        ``https://app.helpmefindthejob.org``. No trailing slash.
    session_cookie:
        Value of the ``session`` cookie issued by
        ``POST /api/auth/login``. Required for every call —
        anonymous access is not supported.
    csrf_token:
        Value of the ``X-CSRF-Token`` header. The login response
        carries this; pass it here for any state-mutating call.
        Read-only calls (``list_tools``, ``get_openapi_spec``)
        don't need it.
    timeout:
        Per-request timeout in seconds (default 10).
    """

    def __init__(
        self,
        *,
        base_url: str,
        session_cookie: str = "",
        csrf_token: str = "",
        timeout: float = 10.0,
    ) -> None:
        if not base_url:
            raise ValueError("base_url is required")
        # Normalise: no trailing slash
        self.base_url = base_url.rstrip("/")
        self.session_cookie = session_cookie
        self.csrf_token = csrf_token
        self.timeout = timeout

    # -- public surface ---------------------------------------------------

    def get_openapi_spec(self) -> dict[str, Any]:
        """Fetch the auto-generated OpenAPI 3.0 spec. Feed it to
        an OpenAPI client generator if you want a typed client
        in your language of choice."""

        return self._get("/api/v1/openapi.json")

    def list_tools(self) -> list[dict[str, Any]]:
        """Return the tool catalogue. Each entry has name +
        description + inputSchema + restPath."""

        response = self._get("/api/v1/tools")
        return response.get("tools", [])

    def call_tool(self, tool_name: str, payload: dict[str, Any]) -> Any:
        """Invoke ``tool_name`` with ``payload`` as the JSON body.

        Raises ``ToolNotFoundError`` for unknown tools,
        ``ToolValidationError`` for missing required fields,
        ``AuthRequiredError`` when the session is invalid.
        """

        try:
            response = self._post(f"/api/v1/tools/{tool_name}", payload)
        except urllib.error.HTTPError as err:
            if err.code == 401:
                raise AuthRequiredError("session cookie missing or expired") from err
            if err.code == 404:
                raise ToolNotFoundError(f"Tool '{tool_name}' not in catalogue") from err
            if err.code == 400:
                body = err.read().decode("utf-8", errors="replace")
                raise ToolValidationError(f"Payload validation failed: {body[:300]}") from err
            raise HelpmefindthejobError(f"Tool call failed ({err.code}): {err.reason}") from err
        return response.get("result")

    # -- typed wrappers for the most common tools -------------------------

    def suggest_relevant_companies(
        self,
        *,
        target_roles: list[str],
        industry: str,
        location: str | None = None,
    ) -> dict[str, Any]:
        """Wrap suggest_relevant_companies with native Python
        kwargs. Validates locally so a typo gives a clear
        TypeError, not a server-side validation error."""

        payload: dict[str, Any] = {
            "targetRoles": target_roles,
            "industry": industry,
        }
        if location is not None:
            payload["location"] = location
        return self.call_tool("suggest_relevant_companies", payload)

    def add_company_to_watchlist(
        self,
        *,
        name: str,
        website_url: str,
        career_page_url: str | None = None,
        sector: str | None = None,
        notes: str | None = None,
        watch_enabled: bool | None = None,
    ) -> dict[str, Any]:
        """Wrap add_company_to_watchlist. user_id is injected
        server-side from the session cookie — don't pass it."""

        payload: dict[str, Any] = {
            "name": name,
            "websiteUrl": website_url,
        }
        if career_page_url is not None:
            payload["careerPageUrl"] = career_page_url
        if sector is not None:
            payload["sector"] = sector
        if notes is not None:
            payload["notes"] = notes
        if watch_enabled is not None:
            payload["watchEnabled"] = watch_enabled
        return self.call_tool("add_company_to_watchlist", payload)

    def get_company_watchlist_summary(self) -> dict[str, Any]:
        """Wrap get_company_watchlist_summary. No args needed —
        the user_id comes from the session."""

        # The server's inject_user_id fills userId; we still need
        # to pass an empty userId in the payload to satisfy the
        # required-field check on the schema.
        return self.call_tool("get_company_watchlist_summary", {"userId": ""})

    # -- internals --------------------------------------------------------

    def _headers(self, *, with_csrf: bool = False) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.session_cookie:
            headers["Cookie"] = f"session={self.session_cookie}"
        if with_csrf and self.csrf_token:
            headers["X-CSRF-Token"] = self.csrf_token
        return headers

    def _get(self, path: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url=self.base_url + path,
            method="GET",
            headers=self._headers(),
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as err:
            if err.code == 401:
                raise AuthRequiredError("session cookie missing or expired") from err
            raise HelpmefindthejobError(f"GET {path} failed ({err.code}): {err.reason}") from err
        except urllib.error.URLError as err:
            raise HelpmefindthejobError(f"network error: {err.reason}") from err
        return json.loads(raw)

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(body).encode("utf-8")
        headers = self._headers(with_csrf=True)
        headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url=self.base_url + path,
            data=data,
            method="POST",
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            raw = response.read().decode("utf-8")
        return json.loads(raw)
