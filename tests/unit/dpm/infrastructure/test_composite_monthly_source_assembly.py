"""Complete manifest evidence is independent of business date or individual cut equality."""

import json
from dataclasses import replace

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import ValidationError

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.source_assembly import (
    MonthlySourceAssembly,
    VerifiedMonthlySourceAssembly,
    assembly_verification_request,
)
from src.core.composite_eligibility.verification import VerificationRequest
from src.infrastructure.composites.configured_sources import (
    CompositeSourceTransport,
    ConfiguredCompositeEvidenceVerifier,
    ConfiguredMonthlyEligibilitySource,
)
from src.infrastructure.composites.source_configuration import (
    CompositeSourceConfiguration,
    SourceBinding,
)
from tests.composite_monthly_source_helpers import assembly_material
from tests.composite_staged_eligibility_helpers import lifecycle_material, synthetic_verification
from tests.unit.dpm.infrastructure.test_composite_configured_sources import encoded, signed


@pytest.mark.parametrize("posture", ["SYNTHETIC_UNQUALIFIED", "SOURCE_UNVERIFIED", "UNAVAILABLE"])
@pytest.mark.parametrize("allow_purpose", [True, False])
def test_monthly_signed_assembly_needs_independent_purpose_receipt(
    monkeypatch, posture, allow_purpose
):
    request, assembly = assembly_material()
    assembly["compatibility_posture"] = posture
    key, verifier_key = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    common = dict(
        tenant_id=request.scope.tenant_id,
        owner_service="synthetic-source",
        issuer="urn:synthetic:fixture:issuer",
        credential_env="TEST_ASSEMBLY_CREDENTIAL",
        evidence_posture="SYNTHETIC_NON_CERTIFYING",
    )
    source = SourceBinding(
        **common,
        operation="observations",
        principal_id="source",
        endpoint="https://source.test/observations",
        keys=[
            {
                "kid": "test-key",
                "x": encoded(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)),
            }
        ],
    )
    verifier = SourceBinding(
        **common,
        operation="verification",
        receipt_issuer_id="synthetic-fixture-issuer",
        principal_id="synthetic-fixture-verifier",
        endpoint="https://verifier.test/verification",
        verification_purposes=[
            "COMPOSITE_MONTHLY_SOURCE_CUT" if allow_purpose else "PROVIDER_REGISTRATION"
        ],
        keys=[
            {
                "kid": "test-key",
                "x": encoded(
                    verifier_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
                ),
            }
        ],
    )
    calls = []

    def handler(http_request):
        requested = json.loads(http_request.content)
        calls.append(http_request.url.host)
        if http_request.url.host == "source.test":
            selected, signer, payload = source, key, assembly
        else:
            verification = VerificationRequest.model_validate(requested)
            assert verification.purpose == "COMPOSITE_MONTHLY_SOURCE_CUT"
            assert verification.subject_content_hash == request.expected_content_hash
            assert verification.claims_digest == hash_canonical_payload(assembly)
            assert verification.binding.digest == assembly["compatibility_binding"]["digest"]
            selected, signer, payload = (
                verifier,
                verifier_key,
                synthetic_verification(verification).model_dump(mode="json"),
            )
        return httpx.Response(
            200,
            json={
                "owner_service": selected.owner_service,
                "payload": payload,
                "credential": signed(signer, selected, requested, payload),
            },
        )

    monkeypatch.setenv(source.credential_env, "test-only")
    transport = CompositeSourceTransport(
        CompositeSourceConfiguration(bindings=[source, verifier]),
        httpx.Client(transport=httpx.MockTransport(handler)),
    )
    port = ConfiguredMonthlyEligibilitySource(
        transport, ConfiguredCompositeEvidenceVerifier(transport)
    )
    resolution = port.resolve(request)
    assert (resolution.observations is not None) == (
        posture == "SYNTHETIC_UNQUALIFIED" and allow_purpose
    )
    assert calls == (
        ["source.test", "verifier.test"]
        if posture == "SYNTHETIC_UNQUALIFIED" and allow_purpose
        else ["source.test"]
    )
    assert (
        resolution.observations is None
        or resolution.observations.evidence_class == "SYNTHETIC_UNQUALIFIED"
    )
    with pytest.raises(ValueError, match="SOURCE_OWNER_MISMATCH"):
        port.resolve(replace(request, owner_service="other"))
    monkeypatch.delenv(source.credential_env)
    assert port.resolve(request).observations is None
    unbound = CompositeSourceTransport(
        CompositeSourceConfiguration(bindings=[verifier]), transport.client
    )
    assert (
        ConfiguredMonthlyEligibilitySource(unbound, ConfiguredCompositeEvidenceVerifier(unbound))
        .resolve(request)
        .observations
        is None
    )


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("missing", "too_short"),
        ("duplicate", "INPUTS_INCOMPLETE"),
        ("order", "INPUTS_NONCANONICAL"),
        ("altered_cut", "CONTENT_MISMATCH"),
        ("altered_fact", "CONTENT_MISMATCH"),
        ("product", "BINDING_INVALID"),
    ],
)
def test_complete_manifest_refusals(mutation, error):
    _, material = assembly_material()
    if mutation == "missing":
        material["inputs"].pop()
    elif mutation == "duplicate":
        material["inputs"][0] = material["inputs"][1]
    elif mutation == "order":
        material["inputs"].reverse()
    elif mutation == "altered_cut":
        material["inputs"][0]["source_cut_id"] = "other"
    elif mutation == "altered_fact":
        material["observations"]["source_revision"] = "other"
    else:
        material["compatibility_binding"]["product_name"] = "Wrong"
    with pytest.raises(ValidationError, match=error):
        MonthlySourceAssembly.model_validate(material)


def test_retained_source_evidence_rejects_changed_receipt_or_observations():
    from src.core.composite_eligibility.staged_controls import SubjectEvaluationProposal

    _, material = assembly_material()
    assembly = MonthlySourceAssembly.model_validate(material)
    request = assembly_verification_request(assembly)
    evidence = VerifiedMonthlySourceAssembly(
        assembly=assembly, verification=synthetic_verification(request)
    )
    _, _, _, _, proposal, *_ = lifecycle_material()
    legacy = proposal.model_dump(mode="json")
    assert "source_assembly_evidence" not in legacy
    assert SubjectEvaluationProposal.model_validate(legacy).content_hash == proposal.content_hash
    payload = {
        **legacy,
        "source_assembly_evidence": evidence.model_dump(mode="json"),
        "content_hash": "",
    }
    retained = SubjectEvaluationProposal.model_validate(payload)
    assert retained.source_assembly_evidence == evidence
    wrong_request = request.model_copy(update={"claims_digest": "sha256:" + "2" * 64})
    with pytest.raises(ValidationError, match="VERIFICATION_MISMATCH"):
        VerifiedMonthlySourceAssembly(
            assembly=assembly, verification=synthetic_verification(wrong_request)
        )
    changed = material["observations"]
    changed["source_revision"] = "other"
    material["compatibility_binding"]["digest"] = hash_canonical_payload(
        {"observations": changed, "inputs": material["inputs"]}
    )
    altered = MonthlySourceAssembly.model_validate(material)
    altered_evidence = VerifiedMonthlySourceAssembly(
        assembly=altered,
        verification=synthetic_verification(assembly_verification_request(altered)),
    )
    payload["source_assembly_evidence"] = altered_evidence.model_dump(mode="json")
    with pytest.raises(ValidationError, match="OBSERVATIONS_MISMATCH"):
        SubjectEvaluationProposal.model_validate(payload)
