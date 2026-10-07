"""Rehashed inputs still obey subject, source, purpose and immutable financial graph."""

import pytest
from pydantic import ValidationError

from src.core.composite_eligibility.staged_subject import CandidateUniverse, EligibilitySubject
from src.core.composite_eligibility.staged_controls import (
    SubjectPolicyProposal,
    SubjectPolicyApproval,
    SubjectEvaluationProposal,
    SubjectEvaluationApproval,
    subject_approval_claims,
)
from src.core.composite_eligibility.staged_publication import (
    SubjectFinalization,
    SubjectFinalizationReceipt,
    require_definition_subject,
    finalization_verification_requests,
    initial_projection,
)
from src.core.composite_eligibility.verification import (
    UnavailableCompositeEvidenceVerifier,
    require_verification,
    VerificationReceipt,
    VerificationRequest,
)
from tests.composite_staged_eligibility_helpers import (
    finalization_material,
    synthetic_verification,
    final_definition,
)
from tests.composite_authority_helpers import (
    independent_digest,
    rebind_definition,
    institutional_reference_wire,
)
from src.core.composite_definition_versions import DpmCompositeDefinitionV2
from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations


def assert_domain_refusal(model, wire, code):
    """Require the intended validator, not an earlier malformed-fixture error."""
    with pytest.raises(ValidationError) as failure:
        model.model_validate(wire)
    assert [str(error.get("ctx", {}).get("error")) for error in failure.value.errors()] == [code]


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


@pytest.mark.parametrize("mutation", ["duplicate", "reversed", "no-authority", "policy-input"])
def test_candidate_population_requires_canonical_identities_and_one_registry(mutation):
    subject, _, _ = finalization_material()
    wire = subject.universe.model_dump(mode="json")
    assert CandidateUniverse.model_validate(wire) == subject.universe
    if mutation == "duplicate":
        wire["members"] *= 2
    elif mutation == "reversed":
        second = wire["members"][0] | {"member_id": "z-second"}
        wire["members"] = [second, wire["members"][0]]
    else:
        wire["source_products"][0]["authority_scope"] = (
            "POLICY_INPUT" if mutation == "policy-input" else "REFERENCE_INPUT"
        )
    wire["content_hash"] = ""
    assert_domain_refusal(
        CandidateUniverse,
        wire,
        "COMPOSITE_SUBJECT_MEMBERS_NONCANONICAL"
        if mutation in {"duplicate", "reversed"}
        else "COMPOSITE_SUBJECT_SOURCE_REFERENCE_INVALID",
    )


@pytest.mark.parametrize(
    "field,value", [("inception_date", "2026-09-02"), ("termination_date", "2026-09-29")]
)
def test_subject_requires_full_calendar_month_even_with_valid_rehash(field, value):
    subject, _, _ = finalization_material()
    complete = subject.model_dump(mode="json") | {
        "termination_date": "2026-09-30",
        "content_hash": "",
    }
    assert EligibilitySubject.model_validate(complete).termination_date == "2026-09-30"
    assert_domain_refusal(
        EligibilitySubject,
        complete | {field: value},
        "COMPOSITE_SUBJECT_DEFINITION_WINDOW_MISMATCH",
    )


def test_subject_rejects_supplied_digest_without_silently_rehashing():
    subject, _, _ = finalization_material()
    assert_domain_refusal(
        EligibilitySubject,
        subject.model_dump(mode="json") | {"content_hash": "sha256:" + "0" * 64},
        "COMPOSITE_SUBJECT_CONTENT_MISMATCH",
    )


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("eligibility_policy_version", "other-policy", "COMPOSITE_SUBJECT_POLICY_MISMATCH"),
        ("proposed_by", "other-maker", "COMPOSITE_SUBJECT_MAKER_MISMATCH"),
        ("proposed_at", "2026-08-19T00:00:00.000000Z", "COMPOSITE_SUBJECT_MAKER_MISMATCH"),
    ],
)
def test_policy_is_bound_to_subject_version_maker_and_creation(field, value, code):
    _, controls, _ = finalization_material()
    policy = controls[0]
    assert SubjectPolicyProposal.model_validate(policy.model_dump(mode="json")) == policy
    wire = policy.model_dump(mode="json")
    wire["proposal"].update({field: value, "content_hash": ""})
    wire["content_hash"] = ""
    assert_domain_refusal(SubjectPolicyProposal, wire, code)


