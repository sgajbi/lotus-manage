from src.core.dpm_engine import run_simulation
from src.core.models import EngineOptions
from tests.shared.assertions import assert_status
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


def _settlement_toggle_context():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_settlement",
        base_currency="USD",
        positions=[position("SLOW_FUND", "10")],
        cash_balances=[cash("USD", "0")],
    )
    market_data = market_data_snapshot(
        prices=[
            price("SLOW_FUND", "100", "USD"),
            price("FAST_STOCK", "100", "USD"),
        ],
        fx_rates=[],
    )
    model = model_portfolio(
        targets=[
            target("SLOW_FUND", "0.0"),
            target("FAST_STOCK", "1.0"),
        ]
    )
    shelf = [
        shelf_entry("SLOW_FUND", status="APPROVED", asset_class="FUND", settlement_days=3),
        shelf_entry("FAST_STOCK", status="APPROVED", asset_class="EQUITY", settlement_days=1),
    ]
    return portfolio, market_data, model, shelf


def test_settlement_awareness_can_be_disabled_per_request():
    portfolio, market_data, model, shelf = _settlement_toggle_context()

    result = run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=EngineOptions(enable_settlement_awareness=False),
    )

    assert_status(result, "READY")
    assert result.diagnostics.cash_ladder == []
    assert result.diagnostics.cash_ladder_breaches == []


def test_settlement_awareness_blocks_on_timing_overdraft():
    portfolio, market_data, model, shelf = _settlement_toggle_context()

    result = run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=EngineOptions(enable_settlement_awareness=True, settlement_horizon_days=3),
    )

    assert_status(result, "BLOCKED")
    assert result.diagnostics.cash_ladder
    assert result.diagnostics.cash_ladder_breaches
    assert result.diagnostics.cash_ladder_breaches[0].date_offset == 1
    assert result.diagnostics.cash_ladder_breaches[0].reason_code == "OVERDRAFT_ON_T_PLUS_1"
    assert "OVERDRAFT_ON_T_PLUS_1" in result.diagnostics.warnings


def test_settlement_awareness_allows_configured_overdraft():
    portfolio, market_data, model, shelf = _settlement_toggle_context()

    result = run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=EngineOptions(
            enable_settlement_awareness=True,
            settlement_horizon_days=3,
            max_overdraft_by_ccy={"USD": 1000},
        ),
    )

    assert_status(result, "READY")
    assert result.diagnostics.cash_ladder
    assert result.diagnostics.cash_ladder_breaches == []
    assert "SETTLEMENT_OVERDRAFT_UTILIZED" in result.diagnostics.warnings
