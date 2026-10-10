"""Approved-policy evaluation and independent, atomic canonical membership publication."""

from dataclasses import dataclass

from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
    MonthlyApprovalRequest,
    MonthlySimulationRequest,
)
from src.core.composite_authority_models import (
    Digest,
    Identity,
    StrictAuthorityModel,
)
from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.evaluation_control import MonthlyEvaluationProposalContent
from src.core.composite_eligibility.historical_policy import (
    HistoricalMonthlyPolicyApproval,
    HistoricalPolicyVerificationRequest,
    admitted_historical_policy,
)
from src.core.composite_eligibility.monthly_amendment import (
    MonthlyAmendmentProposalContent as MonthlyAmendmentProposal,
    MonthlyAmendmentProposalContent,
    MonthlyApproval,
    MonthlyProposal,
    MonthlySourceAmendment,
    HistoricalMonthlySourceAmendment,
    decode_monthly_proposal,
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


class MonthlyAmendmentRequest(MonthlyEvaluationRequest):
    amendment: MonthlySourceAmendment | HistoricalMonthlySourceAmendment


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
    ) -> MonthlyProposal:
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
    ) -> MonthlyApproval:
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
        command: MonthlyEvaluationRequest | MonthlyAmendmentRequest,
    ) -> MonthlyProposal:
        command = type(command).model_validate(command.model_dump(mode="json"))
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
        observations, universe, source_evidence = (
            self.configuration.resolve_source_inputs_with_evidence(
                policy.proposal.policy,
                request,
                reporting_currency=definition.reporting_currency,
            )
        )
        instant = self.configuration.clock()
        evaluation = evaluate_monthly_eligibility(
            policy.proposal.policy,
            observations,
            evaluated_at=instant,
            universe_content_hash=universe.content_hash,
        )
        proposal_wire: dict[str, object] = dict(
            publication_evidence_version="v1",
            source_assembly_evidence=source_evidence,
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
        if isinstance(command, MonthlyAmendmentRequest):
            proposal_wire.update(product_version="v2", amendment=command.amendment)
        if isinstance(policy, HistoricalMonthlyPolicyApproval):
            proposal_wire["product_version"] = (
                "v4" if isinstance(command, MonthlyAmendmentRequest) else "v3"
            )
            model = (
                MonthlyAmendmentProposalContent
                if isinstance(command, MonthlyAmendmentRequest)
                else MonthlyEvaluationProposalContent
            )
            unsigned = model.model_validate(proposal_wire).model_dump(
                mode="json", exclude={"content_hash"}
            )
            verification_request = HistoricalPolicyVerificationRequest.model_validate(
                policy.verification.request.model_dump(mode="json")
                | {
                    "operation": "EVALUATION_PROPOSAL",
                    "revision": evaluation_revision,
                    "actor_id": actor_id,
                    "requested_at": instant,
                    "intent_digest": hash_canonical_payload(unsigned),
                }
            )
            proposal_wire = unsigned | {
                "operation_verification": admitted_historical_policy(
                    self.configuration.historical_admission, verification_request
                )
            }
        proposal = decode_monthly_proposal(proposal_wire)
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
    ) -> MonthlyApproval:
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
        instant = self.configuration.clock()
        verification = None
        if isinstance(proposal.policy_approval, HistoricalMonthlyPolicyApproval):
            request = HistoricalPolicyVerificationRequest.model_validate(
                proposal.policy_approval.verification.request.model_dump(mode="json")
                | {
                    "operation": "EVALUATION_APPROVAL",
                    "revision": evaluation_revision,
                    "actor_id": actor_id,
                    "requested_at": instant,
                    "intent_digest": proposal.content_hash,
                }
            )
            verification = admitted_historical_policy(
                self.configuration.historical_admission, request
            )
        approval, _, _ = build_monthly_publication(
            proposal,
            parent,
            approved_by=actor_id,
            approved_at=instant,
            operation_verification=verification,
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
    proposal: MonthlyProposal, command: MonthlyEvaluationRequest, actor_id: str
) -> None:
    if isinstance(proposal, MonthlyAmendmentProposal) != isinstance(
        command, MonthlyAmendmentRequest
    ):
        raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_IMMUTABLE_CONFLICT")
    if isinstance(proposal, MonthlyAmendmentProposal) and isinstance(
        command, MonthlyAmendmentRequest
    ):
        if proposal.amendment != command.amendment:
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_IMMUTABLE_CONFLICT")
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
    approval: MonthlyApproval, proposal: MonthlyProposal, actor_id: str
) -> None:
    if approval.proposal.content_hash != proposal.content_hash or approval.approved_by != actor_id:
        raise ValueError("COMPOSITE_ELIGIBILITY_ACTIVE_EVALUATION_CONFLICT")
