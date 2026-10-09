"""Real signed bytes, exact artifact binding and fail-closed configured transport."""

import base64
import json
import time
from pathlib import Path

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import ValidationError
from prometheus_client import REGISTRY

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.staged_ports import CandidateUniverseRequest
from src.core.composite_eligibility.verification import VerificationReceipt
from src.api.composition.composite_source_service import build_composite_subject_service
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from src.infrastructure.authority_http import AuthorityHttpError
from src.infrastructure.composites.configured_sources import (
    CompositeSourceTransport,
    ConfiguredCandidateUniverseSource,
    ConfiguredCompositeEvidenceVerifier,
)
from src.infrastructure.composites.source_configuration import (
    CompositeSourceConfiguration,
    SourceBinding,
)
from src.infrastructure.composites.source_credentials import verified_artifact
from tests.composite_staged_eligibility_helpers import (
    lifecycle_material,
    synthetic_verification,
    verification_request,
)


def encoded(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@pytest.fixture
def signing():
    key = Ed25519PrivateKey.generate()
    binding = SourceBinding(
        operation="candidates",
        tenant_id="synthetic-tenant",
        owner_service="synthetic-source",
        endpoint="https://source.test/candidates",
        issuer="urn:synthetic:fixture:issuer",
        principal_id="synthetic-fixture-source",
        credential_env="SYNTHETIC_SOURCE_CREDENTIAL",
        keys=[
            {
                "kid": "test-key",
                "x": encoded(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)),
            }
        ],
        evidence_posture="SYNTHETIC_NON_CERTIFYING",
    )
    return key, binding


def signed(key, binding, request, payload, *, change=None, header_change=None):
    claims = dict(
        iss=binding.issuer,
        aud="lotus-manage",
        sub=binding.principal_id,
        tenant=binding.tenant_id,
        principal_kind="service",
        jti="test-credential",
        exp=int(time.time()) + 60,
        operation=binding.operation,
        request_digest=hash_canonical_payload(request),
        payload_digest=hash_canonical_payload(payload),
        evidence_posture=binding.evidence_posture,
    )
    claims.update(change or {})
    header = dict(alg="EdDSA", kid="test-key", typ="JWT")
    header.update(header_change or {})
    signing_input = f"{encoded(header)}.{encoded(claims)}"
    return f"{signing_input}.{encoded(key.sign(signing_input.encode()))}"


@pytest.mark.parametrize(
    "change,error",
    [
        ({"iss": "other"}, "wrong_issuer"),
        ({"aud": "lotus-core"}, "wrong_audience"),
        ({"exp": 0}, "expired_credential"),
        ({"exp": True}, "expired_credential"),
        ({"nbf": 9999999999}, "expired_credential"),
        ({"jti": ""}, "malformed_credential"),
        ({"sub": "other"}, "PRINCIPAL_MISMATCH"),
        ({"tenant": "other"}, "PRINCIPAL_MISMATCH"),
        ({"principal_kind": "user"}, "PRINCIPAL_MISMATCH"),
        ({"act": "other"}, "PRINCIPAL_MISMATCH"),
        ({"operation": "verification"}, "ARTIFACT_BINDING_MISMATCH"),
        ({"request_digest": "0" * 64}, "ARTIFACT_BINDING_MISMATCH"),
        ({"payload_digest": "0" * 64}, "ARTIFACT_BINDING_MISMATCH"),
        ({"evidence_posture": "QUALIFIED_RECEIPT"}, "ARTIFACT_BINDING_MISMATCH"),
    ],
)
def test_signed_claim_refusals(signing, change, error):
    key, binding = signing
    with pytest.raises(ValueError, match=error):
        verified_artifact(
            signed(key, binding, {}, {}, change=change), binding=binding, request={}, payload={}
        )


@pytest.mark.parametrize(
    "header,error",
    [
        ({"alg": "none"}, "malformed_credential"),
        ({"kid": "unknown"}, "unknown_key_id"),
        ({"jku": "https://attacker.test"}, "malformed_credential"),
    ],
)
def test_token_cannot_nominate_trust(signing, header, error):
    key, binding = signing
    with pytest.raises(ValueError, match=error):
        verified_artifact(
            signed(key, binding, {}, {}, header_change=header),
            binding=binding,
            request={},
            payload={},
        )


