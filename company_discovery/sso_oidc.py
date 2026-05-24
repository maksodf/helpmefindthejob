# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""OpenID Connect (OIDC) service-provider implementation
(13-plan item 12/13; gap #21).

Implements the OIDC Authorization Code flow with PKCE so an
institutional deployer can wire any standards-compliant IdP
(Okta, Azure AD / Entra ID, Google Workspace, Keycloak, Auth0,
Authentik, etc.) for single sign-on. Pairs with the SAML 2.0
SP layer in ``sso_saml.py`` so deployers running either
federation protocol can plug in.

Design:

- **Stdlib HTTP** for discovery + token-endpoint calls. The
  HTTP surface is small enough that adding ``httpx`` is
  unjustified.
- **PyJWT (via the ``cryptography`` backend)** for ID-token
  signature verification. Implementing JWT signature
  verification by hand against arbitrary IdP key sets is
  security-critical; PyJWT is the industry standard.
- **Multi-IdP via env-var config**: ``HELPMEFINDTHEJOB_OIDC_
  PROVIDERS=okta-main,azure-tenant`` plus per-provider
  ``..._ISSUER``, ``..._CLIENT_ID``, ``..._CLIENT_SECRET``,
  ``..._EMAIL_DOMAIN`` env vars. Admin-UI-managed providers
  ship as a follow-up; env-var-only is the Phase 1 default
  because it matches how most deployers actually configure
  enterprise SSO (Kubernetes secrets, Vault, etc.).
- **PKCE always on**: the Authorization Code flow with PKCE
  is the modern best practice; ``client_secret`` is still
  used (we're a confidential client) but PKCE adds defense
  against authorization-code interception.
- **Email-domain routing**: an IdP can declare
  ``email_domain=hospital.de`` so users entering an email
  with that suffix get redirected to that IdP automatically.

JIT user provisioning:

- On successful SSO callback, look up by ``(provider_id,
  sub)`` in the ``sso_links`` table.
- If not found, fall back to ``email`` match — promote the
  existing local account into an SSO account, link the
  subject id.
- If neither matches, create a new user account with
  ``email`` from the ID token and a random password (the
  user can never use it; SSO is the only login path).
- ``sso_only=True`` flag prevents the user from later
  switching to password auth via a side door.

Security:

- ``state`` is a per-request CSRF token; the callback MUST
  match what was set at /login. Defends against forged
  callbacks.
- ``nonce`` is embedded in the ID token; defends against
  token-replay across sessions.
- ``code_verifier`` (PKCE) prevents stolen authorization
  codes from being redeemed by an attacker who doesn't have
  the verifier.
- ID-token validation enforces: ``iss`` matches expected
  issuer; ``aud`` matches our client_id; ``exp`` is in the
  future; ``nonce`` matches what we set.
"""

from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import json
import logging
import os
import secrets
import time as _time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

_log = logging.getLogger(__name__)


# Env-var prefix for OIDC provider config. To configure provider
# `okta-main`, the operator sets:
#   HELPMEFINDTHEJOB_OIDC_OKTA_MAIN_ISSUER=https://...
#   HELPMEFINDTHEJOB_OIDC_OKTA_MAIN_CLIENT_ID=...
#   HELPMEFINDTHEJOB_OIDC_OKTA_MAIN_CLIENT_SECRET=...
#   HELPMEFINDTHEJOB_OIDC_OKTA_MAIN_EMAIL_DOMAIN=hospital.de  (optional)
# And lists `okta-main` in HELPMEFINDTHEJOB_OIDC_PROVIDERS.
_PROVIDER_ENV_PREFIX = "HELPMEFINDTHEJOB_OIDC_"
_PROVIDERS_LIST_ENV = "HELPMEFINDTHEJOB_OIDC_PROVIDERS"


class OidcError(RuntimeError):
    """Base error class for OIDC operations. Caller maps to
    HTTP 5xx unless a more specific subclass is raised."""


class OidcConfigError(OidcError):
    """Provider configuration is missing or malformed."""


class OidcDiscoveryError(OidcError):
    """The IdP's /.well-known/openid-configuration could not be
    fetched OR returned malformed JSON."""


class OidcStateMismatchError(OidcError):
    """The callback's `state` parameter doesn't match what we
    set at /login. Defends against forged callbacks (CSRF)."""


class OidcTokenError(OidcError):
    """Token endpoint returned a non-2xx response OR a malformed
    token response."""


class OidcIdTokenError(OidcError):
    """The ID token failed signature verification or claim
    validation (issuer mismatch, audience mismatch, expired,
    nonce mismatch)."""


@dataclass(frozen=True)
class OidcProviderConfig:
    """Operator-provided config for one OIDC IdP.

    - ``provider_id`` is our internal key for this IdP (e.g.,
      ``okta-main``). Used in routes:
      ``/api/auth/sso/oidc/<provider_id>/login``.
    - ``issuer`` is the IdP's issuer URL — used to fetch
      /.well-known/openid-configuration and to validate the
      ``iss`` claim of returned ID tokens.
    - ``client_id`` + ``client_secret`` are credentials the
      operator registered the app with at the IdP.
    - ``email_domain`` (optional) enables auto-routing: users
      whose email ends with this domain land on this IdP.
    """

    provider_id: str
    issuer: str
    client_id: str
    client_secret: str
    email_domain: str = ""


@dataclass(frozen=True)
class OidcDiscoveryDoc:
    """Subset of /.well-known/openid-configuration we care about."""

    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    userinfo_endpoint: str = ""
    end_session_endpoint: str = ""


@dataclass(frozen=True)
class AuthRequest:
    """Per-login state we stash in the session cookie / signed
    cookie. The callback compares incoming params against
    these to detect tampering."""

    provider_id: str
    state: str
    nonce: str
    code_verifier: str
    redirect_uri: str


@dataclass(frozen=True)
class UserClaims:
    """Validated claims pulled from the ID token. The HTTP
    layer uses these to JIT-provision or sign-in the user."""

    issuer: str
    subject: str
    email: str
    email_verified: bool
    name: str
    raw_claims: dict[str, Any]


def load_providers_from_env() -> list[OidcProviderConfig]:
    """Read every OIDC provider declared in env vars and return
    them. Returns empty list when no providers are declared
    (SSO simply isn't enabled — the password path stays the
    sole auth surface)."""

    list_raw = os.environ.get(_PROVIDERS_LIST_ENV, "").strip()
    if not list_raw:
        return []
    provider_ids = [p.strip() for p in list_raw.split(",") if p.strip()]
    configs: list[OidcProviderConfig] = []
    for provider_id in provider_ids:
        env_key = provider_id.upper().replace("-", "_")
        issuer = os.environ.get(f"{_PROVIDER_ENV_PREFIX}{env_key}_ISSUER", "").strip()
        client_id = os.environ.get(f"{_PROVIDER_ENV_PREFIX}{env_key}_CLIENT_ID", "").strip()
        client_secret = os.environ.get(f"{_PROVIDER_ENV_PREFIX}{env_key}_CLIENT_SECRET", "").strip()
        email_domain = os.environ.get(f"{_PROVIDER_ENV_PREFIX}{env_key}_EMAIL_DOMAIN", "").strip()
        missing = []
        if not issuer:
            missing.append("ISSUER")
        if not client_id:
            missing.append("CLIENT_ID")
        if not client_secret:
            missing.append("CLIENT_SECRET")
        if missing:
            _log.warning(
                "OIDC provider %r is in %s but missing env vars: %s — skipping",
                provider_id,
                _PROVIDERS_LIST_ENV,
                ", ".join(missing),
            )
            continue
        configs.append(
            OidcProviderConfig(
                provider_id=provider_id,
                issuer=issuer,
                client_id=client_id,
                client_secret=client_secret,
                email_domain=email_domain,
            )
        )
    return configs


def discover(issuer: str, *, timeout: float = 5.0) -> OidcDiscoveryDoc:
    """Fetch /.well-known/openid-configuration from ``issuer``.

    OIDC discovery says the well-known doc lives at
    ``{issuer}/.well-known/openid-configuration`` (with the
    issuer's trailing slash normalized). Returns the subset of
    endpoints our flow needs.
    """

    base = issuer.rstrip("/")
    url = f"{base}/.well-known/openid-configuration"
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.URLError as err:
        raise OidcDiscoveryError(f"discovery_fetch_failed:{err.reason}") from err
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError as err:
        raise OidcDiscoveryError(f"discovery_invalid_json:{err}") from err
    for required in ("issuer", "authorization_endpoint", "token_endpoint", "jwks_uri"):
        if required not in doc:
            raise OidcDiscoveryError(f"discovery_missing_field:{required}")
    return OidcDiscoveryDoc(
        issuer=doc["issuer"],
        authorization_endpoint=doc["authorization_endpoint"],
        token_endpoint=doc["token_endpoint"],
        jwks_uri=doc["jwks_uri"],
        userinfo_endpoint=doc.get("userinfo_endpoint", ""),
        end_session_endpoint=doc.get("end_session_endpoint", ""),
    )


def _b64url(data: bytes) -> str:
    """Standard base64-url-without-padding encoding used in OIDC
    PKCE + JWT."""

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_pkce() -> tuple[str, str]:
    """Generate (code_verifier, code_challenge) for PKCE per
    RFC 7636 (S256 method). The verifier is high-entropy random;
    the challenge is the SHA256 of the verifier, base64url-
    encoded."""

    verifier = _b64url(secrets.token_bytes(64))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def build_authorization_url(
    provider: OidcProviderConfig,
    discovery: OidcDiscoveryDoc,
    *,
    redirect_uri: str,
    state: str,
    nonce: str,
    code_challenge: str,
    scope: str = "openid email profile",
) -> str:
    """Construct the URL the user-agent is redirected to to start
    the SSO flow.

    The frontend issues a 302 to this URL. The user authenticates
    at the IdP, then the IdP redirects them back to our
    ``redirect_uri`` with ``?code=…&state=…``.
    """

    params = {
        "client_id": provider.client_id,
        "response_type": "code",
        "scope": scope,
        "redirect_uri": redirect_uri,
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    query = urllib.parse.urlencode(params)
    sep = "&" if "?" in discovery.authorization_endpoint else "?"
    return f"{discovery.authorization_endpoint}{sep}{query}"


def exchange_code_for_tokens(
    provider: OidcProviderConfig,
    discovery: OidcDiscoveryDoc,
    *,
    code: str,
    code_verifier: str,
    redirect_uri: str,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """POST to the token endpoint to exchange an authorization
    code for an ID token + access token. Returns the parsed
    JSON response.

    Raises OidcTokenError on non-2xx or malformed response.
    """

    body = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": provider.client_id,
            "client_secret": provider.client_secret,
            "code_verifier": code_verifier,
        }
    ).encode("ascii")
    request = urllib.request.Request(
        discovery.token_endpoint,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        body_preview = err.read().decode("utf-8", errors="replace")[:300]
        raise OidcTokenError(f"token_endpoint_http_{err.code}:{body_preview}") from err
    except urllib.error.URLError as err:
        raise OidcTokenError(f"token_endpoint_network:{err.reason}") from err
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as err:
        raise OidcTokenError(f"token_invalid_json:{err}") from err
    if "id_token" not in parsed:
        raise OidcTokenError("token_response_missing_id_token")
    return parsed


def validate_id_token(
    id_token: str,
    *,
    provider: OidcProviderConfig,
    discovery: OidcDiscoveryDoc,
    expected_nonce: str,
    leeway_seconds: int = 30,
) -> UserClaims:
    """Verify the ID token's signature against the IdP's JWKS,
    validate the standard claims (iss, aud, exp, nonce), and
    extract user info.

    Raises ``OidcIdTokenError`` on any verification failure.
    """

    try:
        import jwt
        from jwt import PyJWKClient
    except ImportError as err:  # pragma: no cover - dep is in requirements.txt
        raise OidcError("pyjwt_not_installed") from err
    try:
        # PyJWKClient caches the JWKS per instance; we create one
        # per request for simplicity. For higher-throughput
        # deploys a module-level cache by jwks_uri would amortize.
        jwks_client = PyJWKClient(discovery.jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=provider.client_id,
            issuer=discovery.issuer,
            leeway=leeway_seconds,
        )
    except jwt.PyJWTError as err:
        raise OidcIdTokenError(f"jwt_validation_failed:{err}") from err
    except Exception as err:  # noqa: BLE001 - network errors on JWKS
        raise OidcIdTokenError(f"jwks_fetch_failed:{err}") from err

    # Nonce check: defends against ID token replay across sessions
    if claims.get("nonce") != expected_nonce:
        raise OidcIdTokenError("nonce_mismatch")

    email = str(claims.get("email") or "").strip().lower()
    if not email:
        raise OidcIdTokenError("missing_email_claim")
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise OidcIdTokenError("missing_sub_claim")
    return UserClaims(
        issuer=discovery.issuer,
        subject=subject,
        email=email,
        email_verified=bool(claims.get("email_verified", False)),
        name=str(claims.get("name") or claims.get("preferred_username") or "").strip(),
        raw_claims=dict(claims),
    )


# ---------------------------------------------------------------------------
# Signed auth-state cookie helpers
# ---------------------------------------------------------------------------
#
# The OIDC dance needs us to remember `state`, `nonce`, `code_verifier`,
# `redirect_uri`, `provider_id` between /login and /callback. We could
# stash them in a SQLite table, but a signed HMAC cookie is simpler:
# - no DB roundtrip
# - no cleanup cron
# - tampering is detected (HMAC mismatch)
# - per-request — multiple in-flight logins don't collide
#
# Format: base64url(json_bytes) + "." + base64url(hmac)
# The cookie carries an `exp` field; the verifier rejects expired blobs.


_COOKIE_TTL_SECONDS = 10 * 60  # 10 minutes is plenty for an interactive login


def sign_auth_request(
    auth_request: AuthRequest, *, secret_key: str, now: float | None = None
) -> str:
    """Encode + sign an AuthRequest for cookie transport. The
    cookie value MUST be set with HttpOnly + Secure + SameSite=
    Lax by the HTTP layer."""

    if not secret_key:
        raise OidcConfigError("secret_key_required_for_cookie_signing")
    exp = int((now or _time.time()) + _COOKIE_TTL_SECONDS)
    payload = {
        "provider_id": auth_request.provider_id,
        "state": auth_request.state,
        "nonce": auth_request.nonce,
        "code_verifier": auth_request.code_verifier,
        "redirect_uri": auth_request.redirect_uri,
        "exp": exp,
    }
    body = json.dumps(payload, sort_keys=True).encode("utf-8")
    sig = _hmac.new(secret_key.encode("utf-8"), body, hashlib.sha256).digest()
    return f"{_b64url(body)}.{_b64url(sig)}"


def verify_auth_request(
    cookie_value: str, *, secret_key: str, now: float | None = None
) -> AuthRequest:
    """Decode + verify a cookie produced by :func:`sign_auth_request`.

    Raises OidcStateMismatchError on any tampering or expiry — the
    HTTP layer maps to 400.
    """

    if not cookie_value or "." not in cookie_value:
        raise OidcStateMismatchError("malformed_cookie")
    try:
        body_b64, sig_b64 = cookie_value.split(".", 1)
        body = base64.urlsafe_b64decode(body_b64 + "=" * (-len(body_b64) % 4))
        sig = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
    except (ValueError, base64.binascii.Error) as err:  # type: ignore[attr-defined]
        raise OidcStateMismatchError(f"cookie_decode_failed:{err}") from err
    expected_sig = _hmac.new(secret_key.encode("utf-8"), body, hashlib.sha256).digest()
    if not _hmac.compare_digest(sig, expected_sig):
        raise OidcStateMismatchError("cookie_hmac_mismatch")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as err:
        raise OidcStateMismatchError(f"cookie_invalid_json:{err}") from err
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp < (now or _time.time()):
        raise OidcStateMismatchError("cookie_expired")
    return AuthRequest(
        provider_id=str(payload.get("provider_id") or ""),
        state=str(payload.get("state") or ""),
        nonce=str(payload.get("nonce") or ""),
        code_verifier=str(payload.get("code_verifier") or ""),
        redirect_uri=str(payload.get("redirect_uri") or ""),
    )


def route_by_email_domain(
    providers: list[OidcProviderConfig], email: str
) -> OidcProviderConfig | None:
    """Find the OIDC provider configured for the email's domain.
    Returns None if no provider claims this domain (caller
    falls back to the password login path)."""

    if not email or "@" not in email:
        return None
    domain = email.split("@", 1)[1].lower()
    for provider in providers:
        if provider.email_domain and provider.email_domain.lower() == domain:
            return provider
    return None
