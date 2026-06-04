from decimal import Decimal

from src.core.rebalance.engine import _generate_fx_and_simulate, run_simulation
from src.core.rebalance.intents import (
    _TaxBudgetAccumulator,
    _TaxBudgetLotAllowance,
    _apply_tax_budget_lot_allowance,
    _clamped_sell_quantity,
    _current_instrument_value_and_unit_value,
    _hifo_sorted_lots,
    _intent_market_context,
    _record_tax_budget_limit_reached,
    _security_intent_constraints,
    _suppress_dust_trade,
    _target_trade_delta,
    _tax_impact_from_budget,
    _tax_budget_lot_allowance,
    _tax_budget_limited_sell_quantity,
    _trade_notional_threshold,
    generate_intents,
)
from src.core.models import (
    EngineOptions,
    Money,
    Position,
    SecurityTradeIntent,
    TaxLot,
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


def test_hifo_sorted_lots_orders_highest_cost_then_latest_purchase() -> None:
    lot_position = Position(
        instrument_id="EQ_1",
        quantity=Decimal("30"),
        lots=[
            TaxLot(
                lot_id="LOT_LOW",
                quantity=Decimal("10"),
                unit_cost=Money(amount=Decimal("80"), currency="SGD"),
                purchase_date="2024-01-01",
            ),
            TaxLot(
                lot_id="LOT_HIGH_OLD",
                quantity=Decimal("10"),
                unit_cost=Money(amount=Decimal("100"), currency="SGD"),
                purchase_date="2024-02-01",
            ),
            TaxLot(
                lot_id="LOT_HIGH_NEW",
                quantity=Decimal("10"),
                unit_cost=Money(amount=Decimal("100"), currency="SGD"),
                purchase_date="2024-03-01",
            ),
        ],
    )

    sorted_lots = _hifo_sorted_lots(
        position=lot_position,
        instrument_ccy="SGD",
        market_data=market_data_snapshot(),
        dq_log={"fx_missing": []},
    )

    assert [lot.lot_id for lot, _cost in sorted_lots] == [
        "LOT_HIGH_NEW",
        "LOT_HIGH_OLD",
        "LOT_LOW",
    ]


def test_hifo_sorted_lots_returns_empty_when_lot_fx_is_missing() -> None:
    lot_position = Position(
        instrument_id="EQ_1",
        quantity=Decimal("10"),
        lots=[
            TaxLot(
                lot_id="LOT_EUR",
                quantity=Decimal("10"),
                unit_cost=Money(amount=Decimal("80"), currency="EUR"),
                purchase_date="2024-01-01",
            )
        ],
    )
    dq_log = {"fx_missing": []}

    assert (
        _hifo_sorted_lots(
            position=lot_position,
            instrument_ccy="SGD",
            market_data=market_data_snapshot(),
            dq_log=dq_log,
        )
        == []
    )
    assert dq_log["fx_missing"] == ["EUR/SGD"]


def test_clamped_sell_quantity_records_warning_once() -> None:
    diagnostics = empty_diagnostics()
    sell_position = Position(instrument_id="EQ_1", quantity=Decimal("10"))

    first = _clamped_sell_quantity(
        requested_qty=Decimal("20"),
        position=sell_position,
        diagnostics=diagnostics,
    )
    second = _clamped_sell_quantity(
        requested_qty=Decimal("15"),
        position=sell_position,
        diagnostics=diagnostics,
    )

    assert first == Decimal("10")
    assert second == Decimal("10")
    assert diagnostics.warnings == ["SELL_QUANTITY_CLAMPED_TO_AVAILABLE_HOLDING"]


def test_record_tax_budget_limit_reached_appends_event_without_duplicate_warning() -> None:
    diagnostics = empty_diagnostics()

    _record_tax_budget_limit_reached(
        instrument_id="EQ_1",
        requested_quantity=Decimal("20"),
        allowed_quantity=Decimal("7"),
        diagnostics=diagnostics,
    )
    _record_tax_budget_limit_reached(
        instrument_id="EQ_2",
        requested_quantity=Decimal("15"),
        allowed_quantity=Decimal("0"),
        diagnostics=diagnostics,
    )

    assert diagnostics.warnings == ["TAX_BUDGET_LIMIT_REACHED"]
    assert [
        (event.instrument_id, event.requested_quantity, event.allowed_quantity)
        for event in diagnostics.tax_budget_constraint_events
    ] == [
        ("EQ_1", Decimal("20"), Decimal("7")),
        ("EQ_2", Decimal("15"), Decimal("0")),
    ]


def test_trade_notional_threshold_prefers_option_before_shelf_value() -> None:
    option_threshold = Money(amount=Decimal("100"), currency="SGD")
    shelf_threshold = Money(amount=Decimal("50"), currency="SGD")

    assert (
        _trade_notional_threshold(
            options=EngineOptions(min_trade_notional=option_threshold),
            shelf_entry=shelf_entry("EQ_1").model_copy(update={"min_notional": shelf_threshold}),
        )
        == option_threshold
    )
    assert (
        _trade_notional_threshold(
            options=EngineOptions(),
            shelf_entry=shelf_entry("EQ_1").model_copy(update={"min_notional": shelf_threshold}),
        )
        == shelf_threshold
    )


def test_security_intent_constraints_include_sell_safety_and_tax_budget_labels() -> None:
    assert _security_intent_constraints(
        threshold=Money(amount=Decimal("100"), currency="SGD"),
        side="SELL",
        quantity=Decimal("5"),
        requested_quantity=Decimal("10"),
        sell_quantity_before_tax=Decimal("8"),
        tax_awareness_enabled=True,
    ) == ["MIN_NOTIONAL", "AVAILABLE_HOLDING", "TAX_BUDGET"]


def test_suppress_dust_trade_records_below_min_notional_intent() -> None:
    suppressed = []
    threshold = Money(amount=Decimal("100"), currency="SGD")

    suppressed_trade = _suppress_dust_trade(
        instrument_id="EQ_1",
        notional=Decimal("75"),
        notional_currency="SGD",
        threshold=threshold,
        options=EngineOptions(suppress_dust_trades=True),
        suppressed=suppressed,
    )

    assert suppressed_trade is True
    assert len(suppressed) == 1
    assert suppressed[0].instrument_id == "EQ_1"
    assert suppressed[0].reason == "BELOW_MIN_NOTIONAL"
    assert suppressed[0].intended_notional == Money(amount=Decimal("75"), currency="SGD")
    assert suppressed[0].threshold == threshold


def test_suppress_dust_trade_keeps_supported_notional_unsuppressed() -> None:
    suppressed = []

    suppressed_trade = _suppress_dust_trade(
        instrument_id="EQ_1",
        notional=Decimal("125"),
        notional_currency="SGD",
        threshold=Money(amount=Decimal("100"), currency="SGD"),
        options=EngineOptions(suppress_dust_trades=True),
        suppressed=suppressed,
    )

    assert suppressed_trade is False
    assert suppressed == []


def test_target_trade_delta_classifies_side_and_floor_quantity() -> None:
    buy_delta = _target_trade_delta(
        target_instrument_value=Decimal("127"),
        current_instrument_value=Decimal("100"),
        unit_value=Decimal("10"),
    )
    sell_delta = _target_trade_delta(
        target_instrument_value=Decimal("70"),
        current_instrument_value=Decimal("100"),
        unit_value=Decimal("12"),
    )

    assert buy_delta.side == "BUY"
    assert buy_delta.raw_quantity == Decimal("2")
    assert sell_delta.side == "SELL"
    assert sell_delta.raw_quantity == Decimal("2")


def test_tax_impact_from_budget_normalizes_budget_used_at_tolerance_boundary() -> None:
    tax_impact = _tax_impact_from_budget(
        tax_budget=_TaxBudgetAccumulator(
            total_realized_gain_base=Decimal("100.00000000001"),
            total_realized_loss_base=Decimal("25"),
            tax_budget_used_base=Decimal("99.99999999999"),
            tax_budget_limit_base=Decimal("100"),
        ),
        base_currency="SGD",
    )

    assert tax_impact.total_realized_gain.amount == Decimal("100.00000000001")
    assert tax_impact.total_realized_loss.amount == Decimal("25")
    assert tax_impact.budget_limit == Money(amount=Decimal("100"), currency="SGD")
    assert tax_impact.budget_used == Money(amount=Decimal("100"), currency="SGD")


def test_tax_budget_limited_sell_quantity_caps_realized_gain_to_budget() -> None:
    lot_position = Position(
        instrument_id="EQ_1",
        quantity=Decimal("10"),
        lots=[
            TaxLot(
                lot_id="LOT_GAIN",
                quantity=Decimal("10"),
                unit_cost=Money(amount=Decimal("90"), currency="SGD"),
                purchase_date="2024-01-01",
            )
        ],
    )
    tax_budget = _TaxBudgetAccumulator(
        total_realized_gain_base=Decimal("0"),
        total_realized_loss_base=Decimal("0"),
        tax_budget_used_base=Decimal("0"),
        tax_budget_limit_base=Decimal("50"),
    )

    allowed_quantity = _tax_budget_limited_sell_quantity(
        options=EngineOptions(enable_tax_awareness=True),
        position=lot_position,
        requested_qty=Decimal("10"),
        sell_price=Decimal("100"),
        price_ccy="SGD",
        base_rate=Decimal("1"),
        market_data=market_data_snapshot(),
        dq_log={"fx_missing": []},
        tax_budget=tax_budget,
    )

    assert allowed_quantity == Decimal("5")
    assert tax_budget.total_realized_gain_base == Decimal("50")
    assert tax_budget.total_realized_loss_base == Decimal("0")
    assert tax_budget.tax_budget_used_base == Decimal("50")


def test_tax_budget_lot_allowance_returns_zero_when_gain_budget_exhausted() -> None:
    allowance = _tax_budget_lot_allowance(
        remaining_quantity=Decimal("10"),
        lot_quantity=Decimal("10"),
        lot_unit_cost=Decimal("90"),
        sell_price=Decimal("100"),
        base_rate=Decimal("1"),
        tax_budget=_TaxBudgetAccumulator(
            total_realized_gain_base=Decimal("50"),
            total_realized_loss_base=Decimal("0"),
            tax_budget_used_base=Decimal("50"),
            tax_budget_limit_base=Decimal("50"),
        ),
    )

    assert allowance == _TaxBudgetLotAllowance(
        requested_quantity=Decimal("10"),
        allowed_quantity=Decimal("0"),
        realized_base=Decimal("0"),
    )


def test_apply_tax_budget_lot_allowance_records_realized_losses_without_using_budget() -> None:
    tax_budget = _TaxBudgetAccumulator(
        total_realized_gain_base=Decimal("0"),
        total_realized_loss_base=Decimal("0"),
        tax_budget_used_base=Decimal("0"),
        tax_budget_limit_base=Decimal("25"),
    )

    _apply_tax_budget_lot_allowance(
        allowance=_TaxBudgetLotAllowance(
            requested_quantity=Decimal("4"),
            allowed_quantity=Decimal("4"),
            realized_base=Decimal("-12"),
        ),
        tax_budget=tax_budget,
    )

    assert tax_budget.total_realized_gain_base == Decimal("0")
    assert tax_budget.total_realized_loss_base == Decimal("12")
    assert tax_budget.tax_budget_used_base == Decimal("0")


def test_tax_budget_limited_sell_quantity_bypasses_when_tax_awareness_disabled() -> None:
    tax_budget = _TaxBudgetAccumulator(
        total_realized_gain_base=Decimal("0"),
        total_realized_loss_base=Decimal("0"),
        tax_budget_used_base=Decimal("0"),
        tax_budget_limit_base=Decimal("0"),
    )

    allowed_quantity = _tax_budget_limited_sell_quantity(
        options=EngineOptions(enable_tax_awareness=False),
        position=None,
        requested_qty=Decimal("10"),
        sell_price=Decimal("100"),
        price_ccy="SGD",
        base_rate=Decimal("1"),
        market_data=market_data_snapshot(),
        dq_log={"fx_missing": []},
        tax_budget=tax_budget,
    )

    assert allowed_quantity == Decimal("10")
    assert tax_budget.total_realized_gain_base == Decimal("0")
    assert tax_budget.tax_budget_used_base == Decimal("0")


def test_intent_market_context_resolves_price_fx_and_position() -> None:
    portfolio = portfolio_snapshot(
        portfolio_id="pf_market_context",
        base_currency="SGD",
        positions=[position("EQ_US", "10")],
        cash_balances=[cash("SGD", "1000")],
    )
    market_data = market_data_snapshot(
        prices=[price("EQ_US", "100", "USD")],
        fx_rates=[fx("USD/SGD", "1.35")],
    )
    dq_log = {"price_missing": [], "fx_missing": []}

    context = _intent_market_context(
        instrument_id="EQ_US",
        portfolio=portfolio,
        market_data=market_data,
        dq_log=dq_log,
    )

    assert context is not None
    resolved_price, rate, resolved_position = context
    assert resolved_price.instrument_id == "EQ_US"
    assert rate == Decimal("1.35")
    assert resolved_position is not None
    assert resolved_position.instrument_id == "EQ_US"
    assert dq_log == {"price_missing": [], "fx_missing": []}


def test_intent_market_context_records_missing_price_and_fx() -> None:
    portfolio = portfolio_snapshot(
        portfolio_id="pf_market_context_missing",
        base_currency="SGD",
        positions=[],
        cash_balances=[cash("SGD", "1000")],
    )
    dq_log = {"price_missing": [], "fx_missing": []}

    assert (
        _intent_market_context(
            instrument_id="EQ_MISSING",
            portfolio=portfolio,
            market_data=market_data_snapshot(prices=[], fx_rates=[]),
            dq_log=dq_log,
        )
        is None
    )
    assert dq_log["price_missing"] == ["EQ_MISSING"]

    assert (
        _intent_market_context(
            instrument_id="EQ_US",
            portfolio=portfolio,
            market_data=market_data_snapshot(
                prices=[price("EQ_US", "100", "USD")],
                fx_rates=[],
            ),
            dq_log=dq_log,
        )
        is None
    )
    assert dq_log["fx_missing"] == ["USD/SGD"]


def test_current_instrument_value_and_unit_value_uses_price_without_position() -> None:
    current_value, unit_value = _current_instrument_value_and_unit_value(
        position=None,
        price=price("EQ_1", "10", "SGD"),
    )

    assert current_value == Decimal("0")
    assert unit_value == Decimal("10")


def test_current_instrument_value_and_unit_value_uses_quantity_and_price_without_snapshot_value():
    current_value, unit_value = _current_instrument_value_and_unit_value(
        position=Position(instrument_id="EQ_1", quantity=Decimal("7")),
        price=price("EQ_1", "10", "SGD"),
    )

    assert current_value == Decimal("70")
    assert unit_value == Decimal("10")


def test_current_instrument_value_and_unit_value_uses_trusted_market_value() -> None:
    current_value, unit_value = _current_instrument_value_and_unit_value(
        position=Position(
            instrument_id="EQ_1",
            quantity=Decimal("5"),
            market_value=Money(amount=Decimal("125"), currency="SGD"),
        ),
        price=price("EQ_1", "10", "SGD"),
    )

    assert current_value == Decimal("125")
    assert unit_value == Decimal("25")


def test_current_instrument_value_and_unit_value_keeps_price_unit_for_zero_quantity_snapshot():
    current_value, unit_value = _current_instrument_value_and_unit_value(
        position=Position(
            instrument_id="EQ_1",
            quantity=Decimal("0"),
            market_value=Money(amount=Decimal("125"), currency="SGD"),
        ),
        price=price("EQ_1", "10", "SGD"),
    )

    assert current_value == Decimal("125")
    assert unit_value == Decimal("10")


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
