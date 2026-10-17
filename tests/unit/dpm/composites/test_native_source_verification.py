"""Fixed synthetic JWS integrity and the independent fresh-trust boundary."""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pydantic import ValidationError

from src.core.common.artifact_credentials import verified_artifact
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.native_source_verification import (
    MonthlySourceAdmissionContext,
    MonthlySourceAdmissionProof,
    MonthlySourceVerificationResult,
    NativeAssemblyVerification,
)
from src.core.composite_eligibility.source_assembly import (
    MonthlySourceAssembly,
    NativeMonthlySourceAssembly,
    VerifiedMonthlySourceAssembly,
    assembly_verification_request,
    retained_source_assembly,
)
from src.core.composite_eligibility.verification import VerificationReceipt
from src.infrastructure.composites.source_configuration import SourceBinding
from tests.composite_monthly_source_helpers import assembly_material
from tests.composite_staged_eligibility_helpers import synthetic_verification
from tests.unit.dpm.composites.test_native_source_custody import native_assembly_material
from tests.unit.dpm.infrastructure.test_composite_configured_sources import encoded, signed

ADMITTED = "2026-10-01T00:02:00Z"
ADMITTED_EPOCH = int(datetime.fromisoformat(ADMITTED).timestamp())


def schema_condition_matches(schema, value):
    """Execute the published presence condition's standard JSON Schema keywords.

    This checks the conditional itself, not general schema validation. Complete
    field/type validation is exercised independently through the runtime models.
    """
    if "const" in schema and value != schema["const"]:
        return False
    if schema.get("type") == "null" and value is not None:
        return False
    if "not" in schema and schema_condition_matches(schema["not"], value):
        return False
    if isinstance(value, dict):
        if not all(key in value for key in schema.get("required", [])):
            return False
        if not all(
            schema_condition_matches(child, value[key])
            for key, child in schema.get("properties", {}).items()
            if key in value
        ):
            return False
    if "if" in schema:
        branch = "then" if schema_condition_matches(schema["if"], value) else "else"
        return schema_condition_matches(schema[branch], value)
    return True


def proof_material(seed=bytes(range(32)), *, change=None):
    # Reuse the fixed synthetic seeds already used by composite_historical_policy_helpers.
    key = Ed25519PrivateKey.from_private_bytes(seed)
    assembly = NativeMonthlySourceAssembly.model_validate(native_assembly_material())
    request = assembly_verification_request(assembly)
    receipt = synthetic_verification(request).model_dump(mode="json")
    receipt.update(
        artifact_revision=assembly.observations.source_revision,
        artifact_digest=assembly.native_custody.content_hash,
        content_hash="",
    )
    receipt = VerificationReceipt.model_validate(receipt)
    public_key = {
        "kid": "test-key",
        "kty": "OKP",
        "crv": "Ed25519",
        "alg": "EdDSA",
        "x": encoded(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)),
        "revoked": False,
    }
    context = {
        "configuration_digest": hash_canonical_payload({"public-deployment": "fixture-A"}),
        "issuer": "urn:synthetic:fixture:issuer",
        "audience": "lotus-manage",
        "principal_id": receipt.verifier_id,
        "tenant_id": request.tenant_id,
        "purpose": "COMPOSITE_MONTHLY_SOURCE_CUT",
        "operation": "verification",
        "evidence_posture": "SYNTHETIC_NON_CERTIFYING",
        "verifier_key": public_key,
        "verifier_key_digest": hash_canonical_payload(public_key),
        "revocation_revision": "test-revocation-r1",
        "revocation_digest": hash_canonical_payload({"revocation": "fixed-clear"}),
        "revocation_checked_at": "2026-10-01T00:00:00Z",
        "revocation_expires_at": "2026-10-01T00:05:00Z",
        "admitted_at": ADMITTED,
        "current_revocation_status": "CLEAR",
    }
    admission = MonthlySourceAdmissionContext.model_validate(context)
    result = MonthlySourceVerificationResult(
        receipt=receipt,
        native_custody_digest=assembly.native_custody.content_hash,
        admission=admission,
    )
    credential = signed(
        key,
        admission,
        request.model_dump(mode="json"),
        result.model_dump(mode="json"),
        change={"nbf": ADMITTED_EPOCH - 60, "exp": ADMITTED_EPOCH + 60, **(change or {})},
    )
    proof = {
        "product_name": "CompositeMonthlySourceAdmissionProof",
        "product_version": "v1",
        "result": result.model_dump(mode="json"),
        "verifier_credential": credential,
    }
    return assembly, proof, key