def test_policy_approval_cannot_approve_a_different_proposal_revision():
    _, controls, _ = finalization_material()
    wire = controls[1].model_dump(mode="json")
    wire["approval"]["proposal"].update(proposal_revision="other-revision", content_hash="")
    wire["approval"]["content_hash"] = wire["content_hash"] = ""
    assert_domain_refusal(SubjectPolicyApproval, wire, "COMPOSITE_SUBJECT_POLICY_APPROVAL_MISMATCH")


@pytest.mark.parametrize(
    "field,value",
    [
        ("purpose", "RETURN_METHOD_CALENDAR"),
        ("tenant_id", "other-tenant"),
        ("composite_id", "other-composite"),
        ("definition_version", "other-version"),
        ("subject_content_hash", "sha256:" + "0" * 64),
        ("claims_digest", "sha256:" + "0" * 64),
        ("effective_from", "2026-09-02"),
        ("effective_to", "2026-09-29"),
    ],
)
def test_policy_verification_cannot_rebind_any_approval_dimension(field, value):
    _, controls, _ = finalization_material()
    approval = controls[1]
    assert SubjectPolicyApproval.model_validate(approval.model_dump(mode="json")) == approval
    wire = approval.model_dump(mode="json")
    wire["verification"]["request"][field] = value
    wire["verification"]["content_hash"] = wire["content_hash"] = ""
    assert_domain_refusal(
        SubjectPolicyApproval, wire, "COMPOSITE_SUBJECT_VERIFICATION_BINDING_MISMATCH"
    )


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("universe", "COMPOSITE_SUBJECT_SOURCE_UNIVERSE_MISMATCH"),
        ("currency", "COMPOSITE_SUBJECT_EVALUATION_BINDING_MISMATCH"),
        ("instant", "COMPOSITE_SUBJECT_EVALUATION_BINDING_MISMATCH"),
        ("recomputed-input", "COMPOSITE_ELIGIBILITY_EVALUATION_RECOMPUTATION_MISMATCH"),
    ],
)
def test_evaluation_rebind_and_rehash_cannot_replace_observed_calculation(mutation, code):
    _, controls, _ = finalization_material()
    evaluation = controls[2]
    assert (
        SubjectEvaluationProposal.model_validate(evaluation.model_dump(mode="json")) == evaluation
    )
    wire = evaluation.model_dump(mode="json")
    if mutation == "universe":
        wire["observations"]["expected_portfolio_ids"] = ["other-member"]
        wire["observations"]["portfolios"] = []
    elif mutation == "currency":
        wire["observations"]["reporting_currency"] = "EUR"
    elif mutation == "instant":
        wire["proposed_at"] = "2026-10-03T00:00:00.000000Z"
    else:
        wire["evaluation"]["input_content_hash"] = "sha256:" + "0" * 64
        wire["evaluation"]["content_hash"] = ""
    wire["observation_binding"]["content_hash"] = independent_digest(wire["observations"])
    wire["content_hash"] = ""
    assert_domain_refusal(SubjectEvaluationProposal, wire, code)


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("approved_by", "synthetic-maker", "COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN"),
        (
            "approved_at",
            "2026-10-01T00:00:00.000000Z",
            "COMPOSITE_ELIGIBILITY_APPROVAL_BEFORE_PROPOSAL",
        ),
        ("claims_digest", "sha256:" + "0" * 64, "COMPOSITE_SUBJECT_APPROVAL_CLAIMS_MISMATCH"),
        (
            "evidence_kind",
            "QUALIFIED_VERIFICATION_RECEIPT",
            "COMPOSITE_SUBJECT_VERIFICATION_POSTURE_MISMATCH",
        ),
    ],
)
def test_evaluation_approval_requires_independent_bound_non_certifying_evidence(field, value, code):
    _, controls, _ = finalization_material()
    approval = controls[3]
    assert SubjectEvaluationApproval.model_validate(approval.model_dump(mode="json")) == approval
    assert_domain_refusal(
        SubjectEvaluationApproval,
        approval.model_dump(mode="json") | {field: value, "content_hash": ""},
        code,
    )


