from decimal import Decimal

from src.core.common.intent_dependencies import (
    append_intent_dependency_once,
    link_buy_intent_dependencies,
    sell_intent_id_by_currency,
)
from src.core.models import Money, SecurityTradeIntent


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
