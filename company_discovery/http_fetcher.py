# Copyright (c) 2026 DirectJob Scout contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

from __future__ import annotations

import ipaddress
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .service import FetchResult


class BlockRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _is_public_hostname(hostname: str | None) -> bool:
    if not hostname:
        return False
    host = hostname.strip().strip("[]").casefold()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        return False
    try:
        addresses = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return False
    return True


def validate_public_http_url(url: str) -> tuple[bool, str | None]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False, "unsupported_scheme"
    if not parsed.netloc:
        return False, "missing_host"
    if not _is_public_hostname(parsed.hostname):
        return False, "non_public_host"
    return True, None


class HTTPFetcher:
    def __init__(
        self,
        timeout_seconds: float = 10.0,
        max_response_bytes: int = 1_000_000,
        max_redirects: int = 5,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_response_bytes = max_response_bytes
        self.max_redirects = max_redirects
        self.opener = build_opener(BlockRedirects)

    def fetch(self, url: str, user_agent: str) -> FetchResult:
        current_url = url
        redirects = 0
        while True:
            allowed, reason = validate_public_http_url(current_url)
            if not allowed:
                return FetchResult(url=current_url, status_code=495, text=reason or "blocked_url")

            response = self._fetch_once(current_url, user_agent)
            if response.status_code in {301, 302, 303, 307, 308}:
                location = (response.headers or {}).get("Location") or (response.headers or {}).get(
                    "location"
                )
                if not location:
                    return response
                redirects += 1
                if redirects > self.max_redirects:
                    return FetchResult(
                        url=current_url, status_code=508, text="redirect_limit_exceeded"
                    )
                current_url = urljoin(current_url, location)
                continue
            return response

    def fetch_no_redirect(self, url: str, user_agent: str) -> FetchResult:
        allowed, reason = validate_public_http_url(url)
        if not allowed:
            return FetchResult(url=url, status_code=495, text=reason or "blocked_url")
        return self._fetch_once(url, user_agent)

    def _fetch_once(self, url: str, user_agent: str) -> FetchResult:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return FetchResult(url=url, status_code=400, text="")

        request = Request(
            url,
            headers={
                "User-Agent": f"{user_agent}/0.1 (+local-user-triggered-career-page-scan)",
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.5",
            },
        )
        try:
            with self.opener.open(request, timeout=self.timeout_seconds) as response:
                body = response.read(self.max_response_bytes + 1)
                text = body[: self.max_response_bytes].decode(
                    response.headers.get_content_charset() or "utf-8",
                    errors="replace",
                )
                return FetchResult(
                    url=response.geturl(),
                    status_code=response.status,
                    text=text,
                    headers=dict(response.headers.items()),
                )
        except HTTPError as error:
            body = error.read(min(self.max_response_bytes, 64_000))
            return FetchResult(
                url=url,
                status_code=error.code,
                text=body.decode("utf-8", errors="replace"),
                headers=dict(error.headers.items()) if error.headers else {},
            )
        except (TimeoutError, URLError, OSError):
            return FetchResult(url=url, status_code=599, text="")
