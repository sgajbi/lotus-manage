from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.core.rebalance_runs.models import (
    DpmAsyncOperationRecord,
    DpmAsyncOperationStatusResponse,
    DpmLineageEdgeRecord,
    DpmLineageResponse,
    DpmRunIdempotencyHistoryRecord,
    DpmRunIdempotencyHistoryResponse,
    DpmRunRecord,
    DpmRunWorkflowDecisionRecord,
    DpmRunWorkflowHistoryResponse,
)
from src.core.rebalance_runs.serializers import (
    lineage_cursor,
    to_async_status,
    to_idempotency_history_response,
    to_lineage_response,
    to_workflow_decision_response,
)


def support_bundle_async_operation(
    *,
    run: DpmRunRecord,
    operation: Optional[DpmAsyncOperationRecord],
) -> Optional[DpmAsyncOperationStatusResponse]:
    if operation is None or operation.correlation_id != run.correlation_id:
        return None
    return to_async_status(operation)


def support_bundle_idempotency_history(
    *,
    run: DpmRunRecord,
    history: Optional[list[DpmRunIdempotencyHistoryRecord]],
) -> Optional[DpmRunIdempotencyHistoryResponse]:
    if run.idempotency_key is None or history is None:
        return None
    return to_idempotency_history_response(
        idempotency_key=run.idempotency_key,
        history=history,
    )


def support_bundle_workflow_history(
    *,
    rebalance_run_id: str,
    decisions: list[DpmRunWorkflowDecisionRecord],
) -> DpmRunWorkflowHistoryResponse:
    return DpmRunWorkflowHistoryResponse(
        run_id=rebalance_run_id,
        decisions=[
            to_workflow_decision_response(decision)
            for decision in sorted(decisions, key=lambda item: item.decided_at)
        ],
    )


def support_bundle_lineage(
    *,
    rebalance_run_id: str,
    edges: list[DpmLineageEdgeRecord],
) -> DpmLineageResponse:
    return to_lineage_response(
        entity_id=rebalance_run_id,
        edges=sort_lineage_edges(edges),
        next_cursor=None,
    )


def sort_lineage_edges(edges: list[DpmLineageEdgeRecord]) -> list[DpmLineageEdgeRecord]:
    return sorted(
        edges,
        key=lambda edge: (
            edge.created_at,
            edge.source_entity_id,
            edge.edge_type,
            edge.target_entity_id,
        ),
    )


def filter_lineage_edges(
    *,
    edges: list[DpmLineageEdgeRecord],
    edge_type: Optional[str],
    created_from: Optional[datetime],
    created_to: Optional[datetime],
) -> list[DpmLineageEdgeRecord]:
    return [
        edge
        for edge in edges
        if matches_lineage_edge_type(edge=edge, edge_type=edge_type)
        and is_lineage_edge_in_window(
            edge=edge,
            created_from=created_from,
            created_to=created_to,
        )
    ]


def matches_lineage_edge_type(
    *,
    edge: DpmLineageEdgeRecord,
    edge_type: Optional[str],
) -> bool:
    return edge_type is None or edge.edge_type == edge_type


def is_lineage_edge_in_window(
    *,
    edge: DpmLineageEdgeRecord,
    created_from: Optional[datetime],
    created_to: Optional[datetime],
) -> bool:
    if created_from is not None and edge.created_at < created_from:
        return False
    if created_to is not None and edge.created_at > created_to:
        return False
    return True


def page_lineage_edges(
    *,
    edges: list[DpmLineageEdgeRecord],
    cursor: Optional[str],
    limit: int,
) -> tuple[list[DpmLineageEdgeRecord], Optional[str]]:
    if cursor is not None:
        cursor_index = next(
            (index for index, row in enumerate(edges) if lineage_cursor(row) == cursor),
            None,
        )
        edges = [] if cursor_index is None else edges[cursor_index + 1 :]
    page = edges[:limit]
    next_cursor = lineage_cursor(page[-1]) if len(edges) > limit else None
    return page, next_cursor


__all__ = [
    "filter_lineage_edges",
    "is_lineage_edge_in_window",
    "matches_lineage_edge_type",
    "page_lineage_edges",
    "sort_lineage_edges",
    "support_bundle_async_operation",
    "support_bundle_idempotency_history",
    "support_bundle_lineage",
    "support_bundle_workflow_history",
]
