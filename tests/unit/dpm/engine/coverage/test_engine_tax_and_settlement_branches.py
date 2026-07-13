from decimal import Decimal

from src.core.rebalance.engine import (
    _apply_turnover_limit,
    _calculate_turnover_score,
    run_simulation,
)
from src.core.rebalance import turnover as turnover_module
from src.core.models import DiagnosticsData, EngineOptions, Money, SecurityTradeIntent
from tests.shared.assertions import assert_status, security_intents
from tests.shared.factories import (
    cash,
    fx,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    price,
    shelf_entry,
    target,
)


def _diag():
    return DiagnosticsData(
        warnings=[],
        suppressed_intents=[],
        data_quality={"price_missing": [], "fx_missing": [], "shelf_missing": []},
    )


def _security_intent(
    *,
    intent_id: str,
    instrument_id: str,
    notional_base: Decimal | None,
) -> SecurityTradeIntent:
    return SecurityTradeIntent(
        intent_id=intent_id,
        instrument_id=instrument_id,
        side="BUY",
        quantity=Decimal("1"),
        notional=Money(amount=Decimal("100"), currency="USD"),
        notional_base=(
            Money(amount=notional_base, currency="USD") if notional_base is not None else None
        ),
    )


def test_calculate_turnover_score_returns_zero_when_portfolio_value_non_positive():
    intent = SecurityTradeIntent(
        intent_id="oi_1",
        instrument_id="A",
        side="BUY",
        quantity=Decimal("1"),
        notional=Money(amount=Decimal("100"), currency="USD"),
        notional_base=Money(amount=Decimal("100"), currency="USD"),
    )
    assert _calculate_turnover_score(intent, Decimal("0")) == Decimal("0")


def test_calculate_turnover_score_returns_zero_when_notional_base_missing():
    intent = SecurityTradeIntent(
        intent_id="oi_1b",
        instrument_id="A",
        side="BUY",
        quantity=Decimal("1"),
        notional=Money(amount=Decimal("100"), currency="USD"),
        notional_base=None,
    )
    assert _calculate_turnover_score(intent, Decimal("1000")) == Decimal("0")


def test_turnover_helper_calculates_budget_proposed_and_rank_key():
    high_score = _security_intent(
        intent_id="oi_high",
        instrument_id="B",
        notional_base=Decimal("200"),
    )
    low_notional = _security_intent(
        intent_id="oi_low",
        instrument_id="A",
        notional_base=Decimal("100"),
    )
    missing_notional = _security_intent(
        intent_id="oi_missing",
        instrument_id="C",
        notional_base=None,
    )

    assert turnover_module._turnover_budget(
        portfolio_value_base=Decimal("1000"),
        max_turnover_pct=Decimal("0.15"),
    ) == Decimal("150.00")
    assert turnover_module._proposed_turnover(
        [high_score, low_notional, missing_notional]
    ) == Decimal("300")
    assert sorted(
        [low_notional, high_score, missing_notional],
        key=lambda intent: turnover_module._turnover_rank_key(
            intent=intent,
            portfolio_value_base=Decimal("1000"),
        ),
    ) == [high_score, low_notional, missing_notional]


def test_turnover_budget_selection_is_pure_and_records_dropped_intents():
    high_score = _security_intent(
        intent_id="oi_high",
        instrument_id="B",
        notional_base=Decimal("200"),
    )
    exact_fit = _security_intent(
        intent_id="oi_fit",
        instrument_id="A",
        notional_base=Decimal("100"),
    )
    over_budget = _security_intent(
        intent_id="oi_drop",
        instrument_id="C",
        notional_base=Decimal("100"),
    )
    missing_notional = _security_intent(
        intent_id="oi_missing",
        instrument_id="D",
        notional_base=None,
    )

    selection = turnover_module._select_turnover_budget_intents(
        intents=[exact_fit, missing_notional, high_score, over_budget],
        budget=Decimal("300"),
        portfolio_value_base=Decimal("1000"),
        base_currency="USD",
    )

    assert [intent.instrument_id for intent in selection.selected] == ["B", "A"]
    assert [item.instrument_id for item in selection.dropped] == ["C"]
    assert selection.dropped[0].potential_notional == Money(amount=Decimal("100"), currency="USD")


