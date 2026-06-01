from src.api.request_models import RebalanceRequest
from src.api.services.construction_client_restriction_supportability import (
    client_restriction_reason_codes,
    client_restriction_status,
    restriction_matches_intent,
    violated_client_restrictions,
)
from src.api.services.construction_sustainability_supportability import (
    sustainability_allocation_breaches,
    sustainability_classification_review_required,
    sustainability_preference_reason_codes,
    sustainability_preference_status,
)
from src.core.construction.models import (
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
