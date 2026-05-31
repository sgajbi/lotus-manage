from datetime import datetime
from typing import Annotated, Optional

from fastapi import Query, Request, status

from src.api.observability import (
    ACTION_REGISTER_SUPPORTABILITY_SURFACE,
    record_action_register_supportability,
)
from src.api.routers import rebalance_runs as shared
from src.api.services import rebalance_run_support_config
from src.core.rebalance_runs import (
    DpmRunListResponse,
    DpmRunSupportService,
    DpmSupportabilitySummaryResponse,
)


@shared.router.get(
    "/rebalance/runs",
    response_model=DpmRunListResponse,
    status_code=status.HTTP_200_OK,
    summary="List lotus-manage Runs",
    description=(
        "Returns paginated lotus-manage runs filtered by creation time range, run status, "
        "canonical request hash, and portfolio id. Use the canonical query parameter "
        "`status_filter` for status filtering; unsupported aliases are rejected. Rows are "
        "ordered by `created_at` descending with `rebalance_run_id` as a deterministic "
        "tie-breaker. Pass the returned `next_cursor` to continue from the next row."
    ),
    responses={
        200: {
            "description": "Bounded page of run supportability records for investigation.",
        },
        422: {
            "description": "Unsupported query parameters were supplied.",
        },
    },
)
def list_runs(
    request: Request,
    created_from: Annotated[
        Optional[datetime],
        Query(
            description="Run creation lower bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T00:00:00Z"],
        ),
    ] = None,
    created_to: Annotated[
        Optional[datetime],
        Query(
            description="Run creation upper bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T23:59:59Z"],
        ),
    ] = None,
    status_filter: Annotated[
        Optional[str],
        Query(
            description="Optional run status filter.",
            examples=["READY"],
        ),
    ] = None,
    request_hash: Annotated[
        Optional[str],
        Query(
            description="Optional canonical request hash filter.",
            examples=["sha256:abc123"],
        ),
    ] = None,
    portfolio_id: Annotated[
        Optional[str],
        Query(
            description="Optional portfolio identifier filter.",
            examples=["pf_123"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=200,
            description="Maximum number of rows returned in one page.",
            examples=[50],
        ),
    ] = 50,
    cursor: Annotated[
        Optional[str],
        Query(
            description="Opaque cursor value returned by previous page.",
            examples=["rr_abc12345"],
        ),
    ] = None,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmRunListResponse:
    shared._assert_support_apis_enabled()
    shared._reject_unexpected_query_params(
        request,
        allowed_params={
            "created_from",
            "created_to",
            "status_filter",
            "request_hash",
            "portfolio_id",
            "limit",
            "cursor",
        },
    )
    return service.list_runs(
        created_from=created_from,
        created_to=created_to,
        status=status_filter,
        request_hash=request_hash,
        portfolio_id=portfolio_id,
        limit=limit,
        cursor=cursor,
    )


@shared.router.get(
    "/rebalance/supportability/summary",
    response_model=DpmSupportabilitySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Supportability Summary",
    description=(
        "Returns supportability storage summary metrics (runs, operations, status counts, "
        "and temporal bounds) for operational investigation without direct database access. "
        "Use this endpoint when operators need a store-wide health and retention snapshot; "
        "it does not accept ad hoc query filters. The response includes bounded action-register "
        "supportability state for Gateway and Workbench portfolio-management readiness surfaces."
    ),
    responses={
        200: {
            "description": (
                "Store-wide supportability summary with counts, freshness, and bounded "
                "action-register posture."
            ),
        },
        404: {
            "description": "Support APIs or supportability summary APIs are disabled.",
        },
        422: {
            "description": "Unsupported query parameters were supplied.",
        },
        503: {
            "description": "Supportability store backend is unavailable or not configured.",
        },
    },
)
def get_dpm_supportability_summary(
    request: Request,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmSupportabilitySummaryResponse:
    shared._assert_support_apis_enabled()
    shared._assert_supportability_summary_apis_enabled()
    shared._reject_unexpected_query_params(request, allowed_params=set())
    response = service.get_supportability_summary(
        store_backend=shared._supportability_store_backend_name(),
        retention_days=rebalance_run_support_config.env_non_negative_int(
            "DPM_SUPPORTABILITY_RETENTION_DAYS", 0
        ),
    )
    record_action_register_supportability(
        surface=ACTION_REGISTER_SUPPORTABILITY_SURFACE,
        supportability_state=response.supportability.state,
        reason=response.supportability.reason,
        freshness_bucket=response.supportability.freshness_bucket,
    )
    return response
