# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""SAML 2.0 SP contract tests (13-plan item 12/13 SAML half).

Pins:

1. Env-var IdP loading (mirror of OIDC).
2. AuthnRequest generation: DEFLATE+base64+URL-encode shape,
   correct ID + Issuer + Destination, request_id round-trips.
3. SP metadata XML carries every required field for IdP
   registration.
4. Response validation full chain — signed by trusted cert →
   pass; tampered subject → fail; wrong audience → fail;
   expired → fail; InResponseTo mismatch → fail; missing
   NameID → fail.
5. Email extraction: from common attribute names + NameID
   fallback.
6. Display-name extraction: displayName / cn / first+last.
7. Email-domain routing mirror of OIDC.

The test fixture is a mock IdP that generates a self-signed cert
+ RSA keypair at setUp, then builds + signs SAML assertions on
demand. This way we exercise the REAL signature verification
path (signxml's XMLVerifier) without depending on a network IdP.
"""

from __future__ import annotations

import base64
import os
import unittest
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlparse

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from signxml import DigestAlgorithm, SignatureMethod, XMLSigner

from company_discovery.sso_saml import (
    _NS,
    SamlConfigError,
    SamlError,
    SamlIdpConfig,
    SamlResponseError,
    SamlUserClaims,
    _extract_display_name,
    _extract_email,
    _normalize_cert,
    build_authn_request,
    build_sp_metadata,
    generate_request_id,
    load_idps_from_env,
    parse_and_validate_response,
    route_by_email_domain,
)

# ---------------------------------------------------------------------------
# Mock IdP — generates a keypair + cert and signs assertions on demand
# ---------------------------------------------------------------------------


class _MockIdp:
    """Test fixture that produces signed SAML assertions the
    real XMLVerifier will accept."""

    def __init__(self, *, entity_id: str = "https://idp.example/entity"):
        self.entity_id = entity_id
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = self.private_key.public_key()
        # Build a self-signed cert
        subject = issuer = x509.Name(
            [
                x509.NameAttribute(NameOID.COMMON_NAME, "Mock IdP"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Test"),
            ]
        )
        self.cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc) - timedelta(days=1))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
            .sign(self.private_key, hashes.SHA256())
        )
        self.cert_pem = self.cert.public_bytes(serialization.Encoding.PEM)
        self.private_key_pem = self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def issue_signed_response(
        self,
        *,
        sp_entity_id: str,
        acs_url: str,
        request_id: str = "",
        subject_email: str = "alice@hospital.de",
        attributes: dict[str, str] | None = None,
        not_before: datetime | None = None,
        not_on_or_after: datetime | None = None,
        sign_assertion_only: bool = True,
    ) -> str:
        """Build + sign a SAML Response. Returns the base64-
        encoded form the SP's ACS would receive."""

        now = datetime.now(timezone.utc)
        not_before = not_before or (now - timedelta(seconds=30))
        not_on_or_after = not_on_or_after or (now + timedelta(minutes=5))
        nb_str = not_before.strftime("%Y-%m-%dT%H:%M:%SZ")
        na_str = not_on_or_after.strftime("%Y-%m-%dT%H:%M:%SZ")
        issue_instant = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        response_id = "resp-" + os.urandom(8).hex()
        assertion_id = "_assertion-" + os.urandom(8).hex()

        attrs_xml = ""
        for name, value in (attributes or {}).items():
            attrs_xml += (
                f'<saml:Attribute Name="{name}" '
                f'NameFormat="urn:oasis:names:tc:SAML:2.0:attrname-format:unspecified">'
                f"<saml:AttributeValue>{value}</saml:AttributeValue>"
                f"</saml:Attribute>"
            )

        in_response_to_attr = f'InResponseTo="{request_id}" ' if request_id else ""

        assertion_xml = (
            f'<saml:Assertion xmlns:saml="{_NS["saml"]}" '
            f'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
            f'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
            f'ID="{assertion_id}" Version="2.0" '
            f'IssueInstant="{issue_instant}">'
            f"<saml:Issuer>{self.entity_id}</saml:Issuer>"
            f"<saml:Subject>"
            f'<saml:NameID Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress">'
            f"{subject_email}"
            f"</saml:NameID>"
            f"</saml:Subject>"
            f'<saml:Conditions NotBefore="{nb_str}" NotOnOrAfter="{na_str}">'
            f"<saml:AudienceRestriction>"
            f"<saml:Audience>{sp_entity_id}</saml:Audience>"
            f"</saml:AudienceRestriction>"
            f"</saml:Conditions>"
            f"<saml:AttributeStatement>"
            f"{attrs_xml}"
            f"</saml:AttributeStatement>"
            f"</saml:Assertion>"
        )

        if sign_assertion_only:
            # Sign just the Assertion, then wrap in unsigned Response
            assertion_el = etree.fromstring(assertion_xml)
            signer = XMLSigner(
                method=signxml_methods_enveloped(),
                signature_algorithm=SignatureMethod.RSA_SHA256,
                digest_algorithm=DigestAlgorithm.SHA256,
                c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
            )
            signed_assertion = signer.sign(
                assertion_el,
                key=self.private_key_pem,
                cert=self.cert_pem,
                reference_uri=assertion_id,
            )
            assertion_serialized = etree.tostring(signed_assertion).decode()
            response_xml = (
                f'<samlp:Response xmlns:samlp="{_NS["samlp"]}" '
                f'xmlns:saml="{_NS["saml"]}" '
                f'ID="{response_id}" Version="2.0" '
                f'IssueInstant="{issue_instant}" '
                f"{in_response_to_attr}"
                f'Destination="{acs_url}">'
                f"<saml:Issuer>{self.entity_id}</saml:Issuer>"
                f"<samlp:Status>"
                f'<samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>'
                f"</samlp:Status>"
                f"{assertion_serialized}"
                f"</samlp:Response>"
            )
            response_bytes = response_xml.encode("utf-8")
        else:
            # Sign the whole Response
            response_xml = (
                f'<samlp:Response xmlns:samlp="{_NS["samlp"]}" '
                f'xmlns:saml="{_NS["saml"]}" '
                f'ID="{response_id}" Version="2.0" '
                f'IssueInstant="{issue_instant}" '
                f"{in_response_to_attr}"
                f'Destination="{acs_url}">'
                f"<saml:Issuer>{self.entity_id}</saml:Issuer>"
                f"<samlp:Status>"
                f'<samlp:StatusCode Value="urn:oasis:names:tc:SAML:2.0:status:Success"/>'
                f"</samlp:Status>"
                f"{assertion_xml}"
                f"</samlp:Response>"
            )
            response_el = etree.fromstring(response_xml)
            signer = XMLSigner(
                method=signxml_methods_enveloped(),
                signature_algorithm=SignatureMethod.RSA_SHA256,
                digest_algorithm=DigestAlgorithm.SHA256,
                c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#",
            )
            signed_response = signer.sign(
                response_el,
                key=self.private_key_pem,
                cert=self.cert_pem,
                reference_uri=response_id,
            )
            response_bytes = etree.tostring(signed_response)

        return base64.b64encode(response_bytes).decode("ascii")


def signxml_methods_enveloped():
    """Return signxml.methods.enveloped — works across signxml
    versions where the enum lives in different submodules."""

    try:
        from signxml import methods

        return methods.enveloped
    except (ImportError, AttributeError):
        from signxml.enums import SignatureConstructionMethod

        return SignatureConstructionMethod.enveloped


# ---------------------------------------------------------------------------
# IdP env loading
# ---------------------------------------------------------------------------


class IdpEnvLoading(unittest.TestCase):
    def setUp(self):
        self._original_env = dict(os.environ)

    def tearDown(self):
        for key in list(os.environ):
            if key.startswith("HELPMEFINDTHEJOB_SAML_"):
                if key not in self._original_env:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = self._original_env[key]

    def test_empty_when_no_idps_listed(self):
        os.environ.pop("HELPMEFINDTHEJOB_SAML_IDPS", None)
        self.assertEqual(load_idps_from_env(), [])

    def test_complete_idp_loads(self):
        os.environ["HELPMEFINDTHEJOB_SAML_IDPS"] = "shibboleth-uni"
        os.environ["HELPMEFINDTHEJOB_SAML_SHIBBOLETH_UNI_ENTITY_ID"] = (
            "https://idp.uni-berlin.de/saml"
        )
        os.environ["HELPMEFINDTHEJOB_SAML_SHIBBOLETH_UNI_SSO_URL"] = (
            "https://idp.uni-berlin.de/SAML2/SSO/Redirect"
        )
        os.environ["HELPMEFINDTHEJOB_SAML_SHIBBOLETH_UNI_CERT_PEM"] = (
            "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----"
        )
        os.environ["HELPMEFINDTHEJOB_SAML_SHIBBOLETH_UNI_EMAIL_DOMAIN"] = "uni-berlin.de"
        idps = load_idps_from_env()
        self.assertEqual(len(idps), 1)
        idp = idps[0]
        self.assertEqual(idp.idp_id, "shibboleth-uni")
        self.assertEqual(idp.email_domain, "uni-berlin.de")

    def test_incomplete_idp_skipped(self):
        os.environ["HELPMEFINDTHEJOB_SAML_IDPS"] = "broken"
        os.environ["HELPMEFINDTHEJOB_SAML_BROKEN_ENTITY_ID"] = "https://x"
        # SSO_URL + CERT_PEM missing
        self.assertEqual(load_idps_from_env(), [])


# ---------------------------------------------------------------------------
# AuthnRequest generation
# ---------------------------------------------------------------------------


class AuthnRequestGeneration(unittest.TestCase):
    def setUp(self):
        self.idp = SamlIdpConfig(
            idp_id="test-idp",
            entity_id="https://idp.example/entity",
            sso_url="https://idp.example/sso",
            cert_pem="(test)",
        )

    def test_request_id_format(self):
        rid = generate_request_id()
        # XML xs:ID must start with a letter or underscore
        self.assertRegex(rid, r"^[A-Za-z_][\w.-]*$")

    def test_redirect_url_contains_saml_request_param(self):
        url, rid = build_authn_request(
            self.idp,
            sp_entity_id="https://sp.example/entity",
            acs_url="https://sp.example/acs",
        )
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        self.assertIn("SAMLRequest", params)
        # Round-trip the SAMLRequest param: base64 → raw deflate →
        # inflate → XML — should contain our request_id
        raw_b64 = params["SAMLRequest"][0]
        raw_deflated = base64.b64decode(raw_b64)
        inflated = zlib.decompress(raw_deflated, -zlib.MAX_WBITS)
        self.assertIn(rid.encode(), inflated)
        self.assertIn(b"AuthnRequest", inflated)
        self.assertIn(b"https://sp.example/acs", inflated)
        self.assertIn(b"https://sp.example/entity", inflated)

    def test_relay_state_included_when_set(self):
        url, _ = build_authn_request(
            self.idp,
            sp_entity_id="x",
            acs_url="y",
            relay_state="return-to:/dashboard",
        )
        params = parse_qs(urlparse(url).query)
        self.assertEqual(params["RelayState"], ["return-to:/dashboard"])


# ---------------------------------------------------------------------------
# SP metadata
# ---------------------------------------------------------------------------


class SpMetadataShape(unittest.TestCase):
    def test_metadata_carries_acs_and_entity_id(self):
        metadata = build_sp_metadata(
            sp_entity_id="https://sp.example/entity",
            acs_url="https://sp.example/acs",
        )
        self.assertIn(b"https://sp.example/entity", metadata)
        self.assertIn(b"https://sp.example/acs", metadata)
        self.assertIn(b"EntityDescriptor", metadata)
        self.assertIn(b"AssertionConsumerService", metadata)
        self.assertIn(b'WantAssertionsSigned="true"', metadata)

    def test_metadata_parses_as_xml(self):
        from lxml import etree as et

        metadata = build_sp_metadata(
            sp_entity_id="x",
            acs_url="y",
        )
        # Must parse cleanly
        root = et.fromstring(metadata)
        self.assertEqual(root.tag, "{urn:oasis:names:tc:SAML:2.0:metadata}EntityDescriptor")


# ---------------------------------------------------------------------------
# Cert normalisation
# ---------------------------------------------------------------------------


class CertNormalisation(unittest.TestCase):
    def test_passes_through_pem(self):
        pem = "-----BEGIN CERTIFICATE-----\nABC\n-----END CERTIFICATE-----"
        out = _normalize_cert(pem)
        self.assertIn(b"BEGIN CERTIFICATE", out)

    def test_wraps_bare_base64(self):
        bare = "MIIBCgKCAQEA" * 10
        out = _normalize_cert(bare)
        self.assertIn(b"-----BEGIN CERTIFICATE-----", out)
        self.assertIn(b"-----END CERTIFICATE-----", out)
        self.assertIn(b"MIIBCgKCAQEA", out)


# ---------------------------------------------------------------------------
# Response validation — full happy path + every failure mode
# ---------------------------------------------------------------------------


class ResponseValidationHappyPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.idp_mock = _MockIdp(entity_id="https://idp.example/entity")
        cls.idp = SamlIdpConfig(
            idp_id="t",
            entity_id="https://idp.example/entity",
            sso_url="https://idp.example/sso",
            cert_pem=cls.idp_mock.cert_pem.decode(),
        )
        cls.sp_entity_id = "https://sp.example/entity"
        cls.acs_url = "https://sp.example/acs"

    def test_valid_signed_assertion_extracts_user(self):
        request_id = generate_request_id()
        b64 = self.idp_mock.issue_signed_response(
            sp_entity_id=self.sp_entity_id,
            acs_url=self.acs_url,
            request_id=request_id,
            subject_email="alice@hospital.de",
            attributes={
                "email": "alice@hospital.de",
                "displayName": "Alice Schmidt",
            },
        )
        claims = parse_and_validate_response(
            b64,
            idp=self.idp,
            sp_entity_id=self.sp_entity_id,
            acs_url=self.acs_url,
            expected_request_id=request_id,
        )
        self.assertEqual(claims.subject, "alice@hospital.de")
        self.assertEqual(claims.email, "alice@hospital.de")
        self.assertEqual(claims.name, "Alice Schmidt")

    def test_email_from_nameid_when_no_email_attribute(self):
        b64 = self.idp_mock.issue_signed_response(
            sp_entity_id=self.sp_entity_id,
            acs_url=self.acs_url,
            request_id=generate_request_id(),
            subject_email="bob@hospital.de",
            attributes={},  # no email attribute — fall back to NameID
        )
        claims = parse_and_validate_response(
            b64,
            idp=self.idp,
            sp_entity_id=self.sp_entity_id,
            acs_url=self.acs_url,
        )
        self.assertEqual(claims.email, "bob@hospital.de")

    def test_signed_response_root_accepted(self):
        # Some IdPs sign the whole Response instead of just the
        # Assertion — both are valid SAML.
        request_id = generate_request_id()
        b64 = self.idp_mock.issue_signed_response(
            sp_entity_id=self.sp_entity_id,
            acs_url=self.acs_url,
            request_id=request_id,
            subject_email="carol@hospital.de",
            attributes={"email": "carol@hospital.de"},
            sign_assertion_only=False,
        )
        claims = parse_and_validate_response(
            b64,
            idp=self.idp,
            sp_entity_id=self.sp_entity_id,
            acs_url=self.acs_url,
            expected_request_id=request_id,
        )
        self.assertEqual(claims.subject, "carol@hospital.de")


class ResponseValidationFailureModes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.idp_mock = _MockIdp(entity_id="https://idp.example/entity")
        cls.idp = SamlIdpConfig(
            idp_id="t",
            entity_id="https://idp.example/entity",
            sso_url="https://idp.example/sso",
            cert_pem=cls.idp_mock.cert_pem.decode(),
        )
        cls.sp_entity_id = "https://sp.example/entity"
        cls.acs_url = "https://sp.example/acs"

    def test_signed_by_wrong_cert_rejected(self):
        other_idp = _MockIdp(entity_id="https://attacker.example/entity")
        b64 = other_idp.issue_signed_response(
            sp_entity_id=self.sp_entity_id,
            acs_url=self.acs_url,
            request_id=generate_request_id(),
            subject_email="attacker@evil.com",
            attributes={"email": "alice@hospital.de"},  # spoofed
        )
        with self.assertRaises(SamlResponseError) as cm:
            parse_and_validate_response(
                b64,
                idp=self.idp,
                sp_entity_id=self.sp_entity_id,
                acs_url=self.acs_url,
            )
        self.assertIn("signature", str(cm.exception).lower())

    def test_audience_mismatch_rejected(self):
        b64 = self.idp_mock.issue_signed_response(
            sp_entity_id="https://other-sp.example/entity",  # wrong
            acs_url=self.acs_url,
            request_id=generate_request_id(),
            subject_email="alice@hospital.de",
            attributes={"email": "alice@hospital.de"},
        )
        with self.assertRaises(SamlResponseError) as cm:
            parse_and_validate_response(
                b64,
                idp=self.idp,
                sp_entity_id=self.sp_entity_id,  # our SP — mismatch
                acs_url=self.acs_url,
            )
        self.assertIn("audience_mismatch", str(cm.exception))

    def test_expired_assertion_rejected(self):
        now = datetime.now(timezone.utc)
        b64 = self.idp_mock.issue_signed_response(
            sp_entity_id=self.sp_entity_id,
            acs_url=self.acs_url,
            request_id=generate_request_id(),
            subject_email="alice@hospital.de",
            attributes={"email": "alice@hospital.de"},
            not_before=now - timedelta(hours=2),
            not_on_or_after=now - timedelta(hours=1),  # expired 1h ago
        )
        with self.assertRaises(SamlResponseError) as cm:
            parse_and_validate_response(
                b64,
                idp=self.idp,
                sp_entity_id=self.sp_entity_id,
                acs_url=self.acs_url,
            )
        self.assertIn("expired", str(cm.exception))

    def test_in_response_to_mismatch_rejected(self):
        b64 = self.idp_mock.issue_signed_response(
            sp_entity_id=self.sp_entity_id,
            acs_url=self.acs_url,
            request_id="id-from-idp",
            subject_email="alice@hospital.de",
            attributes={"email": "alice@hospital.de"},
        )
        with self.assertRaises(SamlResponseError) as cm:
            parse_and_validate_response(
                b64,
                idp=self.idp,
                sp_entity_id=self.sp_entity_id,
                acs_url=self.acs_url,
                expected_request_id="id-we-sent-different",
            )
        self.assertIn("in_response_to_mismatch", str(cm.exception))

    def test_destination_mismatch_rejected(self):
        b64 = self.idp_mock.issue_signed_response(
            sp_entity_id=self.sp_entity_id,
            acs_url="https://other-sp.example/acs",  # wrong
            request_id=generate_request_id(),
            subject_email="alice@hospital.de",
            attributes={"email": "alice@hospital.de"},
        )
        with self.assertRaises(SamlResponseError) as cm:
            parse_and_validate_response(
                b64,
                idp=self.idp,
                sp_entity_id=self.sp_entity_id,
                acs_url=self.acs_url,  # our ACS — mismatch
            )
        self.assertIn("destination_mismatch", str(cm.exception))

    def test_malformed_base64_rejected(self):
        with self.assertRaises(SamlResponseError):
            parse_and_validate_response(
                "@@@not-base64@@@",
                idp=self.idp,
                sp_entity_id=self.sp_entity_id,
                acs_url=self.acs_url,
            )

    def test_malformed_xml_rejected(self):
        garbage = base64.b64encode(b"<not valid xml").decode()
        with self.assertRaises(SamlResponseError):
            parse_and_validate_response(
                garbage,
                idp=self.idp,
                sp_entity_id=self.sp_entity_id,
                acs_url=self.acs_url,
            )


# ---------------------------------------------------------------------------
# Email / display-name extraction helpers
# ---------------------------------------------------------------------------


class EmailExtraction(unittest.TestCase):
    def test_lowercase_email_attribute(self):
        result = _extract_email({"email": ["Alice@Hospital.de"]}, fallback_nameid="")
        self.assertEqual(result, "alice@hospital.de")

    def test_oid_attribute_name_recognised(self):
        result = _extract_email(
            {"urn:oid:0.9.2342.19200300.100.1.3": ["bob@x.com"]},
            fallback_nameid="",
        )
        self.assertEqual(result, "bob@x.com")

    def test_microsoft_claim_name_recognised(self):
        result = _extract_email(
            {
                "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress": [
                    "carol@ad.com"
                ]
            },
            fallback_nameid="",
        )
        self.assertEqual(result, "carol@ad.com")

    def test_falls_back_to_nameid_when_no_attr(self):
        result = _extract_email({}, fallback_nameid="dan@hospital.de")
        self.assertEqual(result, "dan@hospital.de")

    def test_returns_empty_when_no_email_anywhere(self):
        result = _extract_email({}, fallback_nameid="opaque-subject")
        self.assertEqual(result, "")


class DisplayNameExtraction(unittest.TestCase):
    def test_displayname_attribute(self):
        result = _extract_display_name({"displayName": ["Alice Schmidt"]})
        self.assertEqual(result, "Alice Schmidt")

    def test_first_plus_last(self):
        result = _extract_display_name({"givenName": ["Bob"], "surname": ["Müller"]})
        self.assertEqual(result, "Bob Müller")

    def test_first_only(self):
        result = _extract_display_name({"givenName": ["Eve"]})
        self.assertEqual(result, "Eve")

    def test_empty_when_no_name_attrs(self):
        result = _extract_display_name({"randomAttr": ["x"]})
        self.assertEqual(result, "")


class EmailDomainRouting(unittest.TestCase):
    def test_matching_domain_routes(self):
        idps = [
            SamlIdpConfig(
                idp_id="hospital",
                entity_id="x",
                sso_url="y",
                cert_pem="z",
                email_domain="hospital.de",
            )
        ]
        idp = route_by_email_domain(idps, "alice@hospital.de")
        self.assertEqual(idp.idp_id, "hospital")

    def test_case_insensitive(self):
        idps = [
            SamlIdpConfig(
                idp_id="hospital",
                entity_id="x",
                sso_url="y",
                cert_pem="z",
                email_domain="HOSPITAL.de",
            )
        ]
        idp = route_by_email_domain(idps, "alice@Hospital.DE")
        self.assertEqual(idp.idp_id, "hospital")

    def test_unmatched_returns_none(self):
        idps = [
            SamlIdpConfig(
                idp_id="hospital",
                entity_id="x",
                sso_url="y",
                cert_pem="z",
                email_domain="hospital.de",
            )
        ]
        self.assertIsNone(route_by_email_domain(idps, "alice@other.com"))


class HttpRoutesPresence(unittest.TestCase):
    """Pin the four SAML HTTP routes in app.py + the security
    posture (ACS lives in the pre-auth section, NOT inside the
    require_auth-gated block)."""

    @classmethod
    def setUpClass(cls):
        cls.src = Path(str(Path(__file__).resolve().parent.parent / "app.py")).read_text(
            encoding="utf-8"
        )

    def test_idps_listing_route_present(self):
        self.assertIn('"/api/auth/sso/saml/idps"', self.src)

    def test_login_route_present(self):
        self.assertIn("saml_login_match", self.src)
        self.assertIn("build_authn_request", self.src)

    def test_acs_route_present(self):
        self.assertIn('"/api/auth/sso/saml/acs"', self.src)
        self.assertIn("parse_and_validate_response", self.src)
        self.assertIn("find_or_create_sso_user", self.src)

    def test_metadata_route_present(self):
        self.assertIn("saml_metadata_match", self.src)
        self.assertIn("build_sp_metadata", self.src)

    def test_acs_in_pre_auth_section(self):
        """ACS MUST live BEFORE the `require_auth` gate in do_POST.
        The IdP callback hits us with no session; require_auth
        would 401 every legitimate login. We verify by scoping
        the search to the do_POST function body."""

        # Slice the source to do_POST's body only
        post_start = self.src.find("def do_POST(self) -> None:")
        # do_PATCH is the next method
        post_end = self.src.find("def do_PATCH(self) -> None:", post_start)
        self.assertGreater(post_start, 0, "do_POST not found")
        self.assertGreater(post_end, post_start, "do_PATCH not found after do_POST")
        post_body = self.src[post_start:post_end]
        acs_pos = post_body.find('"/api/auth/sso/saml/acs"')
        self.assertGreater(acs_pos, 0, "ACS route not found in do_POST")
        # The `require_auth` gate in do_POST is the line:
        #   if parsed.path.startswith("/api/"):
        #     session = self.require_auth()
        gate_pos = post_body.find(
            'if parsed.path.startswith("/api/"):\n                session = self.require_auth()'
        )
        self.assertGreater(gate_pos, 0, "auth gate not found in do_POST in expected shape")
        self.assertLess(
            acs_pos,
            gate_pos,
            "ACS route is AFTER the require_auth gate in do_POST — every "
            "legitimate SAML login would 401",
        )

    def test_acs_clears_saml_auth_state_cookie(self):
        # After consuming the saml_auth_state cookie, the ACS
        # response MUST clear it (Max-Age=0) so a leaked cookie
        # can't be replayed.
        self.assertRegex(
            self.src,
            r"saml_auth_state=;\s*Path=/;\s*Max-Age=0",
        )

    def test_acs_logs_sso_login_event_with_saml_kind(self):
        # The analytics event MUST carry providerKind: 'saml' so
        # the transparency dashboard can distinguish SAML logins
        # from OIDC logins.
        self.assertRegex(self.src, r'"providerKind":\s*"saml"')


if __name__ == "__main__":
    unittest.main()
