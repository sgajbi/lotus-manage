"""
FILE: tests/engine/test_engine_valuation_service.py
"""

from decimal import Decimal

from src.core.models import (
    CashBalance,
    EngineOptions,
    MarketDataSnapshot,
    Money,
    PortfolioSnapshot,
    Position,
    PositionSummary,
    Price,
    ShelfEntry,
)
from src.core.valuation import (
    _allocation_by_attribute_metrics,
    _position_allocation_maps,
    _safe_total_value,
    _valued_position_summaries,
    _cash_value_in_base,
    build_simulated_state,
)
from tests.shared.factories import fx, market_data_snapshot


def test_cash_value_in_base_returns_base_cash_without_fx() -> None:
    dq_log: dict[str, list[str]] = {}

    value = _cash_value_in_base(
        cash=CashBalance(currency="USD", amount=Decimal("100")),
        market_data=market_data_snapshot(),
        base_ccy="USD",
        dq_log=dq_log,
    )

    assert value == Decimal("100")
    assert dq_log == {}


def test_cash_value_in_base_converts_foreign_cash_with_fx() -> None:
    value = _cash_value_in_base(
        cash=CashBalance(currency="EUR", amount=Decimal("100")),
        market_data=market_data_snapshot(fx_rates=[fx("EUR/USD", "1.2")]),
        base_ccy="USD",
    )

    assert value == Decimal("120.0")


def test_cash_value_in_base_records_missing_cash_fx_when_log_provided() -> None:
    dq_log: dict[str, list[str]] = {}

    value = _cash_value_in_base(
        cash=CashBalance(currency="EUR", amount=Decimal("100")),
        market_data=market_data_snapshot(),
        base_ccy="USD",
        dq_log=dq_log,
    )

    assert value == Decimal("0")
    assert dq_log == {"fx_missing": ["EUR/USD"]}


def test_cash_value_in_base_suppresses_missing_cash_fx_log_without_log() -> None:
    value = _cash_value_in_base(
        cash=CashBalance(currency="EUR", amount=Decimal("100")),
        market_data=market_data_snapshot(),
        base_ccy="USD",
    )

    assert value == Decimal("0")


def test_valued_position_summaries_records_missing_price_and_fx_gaps() -> None:
    portfolio = PortfolioSnapshot(
        portfolio_id="p1",
        base_currency="USD",
        positions=[
            Position(instrument_id="EUR_STOCK", quantity=Decimal("2")),
            Position(instrument_id="MISSING_PRICE", quantity=Decimal("1")),
        ],
        cash_balances=[],
    )
    market_data = MarketDataSnapshot(
        prices=[Price(instrument_id="EUR_STOCK", price=Decimal("50"), currency="EUR")]
    )
    dq_log: dict[str, list[str]] = {}

    summaries, total_value = _valued_position_summaries(
        portfolio=portfolio,
        market_data=market_data,
        options=EngineOptions(),
        dq_log=dq_log,
    )

    assert [summary.instrument_id for summary in summaries] == ["EUR_STOCK", "MISSING_PRICE"]
    assert total_value == Decimal("0")
    assert dq_log == {
        "price_missing": ["MISSING_PRICE"],
        "fx_missing": ["EUR/USD"],
    }


