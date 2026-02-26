from decimal import Decimal

from src.core.dpm_engine import run_simulation
from src.core.models import (
    Money,
)
from tests.shared.factories import (
    cash,
    fx,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


def get_base_data():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_safe",
        base_currency="SGD",
        positions=[position("EQ_1", "100")],
        cash_balances=[cash("SGD", "1000.0")],
    )
    market_data = market_data_snapshot(prices=[price("EQ_1", "10.0", "SGD")], fx_rates=[])
    model = model_portfolio(targets=[target("EQ_1", "0.0")])
    shelf = [shelf_entry("EQ_1", status="APPROVED")]
    return portfolio, market_data, model, shelf


def test_safety_no_shorting_block(base_options):
    portfolio, market_data, model, shelf = get_base_data()
    portfolio.positions[0].quantity = Decimal("10")
    portfolio.positions[0].market_value = Money(amount=Decimal("10000.0"), currency="SGD")

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status == "BLOCKED"
    assert "SIMULATION_SAFETY_CHECK_FAILED" in result.diagnostics.warnings

    rule = next((r for r in result.rule_results if r.rule_id == "NO_SHORTING"), None)
    assert rule is not None
    assert rule.status == "FAIL"
    assert rule.reason_code == "SELL_EXCEEDS_HOLDINGS"


def test_safety_insufficient_cash_block(base_options):
    portfolio, market_data, model, shelf = get_base_data()
    portfolio.positions = []
    portfolio.cash_balances[0].amount = Decimal("100.0")

    market_data.prices = [price("US_EQ", "10.0", "USD")]
    market_data.fx_rates = [fx("USD/SGD", "1.0")]
    model.targets = [target("US_EQ", "1.0")]
    shelf = [shelf_entry("US_EQ", status="APPROVED")]
    options = base_options.model_copy(update={"fx_buffer_pct": Decimal("0.05")})

    result = run_simulation(portfolio, market_data, model, shelf, options)

    assert result.status == "BLOCKED"
    assert "SIMULATION_SAFETY_CHECK_FAILED" in result.diagnostics.warnings

    rule = next((r for r in result.rule_results if r.rule_id == "INSUFFICIENT_CASH"), None)
    assert rule is not None
    assert rule.status == "FAIL"


def test_reconciliation_object_populated_on_success(base_options):
    portfolio, market_data, model, shelf = get_base_data()
    model.targets[0].weight = Decimal("0.5")

    result = run_simulation(portfolio, market_data, model, shelf, base_options)

    assert result.status in ["READY", "PENDING_REVIEW"]
    assert result.reconciliation is not None
    assert result.reconciliation.status == "OK"
    assert abs(result.reconciliation.delta.amount) < Decimal("1.0")
