from typing import Annotated

from fastapi import Path, Request, status

from src.api.routers import rebalance_runs as shared
from src.api.routers.rebalance_runs_http import read_run_with_not_found_http_mapping
from src.core.rebalance_runs import (
    DpmRunIdempotencyHistoryResponse,
    DpmRunSupportService,
)


@shared.router.get(
    "/rebalance/idempotency/{idempotency_key}/history",
    response_model=DpmRunIdempotencyHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Idempotency History",
    description=(
        "Returns append-only run mapping history for one idempotency key, including run ids, "
        "request hashes, correlation ids, and event timestamps for retry support, incident "
        "reconstruction, and audit evidence. Use this endpoint only when "
        "`DPM_IDEMPOTENCY_HISTORY_APIS_ENABLED=true`; use "
        "`GET /rebalance/runs/idempotency/{idempotency_key}` when only the latest mapping is "
        "needed. This endpoint does not accept query parameters."
    ),
    responses={
        200: {
            "description": (
                "Append-only idempotency mapping history ordered by event timestamp, run id, "
                "correlation id, and request hash."
            ),
        },
        404: {"description": "History API disabled or idempotency key not found."},
        422: {"description": "Unsupported query parameters were supplied."},
    },
)
def get_run_idempotency_history(
    request: Request,
    idempotency_key: Annotated[
        str,
        Path(
            description="Idempotency key supplied to `/rebalance/simulate`.",
            examples=["demo-idem-001"],
        ),
    ],
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunIdempotencyHistoryResponse:
    shared._assert_support_apis_enabled()
    shared._assert_idempotency_history_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    return read_run_with_not_found_http_mapping(
        lambda: service.get_idempotency_history(idempotency_key=idempotency_key)
    )
