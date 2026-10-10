"""Project one approved month into the existing immutable membership wire."""

from datetime import date, datetime, timedelta

from src.core.composite_eligibility.evaluation_control import (
    monthly_evaluation_approval_claims_hash,
)
from src.core.composite_eligibility.monthly_amendment import (
    MonthlyAmendmentProposalContent as MonthlyAmendmentProposal,
    MonthlyApproval,
    MonthlyProposal,
    decode_monthly_proposal,
    decode_monthly_approval,
)
from src.core.composite_eligibility.historical_policy import HistoricalPolicyVerification
from src.core.composite_eligibility.policy import month_window
from src.core.composite_eligibility.evaluation import MonthlyEligibilityEvaluation
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations
from src.core.composite_membership import (
    DpmCompositeMembershipDecision,
    DpmCompositeMembershipRevision,
)
from src.core.composite_universe import (
    DpmCompositeUniverseAttestation,
    DpmCompositeUniverseSourceProduct,
)
from src.core.composite_universe_resolution import reconcile_composite_universe


def build_monthly_publication(
    proposal: MonthlyProposal,
    parent: DpmCompositeMembershipRevision,
    *,
    approved_by: str,
    approved_at: str,
    operation_verification: HistoricalPolicyVerification | None = None,
) -> tuple[MonthlyApproval, DpmCompositeMembershipRevision, DpmCompositeUniverseAttestation]:
    proposal = decode_monthly_proposal(proposal.model_dump(mode="json"))
    parent = DpmCompositeMembershipRevision.model_validate(parent.model_dump(mode="json"))
    _require_publishable_month(proposal, parent)
    first_text, last_text = month_window(proposal.evaluation.month)
    first, last = date.fromisoformat(first_text), date.fromisoformat(last_text)
    claims = monthly_evaluation_approval_claims_hash(
        proposal, approved_by=approved_by, approved_at=approved_at
    )
    decisions = _retain_outside_month(parent.decisions, first, last)
    decisions.extend(
        monthly_decisions(proposal.evaluation, proposal.observations, claims, first_text, last_text)
    )
    decisions.sort(key=lambda item: (item.portfolio_id, item.effective_from))
    scope = proposal.policy_approval.proposal.policy.scope
    revision = DpmCompositeMembershipRevision(
        tenant_id=scope.tenant_id,
        composite_id=scope.composite_id,
        definition_version=scope.definition_version,
        membership_revision=proposal.target_membership_revision,
        policy_version=proposal.policy_approval.proposal.eligibility_policy_version,
        source_cut_id=proposal.universe.source_cut_id,
        decisions=decisions,
        decided_by=approved_by,
        decided_at=datetime.fromisoformat(approved_at),
        correlation_id=proposal.correlation_id,
        supersedes_membership_revision=parent.membership_revision,
        affected_from=first_text,
        affected_to=last_text,
    )
    universe = _published_universe(proposal, revision, approved_by, approved_at)
    approval = _projected_approval(
        proposal,
        approved_by,
        approved_at,
        claims,
        revision.content_hash,
        universe.content_hash,
        operation_verification,
    )
    if proposal.publication_evidence_version == "v1":
        linked = _published_universe(
            proposal, revision, approved_by, approved_at, approval_digest=approval.content_hash
        )
        # Legacy universe hashing omits nested content_hash. Explicit receipt admission
        # must verify the locator digest; the outer universe hash alone cannot protect it.
        if linked.content_hash != universe.content_hash:
            raise ValueError("COMPOSITE_ELIGIBILITY_PUBLICATION_LOCATOR_HASH_CYCLE")
        universe = linked
    return approval, revision, universe


def _projected_approval(
    proposal: MonthlyProposal,
    actor: str,
    instant: str,
    claims: str,
    membership_hash: str,
    universe_hash: str,
    operation_verification: HistoricalPolicyVerification | None,
) -> MonthlyApproval:
    wire = {
        "proposal": proposal.model_dump(mode="json"),
        "approved_by": actor,
        "approved_at": instant,
        "claims_digest": claims,
        "membership_content_hash": membership_hash,
        "published_universe_content_hash": universe_hash,
    }
    wire["product_version"] = proposal.product_version
    if operation_verification is not None:
        wire["operation_verification"] = operation_verification.model_dump(mode="json")
    return decode_monthly_approval(wire)


def _require_publishable_month(
    proposal: MonthlyProposal, parent: DpmCompositeMembershipRevision
) -> None:
    if (parent.membership_revision, parent.content_hash) != (
        proposal.parent_membership_revision,
        proposal.parent_membership_content_hash,
    ):
        raise ValueError("COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP")
    if isinstance(proposal, MonthlyAmendmentProposal):
        proposal.require_parent_clock(parent.decided_at)
    if (
        proposal.universe.posture != "COMPLETE"
        or proposal.evaluation.declared_universe_coverage != "COMPLETE"
    ):
        raise ValueError("COMPOSITE_ELIGIBILITY_PUBLICATION_UNIVERSE_INCOMPLETE")
    first, last = month_window(proposal.evaluation.month)
    if datetime.fromisoformat(proposal.observations.source_generated_at).date().isoformat() <= last:
        raise ValueError("COMPOSITE_ELIGIBILITY_PUBLICATION_SOURCE_NOT_FINALIZED")
    observed, missing, unexpected, gaps = reconcile_composite_universe(
        revision=parent,
        coverage_from=date.fromisoformat(first),
        coverage_to=date.fromisoformat(last),
        expected_portfolio_ids=proposal.universe.expected_portfolio_ids,
    )
    if missing or unexpected or gaps or observed != proposal.observations.expected_portfolio_ids:
        raise ValueError("COMPOSITE_ELIGIBILITY_PUBLICATION_UNIVERSE_INCOMPLETE")


