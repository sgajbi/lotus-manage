"""Explicit empty planning products for controlled mandate-health HTTP proof."""

from tests.integration.dpm.controlled_core import AS_OF


def mandate_sources(portfolio):
    common = {
        "product_version": "v1",
        "portfolio_id": portfolio,
        "client_id": "client-reserve",
        "mandate_id": "mandate-reserve",
        "as_of_date": AS_OF,
        "data_quality_status": "COMPLETE",
        "lineage": {"source_system": "controlled-core"},
    }
    products = {}
    for key, product, rows, count in [
        (
            "sustainability-preference-profile",
            "SustainabilityPreferenceProfile",
            "preferences",
            "preference_count",
        ),
        (
            "client-income-needs-schedule",
            "ClientIncomeNeedsSchedule",
            "schedules",
            "schedule_count",
        ),
        (
            "liquidity-reserve-requirement",
            "LiquidityReserveRequirement",
            "requirements",
            "requirement_count",
        ),
        (
            "planned-withdrawal-schedule",
            "PlannedWithdrawalSchedule",
            "withdrawals",
            "withdrawal_count",
        ),
    ]:
        products[key] = {
            **common,
            "product_name": product,
            rows: [],
            "horizon_days": 365,
            "supportability": {"state": "READY", "reason": "CONTROLLED_EMPTY_SCHEDULE", count: 0},
        }
    products["cashflow-projection"] = {
        **common,
        "product_name": "PortfolioCashflowProjection",
        "range_start_date": AS_OF,
        "range_end_date": "2026-07-09",
        "include_projected": True,
        "portfolio_currency": "USD",
        "points": [],
        "total_net_cashflow": "0",
        "projection_days": 90,
    }
    products["benchmark-assignment"] = {
        **common,
        "product_name": "BenchmarkAssignment",
        "benchmark_id": "benchmark-controlled",
        "effective_from": "2026-04-01",
        "assignment_source": "CONTROLLED_CONTRACT",
        "assignment_status": "ACTIVE",
        "assignment_recorded_at": f"{AS_OF}T09:00:00Z",
        "assignment_version": 1,
    }
    return products
