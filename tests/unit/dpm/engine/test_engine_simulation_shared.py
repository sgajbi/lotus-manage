from decimal import Decimal

from src.core.common.simulation_shared import (
    _apply_security_buy,
    _apply_security_sell,
    apply_fx_spot_to_portfolio,
    apply_security_trade_to_portfolio,
    build_reconciliation,
    derive_status_from_rules,
    ensure_cash_balance,
    ensure_position,
    sort_execution_intents,
)
from src.core.compliance import RuleEngine
from src.core.models import (
    CashBalance,
    EngineOptions,
    FxSpotIntent,
    Money,
    Position,
    SecurityTradeIntent,
)
from src.core.rebalance.execution import check_blocking_dq
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


def test_security_trade_buy_helper_increases_matching_market_value_and_reduces_cash() -> None:
    position = Position(
        instrument_id="EQ_1",
        quantity=Decimal("3"),
        market_value=Money(amount=Decimal("300"), currency="USD"),
    )
    cash_balance = CashBalance(currency="USD", amount=Decimal("1000"))
    intent = SecurityTradeIntent(
        intent_id="oi_buy_helper",
        instrument_id="EQ_1",
        side="BUY",
        quantity=Decimal("2"),
        notional=Money(amount=Decimal("200"), currency="USD"),
        notional_base=Money(amount=Decimal("200"), currency="USD"),
    )

    _apply_security_buy(position=position, cash_balance=cash_balance, intent=intent)

    assert position.quantity == Decimal("5")
    assert position.market_value is not None
    assert position.market_value.amount == Decimal("500")
    assert cash_balance.amount == Decimal("800")


def test_security_trade_sell_helper_floors_matching_market_value_and_adds_cash() -> None:
    position = Position(
        instrument_id="EQ_1",
        quantity=Decimal("3"),
        market_value=Money(amount=Decimal("100"), currency="USD"),
    )
    cash_balance = CashBalance(currency="USD", amount=Decimal("50"))
    intent = SecurityTradeIntent(
        intent_id="oi_sell_helper",
        instrument_id="EQ_1",
        side="SELL",
        quantity=Decimal("2"),
        notional=Money(amount=Decimal("200"), currency="USD"),
        notional_base=Money(amount=Decimal("200"), currency="USD"),
    )

    _apply_security_sell(position=position, cash_balance=cash_balance, intent=intent)

    assert position.quantity == Decimal("1")
    assert position.market_value is not None
    assert position.market_value.amount == Decimal("0")
    assert cash_balance.amount == Decimal("250")


def test_security_trade_helpers_preserve_mismatched_market_value_currency() -> None:
    position = Position(
        instrument_id="EQ_1",
        quantity=Decimal("1"),
        market_value=Money(amount=Decimal("300"), currency="EUR"),
    )
    cash_balance = CashBalance(currency="USD", amount=Decimal("1000"))
    intent = SecurityTradeIntent(
        intent_id="oi_buy_currency_mismatch",
        instrument_id="EQ_1",
        side="BUY",
        quantity=Decimal("1"),
        notional=Money(amount=Decimal("100"), currency="USD"),
        notional_base=Money(amount=Decimal("100"), currency="USD"),
    )

    _apply_security_buy(position=position, cash_balance=cash_balance, intent=intent)

    assert position.market_value is not None
    assert position.market_value.amount == Decimal("300")
    assert position.market_value.currency == "EUR"
    assert cash_balance.amount == Decimal("900")


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


def test_check_blocking_dq_always_blocks_missing_shelf_entries() -> None:
    assert check_blocking_dq({"shelf_missing": ["EQ_1"]}, EngineOptions()) is True


def test_check_blocking_dq_respects_missing_price_option() -> None:
    dq_log = {"price_missing": ["EQ_1"]}

    assert check_blocking_dq(dq_log, EngineOptions(block_on_missing_prices=True)) is True
    assert check_blocking_dq(dq_log, EngineOptions(block_on_missing_prices=False)) is False


def test_check_blocking_dq_respects_missing_fx_option() -> None:
    dq_log = {"fx_missing": ["EUR/USD"]}

    assert check_blocking_dq(dq_log, EngineOptions(block_on_missing_fx=True)) is True
    assert check_blocking_dq(dq_log, EngineOptions(block_on_missing_fx=False)) is False


def test_check_blocking_dq_ignores_empty_and_non_blocking_buckets() -> None:
    dq_log = {
        "shelf_missing": [],
        "price_missing": [],
        "fx_missing": [],
        "advisory_note_missing": ["NOTE_1"],
    }

    assert check_blocking_dq(dq_log, EngineOptions()) is False


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


def test_sort_execution_intents_orders_sell_fx_buy():
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

    ordered = sort_execution_intents([buy_intent, fx_intent, sell_intent])
    assert [intent.intent_type for intent in ordered] == [
        "SECURITY_TRADE",
        "FX_SPOT",
        "SECURITY_TRADE",
    ]
    assert ordered[0].side == "SELL"
    assert ordered[2].side == "BUY"


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
