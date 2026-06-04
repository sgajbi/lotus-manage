from copy import deepcopy
from decimal import Decimal
from typing import Literal, TypeAlias

from src.core.common.intent_dependencies import link_buy_intent_dependencies
from src.core.common.simulation_shared import (
    apply_fx_spot_to_portfolio,
    apply_security_trade_to_portfolio,
    build_reconciliation,
    derive_status_from_rules,
    sort_execution_intents,
)
from src.core.compliance import RuleEngine
from src.core.models import (
    CashLadderBreach,
    CashLadderPoint,
    DiagnosticsData,
    EngineOptions,
    FxSpotIntent,
    IntentRationale,
    MarketDataSnapshot,
    OrderIntent,
    PortfolioSnapshot,
    Reconciliation,
    RuleResult,
    SecurityTradeIntent,
    ShelfEntry,
    SimulatedState,
    ValuationMode,
)
from src.core.valuation import build_simulated_state, get_fx_rate

_ExecutionSimulationStatus: TypeAlias = Literal["READY", "BLOCKED", "PENDING_REVIEW"]
_ExecutionSimulationResult: TypeAlias = tuple[
    list[OrderIntent],
    SimulatedState | PortfolioSnapshot,
    list[RuleResult],
    _ExecutionSimulationStatus,
    Reconciliation | None,
]


def build_settlement_ladder(
    portfolio: PortfolioSnapshot,
    shelf: list[ShelfEntry],
    intents: list[OrderIntent],
    options: EngineOptions,
    diagnostics: DiagnosticsData,
) -> None:
    settlement_days_by_instrument = _settlement_days_by_instrument(shelf)
    horizon_days = _settlement_horizon_days(
        settlement_days_by_instrument=settlement_days_by_instrument,
        intents=intents,
        options=options,
    )
    flows = _settlement_cash_flows(
        portfolio=portfolio,
        intents=intents,
        settlement_days_by_instrument=settlement_days_by_instrument,
        horizon_days=horizon_days,
        options=options,
    )
    _append_settlement_ladder_points(
        flows=flows,
        horizon_days=horizon_days,
        options=options,
        diagnostics=diagnostics,
    )


def _settlement_days_by_instrument(shelf: list[ShelfEntry]) -> dict[str, int]:
    return {entry.instrument_id: entry.settlement_days for entry in shelf}


def _settlement_horizon_days(
    *,
    settlement_days_by_instrument: dict[str, int],
    intents: list[OrderIntent],
    options: EngineOptions,
) -> int:
    max_security_day = max(
        (
            settlement_days_by_instrument.get(intent.instrument_id, 2)
            for intent in intents
            if intent.intent_type == "SECURITY_TRADE"
        ),
        default=0,
    )
    return max(options.settlement_horizon_days, options.fx_settlement_days, max_security_day)


def _settlement_cash_flows(
    *,
    portfolio: PortfolioSnapshot,
    intents: list[OrderIntent],
    settlement_days_by_instrument: dict[str, int],
    horizon_days: int,
    options: EngineOptions,
) -> dict[str, list[Decimal]]:
    flows: dict[str, list[Decimal]] = {}

    for cash in portfolio.cash_balances:
        _ensure_settlement_currency(flows=flows, currency=cash.currency, horizon_days=horizon_days)
        flows[cash.currency][0] += cash.settled if cash.settled is not None else cash.amount

    _apply_intent_settlement_flows(
        flows=flows,
        intents=intents,
        settlement_days_by_instrument=settlement_days_by_instrument,
        horizon_days=horizon_days,
        options=options,
    )
    return flows


def _ensure_settlement_currency(
    *,
    flows: dict[str, list[Decimal]],
    currency: str,
    horizon_days: int,
) -> None:
    if currency not in flows:
        flows[currency] = [Decimal("0")] * (horizon_days + 1)


