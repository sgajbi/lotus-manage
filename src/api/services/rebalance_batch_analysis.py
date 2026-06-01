from __future__ import annotations

from decimal import Decimal
from typing import Dict

from pydantic import ValidationError

from src.core.models import (
    BatchRebalanceRequest,
    BatchScenarioMetric,
    Money,
    RebalanceResult,
)


def to_invalid_options_error(exc: ValidationError) -> str:
    first_error = exc.errors()[0]
    return f"INVALID_OPTIONS: {first_error.get('msg', 'validation failed')}"


def resolve_base_snapshot_ids(request: BatchRebalanceRequest) -> Dict[str, str]:
    return {
        "portfolio_snapshot_id": (
            request.portfolio_snapshot.snapshot_id or request.portfolio_snapshot.portfolio_id
        ),
        "market_data_snapshot_id": request.market_data_snapshot.snapshot_id or "md",
    }


def build_comparison_metric(
    scenario_result: RebalanceResult,
    base_currency: str,
) -> BatchScenarioMetric:
    security_intents = [
        intent for intent in scenario_result.intents if intent.intent_type == "SECURITY_TRADE"
    ]
    turnover_proxy = sum(
        (
            intent.notional_base.amount
            for intent in security_intents
            if intent.notional_base is not None
        ),
        Decimal("0"),
    )
    return BatchScenarioMetric(
        status=scenario_result.status,
        security_intent_count=len(security_intents),
        gross_turnover_notional_base=Money(amount=turnover_proxy, currency=base_currency),
    )


__all__ = [
    "build_comparison_metric",
    "resolve_base_snapshot_ids",
    "to_invalid_options_error",
]
