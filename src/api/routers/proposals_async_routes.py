from typing import Annotated, Optional

from fastapi import BackgroundTasks, Depends, Header, HTTPException, Path, status

from src.api.routers import proposals as shared
from src.core.proposals import (
    ProposalAsyncAcceptedResponse,
    ProposalAsyncOperationStatusResponse,
    ProposalCreateRequest,
    ProposalNotFoundError,
    ProposalVersionRequest,
    ProposalWorkflowService,
)


@shared.router.post(
    "/rebalance/proposals/async",
    response_model=ProposalAsyncAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create and Persist Advisory Proposal Asynchronously",
    description=(
        "Accepts proposal creation request for asynchronous processing. "
        "Use returned operation id or correlation id to retrieve status and result."
    ),
)
def create_proposal_async(
    payload: ProposalCreateRequest,
    background_tasks: BackgroundTasks,
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            description="Required idempotency key for proposal-create deduplication.",
            examples=["proposal-create-idem-async-001"],
        ),
    ],
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description=(
                "Optional correlation id for asynchronous tracking. Generated when omitted."
            ),
            examples=["corr-proposal-create-async-001"],
        ),
    ] = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalAsyncAcceptedResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_async_operations_enabled()
    accepted = service.submit_create_proposal_async(
        payload=payload,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
    )
    background_tasks.add_task(
        service.execute_create_proposal_async,
        operation_id=accepted.operation_id,
        payload=payload,
        idempotency_key=idempotency_key,
        correlation_id=accepted.correlation_id,
    )
    return accepted


@shared.router.post(
    "/rebalance/proposals/{proposal_id}/versions/async",
    response_model=ProposalAsyncAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create Proposal Version Asynchronously",
    description=(
        "Accepts proposal-version creation request for asynchronous processing. "
        "Use returned operation id or correlation id to retrieve status and result."
    ),
)
def create_proposal_version_async(
    proposal_id: Annotated[
        str,
        Path(description="Persisted proposal identifier.", examples=["pp_001"]),
    ],
    payload: ProposalVersionRequest,
    background_tasks: BackgroundTasks,
    correlation_id: Annotated[
        Optional[str],
        Header(
            alias="X-Correlation-Id",
            description=(
                "Optional correlation id for asynchronous tracking. Generated when omitted."
            ),
            examples=["corr-proposal-version-async-001"],
        ),
    ] = None,
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalAsyncAcceptedResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_async_operations_enabled()
    accepted = service.submit_create_version_async(
        proposal_id=proposal_id,
        payload=payload,
        correlation_id=correlation_id,
    )
    background_tasks.add_task(
        service.execute_create_version_async,
        operation_id=accepted.operation_id,
        proposal_id=proposal_id,
        payload=payload,
        correlation_id=accepted.correlation_id,
    )
    return accepted


@shared.router.get(
    "/rebalance/proposals/operations/{operation_id}",
    response_model=ProposalAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Proposal Async Operation",
    description="Returns asynchronous operation status and terminal result/error payload.",
)
def get_proposal_async_operation(
    operation_id: Annotated[
        str,
        Path(description="Asynchronous operation identifier.", examples=["pop_001"]),
    ],
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalAsyncOperationStatusResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_async_operations_enabled()
    try:
        return service.get_async_operation(operation_id=operation_id)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/proposals/operations/by-correlation/{correlation_id}",
    response_model=ProposalAsyncOperationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Proposal Async Operation by Correlation Id",
    description="Returns the latest asynchronous operation associated with correlation id.",
)
def get_proposal_async_operation_by_correlation(
    correlation_id: Annotated[
        str,
        Path(
            description="Correlation id associated with asynchronous submission.",
            examples=["corr-proposal-create-async-001"],
        ),
    ],
    service: ProposalWorkflowService = Depends(shared.get_proposal_workflow_service),
) -> ProposalAsyncOperationStatusResponse:
    shared._assert_lifecycle_enabled()
    shared._assert_async_operations_enabled()
    try:
        return service.get_async_operation_by_correlation(correlation_id=correlation_id)
    except ProposalNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
