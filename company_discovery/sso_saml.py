# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""SAML 2.0 service-provider implementation (13-plan item 12/13,
gap #21 — completes the SSO/SAML pair with the OIDC half in
sso_oidc.py).

Why SAML matters: government, healthcare, and many established
NGOs run on SAML-only IdPs (Active Directory Federation
Services, Shibboleth, on-prem Keycloak in SAML mode). OIDC
alone doesn't reach those deployers. This module mirrors the
OIDC surface so the SAME ``AuthStore.find_or_create_sso_user``
JIT-provisioning path serves both protocols.

Bindings supported:

- **AuthnRequest (SP → IdP): HTTP-Redirect** — the request is
  DEFLATE-compressed + base64-encoded + sent as a query
  parameter. The IdP redirects the user-agent to its login
  page; on success they POST the response back.
- **Response (IdP → SP): HTTP-POST** — the IdP renders an
  auto-submitting HTML form that POSTs ``SAMLResponse`` (base64-
  encoded signed XML) to our ACS endpoint.

Validation chain on Response receipt:

1. **XML signature verification** (XML-DSig via ``signxml``).
   Either the Response itself OR the embedded Assertion MUST be
   signed by a cert whose public key matches the IdP config.
2. **Conditions/Audience**: ``<Audience>`` MUST equal our SP
   entity ID. Defends against IdP misconfiguration spilling
   another SP's user into our session.
3. **Conditions/NotBefore + NotOnOrAfter**: a small clock-skew
   window is tolerated; otherwise expired assertions are
   rejected.
4. **InResponseTo**: when present, MUST match the
   AuthnRequest id we sent. Defends against unsolicited /
   forged assertions.
5. **Destination**: MUST match our ACS URL. Defends against
   relay attacks where a leaked assertion is sent to a
   different SP.
6. **NameID + attribute statement**: pull ``email`` from
   common attribute names; fall back to NameID. Subject is
   the long-term stable identity used for SSO linkage in
   ``sso_links`` (same table OIDC populates with
   ``provider_kind='saml'``).

Hard requirements:

- The IdP MUST provide a PEM-formatted signing cert at
  config time (in env var). We do NOT fetch it dynamically
  from the IdP's metadata URL because supply-chain risk
  (an MITM serving a fake metadata document would let an
  attacker swap our trust anchor). Operators paste the cert
  out-of-band.
- The signature algorithm is the IdP's choice; we accept
  the SHA-256 family + reject SHA-1 (deprecated; collision-
  vulnerable). signxml's default deny-list covers this.
