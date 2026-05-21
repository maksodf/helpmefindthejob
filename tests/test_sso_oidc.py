# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""OIDC + JIT-provisioning contract tests (13-plan item 12/13).

Pins:
1. PKCE generation (verifier high-entropy, challenge is SHA256(verifier))
2. Authorization URL has every required parameter
3. Discovery parses + handles missing fields
4. Token exchange happy path + error mapping
5. ID-token validation: signature verified, claims checked,
   nonce mismatch rejected, expired token rejected, wrong
   audience rejected
6. JIT provisioning: (provider, subject) lookup wins, email
   fallback links existing user, neither match → new user
7. Email-domain routing picks the right provider
8. Provider env-var loading skips incomplete entries with a
   warning rather than crashing
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from company_discovery.sso_oidc import (
    AuthRequest,
    OidcConfigError,
    OidcDiscoveryDoc,
    OidcDiscoveryError,
    OidcError,
    OidcIdTokenError,
    OidcProviderConfig,
    OidcStateMismatchError,
    OidcTokenError,
    UserClaims,
    _b64url,
    build_authorization_url,
    discover,
    exchange_code_for_tokens,
    generate_pkce,
    load_providers_from_env,
    route_by_email_domain,
    validate_id_token,
)


# -------------------------------------------------------------------------
# PKCE
# -------------------------------------------------------------------------


class PkceGeneration(unittest.TestCase):
    def test_verifier_high_entropy(self):
        v1, _ = generate_pkce()
        v2, _ = generate_pkce()
        self.assertNotEqual(v1, v2)
        # Length: 64 random bytes base64-url-no-pad = 86 chars
        self.assertEqual(len(v1), 86)
        self.assertEqual(len(v2), 86)

    def test_challenge_is_sha256_of_verifier(self):
        verifier, challenge = generate_pkce()
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).rstrip(b"=").decode("ascii")
        self.assertEqual(challenge, expected)

    def test_verifier_only_url_safe_chars(self):
        # PKCE verifier must be base64-url-no-pad (A-Z, a-z, 0-9, -, _)
        for _ in range(20):
            v, _ = generate_pkce()
            self.assertRegex(v, r"^[A-Za-z0-9\-_]+$")


# -------------------------------------------------------------------------
# Authorization URL
# -------------------------------------------------------------------------


class AuthorizationUrlBuilder(unittest.TestCase):
    def setUp(self):
        self.provider = OidcProviderConfig(
            provider_id="okta-test",
            issuer="https://okta.example.com",
            client_id="our-client-id",
            client_secret="our-secret",
        )
        self.discovery = OidcDiscoveryDoc(
            issuer="https://okta.example.com",
            authorization_endpoint="https://okta.example.com/oauth2/v1/authorize",
            token_endpoint="https://okta.example.com/oauth2/v1/token",
            jwks_uri="https://okta.example.com/oauth2/v1/keys",
        )

    def test_contains_all_required_params(self):
        url = build_authorization_url(
            self.provider,
            self.discovery,
            redirect_uri="https://app.example.com/sso/callback",
            state="state-abc",
            nonce="nonce-xyz",
            code_challenge="challenge-123",
        )
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        self.assertEqual(params["client_id"], ["our-client-id"])
        self.assertEqual(params["response_type"], ["code"])
        self.assertEqual(params["state"], ["state-abc"])
        self.assertEqual(params["nonce"], ["nonce-xyz"])
        self.assertEqual(params["code_challenge"], ["challenge-123"])
        self.assertEqual(params["code_challenge_method"], ["S256"])
        self.assertEqual(
            params["redirect_uri"], ["https://app.example.com/sso/callback"]
        )

    def test_default_scope_includes_openid_email_profile(self):
        url = build_authorization_url(
            self.provider,
            self.discovery,
            redirect_uri="https://x.example/cb",
            state="s",
            nonce="n",
            code_challenge="c",
        )
        params = parse_qs(urlparse(url).query)
        self.assertEqual(params["scope"], ["openid email profile"])

    def test_handles_authorization_endpoint_with_existing_query(self):
        discovery_with_q = OidcDiscoveryDoc(
            issuer="https://x.example",
            authorization_endpoint="https://x.example/auth?tenant=abc",
            token_endpoint="https://x.example/token",
            jwks_uri="https://x.example/jwks",
        )
        url = build_authorization_url(
            self.provider,
            discovery_with_q,
            redirect_uri="https://x.example/cb",
            state="s",
            nonce="n",
            code_challenge="c",
        )
        # Joining must use '&' not '?' since query is already present
        self.assertNotIn("?tenant=abc?", url)
        self.assertIn("?tenant=abc&", url)


