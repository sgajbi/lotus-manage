"""Explicit synthetic correction material; never institutional source or checker authority."""

from datetime import datetime, timedelta, timezone

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility
from src.core.composite_eligibility.evaluation_control import MonthlyEvaluationProposal
from src.core.composite_eligibility.monthly_amendment import MonthlyAmendmentProposal
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations
from src.core.composite_eligibility.source_assembly import (
    MonthlySourceAssembly,
    VerifiedMonthlySourceAssembly,
    assembly_verification_request,
)
from src.core.composite_universe import DpmCompositeUniverseAttestation
from src.core.composite_eligibility.publication import build_monthly_publication
from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
    MonthlyApprovalRequest,
    MonthlyProposalRequest,
)
from tests.composite_monthly_eligibility_helpers import retained_repository, source_snapshot
from tests.composite_monthly_eligibility_helpers import prospective_proposal_body
from tests.composite_monthly_source_helpers import assembly_material
from tests.composite_monthly_v2_helpers import synthetic_monthly_v2_definition
from tests.composite_staged_eligibility_helpers import lifecycle_material, synthetic_verification


def seed_complete_monthly_root(
    repository,
    *,
    definition_product_version="v1",
    coverage_to="2026-09-30",
    approved_at=None,
    parent_decided_at=None,
):
    snapshot = source_snapshot()
    retained, universe = retained_repository(snapshot, coverage_to=coverage_to)
    scope = dict(
        tenant_id=snapshot.tenant_id,
        composite_id=snapshot.composite_id,
        definition_version=snapshot.definition_version,
    )
    definition = retained.get_definition(**scope)
    if parent_decided_at is not None:
        definition = type(definition).model_validate(
            definition.model_dump(mode="json")
            | {"created_at": parent_decided_at, "content_hash": ""}
        )
    if definition_product_version == "v2":
        definition = synthetic_monthly_v2_definition(definition)
    parent = retained.get_membership_revision(**scope, membership_revision="synthetic-membership")
    if parent_decided_at is not None:
        parent = type(parent).model_validate(
            parent.model_dump(mode="json") | {"decided_at": parent_decided_at, "content_hash": ""}
        )
        universe = type(universe).model_validate(
            universe.model_dump(mode="json")
            | {"membership_content_hash": parent.content_hash, "content_hash": ""}
        )
    repository.save_definition(definition=definition)
    repository.save_membership_revision(revision=parent)
    repository.save_universe_attestation(attestation=universe)
    _, _, policy, policy_approval, *_ = lifecycle_material()
    repository.save_monthly_policy_proposal(proposal=policy.proposal)
    repository.save_monthly_policy_approval(approval=policy_approval.approval)
    _, assembly_wire = assembly_material()
    assembly = MonthlySourceAssembly.model_validate(assembly_wire)
    evidence = VerifiedMonthlySourceAssembly(
        assembly=assembly,
        verification=synthetic_verification(assembly_verification_request(assembly)),
    )
    instant = "2026-10-01T01:00:00.000000Z"
    proposal = MonthlyEvaluationProposal(
        evaluation_revision="synthetic.original.evaluation.r1",
        target_membership_revision="synthetic.original.membership.r1",
        parent_membership_revision=parent.membership_revision,
        parent_membership_content_hash=parent.content_hash,
        policy_approval=policy_approval.approval,
        universe=universe,
        observations=snapshot,
        source_assembly_evidence=evidence,
        publication_evidence_version="v1",
        evaluation=evaluate_monthly_eligibility(
            policy.proposal.policy,
            snapshot,
            evaluated_at=instant,
            universe_content_hash=universe.content_hash,
        ),
        proposed_by="synthetic-original-maker",
        proposed_at=instant,
        correlation_id="synthetic-original-month",
    )
    repository.save_monthly_evaluation_proposal(proposal=proposal)
    approval, member, _ = build_monthly_publication(
        proposal,
        parent,
        approved_by="synthetic-original-checker",
        approved_at=approved_at or instant,
    )
    repository.save_monthly_evaluation_approval(approval=approval)
    receipt = repository.resolve_monthly_eligibility_evidence(
        **scope,
        evaluation_revision=proposal.evaluation_revision,
        approval_content_hash=approval.content_hash,
    )
    return scope, receipt, member


