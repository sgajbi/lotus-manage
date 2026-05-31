import importlib
from typing import Annotated

from fastapi import HTTPException, Path, Request, status

from src.api.routers import rebalance_runs as shared
from src.api.routers.rebalance_runs_support_bundle_parameters import (
    SUPPORT_BUNDLE_QUERY_PARAMS,
    IncludeArtifactQuery,
    IncludeAsyncOperationQuery,
    IncludeIdempotencyHistoryQuery,
)
from src.core.rebalance_runs import (
    DpmRunNotFoundError,
    DpmRunSupportBundleResponse,
    DpmRunSupportService,
)


@shared.router.get(
    "/rebalance/runs/{rebalance_run_id}/support-bundle",
    response_model=DpmRunSupportBundleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Support Bundle",
    description=(
        "Returns an aggregated supportability bundle for one run, including run payload, "
        "lineage, workflow history, optional deterministic artifact, and optional mapped async "
        "operation/idempotency history. Optional sections are controlled only by "
        "`include_artifact`, `include_async_operation`, and `include_idempotency_history`; "
        "unsupported query parameters are rejected."
    ),
    responses={
        200: {"description": "Aggregated run supportability bundle for investigation."},
        404: {"description": "Run not found or support-bundle APIs disabled."},
        422: {"description": "Unsupported query parameters were supplied."},
    },
)
def get_dpm_run_support_bundle(
    request: Request,
    rebalance_run_id: Annotated[
        str,
        Path(description="lotus-manage run identifier.", examples=["rr_abc12345"]),
    ],
    include_artifact: IncludeArtifactQuery = True,
    include_async_operation: IncludeAsyncOperationQuery = True,
    include_idempotency_history: IncludeIdempotencyHistoryQuery = True,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunSupportBundleResponse:
    shared._assert_support_apis_enabled()
    shared._assert_support_bundle_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=SUPPORT_BUNDLE_QUERY_PARAMS)
    try:
        return service.get_run_support_bundle(
            rebalance_run_id=rebalance_run_id,
            include_artifact=include_artifact,
            include_async_operation=include_async_operation,
            include_idempotency_history=include_idempotency_history,
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@shared.router.get(
    "/rebalance/runs/by-correlation/{correlation_id}/support-bundle",
    response_model=DpmRunSupportBundleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Support Bundle by Correlation Id",
    description=(
        "Returns aggregated supportability bundle for run resolved by correlation id, "
        "including optional artifact, async operation, and idempotency history. Optional sections "
        "are controlled only by `include_artifact`, `include_async_operation`, and "
        "`include_idempotency_history`; unsupported query parameters are rejected."
    ),
    responses={
        200: {"description": "Aggregated run supportability bundle for investigation."},
        404: {"description": "Run not found or support-bundle APIs disabled."},
        422: {"description": "Unsupported query parameters were supplied."},
    },
)
def get_dpm_run_support_bundle_by_correlation(
    request: Request,
    correlation_id: Annotated[
        str,
        Path(
            description="Correlation identifier used on run submission.",
            examples=["corr-1234-abcd"],
        ),
    ],
    include_artifact: IncludeArtifactQuery = True,
    include_async_operation: IncludeAsyncOperationQuery = True,
    include_idempotency_history: IncludeIdempotencyHistoryQuery = True,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunSupportBundleResponse:
    shared._assert_support_apis_enabled()
    shared._assert_support_bundle_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=SUPPORT_BUNDLE_QUERY_PARAMS)
    try:
        return service.get_run_support_bundle_by_correlation(
            correlation_id=correlation_id,
            include_artifact=include_artifact,
            include_async_operation=include_async_operation,
            include_idempotency_history=include_idempotency_history,
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


importlib.import_module("src.api.routers.rebalance_runs_support_bundle_idempotency_routes")
importlib.import_module("src.api.routers.rebalance_runs_support_bundle_operation_routes")
