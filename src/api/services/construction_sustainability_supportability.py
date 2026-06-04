from decimal import Decimal

from src.core.construction.models import (
    AuthoritativeSustainabilityPreference,
    AuthoritativeSustainabilityPreferenceContext,
)
from src.core.construction.status import lowest_construction_status
from src.core.construction.vocabulary import ConstructionMethodStatus
from src.core.models import RebalanceResult


def sustainability_preference_status(
    *,
    result: RebalanceResult,
    context: AuthoritativeSustainabilityPreferenceContext | None,
) -> ConstructionMethodStatus:
    if context is None:
        return ConstructionMethodStatus.DEGRADED
    status = context.supportability_status
    if sustainability_allocation_breaches(result=result, context=context):
        status = lowest_construction_status([status, ConstructionMethodStatus.PENDING_REVIEW])
    if sustainability_classification_review_required(context=context):
        status = lowest_construction_status([status, ConstructionMethodStatus.PENDING_REVIEW])
    return status


def sustainability_preference_reason_codes(
    *,
    result: RebalanceResult,
    context: AuthoritativeSustainabilityPreferenceContext | None,
) -> list[str]:
    if context is None:
        return ["SUSTAINABILITY_PREFERENCE_PROFILE_UNAVAILABLE"]
    reason_codes = list(context.reason_codes)
    if context.supportability_status != ConstructionMethodStatus.READY:
        reason_codes.append(f"SUSTAINABILITY_PREFERENCE_PROFILE_{context.supportability_status}")
    reason_codes.extend(f"MISSING_{family.upper()}" for family in context.missing_data_families)
    breaches = sustainability_allocation_breaches(result=result, context=context)
    reason_codes.extend(
        f"SUSTAINABILITY_ALLOCATION_REVIEW_{preference.preference_code}" for preference in breaches
    )
    if sustainability_classification_review_required(context=context):
        reason_codes.append("SUSTAINABILITY_CLASSIFICATION_EVIDENCE_REQUIRED")
    if not breaches and not sustainability_classification_review_required(context=context):
        reason_codes.append("SUSTAINABILITY_PREFERENCE_PROFILE_APPLIED")
    return sorted(set(reason_codes))


def sustainability_allocation_breaches(
    *,
    result: RebalanceResult,
    context: AuthoritativeSustainabilityPreferenceContext,
) -> list[AuthoritativeSustainabilityPreference]:
    weight_by_asset_class = allocation_weight_by_asset_class(result=result)
    breaches: list[AuthoritativeSustainabilityPreference] = []
    for preference in active_sustainability_preferences(context=context):
        if not preference.applies_to_asset_classes:
            continue
        weight = sum(
            weight_by_asset_class.get(asset_class.lower(), Decimal("0"))
            for asset_class in preference.applies_to_asset_classes
        )
        if preference.minimum_allocation is not None and weight < preference.minimum_allocation:
            breaches.append(preference)
        if preference.maximum_allocation is not None and weight > preference.maximum_allocation:
            breaches.append(preference)
    return breaches


def allocation_weight_by_asset_class(*, result: RebalanceResult) -> dict[str, Decimal]:
    return {
        allocation.key.lower(): allocation.weight
        for allocation in result.after_simulated.allocation_by_asset_class
    }


def sustainability_classification_review_required(
    *,
    context: AuthoritativeSustainabilityPreferenceContext,
) -> bool:
    return any(
        preference.exclusion_codes or preference.positive_tilt_codes
        for preference in active_sustainability_preferences(context=context)
    )


def active_sustainability_preferences(
    *,
    context: AuthoritativeSustainabilityPreferenceContext,
) -> list[AuthoritativeSustainabilityPreference]:
    return [
        preference
        for preference in context.preferences
        if preference.preference_status.lower() == "active"
    ]


__all__ = [
    "active_sustainability_preferences",
    "allocation_weight_by_asset_class",
    "sustainability_allocation_breaches",
    "sustainability_classification_review_required",
    "sustainability_preference_reason_codes",
    "sustainability_preference_status",
]
