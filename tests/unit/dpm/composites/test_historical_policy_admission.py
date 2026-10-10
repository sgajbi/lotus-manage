"""Original raw custody, independent normalized proof and version-specific admission refusals."""

import base64
from copy import deepcopy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.core.composite_eligibility.approval import decode_policy_proposal, decode_policy_approval
from src.core.composite_eligibility.historical_policy import (
    HistoricalMonthlyPolicyProposal,
    HistoricalMonthlyPolicyApproval,
    HistoricalPolicyMapping,
    HistoricalPolicyVerification,
    admitted_historical_policy,
    UnavailableHistoricalPolicyAdmission,
)
from src.core.composite_eligibility.monthly_amendment import (
    decode_monthly_proposal,
    decode_monthly_approval,
)
from src.core.composite_eligibility.evaluation_control import require_operation_verification
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_historical_policy_helpers import (
    historical_contract_material,
    seed_historical_root,
)


@pytest.fixture(scope="module")
def material():
    return historical_contract_material()


def test_original_raw_bytes_and_credential_survive_normalized_mapping(material):
    port, proposal, approval, root, checked, receipt = material
    raw = base64.b64decode(port.mapping.raw_original_base64, validate=True)
    assert raw.endswith(b"\r\n")
    port.signer.public_key().verify(base64.b64decode(port.mapping.original_credential), raw)
    assert proposal.proposed_at > port.mapping.original_approved_at
    for proof in (
        proposal.verification,
        approval.verification,
        root.operation_verification,
        checked.operation_verification,
    ):
        proof.require_verifier_signature()
        assert proof.mapping.raw_original_base64 == port.mapping.raw_original_base64
    assert receipt.completeness == "UNVERIFIED"
    assert approval.official_activation == "UNAVAILABLE"


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("raw_original_base64", "!!!!", "RAW_INVALID"),
        ("raw_original_base64", "AB==", "RAW_INVALID"),
        ("raw_original_base64", "eA==", "RAW_MISMATCH"),
        ("original_approved_at", "2026-09-01T00:00:00.000000Z", "ORIGINAL_CLOCK_INVALID"),
        ("original_proposed_at", "2026-08-31T23:59:59.000000Z", "ORIGINAL_CLOCK_INVALID"),
        ("original_approved_by", "synthetic-policy-maker", "SELF_APPROVAL"),
    ],
)
def test_original_mapping_refuses_bad_inputs(material, field, value, code):
    wire = material[0].mapping.model_dump(mode="json")
    if field == "original_approved_by":
        value = wire["original_proposed_by"]
    wire.update({field: value, "content_hash": ""})
    with pytest.raises(ValueError, match=code):
        HistoricalPolicyMapping.model_validate(wire)


@pytest.mark.parametrize(
    "field,value",
    [
        ("verifier_id", "different-verifier"),
        ("configuration_digest", "sha256:" + "d" * 64),
        ("revocation_revision", "different-revocation"),
        ("verifier_credential", "eA=="),
        ("verifier_key_digest", "sha256:" + "f" * 64),
        ("verifier_public_key_base64", "eA=="),
    ],
)
def test_rehashed_normalized_proof_cannot_change_signed_content(material, field, value):
    wire = material[1].verification.model_dump(mode="json")
    wire.update({field: value, "content_hash": ""})
    with pytest.raises(ValueError):
        HistoricalPolicyVerification.model_validate(wire)


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("signer_principal_id", "controlled-verifier", "INDEPENDENCE_REQUIRED"),
        ("signer_key_digest", None, "INDEPENDENCE_REQUIRED"),
        ("checked_at", "2026-10-10T01:00:01.000000Z", "ADMISSION_WINDOW_INVALID"),
        ("expires_at", "2026-10-10T01:00:00.000000Z", "ADMISSION_WINDOW_INVALID"),
        ("expires_at", "2026-10-10T01:05:01.000000Z", "ADMISSION_WINDOW_INVALID"),
        ("admitted_at", "2026-10-10T00:59:59.000000Z", "ADMISSION_WINDOW_INVALID"),
        ("original_signature_status", "UNVERIFIED", "literal_error"),
        ("current_revocation_status", "REVOKED", "literal_error"),
    ],
)
def test_normalized_verification_refuses_invalid_state(material, field, value, code):
    wire = material[1].verification.model_dump(mode="json")
    wire.update(
        {field: wire["verifier_key_digest"] if value is None else value, "content_hash": ""}
    )
    with pytest.raises(ValueError, match=code):
        HistoricalPolicyVerification.model_validate(wire)


def test_fresh_admission_requires_server_trust_even_for_valid_other_signature(material):
    port = deepcopy(material[0])
    request = material[1].verification.request
    assert admitted_historical_policy(port, request).request == request
    port.verifier = Ed25519PrivateKey.from_private_bytes(bytes(reversed(range(32))))
    with pytest.raises(ValueError, match="TRUST_MISMATCH"):
        admitted_historical_policy(port, request)
    with pytest.raises(ValueError, match="ADMISSION_UNAVAILABLE"):
        admitted_historical_policy(UnavailableHistoricalPolicyAdmission(), request)


@pytest.mark.parametrize(
    "decode,index,version",
    [
        (decode_policy_proposal, 1, "v1"),
        (decode_policy_approval, 2, "v1"),
        (decode_monthly_proposal, 3, "v1"),
        (decode_monthly_approval, 4, "v2"),
    ],
)
def test_explicit_versions_cannot_be_downgraded(material, decode, index, version):
    wire = material[index].model_dump(mode="json")
    assert decode(wire) == material[index]
    with pytest.raises(ValueError):
        decode(wire | {"product_version": version})
    for unknown in (None, "v99"):
        with pytest.raises(ValueError, match="VERSION_UNSUPPORTED"):
            decode(wire | {"product_version": unknown})


