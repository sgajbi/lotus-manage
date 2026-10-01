from typing import Annotated

from fastapi import Path, Request, status

from src.api.routers import rebalance_runs as shared
from src.api.routers.rebalance_runs_support_bundle_http import (
    read_support_bundle_with_http_mapping,
)
from src.api.routers.rebalance_runs_support_bundle_parameters import (
    SUPPORT_BUNDLE_QUERY_PARAMS,
    IncludeArtifactQuery,
    IncludeAsyncOperationQuery,
    IncludeIdempotencyHistoryQuery,
)
from src.core.rebalance_runs import (
    DpmOperationSupportBundleResponse,
    DpmRunSupportService,
)


@shared.router.get(
    "/rebalance/runs/by-operation/{operation_id}/support-bundle",
    response_model=DpmOperationSupportBundleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Support Bundle by Operation Id",
    description=(
        "Returns every requested scenario's authoritative run bundle, failed or missing outcomes, "
        "and identified non-authoritative attempt runs for an asynchronous operation. "
        "The terminal operation result and explicit attempt-scoped membership determine current "
        "runs; correlation text is never used to infer membership. Optional sections "
        "are controlled only by `include_artifact`, `include_async_operation`, and "
        "`include_idempotency_history`; unsupported query parameters are rejected."
    ),
    responses={
        200: {"description": "Operation-scoped scenario and historical run evidence."},
        404: {"description": "Operation not found or support-bundle APIs disabled."},
        422: {"description": "Unsupported query parameters were supplied."},
    },
)
def get_dpm_run_support_bundle_by_operation(
    request: Request,
    x_tenant_id: shared.DpmRunTenantIdHeader,
    operation_id: Annotated[
        str,
        Path(
            description="Asynchronous operation identifier.",
            examples=["dop_001"],
        ),
    ],
    include_artifact: IncludeArtifactQuery = True,
    include_async_operation: IncludeAsyncOperationQuery = True,
    include_idempotency_history: IncludeIdempotencyHistoryQuery = True,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmOperationSupportBundleResponse:
    shared._assert_support_apis_enabled()
    shared._assert_support_bundle_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=SUPPORT_BUNDLE_QUERY_PARAMS)
    return read_support_bundle_with_http_mapping(
        lambda: service.get_run_support_bundle_by_operation_for_tenant(
            tenant_id=x_tenant_id,
            operation_id=operation_id,
            include_artifact=include_artifact,
            include_async_operation=include_async_operation,
            include_idempotency_history=include_idempotency_history,
        )
    )
