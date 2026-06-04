from decimal import Decimal

from src.core.rebalance.engine import run_simulation
from src.core.rebalance.execution import (
    _append_settlement_ladder_points,
    _settlement_cash_flows,
    _settlement_days_by_instrument,
    _settlement_horizon_days,
)
from src.core.models import EngineOptions, FxSpotIntent, IntentRationale, Money, SecurityTradeIntent
from tests.shared.assertions import assert_status
from tests.unit.dpm.engine.coverage.helpers import empty_diagnostics
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


def test_settlement_cash_flows_apply_security_and_fx_settlement_days() -> None:
    portfolio = portfolio_snapshot(
        portfolio_id="pf_settlement_helpers",
        base_currency="USD",
        cash_balances=[cash("USD", "100"), cash("EUR", "0")],
    )
    shelf = [
        shelf_entry("SLOW_FUND", status="APPROVED", settlement_days=3),
        shelf_entry("FAST_STOCK", status="APPROVED", settlement_days=1),
    ]
    intents = [
        SecurityTradeIntent(
            intent_id="oi_buy_fast",
            instrument_id="FAST_STOCK",
            side="BUY",
            quantity=Decimal("2"),
            notional=Money(amount=Decimal("80"), currency="USD"),
            notional_base=Money(amount=Decimal("80"), currency="USD"),
        ),
        SecurityTradeIntent(
            intent_id="oi_sell_slow",
            instrument_id="SLOW_FUND",
            side="SELL",
            quantity=Decimal("1"),
            notional=Money(amount=Decimal("30"), currency="USD"),
            notional_base=Money(amount=Decimal("30"), currency="USD"),
        ),
        FxSpotIntent(
            intent_id="oi_fx_eur",
            pair="EUR/USD",
            buy_currency="EUR",
            buy_amount=Decimal("50"),
            sell_currency="USD",
            sell_amount_estimated=Decimal("55"),
            rationale=IntentRationale(code="FUNDING", message="Fund EUR purchase."),
        ),
    ]
    settlement_days = _settlement_days_by_instrument(shelf)
    options = EngineOptions(fx_settlement_days=2, settlement_horizon_days=1)

    horizon = _settlement_horizon_days(
        settlement_days_by_instrument=settlement_days,
        intents=intents,
        options=options,
    )
    flows = _settlement_cash_flows(
        portfolio=portfolio,
        intents=intents,
        settlement_days_by_instrument=settlement_days,
        horizon_days=horizon,
        options=options,
    )

    assert horizon == 3
    assert flows["USD"] == [
        Decimal("100"),
        Decimal("-80"),
        Decimal("-55"),
        Decimal("30"),
    ]
    assert flows["EUR"] == [
        Decimal("0"),
        Decimal("0"),
        Decimal("50"),
        Decimal("0"),
    ]


def test_append_settlement_ladder_points_records_breach_and_overdraft_warning() -> None:
    diagnostics = empty_diagnostics()

    _append_settlement_ladder_points(
        flows={"USD": [Decimal("50"), Decimal("-90"), Decimal("10")]},
        horizon_days=2,
        options=EngineOptions(max_overdraft_by_ccy={"USD": Decimal("25")}),
        diagnostics=diagnostics,
    )

    assert [point.projected_balance for point in diagnostics.cash_ladder] == [
        Decimal("50"),
        Decimal("-40"),
        Decimal("-30"),
    ]
    assert diagnostics.cash_ladder_breaches[0].date_offset == 1
    assert diagnostics.cash_ladder_breaches[0].allowed_floor == Decimal("-25")
    assert diagnostics.cash_ladder_breaches[0].reason_code == "OVERDRAFT_ON_T_PLUS_1"
    assert "SETTLEMENT_OVERDRAFT_UTILIZED" in diagnostics.warnings
