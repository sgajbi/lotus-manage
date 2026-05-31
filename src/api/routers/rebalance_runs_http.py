from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, status

from src.core.rebalance_runs import DpmRunNotFoundError

RunHttpResponse = TypeVar("RunHttpResponse")
RunHttpCallback = Callable[[], RunHttpResponse]


def read_run_with_not_found_http_mapping(
    read_run: RunHttpCallback[RunHttpResponse],
) -> RunHttpResponse:
    try:
        return read_run()
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
