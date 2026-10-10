"""Present admission of source-owned original policy history; no clock overrides."""

from dataclasses import dataclass
from typing import Callable

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import StrictAuthorityModel
from src.core.composite_eligibility.historical_policy import (
    HistoricalPolicyReference,
    HistoricalPolicyVerificationRequest,
    HistoricalPolicyAdmissionPort,
    HistoricalMonthlyPolicyProposal,
    HistoricalMonthlyPolicyApproval,
    admitted_historical_policy,
)
from src.core.composite_eligibility.policy import MonthlyPolicyScope
from src.core.composite_repository import DpmCompositeRepository, DpmCompositeConflictError


class HistoricalPolicyAdmissionRequest(StrictAuthorityModel):
    reference: HistoricalPolicyReference


@dataclass(frozen=True)
class HistoricalPolicyAdmissionApplicationService:
    repository: DpmCompositeRepository
    verifier: HistoricalPolicyAdmissionPort
    clock: Callable[[], str]

    def propose(
        self,
        *,
        tenant_id: str,
        composite_id: str,
        definition_version: str,
        month: str,
        proposal_revision: str,
        actor_id: str,
        command: HistoricalPolicyAdmissionRequest,
    ) -> HistoricalMonthlyPolicyProposal:
        command = HistoricalPolicyAdmissionRequest.model_validate(command.model_dump(mode="json"))
        key = dict(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=month,
            proposal_revision=proposal_revision,
        )
        retained = self.repository.get_monthly_policy_proposal(**key)
        if retained is not None:
            return self._same_proposal(retained, command, actor_id)
        definition = self.repository.get_definition(
            tenant_id=tenant_id, composite_id=composite_id, definition_version=definition_version
        )
        if definition is None:
            raise ValueError("COMPOSITE_DEFINITION_NOT_FOUND")
        request = HistoricalPolicyVerificationRequest(
            operation="POLICY_PROPOSAL",
            reference=command.reference,
            scope=MonthlyPolicyScope(
                tenant_id=tenant_id,
                composite_id=composite_id,
                definition_version=definition_version,
                strategy_code=definition.strategy_code,
            ),
            month=month,
            eligibility_policy_version=definition.eligibility_policy_version,
            reporting_currency=definition.reporting_currency,
            revision=proposal_revision,
            actor_id=actor_id,
            requested_at=self.clock(),
            intent_digest=hash_canonical_payload(
                {
                    "reference": command.reference.model_dump(mode="json"),
                    "proposal_revision": proposal_revision,
                }
            ),
        )
        proof = admitted_historical_policy(self.verifier, request)
        proposal = HistoricalMonthlyPolicyProposal(
            proposal_revision=proposal_revision,
            eligibility_policy_version=definition.eligibility_policy_version,
            policy=proof.mapping.policy,
            attachments=proof.mapping.attachments,
            proposed_by=actor_id,
            proposed_at=request.requested_at,
            verification=proof,
        )
        try:
            self.repository.save_monthly_policy_proposal(proposal=proposal)
        except DpmCompositeConflictError:
            winner = self.repository.get_monthly_policy_proposal(**key)
            if winner is None:
                raise
            return self._same_proposal(winner, command, actor_id)
        return proposal

    @staticmethod
    def _same_proposal(
        retained: object, command: HistoricalPolicyAdmissionRequest, actor: str
    ) -> HistoricalMonthlyPolicyProposal:
        if not isinstance(retained, HistoricalMonthlyPolicyProposal) or (
            retained.verification.mapping.reference,
            retained.proposed_by,
        ) != (command.reference, actor):
            raise DpmCompositeConflictError("COMPOSITE_ELIGIBILITY_PROPOSAL_IMMUTABLE_CONFLICT")
        return retained

    def approved(
        self, proposal: HistoricalMonthlyPolicyProposal, actor_id: str
    ) -> HistoricalMonthlyPolicyApproval:
        initial = proposal.verification.request
        request = HistoricalPolicyVerificationRequest.model_validate(
            initial.model_dump(mode="json")
            | {
                "operation": "POLICY_APPROVAL",
                "actor_id": actor_id,
                "requested_at": self.clock(),
                "intent_digest": proposal.content_hash,
            }
        )
        proof = admitted_historical_policy(self.verifier, request)
        return HistoricalMonthlyPolicyApproval(
            proposal=proposal,
            approved_by=actor_id,
            approved_at=request.requested_at,
            verification=proof,
        )
