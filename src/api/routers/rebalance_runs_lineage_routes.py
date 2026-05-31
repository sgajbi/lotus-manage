from typing import Annotated, Optional

from fastapi import Path, Query, Request, status

from src.api.routers import rebalance_runs as shared
from src.core.rebalance_runs import (
    DpmLineageEdgeType,
    DpmLineageResponse,
    DpmRunSupportService,
)


@shared.router.get(
    "/rebalance/lineage/{entity_id}",
    response_model=DpmLineageResponse,
    status_code=status.HTTP_200_OK,
    summary="Get lotus-manage Supportability Lineage by Entity Id",
    description=(
        "Returns supportability lineage edges where the requested entity id is either the source "
        "or target of a persisted relation. Use this endpoint for incident reconstruction, audit "
        "evidence, run-to-correlation traversal, idempotency retry analysis, and async operation "
        "traceability. Supported filters are `edge_type`, `created_from`, `created_to`, `limit`, "
        "and `cursor`; unsupported aliases are rejected. Unknown entity ids return an empty page "
        "rather than `404`, because lineage lookup is a search surface."
    ),
    responses={
        200: {
            "description": (
                "Lineage page ordered by creation timestamp, source entity id, edge type, and "
                "target entity id, with `next_cursor` when more edges are available."
            ),
        },
        422: {
            "description": "Unsupported query parameters or invalid filter values were supplied.",
        },
    },
)
def get_dpm_lineage(
    request: Request,
    entity_id: Annotated[
        str,
        Path(
            description=(
                "Supportability entity identifier such as correlation id, idempotency key, "
                "run id, or operation id."
            ),
            examples=["corr-1234-abcd"],
        ),
    ],
    edge_type: Annotated[
        Optional[DpmLineageEdgeType],
        Query(
            description=(
                "Optional lineage edge-type filter. Valid values are `CORRELATION_TO_RUN`, "
                "`IDEMPOTENCY_TO_RUN`, and `OPERATION_TO_CORRELATION`."
            ),
            examples=["CORRELATION_TO_RUN"],
        ),
    ] = None,
    created_from: Annotated[
        Optional[shared.datetime],
        Query(
            description="Lineage edge creation lower bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T00:00:00Z"],
        ),
    ] = None,
    created_to: Annotated[
        Optional[shared.datetime],
        Query(
            description="Lineage edge creation upper bound timestamp (UTC ISO8601).",
            examples=["2026-02-20T23:59:59Z"],
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=200,
            description="Maximum number of lineage edges returned in one page.",
            examples=[50],
        ),
    ] = 50,
    cursor: Annotated[
        Optional[str],
        Query(
            description="Opaque lineage cursor returned by previous page.",
            examples=["2026-02-20T12:00:00+00:00|corr-1234|CORRELATION_TO_RUN|rr_abc12345"],
        ),
    ] = None,
    service: DpmRunSupportService = shared.Depends(shared.get_dpm_run_support_service),
) -> DpmLineageResponse:
    shared._assert_support_apis_enabled()
    shared._assert_lineage_apis_enabled()
    shared._reject_unexpected_query_params(
        request,
        allowed_params={"edge_type", "created_from", "created_to", "limit", "cursor"},
    )
    return service.get_lineage_filtered(
        entity_id=entity_id,
        edge_type=edge_type,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        cursor=cursor,
    )