def retain_following_month(repository, original, parent):
    """Explicit fictional October history, solely for dependent-month refusal tests."""
    prior = original.approval.proposal
    policy_scope = prior.policy_approval.proposal.policy.scope
    scope = dict(
        tenant_id=policy_scope.tenant_id,
        composite_id=policy_scope.composite_id,
        definition_version=policy_scope.definition_version,
    )
    assembly_wire = prior.source_assembly_evidence.assembly.model_dump(mode="json")
    observations = assembly_wire["observations"]
    instant = "2026-11-01T01:00:00.000000Z"
    observations.update(
        month="2026-10",
        source_revision="synthetic.october.source.r1",
        source_generated_at="2026-11-01T00:00:00.000000Z",
    )
    facts = observations["portfolios"][0]
    facts.update(
        prior_assets_as_of="2026-09-30",
        cash_as_of="2026-10-31",
        readiness_as_of="2026-10-31",
        flow_coverage_from="2026-10-01",
        flow_coverage_to="2026-10-31",
    )
    for flow in facts["flows"]:
        flow.update(business_date="2026-10-15", received_at=observations["source_generated_at"])
    assembly_wire["compatibility_binding"]["digest"] = hash_canonical_payload(
        {"observations": observations, "inputs": assembly_wire["inputs"]}
    )
    assembly = MonthlySourceAssembly.model_validate(assembly_wire)
    evidence = VerifiedMonthlySourceAssembly(
        assembly=assembly,
        verification=synthetic_verification(assembly_verification_request(assembly)),
    )
    universe_wire = prior.universe.model_dump(mode="json")
    universe_wire.update(
        membership_revision=parent.membership_revision,
        membership_content_hash=parent.content_hash,
        content_hash="",
        attestation_version="synthetic.october.input.r1",
        coverage_from="2026-10-01",
        coverage_to="2026-10-31",
    )
    product = next(
        item
        for item in universe_wire["source_products"]
        if item["product_name"] == assembly.observations.product_name
    )
    product.update(
        source_watermark=assembly.observations.source_revision,
        content_hash=hash_canonical_payload(observations),
    )
    universe = DpmCompositeUniverseAttestation.model_validate(universe_wire)
    repository.save_universe_attestation(attestation=universe)
    service = CompositeMonthlyEligibilityApplicationService(
        repository=repository, clock=lambda: "2026-09-20T01:00:00.000000Z"
    )
    body = prospective_proposal_body(universe)
    body["layers"][0]["effective_from"] = "2026-10-01"
    policy = service.propose_policy(
        **scope,
        month="2026-10",
        proposal_revision="synthetic.october.policy.r1",
        actor_id="synthetic-october-maker",
        command=MonthlyProposalRequest.model_validate(body),
    )
    policy_approval = service.approve_policy(
        **scope,
        month="2026-10",
        proposal_revision=policy.proposal_revision,
        actor_id="synthetic-october-checker",
        command=MonthlyApprovalRequest(expected_proposal_content_hash=policy.content_hash),
    )
    proposal = MonthlyEvaluationProposal(
        evaluation_revision="synthetic.october.evaluation.r1",
        target_membership_revision="synthetic.october.membership.r1",
        parent_membership_revision=parent.membership_revision,
        parent_membership_content_hash=parent.content_hash,
        policy_approval=policy_approval,
        universe=universe,
        observations=assembly.observations,
        source_assembly_evidence=evidence,
        publication_evidence_version="v1",
        evaluation=evaluate_monthly_eligibility(
            policy_approval.proposal.policy,
            assembly.observations,
            evaluated_at=instant,
            universe_content_hash=universe.content_hash,
        ),
        proposed_by="synthetic-october-maker",
        proposed_at=instant,
        correlation_id="synthetic-october-history",
    )
    repository.save_monthly_evaluation_proposal(proposal=proposal)
    approval, member, _ = build_monthly_publication(
        proposal, parent, approved_by="synthetic-october-checker", approved_at=instant
    )
    repository.save_monthly_evaluation_approval(approval=approval)
    return member