def test_signature_before_claims_and_revocation(signing):
    key, binding = signing
    foreign = Ed25519PrivateKey.generate()
    with pytest.raises(ValueError, match="present_but_unverified"):
        verified_artifact(
            signed(foreign, binding, {}, {}, change={"iss": "wrong"}),
            binding=binding,
            request={},
            payload={},
        )
    for updated in (
        binding.model_copy(update={"revoked_credentials": ("test-credential",)}),
        binding.model_copy(update={"revoked_subjects": (binding.principal_id,)}),
    ):
        with pytest.raises(ValueError, match="revoked_principal"):
            verified_artifact(signed(key, binding, {}, {}), binding=updated, request={}, payload={})
    with pytest.raises(ValueError, match="unknown_key_id"):
        revoked = binding.model_copy(
            update={"keys": (binding.keys[0].model_copy(update={"revoked": True}),)}
        )
        verified_artifact(signed(key, binding, {}, {}), binding=revoked, request={}, payload={})


@pytest.mark.parametrize("token", ["", "a.b", "a.b.c", "W10.e30.a"])
def test_malformed_credentials(signing, token):
    with pytest.raises(ValueError, match="malformed_credential"):
        verified_artifact(token, binding=signing[1], request={}, payload={})


def test_configured_candidate_and_verifier_exact_artifacts(signing, monkeypatch):
    key, binding = signing
    _, subject, *_ = lifecycle_material()
    universe = subject.universe
    verifier_binding = binding.model_copy(
        update={
            "operation": "verification",
            "receipt_issuer_id": "synthetic-fixture-issuer",
            "verification_purposes": ("ELIGIBILITY_POLICY",),
            "principal_id": "synthetic-fixture-verifier",
            "endpoint": "https://source.test/verification",
            "keys": (
                binding.keys[0].model_copy(
                    update={
                        "x": encoded(
                            Ed25519PrivateKey.generate()
                            .public_key()
                            .public_bytes(Encoding.Raw, PublicFormat.Raw)
                        )
                    }
                ),
            ),
        }
    )
    # Independent signing material, not a caller-owned verification flag.
    verifier_key = Ed25519PrivateKey.generate()
    verifier_binding = verifier_binding.model_copy(
        update={
            "keys": (
                binding.keys[0].model_copy(
                    update={
                        "x": encoded(
                            verifier_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
                        )
                    }
                ),
            )
        }
    )
    configuration = CompositeSourceConfiguration(bindings=(binding, verifier_binding))
    monkeypatch.setenv(binding.credential_env, "outbound-test-only")
    purpose = verification_request(subject, "ELIGIBILITY_POLICY", "sha256:" + "0" * 64)
    receipt = synthetic_verification(purpose)

    def handler(request):
        assert request.headers["Authorization"] == "Bearer outbound-test-only"
        requested = json.loads(request.content)
        selected, signer, payload = (
            (binding, key, universe.model_dump(mode="json"))
            if request.url.path == "/candidates"
            else (verifier_binding, verifier_key, receipt.model_dump(mode="json"))
        )
        return httpx.Response(
            200,
            json={
                "owner_service": selected.owner_service,
                "payload": payload,
                "credential": signed(signer, selected, requested, payload),
            },
        )

    transport = CompositeSourceTransport(
        configuration, httpx.Client(transport=httpx.MockTransport(handler))
    )
    request = CandidateUniverseRequest(
        universe.tenant_id,
        universe.composite_id,
        universe.definition_version,
        universe.month,
        universe.reporting_currency,
        universe.registry_binding,
    )
    assert ConfiguredCandidateUniverseSource(transport).resolve(request) == universe
    assert ConfiguredCompositeEvidenceVerifier(transport).verify(purpose) == receipt
    assert transport.resolve(tenant_id="foreign", operation="candidates", request={}) is None
    monkeypatch.delenv(binding.credential_env)
    assert ConfiguredCandidateUniverseSource(transport).resolve(request) is None


@pytest.mark.parametrize(
    "endpoint,extra",
    [
        ("http://source.test", {}),
        ("https://user:password@source.test", {}),
        ("https://source.test?url=attacker", {}),
        ("https://source.test#fragment", {}),
        ("http://127.0.0.1:8099", {}),
        ("http://localhost:8099", {"allow_local_http": True}),
    ],
)
def test_endpoint_pin_refusals(signing, endpoint, extra):
    with pytest.raises(ValidationError):
        SourceBinding.model_validate({**signing[1].model_dump(), "endpoint": endpoint, **extra})


