from decimal import Decimal

from src.api.request_models import RebalanceRequest
from src.api.services.construction_client_restriction_supportability import (
    client_restriction_reason_codes,
    client_restriction_status,
    restriction_matches_intent,
    violated_client_restrictions,
)
from src.core.construction.models import (
    AuthoritativeSustainabilityPreference,
    AuthoritativeSustainabilityPreferenceContext,
    ConstructionAlternative,
    ConstructionAuthorityContext,
    ConstructionConstraintTrace,
)
from src.core.construction.status import lowest_construction_status
from src.core.construction.vocabulary import (
    ConstructionMethodStatus,
    ConstructionSourceFamily,
    ConstructionTraceTerm,
)
from src.core.models import RebalanceResult


def with_esg_restriction_constraints(
    *,
    request: RebalanceRequest,
    alternative: ConstructionAlternative,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionAlternative:
    return alternative.model_copy(
        update={
            "constraint_trace": [
                *alternative.constraint_trace,
                ConstructionConstraintTrace(
                    constraint=ConstructionTraceTerm.CLIENT_RESTRICTION,
                    status=client_restriction_status(
                        request=request,
                        result=result,
                        context=authority_context.client_restriction_context,
                    ),
                    source_family=ConstructionSourceFamily.ESG_PROFILE,
                    reason_codes=client_restriction_reason_codes(
                        request=request,
                        result=result,
                        context=authority_context.client_restriction_context,
                    ),
                    description=(
                        "Source-owned ClientRestrictionProfile:v1 evidence is applied to "
                        "candidate buy/sell intents when available."
                    ),
                ),
                ConstructionConstraintTrace(
                    constraint=ConstructionTraceTerm.SUSTAINABILITY_PREFERENCE,
                    status=sustainability_preference_status(
                        result=result,
                        context=authority_context.sustainability_preference_context,
                    ),
                    source_family=ConstructionSourceFamily.ESG_PROFILE,
                    reason_codes=sustainability_preference_reason_codes(
                        result=result,
                        context=authority_context.sustainability_preference_context,
                    ),
                    description=(
                        "Source-owned SustainabilityPreferenceProfile:v1 evidence is attached; "
                        "classification-dependent controls remain pending review when the "
                        "source profile alone is insufficient."
                    ),
                ),
            ]
        }
    )


def esg_restriction_status(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> ConstructionMethodStatus:
    return lowest_construction_status(
        [
            client_restriction_status(
                request=request,
                result=result,
                context=authority_context.client_restriction_context,
            ),
            sustainability_preference_status(
                result=result,
                context=authority_context.sustainability_preference_context,
            ),
        ]
    )


def esg_restriction_reason_codes(
    *,
    request: RebalanceRequest,
    result: RebalanceResult,
    authority_context: ConstructionAuthorityContext,
) -> list[str]:
    return sorted(
        set(
            client_restriction_reason_codes(
                request=request,
                result=result,
                context=authority_context.client_restriction_context,
            )
            + sustainability_preference_reason_codes(
                result=result,
                context=authority_context.sustainability_preference_context,
            )
        )
    )


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
    weight_by_asset_class = {
        allocation.key.lower(): allocation.weight
        for allocation in result.after_simulated.allocation_by_asset_class
    }
    breaches: list[AuthoritativeSustainabilityPreference] = []
    for preference in context.preferences:
        if preference.preference_status.lower() != "active":
            continue
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


def sustainability_classification_review_required(
    *,
    context: AuthoritativeSustainabilityPreferenceContext,
) -> bool:
    return any(
        preference.preference_status.lower() == "active"
        and (preference.exclusion_codes or preference.positive_tilt_codes)
        for preference in context.preferences
    )


__all__ = [
    "client_restriction_reason_codes",
    "client_restriction_status",
    "esg_restriction_reason_codes",
    "esg_restriction_status",
    "restriction_matches_intent",
    "sustainability_allocation_breaches",
    "sustainability_classification_review_required",
    "sustainability_preference_reason_codes",
    "sustainability_preference_status",
    "violated_client_restrictions",
    "with_esg_restriction_constraints",
]
