import importlib
from typing import Annotated

from fastapi import HTTPException, Path, Request, status

from src.api.routers import rebalance_runs as shared
from src.core.rebalance_runs import (
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


importlib.import_module("src.api.routers.rebalance_runs_lookup_request_hash_routes")
importlib.import_module("src.api.routers.rebalance_runs_lookup_idempotency_routes")
importlib.import_module("src.api.routers.rebalance_runs_lookup_idempotency_history_routes")


importlib.import_module("src.api.routers.rebalance_runs_lookup_run_routes")
