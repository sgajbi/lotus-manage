from __future__ import annotations

from collections.abc import Callable

from src.api.routers.rebalance_runs_http import read_run_with_not_found_http_mapping
from src.core.rebalance_runs import DpmRunSupportBundleResponse

SupportBundleCallback = Callable[[], DpmRunSupportBundleResponse]


def read_support_bundle_with_http_mapping(
    read_support_bundle: SupportBundleCallback,
) -> DpmRunSupportBundleResponse:
    return read_run_with_not_found_http_mapping(read_support_bundle)