def _apply_intent_settlement_flows(
    *,
    flows: dict[str, list[Decimal]],
    intents: list[OrderIntent],
    settlement_days_by_instrument: dict[str, int],
    horizon_days: int,
    options: EngineOptions,
) -> None:
    for intent in sorted(intents, key=lambda item: item.intent_id):
        if intent.intent_type == "SECURITY_TRADE":
            if intent.notional is None:
                continue
            settlement_day = settlement_days_by_instrument.get(intent.instrument_id, 2)
            _ensure_settlement_currency(
                flows=flows,
                currency=intent.notional.currency,
                horizon_days=horizon_days,
            )
            signed_flow = (
                intent.notional.amount if intent.side == "SELL" else -intent.notional.amount
            )
            flows[intent.notional.currency][settlement_day] += signed_flow
            continue

        if intent.intent_type != "FX_SPOT":
            continue

        _ensure_settlement_currency(
            flows=flows,
            currency=intent.sell_currency,
            horizon_days=horizon_days,
        )
        _ensure_settlement_currency(
            flows=flows,
            currency=intent.buy_currency,
            horizon_days=horizon_days,
        )
        flows[intent.sell_currency][options.fx_settlement_days] -= intent.sell_amount_estimated
        flows[intent.buy_currency][options.fx_settlement_days] += intent.buy_amount


def _append_settlement_ladder_points(
    *,
    flows: dict[str, list[Decimal]],
    horizon_days: int,
    options: EngineOptions,
    diagnostics: DiagnosticsData,
) -> None:
    overdraft_utilized = False
    for currency in sorted(flows.keys()):
        projected_balance = Decimal("0")
        allowed_floor = -options.max_overdraft_by_ccy.get(currency, Decimal("0"))
        for day in range(horizon_days + 1):
            projected_balance += flows[currency][day]
            _append_cash_ladder_point(
                diagnostics=diagnostics,
                day=day,
                currency=currency,
                projected_balance=projected_balance,
            )
            if projected_balance < Decimal("0") and options.max_overdraft_by_ccy.get(
                currency, Decimal("0")
            ) > Decimal("0"):
                overdraft_utilized = True
            if projected_balance < allowed_floor:
                diagnostics.cash_ladder_breaches.append(
                    CashLadderBreach(
                        date_offset=day,
                        currency=currency,
                        projected_balance=projected_balance,
                        allowed_floor=allowed_floor,
                        reason_code=f"OVERDRAFT_ON_T_PLUS_{day}",
                    )
                )

    if overdraft_utilized:
        diagnostics.warnings.append("SETTLEMENT_OVERDRAFT_UTILIZED")


def _append_cash_ladder_point(
    *,
    diagnostics: DiagnosticsData,
    day: int,
    currency: str,
    projected_balance: Decimal,
) -> None:
    diagnostics.cash_ladder.append(
        CashLadderPoint(
            date_offset=day,
            currency=currency,
            projected_balance=projected_balance,
        )
    )


def _project_cash_after_security_trades(
    *,
    portfolio: PortfolioSnapshot,
    intents: list[OrderIntent],
) -> dict[str, Decimal]:
    projected_cash = {cash.currency: cash.amount for cash in portfolio.cash_balances}
    for intent in intents:
        if intent.intent_type != "SECURITY_TRADE" or intent.notional is None:
            continue
        projected_cash[intent.notional.currency] = projected_cash.get(
            intent.notional.currency,
            Decimal("0"),
        ) + (intent.notional.amount if intent.side == "SELL" else -intent.notional.amount)
    return projected_cash


