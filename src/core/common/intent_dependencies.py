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

    for intent in buy_security_intents_with_notional(intents):
        for dependency_id in buy_intent_dependency_ids(
            intent,
            fx_dependencies=fx_dependencies,
            sell_dependencies=sell_dependencies,
            include_same_currency_sell_dependency=include_same_currency_sell_dependency,
        ):
            append_intent_dependency_once(intent, dependency_id)


def sell_intent_id_by_currency(intents: Sequence[RebalanceIntent]) -> dict[str, str]:
    """Return the latest sell intent id by notional currency."""
    return {
        intent.notional.currency: intent.intent_id
        for intent in sell_security_intents_with_notional(intents)
        if intent.notional is not None
    }


def buy_security_intents_with_notional(
    intents: Sequence[RebalanceIntent],
) -> list[SecurityTradeIntent]:
    return [
        intent
        for intent in intents
        if isinstance(intent, SecurityTradeIntent)
        and intent.side == "BUY"
        and intent.notional is not None
    ]


def sell_security_intents_with_notional(
    intents: Sequence[RebalanceIntent],
) -> list[SecurityTradeIntent]:
    return [
        intent
        for intent in intents
        if isinstance(intent, SecurityTradeIntent)
        and intent.side == "SELL"
        and intent.notional is not None
    ]


def buy_intent_dependency_ids(
    intent: SecurityTradeIntent,
    *,
    fx_dependencies: Mapping[str, str],
    sell_dependencies: Mapping[str, str],
    include_same_currency_sell_dependency: bool,
) -> list[str | None]:
    if intent.notional is None:
        return []
    currency = intent.notional.currency
    dependency_ids = [fx_dependencies.get(currency)]
    if include_same_currency_sell_dependency:
        dependency_ids.append(sell_dependencies.get(currency))
    return dependency_ids


def append_intent_dependency_once(
    intent: SecurityTradeIntent | FxSpotIntent,
    dependency_id: str | None,
) -> None:
    if dependency_id is None:
        return
    if dependency_id in intent.dependencies:
        return
    intent.dependencies.append(dependency_id)
