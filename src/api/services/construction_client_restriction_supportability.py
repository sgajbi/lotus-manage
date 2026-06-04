from src.api.request_models import RebalanceRequest
from src.core.construction.models import (
    AuthoritativeClientRestrictionContext,
    AuthoritativeClientRestrictionRule,
)
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import RebalanceResult, SecurityTradeIntent, ShelfEntry


def client_restriction_status(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    context: AuthoritativeClientRestrictionContext | None,
) -> ConstructionMethodStatus:
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    if violated_client_restrictions(request=request, result=result, context=context):
        return ConstructionMethodStatus.BLOCKED
    return context.supportability_status


def client_restriction_reason_codes(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    context: AuthoritativeClientRestrictionContext | None,
) -> list[str]:
    if context is None:
        return ["CLIENT_RESTRICTION_PROFILE_UNAVAILABLE"]
    reason_codes = list(context.reason_codes)
    if context.supportability_status != ConstructionMethodStatus.READY:
        reason_codes.append(f"CLIENT_RESTRICTION_PROFILE_{context.supportability_status}")
    reason_codes.extend(f"MISSING_{family.upper()}" for family in context.missing_data_families)
    violations = violated_client_restrictions(request=request, result=result, context=context)
    if violations:
        reason_codes.extend(
            f"CLIENT_RESTRICTION_VIOLATION_{restriction.restriction_code}"
            for _, restriction in violations
        )
    else:
        reason_codes.append("CLIENT_RESTRICTION_PROFILE_APPLIED")
    return sorted(set(reason_codes))


def violated_client_restrictions(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    context: AuthoritativeClientRestrictionContext,
) -> list[tuple[SecurityTradeIntent, AuthoritativeClientRestrictionRule]]:
    shelf_by_instrument = {entry.instrument_id: entry for entry in request.shelf_entries}
    violations: list[tuple[SecurityTradeIntent, AuthoritativeClientRestrictionRule]] = []
    for intent in result.intents:
        if not isinstance(intent, SecurityTradeIntent):
            continue
        for restriction in active_applicable_restrictions(
            restrictions=context.restrictions,
            trade_side=intent.side,
        ):
            if restriction_matches_intent(
                intent=intent,
                shelf=shelf_by_instrument.get(intent.instrument_id),
                restriction=restriction,
            ):
                violations.append((intent, restriction))
    return violations


def active_applicable_restrictions(
    *,
    restrictions: list[AuthoritativeClientRestrictionRule],
    trade_side: str,
) -> list[AuthoritativeClientRestrictionRule]:
    return [
        restriction
        for restriction in restrictions
        if restriction.restriction_status.lower() == "active"
        and (
            (trade_side == "BUY" and restriction.applies_to_buy)
            or (trade_side == "SELL" and restriction.applies_to_sell)
        )
    ]


def restriction_matches_intent(
    *,
    intent: SecurityTradeIntent,
    shelf: ShelfEntry | None,
    restriction: AuthoritativeClientRestrictionRule,
) -> bool:
    scoped_values = (
        restriction.instrument_ids
        or restriction.asset_classes
        or restriction.issuer_ids
        or restriction.country_codes
    )
    if not scoped_values:
        return True
    if intent.instrument_id in restriction.instrument_ids:
        return True
    if shelf is None:
        return False
    if shelf.asset_class in restriction.asset_classes:
        return True
    if shelf.issuer_id and shelf.issuer_id in restriction.issuer_ids:
        return True
    country_of_risk = shelf.attributes.get("country_of_risk") or shelf.attributes.get("country")
    return bool(country_of_risk and country_of_risk in restriction.country_codes)


__all__ = [
    "active_applicable_restrictions",
    "client_restriction_reason_codes",
    "client_restriction_status",
    "restriction_matches_intent",
    "violated_client_restrictions",
]
