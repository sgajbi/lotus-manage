from collections.abc import Mapping, Sequence
from typing import TypeAlias

from src.core.models import FxSpotIntent, SecurityTradeIntent

RebalanceIntent: TypeAlias = SecurityTradeIntent | FxSpotIntent


def link_buy_intent_dependencies(
    intents: Sequence[RebalanceIntent],
    *,
    fx_intent_id_by_currency: Mapping[str, str] | None = None,
    include_same_currency_sell_dependency: bool = False,
) -> None:
    """Attach deterministic dependencies to BUY security intents in-place."""
    fx_dependencies = dict(fx_intent_id_by_currency or {})
    sell_dependencies = (
        sell_intent_id_by_currency(intents) if include_same_currency_sell_dependency else {}
    )

    for intent in intents:
        if intent.intent_type != "SECURITY_TRADE" or intent.side != "BUY":
            continue

        if intent.notional is None:
            continue
        currency = intent.notional.currency
        fx_dependency = fx_dependencies.get(currency)
        append_intent_dependency_once(intent, fx_dependency)

        if not include_same_currency_sell_dependency:
            continue

        append_intent_dependency_once(intent, sell_dependencies.get(currency))


def sell_intent_id_by_currency(intents: Sequence[RebalanceIntent]) -> dict[str, str]:
    """Return the latest sell intent id by notional currency."""
    dependencies: dict[str, str] = {}
    for intent in intents:
        if intent.intent_type != "SECURITY_TRADE" or intent.side != "SELL":
            continue
        if intent.notional is None:
            continue
        dependencies[intent.notional.currency] = intent.intent_id
    return dependencies


def append_intent_dependency_once(
    intent: SecurityTradeIntent | FxSpotIntent,
    dependency_id: str | None,
) -> None:
    if dependency_id is None:
        return
    if dependency_id in intent.dependencies:
        return
    intent.dependencies.append(dependency_id)
