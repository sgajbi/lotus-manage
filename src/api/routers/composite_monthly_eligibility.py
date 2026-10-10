"""Registered monthly policy control and read-only eligibility assessment."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import Field, ValidationError
from src.api.composite_identity import (
    CompositeTrustedIdentity,
    composite_trusted_identity_required,
    composite_write_identity_required,
)
from src.api.dependencies import get_composite_monthly_eligibility_service
from src.api.dependencies import get_composite_monthly_evaluation_service
from src.api.services.composite_monthly_evaluation import (
    CompositeMonthlyEvaluationApplicationService,
    MonthlyEvaluationRequest,
    MonthlyAmendmentRequest,
)
from src.core.composite_eligibility.monthly_amendment import (
    MonthlyProposal,
    MonthlyApproval,
)

from src.api.services.composite_monthly_eligibility import (
    CompositeMonthlyEligibilityApplicationService,
    MonthlyPolicyValidationRequest,
    MonthlySimulationRequest,
    MonthlyDiffRequest,
    MonthlyProposalRequest,
    MonthlyApprovalRequest,
)
from src.core.composite_eligibility.approval import MonthlyPolicyProposal
from src.core.composite_eligibility.approval import (
    MonthlyPolicyApprovalVariant,
    MonthlyPolicyProposalVariant,
)
from src.core.composite_eligibility.historical_policy import HistoricalMonthlyPolicyProposal
from src.api.services.historical_policy_admission import (
    HistoricalPolicyAdmissionRequest,
    HistoricalPolicyAdmissionApplicationService,
)
from src.core.composite_eligibility.diff import MonthlyEligibilityDiff
from src.core.composite_eligibility.policy import ResolvedMonthlyPolicy
from src.core.composite_eligibility.evaluation import MonthlyEligibilityEvaluation

MonthlyProposalResponse = Annotated[MonthlyProposal, Field(discriminator="product_version")]
MonthlyApprovalResponse = Annotated[MonthlyApproval, Field(discriminator="product_version")]
MonthlyPolicyProposalResponse = Annotated[
    MonthlyPolicyProposalVariant, Field(discriminator="product_version")
]
MonthlyPolicyApprovalResponse = Annotated[
    MonthlyPolicyApprovalVariant, Field(discriminator="product_version")
]

router = APIRouter(
    prefix="/rebalance/composites", tags=["lotus-manage Composite Monthly Eligibility"]
)


@router.post(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/validate",
    response_model=ResolvedMonthlyPolicy,
    summary="Validate a synthetic monthly policy against a retained composite definition",
    description="Read-only resolution. Does not approve configuration or activate official eligibility.",
)
def validate_monthly_policy(
    composite_id: str,
    definition_version: str,
    request: MonthlyPolicyValidationRequest,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: CompositeMonthlyEligibilityApplicationService = Depends(
        get_composite_monthly_eligibility_service
    ),
) -> ResolvedMonthlyPolicy:
    try:
        return service.validate_policy(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            command=request,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


@router.post(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/simulate",
    response_model=MonthlyEligibilityEvaluation,
    summary="Simulate monthly rules over pinned source observations and retained universe evidence",
    description=(
        "Read-only; never publishes membership. Requires an owning source adapter; the default "
        "returns unavailable. Request bodies cannot supply observations, tenant authority or clock."
    ),
)
def simulate_monthly_eligibility(
    composite_id: str,
    definition_version: str,
    request: MonthlySimulationRequest,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: CompositeMonthlyEligibilityApplicationService = Depends(
        get_composite_monthly_eligibility_service
    ),
) -> MonthlyEligibilityEvaluation:
    try:
        return service.simulate(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            command=request,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


@router.post(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/diff",
    response_model=MonthlyEligibilityDiff,
    summary="Compare synthetic monthly policies against the same immutable source inputs",
    description="Read-only comparison at one server instant. Neither candidate is approved or published.",
)
def diff_monthly_eligibility(
    composite_id: str,
    definition_version: str,
    request: MonthlyDiffRequest,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: CompositeMonthlyEligibilityApplicationService = Depends(
        get_composite_monthly_eligibility_service
    ),
) -> MonthlyEligibilityDiff:
    try:
        return service.diff(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            command=request,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


def _monthly_approval_identity_required(
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
) -> CompositeTrustedIdentity:
    if identity.role != "DPM_COMPOSITE_ADMIN":
        raise _problem(status.HTTP_403_FORBIDDEN, "COMPOSITE_POLICY_APPROVAL_ROLE_FORBIDDEN")
    return identity


@router.put(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/policies/{month}/proposals/{proposal_revision}",
    response_model=MonthlyPolicyProposal,
    summary="Retain an immutable prospective synthetic monthly policy proposal",
    description="Maker and time are server-admitted. References are retained evidence, not bank approval.",
)
def propose_monthly_policy(
    composite_id: str,
    definition_version: str,
    month: str,
    proposal_revision: str,
    request: MonthlyProposalRequest,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: CompositeMonthlyEligibilityApplicationService = Depends(
        get_composite_monthly_eligibility_service
    ),
) -> MonthlyPolicyProposal:
    try:
        return service.propose_policy(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=month,
            proposal_revision=proposal_revision,
            actor_id=identity.actor_id,
            command=request,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


@router.put(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/policies/{month}/proposals/{proposal_revision}/approval",
    response_model=MonthlyPolicyApprovalResponse,
    summary="Independently approve exact prospective synthetic configuration content",
    description="A synthetic control decision; does not verify bank IAM, activate official eligibility or publish membership.",
)
def approve_monthly_policy(
    composite_id: str,
    definition_version: str,
    month: str,
    proposal_revision: str,
    request: MonthlyApprovalRequest,
    identity: CompositeTrustedIdentity = Depends(_monthly_approval_identity_required),
    service: CompositeMonthlyEligibilityApplicationService = Depends(
        get_composite_monthly_eligibility_service
    ),
) -> MonthlyPolicyApprovalVariant:
    try:
        return service.approve_policy(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=month,
            proposal_revision=proposal_revision,
            actor_id=identity.actor_id,
            command=request,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


@router.put(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/policies/{month}/proposals/{proposal_revision}/historical-admission",
    response_model=HistoricalMonthlyPolicyProposal,
    summary="Retain a present admission proposal for an exact original historical policy",
    description="The server-owned verifier resolves original bytes and their actual signing contract. The normalized mapping and present verification remain separate. Default unavailable; no caller trust, original timestamp override or institutional activation.",
)
def propose_historical_monthly_policy(
    composite_id: str,
    definition_version: str,
    month: str,
    proposal_revision: str,
    request: HistoricalPolicyAdmissionRequest,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: CompositeMonthlyEligibilityApplicationService = Depends(
        get_composite_monthly_eligibility_service
    ),
) -> HistoricalMonthlyPolicyProposal:
    try:
        return HistoricalPolicyAdmissionApplicationService(
            service.repository, service.historical_admission, service.clock
        ).propose(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=month,
            proposal_revision=proposal_revision,
            actor_id=identity.actor_id,
            command=request,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


@router.get(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/policies/{month}/proposals/{proposal_revision}",
    response_model=MonthlyPolicyProposalResponse,
    summary="Read one exact tenant-scoped monthly policy proposal",
)
def get_monthly_policy_proposal(
    composite_id: str,
    definition_version: str,
    month: str,
    proposal_revision: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: CompositeMonthlyEligibilityApplicationService = Depends(
        get_composite_monthly_eligibility_service
    ),
) -> MonthlyPolicyProposalVariant:
    try:
        return service.get_policy_proposal(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=month,
            proposal_revision=proposal_revision,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


@router.get(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/policies/{month}/approval",
    response_model=MonthlyPolicyApprovalResponse,
    summary="Read retained synthetic monthly configuration approval",
)
def get_monthly_policy_approval(
    composite_id: str,
    definition_version: str,
    month: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: CompositeMonthlyEligibilityApplicationService = Depends(
        get_composite_monthly_eligibility_service
    ),
) -> MonthlyPolicyApprovalVariant:
    try:
        return service.get_policy_approval(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            month=month,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


@router.put(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/evaluations/{evaluation_revision}",
    response_model=MonthlyProposalResponse,
    summary="Retain a reproducible monthly evaluation of the exact approved prospective policy",
    description="Uses pinned source-owned observations, retained universe and current published parent. No caller-owned financial facts or clock.",
)
def propose_monthly_evaluation(
    composite_id: str,
    definition_version: str,
    evaluation_revision: str,
    request: MonthlyEvaluationRequest,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: CompositeMonthlyEvaluationApplicationService = Depends(
        get_composite_monthly_evaluation_service
    ),
) -> MonthlyProposal:
    try:
        return service.propose(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            evaluation_revision=evaluation_revision,
            actor_id=identity.actor_id,
            command=request,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


@router.put(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/evaluations/{evaluation_revision}/source-amendment",
    response_model=MonthlyProposalResponse,
    summary="Propose a source correction to one exact approved membership month",
    description="Binds the selected original/predecessor approval, exact predecessor receipt, current projection and publication sequence. Observations come from configured source owners. Same approved policy only; staged roots and corrections with later approved months are unsupported. Independent approval uses the existing evaluation approval operation.",
)
def propose_monthly_source_amendment(
    composite_id: str,
    definition_version: str,
    evaluation_revision: str,
    request: MonthlyAmendmentRequest,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: CompositeMonthlyEvaluationApplicationService = Depends(
        get_composite_monthly_evaluation_service
    ),
) -> MonthlyProposal:
    try:
        return service.propose(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            evaluation_revision=evaluation_revision,
            actor_id=identity.actor_id,
            command=request,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


@router.put(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/evaluations/{evaluation_revision}/approval",
    response_model=MonthlyApprovalResponse,
    summary="Independently approve and atomically publish one evaluated membership month",
    description="Atomic approval, canonical membership/universe and publication custody. Synthetic unsigned control is not bank IAM or official activation.",
)
def approve_monthly_evaluation(
    composite_id: str,
    definition_version: str,
    evaluation_revision: str,
    request: MonthlyApprovalRequest,
    identity: CompositeTrustedIdentity = Depends(_monthly_approval_identity_required),
    service: CompositeMonthlyEvaluationApplicationService = Depends(
        get_composite_monthly_evaluation_service
    ),
) -> MonthlyApproval:
    try:
        return service.approve(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            evaluation_revision=evaluation_revision,
            actor_id=identity.actor_id,
            command=request,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


@router.get(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/evaluations/{evaluation_revision}",
    response_model=MonthlyProposalResponse,
    summary="Read exact retained monthly inputs and all-rule evidence",
)
def get_monthly_evaluation(
    composite_id: str,
    definition_version: str,
    evaluation_revision: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: CompositeMonthlyEvaluationApplicationService = Depends(
        get_composite_monthly_evaluation_service
    ),
) -> MonthlyProposal:
    try:
        return service.get_proposal(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            evaluation_revision=evaluation_revision,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


@router.get(
    "/{composite_id}/definitions/{definition_version}/monthly-eligibility/evaluations/{evaluation_revision}/approval",
    response_model=MonthlyApprovalResponse,
    summary="Read approval bound to the canonical published membership and universe",
)
def get_monthly_evaluation_approval(
    composite_id: str,
    definition_version: str,
    evaluation_revision: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: CompositeMonthlyEvaluationApplicationService = Depends(
        get_composite_monthly_evaluation_service
    ),
) -> MonthlyApproval:
    try:
        return service.get_approval(
            tenant_id=identity.tenant_id,
            composite_id=composite_id,
            definition_version=definition_version,
            evaluation_revision=evaluation_revision,
        )
    except ValueError as exc:
        raise _monthly_domain_error(exc) from exc


def _monthly_domain_error(exc: ValueError) -> HTTPException:
    raw = str(exc)
    public_codes = {
        "COMPOSITE_MONTHLY_AMENDMENT_CLOCK_MISMATCH",
        "COMPOSITE_MONTHLY_AUTHORITY_HISTORY_UNAVAILABLE",
        "COMPOSITE_MONTHLY_AUTHORITY_HISTORY_LIMIT",
        "COMPOSITE_MONTHLY_AUTHORITY_SCOPE_MISMATCH",
        "COMPOSITE_MONTHLY_AUTHORITY_ROOT_AMBIGUOUS",
        "COMPOSITE_MONTHLY_AUTHORITY_RECORD_AMBIGUOUS",
        "COMPOSITE_MONTHLY_AUTHORITY_PREDECESSOR_MISMATCH",
        "COMPOSITE_MONTHLY_AUTHORITY_ORIGINAL_MISMATCH",
        "COMPOSITE_MONTHLY_AUTHORITY_FORK_FORBIDDEN",
        "COMPOSITE_MONTHLY_AUTHORITY_HISTORY_DISCONNECTED",
        "COMPOSITE_MONTHLY_AUTHORITY_HISTORY_CYCLE",
        "COMPOSITE_MONTHLY_AMENDMENT_STALE_AUTHORITY",
        "COMPOSITE_MONTHLY_AMENDMENT_STALE_PROJECTION",
        "COMPOSITE_MONTHLY_AMENDMENT_PREDECESSOR_RECEIPT_MISMATCH",
        "COMPOSITE_MONTHLY_AMENDMENT_DEPENDENT_MONTH_UNSUPPORTED",
        "COMPOSITE_MONTHLY_AMENDMENT_STAGED_ROOT_UNSUPPORTED",
        "COMPOSITE_MONTHLY_AMENDMENT_POLICY_CHANGE_UNSUPPORTED",
        "COMPOSITE_MONTHLY_AMENDMENT_POPULATION_CHANGE_UNSUPPORTED",
        "COMPOSITE_MONTHLY_AMENDMENT_SOURCE_UNCHANGED",
        "COMPOSITE_MONTHLY_AMENDMENT_REASON_REQUIRED",
        "COMPOSITE_MONTHLY_AMENDMENT_AUTHORITY_MISMATCH",
        "COMPOSITE_MONTHLY_AMENDMENT_PREDECESSOR_MISMATCH",
        "COMPOSITE_MONTHLY_AMENDMENT_PREDECESSOR_VERSION_MISMATCH",
        "COMPOSITE_MONTHLY_AMENDMENT_PROJECTION_PARENT_INVALID",
        "COMPOSITE_MONTHLY_AMENDMENT_EVIDENCE_AMBIGUOUS",
        "COMPOSITE_MONTHLY_AMENDMENT_WINDOW_MISMATCH",
        "COMPOSITE_MONTHLY_AMENDMENT_PROJECTION_PARENT_MISMATCH",
        "COMPOSITE_MONTHLY_AMENDMENT_REVISION_REUSED",
        "COMPOSITE_MONTHLY_AMENDMENT_SOURCE_EVIDENCE_REQUIRED",
        "COMPOSITE_SOURCE_TRANSPORT_UNAVAILABLE",
        "COMPOSITE_SOURCE_TRANSPORT_REJECTED",
        "COMPOSITE_SOURCE_RESPONSE_INVALID",
        "COMPOSITE_ELIGIBILITY_SOURCE_OWNER_MISMATCH",
        "COMPOSITE_ELIGIBILITY_APPROVED_POLICY_NOT_FOUND",
        "COMPOSITE_ELIGIBILITY_APPROVED_POLICY_MISMATCH",
        "COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_NOT_FOUND",
        "COMPOSITE_ELIGIBILITY_EVALUATION_APPROVAL_NOT_FOUND",
        "COMPOSITE_ELIGIBILITY_EVALUATION_PROPOSAL_IMMUTABLE_CONFLICT",
        "COMPOSITE_ELIGIBILITY_EVALUATION_APPROVAL_PROPOSAL_MISMATCH",
        "COMPOSITE_ELIGIBILITY_RETAINED_UNIVERSE_MISMATCH",
        "COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP",
        "COMPOSITE_ELIGIBILITY_TARGET_REVISION_REUSED",
        "COMPOSITE_ELIGIBILITY_ACTIVE_EVALUATION_CONFLICT",
        "COMPOSITE_ELIGIBILITY_TARGET_REVISION_EXISTS",
        "COMPOSITE_ELIGIBILITY_PUBLICATION_UNIVERSE_INCOMPLETE",
        "COMPOSITE_ELIGIBILITY_PUBLICATION_SOURCE_NOT_FINALIZED",
        "COMPOSITE_ELIGIBILITY_DISCRETIONARY_FACT_UNAVAILABLE",
        "COMPOSITE_ELIGIBILITY_APPROVED_PUBLICATION_MISMATCH",
        "COMPOSITE_DEFINITION_NOT_FOUND",
        "COMPOSITE_UNIVERSE_ATTESTATION_NOT_FOUND",
        "COMPOSITE_ELIGIBILITY_SOURCE_UNAVAILABLE",
        "COMPOSITE_ELIGIBILITY_SOURCE_REFERENCE_UNAVAILABLE",
        "COMPOSITE_ELIGIBILITY_UNIVERSE_CONTENT_MISMATCH",
        "COMPOSITE_ELIGIBILITY_UNIVERSE_WINDOW_INCOMPLETE",
        "COMPOSITE_ELIGIBILITY_UNIVERSE_MEMBERSHIP_MISMATCH",
        "COMPOSITE_ELIGIBILITY_SOURCE_SCOPE_MISMATCH",
        "COMPOSITE_ELIGIBILITY_SOURCE_CUT_MISMATCH",
        "COMPOSITE_ELIGIBILITY_SOURCE_REVISION_MISMATCH",
        "COMPOSITE_HISTORICAL_POLICY_ADMISSION_UNAVAILABLE",
        "COMPOSITE_HISTORICAL_POLICY_RESPONSE_INVALID",
        "COMPOSITE_HISTORICAL_POLICY_PROVIDER_REJECTED",
        "COMPOSITE_HISTORICAL_POLICY_CONTENT_MISMATCH",
        "COMPOSITE_HISTORICAL_POLICY_VERIFIER_SIGNATURE_INVALID",
        "COMPOSITE_HISTORICAL_POLICY_TRUST_MISMATCH",
        "COMPOSITE_HISTORICAL_POLICY_RAW_INVALID",
        "COMPOSITE_HISTORICAL_POLICY_RAW_MISMATCH",
        "COMPOSITE_HISTORICAL_POLICY_ORIGINAL_CLOCK_INVALID",
        "COMPOSITE_HISTORICAL_POLICY_MAPPING_MISMATCH",
        "COMPOSITE_HISTORICAL_POLICY_INDEPENDENCE_REQUIRED",
        "COMPOSITE_HISTORICAL_POLICY_ADMISSION_WINDOW_INVALID",
        "COMPOSITE_HISTORICAL_POLICY_REQUEST_MISMATCH",
        "COMPOSITE_HISTORICAL_POLICY_INTENT_MISMATCH",
        "COMPOSITE_ELIGIBILITY_SOURCE_MONTH_MISMATCH",
        "COMPOSITE_ELIGIBILITY_SOURCE_CURRENCY_MISMATCH",
        "COMPOSITE_ELIGIBILITY_SOURCE_UNIVERSE_MISMATCH",
        "COMPOSITE_ELIGIBILITY_SOURCE_CONTENT_MISMATCH",
        "COMPOSITE_ELIGIBILITY_FUTURE_SOURCE_GENERATION",
        "COMPOSITE_ELIGIBILITY_DUPLICATE_PORTFOLIO_CONFLICT",
        "COMPOSITE_ELIGIBILITY_MONTH_INVALID",
        "COMPOSITE_ELIGIBILITY_THRESHOLD_REQUIRED",
        "COMPOSITE_ELIGIBILITY_LAYER_SCOPE_MISMATCH",
        "COMPOSITE_ELIGIBILITY_INHERITANCE_ORDER_INVALID",
        "COMPOSITE_ELIGIBILITY_POLICY_NOT_EFFECTIVE",
        "COMPOSITE_ELIGIBILITY_OVERRIDE_FORBIDDEN",
        "COMPOSITE_ELIGIBILITY_LAYER_BOUND_EXCEEDED",
        "COMPOSITE_ELIGIBILITY_DIFF_BINDING_MISMATCH",
        "COMPOSITE_ELIGIBILITY_DIFF_UNIVERSE_MISMATCH",
        "COMPOSITE_ELIGIBILITY_PROPOSAL_NOT_FOUND",
        "COMPOSITE_ELIGIBILITY_APPROVAL_NOT_FOUND",
        "COMPOSITE_ELIGIBILITY_STALE_PROPOSAL",
        "COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN",
        "COMPOSITE_ELIGIBILITY_APPROVAL_BEFORE_PROPOSAL",
        "COMPOSITE_ELIGIBILITY_RETROSPECTIVE_POLICY_FORBIDDEN",
        "COMPOSITE_ELIGIBILITY_PROPOSAL_IMMUTABLE_CONFLICT",
        "COMPOSITE_ELIGIBILITY_ACTIVE_POLICY_CONFLICT",
        "COMPOSITE_ELIGIBILITY_APPROVAL_PROPOSAL_MISMATCH",
    }
    if isinstance(exc, ValidationError):
        known = {
            str(error.get("ctx", {}).get("error", ""))
            for error in exc.errors(include_input=False, include_url=False)
        } & public_codes
        raw = next(iter(known)) if len(known) == 1 else ""
    code = raw if raw in public_codes else "COMPOSITE_ELIGIBILITY_INPUT_INVALID"
    if code.endswith("UNAVAILABLE"):
        return _problem(status.HTTP_503_SERVICE_UNAVAILABLE, code)
    if code.endswith("NOT_FOUND"):
        return _problem(status.HTTP_404_NOT_FOUND, code)
    if code.endswith("CONFLICT") or code in {
        "COMPOSITE_MONTHLY_AMENDMENT_STALE_AUTHORITY",
        "COMPOSITE_MONTHLY_AMENDMENT_STALE_PROJECTION",
        "COMPOSITE_MONTHLY_AMENDMENT_DEPENDENT_MONTH_UNSUPPORTED",
        "COMPOSITE_MONTHLY_AUTHORITY_HISTORY_LIMIT",
        "COMPOSITE_ELIGIBILITY_STALE_PROPOSAL",
        "COMPOSITE_ELIGIBILITY_STALE_MEMBERSHIP",
    }:
        return _problem(status.HTTP_409_CONFLICT, code)
    return _problem(status.HTTP_422_UNPROCESSABLE_CONTENT, code)


def _problem(status_code: int, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": code})