def test_configuration_cannot_claim_qualification_or_shared_verifier(signing):
    binding = signing[1]
    with pytest.raises(ValidationError):
        SourceBinding.model_validate(
            {**binding.model_dump(), "evidence_posture": "QUALIFIED_RECEIPT"}
        )
    with pytest.raises(ValidationError, match="DUPLICATE_BINDING"):
        CompositeSourceConfiguration(bindings=(binding, binding))
    verifier = binding.model_copy(
        update={
            "operation": "verification",
            "principal_id": "different",
            "receipt_issuer_id": "synthetic-fixture-issuer",
            "verification_purposes": ("ELIGIBILITY_POLICY",),
        }
    )
    with pytest.raises(ValidationError, match="NOT_INDEPENDENT"):
        CompositeSourceConfiguration(bindings=(binding, verifier))
    with pytest.raises(ValidationError, match="DUPLICATE_KEY"):
        SourceBinding.model_validate(
            {**binding.model_dump(), "keys": [binding.keys[0], binding.keys[0]]}
        )
    local = SourceBinding.model_validate(
        {**binding.model_dump(), "endpoint": "http://127.0.0.1:8099", "allow_local_http": True}
    )
    assert local.allow_local_http


def test_encoded_key_alias_cannot_bypass_independence(signing):
    binding = signing[1]
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
    value = binding.keys[0].x
    alias = value[:-1] + alphabet[alphabet.index(value[-1]) + 1]
    assert base64.urlsafe_b64decode(value + "=") == base64.urlsafe_b64decode(alias + "=")
    with pytest.raises(ValidationError, match="KEY_NONCANONICAL"):
        SourceBinding.model_validate(
            {**binding.model_dump(), "keys": [{"kid": "alias", "x": alias}]}
        )


@pytest.mark.parametrize("encoding", [None, "gzip"])
def test_response_stream_cap_aborts_and_closes_before_following_chunk(
    signing, monkeypatch, encoding
):
    monkeypatch.setenv(signing[1].credential_env, "test")
    state = {"chunks": 0, "closed": False}

    class Stream(httpx.SyncByteStream):
        def __iter__(self):
            for _ in range(100):
                state["chunks"] += 1
                yield b"x" * 600

        def close(self):
            state["closed"] = True

    response_headers = {} if encoding is None else {"Content-Encoding": encoding}
    transport = CompositeSourceTransport(
        CompositeSourceConfiguration(bindings=(signing[1],), maximum_response_bytes=1024),
        httpx.Client(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(200, headers=response_headers, stream=Stream())
            )
        ),
    )
    with pytest.raises(ValueError, match="RESPONSE_INVALID"):
        transport.resolve(tenant_id=signing[1].tenant_id, operation="candidates", request={})
    assert state == {"chunks": 2 if encoding is None else 0, "closed": True}


@pytest.mark.parametrize(
    "status,body,error",
    [
        (302, {}, "TRANSPORT_REJECTED"),
        (403, {}, "TRANSPORT_REJECTED"),
        (503, {}, "TRANSPORT_UNAVAILABLE"),
        (200, {"payload": {}}, "RESPONSE_INVALID"),
        (200, {"padding": "x" * 2048}, "RESPONSE_INVALID"),
    ],
)
def test_transport_refusals(signing, monkeypatch, status, body, error):
    monkeypatch.setenv(signing[1].credential_env, "test")
    transport = CompositeSourceTransport(
        CompositeSourceConfiguration(bindings=(signing[1],), maximum_response_bytes=1024),
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(status, json=body))),
    )
    with pytest.raises((AuthorityHttpError, ValueError), match=error):
        transport.resolve(tenant_id=signing[1].tenant_id, operation="candidates", request={})


