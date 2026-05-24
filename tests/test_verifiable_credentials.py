# Copyright (c) 2026 Helpmefindthejob contributors
# SPDX-License-Identifier: Apache-2.0
"""4-week plan W2 D10: Verifiable Credentials contract tests
(invariant 8).

Pins:

1. Roundtrip — sign + verify = True
2. Tamper detection — modify any field → verify fails
3. Canonicalisation — same content → same proofValue
4. Key persistence — second load returns the same key (file
   on disk is the source of truth)
5. Unknown issuer — verify returns unknown_issuer, never crashes
6. Malformed VC — every field combination produces a useful
   structured error, never an exception
7. Cross-agent — VC issued by Anerkennung agent verifies via
   the shared registry; tamper does not
8. DID document — exported document carries the right verification
   method
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from mesh.verifiable_credentials import (
    CRYPTOSUITE,
    PROOF_PURPOSE,
    PROOF_TYPE,
    Ed25519Signer,
    IssuerRecord,
    IssuerRegistry,
    VerificationResult,
    build_did_document,
    canonical_json,
    verify_credential,
)


def _make_unsigned_vc(
    subject_id: str = "did:web:user.example:abc",
    issuer: str = "did:web:test-issuer.example.com",
) -> dict:
    return {
        "@context": [
            "https://www.w3.org/ns/credentials/v2",
            "https://helpmefindthejob.org/vc/anerkennung/v1",
        ],
        "id": "urn:uuid:test-vc-1",
        "type": ["VerifiableCredential", "AnerkennungCredential"],
        "issuer": issuer,
        "validFrom": "2026-05-21T00:00:00+00:00",
        "credentialSubject": {
            "id": subject_id,
            "anerkennungPathway": "pflege_drittstaaten",
            "decision": "issued",
            "issuingAuthority": "Anerkennungsbehörde Brandenburg",
            "legalBasis": "§17 BQFG",
            "missingRequirements": [],
            "estimatedCompletionMonths": 6,
        },
    }


class CanonicalJsonContract(unittest.TestCase):
    def test_sorts_keys_at_every_level(self):
        a = {"b": 2, "a": 1, "nested": {"y": 2, "x": 1}}
        b = {"nested": {"x": 1, "y": 2}, "a": 1, "b": 2}
        self.assertEqual(canonical_json(a), canonical_json(b))

    def test_no_whitespace(self):
        out = canonical_json({"a": 1, "b": 2}).decode("utf-8")
        self.assertNotIn(" ", out)
        self.assertNotIn("\n", out)

    def test_unicode_preserved(self):
        out = canonical_json({"name": "Aïcha"}).decode("utf-8")
        self.assertIn("Aïcha", out)

    def test_floats_serialise_consistently(self):
        # Same float content → same canonical output
        self.assertEqual(canonical_json({"v": 1.5}), canonical_json({"v": 1.5}))


class SignerPersistence(unittest.TestCase):
    def test_keypair_generated_on_first_call(self):
        with TemporaryDirectory() as tmp:
            key_path = Path(tmp) / "key.json"
            signer = Ed25519Signer.from_file_or_create(
                key_path, signer_did="did:web:test"
            )
            self.assertTrue(key_path.exists())
            blob = json.loads(key_path.read_text(encoding="utf-8"))
            self.assertEqual(blob["alg"], "Ed25519")
            self.assertTrue(blob["publicKeyMultibase"].startswith("z"))
            self.assertIn("BEGIN PRIVATE KEY", blob["privateKeyPkcs8Pem"])

    def test_second_load_returns_same_public_key(self):
        with TemporaryDirectory() as tmp:
            key_path = Path(tmp) / "key.json"
            s1 = Ed25519Signer.from_file_or_create(key_path, signer_did="did:web:test")
            s2 = Ed25519Signer.from_file_or_create(key_path, signer_did="did:web:test")
            self.assertEqual(s1.public_key_multibase(), s2.public_key_multibase())

    def test_key_file_permissions_locked_down(self):
        with TemporaryDirectory() as tmp:
            key_path = Path(tmp) / "key.json"
            Ed25519Signer.from_file_or_create(key_path, signer_did="did:web:test")
            mode = key_path.stat().st_mode & 0o777
            # On POSIX expect 0o600; allow more-restrictive too
            self.assertIn(mode, (0o600, 0o400), f"got mode {oct(mode)}")


class SignVerifyRoundtrip(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        key_path = Path(self.tmp.name) / "key.json"
        self.signer_did = "did:web:test-issuer.example.com"
        self.signer = Ed25519Signer.from_file_or_create(
            key_path, signer_did=self.signer_did
        )
        self.registry = IssuerRegistry()
        self.registry.register(
            IssuerRecord(
                issuer_did=self.signer.signer_did,
                public_key_multibase=self.signer.public_key_multibase(),
            )
        )

    def _make_vc(self) -> dict:
        return _make_unsigned_vc(issuer=self.signer_did)

    def test_roundtrip_valid(self):
        signed = self.signer.sign_credential(self._make_vc())
        result = verify_credential(signed, registry=self.registry)
        self.assertTrue(result.valid, f"expected valid, got: {result}")
        self.assertEqual(result.reason, "ok")
        self.assertEqual(result.signer_did, self.signer_did)

    def test_proof_has_required_fields(self):
        vc = self._make_vc()
        signed = self.signer.sign_credential(vc)
        proof = signed["proof"]
        self.assertEqual(proof["type"], PROOF_TYPE)
        self.assertEqual(proof["cryptosuite"], CRYPTOSUITE)
        self.assertEqual(proof["proofPurpose"], PROOF_PURPOSE)
        self.assertTrue(proof["proofValue"].startswith("z"))
        self.assertIn("created", proof)

    def test_sign_does_not_mutate_input(self):
        vc = self._make_vc()
        original = json.dumps(vc, sort_keys=True)
        self.signer.sign_credential(vc)
        self.assertEqual(json.dumps(vc, sort_keys=True), original)

    def test_double_signing_rejected(self):
        vc = self._make_vc()
        signed = self.signer.sign_credential(vc)
        with self.assertRaises(ValueError):
            self.signer.sign_credential(signed)

    def test_tamper_with_subject_breaks_signature(self):
        signed = self.signer.sign_credential(self._make_vc())
        # Tamper: flip the decision
        signed["credentialSubject"]["decision"] = "denied"
        result = verify_credential(signed, registry=self.registry)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "signature_mismatch")

    def test_tamper_with_issuer_breaks_signature(self):
        signed = self.signer.sign_credential(self._make_vc())
        signed["issuer"] = "did:web:imposter.example.com"
        result = verify_credential(signed, registry=self.registry)
        self.assertFalse(result.valid)
        # Either unknown_issuer (if registry doesn't have imposter)
        # or signature_mismatch (if it does). For this test the
        # imposter is unregistered.
        self.assertEqual(result.reason, "unknown_issuer")

    def test_tamper_with_proof_value_breaks_signature(self):
        signed = self.signer.sign_credential(self._make_vc())
        # Flip one byte in the proofValue (after the 'z' multibase prefix)
        old_pv = signed["proof"]["proofValue"]
        signed["proof"]["proofValue"] = old_pv[:2] + ("A" if old_pv[2] != "A" else "B") + old_pv[3:]
        result = verify_credential(signed, registry=self.registry)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "signature_mismatch")

    def test_same_content_produces_signature_verifiable_against_same_key(self):
        # Note: Ed25519 IS deterministic per the RFC — same input, same key
        # produces the same signature. But our signing includes a
        # 'created' timestamp in the proof scaffold which changes per
        # call. So we test the property differently: verify two
        # independent signings of the same content both PASS verify.
        signed_a = self.signer.sign_credential(self._make_vc())
        signed_b = self.signer.sign_credential(self._make_vc())
        self.assertTrue(verify_credential(signed_a, registry=self.registry).valid)
        self.assertTrue(verify_credential(signed_b, registry=self.registry).valid)


class VerifierFailureModes(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        key_path = Path(self.tmp.name) / "key.json"
        self.signer = Ed25519Signer.from_file_or_create(
            key_path, signer_did="did:web:failure-modes-test"
        )
        self.registry = IssuerRegistry()
        self.registry.register(
            IssuerRecord(
                issuer_did=self.signer.signer_did,
                public_key_multibase=self.signer.public_key_multibase(),
            )
        )

    def _make_signed(self) -> dict:
        # Use the signer's own DID for the issuer so we don't trip
        # the issuer_mismatch defense.
        return self.signer.sign_credential(
            _make_unsigned_vc(issuer=self.signer.signer_did)
        )

    def test_missing_proof_field(self):
        vc = _make_unsigned_vc(issuer=self.signer.signer_did)
        result = verify_credential(vc, registry=self.registry)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "missing_or_invalid_proof")

    def test_missing_issuer(self):
        signed = self._make_signed()
        signed.pop("issuer")
        result = verify_credential(signed, registry=self.registry)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "missing_issuer")

    def test_unknown_issuer(self):
        signed = self._make_signed()
        empty_registry = IssuerRegistry()
        result = verify_credential(signed, registry=empty_registry)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "unknown_issuer")

    def test_missing_proof_value(self):
        signed = self._make_signed()
        signed["proof"].pop("proofValue")
        result = verify_credential(signed, registry=self.registry)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "missing_proof_value")

    def test_malformed_proof_value(self):
        signed = self._make_signed()
        signed["proof"]["proofValue"] = "not-multibase"  # missing 'z' prefix
        result = verify_credential(signed, registry=self.registry)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "malformed_proof_value")

    def test_proof_not_a_dict(self):
        signed = self._make_signed()
        signed["proof"] = "i am a string"
        result = verify_credential(signed, registry=self.registry)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "missing_or_invalid_proof")

    def test_completely_garbage_input_does_not_crash(self):
        for garbage in (
            {},
            {"junk": 1},
            {"proof": None},
            {"proof": [], "issuer": "x"},
        ):
            result = verify_credential(garbage, registry=self.registry)
            self.assertIsInstance(result, VerificationResult)
            self.assertFalse(result.valid)

    def test_signer_refuses_to_sign_for_another_issuer(self):
        """Defense-in-depth: an agent CANNOT issue a VC claiming
        to be another agent's DID. The signer rejects with a
        clear error message before the proof is ever attached."""

        vc = _make_unsigned_vc(issuer="did:web:not-this-signer")
        with self.assertRaises(ValueError) as cm:
            self.signer.sign_credential(vc)
        self.assertIn("issuer_mismatch", str(cm.exception))


class CrossAgentTransmission(unittest.TestCase):
    """The civic-services mesh's value proposition is that one agent
    issues a VC and another agent verifies it. These tests pin
    cross-agent verification on the shared registry."""

    def test_two_separate_agents_cross_verify(self):
        with TemporaryDirectory() as tmp:
            # Agent A (Anerkennung) generates its keypair
            agent_a = Ed25519Signer.from_file_or_create(
                Path(tmp) / "agent_a.json", signer_did="did:web:anerkennung-agent"
            )
            # Agent B (Housing) ships its own keypair too
            agent_b = Ed25519Signer.from_file_or_create(
                Path(tmp) / "agent_b.json", signer_did="did:web:housing-agent"
            )
            # Shared registry — both agents register themselves at boot
            registry = IssuerRegistry()
            registry.register(
                IssuerRecord(agent_a.signer_did, agent_a.public_key_multibase())
            )
            registry.register(
                IssuerRecord(agent_b.signer_did, agent_b.public_key_multibase())
            )

            # Agent A issues a credential to a user
            vc = _make_unsigned_vc(issuer=agent_a.signer_did)
            signed = agent_a.sign_credential(vc)

            # Agent B (somewhere else in the mesh) receives + verifies
            result = verify_credential(signed, registry=registry)
            self.assertTrue(result.valid)
            self.assertEqual(result.signer_did, agent_a.signer_did)

    def test_cross_agent_tamper_detection(self):
        with TemporaryDirectory() as tmp:
            agent_a = Ed25519Signer.from_file_or_create(
                Path(tmp) / "agent_a.json", signer_did="did:web:agent-a"
            )
            agent_b = Ed25519Signer.from_file_or_create(
                Path(tmp) / "agent_b.json", signer_did="did:web:agent-b"
            )
            registry = IssuerRegistry()
            registry.register(
                IssuerRecord(agent_a.signer_did, agent_a.public_key_multibase())
            )
            registry.register(
                IssuerRecord(agent_b.signer_did, agent_b.public_key_multibase())
            )
            vc = _make_unsigned_vc(issuer=agent_a.signer_did)
            signed = agent_a.sign_credential(vc)
            # Man-in-the-middle changes the decision to denied
            signed["credentialSubject"]["decision"] = "denied"
            result = verify_credential(signed, registry=registry)
            self.assertFalse(result.valid)
            self.assertEqual(result.reason, "signature_mismatch")

    def test_agent_b_cannot_forge_agent_a_credential_via_signer(self):
        """First defense: the signer refuses to sign a VC whose
        issuer field doesn't match the signer's DID. So agent B
        can't even produce the forged VC through the legitimate
        signing API."""

        with TemporaryDirectory() as tmp:
            agent_a = Ed25519Signer.from_file_or_create(
                Path(tmp) / "agent_a.json", signer_did="did:web:agent-a"
            )
            agent_b = Ed25519Signer.from_file_or_create(
                Path(tmp) / "agent_b.json", signer_did="did:web:agent-b"
            )
            vc = _make_unsigned_vc(issuer=agent_a.signer_did)  # claims agent A
            # Agent B tries to sign it → refused
            with self.assertRaises(ValueError) as cm:
                agent_b.sign_credential(vc)
            self.assertIn("issuer_mismatch", str(cm.exception))

    def test_verify_catches_hand_crafted_forgery(self):
        """Second defense: even if an attacker bypasses the signer
        API and hand-crafts a VC with agent B's signature but agent
        A's DID, verification fails because the registry's public
        key for agent A doesn't match agent B's signature."""

        with TemporaryDirectory() as tmp:
            agent_a = Ed25519Signer.from_file_or_create(
                Path(tmp) / "agent_a.json", signer_did="did:web:agent-a"
            )
            agent_b = Ed25519Signer.from_file_or_create(
                Path(tmp) / "agent_b.json", signer_did="did:web:agent-b"
            )
            registry = IssuerRegistry()
            registry.register(
                IssuerRecord(agent_a.signer_did, agent_a.public_key_multibase())
            )
            # Hand-craft a forgery: sign with agent B's key (via its
            # legitimate API which signs as agent B), then SWAP the
            # issuer field on the wire to claim agent A.
            vc = _make_unsigned_vc(issuer=agent_b.signer_did)
            signed_by_b = agent_b.sign_credential(vc)
            # Attacker on the wire rewrites issuer to agent A
            signed_by_b["issuer"] = agent_a.signer_did
            result = verify_credential(signed_by_b, registry=registry)
            self.assertFalse(result.valid)
            self.assertEqual(result.reason, "signature_mismatch")


class DidDocumentExport(unittest.TestCase):
    def test_did_document_has_required_fields(self):
        with TemporaryDirectory() as tmp:
            signer = Ed25519Signer.from_file_or_create(
                Path(tmp) / "key.json", signer_did="did:web:test"
            )
            doc = build_did_document(signer)
            self.assertEqual(doc["id"], "did:web:test")
            self.assertIn("@context", doc)
            self.assertEqual(len(doc["verificationMethod"]), 1)
            vm = doc["verificationMethod"][0]
            self.assertEqual(vm["controller"], "did:web:test")
            self.assertEqual(vm["type"], "Ed25519VerificationKey2020")
            self.assertEqual(vm["publicKeyMultibase"], signer.public_key_multibase())
            self.assertIn("assertionMethod", doc)
            self.assertEqual(doc["assertionMethod"], [vm["id"]])


if __name__ == "__main__":
    unittest.main()
