"""Actual independent signatures and scope/revocation checks over offline HTTP transport."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.infrastructure.composites.institutional_configuration import (
    InstitutionalVerificationConfiguration,
)
from src.infrastructure.composites.institutional_verifier import (
    ConfiguredInstitutionalEvidenceVerifier,
)
from tests.composite_institutional_helpers import (
    institutional_material,
    configuration_material,
    authority_result,
    sign_artifact,
    utc,
)


def verify_result(monkeypatch, configuration, verifier, request, payload, *, change=None):
    monkeypatch.setenv(configuration.verifier.credential_env, "controlled-test-only")
    calls = []

    def respond(incoming):
        calls.append(incoming)
        return httpx.Response(
            200,
            json=dict(
                owner_service=configuration.verifier.owner_service,
                payload=payload,
                credential=sign_artifact(
                    verifier,
                    configuration.verifier,
                    request.model_dump(mode="json"),
                    payload,
                    change=change,
                ),
            ),
        )

    client = httpx.Client(transport=httpx.MockTransport(respond))
    return ConfiguredInstitutionalEvidenceVerifier(configuration, client), calls


def test_independent_original_signature_and_fresh_admission_retained(monkeypatch):
    *_, artifact, request = institutional_material()
    configuration, signer, verifier = configuration_material()
    result = authority_result(configuration, signer, request, artifact)
    adapter, calls = verify_result(monkeypatch, configuration, verifier, request, result)
    receipt = adapter.verify(request)
    assert len(calls) == 1
    assert receipt.artifact == artifact
    assert receipt.original_credential == result["original_credential"]
    assert receipt.admission.revocation_revision == configuration.revocation.revision
    assert receipt.admission.verifier_credential != receipt.original_credential
    assert receipt.request.definition.authority_approval.official_activation == "UNAVAILABLE"


@pytest.mark.parametrize(
    "change,error",
    [
        ("foreign_signer", "present_but_unverified"),
        ("echo", "malformed_credential"),
        ("issuer", "wrong_issuer"),
        ("audience", "wrong_audience"),
        ("scope", "PRINCIPAL_MISMATCH"),
        ("digest", "ARTIFACT_BINDING_MISMATCH"),
        ("expired_original", "expired_credential"),
        ("unknown_key", "unknown_key_id"),
    ],
)
def test_fresh_signed_verifier_echo_never_substitutes_original_authority(
    monkeypatch, change, error
):
    *_, artifact, request = institutional_material()
    configuration, signer, verifier = configuration_material()
    result = authority_result(configuration, signer, request, artifact)
    if change == "echo":
        result["original_credential"] = "signed-request-echo"
    else:
        claims = {
            "issuer": {"iss": "urn:foreign"},
            "audience": {"aud": "lotus-core"},
            "scope": {"tenant": "foreign"},
            "digest": {"payload_digest": "sha256:" + "f" * 64},
            "expired_original": {"exp": 1},
        }.get(change)
        result["original_credential"] = sign_artifact(
            Ed25519PrivateKey.generate() if change == "foreign_signer" else signer,
            configuration.signer,
            dict(attestation_id=artifact.attestation_id, revision=artifact.revision),
            artifact.model_dump(mode="json"),
            at=datetime.fromisoformat(artifact.claims.approved_at),
            change=claims,
            header_change={"kid": "foreign"} if change == "unknown_key" else None,
        )
    adapter, _ = verify_result(monkeypatch, configuration, verifier, request, result)
    with pytest.raises(ValueError, match=error):
        adapter.verify(request)


@pytest.mark.parametrize(
    "mutation",
    ["attestation_id", "revision", "issuer_id", "approval_time", "subject", "evaluation"],
)
def test_signed_but_wrong_original_content_refuses(monkeypatch, mutation):
    *_, artifact, request = institutional_material()
    configuration, signer, verifier = configuration_material()
    result = authority_result(configuration, signer, request, artifact)
    if mutation in {"attestation_id", "revision", "issuer_id"}:
        result["artifact"][mutation] = "foreign"
    elif mutation == "approval_time":
        result["artifact"]["claims"]["approved_at"] = "2026-10-03T00:00:00.000000Z"
    else:
        result["artifact"][
            "subject_binding" if mutation == "subject" else "evaluation_approval_binding"
        ]["digest"] = "sha256:" + "f" * 64
    result["artifact"]["content_hash"] = ""
    adapter, _ = verify_result(monkeypatch, configuration, verifier, request, result)
    with pytest.raises(ValueError, match="ORIGINAL_MISMATCH"):
        adapter.verify(request)


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("stale", "REVOCATION_UNAVAILABLE"),
        ("future", "REVOCATION_UNAVAILABLE"),
        ("unbounded", "REVOCATION_UNAVAILABLE"),
        ("artifact", "ORIGINAL_UNAVAILABLE"),
        ("signer_subject", "revoked_principal"),
        ("signer_credential", "revoked_principal"),
        ("verifier_subject", "revoked_principal"),
        ("signer_key", "unknown_key_id"),
    ],
)
def test_current_revocation_and_freshness_fail_closed(monkeypatch, mutation, error):
    *_, artifact, request = institutional_material()
    configuration, signer, verifier = configuration_material()
    wire = configuration.model_dump(mode="json")
    now = datetime.now(timezone.utc)
    if mutation == "stale":
        wire["revocation"]["expires_at"] = utc(now - timedelta(seconds=1))
    elif mutation == "future":
        wire["revocation"]["checked_at"] = utc(now + timedelta(seconds=1))
    elif mutation == "unbounded":
        wire["revocation"]["expires_at"] = utc(now + timedelta(hours=1))
    elif mutation == "artifact":
        wire["revocation"]["revoked_artifact_digests"] = [artifact.content_hash]
    elif mutation == "signer_key":
        wire["signer"]["keys"][0]["revoked"] = True
    else:
        role, kind = mutation.split("_")
        wire[role]["revoked_subjects" if kind == "subject" else "revoked_credentials"] = [
            wire[role]["principal_id"] if kind == "subject" else "controlled-credential"
        ]
    changed = InstitutionalVerificationConfiguration.model_validate(wire)
    result = authority_result(configuration, signer, request, artifact)
    adapter, calls = verify_result(monkeypatch, changed, verifier, request, result)
    with pytest.raises(ValueError, match=error):
        adapter.verify(request)
    if mutation in {"stale", "future", "unbounded"}:
        assert calls == []


@pytest.mark.parametrize(
    "mutation",
    [
        "snapshot",
        "revocations",
        "http",
        "same_key",
        "same_principal",
        "source_purpose",
        "issuer",
        "duplicate_key",
    ],
)
def test_missing_or_ambiguous_trust_configuration_refuses(mutation):
    configuration, *_ = configuration_material()
    wire = configuration.model_dump(mode="json")
    if mutation == "snapshot":
        del wire["revocation"]
    elif mutation == "revocations":
        del wire["signer"]["revoked_credentials"]
    elif mutation == "http":
        wire["verifier"]["endpoint"] = "http://127.0.0.1/verification"
    elif mutation == "same_key":
        wire["signer"]["keys"] = deepcopy(wire["verifier"]["keys"])
    elif mutation == "same_principal":
        wire["signer"]["principal_id"] = wire["verifier"]["principal_id"]
    elif mutation == "source_purpose":
        wire["verifier"]["verification_purposes"].append("COMPOSITE_MONTHLY_SOURCE_CUT")
    elif mutation == "issuer":
        wire["signer"]["issuer"] = "unqualified-issuer"
    elif mutation == "duplicate_key":
        wire["signer"]["keys"].append(deepcopy(wire["signer"]["keys"][0]))
    with pytest.raises(ValueError):
        InstitutionalVerificationConfiguration.model_validate(wire)


def test_missing_transport_secret_is_unavailable(monkeypatch):
    *_, artifact, request = institutional_material()
    configuration, signer, verifier = configuration_material()
    result = authority_result(configuration, signer, request, artifact)
    adapter, calls = verify_result(monkeypatch, configuration, verifier, request, result)
    monkeypatch.delenv(configuration.verifier.credential_env)
    assert adapter.verify(request) is None
    assert calls == []


def test_foreign_tenant_is_unavailable_before_transport(monkeypatch):
    *_, artifact, request = institutional_material()
    configuration, signer, verifier = configuration_material()
    result = authority_result(configuration, signer, request, artifact)
    wire = configuration.model_dump(mode="json")
    wire["signer"]["tenant_id"] = wire["verifier"]["tenant_id"] = "foreign-tenant"
    foreign = InstitutionalVerificationConfiguration.model_validate(wire)
    adapter, calls = verify_result(monkeypatch, foreign, verifier, request, result)
    assert adapter.verify(request) is None
    assert calls == []


@pytest.mark.parametrize("mutation", ["before", "expired", "unbounded"])
def test_retained_admission_requires_bounded_revocation_window(monkeypatch, mutation):
    from src.core.composite_eligibility.institutional_verification import (
        InstitutionalAdmissionProof,
    )

    *_, artifact, request = institutional_material()
    configuration, signer, verifier = configuration_material()
    result = authority_result(configuration, signer, request, artifact)
    adapter, _ = verify_result(monkeypatch, configuration, verifier, request, result)
    proof = adapter.verify(request).admission.model_dump(mode="json")
    if mutation == "before":
        proof["admitted_at"] = utc(
            datetime.fromisoformat(proof["revocation_checked_at"]) - timedelta(seconds=1)
        )
    elif mutation == "expired":
        proof["admitted_at"] = proof["revocation_expires_at"]
    else:
        proof["revocation_expires_at"] = utc(
            datetime.fromisoformat(proof["revocation_checked_at"]) + timedelta(minutes=6)
        )
    with pytest.raises(ValueError, match="ADMISSION_WINDOW_INVALID"):
        InstitutionalAdmissionProof.model_validate(proof)


@pytest.mark.parametrize(
    "code,status",
    [
        ("COMPOSITE_ATTESTATION_REVOCATION_UNAVAILABLE", 503),
        ("COMPOSITE_ATTESTATION_ORIGINAL_UNAVAILABLE", 503),
        ("COMPOSITE_ATTESTATION_ORIGINAL_MISMATCH", 422),
        ("COMPOSITE_ATTESTATION_ADMISSION_WINDOW_INVALID", 422),
    ],
)
def test_attestation_refusals_have_stable_public_errors(code, status):
    from fastapi import HTTPException
    from src.api.routers.composite_subjects import _call

    def refused():
        raise ValueError(code)

    with pytest.raises(HTTPException) as error:
        _call(refused)
    assert error.value.status_code == status
    assert error.value.detail["code"] == code


@pytest.mark.parametrize(
    "mutation", ["valid", "revision", "digest", "revoked", "synthetic", "scope"]
)
def test_related_signed_facts_require_exact_qualified_selection(monkeypatch, mutation):
    from src.core.composite_eligibility.staged_publication import finalization_verification_requests
    from src.core.composite_eligibility.verification import VerificationReceipt

    subject, _, definition, *_ = institutional_material()
    related = finalization_verification_requests(definition, subject)[1]
    configuration, _, verifier = configuration_material()
    if mutation == "revoked":
        wire = configuration.model_dump(mode="json")
        wire["revocation"]["revoked_artifact_digests"] = [related.binding.digest]
        configuration = InstitutionalVerificationConfiguration.model_validate(wire)
    payload = VerificationReceipt(
        request=related,
        posture="QUALIFIED_RECEIPT",
        verifier_id=configuration.verifier.principal_id,
        issuer_id=configuration.verifier.receipt_issuer_id,
        artifact_revision=related.binding.revision,
        artifact_digest=related.binding.digest,
    ).model_dump(mode="json")
    if mutation == "revision":
        payload["artifact_revision"] = "foreign"
    elif mutation == "digest":
        payload["artifact_digest"] = "sha256:" + "f" * 64
    elif mutation == "synthetic":
        payload["posture"] = "SYNTHETIC_NON_CERTIFYING"
    elif mutation == "scope":
        payload["request"]["tenant_id"] = "foreign"
    payload["content_hash"] = ""
    adapter, _ = verify_result(monkeypatch, configuration, verifier, related, payload)
    if mutation == "valid":
        assert adapter.verify_related(related).artifact_digest == related.binding.digest
    else:
        with pytest.raises(ValueError):
            adapter.verify_related(related)


@pytest.mark.parametrize("segment,field", [(0, "kid"), (1, "operation"), (1, "tenant")])
def test_validly_signed_duplicate_jws_members_refuse(monkeypatch, segment, field):
    import base64
    from tests.composite_institutional_helpers import encoded

    *_, artifact, request = institutional_material()
    configuration, signer, verifier = configuration_material()
    result = authority_result(configuration, signer, request, artifact)
    parts = result["original_credential"].split(".")
    original = base64.urlsafe_b64decode(parts[segment] + "=" * (-len(parts[segment]) % 4)).decode()
    # Last-member-wins JSON would accept the original valid value and hide the foreign first one.
    parts[segment] = encoded(('{"' + field + '":"foreign",' + original[1:]).encode())
    signing_input = ".".join(parts[:2])
    parts[2] = encoded(signer.sign(signing_input.encode("ascii")))
    result["original_credential"] = ".".join(parts)
    adapter, _ = verify_result(monkeypatch, configuration, verifier, request, result)
    with pytest.raises(ValueError, match="malformed_credential"):
        adapter.verify(request)


@pytest.mark.parametrize("field", ["issuer_id", "verifier_id"])
def test_fresh_signed_result_requires_configured_verifier_identity(monkeypatch, field):
    *_, artifact, request = institutional_material()
    configuration, signer, verifier = configuration_material()
    payload = authority_result(configuration, signer, request, artifact)
    payload[field] = "foreign"
    adapter, _ = verify_result(monkeypatch, configuration, verifier, request, payload)
    with pytest.raises(ValueError, match="COMPOSITE_ATTESTATION_VERIFIER_SCOPE_MISMATCH"):
        adapter.verify(request)


def test_authority_request_cannot_enter_related_fact_channel(monkeypatch):
    from src.core.composite_eligibility.staged_publication import finalization_verification_requests

    subject, _, definition, *_ = institutional_material()
    configuration, _, verifier = configuration_material()
    request = finalization_verification_requests(definition, subject)[0]
    adapter, calls = verify_result(monkeypatch, configuration, verifier, request, {})
    assert adapter.verify_related(request) is None
    assert calls == []


def test_retained_institutional_receipt_requires_unchanged_self_hash(monkeypatch):
    from src.core.composite_eligibility.institutional_verification import (
        InstitutionalVerificationReceipt,
    )

    *_, artifact, request = institutional_material()
    configuration, signer, verifier = configuration_material()
    adapter, _ = verify_result(
        monkeypatch,
        configuration,
        verifier,
        request,
        authority_result(configuration, signer, request, artifact),
    )
    wire = adapter.verify(request).model_dump(mode="json")
    wire["admission"]["revocation_revision"] = "foreign-revision"
    with pytest.raises(ValueError, match="COMPOSITE_ATTESTATION_RECEIPT_CONTENT_MISMATCH"):
        InstitutionalVerificationReceipt.model_validate(wire)


@pytest.mark.parametrize(
    "mutation", ["synthetic_definition", "subject_product", "approval_binding"]
)
def test_institutional_request_requires_original_reference_and_exact_approval_scope(mutation):
    from src.core.composite_eligibility.institutional_verification import (
        InstitutionalVerificationRequest,
    )
    from tests.composite_staged_eligibility_helpers import finalization_material

    *_, request = institutional_material()
    wire = request.model_dump(mode="json")
    if mutation == "synthetic_definition":
        wire["definition"] = finalization_material()[2].definition.model_dump(mode="json")
        error = "COMPOSITE_ATTESTATION_REFERENCE_REQUIRED"
    else:
        if mutation == "subject_product":
            wire["subject_binding"]["product_name"] = "ForeignSubject"
        else:
            wire["evaluation_approval_binding"]["digest"] = "sha256:" + "f" * 64
        error = "COMPOSITE_ATTESTATION_SCOPE_MISMATCH"
    with pytest.raises(ValueError, match=error):
        InstitutionalVerificationRequest.model_validate(wire)


def test_unconfigured_related_channel_never_returns_a_qualified_receipt():
    from src.core.composite_eligibility.institutional_verification import (
        UnavailableInstitutionalEvidenceVerifier,
    )
    from src.core.composite_eligibility.staged_publication import finalization_verification_requests

    subject, _, definition, *_ = institutional_material()
    verifier = UnavailableInstitutionalEvidenceVerifier()
    for request in finalization_verification_requests(definition, subject)[1:]:
        assert verifier.verify_related(request) is None
