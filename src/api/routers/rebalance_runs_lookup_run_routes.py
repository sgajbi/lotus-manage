from typing import Annotated

from fastapi import Path, Request, status

from src.api.routers import rebalance_runs as shared
from src.api.routers.rebalance_runs_http import read_run_with_not_found_http_mapping
from src.core.rebalance_runs import (
    DpmRunLookupResponse,
    DpmRunSupportService,
)


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
    return read_run_with_not_found_http_mapping(
        lambda: service.get_run(rebalance_run_id=rebalance_run_id)
    )
