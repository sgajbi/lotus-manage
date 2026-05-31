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
    "/rebalance/runs/idempotency/{idempotency_key}/support-bundle",
    response_model=DpmRunSupportBundleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Run Support Bundle by Idempotency Key",
    description=(
        "Returns aggregated supportability bundle for run resolved by idempotency key mapping, "
        "including optional artifact, async operation, and idempotency history. Optional sections "
        "are controlled only by `include_artifact`, `include_async_operation`, and "
        "`include_idempotency_history`; unsupported query parameters are rejected."
    ),
    responses={
        200: {"description": "Aggregated run supportability bundle for investigation."},
        404: {"description": "Idempotency key not found or support-bundle APIs disabled."},
        422: {"description": "Unsupported query parameters were supplied."},
    },
)
def get_dpm_run_support_bundle_by_idempotency(
    request: Request,
    idempotency_key: Annotated[
        str,
        Path(
            description="Idempotency key supplied to `/rebalance/simulate`.",
            examples=["demo-idem-001"],
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
        return service.get_run_support_bundle_by_idempotency(
            idempotency_key=idempotency_key,
            include_artifact=include_artifact,
            include_async_operation=include_async_operation,
            include_idempotency_history=include_idempotency_history,
        )
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
