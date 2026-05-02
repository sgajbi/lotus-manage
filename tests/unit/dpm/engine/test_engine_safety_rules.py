from decimal import Decimal

from src.core.rebalance.engine import _generate_fx_and_simulate, run_simulation
from src.core.rebalance.intents import generate_intents
from src.core.models import (
    EngineOptions,
    Money,
    SecurityTradeIntent,
)
from tests.unit.dpm.engine.coverage.helpers import empty_diagnostics
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


def test_generated_sell_intents_are_clamped_to_available_holding(base_options):
    portfolio, market_data, model, shelf = get_base_data()
    portfolio.positions[0].quantity = Decimal("10")
    portfolio.positions[0].market_value = Money(amount=Decimal("10000.0"), currency="SGD")
    options = base_options.model_copy(update={"valuation_mode": "TRUST_SNAPSHOT"})

    result = run_simulation(portfolio, market_data, model, shelf, options)

    assert result.status in {"READY", "PENDING_REVIEW"}
    assert "SIMULATION_SAFETY_CHECK_FAILED" not in result.diagnostics.warnings

    sell = next(intent for intent in result.intents if intent.instrument_id == "EQ_1")
    assert sell.side == "SELL"
    assert sell.quantity == Decimal("10")

    rule = next((r for r in result.rule_results if r.rule_id == "NO_SHORTING"), None)
    assert rule is not None
    assert rule.status == "PASS"


def test_sell_intent_generation_defensively_clamps_impossible_target():
    portfolio, market_data, _, shelf = get_base_data()
    portfolio.positions[0].quantity = Decimal("10")
    portfolio.positions[0].market_value = Money(amount=Decimal("10000.0"), currency="SGD")
    diagnostics = empty_diagnostics()

    intents, _ = generate_intents(
        portfolio=portfolio,
        market_data=market_data,
        targets=[
            type(
                "Target",
                (),
                {"instrument_id": "EQ_1", "final_weight": Decimal("-1.0")},
            )()
        ],
        shelf=shelf,
        options=EngineOptions(valuation_mode="TRUST_SNAPSHOT"),
        total_val=Decimal("11000"),
        dq_log=diagnostics.data_quality,
        diagnostics=diagnostics,
        suppressed=diagnostics.suppressed_intents,
    )

    assert intents[0].quantity == Decimal("10")
    assert intents[0].notional.amount == Decimal("10000.0")
    assert "AVAILABLE_HOLDING" in intents[0].constraints_applied
    assert "SELL_QUANTITY_CLAMPED_TO_AVAILABLE_HOLDING" in diagnostics.warnings


def test_trusted_market_value_drives_sell_sizing_and_after_state(base_options):
    portfolio, market_data, model, shelf = get_base_data()
    portfolio.positions[0].quantity = Decimal("10")
    portfolio.positions[0].market_value = Money(amount=Decimal("10000.0"), currency="SGD")
    options = base_options.model_copy(update={"valuation_mode": "TRUST_SNAPSHOT"})

    result = run_simulation(portfolio, market_data, model, shelf, options)

    sell = next(intent for intent in result.intents if intent.instrument_id == "EQ_1")
    assert sell.quantity == Decimal("10")
    assert sell.notional.amount == Decimal("10000.0")
    assert result.before.total_value.amount == Decimal("11000.0")
    assert result.after_simulated.total_value.amount == Decimal("11000.0")
    assert result.reconciliation is not None
    assert result.reconciliation.status == "OK"


def test_safety_no_shorting_still_blocks_invalid_external_intent():
    portfolio, market_data, _, shelf = get_base_data()
    diagnostics = empty_diagnostics()
    invalid_intents = [
        SecurityTradeIntent(
            intent_id="oi_invalid_oversell",
            instrument_id="EQ_1",
            side="SELL",
            quantity=Decimal("101"),
            notional=Money(amount=Decimal("1010"), currency="SGD"),
            notional_base=Money(amount=Decimal("1010"), currency="SGD"),
        )
    ]

    _, _, rules, status, _ = _generate_fx_and_simulate(
        portfolio=portfolio,
        market_data=market_data,
        shelf=shelf,
        intents=invalid_intents,
        options=EngineOptions(),
        total_val_before=Decimal("2000"),
        diagnostics=diagnostics,
    )

    assert status == "BLOCKED"
    assert "SIMULATION_SAFETY_CHECK_FAILED" in diagnostics.warnings

    rule = next((r for r in rules if r.rule_id == "NO_SHORTING"), None)
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
