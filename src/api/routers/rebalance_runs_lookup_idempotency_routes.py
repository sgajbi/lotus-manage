from typing import Annotated

from fastapi import Path, Request, status

from src.api.routers import rebalance_runs as shared
from src.api.routers.rebalance_runs_http import read_run_with_not_found_http_mapping
from src.core.rebalance_runs import (
    DpmRunIdempotencyLookupResponse,
    DpmRunSupportService,
)


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
    return read_run_with_not_found_http_mapping(
        lambda: service.get_idempotency_lookup(idempotency_key=idempotency_key)
    )
