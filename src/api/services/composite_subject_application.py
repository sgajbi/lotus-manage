"""Subject-scoped orchestration; existing monthly engine owns every financial rule."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, TypeVar

from src.api.services.composite_subject_requests import (
    SubjectRequest,
    SubjectPolicyRequest,
    SubjectApprovalRequest,
    SubjectEvaluationRequest,
    SubjectFinalizationRequest,
)
from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import EvidenceBinding
from src.core.composite_definition_versions import DpmCompositeDefinitionV2
from src.core.composite_eligibility.approval import MonthlyPolicyProposal, MonthlyPolicyApproval
from src.core.composite_eligibility.evaluation import evaluate_monthly_eligibility
from src.core.composite_eligibility.policy import (
    MonthlyPolicyScope,
    resolve_monthly_policy,
    month_window,
)
from src.core.composite_eligibility.source import (
    MonthlyEligibilitySourcePort,
    UnavailableMonthlyEligibilitySource,
    MonthlyEligibilitySourceRequest,
    admitted_source_snapshot,
)
from src.core.composite_eligibility.staged_subject import EligibilitySubject, CandidateUniverse
from src.core.composite_eligibility.staged_ports import (
    SubjectKey,
    ControlKind,
    StagedCompositeRepository,
    CandidateUniverseSource,
    CandidateUniverseRequest,
    UnavailableCandidateUniverseSource,
)
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
    initial_projection,
    finalization_verification_requests,
    require_definition_subject,
)
from src.core.composite_eligibility.verification import (
    CompositeEvidenceVerifier,
    UnavailableCompositeEvidenceVerifier,
    VerificationRequest,
    VerificationPurpose,
    require_verification,
)
from src.core.composite_universe import DpmCompositeUniverseSourceProduct

ControlT = TypeVar(
    "ControlT",
    SubjectPolicyProposal,
    SubjectPolicyApproval,
    SubjectEvaluationProposal,
    SubjectEvaluationApproval,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class CompositeSubjectApplicationService:
    repository: StagedCompositeRepository
    candidates: CandidateUniverseSource = field(default_factory=UnavailableCandidateUniverseSource)
    observations: MonthlyEligibilitySourcePort = field(
        default_factory=UnavailableMonthlyEligibilitySource
    )
    verifier: CompositeEvidenceVerifier = field(
        default_factory=UnavailableCompositeEvidenceVerifier
    )
    clock: Callable[[], str] = utc_now

    def subject(self, key: SubjectKey) -> EligibilitySubject:
        result = self.repository.get_eligibility_subject(key=key)
        if result is None:
            raise ValueError("COMPOSITE_SUBJECT_NOT_FOUND")
        return result

    def control(self, key: SubjectKey, revision: str, model: type[ControlT]) -> ControlT:
        result = self._control(key, revision, model)
        if result is None:
            raise ValueError("COMPOSITE_SUBJECT_CONTROL_NOT_FOUND")
        return result

    def _control(self, key: SubjectKey, revision: str, model: type[ControlT]) -> ControlT | None:
        kinds: dict[
            type[SubjectPolicyProposal]
            | type[SubjectPolicyApproval]
            | type[SubjectEvaluationProposal]
            | type[SubjectEvaluationApproval],
            ControlKind,
        ] = {
            SubjectPolicyProposal: "CompositeSubjectPolicyProposal",
            SubjectPolicyApproval: "CompositeSubjectPolicyApproval",
            SubjectEvaluationProposal: "CompositeSubjectEvaluationProposal",
            SubjectEvaluationApproval: "CompositeSubjectEvaluationApproval",
        }
        result = self.repository.get_subject_control(key=key, kind=kinds[model], revision=revision)
        if result is None:
            return None
        if not isinstance(result, model):
            raise ValueError("COMPOSITE_SUBJECT_CONTROL_INTEGRITY_CONFLICT")
        return result

    def create(self, key: SubjectKey, actor: str, command: SubjectRequest) -> EligibilitySubject:
        command = SubjectRequest.model_validate(command.model_dump(mode="json"))
        retained = self.repository.get_eligibility_subject(key=key)
        business = command.model_dump(mode="json", exclude={"registry_binding"})
        if retained is not None:
            if any(getattr(retained, name) != value for name, value in business.items()) or (
                retained.universe.registry_binding != command.registry_binding
                or retained.created_by != actor
            ):
                raise ValueError("COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT")
            return retained
        request = CandidateUniverseRequest(
            *key[:3], command.month, command.reporting_currency, command.registry_binding
        )
        universe = self.candidates.resolve(request)
        if universe is None:
            raise ValueError("COMPOSITE_SUBJECT_UNIVERSE_UNAVAILABLE")
        universe = CandidateUniverse.model_validate(universe.model_dump(mode="json"))
        if universe.registry_binding != command.registry_binding:
            raise ValueError("COMPOSITE_SUBJECT_REGISTRY_BINDING_MISMATCH")
        instant = self.clock()
        if universe.generated_at > instant:
            raise ValueError("COMPOSITE_SUBJECT_FUTURE_UNIVERSE_GENERATION")
        subject = EligibilitySubject(
            tenant_id=key[0],
            composite_id=key[1],
            definition_version=key[2],
            subject_revision=key[3],
            **business,
            universe=universe,
            created_by=actor,
            created_at=instant,
        )
        self.repository.save_eligibility_subject(subject=subject)
        return subject

    def propose_policy(
        self, key: SubjectKey, revision: str, actor: str, command: SubjectPolicyRequest
    ) -> SubjectPolicyProposal:
        command = SubjectPolicyRequest.model_validate(command.model_dump(mode="json"))
        subject = self.subject(key)
        if subject.content_hash != command.expected_subject_content_hash:
            raise ValueError("COMPOSITE_SUBJECT_STALE_CONTENT_CONFLICT")
        existing = self._control(key, revision, SubjectPolicyProposal)
        if existing is not None:
            if (
                existing.proposal.policy.layers,
                existing.proposal.attachments,
                existing.proposal.proposed_by,
            ) != (command.layers, command.attachments, actor):
                raise ValueError("COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT")
            return existing
        scope = MonthlyPolicyScope(
            tenant_id=key[0],
            composite_id=key[1],
            definition_version=key[2],
            strategy_code=subject.strategy_code,
        )
        policy = resolve_monthly_policy(command.layers, month=subject.month, scope=scope)
        control = SubjectPolicyProposal(
            subject=subject,
            proposal=MonthlyPolicyProposal(
                proposal_revision=revision,
                eligibility_policy_version=subject.eligibility_policy_version,
                policy=policy,
                attachments=command.attachments,
                proposed_by=actor,
                proposed_at=self.clock(),
            ),
        )
        self.repository.save_subject_control(control=control)
        return control

    def approve_policy(
        self, key: SubjectKey, revision: str, actor: str, command: SubjectApprovalRequest
    ) -> SubjectPolicyApproval:
        proposal = self.control(key, revision, SubjectPolicyProposal)
        _require_approval_actor(
            proposal.content_hash, proposal.proposal.proposed_by, actor, command
        )
        existing = self._control(key, revision, SubjectPolicyApproval)
        if existing is not None:
            if existing.proposal != proposal or existing.approval.approved_by != actor:
                raise ValueError("COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT")
            return existing
        approval = MonthlyPolicyApproval(
            proposal=proposal.proposal, approved_by=actor, approved_at=self.clock()
        )
        claims = hash_canonical_payload(
            {
                "subject_content_hash": proposal.subject.content_hash,
                "approval_content_hash": approval.content_hash,
            }
        )
        verification = require_verification(
            self.verifier, _verification(proposal.subject, "ELIGIBILITY_POLICY", claims)
        )
        result = SubjectPolicyApproval(
            proposal=proposal, approval=approval, verification=verification
        )
        self.repository.save_subject_control(control=result)
        return result

    def evaluate(
        self, key: SubjectKey, revision: str, actor: str, command: SubjectEvaluationRequest
    ) -> SubjectEvaluationProposal:
        command = SubjectEvaluationRequest.model_validate(command.model_dump(mode="json"))
        policy = self.control(key, command.policy_proposal_revision, SubjectPolicyApproval)
        if policy.content_hash != command.policy_approval_content_hash:
            raise ValueError("COMPOSITE_SUBJECT_STALE_CONTENT_CONFLICT")
        existing = self._control(key, revision, SubjectEvaluationProposal)
        if existing is not None:
            binding = existing.observation_binding
            if (
                existing.policy_approval,
                existing.proposed_by,
                existing.target_membership_revision,
                binding.source_cut_id,
                binding.source_watermark,
                binding.content_hash,
            ) != (
                policy,
                actor,
                command.target_membership_revision,
                command.source_cut_id,
                command.source_revision,
                command.source_content_hash,
            ):
                raise ValueError("COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT")
            return existing
        subject = policy.proposal.subject
        request = MonthlyEligibilitySourceRequest(
            scope=policy.approval.proposal.policy.scope,
            month=subject.month,
            source_cut_id=command.source_cut_id,
            owner_service=subject.universe.observation_owner,
            expected_source_revision=command.source_revision,
            expected_content_hash=command.source_content_hash,
            expected_portfolio_ids=tuple(member.member_id for member in subject.universe.members),
            reporting_currency=subject.reporting_currency,
        )
        resolution = self.observations.resolve(request)
        snapshot = admitted_source_snapshot(request, resolution)
        instant = self.clock()
        evaluation = evaluate_monthly_eligibility(
            policy.approval.proposal.policy,
            snapshot,
            evaluated_at=instant,
            universe_content_hash=subject.universe.content_hash,
        )
        binding = DpmCompositeUniverseSourceProduct(
            owner_service=subject.universe.observation_owner,
            product_name=snapshot.product_name,
            contract_version=snapshot.product_version,
            authority_scope="POLICY_INPUT",
            source_cut_id=snapshot.source_cut_id,
            source_watermark=snapshot.source_revision,
            content_hash=command.source_content_hash,
        )
        proposal = SubjectEvaluationProposal(
            source_assembly_evidence=resolution.source_assembly_evidence,
            policy_approval=policy,
            evaluation_revision=revision,
            target_membership_revision=command.target_membership_revision,
            observations=snapshot,
            observation_binding=binding,
            evaluation=evaluation,
            proposed_by=actor,
            proposed_at=instant,
        )
        self.repository.save_subject_control(control=proposal)
        return proposal

    def approve_evaluation(
        self, key: SubjectKey, revision: str, actor: str, command: SubjectApprovalRequest
    ) -> SubjectEvaluationApproval:
        proposal = self.control(key, revision, SubjectEvaluationProposal)
        _require_approval_actor(proposal.content_hash, proposal.proposed_by, actor, command)
        existing = self._control(key, revision, SubjectEvaluationApproval)
        if existing is not None:
            if existing.proposal != proposal or existing.approved_by != actor:
                raise ValueError("COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT")
            return existing
        instant = self.clock()
        claims = subject_approval_claims(proposal, actor, instant)
        subject = proposal.policy_approval.proposal.subject
        verification = require_verification(
            self.verifier, _verification(subject, "ELIGIBILITY_POLICY_EVALUATION", claims)
        )
        membership, universe = initial_projection(proposal, claims, actor, instant)
        result = SubjectEvaluationApproval(
            proposal=proposal,
            approved_by=actor,
            approved_at=instant,
            evidence_kind="SYNTHETIC_UNSIGNED"
            if verification.posture == "SYNTHETIC_NON_CERTIFYING"
            else "QUALIFIED_VERIFICATION_RECEIPT",
            claims_digest=claims,
            membership_content_hash=membership.content_hash,
            universe_content_hash=universe.content_hash,
            verification=verification,
        )
        self.repository.save_subject_control(control=result)
        return result

    def finalize(
        self, key: SubjectKey, actor: str, command: SubjectFinalizationRequest
    ) -> SubjectFinalizationReceipt:
        command = SubjectFinalizationRequest.model_validate(command.model_dump(mode="json"))
        subject = self.subject(key)
        approval = self.control(key, command.evaluation_revision, SubjectEvaluationApproval)
        if approval.content_hash != command.expected_approval_content_hash:
            raise ValueError("COMPOSITE_SUBJECT_STALE_CONTENT_CONFLICT")
        definition = DpmCompositeDefinitionV2.model_validate(
            command.definition.model_dump(mode="json")
            | {
                "product_name": "CompositeDefinition",
                "tenant_id": key[0],
                "composite_id": key[1],
                "definition_version": key[2],
                "created_by": subject.created_by,
            }
        )
        if (
            actor != approval.approved_by
            or definition.authority_approval.claims.approving_identity != actor
        ):
            raise ValueError("COMPOSITE_SUBJECT_FINALIZER_FORBIDDEN")
        require_definition_subject(definition, subject, approval)
        retained = self.repository.get_eligibility_finalization(key=key)
        if retained is not None:
            if (
                retained.finalization.definition != definition
                or retained.finalization.evaluation_approval != approval
            ):
                raise ValueError("COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT")
            return retained
        requests = finalization_verification_requests(definition, subject)
        verifications = [require_verification(self.verifier, request) for request in requests]
        finalization = SubjectFinalization(
            subject=subject,
            evaluation_approval=approval,
            definition=definition,
            verifications=verifications,
        )
        return self.repository.finalize_eligibility_subject(finalization=finalization)

    def finalization(self, key: SubjectKey) -> SubjectFinalizationReceipt:
        result = self.repository.get_eligibility_finalization(key=key)
        if result is None:
            raise ValueError("COMPOSITE_SUBJECT_FINALIZATION_NOT_FOUND")
        return result

    def resolve_evidence(
        self, tenant_id: str, composite_id: str, definition_version: str, binding: EvidenceBinding
    ) -> SubjectFinalizationReceipt:
        if (
            binding.product_name != "CompositeSubjectEvaluationApproval"
            or binding.product_version != "v1"
        ):
            raise ValueError("COMPOSITE_SUBJECT_ELIGIBILITY_BINDING_MISMATCH")
        result = self.repository.resolve_eligibility_evidence(
            tenant_id=tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            evaluation_revision=binding.revision,
            approval_content_hash=binding.digest,
        )
        if result is None:
            raise ValueError("COMPOSITE_SUBJECT_FINALIZATION_NOT_FOUND")
        return result


def _require_approval_actor(
    expected: str, maker: str, actor: str, command: SubjectApprovalRequest
) -> None:
    command = SubjectApprovalRequest.model_validate(command.model_dump(mode="json"))
    if command.expected_proposal_content_hash != expected:
        raise ValueError("COMPOSITE_SUBJECT_STALE_CONTENT_CONFLICT")
    if actor == maker:
        raise ValueError("COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN")


def _verification(
    subject: EligibilitySubject, purpose: VerificationPurpose, claims: str
) -> VerificationRequest:
    first, last = month_window(subject.month)
    return VerificationRequest(
        purpose=purpose,
        tenant_id=subject.tenant_id,
        composite_id=subject.composite_id,
        definition_version=subject.definition_version,
        subject_content_hash=subject.content_hash,
        claims_digest=claims,
        effective_from=first,
        effective_to=last,
    )
