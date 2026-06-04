from typing import TypeAlias

from src.api.services.construction_source_product_status import source_status_to_method_status
from src.api.services.construction_source_identity import source_product_identity
from src.core.construction.models import (
    AuthoritativeClientRestrictionContext,
    AuthoritativeClientRestrictionRule,
    AuthoritativeSustainabilityPreference,
    AuthoritativeSustainabilityPreferenceContext,
)
from src.core.dpm_source_context import (
    DpmCoreClientRestrictionProfileResponse,
    DpmCoreSustainabilityPreferenceProfileResponse,
)

ClientProfileSourceResponse: TypeAlias = (
    DpmCoreClientRestrictionProfileResponse | DpmCoreSustainabilityPreferenceProfileResponse
)


def client_profile_source_fields(profile: ClientProfileSourceResponse) -> dict[str, object]:
    identity = source_product_identity(profile)
    return {
        "supportability_status": source_status_to_method_status(profile.supportability.state),
        "source_system": identity.source_system,
        "source_product_name": identity.source_product_name,
        "source_product_version": identity.source_product_version,
        "source_id": identity.source_id,
        "content_hash": identity.content_hash,
        "portfolio_id": profile.portfolio_id,
        "client_id": profile.client_id,
        "mandate_id": profile.mandate_id,
        "as_of_date": profile.as_of_date,
    }


def client_restriction_profile_context(
    restriction_profile: DpmCoreClientRestrictionProfileResponse,
) -> AuthoritativeClientRestrictionContext:
    return AuthoritativeClientRestrictionContext.model_validate(
        {
            **client_profile_source_fields(restriction_profile),
            "restriction_count": restriction_profile.supportability.restriction_count,
            "missing_data_families": restriction_profile.supportability.missing_data_families,
            "restrictions": client_restriction_rules(restriction_profile),
            "reason_codes": [restriction_profile.supportability.reason],
        }
    )


def client_restriction_rules(
    restriction_profile: DpmCoreClientRestrictionProfileResponse,
) -> list[AuthoritativeClientRestrictionRule]:
    return [
        AuthoritativeClientRestrictionRule.model_validate(rule.model_dump(mode="python"))
        for rule in restriction_profile.restrictions
    ]


def sustainability_preference_profile_context(
    sustainability_profile: DpmCoreSustainabilityPreferenceProfileResponse,
) -> AuthoritativeSustainabilityPreferenceContext:
    return AuthoritativeSustainabilityPreferenceContext.model_validate(
        {
            **client_profile_source_fields(sustainability_profile),
            "preference_count": sustainability_profile.supportability.preference_count,
            "missing_data_families": sustainability_profile.supportability.missing_data_families,
            "preferences": sustainability_preferences(sustainability_profile),
            "reason_codes": [sustainability_profile.supportability.reason],
        }
    )


def sustainability_preferences(
    sustainability_profile: DpmCoreSustainabilityPreferenceProfileResponse,
) -> list[AuthoritativeSustainabilityPreference]:
    return [
        AuthoritativeSustainabilityPreference.model_validate(preference.model_dump(mode="python"))
        for preference in sustainability_profile.preferences
    ]


__all__ = [
    "ClientProfileSourceResponse",
    "client_restriction_rules",
    "client_profile_source_fields",
    "client_restriction_profile_context",
    "sustainability_preference_profile_context",
    "sustainability_preferences",
]