"""

from __future__ import annotations

import base64
import logging
import os
import secrets
import urllib.parse
import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from lxml import etree
from signxml import XMLVerifier
from signxml.exceptions import InvalidSignature


_log = logging.getLogger(__name__)


_ENV_PREFIX = "HELPMEFINDTHEJOB_SAML_"
_IDPS_LIST_ENV = "HELPMEFINDTHEJOB_SAML_IDPS"


# SAML 2.0 namespaces — used for lxml XPath queries.
_NS = {
    "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
    "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}


# Attribute names commonly used by IdPs to carry the user's
# email. SAML doesn't standardise on one — different products
# use different conventions, so we accept the union.
_EMAIL_ATTRIBUTE_NAMES: frozenset[str] = frozenset(
    {
        "email",
        "emailaddress",
        "mail",
        "urn:oid:0.9.2342.19200300.100.1.3",
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress",
        "http://schemas.xmlsoap.org/claims/emailaddress",
    }
)


class SamlError(RuntimeError):
    """Base error for SAML operations. HTTP layer maps to 5xx
    unless a more specific subclass is raised."""


class SamlConfigError(SamlError):
    """IdP config missing or malformed."""


class SamlResponseError(SamlError):
    """The IdP's SAML Response failed validation. Could be
    signature, audience, expiry, InResponseTo, or destination
    mismatch — the message names the specific failure."""


@dataclass(frozen=True)
class SamlIdpConfig:
    """Operator-provided config for one SAML IdP.

    - ``idp_id`` is our internal key (e.g., ``shibboleth-uni``).
      Used in routes: ``/api/auth/sso/saml/<idp_id>/login``.
    - ``entity_id`` is the IdP's SAML EntityID — used to set
      ``Issuer`` on AuthnRequests + validate the same on
      Response.
    - ``sso_url`` is the SingleSignOnService endpoint where
      we send AuthnRequests (HTTP-Redirect binding).
    - ``cert_pem`` is the IdP's signing certificate, PEM-
      formatted. Pasted by the operator out-of-band; we
      validate every Response signature against this.
    - ``email_domain`` (optional) enables auto-routing
      mirroring the OIDC behaviour.
    """

    idp_id: str
    entity_id: str
    sso_url: str
    cert_pem: str
    email_domain: str = ""


def load_idps_from_env() -> list[SamlIdpConfig]:
    """Read every SAML IdP declared in env vars. Mirror of
    ``sso_oidc.load_providers_from_env``."""

    list_raw = os.environ.get(_IDPS_LIST_ENV, "").strip()
    if not list_raw:
        return []
    idp_ids = [p.strip() for p in list_raw.split(",") if p.strip()]
    configs: list[SamlIdpConfig] = []
    for idp_id in idp_ids:
        env_key = idp_id.upper().replace("-", "_")
        entity_id = os.environ.get(
            f"{_ENV_PREFIX}{env_key}_ENTITY_ID", ""
        ).strip()
        sso_url = os.environ.get(f"{_ENV_PREFIX}{env_key}_SSO_URL", "").strip()
        cert_pem = os.environ.get(f"{_ENV_PREFIX}{env_key}_CERT_PEM", "").strip()
        email_domain = os.environ.get(
            f"{_ENV_PREFIX}{env_key}_EMAIL_DOMAIN", ""
        ).strip()
        missing = []
        if not entity_id:
            missing.append("ENTITY_ID")
        if not sso_url:
            missing.append("SSO_URL")
        if not cert_pem:
            missing.append("CERT_PEM")
        if missing:
            _log.warning(
                "SAML IdP %r is in %s but missing env vars: %s — skipping",
                idp_id,
                _IDPS_LIST_ENV,
                ", ".join(missing),
            )
            continue
        configs.append(
            SamlIdpConfig(
                idp_id=idp_id,
                entity_id=entity_id,
                sso_url=sso_url,
                cert_pem=cert_pem,
                email_domain=email_domain,
            )
        )
    return configs


def _now_xs_datetime() -> str:
    """Current UTC time formatted per XML-Schema dateTime
    (the format SAML expects in IssueInstant)."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_request_id() -> str:
    """SAML IDs start with a letter (XML xs:ID rule)."""

    return "id-" + secrets.token_hex(16)


