import importlib
from typing import Annotated

from fastapi import HTTPException, Path, Request, status

from src.api.routers import rebalance_runs as shared
from src.core.rebalance_runs import (
    DpmRunIdempotencyLookupResponse,
    DpmRunLookupResponse,
    DpmRunNotFoundError,
    DpmRunSupportService,
)


@shared.router.get(
    "/rebalance/runs/by-correlation/{correlation_id}",
    response_model=DpmRunLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run by Correlation Id",
    description=(
        "Returns the latest discretionary mandate rebalance run mapped to one correlation id. "
        "Use this endpoint when an operator, Gateway trace, or incident ticket has only the "
        "`X-Correlation-Id` submitted with the run. Use `/rebalance/runs` for filtered inventory "
        "search and the support-bundle routes when artifact, workflow, lineage, or idempotency "
        "history context is required. This endpoint does not accept query parameters."
    ),
    responses={
        200: {"description": "Latest run supportability record mapped to the correlation id."},
        404: {"description": "Support APIs disabled or no run is mapped to the correlation id."},
        422: {"description": "Unsupported query parameters were supplied."},
    },
)
def get_run_by_correlation(
    request: Request,
    correlation_id: Annotated[
        str,
        Path(
            description="Correlation identifier used on run submission.",
            examples=["corr-1234-abcd"],
        ),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunLookupResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_run_by_correlation(correlation_id=correlation_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/by-request-hash/{request_hash}",
    response_model=DpmRunLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run by Request Hash",
    description=(
        "Returns the latest discretionary mandate rebalance run mapped to one canonical request "
        "hash. Use this endpoint for retry, replay, or support investigations where the caller "
        "has the `sha256:` request fingerprint but not the run id. URL-encode the request hash "
        "when calling through a path segment. Use `/rebalance/runs` for filtered inventory search "
        "and support-bundle routes when broader investigation evidence is required. This endpoint "
        "does not accept query parameters."
    ),
    responses={
        200: {"description": "Latest run supportability record mapped to the request hash."},
        404: {"description": "Support APIs disabled or no run is mapped to the request hash."},
        422: {"description": "Unsupported query parameters were supplied."},
    },
)
def get_run_by_request_hash(
    request: Request,
    request_hash: Annotated[
        str,
        Path(
            description="Canonical request hash persisted for run supportability record.",
            examples=["sha256:abc123"],
        ),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunLookupResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_run_by_request_hash(request_hash=request_hash)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/idempotency/{idempotency_key}",
    response_model=DpmRunIdempotencyLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Idempotency Mapping",
    description=(
        "Returns the current idempotency-key mapping for one discretionary mandate rebalance "
        "request. Use this endpoint when a client retry token is known and only the latest mapped "
        "run id and request hash are needed. Use `/rebalance/idempotency/{idempotency_key}/history` "
        "for append-only retry history and the idempotency support-bundle route for full run "
        "evidence. This endpoint does not accept query parameters."
    ),
    responses={
        200: {"description": "Current idempotency-key to run mapping."},
        404: {"description": "Support APIs disabled or idempotency key not found."},
        422: {"description": "Unsupported query parameters were supplied."},
    },
)
def get_run_idempotency_lookup(
    request: Request,
    idempotency_key: Annotated[
        str,
        Path(
            description="Idempotency key supplied to `/rebalance/simulate`.",
            examples=["demo-idem-001"],
        ),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunIdempotencyLookupResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_idempotency_lookup(idempotency_key=idempotency_key)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


importlib.import_module("src.api.routers.rebalance_runs_lookup_idempotency_history_routes")


@shared.router.get(
    "/rebalance/runs/{rebalance_run_id}",
    response_model=DpmRunLookupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run by Run Id",
    description=(
        "Returns one discretionary mandate rebalance run payload and its persisted supportability "
        "metadata by run id. Use this endpoint when the caller needs the run result exactly as "
        "stored after simulation. Use `/rebalance/runs/{rebalance_run_id}/artifact` for the "
        "deterministic audit artifact and `/rebalance/runs/{rebalance_run_id}/support-bundle` "
        "when workflow, lineage, async operation, or idempotency context is required. This "
        "endpoint does not accept query parameters."
    ),
    responses={
        200: {"description": "Persisted run supportability record and result payload."},
        404: {"description": "Support APIs disabled or run id not found."},
        422: {"description": "Unsupported query parameters were supplied."},
    },
)
def get_run_by_run_id(
    request: Request,
    rebalance_run_id: Annotated[
        str,
        Path(description="lotus-manage run identifier.", examples=["rr_abc12345"]),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunLookupResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    try:
        return service.get_run(rebalance_run_id=rebalance_run_id)
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
