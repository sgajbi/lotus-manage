"""Present historical admission for an existing unpublished subject, never a clock override."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.api.services.composite_subject_requests import SubjectHistoricalPolicyRequest
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_eligibility.controlled_scenario import (
    ControlledScenarioMonthlyPolicyApproval,
    ControlledScenarioMonthlyPolicyProposal,
    ControlledScenarioVerification,
    ControlledScenarioVerificationRequest,
)
from src.core.composite_eligibility.historical_policy import (
    HistoricalMonthlyPolicyApproval,
    HistoricalMonthlyPolicyProposal,
    HistoricalPolicyAdmissionPort,
    HistoricalPolicyVerification,
    HistoricalPolicyVerificationRequest,
    admitted_historical_policy,
)
from src.core.composite_eligibility.policy import MonthlyPolicyScope, month_window
from src.core.composite_eligibility.staged_controls import (
    ControlledScenarioSubjectEvaluationApproval,
    ControlledScenarioSubjectEvaluationProposal,
    ControlledScenarioSubjectPolicyApproval,
    ControlledScenarioSubjectPolicyProposal,
    HistoricalSubjectEvaluationApproval,
    HistoricalSubjectEvaluationProposal,
    HistoricalSubjectPolicyApproval,
    HistoricalSubjectPolicyProposal,
    SubjectEvaluationProposalContent,
    require_synthetic_history,
)
from src.core.composite_eligibility.staged_ports import StagedCompositeRepository, SubjectKey
from src.core.composite_eligibility.staged_subject import EligibilitySubject
from src.core.composite_eligibility.verification import (
    CompositeEvidenceVerifier,
    VerificationReceipt,
    VerificationRequest,
    require_verification,
)
from src.core.composite_repository import DpmCompositeConflictError


@dataclass(frozen=True)
class HistoricalSubjectPolicyApplicationService:
    repository: StagedCompositeRepository
    historical: HistoricalPolicyAdmissionPort
    verifier: CompositeEvidenceVerifier
    clock: Callable[[], str]

    def propose(
        self, key: SubjectKey, revision: str, actor: str, command: SubjectHistoricalPolicyRequest
    ) -> HistoricalSubjectPolicyProposal | ControlledScenarioSubjectPolicyProposal:
        subject = self.repository.get_eligibility_subject(key=key)
        if subject is None:
            raise ValueError("COMPOSITE_SUBJECT_NOT_FOUND")
        if subject.content_hash != command.expected_subject_content_hash:
            raise ValueError("COMPOSITE_SUBJECT_STALE_CONTENT_CONFLICT")
        retained = self.repository.get_subject_control(
            key=key, kind="CompositeSubjectPolicyProposal", revision=revision
        )
        if retained is not None:
            if not isinstance(
                retained, (HistoricalSubjectPolicyProposal, ControlledScenarioSubjectPolicyProposal)
            ) or (
                retained.proposal.verification.mapping.reference != command.reference
                or retained.proposal.proposed_by != actor
            ):
                raise ValueError("COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT")
            return retained
        request_type = (
            ControlledScenarioVerificationRequest
            if command.reference.signing_contract == "CONTROLLED_SYNTHETIC_POLICY_V1"
            else HistoricalPolicyVerificationRequest
        )
        request = request_type(
            operation="POLICY_PROPOSAL",
            reference=command.reference,
            scope=MonthlyPolicyScope(
                tenant_id=key[0],
                composite_id=key[1],
                definition_version=key[2],
                strategy_code=subject.strategy_code,
            ),
            month=subject.month,
            eligibility_policy_version=subject.eligibility_policy_version,
            reporting_currency=subject.reporting_currency,
            revision=revision,
            actor_id=actor,
            requested_at=self.clock(),
            intent_digest=hash_canonical_payload(
                {
                    "reference": command.reference.model_dump(mode="json"),
                    "proposal_revision": revision,
                }
            ),
        )
        proof = admitted_historical_policy(self.historical, request)
        require_synthetic_history(proof)
        proposal_type = (
            ControlledScenarioMonthlyPolicyProposal
            if isinstance(proof, ControlledScenarioVerification)
            else HistoricalMonthlyPolicyProposal
        )
        proposal = proposal_type.model_validate(
            {
                "proposal_revision": revision,
                "eligibility_policy_version": subject.eligibility_policy_version,
                "policy": proof.mapping.policy,
                "attachments": proof.mapping.attachments,
                "proposed_by": actor,
                "proposed_at": request.requested_at,
                "verification": proof,
            }
        )
        verification = self._subject_verification(
            subject, "proposal_content_hash", proposal.content_hash
        )
        result_type = (
            ControlledScenarioSubjectPolicyProposal
            if isinstance(proof, ControlledScenarioVerification)
            else HistoricalSubjectPolicyProposal
        )
        result = result_type.model_validate(
            {
                "subject": subject,
                "proposal": proposal,
                "verification": verification,
            }
        )
        try:
            self.repository.save_subject_control(control=result)
        except DpmCompositeConflictError:
            winner = self.repository.get_subject_control(
                key=key, kind=result.product_name, revision=revision
            )
            if not isinstance(
                winner, (HistoricalSubjectPolicyProposal, ControlledScenarioSubjectPolicyProposal)
            ) or (
                winner.subject != subject
                or winner.proposal.verification.mapping.reference != command.reference
                or winner.proposal.proposed_by != actor
            ):
                raise
            return winner
        return result

    def approve(
        self,
        proposal: HistoricalSubjectPolicyProposal | ControlledScenarioSubjectPolicyProposal,
        actor: str,
    ) -> HistoricalSubjectPolicyApproval | ControlledScenarioSubjectPolicyApproval:
        instant = self.clock()
        proof = self._operation(
            proposal.proposal.verification,
            "POLICY_APPROVAL",
            actor,
            instant,
            proposal.proposal.content_hash,
        )
        approval_type = (
            ControlledScenarioMonthlyPolicyApproval
            if isinstance(proof, ControlledScenarioVerification)
            else HistoricalMonthlyPolicyApproval
        )
        approval = approval_type.model_validate(
            {
                "proposal": proposal.proposal,
                "approved_by": actor,
                "approved_at": instant,
                "verification": proof,
            }
        )
        result_type = (
            ControlledScenarioSubjectPolicyApproval
            if isinstance(proof, ControlledScenarioVerification)
            else HistoricalSubjectPolicyApproval
        )
        result = result_type.model_validate(
            {
                "proposal": proposal,
                "approval": approval,
                "verification": self._subject_verification(
                    proposal.subject, "approval_content_hash", approval.content_hash
                ),
            }
        )
        key = (
            proposal.subject.tenant_id,
            proposal.subject.composite_id,
            proposal.subject.definition_version,
            proposal.subject.subject_revision,
        )
        try:
            self.repository.save_subject_control(control=result)
        except DpmCompositeConflictError:
            winner = self.repository.get_subject_control(
                key=key, kind=result.product_name, revision=proposal.proposal.proposal_revision
            )
            if (
                not isinstance(
                    winner,
                    (HistoricalSubjectPolicyApproval, ControlledScenarioSubjectPolicyApproval),
                )
                or winner.proposal != proposal
                or winner.approval.approved_by != actor
            ):
                raise
            return winner
        return result

    def save_evaluation(
        self,
        key: SubjectKey,
        control: HistoricalSubjectEvaluationProposal
        | ControlledScenarioSubjectEvaluationProposal
        | HistoricalSubjectEvaluationApproval
        | ControlledScenarioSubjectEvaluationApproval,
    ) -> (
        HistoricalSubjectEvaluationProposal
        | ControlledScenarioSubjectEvaluationProposal
        | HistoricalSubjectEvaluationApproval
        | ControlledScenarioSubjectEvaluationApproval
    ):
        revision = (
            control.evaluation_revision
            if isinstance(
                control,
                (HistoricalSubjectEvaluationProposal, ControlledScenarioSubjectEvaluationProposal),
            )
            else control.proposal.evaluation_revision
        )
        try:
            self.repository.save_subject_control(control=control)
        except DpmCompositeConflictError:
            winner = self.repository.get_subject_control(
                key=key, kind=control.product_name, revision=revision
            )
            if type(winner) is not type(control):
                raise
            fields: tuple[str, ...]
            if isinstance(
                control,
                (HistoricalSubjectEvaluationProposal, ControlledScenarioSubjectEvaluationProposal),
            ) and isinstance(
                winner,
                (HistoricalSubjectEvaluationProposal, ControlledScenarioSubjectEvaluationProposal),
            ):
                fields = (
                    "policy_approval",
                    "target_membership_revision",
                    "observations",
                    "observation_binding",
                    "source_assembly_evidence",
                    "proposed_by",
                )
            elif isinstance(
                control,
                (HistoricalSubjectEvaluationApproval, ControlledScenarioSubjectEvaluationApproval),
            ) and isinstance(
                winner,
                (HistoricalSubjectEvaluationApproval, ControlledScenarioSubjectEvaluationApproval),
            ):
                fields = ("proposal", "approved_by")
            else:
                raise
            if any(getattr(control, name) != getattr(winner, name) for name in fields):
                raise
            return winner
        return control

    def evaluation_proposal(
        self, wire: dict[str, Any]
    ) -> HistoricalSubjectEvaluationProposal | ControlledScenarioSubjectEvaluationProposal:
        wire = wire | {
            "product_name": "CompositeSubjectEvaluationProposal",
            "product_version": wire["policy_approval"]["product_version"],
            "evaluation_kind": "INITIAL",
        }
        # Serialize all defaults and nested hashes before signing the unsigned intent.
        wire = SubjectEvaluationProposalContent.model_validate(wire).model_dump(
            mode="json", exclude={"content_hash"}
        )
        policy_type = (
            ControlledScenarioSubjectPolicyApproval
            if wire["product_version"] == "v3"
            else HistoricalSubjectPolicyApproval
        )
        policy = policy_type.model_validate(wire["policy_approval"])
        proof = self._operation(
            policy.approval.verification,
            "EVALUATION_PROPOSAL",
            wire["proposed_by"],
            wire["proposed_at"],
            hash_canonical_payload(wire),
            revision=wire["evaluation_revision"],
        )
        proposal_type = (
            ControlledScenarioSubjectEvaluationProposal
            if wire["product_version"] == "v3"
            else HistoricalSubjectEvaluationProposal
        )
        return proposal_type.model_validate(wire | {"operation_verification": proof})

    def evaluation_approval(
        self, wire: dict[str, Any]
    ) -> HistoricalSubjectEvaluationApproval | ControlledScenarioSubjectEvaluationApproval:
        proposal_type = (
            ControlledScenarioSubjectEvaluationProposal
            if wire["proposal"]["product_version"] == "v3"
            else HistoricalSubjectEvaluationProposal
        )
        proposal = proposal_type.model_validate(wire["proposal"])
        proof = self._operation(
            proposal.policy_approval.approval.verification,
            "EVALUATION_APPROVAL",
            wire["approved_by"],
            wire["approved_at"],
            proposal.content_hash,
            revision=proposal.evaluation_revision,
        )
        approval_type = (
            ControlledScenarioSubjectEvaluationApproval
            if proposal.product_version == "v3"
            else HistoricalSubjectEvaluationApproval
        )
        return approval_type.model_validate(wire | {"operation_verification": proof})

    def _operation(
        self,
        prior: HistoricalPolicyVerification | ControlledScenarioVerification,
        operation: str,
        actor: str,
        instant: str,
        intent: str,
        *,
        revision: str | None = None,
    ) -> HistoricalPolicyVerification | ControlledScenarioVerification:
        request_type = (
            ControlledScenarioVerificationRequest
            if prior.product_version == "v2"
            else HistoricalPolicyVerificationRequest
        )
        request = request_type.model_validate(
            prior.request.model_dump(mode="json")
            | {
                "operation": operation,
                "actor_id": actor,
                "requested_at": instant,
                "intent_digest": intent,
                "revision": revision or prior.request.revision,
            }
        )
        proof = admitted_historical_policy(self.historical, request)
        require_synthetic_history(proof)
        return proof

    def _subject_verification(
        self, subject: EligibilitySubject, hash_field: str, digest: str
    ) -> VerificationReceipt:
        first, last = month_window(subject.month)
        return require_verification(
            self.verifier,
            VerificationRequest(
                purpose="ELIGIBILITY_POLICY",
                tenant_id=subject.tenant_id,
                composite_id=subject.composite_id,
                definition_version=subject.definition_version,
                subject_content_hash=subject.content_hash,
                claims_digest=hash_canonical_payload(
                    {"subject_content_hash": subject.content_hash, hash_field: digest}
                ),
                effective_from=first,
                effective_to=last,
            ),
        )
