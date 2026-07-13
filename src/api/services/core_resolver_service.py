from __future__ import annotations

import os

from src.api.services.service_config import env_flag, env_float, env_int
from src.infrastructure.core_sourcing import (
    DpmCoreResolverClient,
    DpmCoreResolverConfig,
    DpmCoreResolverUnavailableError,
    DpmCoreResolverError,
)
from src.infrastructure.source_http_clients import (
    build_source_http_client_policy,
    get_shared_source_http_client,
)


def stateful_core_sourcing_enabled() -> bool:
    return env_flag("DPM_STATEFUL_CORE_SOURCING_ENABLED", False)


CoreResolverClient = DpmCoreResolverClient
CoreResolverError = DpmCoreResolverError
CoreResolverUnavailableError = DpmCoreResolverUnavailableError


def build_core_resolver_client() -> DpmCoreResolverClient:
    base_url = os.getenv("DPM_CORE_BASE_URL", "").strip()
    if not base_url:
        raise DpmCoreResolverUnavailableError("DPM_CORE_RESOLVER_UNAVAILABLE")
    config = DpmCoreResolverConfig(
        base_url=base_url,
        query_base_url=os.getenv("DPM_CORE_QUERY_BASE_URL", "").strip() or None,
        path_template=os.getenv(
            "DPM_CORE_RESOLVER_PATH_TEMPLATE",
            "",
        ),
        portfolio_manager_book_memberships_path_template=os.getenv(
            "DPM_CORE_PM_BOOK_MEMBERSHIPS_PATH_TEMPLATE",
            "/integration/portfolio-manager-books/{portfolio_manager_id}/memberships",
        ),
        transaction_cost_curve_path_template=os.getenv(
            "DPM_CORE_TRANSACTION_COST_CURVE_PATH_TEMPLATE",
            "/integration/portfolios/{portfolio_id}/transaction-cost-curve",
        ),
        portfolio_cashflow_projection_path_template=os.getenv(
            "DPM_CORE_CASHFLOW_PROJECTION_PATH_TEMPLATE",
            "/portfolios/{portfolio_id}/cashflow-projection",
        ),
        client_income_needs_schedule_path_template=os.getenv(
            "DPM_CORE_INCOME_NEEDS_SCHEDULE_PATH_TEMPLATE",
            "/integration/portfolios/{portfolio_id}/client-income-needs-schedule",
        ),
        liquidity_reserve_requirement_path_template=os.getenv(
            "DPM_CORE_LIQUIDITY_RESERVE_REQUIREMENT_PATH_TEMPLATE",
            "/integration/portfolios/{portfolio_id}/liquidity-reserve-requirement",
        ),
        planned_withdrawal_schedule_path_template=os.getenv(
            "DPM_CORE_PLANNED_WITHDRAWAL_SCHEDULE_PATH_TEMPLATE",
            "/integration/portfolios/{portfolio_id}/planned-withdrawal-schedule",
        ),
        external_order_execution_acknowledgement_path_template=os.getenv(
            "DPM_CORE_EXTERNAL_ORDER_EXECUTION_ACKNOWLEDGEMENT_PATH_TEMPLATE",
            "/integration/portfolios/{portfolio_id}/external-order-execution-acknowledgement",
        ),
        transaction_cost_lookback_days=env_int("DPM_CORE_TRANSACTION_COST_LOOKBACK_DAYS", 400),
        timeout_seconds=env_float("DPM_CORE_RESOLVER_TIMEOUT_SECONDS", 2.0),
        max_attempts=env_int("DPM_CORE_RESOLVER_MAX_ATTEMPTS", 2),
    )
    return DpmCoreResolverClient(
        config=config,
        client=get_shared_source_http_client(
            "core",
            policy=build_source_http_client_policy(
                "core",
                request_timeout_seconds=config.timeout_seconds,
            ),
        ),
    )


__all__ = [
    "build_core_resolver_client",
    "env_float",
    "env_flag",
    "env_int",
    "stateful_core_sourcing_enabled",
]
