import pytest

from src.core.dpm_engine import run_simulation
from src.core.models import EngineOptions
from tests.shared.assertions import find_excluded
from tests.shared.factories import (
    cash,
    market_data_snapshot,
    model_portfolio,
    portfolio_snapshot,
    position,
    price,
    shelf_entry,
    target,
)


@pytest.mark.parametrize(
    "status, expected_reason",
    [
        ("BANNED", "SHELF_STATUS_BANNED"),
        ("SUSPENDED", "SHELF_STATUS_SUSPENDED"),
        ("RESTRICTED", "SHELF_STATUS_RESTRICTED"),
        ("SELL_ONLY", "SHELF_STATUS_SELL_ONLY"),
    ],
)
def test_model_target_status_exclusion_matrix(status, expected_reason):
    pf = portfolio_snapshot(
        portfolio_id=f"pf_model_{status.lower()}",
        base_currency="USD",
        cash_balances=[cash("USD", "1000")],
    )
    mkt = market_data_snapshot(prices=[price("ASSET_X", "100", "USD")], fx_rates=[])
    model = model_portfolio(targets=[target("ASSET_X", "1.0")])
    shelf = [shelf_entry("ASSET_X", status=status)]

    result = run_simulation(pf, mkt, model, shelf, EngineOptions(allow_restricted=False))

    excluded = find_excluded(result, "ASSET_X")
    assert excluded is not None
    assert expected_reason in excluded.reason_code


@pytest.mark.parametrize(
    "status, expected_reason",
    [
        ("BANNED", "LOCKED_DUE_TO_BANNED"),
        ("SUSPENDED", "LOCKED_DUE_TO_SUSPENDED"),
        ("RESTRICTED", "LOCKED_DUE_TO_RESTRICTED"),
    ],
)
def test_held_position_lock_reason_matrix(status, expected_reason):
    pf = portfolio_snapshot(
        portfolio_id=f"pf_held_{status.lower()}",
        base_currency="USD",
        positions=[position("HELD_X", "10")],
        cash_balances=[cash("USD", "0")],
    )
    mkt = market_data_snapshot(prices=[price("HELD_X", "100", "USD")], fx_rates=[])
    model = model_portfolio(targets=[])
    shelf = [shelf_entry("HELD_X", status=status)]

    result = run_simulation(pf, mkt, model, shelf, EngineOptions(allow_restricted=False))

    excluded = find_excluded(result, "HELD_X")
    assert excluded is not None
    assert expected_reason in excluded.reason_code
