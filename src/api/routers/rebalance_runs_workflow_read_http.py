from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.api.routers.rebalance_runs_http import read_run_with_not_found_http_mapping

WorkflowReadResponse = TypeVar("WorkflowReadResponse")
WorkflowReadCallback = Callable[[], WorkflowReadResponse]


def read_workflow_with_http_mapping(
    read_workflow: WorkflowReadCallback[WorkflowReadResponse],
) -> WorkflowReadResponse:
    return read_run_with_not_found_http_mapping(read_workflow)
