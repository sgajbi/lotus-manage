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
    breaches = sustainability_allocation_breaches(result=result, context=context)
    classification_review_required = sustainability_classification_review_required(context=context)
    reason_codes = [
        *context.reason_codes,
        *_sustainability_supportability_reason_codes(context.supportability_status),
        *_missing_sustainability_family_reason_codes(context.missing_data_families),
        *_sustainability_allocation_review_reason_codes(breaches),
        *_sustainability_classification_reason_codes(classification_review_required),
        *_sustainability_applied_reason_codes(
            breaches=breaches,
            classification_review_required=classification_review_required,
        ),
    ]
    return sorted(set(reason_codes))


def _sustainability_supportability_reason_codes(
    status: ConstructionMethodStatus,
) -> list[str]:
    if status == ConstructionMethodStatus.READY:
        return []
    return [f"SUSTAINABILITY_PREFERENCE_PROFILE_{status}"]


def _missing_sustainability_family_reason_codes(
    missing_data_families: list[str],
) -> list[str]:
    return [f"MISSING_{family.upper()}" for family in missing_data_families]


def _sustainability_allocation_review_reason_codes(
    breaches: list[AuthoritativeSustainabilityPreference],
) -> list[str]:
    return [
        f"SUSTAINABILITY_ALLOCATION_REVIEW_{preference.preference_code}" for preference in breaches
    ]


def _sustainability_classification_reason_codes(
    classification_review_required: bool,
) -> list[str]:
    return (
        ["SUSTAINABILITY_CLASSIFICATION_EVIDENCE_REQUIRED"]
        if classification_review_required
        else []
    )


def _sustainability_applied_reason_codes(
    *,
    breaches: list[AuthoritativeSustainabilityPreference],
    classification_review_required: bool,
) -> list[str]:
    if breaches or classification_review_required:
        return []
    return ["SUSTAINABILITY_PREFERENCE_PROFILE_APPLIED"]


def sustainability_allocation_breaches(
    *,
    result: RebalanceResult,
    context: AuthoritativeSustainabilityPreferenceContext,
) -> list[AuthoritativeSustainabilityPreference]:
    weight_by_asset_class = allocation_weight_by_asset_class(result=result)
    return [
        preference
        for preference in active_sustainability_preferences(context=context)
        if _preference_allocation_breached(
            preference=preference,
            weight_by_asset_class=weight_by_asset_class,
        )
    ]


def _preference_allocation_breached(
    *,
    preference: AuthoritativeSustainabilityPreference,
    weight_by_asset_class: dict[str, Decimal],
) -> bool:
    if not preference.applies_to_asset_classes:
        return False
    weight = _preference_allocation_weight(
        preference=preference,
        weight_by_asset_class=weight_by_asset_class,
    )
    return _minimum_allocation_breached(
        preference=preference,
        weight=weight,
    ) or _maximum_allocation_breached(preference=preference, weight=weight)


def _preference_allocation_weight(
    *,
    preference: AuthoritativeSustainabilityPreference,
    weight_by_asset_class: dict[str, Decimal],
) -> Decimal:
    return sum(
        (
            weight_by_asset_class.get(asset_class.lower(), Decimal("0"))
            for asset_class in preference.applies_to_asset_classes
        ),
        Decimal("0"),
    )


def _minimum_allocation_breached(
    *,
    preference: AuthoritativeSustainabilityPreference,
    weight: Decimal,
) -> bool:
    return preference.minimum_allocation is not None and weight < preference.minimum_allocation


def _maximum_allocation_breached(
    *,
    preference: AuthoritativeSustainabilityPreference,
    weight: Decimal,
) -> bool:
    return preference.maximum_allocation is not None and weight > preference.maximum_allocation


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
