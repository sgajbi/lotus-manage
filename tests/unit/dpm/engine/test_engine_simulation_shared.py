from decimal import Decimal

from src.core.common.simulation_shared import (
    apply_fx_spot_to_portfolio,
    apply_security_trade_to_portfolio,
    build_reconciliation,
    derive_status_from_rules,
    ensure_cash_balance,
    ensure_position,
    sort_execution_intents,
)
from src.core.compliance import RuleEngine
from src.core.models import CashFlowIntent, EngineOptions, FxSpotIntent, SecurityTradeIntent
from src.core.valuation import build_simulated_state
from tests.shared.factories import cash, market_data_snapshot, portfolio_snapshot
from tests.unit.dpm.engine.coverage.helpers import empty_diagnostics


def test_ensure_helpers_create_missing_entries():
    portfolio = portfolio_snapshot(portfolio_id="pf_shared_1", base_currency="USD")
    position = ensure_position(portfolio, "EQ_1")
    cash_balance = ensure_cash_balance(portfolio, "USD")

    assert position.instrument_id == "EQ_1"
    assert cash_balance.currency == "USD"
    assert cash_balance.amount == Decimal("0")


def test_apply_security_trade_to_portfolio_mutates_position_and_cash():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_shared_2",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    intent = SecurityTradeIntent(
        intent_id="oi_1",
        instrument_id="EQ_1",
        side="BUY",
        quantity=Decimal("2"),
        notional={"amount": Decimal("200"), "currency": "USD"},
        notional_base={"amount": Decimal("200"), "currency": "USD"},
    )

    apply_security_trade_to_portfolio(portfolio, intent)

    assert portfolio.positions[0].instrument_id == "EQ_1"
    assert portfolio.positions[0].quantity == Decimal("2")
    assert portfolio.cash_balances[0].amount == Decimal("800")


def test_derive_status_from_rules_matches_ready_outcome():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_shared_3",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    diagnostics = empty_diagnostics()
    state = build_simulated_state(
        portfolio=portfolio,
        market_data=market_data_snapshot(prices=[], fx_rates=[]),
        shelf=[],
        dq_log=diagnostics.data_quality,
        warnings=diagnostics.warnings,
        options=EngineOptions(),
    )
    rules = RuleEngine.evaluate(state, EngineOptions(), diagnostics)

    assert derive_status_from_rules(rules) == "READY"


def test_build_reconciliation_returns_ok_for_expected_total():
    reconciliation, recon_diff, tolerance = build_reconciliation(
        before_total=Decimal("100"),
        after_total=Decimal("110"),
        expected_after_total=Decimal("110"),
        base_currency="USD",
    )

    assert reconciliation.status == "OK"
    assert recon_diff == Decimal("0")
    assert tolerance > Decimal("0")


def test_apply_fx_spot_to_portfolio_mutates_both_currencies():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_shared_4",
        base_currency="USD",
        cash_balances=[cash("USD", "1000"), cash("EUR", "0")],
    )
    intent = FxSpotIntent(
        intent_id="oi_fx_1",
        pair="EUR/USD",
        buy_currency="EUR",
        buy_amount=Decimal("100"),
        sell_currency="USD",
        sell_amount_estimated=Decimal("110"),
    )

    apply_fx_spot_to_portfolio(portfolio, intent)

    usd_cash = next(c for c in portfolio.cash_balances if c.currency == "USD")
    eur_cash = next(c for c in portfolio.cash_balances if c.currency == "EUR")
    assert usd_cash.amount == Decimal("890")
    assert eur_cash.amount == Decimal("100")


def test_sort_execution_intents_orders_cashflow_sell_fx_buy():
    cash_intent = CashFlowIntent(intent_id="oi_cf_1", currency="USD", amount=Decimal("100"))
    buy_intent = SecurityTradeIntent(
        intent_id="oi_buy_1",
        instrument_id="EQ_B",
        side="BUY",
        quantity=Decimal("1"),
        notional={"amount": Decimal("100"), "currency": "USD"},
        notional_base={"amount": Decimal("100"), "currency": "USD"},
    )
    sell_intent = SecurityTradeIntent(
        intent_id="oi_sell_1",
        instrument_id="EQ_A",
        side="SELL",
        quantity=Decimal("1"),
        notional={"amount": Decimal("100"), "currency": "USD"},
        notional_base={"amount": Decimal("100"), "currency": "USD"},
    )
    fx_intent = FxSpotIntent(
        intent_id="oi_fx_1",
        pair="EUR/USD",
        buy_currency="EUR",
        buy_amount=Decimal("100"),
        sell_currency="USD",
        sell_amount_estimated=Decimal("110"),
    )

    ordered = sort_execution_intents([buy_intent, fx_intent, cash_intent, sell_intent])
    assert [intent.intent_type for intent in ordered] == [
        "CASH_FLOW",
        "SECURITY_TRADE",
        "FX_SPOT",
        "SECURITY_TRADE",
    ]
    assert ordered[1].side == "SELL"
    assert ordered[3].side == "BUY"


def test_apply_security_trade_to_portfolio_ignores_incomplete_trade_intent():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_shared_5",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    intent = SecurityTradeIntent(
        intent_id="oi_incomplete_1",
        instrument_id="EQ_1",
        side="BUY",
        quantity=None,
        notional=None,
        notional_base=None,
    )

    apply_security_trade_to_portfolio(portfolio, intent)

    assert portfolio.positions == []
    assert portfolio.cash_balances[0].amount == Decimal("1000")


def test_apply_fx_spot_to_portfolio_ignores_non_fx_intent():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_shared_6",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    intent = SecurityTradeIntent(
        intent_id="oi_non_fx_1",
        instrument_id="EQ_1",
        side="BUY",
        quantity=Decimal("1"),
        notional={"amount": Decimal("100"), "currency": "USD"},
        notional_base={"amount": Decimal("100"), "currency": "USD"},
    )

    apply_fx_spot_to_portfolio(portfolio, intent)

    assert portfolio.cash_balances[0].amount == Decimal("1000")