def _fx_intent_for_projected_cash_balance(
    *,
    currency: str,
    balance: Decimal,
    base_currency: str,
    rate_to_base: Decimal,
    intent_id: str,
    fx_buffer_pct: Decimal,
) -> FxSpotIntent | None:
    if balance < 0:
        buy_amount = abs(balance) * (Decimal("1.0") + fx_buffer_pct)
        return FxSpotIntent(
            intent_id=intent_id,
            pair=f"{currency}/{base_currency}",
            buy_currency=currency,
            buy_amount=buy_amount,
            sell_currency=base_currency,
            sell_amount_estimated=buy_amount * rate_to_base,
            rationale=IntentRationale(code="FUNDING", message="Fund"),
        )
    if balance > 0:
        return FxSpotIntent(
            intent_id=intent_id,
            pair=f"{currency}/{base_currency}",
            buy_currency=base_currency,
            buy_amount=balance * rate_to_base,
            sell_currency=currency,
            sell_amount_estimated=balance,
            rationale=IntentRationale(code="SWEEP", message="Sweep"),
        )
    return None


def _link_execution_dependencies(
    *,
    intents: list[OrderIntent],
    fx_intent_id_by_currency: dict[str, str],
    include_same_currency_sell_dependency: bool | None,
) -> None:
    resolved_include_same_currency_sell_dependency = include_same_currency_sell_dependency
    if resolved_include_same_currency_sell_dependency is None:
        resolved_include_same_currency_sell_dependency = True

    dependency_intents = [
        intent for intent in intents if isinstance(intent, (SecurityTradeIntent, FxSpotIntent))
    ]
    link_buy_intent_dependencies(
        dependency_intents,
        fx_intent_id_by_currency=fx_intent_id_by_currency,
        include_same_currency_sell_dependency=resolved_include_same_currency_sell_dependency,
    )


def _append_projected_cash_fx_intents(
    *,
    projected_cash: dict[str, Decimal],
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    intents: list[OrderIntent],
    options: EngineOptions,
    diagnostics: DiagnosticsData,
) -> tuple[bool, dict[str, str]]:
    fx_intent_id_by_currency: dict[str, str] = {}
    for ccy, bal in projected_cash.items():
        if ccy == portfolio.base_currency:
            continue
        rate = get_fx_rate(market_data, ccy, portfolio.base_currency)
        if rate is None:
            diagnostics.data_quality.setdefault("fx_missing", []).append(
                f"{ccy}/{portfolio.base_currency}"
            )
            if options.block_on_missing_fx:
                return True, fx_intent_id_by_currency
            continue

        fx_id = f"oi_fx_{len(intents) + 1}"
        fx_intent = _fx_intent_for_projected_cash_balance(
            currency=ccy,
            balance=bal,
            base_currency=portfolio.base_currency,
            rate_to_base=rate,
            intent_id=fx_id,
            fx_buffer_pct=options.fx_buffer_pct,
        )
        if fx_intent is None:
            continue
        intents.append(fx_intent)
        if bal < 0:
            fx_intent_id_by_currency[ccy] = fx_id

    return False, fx_intent_id_by_currency


def _settlement_blocked_simulation_result(
    *,
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: list[ShelfEntry],
    intents: list[OrderIntent],
    options: EngineOptions,
    diagnostics: DiagnosticsData,
) -> _ExecutionSimulationResult:
    first_breach = diagnostics.cash_ladder_breaches[0]
    diagnostics.warnings.append(first_breach.reason_code)

    blocked_state = build_simulated_state(
        deepcopy(portfolio),
        market_data,
        shelf,
        diagnostics.data_quality,
        diagnostics.warnings,
        options,
    )
    blocked_rules = [
        RuleResult(
            rule_id="SETTLEMENT_CASH_LADDER",
            severity="HARD",
            status="FAIL",
            measured=first_breach.allowed_floor - first_breach.projected_balance,
            threshold={"min": first_breach.allowed_floor},
            reason_code=first_breach.reason_code,
            remediation_hint="Adjust timing, funding, or overdraft settings.",
        )
    ]
    return intents, blocked_state, blocked_rules, "BLOCKED", None