def test_turnover_drop_helper_records_governed_diagnostic_payload():
    intent = _security_intent(
        intent_id="oi_drop",
        instrument_id="B",
        notional_base=Decimal("-125"),
    )

    dropped = turnover_module._dropped_turnover_intent(
        intent=intent,
        notional_abs=Decimal("125"),
        portfolio_value_base=Decimal("1000"),
        base_currency="USD",
    )

    assert dropped.instrument_id == "B"
    assert dropped.reason == "TURNOVER_LIMIT"
    assert dropped.potential_notional == Money(amount=Decimal("125"), currency="USD")
    assert dropped.score == Decimal("0.125")


def test_apply_turnover_limit_keeps_all_intents_when_within_budget():
    intents = [
        SecurityTradeIntent(
            intent_id="oi_1",
            instrument_id="A",
            side="BUY",
            quantity=Decimal("1"),
            notional=Money(amount=Decimal("100"), currency="USD"),
            notional_base=Money(amount=Decimal("100"), currency="USD"),
        ),
        SecurityTradeIntent(
            intent_id="oi_2",
            instrument_id="B",
            side="BUY",
            quantity=Decimal("1"),
            notional=Money(amount=Decimal("100"), currency="USD"),
            notional_base=Money(amount=Decimal("100"), currency="USD"),
        ),
    ]
    diagnostics = _diag()
    selected = _apply_turnover_limit(
        intents=intents,
        options=EngineOptions(max_turnover_pct=Decimal("0.5")),
        portfolio_value_base=Decimal("1000"),
        base_currency="USD",
        diagnostics=diagnostics,
    )
    assert selected == intents
    assert diagnostics.dropped_intents == []


def test_apply_turnover_limit_skips_intent_without_notional_base():
    intents = [
        SecurityTradeIntent(
            intent_id="oi_no_base",
            instrument_id="A",
            side="BUY",
            quantity=Decimal("1"),
            notional=Money(amount=Decimal("100"), currency="USD"),
            notional_base=None,
        ),
        SecurityTradeIntent(
            intent_id="oi_with_base",
            instrument_id="B",
            side="BUY",
            quantity=Decimal("1"),
            notional=Money(amount=Decimal("100"), currency="USD"),
            notional_base=Money(amount=Decimal("100"), currency="USD"),
        ),
    ]
    diagnostics = _diag()
    selected = _apply_turnover_limit(
        intents=intents,
        options=EngineOptions(max_turnover_pct=Decimal("0.05")),
        portfolio_value_base=Decimal("1000"),
        base_currency="USD",
        diagnostics=diagnostics,
    )

    assert selected == []
    assert [item.instrument_id for item in diagnostics.dropped_intents] == ["B"]


def test_tax_awareness_with_missing_lots_blocks_ready_sell_path():
    pf = portfolio_snapshot(
        portfolio_id="pf_tax_no_lots",
        base_currency="USD",
        positions=[{"instrument_id": "ABC", "quantity": Decimal("100")}],
        cash_balances=[cash("USD", "0")],
    )
    mkt = market_data_snapshot(prices=[price("ABC", "100", "USD")], fx_rates=[])
    shelf = [shelf_entry("ABC", status="APPROVED")]
    model = model_portfolio(targets=[target("ABC", "0.0")])

    result = run_simulation(
        pf,
        mkt,
        model,
        shelf,
        EngineOptions(enable_tax_awareness=True, max_realized_capital_gains=Decimal("1")),
    )

    assert_status(result, "BLOCKED")
    assert security_intents(result) == []
    assert result.tax_impact is None
    assert result.diagnostics.data_quality["tax_lot_evidence_incomplete"] == [
        "ABC:TAX_LOTS_MISSING"
    ]
    assert "TAX_LOTS_MISSING" in result.diagnostics.warnings
    assert "TAX_BUDGET_LIMIT_REACHED" not in result.diagnostics.warnings


