from __future__ import annotations

from collections.abc import Callable

from fastapi import HTTPException, status

from src.core.rebalance_runs import (
    DpmRunNotFoundError,
    DpmRunSupportBundleResponse,
)

SupportBundleCallback = Callable[[], DpmRunSupportBundleResponse]


def read_support_bundle_with_http_mapping(
    read_support_bundle: SupportBundleCallback,
) -> DpmRunSupportBundleResponse:
    try:
        return read_support_bundle()
    except DpmRunNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