# -------------------------------------------------------------------------
# Discovery
# -------------------------------------------------------------------------


class DiscoveryParsing(unittest.TestCase):
    def test_happy_path_returns_doc(self):
        well_known = {
            "issuer": "https://idp.example.com",
            "authorization_endpoint": "https://idp.example.com/authorize",
            "token_endpoint": "https://idp.example.com/token",
            "jwks_uri": "https://idp.example.com/jwks",
            "userinfo_endpoint": "https://idp.example.com/userinfo",
        }
        from io import BytesIO

        mock_response = BytesIO(json.dumps(well_known).encode("utf-8"))

        class _Ctx:
            def __enter__(self):
                return mock_response

            def __exit__(self, *args):
                pass

        with patch(
            "company_discovery.sso_oidc.urllib.request.urlopen",
            return_value=_Ctx(),
        ):
            doc = discover("https://idp.example.com")
        self.assertEqual(doc.issuer, "https://idp.example.com")
        self.assertEqual(doc.authorization_endpoint, "https://idp.example.com/authorize")
        self.assertEqual(doc.userinfo_endpoint, "https://idp.example.com/userinfo")

    def test_missing_required_field_raises(self):
        incomplete = {"issuer": "x", "authorization_endpoint": "y"}
        from io import BytesIO

        mock_response = BytesIO(json.dumps(incomplete).encode("utf-8"))

        class _Ctx:
            def __enter__(self):
                return mock_response

            def __exit__(self, *args):
                pass

        with patch(
            "company_discovery.sso_oidc.urllib.request.urlopen",
            return_value=_Ctx(),
        ):
            with self.assertRaises(OidcDiscoveryError) as cm:
                discover("https://x.example.com")
        self.assertIn("discovery_missing_field", str(cm.exception))

    def test_invalid_json_raises(self):
        from io import BytesIO

        mock_response = BytesIO(b"not json {{{")

        class _Ctx:
            def __enter__(self):
                return mock_response

            def __exit__(self, *args):
                pass

        with patch(
            "company_discovery.sso_oidc.urllib.request.urlopen",
            return_value=_Ctx(),
        ):
            with self.assertRaises(OidcDiscoveryError):
                discover("https://x.example.com")

    def test_well_known_path_normalised(self):
        # The discovery URL must be {issuer}/.well-known/openid-configuration
        # Even when issuer has a trailing slash.
        captured: list[str] = []

        class _Ctx:
            def __enter__(self):
                from io import BytesIO

                return BytesIO(b'{"issuer":"x","authorization_endpoint":"y","token_endpoint":"z","jwks_uri":"j"}')

            def __exit__(self, *args):
                pass

        def fake_urlopen(req, timeout=None):
            captured.append(req.full_url)
            return _Ctx()

        with patch(
            "company_discovery.sso_oidc.urllib.request.urlopen", side_effect=fake_urlopen
        ):
            discover("https://idp.example.com/")  # trailing slash
        self.assertEqual(
            captured[0],
            "https://idp.example.com/.well-known/openid-configuration",
        )


# -------------------------------------------------------------------------
# Env-var provider loading
# -------------------------------------------------------------------------


