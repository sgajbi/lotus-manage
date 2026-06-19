from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fastapi import Request

from src.api.routers.rebalance_runs_http import read_run_with_not_found_http_mapping
from src.core.rebalance_runs import DpmRunSupportService, DpmRunWorkflowHistoryResponse

WorkflowReadResponse = TypeVar("WorkflowReadResponse")
WorkflowReadCallback = Callable[[], WorkflowReadResponse]
WorkflowRouteGuard = Callable[[], None]
RejectUnexpectedQueryParams = Callable[[Request], None]


def read_workflow_with_http_mapping(
    read_workflow: WorkflowReadCallback[WorkflowReadResponse],
) -> WorkflowReadResponse:
    return read_run_with_not_found_http_mapping(read_workflow)


def read_workflow_history_by_correlation_route(
    *,
    request: Request,
    correlation_id: str,
    service: DpmRunSupportService,
    assert_support_apis_enabled: WorkflowRouteGuard,
    assert_workflow_enabled: WorkflowRouteGuard,
    reject_unexpected_query_params: RejectUnexpectedQueryParams,
) -> DpmRunWorkflowHistoryResponse:
    assert_support_apis_enabled()
    assert_workflow_enabled()
    reject_unexpected_query_params(request)
    return read_workflow_with_http_mapping(
        lambda: service.get_workflow_history_by_correlation(correlation_id=correlation_id)
    )
