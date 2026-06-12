from decimal import Decimal

from src.core.common.intent_dependencies import (
    append_intent_dependency_once,
    buy_intent_dependency_ids,
    buy_security_intents_with_notional,
    link_buy_intent_dependencies,
    sell_intent_id_by_currency,
    sell_security_intents_with_notional,
)
from src.core.models import FxSpotIntent, Money, SecurityTradeIntent


def _security_intent(
    *,
    intent_id: str,
    side: str,
    currency: str | None = "USD",
) -> SecurityTradeIntent:
    return SecurityTradeIntent(
        intent_id=intent_id,
        instrument_id=f"EQ_{intent_id}",
        side=side,
        quantity=Decimal("1"),
        notional=(Money(amount=Decimal("10"), currency=currency) if currency is not None else None),
    )


def _fx_intent() -> FxSpotIntent:
    return FxSpotIntent(
        intent_id="fx_usd_sgd",
        pair="USD/SGD",
        buy_currency="USD",
        buy_amount=Decimal("10"),
        sell_currency="SGD",
        sell_amount_estimated=Decimal("13"),
    )


def test_sell_intent_id_by_currency_indexes_latest_sell_with_notional() -> None:
    assert sell_intent_id_by_currency(
        [
            _security_intent(intent_id="sell_usd_1", side="SELL", currency="USD"),
            _security_intent(intent_id="buy_usd", side="BUY", currency="USD"),
            _security_intent(intent_id="sell_missing_notional", side="SELL", currency=None),
            _security_intent(intent_id="sell_usd_2", side="SELL", currency="USD"),
            _security_intent(intent_id="sell_sgd", side="SELL", currency="SGD"),
        ]
    ) == {
        "USD": "sell_usd_2",
        "SGD": "sell_sgd",
    }


def test_security_intent_selectors_require_side_and_notional() -> None:
    buy = _security_intent(intent_id="buy_usd", side="BUY", currency="USD")
    sell = _security_intent(intent_id="sell_usd", side="SELL", currency="USD")
    buy_missing_notional = _security_intent(
        intent_id="buy_missing_notional",
        side="BUY",
        currency=None,
    )

    intents = [sell, buy_missing_notional, _fx_intent(), buy]

    assert buy_security_intents_with_notional(intents) == [buy]
    assert sell_security_intents_with_notional(intents) == [sell]


def test_buy_intent_dependency_ids_preserves_fx_then_optional_sell_order() -> None:
    buy = _security_intent(intent_id="buy_usd", side="BUY", currency="USD")

    assert buy_intent_dependency_ids(
        buy,
        fx_dependencies={"USD": "fx_usd"},
        sell_dependencies={"USD": "sell_usd"},
        include_same_currency_sell_dependency=True,
    ) == ["fx_usd", "sell_usd"]
    assert buy_intent_dependency_ids(
        buy,
        fx_dependencies={"USD": "fx_usd"},
        sell_dependencies={"USD": "sell_usd"},
        include_same_currency_sell_dependency=False,
    ) == ["fx_usd"]


def test_append_intent_dependency_once_preserves_existing_order() -> None:
    intent = _security_intent(intent_id="buy_usd", side="BUY")
    intent.dependencies.append("existing")

    append_intent_dependency_once(intent, "fx_usd")
    append_intent_dependency_once(intent, "fx_usd")
    append_intent_dependency_once(intent, None)

    assert intent.dependencies == ["existing", "fx_usd"]


def test_link_buy_intent_dependencies_uses_fx_then_sell_dependencies() -> None:
    sell = _security_intent(intent_id="sell_usd", side="SELL", currency="USD")
    buy = _security_intent(intent_id="buy_usd", side="BUY", currency="USD")

    link_buy_intent_dependencies(
        [sell, buy],
        fx_intent_id_by_currency={"USD": "fx_usd"},
        include_same_currency_sell_dependency=True,
    )

    assert buy.dependencies == ["fx_usd", "sell_usd"]
