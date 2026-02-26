from copy import deepcopy
from decimal import Decimal
from typing import Literal

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
    PortfolioSnapshot,
    ProposalOrderIntent,
    Reconciliation,
    RuleResult,
    ShelfEntry,
    SimulatedState,
    ValuationMode,
)
from src.core.valuation import build_simulated_state, get_fx_rate


def build_settlement_ladder(
    portfolio: PortfolioSnapshot,
    shelf: list[ShelfEntry],
    intents: list[ProposalOrderIntent],
    options: EngineOptions,
    diagnostics: DiagnosticsData,
) -> None:
    settlement_days_by_instrument = {entry.instrument_id: entry.settlement_days for entry in shelf}
    max_security_day = max(
        (
            settlement_days_by_instrument.get(intent.instrument_id, 2)
            for intent in intents
            if intent.intent_type == "SECURITY_TRADE"
        ),
        default=0,
    )
    horizon_days = max(
        options.settlement_horizon_days, options.fx_settlement_days, max_security_day
    )

    flows: dict[str, list[Decimal]] = {}

    def ensure_currency(currency: str) -> None:
        if currency not in flows:
            flows[currency] = [Decimal("0")] * (horizon_days + 1)

    for cash in portfolio.cash_balances:
        ensure_currency(cash.currency)
        flows[cash.currency][0] += cash.settled if cash.settled is not None else cash.amount

    for intent in sorted(intents, key=lambda item: item.intent_id):
        if intent.intent_type == "SECURITY_TRADE":
            if intent.notional is None:
                continue
            settlement_day = settlement_days_by_instrument.get(intent.instrument_id, 2)
            ensure_currency(intent.notional.currency)
            signed_flow = (
                intent.notional.amount if intent.side == "SELL" else -intent.notional.amount
            )
            flows[intent.notional.currency][settlement_day] += signed_flow
            continue

        ensure_currency(intent.sell_currency)
        ensure_currency(intent.buy_currency)
        flows[intent.sell_currency][options.fx_settlement_days] -= intent.sell_amount_estimated
        flows[intent.buy_currency][options.fx_settlement_days] += intent.buy_amount

    overdraft_utilized = False
    for currency in sorted(flows.keys()):
        projected_balance = Decimal("0")
        allowed_floor = -options.max_overdraft_by_ccy.get(currency, Decimal("0"))
        for day in range(horizon_days + 1):
            projected_balance += flows[currency][day]
            diagnostics.cash_ladder.append(
                CashLadderPoint(
                    date_offset=day,
                    currency=currency,
                    projected_balance=projected_balance,
                )
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


def generate_fx_and_simulate(
    portfolio: PortfolioSnapshot,
    market_data: MarketDataSnapshot,
    shelf: list[ShelfEntry],
    intents: list[ProposalOrderIntent],
    options: EngineOptions,
    total_val_before: Decimal,
    diagnostics: DiagnosticsData,
) -> tuple[
    list[ProposalOrderIntent],
    SimulatedState | PortfolioSnapshot,
    list[RuleResult],
    Literal["READY", "BLOCKED", "PENDING_REVIEW"],
    Reconciliation | None,
]:
    """
    Applies intents, generates FX, checks Safety Guards, and computes Reconciliation.
    """
    proj = {c.currency: c.amount for c in portfolio.cash_balances}
    for i in intents:
        if i.intent_type == "SECURITY_TRADE":
            if i.notional is None:
                continue
            proj[i.notional.currency] = proj.get(i.notional.currency, Decimal("0")) + (
                i.notional.amount if i.side == "SELL" else -i.notional.amount
            )

    fx_map = {}
    for ccy, bal in proj.items():
        if ccy == portfolio.base_currency:
            continue
        rate = get_fx_rate(market_data, ccy, portfolio.base_currency)
        if rate is None:
            diagnostics.data_quality.setdefault("fx_missing", []).append(
                f"{ccy}/{portfolio.base_currency}"
            )
            if options.block_on_missing_fx:
                return intents, deepcopy(portfolio), [], "BLOCKED", None
            continue

        if bal < 0:
            buy_amt = abs(bal) * (Decimal("1.0") + options.fx_buffer_pct)
            sell_amt = buy_amt * rate
            fx_id = f"oi_fx_{len(intents) + 1}"
            fx_map[ccy] = fx_id
            intents.append(
                FxSpotIntent(
                    intent_id=fx_id,
                    pair=f"{ccy}/{portfolio.base_currency}",
                    buy_currency=ccy,
                    buy_amount=buy_amt,
                    sell_currency=portfolio.base_currency,
                    sell_amount_estimated=sell_amt,
                    rationale=IntentRationale(code="FUNDING", message="Fund"),
                )
            )
        elif bal > 0:
            buy_amt = bal * rate
            fx_id = f"oi_fx_{len(intents) + 1}"
            intents.append(
                FxSpotIntent(
                    intent_id=fx_id,
                    pair=f"{ccy}/{portfolio.base_currency}",
                    buy_currency=portfolio.base_currency,
                    buy_amount=buy_amt,
                    sell_currency=ccy,
                    sell_amount_estimated=bal,
                    rationale=IntentRationale(code="SWEEP", message="Sweep"),
                )
            )

    include_sell_dependency = options.link_buy_to_same_currency_sell_dependency
    if include_sell_dependency is None:
        include_sell_dependency = True
    link_buy_intent_dependencies(
        intents,
        fx_intent_id_by_currency=fx_map,
        include_same_currency_sell_dependency=include_sell_dependency,
    )

    intents = sort_execution_intents(intents)

    if options.enable_settlement_awareness:
        build_settlement_ladder(portfolio, shelf, intents, options, diagnostics)
        if diagnostics.cash_ladder_breaches:
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

    after = deepcopy(portfolio)

    for i in intents:
        if i.intent_type == "SECURITY_TRADE":
            apply_security_trade_to_portfolio(after, i)
        elif i.intent_type == "FX_SPOT":
            apply_fx_spot_to_portfolio(after, i)

    after_opts = options.model_copy(update={"valuation_mode": ValuationMode.CALCULATED})
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