def test_tax_awareness_disabled_allows_sell_without_lot_evidence():
    pf = portfolio_snapshot(
        portfolio_id="pf_tax_disabled_no_lots",
        base_currency="USD",
        positions=[{"instrument_id": "ABC", "quantity": Decimal("100")}],
        cash_balances=[cash("USD", "0")],
    )
    mkt = market_data_snapshot(prices=[price("ABC", "100", "USD")], fx_rates=[])
    shelf = [shelf_entry("ABC", status="APPROVED")]
    model = model_portfolio(targets=[target("ABC", "0.0")])

    result = run_simulation(
        pf,
        mkt,
        model,
        shelf,
        EngineOptions(enable_tax_awareness=False, max_realized_capital_gains=Decimal("1")),
    )

    assert_status(result, "READY")
    assert security_intents(result)[0].quantity == Decimal("100")
    assert "tax_lot_evidence_incomplete" not in result.diagnostics.data_quality


def test_tax_awareness_blocks_when_lot_cost_fx_missing():
    pf = portfolio_snapshot(
        portfolio_id="pf_tax_missing_fx",
        base_currency="USD",
        positions=[
            {
                "instrument_id": "ABC",
                "quantity": Decimal("100"),
                "lots": [
                    {
                        "lot_id": "L1",
                        "quantity": Decimal("100"),
                        "unit_cost": {"amount": Decimal("90"), "currency": "EUR"},
                        "purchase_date": "2025-01-01",
                    }
                ],
            }
        ],
        cash_balances=[cash("USD", "0")],
    )
    mkt = market_data_snapshot(prices=[price("ABC", "100", "USD")], fx_rates=[])
    shelf = [shelf_entry("ABC", status="APPROVED")]
    model = model_portfolio(targets=[target("ABC", "0.0")])

    result = run_simulation(
        pf,
        mkt,
        model,
        shelf,
        EngineOptions(
            enable_tax_awareness=True,
            max_realized_capital_gains=Decimal("10"),
            block_on_missing_fx=False,
        ),
    )

    assert_status(result, "BLOCKED")
    assert security_intents(result) == []
    assert "EUR/USD" in result.diagnostics.data_quality["fx_missing"]
    assert result.diagnostics.data_quality["tax_lot_evidence_incomplete"] == [
        "ABC:TAX_LOT_COST_FX_MISSING"
    ]
    assert "TAX_LOT_COST_FX_MISSING" in result.diagnostics.warnings
    assert "TAX_BUDGET_LIMIT_REACHED" not in result.diagnostics.warnings


def test_tax_awareness_budget_exhaustion_stops_next_gain_lot():
    pf = portfolio_snapshot(
        portfolio_id="pf_tax_budget_exhaust",
        base_currency="USD",
        positions=[
            {
                "instrument_id": "ABC",
                "quantity": Decimal("60"),
                "lots": [
                    {
                        "lot_id": "L0",
                        "quantity": Decimal("0"),
                        "unit_cost": {"amount": Decimal("200"), "currency": "USD"},
                        "purchase_date": "2026-01-01",
                    },
                    {
                        "lot_id": "L1",
                        "quantity": Decimal("10"),
                        "unit_cost": {"amount": Decimal("90"), "currency": "USD"},
                        "purchase_date": "2025-01-01",
                    },
                    {
                        "lot_id": "L2",
                        "quantity": Decimal("50"),
                        "unit_cost": {"amount": Decimal("80"), "currency": "USD"},
                        "purchase_date": "2024-01-01",
                    },
                ],
            }
        ],
        cash_balances=[cash("USD", "0")],
    )
    mkt = market_data_snapshot(prices=[price("ABC", "100", "USD")], fx_rates=[])
    shelf = [shelf_entry("ABC", status="APPROVED")]
    model = model_portfolio(targets=[target("ABC", "0.5")])

    result = run_simulation(
        pf,
        mkt,
        model,
        shelf,
        EngineOptions(enable_tax_awareness=True, max_realized_capital_gains=Decimal("100")),
    )

    assert_status(result, "READY")
    assert security_intents(result)[0].quantity == Decimal("10")
    assert "TAX_BUDGET_LIMIT_REACHED" in result.diagnostics.warnings


