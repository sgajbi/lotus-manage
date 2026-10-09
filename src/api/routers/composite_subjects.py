"""Registered staging and server-resolved published eligibility evidence."""

from typing import Annotated, Callable, TypeVar
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import Field, ValidationError

from src.api.composite_identity import (
    CompositeTrustedIdentity,
    composite_trusted_identity_required,
    composite_write_identity_required,
)
from src.api.dependencies import get_composite_subject_service
from src.api.services.composite_subject_application import CompositeSubjectApplicationService
from src.api.services.composite_subject_requests import (
    SubjectRequest,
    SubjectPolicyRequest,
    SubjectApprovalRequest,
    SubjectEvaluationRequest,
    SubjectFinalizationRequest,
)
from src.core.composite_authority_models import EvidenceBinding
from src.core.composite_eligibility.staged_subject import EligibilitySubject
from src.core.composite_eligibility.staged_controls import (
    SubjectPolicyProposal,
    SubjectPolicyApproval,
    SubjectEvaluationProposal,
    SubjectEvaluationApproval,
)
from src.core.composite_eligibility.staged_publication import (
    SubjectFinalizationReceipt,
    authority_approval_follows_evaluation,
)
from src.core.composite_eligibility.monthly_evidence import MonthlyEligibilityPublicationReceipt

PublishedEligibilityReceipt = Annotated[
    SubjectFinalizationReceipt | MonthlyEligibilityPublicationReceipt,
    Field(discriminator="product_name"),
]

router = APIRouter(
    prefix="/rebalance/composites", tags=["lotus-manage Composite Eligibility Subjects"]
)
PREFIX = "/{composite_id}/eligibility-subjects/{definition_version}/{subject_revision}"
T = TypeVar("T")


def checker(
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
) -> CompositeTrustedIdentity:
    if identity.role != "DPM_COMPOSITE_ADMIN":
        raise HTTPException(
            403,
            detail={
                "code": "COMPOSITE_POLICY_APPROVAL_ROLE_FORBIDDEN",
                "message": "Composite administrator required.",
            },
        )
    return identity


