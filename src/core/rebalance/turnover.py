from decimal import Decimal
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
    notional_abs = abs(intent.notional_base.amount)
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

    budget = _turnover_budget(
        portfolio_value_base=portfolio_value_base,
        max_turnover_pct=options.max_turnover_pct,
    )
    proposed = _proposed_turnover(intents)
    if proposed <= budget:
        return intents

    ranked = sorted(
        intents,
        key=lambda intent: _turnover_rank_key(
            intent=intent,
            portfolio_value_base=portfolio_value_base,
        ),
    )

    selected: list[SecurityTradeIntent] = []
    used = Decimal("0")
    for intent in ranked:
        if intent.notional_base is None:
            continue
        notional_abs = abs(intent.notional_base.amount)
        if used + notional_abs <= budget:
            selected.append(intent)
            used += notional_abs
            continue

        diagnostics.dropped_intents.append(
            _dropped_turnover_intent(
                intent=intent,
                notional_abs=notional_abs,
                portfolio_value_base=portfolio_value_base,
                base_currency=base_currency,
            )
        )

    if diagnostics.dropped_intents:
        diagnostics.warnings.append("PARTIAL_REBALANCE_TURNOVER_LIMIT")

    return selected


def _turnover_budget(*, portfolio_value_base: Decimal, max_turnover_pct: Decimal) -> Decimal:
    return portfolio_value_base * max_turnover_pct


def _proposed_turnover(intents: list[SecurityTradeIntent]) -> Decimal:
    return sum(
        (
            abs(intent.notional_base.amount)
            for intent in intents
            if intent.notional_base is not None
        ),
        Decimal("0"),
    )


def _turnover_rank_key(
    *,
    intent: SecurityTradeIntent,
    portfolio_value_base: Decimal,
) -> tuple[Decimal, Decimal, str, str]:
    notional_abs = (
        abs(intent.notional_base.amount) if intent.notional_base is not None else Decimal("0")
    )
    return (
        -calculate_turnover_score(intent, portfolio_value_base),
        notional_abs,
        intent.instrument_id,
        intent.intent_id,
    )


def _dropped_turnover_intent(
    *,
    intent: SecurityTradeIntent,
    notional_abs: Decimal,
    portfolio_value_base: Decimal,
    base_currency: str,
) -> DroppedIntent:
    return DroppedIntent(
        instrument_id=intent.instrument_id,
        reason="TURNOVER_LIMIT",
        potential_notional=Money(amount=notional_abs, currency=base_currency),
        score=calculate_turnover_score(intent, portfolio_value_base),
    )