def corrected_monthly_proposal(
    receipt,
    parent,
    *,
    sequence,
    cash="100",
    revision=2,
    proposed_at_override=None,
    source_revision_override=None,
    historical_verifier=None,
):
    predecessor = receipt.approval
    prior = predecessor.proposal
    proposed_at = max(
        datetime(2026, 10, 2, 1, tzinfo=timezone.utc),
        datetime.fromisoformat(predecessor.approved_at) + timedelta(hours=1),
        parent.decided_at + timedelta(hours=1),
    )
    if proposed_at_override is not None:
        proposed_at = datetime.fromisoformat(proposed_at_override)
    instant = proposed_at.isoformat(timespec="microseconds").replace("+00:00", "Z")
    wire = prior.observations.model_dump(mode="json")
    wire["source_revision"] = source_revision_override or f"synthetic.corrected.source.r{revision}"
    wire["source_generated_at"] = (
        proposed_at.replace(hour=0, minute=0, second=0, microsecond=0)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )
    wire["portfolios"][0]["settled_unencumbered_cash"] = cash
    observations = MonthlyEligibilityObservations.model_validate(wire)
    assembly_wire = prior.source_assembly_evidence.assembly.model_dump(mode="json")
    assembly_wire["observations"] = observations.model_dump(mode="json")
    cash_input = next(item for item in assembly_wire["inputs"] if item["kind"] == "CASH")
    cash_input["evidence"]["revision"] = f"synthetic.corrected.cash.r{revision}"
    cash_input["evidence"]["digest"] = hash_canonical_payload({"settled_unencumbered_cash": cash})
    assembly_wire["compatibility_binding"]["revision"] = (
        f"synthetic.corrected.compatibility.r{revision}"
    )
    assembly_wire["compatibility_binding"]["digest"] = hash_canonical_payload(
        {
            "observations": assembly_wire["observations"],
            "inputs": assembly_wire["inputs"],
        }
    )
    assembly = MonthlySourceAssembly.model_validate(assembly_wire)
    evidence = VerifiedMonthlySourceAssembly(
        assembly=assembly,
        verification=synthetic_verification(assembly_verification_request(assembly)),
    )
    universe_wire = prior.universe.model_dump(mode="json")
    universe_wire.update(
        membership_revision=parent.membership_revision,
        membership_content_hash=parent.content_hash,
        attestation_version=f"synthetic.corrected.input.r{revision}",
        content_hash="",
    )
    product = next(
        item
        for item in universe_wire["source_products"]
        if item["product_name"] == observations.product_name
    )
    product.update(
        source_watermark=observations.source_revision,
        content_hash=hash_canonical_payload(observations.model_dump(mode="json")),
    )
    universe = DpmCompositeUniverseAttestation.model_validate(universe_wire)
    predecessor_binding = {
        "product_name": predecessor.product_name,
        "product_version": predecessor.product_version,
        "revision": prior.evaluation_revision,
        "digest": predecessor.content_hash,
    }
    wire = dict(
        evaluation_revision=f"synthetic.corrected.evaluation.r{revision}",
        target_membership_revision=f"synthetic.corrected.membership.r{revision}",
        parent_membership_revision=parent.membership_revision,
        parent_membership_content_hash=parent.content_hash,
        policy_approval=prior.policy_approval,
        universe=universe,
        observations=observations,
        source_assembly_evidence=evidence,
        publication_evidence_version="v1",
        evaluation=evaluate_monthly_eligibility(
            prior.policy_approval.proposal.policy,
            observations,
            evaluated_at=instant,
            universe_content_hash=universe.content_hash,
        ),
        proposed_by="synthetic-correction-maker",
        proposed_at=instant,
        correlation_id="synthetic-source-correction",
        amendment={
            "correction_kind": "SOURCE_CORRECTION",
            "predecessor_approval_binding": predecessor_binding,
            "expected_authority_binding": predecessor_binding,
            "original_approval_binding": (
                prior.amendment.original_approval_binding
                if isinstance(prior, MonthlyAmendmentProposal)
                else predecessor_binding
            ),
            "predecessor_receipt_binding": {
                "product_name": receipt.product_name,
                "product_version": receipt.product_version,
                "revision": prior.evaluation_revision,
                "digest": receipt.content_hash,
            },
            "projection_parent_membership_binding": {
                "product_name": "CompositeMembership",
                "product_version": "v1",
                "revision": parent.membership_revision,
                "digest": parent.content_hash,
            },
            "expected_current_publication_sequence": sequence,
            "affected_from": "2026-09-01",
            "affected_to": "2026-09-30",
            "reason_code": "SOURCE_CASH_CORRECTION",
            "reason": "Synthetic source owner corrected September settled unencumbered cash.",
            "evidence_bindings": [cash_input["evidence"]],
        },
    )
    if historical_verifier is None:
        return MonthlyAmendmentProposal(**wire)
    import json
    from src.core.composite_eligibility.monthly_amendment import (
        HistoricalMonthlyAmendmentProposal,
        MonthlyAmendmentProposalContent,
    )
    from src.core.composite_eligibility.historical_policy import HistoricalPolicyVerificationRequest

    if isinstance(prior, MonthlyAmendmentProposalContent):
        wire["amendment"]["original_approval_binding"] = prior.amendment.original_approval_binding
    wire["product_version"] = "v4"
    raw = json.loads(json.dumps(wire, default=lambda item: item.model_dump(mode="json")))
    raw = MonthlyAmendmentProposalContent.model_validate(raw).model_dump(
        mode="json", exclude={"content_hash"}
    )
    initial = prior.policy_approval.verification.request.model_dump(mode="json")
    request = HistoricalPolicyVerificationRequest.model_validate(
        initial
        | {
            "operation": "EVALUATION_PROPOSAL",
            "revision": wire["evaluation_revision"],
            "actor_id": wire["proposed_by"],
            "requested_at": instant,
            "intent_digest": hash_canonical_payload(raw),
        }
    )
    return HistoricalMonthlyAmendmentProposal.model_validate(
        raw | {"operation_verification": historical_verifier.verify(request)}
    )