class ProviderEnvLoading(unittest.TestCase):
    def setUp(self):
        self._original_env = dict(os.environ)

    def tearDown(self):
        for key in list(os.environ):
            if key.startswith("HELPMEFINDTHEJOB_OIDC_"):
                if key not in self._original_env:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = self._original_env[key]

    def test_empty_when_no_providers_listed(self):
        os.environ.pop("HELPMEFINDTHEJOB_OIDC_PROVIDERS", None)
        self.assertEqual(load_providers_from_env(), [])

    def test_complete_provider_loads(self):
        os.environ["HELPMEFINDTHEJOB_OIDC_PROVIDERS"] = "okta-main"
        os.environ["HELPMEFINDTHEJOB_OIDC_OKTA_MAIN_ISSUER"] = "https://x.okta.com"
        os.environ["HELPMEFINDTHEJOB_OIDC_OKTA_MAIN_CLIENT_ID"] = "cid"
        os.environ["HELPMEFINDTHEJOB_OIDC_OKTA_MAIN_CLIENT_SECRET"] = "sec"
        os.environ["HELPMEFINDTHEJOB_OIDC_OKTA_MAIN_EMAIL_DOMAIN"] = "hospital.de"
        providers = load_providers_from_env()
        self.assertEqual(len(providers), 1)
        p = providers[0]
        self.assertEqual(p.provider_id, "okta-main")
        self.assertEqual(p.issuer, "https://x.okta.com")
        self.assertEqual(p.email_domain, "hospital.de")

    def test_incomplete_provider_skipped(self):
        # Missing CLIENT_SECRET — provider should be skipped, not crash
        os.environ["HELPMEFINDTHEJOB_OIDC_PROVIDERS"] = "broken-idp"
        os.environ["HELPMEFINDTHEJOB_OIDC_BROKEN_IDP_ISSUER"] = "https://x"
        os.environ["HELPMEFINDTHEJOB_OIDC_BROKEN_IDP_CLIENT_ID"] = "cid"
        providers = load_providers_from_env()
        self.assertEqual(providers, [])

    def test_multiple_providers_load_all(self):
        os.environ["HELPMEFINDTHEJOB_OIDC_PROVIDERS"] = "okta-main,azure-tenant"
        for prefix in ("OKTA_MAIN", "AZURE_TENANT"):
            os.environ[f"HELPMEFINDTHEJOB_OIDC_{prefix}_ISSUER"] = "https://x"
            os.environ[f"HELPMEFINDTHEJOB_OIDC_{prefix}_CLIENT_ID"] = "cid"
            os.environ[f"HELPMEFINDTHEJOB_OIDC_{prefix}_CLIENT_SECRET"] = "sec"
        providers = load_providers_from_env()
        self.assertEqual(len(providers), 2)
        ids = {p.provider_id for p in providers}
        self.assertEqual(ids, {"okta-main", "azure-tenant"})


# -------------------------------------------------------------------------
# Email-domain routing
# -------------------------------------------------------------------------


class EmailDomainRouting(unittest.TestCase):
    def setUp(self):
        self.providers = [
            OidcProviderConfig(
                provider_id="okta-hospital",
                issuer="https://x",
                client_id="c",
                client_secret="s",
                email_domain="hospital.de",
            ),
            OidcProviderConfig(
                provider_id="azure-ngo",
                issuer="https://y",
                client_id="c",
                client_secret="s",
                email_domain="ngo.org",
            ),
            OidcProviderConfig(
                provider_id="generic-no-domain",
                issuer="https://z",
                client_id="c",
                client_secret="s",
                email_domain="",  # no domain → never auto-routed
            ),
        ]

    def test_matching_domain_routes(self):
        p = route_by_email_domain(self.providers, "alice@hospital.de")
        self.assertEqual(p.provider_id, "okta-hospital")
        p2 = route_by_email_domain(self.providers, "bob@NGO.ORG")  # case-insensitive
        self.assertEqual(p2.provider_id, "azure-ngo")

    def test_unmatched_domain_returns_none(self):
        self.assertIsNone(route_by_email_domain(self.providers, "alice@other.com"))

    def test_empty_email_returns_none(self):
        self.assertIsNone(route_by_email_domain(self.providers, ""))
        self.assertIsNone(route_by_email_domain(self.providers, "no-at-sign"))

    def test_provider_with_no_domain_never_auto_routes(self):
        # generic-no-domain is in the list but email_domain=""
        # should not match anything
        for email in ("a@hospital.de", "b@ngo.org", "c@anywhere.com"):
            p = route_by_email_domain(
                [self.providers[2]], email  # only the no-domain provider
            )
            self.assertIsNone(p)


# -------------------------------------------------------------------------
# ID token validation (with PyJWT mock)
# -------------------------------------------------------------------------


def _make_id_token(claims: dict) -> str:
    """Helper: build an unsigned JWT-shaped string (header.payload.sig)
    for tests that mock the signature verification."""

    header = _b64url(json.dumps({"alg": "RS256", "kid": "k1"}).encode())
    body = _b64url(json.dumps(claims).encode())
    sig = _b64url(b"fake-signature")
    return f"{header}.{body}.{sig}"