@router.put(
    PREFIX,
    response_model=EligibilitySubject,
    summary="Reserve an immutable eligibility subject with source-owned population",
    description="No definition or membership is published. Sources are deployment-configured and synthetic only; absent configuration is unavailable. Request bodies cannot supply members, observations or server time.",
)
def create_subject(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    request: SubjectRequest,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> EligibilitySubject:
    return _call(
        lambda: service.create(
            (identity.tenant_id, composite_id, definition_version, subject_revision),
            identity.actor_id,
            request,
        )
    )


@router.get(
    PREFIX, response_model=EligibilitySubject, summary="Read one exact retained eligibility subject"
)
def get_subject(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> EligibilitySubject:
    return _call(
        lambda: service.subject(
            (identity.tenant_id, composite_id, definition_version, subject_revision)
        )
    )


@router.put(
    PREFIX + "/policies/{proposal_revision}",
    response_model=SubjectPolicyProposal,
    summary="Propose exact prospective monthly policy for an unpublished subject",
)
def propose_policy(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    proposal_revision: str,
    request: SubjectPolicyRequest,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> SubjectPolicyProposal:
    return _call(
        lambda: service.propose_policy(
            (identity.tenant_id, composite_id, definition_version, subject_revision),
            proposal_revision,
            identity.actor_id,
            request,
        )
    )


@router.get(
    PREFIX + "/policies/{proposal_revision}",
    response_model=SubjectPolicyProposal,
    summary="Read exact subject-bound policy proposal",
)
def get_policy(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    proposal_revision: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> SubjectPolicyProposal:
    return _call(
        lambda: service.control(
            (identity.tenant_id, composite_id, definition_version, subject_revision),
            proposal_revision,
            SubjectPolicyProposal,
        )
    )


@router.put(
    PREFIX + "/policies/{proposal_revision}/approval",
    response_model=SubjectPolicyApproval,
    summary="Independently approve exact prospective subject policy",
    description="Requires a server-owned verification receipt; default verifier is unavailable. Synthetic receipts are non-certifying.",
)
def approve_policy(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    proposal_revision: str,
    request: SubjectApprovalRequest,
    identity: CompositeTrustedIdentity = Depends(checker),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> SubjectPolicyApproval:
    return _call(
        lambda: service.approve_policy(
            (identity.tenant_id, composite_id, definition_version, subject_revision),
            proposal_revision,
            identity.actor_id,
            request,
        )
    )


@router.get(
    PREFIX + "/policies/{proposal_revision}/approval",
    response_model=SubjectPolicyApproval,
    summary="Read exact retained policy verification evidence",
)
def get_policy_approval(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    proposal_revision: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> SubjectPolicyApproval:
    return _call(
        lambda: service.control(
            (identity.tenant_id, composite_id, definition_version, subject_revision),
            proposal_revision,
            SubjectPolicyApproval,
        )
    )


@router.put(
    PREFIX + "/evaluations/{evaluation_revision}",
    response_model=SubjectEvaluationProposal,
    summary="Freeze actual source observations and evaluate an approved subject policy",
    description="Source selectors identify immutable cuts; no caller financial facts. All monthly rules are retained. No membership is published.",
)
def evaluate_subject(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    evaluation_revision: str,
    request: SubjectEvaluationRequest,
    identity: CompositeTrustedIdentity = Depends(composite_write_identity_required),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> SubjectEvaluationProposal:
    return _call(
        lambda: service.evaluate(
            (identity.tenant_id, composite_id, definition_version, subject_revision),
            evaluation_revision,
            identity.actor_id,
            request,
        )
    )


@router.get(
    PREFIX + "/evaluations/{evaluation_revision}",
    response_model=SubjectEvaluationProposal,
    summary="Read exact subject evaluation and all-rule evidence",
)
def get_evaluation(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    evaluation_revision: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> SubjectEvaluationProposal:
    return _call(
        lambda: service.control(
            (identity.tenant_id, composite_id, definition_version, subject_revision),
            evaluation_revision,
            SubjectEvaluationProposal,
        )
    )


@router.put(
    PREFIX + "/evaluations/{evaluation_revision}/approval",
    response_model=SubjectEvaluationApproval,
    summary="Independently approve frozen evaluation and canonical first-member projection",
    description="Approval remains NOT_PUBLISHED and official activation UNAVAILABLE. Finalization is a separate atomic operation.",
)
def approve_evaluation(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    evaluation_revision: str,
    request: SubjectApprovalRequest,
    identity: CompositeTrustedIdentity = Depends(checker),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> SubjectEvaluationApproval:
    return _call(
        lambda: service.approve_evaluation(
            (identity.tenant_id, composite_id, definition_version, subject_revision),
            evaluation_revision,
            identity.actor_id,
            request,
        )
    )


@router.get(
    PREFIX + "/evaluations/{evaluation_revision}/approval",
    response_model=SubjectEvaluationApproval,
    summary="Read immutable unpublished eligibility approval",
)
def get_evaluation_approval(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    evaluation_revision: str,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> SubjectEvaluationApproval:
    return _call(
        lambda: service.control(
            (identity.tenant_id, composite_id, definition_version, subject_revision),
            evaluation_revision,
            SubjectEvaluationApproval,
        )
    )


@router.put(
    PREFIX + "/finalization",
    response_model=SubjectFinalizationReceipt,
    summary="Atomically finalize the definition and independently evaluated first membership",
    description="Requires independent authority, method and provider verification. Publishes through the existing cursor; completeness remains UNVERIFIED.",
)
def finalize_subject(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    request: SubjectFinalizationRequest,
    response: Response,
    identity: CompositeTrustedIdentity = Depends(checker),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> SubjectFinalizationReceipt:
    receipt = _call(
        lambda: service.finalize(
            (identity.tenant_id, composite_id, definition_version, subject_revision),
            identity.actor_id,
            request,
        )
    )
    return _historical_receipt_response(receipt, response)


@router.get(
    PREFIX + "/finalization",
    response_model=SubjectFinalizationReceipt,
    summary="Read finalization only after verifying retained canonical publication custody",
)
def get_finalization(
    composite_id: str,
    definition_version: str,
    subject_revision: str,
    response: Response,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> SubjectFinalizationReceipt:
    receipt = _call(
        lambda: service.finalization(
            (identity.tenant_id, composite_id, definition_version, subject_revision)
        )
    )
    return _historical_receipt_response(receipt, response)


@router.post(
    "/{composite_id}/definitions/{definition_version}/eligibility-evidence/resolve",
    response_model=PublishedEligibilityReceipt,
    summary="Resolve exact eligibility evidence binding against retained published custody",
    description="Read-only lookup by exact product/version/revision/digest and admitted scope. CompositeSubjectEvaluationApproval returns retained subject finalization; CompositeMonthlyEvaluationApproval returns the monthly publication receipt with full definition, approval/source graph, bindings and UNVERIFIED completeness. Independent policy/evaluation custody, parent, membership, universe and canonical publication must agree in one read snapshot; no latest or correlation inference.",
)
def resolve_evidence(
    composite_id: str,
    definition_version: str,
    binding: EvidenceBinding,
    response: Response,
    identity: CompositeTrustedIdentity = Depends(composite_trusted_identity_required),
    service: CompositeSubjectApplicationService = Depends(get_composite_subject_service),
) -> PublishedEligibilityReceipt:
    receipt = _call(
        lambda: service.resolve_evidence(
            identity.tenant_id, composite_id, definition_version, binding
        )
    )
    if isinstance(receipt, MonthlyEligibilityPublicationReceipt):
        return receipt
    return _historical_receipt_response(receipt, response)


def _historical_receipt_response(
    receipt: SubjectFinalizationReceipt, response: Response
) -> SubjectFinalizationReceipt:
    finalization = receipt.finalization
    if not authority_approval_follows_evaluation(
        finalization.definition, finalization.evaluation_approval
    ):
        response.headers["X-Composite-Evidence-Diagnostic"] = "HISTORICAL_AUTHORITY_CLOCK_MISMATCH"
    return receipt


PUBLIC_CODES = {
    "COMPOSITE_MONTHLY_EVIDENCE_NOT_FOUND",
    "COMPOSITE_MONTHLY_EVIDENCE_UNAVAILABLE",
    "COMPOSITE_MONTHLY_EVIDENCE_BINDING_MISMATCH",
    "COMPOSITE_MONTHLY_EVIDENCE_SCOPE_MISMATCH",
    "COMPOSITE_MONTHLY_EVIDENCE_CONTENT_MISMATCH",
    "COMPOSITE_MONTHLY_EVIDENCE_DEFINITION_WIRE_INVALID",
    "COMPOSITE_MONTHLY_EVIDENCE_CUSTODY_INTEGRITY_CONFLICT",
    "COMPOSITE_ELIGIBILITY_CLOCK_MISMATCH",
    "COMPOSITE_SOURCE_TRANSPORT_UNAVAILABLE",
    "COMPOSITE_SOURCE_TRANSPORT_REJECTED",
    "COMPOSITE_SOURCE_RESPONSE_INVALID",
    "COMPOSITE_SUBJECT_NOT_FOUND",
    "COMPOSITE_SUBJECT_CONTROL_NOT_FOUND",
    "COMPOSITE_SUBJECT_FINALIZATION_NOT_FOUND",
    "COMPOSITE_SUBJECT_UNIVERSE_UNAVAILABLE",
    "COMPOSITE_SUBJECT_VERIFICATION_UNAVAILABLE",
    "COMPOSITE_SUBJECT_INSTITUTIONAL_VERIFICATION_UNAVAILABLE",
    "COMPOSITE_SUBJECT_STALE_CONTENT_CONFLICT",
    "COMPOSITE_SUBJECT_IMMUTABLE_CONFLICT",
    "COMPOSITE_SUBJECT_ACTIVE_CONTROL_CONFLICT",
    "COMPOSITE_SUBJECT_DEFINITION_RESERVED_CONFLICT",
    "COMPOSITE_SUBJECT_ALREADY_FINALIZED_CONFLICT",
    "COMPOSITE_SUBJECT_INTEGRITY_CONFLICT",
    "COMPOSITE_SUBJECT_CONTROL_INTEGRITY_CONFLICT",
    "COMPOSITE_SUBJECT_RECEIPT_INTEGRITY_CONFLICT",
    "COMPOSITE_SUBJECT_ELIGIBILITY_BINDING_MISMATCH",
    "COMPOSITE_SUBJECT_RETAINED_SUBJECT_MISMATCH",
    "COMPOSITE_SUBJECT_RETAINED_CONTROL_MISMATCH",
    "COMPOSITE_SUBJECT_PROJECTION_MISMATCH",
    "COMPOSITE_SUBJECT_VERIFICATION_BINDING_MISMATCH",
    "COMPOSITE_SUBJECT_REGISTRY_BINDING_MISMATCH",
    "COMPOSITE_SUBJECT_FUTURE_UNIVERSE_GENERATION",
    "COMPOSITE_SUBJECT_FINALIZER_FORBIDDEN",
    "COMPOSITE_SUBJECT_UNIVERSE_SCOPE_MISMATCH",
    "COMPOSITE_SUBJECT_SOURCE_BINDING_MISMATCH",
    "COMPOSITE_SUBJECT_DEFINITION_BINDING_MISMATCH",
    "COMPOSITE_SUBJECT_PROFILE_BINDING_MISMATCH",
    "COMPOSITE_ELIGIBILITY_SELF_APPROVAL_FORBIDDEN",
    "COMPOSITE_ELIGIBILITY_RETROSPECTIVE_POLICY_FORBIDDEN",
    "COMPOSITE_ELIGIBILITY_SOURCE_UNAVAILABLE",
    "COMPOSITE_ELIGIBILITY_SOURCE_OWNER_MISMATCH",
    "COMPOSITE_ELIGIBILITY_SOURCE_SCOPE_MISMATCH",
    "COMPOSITE_ELIGIBILITY_SOURCE_CUT_MISMATCH",
    "COMPOSITE_ELIGIBILITY_SOURCE_REVISION_MISMATCH",
    "COMPOSITE_ELIGIBILITY_SOURCE_CONTENT_MISMATCH",
    "COMPOSITE_ELIGIBILITY_SOURCE_MONTH_MISMATCH",
    "COMPOSITE_ELIGIBILITY_SOURCE_CURRENCY_MISMATCH",
    "COMPOSITE_ELIGIBILITY_SOURCE_UNIVERSE_MISMATCH",
    "COMPOSITE_ELIGIBILITY_PUBLICATION_UNIVERSE_INCOMPLETE",
    "COMPOSITE_ELIGIBILITY_PUBLICATION_SOURCE_NOT_FINALIZED",
    "COMPOSITE_ELIGIBILITY_DISCRETIONARY_FACT_UNAVAILABLE",
}


def _call(action: Callable[[], T]) -> T:
    try:
        return action()
    except ValueError as exc:
        code = str(exc)
        if isinstance(exc, ValidationError):
            known = {
                str(error.get("ctx", {}).get("error", ""))
                for error in exc.errors(include_input=False, include_url=False)
            } & PUBLIC_CODES
            code = next(iter(known)) if len(known) == 1 else ""
        code = code if code in PUBLIC_CODES else "COMPOSITE_SUBJECT_INPUT_INVALID"
        status = (
            503
            if code.endswith("UNAVAILABLE")
            else 404
            if code.endswith("NOT_FOUND")
            else 409
            if code.endswith("CONFLICT")
            else 403
            if code.endswith("FORBIDDEN")
            else 422
        )
        raise HTTPException(status, detail={"code": code, "message": code}) from exc
