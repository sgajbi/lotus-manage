from decimal import Decimal
from typing import cast

from src.core.models import (
    DiagnosticsData,
    DroppedIntent,
    EngineOptions,
    Money,
    SecurityTradeIntent,
)


def calculate_turnover_score(intent: SecurityTradeIntent, portfolio_value_base: Decimal) -> Decimal:
    if portfolio_value_base <= Decimal("0"):
        return Decimal("0")
    if intent.notional_base is None:
        return Decimal("0")
    notional_abs = cast(Decimal, abs(intent.notional_base.amount))
    return notional_abs / portfolio_value_base


def apply_turnover_limit(
    *,
    intents: list[SecurityTradeIntent],
    options: EngineOptions,
    portfolio_value_base: Decimal,
    base_currency: str,
    diagnostics: DiagnosticsData,
) -> list[SecurityTradeIntent]:
    if options.max_turnover_pct is None:
        return intents

    budget = portfolio_value_base * options.max_turnover_pct
    proposed = sum(
        (
            abs(intent.notional_base.amount)
            for intent in intents
            if intent.notional_base is not None
        ),
        Decimal("0"),
    )
    if proposed <= budget:
        return intents

    ranked = sorted(
        intents,
        key=lambda intent: (
            -calculate_turnover_score(intent, portfolio_value_base),
            (
                abs(intent.notional_base.amount)
                if intent.notional_base is not None
                else Decimal("0")
            ),
            intent.instrument_id,
            intent.intent_id,
        ),
    )

    selected: list[SecurityTradeIntent] = []
    used = Decimal("0")
    for intent in ranked:
        if intent.notional_base is None:
            continue
        notional_abs = abs(intent.notional_base.amount)
        score = calculate_turnover_score(intent, portfolio_value_base)
        if used + notional_abs <= budget:
            selected.append(intent)
            used += notional_abs
            continue

        diagnostics.dropped_intents.append(
            DroppedIntent(
                instrument_id=intent.instrument_id,
                reason="TURNOVER_LIMIT",
                potential_notional=Money(amount=notional_abs, currency=base_currency),
                score=score,
            )
        )

    if diagnostics.dropped_intents:
        diagnostics.warnings.append("PARTIAL_REBALANCE_TURNOVER_LIMIT")

    return selected