class IdTokenValidation(unittest.TestCase):
    def setUp(self):
        self.provider = OidcProviderConfig(
            provider_id="x",
            issuer="https://idp.example",
            client_id="our-client",
            client_secret="s",
        )
        self.discovery = OidcDiscoveryDoc(
            issuer="https://idp.example",
            authorization_endpoint="https://idp.example/auth",
            token_endpoint="https://idp.example/token",
            jwks_uri="https://idp.example/jwks",
        )

    def _patched_jwt_decode(self, claims_to_return):
        """Patch jwt.decode to return the claims we want, simulating
        a successful signature verification."""

        return patch(
            "jwt.decode",
            return_value=claims_to_return,
        )

    def _patched_jwks_client(self):
        """Patch the PyJWKClient so signing-key lookup doesn't try
        to hit the network."""

        mock_client = MagicMock()
        mock_key = MagicMock()
        mock_key.key = "fake-key"
        mock_client.get_signing_key_from_jwt.return_value = mock_key
        return patch("jwt.PyJWKClient", return_value=mock_client)

    def test_valid_token_returns_user_claims(self):
        token = _make_id_token({})  # contents don't matter; we mock decode
        claims = {
            "iss": "https://idp.example",
            "aud": "our-client",
            "sub": "user-123",
            "email": "alice@hospital.de",
            "email_verified": True,
            "name": "Alice Schmidt",
            "nonce": "expected-nonce",
            "exp": int(time.time()) + 600,
        }
        with self._patched_jwks_client(), self._patched_jwt_decode(claims):
            result = validate_id_token(
                token,
                provider=self.provider,
                discovery=self.discovery,
                expected_nonce="expected-nonce",
            )
        self.assertEqual(result.subject, "user-123")
        self.assertEqual(result.email, "alice@hospital.de")
        self.assertTrue(result.email_verified)
        self.assertEqual(result.name, "Alice Schmidt")

    def test_nonce_mismatch_rejected(self):
        token = _make_id_token({})
        claims = {
            "iss": "https://idp.example",
            "aud": "our-client",
            "sub": "user-123",
            "email": "alice@x.com",
            "nonce": "DIFFERENT",  # mismatch
        }
        with self._patched_jwks_client(), self._patched_jwt_decode(claims):
            with self.assertRaises(OidcIdTokenError) as cm:
                validate_id_token(
                    token,
                    provider=self.provider,
                    discovery=self.discovery,
                    expected_nonce="expected-nonce",
                )
        self.assertIn("nonce_mismatch", str(cm.exception))

    def test_missing_email_rejected(self):
        token = _make_id_token({})
        claims = {
            "iss": "https://idp.example",
            "aud": "our-client",
            "sub": "user-123",
            "nonce": "expected-nonce",
            # email missing
        }
        with self._patched_jwks_client(), self._patched_jwt_decode(claims):
            with self.assertRaises(OidcIdTokenError) as cm:
                validate_id_token(
                    token,
                    provider=self.provider,
                    discovery=self.discovery,
                    expected_nonce="expected-nonce",
                )
        self.assertIn("missing_email_claim", str(cm.exception))

    def test_jwt_signature_failure_propagates(self):
        token = _make_id_token({})
        import jwt as pyjwt

        with self._patched_jwks_client():
            with patch(
                "jwt.decode",
                side_effect=pyjwt.InvalidSignatureError("bad sig"),
            ):
                with self.assertRaises(OidcIdTokenError) as cm:
                    validate_id_token(
                        token,
                        provider=self.provider,
                        discovery=self.discovery,
                        expected_nonce="any",
                    )
        self.assertIn("jwt_validation_failed", str(cm.exception))


# -------------------------------------------------------------------------
# JIT provisioning via AuthStore
# -------------------------------------------------------------------------