def test_finalization_joins_the_actual_subject_and_projection():
    _, _, finalization = finalization_material()
    assert SubjectFinalization.model_validate(finalization.model_dump(mode="json")) == finalization
    wire = finalization.model_dump(mode="json")
    wire["subject"].update(display_name="different-subject", content_hash="")
    wire["content_hash"] = ""
    assert_domain_refusal(SubjectFinalization, wire, "COMPOSITE_SUBJECT_APPROVAL_BINDING_MISMATCH")
    wire = finalization.model_dump(mode="json")
    wire["evaluation_approval"].update(
        membership_content_hash="sha256:" + "0" * 64, content_hash=""
    )
    # This negative reaches the definition's exact approval binding first; test the
    # projection guard independently at custody, where no definition precedes it.
    from src.core.composite_eligibility.staged_custody import require_control_custody

    approval = SubjectEvaluationApproval.model_validate(wire["evaluation_approval"])
    with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_PROJECTION_MISMATCH$"):
        require_control_custody(approval, finalization.subject, approval.proposal)
    definition = final_definition(finalization.subject, approval)
    wire = finalization.model_dump(mode="json") | {
        "evaluation_approval": approval.model_dump(mode="json"),
        "definition": definition.model_dump(mode="json"),
        "content_hash": "",
        "verifications": [
            synthetic_verification(request).model_dump(mode="json")
            for request in finalization_verification_requests(definition, finalization.subject)
        ],
    }
    assert_domain_refusal(SubjectFinalization, wire, "COMPOSITE_SUBJECT_PROJECTION_MISMATCH")


@pytest.mark.parametrize("field", ["membership_content_hash", "universe_content_hash"])
def test_final_receipt_cannot_claim_a_different_published_projection(field):
    _, _, finalization = finalization_material()
    approval = finalization.evaluation_approval
    receipt = SubjectFinalizationReceipt(
        finalization=finalization,
        publication_sequence=1,
        membership_content_hash=approval.membership_content_hash,
        universe_content_hash=approval.universe_content_hash,
    )
    assert_domain_refusal(
        SubjectFinalizationReceipt,
        receipt.model_dump(mode="json") | {field: "sha256:" + "0" * 64, "content_hash": ""},
        "COMPOSITE_SUBJECT_RECEIPT_BINDING_MISMATCH",
    )


def test_verifier_rejects_rebound_receipt_and_inverted_effective_dates():
    subject, _, finalization = finalization_material()
    request = finalization.verifications[0].request
    assert_domain_refusal(
        VerificationRequest,
        request.model_dump(mode="json") | {"effective_from": "2026-10-01"},
        "COMPOSITE_SUBJECT_VERIFICATION_WINDOW_INVALID",
    )

    class ReboundVerifier:
        def verify(self, received):
            assert received == request
            return synthetic_verification(
                VerificationRequest.model_validate(
                    received.model_dump(mode="json") | {"tenant_id": "other-tenant"}
                )
            )

    with pytest.raises(ValueError, match="^COMPOSITE_SUBJECT_VERIFICATION_BINDING_MISMATCH$"):
        require_verification(ReboundVerifier(), request)
    assert finalization.subject == subject


@pytest.mark.parametrize(
    "mutation,code",
    [
        ("business", "COMPOSITE_SUBJECT_DEFINITION_BINDING_MISMATCH"),
        ("window", "COMPOSITE_SUBJECT_PROFILE_BINDING_MISMATCH"),
        ("identity", "COMPOSITE_SUBJECT_PROFILE_BINDING_MISMATCH"),
        ("approval", "COMPOSITE_SUBJECT_ELIGIBILITY_BINDING_MISMATCH"),
    ],
)
def test_valid_reapproved_definition_cannot_change_subject_or_eligibility_join(mutation, code):
    subject, controls, finalization = finalization_material()
    definition = finalization.definition
    require_definition_subject(definition, subject, controls[-1])
    wire = definition.model_dump(mode="json")
    profile = wire["source_authority"]["payload"]
    if mutation == "business":
        wire["display_name"] = "different-name"
    elif mutation == "window":
        profile["effective_to"] = "2026-09-29"
        for selection in profile["selections"]:
            selection["effective_to"] = profile["effective_to"]
        wire["authority_approval"]["claims"]["effective_to"] = profile["effective_to"]
    elif mutation == "identity":
        profile["member_identities"][0]["source_member_id"] = "other-source-account"
    else:
        profile["eligibility_evaluation_binding"]["digest"] = "sha256:" + "0" * 64
        wire["authority_approval"]["claims"]["eligibility_evidence_digest"] = profile[
            "eligibility_evaluation_binding"
        ]["digest"]
    # A fully valid definition and independently recomputed digests establish that
    # the subject join, rather than the V2 schema, rejects the substitution.
    changed = DpmCompositeDefinitionV2.model_validate(
        rebind_definition(wire, refresh_approval=True)
    )
    with pytest.raises(ValueError, match=f"^{code}$"):
        require_definition_subject(changed, subject, controls[-1])
    assert finalization.definition == definition