def _apply_execution_intents(
    *,
    portfolio: PortfolioSnapshot,
    intents: list[OrderIntent],
) -> PortfolioSnapshot:
    after = deepcopy(portfolio)

    for intent in intents:
        if intent.intent_type == "SECURITY_TRADE":
            apply_security_trade_to_portfolio(after, intent)
        elif intent.intent_type == "FX_SPOT":
            apply_fx_spot_to_portfolio(after, intent)

    return after


def _after_simulation_options(options: EngineOptions) -> EngineOptions:
    after_valuation_mode = (
        ValuationMode.TRUST_SNAPSHOT
        if options.valuation_mode == ValuationMode.TRUST_SNAPSHOT
        else ValuationMode.CALCULATED
    )
    return options.model_copy(update={"valuation_mode": after_valuation_mode})


def generate_fx_and_simulate(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: list[ShelfEntry],
    intents: list[OrderIntent],
    options: EngineOptions,
    total_val_before: Decimal,
    diagnostics: DiagnosticsData,
) -> _ExecutionSimulationResult:
    """
    Applies intents, generates FX, checks Safety Guards, and computes Reconciliation.
    """
    proj = _project_cash_after_security_trades(portfolio=portfolio, intents=intents)

    blocked_on_missing_fx, fx_map = _append_projected_cash_fx_intents(
        projected_cash=proj,
        portfolio=portfolio,
        market_data=market_data,
        intents=intents,
        options=options,
        diagnostics=diagnostics,
    )
    if blocked_on_missing_fx:
        return intents, deepcopy(portfolio), [], "BLOCKED", None

    _link_execution_dependencies(
        intents=intents,
        fx_intent_id_by_currency=fx_map,
        include_same_currency_sell_dependency=options.link_buy_to_same_currency_sell_dependency,
    )

    intents = sort_execution_intents(intents)

    if options.enable_settlement_awareness:
        build_settlement_ladder(portfolio, shelf, intents, options, diagnostics)
        if diagnostics.cash_ladder_breaches:
            return _settlement_blocked_simulation_result(
                portfolio=portfolio,
                market_data=market_data,
                shelf=shelf,
                intents=intents,
                options=options,
                diagnostics=diagnostics,
            )

    after = _apply_execution_intents(
        portfolio=portfolio,
        intents=intents,
    )
    after_opts = _after_simulation_options(options)
    state = build_simulated_state(
        after, market_data, shelf, diagnostics.data_quality, diagnostics.warnings, after_opts
    )
    tv_after = state.total_value.amount

    rules = RuleEngine.evaluate(state, options, diagnostics)

    blocked = any(r.severity == "HARD" and r.status == "FAIL" for r in rules)

    if blocked:
        blockers = [r.rule_id for r in rules if r.severity == "HARD" and r.status == "FAIL"]
        if "NO_SHORTING" in blockers:
            diagnostics.warnings.append("SIMULATION_SAFETY_CHECK_FAILED")
        if "INSUFFICIENT_CASH" in blockers:
            diagnostics.warnings.append("SIMULATION_SAFETY_CHECK_FAILED")

        return intents, state, rules, "BLOCKED", None

    recon, recon_diff, tolerance = build_reconciliation(
        before_total=total_val_before,
        after_total=tv_after,
        expected_after_total=total_val_before,
        base_currency=portfolio.base_currency,
    )

    if recon.status == "MISMATCH":
        rules.append(
            RuleResult(
                rule_id="RECONCILIATION",
                severity="HARD",
                status="FAIL",
                measured=recon_diff,
                threshold={"max": tolerance},
                reason_code="VALUE_MISMATCH",
                remediation_hint="Check pricing/FX or engine logic.",
            )
        )
        return intents, state, rules, "BLOCKED", recon

    return intents, state, rules, derive_status_from_rules(rules), recon


def check_blocking_dq(dq_log: dict[str, list[str]], options: EngineOptions) -> bool:
    if dq_log.get("shelf_missing"):
        return True
    if dq_log.get("price_missing") and options.block_on_missing_prices:
        return True
    if dq_log.get("fx_missing") and options.block_on_missing_fx:
        return True
    return False