class JitProvisioning(unittest.TestCase):
    def setUp(self):
        from company_discovery.auth import AuthStore

        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = AuthStore(
            Path(self.tmp.name) / "auth.sqlite3",
            "test-secret-must-be-at-least-32-bytes-padding",
        )
        self.addCleanup(self.store.close)

    def test_first_sso_login_creates_user(self):
        user = self.store.find_or_create_sso_user(
            provider_id="okta-main",
            subject="okta|123",
            email="alice@hospital.de",
        )
        self.assertEqual(user.email, "alice@hospital.de")
        # User exists in users table
        self.assertEqual(self.store.get_user(user.id).email, "alice@hospital.de")
        # And a link row exists
        links = self.store.list_sso_links_for_user(user.id)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["providerId"], "okta-main")
        self.assertEqual(links[0]["subject"], "okta|123")

    def test_second_sso_login_finds_existing_user_by_subject(self):
        u1 = self.store.find_or_create_sso_user(
            provider_id="okta-main",
            subject="okta|123",
            email="alice@hospital.de",
        )
        u2 = self.store.find_or_create_sso_user(
            provider_id="okta-main",
            subject="okta|123",
            email="alice@hospital.de",
        )
        self.assertEqual(u1.id, u2.id)

    def test_email_change_at_idp_still_finds_user_by_subject(self):
        u1 = self.store.find_or_create_sso_user(
            provider_id="okta-main",
            subject="okta|123",
            email="alice@hospital.de",
        )
        # User changes email at the IdP; we still get the same local user
        u2 = self.store.find_or_create_sso_user(
            provider_id="okta-main",
            subject="okta|123",
            email="alice-new@hospital.de",
        )
        self.assertEqual(u1.id, u2.id)

    def test_email_match_links_existing_local_user(self):
        # Existing password-only user
        existing = self.store.create_user(
            "bob@hospital.de", "long-password-1234"
        )
        # First SSO login with a different subject but matching email
        linked = self.store.find_or_create_sso_user(
            provider_id="azure",
            subject="azure|999",
            email="bob@hospital.de",
        )
        self.assertEqual(existing.id, linked.id)
        # And the link is recorded
        links = self.store.list_sso_links_for_user(existing.id)
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["subject"], "azure|999")

    def test_invalid_email_rejected(self):
        with self.assertRaises(ValueError):
            self.store.find_or_create_sso_user(
                provider_id="okta-main",
                subject="x",
                email="not-an-email",
            )

    def test_missing_provider_id_rejected(self):
        with self.assertRaises(ValueError):
            self.store.find_or_create_sso_user(
                provider_id="",
                subject="x",
                email="a@b.com",
            )

    def test_missing_subject_rejected(self):
        with self.assertRaises(ValueError):
            self.store.find_or_create_sso_user(
                provider_id="okta",
                subject="",
                email="a@b.com",
            )

    def test_session_creatable_for_sso_user(self):
        user = self.store.find_or_create_sso_user(
            provider_id="okta",
            subject="okta|1",
            email="x@y.com",
        )
        session = self.store.create_session(user)
        self.assertTrue(session.token)
        self.assertTrue(session.csrf_token)
        self.assertEqual(session.user.id, user.id)


# -------------------------------------------------------------------------
# Token exchange error mapping
# -------------------------------------------------------------------------


class TokenExchangeErrors(unittest.TestCase):
    def setUp(self):
        self.provider = OidcProviderConfig(
            provider_id="x",
            issuer="https://idp",
            client_id="c",
            client_secret="s",
        )
        self.discovery = OidcDiscoveryDoc(
            issuer="https://idp",
            authorization_endpoint="https://idp/auth",
            token_endpoint="https://idp/token",
            jwks_uri="https://idp/jwks",
        )

    def test_http_error_maps_to_token_error(self):
        from io import BytesIO

        from urllib.error import HTTPError

        err = HTTPError(
            url="https://idp/token",
            code=400,
            msg="bad request",
            hdrs={},
            fp=BytesIO(b'{"error":"invalid_grant"}'),
        )
        with patch(
            "company_discovery.sso_oidc.urllib.request.urlopen", side_effect=err
        ):
            with self.assertRaises(OidcTokenError) as cm:
                exchange_code_for_tokens(
                    self.provider,
                    self.discovery,
                    code="bad-code",
                    code_verifier="v",
                    redirect_uri="r",
                )
        self.assertIn("token_endpoint_http_400", str(cm.exception))

    def test_missing_id_token_in_response_raises(self):
        from io import BytesIO

        body = json.dumps({"access_token": "a"}).encode()
        mock_response = BytesIO(body)

        class _Ctx:
            def __enter__(self):
                return mock_response

            def __exit__(self, *args):
                pass

        with patch(
            "company_discovery.sso_oidc.urllib.request.urlopen", return_value=_Ctx()
        ):
            with self.assertRaises(OidcTokenError) as cm:
                exchange_code_for_tokens(
                    self.provider,
                    self.discovery,
                    code="c",
                    code_verifier="v",
                    redirect_uri="r",
                )
        self.assertIn("missing_id_token", str(cm.exception))


