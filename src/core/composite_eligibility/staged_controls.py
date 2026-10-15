"""Subject-bound wrappers reuse the monthly policy and calculation contracts."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator
from src.core.composite_eligibility.source_assembly import (
    VerifiedMonthlySourceAssembly,
    retained_source_assembly,
)

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import Digest, Identity, StrictAuthorityModel
from src.core.composite_eligibility.approval import (
    MonthlyPolicyApproval,
    MonthlyPolicyProposal,
    MonthlyPolicyApprovalVariant,
    MonthlyPolicyProposalVariant,
    decode_policy_approval,
    decode_policy_proposal,
)
from src.core.composite_eligibility.historical_policy import (
    HistoricalMonthlyPolicyProposal,
    HistoricalMonthlyPolicyApproval,
    HistoricalPolicyVerification,
)
from src.core.composite_eligibility.evaluation import (
    MonthlyEligibilityEvaluation,
    evaluate_monthly_eligibility,
)
from src.core.composite_eligibility.observations import MonthlyEligibilityObservations, UtcInstant
from src.core.composite_eligibility.staged_subject import EligibilitySubject, bind_content
from src.core.composite_eligibility.verification import (
    VerificationReceipt,
    VerificationRequest,
    VerificationPurpose,
)
from src.core.composite_universe import DpmCompositeUniverseSourceProduct


class SubjectPolicyProposalContent(StrictAuthorityModel):
    product_name: Literal["CompositeSubjectPolicyProposal"] = "CompositeSubjectPolicyProposal"
    product_version: Literal["v1", "v2"]
    subject: EligibilitySubject
    proposal: MonthlyPolicyProposalVariant
    content_hash: str = ""

    @model_validator(mode="after")
    def require_subject_policy(self) -> "SubjectPolicyProposalContent":
        self.subject = EligibilitySubject.model_validate(self.subject.model_dump(mode="json"))
        self.proposal = decode_policy_proposal(self.proposal.model_dump(mode="json"))
        scope, subject = self.proposal.policy.scope, self.subject
        if (
            scope.tenant_id,
            scope.composite_id,
            scope.definition_version,
            scope.strategy_code,
            self.proposal.policy.month,
            self.proposal.eligibility_policy_version,
        ) != (
            subject.tenant_id,
            subject.composite_id,
            subject.definition_version,
            subject.strategy_code,
            subject.month,
            subject.eligibility_policy_version,
        ):
            raise ValueError("COMPOSITE_SUBJECT_POLICY_MISMATCH")
        if (
            self.proposal.proposed_by != subject.created_by
            or self.proposal.proposed_at < subject.created_at
        ):
            raise ValueError("COMPOSITE_SUBJECT_MAKER_MISMATCH")
        bind_content(self)
        return self


class SubjectPolicyProposal(SubjectPolicyProposalContent):
    product_version: Literal["v1"] = "v1"
    proposal: MonthlyPolicyProposal


class HistoricalSubjectPolicyProposal(SubjectPolicyProposalContent):
    product_version: Literal["v2"] = "v2"
    proposal: HistoricalMonthlyPolicyProposal
    verification: VerificationReceipt

    @model_validator(mode="after")
    def require_historical_subject_admission(self) -> "HistoricalSubjectPolicyProposal":
        require_synthetic_history(self.proposal.verification)
        if self.proposal.verification.mapping.reporting_currency != self.subject.reporting_currency:
            raise ValueError("COMPOSITE_SUBJECT_POLICY_MISMATCH")
        require_synthetic_receipt(self.verification)
        require_verification_scope(
            self.verification.request,
            self.subject,
            "ELIGIBILITY_POLICY",
            hash_canonical_payload(
                {
                    "subject_content_hash": self.subject.content_hash,
                    "proposal_content_hash": self.proposal.content_hash,
                }
            ),
        )
        return self


SubjectPolicyProposalVariant = Annotated[
    SubjectPolicyProposal | HistoricalSubjectPolicyProposal, Field(discriminator="product_version")
]
POLICY_PROPOSAL_ADAPTER: TypeAdapter[SubjectPolicyProposalVariant] = TypeAdapter(
    SubjectPolicyProposalVariant
)


class SubjectPolicyApprovalContent(StrictAuthorityModel):
    product_name: Literal["CompositeSubjectPolicyApproval"] = "CompositeSubjectPolicyApproval"
    product_version: Literal["v1", "v2"]
    proposal: SubjectPolicyProposalVariant
    approval: MonthlyPolicyApprovalVariant
    verification: VerificationReceipt
    content_hash: str = ""

    @model_validator(mode="after")
    def require_exact_policy_approval(self) -> "SubjectPolicyApprovalContent":
        self.proposal = POLICY_PROPOSAL_ADAPTER.validate_python(
            self.proposal.model_dump(mode="json")
        )
        self.approval = decode_policy_approval(self.approval.model_dump(mode="json"))
        if (
            self.product_version != self.proposal.product_version
            or self.product_version != self.approval.product_version
        ):
            raise ValueError("COMPOSITE_SUBJECT_CONTROL_VERSION_MISMATCH")
        if self.approval.proposal != self.proposal.proposal:
            raise ValueError("COMPOSITE_SUBJECT_POLICY_APPROVAL_MISMATCH")
        subject = self.proposal.subject
        request = self.verification.request
        claims = hash_canonical_payload(
            {
                "subject_content_hash": subject.content_hash,
                "approval_content_hash": self.approval.content_hash,
            }
        )
        require_verification_scope(request, subject, "ELIGIBILITY_POLICY", claims)
        bind_content(self)
        return self


class SubjectPolicyApproval(SubjectPolicyApprovalContent):
    product_version: Literal["v1"] = "v1"
    proposal: SubjectPolicyProposal
    approval: MonthlyPolicyApproval


class HistoricalSubjectPolicyApproval(SubjectPolicyApprovalContent):
    product_version: Literal["v2"] = "v2"
    proposal: HistoricalSubjectPolicyProposal
    approval: HistoricalMonthlyPolicyApproval

    @model_validator(mode="after")
    def require_noncertifying_approval(self) -> "HistoricalSubjectPolicyApproval":
        require_synthetic_history(self.approval.verification)
        require_synthetic_receipt(self.verification)
        return self


SubjectPolicyApprovalVariant = Annotated[
    SubjectPolicyApproval | HistoricalSubjectPolicyApproval, Field(discriminator="product_version")
]
POLICY_APPROVAL_ADAPTER: TypeAdapter[SubjectPolicyApprovalVariant] = TypeAdapter(
    SubjectPolicyApprovalVariant
)


class SubjectEvaluationProposalContent(StrictAuthorityModel):
    product_name: Literal["CompositeSubjectEvaluationProposal"] = (
        "CompositeSubjectEvaluationProposal"
    )
    product_version: Literal["v1", "v2"]
    evaluation_kind: Literal["INITIAL"] = "INITIAL"
    policy_approval: SubjectPolicyApprovalVariant
    evaluation_revision: Identity
    target_membership_revision: Identity
    observations: MonthlyEligibilityObservations
    observation_binding: DpmCompositeUniverseSourceProduct
    source_assembly_evidence: VerifiedMonthlySourceAssembly | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    evaluation: MonthlyEligibilityEvaluation
    proposed_by: Identity
    proposed_at: UtcInstant
    content_hash: str = ""

    @model_validator(mode="after")
    def require_reproducible_evaluation(self) -> "SubjectEvaluationProposalContent":
        self.policy_approval = POLICY_APPROVAL_ADAPTER.validate_python(
            self.policy_approval.model_dump(mode="json")
        )
        if self.product_version != self.policy_approval.product_version:
            raise ValueError("COMPOSITE_SUBJECT_CONTROL_VERSION_MISMATCH")
        subject = self.policy_approval.proposal.subject
        observations = MonthlyEligibilityObservations.model_validate(
            self.observations.model_dump(mode="json")
        )
        self.source_assembly_evidence = retained_source_assembly(
            self.source_assembly_evidence, observations
        )
        if observations.expected_portfolio_ids != [m.member_id for m in subject.universe.members]:
            raise ValueError("COMPOSITE_SUBJECT_SOURCE_UNIVERSE_MISMATCH")
        product = self.observation_binding
        if (
            product.owner_service,
            product.product_name,
            product.contract_version,
            product.authority_scope,
            product.source_cut_id,
            product.source_watermark,
            product.content_hash,
        ) != (
            subject.universe.observation_owner,
            observations.product_name,
            observations.product_version,
            "POLICY_INPUT",
            observations.source_cut_id,
            observations.source_revision,
            hash_canonical_payload(observations.model_dump(mode="json")),
        ):
            raise ValueError("COMPOSITE_SUBJECT_SOURCE_BINDING_MISMATCH")
        if (
            observations.reporting_currency != subject.reporting_currency
            or self.proposed_at != self.evaluation.evaluated_at
        ):
            raise ValueError("COMPOSITE_SUBJECT_EVALUATION_BINDING_MISMATCH")
        expected = evaluate_monthly_eligibility(
            self.policy_approval.approval.proposal.policy,
            observations,
            evaluated_at=self.proposed_at,
            universe_content_hash=subject.universe.content_hash,
        )
        if expected != self.evaluation:
            raise ValueError("COMPOSITE_ELIGIBILITY_EVALUATION_RECOMPUTATION_MISMATCH")
        self.observations = observations
        bind_content(self)
        return self


class SubjectEvaluationProposal(SubjectEvaluationProposalContent):
    product_version: Literal["v1"] = "v1"
    policy_approval: SubjectPolicyApproval


class HistoricalSubjectEvaluationProposal(SubjectEvaluationProposalContent):
    product_version: Literal["v2"] = "v2"
    policy_approval: HistoricalSubjectPolicyApproval
    operation_verification: HistoricalPolicyVerification

    @model_validator(mode="after")
    def require_historical_operation(self) -> "HistoricalSubjectEvaluationProposal":
        require_subject_operation(
            self,
            self.operation_verification,
            "EVALUATION_PROPOSAL",
            self.proposed_by,
            self.proposed_at,
        )
        return self


SubjectEvaluationProposalVariant = Annotated[
    SubjectEvaluationProposal | HistoricalSubjectEvaluationProposal,
    Field(discriminator="product_version"),
]
EVALUATION_PROPOSAL_ADAPTER: TypeAdapter[SubjectEvaluationProposalVariant] = TypeAdapter(
    SubjectEvaluationProposalVariant
)


def subject_approval_claims(
    proposal: SubjectEvaluationProposalContent, actor: str, instant: str
) -> str:
    subject = proposal.policy_approval.proposal.subject
    return hash_canonical_payload(
        {
            "purpose": "ELIGIBILITY_POLICY_EVALUATION",
            "subject_content_hash": subject.content_hash,
            "proposal_content_hash": proposal.content_hash,
            "approved_by": actor,
            "approved_at": instant,
        }
    )


class SubjectEvaluationApprovalContent(StrictAuthorityModel):
    product_name: Literal["CompositeSubjectEvaluationApproval"] = (
        "CompositeSubjectEvaluationApproval"
    )
    product_version: Literal["v1", "v2"]
    evidence_kind: Literal["SYNTHETIC_UNSIGNED", "QUALIFIED_VERIFICATION_RECEIPT"]
    official_activation: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    publication_posture: Literal["NOT_PUBLISHED"] = "NOT_PUBLISHED"
    proposal: SubjectEvaluationProposalVariant
    approved_by: Identity
    approved_at: UtcInstant
    claims_digest: Digest
    membership_content_hash: Digest
    universe_content_hash: Digest
    verification: VerificationReceipt
    content_hash: str = ""

    @model_validator(mode="after")
    def require_independent_approval(self) -> "SubjectEvaluationApprovalContent":
        self.proposal = EVALUATION_PROPOSAL_ADAPTER.validate_python(
            self.proposal.model_dump(mode="json")
        )
        if self.product_version != self.proposal.product_version:
            raise ValueError("COMPOSITE_SUBJECT_CONTROL_VERSION_MISMATCH")
        if self.approved_by == self.proposal.proposed_by:
            raise ValueError("COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN")
        if datetime.fromisoformat(self.approved_at) < datetime.fromisoformat(
            self.proposal.proposed_at
        ):
            raise ValueError("COMPOSITE_ELIGIBILITY_APPROVAL_BEFORE_PROPOSAL")
        if self.claims_digest != subject_approval_claims(
            self.proposal, self.approved_by, self.approved_at
        ):
            raise ValueError("COMPOSITE_SUBJECT_APPROVAL_CLAIMS_MISMATCH")
        require_verification_scope(
            self.verification.request,
            self.proposal.policy_approval.proposal.subject,
            "ELIGIBILITY_POLICY_EVALUATION",
            self.claims_digest,
        )
        qualified = self.verification.posture == "QUALIFIED_RECEIPT"
        if qualified != (self.evidence_kind == "QUALIFIED_VERIFICATION_RECEIPT"):
            raise ValueError("COMPOSITE_SUBJECT_VERIFICATION_POSTURE_MISMATCH")
        bind_content(self)
        return self


class SubjectEvaluationApproval(SubjectEvaluationApprovalContent):
    product_version: Literal["v1"] = "v1"
    proposal: SubjectEvaluationProposal


class HistoricalSubjectEvaluationApproval(SubjectEvaluationApprovalContent):
    product_version: Literal["v2"] = "v2"
    proposal: HistoricalSubjectEvaluationProposal
    evidence_kind: Literal["SYNTHETIC_UNSIGNED"] = "SYNTHETIC_UNSIGNED"
    operation_verification: HistoricalPolicyVerification

    @model_validator(mode="after")
    def require_historical_operation(self) -> "HistoricalSubjectEvaluationApproval":
        require_synthetic_receipt(self.verification)
        require_subject_operation(
            self.proposal,
            self.operation_verification,
            "EVALUATION_APPROVAL",
            self.approved_by,
            self.approved_at,
        )
        return self


SubjectEvaluationApprovalVariant = Annotated[
    SubjectEvaluationApproval | HistoricalSubjectEvaluationApproval,
    Field(discriminator="product_version"),
]
EVALUATION_APPROVAL_ADAPTER: TypeAdapter[SubjectEvaluationApprovalVariant] = TypeAdapter(
    SubjectEvaluationApprovalVariant
)


def require_synthetic_history(proof: HistoricalPolicyVerification) -> None:
    if proof.posture != "SYNTHETIC_NON_CERTIFYING":
        raise ValueError("COMPOSITE_SUBJECT_HISTORICAL_POLICY_POSTURE_UNAVAILABLE")


def require_synthetic_receipt(receipt: VerificationReceipt) -> None:
    if receipt.posture != "SYNTHETIC_NON_CERTIFYING":
        raise ValueError("COMPOSITE_SUBJECT_HISTORICAL_POLICY_POSTURE_UNAVAILABLE")


def require_subject_operation(
    proposal: HistoricalSubjectEvaluationProposal,
    proof: HistoricalPolicyVerification,
    operation: str,
    actor: str,
    instant: str,
) -> None:
    require_synthetic_history(proof)
    policy = proposal.policy_approval.approval
    if proof.mapping != policy.verification.mapping:
        raise ValueError("COMPOSITE_HISTORICAL_POLICY_MAPPING_MISMATCH")
    if datetime.fromisoformat(instant) < datetime.fromisoformat(policy.approved_at):
        raise ValueError("COMPOSITE_ELIGIBILITY_APPROVAL_BEFORE_PROPOSAL")
    intent = (
        hash_canonical_payload(
            proposal.model_dump(mode="json", exclude={"content_hash", "operation_verification"})
        )
        if operation == "EVALUATION_PROPOSAL"
        else proposal.content_hash
    )
    request = proof.request
    if (
        request.operation,
        request.revision,
        request.actor_id,
        request.requested_at,
        request.intent_digest,
    ) != (operation, proposal.evaluation_revision, actor, instant, intent):
        raise ValueError("COMPOSITE_HISTORICAL_POLICY_INTENT_MISMATCH")


def require_verification_scope(
    request: VerificationRequest,
    subject: EligibilitySubject,
    purpose: VerificationPurpose,
    claims: str,
) -> None:
    from src.core.composite_eligibility.policy import month_window

    first, last = month_window(subject.month)
    if (
        request.purpose,
        request.tenant_id,
        request.composite_id,
        request.definition_version,
        request.subject_content_hash,
        request.claims_digest,
        request.effective_from,
        request.effective_to,
    ) != (
        purpose,
        subject.tenant_id,
        subject.composite_id,
        subject.definition_version,
        subject.content_hash,
        claims,
        first,
        last,
    ):
        raise ValueError("COMPOSITE_SUBJECT_VERIFICATION_BINDING_MISMATCH")


StagedControl = Annotated[
    SubjectPolicyProposalVariant
    | SubjectPolicyApprovalVariant
    | SubjectEvaluationProposalVariant
    | SubjectEvaluationApprovalVariant,
    Field(discriminator="product_name"),
]
STAGED_CONTROL_ADAPTER: TypeAdapter[StagedControl] = TypeAdapter(StagedControl)


def control_subject(control: StagedControl) -> EligibilitySubject:
    if isinstance(control, SubjectPolicyProposalContent):
        return control.subject
    if isinstance(control, SubjectPolicyApprovalContent):
        return control.proposal.subject
    if isinstance(control, SubjectEvaluationProposalContent):
        return control.policy_approval.proposal.subject
    return control.proposal.policy_approval.proposal.subject


def control_revision(control: StagedControl) -> str:
    if isinstance(control, SubjectPolicyProposalContent):
        return control.proposal.proposal_revision
    if isinstance(control, SubjectPolicyApprovalContent):
        return control.proposal.proposal.proposal_revision
    if isinstance(control, SubjectEvaluationProposalContent):
        return control.evaluation_revision
    return control.proposal.evaluation_revision