@pytest.mark.parametrize("change", ["purpose", "verifier", "posture", "issuer"])
def test_signed_receipt_cannot_rebind_approval(signing, monkeypatch, change):
    key, original = signing
    binding = original.model_copy(
        update={
            "operation": "verification",
            "principal_id": "synthetic-fixture-verifier",
            "verification_purposes": ("ELIGIBILITY_POLICY",),
            "receipt_issuer_id": "synthetic-fixture-issuer",
        }
    )
    _, subject, *_ = lifecycle_material()
    request = verification_request(subject, "ELIGIBILITY_POLICY", "sha256:" + "0" * 64)
    payload = synthetic_verification(request).model_dump(mode="json")
    if change == "purpose":
        payload["request"]["purpose"] = "ELIGIBILITY_POLICY_EVALUATION"
    elif change == "verifier":
        payload["verifier_id"] = "other"
    elif change == "issuer":
        payload["issuer_id"] = "other"
    else:
        payload["posture"] = "QUALIFIED_RECEIPT"
    payload["content_hash"] = ""
    payload = VerificationReceipt.model_validate(payload).model_dump(mode="json")

    def handler(http_request):
        requested = json.loads(http_request.content)
        return httpx.Response(
            200,
            json={
                "owner_service": binding.owner_service,
                "payload": payload,
                "credential": signed(key, binding, requested, payload),
            },
        )

    monkeypatch.setenv(binding.credential_env, "test")
    transport = CompositeSourceTransport(
        CompositeSourceConfiguration(bindings=(binding,)),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ValueError, match="VERIFICATION_BINDING_MISMATCH"):
        ConfiguredCompositeEvidenceVerifier(transport).verify(request)


def test_unconfigured_or_missing_verifier_purpose_makes_no_http_call(signing):
    _, subject, *_ = lifecycle_material()
    request = verification_request(subject, "ELIGIBILITY_POLICY", "sha256:" + "0" * 64)

    def unreachable(_):
        raise AssertionError("Unadmitted purpose contacted authority")

    binding = signing[1].model_copy(
        update={
            "operation": "verification",
            "verification_purposes": ("PROVIDER_REGISTRATION",),
            "receipt_issuer_id": "synthetic-fixture-issuer",
        }
    )
    transport = CompositeSourceTransport(
        CompositeSourceConfiguration(bindings=(binding,)),
        httpx.Client(transport=httpx.MockTransport(unreachable)),
    )
    assert ConfiguredCompositeEvidenceVerifier(transport).verify(request) is None
    assert (
        ConfiguredCandidateUniverseSource(transport).resolve(
            CandidateUniverseRequest(
                subject.tenant_id,
                subject.composite_id,
                subject.definition_version,
                subject.month,
                subject.reporting_currency,
                subject.universe.registry_binding,
            )
        )
        is None
    )
    allowed = binding.model_copy(
        update={
            "verification_purposes": ("ELIGIBILITY_POLICY",),
            "credential_env": "MISSING_SYNTHETIC_VERIFIER_CREDENTIAL",
        }
    )
    unavailable = CompositeSourceTransport(
        CompositeSourceConfiguration(bindings=(allowed,)), transport.client
    )
    assert ConfiguredCompositeEvidenceVerifier(unavailable).verify(request) is None


def test_signed_candidate_wrong_scope_is_rejected(signing, monkeypatch):
    key, binding = signing
    _, subject, *_ = lifecycle_material()
    payload = subject.universe.model_dump(mode="json")
    payload["tenant_id"] = "foreign"
    payload["content_hash"] = ""
    from src.core.composite_eligibility.staged_subject import CandidateUniverse

    payload = CandidateUniverse.model_validate(payload).model_dump(mode="json")

    def handler(http_request):
        requested = json.loads(http_request.content)
        return httpx.Response(
            200,
            json={
                "owner_service": binding.owner_service,
                "payload": payload,
                "credential": signed(key, binding, requested, payload),
            },
        )

    monkeypatch.setenv(binding.credential_env, "test")
    transport = CompositeSourceTransport(
        CompositeSourceConfiguration(bindings=(binding,)),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )
    request = CandidateUniverseRequest(
        subject.tenant_id,
        subject.composite_id,
        subject.definition_version,
        subject.month,
        subject.reporting_currency,
        subject.universe.registry_binding,
    )
    with pytest.raises(ValueError, match="UNIVERSE_SCOPE_MISMATCH"):
        ConfiguredCandidateUniverseSource(transport).resolve(request)


def test_signed_non_object_claims_are_malformed(signing):
    key, binding = signing
    value = f"{encoded({'alg': 'EdDSA', 'kid': 'test-key'})}.{encoded([])}"
    token = f"{value}.{encoded(key.sign(value.encode()))}"
    with pytest.raises(ValueError, match="malformed_credential"):
        verified_artifact(token, binding=binding, request={}, payload={})