def test_fixed_signed_pair_rehydrates_offline_and_keeps_hash_graph_acyclic():
    assembly, material, _ = proof_material()
    proof = MonthlySourceAdmissionProof.model_validate(material)
    receipt = proof.result.receipt
    pair = NativeAssemblyVerification(receipt, proof)
    with pytest.raises(FrozenInstanceError):
        pair.proof = proof
    wrapper = VerifiedMonthlySourceAssembly(
        assembly=assembly, verification=receipt, native_proof=proof
    )
    serialized = wrapper.model_dump(mode="json")
    assert VerifiedMonthlySourceAssembly.model_validate(serialized) == wrapper
    assert retained_source_assembly(wrapper, assembly.observations) == wrapper
    assert receipt.artifact_digest == assembly.native_custody.content_hash
    assert receipt.request.claims_digest == hash_canonical_payload(assembly.model_dump(mode="json"))
    assert "native_proof" not in assembly.model_dump(mode="json")
    assert proof.content_hash == hash_canonical_payload(
        proof.model_dump(mode="json", exclude={"content_hash"})
    )
    assert proof.result.admission.admitted_at == ADMITTED
    # Current time/keys/source availability are deliberately absent from archival integrity.
    assert MonthlySourceAdmissionProof.model_validate(material) == proof


@pytest.mark.parametrize("construction", ["copy", "construct"])
def test_normal_proof_constructor_retains_exact_canonical_signed_nested_values(construction):
    _, material, _ = proof_material()
    original = MonthlySourceAdmissionProof.model_validate(material)
    assert original.content_hash == (
        "sha256:2920165fd5424654fc36f36d46eb93dca8a451ecfb20dffdeeddb92fd52654b9"
    )
    if construction == "copy":
        receipt = original.result.receipt.model_copy(update={"content_hash": ""})
        result = original.result.model_copy(update={"receipt": receipt})
    else:
        receipt = VerificationReceipt.model_construct(
            **{**original.result.receipt.__dict__, "content_hash": ""}
        )
        result = MonthlySourceVerificationResult.model_construct(
            **{**original.result.__dict__, "receipt": receipt}
        )
    accepted = MonthlySourceAdmissionProof(
        result=result, verifier_credential=original.verifier_credential
    )
    assert accepted.model_dump_json() == original.model_dump_json()
    assert MonthlySourceAdmissionProof.model_validate_json(accepted.model_dump_json()) == accepted
    assert accepted.result.receipt.content_hash == original.result.receipt.content_hash
    assert accepted.content_hash == hash_canonical_payload(
        accepted.model_dump(mode="json", exclude={"content_hash"})
    )
    verified_artifact(
        accepted.verifier_credential,
        binding=accepted.result.admission,
        request=accepted.result.receipt.request.model_dump(mode="json"),
        payload=accepted.result.model_dump(mode="json"),
        now=ADMITTED_EPOCH,
    )


@pytest.mark.parametrize("construction", ["copy", "construct"])
@pytest.mark.parametrize("blank_receipt_hash", [False, True])
def test_copied_or_constructed_nested_tampering_cannot_reuse_original_signature(
    construction, blank_receipt_hash
):
    _, material, _ = proof_material()
    original = MonthlySourceAdmissionProof.model_validate(material)
    changed_receipt = original.result.receipt
    changed_receipt.request.binding.digest = "sha256:" + "8" * 64
    if blank_receipt_hash:
        changed_receipt.content_hash = ""
    if construction == "copy":
        result = original.result.model_copy(update={"receipt": changed_receipt})
    else:
        result = MonthlySourceVerificationResult.model_construct(
            **{**original.result.__dict__, "receipt": changed_receipt}
        )
    with pytest.raises(ValidationError, match="CONTENT_MISMATCH|ARTIFACT_BINDING_MISMATCH"):
        MonthlySourceAdmissionProof(result=result, verifier_credential=original.verifier_credential)


