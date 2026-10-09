"""Individually valid proposed inputs cannot change the approved monthly policy or population."""

import pytest

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.approval import MonthlyPolicyApproval, MonthlyPolicyProposal
from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility
from src.core.composite_eligibility.monthly_amendment import MonthlyAmendmentProposal
from src.core.composite_eligibility.monthly_authority import require_source_correction
from src.core.composite_eligibility.policy import resolve_monthly_policy
from src.core.composite_eligibility.source_assembly import (
    MonthlySourceAssembly,
    VerifiedMonthlySourceAssembly,
    assembly_verification_request,
)
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.infrastructure.composites.in_memory import InMemoryDpmCompositeRepository
from tests.composite_monthly_amendment_helpers import (
    corrected_monthly_proposal,
    seed_complete_monthly_root,
)
from tests.composite_staged_eligibility_helpers import synthetic_verification


def material():
    repository = InMemoryDpmCompositeRepository()
    _, original, parent = seed_complete_monthly_root(repository)
    proposal = corrected_monthly_proposal(original, parent, sequence=original.publication_sequence)
    return repository, original, parent, proposal


def test_new_source_generation_time_alone_is_not_a_source_correction():
    repository, original, parent, _ = material()
    proposal = corrected_monthly_proposal(
        original,
        parent,
        sequence=original.publication_sequence,
        cash="50",
        source_revision_override=original.approval.proposal.observations.source_revision,
    )
    assert (
        proposal.observations.source_generated_at
        != original.approval.proposal.observations.source_generated_at
    )
    repository.save_universe_attestation(attestation=proposal.universe)
    with pytest.raises(ValueError, match="SOURCE_UNCHANGED"):
        repository.save_monthly_evaluation_proposal(proposal=proposal)


def test_an_independently_hash_valid_changed_policy_is_not_source_correction_authority():
    _, original, _, proposal = material()
    old = proposal.policy_approval
    policy = old.proposal.policy
    layers = [item.model_copy(update={"cash_threshold": "0.04"}) for item in policy.layers]
    resolved = resolve_monthly_policy(layers, month=policy.month, scope=policy.scope)
    changed_proposal = MonthlyPolicyProposal.model_validate(
        old.proposal.model_dump(mode="json") | {"policy": resolved, "content_hash": ""}
    )
    changed = MonthlyPolicyApproval.model_validate(
        old.model_dump(mode="json") | {"proposal": changed_proposal, "content_hash": ""}
    )
    evaluation = evaluate_monthly_eligibility(
        resolved,
        proposal.observations,
        evaluated_at=proposal.proposed_at,
        universe_content_hash=proposal.universe.content_hash,
    )
    invalid = MonthlyAmendmentProposal.model_validate(
        proposal.model_dump(mode="json")
        | {"policy_approval": changed, "evaluation": evaluation, "content_hash": ""}
    )
    with pytest.raises(ValueError, match="POLICY_CHANGE_UNSUPPORTED"):
        require_source_correction(invalid, original.approval)


def test_changed_expected_population_cannot_use_the_source_correction_profile():
    _, original, _, proposal = material()
    assembly_wire = proposal.source_assembly_evidence.assembly.model_dump(mode="json")
    assembly_wire["observations"]["expected_portfolio_ids"].append("synthetic-other")
    assembly_wire["compatibility_binding"]["digest"] = hash_canonical_payload(
        {"observations": assembly_wire["observations"], "inputs": assembly_wire["inputs"]}
    )
    assembly = MonthlySourceAssembly.model_validate(assembly_wire)
    evidence = VerifiedMonthlySourceAssembly(
        assembly=assembly,
        verification=synthetic_verification(assembly_verification_request(assembly)),
    )
    universe_wire = proposal.universe.model_dump(mode="json")
    universe_wire.update(
        expected_portfolio_ids=assembly.observations.expected_portfolio_ids,
        expected_portfolio_count=2,
        posture="INCOMPLETE",
        missing_portfolio_ids=["synthetic-other"],
        reason_code="EXPECTED_POPULATION_CHANGED",
        content_hash="",
    )
    product = next(
        item
        for item in universe_wire["source_products"]
        if item["product_name"] == assembly.observations.product_name
    )
    product["content_hash"] = hash_canonical_payload(assembly_wire["observations"])
    universe = DpmCompositeUniverseAttestation.model_validate(universe_wire)
    evaluation = evaluate_monthly_eligibility(
        proposal.policy_approval.proposal.policy,
        assembly.observations,
        evaluated_at=proposal.proposed_at,
        universe_content_hash=universe.content_hash,
    )
    invalid = MonthlyAmendmentProposal.model_validate(
        proposal.model_dump(mode="json")
        | {
            "observations": assembly.observations,
            "source_assembly_evidence": evidence,
            "universe": universe,
            "evaluation": evaluation,
            "content_hash": "",
        }
    )
    with pytest.raises(ValueError, match="POPULATION_CHANGE_UNSUPPORTED"):
        require_source_correction(invalid, original.approval)


@pytest.mark.parametrize("fault", ["no_root", "two_roots", "duplicate", "original", "predecessor"])
def test_retained_authority_graph_refuses_ambiguous_or_missing_custody(fault):
    from src.core.composite_eligibility.monthly_authority import selected_monthly_approval
    from src.core.composite_eligibility.publication import build_monthly_publication

    _, original, parent, proposal = material()
    if fault in {"original", "predecessor"}:
        wire = proposal.model_dump(mode="json")
        claims = wire["amendment"]
        field = (
            "original_approval_binding" if fault == "original" else "predecessor_approval_binding"
        )
        claims[field]["digest"] = "sha256:" + "a" * 64
        if fault == "predecessor":
            claims["expected_authority_binding"] = claims[field].copy()
        proposal = MonthlyAmendmentProposal.model_validate(wire | {"content_hash": ""})
    checked = build_monthly_publication(
        proposal, parent, approved_by="synthetic-checker", approved_at=proposal.proposed_at
    )[0]
    valid = [original.approval, checked]
    scope = (
        proposal.policy_approval.proposal.policy.scope.tenant_id,
        proposal.policy_approval.proposal.policy.scope.composite_id,
        proposal.policy_approval.proposal.policy.scope.definition_version,
    )
    if fault == "no_root":
        invalid, code = [checked], "ROOT_AMBIGUOUS"
    elif fault == "two_roots":
        invalid, code = [original.approval, original.approval], "ROOT_AMBIGUOUS"
    elif fault == "duplicate":
        invalid, code = valid + [checked], "RECORD_AMBIGUOUS"
    else:
        invalid, code = valid, fault.upper() + "_MISMATCH"
    with pytest.raises(ValueError, match=code):
        selected_monthly_approval(invalid, scope=scope, month=proposal.evaluation.month)
    if fault not in {"original", "predecessor"}:
        assert (
            selected_monthly_approval(valid, scope=scope, month=proposal.evaluation.month)
            == checked
        )