def test_deployment_composition_preserves_unavailable_default_and_rejects_missing_purpose(
    signing, monkeypatch
):
    repository = InMemoryDpmCompositeRepository()
    monkeypatch.delenv("DPM_COMPOSITE_SOURCES_JSON", raising=False)
    default = build_composite_subject_service(repository)
    assert type(default.candidates).__name__ == "UnavailableCandidateUniverseSource"
    monkeypatch.setenv(
        "DPM_COMPOSITE_SOURCES_JSON",
        CompositeSourceConfiguration(bindings=(signing[1],)).model_dump_json(),
    )
    configured = build_composite_subject_service(repository)
    assert (
        configured.candidates.resolve(
            CandidateUniverseRequest(
                "foreign",
                "c",
                "d",
                "2026-09",
                "USD",
                lifecycle_material()[1].universe.registry_binding,
            )
        )
        is None
    )
    bad = {
        **signing[1].model_dump(),
        "operation": "verification",
        "receipt_issuer_id": "synthetic-fixture-issuer",
    }
    with pytest.raises(ValidationError, match="PURPOSES_INVALID"):
        SourceBinding.model_validate(bad)
    with pytest.raises(ValidationError, match="PURPOSES_INVALID"):
        SourceBinding.model_validate(
            {
                **signing[1].model_dump(),
                "operation": "verification",
                "receipt_issuer_id": "synthetic-fixture-issuer",
                "verification_purposes": ["ELIGIBILITY_POLICY", "ELIGIBILITY_POLICY"],
            }
        )


def test_credential_issuer_and_receipt_issuer_are_distinct_contract_bindings(signing):
    with pytest.raises(ValidationError, match="ISSUER_URI_REQUIRED"):
        SourceBinding.model_validate({**signing[1].model_dump(), "issuer": "opaque-id"})
    with pytest.raises(ValidationError, match="RECEIPT_ISSUER_INVALID"):
        SourceBinding.model_validate(
            {**signing[1].model_dump(), "receipt_issuer_id": "receipt-authority"}
        )


@pytest.mark.parametrize(
    "name,error",
    [("valid_service", "wrong_audience"), ("present_but_unverified", "present_but_unverified")],
)
def test_committed_platform_ed25519_vectors_verify_before_manage_audience(name, error, signing):
    fixture = json.loads(
        (
            Path(__file__).resolve().parents[3] / "fixtures" / "composite_source_credentials.json"
        ).read_text()
    )
    vector = fixture[name]
    key = fixture["jwks"]["keys"][0]
    binding = SourceBinding.model_validate(
        {
            **signing[1].model_dump(),
            "issuer": vector["verification_inputs"]["expected_issuer"],
            "keys": [{field: key[field] for field in ("kid", "kty", "crv", "alg", "x")}],
        }
    )
    # Published valid vector targets the BFF: signature succeeds, then Manage
    # refuses its audience. The structurally identical foreign-signature vector
    # refuses earlier, before trusting issuer, audience or expired fixture time.
    with pytest.raises(ValueError, match=error):
        verified_artifact(vector["credential"], binding=binding, request={}, payload={})


@pytest.mark.parametrize(
    "owner,label", [("lotus-core", "lotus-core"), ("synthetic-owner", "unknown")]
)
def test_configured_source_metrics_keep_bound_owner_and_normalize_external_owner(
    signing, monkeypatch, owner, label
):
    key, original = signing
    binding = original.model_copy(update={"owner_service": owner})
    monkeypatch.setenv(binding.credential_env, "test")
    labels = {"source_service": label, "method": "post", "outcome": "success"}
    metric = "lotus_manage_source_http_request_total"
    before = REGISTRY.get_sample_value(metric, labels) or 0

    def handler(_):
        return httpx.Response(
            200,
            json={
                "owner_service": owner,
                "payload": {},
                "credential": signed(key, binding, {}, {}),
            },
        )

    transport = CompositeSourceTransport(
        CompositeSourceConfiguration(bindings=(binding,)),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )
    assert transport.resolve(tenant_id=binding.tenant_id, operation="candidates", request={}) == {}
    assert REGISTRY.get_sample_value(metric, labels) == before + 1
