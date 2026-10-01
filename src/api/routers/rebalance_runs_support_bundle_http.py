from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from src.api.routers.rebalance_runs_http import read_run_with_not_found_http_mapping

SupportBundleResponse = TypeVar("SupportBundleResponse")
SupportBundleCallback = Callable[[], SupportBundleResponse]


def read_support_bundle_with_http_mapping(
    read_support_bundle: SupportBundleCallback[SupportBundleResponse],
) -> SupportBundleResponse:
    return read_run_with_not_found_http_mapping(read_support_bundle)
