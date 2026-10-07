"""Rehashed inputs still obey subject, source, purpose and immutable financial graph."""

import pytest
from pydantic import ValidationError

from src.core.composite_eligibility.staged_subject import CandidateUniverse, EligibilitySubject
from src.core.composite_eligibility.staged_controls import SubjectEvaluationProposal
from src.core.composite_eligibility.staged_publication import SubjectFinalization
from src.core.composite_eligibility.verification import (
    UnavailableCompositeEvidenceVerifier,
    require_verification,
    VerificationReceipt,
)
from tests.composite_staged_eligibility_helpers import finalization_material


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("coverage_to", "2026-09-29", "UNIVERSE_WINDOW_MISMATCH"),
        ("coverage_to", "2026-09-99", "UNIVERSE_DATE_INVALID"),
        ("source_cut_id", "unrelated-cut", "REGISTRY_BINDING_MISMATCH"),
    ],
)
def test_candidate_rehash_does_not_admit_wrong_window_or_source_reference(field, value, code):
    subject, _, _ = finalization_material()
    wire = subject.universe.model_dump(mode="json") | {field: value, "content_hash": ""}
    with pytest.raises(ValidationError, match=code):
        CandidateUniverse.model_validate(wire)


def test_subject_rehash_cannot_change_currency_or_invent_future_population():
    subject, _, _ = finalization_material()
    wire = subject.model_dump(mode="json") | {"reporting_currency": "EUR", "content_hash": ""}
    with pytest.raises(ValidationError, match="UNIVERSE_SCOPE_MISMATCH"):
        EligibilitySubject.model_validate(wire)
    wire = subject.model_dump(mode="json") | {
        "created_at": "2026-08-19T00:00:00.000000Z",
        "content_hash": "",
    }
    with pytest.raises(ValidationError, match="FUTURE_UNIVERSE_GENERATION"):
        EligibilitySubject.model_validate(wire)


@pytest.mark.parametrize(
    "field,value",
    [
        ("owner_service", "wrong-owner"),
        ("source_cut_id", "wrong-cut"),
        ("source_watermark", "wrong-revision"),
        ("content_hash", "sha256:" + "0" * 64),
    ],
)
def test_evaluation_rehash_cannot_substitute_actual_source_binding(field, value):
    _, controls, _ = finalization_material()
    wire = controls[2].model_dump(mode="json")
    wire["observation_binding"][field] = value
    wire["content_hash"] = ""
    with pytest.raises(ValidationError, match="SOURCE_BINDING_MISMATCH"):
        SubjectEvaluationProposal.model_validate(wire)


def test_rehashed_wrong_verification_purpose_is_not_independent_approval():
    _, _, finalization = finalization_material()
    wire = finalization.model_dump(mode="json")
    wire["verifications"][0]["request"]["purpose"] = "ELIGIBILITY_POLICY"
    wire["verifications"][0]["content_hash"] = ""
    wire["verifications"][0] = VerificationReceipt.model_validate(
        wire["verifications"][0]
    ).model_dump(mode="json")
    wire["content_hash"] = ""
    with pytest.raises(ValidationError, match="FINAL_VERIFICATION_MISMATCH"):
        SubjectFinalization.model_validate(wire)


def test_typed_receipt_cannot_bypass_unavailable_default_verification():
    _, _, finalization = finalization_material()
    request = finalization.verifications[0].request
    with pytest.raises(ValueError, match="VERIFICATION_UNAVAILABLE"):
        require_verification(UnavailableCompositeEvidenceVerifier(), request)


def test_source_fixture_has_no_financial_fact_product_or_activation_claim():
    _, _, finalization = finalization_material()
    assert finalization.official_activation == "UNAVAILABLE"
    assert all(
        receipt.posture == "SYNTHETIC_NON_CERTIFYING" for receipt in finalization.verifications
    )
    assert {
        selection.source_product
        for selection in finalization.definition.source_authority.payload.selections
    } == {"SyntheticAssets", "SyntheticReturns"}
    assert not any(
        product.authority_scope == "POLICY_INPUT"
        for product in finalization.subject.universe.source_products
    )