def build_authn_request(
    idp: SamlIdpConfig,
    *,
    sp_entity_id: str,
    acs_url: str,
    request_id: str | None = None,
    relay_state: str = "",
) -> tuple[str, str]:
    """Build a SAML AuthnRequest for the HTTP-Redirect binding.

    Returns ``(redirect_url, request_id)``. The HTTP layer
    redirects the user-agent to ``redirect_url`` and stashes
    ``request_id`` so the callback can verify ``InResponseTo``.

    The AuthnRequest is NOT signed — most IdPs accept unsigned
    AuthnRequests, and adding SP-side signing is a deployment-
    specific operator choice (signed AuthnRequests require the
    IdP to know the SP's signing cert). Phase 2 can add SP
    signing as an opt-in via an env var.
    """

    rid = request_id or generate_request_id()
    issue_instant = _now_xs_datetime()

    # Build the request XML. We compose it as a string (not via
    # lxml's Element API) because the DEFLATE-encoded form is
    # tiny + the IdP's parser tolerates either.
    xml = (
        f'<samlp:AuthnRequest xmlns:samlp="{_NS["samlp"]}" '
        f'xmlns:saml="{_NS["saml"]}" '
        f'ID="{rid}" Version="2.0" '
        f'IssueInstant="{issue_instant}" '
        f'Destination="{idp.sso_url}" '
        f'AssertionConsumerServiceURL="{acs_url}" '
        f'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">'
        f"<saml:Issuer>{sp_entity_id}</saml:Issuer>"
        f'<samlp:NameIDPolicy '
        f'Format="urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress" '
        f'AllowCreate="true"/>'
        f"</samlp:AuthnRequest>"
    )
    # HTTP-Redirect binding: DEFLATE (raw, no zlib headers) +
    # base64 + URL-encode. RFC 2616 / SAML core spec.
    deflated = zlib.compress(xml.encode("utf-8"))[2:-4]
    encoded = base64.b64encode(deflated).decode("ascii")
    params = {"SAMLRequest": encoded}
    if relay_state:
        params["RelayState"] = relay_state
    query = urllib.parse.urlencode(params)
    sep = "&" if "?" in idp.sso_url else "?"
    return f"{idp.sso_url}{sep}{query}", rid


@dataclass(frozen=True)
class SamlUserClaims:
    """Validated user info pulled from a SAML assertion."""

    subject: str
    email: str
    name: str
    attributes: dict[str, list[str]]


def _normalize_cert(cert_pem: str) -> bytes:
    """Some operators paste the cert without BEGIN/END markers
    or with funny whitespace. Normalise so signxml accepts it."""

    stripped = cert_pem.strip()
    if "BEGIN CERTIFICATE" not in stripped:
        # Bare base64 — wrap with markers
        body = "".join(stripped.split())
        # Re-wrap to 64-char lines per PEM convention
        lines = [body[i : i + 64] for i in range(0, len(body), 64)]
        stripped = (
            "-----BEGIN CERTIFICATE-----\n"
            + "\n".join(lines)
            + "\n-----END CERTIFICATE-----"
        )
    return stripped.encode("utf-8")


