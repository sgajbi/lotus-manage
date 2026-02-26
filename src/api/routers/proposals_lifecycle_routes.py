from datetime import datetime
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Path, Query, status

from src.api.routers import proposals as shared
from src.core.proposals import (
    ProposalCreateRequest,
    ProposalCreateResponse,
    ProposalDetailResponse,
    ProposalIdempotencyConflictError,
    ProposalNotFoundError,
    ProposalStateConflictError,
    ProposalStateTransitionRequest,
    ProposalStateTransitionResponse,
    ProposalTransitionError,
    ProposalValidationError,
    ProposalVersionDetail,
    ProposalVersionRequest,
    ProposalWorkflowService,
)
from src.core.proposals.models import ProposalApprovalRequest, ProposalListResponse


@shared.router.post(
    "/rebalance/proposals",
    response_model=ProposalCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Create and Persist Advisory Proposal",
    description=(
        "Runs advisory simulation + artifact generation and persists immutable proposal version, "
        "workflow creation event, and idempotency mapping."
    ),
)
def create_proposal(
    payload: ProposalCreateRequest,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required idempotency key for proposal-create deduplication.",
            examples=["proposal-create-idem-001"],
        ),
    ],
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation id captured in lifecycle audit reason payload.",
            examples=["corr-proposal-create-001"],
        ),
    ] = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalCreateResponse:
    shared._assert_lifecycle_enabled()
    try:
        return service.create_proposal(
            payload=payload,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
        )
    except ProposalIdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProposalValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@shared.router.get(
    "/rebalance/proposals/{proposal_id}",
    response_model=ProposalDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Proposal",
    description="Returns proposal summary, current immutable version, and last gate decision.",
)
def get_proposal(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    include_evidence: Annotated[
        bool,
        Query(
            description="Include full evidence bundle in current version payload.",
            examples=[True],
        ),
    ] = True,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalDetailResponse:
    shared._assert_lifecycle_enabled()
    try:
        return service.get_proposal(proposal_id=proposal_id, include_evidence=include_evidence)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/proposals",
    response_model=ProposalListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Proposals",
    description="Lists persisted proposals with optional filters and cursor pagination.",
)
def list_proposals(
    portfolio_id: Annotated[
        Optional[str],
        Query(description="Portfolio filter.", examples=["pf_01"]),
    ] = None,
    state: Annotated[
        Optional[str],
        Query(description="Current workflow state filter.", examples=["DRAFT"]),
    ] = None,
    created_by: Annotated[
        Optional[str],
        Query(description="Creator actor id filter.", examples=["advisor_123"]),
    ] = None,
    created_from: Annotated[
        Optional[datetime],
        Query(
            description="Created-at lower bound in UTC ISO8601.",
            examples=["2026-02-19T00:00:00Z"],
        ),
    ] = None,
    created_to: Annotated[
        Optional[datetime],
        Query(
            description="Created-at upper bound in UTC ISO8601.",
            examples=["2026-02-20T00:00:00Z"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(description="Page size.", ge=1, le=100, examples=[20]),
    ] = 20,
    cursor: Annotated[
        Optional[str],
        Query(description="Opaque cursor from previous list response.", examples=["pp_123"]),
    ] = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalListResponse:
    shared._assert_lifecycle_enabled()
    return service.list_proposals(
        portfolio_id=portfolio_id,
        state=state,
        created_by=created_by,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        cursor=cursor,
    )


@shared.router.get(
    "/rebalance/proposals/{proposal_id}/versions/{version_no}",
    summary="Get Proposal Version",
    response_model=ProposalVersionDetail,
    status_code=status.HTTP_200_OK,
    description="Returns one immutable proposal version by version number.",
)
def get_proposal_version(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    version_no: Annotated[
        int,
        Path(description="Immutable proposal version number.", ge=1, examples=[1]),
    ],
    include_evidence: Annotated[
        bool,
        Query(description="Include full evidence bundle in version payload.", examples=[True]),
    ] = True,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalVersionDetail:
    shared._assert_lifecycle_enabled()
    try:
        return service.get_version(
            proposal_id=proposal_id,
            version_no=version_no,
            include_evidence=include_evidence,
        )
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.post(
    "/rebalance/proposals/{proposal_id}/versions",
    response_model=ProposalCreateResponse,
    status_code=status.HTTP_200_OK,
    summary="Create Proposal Version",
    description=(
        "Creates a new immutable proposal version by rerunning simulation + artifact build."
    ),
)
def create_proposal_version(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    payload: ProposalVersionRequest,
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description="Optional correlation id captured in version event reason payload.",
            examples=["corr-proposal-version-001"],
        ),
    ] = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalCreateResponse:
    shared._assert_lifecycle_enabled()
    try:
        return service.create_version(
            proposal_id=proposal_id,
            payload=payload,
            correlation_id=correlation_id,
        )
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProposalValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@shared.router.post(
    "/rebalance/proposals/{proposal_id}/transitions",
    response_model=ProposalStateTransitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Transition Proposal State",
    description=(
        "Applies one validated workflow transition with optimistic state concurrency check."
    ),
)
def transition_proposal_state(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    payload: ProposalStateTransitionRequest,
    idempotency_key: Annotated[
        Optional[str],
        Header(
            alias="Idempotency-Key",
            description="Optional idempotency key for replay-safe transition writes.",
            examples=["proposal-transition-idem-001"],
        ),
    ] = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalStateTransitionResponse:
    shared._assert_lifecycle_enabled()
    try:
        return service.transition_state(
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProposalIdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProposalStateConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProposalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@shared.router.post(
    "/rebalance/proposals/{proposal_id}/approvals",
    response_model=ProposalStateTransitionResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Proposal Approval",
    description=(
        "Persists a structured approval/consent record and appends "
        "the corresponding workflow event "
        "with deterministic state transition."
    ),
)
def record_proposal_approval(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    payload: ProposalApprovalRequest,
    idempotency_key: Annotated[
        Optional[str],
        Header(
            alias="Idempotency-Key",
            description="Optional idempotency key for replay-safe approval writes.",
            examples=["proposal-approval-idem-001"],
        ),
    ] = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalStateTransitionResponse:
    shared._assert_lifecycle_enabled()
    try:
        return service.record_approval(
            proposal_id=proposal_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ProposalIdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProposalStateConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ProposalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