class SignedCookieRoundtrip(unittest.TestCase):
    """The auth-request cookie must roundtrip cleanly under the
    right secret + reject tampering / expiry / wrong secret."""

    def setUp(self):
        from company_discovery.sso_oidc import (
            sign_auth_request,
            verify_auth_request,
        )

        self.sign = sign_auth_request
        self.verify = verify_auth_request
        self.req = AuthRequest(
            provider_id="okta-test",
            state="state-abc",
            nonce="nonce-xyz",
            code_verifier="verifier-123",
            redirect_uri="https://app.example/sso/callback",
        )
        self.secret = "a-secret-at-least-32-bytes-padding-for-tests"

    def test_roundtrip_returns_same_fields(self):
        cookie = self.sign(self.req, secret_key=self.secret)
        result = self.verify(cookie, secret_key=self.secret)
        self.assertEqual(result.provider_id, "okta-test")
        self.assertEqual(result.state, "state-abc")
        self.assertEqual(result.nonce, "nonce-xyz")
        self.assertEqual(result.code_verifier, "verifier-123")
        self.assertEqual(result.redirect_uri, "https://app.example/sso/callback")

    def test_tampered_payload_rejected(self):
        cookie = self.sign(self.req, secret_key=self.secret)
        body_b64, sig_b64 = cookie.split(".", 1)
        # Decode + modify + re-encode body without recomputing sig
        body = base64.urlsafe_b64decode(body_b64 + "=" * (-len(body_b64) % 4))
        payload = json.loads(body)
        payload["nonce"] = "TAMPERED"
        new_body = json.dumps(payload, sort_keys=True).encode()
        tampered = (
            base64.urlsafe_b64encode(new_body).rstrip(b"=").decode("ascii")
            + "."
            + sig_b64
        )
        with self.assertRaises(OidcStateMismatchError) as cm:
            self.verify(tampered, secret_key=self.secret)
        self.assertIn("hmac_mismatch", str(cm.exception))

    def test_wrong_secret_rejected(self):
        cookie = self.sign(self.req, secret_key=self.secret)
        with self.assertRaises(OidcStateMismatchError):
            self.verify(cookie, secret_key="different-secret-32-bytes-padding")

    def test_expired_cookie_rejected(self):
        # Sign with a "now" that's 1h ago — TTL is 10 minutes
        old_now = time.time() - 3600
        cookie = self.sign(self.req, secret_key=self.secret, now=old_now)
        with self.assertRaises(OidcStateMismatchError) as cm:
            self.verify(cookie, secret_key=self.secret)
        self.assertIn("expired", str(cm.exception))

    def test_malformed_cookie_rejected(self):
        with self.assertRaises(OidcStateMismatchError):
            self.verify("not-a-real-cookie", secret_key=self.secret)
        with self.assertRaises(OidcStateMismatchError):
            self.verify("", secret_key=self.secret)


class HttpRoutesPresence(unittest.TestCase):
    """Pin the three OIDC HTTP routes in app.py so a future
    refactor that quietly removes them fails CI."""

    @classmethod
    def setUpClass(cls):
        cls.src = Path(
            "/Users/fouad./Desktop/NasserMCPserver/app.py"
        ).read_text(encoding="utf-8")

    def test_providers_route_present(self):
        self.assertIn('"/api/auth/sso/oidc/providers"', self.src)

    def test_login_route_present(self):
        self.assertIn("sso_login_match", self.src)
        self.assertIn("sso/oidc/", self.src)
        self.assertIn("build_authorization_url", self.src)
        self.assertIn("sign_auth_request", self.src)

    def test_callback_route_present(self):
        self.assertIn("sso_callback_match", self.src)
        self.assertIn("verify_auth_request", self.src)
        self.assertIn("exchange_code_for_tokens", self.src)
        self.assertIn("validate_id_token", self.src)
        self.assertIn("find_or_create_sso_user", self.src)

    def test_callback_clears_auth_state_cookie(self):
        # The callback MUST clear the sso_auth_state cookie after
        # consuming it (Max-Age=0). Otherwise a leaked auth-state
        # cookie could be replayed.
        self.assertRegex(
            self.src,
            r"sso_auth_state=;\s*Path=/;\s*Max-Age=0",
        )

    def test_callback_creates_session_cookie(self):
        # After successful callback, the user MUST get a real
        # session cookie via session_cookie_header.
        self.assertIn("session_cookie_header(", self.src)

    def test_callback_logs_analytics_event(self):
        # An sso_login analytics event MUST fire so the
        # transparency dashboard can count SSO logins.
        self.assertRegex(self.src, r'"sso_login"')


if __name__ == "__main__":
    unittest.main()
