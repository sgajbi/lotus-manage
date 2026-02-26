from decimal import Decimal

from src.core.dpm_engine import run_simulation
from src.core.models import (
    EngineOptions,
    Money,
)
from tests.shared.assertions import (
    assert_dq_contains,
    assert_status,
    find_excluded,
    fx_intents,
    security_intents,
)
from tests.shared.factories import (
    model_portfolio,
    position,
    price,
    shelf_entry,
    target,
)


def test_standard_buy_security(base_context):
    pf, mkt, shelf = base_context
    model = model_portfolio(targets=[target("AAPL", "0.5")])

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert_status(result, "READY")
    assert len(result.intents) == 1
    intent = result.intents[0]
    assert intent.intent_type == "SECURITY_TRADE"
    assert intent.side == "BUY"
    assert intent.instrument_id == "AAPL"
    assert intent.quantity == Decimal("333")


def test_fx_hub_and_spoke_funding(base_context):
    pf, mkt, shelf = base_context
    model = model_portfolio(targets=[target("DBS", "0.5")])

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert_status(result, "READY")
    assert len(result.intents) == 2

    fx = fx_intents(result)[0]
    sec = result.intents[1]

    assert fx.buy_currency == "SGD"
    assert fx.pair == "SGD/USD"

    assert sec.intent_type == "SECURITY_TRADE"
    assert sec.instrument_id == "DBS"
    assert fx.intent_id in sec.dependencies


def test_universe_banned_asset_exclusion(base_context):
    pf, mkt, shelf = base_context
    model = model_portfolio(targets=[target("BANNED_ASSET", "0.5")])

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert len(result.intents) == 0
    assert find_excluded(result, "BANNED_ASSET") is not None


def test_universe_sell_only_logic(base_context):
    pf, mkt, shelf = base_context
    pf.positions.append(position("SELL_ONLY_ASSET", "100"))
    mkt.prices.append(price("SELL_ONLY_ASSET", "10", "USD"))
    model = model_portfolio(targets=[])

    result = run_simulation(pf, mkt, model, shelf, EngineOptions())

    assert len(result.intents) == 1
    assert result.intents[0].instrument_id == "SELL_ONLY_ASSET"
    assert result.intents[0].side == "SELL"
    assert result.intents[0].quantity == Decimal("100")


def test_target_normalization_over_100(base_context):
    pf, mkt, shelf = base_context
    model = model_portfolio(targets=[target("AAPL", "0.8"), target("DBS", "0.8")])
    options = EngineOptions(fx_buffer_pct=Decimal("0.0"))

    result = run_simulation(pf, mkt, model, shelf, options)

    assert result.status == "PENDING_REVIEW"

    aapl_intent = next(i for i in security_intents(result) if i.instrument_id == "AAPL")
    assert aapl_intent.quantity == Decimal("333")


def test_target_single_position_cap(base_context):
    pf, mkt, shelf = base_context
    model = model_portfolio(targets=[target("AAPL", "0.5")])
    options = EngineOptions(single_position_max_weight=Decimal("0.10"))

    result = run_simulation(pf, mkt, model, shelf, options)

    intent = result.intents[0]
    assert intent.quantity == Decimal("66")
    assert result.status == "PENDING_REVIEW"


def test_missing_price_blocking(base_context):
    pf, mkt, shelf = base_context
    model = model_portfolio(targets=[target("UNKNOWN_ASSET", "0.1")])
    shelf.append(shelf_entry("UNKNOWN_ASSET", status="APPROVED", asset_class="EQUITY"))

    result = run_simulation(pf, mkt, model, shelf, EngineOptions(block_on_missing_prices=True))

    assert_status(result, "BLOCKED")
    assert_dq_contains(result, "price_missing", "UNKNOWN_ASSET")


def test_dust_suppression(base_context):
    pf, mkt, shelf = base_context
    model = model_portfolio(targets=[target("AAPL", "0.0001")])
    options = EngineOptions(
        suppress_dust_trades=True,
        min_trade_notional=Money(amount=Decimal("1000"), currency="USD"),
    )

    result = run_simulation(pf, mkt, model, shelf, options)

    assert len(result.intents) == 0
    assert len(result.diagnostics.suppressed_intents) == 1
    assert result.diagnostics.suppressed_intents[0].instrument_id == "AAPL"
