import pytest

from tests.shared.factories import (
    cash,
    fx,
    market_data_snapshot,
    portfolio_snapshot,
    price,
    shelf_entry,
)


@pytest.fixture
def base_context():
    pf = portfolio_snapshot(
        portfolio_id="pf_1",
        base_currency="USD",
        cash_balances=[cash("USD", "100000")],
    )
    mkt = market_data_snapshot(
        prices=[
            price("AAPL", "150.00", "USD"),
            price("DBS", "30.00", "SGD"),
            price("BANNED_ASSET", "10.00", "USD"),
        ],
        fx_rates=[fx("USD/SGD", "1.35")],
    )
    shelf = [
        shelf_entry("AAPL", status="APPROVED", asset_class="EQUITY"),
        shelf_entry("DBS", status="APPROVED", asset_class="EQUITY"),
        shelf_entry("BANNED_ASSET", status="BANNED", asset_class="EQUITY"),
        shelf_entry("RESTRICTED_ASSET", status="RESTRICTED", asset_class="EQUITY"),
        shelf_entry("SELL_ONLY_ASSET", status="SELL_ONLY", asset_class="EQUITY"),
    ]
    return pf, mkt, shelf