def test_tax_awareness_converts_lot_cost_currency_with_available_fx():
    pf = portfolio_snapshot(
        portfolio_id="pf_tax_cost_fx",
        base_currency="USD",
        positions=[
            {
                "instrument_id": "ABC",
                "quantity": Decimal("20"),
                "lots": [
                    {
                        "lot_id": "L1",
                        "quantity": Decimal("20"),
                        "unit_cost": {"amount": Decimal("80"), "currency": "EUR"},
                        "purchase_date": "2024-01-01",
                    }
                ],
            }
        ],
        cash_balances=[cash("USD", "0")],
    )
    mkt = market_data_snapshot(
        prices=[price("ABC", "100", "USD")],
        fx_rates=[fx("EUR/USD", "1.1")],
    )
    shelf = [shelf_entry("ABC", status="APPROVED")]
    model = model_portfolio(targets=[target("ABC", "0.0")])

    result = run_simulation(
        pf,
        mkt,
        model,
        shelf,
        EngineOptions(enable_tax_awareness=True, max_realized_capital_gains=Decimal("500")),
    )

    assert_status(result, "READY")
    assert security_intents(result)[0].quantity == Decimal("20")
    assert result.tax_impact is not None
    assert result.tax_impact.total_realized_gain.amount == Decimal("240")


def test_tax_awareness_allows_loss_lots_even_with_zero_budget():
    pf = portfolio_snapshot(
        portfolio_id="pf_tax_loss",
        base_currency="USD",
        positions=[
            {
                "instrument_id": "ABC",
                "quantity": Decimal("20"),
                "lots": [
                    {
                        "lot_id": "L1",
                        "quantity": Decimal("20"),
                        "unit_cost": {"amount": Decimal("120"), "currency": "USD"},
                        "purchase_date": "2024-01-01",
                    }
                ],
            }
        ],
        cash_balances=[cash("USD", "0")],
    )
    mkt = market_data_snapshot(prices=[price("ABC", "100", "USD")], fx_rates=[])
    shelf = [shelf_entry("ABC", status="APPROVED")]
    model = model_portfolio(targets=[target("ABC", "0.0")])

    result = run_simulation(
        pf,
        mkt,
        model,
        shelf,
        EngineOptions(enable_tax_awareness=True, max_realized_capital_gains=Decimal("0")),
    )

    assert_status(result, "READY")
    assert security_intents(result)[0].quantity == Decimal("20")
    assert result.tax_impact is not None
    assert result.tax_impact.total_realized_loss.amount > Decimal("0")


def test_settlement_ladder_records_fx_cash_flows():
    pf = portfolio_snapshot(
        portfolio_id="pf_settle_fx_branch",
        base_currency="SGD",
        positions=[{"instrument_id": "US_TECH", "quantity": Decimal("100")}],
        cash_balances=[cash("SGD", "0"), cash("USD", "0"), cash("EUR", "0")],
    )
    mkt = market_data_snapshot(
        prices=[price("US_TECH", "100", "USD"), price("EU_BOND", "100", "EUR")],
        fx_rates=[fx("USD/SGD", "1.5"), fx("EUR/SGD", "1.6")],
    )
    shelf = [shelf_entry("US_TECH", status="APPROVED"), shelf_entry("EU_BOND", status="APPROVED")]
    model = model_portfolio(targets=[target("EU_BOND", "1.0"), target("US_TECH", "0.0")])

    result = run_simulation(
        pf,
        mkt,
        model,
        shelf,
        EngineOptions(
            enable_settlement_awareness=True,
            fx_buffer_pct=Decimal("0"),
            max_overdraft_by_ccy={
                "SGD": Decimal("1000000"),
                "USD": Decimal("1000000"),
                "EUR": Decimal("1000000"),
            },
        ),
    )

    assert_status(result, "READY")
    ladder_ccys = {p.currency for p in result.diagnostics.cash_ladder}
    assert {"SGD", "USD", "EUR"}.issubset(ladder_ccys)