def test_result_and_pair_detach_input_receipt_and_canonicalize_copied_blank_proof():
    _, material, _ = proof_material()
    original = MonthlySourceAdmissionProof.model_validate(material)
    input_receipt = original.result.receipt
    result = MonthlySourceVerificationResult(
        receipt=input_receipt,
        native_custody_digest=original.result.native_custody_digest,
        admission=original.result.admission,
    )
    result_before = result.model_dump_json()
    blank = original.model_copy(update={"content_hash": ""})
    pair = NativeAssemblyVerification(input_receipt, blank)
    pair_before = (pair.receipt.model_dump_json(), pair.proof.model_dump_json())
    assert pair.proof == original and pair.proof is not blank
    assert pair.proof.content_hash == original.content_hash
    input_receipt.artifact_revision = "foreign-revision"
    input_receipt.request.binding.digest = "sha256:" + "8" * 64
    # Legacy models remain mutable, while the new retained boundaries own snapshots.
    assert input_receipt.artifact_revision == "foreign-revision"
    assert result.model_dump_json() == result_before
    assert (pair.receipt.model_dump_json(), pair.proof.model_dump_json()) == pair_before
    assert pair.receipt == pair.proof.result.receipt


@pytest.mark.parametrize("side", ["receipt", "proof_receipt", "result_receipt"])
@pytest.mark.parametrize("descendant", ["receipt", "request", "binding"])
def test_returned_legacy_descendants_cannot_mutate_retained_pair_or_signed_result(side, descendant):
    _, material, _ = proof_material()
    proof = MonthlySourceAdmissionProof.model_validate(material)
    pair = NativeAssemblyVerification(proof.result.receipt, proof)
    proof_before = proof.model_dump_json()
    pair_before = (pair.receipt.model_dump_json(), pair.proof.model_dump_json())
    returned = (
        pair.receipt
        if side == "receipt"
        else pair.proof.result.receipt
        if side == "proof_receipt"
        else proof.result.receipt
    )
    if descendant == "receipt":
        returned.verifier_id = "foreign-verifier"
    elif descendant == "request":
        returned.request.claims_digest = "sha256:" + "8" * 64
    else:
        returned.request.binding.revision = "foreign-revision"
    assert proof.model_dump_json() == proof_before
    assert (pair.receipt.model_dump_json(), pair.proof.model_dump_json()) == pair_before
    assert pair.receipt == pair.proof.result.receipt
    assert (
        MonthlySourceAdmissionProof.model_validate_json(pair.proof.model_dump_json()) == pair.proof
    )


@pytest.mark.parametrize(
    "mutation,error",
    [
        ("signature", "present_but_unverified"),
        ("result", "ARTIFACT_BINDING_MISMATCH"),
        ("key_digest", "KEY_DIGEST_MISMATCH"),
        ("proof_digest", "PROOF_CONTENT_MISMATCH"),
        ("custody", "RESULT_BINDING_MISMATCH"),
        ("tenant", "RESULT_BINDING_MISMATCH"),
        ("principal", "RESULT_BINDING_MISMATCH"),
        ("window", "REVOCATION_WINDOW_INVALID"),
        ("admitted", "REVOCATION_WINDOW_INVALID"),
        ("purpose", "literal_error"),
        ("revoked", "literal_error"),
        ("extra", "extra_forbidden"),
    ],
)
def test_corrupt_retained_proof_refusals(mutation, error):
    _, material, _ = proof_material()
    admission = material["result"]["admission"]
    if mutation == "signature":
        parts = material["verifier_credential"].split(".")
        parts[-1] = encoded(b"\0" * 64)
        material["verifier_credential"] = ".".join(parts)
    elif mutation == "result":
        admission["configuration_digest"] = "sha256:" + "9" * 64
    elif mutation == "key_digest":
        admission["verifier_key_digest"] = "sha256:" + "9" * 64
    elif mutation == "proof_digest":
        material["content_hash"] = "sha256:" + "9" * 64
    elif mutation == "custody":
        material["result"]["native_custody_digest"] = "sha256:" + "9" * 64
    elif mutation in {"tenant", "principal"}:
        admission[mutation + "_id"] = "foreign"
    elif mutation == "window":
        admission["revocation_expires_at"] = "2026-10-01T00:05:01Z"
    elif mutation == "admitted":
        admission["admitted_at"] = admission["revocation_expires_at"]
    elif mutation == "purpose":
        admission["purpose"] = "ELIGIBILITY_POLICY"
    elif mutation == "revoked":
        admission["verifier_key"]["revoked"] = True
    else:
        material["admitted"] = True
    with pytest.raises(ValidationError, match=error):
        MonthlySourceAdmissionProof.model_validate(material)


