from datetime import date

from src.api.request_models import RebalanceRequest
from src.core.construction.models import (
    AuthoritativeClientRestrictionContext,
    AuthoritativeClientRestrictionRule,
    ConstructionAlternative,
    ConstructionAuthorityContext,
    ConstructionConstraintTrace,
)
from src.core.construction.vocabulary import (
    ConstructionMethodStatus,
    ConstructionSourceFamily,
    ConstructionTraceTerm,
)
from src.core.models import RebalanceResult, SecurityTradeIntent, ShelfEntry


def client_restriction_policy_required(context: ConstructionAuthorityContext) -> bool:
    return context.client_restriction_required or context.client_restriction_context is not None


def with_client_restriction_constraint(
    *,
    request: RebalanceRequest,
    alternative: ConstructionAlternative,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionAlternative:
    context = authority_context.client_restriction_context
    return alternative.model_copy(
        update={
            "constraint_trace": [
                *alternative.constraint_trace,
                ConstructionConstraintTrace(
                    constraint=ConstructionTraceTerm.CLIENT_RESTRICTION,
                    status=client_restriction_status(
                        request=request, result=result, context=context
                    ),
                    source_family=ConstructionSourceFamily.CLIENT_RESTRICTION_PROFILE,
                    reason_codes=client_restriction_reason_codes(
                        request=request, result=result, context=context
                    ),
                    description=(
                        "Mandatory source-owned ClientRestrictionProfile:v1 policy for candidate "
                        "buy/sell intents, independent of construction optimization method."
                    ),
                ),
            ]
        }
    )


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
    if (
        context.supportability_status == ConstructionMethodStatus.READY
        and missing_restriction_classifications(request=request, result=result, context=context)
    ):
        return ConstructionMethodStatus.DEGRADED
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
    missing_families = missing_restriction_classifications(
        request=request, result=result, context=context
    )
    reason_codes.extend(f"MISSING_{family.upper()}" for family in missing_families)
    violations = violated_client_restrictions(request=request, result=result, context=context)
    if violations:
        reason_codes.extend(
            f"CLIENT_RESTRICTION_VIOLATION_{restriction.restriction_code}"
            for _, restriction in violations
        )
    elif not missing_families:
        reason_codes.append("CLIENT_RESTRICTION_PROFILE_APPLIED")
    return sorted(set(reason_codes))


def missing_restriction_classifications(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    context: AuthoritativeClientRestrictionContext,
) -> set[str]:
    """Do not infer permission when an applicable rule cannot be classified."""
    missing = set(context.missing_data_families)
    shelf_by_instrument = shelf_entries_by_instrument(request=request)
    for intent in result.intents:
        if not isinstance(intent, SecurityTradeIntent):
            continue
        for rule in active_applicable_restrictions(
            restrictions=context.restrictions,
            trade_side=intent.side,
            as_of_date=context.as_of_date,
        ):
            shelf = shelf_by_instrument.get(intent.instrument_id)
            missing.update(_unresolved_rule_classifications(intent=intent, shelf=shelf, rule=rule))
    return missing


def _unresolved_rule_classifications(
    *,
    intent: SecurityTradeIntent,
    shelf: ShelfEntry | None,
    rule: AuthoritativeClientRestrictionRule,
) -> set[str]:
    if restriction_matches_instrument(intent=intent, restriction=rule):
        return set()
    if shelf is None:
        return (
            {"instrument_classification"}
            if rule.asset_classes or rule.issuer_ids or rule.country_codes
            else set()
        )
    if restriction_matches_shelf(shelf=shelf, restriction=rule):
        return set()
    missing = set()
    if rule.asset_classes and shelf.asset_class in {"", "UNKNOWN"}:
        missing.add("asset_class_classification")
    if rule.issuer_ids and not shelf.issuer_id:
        missing.add("issuer_classification")
    if rule.country_codes and not shelf_country_code(shelf):
        missing.add("country_classification")
    return missing


def violated_client_restrictions(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    context: AuthoritativeClientRestrictionContext,
) -> list[tuple[SecurityTradeIntent, AuthoritativeClientRestrictionRule]]:
    shelf_by_instrument = shelf_entries_by_instrument(request=request)
    violations: list[tuple[SecurityTradeIntent, AuthoritativeClientRestrictionRule]] = []
    for intent in result.intents:
        if not isinstance(intent, SecurityTradeIntent):
            continue
        for restriction in active_applicable_restrictions(
            restrictions=context.restrictions,
            trade_side=intent.side,
            as_of_date=context.as_of_date,
        ):
            if restriction_matches_intent(
                intent=intent,
                shelf=shelf_by_instrument.get(intent.instrument_id),
                restriction=restriction,
            ):
                violations.append((intent, restriction))
    return violations


def shelf_entries_by_instrument(*, request: RebalanceRequest) -> dict[str, ShelfEntry]:
    return {entry.instrument_id: entry for entry in request.shelf_entries}


def active_applicable_restrictions(
    *,
    restrictions: list[AuthoritativeClientRestrictionRule],
    trade_side: str,
    as_of_date: date,
) -> list[AuthoritativeClientRestrictionRule]:
    return [
        restriction
        for restriction in restrictions
        if restriction.restriction_status.lower() == "active"
        and restriction.effective_from <= as_of_date
        and (restriction.effective_to is None or as_of_date <= restriction.effective_to)
        and (
            (trade_side == "BUY" and restriction.applies_to_buy)
            or (trade_side == "SELL" and restriction.applies_to_sell)
        )
    ]


def restriction_has_scope(restriction: AuthoritativeClientRestrictionRule) -> bool:
    return bool(
        restriction.instrument_ids
        or restriction.asset_classes
        or restriction.issuer_ids
        or restriction.country_codes
    )


def restriction_matches_instrument(
    *,
    intent: SecurityTradeIntent,
    restriction: AuthoritativeClientRestrictionRule,
) -> bool:
    return intent.instrument_id in restriction.instrument_ids


def shelf_country_code(shelf: ShelfEntry) -> str | None:
    return shelf.attributes.get("country_of_risk") or shelf.attributes.get("country")


def restriction_matches_shelf(
    *,
    shelf: ShelfEntry,
    restriction: AuthoritativeClientRestrictionRule,
) -> bool:
    if shelf.asset_class in restriction.asset_classes:
        return True
    if shelf.issuer_id and shelf.issuer_id in restriction.issuer_ids:
        return True
    country_code = shelf_country_code(shelf)
    return bool(country_code and country_code in restriction.country_codes)


def restriction_matches_intent(
    *,
    intent: SecurityTradeIntent,
    shelf: ShelfEntry | None,
    restriction: AuthoritativeClientRestrictionRule,
) -> bool:
    if not restriction_has_scope(restriction):
        return True
    if restriction_matches_instrument(intent=intent, restriction=restriction):
        return True
    if shelf is None:
        return False
    return restriction_matches_shelf(shelf=shelf, restriction=restriction)


__all__ = [
    "active_applicable_restrictions",
    "client_restriction_policy_required",
    "client_restriction_reason_codes",
    "client_restriction_status",
    "missing_restriction_classifications",
    "restriction_has_scope",
    "restriction_matches_instrument",
    "restriction_matches_intent",
    "restriction_matches_shelf",
    "shelf_country_code",
    "shelf_entries_by_instrument",
    "violated_client_restrictions",
    "with_client_restriction_constraint",
]