def parse_and_validate_response(
    saml_response_b64: str,
    *,
    idp: SamlIdpConfig,
    sp_entity_id: str,
    acs_url: str,
    expected_request_id: str | None = None,
    clock_skew_seconds: int = 60,
) -> SamlUserClaims:
    """Verify a SAML Response delivered to the SP's ACS via
    HTTP-POST binding.

    The validation chain (any failure raises SamlResponseError
    with a structured code):

    1. base64-decode + XML-parse
    2. XML signature verification (Response or Assertion signed
       by the IdP cert)
    3. Destination matches our ACS URL
    4. Issuer matches the IdP's entity_id
    5. InResponseTo matches the AuthnRequest id we sent
    6. Conditions/Audience matches our SP entity ID
    7. Conditions/NotBefore <= now <= NotOnOrAfter (± skew)
    8. NameID + attribute statement provide email + subject
    """

    try:
        raw_xml = base64.b64decode(saml_response_b64, validate=False)
    except Exception as err:  # noqa: BLE001 - b64 decode can raise binascii.Error
        raise SamlResponseError(f"response_b64_decode_failed:{err}") from err
    try:
        root = etree.fromstring(raw_xml)
    except etree.XMLSyntaxError as err:
        raise SamlResponseError(f"response_xml_parse_failed:{err}") from err

    # ---- Step 1: signature verification ---------------------------------
    # signxml.XMLVerifier returns the verified subtree (or raises). We
    # accept either a signed Response root OR a signed embedded
    # Assertion — both are valid SAML.
    cert_bytes = _normalize_cert(idp.cert_pem)
    try:
        verifier = XMLVerifier()
        verified_data = verifier.verify(root, x509_cert=cert_bytes)
        verified_root = verified_data.signed_xml
    except InvalidSignature as err:
        raise SamlResponseError(f"signature_invalid:{err}") from err
    except Exception as err:  # noqa: BLE001 - signxml can raise various error types
        raise SamlResponseError(f"signature_verification_failed:{err}") from err

    # signxml returns the signed subtree. Whether the IdP signed the
    # whole Response or just the Assertion, we use the original root
    # for subsequent assertions about ID-based fields — but ONLY look
    # at the assertion that was actually inside the signed subtree.
    # The "signature wrapping attack" defence: never trust an
    # assertion that lives OUTSIDE the verified subtree.
    if verified_root.tag.endswith("}Response"):
        assertion = verified_root.find("saml:Assertion", _NS)
    elif verified_root.tag.endswith("}Assertion"):
        assertion = verified_root
    else:
        raise SamlResponseError("verified_subtree_not_response_or_assertion")
    if assertion is None:
        raise SamlResponseError("response_missing_assertion")

    # ---- Step 2: Destination ----
    destination = root.get("Destination", "")
    if destination and destination != acs_url:
        raise SamlResponseError(
            f"destination_mismatch:got={destination!r} expected={acs_url!r}"
        )

    # ---- Step 3: Issuer matches IdP ----
    issuer_el = assertion.find("saml:Issuer", _NS)
    if issuer_el is None or (issuer_el.text or "") != idp.entity_id:
        actual = issuer_el.text if issuer_el is not None else None
        raise SamlResponseError(
            f"issuer_mismatch:got={actual!r} expected={idp.entity_id!r}"
        )

    # ---- Step 4: InResponseTo ----
    if expected_request_id:
        in_response_to = root.get("InResponseTo", "")
        if in_response_to != expected_request_id:
            raise SamlResponseError(
                f"in_response_to_mismatch:got={in_response_to!r} "
                f"expected={expected_request_id!r}"
            )

    # ---- Step 5: Conditions/Audience ----
    conditions = assertion.find("saml:Conditions", _NS)
    if conditions is None:
        raise SamlResponseError("assertion_missing_conditions")
    audiences = [
        (e.text or "").strip()
        for e in conditions.findall(
            "saml:AudienceRestriction/saml:Audience", _NS
        )
    ]
    if sp_entity_id not in audiences:
        raise SamlResponseError(
            f"audience_mismatch:got={audiences!r} expected={sp_entity_id!r}"
        )

    # ---- Step 6: Conditions/NotBefore + NotOnOrAfter ----
    now = datetime.now(timezone.utc)
    not_before_str = conditions.get("NotBefore", "")
    not_on_or_after_str = conditions.get("NotOnOrAfter", "")
    if not_before_str:
        try:
            not_before = datetime.strptime(
                not_before_str, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            # Some IdPs include fractional seconds; try alt format
            try:
                not_before = datetime.strptime(
                    not_before_str, "%Y-%m-%dT%H:%M:%S.%fZ"
                ).replace(tzinfo=timezone.utc)
            except ValueError as err:
                raise SamlResponseError(
                    f"not_before_parse_failed:{not_before_str}"
                ) from err
        if now < not_before - _delta(clock_skew_seconds):
            raise SamlResponseError(
                f"assertion_not_yet_valid:not_before={not_before_str}"
            )
    if not_on_or_after_str:
        try:
            not_after = datetime.strptime(
                not_on_or_after_str, "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            try:
                not_after = datetime.strptime(
                    not_on_or_after_str, "%Y-%m-%dT%H:%M:%S.%fZ"
                ).replace(tzinfo=timezone.utc)
            except ValueError as err:
                raise SamlResponseError(
                    f"not_on_or_after_parse_failed:{not_on_or_after_str}"
                ) from err
        if now > not_after + _delta(clock_skew_seconds):
            raise SamlResponseError(
                f"assertion_expired:not_on_or_after={not_on_or_after_str}"
            )

    # ---- Step 7: extract NameID + attributes ----
    subject_el = assertion.find("saml:Subject/saml:NameID", _NS)
    if subject_el is None or not (subject_el.text or "").strip():
        raise SamlResponseError("missing_nameid")
    name_id = (subject_el.text or "").strip()

    attributes: dict[str, list[str]] = {}
    for attr in assertion.findall(
        "saml:AttributeStatement/saml:Attribute", _NS
    ):
        attr_name = attr.get("Name", "")
        values = [
            (v.text or "").strip()
            for v in attr.findall("saml:AttributeValue", _NS)
            if (v.text or "").strip()
        ]
        if attr_name and values:
            attributes[attr_name] = values

    email = _extract_email(attributes, fallback_nameid=name_id)
    if not email:
        raise SamlResponseError("missing_email")

    display_name = _extract_display_name(attributes)

    return SamlUserClaims(
        subject=name_id,
        email=email,
        name=display_name,
        attributes=attributes,
    )


def _delta(seconds: int) -> timedelta:
    """Tiny readability shim for ``timedelta(seconds=N)``."""

    return timedelta(seconds=seconds)


def _extract_email(
    attributes: dict[str, list[str]], *, fallback_nameid: str
) -> str:
    """Pull the email from common attribute names. Falls back
    to NameID if it looks like an email."""

    for name, values in attributes.items():
        if name.lower() in _EMAIL_ATTRIBUTE_NAMES:
            for v in values:
                if "@" in v:
                    return v.lower()
    if "@" in fallback_nameid:
        return fallback_nameid.lower()
    return ""


def _extract_display_name(attributes: dict[str, list[str]]) -> str:
    """Pull a display name. Tries common attribute names; returns
    "" if none found."""

    for name in (
        "displayName",
        "name",
        "cn",
        "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/name",
    ):
        for attr_name, values in attributes.items():
            if attr_name.lower() == name.lower() and values:
                return values[0]
    # First+Last fallback
    first = ""
    last = ""
    for attr_name, values in attributes.items():
        lc = attr_name.lower()
        if lc in {"givenname", "firstname"} and values:
            first = values[0]
        if lc in {"surname", "lastname", "sn"} and values:
            last = values[0]
    if first or last:
        return (first + " " + last).strip()
    return ""


def build_sp_metadata(
    *, sp_entity_id: str, acs_url: str, sp_name: str = "Helpmefindthejob"
) -> bytes:
    """Generate SAML SP metadata XML for IdP registration.

    The operator hands this URL to the IdP admin so they can
    register us as a Service Provider. Returns bytes so the
    HTTP layer can serve it as ``application/samlmetadata+xml``.
    """

    now = _now_xs_datetime()
    xml = (
        f'<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata" '
        f'entityID="{sp_entity_id}" validUntil="2099-01-01T00:00:00Z">'
        f"<SPSSODescriptor "
        f'AuthnRequestsSigned="false" WantAssertionsSigned="true" '
        f'protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">'
        f"<NameIDFormat>urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress</NameIDFormat>"
        f"<AssertionConsumerService "
        f'Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" '
        f'Location="{acs_url}" index="0" isDefault="true"/>'
        f"</SPSSODescriptor>"
        f"<Organization>"
        f"<OrganizationName xml:lang=\"en\">{sp_name}</OrganizationName>"
        f"<OrganizationDisplayName xml:lang=\"en\">{sp_name}</OrganizationDisplayName>"
        f"<OrganizationURL xml:lang=\"en\">https://helpmefindthejob.org</OrganizationURL>"
        f"</Organization>"
        f"</EntityDescriptor>"
    )
    return xml.encode("utf-8")


def route_by_email_domain(
    idps: list[SamlIdpConfig], email: str
) -> SamlIdpConfig | None:
    """Find the IdP configured for an email's domain. Same
    pattern as ``sso_oidc.route_by_email_domain``."""

    if not email or "@" not in email:
        return None
    domain = email.split("@", 1)[1].lower()
    for idp in idps:
        if idp.email_domain and idp.email_domain.lower() == domain:
            return idp
    return None
