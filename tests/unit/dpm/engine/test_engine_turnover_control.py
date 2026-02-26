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


def _turnover_context():
    portfolio = portfolio_snapshot(
        portfolio_id="pf_turnover",
        base_currency="USD",
        cash_balances=[cash("USD", "100000")],
    )
    market = market_data_snapshot(
        prices=[
            price("A", "100", "USD"),
            price("B", "100", "USD"),
            price("C", "100", "USD"),
        ],
        fx_rates=[],
    )
    shelf = [
        shelf_entry("A", status="APPROVED", asset_class="EQUITY"),
        shelf_entry("B", status="APPROVED", asset_class="EQUITY"),
        shelf_entry("C", status="APPROVED", asset_class="EQUITY"),
    ]
    return portfolio, market, shelf


def test_turnover_cap_selects_by_score_with_skip_and_continue():
    pf, mkt, shelf = _turnover_context()
    model = model_portfolio(targets=[target("A", "0.10"), target("B", "0.10"), target("C", "0.02")])
    options = EngineOptions(max_turnover_pct=Decimal("0.15"))

    result = run_simulation(pf, mkt, model, shelf, options)

    assert_status(result, "READY")
    sec = security_intents(result)
    assert [i.instrument_id for i in sec] == ["A", "C"]
    assert "PARTIAL_REBALANCE_TURNOVER_LIMIT" in result.diagnostics.warnings
    assert len(result.diagnostics.dropped_intents) == 1
    dropped = result.diagnostics.dropped_intents[0]
    assert dropped.instrument_id == "B"
    assert dropped.reason == "TURNOVER_LIMIT"
    assert dropped.potential_notional.amount == Decimal("10000")
    assert dropped.score == Decimal("0.1")


def test_turnover_cap_uses_exact_fit_when_available():
    pf, mkt, shelf = _turnover_context()
    model = model_portfolio(targets=[target("A", "0.10"), target("B", "0.09"), target("C", "0.05")])
    options = EngineOptions(max_turnover_pct=Decimal("0.15"))

    result = run_simulation(pf, mkt, model, shelf, options)

    sec = security_intents(result)
    assert [i.instrument_id for i in sec] == ["A", "C"]
    assert sum(i.notional_base.amount for i in sec) == Decimal("15000")
    assert result.diagnostics.dropped_intents[0].instrument_id == "B"


def test_turnover_cap_unset_keeps_existing_behavior():
    pf, mkt, shelf = _turnover_context()
    model = model_portfolio(targets=[target("A", "0.10"), target("B", "0.10"), target("C", "0.02")])

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert [i.instrument_id for i in security_intents(result)] == ["A", "B", "C"]
    assert result.diagnostics.dropped_intents == []
    assert "PARTIAL_REBALANCE_TURNOVER_LIMIT" not in result.diagnostics.warnings


def test_turnover_cap_zero_drops_all_security_intents():
    pf, mkt, shelf = _turnover_context()
    model = model_portfolio(targets=[target("A", "0.10"), target("B", "0.10"), target("C", "0.02")])
    options = EngineOptions(max_turnover_pct=Decimal("0"))

    result = run_simulation(pf, mkt, model, shelf, options)

    assert_status(result, "READY")
    assert security_intents(result) == []
    assert [d.instrument_id for d in result.diagnostics.dropped_intents] == ["A", "B", "C"]
    assert result.diagnostics.warnings.count("PARTIAL_REBALANCE_TURNOVER_LIMIT") == 1


def test_turnover_cap_tie_break_is_instrument_id_ascending():
    pf, mkt, shelf = _turnover_context()
    model = model_portfolio(targets=[target("A", "0.10"), target("B", "0.10"), target("C", "0.05")])
    options = EngineOptions(max_turnover_pct=Decimal("0.15"))

    result = run_simulation(pf, mkt, model, shelf, options)

    assert [i.instrument_id for i in security_intents(result)] == ["A", "C"]
    assert [d.instrument_id for d in result.diagnostics.dropped_intents] == ["B"]
