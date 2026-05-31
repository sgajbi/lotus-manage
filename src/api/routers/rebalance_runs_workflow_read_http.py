from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, status

from src.core.rebalance_runs import DpmRunNotFoundError

WorkflowReadResponse = TypeVar("WorkflowReadResponse")
WorkflowReadCallback = Callable[[], WorkflowReadResponse]


def read_workflow_with_http_mapping(
    read_workflow: WorkflowReadCallback[WorkflowReadResponse],
) -> WorkflowReadResponse:
    try:
        return read_workflow()
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