def test_unqualified_institutional_reference_does_not_qualify_finalization():
    _, _, finalization = finalization_material()
    definition = DpmCompositeDefinitionV2.model_validate(
        institutional_reference_wire(finalization.definition.model_dump(mode="json"))
    )
    wire = finalization.model_dump(mode="json") | {
        "definition": definition.model_dump(mode="json"),
        "content_hash": "",
        "verifications": [
            synthetic_verification(request).model_dump(mode="json")
            for request in finalization_verification_requests(definition, finalization.subject)
        ],
    }
    assert_domain_refusal(
        SubjectFinalization, wire, "COMPOSITE_SUBJECT_INSTITUTIONAL_VERIFICATION_UNAVAILABLE"
    )


@pytest.mark.parametrize(
    "case,code",
    [
        ("incomplete", "COMPOSITE_ELIGIBILITY_PUBLICATION_UNIVERSE_INCOMPLETE"),
        ("unfinished-month", "COMPOSITE_ELIGIBILITY_PUBLICATION_SOURCE_NOT_FINALIZED"),
    ],
)
def test_valid_recomputed_proposal_cannot_publish_incomplete_or_unfinished_source(case, code):
    subject, controls, _ = finalization_material()
    original = controls[2]
    assert (
        initial_projection(
            original, controls[-1].claims_digest, controls[-1].approved_by, controls[-1].approved_at
        )[0].content_hash
        == controls[-1].membership_content_hash
    )
    universe = subject.universe.model_dump(mode="json") | {"content_hash": ""}
    if case == "incomplete":
        universe["posture"] = "INCOMPLETE"
    changed_subject = EligibilitySubject.model_validate(
        subject.model_dump(mode="json")
        | {"universe": CandidateUniverse.model_validate(universe), "content_hash": ""}
    )
    proposal = SubjectPolicyProposal(subject=changed_subject, proposal=controls[0].proposal)
    request = controls[1].verification.request.model_dump(mode="json") | {
        "subject_content_hash": changed_subject.content_hash,
        "claims_digest": independent_digest(
            {
                "subject_content_hash": changed_subject.content_hash,
                "approval_content_hash": controls[1].approval.content_hash,
            }
        ),
    }
    policy = SubjectPolicyApproval(
        proposal=proposal,
        approval=controls[1].approval,
        verification=synthetic_verification(VerificationRequest.model_validate(request)),
    )
    observations_wire = original.observations.model_dump(mode="json")
    if case == "unfinished-month":
        observations_wire["source_generated_at"] = "2026-09-30T23:59:59.000000Z"
    observations = MonthlyEligibilityObservations.model_validate(observations_wire)
    evaluation = evaluate_monthly_eligibility(
        policy.approval.proposal.policy,
        observations,
        evaluated_at=original.proposed_at,
        universe_content_hash=changed_subject.universe.content_hash,
    )
    wire = original.model_dump(mode="json") | {
        "policy_approval": policy,
        "observations": observations,
        "evaluation": evaluation,
        "content_hash": "",
    }
    wire["observation_binding"]["content_hash"] = independent_digest(
        observations.model_dump(mode="json")
    )
    changed = SubjectEvaluationProposal.model_validate(wire)
    claims = subject_approval_claims(changed, controls[-1].approved_by, controls[-1].approved_at)
    with pytest.raises(ValueError, match=f"^{code}$"):
        initial_projection(changed, claims, controls[-1].approved_by, controls[-1].approved_at)
