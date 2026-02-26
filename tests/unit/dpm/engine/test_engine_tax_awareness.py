from decimal import Decimal

from src.core.dpm_engine import run_simulation
from src.core.models import EngineOptions
from tests.shared.assertions import assert_status, security_intents
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    price,
    shelf_entry,
    target,
)


def _tax_context():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_tax",
        base_currency="USD",
        positions=[
            {
                "instrument_id": "ABC",
                "quantity": Decimal("100"),
                "lots": [
                    {
                        "lot_id": "L_LOW",
                        "quantity": Decimal("50"),
                        "unit_cost": {"amount": Decimal("10"), "currency": "USD"},
                        "purchase_date": "2024-01-01",
                    },
                    {
                        "lot_id": "L_HIGH",
                        "quantity": Decimal("50"),
                        "unit_cost": {"amount": Decimal("100"), "currency": "USD"},
                        "purchase_date": "2024-02-01",
                    },
                ],
            }
        ],
        cash_balances=[cash("USD", "0")],
    )
    market_data = market_data_snapshot(prices=[price("ABC", "100", "USD")], fx_rates=[])
    shelf = [shelf_entry("ABC", status="APPROVED", asset_class="EQUITY")]
    return portfolio, market_data, shelf


def test_tax_awareness_disabled_keeps_legacy_sell_behavior():
    portfolio, market_data, shelf = _tax_context()
    model = model_portfolio(targets=[target("ABC", "0.0")])

    result = run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=EngineOptions(
            enable_tax_awareness=False, max_realized_capital_gains=Decimal("100")
        ),
    )

    assert_status(result, "READY")
    assert security_intents(result)[0].quantity == Decimal("100")
    assert result.tax_impact is None


def test_tax_awareness_hifo_allows_zero_gain_sell_under_budget():
    portfolio, market_data, shelf = _tax_context()
    model = model_portfolio(targets=[target("ABC", "0.5")])

    result = run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=EngineOptions(enable_tax_awareness=True, max_realized_capital_gains=Decimal("100")),
    )

    assert_status(result, "READY")
    assert security_intents(result)[0].quantity == Decimal("50")
    assert result.tax_impact is not None
    assert result.tax_impact.total_realized_gain.amount == Decimal("0")
    assert result.tax_impact.total_realized_loss.amount == Decimal("0")


def test_tax_awareness_budget_caps_sell_quantity_with_diagnostics():
    portfolio, market_data, shelf = _tax_context()
    model = model_portfolio(targets=[target("ABC", "0.0")])

    result = run_simulation(
        portfolio=portfolio,
        market_data=market_data,
        model=model,
        shelf=shelf,
        options=EngineOptions(enable_tax_awareness=True, max_realized_capital_gains=Decimal("100")),
    )

    assert_status(result, "READY")
    sell_qty = security_intents(result)[0].quantity
    assert sell_qty > Decimal("50")
    assert sell_qty < Decimal("100")
    assert "TAX_BUDGET_LIMIT_REACHED" in result.diagnostics.warnings
    assert len(result.diagnostics.tax_budget_constraint_events) == 1
    assert result.tax_impact is not None
    assert result.tax_impact.budget_used is not None
    assert result.tax_impact.budget_used.amount == Decimal("100")
