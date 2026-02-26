import pytest

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


@pytest.fixture
def base_inputs():
    pf = portfolio_snapshot(
        portfolio_id="gap_fill",
        base_currency="USD",
        positions=[position("LOCKED_ASSET", "100")],
        cash_balances=[cash("JPY", "1000")],
    )
    mkt = market_data_snapshot(
        prices=[
            price("LOCKED_ASSET", "10", "USD"),
            price("TARGET_ASSET", "10", "USD"),
        ],
        fx_rates=[fx("JPY/USD", "0.01")],
    )
    shelf = [
        shelf_entry("LOCKED_ASSET", status="RESTRICTED"),
        shelf_entry("TARGET_ASSET", status="APPROVED"),
    ]
    model = model_portfolio(targets=[target("TARGET_ASSET", "0.5")])
    return pf, mkt, model, shelf