def test_position_allocation_maps_apply_shelf_asset_class_and_attributes() -> None:
    summaries = [
        PositionSummary(
            instrument_id="Tech_A",
            quantity=Decimal("1"),
            instrument_currency="USD",
            value_in_instrument_ccy=Money(amount=Decimal("40"), currency="USD"),
            value_in_base_ccy=Money(amount=Decimal("40"), currency="USD"),
            weight=Decimal("0"),
        ),
        PositionSummary(
            instrument_id="Bond_C",
            quantity=Decimal("1"),
            instrument_currency="USD",
            value_in_instrument_ccy=Money(amount=Decimal("60"), currency="USD"),
            value_in_base_ccy=Money(amount=Decimal("60"), currency="USD"),
            weight=Decimal("0"),
        ),
    ]
    shelf = [
        ShelfEntry(
            instrument_id="Tech_A",
            status="APPROVED",
            asset_class="EQUITY",
            attributes={"sector": "TECH"},
        ),
        ShelfEntry(
            instrument_id="Bond_C",
            status="APPROVED",
            asset_class="FIXED_INCOME",
            attributes={"sector": "FI"},
        ),
    ]

    by_asset_class, by_attribute = _position_allocation_maps(
        position_summaries=summaries,
        shelf=shelf,
    )
    metrics = _allocation_by_attribute_metrics(
        allocation_by_attribute=by_attribute,
        total_value=Decimal("100"),
        base_ccy="USD",
    )

    assert by_asset_class == {
        "EQUITY": Decimal("40"),
        "FIXED_INCOME": Decimal("60"),
    }
    assert summaries[0].asset_class == "EQUITY"
    assert metrics["sector"][0].key == "TECH"
    assert metrics["sector"][0].weight == Decimal("0.4")
    assert metrics["sector"][1].key == "FI"
    assert metrics["sector"][1].weight == Decimal("0.6")
    assert _safe_total_value(Decimal("0")) == Decimal("1")


def test_valuation_service_aggregates_attributes():
    """
    Verify that build_simulated_state correctly aggregates value by attributes (RFC-0008).
    Scenario:
      - Tech_A: $40, sector=TECH
      - Tech_B: $60, sector=TECH
      - Bond_C: $100, sector=FI
      - Total: $200
    Expectation:
      - sector:TECH = 50%
      - sector:FI = 50%
    """
    pf = PortfolioSnapshot(
        portfolio_id="p1",
        base_currency="USD",
        positions=[
            Position(instrument_id="Tech_A", quantity=Decimal("1")),
            Position(instrument_id="Tech_B", quantity=Decimal("1")),
            Position(instrument_id="Bond_C", quantity=Decimal("1")),
        ],
        cash_balances=[CashBalance(currency="USD", amount=Decimal("0"))],
    )

    md = MarketDataSnapshot(
        prices=[
            Price(instrument_id="Tech_A", price=Decimal("40"), currency="USD"),
            Price(instrument_id="Tech_B", price=Decimal("60"), currency="USD"),
            Price(instrument_id="Bond_C", price=Decimal("100"), currency="USD"),
        ]
    )

    shelf = [
        ShelfEntry(instrument_id="Tech_A", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="Tech_B", status="APPROVED", attributes={"sector": "TECH"}),
        ShelfEntry(instrument_id="Bond_C", status="APPROVED", attributes={"sector": "FI"}),
    ]

    state = build_simulated_state(
        portfolio=pf,
        market_data=md,
        shelf=shelf,
        dq_log={},
        warnings=[],
        options=EngineOptions(),
    )

    # Check Total Value
    assert state.total_value.amount == Decimal("200")

    # Check Attribute Aggregation
    assert "sector" in state.allocation_by_attribute
    sectors = state.allocation_by_attribute["sector"]

    tech_metric = next((m for m in sectors if m.key == "TECH"), None)
    fi_metric = next((m for m in sectors if m.key == "FI"), None)

    assert tech_metric is not None
    assert tech_metric.value.amount == Decimal("100")  # 40 + 60
    assert tech_metric.weight == Decimal("0.5")  # 100 / 200

    assert fi_metric is not None
    assert fi_metric.value.amount == Decimal("100")
    assert fi_metric.weight == Decimal("0.5")


def test_valuation_handles_missing_attributes():
    """
    Instruments without attributes should just be skipped in the attribute map,
    not cause errors.
    """
    pf = PortfolioSnapshot(
        portfolio_id="p1",
        base_currency="USD",
        positions=[Position(instrument_id="A", quantity=Decimal("10"))],
        cash_balances=[],
    )
    md = MarketDataSnapshot(prices=[Price(instrument_id="A", price=Decimal("1"), currency="USD")])
    shelf = [ShelfEntry(instrument_id="A", status="APPROVED")]  # No attributes

    state = build_simulated_state(pf, md, shelf, {}, [])

    assert state.total_value.amount == Decimal("10")
    assert state.allocation_by_attribute == {}
