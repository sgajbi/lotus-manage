"""Approved-policy evaluation and independent, atomic canonical membership publication."""

from dataclasses import dataclass

from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
    MonthlyApprovalRequest,
    MonthlySimulationRequest,
)
from src.core.composite_authority_models import Digest, Identity, StrictAuthorityModel
from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility
from src.core.composite_eligibility.evaluation_control import (
    MonthlyEvaluationApproval,
    MonthlyEvaluationProposal,
)
from src.core.composite_eligibility.publication import build_monthly_publication
from src.core.composite_repository import DpmCompositeConflictError


class MonthlyEvaluationRequest(StrictAuthorityModel):
    month: str
    policy_approval_content_hash: Digest
    parent_membership_revision: Identity
    parent_membership_content_hash: Digest
    attestation_version: Identity
    universe_content_hash: Digest
    target_membership_revision: Identity
    correlation_id: Identity


@dataclass(frozen=True)
class CompositeMonthlyEvaluationApplicationService:
    configuration: CompositeMonthlyEligibilityApplicationService

    def get_proposal(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
    ) -> MonthlyEvaluationProposal:
        result = self.configuration.repository.get_monthly_evaluation_proposal(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            evaluation_revision=evaluation_revision,
        )
        if result is None:
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_NOT_FOUND")
        return result

    def get_approval(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
    ) -> MonthlyEvaluationApproval:
        result = self.configuration.repository.get_monthly_evaluation_approval(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            evaluation_revision=evaluation_revision,
        )
        if result is None:
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_APPROVAL_NOT_FOUND")
        return result

    def propose(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
        actor_id: str,
        command: MonthlyEvaluationRequest,
    ) -> MonthlyEvaluationProposal:
        command = MonthlyEvaluationRequest.model_validate(command.model_dump(mode="json"))
        repository = self.configuration.repository
        retained = repository.get_monthly_evaluation_proposal(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            evaluation_revision=evaluation_revision,
        )
        if retained is not None:
            _require_same_proposal_command(retained, command, actor_id)
            return retained
        policy = repository.get_monthly_policy_approval(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=command.month,
        )
        if policy is None:
            raise ValueError("COMPOSITE_ELIGIBILITY_APPROVED_POLICY_NOT_FOUND")
        if policy.content_hash != command.policy_approval_content_hash:
            raise ValueError("COMPOSITE_ELIGIBILITY_APPROVED_POLICY_MISMATCH")
        parent = repository.get_membership_revision(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=command.parent_membership_revision,
        )
        if parent is None or parent.content_hash != command.parent_membership_content_hash:
            raise ValueError("COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP")
        definition = repository.get_definition(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
        )
        if definition is None:
            raise ValueError("COMPOSITE_DEFINITION_NOT_FOUND")
        request = MonthlySimulationRequest(
            month=command.month,
            layers=policy.proposal.policy.layers,
            membership_revision=command.parent_membership_revision,
            attestation_version=command.attestation_version,
            universe_content_hash=command.universe_content_hash,
        )
        observations, universe = self.configuration.resolve_source_inputs(
            policy.proposal.policy,
            request,
            reporting_currency=definition.reporting_currency,
        )
        instant = self.configuration.clock()
        evaluation = evaluate_monthly_eligibility(
            policy.proposal.policy,
            observations,
            evaluated_at=instant,
            universe_content_hash=universe.content_hash,
        )
        proposal = MonthlyEvaluationProposal(
            evaluation_revision=evaluation_revision,
            target_membership_revision=command.target_membership_revision,
            parent_membership_revision=parent.membership_revision,
            parent_membership_content_hash=parent.content_hash,
            policy_approval=policy,
            universe=universe,
            observations=observations,
            evaluation=evaluation,
            proposed_by=actor_id,
            proposed_at=instant,
            correlation_id=command.correlation_id,
        )
        try:
            repository.save_monthly_evaluation_proposal(proposal=proposal)
        except DpmCompositeConflictError:
            winner = repository.get_monthly_evaluation_proposal(
                tenant_id=tenant_id,
                composite_id=composite_id,
                definition_version=definition_version,
                evaluation_revision=evaluation_revision,
            )
            if winner is None:
                raise
            _require_same_proposal_command(winner, command, actor_id)
            return winner
        return proposal

    def approve(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        evaluation_revision: str,
        actor_id: str,
        command: MonthlyApprovalRequest,
    ) -> MonthlyEvaluationApproval:
        command = MonthlyApprovalRequest.model_validate(command.model_dump(mode="json"))
        proposal = self.get_proposal(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            evaluation_revision=evaluation_revision,
        )
        if proposal.content_hash != command.expected_proposal_content_hash:
            raise ValueError("COMPOSITE_ELIGIBILITY_STALE_PROPOSAL")
        if actor_id == proposal.proposed_by:
            raise ValueError("COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN")
        repository = self.configuration.repository
        retained = repository.get_monthly_evaluation_approval(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            evaluation_revision=evaluation_revision,
        )
        if retained is not None:
            _require_same_approval(retained, proposal, actor_id)
            return retained
        parent = repository.get_membership_revision(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            membership_revision=proposal.parent_membership_revision,
        )
        if parent is None:
            raise ValueError("COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP")
        approval, _, _ = build_monthly_publication(
            proposal, parent, approved_by=actor_id, approved_at=self.configuration.clock()
        )
        try:
            repository.save_monthly_evaluation_approval(approval=approval)
        except DpmCompositeConflictError:
            winner = repository.get_monthly_evaluation_approval(
                tenant_id=tenant_id,
                composite_id=composite_id,
                definition_version=definition_version,
                evaluation_revision=evaluation_revision,
            )
            if winner is None:
                raise
            _require_same_approval(winner, proposal, actor_id)
            return winner
        return approval


def _require_same_proposal_command(
    proposal: MonthlyEvaluationProposal, command: MonthlyEvaluationRequest, actor_id: str
) -> None:
    if (
        proposal.evaluation.month,
        proposal.policy_approval.content_hash,
        proposal.parent_membership_revision,
        proposal.parent_membership_content_hash,
        proposal.universe.attestation_version,
        proposal.universe.content_hash,
        proposal.target_membership_revision,
        proposal.correlation_id,
        proposal.proposed_by,
    ) != (
        command.month,
        command.policy_approval_content_hash,
        command.parent_membership_revision,
        command.parent_membership_content_hash,
        command.attestation_version,
        command.universe_content_hash,
        command.target_membership_revision,
        command.correlation_id,
        actor_id,
    ):
        raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_IMMUTABLE_CONFLICT")


def _require_same_approval(
    approval: MonthlyEvaluationApproval, proposal: MonthlyEvaluationProposal, actor_id: str
) -> None:
    if approval.proposal.content_hash != proposal.content_hash or approval.approved_by != actor_id:
        raise ValueError("COMPOSITE_ELIGIBILITY_ACTIVE_EVALUATION_CONFLICT")