def test_historical_root_roundtrips_existing_memory_custody():
    repository = InMemoryDpmCompositeRepository()
    _, scope, original, _ = seed_historical_root(repository)
    assert original.product_version == "v3"
    assert repository.get_monthly_policy_approval(**scope, month="2026-09").product_version == "v2"
    for _ in range(2):
        repository.save_monthly_evaluation_proposal(proposal=original.approval.proposal)
        repository.save_monthly_evaluation_approval(approval=original.approval)
    assert len(repository._publications) == 2


@pytest.mark.parametrize("claim", ["mapping", "request", "intent", "hash"])
def test_policy_proposal_refuses_divergent_current_claims(material, claim):
    port, proposal, *_ = material
    wire = proposal.model_dump(mode="json") | {"content_hash": ""}
    code = "MAPPING_MISMATCH"
    if claim == "mapping":
        wire["eligibility_policy_version"] = "different-version"
    elif claim == "request":
        wire["proposal_revision"] = "different-revision"
        code = "REQUEST_MISMATCH"
    elif claim == "intent":
        request = proposal.verification.request.model_copy(
            update={"intent_digest": "sha256:" + "f" * 64}
        )
        wire["verification"] = port.verify(request).model_dump(mode="json")
        code = "INTENT_MISMATCH"
    else:
        wire["content_hash"] = "sha256:" + "f" * 64
        code = "CONTENT_MISMATCH"
    with pytest.raises(ValueError, match=code):
        HistoricalMonthlyPolicyProposal.model_validate(wire)


@pytest.mark.parametrize("claim", ["self", "clock", "request"])
def test_policy_approval_refuses_changed_checker_or_time(material, claim):
    _, proposal, approval, *_ = material
    wire = approval.model_dump(mode="json") | {"content_hash": ""}
    if claim == "self":
        wire["approved_by"] = proposal.proposed_by
        code = "SELF_APPROVAL"
    elif claim == "clock":
        wire["approved_at"] = "2026-10-10T00:59:00.000000Z"
        code = "APPROVAL_BEFORE_PROPOSAL"
    else:
        wire["approved_by"] = "other-checker"
        code = "REQUEST_MISMATCH"
    with pytest.raises(ValueError, match=code):
        HistoricalMonthlyPolicyApproval.model_validate(wire)


def test_fresh_admission_rejects_valid_proof_for_a_different_operation_actor(material):
    port = deepcopy(material[0])
    request = material[1].verification.request
    proof = port.verify(request.model_copy(update={"actor_id": "different-current-actor"}))
    port.verify = lambda requested: proof
    with pytest.raises(ValueError, match="REQUEST_MISMATCH"):
        admitted_historical_policy(port, request)


def test_mapping_refuses_noncanonical_attachment_identity(material):
    wire = material[0].mapping.model_dump(mode="json") | {"content_hash": ""}
    wire["attachments"].append(wire["attachments"][0])
    with pytest.raises(ValueError, match="ATTACHMENTS_NONCANONICAL"):
        HistoricalPolicyMapping.model_validate(wire)


@pytest.mark.parametrize("claim", ["scope", "original-clock"])
def test_verification_rejects_mapping_scope_or_pre_original_admission(material, claim):
    wire = material[1].verification.model_dump(mode="json") | {"content_hash": ""}
    if claim == "scope":
        wire["request"]["scope"]["run_id"] = "other-run"
        code = "MAPPING_MISMATCH"
    else:
        wire["request"]["requested_at"] = "2025-01-01T00:00:00.000000Z"
        code = "ORIGINAL_CLOCK_INVALID"
    with pytest.raises(ValueError, match=code):
        HistoricalPolicyVerification.model_validate(wire)


@pytest.mark.parametrize("claim", ["policy", "clock", "mapping", "intent"])
def test_current_evaluation_guard_rejects_cross_family_or_changed_proof(material, claim):
    port, _, _, root, *_ = material
    proof = root.operation_verification
    require_operation_verification(
        root, proof, "EVALUATION_PROPOSAL", root.proposed_by, root.proposed_at
    )
    proposal, actor, instant = root, root.proposed_by, root.proposed_at
    if claim == "policy":
        from tests.composite_monthly_amendment_helpers import seed_complete_monthly_root

        _, old, _ = seed_complete_monthly_root(InMemoryDpmCompositeRepository())
        proposal = old.approval.proposal
        code = "REQUEST_MISMATCH"
    elif claim == "clock":
        instant = "2026-10-10T01:00:00.000000Z"
        code = "APPROVAL_BEFORE_PROPOSAL"
    elif claim == "mapping":
        other = deepcopy(port)
        # A separately signed normalized mapping cannot replace the exact retained mapping.
        other.mapping = HistoricalPolicyMapping.model_validate(
            other.mapping.model_dump(mode="json")
            | {"original_approved_by": "different-original-checker", "content_hash": ""}
        )
        proof = other.verify(proof.request)
        code = "MAPPING_MISMATCH"
    else:
        actor = "different-current-maker"
        code = "INTENT_MISMATCH"
    with pytest.raises(ValueError, match=code):
        require_operation_verification(proposal, proof, "EVALUATION_PROPOSAL", actor, instant)