@pytest.mark.parametrize(
    "change,error",
    [
        ({"exp": ADMITTED_EPOCH}, "expired_credential"),
        ({"nbf": ADMITTED_EPOCH + 1}, "expired_credential"),
        ({"exp": True}, "expired_credential"),
        ({"iss": "urn:foreign"}, "wrong_issuer"),
        ({"aud": "foreign"}, "wrong_audience"),
        ({"sub": "foreign"}, "PRINCIPAL_MISMATCH"),
        ({"tenant": "foreign"}, "PRINCIPAL_MISMATCH"),
        ({"operation": "observations"}, "ARTIFACT_BINDING_MISMATCH"),
        ({"request_digest": "sha256:" + "9" * 64}, "ARTIFACT_BINDING_MISMATCH"),
        ({"payload_digest": "sha256:" + "9" * 64}, "ARTIFACT_BINDING_MISMATCH"),
    ],
)
def test_signature_does_not_override_original_claim_binding_or_window(change, error):
    _, material, _ = proof_material(change=change)
    with pytest.raises(ValidationError, match=error):
        MonthlySourceAdmissionProof.model_validate(material)


def independent_binding(proof):
    context = proof.result.admission
    return SourceBinding(
        operation="verification",
        tenant_id=context.tenant_id,
        owner_service="lotus-manage",
        endpoint="https://independent.test/verification",
        issuer=context.issuer,
        principal_id=context.principal_id,
        receipt_issuer_id=proof.result.receipt.issuer_id,
        credential_env="SYNTHETIC_FIXTURE_UNUSED",
        keys=(context.verifier_key.model_dump(),),
        evidence_posture="SYNTHETIC_NON_CERTIFYING",
        verification_purposes=(context.purpose,),
    )


def test_self_selected_integrity_never_enrolls_fresh_deployment_trust():
    _, a, _ = proof_material()
    _, b, _ = proof_material(bytes(range(32, 64)))
    admitted_a = MonthlySourceAdmissionProof.model_validate(a)
    self_selected_b = MonthlySourceAdmissionProof.model_validate(b)
    # B even copies A's kid, issuer and configuration digest; these are signed commitments.
    assert (
        self_selected_b.result.admission.configuration_digest
        == admitted_a.result.admission.configuration_digest
    )
    assert (
        self_selected_b.result.admission.verifier_key.kid
        == admitted_a.result.admission.verifier_key.kid
    )
    assert (
        self_selected_b.result.admission.verifier_key.x
        != admitted_a.result.admission.verifier_key.x
    )
    policy_a = independent_binding(admitted_a)
    with pytest.raises(ValueError, match="present_but_unverified"):
        verified_artifact(
            self_selected_b.verifier_credential,
            binding=policy_a,
            request=self_selected_b.result.receipt.request.model_dump(mode="json"),
            payload=self_selected_b.result.model_dump(mode="json"),
            now=ADMITTED_EPOCH,
        )
    # An original valid proof is archival integrity; its old admitted_at cannot select a fresh clock.
    with pytest.raises(ValueError, match="expired_credential"):
        verified_artifact(
            admitted_a.verifier_credential,
            binding=policy_a,
            request=admitted_a.result.receipt.request.model_dump(mode="json"),
            payload=admitted_a.result.model_dump(mode="json"),
            now=ADMITTED_EPOCH + 60,
        )
    revoked = policy_a.model_copy(update={"revoked_subjects": (policy_a.principal_id,)})
    with pytest.raises(ValueError, match="revoked_principal"):
        verified_artifact(
            admitted_a.verifier_credential,
            binding=revoked,
            request=admitted_a.result.receipt.request.model_dump(mode="json"),
            payload=admitted_a.result.model_dump(mode="json"),
            now=ADMITTED_EPOCH,
        )
    assert MonthlySourceAdmissionProof.model_validate(a) == admitted_a