def _retain_outside_month(
    decisions: list[DpmCompositeMembershipDecision],
    first: date,
    last: date,
) -> list[DpmCompositeMembershipDecision]:
    retained = []
    for decision in decisions:
        start = date.fromisoformat(decision.effective_from)
        end = date.fromisoformat(decision.effective_to) if decision.effective_to else date.max
        if start > last or end < first:
            retained.append(decision.model_copy(deep=True))
            continue
        if start < first:
            retained.append(
                decision.model_copy(
                    update={"effective_to": (first - timedelta(days=1)).isoformat()}, deep=True
                )
            )
        if end > last:
            retained.append(
                decision.model_copy(
                    update={"effective_from": (last + timedelta(days=1)).isoformat()}, deep=True
                )
            )
    return retained


def monthly_decisions(
    evaluation: MonthlyEligibilityEvaluation,
    snapshot: MonthlyEligibilityObservations,
    claims_digest: str,
    first: str,
    last: str,
) -> list[DpmCompositeMembershipDecision]:
    observations = {item.portfolio_id: item for item in snapshot.portfolios}
    decisions = []
    for result in evaluation.portfolios:
        observation = observations[result.portfolio_id]
        if observation.discretionary is None:
            # Legacy wire cannot represent unknown discretionary status. Never manufacture a bool.
            raise ValueError("COMPOSITE_ELIGIBILITY_DISCRETIONARY_FACT_UNAVAILABLE")
        reasons = [
            reason
            for assessment in result.assessments
            for reason in (
                assessment.failure_reasons
                if result.status == "EXCLUDED"
                else assessment.unknown_reasons
            )
        ]
        decisions.append(
            DpmCompositeMembershipDecision(
                portfolio_id=result.portfolio_id,
                effective_from=first,
                effective_to=last,
                status=result.status,
                reason_code=None if result.status == "INCLUDED" else reasons[0],
                discretionary=observation.discretionary,
                approval_ref=claims_digest,
                source_snapshot_id=evaluation.content_hash,
            )
        )
    return decisions


def _published_universe(
    proposal: MonthlyProposal,
    revision: DpmCompositeMembershipRevision,
    approved_by: str,
    approved_at: str,
    *,
    approval_digest: str = "sha256:" + "0" * 64,
) -> DpmCompositeUniverseAttestation:
    first, last = month_window(proposal.evaluation.month)
    expected = proposal.observations.expected_portfolio_ids
    observed, missing, unexpected, gaps = reconcile_composite_universe(
        revision=revision,
        coverage_from=date.fromisoformat(first),
        coverage_to=date.fromisoformat(last),
        expected_portfolio_ids=expected,
    )
    if missing or unexpected or gaps:
        raise ValueError("COMPOSITE_ELIGIBILITY_PROJECTED_UNIVERSE_MISMATCH")
    products = list(proposal.universe.source_products)
    if proposal.publication_evidence_version == "v1":
        # The retained input stays immutable. The output names only its own month's
        # approval rather than inheriting a previous month's locator on the same cut.
        products = [
            item
            for item in products
            if not (
                item.owner_service == "lotus-manage"
                and item.product_name == "CompositeMonthlyEvaluationApproval"
            )
        ]
        products.append(
            DpmCompositeUniverseSourceProduct(
                owner_service="lotus-manage",
                product_name="CompositeMonthlyEvaluationApproval",
                contract_version=proposal.product_version,
                authority_scope="POLICY_INPUT",
                source_cut_id=revision.source_cut_id,
                source_watermark=proposal.evaluation_revision,
                content_hash=approval_digest,
            )
        )
    return DpmCompositeUniverseAttestation(
        tenant_id=revision.tenant_id,
        composite_id=revision.composite_id,
        definition_version=revision.definition_version,
        membership_revision=revision.membership_revision,
        membership_content_hash=revision.content_hash,
        attestation_version=proposal.evaluation_revision,
        coverage_from=first,
        coverage_to=last,
        policy_version=revision.policy_version,
        source_cut_id=revision.source_cut_id,
        source_products=products,
        posture="COMPLETE",
        expected_portfolio_ids=expected,
        expected_portfolio_count=len(expected),
        observed_portfolio_count=len(observed),
        attested_at=datetime.fromisoformat(approved_at),
        attested_by=approved_by,
        correlation_id=proposal.correlation_id,
    )
