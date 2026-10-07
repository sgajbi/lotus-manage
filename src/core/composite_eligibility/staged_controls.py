"""Subject-bound wrappers reuse the monthly policy and calculation contracts."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from src.core.common.canonical import hash_canonical_payload
from src.core.composite_authority_models import Digest, Identity, StrictAuthorityModel
from src.core.composite_eligibility.approval import MonthlyPolicyApproval, MonthlyPolicyProposal
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


class SubjectPolicyProposal(StrictAuthorityModel):
    product_name: Literal["CompositeSubjectPolicyProposal"] = "CompositeSubjectPolicyProposal"
    product_version: Literal["v1"] = "v1"
    subject: EligibilitySubject
    proposal: MonthlyPolicyProposal
    content_hash: str = ""

    @model_validator(mode="after")
    def require_subject_policy(self) -> "SubjectPolicyProposal":
        self.subject = EligibilitySubject.model_validate(self.subject.model_dump(mode="json"))
        self.proposal = MonthlyPolicyProposal.model_validate(self.proposal.model_dump(mode="json"))
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


class SubjectPolicyApproval(StrictAuthorityModel):
    product_name: Literal["CompositeSubjectPolicyApproval"] = "CompositeSubjectPolicyApproval"
    product_version: Literal["v1"] = "v1"
    proposal: SubjectPolicyProposal
    approval: MonthlyPolicyApproval
    verification: VerificationReceipt
    content_hash: str = ""

    @model_validator(mode="after")
    def require_exact_policy_approval(self) -> "SubjectPolicyApproval":
        self.proposal = SubjectPolicyProposal.model_validate(self.proposal.model_dump(mode="json"))
        self.approval = MonthlyPolicyApproval.model_validate(self.approval.model_dump(mode="json"))
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


class SubjectEvaluationProposal(StrictAuthorityModel):
    product_name: Literal["CompositeSubjectEvaluationProposal"] = (
        "CompositeSubjectEvaluationProposal"
    )
    product_version: Literal["v1"] = "v1"
    evaluation_kind: Literal["INITIAL"] = "INITIAL"
    policy_approval: SubjectPolicyApproval
    evaluation_revision: Identity
    target_membership_revision: Identity
    observations: MonthlyEligibilityObservations
    observation_binding: DpmCompositeUniverseSourceProduct
    evaluation: MonthlyEligibilityEvaluation
    proposed_by: Identity
    proposed_at: UtcInstant
    content_hash: str = ""

    @model_validator(mode="after")
    def require_reproducible_evaluation(self) -> "SubjectEvaluationProposal":
        self.policy_approval = SubjectPolicyApproval.model_validate(
            self.policy_approval.model_dump(mode="json")
        )
        subject = self.policy_approval.proposal.subject
        observations = MonthlyEligibilityObservations.model_validate(
            self.observations.model_dump(mode="json")
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


def subject_approval_claims(proposal: SubjectEvaluationProposal, actor: str, instant: str) -> str:
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


class SubjectEvaluationApproval(StrictAuthorityModel):
    product_name: Literal["CompositeSubjectEvaluationApproval"] = (
        "CompositeSubjectEvaluationApproval"
    )
    product_version: Literal["v1"] = "v1"
    evidence_kind: Literal["SYNTHETIC_UNSIGNED", "QUALIFIED_VERIFICATION_RECEIPT"]
    official_activation: Literal["UNAVAILABLE"] = "UNAVAILABLE"
    publication_posture: Literal["NOT_PUBLISHED"] = "NOT_PUBLISHED"
    proposal: SubjectEvaluationProposal
    approved_by: Identity
    approved_at: UtcInstant
    claims_digest: Digest
    membership_content_hash: Digest
    universe_content_hash: Digest
    verification: VerificationReceipt
    content_hash: str = ""

    @model_validator(mode="after")
    def require_independent_approval(self) -> "SubjectEvaluationApproval":
        self.proposal = SubjectEvaluationProposal.model_validate(
            self.proposal.model_dump(mode="json")
        )
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
    SubjectPolicyProposal
    | SubjectPolicyApproval
    | SubjectEvaluationProposal
    | SubjectEvaluationApproval,
    Field(discriminator="product_name"),
]
STAGED_CONTROL_ADAPTER: TypeAdapter[StagedControl] = TypeAdapter(StagedControl)


def control_subject(control: StagedControl) -> EligibilitySubject:
    if isinstance(control, SubjectPolicyProposal):
        return control.subject
    if isinstance(control, SubjectPolicyApproval):
        return control.proposal.subject
    if isinstance(control, SubjectEvaluationProposal):
        return control.policy_approval.proposal.subject
    return control.proposal.policy_approval.proposal.subject


def control_revision(control: StagedControl) -> str:
    if isinstance(control, SubjectPolicyProposal):
        return control.proposal.proposal_revision
    if isinstance(control, SubjectPolicyApproval):
        return control.proposal.proposal.proposal_revision
    if isinstance(control, SubjectEvaluationProposal):
        return control.evaluation_revision
    return control.proposal.evaluation_revision