@pytest.mark.parametrize(
    "version,presence", [("v1", "null"), ("v1", "proof"), ("v2", "missing"), ("v2", "null")]
)
def test_proof_is_required_for_v2_and_key_is_forbidden_for_v1_in_runtime_and_schema(
    version, presence
):
    native, material, _ = proof_material()
    proof = MonthlySourceAdmissionProof.model_validate(material)
    assembly = (
        native if version == "v2" else MonthlySourceAssembly.model_validate(assembly_material()[1])
    )
    payload = {
        "assembly": assembly.model_dump(mode="json"),
        "verification": proof.result.receipt.model_dump(mode="json"),
    }
    if presence != "missing":
        payload["native_proof"] = None if presence == "null" else proof.model_dump(mode="json")
    for mode in ("validation", "serialization"):
        schema = VerifiedMonthlySourceAssembly.model_json_schema(mode=mode)
        assert not schema_condition_matches(schema["allOf"][0], deepcopy(payload))
    with pytest.raises(ValidationError, match="PROOF_(FORBIDDEN_V1|REQUIRED_V2)"):
        VerifiedMonthlySourceAssembly.model_validate(payload)


def test_schema_accepts_complete_v1_and_v2_and_pair_cannot_rebind_receipt():
    assembly, material, _ = proof_material()
    proof = MonthlySourceAdmissionProof.model_validate(material)
    wrappers = [
        VerifiedMonthlySourceAssembly(
            assembly=assembly, verification=proof.result.receipt, native_proof=proof
        )
    ]
    legacy = MonthlySourceAssembly.model_validate(assembly_material()[1])
    wrappers.append(
        VerifiedMonthlySourceAssembly(
            assembly=legacy,
            verification=synthetic_verification(assembly_verification_request(legacy)),
        )
    )
    for mode in ("validation", "serialization"):
        schema = VerifiedMonthlySourceAssembly.model_json_schema(mode=mode)
        for wrapper in wrappers:
            assert schema_condition_matches(schema["allOf"][0], wrapper.model_dump(mode="json"))
    wrong = proof.result.receipt.model_dump(mode="json")
    wrong.update(artifact_revision="foreign", content_hash="")
    receipt = VerificationReceipt.model_validate(wrong)
    with pytest.raises(ValueError, match="PAIRED_RECEIPT_MISMATCH"):
        NativeAssemblyVerification(receipt, proof)
    with pytest.raises(ValidationError, match="PROOF_ASSEMBLY_MISMATCH"):
        VerifiedMonthlySourceAssembly(assembly=assembly, verification=receipt, native_proof=proof)


@pytest.mark.parametrize(
    "injected", ["native_proof", "source_assembly_evidence", "admission", "proposal"]
)
def test_closed_first_recurring_and_approval_commands_refuse_proof_import(injected):
    from src.api.services.composite_monthly_eligibility import MonthlyApprovalRequest
    from src.api.services.composite_monthly_evaluation import MonthlyEvaluationRequest
    from src.api.services.composite_subject_requests import (
        SubjectApprovalRequest,
        SubjectEvaluationRequest,
    )

    first = {
        "policy_proposal_revision": "r1",
        "policy_approval_content_hash": "sha256:" + "1" * 64,
        "target_membership_revision": "r1",
        "source_cut_id": "cut",
        "source_revision": "r1",
        "source_content_hash": "sha256:" + "1" * 64,
    }
    recurring = {
        "month": "2026-09",
        "policy_approval_content_hash": "sha256:" + "1" * 64,
        "parent_membership_revision": "r1",
        "parent_membership_content_hash": "sha256:" + "1" * 64,
        "attestation_version": "v1",
        "universe_content_hash": "sha256:" + "1" * 64,
        "target_membership_revision": "r2",
        "correlation_id": "test-correlation",
    }
    approval = {"expected_proposal_content_hash": "sha256:" + "1" * 64}
    for model, payload in (
        (SubjectEvaluationRequest, first),
        (MonthlyEvaluationRequest, recurring),
        (SubjectApprovalRequest, approval),
        (MonthlyApprovalRequest, approval),
    ):
        model.model_validate(payload)
        with pytest.raises(ValidationError, match="extra_forbidden"):
            model.model_validate({**payload, injected: {"caller": "cannot import trusted custody"}})
