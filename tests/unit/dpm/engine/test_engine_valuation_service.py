"""
FILE: tests/engine/test_engine_valuation_service.py
"""

from decimal import Decimal

from src.core.models import (
    CashBalance,
    EngineOptions,
    MarketDataSnapshot,
    PortfolioSnapshot,
    Position,
    Price,
    ShelfEntry,
)
from src.core.valuation import build_simulated_state


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
