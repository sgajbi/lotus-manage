from src.core.dpm_engine import run_simulation
from src.core.models import EngineOptions
from tests.shared.assertions import assert_dq_contains, assert_status, find_excluded
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    price,
    shelf_entry,
    target,
)


def test_missing_price_non_blocking_when_option_disabled():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_edge_px",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[], fx_rates=[])
    model = model_portfolio(targets=[target("MISSING_PRICE", "1.0")])
    shelf = [shelf_entry("MISSING_PRICE", status="APPROVED")]

    result = run_simulation(
        portfolio,
        market_data,
        model,
        shelf,
        EngineOptions(block_on_missing_prices=False),
    )

    assert result.status in {"READY", "PENDING_REVIEW"}
    assert_dq_contains(result, "price_missing", "MISSING_PRICE")


def test_missing_fx_for_target_blocks_by_default():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_edge_fx_block",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[price("EUR_EQ", "100", "EUR")], fx_rates=[])
    model = model_portfolio(targets=[target("EUR_EQ", "1.0")])
    shelf = [shelf_entry("EUR_EQ", status="APPROVED")]

    result = run_simulation(portfolio, market_data, model, shelf, EngineOptions())

    assert_status(result, "BLOCKED")
    assert_dq_contains(result, "fx_missing", "EUR/USD")


def test_missing_fx_for_target_non_blocking_when_disabled():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_edge_fx_continue",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(prices=[price("EUR_EQ", "100", "EUR")], fx_rates=[])
    model = model_portfolio(targets=[target("EUR_EQ", "1.0")])
    shelf = [shelf_entry("EUR_EQ", status="APPROVED")]

    result = run_simulation(
        portfolio,
        market_data,
        model,
        shelf,
        EngineOptions(block_on_missing_fx=False),
    )

    assert result.status in {"READY", "PENDING_REVIEW"}
    assert_dq_contains(result, "fx_missing", "EUR/USD")


def test_allow_restricted_true_allows_restricted_target_trading():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_edge_restricted",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    market_data = market_data_snapshot(
        prices=[price("RESTRICTED_EQ", "100", "USD")],
        fx_rates=[],
    )
    model = model_portfolio(targets=[target("RESTRICTED_EQ", "1.0")])
    shelf = [shelf_entry("RESTRICTED_EQ", status="RESTRICTED")]

    result = run_simulation(
        portfolio,
        market_data,
        model,
        shelf,
        EngineOptions(allow_restricted=True),
    )

    assert any(i.intent_type == "SECURITY_TRADE" and i.side == "BUY" for i in result.intents)
    assert find_excluded(result, "RESTRICTED_EQ") is None
